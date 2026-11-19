"""Nhi: nghiên cứu xu hướng và chăm các Trang theo chủ đề nóng.

1. Nghiên cứu: mỗi sáng đọc Google Trends Việt Nam (RSS công khai: tìm kiếm tăng mạnh hôm nay, lượt tìm, tin liên quan), lưu lại
   từng ngày. Nhi (Claude) chấm chủ đề nào nóng bền (lặp lại nhiều ngày, có cộng đồng quan tâm lâu) chứ không chỉ một tin chớp nhoáng,
   và đề xuất Trang mới cho ngách đáng làm: tên, mô tả, hạng mục, prompt ảnh đại diện / ảnh bìa, lý do.
2. Tạo Trang: sếp tạo tay trên Facebook (khoảng 3 phút) rồi dán link + chọn nick quản trị. Phần mềm không tự tạo Trang: tạo Trang
   bằng công cụ tự động dễ bị Facebook coi là tạo tài khoản / tài sản giả, khóa luôn nick quản trị.
3. Lịch đăng: mỗi Trang đang chạy, mỗi sáng Nhi viết đủ bài cho các giờ đăng hôm nay (bám chủ đề nóng hợp ngách của Trang) kèm
   prompt tạo ảnh. Bài chờ ảnh: gửi prompt lên Telegram; sếp tạo ảnh rồi TRẢ LỜI tin đó bằng ảnh, phần mềm tự lấy ảnh, xếp bài đăng.
   Nick quản trị chuyển sang Trang đăng bài (browser_poster._switch_to_page), đăng xong chuyển về. Bài chờ ảnh quá 24 giờ thì bỏ.
"""
import random
import re
import xml.etree.ElementTree as ET
from datetime import timedelta
from pathlib import Path

import db

RSS = "https://trends.google.com/trending/rss?geo=VN"
NS = {"ht": "https://trends.google.com/trending/rss"}


def img_dir() -> Path:
    return Path(db.DB_PATH).parent / "media" / "trend_pages"


def _s() -> dict:
    return db.get_settings()


def _ago(**kw) -> str:
    return (db.clock() - timedelta(**kw)).strftime("%Y-%m-%d %H:%M:%S")


def traffic_num(t: str | None) -> int:
    m = re.match(r"\s*([\d.,]+)\s*([KkMm]?)", t or "")
    if not m:
        return 0
    n = float(m.group(1).replace(",", "").replace(".", "")) if not m.group(2) else float(m.group(1).replace(",", "."))
    return int(n * {"k": 1000, "m": 1000000}.get(m.group(2).lower(), 1))


# ---------------------------------------------------------------- 1. nghiên cứu xu hướng
def parse_rss(xml: str) -> list[dict]:
    out = []
    root = ET.fromstring(xml)
    for it in root.iter("item"):
        news = [{"title": (n.findtext("ht:news_item_title", "", NS) or "").strip(), "source": n.findtext("ht:news_item_source", "", NS) or ""}
                for n in it.findall("ht:news_item", NS)]
        out.append({"title": (it.findtext("title") or "").strip(), "traffic": it.findtext("ht:approx_traffic", "", NS) or "",
                    "news": [x for x in news if x["title"]][:3]})
    return [x for x in out if x["title"]]


def fetch_trends(fetch=None) -> list[dict]:
    if fetch:
        return fetch()
    import httpx
    r = httpx.get(RSS, timeout=30, headers={"User-Agent": "Mozilla/5.0"})
    r.raise_for_status()
    return parse_rss(r.text)


def save_trends(items: list[dict]) -> int:
    import json
    n = 0
    for x in items:
        if db.one("SELECT id FROM trends WHERE day=? AND title=?", (db.today(), x["title"])):
            continue
        db.run("INSERT INTO trends(day, title, traffic, traffic_n, news, created_at) VALUES (?,?,?,?,?,?)",
               (db.today(), x["title"], x.get("traffic"), traffic_num(x.get("traffic")), json.dumps(x.get("news") or [], ensure_ascii=False), db.now()))
        n += 1
    return n


def _mock_research(trends: list[dict], pages: list[dict]) -> dict:
    top = sorted(trends, key=lambda t: -(t.get("traffic_n") or 0))[:8]
    hot = [{"title": t["title"], "score": min(95, 40 + (t.get("traffic_n") or 0) // 20000), "niche": t["title"], "why": f"Lượt tìm {t.get('traffic')}"}
           for t in top]
    ideas = [{"name": f"Góc {t['title']}", "niche": t["title"], "category": "Trang tin tức & giải trí",
              "description": f"Cập nhật nhanh, dễ hiểu về {t['title']} và những chủ đề liên quan.",
              "avatar_prompt": f"Minimal flat icon representing {t['title']}, bold colors, centered, no text, square",
              "cover_prompt": f"Wide banner illustration about {t['title']}, modern flat style, no text, 1640x624",
              "why": "Chủ đề có lượt tìm cao (chế độ mô phỏng, chưa có Claude chấm)", "trends": [t["title"]]} for t in top[:2]]
    return {"hot": hot, "ideas": ideas}


def research(fetch=None) -> dict:
    """Đọc xu hướng hôm nay, Nhi chấm chủ đề nóng và đề xuất tối đa 3 Trang mới."""
    import json
    import workflows
    from agents import system_prompt
    from llm import llm
    workflows.set_status("nhi", "working", "Đọc xu hướng tìm kiếm hôm nay")
    try:
        try:
            got = save_trends(fetch_trends(fetch))
        except Exception as e:
            import errors
            errors.report("trends", "Không đọc được Google Trends", str(e)[:300], screen="trends")
            got = 0
        rows = db.q("SELECT title, traffic, traffic_n, news, day FROM trends WHERE day >= ? ORDER BY day DESC, traffic_n DESC LIMIT 60",
                    ((db.clock() - timedelta(days=3)).strftime("%Y-%m-%d"),))
        if not rows:
            return {"ok": False, "why": "Chưa có dữ liệu xu hướng (máy chạy phần mềm cần có mạng)"}
        pages = db.q("SELECT name, niche, status FROM fb_pages WHERE status IN ('active','idea')")
        days = {}
        for r in rows:
            days.setdefault(r["title"].lower(), set()).add(r["day"])
        lines = "\n".join(f"- [{r['day'][5:]}] {r['title']} ({r['traffic']} lượt tìm, {len(days[r['title'].lower()])} ngày) — "
                          + "; ".join(n["title"][:80] for n in json.loads(r["news"] or "[]")[:2]) for r in rows[:40])
        ask = f"""Xu hướng tìm kiếm Google Việt Nam 3 ngày gần đây (mới nhất trước):
{lines}

Trang đang có / đã đề xuất: {', '.join(f"{p['name']} ({p['niche']})" for p in pages) or '(chưa có)'}

Việc của bạn:
1. "hot": tối đa 10 chủ đề đáng viết hôm nay, điểm 0–100 (nóng + còn quan tâm vài ngày + dễ viết bài có ích), gán vào ngách lớn (VD "bóng đá",
   "mẹo nấu ăn", "sức khỏe gia đình", "công nghệ"), một câu lý do.
2. "ideas": tối đa 3 Trang MỚI cho ngách nóng BỀN (lặp nhiều ngày / có cộng đồng quan tâm lâu dài), không trùng Trang đang có. Không làm Trang
   về chính trị, tôn giáo, người thật cụ thể (người nổi tiếng, nạn nhân), tai nạn / tội phạm, cờ bạc, nội dung người lớn, tin giả mạo danh
   cơ quan / báo chí. Tên Trang tự nhiên, không giả làm Trang chính thức của tổ chức hay người nào.
   Mỗi ý tưởng: name, niche, category (hạng mục Trang trên Facebook), description (≤ 200 ký tự), avatar_prompt và cover_prompt (tiếng Anh,
   cho công cụ tạo ảnh: không chữ, không logo, không mặt người thật), why, trends (các xu hướng làm căn cứ).
Trả về JSON: {{"hot": [{{"title","score","niche","why"}}], "ideas": [...]}}"""
        try:  # Nhi tự học: kết quả chủ đề đã viết + độ chính xác chọn xu hướng
            import trend_learn
            note = trend_learn.research_note()
        except Exception as e:
            print("[trend learn]", e)
            note = ""
        if note:
            ask = ask.replace("\n\nViệc của bạn:", f"\n\nBạn tự học từ kết quả trước (dùng để chấm điểm sát hơn):\n{note}\n\nViệc của bạn:", 1)
        trends = [dict(r) for r in rows]
        d = llm.json(system_prompt("nhi", _s()), ask, mock=lambda: _mock_research(trends, pages), max_tokens=2500, task="posts") or {}
        db.run("DELETE FROM trend_hot WHERE day=?", (db.today(),))
        for h in (d.get("hot") or [])[:10]:
            db.run("INSERT INTO trend_hot(day, title, score, niche, why, created_at) VALUES (?,?,?,?,?,?)",
                   (db.today(), str(h.get("title"))[:120], int(h.get("score") or 0), str(h.get("niche") or "")[:60], str(h.get("why") or "")[:300], db.now()))
        new = 0
        for i in (d.get("ideas") or [])[:3]:
            name = str(i.get("name") or "").strip()[:80]
            if not name or db.one("SELECT id FROM fb_pages WHERE lower(name)=lower(?) OR lower(niche)=lower(?)", (name, str(i.get("niche") or ""))):
                continue
            db.run("""INSERT INTO fb_pages(name, niche, category, description, avatar_prompt, cover_prompt, reason, trends, status, created_at)
                      VALUES (?,?,?,?,?,?,?,?, 'idea', ?)""",
                   (name, str(i.get("niche") or "")[:60], str(i.get("category") or "")[:60], str(i.get("description") or "")[:255],
                    str(i.get("avatar_prompt") or "")[:600], str(i.get("cover_prompt") or "")[:600], str(i.get("why") or "")[:400],
                    ", ".join(i.get("trends") or [])[:400], db.now()))
            new += 1
        db.set_setting("trend_research_day", db.today())
        db.log("nhi", "Nghiên cứu xu hướng", f"Đọc {got} xu hướng mới, {len(d.get('hot') or [])} chủ đề đáng viết, {new} ý tưởng Trang mới")
        if new:
            _tg(f"🔎 <b>Nhi đề xuất {new} Trang mới theo xu hướng</b>\nXem và tạo Trang ở mục <b>Trang xu hướng</b> của phần mềm.")
        return {"ok": True, "trends": got, "hot": len(d.get("hot") or []), "ideas": new}
    finally:
        workflows.set_status("nhi", "idle", "Đang sẵn sàng")


# ---------------------------------------------------------------- 2. Trang
def activate(pid: int, url: str, admin_id: int, per_day: int = 2, times: str = "09:00,19:30") -> dict:
    p = db.one("SELECT * FROM fb_pages WHERE id=?", (pid,))
    if not p:
        raise ValueError("Không tìm thấy Trang này")
    url = (url or "").strip()
    if "facebook.com" not in url and not url.startswith("http://localhost"):
        raise ValueError("Dán link Trang trên facebook.com (VD https://facebook.com/tentrang)")
    if not db.one("SELECT id FROM fb_accounts WHERE id=?", (admin_id,)):
        raise ValueError("Chọn nick quản trị Trang")
    ts = ",".join(t for t in (x.strip() for x in times.split(",")) if re.fullmatch(r"\d\d:\d\d", t))[:17] or "09:00,19:30"
    db.run("""UPDATE fb_pages SET url=?, admin_account_id=?, posts_per_day=?, times=?, status='active', activated_at=COALESCE(activated_at, ?)
              WHERE id=?""", (url, admin_id, max(1, min(3, per_day)), ts, db.now(), pid))
    db.log("nhi", "Trang mới chạy", f"Trang {p['name']} ({url}) bắt đầu lên lịch đăng")
    return db.one("SELECT * FROM fb_pages WHERE id=?", (pid,))


def new_page(name: str, niche: str, description: str = "") -> dict:
    """Sếp tự thêm một Trang (đã có sẵn) để Nhi chăm."""
    if not (name or "").strip():
        raise ValueError("Điền tên Trang")
    pid = db.run("INSERT INTO fb_pages(name, niche, description, status, reason, created_at) VALUES (?,?,?, 'idea', 'Sếp thêm', ?)",
                 (name.strip()[:80], (niche or name).strip()[:60], (description or "").strip()[:255], db.now()))
    return db.one("SELECT * FROM fb_pages WHERE id=?", (pid,))


# ---------------------------------------------------------------- 3. bài + ảnh qua Telegram
def _mock_post(pg: dict, topic: str) -> dict:
    return {"content": f"📌 {topic}: những điều đáng chú ý hôm nay\n\nTóm tắt ngắn, dễ hiểu cho người theo dõi {pg['name']}. "
                       f"Bạn nghĩ sao về chủ đề này? Bình luận bên dưới nhé 👇",
            "image_prompt": f"Clean editorial illustration about {topic}, vibrant colors, 4:5 portrait, no text, no logos, no real faces",
            "image_note": f"Ảnh minh họa về {topic}, không chữ"}


def write_post(pg: dict, when: str) -> dict:
    from agents import system_prompt
    from llm import llm
    import fb_policy
    import pricing
    hot = db.q("SELECT title, niche, score, why FROM trend_hot WHERE day=? ORDER BY score DESC LIMIT 10", (db.today(),))
    used = {r["topic"] for r in db.q("SELECT trend_topic topic FROM posts WHERE fb_page_ref=? AND created_at >= ?", (pg["id"], _ago(days=3)))}
    fit = [h for h in hot if h["title"] not in used and (pg["niche"] or "").lower() in (h["niche"] + " " + h["title"]).lower()]
    import trend_learn
    sty = trend_learn.style(pg)
    if sty["kind"] == "evergreen":  # số liệu cho thấy bài bền hợp hơn (hoặc lượt thử): không gắn tin nóng
        fit = []
    kind = "trend" if fit else "evergreen"
    learned = ("\nKinh nghiệm từ số liệu Trang: " + "; ".join(sty["notes"]) + "." if sty["notes"] else "") + \
        (f"\nBài được hưởng ứng nhất của Trang này (học giọng, không chép):\n{sty['example']}" if sty["example"] else "")
    topic = (fit[0]["title"] if fit else pg["niche"]) or pg["name"]
    recent = db.q("SELECT content FROM posts WHERE fb_page_ref=? ORDER BY id DESC LIMIT 6", (pg["id"],))
    ask = f"""Viết 1 bài cho Trang Facebook "{pg['name']}" (ngách: {pg['niche']}; {pg.get('description') or ''}).
Chủ đề hôm nay: {topic}{(' — đang lên xu hướng: ' + fit[0]['why']) if fit else ' (chưa có xu hướng hợp ngách hôm nay: viết bài có ích, bền, không gắn tin nóng)'}.
Yêu cầu: {sty['words'] or '60–160 chữ'}, mở đầu gây chú ý nhưng không giật tít sai sự thật; thông tin chung, không bịa số liệu / trích dẫn / lời người thật;
không nói về người thật cụ thể theo kiểu bôi nhọ hay đồn đoán; không chính trị, không cờ bạc; không kêu gọi like / share / tag để nhận quà;
kết bằng 1 câu hỏi mở để người đọc bình luận. 1–3 emoji, 2–3 hashtag.
Kèm "image_prompt" (tiếng Anh, cho công cụ tạo ảnh: mô tả cảnh, phong cách, tỉ lệ 4:5, không chữ, không logo, không mặt người thật / người nổi tiếng)
và "image_note" (1 câu tiếng Việt: ảnh nên trông thế nào).
{learned}
Đừng mở đầu giống các bài gần đây: {' | '.join((r['content'] or '')[:50] for r in recent) or '(chưa có)'}
JSON: {{"content": "...", "hashtags": "...", "image_prompt": "...", "image_note": "..."}}"""
    d = llm.json(system_prompt("nhi", _s()), ask, mock=lambda: _mock_post(pg, topic), max_tokens=900, task="posts") or {}
    text = pricing.sanitize((d.get("content") or "").strip(), add_contact=False)
    if not text or [i for i in fb_policy.check_text(text) if i["level"] == "high"]:
        d = _mock_post(pg, topic)
        text = d["content"]
    acc = db.one("SELECT * FROM fb_accounts WHERE id=?", (pg["admin_account_id"],)) or {}
    pid = db.run("""INSERT INTO posts(agent_id, target_type, title, content, hashtags, status, scheduled_for, account_id, sale_id, fb_page_ref,
                    trend_topic, trend_kind, image_prompt, image_note, source, created_at) VALUES ('nhi', 'page', ?, ?, ?, 'need_image', ?, ?, ?, ?, ?, ?, ?, ?, 'trend_page', ?)""",
                 (f"{pg['name']} · {topic}"[:120], text, d.get("hashtags") or "", when, acc.get("id"), acc.get("sale_id"), pg["id"], topic, kind,
                  (d.get("image_prompt") or _mock_post(pg, topic)["image_prompt"])[:900], (d.get("image_note") or "")[:300], db.now()))
    ask_image(pid)
    return db.one("SELECT * FROM posts WHERE id=?", (pid,))


def _tg(text: str) -> list:
    """Tin của Nhi đi qua bot ảnh riêng (telegram_img) nếu sếp đã cài, không thì qua bot chính."""
    try:
        import telegram_img
        if telegram_img.configured():
            return telegram_img.send(text)
        import telegram_bot
        if telegram_bot.configured():
            return telegram_bot.send(text)
    except Exception as e:
        print("[trend tg]", e)
    return []


def ask_image(post_id: int) -> bool:
    """Gửi prompt tạo ảnh của bài lên Telegram; sếp trả lời tin đó bằng ảnh."""
    import telegram_bot
    p = db.one("SELECT p.*, f.name page_name FROM posts p LEFT JOIN fb_pages f ON f.id=p.fb_page_ref WHERE p.id=?", (post_id,))
    if not p:
        return False
    e = telegram_bot.e
    msg = (f"🖼 <b>Cần ảnh cho bài #{p['id']}</b> · Trang <b>{e(p['page_name'])}</b> · đăng lúc {(p['scheduled_for'] or '')[11:16]} {(p['scheduled_for'] or '')[8:10]}/{(p['scheduled_for'] or '')[5:7]}\n"
           f"{e((p['content'] or '')[:300])}\n\n<b>Prompt tạo ảnh</b> (chạm để chép):\n<code>{e(p['image_prompt'])}</code>\n"
           + (f"Gợi ý: {e(p['image_note'])}\n" if p.get("image_note") else "")
           + f"\n👉 Tạo ảnh xong, <b>trả lời (reply) tin này bằng ảnh</b>. Nhi tự lấy ảnh và xếp đăng.")
    res = _tg(msg)
    ids = ",".join(str(r.get("message_id")) for r in res if isinstance(r, dict) and r.get("message_id"))
    if ids:
        db.run("UPDATE posts SET img_req_msg=?, img_req_at=? WHERE id=?", (ids, db.now(), post_id))
    return bool(ids)


def _waiting_for(reply_id: int | None) -> dict | None:
    if reply_id:
        for p in db.q("SELECT * FROM posts WHERE status='need_image' AND img_req_msg IS NOT NULL ORDER BY id DESC LIMIT 200"):
            if str(reply_id) in (p["img_req_msg"] or "").split(","):
                return p
        return None
    return db.one("SELECT * FROM posts WHERE status='need_image' ORDER BY COALESCE(scheduled_for, created_at), id LIMIT 1")


def set_image(post_id: int, data: bytes, ext: str = "jpg") -> dict:
    """Gắn ảnh sếp gửi vào bài và xếp đăng (giờ đã qua thì xếp giờ trống gần nhất)."""
    if len(data) < 1000:
        raise ValueError("Ảnh hỏng hoặc quá nhỏ")
    p = db.one("SELECT * FROM posts WHERE id=?", (post_id,))
    if not p or p["status"] not in ("need_image", "scheduled"):
        raise ValueError("Bài này không còn chờ ảnh")
    d = img_dir()
    d.mkdir(parents=True, exist_ok=True)
    f = d / f"post_{post_id}.{ext if ext in ('jpg', 'jpeg', 'png', 'webp') else 'jpg'}"
    f.write_bytes(data)
    when = p["scheduled_for"] or ""
    if when < db.clock().strftime("%Y-%m-%d %H:%M"):
        when = (db.clock() + timedelta(minutes=10)).strftime("%Y-%m-%d %H:%M")
    db.run("UPDATE posts SET image_path=?, status='scheduled', scheduled_for=? WHERE id=?", (str(f), when, post_id))
    db.log("nhi", "Nhận ảnh từ sếp", f"Bài #{post_id}: đã có ảnh, đăng lúc {when[11:16]} {when[8:10]}/{when[5:7]}")
    return db.one("SELECT * FROM posts WHERE id=?", (post_id,))


def on_telegram_photo(msg: dict, getter=None) -> str | None:
    """Bot Telegram nhận ảnh: tìm bài đang chờ (ưu tiên tin sếp trả lời), tải ảnh lớn nhất, gắn vào bài. Trả về câu báo lại."""
    import httpx
    import telegram_bot
    fid, ext = None, "jpg"
    if msg.get("photo"):
        fid = sorted(msg["photo"], key=lambda x: x.get("file_size") or x.get("width", 0))[-1]["file_id"]
    elif (msg.get("document") or {}).get("mime_type", "").startswith("image/"):
        fid, ext = msg["document"]["file_id"], msg["document"]["mime_type"].split("/")[-1]
    if not fid:
        return None
    reply_id = (msg.get("reply_to_message") or {}).get("message_id")
    p = _waiting_for(reply_id)
    if not p:
        return ("Tin sếp trả lời không phải tin xin ảnh đang chờ." if reply_id else "Hiện không có bài nào đang chờ ảnh.")
    if getter:  # ảnh gửi qua bot ảnh riêng
        data = getter(fid)
    else:
        info = telegram_bot.call("getFile", file_id=fid)
        data = httpx.get(f"{telegram_bot.API}/file/bot{telegram_bot.token()}/{info['file_path']}", timeout=60).content
    p = set_image(p["id"], data, ext)
    left = db.one("SELECT COUNT(*) n FROM posts WHERE status='need_image'")["n"]
    return (f"✅ Đã nhận ảnh cho bài #{p['id']}, đăng lúc {p['scheduled_for'][11:16]} {p['scheduled_for'][8:10]}/{p['scheduled_for'][5:7]}."
            + (f" Còn {left} bài chờ ảnh." if left else ""))


def plan_today(force: bool = False) -> int:
    """Mỗi sáng: mỗi Trang đang chạy viết đủ bài cho các giờ còn lại hôm nay (bài chờ ảnh quá 24 giờ thì bỏ)."""
    if not force and _s().get("trend_plan_day") == db.today():
        return 0
    db.set_setting("trend_plan_day", db.today())
    db.run("""UPDATE posts SET status='rejected', error='Không có ảnh sau 24 giờ' WHERE status='need_image' AND source='trend_page'
              AND created_at <= ?""", (_ago(hours=24),))
    now, n = db.clock().strftime("%H:%M"), 0
    for pg in db.q("SELECT * FROM fb_pages WHERE status='active' AND admin_account_id IS NOT NULL"):
        have = db.one("SELECT COUNT(*) n FROM posts WHERE fb_page_ref=? AND substr(scheduled_for,1,10)=?", (pg["id"], db.today()))["n"]
        slots = [t for t in (pg["times"] or "09:00,19:30").split(",")[:pg["posts_per_day"] or 1] if t > now]
        for t in slots[:max(0, (pg["posts_per_day"] or 1) - have)]:
            write_post(pg, f"{db.today()} {t}")
            n += 1
    if n:
        db.log("nhi", "Lên lịch bài Trang xu hướng", f"Viết {n} bài, đã gửi prompt ảnh lên Telegram")
    return n


def due_stats(aid: int) -> list[dict]:
    return db.q("""SELECT * FROM fb_pages WHERE status='active' AND admin_account_id=? AND COALESCE(stats_at,'') < ?""", (aid, db.today()))


def read_stats(page, pages: list[dict]):
    """Trong ca của nick quản trị: đọc người theo dõi từng Trang và tương tác 4 bài gần nhất (chỉ đọc)."""
    import browser_poster as B
    import page_grow as G
    for pg in pages:
        db.run("UPDATE fb_pages SET stats_at=? WHERE id=?", (db.now(), pg["id"]))
        try:
            page.goto(B.fb_url(pg["url"]), wait_until="domcontentloaded", timeout=60000)
            page.wait_for_timeout(3000)
            B._check_blocked(page)
            m = G.FOLLOW_RX.search(page.inner_text("body"))
            if m:
                db.run("UPDATE fb_pages SET followers=? WHERE id=?", (G.num(m.group(1)), pg["id"]))
            for p in db.q("""SELECT id, posted_url FROM posts WHERE fb_page_ref=? AND status='posted' AND posted_url LIKE 'http%'
                             ORDER BY posted_at DESC LIMIT 4""", (pg["id"],)):
                page.goto(B.fb_url(p["posted_url"]), wait_until="domcontentloaded", timeout=60000)
                page.wait_for_timeout(2500)
                body = page.inner_text("body")
                r, c, sh = G.REACT_RX.search(body), G.CMT_RX.search(body), G.SHARE_RX.search(body)
                db.run("UPDATE posts SET reactions=?, comments=MAX(COALESCE(comments,0), ?), shares=? WHERE id=?",
                       (G.num((r.group(1) or r.group(2)) if r else None) or 0, G.num(c.group(1)) if c else 0, G.num(sh.group(1)) if sh else 0, p["id"]))
                B._pause(page, 3, 8)
        except B.Blocked:
            raise
        except Exception as e:
            print("[trend stats]", e)


def overview() -> dict:
    import json
    st = _s()
    pages = db.q("""SELECT f.*, a.name admin_name FROM fb_pages f LEFT JOIN fb_accounts a ON a.id=f.admin_account_id
                    WHERE f.status != 'dismissed' ORDER BY CASE f.status WHEN 'active' THEN 0 WHEN 'idea' THEN 1 ELSE 2 END, f.id DESC""")
    for p in pages:
        if p["status"] == "active":
            r = db.one("""SELECT COUNT(*) n, AVG(COALESCE(reactions,0)+2*COALESCE(comments,0)+3*COALESCE(shares,0)) eng FROM posts
                          WHERE fb_page_ref=? AND status='posted' AND posted_at >= ?""", (p["id"], _ago(days=30)))
            p["posted_30d"], p["avg_eng"] = r["n"], round(r["eng"] or 0, 1)
    trends = db.q("SELECT title, traffic, traffic_n, news, day FROM trends WHERE day=? ORDER BY traffic_n DESC LIMIT 20", (db.today(),)) or \
        db.q("SELECT title, traffic, traffic_n, news, day FROM trends WHERE day=(SELECT MAX(day) FROM trends) ORDER BY traffic_n DESC LIMIT 20")
    for t in trends:
        t["news"] = json.loads(t["news"] or "[]")
    posts = db.q("""SELECT p.id, p.status, p.content, p.scheduled_for, p.posted_at, p.posted_url, p.image_prompt, p.image_note, p.image_path,
                           p.trend_topic, p.error, p.reactions, p.comments, p.shares, f.name page_name FROM posts p JOIN fb_pages f ON f.id=p.fb_page_ref
                    WHERE p.status IN ('need_image','scheduled','posting','failed') OR (p.status='posted' AND p.posted_at >= ?)
                    ORDER BY CASE p.status WHEN 'need_image' THEN 0 WHEN 'scheduled' THEN 1 WHEN 'failed' THEN 2 ELSE 3 END,
                             COALESCE(p.scheduled_for, p.posted_at) LIMIT 60""", (_ago(days=7),))
    import telegram_bot
    import telegram_img
    import trend_learn
    return {"learn": trend_learn.overview(), "pages": pages, "img_bot": telegram_img.status(), "trends": trends, "hot": db.q("SELECT * FROM trend_hot WHERE day=(SELECT MAX(day) FROM trend_hot) ORDER BY score DESC"),
            "posts": posts, "telegram": telegram_bot.configured() or telegram_img.configured(), "research_day": st.get("trend_research_day") or "",
            "nicks": db.q("""SELECT a.id, a.name, s.name sale_name FROM fb_accounts a JOIN sales s ON s.id=a.sale_id WHERE a.enabled=1
                             AND COALESCE(s.status,'active')!='fired' ORDER BY a.sale_id, a.id"""),
            "settings": {k: st.get(k, "") for k in ("trend_on", "trend_time")}}


def tick(now):
    st = _s()
    if st.get("trend_on", "1") != "1":
        return
    hm = now.strftime("%H:%M")
    import threading
    if hm >= (st.get("trend_time") or "07:40") and st.get("trend_research_day") != db.today() and st.get("trend_running") != db.today():
        db.set_setting("trend_running", db.today())

        def go():
            research()
            plan_today(force=True)
        threading.Thread(target=go, daemon=True).start()

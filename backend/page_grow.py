"""Nuôi Fanpage không dùng Graph API: nick quản trị Trang (một nick sale sếp chọn) mở Chrome, chuyển sang Trang, đăng bài, chuyển về.
Không dùng các nick sale khác like / share / theo dõi / bình luận Trang (hành vi không xác thực: Facebook giảm tiếp cận, khóa cả cụm).

1. Lịch nội dung: mỗi ngày Lan viết 1–3 bài cho Trang theo tỉ lệ 80/20: phần lớn là bài có ích cho người theo dõi (kiến thức
   nguyên liệu, cách pha, hậu trường xưởng, mẹo bán hàng online, hỏi đáp khách sỉ, câu hỏi ý kiến), khoảng 20% giới thiệu sản phẩm.
   Bài kèm ảnh, không ghi giá, qua Luật Facebook; đăng đúng giờ người xem đông (mặc định 08:30 và 20:30).
2. Học từ tương tác thật: mỗi ngày (ghép vào ca làm việc của nick quản trị, không mở Chrome riêng) đọc số người theo dõi Trang và
   cảm xúc / bình luận / chia sẻ các bài Trang 14 ngày; chủ đề tương tác cao được viết nhiều hơn (vẫn chừa 30% thử đều các chủ đề).
3. Bình luận dưới bài Trang: sale quét như bài khác để lấy khách (chỉ đọc, không trả lời dưới tên nick).
"""
import re
import random
from datetime import datetime, timedelta

import db

TOPICS = {
    "knowledge": ("Kiến thức nguyên liệu", "Chia sẻ một điều thú vị, dễ hiểu về nguyên liệu của sản phẩm (nguồn gốc, cách chọn, cách bảo quản)."),
    "recipe": ("Cách pha, công thức", "Một cách pha / công thức đơn giản với sản phẩm, viết thành 3–5 bước ngắn."),
    "factory": ("Hậu trường xưởng", "Kể ngắn một công đoạn thật ở xưởng (sơ chế, sấy, đóng gói, kiểm tra chất lượng) để người xem thấy xưởng làm thật."),
    "seller": ("Mẹo bán hàng online", "Một mẹo thiết thực cho người bán online (chụp ảnh sản phẩm, viết bài, livestream, chọn mặt hàng dễ bán)."),
    "faq": ("Hỏi đáp khách sỉ", "Trả lời một câu khách sỉ hay hỏi (nhập tối thiểu, gia công nhãn riêng, giao hàng, hạn dùng), chỉ dùng thông tin thật được đưa."),
    "poll": ("Hỏi ý kiến", "Một câu hỏi ngắn mời người theo dõi trả lời trong bình luận (VD chọn vị yêu thích, khách hay hỏi gì). Không ép like / share / tag."),
    "product": ("Giới thiệu sản phẩm", "Giới thiệu một sản phẩm cho người muốn nhập sỉ / bán lại, mời nhắn Trang hoặc Zalo, không ghi giá."),
}
SALE = "product"
EXPLORE = 0.3


def _s() -> dict:
    return db.get_settings()


def enabled_topics() -> list[str]:
    off = set((_s().get("page_grow_off") or "").split(","))
    return [k for k in TOPICS if k not in off] or [SALE]


def engagement(p: dict) -> int:
    return (p.get("reactions") or 0) + 2 * (p.get("comments") or 0) + 3 * (p.get("shares") or 0)


def topic_stats(days: int = 60) -> list[dict]:
    since = (db.clock() - timedelta(days=days)).strftime("%Y-%m-%d")
    rows = db.q("""SELECT page_topic t, COUNT(*) n, AVG(COALESCE(reactions,0) + 2*COALESCE(comments,0) + 3*COALESCE(shares,0)) eng,
                          SUM(COALESCE(leads,0)) leads FROM posts WHERE target_type='page' AND status='posted' AND page_topic IS NOT NULL
                          AND posted_at >= ? GROUP BY page_topic""", (since,))
    by = {r["t"]: r for r in rows}
    return [{"topic": k, "label": TOPICS[k][0], "n": (by.get(k) or {}).get("n") or 0, "eng": round((by.get(k) or {}).get("eng") or 0, 1),
             "leads": (by.get(k) or {}).get("leads") or 0, "on": k in enabled_topics()} for k in TOPICS]


def choose_topic(rnd: random.Random | None = None) -> str:
    """Bài bán hàng theo tỉ lệ (mặc định 20%); còn lại chọn chủ đề tương tác cao hơn, chừa 30% thử đều, không lặp chủ đề bài trước."""
    rnd = rnd or random.Random()
    on = enabled_topics()
    recent = [r["page_topic"] for r in db.q("""SELECT page_topic FROM posts WHERE target_type='page' AND page_topic IS NOT NULL
                                               ORDER BY id DESC LIMIT 10""")]
    pct = int(_s().get("page_grow_sale_pct") or 20) / 100
    if SALE in on and (recent.count(SALE) / max(1, len(recent)) < pct or on == [SALE]):
        return SALE
    pool = [k for k in on if k != SALE and (not recent or k != recent[0])] or [k for k in on if k != SALE] or [SALE]
    if rnd.random() < EXPLORE:
        return rnd.choice(pool)
    st = {r["topic"]: r for r in topic_stats()}
    avg = (sum(r["eng"] * r["n"] for r in st.values()) / max(1, sum(r["n"] for r in st.values()))) or 1
    w = [((st[k]["eng"] * st[k]["n"] + avg * 5) / (st[k]["n"] + 5)) for k in pool]  # làm mượt: chủ đề ít bài không bị coi là tốt / kém
    return rnd.choices(pool, weights=w)[0]


def _product(topic: str) -> dict | None:
    hot = db.q("SELECT * FROM products WHERE hot=1 ORDER BY RANDOM() LIMIT 1")
    if hot and (topic == SALE or random.random() < 0.5):
        return hot[0]
    return db.one("SELECT * FROM products WHERE COALESCE(is_sample,0)=0 ORDER BY RANDOM() LIMIT 1") or db.one("SELECT * FROM products ORDER BY RANDOM() LIMIT 1")


def _mock(topic: str, p: dict | None, st: dict) -> dict:
    name = (p or {}).get("name") or "trà túi lọc"
    zalo = st.get("price_zalo") or "0386992326"
    body = {
        "knowledge": f"🌿 Bạn có biết? Nguyên liệu làm {name} được chọn kỹ từ vùng trồng quen, sơ chế và sấy ở nhiệt độ vừa phải để giữ mùi vị tự nhiên.\nBảo quản nơi khô ráo, đậy kín sau khi mở để giữ hương lâu hơn.",
        "recipe": f"☕ Pha {name} ngon trong 3 bước:\n1. Tráng ấm / cốc bằng nước nóng\n2. Thả 1 túi, rót 150–200ml nước sôi để nguội bớt\n3. Đợi 3–5 phút, thêm chút mật ong nếu thích",
        "factory": f"🏭 Một buổi sáng ở xưởng: nguyên liệu {name} được sơ chế, sấy rồi đóng túi lọc, mỗi mẻ đều kiểm tra độ ẩm và mùi trước khi đóng thùng.",
        "seller": "📸 Mẹo nhỏ cho shop online: chụp sản phẩm cạnh ly trà đã pha, ánh sáng tự nhiên buổi sáng, khách dễ hình dung hơn và hỏi mua nhiều hơn.",
        "faq": f"❓ Khách sỉ hay hỏi: nhập ít có được không? Xưởng nhận đơn từ số lượng nhỏ cho shop mới bắt đầu, có nhận in nhãn riêng. Cần thông tin chi tiết nhắn Trang hoặc Zalo {zalo}.",
        "poll": f"💬 Shop mình bán vị nào chạy nhất: trà gừng, trà sen hay ngũ cốc? Bình luận cho xưởng biết để chuẩn bị hàng nhé!",
        "product": f"✨ {name} đang được nhiều shop online nhập về bán. Xưởng sản xuất trực tiếp, nhận sỉ và gia công nhãn riêng.\n💬 Giá vui lòng liên hệ trực tiếp Zalo {zalo}",
    }[topic]
    return {"content": body, "hashtags": "#mộctâm #tràtúilọc"}


def _prompt(topic: str, p: dict | None, st: dict) -> str:
    label, guide = TOPICS[topic]
    recent = db.q("SELECT content FROM posts WHERE target_type='page' ORDER BY id DESC LIMIT 8")
    import knowledge
    facts = ""
    try:
        facts = "\n".join("- " + (k.get("answer") or k.get("content") or "")[:160]
                           for k in knowledge.search("lan", f"{label} {(p or {}).get('name','')}", k=4))
    except Exception:
        pass
    return f"""Viết 1 bài cho FANPAGE của xưởng (nuôi Trang: bài có ích để người theo dõi đọc, bình luận, quay lại; không phải bài rao sỉ trong nhóm).
Chủ đề: {label}. {guide}
Sản phẩm liên quan: {(p or {}).get('name') or 'các sản phẩm của xưởng'}. {(p or {}).get('description') or ''} {(p or {}).get('selling_points') or ''}
{('Thông tin thật được dùng:' + chr(10) + facts) if facts else ''}
Yêu cầu: 60–150 chữ, giọng gần gũi, mở đầu bằng 1 câu gây chú ý, xuống dòng cho dễ đọc, 1–3 emoji.
Không ghi giá, không hứa chữa bệnh / giảm cân / công dụng như thuốc, không bịa số liệu hay lời khách, không kêu gọi like / share / tag để nhận quà.
{'Kết bằng lời mời nhắn Trang hoặc Zalo ' + (st.get('price_zalo') or '') + ' để nhận báo giá sỉ.' if topic == SALE else 'Không chèn quảng cáo bán sỉ; có thể kết bằng 1 câu hỏi mở để người đọc bình luận.'}
Đừng mở đầu giống các bài gần đây:
{chr(10).join('- ' + (r['content'] or '')[:70] for r in recent) or '(chưa có)'}
Trả về JSON: {{"content": "...", "hashtags": "2-3 hashtag"}}"""


def write(topic: str | None = None, when: str | None = None) -> dict:
    """Lan viết 1 bài nuôi Trang: kiểm Luật Facebook, bỏ giá; duyệt sẵn và xếp giờ (hoặc chờ duyệt nếu sếp bật)."""
    from agents import system_prompt
    import fb_policy
    import pricing
    from llm import llm
    st = _s()
    topic = topic if topic in TOPICS else choose_topic()
    p = _product(topic)
    data = None
    for _ in range(2):
        data = llm.json(system_prompt("lan", st), _prompt(topic, p, st), mock=lambda: _mock(topic, p, st), max_tokens=700, task="posts") or {}
        text = pricing.sanitize((data.get("content") or "").strip(), add_contact=topic == SALE)
        if text and not [i for i in fb_policy.check_text(text) if i["level"] == "high"]:
            break
        text = ""
    if not text:
        text = _mock(topic, p, st)["content"]
    review = st.get("page_grow_review") == "1"
    status, sched = ("draft", None) if review else ("scheduled", when or next_slot())
    adm = admin_account() or {}
    pid = db.run("""INSERT INTO posts(agent_id, product_id, target_type, angle, title, content, hashtags, status, scheduled_for, page_topic,
                    source, account_id, sale_id, created_at) VALUES ('lan', ?, 'page', ?, ?, ?, ?, ?, ?, ?, 'page_grow', ?, ?, ?)""",
                 (p["id"] if p else None, f"Nuôi Trang: {TOPICS[topic][0]}", f"{TOPICS[topic][0]} · {(p or {}).get('name') or 'Xưởng'}",
                  text, (data or {}).get("hashtags") or "", status, sched, topic, adm.get("id"), adm.get("sale_id"), db.now()))
    db.log("lan", "Viết bài nuôi Trang", f"Bài #{pid} ({TOPICS[topic][0]})" + (" chờ duyệt" if review else f", đăng lúc {sched[11:16]} {sched[8:10]}/{sched[5:7]}"))
    return db.one("SELECT * FROM posts WHERE id=?", (pid,))


def slots() -> list[str]:
    raw = [t.strip() for t in (_s().get("page_grow_times") or "08:30,20:30").split(",")]
    return sorted(t for t in raw if len(t) == 5 and t[2] == ":")[:3] or ["08:30", "20:30"]


def next_slot() -> str:
    """Giờ đăng trống gần nhất (mỗi giờ một bài, chỉ giờ còn ở phía trước)."""
    now = db.clock()
    taken = {r["scheduled_for"][:16] for r in db.q("""SELECT scheduled_for FROM posts WHERE target_type='page' AND scheduled_for IS NOT NULL
                                                      AND status IN ('scheduled','posted') AND scheduled_for >= ?""", (now.strftime("%Y-%m-%d"),))}
    for d in range(0, 8):
        day = (now + timedelta(days=d)).strftime("%Y-%m-%d")
        for t in slots():
            s = f"{day} {t}"
            if s > now.strftime("%Y-%m-%d %H:%M") and s not in taken:
                return s
    return (now + timedelta(minutes=30)).strftime("%Y-%m-%d %H:%M")


def plan_today(force: bool = False) -> int:
    """Mỗi sáng: viết đủ số bài nuôi Trang cho các giờ còn lại hôm nay (không viết bù giờ đã qua)."""
    st = _s()
    if not force and st.get("page_grow_planned") == db.today():
        return 0
    db.set_setting("page_grow_planned", db.today())
    per_day = max(0, min(3, int(st.get("page_grow_per_day") or 1)))
    today = db.today()
    have = db.one("""SELECT COUNT(*) n FROM posts WHERE target_type='page' AND page_topic IS NOT NULL
                     AND (substr(scheduled_for,1,10)=? OR (status='draft' AND substr(created_at,1,10)=?))""", (today, today))["n"]
    now = db.clock().strftime("%H:%M")
    free = [t for t in slots()[:per_day] if t > now]
    n = 0
    for t in free[:max(0, per_day - have)]:
        write(when=f"{today} {t}")
        n += 1
    return n


# ---------------------------------------------------------------- nick quản trị, số liệu đọc qua Chrome
def admin_account() -> dict | None:
    aid = _s().get("page_admin_account")
    if not aid:
        return None
    return db.one("SELECT * FROM fb_accounts WHERE id=? AND enabled=1", (aid,))


def ready() -> str | None:
    """None nếu đủ điều kiện nuôi Trang, không thì lý do."""
    st = _s()
    if not (st.get("page_url") or "").strip():
        return "Chưa điền link Trang"
    a = admin_account()
    if not a:
        return "Chưa chọn nick quản trị Trang (nick sale là quản trị viên / biên tập viên của Trang)"
    if a.get("login_status") != "ok":
        return "Nick quản trị Trang chưa đăng nhập"
    return None


def num(t: str | None) -> int | None:
    """'1,2K' → 1200, '3,4 N' → 3400, '1.234' → 1234, '2 Tr' → 2000000."""
    if not t:
        return None
    m = re.match(r"\s*([\d.,]+)\s*(k|n|nghìn|tr|triệu|m)?", t.strip(), re.I)
    if not m:
        return None
    n, unit = m.group(1), (m.group(2) or "").lower()
    if unit:
        v = float(n.replace(",", ".")) if n.count(",") + n.count(".") <= 1 else float(n.replace(".", "").replace(",", ""))
        return int(v * (1000000 if unit in ("tr", "triệu", "m") else 1000))
    return int(re.sub(r"[.,]", "", n) or 0)


FOLLOW_RX = re.compile(r"([\d.,]+\s*(?:K|N|nghìn|Tr|triệu|M)?)\s*(?:người theo dõi|followers)", re.I)
REACT_RX = re.compile(r"(?:Tất cả cảm xúc|All reactions)\s*:?\s*([\d.,]+\s*(?:K|N|M)?)|([\d.,]+\s*(?:K|N)?)\s*(?:lượt thích|cảm xúc|likes?|reactions)\b", re.I)
CMT_RX = re.compile(r"([\d.,]+\s*(?:K|N)?)\s*(?:bình luận|comments?)\b", re.I)
SHARE_RX = re.compile(r"([\d.,]+\s*(?:K|N)?)\s*(?:lượt chia sẻ|chia sẻ|shares?)\b", re.I)


def stats_due(aid: int) -> bool:
    a = admin_account()
    return bool(a and a["id"] == aid and _s().get("page_grow_on", "1") == "1" and (_s().get("page_grow_stats_at") or "")[:10] != db.today()
                and (_s().get("page_url") or "").strip())


def read_stats(page) -> dict:
    """Trong ca của nick quản trị (đang là nick cá nhân, chỉ đọc): số người theo dõi Trang và tương tác tối đa 6 bài Trang 14 ngày."""
    import browser_poster as B
    db.set_setting("page_grow_stats_at", db.now())
    out = {"followers": None, "posts": 0}
    page.goto(B.fb_url(_s()["page_url"]), wait_until="domcontentloaded", timeout=60000)
    page.wait_for_timeout(3000)
    B._check_blocked(page)
    m = FOLLOW_RX.search(page.inner_text("body"))
    if m:
        out["followers"] = num(m.group(1))
        db.run("""INSERT INTO page_stats(day, followers, created_at) VALUES (?,?,?)
                  ON CONFLICT(day) DO UPDATE SET followers=excluded.followers""", (db.today(), out["followers"], db.now()))
    since = (db.clock() - timedelta(days=14)).strftime("%Y-%m-%d")
    for p in db.q("""SELECT id, posted_url FROM posts WHERE target_type='page' AND status='posted' AND COALESCE(posted_url,'') LIKE 'http%'
                     AND posted_at >= ? ORDER BY posted_at DESC LIMIT 6""", (since,)):
        try:
            page.goto(B.fb_url(p["posted_url"]), wait_until="domcontentloaded", timeout=60000)
            page.wait_for_timeout(2500)
            body = page.inner_text("body")
            r, c, sh = REACT_RX.search(body), CMT_RX.search(body), SHARE_RX.search(body)
            db.run("UPDATE posts SET reactions=?, comments=MAX(COALESCE(comments,0), ?), shares=? WHERE id=?",
                   (num((r.group(1) or r.group(2)) if r else None) or 0, num(c.group(1)) if c else 0, num(sh.group(1)) if sh else 0, p["id"]))
            out["posts"] += 1
        except B.Blocked:
            raise
        except Exception as e:
            print("[page stats]", e)
        B._pause(page, 3, 8)
    db.log("lan", "Đọc số liệu Trang", f"Người theo dõi: {out['followers'] if out['followers'] is not None else 'chưa đọc được'}, "
           f"cập nhật tương tác {out['posts']} bài Trang")
    return out


def overview() -> dict:
    st = _s()
    trend = db.q("SELECT day, followers, fans FROM page_stats ORDER BY day DESC LIMIT 30")[::-1]
    f_now = trend[-1]["followers"] if trend else None
    wk = [t for t in trend if t["day"] <= (db.clock() - timedelta(days=7)).strftime("%Y-%m-%d")]
    upcoming = db.q("""SELECT id, title, content, page_topic, status, scheduled_for FROM posts WHERE target_type='page'
                       AND status IN ('scheduled','draft','approved') ORDER BY COALESCE(scheduled_for,'9'), id LIMIT 12""")
    since = (db.clock() - timedelta(days=30)).strftime("%Y-%m-%d")
    posted = db.q("""SELECT id, title, content, page_topic, posted_at, posted_url, reactions, comments, shares, leads FROM posts
                     WHERE target_type='page' AND status='posted' AND posted_at >= ? ORDER BY posted_at DESC LIMIT 40""", (since,))
    for p in posted:
        p["eng"] = engagement(p)
    return {"ready": ready(), "followers": f_now, "nicks": db.q("""SELECT a.id, a.name, s.name sale_name FROM fb_accounts a
            JOIN sales s ON s.id=a.sale_id WHERE a.enabled=1 AND COALESCE(s.status,'active')!='fired' ORDER BY a.sale_id, a.id"""), "followers_7d": (f_now - wk[-1]["followers"]) if (wk and f_now is not None
            and wk[-1]["followers"] is not None) else None, "trend": trend, "upcoming": upcoming,
            "posted": posted, "top": sorted(posted, key=lambda p: -p["eng"])[:5], "topics": topic_stats(),
            "avg_eng": round(sum(p["eng"] for p in posted) / len(posted), 1) if posted else None, "stats_at": st.get("page_grow_stats_at") or "",
            "settings": {k: st.get(k, "") for k in ("page_grow_on", "page_grow_per_day", "page_grow_times", "page_grow_sale_pct",
                                                     "page_grow_review", "page_grow_off", "page_url", "page_admin_account")}}


def skip(pid: int):
    db.run("UPDATE posts SET status='rejected', scheduled_for=NULL WHERE id=? AND target_type='page' AND status IN ('scheduled','draft','approved')", (pid,))


def tick(now: datetime):
    """Mỗi sáng (mặc định 07:30) Lan viết bài nuôi Trang cho các giờ còn lại hôm nay; nick quản trị đăng trong ca làm việc."""
    st = _s()
    if st.get("page_grow_on", "1") != "1" or ready():
        return
    if now.strftime("%H:%M") >= (st.get("page_grow_plan_time") or "07:30") and st.get("page_grow_planned") != db.today():
        import threading
        db.set_setting("page_grow_planned", db.today())
        threading.Thread(target=plan_today, kwargs={"force": True}, daemon=True).start()

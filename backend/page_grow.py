"""Nuôi Fanpage không dùng Graph API, NHIỀU Trang: mỗi Trang (bảng fb_pages, kind='grow') có link, nick quản trị, số bài/ngày, giờ đăng,
ngành nghề + từ khóa riêng. Nhi (hoặc Biên tập Trang phụ trách) viết; nick quản trị của Trang mở Chrome, chuyển sang Trang, đăng bài, chuyển về.
Không dùng các nick sale khác like / share / theo dõi / bình luận Trang (hành vi không xác thực: Facebook giảm tiếp cận, khóa cả cụm).

1. Lịch nội dung: mỗi ngày Nhi viết 1–3 bài cho từng Trang cho Trang theo tỉ lệ 80/20: phần lớn là bài có ích cho người theo dõi (kiến thức
   nguyên liệu, cách pha, hậu trường xưởng, mẹo bán hàng online, hỏi đáp khách sỉ, câu hỏi ý kiến), khoảng 20% giới thiệu sản phẩm.
   Bài kèm ảnh, không ghi giá, qua Luật Facebook; đăng đúng giờ người xem đông (mặc định 08:30 và 20:30).
2. Học từ tương tác thật: mỗi ngày (ghép vào ca làm việc của nick quản trị, trend_pages.read_stats) đọc số người theo dõi từng Trang và
   cảm xúc / bình luận / chia sẻ các bài Trang; chủ đề tương tác cao được viết nhiều hơn (vẫn chừa 30% thử đều các chủ đề).
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


GROW = "COALESCE(kind,'trend')='grow'"


def pages(active_only: bool = False) -> list[dict]:
    migrate()
    return db.q(f"SELECT * FROM fb_pages WHERE {GROW} AND status " + ("= 'active'" if active_only else "IN ('active','paused')") + " ORDER BY id")


def migrate():
    """Bản cũ chỉ nuôi 1 Trang (cài đặt page_url + page_admin_account): chuyển thành Trang đầu tiên trong danh sách, gắn bài cũ vào Trang đó."""
    st = _s()
    if st.get("page_grow_migrated") == "1":
        return
    db.set_setting("page_grow_migrated", "1")
    url = (st.get("page_url") or "").strip()
    if not url or db.one(f"SELECT id FROM fb_pages WHERE {GROW}"):
        return
    name = (st.get("company_name") or "").strip() or "Fanpage xưởng"
    pid = db.run(f"""INSERT INTO fb_pages(name, niche, url, admin_account_id, status, posts_per_day, times, kind, created_at, activated_at)
                    VALUES (?, ?, ?, ?, 'active', ?, ?, 'grow', ?, ?)""",
                 (name, "trà, ngũ cốc, nhận sỉ và gia công", url, int(st["page_admin_account"]) if (st.get("page_admin_account") or "").isdigit() else None,
                  max(1, min(3, int(st.get("page_grow_per_day") or 1))), st.get("page_grow_times") or "08:30,20:30", db.now(), db.now()))
    db.run("UPDATE posts SET fb_page_ref=? WHERE source='page_grow' AND fb_page_ref IS NULL", (pid,))
    for r in db.q("SELECT day, followers FROM page_stats WHERE followers IS NOT NULL"):
        db.run("INSERT OR IGNORE INTO page_followers(page_id, day, followers) VALUES (?,?,?)", (pid, r["day"], r["followers"]))


def add_page(name: str, url: str, admin_id, per_day=1, times: str = "08:30,20:30", niche: str = "", keywords: str = "") -> dict:
    import trend_pages
    import page_brain
    name = (name or "").strip()[:80]
    if not name:
        raise ValueError("Điền tên Trang")
    if db.one("SELECT id FROM fb_pages WHERE lower(name)=lower(?) AND status IN ('active','paused')", (name,)):
        raise ValueError("Đã có Trang tên này trong danh sách")
    if not str(admin_id or "").isdigit():
        raise ValueError("Chọn nick quản trị Trang (nick sale là quản trị viên / biên tập viên của Trang)")
    pid = db.run("INSERT INTO fb_pages(name, niche, status, kind, created_at, reason) VALUES (?, ?, 'paused', 'grow', ?, 'Sếp thêm')",
                 (name, (niche or "").strip()[:200], db.now()))
    try:
        trend_pages.activate(pid, url, int(admin_id), int(per_day or 1), times or "08:30,20:30")
    except ValueError:
        db.run("DELETE FROM fb_pages WHERE id=?", (pid,))
        raise
    if keywords:
        page_brain.update_page(pid, {"keywords": keywords})
    db.log("nhi", "Nhận nuôi Trang", f"Trang {name}: Nhi viết bài 80/20, nick quản trị đăng theo giờ")
    return db.one("SELECT * FROM fb_pages WHERE id=?", (pid,))


def topic_stats(days: int = 60, pid: int | None = None) -> list[dict]:
    since = (db.clock() - timedelta(days=days)).strftime("%Y-%m-%d")
    rows = db.q("""SELECT page_topic t, COUNT(*) n, AVG(COALESCE(reactions,0) + 2*COALESCE(comments,0) + 3*COALESCE(shares,0)) eng,
                          SUM(COALESCE(leads,0)) leads FROM posts WHERE source='page_grow' AND status='posted' AND page_topic IS NOT NULL
                          AND posted_at >= ?""" + (" AND fb_page_ref=?" if pid else "") + " GROUP BY page_topic", (since, pid) if pid else (since,))
    by = {r["t"]: r for r in rows}
    return [{"topic": k, "label": TOPICS[k][0], "n": (by.get(k) or {}).get("n") or 0, "eng": round((by.get(k) or {}).get("eng") or 0, 1),
             "leads": (by.get(k) or {}).get("leads") or 0, "on": k in enabled_topics()} for k in TOPICS]


def choose_topic(pg: dict, rnd: random.Random | None = None) -> str:
    """Bài bán hàng theo tỉ lệ (mặc định 20%) của từng Trang; còn lại chọn chủ đề tương tác cao hơn (số liệu của Trang, ít thì của mọi Trang),
    chừa 30% thử đều, không lặp chủ đề bài trước."""
    rnd = rnd or random.Random()
    on = enabled_topics()
    recent = [r["page_topic"] for r in db.q("""SELECT page_topic FROM posts WHERE source='page_grow' AND fb_page_ref=? AND page_topic IS NOT NULL
                                               AND status != 'rejected' ORDER BY id DESC LIMIT 10""", (pg["id"],))]
    pct = int(_s().get("page_grow_sale_pct") or 20) / 100
    if SALE in on and (recent.count(SALE) / max(1, len(recent)) < pct or on == [SALE]):
        return SALE
    pool = [k for k in on if k != SALE and (not recent or k != recent[0])] or [k for k in on if k != SALE] or [SALE]
    if rnd.random() < EXPLORE:
        return rnd.choice(pool)
    st = {r["topic"]: r for r in topic_stats(pid=pg["id"])}
    if sum(r["n"] for r in st.values()) < 10:
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
        "faq": f"❓ Khách sỉ hay hỏi: nhập ít có được không? Xưởng nhận đơn từ số lượng nhỏ cho shop mới bắt đầu, có nhận in nhãn riêng. Cần thông tin chi tiết cứ nhắn Trang nhé.",
        "poll": f"💬 Shop mình bán vị nào chạy nhất: trà gừng, trà sen hay ngũ cốc? Bình luận cho xưởng biết để chuẩn bị hàng nhé!",
        "product": f"✨ {name} đang được nhiều shop online nhập về bán. Xưởng sản xuất trực tiếp, nhận sỉ và gia công nhãn riêng.\n💬 Giá vui lòng liên hệ trực tiếp Zalo {zalo}",
    }[topic]
    return {"content": body, "hashtags": "#mộctâm #tràtúilọc"}


def _prompt(pg: dict, topic: str, p: dict | None, st: dict) -> str:
    label, guide = TOPICS[topic]
    recent = db.q("SELECT content FROM posts WHERE fb_page_ref=? ORDER BY id DESC LIMIT 8", (pg["id"],))
    import knowledge
    facts = ""
    try:
        facts = "\n".join("- " + (k.get("answer") or k.get("content") or "")[:160]
                           for k in knowledge.search("lan", f"{label} {(p or {}).get('name','')}", k=4))
    except Exception:
        pass
    return f"""Viết 1 bài cho FANPAGE "{pg['name']}" của xưởng (nuôi Trang: bài có ích để người theo dõi đọc, bình luận, quay lại; không phải bài rao sỉ trong nhóm).
Chủ đề: {label}. {guide}
Sản phẩm liên quan: {(p or {}).get('name') or 'các sản phẩm của xưởng'}. {(p or {}).get('description') or ''} {(p or {}).get('selling_points') or ''}
{('Thông tin thật được dùng:' + chr(10) + facts) if facts else ''}
Yêu cầu: 60–150 chữ, giọng gần gũi, mở đầu bằng 1 câu gây chú ý, xuống dòng cho dễ đọc, 1–3 emoji.
Không ghi giá, không hứa chữa bệnh / giảm cân / công dụng như thuốc, không bịa số liệu hay lời khách, không kêu gọi like / share / tag để nhận quà.
{'Kết bằng lời mời nhắn Trang hoặc Zalo ' + (st.get('price_zalo') or '') + ' để nhận báo giá sỉ.' if topic == SALE else 'Không chèn quảng cáo bán sỉ; có thể kết bằng 1 câu hỏi mở để người đọc bình luận.'}
Đừng mở đầu giống các bài gần đây:
{chr(10).join('- ' + (r['content'] or '')[:70] for r in recent) or '(chưa có)'}
Trả về JSON: {{"content": "...", "hashtags": "2-3 hashtag"}}"""


def _page(pg) -> dict | None:
    if isinstance(pg, dict):
        return pg
    if pg:
        return db.one("SELECT * FROM fb_pages WHERE id=?", (pg,))
    return next((x for x in pages(True) if not ready(x)), None) or next(iter(pages(True)), None)


def write(pg=None, topic: str | None = None, when: str | None = None) -> dict:
    """Nhi viết 1 bài nuôi Trang: theo ngành nghề, từ khóa, điều Nhi ghi nhớ của Trang; kiểm Luật Facebook, bỏ giá;
    chờ sếp duyệt (mục Các Trang của Nhi) hoặc xếp giờ luôn."""
    from agents import system_prompt
    import fb_policy
    import pricing
    import page_brain
    import departments
    from llm import llm
    pg = _page(pg)
    if not pg:
        raise ValueError("Chưa có Trang nào để nuôi: bấm Thêm Trang")
    st = _s()
    topic = topic if topic in TOPICS else choose_topic(pg)
    p = _product(topic)
    kw = page_brain.pick_keyword(pg)
    writer = departments.writer_for_page(pg["id"])
    ask = _prompt(pg, topic, p, st) + "\n" + page_brain.brief(pg, kw)
    data, text = None, ""
    for _ in range(2):
        data = llm.json(system_prompt(writer, st), ask, mock=lambda: _mock(topic, p, st), max_tokens=700, task="posts") or {}
        text = pricing.sanitize((data.get("content") or "").strip(), add_contact=topic == SALE)
        if text and not [i for i in fb_policy.check_text(text) if i["level"] == "high"]:
            break
        text = ""
    if not text:
        text = _mock(topic, p, st)["content"]
    review = page_brain.review_on()
    sched = when or next_slot(pg)
    adm = admin_account(pg) or {}
    pid = db.run("""INSERT INTO posts(agent_id, product_id, target_type, angle, title, content, hashtags, status, scheduled_for, page_topic,
                    source, account_id, sale_id, fb_page_ref, page_kw, nhi_draft, created_at) VALUES (?, ?, 'page', ?, ?, ?, ?, ?, ?, ?, 'page_grow', ?, ?, ?, ?, ?, ?)""",
                 (writer, p["id"] if p else None, f"Nuôi Trang: {TOPICS[topic][0]}", f"{pg['name']} · {TOPICS[topic][0]}"[:120],
                  text, (data or {}).get("hashtags") or "", "page_review" if review else "scheduled", sched, topic, adm.get("id"), adm.get("sale_id"),
                  pg["id"], kw, text, db.now()))
    if review:
        import nhi_tg
        nhi_tg.send_review(pid)
    db.log(writer, "Viết bài nuôi Trang", f"{pg['name']} · bài #{pid} ({TOPICS[topic][0]})" + (" chờ sếp duyệt" if review else f", đăng lúc {sched[11:16]} {sched[8:10]}/{sched[5:7]}"))
    return db.one("SELECT * FROM posts WHERE id=?", (pid,))


def slots(pg: dict) -> list[str]:
    raw = [t.strip() for t in (pg.get("times") or "08:30,20:30").split(",")]
    return sorted(t for t in raw if len(t) == 5 and t[2] == ":")[:3] or ["08:30", "20:30"]


def next_slot(pg: dict) -> str:
    """Giờ đăng trống gần nhất của Trang (mỗi giờ một bài, chỉ giờ còn ở phía trước)."""
    now = db.clock()
    taken = {r["scheduled_for"][:16] for r in db.q("""SELECT scheduled_for FROM posts WHERE fb_page_ref=? AND scheduled_for IS NOT NULL
                                                      AND status IN ('scheduled','posted','page_review') AND scheduled_for >= ?""", (pg["id"], now.strftime("%Y-%m-%d")))}
    for d in range(0, 8):
        day = (now + timedelta(days=d)).strftime("%Y-%m-%d")
        for t in slots(pg):
            s = f"{day} {t}"
            if s > now.strftime("%Y-%m-%d %H:%M") and s not in taken:
                return s
    return (now + timedelta(minutes=30)).strftime("%Y-%m-%d %H:%M")


def plan_today(force: bool = False) -> int:
    """Mỗi sáng: viết đủ số bài cho các giờ còn lại hôm nay của từng Trang đang nuôi (không viết bù giờ đã qua)."""
    st = _s()
    if not force and st.get("page_grow_planned") == db.today():
        return 0
    db.set_setting("page_grow_planned", db.today())
    import nhi_tg
    today, now, n = db.today(), db.clock().strftime("%H:%M"), 0
    for pg in pages(True):
        if ready(pg):
            continue
        pg = nhi_tg.auto_keywords(pg)
        per_day = max(1, min(3, int(pg.get("posts_per_day") or 1)))
        have = db.one("""SELECT COUNT(*) n FROM posts WHERE fb_page_ref=? AND status != 'rejected' AND substr(scheduled_for,1,10)=?""", (pg["id"], today))["n"]
        for t in [t for t in slots(pg)[:per_day] if t > now][:max(0, per_day - have)]:
            write(pg, when=f"{today} {t}")
            n += 1
    if n:
        import page_brain
        db.log("nhi", "Lên lịch nuôi Trang", f"Viết {n} bài cho các Trang" + (", chờ sếp duyệt" if page_brain.review_on() else ""))
        if page_brain.review_on():
            nhi_tg.batch_notice(n)
            nhi_tg.maybe_ask_off()
    return n


# ---------------------------------------------------------------- nick quản trị; số liệu đọc ở trend_pages.read_stats (mọi Trang)
def admin_account(pg=None) -> dict | None:
    pg = _page(pg)
    if not pg or not pg.get("admin_account_id"):
        return None
    return db.one("SELECT * FROM fb_accounts WHERE id=? AND enabled=1", (pg["admin_account_id"],))


def ready(pg=None) -> str | None:
    """None nếu Trang (hoặc ít nhất một Trang) đủ điều kiện nuôi, không thì lý do."""
    if pg is None:
        ps = pages(True)
        if not ps:
            return "Chưa có Trang nào: bấm Thêm Trang, dán link và chọn nick quản trị"
        why = [ready(x) for x in ps]
        return None if any(w is None for w in why) else why[0]
    if not (pg.get("url") or "").strip():
        return f"Trang {pg['name']} chưa có link"
    a = admin_account(pg)
    if not a:
        return f"Trang {pg['name']} chưa chọn nick quản trị (nick sale là quản trị viên / biên tập viên của Trang)"
    if a.get("login_status") != "ok":
        return f"Nick quản trị Trang {pg['name']} chưa đăng nhập"
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
    return False  # số liệu mọi Trang (cả Trang nuôi) đọc ở trend_pages.due_stats / read_stats


def followers_7d(pid: int, now_f: int | None) -> int | None:
    old = db.one("SELECT followers FROM page_followers WHERE page_id=? AND day <= ? ORDER BY day DESC LIMIT 1",
                 (pid, (db.clock() - timedelta(days=7)).strftime("%Y-%m-%d")))
    return (now_f - old["followers"]) if (old and old["followers"] is not None and now_f is not None) else None


def overview() -> dict:
    st = _s()
    ps = pages()
    for p in ps:
        p["ready"] = ready(p) if p["status"] == "active" else None
        p["followers_7d"] = followers_7d(p["id"], p.get("followers"))
        a = admin_account(p)
        p["admin_name"] = a["name"] if a else None
    upcoming = db.q("""SELECT p.id, p.title, p.content, p.page_topic, p.status, p.scheduled_for, f.name page_name FROM posts p JOIN fb_pages f ON f.id=p.fb_page_ref
                       WHERE p.source='page_grow' AND p.status IN ('scheduled','page_review','draft','approved') ORDER BY COALESCE(p.scheduled_for,'9'), p.id LIMIT 30""")
    since = (db.clock() - timedelta(days=30)).strftime("%Y-%m-%d")
    posted = db.q("""SELECT p.id, p.title, p.content, p.page_topic, p.posted_at, p.posted_url, p.reactions, p.comments, p.shares, p.leads, f.name page_name
                     FROM posts p LEFT JOIN fb_pages f ON f.id=p.fb_page_ref WHERE p.source='page_grow' AND p.status='posted' AND p.posted_at >= ?
                     ORDER BY p.posted_at DESC LIMIT 60""", (since,))
    for p in posted:
        p["eng"] = engagement(p)
    fol = [p["followers"] for p in ps if p.get("followers") is not None]
    f7 = [p["followers_7d"] for p in ps if p["followers_7d"] is not None]
    return {"ready": ready(), "pages": ps, "followers": sum(fol) if fol else None, "followers_7d": sum(f7) if f7 else None,
            "nicks": db.q("""SELECT a.id, a.name, s.name sale_name FROM fb_accounts a JOIN sales s ON s.id=a.sale_id WHERE a.enabled=1
                             AND COALESCE(s.status,'active')!='fired' ORDER BY a.sale_id, a.id"""),
            "upcoming": upcoming, "posted": posted, "top": sorted(posted, key=lambda p: -p["eng"])[:5], "topics": topic_stats(),
            "avg_eng": round(sum(p["eng"] for p in posted) / len(posted), 1) if posted else None,
            "stats_at": max([p.get("stats_at") or "" for p in ps] or [""]), "review": st.get("trend_review", "1") == "1",
            "settings": {k: st.get(k, "") for k in ("page_grow_on", "page_grow_sale_pct", "page_grow_off")}}


def skip(pid: int):
    db.run("UPDATE posts SET status='rejected', scheduled_for=NULL WHERE id=? AND source='page_grow' AND status IN ('scheduled','draft','approved','page_review')", (pid,))


def tick(now: datetime):
    """Mỗi sáng (mặc định 07:30) Nhi viết bài nuôi Trang cho các giờ còn lại hôm nay của từng Trang; nick quản trị đăng trong ca làm việc."""
    st = _s()
    if st.get("page_grow_on", "1") != "1" or ready():
        return
    if now.strftime("%H:%M") >= (st.get("page_grow_plan_time") or "07:30") and st.get("page_grow_planned") != db.today():
        import threading
        db.set_setting("page_grow_planned", db.today())
        threading.Thread(target=plan_today, kwargs={"force": True}, daemon=True).start()

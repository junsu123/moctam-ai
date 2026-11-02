"""KPI phòng kinh doanh và chuyển khách cho sếp.

KPI chính: số khách MỚI có số điện thoại trong ngày (mặc định tối thiểu 5, vượt 10).
Chia đều KPI cho các nick sale đang chạy. Khách được tính cho nick đã đăng bài nguồn.

Chuyển khách cho sếp (qua Telegram) khi:
- khách đã để SĐT (AI không gọi điện / nhắn Zalo được) — bật/tắt trong cài đặt;
- khách hỏi vượt khả năng của AI: số lượng lớn, in nhãn riêng, chiết khấu, đại lý, khiếu nại, hóa đơn…;
- khách mới quá N giờ mà chưa ai tư vấn.
Mỗi phiếu chuyển có kịch bản tư vấn do Hà soạn sẵn.
"""
import json
import re
import unicodedata
from datetime import datetime, timedelta

import db

PHONE_RX = re.compile(r"(?<!\d)(?:\+?84|0)(?:[\s.\-]?\d){9}(?!\d)")
INTEREST_RX = re.compile(r"\b(quan tâm|qt|ib|inbox|check ib|xin giá|báo giá|giá sỉ|giá|lấy sỉ|nhập|đặt|cần|tư vấn|bao nhiêu|zalo|sđt|sdt|liên hệ|mua)\b", re.I)
COMPLEX_RX = re.compile(
    r"(oem|in nhãn|nhãn riêng|thương hiệu riêng|gia công|đại lý|độc quyền|phân phối|chiết khấu|giảm giá|"
    r"hóa đơn|hoá đơn|vat|kiểm nghiệm|giấy phép|công bố|khiếu nại|lỗi|hỏng|đổi trả|hoàn tiền|"
    r"\b\d{3,}\s*(hộp|hũ|túi|gói|cái|sp)|\b\d+\s*(thùng|tấn|kg)\b|số lượng lớn|container)", re.I)


def norm_phone(text: str) -> str | None:
    m = PHONE_RX.search(text or "")
    if not m:
        return None
    d = re.sub(r"\D", "", m.group(0))
    if d.startswith("84"):
        d = "0" + d[2:]
    return d if len(d) == 10 and d[1] in "35789" else None


def is_interested(text: str) -> bool:
    return bool(INTEREST_RX.search(text or "")) or bool(norm_phone(text))


def fmt_phone(p: str | None) -> str:
    return f"{p[:4]} {p[4:7]} {p[7:]}" if p and len(p) == 10 else (p or "")


def _today() -> str:
    return db.today()


# ---------------------------------------------------------------- KPI
def targets() -> tuple[int, int]:
    s = db.get_settings()
    mn = max(1, int(s.get("kpi_min") or 5))
    return mn, max(mn, int(s.get("kpi_max") or 10))


def day_stats(day: str | None = None) -> dict:
    d = (day or _today()) + "%"
    one = lambda sql, p=(): db.one(sql, p)["n"] or 0
    mn, mx = targets()
    phone = one("SELECT COUNT(*) n FROM leads WHERE phone IS NOT NULL AND phone!='' AND COALESCE(phone_at, created_at) LIKE ?", (d,))
    st = {
        "date": day or _today(), "target_min": mn, "target_max": mx,
        "leads_phone": phone,
        "leads_total": one("SELECT COUNT(*) n FROM leads WHERE created_at LIKE ?", (d,)),
        "leads_no_phone": one("SELECT COUNT(*) n FROM leads WHERE created_at LIKE ? AND (phone IS NULL OR phone='')", (d,)),
        "from_comments": one("SELECT COUNT(*) n FROM leads WHERE created_at LIKE ? AND origin='comment'", (d,)),
        "asked_phone": one("SELECT COUNT(*) n FROM comment_seen WHERE replied=1 AND created_at LIKE ?", (d,)),
        "posts": one("SELECT COUNT(*) n FROM posts WHERE status='posted' AND posted_at LIKE ?", (d,)),
        "bumps": one("SELECT COUNT(*) n FROM bumps WHERE status='done' AND done_at LIKE ?", (d,)),
        "escalated": one("SELECT COUNT(*) n FROM leads WHERE escalated_at LIKE ?", (d,)),
        "boss_pending": one("SELECT COUNT(*) n FROM leads WHERE escalated_at IS NOT NULL AND COALESCE(boss_status,'') IN ('','remind') AND status NOT IN ('ordered','lost')"),
        "ordered": one("SELECT COUNT(*) n FROM leads WHERE status='ordered' AND updated_at LIKE ?", (d,)),
    }
    st["achieved"] = phone >= mn
    st["exceeded"] = phone >= mx
    st["pct"] = round(100 * phone / mn) if mn else 0
    return st


def pace(st: dict | None = None) -> dict:
    """Đang đúng tiến độ không: so với phần ngày làm việc đã trôi qua (08:00–22:00)."""
    st = st or day_stats()
    now = datetime.now()
    start, end = now.replace(hour=8, minute=0), now.replace(hour=22, minute=0)
    frac = min(1, max(0, (now - start).total_seconds() / (end - start).total_seconds()))
    expected = round(st["target_min"] * frac, 1)
    return {"expected": expected, "behind": st["leads_phone"] + 0.5 < expected and frac > 0.2, "frac": round(frac, 2)}


def per_sale(day: str | None = None) -> list[dict]:
    d = (day or _today()) + "%"
    sales = db.q("SELECT id, name, fb_name, login_status, auto_post FROM sales ORDER BY id")
    active = [s for s in sales if s["login_status"] == "ok" and s["auto_post"]] or sales
    mn, mx = targets()
    share = lambda t: max(1, round(t / max(1, len(active))))
    out = []
    for s in sales:
        q = lambda sql: db.one(sql, (s["id"], d))["n"] or 0
        out.append({
            "id": s["id"], "name": s["name"], "fb_name": s["fb_name"], "active": s in active,
            "target_min": share(mn) if s in active else 0, "target_max": share(mx) if s in active else 0,
            "leads_phone": q("""SELECT COUNT(*) n FROM leads l JOIN posts p ON p.id=l.post_id WHERE p.sale_id=?
                               AND l.phone IS NOT NULL AND l.phone!='' AND COALESCE(l.phone_at, l.created_at) LIKE ?"""),
            "leads": q("SELECT COUNT(*) n FROM leads l JOIN posts p ON p.id=l.post_id WHERE p.sale_id=? AND l.created_at LIKE ?"),
            "posts": q("SELECT COUNT(*) n FROM posts WHERE sale_id=? AND status='posted' AND posted_at LIKE ?"),
            "bumps": q("SELECT COUNT(*) n FROM bumps WHERE sale_id=? AND status='done' AND done_at LIKE ?"),
            "asked": q("SELECT COUNT(*) n FROM comment_seen WHERE sale_id=? AND replied=1 AND created_at LIKE ?"),
            "failed": q("SELECT COUNT(*) n FROM posts WHERE sale_id=? AND status='failed' AND COALESCE(posted_at, scheduled_for) LIKE ?"),
        })
    return out


def snapshot(day: str | None = None):
    st = day_stats(day)
    db.run("""INSERT INTO kpi_daily(date, target_min, target_max, leads_phone, leads_total, posts, bumps, escalated, achieved, detail, created_at)
              VALUES (?,?,?,?,?,?,?,?,?,?,?) ON CONFLICT(date) DO UPDATE SET leads_phone=excluded.leads_phone,
              leads_total=excluded.leads_total, posts=excluded.posts, bumps=excluded.bumps, escalated=excluded.escalated,
              achieved=excluded.achieved, detail=excluded.detail, target_min=excluded.target_min, target_max=excluded.target_max""",
           (st["date"], st["target_min"], st["target_max"], st["leads_phone"], st["leads_total"], st["posts"], st["bumps"],
            st["escalated"], int(st["achieved"]), db.dumps(per_sale(day)), db.now()))
    return st


def history(days: int = 14) -> list[dict]:
    out = []
    for i in range(days - 1, -1, -1):
        d = (datetime.now() - timedelta(days=i)).strftime("%Y-%m-%d")
        r = db.one("SELECT * FROM kpi_daily WHERE date=?", (d,)) if i else None
        if not r:
            s = day_stats(d)
            r = {"date": d, "target_min": s["target_min"], "target_max": s["target_max"], "leads_phone": s["leads_phone"],
                 "leads_total": s["leads_total"], "achieved": int(s["achieved"])}
        out.append({k: r[k] for k in ("date", "target_min", "target_max", "leads_phone", "leads_total", "achieved")})
    return out


def streak() -> int:
    n = 0
    for r in reversed(history(30)[:-1]):
        if r["achieved"]:
            n += 1
        else:
            break
    return n


# ---------------------------------------------------------------- khách hàng
def upsert_lead(name: str, text: str, post_id: int | None, author: str | None = None, origin: str = "comment",
                phone: str | None = None) -> tuple[int, bool, bool]:
    """Tạo hoặc cập nhật khách từ bình luận. Trả về (lead_id, mới_tạo, vừa_có_SĐT)."""
    import learning
    import workflows
    phone = phone or norm_phone(text)
    lead = None
    if phone:
        lead = db.one("SELECT * FROM leads WHERE phone=?", (phone,))
    if not lead and author and post_id:
        lead = db.one("SELECT * FROM leads WHERE fb_author=? AND post_id=?", (author, post_id))
    if lead:
        got_phone = bool(phone and not lead.get("phone"))
        if got_phone:
            db.run("UPDATE leads SET phone=?, phone_at=?, need=?, updated_at=? WHERE id=?",
                   (phone, db.now(), ((lead["need"] or "") + " | " + text)[:300], db.now(), lead["id"]))
            db.log("ha", "Khách để lại SĐT", f"{lead['name']}: {fmt_phone(phone)}")
            learning.award("ha", 10, "Xin được số điện thoại khách")
        return lead["id"], False, got_phone
    post = db.one("""SELECT p.id, p.sale_id, g.name gname FROM posts p LEFT JOIN groups g ON g.id=p.group_id WHERE p.id=?""",
                  (post_id,)) if post_id else None
    src = f"Bình luận bài #{post_id} · {post['gname'] or 'Trang cá nhân'}" if post else "Bình luận Facebook"
    data = {"need": text[:300], "business_type": ""}
    score = workflows.score_lead(data) + (20 if phone else 0)
    lid = db.run("""INSERT INTO leads(name, contact, channel, source, business_type, need, score, status, post_id, phone, phone_at,
                    origin, fb_author, created_at, updated_at) VALUES (?,?,?,?,?,?,?,'new',?,?,?,?,?,?,?)""",
                 (name[:80], fmt_phone(phone) if phone else "Bình luận Facebook", "Facebook", src, "", text[:300], min(100, score),
                  post_id, phone, db.now() if phone else None, origin, author, db.now(), db.now()))
    if post:
        db.run("UPDATE posts SET leads=COALESCE(leads,0)+1 WHERE id=?", (post_id,))
        db.run("UPDATE groups SET leads_count=(SELECT COALESCE(SUM(leads),0) FROM posts WHERE group_id=groups.id)")
        learning.on_post_leads(post_id, 1)
        if phone and post.get("sale_id"):
            learning.award(f"sale-{post['sale_id']}", 10, "Khách để lại SĐT")
    db.log(f"sale-{post['sale_id']}" if post and post.get("sale_id") else "ha", "Khách mới từ bình luận",
           f"{name}{' · ' + fmt_phone(phone) if phone else ' (chưa có SĐT)'}: {text[:80]}")
    return lid, True, bool(phone)


def escalate_reason(lead: dict) -> str | None:
    s = db.get_settings()
    text = f"{lead.get('need', '')} {lead.get('note', '')}"
    if s.get("escalate_complex") == "1" and COMPLEX_RX.search(text):
        return "Khách hỏi vượt khả năng của AI (" + COMPLEX_RX.search(text).group(0)[:30] + ")"
    if s.get("escalate_all_phone") == "1" and lead.get("phone"):
        return "Khách đã để lại SĐT, cần người gọi/nhắn Zalo tư vấn"
    hrs = float(s.get("escalate_after_hours") or 0)
    if hrs > 0 and lead.get("status") == "new" and lead.get("phone"):
        created = datetime.strptime(lead["created_at"][:19], "%Y-%m-%d %H:%M:%S")
        if datetime.now() - created > timedelta(hours=hrs):
            return f"Khách có SĐT nhưng {hrs:g} giờ chưa ai tư vấn"
    return None


def consult_note(lead: dict) -> str:
    """Hà soạn kịch bản tư vấn ngắn cho sếp (Haiku, ~0,0003 USD/khách)."""
    from agents import system_prompt
    from llm import llm
    products = db.q("SELECT name, wholesale_price, retail_price, moq FROM products")
    post = db.one("SELECT p.title, pr.name pname FROM posts p LEFT JOIN products pr ON pr.id=p.product_id WHERE p.id=?",
                  (lead.get("post_id"),)) if lead.get("post_id") else None
    def mock():
        p = next((x for x in products if post and post.get("pname") == x["name"]), products[0] if products else None)
        if not p:
            return "Hỏi khách đang bán kênh nào, số lượng dự kiến, rồi gửi bảng giá sỉ."
        return (f"Chào anh/chị, em gọi từ xưởng về {p['name']} anh/chị quan tâm. "
                f"Giá sỉ {p['wholesale_price']}, bán lẻ gợi ý {p['retail_price']}, nhập tối thiểu {p['moq']}. "
                "Hỏi: đang bán kênh nào (live/ads/sàn), dự kiến nhập bao nhiêu? Đề nghị gửi mẫu thử và ảnh/video để đăng bán.")
    prompt = f"""Sếp sắp gọi điện cho khách sỉ này. Soạn kịch bản ngắn (dưới 70 chữ) gồm: câu mở đầu, báo giá sản phẩm khách quan tâm,
2 câu hỏi để hiểu nhu cầu, 1 đề nghị chốt (gửi mẫu/ưu đãi đơn đầu nếu hợp lý). Không bịa chính sách.
Khách: {lead.get('name')} | Bình luận/nhu cầu: {lead.get('need')} | Bài nguồn: {(post or {}).get('title') or ''} ({(post or {}).get('pname') or ''})
Sản phẩm: {products}"""
    return llm.chat(system_prompt("ha", db.get_settings()), prompt, mock=mock, max_tokens=260, task="replies")


def escalate(lead_id: int, reason: str | None = None, force: bool = False) -> bool:
    lead = db.one("SELECT * FROM leads WHERE id=?", (lead_id,))
    if not lead or (lead.get("escalated_at") and not force) or lead["status"] in ("ordered", "lost"):
        return False
    reason = reason or escalate_reason(lead)
    if not reason and not force:
        return False
    note = lead.get("consult_note") or consult_note(lead)
    db.run("UPDATE leads SET escalated_at=?, escalate_reason=?, consult_note=?, boss_status='' WHERE id=?",
           (db.now(), reason or "Sếp chọn tự tư vấn", note, lead_id))
    db.log("ha", "Chuyển khách cho sếp", f"{lead['name']} · {reason or 'Sếp chọn tự tư vấn'}")
    try:
        import telegram_bot
        telegram_bot.send_lead(lead_id)
    except Exception as e:
        print("[telegram]", e)
    return True


def check_escalations():
    """Gọi định kỳ: khách nào cần sếp thì chuyển, khách hẹn nhắc lại thì nhắc."""
    for l in db.q("SELECT * FROM leads WHERE escalated_at IS NULL AND status NOT IN ('ordered','lost') AND created_at >= ?",
                  ((datetime.now() - timedelta(days=3)).strftime("%Y-%m-%d %H:%M:%S"),)):
        r = escalate_reason(l)
        if r:
            escalate(l["id"], r)
    for l in db.q("SELECT id FROM leads WHERE boss_status='remind' AND remind_at IS NOT NULL AND remind_at <= ?", (db.now(),)):
        db.run("UPDATE leads SET remind_at=NULL WHERE id=?", (l["id"],))
        try:
            import telegram_bot
            telegram_bot.send_lead(l["id"], reminder=True)
        except Exception as e:
            print("[telegram]", e)

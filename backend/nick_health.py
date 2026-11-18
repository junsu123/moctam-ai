"""Sức khỏe từng nick: gom các dấu hiệu rủi ro 30 ngày thành điểm 0–100 (100 = khỏe).

Dấu hiệu (trừ điểm): bị Facebook chặn / checkpoint, bài bị gỡ, bình luận up bài bị nhóm xóa, bình luận trả lời / chào bị xóa,
bài đăng lỗi, tỷ lệ đồng ý kết bạn thấp, đang mất đăng nhập. Nick "Cần để ý" (50–79) tự chạy 75% trần Luật Facebook,
"Nguy hiểm" (dưới 50) chạy 50% (fb_policy.factor), để giảm việc trước khi bị khóa; sếp tắt được. Rơi xuống Nguy hiểm thì báo Telegram.
"""
import time
from datetime import timedelta

import db

LEVELS = (("good", 80, "Khỏe"), ("warn", 50, "Cần để ý"), ("bad", 0, "Nguy hiểm"))
FACTOR = {"good": 1.0, "warn": 0.75, "bad": 0.5}
_cache: dict = {}
TTL = 600


def _ago(days: int) -> str:
    return (db.clock() - timedelta(days=days)).strftime("%Y-%m-%d %H:%M:%S")


def _n(sql: str, args) -> int:
    return (db.one(sql, args) or {}).get("n") or 0


def compute(acc: dict) -> dict:
    """Điểm, mức, các dấu hiệu (kèm điểm trừ) và việc nên làm của một nick."""
    aid, d30, d7 = acc["id"], _ago(30), _ago(7)
    sig = []  # (mã, điểm trừ, mô tả)
    b7 = _n("SELECT COUNT(*) n FROM fb_incidents WHERE account_id=? AND kind='block' AND created_at >= ?", (aid, d7))
    b30 = _n("SELECT COUNT(*) n FROM fb_incidents WHERE account_id=? AND kind='block' AND created_at >= ?", (aid, d30)) - b7
    if b7:
        sig.append(("block", 35 * b7, f"Bị Facebook chặn / checkpoint {b7} lần trong 7 ngày"))
    if b30 > 0:
        sig.append(("block", 20 * b30, f"Bị chặn {b30} lần trong 8–30 ngày trước"))
    rm = _n("SELECT COUNT(*) n FROM fb_incidents WHERE account_id=? AND kind='removed' AND created_at >= ?", (aid, d30))
    if rm:
        sig.append(("removed", min(32, 8 * rm), f"{rm} bài bị gỡ / ẩn"))
    bc = _n("SELECT COUNT(*) n FROM bumps WHERE account_id=? AND removed=1 AND checked_at >= ?", (aid, d30))
    rc = _n("SELECT COUNT(*) n FROM reply_tasks WHERE account_id=? AND removed=1 AND checked_at >= ?", (aid, d30))
    if bc + rc:
        sig.append(("comment", min(24, 6 * (bc + rc)), f"{bc + rc} bình luận bị nhóm xóa"))
    pf = _n("SELECT COUNT(*) n FROM posts WHERE account_id=? AND status='failed' AND COALESCE(scheduled_for, created_at) >= ?", (aid, _ago(7)))
    if pf:
        sig.append(("failed", min(12, 3 * pf), f"{pf} bài đăng lỗi trong 7 ngày"))
    fr = db.one("""SELECT SUM(status IN ('sent','accepted')) sent, SUM(status='accepted') ok FROM friend_suggestions
                   WHERE account_id=? AND sent_at >= ?""", (aid, d30)) or {}
    sent, okf = fr.get("sent") or 0, fr.get("ok") or 0
    if sent >= 10 and okf / sent < 0.3:
        sig.append(("friends", 10, f"Chỉ {round(100 * okf / sent)}% lời mời kết bạn được đồng ý ({okf}/{sent})"))
    ls = acc.get("login_status") or ""
    if ls in ("checkpoint", "error", "blocked"):
        sig.append(("login", 25, "Đang checkpoint / lỗi đăng nhập"))
    elif ls and ls != "ok":
        sig.append(("login", 10, "Chưa đăng nhập"))
    score = max(0, 100 - sum(x[1] for x in sig))
    level = next(k for k, lo, _ in LEVELS if score >= lo)
    advice = {
        "block": "Cho nick nghỉ vài ngày, sếp đăng nhập tay lướt như người thường; giữ nửa trần khi chạy lại",
        "removed": "Xem nội quy các nhóm đã gỡ bài (Luật Facebook → sự cố), bớt đăng nhóm cấm bán hàng",
        "comment": "Bớt bình luận ở nhóm đã xóa bình luận; câu bình luận ngắn, đúng nội dung bài",
        "failed": "Mở Chrome nick xem có thông báo hạn chế nào của Facebook không",
        "friends": "Mời ít hơn, chỉ mời người đang hỏi nguồn hàng hợp ngành",
        "login": "Mở Chrome nick để đăng nhập lại / xử lý checkpoint",
    }
    top = sorted(sig, key=lambda x: -x[1])
    return {"id": aid, "name": acc.get("name"), "sale_name": acc.get("sale_name"), "score": score, "level": level,
            "label": next(t for k, _, t in LEVELS if k == level), "signals": [{"code": c, "minus": m, "text": t} for c, m, t in top],
            "advice": [advice[c] for c, _, _ in top[:2]], "factor": FACTOR[level] if auto() else 1.0}


def auto() -> bool:
    return db.get_settings().get("nick_health_auto", "1") == "1"


def get(aid: int, fresh: bool = False) -> dict | None:
    hit = _cache.get(aid)
    if hit and not fresh and time.time() - hit[0] < TTL:
        return hit[1]
    acc = db.one("SELECT a.*, s.name sale_name FROM fb_accounts a LEFT JOIN sales s ON s.id=a.sale_id WHERE a.id=?", (aid,))
    if not acc:
        return None
    r = compute(acc)
    _cache[aid] = (time.time(), r)
    return r


def factor(acc: dict) -> float:
    """Hệ số trần theo sức khỏe (fb_policy.factor nhân thêm). Lỗi gì cũng trả 1 để không chặn việc."""
    if not auto() or not acc.get("id"):
        return 1.0
    try:
        return (get(acc["id"]) or {}).get("factor", 1.0)
    except Exception as e:
        print("[nick health]", e)
        return 1.0


def overview() -> dict:
    rows = db.q("""SELECT a.*, s.name sale_name FROM fb_accounts a JOIN sales s ON s.id=a.sale_id
                   WHERE a.enabled=1 AND COALESCE(s.status,'active')!='fired' ORDER BY a.sale_id, a.position, a.id""")
    items = []
    for a in rows:
        r = compute(a)
        _cache[a["id"]] = (time.time(), r)
        items.append(r)
    items.sort(key=lambda r: r["score"])
    cnt = {k: sum(1 for r in items if r["level"] == k) for k, _, _ in LEVELS}
    return {"items": items, "counts": cnt, "auto": auto()}


def tick(now) -> None:
    """Mỗi giờ: nick vừa rơi xuống Nguy hiểm thì ghi nhật ký và báo Telegram (mỗi nick một lần mỗi ngày)."""
    st = db.get_settings()
    key = now.strftime("%Y-%m-%d %H")
    if st.get("nick_health_last") == key:
        return
    db.set_setting("nick_health_last", key)
    sent = set((st.get("nick_health_alerted") or "").split(","))
    today = now.strftime("%Y-%m-%d")
    sent = {x for x in sent if x.startswith(today)}
    for r in overview()["items"]:
        tag = f"{today}:{r['id']}"
        if r["level"] != "bad" or tag in sent:
            continue
        sent.add(tag)
        why = "; ".join(s["text"] for s in r["signals"][:3])
        db.log("tuan", "Nick sức khỏe kém", f"Nick {r['name']} còn {r['score']}/100 ({why})"
               + (": tự chạy nửa trần" if r["factor"] < 1 else ""))
        try:
            import telegram_bot
            if telegram_bot.configured() and st.get("tg_alert_nick") == "1":
                telegram_bot.send(f"⚠️ <b>Nick {telegram_bot.e(r['name'])} (sale {telegram_bot.e(r.get('sale_name') or '')}) "
                                  f"sức khỏe {r['score']}/100</b>\n{telegram_bot.e(why)}\n"
                                  + ("Phần mềm đã cho nick chạy nửa trần. " if r["factor"] < 1 else "")
                                  + f"Nên: {telegram_bot.e(r['advice'][0]) if r['advice'] else 'xem mục Nhân viên sale'}")
        except Exception as e:
            print("[nick health tg]", e)
    db.set_setting("nick_health_alerted", ",".join(sorted(sent)))

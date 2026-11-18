"""Màn hình Bình luận: quản lý việc mỗi ngày tự bình luận (kèm 1 ảnh) vào từng bài đã đăng.

Bảo xếp lịch lúc `bump_time` (workflows.plan_bumps), viết mỗi bài một câu riêng; sale gửi bằng đúng nick đã đăng
(browser_poster._do_bump) theo Luật Facebook: mỗi bài tối đa 1 lần/ngày, trần lượt/nick/ngày, cách nhau vài phút,
chỉ trong giờ hoạt động của nick. Ở đây sếp xem lịch, sửa câu, hủy, thử lại, viết lại câu, bật/tắt từng bài.
"""
from datetime import datetime, timedelta

import db

STATUSES = ("scheduled", "running", "done", "failed", "skipped")


def _get(bid: int) -> dict:
    b = db.one("SELECT * FROM bumps WHERE id=?", (bid,))
    if not b:
        raise ValueError("Không tìm thấy lượt bình luận này")
    return b


def _ts(v: str | None) -> datetime | None:
    try:
        return datetime.strptime((v or "")[:16], "%Y-%m-%d %H:%M")
    except ValueError:
        return None


def _reason(p: dict, s: dict, planned: bool, now: datetime) -> str:
    """Vì sao bài chưa có lượt bình luận hôm nay (để sếp không phải đoán)."""
    if not p.get("account_id"):
        return "Không do nick sale đăng (fanpage/sếp tự đăng) nên không tự bình luận được"
    if p.get("permalink_status") == "removed":
        return "Bài đã bị gỡ hoặc ẩn"
    if str(p.get("bump_enabled")) == "0":
        return "Sếp đã tắt tự bình luận bài này"
    if (p.get("no_bump_until") or "") > db.now():
        return f"Nhóm đã xóa bình luận của mình: tạm ngừng bình luận nhóm này tới {p['no_bump_until'][8:10]}/{p['no_bump_until'][5:7]}"
    if s.get("bump_enabled") != "1":
        return "Đang tắt bình luận tự động (bật ở Cài đặt bên dưới)"
    import bump_watch
    why = bump_watch.stopped(p)
    if why:
        return why
    posted = _ts(p.get("posted_at"))
    if posted and posted > now - timedelta(hours=10):
        return "Vừa đăng chưa đủ 10 giờ, mai bình luận"
    if posted and posted < now - timedelta(days=int(s.get("bump_max_age_days") or 7)):
        return f"Đăng quá {s.get('bump_max_age_days') or 7} ngày, đã thôi bình luận"
    if not planned:
        return f"Chờ đến {s.get('bump_time') or '19:30'} Bảo xếp lịch"
    return "Hết lượt hôm nay của nick (trần an toàn) hoặc ngoài giờ hoạt động, mai bình luận tiếp"


def overview(day: str | None = None, status: str = "", account_id: int | None = None, q: str = "") -> dict:
    s = db.get_settings()
    today = db.today()
    day = (day or today)[:10]
    where, args = ["substr(COALESCE(b.scheduled_for, b.created_at), 1, 10)=?"], [day]
    if status in STATUSES:
        where.append("b.status=?"); args.append(status)
    if account_id:
        where.append("b.account_id=?"); args.append(account_id)
    if q.strip():
        where.append("(b.text LIKE ? OR p.title LIKE ? OR g.name LIKE ?)"); args += [f"%{q.strip()}%"] * 3
    items = db.q(f"""SELECT b.id, b.post_id, b.account_id, b.text, b.status, b.scheduled_for, b.done_at, b.error, b.screenshot,
                            b.image, b.gain_comments, b.gain_leads, b.measured_at, b.removed, b.checked_at, p.title, p.posted_url, p.permalink_status, g.name group_name, fa.name account_name, sa.name sale_name
                     FROM bumps b LEFT JOIN posts p ON p.id=b.post_id LEFT JOIN groups g ON g.id=p.group_id
                     LEFT JOIN fb_accounts fa ON fa.id=b.account_id LEFT JOIN sales sa ON sa.id=b.sale_id
                     WHERE {' AND '.join(where)} ORDER BY COALESCE(b.scheduled_for, b.created_at), b.id LIMIT 300""", args)
    counts = {k: 0 for k in STATUSES}
    for r in db.q("""SELECT status, COUNT(*) n FROM bumps WHERE substr(COALESCE(scheduled_for, created_at), 1, 10)=?
                     GROUP BY status""", (day,)):
        counts[r["status"]] = r["n"]

    # Bài đã đăng gần đây và lượt bình luận hôm nay của từng bài
    now = db.clock()
    age = int(s.get("bump_max_age_days") or 7)
    since = (now - timedelta(days=age + 3)).strftime("%Y-%m-%d %H:%M:%S")
    planned = s.get("bump_planned_date") == today
    posts = []
    for p in db.q("""SELECT p.id, p.title, p.posted_at, p.posted_url, p.account_id, p.permalink_status, p.bump_enabled,
                            p.bump_count, p.last_bump_at, p.bump_reset_at, p.group_id, g.no_bump_until, g.name group_name, fa.name account_name
                     FROM posts p LEFT JOIN groups g ON g.id=p.group_id LEFT JOIN fb_accounts fa ON fa.id=p.account_id
                     WHERE p.status='posted' AND p.posted_at >= ? ORDER BY p.posted_at DESC LIMIT 200""", (since,)):
        b = db.one("""SELECT id, status, scheduled_for, error FROM bumps WHERE post_id=? AND created_at LIKE ?
                      ORDER BY id DESC LIMIT 1""", (p["id"], today + "%"))
        p["today"] = b
        p["reason"] = None if b else _reason(p, s, planned, now)
        p["stopped"] = bool(p["reason"] and p["reason"].startswith(tuple("0123456789")))
        p["resting"] = bool(p["reason"] and p["reason"].startswith("Nhóm đã xóa"))
        posts.append(p)

    nicks = []
    try:
        import accounts
        import fb_policy
        for a in accounts.working():
            nicks.append({"id": a["id"], "name": accounts.label(a), "limit": fb_policy.limits(a)["bumps"],
                          "per_nick": int(s.get("bump_max_per_nick") or 8), "used": fb_policy.used_today(a["id"])["bumps"]})
    except Exception as e:  # không để bảng nick làm hỏng cả màn hình
        print("[comments] nicks", e)

    covered = sum(1 for p in posts if p["today"])
    eligible = sum(1 for p in posts if p["today"] or (p["reason"] or "").startswith(("Chờ", "Hết lượt")))
    import bump_watch
    return {"effect": bump_watch.overview(), "day": day, "today": today, "items": items, "counts": counts, "posts": posts, "nicks": nicks,
            "covered": covered, "eligible": eligible, "planned_today": planned,
            "settings": {k: s.get(k, "") for k in ("bump_enabled", "bump_time", "bump_max_age_days", "bump_max_per_nick",
                                                   "bump_gap_minutes", "bump_contact", "bump_text_mode", "bump_folder",
                                                   "bump_stop_after", "bump_check", "bump_rest_days")}}


def edit(bid: int, text: str) -> dict:
    b = _get(bid)
    if b["status"] != "scheduled":
        raise ValueError("Chỉ sửa được bình luận đang chờ gửi")
    text = " ".join((text or "").split())
    if len(text) < 4:
        raise ValueError("Câu bình luận quá ngắn")
    if len(text) > 300:
        raise ValueError("Câu bình luận dài quá 300 ký tự, nên ngắn gọn để không bị coi là spam")
    import fb_policy
    bad = [i for i in fb_policy.check_text(text, b.get("post_id"), b.get("account_id")) if i["level"] == "high"]
    if bad:
        raise ValueError("Câu vi phạm Luật Facebook: " + fb_policy.summary(bad))
    db.run("UPDATE bumps SET text=? WHERE id=? AND status='scheduled'", (text, bid))
    db.log("bao", "Sửa bình luận", f"Sếp sửa câu bình luận bài #{b['post_id']}: “{text[:80]}”")
    return _get(bid)


def rewrite(bid: int) -> dict:
    b = _get(bid)
    if b["status"] != "scheduled":
        raise ValueError("Chỉ viết lại được bình luận đang chờ gửi")
    p = db.one("SELECT * FROM posts WHERE id=?", (b["post_id"],))
    if not p:
        raise ValueError("Bài đăng không còn")
    import post_care
    text = post_care.texts_for([p], b.get("account_id"))[0]
    db.run("UPDATE bumps SET text=? WHERE id=? AND status='scheduled'", (text, bid))
    return _get(bid)


def cancel(bid: int) -> dict:
    b = _get(bid)
    if b["status"] != "scheduled":
        raise ValueError("Chỉ hủy được bình luận đang chờ gửi")
    db.run("UPDATE bumps SET status='skipped', error='Sếp hủy' WHERE id=? AND status='scheduled'", (bid,))
    db.log("bao", "Hủy bình luận", f"Sếp hủy lượt bình luận bài #{b['post_id']}")
    return _get(bid)


def retry(bid: int) -> dict:
    """Lượt lỗi/bỏ qua: xếp lại một lượt mới cho bài đó (vẫn qua Luật Facebook khi gửi)."""
    b = _get(bid)
    if b["status"] not in ("failed", "skipped"):
        raise ValueError("Chỉ thử lại lượt bị lỗi hoặc bỏ qua")
    p = db.one("SELECT id, account_id, sale_id, permalink_status FROM posts WHERE id=?", (b["post_id"],))
    if not p or not p.get("account_id"):
        raise ValueError("Bài không do nick sale đăng nên không bình luận tự động được")
    if p.get("permalink_status") == "removed":
        raise ValueError("Bài đã bị gỡ, không bình luận nữa")
    if db.one("SELECT 1 FROM bumps WHERE post_id=? AND created_at LIKE ? AND status IN ('scheduled','running','done')",
              (p["id"], db.today() + "%")):
        raise ValueError("Bài này hôm nay đã có lượt bình luận (mỗi bài tối đa 1 lần/ngày)")
    nid = db.run("""INSERT INTO bumps(post_id, sale_id, account_id, text, status, scheduled_for, created_at)
                    VALUES (?,?,?,?, 'scheduled', ?, ?)""",
                 (p["id"], p["sale_id"], p["account_id"], b["text"], db.clock().strftime("%Y-%m-%d %H:%M"), db.now()))
    return _get(nid)

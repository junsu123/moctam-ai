"""Bình luận tự động (up bài) có ích không: Bảo đo và tự điều chỉnh.

1. Đo: lúc gửi, ghi số bình luận và số khách của bài. Lần sau nick vào lại bài (hoặc sau 48 giờ) tính lượt đó làm bài có thêm
   bình luận / khách không (trừ chính bình luận của mình).
2. Ngừng sớm: bài có N lượt gần nhất (mặc định 3) không thêm gì thì thôi bình luận bài đó, dành lượt cho bài đang ra khách
   (sếp bấm "Bình luận tiếp" để bật lại). Bài có thêm khách / bình luận gần đây được xếp trước.
3. Nhóm xóa bình luận: sau 6 giờ nick mở lại bài (ghép vào ca làm việc sẵn có, không mở Chrome riêng) xem bình luận còn không.
   Không còn thì ngừng bình luận mọi bài ở nhóm đó 30 ngày: nhóm xóa bình luận là dấu hiệu trước khi nick bị báo cáo / khóa.
"""
import re
from datetime import datetime, timedelta

import db
from knowledge import plain


def _s() -> dict:
    return db.get_settings()


def _ago(**kw) -> str:
    return (db.clock() - timedelta(**kw)).strftime("%Y-%m-%d %H:%M:%S")


def _leads(post_id: int, after: str | None = None) -> int:
    return db.one("SELECT COUNT(*) n FROM leads WHERE post_id=? AND COALESCE(status,'')!='junk'" + (" AND created_at > ?" if after else ""),
                  (post_id, after) if after else (post_id,))["n"]


# ---------------------------------------------------------------- 1. đo
def before(bump_id: int, post_id: int, comments: int | None):
    """Gọi ngay khi gửi xong một lượt: ghi số bình luận (đọc trên trang, trước khi gửi) và số khách của bài."""
    db.run("UPDATE bumps SET comments_before=?, leads_before=? WHERE id=?", (comments, _leads(post_id), bump_id))


def _measure(b: dict, comments_now: int | None):
    gc = max(0, comments_now - (b["comments_before"] or 0) - 1) if comments_now is not None and b["comments_before"] is not None else 0
    gl = _leads(b["post_id"], b["done_at"])
    db.run("UPDATE bumps SET gain_comments=?, gain_leads=?, measured_at=? WHERE id=?", (gc, gl, db.now(), b["id"]))


def observe(post_id: int, comments_now: int | None):
    """Nick vừa vào lại bài và đọc được số bình luận: chấm các lượt trước của bài chưa chấm."""
    for b in db.q("""SELECT * FROM bumps WHERE post_id=? AND status='done' AND measured_at IS NULL AND comments_before IS NOT NULL""",
                  (post_id,)):
        _measure(b, comments_now)


def measure_stale(hours: int = 48) -> int:
    """Lượt đã gửi quá 48 giờ mà nick chưa vào lại: chấm theo số bình luận đã biết và khách mới của bài."""
    rows = db.q("""SELECT b.*, p.comments FROM bumps b JOIN posts p ON p.id=b.post_id WHERE b.status='done' AND b.measured_at IS NULL
                   AND b.done_at <= ?""", (_ago(hours=hours),))
    for b in rows:
        _measure(b, b["comments"] if b["comments_before"] is not None else None)
    return len(rows)


def stopped(post: dict) -> str | None:
    """Bài đã N lượt gần nhất không thêm bình luận / khách nào thì thôi bình luận (trả về lý do), không thì None."""
    n = int(_s().get("bump_stop_after") or 0)
    if n <= 0:
        return None
    rows = db.q("""SELECT gain_comments, gain_leads FROM bumps WHERE post_id=? AND status='done' AND measured_at IS NOT NULL
                   AND done_at > ? ORDER BY done_at DESC LIMIT ?""", (post["id"], post.get("bump_reset_at") or "", n))
    if len(rows) >= n and not any((r["gain_comments"] or 0) + (r["gain_leads"] or 0) for r in rows):
        return f"{n} lượt bình luận gần nhất không thêm bình luận hay khách nào: Bảo thôi bình luận bài này"
    return None


def score(post_id: int, days: int = 14) -> int:
    """Điểm hiệu quả gần đây của bài (khách × 5 + bình luận) để xếp bài đáng bình luận lên trước."""
    r = db.one("""SELECT COALESCE(SUM(gain_leads),0)*5 + COALESCE(SUM(gain_comments),0) s FROM bumps WHERE post_id=? AND done_at >= ?""",
               (post_id, _ago(days=days)))
    return r["s"] or 0


def resting_groups() -> list[dict]:
    return db.q("SELECT id, name, no_bump_until FROM groups WHERE no_bump_until > ? ORDER BY no_bump_until DESC", (db.now(),))


def resume_post(pid: int):
    db.run("UPDATE posts SET bump_reset_at=?, bump_enabled=1 WHERE id=?", (db.now(), pid))
    db.log("bao", "Bình luận tiếp", f"Sếp cho bình luận tiếp bài #{pid} (tính lại hiệu quả từ hôm nay)")


def resume_group(gid: int):
    db.run("UPDATE groups SET no_bump_until=NULL WHERE id=?", (gid,))
    g = db.one("SELECT name FROM groups WHERE id=?", (gid,)) or {}
    db.log("bao", "Bình luận lại nhóm", f"Sếp cho bình luận lại ở nhóm {g.get('name') or gid}")


# ---------------------------------------------------------------- 3. bình luận còn không
def due_checks(aid: int, n: int = 2) -> list[int]:
    if _s().get("bump_check", "1") != "1":
        return []
    return [r["id"] for r in db.q("""SELECT b.id FROM bumps b JOIN posts p ON p.id=b.post_id WHERE b.account_id=? AND b.status='done'
                                     AND b.checked_at IS NULL AND b.done_at <= ? AND b.done_at >= ? AND p.group_id IS NOT NULL
                                     AND COALESCE(p.posted_url,'')!='' ORDER BY b.done_at LIMIT ?""",
                                  (aid, _ago(hours=6), _ago(days=3), n))]


def _mine(text: str) -> str:
    return plain(re.sub(r"\s*👉.*$", "", text or "", flags=re.S))[:40]


def check(page, aid: int, ids: list[int]) -> int:
    """Mở lại bài của các lượt đã gửi trên 6 giờ: không còn thấy câu của mình thì coi như nhóm xóa, ngừng bình luận ở nhóm 30 ngày."""
    import browser_poster as B
    gone = 0
    for bid in ids:
        b = db.one("""SELECT b.*, p.posted_url, p.group_id, g.name group_name FROM bumps b JOIN posts p ON p.id=b.post_id
                      LEFT JOIN groups g ON g.id=p.group_id WHERE b.id=?""", (bid,))
        if not b:
            continue
        try:
            page.goto(B.fb_url(b["posted_url"]), wait_until="domcontentloaded", timeout=60000)
            page.wait_for_timeout(3500)
            B._check_blocked(page)
            body = page.inner_text("body")
            mine = _mine(b["text"])
            if any(t.lower() in body.lower() for t in B.selectors()["removed_texts"]) or not mine or mine in plain(body):
                db.run("UPDATE bumps SET checked_at=? WHERE id=?", (db.now(), bid))  # còn (hoặc cả bài bị gỡ: _do_bump tự xử lý)
                continue
            days = int(_s().get("bump_rest_days") or 30)
            until = (db.clock() + timedelta(days=days)).strftime("%Y-%m-%d %H:%M:%S")
            db.run("UPDATE bumps SET checked_at=?, removed=1 WHERE id=?", (db.now(), bid))
            db.run("UPDATE groups SET no_bump_until=? WHERE id=?", (until, b["group_id"]))
            db.run("UPDATE bumps SET status='skipped', error='Nhóm đã xóa bình luận của mình, tạm ngừng bình luận nhóm này' "
                   "WHERE status='scheduled' AND post_id IN (SELECT id FROM posts WHERE group_id=?)", (b["group_id"],))
            db.log("bao", "Nhóm xóa bình luận up bài",
                   f"Bình luận ở bài #{b['post_id']} (nhóm {b['group_name']}) không còn: ngừng bình luận nhóm này {days} ngày")
            gone += 1
        except B.Blocked:
            raise
        except Exception as e:
            print("[bump check]", e)
        B._pause(page, 4, 10)
    return gone


# ---------------------------------------------------------------- màn hình Bình luận
def overview(days: int = 30) -> dict:
    since = _ago(days=days)
    r = db.one("""SELECT COUNT(*) done, SUM(measured_at IS NOT NULL) measured,
                         SUM(measured_at IS NOT NULL AND COALESCE(gain_comments,0)+COALESCE(gain_leads,0)>0) useful,
                         COALESCE(SUM(gain_comments),0) comments, COALESCE(SUM(gain_leads),0) leads, COALESCE(SUM(removed),0) removed
                  FROM bumps WHERE status='done' AND done_at >= ?""", (since,))
    top = db.q("""SELECT b.post_id, p.title, g.name group_name, COUNT(*) n, SUM(COALESCE(b.gain_comments,0)) gc,
                         SUM(COALESCE(b.gain_leads,0)) gl FROM bumps b JOIN posts p ON p.id=b.post_id LEFT JOIN groups g ON g.id=p.group_id
                  WHERE b.status='done' AND b.done_at >= ? GROUP BY b.post_id HAVING gc + gl > 0
                  ORDER BY gl DESC, gc DESC LIMIT 5""", (since,))
    m = r["measured"] or 0
    return {"days": days, "done": r["done"] or 0, "measured": m, "useful": r["useful"] or 0, "comments": r["comments"],
            "leads": r["leads"], "removed": r["removed"], "useful_pct": round(100 * (r["useful"] or 0) / m) if m else None,
            "top": top, "resting": resting_groups(), "stop_after": int(_s().get("bump_stop_after") or 0)}

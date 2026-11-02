"""Lịch tự động: họp giao ban mỗi sáng, đăng Fanpage và giao bài cho nhân viên sale đúng giờ."""
import threading
import time
from datetime import datetime

import browser_poster
import db
import facebook
import meeting
import workflows


_n = {"tick": 0}


def _tick():
    _n["tick"] += 1
    if _n["tick"] % 4 == 1:  # khoảng 2 phút một lần: lô viết bài nào xong thì nhập bài nháp
        workflows.poll_batches()
    s = db.get_settings()
    now = datetime.now()
    stamp = now.strftime("%Y-%m-%d %H:%M")
    # Họp giao ban hằng ngày
    days = {d.strip() for d in (s.get("meeting_weekdays") or "1,2,3,4,5,6,7").split(",")}
    if s.get("auto_meeting") == "1" and str(now.isoweekday()) in days and now.strftime("%H:%M") >= s.get("meeting_time", "08:30"):
        if not db.one("SELECT id FROM meetings WHERE date=?", (db.today(),)) and not meeting.is_running():
            meeting.start()
    # Tự học mỗi đêm
    if s.get("learn_enabled") == "1" and now.strftime("%H:%M") >= (s.get("learn_time") or "23:15") \
            and s.get("learn_last_date") != db.today():
        import learning
        db.set_setting("learn_last_date", db.today())
        learning.nightly_async()
    # Bài Fanpage đã duyệt và đến giờ -> đăng qua Graph API
    if facebook.configured():
        for p in db.q("""SELECT * FROM posts WHERE target_type='page' AND status='scheduled'
                         AND scheduled_for <= ?""", (stamp,)):
            res = facebook.publish_page(f"{p['content']}\n\n{p['hashtags'] or ''}")
            if res["ok"]:
                workflows.mark_posted(p["id"], res["url"], "Fanpage (tự động)", res["id"])
            else:
                db.log("tuan", "Lỗi đăng Fanpage", res["error"])
                db.run("UPDATE posts SET status='approved' WHERE id=?", (p["id"],))
    # Bài nhóm / trang cá nhân đến giờ -> giao cho nhân viên sale giữ nick đó
    due = db.q("""SELECT p.id, p.sale_id FROM posts p JOIN sales s ON s.id=p.sale_id
                  WHERE p.status='scheduled' AND p.scheduled_for <= ? AND s.auto_post=1 AND s.login_status='ok'
                  ORDER BY p.scheduled_for""", (stamp,))
    started = set()
    busy_post = {p["sale_id"] for p in due}
    for p in due:
        sid = p["sale_id"]
        if sid in started or browser_poster.busy(sid) or browser_poster.queued(sid):
            continue  # mỗi nick làm một việc một lúc
        db.run("UPDATE posts SET status='posting' WHERE id=?", (p["id"],))
        browser_poster.submit(sid, {"kind": "post", "post_id": p["id"]})
        started.add(sid)
    _dispatch_bumps(stamp, s, busy_post | started)


def _dispatch_bumps(stamp: str, s: dict, busy_post: set):
    # Up bài: lên lịch 1 lần/ngày từ giờ đã cài, rồi giao từng lượt khi nick rảnh (ưu tiên việc đăng bài)
    if s.get("bump_enabled") == "1" and stamp[11:] >= (s.get("bump_time") or "19:30"):
        workflows.plan_bumps()
    for b in db.q("""SELECT b.id, b.sale_id, s.active_to FROM bumps b JOIN sales s ON s.id=b.sale_id
                     WHERE b.status='scheduled' AND b.scheduled_for <= ? AND s.auto_post=1 AND s.login_status='ok'
                     ORDER BY b.scheduled_for""", (stamp,)):
        sid = b["sale_id"]
        if stamp[11:] > (b["active_to"] or "22:00"):
            db.run("UPDATE bumps SET status='skipped', error='Ngoài khung giờ hoạt động của nick' WHERE id=?", (b["id"],))
            continue
        if sid in busy_post or browser_poster.busy(sid) or browser_poster.queued(sid):
            continue
        db.run("UPDATE bumps SET status='running' WHERE id=?", (b["id"],))
        browser_poster.submit(sid, {"kind": "bump", "bump_id": b["id"]})
        busy_post.add(sid)
    # lượt up bài của ngày cũ chưa chạy được -> bỏ qua
    db.run("UPDATE bumps SET status='skipped', error='Hết ngày, chưa đến lượt' WHERE status='scheduled' AND scheduled_for < ?",
           (stamp[:10],))


def start():
    def loop():
        while True:
            try:
                _tick()
            except Exception as e:
                print("[scheduler]", e)
            time.sleep(30)
    threading.Thread(target=loop, daemon=True).start()

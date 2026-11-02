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
    for p in due:
        sid = p["sale_id"]
        if sid in started or browser_poster.busy(sid) or browser_poster.queued(sid):
            continue  # mỗi nick làm một việc một lúc
        db.run("UPDATE posts SET status='posting' WHERE id=?", (p["id"],))
        browser_poster.submit(sid, {"kind": "post", "post_id": p["id"]})
        started.add(sid)


def start():
    def loop():
        while True:
            try:
                _tick()
            except Exception as e:
                print("[scheduler]", e)
            time.sleep(30)
    threading.Thread(target=loop, daemon=True).start()

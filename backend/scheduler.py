"""Lịch tự động: họp giao ban mỗi sáng, đăng Fanpage và giao bài cho nhân viên sale đúng giờ."""
import threading
import time
from datetime import datetime, timedelta

import browser_poster
import company
import db
import facebook
import meeting
import kpi
import my_groups
import prospect
import telegram_bot
import workflows


_n = {"tick": 0}


def _tick():
    _n["tick"] += 1
    if _n["tick"] % 4 == 1:  # khoảng 2 phút một lần: lô viết bài nào xong thì nhập bài nháp
        workflows.poll_batches()
    if company.tick() == "dissolved":
        return  # công ty đã giải thể: không họp, không đăng, không quét, không gọi AI
    s = db.get_settings()
    now = db.clock()
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
            res = facebook.publish_post(p)
            if res["ok"]:
                workflows.mark_posted(p["id"], res["url"], "Fanpage (tự động)", res["id"])
            else:
                db.log("tuan", "Không đăng bài thiếu ảnh" if res.get("no_image") else "Lỗi đăng Fanpage", f"Bài #{p['id']}: {res['error']}")
                db.run("UPDATE posts SET status='approved', scheduled_for=NULL WHERE id=?", (p["id"],))
    # Bài nhóm / trang cá nhân, lượt up bài, quét bình luận đến hạn -> sale làm theo ca trên từng nick
    if s.get("bump_enabled") == "1" and stamp[11:] >= (s.get("bump_time") or "19:30"):
        workflows.plan_bumps()
    dispatch_sessions(stamp)
    # Quét bình luận tìm khách theo các mốc giờ trong ngày
    if s.get("scan_enabled") == "1":
        hm = stamp[11:]
        due_slots = [t.strip() for t in (s.get("scan_times") or "").split(",") if t.strip() and t.strip() <= hm]
        if due_slots:
            key = f"{stamp[:10]} {max(due_slots)}"
            if s.get("scan_last") != key:
                db.set_setting("scan_last", key)
                telegram_bot.start_scan_round(force=False)
    # CEO tự vận hành: duyệt bài nháp của Lan rồi cho Tuấn xếp lịch
    import ceo_orders
    ceo_orders.tick()
    # Tìm hội nhóm mới theo chủ đề CEO chọn, xin vào nhóm
    import group_finder
    group_finder.tick(now)
    prospect.tick(now)  # Mai đi tìm khách sỉ mỗi ngày
    my_groups.tick(now)  # Tuấn rà soát nhóm trong nick, thoát nhóm kém; bù bài cho nhóm mình quản lý
    import knowledge
    knowledge.tick(now)
    import growth
    growth.tick(now)  # agent rảnh thì tự học / luyện tập để lên cấp
    import fb_policy
    if fb_policy.watch_due():  # Tuấn đọc lại chính sách Facebook mỗi tuần, báo sếp khi có thay đổi
        db.set_setting("fbp_watch_last", db.now())
        threading.Thread(target=fb_policy.check_sources, daemon=True).start()
    import friends
    friends.tick(now)  # Tuấn tìm người đáng kết bạn trong nhóm sôi nổi (sale tự bấm gửi)
    import website
    website.tick(now)  # Vy viết bài website theo lịch
    # KPI: chuyển khách cần sếp, nhắc lại; báo cáo Telegram
    kpi.check_escalations()
    telegram_bot.tick()


def dispatch_sessions(stamp: str) -> int:
    """Mỗi nhân viên sale đang rảnh: chọn nick kế tiếp (sau nick vừa làm) có việc đến hạn và giao một ca làm việc trên nick đó.
    Sale làm xong nick này mới chuyển sang nick khác."""
    import accounts
    hm = stamp[11:]
    # lượt up bài ngoài khung giờ của nick, hoặc của ngày cũ -> bỏ qua
    for b in db.q("""SELECT b.id, a.active_to FROM bumps b JOIN fb_accounts a ON a.id=b.account_id
                     WHERE b.status='scheduled' AND b.scheduled_for <= ?""", (stamp,)):
        if hm > (b["active_to"] or "22:00"):
            db.run("UPDATE bumps SET status='skipped', error='Ngoài khung giờ hoạt động của nick' WHERE id=?", (b["id"],))
    db.run("UPDATE bumps SET status='skipped', error='Hết ngày, chưa đến lượt' WHERE status='scheduled' AND scheduled_for < ?",
           (stamp[:10],))
    # bài đã quá giờ 2 tiếng mà nick không còn làm được (bị dừng, đăng xuất) -> trả về hàng đợi để Tuấn xếp nick khác
    late = (datetime.strptime(stamp, "%Y-%m-%d %H:%M") - timedelta(hours=2)).strftime("%Y-%m-%d %H:%M")
    ok_ids = {a["id"] for a in accounts.working()}
    for p in db.q("SELECT id, account_id FROM posts WHERE status='scheduled' AND scheduled_for <= ? AND account_id IS NOT NULL", (late,)):
        if p["account_id"] not in ok_ids:
            db.run("UPDATE posts SET status='approved', sale_id=NULL, account_id=NULL, scheduled_for=NULL WHERE id=?", (p["id"],))
    started = 0
    for sale in db.q("SELECT * FROM sales WHERE auto_post=1 AND COALESCE(status,'active')='active' ORDER BY id"):
        sid = sale["id"]
        if browser_poster.busy(sid) or browser_poster.queued(sid):
            continue  # sale đang làm việc trên một nick
        due = [a for a in accounts.working(sid) if any(browser_poster.due_work(a["id"], stamp).values())]
        if not due:
            continue
        last = sale.get("last_account_id") or 0
        due.sort(key=lambda a: (a["id"] <= last, a["position"], a["id"]))  # nick kế tiếp sau nick vừa làm
        browser_poster.submit(sid, {"kind": "session", "account": due[0]["id"]})
        started += 1
    return started


def start():
    def loop():
        while True:
            try:
                _tick()
            except Exception as e:
                print("[scheduler]", e)
                import errors
                errors.report_exc("scheduler", "Lịch tự động gặp lỗi", e)
            time.sleep(30)
    threading.Thread(target=loop, daemon=True).start()

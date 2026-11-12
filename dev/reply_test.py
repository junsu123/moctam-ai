"""Bảo trả lời khách hỏi mua trong nhóm: CEO giao -> nick đọc nhóm -> chọn bài hỏi mua -> sếp duyệt -> nick gửi (mockfb)."""
import os, sys, time, json, shutil, urllib.request
os.environ["FB_BASE_URL"] = "http://localhost:8098"
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "backend"))
from pathlib import Path
from datetime import timedelta
SP = Path(__import__("os").environ.get("MT_WORK") or Path(__file__).resolve().parent / "work")
import db
db.DB_PATH = SP / "reply.db"; db.DB_PATH.unlink(missing_ok=True)
db.PROFILES_DIR = SP / "reply_profiles"; shutil.rmtree(db.PROFILES_DIR, ignore_errors=True); db.PROFILES_DIR.mkdir()
db.SHOTS_DIR = SP / "multi_shots"; db.SHOTS_DIR.mkdir(exist_ok=True)
db.init(); db.set_setting("browser_headless", "1"); db.set_setting("anthropic_api_key", "")
urllib.request.urlopen(urllib.request.Request("http://localhost:8098/mockmode", data=json.dumps({"cmt": os.environ.get("CMT", "fb26")}).encode(), method="POST")).read()
import accounts, browser_poster as B, replies, ceo_orders, friends, fb_policy
B._pause = lambda *a, **k: None
import random
_ri = random.randint
from fastapi.testclient import TestClient
import main
c = TestClient(main.app)
sid = c.post("/api/sales", json={"name": "Linh", "fb_name": "Linh Nguyễn"}).json()["id"]
aid = accounts.of_sale(sid)[0]["id"]
db.run("UPDATE fb_accounts SET active_from='00:00', active_to='23:59', created_at='2025-01-01 00:00:00' WHERE id=?", (aid,))
from playwright.sync_api import sync_playwright
with sync_playwright() as pw:
    ctx = B._launch(pw, aid, headless=True); pg = ctx.new_page(); pg.goto("http://localhost:8098/setlogin"); ctx.close()
c.post(f"/api/accounts/{aid}/check"); time.sleep(1)
while B.busy(sid) or B.queued(sid): time.sleep(0.3)
print("nick:", accounts.get(aid)["login_status"])
gid = db.run("""INSERT INTO groups(name, url, members, avg_comments, avg_reactions, posts_today, created_at)
                VALUES ('Hội Tìm Nguồn Hàng Sỉ', 'http://localhost:8098/groups/hoimua', 25000, 14, 40, 12, ?)""", (db.now(),))
gid = gid if isinstance(gid, int) else db.one("SELECT MAX(id) i FROM groups")["i"]
db.run("INSERT INTO account_groups(group_id, account_id, status, updated_at) VALUES (?,?, 'joined', '2025-01-01')", (gid, aid))
print("nhóm sôi nổi:", [(g["name"], g["score"]) for g in friends.active_groups(aid, 3)])

# 1) CEO hiểu lệnh của sếp (đòi 24/24 vẫn chỉ làm phương án an toàn)
cmd = "điều các bạn nhân viên đi comment vào các bài ở các hội nhóm có độ tương tác cao, làm 24/24"
r = ceo_orders._rule_plan(cmd)
print("CEO hiểu:", r["actions"])
print("CEO làm:", ceo_orders.execute(r["actions"][0]))
time.sleep(1)
while B.busy(sid) or B.queued(sid): time.sleep(0.5)
rows = db.q("SELECT id, author, status, source, reply, post_url FROM reply_tasks ORDER BY id")
for x in rows: print("  chờ duyệt:", x["author"], "|", x["source"], "|", x["reply"])
assert {x["author"] for x in rows} == {"Ngọc Ánh", "Lê Minh Tâm"}, "chỉ lấy bài hỏi mua hợp ngành"
print("nhật ký Bảo:", [x["detail"][:160] for x in db.q("SELECT detail FROM activity WHERE agent_id='bao' ORDER BY id")][-1:])

# 2) quét lại không trùng bài
replies.start(aid)
time.sleep(1)
while B.busy(sid) or B.queued(sid): time.sleep(0.5)
print("quét lại, tổng bài:", db.one("SELECT COUNT(*) n FROM reply_tasks")["n"])

# 3) duyệt: câu phạm luật bị chặn, sếp sửa câu -> Bảo lưu làm mẫu, giãn cách giữa 2 câu
try:
    replies.approve(rows[0]["id"], "Trà này chữa bệnh tiểu đường, giảm cân cấp tốc")
    print("LỖI: câu phạm luật vẫn được duyệt")
except ValueError as e:
    print("chặn câu phạm luật:", e)
a1 = replies.approve(rows[0]["id"], "Chào bạn, bên mình là xưởng trà gừng mật ong túi lọc, có giá sỉ và gửi mẫu thử được nha. 👉 " + replies.contact())
a2 = c.put(f"/api/replies/{rows[1]['id']}", json={"action": "approve"}).json()
print("duyệt:", a1, a2)
from datetime import datetime
t1, t2 = (datetime.strptime(x["scheduled_for"], "%Y-%m-%d %H:%M") for x in (a1, a2))
print("cách nhau (phút):", (t2 - t1).seconds // 60)
assert 51 <= (t2 - t1).seconds // 60 <= replies.gap_minutes(accounts.get(aid), replies.quota(aid)["limit"]) * 1.2 + 1  # dàn đều giờ làm
print("mẫu Bảo học từ câu sếp sửa:", post_care_s := [s["text"] for s in __import__("post_care").samples(5, "reply")])

# 4) tới giờ: ca làm việc của sale gửi câu đã duyệt (chỉ chữ, không ảnh)
db.run("UPDATE reply_tasks SET scheduled_for=? WHERE id=?", ((db.clock() - timedelta(minutes=1)).strftime("%Y-%m-%d %H:%M"), rows[0]["id"]))
print("việc đến hạn:", B.due_work(aid)["replies"])
B.submit(sid, {"kind": "session", "account": aid})
time.sleep(1)
while B.busy(sid) or B.queued(sid): time.sleep(0.5)
x = db.one("SELECT status, error, shot, sent_at FROM reply_tasks WHERE id=?", (rows[0]["id"],))
print("gửi:", x)
cm = [json.loads(l) for l in open(SP / "mockfb_log.jsonl", encoding="utf-8") if '"path": "/comment"' in l][-1]
print("  mock nhận:", cm.get("post"), cm.get("text"), cm.get("files"))
assert x["status"] == "sent" and cm.get("post") == 800 and not cm.get("files")

# 5) trần mỗi ngày: hạ còn 2 -> câu thứ 3 dời sang ngày mai
db.set_setting("replies_per_nick_day", "2")
db.run("""INSERT INTO reply_tasks(account_id, group_id, post_url, author, post_text, reply, source, status, created_at)
          VALUES (?,?,'http://localhost:8098/groups/hoimua/posts/899','Khách C','cần nguồn trà túi lọc','Bên mình có nhé','bao','draft',?)""",
       (aid, gid, db.now()))
rid3 = db.one("SELECT MAX(id) i FROM reply_tasks")["i"]
print("quota:", replies.quota(aid), "| duyệt câu 3:", replies.approve(rid3))

# 6) ngoài giờ làm: không gửi, dời sang sáng mai
hm = db.clock()
db.run("UPDATE fb_accounts SET active_from=?, active_to=? WHERE id=?",
       ((hm + timedelta(hours=2)).strftime("%H:%M"), (hm + timedelta(hours=3)).strftime("%H:%M"), aid))
db.run("UPDATE reply_tasks SET scheduled_for=? WHERE id=?", ((hm - timedelta(minutes=1)).strftime("%Y-%m-%d %H:%M"), rows[1]["id"]))
with sync_playwright() as pw:
    ctx, page = B._open(pw, aid)
    replies.send(page, aid, rows[1]["id"]); ctx.close()
print("ngoài giờ làm:", db.one("SELECT status, scheduled_for FROM reply_tasks WHERE id=?", (rows[1]["id"],)))

# 6b) gửi dồn: câu 2 tới hạn ngay sau câu 1 -> lùi lại >=45 phút; đủ trần -> dời sang mai
db.run("UPDATE fb_accounts SET active_from='00:00', active_to='23:59' WHERE id=?", (aid,))
db.run("UPDATE reply_tasks SET scheduled_for=? WHERE id=?", ((hm - timedelta(minutes=1)).strftime("%Y-%m-%d %H:%M"), rows[1]["id"]))
with sync_playwright() as pw:
    ctx, page = B._open(pw, aid)
    replies.send(page, aid, rows[1]["id"]); ctx.close()
print("gửi dồn (lùi giờ):", db.one("SELECT status, scheduled_for FROM reply_tasks WHERE id=?", (rows[1]["id"],)))
db.set_setting("replies_per_nick_day", "1")
with sync_playwright() as pw:
    ctx, page = B._open(pw, aid)
    replies.send(page, aid, rows[1]["id"]); ctx.close()
print("đủ trần (dời mai):", db.one("SELECT status, scheduled_for FROM reply_tasks WHERE id=?", (rows[1]["id"],)))

# 7) API
print("API tổng quan:", {k: v for k, v in c.get("/api/replies").json().items() if k in ("stats", "nicks", "skill")})
print("API trần 50:", c.put("/api/replies-settings", json={"replies_per_nick_day": "50"}).status_code)
print("API bỏ qua + chặn:", c.put(f"/api/replies/{rid3}", json={"action": "junk"}).json())
print("luật FB có mục bình luận bài người khác:", any(r["id"] == "comment_others" for r in fb_policy.RULES))
print("lỗi:", db.q("SELECT title, message FROM errors"))

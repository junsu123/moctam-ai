"""Chỉ đạo nơi đăng + gợi ý kết bạn trong nhóm sôi nổi (đọc mockfb, sale tự bấm gửi)."""
import os, sys, time, json
os.environ["FB_BASE_URL"] = "http://localhost:8098"
sys.path.insert(0, "/home/claude/ai-sales-company/backend")
from pathlib import Path
import shutil
SP = Path(__import__("os").environ.get("MT_WORK") or Path(__file__).resolve().parent / "work")
import db
db.DB_PATH = SP / "friends.db"; db.DB_PATH.unlink(missing_ok=True)
db.PROFILES_DIR = SP / "friends_profiles"; shutil.rmtree(db.PROFILES_DIR, ignore_errors=True); db.PROFILES_DIR.mkdir()
db.SHOTS_DIR = SP / "multi_shots"; db.SHOTS_DIR.mkdir(exist_ok=True)
db.init(); db.set_setting("browser_headless", "1"); db.set_setting("fbp_enabled", "1")
import accounts, browser_poster as B, friends, group_target, workflows, group_finder
B._pause = lambda *a, **k: None
import types; friends_rand = types.SimpleNamespace(uniform=lambda a, b: 0.05, randint=lambda a, b: a)
import random as _r; _r.uniform = lambda a, b: 0.05
from fastapi.testclient import TestClient
import main
c = TestClient(main.app)
db.run("DELETE FROM groups")
G = {}
for name, url, topic, extra in [
    ("Chợ Sỉ Thực Phẩm", "http://localhost:8098/groups/chosi", "nguồn hàng sỉ", dict(posts_month=900, avg_comments=8, avg_reactions=30, new_members_week=300, members=40000)),
    ("Hội Bán Hàng Online", "http://localhost:8098/groups/shoponline", "bán hàng online", dict(posts_month=300, avg_comments=4, avg_reactions=12, new_members_week=50, members=20000)),
    ("Trà Thảo Mộc Việt", "http://localhost:8098/groups/trathaomoc", "trà thảo mộc", dict(posts_month=60, avg_comments=1, avg_reactions=3, members=3000)),
    ("Hội Mẹ Bỉm Sữa", "http://localhost:8098/groups/mebim", "mẹ và bé", dict(posts_month=1500, avg_comments=12, avg_reactions=50, members=200000)),
    ("Rao Vặt Quần Áo", "http://localhost:8098/groups/quanao", "thời trang", dict(posts_month=30, members=1000)),
]:
    cols = ["name", "url", "topic", "created_at"] + list(extra)
    G[name] = db.run(f"INSERT INTO groups({','.join(cols)}) VALUES ({','.join('?'*len(cols))})", (name, url, topic, db.now(), *extra.values()))
# 1) chỉ đạo nơi đăng
print("mặc định:", {k: v for k, v in c.get("/api/post-target").json().items() if k in ("mode", "include", "exclude")})
pv = c.post("/api/post-target/preview", json={"mode": "only", "include": "trà, ngũ cốc", "exclude": ["quần áo"]}).json()
print("xem trước only:", pv["counts"], "đăng", pv["will_post"], "|", [(i["name"], i["kind"], i["will_post"]) for i in pv["items"]])
print("chưa lưu -> mode vẫn:", group_target.settings()["mode"])
o = c.put("/api/post-target", json={"mode": "only", "include": "Trà, ngu coc,  trà", "exclude": "quần áo"}).json()
print("lưu:", o["mode"], o["include"], o["exclude"])
print("focus:", c.put(f"/api/groups/{G['Hội Mẹ Bỉm Sữa']}/focus", json={"focus": True}).json())
rows = db.q("SELECT * FROM groups ORDER BY id")
print("apply only:", [g["name"] for g in group_target.apply(rows)])
db.set_setting("post_target_mode", "prefer")
print("apply prefer:", [g["name"] for g in group_target.apply(rows)])
db.set_setting("post_target_mode", "all")
print("apply all:", [g["name"] for g in group_target.apply(rows)])
db.set_setting("post_target_mode", "only"); db.set_setting("post_group_keywords", "giày dép")
db.run("UPDATE groups SET focus=0")
pv = c.get("/api/post-target").json()["preview"]
print("only không khớp -> cảnh báo:", pv["warn"], pv["will_post"])
print("prompt:", group_target.prompt_line())
# group_ready: focus -> 1 ngày
g = dict(db.one("SELECT * FROM groups WHERE id=?", (G["Chợ Sỉ Thực Phẩm"],)))
g["last_posted_at"] = (db.clock().replace(hour=1) - __import__("datetime").timedelta(days=1)).strftime("%Y-%m-%d %H:%M:%S")
print("ready (đăng hôm qua) thường:", workflows.group_ready(g), "| focus:", workflows.group_ready({**g, "focus": 1}))
db.set_setting("post_target_mode", "all"); db.set_setting("post_group_keywords", ""); db.set_setting("post_group_exclude", "quần áo")
# CEO hiểu lệnh
import ceo_orders
for t in ["chỉ đăng ở nhóm có từ khóa trà túi lọc, ngũ cốc", "không đăng vào nhóm mẹ bỉm", "tập trung đăng vào nhóm Hội Bán Hàng Online", "cho các nick kết bạn với thành viên nhóm"]:
    print("CEO:", t, "->", ceo_orders._rule_plan(t)["actions"])
for a in ceo_orders._rule_plan("tập trung đăng vào nhóm Hội Bán Hàng Online")["actions"]:
    print("   thực hiện:", ceo_orders.execute(a))
print("sau lệnh:", group_target.settings(), db.one("SELECT name, focus FROM groups WHERE focus=1"))
db.set_setting("post_target_mode", "all"); db.set_setting("post_group_exclude", "")
# 2) kết bạn
print("chưa có nick:", c.post("/api/friends/scan", json={}).json())
sid = c.post("/api/sales", json={"name": "Linh", "fb_name": "Linh Nguyễn"}).json()["id"]
aid = accounts.of_sale(sid)[0]["id"]
from playwright.sync_api import sync_playwright
with sync_playwright() as pw:
    ctx = B._launch(pw, aid, headless=True); pg = ctx.new_page(); pg.goto("http://localhost:8098/setlogin"); ctx.close()
c.post(f"/api/accounts/{aid}/check"); time.sleep(1)
while B.busy(sid) or B.queued(sid): time.sleep(0.3)
print("nick:", accounts.get(aid)["login_status"])
for name in ("Chợ Sỉ Thực Phẩm", "Hội Bán Hàng Online", "Trà Thảo Mộc Việt", "Rao Vặt Quần Áo"):
    group_finder.set_join(G[name], aid, "joined", "test")
db.run("UPDATE account_groups SET joined_at=datetime(joined_at,'-5 days')")
db.run("UPDATE fb_accounts SET groups_synced_at=? WHERE id=?", (db.now(), aid))
rank = c.get(f"/api/friends/groups?account_id={aid}").json()
print("xếp hạng sôi nổi:", [(r["name"], r["score"], r["parts"]) for r in rank])
print("quota:", friends.quota(aid))
db.run("UPDATE fb_accounts SET created_at=datetime('now','-30 days') WHERE id=?", (aid,))
print("quota nick cũ:", friends.quota(aid))
print("open khi chưa có ai:", c.post("/api/friends/open", json={"account_id": aid}).json())
r = c.post("/api/friends/scan", json={}).json(); print("giao:", r); time.sleep(1)
while B.busy(sid) or B.queued(sid): time.sleep(0.5)
o = c.get("/api/friends").json()
print("nicks:", o["nicks"]); print("stats:", o["stats"])
for it in o["items"]:
    print(f"  {it['score']:>3} {it['name']:22} {it['group_name']:22} {it['profile_url']:45} {it['reason']}")
print("log:", db.one("SELECT detail FROM activity WHERE agent_id='tuan' AND action='Gợi ý kết bạn' ORDER BY id DESC LIMIT 1"))
print("đã đọc nhóm:", db.q("SELECT name, friends_scanned_at IS NOT NULL s, avg_comments, sampled_posts FROM groups WHERE friends_scanned_at IS NOT NULL"))
# chạy lại: không trùng, chọn nhóm khác
n0 = db.one("SELECT COUNT(*) n FROM friend_suggestions")["n"]
print("lần 2 chọn nhóm:", [g["name"] for g in friends.plan_groups(aid)])
# mở hồ sơ (headless trong test): đánh dấu opened, mở tab
B._job_open_orig = B._job_open
opened = {}
def fake_open(pw, aid_, minutes=30, urls=None): opened["urls"] = urls
B._job_open = fake_open
r = c.post("/api/friends/open", json={"account_id": aid, "n": 3}).json(); print("mở hồ sơ:", r["names"])
time.sleep(1)
while B.busy(sid) or B.queued(sid): time.sleep(0.3)
print("tab mở:", opened)
ids = r["opened"]
print("đánh dấu gửi:", c.put(f"/api/friends/{ids[0]}", json={"status": "sent"}).json())
print("đồng ý:", c.put(f"/api/friends/{ids[1]}", json={"status": "accepted"}).json()["quota"])
print("rác:", c.put(f"/api/friends/{ids[2]}", json={"status": "junk", "reason": "competitor", "note": "bán sỉ"}).json()["status"],
      "junk:", db.q("SELECT name, url, reason FROM junk"))
print("tổng:", c.get("/api/friends").json()["stats"], "used_today luật:", __import__("fb_policy").used_today(aid)["friends"])
db.set_setting("fbp_friends_day", "2")
print("hết lượt:", c.post("/api/friends/open", json={"account_id": aid}).json())
print("cài đặt sai:", c.put("/api/friends-settings", json={"friends_time": "abc"}).json(), c.put("/api/friends-settings", json={"x": 1}).status_code)
print("cài đặt:", c.put("/api/friends-settings", json={"friends_time": "9:05", "fbp_friends_day": "8"}).json()["settings"])
# tick: chạy 1 lần/ngày
db.set_setting("friends_last", ""); db.set_setting("friends_time", "00:00")
n1 = db.one("SELECT COUNT(*) n FROM friend_suggestions")["n"]
friends.tick(db.clock()); time.sleep(1)
while B.busy(sid) or B.queued(sid): time.sleep(0.5)
print("tick lần 1 thêm:", db.one("SELECT COUNT(*) n FROM friend_suggestions")["n"] - n1, "| last:", db.get_settings()["friends_last"] == db.today())
friends.tick(db.clock()); print("tick lần 2 hàng đợi:", B.queued(sid), B.busy(sid))
print("luật kết bạn:", [r["title"] for r in __import__("fb_policy").RULES if r["id"] == "friend_requests"], "| kiến thức:",
      db.one("SELECT COUNT(*) n FROM knowledge WHERE topic LIKE '%Kết bạn%'"))
print("lỗi:", db.q("SELECT title, message FROM errors"))

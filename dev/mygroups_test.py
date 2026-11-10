"""Nhóm có sẵn trong nick: đọc danh sách, Tuấn đánh giá, tự thoát nhóm kém, nhóm mới vào nghỉ, nhóm quản lý 5–10 bài/ngày."""
import os, sys, time, json, shutil, types, urllib.request
os.environ["FB_BASE_URL"] = "http://localhost:8098"
sys.path.insert(0, "/home/claude/ai-sales-company/backend")
from pathlib import Path
SP = Path(__import__("os").environ.get("MT_WORK") or Path(__file__).resolve().parent / "work")
urllib.request.urlopen(urllib.request.Request("http://localhost:8098/mygroups", data=b'{"on": true}', method="POST"))
open(SP / "mockfb_log.jsonl", "w").close()
import db
db.DB_PATH = SP / "mg.db"; db.DB_PATH.unlink(missing_ok=True)
db.PROFILES_DIR = SP / "mg_profiles"; shutil.rmtree(db.PROFILES_DIR, ignore_errors=True); db.PROFILES_DIR.mkdir()
db.SHOTS_DIR = SP / "multi_shots"
db.init(); db.set_setting("browser_headless", "1"); db.set_setting("browse_minutes", "0"); db.set_setting("bump_folder", str(SP / "img2_folder"))  # bài bắt buộc có ảnh
import accounts, browser_poster as B, group_finder, my_groups, workflows
B._pause = lambda *a, **k: None
group_finder.random = my_groups.random = types.SimpleNamespace(uniform=lambda a, b: 0.05, randint=lambda a, b: a, Random=__import__("random").Random)
from fastapi.testclient import TestClient
import main
c = TestClient(main.app)
db.run("DELETE FROM groups")  # bỏ nhóm mẫu
sid = c.post("/api/sales", json={"name": "Linh", "fb_name": "Linh Nguyễn"}).json()["id"]
aid = accounts.of_sale(sid)[0]["id"]
db.run("UPDATE fb_accounts SET active_from='00:00', active_to='23:59', max_posts_per_day=5 WHERE id=?", (aid,))
from playwright.sync_api import sync_playwright
with sync_playwright() as pw:
    ctx = B._launch(pw, aid, headless=True); pg = ctx.new_page(); pg.goto("http://localhost:8098/setlogin"); ctx.close()
c.post(f"/api/accounts/{aid}/check"); time.sleep(1)
while B.busy(sid) or B.queued(sid): time.sleep(0.3)
# nhóm phần mềm vừa xin vào 2 ngày trước
gid = db.run("INSERT INTO groups(name, url, created_at, source) VALUES ('Nguồn Hàng Sỉ Thực Phẩm Tận Xưởng','http://localhost:8098/groups/nguonhangsi',?, 'search')", (db.now(),))
group_finder.set_join(gid, aid, "joined", "Sale xin vào")
db.run("UPDATE account_groups SET joined_at=datetime(joined_at,'-2 days') WHERE group_id=?", (gid,))
print("trước rà soát, nick đăng được nhóm mới vào?", accounts.can_post_in(db.one("SELECT * FROM groups WHERE id=?", (gid,)), aid))
print("sync:", c.post("/api/my-groups/sync").json()); time.sleep(1)
while B.busy(sid) or B.queued(sid): time.sleep(0.5)
o = c.get("/api/my-groups").json()
for it in o["items"]:
    print(f"- {it['name'][:40]:40} {it['role']:6} {str(it['origin']):8} {it['status']:6} {it['verdict']:8} điểm={it['eng_score']} nghỉ đến={it['rest_until']} "
          f"| {(it['verdict_note'] or '')[:110]}" + (f" | hôm nay {it.get('today')}/{it.get('target')}" if it.get('target') else ""))
print("nicks:", o["nicks"])
print("mock đã thoát:", [json.loads(l)["slug"] for l in open(SP / "mockfb_log.jsonl") if '"/leave"' in l])
print("log:", db.q("SELECT action, detail FROM activity WHERE agent_id IN ('tuan','lan') ORDER BY id DESC LIMIT 3"))
for g in db.q("SELECT * FROM groups"):
    print("   can_post", g["name"][:30], accounts.can_post_in(g, aid), my_groups.membership(g, aid))
# bài bán hàng đã duyệt + xếp lịch
workflows.generate_posts(4)
db.run("UPDATE posts SET status='approved' WHERE status='draft'")
plan = workflows.plan_distribution()
print("plan thường:", [(p["group"], p["time"]) for p in plan])
print("bài nhóm quản lý:", db.q("""SELECT g.name, COUNT(*) n, SUM(p.source='template') tpl, MIN(scheduled_for) t1, MAX(scheduled_for) t2 FROM posts p JOIN groups g ON g.id=p.group_id WHERE p.managed=1 GROUP BY g.name"""))
print("mẫu bài:", [r["content"][:90] for r in db.q("SELECT content FROM posts WHERE managed=1 LIMIT 2")]); print("nguồn bài nhóm:", db.q("SELECT source, status, COUNT(*) n FROM posts GROUP BY source, status"))
print("chạy lại plan_admin:", my_groups.plan_admin()); print("thời gian:", [r["scheduled_for"][11:] + ("C" if r["source"]=="care" else "S") for r in db.q("SELECT scheduled_for, source FROM posts WHERE managed=1 ORDER BY scheduled_for")])
print("đăng thử 1 bài chăm sóc:")
pid = db.one("SELECT id FROM posts WHERE managed=1 ORDER BY scheduled_for LIMIT 1")["id"]
db.run("UPDATE posts SET scheduled_for=? WHERE id=?", (db.now()[:16], pid))
B.submit(sid, {"kind": "session", "account": aid}); time.sleep(1)
while B.busy(sid) or B.queued(sid): time.sleep(0.5)
print("  ", db.one("SELECT status, error, posted_url FROM posts WHERE id=?", (pid,)))
print("lỗi:", db.q("SELECT title, message FROM errors"))

"""Lưu link bài sau khi đăng: phản hồi Facebook, bảng tin kiểu mới (rê chuột mới có link), chờ duyệt, thử lại, dán tay."""
import os, sys, json, shutil, types, urllib.request
os.environ["FB_BASE_URL"] = "http://localhost:8098"
sys.path.insert(0, "/home/claude/ai-sales-company/backend")
from pathlib import Path
SP = Path(__import__("os").environ.get("MT_WORK") or Path(__file__).resolve().parent / "work")
import db
db.DB_PATH = SP / "link.db"; db.DB_PATH.unlink(missing_ok=True)
db.PROFILES_DIR = SP / "link_profiles"; shutil.rmtree(db.PROFILES_DIR, ignore_errors=True); db.PROFILES_DIR.mkdir()
db.SHOTS_DIR = SP / "link_shots"; db.SHOTS_DIR.mkdir(exist_ok=True)
db.init(); db.set_setting("fbp_enabled", "0"); db.set_setting("browser_headless", "1"); db.set_setting("bump_folder", str(SP / "img2_folder"))
import accounts, browser_poster as B
B._pause = lambda *a, **k: None
from fastapi.testclient import TestClient
import main
c = TestClient(main.app)
def mode(**kw):
    urllib.request.urlopen(urllib.request.Request("http://localhost:8098/mockmode", data=json.dumps(kw).encode(), method="POST"))
def mock(path, **kw):
    urllib.request.urlopen(urllib.request.Request("http://localhost:8098" + path, data=json.dumps(kw).encode(), method="POST"))
sid = c.post("/api/sales", json={"name": "Linh", "fb_name": "Linh Nguyễn"}).json()["id"]; aid = accounts.of_sale(sid)[0]["id"]
from playwright.sync_api import sync_playwright
with sync_playwright() as pw:
    ctx = B._launch(pw, aid, headless=True); pg = ctx.new_page(); pg.goto("http://localhost:8098/setlogin"); ctx.close()
gm = db.run("INSERT INTO groups(name, url, created_at) VALUES ('Nhóm hiện đại','http://localhost:8098/groups/modern',?)", (db.now(),))
gr = db.run("INSERT INTO groups(name, url, created_at) VALUES ('Nhóm thật','http://localhost:8098/groups/real',?)", (db.now(),))
n = [0]
def post(gid=gm):
    n[0] += 1
    return db.run("""INSERT INTO posts(agent_id, target_type, group_id, title, content, status, account_id, sale_id, scheduled_for, created_at)
                     VALUES ('lan','group',?,?,?,'scheduled',?,?,?,?)""",
                  (gid, f"Bài {n[0]}", f"🌿 MỘC TÂM 🌿\nNhận gia công & sỉ toàn quốc trà túi lọc số {n[0]} {os.urandom(3).hex()}\nInbox Zalo 0386992326",
                   aid, sid, db.now()[:16], db.now()))
def run(pid):
    with sync_playwright() as pw: B._job_post(pw, aid, pid, False)
    return db.one("SELECT status, posted_url, permalink_status, link_tries, link_next_at, link_error FROM posts WHERE id=?", (pid,))
def show(name, r): print(f"{name:42} {r['status']} | {r['permalink_status']} | {r['posted_url']} | thử {r['link_tries']} hẹn {r['link_next_at']} | {(r['link_error'] or '')[:70]}")
mode(graphql="url", pending=False, comments=False); show("A. phản hồi Facebook có link", run(post()))
mode(graphql="none"); show("B. không có phản hồi -> rê chuột trên bảng tin", run(post()))
mode(graphql="none", comments=True); show("C. như B, có bình luận dưới bài", run(post()))
mode(graphql="id", comments=False); show("D. phản hồi chỉ có mã bài", run(post()))
show("E. nhóm kiểu cũ (role=article)", run(post(gr)))
mode(graphql="url", pending=True); pe = post(); r = run(pe); show("F. nhóm cần duyệt bài", r)
# F2: nhóm duyệt bài -> ca làm việc tự lấy lại
mock("/approve_post", id=1000 + len([1 for l in open(SP / "mockfb_log.jsonl") if '"/record"' in l]) - 1) if False else None
last_id = int(r["posted_url"].rstrip("/").split("/")[-1]) if r["posted_url"] else None
print("   chờ duyệt, gọi due_work ngay:", B.due_work(aid)["links"])
mock("/approve_post", id=last_id); mode(pending=False)
print("   hẹn xem lại:", db.one("SELECT link_next_at, link_error FROM posts WHERE id=?", (pe,))); db.run("UPDATE posts SET link_next_at=? WHERE id=?", (db.now()[:16], pe))
print("   đến giờ:", B.due_work(aid)["links"])
with sync_playwright() as pw: B._job_session(pw, aid)
show("F2. sau khi nhóm duyệt, sale lấy lại", db.one("SELECT * FROM posts WHERE id=?", (pe,)))
# G: không tìm thấy -> hẹn thử lại -> lần sau tìm được
mode(graphql="none"); orig = B._snippets; B._snippets = lambda c: ["khong co doan chu nay"]
pg_ = post(); show("G. không thấy bài", run(pg_))
B._snippets = orig
db.run("UPDATE posts SET link_next_at=? WHERE id=?", (db.now()[:16], pg_))
r = c.post(f"/api/posts/{pg_}/fetch-link").json(); print("   nút Lấy link ngay:", r)
import time
while B.busy(sid) or B.queued(sid): time.sleep(0.5)
show("G2. sale thử lại", db.one("SELECT * FROM posts WHERE id=?", (pg_,)))
# H: hết lượt -> báo sếp
B._snippets = lambda c: ["khong co doan chu nay"]
ph = post(); run(ph)
for _ in range(5):
    db.run("UPDATE posts SET link_next_at=? WHERE id=?", (db.now()[:16], ph))
    with sync_playwright() as pw: B._job_link(pw, aid, ph)
B._snippets = orig
show("H. thử 6 lần không được", db.one("SELECT * FROM posts WHERE id=?", (ph,)))
print("   sổ lỗi:", [(e["title"], e["status"]) for e in db.q("SELECT * FROM errors WHERE source='link'")])
# I: sếp dán link
print("   dán link nhóm:", c.patch(f"/api/posts/{ph}", json={"posted_url": "https://www.facebook.com/groups/modern"}).status_code)
r = c.patch(f"/api/posts/{ph}", json={"posted_url": "https://www.facebook.com/groups/modern/posts/123456/?__cft__[0]=x"}).json()
print("I. dán link bài:", r["posted_url"], r["permalink_status"], r["link_next_at"], "| lỗi:", [(e["status"]) for e in db.q("SELECT * FROM errors WHERE source='link'")])
print("lỗi khác:", [e["title"] for e in db.q("SELECT title FROM errors WHERE source!='link'")])

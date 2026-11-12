"""Ảnh phải thật sự nằm trong bài trên Facebook."""
import os, sys, json, shutil, urllib.request
os.environ["FB_BASE_URL"] = "http://localhost:8098"
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "backend"))
from pathlib import Path
SP = Path(__import__("os").environ.get("MT_WORK") or Path(__file__).resolve().parent / "work")
import db
db.DB_PATH = SP / "attach.db"; db.DB_PATH.unlink(missing_ok=True)
db.PROFILES_DIR = SP / "attach_profiles"; shutil.rmtree(db.PROFILES_DIR, ignore_errors=True); db.PROFILES_DIR.mkdir()
db.SHOTS_DIR = SP / "attach_shots"; db.SHOTS_DIR.mkdir(exist_ok=True)
db.init(); db.set_setting("fbp_enabled", "0"); db.set_setting("browser_headless", "1"); db.set_setting("bump_folder", str(SP / "img2_folder"))
import accounts, browser_poster as B
B._pause = lambda *a, **k: None
from fastapi.testclient import TestClient
import main
c = TestClient(main.app)
LOG = SP / "mockfb_log.jsonl"
def mode(**kw): urllib.request.urlopen(urllib.request.Request("http://localhost:8098/mockmode", data=json.dumps(kw).encode(), method="POST"))
def last_rec():
    rs = [json.loads(l) for l in LOG.read_text().splitlines() if '"/record"' in l]
    return rs[-1] if rs else {}
sid = c.post("/api/sales", json={"name": "Linh", "fb_name": "Linh Nguyễn"}).json()["id"]; aid = accounts.of_sale(sid)[0]["id"]
from playwright.sync_api import sync_playwright
with sync_playwright() as pw:
    ctx = B._launch(pw, aid, headless=True); pg = ctx.new_page(); pg.goto("http://localhost:8098/setlogin"); ctx.close()
G = {u: db.run("INSERT INTO groups(name, url, created_at) VALUES (?,?,?)", (u, "http://localhost:8098/groups/" + u, db.now())) for u in ("modern", "real", "abc")}
k = [0]
def run(g, label):
    k[0] += 1
    pid = db.run("""INSERT INTO posts(agent_id, target_type, group_id, title, content, status, account_id, sale_id, scheduled_for, created_at)
                    VALUES ('lan','group',?,?,?,'scheduled',?,?,?,?)""", (G[g], f"Bài {k[0]}", f"Trà gừng mật ong sỉ tận xưởng số {k[0]} {os.urandom(3).hex()}\\nInbox Zalo", aid, sid, db.now()[:16], db.now()))
    n0 = len(LOG.read_text().splitlines())
    with sync_playwright() as pw: B._job_post(pw, aid, pid, False)
    new = [json.loads(l) for l in LOG.read_text().splitlines()[n0:] if '"/record"' in l]
    r = db.one("SELECT status, images_used, error FROM posts WHERE id=?", (pid,))
    print(f"{label:46} {r['status']:8} | Facebook nhận: {('bài có ' + str(new[-1]['files']) + ' ảnh') if new else 'không có bài'} | ảnh ghi: {len(json.loads(r['images_used'] or '[]'))} | {(r['error'] or '')[:80]}")
mode(graphql="url", pending=False, dropzone=False)
run("modern", "FB mới: bấm Ảnh/video mở hộp chọn tệp")
mode(dropzone=True)
run("modern", "FB mới: bấm Ảnh/video hiện ô 'Thêm ảnh/video'")
mode(dropzone=False)
run("real", "FB kiểu Ảnh/video tạo ô tệp trong hộp")
run("abc", "hộp soạn đơn giản (ô tệp có sẵn)")
mode(nopreview=True)
run("modern", "FB không hiện ảnh xem trước -> KHÔNG đăng")
mode(nopreview=False)
print("sổ lỗi:", [e["title"] for e in db.q("SELECT title FROM errors")])
# lần 2 cùng bài: dừng hẳn
pid = db.one("SELECT id FROM posts WHERE status='approved' ORDER BY id DESC LIMIT 1")["id"]
mode(nopreview=True)
db.run("UPDATE posts SET status='scheduled', account_id=?, sale_id=?, scheduled_for=? WHERE id=?", (aid, sid, db.now()[:16], pid))
with sync_playwright() as pw: B._job_post(pw, aid, pid, False)
mode(nopreview=False)
r = db.one("SELECT status, img_fails, screenshot, error FROM posts WHERE id=?", (pid,)); print("lần 2:", r["status"], r["img_fails"], r["screenshot"], r["error"][:70])
print("ảnh chụp có:", (db.SHOTS_DIR / Path(r["screenshot"]).name).exists())
c.post(f"/api/posts/{pid}/retry"); print("đưa về hàng đợi:", db.one("SELECT status, img_fails FROM posts WHERE id=?", (pid,)))

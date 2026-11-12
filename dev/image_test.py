"""Bài đăng bắt buộc có ảnh: không có ảnh thì không đăng."""
import os, sys, time, json, shutil
os.environ["FB_BASE_URL"] = "http://localhost:8098"
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "backend"))
from pathlib import Path
SP = Path(__import__("os").environ.get("MT_WORK") or Path(__file__).resolve().parent / "work")
import db
db.DB_PATH = SP / "img2.db"; db.DB_PATH.unlink(missing_ok=True)
db.PROFILES_DIR = SP / "img2_profiles"; shutil.rmtree(db.PROFILES_DIR, ignore_errors=True); db.PROFILES_DIR.mkdir()
db.SHOTS_DIR = SP / "img2_shots"; db.SHOTS_DIR.mkdir(exist_ok=True)
db.init(); db.set_setting("browser_headless", "1"); db.set_setting("bump_folder", "")
import accounts, browser_poster as B, workflows, media_folder, facebook
B._pause = lambda *a, **k: None
from fastapi.testclient import TestClient
import main
c = TestClient(main.app)
LOG = SP / "mockfb_log.jsonl"
def recs(): return len(LOG.read_text().strip().splitlines()) if LOG.exists() else 0
print("mặc định bắt buộc ảnh:", db.get_settings().get("require_images"))
sid = c.post("/api/sales", json={"name": "Linh", "fb_name": "Linh Nguyễn"}).json()["id"]
aid = accounts.of_sale(sid)[0]["id"]
from playwright.sync_api import sync_playwright
with sync_playwright() as pw:
    ctx = B._launch(pw, aid, headless=True); pg = ctx.new_page(); pg.goto("http://localhost:8098/setlogin"); ctx.close()
pid_prod = db.run("INSERT INTO products(name, category, created_at) VALUES ('Trà gừng','Trà túi lọc',?)", (db.now(),))
db.run("UPDATE products SET image_folder='' WHERE id=?", (pid_prod,))
gid = db.run("INSERT INTO groups(name, url, created_at) VALUES ('Nhóm thật','http://localhost:8098/groups/real',?)", (db.now(),))
def new_post():
    return db.run("""INSERT INTO posts(agent_id, product_id, target_type, group_id, title, content, hashtags, status, created_at)
                     VALUES ('lan',?,'group',?,'Trà gừng sỉ','Trà gừng mật ong giá sỉ tận xưởng, inbox nhé','#tra','approved',?)""",
                  (pid_prod, gid, db.now()))
p1 = new_post()
# 1. xếp lịch: bài thiếu ảnh không được xếp
print("lọc bài có ảnh:", [p["id"] for p in workflows.with_images(db.q("SELECT * FROM posts WHERE id=?", (p1,)))],
      "| lỗi ghi:", db.one("SELECT error FROM posts WHERE id=?", (p1,))["error"][:90])
# 2. API đăng ngay -> 400
r = c.post(f"/api/posts/{p1}/run", json={"account_id": aid, "dry_run": False}); print("đăng ngay:", r.status_code, r.json().get("detail", "")[:80])
# 3. job chạy thẳng (bài đã nằm trong lịch từ trước) -> không đăng
db.run("UPDATE posts SET status='scheduled', account_id=?, sale_id=? WHERE id=?", (aid, sid, p1))
n0 = recs()
with sync_playwright() as pw: B._job_post(pw, aid, p1, False)
print("job thiếu ảnh:", db.one("SELECT status, account_id, error FROM posts WHERE id=?", (p1,)), "| FB nhận bài:", recs() - n0)
print("sổ lỗi:", [e["title"] for e in db.q("SELECT title FROM errors")])
# 4. có thư mục ảnh -> đăng kèm ảnh
d = SP / "img2_folder"; shutil.rmtree(d, ignore_errors=True); d.mkdir()
for f in sorted((SP / "pubimg").glob("*.png"))[:3]: shutil.copy(f, d / f.name)
db.run("UPDATE products SET image_folder=? WHERE id=?", (str(d), pid_prod)); media_folder._count_cache.clear()
print("lọc lại:", [p["id"] for p in workflows.with_images(db.q("SELECT * FROM posts WHERE id=?", (p1,)))], db.one("SELECT error FROM posts WHERE id=?", (p1,)))
print("API posts img_count:", [(x["id"], x.get("img_count"), x.get("img_required")) for x in c.get("/api/posts").json()])
db.run("UPDATE posts SET status='scheduled', account_id=?, sale_id=? WHERE id=?", (aid, sid, p1))
n0 = recs()
with sync_playwright() as pw: B._job_post(pw, aid, p1, False)
last = json.loads(LOG.read_text().strip().splitlines()[-1]) if recs() > n0 else {}
print("có ảnh:", db.one("SELECT status, images_used, error FROM posts WHERE id=?", (p1,))["status"], "| FB nhận:", recs() - n0, "bài, files =", last.get("files"))
# 5. đính ảnh thất bại -> hủy, không đăng
p2 = new_post(); db.run("UPDATE posts SET status='scheduled', account_id=?, sale_id=? WHERE id=?", (aid, sid, p2))
orig = B._attach_images; B._attach_images = lambda *a, **k: []
n0 = recs()
with sync_playwright() as pw: B._job_post(pw, aid, p2, False)
B._attach_images = orig
print("đính ảnh lỗi:", db.one("SELECT status, error FROM posts WHERE id=?", (p2,)), "| FB nhận:", recs() - n0)
# 6. Fanpage
calls = []
class R:
    def __init__(s, d): s.d = d; s.status_code = 200; s.text = json.dumps(d)
    def json(s): return s.d
def fake_post(url, data=None, files=None, timeout=None):
    calls.append((url.split("/")[-1], {k: v for k, v in (data or {}).items() if k != "access_token"}, bool(files)))
    return R({"id": f"x{len(calls)}"})
facebook.httpx.post = fake_post
db.set_setting("fb_page_id", "123"); db.set_setting("fb_page_token", "tok")
pp = db.run("""INSERT INTO posts(agent_id, product_id, target_type, title, content, status, created_at) VALUES ('lan',NULL,'page','Fanpage','Bài fanpage','approved',?)""", (db.now(),))
r = c.post(f"/api/posts/{pp}/publish-page"); print("Fanpage không ảnh:", r.status_code, r.json().get("detail", "")[:70], "| gọi Graph:", len(calls))
db.run("UPDATE posts SET product_id=? WHERE id=?", (pid_prod, pp))
r = c.post(f"/api/posts/{pp}/publish-page").json(); print("Fanpage có ảnh:", r.get("ok"), [(u, d.get("published"), [k for k in d if k.startswith("attached")], f) for u, d, f in calls])
# 7. sếp tắt bắt buộc -> đăng chữ được
db.set_setting("require_images", "0"); db.run("UPDATE products SET image_folder='' WHERE id=?", (pid_prod,)); media_folder._count_cache.clear()
p3 = new_post(); print("tắt bắt buộc, lọc:", [p["id"] for p in workflows.with_images(db.q("SELECT * FROM posts WHERE id=?", (p3,)))])
print("lỗi khác:", [e["title"] for e in db.q("SELECT title FROM errors")])

"""Ảnh tổng hợp nhà máy: tích thì mọi bài chỉ lấy ảnh ở đó."""
import os, sys, json, shutil
os.environ["FB_BASE_URL"] = "http://localhost:8098"
sys.path.insert(0, "/home/claude/ai-sales-company/backend")
from pathlib import Path
SP = Path(__import__("os").environ.get("MT_WORK") or Path(__file__).resolve().parent / "work")
import db
db.DB_PATH = SP / "gen.db"; db.DB_PATH.unlink(missing_ok=True)
db.PROFILES_DIR = SP / "gen_profiles"; shutil.rmtree(db.PROFILES_DIR, ignore_errors=True); db.PROFILES_DIR.mkdir()
db.SHOTS_DIR = SP / "gen_shots"; db.SHOTS_DIR.mkdir(exist_ok=True)
db.init(); db.set_setting("browser_headless", "1"); db.set_setting("bump_folder", "")
import accounts, browser_poster as B, media_folder as M, workflows
B._pause = lambda *a, **k: None
from fastapi.testclient import TestClient
import main
c = TestClient(main.app)
src = sorted((SP / "pubimg").glob("*.png"))
def folder(name, n):
    d = SP / "gen_dirs" / name; shutil.rmtree(d, ignore_errors=True); d.mkdir(parents=True)
    for i in range(n): shutil.copy(src[i % len(src)], d / f"{name}_{i}.png")
    return str(d)
A = c.post("/api/products", json={"name": "Trà gừng", "image_folder": folder("tragung", 3)}).json()["id"]
Bp = c.post("/api/products", json={"name": "Ngũ cốc", "image_folder": folder("nguccoc", 3)}).json()["id"]
G = c.post("/api/products", json={"name": "Tổng hợp sản phẩm nhà máy", "image_folder": folder("tonghop", 6), "is_general": True}).json()
print("tạo mục tổng hợp:", G["is_general"], G["folder"]["count"], "ảnh")
post = {"id": 0, "product_id": A, "group_id": None}
picks = set()
for _ in range(20):
    imgs, _w = M.pick_for_post(post); picks |= {Path(i).parent.name for i in imgs}
print("bài Trà gừng lấy ảnh ở:", picks, "| up bài lấy ở:", Path(M.pick({"id": 0, "product_id": Bp})).parent.name)
print("GET thứ tự:", [(p["name"], p["is_general"]) for p in c.get("/api/products").json()])
# chỉ 1 mục tổng hợp
c.patch(f"/api/products/{Bp}", json={"is_general": True})
print("tích Ngũ cốc:", [(p["name"], p["is_general"]) for p in c.get("/api/products").json()])
print("bài Trà gừng giờ lấy ở:", {Path(i).parent.name for i in M.pick_for_post(post)[0]})
c.patch(f"/api/products/{Bp}", json={"is_general": False})
print("bỏ tích:", {Path(i).parent.name for i in M.pick_for_post(post)[0]})
# mục tổng hợp chưa có ảnh -> không lấy ảnh sản phẩm khác, không đăng
c.patch(f"/api/products/{G['id']}", json={"is_general": True, "image_folder": ""})
print("tổng hợp chưa có ảnh:", M.pick_for_post(post)[0], "|", M.missing(post)[:110])
print("posts API img_count:", (lambda: (db.run("INSERT INTO posts(agent_id, product_id, target_type, title, content, status, created_at) VALUES ('lan',?,'group','x','y','approved',?)", (A, db.now())), [x.get("img_count") for x in c.get("/api/posts").json()])[1])())
c.patch(f"/api/products/{G['id']}", json={"image_folder": str(SP / "gen_dirs" / "tonghop")})
print("điền lại thư mục:", [x.get("img_count") for x in c.get("/api/posts").json()])
# đăng thật trên Facebook giả lập
sid = c.post("/api/sales", json={"name": "Linh", "fb_name": "Linh Nguyễn"}).json()["id"]; aid = accounts.of_sale(sid)[0]["id"]
from playwright.sync_api import sync_playwright
with sync_playwright() as pw:
    ctx = B._launch(pw, aid, headless=True); pg = ctx.new_page(); pg.goto("http://localhost:8098/setlogin"); ctx.close()
gid = db.run("INSERT INTO groups(name, url, created_at) VALUES ('Nhóm thật','http://localhost:8098/groups/real',?)", (db.now(),))
pid = db.run("""INSERT INTO posts(agent_id, product_id, target_type, group_id, title, content, status, account_id, sale_id, created_at)
                VALUES ('lan',?,'group',?,'Ngũ cốc sỉ','Ngũ cốc giá sỉ tận xưởng','scheduled',?,?,?)""", (Bp, gid, aid, sid, db.now()))
with sync_playwright() as pw: B._job_post(pw, aid, pid, False)
r = db.one("SELECT status, images_used FROM posts WHERE id=?", (pid,))
print("đăng bài Ngũ cốc:", r["status"], {Path(i).parent.name for i in json.loads(r["images_used"] or "[]")})
print("nhật ký:", [a["detail"][:90] for a in db.q("SELECT detail FROM activity WHERE action='Ảnh đăng bài'")])
print("lỗi:", [e["title"] for e in db.q("SELECT title FROM errors")])

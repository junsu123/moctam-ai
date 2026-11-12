import sys, shutil, random
import os; sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "backend"))
from pathlib import Path
from datetime import timedelta
SP = Path(__import__("os").environ.get("MT_WORK") or Path(__file__).resolve().parent / "work")
import db
db.DB_PATH = SP / "posted.db"; db.DB_PATH.unlink(missing_ok=True)
db.PROFILES_DIR = SP / "posted_profiles"; shutil.rmtree(db.PROFILES_DIR, ignore_errors=True); db.PROFILES_DIR.mkdir()
db.init()
from fastapi.testclient import TestClient
import main, accounts
c = TestClient(main.app)
s1 = c.post("/api/sales", json={"name": "Linh", "fb_name": "Linh Nguyễn"}).json()["id"]; a1 = accounts.of_sale(s1)[0]["id"]
s2 = c.post("/api/sales", json={"name": "Phương", "fb_name": "Phương Sỉ"}).json()["id"]; a2 = accounts.of_sale(s2)[0]["id"]
gs = [db.run("INSERT INTO groups(name, url, created_at) VALUES (?,?,?)", (f"Nhóm {n}", f"https://www.facebook.com/groups/g{n}", db.now())) for n in ("Trà sỉ", "Mẹ bỉm", "Ngũ cốc")]
random.seed(1)
st = ["found"] * 6 + ["not_found", "pending", "removed", None]
for i in range(57):
    t = (db.clock() - timedelta(hours=i * 9)).strftime("%Y-%m-%d %H:%M:%S")
    a, s = (a1, s1) if i % 2 else (a2, s2)
    db.run("""INSERT INTO posts(agent_id, target_type, group_id, title, content, status, posted_at, account_id, sale_id, permalink_status,
              posted_url, comments, leads, images_used, created_at) VALUES ('lan','group',?,?,?,'posted',?,?,?,?,?,?,?,?,?)""",
           (gs[i % 3], f"Bài sỉ số {i}", f"Trà gừng mật ong {'gia công' if i % 5 == 0 else 'sỉ'} {i}", t, a, s, st[i % 10],
            f"https://www.facebook.com/groups/g/posts/{9000+i}", i % 7, i % 4 == 0, '["a.jpg","b.jpg"]', t))
db.run("INSERT INTO posts(agent_id, target_type, title, content, status, created_at) VALUES ('lan','group','nháp','x','draft',?)", (db.now(),))
r = c.get("/api/posts/posted").json(); print("trang 1:", r["page"], r["pages"], r["total"], len(r["items"]), r["stats"])
print("  nhóm:", [(g["name"], g["n"]) for g in r["groups"]], "| nick:", [(a["sale_name"], a["name"], a["n"]) for a in r["accounts"]])
r = c.get("/api/posts/posted?page=3&size=20").json(); print("trang 3:", r["page"], len(r["items"]), r["items"][0]["title"])
r = c.get("/api/posts/posted?page=99").json(); print("trang quá:", r["page"])
r = c.get(f"/api/posts/posted?group_id={gs[1]}&link=missing").json(); print("lọc nhóm+chưa link:", r["total"], {x["permalink_status"] for x in r["items"]})
r = c.get(f"/api/posts/posted?account_id={a1}&days=7").json(); print("nick Linh 7 ngày:", r["total"])
r = c.get("/api/posts/posted?q=gia công").json(); print("tìm 'gia công':", r["total"])
r = c.get("/api/posts/posted?q=%2312").json(); print("tìm #12:", [x["title"] for x in r["items"]][:3])
r = c.get("/api/posts/posted?sort=leads&size=5").json(); print("nhiều khách:", [(x["leads"], x["comments"]) for x in r["items"]])

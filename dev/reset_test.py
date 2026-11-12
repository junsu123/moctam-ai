"""Làm lại bài đăng: xóa bài chưa đăng, giữ bài đã đăng/đang đăng, Lan viết lại."""
import os, sys, time, shutil
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "backend"))
from pathlib import Path
SP = Path(__import__("os").environ.get("MT_WORK") or Path(__file__).resolve().parent / "work")
import db
db.DB_PATH = SP / "reset.db"; db.DB_PATH.unlink(missing_ok=True)
db.PROFILES_DIR = SP / "reset_profiles"; shutil.rmtree(db.PROFILES_DIR, ignore_errors=True); db.PROFILES_DIR.mkdir()
db.init(); db.set_setting("bump_folder", str(SP / "img2_folder"))
from fastapi.testclient import TestClient
import main, workflows
c = TestClient(main.app)
for st, n in [("approved", 3), ("scheduled", 4), ("failed", 2), ("draft", 2), ("posted", 2), ("posting", 1)]:
    for i in range(n):
        pid = db.run("""INSERT INTO posts(agent_id, target_type, title, content, status, scheduled_for, created_at) VALUES ('lan','group',?,?,?,?,?)""",
                     (f"{st} {i}", f"Nội dung {st} {i}", st, db.now()[:16] if st == "scheduled" else None, db.now()))
        db.run("INSERT INTO feedback(post_id, kind, created_at) VALUES (?, 'approve', ?)", (pid, db.now()))
        if st == "failed":
            db.run("INSERT INTO errors(source, title, ref_type, ref_id, status, created_at) VALUES ('post','Đăng lỗi','post',?, 'new', ?)", (str(pid), db.now()))
print("xem trước:", c.get("/api/posts/reset").json())
before = len(db.q("SELECT id FROM posts"))
r = c.post("/api/posts/reset", json={"kinds": ["approved", "scheduled", "failed"], "rewrite": 4, "plan": True}).json()
print("làm lại:", r)
time.sleep(4)
print("còn lại:", {x["status"]: x["n"] for x in db.q("SELECT status, COUNT(*) n FROM posts GROUP BY status")})
print("bài mới:", [(p["status"], p["source"], p["review_score"]) for p in db.q("SELECT * FROM posts WHERE id > 14")])
print("feedback mồ côi:", db.one("SELECT COUNT(*) n FROM feedback WHERE post_id NOT IN (SELECT id FROM posts)")["n"],
      "| lỗi bài đã xóa:", [e["status"] for e in db.q("SELECT status FROM errors WHERE ref_type='post'")])
print("nhật ký:", [a["detail"] for a in db.q("SELECT detail FROM activity WHERE action='Làm lại bài đăng'")])
r = c.post("/api/posts/reset", json={"kinds": ["draft"], "rewrite": 0}).json(); print("chỉ xóa chờ duyệt:", r)
print("lỗi:", [e["title"] for e in db.q("SELECT title FROM errors WHERE source!='post'")])

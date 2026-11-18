"""Màn hình Bình luận: Bảo xếp bình luận hằng ngày cho từng bài đã đăng; sếp xem, sửa, viết lại, hủy, thử lại (không cần Chrome)."""
import os, sys, shutil
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "backend"))
from pathlib import Path
SP = Path(os.environ.get("MT_WORK") or Path(__file__).resolve().parent / "work")
import db
db.DB_PATH = SP / "comments.db"; db.DB_PATH.unlink(missing_ok=True)
img = SP / "comments_img"; shutil.rmtree(img, ignore_errors=True); img.mkdir(parents=True)
(img / "a.jpg").write_bytes(b"\xff\xd8\xff\xe0" + b"0" * 200)
db.init(); db.set_setting("bump_folder", str(img)); db.set_setting("anthropic_api_key", "")
from fastapi.testclient import TestClient
import main, accounts
c = TestClient(main.app)
sid = c.post("/api/sales", json={"name": "Linh", "fb_name": "Linh Nguyễn"}).json()["id"]
aid = accounts.of_sale(sid)[0]["id"]
db.run("UPDATE fb_accounts SET login_status='ok', active_from='00:00', active_to='23:59', created_at='2025-01-01 00:00:00' WHERE id=?", (aid,))
db.run("UPDATE sales SET auto_post=1 WHERE id=?", (sid,))
add = lambda hours, **kw: db.run(
    """INSERT INTO posts(title, content, target_type, status, sale_id, account_id, posted_at, posted_url, permalink_status, bump_enabled, created_at)
       VALUES (?, 'x', 'group', 'posted', ?, ?, datetime('now','localtime',?), 'http://x/p', 'found', ?, ?)""",
    (kw.get("t", "bài"), sid, aid, f"-{hours} hours", kw.get("on", 1), db.now()))
ok1, ok2, new, old, off = add(30, t="A"), add(50, t="B"), add(2, t="mới"), add(24 * 20, t="cũ"), add(30, t="tắt", on=0)
d = c.get("/api/comments").json()
print("trước giờ xếp:", {p["title"]: p["reason"][:20] for p in d["posts"]})
import workflows
n = workflows.plan_bumps(force=True)
d = c.get("/api/comments").json()
print("xếp:", n, "| đủ bài:", d["covered"], "/", d["eligible"], "| đếm:", d["counts"], "| nick:", d["nicks"])
assert n == 2 and d["covered"] == 2 and d["counts"]["scheduled"] == 2
assert {p["title"] for p in d["posts"] if p["reason"]} == {"mới", "tắt"}  # bài quá cũ không còn hiện
b1, b2 = d["items"][0]["id"], d["items"][1]["id"]
r = c.put(f"/api/comments/{b1}", json={"text": "Còn hàng sỉ trà gừng nhé cả nhà. Cần hàng liên hệ Zalo 0386992326"})
print("sửa:", r.status_code, r.json()["text"][:40])
r2 = c.post(f"/api/comments/{b2}/rewrite"); print("viết lại:", r2.status_code, r2.json()["text"][:40])
r3 = c.post(f"/api/comments/{b2}/cancel"); print("hủy:", r3.json()["status"], r3.json()["error"])
print("sửa lượt đã hủy:", c.put(f"/api/comments/{b2}", json={"text": "abc abc abc"}).json())
r4 = c.post(f"/api/comments/{b2}/retry"); print("thử lại:", r4.status_code, r4.json()["status"])
print("thử lại lần 2 (1 lần/ngày):", c.post(f"/api/comments/{b2}/retry").json())
print("lọc chờ gửi:", len(c.get("/api/comments?status=scheduled").json()["items"]), "| tìm 'trà gừng':",
      len(c.get("/api/comments?q=trà gừng").json()["items"]))
assert r.status_code == 200 and r3.json()["status"] == "skipped" and r4.json()["status"] == "scheduled"
print("OK màn hình bình luận")

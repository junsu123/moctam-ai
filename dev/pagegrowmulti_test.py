"""Nuôi nhiều Trang: chuyển Trang cũ (cài đặt page_url) sang danh sách, thêm Trang, Nhi viết cho từng Trang, duyệt xong xếp đăng (không cần Chrome)."""
import os, sys
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "backend"))
from pathlib import Path
SP = Path(os.environ.get("MT_WORK") or Path(__file__).resolve().parent / "work")
import db
db.DB_PATH = SP / "pagegrowmulti.db"; db.DB_PATH.unlink(missing_ok=True)
db.init(); db.set_setting("anthropic_api_key", "")
from fastapi.testclient import TestClient
import main, accounts, page_grow as G, page_brain as PB, trend_pages as T
c = TestClient(main.app)
ok = []
def chk(name, cond, extra=""):
    ok.append(bool(cond)); print(("   ✓ " if cond else "   ✗ ") + name, extra)
sid = c.post("/api/sales", json={"name": "Linh", "fb_name": "Linh Nguyễn"}).json()["id"]
aid = accounts.of_sale(sid)[0]["id"]
db.run("UPDATE fb_accounts SET login_status='ok' WHERE id=?", (aid,))
# bản cũ: 1 Trang trong cài đặt, có bài cũ và số người theo dõi
db.set_setting("page_url", "https://facebook.com/moctamvn"); db.set_setting("page_admin_account", str(aid)); db.set_setting("page_grow_migrated", "")
old = db.run("INSERT INTO posts(target_type, content, status, source, page_topic, created_at) VALUES ('page', 'bài cũ', 'posted', 'page_grow', 'recipe', ?)", (db.now(),))
db.run("INSERT INTO page_stats(day, followers, created_at) VALUES (?, 900, ?)", (db.today(), db.now()))
d = c.get("/api/page-grow").json()
pg1 = d["pages"][0] if d["pages"] else {}
chk("Trang cũ tự vào danh sách, giữ link, nick, bài cũ, người theo dõi", len(d["pages"]) == 1 and pg1["url"].endswith("moctamvn") and pg1["admin_account_id"] == aid
    and db.one("SELECT fb_page_ref FROM posts WHERE id=?", (old,))["fb_page_ref"] == pg1["id"]
    and db.one("SELECT followers FROM page_followers WHERE page_id=?", (pg1["id"],))["followers"] == 900, d["pages"])
e = c.post("/api/page-grow/pages", json={"name": "Trà Ngon Mỗi Ngày", "url": "https://facebook.com/trangon"})
chk("thêm Trang thiếu nick quản trị bị từ chối", e.status_code == 400, e.text[:80])
d = c.post("/api/page-grow/pages", json={"name": "Trà Ngon Mỗi Ngày", "url": "https://facebook.com/trangon", "admin_account_id": aid,
                                         "posts_per_day": 2, "times": "23:58,23:59", "niche": "trà thảo mộc", "keywords": "trà gừng, trà sen"}).json()
chk("thêm Trang thứ hai: đủ link, nick, từ khóa", len(d["pages"]) == 2 and d["pages"][1]["keywords"] == "trà gừng, trà sen" and d["pages"][1]["ready"] is None, d["pages"][1])
e = c.post("/api/page-grow/pages", json={"name": "Trà Ngon Mỗi Ngày", "url": "https://facebook.com/x", "admin_account_id": aid})
chk("không thêm trùng tên Trang", e.status_code == 400)
p2 = d["pages"][1]
db.run("UPDATE fb_pages SET times='23:58,23:59' WHERE id=?", (pg1["id"],))
db.set_setting("page_grow_planned", "")
n = G.plan_today(force=True)
rows = db.q("SELECT fb_page_ref, status, page_kw, agent_id FROM posts WHERE source='page_grow' AND id != ?", (old,))
chk("Nhi viết cho từng Trang theo số bài/ngày của Trang, chờ sếp duyệt", n == 3 and sum(r["fb_page_ref"] == p2["id"] for r in rows) == 2
    and sum(r["fb_page_ref"] == pg1["id"] for r in rows) == 1 and all(r["status"] == "page_review" for r in rows) and all(r["agent_id"] == "nhi" for r in rows), rows)
chk("bài Trang có từ khóa theo từ khóa sếp đặt", all(r["page_kw"] in ("trà gừng", "trà sen") for r in rows if r["fb_page_ref"] == p2["id"]))
q = c.get("/api/nhi-pages").json()
chk("hàng chờ duyệt chung ở Các Trang của Nhi, có cả Trang nuôi", len(q["queue"]) == 3 and {x["page_name"] for x in q["queue"]} == {pg1["name"], "Trà Ngon Mỗi Ngày"})
pid = q["queue"][0]["id"]
r = c.post(f"/api/nhi-pages/posts/{pid}/review", json={"action": "approve"}).json()
chk("duyệt bài nuôi Trang: xếp đăng luôn, không xin ảnh Telegram", r["status"] == "scheduled" and not r.get("img_req_msg"), r["status"])
chk("Trang nuôi không lẫn vào Trang xu hướng (lịch bài, chủ đề nóng)", not any(p["id"] in (pg1["id"], p2["id"]) for p in T.overview()["pages"])
    and T.plan_today(force=True) == 0)
c.put(f"/api/page-grow/pages/{p2['id']}", json={"posts_per_day": 1, "keywords": "trà gừng"})
c.post(f"/api/trends/pages/{p2['id']}/status", json={"status": "paused"})
d = c.get("/api/page-grow").json()
chk("sửa / tạm dừng một Trang: bài chưa đăng của Trang đó bị bỏ, Trang kia giữ nguyên", next(p for p in d["pages"] if p["id"] == p2["id"])["status"] == "paused"
    and not db.one("SELECT 1 FROM posts WHERE fb_page_ref=? AND status IN ('page_review','scheduled')", (p2["id"],))
    and db.one("SELECT 1 FROM posts WHERE fb_page_ref=? AND status IN ('page_review','scheduled')", (pg1["id"],)))
w = c.post("/api/page-grow/write", json={"page_id": pg1["id"]}).json()
chk("viết ngay 1 bài cho đúng Trang chọn", w["fb_page_ref"] == pg1["id"])
print(f"XONG {sum(ok)}/{len(ok)}" if all(ok) else f"CÓ LỖI {sum(ok)}/{len(ok)}")

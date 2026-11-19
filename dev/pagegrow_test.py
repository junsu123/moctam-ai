"""Nuôi Trang không dùng API (mockfb): Lan viết theo chủ đề 80/20, nick quản trị chuyển sang Trang đăng bài, chuyển về, đọc số liệu."""
import os, sys, time, json, shutil, urllib.request
os.environ["FB_BASE_URL"] = "http://localhost:8098"
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "backend"))
from pathlib import Path
from datetime import timedelta
SP = Path(os.environ.get("MT_WORK") or Path(__file__).resolve().parent / "work")
import db
db.DB_PATH = SP / "pagegrow.db"; db.DB_PATH.unlink(missing_ok=True)
db.PROFILES_DIR = SP / "pagegrow_profiles"; shutil.rmtree(db.PROFILES_DIR, ignore_errors=True); db.PROFILES_DIR.mkdir()
db.SHOTS_DIR = SP / "multi_shots"; db.SHOTS_DIR.mkdir(exist_ok=True)
db.init(); db.set_setting("browser_headless", "1"); db.set_setting("bump_folder", str(SP / "pubimg")); db.set_setting("anthropic_api_key", "")
mock = lambda path, d=None: urllib.request.urlopen(urllib.request.Request("http://localhost:8098" + path, data=json.dumps(d).encode() if d is not None else None,
                                                                          method="POST" if d is not None else "GET")).read().decode()
mock("/pageswitch", {"on": 0})
import accounts, browser_poster as B, page_grow
B._pause = lambda *a, **k: None
from fastapi.testclient import TestClient
import main
c = TestClient(main.app)
ok = []
def chk(name, cond, extra=""):
    ok.append(bool(cond)); print(("   ✓ " if cond else "   ✗ ") + name, extra)
sid = c.post("/api/sales", json={"name": "Linh", "fb_name": "Linh Nguyễn"}).json()["id"]
aid = accounts.of_sale(sid)[0]["id"]
from playwright.sync_api import sync_playwright
with sync_playwright() as pw:
    ctx = B._launch(pw, aid, headless=True); pg = ctx.new_page(); pg.goto("http://localhost:8098/setlogin"); ctx.close()
c.post(f"/api/accounts/{aid}/check"); time.sleep(1)
while B.busy(sid) or B.queued(sid): time.sleep(0.3)
chk("chưa cài thì báo thiếu link Trang", c.post("/api/page-grow/write").status_code == 400)
e = c.put("/api/page-grow/settings", json={"page_url": "trang mộc tâm"})
chk("link Trang sai bị từ chối", e.status_code == 400)
d = c.put("/api/page-grow/settings", json={"page_url": "http://localhost:8098/moctampage", "page_admin_account": aid}).json()
chk("đủ link Trang + nick quản trị: sẵn sàng", d["ready"] is None and d["nicks"], d["ready"])
p1 = c.post("/api/page-grow/write").json()
chk("bài đầu là giới thiệu sản phẩm (tỉ lệ 20% bán hàng), có Zalo, không có giá", p1["page_topic"] == "product" and "Zalo" in p1["content"]
    and "k/" not in p1["content"] and p1["account_id"] == aid and p1["status"] == "scheduled", p1["content"][:80])
p2 = page_grow.write()
chk("bài sau là bài có ích, không quảng cáo Zalo", p2["page_topic"] != "product" and "Zalo" not in p2["content"], p2["page_topic"])
db.run("UPDATE posts SET scheduled_for=? WHERE id=?", (db.clock().strftime("%Y-%m-%d %H:%M"), p1["id"]))
B.submit(sid, {"kind": "session", "account": aid}); time.sleep(1)
while B.busy(sid) or B.queued(sid): time.sleep(0.5)
po = db.one("SELECT * FROM posts WHERE id=?", (p1["id"],))
rec = [json.loads(l) for l in open(SP / "mockfb_log.jsonl", encoding="utf-8") if '"path": "/record"' in l][-1:]
chk("nick chuyển sang Trang, đăng dưới tên Trang", po["status"] == "posted" and rec and rec[0].get("where") == "/moctampage"
    and rec[0].get("as_page") is True, (po["status"], po["error"], rec))
chk("lưu được link bài Trang", "/moctampage/posts/pfbid" in (po["posted_url"] or ""), po["posted_url"])
chk("đăng xong chuyển về nick cá nhân", "Chuyển ngay" in mock("/moctampage") and not db.get_settings()["page_acting_aid"])
st = db.one("SELECT * FROM page_stats WHERE day=?", (db.today(),))
po = db.one("SELECT reactions, comments, shares FROM posts WHERE id=?", (p1["id"],))
chk("đọc được 1,2K người theo dõi và tương tác bài (12 cảm xúc, 3 bình luận, 2 chia sẻ)", st and st["followers"] == 1200
    and (po["reactions"], po["comments"], po["shares"]) == (12, 3, 2), (st, po))
# ca trước lỡ còn dưới tên Trang: ca sau chuyển về trước rồi mới đăng trang cá nhân
two_h = (db.clock() - timedelta(hours=2)).strftime("%Y-%m-%d %H:%M:%S")  # giãn cách giữa 2 bài của nick (Luật Facebook)
db.run("UPDATE posts SET posted_at=? WHERE id=?", (two_h, p1["id"])); db.run("UPDATE fb_accounts SET last_post_at=? WHERE id=?", (two_h, aid))
mock("/pageswitch", {"on": 1}); db.set_setting("page_acting_aid", str(aid))
q = db.run("INSERT INTO posts(content, target_type, status, scheduled_for, account_id, sale_id, product_id, created_at) VALUES (?, 'profile', 'scheduled', ?, ?, ?, 1, ?)",
           ("Bài trang cá nhân sau ca Trang", db.clock().strftime("%Y-%m-%d %H:%M"), aid, sid, db.now()))
B.submit(sid, {"kind": "session", "account": aid}); time.sleep(1)
while B.busy(sid) or B.queued(sid): time.sleep(0.5)
rec = [json.loads(l) for l in open(SP / "mockfb_log.jsonl", encoding="utf-8") if '"path": "/record"' in l][-1:]
chk("ca sau chuyển về trước, bài trang cá nhân đăng dưới tên nick", rec and rec[0].get("where") == "/me" and rec[0].get("as_page") is False, (rec, db.one("SELECT status, error, scheduled_for FROM posts WHERE id=?", (q,))))
d = c.get("/api/page-grow").json()
chk("màn Nuôi Page: người theo dõi, bài đã đăng, chủ đề", d["followers"] == 1200 and d["posted"] and d["posted"][0]["eng"] == 12 + 6 + 6
    and next(t for t in d["topics"] if t["topic"] == "product")["n"] == 1, (d["followers"], d["avg_eng"]))
chk("bỏ bài sắp đăng", not any(x["id"] == p2["id"] for x in c.post(f"/api/page-grow/{p2['id']}/skip").json()["upcoming"]))
# Trang xu hướng (Nhi): bài có ảnh sếp gửi qua Telegram, đăng lên đúng Trang của bài
db.run("UPDATE posts SET posted_at=? WHERE status='posted'", (two_h,)); db.run("UPDATE fb_accounts SET last_post_at=? WHERE id=?", (two_h, aid))
fp = db.run("INSERT INTO fb_pages(name, niche, url, admin_account_id, status, created_at) VALUES ('Góc nấu ăn', 'nấu ăn', 'http://localhost:8098/moctampage', ?, 'active', ?)", (aid, db.now()))
img = sorted((SP / "pubimg").glob("*.png"))[0]
tp = db.run("""INSERT INTO posts(agent_id, target_type, content, status, scheduled_for, account_id, sale_id, fb_page_ref, image_path, source, created_at)
               VALUES ('nhi', 'page', 'Bài Trang xu hướng thử nghiệm', 'scheduled', ?, ?, ?, ?, ?, 'trend_page', ?)""",
            (db.clock().strftime("%Y-%m-%d %H:%M"), aid, sid, fp, str(img), db.now()))
B.submit(sid, {"kind": "session", "account": aid}); time.sleep(1)
while B.busy(sid) or B.queued(sid): time.sleep(0.5)
rec = [json.loads(l) for l in open(SP / "mockfb_log.jsonl", encoding="utf-8") if '"path": "/record"' in l][-1:]
chk("bài Trang xu hướng: đăng dưới tên Trang của bài, đúng 1 ảnh sếp gửi", rec and rec[0].get("as_page") is True and rec[0].get("files") == 1
    and "xu hướng thử" in rec[0].get("text", "") and db.one("SELECT status FROM posts WHERE id=?", (tp,))["status"] == "posted"
    and "Chuyển ngay" in mock("/moctampage"), (rec, db.one("SELECT status, error FROM posts WHERE id=?", (tp,))))
import workflows
workflows.plan_bumps(force=True)
chk("không up bài Trang bằng nick cá nhân", not db.one("SELECT 1 FROM bumps WHERE post_id=?", (p1["id"],)))
print(("XONG" if all(ok) else "CÓ LỖI") + f" {sum(ok)}/{len(ok)}")

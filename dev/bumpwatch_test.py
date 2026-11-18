"""Bình luận tự động có ích không: đo lượt bình luận, ngừng bài không ra gì, nhóm xóa bình luận thì nghỉ (không cần Chrome)."""
import os, sys, shutil
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "backend"))
from pathlib import Path
from datetime import timedelta
SP = Path(os.environ.get("MT_WORK") or Path(__file__).resolve().parent / "work")
import db
db.DB_PATH = SP / "bumpwatch.db"; db.DB_PATH.unlink(missing_ok=True)
img = SP / "bumpwatch_img"; shutil.rmtree(img, ignore_errors=True); img.mkdir(parents=True)
(img / "a.jpg").write_bytes(b"\xff\xd8\xff\xe0" + b"0" * 200)
db.init(); db.set_setting("bump_folder", str(img)); db.set_setting("anthropic_api_key", "")
from fastapi.testclient import TestClient
import main, accounts, workflows, bump_watch, browser_poster as B
c = TestClient(main.app)
ok = []
def chk(name, cond, extra=""):
    ok.append(bool(cond)); print(("   ✓ " if cond else "   ✗ ") + name, extra)
sid = c.post("/api/sales", json={"name": "Linh", "fb_name": "Linh Nguyễn"}).json()["id"]
aid = accounts.of_sale(sid)[0]["id"]
db.run("UPDATE fb_accounts SET login_status='ok', active_from='00:00', active_to='23:59', created_at='2025-01-01 00:00:00' WHERE id=?", (aid,))
g1 = db.run("INSERT INTO groups(name, url, created_at) VALUES ('Nhóm Sỉ Trà', 'http://x/g1', ?)", (db.now(),))
g2 = db.run("INSERT INTO groups(name, url, created_at) VALUES ('Nhóm Hay Xóa', 'http://x/g2', ?)", (db.now(),))
ago = lambda **kw: (db.clock() - timedelta(**kw)).strftime("%Y-%m-%d %H:%M:%S")
def post(title, gid, hours=30):
    return db.run("""INSERT INTO posts(title, content, target_type, status, sale_id, account_id, group_id, posted_at, posted_url, permalink_status,
                     bump_enabled, created_at) VALUES (?, 'x', 'group', 'posted', ?, ?, ?, ?, ?, 'found', 1, ?)""",
                  (title, sid, aid, gid, ago(hours=hours), f"http://x/p/{title}", db.now()))
def done_bump(pid, days, before, text="Còn hàng sỉ trà gừng nhé cả nhà 👉 Cần hàng liên hệ Zalo 0386992326"):
    b = db.run("INSERT INTO bumps(post_id, sale_id, account_id, text, status, scheduled_for, done_at, created_at) VALUES (?,?,?,?, 'done', ?,?,?)",
               (pid, sid, aid, text, ago(days=days)[:16], ago(days=days), ago(days=days)))
    bump_watch.before(b, pid, before); return b
pA, pB, pC = post("A", g1, 100), post("B", g1, 100), post("C", g2, 100)

# 1) đo: B lần nào cũng có thêm bình luận + 1 khách; A 3 lượt không thêm gì
for d, n in ((3, 5), (2, 5), (1, 5)):
    b = done_bump(pA, d, n); bump_watch.observe(pA, n + 1)  # +1 = chính bình luận của mình
bb = done_bump(pB, 2, 4)
db.run("INSERT INTO leads(name, post_id, origin, created_at) VALUES ('Khách B', ?, 'comment', ?)", (pB, ago(days=1)))
bump_watch.observe(pB, 8)
r = db.one("SELECT gain_comments, gain_leads FROM bumps WHERE id=?", (bb,))
chk("đo được bài B thêm 3 bình luận, 1 khách", (r["gain_comments"], r["gain_leads"]) == (3, 1), r)
chk("bài A 3 lượt không thêm gì: thôi bình luận", bump_watch.stopped(db.one("SELECT * FROM posts WHERE id=?", (pA,))))
old = done_bump(pC, 3, 2); db.run("UPDATE posts SET comments=4 WHERE id=?", (pC,))
chk("lượt quá 48 giờ chưa vào lại vẫn được chấm", bump_watch.measure_stale() >= 1
    and db.one("SELECT gain_comments FROM bumps WHERE id=?", (old,))["gain_comments"] == 1)

# 2) xếp lịch: bỏ A, B (ra khách) lên trước
n = workflows.plan_bumps(force=True)
got = [x["post_id"] for x in db.q("SELECT post_id FROM bumps WHERE status='scheduled' ORDER BY scheduled_for")]
chk("xếp lịch bỏ bài A, bài B ra khách xếp đầu", pA not in got and got[:1] == [pB], got)
ov = c.get("/api/comments").json()
ra = next(p for p in ov["posts"] if p["id"] == pA)
chk("màn Bình luận ghi lý do bài A và nút bình luận tiếp", ra["stopped"] and "không thêm" in ra["reason"], ra["reason"])
e = ov["effect"]
chk("thẻ hiệu quả 30 ngày", e["done"] == 5 and e["measured"] == 5 and e["useful"] == 2 and e["leads"] == 1 and e["top"][0]["post_id"] == pB, e)
c.post(f"/api/comments/post/{pA}/resume")
chk("sếp cho bình luận tiếp: bài A hết bị ngừng", not bump_watch.stopped(db.one("SELECT * FROM posts WHERE id=?", (pA,))))

# 3) bình luận còn không: lượt ở nhóm 2 gửi 7 giờ trước, trang không còn câu của mình
db.run("DELETE FROM bumps WHERE status='scheduled'")
k1 = done_bump(pC, 0, 3); db.run("UPDATE bumps SET done_at=?, created_at=? WHERE id=?", (ago(hours=7), ago(days=1), k1))
k2 = done_bump(pB, 0, 3, "Mẻ bột ngũ cốc vừa đóng thùng 👉 Cần hàng liên hệ Zalo 0386992326"); db.run("UPDATE bumps SET done_at=? WHERE id=?", (ago(hours=7), k2))
db.run("UPDATE bumps SET checked_at=? WHERE id NOT IN (?,?)", (db.now(), k1, k2))  # các lượt cũ đã xem rồi
chk("chưa có việc khác thì không mở Chrome chỉ để xem", "checks" not in B.due_work(aid))
ids = bump_watch.due_checks(aid)
class Page:
    url = "http://x"
    def __init__(s): s.cur = ""
    def goto(s, u, **k): s.cur = u
    def wait_for_timeout(s, ms): pass
    def content(s): return s.inner_text("body")
    def inner_text(s, sel): return "Bài viết C · 5 bình luận" if s.cur.endswith("/C") else "Bài B ... Mẻ bột ngũ cốc vừa đóng thùng 👉 ..."
B._pause = lambda *a, **k: None
gone = bump_watch.check(Page(), aid, ids)
g = db.one("SELECT no_bump_until FROM groups WHERE id=?", (g2,))
chk("bình luận ở nhóm 2 bị xóa: nhóm nghỉ 30 ngày, nhóm 1 vẫn còn", gone == 1 and g["no_bump_until"]
    and not db.one("SELECT no_bump_until FROM groups WHERE id=?", (g1,))["no_bump_until"], (ids, gone, g))
workflows.plan_bumps(force=True)
got = [x["post_id"] for x in db.q("SELECT post_id FROM bumps WHERE status='scheduled'")]
chk("xếp lịch bỏ bài ở nhóm đang nghỉ", pC not in got, got)
ov = c.get("/api/comments").json()
chk("màn Bình luận có nhóm đang nghỉ và lý do", ov["effect"]["resting"] and ov["effect"]["removed"] == 1
    and next(p for p in ov["posts"] if p["id"] == pC)["resting"])
c.post(f"/api/comments/group/{g2}/resume")
chk("sếp cho bình luận lại nhóm", not bump_watch.resting_groups())
print(("XONG" if all(ok) else "CÓ LỖI") + f" {sum(ok)}/{len(ok)}")

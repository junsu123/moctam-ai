"""Dữ liệu không phình to: WAL + chỉ mục, mỗi đêm dọn nhật ký cũ / ảnh chụp / sao lưu / bộ nhớ Chrome, giữ dữ liệu agent dùng."""
import os, sys, shutil, time, json
from pathlib import Path
from datetime import timedelta
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "backend"))
SP = Path(os.environ.get("MT_WORK") or Path(__file__).resolve().parent / "work"); SP.mkdir(exist_ok=True)
import db
D = SP / "hk"; shutil.rmtree(D, ignore_errors=True); D.mkdir()
db.DB_PATH = D / "company.db"; db.DATA_DIR = D; db.SHOTS_DIR = D / "shots"; db.PROFILES_DIR = D / "profiles"
db.SHOTS_DIR.mkdir(); db.PROFILES_DIR.mkdir()
db.init(); db.set_setting("anthropic_api_key", "")
import housekeeping as H, ceo_orders, content_style, browser_poster as B

ok = []
def check(name, cond): ok.append(bool(cond)); print(("OK  " if cond else "LỖI ") + name)
ago = lambda d: (db.clock() - timedelta(days=d)).strftime("%Y-%m-%d %H:%M:%S")

check("ghi kiểu WAL", db.q("PRAGMA journal_mode")[0]["journal_mode"] == "wal")
idx = {r["name"] for r in db.q("SELECT name FROM sqlite_master WHERE type='index'")}
check("có chỉ mục cho truy vấn chạy thường xuyên", {"idx_posts_status", "idx_bumps_post", "idx_activity_at", "idx_usage_cov"} <= idx)

db.many("INSERT INTO activity(agent_id, action, detail, created_at) VALUES (?,?,?,?)",
        [("lan", "x", "cũ", ago(90))] * 12000 + [("lan", "x", "mới", ago(5))] * 3)
for st, d in (("sent", 200), ("draft", 200), ("skipped", 200), ("draft", 3)):
    db.run("INSERT INTO reply_tasks(post_url, status, created_at) VALUES (?,?,?)", (f"https://fb.com/p/{st}{d}", st, ago(d)))
db.run("INSERT INTO friend_suggestions(account_id, profile_url, status, created_at) VALUES (1,'u1','sent',?)", (ago(200),))
db.run("INSERT INTO friend_suggestions(account_id, profile_url, status, created_at) VALUES (1,'u2','suggested',?)", (ago(200),))
pid = db.run("INSERT INTO posts(content, status, posted_at, created_at, screenshot) VALUES ('bài cũ','posted',?,?,'/shots/post-1.png')", (ago(400), ago(400)))
db.run("INSERT INTO bumps(post_id, status, done_at, created_at) VALUES (?, 'done', ?, ?)", (pid, ago(300), ago(300)))
db.run("INSERT INTO usage(task, cost_usd, created_at) VALUES ('posts', 0.5, ?)", (ago(400),))

old = time.time() - 40 * 86400
for n in ("post-1.png", "err-1.png", "post-2.png"):
    (db.SHOTS_DIR / n).write_bytes(b"x" * 1000)
for n in ("post-1.png", "err-1.png"):
    os.utime(db.SHOTS_DIR / n, (old, old))
db.run("INSERT INTO errors(screen, title, status, screenshot, created_at, last_at) VALUES ('posts','lỗi','new','/shots/err-1.png',?,?)", (db.now(), db.now()))
(D / "backups").mkdir()
for i in range(7):
    f = D / "backups" / f"b{i}.db"; f.write_bytes(b"x"); os.utime(f, (old + i, old + i))
aid = db.run("INSERT INTO fb_accounts(name, login_status, created_at) VALUES ('Nick A','ok',?)", (db.now(),))
prof = B.profile_dir(aid); (prof / "Default" / "Cache").mkdir(parents=True); (prof / "Default" / "Cache" / "data_1").write_bytes(b"x" * 300000)
(prof / "Default" / "Cookies").write_bytes(b"phien-dang-nhap")
db.set_setting("chrome_cache_min_mb", "0")

r = H.run(force=True)
check("xóa nhật ký trên 60 ngày, giữ nhật ký mới", db.one("SELECT COUNT(*) n FROM activity WHERE detail='mới'")["n"] == 3 and not db.one("SELECT 1 FROM activity WHERE detail='cũ'") and r["rows"]["activity"] == 12000)
rt = {x["status"] for x in db.q("SELECT status FROM reply_tasks")}
check("câu đã gửi giữ (chống trả lời trùng), câu nháp/bỏ qua cũ xóa, nháp mới giữ",
      db.one("SELECT COUNT(*) n FROM reply_tasks")["n"] == 2 and rt == {"sent", "draft"})
check("lời mời đã gửi giữ (một người một nick), gợi ý cũ chưa mời xóa",
      [x["profile_url"] for x in db.q("SELECT profile_url FROM friend_suggestions")] == ["u1"])
check("bài đăng, chi phí AI luôn giữ", db.one("SELECT COUNT(*) n FROM posts")["n"] == 1 and db.one("SELECT COUNT(*) n FROM usage")["n"] == 1)
check("lượt up cũ xóa", db.one("SELECT COUNT(*) n FROM bumps")["n"] == 0)
check("ảnh chụp cũ xóa, ảnh của lỗi chưa xử lý và ảnh mới giữ",
      sorted(f.name for f in db.SHOTS_DIR.glob("*.png")) == ["err-1.png", "post-2.png"])
check("bài có ảnh đã xóa: bỏ đường dẫn ảnh (không hiện ảnh hỏng)", db.one("SELECT screenshot FROM posts WHERE id=?", (pid,))["screenshot"] is None)
check("giữ 5 bản sao lưu mới nhất", sorted(f.name for f in (D / "backups").glob("*.db")) == [f"b{i}.db" for i in range(2, 7)])
check("dọn bộ nhớ Chrome, giữ phiên đăng nhập", not (prof / "Default" / "Cache").exists() and (prof / "Default" / "Cookies").exists())
check("nén lại dữ liệu sau khi xóa nhiều", "vacuum_mb" in r.get("compact", {}))

B._busy = True
r = H.run()
check("sale đang làm: không đụng Chrome, không nén, hẹn đêm sau", "chrome" not in r and "later" in r)
B._busy = False

calls = []
H.run = lambda force=False: calls.append(force) or {"busy": True}
from datetime import datetime
db.set_setting("housekeeping_day", "")
H.tick(datetime(2030, 1, 1, 2, 0)); time.sleep(0.2)
check("chưa tới giờ dọn: chưa dọn", not calls)
H.tick(datetime(2030, 1, 1, 9, 0)); time.sleep(0.2); H.tick(datetime(2030, 1, 1, 9, 1)); time.sleep(0.2)
check("máy tắt đêm: dọn lúc bật máy, mỗi ngày một lần", calls == [False])

ceo_orders._bg = lambda fn, *a: fn(*a)
said = []; ceo_orders.followup = lambda t, via="web": said.append(t)
H.run = lambda force=False: {"rows": {"activity": 5}, "shots": {"files": 1}, "backups": {"files": 0}, "freed_mb": 3.2}
rep = ceo_orders.handle("dữ liệu có phình to không, dung lượng bao nhiêu")["reply"]
check("hỏi CEO dung lượng: báo số MB", "cơ sở dữ liệu" in rep and "MB" in rep)
ceo_orders.handle("dọn dẹp dữ liệu giúp anh")
check("bảo CEO dọn dữ liệu: dọn và báo lại", said and "5 dòng" in said[-1])

db.run("INSERT INTO content_library(post_id, status, leads, comments, created_at) VALUES (?, 'approved', 0, 0, ?)", (pid, db.now()))
db.run("UPDATE posts SET leads=3 WHERE id=?", (pid,))
n = []; om = db.many; db.many = lambda sql, rows: n.append(len(list(rows))) or 0
content_style.refresh_quality(); db.many = om
check("kho bài: chỉ ghi dòng có đổi, ghi một lần", n == [1])
print(f"XONG {sum(ok)}/{len(ok)}")

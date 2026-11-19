"""Đo hiệu suất trên dữ liệu giả lập lớn (1 năm, 25 nick): thời gian 1 lượt lịch tự động, các API giao diện gọi liên tục,
số lần đọc cài đặt. Chạy: python3 dev/perf.py  (dữ liệu ở dev/work/perf.db, tạo một lần, lần sau dùng lại)."""
import os, sys, time, random
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "backend"))
from pathlib import Path
from datetime import datetime, timedelta
SP = Path(os.environ.get("MT_WORK") or Path(__file__).resolve().parent / "work"); SP.mkdir(exist_ok=True)
import db
db.DB_PATH = SP / "perf.db"
fresh = not db.DB_PATH.exists()
db.init(); db.set_setting("anthropic_api_key", ""); db.set_setting("browser_headless", "1")
if fresh:
    t0 = time.time(); now = datetime.now()
    con = db.conn() if hasattr(db, "conn") else None
    sids = [db.run("INSERT INTO sales(name, fb_name, status, created_at) VALUES (?,?, 'active', ?)", (f"Sale {i}", f"Nick {i}", db.now())) for i in range(5)]
    aids = [db.run("INSERT INTO fb_accounts(sale_id, name, login_status, enabled, position, created_at) VALUES (?,?, 'ok', 1, ?, '2025-01-01 00:00:00')",
                   (sids[i % 5], f"Nick {i}", i)) for i in range(25)]
    gids = [db.run("INSERT INTO groups(name, url, created_at) VALUES (?,?,?)", (f"Nhóm {i}", f"https://facebook.com/groups/g{i}", db.now())) for i in range(300)]
    ts = lambda d: (now - timedelta(days=d, minutes=random.randint(0, 1400))).strftime("%Y-%m-%d %H:%M:%S")
    rows = [(f"Bài {i}", "nội dung " * 40, "group", "posted", sids[i % 5], aids[i % 25], gids[i % 300], ts(i % 365), f"https://facebook.com/groups/g/posts/{i}",
             "found", random.randint(0, 9), ts(i % 365)) for i in range(9000)]
    db.many("""INSERT INTO posts(title, content, target_type, status, sale_id, account_id, group_id, posted_at, posted_url, permalink_status, comments, created_at)
               VALUES (?,?,?,?,?,?,?,?,?,?,?,?)""", rows) if hasattr(db, "many") else [db.run("""INSERT INTO posts(title, content, target_type, status, sale_id,
               account_id, group_id, posted_at, posted_url, permalink_status, comments, created_at) VALUES (?,?,?,?,?,?,?,?,?,?,?,?)""", r) for r in rows]
    for i in range(200000):
        db.run("INSERT INTO activity(agent_id, action, detail, created_at) VALUES (?,?,?,?)", ("lan", "Viết bài", f"Bài {i}", ts(i % 365))) if i < 0 else None
    import sqlite3
    c = sqlite3.connect(db.DB_PATH)
    c.executemany("INSERT INTO activity(agent_id, action, detail, created_at) VALUES (?,?,?,?)",
                  [(random.choice(["lan", "tuan", "bao", "sale-1"]), "Viết bài", f"Chi tiết {i}", ts(i % 365)) for i in range(200000)])
    c.executemany("INSERT INTO leads(name, phone, post_id, origin, status, created_at) VALUES (?,?,?,?,?,?)",
                  [(f"Khách {i}", f"09{i:08d}" if i % 3 else None, 1 + i % 9000, "comment", "new", ts(i % 365)) for i in range(6000)])
    c.executemany("INSERT INTO bumps(post_id, sale_id, account_id, text, status, done_at, created_at) VALUES (?,?,?,?,?,?,?)",
                  [(1 + i % 9000, sids[i % 5], aids[i % 25], "câu", "done", ts(i % 180), ts(i % 180)) for i in range(30000)])
    c.commit(); c.close()
    print(f"tạo dữ liệu {time.time() - t0:.1f}s")
calls = {"n": 0}
_q = db.q
def counted(sql, *a, **k):
    if "FROM settings" in sql: calls["n"] += 1
    return _q(sql, *a, **k)
db.q = counted
import scheduler, main
import browser_poster as B
B.submit = lambda *a, **k: None  # không mở Chrome khi đo
from fastapi.testclient import TestClient
c = TestClient(main.app)
def bench(name, fn, n=5):
    calls["n"] = 0; t = time.perf_counter()
    for _ in range(n): fn()
    dt = (time.perf_counter() - t) / n * 1000
    print(f"{name:34s} {dt:8.1f} ms/lần   đọc cài đặt {calls['n'] / n:6.1f} lần/lượt")
    return dt
bench("lịch tự động (_tick)", scheduler._tick, 3)
for p in ["/api/dashboard", "/api/agents", "/api/comments", "/api/nick-health", "/api/posts", "/api/leads"]:
    bench("GET " + p, lambda p=p: c.get(p), 5)
bench("trang giao diện (/)", lambda: c.get("/"), 5)
bench("dấu bản mới (_code_stamp)", main._code_stamp, 5)

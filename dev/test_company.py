"""Kiểm tra luật công ty bằng cách lùi ngày: KPI tháng, sa thải, giải thể, hết vốn, đơn hàng."""
import sys, types
from datetime import date, timedelta
from pathlib import Path
import os; sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "backend"))
SP = Path(__import__("os").environ.get("MT_WORK") or Path(__file__).resolve().parent / "work")
import db
db.DB_PATH = SP / "company.db"; db.DB_PATH.unlink(missing_ok=True); db.init()
import company as C
tg = []
C._tg = lambda t: tg.append(t)
ago = lambda n: (date.today() - timedelta(days=n)).isoformat()

def mk_sale(name):
    sid = db.run("INSERT INTO sales(name, fb_name, login_status, auto_post, created_at) VALUES (?,?,'ok',1,?)", (name, name + " nick", db.now()))
    return sid

def give_leads(sid, n, days_ago=5):
    pid = db.run("INSERT INTO posts(sale_id, status, posted_at, created_at) VALUES (?,'posted',?,?)", (sid, db.now(), db.now()))
    for i in range(n):
        db.run("INSERT INTO leads(name, phone, phone_at, post_id, status, created_at, updated_at) VALUES (?,?,?,?,'new',?,?)",
               (f"K{sid}-{i}", f"09{sid:02d}{i:06d}", ago(days_ago) + " 10:00:00", pid, db.now(), db.now()))

def work_days(sid, n, target):
    for d in range(n):
        db.run("INSERT OR IGNORE INTO sale_days(sale_id, date, target) VALUES (?,?,?)", (sid, ago(d), target))

a, b, c = mk_sale("An"), mk_sale("Bình"), mk_sale("Cường")
print("1) chưa thành lập:", C.status(), "| tick:", C.tick())
C.found(10_000_000)
print("2) thành lập:", C.status(), "ngày", C.day_no(), "| sale period:", db.one("SELECT kpi_period_start p FROM sales WHERE id=?", (a,))["p"])

# lùi kỳ đánh giá 30 ngày; An đạt, Bình không đạt, Cường ít ngày làm việc (nick bị lỗi) -> kéo dài
db.run("UPDATE settings SET value=? WHERE key='company_founded_at'", (ago(31),))
db.run("UPDATE sales SET kpi_period_start=?", (ago(30),))
work_days(a, 26, 2); work_days(b, 26, 2); work_days(c, 8, 2)
give_leads(a, 55); give_leads(b, 20); give_leads(c, 3)
for sid in (a, b, c):
    r = C.sale_review(db.one("SELECT * FROM sales WHERE id=?", (sid,)))
    print(f"   {sid}: ngày {r['day']}, {r['work_days']} ngày công, {r['leads_phone']}/{r['target_so_far']} -> {r['risk']}")
C.review_sales()
print("3) sau đánh giá:", [(r["name"], r["status"] or "active", r["kpi_period_start"]) for r in db.q("SELECT name, status, kpi_period_start FROM sales")])
print("   AI không gọi được khi bị sa thải? auto_post Bình =", db.one("SELECT auto_post a FROM sales WHERE id=?", (b,))["a"])
print("   telegram:", [t[:60] for t in tg])

# chưa có đơn sau 61 ngày -> giải thể
db.run("UPDATE settings SET value=? WHERE key='company_founded_at'", (ago(60),))
tg.clear(); C.check_dissolution()
print("4) ngày", C.day_no(), "không đơn:", C.status(), "|", C.s().get("dissolved_reason"))

# thành lập lại, có đơn -> không giải thể
C.found(10_000_000)
db.run("UPDATE settings SET value=? WHERE key='company_founded_at'", (ago(60),))
lead = db.one("SELECT id FROM leads LIMIT 1")["id"]
C.add_order(lead, C.parse_vnd("2,5tr"))
C.check_dissolution()
print("5) có đơn 2,5tr:", C.status(), C.finance()["revenue"], C.finance()["orders"], "đơn")

# tất cả sale bị sa thải -> giải thể
for sid in (a, c):
    C.fire(sid, "test")
C.check_dissolution()
print("6) sa thải hết:", C.status(), "|", C.s().get("dissolved_reason"))

# hết vốn -> AI dừng
C.found(100_000)
db.run("INSERT INTO usage(task, model, input_tokens, output_tokens, cost_usd, created_at) VALUES ('posts','x',1,1,5,?)", (db.now(),))
import llm
print("7) vốn 100k, AI tiêu $5:", C.fmt_vnd(C.finance()["left"]), "| budget:", llm.budget_state())
C.add_capital(1_000_000); print("   bơm 1tr:", C.fmt_vnd(C.finance()["left"]), "| budget:", llm.budget_state())
print("8) parse:", [C.parse_vnd(x) for x in ["2500000", "2.500.000", "2,5tr", "2tr5", "800k", "1.2 triệu", "abc"]])
print("9) brief:", C.brief_text())
C.check_dissolution()
print("10) thành lập lại khi sale cũ đã nghỉ, chưa tuyển ai:", C.status())

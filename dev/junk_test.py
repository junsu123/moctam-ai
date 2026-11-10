"""Sếp loại data rác -> Mai ghi nhớ, lần sau tìm khách tự loại."""
import os, sys, time, json, shutil, types
os.environ["FB_BASE_URL"] = "http://localhost:8098"
sys.path.insert(0, "/home/claude/ai-sales-company/backend")
from pathlib import Path
SP = Path(__import__("os").environ.get("MT_WORK") or Path(__file__).resolve().parent / "work")
import db
db.DB_PATH = SP / "junk.db"; db.DB_PATH.unlink(missing_ok=True)
db.PROFILES_DIR = SP / "junk_profiles"; shutil.rmtree(db.PROFILES_DIR, ignore_errors=True); db.PROFILES_DIR.mkdir()
db.init(); db.set_setting("browser_headless", "1")
import accounts, browser_poster as B, prospect, prospect_rules as R, junk, kpi
B._pause = lambda *a, **k: None
prospect.random = types.SimpleNamespace(uniform=lambda a, b: 0.05, randint=lambda a, b: a)
from fastapi.testclient import TestClient
import main
c = TestClient(main.app)
db.run("UPDATE groups SET url=NULL")
sid = c.post("/api/sales", json={"name": "Linh", "fb_name": "Linh Nguyễn"}).json()["id"]
aid = accounts.of_sale(sid)[0]["id"]
from playwright.sync_api import sync_playwright
with sync_playwright() as pw:
    ctx = B._launch(pw, aid, headless=True); pg = ctx.new_page(); pg.goto("http://localhost:8098/setlogin"); ctx.close()
c.post(f"/api/accounts/{aid}/check"); time.sleep(1)
while B.busy(sid) or B.queued(sid): time.sleep(0.3)
def run():
    c.post("/api/prospects/run", json={"directions": [1, 2, 3]}); time.sleep(1)
    while B.busy(sid) or B.queued(sid): time.sleep(0.5)
run()
leads = db.q("SELECT id, name, phone, contact FROM leads WHERE origin='prospect' ORDER BY id")
print("lần 1 leads:", [(l["name"][:25], l["phone"]) for l in leads])
assert leads, "không có khách"
bad = leads[0]
r = c.post(f"/api/leads/{bad['id']}/junk", json={"reason": "wrong_niche", "note": "mỹ phẩm, quần áo"}).json()
print("đánh dấu:", r)
print("điều kiện loại:", R.get()["exclude"])
print("knowledge:", db.one("SELECT content FROM knowledge WHERE agent_id='mai' AND topic='Data rác sếp đã loại'")["content"][:200])
print("prospect:", db.one("SELECT status, grade, rule_fail FROM prospects WHERE lead_id=?", (bad["id"],)))
print("list mặc định vẫn trả về (UI lọc):", any(l["id"] == bad["id"] for l in c.get("/api/leads").json()))
# comment trùng SĐT -> không tạo lại
if bad["phone"]:
    lid, new, _ = kpi.upsert_lead("comment", None, "Khách lạ", f"Lấy sỉ ib em {bad['phone']}", phone=bad["phone"])
    print("upsert SĐT rác:", lid, new)
# xoá prospect cũ cho chạy lại, xem có bị bỏ qua
db.run("DELETE FROM prospects")
run()
print("báo cáo:", [r["detail"][:300] for r in db.q("SELECT detail FROM activity WHERE agent_id='mai' AND detail LIKE '%data rác%' ORDER BY id DESC LIMIT 3")])
again = db.q("SELECT id, status FROM leads WHERE name=? OR (phone=? AND phone!='')", (bad["name"], bad["phone"] or "x"))
print("lead rác tồn tại:", again)
print("overview:", {k: v for k, v in c.get("/api/junk").json().items() if k != "items"})
# KPI không tính rác
print("day_stats ok:", type(kpi.day_stats()).__name__ if hasattr(kpi, "day_stats") else "-")
# thêm 2 rác nữa để học mẫu chữ
for l in leads[1:3]:
    c.post(f"/api/leads/{l['id']}/junk", json={"reason": "affiliate"})
print("skip_types:", R.get()["skip_types"])
print("patterns:", junk.patterns())
o = c.get("/api/junk").json(); print("tổng:", o["total"], o["by_reason"], "skipped", o["skipped"])
if o["patterns"]:
    w = o["patterns"][0]["word"]; c.post("/api/junk/dismiss", json={"word": w}); print("bỏ qua", w, w not in [p["word"] for p in junk.patterns()])
c.post(f"/api/leads/{bad['id']}/unjunk"); print("khôi phục:", db.one("SELECT status FROM leads WHERE id=?", (bad["id"],)), junk.blocked(phone=bad["phone"]))
print("lỗi:", db.q("SELECT title, message FROM errors"))
# học mẫu chữ rác: 6 khách thường + 3 khách rác giống nhau
for i in range(6):
    db.run("INSERT INTO leads(name, need, status, created_at) VALUES (?,?,?,?)", (f"Shop Mẹ Bỉm {i}", "nhập trà túi lọc, ngũ cốc bán online ship cod", "new", db.now()))
for i in range(3):
    lid = db.run("INSERT INTO leads(name, need, status, created_at) VALUES (?,?,?,?)", (f"Kho Sỉ Dropship {i}", "chuyên dropship đồng hồ Quảng Châu, nhập trà bán online", "new", db.now()))
    junk.mark(lid, "competitor")
P = junk.patterns(); print("mẫu chữ rác:", P)
print("check khách mới:", junk.check("Nhận dropship đồng hồ, tìm nguồn trà", "Shop ABC"))
print("check khách tốt:", junk.check("Shop mẹ bỉm cần nhập ngũ cốc", "Mẹ Su"))
c.post("/api/junk/exclude", json={"word": P[0]["label"]}); print("loại hẳn ->", R.get()["exclude"][-1], [p["word"] for p in junk.patterns()][:3])

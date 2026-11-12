"""Mai tìm khách sỉ: Facebook (giả lập) tìm + phân tích; TikTok bắt captcha -> dừng; Shopee shop bắt đăng nhập -> cần xem tay."""
import os, sys, time, json
os.environ["FB_BASE_URL"] = "http://localhost:8098"
os.environ["TIKTOK_BASE_URL"] = "http://localhost:8096"
os.environ["SHOPEE_BASE_URL"] = "http://localhost:8095"
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "backend"))
from pathlib import Path
import shutil
SP = Path(__import__("os").environ.get("MT_WORK") or Path(__file__).resolve().parent / "work")
import db
db.DB_PATH = SP / "prospect.db"; db.DB_PATH.unlink(missing_ok=True)
db.PROFILES_DIR = SP / "prospect_profiles"; shutil.rmtree(db.PROFILES_DIR, ignore_errors=True); db.PROFILES_DIR.mkdir()
db.SHOTS_DIR = SP / "multi_shots"; db.SHOTS_DIR.mkdir(exist_ok=True)
db.init(); db.set_setting("browser_headless", "1")
import accounts, browser_poster as B, prospect
B._pause = lambda *a, **k: None
import types; prospect.random = types.SimpleNamespace(uniform=lambda a, b: 0.05, randint=lambda a, b: a)
from fastapi.testclient import TestClient
import main
c = TestClient(main.app)
print("agents:", [a["id"] for a in c.get("/api/agents").json()["agents"]][:8] if isinstance(c.get("/api/agents").json(), dict) else [a["id"] for a in c.get("/api/agents").json()][:8])
r = c.post("/api/prospects/run", json={})
print("chưa có nick:", r.status_code, r.json().get("detail"))
sid = c.post("/api/sales", json={"name": "Linh", "fb_name": "Linh Nguyễn"}).json()["id"]
aid = accounts.of_sale(sid)[0]["id"]
from playwright.sync_api import sync_playwright
with sync_playwright() as pw:
    ctx = B._launch(pw, aid, headless=True); pg = ctx.new_page(); pg.goto("http://localhost:8098/setlogin"); ctx.close()
c.post(f"/api/accounts/{aid}/check"); time.sleep(1)
while B.busy(sid) or B.queued(sid): time.sleep(0.3)
print("nick:", accounts.get(aid)["login_status"])
db.set_setting("prospect_inspect_per_run", "10"); db.set_setting("tg_alert_leads", "1")
print("mặc định:", {k: v for k, v in db.get_settings().items() if k in ("prospect_tiktok", "prospect_shopee")})
r = c.post("/api/prospects/run", json={}).json()
print("giao:", r["account"], [(p.get("kind") or p["platform"], p.get("keyword")) for p in r["plan"]])
time.sleep(1)
while B.busy(sid) or B.queued(sid): time.sleep(0.5)
o = c.get("/api/prospects").json()
print("SĐT:", o["phones"], "hôm nay", o["phones_today"], "chưa có SĐT:", o["no_phone"], "nguồn:", o["platforms_on"])
print("escalated:", db.q("SELECT name, phone, escalated_at IS NOT NULL esc, escalate_reason FROM leads WHERE origin='prospect'"))
print("lọc có SĐT:", [x["account_name"] for x in c.get("/api/prospects?phone=yes").json()["items"]])
print("counts:", o["counts"], "manual:", o["manual"], "crm:", o["crm"])
for it in o["items"]:
    print(f"- {it['grade'] or '-'} {it['score'] or 0:>3} {it['platform']:8} {prospect.SELLER_TYPES.get(it['seller_type'] or 'unknown'):26} {(it['account_name'] or it['account_url'])[:34]:34} "
          f"parts={it['parts']} tags={it['tags']} phone={it['phone']} zalo={it['zalo']} status={it['status']}")
    print("    next:", it["next_action"])
for it in o["items"][:1]:
    print("  evidence:", json.dumps(it["evidence"][:6], ensure_ascii=False)[:900])
    print("  suggested:", it["suggested"]); print("  approach:", it["approach"])
print("leads:", [(l["name"], l["source"], l["business_type"], l["phone"], l["score"]) for l in db.q("SELECT * FROM leads WHERE origin='prospect'")])
print("log:", db.one("SELECT detail FROM activity WHERE agent_id='mai' ORDER BY id DESC LIMIT 1"))
# chạy lại: không tạo trùng
n0 = db.one("SELECT COUNT(*) n FROM prospects")["n"]
c.post("/api/prospects/run", json={"directions": [4]}); time.sleep(1)
while B.busy(sid) or B.queued(sid): time.sleep(0.5)
print("chạy lại, số tài khoản:", n0, "->", db.one("SELECT COUNT(*) n FROM prospects")["n"], "| leads:", db.one("SELECT COUNT(*) n FROM leads WHERE origin='prospect'")["n"])
print("log2:", db.one("SELECT detail FROM activity WHERE agent_id='mai' ORDER BY id DESC LIMIT 1"))
# sếp dán link TikTok khi đang tắt
print("dán TikTok khi tắt:", c.post("/api/prospects/analyze", json={"urls": ["http://localhost:8096/@shopabc"]}).json())
print("bật TikTok:", c.put("/api/prospects/settings", json={"tiktok": True}).json()["platforms_on"])
# sếp dán link
r = c.post("/api/prospects/analyze", json={"urls": ["http://localhost:8098/daimart.online?ref=abc http://localhost:8096/@shopabc"]}).json()
print("dán link:", r["urls"]); time.sleep(1)
while B.busy(sid) or B.queued(sid): time.sleep(0.5)
print("log3:", db.one("SELECT detail FROM activity WHERE agent_id='mai' ORDER BY id DESC LIMIT 1"))
print("tiktok row:", db.one("SELECT platform, account_url, status, next_action FROM prospects WHERE account_url LIKE '%8096%'"))
# patch, crm
p = o["items"][-1]
print("patch:", c.patch(f"/api/prospects/{p['id']}", json={"status": "rejected"}).json()["status"])
print("bỏ khỏi danh sách:", p["id"] in [x["id"] for x in c.get("/api/prospects").json()["items"]])
print("settings:", c.put("/api/prospects/settings", json={"shopee": False, "keywords": {"1": ["live bán trà sữa"]}}).json()["settings"])
print("lỗi:", db.q("SELECT title, message FROM errors"))

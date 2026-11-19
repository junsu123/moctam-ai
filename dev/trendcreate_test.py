"""Nhi tự tạo Trang (mockfb): chọn ý tưởng + nick an toàn, tạo trong ca của nick, bỏ qua bước thiết lập, chạy lịch đăng, báo Telegram, trần an toàn, lỗi."""
import os, sys, time, json, shutil, urllib.request
os.environ["FB_BASE_URL"] = "http://localhost:8098"
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "backend"))
from pathlib import Path
from datetime import timedelta
SP = Path(os.environ.get("MT_WORK") or Path(__file__).resolve().parent / "work")
import db
db.DB_PATH = SP / "trendcreate.db"; db.DB_PATH.unlink(missing_ok=True)
db.PROFILES_DIR = SP / "trendcreate_profiles"; shutil.rmtree(db.PROFILES_DIR, ignore_errors=True); db.PROFILES_DIR.mkdir()
db.SHOTS_DIR = SP / "multi_shots"; db.SHOTS_DIR.mkdir(exist_ok=True)
db.init(); db.set_setting("browser_headless", "1"); db.set_setting("anthropic_api_key", "")
import accounts, browser_poster as B, trend_pages as T, trend_create as C
B._pause = lambda *a, **k: None
sent = []
T._tg = lambda text: sent.append(text) or [{"message_id": 700 + len(sent)}]
T.ask_image = lambda pid: True
from fastapi.testclient import TestClient
import main
c = TestClient(main.app)
ok = []
def chk(name, cond, extra=""):
    ok.append(bool(cond)); print(("   ✓ " if cond else "   ✗ ") + name, extra)
def session():
    B.submit(sid, {"kind": "session", "account": aid}); time.sleep(1)
    while B.busy(sid) or B.queued(sid): time.sleep(0.5)
sid = c.post("/api/sales", json={"name": "Linh", "fb_name": "Linh Nguyễn"}).json()["id"]
aid = accounts.of_sale(sid)[0]["id"]
from playwright.sync_api import sync_playwright
with sync_playwright() as pw:
    ctx = B._launch(pw, aid, headless=True); pg = ctx.new_page(); pg.goto("http://localhost:8098/setlogin"); ctx.close()
c.post(f"/api/accounts/{aid}/check"); time.sleep(1)
while B.busy(sid) or B.queued(sid): time.sleep(0.3)
db.run("UPDATE fb_accounts SET active_from='00:00', active_to='23:59' WHERE id=?", (aid,))
add = lambda name, cat="Thú cưng": db.run("""INSERT INTO fb_pages(name, niche, category, description, avatar_prompt, cover_prompt, reason, status, created_at)
    VALUES (?, 'nuôi mèo', ?, 'Mẹo chăm mèo cho người mới nuôi.', 'Cute cat icon, flat, no text', 'Wide banner of cats, no text', 'Lên xu hướng 5/7 ngày', 'idea', ?)""",
    (name, cat, db.now()))
p1 = add("Góc Mèo Cưng")
r = C.pick()
chk("nick mới dưới 14 ngày không được dùng để tạo Trang", not r["ok"] and "14 ngày" in r["why"], r)
db.run("UPDATE fb_accounts SET created_at=? WHERE id=?", ((db.clock() - timedelta(days=40)).strftime("%Y-%m-%d %H:%M:%S"), aid))
r = C.pick()
chk("chọn ý tưởng + nick an toàn → chờ ca làm việc của nick", r["ok"] and r["page_id"] == p1 and B.due_work(aid)["create_pages"] == [p1], r)
session()
p = db.one("SELECT * FROM fb_pages WHERE id=?", (p1,))
log = [json.loads(l) for l in open(SP / "mockfb_log.jsonl", encoding="utf-8") if '"path": "/pagecreate"' in l][-1:]
chk("tạo Trang trên Facebook: tên, hạng mục gợi ý, tiểu sử", log and log[0]["name"] == "Góc Mèo Cưng" and log[0]["category"] == "Blog cá nhân"
    and "Mẹo chăm mèo" in log[0]["bio"], log)
chk("bỏ qua bước thiết lập, lấy link, Trang chạy lịch đăng", p["status"] == "active" and "/newpage" in (p["url"] or "") and p["admin_account_id"] == aid and p["auto_created_at"], (p["status"], p["url"], p["create_error"]))
chk("về nick cá nhân sau khi tạo", db.get_settings().get("page_acting_aid") == "")
chk("báo Telegram: link, nick, prompt ảnh đại diện / ảnh bìa", any("Nhi đã tạo Trang mới" in t and p["url"] in t and "Linh" in t for t in sent) and any("Cute cat icon" in t and "Cần logo" in t for t in sent), sent[-1:])
p2 = add("Góc Chó Cưng")
r = C.pick()
chk("trần 1 Trang / 7 ngày", not r["ok"] and "7 ngày" in r["why"], r)
r = c.post(f"/api/trends/pages/{p2}/autocreate")
chk("sếp chọn tạo: vẫn giữ luật mỗi nick 1 Trang / 30 ngày", r.status_code == 400 and "30 ngày" in r.json()["detail"], r.json())
d = c.get("/api/trends").json()
chk("API: cài đặt tự tạo + số Trang đã tạo 7 ngày", d["settings"]["trend_autocreate"] == "1" and d["created_7d"] == 1 and any(x.get("auto_created_at") for x in d["pages"]))
# lỗi: Facebook từ chối tên → trả về ý tưởng, ghi lỗi, lần 2 báo sếp
db.run("UPDATE fb_pages SET auto_created_at=? WHERE id=?", ((db.clock() - timedelta(days=40)).strftime("%Y-%m-%d %H:%M:%S"), p1))
p3 = add("Trang Lỗi Tên")
for i in range(2):
    r = C.pick(p3)
    session()
p = db.one("SELECT * FROM fb_pages WHERE id=?", (p3,))
chk("Facebook từ chối tên: về ý tưởng, ghi lỗi, 2 lần thì báo sếp tạo tay", r["ok"] and p["status"] == "idea" and p["create_tries"] == 2 and "chưa mở Trang mới" in (p["create_error"] or "")
    and any("lỗi 2 lần" in t for t in sent) and db.get_settings().get("page_acting_aid") == "", (p["status"], p["create_tries"], p["create_error"]))
chk("ý tưởng hỏng 2 lần không tự chọn lại", C.pick().get("page_id") != p3)
db.run("UPDATE fb_pages SET status='creating', create_at=?, admin_account_id=? WHERE id=?", ((db.clock() - timedelta(days=3)).strftime("%Y-%m-%d %H:%M:%S"), aid, p2))
C.pick()
chk("chờ ca quá 2 ngày thì trả về ý tưởng", db.one("SELECT status FROM fb_pages WHERE id=?", (p2,))["status"] in ("idea", "creating")
    and (db.one("SELECT create_tries FROM fb_pages WHERE id=?", (p2,))["create_tries"] or 0) >= 1)
# sếp giao tên Trang: trùng trên Facebook thì Nhi đổi tên; logo / banner: prompt → sếp trả lời ảnh → nick đặt lên Trang
db.run("UPDATE fb_pages SET status='dismissed' WHERE status IN ('creating','idea')")
import ceo_orders
pl = ceo_orders._rule_plan("Nhi tạo trang Mẹo Bếp Nhà Mình về mẹo nấu ăn")
chk("CEO hiểu lệnh: Nhi tạo trang <tên> về <chủ đề>", pl["actions"] and pl["actions"][0]["type"] == "trend_page_idea" and pl["actions"][0]["name"] == "Mẹo Bếp Nhà Mình"
    and pl["actions"][0]["niche"] == "mẹo nấu ăn", pl)
try:
    C.boss_idea("Facebook Việt Nam"); bad = False
except ValueError:
    bad = True
chk("tên giả Trang chính thức bị từ chối", bad)
r = C.boss_idea("Bếp Nhà Mình", "nấu ăn")
chk("sếp giao: Nhi soạn prompt logo / banner, đưa vào hàng tạo", r["queued"] and r["page"]["avatar_prompt"] and r["page"]["cover_prompt"] and not r["renamed"], r)
n0 = len(sent)
session()
p = db.one("SELECT * FROM fb_pages WHERE id=?", (r["page"]["id"],))
log = [json.loads(l) for l in open(SP / "mockfb_log.jsonl", encoding="utf-8") if '"path": "/pagecreate"' in l][-1:]
chk("trùng tên trên Facebook: Nhi đổi tên gần nghĩa rồi tạo", p["status"] == "active" and p["name"] != "Bếp Nhà Mình" and log and log[0]["name"] == p["name"]
    and "trùng" in (p["name_note"] or ""), (p["name"], p["name_note"], p["create_error"]))
msgs = sent[n0:]
chk("Telegram: báo đổi tên + 2 tin xin logo, banner kèm prompt", any("đổi thành" in t for t in msgs) and any("Cần logo" in t for t in msgs)
    and any("Cần banner" in t for t in msgs) and p["avatar_msg"] and p["cover_msg"], [t[:40] for t in msgs])
r2 = C.boss_idea(p["name"], "nấu ăn")
chk("trùng Trang trong phần mềm: đổi tên ngay khi nhận", r2["renamed"] and r2["page"]["name"] != p["name"], r2["page"]["name"])
img = b"\x89PNG" + b"0" * 3000
a1 = T.on_telegram_photo({"photo": [{"file_id": "a", "file_size": 9}], "reply_to_message": {"message_id": int(p["avatar_msg"])}}, getter=lambda f: img)
a2 = T.on_telegram_photo({"photo": [{"file_id": "c", "file_size": 9}], "reply_to_message": {"message_id": int(p["cover_msg"])}}, getter=lambda f: img)
chk("sếp trả lời tin bằng ảnh: Nhi nhận logo, banner", "logo" in a1 and "banner" in a2 and C.image_due(aid) == [p["id"]], (a1, a2))
db.run("UPDATE fb_pages SET status='dismissed' WHERE id=?", (r2["page"]["id"],))
session()
p = db.one("SELECT * FROM fb_pages WHERE id=?", (p["id"],))
up = [json.loads(l) for l in open(SP / "mockfb_log.jsonl", encoding="utf-8") if '"path": "/pageimage"' in l][-2:]
chk("nick chuyển sang Trang đặt logo + banner rồi chuyển về", p["avatar_done"] == 1 and p["cover_done"] == 1 and {u["kind"] for u in up} == {"avatar", "cover"}
    and db.get_settings().get("page_acting_aid") == "" and any("Đã đặt" in t for t in sent[-3:]), (p["img_error"], up))
print(f"XONG {sum(ok)}/{len(ok)}")

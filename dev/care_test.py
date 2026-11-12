"""Nam: rà soát bài đã đăng, bình luận ảnh + câu tự viết + Zalo (chạy thật trên mockfb)."""
import os, sys, time, json, shutil, urllib.request
os.environ["FB_BASE_URL"] = "http://localhost:8098"
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "backend"))
from pathlib import Path
SP = Path(__import__("os").environ.get("MT_WORK") or Path(__file__).resolve().parent / "work")
import db
db.DB_PATH = SP / "care.db"; db.DB_PATH.unlink(missing_ok=True)
db.PROFILES_DIR = SP / "care_profiles"; shutil.rmtree(db.PROFILES_DIR, ignore_errors=True); db.PROFILES_DIR.mkdir()
db.SHOTS_DIR = SP / "multi_shots"; db.SHOTS_DIR.mkdir(exist_ok=True)
db.init(); db.set_setting("browser_headless", "1"); db.set_setting("bump_folder", str(SP / "img2_folder")); db.set_setting("anthropic_api_key", "")
urllib.request.urlopen(urllib.request.Request("http://localhost:8098/mockmode", data=json.dumps({"cmt": os.environ.get("CMT", "")}).encode(), method="POST")).read()
import accounts, browser_poster as B, workflows, post_care, ceo_orders
from knowledge import plain
B._pause = lambda *a, **k: None
print("mặc định:", post_care.contact(), "|", post_care.mode())
L = post_care.lines([{"product_id": 1}, {"product_id": 2}, {"product_id": 1}, {}] * 3)
print("12 câu, khác nhau:", len({plain(x) for x in L}), "| VD:", L[:3])
print("ghép:", post_care.compose(L[0]))
print("bỏ câu tự ghi số:", repr(post_care._clean("Hàng mới về, liên hệ Zalo 0911222333 nhé")), "|", post_care.compose("Cần hàng liên hệ Zalo 0386992326"))
db.set_setting("bump_text_mode", "list"); print("chế độ danh sách:", post_care.texts_for([{}, {}]))
db.set_setting("bump_text_mode", "ai")
db.set_setting("bump_contact", ""); print("không có dòng liên hệ:", post_care.texts_for([{}]))
db.set_setting("bump_contact", "Cần hàng liên hệ Zalo 0386992326")
from fastapi.testclient import TestClient
import main
c = TestClient(main.app)
print("xem thử API:", c.get("/api/bump/preview-text?n=2").json())
sid = c.post("/api/sales", json={"name": "Linh", "fb_name": "Linh Nguyễn"}).json()["id"]
aid = accounts.of_sale(sid)[0]["id"]
from playwright.sync_api import sync_playwright
with sync_playwright() as pw:
    ctx = B._launch(pw, aid, headless=True); pg = ctx.new_page(); pg.goto("http://localhost:8098/setlogin"); ctx.close()
c.post(f"/api/accounts/{aid}/check"); time.sleep(1)
while B.busy(sid) or B.queued(sid): time.sleep(0.3)
print("nick:", accounts.get(aid)["login_status"])
def rec(text):
    req = urllib.request.Request("http://localhost:8098/record", data=json.dumps({"where": "/groups/abc", "text": text, "files": 1, "real": True}).encode(), method="POST")
    urllib.request.urlopen(req).read()
    log = [json.loads(l) for l in open(SP / "mockfb_log.jsonl", encoding="utf-8") if '"/record"' in l]
    return 1000 + sum(1 for _ in [0]) if False else None
before = sum(1 for l in open(SP / "mockfb_log.jsonl", encoding="utf-8") if '"path": "/record"' in l) if (SP / "mockfb_log.jsonl").exists() else 0
import re
ids = []
for i in range(3):
    rec(f"Bài test chăm sóc {i}")
# id mock = 1000 + số bài trong bộ nhớ mock; đọc lại từ trang nhóm không cần: thử dò id còn sống
for pid in range(1000, 1200):
    try:
        h = urllib.request.urlopen(f"http://localhost:8098/groups/abc/posts/{pid}").read().decode()
        if "Bài test chăm sóc" in h: ids.append(pid)
    except Exception: pass
ids = ids[-3:]
print("bài trên mock:", ids)
for k, mid in enumerate(ids):
    db.run("""INSERT INTO posts(content, target_type, status, product_id, sale_id, account_id, posted_at, posted_url, permalink_status, created_at)
              VALUES (?, 'group', 'posted', ?, ?, ?, datetime('now','localtime','-1 day'), ?, 'found', ?)""",
           (f"Bài {k}", 1 + k % 2, sid, aid, f"http://localhost:8098/groups/abc/posts/{mid}", db.now()))
db.run("INSERT INTO posts(content, target_type, status, sale_id, account_id, posted_at, created_at) VALUES ('mới đăng', 'group', 'posted', ?, ?, datetime('now','localtime','-1 hour'), ?)", (sid, aid, db.now()))
r = ceo_orders._rule_plan("rà soát lại các bài đã đăng và comment ảnh kèm zalo")
print("CEO hiểu:", r["actions"])
print("CEO làm:", ceo_orders.execute(r["actions"][0]))
print("CEO đổi zalo:", ceo_orders._rule_plan("từ nay đổi zalo liên hệ thành 0911222333")["actions"])
bs = db.q("SELECT id, post_id, text, scheduled_for FROM bumps ORDER BY id")
for b in bs: print("  lượt:", b["post_id"], b["text"])
print("lần 2 trong ngày (không trùng bài):", workflows.plan_bumps(force=True))
db.run("UPDATE bumps SET scheduled_for=?", (db.clock().strftime("%Y-%m-%d %H:%M"),))
for b in bs:
    B.submit(sid, {"kind": "bump", "account": aid, "bump_id": b["id"]})
time.sleep(1)
while B.busy(sid) or B.queued(sid): time.sleep(0.5)
print("kết quả:", [(x["status"], (x["error"] or "")[:80]) for x in db.q("SELECT status, error FROM bumps ORDER BY id")])
cm = [json.loads(l) for l in open(SP / "mockfb_log.jsonl", encoding="utf-8") if '"path": "/comment"' in l][-3:]
for x in cm: print("  mock nhận:", x.get("post"), x.get("text"), x.get("files"))
print("nhật ký Bảo:", [x["detail"] for x in db.q("SELECT detail FROM activity WHERE agent_id='bao' ORDER BY id")])
print("overview:", post_care.overview())
print("lỗi:", db.q("SELECT title, message FROM errors"))

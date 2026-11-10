"""Lướt bảng tin nhóm: nick đọc >=20 bài trên /groups/feed/, Bảo chọn người hỏi mua (ảnh) và người bán online (chào nhẹ),
bỏ người bán dịch vụ / nhà cung cấp / nhóm gợi ý; sếp duyệt; nick gửi; trần chào người bán; nhóm xóa bình luận thì ngừng chào (mockfb)."""
import os, sys, time, json, shutil, urllib.request
os.environ["FB_BASE_URL"] = "http://localhost:8098"
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "backend"))
from pathlib import Path
from datetime import timedelta
SP = Path(os.environ.get("MT_WORK") or Path(__file__).resolve().parent / "work")
import db
db.DB_PATH = SP / "feed.db"; db.DB_PATH.unlink(missing_ok=True)
db.PROFILES_DIR = SP / "feed_profiles"; shutil.rmtree(db.PROFILES_DIR, ignore_errors=True); db.PROFILES_DIR.mkdir()
db.SHOTS_DIR = SP / "multi_shots"; db.SHOTS_DIR.mkdir(exist_ok=True)
db.init(); db.set_setting("browser_headless", "1"); db.set_setting("anthropic_api_key", "")
db.set_setting("bump_folder", str(SP / "pubimg"))
post = lambda path, d: urllib.request.urlopen(urllib.request.Request("http://localhost:8098" + path, data=json.dumps(d).encode(), method="POST")).read()
post("/mockmode", {"cmt": "fb26"})
import accounts, browser_poster as B, replies, group_feed, ceo_orders, prospect_rules, fb_policy
B._pause = lambda *a, **k: None
from fastapi.testclient import TestClient
import main
c = TestClient(main.app)
prospect_rules.save({"exclude": ["quần áo"]})
sid = c.post("/api/sales", json={"name": "Linh", "fb_name": "Linh Nguyễn"}).json()["id"]
aid = accounts.of_sale(sid)[0]["id"]
db.run("UPDATE fb_accounts SET active_from='00:00', active_to='23:59', created_at='2025-01-01 00:00:00' WHERE id=?", (aid,))
from playwright.sync_api import sync_playwright
with sync_playwright() as pw:
    ctx = B._launch(pw, aid, headless=True); pg = ctx.new_page(); pg.goto("http://localhost:8098/setlogin"); ctx.close()
c.post(f"/api/accounts/{aid}/check"); time.sleep(1)
wait = lambda: [time.sleep(0.5) for _ in iter(lambda: bool(B.busy(sid) or B.queued(sid)), False)]
wait()
gid = db.run("""INSERT INTO groups(name, url, slug, members, created_at) VALUES ('Hội Tìm Nguồn Hàng Sỉ', 'http://localhost:8098/groups/hoimua', 'hoimua', 25000, ?)""", (db.now(),))
print("nick:", accounts.get(aid)["login_status"], "| kế hoạch:", group_feed.plan(aid))

# 1) CEO hiểu lệnh, nick lướt feed (đọc >= 20 bài)
r = ceo_orders._rule_plan("cho các nick lướt bảng tin nhóm và comment vào các bài")
print("CEO hiểu:", r["actions"])
assert r["actions"][0]["type"] == "feed_scan"
print("CEO làm:", ceo_orders.execute(r["actions"][0])[:160])
time.sleep(1); wait()
sc = db.one("SELECT * FROM feed_scans ORDER BY id DESC LIMIT 1")
print("lượt lướt:", {k: sc[k] for k in ("status", "read", "buyers", "sellers", "note")})
assert sc["status"] == "done" and sc["read"] >= 20
rows = db.q("SELECT id, kind, author, score, reason, reply, image, group_id FROM reply_tasks ORDER BY id")
for x in rows: print("  chờ duyệt:", x["kind"], x["author"], x["score"], "|", x["reason"], "|", x["reply"][:90], "| ảnh:", bool(x["image"]))
got = {x["author"]: x for x in rows}
assert {"Ngọc Hân", "Phạm Thu"} <= set(got) and got["Ngọc Hân"]["kind"] == "buyer" and got["Ngọc Hân"]["image"], "người hỏi mua kèm ảnh"
assert {"Shop Mẹ Sóc", "Tuấn Shop", "Lan Livestream"} <= set(got) and all(got[n]["kind"] == "seller" and not got[n]["image"]
                                                                          for n in ("Shop Mẹ Sóc", "Tuấn Shop", "Lan Livestream"))
assert not {"Dịch Vụ Ads Pro", "Kho Sỉ Trà", "Khách Lạ", "Shop Thời Trang Vy"} & set(got), "bỏ dịch vụ, nhà cung cấp, nhóm gợi ý, ngành loại"
assert all("0386992326" in x["reply"] or "Zalo" in x["reply"] for x in rows)
print("nhóm mới thấy trên feed:", [g["name"] for g in db.q("SELECT name FROM groups WHERE slug='chayads'")],
      "| nick là thành viên:", db.one("SELECT status FROM account_groups WHERE account_id=? AND group_id=(SELECT id FROM groups WHERE slug='chayads')", (aid,)))

# 2) lướt lại: không trùng bài, không chào lại cùng người
group_feed.start(aid); time.sleep(1); wait()
print("lướt lại, tổng bình luận chờ:", db.one("SELECT COUNT(*) n FROM reply_tasks")["n"], "| kế hoạch:", group_feed.plan(aid)["why"])
assert db.one("SELECT COUNT(*) n FROM reply_tasks")["n"] == len(rows)

# 3) duyệt: trần chào người bán 2/ngày -> câu chào thứ 3 dời sang mai
sel = [got[n]["id"] for n in ("Shop Mẹ Sóc", "Tuấn Shop", "Lan Livestream")]
ap = [replies.approve(i) for i in sel]
print("duyệt chào người bán:", [(x["scheduled_for"], x["later"]) for x in ap], "| quota:", replies.quota(aid))
assert not ap[0]["later"] and not ap[1]["later"] and ap[2]["later"]
ab = c.put(f"/api/replies/{got['Ngọc Hân']['id']}", json={"action": "approve"}).json()
print("duyệt người hỏi mua:", ab)
assert not ab["later"], "câu chào dời sang mai không chặn câu hỏi mua hôm nay"

# 4) tới giờ: nick gửi câu hỏi mua kèm ảnh, câu chào chỉ chữ
db.run("UPDATE reply_tasks SET scheduled_for=? WHERE id IN (?,?)", ((db.clock() - timedelta(minutes=1)).strftime("%Y-%m-%d %H:%M"),
                                                                       got["Ngọc Hân"]["id"], sel[0]))
with sync_playwright() as pw:
    ctx, page = B._open(pw, aid)
    page.add_init_script("window.UPLOAD_MS=1500")
    replies.send(page, aid, got["Ngọc Hân"]["id"])
    db.run("UPDATE reply_tasks SET sent_at=? WHERE id=?", ((db.clock() - timedelta(hours=1)).strftime("%Y-%m-%d %H:%M:%S"), got["Ngọc Hân"]["id"]))
    replies.send(page, aid, sel[0]); ctx.close()
for i in (got["Ngọc Hân"]["id"], sel[0]):
    print("gửi:", db.one("SELECT kind, status, error FROM reply_tasks WHERE id=?", (i,)))
log = [json.loads(l) for l in open(SP / "mockfb_log.jsonl", encoding="utf-8") if '"path": "/comment"' in l][-2:]
print("mock nhận:", [(x["post"], x["text"][:50], x["files"]) for x in log])
assert log[0]["files"] and not log[1]["files"]
assert db.one("SELECT COUNT(*) n FROM image_usage WHERE kind='reply'")["n"] == 1

# 5) nhóm xóa bình luận chào -> ngừng chào người bán ở nhóm đó 30 ngày
pid = int(db.one("SELECT post_url FROM reply_tasks WHERE id=?", (sel[0],))["post_url"].rstrip("/").split("/")[-1])
post("/hidecmt", {"post": pid})
db.run("UPDATE reply_tasks SET sent_at=? WHERE id=?", ((db.clock() - timedelta(hours=7)).strftime("%Y-%m-%d %H:%M:%S"), sel[0]))
with sync_playwright() as pw:
    ctx, page = B._open(pw, aid)
    print("bình luận bị xóa:", group_feed.check_removed(page, aid)); ctx.close()
g = db.one("SELECT name, no_pitch_until FROM groups WHERE id=(SELECT group_id FROM reply_tasks WHERE id=?)", (sel[0],))
print("nhóm ngừng chào:", g)
assert g["no_pitch_until"]

# 6) luật nhịp: nick mới 1 lượt/ngày; kế hoạch, API
db.run("UPDATE fb_accounts SET created_at=? WHERE id=?", (db.now(), aid))
print("nick mới:", group_feed.plan(aid), "| quota:", replies.quota(aid))
print("API feed:", {k: v for k, v in c.get("/api/feed").json().items() if k in ("nicks", "no_pitch")})
print("API chào 10/ngày:", c.put("/api/feed-settings", json={"feed_seller_per_nick_day": "10"}).status_code)
print("lỗi:", db.q("SELECT title, message FROM errors"))

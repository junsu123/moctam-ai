"""Nhi: đọc xu hướng (RSS giả), đề xuất Trang, lên lịch bài, gửi prompt ảnh Telegram, nhận ảnh sếp trả lời, bỏ bài quá 24 giờ (không cần Chrome)."""
import os, sys
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "backend"))
from pathlib import Path
from datetime import timedelta
SP = Path(os.environ.get("MT_WORK") or Path(__file__).resolve().parent / "work")
import db
db.DB_PATH = SP / "trendpages.db"; db.DB_PATH.unlink(missing_ok=True)
db.init(); db.set_setting("anthropic_api_key", "")
from fastapi.testclient import TestClient
import main, accounts, trend_pages as T, telegram_bot as TG, media_folder, httpx
c = TestClient(main.app)
ok = []
def chk(name, cond, extra=""):
    ok.append(bool(cond)); print(("   ✓ " if cond else "   ✗ ") + name, extra)
XML = """<?xml version="1.0"?><rss xmlns:ht="https://trends.google.com/trending/rss"><channel>
<item><title>công thức nấu ăn</title><ht:approx_traffic>200K+</ht:approx_traffic><ht:news_item><ht:news_item_title>10 món ngon cuối tuần</ht:news_item_title></ht:news_item></item>
<item><title>thời tiết hà nội</title><ht:approx_traffic>50K+</ht:approx_traffic></item>
<item><title>mẹo nuôi mèo</title><ht:approx_traffic>20K+</ht:approx_traffic></item></channel></rss>"""
items = T.parse_rss(XML)
chk("đọc RSS Google Trends: tiêu đề, lượt tìm, tin", len(items) == 3 and items[0]["traffic"] == "200K+" and T.traffic_num("200K+") == 200000
    and items[0]["news"][0]["title"] == "10 món ngon cuối tuần", items[0])
sent, replies = [], []
TG.configured = lambda: True
TG.send = lambda text, *a, **k: sent.append(text) or [{"message_id": 500 + len(sent)}]
r = T.research(fetch=lambda: items)
d = c.get("/api/trends").json()
chk("lưu xu hướng, chấm chủ đề nóng, đề xuất Trang mới", r["ok"] and r["trends"] == 3 and d["hot"] and any(p["status"] == "idea" for p in d["pages"]), r)
chk("báo Telegram có ý tưởng Trang mới", any("đề xuất" in t for t in sent))
idea = next(p for p in d["pages"] if p["status"] == "idea")
chk("ý tưởng có prompt ảnh đại diện / ảnh bìa", idea["avatar_prompt"] and idea["cover_prompt"])
sid = c.post("/api/sales", json={"name": "Linh", "fb_name": "Linh Nguyễn"}).json()["id"]
aid = accounts.of_sale(sid)[0]["id"]
e = c.post(f"/api/trends/pages/{idea['id']}/activate", json={"url": "trang nấu ăn", "admin_account_id": aid})
chk("link Trang sai bị từ chối", e.status_code == 400)
pg = c.post(f"/api/trends/pages/{idea['id']}/activate", json={"url": "https://facebook.com/gocnauan", "admin_account_id": aid, "posts_per_day": 2}).json()
chk("sếp tạo Trang xong dán link: Trang chạy", pg["status"] == "active" and pg["admin_account_id"] == aid)
n0 = len(sent)
p = T.write_post(pg, (db.clock() + timedelta(hours=2)).strftime("%Y-%m-%d %H:%M"))
chk("Nhi viết bài + prompt ảnh, bài chờ ảnh, gửi prompt lên Telegram", p["status"] == "need_image" and p["image_prompt"] and p["account_id"] == aid
    and len(sent) == n0 + 1 and p["image_prompt"][:30] in sent[-1] and p["img_req_msg"], p["image_prompt"][:60])
p2 = T.write_post(pg, (db.clock() + timedelta(hours=3)).strftime("%Y-%m-%d %H:%M"))
TG.call = lambda method, **kw: {"file_path": "photos/a.jpg"} if method == "getFile" else {}
class R: content = b"\xff\xd8\xff" + b"1" * 5000
_get = httpx.get; httpx.get = lambda *a, **k: R()
msg = lambda reply=None: {"chat": {"id": 42}, "photo": [{"file_id": "s", "width": 90}, {"file_id": "big", "width": 1280, "file_size": 99999}],
                          **({"reply_to_message": {"message_id": reply}} if reply else {})}
out = T.on_telegram_photo(msg(int(p2["img_req_msg"])))
q2 = db.one("SELECT * FROM posts WHERE id=?", (p2["id"],))
chk("sếp trả lời đúng tin bằng ảnh: gắn vào đúng bài, xếp đăng", q2["status"] == "scheduled" and Path(q2["image_path"]).is_file()
    and "#%d" % p2["id"] in out and db.one("SELECT status FROM posts WHERE id=?", (p["id"],))["status"] == "need_image", out)
chk("trả lời nhầm tin: báo lại, không gắn bừa", "không phải tin xin ảnh" in T.on_telegram_photo(msg(9999)))
TG._reply = lambda chat, text, *a, **k: replies.append(text)
db.set_setting("tg_chat_ids", "42")
TG.handle_message(msg())  # gửi ảnh không trả lời: gắn bài chờ lâu nhất
chk("bot Telegram nhận ảnh không trả lời: gắn bài chờ sớm nhất và báo lại", db.one("SELECT status FROM posts WHERE id=?", (p["id"],))["status"] == "scheduled"
    and replies and "Đã nhận ảnh" in replies[-1], replies[-1:])
httpx.get = _get
imgs, _ = media_folder.pick_for_post(db.one("SELECT * FROM posts WHERE id=?", (p["id"],)))
chk("khi đăng dùng đúng ảnh sếp gửi", len(imgs) == 1 and imgs[0].name == f"post_{p['id']}.jpg", imgs)
p3 = T.write_post(pg, (db.clock() + timedelta(hours=4)).strftime("%Y-%m-%d %H:%M"))
import base64
r = c.post(f"/api/trends/posts/{p3['id']}/image", json={"data": base64.b64encode(R.content).decode(), "ext": "jpg"}).json()
chk("tải ảnh trên web (dự phòng) cũng được", r["status"] == "scheduled")
p4 = T.write_post(pg, (db.clock() + timedelta(hours=5)).strftime("%Y-%m-%d %H:%M"))
db.run("UPDATE posts SET created_at=? WHERE id=?", ((db.clock() - timedelta(hours=25)).strftime("%Y-%m-%d %H:%M:%S"), p4["id"]))
T.plan_today(force=True)
chk("bài chờ ảnh quá 24 giờ thì bỏ", db.one("SELECT status FROM posts WHERE id=?", (p4["id"],))["status"] == "rejected")
c.post(f"/api/trends/pages/{pg['id']}/status", json={"status": "paused"})
chk("dừng Trang: bỏ các bài chưa đăng", not db.one("SELECT 1 FROM posts WHERE fb_page_ref=? AND status IN ('need_image','scheduled')", (pg["id"],)))
import ceo_orders
chk("CEO biết Nhi", "nhi" in ceo_orders.AGENT_ALIASES)
print(("XONG" if all(ok) else "CÓ LỖI") + f" {sum(ok)}/{len(ok)}")

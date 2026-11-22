"""Nhi tự làm ảnh: Cloudflare Workers AI tạo ảnh, dự phòng Pixabay, không được thì xin sếp; logo/banner Trang; đổi ảnh qua Telegram
(giả lập Cloudflare, Pixabay, Telegram; không cần mạng, không cần Chrome)."""
import os, sys, io, base64
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "backend"))
from pathlib import Path
from datetime import timedelta
SP = Path(os.environ.get("MT_WORK") or Path(__file__).resolve().parent / "work")
import db
db.DB_PATH = SP / "imagegen.db"; db.DB_PATH.unlink(missing_ok=True)
db.init(); db.set_setting("anthropic_api_key", ""); db.set_setting("trend_review", "0")
from PIL import Image
from fastapi.testclient import TestClient
import main, accounts, image_gen as IG, trend_pages as T, trend_create as TC, nhi_tg as N
c = TestClient(main.app)
ok = []
def chk(name, cond, extra=""):
    ok.append(bool(cond)); print(("   ✓ " if cond else "   ✗ ") + name, extra)
def jpg(w=1024, h=1024, col=(200, 120, 40)):
    b = io.BytesIO(); Image.new("RGB", (w, h), col).save(b, "JPEG"); return b.getvalue()
class R:
    def __init__(self, code=200, js=None, content=b""): self.status_code, self._js, self.content, self.text = code, js, content, str(js)
    def json(self): return self._js
    def raise_for_status(self):
        if self.status_code >= 400: raise RuntimeError(f"HTTP {self.status_code}")
net = {"cf": "ok", "px": [{"id": 11, "user": "An", "largeImageURL": "u11"}, {"id": 12, "user": "Bình", "largeImageURL": "u12"}], "cf_calls": 0, "prompts": []}
def fpost(url, **kw):
    net["cf_calls"] += 1; net["prompts"].append(kw["json"]["prompt"])
    if net["cf"] == "ok": return R(200, {"success": True, "result": {"image": base64.b64encode(jpg()).decode()}})
    return R(429, {"success": False, "errors": [{"message": "daily free allocation of neurons exceeded"}]})
def fget(url, params=None, **kw):
    if "pixabay.com/api" in url: return R(200, {"hits": net["px"]})
    return R(200, content=jpg(1280, 853, (40, 160, 90)))
IG.httpx.post, IG.httpx.get = fpost, fget
IG.SYNC = True
photos, tg = [], []
N.send_photo = lambda path, cap: photos.append((path, cap)) or str(800 + len(photos))
N.send = lambda text, buttons=None: tg.append(text) or [{"message_id": 1}]
T._tg = lambda text: tg.append(text) or [{"message_id": 500 + len(tg)}]
sid = c.post("/api/sales", json={"name": "Linh", "fb_name": "Linh Nguyễn"}).json()["id"]
aid = accounts.of_sale(sid)[0]["id"]
pg = db.run("INSERT INTO fb_pages(name, niche, status, url, admin_account_id, posts_per_day, times, keywords, created_at) VALUES ('Bếp Nhà Mình','nấu ăn gia đình','active','https://facebook.com/bep',?,2,'09:00,19:30','canh chua',?)", (aid, db.now()))
when = (db.clock() + timedelta(hours=3)).strftime("%Y-%m-%d %H:%M")
def post():
    return db.run("""INSERT INTO posts(target_type, content, status, scheduled_for, fb_page_ref, source, trend_topic, image_prompt, created_at)
                     VALUES ('page','Canh chua cá lóc','need_image',?,?,'trend_page','canh chua','sour fish soup in a clay bowl, warm light',?)""", (when, pg, db.now()))
chk("chưa cài khóa: Nhi xin ảnh sếp như cũ", not IG.on() and T.ask_image(post()) and any("Cần ảnh" in t for t in tg))
r = c.put("/api/nhi-images", json={"on": True, "cf_account_id": "a" * 32, "cf_api_token": "tok_" + "x" * 30, "pixabay_key": "px_key_123456"}).json()
s = c.get("/api/settings").json()
chk("lưu khóa: giao diện chỉ thấy bản che, không lộ khóa", r["cf_ready"] and r["pixabay_ready"] and "x" * 20 not in str(r) and s["cf_api_token"] == "••••••" and s["pixabay_key"] == "••••••")
p1 = post(); T.ask_image(p1)
q = db.one("SELECT * FROM posts WHERE id=?", (p1,))
im = Image.open(q["image_path"]) if q["image_path"] else None
chk("Cloudflare tạo ảnh theo prompt: bài có ảnh 4:5, xếp đăng, gửi ảnh lên Telegram để sếp xem", q["status"] == "scheduled" and q["image_src"] == "cloudflare"
    and im and abs(im.size[0] / im.size[1] - 0.8) < 0.01 and photos and "no text" in net["prompts"][-1] and q["img_req_msg"] == "801", (q["status"], q["image_src"], im and im.size))
r = T.on_telegram_photo({"photo": [{"file_id": "f1", "file_size": 9}], "reply_to_message": {"message_id": 801}}, getter=lambda fid: jpg(900, 900, (1, 2, 3)))
q = db.one("SELECT * FROM posts WHERE id=?", (p1,))
chk("sếp trả lời tin ảnh bằng ảnh khác: đổi ảnh", q["image_src"] == "boss" and q["status"] == "scheduled", r)
net["cf"] = "limit"
p2 = post(); T.ask_image(p2); p3 = post(); T.ask_image(p3)
a, b = db.one("SELECT * FROM posts WHERE id=?", (p2,)), db.one("SELECT * FROM posts WHERE id=?", (p3,))
chk("Cloudflare hết lượt: lấy ảnh Pixabay theo chủ đề, ghi nguồn, không dùng lại ảnh đã dùng", a["image_src"].startswith("pixabay:") and b["image_src"].startswith("pixabay:")
    and a["image_src"] != b["image_src"] and "Pixabay" in photos[-1][1], (a["image_src"], b["image_src"]))
net["px"] = []
n0 = len(tg); p4 = post(); T.ask_image(p4)
q = db.one("SELECT * FROM posts WHERE id=?", (p4,))
chk("cả hai không được: xin ảnh sếp, ghi lý do", q["status"] == "need_image" and "Cần ảnh" in tg[-1] and "Cloudflare hết lượt" in (q["error"] or ""), q["error"])
net["cf"] = "ok"
r = N.handle_text(f"đổi ảnh #{p2}")
chk("nhắn “đổi ảnh #id”: Nhi làm ảnh mới", "ảnh mới" in r and db.one("SELECT image_src FROM posts WHERE id=?", (p2,))["image_src"] == "cloudflare", r)
r = N.handle_text("cloudflare " + "b" * 32 + " newtoken_" + "y" * 24)
chk("nhắn khóa Cloudflare qua Telegram: lưu, thử, tin chứa khóa sẽ bị xóa", db.get_settings()["cf_account_id"] == "b" * 32 and "Đã lưu khóa" in r
    and N.has_secret("cloudflare abc def") and N.has_secret("Nhi ơi pixabay 123") and not N.has_secret("các trang"), r)
N.handle_text("tắt tự làm ảnh")
chk("tắt tự làm ảnh bằng lời", not IG.on() and db.get_settings()["img_auto"] == "0")
N.handle_text("bật tự làm ảnh")
np_ = db.run("INSERT INTO fb_pages(name, niche, status, avatar_prompt, cover_prompt, created_at) VALUES ('Góc Thú Cưng','nuôi chó mèo','active','cute pet logo','pets banner',?)", (db.now(),))
n = IG.for_page(np_)
f = db.one("SELECT * FROM fb_pages WHERE id=?", (np_,))
ia, ic = Image.open(f["avatar_path"]), Image.open(f["cover_path"])
chk("Trang mới: Nhi tự làm logo vuông và banner ngang, gửi Telegram để sếp xem", n == 2 and ia.size[0] == ia.size[1] and ic.size == (1640, 624)
    and f["avatar_msg"] and f["cover_msg"], (ia.size, ic.size))
chk("hàng xin ảnh Telegram không xin lại logo/banner đã làm", TC.request_images(np_) == 0)
print(f"XONG {sum(ok)}/{len(ok)}" if all(ok) else f"CÓ LỖI {sum(ok)}/{len(ok)}")

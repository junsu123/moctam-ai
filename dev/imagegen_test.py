"""Nhi tự làm ảnh: Cloudflare Workers AI tạo ảnh, dự phòng Pixabay, không được thì xin sếp; logo/banner Trang; đổi ảnh qua Telegram
(giả lập Cloudflare, Pixabay, Telegram; không cần mạng, không cần Chrome)."""
import os, sys, io, base64, json
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
# ---- ảnh 3D sản phẩm
import page_grow as G, media_folder as MF
def fpost2(url, **kw):
    if "flux-2-klein" in url:
        net["blend"] = net.get("blend", 0) + 1
        if net.get("blend_fail"): return R(500, {"success": False, "errors": [{"message": "capacity"}]})
        assert "input_image_0" in kw.get("files", {})
        return R(200, {"success": True, "result": {"image": base64.b64encode(jpg(832, 1040, (90, 60, 200))).decode()}})
    return fpost(url, **kw)
IG.httpx.post = fpost2
b = io.BytesIO(); im3 = Image.new("RGB", (600, 900), (255, 255, 255)); im3.paste((220, 30, 30), (150, 150, 450, 750)); im3.save(b, "PNG")
prods = db.q("SELECT id, name FROM products")
for pr in prods:
    r = c.post(f"/api/products/{pr['id']}/images3d", json={"filename": "hop-tra-3d.png", "data": "data:image/png;base64," + base64.b64encode(b.getvalue()).decode()}).json()
chk("trang Sản phẩm: lưu ảnh 3D cho sản phẩm", len(r["images3d"]) == 1 and IG.product_3d(prods[-1]["id"]), r)
gp = db.run("INSERT INTO fb_pages(name, niche, status, kind, url, admin_account_id, posts_per_day, times, created_at) VALUES ('Mộc Tâm','trà','active','grow','https://facebook.com/mt',?,2,'09:00,20:00',?)", (aid, db.now()))
db.run("UPDATE fb_accounts SET login_status='ok'")
w = G.write(gp, topic="product")
q = db.one("SELECT * FROM posts WHERE id=?", (w["id"],))
out = Image.open(q["image_path"]).convert("RGB") if q["image_path"] else None
chk("bài bán hàng: ghép chính xác ảnh 3D lên nền AI (giữ nguyên màu nhãn), khung 4:5, gửi Telegram", q["image_src"] == "p3d-exact" and out.size == (1080, 1350)
    and out.getpixel((540, 1000))[0] > 180 and out.getpixel((540, 1000))[1] < 80 and "ghép chính xác" in photos[-1][1], (q["image_src"], out and out.getpixel((540, 1000))))
chk("ảnh nền trắng của sản phẩm được xóa (góc ảnh là nền cảnh, không phải trắng)", out.getpixel((40, 40)) != (255, 255, 255))
w2 = G.write(gp, topic="recipe")
q2 = db.one("SELECT * FROM posts WHERE id=?", (w2["id"],))
chk("bài khác: AI hòa trộn ảnh 3D vào cảnh (FLUX.2 klein, ảnh sản phẩm làm tham chiếu)", q2["image_src"] == "p3d-blend" and net["blend"] == 1, q2["image_src"])
net["blend_fail"] = True
w3 = G.write(gp, topic="recipe")
chk("AI hòa trộn lỗi: tự chuyển sang ghép chính xác", db.one("SELECT image_src FROM posts WHERE id=?", (w3["id"],))["image_src"] == "p3d-exact")
chk("lúc đăng, sale dùng đúng ảnh Nhi ghép", MF.pick_for_post(db.one("SELECT * FROM posts WHERE id=?", (w["id"],)))[0][0] == Path(q["image_path"]))
r = N.handle_text("ghép ảnh 3D chính xác")
chk("đổi kiểu ghép ảnh 3D bằng lời", db.get_settings()["img3d_mode"] == "exact", r)
class Bot:
    API = "http://tg"
    @staticmethod
    def token(): return "t"
    @staticmethod
    def call(m, **kw): return {"file_path": "x.png"}
pn = prods[0]["name"]
r = N.on_photo_3d({"caption": f"ảnh 3D {pn}", "document": {"file_id": "d1", "mime_type": "image/png"}}, Bot)
chk("gửi ảnh qua Telegram kèm chú thích “ảnh 3D <tên>”: lưu đúng sản phẩm", "Đã lưu ảnh 3D" in r and len(IG.product_3d(prods[0]["id"])) == 2, r)
chk("ảnh không có chú thích 3D thì xử lý như ảnh bài bình thường", N.on_photo_3d({"caption": "", "photo": [{"file_id": "p"}]}, Bot) is None)
r = c.delete(f"/api/products/{prods[0]['id']}/images3d", params={"path": json.loads(db.one("SELECT images3d FROM products WHERE id=?", (prods[0]["id"],))["images3d"])[0]}).json()
chk("xóa ảnh 3D", len(r["images3d"]) == 1)
print(f"XONG {sum(ok)}/{len(ok)}" if all(ok) else f"CÓ LỖI {sum(ok)}/{len(ok)}")

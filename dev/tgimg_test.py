"""Bot Telegram riêng cho ảnh + việc của Nhi: ghép nối, nhận ảnh, lệnh, báo việc tách khỏi bot chính (Telegram giả, không cần Chrome)."""
import os, sys
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "backend"))
from pathlib import Path
from datetime import timedelta
SP = Path(os.environ.get("MT_WORK") or Path(__file__).resolve().parent / "work")
import db
db.DB_PATH = SP / "tgimg.db"; db.DB_PATH.unlink(missing_ok=True)
db.init(); db.set_setting("trend_review", "0"); db.set_setting("anthropic_api_key", "")
from fastapi.testclient import TestClient
import main, accounts, trend_pages as T, telegram_bot as TG, telegram_img as TI
c = TestClient(main.app)
ok = []
def chk(name, cond, extra=""):
    ok.append(bool(cond)); print(("   ✓ " if cond else "   ✗ ") + name, extra)
main_sent, img_sent = [], []
db.set_setting("tg_token", "111111:" + "A" * 35); db.set_setting("tg_chat_ids", "1")
TG.send = lambda text, *a, **k: main_sent.append(text) or [{"message_id": 9}]
TG.verify_token = TI.verify_token = lambda t: {"username": "nhi_anh_bot"}
calls = []
def fake_call(method, timeout=20, **kw):
    calls.append((method, kw))
    if method == "sendMessage":
        img_sent.append((kw["chat_id"], kw["text"])); return {"message_id": 700 + len(img_sent)}
    if method == "getMe": return {"username": "nhi_anh_bot"}
    return {}
TI.call = fake_call
r = c.post("/api/tg-img/token", json={"token": "111111:" + "B" * 35})
chk("không cho dùng lại token của bot chính", r.status_code == 400 and "bot chính" in r.json()["detail"])
r = c.post("/api/tg-img/token", json={"token": "222222:" + "C" * 35}).json()
chk("lưu token bot ảnh, ra mã ghép nối", r["has_token"] and len(r["pair_code"]) == 6 and not TI.configured(), r)
TI.handle_message({"chat": {"id": 55}, "text": "xin chào"})
chk("chưa ghép nối: bot xin mã", "mã ghép nối" in img_sent[-1][1] and not TI.configured())
TI.handle_message({"chat": {"id": 55}, "text": r["pair_code"], "from": {"first_name": "Sếp"}})
chk("gửi mã 6 số: ghép nối xong", TI.configured() and TI.chats() == ["55"] and "Đã kết nối" in img_sent[-1][1])
sid = c.post("/api/sales", json={"name": "Linh", "fb_name": "Linh Nguyễn"}).json()["id"]
aid = accounts.of_sale(sid)[0]["id"]
pg = T.activate(T.new_page("Bếp Nhà Mình", "nấu ăn")["id"], "https://facebook.com/bepnha", aid)
n_main = len(main_sent)
p = T.write_post(pg, (db.clock() + timedelta(hours=2)).strftime("%Y-%m-%d %H:%M"))
chk("prompt ảnh gửi qua bot ảnh, không qua bot chính", "Cần ảnh cho bài" in img_sent[-1][1] and len(main_sent) == n_main
    and p["img_req_msg"] == str(700 + len(img_sent)), p["img_req_msg"])
TI.file_bytes = lambda fid: b"\xff\xd8\xff" + b"2" * 4000
TI.handle_message({"chat": {"id": 55}, "photo": [{"file_id": "big", "width": 1280}], "reply_to_message": {"message_id": int(p["img_req_msg"])}})
q = db.one("SELECT status, image_path FROM posts WHERE id=?", (p["id"],))
chk("trả lời tin bằng ảnh trên bot ảnh: gắn đúng bài, báo lại", q["status"] == "scheduled" and Path(q["image_path"]).is_file()
    and "Đã nhận ảnh" in img_sent[-1][1], img_sent[-1][1][:80])
TI.handle_message({"chat": {"id": 99}, "photo": [{"file_id": "x", "width": 10}]})
chk("người lạ gửi ảnh: không nhận", "mã ghép nối" in img_sent[-1][1])
db.log("nhi", "Lên lịch bài Trang xu hướng", "Viết 2 bài, đã gửi prompt ảnh")
db.log("lan", "Viết bài", "Bài #1")
import workflows
workflows.mark_posted(p["id"], "https://facebook.com/bepnha/posts/1")
TG.flush_done(force=True); n = TI.flush()
chk("việc của Nhi + bài đã đăng lên Trang báo qua bot ảnh", n >= 2 and "Lên lịch bài" in img_sent[-1][1] and "Đã đăng lên Trang Bếp Nhà Mình" in img_sent[-1][1])
chk("bot chính không nhận việc của Nhi, vẫn nhận việc của đội bán hàng", not any("Lên lịch bài Trang" in t for t in main_sent[n_main:])
    and any("Viết bài" in t for t in main_sent[n_main:]))
T.write_post(pg, (db.clock() + timedelta(hours=3)).strftime("%Y-%m-%d %H:%M"))
k = len(img_sent)
TI.handle_message({"chat": {"id": 55}, "text": "/anh"})
chk("/anh: liệt kê bài chờ ảnh và gửi lại prompt", "Bài đang chờ ảnh" in img_sent[k][1] and any("Cần ảnh cho bài" in t for _, t in img_sent[k + 1:]))
TI.handle_message({"chat": {"id": 55}, "text": "/baocao"})
chk("/baocao: số bài đăng, chờ ảnh theo Trang", "Bếp Nhà Mình" in img_sent[-1][1] and "chờ ảnh 1" in img_sent[-1][1], img_sent[-1][1])
db.set_setting("tg2_evening", ""); TI.tick(db.clock().replace(hour=21, minute=50)); m = len(img_sent); TI.tick(db.clock().replace(hour=22, minute=0))
chk("21:45 báo cáo cuối ngày một lần", "Trang xu hướng" in img_sent[m - 1][1] and len(img_sent) == m)
d = c.get("/api/trends").json()
chk("màn Trang xu hướng thấy trạng thái bot ảnh", d["img_bot"]["bot"] == "nhi_anh_bot" and d["img_bot"]["chats"] == 1)
c.delete("/api/tg-img/token")
k = len(main_sent); T._tg("thử")
chk("gỡ bot ảnh: Nhi quay về dùng bot chính", not TI.configured() and len(main_sent) == k + 1)
print(("XONG" if all(ok) else "CÓ LỖI") + f" {sum(ok)}/{len(ok)}")

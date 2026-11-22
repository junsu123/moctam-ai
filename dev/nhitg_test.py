"""Sếp điều khiển Nhi qua Telegram: lệnh bằng lời, duyệt / loại / sửa bằng nút và trả lời tin, Nhi tự đặt từ khóa, tự hỏi tắt duyệt,
tới giờ chưa có ảnh thì đăng chữ (không cần Chrome)."""
import os, sys
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "backend"))
from pathlib import Path
from datetime import timedelta
SP = Path(os.environ.get("MT_WORK") or Path(__file__).resolve().parent / "work")
import db
db.DB_PATH = SP / "nhitg.db"; db.DB_PATH.unlink(missing_ok=True)
db.init(); db.set_setting("anthropic_api_key", "")
from fastapi.testclient import TestClient
import main, accounts, telegram_img as TI, telegram_bot as TB, nhi_tg as N, page_brain as PB, trend_pages as T, media_folder as MF
c = TestClient(main.app)
ok = []
def chk(name, cond, extra=""):
    ok.append(bool(cond)); print(("   ✓ " if cond else "   ✗ ") + name, extra)
sent, calls, replies = [], [], []
TI.configured = lambda: True
TI.send = lambda text, chat_ids=None, buttons=None: sent.append((text, buttons)) or [{"message_id": 900 + len(sent)}]
TI._reply = lambda chat_id, text: replies.append(text)
db.set_setting("tg2_chat_ids", "55")
call = lambda method, **kw: calls.append((method, kw)) or {}
say = lambda text: TI.handle_message({"chat": {"id": 55}, "text": text}) or replies[-1]
sid = c.post("/api/sales", json={"name": "Linh", "fb_name": "Linh Nguyễn"}).json()["id"]
aid = accounts.of_sale(sid)[0]["id"]
db.run("UPDATE fb_accounts SET login_status='ok' WHERE id=?", (aid,))
r = say("thêm trang Bếp Nhà Mình https://facebook.com/bepnhaminh"); db.run("UPDATE fb_pages SET niche='nấu ăn gia đình'"); N.auto_keywords(db.one("SELECT * FROM fb_pages WHERE name='Bếp Nhà Mình'"))
pg = db.one("SELECT * FROM fb_pages WHERE name='Bếp Nhà Mình'")
chk("nhắn thêm Trang: Nhi nhận nuôi, tự chọn nick quản trị, tự đặt từ khóa và báo", pg and pg["kind"] == "grow" and pg["admin_account_id"] == aid
    and pg["keywords"] and "nấu ăn" in pg["keywords"] and "nhận nuôi" in r and any("chưa có từ khóa" in t for t, _ in sent), (r[:120], pg and pg["keywords"]))
r = say("Bếp Nhà Mình từ khóa: món chay, canh chua")
chk("đặt từ khóa bằng lời", db.one("SELECT keywords FROM fb_pages WHERE id=?", (pg["id"],))["keywords"] == "món chay, canh chua", r)
say("Bếp Nhà Mình không viết về: rượu bia"); say("Bếp Nhà Mình 2 bài/ngày lúc 09:00, 19:30"); say("Bếp Nhà Mình nhớ: luôn xưng mình")
p = db.one("SELECT * FROM fb_pages WHERE id=?", (pg["id"],))
chk("chủ đề tránh, số bài, giờ đăng, điều Nhi ghi nhớ", p["avoid"] == "rượu bia" and p["posts_per_day"] == 2 and p["times"] == "09:00,19:30"
    and any(m["text"] == "luôn xưng mình" for m in PB.memory(pg["id"])), (p["avoid"], p["posts_per_day"], p["times"]))
n0 = len(sent)
r = say("viết bài cho Bếp Nhà Mình")
post = db.one("SELECT * FROM posts WHERE fb_page_ref=? ORDER BY id DESC", (pg["id"],))
rv = sent[-1]
chk("viết ngay: bài chờ duyệt gửi lên Telegram kèm nút Duyệt / Loại", post["status"] == "page_review" and "Bài chờ duyệt" in rv[0]
    and rv[1][0][0]["callback_data"] == f"nr:a:{post['id']}" and post["review_msg"], (r, post["status"]))
N.on_callback({"id": "c1", "data": f"nr:a:{post['id']}", "message": {"chat": {"id": 55}, "message_id": 901}}, call)
chk("bấm Duyệt: bài nuôi Trang xếp đăng, nút đổi thành “Đã duyệt”", db.one("SELECT status FROM posts WHERE id=?", (post["id"],))["status"] == "scheduled"
    and any(m == "editMessageReplyMarkup" and "Đã duyệt" in str(k) for m, k in calls) and calls[-1][0] == "answerCallbackQuery")
say("viết bài cho Bếp Nhà Mình"); p2 = db.one("SELECT * FROM posts WHERE fb_page_ref=? ORDER BY id DESC", (pg["id"],))
N.on_callback({"id": "c2", "data": f"nr:r:{p2['id']}", "message": {"chat": {"id": 55}, "message_id": 902}}, call)
chk("bấm Loại: hiện nút lý do", any(m == "editMessageReplyMarkup" and f"nr:x:{p2['id']}:2" in str(k) for m, k in calls[-2:]))
N.on_callback({"id": "c3", "data": f"nr:x:{p2['id']}:2", "message": {"chat": {"id": 55}, "message_id": 902}}, call)
chk("chọn lý do: bài bị loại, Nhi ghi nhớ lý do", db.one("SELECT status FROM posts WHERE id=?", (p2["id"],))["status"] == "rejected"
    and any(m["kind"] == "reject" and "Giọng văn" in m["text"] for m in PB.memory(pg["id"])))
say("viết bài cho Bếp Nhà Mình"); p3 = db.one("SELECT * FROM posts WHERE fb_page_ref=? ORDER BY id DESC", (pg["id"],))
mid = int(p3["review_msg"].split(",")[0])
TI.handle_message({"chat": {"id": 55}, "text": "Canh chua chay 15 phút, nhà mình nấu hoài không chán. Bạn thích chua nhiều hay ít?",
                   "reply_to_message": {"message_id": mid}})
q = db.one("SELECT status, review_result, content FROM posts WHERE id=?", (p3["id"],))
chk("trả lời tin bài bằng bản sửa: duyệt bản sếp, Nhi ghi nhớ", q["status"] == "scheduled" and q["review_result"] == "edit" and "15 phút" in q["content"]
    and "bản sếp sửa" in replies[-1], replies[-1])
chk("tắt / bật duyệt bằng lời", "tắt duyệt" and (say("tắt duyệt") and db.get_settings()["trend_review"] == "0") and (say("bật duyệt") and db.get_settings()["trend_review"] == "1"))
# Trang xu hướng: chưa có từ khóa thì Nhi tự đặt khi lên lịch; tới giờ chưa có ảnh thì đăng chữ
tp = db.run("INSERT INTO fb_pages(name, niche, status, url, admin_account_id, posts_per_day, times, created_at) VALUES ('Góc Thú Cưng','nuôi chó mèo','active','https://facebook.com/goc',?,1,'23:59',?)", (aid, db.now()))
db.set_setting("trend_plan_day", "")
T.plan_today(force=True)
chk("Trang chưa có từ khóa: Nhi tự đặt rồi báo, có nút duyệt tất cả khi nhiều bài", db.one("SELECT keywords FROM fb_pages WHERE id=?", (tp,))["keywords"]
    and any("Góc Thú Cưng" in t and "chưa có từ khóa" in t for t, _ in sent))
past = (db.clock() - timedelta(minutes=5)).strftime("%Y-%m-%d %H:%M")
ni = db.run("INSERT INTO posts(target_type, content, status, scheduled_for, fb_page_ref, source, created_at) VALUES ('page','bài chờ ảnh','need_image',?,?,'trend_page',?)", (past, tp, db.now()))
n1 = len(sent)
N.noimg_due()
q = db.one("SELECT * FROM posts WHERE id=?", (ni,))
chk("tới giờ chưa có ảnh: Nhi đăng chữ (không lấy ảnh sản phẩm), báo sếp", q["status"] == "scheduled" and q["text_only"] == 1
    and MF.pick_for_post(q) == ([], None) and len(sent) == n1 + 1)
r = say("luôn chờ ảnh")
chk("nhắn “luôn chờ ảnh” thì tắt đăng chữ", db.get_settings()["trend_noimg_post"] == "0", r)
for i in range(20):
    db.run("INSERT INTO posts(fb_page_ref, source, status, review_result, reviewed_at, created_at) VALUES (?, 'trend_page', 'posted', 'ok', ?, ?)", (tp, db.now(), db.now()))
db.set_setting("nhi_off_asked", "")
N.maybe_ask_off()
chk("Nhi hiểu ý sếp: tự hỏi tắt duyệt bằng nút, chỉ hỏi 1 lần/tuần", sent[-1][1] and sent[-1][1][0][0]["callback_data"] == "nr:off" and not N.maybe_ask_off())
N.on_callback({"id": "c4", "data": "nr:off", "message": {"chat": {"id": 55}, "message_id": 950}}, call)
chk("bấm “Nhi tự đăng”: tắt duyệt", db.get_settings()["trend_review"] == "0")
r = say("tạm dừng Bếp Nhà Mình")
chk("tạm dừng Trang bằng lời", db.one("SELECT status FROM fb_pages WHERE id=?", (pg["id"],))["status"] == "paused", r)
r = say("các trang")
chk("xem danh sách Trang, từ khóa, bài hôm nay", "Bếp Nhà Mình" in r and "Góc Thú Cưng" in r and "từ khóa" in r, r[:200])
r = say("tạo trang Mèo Nhà Mình về nuôi mèo")
chk("tạo Trang mới bằng lời: vào hàng tạo của Nhi", db.one("SELECT status FROM fb_pages WHERE name LIKE 'Mèo Nhà Mình%'") and "hàng tạo" in r, r)
# bot chính: tin bắt đầu bằng “Nhi”, nút nr:
main_replies = []
TB._reply = lambda chat_id, text: main_replies.append(text)
db.set_setting("tg_chat_ids", "77")
TB.handle_message({"chat": {"id": 77}, "text": "Nhi ơi các trang"})
chk("bot chính: “Nhi ơi …” là lệnh cho Nhi", main_replies and "Các Trang của Nhi" in main_replies[-1], main_replies[-1][:80] if main_replies else "")
for i, (kw, rc, cm) in enumerate([("canh chua", 40, 12), ("canh chua", 30, 8), ("món chay", 5, 1)]):
    db.run("""INSERT INTO posts(target_type, content, status, posted_at, fb_page_ref, source, page_kw, reactions, comments, shares, created_at)
              VALUES ('page','x','posted',?,?,'trend_page',?,?,?,1,?)""", (db.now(), pg["id"], kw, rc, cm, db.now()))
r = say("chủ đề nào được quan tâm nhất")
chk("hỏi Nhi chủ đề được quan tâm nhất: xếp theo tương tác thật, nói rõ khi ít số liệu", r.index("canh chua") < r.index("món chay") and "chưa đủ để kết luận" in r, r[:160])
print(f"XONG {sum(ok)}/{len(ok)}" if all(ok) else f"CÓ LỖI {sum(ok)}/{len(ok)}")

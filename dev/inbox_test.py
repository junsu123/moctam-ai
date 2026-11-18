"""Tin nhắn Fanpage (Messenger, Graph API giả lập): khách nhắn → khách hàng + Hà soạn → sếp duyệt gửi, luật 24 giờ."""
import os, sys
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "backend"))
from pathlib import Path
from datetime import timedelta, timezone, datetime
SP = Path(os.environ.get("MT_WORK") or Path(__file__).resolve().parent / "work")
import db
db.DB_PATH = SP / "inbox.db"; db.DB_PATH.unlink(missing_ok=True)
db.init(); db.set_setting("anthropic_api_key", ""); db.set_setting("fb_page_id", "999"); db.set_setting("fb_page_token", "tok")
from fastapi.testclient import TestClient
import main, page_inbox, funnel
c = TestClient(main.app)
ok = []
def chk(name, cond, extra=""):
    ok.append(bool(cond)); print(("   ✓ " if cond else "   ✗ ") + name, extra)
utc = lambda **kw: (datetime.now(timezone.utc) - timedelta(**kw)).strftime("%Y-%m-%dT%H:%M:%S+0000")
CONV = [
    {"id": "c1", "messages": {"data": [{"message": "Shop mình cần nhập trà gừng túi lọc số lượng 200 hộp, báo giá sỉ giúp mình", "from": {"id": "u1", "name": "Shop Mộc An"}, "created_time": utc(minutes=30)}]}},
    {"id": "c2", "messages": {"data": [{"message": "Còn hàng không ạ", "from": {"id": "u2", "name": "Lan Phương"}, "created_time": utc(hours=3)},
                                       {"message": "Dạ còn ạ", "from": {"id": "999", "name": "Trang"}, "created_time": utc(hours=2)}]}},
    {"id": "c3", "messages": {"data": [{"message": "Cho mình xin catalog", "from": {"id": "u3", "name": "Bảo Ngọc"}, "created_time": utc(hours=25)}]}},
]
page_inbox.fetch_conversations = lambda: CONV
sent = []
page_inbox._graph_send = lambda psid, text: sent.append((psid, text)) or {"message_id": "m1"}
r = c.post("/api/page-inbox/sync").json()
d = c.get("/api/page-inbox").json()
by = {x["conv_id"]: x for x in d["items"]}
chk("đọc 3 cuộc, 2 cuộc khách chờ (cuộc Trang đã trả lời bỏ qua)", r["new"] == 2 and "c2" not in by, r)
chk("quá 24 giờ thì hết hạn, không gửi được", by["c3"]["status"] == "expired")
t1 = by["c1"]
chk("Hà soạn sẵn câu trả lời, còn ~23 giờ", t1["status"] == "waiting" and len(t1["draft"] or "") > 10 and 23 <= t1["left_h"] <= 24, (t1["draft"] or "")[:60])
lead = db.one("SELECT * FROM leads WHERE id=?", (t1["lead_id"],))
chk("khách vào mục Khách hàng, kênh Tin nhắn Fanpage", lead["origin"] == "messenger" and lead["source"] == "Tin nhắn Fanpage")
chk("phễu có kênh Tin nhắn Fanpage", "messenger" in funnel.CHANNELS)
e = c.post(f"/api/page-inbox/{t1['id']}/send", json={"text": "Trà gừng chữa khỏi bệnh dạ dày, bạn nhắn Zalo nhé"})
chk("câu phạm Luật Facebook thì không gửi", e.status_code == 400 and not sent, e.json())
s1 = c.post(f"/api/page-inbox/{t1['id']}/send", json={"text": "Dạ em chào shop, anh/chị cho em xin SĐT hoặc Zalo để em gửi catalog và báo giá sỉ ạ"}).json()
chk("sếp duyệt (có sửa câu): gửi đúng người qua Messenger", s1["status"] == "sent" and sent == [("u1", s1["sent_text"])], sent)
chk("khách chuyển sang đã liên hệ", db.one("SELECT status FROM leads WHERE id=?", (t1["lead_id"],))["status"] == "contacted")
chk("gửi lại lần 2 bị chặn", c.post(f"/api/page-inbox/{t1['id']}/send", json={}).status_code == 400)
chk("cuộc hết hạn không gửi được", c.post(f"/api/page-inbox/{by['c3']['id']}/send", json={}).status_code == 400)
# khách nhắn tiếp, để SĐT: cùng khách, có SĐT
CONV[0]["messages"]["data"].append({"message": "Số mình 0912 345 678 nhé", "from": {"id": "u1", "name": "Shop Mộc An"}, "created_time": utc(minutes=1)})
CONV[0]["messages"]["data"].insert(1, {"message": "Dạ em chào shop", "from": {"id": "999"}, "created_time": utc(minutes=20)})
page_inbox.sync()
t1b = db.one("SELECT * FROM page_threads WHERE conv_id='c1'")
chk("khách nhắn tiếp: chờ trả lời lại, cùng một khách, có SĐT",
    t1b["status"] == "waiting" and t1b["lead_id"] == t1["lead_id"] and db.one("SELECT phone FROM leads WHERE id=?", (t1["lead_id"],))["phone"]
    and db.one("SELECT COUNT(*) n FROM leads WHERE origin='messenger'")["n"] == 2 and "0912" in t1b["last_text"] and "200 hộp" not in t1b["last_text"])
# sếp tự trả lời trên Facebook: thôi chờ
CONV[0]["messages"]["data"].append({"message": "Ok em gọi ngay", "from": {"id": "999"}, "created_time": utc(seconds=5)})
page_inbox.sync()
chk("sếp tự trả lời trên Facebook: không chờ nữa", db.one("SELECT status FROM page_threads WHERE conv_id='c1'")["status"] == "answered")
db.set_setting("page_inbox_auto", "1")
CONV.append({"id": "c4", "messages": {"data": [{"message": "Bên bạn có nhận gia công không", "from": {"id": "u4", "name": "Hùng"}, "created_time": utc(minutes=2)}]}})
page_inbox.sync()
chk("bật tự gửi: gửi luôn câu Hà soạn", db.one("SELECT status FROM page_threads WHERE conv_id='c4'")["status"] == "sent" and sent[-1][0] == "u4")
page_inbox.fetch_conversations = lambda: (_ for _ in ()).throw(RuntimeError("(#230) Requires pages_messaging permission"))
e = c.post("/api/page-inbox/sync")
chk("thiếu quyền: báo rõ cần pages_messaging", e.status_code == 400 and "pages_messaging" in e.json()["detail"], e.json())
import ceo_orders
chk("CEO hiểu “đọc tin nhắn fanpage”", any(a["type"] == "scan_fanpage" for a in ceo_orders._rule_plan("đọc tin nhắn fanpage giúp anh")["actions"]))
print(("XONG" if all(ok) else "CÓ LỖI") + f" {sum(ok)}/{len(ok)}")

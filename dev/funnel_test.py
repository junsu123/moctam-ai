"""Đo tới khách mua: phễu theo kênh, lý do không mua (web + Telegram), lý do vào lời dặn của Mai/Lan/Hà."""
import os, sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "backend"))
SP = Path(os.environ.get("MT_WORK") or Path(__file__).resolve().parent / "work"); SP.mkdir(exist_ok=True)
import db
db.DB_PATH = SP / "funnel.db"; db.DB_PATH.unlink(missing_ok=True); db.init(); db.set_setting("anthropic_api_key", "")
import funnel, agents, telegram_bot as TG
from fastapi.testclient import TestClient
import main
c = TestClient(main.app)

ok = []
def check(name, cond): ok.append(bool(cond)); print(("OK  " if cond else "LỖI ") + name)

def lead(origin, phone="0912345678", direction=None):
    lid = db.run("""INSERT INTO leads(name, contact, status, phone, origin, created_at, updated_at) VALUES (?,?, 'new', ?, ?, ?, ?)""",
                 (f"Shop {origin}", "fb", phone, origin, db.now(), db.now()))
    if origin == "prospect":
        db.run("INSERT INTO prospects(account_name, direction, lead_id, created_at) VALUES ('x', ?, ?, ?)", (direction, lid, db.now()))
    return lid
cm = [lead("comment") for _ in range(4)] + [lead("comment", phone=None)]
pg = [lead("prospect", direction=2) for _ in range(4)]
dm = lead("prospect", direction=6)

# đã gọi + chốt đơn (có doanh thu)
c.patch(f"/api/leads/{cm[0]}", json={"status": "contacted", "contacted": True})
r = c.post(f"/api/leads/{cm[0]}/order", json={"amount": 2500000})
check(f"ghi đơn hàng ({r.status_code})", r.status_code == 200 and db.one("SELECT status FROM leads WHERE id=?", (cm[0],))["status"] == "ordered")

# web: bắt chọn lý do
check("không chọn lý do bị từ chối", c.post(f"/api/leads/{pg[0]}/lost", json={"reason": ""}).status_code == 400)
c.post(f"/api/leads/{pg[0]}/lost", json={"reason": "wrong_fit", "note": "chỉ mua lẻ"})
c.post(f"/api/leads/{pg[1]}/lost", json={"reason": "wrong_fit"})
c.post(f"/api/leads/{cm[1]}/lost", json={"reason": "moq"})
l = db.one("SELECT * FROM leads WHERE id=?", (pg[0],))
check("web ghi lý do + ghi chú", l["status"] == "lost" and l["lost_reason"] == "wrong_fit" and l["lost_note"] == "chỉ mua lẻ")
c.patch(f"/api/leads/{pg[2]}", json={"status": "lost"})
check("đổi trạng thái Không mua: ghi nhận, chờ lý do", db.one("SELECT status, lost_reason FROM leads WHERE id=?", (pg[2],)) == {"status": "lost", "lost_reason": None})

# Telegram: Không mua -> hỏi lý do bằng nút -> chọn
sent = []
TG.call = lambda method, **kw: sent.append((method, kw)) or {"ok": True}
TG.chats = lambda: ["1"]
msg = {"chat": {"id": 1}, "message_id": 9, "text": "Phiếu khách"}
TG.handle_callback({"id": "a", "data": f"l:{dm}:lost", "message": msg})
kb = next((kw.get("reply_markup") for m, kw in sent if m == "editMessageText"), None)
check("Telegram hiện nút lý do", kb and any("lr_has_supplier" in b["callback_data"] for row in kb["inline_keyboard"] for b in row))
TG.handle_callback({"id": "b", "data": f"l:{dm}:lr_has_supplier", "message": msg})
check("Telegram ghi lý do", db.one("SELECT lost_reason FROM leads WHERE id=?", (dm,))["lost_reason"] == "has_supplier")

r = funnel.report(30)
ch = {x["key"]: x for x in r["channels"]}
check(f"phễu bình luận: {ch['comment']}", ch["comment"]["phones"] == 4 and ch["comment"]["won"] == 1 and ch["comment"]["revenue"] == 2500000
      and ch["comment"]["called"] == 2 and ch["comment"]["leads"] == 5)
check(f"phễu trang shop: {ch['pages']}", ch["pages"]["lost"] == 3 and ch["pages"]["lost_noreason"] == 1 and ch["pages"]["won"] == 0)
check("lý do xếp nhiều nhất trước", r["reasons"][0]["key"] == "wrong_fit" and r["reasons"][0]["by_channel"] == {"pages": 2})
check("API /funnel", c.get("/api/funnel?days=30").json()["total"]["won"] == 1)

mai, lan, tuan = funnel.prompt_block("mai"), agents.system_prompt("lan", db.get_settings()), funnel.prompt_block("tuan")
check("lời dặn Mai có lý do + việc cần làm", "Sai tệp" in mai and "bằng chứng đang bán online" in mai)
check("lời dặn Lan (system prompt) có việc của Lan", "KẾT QUẢ SẾP GỌI KHÁCH" in lan and "nhập về bán lại" in lan)
check("Tuấn không nhận khối này", tuan == "")
t = funnel.text_summary(7)
check("báo cáo tối có phễu", "SĐT → sếp gọi" in t and "chưa ghi lý do" in t)
print(("XONG" if all(ok) else "CÓ LỖI") + f" {sum(ok)}/{len(ok)}")

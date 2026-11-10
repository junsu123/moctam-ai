"""CEO Đức thông minh hơn: nhớ hội thoại, đọc số liệu thật, hỏi lại khi lệnh mơ hồ, học khách đã mua để thử từ khóa mới,
đọc bình luận Fanpage, báo cáo tuần; không lách luật Facebook."""
import os, sys, json
from pathlib import Path
from types import SimpleNamespace as NS
from datetime import timedelta
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "backend"))
SP = Path(os.environ.get("MT_WORK") or Path(__file__).resolve().parent / "work"); SP.mkdir(exist_ok=True)
import db
db.DB_PATH = SP / "ceobrain.db"; db.DB_PATH.unlink(missing_ok=True); db.init(); db.set_setting("anthropic_api_key", "")
import llm as L, ceo_orders as CO, ceo_brain as B, funnel, telegram_bot as TG, prospect

ok = []
def check(name, cond): ok.append(bool(cond)); print(("OK  " if cond else "LỖI ") + name)
seen, queue = [], []
class Fake:
    def create(self, **kw):
        msg = kw["messages"][0]["content"]
        mine = "Sếp nhắn:" in msg or "Chân dung khách thật" in msg or "báo cáo tuần" in msg
        if not mine:  # việc nền khác (Lan viết bài...) không lấy câu trả lời dành cho CEO
            return NS(stop_reason="end_turn", usage=NS(input_tokens=1, output_tokens=1), content=[NS(type="text", text="{}")])
        seen.append(kw)
        out = queue.pop(0) if queue else {"reply": "Dạ.", "actions": []}
        if "tools" in kw:
            return NS(stop_reason="tool_use", usage=NS(input_tokens=5, output_tokens=5), content=[NS(type="tool_use", input={"ket_qua": out})])
        return NS(stop_reason="end_turn", usage=NS(input_tokens=5, output_tokens=5), content=[NS(type="text", text=out)])
L.llm.client = NS(messages=Fake())
TG.configured = lambda: False

# 1) nhớ hội thoại + số liệu thật
queue.append({"reply": "Dạ em giao Lan viết 2 bài trà gừng.", "actions": []})
CO.handle("Viết 2 bài về trà gừng mật ong")
queue.append({"reply": "Dạ.", "actions": []})
CO.handle("làm tiếp như vậy cho bột ngũ cốc")
p = seen[-1]["messages"][0]["content"]
check("CEO nhớ tin trước (“trà gừng”)", "trà gừng" in p and "Hội thoại gần đây" in p)
check("CEO đọc số liệu thật (phễu, khách chờ gọi)", "SỐ LIỆU THẬT" in p and "khach_cho_sep_goi" in p)
sysm = seen[-1]["system"]
check("phong cách giám đốc + không lách luật trong lời dặn", "giám đốc" in sysm and "KHÔNG né phát hiện" in sysm)

# 2) lệnh mơ hồ -> hỏi lại có lựa chọn
queue.append({"reply": "", "actions": [], "clarify": {"question": "Sếp muốn viết về sản phẩm nào ạ?", "options": ["Trà gừng", "Bột ngũ cốc", "Hàng bán chạy"]}})
r = CO.handle("viết bài đi")
check("hỏi lại 1 câu + lựa chọn", r["clarify"]["options"] == ["Trà gừng", "Bột ngũ cốc", "Hàng bán chạy"] and not r["actions"])
pq = B.pending_question()
check("nhớ câu đang hỏi", pq and pq["question"].startswith("Sếp muốn"))
queue.append({"reply": "Dạ em giao Lan.", "actions": []})
CO.handle("Bột ngũ cốc")
check("câu trả lời của sếp được hiểu là trả lời câu hỏi", "Em vừa hỏi lại sếp" in seen[-1]["messages"][0]["content"])

# Telegram: bấm lựa chọn -> CEO làm tiếp
sent = []
TG.call = lambda method, **kw: sent.append((method, kw)) or {"ok": True}
TG.chats = lambda: ["1"]; TG._reply = lambda chat, text: sent.append(("reply", text))
queue.append({"reply": "", "actions": [], "clarify": {"question": "Nhóm nào ạ?", "options": ["Nhóm sỉ", "Nhóm mẹ bỉm"]}})
TG.send = lambda text, buttons=None: sent.append(("send", text, buttons))
r = CO.handle("đăng bài đi", via="telegram")
btn = sent[-1][2]
check("Telegram gửi nút lựa chọn", r.get("sent") and btn and btn[0][0]["callback_data"].startswith("q:"))
queue.append({"reply": "Dạ em đăng vào nhóm sỉ.", "actions": []})
TG.handle_callback({"id": "x", "data": btn[0][0]["callback_data"], "message": {"chat": {"id": 1}, "message_id": 3}})
check("bấm nút -> CEO nhận “Nhóm sỉ”", any(m == "reply" and "nhóm sỉ" in t for m, t, *_ in sent))

# 3) học khách đã mua -> thử từ khóa mới, 14 ngày sau giữ / bỏ
for i in range(3):
    lid = db.run("INSERT INTO leads(name, status, business_type, need, origin, phone, created_at) VALUES (?, 'ordered', 'Người bán livestream', 'cần nguồn trà ổn định', 'prospect', ?, ?)",
                 (f"Shop {i}", f"09100000{i}", db.now()))
    db.run("INSERT INTO prospects(account_name, keyword, direction, seller_type, categories, lead_id, phone, created_at) VALUES ('x','livestream trà',1,'live','đồ uống healthy',?,?,?)",
           (lid, f"09100000{i}", db.now()))
prof = B.won_profile()
check("chân dung khách mua thật", prof["so_khach_mua"] == 3 and prof["dung"] == "khach_mua")
queue.append({"mai": [{"huong": 1, "tu_khoa": "livestream trà healthy"}, {"huong": 4, "tu_khoa": "cần nguồn trà ổn định"}, {"huong": 1, "tu_khoa": "livestream trà"}],
              "nhom": ["hội bán đồ uống healthy online"], "vi_sao": "khách mua đều bán livestream đồ uống healthy"})
r = B.suggest_keywords()
kws = prospect.keywords()
check(f"thử từ khóa mới, bỏ từ trùng ({r['added']})", len(r["added"]) == 3 and kws[1][0] == "livestream trà healthy" and "cần nguồn trà ổn định" in kws[4])
check("chủ đề nhóm mới vào kho tìm nhóm", "hội bán đồ uống healthy online" in db.get_settings()["group_keywords"])
tr = json.loads(db.get_settings()["ceo_kw_trials"]); old = (db.clock() - timedelta(days=15)).strftime("%Y-%m-%d")
for k in tr: tr[k]["at"] = old
db.set_setting("ceo_kw_trials", json.dumps(tr))
db.run("INSERT INTO prospects(account_name, keyword, direction, phone, created_at) VALUES ('y','livestream trà healthy',1,'0911111111',?)", (db.now(),))
out = B.review_trials()
kws = prospect.keywords()
check(f"14 ngày: giữ từ ra SĐT, bỏ từ không ra ({out})", "livestream trà healthy" in kws[1] and "cần nguồn trà ổn định" not in kws.get(4, []))

# 4) Fanpage: bình luận có SĐT / hỏi giá -> khách kênh Fanpage
db.set_setting("fb_page_id", "999"); db.set_setting("fb_page_token", "t")
pid = db.run("INSERT INTO posts(agent_id, target_type, status, posted_at, fb_post_id, created_at) VALUES ('lan','page','posted',?, '999_1', ?)", (db.now(), db.now()))
fake_c = [{"from": {"id": "5", "name": "Chị Hoa"}, "message": "Cho chị xin giá sỉ, sđt 0987654321"},
          {"from": {"id": "6", "name": "Anh Nam"}, "message": "đẹp quá"},
          {"from": {"id": "999", "name": "Trang"}, "message": "Inbox giúp em ạ 0900000000"}]
r = B.scan_fanpage(fetch=lambda pid_: fake_c)
check(f"Fanpage: 1 khách có SĐT ({r})", r["ok"] and r["phones"] == 1 and db.one("SELECT origin FROM leads WHERE phone LIKE '%987654321%'")["origin"] == "fanpage")
check("phễu có kênh Bình luận Fanpage", any(c["key"] == "fanpage" for c in funnel.report(30)["channels"]))

# 5) báo cáo tuần
queue.append({"mai": [], "nhom": [], "vi_sao": ""})
queue.append("Tuần qua có 4 SĐT, chốt 3 đơn. Nút thắt: sếp chưa gọi hết khách. Tuần này: 1) ...")
w = B.weekly(send=False)
check("báo cáo tuần có số liệu + gợi ý", "Tuần qua" in w and db.get_settings()["ceo_weekly_last"] == db.today())

# 6) hiểu lệnh khi chưa có khóa Claude
L.llm.client = None
acts = lambda t: [a["type"] for a in CO._rule_plan(t)["actions"]]
check("mẫu câu: báo cáo tuần / từ khóa mới / Fanpage", acts("báo cáo tuần đi em") == ["weekly_report"]
      and acts("tìm khách theo hướng mới đi") == ["suggest_keywords"] and acts("đọc bình luận fanpage") == ["scan_fanpage"])
print(("XONG" if all(ok) else "CÓ LỖI") + f" {sum(ok)}/{len(ok)}")

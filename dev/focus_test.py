"""Dồn sức vào kênh ra đơn: CEO dừng kênh chỉ ra số, dồn sức kênh ra đơn, chờ đủ cuộc gọi, tự chạy lại sau 30 ngày."""
import os, sys, json
from pathlib import Path
from datetime import timedelta
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "backend"))
SP = Path(os.environ.get("MT_WORK") or Path(__file__).resolve().parent / "work"); SP.mkdir(exist_ok=True)
import db
db.DB_PATH = SP / "focus.db"; db.DB_PATH.unlink(missing_ok=True); db.init(); db.set_setting("anthropic_api_key", "")
import channel_focus as F, prospect, ceo, ceo_orders
from fastapi.testclient import TestClient
import main
c = TestClient(main.app)
sent = []
ceo._tg = lambda text, buttons=None: sent.append((text, buttons))

ok = []
def check(name, cond): ok.append(bool(cond)); print(("OK  " if cond else "LỖI ") + name)

def leads(direction, n, called=0, won=0, origin="prospect"):
    for i in range(n):
        st = "ordered" if i < won else "lost" if i < called else "new"
        lid = db.run("INSERT INTO leads(name, status, phone, origin, created_at, updated_at) VALUES (?,?,?,?,?,?)",
                     (f"S{direction}-{i}", st, f"09{direction}{i:07d}", origin, db.now(), db.now()))
        if origin == "prospect":
            db.run("INSERT INTO prospects(account_name, direction, lead_id, created_at) VALUES ('x',?,?,?)", (direction, lid, db.now()))
leads(2, 10, called=6)            # trang / shop: đủ số, đủ gọi, 0 đơn -> dừng
leads(6, 9, called=4, won=2)      # hỏi nguồn trong nhóm: ra đơn -> dồn sức
leads(5, 9, called=2)             # quảng cáo: sếp mới gọi 2 -> nhắc gọi
leads(0, 12, called=8, origin="comment")  # bình luận: 0 đơn nhưng không bao giờ tự dừng

rv = {x["key"]: x for x in F.review()["channels"]}
check("đánh giá đúng từng kênh", (rv["pages"]["verdict"], rv["demand"]["verdict"], rv["ads"]["verdict"], rv["comment"]["verdict"]) == ("weak", "good", "call", "weak"))
acts = F.plan()
check(f"kế hoạch: dừng trang, dồn sức nhóm, không đụng bình luận/quảng cáo {[(a['op'], a['key']) for a in acts]}",
      {(a["op"], a["key"]) for a in acts} == {("pause", "pages"), ("boost", "demand")})

g0 = int(db.get_settings()["prospect_groups_per_run"])
r = F.run()
st = db.get_settings()
check("CEO tự quyết: đã dừng kênh trang / shop", st["prospect_pages"] == "0" and "pages" in F.paused() and len(r["done"]) == 2)
check("dồn sức: đọc thêm 1 nhóm mỗi lượt", int(st["prospect_groups_per_run"]) == g0 + 1)
check("Mai không tìm trang theo 4 hướng nữa", all(x.get("direction") not in (1, 2, 3, 4) for x in prospect.plan_for_run()))
check("báo Telegram có nhắc gọi thêm + bài đăng", sent and "gọi thêm" in sent[-1][0] and "CEO không tự dừng đăng bài" in sent[-1][0])
check("lần sau không dừng lại kênh đang dừng", all(a["key"] != "pages" for a in F.plan()))

# hết 30 ngày: tự chạy lại, không dừng ngay vì số liệu cũ
db.set_setting("focus_paused", json.dumps({"pages": db.today()}))
r = F.run()
check("hết hạn: tự chạy lại, chưa dừng lại ngay", db.get_settings()["prospect_pages"] == "1" and "pages" not in F.paused()
      and any("Chạy lại" in d for d in r["done"]) and all(a["key"] != "pages" for a in F.plan()))

# chờ sếp duyệt
db.set_setting("ceo_mode", "approve"); db.set_setting("focus_resumed", "{}"); db.set_setting("prospect_groups_per_run", "3")
r = F.run()
check("chờ duyệt: chỉ đề xuất, chưa đổi gì", r["proposed"] and db.get_settings()["prospect_pages"] == "1" and sent[-1][1])
c.post(f"/api/ceo/decisions/{r['proposed']}", json={"approve": True})
check("sếp duyệt: CEO làm", db.get_settings()["prospect_pages"] == "0" and db.one("SELECT status FROM ceo_decisions WHERE id=?", (r["proposed"],))["status"] == "done")
check("sếp bấm Chạy lại", c.post("/api/focus/resume/pages").status_code == 200 and db.get_settings()["prospect_pages"] == "1")
check("không cho dừng kênh bình luận qua API", c.post("/api/focus/resume/comment").status_code == 400)

p = ceo_orders._rule_plan("kênh nào ra đơn vậy em, dồn sức vào đó")
check(f"CEO hiểu lệnh: {p['actions']}", p["actions"] and p["actions"][0]["type"] == "focus_review")
msg = ceo_orders.execute(p["actions"][0])
check("CEO trả lời có từng kênh", "Trang, shop livestream" in msg)
check("API /focus", c.get("/api/focus").json()["min_called"] == 5)
print(("XONG" if all(ok) else "CÓ LỖI") + f" {sum(ok)}/{len(ok)}")

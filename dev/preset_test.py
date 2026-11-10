"""Gói Cân bằng: Hà tư vấn khách + CEO hiểu lệnh dùng Sonnet, CEO chấm bài dùng Haiku; nâng cấp không đè cấu hình tùy chỉnh."""
import os, sys
from pathlib import Path
from types import SimpleNamespace as NS
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "backend"))
SP = Path(os.environ.get("MT_WORK") or Path(__file__).resolve().parent / "work"); SP.mkdir(exist_ok=True)
import db
db.DB_PATH = SP / "preset.db"; db.DB_PATH.unlink(missing_ok=True); db.init(); db.set_setting("anthropic_api_key", "")
import llm as L

ok = []
def check(name, cond): ok.append(bool(cond)); print(("OK  " if cond else "LỖI ") + name)
m = lambda: {t: L.model_for(t) for t in ("posts", "replies", "ceo", "review", "meeting")}
check(f"cài mới: {m()}", m() == {"posts": L.SONNET, "replies": L.SONNET, "ceo": L.SONNET, "review": L.HAIKU, "meeting": L.HAIKU})

# máy cũ đang dùng gói Cân bằng (Haiku cho tin nhắn, CEO) -> nâng cấp
for k, v in (("model_replies", L.HAIKU), ("model_ceo", L.HAIKU), ("preset_v2", "0"), ("cost_preset", "can_bang")):
    db.set_setting(k, v)
db.init()
check("máy cũ gói Cân bằng: lên Sonnet", m()["replies"] == L.SONNET and m()["ceo"] == L.SONNET)
db.set_setting("model_replies", L.HAIKU); db.init()
check("chỉ nâng cấp 1 lần (sếp đổi lại Haiku thì giữ)", m()["replies"] == L.HAIKU)

# máy cũ tùy chỉnh -> không đụng
for k, v in (("model_replies", L.HAIKU), ("model_ceo", L.HAIKU), ("preset_v2", "0"), ("cost_preset", "tuy_chinh")):
    db.set_setting(k, v)
db.init()
check("cấu hình tùy chỉnh giữ nguyên", m()["replies"] == L.HAIKU and m()["ceo"] == L.HAIKU)

from fastapi.testclient import TestClient
import main
c = TestClient(main.app)
c.post("/api/costs/preset", json={"name": "tiet_kiem"})
check("gói Tiết kiệm: Haiku hết", set(m().values()) == {L.HAIKU})
c.post("/api/costs/preset", json={"name": "can_bang"})
check("chọn lại Cân bằng", m()["replies"] == L.SONNET and m()["review"] == L.HAIKU)

# CEO chấm bài gọi đúng việc "review"
seen = []
class Fake:
    def create(self, **kw):
        seen.append(kw["model"])
        return NS(stop_reason="tool_use", usage=NS(input_tokens=5, output_tokens=5), content=[NS(type="tool_use", input={"ket_qua": {"score": 80, "tips": []}})])
L.llm.client = NS(messages=Fake())
import ceo_review
ceo_review.review("Xưởng trà túi lọc nhận sỉ cho shop online, nhận gia công nhãn riêng.\n💬 Giá vui lòng liên hệ trực tiếp Zalo 0386992326")
check(f"CEO chấm bài dùng Haiku ({seen})", seen == [L.HAIKU] and db.one("SELECT task FROM usage ORDER BY id DESC LIMIT 1")["task"] == "review")
db.set_setting("monthly_budget_usd", "0.000001"); db.run("INSERT INTO usage(task, model, cost_usd, created_at) VALUES ('x','x',1,?)", (db.now(),))
check("vượt ngân sách vẫn tự về Haiku", m()["replies"] == L.HAIKU or L.budget_state() == "stop")
print(("XONG" if all(ok) else "CÓ LỖI") + f" {sum(ok)}/{len(ok)}")

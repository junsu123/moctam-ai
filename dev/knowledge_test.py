"""Sổ kiến thức chỉ dùng dữ liệu thật: tắt tự học kiến thức chung (mặc định) thì lời dặn không có kiến thức Claude tự viết."""
import os, sys
from pathlib import Path
from types import SimpleNamespace as NS
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "backend"))
SP = Path(os.environ.get("MT_WORK") or Path(__file__).resolve().parent / "work"); SP.mkdir(exist_ok=True)
import db
db.DB_PATH = SP / "knowledge.db"; db.DB_PATH.unlink(missing_ok=True); db.init(); db.set_setting("anthropic_api_key", "")
import knowledge as K, growth, llm as L, ceo_orders

ok = []
def check(name, cond): ok.append(bool(cond)); print(("OK  " if cond else "LỖI ") + name)

def add(src, topic, content):
    return db.run("""INSERT INTO knowledge(agent_id, topic, question, content, source, status, created_at, updated_at)
                     VALUES ('lan',?,?,?,?,'active',?,?)""", (topic, topic, content, src, db.now(), db.now()))
add("study", "Cách viết bài trà túi lọc thu hút", "Mở bài bằng câu hỏi gây tò mò về trà túi lọc, kể chuyện người bán")
add("library", "Viết bài trà túi lọc bán sỉ", "Thư viện: bài trà túi lọc nên có gạch đầu dòng lợi ích")
add("boss", "Sếp dạy viết bài trà túi lọc", "Bài trà túi lọc luôn nói rõ xưởng có GMP, nhận gia công")
add("library", "Luật Facebook: Spam", "Không đăng một bài trà túi lọc y hệt vào nhiều nhóm")
db.init()  # chạy lại migration
check("luật Facebook chuyển nguồn 'rule'", db.one("SELECT source FROM knowledge WHERE topic LIKE 'Luật Facebook:%'")["source"] == "rule")
check("mặc định tắt tự học kiến thức chung", db.get_settings().get("self_study") == "0" and not K.self_study_on())

b = K.block("lan", "viết bài trà túi lọc")
check("lời dặn có sếp dạy + luật", "GMP" in b and "y hệt" in b)
check("lời dặn KHÔNG có kiến thức tự học / thư viện", "tò mò" not in b and "Thư viện:" not in b)
check("Hà không tự trả lời khách bằng kiến thức chung",
      all(h["source"] not in K.GENERIC for h in K.search("lan", "cách viết bài trà túi lọc thu hút", k=9)))
ov = K.overview("lan", limit=400)
check("trang Đào tạo vẫn thấy kiến thức chung, đếm đúng 2",
      {"study", "library"} <= {i["source"] for i in ov["items"]} and K.overview()["generic_count"] == 2)

db.set_setting("self_study", "1")
check("bật lại: lời dặn có kiến thức tự học", "tò mò" in K.block("lan", "viết bài trà túi lọc", k=6))
db.set_setting("self_study", "0")

a = growth._a(growth._state(), "lan")
check("rảnh không học với Claude khi tắt", growth._can_study(a) is False)

# câu hỏi còn chờ và câu khách hỏi thật vẫn được học; giáo trình chung thì không
db.run("INSERT INTO knowledge(agent_id, topic, question, content, source, status, created_at, updated_at) VALUES ('ha','Có chiết khấu không?','Có chiết khấu không?','','claude','pending',?,?)", (db.now(), db.now()))
db.run("INSERT INTO leads(name, need, created_at) VALUES ('Shop A', 'Nhập 200 hộp trà gừng thì ship Hà Nội mất mấy ngày?', ?)", (db.now(),))
t = K.plan_topics("ha", 5)
check(f"Hà chỉ học câu thật ({len(t)} chủ đề)", len(t) == 2 and t[0].get("pending_id") and t[1]["topic"].startswith(K.REAL_Q))
check("Lan không có gì để tự học", K.plan_topics("lan", 3) == [])

class Fake:
    def create(self, **kw):
        return NS(stop_reason="tool_use", usage=NS(input_tokens=10, output_tokens=10), content=[NS(type="tool_use", input={"ket_qua": {"items": [
            {"topic": "Chiết khấu khi nhập nhiều", "question": "Có chiết khấu không?", "content": "Báo khách mức chiết khấu do sếp quyết, mời nhắn Zalo để được báo cụ thể."},
            {"topic": "Thời gian giao hàng Hà Nội", "question": "ship Hà Nội mấy ngày", "content": "Hẹn khách sếp xác nhận lịch giao, thường báo trong ngày khi nhận đơn."}]}})])
L.llm.client = NS(messages=Fake())
ids = K.study_agent("ha", 5)
src = [r["source"] for r in db.q(f"SELECT source FROM knowledge WHERE id IN ({','.join('?' * len(ids))})", tuple(ids))]
check(f"học câu thật lưu nguồn 'claude' (được dùng): {src}", len(ids) == 2 and set(src) == {"claude"})
check("hết câu chờ", db.one("SELECT COUNT(*) n FROM knowledge WHERE status='pending'")["n"] == 0)

msg = ceo_orders.execute({"type": "study_now"})
check("CEO giải thích khi sếp bảo tự học", "dữ liệu thật" in msg)
print(("XONG" if all(ok) else "CÓ LỖI") + f" {sum(ok)}/{len(ok)}")

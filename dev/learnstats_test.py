"""Không học từ quá ít số liệu: đủ mẫu + chênh lệch có ý nghĩa mới ưu tiên / rút bài học; Claude phản tỉnh mỗi tuần."""
import os, sys, random
from pathlib import Path
from types import SimpleNamespace as NS
from datetime import timedelta
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "backend"))
SP = Path(os.environ.get("MT_WORK") or Path(__file__).resolve().parent / "work"); SP.mkdir(exist_ok=True)
import db
db.DB_PATH = SP / "learnstats.db"; db.DB_PATH.unlink(missing_ok=True); db.init(); db.set_setting("anthropic_api_key", "")
import learning as Lr, llm as L
random.seed(7)
ok = []
def check(name, cond): ok.append(bool(cond)); print(("OK  " if cond else "LỖI ") + name)

def post(angle, leads, comments, hour=10):
    t = (db.clock() - timedelta(days=random.randint(1, 20))).strftime("%Y-%m-%d") + f" {hour:02d}:15:00"
    db.run("INSERT INTO posts(agent_id, angle, status, posted_at, leads, comments, created_at) VALUES ('lan',?, 'posted', ?,?,?,?)",
           (angle, t, leads, comments, t))
angles = list(Lr.ANGLE)
A, B = angles[0], angles[1]

# 1) ít bài: 5 bài góc A gặp may (2 khách/bài), 5 bài góc B không ai -> KHÔNG kết luận
for _ in range(5): post(A, 2, 3)
for _ in range(5): post(B, 0, 0)
keys = {l["rule_key"] for l in Lr.rule_lessons("lan")}
check("5 bài/góc: chưa rút bài học về góc", "angle" not in keys)
w = Lr.weights("angle", angles)
check(f"5 bài/góc: trọng số như nhau ({w[A]} vs {w[B]})", abs(w[A] - w[B]) < 1e-6)
check("chưa đủ 40 bài: chưa có giờ vàng", Lr.golden_hours() == [])
check("báo chưa đủ dữ liệu", Lr.data_ready() == {"posts": 10, "need": 40, "each": 15, "ready": False})
db.run("""INSERT INTO lessons(agent_id, text, source, rule_key, confidence, status, created_at, updated_at)
          VALUES ('lan','Ưu tiên góc may mắn cũ','auto','angle',0.7,'active',?,?)""", (db.now(), db.now()))
Lr.reflect("lan", ai=False)
check("bài học cũ rút từ số ít bị bỏ", not db.one("SELECT id FROM lessons WHERE text='Ưu tiên góc may mắn cũ' AND status='active'"))

# 2) đủ mẫu nhưng chênh lệch nhỏ (ngẫu nhiên) -> vẫn không kết luận
db.run("DELETE FROM posts")
for _ in range(20): post(A, random.choice([0, 0, 1]), random.randint(0, 4))
for _ in range(20): post(B, random.choice([0, 0, 1]), random.randint(0, 4))
a, b = Lr.perf("angle")["items"][A], Lr.perf("angle")["items"][B]
check(f"20 bài/góc, chênh lệch nhỏ (z={Lr.z_score(a, b)}): không kết luận", "angle" not in {l["rule_key"] for l in Lr.rule_lessons("lan")})

# 3) đủ mẫu và chênh lệch rõ -> rút bài học, ưu tiên khi chọn
db.run("DELETE FROM posts")
for _ in range(25): post(A, random.choice([1, 1, 2]), random.randint(2, 6), hour=20)
for _ in range(25): post(B, 0, random.randint(0, 2), hour=9)
a, b = Lr.perf("angle")["items"][A], Lr.perf("angle")["items"][B]
rl = {l["rule_key"]: l for l in Lr.rule_lessons("lan")}
check(f"25 bài/góc, chênh rõ (z={Lr.z_score(a, b)}): có bài học + bằng chứng z", "angle" in rl and "z=" in rl["angle"]["evidence"])
w = Lr.weights("angle", angles)
check("đủ dữ liệu: ưu tiên góc tốt khi chọn", w[A] > w[B] * 2)
check(f"giờ vàng có ý nghĩa: {Lr.golden_hours()}", Lr.golden_hours() == [20])

# 4) Hà: 3 tin chốt / 1 mất chưa đủ để rút tỉ lệ chốt
for o in ("won", "won", "won", "lost"):
    db.run("INSERT INTO replies(lead_id, text, sent, outcome, created_at) VALUES (1,'x',1,?,?)", (o, db.now()))
check("Hà: 4 tin chưa đủ để rút tỉ lệ chốt", "close" not in {l["rule_key"] for l in Lr.rule_lessons("ha")})

# 5) Claude phản tỉnh mỗi tuần, không mỗi đêm
calls = []
class Fake:
    def create(self, **kw):
        calls.append(1)
        return NS(stop_reason="tool_use", usage=NS(input_tokens=5, output_tokens=5), content=[NS(type="tool_use", input={"ket_qua": {"new": [], "retire": [], "goal": "Viết 2 bài góc tốt"}})])
L.llm.client = NS(messages=Fake())
Lr.nightly(); n1 = len(calls)
Lr.nightly(); n2 = len(calls)
check(f"đêm đầu Claude phản tỉnh ({n1} lượt), đêm sau không gọi ({n2 - n1})", n1 > 0 and n2 == n1)
db.set_setting("learn_ai_last", (db.clock() - timedelta(days=7)).strftime("%Y-%m-%d"))
Lr.nightly()
check("đủ 7 ngày: phản tỉnh lại", len(calls) > n2)
ev = Lr.evidence("lan")
check("dữ liệu đưa Claude có số bài mỗi mục", all("so_bai" in r for r in ev["theo_goc"]))
print(("XONG" if all(ok) else "CÓ LỖI") + f" {sum(ok)}/{len(ok)}")

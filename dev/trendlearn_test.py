"""Nhi tự học: điểm tương đối theo Trang, bài học kiểu bài / độ dài / khung giờ, độ chính xác chọn xu hướng, áp dụng khi viết bài và đọc xu hướng."""
import os, sys
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "backend"))
from pathlib import Path
from datetime import timedelta
SP = Path(os.environ.get("MT_WORK") or Path(__file__).resolve().parent / "work")
import db
db.DB_PATH = SP / "trendlearn.db"; db.DB_PATH.unlink(missing_ok=True)
db.init(); db.set_setting("anthropic_api_key", ""); db.set_setting("learn_explore", "0")
from fastapi.testclient import TestClient
import main, learning, trend_pages as T, trend_learn as L, llm as LLM
c = TestClient(main.app)
ok = []
def chk(name, cond, extra=""):
    ok.append(bool(cond)); print(("   ✓ " if cond else "   ✗ ") + name, extra)
T._tg = lambda text: []
T.ask_image = lambda pid: True
ago = lambda **k: (db.clock() - timedelta(**k)).strftime("%Y-%m-%d %H:%M:%S")
big = db.run("INSERT INTO fb_pages(name, niche, status, created_at) VALUES ('Bếp Nhà', 'nấu ăn', 'active', ?)", (db.now(),))
small = db.run("INSERT INTO fb_pages(name, niche, status, created_at) VALUES ('Góc Mèo', 'nuôi mèo', 'active', ?)", (db.now(),))
words = lambda n: " ".join(["chữ"] * n)
def post(pg, topic, kind, n_words, hour, react, day):
    db.run("""INSERT INTO posts(agent_id, target_type, content, status, fb_page_ref, trend_topic, trend_kind, reactions, comments, shares, posted_at, created_at)
              VALUES ('nhi','page',?, 'posted', ?, ?, ?, ?, 0, 0, ?, ?)""",
           (words(n_words), pg, topic, kind, react, (db.clock() - timedelta(days=day)).strftime(f"%Y-%m-%d {hour:02d}:00:00"), db.now()))
# Trang lớn tương tác gấp 10 Trang nhỏ; ở cả hai, bài bền + vừa + tối tốt gấp ~2 lần bài tin nóng + ngắn + sáng
for i in range(10):
    post(big, "nấu ăn", "evergreen", 100, 20, 200 + i * 5, 1 + i)
    post(big, f"tin nóng {i}", "trend", 50, 8, 90 + i * 5, 1 + i)
    post(small, "nuôi mèo", "evergreen", 100, 20, 20 + i, 1 + i)
    post(small, f"tin mèo {i}", "trend", 50, 8, 9 + i, 1 + i)
rs = L.rows()
chk("điểm tương đối theo Trang: Trang nhỏ không bị Trang lớn lấn", len(rs) == 40 and
    abs(sum(r["rel"] for r in rs if r["page_id"] == small) / 20 - sum(r["rel"] for r in rs if r["page_id"] == big) / 20) < 0.15,
    round(sum(r["rel"] for r in rs if r["page_id"] == small) / 20, 2))
les = {l["rule_key"]: l for l in L.rule_lessons()}
chk("bài học kiểu bài, độ dài, khung giờ khi chênh rõ", {"tp_kind", "tp_len", "tp_slot"} <= set(les) and "bền" in les["tp_kind"]["text"]
    and "vừa" in les["tp_len"]["text"] and "tối" in les["tp_slot"]["text"], list(les))
r = learning.reflect("nhi", ai=False)
act = learning.active_lessons("nhi")
chk("learning.reflect('nhi') ghi bài học + mục tiêu, có trong lời dặn", r["added"] >= 3 and r["goal"] and "bền" in learning.prompt_block("nhi"), r)
chk("Đào tạo: kỹ năng riêng của Nhi", any(s["label"].startswith("Tương tác TB") and s["now"] for s in learning.skills("nhi")))
chk("bài Trang không làm lệch giờ vàng nhóm của Tuấn", learning.perf("hour")["n"] == 0)
# ít mẫu: không rút bài học, bỏ bài học thống kê cũ
db.set_setting("trend_learn_min", "50")
learning.reflect("nhi", ai=False)
chk("ít mẫu: không rút bài học, bỏ bài học cũ", not L.rule_lessons() and not [l for l in learning.active_lessons("nhi") if (l["rule_key"] or "").startswith("tp_")])
db.set_setting("trend_learn_min", "8")
# áp dụng khi viết: có xu hướng hợp ngách nhưng số liệu nói bài bền tốt hơn
db.run("INSERT INTO trend_hot(day, title, score, niche, why, created_at) VALUES (?, 'món nấu ăn hot', 90, 'nấu ăn', 'đang lên', ?)", (db.today(), db.now()))
asks = []
orig = LLM.llm.json
LLM.llm.json = lambda system, prompt, mock=None, **k: asks.append(prompt) or (mock() if mock else {})
pg = db.one("SELECT * FROM fb_pages WHERE id=?", (big,))
p = T.write_post(pg, (db.clock() + timedelta(hours=2)).strftime("%Y-%m-%d %H:%M"))
chk("viết bài theo kiểu học được (bài bền), độ dài vừa, có bài mẫu của Trang", p["trend_kind"] == "evergreen" and p["trend_topic"] == "nấu ăn"
    and "80–120 chữ" in asks[-1] and "Kinh nghiệm từ số liệu Trang" in asks[-1] and "hưởng ứng nhất" in asks[-1], p["trend_kind"])
db.set_setting("learn_explore", "1")
p = T.write_post(pg, (db.clock() + timedelta(hours=3)).strftime("%Y-%m-%d %H:%M"))
chk("vẫn chừa lượt thử kiểu còn lại", p["trend_kind"] == "trend" and p["trend_topic"] == "món nấu ăn hot" and "thử kiểu còn lại" in asks[-1], p["trend_topic"])
db.set_setting("learn_explore", "0")
# độ chính xác chọn xu hướng
for i in range(12):
    d = (db.clock() - timedelta(days=4 + i % 6)).strftime("%Y-%m-%d")
    db.run("INSERT INTO trend_hot(day, title, score, niche, created_at) VALUES (?, ?, 80, 'x', ?)", (d, f"chủ đề {i}", db.now()))
    db.run("INSERT INTO trends(title, traffic_n, day) VALUES (?, 1000, ?)", (f"chủ đề {i}", d))
    if i < 3:  # chỉ 3/12 còn nóng hôm sau
        db.run("INSERT INTO trends(title, traffic_n, day) VALUES (?, 1000, date(?, '+1 day'))", (f"Chủ Đề {i} hôm nay", d))
cb = L.calibration()
chk("chấm mắt chọn xu hướng: 3/12 chủ đề chấm cao còn nóng", cb["n"] == 12 and cb["hit"] == 3 and cb["pct"] == 25, cb)
chk("độ chính xác thấp → bài học chấm chặt hơn", any(l["rule_key"] == "tp_calib" for l in L.rule_lessons()))
db.run("INSERT INTO trends(title, traffic, traffic_n, news, day) VALUES ('món nấu ăn hot', '20K+', 20000, '[]', ?)", (db.today(),))
T.research(fetch=lambda: [])
chk("đọc xu hướng: đề bài có kết quả chủ đề cũ + độ chính xác", "Bạn tự học từ kết quả trước" in asks[-1] and "Độ chính xác của bạn: 25%" in asks[-1])
LLM.llm.json = orig
learning.reflect("nhi", ai=False)
d = c.get("/api/trends").json()["learn"]
chk("API Trang xu hướng có thẻ Nhi tự học", d["n"] >= 40 and d["kind"][0]["key"] == "evergreen" and d["calib"]["pct"] == 25 and d["lessons"] and d["best_slot"], list(d))
print(f"XONG {sum(ok)}/{len(ok)}")

"""Claude kèm cặp từng agent từ việc thật: ghi kết quả thật, đủ 5 kết quả mới thì gửi một lô (giảm 50%), nhận bài học."""
import os, sys, json, time
from pathlib import Path
from datetime import datetime
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "backend"))
SP = Path(os.environ.get("MT_WORK") or Path(__file__).resolve().parent / "work"); SP.mkdir(exist_ok=True)
import db
db.DB_PATH = SP / "coach.db"; db.DB_PATH.unlink(missing_ok=True); db.init(); db.set_setting("anthropic_api_key", "")
import coach as C, learning, replies, junk, ceo_review, ceo_orders, workflows, llm as L

ok = []
def check(name, cond): ok.append(bool(cond)); print(("OK  " if cond else "LỖI ") + name)
P = lambda c, **k: db.run("INSERT INTO posts(content, status, target_type, created_at) VALUES (?,?,?,?)", (c, k.get("st", "draft"), "group", db.now()))

# ---- kết quả thật được ghi ngay ở nơi xảy ra
p = [P(f"Bài {i}: Xưởng trà túi lọc MỘC TÂM tìm đại lý sỉ, inbox Zalo") for i in range(6)]
learning.record_feedback(p[0], "approve")
learning.record_feedback(p[1], "edit", "Bài dài dòng", "Bài ngắn gọn")
learning.record_feedback(p[2], "reject", "Bài 2", "", "Nhiều emoji quá")
learning.record_feedback(p[3], "approve", "Bài 3", by="ceo")
check("Lan: sếp duyệt / sửa / loại được ghi kèm nội dung", C.pending("lan") == 4 and
      db.one("SELECT result FROM coach_outcomes WHERE verdict='edit'")["result"].startswith("Sếp sửa thành: Bài ngắn gọn"))
gid = db.run("INSERT INTO groups(name, created_at) VALUES ('Hội Bán Hàng Online', ?)", (db.now(),))
db.run("UPDATE posts SET group_id=?, status='posted', posted_at=?, leads=1, reviewed_by='ceo' WHERE id=?", (gid, db.now(), p[4]))
learning.on_post_leads(p[4], 1)
check("bài có khách: Lan, Tuấn (nhóm), CEO (bài CEO duyệt) cùng được ghi tốt",
      C.pending("lan") == 5 and C.pending("tuan") == 1 and C.pending("ceo") == 1)
ceo_review.on_boss_correction(db.one("SELECT * FROM posts WHERE id=?", (p[4],)), None, "sai thông tin")
check("CEO: sếp hủy bài CEO duyệt được ghi", C.pending("ceo") == 2)
lid = db.run("INSERT INTO leads(name, status, origin, need, created_at) VALUES ('Shop An','new','prospect','Bán trà livestream',?)", (db.now(),))
db.run("INSERT INTO replies(lead_id, text, sent, created_at) VALUES (?, 'Dạ bên em gửi mẫu thử nhé', 1, ?)", (lid, db.now()))
learning.on_lead_status(lid, "ordered")
check("khách chốt đơn: Hà (tin nhắn đã gửi) và Mai (khách Mai tìm) được ghi tốt",
      C.pending("ha") == 1 and C.pending("mai") == 1)
lid2 = db.run("INSERT INTO leads(name, status, origin, created_at) VALUES ('Shop Rác','new','prospect',?)", (db.now(),))
junk.mark(lid2, "wrong_industry" if "wrong_industry" in junk.REASONS else list(junk.REASONS)[0], "bán mỹ phẩm")
check("Mai: sếp loại data rác được ghi", C.pending("mai") == 2)
for i in range(3):
    db.run("INSERT INTO reply_tasks(account_id, post_url, post_text, reply, status, created_at) VALUES (1,?,?,?,'draft',?)",
           (f"https://fb.com/p/{i}", "Ai có nguồn trà túi lọc sỉ không ạ", "Dạ bên em là xưởng trà túi lọc", db.now()))
replies.approve(1); replies.approve(2, "Dạ em là xưởng, gửi mẫu cho chị nhé"); replies.skip(3, as_junk=False)
check("Bảo: duyệt / sửa / bỏ qua được ghi", [r["verdict"] for r in db.q("SELECT verdict FROM coach_outcomes WHERE agent_id='bao' ORDER BY id")] == ["good", "edit", "bad"])
C.note("lan", "good", "x", "Sếp duyệt ngay, không sửa", f"post:{p[0]}")
check("cùng một kết quả không ghi hai lần", C.pending("lan") == 5)

# ---- chỉ agent đủ 5 kết quả mới mới được kèm; chưa có khóa thì không gọi
check("chỉ agent đủ 5 kết quả mới đến lượt", C.due_agents() == ["lan"])
check("chưa có khóa Claude: không gọi, nói rõ", "khóa" in C.run()["msg"])

class FakeClient: pass
L.llm.client = FakeClient()
sent = []; status = {"v": "in_progress"}
L.llm.batch_create = lambda task, items, max_tokens=0: sent.append((task, items)) or f"lo-{time.time()}"
L.llm.batch_status = lambda bid: status["v"]
old = learning.add_lesson("lan", "Viết bài thật dài, kể chuyện xưởng", "", "auto", 0.6)
answer = {"assessment": "Bài ngắn, nói thẳng tìm đại lý được duyệt; bài dài bị sửa.",
          "lessons": [{"text": "Giữ bài dưới 120 chữ, câu đầu nói rõ tìm đại lý sỉ", "evidence": "#1 #2"},
                      {"text": "Tăng số bài mỗi ngày lên 10 bài", "evidence": "#3"}],
          "retire": [old], "check": "Câu đầu đã nói tìm đại lý chưa?"}
L.llm.batch_results = lambda bid, task: {"coach-lan": json.dumps(answer, ensure_ascii=False)}
r = C.run()
check("gửi MỘT lô qua Batch API (giảm 50%), không qua CEO", sent and sent[0][0] == "coach" and len(sent[0][1]) == 1
      and "Sếp sửa thành" in sent[0][1][0]["prompt"] and r["sent"] == ["lan"])
check("mô hình kèm cặp theo gói chi phí", db.get_settings().get("model_coach") == L.SONNET)
check("đang có lô chờ: không gửi thêm", "Đang có" in C.run(force=True)["msg"] and len(sent) == 1)
called = []; workflows.llm.batch_results = lambda *a: called.append(a) or {}
status["v"] = "ended"; workflows.poll_batches()
check("lô viết bài không nhận nhầm lô kèm cặp", not called)
L.llm.batch_results = lambda bid, task: {"coach-lan": json.dumps(answer, ensure_ascii=False)}
C.poll()
les = db.q("SELECT text, source, status FROM lessons WHERE agent_id='lan'")
check("ghi bài học vào sổ tay của Lan", any(l["source"] == "coach" and "120 chữ" in l["text"] for l in les))
check("bài học tăng số bài (lách giới hạn) bị loại", not any("10 bài" in l["text"] for l in les))
check("bỏ bài học mà kết quả thật chứng minh sai", db.one("SELECT status FROM lessons WHERE id=?", (old,))["status"] == "retired")
check("kết quả đã kèm không gửi lại", C.pending("lan") == 0 and not db.one("SELECT 1 FROM coach_outcomes WHERE agent_id='lan' AND coached_at IS NULL"))
ov = C.overview(); lan = [a for a in ov["agents"] if a["agent"] == "lan"][0]
check("trang Đào tạo có nhận xét, bài học, câu tự kiểm", lan["assessment"] and lan["lessons"] and lan["check"] and lan["times"] == 1)

# ---- 7 ngày mới kèm lại; Claude lỗi thì trả kết quả về hàng chờ
for i in range(5):
    C.note("lan", "bad", f"bài {i}", f"Sếp loại bài số {i}", f"post:x{i}")
check("vừa kèm xong: chờ đủ 7 ngày", C.due_agents() == [] and C.due_agents(force=True) == ["lan"])
sent.clear(); status["v"] = "in_progress"; C.run(force=True)
status["v"] = "ended"; L.llm.batch_results = lambda bid, task: {"coach-lan": None}; C.poll()
check("Claude lỗi: kết quả về hàng chờ, lần sau gửi lại", C.pending("lan") == 5)

# ---- lượt chung mỗi tuần không gọi Claude lần nữa cho agent đã được kèm riêng
ref = []; learning._llm_reflect = lambda a: ref.append(a) or None
learning.reflect("lan", True); learning.reflect("minh", True)
check("phản tỉnh chung bỏ phần gọi Claude cho agent được kèm (không trả tiền hai lần)", ref == ["minh"])

# ---- lịch: mỗi ngày một lần sau 22:30
runs = []; C.run = lambda force=False: runs.append(force) or {"msg": ""}
C.poll = lambda: 0
C.tick(datetime(2030, 1, 1, 21, 0)); C.tick(datetime(2030, 1, 1, 22, 40)); C.tick(datetime(2030, 1, 1, 23, 0))
check("tự gửi mỗi ngày một lần sau giờ kèm cặp", runs == [False])
check("nhắn CEO “cho các agent kèm cặp với Claude”", "Dạ" in ceo_orders.handle("cho các agent kèm cặp với Claude")["reply"] and runs[-1] is True)
print(f"XONG {sum(ok)}/{len(ok)}")

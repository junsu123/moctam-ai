"""Lan chỉnh bài theo nhóm: chỉ khi nhóm có dữ liệu thật; giữ Zalo, không phạm luật; đổi nhóm thì chỉnh lại từ bài gốc."""
import os, sys
from pathlib import Path
from types import SimpleNamespace as NS
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "backend"))
SP = Path(os.environ.get("MT_WORK") or Path(__file__).resolve().parent / "work"); SP.mkdir(exist_ok=True)
import db
db.DB_PATH = SP / "groupfit.db"; db.DB_PATH.unlink(missing_ok=True); db.init(); db.set_setting("anthropic_api_key", "")
import group_fit as F, pricing, llm as L

ok = []
def check(name, cond): ok.append(bool(cond)); print(("OK  " if cond else "LỖI ") + name)

Z = pricing.contact_line()
BASE = "Xưởng trà túi lọc nhận sỉ cho shop online, có GMP, nhận gia công nhãn riêng.\n- Trà gừng mật ong\n- Trà sen\n" + Z
later = (db.clock().replace(microsecond=0)).strftime("%Y-%m-%d") + " 23:59"
g1 = db.run("INSERT INTO groups(name, topic, created_at) VALUES ('Hội Nguồn Hàng Sỉ', 'nguồn hàng', ?)", (db.now(),))
g2 = db.run("INSERT INTO groups(name, created_at) VALUES ('Nhóm Mới Toanh', ?)", (db.now(),))
pid = db.run("""INSERT INTO posts(agent_id, target_type, group_id, content, status, scheduled_for, created_at, source)
                VALUES ('lan','group',?,?,'scheduled',?,?,'template')""", (g1, BASE, later, db.now()))
for t in ["Ai có nguồn trà túi lọc gừng sỉ không ạ, shop em bán livestream", "Cần nhập trà sen túi lọc số lượng ổn định, xin giá sỉ"]:
    db.run("INSERT INTO reply_tasks(group_id, post_url, post_text, kind, created_at) VALUES (?,?,?,'buyer',?)", (g1, t[:10], t, db.now()))
check("nhóm 1 đủ dữ liệu, nhóm 2 không", F.ready(F.context(g1)) and not F.ready(F.context(g2)))
check("prompt có câu hỏi thật của nhóm", "livestream" in F._prompt(BASE, F.context(g1)))

calls = []
class Fake:
    def __init__(self, content): self.content = content
    def create(self, **kw):
        calls.append(kw)
        return NS(stop_reason="tool_use", usage=NS(input_tokens=10, output_tokens=10),
                  content=[NS(type="tool_use", input={"ket_qua": {"content": self.content, "note": "mở đầu nhắm shop livestream tìm nguồn trà gừng"}})])
GOOD = "Shop livestream đang tìm nguồn trà túi lọc gừng, trà sen sỉ? Xưởng có GMP, nhận gia công nhãn riêng.\n- Trà gừng mật ong\n- Trà sen\n" + Z

# chưa có khóa: không gọi Claude, giữ bài
F.run(); p = db.one("SELECT * FROM posts WHERE id=?", (pid,))
check("chưa có khóa: giữ nguyên, không gọi lại", p["content"] == BASE and p["fit_group_id"] == g1 and not F.due())

db.run("UPDATE posts SET fit_group_id=NULL WHERE id=?", (pid,))
L.llm.client = NS(messages=Fake(GOOD))
r = F.run(); p = db.one("SELECT * FROM posts WHERE id=?", (pid,))
check(f"có dữ liệu: chỉnh bài {r}", r["fitted"] == 1 and p["content"] == GOOD and p["orig_content"] == BASE and "câu hỏi mua" in p["fit_note"])

# đổi sang nhóm chưa có dữ liệu: trả bài gốc, không gọi Claude
n = len(calls); db.run("UPDATE posts SET group_id=? WHERE id=?", (g2, pid))
r = F.run(); p = db.one("SELECT * FROM posts WHERE id=?", (pid,))
check(f"đổi nhóm thiếu dữ liệu: trả bài gốc {r}", p["content"] == BASE and len(calls) == n and r["restored"] == 1)

# bản chỉnh mất Zalo -> giữ gốc; bản chỉnh hứa chữa bệnh -> giữ gốc
db.run("UPDATE posts SET group_id=? WHERE id=?", (g1, pid))
L.llm.client = NS(messages=Fake("Shop livestream tìm nguồn trà gừng sỉ? Xưởng có GMP, nhận gia công. Trà gừng mật ong, trà sen ngon lắm nha"))
F.run(); p = db.one("SELECT * FROM posts WHERE id=?", (pid,))
check("bản chỉnh thiếu Zalo: tự gắn lại dòng liên hệ", pricing.has_contact(p["content"]))
db.run("UPDATE posts SET fit_group_id=NULL WHERE id=?", (pid,))
L.llm.client = NS(messages=Fake("Trà gừng chữa khỏi đau dạ dày! Xưởng có GMP, nhận gia công.\n- Trà gừng mật ong\n- Trà sen\n" + Z))
F.run(); p = db.one("SELECT * FROM posts WHERE id=?", (pid,))
check("phạm luật Facebook -> giữ bài gốc", "chữa" not in p["content"] and "luật Facebook" in p["fit_note"])

# sếp sửa chữ: không chỉnh đè
db.run("UPDATE posts SET fit_group_id=NULL WHERE id=?", (pid,))
from fastapi.testclient import TestClient
import main
c = TestClient(main.app)
c.patch(f"/api/posts/{pid}", json={"content": "Bài sếp tự viết. " + Z})
L.llm.client = NS(messages=Fake(GOOD)); F.run(); p = db.one("SELECT * FROM posts WHERE id=?", (pid,))
check("sếp sửa: không chỉnh đè", p["content"].startswith("Bài sếp tự viết") and p["orig_content"] is None and not F.due())

# bài sắp đăng (dưới 3 phút) không đụng tới
pid2 = db.run("""INSERT INTO posts(agent_id, target_type, group_id, content, status, scheduled_for, created_at)
                 VALUES ('lan','group',?,?,'scheduled',?,?)""", (g1, BASE, db.clock().strftime("%Y-%m-%d %H:%M"), db.now()))
check("bài sắp đăng không chỉnh", all(x["id"] != pid2 for x in F.due()))
check("API trả fit_note", any(x.get("fit_note") is not None or "fit_note" in x for x in c.get("/api/posts").json()))
print(("XONG" if all(ok) else "CÓ LỖI") + f" {sum(ok)}/{len(ok)}")

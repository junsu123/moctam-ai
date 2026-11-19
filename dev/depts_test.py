"""Phòng ban: trưởng phòng tự đánh giá (luật số liệu), đề xuất tuyển, CEO xét (số liệu, trần, vốn, quyền), nhân viên mới làm việc thật."""
import os, sys
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "backend"))
from pathlib import Path
SP = Path(os.environ.get("MT_WORK") or Path(__file__).resolve().parent / "work")
import db
db.DB_PATH = SP / "depts.db"; db.DB_PATH.unlink(missing_ok=True)
db.init(); db.set_setting("anthropic_api_key", ""); db.set_setting("site_auto_publish", "0")
from fastapi.testclient import TestClient
import main, departments as D, agents, ceo, website, trend_pages as T, trend_create as C, llm as LLM
c = TestClient(main.app)
ok = []
def chk(name, cond, extra=""):
    ok.append(bool(cond)); print(("   ✓ " if cond else "   ✗ ") + name, extra)
tg = []
ceo._tg = lambda text, buttons=None: tg.append(text)
d = c.get("/api/departments").json()
chk("5 phòng, đúng trưởng phòng", [x["key"] for x in d["depts"]] == D.ORDER and {x["key"]: x["head"] for x in d["depts"]} ==
    {"director": "ceo", "sales": "minh", "groups": "tuan", "pages": "nhi", "website": "vy"})
chk("trưởng phòng thăng chức, lời dặn có phòng ban + cách nghĩ riêng", agents.AGENTS["vy"]["role"].startswith("Trưởng phòng")
    and "trưởng phòng" in agents.system_prompt("vy").lower() and "từ khóa" in D.prompt_block("vy") and "Trưởng phòng là" in agents.system_prompt("bao"))
# website ít từ khóa: không cần người
r = c.post("/api/departments/website/review").json()
chk("ít việc: trưởng phòng không đề xuất tuyển", r["summary"] and not r["decisions"], r["bottleneck"])
for i in range(20):
    db.run("INSERT INTO site_keywords(keyword, priority, status, created_at) VALUES (?, 2, 'planned', ?)", (f"từ khóa {i}", db.now()))
db.run("INSERT INTO site_posts(keyword, title, slug, status, seo_score, created_at) VALUES ('a','A','a','draft',86,?)", (db.now(),))
r = c.post("/api/departments/website/review").json()
dn = (r["decisions"] or [{}])[0]
st = D.staff("website")
chk("thiếu sức viết: đề xuất Biên tập viên SEO, CEO tự quyết tuyển", dn.get("status") == "done" and len(st) == 1 and st[0]["desk"] in (20, 21)
    and any("Biên tập viên SEO" in t for t in tg), dn)
sid = f"st-{st[0]['id']}"
chk("nhân viên mới là agent: văn phòng, lời dặn, phòng ban", any(a["id"] == sid and a["kind"] == "staff" for a in agents.public_list())
    and "Phòng Website" in agents.system_prompt(sid) and D.dept_of(sid) == "website")
# nhân viên viết bài thật
website._ai_article = lambda kw, fix=None, prev=None: None
p = website.write(agent=sid)
chk("Biên tập viên SEO viết bài website ghi tên mình", db.one("SELECT author FROM site_posts WHERE id=?", (p["id"],))["author"] == sid, p.get("id"))
r = c.post("/api/departments/website/review").json()
r2 = c.post("/api/departments/website/review").json()
chk("trần 2 người mỗi vị trí", len(D.staff("website")) == 2 and any(x["status"] == "rejected" and "đủ 2" in (x.get("why") or "") for x in r2["decisions"]), r2["decisions"])
# quyền CEO chờ sếp duyệt
db.set_setting("ceo_mode", "approve")
for i in range(4):
    pg = db.run("INSERT INTO fb_pages(name, niche, status, created_at) VALUES (?, 'mèo', 'active', ?)", (f"Trang {i}", db.now()))
r = c.post("/api/departments/pages/review").json()
pend = db.one("SELECT * FROM dept_proposals WHERE dept='pages' ORDER BY id DESC")
chk("quyền chờ sếp duyệt: đề xuất Biên tập Trang chờ sếp", ceo.mode() == "approve" and pend["status"] == "pending" and not D.staff("pages"), pend)
r = c.post(f"/api/departments/proposals/{pend['id']}/approve").json()
ed = D.staff("pages")
chk("sếp duyệt: tuyển Biên tập Trang, phòng được tạo thêm Trang", r["status"] == "done" and len(ed) == 1 and C.per_week() == 2, r)
writers = {D.writer_for_page(x["id"]) for x in db.q("SELECT id FROM fb_pages")}
chk("bài Trang chia cho Nhi và Biên tập Trang", writers == {"nhi", f"st-{ed[0]['id']}"}, writers)
T.ask_image = lambda pid: True
pgx = next(x for x in db.q("SELECT * FROM fb_pages") if D.writer_for_page(x["id"]) != "nhi")
post = T.write_post(pgx, db.today() + " 23:00")
chk("Biên tập Trang viết bài Trang ghi tên mình", post["agent_id"] == f"st-{ed[0]['id']}", post["agent_id"])
chk("sếp cho nghỉ", c.post(f"/api/departments/staff/{ed[0]['id']}/leave").json()["ok"] and not D.staff("pages") and C.per_week() == 1)
chk("Phòng Hội nhóm: chưa đủ nhóm thì không xin người", not c.post("/api/departments/groups/review").json()["decisions"])
chk("Phòng Giám đốc không tự đánh giá kiểu phòng", c.post("/api/departments/director/review").status_code == 400)
# Claude trưởng phòng: đề xuất vị trí không thuộc phòng bị bỏ
LLM.LLM.live = property(lambda self: True)
orig = LLM.llm.json
LLM.llm.json = lambda system, prompt, mock=None, **k: {"summary": "Tình hình ổn", "bottleneck": "x", "plan": ["a", "b", "c"],
                                                         "proposals": [{"position": "seo_writer", "reason": "muốn thêm người"}]}
r = c.post("/api/departments/groups/review").json()
LLM.llm.json = orig; LLM.LLM.live = property(lambda self: self.client is not None)
chk("Claude đề xuất vị trí của phòng khác: bỏ", r["summary"] == "Tình hình ổn" and len(r["plan"]) == 3 and not r["decisions"], r["decisions"])
print(f"XONG {sum(ok)}/{len(ok)}")

"""Máy chủ web: API cho giao diện quản lý công ty Agent AI.
Chạy:  python main.py   rồi mở http://localhost:8000
"""
import json
import os
import time
from pathlib import Path

import uvicorn
from fastapi import FastAPI, HTTPException
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

import base64
import re

import agents
import browser_poster
import db
import facebook
import meeting
import scheduler
import workflows
from llm import llm, MODEL

FRONTEND = Path(__file__).resolve().parent.parent / "frontend"
app = FastAPI(title="Công ty Agent AI - Phòng Kinh doanh")


@app.on_event("startup")
def startup():
    db.init()
    scheduler.start()


# ------------------------------------------------------------------ chung
@app.get("/api/health")
def health():
    return {"ok": True, "ai_live": llm.live, "model": MODEL if llm.live else "mô phỏng"}


@app.get("/api/agents")
def list_agents():
    out = agents.public_list()
    login_txt = {"ok": "Nick sẵn sàng", "not_logged_in": "Chờ sếp đăng nhập Facebook", "checkpoint": "Nick bị checkpoint, đã dừng"}
    sales_by_id = {f"sale-{r['id']}": r for r in db.q("SELECT id, login_status FROM sales")}
    for a in out:
        a["status"] = workflows.STATUS.get(a["id"]) or {"state": "idle", "text": "Đang sẵn sàng"}
        if a["id"] in sales_by_id:
            a["login_status"] = sales_by_id[a["id"]]["login_status"]
            if a["status"].get("state") == "idle":
                a["status"] = {"state": "idle", "text": login_txt.get(a["login_status"], "")}
        a["tasks"] = db.q("SELECT * FROM tasks WHERE agent_id=? AND status!='done' ORDER BY id DESC LIMIT 5", (a["id"],))
    return out


@app.get("/api/dashboard")
def dashboard():
    return {"stats": workflows.stats(),
            "activity": db.q("SELECT * FROM activity ORDER BY id DESC LIMIT 30"),
            "meeting_running": meeting.is_running()}


# ------------------------------------------------------------------ sản phẩm
class Product(BaseModel):
    name: str
    category: str = ""
    description: str = ""
    wholesale_price: str = ""
    retail_price: str = ""
    moq: str = ""
    selling_points: str = ""


@app.get("/api/products")
def products():
    return db.q("SELECT * FROM products ORDER BY id")


@app.post("/api/products")
def add_product(p: Product):
    pid = db.run("""INSERT INTO products(name, category, description, wholesale_price, retail_price, moq,
                    selling_points, created_at) VALUES (?,?,?,?,?,?,?,?)""",
                 (p.name, p.category, p.description, p.wholesale_price, p.retail_price, p.moq, p.selling_points, db.now()))
    return db.one("SELECT * FROM products WHERE id=?", (pid,))


@app.delete("/api/products/{pid}")
def del_product(pid: int):
    db.run("DELETE FROM products WHERE id=?", (pid,))
    return {"ok": True}


# ------------------------------------------------------------------ hội nhóm
class Group(BaseModel):
    name: str
    url: str = ""
    topic: str = ""
    members: int = 0
    rules: str = ""
    min_days_between_posts: int = 3
    note: str = ""


@app.get("/api/groups")
def groups():
    rows = db.q("SELECT * FROM groups ORDER BY leads_count DESC, members DESC")
    for g in rows:
        g["ready"] = workflows.group_ready(g)
    return rows


@app.post("/api/groups")
def add_group(g: Group):
    gid = db.run("""INSERT INTO groups(name, url, topic, members, rules, min_days_between_posts, note, created_at)
                    VALUES (?,?,?,?,?,?,?,?)""",
                 (g.name, g.url, g.topic, g.members, g.rules, g.min_days_between_posts, g.note, db.now()))
    db.log("tuan", "Thêm nhóm", g.name)
    return db.one("SELECT * FROM groups WHERE id=?", (gid,))


@app.delete("/api/groups/{gid}")
def del_group(gid: int):
    db.run("DELETE FROM groups WHERE id=?", (gid,))
    return {"ok": True}


# ------------------------------------------------------------------ bài đăng
class GenReq(BaseModel):
    count: int = 3
    product_id: int | None = None
    target_type: str = "group"
    angle: str | None = None
    note: str = ""


class PostPatch(BaseModel):
    status: str | None = None
    content: str | None = None
    title: str | None = None
    group_id: int | None = None
    sale_id: int | None = None
    scheduled_for: str | None = None
    comments: int | None = None
    leads: int | None = None


class MarkPosted(BaseModel):
    posted_url: str = ""
    poster: str = ""


@app.get("/api/posts")
def posts(status: str | None = None):
    sql = """SELECT p.*, pr.name product_name, g.name group_name, g.url group_url, s.name sale_name FROM posts p
             LEFT JOIN products pr ON pr.id=p.product_id LEFT JOIN groups g ON g.id=p.group_id
             LEFT JOIN sales s ON s.id=p.sale_id"""
    return db.q(sql + (" WHERE p.status=?" if status else "") + " ORDER BY p.id DESC LIMIT 200",
                (status,) if status else ())


@app.post("/api/posts/generate")
def gen_posts(r: GenReq):
    return workflows.generate_posts(min(max(r.count, 1), 10), r.product_id, r.target_type, r.angle, r.note)


@app.patch("/api/posts/{pid}")
def patch_post(pid: int, p: PostPatch):
    fields = {k: v for k, v in p.model_dump().items() if v is not None}
    if fields:
        db.run(f"UPDATE posts SET {', '.join(k + '=?' for k in fields)} WHERE id=?", (*fields.values(), pid))
    if p.leads is not None:  # cập nhật số khách của nhóm để Khoa xếp hạng
        db.run("""UPDATE groups SET leads_count=(SELECT COALESCE(SUM(leads),0) FROM posts WHERE group_id=groups.id)""")
    if p.status == "approved":
        db.log("minh", "Duyệt bài", f"Sếp duyệt bài #{pid}")
    return db.one("SELECT * FROM posts WHERE id=?", (pid,))


@app.post("/api/posts/{pid}/posted")
def posted(pid: int, m: MarkPosted):
    workflows.mark_posted(pid, m.posted_url, m.poster)
    return db.one("SELECT * FROM posts WHERE id=?", (pid,))


@app.post("/api/posts/{pid}/publish-page")
def publish_page(pid: int):
    p = db.one("SELECT * FROM posts WHERE id=?", (pid,))
    if not p:
        raise HTTPException(404)
    res = facebook.publish_page(f"{p['content']}\n\n{p['hashtags'] or ''}")
    if res["ok"]:
        workflows.mark_posted(pid, res["url"], "Fanpage (API)", res["id"])
    return res


@app.post("/api/distribution/plan")
def plan():
    return workflows.plan_distribution()


# ------------------------------------------------------------------ khách hàng
class Lead(BaseModel):
    name: str
    contact: str = ""
    channel: str = "Facebook"
    source: str = ""
    business_type: str = ""
    need: str = ""
    note: str = ""


class LeadPatch(BaseModel):
    status: str | None = None
    note: str | None = None
    score: int | None = None
    contacted: bool = False


class ReplyReq(BaseModel):
    message: str = ""


@app.get("/api/leads")
def leads():
    return db.q("SELECT * FROM leads ORDER BY score DESC, id DESC")


@app.post("/api/leads")
def add_lead(l: Lead):
    data = l.model_dump()
    score = workflows.score_lead(data)
    lid = db.run("""INSERT INTO leads(name, contact, channel, source, business_type, need, note, score, status,
                    created_at, updated_at) VALUES (?,?,?,?,?,?,?,?,'new',?,?)""",
                 (l.name, l.contact, l.channel, l.source, l.business_type, l.need, l.note, score, db.now(), db.now()))
    db.log("ha", "Khách mới", f"{l.name} ({score} điểm)")
    return db.one("SELECT * FROM leads WHERE id=?", (lid,))


@app.patch("/api/leads/{lid}")
def patch_lead(lid: int, p: LeadPatch):
    fields = {k: v for k, v in p.model_dump().items() if v is not None and k != "contacted"}
    fields["updated_at"] = db.now()
    if p.contacted:
        fields["last_contact_at"] = db.now()
    db.run(f"UPDATE leads SET {', '.join(k + '=?' for k in fields)} WHERE id=?", (*fields.values(), lid))
    return db.one("SELECT * FROM leads WHERE id=?", (lid,))


@app.post("/api/leads/{lid}/reply")
def lead_reply(lid: int, r: ReplyReq):
    return {"reply": workflows.draft_reply(lid, r.message)}


@app.get("/api/leads/follow-up")
def follow_up():
    return workflows.follow_up_list()


# ------------------------------------------------------------------ họp
class StartMeeting(BaseModel):
    topic: str = ""


class BossSay(BaseModel):
    text: str


@app.get("/api/meetings")
def meetings():
    return db.q("SELECT * FROM meetings ORDER BY id DESC LIMIT 30")


@app.get("/api/meetings/topics")
def topics():
    return meeting.TOPICS


@app.post("/api/meetings")
def start_meeting(s: StartMeeting):
    return {"id": meeting.start(s.topic)}


@app.get("/api/meetings/{mid}")
def get_meeting(mid: int, after: int = 0):
    m = db.one("SELECT * FROM meetings WHERE id=?", (mid,))
    if not m:
        raise HTTPException(404)
    m["action_items"] = json.loads(m["action_items"]) if m.get("action_items") else []
    m["messages"] = db.q("SELECT * FROM meeting_messages WHERE meeting_id=? AND id>? ORDER BY id", (mid, after))
    return m


@app.post("/api/meetings/{mid}/say")
def say(mid: int, b: BossSay):
    meeting.boss_say(mid, b.text)
    return {"ok": True}


# ------------------------------------------------------------------ việc & cài đặt
class TaskPatch(BaseModel):
    status: str


@app.get("/api/tasks")
def tasks():
    return db.q("SELECT * FROM tasks ORDER BY status='done', id DESC LIMIT 100")


@app.patch("/api/tasks/{tid}")
def patch_task(tid: int, t: TaskPatch):
    db.run("UPDATE tasks SET status=? WHERE id=?", (t.status, tid))
    return {"ok": True}


@app.post("/api/run/daily-work")
def run_daily():
    return workflows.daily_work()


@app.get("/api/settings")
def settings():
    s = db.get_settings()
    s["fb_page_token"] = "••••••" if s.get("fb_page_token") else ""
    s["ai_live"] = llm.live
    s["model"] = MODEL
    return s


@app.put("/api/settings")
def put_settings(data: dict):
    for k, v in data.items():
        if k in db.DEFAULT_SETTINGS and not (k == "fb_page_token" and v == "••••••"):
            db.set_setting(k, str(v))
    return settings()


# ------------------------------------------------------------------ nhân viên sale & nick Facebook
class Sale(BaseModel):
    name: str
    fb_name: str = ""


class SalePatch(BaseModel):
    name: str | None = None
    fb_name: str | None = None
    auto_post: int | None = None
    max_posts_per_day: int | None = None
    min_gap_minutes: int | None = None
    active_from: str | None = None
    active_to: str | None = None


def _sale_out(r: dict) -> dict:
    t = db.today() + "%"
    r["posted_today"] = db.one("SELECT COUNT(*) n FROM posts WHERE sale_id=? AND status='posted' AND posted_at LIKE ?", (r["id"], t))["n"]
    r["scheduled_today"] = db.one("SELECT COUNT(*) n FROM posts WHERE sale_id=? AND status IN ('scheduled','posting') AND scheduled_for LIKE ?", (r["id"], t))["n"]
    r["failed"] = db.one("SELECT COUNT(*) n FROM posts WHERE sale_id=? AND status='failed'", (r["id"],))["n"]
    r["busy"] = browser_poster.busy(r["id"])
    r["agent_id"] = f"sale-{r['id']}"
    r["recent"] = db.q("""SELECT p.id, p.status, p.title, p.target_type, p.posted_at, p.scheduled_for, p.error, p.screenshot,
                          g.name group_name FROM posts p LEFT JOIN groups g ON g.id=p.group_id
                          WHERE p.sale_id=? ORDER BY COALESCE(p.posted_at, p.scheduled_for) DESC LIMIT 6""", (r["id"],))
    r.pop("profile_dir", None)
    return r


@app.get("/api/sales")
def sales():
    return [_sale_out(r) for r in db.q("SELECT * FROM sales ORDER BY id")]


@app.post("/api/sales")
def add_sale(s: Sale):
    if db.one("SELECT COUNT(*) n FROM sales")["n"] >= agents.MAX_SALES:
        raise HTTPException(400, f"Văn phòng tối đa {agents.MAX_SALES} nhân viên sale")
    sid = db.run("INSERT INTO sales(name, fb_name, created_at) VALUES (?,?,?)", (s.name.strip(), s.fb_name.strip(), db.now()))
    db.run("UPDATE sales SET profile_dir=? WHERE id=?", (str(browser_poster.profile_dir(sid)), sid))
    db.log("minh", "Tuyển sale", f"{s.name} nhận quản lý nick {s.fb_name or s.name}")
    return _sale_out(db.one("SELECT * FROM sales WHERE id=?", (sid,)))


@app.patch("/api/sales/{sid}")
def patch_sale(sid: int, p: SalePatch):
    fields = {k: v for k, v in p.model_dump().items() if v is not None}
    for k in ("active_from", "active_to"):
        if k in fields and not re.fullmatch(r"\d{2}:\d{2}", fields[k]):
            raise HTTPException(400, "Giờ phải có dạng HH:MM")
    if fields:
        db.run(f"UPDATE sales SET {', '.join(k + '=?' for k in fields)} WHERE id=?", (*fields.values(), sid))
    if p.auto_post == 0:  # tạm dừng: trả bài chờ về hàng đợi để Tuấn xếp cho nick khác
        db.run("UPDATE posts SET status='approved', sale_id=NULL, scheduled_for=NULL WHERE sale_id=? AND status='scheduled'", (sid,))
    return _sale_out(db.one("SELECT * FROM sales WHERE id=?", (sid,)))


@app.delete("/api/sales/{sid}")
def del_sale(sid: int):
    db.run("UPDATE posts SET status='approved', sale_id=NULL, scheduled_for=NULL WHERE sale_id=? AND status='scheduled'", (sid,))
    db.run("DELETE FROM sales WHERE id=?", (sid,))
    return {"ok": True, "note": "Hồ sơ Chrome vẫn giữ trong data/profiles, xóa thư mục đó nếu không dùng nữa"}


@app.post("/api/sales/{sid}/open")
def open_browser(sid: int):
    """Mở cửa sổ Chrome của nick này trên máy chạy phần mềm để sếp đăng nhập / vào nhóm."""
    if browser_poster.busy(sid):
        raise HTTPException(409, "Nick đang bận, chờ xong việc hiện tại rồi mở")
    browser_poster.submit(sid, {"kind": "open"})
    return {"ok": True}


@app.post("/api/sales/{sid}/check")
def check_sale(sid: int):
    browser_poster.submit(sid, {"kind": "check"})
    return {"ok": True}


class PostRun(BaseModel):
    sale_id: int | None = None
    dry_run: bool = False


@app.post("/api/posts/{pid}/run")
def run_post(pid: int, r: PostRun):
    """Đăng ngay (hoặc đăng thử) một bài bằng nick sale."""
    p = db.one("SELECT * FROM posts WHERE id=?", (pid,))
    if not p:
        raise HTTPException(404)
    sid = r.sale_id or p.get("sale_id")
    if not sid:
        raise HTTPException(400, "Chọn nick sale để đăng bài này")
    if p["target_type"] == "page":
        raise HTTPException(400, "Bài Fanpage đăng qua nút Đăng Fanpage")
    if p["target_type"] == "group" and not p.get("group_id"):
        raise HTTPException(400, "Bài nhóm chưa được xếp vào nhóm nào. Bấm 'Tuấn xếp lịch' trước")
    db.run("UPDATE posts SET sale_id=? WHERE id=?", (sid, pid))
    if not r.dry_run:
        db.run("UPDATE posts SET status='posting', error=NULL WHERE id=?", (pid,))
    browser_poster.submit(sid, {"kind": "post", "post_id": pid, "dry_run": r.dry_run})
    return {"ok": True, "queued": browser_poster.queued(sid)}


@app.post("/api/posts/{pid}/retry")
def retry_post(pid: int):
    db.run("UPDATE posts SET status='approved', error=NULL, sale_id=NULL, scheduled_for=NULL WHERE id=? AND status='failed'", (pid,))
    return db.one("SELECT * FROM posts WHERE id=?", (pid,))


class GroupMembers(BaseModel):
    sale_ids: list[int] = []


@app.put("/api/groups/{gid}/members")
def group_members(gid: int, m: GroupMembers):
    db.run("UPDATE groups SET member_sale_ids=? WHERE id=?", (",".join(map(str, m.sale_ids)), gid))
    return {"ok": True}


class ImageUp(BaseModel):
    filename: str
    data: str  # data URL base64


@app.post("/api/products/{pid}/images")
def add_image(pid: int, img: ImageUp):
    p = db.one("SELECT images FROM products WHERE id=?", (pid,))
    if not p:
        raise HTTPException(404)
    raw = base64.b64decode(img.data.split(",", 1)[-1])
    if len(raw) > 8 * 1024 * 1024:
        raise HTTPException(400, "Ảnh tối đa 8MB")
    ext = (os.path.splitext(img.filename)[1].lower() or ".jpg")
    if ext not in (".jpg", ".jpeg", ".png", ".webp"):
        raise HTTPException(400, "Chỉ nhận ảnh JPG, PNG, WEBP")
    folder = db.MEDIA_DIR / f"product-{pid}"
    folder.mkdir(parents=True, exist_ok=True)
    name = f"{int(time.time() * 1000)}{ext}"
    (folder / name).write_bytes(raw)
    imgs = json.loads(p["images"] or "[]") + [f"media/product-{pid}/{name}"]
    db.run("UPDATE products SET images=? WHERE id=?", (json.dumps(imgs), pid))
    return {"images": imgs}


@app.delete("/api/products/{pid}/images")
def del_image(pid: int, path: str):
    p = db.one("SELECT images FROM products WHERE id=?", (pid,))
    imgs = [i for i in json.loads((p or {}).get("images") or "[]") if i != path]
    db.run("UPDATE products SET images=? WHERE id=?", (json.dumps(imgs), pid))
    return {"images": imgs}


# ------------------------------------------------------------------ giao diện
@app.get("/", response_class=HTMLResponse)
def index():
    body = (FRONTEND / "index.html").read_text(encoding="utf-8")
    return ('<!doctype html><html lang="vi"><head><meta charset="utf-8">'
            '<meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover">'
            '<style>html,body{height:100%;margin:0}[hidden]{display:none!important}</style>'
            f'</head><body>{body}</body></html>')


app.mount("/static", StaticFiles(directory=FRONTEND), name="static")
app.mount("/media", StaticFiles(directory=db.MEDIA_DIR), name="media")   # chỉ ảnh sản phẩm
app.mount("/shots", StaticFiles(directory=db.SHOTS_DIR), name="shots")   # ảnh chụp kết quả đăng bài

if __name__ == "__main__":
    uvicorn.run("main:app", host=os.getenv("HOST", "127.0.0.1"), port=int(os.getenv("PORT", 8000)), reload=False)

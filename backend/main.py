"""Máy chủ web: API cho giao diện quản lý công ty Agent AI.
Chạy:  python main.py   rồi mở http://localhost:8000
"""
import json
import os
import subprocess
import sys
import threading
import time
from pathlib import Path

import uvicorn
from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import FileResponse, HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

import base64
import re

import accounts
import agents
import browser_poster
import db
import errors
import facebook
import ceo
import company
import kpi
import learning
import telegram_bot
import media_folder
import meeting
import scheduler
import workflows
import llm as llm_mod
from llm import llm, MODEL

FRONTEND = Path(__file__).resolve().parent.parent / "frontend"
app = FastAPI(title="Công ty Agent AI - Phòng Kinh doanh")


@app.exception_handler(Exception)
async def _unhandled(request: Request, exc: Exception):
    """Lỗi bất ngờ ở bất kỳ thao tác nào: ghi vào sổ lỗi, trả về thông báo dễ hiểu kèm mã lỗi."""
    eid = errors.report_exc("api", f"Lỗi khi xử lý {request.method} {request.url.path}", exc,
                            screen=request.headers.get("x-screen") or None, action=request.headers.get("x-action", ""))
    return JSONResponse({"detail": f"Phần mềm gặp lỗi: {str(exc).splitlines()[0][:160] if str(exc) else exc.__class__.__name__}. "
                                   f"Xem chi tiết ở màn hình Lỗi (mã #{eid}).", "error_id": eid}, status_code=500)


@app.on_event("startup")
def startup():
    db.init()
    llm.reload()  # khóa API nhập trong phần mềm (nếu có) được ưu tiên hơn file .env
    scheduler.start()
    telegram_bot.start()
    threading.Thread(target=_update_watcher, daemon=True).start()


# ------------------------------------------------------------------ chung
def _code_stamp() -> str:
    """Dấu vân tay của mã nguồn trên đĩa: đổi khi tải bản mới về mà chưa khởi động lại phần mềm."""
    import hashlib
    h = hashlib.md5()
    for f in sorted(Path(__file__).resolve().parent.glob("*.py")) + [FRONTEND / "index.html"]:
        try:
            st = f.stat()
            h.update(f"{f.name}:{st.st_mtime_ns}:{st.st_size}".encode())
        except OSError:
            pass
    return h.hexdigest()[:12]


STARTED_STAMP = _code_stamp()
STARTED_AT = time.strftime("%Y-%m-%d %H:%M:%S")


# ------------------------------------------------------------------ tự khởi động lại khi có bản mới
ROOT = Path(__file__).resolve().parent.parent
_restart = {"tried": None, "at": None, "reason": ""}


def _idle() -> bool:
    """Không có việc đang dở: sale không mở Chrome, không họp, không tự học."""
    try:
        if browser_poster._busy or any(q.qsize() for q in browser_poster._queues.values()):
            return False
        if meeting.is_running():
            return False
        if learning._running.get("on"):
            return False
    except Exception:
        return False
    return True


def restart_self(reason: str) -> bool:
    """Chạy lại phần mềm bằng run.bat / run.sh (cài thêm thư viện mới nếu có). Bản mới khởi động sẽ tự tắt bản này.
    Nếu bản mới lỗi không chạy được, bản này vẫn tiếp tục chạy."""
    stamp = _code_stamp()
    if _restart["tried"] == stamp and reason != "manual":
        return False
    _restart.update(tried=stamp, at=time.strftime("%H:%M:%S"), reason=reason)
    db.log("minh", "Khởi động lại phần mềm", "Có bản mới trên máy, chạy lại để dùng bản mới" if reason == "update"
           else "Sếp bấm khởi động lại")
    try:
        if os.name == "nt" and (ROOT / "run.bat").exists():
            subprocess.Popen(["cmd", "/c", "start", "Moc Tam AI", str(ROOT / "run.bat"), "restart"], cwd=str(ROOT))
        elif (ROOT / "run.sh").exists() and os.getenv("RESTART_WITH_SCRIPT", "1") == "1":
            log = open(db.DATA_DIR / "app.log", "ab")
            subprocess.Popen(["bash", str(ROOT / "run.sh"), "restart"], cwd=str(ROOT), stdout=log, stderr=log,
                             start_new_session=True)
        else:
            log = open(db.DATA_DIR / "app.log", "ab")
            subprocess.Popen([sys.executable, str(Path(__file__).resolve())], cwd=str(Path(__file__).resolve().parent),
                             stdout=log, stderr=log, start_new_session=True)
        return True
    except Exception as e:
        errors.report_exc("api", "Không tự khởi động lại được phần mềm", e)
        return False


def _update_watcher():
    """Mỗi 30 giây xem mã nguồn trên máy có đổi không (vừa tải bản mới). Đổi và ổn định (đã tải xong) thì chờ lúc rảnh
    rồi tự khởi động lại bằng bản mới."""
    prev = None
    while True:
        time.sleep(30)
        try:
            cur = _code_stamp()
            if cur != STARTED_STAMP and cur == prev and _idle():
                restart_self("update")
            prev = cur
        except Exception as e:
            print("[update]", e)


@app.post("/api/admin/restart")
def admin_restart():
    if not restart_self("manual"):
        raise HTTPException(500, "Không khởi động lại được, hãy đóng cửa sổ run.bat rồi chạy lại")
    return {"ok": True, "pid": os.getpid()}


@app.get("/api/health")
def health():
    return {"ok": True, "ai_live": llm.live, "model": llm_mod.model_for("posts") if llm.live else "mô phỏng",
            "build": STARTED_STAMP, "stale": _code_stamp() != STARTED_STAMP, "pid": os.getpid(), "started_at": STARTED_AT,
            "restarting": _restart["at"], "idle": _idle(), "time": db.tz_info()}


@app.get("/api/agents")
def list_agents():
    out = agents.public_list()
    import growth
    growth_today = growth.today()
    login_txt = {"ok": "Nick sẵn sàng", "not_logged_in": "Chờ sếp đăng nhập Facebook", "checkpoint": "Nick bị checkpoint, đã dừng"}
    sales_by_id = {f"sale-{r['id']}": r for r in db.q("SELECT id, login_status FROM sales")}
    for a in out:
        a["status"] = workflows.STATUS.get(a["id"]) or {"state": "idle", "text": "Đang sẵn sàng"}
        a["level"] = learning.level_for((db.one("SELECT xp FROM agent_progress WHERE agent_id=?", (a["id"],)) or {"xp": 0})["xp"])
        if a["id"] in sales_by_id:
            a["login_status"] = sales_by_id[a["id"]]["login_status"]
            if a["status"].get("state") == "idle":
                a["status"] = {"state": "idle", "text": login_txt.get(a["login_status"], "")}
        a["tasks"] = db.q("SELECT * FROM tasks WHERE agent_id=? AND status!='done' ORDER BY id DESC LIMIT 5", (a["id"],))
        a["progress"] = learning.progress(a["id"])
        a["recent"] = db.q("""SELECT action, detail, created_at FROM activity WHERE agent_id=? AND action NOT IN ('Tự học lúc rảnh')
                              ORDER BY id DESC LIMIT 3""", (a["id"],))
        a["learned_today"] = (growth_today.get(a["id"]) or {}).get("learned", 0)
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
    image_folder: str = ""
    hot: bool = False
    hot_note: str = ""


class ProductPatch(BaseModel):
    name: str | None = None
    category: str | None = None
    description: str | None = None
    wholesale_price: str | None = None
    retail_price: str | None = None
    moq: str | None = None
    selling_points: str | None = None
    image_folder: str | None = None
    hot: bool | None = None
    hot_note: str | None = None


def _set_hot(pid: int, hot: bool, by: str = "boss"):
    import products as P
    P.set_hot(pid, hot, by)


@app.get("/api/products")
def products():
    return [{**p, "folder": media_folder.folder_info(p)}
            for p in db.q("SELECT * FROM products ORDER BY hot DESC, id")]


@app.post("/api/products")
def add_product(p: Product):
    if not p.name.strip():
        raise HTTPException(400, "Nhập tên sản phẩm")
    if db.one("SELECT id FROM products WHERE lower(name)=lower(?)", (p.name.strip(),)):
        raise HTTPException(400, "Đã có sản phẩm cùng tên. Sửa sản phẩm đó thay vì thêm mới")
    pid = db.run("""INSERT INTO products(name, category, description, wholesale_price, retail_price, moq,
                    selling_points, image_folder, hot_note, created_at) VALUES (?,?,?,?,?,?,?,?,?,?)""",
                 (p.name.strip(), p.category, p.description, p.wholesale_price, p.retail_price, p.moq, p.selling_points,
                  p.image_folder.strip().strip('"'), p.hot_note.strip(), db.now()))
    db.log("minh", "Thêm sản phẩm", f"{p.name.strip()}: Lan có thể viết bài, Hà tư vấn sản phẩm này từ giờ")
    if p.hot:
        _set_hot(pid, True)
    prod = db.one("SELECT * FROM products WHERE id=?", (pid,))
    return {**prod, "folder": media_folder.folder_info(prod)}


@app.patch("/api/products/{pid}")
def patch_product(pid: int, p: ProductPatch):
    if not db.one("SELECT id FROM products WHERE id=?", (pid,)):
        raise HTTPException(404, "Không tìm thấy sản phẩm")
    data = p.model_dump()
    hot = data.pop("hot")
    fields = {k: (v.strip().strip('"') if k == "image_folder" else v.strip() if isinstance(v, str) else v)
              for k, v in data.items() if v is not None}
    if "name" in fields and not fields["name"]:
        raise HTTPException(400, "Tên sản phẩm không được để trống")
    if "name" in fields and db.one("SELECT id FROM products WHERE lower(name)=lower(?) AND id!=?", (fields["name"], pid)):
        raise HTTPException(400, "Đã có sản phẩm khác cùng tên")
    if hot is not None:
        _set_hot(pid, hot)
    if fields:
        fields["is_sample"] = 0  # sếp đã sửa -> thành dữ liệu thật
        db.run(f"UPDATE products SET {', '.join(k + '=?' for k in fields)} WHERE id=?", (*fields.values(), pid))
    prod = db.one("SELECT * FROM products WHERE id=?", (pid,))
    if not prod:
        raise HTTPException(404)
    return {**prod, "folder": media_folder.folder_info(prod)}


@app.get("/api/products/{pid}/folder")
def product_folder(pid: int):
    prod = db.one("SELECT * FROM products WHERE id=?", (pid,))
    if not prod:
        raise HTTPException(404)
    return media_folder.folder_info(prod)


@app.get("/api/products/{pid}/folder-image")
def product_folder_image(pid: int, name: str):
    f = media_folder.safe_file(name, db.one("SELECT * FROM products WHERE id=?", (pid,)))
    if not f:
        raise HTTPException(404)
    return FileResponse(f)


@app.get("/api/image")
def used_image(path: str):
    """Ảnh đã đăng (để xem lại trên thẻ bài): chỉ trả file đã ghi trong lịch sử đăng ảnh."""
    if not db.one("SELECT id FROM image_usage WHERE path=? UNION SELECT id FROM posts WHERE images_used LIKE ?",
                  (path, f'%{json.dumps(path, ensure_ascii=False)[1:-1]}%')):
        raise HTTPException(404)
    f = Path(path)
    if not f.is_file() or f.suffix.lower() not in media_folder.IMG_EXT:
        raise HTTPException(404)
    return FileResponse(f)


@app.delete("/api/products/{pid}")
def del_product(pid: int):
    p = db.one("SELECT name FROM products WHERE id=?", (pid,))
    if not p:
        raise HTTPException(404, "Không tìm thấy sản phẩm")
    drafts = db.one("SELECT COUNT(*) n FROM posts WHERE product_id=? AND status IN ('draft','approved')", (pid,))["n"]
    db.run("UPDATE posts SET status='rejected' WHERE product_id=? AND status IN ('draft','approved')", (pid,))
    db.run("DELETE FROM products WHERE id=?", (pid,))
    db.log("minh", "Xóa sản phẩm", f"{p['name']}" + (f", bỏ {drafts} bài nháp/chờ đăng của sản phẩm này" if drafts else ""))
    return {"ok": True, "drafts_removed": drafts}


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
    joins = {}
    for j in db.q("SELECT group_id, account_id, status, note FROM account_groups"):
        joins.setdefault(j["group_id"], {})[j["account_id"]] = {"status": j["status"], "note": j["note"]}
    import group_finder
    for g in rows:
        g["ready"] = workflows.group_ready(g)
        g["joins"] = joins.get(g["id"], {})
        g["today"] = group_finder.matches_today(g)
    return rows


# ------------------------------------------------------------------ tìm nhóm mới
@app.get("/api/group-finder")
def gf_get():
    import group_finder
    return group_finder.overview()


class GFSettings(BaseModel):
    pool: list[str] | None = None
    discover_enabled: bool | None = None
    discover_time: str | None = None
    discover_keywords_per_day: int | None = None
    discover_add_per_day: int | None = None
    join_enabled: bool | None = None
    join_per_nick_day: int | None = None
    browse_minutes: float | None = None
    scout_per_run: int | None = None
    review_posts_day: float | None = None
    review_avg_reactions: float | None = None
    review_avg_comments: float | None = None
    review_growth_week: float | None = None
    review_min_members: int | None = None
    review_join_score: int | None = None
    review_consider_score: int | None = None
    review_use_best_groups: bool | None = None


@app.post("/api/group-finder/review")
def gf_review():
    """Tuấn chấm lại mọi nhóm đã khảo sát theo tiêu chí hiện tại."""
    import group_finder
    import group_review
    r = group_review.rereview_all()
    return {**group_finder.overview(), "result": r}


@app.put("/api/group-finder")
def gf_put(p: GFSettings):
    import group_finder
    if p.pool is not None:
        kws = [k.strip() for k in p.pool if k.strip()]
        if not kws:
            raise HTTPException(400, "Cần ít nhất 1 từ khóa tìm nhóm")
        db.set_setting("group_keywords", "\n".join(dict.fromkeys(kws)))
    if p.discover_time is not None:
        if not re.fullmatch(r"\d{2}:\d{2}", p.discover_time):
            raise HTTPException(400, "Giờ phải có dạng HH:MM")
        db.set_setting("discover_time", p.discover_time)
    for k, lo, hi in (("discover_keywords_per_day", 1, 6), ("discover_add_per_day", 0, 30), ("join_per_nick_day", 0, 5)):
        v = getattr(p, k)
        if v is not None:
            db.set_setting(k, str(max(lo, min(hi, v))))
    if p.browse_minutes is not None:
        db.set_setting("browse_minutes", str(max(0, min(10, p.browse_minutes))))
    for k, lo, hi in (("scout_per_run", 0, 15), ("review_posts_day", 0.5, 200), ("review_avg_reactions", 1, 5000),
                      ("review_avg_comments", 0.5, 1000), ("review_growth_week", 0.05, 20), ("review_min_members", 0, 1_000_000),
                      ("review_join_score", 20, 95), ("review_consider_score", 0, 90)):
        v = getattr(p, k)
        if v is not None:
            db.set_setting(k, str(round(max(lo, min(hi, v)), 2)).removesuffix(".0"))
    st = db.get_settings()
    if float(st.get("review_consider_score") or 40) >= float(st.get("review_join_score") or 60):
        db.set_setting("review_consider_score", str(max(0, int(float(st.get("review_join_score") or 60)) - 10)))
    if p.review_use_best_groups is not None:
        db.set_setting("review_use_best_groups", "1" if p.review_use_best_groups else "0")
    for k in ("discover_enabled", "join_enabled"):
        v = getattr(p, k)
        if v is not None:
            db.set_setting(k, "1" if v else "0")
    return group_finder.overview()


class GFToday(BaseModel):
    keywords: list[str]


@app.post("/api/group-finder/today")
def gf_today(t: GFToday):
    import group_finder
    if not [k for k in t.keywords if k.strip()]:
        raise HTTPException(400, "Nhập ít nhất 1 chủ đề")
    group_finder.set_today(t.keywords)
    return group_finder.overview()


@app.post("/api/group-finder/reroll")
def gf_reroll():
    import group_finder
    group_finder.today_keywords(force=True)
    return group_finder.overview()


class GFRun(BaseModel):
    sale_id: int | None = None
    keywords: list[str] | None = None


@app.post("/api/group-finder/run")
def gf_run(r: GFRun):
    import group_finder
    try:
        return group_finder.start_discover(r.sale_id, [k for k in (r.keywords or []) if k.strip()] or None)
    except ValueError as e:
        raise HTTPException(400, str(e))


@app.post("/api/group-finder/join")
def gf_join():
    import group_finder
    n = group_finder.submit_joins()
    if not n:
        raise HTTPException(400, "Chưa có nick sale nào đăng nhập và đang bật tự đăng")
    return {"ok": True, "sales": n}


@app.post("/api/group-finder/candidates/{cid}/add")
def gf_add(cid: int):
    import group_finder
    g = group_finder.add_candidate(cid, by="boss")
    if not g:
        raise HTTPException(400, "Nhóm này đã được thêm")
    return g


@app.post("/api/group-finder/candidates/{cid}/ignore")
def gf_ignore(cid: int):
    db.run("UPDATE group_candidates SET status='ignored' WHERE id=?", (cid,))
    return {"ok": True}


# ------------------------------------------------------------------ Mai: tìm khách sỉ
@app.get("/api/prospects")
def pr_get(grade: str = "", platform: str = "", seller_type: str = "", status: str = ""):
    import prospect
    return prospect.overview(grade, platform, seller_type, status)


class PRRun(BaseModel):
    directions: list[int] | None = None
    keywords: list[str] | None = None


@app.post("/api/prospects/run")
def pr_run(r: PRRun):
    import prospect
    try:
        return prospect.start([d for d in (r.directions or []) if d in prospect.DIRECTIONS] or None,
                              [k.strip() for k in (r.keywords or []) if k.strip()] or None)
    except ValueError as e:
        raise HTTPException(400, str(e))


class PRUrls(BaseModel):
    urls: list[str]


@app.post("/api/prospects/analyze")
def pr_analyze(r: PRUrls):
    """Sếp dán link (Facebook, TikTok, Shopee): Mai mở bằng Chrome của 1 nick sale rồi phân tích."""
    import prospect
    urls = [u.strip() for u in re.split(r"[\s,]+", " ".join(r.urls)) if re.match(r"(https?://\S+|(www\.|m\.)?(facebook|fb|tiktok|shopee)\.\w+/\S*)", u.strip(), re.I)]
    if not urls:
        raise HTTPException(400, "Dán ít nhất 1 link trang Facebook, TikTok hoặc Shopee")
    try:
        return prospect.start(urls=urls)
    except ValueError as e:
        raise HTTPException(400, str(e))


class PRSettings(BaseModel):
    enabled: bool | None = None
    time: str | None = None
    inspect_per_run: int | None = None
    facebook: bool | None = None
    tiktok: bool | None = None
    shopee: bool | None = None
    auto_crm: bool | None = None
    ai_script: bool | None = None
    keywords: dict[str, list[str]] | None = None


@app.put("/api/prospects/settings")
def pr_settings(p: PRSettings):
    import prospect
    if p.time is not None:
        if not re.fullmatch(r"\d{2}:\d{2}", p.time):
            raise HTTPException(400, "Giờ phải có dạng HH:MM")
        db.set_setting("prospect_time", p.time)
    if p.inspect_per_run is not None:
        db.set_setting("prospect_inspect_per_run", str(max(1, min(20, p.inspect_per_run))))
    for k in ("enabled", "facebook", "tiktok", "shopee", "auto_crm", "ai_script"):
        v = getattr(p, k)
        if v is not None:
            db.set_setting(f"prospect_{k}", "1" if v else "0")
    if p.keywords is not None:
        kw = {str(d): [x.strip() for x in v if x.strip()][:12] for d, v in p.keywords.items() if str(d) in ("1", "2", "3", "4")}
        db.set_setting("prospect_keywords", json.dumps({d: v for d, v in kw.items() if v}, ensure_ascii=False))
    return prospect.overview()


class PRPatch(BaseModel):
    status: str | None = None
    note: str | None = None
    approach: str | None = None


@app.patch("/api/prospects/{pid}")
def pr_patch(pid: int, p: PRPatch):
    import prospect
    r = db.one("SELECT * FROM prospects WHERE id=?", (pid,))
    if not r:
        raise HTTPException(404, "Không tìm thấy")
    if p.status is not None:
        if p.status not in ("verified", "needs_manual", "contacted", "rejected"):
            raise HTTPException(400, "Trạng thái không hợp lệ")
        db.run("UPDATE prospects SET status=?, updated_at=? WHERE id=?", (p.status, db.now(), pid))
        if p.status == "contacted" and r.get("lead_id"):
            db.run("UPDATE leads SET status='contacted', updated_at=? WHERE id=? AND status='new'", (db.now(), r["lead_id"]))
    for k in ("note", "approach"):
        v = getattr(p, k)
        if v is not None:
            db.run(f"UPDATE prospects SET {k}=?, updated_at=? WHERE id=?", (v.strip()[:2000], db.now(), pid))
    return db.one("SELECT * FROM prospects WHERE id=?", (pid,))


@app.post("/api/prospects/{pid}/crm")
def pr_crm(pid: int):
    import prospect
    lid = prospect.to_crm(pid)
    if not lid:
        raise HTTPException(404, "Không tìm thấy")
    return {"lead_id": lid}


@app.post("/api/prospects/{pid}/recheck")
def pr_recheck(pid: int):
    import prospect
    r = db.one("SELECT account_url FROM prospects WHERE id=?", (pid,))
    if not r:
        raise HTTPException(404, "Không tìm thấy")
    try:
        return prospect.start(urls=[r["account_url"]])
    except ValueError as e:
        raise HTTPException(400, str(e))


@app.post("/api/groups")
def add_group(g: Group):
    url, err = browser_poster.check_group_url(g.url)
    if err:
        raise HTTPException(400, err)
    gid = db.run("""INSERT INTO groups(name, url, topic, members, rules, min_days_between_posts, note, created_at)
                    VALUES (?,?,?,?,?,?,?,?)""",
                 (g.name, url, g.topic, g.members, g.rules, g.min_days_between_posts, g.note, db.now()))
    db.log("tuan", "Thêm nhóm", g.name)
    return db.one("SELECT * FROM groups WHERE id=?", (gid,))


class GroupPatch(BaseModel):
    name: str | None = None
    url: str | None = None
    topic: str | None = None
    members: int | None = None
    rules: str | None = None
    min_days_between_posts: int | None = None
    note: str | None = None


@app.patch("/api/groups/{gid}")
def patch_group(gid: int, p: GroupPatch):
    g = db.one("SELECT * FROM groups WHERE id=?", (gid,))
    if not g:
        raise HTTPException(404)
    fields = {k: v for k, v in p.model_dump().items() if v is not None}
    if "url" in fields:
        fields["url"], err = browser_poster.check_group_url(fields["url"])
        if err:
            raise HTTPException(400, err)
    if fields:
        db.run(f"UPDATE groups SET {', '.join(k + '=?' for k in fields)} WHERE id=?", (*fields.values(), gid))
    if fields.get("url") and not g.get("url"):
        # bài từng lỗi vì nhóm chưa có link: đưa về hàng chờ để Tuấn xếp lại
        db.run("""UPDATE posts SET status='approved', error=NULL, sale_id=NULL, scheduled_for=NULL
                  WHERE group_id=? AND status='failed' AND (error LIKE '%chưa có link%' OR error LIKE '%chưa có đường dẫn%')""",
               (gid,))
        db.log("tuan", "Thêm link nhóm", f"{g['name']}: {fields['url']}")
    out = db.one("SELECT * FROM groups WHERE id=?", (gid,))
    out["ready"] = workflows.group_ready(out)
    return out


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
    posted_url: str | None = None
    bump_enabled: int | None = None
    reason: str | None = None  # lý do sếp loại bài (để Lan học)
    comments: int | None = None
    leads: int | None = None


class MarkPosted(BaseModel):
    posted_url: str = ""
    poster: str = ""


@app.get("/api/posts")
def posts(status: str | None = None):
    sql = """SELECT p.*, pr.name product_name, g.name group_name, g.url group_url, s.name sale_name, fa.name account_name,
             (SELECT status || '|' || COALESCE(error,'') || '|' || COALESCE(screenshot,'') || '|' || COALESCE(scheduled_for,'')
              FROM bumps b WHERE b.post_id=p.id ORDER BY b.id DESC LIMIT 1) last_bump FROM posts p
             LEFT JOIN products pr ON pr.id=p.product_id LEFT JOIN groups g ON g.id=p.group_id
             LEFT JOIN sales s ON s.id=p.sale_id LEFT JOIN fb_accounts fa ON fa.id=p.account_id"""
    return db.q(sql + (" WHERE p.status=?" if status else "") + " ORDER BY p.id DESC LIMIT 200",
                (status,) if status else ())


@app.post("/api/posts/generate")
def gen_posts(r: GenReq):
    return workflows.generate_posts(min(max(r.count, 1), 10), r.product_id, r.target_type, r.angle, r.note)


@app.patch("/api/posts/{pid}")
def patch_post(pid: int, p: PostPatch):
    old = db.one("SELECT * FROM posts WHERE id=?", (pid,))
    if not old:
        raise HTTPException(404)
    # --- tín hiệu học từ sếp
    if p.content is not None and p.content.strip() != (old["content"] or "").strip():
        learning.record_feedback(pid, "edit", old["content"], p.content)
        try:
            import content_style
            content_style.on_boss_edit(pid, p.content)  # Lan học câu chữ sếp sửa
        except Exception as e:
            print("[content_style]", e)
    if p.status == "approved" and old["status"] == "draft":
        edited = db.one("SELECT id FROM feedback WHERE post_id=? AND kind='edit'", (pid,))
        if not edited:
            learning.record_feedback(pid, "approve")
        learning.award("lan", 5 if edited else 10, "Bài được sếp duyệt")
    if p.status == "rejected" and old["status"] == "draft":
        learning.record_feedback(pid, "reject", old["content"], "", (p.reason or "").strip()[:120])
    fields = {k: v for k, v in p.model_dump().items() if v is not None and k != "reason"}
    if p.posted_url is not None:  # sếp dán link bài thủ công
        fields["permalink_status"] = "found" if p.posted_url.strip() else "not_found"
        if p.posted_url.strip() and p.bump_enabled is None:
            fields["bump_enabled"] = 1
    if fields:
        db.run(f"UPDATE posts SET {', '.join(k + '=?' for k in fields)} WHERE id=?", (*fields.values(), pid))
    if p.leads is not None:  # cập nhật số khách của nhóm để Khoa xếp hạng
        learning.on_post_leads(pid, p.leads - (old["leads"] or 0))
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
    post_id: int | None = None  # khách đến từ bài đăng nào (để cả đội học bài nào hiệu quả)


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
    kpi.clear_sample_leads()
    data = l.model_dump()
    score = workflows.score_lead(data)
    src = l.source
    phone = kpi.norm_phone(f"{l.contact} {l.need}")
    if l.post_id:
        post = db.one("""SELECT p.id, g.name gname, p.target_type FROM posts p LEFT JOIN groups g ON g.id=p.group_id
                         WHERE p.id=?""", (l.post_id,))
        if post:
            src = src or f"Bài #{post['id']} · {post['gname'] or 'Trang cá nhân'}"
            db.run("UPDATE posts SET leads=COALESCE(leads,0)+1 WHERE id=?", (post["id"],))
            db.run("UPDATE groups SET leads_count=(SELECT COALESCE(SUM(leads),0) FROM posts WHERE group_id=groups.id)")
            learning.on_post_leads(post["id"], 1)
    lid = db.run("""INSERT INTO leads(name, contact, channel, source, business_type, need, note, score, status,
                    post_id, phone, phone_at, origin, created_at, updated_at) VALUES (?,?,?,?,?,?,?,?,'new',?,?,?,'manual',?,?)""",
                 (l.name, l.contact, l.channel, src, l.business_type, l.need, l.note, score, l.post_id,
                  phone, db.now() if phone else None, db.now(), db.now()))
    db.log("ha", "Khách mới", f"{l.name} ({score} điểm)")
    return db.one("SELECT * FROM leads WHERE id=?", (lid,))


@app.patch("/api/leads/{lid}")
def patch_lead(lid: int, p: LeadPatch):
    fields = {k: v for k, v in p.model_dump().items() if v is not None and k != "contacted"}
    fields["updated_at"] = db.now()
    if p.contacted:
        fields["last_contact_at"] = db.now()
    old = db.one("SELECT status FROM leads WHERE id=?", (lid,))
    db.run(f"UPDATE leads SET {', '.join(k + '=?' for k in fields)} WHERE id=?", (*fields.values(), lid))
    if p.status and old and p.status != old["status"]:
        learning.on_lead_status(lid, p.status)
    return db.one("SELECT * FROM leads WHERE id=?", (lid,))


class ReplySent(BaseModel):
    text: str = ""


@app.post("/api/replies/{rid}/sent")
def reply_sent(rid: int, r: ReplySent):
    """Sếp đã gửi tin cho khách (có thể đã sửa) -> lưu bản cuối để Hà học tin nào chốt được."""
    db.run("UPDATE replies SET sent=1, text=CASE WHEN ?!='' THEN ? ELSE text END, sent_at=? WHERE id=?",
           (r.text.strip(), r.text.strip(), db.now(), rid))
    learning.award("ha", 2, "Gửi tin nhắn cho khách")
    return {"ok": True}


@app.post("/api/leads/{lid}/reply")
def lead_reply(lid: int, r: ReplyReq):
    return workflows.draft_reply(lid, r.message) or {"reply": ""}


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


@app.get("/api/costs")
def costs():
    """Chi phí AI thật (đo từ số token mỗi lần gọi) + dự báo cuối tháng."""
    import calendar
    from datetime import datetime
    now = db.clock()
    month = now.strftime("%Y-%m") + "%"
    spent = llm_mod.month_spent()
    days_in = calendar.monthrange(now.year, now.month)[1]
    by_task = db.q("""SELECT task, COUNT(*) calls, SUM(input_tokens) tin, SUM(output_tokens) tout, SUM(cost_usd) cost,
                      SUM(batch) batched FROM usage WHERE created_at LIKE ? GROUP BY task ORDER BY cost DESC""", (month,))
    for r in by_task:
        r["label"] = llm_mod.TASKS.get(r["task"], r["task"])
    by_model = db.q("SELECT model, COUNT(*) calls, SUM(cost_usd) cost FROM usage WHERE created_at LIKE ? GROUP BY model", (month,))
    last = db.q("""SELECT substr(created_at,1,10) day, SUM(cost_usd) cost FROM usage
                   GROUP BY day ORDER BY day DESC LIMIT 14""")[::-1]
    saved = db.one("""SELECT COALESCE(SUM(cost_usd),0) c FROM usage WHERE batch=1 AND created_at LIKE ?""", (month,))["c"]
    s = db.get_settings()
    return {"spent": round(spent, 4), "budget": float(s.get("monthly_budget_usd") or 0),
            "projected": round(spent / max(now.day, 1) * days_in, 3), "state": llm_mod.budget_state(),
            "batch_saved": round(saved, 4), "by_task": by_task, "by_model": by_model, "daily": last,
            "prices": llm_mod.PRICES, "presets": llm_mod.PRESETS, "live": llm.live,
            "pending_batches": db.one("SELECT COUNT(*) n FROM ai_batches WHERE status='in_progress'")["n"]}


class Preset(BaseModel):
    name: str


@app.post("/api/costs/preset")
def apply_preset(p: Preset):
    if p.name not in llm_mod.PRESETS:
        raise HTTPException(400, "Gói không tồn tại")
    for k, v in llm_mod.PRESETS[p.name].items():
        db.set_setting(k, v)
    db.set_setting("cost_preset", p.name)
    return settings()


@app.get("/api/settings")
def settings():
    s = db.get_settings()
    s["fb_page_token"] = "••••••" if s.get("fb_page_token") else ""
    s["tg_token"] = "••••••" if s.get("tg_token") else ""
    key, src = llm.current_key()
    s["anthropic_api_key"] = ""
    s["ai_key_masked"] = llm_mod.mask_key(key)
    s["ai_key_source"] = src
    s.pop("tg_chat_ids", None)
    s["ai_live"] = llm.live
    s["model"] = MODEL
    s["models"] = list(llm_mod.PRICES)
    return s


@app.put("/api/settings")
def put_settings(data: dict):
    for k, v in data.items():
        if k in ("fb_page_token", "tg_token") and v == "••••••":
            continue
        if k == "anthropic_api_key":
            continue  # chỉ lưu qua /api/ai-key sau khi kiểm tra
        if k == "tg_token":  # token bot: kiểm tra với Telegram trước khi lưu
            if str(v).strip():
                try:
                    telegram_bot.save_token(str(v))
                except ValueError as e:
                    raise HTTPException(400, str(e))
            continue
        if k == "app_tz":
            if v and v not in db.TZ_CHOICES:
                raise HTTPException(400, "Múi giờ không hợp lệ")
            db.set_tz(v or db.DEFAULT_TZ)
        if k in db.DEFAULT_SETTINGS and k not in ("tg_chat_ids", "tg_pair_code", "tg_sent_log"):
            db.set_setting(k, str(v))
    return settings()


# ------------------------------------------------------------------ nhân viên sale & nick Facebook
class Sale(BaseModel):
    name: str
    fb_name: str = ""


class SalePatch(BaseModel):
    name: str | None = None
    auto_post: int | None = None


class AccountIn(BaseModel):
    sale_id: int
    name: str = ""


class AccountPatch(BaseModel):
    name: str | None = None
    enabled: int | None = None
    max_posts_per_day: int | None = None
    min_gap_minutes: int | None = None
    active_from: str | None = None
    active_to: str | None = None


def _acc_out(a: dict) -> dict:
    t = db.today() + "%"
    a["posted_today"] = db.one("SELECT COUNT(*) n FROM posts WHERE account_id=? AND status='posted' AND posted_at LIKE ?", (a["id"], t))["n"]
    a["scheduled_today"] = db.one("SELECT COUNT(*) n FROM posts WHERE account_id=? AND status IN ('scheduled','posting') AND scheduled_for LIKE ?", (a["id"], t))["n"]
    a["groups_joined"] = db.one("SELECT COUNT(*) n FROM account_groups WHERE account_id=? AND status='joined'", (a["id"],))["n"]
    a.pop("profile_dir", None)
    return a


def _sale_out(r: dict) -> dict:
    t = db.today() + "%"
    r["posted_today"] = db.one("SELECT COUNT(*) n FROM posts WHERE sale_id=? AND status='posted' AND posted_at LIKE ?", (r["id"], t))["n"]
    r["scheduled_today"] = db.one("SELECT COUNT(*) n FROM posts WHERE sale_id=? AND status IN ('scheduled','posting') AND scheduled_for LIKE ?", (r["id"], t))["n"]
    r["failed"] = db.one("SELECT COUNT(*) n FROM posts WHERE sale_id=? AND status='failed'", (r["id"],))["n"]
    r["busy"] = browser_poster.busy(r["id"])
    r["busy_account"] = browser_poster.busy_account(r["id"])
    r["agent_id"] = f"sale-{r['id']}"
    r["accounts"] = [_acc_out(a) for a in accounts.of_sale(r["id"])]
    r["max_accounts"] = accounts.MAX_PER_SALE
    r["recent"] = db.q("""SELECT p.id, p.status, p.title, p.target_type, p.posted_at, p.scheduled_for, p.error, p.screenshot,
                          g.name group_name, a.name account_name FROM posts p LEFT JOIN groups g ON g.id=p.group_id
                          LEFT JOIN fb_accounts a ON a.id=p.account_id
                          WHERE p.sale_id=? ORDER BY COALESCE(p.posted_at, p.scheduled_for) DESC LIMIT 6""", (r["id"],))
    r.pop("profile_dir", None)
    return r


@app.get("/api/sales")
def sales():
    return [_sale_out(r) for r in db.q("SELECT * FROM sales ORDER BY id")]


@app.post("/api/sales")
def add_sale(s: Sale):
    if company.status() == "dissolved":
        raise HTTPException(400, "Công ty đã giải thể. Thành lập lại ở trang Công ty trước khi tuyển.")
    if db.one("SELECT COUNT(*) n FROM sales WHERE COALESCE(status,'active')!='fired'")["n"] >= agents.MAX_SALES:
        raise HTTPException(400, f"Văn phòng tối đa {agents.MAX_SALES} nhân viên sale")
    removed = db.clear_samples(("sales",))  # tuyển người thật -> sale mẫu rời văn phòng
    if removed:
        db.log("minh", "Dọn sale mẫu", f"Đã cho {removed['sales']} sale mẫu rời văn phòng")
    # kỳ KPI bắt đầu từ ngày đầu tiên nick chạy được (sau khi sếp đăng nhập), không tính ngày chờ nick
    sid = db.run("INSERT INTO sales(name, fb_name, created_at, hired_by) VALUES (?,?,?,'boss')",
                 (s.name.strip(), s.fb_name.strip(), db.now()))
    accounts.create(sid, s.fb_name.strip() or "Nick 1")
    db.log("minh", "Tuyển sale", f"{s.name} nhận quản lý nick {s.fb_name or 'Nick 1'} (thêm được tới {accounts.MAX_PER_SALE} nick)")
    return _sale_out(db.one("SELECT * FROM sales WHERE id=?", (sid,)))


def _requeue(where: str, val: int):
    db.run(f"UPDATE posts SET status='approved', sale_id=NULL, account_id=NULL, scheduled_for=NULL WHERE {where}=? AND status='scheduled'", (val,))
    db.run(f"UPDATE bumps SET status='skipped', error='Nick tạm dừng' WHERE {where}=? AND status='scheduled'", (val,))


@app.patch("/api/sales/{sid}")
def patch_sale(sid: int, p: SalePatch):
    row = db.one("SELECT status FROM sales WHERE id=?", (sid,))
    if p.auto_post == 1 and (row or {}).get("status") == "fired":
        raise HTTPException(400, "Sale này đã nghỉ việc. Tuyển người thay để dùng tiếp nick.")
    if p.auto_post == 1 and company.status() == "dissolved":
        raise HTTPException(400, "Công ty đã giải thể.")
    fields = {k: v for k, v in p.model_dump().items() if v is not None}
    if fields:
        db.run(f"UPDATE sales SET {', '.join(k + '=?' for k in fields)} WHERE id=?", (*fields.values(), sid))
    if p.auto_post == 0:  # tạm dừng: trả bài chờ về hàng đợi để Tuấn xếp cho nick khác
        _requeue("sale_id", sid)
    return _sale_out(db.one("SELECT * FROM sales WHERE id=?", (sid,)))


@app.delete("/api/sales/{sid}")
def del_sale(sid: int):
    _requeue("sale_id", sid)
    for a in accounts.of_sale(sid):
        db.run("DELETE FROM account_groups WHERE account_id=?", (a["id"],))
    db.run("DELETE FROM fb_accounts WHERE sale_id=?", (sid,))
    db.run("DELETE FROM sales WHERE id=?", (sid,))
    return {"ok": True, "note": "Hồ sơ Chrome vẫn giữ trong data/profiles, xóa thư mục đó nếu không dùng nữa"}


def _acc_or_404(aid: int) -> dict:
    a = accounts.get(aid)
    if not a:
        raise HTTPException(404, "Không tìm thấy nick")
    return a


@app.post("/api/accounts")
def add_account(a: AccountIn):
    s = db.one("SELECT * FROM sales WHERE id=?", (a.sale_id,))
    if not s:
        raise HTTPException(404, "Không tìm thấy nhân viên sale")
    if s.get("status") == "fired":
        raise HTTPException(400, "Sale này đã nghỉ việc")
    try:
        acc = accounts.create(a.sale_id, a.name, copy_limits_from=accounts.first(a.sale_id))
    except ValueError as e:
        raise HTTPException(400, str(e))
    db.log("minh", "Thêm nick", f"{s['name']} nhận thêm nick {acc['name']}. Bấm Mở Chrome để đăng nhập nick này")
    return _sale_out(db.one("SELECT * FROM sales WHERE id=?", (a.sale_id,)))


@app.patch("/api/accounts/{aid}")
def patch_account(aid: int, p: AccountPatch):
    a = _acc_or_404(aid)
    fields = {k: v for k, v in p.model_dump().items() if v is not None}
    for k in ("active_from", "active_to"):
        if k in fields and not re.fullmatch(r"\d{2}:\d{2}", fields[k]):
            raise HTTPException(400, "Giờ phải có dạng HH:MM")
    if "name" in fields:
        fields["name"] = fields["name"].strip() or a["name"]
    if fields:
        db.run(f"UPDATE fb_accounts SET {', '.join(k + '=?' for k in fields)} WHERE id=?", (*fields.values(), aid))
    if p.enabled == 0:
        _requeue("account_id", aid)
    accounts.sync_sale(a["sale_id"])
    return _sale_out(db.one("SELECT * FROM sales WHERE id=?", (a["sale_id"],)))


@app.delete("/api/accounts/{aid}")
def del_account(aid: int):
    a = _acc_or_404(aid)
    if browser_poster.busy_account(a["sale_id"]) == aid:
        raise HTTPException(409, "Nick đang làm việc, chờ xong ca rồi xóa")
    _requeue("account_id", aid)
    db.run("DELETE FROM account_groups WHERE account_id=?", (aid,))
    db.run("DELETE FROM fb_accounts WHERE id=?", (aid,))
    accounts.sync_sale(a["sale_id"])
    return {"ok": True, "note": "Hồ sơ Chrome của nick vẫn giữ trong data/profiles"}


@app.post("/api/accounts/{aid}/open")
def open_account(aid: int):
    """Mở cửa sổ Chrome của nick này trên máy chạy phần mềm để sếp đăng nhập / vào nhóm."""
    a = _acc_or_404(aid)
    if browser_poster.busy(a["sale_id"]):
        raise HTTPException(409, "Sale đang làm việc trên một nick, chờ xong ca hiện tại rồi mở")
    browser_poster.submit(a["sale_id"], {"kind": "open", "account": aid})
    return {"ok": True}


@app.post("/api/accounts/{aid}/check")
def check_account(aid: int):
    a = _acc_or_404(aid)
    browser_poster.submit(a["sale_id"], {"kind": "check", "account": aid})
    return {"ok": True}


@app.post("/api/sales/{sid}/open")
def open_browser(sid: int):
    a = accounts.first(sid)
    if not a:
        raise HTTPException(400, "Sale này chưa có nick nào. Thêm nick trước")
    return open_account(a["id"])


@app.post("/api/sales/{sid}/check")
def check_sale(sid: int):
    for a in accounts.of_sale(sid):
        browser_poster.submit(sid, {"kind": "check", "account": a["id"]})
    return {"ok": True}


class PostRun(BaseModel):
    sale_id: int | None = None
    account_id: int | None = None
    dry_run: bool = False


@app.post("/api/posts/{pid}/run")
def run_post(pid: int, r: PostRun):
    """Đăng ngay (hoặc đăng thử) một bài bằng nick sale."""
    p = db.one("SELECT * FROM posts WHERE id=?", (pid,))
    if not p:
        raise HTTPException(404)
    aid = r.account_id
    if not aid and r.sale_id:
        a = accounts.first(r.sale_id)
        aid = a and a["id"]
    aid = aid or p.get("account_id")
    acc = accounts.get(aid) if aid else None
    if not acc:
        raise HTTPException(400, "Chọn nick sale để đăng bài này")
    sid = acc["sale_id"]
    if p["target_type"] == "page":
        raise HTTPException(400, "Bài Fanpage đăng qua nút Đăng Fanpage")
    if p["target_type"] == "group" and not p.get("group_id"):
        raise HTTPException(400, "Bài nhóm chưa được xếp vào nhóm nào. Bấm 'Tuấn xếp lịch' trước")
    db.run("UPDATE posts SET sale_id=?, account_id=? WHERE id=?", (sid, aid, pid))
    if not r.dry_run:
        db.run("UPDATE posts SET status='posting', error=NULL WHERE id=?", (pid,))
    browser_poster.submit(sid, {"kind": "post", "account": aid, "post_id": pid, "dry_run": r.dry_run})
    return {"ok": True, "queued": browser_poster.queued(sid)}


@app.post("/api/posts/{pid}/retry")
def retry_post(pid: int):
    db.run("UPDATE posts SET status='approved', error=NULL, sale_id=NULL, scheduled_for=NULL WHERE id=? AND status='failed'", (pid,))
    return db.one("SELECT * FROM posts WHERE id=?", (pid,))


class GroupMembers(BaseModel):
    account_ids: list[int] = []
    sale_ids: list[int] = []  # bản cũ: chọn theo sale -> mọi nick của sale đó


@app.put("/api/groups/{gid}/members")
def group_members(gid: int, m: GroupMembers):
    ids = list(m.account_ids)
    for sid in m.sale_ids:
        ids += [a["id"] for a in accounts.of_sale(sid)]
    ids = sorted(set(ids))
    db.run("UPDATE groups SET member_account_ids=? WHERE id=?", (",".join(map(str, ids)), gid))
    for aid in ids:
        db.run("""INSERT INTO account_groups(group_id, account_id, status, requested_at, updated_at) VALUES (?,?,'joined',?,?)
                  ON CONFLICT(group_id, account_id) DO UPDATE SET status='joined', updated_at=excluded.updated_at""",
               (gid, aid, db.now(), db.now()))
    db.run(f"DELETE FROM account_groups WHERE group_id=? AND status='joined' AND account_id NOT IN ({','.join('?' * len(ids)) or 'NULL'})",
           (gid, *ids))
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


# ------------------------------------------------------------------ công ty: vốn, doanh thu, sa thải, giải thể
@app.get("/api/company")
def company_overview():
    return company.overview()


class Found(BaseModel):
    capital: int = 10_000_000
    usd_vnd: float | None = None


@app.post("/api/company/found")
def company_found(f: Found):
    if f.capital < 0:
        raise HTTPException(400, "Vốn không hợp lệ")
    if company.status() == "active":
        raise HTTPException(400, "Công ty đang hoạt động")
    company.found(f.capital, f.usd_vnd)
    return company.overview()


class Money(BaseModel):
    amount: int
    note: str = ""
    category: str = "Khác"
    date: str = ""


@app.post("/api/company/capital")
def company_capital(m: Money):
    if m.amount <= 0:
        raise HTTPException(400, "Số tiền phải lớn hơn 0")
    company.add_capital(m.amount, m.note)
    return company.overview()


class Revenue(BaseModel):
    amount: int
    customer: str = ""
    note: str = ""
    lead_id: int | None = None


@app.post("/api/company/revenue")
def company_revenue(r: Revenue):
    """Sếp tự nhập doanh thu (sếp chốt và làm việc với khách)."""
    if r.amount <= 0:
        raise HTTPException(400, "Nhập doanh thu lớn hơn 0")
    try:
        company.add_order(r.lead_id, r.amount, r.note, via="app", customer=r.customer)
    except ValueError as e:
        raise HTTPException(404, str(e))
    return company.overview()


class OrderReq(BaseModel):
    amount: int
    note: str = ""


@app.post("/api/leads/{lid}/order")
def lead_order(lid: int, o: OrderReq):
    if o.amount <= 0:
        raise HTTPException(400, "Nhập giá trị đơn lớn hơn 0")
    try:
        return company.add_order(lid, o.amount, o.note)
    except ValueError as e:
        raise HTTPException(404, str(e))


@app.delete("/api/orders/{oid}")
def del_order(oid: int):
    db.run("DELETE FROM orders WHERE id=?", (oid,))
    return company.overview()


class Replace(BaseModel):
    name: str = ""


@app.post("/api/sales/{sid}/replace")
def replace_sale(sid: int, r: Replace):
    """Tuyển người thay cho sale đã nghỉ: dùng tiếp nick (hồ sơ Chrome đã đăng nhập) của người cũ."""
    try:
        return _sale_out(ceo.replace(sid, r.name, by="boss"))
    except ValueError as e:
        raise HTTPException(400, str(e))


# ------------------------------------------------------------------ sổ lỗi
@app.get("/api/errors")
def errors_list(status: str = "open", source: str = ""):
    return {"items": errors.listing(status, source), "new": errors.count_new(), "sources": errors.SOURCES,
            "open": db.one("SELECT COUNT(*) n FROM errors WHERE status!='resolved'")["n"]}


class ErrorIn(BaseModel):
    title: str
    message: str = ""
    detail: str = ""
    screen: str = ""
    action: str = ""


@app.post("/api/errors")
def errors_add(e: ErrorIn):
    """Giao diện gửi lỗi người dùng gặp ở bất kỳ màn hình nào."""
    return {"id": errors.report("ui", e.title, e.message, e.detail, screen=e.screen or None, action=e.action)}


class ErrorPatch(BaseModel):
    status: str


@app.patch("/api/errors/{eid}")
def errors_patch(eid: int, p: ErrorPatch):
    if p.status not in ("new", "seen", "resolved"):
        raise HTTPException(400, "Trạng thái không hợp lệ")
    db.run("UPDATE errors SET status=? WHERE id=?", (p.status, eid))
    return {"ok": True, "new": errors.count_new()}


@app.post("/api/errors/seen")
def errors_seen():
    db.run("UPDATE errors SET status='seen' WHERE status='new'")
    return {"ok": True}


@app.post("/api/errors/resolve-all")
def errors_resolve_all():
    db.run("UPDATE errors SET status='resolved' WHERE status!='resolved'")
    return {"ok": True}


@app.delete("/api/errors/resolved")
def errors_clear():
    db.run("DELETE FROM errors WHERE status='resolved'")
    return {"ok": True}


# ------------------------------------------------------------------ sếp giao việc cho CEO
@app.get("/api/ceo/chat")
def ceo_chat_get():
    import ceo_orders
    return ceo_orders.overview()


class CeoMsg(BaseModel):
    text: str


@app.post("/api/ceo/chat")
def ceo_chat(m: CeoMsg):
    import ceo_orders
    try:
        ceo_orders.handle(m.text, via="web")
    except ValueError as e:
        raise HTTPException(400, str(e))
    return ceo_orders.overview()


class Autopilot(BaseModel):
    on: bool


@app.put("/api/ceo/autopilot")
def ceo_autopilot(a: Autopilot):
    import ceo_orders
    db.set_setting("ceo_autopilot", "1" if a.on else "0")
    db.log("ceo", "Luật vận hành", "Sếp chỉ giao việc cho CEO, CEO tự vận hành" if a.on else "Sếp giao việc trực tiếp cho từng agent")
    return ceo_orders.overview()


@app.delete("/api/ceo/orders/{oid}")
def ceo_order_off(oid: int):
    import ceo_orders
    db.run("UPDATE ceo_orders SET active=0 WHERE id=?", (oid,))
    db.log("ceo", "Bỏ chỉ đạo", f"Chỉ đạo #{oid}")
    return ceo_orders.overview()


# ------------------------------------------------------------------ CEO
@app.get("/api/ceo")
def ceo_get():
    return ceo.overview()


class CeoSettings(BaseModel):
    mode: str | None = None
    enabled: bool | None = None
    potential: bool | None = None
    milestones: list[dict] | None = None  # [{"amount": 50000000, "hires": 1}]


@app.put("/api/ceo")
def ceo_put(c: CeoSettings):
    if c.mode in ("auto", "approve"):
        db.set_setting("ceo_mode", c.mode)
    if c.enabled is not None:
        db.set_setting("ceo_enabled", "1" if c.enabled else "0")
    if c.potential is not None:
        db.set_setting("ceo_potential", "1" if c.potential else "0")
    if c.milestones is not None:
        ms = []
        for m in c.milestones:
            amt, n = int(m.get("amount") or 0), int(m.get("hires") or 0)
            if amt <= 0 or not 1 <= n <= 4:
                raise HTTPException(400, "Mỗi mốc cần số tiền lớn hơn 0 và tuyển 1-4 người")
            ms.append((amt, n))
        db.set_setting("ceo_milestones", ",".join(f"{a}:{n}" for a, n in sorted(set(ms))))
    return ceo.overview()


class Approve(BaseModel):
    approve: bool


@app.post("/api/ceo/decisions/{did}")
def ceo_resolve(did: int, a: Approve):
    try:
        ceo.resolve(did, a.approve)
    except ValueError as e:
        raise HTTPException(400, str(e))
    return ceo.overview()


@app.post("/api/ceo/review")
def ceo_review_now():
    """Sếp bấm 'CEO đánh giá ngay': chạy đánh giá tiềm năng và mốc doanh thu ngay lập tức."""
    if not company.active():
        raise HTTPException(400, "Công ty chưa hoạt động")
    ceo.check_milestones()
    ceo.check_potential()
    return ceo.overview()


# ------------------------------------------------------------------ bắt đầu chạy thật
class ResetReq(BaseModel):
    confirm: str = ""
    products: bool = False
    groups: bool = False
    found_capital: int = 0  # > 0: thành lập công ty ngay sau khi xóa


@app.get("/api/reset")
def reset_preview():
    return db.reset_preview()


@app.post("/api/reset")
def reset(r: ResetReq):
    if r.confirm.strip().upper() != "CHAY THAT":
        raise HTTPException(400, 'Gõ đúng "CHAY THAT" để xác nhận')
    busy = [s["name"] for s in db.q("SELECT id, name FROM sales") if browser_poster.busy(s["id"]) or browser_poster.queued(s["id"])]
    if busy or meeting.is_running():
        raise HTTPException(409, "Đang có " + (f"nick {', '.join(busy)} làm việc" if busy else "cuộc họp") + ". Chờ xong rồi thử lại.")
    res = db.reset_test_data(r.products, r.groups)
    if r.found_capital > 0:
        company.found(r.found_capital)
        res["founded"] = True
    for k in list(workflows.STATUS):
        workflows.STATUS[k] = {"state": "idle", "text": "Sẵn sàng làm việc thật"}
    return res


# ------------------------------------------------------------------ dữ liệu mẫu
@app.get("/api/sample-data")
def sample_data():
    return db.sample_counts()


@app.delete("/api/sample-data")
def delete_sample_data():
    done = db.clear_samples()
    if done:
        db.log("minh", "Dọn dữ liệu mẫu", ", ".join(f"{v} {k}" for k, v in done.items()))
    return {"deleted": done, "left": db.sample_counts()}


# ------------------------------------------------------------------ khóa API Claude
class AiKey(BaseModel):
    key: str


@app.post("/api/ai-key")
def save_ai_key(k: AiKey):
    """Kiểm tra khóa với Anthropic rồi mới lưu; hiệu lực ngay, không cần khởi động lại."""
    res = llm_mod.check_key(k.key)
    if not res["ok"]:
        raise HTTPException(400, res["error"])
    db.set_setting("anthropic_api_key", k.key.strip())
    llm.reload()
    db.log("minh", "Kết nối Claude", "Đã lưu khóa API, cả đội chuyển sang suy nghĩ bằng Claude")
    return {"ok": True, "warning": res.get("warning"), "masked": llm_mod.mask_key(k.key), "source": llm.source}


@app.post("/api/ai-key/test")
def test_ai_key():
    key, src = llm.current_key()
    if not key:
        raise HTTPException(400, "Chưa có khóa API")
    res = llm_mod.check_key(key)
    if not res["ok"]:
        raise HTTPException(400, res["error"])
    return {"ok": True, "warning": res.get("warning"), "source": src}


@app.delete("/api/ai-key")
def delete_ai_key():
    db.set_setting("anthropic_api_key", "")
    llm.reload()
    db.log("minh", "Ngắt Claude", "Đã xóa khóa API trong phần mềm")
    return {"ok": True, "live": llm.live, "source": llm.source}


# ------------------------------------------------------------------ KPI & Telegram
@app.get("/api/kpi")
def kpi_overview():
    st = kpi.day_stats()
    return {"today": st, "pace": kpi.pace(st), "per_sale": kpi.per_sale(), "history": kpi.history(14), "streak": kpi.streak()}


@app.post("/api/leads/{lid}/escalate")
def escalate_lead(lid: int):
    ok = kpi.escalate(lid, "Sếp chọn tự tư vấn khách này", force=True)
    return {"ok": ok, "telegram": telegram_bot.configured()}


@app.post("/api/scan/now")
def scan_now():
    return {"posts": telegram_bot.start_scan_round(force=True)}


@app.get("/api/telegram")
def tg_status():
    return telegram_bot.status()


class TgToken(BaseModel):
    token: str


@app.post("/api/telegram/token")
def tg_save_token(t: TgToken):
    """Lưu token bot Telegram sau khi hỏi Telegram token có đúng không."""
    try:
        bot = telegram_bot.save_token(t.token)
    except ValueError as e:
        raise HTTPException(400, str(e))
    db.log("minh", "Kết nối Telegram", f"Đã lưu token bot @{bot.get('username')}")
    return telegram_bot.status()


@app.delete("/api/telegram/token")
def tg_delete_token():
    db.set_setting("tg_token", "")
    db.set_setting("tg_chat_ids", "")
    db.set_setting("tg_pair_code", "")
    telegram_bot.reset_token()
    return telegram_bot.status()


class TgReport(BaseModel):
    report_done: bool


@app.put("/api/telegram/report")
def tg_report(r: TgReport):
    db.set_setting("tg_report_done", "1" if r.report_done else "0")
    return telegram_bot.status()


@app.post("/api/telegram/pair")
def tg_pair():
    if not telegram_bot.token():
        raise HTTPException(400, "Dán token bot Telegram và bấm Lưu trước")
    return {"code": telegram_bot.new_pair_code(), **telegram_bot.status()}


class TgSend(BaseModel):
    kind: str = "test"


@app.post("/api/telegram/send")
def tg_send(t: TgSend):
    if not telegram_bot.configured():
        raise HTTPException(400, "Chưa ghép nối Telegram. Tạo mã ghép nối và gửi mã đó cho bot")
    text = {"test": "👋 Phòng kinh doanh AI đã kết nối thành công. Sếp sẽ nhận báo cáo và khách cần tư vấn tại đây.",
            "kpi": None, "morning": None, "evening": None}.get(t.kind)
    text = text or {"kpi": telegram_bot.kpi_text, "morning": telegram_bot.morning_text, "evening": telegram_bot.evening_text}[t.kind]()
    sent = telegram_bot.send(text)
    if not sent:
        raise HTTPException(502, "Gửi Telegram không thành công: " + (telegram_bot.status().get("error") or "không rõ lỗi"))
    return {"ok": True}


@app.post("/api/telegram/unlink")
def tg_unlink():
    db.set_setting("tg_chat_ids", "")
    return telegram_bot.status()


# ------------------------------------------------------------------ tự học
@app.get("/api/learning")
def learning_overview():
    return learning.overview()


@app.post("/api/learning/run")
def learning_run():
    learning.nightly_async()
    return {"ok": True}


# ------------------------------------------------------------------ kho bài & phong cách viết của Lan
@app.get("/api/content-style")
def content_style_get():
    import content_style
    return content_style.overview()


class StyleSet(BaseModel):
    mode: str | None = None
    min: int | None = None


@app.put("/api/content-style")
def content_style_put(st: StyleSet):
    import content_style
    if st.mode is not None:
        if st.mode not in ("auto", "always", "off"):
            raise HTTPException(400, "Chế độ không hợp lệ")
        db.set_setting("self_write_mode", st.mode)
    if st.min is not None:
        db.set_setting("self_write_min", str(max(5, min(200, st.min))))
    return content_style.overview()


class StylePreview(BaseModel):
    product_id: int | None = None
    angle: str | None = None
    target: str = "group"


@app.post("/api/content-style/preview")
def content_style_preview(r: StylePreview):
    """Lan viết thử 1 bài theo phong cách đã học (chỉ xem, không lưu, không gọi Claude)."""
    import content_style
    import mock_brain
    ok, why = content_style.ready()
    if not ok:
        raise HTTPException(400, why)
    p = db.one("SELECT * FROM products WHERE id=?", (r.product_id,)) if r.product_id else learning.choose_product(db.q("SELECT * FROM products"))
    if not p:
        raise HTTPException(400, "Chưa có sản phẩm")
    ang = r.angle if r.angle in mock_brain.ANGLES else learning.choose_angle()
    d = content_style.compose(p, ang, r.target if r.target in ("group", "profile", "page") else "group", dry=True)
    if not d:
        raise HTTPException(400, "Lan chưa ghép được bài khác đủ xa các bài cũ, cần học thêm bài Claude viết")
    return {**d, "product": p["name"], "angle": mock_brain.ANGLES.get(ang, ang)}


# ------------------------------------------------------------------ sổ kiến thức
@app.get("/api/knowledge")
def knowledge_get(agent: str = "", q: str = ""):
    import knowledge
    return knowledge.overview(agent, q)


class KnowIn(BaseModel):
    agent_id: str = "all"
    topic: str
    content: str
    question: str = ""
    kind: str = "guide"


@app.post("/api/knowledge")
def knowledge_add(k: KnowIn):
    """Sếp dạy kiến thức: agent dùng ngay từ việc tiếp theo."""
    import knowledge
    if k.agent_id not in knowledge.ROLE_NAME:
        raise HTTPException(400, "Chọn agent để dạy")
    if len(k.content.strip()) < 15:
        raise HTTPException(400, "Nội dung kiến thức quá ngắn")
    if not k.topic.strip():
        raise HTTPException(400, "Nhập chủ đề")
    iid = knowledge.save(k.agent_id, k.topic, k.content, question=k.question, source="boss", confidence=1.0,
                         kind="faq" if k.kind == "faq" else "guide")
    db.log("minh", "Sếp dạy kiến thức", f"{knowledge.ROLE_NAME[k.agent_id]}: {k.topic[:80]}")
    return {"ok": True, "id": iid, **knowledge.overview()}


class KnowPatch(BaseModel):
    topic: str | None = None
    content: str | None = None
    question: str | None = None


@app.patch("/api/knowledge/{kid}")
def knowledge_patch(kid: int, p: KnowPatch):
    fields = {k: v.strip() for k, v in p.model_dump().items() if v is not None}
    if fields:
        db.run(f"UPDATE knowledge SET {', '.join(k + '=?' for k in fields)}, updated_at=? WHERE id=?", (*fields.values(), db.now(), kid))
    return db.one("SELECT * FROM knowledge WHERE id=?", (kid,))


@app.delete("/api/knowledge/{kid}")
def knowledge_delete(kid: int):
    db.run("DELETE FROM knowledge WHERE id=?", (kid,))
    return {"ok": True}


@app.post("/api/knowledge/study")
def knowledge_study():
    import knowledge
    threading.Thread(target=knowledge.study_all, daemon=True).start()
    return {"ok": True}


class KnowAsk(BaseModel):
    question: str


@app.post("/api/knowledge/ask")
def knowledge_ask(a: KnowAsk):
    """Sếp hỏi đội: tra sổ kiến thức trước, chưa có mới hỏi Claude và lưu lại."""
    import knowledge
    if not a.question.strip():
        raise HTTPException(400, "Nhập câu hỏi")
    return knowledge.ask("ceo", a.question)


class KnowSettings(BaseModel):
    idle_learning: bool | None = None
    idle_study_per_day: int | None = None
    knowledge_enabled: bool | None = None
    study_time: str | None = None
    study_per_agent: int | None = None


@app.put("/api/knowledge/settings")
def knowledge_settings(k: KnowSettings):
    import knowledge
    if k.knowledge_enabled is not None:
        db.set_setting("knowledge_enabled", "1" if k.knowledge_enabled else "0")
    if k.idle_learning is not None:
        db.set_setting("idle_learning", "1" if k.idle_learning else "0")
    if k.idle_study_per_day is not None:
        db.set_setting("idle_study_per_day", str(max(0, min(24, k.idle_study_per_day))))
    if k.study_time is not None:
        if not re.fullmatch(r"\d{2}:\d{2}", k.study_time):
            raise HTTPException(400, "Giờ phải có dạng HH:MM")
        db.set_setting("study_time", k.study_time)
    if k.study_per_agent is not None:
        db.set_setting("study_per_agent", str(max(1, min(5, k.study_per_agent))))
    return knowledge.overview()


class Teach(BaseModel):
    agent_id: str
    text: str


@app.post("/api/lessons")
def teach(t: Teach):
    """Sếp dạy trực tiếp: bài học được ghim, luôn nằm trong sổ tay của agent."""
    lid = learning.add_lesson(t.agent_id, t.text, "Sếp dạy", "boss", 1.0, None, 1)
    if not lid:
        raise HTTPException(400, "Bài học quá ngắn")
    db.log(t.agent_id, "Được sếp dạy", t.text[:120])
    return db.one("SELECT * FROM lessons WHERE id=?", (lid,))


class LessonPatch(BaseModel):
    text: str | None = None
    pinned: int | None = None
    status: str | None = None


@app.patch("/api/lessons/{lid}")
def patch_lesson(lid: int, p: LessonPatch):
    fields = {k: v for k, v in p.model_dump().items() if v is not None}
    if p.status and p.status not in ("active", "retired"):
        raise HTTPException(400)
    if fields:
        fields["updated_at"] = db.now()
        db.run(f"UPDATE lessons SET {', '.join(k + '=?' for k in fields)} WHERE id=?", (*fields.values(), lid))
    return db.one("SELECT * FROM lessons WHERE id=?", (lid,))


@app.get("/api/posts/recent-posted")
def recent_posted():
    return db.q("""SELECT p.id, p.title, p.posted_at, g.name group_name, p.target_type FROM posts p
                   LEFT JOIN groups g ON g.id=p.group_id WHERE p.status='posted' ORDER BY p.posted_at DESC LIMIT 40""")


# ------------------------------------------------------------------ up bài
@app.get("/api/bump/folder")
def bump_folder():
    return media_folder.info()


@app.get("/api/bump/image")
def bump_image(name: str):
    f = media_folder.safe_file(name)
    if not f:
        raise HTTPException(404)
    return FileResponse(f)


@app.post("/api/posts/{pid}/bump")
def bump_post(pid: int):
    bid = workflows.bump_now(pid)
    if not bid:
        raise HTTPException(400, "Bài này không do nhân viên sale đăng nên chưa up tự động được")
    if not media_folder.root():
        raise HTTPException(400, "Chưa cài thư mục ảnh sản phẩm. Vào Cài đặt → Up bài")
    return {"ok": True, "bump_id": bid, "note": "Sale sẽ up bài trong vòng 1 phút khi rảnh"}


@app.post("/api/bump/plan-now")
def bump_plan_now():
    return {"scheduled": workflows.plan_bumps(force=True)}


@app.get("/api/bumps")
def bumps(post_id: int | None = None):
    sql = """SELECT b.*, s.name sale_name, fa.name account_name FROM bumps b LEFT JOIN sales s ON s.id=b.sale_id
             LEFT JOIN fb_accounts fa ON fa.id=b.account_id"""
    return db.q(sql + (" WHERE b.post_id=?" if post_id else "") + " ORDER BY b.id DESC LIMIT 100", (post_id,) if post_id else ())


# ------------------------------------------------------------------ giao diện
@app.get("/", response_class=HTMLResponse)
def index():
    body = (FRONTEND / "index.html").read_text(encoding="utf-8")
    return ('<!doctype html><html lang="vi"><head><meta charset="utf-8">'
            '<meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover">'
            '<style>html,body{height:100%;margin:0}[hidden]{display:none!important}</style>'
            '<script>window.__BACKEND__=true</script>'
            f'</head><body>{body}</body></html>')


app.mount("/static", StaticFiles(directory=FRONTEND), name="static")
app.mount("/media", StaticFiles(directory=db.MEDIA_DIR), name="media")   # chỉ ảnh sản phẩm
app.mount("/shots", StaticFiles(directory=db.SHOTS_DIR), name="shots")   # ảnh chụp kết quả đăng bài

# ------------------------------------------------------------------ chỉ cho chạy 1 bản phần mềm
def _port_owners(port: int) -> list:
    try:
        import psutil
    except ImportError:
        return []
    pids = set()
    try:
        for c in psutil.net_connections(kind="tcp"):
            if c.laddr and c.laddr.port == port and c.status == psutil.CONN_LISTEN and c.pid and c.pid != os.getpid():
                pids.add(c.pid)
    except Exception:
        pass
    out = []
    for pid in pids:
        try:
            out.append(psutil.Process(pid))
        except Exception:
            pass
    return out


def _is_this_app(p) -> bool:
    try:
        cmd = " ".join(p.cmdline()).lower()
        here = str(Path(__file__).resolve().parent).lower()
        cwd = ""
        try:
            cwd = p.cwd().lower()
        except Exception:
            pass
        return "python" in p.name().lower() and "main.py" in cmd and (cwd == here or here in cmd)
    except Exception:
        return False


def _kill_tree(p):
    """Tắt một bản phần mềm cùng Chrome nó mở. Không tắt chính mình (bản mới có thể là tiến trình con của bản cũ
    khi bản cũ tự khởi động lại)."""
    me = os.getpid()
    try:
        for ch in p.children(recursive=True):
            if ch.pid == me:
                continue
            try:
                ch.kill()
            except Exception:
                pass
        p.kill()
        p.wait(10)
    except Exception:
        pass


def _listening(p) -> bool:
    """Tiến trình có đang mở cổng web không (bản phần mềm thật sự đang chạy, khác với tiến trình khởi chạy)."""
    try:
        import psutil
        conns = (getattr(p, "net_connections", None) or p.connections)(kind="tcp")
        return any(c.status == psutil.CONN_LISTEN for c in conns)
    except Exception:
        return False


def _kill_other_instances():
    """Tắt mọi bản phần mềm này đang chạy (bản cũ, bản chạy trùng), kể cả bản không giữ cổng.
    Không tắt tiến trình khởi chạy của chính mình: trên Windows, .venv\\Scripts\\python.exe chỉ là trình khởi chạy,
    nó mở Python thật thành tiến trình con và tắt nó là tắt luôn bản đang khởi động."""
    try:
        import psutil
    except ImportError:
        return
    me = os.getpid()
    try:
        ancestors = {a.pid for a in psutil.Process(me).parents()}
    except Exception:
        ancestors = set()
    for p in psutil.process_iter(["name"]):
        if p.pid == me:
            continue
        if p.pid in ancestors and not _listening(p):
            continue  # trình khởi chạy của chính mình (hoặc cửa sổ run.bat): giữ nguyên
        if _is_this_app(p):
            print(f"[!] Phát hiện phần mềm đang chạy sẵn (PID {p.pid}, có thể là bản cũ). Đang tắt để chạy bản này...")
            try:
                REPLACED_FLAG.write_text(str(p.pid))  # cửa sổ run.bat của bản cũ thấy cờ này thì tự đóng, không báo lỗi
            except Exception:
                pass
            _kill_tree(p)


def _bind(host: str, port: int):
    """Mở cổng độc quyền. Trên Windows, uvicorn mặc định cho 2 phần mềm dùng chung 1 cổng (SO_REUSEADDR):
    bản cũ và bản mới cùng chạy, giành nhau yêu cầu và cùng mở Chrome của sale. Ở đây chỉ cho 1 bản chạy:
    gặp bản cũ của chính phần mềm này thì tắt nó, gặp chương trình khác thì báo rõ."""
    import socket
    for attempt in range(4):
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        if os.name == "nt":
            s.setsockopt(socket.SOL_SOCKET, socket.SO_EXCLUSIVEADDRUSE, 1)
        else:
            s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        try:
            s.bind((host, port))
            return s
        except OSError:
            s.close()
        owners = _port_owners(port)
        ours = [p for p in owners if _is_this_app(p)]
        if ours:
            for p in ours:
                print(f"[!] Phần mềm đang chạy sẵn một bản khác (PID {p.pid}, có thể là bản cũ). Đang tắt bản đó để chạy bản này...")
                _kill_tree(p)
            time.sleep(2)
            continue
        if owners:
            names = ", ".join(f"{p.name()} (PID {p.pid})" for p in owners)
            print(f"[x] Cổng {port} đang bị chương trình khác dùng: {names}.\n"
                  f"    Tắt chương trình đó, hoặc đặt PORT=8010 trong file .env rồi chạy lại.")
            sys.exit(1)
        time.sleep(2)  # cổng vừa được giải phóng, chờ hệ điều hành nhả hẳn
    print(f"[x] Không mở được cổng {port}. Có thể phần mềm đang chạy ở một cửa sổ khác: đóng hết các cửa sổ run.bat "
          f"(hoặc Task Manager → tắt python.exe) rồi chạy lại.")
    sys.exit(1)


# ------------------------------------------------------------------ tắt êm, nhường chỗ cho bản mới
INSTANCE_FILE = db.DATA_DIR / "instance.json"
REPLACED_FLAG = db.DATA_DIR / "replaced.flag"
_server = {"obj": None, "replaced": False, "token": None}


class Quit(BaseModel):
    token: str


@app.post("/api/admin/quit")
def admin_quit(q: Quit, request: Request):
    """Bản mới khởi động gọi vào đây để bản đang chạy tự tắt êm (không phải bị buộc tắt)."""
    if not _server["token"] or q.token != _server["token"] or (request.client and request.client.host not in ("127.0.0.1", "::1", "localhost")):
        raise HTTPException(403, "Không có quyền")
    _server["replaced"] = True
    if _server["obj"]:
        _server["obj"].should_exit = True
    return {"ok": True, "pid": os.getpid()}


def _ask_old_to_quit():
    """Nhờ bản đang chạy (bản có hỗ trợ) tự tắt êm, chờ tối đa 20 giây."""
    try:
        info = json.loads(INSTANCE_FILE.read_text(encoding="utf-8"))
    except Exception:
        return
    pid = info.get("pid")
    if not pid or pid == os.getpid():
        return
    try:
        import psutil
        if not psutil.pid_exists(pid):
            return
    except ImportError:
        return
    try:
        import httpx
        httpx.post(f"http://127.0.0.1:{info.get('port', 8000)}/api/admin/quit", json={"token": info.get("token", "")}, timeout=5)
        print(f"[!] Đang nhờ bản phần mềm đang chạy (PID {pid}) tự tắt để chạy bản này...")
    except Exception:
        return
    end = time.time() + 20
    while time.time() < end and psutil.pid_exists(pid):
        try:
            if psutil.Process(pid).status() == psutil.STATUS_ZOMBIE:
                break
        except Exception:
            break
        time.sleep(0.5)


def _quiet_console():
    """Windows: tắt chế độ chọn chữ (QuickEdit) của cửa sổ đen. Khi đang chọn chữ, Windows dừng mọi chữ in ra
    nên phần mềm bị treo cho tới khi bấm Esc."""
    if os.name != "nt":
        return
    try:
        import ctypes
        k = ctypes.windll.kernel32
        h = k.GetStdHandle(-10)
        mode = ctypes.c_uint32()
        if k.GetConsoleMode(h, ctypes.byref(mode)):
            k.SetConsoleMode(h, (mode.value & ~0x0040) | 0x0080)  # bỏ ENABLE_QUICK_EDIT_MODE, giữ EXTENDED_FLAGS
    except Exception:
        pass


def _cleanup_children():
    """Tắt Chrome và các tiến trình con còn lại để không giữ hồ sơ của sale sau khi phần mềm tắt."""
    try:
        import psutil
        for ch in psutil.Process(os.getpid()).children(recursive=True):
            try:
                name = ch.name().lower()
                # chỉ tắt Chrome và trình điều khiển trình duyệt; không đụng bản phần mềm mới vừa được mở để thay bản này
                if any(k in name for k in ("chrom", "node", "playwright", "headless_shell", "msedge")) and not _is_this_app(ch):
                    ch.kill()
            except Exception:
                pass
    except Exception:
        pass


if __name__ == "__main__":
    import secrets
    host, port = os.getenv("HOST", "127.0.0.1"), int(os.getenv("PORT", 8000))
    _quiet_console()
    try:  # cờ "đã bị thay" còn sót từ lâu (cửa sổ cũ không đọc tới): bỏ đi
        if REPLACED_FLAG.exists() and time.time() - REPLACED_FLAG.stat().st_mtime > 120:
            REPLACED_FLAG.unlink()
    except Exception:
        pass
    _ask_old_to_quit()
    _kill_other_instances()
    sock = _bind(host, port)
    _server["token"] = secrets.token_hex(16)
    try:
        INSTANCE_FILE.write_text(json.dumps({"pid": os.getpid(), "port": port, "token": _server["token"]}), encoding="utf-8")
    except Exception:
        pass
    print(f"Phần mềm đang chạy: http://localhost:{port}  (để tắt: đóng cửa sổ này, hoặc bấm Ctrl+C)")
    server = uvicorn.Server(uvicorn.Config(app, host=host, port=port, reload=False))
    _server["obj"] = server
    code = 0
    try:
        server.run(sockets=[sock])
    except KeyboardInterrupt:
        pass  # bấm Ctrl+C: tắt bình thường, không phải lỗi
    except SystemExit as e:
        code = e.code if isinstance(e.code, int) else 1
    finally:
        _cleanup_children()
        try:
            if json.loads(INSTANCE_FILE.read_text(encoding="utf-8")).get("pid") == os.getpid():
                INSTANCE_FILE.unlink()
        except Exception:
            pass
    if _server["replaced"]:
        try:
            REPLACED_FLAG.write_text(str(os.getpid()))
        except Exception:
            pass
        print("Đã chuyển sang bản mới ở cửa sổ khác. Cửa sổ này tự đóng.")
    else:
        print("Đã tắt phần mềm.")
    sys.exit(code)

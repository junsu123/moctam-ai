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
    try:
        a["diag"] = accounts.diagnose(a["id"])  # vì sao nick có / không có việc hôm nay
    except Exception as e:
        print("[diagnose]", e)
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


class ResetPosts(BaseModel):
    kinds: list[str] = ["approved", "scheduled", "failed"]
    rewrite: int = 0
    plan: bool = True


@app.get("/api/posts/reset")
def reset_posts_preview():
    return workflows.reset_preview()


@app.post("/api/posts/reset")
def reset_posts(r: ResetPosts):
    """Làm lại bài đăng: xóa bài chưa đăng (đã duyệt, lịch đăng, lỗi...) rồi cho Lan viết bài mới."""
    return workflows.reset_posts(r.kinds, r.rewrite, r.plan)


@app.post("/api/posts/{pid}/fetch-link")
def fetch_link(pid: int):
    """Sếp bấm “Lấy link ngay”: sale mở Chrome nick đã đăng bài để tìm lại link."""
    p = db.one("SELECT * FROM posts WHERE id=?", (pid,))
    if not p or p["status"] != "posted":
        raise HTTPException(400, "Bài chưa đăng nên chưa có link")
    if not p.get("account_id") or not accounts.get(p["account_id"]):
        raise HTTPException(400, "Bài này đăng tay, không có nick để tìm lại. Dán link bài vào ô bên dưới")
    db.run("UPDATE posts SET link_next_at=?, link_tries=0, link_error=NULL WHERE id=?", (db.now()[:16], pid))
    acc = accounts.get(p["account_id"])
    browser_poster.submit(acc["sale_id"], {"kind": "link", "account": acc["id"], "post_id": pid})
    return {"ok": True, "queued": browser_poster.queued(acc["sale_id"])}


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
    import media_folder
    if (why := media_folder.missing(p)):  # sếp quy định bài phải có ảnh
        raise HTTPException(400, why)
    db.run("UPDATE posts SET sale_id=?, account_id=? WHERE id=?", (sid, aid, pid))
    if not r.dry_run:
        db.run("UPDATE posts SET status='posting', error=NULL WHERE id=?", (pid,))
    browser_poster.submit(sid, {"kind": "post", "account": aid, "post_id": pid, "dry_run": r.dry_run})
    return {"ok": True, "queued": browser_poster.queued(sid)}


@app.post("/api/posts/{pid}/retry")
def retry_post(pid: int):
    db.run("UPDATE posts SET status='approved', error=NULL, img_fails=0, sale_id=NULL, scheduled_for=NULL WHERE id=? AND status='failed'", (pid,))
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
        db.run("""INSERT INTO account_groups(group_id, account_id, status, requested_at, updated_at, origin, joined_at)
                  VALUES (?,?,'joined',?,?,'boss',?)
                  ON CONFLICT(group_id, account_id) DO UPDATE SET status='joined', updated_at=excluded.updated_at,
                  origin=COALESCE(account_groups.origin, 'boss')""", (gid, aid, db.now(), db.now(), db.now()))
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
    media_folder._count_cache.clear()
    return {"images": imgs}


@app.delete("/api/products/{pid}/images")
def del_image(pid: int, path: str):
    p = db.one("SELECT images FROM products WHERE id=?", (pid,))
    imgs = [i for i in json.loads((p or {}).get("images") or "[]") if i != path]
    db.run("UPDATE products SET images=? WHERE id=?", (json.dumps(imgs), pid))
    media_folder._count_cache.clear()
    return {"images": imgs}

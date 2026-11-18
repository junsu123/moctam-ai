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
    rows = db.q(sql + (" WHERE p.status=?" if status else "") + " ORDER BY p.id DESC LIMIT 200",
                (status,) if status else ())
    import media_folder
    need = media_folder.required()
    for r in rows:  # bài chưa đăng: còn ảnh để đăng không (bắt buộc có ảnh thì thiếu ảnh sẽ không đăng)
        if r["status"] in ("draft", "approved", "scheduled", "posting", "failed"):
            r["img_count"] = media_folder.image_count(r)
            r["img_required"] = need
    return rows


@app.get("/api/posts/posted")
def posted_posts(page: int = 1, size: int = 20, q: str = "", group_id: int | None = None, account_id: int | None = None,
                 link: str = "", target: str = "", days: int = 0, sort: str = "new"):
    """Bảng bài đã đăng có phân trang + bộ lọc (nhóm, nick, link, thời gian, tìm chữ)."""
    size = max(5, min(100, size))
    where, args = ["p.status='posted'"], []
    if q.strip():
        like = f"%{q.strip()}%"
        where.append("(p.title LIKE ? OR p.content LIKE ? OR g.name LIKE ? OR p.posted_url LIKE ? OR CAST(p.id AS TEXT)=?)")
        args += [like, like, like, like, q.strip().lstrip("#")]
    if group_id:
        where.append("p.group_id=?"); args.append(group_id)
    if account_id:
        where.append("p.account_id=?"); args.append(account_id)
    if target in ("group", "profile", "page"):
        where.append("p.target_type=?"); args.append(target)
    if link == "found":
        where.append("p.permalink_status='found'")
    elif link == "missing":
        where.append("COALESCE(p.permalink_status,'') NOT IN ('found','pending','removed')")
    elif link in ("pending", "removed"):
        where.append("p.permalink_status=?"); args.append(link)
    if days > 0:
        since = (db.clock() - timedelta(days=days)).strftime("%Y-%m-%d %H:%M:%S")
        where.append("p.posted_at >= ?"); args.append(since)
    base = """FROM posts p LEFT JOIN products pr ON pr.id=p.product_id LEFT JOIN groups g ON g.id=p.group_id
              LEFT JOIN sales s ON s.id=p.sale_id LEFT JOIN fb_accounts fa ON fa.id=p.account_id WHERE """ + " AND ".join(where)
    total = db.one("SELECT COUNT(*) n " + base, tuple(args))["n"]
    pages = max(1, -(-total // size))
    page = max(1, min(page, pages))
    order = {"new": "p.posted_at DESC, p.id DESC", "old": "p.posted_at ASC, p.id ASC",
             "leads": "COALESCE(p.leads,0) DESC, COALESCE(p.comments,0) DESC, p.posted_at DESC",
             "comments": "COALESCE(p.comments,0) DESC, p.posted_at DESC"}.get(sort, "p.posted_at DESC, p.id DESC")
    items = db.q(f"""SELECT p.*, pr.name product_name, g.name group_name, g.url group_url, s.name sale_name, fa.name account_name,
                     (SELECT status || '|' || COALESCE(error,'') || '|' || COALESCE(screenshot,'') || '|' || COALESCE(scheduled_for,'')
                      FROM bumps b WHERE b.post_id=p.id ORDER BY b.id DESC LIMIT 1) last_bump {base} ORDER BY {order} LIMIT ? OFFSET ?""",
                 tuple(args) + (size, (page - 1) * size))
    st = db.one("""SELECT COUNT(*) total, SUM(permalink_status='found') found, SUM(permalink_status='pending') pending,
                   SUM(permalink_status='removed') removed,
                   SUM(COALESCE(permalink_status,'') NOT IN ('found','pending','removed')) missing,
                   SUM(COALESCE(comments,0)) comments, SUM(COALESCE(leads,0)) leads,
                   SUM(posted_at >= ?) today FROM posts WHERE status='posted'""", (db.today(),))
    groups = db.q("""SELECT g.id, g.name, COUNT(*) n FROM posts p JOIN groups g ON g.id=p.group_id WHERE p.status='posted'
                     GROUP BY g.id ORDER BY n DESC, g.name LIMIT 300""")
    accs = db.q("""SELECT fa.id, fa.name, s.name sale_name, COUNT(*) n FROM posts p JOIN fb_accounts fa ON fa.id=p.account_id
                   LEFT JOIN sales s ON s.id=fa.sale_id WHERE p.status='posted' GROUP BY fa.id ORDER BY s.name, fa.name""")
    return {"items": items, "total": total, "page": page, "size": size, "pages": pages,
            "stats": {k: (v or 0) for k, v in st.items()}, "groups": groups, "accounts": accs}


@app.post("/api/posts/generate")
def gen_posts(r: GenReq):
    return workflows.generate_posts(min(max(r.count, 1), 10), r.product_id, r.target_type, r.angle, r.note)


@app.patch("/api/posts/{pid}")
def patch_post(pid: int, p: PostPatch):
    old = db.one("SELECT * FROM posts WHERE id=?", (pid,))
    if not old:
        raise HTTPException(404)
    # --- tín hiệu học từ sếp
    import ceo_review
    if old.get("reviewed_by") == "ceo" and old["status"] in ("approved", "scheduled"):  # sếp sửa / hủy bài CEO đã duyệt
        if p.content is not None and p.content.strip() != (old["content"] or "").strip():
            ceo_review.on_boss_correction(old, p.content)
        elif p.status == "rejected":
            ceo_review.on_boss_correction(old, None, (p.reason or "").strip()[:120])
            learning.record_feedback(pid, "reject", old["content"], "", (p.reason or "").strip()[:120])
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
        u = p.posted_url.strip()
        if u and not browser_poster.PERMA_RX.search(u):
            raise HTTPException(400, "Đây chưa phải link bài viết. Mở bài trên Facebook, bấm vào giờ đăng (VD “2 giờ”) "
                                     "rồi chép link trên thanh địa chỉ (có /posts/ hoặc /permalink/)")
        fields["posted_url"] = browser_poster._clean_link(u) if u else u
        fields["permalink_status"] = "found" if u else "not_found"
        fields["link_next_at"] = None
        fields["link_error"] = None
        if p.posted_url.strip() and p.bump_enabled is None:
            fields["bump_enabled"] = 1
    if fields:
        db.run(f"UPDATE posts SET {', '.join(k + '=?' for k in fields)} WHERE id=?", (*fields.values(), pid))
        if "content" in fields:  # sếp sửa chữ là bản cuối: Lan không chỉnh theo nhóm đè lên nữa
            db.run("UPDATE posts SET orig_content=NULL, fit_group_id=COALESCE(group_id, -1), fit_note=NULL WHERE id=?", (pid,))
    if p.posted_url and p.posted_url.strip():
        db.run("""UPDATE errors SET status='resolved' WHERE source='link' AND ref_type='post' AND ref_id=?
                  AND status!='resolved'""", (pid,))  # sếp đã dán link: lỗi “không lưu được link” xong
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
    res = facebook.publish_post(p)
    if res["ok"]:
        workflows.mark_posted(pid, res["url"], "Fanpage (API)", res["id"])
    elif res.get("no_image"):
        raise HTTPException(400, res["error"])
    return res


@app.post("/api/distribution/plan")
def plan():
    return workflows.plan_distribution()

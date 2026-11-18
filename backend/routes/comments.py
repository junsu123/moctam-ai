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
        raise HTTPException(400, "Chưa cài thư mục ảnh sản phẩm. Vào Bình luận → Cài đặt")
    return {"ok": True, "bump_id": bid, "note": "Sale sẽ up bài trong vòng 1 phút khi rảnh"}


@app.get("/api/bump/preview-text")
def bump_preview_text(n: int = 3):
    """Bảo viết thử vài câu bình luận up bài (chưa lưu, chưa gửi)."""
    import post_care
    return post_care.preview(max(1, min(n, 6)))


@app.get("/api/post-care")
def post_care_get():
    import post_care
    return post_care.overview()


@app.post("/api/post-care/relearn")
def post_care_relearn():
    import post_care
    return post_care.relearn()


@app.post("/api/bump/plan-now")
def bump_plan_now():
    return {"scheduled": workflows.plan_bumps(force=True)}


@app.get("/api/bumps")
def bumps(post_id: int | None = None):
    sql = """SELECT b.*, s.name sale_name, fa.name account_name FROM bumps b LEFT JOIN sales s ON s.id=b.sale_id
             LEFT JOIN fb_accounts fa ON fa.id=b.account_id"""
    return db.q(sql + (" WHERE b.post_id=?" if post_id else "") + " ORDER BY b.id DESC LIMIT 100", (post_id,) if post_id else ())


# ------------------------------------------------------------------ màn hình Bình luận (bình luận tự động mỗi ngày)
class CommentEdit(BaseModel):
    text: str


@app.get("/api/comments")
def comments_get(day: str | None = None, status: str = "", account_id: int | None = None, q: str = ""):
    import comments
    return comments.overview(day, status, account_id, q)


@app.put("/api/comments/{bid}")
def comments_edit(bid: int, body: CommentEdit):
    import comments
    try:
        return comments.edit(bid, body.text)
    except ValueError as e:
        raise HTTPException(400, str(e))


@app.post("/api/comments/post/{pid}/resume")
def comments_resume_post(pid: int):
    import bump_watch
    bump_watch.resume_post(pid)
    return {"ok": True}


@app.post("/api/comments/group/{gid}/resume")
def comments_resume_group(gid: int):
    import bump_watch
    bump_watch.resume_group(gid)
    return {"ok": True}


@app.post("/api/comments/{bid}/{act}")
def comments_act(bid: int, act: str):
    import comments
    fn = {"cancel": comments.cancel, "retry": comments.retry, "rewrite": comments.rewrite}.get(act)
    if not fn:
        raise HTTPException(404)
    try:
        return fn(bid)
    except ValueError as e:
        raise HTTPException(400, str(e))

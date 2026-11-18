# ------------------------------------------------------------------ chỉ đạo nơi đăng bài
class PostTarget(BaseModel):
    mode: str | None = None
    include: list[str] | str | None = None
    exclude: list[str] | str | None = None


@app.get("/api/post-target")
def post_target_get():
    import group_target
    return group_target.overview()


@app.put("/api/post-target")
def post_target_put(p: PostTarget):
    import group_target
    try:
        group_target.save(p.mode, p.include, p.exclude)
    except ValueError as e:
        raise HTTPException(400, str(e))
    return group_target.overview()


@app.post("/api/post-target/preview")
def post_target_preview(p: PostTarget):
    """Xem trước khi lưu: nhóm nào sẽ được đăng với chỉ đạo đang gõ."""
    import group_target
    c = group_target.settings()
    if p.mode in group_target.MODES:
        c["mode"] = p.mode
    for k in ("include", "exclude"):
        v = getattr(p, k)
        if v is not None:
            c[k] = group_target.words(", ".join(v) if isinstance(v, list) else v)
    return group_target.preview(c)


class FocusIn(BaseModel):
    focus: bool = True


@app.put("/api/groups/{gid}/focus")
def group_focus(gid: int, f: FocusIn):
    import group_target
    try:
        return group_target.set_focus(gid, f.focus)
    except KeyError:
        raise HTTPException(404, "Không tìm thấy nhóm")

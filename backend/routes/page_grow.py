# ------------------------------------------------------------------ nuôi nhiều Trang qua Chrome của nick quản trị (không dùng Graph API)
@app.get("/api/page-grow")
def page_grow_get():
    import page_grow
    return page_grow.overview()


@app.put("/api/page-grow/settings")
def page_grow_settings(data: dict):
    import page_grow
    for k, v in data.items():
        v = "" if v is None else str(v).strip()
        if k == "page_grow_on":
            db.set_setting(k, "1" if v in ("1", "true", "True") else "0")
        elif k == "page_grow_sale_pct":
            db.set_setting(k, str(max(0, min(50, int(v or 20)))))
        elif k == "page_grow_off":
            db.set_setting(k, ",".join(t for t in v.split(",") if t in page_grow.TOPICS))
    return page_grow.overview()


@app.post("/api/page-grow/pages")
def page_grow_add(data: dict):
    import page_grow
    try:
        page_grow.add_page(data.get("name"), data.get("url"), data.get("admin_account_id"), data.get("posts_per_day") or 1,
                           data.get("times") or "08:30,20:30", data.get("niche") or "", data.get("keywords") or "")
    except ValueError as e:
        raise HTTPException(400, str(e))
    return page_grow.overview()


@app.put("/api/page-grow/pages/{pid}")
def page_grow_update(pid: int, data: dict):
    import page_grow
    import trend_pages
    import page_brain
    pg = db.one("SELECT * FROM fb_pages WHERE id=? AND COALESCE(kind,'trend')='grow'", (pid,))
    if not pg:
        raise HTTPException(404, "Không có Trang này")
    try:
        if data.get("url") is not None or data.get("admin_account_id") is not None:
            st = pg["status"]
            trend_pages.activate(pid, data.get("url") or pg["url"] or "", int(data.get("admin_account_id") or pg["admin_account_id"] or 0),
                                 int(data.get("posts_per_day") or pg["posts_per_day"] or 1), data.get("times") or pg["times"] or "08:30,20:30")
            if st == "paused":
                db.run("UPDATE fb_pages SET status='paused' WHERE id=?", (pid,))
        if (data.get("name") or "").strip():
            db.run("UPDATE fb_pages SET name=? WHERE id=?", (data["name"].strip()[:80], pid))
        page_brain.update_page(pid, {k: data.get(k) for k in ("niche", "keywords", "posts_per_day", "times")})
    except ValueError as e:
        raise HTTPException(400, str(e))
    return page_grow.overview()


@app.post("/api/page-grow/write")
def page_grow_write(data: dict | None = None):
    import page_grow
    pid = (data or {}).get("page_id")
    pg = db.one("SELECT * FROM fb_pages WHERE id=?", (pid,)) if pid else None
    why = page_grow.ready(pg) if pg else page_grow.ready()
    if why:
        raise HTTPException(400, why)
    return page_grow.write(pg, (data or {}).get("topic"))


@app.post("/api/page-grow/{pid}/skip")
def page_grow_skip(pid: int):
    import page_grow
    page_grow.skip(pid)
    return page_grow.overview()


@app.post("/api/page-grow/pages/{pid}/status")
def page_grow_status(pid: int, data: dict):
    import page_grow
    if not db.one("SELECT id FROM fb_pages WHERE id=? AND COALESCE(kind,'trend')='grow'", (pid,)):
        raise HTTPException(404, "Không có Trang này")
    trends_page_status(pid, data)  # cùng luật với Trang xu hướng: dừng thì bỏ bài chưa đăng
    return page_grow.overview()

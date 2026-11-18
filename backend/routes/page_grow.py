# ------------------------------------------------------------------ nuôi Trang qua Chrome của nick quản trị (không dùng Graph API)
@app.get("/api/page-grow")
def page_grow_get():
    import page_grow
    return page_grow.overview()


@app.put("/api/page-grow/settings")
def page_grow_settings(data: dict):
    import page_grow
    for k, v in data.items():
        v = "" if v is None else str(v).strip()
        if k == "page_url":
            if v and "facebook.com" not in v and not v.startswith("http://localhost"):
                raise HTTPException(400, "Link Trang phải là link facebook.com của Trang (VD https://facebook.com/moctamvn)")
            db.set_setting(k, v)
        elif k in ("page_grow_on", "page_grow_review"):
            db.set_setting(k, "1" if v in ("1", "true", "True") else "0")
        elif k == "page_grow_per_day":
            db.set_setting(k, str(max(0, min(3, int(v or 1)))))
        elif k == "page_grow_sale_pct":
            db.set_setting(k, str(max(0, min(50, int(v or 20)))))
        elif k == "page_grow_times":
            ts = [t.strip() for t in v.split(",") if re.fullmatch(r"\d\d:\d\d", t.strip())]
            db.set_setting(k, ",".join(ts[:3]) or "08:30,20:30")
        elif k == "page_grow_off":
            db.set_setting(k, ",".join(t for t in v.split(",") if t in page_grow.TOPICS))
        elif k == "page_admin_account":
            if v and not db.one("SELECT id FROM fb_accounts WHERE id=?", (v,)):
                raise HTTPException(400, "Không tìm thấy nick này")
            db.set_setting(k, v)
    return page_grow.overview()


@app.post("/api/page-grow/write")
def page_grow_write(data: dict | None = None):
    import page_grow
    why = page_grow.ready()
    if why:
        raise HTTPException(400, why)
    return page_grow.write((data or {}).get("topic"))


@app.post("/api/page-grow/{pid}/skip")
def page_grow_skip(pid: int):
    import page_grow
    page_grow.skip(pid)
    return page_grow.overview()

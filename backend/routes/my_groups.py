# ------------------------------------------------------------------ nhóm có sẵn trong nick (Tuấn rà soát)
@app.get("/api/my-groups")
def mg_get():
    import my_groups
    return my_groups.overview()


@app.post("/api/my-groups/sync")
def mg_sync():
    import my_groups
    n = my_groups.start_sync()
    if not n:
        raise HTTPException(400, "Chưa có nick sale nào đăng nhập để đọc danh sách nhóm")
    return {"nicks": n}


class MGSettings(BaseModel):
    enabled: bool | None = None
    time: str | None = None
    auto_leave: bool | None = None
    leave_per_nick_day: int | None = None
    rest_days: int | None = None
    review_per_run: int | None = None
    admin_min: int | None = None
    admin_max: int | None = None
    sell_share: int | None = None


@app.put("/api/my-groups/settings")
def mg_settings(p: MGSettings):
    import my_groups
    if p.time is not None:
        if not re.fullmatch(r"\d{2}:\d{2}", p.time):
            raise HTTPException(400, "Giờ phải có dạng HH:MM")
        db.set_setting("mygroups_time", p.time)
    for k, key in (("enabled", "mygroups_enabled"), ("auto_leave", "auto_leave")):
        v = getattr(p, k)
        if v is not None:
            db.set_setting(key, "1" if v else "0")
    for k, key, lo, hi in (("leave_per_nick_day", "leave_per_nick_day", 0, 10), ("rest_days", "new_group_rest_days", 0, 30),
                           ("review_per_run", "mygroups_review_per_run", 1, 20), ("admin_min", "admin_posts_min", 0, 20),
                           ("admin_max", "admin_posts_max", 1, 20), ("sell_share", "admin_sell_share", 0, 100)):
        v = getattr(p, k)
        if v is not None:
            db.set_setting(key, str(max(lo, min(hi, v))))
    st = db.get_settings()
    if int(st.get("admin_posts_min") or 5) > int(st.get("admin_posts_max") or 10):
        db.set_setting("admin_posts_max", st.get("admin_posts_min"))
    my_groups.apply_decisions()
    return my_groups.overview()


class MGPin(BaseModel):
    pin: bool


@app.post("/api/my-groups/{gid}/pin")
def mg_pin(gid: int, p: MGPin):
    import my_groups
    db.run("UPDATE groups SET pinned=? WHERE id=?", (1 if p.pin else 0, gid))
    my_groups.apply_decisions()
    return my_groups.overview()


class MGLeave(BaseModel):
    account_id: int


@app.post("/api/my-groups/{gid}/leave")
def mg_leave(gid: int, p: MGLeave):
    import my_groups
    try:
        my_groups.leave_now(gid, p.account_id)
    except ValueError as e:
        raise HTTPException(400, str(e))
    return {"ok": True}

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

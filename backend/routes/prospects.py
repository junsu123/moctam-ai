# ------------------------------------------------------------------ Mai: tìm khách sỉ
@app.get("/api/prospects")
def pr_get(grade: str = "", platform: str = "", seller_type: str = "", status: str = "", phone: str = ""):
    import prospect
    return prospect.overview(grade, platform, seller_type, status, phone)


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
    fb_keywords: int | None = None
    groups_per_run: int | None = None
    ads: bool | None = None
    groups: bool | None = None
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
    if p.fb_keywords is not None:
        db.set_setting("prospect_fb_keywords", str(max(1, min(4, p.fb_keywords))))
    if p.groups_per_run is not None:
        db.set_setting("prospect_groups_per_run", str(max(0, min(10, p.groups_per_run))))
    for k in ("enabled", "facebook", "tiktok", "shopee", "auto_crm", "ai_script", "ads", "groups"):
        v = getattr(p, k)
        if v is not None:
            db.set_setting(f"prospect_{k}", "1" if v else "0")
    if p.keywords is not None:
        kw = {str(d): [x.strip() for x in v if x.strip()][:12] for d, v in p.keywords.items() if str(d) in ("1", "2", "3", "4", "5")}
        db.set_setting("prospect_keywords", json.dumps({d: v for d, v in kw.items() if v}, ensure_ascii=False))
    return prospect.overview()


class PRPatch(BaseModel):
    status: str | None = None
    note: str | None = None
    approach: str | None = None


class PRCriteria(BaseModel):
    must: list[str] | None = None
    exclude: list[str] | None = None
    bonus: list[str] | None = None
    bonus_points: int | None = None
    fit: list[str] | None = None
    regions: list[str] | None = None
    followers_min: int | None = None
    followers_max: int | None = None
    recent_days: int | None = None
    skip_types: list[str] | None = None
    crm_min_grade: str | None = None
    search_kinds: list[str] | None = None
    note: str | None = None
    keywords: dict[str, list[str]] | None = None
    rescore: bool = True


@app.put("/api/prospects/criteria")
def pr_criteria(p: PRCriteria):
    """Sếp đặt điều kiện tìm khách sỉ: Mai học (lưu sổ kiến thức) và chấm lại các khách đã tìm."""
    import prospect
    import prospect_rules
    prospect_rules.save({k: v for k, v in p.model_dump().items() if v is not None and k not in ("keywords", "rescore")})
    if p.keywords is not None:
        kw = {str(d): [x.strip() for x in v if x.strip()][:12] for d, v in p.keywords.items() if str(d) in ("1", "2", "3", "4", "5")}
        db.set_setting("prospect_keywords", json.dumps({d: v for d, v in kw.items() if v}, ensure_ascii=False))
    res = prospect_rules.rescore_all() if p.rescore else None
    return {**prospect.overview(), "rescore": res}


@app.post("/api/prospects/rescore")
def pr_rescore():
    import prospect
    import prospect_rules
    return {**prospect.overview(), "rescore": prospect_rules.rescore_all()}


class PRLesson(BaseModel):
    text: str


@app.post("/api/prospects/lessons")
def pr_lesson_add(p: PRLesson):
    import prospect_rules
    try:
        return prospect_rules.add_lesson(p.text)
    except ValueError as e:
        raise HTTPException(400, str(e))


@app.post("/api/prospects/lessons/{lid}/apply")
def pr_lesson_apply(lid: int):
    import prospect
    import prospect_rules
    try:
        r = prospect_rules.apply_lesson(lid)
    except ValueError as e:
        raise HTTPException(404, str(e))
    return {**prospect.overview(), "groups_added": r["groups_added"], "rescore": prospect_rules.rescore_all()}


@app.delete("/api/prospects/lessons/{lid}")
def pr_lesson_del(lid: int):
    import prospect
    import prospect_rules
    prospect_rules.delete_lesson(lid)
    return prospect.overview()


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

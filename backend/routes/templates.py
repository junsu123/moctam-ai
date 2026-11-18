# ------------------------------------------------------------------ mẫu bài đăng nhóm của sếp
@app.get("/api/post-template")
def tpl_get():
    import post_template as T
    st = db.get_settings()
    return {"template": T.template(), "default": T.DEFAULT_TEMPLATE, "enabled": T.enabled(), "ai": st.get("template_ai", "1") == "1",
            "phone": T.phone_line(), "preview": T.preview(2),
            "stats": {"approved": db.one("SELECT COUNT(*) n FROM posts WHERE source='template' AND status='approved'")["n"],
                      "scheduled": db.one("SELECT COUNT(*) n FROM posts WHERE source='template' AND status='scheduled'")["n"],
                      "posted_today": db.one("SELECT COUNT(*) n FROM posts WHERE source='template' AND status='posted' AND posted_at LIKE ?",
                                             (db.today() + "%",))["n"]}}


class TplIn(BaseModel):
    template: str | None = None
    enabled: bool | None = None
    ai: bool | None = None


@app.put("/api/post-template")
def tpl_put(p: TplIn):
    if p.template is not None:
        t = p.template.strip()
        if t and len(t) < 40:
            raise HTTPException(400, "Mẫu quá ngắn")
        db.set_setting("post_template", t)
    if p.enabled is not None:
        db.set_setting("template_mode", "1" if p.enabled else "0")
    if p.ai is not None:
        db.set_setting("template_ai", "1" if p.ai else "0")
    db.log("minh", "Đổi mẫu bài đăng nhóm", "Sếp cập nhật mẫu bài đăng nhóm, Lan làm bài theo mẫu mới từ lượt sau")
    return tpl_get()


class TplPreview(BaseModel):
    template: str | None = None


@app.post("/api/post-template/preview")
def tpl_preview(p: TplPreview):
    import post_template as T
    return {"preview": T.preview(2, (p.template or "").strip() or None)}


class TplMake(BaseModel):
    count: int = 3


@app.post("/api/post-template/make")
def tpl_make(p: TplMake):
    import post_template as T
    made = T.make_posts(max(1, min(20, p.count)))
    return {"count": len(made)}


# ------------------------------------------------------------------ CEO học duyệt bài
@app.get("/api/ceo-review")
def cr_get():
    import ceo_review
    return ceo_review.overview()


class CRSet(BaseModel):
    min_score: int | None = None
    ai: bool | None = None


@app.put("/api/ceo-review")
def cr_put(p: CRSet):
    import ceo_review
    if p.min_score is not None:
        db.set_setting("ceo_review_min", str(max(40, min(95, p.min_score))))
    if p.ai is not None:
        db.set_setting("ceo_review_ai", "1" if p.ai else "0")
    return ceo_review.overview()


class CRTry(BaseModel):
    content: str


@app.post("/api/ceo-review/try")
def cr_try(p: CRTry):
    import ceo_review
    return ceo_review.review(p.content)


# ------------------------------------------------------------------ thư viện bài mẫu sỉ của sếp
@app.get("/api/samples")
def smp_list():
    import post_template as T
    T.seed()
    st = db.get_settings()
    return {"items": T.samples(), "enabled": T.enabled(), "ai": st.get("template_ai", "1") == "1", "phone": T.phone_line(),
            "stats": tpl_get()["stats"]}


class SampleIn(BaseModel):
    content: str
    title: str = ""


@app.post("/api/samples")
def smp_add(p: SampleIn):
    import post_template as T
    try:
        r = T.add_sample(p.content, p.title)
    except ValueError as e:
        raise HTTPException(400, str(e))
    db.log("lan", "Học kiến thức mới", f"Sếp thêm bài mẫu đăng nhóm: {r['title'][:80]}")
    return r


class SampleImport(BaseModel):
    text: str


@app.post("/api/samples/import")
def smp_import(p: SampleImport):
    import post_template as T
    n = T.import_many(p.text)
    if not n:
        raise HTTPException(400, "Không thêm được bài nào (bài quá ngắn hoặc đã có trong thư viện)")
    db.log("lan", "Học kiến thức mới", f"Sếp thêm {n} bài mẫu đăng nhóm vào thư viện")
    return {"added": n}


class SamplePatch(BaseModel):
    content: str | None = None
    title: str | None = None
    enabled: bool | None = None


@app.patch("/api/samples/{sid}")
def smp_patch(sid: int, p: SamplePatch):
    import post_template as T
    if not db.one("SELECT id FROM post_samples WHERE id=?", (sid,)):
        raise HTTPException(404, "Không tìm thấy bài mẫu")
    if p.content is not None:
        c = p.content.strip()
        if len(c) < 40:
            raise HTTPException(400, "Bài mẫu quá ngắn")
        db.run("UPDATE post_samples SET content=?, updated_at=? WHERE id=?", (c, db.now(), sid))
    if p.title is not None:
        db.run("UPDATE post_samples SET title=? WHERE id=?", (p.title.strip()[:80], sid))
    if p.enabled is not None:
        db.run("UPDATE post_samples SET enabled=? WHERE id=?", (1 if p.enabled else 0, sid))
    T._learn()
    return db.one("SELECT * FROM post_samples WHERE id=?", (sid,))


@app.delete("/api/samples/{sid}")
def smp_del(sid: int):
    import post_template as T
    db.run("DELETE FROM post_samples WHERE id=?", (sid,))
    T._learn()
    return {"ok": True}


@app.post("/api/samples/{sid}/preview")
def smp_preview(sid: int):
    import post_template as T
    return {"preview": T.preview(2, sample_id=sid)}

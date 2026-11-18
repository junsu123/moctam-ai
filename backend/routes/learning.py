# ------------------------------------------------------------------ tự học
@app.get("/api/learning")
def learning_overview():
    return learning.overview()


@app.post("/api/learning/run")
def learning_run():
    learning.nightly_async()
    return {"ok": True}


# ------------------------------------------------------------------ kho bài & phong cách viết của Lan
@app.get("/api/content-style")
def content_style_get():
    import content_style
    return content_style.overview()


class StyleSet(BaseModel):
    mode: str | None = None
    min: int | None = None


@app.put("/api/content-style")
def content_style_put(st: StyleSet):
    import content_style
    if st.mode is not None:
        if st.mode not in ("auto", "always", "off"):
            raise HTTPException(400, "Chế độ không hợp lệ")
        db.set_setting("self_write_mode", st.mode)
    if st.min is not None:
        db.set_setting("self_write_min", str(max(5, min(200, st.min))))
    return content_style.overview()


class StylePreview(BaseModel):
    product_id: int | None = None
    angle: str | None = None
    target: str = "group"


@app.post("/api/content-style/preview")
def content_style_preview(r: StylePreview):
    """Lan viết thử 1 bài theo phong cách đã học (chỉ xem, không lưu, không gọi Claude)."""
    import content_style
    import mock_brain
    ok, why = content_style.ready()
    if not ok:
        raise HTTPException(400, why)
    p = db.one("SELECT * FROM products WHERE id=?", (r.product_id,)) if r.product_id else learning.choose_product(db.q("SELECT * FROM products"))
    if not p:
        raise HTTPException(400, "Chưa có sản phẩm")
    ang = r.angle if r.angle in mock_brain.ANGLES else learning.choose_angle()
    d = content_style.compose(p, ang, r.target if r.target in ("group", "profile", "page") else "group", dry=True)
    if not d:
        raise HTTPException(400, "Lan chưa ghép được bài khác đủ xa các bài cũ, cần học thêm bài Claude viết")
    return {**d, "product": p["name"], "angle": mock_brain.ANGLES.get(ang, ang)}


# ------------------------------------------------------------------ sổ kiến thức
@app.get("/api/knowledge")
def knowledge_get(agent: str = "", q: str = ""):
    import knowledge
    return knowledge.overview(agent, q)


class KnowIn(BaseModel):
    agent_id: str = "all"
    topic: str
    content: str
    question: str = ""
    kind: str = "guide"


@app.post("/api/knowledge")
def knowledge_add(k: KnowIn):
    """Sếp dạy kiến thức: agent dùng ngay từ việc tiếp theo."""
    import knowledge
    if k.agent_id not in knowledge.ROLE_NAME:
        raise HTTPException(400, "Chọn agent để dạy")
    if len(k.content.strip()) < 15:
        raise HTTPException(400, "Nội dung kiến thức quá ngắn")
    if not k.topic.strip():
        raise HTTPException(400, "Nhập chủ đề")
    iid = knowledge.save(k.agent_id, k.topic, k.content, question=k.question, source="boss", confidence=1.0,
                         kind="faq" if k.kind == "faq" else "guide")
    db.log("minh", "Sếp dạy kiến thức", f"{knowledge.ROLE_NAME[k.agent_id]}: {k.topic[:80]}")
    return {"ok": True, "id": iid, **knowledge.overview()}


class KnowPatch(BaseModel):
    topic: str | None = None
    content: str | None = None
    question: str | None = None


@app.patch("/api/knowledge/{kid}")
def knowledge_patch(kid: int, p: KnowPatch):
    fields = {k: v.strip() for k, v in p.model_dump().items() if v is not None}
    if fields:
        db.run(f"UPDATE knowledge SET {', '.join(k + '=?' for k in fields)}, updated_at=? WHERE id=?", (*fields.values(), db.now(), kid))
    return db.one("SELECT * FROM knowledge WHERE id=?", (kid,))


@app.delete("/api/knowledge/{kid}")
def knowledge_delete(kid: int):
    db.run("DELETE FROM knowledge WHERE id=?", (kid,))
    return {"ok": True}


@app.post("/api/knowledge/study")
def knowledge_study():
    import knowledge
    threading.Thread(target=knowledge.study_all, daemon=True).start()
    return {"ok": True}


class KnowAsk(BaseModel):
    question: str


@app.post("/api/knowledge/ask")
def knowledge_ask(a: KnowAsk):
    """Sếp hỏi đội: tra sổ kiến thức trước, chưa có mới hỏi Claude và lưu lại."""
    import knowledge
    if not a.question.strip():
        raise HTTPException(400, "Nhập câu hỏi")
    return knowledge.ask("ceo", a.question)


class KnowSettings(BaseModel):
    idle_learning: bool | None = None
    idle_study_per_day: int | None = None
    knowledge_enabled: bool | None = None
    study_time: str | None = None
    study_per_agent: int | None = None
    self_study: bool | None = None


@app.put("/api/knowledge/settings")
def knowledge_settings(k: KnowSettings):
    import knowledge
    if k.self_study is not None:
        db.set_setting("self_study", "1" if k.self_study else "0")
    if k.knowledge_enabled is not None:
        db.set_setting("knowledge_enabled", "1" if k.knowledge_enabled else "0")
    if k.idle_learning is not None:
        db.set_setting("idle_learning", "1" if k.idle_learning else "0")
    if k.idle_study_per_day is not None:
        db.set_setting("idle_study_per_day", str(max(0, min(24, k.idle_study_per_day))))
    if k.study_time is not None:
        if not re.fullmatch(r"\d{2}:\d{2}", k.study_time):
            raise HTTPException(400, "Giờ phải có dạng HH:MM")
        db.set_setting("study_time", k.study_time)
    if k.study_per_agent is not None:
        db.set_setting("study_per_agent", str(max(1, min(5, k.study_per_agent))))
    return knowledge.overview()


class Teach(BaseModel):
    agent_id: str
    text: str


@app.post("/api/lessons")
def teach(t: Teach):
    """Sếp dạy trực tiếp: bài học được ghim, luôn nằm trong sổ tay của agent."""
    lid = learning.add_lesson(t.agent_id, t.text, "Sếp dạy", "boss", 1.0, None, 1)
    if not lid:
        raise HTTPException(400, "Bài học quá ngắn")
    db.log(t.agent_id, "Được sếp dạy", t.text[:120])
    return db.one("SELECT * FROM lessons WHERE id=?", (lid,))


class LessonPatch(BaseModel):
    text: str | None = None
    pinned: int | None = None
    status: str | None = None


@app.patch("/api/lessons/{lid}")
def patch_lesson(lid: int, p: LessonPatch):
    fields = {k: v for k, v in p.model_dump().items() if v is not None}
    if p.status and p.status not in ("active", "retired"):
        raise HTTPException(400)
    if fields:
        fields["updated_at"] = db.now()
        db.run(f"UPDATE lessons SET {', '.join(k + '=?' for k in fields)} WHERE id=?", (*fields.values(), lid))
    return db.one("SELECT * FROM lessons WHERE id=?", (lid,))


@app.get("/api/posts/recent-posted")
def recent_posted():
    return db.q("""SELECT p.id, p.title, p.posted_at, g.name group_name, p.target_type FROM posts p
                   LEFT JOIN groups g ON g.id=p.group_id WHERE p.status='posted' ORDER BY p.posted_at DESC LIMIT 40""")

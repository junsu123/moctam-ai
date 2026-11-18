# ------------------------------------------------------------------ khách hàng
class Lead(BaseModel):
    name: str
    contact: str = ""
    channel: str = "Facebook"
    source: str = ""
    business_type: str = ""
    need: str = ""
    note: str = ""
    post_id: int | None = None  # khách đến từ bài đăng nào (để cả đội học bài nào hiệu quả)


class LeadPatch(BaseModel):
    status: str | None = None
    note: str | None = None
    score: int | None = None
    contacted: bool = False


class ReplyReq(BaseModel):
    message: str = ""


@app.get("/api/leads")
def leads():
    return db.q("SELECT * FROM leads ORDER BY score DESC, id DESC")


@app.post("/api/leads")
def add_lead(l: Lead):
    kpi.clear_sample_leads()
    data = l.model_dump()
    score = workflows.score_lead(data)
    src = l.source
    phone = kpi.norm_phone(f"{l.contact} {l.need}")
    if l.post_id:
        post = db.one("""SELECT p.id, g.name gname, p.target_type FROM posts p LEFT JOIN groups g ON g.id=p.group_id
                         WHERE p.id=?""", (l.post_id,))
        if post:
            src = src or f"Bài #{post['id']} · {post['gname'] or 'Trang cá nhân'}"
            db.run("UPDATE posts SET leads=COALESCE(leads,0)+1 WHERE id=?", (post["id"],))
            db.run("UPDATE groups SET leads_count=(SELECT COALESCE(SUM(leads),0) FROM posts WHERE group_id=groups.id)")
            learning.on_post_leads(post["id"], 1)
    lid = db.run("""INSERT INTO leads(name, contact, channel, source, business_type, need, note, score, status,
                    post_id, phone, phone_at, origin, created_at, updated_at) VALUES (?,?,?,?,?,?,?,?,'new',?,?,?,'manual',?,?)""",
                 (l.name, l.contact, l.channel, src, l.business_type, l.need, l.note, score, l.post_id,
                  phone, db.now() if phone else None, db.now(), db.now()))
    db.log("ha", "Khách mới", f"{l.name} ({score} điểm)")
    return db.one("SELECT * FROM leads WHERE id=?", (lid,))


@app.patch("/api/leads/{lid}")
def patch_lead(lid: int, p: LeadPatch):
    fields = {k: v for k, v in p.model_dump().items() if v is not None and k != "contacted"}
    fields["updated_at"] = db.now()
    if p.contacted:
        fields["last_contact_at"] = db.now()
    old = db.one("SELECT status FROM leads WHERE id=?", (lid,))
    if p.status == "lost" and old and old["status"] != "lost":  # không mua: ghi qua funnel (lý do chọn sau)
        import funnel
        funnel.mark_lost(lid)
        fields.pop("status")
        old = None
    db.run(f"UPDATE leads SET {', '.join(k + '=?' for k in fields)} WHERE id=?", (*fields.values(), lid))
    if p.status and old and p.status != old["status"]:
        learning.on_lead_status(lid, p.status)
    return db.one("SELECT * FROM leads WHERE id=?", (lid,))


class LostIn(BaseModel):
    reason: str = ""
    note: str = ""


@app.post("/api/leads/{lid}/lost")
def lead_lost(lid: int, p: LostIn):
    """Khách không mua: ghi kèm lý do để cả đội biết vì sao (Mai, Lan, Hà học theo)."""
    import funnel
    if p.reason not in funnel.LOST_REASONS:
        raise HTTPException(400, "Chọn lý do khách không mua")
    r = funnel.mark_lost(lid, p.reason, p.note)
    if not r:
        raise HTTPException(404)
    return r


@app.get("/api/focus")
def focus_overview():
    import channel_focus
    return channel_focus.overview()


@app.post("/api/focus/run")
def focus_run():
    import channel_focus
    r = channel_focus.run(force=True)
    return {"done": r["done"], "proposed": r["proposed"], **channel_focus.overview()}


@app.post("/api/focus/resume/{key}")
def focus_resume(key: str):
    import channel_focus
    if key not in channel_focus.CONTROL:
        raise HTTPException(400, "Kênh này không tạm dừng được")
    channel_focus.resume(key)
    return channel_focus.overview()


@app.put("/api/focus/settings")
def focus_settings(data: dict):
    import channel_focus
    if "enabled" in data:
        db.set_setting("focus_enabled", "1" if data["enabled"] else "0")
    return channel_focus.overview()


@app.get("/api/funnel")
def funnel_report(days: int = 30):
    import funnel
    return funnel.report(max(7, min(180, days)))


class JunkIn(BaseModel):
    reason: str = "other"
    note: str = ""


@app.post("/api/leads/{lid}/junk")
def lead_junk(lid: int, p: JunkIn):
    """Sếp loại khách là data rác: Mai ghi nhớ để lần sau tìm khách tự loại các trường hợp giống vậy."""
    import junk
    import prospect_rules
    try:
        r = junk.mark(lid, p.reason, p.note)
    except ValueError as e:
        raise HTTPException(404, str(e))
    try:
        prospect_rules.rescore_all()  # khách khác giống data rác này: chấm lại
    except Exception as e:
        print("[junk rescore]", e)
    return r


@app.post("/api/leads/{lid}/unjunk")
def lead_unjunk(lid: int):
    import junk
    junk.restore(lid)
    return db.one("SELECT * FROM leads WHERE id=?", (lid,))


@app.get("/api/junk")
def junk_get():
    import junk
    return junk.overview()


class JunkWord(BaseModel):
    word: str


@app.post("/api/junk/exclude")
def junk_exclude(p: JunkWord):
    import junk
    import prospect_rules
    junk.exclude_word(p.word.strip())
    prospect_rules.rescore_all()
    return junk.overview()


@app.post("/api/junk/dismiss")
def junk_dismiss(p: JunkWord):
    import junk
    junk.dismiss(p.word.strip())
    return junk.overview()


class ReplySent(BaseModel):
    text: str = ""


@app.post("/api/replies/{rid}/sent")
def reply_sent(rid: int, r: ReplySent):
    """Sếp đã gửi tin cho khách (có thể đã sửa) -> lưu bản cuối để Hà học tin nào chốt được."""
    db.run("UPDATE replies SET sent=1, text=CASE WHEN ?!='' THEN ? ELSE text END, sent_at=? WHERE id=?",
           (r.text.strip(), r.text.strip(), db.now(), rid))
    learning.award("ha", 2, "Gửi tin nhắn cho khách")
    return {"ok": True}


@app.post("/api/leads/{lid}/reply")
def lead_reply(lid: int, r: ReplyReq):
    return workflows.draft_reply(lid, r.message) or {"reply": ""}


@app.get("/api/leads/follow-up")
def follow_up():
    return workflows.follow_up_list()

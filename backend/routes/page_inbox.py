# ------------------------------------------------------------------ tin nhắn Fanpage (Messenger, Graph API): Hà soạn, sếp duyệt, gửi trong 24 giờ
class InboxSend(BaseModel):
    text: str | None = None


@app.get("/api/page-inbox")
def page_inbox_get():
    import page_inbox
    return page_inbox.overview()


@app.post("/api/page-inbox/sync")
def page_inbox_sync():
    import page_inbox
    r = page_inbox.sync()
    if not r.get("ok"):
        raise HTTPException(400, r.get("why") or "Chưa đọc được tin nhắn Fanpage")
    return r


@app.put("/api/page-inbox/settings")
def page_inbox_settings(data: dict):
    for k, v in data.items():
        if k in ("page_inbox_on", "page_inbox_auto"):
            db.set_setting(k, "1" if str(v) in ("1", "true", "True") else "0")
        elif k == "page_inbox_minutes":
            db.set_setting(k, str(max(5, min(120, int(v or 10)))))
    import page_inbox
    return page_inbox.overview()


@app.post("/api/page-inbox/{tid}/{act}")
def page_inbox_act(tid: int, act: str, body: InboxSend | None = None):
    import page_inbox
    try:
        if act == "send":
            return page_inbox.send(tid, body.text if body else None)
        if act == "skip":
            return page_inbox.skip(tid)
        if act == "redraft":
            return page_inbox.redraft(tid)
    except ValueError as e:
        raise HTTPException(400, str(e))
    raise HTTPException(404)

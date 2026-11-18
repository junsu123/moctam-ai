# ------------------------------------------------------------------ sổ lỗi
@app.get("/api/errors")
def errors_list(status: str = "open", source: str = ""):
    return {"items": errors.listing(status, source), "new": errors.count_new(), "sources": errors.SOURCES,
            "open": db.one("SELECT COUNT(*) n FROM errors WHERE status!='resolved'")["n"]}


class ErrorIn(BaseModel):
    title: str
    message: str = ""
    detail: str = ""
    screen: str = ""
    action: str = ""


@app.post("/api/errors")
def errors_add(e: ErrorIn):
    """Giao diện gửi lỗi người dùng gặp ở bất kỳ màn hình nào."""
    return {"id": errors.report("ui", e.title, e.message, e.detail, screen=e.screen or None, action=e.action)}


class ErrorPatch(BaseModel):
    status: str


@app.patch("/api/errors/{eid}")
def errors_patch(eid: int, p: ErrorPatch):
    if p.status not in ("new", "seen", "resolved"):
        raise HTTPException(400, "Trạng thái không hợp lệ")
    db.run("UPDATE errors SET status=? WHERE id=?", (p.status, eid))
    return {"ok": True, "new": errors.count_new()}


@app.post("/api/errors/seen")
def errors_seen():
    db.run("UPDATE errors SET status='seen' WHERE status='new'")
    return {"ok": True}


@app.post("/api/errors/resolve-all")
def errors_resolve_all():
    db.run("UPDATE errors SET status='resolved' WHERE status!='resolved'")
    return {"ok": True}


@app.delete("/api/errors/resolved")
def errors_clear():
    db.run("DELETE FROM errors WHERE status='resolved'")
    return {"ok": True}

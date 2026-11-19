# ------------------------------------------------------------------ Các Trang của Nhi: từ khóa sếp đặt, duyệt bài, Nhi ghi nhớ theo sếp
@app.get("/api/nhi-pages")
def nhi_pages_get():
    import page_brain
    return page_brain.overview()


@app.put("/api/nhi-pages/settings")
def nhi_pages_settings(data: dict):
    db.set_setting("trend_review", "1" if data.get("review") else "0")
    db.log("nhi", "Sếp đổi cách duyệt bài Trang", "Sếp duyệt từng bài trước khi đăng" if data.get("review") else "Nhi tự đăng, không chờ sếp duyệt")
    return {"ok": True}


@app.put("/api/nhi-pages/{pid}")
def nhi_pages_update(pid: int, data: dict):
    import page_brain
    try:
        return page_brain.update_page(pid, data)
    except ValueError as e:
        raise HTTPException(400, str(e))


@app.post("/api/nhi-pages/{pid}/suggest")
def nhi_pages_suggest(pid: int):
    import page_brain
    try:
        return {"keywords": page_brain.suggest_keywords(pid)}
    except ValueError as e:
        raise HTTPException(400, str(e))


@app.delete("/api/nhi-pages/memory/{mid}")
def nhi_pages_forget(mid: int):
    db.run("DELETE FROM page_memory WHERE id=?", (mid,))
    return {"ok": True}


@app.post("/api/nhi-pages/posts/{post_id}/review")
def nhi_pages_review(post_id: int, data: dict):
    import page_brain
    if data.get("action") not in ("approve", "reject"):
        raise HTTPException(400, "Thao tác không hợp lệ")
    try:
        return page_brain.review(post_id, data["action"], data.get("content"), data.get("reason") or "")
    except ValueError as e:
        raise HTTPException(400, str(e))


@app.post("/api/nhi-pages/approve-all")
def nhi_pages_approve_all():
    import page_brain
    return {"approved": page_brain.approve_all()}

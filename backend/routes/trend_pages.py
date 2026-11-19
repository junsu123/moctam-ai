# ------------------------------------------------------------------ Nhi: xu hướng, Trang mới, bài Trang chờ ảnh (ảnh qua Telegram)
@app.get("/api/trends")
def trends_get():
    import trend_pages
    return trend_pages.overview()


@app.post("/api/trends/research")
def trends_research():
    import trend_pages
    r = trend_pages.research()
    if not r.get("ok"):
        raise HTTPException(400, r.get("why") or "Chưa đọc được xu hướng")
    return r


@app.post("/api/trends/plan")
def trends_plan():
    import trend_pages
    return {"written": trend_pages.plan_today(force=True)}


@app.post("/api/trends/pages")
def trends_page_add(data: dict):
    import trend_pages
    try:
        return trend_pages.new_page(data.get("name", ""), data.get("niche", ""), data.get("description", ""))
    except ValueError as e:
        raise HTTPException(400, str(e))


@app.post("/api/trends/pages/{pid}/activate")
def trends_page_activate(pid: int, data: dict):
    import trend_pages
    try:
        return trend_pages.activate(pid, data.get("url", ""), int(data.get("admin_account_id") or 0), int(data.get("posts_per_day") or 2),
                                    data.get("times") or "09:00,19:30")
    except ValueError as e:
        raise HTTPException(400, str(e))


@app.post("/api/trends/pages/{pid}/status")
def trends_page_status(pid: int, data: dict):
    st = data.get("status")
    if st not in ("active", "paused", "dismissed"):
        raise HTTPException(400, "Trạng thái không hợp lệ")
    p = db.one("SELECT * FROM fb_pages WHERE id=?", (pid,))
    if not p:
        raise HTTPException(404)
    if st == "active" and not p.get("url"):
        raise HTTPException(400, "Trang chưa có link: bấm Tôi đã tạo Trang này")
    db.run("UPDATE fb_pages SET status=? WHERE id=?", (st, pid))
    if st != "active":
        db.run("UPDATE posts SET status='rejected', error='Sếp dừng Trang' WHERE fb_page_ref=? AND status IN ('need_image','scheduled')", (pid,))
    return {"ok": True}


@app.post("/api/trends/posts/{post_id}/image")
def trends_post_image(post_id: int, data: dict):
    """Tải ảnh từ web (dự phòng khi không dùng Telegram): data = {"data": base64, "ext": "jpg"}."""
    import trend_pages
    try:
        raw = base64.b64decode((data.get("data") or "").split(",")[-1])
        return trend_pages.set_image(post_id, raw, (data.get("ext") or "jpg").lower())
    except (ValueError, base64.binascii.Error) as e:
        raise HTTPException(400, str(e) or "Ảnh không hợp lệ")


@app.post("/api/trends/posts/{post_id}/ask")
def trends_post_ask(post_id: int):
    import trend_pages
    if not trend_pages.ask_image(post_id):
        raise HTTPException(400, "Chưa gửi được lên Telegram (chưa kết nối bot?)")
    return {"ok": True}


@app.post("/api/trends/posts/{post_id}/skip")
def trends_post_skip(post_id: int):
    db.run("UPDATE posts SET status='rejected', error='Sếp bỏ bài' WHERE id=? AND status IN ('need_image','scheduled')", (post_id,))
    return {"ok": True}

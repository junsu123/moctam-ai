# ------------------------------------------------------------------ Các Trang của Nhi: từ khóa sếp đặt, duyệt bài, Nhi ghi nhớ theo sếp
@app.get("/api/nhi-pages")
def nhi_pages_get():
    import page_brain
    return page_brain.overview()


@app.put("/api/nhi-pages/settings")
def nhi_pages_settings(data: dict):
    for k, key in (("noimg", "trend_noimg_post"), ("auto_kw", "nhi_auto_kw")):
        if k in data:
            db.set_setting(key, "1" if data[k] else "0")
    if (data.get("focus") or "").strip():
        db.set_setting("nhi_focus", " | ".join(x.strip() for x in data["focus"].split("|") if x.strip())[:500])
    if "review" not in data:
        return {"ok": True}
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


# ------------------------------------------------------------------ Nhi tự làm ảnh (Cloudflare Workers AI + Pixabay)
@app.get("/api/nhi-images")
def nhi_images_get():
    import image_gen
    return image_gen.status()


@app.put("/api/nhi-images")
def nhi_images_put(data: dict):
    import image_gen
    for k in ("cf_account_id", "cf_api_token", "pixabay_key"):
        v = (data.get(k) or "").strip()
        if v and "…" not in v and "•" not in v:
            db.set_setting(k, v)
        elif data.get(k) == "" and data.get("clear"):
            db.set_setting(k, "")
    if "on" in data:
        db.set_setting("img_auto", "1" if data["on"] else "0")
    return image_gen.status()


@app.post("/api/nhi-images/test")
def nhi_images_test():
    import image_gen
    return image_gen.test()

# ------------------------------------------------------------------ website công ty (Vy)
SITE_KEYS = {"site_name", "site_legal_name", "site_tagline", "site_domain", "site_about", "site_address", "site_email", "site_phone",
             "site_certs", "site_founded", "site_color", "site_ga_id", "site_posts_week", "site_write_days", "site_write_time",
             "site_auto_publish", "site_min_seo", "site_ftp_host", "site_ftp_user", "site_ftp_pass", "site_ftp_dir", "site_ftp_tls",
             "site_deploy_mode", "site_auto_deploy", "site_sync_url", "site_chmod_file", "site_chmod_dir"}


@app.get("/api/website")
def website_get():
    import website
    return website.overview()


@app.put("/api/website/settings")
def website_settings(data: dict):
    import website
    bad = [k for k in data if k not in SITE_KEYS]
    if bad:
        raise HTTPException(400, "Không sửa được: " + ", ".join(bad))
    for k, v in data.items():
        if k == "site_ftp_pass" and not str(v):
            continue  # để trống = giữ mật khẩu cũ
        if k == "site_ftp_host" and v:
            import site_deploy
            h, p = site_deploy.clean_host(str(v))
            v = f"{h}:{p}" if p else h
        if k in ("site_chmod_file", "site_chmod_dir"):
            v = str(v).strip()
            if not re.fullmatch(r"[0-7]{3}", v) or int(v[2]) & 2 or not int(v[0]) & 4:
                raise HTTPException(400, "Quyền phải là 3 số như 755 hoặc 644 (không cho người khác ghi: không dùng 777, 666)")
        if k == "site_deploy_mode" and v not in ("auto", "ftps", "ftp", "sftp", "http"):
            raise HTTPException(400, "Cách đăng không hợp lệ")
        if k in ("site_ftp_host", "site_ftp_user", "site_ftp_dir", "site_deploy_mode"):
            db.set_setting("site_deploy_ok_mode", "")
        if k == "site_domain" and v:
            v = str(v).strip().rstrip("/")
            if not re.match(r"^https?://", v):
                v = "https://" + v
        db.set_setting(k, str(v))
    return website.overview()


class SiteKeyword(BaseModel):
    keyword: str
    priority: int = 2


@app.post("/api/website/keywords")
def website_add_kw(k: SiteKeyword):
    import website
    kw = k.keyword.strip()
    if len(kw) < 3:
        raise HTTPException(400, "Ghi từ khóa")
    db.run("INSERT OR IGNORE INTO site_keywords(keyword, cluster, intent, priority, status, source, created_at) VALUES (?,?,?,?,?,?,?)",
           (kw[:100], "", "", max(1, min(3, k.priority)), "planned", "boss", db.now()))
    return website.overview()


@app.delete("/api/website/keywords/{kid}")
def website_del_kw(kid: int):
    import website
    db.run("DELETE FROM site_keywords WHERE id=? AND status='planned'", (kid,))
    return website.overview()


@app.post("/api/website/keywords/plan")
def website_plan_kw():
    import website
    return {"added": website.plan_more(), **website.overview()}


class SiteWrite(BaseModel):
    keyword: str | None = None
    kid: int | None = None
    wait: bool = False


@app.post("/api/website/write")
def website_write(w: SiteWrite):
    import website
    if w.wait:
        try:
            return website.write(w.keyword, w.kid)
        except ValueError as e:
            raise HTTPException(400, str(e))

    def run():
        try:
            website.write(w.keyword, w.kid)
        except Exception as e:
            import errors
            errors.report_exc("website", "Vy viết bài website bị lỗi", e, screen="website")
    threading.Thread(target=run, daemon=True).start()
    return {"started": True}


@app.get("/api/website/posts/{pid}")
def website_post(pid: int):
    import website
    p = website.get(pid)
    if not p:
        raise HTTPException(404, "Không có bài này")
    return p


@app.patch("/api/website/posts/{pid}")
def website_post_update(pid: int, data: dict):
    import website
    try:
        return website.update(pid, data)
    except ValueError as e:
        raise HTTPException(400, str(e))


@app.post("/api/website/posts/{pid}/publish")
def website_publish(pid: int):
    import website
    try:
        return website.publish(pid)
    except ValueError as e:
        raise HTTPException(400, str(e))


@app.post("/api/website/posts/{pid}/unpublish")
def website_unpublish(pid: int):
    import website
    return website.unpublish(pid)


@app.delete("/api/website/posts/{pid}")
def website_delete(pid: int):
    import website
    website.delete(pid)
    return {"ok": True}


class SiteShow(BaseModel):
    show: bool | None = None


@app.put("/api/website/products/{pid}")
def website_product_show(pid: int, b: SiteShow):
    import website
    try:
        p = website.set_show(pid, b.show)
    except KeyError:
        raise HTTPException(404, "Không tìm thấy sản phẩm")
    return {"id": pid, "on": p["site_on"], "why": p["site_why"], "auto": p["site_auto"]}


@app.post("/api/website/build")
def website_build():
    import website
    return website.build()


@app.get("/api/website/export.zip")
def website_zip():
    import website
    from fastapi.responses import Response
    return Response(website.export_zip(), media_type="application/zip",
                    headers={"Content-Disposition": 'attachment; filename="website.zip"'})


@app.post("/api/website/deploy")
def website_deploy(full: int = 0):
    import website
    try:
        return website.deploy(full=bool(full))
    except ValueError as e:
        raise HTTPException(400, str(e))
    except Exception as e:
        raise HTTPException(400, f"Không đăng được lên hosting: {e}")


@app.post("/api/website/deploy/test")
def website_deploy_test():
    import site_deploy
    return site_deploy.test()


@app.post("/api/website/check")
def website_check():
    """Mở sitemap.xml / robots.txt trên tên miền như Googlebot, tìm lỗi, tự sửa thư mục web và đăng lại."""
    import site_deploy
    return site_deploy.check()


@app.get("/api/website/mt-sync.php")
def website_sync_php(new: int = 0):
    """Tệp cổng nhận PHP (có mã bí mật của máy này) để tải lên public_html một lần."""
    import site_deploy
    from fastapi.responses import Response
    return Response(site_deploy.sync_php(new=bool(new)), media_type="application/octet-stream",
                    headers={"Content-Disposition": f'attachment; filename="{site_deploy.SYNC_FILE}"'})


@app.get("/site", include_in_schema=False)
@app.get("/site/{path:path}", include_in_schema=False)
def site_preview(path: str = ""):
    """Xem trước website: phục vụ data/site/, sửa đường dẫn gốc (/...) thành /site/... để bấm thử được."""
    import website
    root = website.SITE_DIR.resolve()
    if not (root / "index.html").exists():
        website.build()
    f = (root / path).resolve()
    if root not in f.parents and f != root:
        raise HTTPException(404, "Không có trang này")
    if f.is_dir():
        f = f / "index.html"
    if not f.exists():
        f, code = root / "404.html", 404
    else:
        code = 200
    if f.suffix == ".html":
        doc = f.read_text(encoding="utf-8")
        doc = re.sub(r'(href|src)="/(?!/)', r'\1="/site/', doc)
        return HTMLResponse(doc, status_code=code)
    return FileResponse(f)

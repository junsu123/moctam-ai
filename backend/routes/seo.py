# ------------------------------------------------------------------ đội SEO: Vy (Leader), Hương (Content), Khải (Technical)
import json
import re

class SeoGoogle(BaseModel):
    sa: str | None = None
    gsc_site: str | None = None
    ga4: str | None = None
    psi_key: str | None = None


@app.get("/api/seo")
def seo_get():
    import seo_team
    return seo_team.overview()


@app.put("/api/seo/google")
def seo_google_put(g: SeoGoogle):
    import seo_team
    if g.sa is not None and g.sa.strip():
        try:
            d = json.loads(g.sa)
            assert d.get("client_email") and "PRIVATE KEY" in (d.get("private_key") or "")
        except Exception:
            raise HTTPException(400, "Dán nguyên nội dung tệp khóa JSON của tài khoản dịch vụ (có client_email, private_key)")
        db.set_setting("seo_google_sa", g.sa.strip())
        db.set_setting("seo_gsc_site", "")  # tự tìm lại trang web theo tài khoản mới
    if g.gsc_site is not None:
        db.set_setting("seo_gsc_site", g.gsc_site.strip())
    if g.ga4 is not None:
        db.set_setting("seo_ga4_property", re.sub(r"\D", "", g.ga4))
    if g.psi_key is not None and g.psi_key != "••••••":
        db.set_setting("seo_psi_key", g.psi_key.strip())
    return seo_team.overview()


@app.delete("/api/seo/google")
def seo_google_del():
    import seo_team
    for k in ("seo_google_sa", "seo_gsc_site"):
        db.set_setting(k, "")
    return seo_team.overview()


@app.post("/api/seo/google/test")
def seo_google_test():
    import seo_team
    return seo_team.test_google()


class SeoRun(BaseModel):
    job: str


@app.post("/api/seo/run")
def seo_run(r: SeoRun):
    import seo_team
    fn = {"audit": seo_team.run_audit, "leader": seo_team.run_leader, "content": seo_team.run_content}.get(r.job)
    if not fn:
        raise HTTPException(400, "Việc không hợp lệ")
    return {"started": seo_team._bg(r.job if r.job != "leader" else "leader", fn), **seo_team.overview()}


@app.post("/api/seo/products/{pid}/write")
def seo_product_write(pid: int):
    import seo_team
    import website
    try:
        r = seo_team.write_product(pid)
    except ValueError as e:
        raise HTTPException(400, str(e))
    if r["status"] == "approved":
        website.build()
    return {"result": r, **seo_team.overview()}


@app.put("/api/seo/products/{pid}")
def seo_product_approve(pid: int, data: dict):
    import seo_team
    import website
    try:
        seo_team.approve_product(pid, data)
    except ValueError as e:
        raise HTTPException(400, str(e))
    website.build()
    return seo_team.overview()


@app.post("/api/seo/products/{pid}/reject")
def seo_product_reject(pid: int):
    import seo_team
    import website
    seo_team.reject_product(pid)
    website.build()
    return seo_team.overview()

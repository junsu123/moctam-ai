# ------------------------------------------------------------------ sức khỏe từng nick (trang Nhân viên sale)
@app.get("/api/nick-health")
def nick_health_get():
    import nick_health
    return nick_health.overview()


@app.put("/api/nick-health/settings")
def nick_health_settings(data: dict):
    import nick_health
    if "auto" in data:
        db.set_setting("nick_health_auto", "1" if data["auto"] in (1, "1", True, "true") else "0")
        nick_health._cache.clear()
    return nick_health.overview()

# ------------------------------------------------------------------ sếp giao việc cho CEO
@app.get("/api/ceo/chat")
def ceo_chat_get():
    import ceo_orders
    return ceo_orders.overview()


class CeoMsg(BaseModel):
    text: str


@app.post("/api/ceo/chat")
def ceo_chat(m: CeoMsg):
    import ceo_orders
    try:
        ceo_orders.handle(m.text, via="web")
    except ValueError as e:
        raise HTTPException(400, str(e))
    return ceo_orders.overview()


class Autopilot(BaseModel):
    on: bool


@app.put("/api/ceo/autopilot")
def ceo_autopilot(a: Autopilot):
    import ceo_orders
    db.set_setting("ceo_autopilot", "1" if a.on else "0")
    db.log("ceo", "Luật vận hành", "Sếp chỉ giao việc cho CEO, CEO tự vận hành" if a.on else "Sếp giao việc trực tiếp cho từng agent")
    return ceo_orders.overview()


@app.delete("/api/ceo/orders/{oid}")
def ceo_order_off(oid: int):
    import ceo_orders
    db.run("UPDATE ceo_orders SET active=0 WHERE id=?", (oid,))
    db.log("ceo", "Bỏ chỉ đạo", f"Chỉ đạo #{oid}")
    return ceo_orders.overview()


# ------------------------------------------------------------------ CEO
@app.get("/api/ceo")
def ceo_get():
    return ceo.overview()


class CeoSettings(BaseModel):
    mode: str | None = None
    enabled: bool | None = None
    potential: bool | None = None
    milestones: list[dict] | None = None  # [{"amount": 50000000, "hires": 1}]


@app.put("/api/ceo")
def ceo_put(c: CeoSettings):
    if c.mode in ("auto", "approve"):
        db.set_setting("ceo_mode", c.mode)
    if c.enabled is not None:
        db.set_setting("ceo_enabled", "1" if c.enabled else "0")
    if c.potential is not None:
        db.set_setting("ceo_potential", "1" if c.potential else "0")
    if c.milestones is not None:
        ms = []
        for m in c.milestones:
            amt, n = int(m.get("amount") or 0), int(m.get("hires") or 0)
            if amt <= 0 or not 1 <= n <= 4:
                raise HTTPException(400, "Mỗi mốc cần số tiền lớn hơn 0 và tuyển 1-4 người")
            ms.append((amt, n))
        db.set_setting("ceo_milestones", ",".join(f"{a}:{n}" for a, n in sorted(set(ms))))
    return ceo.overview()


class Approve(BaseModel):
    approve: bool


@app.post("/api/ceo/decisions/{did}")
def ceo_resolve(did: int, a: Approve):
    try:
        ceo.resolve(did, a.approve)
    except ValueError as e:
        raise HTTPException(400, str(e))
    return ceo.overview()


@app.post("/api/ceo/review")
def ceo_review_now():
    """Sếp bấm 'CEO đánh giá ngay': chạy đánh giá tiềm năng và mốc doanh thu ngay lập tức."""
    if not company.active():
        raise HTTPException(400, "Công ty chưa hoạt động")
    ceo.check_milestones()
    ceo.check_potential()
    return ceo.overview()

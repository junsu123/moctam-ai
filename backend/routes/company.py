# ------------------------------------------------------------------ công ty: vốn, doanh thu, sa thải, giải thể
@app.get("/api/company")
def company_overview():
    return company.overview()


class Found(BaseModel):
    capital: int = 10_000_000
    usd_vnd: float | None = None


@app.post("/api/company/found")
def company_found(f: Found):
    if f.capital < 0:
        raise HTTPException(400, "Vốn không hợp lệ")
    if company.status() == "active":
        raise HTTPException(400, "Công ty đang hoạt động")
    company.found(f.capital, f.usd_vnd)
    return company.overview()


class Money(BaseModel):
    amount: int
    note: str = ""
    category: str = "Khác"
    date: str = ""


@app.post("/api/company/capital")
def company_capital(m: Money):
    if m.amount <= 0:
        raise HTTPException(400, "Số tiền phải lớn hơn 0")
    company.add_capital(m.amount, m.note)
    return company.overview()


class Revenue(BaseModel):
    amount: int
    customer: str = ""
    note: str = ""
    lead_id: int | None = None


@app.post("/api/company/revenue")
def company_revenue(r: Revenue):
    """Sếp tự nhập doanh thu (sếp chốt và làm việc với khách)."""
    if r.amount <= 0:
        raise HTTPException(400, "Nhập doanh thu lớn hơn 0")
    try:
        company.add_order(r.lead_id, r.amount, r.note, via="app", customer=r.customer)
    except ValueError as e:
        raise HTTPException(404, str(e))
    return company.overview()


class OrderReq(BaseModel):
    amount: int
    note: str = ""


@app.post("/api/leads/{lid}/order")
def lead_order(lid: int, o: OrderReq):
    if o.amount <= 0:
        raise HTTPException(400, "Nhập giá trị đơn lớn hơn 0")
    try:
        return company.add_order(lid, o.amount, o.note)
    except ValueError as e:
        raise HTTPException(404, str(e))


@app.delete("/api/orders/{oid}")
def del_order(oid: int):
    db.run("DELETE FROM orders WHERE id=?", (oid,))
    return company.overview()


class Replace(BaseModel):
    name: str = ""


@app.post("/api/sales/{sid}/replace")
def replace_sale(sid: int, r: Replace):
    """Tuyển người thay cho sale đã nghỉ: dùng tiếp nick (hồ sơ Chrome đã đăng nhập) của người cũ."""
    try:
        return _sale_out(ceo.replace(sid, r.name, by="boss"))
    except ValueError as e:
        raise HTTPException(400, str(e))

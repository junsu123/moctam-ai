# ------------------------------------------------------------------ KPI & Telegram
@app.get("/api/kpi")
def kpi_overview():
    st = kpi.day_stats()
    return {"today": st, "pace": kpi.pace(st), "per_sale": kpi.per_sale(), "history": kpi.history(14), "streak": kpi.streak()}


@app.post("/api/leads/{lid}/escalate")
def escalate_lead(lid: int):
    ok = kpi.escalate(lid, "Sếp chọn tự tư vấn khách này", force=True)
    return {"ok": ok, "telegram": telegram_bot.configured()}


@app.post("/api/scan/now")
def scan_now():
    return {"posts": telegram_bot.start_scan_round(force=True)}


@app.get("/api/telegram")
def tg_status():
    return telegram_bot.status()


class TgToken(BaseModel):
    token: str


@app.post("/api/telegram/token")
def tg_save_token(t: TgToken):
    """Lưu token bot Telegram sau khi hỏi Telegram token có đúng không."""
    try:
        bot = telegram_bot.save_token(t.token)
    except ValueError as e:
        raise HTTPException(400, str(e))
    db.log("minh", "Kết nối Telegram", f"Đã lưu token bot @{bot.get('username')}")
    return telegram_bot.status()


@app.delete("/api/telegram/token")
def tg_delete_token():
    db.set_setting("tg_token", "")
    db.set_setting("tg_chat_ids", "")
    db.set_setting("tg_pair_code", "")
    telegram_bot.reset_token()
    return telegram_bot.status()


class TgReport(BaseModel):
    report_done: bool


@app.put("/api/telegram/report")
def tg_report(r: TgReport):
    db.set_setting("tg_report_done", "1" if r.report_done else "0")
    return telegram_bot.status()


@app.post("/api/telegram/pair")
def tg_pair():
    if not telegram_bot.token():
        raise HTTPException(400, "Dán token bot Telegram và bấm Lưu trước")
    return {"code": telegram_bot.new_pair_code(), **telegram_bot.status()}


class TgSend(BaseModel):
    kind: str = "test"


@app.post("/api/telegram/send")
def tg_send(t: TgSend):
    if not telegram_bot.configured():
        raise HTTPException(400, "Chưa ghép nối Telegram. Tạo mã ghép nối và gửi mã đó cho bot")
    text = {"test": "👋 Phòng kinh doanh AI đã kết nối thành công. Sếp sẽ nhận báo cáo và khách cần tư vấn tại đây.",
            "kpi": None, "morning": None, "evening": None}.get(t.kind)
    text = text or {"kpi": telegram_bot.kpi_text, "morning": telegram_bot.morning_text, "evening": telegram_bot.evening_text}[t.kind]()
    sent = telegram_bot.send(text)
    if not sent:
        raise HTTPException(502, "Gửi Telegram không thành công: " + (telegram_bot.status().get("error") or "không rõ lỗi"))
    return {"ok": True}


@app.post("/api/telegram/unlink")
def tg_unlink():
    db.set_setting("tg_chat_ids", "")
    return telegram_bot.status()

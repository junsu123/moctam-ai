# ------------------------------------------------------------------ bot Telegram riêng cho ảnh + việc của Nhi (Trang xu hướng)
@app.get("/api/tg-img")
def tg_img_status():
    import telegram_img
    return telegram_img.status()


@app.post("/api/tg-img/token")
def tg_img_token(data: dict):
    import telegram_img
    try:
        telegram_img.save_token(data.get("token") or "")
    except ValueError as ex:
        raise HTTPException(400, str(ex))
    return {**telegram_img.status(), "pair_code": telegram_img.new_pair_code()}


@app.post("/api/tg-img/pair")
def tg_img_pair():
    import telegram_img
    if not telegram_img.token():
        raise HTTPException(400, "Nhập token bot ảnh trước")
    return {**telegram_img.status(), "pair_code": telegram_img.new_pair_code()}


@app.post("/api/tg-img/test")
def tg_img_test():
    import telegram_img
    if not telegram_img.configured():
        raise HTTPException(400, "Bot ảnh chưa ghép nối: gửi mã 6 số cho bot trên Telegram")
    if not telegram_img.send("👋 Bot ảnh của Nhi đang hoạt động.\n\n" + telegram_img.HELP):
        raise HTTPException(400, "Không gửi được tin, xem màn Lỗi")
    return {"ok": True}


@app.put("/api/tg-img/settings")
def tg_img_settings(data: dict):
    import telegram_img
    if "report" in data:
        db.set_setting("tg2_report", "1" if data["report"] in (1, "1", True, "true") else "0")
    return telegram_img.status()


@app.delete("/api/tg-img/token")
def tg_img_clear():
    import telegram_img
    telegram_img.clear()
    return telegram_img.status()

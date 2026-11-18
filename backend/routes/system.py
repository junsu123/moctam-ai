# ------------------------------------------------------------------ bắt đầu chạy thật
class ResetReq(BaseModel):
    confirm: str = ""
    products: bool = False
    groups: bool = False
    found_capital: int = 0  # > 0: thành lập công ty ngay sau khi xóa


@app.get("/api/coach")
def coach_info():
    import coach
    return coach.overview()


@app.post("/api/coach")
def coach_now():
    import coach
    return {**coach.run(force=True), **coach.overview()}


@app.get("/api/housekeeping")
def housekeeping_info():
    import housekeeping
    st = db.get_settings()
    try:
        last = json.loads(st.get("housekeeping_last") or "null")
    except Exception:
        last = None
    return {"sizes": housekeeping.sizes(), "last": last, "time": st.get("housekeeping_time") or "03:20",
            "on": st.get("housekeeping_on", "1") == "1", "shots_keep_days": int(st.get("shots_keep_days") or 30)}


@app.post("/api/housekeeping")
def housekeeping_now():
    import housekeeping
    r = housekeeping.run(force=True)
    if r.get("busy"):
        raise HTTPException(409, "Đang dọn dữ liệu, chờ chút rồi xem lại")
    return {"text": housekeeping.summary(r), **housekeeping_info()}


@app.get("/api/reset")
def reset_preview():
    return db.reset_preview()


@app.post("/api/reset")
def reset(r: ResetReq):
    if r.confirm.strip().upper() != "CHAY THAT":
        raise HTTPException(400, 'Gõ đúng "CHAY THAT" để xác nhận')
    busy = [s["name"] for s in db.q("SELECT id, name FROM sales") if browser_poster.busy(s["id"]) or browser_poster.queued(s["id"])]
    if busy or meeting.is_running():
        raise HTTPException(409, "Đang có " + (f"nick {', '.join(busy)} làm việc" if busy else "cuộc họp") + ". Chờ xong rồi thử lại.")
    res = db.reset_test_data(r.products, r.groups)
    if r.found_capital > 0:
        company.found(r.found_capital)
        res["founded"] = True
    for k in list(workflows.STATUS):
        workflows.STATUS[k] = {"state": "idle", "text": "Sẵn sàng làm việc thật"}
    return res


# ------------------------------------------------------------------ dữ liệu mẫu
@app.get("/api/sample-data")
def sample_data():
    return db.sample_counts()


@app.delete("/api/sample-data")
def delete_sample_data():
    done = db.clear_samples()
    if done:
        db.log("minh", "Dọn dữ liệu mẫu", ", ".join(f"{v} {k}" for k, v in done.items()))
    return {"deleted": done, "left": db.sample_counts()}


# ------------------------------------------------------------------ khóa API Claude
class AiKey(BaseModel):
    key: str


@app.post("/api/ai-key")
def save_ai_key(k: AiKey):
    """Kiểm tra khóa với Anthropic rồi mới lưu; hiệu lực ngay, không cần khởi động lại."""
    res = llm_mod.check_key(k.key)
    if not res["ok"]:
        raise HTTPException(400, res["error"])
    db.set_setting("anthropic_api_key", k.key.strip())
    llm.reload()
    db.log("minh", "Kết nối Claude", "Đã lưu khóa API, cả đội chuyển sang suy nghĩ bằng Claude")
    return {"ok": True, "warning": res.get("warning"), "masked": llm_mod.mask_key(k.key), "source": llm.source}


@app.post("/api/ai-key/test")
def test_ai_key():
    key, src = llm.current_key()
    if not key:
        raise HTTPException(400, "Chưa có khóa API")
    res = llm_mod.check_key(key)
    if not res["ok"]:
        raise HTTPException(400, res["error"])
    return {"ok": True, "warning": res.get("warning"), "source": src}


@app.delete("/api/ai-key")
def delete_ai_key():
    db.set_setting("anthropic_api_key", "")
    llm.reload()
    db.log("minh", "Ngắt Claude", "Đã xóa khóa API trong phần mềm")
    return {"ok": True, "live": llm.live, "source": llm.source}

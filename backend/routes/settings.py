# ------------------------------------------------------------------ việc & cài đặt
class TaskPatch(BaseModel):
    status: str


@app.get("/api/tasks")
def tasks():
    return db.q("SELECT * FROM tasks ORDER BY status='done', id DESC LIMIT 100")


@app.patch("/api/tasks/{tid}")
def patch_task(tid: int, t: TaskPatch):
    db.run("UPDATE tasks SET status=? WHERE id=?", (t.status, tid))
    return {"ok": True}


@app.post("/api/run/daily-work")
def run_daily():
    return workflows.daily_work()


@app.get("/api/costs")
def costs():
    """Chi phí AI thật (đo từ số token mỗi lần gọi) + dự báo cuối tháng."""
    import calendar
    from datetime import datetime
    now = db.clock()
    month = now.strftime("%Y-%m") + "%"
    spent = llm_mod.month_spent()
    days_in = calendar.monthrange(now.year, now.month)[1]
    by_task = db.q("""SELECT task, COUNT(*) calls, SUM(input_tokens) tin, SUM(output_tokens) tout, SUM(cost_usd) cost,
                      SUM(batch) batched FROM usage WHERE created_at LIKE ? GROUP BY task ORDER BY cost DESC""", (month,))
    for r in by_task:
        r["label"] = llm_mod.TASKS.get(r["task"], r["task"])
    by_model = db.q("SELECT model, COUNT(*) calls, SUM(cost_usd) cost FROM usage WHERE created_at LIKE ? GROUP BY model", (month,))
    last = db.q("""SELECT substr(created_at,1,10) day, SUM(cost_usd) cost FROM usage
                   GROUP BY day ORDER BY day DESC LIMIT 14""")[::-1]
    saved = db.one("""SELECT COALESCE(SUM(cost_usd),0) c FROM usage WHERE batch=1 AND created_at LIKE ?""", (month,))["c"]
    s = db.get_settings()
    return {"spent": round(spent, 4), "budget": float(s.get("monthly_budget_usd") or 0),
            "projected": round(spent / max(now.day, 1) * days_in, 3), "state": llm_mod.budget_state(),
            "batch_saved": round(saved, 4), "by_task": by_task, "by_model": by_model, "daily": last,
            "prices": llm_mod.PRICES, "presets": llm_mod.PRESETS, "live": llm.live,
            "pending_batches": db.one("SELECT COUNT(*) n FROM ai_batches WHERE status='in_progress'")["n"],
            "fallback": llm_mod.fallback_stats(30)}


class Preset(BaseModel):
    name: str


@app.post("/api/costs/preset")
def apply_preset(p: Preset):
    if p.name not in llm_mod.PRESETS:
        raise HTTPException(400, "Gói không tồn tại")
    for k, v in llm_mod.PRESETS[p.name].items():
        db.set_setting(k, v)
    db.set_setting("cost_preset", p.name)
    return settings()


@app.get("/api/settings")
def settings():
    s = db.get_settings()
    s["fb_page_token"] = "••••••" if s.get("fb_page_token") else ""
    s["tg_token"] = "••••••" if s.get("tg_token") else ""
    for k in ("tg2_token", "cf_api_token", "pixabay_key", "seo_google_sa", "seo_psi_key", "site_ftp_pass", "site_sync_token"):  # khóa bí mật: không trả về giao diện
        s[k] = "••••••" if s.get(k) else ""
    key, src = llm.current_key()
    s["anthropic_api_key"] = ""
    s["ai_key_masked"] = llm_mod.mask_key(key)
    s["ai_key_source"] = src
    s.pop("tg_chat_ids", None)
    s["ai_live"] = llm.live
    s["model"] = MODEL
    s["models"] = list(llm_mod.PRICES)
    return s


@app.put("/api/settings")
def put_settings(data: dict):
    for k, v in data.items():
        if k in ("fb_page_token", "tg_token", "tg2_token", "cf_api_token", "pixabay_key", "seo_google_sa", "seo_psi_key", "site_ftp_pass",
                 "site_sync_token") and v == "••••••":
            continue
        if k == "anthropic_api_key":
            continue  # chỉ lưu qua /api/ai-key sau khi kiểm tra
        if k == "tg_token":  # token bot: kiểm tra với Telegram trước khi lưu
            if str(v).strip():
                try:
                    telegram_bot.save_token(str(v))
                except ValueError as e:
                    raise HTTPException(400, str(e))
            continue
        if k == "app_tz":
            if v and v not in db.TZ_CHOICES:
                raise HTTPException(400, "Múi giờ không hợp lệ")
            db.set_tz(v or db.DEFAULT_TZ)
        if k in db.DEFAULT_SETTINGS and k not in ("tg_chat_ids", "tg_pair_code", "tg_sent_log"):
            db.set_setting(k, str(v))
    return settings()

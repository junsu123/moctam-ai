# ------------------------------------------------------------------ luật Facebook
FBP_KEYS = {"fbp_enabled", "fbp_posts_day", "fbp_gap_minutes", "fbp_bumps_day", "fbp_joins_day", "fbp_friends_day", "fbp_same_group_hours",
            "fbp_new_nick_days", "fbp_new_nick_factor", "fbp_rest_days", "fbp_after_days", "fbp_after_factor", "fbp_hashtags_max",
            "fbp_similar_max", "fbp_removed_max", "fbp_group_rest_days", "fbp_watch_enabled", "fbp_watch_time", "fbp_auto_tighten"}


@app.get("/api/fb-policy")
def fb_policy_get():
    import fb_policy
    return fb_policy.overview()


@app.put("/api/fb-policy/settings")
def fb_policy_settings(data: dict):
    import fb_policy
    bad = [k for k in data if k not in FBP_KEYS]
    if bad:
        raise HTTPException(400, "Không sửa được: " + ", ".join(bad))
    for k, v in data.items():
        db.set_setting(k, str(v))
    db.log("tuan", "Sếp chỉnh giới hạn an toàn", ", ".join(f"{k.replace('fbp_', '')}={v}" for k, v in data.items())[:300])
    return fb_policy.overview()


class PolicyText(BaseModel):
    text: str


@app.post("/api/fb-policy/check")
def fb_policy_check(p: PolicyText):
    import fb_policy
    iss = fb_policy.check_text(p.text)
    return {"issues": iss, "ok": not fb_policy.blocking(iss)}


class PolicyRule(BaseModel):
    title: str
    text: str = ""
    phrases: list[str] = []
    level: str = "high"
    cat: str = "content"


@app.post("/api/fb-policy/rules")
def fb_policy_add_rule(r: PolicyRule):
    import fb_policy
    if not r.title.strip():
        raise HTTPException(400, "Ghi tên luật")
    rules = fb_policy.custom_rules()
    rules.append({"id": f"c{int(time.time())}", "title": r.title.strip()[:120], "text": r.text.strip()[:500],
                  "phrases": [x.strip() for x in r.phrases if x.strip()][:20], "level": "high" if r.level == "high" else "medium",
                  "cat": r.cat if r.cat in fb_policy.CATS else "content"})
    db.set_setting("fbp_custom_rules", json.dumps(rules, ensure_ascii=False))
    fb_policy.teach()
    db.log("tuan", "Sếp thêm luật Facebook", r.title.strip()[:200])
    return fb_policy.overview()


@app.delete("/api/fb-policy/rules/{rid}")
def fb_policy_del_rule(rid: str):
    import fb_policy
    rules = [x for x in fb_policy.custom_rules() if x.get("id") != rid]
    db.set_setting("fbp_custom_rules", json.dumps(rules, ensure_ascii=False))
    return fb_policy.overview()


@app.post("/api/fb-policy/watch")
def fb_policy_watch():
    import fb_policy
    threading.Thread(target=fb_policy.check_sources, daemon=True).start()
    return {"started": True}


@app.post("/api/fb-policy/changes/{cid}/read")
def fb_policy_change_read(cid: int):
    import fb_policy
    db.run("UPDATE fb_policy_changes SET status='read' WHERE id=?", (cid,))
    return fb_policy.overview()


@app.post("/api/fb-policy/nicks/{aid}/lift")
def fb_policy_lift(aid: int):
    """Sếp cho nick hết nghỉ sớm (vẫn chạy nửa giới hạn tới hết hạn)."""
    import fb_policy
    db.run("UPDATE fb_accounts SET rest_until=NULL WHERE id=?", (aid,))
    db.log("tuan", "Sếp cho nick làm lại sớm", f"Nick #{aid}: bỏ thời gian nghỉ, vẫn chạy nửa giới hạn tới hết hạn")
    return fb_policy.overview()


@app.post("/api/fb-policy/teach")
def fb_policy_teach():
    import fb_policy
    return {"taught": fb_policy.teach()}

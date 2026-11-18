# ------------------------------------------------------------------ Bảo trả lời khách hỏi mua trong nhóm (sếp duyệt, nick gửi)
REPLY_KEYS = {"replies_enabled", "replies_time", "replies_per_nick_day", "replies_groups_per_run", "replies_per_group", "reply_contact"}


@app.get("/api/replies")
def replies_get(status: str = ""):
    import replies
    return replies.overview(status)


class ReplyScan(BaseModel):
    account_id: int | None = None
    group_ids: list[int] | None = None


@app.post("/api/replies/scan")
def replies_scan(p: ReplyScan):
    import replies
    try:
        return replies.start(p.account_id, p.group_ids)
    except ValueError as e:
        raise HTTPException(400, str(e))


class ReplyAct(BaseModel):
    action: str  # approve | skip | junk | edit | retry
    reply: str | None = None


@app.put("/api/replies/{rid}")
def replies_act(rid: int, p: ReplyAct):
    import replies
    try:
        if p.action == "approve":
            return replies.approve(rid, p.reply)
        if p.action in ("skip", "junk"):
            return replies.skip(rid, p.action == "junk")
        if p.action == "retry":
            return replies.retry(rid)
        if p.action == "edit":
            if not (p.reply or "").strip():
                raise ValueError("Câu trả lời đang trống")
            db.run("UPDATE reply_tasks SET reply=? WHERE id=? AND status IN ('draft','failed')", (p.reply.strip()[:600], rid))
            return {"id": rid}
        raise ValueError("Thao tác không hợp lệ")
    except KeyError:
        raise HTTPException(404, "Không tìm thấy câu trả lời")
    except ValueError as e:
        raise HTTPException(400, str(e))


@app.post("/api/replies/approve-all")
def replies_approve_all():
    import replies
    n, later = 0, 0
    for r in db.q("SELECT id FROM reply_tasks WHERE status='draft' AND COALESCE(reply,'')<>'' ORDER BY id"):
        try:
            x = replies.approve(r["id"])
            n += 1
            later += 1 if x.get("later") else 0
        except ValueError:
            pass
    return {"approved": n, "later": later}


FEED_KEYS = {"feed_enabled", "feed_min_posts", "feed_scans_day", "feed_min_score", "feed_buyer_image", "feed_seller_enabled",
             "feed_seller_per_nick_day", "feed_seller_words", "feed_comment_all", "feed_general_style", "feed_per_group_day", "reply_gap_min"}


@app.get("/api/feed")
def feed_get():
    import group_feed
    return group_feed.overview()


@app.post("/api/feed/run")
def feed_run(p: ReplyScan):
    import group_feed
    try:
        return group_feed.start(p.account_id)
    except ValueError as e:
        raise HTTPException(400, str(e))


@app.put("/api/feed-settings")
def feed_settings(data: dict):
    import group_feed
    bad = [k for k in data if k not in FEED_KEYS]
    if bad:
        raise HTTPException(400, "Không sửa được: " + ", ".join(bad))
    lim = {"feed_min_posts": (10, 60, "Mỗi lượt đọc 10–60 bài"), "feed_scans_day": (1, 4, "Mỗi nick lướt 1–4 lượt/ngày"),
           "feed_min_score": (40, 95, "Điểm tối thiểu 40–95"),
           "feed_seller_per_nick_day": (0, 3, "Chào người bán tối đa 3 câu/nick/ngày để không bị báo cáo spam"),
           "feed_per_group_day": (1, 3, "Mỗi nhóm 1–3 bình luận/ngày để nhóm không coi là spam"),
           "reply_gap_min": (30, 240, "Giãn cách 30–240 phút giữa 2 bình luận của một nick")}
    for k, v in data.items():
        v = str(v).strip()
        if k in lim:
            lo, hi, msg = lim[k]
            if not v.isdigit() or not lo <= int(v) <= hi:
                raise HTTPException(400, msg)
        elif k in ("feed_enabled", "feed_buyer_image", "feed_seller_enabled", "feed_comment_all") and v not in ("0", "1"):
            raise HTTPException(400, "Giá trị 0 hoặc 1")
        elif k == "feed_general_style" and v not in ("invite", "natural"):
            raise HTTPException(400, "Kiểu bình luận: invite hoặc natural")
        db.set_setting(k, v[:300])
    db.log("bao", "Sếp chỉnh lướt bảng tin nhóm", ", ".join(f"{k}={v}" for k, v in data.items())[:300])
    return group_feed.overview()


@app.post("/api/replies/relearn")
def replies_relearn():
    import post_care
    return post_care.relearn("reply")


@app.put("/api/replies-settings")
def replies_settings(data: dict):
    import replies
    bad = [k for k in data if k not in REPLY_KEYS]
    if bad:
        raise HTTPException(400, "Không sửa được: " + ", ".join(bad))
    for k, v in data.items():
        v = str(v).strip()
        if k == "replies_time" and not re.fullmatch(r"\d{1,2}:\d{2}", v):
            raise HTTPException(400, "Giờ có dạng HH:MM")
        if k == "replies_per_nick_day" and (not v.isdigit() or int(v) > 10):
            raise HTTPException(400, "Mỗi nick tối đa 10 câu/ngày để không bị coi là spam")
        if k in ("replies_groups_per_run", "replies_per_group") and not re.fullmatch(r"\d{1,2}", v):
            raise HTTPException(400, "Giá trị phải là số")
        if k == "replies_enabled" and v not in ("0", "1"):
            raise HTTPException(400, "Giá trị 0 hoặc 1")
        db.set_setting(k, v.zfill(5) if k == "replies_time" else v[:120])
    db.log("bao", "Sếp chỉnh trả lời khách", ", ".join(f"{k}={v}" for k, v in data.items())[:300])
    return replies.overview()

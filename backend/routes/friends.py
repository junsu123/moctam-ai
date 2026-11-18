# ------------------------------------------------------------------ gợi ý kết bạn trong nhóm
FRIEND_KEYS = {"friends_enabled", "friends_time", "friends_groups_per_run", "friends_per_group", "fbp_friends_day"}


@app.get("/api/friends")
def friends_get(account_id: int | None = None, status: str = ""):
    import friends
    return friends.overview(account_id, status)


@app.get("/api/friends/groups")
def friends_groups(account_id: int | None = None):
    import friends
    return friends.active_groups(account_id, 50)


class FriendScan(BaseModel):
    account_id: int | None = None
    group_ids: list[int] | None = None


@app.post("/api/friends/scan")
def friends_scan(p: FriendScan):
    import friends
    try:
        return friends.start(p.account_id, p.group_ids)
    except ValueError as e:
        raise HTTPException(400, str(e))


class FriendOpen(BaseModel):
    account_id: int
    n: int = 5
    ids: list[int] | None = None


@app.post("/api/friends/open")
def friends_open(p: FriendOpen):
    import friends
    try:
        return friends.open_next(p.account_id, p.n, p.ids)
    except KeyError:
        raise HTTPException(404, "Không tìm thấy nick")
    except ValueError as e:
        raise HTTPException(400, str(e))


class FriendMark(BaseModel):
    status: str
    reason: str = "other"
    note: str = ""


@app.put("/api/friends/{fid}")
def friends_mark(fid: int, p: FriendMark):
    import friends
    try:
        if p.status == "junk":
            return friends.junk_it(fid, p.reason, p.note)
        return friends.mark(fid, p.status)
    except KeyError:
        raise HTTPException(404, "Không tìm thấy gợi ý")
    except ValueError as e:
        raise HTTPException(400, str(e))


@app.put("/api/friends-settings")
def friends_settings(data: dict):
    import friends
    bad = [k for k in data if k not in FRIEND_KEYS]
    if bad:
        raise HTTPException(400, "Không sửa được: " + ", ".join(bad))
    for k, v in data.items():
        v = str(v).strip()
        if k == "friends_time" and not re.fullmatch(r"\d{1,2}:\d{2}", v):
            raise HTTPException(400, "Giờ có dạng HH:MM")
        if k != "friends_time" and not re.fullmatch(r"\d{1,3}", v):
            raise HTTPException(400, "Giá trị phải là số")
        db.set_setting(k, v.zfill(5) if k == "friends_time" else v)
    db.log("tuan", "Sếp chỉnh gợi ý kết bạn", ", ".join(f"{k}={v}" for k, v in data.items())[:300])
    return friends.overview()

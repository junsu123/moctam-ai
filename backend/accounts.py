"""Nick Facebook của nhân viên sale.

Mỗi nhân viên sale (một agent) giữ 3–5 nick Facebook. Mỗi nick có hồ sơ Chrome riêng (phiên đăng nhập riêng), giới hạn
an toàn riêng (số bài/ngày, giãn cách, khung giờ) và danh sách nhóm đã vào riêng. Sale làm việc theo ca: mở Chrome của
một nick, làm hết việc đến hạn của nick đó (đăng bài, up bài, quét bình luận), đóng lại rồi chuyển sang nick kế tiếp.

Bảng sales vẫn giữ trạng thái tổng hợp (login_status = 'ok' nếu có ít nhất một nick chạy được, fb_name = danh sách nick)
để KPI, công ty, CEO dùng như trước.
"""
import db

MAX_PER_SALE = 5
RECOMMENDED = 3


def get(aid: int) -> dict | None:
    return db.one("SELECT * FROM fb_accounts WHERE id=?", (aid,))


def of_sale(sale_id: int) -> list[dict]:
    return db.q("SELECT * FROM fb_accounts WHERE sale_id=? ORDER BY position, id", (sale_id,))


def first(sale_id: int) -> dict | None:
    rows = of_sale(sale_id)
    ok = [a for a in rows if a["login_status"] == "ok" and a["enabled"]]
    return (ok or rows or [None])[0]


def working(sale_id: int | None = None) -> list[dict]:
    """Nick làm việc được: nick bật, đã đăng nhập; sale chưa nghỉ việc và không bị tạm dừng."""
    sql = """SELECT a.*, s.name sale_name FROM fb_accounts a JOIN sales s ON s.id=a.sale_id
             WHERE a.enabled=1 AND a.login_status='ok' AND s.auto_post=1 AND COALESCE(s.status,'active')='active'"""
    if sale_id is not None:
        return db.q(sql + " AND a.sale_id=? ORDER BY a.position, a.id", (sale_id,))
    return db.q(sql + " ORDER BY a.sale_id, a.position, a.id")


def profile_path(aid: int):
    a = get(aid)
    if a and a.get("profile_dir"):
        from pathlib import Path
        p = Path(a["profile_dir"])
    else:
        p = db.PROFILES_DIR / f"acc-{aid}"
    p.mkdir(parents=True, exist_ok=True)
    return p


def create(sale_id: int, name: str = "", copy_limits_from: dict | None = None) -> dict:
    n = len(of_sale(sale_id))
    if n >= MAX_PER_SALE:
        raise ValueError(f"Mỗi nhân viên sale giữ tối đa {MAX_PER_SALE} nick")
    lim = copy_limits_from or {}
    aid = db.run("""INSERT INTO fb_accounts(sale_id, name, position, max_posts_per_day, min_gap_minutes, active_from, active_to,
                    created_at) VALUES (?,?,?,?,?,?,?,?)""",
                 (sale_id, (name or "").strip() or f"Nick {n + 1}", n, int(lim.get("max_posts_per_day") or 3),
                  int(lim.get("min_gap_minutes") or 45), lim.get("active_from") or "08:00", lim.get("active_to") or "22:00",
                  db.now()))
    db.run("UPDATE fb_accounts SET profile_dir=? WHERE id=?", (str(db.PROFILES_DIR / f"acc-{aid}"), aid))
    sync_sale(sale_id)
    return get(aid)


def set_login(aid: int, status: str, err: str = ""):
    db.run("UPDATE fb_accounts SET login_status=?, last_check_at=?, last_error=? WHERE id=?", (status, db.now(), err, aid))
    a = get(aid)
    if a:
        sync_sale(a["sale_id"])


def sync_sale(sale_id: int):
    """Cập nhật trạng thái tổng hợp của nhân viên sale từ các nick."""
    rows = of_sale(sale_id)
    if not rows:
        db.run("UPDATE sales SET login_status='not_logged_in', fb_name='' WHERE id=?", (sale_id,))
        return
    on = [a for a in rows if a["enabled"]]
    st = "ok" if any(a["login_status"] == "ok" for a in on) else \
        "checkpoint" if any(a["login_status"] == "checkpoint" for a in rows) else "not_logged_in"
    err = next((a["last_error"] for a in rows if a["login_status"] != "ok" and a["last_error"]), None)
    db.run("UPDATE sales SET login_status=?, fb_name=?, last_error=? WHERE id=?",
           (st, ", ".join(a["name"] for a in rows), err if st != "ok" else None, sale_id))


def label(a: dict) -> str:
    return a.get("name") or f"Nick #{a['id']}"


def migrate():
    """Bản cũ: mỗi sale giữ 1 nick trong hồ sơ data/profiles/sale-<id>. Chuyển thành nick đầu tiên của sale,
    giữ nguyên hồ sơ Chrome (không phải đăng nhập lại), chuyển luôn bài, lượt up, nhóm đã vào."""
    if db.get_settings().get("accounts_migrated") == "1":
        return
    for s in db.q("SELECT * FROM sales ORDER BY id"):
        if db.one("SELECT id FROM fb_accounts WHERE sale_id=?", (s["id"],)):
            continue
        prof = s.get("profile_dir") or str(db.PROFILES_DIR / f"sale-{s['id']}")
        aid = db.run("""INSERT INTO fb_accounts(sale_id, name, profile_dir, login_status, enabled, position, max_posts_per_day,
                        min_gap_minutes, active_from, active_to, last_check_at, last_error, last_post_at, created_at)
                        VALUES (?,?,?,?,1,0,?,?,?,?,?,?,?,?)""",
                     (s["id"], s.get("fb_name") or s["name"], prof, s.get("login_status") or "not_logged_in",
                      s.get("max_posts_per_day") or 5, s.get("min_gap_minutes") or 40, s.get("active_from") or "08:00",
                      s.get("active_to") or "22:00", s.get("last_check_at"), s.get("last_error"), s.get("last_post_at"),
                      s.get("created_at") or db.now()))
        db.run("UPDATE posts SET account_id=? WHERE sale_id=? AND account_id IS NULL", (aid, s["id"]))
        db.run("UPDATE bumps SET account_id=? WHERE sale_id=? AND account_id IS NULL", (aid, s["id"]))
        db.run("UPDATE comment_seen SET account_id=? WHERE sale_id=? AND account_id IS NULL", (aid, s["id"]))
        try:
            for j in db.q("SELECT * FROM group_joins WHERE sale_id=?", (s["id"],)):
                db.run("""INSERT OR IGNORE INTO account_groups(group_id, account_id, status, note, requested_at, updated_at)
                          VALUES (?,?,?,?,?,?)""", (j["group_id"], aid, j["status"], j.get("note"), j.get("requested_at"),
                                                    j.get("updated_at")))
        except Exception:
            pass
    first_acc = {r["sale_id"]: r["id"] for r in db.q("SELECT sale_id, MIN(id) id FROM fb_accounts GROUP BY sale_id")}
    for g in db.q("SELECT id, member_sale_ids FROM groups WHERE COALESCE(member_sale_ids,'')!=''"):
        ids = [first_acc[int(x)] for x in g["member_sale_ids"].split(",") if x.strip().isdigit() and int(x) in first_acc]
        db.run("UPDATE groups SET member_account_ids=? WHERE id=?", (",".join(map(str, ids)), g["id"]))
    db.set_setting("accounts_migrated", "1")


def member_ids(g: dict) -> set[int]:
    return {int(x) for x in (g.get("member_account_ids") or "").split(",") if x.strip().isdigit()}


def can_post_in(g: dict, aid: int) -> bool:
    """Nick có được đăng vào nhóm này không.
    - Nick đã đọc danh sách nhóm thật (Tuấn rà soát): chỉ nhóm nick đang ở, trừ nhóm mới vào còn đang nghỉ và nhóm Tuấn cho thoát.
    - Chưa rà soát: nhóm sếp nhập chưa đánh dấu nick nào coi như mọi nick đã vào; nhóm sale tự tìm chỉ nick đã vào."""
    import my_groups
    st = my_groups.membership(g, aid)
    if st != "unknown":
        return st == "ok"
    mem = member_ids(g)
    return aid in mem if (mem or g.get("source") == "search") else True


def diagnose(aid: int) -> dict:
    """Vì sao nick có / không có việc hôm nay: số việc trong ngày và các lý do chặn (đọc từ dữ liệu, không mở Chrome)."""
    import my_groups
    a = db.one("""SELECT a.*, s.name sale_name, s.auto_post, COALESCE(s.status,'active') sale_status FROM fb_accounts a
                  JOIN sales s ON s.id=a.sale_id WHERE a.id=?""", (aid,))
    if not a:
        return {}
    t = db.today()
    work = {
        "posted": db.one("SELECT COUNT(*) n FROM posts WHERE account_id=? AND status='posted' AND posted_at LIKE ?", (aid, t + "%"))["n"],
        "scheduled": db.one("""SELECT COUNT(*) n FROM posts WHERE account_id=? AND status IN ('scheduled','posting')
                               AND scheduled_for LIKE ?""", (aid, t + "%"))["n"],
        "bumps": db.one("SELECT COUNT(*) n FROM bumps WHERE account_id=? AND created_at LIKE ? AND status!='skipped'", (aid, t + "%"))["n"],
        "posts_7d": db.one("SELECT COUNT(*) n FROM posts WHERE account_id=? AND status='posted' AND posted_at >= ?",
                           (aid, (db.clock() - __import__("datetime").timedelta(days=7)).strftime("%Y-%m-%d")))["n"],
    }
    groups = db.q("SELECT * FROM groups WHERE COALESCE(url,'')!='' AND COALESCE(managed,0)=0 AND COALESCE(is_sample,0)=0")
    st = {"ok": 0, "rest": 0, "no": 0, "leave": 0, "unknown": 0}
    for g in groups:
        m = my_groups.membership(g, aid)
        st[m] = st.get(m, 0) + 1
    can = sum(1 for g in groups if can_post_in(g, aid))
    why = []  # (mức, lý do, cách xử lý)
    if not a["enabled"]:
        why.append(("bad", "Nick đang tắt", "Bật nick ở thẻ nick"))
    if a["login_status"] != "ok":
        why.append(("bad", "Nick chưa đăng nhập hoặc phiên đã hết", "Bấm Mở Chrome, đăng nhập lại rồi bấm Kiểm tra"))
    if not a["auto_post"] or a["sale_status"] != "active":
        why.append(("bad", "Sale đang tạm dừng hoặc đã nghỉ", "Bật lại sale ở trang Nhân viên sale"))
    if (a.get("rest_until") or "") > db.now():
        why.append(("warn", f"Nick đang nghỉ theo Luật Facebook tới {a['rest_until'][:16]}", "Chờ hết giờ nghỉ hoặc gỡ nghỉ ở trang Luật Facebook"))
    if not a.get("groups_synced_at") and not can:
        why.append(("bad", "Chưa biết nick đang ở nhóm nào", "Hội nhóm → Rà soát nhóm của nick"))
    elif not can:
        why.append(("bad", f"Nick không ở nhóm nào trong danh sách đăng ({st['no']} nhóm nick chưa vào"
                    + (f", {st['rest']} nhóm mới vào đang chờ đủ ngày" if st["rest"] else "") + ")",
                    "Cho nick xin vào nhóm (Hội nhóm → Tìm nhóm) hoặc Rà soát nhóm của nick để thêm nhóm nick đang ở"))
    elif can <= 2:
        why.append(("warn", f"Nick chỉ đăng được {can} nhóm, nhóm vừa đăng phải giãn cách vài ngày nên nhiều hôm không có lượt",
                    "Cho nick vào thêm nhóm"))
    now_hm = db.clock().strftime("%H:%M")
    if now_hm > (a.get("active_to") or "22:00"):
        why.append(("info", f"Đã hết giờ làm của nick ({a.get('active_from') or '08:00'}–{a.get('active_to') or '22:00'})", "Mai nick làm tiếp"))
    try:
        import fb_policy
        lim = fb_policy.limits(a) if fb_policy.enabled() else None
        if lim and work["posted"] + work["scheduled"] >= min(lim["posts"], int(a.get("max_posts_per_day") or 5)):
            why.append(("info", "Nick đã đủ số bài hôm nay", "Mai nick làm tiếp"))
        elif lim and lim["factor"] < 1:
            why.append(("info", f"Nick mới hoặc vừa bị chặn: trần {lim['posts']} bài/ngày", "Tự tăng dần khi nick ổn định"))
    except Exception:
        pass
    if not why and not (work["posted"] + work["scheduled"] + work["bumps"]):
        why.append(("info", "Chưa có bài đã duyệt để xếp cho nick", "Lan viết thêm bài hoặc sếp duyệt bài ở trang Bài đăng"))
    return {"id": aid, "name": label(a), "work": work, "groups_can": can, "groups": st, "why":
            [{"level": l, "text": x, "fix": f} for l, x, f in why], "idle": not (work["posted"] + work["scheduled"] + work["bumps"])}

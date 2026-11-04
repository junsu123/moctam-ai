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
    """Nick có được đăng vào nhóm này không. Nhóm sếp nhập chưa đánh dấu nick nào: coi như mọi nick đã vào;
    nhóm sale tự tìm: chỉ nick đã vào."""
    mem = member_ids(g)
    return aid in mem if (mem or g.get("source") == "search") else True

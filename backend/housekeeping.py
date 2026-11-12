"""Dọn dẹp dữ liệu hằng đêm để phần mềm không phình to theo thời gian:
xóa nhật ký cũ (giữ dữ liệu mà agent dùng để học, tính tiền, chống trùng), ảnh chụp màn hình cũ, bản sao lưu thừa,
bộ nhớ đệm Chrome của các nick; nén lại cơ sở dữ liệu khi có nhiều chỗ trống."""
import json
import shutil
import threading
import time
from datetime import timedelta
from pathlib import Path

import db

# (bảng, điều kiện, cột ngày, số ngày giữ). Không đụng: bài đăng, khách, đơn, chi phí AI, kho bài, sổ kiến thức, bài học,
# data rác, ảnh đã dùng (chống trùng ảnh), bình luận đã gửi / lời mời đã gửi (một người chỉ một nick).
RULES = [
    ("activity", "", "created_at", 60),                      # nhật ký hoạt động
    ("comment_seen", "", "created_at", 120),                 # bình luận đã quét (chỉ quét bài 7 ngày)
    ("feed_scans", "", "created_at", 90),                    # lượt lướt bảng tin
    ("group_searches", "", "searched_at", 180),              # lượt tìm nhóm
    ("ceo_messages", "", "created_at", 180),                 # tin nhắn sếp ↔ CEO (CEO chỉ đọc 3 ngày gần nhất)
    ("meeting_messages", "", "created_at", 180),             # lời thoại trong họp (giữ biên bản, kết luận)
    ("knowledge_log", "", "created_at", 180),
    ("ai_fallback", "", "created_at", 90),
    ("bumps", "status!='scheduled'", "COALESCE(done_at, created_at)", 180),  # lượt up bài (bài vẫn giữ số lần up)
    ("reply_tasks", "status IN ('draft','skipped','failed','lost')", "created_at", 90),  # câu chưa gửi, sếp bỏ qua
    ("friend_suggestions", "status IN ('suggested','skipped')", "created_at", 90),       # người gợi ý chưa mời
]
CACHE_DIRS = ("Cache", "Code Cache", "GPUCache", "DawnCache", "GrShaderCache", "Service Worker/CacheStorage",
              "Service Worker/ScriptCache")
_run = threading.Lock()


def _s(key, default):
    try:
        return int(db.get_settings().get(key) or default)
    except ValueError:
        return default


def _size(p: Path) -> int:
    if p.is_file():
        return p.stat().st_size
    n = 0
    for f in p.rglob("*") if p.exists() else []:
        try:
            if f.is_file():
                n += f.stat().st_size
        except OSError:
            pass
    return n


def _mb(n: int) -> float:
    return round(n / 1048576, 1)


def _idle() -> bool:
    try:
        import browser_poster as B
        return not B._busy and not any(q.qsize() for q in B._queues.values())
    except Exception:
        return True


def _cols(table: str) -> set:
    return {r["name"] for r in db.q(f"PRAGMA table_info({table})")}


def purge_rows() -> dict:
    """Xóa từng phần 5.000 dòng để không giữ khóa lâu (sale vẫn ghi được trong lúc dọn)."""
    out = {}
    scale = max(1, _s("keep_log_scale", 1))  # sếp muốn giữ lâu hơn: đặt 2, 3 (giữ gấp đôi, gấp ba)
    for table, cond, col, days in RULES:
        try:
            if col.split("(")[-1].split(",")[0].strip() not in _cols(table):
                continue
            cut = (db.clock() - timedelta(days=days * scale)).strftime("%Y-%m-%d %H:%M:%S")
            where = f"{col} < ?" + (f" AND {cond}" if cond else "")
            n = 0
            while True:
                with db._lock:
                    cur = db.conn().execute(f"DELETE FROM {table} WHERE rowid IN (SELECT rowid FROM {table} WHERE {where} LIMIT 5000)", (cut,))
                    db.conn().commit()
                n += cur.rowcount
                if cur.rowcount < 5000:
                    break
                time.sleep(0.05)
            if n:
                out[table] = n
        except Exception as e:
            print("[dọn]", table, e)
    return out


def purge_shots() -> dict:
    """Ảnh chụp màn hình cũ hơn N ngày (mặc định 30). Giữ ảnh của lỗi chưa xử lý."""
    days = _s("shots_keep_days", 30)
    cut = time.time() - days * 86400
    keep = {Path(r["screenshot"]).name for r in db.q("SELECT screenshot FROM errors WHERE status!='resolved' AND screenshot IS NOT NULL")}
    gone, freed = set(), 0
    for f in db.SHOTS_DIR.glob("*.png"):
        try:
            if f.stat().st_mtime < cut and f.name not in keep:
                freed += f.stat().st_size
                f.unlink()
                gone.add(f.name)
        except OSError:
            pass
    if gone:  # bỏ đường dẫn ảnh đã xóa để giao diện không hiện ảnh hỏng
        for table, col in (("posts", "screenshot"), ("bumps", "screenshot"), ("reply_tasks", "shot")):
            if col in _cols(table):
                ids = [(r["id"],) for r in db.q(f"SELECT id, {col} v FROM {table} WHERE {col} IS NOT NULL AND {col}!=''")
                       if Path(str(r["v"]).split("?")[0]).name in gone]
                db.many(f"UPDATE {table} SET {col}=NULL WHERE id=?", ids)
    return {"files": len(gone), "mb": _mb(freed)}


def purge_backups() -> dict:
    keep = _s("backups_keep", 5)
    d = db.DATA_DIR / "backups"
    files = sorted(d.glob("*.db"), key=lambda f: f.stat().st_mtime, reverse=True) if d.exists() else []
    freed = 0
    for f in files[keep:]:
        freed += f.stat().st_size
        f.unlink(missing_ok=True)
    return {"files": max(0, len(files) - keep), "mb": _mb(freed)}


def purge_chrome_cache() -> dict:
    """Bộ nhớ đệm Chrome của từng nick (Chrome tự tải lại). Giữ nguyên phiên đăng nhập, cookie. Chỉ dọn nick không mở Chrome."""
    import browser_poster as B
    min_mb = _s("chrome_cache_min_mb", 150)
    freed, n = 0, 0
    for acc in db.q("SELECT id FROM fb_accounts"):
        try:
            if B.profile_in_use(acc["id"]):
                continue
            base = B.profile_dir(acc["id"])
            dirs = [prof / c for prof in [base, *base.glob("Default"), *base.glob("Profile *")] for c in CACHE_DIRS]
            dirs = [d for d in dirs if d.is_dir()]
            size = sum(_size(d) for d in dirs)
            if size < min_mb * 1048576:
                continue
            for d in dirs:
                shutil.rmtree(d, ignore_errors=True)
            freed += size
            n += 1
        except Exception as e:
            print("[dọn] chrome", acc["id"], e)
    return {"nicks": n, "mb": _mb(freed)}


def compact(force=False) -> dict:
    """Nén lại file dữ liệu khi chỗ trống (sau khi xóa) chiếm từ 25%; luôn cập nhật thống kê chỉ mục."""
    out = {}
    with db._lock:
        c = db.conn()
        pages = c.execute("PRAGMA page_count").fetchone()[0]
        free = c.execute("PRAGMA freelist_count").fetchone()[0]
        before = db.DB_PATH.stat().st_size if db.DB_PATH.exists() else 0
        if pages and ((force and free) or (free / pages >= 0.25 and free * 4096 > 5 * 1048576)):
            c.commit()
            c.execute("VACUUM")
            out["vacuum_mb"] = _mb(max(0, before - db.DB_PATH.stat().st_size))
        c.execute("PRAGMA optimize")
        c.execute("PRAGMA wal_checkpoint(TRUNCATE)")
    return out


def sizes() -> dict:
    wal = Path(str(db.DB_PATH) + "-wal")
    big = db.q("SELECT name, SUM(pgsize) b FROM dbstat GROUP BY name ORDER BY b DESC LIMIT 6") if _has_dbstat() else []
    return {"db_mb": _mb(_size(db.DB_PATH) + (_size(wal) if wal.exists() else 0)),
            "shots_mb": _mb(_size(db.SHOTS_DIR)), "shots": len(list(db.SHOTS_DIR.glob("*.png"))),
            "backups_mb": _mb(_size(db.DATA_DIR / "backups")), "profiles_mb": _mb(_size(db.PROFILES_DIR)),
            "tables": [{"name": r["name"], "mb": _mb(r["b"])} for r in big if not r["name"].startswith("sqlite_")][:5]}


def _has_dbstat() -> bool:
    try:
        db.q("SELECT 1 FROM dbstat LIMIT 1")
        return True
    except Exception:
        return False


def run(force=False) -> dict:
    """Một lượt dọn. force: sếp bấm, nén lại cả khi ít chỗ trống. Chrome và nén lại chỉ làm khi sale rảnh."""
    if not _run.acquire(blocking=False):
        return {"busy": True}
    try:
        t0 = time.time()
        before = sizes()
        res = {"rows": purge_rows(), "shots": purge_shots(), "backups": purge_backups()}
        if _idle():
            res["chrome"] = purge_chrome_cache()
            res["compact"] = compact(force)
        else:
            res["later"] = "Sale đang làm việc nên chưa nén lại và chưa dọn bộ nhớ Chrome, đêm sau làm tiếp"
        after = sizes()
        res.update(at=db.now(), secs=round(time.time() - t0, 1), before=before, after=after)
        db.set_setting("housekeeping_last", json.dumps(res, ensure_ascii=False))
        db.set_setting("housekeeping_day", db.today())
        rows = sum(res["rows"].values())
        freed = round(before["db_mb"] + before["shots_mb"] + before["backups_mb"] + before["profiles_mb"]
                      - after["db_mb"] - after["shots_mb"] - after["backups_mb"] - after["profiles_mb"], 1)
        res["freed_mb"] = max(0, freed)
        db.log("khoa", "Dọn dữ liệu", f"Xóa {rows} dòng nhật ký cũ, {res['shots']['files']} ảnh chụp, "
               f"{res['backups']['files']} bản sao lưu thừa; giải phóng {res['freed_mb']} MB")
        return res
    finally:
        _run.release()


def summary(res: dict | None = None) -> str:
    """Một câu cho CEO báo sếp."""
    s = sizes()
    line = (f"Dữ liệu hiện tại: cơ sở dữ liệu {s['db_mb']} MB, ảnh chụp {s['shots_mb']} MB ({s['shots']} ảnh), "
            f"sao lưu {s['backups_mb']} MB, hồ sơ Chrome các nick {s['profiles_mb']} MB.")
    if res and not res.get("busy"):
        line = (f"Em đã dọn: {sum(res['rows'].values())} dòng nhật ký cũ, {res['shots']['files']} ảnh chụp cũ, "
                f"{res['backups']['files']} bản sao lưu thừa"
                + (f", bộ nhớ Chrome của {res['chrome']['nicks']} nick" if res.get("chrome", {}).get("nicks") else "")
                + f", giải phóng {res['freed_mb']} MB. " + line)
    elif res and res.get("busy"):
        line = "Đang dọn dữ liệu rồi ạ. " + line
    return line


def tick(now):
    """Mỗi ngày một lần sau giờ dọn (mặc định 03:20); máy tắt đêm thì dọn ở lần bật máy sau đó."""
    st = db.get_settings()
    if st.get("housekeeping_on", "1") != "1" or st.get("housekeeping_day") == db.today():
        return
    if now.strftime("%H:%M") < (st.get("housekeeping_time") or "03:20"):
        return
    db.set_setting("housekeeping_day", db.today())
    threading.Thread(target=run, daemon=True).start()

"""Nhi tự tạo Trang Facebook từ ý tưởng của mình, tạo xong báo sếp (sếp bật ở mục Trang xu hướng, cài đặt `trend_autocreate`).

1. Chọn (sau mỗi lượt đọc xu hướng, hoặc sếp bấm “Nhi tạo Trang này”): ý tưởng mới nhất chưa hỏng quá 2 lần, nick quản trị đủ an toàn:
   đang làm việc, đã dùng từ 14 ngày, không nghỉ sau sự cố, sức khỏe nick từ 50 điểm, 30 ngày qua chưa tạo Trang nào. Trần chung:
   `trend_create_per_week` Trang / 7 ngày (mặc định 1, tối đa 3). Trang chuyển sang 'creating' và chờ ca làm việc của nick.
2. Tạo (trong ca của nick, đúng giờ làm, cùng Chrome đang mở, không mở riêng): facebook.com/pages/creation → điền tên, hạng mục, tiểu sử
   → Tạo Trang → bỏ qua các bước thiết lập → lấy link → chuyển về nick cá nhân (xác nhận bằng nút “Chuyển ngay” trên Trang mới).
3. Xong: Trang chạy lịch đăng mặc định, Nhi viết bài hôm nay, báo Telegram (link, nick, mô tả, prompt ảnh đại diện / ảnh bìa).
Facebook hỏi xác minh / checkpoint: dừng như mọi việc khác (không giải captcha). Lỗi 2 lần thì dừng ý tưởng đó, báo sếp tạo tay.
"""
import re
import threading
from datetime import datetime, timedelta
from urllib.parse import parse_qs, urlsplit

import db

MAX_TRIES = 2


def _s() -> dict:
    return db.get_settings()


def on() -> bool:
    return _s().get("trend_autocreate", "1") == "1"


def per_week() -> int:
    try:
        import departments  # mỗi Biên tập Trang: phòng được tạo thêm 1 Trang / 7 ngày (tối đa 3)
        return max(1, min(3, int(_s().get("trend_create_per_week") or 1) + departments.count("page_editor")))
    except ValueError:
        return 1


def _ago(days: float) -> str:
    return (db.clock() - timedelta(days=days)).strftime("%Y-%m-%d %H:%M:%S")


def made_recently(days: int = 7) -> int:
    return db.one("SELECT COUNT(*) n FROM fb_pages WHERE auto_created_at >= ?", (_ago(days),))["n"]


def nick_ok(acc: dict) -> str | None:
    """None = nick dùng được để tạo Trang; không thì lý do."""
    now = db.now()
    if acc.get("rest_until") and acc["rest_until"] > now:
        return "đang nghỉ sau sự cố"
    try:
        if (db.clock() - datetime.strptime((acc.get("created_at") or "")[:10], "%Y-%m-%d")).days < 14:
            return "nick mới dưới 14 ngày"
    except ValueError:
        pass
    try:
        import nick_health
        h = nick_health.get(acc["id"]) or {}
        if h.get("score") is not None and h["score"] < 50:
            return f"sức khỏe nick {h['score']}/100"
    except Exception as e:
        print("[trend create]", e)
    if db.one("SELECT id FROM fb_pages WHERE admin_account_id=? AND auto_created_at >= ?", (acc["id"], _ago(30))):
        return "đã tạo một Trang trong 30 ngày qua"
    return None


def choose_nick() -> tuple[dict | None, str]:
    import accounts
    want = _s().get("trend_create_nick") or ""
    nicks = accounts.working()
    if want:
        nicks = [a for a in nicks if str(a["id"]) == want] or nicks
    why = []
    ok = []
    for a in nicks:
        r = nick_ok(a)
        (why.append(f"{a['name']}: {r}") if r else ok.append(a))
    if not ok:
        return None, ("; ".join(why[:4]) or "chưa có nick đăng nhập, đang làm việc")
    pages = {r["admin_account_id"]: r["n"] for r in db.q("SELECT admin_account_id, COUNT(*) n FROM fb_pages WHERE status='active' GROUP BY admin_account_id")}
    ok.sort(key=lambda a: (str(a["id"]) != want, pages.get(a["id"], 0), a["sale_id"], a["id"]))
    return ok[0], ""


def pick(pid: int | None = None) -> dict:
    """Đưa một ý tưởng vào hàng tạo. pid = sếp chọn đúng ý tưởng (bỏ qua trần tuần, vẫn giữ luật nick)."""
    for p in db.q("SELECT id, admin_account_id FROM fb_pages WHERE status='creating' AND create_at <= ?", (_ago(2),)):
        _fail(p["id"], "Nick quản trị không có ca làm việc trong 2 ngày", notify=False)  # nick bị tắt / hết giờ làm: trả lại
    if not pid and not on():
        return {"ok": False, "why": "Nhi tự tạo Trang đang tắt"}
    if db.one("SELECT id FROM fb_pages WHERE status='creating'"):
        return {"ok": False, "why": "Đang có Trang chờ tạo"}
    if not pid and made_recently() >= per_week():
        return {"ok": False, "why": f"Đã tạo {per_week()} Trang trong 7 ngày (trần an toàn)"}
    idea = db.one("SELECT * FROM fb_pages WHERE id=? AND status='idea'", (pid,)) if pid else \
        db.one(f"SELECT * FROM fb_pages WHERE status='idea' AND COALESCE(create_tries,0) < {MAX_TRIES} AND COALESCE(reason,'') != 'Sếp thêm' "
               "ORDER BY id DESC LIMIT 1")
    if not idea:
        return {"ok": False, "why": "Không có ý tưởng Trang nào chờ tạo"}
    acc, why = choose_nick()
    if not acc:
        if _s().get("trend_create_warn") != db.today():
            db.set_setting("trend_create_warn", db.today())
            db.log("nhi", "Chưa tạo được Trang", f"Không có nick đủ an toàn để tạo Trang {idea['name']}: {why}")
        return {"ok": False, "why": f"Không có nick đủ an toàn: {why}"}
    db.run("UPDATE fb_pages SET status='creating', admin_account_id=?, create_at=?, create_error=NULL WHERE id=?", (acc["id"], db.now(), idea["id"]))
    db.log("nhi", "Chuẩn bị tạo Trang", f"Trang {idea['name']} sẽ được tạo bằng nick {acc['name']} ở ca làm việc tới")
    return {"ok": True, "page_id": idea["id"], "account_id": acc["id"], "nick": acc["name"]}


def due(aid: int) -> list[int]:
    acc = db.one("SELECT active_from, active_to FROM fb_accounts WHERE id=?", (aid,)) or {}
    hm = db.clock().strftime("%H:%M")
    if not ((acc.get("active_from") or "08:00") <= hm < (acc.get("active_to") or "22:00")):
        return []
    return [r["id"] for r in db.q("SELECT id FROM fb_pages WHERE status='creating' AND admin_account_id=?", (aid,))]


def _fail(pid: int, why: str, notify: bool = True, shot: str | None = None):
    p = db.one("SELECT * FROM fb_pages WHERE id=?", (pid,)) or {}
    tries = (p.get("create_tries") or 0) + 1
    db.run("UPDATE fb_pages SET status='idea', create_tries=?, create_error=? WHERE id=?", (tries, why[:300], pid))
    db.log("nhi", "Tạo Trang chưa được", f"{p.get('name')}: {why[:200]}")
    if notify:
        import errors
        errors.report("trends", f"Nhi chưa tạo được Trang {p.get('name')}", why, screen="trends", screenshot=shot)
        if tries >= MAX_TRIES:
            import trend_pages
            trend_pages._tg(f"⚠️ <b>Nhi tạo Trang “{_e(p.get('name'))}” lỗi {tries} lần</b>, đã dừng tự tạo Trang này.\n{_e(why[:300])}\n"
                            "Anh tạo tay trên Facebook rồi bấm <b>Tôi đã tạo Trang này</b> ở mục Trang xu hướng.")


def _e(t) -> str:
    import telegram_bot
    return telegram_bot.e(t or "")


def clean_url(u: str) -> str:
    p = urlsplit(u or "")
    if p.path.rstrip("/").endswith("profile.php"):
        i = parse_qs(p.query).get("id", [""])[0]
        return f"{p.scheme}://{p.netloc}/profile.php?id={i}" if i else ""
    return f"{p.scheme}://{p.netloc}{p.path.rstrip('/')}"


def _field(page, labels: list[str]):
    for lb in labels:
        rx = re.compile(re.escape(lb), re.I)
        for loc in (page.get_by_label(rx), page.get_by_role("textbox", name=rx), page.get_by_role("combobox", name=rx), page.get_by_placeholder(rx)):
            try:
                for i in range(min(loc.count(), 4)):
                    if loc.nth(i).is_visible():
                        return loc.nth(i)
            except Exception:
                pass
    return None


def _category(page, box, wanted: list[str]) -> str:
    """Gõ hạng mục rồi chọn gợi ý đầu tiên Facebook đưa ra; không có thì thử hạng mục dự phòng."""
    import browser_poster as B
    for w in [x for x in wanted if x]:
        box.fill("")
        box.fill(w[:40])
        B._pause(page, 1.2, 2.0)
        opts = page.get_by_role("option")
        for i in range(min(opts.count(), 6)):
            o = opts.nth(i)
            if o.is_visible():
                txt = o.inner_text().strip()
                o.click()
                return txt
    return ""


def _create_one(page, aid: int, p: dict) -> str:
    import browser_poster as B
    s = B.selectors()
    g = lambda k, d: s.get(k) or d
    page.goto(B.FB_BASE + "/pages/creation/", wait_until="domcontentloaded", timeout=60000)
    page.wait_for_timeout(3500)
    B._check_blocked(page)
    name = _field(page, g("page_create_name", ["Tên Trang", "Page name"]))
    if not name:
        raise RuntimeError("Không thấy ô Tên Trang ở trang tạo Trang (Facebook đổi giao diện: thêm chữ đang thấy vào page_create_name "
                           f"trong backend/fb_selectors.json). Đang thấy: {B._labels_on(page)}")
    name.fill(p["name"][:75])
    B._pause(page, 0.8, 1.6)
    cat = _field(page, g("page_create_category", ["Hạng mục", "Category"]))
    if not cat:
        raise RuntimeError("Không thấy ô Hạng mục (thêm chữ đang thấy vào page_create_category trong backend/fb_selectors.json)")
    words = (p.get("category") or "").replace("&", " ").split()
    got = _category(page, cat, [p.get("category") or "", " ".join(words[:2])] + g("page_create_category_fallback", ["Blog cá nhân", "Personal blog"]))
    if not got:
        raise RuntimeError(f"Facebook không gợi ý hạng mục nào cho “{p.get('category')}” (thêm hạng mục dự phòng vào page_create_category_fallback)")
    bio = _field(page, g("page_create_bio", ["Tiểu sử", "Bio"]))
    if bio and p.get("description"):
        bio.fill(p["description"][:255])
    B._pause(page, 1.0, 2.0)
    db.set_setting("page_acting_aid", str(aid))  # Facebook có thể tự chuyển nick sang Trang mới: ca sau phải chuyển về trước khi làm việc nhóm
    if not B._wait_click(page, g("page_create_button", ["Tạo Trang", "Create Page"]), timeout=10):
        raise RuntimeError(f"Không bấm được nút Tạo Trang. Đang thấy: {B._labels_on(page)}")
    p["_clicked"] = True
    page.wait_for_timeout(5000)
    B._check_blocked(page)
    steps = g("page_create_steps", ["Bỏ qua", "Skip", "Không phải bây giờ", "Not now", "Tiếp", "Next", "Xong", "Done"])
    for _ in range(8):  # các bước thiết lập sau khi tạo (ảnh, WhatsApp, mời bạn bè...): ưu tiên Bỏ qua, không mời ai
        if not B._wait_click(page, steps, timeout=6):
            break
        page.wait_for_timeout(2500)
    url = clean_url(page.url) if "/pages/creation" not in page.url else ""
    if not url:
        raise RuntimeError(f"Đã bấm Tạo Trang nhưng Facebook chưa mở Trang mới (tên có thể bị từ chối). Đang thấy: {B._labels_on(page)}")
    return url


def create(page, aid: int, ids: list[int]):
    """Trong ca làm việc của nick: tạo các Trang đang chờ (thường 1)."""
    import browser_poster as B
    import trend_pages as T
    for pid in ids:
        p = db.one("SELECT * FROM fb_pages WHERE id=? AND status='creating'", (pid,))
        if not p:
            continue
        import workflows
        workflows.set_status("nhi", "working", f"Tạo Trang {p['name']}")
        try:
            url = _create_one(page, aid, p)
        except B.Blocked as e:
            _fail(pid, f"Facebook chặn / hỏi xác minh khi tạo Trang: {e}")
            raise
        except Exception as e:
            shot = None
            try:
                shot = str(db.SHOTS_DIR / f"page_create_{pid}_{int(datetime.now().timestamp())}.png")
                page.screenshot(path=shot)
            except Exception:
                shot = None
            _fail(pid, str(e), shot=shot)
            if p.get("_clicked"):  # đã bấm Tạo: lỡ Facebook đã chuyển sang Trang thì chuyển về nick cá nhân
                db.set_setting("page_acting_url", "")
                B._switch_back(page, aid, "")
            elif db.get_settings().get("page_acting_aid") == str(aid):
                db.set_setting("page_acting_aid", "")
            continue
        finally:
            workflows.set_status("nhi", "idle", "Đang sẵn sàng")
        db.run("UPDATE fb_pages SET auto_created_at=?, create_error=NULL WHERE id=?", (db.now(), pid))
        T.activate(pid, url, aid, int(_s().get("trend_create_posts") or 2), _s().get("trend_create_times") or "09:00,19:30")
        back = B._switch_back(page, aid, url)  # thấy nút “Chuyển ngay” trên Trang mới = nick cá nhân là quản trị viên, đã về nick cá nhân
        if back:
            db.set_setting("page_acting_aid", "")
        else:
            db.set_setting("page_acting_url", url)
        report(pid, back)
        threading.Thread(target=lambda: T.plan_today(force=True), daemon=True).start()


def report(pid: int, back: bool = True):
    p = db.one("SELECT f.*, a.name nick, s.name sale FROM fb_pages f LEFT JOIN fb_accounts a ON a.id=f.admin_account_id "
               "LEFT JOIN sales s ON s.id=a.sale_id WHERE f.id=?", (pid,))
    db.log("nhi", "Đã tạo Trang mới", f"{p['name']} ({p['url']}) bằng nick {p['nick']}, bắt đầu lịch đăng {p['posts_per_day']} bài/ngày")
    import trend_pages
    trend_pages._tg(
        f"✅ <b>Nhi đã tạo Trang mới: {_e(p['name'])}</b>\n🔗 {_e(p['url'])}\n"
        f"Ngách: {_e(p['niche'])}" + (f" · Hạng mục: {_e(p['category'])}" if p.get("category") else "") + "\n"
        f"Nick quản trị: {_e(p['nick'])} ({_e(p['sale'] or '')})\n"
        + (f"Mô tả: {_e(p['description'])}\n" if p.get("description") else "")
        + (f"Vì sao làm Trang này: {_e(p['reason'])}\n" if p.get("reason") else "")
        + f"Lịch đăng: {p['posts_per_day']} bài/ngày lúc {_e(p['times'])}. Nhi đang viết bài hôm nay, prompt ảnh từng bài sẽ gửi sau.\n"
        + (f"\n<b>Ảnh đại diện</b> (chạm để chép):\n<code>{_e(p['avatar_prompt'])}</code>\n" if p.get("avatar_prompt") else "")
        + (f"<b>Ảnh bìa</b>:\n<code>{_e(p['cover_prompt'])}</code>\n" if p.get("cover_prompt") else "")
        + "Trang chưa có ảnh đại diện, ảnh bìa: anh tạo ảnh rồi đặt trên Trang."
        + ("" if back else "\n⚠️ Nick chưa chuyển về tên cá nhân được: ca sau sale chuyển về trước khi làm việc nhóm."))

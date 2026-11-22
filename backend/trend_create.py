"""Nhi tự tạo Trang Facebook từ ý tưởng của mình, tạo xong báo sếp (sếp bật ở mục Trang xu hướng, cài đặt `trend_autocreate`).

1. Chọn (sau mỗi lượt đọc xu hướng, hoặc sếp bấm “Nhi tạo Trang này”): ý tưởng mới nhất chưa hỏng quá 2 lần, nick quản trị đủ an toàn:
   đang làm việc, đã dùng từ 14 ngày, không nghỉ sau sự cố, sức khỏe nick từ 50 điểm, 30 ngày qua chưa tạo Trang nào. Trần chung:
   `trend_create_per_week` Trang / 7 ngày (mặc định 1, tối đa 3). Trang chuyển sang 'creating' và chờ ca làm việc của nick.
2. Tạo (trong ca của nick, đúng giờ làm, cùng Chrome đang mở, không mở riêng): facebook.com/pages/creation → điền tên, hạng mục, tiểu sử
   → Tạo Trang → bỏ qua các bước thiết lập → lấy link → chuyển về nick cá nhân (xác nhận bằng nút “Chuyển ngay” trên Trang mới).
3. Xong: Trang chạy lịch đăng mặc định, Nhi viết bài hôm nay, báo Telegram (link, nick, mô tả, prompt ảnh đại diện / ảnh bìa).
Facebook hỏi xác minh / checkpoint: dừng như mọi việc khác (không giải captcha). Lỗi 2 lần thì dừng ý tưởng đó, báo sếp tạo tay.
"""
import json
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
    if not pid and idea:  # Nhi tự tạo: chỉ ý tưởng thuộc ngách trọng tâm sếp chọn
        import page_brain
        ideas = db.q(f"SELECT * FROM fb_pages WHERE status='idea' AND COALESCE(create_tries,0) < {MAX_TRIES} AND COALESCE(reason,'') != 'Sếp thêm' ORDER BY id DESC")
        idea = next((i for i in ideas if page_brain.in_focus(f"{i['name']} {i['niche'] or ''} {i.get('description') or ''}")
                     and not page_brain.is_avoided(f"{i['name']} {i['niche'] or ''}")), None)
    if not idea:
        return {"ok": False, "why": "Không có ý tưởng Trang nào chờ tạo (thuộc ngách trọng tâm)"}
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


def _fail(pid: int, why: str, notify: bool = True, shot: str | None = None, keep: bool = False):
    """keep = đã bấm Tạo Trang (Trang có thể đã có): giữ hàng chờ cùng nick để ca sau tìm Trang trong “Trang của bạn”, không tạo trùng."""
    p = db.one("SELECT * FROM fb_pages WHERE id=?", (pid,)) or {}
    tries = (p.get("create_tries") or 0) + 1
    st = "creating" if keep and tries < MAX_TRIES else "idea"
    db.run("UPDATE fb_pages SET status=?, create_tries=?, create_error=?, create_at=? WHERE id=?", (st, tries, why[:300], db.now(), pid))
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


def _norm(t: str) -> str:
    return re.sub(r"\s+", " ", (t or "").casefold()).strip()


def variants(name: str, niche: str = "", alts: list | None = None) -> list[str]:
    """Tên chính trước, rồi tên khác Nhi nghĩ ra (Claude) và tên ghép theo luật khi tên bị trùng."""
    n, nic = (name or "").strip(), (niche or "").strip()
    out = [n] + [a for a in (alts or []) if isinstance(a, str)]
    if nic and _norm(nic) not in _norm(n):
        out.append(f"{n} - {nic[:1].upper() + nic[1:]}")
    out += [f"{n} Mỗi Ngày", f"{n} Việt" if _norm(n).startswith("góc") else f"Góc {n}", f"{n} Việt Nam", f"Nhà {n}"]
    seen, res = set(), []
    for x in out:
        x = re.sub(r"\s+", " ", x).strip()[:75]
        if x and _norm(x) not in seen:
            seen.add(_norm(x))
            res.append(x)
    return res


def unique_name(name: str, niche: str = "", alts: list | None = None, exclude: int | None = None) -> str:
    """Tên chưa trùng Trang nào trong phần mềm."""
    used = {_norm(r["name"]) for r in db.q("SELECT id, name FROM fb_pages WHERE status != 'dismissed'") if r["id"] != exclude}
    return next((v for v in variants(name, niche, alts) if _norm(v) not in used), variants(name, niche, alts)[-1])


def _fb_taken(page, name: str) -> bool:
    """Tìm Trang trên Facebook (chỉ đọc): đã có Trang trùng đúng tên chưa."""
    import browser_poster as B
    from urllib.parse import quote
    try:
        page.goto(B.FB_BASE + "/search/pages/?q=" + quote(name), wait_until="domcontentloaded", timeout=60000)
        page.wait_for_timeout(3000)
        B._check_blocked(page)
        body = page.inner_text("body")
    except B.Blocked:
        raise
    except Exception as e:
        print("[trend create search]", e)
        return False
    key = _norm(name)
    return any(_norm(line) == key for line in body.split("\n"))


def _click_step(page, labels: list[str]) -> bool:
    """Bấm nút bước thiết lập; Facebook hay có thông báo (role=alert) đè lên nút: Esc rồi bấm lại, cuối cùng gửi click thẳng vào nút."""
    import browser_poster as B
    el = B._visible_first(page, labels)
    if not el:
        return False
    for how in ("click", "esc", "dispatch"):
        try:
            if how == "esc":
                page.keyboard.press("Escape")
                page.wait_for_timeout(800)
                el = B._visible_first(page, labels) or el
            if how == "dispatch":
                el.dispatch_event("click")
            else:
                el.click(timeout=6000)
            return True
        except Exception as e:
            print("[trend create step]", how, str(e)[:120])
    return False


def _find_my_page(page, names: list[str]) -> tuple[str, str] | None:
    """Tìm trong “Trang của bạn” của nick: Trang đúng tên (lần trước đã tạo xong mà chưa kịp nhận) → (tên, link)."""
    import browser_poster as B
    want = {_norm(n): n for n in names if n}
    for path in ("/pages/?category=your_pages", "/bookmarks/pages"):
        try:
            page.goto(B.FB_BASE + path, wait_until="domcontentloaded", timeout=60000)
            page.wait_for_timeout(3500)
            B._check_blocked(page)
            links = page.eval_on_selector_all("a[href]", "els=>els.map(e=>[(e.innerText||e.getAttribute('aria-label')||''),e.href])")
        except B.Blocked:
            raise
        except Exception as e:
            print("[trend create my pages]", e)
            continue
        for txt, href in links:
            key = _norm((txt or "").split("\n")[0])
            if key in want and href and "/pages/?" not in href and "/bookmarks" not in href and "/search" not in href:
                u = clean_url(href)
                if u:
                    return want[key], u
    return None


def _create_one(page, aid: int, p: dict) -> str:
    import browser_poster as B
    s = B.selectors()
    g = lambda k, d: s.get(k) or d
    names = variants(p["name"], p.get("niche") or "", json.loads(p.get("alt_names") or "[]"))[:5]
    got = _find_my_page(page, names)  # nick đã quản lý Trang đúng tên (lần trước tạo xong nhưng lỗi ở bước sau): nhận luôn, không tạo trùng
    if got:
        if got[0] != p["name"]:
            db.run("UPDATE fb_pages SET name=? WHERE id=?", (got[0], p["id"]))
            p["name"] = got[0]
        db.log("nhi", "Tìm thấy Trang đã tạo", f"{got[0]} đã có trong Trang của nick, Nhi nhận luôn, không tạo trùng")
        return got[1]
    free, notes = [], []
    for nm in names:  # Facebook đã có Trang trùng đúng tên thì Nhi dùng tên khác
        if _fb_taken(page, nm):
            notes.append(f"“{nm}” đã có Trang trùng tên trên Facebook")
        else:
            free.append(nm)
        if len(free) >= 2:
            break
    if not free:
        raise RuntimeError("Các tên Nhi thử đều đã có Trang trùng trên Facebook: " + "; ".join(names))
    page.goto(B.FB_BASE + "/pages/creation/", wait_until="domcontentloaded", timeout=60000)
    page.wait_for_timeout(3500)
    B._check_blocked(page)
    name = _field(page, g("page_create_name", ["Tên Trang", "Page name"]))
    if not name:
        raise RuntimeError("Không thấy ô Tên Trang ở trang tạo Trang (Facebook đổi giao diện: thêm chữ đang thấy vào page_create_name "
                           f"trong backend/fb_selectors.json). Đang thấy: {B._labels_on(page)}")
    chosen = free[0]
    name.fill(chosen)
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
    for nm in free[1:]:  # Facebook từ chối tên (vẫn ở trang tạo, không sang bước sau): thử tên khác ngay
        if "/pages/creation" not in page.url or B._visible_first(page, g("page_create_steps", ["Bỏ qua", "Skip"])):
            break
        notes.append(f"Facebook không nhận tên “{chosen}”")
        chosen = nm
        name.fill(chosen)
        B._pause(page, 0.8, 1.6)
        B._wait_click(page, g("page_create_button", ["Tạo Trang", "Create Page"]), timeout=10)
        page.wait_for_timeout(5000)
        B._check_blocked(page)
    if chosen != p["name"] or notes:
        db.run("UPDATE fb_pages SET name=?, name_note=? WHERE id=?", (chosen, "; ".join(notes)[:300] or None, p["id"]))
        p["name"] = chosen
    steps = g("page_create_steps", ["Bỏ qua", "Skip", "Không phải bây giờ", "Not now", "Tiếp", "Next", "Xong", "Done"])
    for _ in range(8):  # các bước thiết lập sau khi tạo (ảnh, WhatsApp, mời bạn bè...): ưu tiên Bỏ qua, không mời ai
        if not _click_step(page, steps):
            break
        page.wait_for_timeout(2500)
    here = clean_url(page.url) if "/pages/creation" not in page.url else ""
    got = _find_my_page(page, [chosen])  # link chắc chắn nhất: Trang mới trong “Trang của bạn”
    url = got[1] if got else here
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
        url = ""
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
            if p.get("_clicked"):  # đã bấm Tạo Trang: xem Trang đã có chưa trước khi coi là lỗi
                try:
                    got = _find_my_page(page, [p["name"]])
                except B.Blocked:
                    got = None
                if got:
                    url = got[1]
                    db.log("nhi", "Tạo Trang xong dù bước sau lỗi", f"{p['name']}: {str(e)[:150]}")
            if not url:
                _fail(pid, str(e), shot=shot, keep=bool(p.get("_clicked")))
            if not url and p.get("_clicked"):  # đã bấm Tạo: lỡ Facebook đã chuyển sang Trang thì chuyển về nick cá nhân
                db.set_setting("page_acting_url", "")
                B._switch_back(page, aid, "")
            elif not url and db.get_settings().get("page_acting_aid") == str(aid):
                db.set_setting("page_acting_aid", "")
            if not url:
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
        + (f"ℹ️ Tên sếp giao “{_e(p['requested_name'])}” bị trùng, Nhi đổi thành “{_e(p['name'])}” ({_e(p.get('name_note') or 'trùng Trang đã có')}).\n"
           if p.get("requested_name") and _norm(p["requested_name"]) != _norm(p["name"]) else "")
        + 
        f"Ngách: {_e(p['niche'])}" + (f" · Hạng mục: {_e(p['category'])}" if p.get("category") else "") + "\n"
        f"Nick quản trị: {_e(p['nick'])} ({_e(p['sale'] or '')})\n"
        + (f"Mô tả: {_e(p['description'])}\n" if p.get("description") else "")
        + (f"Vì sao làm Trang này: {_e(p['reason'])}\n" if p.get("reason") else "")
        + f"Lịch đăng: {p['posts_per_day']} bài/ngày lúc {_e(p['times'])}. Nhi đang viết bài hôm nay, prompt ảnh từng bài sẽ gửi sau.\n"
        + ("Nhi đang tự làm logo và banner, xong gửi anh xem (muốn đổi thì trả lời tin ảnh bằng ảnh khác)." if __import__("image_gen").on()
           else "Nhi gửi riêng 2 tin xin logo và banner: anh tạo ảnh rồi trả lời đúng tin đó bằng ảnh, Nhi tự đặt lên Trang.")
        + ("" if back else "\n⚠️ Nick chưa chuyển về tên cá nhân được: ca sau sale chuyển về trước khi làm việc nhóm."))
    import image_gen

    def imgs():
        try:
            if image_gen.on():
                image_gen.for_page(pid)  # Nhi tự làm logo, banner; phần nào chưa làm được thì xin sếp
        except Exception as ex:
            print("[ảnh Trang]", ex)
        request_images(pid)
    imgs() if image_gen.SYNC else threading.Thread(target=imgs, daemon=True).start()


# ---------------------------------------------------------------- sếp giao ý tưởng Trang
BAD_NAME = re.compile(r"facebook|meta\b|instagram|chính thức|official|bộ |sở |ủy ban|công an|chính phủ|vtv|báo ", re.I)


def boss_idea(name: str, niche: str = "", note: str = "") -> dict:
    """Sếp đưa tên / ý tưởng Trang: Nhi soạn đủ thông tin + prompt logo, banner, đổi tên nếu trùng, đưa vào hàng tạo ngay."""
    from llm import llm
    name = re.sub(r"\s+", " ", (name or "")).strip(" .“”\"'")[:75]
    if len(name) < 3:
        raise ValueError("Điền tên Trang (ít nhất 3 ký tự)")
    if BAD_NAME.search(name):
        raise ValueError("Tên giống Trang chính thức của tổ chức / cơ quan / nền tảng: Facebook không cho, dễ bị coi là mạo danh. Sếp đặt tên khác")
    niche = (niche or "").strip()[:60]
    mock = lambda: {"niche": niche or name, "category": "Blog cá nhân",
                    "description": f"Chia sẻ {niche or name}: mẹo hay, thông tin hữu ích, hỏi đáp cho người quan tâm."[:200],
                    "avatar_prompt": f"Minimal flat vector logo icon for a Facebook page about {niche or name}, bold friendly colors, centered symbol, no text, no letters, square 1:1",
                    "cover_prompt": f"Wide banner illustration about {niche or name}, modern flat style, warm colors, empty space in the center, no text, 1640x624",
                    "alt_names": []}
    d = mock()
    if llm.live:
        from agents import system_prompt
        ask = f"""Sếp giao bạn mở Trang Facebook tên “{name}”{(' về ' + niche) if niche else ''}.{(' Sếp dặn: ' + note) if note else ''}
Soạn thông tin để tạo Trang: niche (ngách, ≤ 6 chữ), category (hạng mục Trang trên Facebook, tiếng Việt), description (≤ 200 ký tự, tự nhiên),
avatar_prompt (logo vuông 1:1) và cover_prompt (banner 1640x624) bằng tiếng Anh cho công cụ tạo ảnh: không chữ, không logo thương hiệu thật,
không mặt người thật; alt_names: 3 tên khác gần nghĩa, tự nhiên, dùng khi tên chính đã có Trang trùng (không thêm chữ “official”, “chính thức”).
JSON: {{"niche":"...","category":"...","description":"...","avatar_prompt":"...","cover_prompt":"...","alt_names":["...","...","..."]}}"""
        got = llm.json(system_prompt("nhi", _s()), ask, mock=mock, max_tokens=700, task="posts")
        if isinstance(got, dict):
            d.update({k: v for k, v in got.items() if v})
    alts = [a for a in (d.get("alt_names") or []) if isinstance(a, str) and not BAD_NAME.search(a)][:3]
    final = unique_name(name, d["niche"], alts)
    pid = db.run("""INSERT INTO fb_pages(name, niche, category, description, avatar_prompt, cover_prompt, reason, status, requested_name, alt_names,
                    name_note, created_at) VALUES (?,?,?,?,?,?,?, 'idea', ?,?,?,?)""",
                 (final, str(d["niche"])[:60], str(d.get("category") or "")[:60], str(d.get("description") or "")[:255],
                  str(d.get("avatar_prompt") or "")[:600], str(d.get("cover_prompt") or "")[:600], ("Sếp giao" + (f": {note}" if note else ""))[:400],
                  name, json.dumps(alts, ensure_ascii=False), None if final == name else "Trùng tên Trang đã có trong phần mềm", db.now()))
    db.log("nhi", "Nhận ý tưởng Trang của sếp", f"{final}" + (f" (tên sếp giao “{name}” đã có, Nhi đổi tên)" if final != name else ""))
    r = pick(pid)
    return {"page": db.one("SELECT * FROM fb_pages WHERE id=?", (pid,)), "renamed": final != name, "queued": r.get("ok"),
            "nick": r.get("nick"), "why": r.get("why")}


# ---------------------------------------------------------------- logo + banner: Nhi soạn prompt, sếp tạo ảnh gửi lại, nick đặt lên Trang
KIND = {"avatar": ("logo (ảnh đại diện)", "Ảnh vuông 1:1, tối thiểu 720×720"), "cover": ("banner (ảnh bìa)", "Ảnh ngang 1640×624 (tỉ lệ ~2,6:1)")}


def request_images(pid: int) -> int:
    """Gửi 2 tin Telegram xin logo, banner (kèm prompt); sếp trả lời đúng tin bằng ảnh."""
    import trend_pages
    p = db.one("SELECT * FROM fb_pages WHERE id=?", (pid,))
    n = 0
    for k, (label, size) in KIND.items():
        if p.get(f"{k}_done") or p.get(f"{k}_path"):
            continue
        res = trend_pages._tg(f"🖼 <b>Cần {label} cho Trang {_e(p['name'])}</b>\n{size}.\n<b>Prompt</b> (chạm để chép):\n<code>{_e(p.get(f'{k}_prompt') or '')}</code>\n"
                              f"\n👉 Tạo ảnh xong, <b>trả lời (reply) tin này bằng ảnh</b>. Nhi tự đặt lên Trang ở ca làm việc tới của nick quản trị.")
        ids = ",".join(str(r.get("message_id")) for r in res if isinstance(r, dict) and r.get("message_id"))
        if ids:
            db.run(f"UPDATE fb_pages SET {k}_msg=? WHERE id=?", (ids, pid))
            n += 1
    return n


def page_for_reply(reply_id) -> tuple[dict, str] | None:
    if not reply_id:
        return None
    for p in db.q("SELECT * FROM fb_pages WHERE avatar_msg IS NOT NULL OR cover_msg IS NOT NULL ORDER BY id DESC LIMIT 100"):
        for k in KIND:
            if str(reply_id) in (p.get(f"{k}_msg") or "").split(","):
                return p, k
    return None


def set_page_image(pid: int, kind: str, data: bytes, ext: str = "jpg") -> str:
    import trend_pages
    if kind not in KIND:
        raise ValueError("Loại ảnh không hợp lệ")
    if len(data) < 1000:
        raise ValueError("Ảnh hỏng hoặc quá nhỏ")
    p = db.one("SELECT * FROM fb_pages WHERE id=?", (pid,))
    if not p:
        raise ValueError("Không tìm thấy Trang")
    d = trend_pages.img_dir()
    d.mkdir(parents=True, exist_ok=True)
    f = d / f"page_{pid}_{kind}.{ext if ext in ('jpg', 'jpeg', 'png', 'webp') else 'jpg'}"
    f.write_bytes(data)
    db.run(f"UPDATE fb_pages SET {kind}_path=?, {kind}_done=0, img_tries=0, img_error=NULL WHERE id=?", (str(f), pid))
    db.log("nhi", "Nhận ảnh Trang từ sếp", f"{KIND[kind][0].capitalize()} cho Trang {p['name']}")
    when = "ở ca làm việc tới của nick quản trị" if p["status"] == "active" else "ngay sau khi tạo xong Trang"
    return f"✅ Đã nhận {KIND[kind][0]} cho Trang {p['name']}, Nhi đặt lên Trang {when}."


def image_due(aid: int) -> list[int]:
    if not due_hours(aid):
        return []
    return [r["id"] for r in db.q("""SELECT id FROM fb_pages WHERE status='active' AND admin_account_id=? AND url IS NOT NULL AND COALESCE(img_tries,0) < 2
                                     AND ((avatar_path IS NOT NULL AND COALESCE(avatar_done,0)=0) OR (cover_path IS NOT NULL AND COALESCE(cover_done,0)=0))""", (aid,))]


def due_hours(aid: int) -> bool:
    acc = db.one("SELECT active_from, active_to FROM fb_accounts WHERE id=?", (aid,)) or {}
    hm = db.clock().strftime("%H:%M")
    return (acc.get("active_from") or "08:00") <= hm < (acc.get("active_to") or "22:00")


def _set_photo(page, kind: str, path: str):
    import browser_poster as B
    s = B.selectors()
    g = lambda k, d: s.get(k) or d
    btn = g("page_avatar_button", ["Cập nhật ảnh đại diện", "Update profile picture", "Chọn ảnh đại diện", "Choose profile picture"]) if kind == "avatar" \
        else g("page_cover_button", ["Thêm ảnh bìa", "Chỉnh sửa ảnh bìa", "Add cover photo", "Edit cover photo"])
    if not B._wait_click(page, btn, timeout=10):
        raise RuntimeError(f"Không thấy nút đặt {KIND[kind][0]} (thêm chữ đang thấy vào page_{kind}_button trong fb_selectors.json). Đang thấy: {B._labels_on(page)}")
    page.wait_for_timeout(1500)
    up = None
    for _ in range(10):
        up = B._visible_first(page, g("page_photo_upload", ["Tải ảnh lên", "Upload photo", "Tải lên", "Upload"]))
        if up:
            break
        page.wait_for_timeout(600)
    if not up:
        raise RuntimeError(f"Không thấy nút Tải ảnh lên. Đang thấy: {B._labels_on(page)}")
    with page.expect_file_chooser(timeout=10000) as fc:
        up.click()
    fc.value.set_files(path)
    page.wait_for_timeout(4000)
    if not B._wait_click(page, g("page_photo_save", ["Lưu thay đổi", "Save changes", "Lưu", "Save"]), timeout=30):
        raise RuntimeError(f"Không bấm được Lưu sau khi tải {KIND[kind][0]}. Đang thấy: {B._labels_on(page)}")
    page.wait_for_timeout(5000)


def upload_images(page, aid: int, ids: list[int]):
    """Trong ca của nick quản trị: chuyển sang Trang, đặt logo / banner sếp gửi, chuyển về nick cá nhân."""
    import browser_poster as B
    import trend_pages
    for pid in ids:
        p = db.one("SELECT * FROM fb_pages WHERE id=?", (pid,))
        url = B.fb_url(p["url"])
        done = []
        try:
            B._switch_to_page(page, aid, url)
            for k in KIND:
                if p.get(f"{k}_path") and not p.get(f"{k}_done"):
                    page.goto(url, wait_until="domcontentloaded", timeout=60000)
                    page.wait_for_timeout(2500)
                    _set_photo(page, k, p[f"{k}_path"])
                    db.run(f"UPDATE fb_pages SET {k}_done=1 WHERE id=?", (pid,))
                    done.append(KIND[k][0])
        except B.Blocked:
            raise
        except Exception as e:
            tries = (p.get("img_tries") or 0) + 1
            db.run("UPDATE fb_pages SET img_tries=?, img_error=? WHERE id=?", (tries, str(e)[:300], pid))
            import errors
            errors.report("trends", f"Chưa đặt được ảnh cho Trang {p['name']}", str(e), screen="trends")
            if tries >= 2:
                trend_pages._tg(f"⚠️ Nhi chưa đặt được ảnh cho Trang <b>{_e(p['name'])}</b> sau 2 lần: {_e(str(e)[:200])}\nAnh đặt tay trên Trang giúp em.")
        finally:
            if db.get_settings().get("page_acting_aid") == str(aid):
                B._switch_back(page, aid, url)
        if done:
            db.log("nhi", "Đặt ảnh Trang", f"Trang {p['name']}: đã đặt {', '.join(done)}")
            trend_pages._tg(f"🎨 Đã đặt {', '.join(done)} cho Trang <b>{_e(p['name'])}</b>\n🔗 {_e(p['url'])}")

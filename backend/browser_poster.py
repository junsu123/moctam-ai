"""Nhân viên sale đăng bài Facebook bằng hồ sơ Chrome riêng của mình.

Mỗi sale có một thư mục hồ sơ (data/profiles/sale-<id>). Lần đầu, sếp bấm "Mở Chrome",
tự đăng nhập Facebook trong cửa sổ đó; phiên đăng nhập được lưu trong hồ sơ.
Từ đó sale tự mở hồ sơ, đăng bài theo lịch rồi đóng lại.

Hệ thống không lưu mật khẩu, không giải captcha, không giả mạo dấu vân tay trình duyệt.
Gặp checkpoint hoặc khóa tạm thời -> dừng tự đăng nick đó và báo sếp.
"""
import hashlib
import json
import os
import random
import re
import threading
import time
import traceback
from pathlib import Path
from queue import Queue

import db
import kpi
import media_folder
import workflows

FB_BASE = os.getenv("FB_BASE_URL", "https://www.facebook.com").rstrip("/")
SEL_FILE = Path(__file__).resolve().parent / "fb_selectors.json"

_queues: dict[int, Queue] = {}
_busy: dict[int, str] = {}
_lock = threading.Lock()


class Blocked(Exception):
    """Tài khoản bị checkpoint / khóa / đăng xuất."""


def selectors() -> dict:
    return json.loads(SEL_FILE.read_text(encoding="utf-8"))


def profile_dir(sale_id: int) -> Path:
    p = db.PROFILES_DIR / f"sale-{sale_id}"
    p.mkdir(parents=True, exist_ok=True)
    return p


def busy(sale_id: int) -> str | None:
    return _busy.get(sale_id)


def queued(sale_id: int) -> int:
    q = _queues.get(sale_id)
    return q.qsize() if q else 0


def submit(sale_id: int, job: dict):
    with _lock:
        q = _queues.get(sale_id)
        if q is None:
            q = Queue()
            _queues[sale_id] = q
            threading.Thread(target=_worker, args=(sale_id, q), daemon=True).start()
    q.put(job)


# ---------------------------------------------------------------- trình duyệt
def _launch(pw, sale_id: int, headless: bool | None = None):
    if headless is None:
        headless = db.get_settings().get("browser_headless") == "1"
    kw = dict(user_data_dir=str(profile_dir(sale_id)), headless=headless, locale="vi-VN",
              viewport={"width": 1280, "height": 900}, args=["--disable-notifications"])
    try:
        return pw.chromium.launch_persistent_context(channel="chrome", **kw)  # Google Chrome đã cài
    except Exception as e:
        msg = str(e)
        if any(k in msg for k in ("ProcessSingleton", "already in use", "SingletonLock", "lock file")):
            raise RuntimeError("Hồ sơ Chrome của nick này đang mở ở một cửa sổ khác. Đóng cửa sổ Chrome của sale rồi thử lại")
        if "is not found" not in msg and "Executable doesn't exist" not in msg and "not installed" not in msg.lower():
            # Chrome có trên máy nhưng mở lỗi: không chuyển sang Chromium, vì Chromium không đọc được phiên đăng nhập
            # do Chrome mã hóa (sẽ báo sai là "chưa đăng nhập")
            raise RuntimeError(f"Không mở được Google Chrome: {msg.splitlines()[0][:160]}")
        return pw.chromium.launch_persistent_context(**kw)  # máy chưa cài Chrome: dùng Chromium của Playwright


IN_USE_MSG = ("Hồ sơ Chrome của nick này đang được mở ở một cửa sổ Chrome khác (thường là cửa sổ mở bằng nút “Mở Chrome”). "
              "Đóng hết cửa sổ Chrome của sale này rồi thử lại")
CLOSED_RX = re.compile(r"Target page, context or browser has been closed|Browser closed|browser has disconnected|"
                       r"Target closed|has been closed", re.I)


def is_closed_error(e) -> bool:
    return bool(CLOSED_RX.search(str(e)))


def profile_in_use(sale_id: int) -> bool:
    """Có tiến trình Chrome khác đang giữ hồ sơ này không (mở cùng hồ sơ thì Chrome mới tự đóng ngay)."""
    d = profile_dir(sale_id)
    try:
        if os.name == "nt":
            lf = d / "lockfile"
            if lf.exists():
                try:
                    lf.unlink()  # khóa cũ còn sót: xóa được nghĩa là không ai đang dùng
                except PermissionError:
                    return True
            return False
        lk = d / "SingletonLock"
        if lk.is_symlink():
            pid = int(os.readlink(lk).rsplit("-", 1)[-1])
            try:
                os.kill(pid, 0)
                return True
            except ProcessLookupError:
                lk.unlink(missing_ok=True)  # Chrome cũ đã tắt, khóa còn sót
            except PermissionError:
                return True
    except Exception:
        return False
    return False


def release_profile(sale_id: int) -> int:
    """Đóng các tiến trình Chrome còn treo đang giữ hồ sơ của sale (chỉ những tiến trình mở đúng thư mục hồ sơ này,
    không đụng tới Chrome cá nhân của sếp). Trả về số tiến trình đã đóng."""
    target = str(profile_dir(sale_id).resolve()).lower().replace("\\", "/")
    killed = 0
    try:
        import psutil
    except ImportError:
        return 0
    for p in psutil.process_iter(["name", "cmdline"]):
        try:
            name = (p.info["name"] or "").lower()
            if "chrom" not in name:
                continue
            cmd = " ".join(p.info["cmdline"] or []).lower().replace("\\", "/")
            if f"--user-data-dir={target}" in cmd or f'--user-data-dir="{target}"' in cmd:
                p.kill()
                killed += 1
        except Exception:
            continue
    if killed:
        time.sleep(2)
        db.log(f"sale-{sale_id}", "Đóng Chrome bị treo", f"Đã đóng {killed} tiến trình Chrome cũ còn giữ hồ sơ của nick")
    return killed


def _chrome_version() -> str | None:
    """Phiên bản Google Chrome cài trên máy (Windows), để so với hồ sơ."""
    if os.name != "nt":
        return None
    try:
        import winreg
        for root in (winreg.HKEY_CURRENT_USER, winreg.HKEY_LOCAL_MACHINE):
            try:
                with winreg.OpenKey(root, r"Software\Google\Chrome\BLBeacon") as k:
                    return winreg.QueryValueEx(k, "version")[0]
            except OSError:
                continue
    except Exception:
        pass
    return None


def diagnose_closed(sale_id: int) -> str:
    """Giải thích vì sao Chrome của sale tự đóng ngay khi mở."""
    if profile_in_use(sale_id):
        return IN_USE_MSG
    try:
        prof = (profile_dir(sale_id) / "Last Version").read_text().strip()
    except Exception:
        prof = ""
    cur = _chrome_version()
    major = lambda v: int(v.split(".")[0]) if v and v.split(".")[0].isdigit() else 0
    if prof and cur and major(prof) > major(cur):
        return (f"Hồ sơ Chrome của nick được tạo bằng trình duyệt bản {major(prof)}, mới hơn Google Chrome trên máy (bản "
                f"{major(cur)}), nên Chrome từ chối mở và tự đóng. Cập nhật Google Chrome (menu ⋮ → Trợ giúp → Giới thiệu "
                "về Google Chrome), khởi động lại máy rồi thử lại")
    return ("Chrome của sale tự đóng ngay khi vừa mở. Thử lần lượt: đóng hết cửa sổ Chrome của sale này; cập nhật Google "
            "Chrome; tạm tắt phần mềm diệt virus đang chặn Chrome; bấm “Mở Chrome” ở trang Nhân viên sale xem Chrome báo gì")


CLOSED_MID = ("Cửa sổ Chrome của sale bị đóng khi sale đang làm việc (cửa sổ vừa bị tắt tay, hoặc Chrome bị lỗi). "
              "Không tắt cửa sổ Chrome khi sale đang làm; muốn không thấy cửa sổ thì bật “Ẩn cửa sổ Chrome khi sale đăng bài” "
              "trong Cài đặt. Việc này sẽ được làm lại ở lượt sau")


def friendly(e) -> str:
    """Thông báo lỗi dễ hiểu cho các lỗi kỹ thuật của trình duyệt."""
    first = str(e).strip().splitlines()[0] if str(e).strip() else e.__class__.__name__
    return CLOSED_MID if is_closed_error(first) else first


def _open(pw, sale_id: int, headless: bool | None = None):
    """Mở Chrome của sale và một tab mới để làm việc. Tự thử lại 1 lần nếu Chrome bị đóng ngay khi mở."""
    if profile_in_use(sale_id):
        # việc của một sale chạy lần lượt, nên lúc này phần mềm không mở Chrome nào cho sale này:
        # hồ sơ bị giữ là do Chrome cũ còn treo (phần mềm từng tắt đột ngột) hoặc cửa sổ sếp tự mở -> đóng Chrome treo
        release_profile(sale_id)
        if profile_in_use(sale_id):
            raise RuntimeError(IN_USE_MSG)
    last = None
    for attempt in range(2):
        ctx = _launch(pw, sale_id, headless)
        try:
            # luôn mở tab mới: tab đầu tiên có thể bị Chrome đóng khi khôi phục phiên trước
            page = ctx.new_page()
            page.evaluate("1")
            for other in list(ctx.pages):
                if other is not page and other.url in ("about:blank", "", "chrome://newtab/", "chrome://new-tab-page/"):
                    try:
                        other.close()
                    except Exception:
                        pass
            return ctx, page
        except Exception as e:
            last = e
            try:
                ctx.close()
            except Exception:
                pass
            if not is_closed_error(e):
                raise
            release_profile(sale_id)
            time.sleep(4)
    raise RuntimeError(diagnose_closed(sale_id)) from last


def fb_url(u: str) -> str:
    """Chuẩn hóa link nhóm sếp dán: thêm https://, đổi link điện thoại (m., mbasic., web.) sang giao diện máy tính."""
    u = (u or "").strip()
    if not u:
        return u
    if not re.match(r"^https?://", u, re.I):
        u = "https://" + u.lstrip("/")
    u = re.sub(r"^https?://(m|mbasic|web|touch|mobile)\.facebook\.com", "https://www.facebook.com", u, flags=re.I)
    u = re.sub(r"^https?://(facebook\.com|fb\.com|www\.fb\.com)", "https://www.facebook.com", u, flags=re.I)
    return u


def check_group_url(u: str) -> tuple[str, str | None]:
    """Chuẩn hóa và kiểm tra link nhóm. Trả về (link, lỗi hoặc None)."""
    url = fb_url(u)
    if not url:
        return "", "Dán link nhóm Facebook, ví dụ https://www.facebook.com/groups/tennhom"
    if FB_BASE != "https://www.facebook.com" and url.startswith(FB_BASE):
        return url, None  # Facebook giả lập khi kiểm thử
    if not re.match(r"^https://www\.facebook\.com/(groups/[^/?#]+|share/g/[^/?#]+)", url, re.I):
        return url, ("Link này không phải link nhóm. Mở nhóm trên Facebook (máy tính), copy link trên thanh địa chỉ, "
                     "có dạng https://www.facebook.com/groups/…")
    m = re.match(r"^(https://www\.facebook\.com/groups/[^/?#]+)", url, re.I)
    return (m.group(1) if m else url), None


def _logged_in(ctx) -> bool:
    return any(c["name"] == "c_user" and c["value"] for c in ctx.cookies())


def _check_blocked(page):
    s = selectors()
    url = page.url.lower()
    if any(p in url for p in s["blocked_url_parts"]):
        raise Blocked(f"Facebook chuyển tới trang {page.url[:80]} (checkpoint / đăng xuất)")
    html = page.content()
    for t in s["blocked_texts"]:
        if t.lower() in html.lower():
            raise Blocked(f"Facebook báo: {t}")


def _visible_first(page_or_loc, labels: list[str], role: str | None = "button"):
    for lb in labels:
        rx = re.compile(re.escape(lb), re.I)
        cands = []
        if role:
            cands.append(page_or_loc.get_by_role(role, name=rx))
        cands.append(page_or_loc.get_by_text(rx))
        for loc in cands:
            try:
                n = loc.count()
            except Exception:
                n = 0
            for i in range(min(n, 6)):
                el = loc.nth(i)
                try:
                    if el.is_visible():
                        return el
                except Exception:
                    pass
    return None


def _wait_click(page, labels, timeout=20, role="button"):
    end = time.time() + timeout
    while time.time() < end:
        el = _visible_first(page, labels, role)
        if el:
            el.click()
            return True
        page.wait_for_timeout(600)
    return False


def _pause(page, a=0.6, b=1.6):
    page.wait_for_timeout(int(random.uniform(a, b) * 1000))


def _labels_on(scope, limit=14) -> str:
    """Tên các nút đang thấy (để ghi vào lỗi, giúp sửa fb_selectors.json khi Facebook đổi giao diện)."""
    out = []
    try:
        for el in scope.locator('[role="button"], button').all()[:120]:
            try:
                if el.is_visible():
                    t = (el.get_attribute("aria-label") or el.inner_text() or "").strip().replace("\n", " ")
                    if t and len(t) < 40 and t not in out:
                        out.append(t)
            except Exception:
                pass
            if len(out) >= limit:
                break
    except Exception:
        pass
    return ", ".join(out)


def _composer_dialog(page, timeout=20):
    """Hộp soạn bài: dialog đang hiện có ô nhập (contenteditable). Bỏ qua các dialog khác như khung chat."""
    end = time.time() + timeout
    while time.time() < end:
        dlgs = page.get_by_role("dialog")
        for i in range(dlgs.count() - 1, -1, -1):
            d = dlgs.nth(i)
            try:
                if not d.is_visible():
                    continue
                box = d.locator('[contenteditable="true"][role="textbox"], [contenteditable="true"]')
                for j in range(box.count()):
                    if box.nth(j).is_visible():
                        return d, box.nth(j)
            except Exception:
                pass
        page.wait_for_timeout(500)
    return None, None


def _exact_button(scope, labels):
    """Nút có tên đúng bằng một trong các nhãn (VD 'Đăng', không nhầm với 'Đăng ảnh')."""
    for lb in labels:
        rx = re.compile(rf"^\s*{re.escape(lb)}\s*$", re.I)
        for loc in (scope.get_by_role("button", name=rx), scope.locator(f'[role="button"][aria-label="{lb}"]')):
            try:
                for i in range(loc.count() - 1, -1, -1):
                    if loc.nth(i).is_visible():
                        return loc.nth(i)
            except Exception:
                pass
    return None


def _type_text(page, box, text: str):
    box.click()
    _pause(page, 0.4, 0.9)
    lines = text.split("\n")
    for i, line in enumerate(lines):
        if line:
            page.keyboard.insert_text(line)
        if i < len(lines) - 1:
            page.keyboard.press("Shift+Enter")
    page.wait_for_timeout(600)
    probe = next((l.strip() for l in lines if l.strip()), "")[:15]
    got = ""
    try:
        got = box.inner_text()
    except Exception:
        pass
    if probe and _norm(probe)[:10] not in _norm(got):  # trình soạn thảo không nhận insert_text -> gõ từng phím
        box.click()
        page.keyboard.press("Control+A")
        page.keyboard.press("Delete")
        for i, line in enumerate(lines):
            if line:
                page.keyboard.type(line, delay=15)
            if i < len(lines) - 1:
                page.keyboard.press("Shift+Enter")
        page.wait_for_timeout(600)
        if _norm(probe)[:10] not in _norm(box.inner_text()):
            raise RuntimeError("Không điền được nội dung vào ô viết bài")


def _attach_images(page, dialog, imgs: list[str], labels: list[str]) -> list[str]:
    """Đính ảnh vào hộp soạn bài. Trả về danh sách ảnh đã đính (rỗng nếu không đính được: vẫn đăng chữ)."""
    def inputs():
        loc = dialog.locator('input[type="file"]')
        return [loc.nth(i) for i in range(loc.count())]
    cands = inputs()
    if not cands:
        el = _visible_first(dialog, labels)
        if el:
            el.click()
            page.wait_for_timeout(1500)
        cands = inputs()
    if not cands:
        return []
    # ưu tiên ô nhận ảnh và chọn được nhiều tệp
    def score(el):
        acc = (el.get_attribute("accept") or "").lower()
        return (("image" in acc) or acc == "") * 2 + (el.get_attribute("multiple") is not None)
    inp = max(cands, key=score)
    done = []
    if inp.get_attribute("multiple") is not None:
        inp.set_input_files(imgs)
        done = list(imgs)
    else:
        for f in imgs:  # ô chỉ nhận 1 tệp: đính từng ảnh
            cur = max(inputs() or [inp], key=score)
            cur.set_input_files(f)
            done.append(f)
            page.wait_for_timeout(1500)
    page.wait_for_timeout(2500 + 1500 * len(done))
    return done


def _top_dialog(page):
    dl = page.get_by_role("dialog")
    for i in range(dl.count() - 1, -1, -1):
        try:
            if dl.nth(i).is_visible():
                return dl.nth(i)
        except Exception:
            pass
    return None


def _find_submit(page, s):
    """Tìm nút Đăng (hoặc Tiếp) trong các hộp thoại đang hiện, ưu tiên hộp mở sau cùng."""
    dl = page.get_by_role("dialog")
    for i in range(dl.count() - 1, -1, -1):
        d = dl.nth(i)
        try:
            if not d.is_visible():
                continue
        except Exception:
            continue
        btn = _exact_button(d, s["post_button"])
        if btn:
            return btn, None
        nxt = _exact_button(d, s.get("next_button", []))
        if nxt:
            return None, nxt
    return None, None


def _publish(page, post: dict, target_url: str, composer_labels: list[str], dry_run: bool, imgs=None):
    """Mở trang, mở hộp soạn bài, điền nội dung + ảnh, bấm Đăng (hoặc Tiếp → Đăng). Trả về (ảnh chụp, ảnh đã đính)."""
    s = selectors()
    page.goto(fb_url(target_url), wait_until="domcontentloaded", timeout=60000)
    page.wait_for_timeout(3500)
    _check_blocked(page)
    opened = _wait_click(page, composer_labels, timeout=20)
    if not opened and post.get("target_type") == "profile":
        page.goto(FB_BASE, wait_until="domcontentloaded", timeout=60000)  # trang cá nhân không có ô viết: thử bảng tin
        page.wait_for_timeout(3500)
        opened = _wait_click(page, composer_labels, timeout=15)
    if not opened:
        if _visible_first(page, s.get("join_button", [])):
            raise RuntimeError("Nick chưa là thành viên nhóm này (còn nút Tham gia nhóm). Mở Chrome của sale và tham gia nhóm trước")
        if _visible_first(page, s.get("pending_join", [])):
            raise RuntimeError("Nick đang chờ quản trị viên duyệt vào nhóm, chưa đăng được")
        raise RuntimeError("Không tìm thấy ô viết bài. Nút đang thấy: " + (_labels_on(page) or "không có")
                           + ". Thêm chữ của ô viết bài vào fb_selectors.json")
    dialog, box = _composer_dialog(page)
    if not dialog:
        raise RuntimeError("Đã bấm ô viết bài nhưng không thấy hộp soạn bài hiện ra. Nút đang thấy: " + _labels_on(page))
    text = post["content"].rstrip() + ("\n\n" + post["hashtags"] if post.get("hashtags") else "")
    _type_text(page, box, text)
    _pause(page)
    used = []
    if imgs:
        try:
            used = _attach_images(page, dialog, [str(i) for i in imgs], s["photo_button"])
        except Exception as e:
            db.log("tuan", "Không đính được ảnh", f"Bài #{post['id']}: {str(e).splitlines()[0][:150]}. Vẫn đăng phần chữ.")
            used = []
        if not used:
            db.log("tuan", "Không đính được ảnh", f"Bài #{post['id']}: không thấy ô chọn ảnh trong hộp soạn bài, đăng phần chữ.")
    shot = db.SHOTS_DIR / f"post-{post['id']}.png"
    if dry_run:
        page.screenshot(path=str(shot))
        page.keyboard.press("Escape")
        page.wait_for_timeout(1200)
        _wait_click(page, s["discard_button"], timeout=4)
        return f"/shots/{shot.name}", used
    # Bấm Đăng; giao diện mới có thể hiện "Tiếp" trước (chọn đối tượng, cài đặt bài viết) rồi mới tới "Đăng"
    posted = False
    for _step in range(3):
        end = time.time() + 30
        btn = nxt = None
        while time.time() < end:
            btn, nxt = _find_submit(page, s)
            target = btn or nxt
            if target and target.get_attribute("aria-disabled") != "true":
                break
            page.wait_for_timeout(800)
        target = btn or nxt
        if not target:
            raise RuntimeError("Không tìm thấy nút Đăng trong hộp soạn bài. Nút đang thấy: " + _labels_on(_top_dialog(page) or page))
        if target.get_attribute("aria-disabled") == "true":
            raise RuntimeError("Nút Đăng vẫn bị mờ sau 30 giây (ảnh chưa tải xong hoặc nội dung chưa điền được)")
        target.click()
        if btn:
            posted = True
            break
        page.wait_for_timeout(2500)  # vừa bấm Tiếp, chờ bước sau hiện ra
    if not posted:
        raise RuntimeError("Bấm Tiếp nhiều lần nhưng không tới được nút Đăng")
    try:
        btn.wait_for(state="hidden", timeout=90000)
    except Exception:
        page.screenshot(path=str(shot))
        raise RuntimeError("Đã bấm Đăng nhưng hộp soạn bài chưa đóng sau 90 giây (mạng chậm hoặc Facebook chặn)")
    page.wait_for_timeout(4000)
    _check_blocked(page)
    page.screenshot(path=str(shot))
    return f"/shots/{shot.name}", used


# ---------------------------------------------------------------- công việc
def _set_login(sale_id: int, status: str, err: str = ""):
    db.run("UPDATE sales SET login_status=?, last_check_at=?, last_error=? WHERE id=?",
           (status, db.now(), err, sale_id))


def _job_open(pw, sale_id: int, minutes: int = 30):
    """Mở Chrome để sếp đăng nhập / vào nhóm; đóng cửa sổ là xong."""
    ctx, page = _open(pw, sale_id, headless=False)
    try:
        page.goto(FB_BASE, wait_until="domcontentloaded")
    except Exception as e:
        if not is_closed_error(e):  # sếp tự đóng cửa sổ ngay: không phải lỗi
            raise
    end = time.time() + minutes * 60
    was = None
    while time.time() < end:
        try:
            if not ctx.pages:
                break
            ok = _logged_in(ctx)
            if ok != was:
                _set_login(sale_id, "ok" if ok else "not_logged_in")
                if ok:
                    db.log(f"sale-{sale_id}", "Đăng nhập", "Phiên Facebook đã được lưu trong hồ sơ Chrome")
                was = ok
            time.sleep(2)
        except Exception:
            break
    try:
        ok = _logged_in(ctx)
        _set_login(sale_id, "ok" if ok else "not_logged_in")
        ctx.close()
    except Exception:
        pass


def _job_check(pw, sale_id: int):
    ctx, page = _open(pw, sale_id)
    try:
        if not _logged_in(ctx):
            _set_login(sale_id, "not_logged_in", "Chưa đăng nhập Facebook trong hồ sơ này")
            return
        page.goto(FB_BASE, wait_until="domcontentloaded", timeout=60000)
        page.wait_for_timeout(3000)
        _check_blocked(page)
        _set_login(sale_id, "ok")
    except Blocked as e:
        _block(sale_id, str(e))
    finally:
        ctx.close()


def _block(sale_id: int, reason: str):
    import errors
    s = db.one("SELECT name, fb_name FROM sales WHERE id=?", (sale_id,)) or {}
    errors.report("nick", f"Nick {s.get('fb_name') or s.get('name') or sale_id} bị Facebook chặn hoặc kiểm tra", reason,
                  screen="sales", ref_type="sale", ref_id=sale_id)
    _set_login(sale_id, "checkpoint", reason)
    db.run("UPDATE sales SET auto_post=0 WHERE id=?", (sale_id,))
    db.run("UPDATE posts SET status='approved', sale_id=NULL, scheduled_for=NULL WHERE sale_id=? AND status='scheduled'",
           (sale_id,))
    db.log("tuan", "Nick gặp sự cố", f"Sale #{sale_id}: {reason}. Đã dừng tự đăng và trả các bài chờ về hàng đợi.")
    try:
        import telegram_bot
        telegram_bot.alert_nick(sale_id, reason)
    except Exception as e:
        print("[telegram]", e)


def _job_post(pw, sale_id: int, post_id: int, dry_run: bool):
    post = db.one("""SELECT p.*, g.url group_url, g.name group_name FROM posts p
                     LEFT JOIN groups g ON g.id=p.group_id WHERE p.id=?""", (post_id,))
    sale = db.one("SELECT * FROM sales WHERE id=?", (sale_id,))
    if not post or not sale:
        return
    aid = f"sale-{sale_id}"
    where = post.get("group_name") or "trang cá nhân"
    workflows.set_status(aid, "working", f"{'Đăng thử' if dry_run else 'Đang đăng'} bài vào {where}")
    if not dry_run:
        db.run("UPDATE posts SET status='posting', error=NULL WHERE id=?", (post_id,))
    ctx, page = _open(pw, sale_id)
    try:
        if not _logged_in(ctx):
            _set_login(sale_id, "not_logged_in", "Phiên đăng nhập đã hết, cần đăng nhập lại")
            raise RuntimeError("Nick chưa đăng nhập. Vào Nhân viên sale → Mở Chrome để đăng nhập lại")
        if post["target_type"] == "group":
            if not post.get("group_url"):
                raise RuntimeError(f"Nhóm “{post.get('group_name') or ''}” chưa có link. Vào Hội nhóm, bấm “Thêm link” ở dòng nhóm này "
                                   "rồi bấm Đăng lại")
            url, labels = fb_url(post["group_url"]), selectors()["group_composer"]
        else:
            url, labels = f"{FB_BASE}/me", selectors()["profile_composer"]
        imgs, warn = media_folder.pick_for_post(post, sale_id)
        if warn:
            db.log("tuan", "Thiếu ảnh mới", f"Bài #{post_id}: {warn}")
        shot, attached = _publish(page, post, url, labels, dry_run, imgs)
        if post["target_type"] == "group" and "/share/" in url:  # link chia sẻ: lưu lại link nhóm thật sau khi mở
            real, err = check_group_url(page.url)
            if not err and "/groups/" in real:
                db.run("UPDATE groups SET url=? WHERE id=?", (real, post["group_id"]))
        imgs = [i for i in imgs if str(i) in attached]
        used = json.dumps([str(i) for i in imgs], ensure_ascii=False)
        if dry_run:
            db.run("UPDATE posts SET screenshot=?, error=NULL, images_used=? WHERE id=?", (shot, used, post_id))
            db.log(aid, "Đăng thử", f"Bài #{post_id}: điền nội dung thành công ở {where} (chưa bấm Đăng)")
        else:
            workflows.mark_posted(post_id, url, f"{sale['name']} (tự động)")
            db.run("UPDATE posts SET screenshot=?, images_used=? WHERE id=?", (shot, used, post_id))
            media_folder.record(imgs, "post", post, sale_id)
            db.run("UPDATE sales SET last_post_at=?, last_error=NULL WHERE id=?", (db.now(), sale_id))
            _set_login(sale_id, "ok")
            workflows.set_status(aid, "working", "Đang lấy link bài vừa đăng")
            link, st = _capture_link(page, post)
            note = {"found": "đã lưu link bài", "pending": "bài đang chờ nhóm duyệt, sẽ lấy link sau",
                    "not_found": "chưa lấy được link, sẽ thử lại khi up bài"}[st]
            db.log(aid, "Đã đăng", f"Bài #{post_id} lên {where}, {note}")
    except Blocked as e:
        _fail(page, post_id, str(e), dry_run)
        _block(sale_id, str(e))
    except Exception as e:
        _fail(page, post_id, friendly(e)[:300], dry_run)
        if "chưa là thành viên" in str(e) and post.get("group_id"):
            import group_finder
            group_finder.mark_not_member(post["group_id"], sale_id)
        db.log(aid, "Lỗi đăng bài", f"Bài #{post_id}: {str(e).splitlines()[0][:200]}")
    finally:
        try:
            ctx.close()
        except Exception:
            pass
        workflows.set_status(aid, "idle", "Chờ lịch đăng tiếp theo")


# ---------------------------------------------------------------- lấy link bài
PERMA_RX = re.compile(r"(/groups/[^/?#]+/(posts|permalink)/[\w]+|/posts/(pfbid\w+|\d+)|story_fbid=|/permalink\.php|/photo/\?fbid=)")


def _norm(t: str) -> str:
    return re.sub(r"[^\w]+", " ", (t or "").lower()).strip()


def _snippet(content: str) -> str:
    first = next((ln for ln in content.splitlines() if len(_norm(ln)) >= 12), content)
    return _norm(first)[:45]


def _clean_link(h: str) -> str:
    from urllib.parse import parse_qs, urlencode, urljoin, urlparse
    u = urlparse(urljoin(FB_BASE + "/", h))
    if "permalink.php" in u.path or "story_fbid" in u.query:
        q = parse_qs(u.query)
        keep = {k: q[k][0] for k in ("story_fbid", "id") if k in q}
        return f"{u.scheme}://{u.netloc}{u.path}?{urlencode(keep)}"
    return f"{u.scheme}://{u.netloc}{u.path}".rstrip("/")


def _find_permalink(page, post: dict) -> tuple[str | None, str]:
    """Tìm bài vừa đăng trong 'Nội dung của bạn' của nhóm (hoặc trang cá nhân), trích link thật."""
    s = selectors()
    snip = _snippet(post["content"])
    if post["target_type"] == "group" and post.get("group_url"):
        base = fb_url(post["group_url"]).rstrip("/")
        pages = [base + p for p in s.get("my_posts_paths", ["/my_posted_content", ""])]
    else:
        pages = [f"{FB_BASE}/me"]
    for u in pages:
        page.goto(u, wait_until="domcontentloaded", timeout=60000)
        page.wait_for_timeout(3000)
        _check_blocked(page)
        for _ in range(4):
            arts = page.locator('[role="article"]')
            for i in range(min(arts.count(), 15)):
                a = arts.nth(i)
                try:
                    if snip not in _norm(a.inner_text(timeout=3000)):
                        continue
                    hrefs = a.locator("a[href]").evaluate_all("els => els.map(e => e.href)")
                except Exception:
                    continue
                for h in hrefs:
                    if PERMA_RX.search(h):
                        return _clean_link(h), "found"
            page.mouse.wheel(0, 2400)
            page.wait_for_timeout(1500)
    if post["target_type"] == "group" and post.get("group_url"):
        for pth in s.get("pending_paths", []):
            page.goto(fb_url(post["group_url"]).rstrip("/") + pth, wait_until="domcontentloaded", timeout=60000)
            page.wait_for_timeout(2500)
            if snip in _norm(page.inner_text("body")):
                return None, "pending"
    return None, "not_found"


def _capture_link(page, post: dict) -> tuple[str | None, str]:
    try:
        link, st = _find_permalink(page, post)
    except Blocked:
        raise
    except Exception as e:
        print("[permalink]", e)
        link, st = None, "not_found"
    if link:
        db.run("UPDATE posts SET posted_url=?, permalink_status='found' WHERE id=?", (link, post["id"]))
    else:
        db.run("UPDATE posts SET permalink_status=? WHERE id=?", (st, post["id"]))
    return link, st


# ---------------------------------------------------------------- quét bình luận tìm khách, xin SĐT
TIME_RX = re.compile(r"^(\d+\s*(giây|phút|giờ|ngày|tuần|tháng|năm|s|m|h|d|w|y|min|mins|hr|hrs)|vừa xong|just now)$", re.I)


def _replies_today(sale_id: int) -> int:
    return db.one("SELECT COUNT(*) n FROM comment_seen WHERE sale_id=? AND replied=1 AND created_at LIKE ?",
                  (sale_id, db.today() + "%"))["n"]


def _parse_comment(art, s: dict, label: str) -> tuple[str, str] | None:
    author = ""
    try:
        for t in art.locator("a").evaluate_all("els => els.map(e => (e.innerText||'').trim()).filter(Boolean)")[:3]:
            if not TIME_RX.match(t) and len(t) <= 60:
                author = t
                break
    except Exception:
        pass
    if not author:
        for pre in s["comment_labels"]:
            if label.lower().startswith(pre.lower()):
                author = re.split(r"\s+\d", label[len(pre):].strip())[0][:60]
    ui = {w.lower() for w in s["comment_ui_words"]}
    lines = [ln.strip() for ln in (art.inner_text(timeout=3000) or "").splitlines()]
    lines = [ln for ln in lines if ln and ln != author and ln.lower() not in ui and not TIME_RX.match(ln) and not re.fullmatch(r"[\d.,]+", ln)]
    text = " ".join(lines).strip()
    return (author or "Khách Facebook", text) if text else None


def _scan_comments(page, post: dict, sale: dict) -> dict:
    """Đọc bình luận trên bài của chính nick này, tạo khách, trả lời xin SĐT (có giới hạn)."""
    s = selectors()
    st = db.get_settings()
    found = {"comments": 0, "leads": 0, "phones": 0, "asked": 0}
    for _ in range(3):  # mở thêm bình luận cũ
        more = _visible_first(page, s["more_comments"])
        if not more:
            break
        try:
            more.click()
            page.wait_for_timeout(1800)
        except Exception:
            break
    own = {x.strip().lower() for x in (sale.get("fb_name"), sale.get("name")) if x}
    ours = [t.strip().lower()[:40] for t in (st.get("reply_texts", "") + "\n" + st.get("bump_texts", "")).splitlines() if t.strip()]
    arts = page.locator('[role="article"][aria-label]')
    items = []
    for i in range(min(arts.count(), 60)):
        a = arts.nth(i)
        try:
            label = a.get_attribute("aria-label") or ""
            if not any(label.lower().startswith(p.lower()) for p in s["comment_labels"]):
                continue
            parsed = _parse_comment(a, s, label)
        except Exception:
            continue
        if parsed:
            items.append((a, *parsed))
    max_reply = int(st.get("reply_max_per_nick") or 10)
    texts = [t.strip() for t in (st.get("reply_texts") or "").splitlines() if t.strip()]
    for art, author, text in items:
        if author.strip().lower() in own or any(text.lower().startswith(o) for o in ours):
            continue
        found["comments"] += 1
        h = hashlib.md5(text.lower().encode("utf-8")).hexdigest()[:16]
        if db.one("SELECT id FROM comment_seen WHERE post_id=? AND author=? AND text_hash=?", (post["id"], author, h)):
            continue
        lead_id, is_new, got_phone = (None, False, False)
        if kpi.is_interested(text):
            lead_id, is_new, got_phone = kpi.upsert_lead(author, text, post["id"], author)
            found["leads"] += int(is_new)
            found["phones"] += int(got_phone or (is_new and bool(kpi.norm_phone(text))))
        cid = db.run("INSERT OR IGNORE INTO comment_seen(post_id, author, text_hash, lead_id, sale_id, created_at) VALUES (?,?,?,?,?,?)",
                     (post["id"], author, h, lead_id, sale["id"], db.now()))
        lead = db.one("SELECT phone FROM leads WHERE id=?", (lead_id,)) if lead_id else None
        if (lead_id and not (lead or {}).get("phone") and st.get("auto_reply_comments") == "1" and texts
                and _replies_today(sale["id"]) < max_reply
                and not db.one("SELECT id FROM comment_seen WHERE lead_id=? AND replied=1", (lead_id,))):
            try:
                btn = _visible_first(art, s["reply_button"])
                if btn:
                    _pause(page, 6, 14)
                    btn.click()
                    page.wait_for_timeout(1200)
                    page.keyboard.insert_text(random.choice(texts))
                    _pause(page)
                    page.keyboard.press("Enter")
                    page.wait_for_timeout(2500)
                    db.run("UPDATE comment_seen SET replied=1 WHERE id=?", (cid,))
                    found["asked"] += 1
            except Exception as e:
                print("[reply]", e)
    db.run("UPDATE posts SET last_scan_at=? WHERE id=?", (db.now(), post["id"]))
    if found["leads"] or found["phones"] or found["asked"]:
        db.log(f"sale-{sale['id']}", "Quét bình luận",
               f"Bài #{post['id']}: {found['leads']} khách mới, {found['phones']} SĐT, đã xin SĐT {found['asked']} người")
    kpi.check_escalations()
    return found


def _job_scan(pw, sale_id: int, post_ids: list[int]):
    sale = db.one("SELECT * FROM sales WHERE id=?", (sale_id,))
    if not sale:
        return
    aid = f"sale-{sale_id}"
    workflows.set_status(aid, "working", f"Đang đọc bình luận {len(post_ids)} bài để tìm khách")
    ctx, page = _open(pw, sale_id)
    total = {"leads": 0, "phones": 0, "asked": 0}
    try:
        if not _logged_in(ctx):
            _set_login(sale_id, "not_logged_in", "Phiên đăng nhập đã hết, cần đăng nhập lại")
            return
        for pid in post_ids:
            post = db.one("SELECT * FROM posts WHERE id=?", (pid,))
            if not post or post.get("permalink_status") != "found":
                continue
            page.goto(post["posted_url"], wait_until="domcontentloaded", timeout=60000)
            page.wait_for_timeout(3000)
            _check_blocked(page)
            body = page.inner_text("body").lower()
            if any(t.lower() in body for t in selectors()["removed_texts"]):
                db.run("UPDATE posts SET permalink_status='removed', bump_enabled=0 WHERE id=?", (pid,))
                continue
            r = _scan_comments(page, post, sale)
            for k in total:
                total[k] += r[k]
            _pause(page, 4, 9)
    except Blocked as e:
        _block(sale_id, str(e))
    except Exception as e:
        db.log(aid, "Lỗi quét bình luận", str(e).splitlines()[0][:160])
        import errors
        errors.report_exc("scan", f"Sale #{sale_id} quét bình luận bị lỗi", e, screen="kpi", ref_type="sale", ref_id=sale_id)
    finally:
        try:
            ctx.close()
        except Exception:
            pass
        workflows.set_status(aid, "idle", f"Quét xong: {total['leads']} khách mới, {total['phones']} SĐT")


# ---------------------------------------------------------------- up bài: bình luận ảnh sản phẩm
def _bump_done(bump_id: int, status: str, err: str | None = None, shot: str | None = None, image: str | None = None):
    if status == "failed":
        import errors
        b = db.one("SELECT post_id FROM bumps WHERE id=?", (bump_id,)) or {}
        errors.report("bump", f"Up bài #{b.get('post_id') or '?'} bị lỗi", err or "", screen="posts",
                      ref_type="post", ref_id=b.get("post_id"), screenshot=shot)
    db.run("UPDATE bumps SET status=?, error=?, screenshot=COALESCE(?, screenshot), image=COALESCE(?, image), done_at=? WHERE id=?",
           (status, err, shot, image, db.now(), bump_id))


def _job_bump(pw, sale_id: int, bump_id: int):
    b = db.one("SELECT * FROM bumps WHERE id=?", (bump_id,))
    post = db.one("""SELECT p.*, g.url group_url, g.name group_name FROM posts p
                     LEFT JOIN groups g ON g.id=p.group_id WHERE p.id=?""", (b["post_id"],)) if b else None
    if not b or not post:
        return
    aid = f"sale-{sale_id}"
    where = post.get("group_name") or "trang cá nhân"
    img = media_folder.pick(post)
    if not img:
        _bump_done(bump_id, "failed", "Thư mục ảnh trống hoặc chưa cài. Vào Cài đặt → Up bài để chọn thư mục")
        return
    workflows.set_status(aid, "working", f"Đang up bài ở {where}")
    ctx, page = _open(pw, sale_id)
    shot = db.SHOTS_DIR / f"bump-{bump_id}.png"
    try:
        if not _logged_in(ctx):
            _set_login(sale_id, "not_logged_in", "Phiên đăng nhập đã hết, cần đăng nhập lại")
            raise RuntimeError("Nick chưa đăng nhập")
        link = post["posted_url"] if post.get("permalink_status") == "found" else None
        if not link:
            link, st = _capture_link(page, post)
            if not link:
                _bump_done(bump_id, "skipped", "Bài đang chờ nhóm duyệt" if st == "pending" else
                           "Chưa lấy được link bài. Dán link vào thẻ bài ở mục Bài đăng để sale up được")
                return
        s = selectors()
        page.goto(link, wait_until="domcontentloaded", timeout=60000)
        page.wait_for_timeout(3500)
        _check_blocked(page)
        body = page.inner_text("body").lower()
        m = re.search(r"(\d[\d.,]*)\s*(bình luận|comments?)\b", body)
        if m:  # số bình luận thật -> dữ liệu cho cả đội học
            n = int(re.sub(r"[^\d]", "", m.group(1)) or 0)
            db.run("UPDATE posts SET comments=MAX(COALESCE(comments,0), ?) WHERE id=?", (n, post["id"]))
        if not any(t.lower() in body for t in s["removed_texts"]):
            try:
                _scan_comments(page, post, db.one("SELECT * FROM sales WHERE id=?", (sale_id,)))
            except Blocked:
                raise
            except Exception as e:
                print("[scan]", e)
                import errors
                errors.report_exc("scan", f"Quét bình luận bài #{post['id']} bị lỗi", e, screen="kpi")
        if any(t.lower() in body for t in s["removed_texts"]):
            db.run("UPDATE posts SET permalink_status='removed', bump_enabled=0 WHERE id=?", (post["id"],))
            _bump_done(bump_id, "skipped", "Bài đã bị xóa hoặc ẩn, đã ngừng up bài này")
            db.log(aid, "Bài bị gỡ", f"Bài #{post['id']} ở {where} không còn hiển thị, ngừng up")
            return
        box = None
        end = time.time() + 15
        while not box and time.time() < end:
            box = _visible_first(page, s["comment_box"], role="textbox")
            if not box:
                page.mouse.wheel(0, 600)
                page.wait_for_timeout(800)
        if not box:
            raise RuntimeError("Không tìm thấy ô bình luận. Thêm chữ hiển thị mới vào comment_box trong fb_selectors.json")
        box.click()
        _pause(page)
        text = (b.get("text") or "").strip()
        if text:
            page.keyboard.insert_text(text)
        attached = False
        btn = _visible_first(page, s["comment_attach"])
        if btn:
            try:
                with page.expect_file_chooser(timeout=8000) as fc:
                    btn.click()
                fc.value.set_files(str(img))
                attached = True
            except Exception:
                pass
        if not attached:
            inp = page.locator('input[type="file"][accept*="image"]')
            if inp.count():
                inp.last.set_input_files(str(img))
                attached = True
        if not attached:
            raise RuntimeError("Không đính kèm được ảnh vào bình luận (thêm chữ nút đính kèm vào comment_attach)")
        page.wait_for_timeout(4000)
        box.click()
        page.keyboard.press("Enter")
        page.wait_for_timeout(5000)
        _check_blocked(page)
        page.screenshot(path=str(shot))
        _bump_done(bump_id, "done", None, f"/shots/{shot.name}", str(img))
        media_folder.record([img], "bump", post, sale_id, bump_id)
        db.run("UPDATE posts SET bump_count=COALESCE(bump_count,0)+1, last_bump_at=? WHERE id=?", (db.now(), post["id"]))
        db.log(aid, "Up bài", f"Bình luận ảnh {img.name} vào bài #{post['id']} ở {where}")
        import learning
        learning.award(aid, 1, "Up bài")
    except Blocked as e:
        _bump_done(bump_id, "failed", str(e))
        _block(sale_id, str(e))
        db.run("UPDATE bumps SET status='skipped', error='Nick bị dừng' WHERE sale_id=? AND status='scheduled'", (sale_id,))
    except Exception as e:
        try:
            page.screenshot(path=str(shot))
        except Exception:
            pass
        _bump_done(bump_id, "failed", str(e).splitlines()[0][:300], f"/shots/{shot.name}" if shot.exists() else None, str(img))
        db.log(aid, "Lỗi up bài", f"Bài #{post['id']}: {str(e).splitlines()[0][:160]}")
    finally:
        try:
            ctx.close()
        except Exception:
            pass
        workflows.set_status(aid, "idle", "Chờ lịch tiếp theo")


def _fail(page, post_id: int, msg: str, dry_run: bool):
    shot = db.SHOTS_DIR / f"post-{post_id}-error.png"
    try:
        page.screenshot(path=str(shot))
        rel = f"/shots/{shot.name}"
    except Exception:
        rel = None
    import errors
    p = db.one("SELECT p.*, g.name group_name, s.name sale_name FROM posts p LEFT JOIN groups g ON g.id=p.group_id "
               "LEFT JOIN sales s ON s.id=p.sale_id WHERE p.id=?", (post_id,)) or {}
    where = p.get("group_name") or {"profile": "trang cá nhân"}.get(p.get("target_type"), "")
    errors.report("post", f"{'Đăng thử' if dry_run else 'Đăng'} bài #{post_id}{' vào ' + where if where else ''} bị lỗi",
                  msg, f"Nick: {p.get('sale_name') or '?'} · Bài: {(p.get('title') or '')[:80]}", screen="posts",
                  ref_type="post", ref_id=post_id, screenshot=rel)
    db.run(f"UPDATE posts SET {'status=' + repr('failed') + ',' if not dry_run else ''} error=?, screenshot=? WHERE id=?",
           (msg, rel, post_id))


JOB_NAME = {"open": "mở Chrome", "check": "kiểm tra phiên", "post": "đăng bài", "bump": "up bài", "scan": "quét bình luận",
            "discover": "tìm nhóm mới", "join": "xin vào nhóm"}


def _worker(sale_id: int, q: Queue):
    from playwright.sync_api import sync_playwright
    while True:
        job = q.get()
        _busy[sale_id] = job.get("kind", "")
        try:
            with sync_playwright() as pw:
                if job["kind"] == "open":
                    _job_open(pw, sale_id)
                elif job["kind"] == "check":
                    _job_check(pw, sale_id)
                elif job["kind"] == "post":
                    _job_post(pw, sale_id, job["post_id"], job.get("dry_run", False))
                elif job["kind"] == "bump":
                    _job_bump(pw, sale_id, job["bump_id"])
                elif job["kind"] == "scan":
                    _job_scan(pw, sale_id, job["post_ids"])
                elif job["kind"] == "discover":
                    import group_finder
                    group_finder.job_discover(pw, sale_id, job["keywords"], job.get("notify"))
                elif job["kind"] == "join":
                    import group_finder
                    group_finder.job_join(pw, sale_id, job.get("notify"))
        except Exception as e:
            traceback.print_exc()
            msg = friendly(e)
            if job["kind"] == "open" and is_closed_error(e):
                continue  # sếp tự đóng cửa sổ Chrome vừa mở: không phải lỗi
            db.log(f"sale-{sale_id}", "Lỗi trình duyệt", msg[:200])
            import errors
            s = db.one("SELECT name FROM sales WHERE id=?", (sale_id,)) or {}
            eid = errors.report_exc("browser", f"Chrome của sale {s.get('name') or '#' + str(sale_id)} lỗi khi "
                                    f"{JOB_NAME.get(job['kind'], job['kind'])}", e, screen="sales", ref_type="sale", ref_id=sale_id)
            if eid and msg != str(e).strip().splitlines()[0]:
                db.run("UPDATE errors SET message=? WHERE id=?", (msg[:1000], eid))
            if job["kind"] == "check":
                db.run("UPDATE sales SET last_error=? WHERE id=?", (msg[:300], sale_id))
            if job.get("notify"):  # việc CEO giao theo lệnh sếp: báo lại là không làm được
                import ceo_orders
                ceo_orders.followup(f"{s.get('name') or 'Sale'} chưa {JOB_NAME.get(job['kind'], job['kind'])} được: {msg[:200]}. "
                                    "Chi tiết ở mục Lỗi.", job["notify"])
            if job["kind"] == "bump":
                db.run("UPDATE bumps SET status='failed', error=? WHERE id=? AND status='running'",
                       (msg[:300], job["bump_id"]))
            if job["kind"] == "post" and not job.get("dry_run"):
                db.run("UPDATE posts SET status='failed', error=? WHERE id=? AND status='posting'",
                       (msg[:300], job["post_id"]))
        finally:
            _busy.pop(sale_id, None)
            q.task_done()

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

import accounts
import db
import kpi
import media_folder
import workflows

FB_BASE = os.getenv("FB_BASE_URL", "https://www.facebook.com").rstrip("/")
SEL_FILE = Path(__file__).resolve().parent / "fb_selectors.json"

_queues: dict[int, Queue] = {}
_busy: dict[int, str] = {}
_busy_acc: dict[int, int] = {}  # sale_id -> nick đang mở Chrome
_lock = threading.Lock()


class Blocked(Exception):
    """Tài khoản bị checkpoint / khóa / đăng xuất."""


def selectors() -> dict:
    return json.loads(SEL_FILE.read_text(encoding="utf-8"))


def profile_dir(aid: int) -> Path:
    """Hồ sơ Chrome của một nick Facebook."""
    return accounts.profile_path(aid)


def sale_of(aid: int) -> int | None:
    a = accounts.get(aid)
    return a["sale_id"] if a else None


def busy(sale_id: int) -> str | None:
    return _busy.get(sale_id)


def busy_account(sale_id: int) -> int | None:
    return _busy_acc.get(sale_id)


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
BROWSER_MODES = {"background": "Chạy ngầm (cửa sổ nằm ngoài màn hình)", "show": "Hiện cửa sổ để xem sale làm",
                 "headless": "Ẩn hoàn toàn (không có cửa sổ)"}
# Chrome tự giảm tốc tab bị che / nằm ngoài màn hình / không được chú ý: tắt để sale vẫn thao tác đều khi sếp dùng máy việc khác
NO_THROTTLE = ["--disable-backgrounding-occluded-windows", "--disable-renderer-backgrounding",
               "--disable-background-timer-throttling"]


def browser_mode() -> str:
    st = db.get_settings()
    if st.get("browser_headless") == "1":
        return "headless"
    m = st.get("browser_mode") or "background"
    return m if m in BROWSER_MODES else "background"


def _launch(pw, aid: int, headless: bool | None = None):
    """headless=None: theo cài đặt Chế độ Chrome. headless=False: luôn hiện cửa sổ (đăng nhập, mở hồ sơ cho sale bấm)."""
    args = ["--disable-notifications", *NO_THROTTLE]
    if headless is None:
        mode = browser_mode()
        headless = mode == "headless"
        if mode == "background":
            # Chrome thật có cửa sổ, chỉ đặt ra ngoài vùng màn hình: sếp không thấy, không bị giành chuột / bàn phím
            # (phần mềm điều khiển Chrome qua kênh riêng, không dùng chuột, bàn phím, khay nhớ tạm của máy)
            args += ["--window-position=-32000,-32000", "--window-size=1280,900"]
        elif mode == "show":
            args += ["--window-position=60,40"]  # Chrome nhớ vị trí cũ (có thể đang ngoài màn hình sau khi chạy ngầm)
    else:
        args += ["--window-position=60,40"]  # cửa sổ cần người thao tác: luôn hiện trên màn hình
    kw = dict(user_data_dir=str(profile_dir(aid)), headless=headless, locale="vi-VN",
              viewport={"width": 1280, "height": 900}, args=args)
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


def profile_in_use(aid: int) -> bool:
    """Có tiến trình Chrome khác đang giữ hồ sơ này không (mở cùng hồ sơ thì Chrome mới tự đóng ngay)."""
    d = profile_dir(aid)
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


def release_profile(aid: int) -> int:
    """Đóng các tiến trình Chrome còn treo đang giữ hồ sơ của sale (chỉ những tiến trình mở đúng thư mục hồ sơ này,
    không đụng tới Chrome cá nhân của sếp). Trả về số tiến trình đã đóng."""
    target = str(profile_dir(aid).resolve()).lower().replace("\\", "/")
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
        db.log(f"sale-{sale_of(aid)}", "Đóng Chrome bị treo", f"Đã đóng {killed} tiến trình Chrome cũ còn giữ hồ sơ của nick {accounts.label(accounts.get(aid) or {'id': aid})}")
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


def diagnose_closed(aid: int) -> str:
    """Giải thích vì sao Chrome của sale tự đóng ngay khi mở."""
    if profile_in_use(aid):
        return IN_USE_MSG
    try:
        prof = (profile_dir(aid) / "Last Version").read_text().strip()
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


def _open(pw, aid: int, headless: bool | None = None):
    """Mở Chrome của sale và một tab mới để làm việc. Tự thử lại 1 lần nếu Chrome bị đóng ngay khi mở."""
    if profile_in_use(aid):
        # việc của một sale chạy lần lượt, nên lúc này phần mềm không mở Chrome nào cho sale này:
        # hồ sơ bị giữ là do Chrome cũ còn treo (phần mềm từng tắt đột ngột) hoặc cửa sổ sếp tự mở -> đóng Chrome treo
        release_profile(aid)
        if profile_in_use(aid):
            raise RuntimeError(IN_USE_MSG)
    last = None
    for attempt in range(2):
        ctx = _launch(pw, aid, headless)
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
            release_profile(aid)
            time.sleep(4)
    raise RuntimeError(diagnose_closed(aid)) from last


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


PREVIEW_JS = """d => {
  // ảnh xem trước trong hộp soạn bài: <img> blob:/data:/ảnh tải lên, hoặc khối có ảnh nền blob:
  const imgs = [...d.querySelectorAll('img')].filter(i => /^(blob:|data:image)/.test(i.src || '') ||
      ((i.naturalWidth || i.width) >= 60 && !i.closest('[role="button"][aria-label]') && !/emoji|static\\.xx|rsrc\\.php/.test(i.src || '')));
  const bg = [...d.querySelectorAll('[style*="blob:"]')];
  const vids = [...d.querySelectorAll('video')];
  return imgs.length + bg.length + vids.length;
}"""
DROPZONE = ["Thêm ảnh/video", "Add photos/videos", "Thêm ảnh", "Add photos", "hoặc kéo và thả", "or drag and drop"]


def _preview_count(dialog) -> int:
    try:
        return dialog.evaluate(PREVIEW_JS)
    except Exception:
        return 0


def _wait_previews(page, dialog, base: int, want: int, timeout: float = 25) -> int:
    """Chờ Facebook hiện ảnh xem trước trong hộp soạn bài. Trả về số ảnh mới hiện."""
    end, got = time.time() + timeout, 0
    while time.time() < end:
        got = _preview_count(dialog) - base
        if got >= want:
            break
        page.wait_for_timeout(700)
    return max(0, got)


def _wait_uploaded(page, dialog, timeout: float = 120):
    """Chờ ảnh tải lên xong (hết thanh tiến trình) trước khi bấm Đăng."""
    end = time.time() + timeout
    while time.time() < end:
        try:
            busy = dialog.locator('[role="progressbar"]').count()
        except Exception:
            busy = 0
        if not busy:
            return True
        page.wait_for_timeout(800)
    return False


def _chooser(page, scope, labels: list[str], wait_ms: int = 5000):
    """Bấm nút (Ảnh/video, Thêm ảnh/video) và bắt hộp chọn tệp của Facebook. Trả về FileChooser hoặc None."""
    el = _visible_first(scope, labels) or _exact_button(scope, labels)
    if not el:
        return None, False
    try:
        with page.expect_file_chooser(timeout=wait_ms) as fc:
            el.click()
        return fc.value, True
    except Exception:
        return None, True  # đã bấm nhưng không mở hộp chọn tệp (có thể hiện ô “Thêm ảnh/video”)


def _attach_images(page, dialog, imgs: list[str], labels: list[str]) -> list[str]:
    """Đính ảnh vào hộp soạn bài như người dùng: bấm Ảnh/video, chọn tệp trong hộp chọn tệp của Facebook,
    rồi CHỜ ảnh xem trước hiện trong bài. Ảnh không hiện thì coi như chưa đính (trả về rỗng, không đăng)."""
    base = _preview_count(dialog)
    want = 1  # ít nhất 1 ảnh hiện ra; Facebook có thể gộp nhiều ảnh thành 1 khung xem trước
    # 1) Bấm Ảnh/video -> hộp chọn tệp (Facebook mới); hoặc hiện ô "Thêm ảnh/video" -> bấm tiếp
    fc, clicked = _chooser(page, dialog, labels)
    if not fc and clicked:
        page.wait_for_timeout(800)
        fc, _ = _chooser(page, dialog, DROPZONE)
    if fc:
        fc.set_files(imgs)
        if _wait_previews(page, dialog, base, want):
            _wait_uploaded(page, dialog)
            return list(imgs)
    # 2) Dự phòng: ô chọn tệp ảnh MỚI xuất hiện sau khi bấm Ảnh/video (trong hộp soạn hoặc gắn ngoài trang)
    if not clicked:
        el = _visible_first(dialog, labels)
        if el:
            el.click()
            page.wait_for_timeout(1500)
    loc = page.locator('input[type="file"]')
    cands = []
    for k in range(loc.count() - 1, -1, -1):  # ô mới nhất trước
        el = loc.nth(k)
        acc = (el.get_attribute("accept") or "").lower()
        if acc and "image" not in acc:
            continue
        cands.append(el)
    for el in cands[:4]:
        try:
            if el.get_attribute("multiple") is not None:
                el.set_input_files(imgs)
            else:
                el.set_input_files(imgs[0])
        except Exception:
            continue
        if _wait_previews(page, dialog, base, want, timeout=12):
            _wait_uploaded(page, dialog)
            return list(imgs) if el.get_attribute("multiple") is not None else [imgs[0]]
    return []


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
    used, why = [], ""
    if imgs:
        try:
            used = _attach_images(page, dialog, [str(i) for i in imgs], s["photo_button"])
        except Exception as e:
            why = str(e).splitlines()[0][:150]
            used = []
        if not used and not media_folder.required():
            db.log("tuan", "Không đính được ảnh", f"Bài #{post['id']}: {why or 'không thấy ô chọn ảnh trong hộp soạn bài'}, đăng phần chữ.")
    if not used and media_folder.required():  # sếp quy định: bài phải có ảnh -> hủy bài đang soạn, không bấm Đăng
        noimg_shot = None
        try:  # chụp lại hộp soạn bài để sếp xem Facebook đang hiện gì
            f = db.SHOTS_DIR / f"post-{post['id']}-noimg.png"
            page.screenshot(path=str(f))
            noimg_shot = f"/shots/{f.name}"
        except Exception:
            pass
        try:
            page.keyboard.press("Escape")
            page.wait_for_timeout(1200)
            _wait_click(page, s["discard_button"], timeout=4)
        except Exception:
            pass
        err = NoImage("Không đính được ảnh vào bài nên KHÔNG đăng (sếp quy định bài phải có ảnh). "
                      + (f"Lỗi: {why}. " if why else "Đã chọn ảnh nhưng Facebook không hiện ảnh trong bài (hoặc không thấy nút Ảnh/video). ")
                      + "Xem ảnh chụp hộp soạn bài; Facebook đổi chữ nút thì thêm vào photo_button trong fb_selectors.json")
        err.shot, err.attach = noimg_shot, True
        raise err
    shot = db.SHOTS_DIR / f"post-{post['id']}.png"
    if dry_run:
        page.screenshot(path=str(shot))
        page.keyboard.press("Escape")
        page.wait_for_timeout(1200)
        _wait_click(page, s["discard_button"], timeout=4)
        return f"/shots/{shot.name}", used
    # Bấm Đăng; giao diện mới có thể hiện "Tiếp" trước (chọn đối tượng, cài đặt bài viết) rồi mới tới "Đăng"
    caught, on_resp = _net_watch(page)  # nghe phản hồi của Facebook để lấy link bài vừa tạo
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
    try:
        page.remove_listener("response", on_resp)
        post["_net"] = _net_link(caught, post, page)
    except Exception as e:
        print("[net link]", e)
    _check_blocked(page)
    page.screenshot(path=str(shot))
    return f"/shots/{shot.name}", used


# ---------------------------------------------------------------- công việc
def _set_login(aid: int, status: str, err: str = ""):
    accounts.set_login(aid, status, err)


def _ctx_names(aid: int) -> tuple[dict, dict, str]:
    """(nick, sale, mã agent của sale) cho nhật ký và trạng thái nhân vật."""
    acc = accounts.get(aid) or {"id": aid, "name": f"Nick #{aid}", "sale_id": None}
    sale = db.one("SELECT * FROM sales WHERE id=?", (acc["sale_id"],)) or {"id": acc["sale_id"], "name": "Sale"}
    return acc, sale, f"sale-{sale['id']}"


def _job_open(pw, aid: int, minutes: int = 30, urls: list[str] | None = None):
    """Mở Chrome của một nick để sếp đăng nhập / vào nhóm; đóng cửa sổ là xong.
    urls: mở sẵn mỗi link một tab (vd. trang cá nhân người Tuấn gợi ý kết bạn, sale tự bấm Thêm bạn bè)."""
    acc, sale, agent = _ctx_names(aid)
    workflows.set_status(agent, "working", f"Mở Chrome nick {accounts.label(acc)} " +
                         (f"với {len(urls)} trang cá nhân chờ sale kết bạn" if urls else "chờ sếp đăng nhập"))
    ctx, page = _open(pw, aid, headless=False)
    try:
        page.goto(urls[0] if urls else FB_BASE, wait_until="domcontentloaded")
        for u in (urls or [])[1:10]:
            try:
                ctx.new_page().goto(u, wait_until="domcontentloaded")
            except Exception as e:
                if is_closed_error(e):
                    raise
                print("[open tab]", u, e)
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
                _set_login(aid, "ok" if ok else "not_logged_in")
                if ok:
                    db.log(agent, "Đăng nhập", f"Phiên Facebook của nick {accounts.label(acc)} đã được lưu trong hồ sơ Chrome")
                was = ok
            time.sleep(2)
        except Exception:
            break
    try:
        ok = _logged_in(ctx)
        _set_login(aid, "ok" if ok else "not_logged_in")
        ctx.close()
    except Exception:
        pass
    workflows.set_status(agent, "idle", "Chờ việc tiếp theo")


def _job_check(pw, aid: int):
    ctx, page = _open(pw, aid)
    try:
        if not _logged_in(ctx):
            _set_login(aid, "not_logged_in", "Chưa đăng nhập Facebook trong hồ sơ này")
            return
        page.goto(FB_BASE, wait_until="domcontentloaded", timeout=60000)
        page.wait_for_timeout(3000)
        _check_blocked(page)
        _set_login(aid, "ok")
    except Blocked as e:
        _block(aid, str(e))
    finally:
        ctx.close()


def _policy_hold(post: dict, aid: int, agent: str) -> bool:
    """Kiểm luật Facebook ngay trước khi đăng. Trả về True nếu phải hoãn / dừng bài này."""
    import fb_policy
    if not fb_policy.enabled():
        return False
    bad = fb_policy.blocking(fb_policy.check_text(post.get("content") or "", post["id"], aid))
    if bad:
        why = fb_policy.summary(bad)
        db.run("""UPDATE posts SET status='draft', sale_id=NULL, account_id=NULL, scheduled_for=NULL, review_ok=0, policy_note=?,
                  error=? WHERE id=?""", (why[:500], ("Không đăng vì phạm luật Facebook: " + why)[:300], post["id"]))
        db.log("tuan", "Giữ bài phạm luật Facebook", f"Bài #{post['id']}: {why[:300]}. Đưa về chờ duyệt để sửa.")
        return True
    ok, why, until = fb_policy.allow(aid, "post", post.get("group_id") if post.get("target_type") == "group" else None)
    if ok:
        return False
    if until:  # dời giờ đăng của nick này
        db.run("UPDATE posts SET status='scheduled', scheduled_for=?, error=? WHERE id=?",
               (until[:16], f"Hoãn theo luật Facebook: {why}"[:300], post["id"]))
    else:  # nhóm đang tạm ngừng: trả bài về hàng đợi cho nhóm khác
        db.run("UPDATE posts SET status='approved', sale_id=NULL, account_id=NULL, group_id=NULL, scheduled_for=NULL, error=? WHERE id=?",
               (f"Hoãn theo luật Facebook: {why}"[:300], post["id"]))
    db.log(agent, "Hoãn đăng theo luật Facebook", f"Bài #{post['id']}: {why}" + (f", dời tới {until[11:16]}" if until else ""))
    return True


def _block(aid: int, reason: str):
    """Nick bị checkpoint/khóa: dừng riêng nick đó (các nick khác của sale vẫn làm), trả bài của nick về hàng đợi."""
    import errors
    acc, sale, agent = _ctx_names(aid)
    errors.report("nick", f"Nick {accounts.label(acc)} (sale {sale.get('name')}) bị Facebook chặn hoặc kiểm tra", reason,
                  screen="sales", ref_type="account", ref_id=aid)
    _set_login(aid, "checkpoint", reason)
    db.run("UPDATE fb_accounts SET enabled=0 WHERE id=?", (aid,))
    accounts.sync_sale(acc["sale_id"]) if acc.get("sale_id") else None
    db.run("""UPDATE posts SET status='approved', sale_id=NULL, account_id=NULL, scheduled_for=NULL
              WHERE account_id=? AND status='scheduled'""", (aid,))
    db.run("UPDATE bumps SET status='skipped', error='Nick bị dừng' WHERE account_id=? AND status='scheduled'", (aid,))
    db.log("tuan", "Nick gặp sự cố", f"Nick {accounts.label(acc)} của {sale.get('name')}: {reason}. Đã dừng riêng nick này "
           "và trả các bài chờ về hàng đợi.")
    try:
        import fb_policy
        fb_policy.on_block(aid, reason)  # nghỉ, giảm giới hạn, rút kinh nghiệm
    except Exception as e:
        print("[fb policy]", e)
    try:
        import telegram_bot
        telegram_bot.alert_nick(aid, reason)
    except Exception as e:
        print("[telegram]", e)


def _do_post(ctx, page, aid: int, post_id: int, dry_run: bool):
    """Đăng (hoặc đăng thử) một bài bằng nick đang mở."""
    post = db.one("""SELECT p.*, g.url group_url, g.name group_name FROM posts p
                     LEFT JOIN groups g ON g.id=p.group_id WHERE p.id=?""", (post_id,))
    acc, sale, agent = _ctx_names(aid)
    if not post:
        return
    where = post.get("group_name") or "trang cá nhân"
    if not dry_run and _policy_hold(post, aid, agent):  # luật Facebook: nhịp đăng / nội dung chưa an toàn -> chưa đăng
        return
    workflows.set_status(agent, "working", f"{'Đăng thử' if dry_run else 'Đang đăng'} bài vào {where} (nick {accounts.label(acc)})")
    if not dry_run:
        db.run("UPDATE posts SET status='posting', error=NULL, account_id=?, sale_id=? WHERE id=?", (aid, acc["sale_id"], post_id))
    try:
        if not _logged_in(ctx):
            _set_login(aid, "not_logged_in", "Phiên đăng nhập đã hết, cần đăng nhập lại")
            raise RuntimeError(f"Nick {accounts.label(acc)} chưa đăng nhập. Vào Nhân viên sale → Mở Chrome nick này để đăng nhập lại")
        if post["target_type"] == "group":
            if not post.get("group_url"):
                raise RuntimeError(f"Nhóm “{post.get('group_name') or ''}” chưa có link. Vào Hội nhóm, bấm “Thêm link” ở dòng nhóm này "
                                   "rồi bấm Đăng lại")
            url, labels = fb_url(post["group_url"]), selectors()["group_composer"]
        else:
            url, labels = f"{FB_BASE}/me", selectors()["profile_composer"]
        imgs, warn = media_folder.pick_for_post(post, acc["sale_id"])
        if not imgs and media_folder.required():
            raise NoImage(media_folder.missing(post) or "Bài chưa chọn được ảnh nên không đăng (sếp quy định bài phải có ảnh)")
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
            db.log(agent, "Đăng thử", f"Bài #{post_id}: điền nội dung thành công ở {where} bằng nick {accounts.label(acc)} (chưa bấm Đăng)")
        else:
            workflows.mark_posted(post_id, url, f"{sale['name']} · nick {accounts.label(acc)} (tự động)")
            db.run("UPDATE posts SET screenshot=?, images_used=? WHERE id=?", (shot, used, post_id))
            media_folder.record(imgs, "post", post, acc["sale_id"])
            db.run("UPDATE fb_accounts SET last_post_at=?, last_error=NULL WHERE id=?", (db.now(), aid))
            db.run("UPDATE sales SET last_post_at=? WHERE id=?", (db.now(), acc["sale_id"]))
            _set_login(aid, "ok")
            workflows.set_status(agent, "working", "Đang lấy link bài vừa đăng")
            link, st = _capture_link(page, post, fresh=True)
            note = {"found": "đã lưu link bài", "pending": "bài đang chờ nhóm duyệt, sale sẽ tự lấy link khi bài được duyệt",
                    "not_found": "chưa lấy được link, sale sẽ tự thử lại sau 20 phút"}[st]
            db.log(agent, "Đã đăng", f"Bài #{post_id} lên {where} bằng nick {accounts.label(acc)}, {note}"
                   + (f": {link}" if st == "found" and link else ""))
    except Blocked as e:
        _fail(page, post_id, str(e), dry_run)
        _block(aid, str(e))
        raise
    except NoImage as e:
        _no_image(post, str(e), dry_run, agent, getattr(e, "shot", None), getattr(e, "attach", False))
    except Exception as e:
        _fail(page, post_id, friendly(e)[:300], dry_run)
        if "chưa là thành viên" in str(e) and post.get("group_id"):
            import group_finder
            group_finder.mark_not_member(post["group_id"], aid)
        db.log(agent, "Lỗi đăng bài", f"Bài #{post_id} (nick {accounts.label(acc)}): {str(e).splitlines()[0][:200]}")


def _job_post(pw, aid: int, post_id: int, dry_run: bool):
    acc, sale, agent = _ctx_names(aid)
    if not dry_run:
        db.run("UPDATE posts SET status='posting', error=NULL WHERE id=?", (post_id,))
    ctx, page = _open(pw, aid)
    try:
        _do_post(ctx, page, aid, post_id, dry_run)
    except Blocked:
        pass
    finally:
        try:
            ctx.close()
        except Exception:
            pass
        workflows.set_status(agent, "idle", "Chờ lịch đăng tiếp theo")


# ---------------------------------------------------------------- lấy link bài
PERMA_RX = re.compile(r"(/groups/[^/?#]+/(posts|permalink)/[\w]+|/posts/(pfbid\w+|\d+)|story_fbid=|/permalink\.php|"
                      r"/photo/\?fbid=|[?&]multi_permalinks=\d+|/share/p/\w+)")
PENDING_TEXTS = ["đang chờ phê duyệt", "đang chờ quản trị viên", "chờ quản trị viên phê duyệt", "pending approval", "is pending"]
# lấy lại link: chưa thấy bài thì thử lại sau 20 phút, 2 giờ, 6 giờ, 12 giờ, 24 giờ; bài chờ duyệt: 3 giờ một lần trong 3 ngày
LINK_RETRY_MIN = [20, 120, 360, 720, 1440]
PENDING_RETRY_MIN, PENDING_MAX_TRIES = 180, 24


def _norm(t: str) -> str:
    import unicodedata
    return re.sub(r"[^\w]+", " ", unicodedata.normalize("NFC", t or "").lower()).strip()


def _snippet(content: str) -> str:
    first = next((ln for ln in content.splitlines() if len(_norm(ln)) >= 12), content)
    return _norm(first)[:45]


def _snippets(content: str) -> list[str]:
    """2 đoạn chữ đầu đủ dài của bài để nhận ra bài trên Facebook (Facebook có thể cắt “Xem thêm”)."""
    out = [_norm(ln)[:45] for ln in content.splitlines() if len(_norm(ln)) >= 12][:2]
    return out or [_norm(content)[:45]]


def _clean_link(h: str) -> str:
    from urllib.parse import parse_qs, urlencode, urljoin, urlparse
    u = urlparse(urljoin(FB_BASE + "/", h))
    q = parse_qs(u.query)
    if "multi_permalinks" in q and "/groups/" in u.path:  # /groups/x/?multi_permalinks=123 -> /groups/x/posts/123
        g = u.path.split("/groups/")[1].split("/")[0]
        return f"{u.scheme}://{u.netloc}/groups/{g}/posts/{q['multi_permalinks'][0].split(',')[0]}"
    if "permalink.php" in u.path or "story_fbid" in u.query:
        keep = {k: q[k][0] for k in ("story_fbid", "id") if k in q}
        return f"{u.scheme}://{u.netloc}{u.path}?{urlencode(keep)}"
    return f"{u.scheme}://{u.netloc}{u.path}".rstrip("/")


# ---- 1) đọc link ngay trong phản hồi của Facebook lúc bấm Đăng (chắc chắn nhất)
NET_NAMES = ("ComposerStoryCreate", "StoryCreate", "GroupsCometComposer", "useCometComposer")


def _net_watch(page) -> tuple[list, callable]:
    """Nghe phản hồi tạo bài; đọc nội dung ngay khi về (trang có thể tải lại sau khi đăng làm mất nội dung)."""
    caught = []

    def on_resp(r):
        try:
            if "graphql" not in r.url and "/api/" not in r.url:
                return
            req = r.request
            name = (req.headers.get("x-fb-friendly-name") or "") + " " + (req.post_data or "")[:3000]
            if any(n in name for n in NET_NAMES):
                caught.append(r.text())
        except Exception as e:
            print("[net]", e)
    page.on("response", on_resp)
    return caught, on_resp


def _net_link(caught: list, post: dict, page) -> tuple[str | None, bool]:
    """(link, chờ duyệt?) từ phản hồi tạo bài của Facebook."""
    pending = False
    for body in caught:
        body = body.replace("\\/", "/")
        if re.search(r'"(is_)?pending[_a-z]*"\s*:\s*true|pending_post|PENDING', body):
            pending = True
        for m in re.finditer(r'"(?:url|permalink_url|wwwURL)"\s*:\s*"([^"]+)"', body):
            u = m.group(1)
            if PERMA_RX.search(u):
                return _clean_link(u), pending
        m = re.search(r'"(?:legacy_story_hideable_id|post_id|top_level_post_id)"\s*:\s*"?(\d{6,})', body)
        if m:
            if post.get("target_type") == "group" and post.get("group_url"):
                base = _clean_link(fb_url(post["group_url"]))
                if "/groups/" in base:
                    return f"{base.split('/groups/')[0]}/groups/{base.split('/groups/')[1].split('/')[0]}/posts/{m.group(1)}", pending
            try:  # trang cá nhân: permalink.php?story_fbid=..&id=<mã nick>
                uid = next(c["value"] for c in page.context.cookies() if c["name"] == "c_user")
                return f"{FB_BASE}/permalink.php?story_fbid={m.group(1)}&id={uid}", pending
            except Exception:
                pass
    return None, pending


# ---- 2) tìm bài trên trang (bảng tin nhóm, Nội dung của bạn, trang cá nhân)
LINK_JS = r"""(snips) => {
  const norm = t => (t || '').normalize('NFC').toLowerCase().replace(/[^\p{L}\p{N}_]+/gu, ' ').trim();
  const has = t => { const n = norm(t); return snips.some(s => s && n.includes(s)); };
  document.querySelectorAll('[data-mt-link]').forEach(e => e.removeAttribute('data-mt-link'));
  const pick = new Set();
  for (const u of document.querySelectorAll('[aria-posinset],[role="article"],[data-pagelet*="FeedUnit"],[data-pagelet*="GroupFeed"] > div > div')) {
    if (has(u.innerText)) pick.add(u.closest('[aria-posinset]') || u.closest('[data-pagelet*="FeedUnit"]') || u);
  }
  if (!pick.size) {  // giao diện lạ: đi ngược lên từ đoạn chữ của bài
    const first = snips[0].split(' ').slice(0, 5).join(' ');
    const tw = document.createTreeWalker(document.body, NodeFilter.SHOW_TEXT);
    let n;
    while ((n = tw.nextNode()) && pick.size < 3) {
      if (!norm(n.nodeValue).includes(first)) continue;
      let e = n.parentElement;
      for (let k = 0; k < 14 && e && e.querySelectorAll('a').length < 4; k++) e = e.parentElement;
      if (e && e !== document.body) pick.add(e);
    }
  }
  const roots = [...pick].filter(r => ![...pick].some(o => o !== r && o.contains(r)));
  roots.slice(0, 4).forEach((r, i) => r.querySelectorAll('a').forEach((a, j) => { if (j < 80) a.setAttribute('data-mt-link', String(i + 1)); }));
  return Math.min(roots.length, 4);
}"""

HOVER_JS = """els => els.forEach(a => { for (const t of ['mouseover', 'mouseenter', 'focusin', 'focus'])
  a.dispatchEvent(new (t.startsWith('focus') ? FocusEvent : MouseEvent)(t, {bubbles: t !== 'mouseenter' && t !== 'focus'})); })"""


def _pick_href(hrefs: list[str], post: dict) -> str | None:
    hits = [h for h in hrefs if h and PERMA_RX.search(h)]
    if not hits:
        return None
    g = ""
    if post.get("group_url"):
        g = _clean_link(fb_url(post["group_url"])).split("/groups/")[-1].split("/")[0] if "/groups/" in post["group_url"] else ""
    hits.sort(key=lambda h: (g and f"/groups/{g}/" not in h, "comment_id" in h))  # ưu tiên link bài trong đúng nhóm
    return _clean_link(hits[0])


def _links_in(page, k: int, post: dict) -> str | None:
    loc = page.locator(f'a[data-mt-link="{k}"]')
    read = lambda: loc.evaluate_all("els => els.map(e => e.href)")
    link = _pick_href(read(), post)
    if link:
        return link
    try:  # Facebook chỉ gắn link thật vào mốc thời gian khi rê chuột lên
        loc.evaluate_all(HOVER_JS)
        page.wait_for_timeout(600)
        link = _pick_href(read(), post)
        if link:
            return link
        for j in range(min(loc.count(), 20)):
            try:
                if loc.nth(j).is_visible():
                    loc.nth(j).hover(timeout=1500)
                    page.wait_for_timeout(150)
            except Exception:
                pass
        page.mouse.move(2, 2)
        page.wait_for_timeout(500)
        return _pick_href(read(), post)
    except Exception:
        return None


def _scan_for_link(page, post: dict, scrolls: int = 4) -> str | None:
    snips = _snippets(post["content"])
    for _ in range(scrolls):
        try:
            n = page.evaluate(LINK_JS, snips)
        except Exception:
            n = 0
        for k in range(1, n + 1):
            link = _links_in(page, k, post)
            if link:
                return link
        page.mouse.wheel(0, 2400)
        page.wait_for_timeout(1500)
    return None


def _is_pending_page(page, post: dict) -> bool:
    try:
        body = _norm(page.inner_text("body"))
    except Exception:
        return False
    texts = selectors().get("pending_texts", PENDING_TEXTS)
    return any(_norm(x) in body for x in texts)


def _find_permalink(page, post: dict) -> tuple[str | None, str]:
    """Tìm bài vừa đăng trong 'Nội dung của bạn' của nhóm, bảng tin nhóm (hoặc trang cá nhân), trích link thật."""
    s = selectors()
    if post["target_type"] == "group" and post.get("group_url"):
        base = fb_url(post["group_url"]).rstrip("/")
        pages = [base + p for p in s.get("my_posts_paths", ["/my_posted_content", ""])]
    else:
        pages = [f"{FB_BASE}/me"]
    for u in pages:
        page.goto(u, wait_until="domcontentloaded", timeout=60000)
        page.wait_for_timeout(3000)
        _check_blocked(page)
        link = _scan_for_link(page, post)
        if link:
            return link, "found"
    if post["target_type"] == "group" and post.get("group_url"):
        snips = _snippets(post["content"])
        for pth in s.get("pending_paths", []):
            page.goto(fb_url(post["group_url"]).rstrip("/") + pth, wait_until="domcontentloaded", timeout=60000)
            page.wait_for_timeout(2500)
            body = _norm(page.inner_text("body"))
            if any(sn in body for sn in snips):
                return None, "pending"
    return None, "not_found"


def _save_link(post: dict, link: str | None, st: str) -> None:
    """Lưu link; chưa có thì hẹn sale thử lại, hết lượt thì báo sếp dán link."""
    if link and st != "pending":
        db.run("""UPDATE posts SET posted_url=?, permalink_status='found', link_next_at=NULL, link_error=NULL WHERE id=?""",
               (link, post["id"]))
        return
    if link:  # đã có link nhưng bài còn chờ nhóm duyệt: lưu link, hẹn xem lại bài đã hiện chưa
        db.run("UPDATE posts SET posted_url=? WHERE id=?", (link, post["id"]))
    cur = db.one("SELECT COALESCE(link_tries,0) n, group_id FROM posts WHERE id=?", (post["id"],)) or {"n": 0}
    tries = cur["n"] + 1
    if st == "pending":
        delay = PENDING_RETRY_MIN if tries < PENDING_MAX_TRIES else None
        why = "Bài đang chờ quản trị viên nhóm duyệt, sale sẽ tự lấy link khi bài được duyệt"
    else:
        delay = LINK_RETRY_MIN[tries - 1] if tries <= len(LINK_RETRY_MIN) else None
        why = "Chưa tìm thấy bài trên Facebook để lấy link"
    nxt = (db.clock() + __import__("datetime").timedelta(minutes=delay)).strftime("%Y-%m-%d %H:%M") if delay else None
    msg = why + (f". Thử lại lúc {nxt[11:16]} {nxt[8:10]}/{nxt[5:7]}" if nxt else
                 ". Đã thử nhiều lần không được: mở bài trên Facebook, chép link dán vào thẻ bài ở mục Bài đăng")
    db.run("UPDATE posts SET permalink_status=?, link_tries=?, link_next_at=?, link_error=? WHERE id=?",
           (st, tries, nxt, msg[:300], post["id"]))
    if not nxt:
        import errors
        errors.report("link", f"Không lưu được link bài #{post['id']}", msg,
                      f"Nhóm: {post.get('group_name') or 'trang cá nhân'} · Bài: {(post.get('title') or '')[:80]}",
                      screen="posts", ref_type="post", ref_id=post["id"])


def _capture_link(page, post: dict, fresh: bool = False) -> tuple[str | None, str]:
    """Lấy link bài: phản hồi của Facebook lúc đăng -> bài trên trang đang mở -> Nội dung của bạn / bảng tin -> chờ duyệt."""
    link, st = None, "not_found"
    try:
        net = post.get("_net") or (None, False)
        if net[0]:
            link, st = net[0], ("pending" if net[1] else "found")
        if not link and fresh:  # vừa đăng: bài thường hiện ngay đầu bảng tin
            link = _scan_for_link(page, post, scrolls=2)
            if link:
                st = "found"
            elif net[1] or _is_pending_page(page, post):
                st = "pending"
        if not link and st != "pending":
            link, st = _find_permalink(page, post)
    except Blocked:
        raise
    except Exception as e:
        print("[permalink]", e)
    _save_link(post, link, st)
    return link, st


def _job_link(pw, aid: int, post_id: int):
    acc, sale, agent = _ctx_names(aid)
    ctx, page = _open(pw, aid)
    try:
        if not _logged_in(ctx):
            _set_login(aid, "not_logged_in", "Phiên đăng nhập đã hết, cần đăng nhập lại")
            raise RuntimeError(f"Nick {accounts.label(acc)} chưa đăng nhập. Vào Nhân viên sale → Mở Chrome nick này để đăng nhập lại")
        _do_link(ctx, page, aid, post_id)
    except Blocked as e:
        _block(aid, str(e))
    finally:
        try:
            ctx.close()
        except Exception:
            pass
        workflows.set_status(agent, "idle", "Chờ lịch đăng tiếp theo")


def _do_link(ctx, page, aid: int, post_id: int) -> None:
    """Sale quay lại lấy link bài đã đăng mà lần trước chưa lấy được."""
    post = db.one("""SELECT p.*, g.url group_url, g.name group_name FROM posts p
                     LEFT JOIN groups g ON g.id=p.group_id WHERE p.id=?""", (post_id,))
    if not post or post.get("permalink_status") == "found":
        return
    acc, sale, agent = _ctx_names(aid)
    workflows.set_status(agent, "working", f"Lấy link bài #{post_id} ({post.get('group_name') or 'trang cá nhân'})")
    if post.get("permalink_status") == "pending" and PERMA_RX.search(post.get("posted_url") or ""):
        page.goto(post["posted_url"], wait_until="domcontentloaded", timeout=60000)  # đã có link, chờ duyệt: xem bài hiện chưa
        page.wait_for_timeout(3000)
        _check_blocked(page)
        body = page.inner_text("body").lower()
        if not any(x.lower() in body for x in selectors()["removed_texts"]) and not _is_pending_page(page, post):
            db.run("UPDATE posts SET permalink_status='found', link_next_at=NULL, link_error=NULL WHERE id=?", (post_id,))
            db.log(agent, "Đã lưu link bài", f"Bài #{post_id} đã được nhóm duyệt: {post['posted_url']}")
            return
        _save_link(post, None, "pending")
        return
    link, st = _capture_link(page, post)
    db.log(agent, "Đã lưu link bài" if link else "Chưa lấy được link bài",
           f"Bài #{post_id}: {link}" if link else f"Bài #{post_id}: " + (db.one("SELECT link_error FROM posts WHERE id=?", (post_id,)) or {}).get("link_error", ""))


# ---------------------------------------------------------------- quét bình luận tìm khách, xin SĐT
TIME_RX = re.compile(r"^(\d+\s*(giây|phút|giờ|ngày|tuần|tháng|năm|s|m|h|d|w|y|min|mins|hr|hrs)|vừa xong|just now)$", re.I)


def _replies_today(aid: int) -> int:
    return db.one("SELECT COUNT(*) n FROM comment_seen WHERE account_id=? AND replied=1 AND created_at LIKE ?",
                  (aid, db.today() + "%"))["n"]


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


def _scan_comments(page, post: dict, sale: dict, acc: dict | None = None) -> dict:
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
    own = {x.strip().lower() for x in (sale.get("name"), (acc or {}).get("name")) if x}
    own |= {a["name"].strip().lower() for a in accounts.of_sale(sale["id"]) if a.get("name")}  # mọi nick của sale
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
        cid = db.run("""INSERT OR IGNORE INTO comment_seen(post_id, author, text_hash, lead_id, sale_id, account_id, created_at)
                        VALUES (?,?,?,?,?,?,?)""", (post["id"], author, h, lead_id, sale["id"], (acc or {}).get("id"), db.now()))
        lead = db.one("SELECT phone FROM leads WHERE id=?", (lead_id,)) if lead_id else None
        if (lead_id and not (lead or {}).get("phone") and st.get("auto_reply_comments") == "1" and texts
                and _replies_today((acc or {}).get("id")) < max_reply
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


def _do_scan(ctx, page, aid: int, post_ids: list[int]) -> dict:
    acc, sale, agent = _ctx_names(aid)
    total = {"leads": 0, "phones": 0, "asked": 0}
    workflows.set_status(agent, "working", f"Đang đọc bình luận {len(post_ids)} bài (nick {accounts.label(acc)}) để tìm khách")
    if not _logged_in(ctx):
        _set_login(aid, "not_logged_in", "Phiên đăng nhập đã hết, cần đăng nhập lại")
        return total
    for pid in post_ids:
        post = db.one("SELECT * FROM posts WHERE id=?", (pid,))
        if not post or post.get("permalink_status") != "found":
            continue
        try:
            page.goto(post["posted_url"], wait_until="domcontentloaded", timeout=60000)
            page.wait_for_timeout(3000)
            _check_blocked(page)
            body = page.inner_text("body").lower()
            if any(t.lower() in body for t in selectors()["removed_texts"]):
                db.run("UPDATE posts SET permalink_status='removed', bump_enabled=0 WHERE id=?", (pid,))
                try:
                    import fb_policy
                    fb_policy.on_removed(post)
                except Exception as e:
                    print("[fb policy]", e)
                continue
            r = _scan_comments(page, post, sale, acc)
            for k in total:
                total[k] += r[k]
        except Blocked:
            raise
        except Exception as e:
            db.log(agent, "Lỗi quét bình luận", str(e).splitlines()[0][:160])
            import errors
            errors.report_exc("scan", f"Quét bình luận bài #{pid} (nick {accounts.label(acc)}) bị lỗi", e, screen="kpi",
                              ref_type="account", ref_id=aid)
        _pause(page, 4, 9)
    return total


def _job_scan(pw, aid: int, post_ids: list[int]):
    acc, sale, agent = _ctx_names(aid)
    ctx, page = _open(pw, aid)
    total = {"leads": 0, "phones": 0, "asked": 0}
    try:
        total = _do_scan(ctx, page, aid, post_ids)
    except Blocked as e:
        _block(aid, str(e))
    finally:
        try:
            ctx.close()
        except Exception:
            pass
        workflows.set_status(agent, "idle", f"Quét xong: {total['leads']} khách mới, {total['phones']} SĐT")


# ---------------------------------------------------------------- up bài: bình luận ảnh sản phẩm
def _bump_done(bump_id: int, status: str, err: str | None = None, shot: str | None = None, image: str | None = None):
    if status == "failed":
        import errors
        b = db.one("SELECT post_id FROM bumps WHERE id=?", (bump_id,)) or {}
        errors.report("bump", f"Up bài #{b.get('post_id') or '?'} bị lỗi", err or "", screen="posts",
                      ref_type="post", ref_id=b.get("post_id"), screenshot=shot)
    db.run("UPDATE bumps SET status=?, error=?, screenshot=COALESCE(?, screenshot), image=COALESCE(?, image), done_at=? WHERE id=?",
           (status, err, shot, image, db.now(), bump_id))


CMT_PIN_JS = """el => {
  document.querySelectorAll('[data-mt-cmt],[data-mt-box]').forEach(e => { e.removeAttribute('data-mt-cmt'); e.removeAttribute('data-mt-box'); });
  const ED = '[role=textbox],[contenteditable="true"],textarea';
  let box = el.matches(ED) ? el : null, up = el;
  for (let k = 0; !box && k < 6 && up.parentElement; k++) { up = up.parentElement; box = up.querySelector(ED); }  // chữ mờ -> ô soạn cạnh nó
  box = box || el;
  box.setAttribute('data-mt-box', '1');
  let r = box;
  for (let k = 0; k < 12 && r.parentElement; k++) {
    r = r.parentElement;
    if (r.tagName === 'FORM' || r.querySelector('input[type=file]')) break;
  }
  if (!(r.tagName === 'FORM' || r.querySelector('input[type=file]'))) return false;
  r.setAttribute('data-mt-cmt', '1');
  return true;
}"""
CMT_PREVIEW_JS = """() => {
  const g = [...document.querySelectorAll('img')].filter(i => /^(blob:|data:image)/.test(i.src || '')).length
          + document.querySelectorAll('[style*="blob:"]').length;
  let z = document.querySelector('[data-mt-cmt]');
  if (!z) return g;
  for (let k = 0; k < 3 && z.parentElement; k++) z = z.parentElement;  // ảnh xem trước có thể nằm ngay dưới khung soạn
  const imgs = [...z.querySelectorAll('img,video')].filter(i => i.tagName === 'VIDEO' ||
      ((i.naturalWidth || i.width) >= 40 && !/emoji|rsrc\\.php|static\\.xx/.test(i.src || ''))).length;
  const rm = [...z.querySelectorAll('[role=button]')].filter(b => /^(gỡ|xóa|xoá|remove|×|✕)/i.test((b.getAttribute('aria-label') || b.innerText || '').trim())).length;
  return g + imgs + rm;
}"""
CMT_STATE_JS = """labels => {
  // nút gửi (mũi tên) trong vùng bình luận: còn mờ (aria-disabled) nghĩa là ảnh chưa tải xong
  let z = document.querySelector('[data-mt-cmt]');
  const box = document.querySelector('[data-mt-box]');
  if (z) for (let k = 0; k < 3 && z.parentElement; k++) z = z.parentElement;
  z = z || document;
  const want = labels.map(l => l.toLowerCase());
  const btn = [...z.querySelectorAll('[role=button],button')].find(b => want.includes((b.getAttribute('aria-label') || '').trim().toLowerCase()));
  return {send: !!btn, enabled: !!btn && btn.getAttribute('aria-disabled') !== 'true' && !btn.disabled,
          busy: z.querySelectorAll('[role=progressbar]').length, text: box ? (box.innerText || '').trim().length : -1};
}"""


def _cmt_state(page, labels) -> dict:
    try:
        return page.evaluate(CMT_STATE_JS, labels)
    except Exception:
        return {"send": False, "enabled": False, "busy": 0, "text": -1}


def _cmt_previews(page) -> int:
    """Số ảnh xem trước: ảnh blob trên trang + ảnh / nút gỡ ảnh trong khung bình luận đã ghim."""
    try:
        return page.evaluate(CMT_PREVIEW_JS)
    except Exception:
        return 0


def _cmt_choose(page, btn, img) -> bool:
    try:
        with page.expect_file_chooser(timeout=8000) as fc:
            btn.click()
        fc.value.set_files(str(img))
        return True
    except Exception:
        return False


def _send_comment(page, text: str, img=None):
    """Gõ bình luận vào bài đang mở (kèm 1 ảnh nếu có), chờ ảnh tải xong, bấm gửi, kiểm tra ô soạn đã trống.
    Dùng cho up bài (ảnh + câu) và trả lời khách (chỉ chữ). Lỗi thì raise RuntimeError có lý do."""
    s = selectors()
    box = None
    end = time.time() + 15
    while not box and time.time() < end:
        # ô soạn thật (role=textbox) trước, rồi mới tới chữ mờ "Viết bình luận..." (chữ mờ biến mất khi gõ)
        for lb in s["comment_box"]:
            loc = page.get_by_role("textbox", name=re.compile(re.escape(lb), re.I))
            try:
                for i in range(min(loc.count(), 6)):
                    if loc.nth(i).is_visible():
                        box = loc.nth(i)
                        break
            except Exception:
                pass
            if box:
                break
        if not box:
            box = _visible_first(page, s["comment_box"], role=None)
        if not box:
            page.mouse.wheel(0, 600)
            page.wait_for_timeout(800)
    if not box:
        raise RuntimeError("Không tìm thấy ô bình luận. Thêm chữ hiển thị mới vào comment_box trong fb_selectors.json")
    # ghim ô soạn thật và khung bình luận (form chứa ô tệp) để mọi thao tác sau chỉ làm trong đúng khung này:
    # trên trang bài còn hộp đăng bài "Ảnh/video" và ô tệp khác, chọn nhầm là ảnh không vào bình luận
    try:
        scoped = box.evaluate(CMT_PIN_JS)
    except Exception:
        scoped = False
    pin = page.locator("[data-mt-box]")
    if pin.count():
        box = pin.first
    box.scroll_into_view_if_needed()
    box.click()
    _pause(page)
    comp = page.locator("[data-mt-cmt]")
    if text:
        page.keyboard.insert_text(text)
    base = _cmt_previews(page)
    tried = []
    ok = not img  # bình luận chỉ có chữ (trả lời khách): không cần ảnh
    for how in (("form", "button", "page") if img else ()):
        if how == "form":  # ô tệp ngay trong khung bình luận: đặt tệp thẳng vào, không cần bấm nút
            inp = comp.locator('input[type="file"]') if scoped else None
            if not inp or not inp.count():
                continue
            try:
                inp.first.set_input_files(str(img))
            except Exception as e:
                tried.append(f"ô tệp trong khung: {str(e)[:60]}")
                continue
        elif how == "button":  # nút Đính kèm trong khung bình luận
            btn = _visible_first(comp, s["comment_attach"]) if scoped and comp.count() else None
            if not btn:
                continue
            if not _cmt_choose(page, btn, img):
                tried.append("nút đính kèm không mở hộp chọn tệp")
                continue
        else:  # dự phòng: nút có chữ dành riêng cho bình luận trên cả trang (không dùng "Ảnh/video" của hộp đăng bài)
            labels = [x for x in s["comment_attach"] if "đính kèm" in x.lower() or "attach" in x.lower()]
            btn = _visible_first(page, labels)
            if not btn or not _cmt_choose(page, btn, img):
                tried.append("không thấy nút đính kèm của bình luận")
                continue
        end = time.time() + 30  # chờ ảnh hiện trong ô bình luận; không hiện thì không gửi (tránh up bài không ảnh)
        while _cmt_previews(page) <= base and time.time() < end:
            page.wait_for_timeout(700)
        if _cmt_previews(page) > base:
            ok = True
            break
        tried.append({"form": "đặt tệp vào ô trong khung", "button": "nút đính kèm trong khung",
                      "page": "nút đính kèm trên trang"}[how] + ": không hiện ảnh")
    if img and not ok:
        raise RuntimeError("Đã chọn ảnh nhưng Facebook không hiện ảnh trong ô bình luận nên chưa gửi ("
                           + ("; ".join(tried) or "không tìm thấy nút hoặc ô đính kèm ảnh") + "). Xem ảnh chụp lượt up này")
    # ảnh thường mất 10–20 giây mới tải lên xong: chờ nút gửi (mũi tên) sáng lên, hết thanh tiến trình
    labels = s.get("comment_send") or ["Bình luận", "Comment"]
    t0, end = time.time(), time.time() + 90
    st = _cmt_state(page, labels)
    while time.time() < end:
        st = _cmt_state(page, labels)
        if st["send"] and st["enabled"] and not st["busy"] and time.time() - t0 > 2:
            break
        if not st["send"] and not st["busy"] and time.time() - t0 > 20:  # không thấy nút gửi: chờ đủ 20 giây
            break
        page.wait_for_timeout(1000)
    if st["send"] and not st["enabled"]:
        raise RuntimeError("Ảnh tải lên quá 90 giây chưa xong (nút gửi bình luận vẫn mờ) nên chưa gửi. Xem ảnh chụp lượt up này")
    page.wait_for_timeout(1500)
    sent_by = "Enter"
    if st["send"]:
        btn = None
        zone = page.locator("[data-mt-cmt]").locator("xpath=ancestor::*[3]") if comp.count() else page
        for lb in labels:
            loc = zone.get_by_role("button", name=re.compile(r"^\s*" + re.escape(lb) + r"\s*$", re.I))
            try:
                if loc.count() and loc.first.is_visible():
                    btn = loc.first
                    break
            except Exception:
                pass
        if btn:
            btn.click()
            sent_by = "nút gửi"
    if sent_by == "Enter":
        pin = page.locator("[data-mt-box]")
        (pin.first if pin.count() else box).click()
        page.keyboard.press("Enter")
    # kiểm tra đã gửi: ô soạn trống lại (Facebook xóa chữ và ảnh sau khi gửi)
    end = time.time() + 20
    while time.time() < end and _cmt_state(page, labels)["text"] > 0:
        page.wait_for_timeout(800)
    if _cmt_state(page, labels)["text"] > 0:
        pin = page.locator("[data-mt-box]")
        if pin.count():
            pin.first.click()
            page.keyboard.press("Enter")
            page.wait_for_timeout(6000)
        if _cmt_state(page, labels)["text"] > 0:
            raise RuntimeError(f"Đã bấm gửi ({sent_by}) nhưng bình luận chưa đi (chữ vẫn nằm trong ô). Xem ảnh chụp")


def _do_bump(ctx, page, aid: int, bump_id: int):
    b = db.one("SELECT * FROM bumps WHERE id=?", (bump_id,))
    post = db.one("""SELECT p.*, g.url group_url, g.name group_name FROM posts p
                     LEFT JOIN groups g ON g.id=p.group_id WHERE p.id=?""", (b["post_id"],)) if b else None
    if not b or not post:
        return
    acc, sale, agent = _ctx_names(aid)
    where = post.get("group_name") or "trang cá nhân"
    import fb_policy
    ok, why, _ = fb_policy.allow(aid, "bump")
    if not ok:
        _bump_done(bump_id, "skipped", f"Không up theo luật Facebook: {why}")
        return
    img = media_folder.pick(post)
    if not img:
        _bump_done(bump_id, "failed", "Thư mục ảnh trống hoặc chưa cài. Vào Cài đặt → Up bài để chọn thư mục")
        return
    db.run("UPDATE bumps SET status='running' WHERE id=?", (bump_id,))
    workflows.set_status(agent, "working", f"Đang up bài ở {where} (nick {accounts.label(acc)})")
    shot = db.SHOTS_DIR / f"bump-{bump_id}.png"
    try:
        if not _logged_in(ctx):
            _set_login(aid, "not_logged_in", "Phiên đăng nhập đã hết, cần đăng nhập lại")
            raise RuntimeError(f"Nick {accounts.label(acc)} chưa đăng nhập")
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
                _scan_comments(page, post, sale, acc)
            except Blocked:
                raise
            except Exception as e:
                print("[scan]", e)
                import errors
                errors.report_exc("scan", f"Quét bình luận bài #{post['id']} bị lỗi", e, screen="kpi")
        if any(t.lower() in body for t in s["removed_texts"]):
            db.run("UPDATE posts SET permalink_status='removed', bump_enabled=0 WHERE id=?", (post["id"],))
            try:
                import fb_policy
                fb_policy.on_removed(post)
            except Exception as e:
                print("[fb policy]", e)
            _bump_done(bump_id, "skipped", "Bài đã bị xóa hoặc ẩn, đã ngừng up bài này")
            db.log(agent, "Bài bị gỡ", f"Bài #{post['id']} ở {where} không còn hiển thị, ngừng up")
            return
        _send_comment(page, (b.get("text") or "").strip(), img)
        page.wait_for_timeout(5000)
        _check_blocked(page)
        page.screenshot(path=str(shot))
        _bump_done(bump_id, "done", None, f"/shots/{shot.name}", str(img))
        media_folder.record([img], "bump", post, acc["sale_id"], bump_id)
        db.run("UPDATE posts SET bump_count=COALESCE(bump_count,0)+1, last_bump_at=? WHERE id=?", (db.now(), post["id"]))
        db.log(agent, "Up bài", f"Bình luận ảnh {img.name} vào bài #{post['id']} ở {where} (nick {accounts.label(acc)})")
        import learning
        learning.award(agent, 1, "Up bài")
    except Blocked as e:
        _bump_done(bump_id, "failed", str(e))
        _block(aid, str(e))
        raise
    except Exception as e:
        try:
            page.screenshot(path=str(shot))
        except Exception:
            pass
        _bump_done(bump_id, "failed", str(e).splitlines()[0][:300], f"/shots/{shot.name}" if shot.exists() else None, str(img))
        db.log(agent, "Lỗi up bài", f"Bài #{post['id']}: {str(e).splitlines()[0][:160]}")


def _job_bump(pw, aid: int, bump_id: int):
    acc, sale, agent = _ctx_names(aid)
    ctx, page = _open(pw, aid)
    try:
        _do_bump(ctx, page, aid, bump_id)
    except Blocked:
        pass
    finally:
        try:
            ctx.close()
        except Exception:
            pass
        workflows.set_status(agent, "idle", "Chờ lịch tiếp theo")


# ---------------------------------------------------------------- ca làm việc trên một nick
_scan_pending: dict[int, list[int]] = {}  # nick -> bài cần quét bình luận ở ca tới


def request_scan(aid: int, post_ids: list[int]):
    cur = _scan_pending.setdefault(aid, [])
    cur.extend(p for p in post_ids if p not in cur)


def due_work(aid: int, stamp: str | None = None) -> dict:
    """Việc đến hạn của một nick: bài đến giờ đăng, lượt up bài đến giờ, bài chờ quét bình luận."""
    stamp = stamp or db.now()[:16]
    posts = [r["id"] for r in db.q("""SELECT id FROM posts WHERE account_id=? AND status='scheduled' AND scheduled_for <= ?
                                      ORDER BY scheduled_for""", (aid, stamp))]
    bumps = [r["id"] for r in db.q("""SELECT id FROM bumps WHERE account_id=? AND status='scheduled' AND scheduled_for <= ?
                                      ORDER BY scheduled_for""", (aid, stamp))]
    links = [r["id"] for r in db.q("""SELECT id FROM posts WHERE account_id=? AND status='posted'
                                      AND COALESCE(permalink_status,'') IN ('not_found','pending','')
                                      AND link_next_at IS NOT NULL AND link_next_at <= ? ORDER BY link_next_at LIMIT 6""", (aid, stamp))]
    try:
        import replies
        rep = replies.due(aid)
    except Exception:
        rep = []
    return {"posts": posts, "bumps": bumps, "scan": list(_scan_pending.get(aid, [])), "links": links, "replies": rep}


def _job_session(pw, aid: int):
    """Ca làm việc: mở Chrome của nick, làm hết việc đến hạn của nick đó, đóng lại (rồi sale chuyển sang nick khác)."""
    acc, sale, agent = _ctx_names(aid)
    work = due_work(aid)
    if not any(work.values()):
        return
    _scan_pending.pop(aid, None)
    db.run("UPDATE fb_accounts SET last_session_at=? WHERE id=?", (db.now(), aid))
    db.run("UPDATE sales SET last_account_id=? WHERE id=?", (aid, acc["sale_id"]))
    workflows.set_status(agent, "working", f"Chuyển sang nick {accounts.label(acc)}")
    ctx, page = _open(pw, aid)
    done = {"posts": 0, "bumps": 0, "scan": 0, "links": 0, "replies": 0}
    try:
        for pid in work["posts"]:
            _do_post(ctx, page, aid, pid, False)
            done["posts"] += 1
            _pause(page, 20, 45)
        for pid in work.get("links", []):  # bài đã đăng nhưng chưa lưu được link: quay lại lấy
            try:
                _do_link(ctx, page, aid, pid)
                done["links"] += 1
            except Blocked:
                raise
            except Exception as e:
                print("[link]", e)
            _pause(page, 5, 15)
        for bid in work["bumps"]:
            _do_bump(ctx, page, aid, bid)
            done["bumps"] += 1
            _pause(page, 15, 40)
        for rid in work.get("replies", []):  # câu trả lời khách sếp đã duyệt, tới giờ gửi
            import replies
            replies.send(page, aid, rid)
            done["replies"] += 1
            _pause(page, 15, 40)
        if work["scan"]:
            _do_scan(ctx, page, aid, work["scan"])
            done["scan"] = len(work["scan"])
        db.log(agent, "Xong ca trên nick", f"Nick {accounts.label(acc)}: đăng {done['posts']} bài, up {done['bumps']} lượt, "
               f"quét {done['scan']} bài" + (f", lấy link {done['links']} bài" if done["links"] else "")
               + (f", trả lời {done['replies']} khách" if done["replies"] else ""))
    except Blocked:
        pass  # _block đã dừng riêng nick này; việc còn lại của nick đã trả về hàng đợi
    finally:
        try:
            ctx.close()
        except Exception:
            pass
        workflows.set_status(agent, "idle", f"Xong việc trên nick {accounts.label(acc)}")


class NoImage(RuntimeError):
    """Bài không có ảnh: không đăng."""


def _no_image(post: dict, msg: str, dry_run: bool, agent: str, shot: str | None = None, attach: bool = False):
    """Bài thiếu ảnh: không đăng, trả bài về hàng chờ duyệt (bỏ nick/giờ) để khi có ảnh Tuấn xếp lại.
    Đính ảnh lên Facebook thất bại 2 lần: dừng hẳn (báo Lỗi) để không thử đi thử lại mãi."""
    import errors
    fails = 0
    if attach and not dry_run:
        db.run("UPDATE posts SET img_fails=COALESCE(img_fails,0)+1 WHERE id=?", (post["id"],))
        fails = (db.one("SELECT img_fails FROM posts WHERE id=?", (post["id"],)) or {}).get("img_fails") or 0
    errors.report("image", "Facebook không nhận ảnh nên chưa đăng bài" if attach else "Bài không có ảnh nên chưa đăng", msg,
                  f"Bài #{post['id']}: {(post.get('title') or '')[:80]}", screen="posts" if attach else "products",
                  ref_type="post", ref_id=post["id"], screenshot=shot)
    if dry_run:
        db.run("UPDATE posts SET error=?, screenshot=COALESCE(?, screenshot) WHERE id=?", (msg[:300], shot, post["id"]))
    elif attach and fails >= 2:
        db.run("UPDATE posts SET status='failed', error=?, screenshot=COALESCE(?, screenshot) WHERE id=?",
               (("Đã thử 2 lần, Facebook không nhận ảnh nên KHÔNG đăng. Xem ảnh chụp, sửa rồi bấm Đưa về hàng đợi. " + msg)[:300],
                shot, post["id"]))
        db.log(agent, "Không đăng bài thiếu ảnh", f"Bài #{post['id']}: Facebook không nhận ảnh 2 lần, dừng bài này")
        return
    else:
        # bài chăm sóc nhóm viết riêng cho 1 nhóm: bỏ luôn; bài tìm khách: về hàng chờ, có ảnh thì xếp lại
        st = "failed" if post.get("source") == "care" else "approved"
        db.run("""UPDATE posts SET status=?, error=?, sale_id=NULL, account_id=NULL, scheduled_for=NULL,
                  managed=0 WHERE id=?""", (st, msg[:300], post["id"]))
    db.log(agent, "Không đăng bài thiếu ảnh", f"Bài #{post['id']}: {msg[:200]}")


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
            "discover": "tìm nhóm mới", "join": "xin vào nhóm", "session": "làm ca trên nick",
            "prospect": "mở trang tìm khách sỉ cho Mai", "mygroups": "rà soát nhóm của nick", "link": "lấy link bài đã đăng",
            "friends": "đọc nhóm tìm người kết bạn", "replyscan": "đọc nhóm tìm người hỏi mua",
            "reply": "trả lời khách trong nhóm"}


def _worker(sale_id: int, q: Queue):
    """Một nhân viên sale làm lần lượt từng việc (mỗi lúc chỉ mở Chrome của một nick)."""
    from playwright.sync_api import sync_playwright
    while True:
        job = q.get()
        _busy[sale_id] = job.get("kind", "")
        aid = job.get("account")
        if not aid:  # việc cũ không ghi nick: dùng nick đầu tiên của sale
            a = accounts.first(sale_id)
            aid = a["id"] if a else None
        if aid:
            _busy_acc[sale_id] = aid
        try:
            if not aid:
                raise RuntimeError("Nhân viên sale này chưa có nick Facebook nào. Vào Nhân viên sale → Thêm nick")
            with sync_playwright() as pw:
                k = job["kind"]
                if k == "open":
                    _job_open(pw, aid, 15 if job.get("urls") else 30, urls=job.get("urls"))  # mở hồ sơ kết bạn: giữ cửa sổ tối đa 15 phút
                elif k == "check":
                    _job_check(pw, aid)
                elif k == "post":
                    _job_post(pw, aid, job["post_id"], job.get("dry_run", False))
                elif k == "bump":
                    _job_bump(pw, aid, job["bump_id"])
                elif k == "scan":
                    _job_scan(pw, aid, job["post_ids"])
                elif k == "session":
                    _job_session(pw, aid)
                elif k == "link":
                    _job_link(pw, aid, job["post_id"])
                elif k == "discover":
                    import group_finder
                    group_finder.job_discover(pw, aid, job["keywords"], job.get("notify"))
                elif k == "join":
                    import group_finder
                    group_finder.job_join(pw, aid, job.get("notify"))
                elif k == "mygroups":
                    import my_groups
                    my_groups.job_sync(pw, aid, job.get("notify"), job.get("leave"))
                elif k == "friends":
                    import friends
                    friends.job(pw, aid, job.get("group_ids"), job.get("notify"))
                elif k == "replyscan":
                    import replies
                    replies.job(pw, aid, job.get("group_ids"), job.get("notify"))
                elif k == "reply":
                    import replies
                    ctx, page = _open(pw, aid)
                    try:
                        replies.send(page, aid, job["reply_id"])
                    finally:
                        ctx.close()
                elif k == "prospect":
                    import prospect
                    prospect.job(pw, aid, job.get("plan"), job.get("urls"), job.get("notify"))
        except Exception as e:
            traceback.print_exc()
            msg = friendly(e)
            if job["kind"] == "open" and is_closed_error(e):
                continue  # sếp tự đóng cửa sổ Chrome vừa mở: không phải lỗi
            db.log(f"sale-{sale_id}", "Lỗi trình duyệt", msg[:200])
            import errors
            s = db.one("SELECT name FROM sales WHERE id=?", (sale_id,)) or {}
            acc = accounts.get(aid) if aid else None
            nick = f" (nick {accounts.label(acc)})" if acc else ""
            eid = errors.report_exc("browser", f"Chrome của sale {s.get('name') or '#' + str(sale_id)}{nick} lỗi khi "
                                    f"{JOB_NAME.get(job['kind'], job['kind'])}", e, screen="sales",
                                    ref_type="account" if aid else "sale", ref_id=aid or sale_id)
            if eid and msg != str(e).strip().splitlines()[0]:
                db.run("UPDATE errors SET message=? WHERE id=?", (msg[:1000], eid))
            if job["kind"] == "check" and aid:
                db.run("UPDATE fb_accounts SET last_error=? WHERE id=?", (msg[:300], aid))
                accounts.sync_sale(sale_id)
            if job.get("notify"):  # việc CEO giao theo lệnh sếp: báo lại là không làm được
                import ceo_orders
                ceo_orders.followup(f"{s.get('name') or 'Sale'}{nick} chưa {JOB_NAME.get(job['kind'], job['kind'])} được: {msg[:200]}. "
                                    "Chi tiết ở mục Lỗi.", job["notify"])
            if job["kind"] == "bump":
                db.run("UPDATE bumps SET status='failed', error=? WHERE id=? AND status='running'",
                       (msg[:300], job["bump_id"]))
            if job["kind"] == "post" and not job.get("dry_run"):
                db.run("UPDATE posts SET status='failed', error=? WHERE id=? AND status='posting'",
                       (msg[:300], job["post_id"]))
            if job["kind"] == "session" and aid:  # ca lỗi khi đang mở Chrome: bài đang đăng dở trả về chờ lượt sau
                db.run("UPDATE posts SET status='scheduled' WHERE account_id=? AND status='posting'", (aid,))
                db.run("UPDATE bumps SET status='scheduled' WHERE account_id=? AND status='running'", (aid,))
        finally:
            _busy.pop(sale_id, None)
            _busy_acc.pop(sale_id, None)
            q.task_done()

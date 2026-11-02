"""Nhân viên sale đăng bài Facebook bằng hồ sơ Chrome riêng của mình.

Mỗi sale có một thư mục hồ sơ (data/profiles/sale-<id>). Lần đầu, sếp bấm "Mở Chrome",
tự đăng nhập Facebook trong cửa sổ đó; phiên đăng nhập được lưu trong hồ sơ.
Từ đó sale tự mở hồ sơ, đăng bài theo lịch rồi đóng lại.

Hệ thống không lưu mật khẩu, không giải captcha, không giả mạo dấu vân tay trình duyệt.
Gặp checkpoint hoặc khóa tạm thời -> dừng tự đăng nick đó và báo sếp.
"""
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
    except Exception:
        return pw.chromium.launch_persistent_context(**kw)  # Chromium của Playwright


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


def _post_images(post: dict) -> list[str]:
    if db.get_settings().get("attach_images") != "1" or not post.get("product_id"):
        return []
    p = db.one("SELECT images FROM products WHERE id=?", (post["product_id"],))
    files = [str(db.DATA_DIR / rel) for rel in json.loads((p or {}).get("images") or "[]")]
    return [f for f in files if Path(f).exists()][:4]


def _publish(page, post: dict, target_url: str, composer_labels: list[str], dry_run: bool) -> str:
    s = selectors()
    page.goto(target_url, wait_until="domcontentloaded", timeout=60000)
    page.wait_for_timeout(3500)
    _check_blocked(page)
    if not _wait_click(page, composer_labels, timeout=25):
        raise RuntimeError("Không tìm thấy ô viết bài. Kiểm tra nick đã vào nhóm chưa, hoặc thêm chữ hiển thị mới vào fb_selectors.json")
    page.wait_for_timeout(2000)
    dialog = page.get_by_role("dialog").last
    box = dialog.get_by_role("textbox").first
    box.wait_for(state="visible", timeout=20000)
    box.click()
    _pause(page)
    text = post["content"].rstrip() + ("\n\n" + post["hashtags"] if post.get("hashtags") else "")
    lines = text.split("\n")
    for i, line in enumerate(lines):
        if line:
            page.keyboard.insert_text(line)
        if i < len(lines) - 1:
            page.keyboard.press("Enter")
    _pause(page)
    imgs = _post_images(post)
    if imgs:
        inp = dialog.locator('input[type="file"]')
        if not inp.count():
            el = _visible_first(dialog, s["photo_button"])
            if el:
                el.click()
                page.wait_for_timeout(1200)
            inp = page.locator('input[type="file"]')
        if inp.count():
            inp.last.set_input_files(imgs)
            page.wait_for_timeout(2500 + 1500 * len(imgs))
    shot = db.SHOTS_DIR / f"post-{post['id']}.png"
    if dry_run:
        page.screenshot(path=str(shot))
        page.keyboard.press("Escape")
        page.wait_for_timeout(1200)
        _wait_click(page, s["discard_button"], timeout=4)
        return f"/shots/{shot.name}"
    btn = None
    for lb in s["post_button"]:
        loc = dialog.get_by_role("button", name=re.compile(rf"^\s*{re.escape(lb)}\s*$", re.I))
        if loc.count():
            btn = loc.last
            break
    if not btn:
        raise RuntimeError("Không tìm thấy nút Đăng trong hộp soạn bài")
    end = time.time() + 30
    while btn.get_attribute("aria-disabled") == "true" and time.time() < end:
        page.wait_for_timeout(800)
    btn.click()
    try:
        box.wait_for(state="hidden", timeout=90000)
    except Exception:
        page.screenshot(path=str(shot))
        raise RuntimeError("Đã bấm Đăng nhưng hộp soạn bài chưa đóng sau 90 giây (mạng chậm hoặc Facebook chặn)")
    page.wait_for_timeout(4000)
    _check_blocked(page)
    page.screenshot(path=str(shot))
    return f"/shots/{shot.name}"


# ---------------------------------------------------------------- công việc
def _set_login(sale_id: int, status: str, err: str = ""):
    db.run("UPDATE sales SET login_status=?, last_check_at=?, last_error=? WHERE id=?",
           (status, db.now(), err, sale_id))


def _job_open(pw, sale_id: int, minutes: int = 30):
    """Mở Chrome để sếp đăng nhập / vào nhóm; đóng cửa sổ là xong."""
    ctx = _launch(pw, sale_id, headless=False)
    page = ctx.pages[0] if ctx.pages else ctx.new_page()
    page.goto(FB_BASE, wait_until="domcontentloaded")
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
    ctx = _launch(pw, sale_id)
    try:
        if not _logged_in(ctx):
            _set_login(sale_id, "not_logged_in", "Chưa đăng nhập Facebook trong hồ sơ này")
            return
        page = ctx.pages[0] if ctx.pages else ctx.new_page()
        page.goto(FB_BASE, wait_until="domcontentloaded", timeout=60000)
        page.wait_for_timeout(3000)
        _check_blocked(page)
        _set_login(sale_id, "ok")
    except Blocked as e:
        _block(sale_id, str(e))
    finally:
        ctx.close()


def _block(sale_id: int, reason: str):
    _set_login(sale_id, "checkpoint", reason)
    db.run("UPDATE sales SET auto_post=0 WHERE id=?", (sale_id,))
    db.run("UPDATE posts SET status='approved', sale_id=NULL, scheduled_for=NULL WHERE sale_id=? AND status='scheduled'",
           (sale_id,))
    db.log("tuan", "Nick gặp sự cố", f"Sale #{sale_id}: {reason}. Đã dừng tự đăng và trả các bài chờ về hàng đợi.")


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
    ctx = _launch(pw, sale_id)
    page = ctx.pages[0] if ctx.pages else ctx.new_page()
    try:
        if not _logged_in(ctx):
            _set_login(sale_id, "not_logged_in", "Phiên đăng nhập đã hết, cần đăng nhập lại")
            raise RuntimeError("Nick chưa đăng nhập. Vào Nhân viên sale → Mở Chrome để đăng nhập lại")
        if post["target_type"] == "group":
            if not post.get("group_url"):
                raise RuntimeError("Nhóm chưa có đường dẫn. Vào mục Hội nhóm để thêm link nhóm")
            url, labels = post["group_url"], selectors()["group_composer"]
        else:
            url, labels = f"{FB_BASE}/me", selectors()["profile_composer"]
        shot = _publish(page, post, url, labels, dry_run)
        if dry_run:
            db.run("UPDATE posts SET screenshot=?, error=NULL WHERE id=?", (shot, post_id))
            db.log(aid, "Đăng thử", f"Bài #{post_id}: điền nội dung thành công ở {where} (chưa bấm Đăng)")
        else:
            workflows.mark_posted(post_id, url, f"{sale['name']} (tự động)")
            db.run("UPDATE posts SET screenshot=? WHERE id=?", (shot, post_id))
            db.run("UPDATE sales SET last_post_at=?, last_error=NULL WHERE id=?", (db.now(), sale_id))
            _set_login(sale_id, "ok")
            db.log(aid, "Đã đăng", f"Bài #{post_id} lên {where}")
    except Blocked as e:
        _fail(page, post_id, str(e), dry_run)
        _block(sale_id, str(e))
    except Exception as e:
        _fail(page, post_id, str(e).split("\n")[0][:300], dry_run)
        db.log(aid, "Lỗi đăng bài", f"Bài #{post_id}: {str(e).splitlines()[0][:200]}")
    finally:
        try:
            ctx.close()
        except Exception:
            pass
        workflows.set_status(aid, "idle", "Chờ lịch đăng tiếp theo")


def _fail(page, post_id: int, msg: str, dry_run: bool):
    shot = db.SHOTS_DIR / f"post-{post_id}-error.png"
    try:
        page.screenshot(path=str(shot))
        rel = f"/shots/{shot.name}"
    except Exception:
        rel = None
    db.run(f"UPDATE posts SET {'status=' + repr('failed') + ',' if not dry_run else ''} error=?, screenshot=? WHERE id=?",
           (msg, rel, post_id))


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
        except Exception as e:
            traceback.print_exc()
            db.log(f"sale-{sale_id}", "Lỗi trình duyệt", str(e).splitlines()[0][:200])
            if job["kind"] == "post" and not job.get("dry_run"):
                db.run("UPDATE posts SET status='failed', error=? WHERE id=? AND status='posting'",
                       (str(e).splitlines()[0][:300], job["post_id"]))
        finally:
            _busy.pop(sale_id, None)
            q.task_done()

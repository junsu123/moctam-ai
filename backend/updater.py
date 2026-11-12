"""Cập nhật phần mềm theo lệnh của sếp (nhắn CEO “cập nhật phần mềm” hoặc /capnhat trên Telegram):
git pull bản mới từ GitHub, chờ lúc sale không có việc dở rồi tự khởi động lại, chạy xong báo lại sếp."""
import json
import os
import shutil
import subprocess
import threading
import time
from pathlib import Path

import db

ROOT = Path(__file__).resolve().parent.parent
restart_hook = None   # main.py gán: restart_self(reason) -> bool
idle_hook = None      # main.py gán: _idle() -> bool
_busy = threading.Lock()
WAIT_IDLE_S = int(os.getenv("UPDATE_WAIT_IDLE_S", "7200"))  # chờ sale rảnh tối đa 2 giờ
CHECK_ALIVE_S = int(os.getenv("UPDATE_CHECK_ALIVE_S", "240"))  # sau chừng này giây mà bản cũ còn chạy = bản mới lỗi
RESTART_FILES = ("requirements.txt", "run.bat", "run.sh", "frontend/index.html")


def _git(*args, timeout=60) -> subprocess.CompletedProcess:
    env = dict(os.environ, GIT_TERMINAL_PROMPT="0", LC_ALL="C")
    return subprocess.run(["git", "-C", str(ROOT), *args], capture_output=True, text=True, timeout=timeout, env=env,
                          encoding="utf-8", errors="replace")


def _head() -> str:
    r = _git("rev-parse", "--short", "HEAD")
    return r.stdout.strip() if r.returncode == 0 else ""


def _err_text(r: subprocess.CompletedProcess) -> str:
    return " ".join((r.stderr or r.stdout or "").split())[:300]


def pull() -> dict:
    """Tải bản mới. Trả về {ok, changed, restart, old, new, commits, msg}. Không bao giờ ghi đè chỗ sếp tự sửa."""
    if not _busy.acquire(blocking=False):
        return {"ok": False, "msg": "Đang cập nhật rồi, sếp chờ chút ạ."}
    try:
        if not shutil.which("git"):
            return {"ok": False, "msg": "Máy chưa cài Git nên em không tự tải bản mới được. Sếp cài Git for Windows "
                                         "(git-scm.com), rồi tải lại phần mềm bằng lệnh git clone thay cho file zip."}
        if not (ROOT / ".git").exists():
            return {"ok": False, "msg": "Thư mục phần mềm không tải bằng git (có thể giải nén từ file zip) nên em không tự "
                                         "cập nhật được. Sếp tải lại bằng git clone để lần sau em tự cập nhật."}
        old = _head()
        dirty = [ln[3:] for ln in _git("status", "--porcelain", "--untracked-files=no").stdout.splitlines() if ln.strip()]
        r = _git("pull", "--ff-only", timeout=300)
        if r.returncode != 0:
            low = (r.stderr or "").lower()
            if "would be overwritten" in low or "local changes" in low:
                why = f"trên máy có file sửa tay trùng với bản mới ({', '.join(dirty[:4])})"
                fix = "Sếp chép riêng phần đã sửa, chạy “git checkout -- <tên file>” rồi nhắn em cập nhật lại."
            elif "could not resolve" in low or "unable to access" in low or "timed out" in low:
                why, fix = "máy không kết nối được GitHub", "Sếp kiểm tra mạng rồi nhắn em cập nhật lại."
            elif "authentication" in low or "permission denied" in low or "could not read username" in low:
                why, fix = "GitHub đòi đăng nhập", "Sếp mở cửa sổ lệnh trong thư mục phần mềm, chạy “git pull” một lần để lưu đăng nhập."
            elif "not possible to fast-forward" in low or "diverg" in low:
                why, fix = "bản trên máy có thay đổi riêng khác bản trên GitHub", "Sếp nhờ người lập trình gộp bản."
            else:
                why, fix = "git báo lỗi", ""
            db.log("ceo", "Cập nhật phần mềm lỗi", _err_text(r))
            return {"ok": False, "old": old, "msg": f"Chưa cập nhật được: {why}. {fix}".strip(), "detail": _err_text(r)}
        new = _head()
        if new == old:
            return {"ok": True, "changed": False, "old": old, "new": new,
                    "msg": f"Phần mềm đang là bản mới nhất ({new}), không cần khởi động lại."}
        commits = [c for c in _git("log", "--format=%s", f"{old}..{new}").stdout.splitlines() if c.strip()]
        files = _git("diff", "--name-only", old, new).stdout.split()
        restart = any((f.startswith("backend/") and f.endswith((".py", ".json"))) or f in RESTART_FILES for f in files)
        db.log("ceo", "Tải bản mới", f"{old} → {new}: " + " · ".join(c[:80] for c in commits[:5]))
        return {"ok": True, "changed": True, "restart": restart, "old": old, "new": new, "commits": commits, "files": files,
                "msg": f"Đã tải bản mới {old} → {new} ({len(commits)} thay đổi)."}
    except subprocess.TimeoutExpired:
        return {"ok": False, "msg": "Tải bản mới quá lâu (mạng chậm), sếp nhắn em thử lại sau ạ."}
    except Exception as e:
        return {"ok": False, "msg": f"Chưa cập nhật được: {str(e)[:200]}"}
    finally:
        _busy.release()


def _say(text: str, via: str):
    import ceo_orders
    ceo_orders.followup(text, via=via)


def _restart_when_idle(new: str, via: str):
    """Chờ sale làm xong việc đang dở rồi khởi động lại. Bản mới chạy lên sẽ tắt bản này; còn sống tức là bản mới lỗi."""
    t0 = time.time()
    told = False
    while time.time() - t0 < WAIT_IDLE_S:
        if idle_hook is None or idle_hook():
            break
        if not told and time.time() - t0 > 300:
            _say("Sale vẫn đang làm dở việc, em chờ xong mới khởi động lại để không đứt bài đang đăng.", via)
            told = True
        time.sleep(15)
    if restart_hook is None or not restart_hook("update"):
        db.set_setting("update_pending", "")
        _say("Em đã tải bản mới nhưng chưa tự khởi động lại được. Sếp đóng cửa sổ run.bat rồi chạy lại giúp em.", via)
        return
    time.sleep(CHECK_ALIVE_S)
    if db.get_settings().get("update_pending"):  # bản mới chưa lên: bản này vẫn đang chạy
        db.set_setting("update_pending", "")
        _say(f"Bản mới {new} chưa chạy được nên phần mềm vẫn chạy bản cũ, sale vẫn làm việc bình thường. "
             "Sếp xem cửa sổ run.bat có báo lỗi không, hoặc vào mục Lỗi.", via)


def run(via: str = "web") -> str:
    """Lệnh của sếp: tải bản mới rồi tự khởi động lại khi rảnh. Trả về câu CEO báo ngay."""
    r = pull()
    if not r.get("ok"):
        return r["msg"]
    if not r.get("changed"):
        return r["msg"]
    news = "; ".join(c[:70] for c in r["commits"][:3]) + ("…" if len(r["commits"]) > 3 else "")
    if not r.get("restart"):
        return r["msg"] + f" Chỉ đổi tài liệu, không cần khởi động lại. Nội dung: {news}"
    db.set_setting("update_pending", json.dumps({"to": r["new"], "via": via, "at": db.now()}))
    threading.Thread(target=_restart_when_idle, args=(r["new"], via), daemon=True).start()
    idle = idle_hook is None or idle_hook()
    return (r["msg"] + f" Nội dung: {news}. "
            + ("Em khởi động lại ngay, khoảng 1 phút nữa chạy xong em báo sếp."
               if idle else "Sale đang làm dở việc, xong việc em tự khởi động lại rồi báo sếp."))


def after_start():
    """Gọi khi phần mềm vừa chạy: nếu đây là bản mới do sếp ra lệnh cập nhật thì báo lại sếp."""
    raw = db.get_settings().get("update_pending")
    if not raw:
        return
    try:
        p = json.loads(raw)
    except Exception:
        p = {}
    head = _head()
    if p.get("to") and head and not head.startswith(p["to"][:7]) and not p["to"].startswith(head[:7]):
        return
    db.set_setting("update_pending", "")

    def later():
        time.sleep(5)  # chờ bot Telegram chạy
        _say(f"✅ Đã cập nhật xong, phần mềm đang chạy bản mới {head}.", p.get("via", "web"))
    threading.Thread(target=later, daemon=True).start()

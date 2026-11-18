"""Máy chủ web: API cho giao diện quản lý công ty Agent AI.
Chạy:  python main.py   rồi mở http://localhost:8000
"""
import json
import os
import subprocess
import sys
import threading
import time
from datetime import timedelta
from pathlib import Path

import uvicorn
from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import FileResponse, HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

import base64
import re

import accounts
import agents
import browser_poster
import db
import errors
import facebook
import ceo
import company
import kpi
import learning
import telegram_bot
import media_folder
import meeting
import scheduler
import workflows
import llm as llm_mod
from llm import llm, MODEL

FRONTEND = Path(__file__).resolve().parent.parent / "frontend"
app = FastAPI(title="Công ty Agent AI - Phòng Kinh doanh")


@app.exception_handler(Exception)
async def _unhandled(request: Request, exc: Exception):
    """Lỗi bất ngờ ở bất kỳ thao tác nào: ghi vào sổ lỗi, trả về thông báo dễ hiểu kèm mã lỗi."""
    eid = errors.report_exc("api", f"Lỗi khi xử lý {request.method} {request.url.path}", exc,
                            screen=request.headers.get("x-screen") or None, action=request.headers.get("x-action", ""))
    return JSONResponse({"detail": f"Phần mềm gặp lỗi: {str(exc).splitlines()[0][:160] if str(exc) else exc.__class__.__name__}. "
                                   f"Xem chi tiết ở màn hình Lỗi (mã #{eid}).", "error_id": eid}, status_code=500)


@app.on_event("startup")
def startup():
    db.init()
    llm.reload()  # khóa API nhập trong phần mềm (nếu có) được ưu tiên hơn file .env
    scheduler.start()
    telegram_bot.start()
    threading.Thread(target=_update_watcher, daemon=True).start()
    import updater
    updater.idle_hook = _idle
    updater.restart_hook = lambda reason: restart_self(reason) or _restart["tried"] == _code_stamp()
    updater.after_start()


# ------------------------------------------------------------------ chung
def _code_stamp() -> str:
    """Dấu vân tay của mã nguồn trên đĩa: đổi khi tải bản mới về mà chưa khởi động lại phần mềm."""
    import hashlib
    h = hashlib.md5()
    here = Path(__file__).resolve().parent
    import ui
    for f in sorted(here.glob("*.py")) + sorted(here.glob("routes/*.py")) + ui.files():
        try:
            st = f.stat()
            h.update(f"{f.name}:{st.st_mtime_ns}:{st.st_size}".encode())
        except OSError:
            pass
    return h.hexdigest()[:12]


STARTED_STAMP = _code_stamp()
STARTED_AT = time.strftime("%Y-%m-%d %H:%M:%S")


# ------------------------------------------------------------------ tự khởi động lại khi có bản mới
ROOT = Path(__file__).resolve().parent.parent
_restart = {"tried": None, "at": None, "reason": ""}


def _idle() -> bool:
    """Không có việc đang dở: sale không mở Chrome, không họp, không tự học."""
    try:
        if browser_poster._busy or any(q.qsize() for q in browser_poster._queues.values()):
            return False
        if meeting.is_running():
            return False
        if learning._running.get("on"):
            return False
    except Exception:
        return False
    return True


def restart_self(reason: str) -> bool:
    """Chạy lại phần mềm bằng run.bat / run.sh (cài thêm thư viện mới nếu có). Bản mới khởi động sẽ tự tắt bản này.
    Nếu bản mới lỗi không chạy được, bản này vẫn tiếp tục chạy."""
    stamp = _code_stamp()
    if _restart["tried"] == stamp and reason != "manual":
        return False
    _restart.update(tried=stamp, at=time.strftime("%H:%M:%S"), reason=reason)
    db.log("minh", "Khởi động lại phần mềm", "Có bản mới trên máy, chạy lại để dùng bản mới" if reason == "update"
           else "Sếp bấm khởi động lại")
    try:
        if os.name == "nt" and (ROOT / "run.bat").exists():
            subprocess.Popen(["cmd", "/c", "start", "Moc Tam AI", str(ROOT / "run.bat"), "restart"], cwd=str(ROOT))
        elif (ROOT / "run.sh").exists() and os.getenv("RESTART_WITH_SCRIPT", "1") == "1":
            log = open(db.DATA_DIR / "app.log", "ab")
            subprocess.Popen(["bash", str(ROOT / "run.sh"), "restart"], cwd=str(ROOT), stdout=log, stderr=log,
                             start_new_session=True)
        else:
            log = open(db.DATA_DIR / "app.log", "ab")
            subprocess.Popen([sys.executable, str(Path(__file__).resolve())], cwd=str(Path(__file__).resolve().parent),
                             stdout=log, stderr=log, start_new_session=True)
        return True
    except Exception as e:
        errors.report_exc("api", "Không tự khởi động lại được phần mềm", e)
        return False


def _update_watcher():
    """Mỗi 30 giây xem mã nguồn trên máy có đổi không (vừa tải bản mới). Đổi và ổn định (đã tải xong) thì chờ lúc rảnh
    rồi tự khởi động lại bằng bản mới."""
    prev = None
    while True:
        time.sleep(30)
        try:
            cur = _code_stamp()
            if cur != STARTED_STAMP and cur == prev and _idle():
                restart_self("update")
            prev = cur
        except Exception as e:
            print("[update]", e)


@app.post("/api/admin/restart")
def admin_restart():
    if not restart_self("manual"):
        raise HTTPException(500, "Không khởi động lại được, hãy đóng cửa sổ run.bat rồi chạy lại")
    return {"ok": True, "pid": os.getpid()}


@app.get("/api/health")
def health():
    return {"ok": True, "ai_live": llm.live, "model": llm_mod.model_for("posts") if llm.live else "mô phỏng",
            "build": STARTED_STAMP, "stale": _code_stamp() != STARTED_STAMP, "pid": os.getpid(), "started_at": STARTED_AT,
            "restarting": _restart["at"], "idle": _idle(), "time": db.tz_info()}


class AgentProfile(BaseModel):
    name: str | None = None
    face: str | None = None  # ảnh dạng data URL (base64)


@app.put("/api/agents/{aid}")
def agent_profile(aid: str, p: AgentProfile):
    """Sếp đổi tên / ảnh mặt của một agent (cả nhân viên sale)."""
    try:
        if p.face:
            agents.set_face(aid, p.face)
        if p.name is not None:
            agents.rename(aid, p.name)
    except ValueError as e:
        raise HTTPException(400, str(e))
    return {"id": aid, "name": agents.name_of(aid), "face": agents.face_of(aid)}


@app.delete("/api/agents/{aid}/profile")
def agent_profile_reset(aid: str, what: str = "all"):
    return agents.reset_profile(aid, what)


@app.get("/api/agents")
def list_agents():
    out = agents.public_list()
    import growth
    growth_today = growth.today()
    login_txt = {"ok": "Nick sẵn sàng", "not_logged_in": "Chờ sếp đăng nhập Facebook", "checkpoint": "Nick bị checkpoint, đã dừng"}
    sales_by_id = {f"sale-{r['id']}": r for r in db.q("SELECT id, login_status FROM sales")}
    for a in out:
        a["status"] = workflows.STATUS.get(a["id"]) or {"state": "idle", "text": "Đang sẵn sàng"}
        a["level"] = learning.level_for((db.one("SELECT xp FROM agent_progress WHERE agent_id=?", (a["id"],)) or {"xp": 0})["xp"])
        if a["id"] in sales_by_id:
            a["login_status"] = sales_by_id[a["id"]]["login_status"]
            if a["status"].get("state") == "idle":
                a["status"] = {"state": "idle", "text": login_txt.get(a["login_status"], "")}
        a["tasks"] = db.q("SELECT * FROM tasks WHERE agent_id=? AND status!='done' ORDER BY id DESC LIMIT 5", (a["id"],))
        a["progress"] = learning.progress(a["id"])
        a["recent"] = db.q("""SELECT action, detail, created_at FROM activity WHERE agent_id=? AND action NOT IN ('Tự học lúc rảnh')
                              ORDER BY id DESC LIMIT 3""", (a["id"],))
        a["learned_today"] = (growth_today.get(a["id"]) or {}).get("learned", 0)
    return out


@app.get("/api/dashboard")
def dashboard():
    return {"stats": workflows.stats(),
            "activity": db.q("SELECT * FROM activity ORDER BY id DESC LIMIT 30"),
            "meeting_running": meeting.is_running()}


# ------------------------------------------------------------------ các nhóm API: backend/routes/*.py
# Mỗi file routes/xxx.py là một đoạn của main.py, chạy chung không gian tên với main.py (dùng chung app, db, helper),
# đúng thứ tự dưới đây (thứ tự đăng ký đường dẫn giữ nguyên như khi còn là một file). Thêm nhóm mới: tạo file rồi thêm tên vào ROUTES.
ROUTES = ["products", "groups", "templates", "my_groups", "prospects", "posts", "leads", "meeting", "settings", "sales", "company", "errors", "ceo", "system", "kpi", "learning", "comments", "post_target", "friends", "replies", "fb_rules", "website"]


def _include(name: str):
    f = Path(__file__).resolve().parent / "routes" / f"{name}.py"
    exec(compile(f.read_text(encoding="utf-8"), str(f), "exec"), globals())


for _r in ROUTES:
    _include(_r)


# ------------------------------------------------------------------ giao diện
@app.get("/", response_class=HTMLResponse)
def index():
    import ui
    body = ui.page()  # ghép từ frontend/app.html + css/ views/ js/
    return ('<!doctype html><html lang="vi"><head><meta charset="utf-8">'
            '<meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover">'
            '<style>html,body{height:100%;margin:0}[hidden]{display:none!important}</style>'
            '<script>window.__BACKEND__=true</script>'
            f'</head><body>{body}</body></html>')


app.mount("/static", StaticFiles(directory=FRONTEND), name="static")
app.mount("/media", StaticFiles(directory=db.MEDIA_DIR), name="media")   # chỉ ảnh sản phẩm
app.mount("/shots", StaticFiles(directory=db.SHOTS_DIR), name="shots")   # ảnh chụp kết quả đăng bài
app.mount("/faces", StaticFiles(directory=agents.faces_dir()), name="faces")   # ảnh mặt agent sếp tải lên

# ------------------------------------------------------------------ chỉ cho chạy 1 bản phần mềm
def _port_owners(port: int) -> list:
    try:
        import psutil
    except ImportError:
        return []
    pids = set()
    try:
        for c in psutil.net_connections(kind="tcp"):
            if c.laddr and c.laddr.port == port and c.status == psutil.CONN_LISTEN and c.pid and c.pid != os.getpid():
                pids.add(c.pid)
    except Exception:
        pass
    out = []
    for pid in pids:
        try:
            out.append(psutil.Process(pid))
        except Exception:
            pass
    return out


def _is_this_app(p) -> bool:
    try:
        cmd = " ".join(p.cmdline()).lower()
        here = str(Path(__file__).resolve().parent).lower()
        cwd = ""
        try:
            cwd = p.cwd().lower()
        except Exception:
            pass
        return "python" in p.name().lower() and "main.py" in cmd and (cwd == here or here in cmd)
    except Exception:
        return False


def _kill_tree(p):
    """Tắt một bản phần mềm cùng Chrome nó mở. Không tắt chính mình (bản mới có thể là tiến trình con của bản cũ
    khi bản cũ tự khởi động lại)."""
    me = os.getpid()
    try:
        for ch in p.children(recursive=True):
            if ch.pid == me:
                continue
            try:
                ch.kill()
            except Exception:
                pass
        p.kill()
        p.wait(10)
    except Exception:
        pass


def _listening(p) -> bool:
    """Tiến trình có đang mở cổng web không (bản phần mềm thật sự đang chạy, khác với tiến trình khởi chạy)."""
    try:
        import psutil
        conns = (getattr(p, "net_connections", None) or p.connections)(kind="tcp")
        return any(c.status == psutil.CONN_LISTEN for c in conns)
    except Exception:
        return False


def _kill_other_instances():
    """Tắt mọi bản phần mềm này đang chạy (bản cũ, bản chạy trùng), kể cả bản không giữ cổng.
    Không tắt tiến trình khởi chạy của chính mình: trên Windows, .venv\\Scripts\\python.exe chỉ là trình khởi chạy,
    nó mở Python thật thành tiến trình con và tắt nó là tắt luôn bản đang khởi động."""
    try:
        import psutil
    except ImportError:
        return
    me = os.getpid()
    try:
        ancestors = {a.pid for a in psutil.Process(me).parents()}
    except Exception:
        ancestors = set()
    for p in psutil.process_iter(["name"]):
        if p.pid == me:
            continue
        if p.pid in ancestors and not _listening(p):
            continue  # trình khởi chạy của chính mình (hoặc cửa sổ run.bat): giữ nguyên
        if _is_this_app(p):
            print(f"[!] Phát hiện phần mềm đang chạy sẵn (PID {p.pid}, có thể là bản cũ). Đang tắt để chạy bản này...")
            try:
                REPLACED_FLAG.write_text(str(p.pid))  # cửa sổ run.bat của bản cũ thấy cờ này thì tự đóng, không báo lỗi
            except Exception:
                pass
            _kill_tree(p)


def _bind(host: str, port: int):
    """Mở cổng độc quyền. Trên Windows, uvicorn mặc định cho 2 phần mềm dùng chung 1 cổng (SO_REUSEADDR):
    bản cũ và bản mới cùng chạy, giành nhau yêu cầu và cùng mở Chrome của sale. Ở đây chỉ cho 1 bản chạy:
    gặp bản cũ của chính phần mềm này thì tắt nó, gặp chương trình khác thì báo rõ."""
    import socket
    for attempt in range(4):
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        if os.name == "nt":
            s.setsockopt(socket.SOL_SOCKET, socket.SO_EXCLUSIVEADDRUSE, 1)
        else:
            s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        try:
            s.bind((host, port))
            return s
        except OSError:
            s.close()
        owners = _port_owners(port)
        ours = [p for p in owners if _is_this_app(p)]
        if ours:
            for p in ours:
                print(f"[!] Phần mềm đang chạy sẵn một bản khác (PID {p.pid}, có thể là bản cũ). Đang tắt bản đó để chạy bản này...")
                _kill_tree(p)
            time.sleep(2)
            continue
        if owners:
            names = ", ".join(f"{p.name()} (PID {p.pid})" for p in owners)
            print(f"[x] Cổng {port} đang bị chương trình khác dùng: {names}.\n"
                  f"    Tắt chương trình đó, hoặc đặt PORT=8010 trong file .env rồi chạy lại.")
            sys.exit(1)
        time.sleep(2)  # cổng vừa được giải phóng, chờ hệ điều hành nhả hẳn
    print(f"[x] Không mở được cổng {port}. Có thể phần mềm đang chạy ở một cửa sổ khác: đóng hết các cửa sổ run.bat "
          f"(hoặc Task Manager → tắt python.exe) rồi chạy lại.")
    sys.exit(1)


# ------------------------------------------------------------------ tắt êm, nhường chỗ cho bản mới
INSTANCE_FILE = db.DATA_DIR / "instance.json"
REPLACED_FLAG = db.DATA_DIR / "replaced.flag"
_server = {"obj": None, "replaced": False, "token": None}


class Quit(BaseModel):
    token: str


@app.post("/api/admin/quit")
def admin_quit(q: Quit, request: Request):
    """Bản mới khởi động gọi vào đây để bản đang chạy tự tắt êm (không phải bị buộc tắt)."""
    if not _server["token"] or q.token != _server["token"] or (request.client and request.client.host not in ("127.0.0.1", "::1", "localhost")):
        raise HTTPException(403, "Không có quyền")
    _server["replaced"] = True
    if _server["obj"]:
        _server["obj"].should_exit = True
    return {"ok": True, "pid": os.getpid()}


def _ask_old_to_quit():
    """Nhờ bản đang chạy (bản có hỗ trợ) tự tắt êm, chờ tối đa 20 giây."""
    try:
        info = json.loads(INSTANCE_FILE.read_text(encoding="utf-8"))
    except Exception:
        return
    pid = info.get("pid")
    if not pid or pid == os.getpid():
        return
    try:
        import psutil
        if not psutil.pid_exists(pid):
            return
    except ImportError:
        return
    try:
        import httpx
        httpx.post(f"http://127.0.0.1:{info.get('port', 8000)}/api/admin/quit", json={"token": info.get("token", "")}, timeout=5)
        print(f"[!] Đang nhờ bản phần mềm đang chạy (PID {pid}) tự tắt để chạy bản này...")
    except Exception:
        return
    end = time.time() + 20
    while time.time() < end and psutil.pid_exists(pid):
        try:
            if psutil.Process(pid).status() == psutil.STATUS_ZOMBIE:
                break
        except Exception:
            break
        time.sleep(0.5)


def _quiet_console():
    """Windows: tắt chế độ chọn chữ (QuickEdit) của cửa sổ đen. Khi đang chọn chữ, Windows dừng mọi chữ in ra
    nên phần mềm bị treo cho tới khi bấm Esc."""
    if os.name != "nt":
        return
    try:
        import ctypes
        k = ctypes.windll.kernel32
        h = k.GetStdHandle(-10)
        mode = ctypes.c_uint32()
        if k.GetConsoleMode(h, ctypes.byref(mode)):
            k.SetConsoleMode(h, (mode.value & ~0x0040) | 0x0080)  # bỏ ENABLE_QUICK_EDIT_MODE, giữ EXTENDED_FLAGS
    except Exception:
        pass


def _cleanup_children():
    """Tắt Chrome và các tiến trình con còn lại để không giữ hồ sơ của sale sau khi phần mềm tắt."""
    try:
        import psutil
        for ch in psutil.Process(os.getpid()).children(recursive=True):
            try:
                name = ch.name().lower()
                # chỉ tắt Chrome và trình điều khiển trình duyệt; không đụng bản phần mềm mới vừa được mở để thay bản này
                if any(k in name for k in ("chrom", "node", "playwright", "headless_shell", "msedge")) and not _is_this_app(ch):
                    ch.kill()
            except Exception:
                pass
    except Exception:
        pass


if __name__ == "__main__":
    import secrets
    host, port = os.getenv("HOST", "127.0.0.1"), int(os.getenv("PORT", 8000))
    _quiet_console()
    try:  # cờ "đã bị thay" còn sót từ lâu (cửa sổ cũ không đọc tới): bỏ đi
        if REPLACED_FLAG.exists() and time.time() - REPLACED_FLAG.stat().st_mtime > 120:
            REPLACED_FLAG.unlink()
    except Exception:
        pass
    _ask_old_to_quit()
    _kill_other_instances()
    sock = _bind(host, port)
    _server["token"] = secrets.token_hex(16)
    try:
        INSTANCE_FILE.write_text(json.dumps({"pid": os.getpid(), "port": port, "token": _server["token"]}), encoding="utf-8")
    except Exception:
        pass
    print(f"Phần mềm đang chạy: http://localhost:{port}  (để tắt: đóng cửa sổ này, hoặc bấm Ctrl+C)")
    server = uvicorn.Server(uvicorn.Config(app, host=host, port=port, reload=False))
    _server["obj"] = server
    code = 0
    try:
        server.run(sockets=[sock])
    except KeyboardInterrupt:
        pass  # bấm Ctrl+C: tắt bình thường, không phải lỗi
    except SystemExit as e:
        code = e.code if isinstance(e.code, int) else 1
    finally:
        _cleanup_children()
        try:
            if json.loads(INSTANCE_FILE.read_text(encoding="utf-8")).get("pid") == os.getpid():
                INSTANCE_FILE.unlink()
        except Exception:
            pass
    if _server["replaced"]:
        try:
            REPLACED_FLAG.write_text(str(os.getpid()))
        except Exception:
            pass
        print("Đã chuyển sang bản mới ở cửa sổ khác. Cửa sổ này tự đóng.")
    else:
        print("Đã tắt phần mềm.")
    sys.exit(code)

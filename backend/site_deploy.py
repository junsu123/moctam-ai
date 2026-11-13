"""Đưa website (data/site/) lên hosting và tự đồng bộ khi tin tức / sản phẩm thay đổi.

Cách đăng (site_deploy_mode):
  auto  FTPS, máy chủ không nhận TLS thì tự chuyển FTP thường (cổng 22 thì SFTP)
  ftps / ftp / sftp
  http  cổng nhận PHP qua HTTPS: tải mt-sync.php lên public_html một lần, phần mềm đẩy tệp qua cổng 443
        (dùng khi mạng / hosting chặn cổng FTP). Cổng chỉ ghi tệp tĩnh, không nhận .php/.htaccess, có mã bí mật.
Chỉ tải tệp thay đổi (so mã md5 lần trước), xóa trên hosting tệp đã gỡ (bài gỡ đăng, sản phẩm ẩn).
Tự đồng bộ: dữ liệu website đổi (bài đăng / gỡ, sản phẩm, thông tin công ty) thì ~2 phút sau Vy dựng lại và đẩy lên.
"""
import ftplib
import hashlib
import json
import re
import secrets
import socket
import ssl
import threading
import time
from pathlib import Path

import db

MODES = {"auto": "Tự chọn", "ftps": "FTPS", "ftp": "FTP", "sftp": "SFTP", "http": "Cổng nhận PHP (HTTPS)"}
SYNC_FILE = "mt-sync.php"
MANIFEST = db.DATA_DIR / "site_deploy.json"
ROOT_HINTS = (".well-known", "cgi-bin", "index.html", "index.php", ".htaccess", "default.html", "index.htm")


def _st() -> dict:
    return db.get_settings()


def perms(st: dict | None = None) -> tuple[str, str]:
    """Quyền tệp / thư mục đặt sau khi tải lên (mặc định 755 / 755; không cho quyền ghi cho người khác)."""
    st = st or _st()

    def ok(v, d):
        v = str(v or "").strip()
        return v if re.fullmatch(r"[0-7]{3}", v) and not int(v[2]) & 2 and int(v[0]) & 4 else d
    return ok(st.get("site_chmod_file"), "755"), ok(st.get("site_chmod_dir"), "755")


def _site_dir() -> Path:
    import website
    return website.SITE_DIR


def clean_host(h: str) -> tuple[str, int | None]:
    """'ftp://user@ftp.moctamvn.vn:21/public_html' → ('ftp.moctamvn.vn', 21)."""
    h = re.sub(r"^[a-z]+://", "", (h or "").strip(), flags=re.I).split("/")[0].split("@")[-1].strip()
    port = None
    if h.count(":") == 1:
        h, p = h.split(":")
        port = int(p) if p.strip().isdigit() else None
    return h.strip().lower().rstrip("."), port


def domain(st: dict | None = None) -> str:
    return clean_host((st or _st()).get("site_domain") or "")[0]


def sync_url(st: dict | None = None) -> str:
    st = st or _st()
    u = (st.get("site_sync_url") or "").strip()
    if u:
        return u if re.match(r"^https?://", u) else "https://" + u
    d = domain(st)
    return f"https://{d}/{SYNC_FILE}" if d else ""


def configured(st: dict | None = None) -> bool:
    st = st or _st()
    if (st.get("site_deploy_mode") or "auto") == "http":
        return bool(sync_url(st) and st.get("site_sync_token"))
    return bool(clean_host(st.get("site_ftp_host") or "")[0] and (st.get("site_ftp_user") or "").strip() and st.get("site_ftp_pass"))


# ---------------------------------------------------------------- lỗi dễ hiểu
def explain(e: BaseException, mode: str, host: str, port: int | None, stage: str = "") -> str:
    s = str(e)
    d = domain() or "tenmien.vn"
    if isinstance(e, socket.gaierror):
        return (f"Không tìm thấy máy chủ “{host}”. Điền đúng máy chủ: thường là ftp.{d}, {d} hoặc địa chỉ IP hosting "
                "ghi trong email kích hoạt hosting. Tên miền mới trỏ về hosting thì chờ vài giờ hoặc dùng IP.")
    if isinstance(e, ConnectionRefusedError):
        return (f"Máy chủ {host} từ chối cổng {port}. Kiểm tra cổng (FTP 21, SFTP 22 hoặc cổng riêng hosting cấp), "
                "hoặc chọn cách đăng “Cổng nhận PHP (HTTPS)”.")
    if isinstance(e, (socket.timeout, TimeoutError)) or "timed out" in s.lower():
        if stage == "data":
            return ("Đăng nhập được nhưng kênh truyền tệp bị chặn (chế độ thụ động / passive). Thử bỏ FTPS (chọn FTP), "
                    "hoặc chọn “Cổng nhận PHP (HTTPS)”, hoặc hỏi hosting mở cổng passive.")
        return (f"Hết thời gian chờ khi nối tới {host}:{port}. Mạng hoặc tường lửa đang chặn cổng này, hoặc hosting đã khóa IP "
                "của máy (thường do nhập sai mật khẩu nhiều lần: vào cPanel → IP Blocker / hỏi hosting mở khóa). "
                "Cách chắc chắn: chọn “Cổng nhận PHP (HTTPS)”.")
    if isinstance(e, ssl.SSLError) or "ssl" in s.lower() or s[:3] in ("534", "522", "431"):
        return ("Máy chủ không nhận kết nối bảo mật FTPS (" + s[:80] + "). Chọn cách đăng “Tự chọn” hoặc “FTP”.")
    if s[:3] == "530" or e.__class__.__name__ == "AuthenticationException":
        return ("Sai tài khoản hoặc mật khẩu. Tài khoản FTP phụ của cPanel có dạng ten@" + d + "; tài khoản chính là tên đăng nhập "
                "cPanel. Đặt lại mật khẩu ở cPanel → FTP Accounts rồi điền lại (sai nhiều lần hosting sẽ khóa IP).")
    if s[:3] in ("550", "553"):
        return f"Hosting không cho ghi vào thư mục ({s[:100]}). Kiểm tra “Thư mục trên hosting” (thường /public_html) và quyền tài khoản FTP."
    if isinstance(e, ModuleNotFoundError):
        return "Máy chưa cài gói SFTP: chạy “pip install paramiko” (hoặc chạy lại run.bat) rồi thử lại."
    return f"{mode.upper()} lỗi: {s[:200] or e.__class__.__name__}"


# ---------------------------------------------------------------- các cách kết nối
class _ReuseFTPS(ftplib.FTP_TLS):
    """FTPS dùng lại phiên TLS ở kênh dữ liệu (vsftpd / Pure-FTPd của nhiều hosting bắt buộc, không thì báo 522)."""
    def ntransfercmd(self, cmd, rest=None):
        conn, size = ftplib.FTP.ntransfercmd(self, cmd, rest)
        if self._prot_p:
            conn = self.context.wrap_socket(conn, server_hostname=self.host, session=self.sock.session)
        return conn, size


class FtpConn:
    def __init__(self, host, port, user, pw, tls: bool):
        self.mode = "ftps" if tls else "ftp"
        self.stage = "connect"
        ftp = _ReuseFTPS() if tls else ftplib.FTP()
        ftp.connect(host, port or 21, timeout=25)
        self.stage = "login"
        ftp.login(user, pw)
        if tls:
            ftp.prot_p()
        ftp.set_pasv(True)
        self.ftp, self.made = ftp, set()
        self.stage = "data"

    def is_dir(self, p: str) -> bool:
        cur = self.ftp.pwd()
        try:
            self.ftp.cwd(p or "/")
            return True
        except ftplib.all_errors:
            return False
        finally:
            try:
                self.ftp.cwd(cur)
            except ftplib.all_errors:
                pass

    def names(self, p: str) -> list[str]:
        try:
            return [x.rsplit("/", 1)[-1] for x in self.ftp.nlst(p or ".")]
        except ftplib.error_perm:
            return []

    def mkdirs(self, d: str):
        cur = "/" if d.startswith("/") else ""
        for x in [x for x in d.split("/") if x]:
            cur = f"{cur}{x}/"
            if cur in self.made:
                continue
            try:
                self.ftp.mkd(cur.rstrip("/"))
            except ftplib.error_perm:
                pass
            self.made.add(cur)

    def put(self, dest: str, data: bytes):
        import io
        self.ftp.storbinary(f"STOR {dest}", io.BytesIO(data))

    def chmod(self, path: str, mode: str) -> bool:
        try:
            self.ftp.sendcmd(f"SITE CHMOD {mode} {path}")
            return True
        except ftplib.all_errors:
            return False

    def delete(self, dest: str):
        try:
            self.ftp.delete(dest)
        except ftplib.all_errors:
            pass

    def close(self):
        try:
            self.ftp.quit()
        except Exception:
            try:
                self.ftp.close()
            except Exception:
                pass


class SftpConn:
    def __init__(self, host, port, user, pw):
        import paramiko
        self.mode, self.stage = "sftp", "connect"
        self.t = paramiko.Transport(socket.create_connection((host, port or 22), timeout=25))
        self.t.banner_timeout = 25
        self.stage = "login"
        self.t.connect(username=user, password=pw)
        self.sftp, self.made = paramiko.SFTPClient.from_transport(self.t), set()
        self.stage = "data"

    def is_dir(self, p: str) -> bool:
        import stat
        try:
            return stat.S_ISDIR(self.sftp.stat(p or ".").st_mode)
        except OSError:
            return False

    def names(self, p: str) -> list[str]:
        try:
            return self.sftp.listdir(p or ".")
        except OSError:
            return []

    def mkdirs(self, d: str):
        cur = "/" if d.startswith("/") else ""
        for x in [x for x in d.split("/") if x]:
            cur = f"{cur}{x}/"
            if cur in self.made:
                continue
            try:
                self.sftp.mkdir(cur.rstrip("/"))
            except OSError:
                pass
            self.made.add(cur)

    def put(self, dest: str, data: bytes):
        with self.sftp.open(dest, "wb") as f:
            f.write(data)

    def chmod(self, path: str, mode: str) -> bool:
        try:
            self.sftp.chmod(path, int(mode, 8))
            return True
        except OSError:
            return False

    def delete(self, dest: str):
        try:
            self.sftp.remove(dest)
        except OSError:
            pass

    def close(self):
        try:
            self.t.close()
        except Exception:
            pass


class HttpConn:
    """Gọi cổng mt-sync.php trên hosting (HTTPS cổng 443)."""
    def __init__(self, url: str, token: str):
        import httpx
        self.mode, self.stage, self.url, self.token = "http", "connect", url, token
        self.c = httpx.Client(timeout=60, follow_redirects=True, headers={"X-MT-Token": token, "User-Agent": "MocTam-Sync/1"})
        r = self._call("ping")
        self.writable = r.get("writable", True)
        self.version = int(r.get("v", 1))
        self.fm, self.dm = perms()
        self.stage = "data"

    def _call(self, op: str, path: str = "", data: bytes = b"") -> dict:
        params = {"op": op, "path": path}
        if op == "put":
            params.update(fm=self.fm, dm=self.dm)
        r = self.c.post(self.url, params=params, content=data)
        if r.status_code == 404:
            raise RuntimeError(f"Chưa có {SYNC_FILE} trên hosting ({self.url}). Tải tệp ở mục Đăng lên hosting rồi tải lên thư mục public_html.")
        if r.status_code == 403:
            raise RuntimeError(f"{SYNC_FILE} trên hosting có mã khác máy này. Tải lại tệp mới rồi ghi đè lên hosting.")
        try:
            j = r.json()
        except ValueError:
            raise RuntimeError(f"{self.url} trả về HTTP {r.status_code}, không phải cổng nhận của phần mềm (hosting chưa chạy PHP hoặc tường lửa chặn).")
        if not j.get("ok"):
            raise RuntimeError(f"Cổng nhận báo lỗi: {j.get('error')} ({path})")
        return j

    def is_dir(self, p):
        return True

    def names(self, p):
        return []

    def mkdirs(self, d):
        pass

    def put(self, dest: str, data: bytes):
        self._call("put", dest.lstrip("/"), data)

    def chmod(self, path: str, mode: str) -> bool:
        return self.version >= 2  # cổng bản 2 tự đặt quyền khi ghi tệp

    def delete(self, dest: str):
        try:
            self._call("del", dest.lstrip("/"))
        except Exception:
            pass

    def close(self):
        self.c.close()


def _modes(st: dict, port: int | None) -> list[str]:
    m = st.get("site_deploy_mode") or "auto"
    if m != "auto":
        return [m]
    if port == 22:
        return ["sftp"]
    if st.get("site_deploy_ok_mode") in ("ftps", "ftp", "sftp"):
        return [st["site_deploy_ok_mode"]]
    return ["ftps", "ftp"] if st.get("site_ftp_tls", "1") != "0" else ["ftp"]


def open_conn(st: dict | None = None):
    """Mở kết nối theo cách đăng đã chọn. Lỗi → RuntimeError tiếng Việt dễ hiểu."""
    st = st or _st()
    if (st.get("site_deploy_mode") or "auto") == "http":
        url = sync_url(st)
        if not url:
            raise ValueError("Chưa điền tên miền (tab Thông tin công ty) để biết địa chỉ cổng nhận")
        if not st.get("site_sync_token"):
            raise ValueError(f"Chưa tạo cổng nhận: bấm “Tải {SYNC_FILE}” rồi tải lên public_html")
        try:
            return HttpConn(url, st["site_sync_token"])
        except RuntimeError:
            raise
        except Exception as e:
            raise RuntimeError(explain(e, "http", domain(st), 443)) from e
    host, port = clean_host(st.get("site_ftp_host") or "")
    user, pw = (st.get("site_ftp_user") or "").strip(), st.get("site_ftp_pass") or ""
    if not (host and user and pw):
        raise ValueError("Chưa điền máy chủ FTP, tài khoản và mật khẩu ở mục Website → Đăng lên hosting")
    errs = []
    for m in _modes(st, port):
        try:
            c = SftpConn(host, port, user, pw) if m == "sftp" else FtpConn(host, port, user, pw, m == "ftps")
            if (st.get("site_deploy_mode") or "auto") == "auto" and st.get("site_deploy_ok_mode") != m:
                db.set_setting("site_deploy_ok_mode", m)
            return c
        except Exception as e:
            msg = explain(e, m, host, port or (22 if m == "sftp" else 21))
            errs.append(msg)
            tls_fail = isinstance(e, ssl.SSLError) or str(e)[:3] in ("534", "522", "431", "500", "502", "504") or "ssl" in str(e).lower()
            if not (m == "ftps" and tls_fail):
                break  # chỉ chuyển FTP thường khi lỗi nằm ở TLS
    raise RuntimeError(errs[-1])


def find_root(conn, st: dict) -> str:
    """Thư mục web thật trên hosting: thư mục đã điền nếu có, không thì dò cPanel / DirectAdmin / Plesk."""
    if conn.mode == "http":
        return ""
    want = (st.get("site_ftp_dir") or "/public_html").strip() or "/"
    want = "/" + want.strip("/") if want.strip("/") else "/"
    d = domain(st)
    cands = [want, f"/domains/{d}/public_html", "/public_html", "/httpdocs", "/htdocs", "/www", f"/{d}/public_html", f"/{d}"]
    if conn.mode == "sftp":  # SFTP đăng nhập ở thư mục nhà: thử cả đường dẫn tương đối
        cands = [x for c in cands for x in (c, c.lstrip("/"))]
    seen = []
    for c in cands:
        if c in seen or not c.strip("/") or (d == "" and "//" in c):
            continue
        seen.append(c)
        if conn.is_dir(c):
            return c.rstrip("/") or "/"
    top = conn.names("." if conn.mode == "sftp" else "/")
    if any(x in ROOT_HINTS for x in top):  # tài khoản FTP mở thẳng vào thư mục web
        return "." if conn.mode == "sftp" else "/"
    return want


def _join(root: str, rel: str) -> str:
    if root in ("", "."):
        return rel
    return f"{root.rstrip('/')}/{rel}" if root != "/" else f"/{rel}"


def _local_files() -> dict[str, tuple[Path, str]]:
    out = {}
    base = _site_dir()
    for f in sorted(base.rglob("*")):
        if f.is_file():
            out[f.relative_to(base).as_posix()] = (f, hashlib.md5(f.read_bytes()).hexdigest())
    return out


def _manifest() -> dict:
    try:
        return json.loads(MANIFEST.read_text())
    except Exception:
        return {}


# ---------------------------------------------------------------- đăng
_lock = threading.Lock()


def deploy(full: bool = False, who: str = "sếp") -> dict:
    """Dựng (nếu chưa) rồi tải lên hosting những tệp thay đổi, xóa tệp đã gỡ."""
    import website
    if not _lock.acquire(timeout=1):
        raise RuntimeError("Đang đăng website lên hosting, đợi lượt này xong")
    try:
        st = _st()
        if not (_site_dir() / "index.html").exists():
            website.build()
        conn = open_conn(st)
        up = rm = 0
        try:
            root = find_root(conn, st)
            if conn.mode != "http" and root != (st.get("site_ftp_dir") or "/public_html") and root not in ("/", "."):
                db.set_setting("site_ftp_dir", root)
            fm, dm = perms(st)
            key = f"{conn.mode}|{clean_host(st.get('site_ftp_host') or '')[0] if conn.mode != 'http' else sync_url(st)}|{root}|{fm}{dm}"
            old = _manifest()
            had = old.get("files", {}) if (old.get("key") == key and not full) else {}
            files = _local_files()
            todo = [r for r, (_, h) in files.items() if had.get(r) != h]
            todo.sort(key=lambda r: (r.endswith("index.html") and "/" not in r, r == "sitemap.xml"))  # trang chủ, sitemap lên sau cùng
            done = dict(had)
            dirs_done, bad_perm = set(), 0
            try:
                for rel in todo:
                    if rel == SYNC_FILE:
                        continue
                    dest = _join(root, rel)
                    if "/" in dest:
                        conn.mkdirs(dest.rsplit("/", 1)[0])
                    if conn.mode != "http":  # thư mục con (không đụng thư mục gốc web, VD public_html của cPanel để 750)
                        parts = rel.split("/")[:-1]
                        for i in range(1, len(parts) + 1):
                            sub = "/".join(parts[:i])
                            if sub not in dirs_done:
                                dirs_done.add(sub)
                                bad_perm += not conn.chmod(_join(root, sub), dm)
                    conn.put(dest, files[rel][0].read_bytes())
                    bad_perm += not conn.chmod(dest, fm)
                    done[rel] = files[rel][1]
                    up += 1
                for rel in [r for r in had if r not in files]:
                    conn.delete(_join(root, rel))
                    done.pop(rel, None)
                    rm += 1
            finally:
                MANIFEST.write_text(json.dumps({"key": key, "files": done}))
        except Exception as e:
            raise RuntimeError(e if isinstance(e, RuntimeError) else explain(e, conn.mode, clean_host(st.get("site_ftp_host") or "")[0], None, conn.stage)) from e
        finally:
            conn.close()
        where = sync_url(st).rsplit("/", 1)[0] if conn.mode == "http" else f"{clean_host(st.get('site_ftp_host') or '')[0]}{'' if root.startswith('/') else '/'}{root}"
        db.set_setting("site_last_deploy", db.now())
        _sync["fail_at"] = 0.0  # đăng được rồi thì tự đồng bộ chạy lại ngay, không chờ hết 30 phút
        warn = ""
        if bad_perm:
            warn = (f" · {bad_perm} tệp / thư mục chưa đặt được quyền {fm}/{dm}: "
                    + (f"tải lại {SYNC_FILE} mới (bản cũ không đặt quyền)" if conn.mode == "http"
                       else "hosting không cho đổi quyền qua FTP, vào cPanel → File Manager chọn tệp → Permissions"))
        db.set_setting("site_deploy_msg", f"OK: {up} tệp mới/sửa, xóa {rm} tệp cũ ({MODES.get(conn.mode, conn.mode)}){warn}")
        if up or rm:
            db.log("vy", "Đăng website lên hosting", f"{who}: tải {up} tệp, xóa {rm} tệp cũ ở {where} ({MODES.get(conn.mode)})")
        return {"files": up, "deleted": rm, "unchanged": len(files) - up, "host": where, "dir": root, "mode": conn.mode,
                "perms": f"{fm}/{dm}", "perm_fail": bad_perm, "warn": warn.strip(" ·")}
    except Exception as e:
        db.set_setting("site_deploy_msg", "LỖI: " + str(e)[:300])
        raise
    finally:
        _lock.release()


def test() -> dict:
    """Kiểm tra từng bước: tìm máy chủ → mở cổng → đăng nhập → thư mục web → ghi thử."""
    st = _st()
    steps = []

    def step(name, ok, msg=""):
        steps.append({"name": name, "ok": ok, "msg": msg})
        return ok
    mode = st.get("site_deploy_mode") or "auto"
    if mode == "http":
        from urllib.parse import urlparse
        host, port = urlparse(sync_url(st)).hostname or domain(st), 443
    else:
        host, port = clean_host(st.get("site_ftp_host") or "")
    if not configured(st):
        step("Thông tin kết nối", False, "Cổng nhận PHP cần tên miền và tệp mt-sync.php đã tải lên" if mode == "http"
             else "Chưa điền đủ máy chủ, tài khoản, mật khẩu")
        return {"ok": False, "steps": steps}
    try:
        ip = socket.gethostbyname(host)
        step("Tìm máy chủ", True, f"{host} → {ip}")
    except Exception as e:
        step("Tìm máy chủ", False, explain(e, mode, host, port))
        return {"ok": False, "steps": steps}
    if mode != "http":
        ports = [port] if port else ([22] if mode == "sftp" else [21])
        for p in ports:
            try:
                socket.create_connection((host, p), timeout=10).close()
                step("Mở cổng", True, f"cổng {p} mở")
            except Exception as e:
                step("Mở cổng", False, explain(e, mode, host, p))
                if mode == "auto":
                    try:
                        socket.create_connection((host, 22), timeout=6).close()
                        steps[-1]["msg"] += " Cổng 22 (SFTP) đang mở: thử chọn cách đăng SFTP."
                    except Exception:
                        pass
                return {"ok": False, "steps": steps}
    try:
        conn = open_conn(st)
        step("Đăng nhập", True, MODES.get(conn.mode, conn.mode) + (" (máy chủ không nhận FTPS, đã tự dùng FTP thường)"
                                                                   if mode == "auto" and conn.mode == "ftp" and st.get("site_ftp_tls", "1") != "0" else ""))
    except Exception as e:
        step("Đăng nhập", False, str(e))
        return {"ok": False, "steps": steps}
    root = ""
    try:
        root = find_root(conn, st)
        if conn.mode != "http":
            step("Thư mục website", True, root + ("" if conn.is_dir(root) else " (chưa có, sẽ tạo mới — kiểm tra lại đúng thư mục web chưa)"))
        name = f"mt-test-{secrets.token_hex(3)}.txt"
        conn.put(_join(root, name), b"moctam ok")
        fm, dm = perms(st)
        can = conn.chmod(_join(root, name), fm)
        conn.delete(_join(root, name))
        step("Ghi thử tệp", True, "ghi và xóa được tệp thử")
        step("Đặt quyền tệp", can, f"đặt được quyền {fm} (thư mục {dm})" if can else
             (f"{SYNC_FILE} trên hosting là bản cũ, không đặt quyền: tải lại tệp mới rồi ghi đè" if conn.mode == "http" else
              f"hosting không cho đổi quyền qua FTP (lệnh SITE CHMOD). Tệp sẽ theo quyền mặc định của hosting; nếu web báo 403 "
              f"thì vào cPanel → File Manager đặt thư mục {dm}, tệp {fm}"))
    except Exception as e:
        step("Ghi thử tệp", False, explain(e, conn.mode, host, port, conn.stage) if not isinstance(e, RuntimeError) else str(e))
        return {"ok": False, "steps": steps}
    finally:
        conn.close()
    return {"ok": True, "steps": steps, "mode": conn.mode, "root": root}


# ---------------------------------------------------------------- cổng nhận PHP
PHP = r"""<?php
// MOC TAM - cong nhan website (phan mem Phong Kinh doanh AI). Chi ghi tep tinh vao thu muc nay, khong nhan .php / tep an.
$TOKEN = '__TOKEN__';
header('Content-Type: application/json; charset=utf-8');
header('Cache-Control: no-store');
header('X-Robots-Tag: noindex');
$t = isset($_SERVER['HTTP_X_MT_TOKEN']) ? $_SERVER['HTTP_X_MT_TOKEN'] : '';
if ($_SERVER['REQUEST_METHOD'] !== 'POST' || !is_string($t) || strlen($TOKEN) < 24 || !hash_equals($TOKEN, $t)) {
  http_response_code(403); echo '{"ok":false,"error":"forbidden"}'; exit;
}
$op = isset($_GET['op']) ? $_GET['op'] : '';
$root = __DIR__;
if ($op === 'ping') { echo json_encode(array('ok' => true, 'v' => 2, 'writable' => is_writable($root), 'php' => PHP_VERSION)); exit; }
$p = isset($_GET['path']) ? (string)$_GET['path'] : '';
if (!preg_match('#^[A-Za-z0-9_\-][A-Za-z0-9._\-/]*$#', $p) || strpos($p, '..') !== false || preg_match('#(^|/)\.#', $p)
    || preg_match('#\.(php\d?|phtml|phar|pht|cgi|pl|py|sh|asp|aspx|jsp|shtml)(\.|$)#i', $p) || basename($p) === basename(__FILE__)) {
  http_response_code(400); echo '{"ok":false,"error":"bad path"}'; exit;
}
$f = $root . '/' . $p;
function mt_mode($k, $d) { $v = isset($_GET[$k]) ? (string)$_GET[$k] : ''; if (!preg_match('/^[0-7]{3}$/', $v)) return $d; $m = octdec($v); return (($m & 02) || !($m & 0400)) ? $d : $m; }
$fm = mt_mode('fm', 0755); $dm = mt_mode('dm', 0755);
if ($op === 'put') {
  $d = dirname($f);
  if (!is_dir($d) && !@mkdir($d, $dm, true)) { http_response_code(500); echo '{"ok":false,"error":"mkdir"}'; exit; }
  $cur = $root; foreach (array_slice(explode('/', $p), 0, -1) as $seg) { $cur .= '/' . $seg; @chmod($cur, $dm); }
  $data = file_get_contents('php://input');
  $tmp = $f . '.part';
  if (@file_put_contents($tmp, $data) === false || !@rename($tmp, $f)) { @unlink($tmp); http_response_code(500); echo '{"ok":false,"error":"write"}'; exit; }
  @chmod($f, $fm);
  echo json_encode(array('ok' => true, 'bytes' => strlen($data))); exit;
}
if ($op === 'del') { if (is_file($f)) { @unlink($f); } echo '{"ok":true}'; exit; }
http_response_code(400); echo '{"ok":false,"error":"bad op"}';
"""


def sync_php(new: bool = False) -> str:
    """Tệp mt-sync.php kèm mã bí mật riêng của máy này (tạo mã lần đầu; new=True đổi mã)."""
    tok = _st().get("site_sync_token") or ""
    if new or len(tok) < 24:
        tok = secrets.token_urlsafe(32)
        db.set_setting("site_sync_token", tok)
    return PHP.replace("__TOKEN__", tok)


# ---------------------------------------------------------------- tự đồng bộ
_sync = {"busy": False, "fp": None, "since": 0.0, "fail_at": 0.0}
WAIT = 90        # dữ liệu đứng yên 90 giây mới đẩy (sửa nhiều sản phẩm liền tay chỉ đẩy một lần)
RETRY = 1800     # lỗi thì 30 phút sau thử lại


def fingerprint() -> str:
    st = _st()
    skip = ("site_last_", "site_ftp_", "site_sync_", "site_deploy_", "site_auto_deploy", "site_write", "site_posts_week",
            "site_auto_publish", "site_min_seo")
    cfg = {k: v for k, v in st.items() if k.startswith("site_") and not k.startswith(skip)}
    data = [cfg, db.q("SELECT * FROM products ORDER BY id"),
            db.q("SELECT id, slug, status, updated_at, published_at FROM site_posts WHERE status='published' ORDER BY id")]
    return hashlib.md5(json.dumps(data, ensure_ascii=False, default=str, sort_keys=True).encode()).hexdigest()


def mark_synced():
    db.set_setting("site_sync_fp", fingerprint())


def tick(now=None, wait: int = WAIT):
    st = _st()
    if st.get("site_auto_deploy", "1") != "1" or _sync["busy"] or not configured(st):
        return
    fp, t = fingerprint(), time.time()
    if fp == st.get("site_sync_fp"):
        return
    if _sync["fp"] != fp:
        _sync["fp"], _sync["since"] = fp, t
        if wait > 0:
            return
    if t - _sync["since"] < wait or t - _sync["fail_at"] < RETRY:
        return

    def run():
        import website
        _sync["busy"] = True
        try:
            website.build()
            r = deploy(who="Vy tự đồng bộ")
            db.set_setting("site_sync_fp", fp)
            _sync["fail_at"] = 0.0
            return r
        except Exception as e:
            _sync["fail_at"] = time.time()
            import errors
            errors.report_exc("website", "Không đẩy được website lên hosting", e, screen="website")
        finally:
            _sync["busy"] = False
    if wait <= 0:
        return run()
    threading.Thread(target=run, daemon=True).start()


# ---------------------------------------------------------------- kiểm tra sitemap trên mạng (như Google đọc)
GOOGLEBOT = "Mozilla/5.0 (compatible; Googlebot/2.1; +http://www.google.com/bot.html)"


def _fetch(url: str):
    import httpx
    with httpx.Client(timeout=20, follow_redirects=True, headers={"User-Agent": GOOGLEBOT}, verify=True) as c:
        return c.get(url)


def _probe_roots(conn, st: dict) -> list[str]:
    """Các thư mục có thể là thư mục web trên hosting (chỉ những thư mục có thật)."""
    d = domain(st)
    want = "/" + (st.get("site_ftp_dir") or "/public_html").strip("/")
    cands = [want, f"/public_html/{d}", f"/domains/{d}/public_html", "/public_html", f"/{d}/public_html", f"/{d}/httpdocs", f"/{d}",
             "/httpdocs", "/htdocs", "/www", "/web", "/html", f"/home/{d}/public_html", "/"]
    out = []
    for c in cands:
        c = c.replace("//", "/") or "/"
        if c in out or (c != "/" and not c.strip("/")):
            continue
        if c == "/" or conn.is_dir(c if conn.mode != "sftp" else c.lstrip("/") or "."):
            out.append(c)
    return out


def find_web_root(base: str, st: dict | None = None) -> str | None:
    """Đặt một tệp thử vào từng thư mục, mở bằng trình duyệt: thư mục nào hiện ra trên tên miền là thư mục web thật."""
    st = st or _st()
    conn = open_conn(st)
    if conn.mode == "http":
        conn.close()
        return None
    try:
        for r in _probe_roots(conn, st):
            path = r if conn.mode != "sftp" else (r.lstrip("/") or ".")
            name = f"mt-probe-{secrets.token_hex(4)}.txt"
            tok = secrets.token_hex(8).encode()
            try:
                conn.put(_join(path, name), tok)
                conn.chmod(_join(path, name), perms(st)[0])
            except Exception:
                continue
            try:
                ok = _fetch(f"{base}/{name}").content.strip() == tok
            except Exception:
                ok = False
            conn.delete(_join(path, name))
            if ok:
                return path
    finally:
        conn.close()
    return None


def check(base: str | None = None, fix: bool = True) -> dict:
    """Mở sitemap.xml, robots.txt, trang chủ trên tên miền như Googlebot; tìm nguyên nhân, sửa được thì tự sửa và đăng lại."""
    import xml.etree.ElementTree as ET
    from urllib.parse import urlparse
    st = _st()
    steps, fixed = [], []

    def step(name, ok, msg=""):
        steps.append({"name": name, "ok": ok, "msg": msg})
        return ok

    dom = (st.get("site_domain") or "").strip().rstrip("/")
    if not dom:
        step("Tên miền", False, "Chưa điền tên miền ở tab Thông tin công ty: sitemap đang ghi đường dẫn tương đối, Google không đọc được")
        return {"ok": False, "steps": steps}
    host = clean_host(dom)[0]
    base = (base or dom).rstrip("/")
    local = _site_dir() / "sitemap.xml"
    if not local.exists():
        import website
        website.build()
    if base == dom:
        try:
            step("Tìm tên miền", True, f"{host} → {socket.gethostbyname(host)}")
        except Exception:
            step("Tìm tên miền", False, f"Tên miền {host} chưa trỏ về máy chủ nào (chưa có bản ghi DNS). Vào trang quản lý tên miền, "
                 "trỏ bản ghi A của @ và www về IP hosting, chờ vài giờ")
            return {"ok": False, "steps": steps}

    def get(path):
        try:
            return _fetch(base + path), None
        except Exception as e:
            return None, e
    r, err = get("/sitemap.xml")
    if err is not None:
        s = str(err)
        if isinstance(err, ssl.SSLError) or "ssl" in s.lower() or "certificate" in s.lower():
            step("Mở sitemap", False, "Tên miền chưa có chứng chỉ SSL (https lỗi). Vào cPanel → SSL/TLS Status → Run AutoSSL "
                 "(hoặc nhờ hosting cài Let's Encrypt miễn phí). Google chỉ đọc được khi https chạy")
        else:
            step("Mở sitemap", False, f"Không mở được {base}/sitemap.xml: {s[:150]}. Hosting đang tắt, tên miền trỏ sai IP hoặc tường lửa chặn")
        return {"ok": False, "steps": steps}
    final = str(r.url)
    sent = _manifest().get("files", {}).get("sitemap.xml")
    got = hashlib.md5(r.content).hexdigest()
    same = r.status_code == 200 and (got == sent or r.content.strip() == local.read_bytes().strip())
    if r.status_code == 200 and same:
        step("Mở sitemap", True, f"{final} (HTTP 200, đúng bản Vy đã đăng)")
    else:
        why = (f"HTTP {r.status_code}" if r.status_code != 200 else "hosting trả về sitemap khác bản Vy đăng (trang cũ / WordPress / trang mặc định)")
        if r.status_code == 403:
            why += f" (web không được đọc tệp: quyền tệp / thư mục sai, Vy đặt lại quyền {'/'.join(perms(st))} và tải lại)"
        step("Mở sitemap", False, f"{base}/sitemap.xml: {why}")
        if fix and configured(st) and (st.get("site_deploy_mode") or "auto") != "http":
            try:
                if not st.get("site_last_deploy"):
                    deploy(who="Vy kiểm tra sitemap")
                    fixed.append("đăng website lên hosting lần đầu")
                else:
                    root = find_web_root(base, st)
                    cur = st.get("site_ftp_dir") or "/public_html"
                    if root and ("/" + root.strip("/")) != ("/" + cur.strip("/")):
                        db.set_setting("site_ftp_dir", root)
                        deploy(full=True, who="Vy sửa thư mục web")
                        fixed.append(f"thư mục web thật là {root} (trước tải vào {cur}): đã đổi và đăng lại toàn bộ")
                    elif root:
                        deploy(full=True, who="Vy kiểm tra sitemap")
                        fixed.append(f"thư mục {root} đúng, đã tải lại toàn bộ website")
                    else:
                        step("Tìm thư mục web", False, "Đã thử đặt tệp vào mọi thư mục có trên hosting nhưng không thư mục nào hiện ra trên "
                             f"{host}: tên miền đang trỏ về máy chủ khác với hosting FTP này, hoặc tên miền chưa gắn vào gói hosting "
                             "(cPanel → Domains / Addon Domains). Kiểm tra IP trong email hosting so với bản ghi A của tên miền")
            except Exception as e:
                step("Tự sửa", False, str(e)[:300])
            if fixed:
                return {**check(base, fix=False), "fixed": fixed}
        elif (st.get("site_deploy_mode") or "auto") == "http" and fix and configured(st):
            try:
                deploy(full=True, who="Vy kiểm tra sitemap")
                fixed.append("đã tải lại toàn bộ website qua cổng nhận PHP")
                return {**check(base, fix=False), "fixed": fixed}
            except Exception as e:
                step("Tự sửa", False, str(e)[:300])
        elif not configured(st):
            step("Kết nối hosting", False, "Chưa điền kết nối hosting nên chưa đăng được: vào tab Đăng lên hosting")
    if r.status_code == 200:
        ctype = r.headers.get("content-type", "")
        if "html" in ctype:
            step("Kiểu tệp", False, f"Hosting trả sitemap dạng {ctype} (thường là trang lỗi / chuyển hướng), Google cần XML")
        try:
            root_el = ET.fromstring(r.content)
            locs = [x.text or "" for x in root_el.iter() if x.tag.endswith("loc")]
            live = urlparse(final).netloc if base == dom else host  # base khác tên miền: chỉ khi kiểm thử
            bad = [u for u in locs if urlparse(u).netloc != live]
            if bad:
                step("Địa chỉ trong sitemap", False, f"{len(bad)}/{len(locs)} địa chỉ ghi {urlparse(bad[0]).netloc} nhưng trang chạy ở "
                     f"{urlparse(final).netloc}: Google báo “URL không được phép”. Sửa tên miền ở tab Thông tin công ty thành "
                     f"{urlparse(final).scheme}://{urlparse(final).netloc}")
                steps[-1]["fix_domain"] = f"{urlparse(final).scheme}://{urlparse(final).netloc}"
            else:
                step("Địa chỉ trong sitemap", True, f"{len(locs)} trang, cùng tên miền {urlparse(final).netloc}")
            for u in locs[:3]:
                try:
                    pr = _fetch(u if base == dom else base + urlparse(u).path)
                    if pr.status_code != 200:
                        step("Mở thử trang", False, f"{u}: HTTP {pr.status_code}")
                        break
                except Exception as e:
                    step("Mở thử trang", False, f"{u}: {str(e)[:100]}")
                    break
            else:
                step("Mở thử trang", True, f"{min(3, len(locs))} trang đầu mở được")
        except ET.ParseError as e:
            step("Đọc XML", False, f"Sitemap trên hosting hỏng ({e}); tải lại bằng nút Đăng lên hosting")
        xr = r.headers.get("x-robots-tag", "")
        if "noindex" in xr.lower():
            step("Thẻ chặn Google", False, f"Hosting gắn X-Robots-Tag: {xr} (thường do .htaccess hoặc chế độ bảo trì)")
    rb, err = get("/robots.txt")
    if rb is not None and rb.status_code == 200:
        txt, block, ua = rb.text, False, None
        for line in txt.splitlines():
            k, _, v = line.partition(":")
            k, v = k.strip().lower(), v.strip()
            if k == "user-agent":
                ua = v.lower()
            elif k == "disallow" and v == "/" and ua in ("*", "googlebot"):
                block = True
        if block:
            step("robots.txt", False, "robots.txt trên hosting chặn Google (Disallow: /). Bản của Vy cho phép; đăng lại website để ghi đè, "
                 "nếu vẫn thế là thư mục web khác (xem bước Mở sitemap)")
        else:
            step("robots.txt", True, "cho Google đọc" + (", có dòng Sitemap" if "sitemap:" in txt.lower() else ""))
    ok = all(s["ok"] for s in steps)
    db.set_setting("site_check_msg", ("OK " if ok else "LỖI ") + db.now() + ": " + "; ".join(s["name"] for s in steps if not s["ok"]))
    return {"ok": ok, "steps": steps, "fixed": fixed, "sitemap": f"{dom}/sitemap.xml",
            "next": "Vào Google Search Console → Sơ đồ trang web, gửi lại “sitemap.xml”. Trạng thái “Không thể tìm nạp” có thể còn hiện "
                    "vài giờ sau lần gửi đầu; bấm vào sitemap → Gửi lại." if ok else ""}

"""Đưa website lên hosting: FTP tự chuyển khi không có TLS, FTPS, dò thư mục DirectAdmin, chỉ tải tệp đổi, xóa tệp gỡ,
tự đồng bộ khi sửa sản phẩm, báo lỗi tiếng Việt, cổng nhận PHP thật (php -S), lệnh CEO."""
import sys, os, shutil, json, threading, time, subprocess, socket
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "backend"))
from pathlib import Path
SP = Path(os.environ.get("MT_WORK") or Path(__file__).resolve().parent / "work")
import db
db.DB_PATH = SP / "deploy.db"; db.DB_PATH.unlink(missing_ok=True)
db.DATA_DIR = SP / "deploy_data"; shutil.rmtree(db.DATA_DIR, ignore_errors=True); db.DATA_DIR.mkdir()
db.PROFILES_DIR = SP / "deploy_profiles"; shutil.rmtree(db.PROFILES_DIR, ignore_errors=True); db.PROFILES_DIR.mkdir()
db.init(); db.set_setting("anthropic_api_key", "")
import website as W, site_deploy as D, ceo_orders
W.SITE_DIR = db.DATA_DIR / "site"; D.MANIFEST = db.DATA_DIR / "site_deploy.json"
from fastapi.testclient import TestClient
import main
c = TestClient(main.app)
bad = []
def chk(name, ok, extra=""):
    print(("   ✓ " if ok else "   ✗ ") + name, extra)
    if not ok: bad.append(name)

chk("làm sạch máy chủ", [D.clean_host(x) for x in ("ftp://user@FTP.moctamvn.vn:2121/public_html", "https://moctamvn.vn/", " 103.1.2.3 ")]
    == [("ftp.moctamvn.vn", 2121), ("moctamvn.vn", None), ("103.1.2.3", None)])
c.put("/api/website/settings", json={"site_domain": "moctamvn.vn"})
r = c.post("/api/website/write", json={"wait": True}).json(); pid = r["id"]
c.post(f"/api/website/posts/{pid}/publish")
slug = c.get(f"/api/website/posts/{pid}").json()["slug"]

# --- FTP không TLS, hosting kiểu DirectAdmin (thư mục web: domains/moctamvn.vn/public_html)
from pyftpdlib.authorizers import DummyAuthorizer
from pyftpdlib.handlers import FTPHandler, TLS_FTPHandler
from pyftpdlib.servers import FTPServer
root = SP / "deploy_ftp"; shutil.rmtree(root, ignore_errors=True); web = root / "domains" / "moctamvn.vn" / "public_html"; web.mkdir(parents=True)
au = DummyAuthorizer(); au.add_user("moctam", "secret", str(root), perm="elradfmwMT")
class H(FTPHandler): authorizer = au
srv = FTPServer(("127.0.0.1", 2131), H); threading.Thread(target=srv.serve_forever, daemon=True).start(); time.sleep(0.3)
c.put("/api/website/settings", json={"site_ftp_host": "ftp://moctam@127.0.0.1:2131/", "site_ftp_user": "moctam", "site_ftp_pass": "sai", "site_auto_deploy": "1"})
chk("lưu máy chủ đã làm sạch", db.get_settings()["site_ftp_host"] == "127.0.0.1:2131")
t = c.post("/api/website/deploy/test").json()
chk("sai mật khẩu báo tiếng Việt", not t["ok"] and "Sai tài khoản hoặc mật khẩu" in t["steps"][-1]["msg"], t["steps"][-1]["msg"][:60])
c.put("/api/website/settings", json={"site_ftp_pass": "secret"})
t = c.post("/api/website/deploy/test").json()
chk("kiểm tra kết nối ok, tự chuyển FTP thường", t["ok"] and t["mode"] == "ftp", [s["name"] for s in t["steps"]])
chk("dò ra thư mục DirectAdmin", t["root"] == "/domains/moctamvn.vn/public_html", t["root"])
d = c.post("/api/website/deploy").json()
chk("đăng lần đầu", d["files"] > 5 and (web / "tin-tuc" / slug / "index.html").exists() and (web / "index.html").exists(), d)
chk("không tạo nhầm /public_html", not (root / "public_html").exists())
d2 = c.post("/api/website/deploy").json(); chk("lần 2 không tải lại gì", d2["files"] == 0 and d2["deleted"] == 0, d2)
chk("không còn thay đổi chờ đẩy", not c.get("/api/website").json()["settings"]["site_sync_pending"])
# tự đồng bộ: thêm sản phẩm -> tick đẩy lên; gỡ bài -> tick xóa trên hosting
before = len(list(web.rglob("*.html")))
c.post(f"/api/website/posts/{pid}/unpublish")
chk("gỡ bài: có thay đổi chờ đẩy", c.get("/api/website").json()["settings"]["site_sync_pending"])
D.tick(wait=0)
chk("tự đồng bộ xóa bài đã gỡ trên hosting", not (web / "tin-tuc" / slug / "index.html").exists(), f"{before} → {len(list(web.rglob('*.html')))} trang")
c.post(f"/api/website/posts/{pid}/publish"); D.tick(wait=0)
chk("đăng lại: tự đẩy lên", (web / "tin-tuc" / slug / "index.html").exists())
db.set_setting("site_auto_deploy", "0"); c.post(f"/api/website/posts/{pid}/unpublish"); D.tick(wait=0)
chk("tắt tự đẩy thì không đẩy", (web / "tin-tuc" / slug / "index.html").exists())
db.set_setting("site_auto_deploy", "1"); c.post(f"/api/website/posts/{pid}/publish")
srv.close_all()

# --- FTPS (chứng chỉ tự ký), chế độ ftps
cert = SP / "deploy_cert.pem"
subprocess.run(["openssl", "req", "-x509", "-newkey", "rsa:2048", "-nodes", "-keyout", str(cert), "-out", str(cert), "-days", "2",
                "-subj", "/CN=localhost"], capture_output=True)
root2 = SP / "deploy_ftps"; shutil.rmtree(root2, ignore_errors=True); (root2 / "public_html").mkdir(parents=True)
au2 = DummyAuthorizer(); au2.add_user("moctam", "secret", str(root2), perm="elradfmwMT")
class T(TLS_FTPHandler): authorizer = au2; certfile = str(cert); tls_control_required = True; tls_data_required = True
srv2 = FTPServer(("127.0.0.1", 2132), T); threading.Thread(target=srv2.serve_forever, daemon=True).start(); time.sleep(0.3)
c.put("/api/website/settings", json={"site_ftp_host": "127.0.0.1:2132", "site_deploy_mode": "auto", "site_ftp_dir": "/public_html"})
d = c.post("/api/website/deploy").json()
chk("FTPS đăng được", d["mode"] == "ftps" and (root2 / "public_html" / "tin-tuc" / slug / "index.html").exists(), d)
srv2.close_all()

# --- máy chủ không có / cổng đóng
c.put("/api/website/settings", json={"site_ftp_host": "khong-co-may-nay.invalid"})
t = c.post("/api/website/deploy/test").json(); chk("tên máy chủ sai", "Không tìm thấy máy chủ" in t["steps"][-1]["msg"])
c.put("/api/website/settings", json={"site_ftp_host": "127.0.0.1:2139"})
t = c.post("/api/website/deploy/test").json(); chk("cổng đóng", "từ chối cổng" in t["steps"][-1]["msg"], t["steps"][-1]["msg"][:50])
e = c.post("/api/website/deploy"); chk("đăng lỗi trả 400 tiếng Việt", e.status_code == 400 and "từ chối cổng" in e.json()["detail"])
chk("lưu lỗi để hiện", c.get("/api/website").json()["settings"]["site_deploy_msg"].startswith("LỖI"))
D._sync["fail_at"] = 0; db.set_setting("site_sync_fp", ""); D.tick(wait=0)
chk("tự đồng bộ lỗi ghi sổ lỗi", bool(db.q("SELECT 1 FROM errors WHERE title LIKE 'Không đẩy được website%'")))

# --- cổng nhận PHP thật
php = SP / "deploy_php"; shutil.rmtree(php, ignore_errors=True); php.mkdir()
code = c.get("/api/website/mt-sync.php").text; (php / "mt-sync.php").write_text(code)
tok = db.get_settings()["site_sync_token"]; chk("mã bí mật đủ dài, có trong tệp", len(tok) >= 32 and tok in code)
chk("mã không lộ ở tổng quan", tok not in json.dumps(c.get("/api/website").json()))
ps = subprocess.Popen(["php", "-S", "127.0.0.1:8137", "-t", str(php)], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
for _ in range(30):
    try: socket.create_connection(("127.0.0.1", 8137), 0.2).close(); break
    except OSError: time.sleep(0.1)
try:
    c.put("/api/website/settings", json={"site_deploy_mode": "http", "site_sync_url": "http://127.0.0.1:8137/mt-sync.php"})
    db.set_setting("site_sync_url", "http://127.0.0.1:8137/mt-sync.php")
    t = c.post("/api/website/deploy/test").json(); chk("kiểm tra cổng PHP", t["ok"], [s["msg"] for s in t["steps"]])
    d = c.post("/api/website/deploy").json()
    chk("đăng qua cổng PHP", d["mode"] == "http" and (php / "tin-tuc" / slug / "index.html").exists() and (php / "sitemap.xml").exists(), d)
    import httpx
    u = "http://127.0.0.1:8137/mt-sync.php"
    def call(path, tk=tok, data=b"x"): return httpx.post(u, params={"op": "put", "path": path}, headers={"X-MT-Token": tk}, content=data).status_code
    chk("sai mã bị chặn", call("a.html", "sai") == 403)
    chk("chặn tệp .php / .htaccess / thoát thư mục", [call(x) for x in ("x.php", "a/b.phtml", ".htaccess", "../x.html", "a/.user.ini", "mt-sync.php", "/etc/x")]
        == [400] * 7 and not (php / "x.php").exists())
    c.post(f"/api/website/posts/{pid}/unpublish"); D.tick(wait=0)
    chk("cổng PHP xóa bài đã gỡ", not (php / "tin-tuc" / slug / "index.html").exists() and (php / "mt-sync.php").exists())
    (php / "mt-sync.php").write_text(code.replace(tok, "x" * 40))
    e = c.post("/api/website/deploy", params={"full": 1}); chk("tệp cũ mã khác: báo tải lại", e.status_code == 400 and "Tải lại tệp mới" in e.json()["detail"])
    (php / "mt-sync.php").unlink()
    e = c.post("/api/website/deploy"); chk("chưa tải cổng lên: báo rõ", "Chưa có mt-sync.php" in e.json()["detail"])
finally:
    ps.terminate()

# --- lệnh CEO
p1 = ceo_orders._rule_plan("đẩy website lên hosting giúp anh"); p2 = ceo_orders._rule_plan("kiểm tra kết nối hosting")
p3 = ceo_orders._rule_plan("đưa tin tức lên online")
chk("CEO hiểu lệnh", [p["actions"][0] for p in (p1, p2, p3)] == [{"type": "site_deploy"}, {"type": "site_deploy", "test": True}, {"type": "site_deploy"}],
    [p["actions"] for p in (p1, p2, p3)])
print("KẾT QUẢ:", "OK" if not bad else "LỖI " + ", ".join(bad))

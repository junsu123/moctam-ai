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
    chk("cổng PHP đặt quyền 755", oct((php / "sitemap.xml").stat().st_mode & 0o777)[2:] == "755" and oct((php / "tin-tuc").stat().st_mode & 0o777)[2:] == "755"
        and d["perm_fail"] == 0)
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

# --- kiểm tra sitemap trên mạng: hosting cPanel tên miền phụ (web đọc public_html/moctamvn.vn), Vy tải nhầm vào public_html
root3 = SP / "deploy_web"; shutil.rmtree(root3, ignore_errors=True); served = root3 / "public_html" / "moctamvn.vn"; served.mkdir(parents=True)
(served / "robots.txt").write_text("User-agent: *\nDisallow: /\n")
au3 = DummyAuthorizer(); au3.add_user("moctam", "secret", str(root3), perm="elradfmwMT")
class H3(FTPHandler): authorizer = au3
srv3 = FTPServer(("127.0.0.1", 2133), H3); threading.Thread(target=srv3.serve_forever, daemon=True).start()
web3 = subprocess.Popen([sys.executable, "-m", "http.server", "8139", "--bind", "127.0.0.1", "-d", str(served)], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
time.sleep(0.8)
try:
    c.put("/api/website/settings", json={"site_deploy_mode": "auto", "site_ftp_host": "127.0.0.1:2133", "site_ftp_dir": "/public_html"})
    D.MANIFEST.unlink(missing_ok=True); c.post(f"/api/website/posts/{pid}/publish")
    d = c.post("/api/website/deploy").json(); chk("đăng nhầm vào public_html", d["dir"] == "/public_html" and not (served / "sitemap.xml").exists())
    r = D.check(base="http://127.0.0.1:8139")
    chk("kiểm tra sitemap: tìm ra thư mục web thật và sửa", r["ok"] and r["fixed"] and "/public_html/moctamvn.vn" in r["fixed"][0], r.get("fixed"))
    chk("đã đổi thư mục, sitemap lên đúng chỗ", db.get_settings()["site_ftp_dir"] == "/public_html/moctamvn.vn" and (served / "sitemap.xml").exists())
    chk("robots.txt chặn Google đã bị ghi đè", "Disallow: /" not in (served / "robots.txt").read_text(), [x["name"] + ("✓" if x["ok"] else "✗") for x in r["steps"]])
    chk("không để lại tệp thử", not list(root3.rglob("mt-probe-*")))
    md = lambda p: oct(p.stat().st_mode & 0o777)[2:]
    chk("quyền tệp / thư mục 755", [md(served / "sitemap.xml"), md(served / "tin-tuc"), md(served / "assets" / "style.css")] == ["755"] * 3,
        [md(served / "sitemap.xml"), md(served / "tin-tuc"), md(served / "assets" / "style.css")])
    t3 = D.test(); chk("kiểm tra kết nối: đặt được quyền", any(x["name"] == "Đặt quyền tệp" and x["ok"] for x in t3["steps"]))
    os.chmod(served / "sitemap.xml", 0o600); os.chmod(served / "tin-tuc", 0o644); os.chmod(served, 0o750)
    c.put("/api/website/settings", json={"site_chmod_file": "644", "site_chmod_dir": "755"})
    chk("chặn quyền 777", c.put("/api/website/settings", json={"site_chmod_file": "777"}).status_code == 400)
    d = c.post("/api/website/deploy").json()
    chk("đổi quyền: tải lại toàn bộ, đặt lại quyền", d["files"] > 5 and d["perms"] == "644/755" and md(served / "sitemap.xml") == "644"
        and md(served / "tin-tuc") == "755", (d["files"], d["perms"], md(served / "sitemap.xml"), md(served / "tin-tuc")))
    chk("không đụng quyền thư mục gốc web", md(served) == "750")
    os.chmod(served, 0o755); c.put("/api/website/settings", json={"site_chmod_file": "755"}); c.post("/api/website/deploy")
    r2 = D.check(base="http://127.0.0.1:8139"); chk("kiểm tra lại: ổn, không sửa gì", r2["ok"] and not r2["fixed"])
    # Vy viết xong bài đạt chuẩn: tự đăng + đẩy lên hosting ngay, không ai bấm
    chk("tự đăng bật mặc định", db.get_settings()["site_auto_publish"] == "1")
    db.set_setting("site_min_seo", "0")
    w = W.write(keyword="trà túi lọc gừng sả nguồn sỉ")
    np = W.get(w["id"])
    chk("Vy viết xong: tự đăng", w["published"] and np["status"] == "published" and w["pushing"], w)
    for _ in range(60):
        if (served / "tin-tuc" / np["slug"] / "index.html").exists() and np["slug"] in (served / "sitemap.xml").read_text(): break
        time.sleep(0.25)
    chk("bài mới lên hosting và sitemap không cần bấm", (served / "tin-tuc" / np["slug"] / "index.html").exists() and np["slug"] in (served / "sitemap.xml").read_text())
    db.run("UPDATE site_posts SET status='review' WHERE id=?", (pid,)); db.set_setting("site_min_seo", "0")
    chk("bài chờ duyệt đạt chuẩn: tự đăng ở lượt sau", W.auto_publish_waiting() >= 1 and W.get(pid)["status"] == "published")
    db.set_setting("site_min_seo", "75")
    (served / "sitemap.xml").write_text("<html>trang lỗi</html>")
    r3 = D.check(base="http://127.0.0.1:8139", fix=False)
    chk("sitemap trên mạng khác bản Vy: báo lỗi", not r3["ok"] and "khác bản Vy" in r3["steps"][0]["msg"], r3["steps"][0]["msg"][:70])
    db.set_setting("site_domain", "")
    chk("chưa có tên miền: báo", "Chưa điền tên miền" in D.check()["steps"][0]["msg"])
    db.set_setting("site_domain", "https://moctamvn.vn")
finally:
    web3.terminate(); srv3.close_all()

# --- lệnh CEO
p1 = ceo_orders._rule_plan("đẩy website lên hosting giúp anh"); p2 = ceo_orders._rule_plan("kiểm tra kết nối hosting")
p3 = ceo_orders._rule_plan("đưa tin tức lên online")
chk("CEO hiểu lệnh sitemap", ceo_orders._rule_plan("kiểm tra sitemap không thể truy cập")["actions"] == [{"type": "site_deploy", "check": True}])
chk("CEO hiểu lệnh", [p["actions"][0] for p in (p1, p2, p3)] == [{"type": "site_deploy"}, {"type": "site_deploy", "test": True}, {"type": "site_deploy"}],
    [p["actions"] for p in (p1, p2, p3)])
print("KẾT QUẢ:", "OK" if not bad else "LỖI " + ", ".join(bad))

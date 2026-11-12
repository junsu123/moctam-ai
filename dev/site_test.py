import sys, shutil, json, re, threading, time, zipfile, io
import os; sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "backend"))
from pathlib import Path
SP = Path(__import__("os").environ.get("MT_WORK") or Path(__file__).resolve().parent / "work")
import db
db.DB_PATH = SP / "site.db"; db.DB_PATH.unlink(missing_ok=True)
db.DATA_DIR = SP / "site_data"; shutil.rmtree(db.DATA_DIR, ignore_errors=True); db.DATA_DIR.mkdir()
db.PROFILES_DIR = SP / "site_profiles"; shutil.rmtree(db.PROFILES_DIR, ignore_errors=True); db.PROFILES_DIR.mkdir()
db.init(); db.set_setting("bump_folder", str(SP / "img2_folder"))
import website as W
W.SITE_DIR = db.DATA_DIR / "site"
from fastapi.testclient import TestClient
import main
c = TestClient(main.app)
o = c.get("/api/website").json(); print("1. kế hoạch từ khóa:", o["stats"], [k["keyword"] for k in o["keywords"][:4]])
c.put("/api/website/settings", json={"site_domain": "moctam.vn", "site_email": "lienhe@moctam.vn", "site_address": "KCN Long An"})
print("   tên miền:", db.get_settings()["site_domain"])
r = c.post("/api/website/write", json={"wait": True}).json(); print("2. Vy viết:", r)
p = c.get(f"/api/website/posts/{r['id']}").json()
print("   tiêu đề:", p["title"], "|", len(p["title"]), "ký tự")
print("   meta:", len(p["meta_title"]), "/", len(p["meta_desc"]), "ký tự | chữ:", p["words"], "| ảnh:", p["cover"])
for it in p["seo"]["items"]: print(f"   {'✓' if it['ok'] else '✗'} {it['label']} ({it['points']}/{it['max']}) {it['tip']}")
print("   luật:", p["seo"]["policy"] or "sạch")
r2 = c.post("/api/website/write", json={"keyword": "gia công cà phê hòa tan", "wait": True}).json(); print("3. viết theo từ khóa sếp:", r2)
# sửa bài: chèn câu hứa chữa bệnh -> không cho đăng
bad = c.patch(f"/api/website/posts/{r2['id']}", json={"body": p["body"] + "\n\nTrà này chữa khỏi bệnh dạ dày."}).json()
print("4. sửa có câu chữa bệnh:", bad["seo_score"], bad["policy_note"], "| đăng:", c.post(f"/api/website/posts/{r2['id']}/publish").status_code)
c.patch(f"/api/website/posts/{r2['id']}", json={"body": p["body"].replace(p["keyword"], "gia công cà phê hòa tan")})
pub = c.post(f"/api/website/posts/{r['id']}/publish").json(); print("5. đăng bài:", pub["status"], pub["published_at"])
c.post(f"/api/website/posts/{r2['id']}/publish")
site = W.SITE_DIR
files = sorted(str(f.relative_to(site)) for f in site.rglob("*") if f.is_file())
print("6. website:", len(files), "tệp:", [f for f in files if not f.startswith("media")][:14])
art = (site / "tin-tuc" / p["slug"] / "index.html").read_text()
lds = [json.loads(x) for x in re.findall(r'<script type="application/ld\+json">(.*?)</script>', art, re.S)]
print("   schema bài:", [x["@type"] for x in lds], "| canonical:", re.search(r'rel="canonical" href="([^"]+)"', art).group(1))
print("   h1:", len(re.findall("<h1", art)), "| h2:", len(re.findall("<h2", art)), "| mục lục:", "toc" in art, "| ảnh:", "/media/" in art, "| og:image:", 'og:image' in art)
sm = (site / "sitemap.xml").read_text(); print("   sitemap:", sm.count("<url>"), "trang; có bài:", p["slug"] in sm, "| robots:", (site / "robots.txt").read_text().strip().replace("\n", " | "))
prod_pages = list((site / "san-pham").glob("*/index.html"))
txt = " ".join(x.read_text() for x in prod_pages)
print("   trang sản phẩm:", len(prod_pages), "| có giá tiền:", bool(re.search(r"\d[\d.,]*\s*(đ|vnđ|k\b|000)", re.sub(r"<[^>]+>", " ", txt), re.I)), "| có Zalo:", "0386992326" in txt)
pv = c.get("/site/"); print("7. xem trước /site/:", pv.status_code, 'href="/site/tin-tuc/' in pv.text, 'href="/site/assets/style.css"' in pv.text)
print("   bài:", c.get(f"/site/tin-tuc/{p['slug']}/").status_code, "| css:", c.get("/site/assets/style.css").status_code, "| 404:", c.get("/site/khong-co/").status_code, "| thoát thư mục:", c.get("/site/../../etc/passwd").status_code)
z = zipfile.ZipFile(io.BytesIO(c.get("/api/website/export.zip").content)); print("8. zip:", len(z.namelist()), "tệp, có index:", "index.html" in z.namelist())
# FTP
from pyftpdlib.authorizers import DummyAuthorizer
from pyftpdlib.handlers import FTPHandler
from pyftpdlib.servers import FTPServer
ftproot = SP / "ftp_root"; shutil.rmtree(ftproot, ignore_errors=True); ftproot.mkdir()
au = DummyAuthorizer(); au.add_user("moctam", "secret", str(ftproot), perm="elradfmwMT")
h = FTPHandler; h.authorizer = au
srv = FTPServer(("127.0.0.1", 2121), h); threading.Thread(target=srv.serve_forever, daemon=True).start(); time.sleep(0.5)
print("9. FTP chưa cài:", c.post("/api/website/deploy").json())
c.put("/api/website/settings", json={"site_ftp_host": "127.0.0.1:2121", "site_ftp_user": "moctam", "site_ftp_pass": "secret", "site_ftp_dir": "/public_html", "site_ftp_tls": "0"})
print("   mật khẩu không trả về:", "secret" not in json.dumps(c.get("/api/website").json()))
d = c.post("/api/website/deploy").json(); print("   đăng hosting:", d, "| có trên máy chủ:", (ftproot / "public_html" / "tin-tuc" / p["slug"] / "index.html").exists())
print("10. kế hoạch thêm:", c.post("/api/website/keywords/plan").json()["added"], "| gỡ bài:", c.post(f"/api/website/posts/{r2['id']}/unpublish").json()["status"])
o = c.get("/api/website").json(); print("   tổng quan:", o["stats"], o["pages"], "trang")
import fb_policy, agents
print("11. Vy có trong đội:", "vy" in agents.ORDER, "| lời dặn Vy có website:", "WEBSITE CÔNG TY" in agents.system_prompt("vy", db.get_settings()))
print("lỗi:", [e["title"] for e in db.q("SELECT title FROM errors")])
srv.close_all()

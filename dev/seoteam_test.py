"""Đội SEO: Vy (Leader) đọc Google giả, Hương viết trang sản phẩm, Khải kiểm tra kỹ thuật; khóa Google không lộ."""
import sys, os, shutil, json, re, base64
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "backend"))
from pathlib import Path
SP = Path(os.environ.get("MT_WORK") or Path(__file__).resolve().parent / "work")
import db
db.DB_PATH = SP / "seoteam.db"; db.DB_PATH.unlink(missing_ok=True)
db.DATA_DIR = SP / "seoteam_data"; shutil.rmtree(db.DATA_DIR, ignore_errors=True); db.DATA_DIR.mkdir()
db.PROFILES_DIR = SP / "seoteam_prof"; shutil.rmtree(db.PROFILES_DIR, ignore_errors=True); db.PROFILES_DIR.mkdir()
db.init(); db.set_setting("site_domain", "https://moctam.vn")
import website as W, seo_team as T
W.SITE_DIR = db.DATA_DIR / "site"
from fastapi.testclient import TestClient
import main
c = TestClient(main.app)
ok = n = 0
def chk(name, cond, info=""):
    global ok, n
    n += 1; ok += bool(cond); print(("✓ " if cond else "✗ ") + name, "" if cond else str(info)[:400])

from cryptography.hazmat.primitives.asymmetric import rsa, padding
from cryptography.hazmat.primitives import serialization, hashes
key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
pem = key.private_bytes(serialization.Encoding.PEM, serialization.PrivateFormat.PKCS8, serialization.NoEncryption()).decode()
SA = json.dumps({"type": "service_account", "client_email": "seo@du-an.iam.gserviceaccount.com", "private_key": pem})
jwt = T.make_jwt(json.loads(SA))
h, cl, sig = jwt.split(".")
pad = lambda x: x + "=" * (-len(x) % 4)
key.public_key().verify(base64.urlsafe_b64decode(pad(sig)), f"{h}.{cl}".encode(), padding.PKCS1v15(), hashes.SHA256())
chk("ký JWT RS256 đúng, có scope Search Console + GA4", "webmasters" in json.loads(base64.urlsafe_b64decode(pad(cl)))["scope"])

prods = W._product_pages()
P1 = prods[0]; PURL = "https://moctam.vn" + W.u_prod(P1["slug"])
pw = W.write("gia công trà túi lọc"); W.publish(pw["id"]); post = W.get(pw["id"])
POSTURL = "https://moctam.vn" + W.u_post(post["slug"])
calls = []

class Resp:
    def __init__(self, code, data=None, headers=None, text=None):
        self.status_code, self._d, self.headers = code, data, headers or {}
        self.text = text if text is not None else json.dumps(data or {})
    def json(self): return self._d

def fake(method, url, **kw):
    calls.append((method, url))
    if url == T.TOKEN_URL: return Resp(200, {"access_token": "tok", "expires_in": 3600})
    if url.endswith("/webmasters/v3/sites"): return Resp(200, {"siteEntry": [{"siteUrl": "sc-domain:moctam.vn", "permissionLevel": "siteOwner"}]})
    if "searchAnalytics" in url:
        dims = kw["json"]["dimensions"]
        if dims == ["date"]:
            return Resp(200, {"rows": [{"keys": [f"2026-11-{d:02d}"], "clicks": 5, "impressions": 200, "position": 12.0} for d in range(1, 21)]})
        if dims == ["query"]: return Resp(200, {"rows": [{"keys": ["gia công trà túi lọc"], "clicks": 3, "impressions": 90, "position": 6}]})
        prev = kw["json"]["endDate"] < "2026-10-28"
        return Resp(200, {"rows": [
            {"keys": [P1["name"].lower() + " sỉ", PURL], "clicks": 2, "impressions": 300, "position": 14.0 if prev else 9.5},
            {"keys": ["gia công trà túi lọc", POSTURL], "clicks": 1, "impressions": 400, "position": 3.0},
            {"keys": ["nguồn hàng bột ngũ cốc cho shop", "https://moctam.vn/"], "clicks": 0, "impressions": 60, "position": 25},
            {"keys": ["váy cưới đẹp", "https://moctam.vn/"], "clicks": 0, "impressions": 80, "position": 40}]})
    if "runReport" in url:
        if "dimensionFilter" in kw["json"]: return Resp(200, {"dimensionHeaders": [{"name": "date"}], "metricHeaders": [{"name": "eventCount"}], "rows": [{"dimensionValues": [{"value": "20261110"}], "metricValues": [{"value": "4"}]}]})
        return Resp(200, {"dimensionHeaders": [{"name": "date"}], "metricHeaders": [{"name": "sessions"}], "rows": [{"dimensionValues": [{"value": "20261110"}], "metricValues": [{"value": "37"}]}]})
    if "/sitemaps/" in url: return Resp(204, text="")
    if "urlInspection" in url:
        u = kw["json"]["inspectionUrl"]
        return Resp(200, {"inspectionResult": {"indexStatusResult": {"verdict": "PASS" if u.endswith("/") else "NEUTRAL", "coverageState": "Đã thu thập dữ liệu - hiện chưa được lập chỉ mục", "lastCrawlTime": "2026-11-20T01:00:00Z"}}})
    if "pagespeedonline" in url:
        return Resp(200, {"lighthouseResult": {"categories": {"performance": {"score": 0.72}}, "audits": {"largest-contentful-paint": {"numericValue": 3100}, "cumulative-layout-shift": {"numericValue": 0.02}, "total-blocking-time": {"numericValue": 120}}}})
    if url.startswith("http://moctam.vn"): return Resp(301, headers={"location": "https://moctam.vn/"})
    if "khai-kiem-tra-404" in url: return Resp(404, text="nf")
    return Resp(404, {"error": {"message": "không có"}})
T._http = fake

# kết nối, khóa không lộ
chk("dán JSON sai bị từ chối", c.put("/api/seo/google", json={"sa": "abc"}).status_code == 400)
o = c.put("/api/seo/google", json={"sa": SA, "ga4": "properties/412345678"}).json()
chk("lưu khóa, mã GA4 lấy số", o["google"]["configured"] and o["google"]["ga4"] == "412345678", o["google"])
chk("khóa không trả về giao diện", "PRIVATE KEY" not in json.dumps(o) and "PRIVATE KEY" not in c.get("/api/settings").text)
t = c.post("/api/seo/google/test").json()
chk("kiểm tra kết nối: Search Console + GA4 ổn", all(x["ok"] for x in t["steps"] if x["name"] in ("Khóa tài khoản dịch vụ", "Search Console", "GA4")), t)
chk("tự tìm trang web trong Search Console", db.get_settings()["seo_gsc_site"] == "sc-domain:moctam.vn")

# Vy
r = T.run_leader()
chk("Vy đọc Search Console + GA4", r["pulled"] and r["pulled"]["queries"] == 4 and r["pulled"]["ga_days"] == 1, r)
op = T.opportunities()
chk("cơ hội: trang sản phẩm vị trí 9.5 (trước 14)", any(o["query"].endswith(" sỉ") and o["position"] == 9.5 and o["prev_position"] == 14.0 for o in op), op)
chk("cơ hội: top 3 mà ít người bấm", any(o["query"] == "gia công trà túi lọc" and "ít người bấm" in o["kind"] for o in op), op)
tk = db.q("SELECT kind, ref_id FROM seo_tasks WHERE status='todo'")
chk("Vy giao Hương việc trang sản phẩm + sửa tiêu đề bài", {("product", P1["id"]), ("post_meta", post["id"])} <= {(x["kind"], x["ref_id"]) for x in tk}, tk)
kws = [x["keyword"] for x in db.q("SELECT keyword FROM site_keywords WHERE source='gsc'")]
chk("thêm từ khóa khách đang tìm (đúng ngành), bỏ từ khóa lạ", "nguồn hàng bột ngũ cốc cho shop" in kws and "váy cưới đẹp" not in kws, kws)
sm = T.summary()
chk("số liệu 28 ngày có lượt bấm, truy cập, liên hệ GA4", sm["cur"]["clicks"] == 100 and sm["cur"]["sessions"] == 37 and sm["cur"]["contacts"] == 4, sm["cur"])
chk("theo dõi thứ hạng từ khóa", any(x["keyword"] == "gia công trà túi lọc" and x["position"] == 3.0 for x in T.ranks()), T.ranks())
km = T.keyword_map()
chk("phân từ khóa → trang đích", any(k["keyword"] == "gia công trà túi lọc" and k["kind"] == "Bài viết" for k in km), km[:3])
rep = T.weekly_report()
chk("báo cáo tuần có số liệu, cơ hội", "Lượt bấm từ Google: 100" in rep and "Cơ hội" in rep, rep)

# Hương
db.set_setting("site_auto_publish", "1")
res = T.run_content(n=1)
row = db.one("SELECT * FROM site_product_seo WHERE product_id=?", (P1["id"],))
chk("Hương viết trang sản phẩm theo từ khóa Google", row and row["keyword"].endswith(" sỉ") and row["author"] == "huong", row)
chk("Vy duyệt nội dung đạt chuẩn", row["status"] == "approved", (row["status"], row["note"]))
pg = (W.SITE_DIR / "san-pham" / f"{P1['slug']}.html").read_text()
chk("trang sản phẩm dùng tiêu đề, nội dung, FAQPage của Hương", f"<title>{__import__('html').escape(row['title'])}</title>" in pg and '"FAQPage"' in pg and "Phù hợp với ai" in pg)
p2 = W.get(post["id"])
chk("Hương sửa tiêu đề / mô tả bài theo từ khóa Google (điểm SEO không giảm)", p2["meta_title"] != post["meta_title"] or p2["meta_desc"] != post["meta_desc"], (post["meta_title"], p2["meta_title"]))
chk("việc Vy giao đã xong", not db.q("SELECT 1 FROM seo_tasks WHERE status='todo' AND kind IN ('product','post_meta') AND ref_id IN (?,?)", (P1["id"], post["id"])))
bad = {"keyword": "trà sỉ", "title": "Trà sỉ giá tốt | MỘC TÂM", "meta": "x" * 130, "body": "Trà sỉ có 37% hoạt chất quý.\n\n## A\n\n- a\n\n## B\n\n" + "chữ " * 200, "faq": [{"q": "a", "a": "b"}, {"q": "c", "a": "d"}]}
chk("kiểm chứng: số liệu không có trong thông tin sản phẩm thì chờ sếp", not T.product_check(bad, P1)["ok"] and "37" in " ".join(T.product_check(bad, P1)["flags"]))
o = c.put(f"/api/seo/products/{P1['id']}", json={"title": "Sếp sửa tiêu đề trà sỉ", "keyword": "trà sỉ"}).json()
chk("sếp sửa rồi duyệt", any(p["id"] == P1["id"] and p["title"] == "Sếp sửa tiêu đề trà sỉ" and p["status"] == "approved" for p in o["products"]))

# Khải
(W.SITE_DIR / "tin-tuc" / f"{post['slug']}.html").write_text((W.SITE_DIR / "tin-tuc" / f"{post['slug']}.html").read_text().replace("</main>", '<a href="/san-pham/mat-tich.html">x</a></main>'))
a = T.run_audit(psi_run=True)
areas = {i["area"] for i in a["issues"]}
chk("Khải tự sửa link hỏng (dựng lại)", "Link hỏng" not in areas, a["issues"])
chk("đo PageSpeed điện thoại 3 trang", len(a["psi"]) == 3 and a["psi"][0]["score"] == 72 and a["psi"][0]["lcp"] == 3.1, a["psi"])
chk("báo tốc độ chưa đạt kèm cách sửa", "Tốc độ" in areas)
chk("chưa gắn GA4 thì báo sếp", any(i["area"] == "Đo lường" and i["who"] == "sep" for i in a["issues"]))
chk("gửi sitemap cho Google khi đổi", any("/sitemaps/" in u for _, u in calls) and db.get_settings()["seo_sitemap_sent"])
chk("kiểm tra index, báo trang chưa vào chỉ mục", a["index"] and a["index"]["checked"] >= 8 and a["index"]["indexed"] >= 1 and "Index" in areas, a["index"])
chk("https, trang 404 đúng mã: không báo lỗi", "HTTPS" not in areas and "404" not in areas)
chk("điểm sức khỏe 0–100, lưu lịch sử", 0 <= a["score"] < 100 and T.last_audit()["score"] == a["score"])
n0 = len([x for x in calls if "/sitemaps/" in x[1]]); T.run_audit(psi_run=False)
chk("sitemap không đổi thì không gửi lại", len([x for x in calls if "/sitemaps/" in x[1]]) == n0)

# API, CEO, đội
o = c.get("/api/seo").json()
chk("API tổng quan đủ phần", all(k in o for k in ("summary", "opps", "ranks", "kwmap", "products", "audit", "google")))
import ceo_orders, agents, departments
chk("CEO hiểu: kiểm tra tốc độ website → Khải", ceo_orders._rule_plan("kiểm tra tốc độ website giúp anh")["actions"][0] == {"type": "seo_team", "job": "audit"})
chk("CEO hiểu: báo cáo seo → Vy", ceo_orders._rule_plan("báo cáo seo tuần này")["actions"][0]["job"] == "report")
chk("Hương, Khải có trong đội và Phòng Website", {"huong", "khai"} <= set(agents.ORDER) and {"huong", "khai"} <= set(departments.DEPTS["website"]["core"]))
T._http = lambda *a, **k: Resp(403, {"error": {"message": "The caller does not have permission"}})
T._tok["v"] = ""
t = c.post("/api/seo/google/test").json()
chk("Google từ chối: báo cách sửa bằng tiếng Việt", not t["ok"] and "từ chối" in t["steps"][0]["msg"], t)
print(f"XONG {ok}/{n}")

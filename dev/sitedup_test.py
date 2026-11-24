"""Website: liên kết tới trang không còn được sửa, từ khóa trùng chủ đề bị chặn, gộp bài trùng chuyển địa chỉ cũ."""
import sys, os, shutil, json, re
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "backend"))
from pathlib import Path
SP = Path(os.environ.get("MT_WORK") or Path(__file__).resolve().parent / "work")
import db
db.DB_PATH = SP / "sitedup.db"; db.DB_PATH.unlink(missing_ok=True)
db.DATA_DIR = SP / "sitedup_data"; shutil.rmtree(db.DATA_DIR, ignore_errors=True); db.DATA_DIR.mkdir()
db.PROFILES_DIR = SP / "sitedup_prof"; shutil.rmtree(db.PROFILES_DIR, ignore_errors=True); db.PROFILES_DIR.mkdir()
db.init(); db.set_setting("site_domain", "https://moctam.vn")
import website as W
W.SITE_DIR = db.DATA_DIR / "site"
from fastapi.testclient import TestClient
import main
c = TestClient(main.app)
ok = n = 0
def chk(name, cond, info=""):
    global ok, n
    n += 1; ok += bool(cond); print(("✓ " if cond else "✗ ") + name, "" if cond else info)

chk("giống: gia công trà túi lọc / OEM trà túi lọc", W.kw_similar("gia công trà túi lọc", "OEM trà túi lọc thương hiệu riêng"))
chk("giống: nguồn hàng sỉ trà túi lọc / nguồn hàng trà túi lọc sỉ", W.kw_similar("nguồn hàng sỉ trà túi lọc", "nguồn hàng trà túi lọc sỉ"))
chk("khác ý định: gia công / nguồn sỉ", not W.kw_similar("gia công trà túi lọc", "nguồn hàng trà túi lọc sỉ"))
chk("khác: bài kiến thức / bài mua sỉ", not W.kw_similar("kinh doanh trà thảo mộc online cần chuẩn bị gì", "nhập sỉ trà thảo mộc giá xưởng"))
# sếp thêm từ khóa trùng: báo, bấm lại thì thêm
r = c.post("/api/website/keywords", json={"keyword": "nguồn hàng trà túi lọc sỉ giá tốt"})
chk("sếp thêm từ khóa trùng bị báo", r.status_code == 409 and "Gần giống" in r.json()["detail"], r.text[:200])
chk("bấm lại thì vẫn thêm", c.post("/api/website/keywords", json={"keyword": "nguồn hàng trà túi lọc sỉ giá tốt", "force": True}).status_code == 200)
# Vy viết: bài 1, rồi từ khóa trùng trong kế hoạch bị bỏ khi tự chọn
p1 = W.write("gia công trà túi lọc"); W.publish(p1["id"])
db.run("UPDATE site_keywords SET priority=0 WHERE keyword='OEM trà túi lọc thương hiệu riêng'")
p2 = W.get(W.write()['id'])
k = db.one("SELECT status, note FROM site_keywords WHERE keyword='OEM trà túi lọc thương hiệu riêng'")
chk("Vy tự bỏ từ khóa trùng bài đã viết", k["status"] == "dup" and "gia công trà túi lọc" in (k["note"] or ""), k)
chk("Vy viết từ khóa kế tiếp không trùng", not W.kw_similar(p2["keyword"], "gia công trà túi lọc"), p2["keyword"])
before = W.plan_more(20)
kws = [r["keyword"] for r in db.q("SELECT keyword FROM site_keywords WHERE source='vy' AND status='planned'")]
chk("Vy nghĩ thêm không ra từ khóa trùng", not any(W.kw_similar(a, b) for i, a in enumerate(kws) for b in kws[i + 1:]), kws)
# bài trùng đã đăng (sếp ép viết) -> gợi ý gộp
p3 = W.write("trà túi lọc", agent="vy"); W.publish(p3["id"])
o = c.get("/api/website").json()
grp = [g for g in o["dups"] if {g["keep"]["id"]} | {x["id"] for x in g["others"]} == {p1["id"], p3["id"]}]
chk("phát hiện 2 bài đang đăng trùng chủ đề", grp, o["dups"])
keep, other = grp[0]["keep"], grp[0]["others"][0]
# liên kết hỏng: bài trỏ tới sản phẩm không có trang
db.run("UPDATE site_posts SET body=body||? WHERE id=?", ("\n\nXem [sản phẩm cũ](/san-pham/khong-con-nua/) và [bài cũ](/tin-tuc/bai-da-go.html#muc).", keep["id"]))
o = c.post(f"/api/website/posts/{other['id']}/merge", json={"into": keep["id"]}).json()
site = W.SITE_DIR
art = (site / "tin-tuc" / f"{keep['slug']}.html").read_text()
chk("link sản phẩm không còn -> trang Sản phẩm", 'href="/san-pham.html">sản phẩm cũ' in art and "khong-con-nua" not in art)
chk("link bài không còn -> trang Tin tức", 'href="/tin-tuc.html">bài cũ' in art)
st = (site / "tin-tuc" / f"{other['slug']}.html").read_text()
chk("bài gộp: địa chỉ cũ chuyển sang bài giữ", f"/tin-tuc/{keep['slug']}.html" in st and "refresh" in st, st[:300])
sm = (site / "sitemap.xml").read_text()
chk("bài gộp ra khỏi sitemap, bài giữ vẫn có", f"/tin-tuc/{other['slug']}.html" not in sm and f"/tin-tuc/{keep['slug']}.html" in sm)
chk("hết nhóm trùng sau khi gộp", not any(g["keep"]["id"] == keep["id"] for g in o["dups"]))
W.unpublish(p2["id"])
chk("gộp vào bài chưa đăng bị chặn", c.post(f"/api/website/posts/{keep['id']}/merge", json={"into": p2["id"]}).status_code == 400)
# không trang nào trỏ tới trang .html không có
bad = set()
for f in site.rglob("*.html"):
    for u in re.findall(r'href="(/[^"#?]*\.html)', f.read_text()):
        if not (site / u.lstrip("/")).exists():
            bad.add(u)
chk("không còn liên kết nội bộ hỏng", not bad, bad)
print(f"XONG {ok}/{n}")

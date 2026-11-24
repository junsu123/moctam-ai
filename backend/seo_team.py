"""Đội SEO của Phòng Website: Vy (SEO Leader), Hương (SEO Content Specialist), Khải (Technical SEO).

Kết nối Google bằng tài khoản dịch vụ (JSON sếp dán, không trả về giao diện):
  Search Console  thứ hạng, lượt hiển thị, lượt bấm theo từ khóa / trang; gửi sitemap; kiểm tra index từng trang
  GA4             lượt truy cập, lượt bấm Zalo / Gọi trên website (sự kiện contact_click do site.js gửi)
  PageSpeed       tốc độ thật trên điện thoại (không cần khóa; có khóa thì ít bị giới hạn)
Vy    mỗi sáng đọc số liệu, theo dõi thứ hạng từ khóa, tìm cơ hội (từ khóa trang 2, CTR thấp, từ khóa mới khách đang tìm),
      phân từ khóa cho trang đích (sản phẩm / bài / danh mục), giao việc cho Hương, duyệt nội dung, báo cáo tuần.
Hương viết nội dung trang sản phẩm (tiêu đề, mô tả, thân trang, FAQ), sửa tiêu đề / mô tả trang có cơ hội, viết bài cùng Vy;
      kiểm chứng: con số không có trong thông tin sản phẩm thì không cho tự duyệt.
Khải  mỗi sáng kiểm tra kỹ thuật: link hỏng, tiêu đề / mô tả trùng hoặc sai độ dài, H1, canonical, schema, ảnh nặng / thiếu alt,
      trang mỏng, https, trang 404, tốc độ, index trên Google; tự sửa được thì sửa (dựng lại, gửi sitemap), còn lại giao người.
"""
import base64
import html
import json
import re
import threading
import time
from datetime import date, timedelta
from urllib.parse import quote

import db

TOKEN_URL = "https://oauth2.googleapis.com/token"
SCOPES = "https://www.googleapis.com/auth/webmasters https://www.googleapis.com/auth/analytics.readonly"
GSC = "https://www.googleapis.com/webmasters/v3"
INSPECT = "https://searchconsole.googleapis.com/v1/urlInspection/index:inspect"
GA4 = "https://analyticsdata.googleapis.com/v1beta"
PSI = "https://www.googleapis.com/pagespeedonline/v5/runPagespeed"
_tok = {"v": "", "exp": 0, "sa": ""}
_busy = {"leader": False, "content": False, "audit": False}
BIZ = ("tra", "ngu coc", "ca phe", "bot", "com", "gia cong", "si", "oem", "tui loc", "thao moc", "detox", "dinh duong", "nha may", "xuong")


def s() -> dict:
    return db.get_settings()


def _status(aid, state, text):
    try:
        import workflows
        workflows.set_status(aid, state, text)
    except Exception:
        pass


# ---------------------------------------------------------------- Google: tài khoản dịch vụ
class GoogleError(Exception):
    pass


def _sa() -> dict | None:
    raw = (s().get("seo_google_sa") or "").strip()
    if not raw:
        return None
    try:
        d = json.loads(raw)
    except ValueError:
        raise GoogleError("Tệp khóa JSON không đọc được: dán nguyên nội dung tệp .json tải từ Google Cloud")
    if not d.get("client_email") or "PRIVATE KEY" not in (d.get("private_key") or ""):
        raise GoogleError("JSON không phải khóa tài khoản dịch vụ (thiếu client_email / private_key)")
    return d


def sa_email() -> str:
    try:
        return (_sa() or {}).get("client_email", "")
    except GoogleError:
        return ""


def configured() -> bool:
    return bool(sa_email())


def _b64(b: bytes) -> str:
    return base64.urlsafe_b64encode(b).rstrip(b"=").decode()


def make_jwt(sa: dict, now: int | None = None) -> str:
    from cryptography.hazmat.primitives import hashes, serialization
    from cryptography.hazmat.primitives.asymmetric import padding
    now = now or int(time.time())
    head = _b64(json.dumps({"alg": "RS256", "typ": "JWT"}).encode())
    claim = _b64(json.dumps({"iss": sa["client_email"], "scope": SCOPES, "aud": TOKEN_URL, "iat": now, "exp": now + 3600}).encode())
    key = serialization.load_pem_private_key(sa["private_key"].encode(), None)
    return f"{head}.{claim}.{_b64(key.sign(f'{head}.{claim}'.encode(), padding.PKCS1v15(), hashes.SHA256()))}"


def _http(method: str, url: str, **kw):
    """Một lần gọi HTTP (test thay hàm này bằng Google giả)."""
    import httpx
    with httpx.Client(timeout=kw.pop("timeout", 40), follow_redirects=kw.pop("follow", True)) as c:
        return c.request(method, url, **kw)


def _why(r, what: str) -> str:
    try:
        err = r.json().get("error", {})
        msg = err.get("message", "") if isinstance(err, dict) else str(err)
    except Exception:
        msg = r.text[:200]
    em = sa_email()
    if "has not been used" in msg or "SERVICE_DISABLED" in msg or "disabled" in msg.lower():
        api = "Google Analytics Data API" if "analytics" in what.lower() else "Google Search Console API" if "search" in what.lower() else "API"
        return f"{what}: chưa bật {api} trong Google Cloud (APIs & Services → Library → Enable)"
    if r.status_code in (401, 403):
        where = ("GA4 → Quản trị → Quyền truy cập thuộc tính → thêm email, vai trò Người xem" if "analytics" in what.lower()
                 else "Search Console → Cài đặt → Người dùng và quyền → Thêm người dùng, quyền Đầy đủ")
        return f"{what}: tài khoản dịch vụ chưa có quyền. Vào {where}: {em}"
    if r.status_code == 404:
        return f"{what}: không tìm thấy (sai mã thuộc tính GA4 hoặc trang web chưa có trong Search Console)"
    return f"{what}: lỗi {r.status_code} {msg[:150]}"


def token() -> str:
    sa = _sa()
    if not sa:
        raise GoogleError("Chưa kết nối Google: dán khóa tài khoản dịch vụ ở mục Website → Đội SEO")
    if _tok["v"] and _tok["exp"] > time.time() + 60 and _tok["sa"] == sa["client_email"]:
        return _tok["v"]
    try:
        jwt = make_jwt(sa)
    except Exception as e:
        raise GoogleError(f"Khóa riêng trong JSON không dùng được ({e})")
    r = _http("POST", TOKEN_URL, data={"grant_type": "urn:ietf:params:oauth:grant-type:jwt-bearer", "assertion": jwt})
    if r.status_code != 200:
        raise GoogleError("Google từ chối khóa (tài khoản dịch vụ bị xóa / khóa bị thu hồi / giờ máy sai): " + r.text[:150])
    d = r.json()
    _tok.update(v=d["access_token"], exp=time.time() + int(d.get("expires_in", 3600)), sa=sa["client_email"])
    return _tok["v"]


def _g(method: str, url: str, what: str, **kw):
    r = _http(method, url, headers={"Authorization": f"Bearer {token()}"}, **kw)
    if r.status_code >= 300:
        raise GoogleError(_why(r, what))
    return r.json() if r.text.strip() else {}


def domain() -> str:
    import site_deploy
    return site_deploy.domain()


def gsc_site() -> str:
    """Trang web trong Search Console: lấy theo cài đặt, chưa có thì tự tìm theo tên miền website."""
    st = s()
    if st.get("seo_gsc_site"):
        return st["seo_gsc_site"]
    sites = [x["siteUrl"] for x in _g("GET", f"{GSC}/sites", "Search Console").get("siteEntry", [])
             if x.get("permissionLevel") != "siteUnverifiedUser"]
    d = domain()
    pick = next((x for x in sites if d and (x == f"sc-domain:{d.removeprefix('www.')}" or d in x)), None) or (sites[0] if len(sites) == 1 else None)
    if not pick:
        raise GoogleError("Tài khoản dịch vụ chưa thấy trang web nào trong Search Console" + (f" (có: {', '.join(sites)})" if sites else
                          f". Thêm {sa_email()} vào Search Console → Cài đặt → Người dùng và quyền"))
    db.set_setting("seo_gsc_site", pick)
    return pick


def gsc_query(start: str, end: str, dims: list[str], limit: int = 1000) -> list[dict]:
    d = _g("POST", f"{GSC}/sites/{quote(gsc_site(), safe='')}/searchAnalytics/query", "Search Console",
           json={"startDate": start, "endDate": end, "dimensions": dims, "rowLimit": limit})
    return [{**dict(zip(dims, r.get("keys", []))), "clicks": int(r.get("clicks", 0)), "impressions": int(r.get("impressions", 0)),
             "ctr": float(r.get("ctr", 0)), "position": float(r.get("position", 0))} for r in d.get("rows", [])]


def gsc_submit_sitemap() -> str:
    feed = f"https://{domain()}/sitemap.xml"
    _g("PUT", f"{GSC}/sites/{quote(gsc_site(), safe='')}/sitemaps/{quote(feed, safe='')}", "Search Console (gửi sitemap)")
    return feed


def gsc_inspect(url: str) -> dict:
    d = _g("POST", INSPECT, "Search Console (kiểm tra index)", json={"inspectionUrl": url, "siteUrl": gsc_site(), "languageCode": "vi"})
    st = (d.get("inspectionResult") or {}).get("indexStatusResult") or {}
    return {"verdict": st.get("verdict", ""), "coverage": st.get("coverageState", ""), "last_crawl": (st.get("lastCrawlTime") or "")[:10]}


def ga4_report(body: dict) -> list[dict]:
    pid = re.sub(r"\D", "", s().get("seo_ga4_property") or "")
    if not pid:
        return []
    d = _g("POST", f"{GA4}/properties/{pid}:runReport", "Google Analytics (GA4)", json=body)
    dn = [x["name"] for x in d.get("dimensionHeaders", [])]
    mn = [x["name"] for x in d.get("metricHeaders", [])]
    return [{**{dn[i]: v["value"] for i, v in enumerate(r.get("dimensionValues", []))},
             **{mn[i]: float(v["value"]) for i, v in enumerate(r.get("metricValues", []))}} for r in d.get("rows", [])]


def psi(url: str) -> dict:
    p = {"url": url, "strategy": "mobile", "category": "performance"}
    if s().get("seo_psi_key"):
        p["key"] = s()["seo_psi_key"]
    r = _http("GET", PSI, params=p, timeout=90)
    if r.status_code != 200:
        raise GoogleError(f"PageSpeed: lỗi {r.status_code} {r.text[:120]}")
    lh = r.json().get("lighthouseResult", {})
    a = lh.get("audits", {})
    num = lambda k: (a.get(k) or {}).get("numericValue")
    return {"url": url, "score": round(100 * ((lh.get("categories", {}).get("performance") or {}).get("score") or 0)),
            "lcp": round((num("largest-contentful-paint") or 0) / 1000, 1), "cls": round(num("cumulative-layout-shift") or 0, 3),
            "tbt": round(num("total-blocking-time") or 0)}


def test_google() -> dict:
    steps, ok = [], True

    def step(name, good, msg=""):
        nonlocal ok
        ok = ok and good
        steps.append({"name": name, "ok": good, "msg": msg})
    try:
        _tok["v"] = ""
        token()
        step("Khóa tài khoản dịch vụ", True, sa_email())
    except GoogleError as e:
        step("Khóa tài khoản dịch vụ", False, str(e))
        return {"ok": False, "steps": steps, "email": sa_email()}
    try:
        site = gsc_site()
        end = (date.today() - timedelta(days=3)).isoformat()
        rows = gsc_query((date.today() - timedelta(days=30)).isoformat(), end, ["query"], 5)
        step("Search Console", True, f"{site}: đọc được dữ liệu" + (f", từ khóa đầu: “{rows[0]['query']}”" if rows else " (chưa có lượt hiển thị)"))
    except GoogleError as e:
        step("Search Console", False, str(e))
    if s().get("seo_ga4_property"):
        try:
            r = ga4_report({"dateRanges": [{"startDate": "7daysAgo", "endDate": "yesterday"}], "metrics": [{"name": "sessions"}]})
            step("GA4", True, f"{int(r[0]['sessions']) if r else 0} lượt truy cập 7 ngày")
        except GoogleError as e:
            step("GA4", False, str(e))
    else:
        step("GA4", False, "Chưa điền mã thuộc tính GA4 (GA4 → Quản trị → Chi tiết thuộc tính, dãy số 9–10 chữ số)")
    if not (s().get("site_ga_id") or "").strip():
        step("Mã đo GA4 trên website", False, "Điền mã G-XXXX ở tab Thông tin công ty để website gửi lượt truy cập và lượt bấm Zalo về GA4")
    return {"ok": ok, "steps": steps, "email": sa_email()}


# ---------------------------------------------------------------- Vy: SEO Leader
def _relevant(q: str) -> bool:
    t = " " + _plain(q) + " "
    if any(f" {b} " in t for b in BIZ):
        return True
    names = [_plain(p["name"]) for p in db.q("SELECT name FROM products")]
    return any(len(set(n.split()) & set(t.split())) >= 2 for n in names)


def _plain(t):
    import website
    return website.plain(t)


def pull() -> dict:
    """Đọc Search Console (28 ngày, so với 28 ngày trước) và GA4 vào máy."""
    today = date.today()
    end = today - timedelta(days=3)  # Search Console trễ 2–3 ngày
    cur = gsc_query((end - timedelta(days=27)).isoformat(), end.isoformat(), ["query", "page"])
    prev = gsc_query((end - timedelta(days=55)).isoformat(), (end - timedelta(days=28)).isoformat(), ["query", "page"])
    daily = gsc_query((end - timedelta(days=34)).isoformat(), end.isoformat(), ["date"])
    db.run("DELETE FROM seo_gsc")
    for period, rows in (("cur", cur), ("prev", prev)):
        for r in rows:
            db.run("INSERT INTO seo_gsc(query, page, clicks, impressions, ctr, position, period) VALUES (?,?,?,?,?,?,?)",
                   (r["query"], r["page"], r["clicks"], r["impressions"], r["ctr"], r["position"], period))
    for r in daily:
        db.run("INSERT INTO seo_daily(day, clicks, impressions, position) VALUES (?,?,?,?) ON CONFLICT(day) DO UPDATE SET "
               "clicks=excluded.clicks, impressions=excluded.impressions, position=excluded.position",
               (r["date"], r["clicks"], r["impressions"], r["position"]))
    ga = 0
    try:
        rng = [{"startDate": "35daysAgo", "endDate": "yesterday"}]
        for r in ga4_report({"dateRanges": rng, "dimensions": [{"name": "date"}], "metrics": [{"name": "sessions"}]}):
            d = f"{r['date'][:4]}-{r['date'][4:6]}-{r['date'][6:]}"
            db.run("INSERT INTO seo_daily(day, sessions) VALUES (?,?) ON CONFLICT(day) DO UPDATE SET sessions=excluded.sessions", (d, int(r["sessions"])))
            ga += 1
        for r in ga4_report({"dateRanges": rng, "dimensions": [{"name": "date"}], "metrics": [{"name": "eventCount"}],
                             "dimensionFilter": {"filter": {"fieldName": "eventName", "stringFilter": {"value": "contact_click"}}}}):
            d = f"{r['date'][:4]}-{r['date'][4:6]}-{r['date'][6:]}"
            db.run("INSERT INTO seo_daily(day, contacts) VALUES (?,?) ON CONFLICT(day) DO UPDATE SET contacts=excluded.contacts", (d, int(r["eventCount"])))
    except GoogleError as e:
        import errors
        errors.report("website", "Vy chưa đọc được GA4", str(e), screen="website")
    return {"queries": len(cur), "days": len(daily), "ga_days": ga}


def _agg(period: str) -> dict:
    out = {}
    for r in db.q("SELECT query, SUM(clicks) c, SUM(impressions) i, SUM(position*impressions)/MAX(SUM(impressions),1) p, MAX(page) page "
                  "FROM seo_gsc WHERE period=? GROUP BY query", (period,)):
        out[r["query"]] = r
    return out


def _page_of(url: str) -> tuple[str, int | None]:
    """URL trên website → ('product', id) / ('post', id) / ('other', None)."""
    import website
    path = re.sub(r"^https?://[^/]+", "", url or "").split("#")[0].split("?")[0]
    m = re.match(r"^/san-pham/([^/]+?)(?:\.html|/)?$", path)
    if m:
        p = next((x for x in website._product_pages() if x["slug"] == m.group(1)), None) if path != "/san-pham.html" else None
        if p:
            return "product", p["id"]
    m = re.match(r"^/tin-tuc/([^/]+?)(?:\.html|/)?$", path)
    if m:
        r = db.one("SELECT id FROM site_posts WHERE slug=?", (m.group(1),))
        if r:
            return "post", r["id"]
    return "other", None


def opportunities(limit: int = 12) -> list[dict]:
    """Từ khóa khách đang tìm thấy website: trang 2 (vị trí 4–20) hoặc top 5 mà ít người bấm."""
    cur, prev = _agg("cur"), _agg("prev")
    out = []
    for q, r in cur.items():
        pos, imp, ctr = r["p"] or 0, r["i"] or 0, (r["c"] or 0) / max(r["i"] or 1, 1)
        kind = None
        if imp >= 10 and 4 <= pos <= 20:
            kind = "Đẩy lên trang 1"
        elif imp >= 30 and pos < 4 and ctr < 0.02:
            kind = "Nhiều người thấy, ít người bấm: sửa tiêu đề / mô tả"
        if kind:
            p0 = (prev.get(q) or {}).get("p")
            out.append({"query": q, "impressions": imp, "clicks": r["c"] or 0, "position": round(pos, 1), "page": r["page"],
                        "prev_position": round(p0, 1) if p0 else None, "kind": kind, "value": imp * (21 - min(pos, 20))})
    out.sort(key=lambda x: -x["value"])
    return out[:limit]


def keyword_map() -> list[dict]:
    """Từ khóa → trang đích (topic cluster): bài đã viết / trang sản phẩm / trang danh mục."""
    import website
    prods = website._product_pages()
    posts = db.q("SELECT id, keyword, slug, status FROM site_posts WHERE status='published'")
    out = []
    kws = [r for r in db.q("SELECT keyword, status, cluster FROM site_keywords WHERE status!='dup' ORDER BY priority, id")]
    for k in kws[:60]:
        kw = k["keyword"]
        post = next((p for p in posts if _plain(p["keyword"]) == _plain(kw) or website.kw_similar(p["keyword"], kw)), None)
        toks = set(_plain(kw).split())
        prod = max(prods, key=lambda p: len(toks & set(_plain(p["name"]).split())), default=None)
        prod = prod if prod and len(toks & set(_plain(prod["name"]).split())) >= 2 else None
        intent = website.kw_sig(kw)[0]
        if post:
            url, kind = website.u_post(post["slug"]), "Bài viết"
        elif prod and intent != "info":
            url, kind = website.u_prod(prod["slug"]), "Trang sản phẩm"
        elif intent == "gc":
            url, kind = "/gia-cong.html", "Trang Gia công"
        elif intent == "si":
            url, kind = "/san-pham.html", "Danh mục Sản phẩm"
        else:
            url, kind = "", "Cần bài mới"
        out.append({"keyword": kw, "cluster": k["cluster"] or (prod or {}).get("category") or "", "status": k["status"], "url": url, "kind": kind})
    return out


def _rank_snapshot():
    cur = _agg("cur")
    day = db.today()
    kws = [r["keyword"] for r in db.q("SELECT keyword FROM site_keywords WHERE status IN ('written','planned')")]
    for kw in kws:
        pk = _plain(kw)
        rows = [r for q, r in cur.items() if _plain(q) == pk] or [r for q, r in cur.items() if pk in _plain(q)]
        if rows:
            best = max(rows, key=lambda r: r["i"] or 0)
            db.run("INSERT OR REPLACE INTO seo_rank(day, keyword, position, clicks, impressions) VALUES (?,?,?,?,?)",
                   (day, kw, round(best["p"] or 0, 1), best["c"] or 0, best["i"] or 0))


def ranks() -> list[dict]:
    last = db.one("SELECT MAX(day) d FROM seo_rank")
    if not last or not last["d"]:
        return []
    rows = db.q("SELECT * FROM seo_rank WHERE day=? ORDER BY position", (last["d"],))
    for r in rows:
        p = db.one("SELECT position FROM seo_rank WHERE keyword=? AND day<=? ORDER BY day DESC LIMIT 1",
                   (r["keyword"], (date.fromisoformat(r["day"]) - timedelta(days=7)).isoformat()))
        r["prev"] = p["position"] if p else None
    return rows


def _task(kind: str, ref: int, query: str, reason: str) -> bool:
    if db.one("SELECT 1 x FROM seo_tasks WHERE kind=? AND ref_id=? AND status='todo'", (kind, ref)):
        return False
    db.run("INSERT INTO seo_tasks(kind, ref_id, query, reason, status, created_at) VALUES (?,?,?,?, 'todo', ?)", (kind, ref, query, reason, db.now()))
    return True


def run_leader(force: bool = False) -> dict:
    """Vy: đọc số liệu Google, theo dõi thứ hạng, giao việc cho Hương, thêm từ khóa khách đang tìm."""
    import website
    _status("vy", "working", "Đọc Search Console, GA4")
    res = {"pulled": None, "tasks": 0, "keywords": 0, "opps": 0}
    try:
        if configured():
            res["pulled"] = pull()
            _rank_snapshot()
        opps = opportunities(20)
        res["opps"] = len(opps)
        for o in opps[:6]:
            kind, ref = _page_of(o["page"])
            if kind == "product":
                res["tasks"] += _task("product", ref, o["query"], f"{o['kind']}: “{o['query']}” vị trí {o['position']}, {o['impressions']} lượt hiển thị")
            elif kind == "post":
                res["tasks"] += _task("post_meta", ref, o["query"], f"{o['kind']}: “{o['query']}” vị trí {o['position']}, {o['impressions']} lượt hiển thị")
        have = [r["keyword"] for r in db.q("SELECT keyword FROM site_keywords")] + [r["keyword"] for r in db.q("SELECT keyword FROM site_posts")]
        for q, r in sorted(_agg("cur").items(), key=lambda x: -(x[1]["i"] or 0)):
            if res["keywords"] >= 5:
                break
            if (r["i"] or 0) < 5 or len(q) > 80 or not _relevant(q) or website.similar_kw(q, have) or _plain(q) in {_plain(h) for h in have}:
                continue
            db.run("INSERT OR IGNORE INTO site_keywords(keyword, cluster, intent, priority, status, source, created_at) VALUES (?,?,?,?,?,?,?)",
                   (q, "", website.kw_sig(q)[0], 1 if (r["i"] or 0) >= 50 else 2, "planned", "gsc", db.now()))
            have.append(q)
            res["keywords"] += 1
        db.set_setting("seo_last_leader", db.now())
        if res["pulled"] or res["tasks"] or res["keywords"]:
            db.log("vy", "Phân tích SEO", (f"Đọc {res['pulled']['queries']} từ khóa từ Search Console; " if res["pulled"] else "")
                   + f"{res['opps']} cơ hội, giao Hương {res['tasks']} việc, thêm {res['keywords']} từ khóa khách đang tìm")
    except GoogleError as e:
        import errors
        errors.report("website", "Vy chưa đọc được Search Console", str(e), screen="website")
        res["error"] = str(e)
    finally:
        _status("vy", "idle", "Xong phân tích SEO")
    return res


def summary() -> dict:
    """Số liệu 28 ngày gần nhất so với 28 ngày trước (theo ngày có dữ liệu)."""
    rows = db.q("SELECT * FROM seo_daily ORDER BY day DESC LIMIT 56")
    def tot(rs):
        imp = sum(r["impressions"] or 0 for r in rs)
        return {"clicks": sum(r["clicks"] or 0 for r in rs), "impressions": imp,
                "position": round(sum((r["position"] or 0) * (r["impressions"] or 0) for r in rs) / imp, 1) if imp else None,
                "sessions": sum(r["sessions"] or 0 for r in rs), "contacts": sum(r["contacts"] or 0 for r in rs)}
    return {"cur": tot(rows[:28]), "prev": tot(rows[28:56]), "days": len(rows[:28]),
            "series": [{"day": r["day"], "clicks": r["clicks"] or 0, "impressions": r["impressions"] or 0} for r in reversed(rows[:28])]}


def weekly_report() -> str:
    sm = summary()
    c, p = sm["cur"], sm["prev"]
    pct = lambda a, b: (f" ({'+' if a >= b else ''}{round((a - b) / b * 100)}%)" if b else "")
    lines = [f"📈 <b>Báo cáo SEO tuần</b> (Vy) · 28 ngày",
             f"Lượt bấm từ Google: {c['clicks']}{pct(c['clicks'], p['clicks'])} · hiển thị {c['impressions']}{pct(c['impressions'], p['impressions'])}"
             + (f" · vị trí TB {c['position']}" if c["position"] else "")]
    if c["sessions"] or c["contacts"]:
        lines.append(f"Truy cập web: {c['sessions']} · bấm Zalo / Gọi: {c['contacts']}{pct(c['contacts'], p['contacts'])}")
    up = [r for r in ranks() if r.get("prev") and r["prev"] - r["position"] >= 2][:3]
    down = [r for r in ranks() if r.get("prev") and r["position"] - r["prev"] >= 2][:3]
    if up:
        lines.append("Lên hạng: " + "; ".join(f"{e(r['keyword'])} {r['prev']}→{r['position']}" for r in up))
    if down:
        lines.append("Xuống hạng: " + "; ".join(f"{e(r['keyword'])} {r['prev']}→{r['position']}" for r in down))
    op = opportunities(3)
    if op:
        lines.append("Cơ hội: " + "; ".join(f"{e(o['query'])} (vị trí {o['position']})" for o in op))
    a = db.one("SELECT score FROM seo_audit ORDER BY id DESC LIMIT 1")
    if a:
        lines.append(f"Sức khỏe kỹ thuật (Khải): {a['score']}/100")
    n = db.one("SELECT COUNT(*) n FROM site_product_seo WHERE status='approved'")["n"]
    lines.append(f"Trang sản phẩm đã tối ưu (Hương): {n}")
    return "\n".join(lines)


def e(x):
    return html.escape(str(x or ""))


# ---------------------------------------------------------------- Hương: SEO Content Specialist
def _num_ok(text: str, source: str) -> list[str]:
    """Kiểm chứng: con số trong bài phải có trong thông tin sản phẩm (không bịa %, gam, năm...)."""
    src = re.sub(r"[.,](?=\d{3}\b)", "", source)
    bad = []
    for n in set(re.findall(r"\d+(?:[.,]\d+)?", re.sub(r"[.,](?=\d{3}\b)", "", text))):
        if n not in src and n not in ("1", "2", "3", "4", "5", "100"):
            bad.append(n)
    return bad


def _src(p: dict) -> str:
    import website
    c = website.company()
    return " ".join(str(p.get(k) or "") for k in ("name", "category", "description", "selling_points", "moq", "uses")) + f" {c['certs']} {c['phone']} 63"


def product_check(d: dict, p: dict) -> dict:
    import website
    kw = d.get("keyword") or ""
    items = []
    add = lambda ok, label: items.append({"ok": bool(ok), "label": label})
    has = lambda t: bool(kw) and website.plain(kw) in website.plain(t or "")
    add(20 <= len(d.get("title") or "") <= 60 and has(d.get("title")), "Tiêu đề 20–60 ký tự, có từ khóa")
    add(110 <= len(d.get("meta") or "") <= 160, "Mô tả 110–160 ký tự")
    w = website.words(website.text_of(d.get("body") or ""))
    add(150 <= w <= 450, f"Thân trang 150–450 chữ (đang {w})")
    add(len(re.findall(r"^##\s", d.get("body") or "", re.M)) >= 2, "Có ít nhất 2 mục H2")
    add(len(d.get("faq") or []) >= 2, "Có ít nhất 2 câu hỏi thường gặp")
    add(has(" ".join((d.get("body") or "").split()[:80])), "Từ khóa trong đoạn đầu")
    bad = _num_ok(" ".join([d.get("title") or "", d.get("meta") or "", d.get("body") or ""] + [f"{q.get('q')} {q.get('a')}" for q in d.get("faq") or []]), _src(p))
    policy = []
    try:
        import fb_policy
        full = " ".join([d.get("title") or "", d.get("meta") or "", d.get("body") or ""] + [f"{q.get('q')} {q.get('a')}" for q in d.get("faq") or []])
        policy = [x["msg"] for x in fb_policy.check_text(full) if x["rule"] in ("health_claims", "superlatives", "guarantee") and x["level"] == "high"]
    except Exception:
        pass
    score = round(100 * sum(i["ok"] for i in items) / len(items))
    flags = ([f"Số liệu không có trong thông tin sản phẩm: {', '.join(sorted(bad)[:5])} (sếp kiểm lại)"] if bad else []) + policy
    return {"score": score, "items": items, "flags": flags, "ok": score >= 80 and not flags}


def _offline_product(p: dict, kw: str) -> dict:
    import website
    c = website.company()
    name = p["name"]
    desc = [x.strip() for x in (p.get("description") or "").splitlines() if x.strip()]
    sp = [x.strip(" -•") for x in (p.get("selling_points") or "").splitlines() if x.strip()]
    uses = (p.get("uses") or "").strip()
    body = (f"{kw[0].upper() + kw[1:]} tại nhà máy {c['name']}: {name} được sản xuất theo tiêu chuẩn {c['certs']}, nhận sỉ toàn quốc cho "
            "shop online, đại lý, nhà phân phối và nhận gia công in nhãn riêng.\n\n## Thông tin sản phẩm\n\n"
            + ("\n".join(f"- {x}" for x in desc[:6]) or f"- {name}") + "\n"
            + (("\n## Điểm nổi bật\n\n" + "\n".join(f"- {x}" for x in sp[:6]) + "\n") if sp else "")
            + (f"\n## Cách dùng\n\n{uses}\n" if uses else "")
            + "\n## Phù hợp với ai\n\n- Shop online, người bán trên Facebook, TikTok Shop, Shopee cần nguồn hàng ổn định.\n"
              "- Đại lý, nhà phân phối muốn thêm mặt hàng trà, ngũ cốc, đồ uống.\n- Thương hiệu muốn gia công in nhãn riêng.\n"
            + f"\n## Nhập sỉ và gia công\n\nNhập tối thiểu: {p.get('moq') or 'liên hệ để được báo theo quy cách'}. Giá sỉ báo theo số lượng, "
              f"nhắn Zalo {c['phone']} để nhận catalog, mẫu thử và báo giá. Nhà máy nhận in nhãn, thiết kế bao bì theo yêu cầu.")
    return {"keyword": kw, "title": website.cut(f"{kw[0].upper() + kw[1:]} | {c['name']}", 60) if len(kw) < 45 else website.cut(kw, 60),
            "meta": website.cut(f"{name} giá sỉ tại nhà máy {c['name']} đạt {c['certs']}. Nhận sỉ toàn quốc, gia công in nhãn riêng, "
                                f"có mẫu thử. Zalo {c['phone']}.", 160, dots=True),
            "body": body, "faq": [{"q": f"Nhập sỉ {name} tối thiểu bao nhiêu?", "a": f"{p.get('moq') or 'Tùy quy cách đóng gói'}. Nhắn Zalo {c['phone']} để được báo cụ thể."},
                                  {"q": f"Có gia công {name} in nhãn riêng không?", "a": "Có, nhà máy nhận in nhãn và thiết kế bao bì theo yêu cầu."},
                                  {"q": "Có mẫu thử trước khi nhập không?", "a": "Có, bạn nhận mẫu để đánh giá trước khi đặt hàng."}]}


def _product_kw(p: dict) -> str:
    """Từ khóa chính cho trang sản phẩm: từ khóa Google đang đưa khách tới trang đó, không có thì 'tên + sỉ'."""
    import website
    url = website.u_prod(next((x["slug"] for x in website._product_pages() if x["id"] == p["id"]), website.slugify(p["name"])))
    r = db.one("SELECT query FROM seo_gsc WHERE period='cur' AND page LIKE ? ORDER BY impressions DESC LIMIT 1", ("%" + url,))
    if r:
        return r["query"]
    base = re.sub(r"\s*[-–(].*$", "", p["name"]).strip().lower()
    return f"{base} sỉ"


def write_product(pid: int, query: str = "", reason: str = "") -> dict:
    """Hương viết nội dung SEO cho trang sản phẩm; Vy duyệt (đạt chuẩn + không có số liệu lạ + bật tự đăng)."""
    import website
    from llm import llm
    p = db.one("SELECT * FROM products WHERE id=?", (pid,))
    if not p:
        raise ValueError("Không có sản phẩm này")
    kw = query or _product_kw(p)
    _status("huong", "working", f"Viết trang sản phẩm: {p['name'][:40]}")
    try:
        d = None
        if llm.live:
            from agents import system_prompt
            c = website.company()
            old = db.one("SELECT * FROM site_product_seo WHERE product_id=?", (pid,))
            ask = (f"Viết nội dung chuẩn SEO cho TRANG SẢN PHẨM trên website nhà máy {c['name']} (đạt {c['certs']}; nhận sỉ toàn quốc, gia công "
                   f"in nhãn riêng). Từ khóa chính: “{kw}”.\nTHÔNG TIN SẢN PHẨM (chỉ dùng thông tin này, không thêm số liệu, thành phần, "
                   f"chứng nhận nào khác):\nTên: {p['name']}\nNhóm: {p.get('category') or ''}\nMô tả: {p.get('description') or ''}\n"
                   f"Điểm mạnh: {p.get('selling_points') or ''}\nCông dụng sếp ghi: {p.get('uses') or ''}\nNhập tối thiểu: {p.get('moq') or 'liên hệ'}\n"
                   + (f"Lý do viết lại: {reason}\n" if reason else "") + (f"Bản trước: {old['title']} / {old['meta']}\n" if old else "")
                   + "Người đọc là người bán online / đại lý / chủ thương hiệu tìm nguồn sỉ hoặc gia công, không phải người mua lẻ. "
                     "Thân trang 200–350 chữ, mở đầu có từ khóa, 3–4 mục '## H2' (thông tin sản phẩm, phù hợp bán cho ai, nhập sỉ & gia công...), "
                     f"gạch đầu dòng '- '. Không ghi giá (mời Zalo {c['phone']}); không hứa chữa bệnh, giảm cân; không dùng 'nhất', 'số 1'.\n"
                     "Trả JSON {\"title\": \"≤60 ký tự, có từ khóa\", \"meta\": \"120–160 ký tự\", \"body\": \"...\", "
                     "\"faq\": [{\"q\": \"...\", \"a\": \"...\"}] (3 câu)}")
            d = llm.json(system_prompt("huong", s()), ask, mock=None, max_tokens=1800, task="posts")
            if not isinstance(d, dict) or not d.get("body"):
                d = None
        d = d or _offline_product(p, kw)
        d["keyword"] = kw
        r = product_check(d, p)
        auto = s().get("site_auto_publish", "1") == "1" and r["ok"]
        status = "approved" if auto else "review"
        note = ("Vy duyệt: đạt chuẩn" if auto else "Chờ sếp: " + "; ".join(r["flags"] or [i["label"] for i in r["items"] if not i["ok"]]))
        db.run("""INSERT INTO site_product_seo(product_id, keyword, title, meta, body, faq, status, score, note, author, created_at, updated_at)
                  VALUES (?,?,?,?,?,?,?,?,?,?,?,?) ON CONFLICT(product_id) DO UPDATE SET keyword=excluded.keyword, title=excluded.title,
                  meta=excluded.meta, body=excluded.body, faq=excluded.faq, status=excluded.status, score=excluded.score, note=excluded.note,
                  author=excluded.author, updated_at=excluded.updated_at""",
               (pid, kw, d.get("title") or "", d.get("meta") or "", d["body"], json.dumps(d.get("faq") or [], ensure_ascii=False), status,
                r["score"], note, "huong", db.now(), db.now()))
        db.log("huong", "Viết trang sản phẩm", f"“{p['name']}” (từ khóa “{kw}”): {r['score']} điểm, " + ("Vy duyệt, lên website" if auto else note))
        return {"product_id": pid, "status": status, **r}
    finally:
        _status("huong", "idle", "Sẵn sàng")


def approve_product(pid: int, data: dict | None = None) -> dict:
    p = db.one("SELECT * FROM products WHERE id=?", (pid,))
    row = db.one("SELECT * FROM site_product_seo WHERE product_id=?", (pid,))
    if not p or not row:
        raise ValueError("Chưa có nội dung cho sản phẩm này")
    d = {**row, "faq": json.loads(row["faq"] or "[]")}
    for k in ("keyword", "title", "meta", "body"):
        if data and data.get(k) is not None:
            d[k] = str(data[k])
    if data and isinstance(data.get("faq"), list):
        d["faq"] = data["faq"]
    r = product_check(d, p)
    try:
        import fb_policy
        if any(x["level"] == "high" for x in fb_policy.check_text(d["body"] + d["title"] + d["meta"]) if x["rule"] == "health_claims"):
            raise ValueError("Nội dung hứa công dụng chữa bệnh, không đăng được")
    except ImportError:
        pass
    db.run("UPDATE site_product_seo SET keyword=?, title=?, meta=?, body=?, faq=?, status='approved', score=?, note='Sếp duyệt', updated_at=? WHERE product_id=?",
           (d["keyword"], d["title"], d["meta"], d["body"], json.dumps(d["faq"], ensure_ascii=False), r["score"], db.now(), pid))
    return {"ok": True, **r}


def reject_product(pid: int) -> dict:
    db.run("UPDATE site_product_seo SET status='rejected', updated_at=? WHERE product_id=?", (db.now(), pid))
    return {"ok": True}


def rewrite_post_meta(post_id: int, query: str) -> dict:
    """Hương sửa tiêu đề / mô tả bài đang có cơ hội để chứa đúng từ khóa khách tìm; chỉ giữ nếu điểm SEO không giảm."""
    import website
    from llm import llm
    p = website.get(post_id)
    if not p:
        return {"ok": False}
    c = website.company()
    mt = md = None
    if llm.live:
        from agents import system_prompt
        d = llm.json(system_prompt("huong", s()), f"Bài “{p['title']}” (từ khóa chính “{p['keyword']}”) đang hiện trên Google cho “{query}” nhưng ít người "
                     f"bấm. Viết lại thẻ tiêu đề và mô tả cho hấp dẫn, đúng nội dung bài, có cả hai cụm từ nếu tự nhiên. Không hứa công dụng, "
                     f"không 'nhất'. Mô tả bài: {p['meta_desc']}\nTrả JSON {{\"meta_title\": \"30–60 ký tự\", \"meta_desc\": \"120–160 ký tự\"}}",
                     mock=None, max_tokens=300, task="posts")
        if isinstance(d, dict):
            mt, md = d.get("meta_title"), d.get("meta_desc")
    if not mt:
        q = query[0].upper() + query[1:]
        mt = website.cut(f"{q}: {p['keyword']}" if website.plain(p["keyword"]) not in website.plain(query) else q, 60)
        mt = mt if len(mt) >= 30 else website.title_with(q, c["name"])
        md = website.cut(f"{q}: {p['meta_desc']}", 160, dots=True)
    new = {**p, "meta_title": mt, "meta_desc": md}
    old_s, new_s = website.seo_check(p)["score"], website.seo_check(new)["score"]
    if new_s < old_s:
        return {"ok": False, "why": f"điểm SEO giảm {old_s}→{new_s}, giữ bản cũ"}
    db.run("UPDATE site_posts SET meta_title=?, meta_desc=?, seo_score=?, updated_at=? WHERE id=?", (mt, md, new_s, db.now(), post_id))
    db.log("huong", "Sửa tiêu đề / mô tả bài", f"“{p['title']}” theo từ khóa khách tìm “{query}” (Vy duyệt: SEO {old_s}→{new_s})")
    return {"ok": True, "meta_title": mt, "meta_desc": md}


def run_content(n: int | None = None) -> dict:
    """Hương: làm việc Vy giao (từ Search Console), rồi tối ưu trang sản phẩm chưa có nội dung SEO."""
    import website
    n = n or int(s().get("seo_product_per_day") or 2)
    done = []
    for t in db.q("SELECT * FROM seo_tasks WHERE status='todo' ORDER BY id LIMIT 3"):
        try:
            if t["kind"] == "product":
                write_product(t["ref_id"], t["query"], t["reason"])
            elif t["kind"] == "post_meta":
                rewrite_post_meta(t["ref_id"], t["query"])
            db.run("UPDATE seo_tasks SET status='done', done_at=? WHERE id=?", (db.now(), t["id"]))
            done.append(t["kind"])
        except Exception as e:
            db.run("UPDATE seo_tasks SET status='skip', done_at=?, reason=reason||? WHERE id=?", (db.now(), f" · lỗi: {e}"[:200], t["id"]))
    have = {r["product_id"] for r in db.q("SELECT product_id FROM site_product_seo WHERE status IN ('approved','review')")}
    for p in [x for x in website.site_products() if x["id"] not in have][:n]:
        write_product(p["id"])
        done.append("product")
    db.set_setting("seo_last_content", db.now())
    if done:
        website.build()
    return {"done": len(done)}


# ---------------------------------------------------------------- Khải: Technical SEO
def _local_audit() -> list[dict]:
    import website
    site = website.SITE_DIR
    if not (site / "index.html").exists():
        website.build()
    issues = []
    add = lambda sev, area, msg, fix, who="khai", url="": issues.append({"sev": sev, "area": area, "msg": msg, "fix": fix, "who": who, "url": url})
    titles, descs = {}, {}
    broken, noalt, thin, h1bad, ldbad, nocanon = [], [], [], [], [], []
    for f in site.rglob("*.html"):
        rel = "/" + str(f.relative_to(site)).replace("\\", "/")
        if f.name == "404.html":
            continue
        doc = f.read_text(encoding="utf-8", errors="ignore")
        if 'http-equiv="refresh"' in doc:
            continue  # trang chuyển từ địa chỉ cũ
        url = "/" if rel == "/index.html" else rel
        t = (re.search(r"<title>(.*?)</title>", doc, re.S) or [None, ""])[1]
        dsc = (re.search(r'<meta name="description" content="([^"]*)"', doc) or [None, ""])[1]
        titles.setdefault(html.unescape(t), []).append(url)
        descs.setdefault(html.unescape(dsc), []).append(url)
        if not 20 <= len(html.unescape(t)) <= 65:
            add("med", "Tiêu đề", f"Thẻ tiêu đề {len(html.unescape(t))} ký tự", "Giữ 20–65 ký tự", "huong", url)
        if not 70 <= len(html.unescape(dsc)) <= 160:
            add("low", "Mô tả", f"Thẻ mô tả {len(html.unescape(dsc))} ký tự", "Giữ 70–160 ký tự", "huong", url)
        if len(re.findall(r"<h1[\s>]", doc)) != 1:
            h1bad.append(url)
        if 'rel="canonical"' not in doc:
            nocanon.append(url)
        for m in re.findall(r'<script type="application/ld\+json">(.*?)</script>', doc, re.S):
            try:
                json.loads(m)
            except ValueError:
                ldbad.append(url)
        for u in re.findall(r'href="(/[^"#?]*\.html)', doc):
            if not (site / u.lstrip("/")).exists():
                broken.append((url, u))
        for img in re.findall(r"<img\b[^>]*>", doc):
            if " alt=" not in img:
                noalt.append(url)
        if url.startswith("/san-pham/"):
            main = re.sub(r"<[^>]+>", " ", (re.search(r'<section class="pdesc">(.*?)</section>', doc, re.S) or [None, ""])[1])
            lead = re.sub(r"<[^>]+>", " ", (re.search(r'<div class="pi">(.*?)<table', doc, re.S) or [None, ""])[1])
            if len((main + " " + lead).split()) < 120:
                thin.append(url)
    for t, us in titles.items():
        if len(us) > 1 and not all("/tin-tuc/trang-" in u or u == "/tin-tuc.html" for u in us):
            add("med", "Tiêu đề trùng", f"{len(us)} trang cùng tiêu đề “{t[:60]}”", "Mỗi trang một tiêu đề riêng", "huong", us[0])
    for t, us in descs.items():
        if len(us) > 1 and t and not all("/tin-tuc" in u for u in us):
            add("low", "Mô tả trùng", f"{len(us)} trang cùng thẻ mô tả", "Mỗi trang một mô tả riêng", "huong", us[0])
    if broken:
        add("high", "Link hỏng", f"{len(broken)} liên kết nội bộ tới trang không có (VD {broken[0][1]} ở {broken[0][0]})", "Khải dựng lại website", "khai", broken[0][0])
    if h1bad:
        add("med", "H1", f"{len(h1bad)} trang không có đúng 1 thẻ H1", "Mỗi trang 1 H1", "khai", h1bad[0])
    if nocanon:
        add("med", "Canonical", f"{len(nocanon)} trang thiếu canonical", "Thêm thẻ canonical", "khai", nocanon[0])
    if ldbad:
        add("high", "Schema", f"{len(ldbad)} trang có dữ liệu cấu trúc (JSON-LD) lỗi", "Sửa schema", "khai", ldbad[0])
    if noalt:
        add("low", "Ảnh", f"{len(noalt)} ảnh thiếu chữ thay thế (alt)", "Thêm alt mô tả ảnh", "khai", noalt[0])
    if thin:
        add("med", "Trang mỏng", f"{len(thin)} trang sản phẩm dưới 120 chữ", "Hương viết nội dung trang sản phẩm", "huong", thin[0])
        for u in thin:
            kind, ref = _page_of(u)
            if kind == "product":
                _task("product", ref, "", "Khải báo: trang sản phẩm mỏng, dưới 120 chữ")
    media = site / "media"
    heavy = [x for x in media.glob("*") if x.is_file() and x.stat().st_size > 400_000] if media.exists() else []
    if heavy:
        add("med", "Ảnh nặng", f"{len(heavy)} ảnh trên 400 KB (VD {heavy[0].name}, {heavy[0].stat().st_size // 1024} KB)", "Thu nhỏ / nén ảnh trước khi tải lên", "sep", "/media/" + heavy[0].name)
    sm = (site / "sitemap.xml").read_text(encoding="utf-8") if (site / "sitemap.xml").exists() else ""
    base = website.company()["domain"]
    miss = [u for u in re.findall(r"<loc>([^<]+)</loc>", sm) if not (site / (u.replace(base, "").lstrip("/") or "index.html")).exists()]
    if miss:
        add("high", "Sitemap", f"{len(miss)} địa chỉ trong sitemap không có trang", "Khải dựng lại website", "khai", miss[0])
    if not base:
        add("high", "Tên miền", "Chưa điền tên miền: canonical, sitemap đang dùng đường dẫn tương đối", "Điền tên miền ở tab Thông tin công ty", "sep")
    if not (s().get("site_ga_id") or "").strip():
        add("med", "Đo lường", "Website chưa gắn GA4 (không đo được truy cập, lượt bấm Zalo)", "Điền mã G-XXXX ở tab Thông tin công ty", "sep")
    return issues


def _online_audit(issues: list, psi_run: bool) -> dict:
    out = {"psi": [], "index": None}
    d = domain()
    if not d:
        return out
    add = lambda sev, area, msg, fix, who="khai", url="": issues.append({"sev": sev, "area": area, "msg": msg, "fix": fix, "who": who, "url": url})
    try:
        r = _http("GET", f"http://{d}/", follow=False, timeout=20)
        loc = r.headers.get("location", "")
        if r.status_code not in (301, 302, 307, 308) or not loc.startswith("https://"):
            add("med", "HTTPS", "Bản http:// không tự chuyển sang https://", "cPanel → Domains → bật Force HTTPS Redirect", "sep", f"http://{d}/")
        elif r.status_code != 301 and r.status_code != 308:
            add("low", "HTTPS", f"http:// chuyển sang https:// bằng mã {r.status_code} (nên dùng 301)", "Bật Force HTTPS Redirect (301)", "sep")
        r = _http("GET", f"https://{d}/khai-kiem-tra-404.html", timeout=20)
        if r.status_code == 200:
            add("med", "404", "Trang không tồn tại vẫn trả mã 200 (soft 404)", "cPanel → Error Pages hoặc .htaccess: ErrorDocument 404 /404.html", "sep")
    except Exception as ex:
        add("high", "Truy cập", f"Không mở được https://{d}/ ({str(ex)[:80]})", "Kiểm tra hosting / tên miền", "sep")
        return out
    if psi_run:
        import website
        urls = [f"https://{d}/"]
        pp = website._product_pages()
        if pp:
            urls.append(f"https://{d}{website.u_prod(pp[0]['slug'])}")
        post = db.one("SELECT slug FROM site_posts WHERE status='published' ORDER BY id DESC LIMIT 1")
        if post:
            urls.append(f"https://{d}{website.u_post(post['slug'])}")
        for u in urls:
            try:
                x = psi(u)
                out["psi"].append(x)
                if x["score"] < 50 or x["lcp"] > 4:
                    add("high", "Tốc độ", f"Điện thoại {x['score']}/100, LCP {x['lcp']} giây", "Nén ảnh lớn, giảm ảnh đầu trang", "khai", u)
                elif x["score"] < 90 or x["lcp"] > 2.5:
                    add("med", "Tốc độ", f"Điện thoại {x['score']}/100, LCP {x['lcp']} giây (tốt: ≥ 90, LCP ≤ 2,5 giây)", "Nén ảnh, giảm ảnh đầu trang", "khai", u)
                if x["cls"] > 0.1:
                    add("med", "Tốc độ", f"Bố cục nhảy CLS {x['cls']} (tốt: ≤ 0,1)", "Đặt kích thước ảnh, phông chữ", "khai", u)
            except Exception as ex:
                out["psi"].append({"url": u, "error": str(ex)[:120]})
    if configured():
        try:
            import hashlib
            import website
            sm = (website.SITE_DIR / "sitemap.xml").read_bytes() if (website.SITE_DIR / "sitemap.xml").exists() else b""
            h = hashlib.md5(sm).hexdigest()
            if sm and h != s().get("seo_sitemap_sent"):
                gsc_submit_sitemap()
                db.set_setting("seo_sitemap_sent", h)
                db.log("khai", "Gửi sitemap cho Google", "Sitemap đổi, đã gửi lại qua Search Console")
            urls = [re.sub(r"^https?://[^/]+", f"https://{d}", u) for u in re.findall(r"<loc>([^<]+)</loc>", sm.decode("utf-8", "ignore"))]
            seen = {r["url"]: r["inspected_at"] or "" for r in db.q("SELECT url, inspected_at FROM seo_pages")}
            for u in sorted(urls, key=lambda u: seen.get(u, ""))[:int(s().get("seo_inspect_per_day") or 8)]:
                x = gsc_inspect(u)
                db.run("INSERT OR REPLACE INTO seo_pages(url, verdict, coverage, last_crawl, inspected_at) VALUES (?,?,?,?,?)",
                       (u, x["verdict"], x["coverage"], x["last_crawl"], db.now()))
            rows = db.q("SELECT * FROM seo_pages")
            live = set(urls)
            rows = [r for r in rows if r["url"] in live]
            out["index"] = {"checked": len(rows), "indexed": sum(r["verdict"] == "PASS" for r in rows),
                            "not": [{"url": r["url"], "why": r["coverage"]} for r in rows if r["verdict"] != "PASS"][:10]}
            if out["index"]["not"]:
                add("med" if len(out["index"]["not"]) < 5 else "high", "Index",
                    f"{len(out['index']['not'])}/{len(rows)} trang chưa vào chỉ mục Google (VD {out['index']['not'][0]['why']})",
                    "Trang mới: chờ Google; “Đã thu thập, chưa lập chỉ mục”: làm nội dung dày hơn, thêm link nội bộ", "khai", out["index"]["not"][0]["url"])
        except GoogleError as ex:
            add("med", "Search Console", str(ex), "Xem thẻ Kết nối Google", "sep")
    return out


def run_audit(psi_run: bool = True) -> dict:
    import website
    _status("khai", "working", "Kiểm tra kỹ thuật website")
    try:
        issues = _local_audit()
        if any(i["area"] in ("Link hỏng", "Sitemap") for i in issues):
            website.build()  # tự sửa: dựng lại (link hỏng tự trỏ về trang danh sách, sitemap đúng trang)
            db.log("khai", "Tự sửa website", "Dựng lại website để sửa link hỏng / sitemap")
            issues = _local_audit()
        on = _online_audit(issues, psi_run)
        w = {"high": 15, "med": 5, "low": 1}
        score = max(0, 100 - sum(w[i["sev"]] for i in issues))
        db.run("INSERT INTO seo_audit(created_at, score, issues, psi, index_stats) VALUES (?,?,?,?,?)",
               (db.now(), score, json.dumps(issues, ensure_ascii=False), json.dumps(on["psi"], ensure_ascii=False), json.dumps(on["index"], ensure_ascii=False)))
        db.run("DELETE FROM seo_audit WHERE id NOT IN (SELECT id FROM seo_audit ORDER BY id DESC LIMIT 60)")
        db.set_setting("seo_last_audit", db.now())
        hi = [i for i in issues if i["sev"] == "high"]
        db.log("khai", "Kiểm tra kỹ thuật SEO", f"Sức khỏe {score}/100, {len(issues)} vấn đề" + (f" ({len(hi)} nặng: {hi[0]['msg'][:80]})" if hi else ""))
        return {"score": score, "issues": issues, **on}
    finally:
        _status("khai", "idle", "Sẵn sàng")


def last_audit() -> dict | None:
    r = db.one("SELECT * FROM seo_audit ORDER BY id DESC LIMIT 1")
    if not r:
        return None
    prev = db.one("SELECT score FROM seo_audit WHERE id<? ORDER BY id DESC LIMIT 1", (r["id"],))
    return {"at": r["created_at"], "score": r["score"], "prev": prev["score"] if prev else None, "issues": json.loads(r["issues"] or "[]"),
            "psi": json.loads(r["psi"] or "[]"), "index": json.loads(r["index_stats"] or "null")}


# ---------------------------------------------------------------- lịch + tổng quan
def _bg(name: str, fn, *a):
    if _busy[name]:
        return False

    def run():
        _busy[name] = True
        try:
            fn(*a)
        except Exception as ex:
            import errors
            errors.report_exc("website", f"Đội SEO ({name}) bị lỗi", ex, screen="website")
        finally:
            _busy[name] = False
    threading.Thread(target=run, daemon=True).start()
    return True


def tick(now):
    st = s()
    if st.get("seo_on", "1") != "1":
        return
    day, hm = now.strftime("%Y-%m-%d"), now.strftime("%H:%M")
    if hm >= (st.get("seo_audit_time") or "06:50") and (st.get("seo_last_audit") or "")[:10] != day:
        db.set_setting("seo_last_audit", now.strftime("%Y-%m-%d %H:%M:%S"))
        _bg("audit", run_audit, True)
    elif hm >= (st.get("seo_leader_time") or "07:50") and (st.get("seo_last_leader") or "")[:10] != day:
        db.set_setting("seo_last_leader", now.strftime("%Y-%m-%d %H:%M:%S"))

        def lead():
            run_leader()
            if str(now.isoweekday()) == (st.get("seo_report_weekday") or "1") and (s().get("seo_last_report") or "")[:10] != day:
                db.set_setting("seo_last_report", db.now())
                try:
                    import telegram_bot
                    telegram_bot.send(weekly_report())
                except Exception as ex:
                    print("[seo report]", ex)
        _bg("leader", lead)
    elif hm >= (st.get("seo_content_time") or "10:20") and (st.get("seo_last_content") or "")[:10] != day:
        db.set_setting("seo_last_content", now.strftime("%Y-%m-%d %H:%M:%S"))
        _bg("content", run_content)


def overview() -> dict:
    import website
    st = s()
    prods = website.site_products()
    seo = {r["product_id"]: r for r in db.q("SELECT product_id, keyword, title, meta, body, faq, status, score, note, updated_at FROM site_product_seo")}
    return {
        "google": {"email": sa_email(), "gsc_site": st.get("seo_gsc_site") or "", "ga4": st.get("seo_ga4_property") or "",
                   "psi_key_set": bool(st.get("seo_psi_key")), "ga_id": st.get("site_ga_id") or "", "configured": configured()},
        "busy": dict(_busy), "last": {k: st.get(f"seo_last_{k}") or "" for k in ("leader", "content", "audit", "report")},
        "summary": summary(), "opps": opportunities(12), "ranks": ranks()[:30], "kwmap": keyword_map(),
        "tasks": db.q("SELECT * FROM seo_tasks ORDER BY status='todo' DESC, id DESC LIMIT 20"),
        "products": [{"id": p["id"], "name": p["name"], **({k: v for k, v in seo[p["id"]].items() if k != "product_id"} if p["id"] in seo else {"status": "none"})}
                     for p in prods],
        "audit": last_audit(),
    }

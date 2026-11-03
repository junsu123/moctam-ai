"""Tìm hội nhóm mới trên Facebook theo chủ đề CEO chọn mỗi ngày.

Mỗi ngày:
1. CEO chọn vài chủ đề (từ khóa) để tìm nhóm: ưu tiên chủ đề từng mang về khách, xen kẽ chủ đề chưa thử,
   tránh chủ đề vừa tìm hôm trước. Sếp sửa được kho từ khóa và chủ đề của ngày.
2. Một sale lướt bảng tin Facebook một lúc, rồi tìm nhóm theo từng từ khóa (Facebook → Tìm kiếm → Nhóm), đọc kết quả:
   tên, link, số thành viên, công khai/riêng tư, số bài mỗi ngày, đã tham gia chưa.
3. Chấm điểm nhóm (đúng chủ đề, đông thành viên, hoạt động nhiều), tự thêm nhóm tốt vào danh sách Hội nhóm.
4. Mỗi nick xin vào một số nhóm mỗi ngày (có giới hạn), nhóm cần trả lời câu hỏi thì để sếp tự vào.
5. Khi xếp lịch đăng, Tuấn ưu tiên nhóm hợp chủ đề CEO chọn hôm nay. Nhóm tìm được chỉ nhận bài từ nick đã vào nhóm.
"""
import json
import math
import random
import re
import time
import unicodedata
from datetime import date, datetime, timedelta
from urllib.parse import quote

import db

DEFAULT_KEYWORDS = [
    "hội chạy quảng cáo facebook", "cộng đồng bán hàng online", "nguồn hàng sỉ thực phẩm", "livestream bán hàng",
    "bán hàng shopee tiktok shop", "nhập hàng tận xưởng", "mẹ bỉm sữa kinh doanh online", "kinh doanh online tại nhà",
    "sỉ trà túi lọc", "bột ngũ cốc dinh dưỡng", "đồ uống healthy", "cộng tác viên bán hàng online",
    "khởi nghiệp kinh doanh nhỏ", "chợ sỉ online", "thực phẩm sạch",
]
SKIP_SLUGS = {"feed", "discover", "joins", "create", "search", "notifications", "your_groups", "learning", "you",
              "categories", "join", "groups"}
STOP = {"hoi", "nhom", "cong", "dong", "group", "groups", "va", "cua", "tai", "online"}


def s() -> dict:
    return db.get_settings()


def _plain(t: str) -> str:
    t = unicodedata.normalize("NFD", (t or "").lower().replace("đ", "d"))
    return re.sub(r"[^a-z0-9 ]+", " ", "".join(c for c in t if unicodedata.category(c) != "Mn"))


def _tokens(t: str) -> list[str]:
    return [w for w in _plain(t).split() if w not in STOP and len(w) > 1]


# ---------------------------------------------------------------- CEO chọn chủ đề
def pool() -> list[str]:
    raw = s().get("group_keywords") or ""
    kws = [k.strip() for k in raw.splitlines() if k.strip()]
    return kws or DEFAULT_KEYWORDS


def keyword_stats() -> list[dict]:
    out = []
    for kw in pool():
        g = db.one("""SELECT COUNT(*) n, COALESCE(SUM(leads_count),0) leads FROM groups WHERE keyword=?""", (kw,))
        c = db.one("""SELECT COUNT(*) n, MAX(found_at) last FROM group_candidates WHERE keyword=?""", (kw,))
        last = db.one("SELECT MAX(searched_at) d FROM group_searches WHERE keyword=?", (kw,))["d"]
        out.append({"keyword": kw, "groups": g["n"], "leads": g["leads"], "found": c["n"], "last_searched": last})
    return out


def today_keywords(force: bool = False) -> list[str]:
    """Chủ đề tìm nhóm hôm nay do CEO chọn (giữ nguyên trong ngày, sếp sửa được)."""
    st = s()
    try:
        cur = json.loads(st.get("ceo_kw_today") or "{}")
    except Exception:
        cur = {}
    if cur.get("date") == db.today() and cur.get("keywords") and not force:
        return cur["keywords"]
    n = max(1, min(6, int(st.get("discover_keywords_per_day") or 3)))
    recent = (date.today() - timedelta(days=2)).isoformat()
    scored = []
    for k in keyword_stats():
        sc = k["leads"] * 5 + k["groups"] * 0.5 + random.random() * 2
        if not k["last_searched"]:
            sc += 3          # chưa tìm lần nào: thử
        elif k["last_searched"][:10] >= recent:
            sc -= 4          # vừa tìm gần đây: để dành
        scored.append((sc, k["keyword"]))
    pick = [k for _, k in sorted(scored, reverse=True)[:n]]
    db.set_setting("ceo_kw_today", json.dumps({"date": db.today(), "keywords": pick, "by": "ceo"}, ensure_ascii=False))
    best = max(keyword_stats(), key=lambda k: k["leads"], default=None)
    why = f" Chủ đề mang về nhiều khách nhất: “{best['keyword']}” ({best['leads']} khách)." if best and best["leads"] else ""
    db.log("ceo", "Chọn chủ đề tìm nhóm hôm nay", "; ".join(pick) + "." + why)
    return pick


def set_today(keywords: list[str]):
    kws = [k.strip() for k in keywords if k.strip()][:6]
    db.set_setting("ceo_kw_today", json.dumps({"date": db.today(), "keywords": kws, "by": "boss"}, ensure_ascii=False))
    db.log("ceo", "Sếp đổi chủ đề tìm nhóm hôm nay", "; ".join(kws))


def matches_today(g: dict) -> bool:
    """Nhóm hợp chủ đề CEO chọn hôm nay (để Tuấn ưu tiên khi xếp lịch đăng)."""
    try:
        kws = json.loads(s().get("ceo_kw_today") or "{}")
        if kws.get("date") != db.today():
            return False
        kws = kws.get("keywords") or []
    except Exception:
        return False
    if g.get("keyword") in kws:
        return True
    text = set(_tokens(f"{g.get('name', '')} {g.get('topic', '')}"))
    return any(len(set(_tokens(k)) & text) >= max(1, len(_tokens(k)) // 2) for k in kws)


# ---------------------------------------------------------------- đọc kết quả tìm kiếm
def parse_count(t: str) -> int:
    t = (t or "").strip().lower()
    m = re.match(r"([\d.,]+)\s*(k|n|nghìn|ngàn|triệu|tr|m)?", t)
    if not m:
        return 0
    num, unit = m.group(1), m.group(2)
    if unit:
        v = float(num.replace(",", "."))
        return int(v * (1_000_000 if unit in ("triệu", "tr", "m") else 1000))
    return int(re.sub(r"[.,]", "", num) or 0)


def parse_meta(meta: str) -> dict:
    m = meta or ""
    mem = re.search(r"([\d.,]+\s*(?:K|N|nghìn|ngàn|triệu|Tr|M)?)\s*(?:thành viên|members?)", m, re.I)
    ppd = re.search(r"([\d.,]+)\+?\s*(?:bài viết|posts?)\s*(mỗi ngày|/\s*ngày|một ngày|a day|per day|mỗi tuần|/\s*tuần|a week)", m, re.I)
    posts = 0.0
    if ppd:
        posts = float(ppd.group(1).replace(",", "."))
        if "tuần" in ppd.group(2) or "week" in ppd.group(2):
            posts = round(posts / 7, 1)
    privacy = "public" if re.search(r"Công khai|Public", m, re.I) else "private" if re.search(r"Riêng tư|Private", m, re.I) else ""
    joined = bool(re.search(r"Đã tham gia|\bJoined\b|Truy cập|\bVisit\b", m, re.I))
    return {"members": parse_count(mem.group(1)) if mem else 0, "posts_per_day": posts, "privacy": privacy, "joined": joined}


def score(c: dict, keyword: str) -> tuple[float, float]:
    kt = _tokens(keyword)
    nt = set(_tokens(c["name"]))
    rel = (sum(1 for w in kt if w in nt) / len(kt)) if kt else 0
    sc = rel * 50 + min(math.log10((c.get("members") or 0) + 1), 6) * 7 + min(c.get("posts_per_day") or 0, 30) * 0.8
    sc += 5 if c.get("privacy") == "public" else 0
    return round(sc, 1), rel


EXTRACT_JS = r"""(skip) => {
  const out = {};
  for (const a of document.querySelectorAll('a[href*="/groups/"]')) {
    const m = a.href.match(/\/groups\/([^/?#]+)/); if (!m) continue;
    const slug = decodeURIComponent(m[1]); if (skip.includes(slug.toLowerCase())) continue;
    const name = (a.innerText || '').trim().split('\n')[0];
    if (!name || name.length < 3) continue;
    let el = a, meta = '';
    for (let i = 0; i < 9 && el; i++) { el = el.parentElement; if (!el) break;
      const t = el.innerText || ''; if (/thành viên|members/i.test(t)) { meta = t; break; } }
    if (!out[slug] || out[slug].name.length < name.length) out[slug] = {slug, name, meta: meta.slice(0, 500)};
  }
  return Object.values(out);
}"""


def save_results(rows: list[dict], keyword: str, sale_id: int, base: str) -> int:
    """Lưu nhóm tìm được (bỏ nhóm đã có trong danh sách). Trả về số nhóm mới."""
    import browser_poster
    new = 0
    known = {(g["url"] or "").rstrip("/").lower() for g in db.q("SELECT url FROM groups")}
    for r in rows:
        url = f"{base}/groups/{r['slug']}"
        canon, err = browser_poster.check_group_url(url)
        if err:
            continue
        info = parse_meta(r.get("meta", ""))
        c = {"name": r["name"][:150], **info}
        sc, rel = score(c, keyword)
        if canon.rstrip("/").lower() in known:
            continue
        old = db.one("SELECT id FROM group_candidates WHERE url=?", (canon,))
        if old:
            db.run("""UPDATE group_candidates SET members=?, posts_per_day=?, privacy=?, joined=?, score=MAX(score, ?),
                      last_seen_at=? WHERE id=?""", (c["members"], c["posts_per_day"], c["privacy"], int(c["joined"]), sc,
                                                     db.now(), old["id"]))
            continue
        db.run("""INSERT INTO group_candidates(url, name, members, posts_per_day, privacy, joined, keyword, relevance, score,
                  found_by, status, found_at, last_seen_at) VALUES (?,?,?,?,?,?,?,?,?,?,'new',?,?)""",
               (canon, c["name"], c["members"], c["posts_per_day"], c["privacy"], int(c["joined"]), keyword, rel, sc,
                sale_id, db.now(), db.now()))
        new += 1
    db.run("INSERT INTO group_searches(keyword, sale_id, results, new, searched_at) VALUES (?,?,?,?,?)",
           (keyword, sale_id, len(rows), new, db.now()))
    return new


def add_candidate(cid: int, by: str = "ceo", joined_sale: int | None = None) -> dict | None:
    c = db.one("SELECT * FROM group_candidates WHERE id=?", (cid,))
    if not c or c["status"] == "added":
        return None
    gid = db.run("""INSERT INTO groups(name, url, topic, members, rules, min_days_between_posts, note, created_at, source,
                    keyword, privacy, posts_per_day, score, member_sale_ids) VALUES (?,?,?,?,?,?,?,?,'search',?,?,?,?,?)""",
                 (c["name"], c["url"], c["keyword"], c["members"], "", 3,
                  f"Sale tìm thấy khi tìm “{c['keyword']}”", db.now(), c["keyword"], c["privacy"], c["posts_per_day"],
                  c["score"], str(joined_sale) if joined_sale else ""))
    db.run("UPDATE group_candidates SET status='added', group_id=? WHERE id=?", (gid, cid))
    if joined_sale:
        db.run("INSERT OR REPLACE INTO group_joins(group_id, sale_id, status, requested_at, updated_at) VALUES (?,?,?,?,?)",
               (gid, joined_sale, "joined", db.now(), db.now()))
    db.log("tuan" if by == "ceo" else "minh", "Thêm nhóm mới tìm được",
           f"{c['name']} ({c['members']:,} thành viên, chủ đề “{c['keyword']}”)".replace(",", "."))
    return db.one("SELECT * FROM groups WHERE id=?", (gid,))


def auto_add(limit: int | None = None) -> list[dict]:
    """Thêm các nhóm tốt nhất vào danh sách Hội nhóm (đúng chủ đề, đủ đông)."""
    limit = int(s().get("discover_add_per_day") or 5) if limit is None else limit
    today_added = db.one("SELECT COUNT(*) n FROM groups WHERE source='search' AND created_at LIKE ?", (db.today() + "%",))["n"]
    room = max(0, limit - today_added)
    out = []
    for c in db.q("""SELECT * FROM group_candidates WHERE status='new' AND relevance > 0 AND members >= 1000
                     ORDER BY score DESC LIMIT ?""", (room,)):
        g = add_candidate(c["id"], joined_sale=c["found_by"] if c["joined"] else None)
        if g:
            out.append(g)
    return out


def set_join(group_id: int, sale_id: int, status: str, note: str = ""):
    db.run("""INSERT INTO group_joins(group_id, sale_id, status, note, requested_at, updated_at) VALUES (?,?,?,?,?,?)
              ON CONFLICT(group_id, sale_id) DO UPDATE SET status=excluded.status, note=excluded.note,
              updated_at=excluded.updated_at""", (group_id, sale_id, status, note[:200], db.now(), db.now()))
    g = db.one("SELECT member_sale_ids FROM groups WHERE id=?", (group_id,))
    if not g:
        return
    mem = [int(x) for x in (g["member_sale_ids"] or "").split(",") if x.strip().isdigit()]
    if status == "joined" and sale_id not in mem:
        mem.append(sale_id)
    if status != "joined" and sale_id in mem:
        mem.remove(sale_id)
    db.run("UPDATE groups SET member_sale_ids=? WHERE id=?", (",".join(map(str, mem)), group_id))


def mark_not_member(group_id: int, sale_id: int):
    """Đăng bài báo nick chưa vào nhóm: cập nhật để Tuấn không xếp bài nick này vào nhóm đó nữa."""
    if group_id and sale_id:
        set_join(group_id, sale_id, "none", "Đăng bài báo nick chưa là thành viên")


def joins_today(sale_id: int) -> int:
    return db.one("""SELECT COUNT(*) n FROM group_joins WHERE sale_id=? AND requested_at LIKE ?
                     AND status IN ('requested','joined','needs_answers')""", (sale_id, db.today() + "%"))["n"]


# ---------------------------------------------------------------- việc của sale trên trình duyệt
def _browse(page, minutes: float):
    """Lướt bảng tin một lúc trước khi làm việc (chỉ xem, không bấm thích, không bình luận)."""
    import browser_poster as B
    if minutes <= 0:
        return
    page.goto(B.FB_BASE, wait_until="domcontentloaded", timeout=60000)
    page.wait_for_timeout(3000)
    B._check_blocked(page)
    end = time.time() + minutes * 60
    while time.time() < end:
        page.mouse.wheel(0, random.randint(500, 1100))
        page.wait_for_timeout(int(random.uniform(2.5, 7) * 1000))


def _search(page, keyword: str, sale_id: int) -> int:
    import browser_poster as B
    page.goto(f"{B.FB_BASE}/search/groups/?q={quote(keyword)}", wait_until="domcontentloaded", timeout=60000)
    page.wait_for_timeout(4000)
    B._check_blocked(page)
    for _ in range(4):  # cuộn để tải thêm kết quả
        page.mouse.wheel(0, 1600)
        page.wait_for_timeout(int(random.uniform(1.8, 3.5) * 1000))
    rows = page.evaluate(EXTRACT_JS, sorted(SKIP_SLUGS))
    base = B.FB_BASE if not B.FB_BASE.startswith("https://www.facebook.com") else "https://www.facebook.com"
    return save_results(rows, keyword, sale_id, base)


def _is_member(page) -> bool:
    import browser_poster as B
    return bool(B._visible_first(page, B.selectors()["group_composer"]))


def _join_one(page, g: dict, sale_id: int) -> str:
    import browser_poster as B
    sel = B.selectors()
    page.goto(B.fb_url(g["url"]), wait_until="domcontentloaded", timeout=60000)
    page.wait_for_timeout(3500)
    B._check_blocked(page)
    if _is_member(page):
        set_join(g["id"], sale_id, "joined")
        return "joined"
    if B._visible_first(page, sel.get("pending_join", [])):
        set_join(g["id"], sale_id, "requested")
        return "requested"
    btn = B._visible_first(page, sel.get("join_button", []))
    if not btn:
        set_join(g["id"], sale_id, "failed", "Không thấy nút Tham gia nhóm. Nút đang thấy: " + B._labels_on(page))
        return "failed"
    btn.click()
    page.wait_for_timeout(3500)
    dlg = B._top_dialog(page)
    if dlg and re.search(r"câu hỏi|trả lời|answer|question|nội quy|rules", dlg.inner_text(), re.I):
        # nhóm bắt trả lời câu hỏi: sale không tự trả lời thay sếp
        page.keyboard.press("Escape")
        page.wait_for_timeout(1000)
        set_join(g["id"], sale_id, "needs_answers", "Nhóm yêu cầu trả lời câu hỏi khi xin vào")
        return "needs_answers"
    if _is_member(page):
        set_join(g["id"], sale_id, "joined")
        return "joined"
    set_join(g["id"], sale_id, "requested")
    return "requested"


def _join_some(page, sale_id: int) -> dict:
    """Kiểm tra các yêu cầu đang chờ, rồi xin vào thêm nhóm mới (trong giới hạn mỗi ngày)."""
    import browser_poster as B
    res = {"joined": 0, "requested": 0, "needs_answers": 0, "failed": 0, "checked": 0}
    for g in db.q("""SELECT g.* FROM group_joins j JOIN groups g ON g.id=j.group_id WHERE j.sale_id=? AND j.status='requested'
                     ORDER BY j.updated_at LIMIT 3""", (sale_id,)):
        page.goto(B.fb_url(g["url"]), wait_until="domcontentloaded", timeout=60000)
        page.wait_for_timeout(3000)
        B._check_blocked(page)
        res["checked"] += 1
        if _is_member(page):
            set_join(g["id"], sale_id, "joined")
            res["joined"] += 1
        B._pause(page, 3, 7)
    if s().get("join_enabled", "1") != "1":
        return res
    cap = max(0, int(s().get("join_per_nick_day") or 2) - joins_today(sale_id))
    for g in db.q("""SELECT * FROM groups g WHERE source='search' AND COALESCE(url,'')!='' AND NOT EXISTS
                     (SELECT 1 FROM group_joins j WHERE j.group_id=g.id AND j.sale_id=?)
                     ORDER BY score DESC, members DESC LIMIT ?""", (sale_id, cap)):
        st = _join_one(page, g, sale_id)
        res[st] = res.get(st, 0) + 1
        B._pause(page, 8, 20)  # giãn cách giữa các lần xin vào nhóm
    return res


def job_discover(pw, sale_id: int, keywords: list[str]):
    import browser_poster as B
    import workflows
    aid = f"sale-{sale_id}"
    ctx, page = B._open(pw, sale_id)
    found, added, jr = 0, [], {}
    try:
        if not B._logged_in(ctx):
            B._set_login(sale_id, "not_logged_in", "Phiên đăng nhập đã hết, cần đăng nhập lại")
            raise RuntimeError("Nick chưa đăng nhập. Vào Nhân viên sale → Mở Chrome để đăng nhập lại")
        workflows.set_status(aid, "working", "Đang lướt Facebook")
        _browse(page, float(s().get("browse_minutes") or 2))
        for kw in keywords:
            workflows.set_status(aid, "working", f"Đang tìm nhóm: {kw}")
            found += _search(page, kw, sale_id)
            B._pause(page, 5, 12)
        added = auto_add()
        if added or db.one("SELECT 1 x FROM groups WHERE source='search' LIMIT 1"):
            workflows.set_status(aid, "working", "Đang xin vào nhóm mới")
            jr = _join_some(page, sale_id)
        db.set_setting("discover_last_result", json.dumps({"at": db.now(), "sale_id": sale_id, "keywords": keywords,
                                                           "found": found, "added": len(added), "joins": jr}, ensure_ascii=False))
        db.log(aid, "Tìm nhóm mới", f"Tìm “{'”, “'.join(keywords)}”: {found} nhóm mới, thêm {len(added)} nhóm vào danh sách"
               + (f", xin vào {jr.get('requested', 0) + jr.get('joined', 0)} nhóm" if jr else ""))
    except B.Blocked as e:
        B._block(sale_id, str(e))
    finally:
        try:
            ctx.close()
        except Exception:
            pass
        workflows.set_status(aid, "idle", f"Tìm được {found} nhóm mới")


def job_join(pw, sale_id: int):
    import browser_poster as B
    import workflows
    aid = f"sale-{sale_id}"
    ctx, page = B._open(pw, sale_id)
    try:
        if not B._logged_in(ctx):
            raise RuntimeError("Nick chưa đăng nhập. Vào Nhân viên sale → Mở Chrome để đăng nhập lại")
        workflows.set_status(aid, "working", "Đang xin vào nhóm mới")
        jr = _join_some(page, sale_id)
        if any(jr.values()):
            db.log(aid, "Xin vào nhóm", f"Vào được {jr['joined']} nhóm, chờ duyệt {jr['requested']}, "
                   f"cần sếp trả lời câu hỏi {jr['needs_answers']}")
    except B.Blocked as e:
        B._block(sale_id, str(e))
    finally:
        try:
            ctx.close()
        except Exception:
            pass
        workflows.set_status(aid, "idle", "Chờ việc tiếp theo")


# ---------------------------------------------------------------- lịch hằng ngày
def _working_sales() -> list[dict]:
    return db.q("""SELECT * FROM sales WHERE COALESCE(status,'active')='active' AND COALESCE(is_sample,0)=0
                   AND login_status='ok' AND auto_post=1 ORDER BY id""")


def start_discover(sale_id: int | None = None, keywords: list[str] | None = None) -> dict:
    import browser_poster as B
    sales = _working_sales()
    if not sales:
        raise ValueError("Chưa có nick sale nào đăng nhập và đang bật tự đăng")
    if sale_id is None:  # luân phiên nick đi tìm nhóm
        last = int(s().get("discover_last_sale") or 0)
        nxt = [x for x in sales if x["id"] > last] or sales
        sale_id = nxt[0]["id"]
    kws = keywords or today_keywords()
    db.set_setting("discover_last_sale", str(sale_id))
    B.submit(sale_id, {"kind": "discover", "keywords": kws})
    return {"sale_id": sale_id, "keywords": kws}


def tick(now: datetime):
    """Gọi từ lịch tự động mỗi 30 giây."""
    st = s()
    hm = now.strftime("%H:%M")
    if st.get("discover_enabled", "1") != "1":
        return
    t = st.get("discover_time") or "10:30"
    if hm >= t and st.get("discover_last") != db.today():
        db.set_setting("discover_last", db.today())
        try:
            start_discover()
        except ValueError:
            pass
    # 45 phút sau: các nick khác xin vào nhóm mới được thêm
    later = (datetime.strptime(t, "%H:%M") + timedelta(minutes=45)).strftime("%H:%M")
    if st.get("join_enabled", "1") == "1" and hm >= later and st.get("join_last") != db.today():
        db.set_setting("join_last", db.today())
        import browser_poster as B
        for x in _working_sales():
            if joins_today(x["id"]) < int(st.get("join_per_nick_day") or 2) and not B.busy(x["id"]):
                B.submit(x["id"], {"kind": "join"})


def overview() -> dict:
    cand = db.q("""SELECT * FROM group_candidates WHERE status='new' ORDER BY score DESC LIMIT 60""")
    st = s()
    try:
        today = json.loads(st.get("ceo_kw_today") or "{}")
    except Exception:
        today = {}
    return {"today": today_keywords() if (today.get("date") != db.today()) else today.get("keywords"),
            "today_by": today.get("by", "ceo"), "pool": pool(), "stats": keyword_stats(), "candidates": cand,
            "last": json.loads(st.get("discover_last_result") or "{}"),
            "settings": {k: st.get(k) for k in ("discover_enabled", "discover_time", "discover_keywords_per_day",
                                                 "discover_add_per_day", "join_enabled", "join_per_nick_day", "browse_minutes")},
            "pending_answers": db.q("""SELECT g.id, g.name, g.url, s.name sale FROM group_joins j JOIN groups g ON g.id=j.group_id
                                       JOIN sales s ON s.id=j.sale_id WHERE j.status='needs_answers'""")}

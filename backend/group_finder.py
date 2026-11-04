"""Tìm hội nhóm mới trên Facebook theo chủ đề CEO chọn mỗi ngày.

Mỗi ngày:
1. CEO chọn vài chủ đề (từ khóa) để tìm nhóm: ưu tiên chủ đề từng mang về khách, xen kẽ chủ đề chưa thử,
   tránh chủ đề vừa tìm hôm trước. Sếp sửa được kho từ khóa và chủ đề của ngày.
2. Một sale lướt bảng tin Facebook một lúc, rồi tìm nhóm theo từng từ khóa (Facebook → Tìm kiếm → Nhóm), đọc kết quả:
   tên, link, số thành viên, công khai/riêng tư, số bài mỗi ngày, đã tham gia chưa.
3. Sale khảo sát các nhóm hứa hẹn nhất: mở trang Giới thiệu và bảng tin của nhóm, đọc chỉ số tương tác
   (bài mới/ngày, thành viên mới/tuần, cảm xúc và bình luận mỗi bài, bài mới nhất, luật nhóm) rồi báo cáo.
4. Tuấn đánh giá từng nhóm theo chuẩn nhóm tương tác cao (group_review.py): Nên vào / Cân nhắc / Bỏ qua.
   Chỉ nhóm "Nên vào" được tự thêm vào danh sách Hội nhóm.
5. Mỗi nick xin vào một số nhóm mỗi ngày (có giới hạn), nhóm điểm tương tác cao xin trước; nhóm cần trả lời câu hỏi
   thì để sếp tự vào. Vào được nhóm riêng tư thì sale đọc bài trong nhóm để Tuấn đánh giá lại.
6. Khi xếp lịch đăng, Tuấn ưu tiên nhóm hợp chủ đề CEO chọn hôm nay, rồi nhóm tương tác cao. Nhóm tìm được chỉ nhận bài từ nick đã vào nhóm.
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
    recent = (db.clock().date() - timedelta(days=2)).isoformat()
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


def save_results(rows: list[dict], keyword: str, aid: int, base: str) -> int:
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
                aid, db.now(), db.now()))
        new += 1
    import accounts
    db.run("INSERT INTO group_searches(keyword, sale_id, results, new, searched_at) VALUES (?,?,?,?,?)",
           (keyword, (accounts.get(aid) or {}).get("sale_id"), len(rows), new, db.now()))
    return new


def add_candidate(cid: int, by: str = "ceo", joined_account: int | None = None) -> dict | None:
    c = db.one("SELECT * FROM group_candidates WHERE id=?", (cid,))
    if not c or c["status"] == "added":
        return None
    gid = db.run("""INSERT INTO groups(name, url, topic, members, rules, min_days_between_posts, note, created_at, source,
                    keyword, privacy, posts_per_day, score, member_account_ids) VALUES (?,?,?,?,?,?,?,?,'search',?,?,?,?,?)""",
                 (c["name"], c["url"], c["keyword"], c["members"], c.get("rules_note") or "", 3,
                  f"Sale tìm thấy khi tìm “{c['keyword']}”", db.now(), c["keyword"], c["privacy"], c["posts_per_day"],
                  c["score"], str(joined_account) if joined_account else ""))
    cols = [k for k in METRIC_COLS if k not in ("members", "posts_per_day", "privacy")] + ["eng_score", "verdict", "review_note", "reviewed_at"]
    db.run(f"UPDATE groups SET {', '.join(k + '=?' for k in cols)} WHERE id=?", (*[c.get(k) for k in cols], gid))
    if by == "boss" and c.get("verdict") and c["verdict"] != "join":  # sếp vẫn chọn thêm: nick sẽ xin vào nhóm này
        db.run("UPDATE groups SET verdict='join', review_note=? WHERE id=?",
               (f"Sếp chọn thêm (Tuấn: {c.get('review_note') or ''})"[:600], gid))
    db.run("UPDATE group_candidates SET status='added', group_id=? WHERE id=?", (gid, cid))
    if joined_account:
        db.run("INSERT OR REPLACE INTO account_groups(group_id, account_id, status, requested_at, updated_at) VALUES (?,?,?,?,?)",
               (gid, joined_account, "joined", db.now(), db.now()))
    mem = f"{c['members'] or 0:,}".replace(",", ".")
    sc = f", {c['eng_score']:g} điểm tương tác".replace(".", ",") if c.get("eng_score") is not None else ""
    db.log("tuan" if by == "ceo" else "minh", "Thêm nhóm mới tìm được", f"{c['name']} ({mem} thành viên{sc}, chủ đề “{c['keyword']}”)")
    return db.one("SELECT * FROM groups WHERE id=?", (gid,))


def auto_add(limit: int | None = None) -> list[dict]:
    """Thêm vào danh sách Hội nhóm các nhóm Tuấn kết luận "Nên vào", điểm tương tác cao trước."""
    limit = int(s().get("discover_add_per_day") or 5) if limit is None else limit
    today_added = db.one("SELECT COUNT(*) n FROM groups WHERE source='search' AND created_at LIKE ?", (db.today() + "%",))["n"]
    room = max(0, limit - today_added)
    out = []
    for c in db.q("""SELECT * FROM group_candidates WHERE status='new' AND verdict='join'
                     ORDER BY eng_score DESC LIMIT ?""", (room,)):
        g = add_candidate(c["id"], joined_account=c["found_by"] if c["joined"] else None)
        if g:
            out.append(g)
    return out


def set_join(group_id: int, aid: int, status: str, note: str = ""):
    """Trạng thái xin vào nhóm của một nick; nick đã vào thì được Tuấn xếp bài vào nhóm đó."""
    db.run("""INSERT INTO account_groups(group_id, account_id, status, note, requested_at, updated_at) VALUES (?,?,?,?,?,?)
              ON CONFLICT(group_id, account_id) DO UPDATE SET status=excluded.status, note=excluded.note,
              updated_at=excluded.updated_at""", (group_id, aid, status, note[:200], db.now(), db.now()))
    g = db.one("SELECT member_account_ids FROM groups WHERE id=?", (group_id,))
    if not g:
        return
    mem = [int(x) for x in (g["member_account_ids"] or "").split(",") if x.strip().isdigit()]
    if status == "joined" and aid not in mem:
        mem.append(aid)
    if status != "joined" and aid in mem:
        mem.remove(aid)
    db.run("UPDATE groups SET member_account_ids=? WHERE id=?", (",".join(map(str, mem)), group_id))


def mark_not_member(group_id: int, aid: int):
    """Đăng bài báo nick chưa vào nhóm: cập nhật để Tuấn không xếp bài nick này vào nhóm đó nữa."""
    if group_id and aid:
        set_join(group_id, aid, "none", "Đăng bài báo nick chưa là thành viên")


def joins_today(aid: int) -> int:
    return db.one("""SELECT COUNT(*) n FROM account_groups WHERE account_id=? AND requested_at LIKE ?
                     AND status IN ('requested','joined','needs_answers')""", (aid, db.today() + "%"))["n"]


# ---------------------------------------------------------------- khảo sát chỉ số tương tác của nhóm
METRIC_COLS = ("members", "posts_per_day", "posts_today", "posts_month", "new_members_week", "avg_reactions", "avg_comments",
               "sampled_posts", "last_post_hours", "selling_ratio", "no_selling", "rules_note", "privacy", "scouted_at")
NUM = r"([\d.,]+\s*(?:K|N|k|nghìn|ngàn|triệu|Tr|M)?)"
NO_SELL_RX = re.compile(r"(không|cấm|nghiêm cấm|ko|no|không được|không cho phép)\s+(?:đăng\s+)?(?:bài\s+)?(quảng cáo|bán hàng|"
                        r"rao vặt|rao bán|pr\b|seeding|spam bán|self[- ]?promotion|advertis|selling|sales)", re.I)
SELL_RX = re.compile(r"(giá sỉ|giá lẻ|\bgiá\b|inbox|\bib\b|liên hệ|zalo|ship cod|freeship|order|\bsỉ\b|bán\b|xả kho|"
                     r"\d{2,4}\s?k\b|\d{1,3}(?:\.\d{3})+\s?(?:đ|vnd)|0\d{9})", re.I)


def parse_about(text: str) -> dict:
    """Đọc chỉ số ở trang Giới thiệu của nhóm (tiếng Việt và tiếng Anh)."""
    t = text or ""
    out = {}
    m = re.search(NUM + r"\s*bài viết mới hôm nay", t, re.I) or re.search(NUM + r"\s*new posts? today", t, re.I)
    if m:
        out["posts_today"] = parse_count(m.group(1))
    m = (re.search(NUM + r"\s*bài viết trong (?:tháng trước|30 ngày qua|tháng qua)", t, re.I)
         or re.search(NUM + r"\s*posts? in the last month", t, re.I))
    if m:
        out["posts_month"] = parse_count(m.group(1))
    m = (re.search(r"Tổng cộng\s*" + NUM + r"\s*thành viên", t, re.I) or re.search(NUM + r"\s*total members", t, re.I)
         or re.search(NUM + r"\s*(?:thành viên|members)", t, re.I))
    if m:
        out["members"] = parse_count(m.group(1))
    m = (re.search(r"\+\s*" + NUM + r"\s*(?:thành viên\s*)?(?:mới\s*)?(?:trong|in the)\s*(?:tuần trước|tuần qua|7 ngày qua|last week)", t, re.I)
         or re.search(NUM + r"\s*thành viên mới\s*(?:trong\s*)?(?:tuần trước|tuần qua|7 ngày qua)", t, re.I))
    if m:
        out["new_members_week"] = parse_count(m.group(1))
    if re.search(r"\bCông khai\b|\bPublic\b", t):
        out["privacy"] = "public"
    elif re.search(r"\bRiêng tư\b|\bPrivate\b", t):
        out["privacy"] = "private"
    ban = NO_SELL_RX.search(t)
    out["no_selling"] = 1 if ban else 0
    if ban:
        head = t[max(0, ban.start() - 120):ban.start()]
        cut = max(head.rfind(x) for x in (".", ":", "\n", "·"))
        a = ban.start() - len(head) + cut + 1 if cut >= 0 else max(0, ban.start() - 40)
        out["rules_note"] = re.sub(r"\s+", " ", t[a:ban.end() + 60]).strip()[:200]
    return out


def post_age_hours(t: str) -> float | None:
    t = t or ""
    if re.search(r"Vừa xong|Just now", t, re.I):
        return 0.0
    if re.search(r"\bHôm qua\b|\bYesterday\b", t, re.I):
        return 24.0
    m = re.search(r"(?<![\d.,])(\d{1,3})\s*(phút|giờ|ngày|tuần|tháng|năm|mins?|m|hrs?|hours?|h|days?|d|weeks?|w|y)\b", t, re.I)
    if not m:
        return None
    v, u = int(m.group(1)), m.group(2).lower()
    if u in ("phút", "m", "min", "mins"):
        return v / 60
    if u in ("giờ", "h", "hr", "hrs", "hour", "hours"):
        return float(v)
    if u in ("ngày", "d", "day", "days"):
        return v * 24.0
    if u in ("tuần", "w", "week", "weeks"):
        return v * 168.0
    if u == "tháng":
        return v * 720.0
    return v * 8760.0


def parse_post(t: str) -> dict:
    """Chỉ số một bài trên bảng tin nhóm: cảm xúc, bình luận, tuổi bài, có phải bài rao bán không."""
    t = t or ""
    m = re.search(r"(?:Tất cả cảm xúc|All reactions)\s*:?\s*" + NUM, t, re.I)
    r = parse_count(m.group(1)) if m else 0
    if not m:
        m = re.search(r"và\s*" + NUM + r"\s*người khác|and\s*" + NUM + r"\s*others", t, re.I)
        if m:
            r = parse_count(m.group(1) or m.group(2)) + 1
    m = re.search(NUM + r"\s*(?:bình luận|comments?)\b", t, re.I)
    c = parse_count(m.group(1)) if m else 0
    return {"reactions": r, "comments": c, "age": post_age_hours(t[:300]), "selling": len(SELL_RX.findall(t[:1500])) >= 2}


FEED_JS = r"""() => {
  const arts = [...document.querySelectorAll('[role="article"]')].filter(a => !a.parentElement.closest('[role="article"]'));
  return arts.slice(0, 12).map(a => {
    const labels = [...a.querySelectorAll('[aria-label]')].map(x => x.getAttribute('aria-label')).filter(Boolean).join(' · ');
    return ((a.innerText || '') + ' · ' + labels).slice(0, 2500);
  });
}"""


def read_feed(page, scrolls: int = 3) -> dict:
    """Đọc vài bài mới trên bảng tin nhóm (chỉ đọc, không bấm gì)."""
    for _ in range(scrolls):
        page.mouse.wheel(0, random.randint(900, 1500))
        page.wait_for_timeout(int(random.uniform(1.5, 3) * 1000))
    posts = [parse_post(t) for t in page.evaluate(FEED_JS)]
    posts = [p for p in posts if p["reactions"] or p["comments"] or p["age"] is not None]
    if not posts:
        return {"sampled_posts": 0}
    ages = [p["age"] for p in posts if p["age"] is not None]
    return {"sampled_posts": len(posts),
            "avg_reactions": round(sum(p["reactions"] for p in posts) / len(posts), 1),
            "avg_comments": round(sum(p["comments"] for p in posts) / len(posts), 1),
            "last_post_hours": round(min(ages), 1) if ages else None,
            "selling_ratio": round(sum(p["selling"] for p in posts) / len(posts), 2)}


def _about_url(url: str) -> str:
    import browser_poster as B
    return B.fb_url(url).rstrip("/") + "/about"


def scout(page, url: str) -> dict:
    """Sale mở trang Giới thiệu và bảng tin của nhóm, đọc chỉ số tương tác."""
    import browser_poster as B
    page.goto(_about_url(url), wait_until="domcontentloaded", timeout=60000)
    page.wait_for_timeout(int(random.uniform(3, 5) * 1000))
    B._check_blocked(page)
    m = parse_about(page.inner_text("body"))
    B._pause(page, 2, 5)
    page.goto(B.fb_url(url), wait_until="domcontentloaded", timeout=60000)
    page.wait_for_timeout(int(random.uniform(3, 5) * 1000))
    B._check_blocked(page)
    m.update(read_feed(page))
    m["scouted_at"] = db.now()
    return m


def _save_metrics(table: str, row_id: int, m: dict):
    cols = [k for k in METRIC_COLS if k in m and m[k] is not None]
    if cols:
        db.run(f"UPDATE {table} SET {', '.join(k + '=?' for k in cols)} WHERE id=?", (*[m[k] for k in cols], row_id))


def _scout_some(page, aid: int, sale_label: str) -> list[dict]:
    """Khảo sát các nhóm hứa hẹn nhất chưa khảo sát, rồi báo cáo cho Tuấn."""
    import browser_poster as B
    import workflows
    n = max(0, int(s().get("scout_per_run") or 6))
    minm = int(s().get("review_min_members") or 1000)
    rows = db.q("""SELECT * FROM group_candidates WHERE status='new' AND scouted_at IS NULL AND relevance > 0
                   AND (members >= ? OR members = 0) ORDER BY score DESC LIMIT ?""", (minm, n))
    done = []
    # nhóm đã biết chắc không đạt từ kết quả tìm kiếm (quá ít thành viên, sai chủ đề): Tuấn loại luôn, không cần mở xem
    for c in db.q("""SELECT * FROM group_candidates WHERE status='new' AND scouted_at IS NULL AND reviewed_at IS NULL
                     AND (relevance <= 0 OR (members > 0 AND members < ?))""", (minm,)):
        done.append({**c, "_prefilter": True})
    for c in rows:
        workflows.set_status(f"sale-{(db.one('SELECT sale_id FROM fb_accounts WHERE id=?', (aid,)) or {}).get('sale_id')}",
                             "working", f"Đang xem nhóm: {c['name'][:40]}")
        try:
            m = scout(page, c["url"])
        except B.Blocked:
            raise
        except Exception as e:
            print("[scout]", c["url"], e)
            m = {"scouted_at": db.now(), "sampled_posts": 0}
        _save_metrics("group_candidates", c["id"], m)
        done.append({**c, **m})
        B._pause(page, 6, 14)
    if any(not c.get("_prefilter") for c in done):
        import group_review as R
        parts = []
        for c in [c for c in done if not c.get("_prefilter")]:
            ppd = R.per_day(c)
            bits = [f"{R.n(ppd)} bài/ngày" if ppd is not None else "",
                    f"TB {R.n(c.get('avg_reactions'))} cảm xúc, {R.n(c.get('avg_comments'))} bình luận" if c.get("sampled_posts") else
                    "chưa xem được bài",
                    f"+{R.n(c['new_members_week'])} tv/tuần" if c.get("new_members_week") is not None else "",
                    "luật cấm bán hàng" if c.get("no_selling") else ""]
            parts.append(f"{c['name'][:50]} ({', '.join(b for b in bits if b)})")
        db.log(f"sale-{(db.one('SELECT sale_id FROM fb_accounts WHERE id=?', (aid,)) or {}).get('sale_id')}", "Khảo sát nhóm",
               f"{sale_label} xem {len(parts)} nhóm và báo Tuấn: " + "; ".join(parts))
    return done


def _refresh_after_join(page, g: dict):
    """Vừa vào được nhóm (thường là nhóm riêng tư): đọc bài trong nhóm để Tuấn đánh giá lại tương tác thật."""
    if int(g.get("sampled_posts") or 0) >= 3:
        return
    try:
        m = read_feed(page, scrolls=2)
        if m.get("sampled_posts"):
            m["scouted_at"] = db.now()
            _save_metrics("groups", g["id"], m)
            import group_review
            ev = group_review.review_group(g["id"])
            if ev:
                db.log("tuan", "Đánh giá lại nhóm", f"{g['name']}: vào được nhóm, đọc {m['sampled_posts']} bài, "
                       f"{group_review.n(ev['score'])} điểm tương tác ({group_review.VERDICT_TXT[ev['verdict']]}). {ev['reasons'][:160]}")
    except Exception as e:
        print("[scout after join]", e)


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


def _search(page, keyword: str, aid: int) -> int:
    import browser_poster as B
    page.goto(f"{B.FB_BASE}/search/groups/?q={quote(keyword)}", wait_until="domcontentloaded", timeout=60000)
    page.wait_for_timeout(4000)
    B._check_blocked(page)
    for _ in range(4):  # cuộn để tải thêm kết quả
        page.mouse.wheel(0, 1600)
        page.wait_for_timeout(int(random.uniform(1.8, 3.5) * 1000))
    rows = page.evaluate(EXTRACT_JS, sorted(SKIP_SLUGS))
    base = B.FB_BASE if not B.FB_BASE.startswith("https://www.facebook.com") else "https://www.facebook.com"
    return save_results(rows, keyword, aid, base)


def _is_member(page) -> bool:
    import browser_poster as B
    return bool(B._visible_first(page, B.selectors()["group_composer"]))


def _join_one(page, g: dict, aid: int) -> str:
    import browser_poster as B
    sel = B.selectors()
    page.goto(B.fb_url(g["url"]), wait_until="domcontentloaded", timeout=60000)
    page.wait_for_timeout(3500)
    B._check_blocked(page)
    if _is_member(page):
        set_join(g["id"], aid, "joined")
        _refresh_after_join(page, g)
        return "joined"
    if B._visible_first(page, sel.get("pending_join", [])):
        set_join(g["id"], aid, "requested")
        return "requested"
    btn = B._visible_first(page, sel.get("join_button", []))
    if not btn:
        set_join(g["id"], aid, "failed", "Không thấy nút Tham gia nhóm. Nút đang thấy: " + B._labels_on(page))
        return "failed"
    btn.click()
    page.wait_for_timeout(3500)
    dlg = B._top_dialog(page)
    if dlg and re.search(r"câu hỏi|trả lời|answer|question|nội quy|rules", dlg.inner_text(), re.I):
        # nhóm bắt trả lời câu hỏi: sale không tự trả lời thay sếp
        page.keyboard.press("Escape")
        page.wait_for_timeout(1000)
        set_join(g["id"], aid, "needs_answers", "Nhóm yêu cầu trả lời câu hỏi khi xin vào")
        return "needs_answers"
    if _is_member(page):
        set_join(g["id"], aid, "joined")
        return "joined"
    set_join(g["id"], aid, "requested")
    return "requested"


def _join_some(page, aid: int) -> dict:
    """Kiểm tra các yêu cầu đang chờ, rồi xin vào thêm nhóm mới (trong giới hạn mỗi ngày)."""
    import browser_poster as B
    res = {"joined": 0, "requested": 0, "needs_answers": 0, "failed": 0, "checked": 0}
    for g in db.q("""SELECT g.* FROM account_groups j JOIN groups g ON g.id=j.group_id WHERE j.account_id=? AND j.status='requested'
                     ORDER BY j.updated_at LIMIT 3""", (aid,)):
        page.goto(B.fb_url(g["url"]), wait_until="domcontentloaded", timeout=60000)
        page.wait_for_timeout(3000)
        B._check_blocked(page)
        res["checked"] += 1
        if _is_member(page):
            set_join(g["id"], aid, "joined")
            _refresh_after_join(page, g)
            res["joined"] += 1
        B._pause(page, 3, 7)
    if s().get("join_enabled", "1") != "1":
        return res
    cap = max(0, int(s().get("join_per_nick_day") or 2) - joins_today(aid))
    for g in db.q("""SELECT * FROM groups g WHERE source='search' AND COALESCE(url,'')!='' AND COALESCE(verdict,'join')!='skip'
                     AND NOT EXISTS (SELECT 1 FROM account_groups j WHERE j.group_id=g.id AND j.account_id=?)
                     ORDER BY COALESCE(eng_score, score / 2) DESC, members DESC LIMIT ?""", (aid, cap)):
        st = _join_one(page, g, aid)
        res[st] = res.get(st, 0) + 1
        B._pause(page, 8, 20)  # giãn cách giữa các lần xin vào nhóm
    return res


def _report(notify, text):
    if notify:
        import ceo_orders
        ceo_orders.followup(text, notify)


def job_discover(pw, acc_id: int, keywords: list[str], notify: str | None = None):
    import browser_poster as B
    import workflows
    acc, sale_row, aid = B._ctx_names(acc_id)
    sale_id = acc["sale_id"]
    ctx, page = B._open(pw, acc_id)
    found, added, jr, scouted, rv, n_sc = 0, [], {}, [], {}, 0
    try:
        if not B._logged_in(ctx):
            B._set_login(acc_id, "not_logged_in", "Phiên đăng nhập đã hết, cần đăng nhập lại")
            raise RuntimeError("Nick chưa đăng nhập. Vào Nhân viên sale → Mở Chrome để đăng nhập lại")
        workflows.set_status(aid, "working", "Đang lướt Facebook")
        _browse(page, float(s().get("browse_minutes") or 2))
        for kw in keywords:
            workflows.set_status(aid, "working", f"Đang tìm nhóm: {kw}")
            found += _search(page, kw, acc_id)
            B._pause(page, 5, 12)
        sale_label = f"{sale_row['name']} (nick {acc['name']})"
        scouted = _scout_some(page, acc_id, sale_label)
        n_sc = len([c for c in scouted if not c.get("_prefilter")])
        import group_review
        rv = group_review.review_candidates([c["id"] for c in scouted], by=sale_label) if scouted else {"added": auto_add()}
        added = rv["added"]
        if added or db.one("SELECT 1 x FROM groups WHERE source='search' LIMIT 1"):
            workflows.set_status(aid, "working", "Đang xin vào nhóm mới")
            jr = _join_some(page, acc_id)
        db.set_setting("discover_last_result", json.dumps({"at": db.now(), "sale_id": sale_id, "account_id": acc_id, "keywords": keywords,
                                                           "found": found, "scouted": n_sc, "added": len(added),
                                                           "review": {k: len(rv.get(k, [])) for k in ("join", "consider", "skip")},
                                                           "joins": jr}, ensure_ascii=False))
        db.log(aid, "Tìm nhóm mới", f"Tìm “{'”, “'.join(keywords)}”: {found} nhóm mới, khảo sát {n_sc} nhóm, "
               f"Tuấn duyệt thêm {len(added)} nhóm vào danh sách"
               + (f", xin vào {jr.get('requested', 0) + jr.get('joined', 0)} nhóm" if jr else ""))
        sale = f"{sale_row['name']} (nick {acc['name']})"
        if found or added or scouted:
            rvt = (f" Sale khảo sát {n_sc} nhóm, Tuấn đánh giá: nên vào {len(rv.get('join', []))}, cân nhắc "
                   f"{len(rv.get('consider', []))}, bỏ qua {len(rv.get('skip', []))}." if scouted else "")
            if added:
                msg = (f"{sale} tìm xong theo “{'”, “'.join(keywords)}”: {found} nhóm mới.{rvt} Em đã thêm {len(added)} nhóm tương tác "
                       f"tốt vào danh sách Hội nhóm: " + ", ".join(g["name"] for g in added[:4]) + ".")
            else:
                limit = int(s().get("discover_add_per_day") or 5)
                today_n = db.one("SELECT COUNT(*) n FROM groups WHERE source='search' AND created_at LIKE ?", (db.today() + "%",))["n"]
                why = (f"hôm nay đã tự thêm đủ {limit} nhóm (giới hạn mỗi ngày)" if today_n >= limit else
                       "chưa nhóm nào đạt chuẩn nhóm tương tác cao (xem lý do từng nhóm ở Hội nhóm → Tìm nhóm mới)")
                msg = f"{sale} tìm xong theo “{'”, “'.join(keywords)}”: {found} nhóm mới.{rvt} Em chưa thêm nhóm nào vì {why}."
            if jr and any(jr.get(k) for k in ("joined", "requested", "needs_answers")):
                msg += (f" Đã vào {jr.get('joined', 0)} nhóm, đang chờ duyệt {jr.get('requested', 0)} nhóm"
                        + (f", {jr['needs_answers']} nhóm cần sếp tự trả lời câu hỏi" if jr.get("needs_answers") else "") + ".")
            rest = db.one("SELECT COUNT(*) n FROM group_candidates WHERE status='new' AND verdict='consider'")["n"]
            if rest:
                msg += f" Có {rest} nhóm Tuấn để “Cân nhắc”, chờ sếp xem ở Hội nhóm → Tìm nhóm mới."
        else:
            msg = (f"{sale} đã tìm theo “{'”, “'.join(keywords)}” nhưng không thấy nhóm mới nào (có thể các nhóm đã có trong danh "
                   "sách, hoặc trang tìm kiếm của Facebook hiển thị khác). Sếp thử chủ đề khác, hoặc vào mục Lỗi xem có báo lỗi không.")
        _report(notify, msg)
    except B.Blocked as e:
        B._block(acc_id, str(e))
        _report(notify, f"Nick của sale bị Facebook chặn hoặc kiểm tra khi đang tìm nhóm: {e}. Em đã dừng nick này, sếp mở Chrome của sale để xử lý.")
    finally:
        try:
            ctx.close()
        except Exception:
            pass
        workflows.set_status(aid, "idle", f"Tìm được {found} nhóm mới")


def job_join(pw, acc_id: int, notify: str | None = None):
    import browser_poster as B
    import workflows
    acc, sale_row, aid = B._ctx_names(acc_id)
    sale_id = acc["sale_id"]
    ctx, page = B._open(pw, acc_id)
    try:
        if not B._logged_in(ctx):
            raise RuntimeError("Nick chưa đăng nhập. Vào Nhân viên sale → Mở Chrome để đăng nhập lại")
        workflows.set_status(aid, "working", "Đang xin vào nhóm mới")
        jr = _join_some(page, acc_id)
        if any(jr.values()):
            db.log(aid, "Xin vào nhóm", f"Vào được {jr['joined']} nhóm, chờ duyệt {jr['requested']}, "
                   f"cần sếp trả lời câu hỏi {jr['needs_answers']}")
        sale = f"{sale_row['name']} (nick {acc['name']})"
        _report(notify, f"{sale} xin vào nhóm xong: vào được {jr.get('joined', 0)}, chờ duyệt {jr.get('requested', 0)}"
                + (f", {jr['needs_answers']} nhóm cần sếp tự trả lời câu hỏi" if jr.get("needs_answers") else "")
                + ("." if any(jr.values()) else ". Hôm nay nick đã xin đủ số nhóm cho phép hoặc chưa có nhóm mới để xin."))
    except B.Blocked as e:
        B._block(acc_id, str(e))
    finally:
        try:
            ctx.close()
        except Exception:
            pass
        workflows.set_status(aid, "idle", "Chờ việc tiếp theo")


# ---------------------------------------------------------------- lịch hằng ngày
def _working_sales() -> list[dict]:
    """Nhân viên sale có ít nhất một nick làm được."""
    return db.q("""SELECT * FROM sales WHERE COALESCE(status,'active')='active' AND COALESCE(is_sample,0)=0
                   AND login_status='ok' AND auto_post=1 ORDER BY id""")


def _working_accounts() -> list[dict]:
    import accounts
    return [a for a in accounts.working() if not db.one("SELECT 1 x FROM sales WHERE id=? AND COALESCE(is_sample,0)=1", (a["sale_id"],))]


def start_discover(sale_id: int | None = None, keywords: list[str] | None = None, notify: str | None = None) -> dict:
    """Giao một nick đi tìm nhóm (luân phiên các nick, ưu tiên nick của sale đang rảnh)."""
    import browser_poster as B
    accs = _working_accounts()
    if sale_id is not None:
        accs = [a for a in accs if a["sale_id"] == sale_id] or accs
    if not accs:
        raise ValueError("Chưa có nick sale nào đăng nhập và đang bật tự đăng")
    last = int(s().get("discover_last_account") or 0)
    idle = [a for a in accs if not B.busy(a["sale_id"]) and not B.queued(a["sale_id"])] or accs
    nxt = [a for a in idle if a["id"] > last] or idle
    acc = nxt[0]
    kws = keywords or today_keywords()
    db.set_setting("discover_last_account", str(acc["id"]))
    db.set_setting("discover_last_sale", str(acc["sale_id"]))
    B.submit(acc["sale_id"], {"kind": "discover", "account": acc["id"], "keywords": kws, "notify": notify})
    return {"sale_id": acc["sale_id"], "account_id": acc["id"], "account": acc["name"], "keywords": kws}


def submit_joins(notify: str | None = None) -> int:
    """Mỗi nick còn lượt xin vào nhóm hôm nay: giao xin vào nhóm (sale làm lần lượt từng nick)."""
    import browser_poster as B
    n = 0
    cap = int(s().get("join_per_nick_day") or 2)
    for a in _working_accounts():
        if joins_today(a["id"]) < cap:
            B.submit(a["sale_id"], {"kind": "join", "account": a["id"], "notify": notify})
            n += 1
    return n


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
    # 45 phút sau: các nick xin vào nhóm mới được thêm
    later = (datetime.strptime(t, "%H:%M") + timedelta(minutes=45)).strftime("%H:%M")
    if st.get("join_enabled", "1") == "1" and hm >= later and st.get("join_last") != db.today():
        db.set_setting("join_last", db.today())
        submit_joins()


def overview() -> dict:
    import group_review
    cand = db.q("""SELECT * FROM group_candidates WHERE status='new'
                   ORDER BY CASE verdict WHEN 'join' THEN 0 WHEN 'consider' THEN 1 ELSE 2 END, COALESCE(eng_score,-1) DESC, score DESC
                   LIMIT 60""")
    rejected = db.q("""SELECT * FROM group_candidates WHERE status='rejected' ORDER BY reviewed_at DESC LIMIT 30""")
    bench = group_review.benchmark()
    st = s()
    try:
        today = json.loads(st.get("ceo_kw_today") or "{}")
    except Exception:
        today = {}
    return {"today": today_keywords() if (today.get("date") != db.today()) else today.get("keywords"),
            "today_by": today.get("by", "ceo"), "pool": pool(), "stats": keyword_stats(), "candidates": cand,
            "rejected": rejected, "benchmark": bench, "benchmark_text": group_review.bench_text(bench),
            "last": json.loads(st.get("discover_last_result") or "{}"),
            "settings": {k: st.get(k) for k in ("discover_enabled", "discover_time", "discover_keywords_per_day",
                                                 "discover_add_per_day", "join_enabled", "join_per_nick_day", "browse_minutes",
                                                 "scout_per_run", "review_posts_day", "review_avg_reactions", "review_avg_comments",
                                                 "review_growth_week", "review_min_members", "review_join_score",
                                                 "review_consider_score", "review_use_best_groups")},
            "pending_answers": db.q("""SELECT g.id, g.name, g.url, s.name || ' · nick ' || a.name sale FROM account_groups j
                                       JOIN groups g ON g.id=j.group_id JOIN fb_accounts a ON a.id=j.account_id
                                       JOIN sales s ON s.id=a.sale_id WHERE j.status='needs_answers'""")}

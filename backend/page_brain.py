"""Nhi quản lý nhiều Trang theo ý sếp.

- Mỗi Trang có ngành nghề (niche), từ khóa nội dung sếp đặt, chủ đề không viết, lời dặn riêng.
- Nhi chia chủ đề cho các Trang: tin nóng hôm nay giao cho Trang hợp nhất (mỗi tin một Trang / ngày), còn lại xoay vòng
  từ khóa của Trang, ưu tiên từ khóa sếp hay duyệt ngay và có tương tác, lâu chưa viết.
- Sếp duyệt bài trước khi đăng (cài đặt trend_review, mặc định bật). Duyệt ngay / sửa rồi duyệt / loại kèm lý do đều được
  Nhi ghi nhớ theo từng Trang (page_memory) và đưa vào đề bài lần sau. Tỉ lệ duyệt ngay = "Nhi hiểu ý sếp"; đủ cao thì gợi ý tắt duyệt.
"""
import random
import re
import threading

import db
from group_target import words
from knowledge import tokens, plain

REASONS = ["Sai chủ đề của Trang", "Không đúng từ khóa", "Giọng văn chưa hợp", "Quá dài", "Quá ngắn", "Thông tin chưa đúng / bịa", "Trùng bài cũ", "Khác"]
KEEP_LESSONS = 12


def _s() -> dict:
    return db.get_settings()


def review_on() -> bool:
    return _s().get("trend_review", "1") == "1"


def _toks(t: str) -> set:
    return set(tokens(t or ""))


def _fit(topic: str, pg: dict) -> float:
    """Tin nóng hợp Trang bao nhiêu (0–1): phần chữ của tin có trong từ khóa / ngành / tên / mô tả của Trang."""
    a = _toks(topic)
    if not a:
        return 0.0
    kw = _toks(" ".join(words(pg.get("keywords") or "")) + " " + (pg.get("niche") or ""))
    rest = _toks(f"{pg.get('name') or ''} {pg.get('description') or ''}")
    return min(1.0, (len(a & kw) + 0.5 * len(a & (rest - kw))) / len(a))


def _avoid(topic: str, pg: dict) -> bool:
    t = " " + plain(topic) + " "
    return any(plain(w).strip() and f" {plain(w).strip()} " in t for w in words(pg.get("avoid") or ""))


def kw_stats(pg: dict) -> list[dict]:
    """Từng từ khóa của Trang: số bài 60 ngày, sếp duyệt ngay bao nhiêu, tương tác trung bình."""
    rows = {plain(r["k"]): r for r in db.q("""SELECT page_kw k, COUNT(*) n, SUM(review_result='ok') ok, SUM(review_result='reject') bad,
            AVG(CASE WHEN status='posted' THEN COALESCE(reactions,0)+2*COALESCE(comments,0)+3*COALESCE(shares,0) END) eng, MAX(created_at) last
            FROM posts WHERE fb_page_ref=? AND page_kw IS NOT NULL AND created_at >= date('now','-60 day') GROUP BY page_kw""", (pg["id"],))}
    out = []
    for k in words(pg.get("keywords") or ""):
        r = rows.get(plain(k)) or {}
        out.append({"kw": k, "n": r.get("n") or 0, "ok": r.get("ok") or 0, "bad": r.get("bad") or 0,
                    "eng": round(r.get("eng") or 0, 1), "last": r.get("last") or ""})
    return out


def pick_keyword(pg: dict, rnd=None) -> str | None:
    rnd = rnd or random.Random()
    st = kw_stats(pg)
    if not st:
        return None
    if rnd.random() < 0.2:  # chừa lượt thử: từ khóa lâu chưa viết nhất
        return min(st, key=lambda x: (x["last"], x["n"]))["kw"]
    recent = [plain(r["page_kw"] or "") for r in db.q("SELECT page_kw FROM posts WHERE fb_page_ref=? ORDER BY id DESC LIMIT ?",
                                                       (pg["id"], max(1, len(st) - 1)))]
    top = max([x["eng"] for x in st] + [1])

    def score(x):
        return (x["ok"] + 1) / (x["n"] + 2) - 0.6 * x["bad"] / (x["n"] + 2) + 0.3 * x["eng"] / top - (1.0 if plain(x["kw"]) in recent else 0)
    return max(st, key=score)["kw"]


def choose(pg: dict, allow_trend: bool = True, rnd=None) -> dict:
    """Chủ đề cho bài kế tiếp của Trang: tin nóng hợp nhất (Trang này hợp nhất trong các Trang đang chạy) hoặc từ khóa của Trang."""
    hot = db.q("SELECT title, niche, score, why FROM trend_hot WHERE day=? ORDER BY score DESC LIMIT 10", (db.today(),)) if allow_trend else []
    taken = {plain(r["t"]) for r in db.q("""SELECT trend_topic t FROM posts WHERE fb_page_ref IS NOT NULL AND trend_kind='trend'
                                           AND created_at >= ?""", (db.today(),))}
    taken |= {plain(r["t"]) for r in db.q("SELECT trend_topic t FROM posts WHERE fb_page_ref=? AND created_at >= date('now','-3 day')", (pg["id"],))}
    others = [p for p in db.q("SELECT * FROM fb_pages WHERE status='active' AND id != ? AND COALESCE(kind,'trend')='trend'", (pg["id"],))]
    for h in hot:
        t = h["title"]
        if plain(t) in taken or _avoid(t, pg):
            continue
        f = max(_fit(t, pg), _fit(h.get("niche") or "", pg) * 0.9)
        if f >= 0.5 and all(_fit(t, o) <= f for o in others):
            kw = next((k for k in words(pg.get("keywords") or "") if _toks(k) & _toks(t)), None)
            return {"topic": t, "kind": "trend", "kw": kw, "hot": h}
    kw = pick_keyword(pg, rnd)
    return {"topic": kw or pg.get("niche") or pg["name"], "kind": "evergreen", "kw": kw, "hot": None}


def memory(pid: int, limit: int = 20) -> list[dict]:
    return db.q("SELECT * FROM page_memory WHERE page_id=? ORDER BY id DESC LIMIT ?", (pid, limit))


def remember(pid: int, kind: str, text: str, kw: str | None = None):
    text = (text or "").strip()
    if not text:
        return
    if db.one("SELECT 1 FROM page_memory WHERE page_id=? AND text=?", (pid, text)):
        return
    db.run("INSERT INTO page_memory(page_id, kind, text, keyword, created_at) VALUES (?,?,?,?,?)", (pid, kind, text[:300], kw, db.now()))
    old = db.q("SELECT id FROM page_memory WHERE page_id=? AND kind IN ('lesson','reject') ORDER BY id DESC LIMIT -1 OFFSET ?", (pid, KEEP_LESSONS))
    for r in old:
        db.run("DELETE FROM page_memory WHERE id=?", (r["id"],))


def brief(pg: dict, kw: str | None) -> str:
    """Phần đề bài nói Trang này là gì, sếp muốn gì và Nhi đã ghi nhớ gì từ những lần sếp duyệt."""
    out = [f"Ngành nghề / chủ đề của Trang: {pg.get('niche') or '(chưa ghi)'}. Bài phải đúng ngành nghề và hợp với tên Trang."]
    kws = words(pg.get("keywords") or "")
    if kws:
        out.append("Từ khóa nội dung sếp đặt cho Trang: " + ", ".join(kws) + ".")
    if kw:
        out.append(f"Bài này viết xoay quanh từ khóa: {kw}.")
    if pg.get("avoid"):
        out.append("Không viết về: " + ", ".join(words(pg["avoid"])) + ".")
    if pg.get("boss_note"):
        out.append("Sếp dặn riêng Trang này: " + pg["boss_note"].strip())
    mem = [m for m in memory(pg["id"], 12) if m["kind"] in ("lesson", "note", "reject")]
    if mem:
        out.append("Nhi đã ghi nhớ theo ý sếp (làm đúng như vậy):\n" + "\n".join(
            f"- {'Sếp từng loại bài vì: ' if m['kind'] == 'reject' else ''}{m['text']}" for m in mem[:8]))
    ex = db.q("""SELECT content FROM posts WHERE fb_page_ref=? AND review_result='edit' ORDER BY reviewed_at DESC LIMIT 2""", (pg["id"],))
    if ex:
        out.append("Bản sếp đã sửa (học giọng và cách trình bày, không chép):\n" + "\n---\n".join((e["content"] or "")[:400] for e in ex))
    return "\n".join(out)


def _mock_lesson(before: str, after: str) -> str:
    lb, la = len(before.split()), len(after.split())
    emo = lambda t: sum(1 for c in t if ord(c) > 0x2600)
    if la < lb * 0.8:
        return f"Sếp thích bài ngắn hơn: khoảng {la} chữ"
    if la > lb * 1.25:
        return f"Sếp thích bài đầy đủ hơn: khoảng {la} chữ"
    if emo(after) < emo(before):
        return "Dùng ít emoji hơn"
    if before.count("#") > after.count("#"):
        return "Ít hashtag hơn"
    first = (after.strip().split("\n") or [""])[0][:80]
    return f"Mở bài theo kiểu sếp viết: “{first}”" if first else ""


def learn_edit(pid: int, before: str, after: str, kw: str | None = None, wait: bool = False):
    """Sếp sửa bài: rút 1 bài học ngắn (Claude so hai bản; chưa có khóa thì so độ dài, emoji, hashtag)."""
    def go():
        from llm import llm
        pg = db.one("SELECT name, niche FROM fb_pages WHERE id=?", (pid,)) or {}
        mock = _mock_lesson(before, after)
        d = llm.json("Bạn là Nhi, biên tập Trang Facebook, đang học cách sếp muốn viết.",
                     f"""Trang "{pg.get('name')}" ({pg.get('niche')}). Sếp đã sửa bài của em trước khi duyệt.
Bản em viết:\n{before[:1200]}\n\nBản sếp sửa:\n{after[:1200]}
Rút 1 bài học ngắn (dưới 25 chữ, tiếng Việt, câu ra lệnh cho chính em) về điều sếp muốn ở bài cho Trang này. Không nhắc lại nội dung cụ thể của bài.
JSON: {{"lesson": "..."}}""", mock=lambda: {"lesson": mock}, max_tokens=200, task="posts") or {}
        remember(pid, "lesson", (d.get("lesson") or mock).strip(), kw)
    if wait:
        go()
    else:
        threading.Thread(target=go, daemon=True).start()


def review(post_id: int, action: str, content: str | None = None, reason: str = "", wait: bool = False) -> dict:
    import fb_policy
    import pricing
    import trend_pages
    p = db.one("SELECT * FROM posts WHERE id=?", (post_id,))
    if not p or p["status"] != "page_review":
        raise ValueError("Bài này không còn chờ duyệt")
    if action == "reject":
        why = (reason or "").strip()[:200] or "Sếp loại"
        db.run("UPDATE posts SET status='rejected', error=?, review_result='reject', reviewed_at=? WHERE id=?", (f"Sếp loại: {why}", db.now(), post_id))
        if why not in ("Sếp loại", "Khác"):
            remember(p["fb_page_ref"], "reject", f"{why}" + (f" (từ khóa “{p['page_kw']}”)" if p["page_kw"] else ""), p["page_kw"])
        db.log("nhi", "Sếp loại bài Trang", f"Bài #{post_id}: {why}")
        return db.one("SELECT * FROM posts WHERE id=?", (post_id,))
    new = pricing.sanitize((content if content is not None else p["content"]) or "", add_contact=False).strip()
    if not new:
        raise ValueError("Bài trống")
    bad = [i for i in fb_policy.check_text(new) if i["level"] == "high"]
    if bad:
        raise ValueError("Bài phạm Luật Facebook: " + "; ".join(i.get("msg") or i.get("rule") or "" for i in bad)[:200])
    edited = " ".join(new.split()) != " ".join((p["content"] or "").split())
    grow = p.get("source") == "page_grow"  # bài nuôi Trang: ảnh lấy từ thư mục sản phẩm, duyệt xong xếp đăng luôn
    db.run("UPDATE posts SET content=?, status=?, review_result=?, reviewed_at=? WHERE id=?",
           (new, "scheduled" if grow else "need_image", "edit" if edited else "ok", db.now(), post_id))
    if grow and (p["scheduled_for"] or "") < db.clock().strftime("%Y-%m-%d %H:%M"):
        import page_grow
        pg = db.one("SELECT * FROM fb_pages WHERE id=?", (p["fb_page_ref"],))
        db.run("UPDATE posts SET scheduled_for=? WHERE id=?", (page_grow.next_slot(pg), post_id))
    if edited:
        learn_edit(p["fb_page_ref"], p["content"] or "", new, p["page_kw"], wait=wait)
    db.log("nhi", "Sếp duyệt bài Trang", f"Bài #{post_id}" + (" (sếp đã sửa, Nhi ghi nhớ)" if edited else "") + (": xếp đăng" if grow else ": đã gửi prompt ảnh"))
    if not grow:
        trend_pages.ask_image(post_id)
    return db.one("SELECT * FROM posts WHERE id=?", (post_id,))


def approve_all() -> int:
    n = 0
    for r in db.q("SELECT id FROM posts WHERE status='page_review' ORDER BY scheduled_for"):
        try:
            review(r["id"], "approve")
            n += 1
        except ValueError:
            pass
    return n


def cleanup():
    db.run("""UPDATE posts SET status='rejected', error='Sếp chưa duyệt sau 48 giờ' WHERE status='page_review' AND created_at <= datetime('now','-2 day')""")


def smartness(pid: int | None = None, n: int = 30) -> dict:
    """Nhi hiểu ý sếp: trong n lần sếp duyệt gần nhất, bao nhiêu bài sếp duyệt ngay không sửa."""
    rows = db.q("SELECT review_result r FROM posts WHERE review_result IS NOT NULL AND source='trend_page'" + (" AND fb_page_ref=?" if pid else "")
                + " ORDER BY reviewed_at DESC LIMIT ?", ((pid, n) if pid else (n,)))
    c = {k: sum(1 for x in rows if x["r"] == k) for k in ("ok", "edit", "reject")}
    tot = len(rows)
    pct = round(100 * c["ok"] / tot) if tot else 0
    return {"n": tot, **c, "pct": pct, "need": 20, "suggest_off": tot >= 20 and pct >= 85}


def suggest_keywords(pid: int) -> list[str]:
    from llm import llm
    pg = db.one("SELECT * FROM fb_pages WHERE id=?", (pid,))
    if not pg:
        raise ValueError("Không có Trang này")
    have = words(pg["keywords"] or "")
    good = [r["t"] for r in db.q("""SELECT trend_topic t FROM posts WHERE fb_page_ref=? AND review_result='ok' AND trend_topic IS NOT NULL
                                    GROUP BY trend_topic ORDER BY MAX(COALESCE(reactions,0)+2*COALESCE(comments,0)) DESC LIMIT 8""", (pid,))]
    mock = [t for t in good if plain(t) not in {plain(h) for h in have}][:6] or \
        [f"{pg['niche'] or pg['name']} {s}" for s in ("cho người mới", "mẹo hay", "hỏi đáp", "sai lầm thường gặp")]
    d = llm.json("Bạn là Nhi, biên tập Trang Facebook.", f"""Trang "{pg['name']}", ngành nghề: {pg['niche']}. {pg['description'] or ''}
Từ khóa nội dung sếp đã đặt: {', '.join(have) or '(chưa có)'}. Không viết về: {pg['avoid'] or '(không)'}.
Chủ đề sếp duyệt ngay và được hưởng ứng: {', '.join(good) or '(chưa có)'}.
Đề xuất tối đa 6 từ khóa nội dung MỚI (2–5 chữ, cùng tinh thần với từ khóa sếp đặt, đúng ngành nghề của Trang, viết bài bền được nhiều lần).
JSON: {{"keywords": ["..."]}}""", mock=lambda: {"keywords": mock}, max_tokens=300, task="posts") or {}
    out = []
    for k in d.get("keywords") or mock:
        k = str(k).strip()[:60]
        if k and plain(k) not in {plain(x) for x in have + out}:
            out.append(k)
    return out[:6]


def update_page(pid: int, data: dict) -> dict:
    pg = db.one("SELECT * FROM fb_pages WHERE id=?", (pid,))
    if not pg:
        raise ValueError("Không có Trang này")
    sets, vals = [], []
    for k in ("niche", "keywords", "avoid", "boss_note", "times"):
        if k in data and data[k] is not None:
            v = str(data[k]).strip()
            if k in ("keywords", "avoid"):
                v = ", ".join(words(v))
            sets.append(f"{k}=?"); vals.append(v[:1500])
    if data.get("posts_per_day") not in (None, ""):
        sets.append("posts_per_day=?"); vals.append(max(1, min(5, int(data["posts_per_day"]))))
    if sets:
        db.run(f"UPDATE fb_pages SET {', '.join(sets)} WHERE id=?", (*vals, pid))
    if (data.get("teach") or "").strip():
        remember(pid, "note", data["teach"].strip())
    return db.one("SELECT * FROM fb_pages WHERE id=?", (pid,))


def overview() -> dict:
    pages = db.q("""SELECT f.*, a.name admin_name FROM fb_pages f LEFT JOIN fb_accounts a ON a.id=f.admin_account_id
                    WHERE f.status IN ('active','paused','creating') ORDER BY CASE f.status WHEN 'active' THEN 0 ELSE 1 END, f.name""")
    today = db.q("""SELECT fb_page_ref pid, id, status, COALESCE(trend_topic, angle) trend_topic, page_kw, trend_kind, scheduled_for FROM posts
                    WHERE fb_page_ref IS NOT NULL AND substr(scheduled_for,1,10)=? AND status != 'rejected' ORDER BY scheduled_for""", (db.today(),))
    for p in pages:
        p["kw"] = kw_stats(p)
        p["memory"] = memory(p["id"], 15)
        p["smart"] = smartness(p["id"])
        p["today"] = [t for t in today if t["pid"] == p["id"]]
    queue = db.q("""SELECT p.id, p.content, p.scheduled_for, COALESCE(p.trend_topic, p.angle) trend_topic, p.trend_kind, p.page_kw, p.source, p.created_at, p.agent_id, f.name page_name, f.niche
                    FROM posts p JOIN fb_pages f ON f.id=p.fb_page_ref WHERE p.status='page_review' ORDER BY p.scheduled_for""")
    s = _s()
    return {"pages": pages, "queue": queue, "smart": smartness(), "review": review_on(), "reasons": REASONS,
            "noimg": s.get("trend_noimg_post", "1") == "1", "auto_kw": s.get("nhi_auto_kw", "1") == "1",
            "focus": " | ".join(focus()), "avoid": " | ".join(avoid_niches())}


# ---------------------------------------------------------------- ngách trọng tâm sếp chọn cho Nhi
FOCUS_DEFAULT = "ẩm thực, nấu ăn | mẹo vặt gia đình | lối sống, sống khỏe nhẹ nhàng"
AVOID_DEFAULT = "tin tức thời sự | bói toán, tử vi, phong thủy | cờ bạc, xổ số, cá độ | chính trị, tôn giáo"
FOCUS_PHRASES = {  # cụm từ nhận diện từng ngách (không dấu, so nguyên cụm), dùng khi chưa có Claude và để lọc lại kết quả
    "am thuc": "am thuc|nau an|mon an|mon ngon|cong thuc|nha bep|vao bep|do uong|tra sua|ca phe|an vat|an sang|bua sang|bua com|bua toi|nuoc ep|sinh to|"
               "lau|nuong|banh|canh|kho to|xao|chien|hap|thuc don|dac san|mon chay|tra |pha che|bep nha",
    "meo vat": "meo vat|meo hay|meo nho|meo nau|meo don|meo giat|meo bao quan|meo tiet kiem|meo gia dinh|meo nha|nha cua|don dep|tiet kiem|noi tro|"
               "giat ui|bep nuc|sap xep|bao quan|khu mui|ve sinh nha|cham soc nha|gia dinh",
    "song khoe": "song khoe|suc khoe|lanh manh|giac ngu|ngu ngon|yoga|tap the duc|the duc|dinh duong|thu gian|song cham|thien |di bo|giu am|"
                 "cang thang|an uong lanh manh|song xanh|loi song|cham soc ban than|eat clean|healthy",
}
def focus() -> list[str]:
    return [x.strip() for x in (_s().get("nhi_focus") or FOCUS_DEFAULT).split("|") if x.strip()]


def avoid_niches() -> list[str]:
    return [x.strip() for x in (_s().get("nhi_avoid_niches") or AVOID_DEFAULT).split("|") if x.strip()]


def _plain_set(t: str) -> set:
    return set(tokens(t or ""))


def in_focus(text: str) -> bool:
    """Chủ đề / Trang thuộc ngách trọng tâm: có cụm từ của ngách sếp đặt hoặc cụm nhận diện của ngách đó (so nguyên cụm, không dấu)."""
    t = " " + plain(text or "") + " "
    for f in focus():
        pf = plain(f)
        phrases = [plain(x).strip() for x in re.split(r"[,;/]", f) if len(plain(x).strip()) > 2]
        for key, ph in FOCUS_PHRASES.items():
            if key in pf:
                phrases += [x for x in ph.split("|") if x.strip()]
        if any((f" {x.strip()} " in t) if not x.endswith(" ") else (f" {x}" in t) for x in phrases):
            return True
    return False


def is_avoided(text: str) -> bool:
    t = " " + plain(text or "") + " "
    pairs = ("tin tuc", "thoi su", "tu vi", "phong thuy", "xo so", "ca do", "co bac", "chinh tri", "ton giao", "boi toan", "xem boi", "vu an", "tai nan")
    return any(f" {p} " in t for p in pairs) or any(f" {p} " in t for a in avoid_niches() for p in [plain(a).strip()] if p)


def focus_prompt() -> str:
    return (f"TRỌNG TÂM CỦA SẾP: Nhi chỉ chọn chủ đề và đề xuất Trang trong các ngách: {'; '.join(focus())}. "
            "Tin nóng ngoài các ngách này chỉ dùng khi có góc liên quan rõ (VD trời lạnh → món ăn ấm, mẹo giữ ấm, cách ngủ ngon), gán vào ngách trọng tâm. "
            f"Không bao giờ làm: {'; '.join(avoid_niches())}.")


def focus_report() -> str:
    rows = db.q("SELECT name, niche, status FROM fb_pages WHERE status IN ('active','paused','creating','idea') ORDER BY status, id")
    out = ["🎯 <b>Ngách trọng tâm của Nhi</b>: " + "; ".join(focus()), "🚫 Không làm: " + "; ".join(avoid_niches())]
    off = [r for r in rows if r["status"] != "idea" and not in_focus(f"{r['name']} {r['niche'] or ''}")]
    if off:
        out.append("⚠️ Trang ngoài trọng tâm (Nhi vẫn viết đúng ngành nghề của Trang; muốn dừng thì nhắn “tạm dừng &lt;tên Trang&gt;”): "
                   + ", ".join(f"{r['name']} ({r['niche'] or 'chưa ghi ngành'})" for r in off))
    out.append("Đổi trọng tâm: nhắn <code>Nhi tập trung: ẩm thực | mẹo vặt gia đình | sống khỏe</code>")
    return "\n".join(out)

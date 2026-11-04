"""Kho bài viết và phong cách viết của Lan: học từ bài Claude viết để tự viết content.

1. Lưu trữ: MỌI bài Claude viết cho Lan đều được lưu vào kho (content_library), không bị xóa khi dọn dữ liệu thử nghiệm.
   Bài sếp sửa rồi duyệt cũng được lưu (nguồn "sếp sửa", học nặng hơn). Kết quả của từng bài (sếp duyệt/loại, số bình luận,
   số khách) được cập nhật vào kho để biết câu nào hiệu quả.
2. Ghi nhớ phong cách: mỗi bài được tách thành các mảnh: câu mở đầu, ý lợi ích, dòng giá, dịch vụ xưởng, câu kêu gọi,
   đoạn kể chuyện, hashtag. Tên sản phẩm, giá, số nhập tối thiểu được thay bằng chỗ trống để dùng lại cho sản phẩm khác.
   Mảnh từ bài được duyệt/có khách được điểm cao; bài bị loại bị trừ điểm. Hồ sơ phong cách: độ dài, số dòng, emoji hay dùng,
   có gạch đầu dòng không, hashtag hay dùng.
3. Tự viết: đủ vốn (mặc định từ 12 bài Claude viết và 4 câu mở đầu) thì Lan tự ghép bài mới theo phong cách đã học, không
   gọi Claude: chọn câu mở đầu hợp góc viết, ý lợi ích từ điểm mạnh sản phẩm, dòng giá, dịch vụ, kêu gọi, hashtag; kiểm tra
   không trùng bài cũ. Chế độ "Tự động": tỉ lệ tự viết tăng dần theo số bài đã học (tối đa 80%) và giảm nếu bài tự viết
   bị sếp loại nhiều hơn bài Claude viết. Bài có yêu cầu riêng của sếp vẫn nhờ Claude. Chưa có khóa Claude: tự viết khi đủ vốn.
"""
import json
import random
import re
from collections import Counter

import db

KINDS = {"hook": "Câu mở đầu", "point": "Ý lợi ích", "price": "Dòng giá", "service": "Dịch vụ xưởng", "cta": "Kêu gọi",
         "story": "Đoạn kể chuyện"}
SOURCE_TXT = {"claude": "Claude viết", "self": "Lan tự viết", "boss": "Sếp sửa", "mock": "Mẫu có sẵn"}
CTA_RX = re.compile(r"bình luận|comment|cmt|inbox|\bib\b|nhắn tin|để lại|sđt|số điện thoại|zalo|liên hệ|gọi ngay|hotline|đăng ký", re.I)
PRICE_RX = re.compile(r"(giá|sỉ|lẻ|lãi|lời|vốn|chiết khấu)", re.I)
NUM_RX = re.compile(r"\d[\d.,]*\s*(k|đ|vnđ|vnd|nghìn|triệu|%)?", re.I)
SERVICE_RX = re.compile(r"xưởng hỗ trợ|hỗ trợ|gửi mẫu|mẫu thử|ship|giao hàng|đóng gói|video|ảnh thật|in nhãn|đổi trả|bảo hành|cod", re.I)
BULLET_RX = re.compile(r"^\s*([•\-–*✅✔☑️👉🔹🔸▪️➡️⭐️🌿💵📦🎁🔥✨💰📈🎥🏷️☕🏭]|\d+[.)])")
EMOJI_RX = re.compile(r"[\U0001F300-\U0001FAFF☀-➿⭐✅❌]")


def s() -> dict:
    return db.get_settings()


# ---------------------------------------------------------------- tách mảnh, thay biến
def _variants(name: str) -> list[str]:
    name = (name or "").strip()
    if not name:
        return []
    words = name.split()
    out = [name] + [" ".join(words[:k]) for k in (4, 3) if len(words) > k]
    return sorted(set(out), key=len, reverse=True)


def templatize(text: str, p: dict, contact: str = "") -> tuple[str, bool]:
    """Thay tên, giá, nhập tối thiểu của sản phẩm bằng chỗ trống. Trả về (mảnh, còn chi tiết riêng của sản phẩm?)."""
    t = text
    for v in _variants(p.get("name") or ""):
        t = re.sub(re.escape(v), "{name}", t, flags=re.I)
    for key, val in (("wp", p.get("wholesale_price")), ("rp", p.get("retail_price")), ("moq", p.get("moq")),
                     ("contact", contact)):
        val = (val or "").strip()
        if len(val) >= 2:
            t = t.replace(val, "{" + key + "}")
    cat = (p.get("category") or "").strip()
    if len(cat) > 3:
        t = re.sub(re.escape(cat), "{cat}", t, flags=re.I)
    leftover = bool(NUM_RX.search(re.sub(r"\{\w+\}", "", t)) and PRICE_RX.search(t))
    rest = set(re.findall(r"\w+", re.sub(r"\{\w+\}", "", t).lower()))
    if any(w in rest for w in re.findall(r"\w+", (p.get("name") or "").lower()) if len(w) >= 3):
        leftover = True  # còn sót chữ trong tên sản phẩm (VD "trà", "gừng"): chỉ dùng lại cho đúng sản phẩm này
    if re.search(r"\b(trà|bột|cà phê|cafe|coffee|ngũ cốc|hạt|thảo mộc|gừng|sen|đậu)\b", re.sub(r"\{\w+\}", "", t), re.I):
        leftover = True  # nhắc loại hàng cụ thể: không dùng cho dòng sản phẩm khác
    for other in db.q("SELECT name FROM products WHERE id != ?", (p.get("id") or 0,)):
        if other["name"] and other["name"].lower() in t.lower():
            leftover = True
    return t.strip(), leftover


def fill(tpl: str, p: dict, contact: str = "") -> str:
    vals = {"name": p.get("name") or "", "wp": p.get("wholesale_price") or "", "rp": p.get("retail_price") or "",
            "moq": p.get("moq") or "", "cat": (p.get("category") or "").lower(), "contact": contact}
    return re.sub(r"\{(\w+)\}", lambda m: vals.get(m.group(1), m.group(0)), tpl)


def split(content: str, target: str) -> list[tuple[str, str]]:
    """Chia bài thành các mảnh (loại, câu)."""
    lines = [l.rstrip() for l in (content or "").splitlines()]
    idx = [i for i, l in enumerate(lines) if l.strip()]
    if not idx:
        return []
    out = []
    first, last = idx[0], idx[-1]
    tail = set(idx[-3:])
    for i in idx:
        l = lines[i].strip()
        if l.startswith("#") and " " not in l.strip("# "):
            continue
        if i == first and len(l) <= 160:
            out.append(("hook", l))
        elif i in tail and CTA_RX.search(l):
            out.append(("cta", l))
        elif PRICE_RX.search(l) and NUM_RX.search(l) and len(l) <= 180:
            out.append(("price", l))
        elif SERVICE_RX.search(l) and len(l) <= 160:
            out.append(("service", l))
        elif BULLET_RX.match(l) and len(l) <= 180:
            out.append(("point", l))
        elif len(l) >= 60 and i not in (first, last):
            out.append(("story", l))
    return out


# ---------------------------------------------------------------- lưu kho
def is_mock(data: dict) -> bool:
    c = (data or {}).get("content") or ""
    return bool((data or {}).get("_mock")) or ("Xưởng hỗ trợ người bán online:" in c and "• Gửi mẫu thử trước khi nhập" in c)


def save(post_id: int | None, p: dict, angle: str, target: str, data: dict, source: str, agent_id: str = "lan") -> int | None:
    if not isinstance(data, dict) or not (data.get("content") or "").strip():
        return None
    lid = db.run("""INSERT INTO content_library(agent_id, post_id, product_id, product_name, category, angle, target_type, title,
                    content, hashtags, image_idea, source, status, leads, comments, edited, created_at)
                    VALUES (?,?,?,?,?,?,?,?,?,?,?,?,'draft',0,0,0,?)""",
                 (agent_id, post_id, p.get("id"), p.get("name"), p.get("category"), angle, target, data.get("title") or "",
                  data["content"], data.get("hashtags") or "", data.get("image_idea") or "", source, db.now()))
    if source in ("claude", "boss"):
        _extract(lid, p, angle, target, data, weight=2.0 if source == "boss" else 1.0)
    profile(refresh=True)
    return lid


def _facts() -> list[tuple[int, str]]:
    """Mô tả và điểm mạnh của các sản phẩm: dòng chứa chúng là thông tin sản phẩm, không phải phong cách."""
    out = []
    for r in db.q("SELECT id, description, selling_points FROM products"):
        for t in [r["description"] or ""] + re.split(r"[;,\n]", r["selling_points"] or ""):
            t = t.strip().lower()
            if len(t) >= 5:
                out.append((r["id"], t))
    return out


def _extract(lid: int, p: dict, angle: str, target: str, data: dict, weight: float = 1.0):
    contact = s().get("contact_info") or ""
    facts = _facts()
    for kind, line in split(data["content"], target):
        low = line.lower()
        if any(f in low for _, f in facts):
            continue  # dòng mô tả/điểm mạnh của một sản phẩm: Lan tự lấy từ thông tin sản phẩm khi viết
        tpl, specific = templatize(line, p, contact)
        if len(tpl) < 8:
            continue
        old = db.one("SELECT id FROM content_snippets WHERE kind=? AND text=?", (kind, tpl))
        if old:
            db.run("UPDATE content_snippets SET seen=seen+1, score=score+? WHERE id=?", (0.5 * weight, old["id"]))
            continue
        db.run("""INSERT INTO content_snippets(library_id, kind, angle, target_type, product_id, text, score, seen, uses, created_at)
                  VALUES (?,?,?,?,?,?,?,1,0,?)""", (lid, kind, angle, target, p.get("id") if specific else None, tpl, weight, db.now()))


def record_post(post_id: int, p: dict, angle: str, target: str, data: dict, source: str):
    try:
        db.run("UPDATE posts SET source=? WHERE id=?", (source, post_id))
        if source != "mock":
            save(post_id, p, angle, target, data, source)
    except Exception as e:
        print("[content_style]", e)


def on_boss_edit(post_id: int, new_content: str):
    """Sếp sửa bài: lưu bản sếp sửa vào kho, học nặng hơn (câu chữ sếp thích)."""
    post = db.one("SELECT * FROM posts WHERE id=?", (post_id,))
    if not post or not (new_content or "").strip():
        return
    p = db.one("SELECT * FROM products WHERE id=?", (post.get("product_id"),)) or {"id": None, "name": ""}
    db.run("UPDATE content_library SET edited=1 WHERE post_id=?", (post_id,))
    old = db.one("SELECT id FROM content_library WHERE post_id=? AND source='boss'", (post_id,))
    if old:
        db.run("UPDATE content_library SET content=? WHERE id=?", (new_content, old["id"]))
        db.run("DELETE FROM content_snippets WHERE library_id=?", (old["id"],))
        _extract(old["id"], p, post.get("angle") or "", post.get("target_type") or "group",
                 {"content": new_content}, weight=2.0)
        return
    save(post_id, p, post.get("angle") or "", post.get("target_type") or "group",
         {"title": post.get("title"), "content": new_content, "hashtags": post.get("hashtags")}, "boss")


def refresh_quality():
    """Cập nhật kết quả thật của bài vào kho và điểm của từng mảnh câu."""
    for r in db.q("""SELECT l.id, p.status, p.leads, p.comments FROM content_library l JOIN posts p ON p.id=l.post_id
                     WHERE l.post_id IS NOT NULL"""):
        st = "approved" if r["status"] in ("approved", "scheduled", "posting", "posted", "failed") else r["status"]
        db.run("UPDATE content_library SET status=?, leads=?, comments=? WHERE id=?",
               (st, r["leads"] or 0, r["comments"] or 0, r["id"]))
    db.run("""UPDATE content_snippets SET score = MAX(0.1, (SELECT
                CASE l.source WHEN 'boss' THEN 2.0 ELSE 1.0 END
                + CASE WHEN l.status IN ('approved','posted') THEN 1.0 WHEN l.status='rejected' THEN -1.5 ELSE 0 END
                + COALESCE(l.leads,0) * 2 + COALESCE(l.comments,0) * 0.2
              FROM content_library l WHERE l.id = content_snippets.library_id) + (seen - 1) * 0.5)
              WHERE library_id IN (SELECT id FROM content_library)""")


# ---------------------------------------------------------------- hồ sơ phong cách
def profile(refresh: bool = False) -> dict:
    if not refresh:
        try:
            pr = json.loads(s().get("lan_style") or "{}")
            if pr:
                return pr
        except Exception:
            pass
    rows = db.q("SELECT content, hashtags FROM content_library WHERE source IN ('claude','boss') ORDER BY id DESC LIMIT 200")
    if not rows:
        pr = {"posts": 0}
    else:
        words = [len((r["content"] or "").split()) for r in rows]
        lines = [len([l for l in (r["content"] or "").splitlines() if l.strip()]) for r in rows]
        emo = Counter(e for r in rows for e in EMOJI_RX.findall(r["content"] or ""))
        tags = Counter(t.lower() for r in rows for t in re.findall(r"#\w+", r["hashtags"] or ""))
        bullets = sum(1 for r in rows if any(BULLET_RX.match(l) for l in (r["content"] or "").splitlines()))
        pr = {"posts": len(rows), "avg_words": round(sum(words) / len(words)), "avg_lines": round(sum(lines) / len(lines)),
              "emoji_per_post": round(sum(emo.values()) / len(rows), 1), "top_emoji": [e for e, _ in emo.most_common(8)],
              "top_tags": [t for t, _ in tags.most_common(8)], "bullet_share": round(bullets / len(rows) * 100)}
    db.set_setting("lan_style", json.dumps(pr, ensure_ascii=False))
    return pr


def style_hint() -> str:
    """Nhắc Claude giữ phong cách quen của Lan (để kho học đồng nhất)."""
    pr = profile()
    if not pr.get("posts") or pr["posts"] < 5:
        return ""
    return (f"\nPhong cách quen thuộc của bạn (giữ đồng nhất): khoảng {pr['avg_words']} chữ, {pr['avg_lines']} dòng, "
            f"emoji hay dùng {' '.join(pr['top_emoji'][:5])}" + (", có gạch đầu dòng" if pr["bullet_share"] >= 50 else "") + ".")


# ---------------------------------------------------------------- tự viết
def counts() -> dict:
    c = {r["source"]: r["n"] for r in db.q("SELECT source, COUNT(*) n FROM content_library GROUP BY source")}
    k = {r["kind"]: r["n"] for r in db.q("SELECT kind, COUNT(*) n FROM content_snippets GROUP BY kind")}
    return {"library": c, "snippets": k}


def ready() -> tuple[bool, str]:
    c = counts()
    n = c["library"].get("claude", 0) + c["library"].get("boss", 0)
    need = int(s().get("self_write_min") or 12)
    hooks = c["snippets"].get("hook", 0)
    if n < need:
        return False, f"Lan đã học {n}/{need} bài Claude viết, cần thêm {need - n} bài nữa để tự viết"
    if hooks < 4 or c["snippets"].get("cta", 0) < 2:
        return False, "Chưa đủ câu mở đầu và câu kêu gọi đã học"
    return True, f"Đã học {n} bài, {hooks} câu mở đầu"


def quality() -> dict:
    refresh_quality()
    out = {}
    for src in ("claude", "self"):
        r = db.one("""SELECT COUNT(*) n, SUM(status IN ('approved','posted')) ok, SUM(status='rejected') bad,
                      SUM(edited) ed, AVG(leads) leads FROM content_library WHERE source=? AND status != 'draft'""", (src,))
        judged = (r["ok"] or 0) + (r["bad"] or 0)
        out[src] = {"judged": judged, "approve_rate": round((r["ok"] or 0) / judged * 100) if judged else None,
                    "leads_avg": round(r["leads"] or 0, 2), "edited": r["ed"] or 0}
    return out


def self_share() -> float:
    """Tỉ lệ bài Lan tự viết lúc này."""
    mode = s().get("self_write_mode", "auto")
    if mode == "off" or not ready()[0]:
        return 0.0
    if mode == "always":
        return 1.0
    from llm import llm
    if not llm.live:
        return 1.0  # chưa có khóa: tự viết theo phong cách đã học tốt hơn bài mẫu cố định
    c = counts()["library"]
    n = c.get("claude", 0) + c.get("boss", 0)
    need = int(s().get("self_write_min") or 12)
    share = min(0.8, 0.2 + (n - need) / 40)
    q = quality()
    if q["self"]["judged"] >= 5 and q["claude"]["approve_rate"]:
        ratio = (q["self"]["approve_rate"] or 0) / q["claude"]["approve_rate"]
        share *= max(0.3, min(1.2, ratio))
    return round(max(0.0, min(0.8, share)), 2)


def _pick(kind: str, angle: str, target: str, product_id, k: int = 1, exclude=()) -> list[dict]:
    rows = db.q("""SELECT * FROM content_snippets WHERE kind=? AND (product_id IS NULL OR product_id=?)""", (kind, product_id))
    rows = [r for r in rows if r["text"] not in exclude]
    if not rows:
        return []
    def w(r):
        x = max(0.1, r["score"])
        if angle and r["angle"] == angle:
            x *= 3
        if r["target_type"] == target:
            x *= 1.5
        return x / (1 + 0.3 * (r["uses"] or 0))
    out = []
    pool = rows[:]
    for _ in range(min(k, len(pool))):
        r = random.choices(pool, weights=[w(x) for x in pool])[0]
        out.append(r)
        pool.remove(r)
    return out


def _similar(a: str, b: str) -> float:
    wa, wb = set(re.findall(r"\w+", a.lower())), set(re.findall(r"\w+", b.lower()))
    return len(wa & wb) / max(1, len(wa | wb))


def compose(p: dict, angle: str, target: str, dry: bool = False) -> dict | None:
    """Lan tự viết một bài theo phong cách đã học (không gọi Claude)."""
    contact = s().get("contact_info") or ""
    pr = profile()
    emo = pr.get("top_emoji") or ["🌿", "✅", "💵", "📦"]
    recent = [r["content"] for r in db.q("SELECT content FROM posts ORDER BY id DESC LIMIT 40")]
    best = None
    for _ in range(6):
        hook = _pick("hook", angle, target, p.get("id"))
        if not hook:
            return None
        used = [hook[0]]
        lines = [fill(hook[0]["text"], p, contact), ""]
        if angle == "cau_chuyen" and (st := _pick("story", angle, target, p.get("id"))):
            lines += [fill(st[0]["text"], p, contact), ""]
            used += st
        lines.append(f"{emo[0]} {p.get('name')}: {p.get('description') or ''}".rstrip(": "))
        sps = [x.strip() for x in re.split(r"[;,\n]", p.get("selling_points") or "") if len(x.strip()) > 3][:3]
        bullet = next((e for e in emo if e in "✅✔️👉🔹•"), "✅")
        lines += [f"{bullet} {x[0].upper() + x[1:]}" for x in sps]
        pts = _pick("point", angle, target, p.get("id"), k=1 if sps else 2)
        lines += [t for t in (fill(x["text"], p, contact) for x in pts) if t.lower().strip("✅•-👉 ") not in
                  {l.lower().strip("✅•-👉 ") for l in lines}]
        used += pts
        price = _pick("price", angle, target, p.get("id"))
        price = [x for x in price if "{wp}" in x["text"] or x["product_id"] == p.get("id")]
        lines.append(fill(price[0]["text"], p, contact) if price else
                     f"💵 Giá sỉ: {p.get('wholesale_price') or 'inbox'} — giá bán lẻ gợi ý: {p.get('retail_price') or ''}".rstrip(" —:"))
        used += price[:1]
        if p.get("moq") and not any("{moq}" in x["text"] for x in used):
            lines.append(f"📦 Nhập tối thiểu: {p['moq']}")
        sv = _pick("service", angle, target, p.get("id"), k=random.choice([1, 2]))
        if sv:
            lines += [""] + [fill(x["text"], p, contact) for x in sv]
            used += sv
        cta = _pick("cta", angle, target, p.get("id"))
        if target != "group" and contact and not any("{contact}" in c["text"] for c in cta):
            lines += ["", f"Liên hệ: {contact}"]
        if cta:
            lines += ["", fill(cta[0]["text"], p, contact)]
            used += cta
        content = "\n".join(lines).strip()
        content = re.sub(r"\n{3,}", "\n\n", content)
        sim = max([_similar(content, r) for r in recent] or [0])
        if best is None or sim < best[1]:
            best = (content, sim, used, fill(hook[0]["text"], p, contact))
        if sim < 0.75:
            break
    content, sim, used, title = best
    if sim >= 0.9:
        return None  # quá giống bài cũ, để Claude viết
    for u in ([] if dry else used):
        db.run("UPDATE content_snippets SET uses=COALESCE(uses,0)+1 WHERE id=?", (u["id"],))
    tags = (pr.get("top_tags") or ["#nguonhangsi", "#taxuong", "#banhangonline"])[:4]
    return {"title": title[:150], "content": content, "hashtags": " ".join(tags),
            "image_idea": f"Ảnh thật {p.get('name')} tại xưởng, chữ to: GIÁ SỈ TẬN XƯỞNG", "_self": True,
            "_similar": round(sim, 2)}


def should_self_write(note: str = "") -> bool:
    if note and note.strip():
        from llm import llm
        if llm.live:
            return False  # yêu cầu riêng của sếp: nhờ Claude cho đúng ý
    sh = self_share()
    return sh > 0 and random.random() < sh


def migrate():
    """Lần đầu: đưa các bài Claude đã viết trước đây vào kho (bỏ bài mẫu có sẵn)."""
    if s().get("content_library_migrated") == "1":
        return
    for po in db.q("SELECT * FROM posts WHERE agent_id='lan' AND COALESCE(content,'')!='' ORDER BY id"):
        data = {"title": po["title"], "content": po["content"], "hashtags": po["hashtags"], "image_idea": po["image_idea"]}
        src = "mock" if is_mock(data) else "claude"
        db.run("UPDATE posts SET source=COALESCE(source, ?) WHERE id=?", (src, po["id"]))
        if src == "claude" and not db.one("SELECT id FROM content_library WHERE post_id=?", (po["id"],)):
            p = db.one("SELECT * FROM products WHERE id=?", (po["product_id"],)) or {"id": None, "name": ""}
            save(po["id"], p, po["angle"] or "", po["target_type"] or "group", data, "claude")
    db.set_setting("content_library_migrated", "1")


# ---------------------------------------------------------------- giao diện
def overview() -> dict:
    ok, why = ready()
    snip = {k: [dict(text=r["text"], score=round(r["score"], 1), uses=r["uses"], seen=r["seen"]) for r in db.q(
        "SELECT * FROM content_snippets WHERE kind=? ORDER BY score DESC, seen DESC LIMIT 6", (k,))] for k in ("hook", "cta", "point")}
    return {"counts": counts(), "ready": ok, "ready_text": why, "share": self_share(), "mode": s().get("self_write_mode", "auto"),
            "min": int(s().get("self_write_min") or 12), "profile": profile(), "quality": quality(), "top": snip,
            "recent": db.q("""SELECT id, source, product_name, angle, target_type, title, substr(content,1,400) content, status, leads,
                              comments, edited, created_at FROM content_library ORDER BY id DESC LIMIT 20"""),
            "kinds": KINDS, "sources": SOURCE_TXT}

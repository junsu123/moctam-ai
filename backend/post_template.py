"""Bài đăng nhóm theo MẪU CỦA SẾP: chỉ đăng bài tìm khách sỉ / gia công, không đăng bài linh tinh.

Sếp chốt: mọi bài đăng vào nhóm nick đã tham gia và nhóm nick quản lý đều theo mẫu sếp đưa (MỘC TÂM nhận gia công & sỉ
toàn quốc...). Mẫu sửa được ở trang Bài đăng → "Mẫu bài đăng nhóm". {số điện thoại} / {phone} thay bằng số Zalo báo giá.

Đăng cùng một bài nhiều lần dễ bị Facebook coi là spam, nên mỗi bài là một bản biến thể của mẫu: giữ nguyên ý và thông tin,
đổi emoji, đổi vài cách nói tương đương, đảo thứ tự gạch đầu dòng, đổi câu mở đầu và hashtag, có thể nhắc sản phẩm đang
bán chạy. Có khóa Claude thì Lan nhờ Claude viết lại (giữ đúng thông tin, không thêm giá); chưa có thì Lan tự biến thể theo
quy tắc. Bài theo mẫu được duyệt sẵn (nội dung do sếp viết), phần mềm vẫn tự bỏ mọi con số giá.
"""
import random
import re

import db
from knowledge import plain

DEFAULT_TEMPLATE = """MỘC TÂM
Nhận gia công & sỉ toàn quốc các dòng Trà Túi Lọc, Cafe Hòa Tan, Cốm, Bột Thiên Nhiên...
Sản xuất tại nhà máy đạt các tiêu chuẩn GMP – ISO – FDA – VSATTP
Hơn 100+ mã sản phẩm đa dạng:
Trà thảo mộc • Cafe • Ngũ cốc
Bột • Cốm • Detox • Các dòng thảo mộc...
Nhiều sản phẩm đang được thị trường và các nền tảng TMĐT quan tâm.
Nhận sỉ & gia công trọn gói:
• Bỏ sỉ toàn quốc
• Gia công thương hiệu riêng
• Thiết kế bao bì theo yêu cầu
• Hỗ trợ xây dựng & phát triển sản phẩm
• Hỗ trợ từ khâu sản xuất đến hoàn thiện sản phẩm
Phù hợp cho shop online, đại lý, nhà phân phối, người mới bắt đầu kinh doanh và các thương hiệu muốn phát triển sản phẩm riêng.
Cần catalog sản phẩm + bảng giá sỉ/gia công, ib trực tiếp để được tư vấn.
{số điện thoại}"""

PHONE_RX = re.compile(r"\{\s*(số điện thoại|so dien thoai|sđt|sdt|phone|zalo)\s*\}", re.I)
SKIP_LINE = re.compile(r"^\s*(ẩn bớt|xem thêm|see less|see more)\s*$", re.I)
# emoji gợi ý theo nội dung dòng (dòng đã có emoji thì có thể đổi sang emoji cùng nhóm)
EMO = [
    (r"gia công|sỉ toàn quốc|nhận sỉ", ["🏭", "📦", "🤝", "✨"]),
    (r"gmp|iso|fda|vsattp|tiêu chuẩn|nhà máy", ["✅", "🏅", "🛡️", "🔰"]),
    (r"mã sản phẩm|đa dạng", ["🌿", "🍃", "🧺", "📋"]),
    (r"trà|cafe|cà phê|ngũ cốc|bột|cốm|detox", ["🍵", "☕", "🌾", "🌱"]),
    (r"thị trường|tmđt|sàn|quan tâm", ["🔥", "📈", "🛒", "💡"]),
    (r"phù hợp|dành cho|hợp với", ["👉", "🎯", "🙌", "👥"]),
    (r"catalog|bảng giá|ib|inbox|tư vấn|liên hệ", ["📩", "💬", "📲", "📞"]),
]
SYN = [  # cách nói tương đương (chỉ đổi chữ, không đổi thông tin)
    (r"\bNhận gia công & sỉ toàn quốc\b", ["Nhận gia công & sỉ toàn quốc", "Chuyên gia công & phân phối sỉ toàn quốc",
                                         "Nhận gia công và cung cấp sỉ toàn quốc"]),
    (r"\bSản xuất tại nhà máy đạt các tiêu chuẩn\b", ["Sản xuất tại nhà máy đạt các tiêu chuẩn", "Sản xuất trực tiếp tại nhà máy đạt chuẩn",
                                                    "Nhà máy sản xuất đạt các tiêu chuẩn"]),
    (r"\bHơn 100\+ mã sản phẩm đa dạng\b", ["Hơn 100+ mã sản phẩm đa dạng", "Trên 100 mã sản phẩm đa dạng", "100+ mã sản phẩm phong phú"]),
    (r"\bNhiều sản phẩm đang được thị trường và các nền tảng TMĐT quan tâm\b",
     ["Nhiều sản phẩm đang được thị trường và các nền tảng TMĐT quan tâm", "Nhiều mã đang bán tốt trên thị trường và các sàn TMĐT",
      "Nhiều sản phẩm đang được các sàn TMĐT và thị trường săn đón"]),
    (r"\bNhận sỉ & gia công trọn gói\b", ["Nhận sỉ & gia công trọn gói", "Dịch vụ sỉ & gia công trọn gói", "Hỗ trợ sỉ & gia công trọn gói"]),
    (r"\bPhù hợp cho\b", ["Phù hợp cho", "Dành cho", "Rất hợp với"]),
    (r"\bib trực tiếp để được tư vấn\b", ["ib trực tiếp để được tư vấn", "inbox ngay để được tư vấn", "nhắn tin trực tiếp để được tư vấn"]),
    (r"\bBỏ sỉ toàn quốc\b", ["Bỏ sỉ toàn quốc", "Giao sỉ toàn quốc", "Bỏ sỉ khắp toàn quốc"]),
]
HOOKS = ["📣 TÌM ĐỐI TÁC SỈ & GIA CÔNG", "🤝 KẾT NỐI SHOP ONLINE – ĐẠI LÝ – NHÀ PHÂN PHỐI", "🔎 Shop nào đang tìm nguồn hàng tận xưởng?",
         "📢 Nguồn hàng tận nhà máy cho người bán online", "💼 Cơ hội hợp tác sỉ & làm thương hiệu riêng", ""]
TAGS = ["#nguonhangsi", "#giacong", "#tratuiloc", "#cafehoatan", "#ngucoc", "#botthiennhien", "#thuonghieurieng", "#bansi",
        "#nguonhangtanxuong", "#OEM", "#daily", "#kinhdoanhonline"]
EMOJI_START = re.compile(r"^[\U0001F300-\U0001FAFF\u2600-\u27BF\u2B50\u2705\u2194-\u21FF\u2190-\u2193]")


def s() -> dict:
    return db.get_settings()


def enabled() -> bool:
    return s().get("template_mode", "1") == "1"


def template() -> str:
    """Bài mẫu đầu tiên đang bật (giữ cho chỗ cũ dùng một mẫu)."""
    r = db.one("SELECT content FROM post_samples WHERE enabled=1 ORDER BY id LIMIT 1")
    return r["content"] if r else ((s().get("post_template") or "").strip() or DEFAULT_TEMPLATE)


def phone_line() -> str:
    import pricing
    return f"📞 Zalo/ĐT: {pricing.zalo()}"


def _lines(tpl: str) -> list[str]:
    out = [l.rstrip() for l in tpl.splitlines() if not SKIP_LINE.match(l)]
    while out and not out[-1].strip():
        out.pop()
    return out


def _has_emoji(l: str) -> bool:
    return bool(EMOJI_START.match(l.strip()))


def _emo_for(l: str, rnd: random.Random) -> str:
    p = l.lower()
    for rx, opts in EMO:
        if re.search(rx, p):
            return rnd.choice(opts)
    return ""


def variant(seed: int | str, tpl: str | None = None, extra_hooks: list[str] | None = None) -> str:
    """Một bản biến thể của mẫu (cùng seed -> cùng bài)."""
    import pricing
    rnd = random.Random(f"tpl-{seed}")
    lines = _lines(tpl or template())
    hot = [r["name"] for r in db.q("SELECT name FROM products WHERE hot=1 ORDER BY hot_since DESC, id LIMIT 3")]
    out, bullets = [], []
    sym = rnd.choice(["•", "✅", "✔️", "🔹", "▪️"])  # một kiểu gạch đầu dòng cho cả bài

    def flush():
        if bullets:
            if rnd.random() < 0.7:
                rnd.shuffle(bullets)
            out.extend(bullets)
            bullets.clear()
    for i, raw in enumerate(lines):
        l = raw.strip()
        if PHONE_RX.search(l):
            flush()
            out.append(PHONE_RX.sub(pricing.zalo(), l) if l != PHONE_RX.search(l).group(0) else phone_line())
            continue
        if not l:
            flush()
            out.append("")
            continue
        for rx, opts in SYN:
            if re.search(rx, l) and rnd.random() < 0.6:
                l = re.sub(rx, rnd.choice(opts), l)
        if l.startswith(("•", "-", "✅", "✔", "▪", "+")):
            bullets.append(f"{sym} {l.lstrip('•-✅✔️▪+ ').strip()}")
            continue
        flush()
        if i == 0 and len(l) <= 40 and not _has_emoji(l):  # tên thương hiệu / tiêu đề
            out.append(rnd.choice(["🌿 ", "✨ ", "🍃 ", "🏭 ", ""]) + l.upper() + rnd.choice(["", " 🌿", " ✨"]))
            continue
        if i == 0:
            out.append(l)
            continue
        if not _has_emoji(l) and (e := _emo_for(l, rnd)) and rnd.random() < 0.85:
            if out and out[-1].startswith(e):  # không lặp emoji dòng trên
                e = next((x for rx, opts in EMO for x in opts if x != e), e)
            l = f"{e} {l}"
        out.append(l)
    flush()
    first = next((x for x in out if x.strip()), "")
    letters = re.sub(r"[^A-Za-zÀ-ỹ]", "", first)
    headline = _has_emoji(first) or (letters and sum(c.isupper() for c in letters) / len(letters) > 0.7 and len(first) > 15)
    hook = rnd.choice(HOOKS) if not headline or rnd.random() < 0.3 else ""  # bài mẫu đã có tiêu đề thì ít khi thêm câu mở
    if hook:
        out = [hook, ""] + out
    if hot and rnd.random() < 0.6:  # nhắc sản phẩm sếp đang đẩy
        line = rnd.choice(["🔥 Đang được hỏi nhiều: ", "⭐ Sản phẩm nổi bật: ", "🔥 Bán chạy tháng này: "]) + ", ".join(hot[:rnd.choice([1, 2, 3])])
        cta = next((k for k, x in enumerate(out) if re.search(r"catalog|bảng giá|ib |inbox|tư vấn", x, re.I)), len(out))
        out.insert(cta, line)
    text = "\n".join(out).strip()
    if not pricing.has_contact(text):
        text += "\n" + phone_line()
    tags = rnd.sample(TAGS, 4)
    text += "\n\n" + " ".join(tags)
    return pricing.sanitize(text, add_contact=False)


# ---------------------------------------------------------------- thư viện bài mẫu của sếp
def samples(enabled_only: bool = False) -> list[dict]:
    rows = db.q("SELECT * FROM post_samples" + (" WHERE enabled=1" if enabled_only else "") + " ORDER BY id")
    stats = {r["sample_id"]: r for r in db.q("""SELECT sample_id, COUNT(*) made, SUM(status='posted') posted,
                                                COALESCE(SUM(comments),0) comments, COALESCE(SUM(leads),0) leads
                                                FROM posts WHERE sample_id IS NOT NULL GROUP BY sample_id""")}
    for r in rows:
        st = stats.get(r["id"]) or {}
        r.update(made=st.get("made") or 0, posted=st.get("posted") or 0, comments=st.get("comments") or 0, leads=st.get("leads") or 0)
        r["score"] = round((r["leads"] * 5 + r["comments"] + 1) / (r["posted"] + 2), 2)  # khách, bình luận trên mỗi bài đã đăng
    return rows


def seed():
    """Lần đầu: đưa mẫu sếp đã nhập (hoặc mẫu MỘC TÂM) vào thư viện."""
    if db.one("SELECT id FROM post_samples LIMIT 1"):
        return
    tpl = (s().get("post_template") or "").strip() or DEFAULT_TEMPLATE
    add_sample(tpl, "MỘC TÂM - nhận gia công & sỉ toàn quốc")


def add_sample(content: str, title: str = "") -> dict:
    content = "\n".join(l for l in (content or "").strip().splitlines() if not SKIP_LINE.match(l)).strip()
    if len(content) < 40:
        raise ValueError("Bài mẫu quá ngắn")
    if db.one("SELECT id FROM post_samples WHERE content=?", (content,)):
        raise ValueError("Bài mẫu này đã có trong thư viện")
    title = (title or next((l for l in content.splitlines() if l.strip()), ""))[:80].strip()
    sid = db.run("INSERT INTO post_samples(title, content, enabled, created_at, updated_at) VALUES (?,?,1,?,?)",
                 (title, content, db.now(), db.now()))
    _learn()
    return db.one("SELECT * FROM post_samples WHERE id=?", (sid,))


def import_many(text: str) -> int:
    """Dán nhiều bài một lần, các bài cách nhau bằng một dòng --- (hoặc ===)."""
    n = 0
    for chunk in re.split(r"\n\s*(?:-{3,}|={3,})\s*\n", "\n" + (text or "") + "\n"):
        try:
            add_sample(chunk)
            n += 1
        except ValueError:
            pass
    return n


def _learn():
    """Lan ghi vào sổ kiến thức: sếp có thư viện bài mẫu, viết theo cách của các bài đó."""
    import knowledge
    rows = samples(True)
    if not rows:
        return
    best = max(rows, key=lambda r: r["score"])
    txt = (f"Sếp có {len(rows)} bài mẫu đăng nhóm tìm khách sỉ, gia công. Mọi bài đăng nhóm phải viết theo các bài mẫu này: giữ đúng "
           "thông tin, không đăng bài linh tinh, không ghi giá, cuối bài là số Zalo báo giá. Mở đầu hay dùng: "
           + "; ".join(next((l for l in r["content"].splitlines() if l.strip()), "")[:60] for r in rows[:5])
           + (f". Bài mẫu ra nhiều khách nhất: “{best['title']}”." if best["posted"] else "."))
    old = db.one("SELECT id FROM knowledge WHERE agent_id='lan' AND topic='Thư viện bài mẫu đăng nhóm của sếp' AND status='active'")
    if old:
        db.run("UPDATE knowledge SET content=?, updated_at=? WHERE id=?", (txt, db.now(), old["id"]))
    else:
        knowledge.save("lan", "Thư viện bài mẫu đăng nhóm của sếp", txt, question="Viết bài đăng nhóm thế nào?",
                       keywords="bai mau dang nhom si gia cong sep", source="boss", kind="guide")


def pick(rnd: random.Random, rows: list[dict]) -> dict:
    """Chọn bài mẫu: mẫu ra khách nhiều được chọn nhiều hơn, vẫn thử đều các mẫu khác."""
    if rnd.random() < 0.25:
        return rnd.choice(rows)
    return rnd.choices(rows, weights=[r["score"] for r in rows], k=1)[0]


def _borrow_hooks(rows: list[dict]) -> list[str]:
    """Câu mở đầu học từ các bài mẫu khác (dòng đầu ngắn, có tính kêu gọi)."""
    out = []
    for r in rows:
        first = next((l.strip() for l in r["content"].splitlines() if l.strip()), "")
        if 8 <= len(first) <= 70 and re.search(r"(tìm|cần|nguồn|sỉ|đại lý|gia công|hợp tác|shop)", first, re.I):
            out.append(first)
    return out


def _ai_variants(n: int, rows: list[dict], rnd: random.Random) -> list[tuple[int, str]]:
    """Có khóa Claude: Lan đọc cả thư viện bài mẫu, viết lại hay hơn (giữ đúng thông tin của bài mẫu được chọn)."""
    from llm import llm
    if not (llm.live and s().get("template_ai", "1") == "1") or not rows:
        return []
    try:
        import pricing
        from agents import system_prompt
        lib = "\n\n".join(f"[MẪU {r['id']}]{' (ra nhiều khách)' if r['leads'] else ''}\n{r['content'][:1500]}" for r in rows[:8])
        picks = [pick(rnd, rows) for _ in range(n)]
        d = llm.json(system_prompt("lan", s()),
                     f"THƯ VIỆN BÀI MẪU của sếp (bài đăng nhóm Facebook tìm khách sỉ, khách gia công):\n{lib}\n\n"
                     f"Học cách viết của các bài mẫu (mở đầu, bố cục, gạch đầu dòng, lời kêu gọi). Rồi viết {n} bài MỚI, bài thứ i viết lại "
                     f"từ mẫu số: {[r['id'] for r in picks]}. Viết hay hơn, tự nhiên hơn, mỗi bài khác nhau để đăng nhiều nhóm không bị coi là "
                     "trùng. GIỮ ĐÚNG thông tin của mẫu đó (thương hiệu, dòng sản phẩm, tiêu chuẩn, dịch vụ, đối tượng); không thêm thông tin "
                     "mới, không ghi giá, không hứa công dụng chữa bệnh. Dòng liên hệ cuối ghi đúng: "
                     f"\"{phone_line()}\". Trả JSON {{\"posts\": [{{\"sample_id\": số, \"content\": \"...\"}}]}}.",
                     mock=None, max_tokens=800 * n, task="posts")
        ids = {r["id"] for r in rows}
        out = []
        for i, it in enumerate((d or {}).get("posts", [])):
            c = it.get("content") if isinstance(it, dict) else it if isinstance(it, str) else None
            sid = it.get("sample_id") if isinstance(it, dict) else None
            sid = sid if sid in ids else picks[min(i, len(picks) - 1)]["id"]
            if c and len(c) > 120:
                c = pricing.sanitize(PHONE_RX.sub(pricing.zalo(), c), add_contact=False)
                if not pricing.has_contact(c):
                    c += "\n" + phone_line()
                out.append((sid, c))
        return out[:n]
    except Exception as e:
        print("[template ai]", e)
        return []


def _recent_keys(days: int = 14) -> set:
    rows = db.q("SELECT content FROM posts WHERE source='template' AND created_at >= date('now', ?)", (f"-{days} day",))
    return {plain(r["content"] or "")[:160] for r in rows}


def make_posts(n: int, status: str = "approved", target_type: str = "group") -> list[dict]:
    """Lan làm n bài từ thư viện bài mẫu của sếp (mỗi bài một bản viết lại), lưu sẵn để Tuấn xếp lịch."""
    if n <= 0:
        return []
    import workflows
    seed()
    rows = samples(True)
    if not rows:
        return []
    rnd = random.Random()
    out = _ai_variants(n, rows, rnd)
    seen = _recent_keys() | {plain(c)[:160] for _, c in out}
    k = 0
    while len(out) < n and k < n * 20:
        r = pick(rnd, rows)
        c = variant(f"{rnd.random()}-{k}", r["content"])
        k += 1
        if plain(c)[:160] in seen:
            continue
        seen.add(plain(c)[:160])
        out.append((r["id"], c))
    import ceo_review
    by_id = {r["id"]: r for r in rows}
    made, redo = [], 0
    for sid, c in out[:n]:
        rv = ceo_review.review(c, sample=by_id.get(sid, {}).get("content"))  # CEO chấm trước khi cho đăng
        tries = 0
        while not rv["ok"] and tries < 4:  # chưa đạt: Lan viết lại bản khác từ đúng bài mẫu đó
            tries += 1
            redo += 1
            c2 = variant(f"{rnd.random()}-redo-{tries}", by_id[sid]["content"]) if sid in by_id else c
            rv2 = ceo_review.review(c2, sample=by_id.get(sid, {}).get("content"))
            if rv2["score"] > rv["score"]:
                c, rv = c2, rv2
        if not rv["ok"]:
            db.log("ceo", "Duyệt bài", f"Không duyệt bài viết lại từ mẫu #{sid}: {ceo_review.note(rv)[:200]}")
            continue
        title = next((l for l in c.splitlines() if l.strip()), "")[:80]
        pid = db.run("""INSERT INTO posts(agent_id, product_id, target_type, angle, title, content, hashtags, image_idea, status,
                        created_at, source, sample_id) VALUES ('lan', NULL, ?, 'mau_sep', ?, ?, '', ?, ?, ?, 'template', ?)""",
                     (target_type, title, c, "Ảnh catalog / nhà máy / dây chuyền sản xuất, sản phẩm thật", status, db.now(), sid))
        ceo_review.save(pid, rv)
        made.append(db.one("SELECT * FROM posts WHERE id=?", (pid,)))
    if made:
        db.log("lan", "Viết bài", f"Viết lại {len(made)} bài đăng nhóm từ thư viện {len(rows)} bài mẫu của sếp, CEO chấm "
               f"{min(m['review_score'] for m in made)}–{max(m['review_score'] for m in made)} điểm rồi mới duyệt"
               + (f" (Lan viết lại {redo} lần theo góp ý của CEO)" if redo else ""))
        workflows.set_status("lan", "idle", f"Vừa viết {len(made)} bài từ bài mẫu")
    return made


def preview(n: int = 2, tpl: str | None = None, sample_id: int | None = None) -> list[str]:
    rnd = random.Random()
    if tpl:
        return [variant(f"{rnd.random()}-{i}", tpl) for i in range(n)]
    seed()
    rows = samples(True)
    if sample_id:
        rows = [r for r in rows if r["id"] == sample_id] or rows
    if not rows:
        return []
    out = []
    for i in range(n):
        r = rows[i % len(rows)] if sample_id else pick(rnd, rows)
        out.append(variant(f"{rnd.random()}-{i}", r["content"]))
    return out

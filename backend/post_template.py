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
    return (s().get("post_template") or "").strip() or DEFAULT_TEMPLATE


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


def variant(seed: int | str, tpl: str | None = None) -> str:
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
        if i == 0 and len(l) <= 40:  # tên thương hiệu
            out.append(rnd.choice(["🌿 ", "✨ ", "🍃 ", "🏭 ", ""]) + l.upper() + rnd.choice(["", " 🌿", " ✨"]))
            continue
        if not _has_emoji(l) and (e := _emo_for(l, rnd)) and rnd.random() < 0.85:
            if out and out[-1].startswith(e):  # không lặp emoji dòng trên
                e = next((x for rx, opts in EMO for x in opts if x != e), e)
            l = f"{e} {l}"
        out.append(l)
    flush()
    hook = rnd.choice(HOOKS)
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


def _ai_variants(n: int, tpl: str) -> list[str]:
    from llm import llm
    if not (llm.live and s().get("template_ai", "1") == "1"):
        return []
    try:
        import pricing
        from agents import system_prompt
        d = llm.json(system_prompt("lan", s()),
                     f"Đây là MẪU BÀI của sếp để đăng nhóm Facebook tìm khách sỉ và khách gia công:\n\"\"\"\n{tpl}\n\"\"\"\n"
                     f"Viết {n} bản khác nhau của mẫu này để đăng nhiều nhóm mà không bị Facebook coi là trùng lặp. GIỮ ĐÚNG mọi thông tin "
                     "(tên thương hiệu, dòng sản phẩm, tiêu chuẩn, dịch vụ, đối tượng phù hợp); chỉ được đổi câu chữ, emoji, thứ tự gạch đầu "
                     "dòng, câu mở đầu. Không thêm thông tin mới, không ghi giá, không hứa công dụng. Dòng liên hệ cuối ghi đúng: "
                     f"\"{phone_line()}\". Trả JSON {{\"posts\": [\"...\"]}}.", mock=None, max_tokens=700 * n, task="posts")
        out = []
        for p in (d or {}).get("posts", []):
            if isinstance(p, str) and len(p) > 120:
                p = pricing.sanitize(PHONE_RX.sub(pricing.zalo(), p), add_contact=False)
                if not pricing.has_contact(p):
                    p += "\n" + phone_line()
                out.append(p)
        return out[:n]
    except Exception as e:
        print("[template ai]", e)
        return []


def _recent_keys(days: int = 14) -> set:
    rows = db.q("SELECT content FROM posts WHERE source='template' AND created_at >= date('now', ?)", (f"-{days} day",))
    return {plain(r["content"] or "")[:160] for r in rows}


def make_posts(n: int, status: str = "approved", target_type: str = "group") -> list[dict]:
    """Lan làm n bài theo mẫu của sếp (mỗi bài một biến thể), lưu sẵn để Tuấn xếp lịch."""
    if n <= 0:
        return []
    import workflows
    tpl = template()
    texts = _ai_variants(n, tpl)
    seen = _recent_keys() | {plain(t)[:160] for t in texts}
    base = random.randint(1, 10_000_000)
    k = 0
    while len(texts) < n and k < n * 20:
        t = variant(f"{base}-{k}", tpl)
        k += 1
        key = plain(t)[:160]
        if key in seen:
            continue
        seen.add(key)
        texts.append(t)
    made = []
    for t in texts[:n]:
        title = next((l for l in t.splitlines() if l.strip()), "")[:80]
        pid = db.run("""INSERT INTO posts(agent_id, product_id, target_type, angle, title, content, hashtags, image_idea, status,
                        created_at, source) VALUES ('lan', NULL, ?, 'mau_sep', ?, ?, '', ?, ?, ?, 'template')""",
                     (target_type, title, t, "Ảnh catalog / nhà máy / dây chuyền sản xuất, sản phẩm thật", status, db.now()))
        made.append(db.one("SELECT * FROM posts WHERE id=?", (pid,)))
    if made:
        db.log("lan", "Viết bài", f"Làm {len(made)} bài đăng nhóm theo mẫu của sếp (mỗi bài một biến thể, chỉ nội dung tìm khách sỉ, gia công)")
        workflows.set_status("lan", "idle", f"Vừa làm {len(made)} bài theo mẫu")
    return made


def preview(n: int = 2, tpl: str | None = None) -> list[str]:
    base = random.randint(1, 10_000_000)
    return [variant(f"{base}-{i}", tpl) for i in range(n)]

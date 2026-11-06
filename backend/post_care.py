"""Bảo: chăm bài đã đăng. Mỗi ngày rà soát các bài đã đăng còn hiển thị, xếp cho đúng nick đã đăng vào lại bài,
bình luận 1 ảnh bất kỳ trong thư mục ảnh kèm một câu ngắn do Bảo tự viết (gọi Claude nếu có khóa) và dòng liên hệ
của sếp (mặc định "Cần hàng liên hệ Zalo 0386992326").

Mỗi câu khác nhau (Facebook coi bình luận giống hệt lặp lại là spam), không hứa công dụng chữa bệnh, không quá 20 chữ.
Việc vào bài, đính kèm ảnh, gửi bình luận vẫn do browser_poster._do_bump làm theo Luật Facebook (trần lượt up/nick/ngày).
"""
import random
import re

import db
from knowledge import plain

DEFAULT_CONTACT = "Cần hàng liên hệ Zalo 0386992326"

OPEN = ["Xưởng vừa ra mẻ {p} mới", "Ảnh thật {p} tại xưởng hôm nay", "{p} đóng gói xong, sẵn hàng giao ngay",
        "Mẻ {p} sáng nay vừa đóng thùng", "Hàng {p} chuẩn xưởng, giá tận gốc", "Nhận sỉ {p} số lượng lớn",
        "{p} còn hàng sỉ nhé cả nhà", "Lô {p} mới về kho, ảnh thật", "Shop online cần nguồn {p} thì ghé xưởng",
        "Gửi cả nhà ảnh {p} thực tế tại xưởng", "{p} có sẵn, nhận in nhãn theo yêu cầu", "Bạn nào đang bán {p} online ghé xem"]
TAIL = ["", " 🌿", " ✨", ", ship toàn quốc", ", có hóa đơn đầy đủ", ", giá sỉ tốt cho shop mới", ", nhận đơn từ 1 thùng",
        " 📦", ", hỗ trợ ảnh và video cho shop"]
GENERIC = "trà, ngũ cốc"


def s() -> dict:
    return db.get_settings()


def contact() -> str:
    c = (s().get("bump_contact") or "").strip()
    return c[:120]


def mode() -> str:
    return "list" if s().get("bump_text_mode") == "list" else "ai"


def _short_name(name: str) -> str:
    n = re.sub(r"\s*[\(\[].*?[\)\]]", "", name or "")
    n = re.split(r"\s[-–|/]\s|[,;:]", n)[0].strip(" -–.")
    words = n.split()[:7]
    while len(words) > 2 and re.fullmatch(r"\d+\w*|loại|vị|gói|túi", words[-1].lower()):  # không cắt dở "25 loại hạt"
        words.pop()
    return " ".join(words).lower() if words else GENERIC


def _recent(aid: int | None, days: int = 14) -> set[str]:
    rows = db.q("SELECT text FROM bumps WHERE created_at >= datetime('now', ?)" + (" AND account_id=?" if aid else ""),
                (f"-{days} days", *([aid] if aid else [])))
    c = plain(contact())
    return {plain(r["text"] or "").replace(c, "").strip(" -👉·.,") for r in rows if r.get("text")}


def _clean(line: str) -> str:
    line = re.sub(r"\s+", " ", str(line or "")).strip().strip('"“”').strip()
    if re.search(r"(?i)zalo|sđt|sdt|hotline|\d[\d .]{7,}\d", line):  # câu tự ghi số liên hệ: bỏ, Bảo tự gắn dòng liên hệ của sếp
        return ""
    words = line.split()
    return " ".join(words[:20])


def _ok(line: str) -> bool:
    if len(line) < 8:
        return False
    try:
        import fb_policy
        return not any(i["level"] == "high" for i in fb_policy.check_text(line))
    except Exception:
        return True


def _offline(names: list[str], n: int, avoid: set[str]) -> list[str]:
    """Ghép câu từ mẫu: mỗi câu trong lượt một kiểu mở đầu khác nhau, không trùng câu nick đã dùng gần đây."""
    out, opens, tries = [], [], 0
    while len(out) < n and tries < n * 60:
        tries += 1
        if not opens:
            opens = random.sample(OPEN, len(OPEN))
        tpl = opens[-1]
        p = names[len(out)] if len(out) < len(names) else (random.choice(names) if names else GENERIC)
        line = tpl.format(p=p)
        line = line[0].upper() + line[1:] + ("" if "," in line else random.choice(TAIL))
        k = plain(line)
        if k in avoid or any(plain(x) == k for x in out):
            if tries % 3 == 0:
                opens.pop()
            continue
        opens.pop()
        out.append(line)
    while len(out) < n:  # hết biến thể: chấp nhận lặp lại câu cũ
        line = random.choice(OPEN).format(p=random.choice(names) if names else GENERIC)
        out.append(line[0].upper() + line[1:])
    return out


# ---------------------------------------------------------------- Bảo học viết câu từ mẫu Claude
# Mỗi câu Claude viết được lưu làm mẫu (comment_samples, source='claude'). Bảo tách mẫu thành khuôn câu (thay tên sản phẩm
# bằng {p}) và hai vế (trước / sau dấu phẩy) để tự ghép câu mới cùng giọng. Khi còn học, mỗi lượt Bảo nộp câu tự viết cho
# Claude chấm điểm 1–10 trong cùng lần gọi (không tốn thêm lượt gọi). Đạt Master thì Bảo tự viết, không gọi Claude nữa.
SKILL_LEVELS = [  # (tên, số mẫu Claude tối thiểu, tỷ lệ câu tự viết đạt ≥8 điểm trong 40 câu chấm gần nhất, số câu đã chấm tối thiểu)
    ("Học việc", 0, 0, 0),
    ("Thạo việc", 20, 60, 10),
    ("Giỏi", 50, 80, 20),
    ("Master", 100, 90, 40),
]
PASS = 8


def skill() -> dict:
    """Tay nghề viết câu bình luận của Bảo."""
    n = db.one("SELECT COUNT(*) n FROM comment_samples WHERE source='claude'")["n"]
    graded = db.q("SELECT score FROM comment_samples WHERE source='bao' AND score IS NOT NULL ORDER BY id DESC LIMIT 40")
    rate = round(sum(1 for g in graded if g["score"] >= PASS) * 100 / len(graded)) if graded else 0
    avg = round(sum(g["score"] for g in graded) / len(graded), 1) if graded else None
    lv = 0
    for i, (_, need, pct, cnt) in enumerate(SKILL_LEVELS):
        if n >= need and rate >= pct and len(graded) >= cnt:
            lv = i
    st = s()
    nxt = SKILL_LEVELS[lv + 1] if lv + 1 < len(SKILL_LEVELS) else None
    return {"level": lv, "name": SKILL_LEVELS[lv][0], "master": lv == len(SKILL_LEVELS) - 1, "samples": n,
            "graded": len(graded), "pass_rate": rate, "avg": avg,
            "next": {"name": nxt[0], "samples": nxt[1], "pass_rate": nxt[2], "graded": nxt[3]} if nxt else None,
            "calls": int(st.get("bao_claude_calls") or 0), "saved": int(st.get("bao_calls_saved") or 0)}


def _template(text: str, pname: str) -> str:
    """Thay tên sản phẩm trong câu bằng {p}; câu không nhắc tên sản phẩm giữ nguyên."""
    if pname and pname != GENERIC:
        m = re.search(re.escape(pname), text, flags=re.I)
        if m:
            return text[:m.start()] + "{p}" + text[m.end():]
    return text


def learn(texts: list[str], names: list[str], source: str = "claude", scores: list | None = None) -> int:
    """Lưu câu mẫu (Claude viết) hoặc câu Bảo tự viết kèm điểm Claude chấm."""
    n = 0
    for i, t in enumerate(texts):
        t = (t or "").strip()
        if not t:
            continue
        pname = names[i] if i < len(names) else GENERIC
        sc = None
        if scores and i < len(scores):
            try:
                sc = max(0, min(10, int(round(float(scores[i])))))
            except (TypeError, ValueError):
                sc = None
        if source == "claude" and db.one("SELECT id FROM comment_samples WHERE source='claude' AND text=?", (t,)):
            continue
        db.run("""INSERT INTO comment_samples(text, template, product, source, score, created_at) VALUES (?,?,?,?,?,?)""",
               (t, _template(t, pname), pname, source, sc, db.now()))
        n += 1
    return n


def _learned() -> tuple[list[str], list[str], list[str]]:
    """Khuôn câu, vế đầu, vế sau học từ mẫu Claude và câu tự viết đạt điểm cao."""
    rows = db.q("""SELECT template FROM comment_samples WHERE source='claude' OR (source='bao' AND score >= ?)
                   ORDER BY id DESC LIMIT 400""", (PASS,))
    tpls, heads, tails = [], [], []
    for r in rows:
        t = (r["template"] or "").strip()
        if not t:
            continue
        tpls.append(t)
        if ", " in t:
            h, tail = t.split(", ", 1)
            if len(h.split()) >= 3:
                heads.append(h)
                tails.append(", " + tail)
    return tpls, heads, tails


def _fill(tpl: str, p: str) -> str:
    line = tpl.replace("{p}", p)
    return line[0].upper() + line[1:] if line else line


def self_write(names: list[str], n: int, avoid: set[str]) -> list[str]:
    """Bảo tự viết từ những gì đã học (không gọi Claude). Chưa học được gì thì dùng mẫu gốc."""
    tpls, heads, tails = _learned()
    if len(tpls) < 5:
        return _offline(names, n, avoid)
    out, used, tries = [], set(), 0
    while len(out) < n and tries < n * 80:
        tries += 1
        p = names[len(out)] if len(out) < len(names) else (random.choice(names) if names else GENERIC)
        if heads and random.random() < 0.45:  # ghép vế đầu câu này với vế sau câu khác
            tpl = random.choice(heads) + random.choice(tails)
        else:
            tpl = random.choice(tpls)
        if "{p}" not in tpl and random.random() < 0.6:  # ưu tiên câu nhắc đúng sản phẩm của bài
            continue
        line = _fill(tpl, p)
        k = plain(line)
        if k in avoid or k in used or not (5 <= len(line.split()) <= 20) or not _ok(line):
            continue
        used.add(k)
        out.append(line)
    if len(out) < n:
        out += _offline(names[len(out):], n - len(out), avoid | used)
    return out


def _claude(names: list[str], avoid: set[str], drafts: list[str]) -> tuple[list[str], list]:
    """Một lần gọi Claude: viết câu mới cho từng bài + chấm điểm câu Bảo tự viết."""
    from llm import llm
    import agents
    ask = ("Viết " + str(len(names)) + " câu bình luận NGẮN (8–18 chữ) để sale bình luận kèm ảnh sản phẩm vào bài đăng "
           "bán sỉ của chính mình trong nhóm Facebook, giúp bài nổi lên. Mỗi câu ứng với một sản phẩm theo thứ tự: "
           + "; ".join(f"{i + 1}. {n}" for i, n in enumerate(names))
           + ". Yêu cầu: giọng tự nhiên như người bán thật, mỗi câu khác hẳn nhau (mở đầu khác, ý khác: ảnh thật, mẻ mới, "
           "sẵn hàng, giao nhanh, nhận in nhãn...), nhắc đúng tên sản phẩm, có dấu phẩy ngăn hai ý, tối đa 1 biểu tượng cảm xúc, "
           "KHÔNG ghi số điện thoại hay Zalo (sẽ tự gắn sau), không hứa chữa bệnh, giảm cân, cam kết 100%, không viết hoa cả "
           "câu, không hashtag."
           + (" Tránh lặp các câu đã dùng: " + " | ".join(list(avoid)[:12]) if avoid else "")
           + ((" Ngoài ra chấm điểm 1–10 các câu Bảo (nhân viên mới) tự viết dưới đây theo đúng các yêu cầu trên "
               "(tự nhiên, ngắn, đúng sản phẩm, không vi phạm): " + " | ".join(f"{i + 1}. {d}" for i, d in enumerate(drafts))
               + '. Trả về JSON {"lines": ["..."], "scores": [số, ...]} (scores theo đúng thứ tự câu của Bảo).')
              if drafts else ' Trả về JSON {"lines": ["...", "..."]}.'))
    d = llm.json(agents.system_prompt("bao", s(), with_learning=False), ask, mock=None, max_tokens=900, task="posts")
    db.set_setting("bao_claude_calls", str(int(s().get("bao_claude_calls") or 0) + 1))
    d = d or {}
    got = [_clean(x) for x in d.get("lines") or [] if isinstance(x, str)]
    return got, d.get("scores") or []


def lines(posts: list[dict], aid: int | None = None) -> list[str]:
    """Câu ngắn (chưa có dòng liên hệ) cho từng bài, khác nhau và khác các lần up gần đây của nick."""
    return [x[:1].upper() + x[1:] for x in _lines(posts, aid)]


def _lines(posts: list[dict], aid: int | None = None) -> list[str]:
    if not posts:
        return []
    names = []
    for p in posts:
        pr = db.one("SELECT name FROM products WHERE id=?", (p.get("product_id"),)) if p.get("product_id") else None
        names.append(_short_name(pr["name"]) if pr else GENERIC)
    avoid = _recent(aid)
    if mode() == "list":
        texts = [t.strip() for t in (s().get("bump_texts") or "").splitlines() if t.strip()] or [""]
        fresh = [t for t in texts if plain(t) not in avoid] or texts
        return [random.choice(fresh) for _ in posts]
    from llm import llm
    sk = skill()
    if sk["master"] or not llm.live:  # Master: tự viết, không gọi Claude; chưa có khóa: tự viết từ những gì đã học
        if sk["master"] and llm.live:
            db.set_setting("bao_calls_saved", str(sk["saved"] + 1))
        return self_write(names, len(posts), avoid)
    out = []
    drafts = self_write(names, min(len(names), 6), avoid)  # bài kiểm tra: Bảo tự viết, Claude chấm
    try:
        got, scores = _claude(names, avoid, drafts)
        seen = set()
        keep_names = []
        for i, x in enumerate(got):
            k = plain(x)
            if _ok(x) and k not in avoid and k not in seen:
                out.append(x)
                seen.add(k)
                keep_names.append(names[i] if i < len(names) else GENERIC)
        new = learn(out, keep_names, "claude")
        if scores:
            learn(drafts, names, "bao", scores)
        before = sk["name"]
        after = skill()
        try:
            import learning
            learning.award("bao", 2 * new, "Học câu mẫu Claude")
        except Exception:
            pass
        if after["name"] != before:
            db.log("bao", "Lên tay nghề", f"Viết câu bình luận: {before} → {after['name']} ({after['samples']} mẫu Claude, "
                   f"{after['pass_rate']}% câu tự viết đạt)" + (". Từ nay Bảo tự viết, không gọi Claude nữa" if after["master"] else ""))
    except Exception as e:
        print("[post_care claude]", e)
    if len(out) < len(posts):
        out += self_write(names[len(out):], len(posts) - len(out), avoid | {plain(x) for x in out})
    return out[:len(posts)]


def relearn() -> dict:
    """Sếp thấy câu Bảo tự viết chưa ổn: quay lại gọi Claude, chấm lại từ đầu (mẫu đã học vẫn giữ)."""
    db.run("UPDATE comment_samples SET score=NULL WHERE source='bao'")
    db.log("bao", "Học lại", "Sếp cho Bảo học lại cách viết câu bình luận: gọi Claude và chấm điểm lại từ đầu")
    return skill()


def samples(limit: int = 30) -> list[dict]:
    return db.q("SELECT id, text, product, source, score, created_at FROM comment_samples ORDER BY id DESC LIMIT ?", (limit,))


def compose(line: str) -> str:
    """Câu Bảo viết + dòng liên hệ của sếp, trên một dòng (Enter trong ô bình luận là gửi luôn)."""
    c = contact()
    line = (line or "").strip()
    if c and plain(c) in plain(line):
        return line
    if line and c:
        line = line.rstrip(" .")
        return f"{line}{'.' if line[-1:].isalnum() else ''} 👉 {c}"
    return line or c


def texts_for(posts: list[dict], aid: int | None = None) -> list[str]:
    return [compose(x) for x in lines(posts, aid)]


def preview(n: int = 3) -> dict:
    posts = db.q("SELECT * FROM posts WHERE status='posted' ORDER BY posted_at DESC LIMIT ?", (n,)) or \
        [{"product_id": p["id"]} for p in db.q("SELECT id FROM products ORDER BY COALESCE(hot,0) DESC, id LIMIT ?", (n,))]
    from llm import llm
    return {"texts": texts_for(posts or [{}] * n), "mode": mode(), "contact": contact(), "ai": llm.live, "skill": skill()}


def overview() -> dict:
    today = db.today()
    b = db.one("""SELECT SUM(status='done') done, SUM(status='scheduled') waiting, SUM(status='failed') failed,
                  SUM(status='skipped') skipped FROM bumps WHERE created_at >= ?""", (today,))
    alive = db.one("""SELECT COUNT(*) n FROM posts WHERE status='posted' AND COALESCE(permalink_status,'')!='removed'
                      AND COALESCE(bump_enabled,1)=1""")["n"]
    return {"today": {k: b[k] or 0 for k in ("done", "waiting", "failed", "skipped")}, "alive": alive,
            "contact": contact(), "mode": mode(), "skill": skill(), "samples": samples(12)}

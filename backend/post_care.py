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
        line = line[0].upper() + line[1:] + random.choice(TAIL)
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


def lines(posts: list[dict], aid: int | None = None) -> list[str]:
    """Câu ngắn (chưa có dòng liên hệ) cho từng bài, khác nhau và khác các lần up gần đây của nick."""
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
    out = []
    from llm import llm
    if llm.live:
        import agents
        ask = ("Viết " + str(len(posts)) + " câu bình luận NGẮN (8–18 chữ) để sale bình luận kèm ảnh sản phẩm vào bài đăng "
               "bán sỉ của chính mình trong nhóm Facebook, giúp bài nổi lên. Mỗi câu ứng với một sản phẩm theo thứ tự: "
               + "; ".join(f"{i + 1}. {n}" for i, n in enumerate(names))
               + ". Yêu cầu: giọng tự nhiên như người bán thật, mỗi câu khác hẳn nhau (mở đầu khác, ý khác: ảnh thật, mẻ mới, "
               "sẵn hàng, giao nhanh, nhận in nhãn...), tối đa 1 biểu tượng cảm xúc, KHÔNG ghi số điện thoại hay Zalo "
               "(sẽ tự gắn sau), không hứa chữa bệnh, giảm cân, cam kết 100%, không viết hoa cả câu, không hashtag."
               + (" Tránh lặp các câu đã dùng: " + " | ".join(list(avoid)[:12]) if avoid else "")
               + ' Trả về JSON {"lines": ["...", "..."]}.')
        try:
            d = llm.json(agents.system_prompt("bao", s(), with_learning=False), ask, mock=None, max_tokens=600, task="posts")
            got = [_clean(x) for x in (d or {}).get("lines") or [] if isinstance(x, str)]
            seen = set()
            for x in got:
                k = plain(x)
                if _ok(x) and k not in avoid and k not in seen:
                    out.append(x)
                    seen.add(k)
        except Exception as e:
            print("[post_care claude]", e)
    if len(out) < len(posts):
        out += _offline(names[len(out):], len(posts) - len(out), avoid | {plain(x) for x in out})
    return out[:len(posts)]


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
    return {"texts": texts_for(posts or [{}] * n), "mode": mode(), "contact": contact(), "ai": llm.live}


def overview() -> dict:
    today = db.today()
    b = db.one("""SELECT SUM(status='done') done, SUM(status='scheduled') waiting, SUM(status='failed') failed,
                  SUM(status='skipped') skipped FROM bumps WHERE created_at >= ?""", (today,))
    alive = db.one("""SELECT COUNT(*) n FROM posts WHERE status='posted' AND COALESCE(permalink_status,'')!='removed'
                      AND COALESCE(bump_enabled,1)=1""")["n"]
    return {"today": {k: b[k] or 0 for k in ("done", "waiting", "failed", "skipped")}, "alive": alive,
            "contact": contact(), "mode": mode()}

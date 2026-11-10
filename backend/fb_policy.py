"""Luật Facebook cho cả đội: học luật, kiểm bài theo luật, giữ nhịp đăng an toàn cho từng nick,
rút kinh nghiệm khi nick bị chặn / bài bị gỡ, và theo dõi khi Meta đổi chính sách.

Nguồn luật (đọc ngày 06/11/2026):
- Meta Community Standards: Spam, Account Integrity, Authentic Identity Representation, Inauthentic Behavior
  https://transparency.meta.com/policies/community-standards/
- Meta 04/2025 "Cracking down on spammy content on Facebook": caption dài, quá nhiều hashtag, mạng lưới nhiều tài khoản
  đăng cùng nội dung, bình luận dàn dựng bị giảm hiển thị.
- Meta Restricting accounts: vi phạm cộng dồn thành "gậy" (strike), bị chặn tính năng 1, 3, 7, 30 ngày rồi khóa hẳn.
- Luật Quảng cáo VN (sửa đổi, hiệu lực 01/01/2026): thực phẩm thuộc nhóm quản lý chặt; không quảng cáo công dụng
  chữa bệnh; không dùng từ "nhất", "số 1", "duy nhất" khi không có tài liệu chứng minh.

Điểm quan trọng nhất, nói thẳng: Account Integrity cấm dùng tài khoản "qua phương tiện tự động như script, trừ khi qua kênh
được phép". Đăng bằng nick cá nhân qua Chrome tự động vẫn có rủi ro bị khóa dù làm đúng mọi giới hạn bên dưới. Kênh tự động
được phép: Fanpage qua Graph API (đã có ở Cài đặt → Fanpage).
"""
import difflib
import hashlib
import json
import re
import threading
from datetime import datetime, timedelta

import db

# ---------------------------------------------------------------- nguồn chính sách theo dõi định kỳ
SOURCES = [
    {"key": "spam", "name": "Meta: Spam (tiêu chuẩn cộng đồng)", "kind": "meta",
     "url": "https://transparency.meta.com/policies/community-standards/spam/"},
    {"key": "account_integrity", "name": "Meta: Tính toàn vẹn của tài khoản", "kind": "meta",
     "url": "https://transparency.meta.com/policies/community-standards/account-integrity/"},
    {"key": "authentic_identity", "name": "Meta: Danh tính thật", "kind": "meta",
     "url": "https://transparency.meta.com/policies/community-standards/authentic-identity-representation/"},
    {"key": "inauthentic", "name": "Meta: Hành vi không xác thực", "kind": "meta",
     "url": "https://transparency.meta.com/policies/community-standards/inauthentic-behavior/"},
    {"key": "restricting", "name": "Meta: Cách hạn chế tài khoản (gậy, chặn tính năng)", "kind": "meta",
     "url": "https://transparency.meta.com/enforcement/taking-action/restricting-accounts/"},
    {"key": "commerce", "name": "Meta: Chính sách thương mại", "kind": "meta",
     "url": "https://transparency.meta.com/policies/commerce-policies/"},
    {"key": "spam_news", "name": "Meta: Tin siết nội dung spam (04/2025)", "kind": "meta",
     "url": "https://about.fb.com/news/2025/04/cracking-down-spammy-content-facebook/"},
]

# ---------------------------------------------------------------- bộ luật cả đội làm theo
CATS = {"rate": "Nhịp đăng & hành vi", "content": "Nội dung bài", "account": "Tài khoản", "group": "Hội nhóm",
        "law": "Quảng cáo thực phẩm (luật Việt Nam)"}
HOW = {"limit": "Tự giới hạn", "check": "Tự kiểm bài", "learn": "Tự rút kinh nghiệm", "guide": "Nguyên tắc"}

RULES = [
    {"id": "automation", "cat": "account", "how": "guide", "level": "high", "src": "account_integrity",
     "title": "Tự động hóa tài khoản cá nhân là rủi ro lớn nhất",
     "rule": "Meta cấm tạo hoặc dùng tài khoản bằng phương tiện tự động như script, trừ khi qua kênh được phép. "
             "Đăng bằng nick cá nhân qua Chrome tự động vẫn có thể bị khóa dù làm đúng mọi giới hạn.",
     "do": "Ưu tiên Fanpage qua Graph API (kênh được phép). Nick cá nhân: ít bài, nhịp chậm, nội dung khác nhau, người thật kiểm tra."},
    {"id": "real_identity", "cat": "account", "how": "guide", "level": "high", "src": "authentic_identity",
     "title": "Mỗi nick là một người thật, tên thật",
     "rule": "Không dùng tài khoản giả, tên giả, mua bán hay cho mượn tài khoản; không tạo tài khoản mới để lách khi bị chặn.",
     "do": "Chỉ thêm nick là tài khoản thật của nhân viên. Nick bị chặn thì nghỉ, không tạo nick mới thay."},
    {"id": "high_frequency", "cat": "rate", "how": "limit", "level": "high", "src": "spam",
     "title": "Không đăng, bình luận, tham gia nhóm với tần suất rất cao",
     "rule": "Meta cấm đăng, chia sẻ, tương tác hoặc tạo nhóm, trang với tần suất rất cao, dù thủ công hay tự động.",
     "do": "Mỗi nick có trần bài/ngày, khoảng cách tối thiểu giữa 2 bài, trần bình luận up bài và trần xin vào nhóm (bảng giới hạn)."},
    {"id": "repetitive", "cat": "content", "how": "check", "level": "high", "src": "spam",
     "title": "Không đăng nội dung lặp lại",
     "rule": "Meta có thể hạn chế cả nick đăng ít nếu có dấu hiệu spam như nội dung lặp lại.",
     "do": "Mỗi bài là một biến thể khác; bài giống bài nick đã đăng trong 7 ngày, hoặc giống bài nick khác đăng hôm nay, bị chặn."},
    {"id": "network", "cat": "account", "how": "check", "level": "high", "src": "inauthentic",
     "title": "Không dùng nhiều nick đăng cùng một nội dung",
     "rule": "Mạng lưới nhiều tài khoản cùng chia sẻ một nội dung bị giảm hiển thị hoặc xử lý như hành vi không xác thực.",
     "do": "Không 2 nick đăng bài giống nhau cùng ngày; các nick không bình luận dàn dựng vào bài của nhau."},
    {"id": "hashtags", "cat": "content", "how": "check", "level": "medium", "src": "spam_news",
     "title": "Không nhồi hashtag, caption không lan man",
     "rule": "Bài có caption dài lan man, quá nhiều hashtag chỉ được hiện cho người theo dõi (giảm tiếp cận).",
     "do": "Tối đa 5 hashtag mỗi bài, đúng chủ đề."},
    {"id": "engagement_bait", "cat": "content", "how": "check", "level": "medium", "src": "spam_news",
     "title": "Không câu tương tác",
     "rule": "Kêu gọi like, share, tag bạn bè, bình luận số để nhận quà là câu tương tác, bị giảm hiển thị.",
     "do": "Kêu gọi đúng việc: inbox / nhắn Zalo để nhận catalog, báo giá."},
    {"id": "links", "cat": "content", "how": "check", "level": "high", "src": "spam",
     "title": "Không dùng link rút gọn, link chuyển hướng",
     "rule": "Link gây hiểu nhầm, che giấu đích đến là dấu hiệu spam.",
     "do": "Không đặt link rút gọn (bit.ly, tinyurl...). Liên hệ bằng số Zalo."},
    {"id": "going_fast", "cat": "rate", "how": "limit", "level": "high", "src": "restricting",
     "title": "Tránh bị chặn vì \u201cthao tác quá nhanh\u201d",
     "rule": "Xin vào nhiều nhóm liền nhau, bình luận giống nhau ở nhiều bài trong vài giây, kết bạn hàng loạt sẽ bị chặn tạm thời.",
     "do": "Mỗi nick xin vào tối đa 2 nhóm/ngày, mỗi lượt up bài cách nhau vài phút và lời up khác nhau, không kết bạn hàng loạt."},
    {"id": "friend_requests", "cat": "rate", "how": "limit", "level": "high", "src": "restricting",
     "title": "Kết bạn: ít, đúng người, gửi bằng tay",
     "rule": "Gửi nhiều lời mời kết bạn cho người lạ, nhiều lời mời bị bỏ qua hoặc bấm \u201cKhông biết người này\u201d làm nick bị chặn "
             "tính năng kết bạn, nặng thì khóa. Công cụ tự động gửi lời mời hàng loạt là spam.",
     "do": "Tuấn chỉ gợi ý người đang hoạt động trong nhóm chung, hợp tệp khách; sale tự bấm Thêm bạn bè, tối đa 10 lời mời/nick/ngày "
           "(nick mới một nửa), dừng khi tỷ lệ đồng ý thấp."},
    {"id": "comment_others", "cat": "rate", "how": "limit", "level": "high", "src": "spam",
     "title": "Bình luận vào bài người khác: đúng người, viết riêng, sếp duyệt",
     "rule": "Bình luận quảng cáo vào bài không liên quan, cùng một câu ở nhiều bài, bình luận liên tục cả ngày lẫn đêm là spam: "
             "nhóm xóa bình luận, chặn thành viên, Facebook giới hạn tính năng bình luận rồi khóa nick.",
     "do": "Bảo chỉ bình luận bài đang hỏi mua / hỏi nguồn hàng hợp ngành (kèm 1 ảnh), và chào nhẹ người đang bán hàng online "
           "(chỉ chữ, bám vào điều họ viết, mỗi người một lần, tối đa 2 câu/nick/ngày, không chào ở nhóm cấm bán hàng hay nhóm từng "
           "xóa bình luận chào). Mỗi câu viết riêng, sếp duyệt trước khi gửi; mỗi nick tối đa 5 câu/ngày (nick mới một nửa), cách "
           "nhau 45–90 phút, chỉ trong giờ làm; lướt bảng tin nhóm 2 lượt/ngày (nick mới 1), chỉ đọc."},
    {"id": "strikes", "cat": "account", "how": "learn", "level": "high", "src": "restricting",
     "title": "Vi phạm cộng dồn thành \u201cgậy\u201d",
     "rule": "Mỗi vi phạm cộng một gậy; gậy tăng dần dẫn tới chặn đăng 1, 3, 7, 30 ngày rồi khóa hẳn. Gậy hết hạn sau khoảng 90 ngày.",
     "do": "Nick bị chặn: nghỉ 3 ngày, sau đó chạy nửa giới hạn trong 7 ngày. Tuấn ghi lại nick đã làm gì trước khi bị chặn để rút kinh nghiệm."},
    {"id": "group_rules", "cat": "group", "how": "learn", "level": "medium", "src": None,
     "title": "Tôn trọng nội quy từng nhóm",
     "rule": "Quản trị viên nhóm được xóa bài, báo cáo, chặn thành viên; bị báo cáo nhiều làm nick dễ bị Facebook hạn chế.",
     "do": "Nhóm cấm bán hàng thì không đăng. Bài bị gỡ 2 lần trong 30 ngày ở cùng nhóm: ngừng đăng nhóm đó 30 ngày."},
    {"id": "same_group", "cat": "group", "how": "limit", "level": "medium", "src": "spam",
     "title": "Không đăng dồn vào một nhóm",
     "rule": "Đăng nhiều bài vào cùng một nhóm trong ngày dễ bị thành viên và quản trị viên báo cáo spam.",
     "do": "Một nick đăng tối đa 1 bài/nhóm trong 24 giờ (trừ nhóm mình quản lý)."},
    {"id": "health_claims", "cat": "law", "how": "check", "level": "high", "src": None,
     "title": "Không hứa công dụng chữa bệnh",
     "rule": "Thực phẩm không được quảng cáo chữa, trị, phòng bệnh hay thay thế thuốc (Luật Quảng cáo, Luật An toàn thực phẩm; "
             "Meta cũng hạn chế nội dung sức khỏe gây hiểu nhầm).",
     "do": "Chỉ nói thành phần, quy trình, tiêu chuẩn nhà máy, hương vị, cách dùng."},
    {"id": "superlatives", "cat": "law", "how": "check", "level": "medium", "src": None,
     "title": "Không dùng \u201cnhất\u201d, \u201csố 1\u201d khi không chứng minh được",
     "rule": "Luật Quảng cáo cấm dùng từ \u201cnhất\u201d, \u201cduy nhất\u201d, \u201ctốt nhất\u201d, \u201csố một\u201d khi không có tài liệu hợp pháp chứng minh.",
     "do": "Thay bằng sự thật kiểm chứng được: \u201cnhà máy đạt GMP\u201d, \u201chơn 100 mã sản phẩm\u201d."},
    {"id": "guarantee", "cat": "law", "how": "check", "level": "medium", "src": None,
     "title": "Không cam kết tuyệt đối",
     "rule": "\u201cCam kết 100%\u201d, \u201can toàn tuyệt đối\u201d, \u201ckhông tác dụng phụ\u201d là quảng cáo gây hiểu nhầm.",
     "do": "Nói điều xưởng làm được và chứng minh được."},
]

HEALTH_RX = re.compile(r"chữa (khỏi|bệnh|dứt|trị)|trị (bệnh|dứt điểm|khỏi|tận gốc)|điều trị|khỏi hẳn|thần dược|thay (thế )?thuốc|"
                       r"đặc trị|phòng (ngừa )?bệnh|hết bệnh|tiêu diệt (tế bào|virus)|ung thư|tiểu đường|huyết áp|"
                       r"giảm \d+\s*(kg|ký|cân)|giảm cân cấp tốc|bác sĩ (khuyên|khuyến)", re.I)
SUPER_RX = re.compile(r"(tốt|rẻ|ngon|uy tín|chất lượng|lớn|hàng đầu) nhất|duy nhất|số\s*(1|một)\b|no\.?\s*1\b|đứng đầu", re.I)
GUARANTEE_RX = re.compile(r"cam kết\s*100\s*%|100\s*%\s*(hiệu quả|khỏi|an toàn)|an toàn tuyệt đối|không (có )?tác dụng phụ|"
                          r"hoàn tiền nếu không (khỏi|hiệu quả)", re.I)
BAIT_RX = re.compile(r"(like|thích)\s*(và|\+|&)?\s*(share|chia sẻ)|tag\s*\d*\s*(người|bạn)|gắn thẻ\s*\d*\s*(người|bạn)|"
                     r"(comment|cmt|bình luận)\s*[\"“]?\s*\d+\s*[\"”]?\s*(để|nhận)|share (bài|về tường) để nhận|"
                     r"chia sẻ (bài|về tường) để nhận|ai (thấy|đọc) thì (like|share)", re.I)
SHORT_RX = re.compile(r"\b(bit\.ly|tinyurl\.com|goo\.gl|t\.ly|cutt\.ly|shorturl\.at|rb\.gy|is\.gd|ow\.ly|s\.id|tiny\.cc|bom\.so|"
                      r"link1s|shope\.ee|vt\.tiktok\.com)/\S*", re.I)
HASHTAG_RX = re.compile(r"(?<![\w&])#[^\s#]{2,}")


def s() -> dict:
    return db.get_settings()


def _i(k: str, d: int) -> int:
    try:
        return int(float(s().get(k) or d))
    except (TypeError, ValueError):
        return d


def enabled() -> bool:
    return s().get("fbp_enabled", "1") != "0"


def custom_rules() -> list[dict]:
    try:
        return [r for r in json.loads(s().get("fbp_custom_rules") or "[]") if isinstance(r, dict)]
    except Exception:
        return []


def all_rules() -> list[dict]:
    out = [dict(r) for r in RULES]
    for c in custom_rules():
        out.append({"id": c.get("id"), "cat": c.get("cat") or "content", "how": "check" if c.get("phrases") else "guide",
                    "level": c.get("level") or "medium", "src": None, "title": c.get("title", ""), "rule": c.get("text", ""),
                    "do": ("Bài có cụm: " + ", ".join(c["phrases"]) + " sẽ bị chặn") if c.get("phrases") else "", "custom": True})
    return out


# ---------------------------------------------------------------- kiểm bài theo luật
def _plain(t: str) -> str:
    import unicodedata
    t = unicodedata.normalize("NFD", (t or "").lower()).replace("đ", "d")
    return re.sub(r"\s+", " ", re.sub(r"[^\w\s]", " ", "".join(ch for ch in t if unicodedata.category(ch) != "Mn"))).strip()


def _similar(a: str, b: str) -> float:
    wa, wb = set(_plain(a).split()), set(_plain(b).split())
    if not wa or not wb:
        return 0.0
    return len(wa & wb) / len(wa | wb)


def check_text(text: str, post_id: int | None = None, account_id: int | None = None) -> list[dict]:
    """Các điểm bài vi phạm luật: [{rule, level (high|medium), msg, hit}]. high = không cho đăng."""
    t = text or ""
    out = []

    def add(rule, level, msg, hit=""):
        out.append({"rule": rule, "level": level, "msg": msg, "hit": hit})
    for m in HEALTH_RX.finditer(t):  # bỏ qua câu phủ định: "không hứa chữa bệnh", "tránh nói thay thế thuốc"
        before = t[max(0, m.start() - 40):m.start()].lower()
        if re.search(r"(không|chẳng|cấm|tránh|đừng|chớ|không được|không phải là)\s+([\wÀ-ỹ]+\s+){0,5}$", before):
            continue
        add("health_claims", "high", "hứa công dụng chữa bệnh, giảm cân (thực phẩm không được quảng cáo như thuốc)", m.group(0))
        break
    if (m := GUARANTEE_RX.search(t)):
        add("guarantee", "medium", "cam kết tuyệt đối, dễ thành quảng cáo gây hiểu nhầm", m.group(0))
    if (m := SUPER_RX.search(t)):
        add("superlatives", "medium", "dùng từ \u201cnhất\u201d / \u201csố 1\u201d khi không có chứng minh", m.group(0))
    if (m := BAIT_RX.search(t)):
        add("engagement_bait", "medium", "câu tương tác (like/share/tag/bình luận số) bị Facebook giảm hiển thị", m.group(0))
    if (m := SHORT_RX.search(t)):
        add("links", "high", "link rút gọn / chuyển hướng là dấu hiệu spam", m.group(0))
    tags = HASHTAG_RX.findall(t)
    mx = _i("fbp_hashtags_max", 5)
    if len(tags) > mx:
        add("hashtags", "high" if len(tags) > mx * 2 else "medium", f"{len(tags)} hashtag (tối đa {mx})", " ".join(tags[:6]))
    if len(t) > _i("fbp_caption_max", 2500):
        add("hashtags", "medium", f"bài quá dài ({len(t)} ký tự), Facebook giảm hiển thị caption lan man")
    letters = [c for c in t if c.isalpha()]
    if len(letters) > 80 and sum(c.isupper() for c in letters) / len(letters) > 0.5:
        add("engagement_bait", "medium", "viết hoa quá nhiều, trông như spam")
    for c in custom_rules():
        for ph in c.get("phrases") or []:
            if ph and _plain(ph) and _plain(ph) in _plain(t):
                add(c.get("id") or "custom", c.get("level") or "high", f"sếp cấm: {c.get('title') or ph}", ph)
                break
    # nội dung lặp lại: cùng nick 7 ngày, nick khác cùng ngày
    warn, block = float(s().get("fbp_similar_max") or 0.85), float(s().get("fbp_similar_block") or 0.95)
    since = (db.clock() - timedelta(days=7)).strftime("%Y-%m-%d")
    rows = db.q("""SELECT id, content, account_id, posted_at, scheduled_for FROM posts WHERE id != ? AND status IN ('scheduled','posting','posted')
                   AND COALESCE(posted_at, scheduled_for, created_at) >= ? ORDER BY id DESC LIMIT 200""", (post_id or 0, since))
    today = db.today()
    for r in rows:
        sim = _similar(t, r["content"] or "")
        if sim < warn:
            continue
        lvl = "high" if sim >= block else "medium"
        when = r["posted_at"] or r["scheduled_for"] or ""
        if account_id and r["account_id"] == account_id:
            add("repetitive", lvl, f"giống {round(sim * 100)}% bài #{r['id']} nick này đăng trong 7 ngày (nội dung lặp lại)")
            break
        if r["account_id"] and r["account_id"] != account_id and when.startswith(today):
            add("network", lvl, f"giống {round(sim * 100)}% bài #{r['id']} nick khác đăng hôm nay (nhiều nick cùng nội dung)")
            break
    return out


def summary(issues: list[dict]) -> str:
    return "; ".join(f"{i['msg']}" + (f" (\u201c{i['hit']}\u201d)" if i.get("hit") else "") for i in issues)


def blocking(issues: list[dict]) -> list[dict]:
    return [i for i in issues if i["level"] == "high"]


def prompt_rule() -> str:
    """Luật ngắn gọn gắn vào lời dặn của mọi agent khi viết bài, trả lời khách."""
    if not enabled():
        return ""
    lines = ["Không hứa chữa bệnh, trị bệnh, giảm cân, thay thuốc; chỉ nói thành phần, quy trình, tiêu chuẩn nhà máy.",
             "Không dùng \u201cnhất\u201d, \u201csố 1\u201d, \u201cduy nhất\u201d, \u201ccam kết 100%\u201d, \u201ckhông tác dụng phụ\u201d.",
             f"Tối đa {_i('fbp_hashtags_max', 5)} hashtag; không câu like/share/tag/bình luận số; không link rút gọn.",
             "Mỗi bài là một cách viết khác, không chép y bài cũ; tôn trọng nội quy nhóm."]
    lines += [f"{c.get('title')}: {c.get('text')}" for c in custom_rules() if c.get("title")]
    return "\n\nLUẬT FACEBOOK CẢ ĐỘI PHẢI GIỮ (tránh nick bị khóa):\n- " + "\n- ".join(lines)


# ---------------------------------------------------------------- giới hạn an toàn cho từng nick
def factor(acc: dict) -> float:
    """Hệ số giới hạn của nick: nick mới, nick vừa bị chặn chạy nửa giới hạn."""
    f = 1.0
    now = db.now()
    if acc.get("factor_until") and acc["factor_until"] > now:
        f = min(f, float(acc.get("limit_factor") or 0.5))
    created = (acc.get("created_at") or "")[:10]
    if created:
        try:
            age = (db.clock() - datetime.strptime(created, "%Y-%m-%d")).days
            if age < _i("fbp_new_nick_days", 14):
                f = min(f, float(s().get("fbp_new_nick_factor") or 0.5))
        except ValueError:
            pass
    return f


def limits(acc: dict) -> dict:
    f = factor(acc)
    cap = lambda k, d: max(1, int(_i(k, d) * f))
    own = int(acc.get("max_posts_per_day") or 0)  # trần riêng sếp đặt cho nick (nếu thấp hơn)
    posts = cap("fbp_posts_day", 6)  # nick mới / vừa bị chặn: giảm trần chung, không nhân thêm lần nữa vào trần riêng
    if own:
        posts = min(posts, own)
    gap = max(_i("fbp_gap_minutes", 30), int(acc.get("min_gap_minutes") or 0))
    return {"posts": posts, "bumps": cap("fbp_bumps_day", 6), "joins": max(0, int(_i("fbp_joins_day", 2) * f)),
            "friends": max(0, int(_i("fbp_friends_day", 10) * f)),
            "gap": int(gap / f) if f < 1 else gap, "factor": f}


def used_today(aid: int) -> dict:
    today = db.today()
    posts = db.one("""SELECT COUNT(*) n, MAX(posted_at) last FROM posts WHERE account_id=? AND status IN ('posted','posting')
                      AND COALESCE(posted_at, scheduled_for) >= ?""", (aid, today))
    bumps = db.one("SELECT COUNT(*) n, MAX(done_at) last FROM bumps WHERE account_id=? AND status='done' AND done_at >= ?",
                   (aid, today))
    try:
        joins = db.one("""SELECT COUNT(*) n FROM account_groups WHERE account_id=? AND status IN ('joined','requested','pending')
                          AND COALESCE(requested_at, updated_at) >= ?""", (aid, today))["n"]
    except Exception:
        joins = 0
    try:
        friends = db.one("SELECT COUNT(*) n FROM friend_suggestions WHERE account_id=? AND sent_at >= ?", (aid, today))["n"]
    except Exception:
        friends = 0
    return {"posts": posts["n"], "last_post": posts["last"], "bumps": bumps["n"], "last_bump": bumps["last"], "joins": joins,
            "friends": friends}


def allow(aid: int, kind: str, group_id: int | None = None) -> tuple[bool, str, str | None]:
    """Nick còn được làm việc này không. Trả về (được?, lý do, giờ sớm nhất làm được)."""
    if not enabled():
        return True, "", None
    acc = db.one("SELECT * FROM fb_accounts WHERE id=?", (aid,))
    if not acc:
        return True, "", None
    now = db.clock()
    if acc.get("rest_until") and acc["rest_until"] > db.now():
        return False, f"nick đang nghỉ sau sự cố tới {acc['rest_until'][11:16]} {acc['rest_until'][8:10]}/{acc['rest_until'][5:7]}", acc["rest_until"]
    L, U = limits(acc), used_today(aid)
    tomorrow = (now + timedelta(days=1)).strftime("%Y-%m-%d ") + (acc.get("active_from") or "08:00") + ":00"
    if kind == "post":
        if U["posts"] >= L["posts"]:
            return False, f"nick đã đăng {U['posts']}/{L['posts']} bài hôm nay (trần an toàn)", tomorrow
        last = max([x for x in (U["last_post"], acc.get("last_post_at")) if x] or [""])
        if last:
            nxt = datetime.strptime(last[:19], "%Y-%m-%d %H:%M:%S") + timedelta(minutes=L["gap"])
            if nxt > now:
                return False, f"chưa đủ {L['gap']} phút kể từ bài trước của nick", nxt.strftime("%Y-%m-%d %H:%M:%S")
        if group_id:
            g = db.one("SELECT COALESCE(managed,0) managed FROM groups WHERE id=?", (group_id,)) or {"managed": 0}
            hrs = _i("fbp_same_group_hours", 24)
            if not g["managed"]:
                since = (now - timedelta(hours=hrs)).strftime("%Y-%m-%d %H:%M:%S")
                r = db.one("""SELECT MAX(posted_at) t FROM posts WHERE account_id=? AND group_id=? AND status='posted' AND posted_at >= ?""",
                           (aid, group_id, since))
                if r and r["t"]:
                    nxt = datetime.strptime(r["t"][:19], "%Y-%m-%d %H:%M:%S") + timedelta(hours=hrs)
                    return False, f"nick đã đăng vào nhóm này trong {hrs} giờ qua", nxt.strftime("%Y-%m-%d %H:%M:%S")
            rest = rest_group_until(group_id)
            if rest:
                return False, f"nhóm đang tạm ngừng đăng tới {rest[8:10]}/{rest[5:7]} (bài bị quản trị viên gỡ nhiều lần)", None
    elif kind == "bump":
        if U["bumps"] >= L["bumps"]:
            return False, f"nick đã up {U['bumps']}/{L['bumps']} lượt hôm nay (trần an toàn)", tomorrow
    elif kind == "join":
        if U["joins"] >= L["joins"]:
            return False, f"nick đã xin vào {U['joins']}/{L['joins']} nhóm hôm nay", tomorrow
    return True, "", None


def remaining(aid: int, kind: str) -> int:
    acc = db.one("SELECT * FROM fb_accounts WHERE id=?", (aid,))
    if not acc or not enabled():
        return 999
    if acc.get("rest_until") and acc["rest_until"] > db.now():
        return 0
    L, U = limits(acc), used_today(aid)
    key = {"post": "posts", "bump": "bumps", "join": "joins"}[kind]
    return max(0, L[key] - U[key])


# ---------------------------------------------------------------- sự cố và bài học
def _activity_24h(aid: int) -> dict:
    since = (db.clock() - timedelta(hours=24)).strftime("%Y-%m-%d %H:%M:%S")
    posts = db.one("SELECT COUNT(*) n FROM posts WHERE account_id=? AND status='posted' AND posted_at >= ?", (aid, since))["n"]
    bumps = db.one("SELECT COUNT(*) n FROM bumps WHERE account_id=? AND status='done' AND done_at >= ?", (aid, since))["n"]
    try:
        joins = db.one("SELECT COUNT(*) n FROM account_groups WHERE account_id=? AND COALESCE(requested_at, updated_at) >= ?",
                       (aid, since))["n"]
    except Exception:
        joins = 0
    return {"posts": posts, "bumps": bumps, "joins": joins}


def on_block(aid: int, reason: str) -> dict:
    """Nick bị chặn / kiểm tra: ghi sự cố, cho nghỉ, giảm nửa giới hạn một thời gian, rút bài học."""
    act = _activity_24h(aid)
    rest_days, after_days = _i("fbp_rest_days", 3), _i("fbp_after_days", 7)
    rest_until = (db.clock() + timedelta(days=rest_days)).strftime("%Y-%m-%d %H:%M:%S")
    factor_until = (db.clock() + timedelta(days=rest_days + after_days)).strftime("%Y-%m-%d %H:%M:%S")
    db.run("UPDATE fb_accounts SET rest_until=?, limit_factor=?, factor_until=? WHERE id=?",
           (rest_until, float(s().get("fbp_after_factor") or 0.5), factor_until, aid))
    L = limits(db.one("SELECT * FROM fb_accounts WHERE id=?", (aid,)) or {})
    fast = re.search(r"quá nhanh|too fast|tạm thời|temporarily|blocked", reason or "", re.I)
    lesson = (f"24 giờ trước khi bị chặn nick đã đăng {act['posts']} bài, up {act['bumps']} lượt, xin vào {act['joins']} nhóm. "
              + ("Facebook báo thao tác quá nhanh: " if fast else "")
              + f"Nghỉ {rest_days} ngày, sau đó chạy {int(L.get('factor', 0.5) * 100)}% giới hạn trong {after_days} ngày.")
    db.run("""INSERT INTO fb_incidents(account_id, kind, detail, posts_24h, bumps_24h, joins_24h, lesson, created_at)
              VALUES (?,?,?,?,?,?,?,?)""", (aid, "block", (reason or "")[:500], act["posts"], act["bumps"], act["joins"], lesson, db.now()))
    # nhiều nick bị chặn trong 7 ngày: cả đội siết giới hạn chung
    since = (db.clock() - timedelta(days=7)).strftime("%Y-%m-%d")
    n = db.one("SELECT COUNT(DISTINCT account_id) n FROM fb_incidents WHERE kind='block' AND created_at >= ?", (since,))["n"]
    if n >= 2 and s().get("fbp_auto_tighten", "1") == "1":
        cur = _i("fbp_posts_day", 6)
        if cur > 3 and s().get("fbp_tightened_at", "")[:10] < since:
            db.set_setting("fbp_posts_day", str(cur - 1))
            db.set_setting("fbp_tightened_at", db.now())
            lesson += f" {n} nick bị chặn trong 7 ngày: Tuấn hạ trần chung xuống {cur - 1} bài/nick/ngày."
            db.log("tuan", "Siết nhịp đăng", f"{n} nick bị chặn trong 7 ngày, hạ trần chung từ {cur} xuống {cur - 1} bài/nick/ngày")
    db.log("tuan", "Rút kinh nghiệm nick bị chặn", lesson)
    return {"lesson": lesson, "rest_until": rest_until}


def on_removed(post: dict) -> None:
    """Bài bị gỡ / ẩn: ghi sự cố; cùng nhóm bị gỡ nhiều lần thì tạm ngừng đăng nhóm đó."""
    gid = post.get("group_id")
    db.run("""INSERT INTO fb_incidents(account_id, kind, detail, group_id, post_id, lesson, created_at) VALUES (?,?,?,?,?,?,?)""",
           (post.get("account_id"), "removed", f"Bài #{post['id']} không còn hiển thị (có thể quản trị viên gỡ hoặc Facebook ẩn)",
            gid, post["id"], "", db.now()))
    if not gid:
        return
    since = (db.clock() - timedelta(days=30)).strftime("%Y-%m-%d")
    n = db.one("SELECT COUNT(*) n FROM fb_incidents WHERE kind='removed' AND group_id=? AND created_at >= ?", (gid, since))["n"]
    if n >= _i("fbp_removed_max", 2):
        until = (db.clock() + timedelta(days=_i("fbp_group_rest_days", 30))).strftime("%Y-%m-%d %H:%M:%S")
        db.run("UPDATE groups SET policy_rest_until=? WHERE id=?", (until, gid))
        g = db.one("SELECT name FROM groups WHERE id=?", (gid,)) or {"name": f"#{gid}"}
        lesson = f"Nhóm “{g['name']}” gỡ {n} bài trong 30 ngày: ngừng đăng nhóm này tới {until[8:10]}/{until[5:7]}, xem lại nội quy nhóm."
        db.run("UPDATE fb_incidents SET lesson=? WHERE id=(SELECT MAX(id) FROM fb_incidents)", (lesson,))
        db.log("tuan", "Tạm ngừng nhóm hay gỡ bài", lesson)


def rest_group_until(gid: int) -> str | None:
    r = db.one("SELECT policy_rest_until t FROM groups WHERE id=?", (gid,))
    return r["t"] if r and r["t"] and r["t"] > db.now() else None


# ---------------------------------------------------------------- theo dõi thay đổi chính sách
_watch_lock = threading.Lock()


def _norm_text(t: str) -> str:
    lines = [re.sub(r"\s+", " ", ln).strip() for ln in (t or "").splitlines()]
    return "\n".join(ln for ln in lines if len(ln) > 2)


def fetch_text(url: str) -> str:
    """Trang chính sách của Meta dựng bằng JavaScript: mở bằng Chrome ẩn (không đăng nhập) rồi lấy chữ."""
    from playwright.sync_api import sync_playwright
    with sync_playwright() as pw:
        b = pw.chromium.launch(headless=True)
        try:
            pg = b.new_page(locale="vi-VN")
            pg.goto(url, wait_until="domcontentloaded", timeout=60000)
            pg.wait_for_timeout(4000)
            txt = pg.evaluate("""() => { const m = document.querySelector('main, article, [role=main]') || document.body;
                                       return m.innerText || ''; }""")
        finally:
            b.close()
    return _norm_text(txt)


def sources() -> list[dict]:
    rows = {r["key"]: r for r in db.q("SELECT * FROM fb_policy_sources")}
    extra = []
    try:
        extra = [x for x in json.loads(s().get("fbp_extra_sources") or "[]") if isinstance(x, dict) and x.get("url")]
    except Exception:
        pass
    out = []
    for src in SOURCES + extra:
        r = rows.get(src["key"], {})
        out.append({**src, "last_checked": r.get("last_checked"), "last_changed": r.get("last_changed"),
                    "status": r.get("status") or "chưa kiểm tra", "error": r.get("error"), "chars": len(r.get("last_text") or "")})
    return out


def _summarize(name: str, added: list[str], removed: list[str]) -> str:
    from llm import llm
    plain = (f"{len(added)} dòng mới, {len(removed)} dòng bỏ. " + (" | ".join(added[:4])[:500] if added else ""))
    if not llm.live:
        return plain
    try:
        from agents import system_prompt
        return llm.chat(system_prompt("tuan", s()),
                        f"Chính sách “{name}” của Facebook vừa thay đổi.\nDòng THÊM:\n" + "\n".join(added[:60])[:4000]
                        + "\nDòng BỎ:\n" + "\n".join(removed[:40])[:2500]
                        + "\n\nTóm tắt cho sếp bằng tiếng Việt (tối đa 5 gạch đầu dòng): thay đổi gì, ảnh hưởng gì tới việc đăng bài "
                          "tìm khách sỉ bằng nick cá nhân và Fanpage, đội cần làm gì khác. Không bịa điều không có trong văn bản.",
                        mock=plain, max_tokens=500, task="knowledge") or plain
    except Exception as e:
        print("[policy summary]", e)
        return plain


def check_sources(fetch=None, only: str | None = None) -> dict:
    """Mở từng trang chính sách, so với lần trước; có thay đổi thì ghi lại, tóm tắt và báo sếp."""
    if not _watch_lock.acquire(blocking=False):
        return {"busy": True}
    fetch = fetch or fetch_text
    res = {"checked": 0, "changed": 0, "errors": 0, "new": []}
    try:
        import workflows
        workflows.set_status("tuan", "working", "Đọc lại chính sách Facebook xem có gì mới")
        for src in sources():
            if only and src["key"] != only:
                continue
            now = db.now()
            old = db.one("SELECT * FROM fb_policy_sources WHERE key=?", (src["key"],))
            try:
                text = fetch(src["url"])
                if len(text) < 200:
                    raise RuntimeError(f"Trang trả về quá ít chữ ({len(text)} ký tự), có thể bị chặn hoặc đổi địa chỉ")
            except Exception as e:
                res["errors"] += 1
                db.run("""INSERT INTO fb_policy_sources(key, name, url, kind, last_checked, status, error) VALUES (?,?,?,?,?,?,?)
                          ON CONFLICT(key) DO UPDATE SET last_checked=excluded.last_checked, status='lỗi', error=excluded.error""",
                       (src["key"], src["name"], src["url"], src.get("kind", "meta"), now, "lỗi", str(e)[:300]))
                continue
            res["checked"] += 1
            h = hashlib.sha256(text.encode()).hexdigest()
            if old and old.get("last_hash") and old["last_hash"] != h:
                a_lines, b_lines = (old.get("last_text") or "").splitlines(), text.splitlines()
                added, removed = [], []
                for ln in difflib.unified_diff(a_lines, b_lines, lineterm="", n=0):
                    if ln.startswith("+") and not ln.startswith("+++"):
                        added.append(ln[1:])
                    elif ln.startswith("-") and not ln.startswith("---"):
                        removed.append(ln[1:])
                if added or removed:
                    summ = _summarize(src["name"], added, removed)
                    cid = db.run("""INSERT INTO fb_policy_changes(source_key, name, url, detected_at, added, removed, summary, status)
                                    VALUES (?,?,?,?,?,?,?, 'new')""", (src["key"], src["name"], src["url"], now,
                                                                       "\n".join(added[:200]), "\n".join(removed[:200]), summ))
                    res["changed"] += 1
                    res["new"].append({"id": cid, "name": src["name"], "summary": summ})
                    db.log("tuan", "Chính sách Facebook thay đổi", f"{src['name']}: {summ[:400]}")
                    try:
                        import telegram_bot
                        if telegram_bot.configured():
                            telegram_bot.send(f"⚠️ <b>Facebook đổi chính sách</b>: {telegram_bot.e(src['name'])}\n{telegram_bot.e(summ[:900])}\n"
                                              f"Xem ở mục Luật Facebook.")
                    except Exception as e:
                        print("[telegram]", e)
            changed = now if (old and old.get("last_hash") and old["last_hash"] != h) else (old or {}).get("last_changed")
            db.run("""INSERT INTO fb_policy_sources(key, name, url, kind, last_hash, last_text, last_checked, last_changed, status, error)
                      VALUES (?,?,?,?,?,?,?,?,?,NULL)
                      ON CONFLICT(key) DO UPDATE SET name=excluded.name, url=excluded.url, last_hash=excluded.last_hash,
                      last_text=excluded.last_text, last_checked=excluded.last_checked, last_changed=excluded.last_changed,
                      status=excluded.status, error=NULL""",
                   (src["key"], src["name"], src["url"], src.get("kind", "meta"), h, text[:120000], now, changed,
                    "có thay đổi" if changed == now else "đã đọc"))
        db.set_setting("fbp_watch_last", db.now())
        if res["checked"]:
            db.log("tuan", "Đọc lại chính sách Facebook",
                   f"Đọc {res['checked']} trang chính sách" + (f", {res['changed']} trang có thay đổi" if res["changed"] else ", không có gì mới")
                   + (f", {res['errors']} trang không mở được" if res["errors"] else ""))
        workflows.set_status("tuan", "idle", "Đã đọc lại chính sách Facebook")
    finally:
        _watch_lock.release()
    return res


def watch_due() -> bool:
    """Đọc lại chính sách mỗi tuần một lần (mặc định thứ Hai 06:40)."""
    st = s()
    if st.get("fbp_watch_enabled", "1") != "1":
        return False
    now = db.clock()
    last = st.get("fbp_watch_last") or ""
    if last and last >= (now - timedelta(days=_i("fbp_watch_every_days", 7))).strftime("%Y-%m-%d %H:%M:%S"):
        return False
    return now.strftime("%H:%M") >= (st.get("fbp_watch_time") or "06:40")


def overview() -> dict:
    st = s()
    accs = db.q("""SELECT fa.*, sa.name sale_name FROM fb_accounts fa LEFT JOIN sales sa ON sa.id=fa.sale_id
                   WHERE COALESCE(fa.enabled,1)=1 OR fa.rest_until > ? ORDER BY sa.name, fa.position""", (db.now(),))
    nicks = []
    for a in accs:
        L, U = limits(a), used_today(a["id"])
        nicks.append({"id": a["id"], "name": a["name"], "sale_name": a.get("sale_name"), "limits": L, "used": U,
                      "rest_until": a["rest_until"] if (a.get("rest_until") or "") > db.now() else None,
                      "factor": L["factor"], "login_status": a.get("login_status")})
    keys = ["fbp_enabled", "fbp_posts_day", "fbp_gap_minutes", "fbp_bumps_day", "fbp_joins_day", "fbp_friends_day", "fbp_same_group_hours",
            "fbp_new_nick_days", "fbp_new_nick_factor", "fbp_rest_days", "fbp_after_days", "fbp_after_factor", "fbp_hashtags_max",
            "fbp_similar_max", "fbp_removed_max", "fbp_group_rest_days", "fbp_watch_enabled", "fbp_watch_time", "fbp_auto_tighten"]
    return {
        "cats": CATS, "how": HOW, "rules": all_rules(), "settings": {k: st.get(k) for k in keys},
        "sources": sources(), "watch_last": st.get("fbp_watch_last"),
        "changes": db.q("SELECT id, source_key, name, url, detected_at, summary, status, added, removed FROM fb_policy_changes ORDER BY id DESC LIMIT 30"),
        "incidents": db.q("""SELECT i.*, fa.name account_name, g.name group_name FROM fb_incidents i
                             LEFT JOIN fb_accounts fa ON fa.id=i.account_id LEFT JOIN groups g ON g.id=i.group_id
                             ORDER BY i.id DESC LIMIT 30"""),
        "nicks": nicks,
        "flagged": db.one("""SELECT COUNT(*) n FROM posts WHERE status IN ('draft','approved','scheduled') AND COALESCE(policy_note,'')!=''""")["n"],
        "rested_groups": db.q("SELECT id, name, policy_rest_until FROM groups WHERE policy_rest_until > ? ORDER BY policy_rest_until", (db.now(),)),
    }


# ---------------------------------------------------------------- dạy luật vào sổ kiến thức của từng agent
TEACH = {"lan": ["content", "law"], "ceo": ["content", "law", "account", "rate", "group"], "tuan": ["rate", "group", "account"],
         "sale": ["rate", "account", "group"], "vy": ["law"], "mai": ["account"], "bao": ["rate", "content"]}


def teach() -> int:
    """Ghi từng luật vào sổ kiến thức của agent liên quan (cập nhật khi luật đổi). Trả về số mục đã ghi."""
    import knowledge
    n = 0
    for aid, cats in TEACH.items():
        for r in all_rules():
            if r["cat"] not in cats:
                continue
            src = next((x for x in SOURCES if x["key"] == r.get("src")), None)
            body = f"{r['rule']} Cách làm: {r['do']}" + (f" Nguồn: {src['name']} ({src['url']})." if src else "")
            if knowledge.save(aid, f"Luật Facebook: {r['title']}", body, question=f"Luật Facebook về {r['title'].lower()}?",
                              keywords=f"luat facebook {CATS.get(r['cat'], '')} {r['id']}", source="library", confidence=0.95):
                n += 1
    db.set_setting("fbp_taught", db.now())
    return n

"""Mai – chuyên viên tìm khách sỉ: tìm người ĐANG BÁN HÀNG ONLINE có thể nhập trà túi lọc, ngũ cốc về bán lại.

Mục tiêu (sếp đặt): người livestream bán hàng, bán qua Facebook/TikTok, TikTok Shop, Shopee, bán đa nền tảng, có nhu cầu tìm
nguồn hàng mới, có khả năng nhập hàng về bán lại. Không tập trung cửa hàng truyền thống không bán online.

MỤC TIÊU SỐ 1 (sếp chốt): tìm ra SỐ ĐIỆN THOẠI kinh doanh được công khai để sếp liên lạc. Tập trung Facebook trước;
TikTok, Shopee chỉ chạy khi sếp bật (mặc định tắt). Người chưa có SĐT: Mai đào thêm trang Giới thiệu / Liên hệ, đọc thêm
bài, và lần sau quay lại tìm tiếp (tối đa 3 lần). Có SĐT + đang bán hàng -> vào mục Khách hàng và chuyển sếp qua Telegram.

Quy trình mỗi lượt (1 nick sale mở Chrome, Mai nghiên cứu):
 1. Tìm tài khoản theo 4 hướng (từ khóa sửa được):
    H1 người livestream bán trà/ngũ cốc/thực phẩm; H2 người bán sản phẩm tương tự/bổ trợ; H3 người bán nhiều nhóm hàng tiêu
    dùng có thể mở rộng; H4 người công khai tuyển đại lý, tìm nguồn hàng, nhận phân phối, bán sỉ.
    Facebook: tìm Trang và bài đăng công khai. TikTok, Shopee: mở trang tìm kiếm công khai; gặp đăng nhập/captcha thì DỪNG,
    ghi "cần sếp xem tay" (không vượt qua cơ chế bảo vệ). Sếp/sale dán link bất kỳ để Mai phân tích.
 2. Kiểm tra hoạt động: mở trang của tài khoản, đọc giới thiệu và các bài gần nhất (chỉ đọc, không bấm gì).
 3. Nghiên cứu sản phẩm đang bán, nhóm ngành hàng.
 4. Phân biệt chủ shop / người livestream / đa nền tảng / nhà bán trên sàn / CTV / affiliate / KOC-KOL (không gộp chung).
 5. Lấy thông tin liên hệ KINH DOANH được công khai trên trang (SĐT, Zalo, email); không thu thập thông tin riêng tư.
 6. Kiểm tra trùng (link, SĐT, tên) với danh sách đã có và mục Khách hàng.
 7. Chấm điểm 100: bán hàng 20, livestream 20, phù hợp ngành 20, tự nhập hàng 15, hoạt động-tương tác 10, liên hệ 10,
    mở rộng sản phẩm 5. Hạng A ≥ 80, B 60–79, C 40–59, D < 40.
 8. Đề xuất sản phẩm của xưởng hợp với họ.  9. Viết kịch bản tiếp cận (không cam kết giá, chiết khấu, chính sách).
 10. Lưu: mọi người vào danh sách "Tìm khách sỉ"; hạng A/B tự vào mục Khách hàng (CRM) để sếp/Hà liên hệ BẰNG TAY.

Nguyên tắc: mọi điểm đều có bằng chứng (đoạn chữ + link). Không tạo dữ liệu giả, không đoán số đơn hay doanh thu từ lượt xem,
không coi người chia sẻ/xem livestream là người bán, không coi affiliate là khách nhập sỉ nếu chưa có bằng chứng tự nhập,
không tự nhắn tin. Không đủ chữ để đánh giá thì ghi "chưa đủ bằng chứng", không bịa.
"""
import json
import os
import random
import re
from datetime import timedelta
from urllib.parse import quote, urlparse, parse_qs

import db
from knowledge import plain

TIKTOK_BASE = os.getenv("TIKTOK_BASE_URL", "https://www.tiktok.com").rstrip("/")
SHOPEE_BASE = os.getenv("SHOPEE_BASE_URL", "https://shopee.vn").rstrip("/")

DIRECTIONS = {
    1: "Người livestream bán trà, ngũ cốc, thực phẩm",
    2: "Người bán sản phẩm tương tự hoặc bổ trợ",
    3: "Người bán nhiều nhóm hàng tiêu dùng, có thể mở rộng danh mục",
    4: "Người tuyển đại lý, tìm nguồn hàng, nhận phân phối, bán sỉ",
}
DEFAULT_KEYWORDS = {
    1: ["livestream bán trà", "live bán ngũ cốc", "livestream đồ ăn healthy", "live bán thực phẩm sạch"],
    2: ["shop trà túi lọc", "bán bột ngũ cốc online", "shop đồ ăn healthy", "shop cà phê online", "shop đồ ăn vặt healthy"],
    3: ["shop tạp hóa online", "shop mẹ và bé online", "shop đồ gia dụng bán online", "bán hàng đa kênh shopee tiktok"],
    4: ["tuyển đại lý thực phẩm", "tìm nguồn hàng trà", "nhận phân phối thực phẩm", "tìm nguồn hàng sỉ ngũ cốc", "tuyển ctv bán trà"],
}
SELLER_TYPES = {"owner": "Chủ shop tự nhập hàng", "live": "Người bán hàng livestream", "multi": "Người bán hàng đa nền tảng",
                "marketplace": "Nhà bán hàng trên sàn TMĐT", "ctv": "Cộng tác viên", "affiliate": "Affiliate",
                "koc": "KOC/KOL", "store": "Cửa hàng truyền thống", "unknown": "Chưa rõ"}
PLATFORM_TXT = {"facebook": "Facebook", "tiktok": "TikTok", "shopee": "Shopee"}
GRADE_ACTION = {
    "A": "Sếp hoặc Hà nhắn/gọi trong 24 giờ theo kịch bản (nhắn tay, không gửi tự động)",
    "B": "Theo dõi thêm 1 tuần (xem 1–2 phiên live hoặc bài mới) rồi tiếp cận",
    "C": "Lưu theo dõi, kiểm tra lại sau 2 tuần",
    "D": "Không ưu tiên",
}

# ---------------------------------------------------------------- dấu hiệu (so trên chữ đã bỏ dấu)
RX = {k: re.compile(v) for k, v in {
    "sell": r"\b(gia|inbox|ib|ship|cod|freeship|dat hang|order|chot don|san hang|con hang|giam gia|ban si|ban le|gio hang|mua ngay|"
            r"lien he dat|nhan don|giao hang|size|combo|khuyen mai)\b",
    "live": r"(dang phat truc tiep|da phat truc tiep|livestream|\blive\b|len song|phien live|lich live|live luc|\blai live\b)",
    "live_strong": r"(dang phat truc tiep|da phat truc tiep|livestream|phien live|len song|\blive (xa|sale|ban|chot|tang|giam)|"
                   r"\b(lich|gio) live\b|live luc)",
    "shared": r"(da chia se|chia se video truc tiep|dang xem|cung xem|shared a live|is watching)",
    "import": r"(nhap hang|nguon hang|tim nguon|tuyen dai ly|tuyen ctv|nhan phan phoi|phan phoi|ban si|gia si|kho hang|"
              r"hang moi ve|hang ve|nhap ve|dai ly|si le|lay si|nha phan phoi|tim nha cung cap)",
    "owner": r"(shop minh|shop em|cua hang|nha minh|xuong nha|hang nha lam|kho cua shop|shop chinh chu)",
    "affiliate": r"(affiliate|tiep thi lien ket|link san pham|link o binh luan|link mua|link duoi binh luan|hoa hong|#aff\b|"
                 r"s\.shopee|shope\.ee|vt\.tiktok|link bio|link trong bio|ma giam gia shopee)",
    "koc": r"(review|unbox|dap hop|trai nghiem|booking|hop tac quang cao|\bkoc\b|\bkol\b|content creator|nha sang tao)",
    "ctv": r"(cong tac vien|\bctv\b|ban hang khong can von|khong can von|lay hang tu kho|ban ho)",
    "fit_core": r"(\btra\b|tra tui loc|ngu coc|yen mach|granola|hat dinh duong|ca phe|cafe|coffee|matcha|cacao|bot can tay|diep ca|"
                r"bot rau|healthy|eat clean|an kieng|thuc pham sach|sua hat|do uong)",
    "fit_food": r"(do an vat|banh keo|thuc pham|dac san|mat ong|nong san|do an|gia vi|hat dieu|kho ga|banh trang|an vat)",
    "consumer": r"(my pham|gia dung|me va be|thoi trang|phu kien|do choi|cham soc|tap hoa|nha cua|do dung)",
    "store_only": r"(cua hang tai|dia chi cua hang|ghe cua hang|mo cua tu)",
}.items()}
PHONE_RX = re.compile(r"(?<!\d)(?:\+?84|0)(?:[\s.\-]?\d){9}(?!\d)")
EMAIL_RX = re.compile(r"[\w.+-]+@[\w-]+\.[\w.]{2,}")
FOLLOW_RX = re.compile(r"([\d.,]+\s*(?:K|N|k|n|M|tr|triệu)?)\s*(?:người theo dõi|followers?|follower|lượt thích|người thích)", re.I)
BLOCK_RX = re.compile(r"(captcha|xac minh ban khong phai|verify you are human|verify to continue|log in to tiktok|"
                      r"dang nhap de tiep tuc|vui long dang nhap|please log in|security check|kiem tra bao mat|"
                      r"too many requests|qua nhieu yeu cau|not a robot|khong phai la robot|khong phai robot)", re.I)


def s() -> dict:
    return db.get_settings()


def keywords() -> dict:
    try:
        k = json.loads(s().get("prospect_keywords") or "{}")
        return {int(d): v for d, v in k.items() if v} or DEFAULT_KEYWORDS
    except Exception:
        return DEFAULT_KEYWORDS


# ---------------------------------------------------------------- link
def platform_of(url: str) -> str:
    h = urlparse(url).netloc.lower()
    if "tiktok" in h or url.startswith(TIKTOK_BASE):
        return "tiktok"
    if "shopee" in h or url.startswith(SHOPEE_BASE):
        return "shopee"
    return "facebook"


def canon(url: str) -> str:
    """Link chuẩn của một tài khoản (để chống trùng): bỏ tham số, bỏ đường dẫn bài viết."""
    u = (url or "").strip()
    if not u:
        return ""
    if not re.match(r"https?://", u):
        u = "https://" + u.lstrip("/")
    p = urlparse(u)
    host = p.netloc.lower()
    if host in ("facebook.com", "m.facebook.com", "web.facebook.com", "mbasic.facebook.com"):
        host = "www.facebook.com"
    seg = [x for x in p.path.split("/") if x]
    base = f"{p.scheme}://{host}"
    if not seg:
        return base
    if seg[0] == "profile.php":
        return f"{base}/profile.php?id={parse_qs(p.query).get('id', [''])[0]}"
    if seg[0].startswith("@"):  # TikTok
        return f"{base}/{seg[0].lower()}"
    if seg[0] == "shop" and len(seg) > 1:  # Shopee /shop/123
        return f"{base}/shop/{seg[1]}"
    if seg[0] in ("p", "people") and len(seg) > 1:  # Facebook trang kiểu mới
        return f"{base}/{seg[0]}/{seg[1]}".lower()
    return f"{base}/{seg[0]}".lower()


FB_SKIP = {"groups", "search", "hashtag", "photo", "photos", "watch", "events", "marketplace", "stories", "help", "policies",
           "privacy", "settings", "notifications", "friends", "messages", "gaming", "pages", "bookmarks", "reel", "reels", "login",
           "sharer", "share", "dialog", "ads", "business", "legal", "me", "home", "friends", "watch", "live", "permalink.php", "story.php", "video.php", "home.php", "l.php"}

EXTRACT_JS = r"""(pf) => {
  const out = {};
  const near = (a) => { let el = a; for (let i = 0; i < 8 && el; i++) { el = el.parentElement; if (!el) break;
      if (el.getAttribute && (el.getAttribute('role') === 'article' || (el.innerText || '').length > 120)) return (el.innerText || '').slice(0, 600); }
    return (a.innerText || ''); };
  for (const a of document.querySelectorAll('a[href]')) {
    const href = a.href; const name = (a.innerText || a.getAttribute('aria-label') || '').trim().split('\n')[0];
    if (!name || name.length < 2 || name.length > 80) continue;
    if (pf === 'tiktok' && !/\/@[\w.\-]+/.test(href)) continue;
    if (pf === 'shopee' && !/\/shop\/\d+|\/[\w.\-]+\?.*shop|shopee\.vn\/[\w.\-]+$/.test(href)) continue;
    const key = href.split('?')[0].split('#')[0];
    if (!out[key]) out[key] = {href, name, snippet: near(a)};
  }
  return Object.values(out).slice(0, 60);
}"""


def _fb_candidate(href: str) -> bool:
    """Link tới trang/tài khoản Facebook (không phải nhóm, bài viết, menu)."""
    p = urlparse(href)
    if "facebook" not in p.netloc and not href.startswith(_fb_base()):
        return False
    seg = [x for x in p.path.split("/") if x]
    if not seg:
        return False
    if seg[0] == "profile.php":
        return "id=" in p.query
    if seg[0].lower() in FB_SKIP or seg[0].startswith("@"):
        return False
    if seg[0] in ("p", "people"):
        return len(seg) >= 2
    return len(seg) == 1


def _fb_base() -> str:
    import browser_poster as B
    return B.FB_BASE


# ---------------------------------------------------------------- đọc trang, tìm dấu hiệu
FEED_JS = r"""() => {
  const arts = [...document.querySelectorAll('[role="article"]')].filter(a => !a.parentElement.closest('[role="article"]'));
  return arts.slice(0, 10).map(a => ((a.innerText || '') + ' · ' + [...a.querySelectorAll('[aria-label]')].map(x => x.getAttribute('aria-label')).join(' · ')).slice(0, 1500));
}"""
LINKS_JS = r"""() => [...document.querySelectorAll('a[href]')].map(a => a.href).filter(h => /tel:|mailto:|zalo\.me|shopee|tiktok|lazada|m\.me\//i.test(h)).slice(0, 40)"""


def norm_phone(x: str) -> str:
    d = re.sub(r"\D", "", x or "")
    if d.startswith("84") and len(d) == 11:
        d = "0" + d[2:]
    return d if len(d) == 10 and d.startswith("0") else ""


def _lines(text: str) -> list[str]:
    return [l.strip() for l in re.split(r"[\n·•|]+", text or "") if len(l.strip()) >= 3]


def _ev(lines: list[str], key: str, url: str, limit: int = 2) -> list[dict]:
    out = []
    for l in lines:
        if RX[key].search(plain(l)):
            out.append({"kind": key, "text": l[:160], "url": url})
            if len(out) >= limit:
                break
    return out


def analyze(url: str, body: str, articles: list[str], links: list[str], platform: str) -> dict:
    """Từ chữ thật trên trang công khai -> dấu hiệu, bằng chứng, điểm. Không có chữ thì không cho điểm."""
    from group_finder import post_age_hours, parse_count
    lines = _lines(body)
    own = [a for a in articles if not RX["shared"].search(plain(a[:300]))]   # bài tự đăng (bỏ bài chia sẻ/xem live của người khác)
    shared_live = [a for a in articles if RX["shared"].search(plain(a[:300])) and RX["live"].search(plain(a))]
    own_text = "\n".join(own)
    other = {l for a in articles if a not in own for l in _lines(a)}  # chữ trong bài chia sẻ của người khác: không tính cho họ
    alltext = "\n".join(l for l in lines if l not in other) + "\n" + own_text
    p_all = plain(alltext)
    ev = []
    hit = {k: len(set(m.group(0) for m in RX[k].finditer(p_all))) for k in RX}
    # livestream: chỉ tính bài TỰ phát trực tiếp
    live_posts = [a for a in own if RX["live_strong"].search(plain(a))]
    ages = [post_age_hours(a[:300]) for a in own]
    ages = [x for x in ages if x is not None]
    live_ages = [post_age_hours(a[:300]) for a in live_posts]
    live_ages = [x for x in live_ages if x is not None]
    last = min(ages) if ages else None
    # liên hệ công khai (chỉ trên trang kinh doanh của họ)
    tel = [re.sub(r"\D", "", l[4:]) for l in links if l.lower().startswith("tel:")]
    phones = sorted({norm_phone(m.group(0)) for m in PHONE_RX.finditer(alltext)} | {norm_phone(x) for x in tel if x})
    phones = [p for p in phones if p][:2]
    emails = sorted({e for e in EMAIL_RX.findall(alltext) if not e.lower().endswith((".png", ".jpg"))})[:1]
    zalo = next((l for l in links if "zalo.me" in l.lower()), None) or (
        phones[0] if phones and re.search(r"zalo", alltext, re.I) else None)
    shop_links = sorted({canon(l) for l in links if re.search(r"shopee\.vn/(shop/\d+|[\w.\-]+$)|tiktok\.com/@|lazada", l, re.I)})[:4]
    msgr = any("m.me/" in l for l in links) or bool(re.search(r"nhắn tin|send message|gửi tin nhắn", body or "", re.I))
    fm = FOLLOW_RX.search(body or "")
    followers = parse_count(fm.group(1)) if fm else None
    platforms = {platform} | {platform_of(l) for l in shop_links}
    # bằng chứng
    for k in ("live", "import", "sell", "fit_core", "fit_food", "affiliate", "owner", "ctv", "koc"):
        if k == "live":
            le = _ev(_lines("\n".join(live_posts)), "live_strong", url, 2) or _ev(_lines(alltext), "live_strong", url, 1)
            ev += [{**e, "kind": "live"} for e in le if not any(e["text"] == x["text"] for x in ev)]
            continue
        ev += [e for e in _ev(_lines(alltext), k, url, 1 if k not in ("sell", "import") else 2)
               if not any(e["text"] == x["text"] for x in ev)]
    if shared_live:
        ev.append({"kind": "shared_live", "text": shared_live[0][:160], "url": url})
    for p in phones:
        ev.append({"kind": "contact", "text": f"SĐT công khai trên trang: {p}", "url": url})
    for l in shop_links:
        ev.append({"kind": "shop_link", "text": f"Link gian hàng/tài khoản khác: {l}", "url": l})
    # ---- chấm điểm theo thang của sếp
    sell = 20 if hit["sell"] >= 4 else 14 if hit["sell"] >= 2 else 7 if hit["sell"] == 1 else 0
    if last is not None and last > 24 * 30:
        sell //= 2
    if live_posts:
        la = min(live_ages) if live_ages else None
        live = 20 if la is not None and la <= 24 * 7 else 14 if la is not None and la <= 24 * 30 else 8
    else:
        live = 8 if re.search(r"lich live|live luc|live moi|live hang", p_all) else 0
    fit = 20 if hit["fit_core"] else 12 if hit["fit_food"] else 5 if hit["consumer"] else 0
    aff_only = hit["affiliate"] >= 1 and hit["import"] == 0 and hit["owner"] == 0 and not any("shopee.vn/shop" in l for l in shop_links)
    imp = 15 if hit["import"] >= 2 else 9 if hit["import"] == 1 else 0
    imp = min(15, imp + (3 if hit["owner"] else 0) + (3 if any("/shop/" in l for l in shop_links) else 0))
    if aff_only:
        imp = min(imp, 3)
    avg_c = 0.0
    if own:
        cs = [int(m.group(1)) for a in own for m in [re.search(r"(\d+)\s*(?:bình luận|comments?)", a, re.I)] if m]
        avg_c = sum(cs) / len(cs) if cs else 0.0
    eng = 0
    if last is not None:
        eng = 10 if last <= 72 and avg_c >= 3 else 7 if last <= 72 else 6 if last <= 168 else 3 if last <= 720 else 0
    if followers and followers >= 10000:
        eng = min(10, eng + 2)
    if sell == 0:  # có hoạt động nhưng không phải hoạt động bán hàng
        eng = min(eng, 3)
    contact = min(10, (5 if phones else 0) + (3 if zalo else 0) + (2 if emails else 0) + (2 if msgr else 0))
    groups_n = sum(1 for k in ("fit_core", "fit_food", "consumer") if hit[k])
    expand = 5 if groups_n >= 2 or len(platforms) >= 2 else 2 if hit["consumer"] else 0
    if hit["store_only"] and not hit["sell"] and not live_posts:  # cửa hàng truyền thống không có dấu hiệu bán online
        sell, fit = min(sell, 3), min(fit, 10)
    parts = {"sales": sell, "live": live, "fit": fit, "import": imp, "engage": eng, "contact": contact, "expand": expand}
    score = sum(parts.values())
    grade = "A" if score >= 80 else "B" if score >= 60 else "C" if score >= 40 else "D"
    # ---- phân loại người bán (một loại chính + các nhãn phụ)
    tags = []
    if aff_only and hit["affiliate"]:
        tags.append("affiliate")
    if hit["koc"] and (followers or 0) >= 10000:
        tags.append("koc")
    if live >= 14 and sell >= 7:
        tags.append("live")
    if len(platforms) >= 2:
        tags.append("multi")
    if any(re.search(r"shopee|tiktok\.com/@.*shop|lazada", l) for l in shop_links) or platform in ("shopee",):
        tags.append("marketplace")
    if hit["ctv"]:
        tags.append("ctv")
    if (hit["owner"] or hit["import"]) and not aff_only:
        tags.append("owner")
    order = ["affiliate", "koc", "live", "multi", "marketplace", "owner", "ctv"]
    primary = next((t for t in order if t in tags), "unknown")
    if hit["store_only"] and sell < 7 and not live_posts:
        primary, tags = "store", ["store"]
    if primary == "affiliate" and hit["import"]:
        primary = "owner"
    cats = [c for c, k in (("Trà, cà phê, đồ uống, ngũ cốc, healthy", "fit_core"), ("Thực phẩm, đồ ăn vặt, đặc sản", "fit_food"),
                           ("Hàng tiêu dùng khác", "consumer")) if hit[k]]
    products_seen = [e["text"] for e in ev if e["kind"] in ("fit_core", "fit_food")][:2]
    enough = bool(own or len(lines) >= 5)
    return {
        "score": score, "grade": grade if enough else "D", "parts": parts, "seller_type": primary, "tags": tags,
        "categories": cats, "products_text": "; ".join(products_seen), "last_post_hours": last,
        "live_count": len(live_posts), "posts_seen": len(own), "shared_live": bool(shared_live),
        "live_freq": (f"{len(live_posts)}/{len(own)} bài gần nhất là phát trực tiếp" if own and live_posts else ""),
        "followers": followers, "phones": phones, "zalo": zalo, "email": emails[0] if emails else None, "messenger": msgr,
        "shop_links": shop_links, "platforms": sorted(platforms), "affiliate_only": aff_only, "evidence": ev[:14],
        "import_signals": "; ".join(e["text"] for e in ev if e["kind"] == "import")[:300], "enough": enough,
    }


# ---------------------------------------------------------------- đề xuất, kịch bản
def suggest_products(a: dict) -> list[dict]:
    prods = db.q("SELECT id, name, category, hot FROM products ORDER BY hot DESC, id")
    if not prods:
        return []
    p_all = plain(" ".join(e["text"] for e in a.get("evidence", []) if e["kind"] in ("fit_core", "fit_food", "sell", "import", "live")))
    want = []
    if re.search(r"\btra\b|do uong|matcha", p_all):
        want += ["trà"]
    if re.search(r"ca phe|cafe|coffee", p_all):
        want += ["cà phê"]
    if re.search(r"ngu coc|yen mach|granola|hat dinh duong", p_all):
        want += ["ngũ cốc"]
    if re.search(r"healthy|an kieng|eat clean|giam can|detox|bot rau|can tay|diep ca", p_all):
        want += ["bột"]
    if not want:
        want = ["trà", "ngũ cốc"]
    out = []
    for w in want:
        for p in prods:
            if w in (p["category"] or "").lower() + " " + p["name"].lower() and p["name"] not in [o["name"] for o in out]:
                out.append({"id": p["id"], "name": p["name"], "why": "đúng nhóm hàng họ đang bán" if a.get("categories") else "dòng chủ lực của xưởng"})
                break
    for p in prods:  # sản phẩm sếp đang đẩy
        if p["hot"] and len(out) < 3 and p["name"] not in [o["name"] for o in out]:
            out.append({"id": p["id"], "name": p["name"], "why": "sản phẩm xưởng đang bán chạy"})
    return out[:3]


def script(row: dict, a: dict, prods: list[dict]) -> str:
    st = s()
    who = row.get("shop_name") or row.get("account_name") or "shop"
    seen = ("đang livestream bán hàng" if a["parts"]["live"] >= 14 else
            "đang bán " + (a["categories"][0].split(",")[0].lower() if a["categories"] else "hàng online"))
    names = ", ".join(p["name"] for p in prods[:2]) or "trà túi lọc và bột ngũ cốc"
    base = (f"Chào {who}, em là Hà bên {st.get('company_name') or 'xưởng'}. Em thấy bên mình {seen} trên "
            f"{PLATFORM_TXT.get(row.get('platform'), 'mạng xã hội')}. Bên em là xưởng sản xuất {names}, có giá sỉ cho người bán online "
            "và có sẵn ảnh, video thật để đăng bán. Nếu shop quan tâm, em gửi bảng giá và thông tin sản phẩm để mình xem trước ạ.")
    if a.get("affiliate_only"):
        base = (f"Chào {who}, em là Hà bên {st.get('company_name') or 'xưởng'}. Em thấy bạn đang giới thiệu sản phẩm "
                f"{(a['categories'][0].split(',')[0].lower() if a['categories'] else '')} rất hay. Bạn có đang tự nhập hàng về bán hay chủ yếu "
                "làm tiếp thị liên kết ạ? Bên em là xưởng sản xuất " + names + ", nếu phù hợp em gửi thông tin để bạn tham khảo.")
    from llm import llm
    if llm.live and st.get("prospect_ai_script", "1") == "1":
        try:
            from agents import system_prompt
            ev = [{"loai": e["kind"], "chu": e["text"]} for e in a.get("evidence", [])][:8]
            txt = llm.chat(system_prompt("ha", st),
                           f"Viết tin nhắn tiếp cận LẦN ĐẦU (dưới 80 chữ, tự nhiên, xưng em) gửi {who}. Chỉ dựa vào bằng chứng sau, "
                           f"không bịa thêm: {json.dumps(ev, ensure_ascii=False)}. Loại người bán: {SELLER_TYPES[a['seller_type']]}. "
                           f"Sản phẩm của xưởng nên giới thiệu: {names}. KHÔNG hứa giá, chiết khấu, mẫu thử hay chính sách nào; "
                           "chỉ đề nghị gửi bảng giá/thông tin. Kết bằng 1 câu hỏi.",
                           mock=lambda: base, max_tokens=260, task="replies")
            if txt and len(txt) > 40 and not re.search(r"chiết khấu \d|giảm \d|tặng|miễn phí|cam kết", txt, re.I):
                return txt.strip()
        except Exception as e:
            print("[prospect script]", e)
    return base


def next_action(row: dict, a: dict) -> str:
    if row.get("status") == "needs_manual":
        return "Sếp mở link xem tay (nền tảng yêu cầu đăng nhập/xác minh, phần mềm không vượt qua)"
    act = GRADE_ACTION[a["grade"]]
    if a["grade"] == "B" and a["parts"]["live"] == 0:
        act = "Theo dõi thêm 1 tuần (xem bài mới, có livestream không) rồi tiếp cận"
    if a.get("affiliate_only") and a["grade"] in ("A", "B", "C"):
        act = ("Affiliate/KOC, chưa có bằng chứng tự nhập hàng: hỏi thăm mô hình kinh doanh trước, không chào giá sỉ ngay"
               if a["grade"] != "C" else "Affiliate/KOC, chưa có bằng chứng tự nhập hàng: chỉ theo dõi, không chào giá sỉ")
    if a.get("shared_live") and not a["live_count"] and a["parts"]["sales"] < 7:
        act = "Chỉ xem/chia sẻ livestream của người khác, không thấy tự bán hàng: không phải khách sỉ"
    if a["seller_type"] == "store":
        act = "Cửa hàng truyền thống, không thấy bán online: không ưu tiên"
    if a["grade"] in ("A", "B", "C") and not a["phones"] and not a.get("affiliate_only") and a["seller_type"] != "store":
        act = ("Chưa tìm thấy SĐT công khai (đã đọc cả trang Giới thiệu). Mai sẽ quay lại tìm tiếp; sếp có thể nhắn trang để xin SĐT"
               if a.get("dug") else "Chưa có SĐT công khai: Mai sẽ quay lại tìm tiếp")
    if not a["enough"]:
        act = "Chưa đủ bằng chứng (trang ít nội dung công khai): kiểm tra lại sau"
    if a["phones"] and a["grade"] in ("A", "B", "C") and a["enough"] and not a.get("affiliate_only"):
        act = f"Gọi hoặc nhắn Zalo {a['phones'][0]} theo kịch bản" + (" trong 24 giờ" if a["grade"] == "A" else "")
    return act


# ---------------------------------------------------------------- lưu
def find_dup(url: str, phones: list[str], name: str, platform: str) -> dict | None:
    c = canon(url)
    r = db.one("SELECT * FROM prospects WHERE account_url=? OR shop_url=?", (c, c))
    if r:
        return r
    for p in phones or []:
        r = db.one("SELECT * FROM prospects WHERE phone=?", (p,))
        if r:
            return r
    if name:
        for r in db.q("SELECT * FROM prospects WHERE platform=?", (platform,)):
            if plain(r["account_name"] or "") == plain(name):
                return r
    return None


def lead_dup(phones: list[str], url: str) -> dict | None:
    for p in phones or []:
        r = db.one("SELECT id, name FROM leads WHERE phone=?", (p,))
        if r:
            return r
    return db.one("SELECT id, name FROM leads WHERE contact=?", (canon(url),)) if url else None


def save(cand: dict, a: dict | None, direction: int | None, keyword: str, found_by: int | None, status: str = "verified") -> dict:
    url = canon(cand["href"])
    plat = platform_of(url)
    name = (cand.get("name") or "").strip()[:120]
    dup = find_dup(url, (a or {}).get("phones") or [], name, plat)
    now = db.now()
    if a is None:  # chưa xem được (bị chặn / cần xem tay)
        if dup:
            return dup
        pid = db.run("""INSERT INTO prospects(platform, account_name, account_url, direction, keyword, status, next_action, evidence,
                        found_by, created_at, updated_at) VALUES (?,?,?,?,?,?,?,?,?,?,?)""",
                     (plat, name, url, direction, keyword, status, next_action({"status": status}, {}), json.dumps(
                         [{"kind": "found", "text": (cand.get("snippet") or "")[:160], "url": url}], ensure_ascii=False),
                      found_by, now, now))
        return db.one("SELECT * FROM prospects WHERE id=?", (pid,))
    prods = suggest_products(a)
    row = {"platform": plat, "account_name": name, "shop_name": cand.get("shop_name") or name, "status": status}
    data = dict(platform=plat, account_name=name, shop_name=row["shop_name"], account_url=url,
                shop_url=next((l for l in a["shop_links"] if l != url), None), live_url=cand.get("live_url"),
                products=a["products_text"], categories="; ".join(a["categories"]), seller_type=a["seller_type"],
                tags=",".join(a["tags"]), direction=direction, keyword=keyword,
                recent_activity=(f"Bài mới nhất cách đây {int(a['last_post_hours'] // 24)} ngày" if (a["last_post_hours"] or 0) >= 24 else
                                 f"Bài mới nhất cách đây {int(a['last_post_hours'] or 0)} giờ") if a["last_post_hours"] is not None else "",
                live_freq=a["live_freq"], followers=a["followers"], phone=(a["phones"] or [None])[0], zalo=a["zalo"], email=a["email"],
                import_signals=a["import_signals"], evidence=json.dumps(a["evidence"], ensure_ascii=False),
                score=a["score"], grade=a["grade"], parts=json.dumps(a["parts"]),
                suggested=json.dumps(prods, ensure_ascii=False), status=status, verified_at=now, updated_at=now)
    data["next_action"] = next_action(row, a)
    ld = lead_dup(a["phones"], url)
    if ld:
        data["lead_id"] = ld["id"]
        data["next_action"] = f"Đã có trong Khách hàng ({ld['name']}): cập nhật thêm thông tin, không liên hệ trùng"
    if dup:
        cols = [k for k in data if k not in ("direction", "keyword")]
        db.run(f"UPDATE prospects SET {', '.join(k + '=?' for k in cols)} WHERE id=?", (*[data[k] for k in cols], dup["id"]))
        pid = dup["id"]
    else:
        data.update(found_by=found_by, created_at=now)
        pid = db.run(f"INSERT INTO prospects({', '.join(data)}) VALUES ({', '.join('?' * len(data))})", tuple(data.values()))
    r = db.one("SELECT * FROM prospects WHERE id=?", (pid,))
    if not r.get("approach") and a["grade"] in ("A", "B", "C") and a["enough"]:
        db.run("UPDATE prospects SET approach=? WHERE id=?", (script(r, a, prods), pid))
    db.run("UPDATE prospects SET phone_tries=COALESCE(phone_tries,0)+1 WHERE id=?", (pid,))
    if r.get("lead_id") and r.get("phone"):  # đã ở Khách hàng nhưng trước đó chưa có SĐT: bổ sung số và chuyển sếp
        ld = db.one("SELECT phone FROM leads WHERE id=?", (r["lead_id"],))
        if ld and not ld["phone"]:
            db.run("UPDATE leads SET phone=?, phone_at=?, updated_at=? WHERE id=?", (r["phone"], now, now, r["lead_id"]))
            try:
                import kpi
                kpi.escalate(r["lead_id"], f"Mai tìm được SĐT khách sỉ hạng {r['grade']} ({r['score']} điểm)")
            except Exception as e:
                print("[prospect escalate]", e)
    new_crm = False
    if (a["phones"] and a["grade"] in ("A", "B", "C") and a["enough"] and not a.get("affiliate_only") and not r.get("lead_id")
            and s().get("prospect_auto_crm", "1") == "1"):
        new_crm = bool(to_crm(pid, escalate=True))
    return {**db.one("SELECT * FROM prospects WHERE id=?", (pid,)), "_crm_new": new_crm}


def to_crm(pid: int, escalate: bool = False) -> int | None:
    """Bước 10: lưu vào mục Khách hàng để sếp/Hà liên hệ bằng tay."""
    r = db.one("SELECT * FROM prospects WHERE id=?", (pid,))
    if not r:
        return None
    if r.get("lead_id"):
        return r["lead_id"]
    ev = "; ".join(e["text"][:90] for e in json.loads(r.get("evidence") or "[]")[:2])
    note = f"Mai tìm ({PLATFORM_TXT.get(r['platform'])}, hạng {r['grade']} {r['score']}đ). Bằng chứng: {ev}. {r['account_url']}"
    lid = db.run("""INSERT INTO leads(name, contact, channel, source, business_type, need, score, status, note, phone, origin,
                    created_at, updated_at) VALUES (?,?,?,?,?,?,?,'new',?,?,'prospect',?,?)""",
                 (r["shop_name"] or r["account_name"], r["account_url"], PLATFORM_TXT.get(r["platform"], r["platform"]),
                  f"Tìm khách sỉ · {DIRECTIONS.get(r['direction'] or 0, 'dán link')}", SELLER_TYPES.get(r["seller_type"], ""),
                  (r["products"] or r["categories"] or "")[:300], r["score"] or 0, note[:500], r["phone"], db.now(), db.now()))
    db.run("UPDATE prospects SET lead_id=? WHERE id=?", (lid, pid))
    if r.get("approach"):
        db.run("UPDATE leads SET consult_note=? WHERE id=?", (r["approach"], lid))
    if escalate and r.get("phone"):  # có SĐT: chuyển sếp qua Telegram (thẻ khách có nút Đã gọi / Nhắc lại)
        try:
            import kpi
            kpi.escalate(lid, f"Mai tìm được SĐT khách sỉ hạng {r['grade']} ({r['score']} điểm) trên {PLATFORM_TXT.get(r['platform'])}")
        except Exception as e:
            print("[prospect escalate]", e)
    return lid


# ---------------------------------------------------------------- việc trên trình duyệt (chạy trong hàng việc của nick sale)
def _blocked(page) -> bool:
    try:
        t = plain(page.inner_text("body")[:4000])
    except Exception:
        return False
    u = page.url.lower()
    return bool(BLOCK_RX.search(t)) or any(x in u for x in ("/login", "captcha", "verify", "checkpoint", "buyer/login"))


def search_url(platform: str, q: str, kind: str = "pages") -> str:
    if platform == "tiktok":
        return f"{TIKTOK_BASE}/search/user?q={quote(q)}"
    if platform == "shopee":
        return f"{SHOPEE_BASE}/search_user?keyword={quote(q)}"
    return f"{_fb_base()}/search/{kind}/?q={quote(q)}"


def _search(page, platform: str, q: str, kind: str = "pages") -> tuple[list[dict], bool]:
    import browser_poster as B
    page.goto(search_url(platform, q, kind), wait_until="domcontentloaded", timeout=60000)
    page.wait_for_timeout(int(random.uniform(3.5, 6) * 1000))
    if platform == "facebook":
        B._check_blocked(page)
    if _blocked(page):
        return [], True
    for _ in range(3):
        page.mouse.wheel(0, random.randint(1000, 1600))
        page.wait_for_timeout(int(random.uniform(1.5, 3) * 1000))
    rows = page.evaluate(EXTRACT_JS, platform)
    if platform == "facebook":
        rows = [r for r in rows if _fb_candidate(r["href"])]
    seen, out = set(), []
    for r in rows:
        c = canon(r["href"])
        if c in seen or not r["name"].strip():
            continue
        seen.add(c)
        out.append(r)
    return out, False


def inspect(page, url: str, extra: str = "") -> tuple[dict | None, bool]:
    """Mở trang công khai của tài khoản, đọc chữ và vài bài gần nhất. Trả về (phân tích, bị chặn?)."""
    import browser_poster as B
    plat = platform_of(url)
    page.goto(url, wait_until="domcontentloaded", timeout=60000)
    page.wait_for_timeout(int(random.uniform(3.5, 6) * 1000))
    if plat == "facebook":
        B._check_blocked(page)
    if _blocked(page):
        return None, True
    for _ in range(2):
        page.mouse.wheel(0, random.randint(900, 1400))
        page.wait_for_timeout(int(random.uniform(1.5, 3) * 1000))
    body = page.inner_text("body")[:15000]
    arts = page.evaluate(FEED_JS)
    links = page.evaluate(LINKS_JS)
    name = (page.evaluate("() => ((document.querySelector('h1') || {}).innerText || document.title || '').trim()") or "")[:80]
    body += ("\n" + extra) if extra else ""
    a = analyze(url, body, arts, links, plat)
    if not a["phones"] and plat == "facebook":  # mục tiêu là SĐT: đọc thêm bài và mở trang Giới thiệu / Liên hệ
        for _ in range(3):
            page.mouse.wheel(0, random.randint(1200, 1800))
            page.wait_for_timeout(int(random.uniform(1.5, 3) * 1000))
        arts = page.evaluate(FEED_JS) or arts
        for au in about_urls(url):
            try:
                page.goto(au, wait_until="domcontentloaded", timeout=60000)
                page.wait_for_timeout(int(random.uniform(2.5, 4.5) * 1000))
                B._check_blocked(page)
                txt = page.inner_text("body")[:6000]
                body += "\n" + txt
                links += page.evaluate(LINKS_JS)
                if PHONE_RX.search(txt) or any(l.lower().startswith("tel:") for l in links):
                    break
            except B.Blocked:
                raise
            except Exception as e:
                print("[prospect about]", au, e)
        a = analyze(url, body, arts, links, plat)
        a["dug"] = True
    a["page_name"] = name
    return a, False


def about_urls(url: str) -> list[str]:
    """Trang Giới thiệu / Thông tin liên hệ của một Trang hoặc trang cá nhân Facebook."""
    if "profile.php" in url:
        return [url + "&sk=about_contact_and_basic_info", url + "&sk=about"]
    return [url.rstrip("/") + "/about_contact_and_basic_info", url.rstrip("/") + "/about"]


def job(pw, acc_id: int, plan: list[dict] | None = None, urls: list[str] | None = None, notify: str | None = None):
    """Một lượt tìm khách: plan = [{platform, direction, keyword}], hoặc urls = link sếp dán để phân tích."""
    import browser_poster as B
    import workflows
    acc, sale_row, agent = B._ctx_names(acc_id)
    limit = int(s().get("prospect_inspect_per_run") or 8)
    ctx, page = B._open(pw, acc_id)
    res = {"found": 0, "inspected": 0, "grades": {"A": 0, "B": 0, "C": 0, "D": 0}, "manual": 0, "blocked": [], "dup": set(), "new": [], "phones": []}
    blocked = set()
    try:
        if not B._logged_in(ctx):
            raise RuntimeError("Nick chưa đăng nhập. Vào Nhân viên sale → Mở Chrome để đăng nhập lại")
        queue = []  # (cand, direction, keyword)
        if urls:
            queue = [({"href": u, "name": ""}, None, "dán link") for u in urls]
        else:  # quay lại tìm SĐT cho người đang bán hàng nhưng lần trước chưa thấy số
            for r in retry_no_phone():
                queue.append(({"href": r["account_url"], "name": r["account_name"], "_retry": True}, r["direction"], r["keyword"]))
        for step in plan or []:
            pf, q = step["platform"], step["keyword"]
            if pf in blocked:
                continue
            workflows.set_status("mai", "working", f"Tìm trên {PLATFORM_TXT[pf]}: {q}")
            workflows.set_status(agent, "working", f"Mở trang tìm kiếm {PLATFORM_TXT[pf]} cho Mai")
            kinds = ["pages", "posts"] if pf == "facebook" else ["users"]
            for kind in kinds:
                try:
                    rows, blk = _search(page, pf, q, kind)
                except B.Blocked:
                    raise
                except Exception as e:
                    print("[prospect search]", e)
                    rows, blk = [], False
                if blk:
                    blocked.add(pf)
                    res["blocked"].append(PLATFORM_TXT[pf])
                    break
                for r in rows:
                    if find_dup(r["href"], [], r["name"], pf):
                        res["dup"].add(canon(r["href"]))
                        continue
                    queue.append((r, step["direction"], q))
                    res["found"] += 1
                B._pause(page, 4, 9)
        seen = set()
        for cand, d, q in queue:
            if res["inspected"] >= limit and not urls:
                break
            c = canon(cand["href"])
            if c in seen:
                continue
            seen.add(c)
            pf = platform_of(c)
            if pf != "facebook" and s().get(f"prospect_{pf}", "0") != "1" and not urls:
                continue
            if pf in blocked:
                save(cand, None, d, q, acc_id, status="needs_manual")
                res["manual"] += 1
                continue
            nm = cand.get("name") or c
            workflows.set_status("mai", "working", f"Đang nghiên cứu: {nm[:50]}")
            workflows.set_status(agent, "working", f"Mở trang {nm[:40]} cho Mai xem")
            snip = cand.get("snippet") or ""
            try:
                a, blk = inspect(page, c, snip if PHONE_RX.search(snip) else "")
            except B.Blocked:
                raise
            except Exception as e:
                print("[prospect inspect]", c, e)
                a, blk = None, False
            if blk or a is None:
                if blk:
                    blocked.add(pf)
                    res["blocked"].append(PLATFORM_TXT[pf])
                save(cand, None, d, q, acc_id, status="needs_manual")
                res["manual"] += 1
                continue
            if not cand.get("name"):
                cand["name"] = a.get("page_name") or c
            r = save(cand, a, d, q, acc_id)
            if r.get("phone") and r.get("lead_id"):
                res["phones"].append(r)
            res["inspected"] += 1
            res["grades"][r["grade"] or "D"] += 1
            res["new"].append(r)
            B._pause(page, 6, 14)
    except B.Blocked as e:
        B._block(acc_id, str(e))
    finally:
        try:
            ctx.close()
        except Exception:
            pass
        workflows.set_status("mai", "idle", "Xong lượt tìm khách")
        workflows.set_status(agent, "idle", "Chờ việc tiếp theo")
    _report(res, notify, bool(urls))
    return res


def _report(res: dict, notify: str | None, by_link: bool):
    g = res["grades"]
    ph = [r for r in res["phones"] if r.get("_crm_new") or by_link]
    head = (f"Mai {'phân tích link xong' if by_link else 'tìm khách sỉ xong'}: tìm được {len(res['phones'])} SĐT khách đang bán hàng"
            if res["phones"] else f"Mai {'phân tích link xong' if by_link else 'tìm khách sỉ xong'}: chưa tìm được SĐT mới")
    msg = (head + f" (xem {res['inspected']} tài khoản: A {g['A']}, B {g['B']}, C {g['C']}, D {g['D']})"
           + (f"; {res['manual']} tài khoản cần sếp xem tay" if res["manual"] else "")
           + (f"; {', '.join(sorted(set(res['blocked'])))} yêu cầu đăng nhập/xác minh nên dừng (không vượt qua)" if res["blocked"] else "")
           + (f"; bỏ qua {len(res['dup'])} tài khoản đã có trong danh sách" if res["dup"] else "") + ".")
    if ph:
        msg += " Đã chuyển sếp: " + ", ".join(f"{r['shop_name'] or r['account_name']} {r['phone']} ({r['grade']})" for r in ph[:5]) + "."
    db.log("mai", "Tìm khách sỉ", msg[:700])
    if notify:
        import ceo_orders
        ceo_orders.followup(msg, notify)


def alert_text(r: dict) -> str:
    import html
    e = lambda x: html.escape(str(x or ""))
    ev = json.loads(r.get("evidence") or "[]")[:3]
    prods = ", ".join(p["name"] for p in json.loads(r.get("suggested") or "[]"))
    return (f"🎯 <b>Khách sỉ hạng {e(r['grade'])} ({e(r['score'])} điểm)</b>: {e(r['shop_name'] or r['account_name'])}\n"
            f"{e(PLATFORM_TXT.get(r['platform']))} · {e(SELLER_TYPES.get(r['seller_type'], ''))}\n{e(r['account_url'])}\n"
            + (f"📞 {e(r['phone'])}\n" if r.get("phone") else "")
            + "Bằng chứng:\n" + "\n".join(f"• {e(x['text'][:120])}" for x in ev)
            + (f"\nĐề xuất: {e(prods)}" if prods else "") + f"\n➡️ {e(r['next_action'])}")


# ---------------------------------------------------------------- giao việc
def retry_no_phone(limit: int = 3) -> list[dict]:
    """Người đang bán hàng (A/B/C) mà lần trước chưa thấy SĐT: quay lại tìm, cách nhau ít nhất 3 ngày, tối đa 3 lần."""
    cut = (db.clock() - timedelta(days=3)).strftime("%Y-%m-%d %H:%M:%S")
    return db.q("""SELECT * FROM prospects WHERE platform='facebook' AND grade IN ('A','B','C') AND COALESCE(phone,'')=''
                   AND status='verified' AND COALESCE(phone_tries,0) < 3
                   AND COALESCE(seller_type,'') NOT IN ('affiliate','koc','store') AND COALESCE(verified_at,'') < ?
                   ORDER BY score DESC LIMIT ?""", (cut, limit))


def platforms_on() -> list[str]:
    st = s()
    return ["facebook"] + [p for p in ("tiktok", "shopee") if st.get(f"prospect_{p}", "0") == "1"]


def plan_for_run(directions: list[int] | None = None, kw: list[str] | None = None) -> list[dict]:
    """Facebook trước: mỗi hướng 2 từ khóa (đổi vòng mỗi ngày). TikTok, Shopee chỉ khi sếp bật."""
    kws = keywords()
    pfs = platforms_on()
    out = []
    if kw:
        for q in kw:
            for pf in pfs:
                out.append({"platform": pf, "direction": (directions or [None])[0], "keyword": q})
        return out
    day = int(db.today().replace("-", "")) % 97
    per = max(1, min(4, int(s().get("prospect_fb_keywords") or 2)))
    for d in directions or [1, 2, 3, 4]:
        pool = kws.get(d) or DEFAULT_KEYWORDS[d]
        for i in range(min(per, len(pool))):
            out.append({"platform": "facebook", "direction": d, "keyword": pool[(day * per + i) % len(pool)]})
    for pf in pfs[1:]:
        d = (directions or [1])[day % len(directions or [1])]
        out.append({"platform": pf, "direction": d, "keyword": (kws.get(d) or DEFAULT_KEYWORDS[d])[0]})
    return out


def start(directions: list[int] | None = None, kw: list[str] | None = None, urls: list[str] | None = None,
          notify: str | None = None) -> dict:
    import browser_poster as B
    import group_finder
    accs = group_finder._working_accounts()
    if not accs:
        raise ValueError("Chưa có nick sale nào đăng nhập để mở trang (Mai cần 1 nick để xem trang công khai)")
    idle = [a for a in accs if not B.busy(a["sale_id"]) and not B.queued(a["sale_id"])] or accs
    last = int(s().get("prospect_last_account") or 0)
    acc = ([a for a in idle if a["id"] > last] or idle)[0]
    db.set_setting("prospect_last_account", str(acc["id"]))
    job_ = {"kind": "prospect", "account": acc["id"], "notify": notify}
    if urls:
        on = platforms_on()
        off = [u for u in urls if platform_of(u) not in on]
        urls = [u for u in urls if u.strip() and platform_of(u) in on]
        if not urls:
            names = sorted({PLATFORM_TXT[platform_of(u)] for u in off})
            raise ValueError(f"{', '.join(names)} đang tắt. Bật lại ở trang Tìm khách sỉ (mục Nguồn tìm) rồi dán link")
        job_["urls"] = urls[:20]
    else:
        job_["plan"] = plan_for_run(directions, kw)
    B.submit(acc["sale_id"], job_)
    import workflows
    workflows.set_status("mai", "working", "Chờ nick sale mở Chrome để tìm khách")
    return {"account": acc["name"], "sale_id": acc["sale_id"], "plan": job_.get("plan"), "urls": job_.get("urls")}


def tick(now):
    st = s()
    if st.get("prospect_enabled", "1") != "1" or st.get("prospect_last") == db.today():
        return
    if now.strftime("%H:%M") >= (st.get("prospect_time") or "14:30"):
        db.set_setting("prospect_last", db.today())
        try:
            start()
        except ValueError:
            pass


# ---------------------------------------------------------------- giao diện
def overview(grade: str = "", platform: str = "", stype: str = "", status: str = "", phone: str = "") -> dict:
    where, args = ["COALESCE(status,'') != 'rejected'" if status != "rejected" else "status='rejected'"], []
    for col, v in (("grade", grade), ("platform", platform), ("seller_type", stype)):
        if v:
            where.append(f"{col}=?")
            args.append(v)
    if status and status != "rejected":
        where.append("status=?")
        args.append(status)
    if phone == "yes":
        where.append("COALESCE(phone,'')!=''")
    elif phone == "no":
        where.append("COALESCE(phone,'')=''")
    rows = db.q(f"""SELECT * FROM prospects WHERE {' AND '.join(where)}
                    ORDER BY CASE WHEN COALESCE(phone,'')!='' AND grade IN ('A','B','C') THEN 0 ELSE 1 END,
                    CASE grade WHEN 'A' THEN 0 WHEN 'B' THEN 1 WHEN 'C' THEN 2 WHEN 'D' THEN 3 ELSE 4 END,
                    score DESC, id DESC LIMIT 200""", tuple(args))
    for r in rows:
        for k in ("evidence", "suggested", "parts"):
            try:
                r[k] = json.loads(r.get(k) or ("[]" if k != "parts" else "{}"))
            except Exception:
                r[k] = [] if k != "parts" else {}
    cnt = {r["k"]: r["n"] for r in db.q("""SELECT COALESCE(grade, status) k, COUNT(*) n FROM prospects
                                          WHERE COALESCE(status,'')!='rejected' GROUP BY 1""")}
    return {"items": rows, "counts": cnt,
            "manual": db.one("SELECT COUNT(*) n FROM prospects WHERE status='needs_manual'")["n"],
            "crm": db.one("SELECT COUNT(*) n FROM prospects WHERE lead_id IS NOT NULL")["n"],
            "phones": db.one("SELECT COUNT(*) n FROM prospects WHERE COALESCE(phone,'')!='' AND grade IN ('A','B','C') AND status!='rejected'")["n"],
            "phones_today": db.one("SELECT COUNT(*) n FROM prospects WHERE COALESCE(phone,'')!='' AND grade IN ('A','B','C') AND created_at>=?",
                                   (db.today(),))["n"],
            "no_phone": db.one("SELECT COUNT(*) n FROM prospects WHERE COALESCE(phone,'')='' AND grade IN ('A','B','C') AND status='verified'")["n"],
            "platforms_on": platforms_on(),
            "directions": DIRECTIONS, "types": SELLER_TYPES, "platforms": PLATFORM_TXT, "keywords": keywords(),
            "settings": {k: st for k, st in s().items() if k.startswith("prospect_")},
            "last": db.one("SELECT detail, created_at FROM activity WHERE agent_id='mai' AND action='Tìm khách sỉ' ORDER BY id DESC LIMIT 1")}

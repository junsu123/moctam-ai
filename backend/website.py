"""Website giới thiệu công ty + Vy (Biên tập Website & SEO).

Vy lên kế hoạch từ khóa, viết bài chuẩn SEO (chấm điểm theo bảng kiểm), CEO kiểm luật quảng cáo, sếp duyệt rồi đăng.
Website là trang tĩnh (HTML thuần, nhanh, không cần máy chủ đặc biệt) dựng vào data/site/:
  /                trang chủ          /gioi-thieu/      giới thiệu nhà máy
  /gia-cong/       dịch vụ gia công   /san-pham/...     sản phẩm (không ghi giá: liên hệ Zalo)
  /tin-tuc/...     bài viết SEO       /lien-he/         liên hệ
  sitemap.xml, robots.txt, 404.html, schema.org (Organization, WebSite, Article, FAQPage, BreadcrumbList, Product)
Xem trước tại /site/ trên máy chạy phần mềm; tải zip hoặc đăng lên hosting qua FTP.
"""
import html
import io
import json
import math
import re
import shutil
import threading
import unicodedata
import zipfile
from datetime import timedelta
from pathlib import Path

import db

SITE_DIR = db.DATA_DIR / "site"
PER_PAGE = 12

SEED_KEYWORDS = [
    ("gia công trà túi lọc", "gia công", "thương mại", 1), ("gia công trà thảo mộc theo yêu cầu", "gia công", "thương mại", 1),
    ("OEM trà túi lọc thương hiệu riêng", "gia công", "thương mại", 1), ("gia công bột ngũ cốc", "gia công", "thương mại", 1),
    ("gia công cà phê hòa tan", "gia công", "thương mại", 2), ("gia công cốm", "gia công", "thương mại", 2),
    ("gia công bột rau củ sấy lạnh", "gia công", "thương mại", 2), ("nguồn hàng trà túi lọc sỉ", "bán sỉ", "thương mại", 1),
    ("nhập sỉ trà thảo mộc giá xưởng", "bán sỉ", "thương mại", 2), ("bỏ sỉ ngũ cốc dinh dưỡng", "bán sỉ", "thương mại", 2),
    ("kinh doanh trà thảo mộc online cần chuẩn bị gì", "kiến thức kinh doanh", "thông tin", 2),
    ("thủ tục công bố sản phẩm trà túi lọc", "pháp lý", "thông tin", 2),
    ("tiêu chuẩn GMP trong sản xuất thực phẩm", "nhà máy", "thông tin", 3),
    ("thiết kế bao bì trà túi lọc", "bao bì", "thông tin", 3),
    ("cách chọn xưởng gia công thực phẩm uy tín", "gia công", "thông tin", 2),
    ("quy trình sản xuất trà túi lọc", "nhà máy", "thông tin", 3),
]


def s() -> dict:
    return db.get_settings()


def _i(k: str, d: int) -> int:
    try:
        return int(float(s().get(k) or d))
    except (TypeError, ValueError):
        return d


def slugify(t: str) -> str:
    t = unicodedata.normalize("NFD", (t or "").lower()).replace("đ", "d")
    t = "".join(c for c in t if unicodedata.category(c) != "Mn")
    return re.sub(r"-+", "-", re.sub(r"[^a-z0-9]+", "-", t)).strip("-")[:75].strip("-")


def plain(t: str) -> str:
    return slugify(t).replace("-", " ")


def seed():
    if db.one("SELECT COUNT(*) n FROM site_keywords")["n"]:
        return
    for kw, cluster, intent, pr in SEED_KEYWORDS:
        db.run("INSERT OR IGNORE INTO site_keywords(keyword, cluster, intent, priority, status, source, created_at) VALUES (?,?,?,?,?,?,?)",
               (kw, cluster, intent, pr, "planned", "vy", db.now()))


def company() -> dict:
    st = s()
    name = st.get("site_name") or st.get("company_name") or "MỘC TÂM"
    return {"name": name, "legal": st.get("site_legal_name") or name, "tagline": st.get("site_tagline") or "",
            "domain": (st.get("site_domain") or "").strip().rstrip("/"), "about": st.get("site_about") or "",
            "address": st.get("site_address") or "", "email": st.get("site_email") or "",
            "phone": re.sub(r"\D", "", st.get("site_phone") or st.get("price_zalo") or "0386992326"),
            "certs": st.get("site_certs") or "GMP – ISO – FDA – VSATTP", "founded": st.get("site_founded") or "",
            "color": st.get("site_color") or "#2f5d3a", "ga": (st.get("site_ga_id") or "").strip()}


def prompt_block() -> str:
    c = company()
    return (f"\n\nWEBSITE CÔNG TY bạn phụ trách: {c['name']} ({c['domain'] or 'chưa có tên miền'}). Nhà máy đạt {c['certs']}. "
            "Viết bài chuẩn SEO tiếng Việt cho người bán hàng online, chủ thương hiệu tìm xưởng gia công và nguồn sỉ. "
            "Quy tắc: 1 từ khóa chính mỗi bài, có trong tiêu đề, câu đầu, ít nhất 1 tiêu đề H2, thẻ mô tả; 900–1500 chữ; "
            "4–7 mục H2; đoạn ngắn; có FAQ 3–5 câu; liên kết tới trang sản phẩm, gia công, liên hệ; không nhồi từ khóa; "
            f"không ghi giá (liên hệ Zalo {c['phone']}); không hứa công dụng chữa bệnh; chỉ nói điều nhà máy chứng minh được.")


# ---------------------------------------------------------------- nội dung: định dạng gọn kiểu Markdown
def md_html(body: str) -> str:
    """## H2, ### H3, - gạch đầu dòng, 1. danh sách số, **đậm**, [chữ](/link/)."""
    out, lst = [], None

    def inline(x: str) -> str:
        x = html.escape(x, quote=False)
        x = re.sub(r"\*\*(.+?)\*\*", r"<strong>\1</strong>", x)
        return re.sub(r"\[([^\]]+)\]\(([^)\s]+)\)", lambda m: f'<a href="{html.escape(m.group(2))}">{m.group(1)}</a>', x)

    def close():
        nonlocal lst
        if lst:
            out.append(f"</{lst}>")
            lst = None
    for raw in (body or "").splitlines():
        ln = raw.strip()
        if not ln:
            close()
            continue
        if ln.startswith("### "):
            close(); out.append(f"<h3>{inline(ln[4:])}</h3>")
        elif ln.startswith("## "):
            close(); out.append(f'<h2 id="{slugify(ln[3:])}">{inline(ln[3:])}</h2>')
        elif re.match(r"^[-*•]\s+", ln):
            if lst != "ul":
                close(); out.append("<ul>"); lst = "ul"
            item = re.sub(r"^[-*•]\s+", "", ln)
            out.append("<li>" + inline(item) + "</li>")
        elif re.match(r"^\d+[.)]\s+", ln):
            if lst != "ol":
                close(); out.append("<ol>"); lst = "ol"
            item = re.sub(r"^\d+[.)]\s+", "", ln)
            out.append("<li>" + inline(item) + "</li>")
        else:
            close(); out.append(f"<p>{inline(ln)}</p>")
    close()
    return "\n".join(out)


def text_of(body: str) -> str:
    t = re.sub(r"\[([^\]]+)\]\([^)]+\)", r"\1", body or "")
    return re.sub(r"[#*•]", " ", t)


def words(t: str) -> int:
    return len(re.findall(r"\w+", t or ""))


# ---------------------------------------------------------------- bảng kiểm SEO
def seo_check(p: dict) -> dict:
    kw = (p.get("keyword") or "").strip()
    k = plain(kw)
    body = p.get("body") or ""
    txt = text_of(body)
    W = words(txt)
    items = []

    def add(key, label, ok, pts, mx, tip=""):
        items.append({"key": key, "label": label, "ok": bool(ok), "points": pts if ok else (pts if isinstance(ok, float) else 0),
                      "max": mx, "tip": "" if ok else tip})
    has = lambda t: bool(k) and k in plain(t or "")
    title, mt, md = p.get("title") or "", p.get("meta_title") or "", p.get("meta_desc") or ""
    add("kw_title", "Từ khóa chính có trong tiêu đề", has(title), 10, 10, f"đưa “{kw}” vào tiêu đề, càng gần đầu càng tốt")
    add("title_len", "Tiêu đề dài 30–65 ký tự", 30 <= len(title) <= 65, 5, 5, f"tiêu đề đang {len(title)} ký tự")
    add("meta_title", "Thẻ tiêu đề (title) 30–60 ký tự, có từ khóa", 30 <= len(mt) <= 60 and has(mt), 10, 10,
        f"thẻ tiêu đề đang {len(mt)} ký tự" + ("" if has(mt) else ", chưa có từ khóa"))
    add("meta_desc", "Mô tả (meta description) 120–160 ký tự, có từ khóa", 120 <= len(md) <= 160 and has(md), 10, 10,
        f"mô tả đang {len(md)} ký tự" + ("" if has(md) else ", chưa có từ khóa"))
    sl = p.get("slug") or ""
    add("slug", "Đường dẫn ngắn, không dấu, có từ khóa", sl and len(sl) <= 75 and slugify(kw)[:30] in sl, 5, 5, "đặt đường dẫn theo từ khóa")
    first = " ".join(txt.split()[:110])
    add("kw_first", "Từ khóa xuất hiện trong 100 chữ đầu", has(first), 10, 10, "nhắc từ khóa ngay đoạn mở đầu")
    h2 = re.findall(r"^##\s+(.+)$", body, re.M)
    add("h2", "Có ít nhất 4 mục H2, 1 mục chứa từ khóa", len(h2) >= 4 and any(has(h) or any(w in plain(h) for w in k.split()[:2]) for h in h2),
        10, 10, f"đang có {len(h2)} mục H2")
    add("length", "Bài dài từ 900 chữ (600 chữ được nửa điểm)", W >= 900, 10, 10, f"bài đang {W} chữ")
    if 600 <= W < 900:
        items[-1].update(points=5)
    cnt = len(re.findall(re.escape(k), plain(txt))) if k else 0
    dens = cnt * len(k.split()) / max(W, 1) * 100
    add("density", "Mật độ từ khóa 0,5%–2,5% (không nhồi)", 0.5 <= dens <= 2.5, 5, 5, f"mật độ {dens:.1f}% ({cnt} lần)")
    links = re.findall(r"\]\((/[^)]*)\)", body)
    add("links", "Có ít nhất 2 liên kết nội bộ (sản phẩm, gia công, liên hệ)", len(links) >= 2, 10, 10, f"đang có {len(links)} liên kết nội bộ")
    faq = p.get("faq") or []
    if isinstance(faq, str):
        try:
            faq = json.loads(faq or "[]")
        except Exception:
            faq = []
    add("faq", "Có 3 câu hỏi thường gặp (FAQ) trở lên", len(faq) >= 3, 5, 5, f"đang có {len(faq)} câu hỏi")
    add("cover", "Có ảnh đại diện, chữ thay thế (alt) có từ khóa", bool(p.get("cover")) and has(p.get("cover_alt") or ""), 5, 5,
        "chọn ảnh và ghi chữ thay thế có từ khóa")
    paras = [x for x in re.split(r"\n\s*\n|\n", body) if x.strip() and not x.strip().startswith(("#", "-", "*"))]
    avg = sum(words(x) for x in paras) / max(len(paras), 1)
    add("readable", "Đoạn văn ngắn, dễ đọc trên điện thoại (trung bình dưới 90 chữ/đoạn)", avg <= 90, 5, 5, f"trung bình {avg:.0f} chữ/đoạn")
    score = sum(i["points"] for i in items)
    # luật quảng cáo (trùng với luật cả đội): hứa chữa bệnh, "nhất", cam kết tuyệt đối
    policy = []
    try:
        import fb_policy
        full = "\n".join([title, md, txt] + [f"{q.get('q', '')} {q.get('a', '')}" for q in faq])
        policy = [x for x in fb_policy.check_text(full) if x["rule"] in ("health_claims", "superlatives", "guarantee", "links")]
    except Exception as e:
        print("[seo policy]", e)
    if any(x["level"] == "high" for x in policy):
        score = min(score, 40)
    elif policy:
        score = max(0, score - 5 * len(policy))
    return {"score": score, "items": items, "words": W, "density": round(dens, 2), "policy": policy,
            "ok": score >= _i("site_min_seo", 75) and not any(x["level"] == "high" for x in policy)}


# ---------------------------------------------------------------- Vy viết bài
def _products(limit: int = 6) -> list[dict]:
    return db.q("SELECT * FROM products WHERE COALESCE(is_general,0)=0 ORDER BY hot DESC, id LIMIT ?", (limit,))


def _related_products(kw: str, n: int = 3) -> list[dict]:
    k = set(plain(kw).split())
    rows = _products(40)
    rows.sort(key=lambda p: -len(k & set(plain(f"{p['name']} {p.get('category') or ''}").split())))
    return rows[:n]


def _offline_article(kw: str) -> dict:
    """Bài viết khi chưa có AI: dựng từ thông tin nhà máy và sản phẩm thật, đủ cấu trúc SEO."""
    c = company()
    prods = _related_products(kw)
    K = kw[0].upper() + kw[1:]
    plinks = ", ".join(f"[{p['name']}](/san-pham/{slugify(p['name'])}/)" for p in prods) or "[các dòng sản phẩm](/san-pham/)"
    title = f"{K}: quy trình, tiêu chuẩn và kinh nghiệm chọn xưởng"
    if len(title) > 65:
        title = f"{K}: quy trình và kinh nghiệm chọn xưởng"[:65]
    body = f"""{K} là lựa chọn của nhiều người bán hàng online và chủ thương hiệu muốn có sản phẩm riêng mà không phải tự đầu tư nhà xưởng. Bài viết này chia sẻ từ kinh nghiệm thực tế của nhà máy {c['name']}: quy trình làm việc, tiêu chuẩn sản xuất, chi phí cần chuẩn bị và những lưu ý để sản phẩm ra thị trường an toàn, đúng luật.

Nếu bạn đang bán trên Facebook, TikTok Shop, Shopee hay có hệ thống đại lý, phần dưới đây giúp bạn hình dung các bước từ ý tưởng tới thành phẩm.

## {K} là gì và phù hợp với ai?

Hiểu đơn giản, bạn đặt nhà máy sản xuất theo công thức, quy cách và bao bì mang thương hiệu của bạn. Nhà máy lo nguyên liệu, máy móc, kiểm soát chất lượng; bạn tập trung vào bán hàng và xây thương hiệu.

Hình thức này phù hợp với:
- Người bán hàng online muốn có sản phẩm riêng để tăng biên lợi nhuận và giữ chân khách.
- Chủ shop, đại lý, nhà phân phối muốn mở rộng danh mục sản phẩm.
- Người mới bắt đầu kinh doanh cần nhập số lượng vừa phải để thử thị trường.
- Thương hiệu đã có tên tuổi muốn phát triển thêm dòng sản phẩm mới.

## Quy trình làm việc với nhà máy

Một dự án thường đi qua các bước sau, mỗi bước đều có xác nhận bằng văn bản để hai bên dễ theo dõi:

1. Trao đổi nhu cầu: dòng sản phẩm, quy cách đóng gói, số lượng dự kiến, kênh bán.
2. Chọn công thức có sẵn hoặc phát triển công thức riêng, làm mẫu thử để bạn đánh giá hương vị.
3. Thiết kế bao bì theo yêu cầu, kiểm tra thông tin ghi nhãn theo quy định.
4. Hoàn thiện hồ sơ công bố sản phẩm trước khi bán.
5. Sản xuất lô hàng, kiểm tra chất lượng từng lô, đóng gói và giao hàng toàn quốc.

Thời gian cho lô đầu tiên phụ thuộc vào việc bạn dùng công thức có sẵn hay phát triển mới. Dùng công thức có sẵn giúp rút ngắn đáng kể thời gian ra mắt.

## Tiêu chuẩn nhà máy cần có

Khi chọn đơn vị {kw}, điều quan trọng nhất là năng lực sản xuất và hồ sơ pháp lý. Nhà máy {c['name']} sản xuất theo các tiêu chuẩn {c['certs']}, với hơn 100 mã sản phẩm ở các nhóm trà thảo mộc, cà phê, ngũ cốc, bột và cốm.

Bạn nên hỏi rõ:
- Nhà máy có giấy chứng nhận cơ sở đủ điều kiện an toàn thực phẩm không.
- Nguồn nguyên liệu lấy từ đâu, có phiếu kiểm nghiệm theo lô không.
- Quy trình kiểm soát chất lượng trước khi xuất hàng ra sao.
- Có hỗ trợ hồ sơ công bố sản phẩm và ghi nhãn đúng quy định không.

Một nhà máy minh bạch sẽ sẵn sàng cho bạn xem hồ sơ và mời bạn tham quan dây chuyền.

## Chi phí và số lượng đặt hàng tối thiểu

Chi phí của một dự án gồm phần sản xuất, bao bì và hồ sơ pháp lý. Mỗi dòng sản phẩm có số lượng đặt hàng tối thiểu khác nhau tùy quy cách đóng gói. Để nhận báo giá sát nhất, bạn chỉ cần cho nhà máy biết dòng sản phẩm, quy cách và số lượng dự kiến.

Giá sỉ và giá gia công tại {c['name']} được báo trực tiếp theo từng nhu cầu. Liên hệ Zalo {c['phone']} để nhận catalog và bảng giá cập nhật.

## Gợi ý sản phẩm để bắt đầu

Nếu chưa có công thức riêng, bạn có thể bắt đầu từ các sản phẩm nhà máy đang sản xuất ổn định như {plinks}. Đây là những dòng được nhiều người bán online lựa chọn vì dễ giới thiệu, dễ đóng gói và phù hợp nhiều kênh bán.

Bạn cũng có thể xem toàn bộ dịch vụ tại trang [gia công trọn gói](/gia-cong/) để biết các hạng mục nhà máy hỗ trợ.

## Những lưu ý để bán hàng đúng luật

Sản phẩm thực phẩm khi quảng cáo cần trung thực về thành phần, quy cách và nguồn gốc, không nói quá công dụng. Nội dung trên bao bì và bài bán hàng nên tập trung vào nguyên liệu, quy trình, tiêu chuẩn nhà máy và cách dùng.

Một số lưu ý khi bán online:
- Giữ đầy đủ hồ sơ công bố, phiếu kiểm nghiệm để trả lời khách khi cần.
- Ghi nhãn đầy đủ: tên sản phẩm, thành phần, hạn dùng, cơ sở sản xuất.
- Chụp ảnh sản phẩm thật, mô tả đúng quy cách.

## Vì sao nên làm việc với {c['name']}

{c['name']} nhận sỉ và gia công trọn gói: bỏ sỉ toàn quốc, gia công thương hiệu riêng, thiết kế bao bì theo yêu cầu, hỗ trợ xây dựng và phát triển sản phẩm từ khâu sản xuất tới hoàn thiện. Đội ngũ nhà máy đồng hành cùng người mới bắt đầu kinh doanh cũng như các thương hiệu muốn mở rộng dòng sản phẩm.

Liên hệ qua [trang liên hệ](/lien-he/) hoặc Zalo {c['phone']} để được tư vấn và gửi mẫu thử.
"""
    faq = [{"q": f"{K} cần số lượng tối thiểu bao nhiêu?",
            "a": f"Tùy dòng sản phẩm và quy cách đóng gói. Bạn gửi nhu cầu qua Zalo {c['phone']} để nhà máy báo số lượng tối thiểu và báo giá cụ thể."},
           {"q": "Nhà máy có hỗ trợ thiết kế bao bì và hồ sơ công bố không?",
            "a": "Có. Nhà máy hỗ trợ thiết kế bao bì theo yêu cầu và hướng dẫn hồ sơ công bố sản phẩm trước khi bán."},
           {"q": "Tôi có thể nhận mẫu thử trước khi đặt hàng không?",
            "a": "Có. Sau khi chốt công thức, nhà máy làm mẫu để bạn đánh giá hương vị và quy cách trước khi sản xuất lô hàng."},
           {"q": "Giá sỉ và giá gia công xem ở đâu?",
            "a": f"Giá được báo trực tiếp theo số lượng và quy cách. Liên hệ Zalo {c['phone']} để nhận catalog và bảng giá."}]
    md = f"{K} tại nhà máy đạt {c['certs']}: quy trình, tiêu chuẩn, mẫu thử, bao bì. Nhận báo giá qua Zalo {c['phone']}."
    if len(md) > 160:
        md = md[:157].rsplit(" ", 1)[0] + "..."
    while len(md) < 120:
        md += " Tư vấn miễn phí."
    mt = f"{K} | {c['name']}"
    if len(mt) > 60:
        mt = K[:60]
    return {"title": title, "meta_title": mt, "meta_desc": md[:160], "body": body.strip(), "faq": faq,
            "excerpt": f"Kinh nghiệm thực tế về {kw}: quy trình, tiêu chuẩn nhà máy, chi phí và lưu ý pháp lý khi bán hàng.",
            "product_ids": [p["id"] for p in prods]}


def _ai_article(kw: str, fix: list[str] | None = None, prev: dict | None = None) -> dict | None:
    from llm import llm
    if not llm.live:
        return None
    from agents import system_prompt
    c = company()
    prods = _related_products(kw, 5)
    plist = "\n".join(f"- {p['name']} ({p.get('category') or ''}): /san-pham/{slugify(p['name'])}/ — {(p.get('description') or '')[:160]}"
                      for p in prods)
    try:
        import knowledge
        kb = knowledge.block("vy", kw)
    except Exception:
        kb = ""
    ask = (f"Viết bài blog chuẩn SEO tiếng Việt cho website nhà máy {c['name']} (đạt {c['certs']}, hơn 100 mã sản phẩm trà, cà phê, "
           f"ngũ cốc, bột, cốm; nhận sỉ toàn quốc và gia công thương hiệu riêng). Từ khóa chính: “{kw}”.\n"
           f"Sản phẩm thật để liên kết nội bộ:\n{plist or '- /san-pham/'}\nTrang khác: /gia-cong/, /lien-he/.\n{kb}\n"
           "Yêu cầu: 1000–1400 chữ; mở bài nhắc từ khóa trong câu đầu; 5–7 mục '## H2' (1 mục có từ khóa), có thể '### H3'; "
           "đoạn ngắn 2–4 câu; gạch đầu dòng '- '; ít nhất 3 liên kết nội bộ dạng [chữ](/duong-dan/); không ghi giá tiền "
           f"(mời liên hệ Zalo {c['phone']}); không hứa chữa bệnh, giảm cân; không dùng 'nhất', 'số 1'; không bịa số liệu, chứng nhận.\n"
           "Trả JSON: {\"title\": \"30-65 ký tự, có từ khóa\", \"meta_title\": \"30-60 ký tự, có từ khóa\", "
           "\"meta_desc\": \"120-160 ký tự, có từ khóa\", \"excerpt\": \"1-2 câu\", \"body\": \"nội dung dạng ## / - / [link](/...)\", "
           "\"faq\": [{\"q\": \"...\", \"a\": \"...\"}] (4 câu)}")
    if fix and prev:
        ask += "\n\nBản trước chưa đạt, sửa các điểm sau và giữ phần tốt: " + "; ".join(fix) + \
               f"\nBản trước:\n{json.dumps({k: prev.get(k) for k in ('title', 'meta_title', 'meta_desc', 'body')}, ensure_ascii=False)[:6000]}"
    d = llm.json(system_prompt("vy", s()), ask, mock=None, max_tokens=4000, task="posts")
    if not isinstance(d, dict) or not d.get("body"):
        return None
    d["product_ids"] = [p["id"] for p in prods[:3]]
    return d


def _cover_for(product_ids: list[int], slug: str) -> str | None:
    """Ảnh đại diện bài: lấy 1 ảnh sản phẩm thật (thư mục ảnh tổng hợp hoặc của sản phẩm), thu nhỏ cho web."""
    try:
        import media_folder
        pool = []
        for pid in product_ids or [None]:
            pool = media_folder.pool_for({"product_id": pid})
            if pool:
                break
        if not pool:
            return None
        src = Path(pool[hash(slug) % len(pool)])
        dst_dir = db.DATA_DIR / "site_media"
        dst_dir.mkdir(parents=True, exist_ok=True)
        dst = dst_dir / f"{slug}.jpg"
        try:
            from PIL import Image
            im = Image.open(src).convert("RGB")
            im.thumbnail((1200, 1200))
            im.save(dst, "JPEG", quality=82, optimize=True)
        except Exception:
            dst = dst_dir / f"{slug}{src.suffix.lower()}"
            shutil.copyfile(src, dst)
        return dst.name
    except Exception as e:
        print("[site cover]", e)
        return None


def write(keyword: str | None = None, kid: int | None = None) -> dict:
    """Vy viết 1 bài cho từ khóa (hoặc từ khóa ưu tiên kế tiếp), tự chấm SEO, sửa tối đa 2 lần."""
    import workflows
    seed()
    if kid:
        k = db.one("SELECT * FROM site_keywords WHERE id=?", (kid,))
    elif keyword:
        db.run("INSERT OR IGNORE INTO site_keywords(keyword, cluster, intent, priority, status, source, created_at) VALUES (?,?,?,?,?,?,?)",
               (keyword.strip(), "", "", 2, "planned", "boss", db.now()))
        k = db.one("SELECT * FROM site_keywords WHERE keyword=?", (keyword.strip(),))
    else:
        k = db.one("SELECT * FROM site_keywords WHERE status='planned' ORDER BY priority, id LIMIT 1")
    if not k:
        raise ValueError("Hết từ khóa trong kế hoạch. Thêm từ khóa mới ở mục Website")
    kw = k["keyword"]
    workflows.set_status("vy", "working", f"Viết bài SEO: {kw}")
    try:
        d = _ai_article(kw) or _offline_article(kw)
        slug = _unique_slug(slugify(d.get("slug") or kw))
        d.update(keyword=kw, slug=slug, cover_alt=f"{kw[0].upper() + kw[1:]} tại nhà máy {company()['name']}")
        d["cover"] = _cover_for(d.get("product_ids") or [], slug)
        r = seo_check(d)
        for _ in range(2):  # sửa theo bảng kiểm
            if r["ok"]:
                break
            fix = [f"{i['label']}: {i['tip']}" for i in r["items"] if not i["ok"]] + [f"luật: {x['msg']}" for x in r["policy"]]
            d2 = _ai_article(kw, fix, d)
            if not d2:
                d = _fix_basic(d, r)
            else:
                d2.update(keyword=kw, slug=slug, cover=d.get("cover"), cover_alt=d["cover_alt"])
                d = d2
            r = seo_check(d)
        pid = db.run("""INSERT INTO site_posts(keyword, title, slug, meta_title, meta_desc, excerpt, body, faq, product_ids, cover, cover_alt,
                        status, seo_score, seo_report, policy_note, words, author, created_at, updated_at)
                        VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,'vy',?,?)""",
                     (kw, d["title"], slug, d["meta_title"], d["meta_desc"], d.get("excerpt") or "", d["body"],
                      json.dumps(d.get("faq") or [], ensure_ascii=False), json.dumps(d.get("product_ids") or []), d.get("cover"),
                      d["cover_alt"], "review", r["score"], json.dumps(r, ensure_ascii=False),
                      "; ".join(x["msg"] for x in r["policy"]) or None, r["words"], db.now(), db.now()))
        db.run("UPDATE site_keywords SET status='written', post_id=? WHERE id=?", (pid, k["id"]))
        db.set_setting("site_last_write", db.now())
        db.log("vy", "Viết bài website", f"“{d['title']}” (từ khóa: {kw}), {r['words']} chữ, điểm SEO {r['score']}/100"
               + ("" if r["ok"] else ". Chưa đạt, chờ sếp xem") + ".")
        if s().get("site_auto_publish") == "1" and r["ok"]:
            publish(pid)
        return {"id": pid, "score": r["score"], "ok": r["ok"]}
    finally:
        workflows.set_status("vy", "idle", "Chờ lịch viết bài tiếp theo")


def _fix_basic(d: dict, r: dict) -> dict:
    """Sửa nhanh phần đo được khi chưa có AI: độ dài thẻ, từ khóa trong tiêu đề, mô tả."""
    kw = d["keyword"]
    K = kw[0].upper() + kw[1:]
    if plain(kw) not in plain(d["title"]):
        d["title"] = f"{K}: {d['title']}"[:65]
    if not (30 <= len(d["meta_title"]) <= 60) or plain(kw) not in plain(d["meta_title"]):
        d["meta_title"] = f"{K} | {company()['name']}"[:60]
    md = d["meta_desc"]
    if plain(kw) not in plain(md):
        md = f"{K}: {md}"
    d["meta_desc"] = (md[:157].rsplit(" ", 1)[0] + "...") if len(md) > 160 else md.ljust(120, " ").strip() + ("" if len(md) >= 120 else " Liên hệ để được tư vấn.")
    return d


def _unique_slug(base: str, pid: int | None = None) -> str:
    sl, i = base or "bai-viet", 2
    while db.one("SELECT id FROM site_posts WHERE slug=? AND id != ?", (sl, pid or 0)):
        sl, i = f"{base}-{i}", i + 1
    return sl


def get(pid: int) -> dict | None:
    p = db.one("SELECT * FROM site_posts WHERE id=?", (pid,))
    if p:
        p["faq"] = json.loads(p["faq"] or "[]")
        p["product_ids"] = json.loads(p["product_ids"] or "[]")
        p["seo"] = json.loads(p["seo_report"] or "{}")
    return p


def update(pid: int, data: dict) -> dict:
    p = get(pid)
    if not p:
        raise ValueError("Không có bài này")
    for k in ("title", "meta_title", "meta_desc", "excerpt", "body", "keyword", "cover_alt", "note"):
        if data.get(k) is not None:
            p[k] = data[k]
    if data.get("slug"):
        p["slug"] = _unique_slug(slugify(data["slug"]), pid)
    if data.get("faq") is not None:
        p["faq"] = [x for x in data["faq"] if isinstance(x, dict) and x.get("q")]
    r = seo_check(p)
    db.run("""UPDATE site_posts SET title=?, meta_title=?, meta_desc=?, excerpt=?, body=?, keyword=?, cover_alt=?, slug=?, faq=?, note=?,
              seo_score=?, seo_report=?, policy_note=?, words=?, updated_at=? WHERE id=?""",
           (p["title"], p["meta_title"], p["meta_desc"], p["excerpt"], p["body"], p["keyword"], p["cover_alt"], p["slug"],
            json.dumps(p["faq"], ensure_ascii=False), p.get("note"), r["score"], json.dumps(r, ensure_ascii=False),
            "; ".join(x["msg"] for x in r["policy"]) or None, r["words"], db.now(), pid))
    if p["status"] == "published":
        build()
    return get(pid)


def publish(pid: int) -> dict:
    p = get(pid)
    if not p:
        raise ValueError("Không có bài này")
    r = seo_check(p)
    if any(x["level"] == "high" for x in r["policy"]):
        raise ValueError("Bài phạm luật quảng cáo: " + "; ".join(x["msg"] for x in r["policy"]))
    db.run("UPDATE site_posts SET status='published', published_at=COALESCE(published_at, ?), updated_at=? WHERE id=?",
           (db.now(), db.now(), pid))
    db.log("vy", "Đăng bài website", f"“{p['title']}” lên mục Tin tức")
    build()
    return get(pid)


def unpublish(pid: int) -> dict:
    db.run("UPDATE site_posts SET status='review', updated_at=? WHERE id=?", (db.now(), pid))
    build()
    return get(pid)


def delete(pid: int):
    p = get(pid)
    if p:
        db.run("DELETE FROM site_posts WHERE id=?", (pid,))
        db.run("UPDATE site_keywords SET status='planned', post_id=NULL WHERE post_id=?", (pid,))
        if p["status"] == "published":
            build()


# ---------------------------------------------------------------- dựng website tĩnh
CSS = """:root{--c:%(color)s;--ink:#1d2420;--mut:#5d6a62;--bg:#fbfaf6;--pan:#fff;--line:#e4e2da;--soft:#eef3ee}
*{box-sizing:border-box}html{-webkit-text-size-adjust:100%%}body{margin:0;font:16px/1.65 system-ui,-apple-system,"Segoe UI",Roboto,Arial,sans-serif;color:var(--ink);background:var(--bg)}
a{color:var(--c)}img{max-width:100%%;height:auto;display:block}
.wrap{max-width:1120px;margin:0 auto;padding:0 16px}
header.top{background:var(--pan);border-bottom:1px solid var(--line);position:sticky;top:0;z-index:5}
header.top .wrap{display:flex;align-items:center;justify-content:space-between;gap:12px;min-height:60px;flex-wrap:wrap}
.logo{font-weight:800;font-size:20px;color:var(--c);text-decoration:none;letter-spacing:.5px}
nav.menu{display:flex;gap:4px;flex-wrap:wrap}nav.menu a{padding:8px 10px;border-radius:8px;text-decoration:none;color:var(--ink);font-size:15px}
nav.menu a:hover,nav.menu a[aria-current]{background:var(--soft);color:var(--c)}
.hero{background:linear-gradient(135deg,var(--c),#16301f);color:#fff;padding:56px 0}
.hero h1{font-size:clamp(28px,4vw,44px);line-height:1.2;margin:0 0 12px}.hero p{font-size:18px;max-width:720px;opacity:.95;margin:0 0 20px}
.btn{display:inline-block;padding:12px 20px;border-radius:10px;background:#fff;color:var(--c);font-weight:700;text-decoration:none}
.btn.alt{background:transparent;color:#fff;border:2px solid rgba(255,255,255,.7);margin-left:8px}
section.blk{padding:44px 0}section.blk h2{font-size:clamp(22px,3vw,30px);margin:0 0 16px}
.grid{display:grid;grid-template-columns:repeat(auto-fill,minmax(min(100%%,250px),1fr));gap:16px}
.card{background:var(--pan);border:1px solid var(--line);border-radius:14px;overflow:hidden;display:flex;flex-direction:column}
.card .in{padding:14px 16px;display:flex;flex-direction:column;gap:6px;flex:1}.card h3{margin:0;font-size:18px;line-height:1.35}
.card h3 a{color:var(--ink);text-decoration:none}.card p{margin:0;color:var(--mut);font-size:15px}
.card img{aspect-ratio:4/3;object-fit:cover;width:100%%;background:var(--soft)}
.pill{display:inline-block;background:var(--soft);color:var(--c);border-radius:999px;padding:2px 10px;font-size:13px;font-weight:600}
.feat{display:grid;grid-template-columns:repeat(auto-fill,minmax(min(100%%,230px),1fr));gap:12px}
.feat div{background:var(--pan);border:1px solid var(--line);border-radius:12px;padding:16px}.feat b{display:block;color:var(--c);margin-bottom:4px}
article.post{max-width:780px;margin:0 auto;padding:28px 0 40px}article.post h1{font-size:clamp(26px,3.6vw,38px);line-height:1.25;margin:8px 0}
article.post h2{margin-top:32px;font-size:24px}article.post h3{font-size:19px}article.post .cover{border-radius:14px;margin:16px 0}
.meta{color:var(--mut);font-size:14px}.crumbs{font-size:14px;color:var(--mut);padding-top:16px}.crumbs a{color:var(--mut)}
.toc{background:var(--soft);border-radius:12px;padding:12px 16px;margin:16px 0}.toc ol{margin:6px 0 0;padding-left:20px}
.cta{background:var(--c);color:#fff;border-radius:14px;padding:20px;margin:28px 0}.cta a{color:#fff;font-weight:700}
.faq details{background:var(--pan);border:1px solid var(--line);border-radius:10px;padding:10px 14px;margin:8px 0}
.faq summary{font-weight:700;cursor:pointer}
footer{background:#18241c;color:#cfd8d1;padding:32px 0;margin-top:20px;font-size:15px}footer a{color:#fff}
footer .grid{grid-template-columns:repeat(auto-fill,minmax(min(100%%,240px),1fr))}
.zalo{position:fixed;right:16px;bottom:16px;background:#0068ff;color:#fff;border-radius:999px;padding:12px 18px;font-weight:700;
  text-decoration:none;box-shadow:0 6px 18px rgba(0,0,0,.25);z-index:9}
.pager{display:flex;gap:6px;flex-wrap:wrap;margin-top:20px}.pager a,.pager span{padding:6px 12px;border:1px solid var(--line);border-radius:8px;text-decoration:none}
.pager span{background:var(--c);color:#fff;border-color:var(--c)}
@media (max-width:640px){.btn.alt{margin:8px 0 0}header.top{position:static}header.top .wrap{padding-top:6px;padding-bottom:6px}nav.menu a{padding:6px 8px;font-size:14px}}
"""

MENU = [("/", "Trang chủ"), ("/gioi-thieu/", "Giới thiệu"), ("/gia-cong/", "Gia công"), ("/san-pham/", "Sản phẩm"),
        ("/tin-tuc/", "Tin tức"), ("/lien-he/", "Liên hệ")]


def _abs(path: str) -> str:
    d = company()["domain"]
    return f"{d}{path}" if d else path


def _page(path: str, title: str, desc: str, body: str, ld: list | None = None, og_img: str | None = None, og_type: str = "website") -> str:
    c = company()
    e = html.escape
    nav = "".join(f'<a href="{u}"{" aria-current=page" if (u == path or (u != "/" and path.startswith(u))) else ""}>{n}</a>' for u, n in MENU)
    org = {"@context": "https://schema.org", "@type": "Organization", "name": c["legal"], "alternateName": c["name"],
           "url": _abs("/"), "telephone": c["phone"],
           "contactPoint": {"@type": "ContactPoint", "telephone": c["phone"], "contactType": "sales", "areaServed": "VN",
                            "availableLanguage": "Vietnamese"}}
    if c["email"]:
        org["email"] = c["email"]
    if c["address"]:
        org["address"] = {"@type": "PostalAddress", "streetAddress": c["address"], "addressCountry": "VN"}
    lds = [org] + (ld or [])
    ga = (f'<script async src="https://www.googletagmanager.com/gtag/js?id={e(c["ga"])}"></script><script>window.dataLayer=window.dataLayer||[];'
          f'function gtag(){{dataLayer.push(arguments)}}gtag("js",new Date());gtag("config","{e(c["ga"])}");</script>') if c["ga"] else ""
    img = _abs(og_img) if og_img else ""
    return f"""<!doctype html>
<html lang="vi"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>{e(title)}</title><meta name="description" content="{e(desc)}">
<link rel="canonical" href="{e(_abs(path))}"><meta name="robots" content="index,follow">
<meta property="og:type" content="{og_type}"><meta property="og:title" content="{e(title)}"><meta property="og:description" content="{e(desc)}">
<meta property="og:url" content="{e(_abs(path))}"><meta property="og:site_name" content="{e(c['name'])}"><meta property="og:locale" content="vi_VN">
{f'<meta property="og:image" content="{e(img)}">' if img else ''}<meta name="twitter:card" content="summary_large_image">
<link rel="stylesheet" href="/assets/style.css">
{''.join(f'<script type="application/ld+json">{json.dumps(x, ensure_ascii=False)}</script>' for x in lds)}{ga}
</head><body>
<header class="top"><div class="wrap"><a class="logo" href="/">{e(c['name'])}</a><nav class="menu" aria-label="Menu chính">{nav}</nav></div></header>
<main>{body}</main>
<footer><div class="wrap grid">
<div><b>{e(c['legal'])}</b><br>{e(c['tagline'])}<br>Tiêu chuẩn: {e(c['certs'])}</div>
<div>Zalo / Điện thoại: <a href="https://zalo.me/{c['phone']}">{c['phone']}</a>{f"<br>Email: <a href='mailto:{e(c['email'])}'>{e(c['email'])}</a>" if c['email'] else ''}{f"<br>Địa chỉ: {e(c['address'])}" if c['address'] else ''}</div>
<div>{''.join(f'<a href="{u}">{n}</a><br>' for u, n in MENU[1:])}</div>
</div></footer>
<a class="zalo" href="https://zalo.me/{c['phone']}" rel="nofollow">Chat Zalo</a>
</body></html>"""


def _crumbs(items: list[tuple[str, str]]) -> tuple[str, dict]:
    h = '<nav class="crumbs" aria-label="Đường dẫn">' + " › ".join(
        f'<a href="{u}">{html.escape(n)}</a>' if u else html.escape(n) for u, n in items) + "</nav>"
    ld = {"@context": "https://schema.org", "@type": "BreadcrumbList", "itemListElement": [
        {"@type": "ListItem", "position": i + 1, "name": n, **({"item": _abs(u)} if u else {})} for i, (u, n) in enumerate(items)]}
    return h, ld


def _media_url(name: str | None) -> str | None:
    return f"/media/{name}" if name else None


def _product_pages() -> list[dict]:
    out = []
    for p in db.q("SELECT * FROM products WHERE COALESCE(is_general,0)=0 AND COALESCE(is_sample,0)=0 ORDER BY hot DESC, id"):
        sl = slugify(p["name"])
        img = _cover_for([p["id"]], f"sp-{sl}")
        out.append({**p, "slug": sl, "img": img})
    if not out:  # chưa có sản phẩm thật: dùng cả sản phẩm mẫu để website không trống
        for p in db.q("SELECT * FROM products WHERE COALESCE(is_general,0)=0 ORDER BY id"):
            out.append({**p, "slug": slugify(p["name"]), "img": None})
    return out


def _card(url: str, title: str, text: str, img: str | None, pill: str = "") -> str:
    e = html.escape
    pic = ('<a href="%s"><img src="%s" alt="%s" loading="lazy" width="400" height="300"></a>' % (url, img, e(title))) if img else ""
    tag = ('<span class="pill">%s</span>' % e(pill)) if pill else ""
    return ('<div class="card">%s<div class="in">%s<h3><a href="%s">%s</a></h3><p>%s</p></div></div>'
            % (pic, tag, url, e(title), e(text or "")))


def build() -> dict:
    """Dựng lại toàn bộ website tĩnh vào data/site/."""
    import workflows
    workflows.set_status("vy", "working", "Dựng lại website")
    try:
        return _build()
    finally:
        workflows.set_status("vy", "idle", "Website đã cập nhật")


def _build() -> dict:
    c = company()
    e = html.escape
    tmp = SITE_DIR.with_name("site_tmp")
    shutil.rmtree(tmp, ignore_errors=True)
    (tmp / "assets").mkdir(parents=True)
    (tmp / "assets" / "style.css").write_text(CSS % {"color": c["color"]}, encoding="utf-8")
    pages = {}  # path -> (html, lastmod, priority)
    prods = _product_pages()
    posts = [get(r["id"]) for r in db.q("SELECT id FROM site_posts WHERE status='published' ORDER BY COALESCE(published_at, created_at) DESC")]
    today = db.today()
    zalo = f"https://zalo.me/{c['phone']}"
    services = [("Bỏ sỉ toàn quốc", "Giá xưởng cho shop online, đại lý, nhà phân phối; giao hàng toàn quốc."),
                ("Gia công thương hiệu riêng", "Sản xuất theo công thức và quy cách của bạn, in thương hiệu của bạn."),
                ("Thiết kế bao bì theo yêu cầu", "Thiết kế, in ấn bao bì, hướng dẫn ghi nhãn đúng quy định."),
                ("Phát triển sản phẩm", "Hỗ trợ từ công thức, mẫu thử tới hồ sơ công bố và hoàn thiện sản phẩm.")]
    # trang chủ
    def li(items):
        return "".join("<li>" + x + "</li>" for x in items)
    feat = "".join("<div><b>%s</b>%s</div>" % (e(a), e(b)) for a, b in services)
    prod_cards = "".join(_card("/san-pham/%s/" % p["slug"], p["name"], (p.get("description") or p.get("category") or "")[:120],
                               _media_url(p["img"]), p.get("category") or "") for p in prods[:8])
    news = ""
    if posts:
        news = ('<section class="blk"><div class="wrap"><h2>Kiến thức kinh doanh & gia công</h2><div class="grid">'
                + "".join(_card("/tin-tuc/%s/" % p["slug"], p["title"], p["excerpt"] or p["meta_desc"], _media_url(p["cover"])) for p in posts[:3])
                + '</div><p><a href="/tin-tuc/">Tất cả bài viết →</a></p></div></section>')
    tag = c["tagline"] or "nhà máy sản xuất và gia công thực phẩm"
    home = f"""<section class="hero"><div class="wrap"><h1>{e(c['name'])}: {e(tag)}</h1>
<p>Nhà máy đạt {e(c['certs'])}. Hơn 100 mã sản phẩm: trà thảo mộc, cà phê, ngũ cốc, bột, cốm, detox. Nhận sỉ toàn quốc và gia công trọn gói cho shop online, đại lý, nhà phân phối và thương hiệu riêng.</p>
<a class="btn" href="{zalo}" rel="nofollow">Nhận catalog & báo giá qua Zalo</a><a class="btn alt" href="/gia-cong/">Xem dịch vụ gia công</a></div></section>
<section class="blk"><div class="wrap"><h2>Nhận sỉ & gia công trọn gói</h2><div class="feat">{feat}</div></div></section>
<section class="blk" style="background:#fff"><div class="wrap"><h2>Sản phẩm của nhà máy</h2><div class="grid">{prod_cards}</div>
<p><a href="/san-pham/">Xem tất cả sản phẩm →</a></p></div></section>
{news}
<section class="blk"><div class="wrap"><div class="cta"><b>Cần catalog sản phẩm và bảng giá sỉ / gia công?</b><br>Nhắn Zalo <a href="{zalo}" rel="nofollow">{c['phone']}</a> để được tư vấn trực tiếp, nhận mẫu thử.</div></div></section>"""
    site_ld = {"@context": "https://schema.org", "@type": "WebSite", "name": c["name"], "url": _abs("/"), "inLanguage": "vi"}
    pages["/"] = (_page("/", (c["name"] + " | " + c["tagline"])[:65],
                        ("%s: nhà máy đạt %s, hơn 100 mã trà, cà phê, ngũ cốc, bột. Nhận sỉ toàn quốc, gia công thương hiệu riêng. Zalo %s."
                         % (c["name"], c["certs"], c["phone"]))[:160], home, [site_ld]), today, "1.0")
    # giới thiệu
    about = c["about"] or (c["name"] + " là nhà máy sản xuất thực phẩm đạt " + c["certs"] + ", chuyên các dòng trà túi lọc, cà phê hòa tan, cốm, "
                           "bột thiên nhiên và ngũ cốc. Nhà máy nhận sỉ toàn quốc và gia công trọn gói cho shop online, đại lý, nhà phân phối, "
                           "người mới bắt đầu kinh doanh và các thương hiệu muốn phát triển sản phẩm riêng.")
    cr, cld = _crumbs([("/", "Trang chủ"), (None, "Giới thiệu")])
    about_p = "".join("<p>%s</p>" % e(x) for x in about.splitlines() if x.strip())
    zl = '<a href="%s" rel="nofollow">%s</a>' % (zalo, c["phone"])
    body = ('<div class="wrap">' + cr + '<article class="post"><h1>Giới thiệu nhà máy ' + e(c["name"]) + "</h1>" + about_p
            + "<h2>Năng lực sản xuất</h2><ul>" + li(["Tiêu chuẩn: " + e(c["certs"]), "Hơn 100 mã sản phẩm: trà thảo mộc, cà phê, ngũ cốc, bột, cốm, detox",
                                                   "Nhận sỉ toàn quốc, gia công thương hiệu riêng, thiết kế bao bì"]) + "</ul>"
            + '<div class="cta">Liên hệ Zalo ' + zl + " để tham quan nhà máy và nhận mẫu thử.</div></article></div>")
    pages["/gioi-thieu/"] = (_page("/gioi-thieu/", ("Giới thiệu nhà máy " + c["name"])[:60], about[:155], body, [cld]), today, "0.8")
    # gia công
    steps = ["Trao đổi nhu cầu: dòng sản phẩm, quy cách, số lượng, kênh bán", "Chọn công thức có sẵn hoặc phát triển công thức riêng, làm mẫu thử",
             "Thiết kế bao bì, kiểm tra thông tin ghi nhãn", "Hoàn thiện hồ sơ công bố sản phẩm",
             "Sản xuất, kiểm tra chất lượng từng lô, giao hàng toàn quốc"]
    faq = [("Số lượng gia công tối thiểu là bao nhiêu?", "Tùy dòng sản phẩm và quy cách. Nhắn Zalo %s để được báo cụ thể." % c["phone"]),
           ("Nhà máy có làm bao bì và hồ sơ công bố không?", "Có, nhà máy hỗ trợ thiết kế bao bì và hướng dẫn hồ sơ công bố."),
           ("Có mẫu thử trước khi sản xuất không?", "Có, bạn nhận mẫu để đánh giá trước khi chốt sản xuất.")]
    cr, cld = _crumbs([("/", "Trang chủ"), (None, "Gia công")])
    faq_ld = {"@context": "https://schema.org", "@type": "FAQPage", "mainEntity": [
        {"@type": "Question", "name": q, "acceptedAnswer": {"@type": "Answer", "text": a}} for q, a in faq]}
    svc_ld = {"@context": "https://schema.org", "@type": "Service", "name": "Gia công trà túi lọc, cà phê, ngũ cốc, bột theo yêu cầu",
              "provider": {"@type": "Organization", "name": c["legal"]}, "areaServed": "VN"}
    faq_html = "".join("<details><summary>%s</summary><p>%s</p></details>" % (e(q), e(a)) for q, a in faq)
    body = ('<div class="wrap">' + cr + '<article class="post"><h1>Gia công trà túi lọc, cà phê, ngũ cốc, bột theo yêu cầu</h1>'
            + "<p>%s nhận gia công trọn gói thương hiệu riêng tại nhà máy đạt %s. Bạn tập trung bán hàng, nhà máy lo sản xuất.</p>" % (e(c["name"]), e(c["certs"]))
            + "<h2>Hạng mục nhà máy hỗ trợ</h2><ul>" + li("<b>%s</b>: %s" % (e(a), e(b)) for a, b in services) + "</ul>"
            + "<h2>Quy trình gia công</h2><ol>" + li(e(x) for x in steps) + "</ol>"
            + '<h2>Câu hỏi thường gặp</h2><div class="faq">' + faq_html + "</div>"
            + '<div class="cta">Gửi nhu cầu qua Zalo ' + zl + " để nhận báo giá gia công.</div></article></div>")
    pages["/gia-cong/"] = (_page("/gia-cong/", ("Gia công trà túi lọc, cà phê, ngũ cốc | " + c["name"])[:60],
                                 ("Gia công trọn gói tại nhà máy đạt %s: công thức, mẫu thử, bao bì, hồ sơ công bố, sản xuất và giao hàng toàn quốc."
                                  % c["certs"])[:160], body, [cld, faq_ld, svc_ld]), today, "0.9")
    # sản phẩm
    cr, cld = _crumbs([("/", "Trang chủ"), (None, "Sản phẩm")])
    all_cards = "".join(_card("/san-pham/%s/" % p["slug"], p["name"], (p.get("description") or "")[:120], _media_url(p["img"]),
                              p.get("category") or "") for p in prods)
    body = ('<div class="wrap">' + cr + '<section class="blk" style="padding-top:12px"><h1>Sản phẩm của nhà máy</h1><p>Giá sỉ vui lòng liên hệ Zalo '
            + zl + '.</p><div class="grid">' + all_cards + "</div></section></div>")
    pages["/san-pham/"] = (_page("/san-pham/", ("Sản phẩm nhà máy %s: trà, cà phê, ngũ cốc" % c["name"])[:60],
                                 ("Danh mục sản phẩm nhà máy %s: trà túi lọc, cà phê hòa tan, ngũ cốc, bột thiên nhiên, cốm. Nhận sỉ và gia công. Zalo %s."
                                  % (c["name"], c["phone"]))[:160], body, [cld]), today, "0.8")
    for p in prods:
        path = "/san-pham/%s/" % p["slug"]
        rel = [x for x in posts if p["id"] in (x.get("product_ids") or [])][:3]
        cr, cld = _crumbs([("/", "Trang chủ"), ("/san-pham/", "Sản phẩm"), (None, p["name"])])
        pld = {"@context": "https://schema.org", "@type": "Product", "name": p["name"], "description": (p.get("description") or p["name"])[:500],
               "brand": {"@type": "Brand", "name": c["name"]}}
        if p["img"]:
            pld["image"] = _abs(_media_url(p["img"]))
        if p.get("category"):
            pld["category"] = p["category"]
        img = ('<img class="cover" src="%s" alt="%s" width="1200" height="900">' % (_media_url(p["img"]), e(p["name"]))) if p["img"] else ""
        desc = "".join("<p>%s</p>" % e(x) for x in (p.get("description") or "").splitlines() if x.strip())
        sp = [e(x.strip(" -•")) for x in (p.get("selling_points") or "").splitlines() if x.strip()]
        rel_html = ("<h2>Bài viết liên quan</h2><ul>" + li('<a href="/tin-tuc/%s/">%s</a>' % (x["slug"], e(x["title"])) for x in rel) + "</ul>") if rel else ""
        body = ('<div class="wrap">' + cr + '<article class="post"><span class="pill">' + e(p.get("category") or "Sản phẩm") + "</span><h1>" + e(p["name"])
                + "</h1>" + img + desc + (("<h2>Điểm nổi bật</h2><ul>" + li(sp) + "</ul>") if sp else "")
                + "<ul>" + li(["Nhập tối thiểu: " + e(p.get("moq") or "liên hệ"), "Giá sỉ: liên hệ Zalo " + c["phone"], "Nhận gia công thương hiệu riêng"]) + "</ul>"
                + rel_html + '<div class="cta">Nhận báo giá sỉ ' + e(p["name"]) + ": Zalo " + zl + "</div></article></div>")
        pages[path] = (_page(path, (p["name"] + " | " + c["name"])[:60],
                             ("%s: %s. Nhận sỉ, gia công. Zalo %s." % (p["name"], (p.get("description") or "sản phẩm nhà máy")[:100], c["phone"]))[:160],
                             body, [cld, pld], _media_url(p["img"]), "product"), today, "0.7")
    # tin tức (phân trang)
    n_pages = max(1, math.ceil(len(posts) / PER_PAGE))
    page_url = lambda k: "/tin-tuc/" if k == 0 else "/tin-tuc/trang-%d/" % (k + 1)
    for i in range(n_pages):
        path = page_url(i)
        chunk = posts[i * PER_PAGE:(i + 1) * PER_PAGE]
        pager = "".join(("<span>%d</span>" % (k + 1)) if k == i else ('<a href="%s">%d</a>' % (page_url(k), k + 1))
                        for k in range(n_pages)) if n_pages > 1 else ""
        cr, cld = _crumbs([("/", "Trang chủ"), (None, "Tin tức")])
        cards = "".join(_card("/tin-tuc/%s/" % p["slug"], p["title"], p["excerpt"] or p["meta_desc"], _media_url(p["cover"]), p["keyword"]) for p in chunk)
        body = ('<div class="wrap">' + cr + '<section class="blk" style="padding-top:12px"><h1>Tin tức & kiến thức</h1>'
                + (('<div class="grid">' + cards + "</div>") if chunk else "<p>Chưa có bài viết.</p>")
                + (('<nav class="pager" aria-label="Phân trang">' + pager + "</nav>") if pager else "") + "</section></div>")
        pages[path] = (_page(path, ("Tin tức & kiến thức gia công | " + c["name"])[:60] + ((" - trang %d" % (i + 1)) if i else ""),
                             ("Kiến thức kinh doanh trà, cà phê, ngũ cốc; kinh nghiệm gia công thương hiệu riêng từ nhà máy %s." % c["name"])[:160],
                             body, [cld]), today, "0.6")
    for p in posts:
        path = "/tin-tuc/%s/" % p["slug"]
        h2 = re.findall(r"^##\s+(.+)$", p["body"], re.M)
        toc = ('<nav class="toc" aria-label="Mục lục"><b>Nội dung chính</b><ol>'
               + li('<a href="#%s">%s</a>' % (slugify(h), e(h)) for h in h2) + "</ol></nav>") if len(h2) >= 3 else ""
        faq = p["faq"] or []
        others = [x for x in posts if x["id"] != p["id"]][:3]
        pub = (p.get("published_at") or p["created_at"] or "")[:10]
        upd = (p.get("updated_at") or pub)[:10]
        cr, cld = _crumbs([("/", "Trang chủ"), ("/tin-tuc/", "Tin tức"), (None, p["title"])])
        art = {"@context": "https://schema.org", "@type": "Article", "headline": p["title"][:110], "description": p["meta_desc"],
               "datePublished": pub, "dateModified": upd, "inLanguage": "vi", "mainEntityOfPage": _abs(path),
               "author": {"@type": "Organization", "name": c["legal"]}, "publisher": {"@type": "Organization", "name": c["legal"]}}
        if p.get("cover"):
            art["image"] = _abs(_media_url(p["cover"]))
        lds = [cld, art]
        if faq:
            lds.append({"@context": "https://schema.org", "@type": "FAQPage", "mainEntity": [
                {"@type": "Question", "name": q["q"], "acceptedAnswer": {"@type": "Answer", "text": q.get("a", "")}} for q in faq]})
        cover = ('<img class="cover" src="%s" alt="%s" width="1200" height="900">' % (_media_url(p["cover"]), e(p.get("cover_alt") or p["title"]))) if p.get("cover") else ""
        faq_html = ('<h2>Câu hỏi thường gặp</h2><div class="faq">'
                    + "".join("<details><summary>%s</summary><p>%s</p></details>" % (e(q["q"]), e(q.get("a", ""))) for q in faq) + "</div>") if faq else ""
        other_html = ("<h2>Bài viết khác</h2><ul>" + li('<a href="/tin-tuc/%s/">%s</a>' % (x["slug"], e(x["title"])) for x in others) + "</ul>") if others else ""
        mins = max(1, round((p["words"] or 0) / 220))
        body = ('<div class="wrap">' + cr + '<article class="post"><span class="pill">' + e(p["keyword"]) + "</span><h1>" + e(p["title"]) + "</h1>"
                + '<div class="meta">%s · %s/%s/%s · %d phút đọc</div>' % (e(c["name"]), pub[8:10], pub[5:7], pub[:4], mins)
                + cover + toc + md_html(p["body"]) + faq_html
                + '<div class="cta"><b>Cần catalog và báo giá sỉ / gia công?</b><br>Nhắn Zalo ' + zl + " để được tư vấn trực tiếp.</div>"
                + other_html + "</article></div>")
        pages[path] = (_page(path, p["meta_title"] or p["title"], p["meta_desc"], body, lds, _media_url(p.get("cover")), "article"), upd, "0.7")
    # liên hệ
    cr, cld = _crumbs([("/", "Trang chủ"), (None, "Liên hệ")])
    items = ["Zalo / Điện thoại: " + zl]
    if c["email"]:
        items.append('Email: <a href="mailto:%s">%s</a>' % (e(c["email"]), e(c["email"])))
    if c["address"]:
        items.append("Địa chỉ: " + e(c["address"]))
    body = ('<div class="wrap">' + cr + '<article class="post"><h1>Liên hệ ' + e(c["name"]) + "</h1>"
            + "<p>Cần catalog sản phẩm, bảng giá sỉ hoặc báo giá gia công, vui lòng liên hệ trực tiếp:</p><ul>" + li(items) + "</ul>"
            + '<div class="cta"><a href="%s" rel="nofollow">Nhắn Zalo ngay</a></div></article></div>' % zalo)
    pages["/lien-he/"] = (_page("/lien-he/", ("Liên hệ %s: báo giá sỉ & gia công" % c["name"])[:60],
                                ("Liên hệ nhà máy %s qua Zalo %s để nhận catalog, bảng giá sỉ và tư vấn gia công thương hiệu riêng." % (c["name"], c["phone"]))[:160],
                                body, [cld]), today, "0.6")
    # ghi file
    for path, (doc, lastmod, prio) in pages.items():
        f = tmp / path.strip("/") / "index.html" if path != "/" else tmp / "index.html"
        f.parent.mkdir(parents=True, exist_ok=True)
        f.write_text(doc, encoding="utf-8")
    (tmp / "404.html").write_text(_page("/404.html", f"Không tìm thấy trang | {c['name']}", "Trang không tồn tại.",
                                        '<div class="wrap"><article class="post"><h1>Không tìm thấy trang</h1><p><a href="/">Về trang chủ</a></p></article></div>'),
                                  encoding="utf-8")
    base = c["domain"] or ""
    sm = ['<?xml version="1.0" encoding="UTF-8"?>', '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">']
    for path, (_, lastmod, prio) in pages.items():
        sm.append(f"<url><loc>{html.escape(base + path)}</loc><lastmod>{lastmod}</lastmod><priority>{prio}</priority></url>")
    sm.append("</urlset>")
    (tmp / "sitemap.xml").write_text("\n".join(sm), encoding="utf-8")
    (tmp / "robots.txt").write_text("User-agent: *\nAllow: /\n" + (f"Sitemap: {base}/sitemap.xml\n" if base else ""), encoding="utf-8")
    media = db.DATA_DIR / "site_media"
    if media.exists():
        (tmp / "media").mkdir(exist_ok=True)
        used = {p["cover"] for p in posts if p.get("cover")} | {p["img"] for p in prods if p.get("img")}
        for name in used:
            if (media / name).exists():
                shutil.copyfile(media / name, tmp / "media" / name)
    shutil.rmtree(SITE_DIR, ignore_errors=True)
    tmp.rename(SITE_DIR)
    db.set_setting("site_last_build", db.now())
    n = {"pages": len(pages), "posts": len(posts), "products": len(prods), "domain": bool(c["domain"])}
    db.log("vy", "Dựng lại website", f"{n['pages']} trang, {n['posts']} bài viết, {n['products']} sản phẩm"
           + ("" if c["domain"] else ". Chưa điền tên miền: sitemap và thẻ canonical đang dùng đường dẫn tương đối"))
    return n


def export_zip() -> bytes:
    if not (SITE_DIR / "index.html").exists():
        build()
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as z:
        for f in SITE_DIR.rglob("*"):
            if f.is_file():
                z.write(f, f.relative_to(SITE_DIR).as_posix())
    return buf.getvalue()


def deploy() -> dict:
    """Đăng website lên hosting qua FTP (FTPS nếu bật)."""
    import ftplib
    st = s()
    host, user, pw = (st.get("site_ftp_host") or "").strip(), (st.get("site_ftp_user") or "").strip(), st.get("site_ftp_pass") or ""
    if not (host and user and pw):
        raise ValueError("Chưa điền máy chủ FTP, tài khoản và mật khẩu ở mục Website → Đăng lên hosting")
    if not (SITE_DIR / "index.html").exists():
        build()
    port = 21
    if ":" in host:
        host, port = host.rsplit(":", 1)[0], int(host.rsplit(":", 1)[1])
    ftp = ftplib.FTP_TLS() if st.get("site_ftp_tls", "1") == "1" else ftplib.FTP()
    ftp.connect(host, port, timeout=30)
    ftp.login(user, pw)
    if isinstance(ftp, ftplib.FTP_TLS):
        ftp.prot_p()
    root = (st.get("site_ftp_dir") or "/").rstrip("/") or "/"
    n = 0
    try:
        made = set()

        def ensure(d: str):
            parts = [x for x in d.split("/") if x]
            cur = ""
            for x in parts:
                cur += "/" + x
                if cur in made:
                    continue
                try:
                    ftp.mkd(cur)
                except ftplib.error_perm:
                    pass
                made.add(cur)
        ensure(root)
        for f in sorted(SITE_DIR.rglob("*")):
            if not f.is_file():
                continue
            rel = f.relative_to(SITE_DIR).as_posix()
            dest = f"{root.rstrip('/')}/{rel}" if root != "/" else f"/{rel}"
            ensure(dest.rsplit("/", 1)[0])
            with open(f, "rb") as fh:
                ftp.storbinary(f"STOR {dest}", fh)
            n += 1
    finally:
        try:
            ftp.quit()
        except Exception:
            pass
    db.set_setting("site_last_deploy", db.now())
    db.log("vy", "Đăng website lên hosting", f"Tải lên {n} tệp vào {host}{root}")
    return {"files": n, "host": host, "dir": root}


# ---------------------------------------------------------------- lịch làm việc của Vy
_busy = {"on": False}


def tick(now):
    """Ngày viết bài (mặc định thứ 2, 4, 6) đúng giờ: Vy viết đủ số bài tuần chia đều các ngày."""
    st = s()
    days = [int(x) for x in re.findall(r"\d", st.get("site_write_days") or "1,3,5")]
    if not days or (now.isoweekday() not in days) or now.strftime("%H:%M") < (st.get("site_write_time") or "09:45"):
        return
    if (st.get("site_last_write") or "")[:10] == now.strftime("%Y-%m-%d") or _busy["on"]:
        return
    per = max(1, math.ceil(_i("site_posts_week", 3) / len(days)))

    def run():
        _busy["on"] = True
        try:
            for _ in range(per):
                if not db.one("SELECT 1 x FROM site_keywords WHERE status='planned'"):
                    plan_more()
                write()
        except Exception as e:
            import errors
            errors.report_exc("website", "Vy viết bài website bị lỗi", e, screen="website")
        finally:
            _busy["on"] = False
    db.set_setting("site_last_write", now.strftime("%Y-%m-%d %H:%M:%S"))
    threading.Thread(target=run, daemon=True).start()


def plan_more(n: int = 6) -> int:
    """Vy nghĩ thêm từ khóa: AI gợi ý theo sản phẩm thật; chưa có AI thì ghép sản phẩm với ý định tìm kiếm."""
    from llm import llm
    have = {plain(r["keyword"]) for r in db.q("SELECT keyword FROM site_keywords")}
    cands = []
    if llm.live:
        try:
            from agents import system_prompt
            prods = ", ".join(p["name"] for p in _products(20))
            d = llm.json(system_prompt("vy", s()), f"Sản phẩm nhà máy: {prods}. Đề xuất {n * 2} từ khóa tiếng Việt người bán online / chủ thương hiệu "
                         "hay tìm trên Google khi tìm xưởng gia công hoặc nguồn sỉ (không phải từ khóa người tiêu dùng tìm công dụng chữa bệnh). "
                         "Trả JSON {\"keywords\": [{\"keyword\": \"...\", \"cluster\": \"gia công|bán sỉ|kiến thức kinh doanh|pháp lý|nhà máy\", \"priority\": 1-3}]}",
                         mock=None, max_tokens=800, task="knowledge")
            cands = [(x["keyword"], x.get("cluster") or "", int(x.get("priority") or 2)) for x in (d or {}).get("keywords", [])
                     if isinstance(x, dict) and x.get("keyword")]
        except Exception as e:
            print("[site keywords]", e)
    if not cands:
        for p in _products(20):
            base = re.sub(r"\s*\(.*?\)", "", p["name"]).strip().lower()
            cands += [(f"gia công {base}", "gia công", 2), (f"nguồn sỉ {base}", "bán sỉ", 2)]
    added = 0
    for kw, cl, pr in cands:
        if added >= n or plain(kw) in have or len(kw) > 80:
            continue
        db.run("INSERT OR IGNORE INTO site_keywords(keyword, cluster, intent, priority, status, source, created_at) VALUES (?,?,?,?,?,?,?)",
               (kw.strip(), cl, "", pr, "planned", "vy", db.now()))
        have.add(plain(kw))
        added += 1
    if added:
        db.log("vy", "Lên kế hoạch từ khóa", f"Thêm {added} từ khóa mới cho website")
    return added


def overview() -> dict:
    seed()
    st = s()
    posts = db.q("""SELECT id, keyword, title, slug, status, seo_score, words, policy_note, cover, created_at, updated_at, published_at
                    FROM site_posts ORDER BY id DESC""")
    kws = db.q("SELECT * FROM site_keywords ORDER BY status='written', priority, id")
    keys = ["site_name", "site_legal_name", "site_tagline", "site_domain", "site_about", "site_address", "site_email", "site_phone",
            "site_certs", "site_founded", "site_color", "site_ga_id", "site_posts_week", "site_write_days", "site_write_time",
            "site_auto_publish", "site_min_seo", "site_ftp_host", "site_ftp_user", "site_ftp_dir", "site_ftp_tls"]
    cfg = {k: st.get(k) for k in keys}
    cfg["site_ftp_pass_set"] = bool(st.get("site_ftp_pass"))
    return {"posts": posts, "keywords": kws, "settings": cfg, "built": (SITE_DIR / "index.html").exists(),
            "last_build": st.get("site_last_build"), "last_deploy": st.get("site_last_deploy"), "last_write": st.get("site_last_write"),
            "stats": {"published": sum(p["status"] == "published" for p in posts), "review": sum(p["status"] == "review" for p in posts),
                      "planned": sum(k["status"] == "planned" for k in kws),
                      "avg_seo": round(sum(p["seo_score"] or 0 for p in posts) / len(posts)) if posts else 0},
            "pages": len(list(SITE_DIR.rglob("index.html"))) if SITE_DIR.exists() else 0}

"""Sếp chốt: KHÔNG công khai giá. Sản phẩm không còn giá sỉ / giá bán lẻ; mọi bài viết, tin nhắn, kịch bản đều mời khách
liên hệ trực tiếp Zalo để được báo giá (số Zalo sửa được ở Cài đặt).

- contact_line(): câu mời liên hệ (mặc định "💬 Giá vui lòng liên hệ trực tiếp Zalo 0386992326").
- sanitize(text): bỏ mọi dòng/cụm có giá (99k, 35.000đ, giá sỉ: ..., lãi 25k/hộp) rồi thêm câu mời liên hệ nếu chưa có.
- PROMPT: câu dặn đưa vào mọi lời nhắc gửi Claude.
"""
import re

import db

DEFAULT_ZALO = "0386992326"

MONEY = r"\d[\d.,]*\s*(?:k|K|đ|₫|vnđ|VNĐ|vnd|VND|nghìn|ngàn|ngan|nghin|triệu|tr)\b(?:\s*/\s*[\wÀ-ỹ]+)?"
MONEY_RX = re.compile(MONEY)
PRICE_LINE_RX = re.compile(r"(giá\s*(sỉ|lẻ|bán|nhập|gốc|tận xưởng|ưu đãi|chỉ|từ)?\s*:?\s*" + MONEY + r"|lãi\s*" + MONEY + r"|"
                           r"nhập\s+" + MONEY + r"|bán\s+(lẻ\s+)?" + MONEY + r"|💵|💰\s*nhập)", re.I)
PRICE_WORD_LINE = re.compile(r"^\s*[\W_]*\s*(giá\s*(sỉ|bán lẻ|lẻ|bán)( gợi ý)?|bảng giá)\s*[:\-—]", re.I)


def zalo() -> str:
    return (db.get_settings().get("price_zalo") or DEFAULT_ZALO).strip()


def contact_line() -> str:
    t = (db.get_settings().get("price_contact") or "").strip()
    return t or f"💬 Giá vui lòng liên hệ trực tiếp Zalo {zalo()}"


def prompt_rule() -> str:
    return (f"\nQUY ĐỊNH VỀ GIÁ (sếp chốt): TUYỆT ĐỐI không ghi giá sỉ, giá lẻ, giá bán, mức lãi hay bất kỳ con số tiền nào. "
            f"Khi nói tới giá, chỉ ghi: \"{contact_line()}\".")


def has_contact(text: str) -> bool:
    z = re.sub(r"\D", "", zalo())
    return bool(z) and z in re.sub(r"\D", "", text or "")


def sanitize(text: str, add_contact: bool = True) -> str:
    """Bỏ giá khỏi bài/tin; thêm câu mời liên hệ Zalo (một lần)."""
    if not text:
        return text
    out = []
    for line in text.splitlines():
        if PRICE_WORD_LINE.search(line):
            continue  # dòng "Giá sỉ: ..."
        if MONEY_RX.search(line) and (re.search(r"(nhập|bán lẻ|lãi|lời|giá|chiết khấu)", line, re.I)
                                      or len(MONEY_RX.findall(line)) >= 2
                                      or len(MONEY_RX.sub("", line).strip(" -—:|•✅💵💰")) < 25):
            continue  # cả dòng nói về giá / lãi
        l = re.sub(r"\(?\s*(?:(?:giá\s*(?:sỉ|lẻ|bán|chỉ|từ)?|chỉ còn|chỉ|từ|còn|only)\s*:?\s*)?" + MONEY + r"\s*\)?", "", line, flags=re.I)
        if l != line:
            l = re.sub(r"\s{2,}", " ", l).replace(" ,", ",").rstrip(" ,-—")
            if not l.strip(" ,.-—:•"):
                continue
        out.append(l)
    t = "\n".join(out).strip()
    t = re.sub(r"\n{3,}", "\n\n", t)
    if add_contact and not has_contact(t):
        t += "\n\n" + contact_line()
    return t


def migrate():
    """Một lần: xóa giá trong sản phẩm, sửa kiến thức cũ dạy ghi giá, thêm chỉ đạo chung cho cả đội."""
    st = db.get_settings()
    if st.get("price_hidden_migrated") == "1":
        return
    db.run("UPDATE products SET wholesale_price='', retail_price=''")
    db.run("""UPDATE knowledge SET content=?, updated_at=? WHERE topic='cách trình bày giá sỉ và lợi nhuận cho người bán lại'""",
           (f"Không ghi giá trong bài. Nói lợi ích cho người bán lại (nguồn tận xưởng, hàng sẵn, ảnh video thật, hỗ trợ đăng bán) và "
            f"mời liên hệ Zalo {DEFAULT_ZALO} để được báo giá trực tiếp.", db.now()))
    db.run("""UPDATE knowledge SET content=?, updated_at=? WHERE topic='cách trả lời khách hỏi giá sỉ để chốt được số điện thoại'""",
           (f"Không báo giá qua bình luận hay tin nhắn. Mời khách nhắn Zalo {DEFAULT_ZALO} để được báo giá trực tiếp theo số lượng, "
            "đồng thời xin SĐT/Zalo của khách để xưởng gọi tư vấn. Hỏi thêm khách bán kênh nào, nhập khoảng bao nhiêu.", db.now()))
    try:
        if not db.one("SELECT id FROM ceo_orders WHERE text LIKE '%không ghi giá%' AND active=1"):
            db.run("INSERT INTO ceo_orders(agent, text, active, created_at) VALUES ('all', ?, 1, ?)",
                   (f"Không ghi giá sỉ, giá bán hay mức lãi trong bất kỳ bài viết, tin nhắn nào; giá vui lòng liên hệ trực tiếp Zalo {DEFAULT_ZALO}",
                    db.now()))
    except Exception as e:
        print("[pricing order]", e)
    for p in db.q("SELECT id, content, title FROM posts WHERE status IN ('draft','approved','scheduled')"):  # bài chưa đăng
        db.run("UPDATE posts SET content=?, title=? WHERE id=?", (sanitize(p["content"] or ""), sanitize(p["title"] or "", False), p["id"]))
    db.set_setting("price_hidden_migrated", "1")

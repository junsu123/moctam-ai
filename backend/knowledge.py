"""Sổ kiến thức của các agent: tự học mỗi ngày, dùng kiến thức đã có trước, chỉ hỏi Claude khi chưa biết.

- Mỗi agent có sổ kiến thức riêng (agent_id), cộng sổ chung của cả đội ('all') và sổ chung của các sale ('sale').
- Mỗi ngày (mặc định 07:00) mỗi agent tự học vài kiến thức mới hợp với việc mình đang làm: trả lời các câu hỏi còn
  bỏ ngỏ trước (câu sếp/khách hỏi mà chưa biết), rồi chủ đề theo việc thực tế (sản phẩm đang bán chạy, chủ đề tìm nhóm
  hôm nay, câu khách hay hỏi), rồi giáo trình theo vai trò. Có khóa Claude: mỗi agent 1 lần gọi Haiku/ngày. Chưa có khóa:
  học từ thư viện kiến thức có sẵn trong phần mềm.
- Khi làm việc: agent tìm trong sổ trước. Câu hỏi đã có câu trả lời khớp thì tự trả lời, KHÔNG gọi Claude
  (VD Hà trả lời câu khách hay hỏi). Chưa biết mới hỏi Claude; câu trả lời trả về luôn được lưu vào sổ để lần sau tự dùng.
- Kiến thức liên quan được đưa vào lời dặn mỗi khi agent gọi Claude (viết bài, soạn tin, họp), để làm đúng hơn.
- Sếp dạy thêm, sửa, xóa kiến thức ở trang Đào tạo. Không dùng nhúng vector: tìm theo từ khóa (bỏ dấu), đủ nhanh cho vài nghìn mục.
"""
import json
import re
import unicodedata
from datetime import datetime, timedelta

import db

STOP = set("""co khong la cua va cho voi thi ma nay do em anh chi ben minh a nhe oi duoc nhung cac mot nao gi sao the nhu de khi
neu vay roi con hay hoac ve tu tren duoi trong ngoai ra vao lai nua cung rat qua lam bi da se ban toi chung ta ho no
nha nhi ah u uh ok vang da cai chiec bao nhieu may""".split())
ROLE_NAME = {"ceo": "CEO Đức", "minh": "Minh", "lan": "Lan", "tuan": "Tuấn", "ha": "Hà", "khoa": "Khoa", "mai": "Mai", "sale": "Nhân viên sale",
             "all": "Cả đội"}
SOURCE_TXT = {"study": "Tự học", "claude": "Hỏi Claude", "boss": "Sếp dạy", "library": "Thư viện có sẵn", "experience": "Kinh nghiệm thực tế"}

# Giáo trình theo vai trò: chủ đề agent tự học dần mỗi ngày
CURRICULUM = {
    "lan": ["công thức viết bài bán sỉ trên nhóm Facebook (AIDA, PAS)", "cách viết câu mở đầu giữ chân người đọc trong 2 dòng đầu",
            "cách trình bày giá sỉ và lợi nhuận cho người bán lại", "từ ngữ dễ bị Facebook hạn chế khi bán hàng thực phẩm",
            "quy định quảng cáo thực phẩm, không hứa chữa bệnh", "cách kêu gọi bình luận để lấy số điện thoại khách",
            "viết bài kể chuyện xưởng sản xuất tạo niềm tin", "cách dùng emoji và xuống dòng cho bài dễ đọc trên điện thoại",
            "viết bài cho mùa lễ Tết và mùa cao điểm", "cách viết bài khác nhau cho người chạy ads, livestream, bán sàn"],
    "tuan": ["dấu hiệu nên thoát một nhóm Facebook", "cách chăm sóc nhóm Facebook mình quản lý cho sôi nổi",
             "cách thuật toán Facebook xếp bài trong nhóm", "giờ vàng đăng bài nhóm bán hàng ở Việt Nam",
             "cách tránh bị quản trị viên nhóm xóa bài và chặn", "dấu hiệu nhóm tương tác thật và nhóm ảo",
             "giới hạn an toàn khi một nick đăng nhiều nhóm", "cách up bài bằng bình luận cho bài nổi lên",
             "cách đọc luật nhóm trước khi đăng", "quản lý nhiều nick Facebook không bị liên kết"],
    "ha": ["cách trả lời khách hỏi giá sỉ để chốt được số điện thoại", "xử lý khách chê giá cao",
           "cách hỏi nhu cầu khách sỉ (kênh bán, số lượng, tần suất nhập)", "chính sách gửi mẫu thử cho khách sỉ",
           "cách bám khách sau 2 ngày không trả lời", "cách trả lời khách hỏi giấy tờ kiểm nghiệm, hóa đơn",
           "kịch bản gọi điện cho khách sỉ lần đầu", "cách giữ chân khách nhập lần 2"],
    "khoa": ["các chỉ số đo hiệu quả bài đăng nhóm", "cách tính chi phí trên mỗi khách có số điện thoại",
             "cách đọc xu hướng 7 ngày và 30 ngày", "đánh giá nhóm Facebook theo tương tác"],
    "minh": ["cách điều hành họp giao ban 15 phút hiệu quả", "cách giao việc rõ ràng có người chịu trách nhiệm và hạn",
             "cách đặt mục tiêu tuần cho phòng kinh doanh online"],
    "ceo": ["cách mở rộng kênh bán sỉ qua cộng tác viên", "cách định giá sỉ theo bậc số lượng",
            "khi nào nên tuyển thêm nhân sự bán hàng", "cách xây thương hiệu xưởng trên Facebook"],
    "sale": ["cách nuôi nick Facebook an toàn", "dấu hiệu nick sắp bị checkpoint và cách tránh",
             "cách trả lời bình luận xin số điện thoại tự nhiên", "cách tham gia nhóm mới không bị từ chối"],
    "mai": ["cách dùng thư viện quảng cáo Facebook để tìm người bán thực phẩm đang chạy quảng cáo",
            "cách nhận ra bài và bình luận hỏi tìm nguồn hàng trong nhóm Facebook",
            "cách tìm số điện thoại kinh doanh công khai của shop trên Facebook", "từ khóa Facebook để tìm người bán hàng có để lại SĐT",
            "thang chấm điểm khách sỉ 100 điểm và cách xếp hạng A B C D", "phân biệt chủ shop tự nhập hàng với affiliate, KOC, CTV",
            "dấu hiệu một tài khoản đang livestream bán hàng thật", "dấu hiệu người bán có khả năng nhập hàng về bán lại",
            "cách tìm người bán trà, ngũ cốc, đồ ăn healthy trên TikTok Shop", "cách đọc gian hàng Shopee để đánh giá người bán",
            "nhận diện người bán đa nền tảng Facebook TikTok Shopee", "các từ khóa người bán dùng khi tìm nguồn hàng, tuyển đại lý",
            "những nguyên tắc khi nghiên cứu khách: không bịa, không đoán doanh thu", "cách viết tin nhắn tiếp cận khách sỉ lần đầu",
            "sản phẩm bổ trợ cho người đang bán đồ ăn healthy, mẹ và bé, đồ uống", "cách phân biệt cửa hàng truyền thống và người bán online"],
}

# Thư viện kiến thức có sẵn (dùng khi chưa có khóa Claude, hoặc làm nền ban đầu)
LIBRARY = {
    "lan": [
        ("công thức viết bài bán sỉ trên nhóm Facebook (AIDA, PAS)", "Viết bài bán sỉ thế nào cho hiệu quả?",
         "Dùng PAS: nêu nỗi lo của người bán (khó tìm nguồn hàng rẻ, hàng không rõ gốc) → khuấy (nhập qua trung gian mất lãi) → "
         "giải pháp (nhập tận xưởng, giá sỉ cụ thể, lãi bao nhiêu mỗi hộp). Kết bằng 1 lời mời rõ: bình luận 'giá' hoặc để SĐT.",
         "aida pas cong thuc viet bai ban si"),
        ("cách trình bày giá sỉ và lợi nhuận cho người bán lại", "Nên ghi giá trong bài thế nào?",
         "Ghi rõ giá sỉ, giá bán lẻ gợi ý và lãi mỗi sản phẩm (VD: nhập 35k, bán 60k, lãi 25k/hộp). Người bán lại quan tâm lãi "
         "và số nhập tối thiểu hơn là mô tả dài.", "gia si loi nhuan lai ban le"),
        ("quy định quảng cáo thực phẩm, không hứa chữa bệnh", "Bài thực phẩm được nói công dụng tới đâu?",
         "Không dùng chữ 'chữa', 'trị', 'khỏi bệnh', 'thay thuốc'. Chỉ nói thành phần, cách dùng, cảm nhận (ấm bụng, dễ uống). "
         "Nhóm và Facebook hay gỡ bài hứa chữa bệnh.", "quang cao thuc pham chua benh cong dung"),
    ],
    "tuan": [
        ("giờ vàng đăng bài nhóm bán hàng ở Việt Nam", "Đăng bài nhóm giờ nào nhiều người xem?",
         "Thường là 11:00–13:00, 19:30–22:00; sáng sớm 6:30–8:00 hợp nhóm mẹ bỉm. Dùng giờ vàng thực tế của mình (trang Đào tạo) "
         "khi đã đủ dữ liệu.", "gio vang dang bai nhom"),
        ("cách tránh bị quản trị viên nhóm xóa bài và chặn", "Làm sao để bài không bị admin nhóm xóa?",
         "Đọc luật nhóm, đăng đúng ngày cho phép bán hàng, không đăng 1 nội dung giống hệt vào nhiều nhóm cùng lúc, không để link "
         "ngoài, bài có giá trị (chia sẻ kinh nghiệm) trước rồi mới chào hàng.", "admin xoa bai chan nhom luat"),
        ("giới hạn an toàn khi một nick đăng nhiều nhóm", "Một nick đăng bao nhiêu bài mỗi ngày là an toàn?",
         "Nick mới: 2–3 bài nhóm/ngày, cách nhau từ 45 phút; nick lâu năm có tương tác: 4–6 bài. Mỗi bài nội dung khác nhau, "
         "xen kẽ lướt bảng tin và tương tác thật.", "gioi han an toan nick dang bai"),
    ],
    "ha": [
        ("cách trả lời khách hỏi giá sỉ để chốt được số điện thoại", "Khách hỏi giá sỉ thì trả lời thế nào?",
         "Báo khoảng giá sỉ ngay (khách ghét bị giấu giá), nói rõ giá theo số lượng nhập, rồi xin SĐT/Zalo để gửi bảng giá chi tiết "
         "và ảnh/video thật.", "khach hoi gia si bao gia"),
        ("xử lý khách chê giá cao", "Khách chê giá cao thì nói gì?",
         "Không giảm giá ngay. Hỏi khách đang so với hàng nào, nhấn vào lãi khi bán lại, nguồn gốc tận xưởng, hỗ trợ ảnh/video bán "
         "hàng; đề nghị nhập thử số lượng nhỏ hoặc gửi mẫu.", "che gia cao dat"),
        ("cách trả lời khách hỏi giấy tờ kiểm nghiệm, hóa đơn", "Khách hỏi giấy kiểm nghiệm, hóa đơn?",
         "Xác nhận có (chỉ khi xưởng có thật), đề nghị gửi bản chụp qua Zalo; hóa đơn VAT thì báo sếp xác nhận trước khi hứa.",
         "giay kiem nghiem hoa don vat"),
    ],
    "khoa": [
        ("các chỉ số đo hiệu quả bài đăng nhóm", "Đo bài đăng nhóm hiệu quả bằng gì?",
         "Ưu tiên số khách để lại SĐT mỗi bài, rồi số bình luận hỏi giá; lượt thích ít ý nghĩa. So theo nhóm, góc viết, giờ đăng "
         "và sản phẩm để biết cái nào mang khách.", "chi so hieu qua bai dang"),
    ],
    "minh": [
        ("cách giao việc rõ ràng có người chịu trách nhiệm và hạn", "Giao việc sao cho rõ?",
         "Mỗi việc 1 người chịu trách nhiệm, kết quả đo được, hạn cụ thể (VD: Lan viết 3 bài trà gừng trước 10:00).",
         "giao viec trach nhiem han"),
    ],
    "ceo": [
        ("cách định giá sỉ theo bậc số lượng", "Định giá sỉ theo số lượng thế nào?",
         "Chia 3 bậc: lẻ sỉ (nhập tối thiểu), sỉ vừa (gấp 3–5 lần) giảm 5–8%, đại lý (gấp 10 lần) giảm 12–15%. Giữ biên lãi cho "
         "người bán lại tối thiểu 30–40% so với giá bán lẻ gợi ý.", "dinh gia si bac so luong dai ly"),
    ],
    "sale": [
        ("cách nuôi nick Facebook an toàn", "Nuôi nick Facebook thế nào để không bị khóa?",
         "Đủ ảnh đại diện, ảnh bìa, thông tin thật; lướt và tương tác như người thật mỗi ngày; tăng dần số bài; không đăng nhập "
         "nhiều nick trên cùng một hồ sơ trình duyệt.", "nuoi nick an toan khoa"),
        ("cách trả lời bình luận xin số điện thoại tự nhiên", "Xin SĐT khách dưới bình luận thế nào?",
         "Cảm ơn, trả lời đúng câu khách hỏi một ý ngắn, rồi xin SĐT/Zalo để gửi bảng giá và ảnh thật; tránh dán cùng một câu cho "
         "mọi bình luận.", "xin sdt binh luan"),
    ],
    "mai": [
        ("cách dùng thư viện quảng cáo Facebook để tìm người bán thực phẩm đang chạy quảng cáo", "Tìm trang đang chạy quảng cáo thế nào?",
         "Vào Thư viện quảng cáo Facebook, chọn Việt Nam, quảng cáo đang hoạt động, tìm theo từ khóa sản phẩm (trà túi lọc, ngũ cốc, "
         "granola...). Trang trả tiền quảng cáo bán thực phẩm là người bán thật, có ngân sách; quảng cáo thường ghi hotline. Bỏ qua "
         "quảng cáo không hợp ngành.", "thu vien quang cao facebook ads library chay quang cao"),
        ("cách nhận ra bài và bình luận hỏi tìm nguồn hàng trong nhóm Facebook", "Ai trong nhóm là khách nóng?",
         "Người viết 'tìm nguồn', 'cần nhập', 'xin giá sỉ', 'ai có nguồn' kèm tên hàng (trà, ngũ cốc, granola, đồ ăn healthy) là khách "
         "nóng nhất. Bỏ qua người chào bán sỉ ('nhận sỉ', 'cung cấp sỉ', 'tuyển đại lý'): đó là nhà cung cấp. Họ tự ghi SĐT thì lấy; "
         "chưa có thì sếp/Hà trả lời hoặc nhắn tay xin SĐT.", "tim nguon hang binh luan nhom can nhap xin gia si khach nong"),
        ("cách tìm số điện thoại kinh doanh công khai của shop trên Facebook", "Tìm SĐT của shop trên Facebook ở đâu?",
         "Theo thứ tự: phần Giới thiệu đầu trang (hotline, Zalo), mục Giới thiệu → Thông tin liên hệ, bài ghim, bài tuyển CTV/đại lý "
         "hay bài chốt đơn ('liên hệ 09...', 'Zalo 09...'), nút gọi điện, link zalo.me. Chỉ lấy số shop tự công khai để bán hàng; "
         "số trong bình luận của người khác hay thông tin cá nhân thì không lấy.", "tim so dien thoai sdt shop facebook gioi thieu lien he"),
        ("thang chấm điểm khách sỉ 100 điểm và cách xếp hạng A B C D", "Chấm điểm khách sỉ thế nào?",
         "Thang 100: hoạt động bán hàng 20, livestream 20, phù hợp ngành hàng 20, khả năng tự nhập hàng 15, hoạt động và tương tác "
         "10, khả năng liên hệ 10, khả năng mở rộng sản phẩm 5. Hạng A 80–100, B 60–79, C 40–59, D dưới 40. Mỗi điểm phải có "
         "bằng chứng (đoạn chữ + link); không có bằng chứng thì 0 điểm cho mục đó.", "cham diem thang 100 hang a b c d"),
        ("phân biệt chủ shop tự nhập hàng với affiliate, KOC, CTV", "Làm sao biết là chủ shop hay affiliate?",
         "Chủ shop: có kho, 'shop mình', 'hàng mới về', nhận đơn, ship COD, có gian hàng riêng. Affiliate: dẫn link Shopee/TikTok "
         "(s.shopee, vt.tiktok), 'link ở bình luận', 'hoa hồng', không có kho. KOC/KOL: review, unbox, booking, nhiều người theo dõi. "
         "CTV: 'bán không cần vốn', lấy hàng từ kho người khác. Không coi affiliate là khách nhập sỉ nếu chưa có bằng chứng tự nhập.",
         "chu shop affiliate koc ctv phan biet"),
        ("dấu hiệu một tài khoản đang livestream bán hàng thật", "Thế nào là đang livestream bán hàng?",
         "Bài của chính tài khoản ghi 'đang phát trực tiếp'/'đã phát trực tiếp', có lịch live, chốt đơn trong live. Chia sẻ lại live "
         "của người khác hoặc 'đang xem' KHÔNG tính. Tần suất live chỉ ghi khi đếm được từ các bài gần nhất.",
         "livestream ban hang that dau hieu"),
        ("những nguyên tắc khi nghiên cứu khách: không bịa, không đoán doanh thu", "Nguyên tắc khi tìm khách?",
         "Không tạo dữ liệu giả; không suy diễn số đơn; không đánh giá doanh thu từ lượt xem; không nhầm người xem live với người bán; "
         "chỉ lấy SĐT/Zalo/email kinh doanh được công khai; không vượt qua đăng nhập, captcha hay giới hạn của nền tảng; không tự "
         "nhắn tin hàng loạt; không tự cam kết giá hay chính sách.", "nguyen tac khong bia doanh thu rieng tu"),
        ("các từ khóa người bán dùng khi tìm nguồn hàng, tuyển đại lý", "Người bán tìm nguồn hàng hay dùng chữ gì?",
         "'tìm nguồn hàng', 'cần nhập sỉ', 'nhận phân phối', 'tuyển đại lý', 'tuyển CTV', 'giá sỉ', 'lấy sỉ', 'kho hàng', "
         "'hàng mới về'. Đây là dấu hiệu có khả năng nhập hàng mạnh nhất.", "tu khoa nguon hang dai ly si"),
    ],
}


# ---------------------------------------------------------------- tìm kiếm
def plain(t: str) -> str:
    t = unicodedata.normalize("NFD", (t or "").lower().replace("đ", "d"))
    return re.sub(r"[^a-z0-9 ]+", " ", "".join(c for c in t if unicodedata.category(c) != "Mn"))


def tokens(t: str) -> list[str]:
    return [w for w in plain(t).split() if w not in STOP and len(w) > 1]


def scope_of(agent_id: str) -> list[str]:
    if agent_id.startswith("sale-") or agent_id == "sale":
        return ["sale", "all"]
    if agent_id in ("ceo", "*"):
        return []  # CEO tra được sổ của cả đội
    return [agent_id, "all"]


def _items(agent_id: str) -> list[dict]:
    sc = scope_of(agent_id)
    if not sc:
        return db.q("SELECT * FROM knowledge WHERE status='active'")
    return db.q(f"SELECT * FROM knowledge WHERE status='active' AND agent_id IN ({','.join('?' * len(sc))})", tuple(sc))


def _score(q: list[str], qbig: set, it: dict, detail: bool = False):
    head = set(tokens(f"{it.get('question') or ''} {it.get('topic') or ''} {it.get('keywords') or ''}"))
    body = set(tokens(it.get("content") or ""))
    if not q:
        return (0.0, 0.0) if detail else 0.0
    s = sum(1.0 if w in head else 0.5 if w in body else 0 for w in q) / len(q)
    text = plain(f"{it.get('question') or ''} {it.get('topic') or ''} {it.get('content') or ''}")
    s += min(0.3, 0.1 * sum(1 for b in qbig if b in text))
    hc = sum(1 for w in q if w in head) / len(q)  # độ khớp với chính câu hỏi/chủ đề (không tính nội dung)
    return (round(s, 3), round(hc, 3)) if detail else round(s, 3)


def search(agent_id: str, query: str, k: int = 5, min_score: float = 0.3) -> list[dict]:
    q = list(dict.fromkeys(tokens(query)))
    words = plain(query).split()
    qbig = {f"{a} {b}" for a, b in zip(words, words[1:]) if a not in STOP or b not in STOP}
    out = []
    for it in _items(agent_id):
        sc, hc = _score(q, qbig, it, detail=True)
        if sc >= min_score:
            out.append({**it, "score": sc, "head": hc})
    out.sort(key=lambda x: (-x["score"], -(x.get("uses") or 0)))
    return out[:k]


def _used(ids: list[int]):
    for i in ids:
        db.run("UPDATE knowledge SET uses=COALESCE(uses,0)+1, last_used_at=? WHERE id=?", (db.now(), i))


def block(agent_id: str, query: str, k: int = 4) -> str:
    """Kiến thức liên quan để đưa vào lời dặn khi agent làm việc (dùng kiến thức đã học trước)."""
    if db.get_settings().get("knowledge_enabled", "1") != "1":
        return ""
    try:
        hits = search(agent_id, query, k=k, min_score=0.35)
    except Exception:
        return ""
    if not hits:
        return ""
    _used([h["id"] for h in hits])
    return ("\n\nKIẾN THỨC BẠN ĐÃ HỌC (dùng khi phù hợp, ưu tiên hơn hiểu biết chung):\n"
            + "\n".join(f"- {h['topic'] or h['question']}: {h['content'][:300]}" for h in hits))


# ---------------------------------------------------------------- lưu
def save(agent_id: str, topic: str, content: str, question: str = "", keywords: str = "", source: str = "study",
         confidence: float = 0.8, kind: str = "guide") -> int | None:
    content = (content or "").strip()
    if len(content) < 15:
        return None
    topic = (topic or question or content[:60]).strip()[:150]
    dup = search(agent_id if agent_id not in ("all",) else "*", f"{topic} {question}", k=1, min_score=0.92)
    if dup and plain(dup[0]["topic"] or "") == plain(topic):
        db.run("UPDATE knowledge SET content=?, question=COALESCE(NULLIF(?,''),question), keywords=?, updated_at=? WHERE id=?",
               (content[:1500], question[:300], keywords[:300], db.now(), dup[0]["id"]))
        return dup[0]["id"]
    return db.run("""INSERT INTO knowledge(agent_id, topic, question, content, keywords, source, confidence, uses, status,
                     created_at, updated_at, kind) VALUES (?,?,?,?,?,?,?,0,'active',?,?,?)""",
                  (agent_id, topic, (question or "")[:300], content[:1500], (keywords or "")[:300], source, confidence,
                   db.now(), db.now(), kind))


def _log(agent_id: str, kind: str, question: str = "", item_id: int | None = None):
    db.run("INSERT INTO knowledge_log(agent_id, kind, question, item_id, created_at) VALUES (?,?,?,?,?)",
           (agent_id, kind, (question or "")[:300], item_id, db.now()))


# ---------------------------------------------------------------- hỏi: sổ trước, Claude sau
def known_answer(agent_id: str, question: str, kind: str | None = None) -> dict | None:
    """Câu trả lời đã có trong sổ, đủ khớp để tự dùng không cần hỏi Claude.
    kind='faq': chỉ lấy câu trả lời dành cho khách (Hà trả lời khách); mặc định lấy mọi kiến thức."""
    th = float(db.get_settings().get("knowledge_answer_threshold") or 0.8)
    if len(tokens(question)) < 2:
        return None
    hits = [h for h in search(agent_id, question, k=5, min_score=th)
            if h.get("question") and h["head"] >= 0.6 and (kind is None or (h.get("kind") or "guide") == kind)]
    return hits[0] if hits else None


def ask(agent_id: str, question: str, context: str = "", save_to: str | None = None) -> dict:
    """Agent cần biết điều gì: tìm trong sổ trước; chưa có mới hỏi Claude, rồi lưu câu trả lời vào sổ."""
    from agents import system_prompt
    from llm import llm
    question = (question or "").strip()[:500]
    if not question:
        return {"answer": "", "source": "none"}
    hit = known_answer(agent_id, question)
    if hit:
        _used([hit["id"]])
        _log(agent_id, "memory", question, hit["id"])
        return {"answer": hit["content"], "source": "memory", "item_id": hit["id"], "topic": hit["topic"]}
    owner = save_to or ("sale" if agent_id.startswith("sale-") else "all" if agent_id == "ceo" else agent_id)
    if not llm.live:
        pid = db.run("""INSERT INTO knowledge(agent_id, topic, question, content, source, status, created_at, updated_at)
                        VALUES (?,?,?,?,'claude','pending',?,?)""", (owner, question[:150], question, "", db.now(), db.now()))
        _log(agent_id, "pending", question, pid)
        return {"answer": None, "source": "none", "pending_id": pid}
    rel = block(agent_id, question)
    prompt = (f"Câu hỏi trong công việc của bạn: {question}\n" + (f"Bối cảnh: {context[:800]}\n" if context else "")
              + "Trả lời ngắn gọn, thực tế, áp dụng được ngay cho xưởng trà & bột bán sỉ online ở Việt Nam (dưới 120 chữ). "
                "Không bịa số liệu, chính sách của xưởng. Trả về JSON {\"answer\": \"...\", \"topic\": \"chủ đề ngắn\", "
                "\"keywords\": \"vài từ khóa\", \"reusable\": true|false} (reusable=false nếu câu trả lời chỉ đúng cho riêng lần này).")
    data = llm.json(system_prompt("sale-0" if agent_id == "sale" else agent_id, db.get_settings()) + rel, prompt, mock=None,
                    max_tokens=500, task="knowledge")
    if not isinstance(data, dict) or not data.get("answer"):
        return {"answer": None, "source": "error"}
    iid = save(owner, data.get("topic") or question, data["answer"], question=question, keywords=data.get("keywords") or "",
               source="claude") if data.get("reusable", True) else None
    _log(agent_id, "claude", question, iid)
    return {"answer": data["answer"], "source": "claude", "item_id": iid, "topic": data.get("topic")}


def learn_answer(agent_id: str, question: str, answer: str, topic: str = "", keywords: str = "", kind: str = "faq") -> int | None:
    """Lưu kiến thức Claude vừa trả về trong một việc khác (VD Hà soạn tin cho khách) để lần sau tự trả lời."""
    iid = save(agent_id, topic or question, answer, question=question, keywords=keywords, source="claude", kind=kind)
    _log(agent_id, "claude", question, iid)
    return iid


# ---------------------------------------------------------------- tự học mỗi ngày
def _studied_topics(agent_id: str) -> set:
    return {plain(r["topic"]) for r in db.q("SELECT topic FROM knowledge WHERE agent_id=? AND status='active'", (agent_id,))}


def _today_topics(agent_id: str) -> list[str]:
    """Chủ đề theo việc thực tế đang làm."""
    out = []
    try:
        hot = [r["name"] for r in db.q("SELECT name FROM products WHERE hot=1")]
        if agent_id == "lan":
            out += [f"cách viết bài bán sỉ thu hút cho sản phẩm {n}" for n in hot[:1]]
        if agent_id == "ha":
            out += [f"cách tư vấn và chốt khách sỉ cho sản phẩm {n}" for n in hot[:1]]
            out += [f"trả lời câu khách hỏi: “{r['need'][:80]}”" for r in db.q(
                """SELECT need FROM leads WHERE COALESCE(need,'')!='' AND created_at >= ? ORDER BY id DESC LIMIT 20""",
                ((db.clock() - timedelta(days=7)).strftime("%Y-%m-%d"),)) if "?" in (r["need"] or "")][:2]
        if agent_id == "tuan":
            import group_finder
            kws = group_finder.today_keywords()
            out += [f"cách đăng bài hiệu quả trong nhóm “{kws[0]}”"] if kws else []
    except Exception:
        pass
    return out


def plan_topics(agent_id: str, n: int) -> list[dict]:
    """Câu hỏi còn bỏ ngỏ trước, rồi chủ đề theo việc thực tế, rồi giáo trình."""
    done = _studied_topics(agent_id)
    owners = [agent_id] + (["all"] if agent_id == "ceo" else [])  # câu sếp hỏi chung do CEO học thay cả đội
    pend = db.q(f"SELECT * FROM knowledge WHERE agent_id IN ({','.join('?' * len(owners))}) AND status='pending' ORDER BY id LIMIT ?",
                (*owners, n))
    out = [{"topic": p["question"], "pending_id": p["id"], "owner": p["agent_id"]} for p in pend]
    for t in _today_topics(agent_id) + CURRICULUM.get(agent_id, []):
        if len(out) >= n:
            break
        if plain(t) not in done and all(plain(t) != plain(o["topic"]) for o in out):
            out.append({"topic": t})
    return out[:n]


def study_agent(agent_id: str, n: int = 2) -> list[int]:
    from agents import system_prompt
    from llm import llm
    topics = plan_topics(agent_id, n)
    saved = []
    if not topics:
        return saved
    if llm.live:
        have = [r["topic"] for r in db.q("SELECT topic FROM knowledge WHERE agent_id=? AND status='active' ORDER BY id DESC LIMIT 40",
                                         (agent_id,))]
        prompt = ("Hôm nay bạn tự học để làm việc tốt hơn. Với mỗi chủ đề dưới đây, viết 1 mục kiến thức thực tế, cụ thể, áp dụng "
                  "ngay cho công việc của bạn ở xưởng trà & bột bán sỉ online (mỗi mục dưới 110 chữ, có ví dụ ngắn nếu được). "
                  "Không bịa số liệu hay chính sách của xưởng; điều chưa chắc thì nói là kinh nghiệm chung.\n"
                  "Chủ đề:\n" + "\n".join(f"{i + 1}. {t['topic']}" for i, t in enumerate(topics))
                  + (f"\nĐã biết (đừng lặp lại): {'; '.join(have[:25])}" if have else "")
                  + '\nTrả về JSON {"items": [{"topic": "...", "question": "câu hỏi mà kiến thức này trả lời", '
                    '"content": "...", "keywords": "..."}]} theo đúng thứ tự chủ đề.')
        data = llm.json(system_prompt("sale-0" if agent_id == "sale" else agent_id, db.get_settings(), with_learning=False),
                        prompt, mock=None, max_tokens=900, task="knowledge")
        items = (data or {}).get("items") or [] if isinstance(data, dict) else []
        for t, it in zip(topics, items):
            if not isinstance(it, dict):
                continue
            iid = save(t.get("owner") or agent_id, it.get("topic") or t["topic"], it.get("content") or "",
                       question=(t["topic"] if t.get("pending_id") else it.get("question")) or "",
                       keywords=it.get("keywords") or "", source="study")
            if iid:
                saved.append(iid)
                if t.get("pending_id"):
                    db.run("DELETE FROM knowledge WHERE id=?", (t["pending_id"],))
                _log(agent_id, "study", it.get("topic") or t["topic"], iid)
    else:  # chưa có khóa Claude: học từ thư viện có sẵn
        lib = {plain(x[0]): x for x in LIBRARY.get(agent_id, [])}
        done = _studied_topics(agent_id)
        for topic, q, content, kw in [x for k, x in lib.items() if k not in done][:n]:
            iid = save(agent_id, topic, content, question=q, keywords=kw, source="library")
            if iid:
                saved.append(iid)
                _log(agent_id, "study", topic, iid)
    return saved


STUDY_AGENTS = ["lan", "tuan", "ha", "khoa", "mai", "minh", "ceo", "sale"]


def study_all(n: int | None = None) -> dict:
    import workflows
    n = n or int(db.get_settings().get("study_per_agent") or 2)
    res = {}
    for a in STUDY_AGENTS:
        try:
            if a in ("lan", "tuan", "ha", "khoa", "minh", "ceo"):
                workflows.set_status(a, "working", "Đang tự học kiến thức mới")
            ids = study_agent(a, n)
            res[a] = ids
            if ids:
                topics = [r["topic"] for r in db.q(f"SELECT topic FROM knowledge WHERE id IN ({','.join('?' * len(ids))})", tuple(ids))]
                db.log(a if a != "sale" else "minh", "Học kiến thức mới",
                       (f"{ROLE_NAME[a]}: " if a == "sale" else "") + "; ".join(topics))
        except Exception as e:
            print("[knowledge]", a, e)
            import errors
            errors.report_exc("ai", f"{ROLE_NAME.get(a, a)} tự học kiến thức bị lỗi", e, screen="learn")
        finally:
            if a in ("lan", "tuan", "ha", "khoa", "minh", "ceo"):
                workflows.set_status(a, "idle", "Đã học xong kiến thức hôm nay")
    db.set_setting("study_last_date", db.today())
    return res


def tick(now: datetime):
    st = db.get_settings()
    if st.get("knowledge_enabled", "1") != "1" or st.get("study_last_date") == db.today():
        return
    if now.strftime("%H:%M") >= (st.get("study_time") or "07:00"):
        db.set_setting("study_last_date", db.today())
        import threading
        threading.Thread(target=study_all, daemon=True).start()


# ---------------------------------------------------------------- số liệu cho giao diện
def overview(agent: str = "", query: str = "", limit: int = 60) -> dict:
    where, args = ["status IN ('active','pending')"], []
    if agent:
        where.append("agent_id=?")
        args.append(agent)
    rows = db.q(f"SELECT * FROM knowledge WHERE {' AND '.join(where)} ORDER BY id DESC LIMIT 400", tuple(args))
    if query:
        q = tokens(query)
        rows = [r for r in rows if q and _score(q, set(), r) >= 0.5]
    since = (db.clock() - timedelta(days=30)).strftime("%Y-%m-%d")
    c = {r["kind"]: r["n"] for r in db.q("SELECT kind, COUNT(*) n FROM knowledge_log WHERE created_at >= ? GROUP BY kind", (since,))}
    mem, cl = c.get("memory", 0), c.get("claude", 0)
    return {"items": rows[:limit],
            "counts": {r["agent_id"]: r["n"] for r in db.q("SELECT agent_id, COUNT(*) n FROM knowledge WHERE status='active' GROUP BY agent_id")},
            "total": db.one("SELECT COUNT(*) n FROM knowledge WHERE status='active'")["n"],
            "pending": db.one("SELECT COUNT(*) n FROM knowledge WHERE status='pending'")["n"],
            "today": db.one("SELECT COUNT(*) n FROM knowledge WHERE created_at LIKE ? AND status='active'", (db.today() + "%",))["n"],
            "month": {"memory": mem, "claude": cl, "study": c.get("study", 0),
                      "self_rate": round(mem / (mem + cl) * 100) if mem + cl else None},
            "roles": ROLE_NAME, "sources": SOURCE_TXT,
            "settings": {k: st for k, st in db.get_settings().items() if k in ("knowledge_enabled", "study_time", "study_per_agent",
                                                                                "knowledge_answer_threshold", "study_last_date",
                                                                                "idle_learning", "idle_study_per_day")}}

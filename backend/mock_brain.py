"""Bộ não mô phỏng: cho phép chạy thử hệ thống khi chưa có API key.
Khi có ANTHROPIC_API_KEY, mọi nội dung sẽ do Claude viết thay cho các mẫu này."""
import random
import unicodedata

ANGLES = {
    "nguon_hang": "Nguồn hàng tận xưởng",
    "loi_nhuan": "Biên lợi nhuận cho người bán",
    "livestream": "Sản phẩm dễ livestream",
    "ads": "Sản phẩm dễ chạy quảng cáo",
    "oem": "Nhận in nhãn riêng (OEM)",
    "cau_chuyen": "Câu chuyện xưởng",
}

OPENERS = {
    "nguon_hang": ["📦 TÌM ĐẦU MỐI {cat} TẬN XƯỞNG — KHÔNG QUA TRUNG GIAN",
                   "🏭 Xưởng mình trực tiếp sản xuất {name}, cần thêm bạn bán online cùng phát triển"],
    "loi_nhuan": ["💰 Nhập tận xưởng, biên lãi tốt cho shop online",
                  "Ai đang tìm sản phẩm biên lời tốt để bán quanh năm thì đọc bài này nhé 👇"],
    "livestream": ["🎥 Sản phẩm 'lên hình là bán': {name}",
                   "Live 30 phút pha {name} cho khách xem — đây là món mình gợi ý cho các bạn chủ live"],
    "ads": ["📈 Tìm sản phẩm test ads chi phí thấp? Thử {name}",
            "Dân chạy ads cần gì ở một sản phẩm? Dễ hiểu, dễ quay, khách mua lặp lại — {name} có đủ"],
    "oem": ["🏷️ Muốn có thương hiệu {cat} của riêng mình? Xưởng nhận in nhãn từ số lượng nhỏ",
            "Bán hàng lâu dài thì nên có nhãn riêng — xưởng mình làm OEM {cat}"],
    "cau_chuyen": ["☕ Một ngày ở xưởng: từ nguyên liệu tới hộp {name}",
                   "Chuyện xưởng nhỏ làm {cat}: chậm một chút nhưng chắc"],
}


def post(product: dict, angle: str, target_type: str, settings: dict) -> dict:
    name, cat = product["name"], product.get("category", "")
    fill = dict(name=name, cat=cat.lower(), wp=product.get("wholesale_price", ""),
                rp=product.get("retail_price", ""))
    title = random.choice(OPENERS.get(angle, OPENERS["nguon_hang"])).format(**fill)
    body = [title, "",
            f"🌿 {name}: {product.get('description', '')}",
            f"✅ Điểm mạnh khi bán: {product.get('selling_points', '')}",
            f"📦 Nhập tối thiểu: {product.get('moq', '')}"]
    body += ["", "Xưởng hỗ trợ người bán online:",
             "• Ảnh, video thật quay tại xưởng để các bạn đăng bán",
             "• Gửi mẫu thử trước khi nhập",
             "• Đóng gói sẵn để giao hàng sàn TMĐT"]
    if target_type == "group":
        body += ["", "Bạn nào quan tâm để lại bình luận \"quan tâm\", mình inbox tư vấn nhé!"]
    else:
        body += ["", f"Liên hệ: {settings.get('contact_info', '')}"]
    plain = unicodedata.normalize("NFD", cat).encode("ascii", "ignore").decode().replace(" ", "").lower()
    tags = "#nguonhangsi #taxuong #banhangonline #" + plain.replace("đ", "d")
    return {"title": title, "content": "\n".join(body), "hashtags": tags, "_mock": True,
            "image_idea": f"Ảnh thật {name} đặt trên bàn gỗ trong xưởng, có tay người pha/đóng gói, chữ to: GIÁ SỈ TẬN XƯỞNG"}


def lead_reply(lead: dict, message: str) -> str:
    n = lead.get("name") or "bạn"
    return (f"Chào {n} ạ! Cảm ơn {n} đã quan tâm hàng bên xưởng 🌿\n"
            f"Mình gửi {n} hình ảnh, video thật nhé; giá sỉ {n} nhắn Zalo {__import__('pricing').zalo()} để được báo trực tiếp. Với nhu cầu \"{lead.get('need') or message}\", "
            "mình gợi ý {n} nhập thử combo nhỏ trước để test thị trường, xưởng gửi kèm mẫu thử + bộ ảnh/video "
            "để {n} đăng bán luôn.\n"
            f"{n} đang bán chủ yếu kênh nào (live, ads hay sàn) để mình tư vấn sản phẩm hợp nhất ạ?").replace("{n}", n)


def meeting_open(topic: str) -> str:
    return random.choice([
        f"Chào cả nhóm, bắt đầu họp giao ban. Mỗi người báo cáo nhanh 1 phút, sau đó mình bàn chủ đề: \"{topic}\".",
        f"Ok mọi người, họp sáng nay gọn nhé: báo cáo trước, rồi tranh luận \"{topic}\", cuối giờ mình chốt việc.",
    ])


def report(agent_id: str, st: dict) -> str:
    if agent_id == "lan":
        return (f"Bên content: kho đang có {st['drafts']} bài nháp, {st['approved']} bài đã duyệt chờ đăng. "
                f"Hôm qua viết thêm {st['posts_yesterday']} bài. Góc 'dễ livestream' đang được bình luận nhiều nhất, "
                "hôm nay em muốn làm thêm bài kèm video pha trà.")
    if agent_id == "tuan":
        return (f"Đang theo dõi {st['groups']} nhóm. Hôm nay có {st['groups_ready']} nhóm đủ điều kiện đăng lại "
                "theo luật giãn cách. Em đề nghị không đăng trùng nội dung giữa các nhóm để tránh bị báo spam.")
    if agent_id == "ha":
        return (f"Tổng {st['leads']} khách tiềm năng, {st['leads_new']} khách mới chưa liên hệ, "
                f"{st['leads_hot']} khách nóng (điểm ≥ 75). Khách hỏi nhiều nhất là chính sách gửi mẫu và giá theo số lượng.")
    if agent_id == "khoa" and st.get("kpi"):
        k = st["kpi"]
        return (f"KPI: hôm nay đang có {k['leads_phone']}/{k['target_min']} khách để lại SĐT, đã xin SĐT {k['asked_phone']} người qua bình luận. "
                f"Tổng {st['posted_total']} bài đã đăng, {st['leads']} khách. Đề nghị ưu tiên up các bài đang nhiều bình luận.")
    if agent_id == "khoa":
        best = st.get("best_group") or "chưa đủ dữ liệu"
        return (f"Số liệu: {st['posted_total']} bài đã đăng, thu về {st['leads']} khách. "
                f"Nhóm hiệu quả nhất: {best}. Tỉ lệ khách/bài hiện là {st['lead_per_post']}. "
                "Đề nghị gắn nguồn cho mọi khách để đo chính xác hơn.")
    return ""


DEBATE = {
    "lan": [
        "Em nghĩ phải mạnh dạn hơn: nội dung có video thật, câu chuyện xưởng sẽ tạo khác biệt so với bài nguồn hàng đăng tràn lan.",
        "Khách sỉ cũng là người lướt Facebook, bài nào đẹp, có cảm xúc thì họ mới dừng lại đọc. Em ủng hộ thử cách mới.",
        "Em đồng ý cần số liệu, nhưng nếu không thử nội dung mới thì lấy đâu ra số liệu để so sánh ạ?",
    ],
    "tuan": [
        "Em hơi lo: nhóm lớn kiểm duyệt rất chặt, làm quá tay là bị chặn đăng cả nick. Phải tuân thủ luật nhóm trước.",
        "Theo kinh nghiệm của em, ít bài nhưng đúng giờ, đúng chủ đề nhóm cho kết quả bền hơn đăng dồn dập.",
        "Em đề xuất làm thử ở 2 nhóm nhỏ trước, nhóm lớn giữ nhịp cũ, tránh rủi ro mất nhóm.",
    ],
    "ha": [
        "Từ phía khách thì họ cần 3 thứ: giá rõ, có mẫu thử, có ảnh/video để bán lại. Mình đáp ứng được là chốt nhanh.",
        "Nhiều khách mới bán online, họ sợ ôm hàng. Chính sách nhập ít, đổi trả linh hoạt sẽ thuyết phục hơn mọi bài viết.",
        "Em ủng hộ hướng nào giúp khách bán được hàng, vì khách bán được thì mới nhập lại lần hai.",
    ],
    "khoa": [
        "Hiện dữ liệu chưa đủ để kết luận. Em đề xuất A/B test trong 7 ngày: chia đôi số bài, đo số khách và tỉ lệ chốt.",
        "Em nhắc lại: cái gì không đo được thì không cải thiện được. Mỗi bài cần gắn mã theo dõi nguồn khách.",
        "Nếu làm theo hướng của Lan thì đặt ngưỡng: sau 7 ngày không tăng ít nhất 20% khách/bài thì quay lại cách cũ.",
    ],
}


def debate(agent_id: str, round_no: int, topic: str) -> str:
    lines = DEBATE.get(agent_id, ["Em đồng ý với ý kiến trên."])
    return lines[min(round_no, len(lines) - 1)] if round_no < 2 else random.choice(lines)


def conclusion(topic: str) -> dict:
    return {
        "summary": (f"Về chủ đề \"{topic}\": thống nhất thử nghiệm có kiểm soát trong 7 ngày. "
                    "Lan làm nội dung mới kèm video thật, Tuấn chỉ áp dụng ở nhóm nhỏ và giữ đúng luật nhóm lớn, "
                    "Hà chuẩn hóa chính sách mẫu thử, Khoa đo A/B và báo cáo lại cuối tuần."),
        "action_items": [
            {"agent_id": "lan", "title": "Viết 3 bài mới có kịch bản video pha chế tại xưởng"},
            {"agent_id": "tuan", "title": "Chọn 2 nhóm nhỏ để thử nghiệm, lên lịch đăng tuần này"},
            {"agent_id": "ha", "title": "Soạn kịch bản tin nhắn gửi mẫu thử cho khách mới"},
            {"agent_id": "khoa", "title": "Thiết lập bảng A/B: khách/bài theo từng góc nội dung"},
        ],
    }


def chair_reply(boss_text: str) -> str:
    return f"Dạ em ghi nhận ý kiến của sếp: \"{boss_text}\". Cả nhóm sẽ tính đến điểm này khi chốt việc."

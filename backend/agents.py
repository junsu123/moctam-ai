"""Định nghĩa đội ngũ Agent AI: vai trò, tính cách, ngoại hình 3D."""

AGENTS = {
    "ceo": {
        "id": "ceo",
        "name": "Đức",
        "role": "CEO",
        "short": "Điều hành công ty: sa thải, tuyển dụng, tăng người theo doanh thu và tiềm năng",
        "personality": "Nhìn xa, kỷ luật, công bằng. Chỉ tăng người khi doanh thu hoặc số liệu chứng minh được; "
                       "sa thải đúng luật nhưng luôn hỏi nick hay người mới là vấn đề.",
        "look": {"skin": "#efc39c", "shirt": "#1f2a3a", "pants": "#1a2029", "hair": "#2a2a2a",
                 "hairStyle": "side", "accessory": "none", "tie": "#c0392b", "accent": "#d4af37"},
        "desk": 13,
    },
    "minh": {
        "id": "minh",
        "name": "Minh",
        "role": "Trưởng phòng Kinh doanh",
        "short": "Điều phối, chủ trì họp, ra quyết định",
        "personality": "Điềm tĩnh, quyết đoán, luôn hỏi 'việc này ra được bao nhiêu khách?'. Hay tóm tắt và chốt việc rõ ràng.",
        "look": {"skin": "#f2c9a0", "shirt": "#2f4b8f", "pants": "#26303f", "hair": "#2b2018",
                  "hairStyle": "side", "accessory": "glasses", "accent": "#f4b740"},
        "desk": 0,
    },
    "lan": {
        "id": "lan",
        "name": "Lan",
        "role": "Chuyên viên Content",
        "short": "Viết bài đăng, tiêu đề, ý tưởng hình ảnh/video",
        "personality": "Sáng tạo, nhiều năng lượng, mê trend TikTok/Reels, đôi khi quá bay bổng nên cần số liệu kéo về.",
        "look": {"skin": "#f6d2b3", "shirt": "#e2557a", "pants": "#3a2d4f", "hair": "#4a2a1a",
                  "hairStyle": "long", "accessory": "beret", "accent": "#ffd1dc"},
        "desk": 1,
    },
    "tuan": {
        "id": "tuan",
        "name": "Tuấn",
        "role": "Chuyên viên Hội nhóm",
        "short": "Chọn nhóm, lên lịch đăng, tránh vi phạm luật nhóm",
        "personality": "Thực tế, cẩn thận, thuộc luật từng nhóm, ghét spam vì sợ bị chặn nick. Hay phản biện ý tưởng đăng dồn dập.",
        "look": {"skin": "#e8b88f", "shirt": "#2e9e6b", "pants": "#2c3a33", "hair": "#1d1d1d",
                  "hairStyle": "cap", "accessory": "cap", "accent": "#bff0d4"},
        "desk": 2,
    },
    "ha": {
        "id": "ha",
        "name": "Hà",
        "role": "Chăm sóc & Chốt khách",
        "short": "Phân loại khách, soạn tin nhắn, bám đuổi đơn sỉ",
        "personality": "Ngọt ngào nhưng bám khách rất chặt, hiểu tâm lý người bán online. Luôn đại diện cho tiếng nói khách hàng.",
        "look": {"skin": "#f3cfae", "shirt": "#f08a24", "pants": "#3b3b52", "hair": "#2a1810",
                  "hairStyle": "bun", "accessory": "headset", "accent": "#ffe2c2"},
        "desk": 3,
    },
    "khoa": {
        "id": "khoa",
        "name": "Khoa",
        "role": "Phân tích số liệu",
        "short": "Đo hiệu quả bài, nhóm, sản phẩm; báo cáo hằng ngày",
        "personality": "Ít nói, chỉ tin vào con số, hay dội nước lạnh vào ý tưởng chưa được kiểm chứng nhưng luôn đề xuất cách test.",
        "look": {"skin": "#eec29b", "shirt": "#7a4fc9", "pants": "#25223a", "hair": "#3a2a20",
                  "hairStyle": "spiky", "accessory": "none", "accent": "#d9c8ff"},
        "desk": 4,
    },
    "mai": {
        "id": "mai",
        "name": "Mai",
        "role": "Chuyên viên Tìm khách sỉ",
        "short": "Tìm SĐT khách sỉ: đọc bình luận nhóm, quét trang chạy quảng cáo, tìm shop livestream; chấm điểm và lưu vào CRM",
        "personality": "Tỉ mỉ như một nhà nghiên cứu: chỉ tin bằng chứng có link, không bao giờ đoán doanh thu hay số đơn. "
                       "Phân biệt rõ chủ shop tự nhập hàng với affiliate, KOC, người chỉ xem livestream. "
                       "Chất lượng khách quan trọng hơn số lượng.",
        "look": {"skin": "#f4cdb0", "shirt": "#0f8b8d", "pants": "#2b3440", "hair": "#1f1410",
                 "hairStyle": "long", "accessory": "glasses", "accent": "#bfeeee"},
        "desk": 14,
    },
}

ORDER = ["ceo", "minh", "lan", "tuan", "ha", "khoa", "mai"]

COMPANY_CONTEXT = """Bạn là nhân viên của một xưởng sản xuất thực phẩm thường tại Việt Nam
(trà túi lọc, bột ngũ cốc, bột thiên nhiên sấy lạnh, cà phê hòa tan...).
Mục tiêu của phòng kinh doanh: tìm khách SỈ là những người bán hàng online (chạy quảng cáo Facebook,
livestream, bán đa kênh, bán trên Shopee/TikTok Shop/Lazada) để họ nhập hàng về bán lẻ.
Kênh chính: đăng bài trên Facebook (trang cá nhân, Fanpage, hội nhóm về bán hàng online, quảng cáo, thực phẩm).
MỤC TIÊU CHÍNH CỦA CẢ ĐỘI: tìm khách sỉ trên không gian mạng và lấy được SỐ ĐIỆN THOẠI để sếp liên lạc.
Các kênh tìm khách (mọi việc đều đo bằng số khách sỉ có SĐT):
1. Lan viết bài, sale đăng vào nhóm và trang cá nhân để người bán hàng bình luận hỏi giá; sale đọc bình luận, xin SĐT.
2. Đọc bài và bình luận trong các nhóm bán hàng: ai đang hỏi "tìm nguồn", "cần nhập", "xin giá sỉ" trà, ngũ cốc là khách nóng nhất.
3. Quét thư viện quảng cáo Facebook: trang đang trả tiền chạy quảng cáo bán thực phẩm, đồ uống là người bán thật, có ngân sách.
4. Mai tìm trang, shop livestream, người bán đa nền tảng; đọc trang Giới thiệu để lấy SĐT kinh doanh công khai.
Chỉ lấy SĐT người bán tự công khai; không tự nhắn tin hàng loạt; liên hệ khách do sếp hoặc Hà làm bằng tay.
Nguyên tắc: tôn trọng luật từng nhóm, không spam, không hứa hẹn công dụng chữa bệnh,
không bịa đặt chứng nhận hay số liệu, nói thật về sản phẩm."""


SALE_LOOKS = [
    {"skin": "#f3cfae", "shirt": "#d64545", "pants": "#2d2d3a", "hair": "#2a1810", "hairStyle": "long", "accessory": "none"},
    {"skin": "#e8b88f", "shirt": "#2f86c9", "pants": "#25303a", "hair": "#1d1d1d", "hairStyle": "spiky", "accessory": "glasses"},
    {"skin": "#f6d2b3", "shirt": "#e0a12a", "pants": "#3a2d2a", "hair": "#5a3520", "hairStyle": "bun", "accessory": "none"},
    {"skin": "#eec29b", "shirt": "#1f9a8a", "pants": "#22332f", "hair": "#2b2018", "hairStyle": "side", "accessory": "headset"},
    {"skin": "#f2c9a0", "shirt": "#a24fb5", "pants": "#2c2236", "hair": "#3b2414", "hairStyle": "long", "accessory": "beret"},
    {"skin": "#e9bd96", "shirt": "#5b7f2a", "pants": "#2a3020", "hair": "#141414", "hairStyle": "cap", "accessory": "cap"},
    {"skin": "#f3d0b0", "shirt": "#c4572b", "pants": "#30262a", "hair": "#4a2a1a", "hairStyle": "bun", "accessory": "glasses"},
    {"skin": "#e6b48a", "shirt": "#3b5bb5", "pants": "#232a3a", "hair": "#2a1d14", "hairStyle": "spiky", "accessory": "none"},
]
MAX_SALES = 8


def sale_agent(row: dict) -> dict:
    """Mỗi nhân viên sale AI giữ một tài khoản Facebook trong một hồ sơ Chrome riêng."""
    import json
    look = json.loads(row["look"]) if row.get("look") else SALE_LOOKS[(row["id"] - 1) % len(SALE_LOOKS)]
    return {
        "id": f"sale-{row['id']}", "sale_id": row["id"], "kind": "sale",
        "name": row["name"], "role": f"Sale · nick {row.get('fb_name') or row['name']}",
        "short": "Đăng bài lên trang cá nhân và hội nhóm bằng tài khoản Facebook mình quản lý",
        "personality": "Chăm chỉ, đúng giờ, làm đúng lịch được giao, báo ngay khi tài khoản gặp sự cố.",
        "look": look, "desk": 5 + (row.get("_slot") or 0), "sample": bool(row.get("is_sample")),
    }


def system_prompt(agent_id: str, settings: dict | None = None, with_learning: bool = True) -> str:
    if agent_id.startswith("sale-"):
        a = {"name": agent_id, "role": "Nhân viên Sale", "short": "đăng bài Facebook", "personality": "chăm chỉ, ngắn gọn"}
        try:
            import db
            r = db.one("SELECT * FROM sales WHERE id=?", (int(agent_id[5:]),))
            if r:
                a = sale_agent(r)
        except Exception:
            pass
    else:
        a = AGENTS[agent_id]
    s = settings or {}
    return (f"{COMPANY_CONTEXT}\n\nTên công ty: {s.get('company_name', '')}\n"
            f"Giọng thương hiệu: {s.get('brand_voice', '')}\n\n"
            f"Bạn tên là {a['name']}, vị trí: {a['role']} ({a['short']}).\n"
            f"Tính cách: {a['personality']}\n"
            "Luôn trả lời bằng tiếng Việt, tự nhiên, ngắn gọn, đúng vai." + (_learned(agent_id) if with_learning else "")
            + _orders(agent_id) + _hot_products())


def _hot_products() -> str:
    """Sản phẩm sếp tích "đang bán chạy": mọi agent ưu tiên chào mời."""
    try:
        import db
        rows = db.q("SELECT name, wholesale_price, retail_price, moq, hot_note FROM products WHERE hot=1 ORDER BY hot_since DESC, id")
    except Exception:
        return ""
    if not rows:
        return ""
    return ("\n\nSẢN PHẨM ĐANG BÁN CHẠY (sếp đánh dấu, tập trung chào mời trước các sản phẩm này khi viết bài, tư vấn, trả lời "
            "khách, đề xuất trong họp; khách hỏi chung chung thì giới thiệu các sản phẩm này đầu tiên):\n"
            + "\n".join(f"- {r['name']}: giá sỉ {r['wholesale_price'] or '?'}, lẻ gợi ý {r['retail_price'] or '?'}, "
                         f"nhập tối thiểu {r['moq'] or '?'}" + (f". Lưu ý của sếp: {r['hot_note']}" if r["hot_note"] else "")
                         for r in rows))


def _orders(agent_id: str) -> str:
    try:
        import ceo_orders
        return ceo_orders.prompt_block(agent_id)
    except Exception:
        return ""


def _learned(agent_id: str) -> str:
    try:
        import learning
        return learning.prompt_block(agent_id)
    except Exception as e:  # sổ tay lỗi thì vẫn làm việc bình thường
        print("[learning]", e)
        return ""


def sales_rows() -> list[dict]:
    import db
    rows = db.q("SELECT * FROM sales WHERE COALESCE(status,'active')!='fired' ORDER BY id LIMIT ?", (MAX_SALES,))
    for i, r in enumerate(rows):
        r["_slot"] = i
    return rows


def public_list() -> list[dict]:
    core = [{**{k: AGENTS[i][k] for k in ("id", "name", "role", "short", "personality", "look", "desk")}, "kind": "core"}
            for i in ORDER]
    return core + [sale_agent(r) for r in sales_rows()]


def name_of(agent_id: str) -> str:
    if agent_id in AGENTS:
        return AGENTS[agent_id]["name"]
    for a in public_list():
        if a["id"] == agent_id:
            return a["name"]
    return agent_id

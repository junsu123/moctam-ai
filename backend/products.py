"""Sản phẩm: đánh dấu "đang bán chạy" để cả đội tập trung chào mời.

Sản phẩm bán chạy được: Lan viết nhiều bài hơn (mặc định 70% số bài, chỉnh bằng cài đặt hot_share), mọi agent nhận
danh sách này trong lời dặn (Hà tư vấn, trả lời khách, Minh và CEO đề xuất trong họp), Tuấn up bài của sản phẩm này
trước, báo cáo sáng trên Telegram nhắc sản phẩm đang đẩy.
"""
import db


def hot_list() -> list[dict]:
    return db.q("SELECT * FROM products WHERE hot=1 ORDER BY hot_since DESC, id")


def set_hot(pid: int, hot: bool, by: str = "boss") -> bool:
    p = db.one("SELECT name, hot FROM products WHERE id=?", (pid,))
    if not p or bool(p["hot"]) == bool(hot):
        return False
    db.run("UPDATE products SET hot=?, hot_since=? WHERE id=?", (1 if hot else 0, db.now() if hot else None, pid))
    db.log("ceo" if by == "ceo" else "minh", "Sản phẩm bán chạy",
           f"{p['name']}: {'đang bán chạy, cả đội tập trung chào mời' if hot else 'thôi ưu tiên, chào như các sản phẩm khác'}")
    return True

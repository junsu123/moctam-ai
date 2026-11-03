"""Sổ lỗi tập trung: mọi lỗi ở bất kỳ màn hình hay công việc tự động nào đều ghi về đây, kèm cách xử lý.

Nguồn lỗi: giao diện (thao tác của sếp bị lỗi), phần mềm (API), đăng bài, up bài, quét bình luận, Chrome, nick
Facebook, Telegram, AI Claude, Fanpage, lịch tự động. Lỗi giống nhau (cùng nguồn, cùng nội dung, khác con số) được
gộp lại và đếm số lần lặp, để màn hình Lỗi không bị ngập.
"""
import hashlib
import re
import traceback

import db

SOURCES = {
    "ui": "Giao diện", "api": "Phần mềm", "post": "Đăng bài", "bump": "Up bài", "scan": "Quét bình luận",
    "browser": "Chrome", "nick": "Nick Facebook", "telegram": "Telegram", "ai": "AI Claude", "fanpage": "Fanpage",
    "scheduler": "Lịch tự động",
}

# (mẫu lỗi, cách xử lý, màn hình nên mở)
HINTS = [
    (r"chưa có link|chưa có đường dẫn", "Vào Hội nhóm, bấm “Thêm link” ở dòng nhóm đó, dán link nhóm rồi đăng lại.", "groups"),
    (r"không phải link nhóm|Dán link nhóm", "Mở nhóm trên Facebook bằng máy tính, copy địa chỉ trên thanh trình duyệt "
     "(dạng https://www.facebook.com/groups/…) rồi dán lại.", "groups"),
    (r"chưa là thành viên nhóm|Tham gia nhóm", "Vào Nhân viên sale → Mở Chrome của sale đó, vào nhóm bấm Tham gia, "
     "chờ quản trị viên duyệt rồi đăng lại.", "sales"),
    (r"chờ quản trị viên duyệt vào nhóm", "Nick đã xin vào nhóm, đang chờ duyệt. Đăng lại sau khi được duyệt.", "groups"),
    (r"đang (được )?mở ở một cửa sổ|already in use|ProcessSingleton|SingletonLock",
     "Đóng cửa sổ Chrome của sale (cửa sổ mở bằng nút Mở Chrome) rồi thử lại.", "sales"),
    (r"Hồ sơ Chrome của nick được tạo bằng trình duyệt bản", "Cập nhật Google Chrome trên máy lên bản mới nhất "
     "(menu ⋮ → Trợ giúp → Giới thiệu về Google Chrome), khởi động lại máy rồi bấm Kiểm tra phiên ở trang Nhân viên sale.", "sales"),
    (r"bị đóng khi sale đang làm việc", "Để yên cửa sổ Chrome khi sale đang làm. Muốn không thấy cửa sổ: Cài đặt → bật “Ẩn cửa sổ "
     "Chrome khi sale đăng bài”.", "setup"),
    (r"Target page, context or browser has been closed|Browser closed|browser has disconnected|tự đóng ngay khi vừa mở",
     "Chrome của sale bị đóng ngay khi mở. Thường do: (1) hồ sơ Chrome của nick đang mở ở cửa sổ khác: đóng hết cửa sổ Chrome "
     "của sale này; (2) Google Chrome trên máy quá cũ: cập nhật Chrome; (3) phần mềm diệt virus chặn Chrome. Sau đó bấm "
     "Kiểm tra phiên ở trang Nhân viên sale.", "sales"),
    (r"checkpoint|bị khóa|tạm khóa|Temporarily Blocked|suspended|Xác nhận danh tính",
     "Facebook đang kiểm tra nick. Vào Nhân viên sale → Mở Chrome, tự xử lý xác minh trên Facebook, "
     "xong bấm Bật tự đăng. Nên giảm số bài/ngày của nick này.", "sales"),
    (r"chưa đăng nhập|Phiên đăng nhập đã hết|not_logged_in",
     "Vào Nhân viên sale → Mở Chrome để đăng nhập lại Facebook cho nick này.", "sales"),
    (r"Không tìm thấy ô viết bài|Không tìm thấy nút Đăng|không thấy hộp soạn bài|Bấm Tiếp nhiều lần",
     "Facebook vừa đổi chữ trên nút. Lỗi có ghi tên các nút sale đang thấy: thêm đúng chữ đó vào "
     "backend/fb_selectors.json, hoặc bấm Sao chép rồi gửi cho người hỗ trợ.", "posts"),
    (r"Nút Đăng vẫn bị mờ", "Ảnh tải lên chậm hoặc nội dung chưa điền được. Thử đăng lại; nếu lặp lại, giảm số ảnh mỗi bài "
     "trong Cài đặt.", "posts"),
    (r"chưa đóng sau 90 giây", "Mạng chậm hoặc Facebook đang chặn. Mở nhóm/trang trên Facebook xem bài đã lên chưa "
     "trước khi đăng lại, tránh đăng trùng.", "posts"),
    (r"Không điền được nội dung", "Ô viết bài của Facebook không nhận chữ. Thử đăng lại; nếu lặp lại, gửi lỗi cho người hỗ trợ.", "posts"),
    (r"Không mở được Google Chrome|Executable doesn't exist|is not found",
     "Cài Google Chrome trên máy, hoặc chạy lại run.bat để cài trình duyệt dự phòng.", "sales"),
    (r"Mất kết nối với phần mềm", "Phần mềm trên máy đang tắt hoặc vừa khởi động lại. Chạy lại run.bat, chờ vài giây "
     "rồi tải lại trang.", None),
    (r"ERR_INTERNET_DISCONNECTED|ERR_NAME_NOT_RESOLVED|ERR_CONNECTION|ERR_TIMED_OUT|ConnectError|Connection refused|Connection reset|Network is unreachable|timed out|Timeout \d+ms",
     "Kiểm tra Internet của máy chạy phần mềm. Việc tự động sẽ thử lại ở lượt sau.", None),
    (r"Thư mục ảnh|thư mục ảnh", "Vào Sản phẩm, chọn thư mục ảnh cho sản phẩm (hoặc Cài đặt → Up bài).", "products"),
    (r"authentication_error|invalid x-api-key|Error code: 401", "Khóa API Claude sai hoặc đã bị thu hồi. Vào Cài đặt → Khóa API Claude, "
     "dán khóa mới và bấm Kiểm tra và lưu.", "setup"),
    (r"credit balance|billing|insufficient_quota|Error code: 402", "Tài khoản Anthropic hết tín dụng. Nạp thêm ở console.anthropic.com → Billing.", "setup"),
    (r"rate_limit|Error code: 429|overloaded|Error code: 529", "Máy chủ AI đang quá tải. Phần mềm tự dùng nội dung mô phỏng và thử lại sau.", None),
    (r"chat not found|bot was blocked|Unauthorized|bot token", "Kết nối Telegram bị lỗi. Vào KPI & Báo cáo, kiểm tra token "
     "và ghép nối lại bot.", "kpi"),
    (r"OAuthException|Page Access Token|\(#200\)|\(#190\)", "Token Fanpage sai hoặc hết hạn. Vào Cài đặt, nhập Page Access "
     "Token mới.", "setup"),
    (r"giải thể", "Công ty đã giải thể. Vào trang Công ty để xem lý do và thành lập lại.", "company"),
    (r"Hết vốn|hết vốn", "Vào trang Công ty → Bơm thêm vốn để agent hoạt động tiếp.", "company"),
]


def hint_for(text: str) -> tuple[str | None, str | None]:
    for rx, hint, screen in HINTS:
        if re.search(rx, text or "", re.I):
            return hint, screen
    return None, None


def _fp(source: str, title: str, message: str) -> str:
    norm = re.sub(r"\d+", "#", f"{title}|{message}"[:240].lower())
    return hashlib.md5(f"{source}|{norm}".encode()).hexdigest()


def report(source: str, title: str, message: str = "", detail: str = "", screen: str | None = None,
           ref_type: str | None = None, ref_id=None, screenshot: str | None = None, action: str = "") -> int | None:
    """Ghi một lỗi. Không bao giờ ném lỗi ra ngoài (sổ lỗi hỏng không được làm hỏng việc khác)."""
    try:
        message = (message or "").strip()[:1000]
        hint, hint_screen = hint_for(f"{title} {message}")
        screen = screen or hint_screen
        fp = _fp(source, title, message)
        old = db.one("SELECT id FROM errors WHERE fingerprint=? AND status!='resolved' ORDER BY id DESC LIMIT 1", (fp,))
        if old:
            db.run("""UPDATE errors SET count=count+1, last_at=?, status='new', message=?, detail=?, hint=COALESCE(?, hint),
                      screen=COALESCE(screen, ?), screenshot=COALESCE(?, screenshot), ref_type=COALESCE(?, ref_type),
                      ref_id=COALESCE(?, ref_id) WHERE id=?""",
                   (db.now(), message, (detail or "")[:4000], hint, screen, screenshot, ref_type,
                    str(ref_id) if ref_id else None, old["id"]))
            return old["id"]
        eid = db.run("""INSERT INTO errors(source, title, message, detail, hint, screen, action, ref_type, ref_id, screenshot,
                        fingerprint, count, status, created_at, last_at) VALUES (?,?,?,?,?,?,?,?,?,?,?,1,'new',?,?)""",
                     (source, title[:200], message, (detail or "")[:4000], hint, screen, action[:200], ref_type,
                      str(ref_id) if ref_id else None, screenshot, fp, db.now(), db.now()))
        _trim()
        return eid
    except Exception as e:  # pragma: no cover
        print("[errors] không ghi được lỗi:", e)
        return None


def report_exc(source: str, title: str, exc: BaseException, **kw) -> int | None:
    msg = str(exc).strip().splitlines()[0] if str(exc).strip() else exc.__class__.__name__
    return report(source, title, msg, "".join(traceback.format_exception(type(exc), exc, exc.__traceback__))[-4000:], **kw)


def _trim():
    db.run("DELETE FROM errors WHERE status='resolved' AND last_at < datetime('now','-30 days')")
    n = db.one("SELECT COUNT(*) n FROM errors")["n"]
    if n > 1000:
        db.run("DELETE FROM errors WHERE id IN (SELECT id FROM errors ORDER BY status='new', last_at LIMIT ?)", (n - 1000,))


def count_new() -> int:
    return db.one("SELECT COUNT(*) n FROM errors WHERE status='new'")["n"]


def listing(status: str = "open", source: str = "") -> list[dict]:
    where, p = [], []
    if status == "open":
        where.append("status!='resolved'")
    elif status in ("new", "seen", "resolved"):
        where.append("status=?")
        p.append(status)
    if source:
        where.append("source=?")
        p.append(source)
    sql = "SELECT * FROM errors" + (" WHERE " + " AND ".join(where) if where else "") + " ORDER BY last_at DESC, id DESC LIMIT 300"
    rows = db.q(sql, tuple(p))
    for r in rows:
        r["source_label"] = SOURCES.get(r["source"], r["source"])
    return rows

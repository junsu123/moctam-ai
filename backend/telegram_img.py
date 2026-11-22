"""Bot Telegram thứ hai, riêng cho Nhi (Trang xu hướng): xin ảnh, nhận ảnh, báo việc của các Trang.

Bot chính (telegram_bot.py) vẫn lo báo cáo phòng kinh doanh, khách, CEO. Có bot này thì mọi tin của Nhi (prompt ảnh, ý tưởng Trang mới,
lịch bài, bài đã đăng lên Trang, báo cáo tối) đi qua đây, không lẫn với tin bán hàng. Chưa cài bot này thì Nhi dùng bot chính như trước.

Lệnh: /anh (bài đang chờ ảnh, gửi lại prompt), /trang (các Trang đang chạy), /xuhuong (chủ đề nóng hôm nay), /baocao (việc hôm nay).
Gửi ảnh: trả lời (reply) tin “Cần ảnh cho bài #…” bằng ảnh; gửi ảnh không trả lời thì gắn vào bài chờ ảnh lâu nhất.
"""
import random
import threading
import time

import httpx

import db
from telegram_bot import API, TOKEN_RX, e, mask_token, verify_token  # noqa: F401  (dùng chung kiểm tra token, định dạng)

_state = {"started": False, "bot": None, "error": None}
_buf: list[str] = []
_lock = threading.Lock()
HELP = ("Bot riêng của <b>Nhi</b> (mọi Trang Facebook): sếp điều khiển Nhi hoàn toàn ở đây.\n"
        "• Bài chờ duyệt: bấm ✅ Duyệt / ❌ Loại, hoặc trả lời tin bài bằng bản sửa.\n"
        "• Ảnh: trả lời (reply) tin xin ảnh bằng ảnh. Không kịp thì tới giờ Nhi đăng chữ.\n"
        "• /anh: bài chờ ảnh · /trang: các Trang · /xuhuong: chủ đề nóng · /baocao: việc hôm nay\n\n")


def token() -> str:
    return (db.get_settings().get("tg2_token") or "").strip()


def chats() -> list[str]:
    return [c for c in (db.get_settings().get("tg2_chat_ids") or "").split(",") if c]


def configured() -> bool:
    return bool(token() and chats())


def call(method: str, timeout: float = 20, **params):
    t = token()
    if not t:
        raise RuntimeError("Chưa có token bot ảnh")
    r = httpx.post(f"{API}/bot{t}/{method}", json=params, timeout=timeout)
    data = r.json()
    if not data.get("ok"):
        raise RuntimeError(data.get("description") or f"Telegram lỗi {r.status_code}")
    return data["result"]


def file_bytes(file_id: str) -> bytes:
    info = call("getFile", file_id=file_id)
    return httpx.get(f"{API}/file/bot{token()}/{info['file_path']}", timeout=60).content


def send(text: str, chat_ids=None, buttons=None) -> list:
    out = []
    for c in chat_ids or chats():
        try:
            params = {"chat_id": c, "text": text[:4000], "parse_mode": "HTML", "disable_web_page_preview": True}
            if buttons:
                params["reply_markup"] = {"inline_keyboard": buttons}
            out.append(call("sendMessage", **params))
        except Exception as ex:
            _state["error"] = str(ex)[:200]
            import errors
            errors.report("telegram", "Bot ảnh Telegram không gửi được tin", str(ex)[:300], screen="trends")
    return out


def status() -> dict:
    t, s = token(), db.get_settings()
    if t and not _state["bot"]:
        try:
            _state["bot"] = call("getMe", timeout=8)
            _state["error"] = None
        except Exception as ex:
            _state["error"] = str(ex)[:200]
    return {"has_token": bool(t), "token_masked": mask_token(t) if t else "", "bot": (_state["bot"] or {}).get("username") if t else None,
            "chats": len(chats()), "pair_code": s.get("tg2_pair_code") or "", "error": _state["error"] if t else None,
            "report": s.get("tg2_report", "1") == "1"}


def save_token(t: str) -> dict:
    t = (t or "").strip()
    if t and t.split(":")[0] == (db.get_settings().get("tg_token") or "").split(":")[0]:
        raise ValueError("Đây là token của bot chính. Tạo một bot khác ở @BotFather (/newbot) cho phần ảnh")
    bot = verify_token(t)
    if token().split(":")[0] != t.split(":")[0]:
        db.set_setting("tg2_chat_ids", "")  # bot khác: ghép nối lại
        db.set_setting("tg2_offset", "0")
    db.set_setting("tg2_token", t)
    _state.update(bot=bot, error=None)
    return bot


def clear():
    for k in ("tg2_token", "tg2_chat_ids", "tg2_pair_code"):
        db.set_setting(k, "")
    _state.update(bot=None, error=None)


def new_pair_code() -> str:
    code = f"{random.randint(0, 999999):06d}"
    db.set_setting("tg2_pair_code", code)
    return code


# ---------------------------------------------------------------- báo việc của Nhi
def on_log(agent_id: str, action: str, detail: str):
    """Việc của Nhi gom lại gửi qua bot ảnh (mỗi ~45 giây một tin)."""
    if agent_id != "nhi" or not configured() or db.get_settings().get("tg2_report", "1") != "1":
        return
    if action in ("Nhận ảnh từ sếp",):  # sếp vừa gửi ảnh, bot đã trả lời ngay
        return
    with _lock:
        _buf.append(f"• <b>{e(action)}</b>: {e((detail or '')[:300])}")


def flush() -> int:
    with _lock:
        items = _buf[:20]
        del _buf[:20]
    if items:
        send(f"🧾 <b>Nhi báo việc</b> · {db.clock().strftime('%H:%M')}\n" + "\n".join(items))
    return len(items)


def posted(post: dict, url: str = ""):
    """Bài Trang xu hướng vừa đăng xong (gọi từ workflows.mark_posted)."""
    if not post or not post.get("fb_page_ref"):
        return
    pg = db.one("SELECT name FROM fb_pages WHERE id=?", (post["fb_page_ref"],)) or {}
    with _lock:
        _buf.append(f"📣 <b>Đã đăng lên Trang {e(pg.get('name') or '')}</b>: bài #{post['id']}" + (f" · {e(url)}" if url else ""))


def report_text() -> str:
    today = db.today()
    rows = db.q("""SELECT f.name, SUM(p.status='posted' AND substr(p.posted_at,1,10)=?) posted, SUM(p.status='need_image') waiting,
                          SUM(p.status='scheduled') ready, f.followers FROM fb_pages f LEFT JOIN posts p ON p.fb_page_ref=f.id
                   WHERE f.status='active' GROUP BY f.id ORDER BY f.name""", (today,))
    ideas = db.one("SELECT COUNT(*) n FROM fb_pages WHERE status='idea'")["n"]
    lines = [f"📊 <b>Trang xu hướng · {today[8:10]}/{today[5:7]}</b>"]
    for r in rows:
        lines.append(f"• <b>{e(r['name'])}</b>: đăng {r['posted'] or 0} · chờ ảnh {r['waiting'] or 0} · chờ giờ đăng {r['ready'] or 0}"
                     + (f" · {r['followers']:,} người theo dõi".replace(",", ".") if r.get("followers") else ""))
    if not rows:
        lines.append("Chưa có Trang nào đang chạy.")
    if ideas:
        lines.append(f"💡 {ideas} ý tưởng Trang mới đang chờ sếp xem (mục Trang xu hướng).")
    return "\n".join(lines)


def waiting_text() -> str:
    rows = db.q("""SELECT p.id, p.scheduled_for, f.name FROM posts p JOIN fb_pages f ON f.id=p.fb_page_ref WHERE p.status='need_image'
                   ORDER BY p.scheduled_for LIMIT 15""")
    if not rows:
        return "Không có bài nào chờ ảnh 👍"
    return "🖼 <b>Bài đang chờ ảnh</b>\n" + "\n".join(f"• #{r['id']} · {e(r['name'])} · đăng {(r['scheduled_for'] or '')[11:16]}" for r in rows) + \
        "\nEm gửi lại prompt từng bài ngay dưới đây."


# ---------------------------------------------------------------- nhận tin
def _reply(chat_id, text):
    send(text, chat_ids=[chat_id])


def handle_message(msg: dict):
    chat_id = str(msg["chat"]["id"])
    text = (msg.get("text") or "").strip()
    if chat_id not in chats():
        code = db.get_settings().get("tg2_pair_code") or ""
        if code and code in text.replace(" ", ""):
            db.set_setting("tg2_chat_ids", ",".join(chats() + [chat_id]))
            db.set_setting("tg2_pair_code", "")
            db.log("nhi", "Kết nối bot ảnh", f"Đã ghép nối bot ảnh với {msg.get('from', {}).get('first_name') or chat_id}")
            import nhi_tg
            _reply(chat_id, "✅ Đã kết nối bot của Nhi.\n\n" + HELP + nhi_tg.HELP)
        else:
            _reply(chat_id, "Xin chào! Gửi <b>mã ghép nối 6 số</b> hiển thị ở mục Trang xu hướng của phần mềm để kết nối.")
        return
    import trend_pages
    if msg.get("photo") or (msg.get("document") or {}).get("mime_type", "").startswith("image/"):
        try:
            r = trend_pages.on_telegram_photo(msg, getter=file_bytes)
        except Exception as ex:
            r = f"Chưa lấy được ảnh: {ex}"
        _reply(chat_id, e(r or "Không đọc được ảnh"))
        return
    import nhi_tg
    r = nhi_tg.on_reply(msg)
    if r:
        _reply(chat_id, r)
        return
    cmd = text.split()[0].lower().split("@")[0] if text.startswith("/") else ""
    if text and not cmd:
        _reply(chat_id, nhi_tg.handle_text(text))
        return
    if cmd == "/anh":
        _reply(chat_id, waiting_text())
        for r in db.q("SELECT id FROM posts WHERE status='need_image' ORDER BY scheduled_for LIMIT 5"):
            trend_pages.ask_image(r["id"])
    elif cmd == "/trang":
        _reply(chat_id, nhi_tg.report())
    elif cmd == "/baocao":
        _reply(chat_id, report_text())
    elif cmd == "/xuhuong":
        hot = db.q("SELECT title, score, niche FROM trend_hot WHERE day=(SELECT MAX(day) FROM trend_hot) ORDER BY score DESC LIMIT 10")
        _reply(chat_id, ("🔥 <b>Chủ đề Nhi chọn</b>\n" + "\n".join(f"• {e(h['title'])} ({h['score']}) · {e(h['niche'] or '')}" for h in hot))
               if hot else "Nhi chưa đọc xu hướng hôm nay.")
    else:
        _reply(chat_id, HELP + nhi_tg.HELP)


def tick(now):
    """21:45: báo cáo cuối ngày của các Trang xu hướng (mỗi ngày một lần)."""
    s = db.get_settings()
    if configured() and s.get("tg2_report", "1") == "1" and now.strftime("%H:%M") >= "21:45" and s.get("tg2_evening") != db.today():
        db.set_setting("tg2_evening", db.today())
        send(report_text())


def _poll():
    while True:
        t = token()
        if not t:
            time.sleep(5)
            continue
        offset = int(db.get_settings().get("tg2_offset") or 0)
        try:
            ups = httpx.post(f"{API}/bot{t}/getUpdates", json={"offset": offset, "timeout": 25, "allowed_updates": ["message", "callback_query"]}, timeout=40).json()
            if not ups.get("ok"):
                _state["error"] = ups.get("description")
                time.sleep(10)
                continue
            _state["error"] = None
            for u in ups["result"]:
                db.set_setting("tg2_offset", str(u["update_id"] + 1))
                if "callback_query" in u:
                    try:
                        cb = u["callback_query"]
                        if str(cb.get("message", {}).get("chat", {}).get("id")) in chats():
                            import nhi_tg
                            nhi_tg.on_callback(cb, call)
                    except Exception as ex:
                        import errors
                        errors.report_exc("telegram", "Bot của Nhi xử lý nút bấm bị lỗi", ex, screen="nhipages")
                if "message" in u:
                    try:
                        handle_message(u["message"])
                    except Exception as ex:
                        import errors
                        errors.report_exc("telegram", "Bot ảnh Telegram xử lý tin bị lỗi", ex, screen="trends")
        except Exception as ex:
            _state["error"] = str(ex)[:200]
            time.sleep(8)


def _flush_loop():
    while True:
        time.sleep(45)
        try:
            flush()
        except Exception as ex:
            print("[bot ảnh] báo việc lỗi:", ex)


db.LOG_HOOKS.append(on_log)


def start():
    if not _state["started"]:
        _state["started"] = True
        threading.Thread(target=_poll, daemon=True).start()
        threading.Thread(target=_flush_loop, daemon=True).start()

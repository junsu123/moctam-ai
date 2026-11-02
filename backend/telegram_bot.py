"""Telegram: báo cáo công việc cho sếp, chuyển khách cần sếp tư vấn, nhận lệnh.

Cài đặt (1 lần):
1. Trên Telegram, chat với @BotFather → /newbot → đặt tên → nhận token.
2. Dán token vào trang KPI & Báo cáo → bấm "Tạo mã ghép nối".
3. Mở bot vừa tạo, gửi mã 6 số đó. Từ giờ chỉ những chat đã ghép nối mới nhận báo cáo và ra lệnh được.

Bot dùng long polling (không cần IP/tên miền công khai), chạy ngay trên máy của sếp.
"""
import html
import json
import os
import random
import threading
import time
from datetime import datetime, timedelta

import httpx

import db

API = os.getenv("TELEGRAM_API", "https://api.telegram.org").rstrip("/")
_state = {"bot": None, "error": None, "started": False}
HELP = ("Các lệnh:\n/baocao — báo cáo hôm nay\n/kpi — tiến độ KPI\n/khach — khách đang chờ sếp tư vấn\n"
        "/hop [chủ đề] — triệu tập họp\n/tamdung — tạm dừng mọi nick tự đăng\n/tieptuc — bật lại tự đăng\n/help — xem lệnh")


def token() -> str:
    return (db.get_settings().get("tg_token") or "").strip()


def chats() -> list[str]:
    return [c for c in (db.get_settings().get("tg_chat_ids") or "").split(",") if c.strip()]


def configured() -> bool:
    return bool(token() and chats())


def call(method: str, timeout: float = 20, **params):
    t = token()
    if not t:
        raise RuntimeError("Chưa có token bot Telegram")
    r = httpx.post(f"{API}/bot{t}/{method}", json=params, timeout=timeout)
    data = r.json()
    if not data.get("ok"):
        raise RuntimeError(data.get("description") or f"Telegram lỗi {r.status_code}")
    return data["result"]


def e(x) -> str:
    return html.escape(str(x if x is not None else ""))


def send(text: str, buttons=None, chat_ids=None) -> list:
    out = []
    for c in chat_ids or chats():
        try:
            params = {"chat_id": c, "text": text[:4000], "parse_mode": "HTML", "disable_web_page_preview": True}
            if buttons:
                params["reply_markup"] = {"inline_keyboard": buttons}
            out.append(call("sendMessage", **params))
        except Exception as ex:
            _state["error"] = str(ex)
            print("[telegram] gửi lỗi:", ex)
    return out


def status() -> dict:
    t = token()
    if t and not _state["bot"]:
        try:
            _state["bot"] = call("getMe", timeout=8)
            _state["error"] = None
        except Exception as ex:
            _state["error"] = str(ex)
    s = db.get_settings()
    return {"has_token": bool(t), "bot": (_state["bot"] or {}).get("username") if t else None, "chats": len(chats()),
            "pair_code": s.get("tg_pair_code") or "", "error": _state["error"] if t else None}


def new_pair_code() -> str:
    code = f"{random.randint(0, 999999):06d}"
    db.set_setting("tg_pair_code", code)
    return code


def reset_token():
    _state["bot"] = None
    _state["error"] = None


# ---------------------------------------------------------------- nội dung báo cáo
def _bar(v: int, target: int, width: int = 10) -> str:
    n = min(width, round(width * v / max(1, target)))
    return "▰" * n + "▱" * (width - n)


def kpi_text() -> str:
    import kpi
    st = kpi.day_stats()
    pc = kpi.pace(st)
    head = "🎯 <b>KPI hôm nay</b>: {} / {} khách có SĐT (vượt: {})".format(st["leads_phone"], st["target_min"], st["target_max"])
    status_line = ("🏆 Đã VƯỢT mục tiêu" if st["exceeded"] else "✅ Đã đạt KPI tối thiểu" if st["achieved"]
                   else ("⚠️ Đang chậm tiến độ (lúc này nên có ~{})".format(pc["expected"]) if pc["behind"] else "⏳ Đang đúng tiến độ"))
    lines = [head, _bar(st["leads_phone"], st["target_min"]) + f" {st['pct']}%", status_line, ""]
    lines.append(f"• Khách mới: {st['leads_total']} (từ bình luận {st['from_comments']}, chưa có SĐT {st['leads_no_phone']})")
    lines.append(f"• Đã trả lời xin SĐT: {st['asked_phone']} người")
    lines.append(f"• Bài đã đăng: {st['posts']} · Lượt up bài: {st['bumps']}")
    lines.append(f"• Chuyển sếp hôm nay: {st['escalated']} · Đang chờ sếp: {st['boss_pending']}")
    sales = kpi.per_sale()
    if sales:
        lines.append("\n<b>Theo từng nick</b>")
        for s in sales:
            mark = "✅" if s["active"] and s["leads_phone"] >= s["target_min"] else ("⏸" if not s["active"] else "▫️")
            lines.append(f"{mark} {e(s['name'])}: {s['leads_phone']}/{s['target_min']} SĐT · {s['posts']} bài · {s['bumps']} up"
                         + (f" · ⚠️ {s['failed']} lỗi" if s["failed"] else ""))
    return "\n".join(lines)


def morning_text() -> str:
    import kpi
    y = (datetime.now() - timedelta(days=1)).strftime("%Y-%m-%d")
    ys = kpi.day_stats(y)
    lines = [f"☀️ <b>Chào sếp, kế hoạch {datetime.now().strftime('%d/%m')}</b>",
             f"Hôm qua: {ys['leads_phone']}/{ys['target_min']} khách có SĐT {'✅' if ys['achieved'] else '❌'} · chuỗi đạt KPI: {kpi.streak()} ngày",
             f"Hôm nay cần: tối thiểu <b>{kpi.targets()[0]}</b>, phấn đấu <b>{kpi.targets()[1]}</b> khách để lại SĐT."]
    sched = db.one("SELECT COUNT(*) n FROM posts WHERE status='scheduled' AND scheduled_for LIKE ?", (db.today() + "%",))["n"]
    lines.append(f"• Lịch đăng hôm nay: {sched} bài · Quét bình luận lúc {db.get_settings().get('scan_times')}")
    m = db.one("SELECT * FROM meetings WHERE date=? AND status='done' ORDER BY id DESC LIMIT 1", (db.today(),))
    if m:
        lines.append(f"\n🗣 <b>Họp sáng</b>: {e(m['topic'])}\n{e((m['summary'] or '')[:500])}")
        items = json.loads(m["action_items"] or "[]")
        if items:
            import agents
            lines += [f"  – {e(agents.name_of(i['agent_id']))}: {e(i['title'])}" for i in items]
    bad = db.q("SELECT name FROM sales WHERE login_status!='ok'")
    if bad:
        lines.append("\n⚠️ Nick cần sếp xử lý: " + ", ".join(e(b["name"]) for b in bad))
    return "\n".join(lines)


def evening_text() -> str:
    import kpi
    import llm
    st = kpi.snapshot()
    lines = [f"🌙 <b>Báo cáo cuối ngày {datetime.now().strftime('%d/%m')}</b>", kpi_text()]
    pend = db.q("""SELECT name, phone FROM leads WHERE escalated_at IS NOT NULL AND COALESCE(boss_status,'') IN ('','remind')
                   AND status NOT IN ('ordered','lost') ORDER BY escalated_at LIMIT 8""")
    if pend:
        lines.append("\n📞 <b>Khách còn chờ sếp gọi</b>")
        lines += [f"• {e(p['name'])} — {e(kpi.fmt_phone(p['phone']) or 'chưa có SĐT')}" for p in pend]
    won = db.one("SELECT COUNT(*) n FROM leads WHERE status='ordered' AND updated_at LIKE ?", (db.today() + "%",))["n"]
    if won:
        lines.append(f"\n🎉 Chốt đơn hôm nay: {won}")
    les = db.q("SELECT agent_id, text FROM lessons WHERE created_at LIKE ? ORDER BY id DESC LIMIT 3", (db.today() + "%",))
    if les:
        import agents
        lines.append("\n📚 <b>Bài học mới</b>")
        lines += [f"• {e(agents.name_of(l['agent_id']))}: {e(l['text'][:160])}" for l in les]
    cost = db.one("SELECT COALESCE(SUM(cost_usd),0) c FROM usage WHERE created_at LIKE ?", (db.today() + "%",))["c"]
    lines.append(f"\n💵 Chi phí AI hôm nay: ${cost:.3f} · tháng này: ${llm.month_spent():.2f}")
    if not st["achieved"]:
        lines.append("\nNgày mai trong cuộc họp sáng, cả đội sẽ bàn cách đạt KPI.")
    return "\n".join(lines)


def lead_text(l: dict, reminder: bool = False) -> str:
    import kpi
    post = db.one("""SELECT p.id, p.posted_url, p.permalink_status, g.name gname, s.name sname FROM posts p
                     LEFT JOIN groups g ON g.id=p.group_id LEFT JOIN sales s ON s.id=p.sale_id WHERE p.id=?""",
                  (l.get("post_id"),)) if l.get("post_id") else None
    src = e(l.get("source") or "")
    if post:
        where = e(post["gname"] or "Trang cá nhân")
        src = (f'<a href="{e(post["posted_url"])}">Bài #{post["id"]} · {where}</a>' if post["permalink_status"] == "found"
               else f"Bài #{post['id']} · {where}") + (f" · nick {e(post['sname'])}" if post["sname"] else "")
    title = "⏰ <b>Nhắc lại: khách chờ sếp tư vấn</b>" if reminder else "🔔 <b>Khách cần sếp tư vấn</b>"
    return "\n".join([
        title,
        f"👤 <b>{e(l['name'])}</b> · điểm {l.get('score') or 0}",
        f"📞 <b>{e(kpi.fmt_phone(l.get('phone'))) or 'Chưa có SĐT'}</b>" + (f" · {e(l['contact'])}" if l.get("contact") and not l.get("phone") else ""),
        f"💬 {e((l.get('need') or '')[:300])}",
        f"📍 {src}",
        f"❓ {e(l.get('escalate_reason') or '')}",
        "",
        f"<b>Hà gợi ý kịch bản:</b>\n{e((l.get('consult_note') or '')[:700])}",
    ])


def lead_buttons(lid: int):
    return [[{"text": "📞 Đã gọi", "callback_data": f"l:{lid}:called"}, {"text": "✅ Chốt đơn", "callback_data": f"l:{lid}:won"}],
            [{"text": "❌ Không mua", "callback_data": f"l:{lid}:lost"}, {"text": "⏰ Nhắc sau 2 giờ", "callback_data": f"l:{lid}:remind"}]]


# ---------------------------------------------------------------- gửi
def send_lead(lead_id: int, reminder: bool = False):
    if not configured() or db.get_settings().get("tg_alert_leads") != "1":
        return
    l = db.one("SELECT * FROM leads WHERE id=?", (lead_id,))
    if l:
        send(lead_text(l, reminder), lead_buttons(lead_id))


def alert_nick(sale_id: int, reason: str):
    if not configured() or db.get_settings().get("tg_alert_nick") != "1":
        return
    s = db.one("SELECT name, fb_name FROM sales WHERE id=?", (sale_id,))
    send(f"🚨 <b>Nick {e((s or {}).get('fb_name') or (s or {}).get('name'))} gặp sự cố</b>\n{e(reason)}\n"
         "Sale đã dừng nick này và trả bài về hàng đợi. Sếp mở phần mềm → Nhân viên sale → Mở Chrome để xử lý.")


def _sent(key: str) -> bool:
    log = json.loads(db.get_settings().get("tg_sent_log") or "{}")
    return log.get(key) == db.today()


def _mark(key: str):
    log = json.loads(db.get_settings().get("tg_sent_log") or "{}")
    log[key] = db.today()
    db.set_setting("tg_sent_log", json.dumps(log))


def tick():
    """Gọi mỗi 30 giây từ lịch tự động: báo cáo sáng/tối, kiểm tra KPI giữa ngày, chúc mừng đạt KPI."""
    import kpi
    s = db.get_settings()
    hm = datetime.now().strftime("%H:%M")
    st = None
    if s.get("tg_alert_kpi") == "1":
        st = kpi.day_stats()
        if hm >= (s.get("kpi_check_time") or "15:00") and not _sent("kpi_check"):
            _mark("kpi_check")
            if kpi.pace(st)["behind"] and not st["achieved"]:
                start_scan_round()
                if configured():
                    send(f"⚠️ <b>KPI đang chậm</b>: mới {st['leads_phone']}/{st['target_min']} khách có SĐT lúc {hm}.\n"
                         "Đội đã quét lại bình luận ngay và sẽ ưu tiên up các bài nhiều bình luận.")
        if st["achieved"] and not _sent("kpi_hit") and configured():
            _mark("kpi_hit")
            send(f"🎉 <b>Đạt KPI hôm nay!</b> {st['leads_phone']}/{st['target_min']} khách có SĐT. Mục tiêu vượt: {st['target_max']}.")
        if st["exceeded"] and not _sent("kpi_max") and configured():
            _mark("kpi_max")
            send(f"🏆 <b>Vượt KPI!</b> {st['leads_phone']} khách có SĐT, vượt mức {st['target_max']}.")
    if not configured():
        return
    if hm >= (s.get("tg_morning") or "09:00") and not _sent("morning"):
        _mark("morning")
        send(morning_text())
    if hm >= (s.get("tg_evening") or "21:30") and not _sent("evening"):
        _mark("evening")
        send(evening_text())


def start_scan_round(force: bool = True) -> int:
    """Giao cho mỗi nick quét bình luận các bài gần đây của mình."""
    import browser_poster
    s = db.get_settings()
    if s.get("scan_enabled") != "1" and not force:
        return 0
    cutoff = (datetime.now() - timedelta(days=int(s.get("scan_max_age_days") or 7))).strftime("%Y-%m-%d %H:%M:%S")
    n = 0
    for sale in db.q("SELECT * FROM sales WHERE login_status='ok' AND auto_post=1"):
        ids = [r["id"] for r in db.q("""SELECT id FROM posts WHERE sale_id=? AND status='posted' AND permalink_status='found'
                                         AND posted_at >= ? ORDER BY COALESCE(last_scan_at,'') ASC, posted_at DESC LIMIT 8""",
                                      (sale["id"], cutoff))]
        if ids:
            browser_poster.submit(sale["id"], {"kind": "scan", "post_ids": ids})
            n += len(ids)
    if n:
        db.log("tuan", "Quét bình luận", f"Giao các nick đọc bình luận {n} bài để tìm khách và xin SĐT")
    return n


# ---------------------------------------------------------------- nhận lệnh
def _reply(chat_id, text, buttons=None):
    send(text, buttons, [str(chat_id)])


def handle_message(msg: dict):
    chat_id = str(msg["chat"]["id"])
    text = (msg.get("text") or "").strip()
    s = db.get_settings()
    if chat_id not in chats():
        code = s.get("tg_pair_code") or ""
        if code and code in text.replace(" ", ""):
            ids = chats() + [chat_id]
            db.set_setting("tg_chat_ids", ",".join(ids))
            db.set_setting("tg_pair_code", "")
            name = msg.get("from", {}).get("first_name", "")
            db.log("minh", "Kết nối Telegram", f"Đã ghép nối với {name or chat_id}")
            _reply(chat_id, f"✅ Đã kết nối với phòng kinh doanh AI của <b>{e(s.get('company_name'))}</b>.\n"
                            f"Sếp sẽ nhận báo cáo lúc {s.get('tg_morning')} và {s.get('tg_evening')}, khách cần tư vấn, cảnh báo nick.\n\n" + HELP)
        else:
            _reply(chat_id, "Xin chào! Để nhận báo cáo, hãy gửi <b>mã ghép nối 6 số</b> hiển thị trong phần mềm (trang KPI & Báo cáo).")
        return
    cmd = text.split()[0].split("@")[0].lower() if text else ""
    arg = text[len(text.split()[0]):].strip() if text else ""
    if cmd in ("/start", "/help", "help", "lệnh"):
        _reply(chat_id, HELP)
    elif cmd in ("/baocao", "báo cáo", "baocao"):
        _reply(chat_id, evening_text().replace("Báo cáo cuối ngày", "Báo cáo nhanh"))
    elif cmd in ("/kpi", "kpi"):
        _reply(chat_id, kpi_text())
    elif cmd in ("/khach", "khách"):
        rows = db.q("""SELECT * FROM leads WHERE escalated_at IS NOT NULL AND COALESCE(boss_status,'') IN ('','remind')
                       AND status NOT IN ('ordered','lost') ORDER BY escalated_at LIMIT 5""")
        if not rows:
            _reply(chat_id, "Không có khách nào đang chờ sếp tư vấn. 👍")
        for l in rows:
            _reply(chat_id, lead_text(l), lead_buttons(l["id"]))
    elif cmd in ("/hop", "họp"):
        import meeting
        mid = meeting.start(arg)
        _reply(chat_id, f"🗣 Đã triệu tập họp #{mid}{(': ' + e(arg)) if arg else ''}. Kết luận sẽ gửi khi họp xong.")
        threading.Thread(target=_send_meeting_when_done, args=(mid, chat_id), daemon=True).start()
    elif cmd in ("/tamdung", "tạm dừng"):
        db.run("UPDATE sales SET auto_post=0")
        db.run("UPDATE posts SET status='approved', sale_id=NULL, scheduled_for=NULL WHERE status='scheduled' AND sale_id IS NOT NULL")
        db.log("minh", "Tạm dừng", "Sếp tạm dừng mọi nick qua Telegram")
        _reply(chat_id, "⏸ Đã tạm dừng tất cả nick tự đăng và up bài. Gửi /tieptuc để bật lại.")
    elif cmd in ("/tieptuc", "tiếp tục"):
        db.run("UPDATE sales SET auto_post=1 WHERE login_status='ok'")
        db.log("minh", "Tiếp tục", "Sếp bật lại tự đăng qua Telegram")
        _reply(chat_id, "▶️ Đã bật lại tự đăng cho các nick đang đăng nhập bình thường.")
    else:
        _reply(chat_id, "Em chưa hiểu lệnh này ạ.\n\n" + HELP)


def _send_meeting_when_done(mid: int, chat_id: str):
    for _ in range(120):
        time.sleep(5)
        m = db.one("SELECT * FROM meetings WHERE id=?", (mid,))
        if m and m["status"] == "done":
            items = json.loads(m["action_items"] or "[]")
            import agents
            _reply(chat_id, f"✅ <b>Họp xong</b>: {e(m['topic'])}\n{e(m['summary'] or '')}\n"
                   + "\n".join(f"– {e(agents.name_of(i['agent_id']))}: {e(i['title'])}" for i in items))
            return


def handle_callback(cb: dict):
    import learning
    chat_id = str(cb["message"]["chat"]["id"])
    if chat_id not in chats():
        return
    try:
        _, lid, act = cb["data"].split(":")
        lid = int(lid)
    except Exception:
        return
    lead = db.one("SELECT * FROM leads WHERE id=?", (lid,))
    if not lead:
        call("answerCallbackQuery", callback_query_id=cb["id"], text="Không tìm thấy khách")
        return
    hm = datetime.now().strftime("%H:%M %d/%m")
    if act == "called":
        db.run("UPDATE leads SET boss_status='called', status=CASE WHEN status='new' THEN 'contacted' ELSE status END, last_contact_at=?, updated_at=? WHERE id=?",
               (db.now(), db.now(), lid))
        note, toast = f"📞 Sếp đã gọi lúc {hm}", "Đã ghi nhận"
    elif act == "won":
        db.run("UPDATE leads SET boss_status='won', status='ordered', updated_at=? WHERE id=?", (db.now(), lid))
        learning.on_lead_status(lid, "ordered")
        note, toast = f"✅ Chốt đơn lúc {hm}", "Tuyệt vời! Đã ghi chốt đơn"
    elif act == "lost":
        db.run("UPDATE leads SET boss_status='lost', status='lost', updated_at=? WHERE id=?", (db.now(), lid))
        learning.on_lead_status(lid, "lost")
        note, toast = f"❌ Khách không mua ({hm})", "Đã ghi nhận"
    elif act == "remind":
        at = (datetime.now() + timedelta(hours=2)).strftime("%Y-%m-%d %H:%M:%S")
        db.run("UPDATE leads SET boss_status='remind', remind_at=? WHERE id=?", (at, lid))
        note, toast = f"⏰ Sẽ nhắc lại lúc {at[11:16]}", "Em sẽ nhắc sau 2 giờ"
    else:
        return
    db.log("minh", "Sếp xử lý khách", f"{lead['name']}: {note}")
    call("answerCallbackQuery", callback_query_id=cb["id"], text=toast)
    try:
        old = cb["message"].get("text") or ""
        keep = act == "called"  # đã gọi: vẫn giữ nút để ghi kết quả chốt/không mua
        params = {"chat_id": chat_id, "message_id": cb["message"]["message_id"],
                  "text": e(old)[:3500] + f"\n\n<b>{e(note)}</b>", "parse_mode": "HTML", "disable_web_page_preview": True}
        if keep:
            params["reply_markup"] = {"inline_keyboard": [lead_buttons(lid)[0][1:] + lead_buttons(lid)[1][:1]]}
        call("editMessageText", **params)
    except Exception as ex:
        print("[telegram] sửa tin lỗi:", ex)


def _poll():
    offset = int(db.get_settings().get("tg_offset") or 0)
    while True:
        if not token():
            time.sleep(5)
            continue
        try:
            ups = httpx.post(f"{API}/bot{token()}/getUpdates", json={"offset": offset, "timeout": 25,
                             "allowed_updates": ["message", "callback_query"]}, timeout=40).json()
            if not ups.get("ok"):
                _state["error"] = ups.get("description")
                time.sleep(10)
                continue
            _state["error"] = None
            for u in ups["result"]:
                offset = u["update_id"] + 1
                db.set_setting("tg_offset", str(offset))
                try:
                    if "message" in u:
                        handle_message(u["message"])
                    elif "callback_query" in u:
                        handle_callback(u["callback_query"])
                except Exception as ex:
                    print("[telegram] xử lý lỗi:", ex)
        except Exception as ex:
            _state["error"] = str(ex)[:200]
            time.sleep(8)


def start():
    if not _state["started"]:
        _state["started"] = True
        threading.Thread(target=_poll, daemon=True).start()

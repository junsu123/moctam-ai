"""Tin nhắn Fanpage (Messenger) qua Graph API: kênh tự động Facebook cho phép.

Mỗi 10 phút đọc các cuộc trò chuyện mới của Trang. Khách nhắn mà Trang chưa trả lời: khách vào mục Khách hàng (kênh
"Tin nhắn Fanpage", có SĐT thì tính KPI), Hà soạn câu trả lời (xin SĐT / Zalo, không báo giá), sếp duyệt rồi phần mềm gửi.
Luật Messenger: Trang chỉ được trả lời trong 24 giờ kể từ tin cuối của khách (messaging_type RESPONSE); quá hạn thì không gửi,
sếp trả lời bằng tay trong Hộp thư Trang. Trang đã trả lời (sếp tự trả lời trên Facebook) thì thôi.
Token Trang cần quyền pages_messaging (đọc và gửi tin nhắn) ngoài pages_read_engagement.
"""
import threading
from datetime import datetime, timedelta

import db

WINDOW_H = 24
_lock = threading.Lock()


def _s() -> dict:
    return db.get_settings()


def _ts(t: str | None) -> str:
    """Giờ Graph API (2026-11-18T08:01:02+0000) → giờ phần mềm (giờ Việt Nam) dạng YYYY-MM-DD HH:MM:SS."""
    if not t:
        return ""
    try:
        d = datetime.strptime(t[:19] + (t[19:].replace(":", "") or "+0000"), "%Y-%m-%dT%H:%M:%S%z")
    except ValueError:
        return t[:19].replace("T", " ")
    from datetime import timezone
    off = db.clock() - datetime.now(timezone.utc).replace(tzinfo=None)
    return (d.replace(tzinfo=None) - d.utcoffset() + timedelta(minutes=round(off.total_seconds() / 60))).strftime("%Y-%m-%d %H:%M:%S")


def _graph_get(path: str, params: dict) -> dict:
    import httpx
    import facebook
    r = httpx.get(f"{facebook.GRAPH}/{path}", params={**params, "access_token": _s()["fb_page_token"]}, timeout=30)
    d = r.json()
    if "error" in d:
        raise RuntimeError(d["error"].get("message", "Graph API lỗi"))
    return d


def _graph_send(psid: str, text: str) -> dict:
    import httpx
    import facebook
    st = _s()
    r = httpx.post(f"{facebook.GRAPH}/{st['fb_page_id']}/messages", params={"access_token": st["fb_page_token"]},
                   json={"recipient": {"id": psid}, "messaging_type": "RESPONSE", "message": {"text": text}}, timeout=30)
    d = r.json()
    if "error" in d:
        raise RuntimeError(d["error"].get("message", "Graph API lỗi"))
    return d


def fetch_conversations() -> list[dict]:
    st = _s()
    d = _graph_get(f"{st['fb_page_id']}/conversations", {"platform": "messenger", "limit": 25,
                   "fields": "participants,updated_time,messages.limit(10){message,from,created_time}"})
    return d.get("data") or []


def _hint(err: str) -> str:
    if "permission" in err.lower() or "(#10)" in err or "(#200)" in err or "(#230)" in err:
        return " Token Trang cần quyền pages_messaging (ứng dụng Meta phải được duyệt quyền này, hoặc sếp là quản trị viên ứng dụng)."
    return ""


def sync(fetch=None, draft=None) -> dict:
    """Đọc tin nhắn mới, tạo/cập nhật cuộc trò chuyện chờ trả lời và để Hà soạn câu trả lời."""
    import facebook
    if not facebook.configured():
        return {"ok": False, "why": "Chưa kết nối Fanpage (Cài đặt → Fanpage)"}
    if not _lock.acquire(blocking=False):
        return {"ok": False, "why": "Đang đọc tin nhắn rồi"}
    try:
        try:
            convs = (fetch or fetch_conversations)()
        except Exception as e:
            import errors
            errors.report("fanpage", "Không đọc được tin nhắn Fanpage", str(e)[:300] + _hint(str(e)), screen="leads")
            return {"ok": False, "why": str(e)[:200] + _hint(str(e))}
        page_id = _s().get("fb_page_id")
        new = answered = 0
        for c in convs:
            msgs = sorted(((c.get("messages") or {}).get("data") or []), key=lambda m: m.get("created_time") or "")
            mine = [m for m in msgs if (m.get("from") or {}).get("id") == page_id]
            theirs = [m for m in msgs if (m.get("from") or {}).get("id") != page_id and (m.get("message") or "").strip()]
            if not theirs:
                continue
            last = theirs[-1]
            who = last.get("from") or {}
            last_at, page_at = _ts(last.get("created_time")), _ts(mine[-1].get("created_time")) if mine else ""
            row = db.one("SELECT * FROM page_threads WHERE conv_id=?", (c["id"],))
            if page_at and page_at >= last_at:  # Trang đã trả lời sau tin cuối của khách
                if row and row["status"] == "waiting":
                    db.run("UPDATE page_threads SET status='answered', page_last_at=?, updated_at=? WHERE id=?", (page_at, db.now(), row["id"]))
                    answered += 1
                continue
            if row and row["last_at"] == last_at:
                continue  # không có tin mới
            text = "\n".join(m["message"].strip() for m in theirs if not page_at or _ts(m.get("created_time")) > page_at)[-1000:]
            name = who.get("name") or "Khách Fanpage"
            import kpi
            lid, _, _ = kpi.upsert_lead(name, text, None, f"fbmsg:{who.get('id')}", origin="messenger")
            reply = (draft or _draft)(lid, text)
            if row:
                db.run("""UPDATE page_threads SET name=?, last_text=?, last_at=?, page_last_at=?, lead_id=?, draft=?, status='waiting', error=NULL,
                          updated_at=? WHERE id=?""", (name, text, last_at, page_at or None, lid, reply, db.now(), row["id"]))
                tid = row["id"]
            else:
                tid = db.run("""INSERT INTO page_threads(conv_id, psid, name, last_text, last_at, page_last_at, lead_id, draft, status, created_at,
                                updated_at) VALUES (?,?,?,?,?,?,?,?, 'waiting', ?, ?)""",
                             (c["id"], who.get("id"), name, text, last_at, page_at or None, lid, reply, db.now(), db.now()))
            new += 1
            db.log("ha", "Tin nhắn Fanpage", f"{name} nhắn Trang: “{text[:80]}”. Hà đã soạn câu trả lời chờ sếp duyệt")
            if _s().get("page_inbox_auto") == "1":
                try:
                    send(tid)
                except ValueError as e:
                    db.run("UPDATE page_threads SET error=? WHERE id=?", (str(e)[:300], tid))
        expire()
        db.set_setting("page_inbox_last", db.now())
        return {"ok": True, "conversations": len(convs), "new": new, "answered": answered}
    finally:
        _lock.release()


def _draft(lead_id: int, text: str) -> str:
    import workflows
    r = workflows.draft_reply(lead_id, text)
    return (r or {}).get("reply") if isinstance(r, dict) else (r or "")


def left_hours(row: dict) -> float:
    try:
        last = datetime.strptime(row["last_at"][:19], "%Y-%m-%d %H:%M:%S")
    except (TypeError, ValueError):
        return 0
    return round(WINDOW_H - (db.clock() - last).total_seconds() / 3600, 1)


def expire() -> int:
    n = 0
    for r in db.q("SELECT * FROM page_threads WHERE status='waiting'"):
        if left_hours(r) <= 0:
            db.run("UPDATE page_threads SET status='expired', updated_at=? WHERE id=?", (db.now(), r["id"]))
            n += 1
    return n


def _get(tid: int) -> dict:
    r = db.one("SELECT * FROM page_threads WHERE id=?", (tid,))
    if not r:
        raise ValueError("Không tìm thấy cuộc trò chuyện này")
    return r


def send(tid: int, text: str | None = None, sender=None) -> dict:
    r = _get(tid)
    if r["status"] not in ("waiting",):
        raise ValueError("Cuộc trò chuyện này không còn chờ trả lời")
    if left_hours(r) <= 0:
        db.run("UPDATE page_threads SET status='expired', updated_at=? WHERE id=?", (db.now(), tid))
        raise ValueError("Đã quá 24 giờ từ tin cuối của khách: Facebook không cho Trang tự trả lời. Sếp trả lời bằng tay trong Hộp thư Trang")
    text = " ".join((text if text is not None else r["draft"] or "").split()).strip()
    if len(text) < 2:
        raise ValueError("Câu trả lời đang trống")
    import fb_policy
    import pricing
    text = pricing.sanitize(text)
    bad = [i for i in fb_policy.check_text(text) if i["level"] == "high"]
    if bad:
        raise ValueError("Câu trả lời vi phạm Luật Facebook: " + fb_policy.summary(bad))
    try:
        (sender or _graph_send)(r["psid"], text)
    except Exception as e:
        db.run("UPDATE page_threads SET error=?, updated_at=? WHERE id=?", (str(e)[:300], db.now(), tid))
        raise ValueError("Facebook không nhận tin: " + str(e)[:200] + _hint(str(e)))
    db.run("UPDATE page_threads SET status='sent', sent_text=?, sent_at=?, error=NULL, updated_at=? WHERE id=?",
           (text, db.now(), db.now(), tid))
    if r.get("lead_id"):
        db.run("UPDATE leads SET last_contact_at=?, status=CASE WHEN status='new' THEN 'contacted' ELSE status END WHERE id=?",
               (db.now(), r["lead_id"]))
        db.run("INSERT INTO replies(lead_id, text, created_at) VALUES (?,?,?)", (r["lead_id"], text, db.now()))
    db.log("ha", "Trả lời tin nhắn Fanpage", f"Gửi {r['name']}: “{text[:80]}”" + (" (sếp sửa câu)" if text != (r["draft"] or "") else ""))
    return _get(tid)


def skip(tid: int) -> dict:
    _get(tid)
    db.run("UPDATE page_threads SET status='skipped', updated_at=? WHERE id=?", (db.now(), tid))
    return _get(tid)


def redraft(tid: int) -> dict:
    r = _get(tid)
    if r["status"] != "waiting":
        raise ValueError("Cuộc trò chuyện này không còn chờ trả lời")
    db.run("UPDATE page_threads SET draft=?, updated_at=? WHERE id=?", (_draft(r["lead_id"], r["last_text"]), db.now(), tid))
    return _get(tid)


def overview() -> dict:
    import facebook
    expire()
    st = _s()
    rows = db.q("""SELECT t.*, l.phone FROM page_threads t LEFT JOIN leads l ON l.id=t.lead_id
                   ORDER BY CASE t.status WHEN 'waiting' THEN 0 ELSE 1 END, t.last_at DESC LIMIT 40""")
    for r in rows:
        r["left_h"] = left_hours(r) if r["status"] == "waiting" else None
    cnt = {k: 0 for k in ("waiting", "sent", "answered", "skipped", "expired")}
    for r in db.q("SELECT status, COUNT(*) n FROM page_threads WHERE updated_at >= ? GROUP BY status",
                  ((db.clock() - timedelta(days=7)).strftime("%Y-%m-%d"),)):
        cnt[r["status"]] = r["n"]
    return {"configured": facebook.configured(), "items": rows, "counts": cnt, "last_sync": st.get("page_inbox_last") or "",
            "settings": {k: st.get(k, "") for k in ("page_inbox_on", "page_inbox_minutes", "page_inbox_auto")}}


def tick(now: datetime):
    st = _s()
    if st.get("page_inbox_on", "1") != "1":
        return
    import facebook
    if not facebook.configured():
        return
    last = st.get("page_inbox_last") or ""
    every = max(5, int(st.get("page_inbox_minutes") or 10))
    if last and last > (now - timedelta(minutes=every)).strftime("%Y-%m-%d %H:%M:%S"):
        return
    db.set_setting("page_inbox_last", now.strftime("%Y-%m-%d %H:%M:%S"))  # đặt trước: lỗi mạng cũng không gọi dồn
    threading.Thread(target=sync, daemon=True).start()

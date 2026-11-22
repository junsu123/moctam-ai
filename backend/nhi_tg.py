"""Sếp điều khiển Nhi hoàn toàn qua Telegram.

- Bài chờ duyệt gửi lên kèm nút ✅ Duyệt / ❌ Loại (chọn lý do); trả lời (reply) tin bằng bản sửa = sếp sửa rồi duyệt (Nhi ghi nhớ).
- Nhắn lệnh bằng lời (bot riêng của Nhi: mọi tin; bot chính: tin bắt đầu bằng “Nhi”): thêm Trang, từ khóa, số bài, giờ đăng,
  tạm dừng / chạy lại, viết ngay, tạo Trang mới, dạy Nhi, bật / tắt duyệt... Có khóa Claude thì Nhi hiểu câu tự do, không thì theo mẫu câu.
- Nhi tự lo: Trang chưa có từ khóa thì tự đặt rồi báo; đủ hiểu ý sếp thì tự hỏi tắt duyệt; tới giờ đăng chưa có ảnh thì đăng chữ.
"""
import re

import db
from group_target import words
from knowledge import plain


def e(x) -> str:
    import html
    return html.escape(str(x if x is not None else ""))


def _bot():
    import telegram_img
    import telegram_bot
    if telegram_img.configured():
        return telegram_img
    if telegram_bot.configured():
        return telegram_bot
    return None


def send(text: str, buttons=None) -> list:
    b = _bot()
    if not b:
        return []
    try:
        return b.send(text, buttons=buttons)
    except Exception as ex:
        print("[nhi tg]", ex)
        return []


def send_photo(path: str, caption: str) -> str:
    """Gửi ảnh Nhi vừa làm lên Telegram; trả về mã tin (để sếp trả lời bằng ảnh khác là đổi)."""
    import httpx
    b = _bot()
    if not b or not path:
        return ""
    ids = []
    for c in b.chats():
        try:
            with open(path, "rb") as f:
                r = httpx.post(f"{getattr(b, 'API', 'https://api.telegram.org')}/bot{b.token()}/sendPhoto", data={"chat_id": c, "caption": caption[:1000], "parse_mode": "HTML"},
                               files={"photo": ("anh.jpg", f, "image/jpeg")}, timeout=60).json()
            if r.get("ok"):
                ids.append(str(r["result"]["message_id"]))
        except Exception as ex:
            print("[nhi ảnh tg]", ex)
    return ",".join(ids)


def _hm(t: str) -> str:
    return f"{t[11:16]} {t[8:10]}/{t[5:7]}" if t and len(t) >= 16 else ""


# ---------------------------------------------------------------- duyệt bài bằng nút
def review_buttons(pid: int) -> list:
    return [[{"text": "✅ Duyệt", "callback_data": f"nr:a:{pid}"}, {"text": "❌ Loại", "callback_data": f"nr:r:{pid}"}]]


def reason_buttons(pid: int) -> list:
    import page_brain
    rs = [{"text": r[:28], "callback_data": f"nr:x:{pid}:{i}"} for i, r in enumerate(page_brain.REASONS)]
    return [rs[i:i + 2] for i in range(0, len(rs), 2)] + [[{"text": "↩ Quay lại", "callback_data": f"nr:b:{pid}"}]]


def send_review(post_id: int) -> bool:
    p = db.one("SELECT p.*, f.name page_name FROM posts p LEFT JOIN fb_pages f ON f.id=p.fb_page_ref WHERE p.id=?", (post_id,))
    if not p or p["status"] != "page_review":
        return False
    head = f"📝 <b>Bài chờ duyệt #{p['id']}</b> · Trang <b>{e(p['page_name'])}</b>"
    if p.get("page_kw"):
        head += f" · từ khóa “{e(p['page_kw'])}”"
    if p.get("trend_kind") == "trend":
        head += f" · 🔥 {e(p.get('trend_topic'))}"
    msg = (f"{head} · đăng {_hm(p['scheduled_for'] or '')}\n\n{e((p['content'] or '')[:3000])}\n\n"
           "👉 Bấm <b>Duyệt</b> hoặc <b>Loại</b>. Muốn sửa: <b>trả lời (reply) tin này bằng bản sửa</b>, Nhi duyệt bản của sếp và ghi nhớ.")
    res = send(msg, review_buttons(post_id))
    ids = ",".join(str(r.get("message_id")) for r in res if isinstance(r, dict) and r.get("message_id"))
    if ids:
        db.run("UPDATE posts SET review_msg=? WHERE id=?", (ids, post_id))
    return bool(ids)


def pending_reviews(resend: bool = False) -> int:
    rows = db.q("SELECT id FROM posts WHERE status='page_review' ORDER BY scheduled_for LIMIT 20")
    if resend:
        for r in rows:
            send_review(r["id"])
    return len(rows)


def batch_notice(n: int):
    """Sau khi lên lịch: một tin có nút duyệt tất cả (từng bài đã gửi riêng)."""
    total = pending_reviews()
    if n and total > 1:
        send(f"📝 Nhi vừa viết {n} bài, đang có <b>{total} bài chờ sếp duyệt</b> (từng bài ở trên).",
             [[{"text": f"✅ Duyệt tất cả {total} bài", "callback_data": "nr:all"}]])


def on_callback(cb: dict, call) -> bool:
    """Nút bấm của Nhi (callback bắt đầu “nr:”). call = hàm gọi API của bot nhận nút."""
    data = cb.get("data") or ""
    if not data.startswith("nr:"):
        return False
    import page_brain
    m = cb.get("message") or {}
    chat, mid = m.get("chat", {}).get("id"), m.get("message_id")

    def mark(label):
        try:
            call("editMessageReplyMarkup", chat_id=chat, message_id=mid, reply_markup={"inline_keyboard": [[{"text": label, "callback_data": "nr:noop"}]]})
        except Exception:
            pass

    def kb(rows):
        try:
            call("editMessageReplyMarkup", chat_id=chat, message_id=mid, reply_markup={"inline_keyboard": rows})
        except Exception:
            pass
    parts = data.split(":")
    act, toast = parts[1], ""
    try:
        if act == "a":
            page_brain.review(int(parts[2]), "approve")
            mark("✅ Đã duyệt")
            toast = "Đã duyệt"
        elif act == "r":
            kb(reason_buttons(int(parts[2])))
            toast = "Chọn lý do loại"
        elif act == "b":
            kb(review_buttons(int(parts[2])))
        elif act == "x":
            why = page_brain.REASONS[int(parts[3])]
            page_brain.review(int(parts[2]), "reject", reason=why)
            mark(f"❌ Đã loại: {why}")
            toast = "Đã loại, Nhi ghi nhớ lý do"
        elif act == "all":
            n = page_brain.approve_all()
            mark(f"✅ Đã duyệt {n} bài")
            toast = f"Đã duyệt {n} bài"
        elif act == "off":
            db.set_setting("trend_review", "0")
            mark("Nhi tự đăng, không chờ duyệt")
            toast = "Đã tắt duyệt. Nhắn “bật duyệt” để bật lại"
        elif act == "keep":
            mark("Vẫn duyệt từng bài")
            toast = "Nhi vẫn chờ sếp duyệt"
    except (ValueError, IndexError) as ex:
        toast = str(ex) or "Bài này đã xử lý"
        if "không còn chờ duyệt" in toast:
            mark("Đã xử lý")
    try:
        call("answerCallbackQuery", callback_query_id=cb["id"], text=(toast or "OK")[:190])
    except Exception:
        pass
    return True


def on_reply(msg: dict) -> str | None:
    """Sếp trả lời tin “Bài chờ duyệt” bằng chữ = bản sửa, duyệt luôn. None nếu không phải trả lời tin duyệt bài."""
    rid = (msg.get("reply_to_message") or {}).get("message_id")
    text = (msg.get("text") or "").strip()
    if not rid or not text:
        return None
    p = next((r for r in db.q("SELECT id, status, review_msg FROM posts WHERE review_msg IS NOT NULL ORDER BY id DESC LIMIT 300")
              if str(rid) in (r["review_msg"] or "").split(",")), None)
    if not p:
        return None
    if p["status"] != "page_review":
        return f"Bài #{p['id']} đã xử lý rồi."
    import page_brain
    low = plain(text)
    if low in ("duyet", "ok", "dang", "duyet di", "ok dang"):
        page_brain.review(p["id"], "approve")
        return f"✅ Đã duyệt bài #{p['id']}."
    if low.startswith(("loai", "bo bai", "khong dang")):
        why = re.sub(r"^\s*(loại|bỏ bài|không đăng)\s*[:,-]?\s*", "", text, flags=re.I) or "Sếp loại"
        page_brain.review(p["id"], "reject", reason=why)
        return f"❌ Đã loại bài #{p['id']}, Nhi ghi nhớ: {e(why)}"
    try:
        page_brain.review(p["id"], "approve", content=text)
    except ValueError as ex:
        return f"Chưa duyệt được: {e(ex)}"
    return f"✅ Đã duyệt bản sếp sửa cho bài #{p['id']}. Nhi ghi nhớ cách sếp viết cho Trang này."


# ---------------------------------------------------------------- Nhi tự lo
def auto_keywords(pg: dict) -> dict:
    """Trang chưa có từ khóa: Nhi tự đặt (theo tên Trang, ngành nghề, bài được hưởng ứng) rồi báo sếp."""
    if (pg.get("keywords") or "").strip() or db.get_settings().get("nhi_auto_kw", "1") != "1":
        return pg
    from llm import llm
    if not llm.live and not (pg.get("niche") or "").strip():  # chưa có Claude, chưa có ngành nghề: không đoán bừa từ khóa
        return pg
    import page_brain
    try:
        kws = page_brain.suggest_keywords(pg["id"])
    except Exception as ex:
        print("[nhi kw]", ex)
        return pg
    if not kws:
        return pg
    page_brain.update_page(pg["id"], {"keywords": ", ".join(kws)})
    db.log("nhi", "Tự đặt từ khóa Trang", f"{pg['name']}: {', '.join(kws)}")
    send(f"🔑 Trang <b>{e(pg['name'])}</b> chưa có từ khóa, Nhi tự đặt: {e(', '.join(kws))}.\n"
         f"Muốn đổi, nhắn: <code>{e(pg['name'])} từ khóa: …</code>")
    return db.one("SELECT * FROM fb_pages WHERE id=?", (pg["id"],))


def maybe_ask_off():
    """Nhi đã hiểu ý sếp (đủ 20 lần duyệt, từ 85% duyệt ngay): hỏi sếp tắt duyệt, mỗi tuần hỏi tối đa 1 lần."""
    import page_brain
    s = db.get_settings()
    if not page_brain.review_on() or (s.get("nhi_off_asked") or "") > _days_ago(7):
        return False
    sm = page_brain.smartness()
    if not sm["suggest_off"]:
        return False
    db.set_setting("nhi_off_asked", db.today())
    send(f"💡 {sm['pct']}% trong {sm['n']} lần gần nhất sếp duyệt ngay không sửa. Sếp cho Nhi tự đăng, không chờ duyệt nữa?",
         [[{"text": "✅ Nhi tự đăng", "callback_data": "nr:off"}, {"text": "Vẫn duyệt", "callback_data": "nr:keep"}]])
    return True


def _days_ago(n: int) -> str:
    from datetime import timedelta
    return (db.clock() - timedelta(days=n)).strftime("%Y-%m-%d")


def noimg_due() -> int:
    """Tới giờ đăng mà sếp chưa gửi ảnh: Nhi đăng bài chỉ có chữ (cài đặt trend_noimg_post, mặc định bật)."""
    if db.get_settings().get("trend_noimg_post", "1") != "1":
        return 0
    rows = db.q("""SELECT p.id, p.scheduled_for, f.name page_name FROM posts p LEFT JOIN fb_pages f ON f.id=p.fb_page_ref
                   WHERE p.status='need_image' AND p.scheduled_for IS NOT NULL AND p.scheduled_for <= ?""", (db.clock().strftime("%Y-%m-%d %H:%M"),))
    for r in rows:
        db.run("UPDATE posts SET status='scheduled', text_only=1 WHERE id=? AND status='need_image'", (r["id"],))
        db.log("nhi", "Đăng chữ vì chưa có ảnh", f"Bài #{r['id']} ({r['page_name']}): tới giờ chưa có ảnh, đăng bài chỉ có chữ")
    if rows:
        send(f"🕒 Tới giờ đăng mà chưa có ảnh: Nhi đăng <b>{len(rows)} bài chỉ có chữ</b> ({e(', '.join(sorted({r['page_name'] or '' for r in rows})))}). "
             "Muốn Nhi luôn chờ ảnh, nhắn “luôn chờ ảnh”.")
    return len(rows)


# ---------------------------------------------------------------- lệnh bằng lời
HELP = ("Sếp nhắn Nhi bằng lời, ví dụ:\n"
        "• <code>các trang</code> · <code>báo cáo</code> · <code>bài chờ duyệt</code> · <code>duyệt tất cả</code>\n"
        "• <code>thêm trang Bếp Nhà Mình https://facebook.com/bepnhaminh</code>\n"
        "• <code>Bếp Nhà Mình từ khóa: món chay, canh chua</code> (<code>thêm từ khóa</code> để thêm)\n"
        "• <code>Bếp Nhà Mình không viết về: rượu bia</code> · <code>Bếp Nhà Mình ngành nghề: nấu ăn gia đình</code>\n"
        "• <code>Bếp Nhà Mình 2 bài/ngày lúc 09:00, 19:30</code> · <code>tạm dừng Bếp Nhà Mình</code> · <code>chạy lại Bếp Nhà Mình</code>\n"
        "• <code>viết bài cho Bếp Nhà Mình</code> · <code>tạo trang Góc Thú Cưng về nuôi chó mèo</code>\n"
        "• <code>Bếp Nhà Mình nhớ: luôn xưng mình, kết bằng câu hỏi</code> · <code>gợi ý từ khóa Bếp Nhà Mình</code>\n"
        "• <code>chủ đề nào được quan tâm nhất</code> (thêm tên Trang để xem riêng Trang đó)\n"
        "• <code>tắt duyệt</code> / <code>bật duyệt</code> · <code>luôn chờ ảnh</code> / <code>đăng chữ khi thiếu ảnh</code>\n"
        "• Ảnh 3D sản phẩm: gửi ảnh kèm chú thích <code>ảnh 3D Trà gừng</code> · <code>ghép ảnh 3D chính xác / hòa trộn / tự chọn</code>\n"
        "• Ảnh: <code>đổi ảnh #12</code> · <code>tắt tự làm ảnh</code> / <code>bật tự làm ảnh</code> · cài khóa: <code>cloudflare &lt;Account ID&gt; &lt;API Token&gt;</code>, <code>pixabay &lt;key&gt;</code>\n"
        "Bài chờ duyệt: bấm nút, hoặc trả lời tin bài bằng bản sửa. Ảnh: trả lời tin xin ảnh bằng ảnh.")

ACTIONS_DOC = """- list: danh sách Trang + tình hình
- pending: gửi lại các bài chờ duyệt
- approve_all
- review {on: true|false}: bật / tắt sếp duyệt bài trước khi đăng
- noimg {on: true|false}: tới giờ đăng chưa có ảnh thì đăng chữ (true) / luôn chờ ảnh (false)
- add_page {name, url, nick?}: nuôi thêm Trang có sẵn (link facebook.com)
- create_page {name, niche?}: Nhi tự tạo Trang mới trên Facebook
- keywords {page, keywords, add: bool}: đặt / thêm từ khóa nội dung
- avoid {page, words} · niche {page, text} · teach {page, text}: lời dặn Nhi ghi nhớ cho Trang
- schedule {page, per_day?, times?} · pause {page} · resume {page} · write {page?} · suggest {page}
page = tên Trang (đúng như danh sách) hoặc "all"."""


def _pages(status=("active", "paused")) -> list[dict]:
    return db.q(f"SELECT * FROM fb_pages WHERE status IN ({','.join('?' * len(status))}) ORDER BY id", status)


def find_page(text: str) -> dict | None:
    t = " " + plain(text) + " "
    best = None
    for p in _pages(("active", "paused", "creating")):
        n = plain(p["name"]).strip()
        if n and f" {n} " in t and (not best or len(n) > len(plain(best["name"]))):
            best = p
    return best


def _nick(text: str) -> dict | None:
    t = plain(text)
    accs = db.q("""SELECT a.*, (SELECT COUNT(*) FROM fb_pages f WHERE f.admin_account_id=a.id AND f.status='active') pages FROM fb_accounts a
                   JOIN sales s ON s.id=a.sale_id WHERE a.enabled=1 AND COALESCE(s.status,'active')!='fired' ORDER BY a.id""")
    named = next((a for a in accs if plain(a["name"] or "") and plain(a["name"]) in t), None)
    if named:
        return named
    ok = [a for a in accs if a.get("login_status") == "ok"] or accs
    return min(ok, key=lambda a: a["pages"]) if ok else None


def report() -> str:
    import page_brain
    rows = db.q("""SELECT f.*, (SELECT COUNT(*) FROM posts p WHERE p.fb_page_ref=f.id AND substr(p.scheduled_for,1,10)=? AND p.status != 'rejected') today,
                   (SELECT COUNT(*) FROM posts p WHERE p.fb_page_ref=f.id AND p.status='posted' AND substr(p.posted_at,1,10)=?) posted
                   FROM fb_pages f WHERE f.status IN ('active','paused','creating') ORDER BY f.status, f.id""", (db.today(), db.today()))
    sm = page_brain.smartness()
    out = [f"📄 <b>Các Trang của Nhi</b> · duyệt bài: {'bật' if page_brain.review_on() else 'tắt (Nhi tự đăng)'}"
           + (f" · Nhi hiểu ý sếp {sm['pct']}% ({sm['n']} lần)" if sm["n"] else "")]
    for r in rows:
        st = {"active": "▶", "paused": "⏸", "creating": "🛠"}[r["status"]]
        out.append(f"{st} <b>{e(r['name'])}</b> ({'nuôi' if (r.get('kind') or 'trend') == 'grow' else 'xu hướng'}) · {r['posts_per_day'] or 0} bài/ngày {e(r['times'] or '')}"
                   f" · hôm nay {r['posted']}/{r['today']} đã đăng · {r['followers'] if r['followers'] is not None else '—'} theo dõi"
                   + (f"\n   từ khóa: {e(r['keywords'])}" if r.get("keywords") else "\n   chưa có từ khóa"))
    pend = pending_reviews()
    if pend:
        out.append(f"📝 {pend} bài chờ duyệt (nhắn “bài chờ duyệt” để xem lại)")
    return "\n".join(out) if rows else "Nhi chưa nuôi Trang nào. Nhắn: thêm trang &lt;tên&gt; &lt;link&gt;"


def top_topics(pg: dict | None = None, days: int = 30) -> str:
    """Chủ đề / từ khóa được quan tâm nhất trên các Trang (tương tác thật = cảm xúc + 2×bình luận + 3×chia sẻ), kèm xu hướng Google hôm nay."""
    from datetime import timedelta
    since = (db.clock() - timedelta(days=days)).strftime("%Y-%m-%d")
    where, args = "p.status='posted' AND p.fb_page_ref IS NOT NULL AND p.posted_at >= ?", [since]
    if pg:
        where += " AND p.fb_page_ref=?"
        args.append(pg["id"])
    eng = "COALESCE(p.reactions,0)+2*COALESCE(p.comments,0)+3*COALESCE(p.shares,0)"
    rows = db.q(f"""SELECT COALESCE(NULLIF(p.page_kw,''), NULLIF(p.trend_topic,''), p.angle, 'khác') t, COUNT(*) n, AVG({eng}) e,
                    SUM(COALESCE(p.comments,0)) cm, SUM(COALESCE(p.leads,0)) ld, COUNT(DISTINCT p.fb_page_ref) pages
                    FROM posts p WHERE {where} GROUP BY t ORDER BY e DESC LIMIT 8""", args)
    pages = db.q(f"""SELECT f.name, COUNT(*) n, AVG({eng}) e FROM posts p JOIN fb_pages f ON f.id=p.fb_page_ref WHERE {where}
                     GROUP BY f.id ORDER BY e DESC LIMIT 5""", args)
    total = sum(r["n"] for r in rows)
    out = [f"📊 <b>Chủ đề được quan tâm nhất · {days} ngày</b>" + (f" · Trang {e(pg['name'])}" if pg else " · mọi Trang")]
    if rows:
        out += [f"{i}. <b>{e(r['t'])}</b>: tương tác TB {r['e']:.0f}/bài · {r['n']} bài · {r['cm']} bình luận" + (f" · {r['ld']} khách" if r["ld"] else "")
                for i, r in enumerate(rows, 1)]
        if total < 15:
            out.append("<i>Mới có " + str(total) + " bài đã đăng có số liệu: xem để tham khảo, chưa đủ để kết luận.</i>")
    else:
        out.append("Chưa có bài Trang nào đã đăng kèm số liệu tương tác (nick quản trị đọc số liệu mỗi ngày trong ca làm việc).")
    if len(pages) > 1 and not pg:
        out.append("\n🏆 <b>Trang hút tương tác nhất</b>: " + " · ".join(f"{e(p['name'])} ({p['e']:.0f}/bài)" for p in pages))
    hot = db.q("SELECT title, score FROM trend_hot WHERE day=(SELECT MAX(day) FROM trend_hot) ORDER BY score DESC LIMIT 5")
    if hot:
        out.append("\n🔥 <b>Đang lên Google Trends</b> (Nhi chọn): " + " · ".join(f"{e(h['title'])} ({h['score']})" for h in hot))
    return "\n".join(out)


def _rule(text: str) -> list[dict]:
    t, low = text.strip(), plain(text)
    pg = find_page(t)
    name = pg["name"] if pg else None
    url = re.search(r"https?://\S+", t)
    after = lambda key: re.split(key, t, maxsplit=1, flags=re.I)[-1].strip(" :,-.") if re.search(key, t, re.I) else ""
    m = re.match(r"^\s*cloudflare\s+([0-9a-fA-F]{32})\s+(\S{20,})\s*$", t)
    if m:
        return [{"type": "img_keys", "cf_account_id": m.group(1), "cf_api_token": m.group(2)}]
    m = re.match(r"^\s*pixabay\s+(\S{10,})\s*$", t, re.I)
    if m:
        return [{"type": "img_keys", "pixabay_key": m.group(1)}]
    m = re.search(r"(?:đổi|làm lại|tạo lại)\s+ảnh\s*(?:bài)?\s*#?(\d+)", t, re.I)
    if m:
        return [{"type": "regen", "post": int(m.group(1))}]
    m = re.search(r"ghep anh 3d\s+(chinh xac|hoa tron|tu chon)", low)
    if m:
        return [{"type": "img3d_mode", "mode": {"chinh xac": "exact", "hoa tron": "blend", "tu chon": "auto"}[m.group(1)]}]
    if re.search(r"\b(tat|dung) (tu )?lam anh\b", low):
        return [{"type": "img_auto", "on": False}]
    if re.search(r"\b(bat|cho nhi) (tu )?lam anh\b", low):
        return [{"type": "img_auto", "on": True}]
    if re.search(r"chu de nao|quan tam nhat|tuong tac (nhat|cao)|hieu qua nhat|chu de hot|chu de (tot|hay) nhat|nguoi xem nhieu", low):
        return [{"type": "top_topics", "page": name or ""}]
    if re.search(r"^(cac trang|danh sach trang|bao cao|tinh hinh|trang)$", low.strip()):
        return [{"type": "list"}]
    if "cho duyet" in low and "duyet tat ca" not in low:
        return [{"type": "pending"}]
    if "duyet tat ca" in low or "duyet het" in low:
        return [{"type": "approve_all"}]
    if re.search(r"\b(tat|khong can|bo) duyet\b|\btu dang\b", low):
        return [{"type": "review", "on": False}]
    if re.search(r"\bbat duyet\b|\bcho (anh|sep|em) duyet\b", low):
        return [{"type": "review", "on": True}]
    if "luon cho anh" in low or "khong dang chu" in low:
        return [{"type": "noimg", "on": False}]
    if "dang chu" in low:
        return [{"type": "noimg", "on": True}]
    if url and re.search(r"\b(them|nuoi) (trang|page)\b", low):
        nm = re.sub(r"https?://\S+", "", re.split(r"(?:thêm|nuôi)\s+(?:trang|page)", t, maxsplit=1, flags=re.I)[-1])
        nm = re.sub(r"\b(nick|do|admin|quản trị)\b.*$", "", nm, flags=re.I).strip(" :,-.“”\"'")
        return [{"type": "add_page", "name": nm, "url": url.group(0), "nick": t}]
    m = re.search(r"(?:tạo|lập|mở)\s+(?:trang|page)(?:\s+mới)?\s+(.+?)(?:\s+(?:về|chủ đề|ngách)\s+(.+))?$", t, re.I)
    if m and not url:
        return [{"type": "create_page", "name": m.group(1).strip(" “”\"'"), "niche": (m.group(2) or "").strip()}]
    if re.search(r"\b(tam dung|dung)\b", low) and pg:
        return [{"type": "pause", "page": name}]
    if re.search(r"\b(chay lai|nuoi lai|bat lai)\b", low) and pg:
        return [{"type": "resume", "page": name}]
    if re.search(r"\bgoi y (them )?tu khoa\b", low):
        return [{"type": "suggest", "page": name or ""}]
    if "tu khoa" in low and pg:
        return [{"type": "keywords", "page": name, "keywords": after(r"từ khóa|từ khoá|tu khoa"), "add": "them tu khoa" in low}]
    if re.search(r"khong viet ve|tranh|cam viet", low) and pg:
        return [{"type": "avoid", "page": name, "words": after(r"không viết về|tránh|cấm viết")}]
    if re.search(r"nganh nghe|chu de trang|nganh", low) and pg:
        return [{"type": "niche", "page": name, "text": after(r"ngành nghề|chủ đề trang|ngành")}]
    if re.search(r"\b(nho|ghi nho|day|dan)\b", low) and pg:
        return [{"type": "teach", "page": name, "text": after(r"ghi nhớ|nhớ|dạy|dặn")}]
    per = re.search(r"(\d)\s*bai\s*(?:/|moi|1)?\s*ngay", low)
    times = re.findall(r"\b([01]?\d|2[0-3])[:h]([0-5]\d)\b", t)
    if pg and (per or times):
        return [{"type": "schedule", "page": name, "per_day": int(per.group(1)) if per else None,
                 "times": ",".join(f"{int(h):02d}:{mm}" for h, mm in times) or None}]
    if re.search(r"\bviet( \d+)? bai\b", low):
        return [{"type": "write", "page": name or ""}]
    return []


def _llm(text: str) -> list[dict]:
    from llm import llm
    if not llm.live:
        return []
    names = ", ".join(p["name"] for p in _pages(("active", "paused", "creating"))) or "(chưa có)"
    d = llm.json("Bạn là Nhi, quản lý các Trang Facebook. Hiểu lệnh của sếp và chuyển thành việc.",
                 f"Các Trang đang có: {names}\nViệc làm được:\n{ACTIONS_DOC}\nLệnh của sếp: {text}\n"
                 'JSON: {"actions": [{"type": "...", ...}], "reply": "câu trả lời ngắn nếu không có việc nào"}',
                 mock=lambda: {"actions": []}, max_tokens=500, task="ceo") or {}
    acts = [a for a in d.get("actions") or [] if isinstance(a, dict) and a.get("type")]
    if not acts and d.get("reply"):
        return [{"type": "say", "text": d["reply"]}]
    return acts


def _pg(name) -> dict | None:
    if not name or name == "all":
        return None
    return find_page(name) or next((p for p in _pages(("active", "paused", "creating")) if plain(name) in plain(p["name"])), None)


def execute(a: dict) -> str:
    import page_brain
    import page_grow
    import trend_pages
    t = a["type"]
    if t == "say":
        return e(a.get("text"))
    if t == "list":
        return report()
    if t == "top_topics":
        return top_topics(_pg(a.get("page")))
    if t == "img_keys":
        import image_gen
        for k in ("cf_account_id", "cf_api_token", "pixabay_key"):
            if a.get(k):
                db.set_setting(k, a[k])
        r = image_gen.test()
        return ("🔑 Đã lưu khóa (Nhi đã xóa tin chứa khóa khỏi cuộc trò chuyện).\n"
                f"Cloudflare: {e(r['cloudflare'])}\nPixabay: {e(r['pixabay'])}")
    if t == "img3d_mode":
        db.set_setting("img3d_mode", a.get("mode") or "auto")
        return {"exact": "🖼 Ảnh 3D: luôn ghép chính xác (giữ nguyên nhãn sản phẩm).", "blend": "🖼 Ảnh 3D: luôn để AI hòa trộn vào cảnh.",
                "auto": "🖼 Ảnh 3D: bài bán hàng ghép chính xác, bài khác AI hòa trộn."}.get(a.get("mode"), "Đã đổi.")
    if t == "img_auto":
        db.set_setting("img_auto", "1" if a.get("on") else "0")
        return "🖼 Nhi tự làm ảnh cho bài và logo, banner Trang." if a.get("on") else "Nhi thôi tự làm ảnh, gửi prompt để sếp làm."
    if t == "regen":
        import image_gen
        p = db.one("SELECT * FROM posts WHERE id=?", (a.get("post"),))
        if not p or p["status"] not in ("need_image", "scheduled", "page_review") or not p.get("fb_page_ref"):
            return "Bài này không còn chờ đăng nên không đổi ảnh được."
        if p.get("source") == "page_grow":
            if image_gen.for_product_post(p["id"]):
                return f"🖼 Nhi đã ghép ảnh 3D mới cho bài #{p['id']} (gửi ngay bên dưới)."
            return "Sản phẩm của bài chưa có ảnh 3D (thêm ở trang Sản phẩm, hoặc gửi ảnh kèm chú thích “ảnh 3D tên sản phẩm”)."
        db.run("UPDATE posts SET status='need_image' WHERE id=?", (p["id"],))
        if image_gen.for_post(p["id"]):
            return f"🖼 Nhi đã làm ảnh mới cho bài #{p['id']} (gửi ngay bên dưới)."
        db.run("UPDATE posts SET status=? WHERE id=?", (p["status"], p["id"]))
        return "Nhi chưa làm được ảnh mới (xem lý do ở màn Lỗi); bài giữ ảnh cũ."
    if t == "pending":
        n = pending_reviews(resend=True)
        return f"Đã gửi lại {n} bài chờ duyệt." if n else "Không có bài nào chờ duyệt."
    if t == "approve_all":
        return f"✅ Đã duyệt {page_brain.approve_all()} bài."
    if t == "review":
        db.set_setting("trend_review", "1" if a.get("on") else "0")
        return "Đã bật: Nhi chờ sếp duyệt từng bài." if a.get("on") else "Đã tắt duyệt: Nhi tự đăng theo lịch, vẫn ghi nhớ khi sếp nhắn sửa."
    if t == "noimg":
        db.set_setting("trend_noimg_post", "1" if a.get("on") else "0")
        return ("Tới giờ đăng chưa có ảnh thì Nhi đăng bài chỉ có chữ." if a.get("on")
                else "Nhi luôn chờ ảnh của sếp; bài chờ ảnh quá 24 giờ thì bỏ.")
    if t == "add_page":
        nk = _nick(str(a.get("nick") or ""))
        if not nk:
            return "Chưa có nick sale nào để làm quản trị Trang. Thêm nick ở phần mềm trước."
        try:
            pg = page_grow.add_page(a.get("name") or "", a.get("url") or "", nk["id"])
        except ValueError as ex:
            return f"Chưa thêm được: {e(ex)}"
        pg = auto_keywords(pg)
        return (f"✅ Nhi nhận nuôi Trang <b>{e(pg['name'])}</b>, nick quản trị {e(nk['name'])} (phải là quản trị viên Trang), "
                f"{pg['posts_per_day']} bài/ngày lúc {e(pg['times'])}. Từ khóa: {e(pg.get('keywords') or '(chưa có)')}.")
    if t == "create_page":
        import trend_create
        try:
            r = trend_create.boss_idea(a.get("name") or "", a.get("niche") or "")
        except ValueError as ex:
            return f"Chưa tạo được: {e(ex)}"
        return f"🛠 Nhi đưa Trang <b>{e(r['page']['name'])}</b> vào hàng tạo, nick quản trị tạo ở ca làm việc tới rồi báo sếp."
    pg = _pg(a.get("page"))
    if t == "write":
        targets = [pg] if pg else [p for p in _pages(("active",))]
        n = 0
        for p in targets:
            if (p.get("kind") or "trend") == "grow":
                if page_grow.ready(p):
                    continue
                page_grow.write(p)
            else:
                if not p.get("admin_account_id"):
                    continue
                trend_pages.write_post(auto_keywords(p), page_grow.next_slot(p))
            n += 1
        return f"✍️ Nhi viết {n} bài" + (", chờ sếp duyệt (gửi ngay bên dưới)." if page_brain.review_on() else ", đã xếp lịch.") if n else "Chưa có Trang nào sẵn sàng để viết."
    if t == "suggest":
        targets = [pg] if pg else [p for p in _pages(("active",))]
        out = []
        for p in targets[:5]:
            kws = page_brain.suggest_keywords(p["id"])
            if kws:
                cur = words(p.get("keywords") or "")
                page_brain.update_page(p["id"], {"keywords": ", ".join(cur + kws)})
                out.append(f"• {e(p['name'])}: thêm {e(', '.join(kws))}")
        return ("🔑 Nhi thêm từ khóa:\n" + "\n".join(out)) if out else "Nhi chưa nghĩ ra từ khóa mới."
    if not pg:
        return "Nhi chưa rõ Trang nào. Nhắn đúng tên Trang (gõ “các trang” để xem danh sách)."
    if t == "pause":
        db.run("UPDATE fb_pages SET status='paused' WHERE id=?", (pg["id"],))
        db.run("UPDATE posts SET status='rejected', error='Trang tạm dừng' WHERE fb_page_ref=? AND status IN ('page_review','need_image','scheduled')", (pg["id"],))
        return f"⏸ Đã tạm dừng {e(pg['name'])}, bỏ các bài chưa đăng."
    if t == "resume":
        if not pg.get("url") or not pg.get("admin_account_id"):
            return f"Trang {e(pg['name'])} chưa có link hoặc nick quản trị."
        db.run("UPDATE fb_pages SET status='active' WHERE id=?", (pg["id"],))
        return f"▶ Nhi nuôi lại {e(pg['name'])}."
    if t == "keywords":
        kws = words(a.get("keywords") or "")
        if not kws:
            return "Nhắn kèm từ khóa, VD: Bếp Nhà Mình từ khóa: món chay, canh chua"
        if a.get("add"):
            kws = words(pg.get("keywords") or "") + kws
        p = page_brain.update_page(pg["id"], {"keywords": ", ".join(kws)})
        return f"🔑 {e(pg['name'])}: từ khóa {e(p['keywords'])}. Nhi viết theo từ khóa mới từ bài tiếp theo."
    if t == "avoid":
        p = page_brain.update_page(pg["id"], {"avoid": ", ".join(words(pg.get("avoid") or "") + words(a.get("words") or ""))})
        return f"🚫 {e(pg['name'])}: không viết về {e(p['avoid'])}."
    if t == "niche":
        page_brain.update_page(pg["id"], {"niche": a.get("text") or ""})
        return f"🏷 {e(pg['name'])}: ngành nghề “{e(a.get('text'))}”."
    if t == "teach":
        if not (a.get("text") or "").strip():
            return "Nhắn kèm điều cần nhớ, VD: Bếp Nhà Mình nhớ: luôn xưng mình"
        page_brain.update_page(pg["id"], {"teach": a["text"]})
        return f"🧠 Nhi ghi nhớ cho {e(pg['name'])}: {e(a['text'])}"
    if t == "schedule":
        p = page_brain.update_page(pg["id"], {"posts_per_day": a.get("per_day"), "times": a.get("times")})
        return f"🗓 {e(pg['name'])}: {p['posts_per_day']} bài/ngày lúc {e(p['times'])}."
    return "Nhi chưa làm được việc này."


def on_photo_3d(msg: dict, bot) -> str | None:
    """Ảnh gửi kèm chú thích “ảnh 3D <tên sản phẩm>”: lưu vào mục Ảnh 3D của sản phẩm. None nếu không phải ảnh 3D."""
    import httpx
    cap = msg.get("caption") or ""
    if not re.search(r"\b3\s*d\b", plain(cap)):
        return None
    t = " " + plain(re.sub(r"(?i)ảnh|anh|hình|3\s*d", " ", cap)) + " "
    prods = sorted(db.q("SELECT id, name FROM products"), key=lambda p: -len(p["name"] or ""))
    pr = next((p for p in prods if plain(p["name"]).strip() and plain(p["name"]).strip() in t), None)
    if not pr:
        return "Nhi chưa biết ảnh 3D này của sản phẩm nào. Gửi lại kèm chú thích đúng tên sản phẩm, VD “ảnh 3D " + e(prods[0]["name"] if prods else "Trà gừng") + "”."
    fid, ext = None, "jpg"
    if (msg.get("document") or {}).get("mime_type", "").startswith("image/"):  # gửi dạng tệp: giữ nền trong suốt của PNG
        fid, ext = msg["document"]["file_id"], msg["document"]["mime_type"].split("/")[-1]
    elif msg.get("photo"):
        fid = sorted(msg["photo"], key=lambda x: x.get("file_size") or x.get("width", 0))[-1]["file_id"]
    if not fid:
        return None
    try:
        info = bot.call("getFile", file_id=fid)
        data = httpx.get(f"{getattr(bot, 'API', 'https://api.telegram.org')}/file/bot{bot.token()}/{info['file_path']}", timeout=60).content
        import image_gen
        n = len(image_gen.add_3d(pr["id"], data, ext))
    except Exception as ex:
        return f"Chưa lưu được ảnh 3D: {e(ex)}"
    return (f"✅ Đã lưu ảnh 3D cho <b>{e(pr['name'])}</b> ({n} ảnh). Nhi dùng ảnh này để ghép vào ảnh bài Trang."
            + ("" if ext == "png" else "\nMẹo: gửi PNG nền trong suốt <b>dạng tệp</b> (không nén) để ghép đẹp nhất."))


def has_secret(text: str) -> bool:
    return bool(re.match(r"^\s*(nhi\s*(ơi)?[\s,:]*)?(cloudflare|pixabay)\s+\S", text or "", re.I))


def handle_text(text: str) -> str:
    """Lệnh bằng lời của sếp cho Nhi → làm và trả lời (HTML)."""
    text = re.sub(r"^\s*nhi\s*(ơi)?[\s,:]*", "", text or "", flags=re.I).strip()
    if not text or plain(text) in ("help", "giup", "huong dan", "lenh"):
        return HELP
    acts = _rule(text) or _llm(text)
    if not acts:
        return "Nhi chưa hiểu ý sếp.\n\n" + HELP
    out = []
    for a in acts[:5]:
        try:
            out.append(execute(a))
        except Exception as ex:
            out.append(f"Lỗi khi làm “{e(a.get('type'))}”: {e(ex)}")
    db.log("nhi", "Nhận lệnh qua Telegram", text[:200])
    return "\n".join(out)

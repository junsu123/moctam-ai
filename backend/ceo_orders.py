"""Luật: sếp chỉ giao việc cho CEO, CEO tự vận hành phòng kinh doanh.

- Sếp nhắn việc cho CEO bằng lời thường (trên phần mềm hoặc Telegram). CEO hiểu lệnh, chia thành việc cụ thể cho
  từng agent (chỉ trong danh sách việc được phép), làm ngay và báo lại đã làm gì.
- Agent nào làm sai, sếp nói với CEO: CEO ghi thành bài học bắt buộc của agent đó, hoặc thành chỉ đạo lâu dài cho cả đội.
  Chỉ đạo của sếp được đưa vào lời dặn (prompt) của agent liên quan ở mọi lần làm việc sau.
- Chế độ tự vận hành: CEO tự duyệt bài nháp của Lan theo luật (không hứa chữa bệnh, độ dài hợp lý, không trùng bài cũ),
  rồi cho Tuấn xếp lịch. Sau họp sáng, việc hằng ngày luôn được chạy.
Có khóa API thì CEO dùng AI để hiểu lệnh; chưa có khóa thì hiểu các mẫu câu thường gặp.
"""
import json
import re
import threading
from datetime import datetime, timedelta

import db

AGENT_ALIASES = {"minh": "minh", "lan": "lan", "tuan": "tuan", "tuấn": "tuan", "ha": "ha", "hà": "ha", "khoa": "khoa", "mai": "mai", "vy": "vy", "bao": "bao",
                 "đức": "ceo", "duc": "ceo", "ceo": "ceo", "trưởng phòng": "minh"}
def _aliases() -> dict:
    """Tên gọi agent: tên mặc định + tên sếp đã đổi (CEO hiểu “Ngọc viết dài quá” là nói Lan nếu sếp đổi tên Lan thành Ngọc)."""
    import agents
    import unicodedata
    agents.apply_profiles()
    out = dict(AGENT_ALIASES)
    for aid, a in agents.AGENTS.items():
        n = a["name"].lower()
        out[n] = aid
        out[unicodedata.normalize("NFD", n).encode("ascii", "ignore").decode().replace("đ", "d")] = aid
    return dict(sorted(out.items(), key=lambda kv: -len(kv[0])))  # tên dài khớp trước


SETTINGS_OK = {
    "posts_per_day": ("int", 1, 20, "số bài Lan viết mỗi ngày"), "kpi_min": ("int", 1, 50, "KPI tối thiểu khách có SĐT/ngày"),
    "kpi_max": ("int", 1, 100, "KPI phấn đấu"), "scan_times": ("times", 0, 0, "giờ quét bình luận"),
    "discover_time": ("time", 0, 0, "giờ đi tìm nhóm"), "join_per_nick_day": ("int", 0, 5, "số nhóm xin vào/nick/ngày"),
    "discover_add_per_day": ("int", 0, 30, "số nhóm tự thêm/ngày"), "images_min": ("int", 0, 6, "số ảnh tối thiểu mỗi bài"),
    "images_max": ("int", 1, 10, "số ảnh tối đa mỗi bài"), "bump_time": ("time", 0, 0, "giờ up bài"),
    "meeting_time": ("time", 0, 0, "giờ họp sáng"), "auto_meeting": ("bool", 0, 0, "tự họp mỗi sáng"),
    "bump_enabled": ("bool", 0, 0, "tự up bài"), "bump_contact": ("line", 0, 120, "dòng liên hệ Bảo gắn cuối bình luận up bài"), "scan_enabled": ("bool", 0, 0, "tự quét bình luận"),
    "discover_enabled": ("bool", 0, 0, "tự tìm nhóm"), "join_enabled": ("bool", 0, 0, "tự xin vào nhóm"),
    "auto_leave": ("bool", 0, 0, "tự thoát nhóm kém"), "admin_posts_min": ("int", 0, 20, "số bài tối thiểu/ngày ở nhóm mình quản lý"),
    "admin_posts_max": ("int", 1, 20, "số bài tối đa/ngày ở nhóm mình quản lý"),
    "prospect_tiktok": ("bool", 0, 0, "Mai tìm khách trên TikTok"), "prospect_shopee": ("bool", 0, 0, "Mai tìm khách trên Shopee"),
    "prospect_enabled": ("bool", 0, 0, "Mai tự tìm khách sỉ mỗi ngày"), "prospect_time": ("time", 0, 0, "giờ Mai đi tìm khách sỉ"),
    "post_target_mode": ("choice", ("all", "prefer", "only"), 0,
                         "nơi đăng bài (all: mọi nhóm, prefer: ưu tiên nhóm chỉ định, only: chỉ nhóm chỉ định)"),
    "post_group_keywords": ("text", 0, 300, "từ khóa nhóm nên đăng (cách nhau dấu phẩy)"),
    "post_group_exclude": ("text", 0, 300, "từ khóa nhóm không đăng (cách nhau dấu phẩy)"),
    "friends_enabled": ("bool", 0, 0, "Tuấn tìm người kết bạn trong nhóm mỗi ngày"),
    "fbp_friends_day": ("int", 0, 30, "số lời mời kết bạn tối đa/nick/ngày"),
}
REVIEW_BAD = re.compile(r"chữa (khỏi|bệnh|dứt)|trị (bệnh|dứt điểm|khỏi)|điều trị|khỏi hẳn|thần dược|thay thế thuốc|"
                        r"cam kết (giảm|khỏi|trị)|giảm \d+ ?kg|100 ?% (khỏi|hiệu quả)|đặc trị|chữa được", re.I)


def s() -> dict:
    return db.get_settings()


def autopilot() -> bool:
    return s().get("ceo_autopilot", "1") == "1"


def _say(role: str, text: str, actions=None, via: str = "web") -> int:
    return db.run("INSERT INTO ceo_messages(role, text, actions, via, created_at) VALUES (?,?,?,?,?)",
                  (role, text[:4000], json.dumps(actions or [], ensure_ascii=False), via, db.now()))


def history(limit: int = 30) -> list[dict]:
    rows = db.q("SELECT * FROM ceo_messages ORDER BY id DESC LIMIT ?", (limit,))[::-1]
    for r in rows:
        r["actions"] = json.loads(r["actions"] or "[]")
    return rows


# ---------------------------------------------------------------- chỉ đạo lâu dài
def orders(active_only: bool = True) -> list[dict]:
    return db.q("SELECT * FROM ceo_orders" + (" WHERE active=1" if active_only else "") + " ORDER BY id DESC")


def prompt_block(agent_id: str) -> str:
    """Chỉ đạo của sếp (qua CEO) đưa vào lời dặn của agent."""
    try:
        rows = db.q("SELECT text FROM ceo_orders WHERE active=1 AND (agent='all' OR agent=?) ORDER BY id", (agent_id,))
    except Exception:
        return ""
    if not rows:
        return ""
    return "\n\nCHỈ ĐẠO CỦA SẾP (CEO truyền đạt, bắt buộc tuân theo, ưu tiên hơn mọi thói quen cũ):\n" + \
        "\n".join(f"- {r['text']}" for r in rows)


# ---------------------------------------------------------------- người nhận
def _sales() -> list[dict]:
    return db.q("SELECT id, name, fb_name, login_status, auto_post, status FROM sales WHERE COALESCE(status,'active')!='fired'")


def _agent_id(name: str) -> str | None:
    n = (name or "").strip().lower()
    if n in ("all", "cả đội", "tất cả"):
        return "all"
    if n.startswith("sale-") and n[5:].isdigit():
        return n
    al = _aliases()
    if n in al:
        return al[n]
    for r in _sales():
        if r["name"].lower() == n or (r["fb_name"] or "").lower() == n:
            return f"sale-{r['id']}"
    return None


def _sale_id(v) -> int | None:
    if isinstance(v, int) or (isinstance(v, str) and v.isdigit()):
        return int(v)
    a = _agent_id(str(v))
    return int(a[5:]) if a and a.startswith("sale-") else None


def _name(agent_id: str) -> str:
    from agents import name_of
    return "cả đội" if agent_id == "all" else name_of(agent_id)


# ---------------------------------------------------------------- thực hiện việc
def _bg(fn, *a, **kw):
    threading.Thread(target=fn, args=a, kwargs=kw, daemon=True).start()


def followup(text: str, via: str = "web"):
    """CEO báo lại cho sếp khi việc đã giao làm xong (hoặc không làm được)."""
    _say("ceo", text, via=via)
    try:  # mọi việc xong đều báo sếp qua Telegram, kể cả việc sếp giao trên phần mềm
        import telegram_bot
        if via == "telegram" or telegram_bot.report_enabled():
            telegram_bot.send("👔 <b>CEO Đức báo lại:</b> " + telegram_bot.e(text))
    except Exception as ex:
        print("[ceo_orders]", ex)


JOB_TXT = {"open": "mở Chrome chờ sếp đăng nhập", "check": "kiểm tra phiên", "post": "đăng bài", "bump": "up bài",
           "scan": "quét bình luận", "discover": "tìm nhóm mới", "join": "xin vào nhóm"}


def why_no_sales() -> str:
    """Giải thích rõ vì sao chưa có nick sale nào làm được việc trên Facebook, và sếp cần làm gì."""
    import company
    if company.status() == "dissolved":
        return "Công ty đã giải thể nên mọi việc tự động đã dừng. Sếp thành lập lại ở trang Công ty."
    rows = db.q("SELECT * FROM sales WHERE COALESCE(status,'active')!='fired' AND COALESCE(is_sample,0)=0")
    if not rows:
        return "Chưa có nhân viên sale nào giữ nick Facebook. Sếp vào trang Nhân viên sale để tuyển, hoặc bảo em “tuyển thêm 1 sale”."
    import accounts
    nonick = [r["name"] for r in rows if not accounts.of_sale(r["id"])]
    not_in = [r["name"] for r in rows if r["login_status"] != "ok" and r["name"] not in nonick]
    paused = [r["name"] for r in rows if r["login_status"] == "ok" and not r["auto_post"]]
    parts = []
    if nonick:
        parts.append(f"{', '.join(nonick)} chưa có nick Facebook nào: sếp vào Nhân viên sale → Thêm nick")
    if not_in:
        parts.append(f"{', '.join(not_in)} chưa đăng nhập Facebook (hoặc nick bị checkpoint): sếp vào Nhân viên sale → "
                     "Mở Chrome để đăng nhập")
    if paused:
        parts.append(f"{', '.join(paused)} đang bị tạm dừng tự đăng: sếp bảo em “bật lại {paused[0]}”")
    return "Chưa có nick nào làm được: " + "; ".join(parts) + "." if parts else "Chưa có nick nào sẵn sàng."


def _busy_note(sale_id: int) -> str:
    import browser_poster
    b, q = browser_poster.busy(sale_id), browser_poster.queued(sale_id)
    if b:
        return f" ({_name('sale-' + str(sale_id))} đang {JOB_TXT.get(b, b)}, xong việc đó sẽ làm ngay" + \
            (" — nếu đang mở Chrome chờ đăng nhập, sếp đóng cửa sổ Chrome đó thì sale mới làm tiếp" if b == "open" else "") + ")"
    if q > 1:
        return f" (đang chờ {q - 1} việc khác của nick làm xong)"
    return ""


def _write_and_report(n, pid, tt, angle, note, via):
    import workflows
    try:
        made = workflows.generate_posts(n, pid, tt, angle, note)
    except Exception as e:
        followup(f"Lan chưa viết được bài: {str(e)[:150]}", via)
        return
    ids = [p["id"] for p in made]
    if not ids:
        followup("Lan chưa viết được bài nào (chưa có sản phẩm hoặc sản phẩm không hợp). Sếp kiểm tra trang Sản phẩm.", via)
        return
    msg = f"Lan đã viết xong {len(ids)} bài."
    if autopilot():
        ok, bad = [], []
        for pid_ in ids:
            p = db.one("SELECT * FROM posts WHERE id=?", (pid_,))
            if p and p["status"] == "draft":
                good, why = review_post(p)
                _apply_review(p, good, why)
                (ok if good else bad).append((pid_, why))
        plan = workflows.plan_distribution() if ok else []
        msg += f" Em duyệt {len(ok)} bài" + (f", loại {len(bad)} bài ({', '.join(sorted({w for _, w in bad}))})" if bad else "") + "."
        if plan:
            msg += " Tuấn đã xếp lịch: " + "; ".join(f"{x['time'][11:16]} {x['sale'] + ' → ' if x.get('sale') else ''}{x['group']}" for x in plan[:4])
        elif ok:
            msg += " Chưa xếp lịch được: " + (why_no_sales() if not __import__("group_finder")._working_sales()
                                             else "các nhóm đang giãn cách hoặc nick đã đủ bài hôm nay, bài chờ lượt sau.")
    followup(msg, via)


def _push_report(plan: list[dict], kws: list[str], want: int) -> str:
    kw = ", ".join(f"“{k}”" for k in kws)
    if not plan:
        return (f"Chưa xếp được bài nào vào nhóm có từ khóa {kw}: " +
                (why_no_sales() if not __import__("group_finder")._working_sales()
                 else "các nick đã đủ bài hôm nay hoặc hết giờ đăng. Bài chờ lượt sau, Tuấn vẫn ưu tiên nhóm này tới hết hôm nay."))
    msg = f"Tuấn xếp {len(plan)} bài vào nhóm có từ khóa {kw}: " + "; ".join(
        f"{x['time'][11:16]} {x['sale'] + ' → ' if x.get('sale') else ''}{x['group']}" for x in plan[:6]) + \
        (f" và {len(plan) - 6} bài nữa" if len(plan) > 6 else "") + "."
    if len(plan) < want:
        msg += (f" Còn {want - len(plan)} nhóm chưa xếp được vì nick đã đủ bài hôm nay hoặc hết giờ đăng (luật Facebook), "
                "Tuấn vẫn ưu tiên các nhóm này tới hết hôm nay.")
    return msg


def _push_write(need: int, pid, kws: list[str], want: int, via: str):
    """Thiếu bài đã duyệt: Lan viết thêm, CEO duyệt (chế độ tự động), Tuấn xếp vào nhóm khớp từ khóa."""
    import workflows
    kw = ", ".join(kws)
    try:
        made = workflows.generate_posts(need, pid, "group", None, f"Bài đăng vào các nhóm về: {kw}. Viết hợp với thành viên nhóm đó.")
    except Exception as e:
        made = []
        print("[push write]", e)
    if made and autopilot():
        for m in made:
            p = db.one("SELECT * FROM posts WHERE id=?", (m["id"],))
            if p and p["status"] == "draft":
                good, why = review_post(p)
                _apply_review(p, good, why)
    ok = sum(1 for m in made if (db.one("SELECT status FROM posts WHERE id=?", (m["id"],)) or {}).get("status") == "approved")
    if made and not autopilot():
        plan = workflows.plan_distribution(kws, want)  # bài đã duyệt sẵn (nếu có) xếp luôn
        followup((f"Lan viết xong {len(made)} bài cho nhóm có từ khóa “{kw}”. Sếp duyệt ở trang Bài đăng; duyệt xong Tuấn ưu tiên "
                  "xếp vào các nhóm này tới hết hôm nay.") + (" " + _push_report(plan, kws, want) if plan else ""), via)
        return
    plan = workflows.plan_distribution(kws, want)
    head = f"Lan viết {len(made)} bài, {ok} bài đạt. " if made else ("Lan chưa viết được bài mới. " if need else "")
    followup(head + _push_report(plan, kws, want), via)


def _find_product(pid=None, name=None) -> dict | None:
    if str(pid or "").isdigit():
        p = db.one("SELECT * FROM products WHERE id=?", (int(pid),))
        if p:
            return p
    return _product_in(str(name or ""))


def _product_in(text: str) -> dict | None:
    """Sản phẩm được nhắc tới trong câu (khớp nhiều từ nhất trong tên)."""
    low = (text or "").lower()
    best, hit = None, 0
    for p in db.q("SELECT * FROM products"):
        words = [w for w in p["name"].lower().split() if len(w) > 2][:4]
        n = sum(w in low for w in words)
        if words and n >= min(2, len(words)) and n > hit:
            best, hit = p, n
    return best


def execute(act: dict) -> str:
    """Thực hiện một việc trong danh sách được phép. Trả về một câu mô tả kết quả."""
    import workflows
    t = act.get("type")
    if t == "feed_style":
        style = "natural" if act.get("style") == "natural" else "invite"
        db.set_setting("feed_general_style", style)
        db.set_setting("feed_comment_all", "1")
        return ("Từ lượt lướt bảng tin tới, bài không liên quan Bảo viết câu mời sỉ (đáp một câu đúng bài rồi mời nhập sỉ, làm đại lý), "
                "kèm Zalo, sếp duyệt rồi nick mới gửi; vẫn giữ trần mỗi nick / mỗi nhóm và bỏ qua nhóm cấm bán hàng"
                if style == "invite" else "Từ lượt tới, bài không liên quan Bảo bình luận tự nhiên, chỉ giới thiệu nhẹ là xưởng")
    if t == "site_deploy":
        import site_deploy

        def job(via):
            try:
                if act.get("check"):
                    r = site_deploy.check()
                    followup(("Sitemap trên mạng ổn" if r["ok"] else "Sitemap còn lỗi") + (" (em đã sửa: " + "; ".join(r["fixed"]) + ")" if r.get("fixed") else "")
                             + ": " + "; ".join(f"{x['name']} {'✓' if x['ok'] else '✗'} {x['msg']}" for x in r["steps"]), via)
                    return
                if act.get("test"):
                    r = site_deploy.test()
                    followup(("Kết nối hosting ổn: " if r["ok"] else "Kết nối hosting lỗi: ")
                             + "; ".join(f"{x['name']} {'✓' if x['ok'] else '✗'} {x['msg']}" for x in r["steps"]), via)
                    return
                import website
                website.build()
                r = website.deploy()
                followup(f"Đã đẩy website lên hosting: {r['files']} tệp mới/sửa, xóa {r['deleted']} tệp cũ ({r['host']})", via)
            except Exception as e:
                followup(f"Chưa đẩy được website lên hosting: {e}", via)
        _bg(job, act.get("_via", "web"))
        if act.get("check"):
            return "Em đang mở sitemap trên tên miền như Google đọc, có lỗi sửa được thì em sửa luôn, xong em báo sếp"
        return "Em đang kiểm tra kết nối hosting, xong em báo sếp" if act.get("test") else "Em đang dựng lại website và đẩy lên hosting, xong em báo sếp"
    if t == "coach_now":
        import coach
        return coach.run(force=True)["msg"]
    if t == "cleanup_data":
        import housekeeping
        if not act.get("run"):
            return housekeeping.summary() + " Mỗi đêm em tự dọn nhật ký cũ, ảnh chụp cũ; sếp bảo “dọn dữ liệu” để dọn ngay."
        _bg(lambda via: followup(housekeeping.summary(housekeeping.run(force=True)), via), act.get("_via", "web"))
        return "Em đang dọn dữ liệu (nhật ký cũ, ảnh chụp cũ, sao lưu thừa, bộ nhớ Chrome) và nén lại, xong em báo sếp"
    if t == "update_app":
        import updater
        return updater.run(act.get("_via", "web"))
    if t == "write_posts":
        n = max(1, min(10, int(act.get("count") or 3)))
        tt = act.get("target") if act.get("target") in ("group", "profile", "page") else "group"
        pid = act.get("product_id")
        pid = int(pid) if str(pid or "").isdigit() and db.one("SELECT id FROM products WHERE id=?", (int(pid),)) else None
        _bg(_write_and_report, n, pid, tt, act.get("angle") or None, (act.get("note") or "")[:300], act.get("_via", "web"))
        prod = db.one("SELECT name FROM products WHERE id=?", (pid,))["name"] if pid else "các sản phẩm"
        return f"Giao Lan viết {n} bài {({'group': 'đăng nhóm', 'profile': 'trang cá nhân', 'page': 'Fanpage'})[tt]} về {prod}" + \
            (", viết xong em duyệt rồi cho Tuấn xếp lịch và báo lại sếp" if autopilot() else ", viết xong em báo lại sếp")
    if t == "ask":
        import knowledge
        q = (act.get("question") or "").strip()
        r = knowledge.ask("ceo", q)
        if r["source"] == "memory":
            return f"{r['answer']} (em trả lời bằng kiến thức đội đã học, không cần hỏi Claude)"
        if r["source"] == "claude":
            return f"{r['answer']} (em vừa tra cứu và đã lưu vào sổ kiến thức, lần sau tự trả lời)"
        if r["source"] == "none":
            return ("Câu này đội chưa học tới. Em đã ghi vào danh sách câu hỏi cần học, đội sẽ tìm hiểu trong buổi tự học tới "
                    "(cần có khóa Claude ở Cài đặt để tra cứu)")
        return "Em chưa tra cứu được câu này, sếp thử lại sau giúp em"
    if t == "suggest_keywords":
        import ceo_brain
        r = ceo_brain.suggest_keywords()
        if not r["ok"]:
            return "Chưa thử từ khóa mới được: " + r["why"]
        return ("Em đã cho thử: " + "; ".join(r["added"]) + (f". Vì {r['why']}" if r.get("why") else "")
                + ". Chạy thử 14 ngày, không ra SĐT thì em bỏ") if r["added"] else "Claude chưa tìm được từ khóa nào mới hơn từ khóa đang có"
    if t == "weekly_report":
        import ceo_brain
        return ceo_brain.weekly(send=act.get("_via") != "web")[:900]
    if t == "scan_fanpage":
        import ceo_brain
        r = ceo_brain.scan_fanpage()
        return (f"Đã đọc bình luận {r['posts']} bài Fanpage 7 ngày qua: {r['new']} khách mới, {r['phones']} SĐT mới"
                if r["ok"] else "Chưa đọc được Fanpage: " + r["why"])
    if t == "focus_review":
        import channel_focus
        r = channel_focus.run(force=True, notify=False)
        rv = r["review"]
        lines = [f"{c['label']}: {c['text']}" for c in rv["channels"]] or ["Chưa có khách nào trong " + str(rv["days"]) + " ngày qua"]
        tail = (f" Em đã làm: {'; '.join(r['done'])}." if r["done"] else "") + \
               (" Em đã gửi đề xuất, sếp bấm Duyệt ở trang Công ty hoặc Telegram." if r["proposed"] else "") + \
               ("" if r["done"] or r["proposed"] else " Chưa có kênh nào đủ dữ liệu để dừng hay dồn sức.")
        return f"Kênh tìm khách {rv['days']} ngày qua: " + " | ".join(lines) + "." + tail
    if t == "study_now":
        import knowledge
        import threading
        threading.Thread(target=knowledge.study_all, daemon=True).start()
        if not knowledge.self_study_on():
            return ("Đội chỉ học từ dữ liệu thật: điều sếp dạy, luật Facebook, câu sếp và khách hỏi thật. Em cho đội trả lời ngay các câu "
                    "còn chờ. Tự học kiến thức chung với Claude đang tắt vì không có dữ liệu mới, dễ đưa lời khuyên chung chung vào bài "
                    "(bật ở Đào tạo → Sổ kiến thức → Cài đặt). Sếp muốn đội biết điều gì thì dạy ở Đào tạo → Sổ kiến thức → Dạy kiến thức")
        return "Cho cả đội tự học kiến thức mới ngay bây giờ, học xong em báo lại"
    if t == "set_hot":
        p = _find_product(act.get("product_id"), act.get("product"))
        if not p:
            return "Chưa rõ sản phẩm nào. Sếp nói đúng tên sản phẩm trong mục Sản phẩm giúp em"
        on = act.get("hot", True) not in (False, 0, "0", "false")
        import products
        products.set_hot(p["id"], on, by="ceo")
        if act.get("note") is not None and on:
            db.run("UPDATE products SET hot_note=? WHERE id=?", (str(act["note"])[:200], p["id"]))
        hot = [r["name"] for r in db.q("SELECT name FROM products WHERE hot=1")]
        return (f"Đánh dấu {p['name']} đang bán chạy: Lan viết nhiều bài hơn về sản phẩm này, Hà chào sản phẩm này trước khi tư vấn khách"
                if on else f"Thôi ưu tiên {p['name']}") + (f". Đang tập trung: {', '.join(hot)}" if hot else "")
    if t == "plan":
        plan = workflows.plan_distribution()
        return f"Giao Tuấn xếp lịch: {len(plan)} bài đã có giờ đăng" if plan else "Tuấn xếp lịch: chưa có bài đã duyệt hoặc nhóm nào đủ điều kiện"
    if t == "daily_work":
        _bg(workflows.daily_work)
        return "Giao cả đội làm việc hằng ngày: Lan viết bài, Tuấn xếp lịch, Hà lọc khách cần bám"
    if t == "meeting":
        import meeting
        if meeting.is_running():
            return "Đang có cuộc họp, để họp xong đã"
        meeting.start((act.get("topic") or "").strip() or None)
        return f"Triệu tập họp{': ' + act['topic'] if act.get('topic') else ''}"
    if t == "find_groups":
        import group_finder
        kws = [k.strip() for k in (act.get("keywords") or []) if str(k).strip()]
        if kws:
            group_finder.set_today(kws)
        if not group_finder._working_sales():
            return "Chưa giao tìm nhóm được. " + why_no_sales()
        r = group_finder.start_discover(None, kws or None, notify=act.get("_via", "web"))
        return (f"Giao sale {_name('sale-' + str(r['sale_id']))} (nick {r['account']}) lướt Facebook rồi tìm nhóm theo: {', '.join(r['keywords'])}"
                f"{_busy_note(r['sale_id'])}. Tìm xong em báo lại sếp.")
    if t == "teach_mai":
        import prospect_rules
        r = prospect_rules.add_lesson(act.get("text") or "")
        sg = r["suggest"]
        n = sum(len(sg.get(k) or []) for k in ("keywords", "ads_keywords", "must", "exclude", "bonus", "groups"))
        return ("Mai đã học bài sếp dạy và ghi vào sổ kiến thức" + (f"; Mai thấy {n} điều cài được vào điều kiện tìm khách, "
                "sếp mở trang Tìm khách sỉ → Sếp dạy Mai để bấm Áp dụng" if n else ""))
    if t == "review_my_groups":
        import my_groups
        n = my_groups.start_sync(act.get("_via", "web"))
        return (f"Giao {n} nick mở danh sách nhóm đã tham gia, Tuấn đánh giá nhóm nào nên đăng, nhóm nào thoát"
                + (" (đang bật tự thoát nhóm kém)" if s().get("auto_leave", "1") == "1" else "") + ". Xong em báo lại sếp.") if n else \
            "Chưa rà soát được: " + why_no_sales()
    if t == "find_prospects":
        import group_finder
        import prospect
        if not group_finder._working_accounts():
            return "Mai chưa đi tìm khách được vì cần 1 nick sale để mở trang. " + why_no_sales()
        urls = [u for u in (act.get("urls") or []) if str(u).strip()]
        kws = [k.strip() for k in (act.get("keywords") or []) if str(k).strip()]
        dirs = [int(d) for d in (act.get("directions") or []) if str(d).isdigit() and int(d) in prospect.DIRECTIONS]
        r = prospect.start(dirs or None, kws or None, urls or None, notify=act.get("_via", "web"))
        what = f"phân tích {len(r['urls'])} link sếp gửi" if r.get("urls") else \
            ("tìm khách sỉ theo: " + ", ".join(kws) if kws else
             "tìm khách sỉ: " + "; ".join(prospect.DIRECTIONS[d].lower() for d in dirs) if dirs else
             "tìm SĐT khách sỉ: đọc bình luận nhóm, quét trang chạy quảng cáo, tìm shop livestream và trang bán hàng")
        return f"Giao Mai {what}, dùng Chrome của nick {r['account']} để xem trang công khai{_busy_note(r['sale_id'])}. Xong em báo lại sếp."
    if t == "join_groups":
        import group_finder
        if not group_finder._working_sales():
            return "Chưa giao xin vào nhóm được. " + why_no_sales()
        n = group_finder.submit_joins(act.get("_via", "web"))
        return f"Giao {n} nick xin vào các nhóm mới (sale làm lần lượt từng nick), xong em báo lại sếp" if n else \
            "Các nick đã hết lượt xin vào nhóm hôm nay (giới hạn an toàn), mai sale xin tiếp"
    if t == "scan_comments":
        import telegram_bot
        n = telegram_bot.start_scan_round(force=True)
        if not n:
            import group_finder
            return ("Chưa quét được: " + why_no_sales()) if not group_finder._working_sales() else \
                "Chưa có bài nào đã lưu link để quét bình luận (sale đăng bài xong mới có link)"
        return f"Giao sale quét bình luận {n} bài để tìm khách"
    if t == "learn_now":
        import learning
        learning.nightly_async()
        return "Cho cả đội tự xem lại và rút kinh nghiệm ngay"
    if t == "teach":
        import learning
        aid = _agent_id(str(act.get("agent") or ""))
        text = (act.get("text") or "").strip()
        if not aid or aid == "all" or len(text) < 8:
            return "Chưa rõ sửa cho agent nào hoặc nội dung quá ngắn"
        lid = learning.add_lesson(aid, text, "Sếp nhắc qua CEO", "boss", 1.0, None, 1)
        db.log(aid, "CEO yêu cầu sửa", text[:150])
        return f"Yêu cầu {_name(aid)} sửa: “{text}” (đã ghim vào sổ tay, áp dụng từ việc tiếp theo)" if lid else "Không ghi được bài học"
    if t == "order":
        aid = _agent_id(str(act.get("agent") or "all")) or "all"
        text = (act.get("text") or "").strip()
        if len(text) < 6:
            return "Chỉ đạo quá ngắn"
        oid = db.run("INSERT INTO ceo_orders(agent, text, active, source, created_at) VALUES (?,?,1,'boss',?)", (aid, text[:400], db.now()))
        db.log("ceo", "Chỉ đạo mới của sếp", f"{_name(aid)}: {text[:150]}")
        return f"Ghi chỉ đạo lâu dài #{oid} cho {_name(aid)}: “{text}”"
    if t == "cancel_order":
        oid = act.get("id")
        if str(oid or "").isdigit() and db.one("SELECT id FROM ceo_orders WHERE id=?", (int(oid),)):
            db.run("UPDATE ceo_orders SET active=0 WHERE id=?", (int(oid),))
            return f"Bỏ chỉ đạo #{oid}"
        return "Không tìm thấy chỉ đạo cần bỏ"
    if t in ("pause_sale", "resume_sale"):
        sid = _sale_id(act.get("sale_id") or act.get("sale"))
        r = db.one("SELECT * FROM sales WHERE id=?", (sid,)) if sid else None
        if not r or r.get("status") == "fired":
            return "Không tìm thấy nhân viên sale đó"
        on = t == "resume_sale"
        db.run("UPDATE sales SET auto_post=? WHERE id=?", (1 if on else 0, sid))
        if not on:
            db.run("UPDATE posts SET status='approved', sale_id=NULL, scheduled_for=NULL WHERE sale_id=? AND status='scheduled'", (sid,))
        return f"{'Bật lại' if on else 'Tạm dừng'} tự đăng của {r['name']}"
    if t == "post_keyword":
        import group_target
        raw = act.get("keyword") or act.get("keywords") or ""
        kws = group_target.words(", ".join(raw) if isinstance(raw, list) else str(raw))
        if not kws:
            return "Sếp cho em từ khóa nhóm, VD: đăng bài lên các nhóm có từ khóa trà sữa"
        kw = ", ".join(f"“{k}”" for k in kws)
        info = group_target.push_groups(kws)
        if not info["found"]:
            return (f"Chưa có nhóm nào có từ khóa {kw} trong danh sách nhóm. Sếp nhắn “tìm nhóm theo chủ đề {kws[0]}” để sale đi "
                    "tìm và xin vào nhóm trước")
        why = "; ".join(f"{k} {v}" for k, v in info["why"].items())
        if not info["ready"]:
            return f"Có {len(info['found'])} nhóm có từ khóa {kw} nhưng hôm nay chưa nhóm nào đăng được ({why})"
        ready = len(info["ready"])
        try:
            want = max(1, min(int(act.get("count") or ready), ready, 10))
        except (TypeError, ValueError):
            want = min(ready, 10)
        group_target.push_set(kws, want)
        import post_template
        approved = len(workflows.with_images(db.q("SELECT * FROM posts WHERE status='approved' AND target_type='group'"
                                                  + (" AND source='template'" if post_template.enabled() else ""))))
        head = (f"Có {len(info['found'])} nhóm có từ khóa {kw}, hôm nay đăng được {ready} nhóm"
                + (f" ({why})" if why else "") + f". Em giao đăng {want} nhóm. ")
        if approved >= want:
            return head + _push_report(workflows.plan_distribution(kws, want), kws, want)
        need = want - approved
        p = _find_product(act.get("product_id"), act.get("product") or " ".join(kws))
        _bg(_push_write, need, p["id"] if p else None, kws, want, act.get("_via", "web"))
        return head + (f"Đang có {approved} bài đã duyệt, " if approved else "Chưa có bài đã duyệt, ") + \
            f"em giao Lan viết thêm {need} bài" + (f" về {p['name']}" if p else "") + \
            (", viết xong em duyệt rồi Tuấn xếp vào các nhóm này và báo lại sếp" if autopilot() else ", viết xong sếp duyệt giúp em")
    if t == "care_posts":
        import post_care
        n = workflows.plan_bumps(force=True)
        if not n:
            import media_folder
            if not media_folder.root():
                return "Bảo chưa up được: chưa cài thư mục ảnh sản phẩm (Cài đặt → Tự động up bài)"
            return ("Bảo rà soát xong: không có bài nào cần bình luận lúc này (bài quá cũ, vừa đăng dưới 10 giờ, đã up hôm nay, "
                    "bị gỡ hoặc nick đã đủ lượt theo Luật Facebook)")
        ex = db.one("SELECT text FROM bumps ORDER BY id DESC LIMIT 1")
        return (f"Bảo rà soát bài đã đăng và xếp {n} lượt bình luận ảnh, mỗi bài một câu riêng kèm “{post_care.contact()}”. "
                f"Sale bắt đầu trong vài phút" + (f". VD: “{ex['text']}”" if ex and ex.get("text") else ""))
    if t == "focus_group":
        import group_target
        from knowledge import plain
        name = plain(str(act.get("group") or "")).strip()
        rows = [g for g in db.q("SELECT id, name FROM groups WHERE COALESCE(is_sample,0)=0") if name and name in plain(g["name"])]
        if not rows:
            return "Không tìm thấy nhóm có tên đó"
        on = str(act.get("on", True)).lower() not in ("false", "0", "no", "tắt")
        for g in rows[:5]:
            group_target.set_focus(g["id"], on)
        return f"{'Tập trung đăng' if on else 'Thôi tập trung đăng'} nhóm " + "; ".join(g["name"] for g in rows[:5])
    if t == "feed_scan":
        import group_feed
        try:
            r = group_feed.start(notify=act.get("_via", "web"))
        except ValueError as e:
            return str(e)
        return (f"{len(r['queued'])} nick đi lướt bảng tin nhóm ({', '.join(r['queued'])}), mỗi nick đọc ít nhất "
                f"{db.get_settings().get('feed_min_posts') or 20} bài. Bảo chỉ chọn người đang hỏi mua (bình luận kèm ảnh) và người đang "
                "bán hàng online (chào nhẹ kèm Zalo), không comment mọi bài vì Facebook coi là spam và khóa nick. Sếp duyệt ở trang "
                "Trả lời khách, duyệt xong nick gửi trong giờ làm, cách nhau 45–90 phút"
                + (". Chưa lướt: " + "; ".join(r["skipped"]) if r["skipped"] else ""))
    if t == "reply_customers":
        import replies
        try:
            r = replies.start(notify=act.get("_via", "web"))
        except ValueError as e:
            return str(e)
        q = replies.quota(r["account_id"])
        return (f"Nick {r['account']} đi đọc các nhóm sôi nổi nhất, Bảo chọn bài đang HỎI MUA / hỏi nguồn hàng hợp ngành và viết sẵn "
                f"câu trả lời. Sếp duyệt ở trang Trả lời khách, duyệt xong nick gửi trong giờ làm, mỗi nick tối đa {q['limit']} câu/ngày, "
                "cách nhau 45–90 phút. Không bình luận dạo, không chạy ban đêm (Facebook coi là spam, khóa nick)")
    if t == "find_friends":
        import friends
        try:
            r = friends.start(notify=act.get("_via", "web"))
        except ValueError as e:
            return str(e)
        return f"Nick {r['account']} đi đọc nhóm sôi nổi để Tuấn chọn người kết bạn (sale tự bấm gửi)"
    if t == "setting":
        k, v = act.get("key"), str(act.get("value", "")).strip()
        if k not in SETTINGS_OK:
            return f"Không được tự đổi cài đặt “{k}”"
        kind, lo, hi, label = SETTINGS_OK[k]
        if kind == "int":
            if not re.fullmatch(r"\d+", v):
                return f"Giá trị {label} phải là số"
            v = str(max(lo, min(hi, int(v))))
        elif kind == "bool":
            v = "1" if v.lower() in ("1", "true", "bật", "on", "có") else "0"
        elif kind == "time":
            if not re.fullmatch(r"\d{1,2}:\d{2}", v):
                return f"Giờ {label} phải có dạng HH:MM"
            v = v.zfill(5)
        elif kind == "choice":
            if v not in lo:
                return f"{label}: chọn một trong {', '.join(lo)}"
        elif kind == "line":
            v = re.sub(r"\s+", " ", v).strip()[:hi]
        elif kind == "text":
            import group_target
            v = ", ".join(group_target.words(v))[:hi]
        elif kind == "times":
            parts = [p.strip().zfill(5) for p in re.split(r"[,; ]+", v) if p.strip()]
            if not parts or not all(re.fullmatch(r"\d{2}:\d{2}", p) for p in parts):
                return "Giờ quét phải có dạng 11:30, 16:30"
            v = ",".join(parts)
        db.set_setting(k, v)
        db.log("ceo", "Đổi cài đặt theo lệnh sếp", f"{label}: {v}")
        return f"Đổi {label} thành {v if kind != 'bool' else ('bật' if v == '1' else 'tắt')}"
    if t == "hire":
        import ceo
        r = ceo.hire((act.get("reason") or "Sếp yêu cầu tuyển thêm").strip(), "boss")
        return f"Tuyển sale mới {r['name']}, chờ sếp đăng nhập nick" if r else "Chưa tuyển được (văn phòng đủ người hoặc công ty chưa hoạt động)"
    if t == "fire":
        import company
        sid = _sale_id(act.get("sale_id") or act.get("sale"))
        r = db.one("SELECT * FROM sales WHERE id=?", (sid,)) if sid else None
        if not r or r.get("status") == "fired":
            return "Không tìm thấy nhân viên sale đó"
        company.fire(sid, (act.get("reason") or "Sếp yêu cầu cho nghỉ").strip())
        return f"Cho {r['name']} nghỉ việc theo yêu cầu của sếp"
    if t == "task":
        aid = _agent_id(str(act.get("agent") or "minh")) or "minh"
        title = (act.get("title") or "").strip()
        if not title:
            return "Việc không có nội dung"
        db.run("INSERT INTO tasks(agent_id, title, status, due, created_at) VALUES (?,?,?,?,?)",
               (aid if aid != "all" else "minh", title[:200], "todo", db.today(), db.now()))
        return f"Giao {_name(aid)}: {title}"
    if t == "status":
        return status_text()
    return f"Không làm được việc “{t}”"


def status_text() -> str:
    import kpi
    import workflows
    st = workflows.stats()
    k = kpi.day_stats(db.today())
    parts = [f"Hôm nay {k['leads_phone']}/{k['target_min']} khách có SĐT", f"{st['drafts']} bài nháp",
             f"{st['approved']} bài đã duyệt/lên lịch", f"{st['posted_total']} bài đã đăng", f"{st['leads_new']} khách mới chưa liên hệ"]
    pr = db.one("SELECT SUM(grade='A') a, SUM(grade='B') b, SUM(status='needs_manual') m FROM prospects WHERE created_at>=?",
                (db.today(),))
    try:
        import prospect
        ch = [c for c in prospect.channels() if c["phones"]]
        if ch:
            parts.append("Khách sỉ có SĐT 7 ngày theo kênh: " + ", ".join(f"{c['label'].lower()} {c['phones']}" for c in ch))
    except Exception:
        pass
    if pr and (pr["a"] or pr["b"] or pr["m"]):
        parts.append(f"Mai tìm được {pr['a'] or 0} khách sỉ hạng A, {pr['b'] or 0} hạng B hôm nay"
                     + (f", {pr['m']} tài khoản cần sếp xem tay" if pr["m"] else ""))
    try:
        import company
        b = company.brief_text()
        if b:
            parts.append(b.replace("\n", " "))
    except Exception:
        pass
    return "; ".join(parts) + "."


# ---------------------------------------------------------------- hiểu lệnh
def _context() -> str:
    import group_finder
    prods = db.q("SELECT id, name, hot FROM products ORDER BY id")
    sales = _sales()
    od = orders()
    return json.dumps({
        "hom_nay": db.today(),
        "agents": {k: f"{__import__('agents').name_of(k)}, {v}" for k, v in {
            "minh": "trưởng phòng, chủ trì họp", "lan": "viết bài", "tuan": "chọn nhóm và xếp lịch đăng", "ha": "chăm sóc khách, soạn tin",
            "khoa": "số liệu", "mai": "tìm khách sỉ (người bán online, livestream) trên Facebook, TikTok, Shopee",
            "vy": "quản lý website công ty và viết bài chuẩn SEO",
            "bao": "rà soát bài đã đăng, cho nick bình luận ảnh kèm câu ngắn và Zalo liên hệ (up bài)"}.items()},
        "sales": [{"id": r["id"], "ten": r["name"], "nick": r["fb_name"], "dang_nhap": r["login_status"] == "ok",
                   "tu_dang": bool(r["auto_post"])} for r in sales],
        "san_pham": [{"id": p["id"], "ten": p["name"], "dang_ban_chay": bool(p["hot"])} for p in prods],
        "chu_de_tim_nhom_hom_nay": group_finder.today_keywords(),
        "chi_dao_dang_ap_dung": [{"id": o["id"], "cho": o["agent"], "noi_dung": o["text"]} for o in od[:15]],
        "cai_dat_duoc_doi": {k: f"{v[3]} (hiện: {s().get(k)})" for k, v in SETTINGS_OK.items()},
        "tinh_hinh": status_text(),
    }, ensure_ascii=False)


ACTIONS_DOC = """Các việc được phép (type và tham số):
- write_posts {count 1-10, product_id?, target: group|profile|page, angle?, note?}: giao Lan viết bài
- plan {}: giao Tuấn xếp lịch đăng các bài đã duyệt
- feed_style {style: invite|natural}: sếp muốn bình luận MỜI SỈ vào cả bài không liên quan (invite) hoặc chỉ bình luận tự nhiên (natural)
- site_deploy {test?: true, check?: true}: check true khi sếp nói sitemap / Google không đọc được website. Sếp bảo đẩy / đăng / cập nhật website lên hosting (tin tức, sản phẩm lên online); test true khi sếp hỏi kiểm tra kết nối hosting
- coach_now {}: cho các agent đủ kết quả thật mới gửi việc cho Claude kèm cặp ngay (theo lô, giảm 50%)
- cleanup_data {run: true|false}: sếp hỏi dung lượng dữ liệu (run false) hoặc bảo dọn dẹp / dọn dữ liệu / dữ liệu phình to (run true)
- update_app {}: sếp bảo cập nhật / nâng cấp phần mềm, tải bản mới (git pull) rồi tự khởi động lại khi sale rảnh
- ask {question}: sếp HỎI kiến thức/cách làm (không phải giao việc). CEO tra sổ kiến thức của đội trước, chưa có mới tra cứu
- study_now {}: cho cả đội tự học kiến thức mới ngay
- focus_review {}: xem kênh tìm khách nào ra đơn, dồn sức cho kênh ra đơn, tạm dừng kênh chỉ ra số không ra đơn
- suggest_keywords {}: CEO học chân dung khách đã mua, cho Mai thử từ khóa tìm khách mới và Tuấn thử chủ đề nhóm mới (14 ngày, không ra SĐT thì bỏ)
- weekly_report {}: viết báo cáo tuần ngay (tuần qua, nút thắt, 3 việc tuần này)
- scan_fanpage {}: đọc bình luận dưới bài Fanpage (Graph API) để lấy khách để SĐT / hỏi giá
- set_hot {product_id, hot: true|false, note?}: đánh dấu / bỏ đánh dấu sản phẩm đang bán chạy (cả đội tập trung chào mời)
- daily_work {}: cả đội làm việc hằng ngày
- meeting {topic}: triệu tập họp
- find_groups {keywords: [..]}: giao sale lướt Facebook tìm nhóm theo chủ đề
- join_groups {}: các nick xin vào nhóm mới
- teach_mai {text}: sếp dạy Mai cách/điều kiện tìm khách sỉ trên Facebook (lưu nguyên lời sếp vào text)
- review_my_groups {}: đọc danh sách nhóm nick đã tham gia sẵn, Tuấn đánh giá nhóm nào nên đăng, thoát nhóm kém
- find_prospects {keywords: [..], urls: [..], directions: [..]}: directions 5 = quét thư viện quảng cáo Facebook (trang đang chạy
  quảng cáo), 6 = đọc bài và bình luận trong nhóm tìm người hỏi nguồn hàng, 1-4 = tìm trang/shop. Mai tìm khách sỉ (người đang bán online, livestream trên Facebook/TikTok/Shopee),
  chấm điểm A/B/C/D, hạng A/B vào mục Khách hàng. urls = link sếp gửi để Mai phân tích. Không tự nhắn tin cho khách.
- scan_comments {}: sale quét bình luận tìm khách
- learn_now {}: cả đội tự rút kinh nghiệm ngay
- teach {agent: lan|tuan|ha|khoa|minh|<tên sale>, text}: sửa cách làm của MỘT agent bị sếp chê (ghi thành bài học bắt buộc,
  viết dưới dạng quy tắc cụ thể, ví dụ "Viết bài dưới 150 chữ, mở đầu bằng giá sỉ")
- order {agent: all|lan|tuan|..., text}: chỉ đạo lâu dài (từ nay trở đi luôn/không được ...)
- cancel_order {id}: bỏ một chỉ đạo
- pause_sale {sale_id} / resume_sale {sale_id}: tạm dừng / bật lại tự đăng của nick
- setting {key, value}: đổi cài đặt trong danh sách cai_dat_duoc_doi (nơi đăng: post_target_mode, post_group_keywords,
  post_group_exclude)
- post_keyword {keyword, count?, product?}: sếp bảo ĐĂNG BÀI NGAY lên các nhóm có từ khóa (một lần, hôm nay). Tuấn xếp bài đã
  duyệt vào nhóm khớp từ khóa, thiếu bài thì Lan viết thêm. Khác setting post_group_keywords (chỉ đạo lâu dài)
- care_posts {}: giao Bảo rà soát các bài đã đăng ngay bây giờ: nick đã đăng bình luận 1 ảnh + câu ngắn Bảo tự viết + dòng liên hệ
  (bump_contact). Đổi dòng liên hệ thì dùng setting bump_contact
- focus_group {group, on}: sếp bảo tập trung đăng (on=true) / thôi tập trung (on=false) vào một nhóm theo tên
- feed_scan {}: sếp bảo các nick lướt bảng tin nhóm (facebook.com/groups/feed) và comment: mọi nick đọc ít nhất 20 bài, Bảo
  chọn người HỎI MUA hợp ngành (bình luận kèm 1 ảnh) và người ĐANG BÁN HÀNG ONLINE đang hỏi chuyện khác như tài khoản quảng cáo
  (chào nhẹ chỉ chữ kèm Zalo, tối đa 2/nick/ngày, mỗi người một lần). SẾP DUYỆT, nick gửi trong giờ làm, giãn cách 45–90 phút.
  Số lượt lướt/ngày theo luật của nick. Không comment mọi bài trên feed (spam, khóa nick): nói rõ nếu sếp đòi
- reply_customers {}: sếp bảo nhân viên đi comment / trả lời khách trong nhóm: Bảo đọc nhóm sôi nổi, chọn bài người ta đang hỏi mua
  / hỏi nguồn hàng hợp ngành, viết câu trả lời (Claude viết, Bảo học dần rồi tự viết), SẾP DUYỆT, nick gửi trong giờ làm, có trần mỗi
  ngày. Không bình luận dạo vào bài không hỏi mua, không chạy 24/24 (spam, khóa nick): nói rõ điều này nếu sếp đòi
- find_friends {}: Tuấn đọc nhóm sôi nổi nhất của các nick, chuẩn bị danh sách người nên kết bạn (sale tự bấm gửi, không tự gửi)
- hire {reason}: tuyển thêm sale; fire {sale_id, reason}: cho sale nghỉ (chỉ khi sếp nói rõ)
- task {agent, title}: việc khác ghi vào danh sách việc của agent
- status {}: báo cáo tình hình
Chỉ dùng các việc trên. Không bịa số liệu. Lệnh không rõ thì không làm gì, hỏi lại sếp trong reply."""


def _llm_plan(text: str) -> dict | None:
    from agents import system_prompt
    from llm import llm
    if not llm.live:
        return None
    import ceo_brain
    sysmsg = system_prompt("ceo", s()) + "\n\n" + CEO_STYLE + "\n" + ACTIONS_DOC
    pq = ceo_brain.pending_question()
    prompt = (f"Bối cảnh công ty (JSON): {_context()}\n\n"
              f"SỐ LIỆU THẬT (đọc trước khi trả lời, chỉ dùng số có ở đây): {json.dumps(ceo_brain.data_brief(), ensure_ascii=False)}\n\n"
              f"Hội thoại gần đây giữa sếp và em (cũ → mới): {json.dumps(ceo_brain.recent_chat(), ensure_ascii=False)}\n"
              + (f"Em vừa hỏi lại sếp: “{pq.get('question')}”, các lựa chọn {pq.get('options')}. Tin sếp nhắn dưới đây có thể là câu trả lời.\n"
                 if pq else "")
              + f"\nSếp nhắn: \"{text}\"\n\n"
              'Trả về JSON: {"reply": "câu trả lời sếp", "actions": [{"type": "...", ...}], '
              '"clarify": null hoặc {"question": "1 câu hỏi lại", "options": ["2-4 lựa chọn ngắn"]}}')
    data = llm.json(sysmsg, prompt, mock=None, max_tokens=1200, task="ceo")
    if isinstance(data, dict) and isinstance(data.get("actions"), list):
        return data
    return None


CEO_STYLE = """BẠN LÀ CEO ĐỨC — làm việc như một giám đốc kinh doanh chuyên nghiệp. Sếp (chủ xưởng) chỉ giao việc cho bạn.
- Hiểu đúng ý sếp: đọc cả hội thoại gần đây. “làm tiếp”, “cái đó”, “như hôm qua” là nói về việc vừa trao đổi.
- Lệnh rõ thì làm ngay (chia việc cho agent bằng actions), không hỏi lại. Lệnh mơ hồ mà làm sai sẽ tốn công hoặc khó sửa
  (không rõ sản phẩm, số lượng, nhóm nào, ai) thì KHÔNG đoán: đặt "clarify" với 1 câu hỏi và 2–4 lựa chọn, actions để [].
- Trả lời như giám đốc: số liệu thật → nhận định (nút thắt ở đâu) → việc em đã giao / đề xuất. Không chung chung, không bịa số,
  không hứa điều agent không làm được. Ngắn: 2–5 câu, xưng em gọi sếp.
- Sếp hỏi tình hình / vì sao ít khách / nên làm gì: trả lời bằng phễu SĐT → sếp gọi → chốt, lý do không mua, kênh nào ra đơn.
- Tìm khách linh hoạt: dùng suggest_keywords khi sếp muốn tìm khách theo hướng mới hoặc khách đang ít; dùng focus_review để dồn sức kênh ra đơn.
- Luật Facebook: KHÔNG né phát hiện, không mẹo né lọc spam, không tăng số bài / lời mời / bình luận quá trần, không tự nhắn tin hay
  kết bạn hàng loạt. Sếp đòi “lách luật” thì nói thẳng lý do (nick bị khóa cả cụm) và đưa cách hợp lệ: Fanpage qua Graph API,
  chạy quảng cáo, nội dung có giá trị, nhóm đúng tệp."""


def _num(t: str, default: int) -> int:
    m = re.search(r"(\d+)", t)
    return int(m.group(1)) if m else default


FILLER = r"\b(giúp|giùm|hộ|anh|em|mình|nhé|nha|nhá|đi|thôi|cho|vài|mấy|thêm|các|những|một số|mới|ngay|luôn|hôm nay|đó|này|ạ|với)\b"
GROUP_NOUN = r"(hội nhóm|hội|nhóm|group|groups|cộng đồng)"


def _clean_kw(k: str) -> str:
    k = re.sub(FILLER, " ", k, flags=re.I)
    k = re.sub(r"[.!?]+$", "", re.sub(r"\s+", " ", k)).strip(" ,;:-")
    return k


def _keywords(t: str) -> list[str]:
    """Rút chủ đề tìm nhóm từ câu của sếp."""
    q = re.findall(r"[\"“”'‘’]([^\"“”'‘’]{3,80})[\"“”'‘’]", t)
    if q:
        return [k.strip() for k in q]
    m = re.search(r"(?:về|theo|chủ đề|từ khóa|từ khoá|keyword|key|liên quan(?: đến| tới)?|ngành|lĩnh vực|kiểu|như)\s*:?\s*(.+)$", t, re.I)
    rest = m.group(1) if m else None
    if not rest:
        m = re.search(GROUP_NOUN + r"\s+(.+)$", t, re.I)
        rest = m.group(2) if m else ""
    rest = re.sub(r"^(?:về|theo|chủ đề|từ khóa|keyword)\s*:?\s*", "", rest or "", flags=re.I)
    rest = re.split(r"(?:^|\s+)(?:rồi|sau đó|xong|để|thì|và xin|và vào)(?:\s+|$)", rest.strip(), maxsplit=1, flags=re.I)[0]
    out = [_clean_kw(k) for k in re.split(r"[,;]| và | hoặc |\+", rest)]
    return [k for k in out if len(k) >= 4][:6]


UPDATE_RX = (r"(cập nhật|cập nhập|update|nâng cấp|tải|kéo|pull)\s*(lại\s*)?(phần mềm|bản mới|code|mã nguồn|ứng dụng|app|hệ thống)"
            r"|git pull|pull code|lên bản mới|cập nhật bản mới")


def _rule_plan(text: str) -> dict:
    """Hiểu lệnh bằng mẫu câu (khi chưa có khóa AI). Một câu có thể chứa nhiều việc."""
    t = text.strip()
    low = t.lower()
    acts = []
    agent = None
    for alias, aid in _aliases().items():
        if re.search(rf"(?<!\w){re.escape(alias)}(?!\w)", low) and aid != "ceo":
            agent = aid
            break
    if not agent:
        for r in _sales():
            if re.search(rf"(?<!\w){re.escape(r['name'].lower())}(?!\w)", low):
                agent = f"sale-{r['id']}"
                break
    if re.search(r"(bình luận|comment|cmt).{0,20}(tự nhiên|nhẹ nhàng)|(đừng|không|thôi|bỏ) mời sỉ", low):
        return {"reply": "Dạ.", "actions": [{"type": "feed_style", "style": "natural"}]}
    if re.search(r"(bình luận|comment|cmt).{0,40}mời (nhập )?sỉ|mời (nhập )?sỉ.{0,30}(bình luận|comment|cmt|bài không liên quan|mọi bài)", low):
        return {"reply": "Dạ.", "actions": [{"type": "feed_style", "style": "invite"}]}
    if re.search(r"sitemap|site ?map|search console|google (không|chưa) (đọc|tìm|index)", low):
        return {"reply": "Dạ.", "actions": [{"type": "site_deploy", "check": True}]}
    if re.search(r"(kiểm tra|test|thử).{0,15}(kết nối )?(hosting|ftp)|(hosting|ftp).{0,20}(lỗi|không (kết nối|vào|đăng))", low):
        return {"reply": "Dạ.", "actions": [{"type": "site_deploy", "test": True}]}
    if re.search(r"(đẩy|đưa|đồng bộ|up|tải)\s*(lại\s*)?(website|trang web|web\b|tin tức|sản phẩm)\s*(lên|online)|"
                 r"(website|trang web|web\b).{0,20}(lên hosting|lên mạng|online)|(đăng|cập nhật)\s*(lại\s*)?(website|trang web|web\b)\s*lên", low):
        return {"reply": "Dạ.", "actions": [{"type": "site_deploy"}]}
    if re.search(r"kèm cặp|(học|chấm).{0,15}(với|bởi) claude|claude (chấm|kèm|dạy)", low):
        return {"reply": "Dạ.", "actions": [{"type": "coach_now"}]}
    if re.search(r"dọn\s*(dẹp\s*)?(lại\s*)?(dữ liệu|database|cơ sở dữ liệu|csdl|bộ nhớ|ổ đĩa|ổ cứng|máy)|nén (lại )?(dữ liệu|database)", low):
        return {"reply": "Dạ em dọn ngay.", "actions": [{"type": "cleanup_data", "run": True}]}
    if re.search(r"dung lượng|(dữ liệu|database|cơ sở dữ liệu).{0,20}(nặng|to|phình|lớn|bao nhiêu)", low):
        return {"reply": "Dạ.", "actions": [{"type": "cleanup_data", "run": False}]}
    if re.search(UPDATE_RX, low):
        return {"reply": "Dạ em cập nhật phần mềm ngay.", "actions": [{"type": "update_app"}]}
    for rx, typ in ((r"báo cáo tuần|tổng kết tuần", "weekly_report"),
                    (r"(bình luận|comment).{0,20}fanpage|fanpage.{0,20}(bình luận|comment|khách)", "scan_fanpage")):
        if re.search(rx, low):  # việc riêng của CEO: khớp trước các mẫu chung “báo cáo”, “bình luận”
            return {"reply": "Dạ em làm ngay.", "actions": [{"type": typ}]}
    critique = re.search(r"\b(sai|không đúng|chưa đúng|dài quá|quá dài|ngắn quá|quá ngắn|kém|tệ|đừng|không được|phải|nên|"
                         r"cấm|nhầm|lỗi|chán|nhạt|sửa|làm ẩu|lặp lại|trùng)\b", low)
    want_find = re.search(r"\b(tìm|kiếm|săn|lùng|search|khám phá)\b.{0,30}?" + GROUP_NOUN, low) or \
        re.search(GROUP_NOUN + r"\s+mới\b", low)
    want_join = re.search(r"\b(xin|gia nhập|tham gia|join|vào)\b\s*(thêm\s*|các\s*|những\s*)?" + GROUP_NOUN, low)
    want_write = re.search(r"\b(viết|soạn|làm|lên|tạo)\s*(thêm\s*)?(\d+)?\s*(bài|content|nội dung|post)", low)
    want_plan = re.search(r"xếp lịch|lên lịch|sắp lịch|lịch đăng|đăng bài\b(?!.*viết)", low)
    how_q = re.match(r"(làm sao|làm thế nào|làm cách nào|cách nào|tại sao|vì sao|có nên|nên làm gì|thế nào là)\b", low)
    want_status = re.search(r"tình hình|báo cáo|thế nào|ra sao|bao nhiêu khách|đang làm gì|làm được gì", low) and not how_q
    want_hot = re.search(r"bán chạy|đẩy mạnh|tập trung (bán|chào|đẩy)|ưu tiên (bán|chào)|(thôi|bỏ|ngừng|dừng) (ưu tiên|đẩy|tập trung)|"
                         r"sản phẩm (hot|chủ lực)|đang hot", low)
    links = re.findall(r"https?://\S+", t)
    for pf, key in (("tiktok|tik tok", "prospect_tiktok"), ("shopee|shoppe|shope", "prospect_shopee")):
        m = re.search(rf"\b(bật|mở|cho (?:chạy|tìm)|tắt|dừng|ngừng|thôi|bỏ)\b[^.?!]{{0,25}}?\b({pf})\b", low)
        if m and not links:
            acts.append({"type": "setting", "key": key, "value": "0" if m.group(1) in ("tắt", "dừng", "ngừng", "thôi", "bỏ") else "1"})
    want_prospect = (re.search(r"\b(tìm|kiếm|săn|lùng|phân tích|xem|đánh giá|chấm điểm)\b.{0,25}?(khách sỉ|khách nhập|người bán|"
                               r"người livestream|nhà bán|shop|đại lý|khách tiềm năng)", low) or
                     (agent == "mai" and re.search(r"\b(tìm|kiếm|săn|phân tích|xem)\b", low)) or
                     (links and re.search(r"tiktok|shopee|facebook\.com/(?!groups)", " ".join(links)) and not want_join))
    if m := re.search(r"\b(bật|mở|tắt|dừng|ngừng|thôi)\b.{0,12}tự\s*(động\s*)?(thoát|rời)\s*nhóm", low):
        acts.append({"type": "setting", "key": "auto_leave", "value": "0" if m.group(1) in ("tắt", "dừng", "ngừng", "thôi") else "1"})
    want_review_groups = re.search(r"(rà soát|xem lại|đánh giá|dọn|thoát|rời)\s*(các\s*)?(nhóm|group)", low) and not want_find
    want_ads = re.search(r"(quét|tìm|xem|soi)\b.{0,25}(quảng cáo|chạy ads|chạy quảng cáo|thư viện quảng cáo)", low)
    want_demand = re.search(r"(bình luận|comment|cmt|bài)\s*(trong|ở|của)\s*(các\s*)?(nhóm|group|hội)|hỏi nguồn|tìm nguồn hàng|cần nhập hàng", low)
    teach_mai = re.search(r"\b(dạy|hướng dẫn|chỉ)\s+(cho\s+)?mai\b|\bmai\s+(học|nhớ|ghi nhớ)\b|điều kiện tìm khách", low)
    want_friends = re.search(r"kết bạn|add (bạn|friend)|thêm bạn", low)
    want_care = re.search(r"(rà soát|comment|bình luận|cmt|up)\s*(lại\s*)?(vào\s*|cho\s*)?(các\s*|những\s*|mấy\s*)?(bài|post)\s*(viết\s*)?(đã|vừa)\s*đăng"
                          r"|\bup (lại )?(các |những )?bài\b", low)
    want_reply = (not want_care) and re.search(r"(comment|bình luận|cmt|trả lời|rep)\b.{0,60}(nhóm|group|hội|người hỏi|bài hỏi|hỏi mua)"
                                               r"|tìm (bài|người) hỏi (mua|nguồn|hàng)", low)
    want_feed = re.search(r"(lướt|đọc|quét)\s*(feed|bảng tin)|groups/feed|bảng tin (các )?nhóm|feed (các )?nhóm", low)
    zalo = re.search(r"(?:dòng liên hệ|liên hệ|zalo)[^0-9]{0,30}(0\d{9})", low)
    if zalo and re.search(r"đổi|thay|sửa|dùng|từ nay", low):
        acts.append({"type": "setting", "key": "bump_contact", "value": f"Cần hàng liên hệ Zalo {zalo.group(1)}"})
    tgt = re.search(r"\b(chỉ|ưu tiên|tập trung|không|đừng|cấm|tránh)\s+(đăng|post)\s*(bài\s*)?(ở|vào|lên|trong|tại)?\s*(các\s*)?"
                    r"(nhóm|group|hội)\s*(có\s*)?(từ khóa|tên|chữ|về)?\s*[:“\"']?\s*(.+)", low)
    if tgt and not want_friends:
        how, what = tgt.group(1), re.sub(r"[”\"'.!?]+$", "", tgt.group(9)).strip()
        kws = [w.strip() for w in re.split(r",|;| và | hoặc ", what) if w.strip()][:8]
        import group_target
        cur = group_target.settings()
        from knowledge import plain
        named = [g for g in db.q("SELECT id, name FROM groups WHERE COALESCE(is_sample,0)=0")
                 if len(plain(what)) >= 6 and plain(what) in plain(g["name"])]
        if how in ("không", "đừng", "cấm", "tránh"):
            acts.append({"type": "setting", "key": "post_group_exclude", "value": ", ".join(cur["exclude"] + kws)})
        elif named and how == "tập trung":
            acts.append({"type": "focus_group", "group": what, "on": True})
            if cur["mode"] == "all":
                acts.append({"type": "setting", "key": "post_target_mode", "value": "prefer"})
        else:
            acts.append({"type": "setting", "key": "post_group_keywords", "value": ", ".join(cur["include"] + kws)})
            acts.append({"type": "setting", "key": "post_target_mode", "value": "only" if how == "chỉ" else "prefer"})
    kwp = None if tgt else re.search(r"(đăng|post)\s*(\d+\s*)?(bài\s*)?(viết\s*)?(ngay\s*)?(lên|vào|ở|trong|tại|cho)\s*(các\s*|những\s*|mấy\s*)?"
                                      r"(nhóm|group|hội)\s*(có\s*)?(từ khóa|tên|chữ|về|liên quan( tới| đến)?)?\s*[:“\"']?\s*(.+)", low)
    if kwp and (len(low[:kwp.start()].split()) > 6 or re.search(r"không|đừng|chưa|sao|bị|vì|lúc", low[:kwp.start()])
                or low.rstrip().endswith("?") or re.search(r"\bbị\b|tại sao|vì sao|hôm qua|lúc nãy|đã đăng|bài đăng", low)):
        kwp = None  # "đăng" nằm giữa câu kể / câu hỏi, không phải lệnh
    if kwp and not want_friends:
        what = re.sub(r"[”\"'.!?]+$", "", kwp.group(12)).strip()
        what = re.sub(r"\s+(ngay|luôn|hôm nay|nhé|nha|giúp|giùm)(\s.*)?$", "", what).strip()
        n = re.search(r"(\d+)\s*(bài|nhóm)", low)
        kws = [w.strip() for w in re.split(r",|;| và | hoặc ", what) if w.strip()][:8]
        if kws:
            acts.append({"type": "post_keyword", "keyword": ", ".join(kws), "count": int(n.group(1)) if n else None})
    if acts and all(a["type"] in ("setting", "focus_group", "post_keyword") for a in acts):
        pass
    elif want_feed and not want_friends:
        acts.append({"type": "feed_scan"})
    elif want_care and not want_friends:
        acts.append({"type": "care_posts"})
    elif want_reply and not want_friends:
        acts.append({"type": "reply_customers"})
    elif want_friends:
        acts.append({"type": "find_friends"})
    elif teach_mai:
        acts.append({"type": "teach_mai", "text": t})
    elif want_review_groups and not links:
        acts.append({"type": "review_my_groups"})
    elif (want_ads or want_demand) and not want_write and not want_find:
        acts.append({"type": "find_prospects", "urls": [], "keywords": [],
                     "directions": ([5] if want_ads else []) + ([6] if want_demand else [])})
    elif want_prospect and not want_find:
        acts.append({"type": "find_prospects", "urls": links, "keywords": []})
    elif want_hot and not want_write and (hp := _product_in(t)):
        off = re.search(r"(thôi|bỏ|hết|không còn|ngừng|dừng)\s*(đánh dấu\s*)?(ưu tiên|bán chạy|đẩy|tập trung|hot)", low)
        acts.append({"type": "set_hot", "product_id": hp["id"], "hot": not off})
    elif want_status and not critique and not (want_find or want_write or want_plan):
        acts.append({"type": "status"})
    elif agent and critique and not want_find and not re.search(r"(viết|soạn|làm|tạo)\s*(thêm\s*)?\d+\s*(bài|content|post)", low):
        acts.append({"type": "teach", "agent": agent, "text": t})  # sếp chê một agent -> sửa cách làm của agent đó
    else:
        if want_find:
            acts.append({"type": "find_groups", "keywords": _keywords(t)})
        if want_join and not want_find:
            acts.append({"type": "join_groups"})
        if want_write:
            n = int(want_write.group(3)) if want_write.group(3) else 3
            pid = None
            for p in db.q("SELECT id, name FROM products"):
                words = [w for w in p["name"].lower().split() if len(w) > 2][:3]
                if words and sum(w in low for w in words) >= min(2, len(words)):
                    pid = p["id"]
                    break
            tt = "profile" if "trang cá nhân" in low else "page" if "fanpage" in low else "group"
            acts.append({"type": "write_posts", "count": n, "product_id": pid, "target": tt, "note": t})
        elif want_plan:
            acts.append({"type": "plan"})
        if re.search(r"\bhọp\b|triệu tập", low) and not acts:
            topic = re.sub(r".*?(\bhọp\b|triệu tập)\s*(về|bàn|chủ đề)?\s*:?\s*", "", t, count=1, flags=re.I).strip()
            acts.append({"type": "meeting", "topic": topic})
        if re.search(r"quét|(đọc|xem|check)\s+(bình luận|comment|cmt)", low):
            acts.append({"type": "scan_comments"})
        if agent and agent.startswith("sale-") and re.search(r"tạm dừng|dừng đăng|ngừng đăng|nghỉ đăng", low):
            acts.append({"type": "pause_sale", "sale_id": int(agent[5:])})
        if agent and agent.startswith("sale-") and re.search(r"bật lại|cho đăng lại|tiếp tục đăng|chạy lại", low):
            acts.append({"type": "resume_sale", "sale_id": int(agent[5:])})
        if re.search(r"tự học|rút kinh nghiệm", low):
            acts.append({"type": "learn_now"})
        if re.search(r"làm việc (hằng|hàng) ngày|bắt đầu làm việc|vào việc", low) and not acts:
            acts.append({"type": "daily_work"})
        if m := re.search(r"tuyển\s*(thêm)?\s*(\d+)?\s*(sale|nhân viên)", low):
            for _ in range(min(3, int(m.group(2) or 1))):
                acts.append({"type": "hire", "reason": t})
        if not acts and re.search(r"\b(từ nay|từ giờ|từ bây giờ|luôn luôn|bắt buộc|cấm|không được|đừng bao giờ|mỗi bài|bài nào cũng|mọi bài)\b", low):
            acts.append({"type": "order", "agent": agent or "all", "text": t})
        if not acts and re.search(r"báo cáo tuần|tổng kết tuần", low):
            acts.append({"type": "weekly_report"})
        if not acts and re.search(r"từ khóa (mới|khác)|tìm khách (theo )?(hướng|cách) (mới|khác)|tìm khách linh hoạt|đổi cách tìm khách", low):
            acts.append({"type": "suggest_keywords"})
        if not acts and re.search(r"(bình luận|comment).{0,20}fanpage|fanpage.{0,20}(bình luận|comment|khách)", low):
            acts.append({"type": "scan_fanpage"})
        if not acts and re.search(r"kênh nào (ra|có) (đơn|khách)|dồn sức|tập trung (vào )?kênh|xem lại (các )?kênh|kênh (nào )?hiệu quả", low):
            acts.append({"type": "focus_review"})
        if re.search(r"(học|tìm hiểu)\s*(thêm\s*)?(kiến thức|cái mới|điều mới)", low) and not acts:
            acts.append({"type": "study_now"})
        if not acts and (t.rstrip().endswith("?") or re.match(r"(làm sao|làm thế nào|làm cách nào|cách nào|tại sao|vì sao|có nên|"
                                                                r"nên làm gì|thế nào là|là gì|bao nhiêu|khi nào|ở đâu|hỏi)\b", low)):
            acts.append({"type": "ask", "question": t})
        if not acts and agent and critique:
            acts.append({"type": "teach", "agent": agent, "text": t})
        if not acts and agent:
            acts.append({"type": "task", "agent": agent, "title": t})
    if acts and all(a["type"] == "status" for a in acts):
        reply = "Dạ sếp, tình hình hôm nay:"
    elif acts and all(a["type"] == "ask" for a in acts):
        reply = "Dạ sếp,"
    elif acts:
        reply = "Dạ em nhận việc."
    else:
        reply = ("Dạ em chưa hiểu rõ việc này nên chưa giao cho ai. Sếp nói cụ thể hơn giúp em, ví dụ: “Tìm hội nhóm chạy quảng cáo "
                 "facebook”, “Viết 3 bài về trà gừng”, “Xếp lịch đăng bài”, “Lan viết dài quá, viết ngắn lại”.")
    return {"reply": reply, "actions": acts}


def handle(text: str, via: str = "web") -> dict:
    """Sếp giao việc cho CEO. Trả về lời CEO và các việc đã làm."""
    text = (text or "").strip()[:1500]
    if not text:
        raise ValueError("Sếp chưa nhập việc")
    _say("boss", text, via=via)
    plan = None
    if re.search(UPDATE_RX, text.lower()) and len(text) < 120:
        plan = _rule_plan(text)
    try:
        plan = plan or _llm_plan(text)
    except Exception as e:
        print("[ceo_orders]", e)
    if not plan or (not plan.get("actions") and not plan.get("clarify")):  # CEO hỏi lại thì không đoán bằng mẫu câu
        rp = _rule_plan(text)
        if rp["actions"] or not plan:
            plan = rp
    done = []
    for a in (plan.get("actions") or [])[:6]:
        if not isinstance(a, dict) or not a.get("type"):
            continue
        try:
            a["_via"] = via
            res = execute(a)
        except Exception as e:
            import errors
            errors.report_exc("api", f"CEO làm việc “{a.get('type')}” bị lỗi", e)
            res = f"Lỗi khi làm “{a.get('type')}”: {str(e)[:120]}"
        done.append({"type": a["type"], "result": res})
    cl = plan.get("clarify") if isinstance(plan.get("clarify"), dict) else None
    if cl and cl.get("question") and not done:
        opts = [str(o)[:80] for o in (cl.get("options") or []) if str(o).strip()][:4]
        q = str(cl["question"])[:300]
        reply = ((plan.get("reply") or "").strip() + "\n" if plan.get("reply") else "") + q
        mid = _say("ceo", reply, [{"type": "clarify", "question": q, "options": opts}], via=via)
        if via == "telegram" and opts:
            try:
                import telegram_bot
                telegram_bot.send("👔 <b>CEO Đức:</b> " + telegram_bot.e(reply),
                                  buttons=[[{"text": o[:40], "callback_data": f"q:{mid}:{i}"}] for i, o in enumerate(opts)])
                return {"reply": reply, "actions": [], "clarify": {"question": q, "options": opts}, "sent": True}
            except Exception as ex:
                print("[ceo_orders]", ex)
        return {"reply": reply, "actions": [], "clarify": {"question": q, "options": opts}}
    reply = (plan.get("reply") or "Dạ em nhận việc.").strip()
    if done and all(d["result"].startswith(("Chưa", "Không")) for d in done) and reply.startswith("Dạ em nhận việc"):
        reply = "Dạ, việc này em chưa làm được ngay:"
    if done:
        reply += "\n" + "\n".join(f"• {d['result']}" for d in done)
    _say("ceo", reply, done, via=via)
    db.log("ceo", "Nhận việc từ sếp", text[:150])
    if via != "telegram" and done:  # sếp giao trên phần mềm: CEO cũng báo qua Telegram những gì đã làm
        try:
            import telegram_bot
            if telegram_bot.report_enabled():
                telegram_bot.send(f"👔 <b>Sếp giao trên phần mềm:</b> {telegram_bot.e(text[:300])}\n\n<b>CEO Đức:</b> {telegram_bot.e(reply)}")
        except Exception as ex:
            print("[ceo_orders]", ex)
    return {"reply": reply, "actions": done}


# ---------------------------------------------------------------- tự vận hành: CEO duyệt bài
def review_post(p: dict) -> tuple[bool, str]:
    """CEO chấm bài theo những gì đã học (bài mẫu của sếp, quy định, những lần sếp sửa bài): xem ceo_review.py."""
    import ceo_review
    sample = db.one("SELECT content FROM post_samples WHERE id=?", (p["sample_id"],)) if p.get("sample_id") else None
    rv = ceo_review.review(f"{p.get('content') or ''}\n{p.get('hashtags') or ''}", p["id"], (sample or {}).get("content"))
    ceo_review.save(p["id"], rv)
    if rv["ok"]:
        return True, ""
    return False, ceo_review.note(rv)


def _review_post_old(p: dict) -> tuple[bool, str]:
    text = f"{p.get('content') or ''}\n{p.get('hashtags') or ''}"
    words = len(text.split())
    if REVIEW_BAD.search(text):
        return False, "Hứa công dụng quá đà"
    if words < 35:
        return False, "Quá ngắn"
    if words > 380:
        return False, "Quá dài"
    head = re.sub(r"\W+", " ", (p.get("content") or "").lower())[:150]
    since = (db.clock() - timedelta(days=30)).strftime("%Y-%m-%d")
    for o in db.q("""SELECT content FROM posts WHERE id!=? AND status IN ('approved','scheduled','posting','posted')
                     AND created_at >= ?""", (p["id"], since)):
        if head and re.sub(r"\W+", " ", (o["content"] or "").lower())[:150] == head:
            return False, "Trùng bài cũ"
    return True, ""


def _apply_review(p: dict, good: bool, why: str):
    import learning
    if good:
        db.run("UPDATE posts SET status='approved' WHERE id=?", (p["id"],))
        learning.record_feedback(p["id"], "approve", p.get("content") or "", by="ceo")
        learning.award("lan", 8, "Bài được CEO duyệt")
    else:
        db.run("UPDATE posts SET status='rejected' WHERE id=?", (p["id"],))
        learning.record_feedback(p["id"], "reject", p["content"], "", why, by="ceo")


def review_drafts() -> dict:
    import learning
    import workflows
    cutoff = (db.clock() - timedelta(minutes=2)).strftime("%Y-%m-%d %H:%M:%S")
    ok = bad = 0
    for p in db.q("SELECT * FROM posts WHERE status='draft' AND created_at <= ? ORDER BY id LIMIT 20", (cutoff,)):
        good, why = review_post(p)
        _apply_review(p, good, why)
        if good:
            ok += 1
        else:
            bad += 1
    if ok or bad:
        db.log("ceo", "Duyệt bài", f"Duyệt {ok} bài, loại {bad} bài" + (" (lý do được ghi để Lan rút kinh nghiệm)" if bad else ""))
        if ok:
            workflows.plan_distribution()
    return {"approved": ok, "rejected": bad}


def tick():
    """Gọi từ lịch tự động mỗi 30 giây."""
    if not autopilot():
        return
    try:
        review_drafts()
    except Exception as e:
        import errors
        errors.report_exc("scheduler", "CEO duyệt bài bị lỗi", e)


def overview() -> dict:
    import browser_poster
    running = []
    for r in _sales():
        b = browser_poster.busy(r["id"])
        if b:
            running.append(f"{r['name']}: {JOB_TXT.get(b, b)}" + (f" (+{browser_poster.queued(r['id']) - 1} việc chờ)"
                                                                     if browser_poster.queued(r["id"]) > 1 else ""))
    return {"autopilot": autopilot(), "history": history(), "orders": orders(), "running": running,
            "suggestions": ["Tình hình hôm nay thế nào?", "Vì sao tuần này ít khách mua?", "Báo cáo tuần",
                            "Tìm khách theo hướng mới giống khách đã mua", "Kênh nào ra đơn?", "Đăng bài lên các nhóm có từ khóa nguồn hàng, bán hàng online", "Viết 3 bài về trà gừng mật ong", "Xếp lịch đăng nhóm",
                            "Tìm nhóm theo chủ đề “hội chạy quảng cáo facebook”", "Lan viết bài dài quá, viết dưới 150 chữ",
                            "Từ nay bài nào cũng nhắc giao hàng toàn quốc"]}

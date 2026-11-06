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

AGENT_ALIASES = {"minh": "minh", "lan": "lan", "tuan": "tuan", "tuấn": "tuan", "ha": "ha", "hà": "ha", "khoa": "khoa", "mai": "mai", "vy": "vy",
                 "đức": "ceo", "duc": "ceo", "ceo": "ceo", "trưởng phòng": "minh"}
SETTINGS_OK = {
    "posts_per_day": ("int", 1, 20, "số bài Lan viết mỗi ngày"), "kpi_min": ("int", 1, 50, "KPI tối thiểu khách có SĐT/ngày"),
    "kpi_max": ("int", 1, 100, "KPI phấn đấu"), "scan_times": ("times", 0, 0, "giờ quét bình luận"),
    "discover_time": ("time", 0, 0, "giờ đi tìm nhóm"), "join_per_nick_day": ("int", 0, 5, "số nhóm xin vào/nick/ngày"),
    "discover_add_per_day": ("int", 0, 30, "số nhóm tự thêm/ngày"), "images_min": ("int", 0, 6, "số ảnh tối thiểu mỗi bài"),
    "images_max": ("int", 1, 10, "số ảnh tối đa mỗi bài"), "bump_time": ("time", 0, 0, "giờ up bài"),
    "meeting_time": ("time", 0, 0, "giờ họp sáng"), "auto_meeting": ("bool", 0, 0, "tự họp mỗi sáng"),
    "bump_enabled": ("bool", 0, 0, "tự up bài"), "scan_enabled": ("bool", 0, 0, "tự quét bình luận"),
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
    if n in AGENT_ALIASES:
        return AGENT_ALIASES[n]
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
    if t == "study_now":
        import knowledge
        import threading
        threading.Thread(target=knowledge.study_all, daemon=True).start()
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
        "agents": {"minh": "Minh, trưởng phòng, chủ trì họp", "lan": "Lan, viết bài", "tuan": "Tuấn, chọn nhóm và xếp lịch đăng",
                   "ha": "Hà, chăm sóc khách, soạn tin", "khoa": "Khoa, số liệu", "mai": "Mai, tìm khách sỉ (người bán online, livestream) trên Facebook, TikTok, Shopee",
                   "vy": "Vy, quản lý website công ty và viết bài chuẩn SEO"},
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
- ask {question}: sếp HỎI kiến thức/cách làm (không phải giao việc). CEO tra sổ kiến thức của đội trước, chưa có mới tra cứu
- study_now {}: cho cả đội tự học kiến thức mới ngay
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
- focus_group {group, on}: sếp bảo tập trung đăng (on=true) / thôi tập trung (on=false) vào một nhóm theo tên
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
    sysmsg = system_prompt("ceo", s()) + "\n\nBạn là CEO, sếp (chủ xưởng) chỉ giao việc cho bạn. Bạn tự chia việc cho các agent.\n" + ACTIONS_DOC
    prompt = (f"Bối cảnh công ty (JSON): {_context()}\n\nSếp nhắn: \"{text}\"\n\n"
              'Trả về JSON: {"reply": "1-3 câu trả lời sếp, xưng em gọi sếp", "actions": [{"type": "...", ...}]}')
    data = llm.json(sysmsg, prompt, mock=None, max_tokens=700, task="ceo")
    if isinstance(data, dict) and isinstance(data.get("actions"), list):
        return data
    return None


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


def _rule_plan(text: str) -> dict:
    """Hiểu lệnh bằng mẫu câu (khi chưa có khóa AI). Một câu có thể chứa nhiều việc."""
    t = text.strip()
    low = t.lower()
    acts = []
    agent = None
    for alias, aid in AGENT_ALIASES.items():
        if re.search(rf"(?<!\w){re.escape(alias)}(?!\w)", low) and aid != "ceo":
            agent = aid
            break
    if not agent:
        for r in _sales():
            if re.search(rf"(?<!\w){re.escape(r['name'].lower())}(?!\w)", low):
                agent = f"sale-{r['id']}"
                break
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
    try:
        plan = _llm_plan(text)
    except Exception as e:
        print("[ceo_orders]", e)
    if not plan or not plan.get("actions"):
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
        learning.record_feedback(p["id"], "approve")
        learning.award("lan", 8, "Bài được CEO duyệt")
    else:
        db.run("UPDATE posts SET status='rejected' WHERE id=?", (p["id"],))
        learning.record_feedback(p["id"], "reject", p["content"], "", why)


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
            "suggestions": ["Tình hình hôm nay thế nào?", "Đăng bài lên các nhóm có từ khóa nguồn hàng, bán hàng online", "Viết 3 bài về trà gừng mật ong", "Xếp lịch đăng nhóm",
                            "Tìm nhóm theo chủ đề “hội chạy quảng cáo facebook”", "Lan viết bài dài quá, viết dưới 150 chữ",
                            "Từ nay bài nào cũng nhắc giao hàng toàn quốc"]}

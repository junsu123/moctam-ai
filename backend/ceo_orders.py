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

AGENT_ALIASES = {"minh": "minh", "lan": "lan", "tuan": "tuan", "tuấn": "tuan", "ha": "ha", "hà": "ha", "khoa": "khoa",
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


def execute(act: dict) -> str:
    """Thực hiện một việc trong danh sách được phép. Trả về một câu mô tả kết quả."""
    import workflows
    t = act.get("type")
    if t == "write_posts":
        n = max(1, min(10, int(act.get("count") or 3)))
        tt = act.get("target") if act.get("target") in ("group", "profile", "page") else "group"
        pid = act.get("product_id")
        pid = int(pid) if str(pid or "").isdigit() and db.one("SELECT id FROM products WHERE id=?", (int(pid),)) else None
        _bg(workflows.generate_posts, n, pid, tt, act.get("angle") or None, (act.get("note") or "")[:300])
        prod = db.one("SELECT name FROM products WHERE id=?", (pid,))["name"] if pid else "các sản phẩm"
        return f"Giao Lan viết {n} bài {({'group': 'đăng nhóm', 'profile': 'trang cá nhân', 'page': 'Fanpage'})[tt]} về {prod}" + \
            (" (CEO sẽ duyệt rồi cho Tuấn xếp lịch)" if autopilot() else "")
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
        try:
            r = group_finder.start_discover(None, kws or None)
            return f"Giao sale {_name('sale-' + str(r['sale_id']))} lướt Facebook rồi tìm nhóm: {', '.join(r['keywords'])}"
        except ValueError as e:
            return f"Chưa tìm nhóm được: {e}"
    if t == "join_groups":
        import browser_poster
        import group_finder
        ss = group_finder._working_sales()
        for x in ss:
            browser_poster.submit(x["id"], {"kind": "join"})
        return f"Giao {len(ss)} nick xin vào các nhóm mới" if ss else "Chưa có nick nào đăng nhập để xin vào nhóm"
    if t == "scan_comments":
        import telegram_bot
        n = telegram_bot.start_scan_round(force=True)
        return f"Giao sale quét bình luận {n or 0} bài để tìm khách"
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
    prods = db.q("SELECT id, name FROM products ORDER BY id")
    sales = _sales()
    od = orders()
    return json.dumps({
        "hom_nay": db.today(),
        "agents": {"minh": "Minh, trưởng phòng, chủ trì họp", "lan": "Lan, viết bài", "tuan": "Tuấn, chọn nhóm và xếp lịch đăng",
                   "ha": "Hà, chăm sóc khách, soạn tin", "khoa": "Khoa, số liệu"},
        "sales": [{"id": r["id"], "ten": r["name"], "nick": r["fb_name"], "dang_nhap": r["login_status"] == "ok",
                   "tu_dang": bool(r["auto_post"])} for r in sales],
        "san_pham": [{"id": p["id"], "ten": p["name"]} for p in prods],
        "chu_de_tim_nhom_hom_nay": group_finder.today_keywords(),
        "chi_dao_dang_ap_dung": [{"id": o["id"], "cho": o["agent"], "noi_dung": o["text"]} for o in od[:15]],
        "cai_dat_duoc_doi": {k: f"{v[3]} (hiện: {s().get(k)})" for k, v in SETTINGS_OK.items()},
        "tinh_hinh": status_text(),
    }, ensure_ascii=False)


ACTIONS_DOC = """Các việc được phép (type và tham số):
- write_posts {count 1-10, product_id?, target: group|profile|page, angle?, note?}: giao Lan viết bài
- plan {}: giao Tuấn xếp lịch đăng các bài đã duyệt
- daily_work {}: cả đội làm việc hằng ngày
- meeting {topic}: triệu tập họp
- find_groups {keywords: [..]}: giao sale lướt Facebook tìm nhóm theo chủ đề
- join_groups {}: các nick xin vào nhóm mới
- scan_comments {}: sale quét bình luận tìm khách
- learn_now {}: cả đội tự rút kinh nghiệm ngay
- teach {agent: lan|tuan|ha|khoa|minh|<tên sale>, text}: sửa cách làm của MỘT agent bị sếp chê (ghi thành bài học bắt buộc,
  viết dưới dạng quy tắc cụ thể, ví dụ "Viết bài dưới 150 chữ, mở đầu bằng giá sỉ")
- order {agent: all|lan|tuan|..., text}: chỉ đạo lâu dài (từ nay trở đi luôn/không được ...)
- cancel_order {id}: bỏ một chỉ đạo
- pause_sale {sale_id} / resume_sale {sale_id}: tạm dừng / bật lại tự đăng của nick
- setting {key, value}: đổi cài đặt trong danh sách cai_dat_duoc_doi
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


def _rule_plan(text: str) -> dict:
    """Hiểu lệnh bằng mẫu câu (khi chưa có khóa AI)."""
    t = text.strip()
    low = t.lower()
    acts = []
    agent = None
    for alias, aid in AGENT_ALIASES.items():
        if re.search(rf"\b{re.escape(alias)}\b", low) and aid != "ceo":
            agent = aid
            break
    if not agent:
        for r in _sales():
            if re.search(rf"\b{re.escape(r['name'].lower())}\b", low):
                agent = f"sale-{r['id']}"
                break
    critique = re.search(r"\b(sai|không đúng|chưa đúng|dài quá|quá dài|ngắn quá|quá ngắn|kém|tệ|đừng|không được|phải|nên|"
                         r"cấm|nhầm|lỗi|chán|nhạt|sửa)\b", low)
    if re.search(r"tình hình|báo cáo|thế nào|ra sao|bao nhiêu khách", low) and not critique:
        acts.append({"type": "status"})
    elif agent and critique and not re.search(r"^\s*(cho|bảo|giao)?\s*\w+\s+viết\s*\d+\s*bài", low):
        acts.append({"type": "teach", "agent": agent, "text": t})  # sếp chê một agent -> sửa cách làm của agent đó
    elif m := re.search(r"viết\s*(\d+)?\s*bài", low):
        n = int(m.group(1)) if m.group(1) else 3
        pid = None
        for p in db.q("SELECT id, name FROM products"):
            words = [w for w in p["name"].lower().split() if len(w) > 2][:3]
            if words and sum(w in low for w in words) >= min(2, len(words)):
                pid = p["id"]
                break
        tt = "profile" if "trang cá nhân" in low else "page" if "fanpage" in low else "group"
        acts.append({"type": "write_posts", "count": n, "product_id": pid, "target": tt, "note": t})
    elif re.search(r"xếp lịch|lên lịch", low):
        acts.append({"type": "plan"})
    elif re.search(r"\bhọp\b", low):
        topic = re.sub(r".*?\bhọp\b\s*(về|bàn|chủ đề)?\s*:?\s*", "", t, count=1, flags=re.I).strip()
        acts.append({"type": "meeting", "topic": topic})
    elif re.search(r"tìm (hội )?nhóm", low):
        kws = re.findall(r"[\"“”']([^\"“”']{3,60})[\"“”']", t)
        if not kws:
            m = re.search(r"tìm (?:hội )?nhóm\s*(?:theo|về|chủ đề|từ khóa|keyword)?\s*:?\s*(.+)$", t, re.I)
            kws = [k.strip() for k in re.split(r"[,;]| và ", m.group(1)) if len(k.strip()) > 3] if m and m.group(1).strip() else []
        acts.append({"type": "find_groups", "keywords": kws})
    elif re.search(r"xin vào nhóm|tham gia nhóm", low):
        acts.append({"type": "join_groups"})
    elif re.search(r"quét bình luận|quét comment", low):
        acts.append({"type": "scan_comments"})
    elif re.search(r"tạm dừng|dừng đăng|ngừng đăng", low) and agent and agent.startswith("sale-"):
        acts.append({"type": "pause_sale", "sale_id": int(agent[5:])})
    elif re.search(r"bật lại|cho đăng lại|tiếp tục đăng", low) and agent and agent.startswith("sale-"):
        acts.append({"type": "resume_sale", "sale_id": int(agent[5:])})
    elif re.search(r"tự học|rút kinh nghiệm", low):
        acts.append({"type": "learn_now"})
    elif re.search(r"\b(từ nay|từ giờ|luôn luôn|không được|cấm|bắt buộc|mỗi ngày|đừng bao giờ)\b", low):
        acts.append({"type": "order", "agent": agent or "all", "text": t})
    elif agent:
        acts.append({"type": "task", "agent": agent, "title": t})
    reply = ("Dạ sếp, tình hình hôm nay:" if acts and all(a["type"] == "status" for a in acts) else "Dạ em nhận việc.") if acts else ("Dạ em chưa hiểu rõ việc này. Sếp nói cụ thể hơn giúp em, ví dụ: “Viết 3 bài về trà gừng”, "
                                            "“Tìm nhóm theo chủ đề hội chạy quảng cáo facebook”, “Lan viết dài quá, viết ngắn lại”.")
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
    if not plan:
        plan = _rule_plan(text)
    done = []
    for a in (plan.get("actions") or [])[:6]:
        if not isinstance(a, dict) or not a.get("type"):
            continue
        try:
            res = execute(a)
        except Exception as e:
            import errors
            errors.report_exc("api", f"CEO làm việc “{a.get('type')}” bị lỗi", e)
            res = f"Lỗi khi làm “{a.get('type')}”: {str(e)[:120]}"
        done.append({"type": a["type"], "result": res})
    reply = (plan.get("reply") or "Dạ em nhận việc.").strip()
    if done:
        reply += "\n" + "\n".join(f"• {d['result']}" for d in done)
    _say("ceo", reply, done, via=via)
    db.log("ceo", "Nhận việc từ sếp", text[:150])
    return {"reply": reply, "actions": done}


# ---------------------------------------------------------------- tự vận hành: CEO duyệt bài
def review_post(p: dict) -> tuple[bool, str]:
    text = f"{p.get('content') or ''}\n{p.get('hashtags') or ''}"
    words = len(text.split())
    if REVIEW_BAD.search(text):
        return False, "Hứa công dụng quá đà"
    if words < 35:
        return False, "Quá ngắn"
    if words > 380:
        return False, "Quá dài"
    head = re.sub(r"\W+", " ", (p.get("content") or "").lower())[:150]
    since = (datetime.now() - timedelta(days=30)).strftime("%Y-%m-%d")
    for o in db.q("""SELECT content FROM posts WHERE id!=? AND status IN ('approved','scheduled','posting','posted')
                     AND created_at >= ?""", (p["id"], since)):
        if head and re.sub(r"\W+", " ", (o["content"] or "").lower())[:150] == head:
            return False, "Trùng bài cũ"
    return True, ""


def review_drafts() -> dict:
    import learning
    import workflows
    cutoff = (datetime.now() - timedelta(minutes=2)).strftime("%Y-%m-%d %H:%M:%S")
    ok = bad = 0
    for p in db.q("SELECT * FROM posts WHERE status='draft' AND created_at <= ? ORDER BY id LIMIT 20", (cutoff,)):
        good, why = review_post(p)
        if good:
            db.run("UPDATE posts SET status='approved' WHERE id=?", (p["id"],))
            learning.record_feedback(p["id"], "approve")
            learning.award("lan", 8, "Bài được CEO duyệt")
            ok += 1
        else:
            db.run("UPDATE posts SET status='rejected' WHERE id=?", (p["id"],))
            learning.record_feedback(p["id"], "reject", p["content"], "", why)
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
    return {"autopilot": autopilot(), "history": history(), "orders": orders(),
            "suggestions": ["Tình hình hôm nay thế nào?", "Viết 3 bài về trà gừng mật ong", "Xếp lịch đăng nhóm",
                            "Tìm nhóm theo chủ đề “hội chạy quảng cáo facebook”", "Lan viết bài dài quá, viết dưới 150 chữ",
                            "Từ nay bài nào cũng nhắc giao hàng toàn quốc"]}

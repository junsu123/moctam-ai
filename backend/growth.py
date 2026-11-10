"""Agent luôn làm việc hoặc học tập để lên cấp.

Mỗi 30 giây (từ lịch tự động) xem từng agent: đang làm việc thật, đang họp thì để yên. Agent nào rảnh thì tự vào
một buổi học (6–12 phút), theo thứ tự:

1. Học kiến thức mới với Claude (Haiku, rẻ nhất): mỗi agent tối đa N buổi/ngày (mặc định 6), cách nhau ít nhất 45 phút.
   Kiến thức học được lưu vào sổ kiến thức (knowledge.py). +5 kinh nghiệm mỗi kiến thức mới.
   Chưa có khóa Claude: học từ thư viện có sẵn đến khi hết.
2. Luyện tập không tốn tiền: Lan luyện viết bài theo phong cách đã học (không lưu bài), Hà luyện trả lời câu khách
   hay hỏi từ sổ, sale ôn cách giữ nick an toàn... +2 kinh nghiệm, tối đa 10/ngày.
3. Ôn lại kiến thức trong sổ: +1 kinh nghiệm, tối đa 10/ngày.

Việc thật (đăng bài, viết bài, họp...) luôn được ưu tiên: khi có việc, trạng thái học bị thay bằng trạng thái làm việc.
Kinh nghiệm từ học có giới hạn mỗi ngày, nên muốn lên cấp nhanh vẫn phải làm ra kết quả thật (bài được duyệt, khách, đơn).
"""
import json
import random
import threading
from datetime import datetime, timedelta

import db

CORE = ["ceo", "minh", "lan", "tuan", "ha", "khoa", "mai", "vy", "bao"]
_lock = threading.Lock()
_busy: set[str] = set()      # agent đang chạy một buổi học có gọi Claude
_session: dict[str, dict] = {}  # agent -> {"until": datetime, "kind": ...}
CAP_PRACTICE, CAP_REVIEW = 10, 10


def s() -> dict:
    return db.get_settings()


def _state() -> dict:
    try:
        st = json.loads(s().get("growth_state") or "{}")
    except Exception:
        st = {}
    if st.get("date") != db.today():
        st = {"date": db.today(), "agents": {}}
    return st


def _save(st: dict):
    db.set_setting("growth_state", json.dumps(st, ensure_ascii=False))


def _a(st: dict, aid: str) -> dict:
    return st["agents"].setdefault(aid, {"study": 0, "learned": 0, "practice_xp": 0, "review_xp": 0, "last_study": ""})


def owner(aid: str) -> str:
    return "sale" if aid.startswith("sale-") else aid


def agents_now() -> list[str]:
    rows = db.q("SELECT id FROM sales WHERE COALESCE(status,'active')='active' AND COALESCE(is_sample,0)=0")
    return CORE + [f"sale-{r['id']}" for r in rows]


def _real_work(aid: str) -> bool:
    import workflows
    st = workflows.STATUS.get(aid) or {}
    if st.get("state") in ("working", "meeting", "talking") and not st.get("auto"):
        return True
    if aid.startswith("sale-"):
        import browser_poster
        sid = int(aid[5:])
        if browser_poster.busy(sid) or browser_poster.queued(sid):
            return True
    return False


def _set(aid: str, text: str):
    import workflows
    cur = workflows.STATUS.get(aid) or {}
    if cur.get("state") in ("working", "meeting", "talking") and not cur.get("auto"):
        return  # đang có việc thật: không ghi đè
    workflows.STATUS[aid] = {"state": "learning", "text": text, "at": db.now(), "auto": True}


def _award(aid: str, xp: int, reason: str):
    import learning
    learning.award(aid, xp, reason)


def _study(aid: str):
    """Buổi học có gọi Claude (hoặc thư viện có sẵn khi chưa có khóa). Chạy nền."""
    import knowledge
    try:
        topics = knowledge.plan_topics(owner(aid), 1)
        if topics:
            _set(aid, f"Đang học: {topics[0]['topic'][:70]}")
        ids = knowledge.study_agent(owner(aid), 1)
        with _lock:
            st = _state()
            a = _a(st, aid)
            a["study"] += 1
            a["learned"] += len(ids)
            a["last_study"] = db.now()
            _save(st)
        if ids:
            t = db.one("SELECT topic FROM knowledge WHERE id=?", (ids[0],))
            _award(aid, 5 * len(ids), "Học kiến thức mới")
            _set(aid, f"Vừa học xong: {(t or {}).get('topic', '')[:70]}")
            db.log(aid, "Tự học lúc rảnh", (t or {}).get("topic", "")[:150])
        else:  # chưa học được gì mới (chưa có khóa Claude và đã học hết thư viện): ôn lại kiến thức cũ
            txt = _review(aid) or _practice(aid) or "Đọc lại sổ tay kinh nghiệm"
            _set(aid, txt)
            if aid in _session:
                _session[aid]["text"] = txt
    except Exception as e:
        print("[growth]", aid, e)
    finally:
        _busy.discard(aid)


def _practice(aid: str) -> str | None:
    """Luyện tập không gọi Claude. Trả về câu mô tả hoặc None nếu không có gì để luyện."""
    if aid == "lan":
        try:
            import content_style
            import learning
            if content_style.ready()[0]:
                prods = db.q("SELECT * FROM products")
                if prods:
                    p = learning.choose_product(prods)
                    d = content_style.compose(p, learning.choose_angle(), "group", dry=True)
                    if d:
                        return f"Luyện viết bài về {p['name']} theo phong cách đã học"
        except Exception:
            pass
    if aid == "ha":
        r = db.one("SELECT topic FROM knowledge WHERE agent_id='ha' AND kind='faq' AND status='active' ORDER BY RANDOM() LIMIT 1")
        if r:
            return f"Luyện trả lời khách: {r['topic'][:60]}"
    if aid == "tuan":
        g = db.one("SELECT name FROM group_candidates WHERE status='new' AND verdict='consider' ORDER BY RANDOM() LIMIT 1")
        if g:
            return f"Xem lại nhóm cần cân nhắc: {g['name'][:50]}"
    if aid == "khoa":
        return "Xem lại số liệu bài đăng 7 ngày qua"
    if aid == "bao":
        r = db.one("SELECT COUNT(*) n FROM posts WHERE status='posted' AND COALESCE(permalink_status,'')!='removed'")
        return f"Rà lại {r['n']} bài đã đăng, chọn bài cần up" if r and r["n"] else "Chuẩn bị câu bình luận up bài mới"
    if aid == "vy":
        r = db.one("SELECT keyword FROM site_keywords WHERE status='planned' ORDER BY priority, id LIMIT 1")
        return f"Nghiên cứu từ khóa: {r['keyword'][:50]}" if r else "Đọc lại bài website, sửa chỗ chưa chuẩn SEO"
    if aid == "mai":
        r = db.one("SELECT COALESCE(shop_name, account_name) n FROM prospects WHERE grade IN ('B','C') ORDER BY RANDOM() LIMIT 1")
        if r and r["n"]:
            return f"Xem lại bằng chứng khách tiềm năng: {r['n'][:45]}"
        return "Ôn thang chấm điểm khách sỉ A/B/C/D"
    if aid.startswith("sale-"):
        return random.choice(["Ôn cách giữ nick an toàn", "Ôn cách trả lời bình luận xin số điện thoại",
                              "Xem lại các nhóm đã vào"])
    return None


def _review(aid: str) -> str | None:
    r = db.one("""SELECT topic FROM knowledge WHERE agent_id IN (?, 'all') AND status='active'
                  ORDER BY COALESCE(last_used_at,'') ASC, RANDOM() LIMIT 1""", (owner(aid),))
    return f"Ôn lại: {r['topic'][:70]}" if r else None


def _can_study(a: dict) -> bool:
    import knowledge
    if not knowledge.self_study_on():  # tự học kiến thức chung với Claude: mặc định tắt (không có dữ liệu thật)
        return False
    cap = int(s().get("idle_study_per_day") or 6)
    if a["study"] >= cap:
        return False
    if not a["last_study"]:
        return True
    gap = max(45, int(16 * 60 / max(cap, 1)))  # trải đều trong ngày, ít nhất 45 phút
    return db.clock() - datetime.strptime(a["last_study"], "%Y-%m-%d %H:%M:%S") >= timedelta(minutes=gap)


def tick(now: datetime | None = None):
    if s().get("idle_learning", "1") != "1":
        return
    import meeting
    if meeting.is_running():
        return
    try:
        import company
        if company.status() == "dissolved":
            return
    except Exception:
        pass
    now = now or db.clock()
    st = _state()
    delta: dict[str, dict] = {}
    for aid in agents_now():
        if aid in _busy or _real_work(aid):
            continue
        cur = _session.get(aid)
        if cur and cur["until"] > now:
            import workflows
            if (workflows.STATUS.get(aid) or {}).get("state") != "learning":
                _set(aid, cur["text"])
            continue
        a = _a(st, aid)
        mins = random.randint(6, 12)
        if _can_study(a):
            _busy.add(aid)
            _session[aid] = {"until": now + timedelta(minutes=mins), "text": "Đang học kiến thức mới", "kind": "study"}
            _set(aid, "Đang chuẩn bị bài học mới")
            threading.Thread(target=_study, args=(aid,), daemon=True).start()
            continue
        txt = _practice(aid) if random.random() < 0.6 else None
        if txt and a["practice_xp"] < CAP_PRACTICE:
            delta.setdefault(aid, {})["practice_xp"] = 2
            _award(aid, 2, "Luyện tập lúc rảnh")
        else:
            txt = _review(aid) or txt or "Đọc lại sổ tay kinh nghiệm"
            if a["review_xp"] < CAP_REVIEW:
                delta.setdefault(aid, {})["review_xp"] = 1
                _award(aid, 1, "Ôn kiến thức")
        _session[aid] = {"until": now + timedelta(minutes=mins), "text": txt, "kind": "practice"}
        _set(aid, txt)
    if delta:  # gộp vào trạng thái mới nhất (các buổi học chạy nền cũng đang ghi)
        with _lock:
            st2 = _state()
            for aid, d in delta.items():
                a2 = _a(st2, aid)
                for k, v in d.items():
                    a2[k] += v
            _save(st2)


def today() -> dict:
    st = _state()
    return {aid: v for aid, v in st["agents"].items()}


def summary_text() -> str:
    t = today()
    learned = sum(v.get("learned", 0) for v in t.values())
    return f"Hôm nay cả đội tự học thêm {learned} kiến thức lúc rảnh." if learned else ""

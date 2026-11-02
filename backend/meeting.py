"""Phòng họp: các agent báo cáo, tranh luận và chốt việc mỗi ngày."""
import json
import random
import threading
import time

import db
import mock_brain
import workflows
from agents import AGENTS, name_of, public_list, system_prompt
from llm import llm

TOPICS = [
    "Tuần này nên tập trung đẩy sản phẩm nào cho khách sỉ?",
    "Đăng nhiều bài mỗi ngày hay ít bài nhưng chất lượng hơn?",
    "Có nên công khai giá sỉ ngay trong bài đăng hội nhóm không?",
    "Gửi mẫu thử miễn phí cho khách sỉ mới: có đáng chi phí không?",
    "Nên ưu tiên tệp khách livestream hay tệp khách chạy quảng cáo?",
    "Có nên đẩy dịch vụ in nhãn riêng (OEM) cho shop online không?",
]

DEBATERS = ["lan", "tuan", "ha", "khoa"]
_running = {"id": None}
_boss_inbox: dict[int, list[str]] = {}


def is_running():
    return _running["id"]


LOGIN_TXT = {"ok": "nick hoạt động bình thường", "not_logged_in": "nick đang bị đăng xuất, nhờ sếp đăng nhập lại",
             "checkpoint": "nick đang bị Facebook kiểm tra (checkpoint), em đã dừng đăng"}


def _sale_report(r: dict) -> str:
    t = db.today() + "%"
    c = lambda st, col: db.one(f"SELECT COUNT(*) n FROM posts WHERE sale_id=? AND status=? AND {col} LIKE ?",
                               (r["id"], st, t))["n"]
    posted, waiting = c("posted", "posted_at"), c("scheduled", "scheduled_for")
    failed = db.one("SELECT COUNT(*) n FROM posts WHERE sale_id=? AND status='failed'", (r["id"],))["n"]
    msg = f"Em giữ nick {r['fb_name'] or r['name']}: hôm nay đã đăng {posted} bài, còn {waiting} bài trong lịch"
    msg += f", {failed} bài lỗi cần xem lại" if failed else ""
    return msg + f". Tình trạng: {LOGIN_TXT.get(r['login_status'], r['login_status'])}."


def _say(mid: int, agent_id: str, phase: str, content: str):
    workflows.set_status(agent_id, "talking", content[:60])
    db.run("INSERT INTO meeting_messages(meeting_id, agent_id, phase, content, created_at) VALUES (?,?,?,?,?)",
           (mid, agent_id, phase, content, db.now()))
    time.sleep(2.2 if not llm.live else 0.6)  # nhịp để giao diện hiển thị như đang nói
    workflows.set_status(agent_id, "meeting", "Đang họp")


def _transcript(mid: int, limit: int = 30) -> str:
    rows = db.q("SELECT agent_id, content FROM meeting_messages WHERE meeting_id=? ORDER BY id DESC LIMIT ?",
                (mid, limit))[::-1]
    name = lambda a: "SẾP" if a == "boss" else (f"{AGENTS[a]['name']} ({AGENTS[a]['role']})" if a in AGENTS else f"{name_of(a)} (Sale)")
    return "\n".join(f"{name(r['agent_id'])}: {r['content']}" for r in rows)


def _boss_check(mid: int):
    """Nếu sếp vừa nói, trưởng phòng phản hồi ngay."""
    msgs = _boss_inbox.pop(mid, [])
    for text in msgs:
        reply = llm.chat(system_prompt("minh", db.get_settings()),
                         f"Biên bản cuộc họp:\n{_transcript(mid)}\n\nSếp (chủ xưởng) vừa nói: \"{text}\". "
                         "Bạn là người chủ trì, hãy phản hồi sếp trong 1-2 câu và định hướng lại cuộc họp.",
                         mock=lambda: mock_brain.chair_reply(text), max_tokens=250)
        _say(mid, "minh", "boss", reply)


def boss_say(mid: int, text: str):
    db.run("INSERT INTO meeting_messages(meeting_id, agent_id, phase, content, created_at) VALUES (?,?,?,?,?)",
           (mid, "boss", "boss", text, db.now()))
    _boss_inbox.setdefault(mid, []).append(text)


def _run(mid: int, topic: str):
    s = db.get_settings()
    st = workflows.stats()
    try:
        everyone = [a["id"] for a in public_list()]
        for a in everyone:
            workflows.set_status(a, "meeting", "Đi tới phòng họp")
        time.sleep(3)  # thời gian các nhân vật đi vào phòng họp
        # 1. Mở đầu
        _say(mid, "minh", "open", llm.chat(system_prompt("minh", s),
             f"Mở đầu cuộc họp giao ban sáng ngày {db.today()} (1-2 câu). Chủ đề tranh luận hôm nay: \"{topic}\".",
             mock=lambda: mock_brain.meeting_open(topic), max_tokens=200))
        # 2. Báo cáo
        for a in DEBATERS:
            _boss_check(mid)
            _say(mid, a, "report", llm.chat(system_prompt(a, s),
                 f"Số liệu hệ thống hiện tại: {json.dumps(st, ensure_ascii=False)}\n"
                 f"Hãy báo cáo công việc phần của bạn trong cuộc họp (2-3 câu, có con số cụ thể từ số liệu, "
                 "nêu 1 vướng mắc hoặc đề xuất).",
                 mock=lambda a=a: mock_brain.report(a, st), max_tokens=300))
        # 2b. Nhân viên sale báo cáo nick của mình (số liệu thật, không cần AI)
        for r in db.q("SELECT * FROM sales ORDER BY id LIMIT 8"):
            _boss_check(mid)
            _say(mid, f"sale-{r['id']}", "report", _sale_report(r))
        # 3. Tranh luận
        _say(mid, "minh", "debate", f"Cảm ơn mọi người. Giờ vào chủ đề chính: \"{topic}\". Mỗi người nêu quan điểm, cứ phản biện thẳng thắn.")
        for rnd in range(2):
            order = DEBATERS[:] if rnd == 0 else random.sample(DEBATERS, len(DEBATERS))
            for a in order:
                _boss_check(mid)
                _say(mid, a, "debate", llm.chat(system_prompt(a, s),
                     f"Biên bản cuộc họp đến giờ:\n{_transcript(mid)}\n\n"
                     f"Chủ đề tranh luận: \"{topic}\". Đây là vòng {rnd + 1}. Nêu quan điểm của bạn theo đúng tính cách "
                     f"({'nêu lập trường ban đầu' if rnd == 0 else 'phản biện hoặc đồng tình với 1 người cụ thể, gọi tên họ'}). "
                     "Tối đa 3 câu, không lặp lại ý đã nói.",
                     mock=lambda a=a, r=rnd: mock_brain.debate(a, r, topic), max_tokens=300))
        _boss_check(mid)
        # 4. Kết luận + giao việc
        conc = llm.json(system_prompt("minh", s),
                        f"Biên bản cuộc họp:\n{_transcript(mid, 40)}\n\nBạn là chủ trì. Chốt cuộc họp: tóm tắt quyết định "
                        "và giao việc cụ thể cho từng người (lan, tuan, ha, khoa). Trả về JSON: "
                        '{"summary": "3-4 câu", "action_items": [{"agent_id": "lan", "title": "việc cụ thể"}]}',
                        mock=lambda: mock_brain.conclusion(topic))
        if not isinstance(conc, dict) or "summary" not in conc:
            conc = mock_brain.conclusion(topic)
        _say(mid, "minh", "close", "Chốt lại: " + conc["summary"])
        items = [i for i in conc.get("action_items", []) if i.get("agent_id") in AGENTS]
        for it in items:
            db.run("INSERT INTO tasks(agent_id, title, status, meeting_id, due, created_at) VALUES (?,?,?,?,?,?)",
                   (it["agent_id"], it["title"], "todo", mid, db.today(), db.now()))
        _say(mid, "minh", "close", "Giao việc: " + "; ".join(f"{AGENTS[i['agent_id']]['name']} — {i['title']}" for i in items)
             + ". Hết giờ họp, mọi người về vị trí làm việc nhé!")
        db.run("UPDATE meetings SET status='done', summary=?, action_items=?, ended_at=? WHERE id=?",
               (conc["summary"], db.dumps(items), db.now(), mid))
        db.log("minh", "Kết thúc họp", f"Chủ đề: {topic}. Giao {len(items)} việc.")
    except Exception as e:
        db.run("UPDATE meetings SET status='done', summary=?, ended_at=? WHERE id=?",
               (f"Cuộc họp bị gián đoạn: {e}", db.now(), mid))
        print("[meeting] lỗi", e)
    finally:
        for a in [x["id"] for x in public_list()]:
            workflows.set_status(a, "idle", "Quay về bàn làm việc")
        _running["id"] = None
    if s.get("auto_daily_work") == "1":
        workflows.daily_work()


def start(topic: str | None = None) -> int:
    if _running["id"]:
        return _running["id"]
    topic = (topic or "").strip() or random.choice(TOPICS)
    mid = db.run("INSERT INTO meetings(date, topic, status, created_at) VALUES (?,?,?,?)",
                 (db.today(), topic, "running", db.now()))
    _running["id"] = mid
    threading.Thread(target=_run, args=(mid, topic), daemon=True).start()
    return mid

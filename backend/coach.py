"""Claude kèm cặp từng agent từ việc thật.

Mỗi agent tự ghi lại kết quả thật của việc mình làm (sếp duyệt / sửa / loại, có khách, chốt đơn, không mua, sếp bỏ qua...).
Agent nào có từ 5 kết quả mới (sửa được) và đã 7 ngày chưa được kèm thì tự gửi việc của mình cho Claude chấm, không qua CEO.
Mọi agent đến lượt được gom vào MỘT lô (Batch API, giảm 50% chi phí). Claude chỉ nhận xét dựa trên các kết quả được gửi,
ghi tối đa 3 bài học vào sổ tay của agent và bỏ bài học mà kết quả thật đã chứng minh là sai."""
import json
import re
import time

import db

AGENTS = {  # agent có kết quả thật để chấm
    "lan": "viết bài đăng nhóm / trang cá nhân",
    "ceo": "chấm và duyệt bài trước khi đăng",
    "tuan": "chọn nhóm và xếp lịch đăng",
    "ha": "soạn tin nhắn, kịch bản tư vấn khách",
    "mai": "tìm khách sỉ, chấm điểm người bán",
    "bao": "viết câu trả lời khách hỏi mua trong nhóm",
}
VERDICT = {"good": "Tốt", "bad": "Chưa tốt", "edit": "Sếp sửa"}
_poll = {"at": 0.0}


def s() -> dict:
    return db.get_settings()


def on() -> bool:
    return s().get("coach_on", "1") == "1"


def min_new() -> int:
    return max(3, int(s().get("coach_min") or 5))


def every_days() -> int:
    return max(1, int(s().get("coach_days") or 7))


def _cut(t, n):
    t = re.sub(r"\s+", " ", str(t or "")).strip()
    return t if len(t) <= n else t[:n - 1] + "…"


# ---------------------------------------------------------------- ghi kết quả thật (gọi từ nơi kết quả xảy ra)
def note(agent: str, verdict: str, work: str, result: str, ref: str = ""):
    """verdict: good | bad | edit. work: agent đã làm gì (bài, tin nhắn...). result: chuyện gì xảy ra thật."""
    if agent not in AGENTS or verdict not in VERDICT:
        return
    try:
        if ref and db.one("SELECT 1 FROM coach_outcomes WHERE agent_id=? AND ref=? AND verdict=? AND result=?",
                          (agent, ref, verdict, _cut(result, 300))):
            return  # cùng một kết quả không ghi hai lần
        db.run("INSERT INTO coach_outcomes(agent_id, verdict, work, result, ref, created_at) VALUES (?,?,?,?,?,?)",
               (agent, verdict, _cut(work, 700), _cut(result, 300), ref, db.now()))
    except Exception as e:
        print("[coach]", e)


def on_post_feedback(post_id: int, kind: str, before: str = "", after: str = "", reason: str = "", by: str = "boss"):
    p = db.one("SELECT * FROM posts WHERE id=?", (post_id,)) or {}
    work = before or p.get("content") or ""
    who = "CEO" if by == "ceo" else "Sếp"
    if kind == "approve":
        note("lan", "good", work, f"{who} duyệt ngay, không sửa", f"post:{post_id}")
    elif kind == "edit":
        note("lan", "edit", work, f"Sếp sửa thành: {_cut(after, 250)}", f"post:{post_id}")
    elif kind == "reject":
        note("lan", "bad", work, f"{who} loại bài" + (f": {reason}" if reason else ""), f"post:{post_id}")


def on_post_leads(post_id: int, delta: int):
    p = db.one("""SELECT p.*, g.name gname FROM posts p LEFT JOIN groups g ON g.id=p.group_id WHERE p.id=?""", (post_id,))
    if not p or delta <= 0:
        return
    note("lan", "good", p["content"], f"Bài đăng có {delta} khách mới để lại liên hệ", f"post:{post_id}:{p.get('leads')}")
    if p.get("gname"):
        note("tuan", "good", f"Xếp bài #{post_id} vào nhóm “{p['gname']}” lúc {str(p.get('posted_at') or '')[11:16]}",
             f"Bài có {delta} khách mới", f"post:{post_id}:{p.get('leads')}")
    if p.get("reviewed_by") == "ceo":
        note("ceo", "good", p["content"], f"Bài CEO duyệt có {delta} khách mới", f"post:{post_id}:{p.get('leads')}")


def on_lead_status(lead_id: int, status: str):
    lead = db.one("SELECT * FROM leads WHERE id=?", (lead_id,))
    if not lead or status not in ("ordered", "lost"):
        return
    won = status == "ordered"
    why = "Khách chốt đơn" if won else "Khách không mua" + (f": {lead.get('lost_reason')}" if lead.get("lost_reason") else "") \
        + (f" ({lead.get('lost_note')})" if lead.get("lost_note") else "")
    msg = db.one("SELECT text FROM replies WHERE lead_id=? ORDER BY sent DESC, id DESC LIMIT 1", (lead_id,))
    hw = (msg or {}).get("text") or lead.get("consult_note")
    if hw:
        note("ha", "good" if won else "bad", hw, why, f"lead:{lead_id}")
    if (lead.get("origin") or "") == "prospect":
        note("mai", "good" if won else "bad", f"Tìm ra {lead.get('name')}: {_cut(lead.get('need') or lead.get('note'), 300)}",
             why, f"lead:{lead_id}")


# ---------------------------------------------------------------- tình trạng
def pending(agent: str) -> int:
    return db.one("SELECT COUNT(*) n FROM coach_outcomes WHERE agent_id=? AND coached_at IS NULL AND batch_id IS NULL",
                  (agent,))["n"]


def _last() -> dict:
    try:
        return json.loads(s().get("coach_last") or "{}")
    except Exception:
        return {}


def due_agents(force: bool = False) -> list[str]:
    last = _last()
    out = []
    for a in AGENTS:
        if pending(a) < min_new():
            continue
        at = last.get(a, {}).get("at")
        if not force and at:
            from datetime import datetime, timedelta
            try:
                if datetime.strptime(at[:10], "%Y-%m-%d") > (db.clock().replace(tzinfo=None) - timedelta(days=every_days())):
                    continue
            except ValueError:
                pass
        out.append(a)
    return out


# ---------------------------------------------------------------- gửi lô cho Claude
SYSTEM = """Bạn là người kèm cặp (coach) cho một nhân viên AI của xưởng trà túi lọc, ngũ cốc MỘC TÂM. Nhiệm vụ: đọc các việc
nhân viên đã làm cùng KẾT QUẢ THẬT (sếp duyệt / sửa / loại, có khách, chốt đơn, khách không mua) và chỉ ra cách làm tốt hơn.
Quy tắc:
- Chỉ kết luận từ các kết quả được gửi; ghi rõ dựa trên kết quả nào (#số). Không đưa lời khuyên chung chung, không bịa số.
- So sánh việc được khen với việc bị chê / bị sửa để tìm điểm khác biệt cụ thể (câu mở đầu, độ dài, cách gọi tên hàng, lời kêu gọi...).
- Bài học phải làm được ngay ở lần sau, viết dạng việc cần làm, dưới 40 chữ.
- Không đề xuất tăng số bài / bình luận / lời mời, không lách luật Facebook, không hứa công dụng chữa bệnh, không ghi giá.
- Bài học hiện có mà kết quả mới cho thấy sai: liệt kê id để bỏ."""


def _prompt(agent: str, rows: list[dict]) -> str:
    from agents import name_of
    lessons = db.q("""SELECT id, text FROM lessons WHERE agent_id=? AND status='active' ORDER BY pinned DESC, confidence DESC
                      LIMIT 10""", (agent,))
    items = "\n".join(f"#{r['id']} [{VERDICT[r['verdict']]}] Việc: {r['work']}\n   Kết quả: {r['result']}" for r in rows)
    good = sum(r["verdict"] == "good" for r in rows)
    return (f"Nhân viên: {name_of(agent)} — việc: {AGENTS[agent]}.\n"
            f"Bài học đang dùng (id: nội dung): {json.dumps({l['id']: l['text'] for l in lessons}, ensure_ascii=False)}\n\n"
            f"{len(rows)} kết quả thật mới ({good} tốt, {len(rows) - good} chưa tốt / bị sửa):\n{items}\n\n"
            'Trả về JSON: {"assessment": "1-2 câu nhận xét thẳng thắn", "lessons": [{"text": "...", "evidence": "#.. #.."}] (tối đa 3, '
            'bỏ trống nếu kết quả chưa đủ rõ), "retire": [id bài học hiện có bị kết quả chứng minh sai], '
            '"check": "1 câu tự kiểm trước khi làm việc tiếp theo"}')


def _model_default():
    if not s().get("model_coach"):
        import llm as L
        db.set_setting("model_coach", L.HAIKU if s().get("cost_preset") == "tiet_kiem" else L.SONNET)


def run(force: bool = False) -> dict:
    """Gửi một lô cho mọi agent đến lượt. force: sếp bấm, bỏ qua thời gian chờ 7 ngày (vẫn cần đủ kết quả mới)."""
    from llm import llm
    if db.one("SELECT 1 FROM ai_batches WHERE task='coach' AND status='in_progress'"):
        return {"sent": [], "msg": "Đang có một lô kèm cặp chờ Claude chấm, xong em ghi bài học vào sổ tay từng agent"}
    agents = due_agents(force)
    if not agents:
        return {"sent": [], "msg": f"Chưa agent nào có đủ {min_new()} kết quả thật mới để kèm cặp"}
    if not llm.live:
        return {"sent": [], "msg": "Chưa có khóa Claude nên chưa kèm cặp được (đội vẫn tự học bằng thống kê)"}
    _model_default()
    reqs, meta = [], {}
    for a in agents:
        rows = db.q("""SELECT * FROM coach_outcomes WHERE agent_id=? AND coached_at IS NULL AND batch_id IS NULL
                       ORDER BY id DESC LIMIT 20""", (a,))
        reqs.append({"custom_id": f"coach-{a}", "system": SYSTEM, "prompt": _prompt(a, rows)})
        meta[f"coach-{a}"] = {"agent": a, "ids": [r["id"] for r in rows]}
    bid = llm.batch_create("coach", reqs, max_tokens=700)
    if not bid:
        return {"sent": [], "msg": "Chưa gửi được lô cho Claude, đêm sau thử lại"}
    db.run("INSERT INTO ai_batches(id, task, meta, status, created_at) VALUES (?,?,?,?,?)",
           (bid, "coach", json.dumps(meta), "in_progress", db.now()))
    for m in meta.values():
        db.many("UPDATE coach_outcomes SET batch_id=? WHERE id=?", [(bid, i) for i in m["ids"]])
    from agents import name_of
    db.log("khoa", "Gửi lô kèm cặp", f"{', '.join(name_of(a) for a in agents)} gửi việc thật cho Claude chấm (giảm 50% chi phí)")
    return {"sent": agents, "batch": bid,
            "msg": f"{', '.join(name_of(a) for a in agents)} đã gửi việc thật cho Claude chấm, thường có kết quả sau vài phút"}


def apply(agent: str, ids: list[int], data: dict | None) -> dict:
    """Nhận nhận xét của Claude: ghi bài học, bỏ bài học sai, đánh dấu kết quả đã được kèm."""
    import learning
    from agents import name_of
    if not isinstance(data, dict):  # Claude lỗi: trả kết quả về hàng chờ cho lần sau
        db.many("UPDATE coach_outcomes SET batch_id=NULL WHERE id=?", [(i,) for i in ids])
        return {"agent": agent, "added": 0, "failed": True}
    added = []
    for l in (data.get("lessons") or [])[:3]:
        if isinstance(l, dict) and l.get("text"):
            lid = learning.add_lesson(agent, l["text"], f"Claude kèm cặp, dựa trên kết quả {_cut(l.get('evidence'), 80)}",
                                      "coach", 0.75)
            if lid:
                added.append(_cut(l["text"], 200))
    retired = 0
    for rid in (data.get("retire") or [])[:5]:
        if str(rid).isdigit():
            cond = "id=? AND agent_id=? AND pinned=0 AND source!='boss' AND status='active'"
            if db.one(f"SELECT 1 FROM lessons WHERE {cond}", (int(rid), agent)):
                db.run(f"UPDATE lessons SET status='retired', updated_at=? WHERE {cond}", (db.now(), int(rid), agent))
                retired += 1
    db.many("UPDATE coach_outcomes SET coached_at=? WHERE id=?", [(db.now(), i) for i in ids])
    last = _last()
    last[agent] = {"at": db.now(), "n": len(ids), "assessment": _cut(data.get("assessment"), 300),
                   "lessons": added, "check": _cut(data.get("check"), 200)}
    db.set_setting("coach_last", json.dumps(last, ensure_ascii=False))
    learning.award(agent, 10, "Được Claude kèm cặp từ việc thật")
    db.log(agent, "Được Claude kèm cặp", (_cut(data.get("assessment"), 160) + " · ") * bool(data.get("assessment"))
           + (f"{len(added)} bài học mới" if added else "chưa rút được bài học mới"))
    return {"agent": agent, "name": name_of(agent), "added": len(added), "retired": retired}


def poll() -> int:
    from llm import llm
    if not llm.live:
        return 0
    n = 0
    for b in db.q("SELECT * FROM ai_batches WHERE status='in_progress' AND task='coach'"):
        try:
            if llm.batch_status(b["id"]) != "ended":
                continue
            res = llm.batch_results(b["id"], "coach")
            from llm import parse_json
            for cid, m in json.loads(b["meta"]).items():
                apply(m["agent"], m["ids"], parse_json(res.get(cid) or ""))
                n += 1
            db.run("UPDATE ai_batches SET status='ended', ended_at=? WHERE id=?", (db.now(), b["id"]))
        except Exception as e:
            print("[coach]", e)
    return n


def tick(now):
    """Mỗi lượt lịch: 2 phút xem lô xong chưa; mỗi ngày một lần (mặc định 22:30) gửi lô cho agent đến lượt."""
    if time.time() - _poll["at"] > 120:
        _poll["at"] = time.time()
        poll()
    st = s()
    if not on() or st.get("coach_day") == db.today() or now.strftime("%H:%M") < (st.get("coach_time") or "22:30"):
        return
    db.set_setting("coach_day", db.today())
    run()


def covers(agent: str) -> bool:
    """Agent này đã được kèm cặp riêng: lượt phản tỉnh chung mỗi tuần bỏ phần gọi Claude để không trả tiền hai lần."""
    return on() and agent in AGENTS


def overview() -> dict:
    from agents import name_of
    last = _last()
    cost = db.one("SELECT COALESCE(SUM(cost_usd),0) usd, COUNT(*) n FROM usage WHERE task='coach' AND created_at>=?",
                  ((db.clock().strftime("%Y-%m-%d")[:8] + "01"),))
    waiting = db.one("SELECT COUNT(*) n FROM ai_batches WHERE task='coach' AND status='in_progress'")["n"]
    rows = []
    for a in AGENTS:
        L = last.get(a, {})
        rows.append({"agent": a, "name": name_of(a), "job": AGENTS[a], "pending": pending(a),
                     "in_batch": db.one("SELECT COUNT(*) n FROM coach_outcomes WHERE agent_id=? AND batch_id IS NOT NULL "
                                        "AND coached_at IS NULL", (a,))["n"],
                     "times": db.one("SELECT COUNT(DISTINCT batch_id) n FROM coach_outcomes WHERE agent_id=? AND coached_at IS NOT NULL",
                                     (a,))["n"], **{k: L.get(k) for k in ("at", "assessment", "lessons", "check")}})
    return {"on": on(), "min": min_new(), "days": every_days(), "time": s().get("coach_time") or "22:30",
            "model": s().get("model_coach") or "", "month_usd": round(cost["usd"], 4), "month_calls": cost["n"],
            "waiting": waiting, "agents": rows}

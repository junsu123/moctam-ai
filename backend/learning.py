"""Bộ máy tự học của các agent.

Học theo 3 lớp, từ rẻ đến đắt:
1. Thống kê (không tốn AI): điểm hiệu quả của mỗi bài = khách × 5 + bình luận. Từ đó tính hiệu quả
   theo góc tiếp cận, sản phẩm, nhóm, khung giờ (có làm mượt để vài bài may mắn không làm lệch).
   Lan chọn góc/sản phẩm, Tuấn chọn giờ đăng theo các con số này, vẫn giữ một phần thử cái mới.
2. Phản hồi của sếp: bài duyệt ngay, bài bị sửa (lưu bản trước/sau), bài bị loại (kèm lý do),
   tin nhắn dẫn tới chốt đơn. Bản sếp sửa và tin nhắn chốt được dùng làm ví dụ mẫu.
3. Phản tỉnh mỗi đêm: mỗi agent đọc số liệu của mình, rút ra bài học ngắn có bằng chứng và đặt
   mục tiêu ngày mai (Claude Haiku, vài phần nghìn USD/đêm; không có API key thì dùng luật thống kê).

Ranh giới an toàn: bài học chỉ ảnh hưởng nội dung, cách chọn góc/sản phẩm/giờ/nhóm. Không bài học nào
được thay đổi giới hạn bài/ngày, giãn cách, luật nhóm hay checkpoint — các con số đó do sếp đặt trong code/cài đặt.
"""
import json
import math
import random
import re
import threading
from datetime import datetime, timedelta

import db
import mock_brain

LEAD_W = 5                 # 1 khách = 5 bình luận
MAX_ACTIVE = 10            # số bài học tối đa đang dùng của mỗi agent (bài ghim không tính)
PROMPT_LESSONS = 6         # số bài học đưa vào prompt (giữ chi phí thấp)
CORE = ["ceo", "minh", "lan", "tuan", "ha", "khoa"]
BANNED = re.compile(r"(tăng|nâng).{0,20}(số bài|tần suất|giới hạn)|bỏ qua luật|lách|spam|chữa (khỏi|bệnh)|trị bệnh", re.I)
_running = {"on": False}


def _ago(days: int) -> str:
    return (datetime.now() - timedelta(days=days)).strftime("%Y-%m-%d %H:%M:%S")


# ---------------------------------------------------------------- 1. thống kê hiệu quả
def score_sql() -> str:
    return f"(COALESCE(leads,0)*{LEAD_W} + COALESCE(comments,0))"


def perf(dim: str, days: int = 30) -> dict:
    """Hiệu quả theo một chiều: angle | product_id | group_id | hour | target_type | sale_id."""
    key = {"hour": "substr(posted_at,12,2)"}.get(dim, dim)
    rows = db.q(f"""SELECT {key} k, COUNT(*) n, SUM({score_sql()}) score, SUM(COALESCE(leads,0)) leads,
                    SUM(COALESCE(comments,0)) comments FROM posts WHERE status='posted' AND posted_at >= ? AND {key} IS NOT NULL
                    GROUP BY k""", (_ago(days),))
    n_all = sum(r["n"] for r in rows)
    mean = (sum(r["score"] or 0 for r in rows) / n_all) if n_all else 0
    k = 3  # làm mượt: coi như mỗi lựa chọn đã có 3 bài ở mức trung bình
    out = {}
    for r in rows:
        out[str(r["k"])] = {"n": r["n"], "score": r["score"] or 0, "leads": r["leads"] or 0, "comments": r["comments"] or 0,
                            "avg": round((r["score"] or 0) / r["n"], 2), "smoothed": round(((r["score"] or 0) + k * mean) / (r["n"] + k), 3)}
    return {"mean": round(mean, 3), "n": n_all, "items": out}


def approval(days: int = 30) -> dict:
    """Sếp duyệt ngay / sửa / loại theo góc tiếp cận."""
    rows = db.q("""SELECT p.angle, f.kind FROM feedback f JOIN posts p ON p.id=f.post_id WHERE f.created_at >= ?""", (_ago(days),))
    out = {}
    for r in rows:
        a = out.setdefault(r["angle"], {"approve": 0, "edit": 0, "reject": 0})
        a[r["kind"]] = a.get(r["kind"], 0) + 1
    for a in out.values():
        tot = a["approve"] + a["edit"] + a["reject"]
        a["rate"] = round((a["approve"] + 0.5 * a["edit"] + 1) / (tot + 2), 3)  # làm mượt Laplace
    return out


def weights(dim: str, options: list[str]) -> dict:
    """Trọng số chọn cho từng lựa chọn: hiệu quả thật × mức sếp thích (chỉ với góc tiếp cận)."""
    p = perf(dim)
    ap = approval() if dim == "angle" else {}
    base = p["mean"] if p["n"] else 1.0
    w = {}
    for o in options:
        it = p["items"].get(str(o))
        v = it["smoothed"] if it else base
        v = max(v, 0.05 * (base or 1)) + 0.01
        if dim == "angle":
            v *= 0.5 + ap.get(o, {}).get("rate", 0.5)
        w[str(o)] = v
    tot = sum(w.values()) or 1
    return {k: round(v / tot, 4) for k, v in w.items()}


def choose(dim: str, options: list) -> str:
    """Khai thác cái đang hiệu quả, vẫn dành một phần (mặc định 25%) để thử cái ít được thử."""
    opts = [str(o) for o in options]
    if not opts:
        return None
    explore = float(db.get_settings().get("learn_explore") or 0.25)
    p = perf(dim)
    if p["n"] < 6 or random.random() < explore:
        tried = {o: p["items"].get(o, {}).get("n", 0) for o in opts}
        least = min(tried.values())
        return random.choice([o for o in opts if tried[o] <= least + 1])
    w = weights(dim, opts)
    return random.choices(opts, weights=[w[o] for o in opts])[0]


def choose_angle() -> str:
    return choose("angle", list(mock_brain.ANGLES))


def choose_product(products: list[dict]) -> dict:
    """Chọn sản phẩm để viết bài. Sản phẩm sếp tích "đang bán chạy" được ưu tiên (mặc định 70% số bài),
    trong nhóm đó vẫn chọn theo hiệu quả đã học; phần còn lại xoay vòng các sản phẩm khác để không bỏ quên."""
    hot = [p for p in products if p.get("hot")]
    if hot and len(hot) < len(products):
        share = float(db.get_settings().get("hot_share") or 0.7)
        products = hot if random.random() < share else [p for p in products if not p.get("hot")]
    elif hot:
        products = hot
    pid = choose("product_id", [p["id"] for p in products])
    return next((p for p in products if str(p["id"]) == pid), random.choice(products))


def golden_hours(top: int = 3) -> list[int]:
    p = perf("hour")
    if p["n"] < 8:
        return []
    ranked = sorted(p["items"].items(), key=lambda kv: -kv[1]["smoothed"])
    return [int(h) for h, v in ranked[:top] if v["n"] >= 2 and v["smoothed"] > p["mean"]]


# ---------------------------------------------------------------- 2. tín hiệu từ sếp và khách
def record_feedback(post_id: int, kind: str, before: str = "", after: str = "", reason: str = ""):
    db.run("INSERT INTO feedback(post_id, kind, before, after, reason, created_at) VALUES (?,?,?,?,?,?)",
           (post_id, kind, before, after, reason, db.now()))


def best_examples(agent_id: str, limit: int = 2) -> list[str]:
    """Ví dụ mẫu để agent bắt chước: bài sếp sửa rồi duyệt, bài nhiều khách nhất, tin nhắn đã chốt đơn."""
    cut = lambda t: (t or "").strip()[:550]
    if agent_id == "lan":
        top = db.q(f"""SELECT content FROM posts WHERE status='posted' AND posted_at >= ? AND {score_sql()} > 0
                       ORDER BY {score_sql()} DESC LIMIT 1""", (_ago(30),))
        edits = db.q("""SELECT after FROM feedback WHERE kind='edit' AND after != '' ORDER BY id DESC LIMIT 1""")
        ex = [("Bài hiệu quả nhất 30 ngày qua", r["content"]) for r in top] + [("Bản sếp đã sửa và duyệt", r["after"]) for r in edits]
        return [f"{t}:\n{cut(c)}" for t, c in ex[:limit]]
    if agent_id == "ha":
        won = db.q("""SELECT r.text FROM replies r WHERE r.outcome='won' ORDER BY r.id DESC LIMIT ?""", (limit - 1 or 1,))
        return [f"Tin nhắn đã chốt được đơn:\n{cut(r['text'])}" for r in won]
    return []


def on_lead_status(lead_id: int, status: str):
    """Khách chốt / không mua -> gắn kết quả cho các tin nhắn đã gửi, cộng kinh nghiệm."""
    if status not in ("ordered", "lost"):
        return
    outcome = "won" if status == "ordered" else "lost"
    db.run("UPDATE replies SET outcome=? WHERE lead_id=? AND sent=1 AND outcome IS NULL", (outcome, lead_id))
    if outcome == "won":
        award("ha", 50, "Khách chốt đơn")
        lead = db.one("SELECT post_id FROM leads WHERE id=?", (lead_id,))
        post = db.one("SELECT sale_id FROM posts WHERE id=?", (lead["post_id"],)) if lead and lead.get("post_id") else None
        award("lan", 20, "Bài viết mang về đơn hàng")
        if post and post.get("sale_id"):
            award(f"sale-{post['sale_id']}", 20, "Bài đăng mang về đơn hàng")


def on_post_leads(post_id: int, delta: int):
    if delta <= 0:
        return
    post = db.one("SELECT sale_id FROM posts WHERE id=?", (post_id,))
    award("lan", 20 * delta, "Bài viết có khách mới")
    award("tuan", 10 * delta, "Nhóm chọn đúng, có khách mới")
    if post and post.get("sale_id"):
        award(f"sale-{post['sale_id']}", 10 * delta, "Bài đăng có khách mới")


# ---------------------------------------------------------------- 3. kinh nghiệm, cấp độ
def level_for(xp: int) -> int:
    return 1 + int(math.sqrt(max(xp, 0) / 50))


def xp_for_level(level: int) -> int:
    return 50 * (level - 1) ** 2


def award(agent_id: str, xp: int, reason: str = ""):
    if xp <= 0:
        return
    row = db.one("SELECT * FROM agent_progress WHERE agent_id=?", (agent_id,))
    old_xp = row["xp"] if row else 0
    new_xp = old_xp + xp
    lv_old, lv_new = level_for(old_xp), level_for(new_xp)
    db.run("""INSERT INTO agent_progress(agent_id, xp, level, updated_at) VALUES (?,?,?,?)
              ON CONFLICT(agent_id) DO UPDATE SET xp=excluded.xp, level=excluded.level, updated_at=excluded.updated_at""",
           (agent_id, new_xp, lv_new, db.now()))
    if lv_new > lv_old:
        db.log(agent_id, "Lên cấp", f"Đạt cấp {lv_new} ({reason})")


def progress(agent_id: str) -> dict:
    r = db.one("SELECT * FROM agent_progress WHERE agent_id=?", (agent_id,)) or {"xp": 0, "goal": None}
    lv = level_for(r["xp"])
    return {"xp": r["xp"], "level": lv, "level_xp": xp_for_level(lv), "next_xp": xp_for_level(lv + 1), "goal": r.get("goal")}


def _pct(a, b):
    return round(100 * a / b) if b else None


def skills(agent_id: str) -> list[dict]:
    """Chỉ số kỹ năng tuần này so với tuần trước."""
    def win(f):
        now, d7, d14 = db.now(), _ago(7), _ago(14)
        return f(d7, now), f(d14, d7)
    one = lambda sql, p: db.one(sql, p)["n"] or 0
    out = []
    if agent_id == "lan":
        def appr(a, b):
            rows = db.q("SELECT kind, COUNT(*) n FROM feedback WHERE created_at BETWEEN ? AND ? GROUP BY kind", (a, b))
            d = {r["kind"]: r["n"] for r in rows}
            return _pct(d.get("approve", 0), sum(d.values()))
        out.append({"label": "Bài sếp duyệt ngay", "unit": "%", "now_prev": win(appr)})
    if agent_id in ("lan", "tuan") or agent_id.startswith("sale-"):
        cond = "AND sale_id=?" if agent_id.startswith("sale-") else ""
        extra = (int(agent_id[5:]),) if agent_id.startswith("sale-") else ()
        def lpp(a, b):
            r = db.one(f"SELECT COUNT(*) n, SUM(COALESCE(leads,0)) l FROM posts WHERE status='posted' AND posted_at BETWEEN ? AND ? {cond}", (a, b, *extra))
            return round((r["l"] or 0) / r["n"], 2) if r["n"] else None
        out.append({"label": "Khách mỗi bài", "unit": "", "now_prev": win(lpp)})
    if agent_id == "tuan" or agent_id.startswith("sale-"):
        cond = "AND sale_id=?" if agent_id.startswith("sale-") else ""
        extra = (int(agent_id[5:]),) if agent_id.startswith("sale-") else ()
        def ok(a, b):
            r = db.q(f"""SELECT status, COUNT(*) n FROM posts WHERE status IN ('posted','failed')
                         AND COALESCE(posted_at, scheduled_for) BETWEEN ? AND ? {cond} GROUP BY status""", (a, b, *extra))
            d = {x["status"]: x["n"] for x in r}
            return _pct(d.get("posted", 0), d.get("posted", 0) + d.get("failed", 0))
        out.append({"label": "Đăng thành công", "unit": "%", "now_prev": win(ok)})
    if agent_id.startswith("sale-"):
        sid = int(agent_id[5:])
        out.append({"label": "Lượt up bài", "unit": "", "now_prev": win(lambda a, b: one(
            "SELECT COUNT(*) n FROM bumps WHERE sale_id=? AND status='done' AND done_at BETWEEN ? AND ?", (sid, a, b)))})
    if agent_id == "ha":
        def close(a, b):
            r = db.q("SELECT status, COUNT(*) n FROM leads WHERE updated_at BETWEEN ? AND ? AND status IN ('ordered','lost') GROUP BY status", (a, b))
            d = {x["status"]: x["n"] for x in r}
            return _pct(d.get("ordered", 0), d.get("ordered", 0) + d.get("lost", 0))
        out.append({"label": "Tỉ lệ chốt đơn", "unit": "%", "now_prev": win(close)})
        out.append({"label": "Tin nhắn đã gửi", "unit": "", "now_prev": win(lambda a, b: one(
            "SELECT COUNT(*) n FROM replies WHERE sent=1 AND sent_at BETWEEN ? AND ?", (a, b)))})
    if agent_id == "khoa":
        def cover(a, b):
            r = db.one("""SELECT COUNT(*) n, SUM(CASE WHEN COALESCE(comments,0)+COALESCE(leads,0)>0 THEN 1 ELSE 0 END) d
                          FROM posts WHERE status='posted' AND posted_at BETWEEN ? AND ?""", (a, b))
            return _pct(r["d"] or 0, r["n"])
        out.append({"label": "Bài có số liệu kết quả", "unit": "%", "now_prev": win(cover)})
    if agent_id == "ceo":
        out.append({"label": "Khách có SĐT của cả phòng", "unit": "", "now_prev": win(lambda a, b: one(
            "SELECT COUNT(*) n FROM leads WHERE phone IS NOT NULL AND phone!='' AND COALESCE(phone_at, created_at) BETWEEN ? AND ?", (a, b)))})
        out.append({"label": "Doanh thu (triệu đồng)", "unit": "", "now_prev": win(lambda a, b: round(one(
            "SELECT COALESCE(SUM(amount),0) n FROM orders WHERE created_at BETWEEN ? AND ?", (a, b)) / 1_000_000, 1))})
    if agent_id == "minh":
        def done(a, b):
            r = db.q("SELECT status, COUNT(*) n FROM tasks WHERE created_at BETWEEN ? AND ? GROUP BY status", (a, b))
            d = {x["status"]: x["n"] for x in r}
            return _pct(d.get("done", 0), sum(d.values()))
        out.append({"label": "Việc giao được hoàn thành", "unit": "%", "now_prev": win(done)})
    if agent_id in CORE:
        out.append({"label": "Bài học mới", "unit": "", "now_prev": win(lambda a, b: one(
            "SELECT COUNT(*) n FROM lessons WHERE agent_id=? AND created_at BETWEEN ? AND ?", (agent_id, a, b)))})
    for s in out:
        s["now"], s["prev"] = s.pop("now_prev")
    return out


# ---------------------------------------------------------------- sổ tay bài học
def active_lessons(agent_id: str) -> list[dict]:
    return db.q("""SELECT * FROM lessons WHERE agent_id=? AND status='active'
                   ORDER BY pinned DESC, confidence DESC, updated_at DESC""", (agent_id,))


def add_lesson(agent_id: str, text: str, evidence: str = "", source: str = "auto", confidence: float = 0.6,
               rule_key: str | None = None, pinned: int = 0) -> int | None:
    text = re.sub(r"\s+", " ", (text or "")).strip()[:300]
    if len(text) < 8 or (source != "boss" and BANNED.search(text)):
        return None
    if rule_key:
        old = db.one("SELECT id FROM lessons WHERE agent_id=? AND rule_key=? AND status='active'", (agent_id, rule_key))
        if old:
            db.run("UPDATE lessons SET text=?, evidence=?, confidence=?, updated_at=? WHERE id=?",
                   (text, evidence[:400], confidence, db.now(), old["id"]))
            return old["id"]
    norm = lambda t: re.sub(r"[^\w]+", " ", t.lower()).strip()[:60]
    for l in active_lessons(agent_id):
        if norm(l["text"]) == norm(text):
            return l["id"]
    lid = db.run("""INSERT INTO lessons(agent_id, text, evidence, source, rule_key, confidence, pinned, status, created_at, updated_at)
                    VALUES (?,?,?,?,?,?,?,'active',?,?)""",
                 (agent_id, text, (evidence or "")[:400], source, rule_key, confidence, pinned, db.now(), db.now()))
    if source != "boss":
        award(agent_id, 5, "Rút ra bài học mới")
    return lid


def consolidate(agent_id: str):
    rows = [l for l in active_lessons(agent_id) if not l["pinned"]]
    for l in sorted(rows, key=lambda l: (l["confidence"], l["updated_at"]))[:max(0, len(rows) - MAX_ACTIVE)]:
        db.run("UPDATE lessons SET status='retired', updated_at=? WHERE id=?", (db.now(), l["id"]))


def prompt_block(agent_id: str) -> str:
    """Phần kinh nghiệm thêm vào system prompt (ngắn để giữ chi phí)."""
    ls = active_lessons(agent_id)[:PROMPT_LESSONS]
    goal = progress(agent_id).get("goal")
    ex = best_examples(agent_id)
    if not (ls or goal or ex):
        return ""
    parts = ["\n\nKINH NGHIỆM BẠN ĐÃ HỌC (áp dụng khi phù hợp, không được vượt quy tắc của công ty):"]
    parts += [f"- {l['text']}" for l in ls]
    if goal:
        parts.append(f"Mục tiêu hôm nay của bạn: {goal}")
    if ex:
        parts.append("Ví dụ mẫu đã hiệu quả (học cách viết, không chép nguyên văn):")
        parts += ex
    return "\n".join(parts)


# ---------------------------------------------------------------- phản tỉnh mỗi đêm
ANGLE = mock_brain.ANGLES


def _name(dim: str, k: str) -> str:
    if dim == "angle":
        return ANGLE.get(k, k)
    if dim == "product_id":
        r = db.one("SELECT name FROM products WHERE id=?", (k,))
        return r["name"] if r else f"SP {k}"
    if dim == "group_id":
        r = db.one("SELECT name FROM groups WHERE id=?", (k,))
        return r["name"] if r else f"Nhóm {k}"
    if dim == "hour":
        return f"{int(k)}h–{int(k) + 1}h"
    return k


def _best_worst(dim: str, min_n: int = 3):
    p = perf(dim)
    items = [(k, v) for k, v in p["items"].items() if v["n"] >= min_n]
    if len(items) < 2:
        return None
    items.sort(key=lambda kv: -kv[1]["smoothed"])
    return p, items[0], items[-1]


def evidence(agent_id: str) -> dict:
    """Gói dữ liệu ngắn gọn cho agent tự xem lại."""
    def table(dim, top=6):
        p = perf(dim)
        rows = sorted(p["items"].items(), key=lambda kv: -kv[1]["smoothed"])[:top]
        return [{"muc": _name(dim, k), "so_bai": v["n"], "khach": v["leads"], "binh_luan": v["comments"], "diem_tb": v["avg"]} for k, v in rows]
    e = {"ky": "30 ngày gần nhất", "diem_bai": f"khách × {LEAD_W} + bình luận"}
    if agent_id == "lan":
        e["theo_goc"] = table("angle")
        e["theo_san_pham"] = table("product_id")
        e["sep_duyet_theo_goc"] = {ANGLE.get(k, k): v for k, v in approval().items()}
        e["ly_do_sep_loai"] = [r["reason"] for r in db.q("SELECT reason FROM feedback WHERE kind='reject' AND reason!='' ORDER BY id DESC LIMIT 6")]
        e["sep_sua"] = [{"truoc": (r["before"] or "")[:220], "sau": (r["after"] or "")[:220]}
                        for r in db.q("SELECT before, after FROM feedback WHERE kind='edit' ORDER BY id DESC LIMIT 2")]
    elif agent_id == "tuan":
        e["theo_nhom"] = table("group_id", 8)
        e["theo_gio"] = table("hour", 8)
        e["loi_dang"] = [r["error"][:120] for r in db.q("SELECT error FROM posts WHERE status='failed' AND error IS NOT NULL ORDER BY id DESC LIMIT 5")]
        e["bai_bi_go"] = db.one("SELECT COUNT(*) n FROM posts WHERE permalink_status='removed'")["n"]
        e["bai_cho_duyet"] = db.one("SELECT COUNT(*) n FROM posts WHERE permalink_status='pending'")["n"]
    elif agent_id == "ha":
        e["tin_nhan"] = db.q("SELECT COALESCE(outcome,'chua_ro') ket_qua, COUNT(*) n FROM replies WHERE sent=1 GROUP BY outcome")
        e["chot_theo_loai_khach"] = db.q("""SELECT business_type loai, SUM(status='ordered') chot, SUM(status='lost') mat, COUNT(*) tong
                                            FROM leads GROUP BY business_type""")
        e["tin_da_chot"] = [r["text"][:300] for r in db.q("SELECT text FROM replies WHERE outcome='won' ORDER BY id DESC LIMIT 2")]
        e["tin_khong_chot"] = [r["text"][:300] for r in db.q("SELECT text FROM replies WHERE outcome='lost' ORDER BY id DESC LIMIT 2")]
    elif agent_id == "khoa":
        e["tong"] = {"bai_7_ngay": db.one("SELECT COUNT(*) n FROM posts WHERE status='posted' AND posted_at>=?", (_ago(7),))["n"],
                     "khach_7_ngay": db.one("SELECT COUNT(*) n FROM leads WHERE created_at>=?", (_ago(7),))["n"],
                     "khach_7_ngay_truoc": db.one("SELECT COUNT(*) n FROM leads WHERE created_at BETWEEN ? AND ?", (_ago(14), _ago(7)))["n"]}
        e["ky_nang_doi"] = {a: skills(a) for a in ("lan", "tuan", "ha")}
    elif agent_id == "minh":
        e["cuoc_hop"] = [{"chu_de": r["topic"], "ket_luan": (r["summary"] or "")[:260]} for r in
                         db.q("SELECT topic, summary FROM meetings WHERE status='done' ORDER BY id DESC LIMIT 3")]
        e["viec"] = db.q("SELECT status, COUNT(*) n FROM tasks WHERE created_at>=? GROUP BY status", (_ago(14),))
    elif agent_id == "ceo":
        import ceo
        p = ceo.potential()
        e["tiem_nang"] = {k: p[k] for k in ("per_day", "quota_pct", "last7", "prev7", "verdict")}
        e["quyet_dinh_gan_day"] = [{"loai": r["kind"], "noi_dung": r["title"], "ly_do": (r["reason"] or "")[:200]}
                                   for r in db.q("SELECT kind, title, reason FROM ceo_decisions ORDER BY id DESC LIMIT 5")]
        e["sale_bi_sa_thai"] = db.q("SELECT name, fire_reason FROM sales WHERE status='fired' ORDER BY fired_at DESC LIMIT 3")
    return e


def rule_lessons(agent_id: str) -> list[dict]:
    """Bài học rút từ số liệu bằng luật (luôn chạy, không tốn AI)."""
    out = []
    add = lambda key, text, ev, conf: out.append({"rule_key": key, "text": text, "evidence": ev, "confidence": conf})
    if agent_id == "lan":
        bw = _best_worst("angle")
        if bw:
            p, (bk, bv), (wk, wv) = bw
            if bv["smoothed"] > wv["smoothed"] * 1.3:
                add("angle", f"Ưu tiên góc '{_name('angle', bk)}' (điểm {bv['avg']}/bài); hạn chế góc '{_name('angle', wk)}' ({wv['avg']}/bài).",
                    f"{bv['n']} và {wv['n']} bài trong 30 ngày", min(0.9, 0.5 + (bv["n"] + wv["n"]) / 40))
        bw = _best_worst("product_id")
        if bw:
            p, (bk, bv), _ = bw
            if bv["smoothed"] > p["mean"] * 1.2:
                add("product", f"Sản phẩm '{_name('product_id', bk)}' đang hút khách sỉ nhất ({bv['leads']} khách / {bv['n']} bài), nên viết nhiều hơn.",
                    f"Điểm TB {bv['avg']} so với mức chung {p['mean']}", 0.7)
        ed = db.q("SELECT before, after FROM feedback WHERE kind='edit' AND created_at>=?", (_ago(30),))
        if len(ed) >= 2:
            ratio = sum(len((r["after"] or "").split()) for r in ed) / max(1, sum(len((r["before"] or "").split()) for r in ed))
            words = int(sum(len((r["after"] or "").split()) for r in ed) / len(ed))
            if ratio < 0.85:
                add("length", f"Sếp thường rút ngắn bài; nên viết khoảng {words} chữ.", f"{len(ed)} lần sửa, còn {round(ratio * 100)}% độ dài", 0.75)
            elif ratio > 1.15:
                add("length", f"Sếp thường viết thêm chi tiết; bài nên dài khoảng {words} chữ.", f"{len(ed)} lần sửa", 0.7)
        rs = db.q("SELECT reason, COUNT(*) n FROM feedback WHERE kind='reject' AND reason!='' AND created_at>=? GROUP BY reason ORDER BY n DESC LIMIT 1", (_ago(30),))
        if rs and rs[0]["n"] >= 2:
            add("reject", f"Lý do sếp hay loại bài nhất: '{rs[0]['reason']}'. Kiểm tra kỹ điểm này trước khi nộp bài.", f"{rs[0]['n']} lần", 0.8)
    elif agent_id == "tuan":
        bw = _best_worst("group_id", 2)
        if bw:
            p, (bk, bv), (wk, wv) = bw
            add("group", f"Nhóm '{_name('group_id', bk)}' hiệu quả nhất ({bv['leads']} khách / {bv['n']} bài); nhóm '{_name('group_id', wk)}' kém nhất.",
                f"Điểm TB {bv['avg']} so với {wv['avg']}", 0.7)
        gh = golden_hours()
        if gh:
            add("hours", "Giờ vàng đăng bài: " + ", ".join(f"{h}h" for h in gh) + ". Ưu tiên xếp lịch vào các khung này.",
                "Theo điểm hiệu quả bài 30 ngày", 0.7)
        rm = db.q("""SELECT g.name, COUNT(*) n FROM posts p JOIN groups g ON g.id=p.group_id
                     WHERE p.permalink_status IN ('removed','pending') GROUP BY g.id HAVING n>=2 ORDER BY n DESC LIMIT 1""")
        if rm:
            add("strict", f"Nhóm '{rm[0]['name']}' hay gỡ hoặc giữ bài chờ duyệt ({rm[0]['n']} bài); đọc kỹ luật nhóm và giãn cách lâu hơn.", "", 0.75)
    elif agent_id == "ha":
        r = db.one("SELECT SUM(outcome='won') w, SUM(outcome='lost') l FROM replies WHERE sent=1")
        if (r["w"] or 0) + (r["l"] or 0) >= 4:
            add("close", f"Tỉ lệ chốt sau tin nhắn hiện là {_pct(r['w'] or 0, (r['w'] or 0) + (r['l'] or 0))}%. Giữ cách mở lời của các tin đã chốt.",
                f"{r['w']} chốt / {r['l']} mất", 0.6)
        bt = db.q("""SELECT business_type t, SUM(status='ordered') o, COUNT(*) n FROM leads WHERE business_type!=''
                     GROUP BY business_type HAVING n>=3 ORDER BY 1.0*o/n DESC LIMIT 1""")
        if bt and bt[0]["o"]:
            add("segment", f"Nhóm khách '{bt[0]['t']}' dễ chốt nhất ({bt[0]['o']}/{bt[0]['n']}); ưu tiên trả lời họ trước.", "", 0.65)
    elif agent_id == "khoa":
        r = db.one("""SELECT COUNT(*) n, SUM(CASE WHEN COALESCE(comments,0)+COALESCE(leads,0)>0 THEN 1 ELSE 0 END) d
                      FROM posts WHERE status='posted' AND posted_at>=?""", (_ago(14),))
        if r["n"] >= 4 and _pct(r["d"] or 0, r["n"]) < 50:
            add("data", f"Chỉ {_pct(r['d'] or 0, r['n'])}% bài có số liệu kết quả. Nhắc sếp nhập số khách và gắn khách với bài đăng để cả đội học chính xác hơn.",
                f"{r['n']} bài trong 14 ngày", 0.8)
    elif agent_id.startswith("sale-"):
        sid = int(agent_id[5:])
        r = db.one("SELECT SUM(status='posted') ok, SUM(status='failed') f FROM posts WHERE sale_id=? AND COALESCE(posted_at, scheduled_for)>=?", (sid, _ago(14)))
        if (r["f"] or 0) >= 2:
            err = db.one("SELECT error FROM posts WHERE sale_id=? AND status='failed' ORDER BY id DESC LIMIT 1", (sid,))
            add("fail", f"Nick hay lỗi khi đăng ({r['f']} lần/14 ngày). Lỗi gần nhất: {(err or {}).get('error', '')[:120]}", "", 0.7)
    return out


def _llm_reflect(agent_id: str) -> dict | None:
    from agents import system_prompt
    from llm import llm
    if not llm.live:
        return None
    ev = evidence(agent_id)
    old = [{"id": l["id"], "bai_hoc": l["text"]} for l in active_lessons(agent_id) if not l["pinned"]][:10]
    prompt = f"""Cuối ngày, hãy tự xem lại công việc của bạn để giỏi hơn.
Dữ liệu thật: {json.dumps(ev, ensure_ascii=False)}
Bài học bạn đang có: {json.dumps(old, ensure_ascii=False)}
Yêu cầu:
- Rút ra tối đa 2 bài học MỚI, ngắn (dưới 35 chữ), cụ thể, làm được ngay, có bằng chứng từ dữ liệu. Không có bằng chứng thì không rút.
- Chỉ ra id các bài học cũ đã sai hoặc không còn đúng với dữ liệu để bỏ.
- Đặt 1 mục tiêu đo được cho ngày mai (dưới 25 chữ).
- Tuyệt đối không đề xuất tăng số bài, rút ngắn giãn cách, lách luật nhóm hay hứa công dụng chữa bệnh.
Trả về JSON: {{"new": [{{"text": "...", "evidence": "...", "confidence": 0.5-0.9}}], "retire": [id], "goal": "..."}}"""
    return llm.json(system_prompt(agent_id, db.get_settings(), with_learning=False), prompt, mock=None, max_tokens=450, task="learning")


def reflect(agent_id: str) -> dict:
    """Một agent tự học: luật thống kê + (nếu có API) phản tỉnh bằng AI."""
    count = lambda: db.one("SELECT COUNT(*) n FROM lessons WHERE agent_id=?", (agent_id,))["n"]
    before = count()
    for l in rule_lessons(agent_id):
        add_lesson(agent_id, l["text"], l["evidence"], "auto", l["confidence"], l["rule_key"])
    goal = None
    if agent_id in CORE:
        r = None
        try:
            r = _llm_reflect(agent_id)
        except Exception as e:
            print("[learning]", e)
        if isinstance(r, dict):
            for n in (r.get("new") or [])[:2]:
                if isinstance(n, dict):
                    add_lesson(agent_id, n.get("text", ""), str(n.get("evidence", "")), "ai", float(n.get("confidence") or 0.6))
            for lid in r.get("retire") or []:
                db.run("UPDATE lessons SET status='retired', updated_at=? WHERE id=? AND agent_id=? AND pinned=0", (db.now(), lid, agent_id))
            goal = (r.get("goal") or "").strip()[:160] or None
        if not goal:
            goal = default_goal(agent_id)
        db.run("""INSERT INTO agent_progress(agent_id, xp, level, goal, updated_at) VALUES (?,0,1,?,?)
                  ON CONFLICT(agent_id) DO UPDATE SET goal=excluded.goal, updated_at=excluded.updated_at""", (agent_id, goal, db.now()))
    consolidate(agent_id)
    return {"agent_id": agent_id, "added": count() - before, "goal": goal}


def default_goal(agent_id: str) -> str | None:
    if agent_id == "lan":
        if perf("angle")["n"] < 6:
            return "Viết đủ các góc tiếp cận khác nhau để tìm ra góc mang về nhiều khách nhất."
        w = weights("angle", list(ANGLE))
        least = min(ANGLE, key=lambda a: perf("angle")["items"].get(a, {}).get("n", 0))
        best = max(w, key=w.get)
        return f"Viết ít nhất 1 bài góc '{ANGLE[best]}' và thử 1 bài góc '{ANGLE[least]}' để so sánh."
    if agent_id == "tuan":
        gh = golden_hours()
        return f"Xếp ít nhất một nửa số bài vào giờ vàng {', '.join(f'{h}h' for h in gh)}." if gh else "Ghi đủ link bài và kết quả để tìm ra giờ đăng hiệu quả."
    if agent_id == "ha":
        n = db.one("SELECT COUNT(*) n FROM leads WHERE status='new'")["n"]
        return f"Liên hệ hết {n} khách mới trong hôm nay." if n else "Hỏi lại các khách đã gửi mẫu xem phản hồi."
    if agent_id == "khoa":
        return "Đảm bảo bài đăng hôm qua đều có số bình luận và số khách."
    if agent_id == "minh":
        return "Theo dõi để các việc giao trong cuộc họp được hoàn thành trong ngày."
    if agent_id == "ceo":
        try:
            import ceo, company
            o = ceo.overview()
            if o["next_milestone"]:
                gap = o["next_milestone"]["amount"] - o["revenue"]
                return f"Đưa doanh thu tới mốc {company.fmt_vnd(o['next_milestone']['amount'])} (còn thiếu {company.fmt_vnd(gap)}) để tăng người."
            return "Giữ mọi nick đạt KPI tháng, không để ai bị sa thải."
        except Exception:
            return None
    return None


def nightly(force: bool = False) -> list[dict]:
    """Chạy mỗi đêm (Cài đặt → Tự học) hoặc khi sếp bấm 'Cho cả đội học ngay'."""
    if _running["on"]:
        return []
    _running["on"] = True
    try:
        import workflows
        res = []
        ids = CORE + [f"sale-{r['id']}" for r in db.q("SELECT id FROM sales")]
        for a in ids:
            workflows.set_status(a, "working", "Đang tự xem lại và rút kinh nghiệm")
            res.append(reflect(a))
            workflows.set_status(a, "idle", "Vừa học xong bài học hôm nay")
        total = sum(r["added"] for r in res)
        db.set_setting("learn_last_date", db.today())
        db.log("khoa", "Tự học", f"Cả đội rút ra {total} bài học mới, đặt mục tiêu cho ngày mai")
        return res
    finally:
        _running["on"] = False


def nightly_async():
    threading.Thread(target=nightly, daemon=True).start()


def from_meeting(mid: int, summary: str, topic: str):
    if summary:
        add_lesson("minh", f"Quyết định họp ({topic[:60]}): {summary[:200]}", "", "meeting", 0.55, f"meeting-{mid}")
        consolidate("minh")


def overview() -> dict:
    """Dữ liệu cho trang Đào tạo."""
    import agents
    out = []
    for a in agents.public_list():
        aid = a["id"]
        out.append({"id": aid, "name": a["name"], "role": a["role"], "kind": a.get("kind"), "look": a["look"],
                    "progress": progress(aid), "skills": skills(aid), "lessons": active_lessons(aid),
                    "retired": db.one("SELECT COUNT(*) n FROM lessons WHERE agent_id=? AND status='retired'", (aid,))["n"]})
    angles = weights("angle", list(ANGLE))
    prods = db.q("SELECT id, name FROM products ORDER BY id")
    pw = weights("product_id", [p["id"] for p in prods]) if prods else {}
    return {"agents": out, "running": _running["on"], "last": db.get_settings().get("learn_last_date"),
            "choices": {"angles": [{"name": ANGLE[k], "weight": v, **perf("angle")["items"].get(k, {"n": 0, "avg": 0})} for k, v in angles.items()],
                        "products": [{"name": p["name"], "weight": pw.get(str(p["id"]), 0), **perf("product_id")["items"].get(str(p["id"]), {"n": 0, "avg": 0})} for p in prods],
                        "golden_hours": golden_hours(),
                        "explore": float(db.get_settings().get("learn_explore") or 0.25)}}

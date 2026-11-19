"""Nhi tự học từ kết quả thật của các Trang xu hướng (thống kê, không tốn AI; chạy mỗi đêm cùng cả đội ở learning.nightly).

Điểm bài = cảm xúc + 2 × bình luận + 3 × chia sẻ, chia cho mức trung bình của chính Trang đó (1,0 = bình thường), để Trang lớn
không lấn Trang nhỏ. Nhi học:
1. Kiểu bài: bám tin nóng hay bài bền (không gắn tin nóng).
2. Độ dài bài: ngắn / vừa / dài.
3. Khung giờ đăng (gợi ý sếp đổi giờ, không tự đổi).
4. Chủ đề nào được hưởng ứng, chủ đề nào không (đưa vào đề bài đọc xu hướng sáng hôm sau).
5. Tự chấm mắt chọn xu hướng: chủ đề Nhi chấm từ 70 điểm có còn nằm trong xu hướng những ngày sau không (nóng bền hay chớp nhoáng).
Chỉ rút bài học khi đủ mẫu và chênh lệch rõ (z ≥ learn_z), luôn chừa một phần (learn_explore) để thử kiểu ít dùng.
Bài học chỉ đổi cách viết / chọn chủ đề, không đổi số bài mỗi ngày hay giờ đăng sếp đặt.
"""
import random
import re
from datetime import datetime, timedelta

import db

ENG = "(COALESCE(p.reactions,0)+2*COALESCE(p.comments,0)+3*COALESCE(p.shares,0))"
KIND = {"trend": "bám tin nóng", "evergreen": "bền (không gắn tin nóng)"}
LEN = [(0, 80, "short", "ngắn (dưới 80 chữ)", "50–80 chữ"), (80, 120, "mid", "vừa (80–120 chữ)", "80–120 chữ"),
       (120, 10 ** 6, "long", "dài (trên 120 chữ)", "120–170 chữ")]
SLOT = [(0, 5, "night", "đêm (0–5h)"), (5, 11, "morning", "sáng (5–11h)"), (11, 14, "noon", "trưa (11–14h)"),
        (14, 18, "afternoon", "chiều (14–18h)"), (18, 24, "evening", "tối (18–24h)")]
NAME = {"kind": KIND, "length": {k: lb for _, _, k, lb, _ in LEN}, "slot": {k: lb for _, _, k, lb in SLOT}}


def _ago(days: int) -> str:
    return (db.clock() - timedelta(days=days)).strftime("%Y-%m-%d %H:%M:%S")


def _cfg(k: str, d: float) -> float:
    try:
        return float(db.get_settings().get(k) or d)
    except ValueError:
        return d


def min_n() -> int:
    """Số bài tối thiểu của mỗi lựa chọn trước khi so sánh (Trang đăng ít hơn nhóm nên ngưỡng riêng, mặc định 8)."""
    return int(_cfg("trend_learn_min", 8))


def kind_of(topic: str | None, pg: dict) -> str:
    t = (topic or "").strip().lower()
    return "evergreen" if not t or t in ((pg.get("niche") or "").lower(), (pg.get("name") or "").lower()) else "trend"


def rows(days: int = 30) -> list[dict]:
    """Bài Trang đã đăng kèm điểm tương đối so với mức của chính Trang."""
    rs = db.q(f"""SELECT p.id, p.fb_page_ref page_id, p.content, p.trend_topic, p.trend_kind, p.posted_at, {ENG} eng,
                         f.name page_name, f.niche FROM posts p JOIN fb_pages f ON f.id=p.fb_page_ref
                  WHERE p.status='posted' AND p.posted_at >= ?""", (_ago(days),))
    mean = {}
    for r in rs:
        m = mean.setdefault(r["page_id"], [0, 0])
        m[0] += r["eng"] or 0
        m[1] += 1
    for r in rs:
        s, n = mean[r["page_id"]]
        r["rel"] = round(((r["eng"] or 0) + 1) / (s / n + 1), 3)  # +1 làm mượt khi Trang còn ít tương tác
        r["kind"] = r["trend_kind"] or kind_of(r["trend_topic"], {"niche": r["niche"], "name": r["page_name"]})
        w = len((r["content"] or "").split())
        r["length"] = next(k for a, b, k, _, _ in LEN if a <= w < b)
        h = int((r["posted_at"] or "00:00:00 00")[11:13] or 0)
        r["slot"] = next(k for a, b, k, _ in SLOT if a <= h < b)
    return rs


def _agg(items: list[dict]) -> dict:
    n = len(items)
    s = sum(x["rel"] for x in items)
    return {"n": n, "score": s, "sq": sum(x["rel"] ** 2 for x in items), "avg": round(s / n, 2) if n else 0}


def table(dim: str, rs: list[dict]) -> dict:
    g = {}
    for r in rs:
        g.setdefault(r[dim], []).append(r)
    return {k: _agg(v) for k, v in g.items()}


def best_worst(dim: str, rs: list[dict]):
    """(tốt nhất, kém nhất, z) khi cả hai đủ mẫu và chênh lệch đủ rõ; không thì None."""
    import learning
    t = [(k, v) for k, v in table(dim, rs).items() if v["n"] >= min_n()]
    if len(t) < 2:
        return None
    t.sort(key=lambda kv: -kv[1]["avg"])
    z = learning.z_score(t[0][1], t[-1][1])
    return (t[0], t[-1], z) if abs(z) >= _cfg("learn_z", 1.96) else None


def calibration(days: int = 21, skip: int = 2) -> dict:
    """Chủ đề Nhi chấm từ 70 điểm: còn trong xu hướng Google ở 1–3 ngày sau không (nóng bền) hay chỉ một ngày.
    Bỏ `skip` ngày gần nhất (chưa đủ ngày sau để biết)."""
    end = (db.clock() - timedelta(days=skip)).strftime("%Y-%m-%d")
    start = _ago(days)[:10]
    hot = db.q("SELECT title, day FROM trend_hot WHERE score >= 70 AND day >= ? AND day <= ?", (start, end))
    seen = {}
    for t in db.q("SELECT title, day FROM trends WHERE day > ? AND day <= date(?, '+3 day')", (start, end)):
        seen.setdefault(t["day"], []).append(_words(t["title"]))
    nxt = lambda d, k: (datetime.strptime(d, "%Y-%m-%d") + timedelta(days=k)).strftime("%Y-%m-%d")
    hits = []
    for h in hot:
        w = _words(h["title"])  # so theo cụm từ, không phân biệt hoa thường (SQLite lower() không hạ chữ có dấu)
        hits.append(bool(w) and any(w <= x or (x and x <= w) for k in (1, 2, 3) for x in seen.get(nxt(h["day"], k), [])))
    n, hit = len(hot), sum(hits)
    return {"n": n, "hit": hit, "pct": round(100 * hit / n) if n else None,
            "flash": [h["title"] for h, ok in zip(hot, hits) if not ok][:5]}


def _words(t: str | None) -> frozenset:
    return frozenset(re.findall(r"\w+", (t or "").casefold()))


def topics(rs: list[dict], top: int = 5) -> tuple[list, list]:
    g = {}
    for r in rs:
        if r["kind"] == "trend" and r["trend_topic"]:
            g.setdefault(r["trend_topic"], []).append(r["rel"])
    t = sorted(((k, round(sum(v) / len(v), 2), len(v)) for k, v in g.items()), key=lambda x: -x[1])
    return t[:top], [x for x in t[-3:] if x[1] < 1][::-1] if len(t) > top else []


# ---------------------------------------------------------------- bài học (learning.reflect gọi mỗi đêm)
def rule_lessons() -> list[dict]:
    rs = rows()
    out = []
    add = lambda key, text, ev, conf: out.append({"rule_key": key, "text": text, "evidence": ev, "confidence": conf})
    for dim, what in (("kind", "Kiểu bài"), ("length", "Độ dài"), ("slot", "Khung giờ")):
        bw = best_worst(dim, rs)
        if not bw:
            continue
        (bk, bv), (wk, wv), z = bw
        conf = min(0.9, 0.5 + (bv["n"] + wv["n"]) / 80)
        ev = f"{bv['n']} và {wv['n']} bài Trang 30 ngày, z={z}"
        x = round(bv["avg"] / max(0.01, wv["avg"]), 1)
        if dim == "kind":
            add("tp_kind", f"Bài {KIND[bk]} được hưởng ứng gấp {x} lần bài {KIND[wk]}: ưu tiên bài {KIND[bk]}.", ev, conf)
        elif dim == "length":
            add("tp_len", f"Bài Trang {NAME['length'][bk]} được tương tác nhiều nhất (gấp {x} lần bài {NAME['length'][wk]}): viết độ dài này.", ev, conf)
        else:
            add("tp_slot", f"Bài Trang đăng {NAME['slot'][bk]} được tương tác gấp {x} lần {NAME['slot'][wk]}: gợi ý sếp dời giờ đăng vào khung này.", ev, conf)
    c = calibration()
    if c["n"] >= 10 and c["pct"] < 40:
        add("tp_calib", f"Chỉ {c['pct']}% chủ đề mình chấm từ 70 điểm còn nóng hôm sau: chỉ chấm cao chủ đề đã lặp lại từ 2 ngày hoặc có cộng đồng hỏi lâu dài.",
            f"{c['hit']}/{c['n']} chủ đề 3 tuần qua", 0.7)
    good, bad = topics(rs)
    if bad and bad[0][2] >= 2 and len(rs) >= 2 * min_n():
        add("tp_topic", f"Chủ đề '{bad[0][0]}' ít được hưởng ứng ({bad[0][1]}× mức thường): tránh chủ đề kiểu này.", f"{bad[0][2]} bài", 0.55)
    return out


def evidence() -> dict:
    rs = rows()
    good, bad = topics(rs)
    tb = lambda dim: {NAME[dim].get(k, k): {"so_bai": v["n"], "diem_tb": v["avg"]} for k, v in table(dim, rs).items()}
    return {"ky": "30 ngày", "diem_bai": "tương tác so với mức thường của Trang (1,0 = bình thường)", "so_bai": len(rs),
            "theo_kieu": tb("kind"), "theo_do_dai": tb("length"), "theo_khung_gio": tb("slot"),
            "chu_de_hay": good, "chu_de_kem": bad, "do_chinh_xac_chon_xu_huong": calibration()}


def default_goal() -> str:
    rs = rows()
    if len(rs) < 2 * min_n():
        return f"Đăng đủ bài và đọc tương tác ({len(rs)}/{2 * min_n()} bài) để biết kiểu bài nào hợp mỗi Trang."
    least = min(KIND, key=lambda k: table("kind", rs).get(k, {}).get("n", 0))
    return f"Thử ít nhất 1 bài {KIND[least]} và giữ chủ đề nóng bền để so sánh."


def skills() -> list[dict]:
    """Chỉ số tuần này / tuần trước (dạng now_prev như learning.skills)."""
    def eng(a, b):
        r = db.one(f"SELECT COUNT(*) n, AVG({ENG}) e FROM posts p WHERE p.fb_page_ref IS NOT NULL AND p.status='posted' AND p.posted_at BETWEEN ? AND ?", (a, b))
        return round(r["e"] or 0, 1) if r["n"] else None
    now, d7, d14 = db.now(), _ago(7), _ago(14)
    return [{"label": "Tương tác TB mỗi bài Trang", "unit": "", "now_prev": (eng(d7, now), eng(d14, d7))},
            {"label": "Chủ đề chấm cao còn nóng hôm sau", "unit": "%", "now_prev": (calibration(9)["pct"], calibration(16, 9)["pct"])}]


# ---------------------------------------------------------------- áp dụng khi làm việc
def style(pg: dict) -> dict:
    """Kiểu bài, độ dài và bài mẫu cho lượt viết này. Đủ số liệu thì theo kiểu hiệu quả, vẫn chừa phần thử."""
    rs = rows()
    out = {"kind": None, "words": None, "notes": [], "example": None}
    explore = random.random() < _cfg("learn_explore", 0.25)
    bw = best_worst("kind", rs)
    if bw:
        out["kind"] = bw[1][0] if explore else bw[0][0]
        out["notes"].append(f"Số liệu: bài {KIND[bw[0][0]]} hiệu quả hơn bài {KIND[bw[1][0]]}" + (" (lượt này thử kiểu còn lại để kiểm tra lại)" if explore else ""))
    bw = best_worst("length", rs)
    if bw and not explore:
        out["words"] = next(w for _, _, k, _, w in LEN if k == bw[0][0])
        out["notes"].append(f"Bài {NAME['length'][bw[0][0]]} được tương tác nhiều nhất")
    mine = sorted((r for r in rs if r["page_id"] == pg["id"] and (r["eng"] or 0) > 0), key=lambda r: -r["rel"])
    if mine and mine[0]["rel"] >= 1.3:
        out["example"] = (mine[0]["content"] or "")[:450]
    return out


def research_note() -> str:
    """Kết quả chủ đề cũ + độ chính xác, đưa vào đề bài đọc xu hướng để Nhi chấm điểm sát hơn."""
    rs = rows()
    good, bad = topics(rs)
    c = calibration()
    lines = []
    if good:
        lines.append("Chủ đề bài Trang được hưởng ứng (× mức thường): " + "; ".join(f"{t} {v}×" for t, v, _ in good))
    if bad:
        lines.append("Chủ đề ít hưởng ứng: " + "; ".join(f"{t} {v}×" for t, v, _ in bad))
    if c["n"] >= 5:
        lines.append(f"Độ chính xác của bạn: {c['pct']}% chủ đề bạn chấm từ 70 còn nóng 1–3 ngày sau ({c['hit']}/{c['n']})"
                     + (f"; chỉ nóng một ngày: {', '.join(c['flash'][:3])}" if c["flash"] else ""))
    return "\n".join(lines)


def best_slots(pg_id: int | None = None) -> list[str]:
    bw = best_worst("slot", rows())
    return [NAME["slot"][bw[0][0]]] if bw else []


def overview() -> dict:
    """Thẻ “Nhi tự học” trên trang Trang xu hướng."""
    rs = rows()
    good, bad = topics(rs)
    tb = lambda dim: [{"key": k, "label": NAME[dim].get(k, k), "n": v["n"], "avg": v["avg"]}
                      for k, v in sorted(table(dim, rs).items(), key=lambda kv: -kv[1]["avg"])]
    lessons = db.q("""SELECT text, evidence, confidence, source FROM lessons WHERE agent_id='nhi' AND status='active'
                      ORDER BY pinned DESC, confidence DESC LIMIT 6""")
    return {"n": len(rs), "need": 2 * min_n(), "min_n": min_n(), "kind": tb("kind"), "length": tb("length"), "slot": tb("slot"),
            "good": [{"topic": t, "x": v, "n": n} for t, v, n in good], "bad": [{"topic": t, "x": v, "n": n} for t, v, n in bad],
            "calib": calibration(), "lessons": lessons, "best_slot": best_slots()}

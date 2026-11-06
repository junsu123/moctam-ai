"""Sếp chỉ đạo nơi đăng bài: đăng ở nhóm có từ khóa nào, tập trung vào nhóm nào, tránh nhóm nào.

- mode "all":    Tuấn xếp lịch như cũ (mọi nhóm đủ điều kiện), chỉ bỏ nhóm có từ khóa cấm.
- mode "prefer": ưu tiên nhóm sếp ghim "Tập trung đăng", rồi nhóm có từ khóa, rồi tới nhóm khác.
- mode "only":   chỉ đăng vào nhóm Tập trung đăng hoặc nhóm có từ khóa; không có nhóm nào khớp thì không đăng nhóm.
Từ khóa so khớp với tên nhóm, chủ đề và từ khóa tìm ra nhóm, không phân biệt dấu, hoa thường.
"""
import re

import db
from knowledge import plain

MODES = {"all": "Mọi nhóm đủ điều kiện", "prefer": "Ưu tiên nhóm chỉ định", "only": "Chỉ nhóm chỉ định"}


def words(raw: str) -> list[str]:
    out = []
    for w in re.split(r"[,;\n]+", raw or ""):
        w = w.strip()
        if w and plain(w) not in {plain(x) for x in out}:
            out.append(w[:60])
    return out[:40]


def settings() -> dict:
    st = db.get_settings()
    mode = st.get("post_target_mode") or "all"
    return {"mode": mode if mode in MODES else "all", "include": words(st.get("post_group_keywords") or ""),
            "exclude": words(st.get("post_group_exclude") or "")}


def save(mode: str | None = None, include=None, exclude=None) -> dict:
    if mode is not None:
        if mode not in MODES:
            raise ValueError("Chế độ không hợp lệ")
        db.set_setting("post_target_mode", mode)
    for key, v in (("post_group_keywords", include), ("post_group_exclude", exclude)):
        if v is not None:
            db.set_setting(key, ", ".join(words(", ".join(v) if isinstance(v, list) else v)))
    c = settings()
    db.log("tuan", "Nhận chỉ đạo nơi đăng", f"{MODES[c['mode']]} · từ khóa: {', '.join(c['include']) or '—'} · "
           f"tránh: {', '.join(c['exclude']) or '—'}")
    return c


def _text(g: dict) -> str:
    return " " + plain(f"{g.get('name') or ''} {g.get('topic') or ''} {g.get('keyword') or ''}") + " "


def hit(g: dict, kws: list[str]) -> str | None:
    """Từ khóa đầu tiên khớp với nhóm (khớp trọn cụm từ, không dấu)."""
    t = _text(g)
    for k in kws:
        p = plain(k).strip()
        if p and re.search(r"(?<![a-z0-9])" + re.escape(p) + r"(?![a-z0-9])", t):
            return k
    return None


def classify(g: dict, c: dict | None = None) -> tuple[str, str]:
    """('exclude' | 'focus' | 'match' | 'other', lý do)."""
    c = c or settings()
    w = hit(g, c["exclude"])
    if w:
        return "exclude", f"có từ khóa tránh “{w}”"
    if g.get("focus"):
        return "focus", "sếp chọn tập trung đăng"
    w = hit(g, c["include"])
    if w:
        return "match", f"có từ khóa “{w}”"
    return "other", ""


def active(c: dict | None = None) -> bool:
    c = c or settings()
    return c["mode"] != "all" or bool(c["exclude"])


def apply(groups: list[dict]) -> list[dict]:
    """Lọc và sắp lại danh sách nhóm Tuấn định xếp lịch theo chỉ đạo của sếp (giữ thứ tự cũ trong cùng một hạng)."""
    c = settings()
    rank = {"focus": 0, "match": 1, "other": 2}
    out = []
    for i, g in enumerate(groups):
        k, _ = classify(g, c)
        if k == "exclude" or (c["mode"] == "only" and k == "other"):
            continue
        out.append((rank[k] if c["mode"] != "all" else 0, i, g))
    out.sort(key=lambda x: (x[0], x[1]))
    return [g for _, _, g in out]


def set_focus(gid: int, on: bool) -> dict:
    g = db.one("SELECT id, name FROM groups WHERE id=?", (gid,))
    if not g:
        raise KeyError(gid)
    db.run("UPDATE groups SET focus=? WHERE id=?", (1 if on else 0, gid))
    db.log("tuan", "Tập trung đăng" if on else "Bỏ tập trung đăng", g["name"][:80])
    return {"id": gid, "focus": 1 if on else 0}


def preview(c: dict | None = None) -> dict:
    """Xem trước nhóm nào sẽ được đăng theo chỉ đạo hiện tại."""
    c = c or settings()
    rows = db.q("""SELECT id, name, url, topic, keyword, members, COALESCE(focus,0) focus, COALESCE(managed,0) managed,
                   COALESCE(leads_count,0) leads, COALESCE(eng_score,0) eng, verdict, pinned
                   FROM groups WHERE COALESCE(is_sample,0)=0 ORDER BY COALESCE(focus,0) DESC, leads_count DESC, members DESC""")
    cnt = {"focus": 0, "match": 0, "other": 0, "exclude": 0}
    items = []
    for g in rows:
        k, why = classify(g, c)
        posted = not (k == "exclude" or (c["mode"] == "only" and k == "other"))
        ready = bool((g.get("url") or "").strip()) and not (g.get("verdict") == "skip" and not g["leads"] and not g.get("pinned"))
        cnt[k] += 1
        items.append({"id": g["id"], "name": g["name"], "members": g["members"], "focus": g["focus"], "managed": g["managed"],
                      "kind": k, "why": why, "will_post": posted and ready and not g["managed"], "ready": ready})
    usable = sum(1 for i in items if i["will_post"])
    warn = ""
    if c["mode"] == "only" and not usable:
        warn = "Chưa có nhóm nào khớp chỉ đạo: Tuấn sẽ không xếp bài vào nhóm nào. Thêm từ khóa hoặc chọn nhóm tập trung."
    elif c["mode"] != "all" and not (cnt["focus"] + cnt["match"]):
        warn = "Chưa có nhóm nào khớp từ khóa: Tuấn vẫn đăng các nhóm khác như bình thường."
    order = {"focus": 0, "match": 1, "other": 2, "exclude": 3}
    items.sort(key=lambda i: (order[i["kind"]], not i["will_post"]))
    return {"counts": cnt, "will_post": usable, "warn": warn, "items": items[:300]}


def overview() -> dict:
    c = settings()
    focus = db.q("SELECT id, name, members FROM groups WHERE COALESCE(focus,0)=1 ORDER BY name")
    return {**c, "modes": MODES, "focus": focus, "preview": preview(c)}


def prompt_line() -> str:
    """Một dòng cho Tuấn và CEO biết sếp đang chỉ đạo đăng ở đâu."""
    c = settings()
    if not active(c):
        return ""
    focus = [g["name"] for g in db.q("SELECT name FROM groups WHERE COALESCE(focus,0)=1 LIMIT 8")]
    parts = [MODES[c["mode"]]]
    if focus:
        parts.append("nhóm tập trung: " + "; ".join(focus))
    if c["include"]:
        parts.append("từ khóa: " + ", ".join(c["include"]))
    if c["exclude"]:
        parts.append("tránh nhóm có: " + ", ".join(c["exclude"]))
    return "\n\nCHỈ ĐẠO NƠI ĐĂNG CỦA SẾP: " + " · ".join(parts)


# ---------------------------------------------------------------- lệnh một lần: "đăng bài lên các nhóm có từ khóa X"
def push_get() -> dict | None:
    """Đợt đăng theo từ khóa sếp giao hôm nay (còn hiệu lực tới hết ngày)."""
    import json
    try:
        p = json.loads(db.get_settings().get("kw_push") or "{}")
    except Exception:
        return None
    return p if p.get("date") == db.today() and p.get("keywords") else None


def push_set(kws: list[str], count: int) -> dict:
    import json
    p = {"date": db.today(), "keywords": kws, "count": count, "at": db.now()}
    db.set_setting("kw_push", json.dumps(p, ensure_ascii=False))
    return p


def push_groups(kws: list[str]) -> dict:
    """Nhóm khớp từ khóa: tổng số, số nhóm đăng được ngay (có link, hết giãn cách, chưa có bài chờ), lý do nhóm còn lại."""
    import workflows
    c = settings()
    taken = {r["group_id"] for r in db.q("SELECT group_id FROM posts WHERE status IN ('scheduled','posting') AND group_id IS NOT NULL")}
    found, ready, why = [], [], {"Thiếu link nhóm": 0, "Đang giãn cách (vừa đăng)": 0, "Đã có bài chờ đăng": 0, "Sếp đã cấm": 0,
                                 "Tuấn đánh giá không nên đăng": 0}
    for g in db.q("SELECT * FROM groups WHERE COALESCE(is_sample,0)=0 AND COALESCE(managed,0)=0"):
        if not hit(g, kws):
            continue
        found.append(g)
        if hit(g, c["exclude"]):
            why["Sếp đã cấm"] += 1
        elif g.get("verdict") == "skip" and not g.get("leads_count") and not g.get("pinned"):
            why["Tuấn đánh giá không nên đăng"] += 1
        elif not (g.get("url") or "").strip():
            why["Thiếu link nhóm"] += 1
        elif g["id"] in taken:
            why["Đã có bài chờ đăng"] += 1
        elif not workflows.group_ready(g):
            why["Đang giãn cách (vừa đăng)"] += 1
        else:
            ready.append(g)
    return {"found": found, "ready": ready, "why": {k: v for k, v in why.items() if v}}


def filter_push(groups: list[dict], kws: list[str]) -> list[dict]:
    c = settings()
    return [g for g in groups if hit(g, kws) and not hit(g, c["exclude"])]

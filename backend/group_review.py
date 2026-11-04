"""Tuấn (chuyên viên hội nhóm) đánh giá nhóm sale vừa khảo sát: có nên cho nick vào nhóm không.

Sale mở từng nhóm tìm được, đọc chỉ số (trang Giới thiệu + bảng tin): bài mới mỗi ngày/tháng, thành viên mới mỗi tuần,
cảm xúc và bình luận trung bình mỗi bài, bài mới nhất cách đây bao lâu, tỉ lệ bài rao bán, luật nhóm có cấm bán hàng không.

Tuấn so các chỉ số đó với "chuẩn nhóm tương tác cao":
- Mặc định: 10 bài/ngày, mỗi bài 20 cảm xúc và 5 bình luận, thêm 0,5% thành viên mỗi tuần (sếp sửa được).
- Khi đã có nhóm thật mang về khách (và đã đo chỉ số), chuẩn lấy theo trung vị các nhóm mang về nhiều khách nhất.

Chấm điểm 100: tương tác mỗi bài 45 (bình luận 25, cảm xúc 20; bình luận nặng hơn vì khách hỏi giá nằm ở bình luận),
độ sôi nổi (bài/ngày) 20, đúng chủ đề 10, quy mô 10, tăng trưởng 10, bài mới nhất 5; trừ điểm nhóm toàn bài rao bán mà
không ai bình luận. Loại ngay: không đúng chủ đề, quá ít thành viên, luật cấm bán hàng/quảng cáo, nhóm chết.
Kết luận: Nên vào (≥ 60 điểm VÀ tương tác mỗi bài đạt từ 60% chuẩn) → tự thêm vào Hội nhóm và cho nick xin vào, nhóm điểm
cao xin trước. Nhóm riêng tư chưa xem được bài: Nên vào khi số bài mỗi ngày đạt chuẩn (vào rồi đọc bài, chấm lại).
Cân nhắc (40–59, hoặc điểm cao nhưng tương tác mỗi bài thấp) → để sếp xem; Bỏ qua (< 40 hoặc bị loại).
Không gọi AI nên không tốn tiền.
"""
import html
import math
import statistics

import db

METRICS = ("members", "posts_per_day", "posts_today", "posts_month", "new_members_week", "avg_reactions", "avg_comments",
           "sampled_posts", "last_post_hours", "selling_ratio", "no_selling", "rules_note", "privacy", "scouted_at")
VERDICT_TXT = {"join": "Nên vào", "consider": "Cân nhắc", "skip": "Bỏ qua"}


def _f(v, d=0.0) -> float:
    try:
        return float(v) if v is not None and v != "" else d
    except (TypeError, ValueError):
        return d


def n(x) -> str:
    """Số kiểu Việt Nam: 12.400"""
    x = _f(x)
    return f"{x:,.0f}".replace(",", ".") if x >= 100 or x == int(x) else f"{x:.1f}".replace(".", ",")


def per_day(c: dict) -> float | None:
    """Số bài mỗi ngày: ưu tiên bài trong tháng (ổn định hơn), rồi bài hôm nay, rồi số Facebook ghi ở kết quả tìm kiếm."""
    if c.get("posts_month") not in (None, ""):
        return _f(c["posts_month"]) / 30
    if c.get("posts_today") not in (None, ""):
        return _f(c["posts_today"])
    return _f(c.get("posts_per_day")) or None


def growth_pct(c: dict) -> float | None:
    if c.get("new_members_week") in (None, "") or not _f(c.get("members")):
        return None
    return _f(c["new_members_week"]) / _f(c["members"]) * 100


# ---------------------------------------------------------------- chuẩn nhóm tương tác cao
def benchmark() -> dict:
    st = db.get_settings()
    b = {"posts_day": _f(st.get("review_posts_day"), 10), "avg_reactions": _f(st.get("review_avg_reactions"), 20),
         "avg_comments": _f(st.get("review_avg_comments"), 5), "growth_week": _f(st.get("review_growth_week"), 0.5),
         "min_members": int(_f(st.get("review_min_members"), 1000)), "join_score": _f(st.get("review_join_score"), 60),
         "consider_score": _f(st.get("review_consider_score"), 40), "source": "default", "ref_groups": []}
    if st.get("review_use_best_groups", "1") != "1":
        return b
    ref = db.q("""SELECT * FROM groups WHERE leads_count > 0 AND COALESCE(sampled_posts,0) >= 3
                  ORDER BY leads_count DESC LIMIT 5""")
    if len(ref) < 2:
        return b

    def med(vals, base):  # trung vị nhóm tốt nhất, giữ trong khoảng 0,5–2 lần chuẩn mặc định cho khỏi lệch
        vals = [v for v in vals if v is not None]
        return round(max(base * 0.5, min(base * 2, statistics.median(vals))), 1) if vals else base
    b.update(posts_day=med([per_day(g) for g in ref], b["posts_day"]),
             avg_reactions=med([_f(g["avg_reactions"]) for g in ref], b["avg_reactions"]),
             avg_comments=med([_f(g["avg_comments"]) for g in ref], b["avg_comments"]),
             growth_week=med([growth_pct(g) for g in ref], b["growth_week"]),
             source="best", ref_groups=[{"id": g["id"], "name": g["name"], "leads": g["leads_count"]} for g in ref])
    return b


def bench_text(b: dict) -> str:
    t = (f"{n(b['posts_day'])} bài/ngày, mỗi bài {n(b['avg_reactions'])} cảm xúc và {n(b['avg_comments'])} bình luận, "
         f"+{n(b['growth_week'])}% thành viên/tuần")
    if b["source"] == "best":
        t += " (theo các nhóm mang về nhiều khách nhất: " + ", ".join(g["name"] for g in b["ref_groups"][:3]) + ")"
    return t


# ---------------------------------------------------------------- chấm điểm
def evaluate(c: dict, b: dict | None = None) -> dict:
    """Trả về {score, verdict, reasons, good, bad} cho một nhóm (ứng viên hoặc nhóm đã có)."""
    b = b or benchmark()
    good, bad, stop = [], [], []
    rel = _f(c.get("relevance"), 1.0 if c.get("relevance") is None else 0)
    mem = _f(c.get("members"))
    ppd = per_day(c)
    sampled = int(_f(c.get("sampled_posts")))
    r, cm = _f(c.get("avg_reactions")), _f(c.get("avg_comments"))
    g = growth_pct(c)
    age = c.get("last_post_hours")
    age = None if age in (None, "") else _f(age)

    # loại ngay
    if rel <= 0:
        stop.append("tên nhóm không khớp chủ đề đang tìm")
    if mem and mem < b["min_members"]:
        stop.append(f"chỉ {n(mem)} thành viên (cần từ {n(b['min_members'])})")
    if int(_f(c.get("no_selling"))):
        stop.append("luật nhóm cấm bán hàng/quảng cáo" + (f" (“{c['rules_note'][:80]}”)" if c.get("rules_note") else ""))
    if (age is not None and age > 24 * 7) or (c.get("posts_month") not in (None, "") and _f(c["posts_month"]) < 10):
        stop.append("nhóm gần như không còn hoạt động" + (f" (bài mới nhất cách đây {int(age // 24)} ngày)" if age and age > 24 * 7 else ""))

    sc = rel * 10
    sc += min(math.log10(mem + 1) / 5, 1) * 10 if mem else 3
    if ppd is None:
        sc += 6
        bad.append("chưa đọc được số bài mỗi ngày")
    else:
        sc += min(ppd / b["posts_day"], 1) * 20
        (good if ppd >= b["posts_day"] * 0.6 else bad).append(f"{n(ppd)} bài/ngày")
    eng_ok = None  # tương tác mỗi bài có đạt 60% chuẩn không (None: chưa xem được bài)
    if sampled >= 3:
        cr, rr = cm / b["avg_comments"], r / b["avg_reactions"]
        sc += min(cr, 1) * 25 + min(rr, 1) * 20
        eng_ok = cr >= 0.6 or (rr >= 0.6 and cr >= 0.4)
        txt = f"mỗi bài TB {n(r)} cảm xúc, {n(cm)} bình luận"
        (good if eng_ok else bad).append(txt + ("" if eng_ok else f" (chuẩn {n(b['avg_reactions'])} cảm xúc, {n(b['avg_comments'])} bình luận)"))
        sr = _f(c.get("selling_ratio"))
        if sr >= 0.7 and cm < 1:
            sc -= 20
            bad.append(f"{int(sr * 100)}% bài là rao bán mà gần như không ai bình luận (chợ spam)")
    else:
        sc += 18
        bad.append("chưa xem được bài trong nhóm" + (" (nhóm riêng tư, sẽ đánh giá lại sau khi vào)" if c.get("privacy") == "private" else ""))
    if g is None:
        sc += 4
    else:
        sc += min(g / b["growth_week"], 1) * 10 if b["growth_week"] else 0
        (good if g >= b["growth_week"] * 0.5 else bad).append(f"+{n(c['new_members_week'])} thành viên/tuần ({n(g)}%)")
    if age is None:
        sc += 2
    else:
        sc += 5 if age <= 6 else 3 if age <= 24 else 1 if age <= 72 else 0
        if age <= 24:
            good.append("có bài mới trong ngày" if age > 1 else "có bài mới trong giờ qua")
        elif age > 72:
            bad.append(f"bài mới nhất cách đây {int(age // 24)} ngày")
    sc = round(max(0.0, min(100.0, sc)), 1)
    verdict = "skip" if stop else "join" if sc >= b["join_score"] else "consider" if sc >= b["consider_score"] else "skip"
    if verdict == "join" and eng_ok is False:
        verdict = "consider"  # nhóm đông bài nhưng ít người tương tác: không tự vào, để sếp xem
        bad.append("tương tác mỗi bài thấp hơn 60% chuẩn nên chưa tự vào")
    if verdict == "join" and eng_ok is None and (ppd or 0) < b["posts_day"]:
        verdict = "consider"  # chưa xem được bài: chỉ tự vào khi nhóm rất sôi nổi
        bad.append("chưa xem được tương tác và số bài/ngày dưới chuẩn nên chưa tự vào")
    if stop:
        reasons = "Loại: " + "; ".join(stop)
    else:
        reasons = "; ".join(x for x in (("Mạnh: " + ", ".join(good)) if good else "",
                                        ("Yếu: " + ", ".join(bad)) if bad else "") if x)
    return {"score": sc, "verdict": verdict, "reasons": reasons, "good": good, "bad": bad, "stop": stop}


def _save(table: str, row_id: int, ev: dict):
    db.run(f"UPDATE {table} SET eng_score=?, verdict=?, review_note=?, reviewed_at=? WHERE id=?",
           (ev["score"], ev["verdict"], ev["reasons"][:600], db.now(), row_id))


# ---------------------------------------------------------------- Tuấn duyệt các nhóm sale vừa khảo sát
def review_candidates(ids: list[int] | None = None, by: str = "") -> dict:
    """Đánh giá các nhóm đã khảo sát mà chưa đánh giá (hoặc các id chỉ định). Nhóm "Nên vào" được thêm vào Hội nhóm."""
    import group_finder
    b = benchmark()
    if ids:
        rows = db.q(f"SELECT * FROM group_candidates WHERE id IN ({','.join('?' * len(ids))})", tuple(ids))
    else:
        rows = db.q("""SELECT * FROM group_candidates WHERE status='new' AND scouted_at IS NOT NULL
                       AND (reviewed_at IS NULL OR reviewed_at < scouted_at)""")
    out = {"join": [], "consider": [], "skip": []}
    for c in rows:
        ev = evaluate(c, b)
        _save("group_candidates", c["id"], ev)
        if ev["verdict"] == "skip" and c["status"] == "new":
            db.run("UPDATE group_candidates SET status='rejected' WHERE id=?", (c["id"],))
        out[ev["verdict"]].append({**c, "eng_score": ev["score"], "verdict": ev["verdict"], "review_note": ev["reasons"]})
    for k in out:
        out[k].sort(key=lambda x: -x["eng_score"])
    added = group_finder.auto_add()
    out["added"] = added
    if rows:
        db.log("tuan", "Đánh giá nhóm",
               f"Xem {len(rows)} nhóm{(' ' + by + ' vừa khảo sát') if by else ''}: nên vào {len(out['join'])}, cân nhắc "
               f"{len(out['consider'])}, bỏ qua {len(out['skip'])}. Đã thêm {len(added)} nhóm vào Hội nhóm để xin vào"
               + (": " + ", ".join(g["name"] for g in added[:3]) if added else ""))
        _telegram(out, b, by)
    return out


def _line(c: dict) -> str:
    bits = [f"{n(c['members'])} tv" if c.get("members") else ""]
    ppd = per_day(c)
    if ppd is not None:
        bits.append(f"{n(ppd)} bài/ngày")
    if int(_f(c.get("sampled_posts"))) >= 3:
        bits.append(f"TB {n(c['avg_reactions'])} cảm xúc · {n(c['avg_comments'])} bình luận")
    if c.get("new_members_week") not in (None, ""):
        bits.append(f"+{n(c['new_members_week'])} tv/tuần")
    return (f"• <b>{html.escape(c['name'][:70])}</b> — {n(c['eng_score'])} điểm · " + " · ".join(x for x in bits if x)
            + f"\n  <i>{html.escape((c.get('review_note') or '')[:220])}</i>")


def _telegram(out: dict, b: dict, by: str):
    try:
        import telegram_bot as T
        if not T.report_enabled():
            return
        parts = [f"🧐 <b>Tuấn đánh giá {sum(len(out[k]) for k in ('join', 'consider', 'skip'))} nhóm</b>"
                 + (f" {html.escape(by)} vừa khảo sát" if by else ""),
                 f"Chuẩn nhóm tương tác cao: {html.escape(bench_text(b))}."]
        for k, icon in (("join", "✅"), ("consider", "⚖️"), ("skip", "⛔")):
            if out[k]:
                parts.append(f"\n{icon} <b>{VERDICT_TXT[k]} ({len(out[k])})</b>")
                parts += [_line(c) for c in out[k][:6]]
        if out.get("added"):
            parts.append(f"\n➕ Đã thêm {len(out['added'])} nhóm vào Hội nhóm, các nick sẽ xin vào nhóm điểm cao trước.")
        if out["consider"]:
            parts.append("Nhóm “Cân nhắc” chờ sếp xem ở Hội nhóm → Tìm nhóm mới.")
        T.send("\n".join(parts))
    except Exception as e:
        print("[group_review]", e)


def review_group(group_id: int) -> dict | None:
    """Đánh giá lại một nhóm đã có trong danh sách (VD: sau khi nick vào được nhóm riêng tư và đọc được bài)."""
    g = db.one("SELECT * FROM groups WHERE id=?", (group_id,))
    if not g:
        return None
    ev = evaluate({**g, "relevance": 1}, benchmark())
    _save("groups", group_id, ev)
    return ev


def rereview_all() -> dict:
    """Sếp đổi tiêu chí: Tuấn chấm lại mọi nhóm đã khảo sát (ứng viên chưa thêm + nhóm trong danh sách)."""
    b = benchmark()
    cnt = {"join": 0, "consider": 0, "skip": 0}
    for c in db.q("SELECT * FROM group_candidates WHERE status IN ('new','rejected') AND scouted_at IS NOT NULL"):
        ev = evaluate(c, b)
        _save("group_candidates", c["id"], ev)
        db.run("UPDATE group_candidates SET status=? WHERE id=?", ("rejected" if ev["verdict"] == "skip" else "new", c["id"]))
        cnt[ev["verdict"]] += 1
    for g in db.q("SELECT id FROM groups WHERE scouted_at IS NOT NULL"):
        review_group(g["id"])
    import group_finder
    added = group_finder.auto_add()
    db.log("tuan", "Đánh giá nhóm", f"Chấm lại theo tiêu chí mới: nên vào {cnt['join']}, cân nhắc {cnt['consider']}, "
           f"bỏ qua {cnt['skip']}; thêm {len(added)} nhóm vào Hội nhóm")
    return {**cnt, "added": len(added)}

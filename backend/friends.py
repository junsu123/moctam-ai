"""Kết bạn với thành viên trong nhóm: Tuấn chấm nhóm nào sôi nổi nhất mà nick đang ở, mở bảng tin nhóm đó,
chọn ra người đang đăng bài / bình luận hợp tệp khách (người bán hàng online, người hỏi nguồn hàng trà, ngũ cốc).

Phần mềm KHÔNG tự bấm "Thêm bạn bè". Gửi lời mời kết bạn hàng loạt cho người lạ bằng công cụ tự động là hành vi
spam Meta cấm và là lý do nick hay bị khóa nhất. Tuấn chỉ nghiên cứu và chuẩn bị danh sách; sale bấm
“Mở hồ sơ” để Chrome của nick mở sẵn vài trang cá nhân, rồi tự tay bấm Thêm bạn bè và đánh dấu “Đã gửi”.
Mỗi nick có trần lời mời mỗi ngày (fbp_friends_day, nick mới / vừa bị chặn còn một nửa).
"""
import math
import re

import db
import junk
from knowledge import plain

SHOP_RX = re.compile(r"(\bshop\b|ban hang|ban online|\border\b|\bship\b|inbox|dat hang|nhan si|\bctv\b|dai ly|kinh doanh|"
                     r"livestream|tiktok shop|shopee|\bsi le\b|\bsale\b|ban le|tap hoa|cua hang)")
STATUS_TXT = {"suggested": "Chờ gửi", "opened": "Đã mở hồ sơ", "sent": "Đã gửi lời mời", "accepted": "Đã đồng ý",
              "skipped": "Bỏ qua"}


def s() -> dict:
    return db.get_settings()


def _f(x, d: float = 0.0) -> float:
    try:
        return float(x)
    except (TypeError, ValueError):
        return d


# ---------------------------------------------------------------- nhóm nào sôi nổi nhất
def activity(g: dict) -> dict:
    """Điểm sôi nổi 0–100 của một nhóm từ chỉ số Tuấn đã đọc: bài mỗi ngày, bình luận, cảm xúc, thành viên mới, quy mô."""
    import group_review
    pd = group_review.per_day(g) or 0
    gr = group_review.growth_pct(g) or 0
    ac, ar, m = _f(g.get("avg_comments")), _f(g.get("avg_reactions")), _f(g.get("members"))
    parts = {"posts": min(30.0, pd * 3), "comments": min(30.0, ac * 3), "reactions": min(15.0, ar / 2),
             "growth": min(15.0, gr * 15), "size": min(10.0, math.log10(m) * 2) if m >= 10 else 0.0}
    score = sum(parts.values())
    lp = g.get("last_post_hours")
    if lp not in (None, "") and _f(lp) > 72:  # 3 ngày không ai đăng: nhóm đang chết
        score *= 0.5
    known = any(g.get(k) not in (None, "") for k in ("posts_month", "posts_today", "avg_comments", "avg_reactions", "new_members_week"))
    return {"score": int(round(score)), "parts": {k: round(v, 1) for k, v in parts.items()}, "known": known,
            "per_day": round(pd, 1), "growth": round(gr, 2)}


def _nick_groups(aid: int) -> list[dict]:
    import my_groups
    import accounts
    out = []
    for g in db.q("SELECT * FROM groups WHERE COALESCE(url,'')!='' AND COALESCE(is_sample,0)=0"):
        st = my_groups.membership(g, aid)
        if st in ("ok", "rest") or (st == "unknown" and accounts.can_post_in(g, aid)):
            out.append(g)
    return out


def active_groups(aid: int | None = None, limit: int = 30) -> list[dict]:
    """Bảng xếp hạng nhóm sôi nổi nhất (của một nick, hoặc của mọi nick đang làm việc)."""
    import accounts
    import group_target
    accs = [accounts.get(aid)] if aid else accounts.working()
    rows = {}
    for a in accs:
        if not a:
            continue
        for g in _nick_groups(a["id"]):
            r = rows.setdefault(g["id"], {"g": g, "nicks": []})
            r["nicks"].append({"id": a["id"], "name": accounts.label(a)})
    cnt = {r["group_id"]: r for r in db.q("""SELECT group_id, COUNT(*) n, SUM(status IN ('sent','accepted')) sent,
                                             SUM(status='accepted') ok FROM friend_suggestions GROUP BY group_id""")}
    out = []
    for gid, r in rows.items():
        g, act = r["g"], activity(r["g"])
        kind, _ = group_target.classify(g)
        c = cnt.get(gid) or {}
        out.append({"id": gid, "name": g["name"], "url": g["url"], "members": g.get("members"), "score": act["score"],
                    "known": act["known"], "parts": act["parts"], "per_day": act["per_day"], "growth": act["growth"],
                    "avg_comments": g.get("avg_comments"), "avg_reactions": g.get("avg_reactions"),
                    "focus": int(g.get("focus") or 0), "target": kind, "nicks": r["nicks"],
                    "scanned_at": g.get("friends_scanned_at"), "found": c.get("n") or 0, "sent": c.get("sent") or 0,
                    "accepted": c.get("ok") or 0})
    out.sort(key=lambda x: (x["target"] == "exclude", -(x["score"] + (10 if x["focus"] else 0)), -(x["members"] or 0)))
    return out[:limit]


# ---------------------------------------------------------------- trần lời mời mỗi ngày
def quota(aid: int) -> dict:
    import fb_policy
    acc = db.one("SELECT * FROM fb_accounts WHERE id=?", (aid,)) or {}
    f = fb_policy.factor(acc) if acc else 1.0
    lim = max(0, int(int(s().get("fbp_friends_day") or 10) * f))
    used = db.one("SELECT COUNT(*) n FROM friend_suggestions WHERE account_id=? AND sent_at >= ?", (aid, db.today()))["n"]
    resting = bool(acc.get("rest_until") and acc["rest_until"] > db.now())
    return {"limit": 0 if resting else lim, "used": used, "left": 0 if resting else max(0, lim - used), "factor": f,
            "resting": resting}


# ---------------------------------------------------------------- chọn người
def relevance(text: str, comment: bool, times: int) -> tuple[int, list[str]] | None:
    """Điểm hợp tệp khách của một người qua chữ họ viết trong nhóm. None = bỏ (người bán sỉ / xưởng cạnh tranh)."""
    import prospect
    p = plain(text or "")
    if prospect.SUPPLY_RX.search(p):
        return None
    score, why = 20, []
    fit = prospect.fit_text(text or "")
    if prospect.DEMAND_RX.search(p) and fit:
        score += 45
        why.append("Đang hỏi nguồn hàng hợp ngành")
    elif fit:
        score += 20
        why.append("Quan tâm trà, ngũ cốc, đồ uống")
    if SHOP_RX.search(p):
        score += 15
        why.append("Đang bán hàng online")
    if comment:
        score += 5
        why.append("Bình luận trong nhóm")
    else:
        score += 10
        why.append("Đăng bài trong nhóm")
    if times > 1:
        score += min(15, (times - 1) * 5)
        why.append(f"Hoạt động {times} lần trên bảng tin")
    return min(100, score), why


def pick(rows: list[dict], aid: int, group: dict) -> list[dict]:
    """Từ bài + bình luận đọc được trên bảng tin, chọn người đáng kết bạn (chưa nick nào của công ty gợi ý / mời)."""
    import prospect
    me = prospect.our_names()
    # một người chỉ được một nick của công ty mời: nhiều nick cùng mời một người là dấu hiệu mạng lưới tài khoản
    have = {r["profile_url"] for r in db.q("SELECT profile_url FROM friend_suggestions")}
    people = {}
    for r in rows:
        if not r.get("href") or not r.get("author"):
            continue
        name = r["author"].strip()[:80]
        if plain(name) in me or len(name) < 2:
            continue
        c = prospect.canon(r["href"])
        if not c or not prospect._fb_candidate(c) or c in have:
            continue
        p = people.setdefault(c, {"name": name, "texts": [], "comment": True, "times": 0})
        p["times"] += 1
        p["comment"] = p["comment"] and bool(r.get("comment"))
        body = (r.get("text") or "").replace(name, "", 1).strip()
        if body:
            p["texts"].append(body[:300])
    out = []
    for url, p in people.items():
        if junk.blocked(url, name=p["name"]):
            continue
        txt = " · ".join(p["texts"])
        rel = relevance(txt, p["comment"], p["times"])
        if not rel:
            continue
        sc, why = rel
        out.append({"name": p["name"], "profile_url": url, "score": sc, "reason": "; ".join(why),
                    "snippet": re.sub(r"\s+", " ", txt)[:300], "group_id": group["id"]})
    out.sort(key=lambda x: -x["score"])
    return out[:int(s().get("friends_per_group") or 12)]


def save(aid: int, items: list[dict]) -> int:
    n = 0
    for it in items:
        try:
            db.run("""INSERT INTO friend_suggestions (account_id, group_id, name, profile_url, reason, score, snippet, status, created_at)
                      VALUES (?,?,?,?,?,?,?,'suggested',?)""",
                   (aid, it["group_id"], it["name"], it["profile_url"], it["reason"], it["score"], it["snippet"], db.now()))
            n += 1
        except Exception:
            pass  # đã có trong danh sách của nick
    return n


# ---------------------------------------------------------------- nick mở nhóm, đọc bảng tin
def scan_group(page, g: dict) -> tuple[list[dict], dict]:
    """Mở bảng tin nhóm (bài mới nhất), cuộn đọc bài và bình luận. Chỉ đọc, không bấm gì."""
    import random
    import browser_poster as B
    import group_finder
    import prospect
    url = B.fb_url(g["url"]).split("?")[0].rstrip("/") + "/?sorting_setting=CHRONOLOGICAL"
    page.goto(url, wait_until="domcontentloaded", timeout=60000)
    page.wait_for_timeout(int(random.uniform(3.5, 6) * 1000))
    B._check_blocked(page)
    rows = []
    for i in range(6):
        page.mouse.wheel(0, random.randint(1100, 1700))
        page.wait_for_timeout(int(random.uniform(2, 3.5) * 1000))
    try:
        rows = page.evaluate(prospect.GROUP_JS)
    except Exception as e:
        print("[friends scan]", g["name"], e)
    try:
        m = group_finder.read_feed(page, scrolls=0)
    except Exception:
        m = {}
    return rows, m


def job(pw, aid: int, group_ids: list[int] | None = None, notify: str | None = None) -> dict:
    import browser_poster as B
    import workflows
    acc, sale, agent = B._ctx_names(aid)
    res = {"groups": [], "found": 0}
    groups = []
    if group_ids:
        groups = [g for g in (db.one("SELECT * FROM groups WHERE id=?", (i,)) for i in group_ids) if g and g.get("url")]
    else:
        groups = [db.one("SELECT * FROM groups WHERE id=?", (r["id"],)) for r in plan_groups(aid)]
    ctx, page = B._open(pw, aid)
    try:
        if not B._logged_in(ctx):
            raise RuntimeError("Nick chưa đăng nhập. Vào Nhân viên sale → Mở Chrome để đăng nhập lại")
        for g in groups:
            workflows.set_status("tuan", "working", f"Tìm người đáng kết bạn trong nhóm {g['name'][:40]}")
            workflows.set_status(agent, "working", f"Mở bảng tin nhóm {g['name'][:40]} cho Tuấn đọc")
            try:
                rows, m = scan_group(page, g)
            except B.Blocked:
                raise
            except Exception as e:
                print("[friends group]", g["name"], e)
                rows, m = [], {}
            items = pick(rows, aid, g)
            n = save(aid, items)
            sets, args = ["friends_scanned_at=?"], [db.now()]
            m = m or {}
            if (m.get("sampled_posts") or 0) >= 3 and (m.get("avg_reactions") or m.get("avg_comments")):  # cập nhật chỉ số vừa đọc
                for k in ("avg_reactions", "avg_comments", "sampled_posts", "last_post_hours", "selling_ratio"):
                    if m.get(k) is not None:
                        sets.append(f"{k}=?")
                        args.append(m[k])
            db.run(f"UPDATE groups SET {', '.join(sets)} WHERE id=?", (*args, g["id"]))
            res["groups"].append({"name": g["name"], "read": len(rows), "new": n})
            res["found"] += n
            B._pause(page, 5, 12)
    except B.Blocked as e:
        B._block(aid, str(e))
        res["blocked"] = True
    finally:
        try:
            ctx.close()
        except Exception:
            pass
        workflows.set_status("tuan", "idle", "Xong lượt tìm người kết bạn")
        workflows.set_status(agent, "idle", "Chờ việc tiếp theo")
    q = quota(aid)
    msg = (f"Tuấn đọc {len(res['groups'])} nhóm trên nick {acc.get('name')}: thêm {res['found']} người nên kết bạn"
           + (" (" + "; ".join(f"{x['name'][:40]}: {x['new']}" for x in res["groups"]) + ")" if res["groups"] else "")
           + f". Hôm nay nick còn gửi được {q['left']}/{q['limit']} lời mời; sale mở hồ sơ và tự bấm Thêm bạn bè.")
    if res.get("blocked"):
        msg += " Nick bị Facebook kiểm tra nên dừng."
    db.log("tuan", "Gợi ý kết bạn", msg[:600])
    if notify:
        import ceo_orders
        ceo_orders.followup(msg, notify)
    return res


def plan_groups(aid: int) -> list[dict]:
    """Nhóm sôi nổi nhất của nick, lâu chưa đọc (3 ngày), bỏ nhóm sếp cấm đăng."""
    n = int(s().get("friends_groups_per_run") or 2)
    lim = (db.clock().timestamp() - 3 * 86400)
    rows = [g for g in active_groups(aid, 50) if g["target"] != "exclude"]
    from datetime import datetime

    def fresh(g):
        try:
            return datetime.strptime(g["scanned_at"][:19], "%Y-%m-%d %H:%M:%S").timestamp() > lim
        except Exception:
            return False
    todo = [g for g in rows if not fresh(g)] or rows
    return todo[:n]


def start(aid: int | None = None, group_ids: list[int] | None = None, notify: str | None = None) -> dict:
    """Giao cho một nick đi đọc nhóm tìm người kết bạn."""
    import accounts
    import browser_poster as B
    accs = accounts.working()
    if aid:
        accs = [a for a in accs if a["id"] == aid]
    if not accs:
        raise ValueError("Chưa có nick nào đăng nhập và đang làm việc để mở nhóm")
    if not aid:  # nick nào còn nhiều lượt mời nhất, ít gợi ý chờ gửi nhất
        def need(a):
            q = quota(a["id"])
            wait = db.one("SELECT COUNT(*) n FROM friend_suggestions WHERE account_id=? AND status IN ('suggested','opened')",
                          (a["id"],))["n"]
            return (-(q["left"] - wait), a["id"])
        accs.sort(key=need)
    a = accs[0]
    if not group_ids and not plan_groups(a["id"]):
        raise ValueError(f"Nick {accounts.label(a)} chưa ở nhóm nào có link. Vào Hội nhóm → Rà soát nhóm của nick trước")
    B.submit(a["sale_id"], {"kind": "friends", "account": a["id"], "group_ids": group_ids, "notify": notify})
    import workflows
    workflows.set_status("tuan", "working", f"Chờ nick {accounts.label(a)} mở Chrome để đọc nhóm")
    return {"account": accounts.label(a), "account_id": a["id"]}


def tick(now):
    """Mỗi ngày một lượt: nick nào còn lượt mời mà danh sách chờ gửi ít thì Tuấn đi tìm thêm người."""
    import accounts
    st = s()
    if st.get("friends_enabled", "1") != "1" or st.get("friends_last") == db.today():
        return
    if now.strftime("%H:%M") < (st.get("friends_time") or "10:40"):
        return
    db.set_setting("friends_last", db.today())
    for a in accounts.working():
        q = quota(a["id"])
        wait = db.one("SELECT COUNT(*) n FROM friend_suggestions WHERE account_id=? AND status IN ('suggested','opened')",
                      (a["id"],))["n"]
        if q["left"] and wait < q["left"] * 2:
            try:
                start(a["id"])
            except ValueError:
                pass


# ---------------------------------------------------------------- sale gửi lời mời bằng tay
def open_next(aid: int, n: int = 5, ids: list[int] | None = None) -> dict:
    """Mở Chrome của nick với vài trang cá nhân kế tiếp (trong trần còn lại) để sale tự bấm Thêm bạn bè."""
    import accounts
    import browser_poster as B
    acc = accounts.get(aid)
    if not acc:
        raise KeyError(aid)
    q = quota(aid)
    if q["resting"]:
        raise ValueError("Nick đang nghỉ theo Luật Facebook (vừa bị chặn). Chưa gửi lời mời kết bạn")
    if not q["left"]:
        raise ValueError(f"Nick đã gửi đủ {q['limit']} lời mời hôm nay. Mai gửi tiếp để không bị Facebook chặn tính năng kết bạn")
    n = max(1, min(n, q["left"], 10))
    if ids:
        rows = db.q(f"""SELECT * FROM friend_suggestions WHERE account_id=? AND status IN ('suggested','opened')
                        AND id IN ({','.join('?' * len(ids))}) ORDER BY score DESC LIMIT ?""", (aid, *ids, n))
    else:
        rows = db.q("""SELECT * FROM friend_suggestions WHERE account_id=? AND status='suggested'
                       ORDER BY score DESC, id LIMIT ?""", (aid, n))
    if not rows:
        raise ValueError("Chưa có ai trong danh sách chờ gửi. Bấm “Tìm người để kết bạn” trước")
    if B.profile_in_use(aid):
        raise ValueError(B.IN_USE_MSG)
    db.run(f"UPDATE friend_suggestions SET status='opened', opened_at=? WHERE id IN ({','.join('?' * len(rows))})",
           (db.now(), *[r["id"] for r in rows]))
    B.submit(acc["sale_id"], {"kind": "open", "account": aid, "urls": [B.fb_url(r["profile_url"]) for r in rows]})
    db.log("tuan", "Mở hồ sơ để kết bạn", f"Nick {accounts.label(acc)}: {', '.join(r['name'] for r in rows)}")
    return {"opened": [r["id"] for r in rows], "names": [r["name"] for r in rows], "quota": q}


def mark(fid: int, status: str) -> dict:
    if status not in ("suggested", "sent", "accepted", "skipped"):
        raise ValueError("Trạng thái không hợp lệ")
    r = db.one("SELECT * FROM friend_suggestions WHERE id=?", (fid,))
    if not r:
        raise KeyError(fid)
    now = db.now()
    if status == "sent":
        db.run("UPDATE friend_suggestions SET status='sent', sent_at=COALESCE(sent_at, ?) WHERE id=?", (now, fid))
    elif status == "accepted":
        db.run("UPDATE friend_suggestions SET status='accepted', sent_at=COALESCE(sent_at, ?), decided_at=? WHERE id=?",
               (now, now, fid))
    elif status == "skipped":
        db.run("UPDATE friend_suggestions SET status='skipped', decided_at=? WHERE id=?", (now, fid))
    else:
        db.run("UPDATE friend_suggestions SET status='suggested', sent_at=NULL, opened_at=NULL, decided_at=NULL WHERE id=?", (fid,))
    q = quota(r["account_id"])
    return {"id": fid, "status": status, "quota": q,
            "over": status in ("sent", "accepted") and q["used"] > q["limit"]}


def junk_it(fid: int, reason: str = "other", note: str = "") -> dict:
    """Không hợp tệp khách: bỏ qua và cho Mai ghi nhớ là data rác (lần sau không gợi ý, không tìm lại)."""
    r = db.one("SELECT * FROM friend_suggestions WHERE id=?", (fid,))
    if not r:
        raise KeyError(fid)
    junk.mark_url(r["name"], r["profile_url"], reason, note or "Sếp bỏ khi xem gợi ý kết bạn", r.get("snippet") or "")
    return mark(fid, "skipped")


# ---------------------------------------------------------------- giao diện
def overview(aid: int | None = None, status: str = "") -> dict:
    import accounts
    nicks = []
    for a in accounts.working() or db.q("SELECT * FROM fb_accounts WHERE enabled=1 ORDER BY id"):
        q = quota(a["id"])
        c = db.one("""SELECT SUM(status='suggested') wait, SUM(status='opened') opened, SUM(status IN ('sent','accepted')) sent,
                      SUM(status='accepted') ok FROM friend_suggestions WHERE account_id=?""", (a["id"],))
        nicks.append({"id": a["id"], "name": accounts.label(a), "sale": a.get("sale_name"), **q,
                      "wait": c["wait"] or 0, "opened": c["opened"] or 0, "sent_all": c["sent"] or 0, "accepted": c["ok"] or 0})
    where, args = [], []
    if aid:
        where.append("f.account_id=?")
        args.append(aid)
    if status:
        where.append("f.status=?")
        args.append(status)
    else:
        where.append("f.status IN ('suggested','opened')")
    rows = db.q(f"""SELECT f.*, g.name group_name, a.name nick FROM friend_suggestions f LEFT JOIN groups g ON g.id=f.group_id
                    LEFT JOIN fb_accounts a ON a.id=f.account_id WHERE {' AND '.join(where)}
                    ORDER BY CASE f.status WHEN 'opened' THEN 0 WHEN 'suggested' THEN 1 ELSE 2 END, f.score DESC, f.id DESC
                    LIMIT 200""", tuple(args))
    tot = db.one("""SELECT COUNT(*) n, SUM(status IN ('sent','accepted')) sent, SUM(status='accepted') ok,
                    SUM(sent_at >= ?) today FROM friend_suggestions""", (db.today(),))
    sent = tot["sent"] or 0
    return {"nicks": nicks, "groups": active_groups(aid, 15), "items": rows, "status_txt": STATUS_TXT,
            "stats": {"found": tot["n"] or 0, "sent": sent, "accepted": tot["ok"] or 0, "today": tot["today"] or 0,
                      "accept_rate": round((tot["ok"] or 0) * 100 / sent) if sent else None},
            "settings": {k: s().get(k) for k in ("friends_enabled", "friends_time", "friends_groups_per_run", "friends_per_group",
                                                 "fbp_friends_day")}}

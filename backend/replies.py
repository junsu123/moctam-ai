"""Bảo trả lời khách trong nhóm: tìm bài ở nhóm sôi nổi mà người đăng đang HỎI MUA / HỎI NGUỒN HÀNG hợp ngành,
viết câu trả lời có ích (Claude viết, Bảo học dần rồi tự viết), SẾP DUYỆT, nick đang ở nhóm đó gửi trong giờ làm.

Không bình luận dạo vào bài không hỏi mua, không chạy ban đêm, mỗi nick vài bình luận mỗi ngày và giãn cách: bình luận
quảng cáo vào bài người lạ hoặc bình luận suốt đêm là spam theo luật Facebook, nhóm sẽ xóa và nick bị khóa.
"""
import random
import re
from datetime import datetime, timedelta

import db
import junk
import post_care
from knowledge import plain

STATUS = {"draft": "Chờ sếp duyệt", "approved": "Đã duyệt, chờ gửi", "sent": "Đã gửi", "failed": "Gửi lỗi", "skipped": "Bỏ qua"}
CATS = [("tra", "trà"), ("ngu coc", "ngũ cốc"), ("ca phe", "cà phê"), ("bot", "bột"), ("com", "cốm"), ("detox", "trà detox")]


def s() -> dict:
    return db.get_settings()


def contact() -> str:
    return (s().get("reply_contact") or post_care.contact() or "").strip()[:120]


def product_guess(text: str) -> str:
    """Sản phẩm người hỏi đang cần: tên sản phẩm của xưởng có trong bài, không thì nhóm hàng, không thì "trà và ngũ cốc"."""
    t = " " + plain(text or "") + " "
    best = None
    for p in db.q("SELECT name FROM products WHERE COALESCE(is_general,0)=0"):
        short = post_care._short_name(p["name"])
        words = [w for w in plain(short).split() if len(w) > 2][:3]
        if words and all(" " + w + " " in t or w in t for w in words):
            if not best or len(short) > len(best):
                best = short
    if best:
        return best
    for k, name in CATS:
        if re.search(r"(?<![a-z])" + k + r"(?![a-z])", t):
            return name
    return post_care.GENERIC


# ---------------------------------------------------------------- viết câu trả lời (Claude -> Bảo học -> tự viết)
def _claude(posts: list[dict], names: list[str], drafts: list[str]) -> tuple[list[str], list]:
    from llm import llm
    import agents
    ask = ("Viết câu TRẢ LỜI cho từng bài đăng trong nhóm Facebook dưới đây. Người đăng đang hỏi mua / hỏi nguồn hàng; "
           "người trả lời là sale của nhà máy sản xuất trà, ngũ cốc, cà phê, bột (giá sỉ, gia công thương hiệu riêng). "
           "Mỗi câu 15–35 chữ, trả lời đúng điều người đó hỏi, giọng thân thiện như người thật, gợi ý gửi mẫu thử hoặc báo giá, "
           "KHÔNG ghi số điện thoại / Zalo (sẽ tự gắn sau), không hứa chữa bệnh, giảm cân, cam kết 100%, không viết hoa cả câu, "
           "không hashtag, mỗi câu khác nhau. Các bài: "
           + " | ".join(f"{i + 1}. (sản phẩm: {names[i]}) {re.sub(chr(10), ' ', p['post_text'] or '')[:300]}" for i, p in enumerate(posts))
           + ((". Ngoài ra chấm điểm 1–10 các câu Bảo (nhân viên mới) tự viết dưới đây theo đúng yêu cầu trên: "
               + " | ".join(f"{i + 1}. {d}" for i, d in enumerate(drafts))
               + '. Trả về JSON {"lines": ["..."], "scores": [số, ...]}.') if drafts else '. Trả về JSON {"lines": ["..."]}.'))
    d = llm.json(agents.system_prompt("bao", s(), with_learning=False), ask, mock=None, max_tokens=1400, task="posts") or {}
    db.set_setting("bao_claude_calls_reply", str(int(s().get("bao_claude_calls_reply") or 0) + 1))
    got = []
    for x in d.get("lines") or []:
        x = re.sub(r"\s+", " ", str(x)).strip().strip('"“”')
        got.append("" if re.search(r"(?i)zalo|sđt|sdt|hotline|\d[\d .]{7,}\d", x) else " ".join(x.split()[:40]))
    return got, d.get("scores") or []


def write(posts: list[dict]) -> list[tuple[str, str]]:
    """[(câu trả lời có dòng liên hệ, nguồn 'claude'|'bao')] cho từng bài."""
    from llm import llm
    if not posts:
        return []
    names = [product_guess(p["post_text"]) for p in posts]
    avoid = {plain(r["reply"] or "") for r in db.q("SELECT reply FROM reply_tasks ORDER BY id DESC LIMIT 200")}
    sk = post_care.skill("reply")
    out: list[tuple[str, str]] = []
    if llm.live and not sk["master"]:
        drafts = post_care.self_write(names, min(len(names), 5), avoid, "reply")
        try:
            got, scores = _claude(posts, names, drafts)
            good, gnames = [], []
            for i, x in enumerate(got[:len(posts)]):
                if x and post_care._ok(x):
                    good.append(x)
                    gnames.append(names[i])
                    out.append((x, "claude"))
                else:
                    out.append(("", ""))
            post_care.learn(good, gnames, "claude_reply")
            if scores:
                post_care.learn(drafts, names, "bao_reply", scores)
            after = post_care.skill("reply")
            if after["name"] != sk["name"]:
                db.log("bao", "Lên tay nghề", f"Trả lời khách: {sk['name']} → {after['name']}"
                       + (". Từ nay Bảo tự viết câu trả lời, không gọi Claude nữa" if after["master"] else ""))
        except Exception as e:
            print("[replies claude]", e)
    elif sk["master"] and llm.live:
        db.set_setting("bao_calls_saved_reply", str(sk["saved"] + 1))
    out += [("", "")] * (len(posts) - len(out))
    miss = [i for i, (x, _) in enumerate(out) if not x]
    if miss:
        mine = post_care.self_write([names[i] for i in miss], len(miss), avoid, "reply")
        for i, x in zip(miss, mine):
            out[i] = (x, "bao")
    c = contact()
    return [((x.rstrip(" .") + (". 👉 " + c if c else "")) if x else c, src) for x, src in out]


# ---------------------------------------------------------------- tìm bài đang hỏi mua trong nhóm sôi nổi
def pick(rows: list[dict], group: dict, aid: int) -> list[dict]:
    import prospect
    me = prospect.our_names()
    ours = {(r["posted_url"] or "").split("?")[0].rstrip("/") for r in db.q("SELECT posted_url FROM posts WHERE posted_url IS NOT NULL")}
    have = {r["post_url"] for r in db.q("SELECT post_url FROM reply_tasks")}
    out, seen = [], set()
    for r in rows:
        link = (r.get("link") or "").split("?")[0].rstrip("/")
        if r.get("comment") or not link or link in have or link in seen or link in ours:
            continue
        name = (r.get("author") or "").strip()
        if not name or plain(name) in me:
            continue
        text = (r.get("text") or "").replace(name, "", 1).strip()
        p = plain(text)
        if prospect.SUPPLY_RX.search(p) or not prospect.DEMAND_RX.search(p) or not prospect.fit_text(text):
            continue  # chỉ bài đang hỏi mua / hỏi nguồn hàng hợp ngành; bỏ bài người bán khác
        url = prospect.canon(r.get("href") or "") or ""
        if url and junk.blocked(url, name=name):
            continue
        seen.add(link)
        out.append({"account_id": aid, "group_id": group["id"], "post_url": link, "author": name[:80], "author_url": url,
                    "post_text": re.sub(r"\s+", " ", text)[:900]})
    return out[:int(s().get("replies_per_group") or 4)]


def save(items: list[dict]) -> int:
    if not items:
        return 0
    words = write(items)
    n = 0
    for it, (reply, src) in zip(items, words):
        try:
            db.run("""INSERT INTO reply_tasks(account_id, group_id, post_url, author, author_url, post_text, reply, source, status, created_at)
                      VALUES (?,?,?,?,?,?,?,?,'draft',?)""",
                   (it["account_id"], it["group_id"], it["post_url"], it["author"], it["author_url"], it["post_text"], reply, src, db.now()))
            n += 1
        except Exception:
            pass
    return n


def job(pw, aid: int, group_ids: list[int] | None = None, notify: str | None = None) -> dict:
    """Nick mở bảng tin các nhóm sôi nổi nhất (chỉ đọc), Bảo chọn bài đang hỏi mua và viết sẵn câu trả lời chờ sếp duyệt."""
    import browser_poster as B
    import friends
    import workflows
    acc, sale, agent = B._ctx_names(aid)
    if group_ids:
        groups = [g for g in (db.one("SELECT * FROM groups WHERE id=?", (i,)) for i in group_ids) if g and g.get("url")]
    else:
        n = int(s().get("replies_groups_per_run") or 3)
        groups = [db.one("SELECT * FROM groups WHERE id=?", (g["id"],)) for g in friends.active_groups(aid, 30) if g["target"] != "exclude"][:n]
    res = {"groups": [], "found": 0}
    ctx, page = B._open(pw, aid)
    try:
        if not B._logged_in(ctx):
            raise RuntimeError("Nick chưa đăng nhập. Vào Nhân viên sale → Mở Chrome để đăng nhập lại")
        for g in groups:
            workflows.set_status("bao", "working", f"Tìm người đang hỏi mua trong nhóm {g['name'][:40]}")
            workflows.set_status(agent, "working", f"Mở bảng tin nhóm {g['name'][:40]} cho Bảo đọc")
            try:
                rows, _ = friends.scan_group(page, g)
            except B.Blocked:
                raise
            except Exception as e:
                print("[replies group]", g["name"], e)
                rows = []
            n = save(pick(rows, g, aid))
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
        workflows.set_status("bao", "idle", "Chờ sếp duyệt câu trả lời khách")
        workflows.set_status(agent, "idle", "Chờ việc tiếp theo")
    msg = (f"Bảo đọc {len(res['groups'])} nhóm sôi nổi trên nick {acc.get('name')}: {res['found']} bài đang hỏi mua hợp ngành, "
           "đã viết sẵn câu trả lời. Sếp duyệt ở trang Trả lời khách, duyệt xong nick gửi trong giờ làm.")
    if res.get("blocked"):
        msg += " Nick bị Facebook kiểm tra nên dừng."
    db.log("bao", "Tìm bài hỏi mua", msg)
    if notify:
        import ceo_orders
        ceo_orders.followup(msg, notify)
    return res


def start(aid: int | None = None, group_ids: list[int] | None = None, notify: str | None = None) -> dict:
    import accounts
    import browser_poster as B
    import friends
    accs = [a for a in accounts.working() if not aid or a["id"] == aid]
    if not accs:
        raise ValueError("Chưa có nick nào đăng nhập và đang làm việc để mở nhóm")
    if not aid:  # nick ở nhóm sôi nổi nhất, ít bài chờ duyệt nhất
        accs.sort(key=lambda a: (db.one("SELECT COUNT(*) n FROM reply_tasks WHERE account_id=? AND status IN ('draft','approved')",
                                        (a["id"],))["n"], -max([g["score"] for g in friends.active_groups(a["id"], 3)] or [0])))
    a = accs[0]
    if not group_ids and not friends.active_groups(a["id"], 1):
        raise ValueError(f"Nick {accounts.label(a)} chưa ở nhóm nào có link. Vào Hội nhóm → Rà soát nhóm của nick trước")
    B.submit(a["sale_id"], {"kind": "replyscan", "account": a["id"], "group_ids": group_ids, "notify": notify})
    return {"account": accounts.label(a), "account_id": a["id"]}


# ---------------------------------------------------------------- duyệt, xếp lịch gửi (trong giờ làm, giãn cách, có trần)
def quota(aid: int) -> dict:
    import fb_policy
    acc = db.one("SELECT * FROM fb_accounts WHERE id=?", (aid,)) or {}
    f = fb_policy.factor(acc) if acc else 1.0
    lim = max(0, int(int(s().get("replies_per_nick_day") or 5) * f))
    d = db.today()
    used = db.one("""SELECT COUNT(*) n FROM reply_tasks WHERE account_id=? AND (substr(COALESCE(sent_at,''),1,10)=?
                     OR (status='approved' AND substr(COALESCE(scheduled_for,''),1,10)=?))""", (aid, d, d))["n"]
    return {"limit": lim, "used": used, "left": max(0, lim - used)}


def _slot(aid: int) -> str | None:
    """Giờ gửi kế tiếp của nick: trong giờ làm của nick, cách lượt trước 45–90 phút, không ban đêm."""
    a = db.one("SELECT * FROM fb_accounts WHERE id=?", (aid,))
    if not a or quota(aid)["left"] <= 0:
        return None
    now = db.clock()
    day = now.strftime("%Y-%m-%d")
    af = datetime.strptime(f"{day} {a.get('active_from') or '08:00'}", "%Y-%m-%d %H:%M")
    at = datetime.strptime(f"{day} {a.get('active_to') or '22:00'}", "%Y-%m-%d %H:%M")
    last = db.one("""SELECT MAX(COALESCE(sent_at, scheduled_for)) t FROM reply_tasks WHERE account_id=? AND status IN ('approved','sent')
                     AND COALESCE(sent_at, scheduled_for) >= ?""", (aid, day))["t"]
    t = max(now + timedelta(minutes=2), af)
    if last:
        t = max(t, datetime.strptime(last[:16], "%Y-%m-%d %H:%M") + timedelta(minutes=random.randint(45, 90)))
    return t.strftime("%Y-%m-%d %H:%M") if t <= at else None


def _next_day(aid: int) -> str:
    """Hết lượt hôm nay / ngoài giờ: sáng mai trong giờ làm của nick, lệch ngẫu nhiên để các câu không dồn một lúc."""
    a = db.one("SELECT active_from FROM fb_accounts WHERE id=?", (aid,)) or {}
    day = (db.clock() + timedelta(days=1)).strftime("%Y-%m-%d")
    t = datetime.strptime(f"{day} {a.get('active_from') or '08:00'}", "%Y-%m-%d %H:%M") + timedelta(minutes=random.randint(10, 120))
    return t.strftime("%Y-%m-%d %H:%M")


def approve(rid: int, reply: str | None = None) -> dict:
    r = db.one("SELECT * FROM reply_tasks WHERE id=?", (rid,))
    if not r:
        raise KeyError(rid)
    text = (reply if reply is not None else r["reply"] or "").strip()
    if not text:
        raise ValueError("Câu trả lời đang trống")
    import fb_policy
    bad = [i for i in fb_policy.check_text(text) if i["level"] == "high"]
    if bad:
        raise ValueError("Câu trả lời phạm luật Facebook: " + bad[0]["msg"])
    if reply is not None and plain(reply) != plain(r["reply"] or ""):  # sếp sửa câu: lưu làm mẫu cho Bảo học
        post_care.learn([re.sub(r"\s*👉.*$", "", text)], [product_guess(r["post_text"])], "claude_reply")
    t = _slot(r["account_id"])
    db.run("UPDATE reply_tasks SET reply=?, status='approved', decided_at=?, scheduled_for=? WHERE id=?",
           (text, db.now(), t or _next_day(r["account_id"]), rid))
    return {"id": rid, "status": "approved", "scheduled_for": t, "later": not t}


def skip(rid: int, as_junk: bool = False) -> dict:
    r = db.one("SELECT * FROM reply_tasks WHERE id=?", (rid,))
    if not r:
        raise KeyError(rid)
    db.run("UPDATE reply_tasks SET status='skipped', decided_at=? WHERE id=?", (db.now(), rid))
    if as_junk and r.get("author_url"):
        junk.mark_url(r["author"], r["author_url"], "other", "Sếp bỏ khi duyệt trả lời khách", r.get("post_text") or "")
    return {"id": rid, "status": "skipped"}


def due(aid: int) -> list[int]:
    """Lượt trả lời đã duyệt tới giờ gửi của nick (để ca làm việc của sale gửi)."""
    return [r["id"] for r in db.q("""SELECT id FROM reply_tasks WHERE account_id=? AND status='approved' AND scheduled_for <= ?
                                     ORDER BY scheduled_for LIMIT 2""", (aid, db.clock().strftime("%Y-%m-%d %H:%M")))]


def send(page, aid: int, rid: int):
    """Sale mở bài, gửi câu trả lời đã duyệt (chỉ chữ), kiểm tra đã gửi."""
    import browser_poster as B
    import workflows
    r = db.one("SELECT * FROM reply_tasks WHERE id=?", (rid,))
    if not r or r["status"] != "approved":
        return
    acc, sale, agent = B._ctx_names(aid)
    a = db.one("SELECT active_from, active_to FROM fb_accounts WHERE id=?", (aid,)) or {}
    hm = db.clock().strftime("%H:%M")
    if not ((a.get("active_from") or "08:00") <= hm <= (a.get("active_to") or "22:00")):  # ngoài giờ làm: dời sang sáng mai
        db.run("UPDATE reply_tasks SET scheduled_for=? WHERE id=?", (_next_day(aid), rid))
        return
    # kiểm lại lúc gửi: đủ trần hôm nay thì dời sang mai; câu trước của nick chưa đủ 45 phút thì lùi lại
    sent = db.one("SELECT COUNT(*) n, MAX(sent_at) last FROM reply_tasks WHERE account_id=? AND status='sent' AND substr(sent_at,1,10)=?",
                  (aid, db.today()))
    if sent["n"] >= quota(aid)["limit"]:
        db.run("UPDATE reply_tasks SET scheduled_for=? WHERE id=?", (_next_day(aid), rid))
        return
    if sent["last"]:
        nxt = datetime.strptime(sent["last"][:16], "%Y-%m-%d %H:%M") + timedelta(minutes=45)
        if nxt > db.clock():
            db.run("UPDATE reply_tasks SET scheduled_for=? WHERE id=?",
                   ((nxt + timedelta(minutes=random.randint(0, 45))).strftime("%Y-%m-%d %H:%M"), rid))
            return
    import fb_policy
    ok, why, _ = fb_policy.allow(aid, "reply")
    if not ok:  # nick đang nghỉ sau sự cố: dời, không gửi
        db.run("UPDATE reply_tasks SET status='failed', error=? WHERE id=?", (f"Chưa gửi theo luật Facebook: {why}", rid))
        return
    shot = db.SHOTS_DIR / f"reply-{rid}.png"
    workflows.set_status(agent, "working", f"Trả lời {r['author']} trong nhóm (nick {acc.get('name')})")
    try:
        page.goto(B.fb_url(r["post_url"]), wait_until="domcontentloaded", timeout=60000)
        page.wait_for_timeout(3500)
        B._check_blocked(page)
        body = page.inner_text("body").lower()
        if any(t.lower() in body for t in B.selectors()["removed_texts"]):
            db.run("UPDATE reply_tasks SET status='skipped', error=? WHERE id=?", ("Bài đã bị xóa hoặc ẩn", rid))
            return
        B._send_comment(page, r["reply"], None)
        page.wait_for_timeout(3000)
        page.screenshot(path=str(shot))
        db.run("UPDATE reply_tasks SET status='sent', sent_at=?, error=NULL, shot=? WHERE id=?", (db.now(), f"/shots/{shot.name}", rid))
        db.log(agent, "Trả lời khách", f"Trả lời {r['author']} (nick {acc.get('name')}): {r['reply'][:120]}")
        import learning
        learning.award("bao", 2, "Trả lời khách")
    except B.Blocked:
        db.run("UPDATE reply_tasks SET status='failed', error=? WHERE id=?", ("Facebook kiểm tra nick, đã dừng", rid))
        raise
    except Exception as e:
        try:
            page.screenshot(path=str(shot))
        except Exception:
            pass
        db.run("UPDATE reply_tasks SET status='failed', error=?, shot=? WHERE id=?", (str(e).splitlines()[0][:300], f"/shots/{shot.name}", rid))
    finally:
        workflows.set_status(agent, "idle", "Chờ việc tiếp theo")


def retry(rid: int) -> dict:
    r = db.one("SELECT * FROM reply_tasks WHERE id=?", (rid,))
    if not r:
        raise KeyError(rid)
    db.run("UPDATE reply_tasks SET status='draft', error=NULL WHERE id=?", (rid,))
    return approve(rid)


def tick(now):
    """Mỗi ngày một lượt tìm bài hỏi mua (giờ trong cài đặt). Không chạy ban đêm."""
    st = s()
    if st.get("replies_enabled", "1") != "1" or st.get("replies_last") == db.today():
        return
    if now.strftime("%H:%M") < (st.get("replies_time") or "09:20"):
        return
    db.set_setting("replies_last", db.today())
    try:
        start()
    except ValueError:
        pass


def overview(status: str = "") -> dict:
    import accounts
    where = "r.status IN ('draft','approved','failed')" if not status else "r.status=?"
    rows = db.q(f"""SELECT r.*, g.name group_name, a.name nick FROM reply_tasks r LEFT JOIN groups g ON g.id=r.group_id
                    LEFT JOIN fb_accounts a ON a.id=r.account_id WHERE {where}
                    ORDER BY CASE r.status WHEN 'draft' THEN 0 WHEN 'failed' THEN 1 ELSE 2 END, r.id DESC LIMIT 200""",
                (status,) if status else ())
    tot = db.one("""SELECT SUM(status='draft') draft, SUM(status='approved') approved, SUM(status='sent') sent,
                    SUM(status='sent' AND sent_at >= ?) today FROM reply_tasks""", (db.today(),))
    nicks = [{"id": a["id"], "name": accounts.label(a), **quota(a["id"])} for a in accounts.working()]
    return {"items": rows, "status_txt": STATUS, "nicks": nicks, "stats": {k: tot[k] or 0 for k in ("draft", "approved", "sent", "today")},
            "skill": post_care.skill("reply"), "samples": post_care.samples(8, "reply"), "contact": contact(),
            "settings": {k: s().get(k) for k in ("replies_enabled", "replies_time", "replies_per_nick_day", "replies_groups_per_run",
                                                 "replies_per_group", "reply_contact")}}

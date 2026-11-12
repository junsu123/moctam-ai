"""Công việc của từng Agent: viết bài, phân phối nhóm, chăm khách, phân tích."""
import json
import random
from datetime import datetime, timedelta

import threading

import db
import mock_brain
from agents import system_prompt
from llm import llm, month_spent, parse_json

# Trạng thái hiện tại của từng agent (hiển thị trên văn phòng 3D)
STATUS = {a: {"state": "idle", "text": "Đang sẵn sàng"} for a in ["ceo", "minh", "lan", "tuan", "ha", "khoa", "mai", "vy", "bao"]}


TARGET_NAME = {"group": "Hội nhóm", "profile": "Trang cá nhân", "page": "Fanpage"}


def set_status(agent_id: str, state: str, text: str):
    STATUS[agent_id] = {"state": state, "text": text, "at": db.now()}


# ---------------------------------------------------------------- Khoa: số liệu
def stats() -> dict:
    import errors
    _err_new = errors.count_new()
    yesterday = (db.clock() - timedelta(days=1)).strftime("%Y-%m-%d")
    c = lambda sql, p=(): db.one(sql, p)["n"]
    posted = c("SELECT COUNT(*) n FROM posts WHERE status='posted'")
    leads = c("SELECT COUNT(*) n FROM leads WHERE COALESCE(status,'')!='junk'")
    best = db.one("""SELECT g.name, SUM(p.leads) l FROM posts p JOIN groups g ON g.id=p.group_id
                     WHERE p.status='posted' GROUP BY g.id ORDER BY l DESC LIMIT 1""")
    groups = db.q("SELECT * FROM groups")
    return {"errors_new": _err_new, "autopilot": db.get_settings().get("ceo_autopilot", "1") == "1",
        "drafts": c("SELECT COUNT(*) n FROM posts WHERE status='draft'"),
        "approved": c("SELECT COUNT(*) n FROM posts WHERE status IN ('approved','scheduled')"),
        "posted_total": posted,
        "posted_today": c("SELECT COUNT(*) n FROM posts WHERE status='posted' AND posted_at LIKE ?", (db.today() + "%",)),
        "posts_yesterday": c("SELECT COUNT(*) n FROM posts WHERE created_at LIKE ?", (yesterday + "%",)),
        "groups": len(groups),
        "groups_ready": sum(1 for g in groups if group_ready(g)),
        "leads": leads,
        "leads_new": c("SELECT COUNT(*) n FROM leads WHERE status='new'"),
        "prospects_a": c("SELECT COUNT(*) n FROM prospects WHERE grade='A' AND status='verified'"),
        "prospects_manual": c("SELECT COUNT(*) n FROM prospects WHERE status='needs_manual'"),
        "leads_hot": c("SELECT COUNT(*) n FROM leads WHERE score>=75 AND status NOT IN ('ordered','lost','junk')"),
        "leads_ordered": c("SELECT COUNT(*) n FROM leads WHERE status='ordered'"),
        "best_group": best["name"] if best and best["l"] else None,
        "lead_per_post": round(leads / posted, 2) if posted else 0,
        "tasks_open": c("SELECT COUNT(*) n FROM tasks WHERE status!='done'"),
        "failed": c("SELECT COUNT(*) n FROM posts WHERE status='failed'"),
        "bumps_today": c("SELECT COUNT(*) n FROM bumps WHERE status='done' AND done_at LIKE ?", (db.today() + "%",)),
        "kpi": __import__("kpi").day_stats(),
        "company": __import__("company").brief(),
        "sales_total": c("SELECT COUNT(*) n FROM sales"),
        "sales_ok": c("SELECT COUNT(*) n FROM sales WHERE login_status='ok' AND auto_post=1"),
        "sales_problem": c("SELECT COUNT(*) n FROM sales WHERE login_status IN ('checkpoint','not_logged_in')"),
        "nicks_total": c("SELECT COUNT(*) n FROM fb_accounts a JOIN sales s ON s.id=a.sale_id WHERE COALESCE(s.status,'active')!='fired'"),
        "nicks_ok": c("""SELECT COUNT(*) n FROM fb_accounts a JOIN sales s ON s.id=a.sale_id WHERE a.enabled=1 AND a.login_status='ok'
                         AND s.auto_post=1 AND COALESCE(s.status,'active')='active'"""),
        "nicks_problem": c("""SELECT COUNT(*) n FROM fb_accounts a JOIN sales s ON s.id=a.sale_id WHERE a.enabled=1
                              AND a.login_status!='ok' AND COALESCE(s.status,'active')!='fired'"""),
        "ai_live": llm.live,
        "ai_cost_month": round(month_spent(), 3),
    }


def group_ready(g: dict) -> bool:
    if not g.get("last_posted_at"):
        return True
    last = datetime.strptime(g["last_posted_at"][:10], "%Y-%m-%d")
    days = int(g.get("min_days_between_posts") or 3)
    if g.get("focus"):  # sếp chọn tập trung đăng: mỗi ngày một bài (luật Facebook vẫn giữ tối thiểu 24 giờ/nhóm)
        days = min(days, 1)
    return (db.clock() - last).days >= days


# ---------------------------------------------------------------- Lan: viết bài
WHERE = {"group": "một hội nhóm Facebook về bán hàng online/nguồn hàng",
         "profile": "trang cá nhân Facebook của nhân viên kinh doanh",
         "page": "Fanpage của xưởng"}


def _post_prompt(p: dict, ang: str, target_type: str, settings: dict, note: str, i: int) -> str:
    return f"""Viết 1 bài đăng Facebook để đăng lên {WHERE[target_type]}, nhằm tìm khách SỈ (người bán online) nhập sản phẩm sau:
Tên: {p['name']} | Loại: {p['category']} | Mô tả: {p['description']}
Nhập tối thiểu: {p['moq']}
Điểm bán: {p['selling_points']}
Góc tiếp cận: {mock_brain.ANGLES.get(ang, ang)}
Liên hệ: {settings.get('contact_info')}
Yêu cầu thêm của sếp: {note or 'không'}
Bài dài 110-180 chữ, emoji vừa phải, mở đầu gây chú ý, kết bằng lời kêu gọi bình luận/inbox.
Câu chữ phải khác các bài khác (bài số {i + 1}, mã {random.randint(100, 999)}). Không hứa công dụng chữa bệnh.
Không ghi giá hay mức lãi; dòng cuối ghi đúng: "{__import__('pricing').contact_line()}".
Trả về JSON: {{"title": "...", "content": "...", "hashtags": "#... #... (không dấu)", "image_idea": "1 câu mô tả ảnh nên chụp"}}""" + \
        _kb("lan", f"viết bài {p['name']} {p['category']} {mock_brain.ANGLES.get(ang, ang)} {WHERE[target_type]} {note or ''}") + \
        _style_hint()


def _style_hint() -> str:
    try:
        import content_style
        return content_style.style_hint()
    except Exception:
        return ""


def _kb(agent_id: str, query: str) -> str:
    try:
        import knowledge
        return knowledge.block(agent_id, query)
    except Exception:
        return ""


def _save_post(p: dict, ang: str, target_type: str, data) -> dict:
    import content_style
    if not isinstance(data, dict) or not data.get("content"):
        data = mock_brain.post(p, ang, target_type, db.get_settings())
    src = "self" if data.get("_self") else "mock" if content_style.is_mock(data) else "claude"
    import pricing  # sếp chốt: không ghi giá, mời liên hệ Zalo
    data = {**data, "content": pricing.sanitize(data["content"]), "title": pricing.sanitize(data.get("title") or "", False)}
    pid = db.run("""INSERT INTO posts(agent_id, product_id, target_type, angle, title, content, hashtags,
                    image_idea, status, created_at, source) VALUES ('lan',?,?,?,?,?,?,?,'draft',?,?)""",
                 (p["id"], target_type, ang, data.get("title", ""), data["content"],
                  data.get("hashtags", ""), data.get("image_idea", ""), db.now(), src))
    content_style.record_post(pid, p, ang, target_type, data, src)  # bài Claude viết: lưu kho, Lan học phong cách
    return db.one("SELECT * FROM posts WHERE id=?", (pid,))


def _self_write(p: dict, ang: str, tt: str, note: str = "") -> dict | None:
    """Lan tự viết theo phong cách đã học nếu đủ vốn (không gọi Claude)."""
    try:
        import content_style
        if content_style.should_self_write(note):
            return content_style.compose(p, ang, tt)
    except Exception as e:
        print("[self write]", e)
    return None


def _write_one(p: dict, ang: str, tt: str, settings: dict, note: str, i: int) -> dict:
    data = _self_write(p, ang, tt, note)
    if data:
        return data
    return llm.json(system_prompt("lan", settings), _post_prompt(p, ang, tt, settings, note, i),
                    mock=lambda: mock_brain.post(p, ang, tt, settings), max_tokens=900, task="posts")


def _write_note(made: list) -> str:
    n_self = sum(1 for x in made if x and x.get("source") == "self")
    n_ai = sum(1 for x in made if x and x.get("source") == "claude")
    return f" (Lan tự viết {n_self}, nhờ Claude {n_ai})" if n_self else ""


def _plan_items(count: int, product_id: int | None, target_type: str, angle: str | None):
    products = db.q("SELECT * FROM products" + (" WHERE id=?" if product_id else ""),
                    (product_id,) if product_id else ())
    if not products:
        return []
    import learning
    items = []
    for i in range(count):
        p = products[i % len(products)] if product_id else learning.choose_product(products)
        items.append((i, p, angle or learning.choose_angle(), target_type))
    return items


def generate_posts(count: int = 3, product_id: int | None = None, target_type: str = "group",
                   angle: str | None = None, note: str = "") -> list[dict]:
    """Viết ngay (sếp đang chờ trên giao diện)."""
    import post_template
    if target_type == "group" and post_template.enabled():  # sếp chốt: bài nhóm chỉ đăng theo mẫu tìm khách sỉ
        set_status("lan", "working", f"Đang làm {count} bài theo mẫu của sếp")
        return post_template.make_posts(count)
    settings = db.get_settings()
    items = _plan_items(count, product_id, target_type, angle)
    if not items:
        return []
    set_status("lan", "working", f"Đang viết {count} bài đăng")
    created = []
    for i, p, ang, tt in items:
        created.append(_save_post(p, ang, tt, _write_one(p, ang, tt, settings, note, i)))
    db.log("lan", "Viết bài", f"Đã viết {len(created)} bài nháp chờ sếp duyệt" + _write_note(created))
    set_status("lan", "idle", f"Vừa viết xong {len(created)} bài")
    return created


def generate_posts_batch(plan: list[tuple[str, int]]) -> dict:
    """Viết theo lô qua Batch API (rẻ hơn 50%). plan: [(target_type, số bài)].
    Không có API key / tắt chế độ lô / gửi lỗi -> viết ngay như bình thường."""
    settings = db.get_settings()
    import post_template
    tpl_made = []
    if post_template.enabled():  # bài nhóm: theo mẫu của sếp (không cần Claude viết)
        tpl_made = post_template.make_posts(sum(n for tt, n in plan if tt == "group"))
        plan = [(tt, n) for tt, n in plan if tt != "group"]
    items = [it for tt, n in plan if n > 0 for it in _plan_items(n, None, tt, None)]
    if not items and tpl_made:
        return {"mode": "template", "count": len(tpl_made)}
    if not items:
        return {"mode": "none", "count": 0}
    if settings.get("use_batch") != "1" or not llm.live:
        made = [_save_post(p, ang, tt, _write_one(p, ang, tt, settings, "", i)) for i, p, ang, tt in items]
        db.log("lan", "Viết bài", f"Đã viết {len(made)} bài nháp chờ sếp duyệt" + _write_note(made))
        return {"mode": "now", "count": len(made)}
    # Lan tự viết phần bài đủ sức tự viết, phần còn lại gửi lô cho Claude
    own, rest = [], []
    for it in items:
        d = _self_write(it[1], it[2], it[3])
        (own.append((it, d)) if d else rest.append(it))
    for (i, p, ang, tt), d in own:
        _save_post(p, ang, tt, d)
    if own:
        db.log("lan", "Viết bài", f"Lan tự viết {len(own)} bài theo phong cách đã học (không gọi Claude)")
    items = rest
    if not items:
        return {"mode": "self", "count": len(own)}
    sysmsg = system_prompt("lan", settings)
    reqs, meta = [], {}
    for k, (i, p, ang, tt) in enumerate(items):
        cid = f"post-{k}"
        reqs.append({"custom_id": cid, "system": sysmsg, "prompt": _post_prompt(p, ang, tt, settings, "", k)})
        meta[cid] = {"product_id": p["id"], "angle": ang, "target_type": tt}
    bid = llm.batch_create("posts", reqs, max_tokens=900)
    if not bid:
        return generate_posts_batch_fallback(items, settings)
    db.run("INSERT INTO ai_batches(id, task, meta, status, created_at) VALUES (?,?,?,?,?)",
           (bid, "posts", db.dumps(meta), "in_progress", db.now()))
    set_status("lan", "working", f"Đang viết lô {len(items)} bài (giảm 50% chi phí)")
    db.log("lan", "Gửi lô viết bài", f"{len(items)} bài, giảm 50% chi phí, thường xong sau vài phút")
    return {"mode": "batch", "count": len(items), "batch_id": bid}


def generate_posts_batch_fallback(items, settings):
    made = [_save_post(p, ang, tt, llm.json(system_prompt("lan", settings), _post_prompt(p, ang, tt, settings, "", i),
            mock=lambda p=p, ang=ang, tt=tt: mock_brain.post(p, ang, tt, settings), max_tokens=900, task="posts"))
            for i, p, ang, tt in items]
    db.log("lan", "Viết bài", f"Đã viết {len(made)} bài nháp chờ sếp duyệt")
    return {"mode": "now", "count": len(made)}


def poll_batches():
    """Gọi định kỳ: lô nào xong thì nhập bài nháp."""
    if not llm.live:
        return
    for b in db.q("SELECT * FROM ai_batches WHERE status='in_progress' AND task!='coach'"):  # lô kèm cặp: coach.poll
        try:
            if llm.batch_status(b["id"]) != "ended":
                continue
            meta = json.loads(b["meta"])
            res = llm.batch_results(b["id"], b["task"])
            n = 0
            for cid, m in meta.items():
                p = db.one("SELECT * FROM products WHERE id=?", (m["product_id"],))
                if p:
                    _save_post(p, m["angle"], m["target_type"], parse_json(res.get(cid) or ""))
                    n += 1
            db.run("UPDATE ai_batches SET status='ended', ended_at=? WHERE id=?", (db.now(), b["id"]))
            db.log("lan", "Viết bài (lô)", f"Lô xong: {n} bài nháp chờ sếp duyệt")
            set_status("lan", "idle", f"Lô {n} bài đã xong")
        except Exception as e:
            print("[batch]", e)


def post_demand() -> list[tuple[str, int]]:
    """Chỉ viết đủ số bài thực sự đăng được hôm nay -> không tốn tiền cho bài thừa."""
    today = db.today() + "%"
    sales = db.q("SELECT * FROM sales WHERE login_status='ok' AND auto_post=1")
    groups_ready = sum(1 for g in db.q("SELECT * FROM groups") if group_ready(g))
    if sales:
        cap_group = min(sum(int(s["max_posts_per_day"] or 5) for s in sales) - len(sales), groups_ready)
        cap_profile = len(sales)
    else:
        cap_group = min(int(db.get_settings().get("posts_per_day", 4)), groups_ready)
        cap_profile = 0
    def have(tt):  # bài còn trong kho chưa dùng + bài đã lên lịch/đăng hôm nay
        return db.one(f"""SELECT COUNT(*) n FROM posts WHERE target_type=? AND (status IN ('draft','approved')
                          OR (status IN ('scheduled','posting','posted') AND COALESCE(posted_at, scheduled_for) LIKE ?))""",
                      (tt, today))["n"]
    pending = db.one("SELECT COUNT(*) n FROM ai_batches WHERE status='in_progress'")["n"]
    if pending:
        return []  # đang có lô chưa xong, không gửi thêm
    try:
        import my_groups
        extra = my_groups.admin_sell_need()  # bài bán hàng cho nhóm mình quản lý (5–10 bài/ngày/nhóm)
    except Exception:
        extra = 0
    return [("group", max(0, cap_group + extra - have("group"))), ("profile", max(0, cap_profile - have("profile")))]


# ---------------------------------------------------------------- Tuấn: phân phối nhóm
def _dt(s: str) -> datetime:
    return datetime.strptime(s[:16], "%Y-%m-%d %H:%M")


RESET_KINDS = {"approved": "đã duyệt", "scheduled": "lịch đăng", "failed": "đăng lỗi", "draft": "chờ duyệt"}


def reset_preview() -> dict:
    """Số bài sẽ bị xóa khi sếp bấm Làm lại bài đăng (bài đã đăng và bài đang đăng dở giữ nguyên)."""
    rows = db.q("SELECT status, target_type, COUNT(*) n FROM posts WHERE status IN ('approved','scheduled','failed','draft') "
                "GROUP BY status, target_type")
    out = {k: 0 for k in RESET_KINDS}
    groups = {k: 0 for k in RESET_KINDS}
    for r in rows:
        out[r["status"]] += r["n"]
        if r["target_type"] == "group":
            groups[r["status"]] += r["n"]
    today = db.one("SELECT COUNT(*) n FROM posts WHERE status='scheduled' AND scheduled_for LIKE ?", (db.today() + "%",))["n"]
    posting = db.one("SELECT COUNT(*) n FROM posts WHERE status='posting'")["n"]
    return {"counts": out, "group_counts": groups, "scheduled_today": today, "posting": posting, "labels": RESET_KINDS}


def reset_posts(kinds: list[str], rewrite: int = 0, plan: bool = True) -> dict:
    """Sếp làm lại bài đăng: xóa các bài chưa đăng (đã duyệt, lịch đăng, lỗi, tùy chọn chờ duyệt) rồi cho Lan viết bài mới."""
    kinds = [k for k in kinds if k in RESET_KINDS] or ["approved", "scheduled", "failed"]
    rows = db.q(f"SELECT id, status FROM posts WHERE status IN ({','.join('?' * len(kinds))})", tuple(kinds))
    ids = [r["id"] for r in rows]
    by = {k: sum(r["status"] == k for r in rows) for k in kinds}
    if ids:
        qs = ",".join("?" * len(ids))
        db.run(f"DELETE FROM feedback WHERE post_id IN ({qs})", tuple(ids))
        db.run(f"DELETE FROM content_library WHERE post_id IN ({qs})", tuple(ids))
        db.run(f"UPDATE errors SET status='resolved' WHERE ref_type='post' AND ref_id IN ({qs}) AND status!='resolved'",
               tuple(str(i) for i in ids))
        db.run(f"DELETE FROM posts WHERE id IN ({qs})", tuple(ids))
    detail = ", ".join(f"{n} bài {RESET_KINDS[k]}" for k, n in by.items() if n) or "không có bài nào"
    rewrite = max(0, min(20, int(rewrite or 0)))
    db.log("minh", "Làm lại bài đăng", f"Sếp xóa {len(ids)} bài chưa đăng ({detail})"
           + (f". Lan viết lại {rewrite} bài mới" if rewrite else ""))
    set_status("tuan", "idle", "Lịch đăng đã xóa, chờ bài mới")
    if rewrite:
        def work():
            try:
                made = generate_posts(rewrite, target_type="group")
                if plan and any(m.get("status") == "approved" for m in made):
                    plan_distribution()
            except Exception as e:
                import errors
                errors.report_exc("posts", "Viết lại bài sau khi làm lại bài đăng bị lỗi", e, screen="posts")
                set_status("lan", "idle", "Viết lại bài bị lỗi")
        threading.Thread(target=work, daemon=True).start()
    return {"deleted": len(ids), "by": by, "rewrite": rewrite}


def with_images(posts: list[dict]) -> list[dict]:
    """Chỉ giữ bài có ảnh để đăng (sếp quy định bài phải có ảnh). Bài thiếu ảnh ghi rõ lý do, ở lại hàng chờ."""
    import media_folder
    ok, miss = [], 0
    for p in posts:
        why = media_folder.missing(p)
        if why:
            miss += 1
            if p.get("error") != why:
                db.run("UPDATE posts SET error=? WHERE id=?", (why, p["id"]))
        else:
            if (p.get("error") or "").startswith("Bài chưa có ảnh"):
                db.run("UPDATE posts SET error=NULL WHERE id=?", (p["id"],))
            ok.append(p)
    if miss:
        today = db.today()
        s = db.get_settings()
        if s.get("noimg_log_date") != today:  # báo 1 lần mỗi ngày, không spam nhật ký
            db.set_setting("noimg_log_date", today)
            db.log("tuan", "Bài thiếu ảnh chưa xếp lịch", f"{miss} bài chưa có ảnh nên không xếp đăng. Sếp thêm thư mục ảnh ở trang Sản phẩm "
                   "hoặc Cài đặt → Up bài")
            import errors
            errors.report("image", "Có bài không có ảnh nên chưa đăng",
                          f"{miss} bài đã duyệt chưa có ảnh. Bài đăng lên Facebook bắt buộc kèm ảnh. Thêm thư mục ảnh cho sản phẩm "
                          "(trang Sản phẩm) hoặc thư mục ảnh chung (Cài đặt → Up bài).", screen="products")
    return ok


def plan_distribution(keywords: list[str] | None = None, limit: int | None = None) -> list[dict]:
    """Tuấn ghép bài đã duyệt với (nhóm, nick sale, giờ đăng).
    keywords: lệnh một lần của sếp "đăng bài lên các nhóm có từ khóa X": chỉ xếp vào nhóm khớp, không xếp trang cá nhân / Fanpage.

    Quy tắc: nick phải là thành viên nhóm; mỗi nhóm chỉ nhận 1 bài trong 1 lượt và phải hết giãn cách;
    mỗi nick không vượt số bài/ngày, cách nhau ít nhất N phút, chỉ đăng trong khung giờ của nick;
    mỗi nick tối đa 1 bài trang cá nhân/ngày. Mỗi bài là một nội dung khác nhau (Lan viết riêng).
    """
    set_status("tuan", "working", "Đang xếp lịch đăng nhóm")
    import accounts
    import my_groups
    try:
        admin_plan = [] if keywords else my_groups.plan_admin()  # nhóm mình quản lý: 5–10 bài/ngày, xếp trước
    except Exception as e:
        print("[plan_admin]", e)
        admin_plan = []
    today, now = db.today(), db.clock()
    # mỗi nick là một đơn vị đăng bài; một sale giữ nhiều nick và làm lần lượt từng nick
    sales = accounts.working()
    load, sale_last = {}, {}
    for s in sales:
        rows = db.q("""SELECT scheduled_for, posted_at, target_type, COALESCE(managed,0) managed FROM posts WHERE account_id=? AND
                       ((status IN ('scheduled','posting') AND scheduled_for LIKE ?) OR (status='posted' AND posted_at LIKE ?))""",
                    (s["id"], today + "%", today + "%"))
        times = [r["scheduled_for"] or r["posted_at"] for r in rows]
        load[s["id"]] = {"count": sum(1 for r in rows if not r["managed"]), "last": max(times) if times else None,  # bài nhóm mình quản lý không tính giới hạn
                         "profile": sum(r["target_type"] == "profile" for r in rows), "all": len(rows)}  # all: tính trần luật Facebook
        for t in times:
            sale_last[s["sale_id"]] = max(sale_last.get(s["sale_id"]) or "", t)
    taken = {r["group_id"] for r in db.q("SELECT group_id FROM posts WHERE status IN ('scheduled','posting') AND group_id IS NOT NULL")}
    groups = [g for g in db.q("""SELECT * FROM groups WHERE NOT (COALESCE(verdict,'')='skip' AND COALESCE(leads_count,0)=0
                                 AND COALESCE(pinned,0)=0) AND COALESCE(managed,0)=0
                                 ORDER BY leads_count DESC, COALESCE(eng_score, 0) DESC, members DESC""")
              if group_ready(g) and g["id"] not in taken and (g.get("url") or "").strip()]  # nhóm chưa có link: không xếp
    import group_finder
    groups.sort(key=lambda g: not group_finder.matches_today(g))  # ưu tiên nhóm hợp chủ đề CEO chọn hôm nay
    import group_target
    push = None if keywords else group_target.push_get()
    if keywords:  # lệnh một lần: chỉ nhóm khớp từ khóa (bỏ qua chế độ "chỉ nhóm chỉ định" vì sếp vừa nói rõ)
        groups = group_target.filter_push(groups, keywords)
    elif push:  # hôm nay sếp vừa giao đăng theo từ khóa: bài duyệt sau cũng vào nhóm khớp trước
        first = group_target.filter_push(groups, push["keywords"])
        ids = {g["id"] for g in first}
        groups = first + [g for g in group_target.apply(groups) if g["id"] not in ids]
    else:
        groups = group_target.apply(groups)  # sếp chỉ đạo: nhóm tập trung / có từ khóa trước, bỏ nhóm có từ khóa tránh
    plan = []

    import learning
    golden = learning.golden_hours()
    explore = float(db.get_settings().get("learn_explore") or 0.25)

    import fb_policy

    def next_slot(s):
        L = load[s["id"]]
        lim = fb_policy.limits(s) if fb_policy.enabled() else {"posts": 99, "gap": 0}
        if L["count"] >= int(s["max_posts_per_day"] or 5) or L["all"] >= lim["posts"]:
            return None
        if fb_policy.enabled() and (s.get("rest_until") or "") > db.now():  # nick đang nghỉ sau sự cố
            return None
        start = max(now + timedelta(minutes=3), _dt(f"{today} {s['active_from'] or '08:00'}"))
        if db.get_settings().get("spread_posts", "1") == "1":
            # rải bài đều cả ngày: nick đăng bài thứ k không sớm hơn mốc k của khung giờ, các nick cùng sale lệch nhau
            # (không dồn 25 bài của 5 nick vào buổi sáng, mỗi 10 phút một bài)
            af, at = _dt(f"{today} {s['active_from'] or '08:00'}"), _dt(f"{today} {s['active_to'] or '22:00'}")
            cap = max(1, min(int(s["max_posts_per_day"] or 5), int(lim["posts"])))
            peers = sorted(x["id"] for x in sales if x["sale_id"] == s["sale_id"])
            step = max(0.0, (at - af).total_seconds() / 60 / cap)
            even = af + timedelta(minutes=(L["count"] + peers.index(s["id"]) / len(peers)) * step)
            start = max(start, even)
        if L["last"]:
            gap = max(int(s["min_gap_minutes"] or 40), lim["gap"])
            start = max(start, _dt(L["last"]) + timedelta(minutes=gap + random.randint(0, 12)))
        if sale_last.get(s["sale_id"]):  # sale làm từng nick một: chừa thời gian xong ca nick trước
            start = max(start, _dt(sale_last[s["sale_id"]]) + timedelta(minutes=8 + random.randint(0, 6)))
        end = _dt(f"{today} {s['active_to'] or '22:00'}")
        if start > end:
            return None
        # Tuấn học được "giờ vàng": nếu giờ hiện tại không tốt mà trong ngày còn giờ vàng thì dời tới đó
        if golden and start.hour not in golden and random.random() > explore:
            later = [start.replace(hour=h, minute=random.randint(0, 25)) for h in golden if h > start.hour]
            later = [t for t in later if t <= end]
            if later:
                return min(later)
        return start

    def assign(post, acc, when, group=None):
        db.run("UPDATE posts SET sale_id=?, account_id=?, group_id=?, scheduled_for=?, status='scheduled', error=NULL WHERE id=?",
               (acc["sale_id"] if acc else None, acc["id"] if acc else None, group["id"] if group else None, when, post["id"]))
        if acc:
            L = load[acc["id"]]
            L["count"] += 1
            L["all"] += 1
            L["last"] = when
            L["profile"] += post["target_type"] == "profile"
            sale_last[acc["sale_id"]] = max(sale_last.get(acc["sale_id"]) or "", when)
        plan.append({"post_id": post["id"], "group": group["name"] if group else TARGET_NAME[post["target_type"]],
                     "time": when, "sale": f"{acc['sale_name']} · {acc['name']}" if acc else None})

    import post_template
    approved = with_images(db.q("SELECT * FROM posts WHERE status='approved' AND target_type='group'"
                                + (" AND source='template'" if post_template.enabled() else "") + " ORDER BY id"))
    if sales:
        for post in approved:
            if limit and len(plan) >= limit:
                break
            # chia đều cho mọi nick: nick ít bài nhất hôm nay được chọn trước, lấy nhóm tốt nhất mà nick đó đăng được
            # (trước đây chọn theo nhóm rồi mới tới nick sớm giờ nhất, nick ít nhóm chung hay bị bỏ quên cả ngày)
            # nhóm sale tự tìm được: chỉ nick đã vào nhóm mới đăng; nhóm sếp nhập chưa đánh dấu nick: coi như mọi nick đã vào
            opts = []
            for s in sales:
                t = next_slot(s)
                if not t:
                    continue
                g = next((g for g in groups if accounts.can_post_in(g, s["id"])), None)
                if g:
                    opts.append((load[s["id"]]["all"], t, s, g))
            if not opts:
                break
            _, t, s, g = min(opts, key=lambda o: (o[0], o[1]))
            assign(post, s, t.strftime("%Y-%m-%d %H:%M"), g)
            groups.remove(g)
        for post in ([] if keywords else with_images(db.q("SELECT * FROM posts WHERE status='approved' AND target_type='profile' ORDER BY id"))):
            cands = [(t, s) for s in sales if load[s["id"]]["profile"] == 0 and (t := next_slot(s))]
            if cands:
                t, s = min(cands, key=lambda c: c[0])
                assign(post, s, t.strftime("%Y-%m-%d %H:%M"))
    else:  # chưa có nick sale tự động -> xếp lịch để người đăng tay
        per_day = int(db.get_settings().get("posts_per_day", 4))
        slots = ["09:00", "11:30", "15:00", "20:00", "21:30"]
        for post, group in zip(approved[:min(per_day, limit or per_day)], groups):
            assign(post, None, f"{today} {slots[len(plan) % len(slots)]}", group)
    # Bài Fanpage đã duyệt: xếp giờ, đến giờ hệ thống tự đăng qua Graph API
    page_slots = ["10:00", "19:30"]
    for i, post in enumerate([] if keywords else with_images(db.q("SELECT * FROM posts WHERE status='approved' AND target_type='page' ORDER BY id"))[:2]):
        when = f"{db.today()} {page_slots[i]}"
        db.run("UPDATE posts SET scheduled_for=?, status='scheduled' WHERE id=?", (when, post["id"]))
        plan.append({"post_id": post["id"], "group": "Fanpage", "time": when})
    adm = sum(x["count"] for x in admin_plan)
    db.log("tuan", "Xếp lịch", (f"Đã xếp {len(plan)} bài cho hôm nay" + (f", cộng {adm} bài cho nhóm mình quản lý" if adm else "")) if plan or adm
           else "Chưa có bài đã duyệt hoặc nhóm đủ điều kiện để xếp lịch")
    set_status("tuan", "idle", f"Lịch hôm nay: {len(plan)} bài")
    return plan


def mark_posted(post_id: int, posted_url: str = "", poster: str = "", fb_post_id: str = ""):
    post = db.one("SELECT * FROM posts WHERE id=?", (post_id,))
    db.run("UPDATE posts SET status='posted', error=NULL, posted_at=?, posted_url=?, poster=?, fb_post_id=? WHERE id=?",
           (db.now(), posted_url, poster, fb_post_id, post_id))
    if post and post.get("group_id"):
        db.run("UPDATE groups SET last_posted_at=? WHERE id=?", (db.now(), post["group_id"]))
    db.log("tuan", "Đã đăng", f"Bài #{post_id} được đánh dấu đã đăng {('bởi ' + poster) if poster else ''}")
    import learning
    learning.award("tuan", 3, "Bài được đăng đúng lịch")
    if post and post.get("sale_id"):
        learning.award(f"sale-{post['sale_id']}", 5, "Đăng bài thành công")


# ---------------------------------------------------------------- Up bài hằng ngày
def plan_bumps(force: bool = False) -> int:
    """Lên lịch bình luận ảnh cho các bài đã đăng gần đây, mỗi bài tối đa 1 lần/ngày, đúng nick đã đăng."""
    import media_folder
    s = db.get_settings()
    today = db.today()
    if s.get("bump_enabled") != "1" and not force:
        return 0
    if s.get("bump_planned_date") == today and not force:
        return 0
    db.set_setting("bump_planned_date", today)
    if not media_folder.root():
        db.log("bao", "Up bài", "Chưa cài thư mục ảnh sản phẩm (Cài đặt → Up bài), hôm nay bỏ qua")
        return 0
    import post_care
    set_status("bao", "working", "Rà soát bài đã đăng, viết câu bình luận kèm ảnh")
    now = db.clock()
    cutoff = (now - timedelta(days=int(s.get("bump_max_age_days") or 7))).strftime("%Y-%m-%d %H:%M:%S")
    fresh = (now - timedelta(hours=10)).strftime("%Y-%m-%d %H:%M:%S")  # bài vừa đăng hôm nay chưa cần up
    per_nick = int(s.get("bump_max_per_nick") or 8)
    gap = int(s.get("bump_gap_minutes") or 6)
    total = 0
    import accounts
    for sale in accounts.working():  # mỗi nick up bài của chính nick đó
        posts = db.q("""SELECT p.id, p.product_id FROM posts p LEFT JOIN products pr ON pr.id=p.product_id
                        WHERE p.status='posted' AND p.account_id=? AND COALESCE(p.bump_enabled,1)=1
                        AND COALESCE(p.permalink_status,'') != 'removed' AND p.posted_at >= ? AND p.posted_at <= ?
                        AND p.id NOT IN (SELECT post_id FROM bumps WHERE created_at LIKE ? AND status NOT IN ('skipped', 'failed'))  -- lượt lỗi được thử lại khi bấm Up bài ngay
                        ORDER BY COALESCE(pr.hot, 0) DESC, COALESCE(p.last_bump_at, '') ASC, p.posted_at DESC LIMIT ?""",
                     (sale["id"], cutoff, fresh, today + "%", per_nick))
        t = now + timedelta(minutes=random.randint(1, 6))
        end = datetime.strptime(f"{today} {sale['active_to'] or '22:00'}", "%Y-%m-%d %H:%M")
        words = post_care.texts_for(posts, sale["id"]) if posts else []  # Bảo viết mỗi bài một câu khác nhau + dòng liên hệ
        for p, text in zip(posts, words):
            if t > end:
                break
            db.run("INSERT INTO bumps(post_id, sale_id, account_id, text, status, scheduled_for, created_at) VALUES (?,?,?,?,?,?,?)",
                   (p["id"], sale["sale_id"], sale["id"], text, "scheduled", t.strftime("%Y-%m-%d %H:%M"), db.now()))
            total += 1
            t += timedelta(minutes=gap + random.randint(0, 4))
    db.log("bao", "Lịch up bài", f"Rà soát bài đã đăng: xếp {total} lượt bình luận ảnh kèm câu mới và dòng liên hệ" if total
           else "Rà soát bài đã đăng: không có bài nào cần up hôm nay")
    set_status("bao", "idle", f"Hôm nay xếp {total} lượt up bài")
    return total


def bump_now(post_id: int) -> int | None:
    p = db.one("SELECT * FROM posts WHERE id=?", (post_id,))
    if not p or not p.get("account_id"):
        return None
    import post_care
    text = post_care.texts_for([p], p["account_id"])[0]
    return db.run("INSERT INTO bumps(post_id, sale_id, account_id, text, status, scheduled_for, created_at) VALUES (?,?,?,?,?,?,?)",
                  (post_id, p["sale_id"], p["account_id"], text, "scheduled",
                   db.clock().strftime("%Y-%m-%d %H:%M"), db.now()))


# ---------------------------------------------------------------- Hà: chăm sóc khách
def score_lead(lead: dict) -> int:
    s = 40
    text = f"{lead.get('need', '')} {lead.get('business_type', '')}".lower()
    for kw, pts in [("số lượng", 15), ("sỉ", 10), ("giá", 10), ("hóa đơn", 10), ("livestream", 8),
                    ("ads", 8), ("quảng cáo", 8), ("sàn", 8), ("shopee", 8), ("tiktok", 8), ("mẫu", 5)]:
        if kw in text:
            s += pts
    return min(s, 100)


def draft_reply(lead_id: int, message: str = "") -> str:
    lead = db.one("SELECT * FROM leads WHERE id=?", (lead_id,))
    if not lead:
        return ""
    set_status("ha", "working", f"Đang soạn tin cho {lead['name']}")
    import knowledge
    q = (message or lead.get("need") or "").strip()
    hit = knowledge.known_answer("ha", q, kind="faq") if q and db.get_settings().get("knowledge_enabled", "1") == "1" else None
    if hit:  # câu khách hỏi đã biết cách trả lời: tự soạn từ sổ kiến thức, không gọi Claude
        knowledge._used([hit["id"]])
        knowledge._log("ha", "memory", q, hit["id"])
        import pricing
        reply = pricing.sanitize(f"Dạ em chào {lead['name']} ạ! {hit['content'].strip()} Anh/chị cho em xin SĐT hoặc Zalo để em gửi ảnh thật "
                                 f"và tư vấn nhé? Giá sỉ anh/chị nhắn Zalo {pricing.zalo()} để được báo trực tiếp ạ.")
        rid = db.run("INSERT INTO replies(lead_id, text, created_at) VALUES (?,?,?)", (lead_id, reply, db.now()))
        db.log("ha", "Soạn tin", f"Soạn tin cho khách {lead['name']} bằng kiến thức đã học (không cần hỏi Claude): {hit['topic'][:60]}")
        set_status("ha", "idle", "Chờ sếp duyệt tin nhắn")
        return {"reply": reply, "reply_id": rid, "source": "memory"}
    products = [{**p, "dang_ban_chay": bool(p.pop("hot"))} for p in
                db.q("SELECT name, moq, hot FROM products ORDER BY hot DESC, id")]
    prompt = f"""Soạn tin nhắn Messenger/Zalo trả lời khách sỉ tiềm năng.
Khách: {lead['name']} | Kinh doanh: {lead['business_type']} | Nguồn: {lead['source']}
Nhu cầu: {lead['need']} | Trạng thái: {lead['status']} | Ghi chú: {lead['note'] or ''}
Tin nhắn mới nhất của khách: {message or '(chưa có, đây là tin chủ động)'}
Danh sách sản phẩm (dang_ban_chay = sếp muốn ưu tiên chào): {products}
Nếu khách chưa nói rõ sản phẩm, gợi ý sản phẩm đang bán chạy trước. Tin ngắn (dưới 90 chữ), thân thiện, gợi ý 1 bước tiếp theo rõ ràng (mời nhắn Zalo để được báo giá/gửi mẫu thử/hẹn gọi), kết bằng 1 câu hỏi.
Không báo giá: khách hỏi giá thì mời nhắn Zalo {__import__('pricing').zalo()} để được báo giá trực tiếp."""
    prompt += knowledge.block("ha", q)
    if llm.live:  # nhờ Claude soạn, đồng thời rút ra kiến thức dùng lại được để lần sau tự trả lời
        data = llm.json(system_prompt("ha", db.get_settings()), prompt + """
Trả về JSON {"reply": "tin nhắn gửi khách", "faq": {"question": "câu hỏi chung của khách (bỏ tên riêng), để trống nếu khách không hỏi gì cụ thể",
"answer": "cách trả lời chung dùng lại được cho khách khác (không tên riêng, dưới 60 chữ)", "topic": "chủ đề ngắn"}}""",
                        mock=None, max_tokens=500, task="replies")
        reply = (data or {}).get("reply") if isinstance(data, dict) else None
        faq = (data or {}).get("faq") if isinstance(data, dict) else None
        if isinstance(faq, dict) and (faq.get("question") or "").strip() and (faq.get("answer") or "").strip():
            knowledge.learn_answer("ha", faq["question"], faq["answer"], topic=faq.get("topic") or "")
        reply = reply or mock_brain.lead_reply(lead, message)
    else:
        reply = mock_brain.lead_reply(lead, message)
    import pricing
    reply = pricing.sanitize(reply)
    rid = db.run("INSERT INTO replies(lead_id, text, created_at) VALUES (?,?,?)", (lead_id, reply, db.now()))
    db.log("ha", "Soạn tin", f"Soạn tin nhắn cho khách {lead['name']}")
    set_status("ha", "idle", "Chờ sếp duyệt tin nhắn")
    return {"reply": reply, "reply_id": rid, "source": "claude" if llm.live else "mock"}


def follow_up_list() -> list[dict]:
    cutoff = (db.clock() - timedelta(days=2)).strftime("%Y-%m-%d %H:%M:%S")
    return db.q("""SELECT * FROM leads WHERE status IN ('new','contacted','sample')
                   AND (last_contact_at IS NULL OR last_contact_at < ? OR status='new')
                   ORDER BY score DESC""", (cutoff,))


# ---------------------------------------------------------------- Việc hằng ngày
def daily_work() -> dict:
    """Chạy sau cuộc họp: Lan viết bài, Tuấn xếp lịch, Hà lọc khách cần bám."""
    demand = post_demand()
    res = generate_posts_batch(demand) if demand else {"mode": "none", "count": 0}
    plan = plan_distribution()
    fu = follow_up_list()
    db.log("ha", "Danh sách bám khách", f"{len(fu)} khách cần liên hệ lại hôm nay")
    set_status("khoa", "working", "Cập nhật báo cáo")
    st = stats()
    db.log("khoa", "Báo cáo", f"{st['posted_total']} bài đã đăng, {st['leads']} khách, {st['leads_hot']} khách nóng")
    set_status("khoa", "idle", "Báo cáo đã cập nhật")
    return {"drafts": res["count"], "draft_mode": res["mode"], "scheduled": len(plan), "follow_ups": len(fu)}

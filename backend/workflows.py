"""Công việc của từng Agent: viết bài, phân phối nhóm, chăm khách, phân tích."""
import json
import random
from datetime import datetime, timedelta

import db
import mock_brain
from agents import system_prompt
from llm import llm, month_spent, parse_json

# Trạng thái hiện tại của từng agent (hiển thị trên văn phòng 3D)
STATUS = {a: {"state": "idle", "text": "Đang sẵn sàng"} for a in ["minh", "lan", "tuan", "ha", "khoa"]}


TARGET_NAME = {"group": "Hội nhóm", "profile": "Trang cá nhân", "page": "Fanpage"}


def set_status(agent_id: str, state: str, text: str):
    STATUS[agent_id] = {"state": state, "text": text, "at": db.now()}


# ---------------------------------------------------------------- Khoa: số liệu
def stats() -> dict:
    yesterday = (datetime.now() - timedelta(days=1)).strftime("%Y-%m-%d")
    c = lambda sql, p=(): db.one(sql, p)["n"]
    posted = c("SELECT COUNT(*) n FROM posts WHERE status='posted'")
    leads = c("SELECT COUNT(*) n FROM leads")
    best = db.one("""SELECT g.name, SUM(p.leads) l FROM posts p JOIN groups g ON g.id=p.group_id
                     WHERE p.status='posted' GROUP BY g.id ORDER BY l DESC LIMIT 1""")
    groups = db.q("SELECT * FROM groups")
    return {
        "drafts": c("SELECT COUNT(*) n FROM posts WHERE status='draft'"),
        "approved": c("SELECT COUNT(*) n FROM posts WHERE status IN ('approved','scheduled')"),
        "posted_total": posted,
        "posted_today": c("SELECT COUNT(*) n FROM posts WHERE status='posted' AND posted_at LIKE ?", (db.today() + "%",)),
        "posts_yesterday": c("SELECT COUNT(*) n FROM posts WHERE created_at LIKE ?", (yesterday + "%",)),
        "groups": len(groups),
        "groups_ready": sum(1 for g in groups if group_ready(g)),
        "leads": leads,
        "leads_new": c("SELECT COUNT(*) n FROM leads WHERE status='new'"),
        "leads_hot": c("SELECT COUNT(*) n FROM leads WHERE score>=75 AND status NOT IN ('ordered','lost')"),
        "leads_ordered": c("SELECT COUNT(*) n FROM leads WHERE status='ordered'"),
        "best_group": best["name"] if best and best["l"] else None,
        "lead_per_post": round(leads / posted, 2) if posted else 0,
        "tasks_open": c("SELECT COUNT(*) n FROM tasks WHERE status!='done'"),
        "failed": c("SELECT COUNT(*) n FROM posts WHERE status='failed'"),
        "sales_total": c("SELECT COUNT(*) n FROM sales"),
        "sales_ok": c("SELECT COUNT(*) n FROM sales WHERE login_status='ok' AND auto_post=1"),
        "sales_problem": c("SELECT COUNT(*) n FROM sales WHERE login_status IN ('checkpoint','not_logged_in')"),
        "ai_live": llm.live,
        "ai_cost_month": round(month_spent(), 3),
    }


def group_ready(g: dict) -> bool:
    if not g.get("last_posted_at"):
        return True
    last = datetime.strptime(g["last_posted_at"][:10], "%Y-%m-%d")
    return (datetime.now() - last).days >= int(g.get("min_days_between_posts") or 3)


# ---------------------------------------------------------------- Lan: viết bài
WHERE = {"group": "một hội nhóm Facebook về bán hàng online/nguồn hàng",
         "profile": "trang cá nhân Facebook của nhân viên kinh doanh",
         "page": "Fanpage của xưởng"}


def _post_prompt(p: dict, ang: str, target_type: str, settings: dict, note: str, i: int) -> str:
    return f"""Viết 1 bài đăng Facebook để đăng lên {WHERE[target_type]}, nhằm tìm khách SỈ (người bán online) nhập sản phẩm sau:
Tên: {p['name']} | Loại: {p['category']} | Mô tả: {p['description']}
Giá sỉ: {p['wholesale_price']} | Giá lẻ gợi ý: {p['retail_price']} | Nhập tối thiểu: {p['moq']}
Điểm bán: {p['selling_points']}
Góc tiếp cận: {mock_brain.ANGLES.get(ang, ang)}
Liên hệ: {settings.get('contact_info')}
Yêu cầu thêm của sếp: {note or 'không'}
Bài dài 110-180 chữ, emoji vừa phải, mở đầu gây chú ý, kết bằng lời kêu gọi bình luận/inbox.
Câu chữ phải khác các bài khác (bài số {i + 1}, mã {random.randint(100, 999)}). Không hứa công dụng chữa bệnh.
Trả về JSON: {{"title": "...", "content": "...", "hashtags": "#... #... (không dấu)", "image_idea": "1 câu mô tả ảnh nên chụp"}}"""


def _save_post(p: dict, ang: str, target_type: str, data) -> dict:
    if not isinstance(data, dict) or not data.get("content"):
        data = mock_brain.post(p, ang, target_type, db.get_settings())
    pid = db.run("""INSERT INTO posts(agent_id, product_id, target_type, angle, title, content, hashtags,
                    image_idea, status, created_at) VALUES ('lan',?,?,?,?,?,?,?,'draft',?)""",
                 (p["id"], target_type, ang, data.get("title", ""), data["content"],
                  data.get("hashtags", ""), data.get("image_idea", ""), db.now()))
    return db.one("SELECT * FROM posts WHERE id=?", (pid,))


def _plan_items(count: int, product_id: int | None, target_type: str, angle: str | None):
    products = db.q("SELECT * FROM products" + (" WHERE id=?" if product_id else ""),
                    (product_id,) if product_id else ())
    if not products:
        return []
    items = []
    for i in range(count):
        p = products[i % len(products)] if product_id else random.choice(products)
        items.append((i, p, angle or random.choice(list(mock_brain.ANGLES)), target_type))
    return items


def generate_posts(count: int = 3, product_id: int | None = None, target_type: str = "group",
                   angle: str | None = None, note: str = "") -> list[dict]:
    """Viết ngay (sếp đang chờ trên giao diện)."""
    settings = db.get_settings()
    items = _plan_items(count, product_id, target_type, angle)
    if not items:
        return []
    set_status("lan", "working", f"Đang viết {count} bài đăng")
    created = []
    for i, p, ang, tt in items:
        data = llm.json(system_prompt("lan", settings), _post_prompt(p, ang, tt, settings, note, i),
                        mock=lambda p=p, ang=ang, tt=tt: mock_brain.post(p, ang, tt, settings),
                        max_tokens=900, task="posts")
        created.append(_save_post(p, ang, tt, data))
    db.log("lan", "Viết bài", f"Đã viết {len(created)} bài nháp chờ sếp duyệt")
    set_status("lan", "idle", f"Vừa viết xong {len(created)} bài")
    return created


def generate_posts_batch(plan: list[tuple[str, int]]) -> dict:
    """Viết theo lô qua Batch API (rẻ hơn 50%). plan: [(target_type, số bài)].
    Không có API key / tắt chế độ lô / gửi lỗi -> viết ngay như bình thường."""
    settings = db.get_settings()
    items = [it for tt, n in plan if n > 0 for it in _plan_items(n, None, tt, None)]
    if not items:
        return {"mode": "none", "count": 0}
    if settings.get("use_batch") != "1" or not llm.live:
        made = [_save_post(p, ang, tt, llm.json(system_prompt("lan", settings), _post_prompt(p, ang, tt, settings, "", i),
                mock=lambda p=p, ang=ang, tt=tt: mock_brain.post(p, ang, tt, settings), max_tokens=900, task="posts"))
                for i, p, ang, tt in items]
        db.log("lan", "Viết bài", f"Đã viết {len(made)} bài nháp chờ sếp duyệt")
        return {"mode": "now", "count": len(made)}
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
    return {"mode": "now", "count": len(made)}


def poll_batches():
    """Gọi định kỳ: lô nào xong thì nhập bài nháp."""
    if not llm.live:
        return
    for b in db.q("SELECT * FROM ai_batches WHERE status='in_progress'"):
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
    return [("group", max(0, cap_group - have("group"))), ("profile", max(0, cap_profile - have("profile")))]


# ---------------------------------------------------------------- Tuấn: phân phối nhóm
def _dt(s: str) -> datetime:
    return datetime.strptime(s[:16], "%Y-%m-%d %H:%M")


def plan_distribution() -> list[dict]:
    """Tuấn ghép bài đã duyệt với (nhóm, nick sale, giờ đăng).

    Quy tắc: nick phải là thành viên nhóm; mỗi nhóm chỉ nhận 1 bài trong 1 lượt và phải hết giãn cách;
    mỗi nick không vượt số bài/ngày, cách nhau ít nhất N phút, chỉ đăng trong khung giờ của nick;
    mỗi nick tối đa 1 bài trang cá nhân/ngày. Mỗi bài là một nội dung khác nhau (Lan viết riêng).
    """
    set_status("tuan", "working", "Đang xếp lịch đăng nhóm")
    today, now = db.today(), datetime.now()
    sales = [s for s in db.q("SELECT * FROM sales ORDER BY id") if s["login_status"] == "ok" and s["auto_post"]]
    load = {}
    for s in sales:
        rows = db.q("""SELECT scheduled_for, posted_at, target_type FROM posts WHERE sale_id=? AND
                       ((status IN ('scheduled','posting') AND scheduled_for LIKE ?) OR (status='posted' AND posted_at LIKE ?))""",
                    (s["id"], today + "%", today + "%"))
        times = [r["scheduled_for"] or r["posted_at"] for r in rows]
        load[s["id"]] = {"count": len(rows), "last": max(times) if times else None,
                         "profile": sum(r["target_type"] == "profile" for r in rows)}
    taken = {r["group_id"] for r in db.q("SELECT group_id FROM posts WHERE status IN ('scheduled','posting') AND group_id IS NOT NULL")}
    groups = [g for g in db.q("SELECT * FROM groups ORDER BY leads_count DESC, members DESC")
              if group_ready(g) and g["id"] not in taken]
    plan = []

    def next_slot(s):
        L = load[s["id"]]
        if L["count"] >= int(s["max_posts_per_day"] or 5):
            return None
        start = max(now + timedelta(minutes=3), _dt(f"{today} {s['active_from'] or '08:00'}"))
        if L["last"]:
            start = max(start, _dt(L["last"]) + timedelta(minutes=int(s["min_gap_minutes"] or 40) + random.randint(0, 12)))
        return start if start <= _dt(f"{today} {s['active_to'] or '22:00'}") else None

    def assign(post, sale, when, group=None):
        db.run("UPDATE posts SET sale_id=?, group_id=?, scheduled_for=?, status='scheduled', error=NULL WHERE id=?",
               (sale["id"] if sale else None, group["id"] if group else None, when, post["id"]))
        if sale:
            L = load[sale["id"]]
            L["count"] += 1
            L["last"] = when
            L["profile"] += post["target_type"] == "profile"
        plan.append({"post_id": post["id"], "group": group["name"] if group else TARGET_NAME[post["target_type"]],
                     "time": when, "sale": sale["name"] if sale else None})

    approved = db.q("SELECT * FROM posts WHERE status='approved' AND target_type='group' ORDER BY id")
    if sales:
        for post in approved:
            for g in list(groups):
                members = {int(x) for x in (g.get("member_sale_ids") or "").split(",") if x.strip().isdigit()}
                cands = [(t, load[s["id"]]["count"], s) for s in sales
                         if (not members or s["id"] in members) and (t := next_slot(s))]
                if cands:
                    t, _, s = min(cands, key=lambda c: (c[0], c[1]))
                    assign(post, s, t.strftime("%Y-%m-%d %H:%M"), g)
                    groups.remove(g)
                    break
        for post in db.q("SELECT * FROM posts WHERE status='approved' AND target_type='profile' ORDER BY id"):
            cands = [(t, s) for s in sales if load[s["id"]]["profile"] == 0 and (t := next_slot(s))]
            if cands:
                t, s = min(cands, key=lambda c: c[0])
                assign(post, s, t.strftime("%Y-%m-%d %H:%M"))
    else:  # chưa có nick sale tự động -> xếp lịch để người đăng tay
        per_day = int(db.get_settings().get("posts_per_day", 4))
        slots = ["09:00", "11:30", "15:00", "20:00", "21:30"]
        for post, group in zip(approved[:per_day], groups):
            assign(post, None, f"{today} {slots[len(plan) % len(slots)]}", group)
    # Bài Fanpage đã duyệt: xếp giờ, đến giờ hệ thống tự đăng qua Graph API
    page_slots = ["10:00", "19:30"]
    for i, post in enumerate(db.q("SELECT * FROM posts WHERE status='approved' AND target_type='page' ORDER BY id")[:2]):
        when = f"{db.today()} {page_slots[i]}"
        db.run("UPDATE posts SET scheduled_for=?, status='scheduled' WHERE id=?", (when, post["id"]))
        plan.append({"post_id": post["id"], "group": "Fanpage", "time": when})
    db.log("tuan", "Xếp lịch", f"Đã xếp {len(plan)} bài cho hôm nay" if plan
           else "Chưa có bài đã duyệt hoặc nhóm đủ điều kiện để xếp lịch")
    set_status("tuan", "idle", f"Lịch hôm nay: {len(plan)} bài")
    return plan


def mark_posted(post_id: int, posted_url: str = "", poster: str = "", fb_post_id: str = ""):
    post = db.one("SELECT * FROM posts WHERE id=?", (post_id,))
    db.run("UPDATE posts SET status='posted', posted_at=?, posted_url=?, poster=?, fb_post_id=? WHERE id=?",
           (db.now(), posted_url, poster, fb_post_id, post_id))
    if post and post.get("group_id"):
        db.run("UPDATE groups SET last_posted_at=? WHERE id=?", (db.now(), post["group_id"]))
    db.log("tuan", "Đã đăng", f"Bài #{post_id} được đánh dấu đã đăng {('bởi ' + poster) if poster else ''}")


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
    products = db.q("SELECT name, wholesale_price, moq FROM products")
    prompt = f"""Soạn tin nhắn Messenger/Zalo trả lời khách sỉ tiềm năng.
Khách: {lead['name']} | Kinh doanh: {lead['business_type']} | Nguồn: {lead['source']}
Nhu cầu: {lead['need']} | Trạng thái: {lead['status']} | Ghi chú: {lead['note'] or ''}
Tin nhắn mới nhất của khách: {message or '(chưa có, đây là tin chủ động)'}
Danh sách sản phẩm: {products}
Tin ngắn (dưới 90 chữ), thân thiện, gợi ý 1 bước tiếp theo rõ ràng (gửi bảng giá/mẫu thử/hẹn gọi), kết bằng 1 câu hỏi."""
    reply = llm.chat(system_prompt("ha", db.get_settings()), prompt, mock=lambda: mock_brain.lead_reply(lead, message),
                     max_tokens=350, task="replies")
    db.log("ha", "Soạn tin", f"Soạn tin nhắn cho khách {lead['name']}")
    set_status("ha", "idle", "Chờ sếp duyệt tin nhắn")
    return reply


def follow_up_list() -> list[dict]:
    cutoff = (datetime.now() - timedelta(days=2)).strftime("%Y-%m-%d %H:%M:%S")
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

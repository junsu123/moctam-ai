"""CEO: điều hành nhân sự phòng kinh doanh.

- Thực thi luật sa thải (sale không đạt KPI tháng) và quyết định có tuyển người thay vào nick cũ hay không.
- Tăng nhân viên sale khi doanh thu chạm các mốc (mặc định 50 triệu, 100 triệu).
- Tăng nhân viên khi số liệu tìm khách trên Facebook cho thấy còn tiềm năng (đánh giá mỗi ngày, tối đa 1 lần / 14 ngày).

Mọi quyết định dựa trên luật và số liệu thật, không gọi AI (không tốn tiền). Một nhân viên sale mới cần một tài khoản
Facebook: CEO tạo chỗ làm và hồ sơ Chrome, sếp chỉ việc đăng nhập nick lần đầu. Chế độ "Chờ sếp duyệt" thì mọi việc
tuyển dụng phải được sếp bấm duyệt (trong phần mềm hoặc Telegram) mới thực hiện.
"""
import html
import json
import shutil
from datetime import date, datetime, timedelta

import db

NAME = "Đức"
NAME_POOL = ["Hương", "Đạt", "Trang", "Phúc", "Ngọc", "Bảo", "Vy", "Khánh", "Thảo", "Long", "My", "Duy", "Yến",
             "Hiếu", "Nhi", "Sơn", "Châu", "Tâm"]
POTENTIAL_WINDOW = 14
WEAK_NICK_PCT = 30          # nick đạt dưới 30% chỉ tiêu: vấn đề nằm ở nick/nhóm, không tuyển người thay
MIN_RUNWAY_DAYS = 60        # chỉ tuyển thêm khi vốn còn đủ nuôi agent ít nhất 60 ngày
REMIND_EVERY_DAYS = 3


def s() -> dict:
    return db.get_settings()


def mode() -> str:
    return "approve" if s().get("ceo_mode") == "approve" else "auto"


def _tg(text: str, buttons=None):
    try:
        import telegram_bot
        if telegram_bot.configured():
            telegram_bot.send(text, buttons=buttons)
    except Exception as e:
        print("[ceo]", e)


def _decide(kind: str, title: str, reason: str, status: str = "done", sale_id=None, data=None) -> int:
    did = db.run("""INSERT INTO ceo_decisions(kind, status, sale_id, title, reason, data, created_at, decided_at)
                    VALUES (?,?,?,?,?,?,?,?)""",
                 (kind, status, sale_id, title, reason, json.dumps(data or {}, ensure_ascii=False), db.now(),
                  db.now() if status != "proposed" else None))
    db.log("ceo", title, reason)
    return did


def _buttons(did: int):
    return [[{"text": "✅ Duyệt", "callback_data": f"c:{did}:ok"}, {"text": "✖️ Không", "callback_data": f"c:{did}:no"}]]


# ---------------------------------------------------------------- nhân sự
def headcount() -> dict:
    rows = db.q("SELECT * FROM sales WHERE COALESCE(is_sample,0)=0 AND COALESCE(status,'active')!='fired'")
    import agents
    return {"working": sum(1 for r in rows if r["login_status"] == "ok"),
            "waiting_nick": sum(1 for r in rows if r["login_status"] != "ok" and r.get("hired_by") == "ceo"),
            "total": len(rows), "max": agents.MAX_SALES}


def _pick_name() -> str:
    used = {r["name"] for r in db.q("SELECT name FROM sales")}  # không dùng lại tên người đã nghỉ, tránh nhầm lẫn
    for n in NAME_POOL:
        if n not in used:
            return n
    return f"Sale {len(used) + 1}"


def hire(reason: str, source: str, name: str | None = None) -> dict | None:
    """Tạo chỗ làm cho một sale mới. Nick Facebook: sếp đăng nhập lần đầu."""
    import agents
    import browser_poster
    import company
    if not company.active():
        return None
    if headcount()["total"] >= agents.MAX_SALES:
        _decide("hold", "Không tuyển thêm được", f"{reason} Nhưng văn phòng đã đủ {agents.MAX_SALES} sale.")
        return None
    removed = db.clear_samples(("sales",))
    if removed:
        db.log("ceo", "Dọn sale mẫu", f"Đã cho {removed['sales']} sale mẫu rời văn phòng")
    name = (name or "").strip() or _pick_name()
    sid = db.run("""INSERT INTO sales(name, fb_name, auto_post, created_at, hired_by, hire_reason) VALUES (?,?,1,?,?,?)""",
                 (name, "", db.now(), "ceo", f"{source}: {reason}"))
    db.run("UPDATE sales SET profile_dir=? WHERE id=?", (str(browser_poster.profile_dir(sid)), sid))
    _decide("hire", f"Tuyển sale mới: {name}", reason, sale_id=sid, data={"source": source})
    _tg(f"👔 <b>CEO {NAME} tuyển sale mới: {html.escape(name)}</b>\nLý do: {html.escape(reason)}\n\n"
        f"Việc của sếp: chuẩn bị 1 tài khoản Facebook cho {html.escape(name)}, mở phần mềm → <b>Nhân viên sale</b> → "
        f"{html.escape(name)} → <b>Đăng nhập lần đầu</b>. Kỳ KPI của {html.escape(name)} bắt đầu từ ngày nick chạy được.")
    return db.one("SELECT * FROM sales WHERE id=?", (sid,))


def replace(old_id: int, name: str = "", by: str = "boss") -> dict:
    """Người mới tiếp quản nick (hồ sơ Chrome đã đăng nhập) của sale đã nghỉ."""
    import company
    old = db.one("SELECT * FROM sales WHERE id=?", (old_id,))
    if not old or old.get("status") != "fired":
        raise ValueError("Chỉ tuyển thay cho sale đã nghỉ việc")
    if old.get("replaced_by"):
        raise ValueError("Nick này đã có người tiếp quản")
    if company.status() == "dissolved":
        raise ValueError("Công ty đã giải thể. Thành lập lại trước khi tuyển.")
    name = (name or "").strip() or _pick_name()
    new_id = db.run("""INSERT INTO sales(name, fb_name, login_status, created_at, kpi_period_start, max_posts_per_day,
                       min_gap_minutes, active_from, active_to, hired_by, hire_reason) VALUES (?,?,?,?,?,?,?,?,?,?,?)""",
                    (name, old["fb_name"], old["login_status"], db.now(),
                     db.today() if old["login_status"] == "ok" else None, old["max_posts_per_day"],
                     old["min_gap_minutes"], old["active_from"], old["active_to"], by,
                     f"Tiếp quản nick của {old['name']}"))
    src, dst = db.PROFILES_DIR / f"sale-{old_id}", db.PROFILES_DIR / f"sale-{new_id}"
    if src.exists() and not dst.exists():
        shutil.move(str(src), str(dst))
    db.run("UPDATE sales SET profile_dir=? WHERE id=?", (str(dst), new_id))
    db.run("UPDATE sales SET replaced_by=?, ceo_handled=1 WHERE id=?", (new_id, old_id))
    db.run("UPDATE groups SET member_sale_ids=REPLACE(','||member_sale_ids||',', ?, ?) WHERE member_sale_ids!=''",
           (f",{old_id},", f",{new_id},"))
    db.run("UPDATE groups SET member_sale_ids=TRIM(member_sale_ids, ',')")
    db.log("ceo" if by == "ceo" else "minh", "Tuyển người thay",
           f"{name} tiếp quản nick {old['fb_name'] or old['name']} của {old['name']}")
    return db.one("SELECT * FROM sales WHERE id=?", (new_id,))


def _replaced_before(sale_id: int) -> bool:
    """Sale này chính là người thay cho một sale đã bị sa thải trước đó trên cùng nick."""
    return bool(db.one("SELECT 1 x FROM sales WHERE replaced_by=?", (sale_id,)))


def handle_fired():
    """Sau khi sa thải theo luật KPI, CEO quyết định có tuyển người thay vào nick cũ hay không."""
    import company
    gen = s().get("company_gen") or "0"
    for old in db.q("""SELECT * FROM sales WHERE status='fired' AND COALESCE(is_sample,0)=0 AND fired_gen=?
                       AND replaced_by IS NULL AND ceo_handled IS NULL""", (gen,)):
        db.run("UPDATE sales SET ceo_handled=1 WHERE id=?", (old["id"],))
        rv = json.loads(old.get("fire_review") or "{}")
        pct = rv.get("pct", 0)
        nick = old["fb_name"] or old["name"]
        if old["login_status"] != "ok":
            _decide("keep_slot", f"Không tuyển thay {old['name']}",
                    f"Nick {nick} đang lỗi đăng nhập. Sếp xử lý nick xong thì tuyển người thay ở trang Công ty.", sale_id=old["id"])
            continue
        if _replaced_before(old["id"]):
            _decide("keep_slot", f"Dừng nick {nick}",
                    f"Đây là lần thứ hai liên tiếp nick {nick} không đạt KPI ({pct}% chỉ tiêu). Vấn đề nằm ở nick hoặc các "
                    "nhóm nick tham gia, đổi người không giải quyết được. Sếp nên đổi nick khác hoặc bổ sung hội nhóm.",
                    sale_id=old["id"])
            continue
        if pct < WEAK_NICK_PCT:
            _decide("keep_slot", f"Không tuyển thay {old['name']}",
                    f"Nick {nick} chỉ đạt {pct}% chỉ tiêu, quá thấp để đổ lỗi cho người giữ nick. Sếp kiểm tra lại nick "
                    "(bạn bè, độ tin cậy) và các hội nhóm nick đã tham gia.", sale_id=old["id"])
            continue
        reason = (f"{old['name']} đạt {pct}% chỉ tiêu: nick {nick} vẫn có khách, cho người mới tiếp quản và chạy kỳ KPI mới.")
        if mode() == "approve":
            did = _decide("replace", f"Đề xuất tuyển người thay {old['name']}", reason, status="proposed", sale_id=old["id"])
            _tg(f"👔 <b>CEO {NAME} đề xuất</b> tuyển người thay {html.escape(old['name'])} (nick {html.escape(nick)}).\n"
                f"{html.escape(reason)}", buttons=_buttons(did))
            continue
        new = replace(old["id"], by="ceo")
        _decide("replace", f"{new['name']} tiếp quản nick {nick}", reason, sale_id=new["id"])
        _tg(f"👔 <b>CEO {NAME}</b>: {html.escape(new['name'])} tiếp quản nick {html.escape(nick)} thay {html.escape(old['name'])}. "
            "Nick giữ nguyên đăng nhập, sếp không cần làm gì.")


# ---------------------------------------------------------------- mốc doanh thu
def milestones() -> list[dict]:
    out = []
    for part in (s().get("ceo_milestones") or "").split(","):
        if ":" in part:
            a, n = part.split(":", 1)
            if a.strip().isdigit() and n.strip().isdigit():
                out.append({"amount": int(a), "hires": int(n)})
    done = set((s().get("ceo_milestones_done") or "").split(","))
    for m in sorted(out, key=lambda x: x["amount"]):
        m["done"] = str(m["amount"]) in done
    return sorted(out, key=lambda x: x["amount"])


def check_milestones():
    import company
    if not company.active():
        return
    rev = company.finance()["revenue"]
    done = [x for x in (s().get("ceo_milestones_done") or "").split(",") if x]
    for m in milestones():
        if m["done"] or rev < m["amount"]:
            continue
        done.append(str(m["amount"]))
        db.set_setting("ceo_milestones_done", ",".join(done))
        reason = f"Doanh thu đạt mốc {company.fmt_vnd(m['amount'])} (hiện {company.fmt_vnd(rev)})."
        _tg(f"🎯 <b>Doanh thu chạm mốc {company.fmt_vnd(m['amount'])}</b>. CEO {NAME} tăng {m['hires']} sale.")
        for _ in range(m["hires"]):
            _hire_or_propose(reason, "milestone")


def _hire_or_propose(reason: str, source: str):
    import agents
    if headcount()["total"] >= agents.MAX_SALES:
        _decide("hold", "Không tuyển thêm được", f"{reason} Nhưng văn phòng đã đủ {agents.MAX_SALES} sale.")
        return
    if mode() == "approve":
        did = _decide("hire", "Đề xuất tuyển thêm 1 sale", reason, status="proposed", data={"source": source})
        _tg(f"👔 <b>CEO {NAME} đề xuất tuyển thêm 1 sale</b>\n{html.escape(reason)}\n"
            "Duyệt thì sếp cần chuẩn bị thêm 1 tài khoản Facebook.", buttons=_buttons(did))
    else:
        hire(reason, source)


# ---------------------------------------------------------------- tiềm năng Facebook
def potential() -> dict:
    """Đánh giá tiềm năng tìm khách trên Facebook từ số liệu 14 ngày gần nhất."""
    import company
    st = s()
    today = date.today()
    w0 = (today - timedelta(days=POTENTIAL_WINDOW - 1)).isoformat()
    mid = (today - timedelta(days=6)).isoformat()
    since = max(w0, company.founded() or w0)
    leads = db.q("""SELECT substr(COALESCE(phone_at, created_at),1,10) d FROM leads
                    WHERE phone IS NOT NULL AND phone!='' AND COALESCE(is_sample,0)=0
                    AND substr(COALESCE(phone_at, created_at),1,10) >= ?""", (since,))
    total = len(leads)
    last7 = sum(1 for r in leads if r["d"] >= mid)
    prev7 = total - last7
    nick_days = db.one("SELECT COUNT(*) n, COALESCE(SUM(target),0) t FROM sale_days WHERE date >= ?", (since,))
    days = (today - date.fromisoformat(since)).days + 1
    kmax = int(st.get("kpi_max") or 10)
    kmin = int(st.get("kpi_min") or 5)
    per_day = total / days if days else 0
    per_nick_day = total / nick_days["n"] if nick_days["n"] else 0
    quota_pct = round(100 * total / nick_days["t"]) if nick_days["t"] else 0
    growth = round(100 * (last7 - prev7) / prev7) if prev7 else (100 if last7 else 0)
    hc = headcount()
    fin = company.finance()
    runway = fin["runway_days"]
    last_hire = st.get("ceo_last_potential_hire") or ""
    cooldown = int(st.get("ceo_hire_cooldown_days") or 14)
    cool_ok = not last_hire or (today - date.fromisoformat(last_hire)).days >= cooldown
    free_groups = db.one("""SELECT COUNT(*) n FROM groups WHERE COALESCE(is_sample,0)=0
                            AND COALESCE(member_sale_ids,'')=''""")["n"]
    signal = [
        {"key": "exceed", "label": f"Cả phòng trung bình ≥ {kmax} khách có SĐT/ngày (mức vượt KPI)",
         "value": f"{per_day:.1f}/ngày", "ok": per_day >= kmax},
        {"key": "quota", "label": "Mỗi nick vượt 120% chỉ tiêu của mình",
         "value": f"{quota_pct}% chỉ tiêu", "ok": quota_pct >= 120},
    ]
    guards = [
        {"key": "data", "label": f"Đủ dữ liệu: ít nhất {POTENTIAL_WINDOW} ngày hoạt động",
         "value": f"{days} ngày", "ok": days >= POTENTIAL_WINDOW, "fail": f"mới có {days}/{POTENTIAL_WINDOW} ngày dữ liệu"},
        {"key": "trend", "label": "Khách 7 ngày gần nhất không giảm so với 7 ngày trước",
         "value": f"{last7} so với {prev7} ({'+' if growth >= 0 else ''}{growth}%)", "ok": last7 >= prev7, "fail": "số khách tuần này đang giảm"},
        {"key": "waiting", "label": "Không còn sale mới đang chờ sếp đăng nhập nick",
         "value": f"{hc['waiting_nick']} đang chờ", "ok": hc["waiting_nick"] == 0,
         "fail": f"còn {hc['waiting_nick']} sale mới chờ sếp đăng nhập nick"},
        {"key": "room", "label": "Văn phòng còn chỗ", "value": f"{hc['total']}/{hc['max']} sale", "ok": hc["total"] < hc["max"], "fail": "văn phòng đã đủ người"},
        {"key": "runway", "label": f"Vốn đủ nuôi agent ít nhất {MIN_RUNWAY_DAYS} ngày nữa",
         "value": "chưa phát sinh chi phí" if runway is None else (f"~{runway} ngày" if runway <= 365 else "hơn 1 năm"),
         "ok": runway is None or runway >= MIN_RUNWAY_DAYS, "fail": f"vốn không đủ nuôi agent thêm {MIN_RUNWAY_DAYS} ngày"},
        {"key": "cooldown", "label": f"Lần tuyển vì tiềm năng gần nhất đã cách {cooldown} ngày",
         "value": f"lần trước {last_hire}" if last_hire else "chưa tuyển lần nào", "ok": cool_ok,
         "fail": f"vừa tuyển vì tiềm năng chưa đủ {cooldown} ngày"},
    ]
    has_signal = any(x["ok"] for x in signal)
    ready = has_signal and all(g["ok"] for g in guards) and company.active() and st.get("ceo_potential", "1") == "1"
    if not has_signal:
        verdict = (f"Chưa đủ tiềm năng để tăng người. Phòng đang có {per_day:.1f} khách/ngày, mục tiêu tối thiểu {kmin}; "
                   "tập trung để các nick hiện có đạt KPI trước.")
    elif not ready:
        miss = [g["fail"] for g in guards if not g["ok"]]
        verdict = "Tìm khách đang tốt nhưng chưa tuyển thêm vì " + ", ".join(miss) + "."
    else:
        verdict = (f"Facebook đang cho nhiều khách hơn sức các nick hiện có ({per_day:.1f} khách/ngày, "
                   f"{quota_pct}% chỉ tiêu). Thêm 1 nick để mở rộng sang nhóm mới.")
    return {"window_days": days, "leads": total, "per_day": round(per_day, 1), "per_nick_day": round(per_nick_day, 2),
            "quota_pct": quota_pct, "last7": last7, "prev7": prev7, "growth": growth, "free_groups": free_groups,
            "signal": signal, "guards": guards, "ready": ready, "verdict": verdict}


def check_potential():
    p = potential()
    db.set_setting("ceo_last_review", json.dumps({"date": db.today(), "ready": p["ready"], "verdict": p["verdict"]},
                                                 ensure_ascii=False))
    if p["ready"]:
        db.set_setting("ceo_last_potential_hire", db.today())
        tip = f" Còn {p['free_groups']} hội nhóm chưa có nick nào tham gia." if p["free_groups"] else \
            " Sếp nên bổ sung hội nhóm mới để nick mới không đăng trùng nhóm cũ."
        _hire_or_propose(p["verdict"] + tip, "potential")


def remind_waiting():
    for r in db.q("""SELECT * FROM sales WHERE hired_by='ceo' AND COALESCE(status,'active')='active'
                     AND login_status!='ok' AND COALESCE(is_sample,0)=0"""):
        last = (r.get("ceo_reminded_at") or r["created_at"] or db.now())[:10]
        if (date.today() - date.fromisoformat(last)).days >= REMIND_EVERY_DAYS:
            db.run("UPDATE sales SET ceo_reminded_at=? WHERE id=?", (db.now(), r["id"]))
            waited = (date.today() - date.fromisoformat(r["created_at"][:10])).days
            _tg(f"⏳ CEO {NAME} nhắc: {html.escape(r['name'])} đã chờ nick Facebook {waited} ngày. "
                "Sếp đăng nhập nick ở trang Nhân viên sale, hoặc hủy tuyển nếu chưa có nick.")


# ---------------------------------------------------------------- duyệt / từ chối, vòng lặp
def resolve(did: int, approve: bool, by: str = "boss") -> dict:
    d = db.one("SELECT * FROM ceo_decisions WHERE id=?", (did,))
    if not d or d["status"] != "proposed":
        raise ValueError("Đề xuất này đã được xử lý")
    if not approve:
        db.run("UPDATE ceo_decisions SET status='rejected', decided_at=? WHERE id=?", (db.now(), did))
        db.log("ceo", "Sếp không duyệt", d["title"])
        return {"ok": True, "status": "rejected"}
    if d["kind"] == "replace":
        new = replace(d["sale_id"], by="ceo")
        db.run("UPDATE ceo_decisions SET status='done', decided_at=?, title=? WHERE id=?",
               (db.now(), f"{new['name']} tiếp quản nick {new['fb_name'] or ''}".strip(), did))
        return {"ok": True, "status": "done", "sale": new["name"]}
    data = json.loads(d.get("data") or "{}")
    db.run("UPDATE ceo_decisions SET status='approved', decided_at=? WHERE id=?", (db.now(), did))
    new = hire(d["reason"], data.get("source", "boss"))
    if not new:
        raise ValueError("Không tuyển được (văn phòng đã đủ người hoặc công ty không hoạt động)")
    return {"ok": True, "status": "done", "sale": new["name"]}


def tick():
    """Gọi từ company.tick() sau khi đã kiểm tra luật giải thể."""
    import company
    if not company.active() or s().get("ceo_enabled", "1") != "1":
        return
    handle_fired()
    check_milestones()
    if s().get("ceo_last_daily") != db.today() and datetime.now().hour >= 8:
        db.set_setting("ceo_last_daily", db.today())
        if s().get("ceo_potential", "1") == "1":
            check_potential()
        remind_waiting()


def overview() -> dict:
    import company
    rev = company.finance()["revenue"] if company.status() != "setup" else 0
    ms = milestones()
    nxt = next((m for m in ms if not m["done"]), None)
    return {"name": NAME, "mode": mode(), "enabled": s().get("ceo_enabled", "1") == "1",
            "potential_on": s().get("ceo_potential", "1") == "1",
            "milestones": ms, "next_milestone": nxt, "revenue": rev, "headcount": headcount(),
            "potential": potential(), "last_review": json.loads(s().get("ceo_last_review") or "{}"),
            "decisions": db.q("SELECT * FROM ceo_decisions ORDER BY id DESC LIMIT 40"),
            "group_keywords": __import__("group_finder").today_keywords() if company.active() else [],
            "proposed": db.q("SELECT * FROM ceo_decisions WHERE status='proposed' ORDER BY id DESC")}


def brief_text() -> str:
    """Một câu chỉ đạo cho cuộc họp và báo cáo."""
    import company
    if not company.active():
        return ""
    o = overview()
    hc = o["headcount"]
    parts = [f"Đội sale có {hc['working']} nick đang chạy"]
    if hc["waiting_nick"]:
        parts.append(f"{hc['waiting_nick']} sale mới chờ sếp đăng nhập nick")
    if o["next_milestone"]:
        m = o["next_milestone"]
        parts.append(f"mốc tăng người tiếp theo {company.fmt_vnd(m['amount'])} (đang {company.fmt_vnd(o['revenue'])})")
    try:
        import group_finder
        kws = group_finder.today_keywords()
        if kws:
            parts.append("hôm nay tìm và ưu tiên đăng nhóm chủ đề: " + ", ".join(f"“{k}”" for k in kws))
    except Exception:
        pass
    return "; ".join(parts) + ". " + o["potential"]["verdict"]

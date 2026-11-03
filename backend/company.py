"""Vòng đời công ty: vốn, chi phí, doanh thu, đánh giá KPI tháng của sale, sa thải và giải thể.

Luật (sếp đặt):
1. Mỗi nhân viên sale giữ nick phải tìm được khách. Mỗi kỳ 30 ngày (tính từ ngày vào làm hoặc ngày thành lập),
   sale phải đạt chỉ tiêu khách có SĐT từ bài của nick mình. Không đạt -> bị sa thải.
   Chỉ tiêu tháng = tổng chỉ tiêu ngày của những ngày nick thực sự làm việc được (đăng nhập bình thường, không bị
   sếp tạm dừng). Nick nghỉ vì lỗi đăng nhập/checkpoint không bị tính, để không sa thải oan.
   Kỳ có dưới 15 ngày làm việc thì kéo dài tới khi đủ, rồi mới đánh giá.
2. Tất cả nhân viên sale đều bị sa thải -> công ty giải thể.
3. Sau 60 ngày kể từ khi thành lập mà chưa có khách hàng nào chốt đơn và chưa có doanh thu -> công ty giải thể.
Vốn ban đầu (mặc định 10.000.000đ) dùng để trả chi phí: AI (quy đổi từ USD) và các khoản sếp ghi thêm.
Hết vốn thì mọi việc tốn tiền (gọi AI) tạm dừng cho tới khi sếp bơm thêm vốn.
Đội lõi (Minh, Lan, Tuấn, Hà, Khoa) không bị sa thải theo KPI; chỉ giải tán khi công ty giải thể.
"""
import html
import json
import re
from datetime import date, datetime, timedelta

import db

MIN_WORK_DAYS = 15


def s() -> dict:
    return db.get_settings()


def status() -> str:
    return s().get("company_status") or "setup"


def active() -> bool:
    return status() == "active"


def founded() -> str | None:
    return s().get("company_founded_at") or None


def day_no() -> int:
    f = founded()
    return (date.today() - date.fromisoformat(f)).days + 1 if f else 0


def fmt_vnd(n) -> str:
    return f"{int(round(n or 0)):,}".replace(",", ".") + "đ"


def parse_vnd(text: str) -> int | None:
    """'2500000', '2.500.000', '2,5tr', '2tr5', '800k', '1 triệu 200' -> số đồng."""
    t = (text or "").lower().replace(" ", "").replace("đ", "").replace("vnd", "").replace("đồng", "")
    m = re.fullmatch(r"(\d+)(?:tr|triệu|trieu)(\d{1,3})?", t)
    if m:
        frac = m.group(2) or ""
        return int(m.group(1)) * 1_000_000 + (int(frac.ljust(3, "0")) * 1000 if frac else 0)
    m = re.fullmatch(r"(\d+(?:[.,]\d+)?)(tr|triệu|trieu|m)", t)
    if m:
        return int(float(m.group(1).replace(",", ".")) * 1_000_000)
    m = re.fullmatch(r"(\d+(?:[.,]\d+)?)(k|nghìn|nghin|ngàn)", t)
    if m:
        return int(float(m.group(1).replace(",", ".")) * 1000)
    digits = re.sub(r"[.,]", "", t)
    return int(digits) if digits.isdigit() and int(digits) > 0 else None


# ---------------------------------------------------------------- tiền
def finance() -> dict:
    f = founded()
    since = f or "0000"
    rate = float(s().get("usd_vnd") or 25800)
    ai_usd = db.one("SELECT COALESCE(SUM(cost_usd),0) c FROM usage WHERE created_at >= ?", (since,))["c"]
    other = db.one("SELECT COALESCE(SUM(amount),0) c FROM expenses WHERE date >= ?", (since,))["c"]
    revenue = db.one("SELECT COALESCE(SUM(amount),0) c FROM orders WHERE created_at >= ?", (since,))["c"]
    orders = db.one("SELECT COUNT(*) n FROM orders WHERE created_at >= ?", (since,))["n"]
    customers = db.one("SELECT COUNT(DISTINCT lead_id) n FROM orders WHERE created_at >= ?", (since,))["n"]
    capital = float(s().get("capital_vnd") or 0)
    spent = ai_usd * rate + other
    return {"capital": capital, "ai_vnd": round(ai_usd * rate), "ai_usd": round(ai_usd, 4), "other": other,
            "spent": round(spent), "left": round(capital - spent), "revenue": revenue, "orders": orders,
            "customers": customers, "profit": round(revenue - spent), "rate": rate}


def capital_left() -> float:
    return finance()["left"] if active() else 1


def add_order(lead_id: int, amount: int, note: str = "", via: str = "app") -> dict:
    import learning
    lead = db.one("SELECT * FROM leads WHERE id=?", (lead_id,))
    if not lead:
        raise ValueError("Không tìm thấy khách")
    oid = db.run("INSERT INTO orders(lead_id, amount, note, via, created_at) VALUES (?,?,?,?,?)",
                 (lead_id, int(amount), note[:200], via, db.now()))
    if lead["status"] != "ordered":
        db.run("UPDATE leads SET status='ordered', boss_status='won', updated_at=? WHERE id=?", (db.now(), lead_id))
        learning.on_lead_status(lead_id, "ordered")
    db.log("ha", "Có đơn hàng", f"{lead['name']}: {fmt_vnd(amount)}")
    first = db.one("SELECT COUNT(*) n FROM orders WHERE created_at >= ?", (founded() or "0000",))["n"] == 1
    if first and active():
        _tg(f"🎉 <b>Đơn hàng đầu tiên của công ty!</b> {html.escape(lead['name'])}: {fmt_vnd(amount)}. "
            "Điều kiện 'có khách hàng và doanh thu trong 60 ngày' đã đạt.")
    return db.one("SELECT * FROM orders WHERE id=?", (oid,))


# ---------------------------------------------------------------- KPI tháng của sale
def _share(n_active: int) -> int:
    kmin = max(1, int(s().get("kpi_min") or 5))
    return max(1, round(kmin / max(1, n_active)))


def record_work_day():
    """Mỗi ngày ghi nhận nick nào làm việc được, kèm chỉ tiêu ngày của nick đó."""
    if not active():
        return
    today = db.today()
    act = db.q("""SELECT id FROM sales WHERE COALESCE(status,'active')='active' AND COALESCE(is_sample,0)=0
                  AND auto_post=1 AND login_status='ok'""")
    share = _share(len(act))
    for r in act:
        db.run("INSERT OR IGNORE INTO sale_days(sale_id, date, target) VALUES (?,?,?)", (r["id"], today, share))


def sale_review(sale: dict) -> dict:
    """Tiến độ kỳ KPI hiện tại của một sale."""
    start = sale.get("kpi_period_start") or founded() or db.today()
    days = (date.today() - date.fromisoformat(start)).days + 1
    w = db.one("SELECT COUNT(*) n, COALESCE(SUM(target),0) t FROM sale_days WHERE sale_id=? AND date >= ?", (sale["id"], start))
    got = db.one("""SELECT COUNT(*) n FROM leads l JOIN posts p ON p.id=l.post_id WHERE p.sale_id=?
                    AND l.phone IS NOT NULL AND l.phone!='' AND COALESCE(l.phone_at, l.created_at) >= ?""", (sale["id"], start))["n"]
    target = int(w["t"])
    pace_target = target  # chỉ tiêu tính tới hôm nay
    full_target = round(target / max(1, w["n"]) * 30) if w["n"] else _share(1) * 30
    pct = round(100 * got / pace_target) if pace_target else 0
    if days >= 30 and w["n"] >= MIN_WORK_DAYS:
        risk = "pass" if got >= target else "fail"
    elif days >= 30:
        risk = "extend"
    elif not w["n"]:
        risk = "idle"
    elif days < 7:
        risk = "new"  # 7 ngày đầu kỳ: chưa đủ dữ liệu để cảnh báo
    else:
        risk = "safe" if pct >= 90 else "warn" if pct >= 60 else "danger"
    return {"period_start": start, "day": days, "work_days": w["n"], "target_so_far": pace_target,
            "target_month": full_target, "leads_phone": got, "pct": pct, "risk": risk,
            "days_left": max(0, 30 - days)}


def fire(sale_id: int, reason: str):
    sale = db.one("SELECT * FROM sales WHERE id=?", (sale_id,))
    if not sale or sale.get("status") == "fired":
        return
    db.run("UPDATE sales SET status='fired', auto_post=0, fired_at=?, fire_reason=?, fired_gen=? WHERE id=?",
           (db.now(), reason, s().get("company_gen") or "0", sale_id))
    db.run("UPDATE posts SET status='approved', sale_id=NULL, scheduled_for=NULL WHERE sale_id=? AND status='scheduled'", (sale_id,))
    db.run("UPDATE bumps SET status='skipped', error='Sale đã nghỉ việc' WHERE sale_id=? AND status='scheduled'", (sale_id,))
    db.log("minh", "Sa thải", f"{sale['name']} (nick {sale['fb_name'] or sale['name']}): {reason}")
    _tg(f"🚪 <b>Sa thải {html.escape(sale['name'])}</b> (nick {html.escape(sale['fb_name'] or sale['name'])})\n{html.escape(reason)}\n"
        "Nick vẫn giữ nguyên phiên đăng nhập. Sếp có thể tuyển người thay để dùng tiếp nick này.")


def review_sales():
    if not active():
        return
    for sale in db.q("SELECT * FROM sales WHERE COALESCE(status,'active')='active' AND COALESCE(is_sample,0)=0"):
        r = sale_review(sale)
        if r["risk"] == "fail":
            fire(sale["id"], f"Kỳ {r['period_start']} → hôm nay: {r['leads_phone']}/{r['target_so_far']} khách có SĐT "
                             f"({r['work_days']} ngày làm việc), không đạt KPI tháng.")
        elif r["risk"] == "pass":
            import learning
            db.run("UPDATE sales SET kpi_period_start=?, kpi_warned=NULL WHERE id=?", (db.today(), sale["id"]))
            learning.award(f"sale-{sale['id']}", 100, "Đạt KPI tháng")
            db.log(f"sale-{sale['id']}", "Đạt KPI tháng", f"{r['leads_phone']}/{r['target_so_far']} khách có SĐT, bắt đầu kỳ mới")
            _tg(f"🏅 <b>{html.escape(sale['name'])} đạt KPI tháng</b>: {r['leads_phone']}/{r['target_so_far']} khách có SĐT. Bắt đầu kỳ đánh giá mới.")
        elif r["day"] >= 20 and r["risk"] in ("warn", "danger") and sale.get("kpi_warned") != r["period_start"]:
            db.run("UPDATE sales SET kpi_warned=? WHERE id=?", (r["period_start"], sale["id"]))
            msg = (f"{sale['name']}: {r['leads_phone']}/{r['target_so_far']} khách có SĐT ({r['pct']}%), "
                   f"còn {r['days_left']} ngày trước kỳ đánh giá.")
            db.log("minh", "Cảnh báo KPI tháng", msg)
            _tg(f"⚠️ <b>Nguy cơ sa thải</b>\n{html.escape(msg)}")


# ---------------------------------------------------------------- giải thể
def dissolve(reason: str):
    if status() == "dissolved":
        return
    fin = finance()
    db.set_setting("company_status", "dissolved")
    db.set_setting("dissolved_at", db.now())
    db.set_setting("dissolved_reason", reason)
    db.run("UPDATE sales SET auto_post=0")
    db.run("UPDATE posts SET status='approved', sale_id=NULL, scheduled_for=NULL WHERE status='scheduled'")
    db.run("UPDATE bumps SET status='skipped', error='Công ty đã giải thể' WHERE status='scheduled'")
    db.log("minh", "Giải thể công ty", reason)
    _tg(f"🏁 <b>Công ty đã giải thể</b> sau {day_no()} ngày.\nLý do: {reason}\n"
        f"Vốn: {fmt_vnd(fin['capital'])} · đã chi {fmt_vnd(fin['spent'])} · doanh thu {fmt_vnd(fin['revenue'])} "
        f"({fin['orders']} đơn).\nMọi hoạt động tự động đã dừng. Sếp có thể thành lập lại trong phần mềm.")


def check_dissolution():
    if not active():
        return
    # chỉ tính người bị sa thải từ lần thành lập này (thành lập lại thì không bị giải thể ngay vì sale cũ đã nghỉ)
    fired_now = db.one("""SELECT COUNT(*) n FROM sales WHERE COALESCE(is_sample,0)=0 AND status='fired'
                          AND fired_gen=?""", (s().get("company_gen") or "0",))["n"]
    working = db.one("SELECT COUNT(*) n FROM sales WHERE COALESCE(is_sample,0)=0 AND COALESCE(status,'active')!='fired'")["n"]
    if fired_now and not working:
        return dissolve("Toàn bộ nhân viên sale đã bị sa thải vì không đạt KPI.")
    trial = int(s().get("trial_days") or 60)
    fin = finance()
    d = day_no()
    if d > trial and fin["orders"] == 0 and fin["revenue"] == 0:
        return dissolve(f"Sau {trial} ngày chưa có khách hàng chốt đơn và chưa có doanh thu.")
    if fin["orders"] == 0:
        for mark in (trial // 2, trial - 15, trial - 5):
            if d >= mark and s().get("trial_warned") != str(mark):
                db.set_setting("trial_warned", str(mark))
                left = trial - d + 1
                db.log("minh", "Cảnh báo giải thể", f"Còn {left} ngày để có đơn hàng đầu tiên")
                _tg(f"⏳ <b>Còn {left} ngày</b> để có khách hàng chốt đơn đầu tiên, nếu không công ty sẽ giải thể.")
                break
    if fin["capital"] and fin["left"] <= fin["capital"] * 0.2 and s().get("capital_warned") != "20" and fin["left"] > 0:
        db.set_setting("capital_warned", "20")
        _tg(f"💸 Vốn còn {fmt_vnd(fin['left'])} (dưới 20%). Hết vốn thì các việc tốn tiền AI sẽ tạm dừng.")
    if fin["capital"] and fin["left"] <= 0 and s().get("capital_warned") != "0":
        db.set_setting("capital_warned", "0")
        db.log("minh", "Hết vốn", "Tạm dừng mọi việc gọi AI cho tới khi bơm thêm vốn")
        _tg("🛑 <b>Hết vốn.</b> Các việc tốn tiền AI đã tạm dừng. Bơm thêm vốn trong trang Công ty để tiếp tục.")


def tick() -> str:
    """Gọi từ lịch tự động. Trả về trạng thái công ty sau khi kiểm tra."""
    if active():
        record_work_day()
        review_sales()
        check_dissolution()
    return status()


# ---------------------------------------------------------------- thành lập, bơm vốn
def found(capital: int, rate: float | None = None):
    db.set_setting("company_status", "active")
    db.set_setting("company_founded_at", db.today())
    db.set_setting("company_founded_ts", db.now())
    db.set_setting("company_gen", str(int(s().get("company_gen") or 0) + 1))  # lần thành lập thứ mấy
    db.set_setting("capital_vnd", str(int(capital)))
    if rate:
        db.set_setting("usd_vnd", str(rate))
    for k in ("dissolved_at", "dissolved_reason", "trial_warned", "capital_warned"):
        db.set_setting(k, "")
    db.run("UPDATE sales SET kpi_period_start=?, kpi_warned=NULL WHERE COALESCE(status,'active')='active'", (db.today(),))
    db.run("UPDATE sales SET auto_post=1 WHERE COALESCE(status,'active')='active' AND login_status='ok'")
    db.log("minh", "Thành lập công ty", f"Vốn {fmt_vnd(capital)}. Luật KPI và thời hạn 60 ngày bắt đầu tính từ hôm nay.")
    _tg(f"🏢 <b>Công ty chính thức hoạt động</b> với vốn {fmt_vnd(capital)}.\n"
        "Luật: sale không đạt KPI tháng bị sa thải; sau 60 ngày chưa có đơn hàng thì giải thể.")


def add_capital(amount: int, note: str = ""):
    cur = float(s().get("capital_vnd") or 0)
    db.set_setting("capital_vnd", str(int(cur + amount)))
    db.set_setting("capital_warned", "")
    db.log("minh", "Bơm vốn", f"+{fmt_vnd(amount)} {note}".strip())


def overview() -> dict:
    sales = []
    for r in db.q("SELECT * FROM sales WHERE COALESCE(is_sample,0)=0 ORDER BY id"):
        item = {k: r[k] for k in ("id", "name", "fb_name", "login_status", "auto_post", "status", "fired_at", "fire_reason")}
        item["status"] = r.get("status") or "active"
        if item["status"] == "active":
            item["review"] = sale_review(r)
        sales.append(item)
    st = s()
    return {"status": status(), "founded_at": founded(), "day": day_no(), "trial_days": int(st.get("trial_days") or 60),
            "dissolved_at": st.get("dissolved_at"), "dissolved_reason": st.get("dissolved_reason"),
            "finance": finance(), "sales": sales,
            "expenses": db.q("SELECT * FROM expenses ORDER BY date DESC, id DESC LIMIT 50"),
            "orders": db.q("""SELECT o.*, l.name lead_name, l.phone FROM orders o LEFT JOIN leads l ON l.id=o.lead_id
                              ORDER BY o.id DESC LIMIT 50""")}


def brief() -> dict | None:
    """Tóm tắt ngắn cho cuộc họp, báo cáo Telegram và nhân viên AI."""
    if status() == "setup":
        return None
    fin = finance()
    at_risk = [r for r in overview()["sales"] if r["status"] == "active" and r["review"]["risk"] in ("warn", "danger")]
    return {"status": status(), "day": day_no(), "trial_days": int(s().get("trial_days") or 60),
            "capital_left": fin["left"], "capital": fin["capital"], "revenue": fin["revenue"], "orders": fin["orders"],
            "at_risk": [f"{r['name']} ({r['review']['leads_phone']}/{r['review']['target_so_far']})" for r in at_risk]}


def brief_text() -> str:
    b = brief()
    if not b:
        return ""
    if b["status"] == "dissolved":
        return "🏁 Công ty đã giải thể."
    line = (f"🏢 Ngày {b['day']}/{b['trial_days']} · vốn còn {fmt_vnd(b['capital_left'])} · "
            f"doanh thu {fmt_vnd(b['revenue'])} ({b['orders']} đơn)")
    if b["orders"] == 0:
        line += f"\n⏳ Còn {max(0, b['trial_days'] - b['day'] + 1)} ngày để có đơn đầu tiên, nếu không sẽ giải thể."
    if b["at_risk"]:
        line += "\n⚠️ Sale có nguy cơ bị sa thải: " + ", ".join(b["at_risk"])
    return line


def _tg(text: str):
    try:
        import telegram_bot
        if telegram_bot.configured():
            telegram_bot.send(text)
    except Exception as e:
        print("[company]", e)

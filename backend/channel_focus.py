"""Dồn sức vào kênh ra đơn: CEO xem phễu theo kênh mỗi tuần, tạm dừng kênh ra số mà không ra đơn, tăng sức cho kênh ra đơn.

Chỉ quyết khi đủ dữ liệu thật: kênh có từ `focus_min_phones` SĐT và sếp đã gọi từ `focus_min_called` khách trong
`focus_days` ngày. Kênh có SĐT mà sếp chưa gọi đủ thì CEO nhắc sếp gọi, không kết luận.
- Ra đơn (≥1 đơn): tăng sức trong giới hạn an toàn (đọc thêm nhóm, xem thêm trang mỗi lượt).
- Không ra đơn sau đủ số cuộc gọi: tạm dừng 30 ngày rồi tự chạy lại để thử lại (thị trường đổi, từ khóa đổi).
- Bình luận dưới bài mình (đăng bài): không bao giờ tự dừng, chỉ báo để sếp cân nhắc.
Theo quyền của CEO: "CEO tự quyết" thì làm luôn và báo; "Chờ sếp duyệt" thì thành đề xuất có nút Duyệt / Không.
"""
import json
from datetime import timedelta

import db

# kênh -> (cài đặt bật/tắt, cách tăng sức: (cài đặt, bước, trần))
CONTROL = {
    "demand": ("prospect_groups", ("prospect_groups_per_run", 1, 6)),
    "ads": ("prospect_ads", ("prospect_fb_keywords", 1, 4)),
    "pages": ("prospect_pages", ("prospect_inspect_per_run", 3, 20)),
}
PAUSE_DAYS = 30


def s() -> dict:
    return db.get_settings()


def enabled() -> bool:
    return s().get("focus_enabled", "1") == "1"


def _i(k: str, d: int) -> int:
    try:
        return int(float(s().get(k) or d))
    except ValueError:
        return d


def paused() -> dict:
    try:
        return json.loads(s().get("focus_paused") or "{}")
    except Exception:
        return {}


def _resumed_recently(key: str, days: int) -> bool:
    """Kênh vừa chạy lại: chờ đủ dữ liệu mới, không dừng lại ngay vì số liệu cũ."""
    try:
        at = json.loads(s().get("focus_resumed") or "{}").get(key)
    except Exception:
        return False
    return bool(at) and at > (db.clock() - timedelta(days=days)).strftime("%Y-%m-%d")


def review() -> dict:
    """Đánh giá từng kênh (không đổi gì)."""
    import funnel
    days = _i("focus_days", 14)
    r = funnel.report(days)
    mp, mc = _i("focus_min_phones", 8), _i("focus_min_called", 5)
    ps = paused()
    out = []
    for c in r["channels"]:
        k = c["key"]
        v = {"key": k, "label": c["label"], "phones": c["phones"], "called": c["called"], "won": c["won"],
             "revenue": c["revenue"], "can_control": k in CONTROL, "paused_until": ps.get(k)}
        if c["won"] > 0:
            v.update(verdict="good", text=f"Ra {c['won']} đơn từ {c['phones']} SĐT: dồn thêm sức")
        elif c["phones"] < mp:
            v.update(verdict="wait", text=f"Mới {c['phones']}/{mp} SĐT, chưa đủ để kết luận")
        elif c["called"] < mc:
            v.update(verdict="call", text=f"Có {c['phones']} SĐT nhưng sếp mới gọi {c['called']}/{mc}: cần gọi thêm mới biết kênh này ra đơn không")
        else:
            v.update(verdict="weak", text=f"{c['phones']} SĐT, sếp đã gọi {c['called']}, chưa có đơn nào")
        out.append(v)
    return {"days": days, "min_phones": mp, "min_called": mc, "channels": out, "paused": ps}


def plan(rv: dict | None = None) -> list[dict]:
    """Việc CEO nên làm từ kết quả đánh giá."""
    rv = rv or review()
    acts = []
    for c in rv["channels"]:
        k = c["key"]
        if k not in CONTROL or c["paused_until"] or _resumed_recently(k, rv["days"]):
            continue
        on_key, (boost_key, step, cap) = CONTROL[k]
        if c["verdict"] == "weak":
            acts.append({"op": "pause", "key": k, "label": c["label"], "why": c["text"]})
        elif c["verdict"] == "good" and _i(boost_key, 0) < cap:
            acts.append({"op": "boost", "key": k, "label": c["label"], "why": c["text"], "set": boost_key,
                         "value": min(cap, _i(boost_key, 0) + step)})
    return acts


def apply(acts: list[dict], by: str = "ceo") -> list[str]:
    done = []
    ps = paused()
    for a in acts:
        k = a["key"]
        if k not in CONTROL:
            continue
        if a["op"] == "pause":
            db.set_setting(CONTROL[k][0], "0")
            ps[k] = (db.clock() + timedelta(days=PAUSE_DAYS)).strftime("%Y-%m-%d")
            done.append(f"Tạm dừng “{a['label']}” {PAUSE_DAYS} ngày ({a['why']})")
        elif a["op"] == "boost":
            db.set_setting(CONTROL[k][0], "1")
            db.set_setting(a["set"], str(a["value"]))
            done.append(f"Dồn sức cho “{a['label']}” ({a['why']})")
        elif a["op"] == "resume":
            db.set_setting(CONTROL[k][0], "1")
            ps.pop(k, None)
            try:
                rs = json.loads(s().get("focus_resumed") or "{}")
            except Exception:
                rs = {}
            rs[k] = db.today()
            db.set_setting("focus_resumed", json.dumps(rs))
            done.append(f"Chạy lại “{a['label']}”" + (f" ({a['why']})" if a.get("why") else ""))
    db.set_setting("focus_paused", json.dumps(ps, ensure_ascii=False))
    for d in done:
        db.log("ceo", "Dồn sức vào kênh ra đơn", d)
    return done


def resume(key: str, why: str = "sếp cho chạy lại") -> list[str]:
    import funnel
    return apply([{"op": "resume", "key": key, "label": funnel.CHANNELS.get(key, key), "why": why}])


def _report_text(rv: dict, done: list[str], proposed: bool) -> str:
    icon = {"good": "✅", "weak": "⛔", "call": "📞", "wait": "⏳"}
    lines = [f"📊 <b>CEO xem kênh nào ra đơn ({rv['days']} ngày)</b>"]
    lines += [f"{icon.get(c['verdict'], '•')} {c['label']}: {c['text']}" for c in rv["channels"]]
    if done:
        lines.append(("\n<b>CEO đề xuất (chờ sếp duyệt):</b>\n" if proposed else "\n<b>CEO đã làm:</b>\n") + "\n".join(f"• {d}" for d in done))
    cm = next((c for c in rv["channels"] if c["key"] == "comment" and c["verdict"] == "weak"), None)
    if cm:
        lines.append("\n⚠ Bài đăng nhóm ra SĐT nhưng chưa ra đơn: sếp xem lại nội dung bài và nhóm đăng (CEO không tự dừng đăng bài).")
    if any(c["verdict"] == "call" for c in rv["channels"]):
        lines.append("\n📞 Sếp gọi thêm khách ở các kênh trên rồi bấm Đã gọi / Chốt đơn / Không mua để CEO kết luận được.")
    return "\n".join(lines)


def run(force: bool = False, notify: bool = True) -> dict:
    """CEO xem lại kênh: tự chạy lại kênh hết hạn dừng, rồi dừng / tăng sức theo quyền của CEO."""
    import ceo
    out = {"done": [], "proposed": None}
    today = db.today()
    due = [k for k, until in paused().items() if until <= today]
    for k in due:
        out["done"] += resume(k, f"hết {PAUSE_DAYS} ngày tạm dừng, thử lại")
    rv = review()
    acts = plan(rv)
    if acts and ceo.mode() == "approve":
        did = ceo._decide("channel", f"Đề xuất dồn sức vào kênh ra đơn ({len(acts)} việc)",
                          "; ".join(f"{'Tạm dừng' if a['op'] == 'pause' else 'Dồn sức cho'} {a['label']}: {a['why']}" for a in acts),
                          status="proposed", data={"actions": acts})
        out["proposed"] = did
        text = [f"{'Tạm dừng' if a['op'] == 'pause' else 'Dồn sức cho'} “{a['label']}”" for a in acts]
        if notify:
            ceo._tg(_report_text(rv, text, True), ceo._buttons(did))
    else:
        out["done"] += apply(acts)
        if notify and (out["done"] or force):
            ceo._tg(_report_text(rv, out["done"], False))
    db.set_setting("focus_last", today)
    out["review"] = rv
    return out


def tick(now):
    """Mỗi tuần (mặc định thứ Hai, sau 08:00) CEO xem lại kênh."""
    if not enabled() or s().get("focus_last") == db.today():
        return
    wd = int(s().get("focus_weekday") or 1)  # 1 = thứ Hai
    last = s().get("focus_last") or ""
    week_ago = (db.clock() - timedelta(days=7)).strftime("%Y-%m-%d")
    if (now.isoweekday() == wd or (last and last <= week_ago)) and now.hour >= 8:
        try:
            run()
        except Exception as e:
            import errors
            errors.report_exc("ceo", "CEO xem lại kênh ra đơn bị lỗi", e, screen="kpi")


def overview() -> dict:
    rv = review()
    import ceo
    return {**rv, "plan": plan(rv), "enabled": enabled(), "mode": ceo.mode(), "last": s().get("focus_last") or "",
            "proposed": db.q("SELECT * FROM ceo_decisions WHERE kind='channel' AND status='proposed' ORDER BY id DESC LIMIT 3")}

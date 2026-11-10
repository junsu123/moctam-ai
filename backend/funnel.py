"""Đo tới khách mua: phễu khách theo kênh và lý do khách không mua.

Mỗi kênh: khách → có SĐT → sếp đã gọi → chốt đơn → doanh thu; chi phí AI mỗi SĐT và mỗi đơn.
Khách không mua phải có lý do (Telegram hỏi ngay sau nút "Không mua", trang Khách hàng bắt chọn). Lý do được đưa vào lời dặn
của Mai, Lan, Hà, CEO, Minh để đội biết vì sao khách không mua, theo kênh nào.
"""
from datetime import timedelta

import db

LOST_REASONS = {
    "no_answer": "Không nghe máy / sai số",
    "wrong_fit": "Sai tệp (không bán online, chỉ mua lẻ)",
    "has_supplier": "Đã có nguồn hàng",
    "moq": "Chê số lượng nhập tối thiểu",
    "price": "Chê giá",
    "product": "Không hợp sản phẩm",
    "later": "Hẹn để sau",
    "other": "Lý do khác",
}

# Lý do -> ai cần làm gì khác đi (chỉ đổi cách làm, không đổi quy định giá / luật của sếp)
ADVICE = {
    "no_answer": {"mai": "ưu tiên SĐT kinh doanh ghi rõ trên trang (hotline, Zalo), không lấy số lẫn trong bình luận cũ",
                  "ha": "kịch bản nên nhắn Zalo trước rồi mới gọi"},
    "wrong_fit": {"mai": "chặt hơn: phải có bằng chứng đang bán online (chốt đơn, ship, livestream), loại người chỉ mua lẻ",
                  "lan": "nói rõ bài dành cho người bán hàng online nhập về bán lại, không bán lẻ"},
    "has_supplier": {"lan": "nói điểm khác của xưởng so với nguồn họ đang có (tận gốc, gia công nhãn riêng, mẫu thử) — chỉ dùng thông tin có thật",
                     "ha": "hỏi họ đang nhập ở đâu, đề nghị gửi mẫu để so sánh thay vì chào ngay"},
    "moq": {"lan": "ghi rõ số lượng nhập tối thiểu đúng theo thông tin sản phẩm để người không đủ sức nhập khỏi hỏi",
            "ha": "hỏi trước họ bán được bao nhiêu mỗi tháng, gợi ý sản phẩm có mức nhập thấp nhất",
            "mai": "ưu tiên shop đã có lượng bán đều (nhiều bài chốt đơn, livestream thường xuyên)"},
    "price": {"ha": "nói về lợi nhuận và chất lượng trước khi báo giá; giá do sếp báo trực tiếp",
              "lan": "nhấn giá tận xưởng, không qua trung gian (không ghi số giá)"},
    "product": {"mai": "khớp ngành hàng kỹ hơn với sản phẩm của xưởng",
                "lan": "bài nói rõ xưởng làm những dòng sản phẩm nào để người không hợp khỏi hỏi"},
    "later": {"ha": "đặt lịch bám lại sau 3–7 ngày, gửi mẫu hoặc catalog"},
}
WHO = {"mai": "Mai", "lan": "Lan", "ha": "Hà"}

CHANNELS = {
    "comment": "Bình luận dưới bài mình đăng",
    "fanpage": "Bình luận Fanpage",
    "demand": "Người hỏi nguồn trong nhóm (Mai đọc)",
    "ads": "Trang chạy quảng cáo (Mai quét)",
    "pages": "Trang, shop livestream (Mai tìm)",
    "link": "Link sếp dán cho Mai",
    "manual": "Sếp nhập tay",
}
_CH_SQL = """CASE WHEN l.origin='comment' THEN 'comment' WHEN l.origin='fanpage' THEN 'fanpage'
  WHEN l.origin='prospect' THEN CASE WHEN pr.direction=6 THEN 'demand' WHEN pr.direction=5 THEN 'ads'
       WHEN pr.direction BETWEEN 1 AND 4 THEN 'pages' ELSE 'link' END
  ELSE 'manual' END"""
_BASE = f"""FROM leads l LEFT JOIN prospects pr ON pr.lead_id=l.id
  WHERE COALESCE(l.is_sample,0)=0 AND COALESCE(l.status,'')!='junk' AND l.created_at>=?"""
CALLED = "(COALESCE(l.boss_status,'') IN ('called','won','lost') OR l.status IN ('contacted','sample','ordered','lost') OR l.last_contact_at IS NOT NULL)"


def _since(days: int) -> str:
    return (db.clock() - timedelta(days=days)).strftime("%Y-%m-%d")


def mark_lost(lead_id: int, reason: str = "", note: str = "", via: str = "web") -> dict | None:
    """Ghi khách không mua kèm lý do (lý do rỗng: chờ sếp chọn)."""
    lead = db.one("SELECT * FROM leads WHERE id=?", (lead_id,))
    if not lead:
        return None
    reason = reason if reason in LOST_REASONS else ("" if not reason else "other")
    was = lead["status"]
    db.run("""UPDATE leads SET status='lost', boss_status='lost', lost_reason=COALESCE(NULLIF(?,''), lost_reason),
              lost_note=COALESCE(NULLIF(?,''), lost_note), lost_at=COALESCE(lost_at, ?), updated_at=? WHERE id=?""",
           (reason, (note or "").strip()[:200], db.now(), db.now(), lead_id))
    if was != "lost":
        import learning
        learning.on_lead_status(lead_id, "lost")
    if reason:
        db.log("minh", "Khách không mua", f"{lead['name']}: {LOST_REASONS[reason]}" + (f" — {note.strip()[:80]}" if note.strip() else ""))
    return db.one("SELECT * FROM leads WHERE id=?", (lead_id,))


def report(days: int = 30) -> dict:
    since = _since(days)
    rows = db.q(f"""SELECT {_CH_SQL} ch, COUNT(*) leads,
                       SUM(COALESCE(l.phone,'')!='') phones,
                       SUM(COALESCE(l.phone,'')!='' AND {CALLED}) called,
                       SUM(l.status='ordered') won,
                       SUM(l.status='lost') lost,
                       SUM(l.status='lost' AND COALESCE(l.lost_reason,'')='') lost_noreason
                   {_BASE} GROUP BY ch""", (since,))
    rev = {r["ch"]: r["v"] for r in db.q(f"""SELECT {_CH_SQL} ch, SUM(o.amount) v FROM orders o JOIN leads l ON l.id=o.lead_id
                                             LEFT JOIN prospects pr ON pr.lead_id=l.id WHERE o.created_at>=? GROUP BY ch""", (since,))}
    by = {r["ch"]: r for r in rows}
    chans = []
    for k, label in CHANNELS.items():
        r = by.get(k) or {}
        leads, phones, called, won = r.get("leads") or 0, r.get("phones") or 0, r.get("called") or 0, r.get("won") or 0
        if not leads and not rev.get(k):
            continue
        chans.append({"key": k, "label": label, "leads": leads, "phones": phones, "called": called, "won": won,
                      "lost": r.get("lost") or 0, "lost_noreason": r.get("lost_noreason") or 0, "revenue": int(rev.get(k) or 0),
                      "call_rate": round(called / phones * 100) if phones else None,
                      "win_rate": round(won / called * 100) if called else None})
    reasons = db.q(f"""SELECT {_CH_SQL} ch, l.lost_reason reason, COUNT(*) n {_BASE} AND l.status='lost'
                       AND COALESCE(l.lost_reason,'')!='' GROUP BY ch, reason ORDER BY n DESC""", (since,))
    tot_r = {}
    for r in reasons:
        tot_r[r["reason"]] = tot_r.get(r["reason"], 0) + r["n"]
    usd = db.one("SELECT COALESCE(SUM(cost_usd),0) c FROM usage WHERE created_at>=?", (since,))["c"]
    rate = float(db.get_settings().get("usd_vnd") or 25800)
    ai = round(usd * rate)
    T = {k: sum(c[k] for c in chans) for k in ("leads", "phones", "called", "won", "lost", "lost_noreason", "revenue")}
    return {"days": days, "channels": chans, "total": T,
            "reasons": [{"key": k, "label": LOST_REASONS.get(k, k), "n": n,
                         "by_channel": {r["ch"]: r["n"] for r in reasons if r["reason"] == k}}
                        for k, n in sorted(tot_r.items(), key=lambda x: -x[1])],
            "ai_vnd": ai, "per_phone": round(ai / T["phones"]) if T["phones"] else None,
            "per_order": round(ai / T["won"]) if T["won"] else None,
            "channel_names": CHANNELS, "reason_names": LOST_REASONS}


def prompt_block(agent_id: str) -> str:
    """Kết quả gọi khách thật đưa vào lời dặn (chỉ khi đã có từ 3 khách không mua có lý do trong 60 ngày)."""
    if agent_id not in ("mai", "lan", "ha", "ceo", "minh"):
        return ""
    try:
        r = report(60)
    except Exception as e:
        print("[funnel]", e)
        return ""
    rs = [x for x in r["reasons"] if x["n"] > 0]
    if sum(x["n"] for x in rs) < 3:
        return ""
    T = r["total"]
    lines = [f"\n\nKẾT QUẢ SẾP GỌI KHÁCH THẬT (60 ngày): {T['phones']} khách có SĐT, sếp đã gọi {T['called']}, "
             f"chốt {T['won']}, không mua {T['lost']}. Lý do không mua:"]
    for x in rs[:4]:
        ch = max(x["by_channel"].items(), key=lambda kv: kv[1])[0] if x["by_channel"] else ""
        lines.append(f"- {x['label']}: {x['n']} khách" + (f" (nhiều nhất ở kênh {CHANNELS.get(ch, ch)})" if ch else ""))
    tips = []
    for x in rs[:3]:
        adv = ADVICE.get(x["key"], {})
        if agent_id in adv:
            tips.append(f"- Vì “{x['label']}”: {adv[agent_id]}")
        elif agent_id in ("ceo", "minh"):
            tips += [f"- Vì “{x['label']}”, {WHO[a]}: {t}" for a, t in adv.items()][:2]
    if tips:
        lines.append("Việc của bạn để bớt khách không mua (chỉ dùng thông tin có thật, không đổi quy định giá):")
        lines += tips
    return "\n".join(lines)


def text_summary(days: int = 7) -> str:
    """Một đoạn ngắn cho báo cáo tối trên Telegram."""
    r = report(days)
    T = r["total"]
    if not T["phones"]:
        return ""
    best = max(r["channels"], key=lambda c: (c["won"], c["phones"]), default=None)
    out = (f"Phễu {days} ngày: {T['phones']} SĐT → sếp gọi {T['called']} → chốt {T['won']}"
           + (f" · chi phí AI {r['per_order']:,}đ/đơn".replace(",", ".") if r["per_order"] else "")
           + (f"\nKênh ra đơn nhiều nhất: {best['label']} ({best['won']} đơn / {best['phones']} SĐT)" if best and best["won"] else ""))
    if r["reasons"]:
        out += "\nKhách không mua vì: " + ", ".join(f"{x['label'].split(' (')[0].lower()} {x['n']}" for x in r["reasons"][:3])
    if T["lost_noreason"]:
        out += f"\n⚠ {T['lost_noreason']} khách không mua chưa ghi lý do"
    return out

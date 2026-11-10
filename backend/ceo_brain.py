"""Bộ não CEO Đức: nhớ hội thoại, đọc số liệu thật trước khi trả lời, báo cáo tuần như giám đốc,
học từ khách đã chốt để tìm khách linh hoạt hơn, và theo dõi kênh Fanpage (kênh tự động hóa được Facebook cho phép).

Ranh giới (sếp đã chốt): không né phát hiện của Facebook, không mẹo né lọc spam, không tự nhắn tin / kết bạn.
"""
import json
import re
from datetime import timedelta

import db


def s() -> dict:
    return db.get_settings()


def _since(days: int) -> str:
    return (db.clock() - timedelta(days=days)).strftime("%Y-%m-%d")


# ---------------------------------------------------------------- 1. trí nhớ hội thoại
def recent_chat(n: int = 10) -> list[dict]:
    """Các tin gần nhất giữa sếp và CEO (trong 3 ngày) để hiểu “làm tiếp”, “cái đó”, câu trả lời cho câu CEO vừa hỏi."""
    rows = db.q("SELECT role, text, actions, created_at FROM ceo_messages WHERE created_at>=? ORDER BY id DESC LIMIT ?",
                (_since(3), n))[::-1]
    out = []
    for r in rows:
        t = re.sub(r"\s+", " ", r["text"] or "")[:400]
        out.append({"ai": "sep" if r["role"] == "boss" else "ceo", "luc": r["created_at"][5:16], "noi": t})
    return out


def pending_question() -> dict | None:
    """Câu CEO vừa hỏi lại sếp: tin cuối của CEO có câu hỏi, sau đó sếp mới nhắn đúng 1 tin (chính là câu trả lời)."""
    rows = db.q("SELECT id, role, actions FROM ceo_messages ORDER BY id DESC LIMIT 2")
    if not rows:
        return None
    if rows[0]["role"] == "ceo":
        r = rows[0]
    elif len(rows) > 1 and rows[1]["role"] == "ceo":
        r = rows[1]
    else:
        return None
    for a in json.loads(r["actions"] or "[]"):
        if isinstance(a, dict) and a.get("type") == "clarify":
            return {"msg_id": r["id"], **a}
    return None


# ---------------------------------------------------------------- 2. số liệu điều hành
def data_brief(days: int = 14) -> dict:
    """Số liệu thật CEO đọc trước khi trả lời: KPI, phễu theo kênh, lý do không mua, kênh dừng/dồn sức, chi phí, việc đang dở."""
    out = {}
    try:
        import kpi
        st = kpi.day_stats()
        out["kpi_hom_nay"] = {"sdt_moi": st.get("leads_phone"), "toi_thieu": st.get("target_min"), "vuot": st.get("target_max"),
                              "bai_da_dang": st.get("posts")}
    except Exception:
        pass
    try:
        import funnel
        r = funnel.report(days)
        out["pheu"] = {"so_ngay": days, "tong": {k: r["total"][k] for k in ("phones", "called", "won", "lost", "revenue")},
                       "theo_kenh": [{"kenh": c["label"], "sdt": c["phones"], "da_goi": c["called"], "chot": c["won"]} for c in r["channels"]],
                       "ly_do_khong_mua": [{"ly_do": x["label"], "so": x["n"]} for x in r["reasons"][:4]],
                       "chi_phi_ai_moi_don": r["per_order"], "chi_phi_ai_moi_sdt": r["per_phone"]}
    except Exception as e:
        print("[ceo_brain] funnel", e)
    try:
        import channel_focus
        rv = channel_focus.review()
        out["kenh_ket_luan"] = [{"kenh": c["label"], "ket_luan": c["text"], "dang_dung": bool(c["paused_until"])} for c in rv["channels"]]
    except Exception:
        pass
    try:
        import llm
        out["chi_phi_ai_thang_usd"] = round(llm.month_spent(), 2)
    except Exception:
        pass
    out["khach_cho_sep_goi"] = db.one("""SELECT COUNT(*) n FROM leads WHERE escalated_at IS NOT NULL AND COALESCE(boss_status,'') IN ('','remind')
                                         AND status NOT IN ('ordered','lost','junk') AND COALESCE(is_sample,0)=0""")["n"]
    out["bai_cho_duyet"] = db.one("SELECT COUNT(*) n FROM posts WHERE status='draft'")["n"]
    out["nick_loi"] = db.one("SELECT COUNT(*) n FROM fb_accounts WHERE COALESCE(login_status,'')!='ok'")["n"]
    tw = trial_words()
    if tw:
        out["tu_khoa_dang_thu"] = tw
    return out


# ---------------------------------------------------------------- 3. học từ khách đã chốt -> tìm khách linh hoạt
def won_profile(days: int = 90) -> dict:
    """Chân dung khách mua thật (và khách sếp đã gọi mà quan tâm): ngành, kiểu người bán, câu họ viết, từ khóa / nhóm đã ra họ."""
    rows = db.q("""SELECT l.id, l.status, l.business_type, l.need, l.origin, pr.keyword, pr.direction, pr.seller_type, pr.categories,
                          g.name grp, g.keyword gkw
                   FROM leads l LEFT JOIN prospects pr ON pr.lead_id=l.id LEFT JOIN posts p ON p.id=l.post_id LEFT JOIN groups g ON g.id=p.group_id
                   WHERE l.status IN ('ordered','sample','contacted') AND COALESCE(l.is_sample,0)=0 AND l.created_at>=?
                   ORDER BY l.status='ordered' DESC, l.id DESC LIMIT 40""", (_since(days),))
    won = [r for r in rows if r["status"] == "ordered"]
    pick = won if len(won) >= 2 else rows
    return {"so_khach_mua": len(won), "dung": "khach_mua" if pick is won else "khach_quan_tam",
            "mau": [{"loai": r["business_type"] or r["seller_type"] or "", "nganh": (r["categories"] or "")[:80],
                     "ho_viet": (r["need"] or "")[:160], "tu_khoa_ra_khach": r["keyword"] or r["gkw"] or "",
                     "nhom": r["grp"] or ""} for r in pick[:15]]}


def keyword_results(days: int = 30) -> list[dict]:
    """Mỗi từ khóa Mai tìm: bao nhiêu tài khoản, bao nhiêu SĐT, bao nhiêu khách mua."""
    return db.q("""SELECT pr.keyword kw, pr.direction d, COUNT(*) n, SUM(COALESCE(pr.phone,'')!='') phones,
                          SUM(l.status='ordered') won
                   FROM prospects pr LEFT JOIN leads l ON l.id=pr.lead_id
                   WHERE COALESCE(pr.keyword,'')!='' AND pr.created_at>=? GROUP BY pr.keyword, pr.direction ORDER BY won DESC, phones DESC""",
                (_since(days),))


def _trials() -> dict:
    try:
        return json.loads(s().get("ceo_kw_trials") or "{}")
    except Exception:
        return {}


def trial_words() -> list[str]:
    return [f"{v['kind']}: {k}" for k, v in _trials().items()]


def suggest_keywords(apply: bool = True) -> dict:
    """CEO nhờ Claude đọc chân dung khách mua thật, đề xuất từ khóa tìm khách cho Mai và chủ đề tìm nhóm cho Tuấn.
    Từ khóa mới chạy thử 14 ngày; không ra SĐT thì tự bỏ (xem review_trials)."""
    from agents import system_prompt
    from llm import llm
    import prospect
    import group_finder
    prof = won_profile()
    if not prof["mau"]:
        return {"ok": False, "why": "Chưa có khách mua hoặc khách sếp đã liên hệ để học chân dung"}
    if not llm.live:
        return {"ok": False, "why": "Cần khóa Claude để CEO đề xuất từ khóa mới"}
    kws = prospect.keywords()
    have = {d: kws.get(d, []) for d in (1, 2, 3, 4, 5)}
    res = keyword_results()
    prompt = (f"Chân dung khách thật của xưởng (90 ngày): {json.dumps(prof, ensure_ascii=False)}\n"
              f"Kết quả từ khóa Mai đang tìm (30 ngày): {json.dumps(res[:15], ensure_ascii=False)}\n"
              f"Từ khóa đang có theo hướng: {json.dumps(have, ensure_ascii=False)}\n"
              f"Chủ đề tìm nhóm đang có: {json.dumps(group_finder.pool()[:20], ensure_ascii=False)}\n\n"
              "Hướng: 1 = người livestream bán trà, ngũ cốc, thực phẩm; 2 = người bán sản phẩm tương tự / bổ trợ; 3 = người bán nhiều nhóm "
              "hàng tiêu dùng; 4 = người tìm nguồn hàng, tuyển đại lý; 5 = từ khóa quét Thư viện quảng cáo.\n"
              "Đề xuất từ khóa MỚI (chưa có) để Mai gõ vào ô tìm kiếm Facebook, giống cách khách thật tự mô tả mình, và chủ đề nhóm mới "
              "để tìm hội nhóm có người như vậy. Dựa vào điểm chung của khách thật, không đoán bừa. Từ khóa 2–6 chữ, tiếng Việt tự nhiên.\n"
              'Trả JSON {"mai": [{"huong": 1-5, "tu_khoa": "..."}] (tối đa 6), "nhom": ["..."] (tối đa 3), "vi_sao": "1-2 câu: điểm chung của khách thật"}')
    d = llm.json(system_prompt("ceo", s()), prompt, mock=None, max_tokens=700, task="ceo")
    if not isinstance(d, dict):
        return {"ok": False, "why": "Claude chưa đề xuất được"}
    added, trials = [], _trials()
    exist = {k.lower() for v in have.values() for k in v} | {k.lower() for k in group_finder.pool()} \
        | {(r["kw"] or "").lower() for r in keyword_results(90)}  # từ khóa Mai đã từng tìm cũng không thử lại
    if apply:
        cur = {int(k): v for k, v in json.loads(s().get("prospect_keywords") or "{}").items()} if s().get("prospect_keywords") else {}
        for it in (d.get("mai") or [])[:6]:
            try:
                h, kw = int(it.get("huong")), str(it.get("tu_khoa") or "").strip()[:60]
            except Exception:
                continue
            if h not in (1, 2, 3, 4, 5) or len(kw) < 3 or kw.lower() in exist:
                continue
            lst = cur.get(h) or list(have.get(h) or [])
            cur[h] = [kw] + lst  # đặt đầu danh sách để Mai thử sớm
            trials[kw] = {"kind": "mai", "dir": h, "at": db.today()}
            added.append(f"Mai (hướng {h}): {kw}")
            exist.add(kw.lower())
        if cur:
            db.set_setting("prospect_keywords", json.dumps({str(k): v for k, v in cur.items()}, ensure_ascii=False))
        pool = group_finder.pool()
        for kw in (d.get("nhom") or [])[:3]:
            kw = str(kw).strip()[:60]
            if len(kw) < 3 or kw.lower() in exist:
                continue
            pool = [kw] + pool
            trials[kw] = {"kind": "nhom", "at": db.today()}
            added.append(f"Tìm nhóm: {kw}")
            exist.add(kw.lower())
        db.set_setting("group_keywords", "\n".join(pool))
        db.set_setting("ceo_kw_trials", json.dumps(trials, ensure_ascii=False))
        if added:
            db.log("ceo", "Thử từ khóa tìm khách mới", "; ".join(added))
    return {"ok": True, "added": added, "why": str(d.get("vi_sao") or "")[:300]}


def review_trials(days: int = 14) -> list[str]:
    """Từ khóa thử đủ 14 ngày: ra SĐT thì giữ hẳn, không ra gì thì bỏ khỏi danh sách."""
    trials, out = _trials(), []
    if not trials:
        return out
    cut = _since(days)
    res = {r["kw"]: r for r in keyword_results(days + 7)}
    cur = json.loads(s().get("prospect_keywords") or "{}") if s().get("prospect_keywords") else {}
    import group_finder
    pool = group_finder.pool()
    for kw, t in list(trials.items()):
        if t["at"] > cut:
            continue
        if t["kind"] == "mai":
            r = res.get(kw) or {}
            if (r.get("phones") or 0) > 0 or (r.get("won") or 0) > 0:
                out.append(f"Giữ từ khóa “{kw}” ({r.get('phones', 0)} SĐT, {r.get('won', 0) or 0} đơn)")
            else:
                d = str(t.get("dir"))
                cur[d] = [k for k in cur.get(d, []) if k != kw]
                out.append(f"Bỏ từ khóa “{kw}” (14 ngày không ra SĐT)")
        else:
            g = db.one("SELECT COUNT(*) n FROM groups WHERE keyword=?", (kw,))["n"]
            if not g:
                pool = [k for k in pool if k != kw]
                out.append(f"Bỏ chủ đề nhóm “{kw}” (không tìm được nhóm đạt chuẩn)")
            else:
                out.append(f"Giữ chủ đề nhóm “{kw}” ({g} nhóm)")
        trials.pop(kw)
    db.set_setting("prospect_keywords", json.dumps(cur, ensure_ascii=False))
    db.set_setting("group_keywords", "\n".join(pool))
    db.set_setting("ceo_kw_trials", json.dumps(trials, ensure_ascii=False))
    for t in out:
        db.log("ceo", "Xem lại từ khóa thử", t)
    return out


# ---------------------------------------------------------------- 4. kênh Fanpage (Graph API, Facebook cho phép)
def scan_fanpage(fetch=None) -> dict:
    """Đọc bình luận dưới bài Fanpage 7 ngày qua qua Graph API: ai để SĐT hoặc hỏi giá thì thành khách (kênh “Fanpage”).
    Chỉ đọc; trả lời khách vẫn do sếp / Hà làm bằng tay."""
    import facebook
    import kpi
    if not facebook.configured():
        return {"ok": False, "why": "Chưa kết nối Fanpage (Cài đặt → Fanpage)"}
    st = s()
    posts = db.q("""SELECT id, fb_post_id FROM posts WHERE target_type='page' AND status='posted' AND COALESCE(fb_post_id,'')!=''
                    AND posted_at>=?""", (_since(7),))
    new = phones = 0
    for p in posts:
        try:
            data = fetch(p["fb_post_id"]) if fetch else facebook.comments(p["fb_post_id"])
        except Exception as e:
            import errors
            errors.report("fanpage", "Không đọc được bình luận Fanpage", str(e)[:300], screen="setup")
            continue
        cnt = 0
        for c in data:
            msg, who = (c.get("message") or "").strip(), (c.get("from") or {}).get("name") or "Khách Fanpage"
            if not msg or (c.get("from") or {}).get("id") == st.get("fb_page_id"):
                continue  # bình luận của chính trang
            cnt += 1
            if kpi.norm_phone(msg) or kpi.is_interested(msg):
                lid, created, got = kpi.upsert_lead(who, msg, p["id"], who, origin="fanpage")
                new += bool(created)
                phones += bool(got)
        db.run("UPDATE posts SET comments=MAX(COALESCE(comments,0), ?), last_scan_at=? WHERE id=?", (cnt, db.now(), p["id"]))
    return {"ok": True, "posts": len(posts), "new": new, "phones": phones}


def ads_advice() -> str:
    """Gợi ý bài nên chạy quảng cáo (sếp tự chạy trong Trình quản lý quảng cáo): bài có nhiều khách / bình luận nhất 30 ngày."""
    r = db.q("""SELECT p.id, p.target_type, pr.name, p.leads, p.comments, substr(p.content,1,80) head FROM posts p
                LEFT JOIN products pr ON pr.id=p.product_id WHERE p.status='posted' AND p.posted_at>=?
                ORDER BY COALESCE(p.leads,0)*5+COALESCE(p.comments,0) DESC LIMIT 1""", (_since(30),))
    if not r or not ((r[0]["leads"] or 0) + (r[0]["comments"] or 0)):
        return ""
    b = r[0]
    return (f"Bài #{b['id']} ({b['name'] or 'bài mẫu'}) đang hút khách nhất ({b['leads'] or 0} khách, {b['comments'] or 0} bình luận). "
            "Nếu sếp muốn chạy quảng cáo tìm khách sỉ: đăng lại bài này lên Fanpage rồi chạy mục tiêu Tin nhắn / Khách tiềm năng, "
            "nhắm người quản lý Trang bán hàng, sở thích kinh doanh online; ngân sách nhỏ 3–5 ngày để thử, đo bằng phễu kênh Fanpage.")


# ---------------------------------------------------------------- 5. báo cáo tuần như giám đốc
def weekly(send: bool = True) -> str:
    """Thứ Hai: tuần qua thế nào, nút thắt ở đâu, 3 việc tuần này, từ khóa thử giữ / bỏ, gợi ý quảng cáo."""
    from agents import system_prompt
    from llm import llm
    kept = review_trials()
    sug = suggest_keywords() if s().get("ceo_kw_auto", "1") == "1" else {"ok": False}
    data = data_brief(7)
    adv = ads_advice()
    txt = ""
    if llm.live:
        txt = llm.chat(system_prompt("ceo", s()),
                       f"Số liệu thật tuần qua: {json.dumps(data, ensure_ascii=False)}\n"
                       f"Từ khóa thử giữ / bỏ: {kept}\nTừ khóa mới CEO cho thử: {sug.get('added', [])}\n\n"
                       "Viết báo cáo tuần gửi sếp như một giám đốc kinh doanh: (1) 2–3 câu tuần qua bằng số liệu, so với mục tiêu; "
                       "(2) nút thắt lớn nhất và vì sao (dựa vào phễu: SĐT → sếp gọi → chốt, lý do không mua); (3) đúng 3 việc tuần này, "
                       "mỗi việc ghi ai làm và đo bằng gì. Ngắn gọn, không chung chung, không bịa số, xưng em gọi sếp. Dưới 170 chữ.",
                       max_tokens=600, task="ceo")
    if not txt:
        f = data.get("pheu", {}).get("tong", {})
        txt = (f"Tuần qua: {f.get('phones', 0)} SĐT, sếp gọi {f.get('called', 0)}, chốt {f.get('won', 0)} đơn. "
               + ("Nút thắt: còn " + str(data.get("khach_cho_sep_goi", 0)) + " khách chờ sếp gọi." if data.get("khach_cho_sep_goi") else ""))
    extra = []
    if kept:
        extra.append("Từ khóa thử: " + "; ".join(kept))
    if sug.get("added"):
        extra.append("Tuần này thử thêm: " + "; ".join(sug["added"]) + (f" (vì {sug['why']})" if sug.get("why") else ""))
    if adv:
        extra.append("Gợi ý quảng cáo: " + adv)
    full = txt.strip() + ("\n\n" + "\n".join(extra) if extra else "")
    db.set_setting("ceo_weekly_last", db.today())
    db.log("ceo", "Báo cáo tuần", full[:300])
    if send:
        try:
            import telegram_bot
            if telegram_bot.configured():
                telegram_bot.send("📈 <b>CEO Đức — báo cáo tuần</b>\n\n" + telegram_bot.e(full))
        except Exception as e:
            print("[ceo_brain]", e)
        import ceo_orders
        ceo_orders._say("ceo", "📈 Báo cáo tuần\n" + full, via="web")
    return full


def tick(now):
    st = s()
    if st.get("ceo_weekly", "1") != "1" or st.get("ceo_weekly_last") == db.today():
        return
    last = st.get("ceo_weekly_last") or ""
    if now.isoweekday() == 1 and now.strftime("%H:%M") >= (st.get("ceo_weekly_time") or "08:20") \
            and (not last or last <= _since(6)):
        try:
            weekly()
        except Exception as e:
            import errors
            errors.report_exc("ceo", "CEO viết báo cáo tuần bị lỗi", e)
    # Fanpage: đọc bình luận 3 lần/ngày cùng giờ quét bình luận của sale
    if st.get("fanpage_scan", "1") == "1":
        slots = [x.strip() for x in (st.get("scan_times") or "11:30,16:30,20:45").split(",") if x.strip()]
        hm = now.strftime("%H:%M")
        due = [x for x in slots if x <= hm]
        key = f"{db.today()} {max(due)}" if due else ""
        if key and st.get("fanpage_scan_last") != key:
            db.set_setting("fanpage_scan_last", key)
            try:
                scan_fanpage()
            except Exception as e:
                print("[ceo_brain] fanpage", e)

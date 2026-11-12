"""CEO học cách viết bài để duyệt bài tốt hơn.

CEO chấm mỗi bài trước khi cho đăng (thang 100) theo những gì CEO học được:
1. Từ THƯ VIỆN BÀI MẪU của sếp: bài tốt phải có ý tìm khách sỉ/gia công, lời kêu gọi + số Zalo, bố cục kiểu bài mẫu
   (tiêu đề, gạch đầu dòng, emoji vừa phải), độ dài trong khoảng của bài mẫu; bài viết lại từ mẫu phải giữ đủ thông tin chính
   của mẫu (thương hiệu, tiêu chuẩn GMP/ISO..., dòng sản phẩm).
2. Từ QUY ĐỊNH của sếp: không ghi giá, không hứa công dụng chữa bệnh, không trùng bài cũ (dễ bị Facebook coi là spam).
3. Từ SẾP SỬA BÀI: bài CEO đã duyệt mà sếp sửa hoặc hủy -> CEO ghi bài học (sổ tay + sổ kiến thức), lần sau chấm chặt hơn:
   sếp hay rút ngắn -> hạ độ dài tối đa; sếp hủy vì lý do X -> lần sau gặp X là trừ điểm.
4. Có khóa Claude: CEO nhờ Claude đọc bài cùng thư viện mẫu và bài học, cho điểm và góp ý cụ thể (dùng thêm, không thay quy tắc cứng).

Điểm từ 70 (sửa được ở Bài mẫu sỉ → CEO học duyệt bài) thì duyệt; thấp hơn thì trả về cho Lan kèm góp ý.
"""
import json
import re
from datetime import timedelta

import db
from knowledge import plain

WHOLESALE = re.compile(r"(sỉ|đại lý|gia công|nguồn hàng|phân phối|nhà phân phối|ctv|cộng tác viên|bỏ sỉ|nhập hàng|thương hiệu riêng|oem)", re.I)
CTA = re.compile(r"(ib|inbox|nhắn|liên hệ|zalo|gọi|để lại|comment|bình luận|kết bạn)", re.I)
EMOJI = re.compile(r"[\U0001F300-\U0001FAFF\u2600-\u27BF\u2B50\u2705]")
BULLET = re.compile(r"^\s*([•\-▪✅✔️🔹+]|\d+[.)])", re.M)
KEYTOK = re.compile(r"\b([A-ZĐ]{2,}[A-ZĐ0-9À-Ỹ]*)\b")


def s() -> dict:
    return db.get_settings()


def min_score() -> int:
    return int(s().get("ceo_review_min") or 70)


def _words(t: str) -> int:
    return len(re.findall(r"\w+", t or ""))


# ---------------------------------------------------------------- CEO học từ bài mẫu và từ sếp
def profile() -> dict:
    """Chuẩn bài tốt CEO rút ra từ thư viện bài mẫu + bài học từ sếp."""
    import post_template
    rows = post_template.samples(True)
    texts = [r["content"] for r in rows] or [post_template.DEFAULT_TEMPLATE]
    wc = sorted(_words(t) for t in texts)
    learned = json.loads(s().get("ceo_review_learned") or "{}")
    lo = max(30, int(wc[0] * 0.4))
    hi = int(wc[-1] * 1.6) + 30
    if learned.get("max_words"):
        hi = min(hi, int(learned["max_words"]))
    share = lambda rx: sum(bool(rx.search(t)) for t in texts) / len(texts)
    return {"samples": len(rows), "min_words": lo, "max_words": max(hi, lo + 20),
            "need_wholesale": share(WHOLESALE) >= 0.5, "need_cta": share(CTA) >= 0.5,
            "need_bullets": share(BULLET) >= 0.5,
            "emoji_max": int(learned.get("emoji_max") or max(12, max(len(EMOJI.findall(t)) for t in texts) * 2 + 6)),
            "bad_phrases": learned.get("bad_phrases", []), "lessons": [r["text"] for r in db.q(
                "SELECT text FROM lessons WHERE agent_id='ceo' AND status='active' AND rule_key LIKE 'review:%' ORDER BY id DESC LIMIT 8")]}


def _key_facts(sample: str) -> list[str]:
    """Thông tin chính của bài mẫu phải còn trong bài viết lại: chữ viết hoa (thương hiệu, GMP, ISO...)."""
    toks = {t for t in KEYTOK.findall(sample) if len(t) >= 2 and t not in ("CTV", "ĐT", "SĐT")}
    return sorted(toks)[:12]


def _similar(a: str, b: str) -> float:
    ta, tb = set(re.findall(r"\w+", plain(a))), set(re.findall(r"\w+", plain(b)))
    return len(ta & tb) / max(1, len(ta | tb))


# ---------------------------------------------------------------- chấm bài
def review(text: str, post_id: int | None = None, sample: str | None = None) -> dict:
    """Trả về {score, ok, reasons: [...], tips: [...]} cho một bài."""
    import ceo_orders
    import pricing
    pf = profile()
    t = text or ""
    reasons, tips, sc = [], [], 0
    hard = []
    if ceo_orders.REVIEW_BAD.search(t):
        hard.append("hứa công dụng chữa bệnh")
    if pricing.MONEY_RX.search(t) and re.search(r"giá|lãi|nhập|bán", t, re.I):
        hard.append("còn ghi giá (sếp chốt không công khai giá)")
    for ph in pf["bad_phrases"]:
        if plain(ph) and plain(ph) in plain(t):
            hard.append(f"có cụm sếp không thích: “{ph}”")
    # 1. đúng mục tiêu tìm khách sỉ (25)
    if WHOLESALE.search(t):
        sc += 25
    else:
        reasons.append("chưa nói rõ tìm khách sỉ / đại lý / gia công")
        tips.append("thêm 1 câu nói rõ xưởng nhận sỉ, tìm đại lý hoặc nhận gia công")
    # 2. lời kêu gọi + số Zalo (20)
    if pricing.has_contact(t) and CTA.search(t):
        sc += 20
    elif pricing.has_contact(t):
        sc += 12
        tips.append("thêm lời kêu gọi (ib, nhắn Zalo) trước số điện thoại")
    else:
        reasons.append("thiếu số Zalo báo giá")
        tips.append(f"thêm dòng {pricing.contact_line()}")
    # 3. bố cục giống bài mẫu (15)
    lines = [l for l in t.splitlines() if l.strip()]
    b = 0
    b += 5 if lines and len(lines[0]) <= 90 else 0
    b += 5 if (BULLET.search(t) or not pf["need_bullets"]) else 0
    em = len(EMOJI.findall(t))
    b += 5 if 1 <= em <= pf["emoji_max"] else 0
    sc += b
    if b < 10:
        tips.append("bố cục chưa giống bài mẫu: tiêu đề ngắn, gạch đầu dòng, emoji vừa phải" + (f" (đang có {em} emoji)" if em > pf["emoji_max"] else ""))
    # 4. độ dài (10)
    w = _words(t)
    if pf["min_words"] <= w <= pf["max_words"]:
        sc += 10
    else:
        reasons.append(f"{'quá ngắn' if w < pf['min_words'] else 'quá dài'} ({w} chữ, bài mẫu khoảng {pf['min_words']}–{pf['max_words']} chữ)")
    # 5. giữ đủ thông tin của bài mẫu (15)
    if sample:
        facts = _key_facts(sample)
        miss = [f for f in facts if f.lower() not in t.lower()]
        cover = 1 - len(miss) / len(facts) if facts else 1
        sc += round(15 * cover)
        if cover < 0.7:
            reasons.append("thiếu thông tin chính của bài mẫu: " + ", ".join(miss[:5]))
    else:
        sc += 10 if re.search(r"xưởng|nhà máy|sản xuất|tận gốc", t, re.I) else 5
    # 6. không trùng bài cũ (15)
    since = (db.clock() - timedelta(days=14)).strftime("%Y-%m-%d")
    top = max([_similar(t, o["content"] or "") for o in db.q(
        """SELECT content FROM posts WHERE id != ? AND target_type='group' AND status IN ('approved','scheduled','posting','posted')
           AND created_at >= ? ORDER BY id DESC LIMIT 80""", (post_id or 0, since))] or [0])
    if top >= 0.97:
        hard.append("trùng gần như y hệt bài đã đăng (Facebook dễ coi là spam)")
    elif top >= 0.85:
        sc += 5
        tips.append("khá giống bài đã đăng, nên đổi câu mở đầu và cách nói")
    else:
        sc += 15
    ai = _ai_review(t, pf, sample)
    if ai:
        sc = round((sc + ai["score"]) / 2)  # CEO tự chấm + Claude góp ý
        tips += [x for x in ai.get("tips", []) if x not in tips][:3]
    try:  # luật Facebook: phạm nặng thì không duyệt, phạm nhẹ thì trừ điểm và góp ý
        import fb_policy
        if fb_policy.enabled():
            for iss in fb_policy.check_text(t, post_id):
                if iss["level"] == "high":
                    hard.append("phạm luật Facebook: " + iss["msg"] + (f" (“{iss['hit']}”)" if iss.get("hit") else ""))
                else:
                    sc -= 5
                    tips.append("luật Facebook: " + iss["msg"] + (f" (“{iss['hit']}”)" if iss.get("hit") else ""))
    except Exception as e:
        print("[fb policy review]", e)
    if hard:
        reasons = hard + reasons
        sc = min(sc, 30)
    ok = not hard and sc >= min_score()
    return {"score": sc, "ok": ok, "reasons": reasons, "tips": tips[:5], "ai": bool(ai)}


def _ai_review(t: str, pf: dict, sample: str | None) -> dict | None:
    from llm import llm
    if not (llm.live and s().get("ceo_review_ai", "1") == "1"):
        return None
    try:
        import post_template
        from agents import system_prompt
        lib = "\n\n".join(r["content"][:900] for r in post_template.samples(True)[:4])
        d = llm.json(system_prompt("ceo", s()),
                     f"Bạn là CEO duyệt bài đăng nhóm Facebook tìm khách sỉ. Bài mẫu sếp thích:\n{lib}\n\nBài học từ những lần sếp sửa: "
                     f"{'; '.join(pf['lessons']) or 'chưa có'}\n" + (f"Bài này viết lại từ mẫu:\n{sample[:900]}\n" if sample else "")
                     + f"\nBÀI CẦN DUYỆT:\n{t[:2000]}\n\nChấm 0-100 (hay, đúng mục tiêu tìm khách sỉ, đúng thông tin mẫu, tự nhiên, không spam). "
                     "Trả JSON {\"score\": số, \"tips\": [\"góp ý cụ thể, tối đa 3\"]}.", mock=None, max_tokens=300, task="review")
        if isinstance(d, dict) and isinstance(d.get("score"), (int, float)):
            return {"score": max(0, min(100, int(d["score"]))), "tips": [str(x)[:160] for x in d.get("tips", [])][:3]}
    except Exception as e:
        print("[ceo ai review]", e)
    return None


def note(r: dict) -> str:
    return f"CEO chấm {r['score']}/100" + (": " + "; ".join(r["reasons"]) if r["reasons"] else "") + \
        (". Góp ý: " + "; ".join(r["tips"]) if r["tips"] else "")


def save(post_id: int, r: dict):
    pn = "; ".join(x for x in r["reasons"] + r["tips"] if "luật Facebook" in x)
    db.run("UPDATE posts SET review_score=?, review_note=?, reviewed_by='ceo', reviewed_at=?, review_ok=?, policy_note=? WHERE id=?",
           (r["score"], note(r)[:600], db.now(), 1 if r["ok"] else 0, pn[:500] or None, post_id))


# ---------------------------------------------------------------- sếp sửa / hủy bài CEO đã duyệt -> CEO rút kinh nghiệm
def on_boss_correction(post: dict, new_content: str | None = None, reason: str = ""):
    import knowledge
    import learning
    if post.get("reviewed_by") != "ceo":
        return
    learned = json.loads(s().get("ceo_review_learned") or "{}")
    old = post.get("content") or ""
    if new_content is not None:
        wo, wn = _words(old), _words(new_content)
        if wn < wo * 0.8:  # sếp rút ngắn: hạ độ dài tối đa
            learned["max_words"] = int(max(60, (learned.get("max_words") or wo) * 0.6 + wn * 0.4 * 1.2))
            lesson = f"Sếp rút ngắn bài CEO đã duyệt ({wo} → {wn} chữ): duyệt bài dài tối đa khoảng {learned['max_words']} chữ."
        else:
            gone = [l.strip() for l in old.splitlines() if len(l.strip()) > 8 and l.strip() not in new_content][:2]
            lesson = ("Sếp sửa bài CEO đã duyệt, bỏ các câu: " + " | ".join(g[:60] for g in gone)) if gone else \
                "Sếp sửa câu chữ bài CEO đã duyệt: xem bản sếp sửa làm chuẩn."
            for g in gone:
                if 8 < len(g) <= 60:
                    learned.setdefault("bad_phrases", [])
                    if g not in learned["bad_phrases"]:
                        learned["bad_phrases"] = (learned["bad_phrases"] + [g])[-20:]
    else:
        lesson = "Sếp hủy bài CEO đã duyệt" + (f": {reason}" if reason else "") + ". Lần sau gặp bài như vậy không duyệt."
        r = plain(reason)
        if "emoji" in r or "icon" in r:  # sếp chê nhiều emoji: lần sau giới hạn chặt hơn
            learned["emoji_max"] = max(4, int(len(EMOJI.findall(old)) * 0.7))
        if re.search(r"\bdai\b", r):
            learned["max_words"] = max(60, int(_words(old) * 0.8))
        if reason and 3 < len(reason) <= 60:
            learned.setdefault("bad_reasons", [])
            learned["bad_reasons"] = (learned["bad_reasons"] + [reason])[-20:]
    db.set_setting("ceo_review_learned", json.dumps(learned, ensure_ascii=False))
    import coach
    coach.note("ceo", "edit" if new_content is not None else "bad", old,
               (f"Sếp sửa bài CEO đã duyệt thành: {new_content[:250]}" if new_content is not None
                else "Sếp hủy bài CEO đã duyệt" + (f": {reason}" if reason else "")), f"post:{post['id']}")
    learning.add_lesson("ceo", lesson, f"Bài #{post['id']}", "boss", 0.9, f"review:{post['id']}")
    knowledge.save("ceo", "Bài học duyệt bài: " + lesson[:60], lesson, question="Duyệt bài đăng nhóm thế nào cho sếp hài lòng?",
                   keywords="duyet bai ceo sep sua", source="boss", kind="guide")
    db.log("ceo", "Học kiến thức mới", "Rút kinh nghiệm duyệt bài: " + lesson[:160])


def overview() -> dict:
    pf = profile()
    since = (db.clock() - timedelta(days=30)).strftime("%Y-%m-%d")
    ok = db.one("SELECT COUNT(*) n FROM posts WHERE reviewed_by='ceo' AND review_ok=1 AND created_at>=?", (since,))["n"]
    rej = db.one("SELECT COUNT(*) n FROM posts WHERE reviewed_by='ceo' AND review_ok=0 AND created_at>=?", (since,))["n"]
    fixed = db.one("""SELECT COUNT(DISTINCT p.id) n FROM posts p JOIN feedback f ON f.post_id=p.id AND f.kind IN ('edit','reject')
                      WHERE p.reviewed_by='ceo' AND p.review_ok=1 AND p.created_at>=? AND f.created_at >= COALESCE(p.reviewed_at,'')""",
                   (since,))["n"]
    return {"profile": pf, "min_score": min_score(), "approved": ok, "rejected": rej, "boss_fixed": fixed,
            "accuracy": round(100 * (ok - fixed) / ok) if ok else None,
            "recent": db.q("""SELECT id, title, review_score, review_note, status FROM posts WHERE reviewed_by='ceo'
                              ORDER BY reviewed_at DESC LIMIT 8"""),
            "ai": s().get("ceo_review_ai", "1") == "1"}

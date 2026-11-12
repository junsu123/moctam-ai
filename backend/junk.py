"""Data rác: sếp loại một khách ở màn hình Khách hàng -> Mai ghi nhớ, lần sau tìm khách tự loại các trường hợp giống vậy.

Mai nhớ theo 3 tầng:
1. Đích danh: link trang, số điện thoại, tên đã bị loại -> không bao giờ đưa lại (cả khách Mai tìm lẫn khách từ bình luận).
2. Lý do sếp chọn:
   - "Sai ngành hàng" + chữ sếp ghi (VD quần áo) -> thêm vào điều kiện "Loại ngay nếu có" của Mai.
   - "Affiliate / KOC", "Cửa hàng truyền thống": loại cùng kiểu người bán 2 lần trở lên -> Mai bỏ qua kiểu người bán đó.
   - Các lý do khác ghi vào sổ kiến thức và lời dặn của Mai.
3. Học từ chữ: so chữ trong các data rác với khách tốt (khách đã liên hệ, đã nhập hàng). Chữ xuất hiện ở ít nhất 3 data rác mà
   gần như không có ở khách tốt -> Mai trừ 25 điểm khách có chữ đó và đề xuất sếp "Loại hẳn". Khách mới giống hệt một data rác
   (trùng trên 60% chữ) -> Mai loại luôn.
"""
import json
import re
from collections import Counter

import db
from knowledge import plain

REASONS = {
    "not_seller": "Không bán hàng online",
    "wrong_niche": "Sai ngành hàng",
    "retail_buyer": "Chỉ mua lẻ, không nhập sỉ",
    "competitor": "Đối thủ / nhà cung cấp",
    "affiliate": "Affiliate / KOC",
    "store": "Cửa hàng truyền thống",
    "bad_phone": "Số điện thoại sai, không liên lạc được",
    "spam": "Tài khoản ảo, spam",
    "other": "Khác",
}
STOP = set("""co khong la cua va cho voi thi ma nay do em anh chi ben minh a nhe oi duoc nhung cac mot nao gi sao the nhu de khi
neu vay roi con hay hoac ve tu tren duoi trong ngoai ra vao lai nua cung rat qua lam bi da se ban toi chung ta no nha nhi
shop hang facebook trang bai viet gio ngay phut tuan thang nam nguoi theo doi thich binh luan chia se zalo inbox ib sdt
chuyen nhan can tim nguon kho si le gia uy tin chat luong moi dang tot nhieu them cac
bang tai sau truoc het luon vua rang nen vi boi cung hon nhat moi tung tat ca cai chiec nhieu it day kia
mai lan tuan minh ceo xuong moc tam diem hang""".split())  # tên agent, tên xưởng: không phải dấu hiệu khách


URL_RX = re.compile(r"https?://\S+|www\.\S+|\S+\.(?:com|vn|net)\S*", re.I)


def _words(text: str) -> list[str]:
    return [w for w in re.findall(r"[a-z0-9]+", plain(URL_RX.sub(" ", text or ""))) if w not in STOP and not w.isdigit()]


def _tokens(text: str) -> set[str]:
    return {w for w in _words(text) if len(w) >= 3}


def _bigrams(text: str) -> set[str]:
    ws = _words(text)
    return {f"{a} {b}" for a, b in zip(ws, ws[1:]) if len(a) >= 2 and len(b) >= 2}


def _norm_phone(p: str | None) -> str:
    d = re.sub(r"\D", "", p or "")
    return "0" + d[2:] if d.startswith("84") and len(d) == 11 else d


def _canon(url: str | None) -> str:
    if not url or "http" not in url:
        return ""
    import prospect
    return prospect.canon(url)


# ---------------------------------------------------------------- sếp loại
def lead_text(lead: dict, pr: dict | None) -> str:
    parts = [lead.get("name"), lead.get("business_type"), lead.get("need"), lead.get("note"), lead.get("source")]
    if pr:
        parts += [pr.get("account_name"), pr.get("products"), pr.get("categories"), pr.get("import_signals")]
        try:
            parts += [e["text"] for e in json.loads(pr.get("evidence") or "[]") if e.get("kind") not in ("rule", "rule_fail")]
        except Exception:
            pass
    return " \n".join(str(x) for x in parts if x)


def mark(lead_id: int, reason: str, note: str = "") -> dict:
    _cache.clear()
    lead = db.one("SELECT * FROM leads WHERE id=?", (lead_id,))
    if not lead:
        raise ValueError("Không tìm thấy khách")
    reason = reason if reason in REASONS else "other"
    pr = db.one("SELECT * FROM prospects WHERE lead_id=? ORDER BY id DESC LIMIT 1", (lead_id,))
    url = _canon((pr or {}).get("account_url") or lead.get("contact"))
    jid = db.run("""INSERT INTO junk(lead_id, prospect_id, name, phone, url, seller_type, reason, note, text, created_at)
                    VALUES (?,?,?,?,?,?,?,?,?,?)""",
                 (lead_id, (pr or {}).get("id"), lead["name"], _norm_phone(lead.get("phone")), url, (pr or {}).get("seller_type"),
                  reason, (note or "").strip()[:300], lead_text(lead, pr)[:4000], db.now()))
    db.run("UPDATE leads SET status='junk', boss_status='junk', updated_at=? WHERE id=?", (db.now(), lead_id))
    if pr:
        db.run("""UPDATE prospects SET status='rejected', grade='D', rule_fail=?, next_action=?, updated_at=? WHERE id=?""",
               (f"Sếp đánh dấu data rác: {REASONS[reason]}", f"Sếp đánh dấu data rác ({REASONS[reason]}). Mai không tìm lại.",
                db.now(), pr["id"]))
    learned = _learn_from(reason, note, pr)
    if pr or (lead.get("origin") or "") == "prospect":
        import coach
        coach.note("mai", "bad", f"Tìm ra {lead['name']}, chấm {(pr or {}).get('score', '?')} điểm: {lead_text(lead, pr)[:400]}",
                   f"Sếp loại data rác: {REASONS[reason]}" + (f" – {note}" if note else ""), f"lead:{lead_id}")
    db.log("mai", "Ghi nhớ data rác", f"Sếp loại {lead['name']}: {REASONS[reason]}{(' – ' + note) if note else ''}. " + learned)
    return {"id": jid, "learned": learned}


def mark_url(name: str, url: str, reason: str = "other", note: str = "", text: str = "") -> dict:
    """Loại một tài khoản chưa thành khách (vd. người trong gợi ý kết bạn): Mai không tìm lại, Tuấn không gợi ý lại."""
    _cache.clear()
    reason = reason if reason in REASONS else "other"
    c = _canon(url)
    old = db.one("SELECT id FROM junk WHERE url=?", (c,)) if c else None
    if old:
        return {"id": old["id"], "learned": ""}
    jid = db.run("""INSERT INTO junk(lead_id, prospect_id, name, phone, url, seller_type, reason, note, text, created_at)
                    VALUES (NULL,NULL,?,?,?,?,?,?,?,?)""",
                 (name, "", c, None, reason, (note or "").strip()[:300], (text or "")[:4000], db.now()))
    learned = _learn_from(reason, note, None)
    db.log("mai", "Ghi nhớ data rác", f"Sếp loại {name}: {REASONS[reason]}{(' – ' + note) if note else ''}. " + learned)
    return {"id": jid, "learned": learned}


def _learn_from(reason: str, note: str, pr: dict | None) -> str:
    """Biến lý do sếp chọn thành điều kiện Mai áp dụng."""
    import knowledge
    import prospect_rules
    out = []
    if reason == "wrong_niche" and note:
        lead_rx = r"^(?:chuyên |bán |shop |kinh doanh |buôn |sỉ |nhập )+"  # "bán mỹ phẩm" -> "mỹ phẩm"
        words = [re.sub(lead_rx, "", w.strip(), flags=re.I).strip() for w in re.split(r"[,;/.]| và | hoặc ", note)]
        words = [w for w in words if 1 < len(w) <= 30]
        if words:
            c = prospect_rules.get()
            prospect_rules.save({"exclude": c["exclude"] + [w for w in words if plain(w) not in map(plain, c["exclude"])]})
            out.append("Thêm vào điều kiện loại: " + ", ".join(words))
    stype = {"affiliate": ("affiliate", "koc"), "store": ("store",)}.get(reason)
    if stype:
        n = db.one(f"SELECT COUNT(*) n FROM junk WHERE reason=?", (reason,))["n"]
        c = prospect_rules.get()
        if n >= 2 and not all(t in c["skip_types"] for t in stype):
            prospect_rules.save({"skip_types": sorted(set(c["skip_types"]) | set(stype))})
            out.append("Sếp đã loại kiểu người bán này " + str(n) + " lần: Mai bỏ qua từ giờ")
    rows = db.q("SELECT reason, note FROM junk ORDER BY id DESC LIMIT 40")
    cnt = Counter(r["reason"] for r in rows)
    summary = "Những data sếp đã loại vì không hợp tệp khách: " + "; ".join(
        f"{REASONS[k]} ({v} lần)" for k, v in cnt.most_common()) + ". Ghi chú của sếp: " + "; ".join(
        dict.fromkeys(r["note"] for r in rows if r["note"])) + "."
    old = db.one("SELECT id FROM knowledge WHERE agent_id='mai' AND topic='Data rác sếp đã loại' AND status='active'")
    if old:
        db.run("UPDATE knowledge SET content=?, updated_at=? WHERE id=?", (summary[:1500], db.now(), old["id"]))
    else:
        knowledge.save("mai", "Data rác sếp đã loại", summary, question="Data nào không phù hợp tệp khách của sếp?",
                       keywords="data rac loai khong phu hop", source="boss", kind="guide")
    return ". ".join(out) or "Mai đã ghi nhớ, lần sau không đưa lại và loại các trường hợp giống vậy"


def restore(lead_id: int) -> None:
    _cache.clear()
    """Sếp bấm nhầm: bỏ đánh dấu rác."""
    db.run("DELETE FROM junk WHERE lead_id=?", (lead_id,))
    db.run("UPDATE leads SET status='new', boss_status='', updated_at=? WHERE id=?", (db.now(), lead_id))
    db.run("UPDATE prospects SET status='verified', rule_fail=NULL WHERE lead_id=? AND status='rejected'", (lead_id,))


# ---------------------------------------------------------------- Mai dùng khi tìm khách
def blocked(url: str | None = None, phone: str | None = None, name: str | None = None) -> str | None:
    """Đã bị sếp loại đích danh? Trả về lý do."""
    c, p = _canon(url), _norm_phone(phone)
    r = None
    if c:
        r = db.one("SELECT reason FROM junk WHERE url=?", (c,))
    if not r and p and len(p) >= 9:
        r = db.one("SELECT reason FROM junk WHERE phone=?", (p,))
    if not r and name and len(name.strip()) >= 4:
        r = db.one("SELECT reason FROM junk WHERE lower(name)=lower(?)", (name.strip(),))
    return REASONS.get(r["reason"], "data rác") if r else None


_cache: dict = {}


def _patterns_cached() -> list[dict]:
    """Mai kiểm hàng trăm tài khoản mỗi lần tìm: tính mẫu chữ rác 1 lần mỗi phút."""
    import time
    if _cache.get("at", 0) > time.time() - 60:
        return _cache["p"]
    _cache.update(at=time.time(), p=patterns())
    return _cache["p"]


def patterns(min_junk: int = 3) -> list[dict]:
    """Chữ hay gặp ở data rác mà hiếm ở khách tốt."""
    junk = db.q("SELECT text FROM junk ORDER BY id DESC LIMIT 200")
    if len(junk) < min_junk:
        return []
    # so với mọi khách chưa bị loại (khách tốt + khách đang chờ): chữ chung chung như "khách sỉ", "ship cod" sẽ không bị học nhầm
    good = db.q("""SELECT l.name, l.need, l.business_type, l.note, p.products, p.categories, p.evidence FROM leads l
                   LEFT JOIN prospects p ON p.lead_id=l.id WHERE COALESCE(l.status,'')!='junk'
                   ORDER BY (l.status IN ('contacted','sample','ordered')) DESC, l.id DESC LIMIT 300""")
    good += db.q("""SELECT account_name name, products, categories, evidence FROM prospects
                    WHERE lead_id IS NULL AND status NOT IN ('rejected') ORDER BY id DESC LIMIT 300""")
    if len(good) < 5:
        return []  # chưa đủ khách để so sánh: chỉ chặn đích danh + giống hệt
    niche = _niche()
    jc, gc = Counter(), Counter()
    for r in junk:
        jc.update(_tokens(r["text"]) | _bigrams(r["text"]))
    for r in good:
        t = " ".join(str(v) for v in r.values() if v)
        gc.update(_tokens(t) | _bigrams(t))
    dismissed = set(json.loads(db.get_settings().get("junk_dismissed") or "[]"))
    ex = {plain(x) for x in __import__("prospect_rules").get()["exclude"]}
    dis_words = {x for d in dismissed for x in d.split()} | {x for e in ex for x in e.split()}  # sếp bỏ qua/đã loại cụm: không gợi lại từng chữ
    out = []
    for w, n in jc.items():
        if n < min_junk or w in dismissed or w in ex or set(w.split()) <= niche or set(w.split()) & dis_words:
            continue
        g = gc.get(w, 0)
        if n / len(junk) >= 0.25 and g <= int(0.05 * len(good)):
            out.append({"word": w, "junk": n, "good": g})
    out.sort(key=lambda x: (-x["junk"], -len(x["word"])))
    # gộp 2 chữ luôn đi liền nhau thành cụm (quang chau), còn lại giữ chữ đơn
    one = {x["word"]: x for x in out if " " not in x["word"]}
    keep, used = [], set()
    for x in out:
        if " " not in x["word"]:
            continue
        a, b = x["word"].split()
        if a == b or {a, b} & used or {a, b} & niche or not ({a, b} & set(one)):
            continue
        if x["junk"] >= max(one[w]["junk"] for w in (a, b) if w in one):
            keep.append(x); used |= {a, b}
    keep += [x for w, x in one.items() if w not in used]
    keep.sort(key=lambda x: (-x["junk"], x["good"], -len(x["word"])))
    keep = keep[:12]
    for x in keep:
        x["label"] = _label(x["word"], [r["text"] for r in junk])
    return keep


def _label(word: str, texts: list[str]) -> str:
    """Tìm lại chữ có dấu cho sếp dễ đọc: 'quang chau' -> 'Quảng Châu'."""
    n = len(word.split())
    for tx in texts:
        ws = re.findall(r"\w+", URL_RX.sub(" ", tx or ""))
        for i in range(len(ws) - n + 1):
            if " ".join(plain(w) for w in ws[i:i + n]) == word:
                return " ".join(ws[i:i + n]).lower()
    return word


def _niche() -> set[str]:
    """Chữ thuộc ngành hàng của xưởng (trà, ngũ cốc...): không bao giờ học thành chữ rác."""
    import prospect_rules
    c = prospect_rules.get()
    src = " ".join(r["name"] + " " + (r.get("category") or "") for r in db.q("SELECT * FROM products"))
    src += " " + " ".join(c.get("must", []) + c.get("bonus", []) + c.get("fit", []))
    src += (" tra ngu coc cafe ca phe bot com detox thao moc tui loc si nhap hang khach ship cod ban online shop"
            " livestream live tiktok shopee lazada san tmdt dai ly ctv cong tac vien me bim kinh doanh"
            " ha noi hcm sai gon da nang toan quoc")  # kiểu khách sỉ xưởng nhắm tới: không coi là dấu hiệu rác
    return _tokens(src)


def check(text: str, name: str = "") -> tuple[int, str | None, str | None]:
    """(điểm trừ, lý do trừ điểm, lý do loại hẳn) cho một khách mới."""
    t = (name or "") + " " + (text or "")
    toks = _tokens(t)
    if toks:
        for r in db.q("SELECT id, name, text FROM junk ORDER BY id DESC LIMIT 200"):
            jt = _tokens(r["text"])
            if jt and len(toks & jt) / max(1, len(toks | jt)) >= 0.6:
                return 0, None, f"giống data rác sếp đã loại ({r['name'][:40]})"
    pt = plain(t)
    hit = [p["label"] for p in _patterns_cached() if re.search(r"(?<![a-z0-9])" + re.escape(p["word"]) + r"(?![a-z0-9])", pt)]
    if hit:
        return 25, "giống data rác: " + ", ".join(hit[:3]), None
    return 0, None, None


def dismiss(word: str):
    _cache.clear()
    d = json.loads(db.get_settings().get("junk_dismissed") or "[]")
    if word not in d:
        db.set_setting("junk_dismissed", json.dumps((d + [word])[-200:], ensure_ascii=False))


def exclude_word(word: str):
    _cache.clear()
    import prospect_rules
    c = prospect_rules.get()
    if plain(word) not in map(plain, c["exclude"]):
        prospect_rules.save({"exclude": c["exclude"] + [word]})
    db.log("mai", "Ghi nhớ data rác", f"Sếp cho loại hẳn khách có chữ “{word}”")


def overview() -> dict:
    rows = db.q("SELECT * FROM junk ORDER BY id DESC LIMIT 100")
    return {"items": rows, "total": db.one("SELECT COUNT(*) n FROM junk")["n"], "reasons": REASONS,
            "by_reason": db.q("SELECT reason, COUNT(*) n FROM junk GROUP BY reason ORDER BY n DESC"),
            "patterns": patterns(), "skipped": int(db.get_settings().get("junk_skipped") or 0)}


def count_skip(n: int = 1):
    db.set_setting("junk_skipped", str(int(db.get_settings().get("junk_skipped") or 0) + n))

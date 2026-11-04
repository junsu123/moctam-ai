"""Điều kiện tìm khách sỉ do sếp đặt + bài sếp dạy Mai kỹ năng tìm kiếm trên Facebook.

Sếp nhập điều kiện ở trang Tìm khách sỉ → "Điều kiện tìm khách sỉ của sếp". Mai áp dụng cho MỌI tài khoản tìm được:
- Phải có (ít nhất 1 trong các chữ): không có thì Không đạt (hạng D).
- Loại ngay nếu có: VD "quần áo", "mỹ phẩm", "vay tiền" -> Không đạt.
- Ưu tiên (cộng điểm): mỗi chữ khớp cộng N điểm (mặc định 5), tối đa 20.
- Ngành hàng hợp thêm: chữ khớp thì điểm "Phù hợp ngành hàng" đủ 20.
- Khu vực ưu tiên: khớp thì cộng điểm.
- Người theo dõi tối thiểu / tối đa, bài mới nhất trong N ngày, loại người bán bỏ qua.
- Hạng tối thiểu để vào mục Khách hàng (mặc định C) — vẫn phải có SĐT.
- Cách tìm trên Facebook: tìm Trang, Bài viết, Bài viết gần đây, Mọi người.

Sếp dạy kỹ năng: mỗi bài dạy được lưu vào sổ kiến thức của Mai (nguồn: Sếp dạy) và đưa vào lời dặn của Mai. Mai đọc bài dạy,
rút ra gợi ý (từ khóa trong ngoặc kép, nhóm cần đọc, chữ cần loại / phải có / ưu tiên); sếp bấm "Áp dụng" thì thành điều kiện.
"""
import json
import re

import db
from knowledge import plain

DEFAULT = {"must": [], "exclude": [], "bonus": [], "bonus_points": 5, "fit": [], "regions": [], "followers_min": 0,
           "followers_max": 0, "recent_days": 0, "skip_types": [], "crm_min_grade": "C", "search_kinds": ["pages", "posts"],
           "note": ""}
SEARCH_KINDS = {"pages": "Trang", "posts": "Bài viết", "posts_recent": "Bài viết gần đây", "people": "Mọi người"}
LIST_KEYS = ("must", "exclude", "bonus", "fit", "regions")


def get() -> dict:
    try:
        c = json.loads(db.get_settings().get("prospect_criteria") or "{}")
    except Exception:
        c = {}
    return {**DEFAULT, **{k: v for k, v in c.items() if k in DEFAULT}}


def _clean_list(v, strip: bool = True) -> list[str]:
    if isinstance(v, str):
        v = re.split(r"[\n,;]+", v)
    out = []
    for x in v or []:
        x = str(x).strip().strip('"“”\'').strip()
        for _ in range(3 if strip else 0):  # bỏ chữ đệm đầu cụm: "các shop có livestream" -> "livestream"
            x = re.sub(r"^(các|những|người|shop|có|đang|bán|là|cho|em|sếp)\s+", "", x, flags=re.I).strip()
        if 1 < len(x) <= 60 and plain(x) not in [plain(y) for y in out]:
            out.append(x)
    return out[:60]


def save(data: dict) -> dict:
    c = get()
    for k in LIST_KEYS:
        if k in data:
            c[k] = _clean_list(data[k])
    for k, lo, hi in (("bonus_points", 1, 20), ("followers_min", 0, 10_000_000), ("followers_max", 0, 100_000_000),
                      ("recent_days", 0, 365)):
        if data.get(k) is not None:
            c[k] = max(lo, min(hi, int(data[k] or 0)))
    if "skip_types" in data:
        c["skip_types"] = [t for t in data["skip_types"] if isinstance(t, str)][:10]
    if data.get("crm_min_grade") in ("A", "B", "C"):
        c["crm_min_grade"] = data["crm_min_grade"]
    if "search_kinds" in data:
        c["search_kinds"] = [k for k in data["search_kinds"] if k in SEARCH_KINDS] or ["pages", "posts"]
    if "note" in data:
        c["note"] = str(data["note"] or "")[:3000]
    db.set_setting("prospect_criteria", json.dumps(c, ensure_ascii=False))
    _to_knowledge(c)
    return c


def summary(c: dict | None = None) -> str:
    """Điều kiện viết thành lời (đưa vào lời dặn của Mai và sổ kiến thức)."""
    c = c or get()
    import prospect
    parts = []
    if c["must"]:
        parts.append("Phải có ít nhất 1 trong: " + ", ".join(c["must"]))
    if c["exclude"]:
        parts.append("Loại ngay nếu có: " + ", ".join(c["exclude"]))
    if c["bonus"]:
        parts.append(f"Ưu tiên (+{c['bonus_points']} điểm mỗi chữ): " + ", ".join(c["bonus"]))
    if c["fit"]:
        parts.append("Ngành hàng phù hợp thêm: " + ", ".join(c["fit"]))
    if c["regions"]:
        parts.append("Khu vực ưu tiên: " + ", ".join(c["regions"]))
    if c["followers_min"] or c["followers_max"]:
        parts.append("Người theo dõi " + (f"từ {c['followers_min']:,}".replace(",", ".") if c["followers_min"] else "")
                     + (f" đến {c['followers_max']:,}".replace(",", ".") if c["followers_max"] else ""))
    if c["recent_days"]:
        parts.append(f"Bài mới nhất trong {c['recent_days']} ngày")
    if c["skip_types"]:
        parts.append("Bỏ qua: " + ", ".join(prospect.SELLER_TYPES.get(t, t) for t in c["skip_types"]))
    parts.append(f"Hạng từ {c['crm_min_grade']} trở lên và có SĐT thì vào mục Khách hàng")
    parts.append("Cách tìm trên Facebook: " + ", ".join(SEARCH_KINDS[k] for k in c["search_kinds"]))
    if c["note"]:
        parts.append("Sếp dặn thêm: " + c["note"])
    return ". ".join(parts) + "."


def _to_knowledge(c: dict):
    import knowledge
    txt = summary(c)
    old = db.one("SELECT id FROM knowledge WHERE agent_id='mai' AND topic='Điều kiện tìm khách sỉ của sếp' AND status='active'")
    if old:
        db.run("UPDATE knowledge SET content=?, updated_at=? WHERE id=?", (txt, db.now(), old["id"]))
    else:
        knowledge.save("mai", "Điều kiện tìm khách sỉ của sếp", txt, question="Sếp muốn tìm khách sỉ theo điều kiện nào?",
                       keywords="dieu kien tim khach si sep", source="boss", kind="guide")


def prompt_block() -> str:
    c = get()
    lessons = db.q("SELECT text FROM prospect_lessons ORDER BY id DESC LIMIT 8")
    out = "\n\nĐIỀU KIỆN TÌM KHÁCH SỈ CỦA SẾP (bắt buộc làm theo): " + summary(c)
    if lessons:
        out += "\nKỸ NĂNG TÌM KIẾM SẾP ĐÃ DẠY:\n" + "\n".join(f"- {r['text'][:400]}" for r in lessons)
    return out


# ---------------------------------------------------------------- áp dụng khi chấm điểm
def hits(p: str, words: list[str]) -> list[str]:
    return [w for w in words if re.search(r"(?<!\w)" + re.escape(plain(w)) + r"(?!\w)", p)]


def grade_ok(g: str | None, c: dict | None = None) -> bool:
    c = c or get()
    return bool(g) and g <= c["crm_min_grade"]


def fit_words_hit(text: str) -> bool:
    c = get()
    return bool(c["fit"] and hits(plain(text or ""), c["fit"]))


def excluded(text: str) -> list[str]:
    return hits(plain(text or ""), get()["exclude"])


def apply(a: dict, name: str = "", extra: str = "") -> dict:
    """Áp điều kiện của sếp lên kết quả phân tích của một tài khoản."""
    import prospect
    c = get()
    p = plain(" ".join([name or "", a.get("_text") or "", extra or "", a.get("products_text") or ""]
                       + [e["text"] for e in a.get("evidence", [])]))
    parts = a["parts"]
    base = sum(parts.values())
    fail, good = [], []
    if c["fit"] and (fh := hits(p, c["fit"])):
        parts["fit"] = 20
        good.append("ngành hàng sếp chọn: " + ", ".join(fh[:3]))
    bonus = 0
    if bh := hits(p, c["bonus"]):
        bonus += min(20, len(bh) * int(c["bonus_points"]))
        good.append("ưu tiên: " + ", ".join(bh[:4]))
    if rh := hits(p, c["regions"]):
        bonus += min(10, 5 * len(rh))
        good.append("khu vực: " + ", ".join(rh[:2]))
    if eh := hits(p, c["exclude"]):
        fail.append("có chữ sếp loại: " + ", ".join(eh[:3]))
    if c["must"] and not hits(p, c["must"]):
        fail.append("thiếu điều kiện bắt buộc (" + ", ".join(c["must"][:4]) + ")")
    f = a.get("followers")
    if f is not None and f > 0:
        if c["followers_min"] and f < c["followers_min"]:
            fail.append(f"chỉ {f:,} người theo dõi".replace(",", "."))
        if c["followers_max"] and f > c["followers_max"]:
            fail.append(f"{f:,} người theo dõi, vượt mức sếp đặt".replace(",", "."))
    if c["recent_days"] and a.get("last_post_hours") is not None and a["last_post_hours"] > c["recent_days"] * 24:
        fail.append(f"bài mới nhất cách đây {int(a['last_post_hours'] // 24)} ngày (sếp cần trong {c['recent_days']} ngày)")
    if a.get("seller_type") in c["skip_types"]:
        fail.append(f"là {prospect.SELLER_TYPES.get(a['seller_type'], a['seller_type'])} (sếp bỏ qua)")
    a["rule_bonus"] = bonus
    a["score"] = max(0, min(100, sum(parts.values()) + bonus))
    g = prospect.grade_of(a["score"])
    if "buyer" in a.get("tags", []) and parts.get("fit") == 20:
        g = min(g, "A" if a["phones"] else "B")
    a["grade"] = g if a.get("enough") else "D"
    if good:
        a["evidence"] = [{"kind": "rule", "text": "Đúng điều kiện của sếp: " + "; ".join(good), "url": None}] + a["evidence"]
    if fail:
        a["rule_fail"] = "; ".join(fail)
        a["grade"] = "D"
        a["evidence"] = [{"kind": "rule_fail", "text": "Không đạt điều kiện của sếp: " + a["rule_fail"], "url": None}] + a["evidence"]
    a["rule_note"] = "; ".join(good)
    return a


def rescore_all() -> dict:
    """Sếp đổi điều kiện: Mai chấm lại mọi khách đã tìm (dựa trên chữ, bằng chứng đã lưu)."""
    import prospect
    cnt = {"checked": 0, "fail": 0, "crm": 0}
    for r in db.q("SELECT * FROM prospects WHERE status IN ('verified','contacted') AND COALESCE(parts,'') NOT IN ('','{}')"):
        try:
            parts = json.loads(r["parts"])
            ev = [e for e in json.loads(r["evidence"] or "[]") if e["kind"] not in ("rule", "rule_fail")]
        except Exception:
            continue
        a = {"parts": {k: v for k, v in parts.items()}, "evidence": ev, "phones": [r["phone"]] if r["phone"] else [],
             "followers": r["followers"], "seller_type": r["seller_type"], "tags": (r["tags"] or "").split(","),
             "products_text": r["products"] or "", "enough": True, "_text": (r["categories"] or "") + " " + (r["import_signals"] or ""),
             "last_post_hours": None}
        m = re.search(r"cách đây (\d+) (ngày|giờ)", r["recent_activity"] or "")
        if m:
            a["last_post_hours"] = int(m.group(1)) * (24 if m.group(2) == "ngày" else 1)
        apply(a, (r["account_name"] or "") + " " + (r["shop_name"] or ""))
        nxt = r["next_action"]
        if a.get("rule_fail"):
            nxt = "Không đạt điều kiện của sếp: " + a["rule_fail"]
            cnt["fail"] += 1
        elif (r["next_action"] or "").startswith("Không đạt điều kiện của sếp"):
            nxt = prospect.next_action(r, {**a, "categories": [], "shared_live": False, "live_count": 0,
                                          "affiliate_only": r["seller_type"] == "affiliate", "zalo": r["zalo"], "email": r["email"]})
        db.run("""UPDATE prospects SET score=?, grade=?, evidence=?, rule_bonus=?, rule_note=?, rule_fail=?, next_action=?, updated_at=?
                  WHERE id=?""", (a["score"], a["grade"], json.dumps(a["evidence"], ensure_ascii=False), a["rule_bonus"],
                                  a["rule_note"], a.get("rule_fail"), nxt, db.now(), r["id"]))
        cnt["checked"] += 1
        if (not a.get("rule_fail") and r["phone"] and not r["lead_id"] and grade_ok(a["grade"])
                and r["seller_type"] not in ("affiliate", "koc", "store")):
            if prospect.to_crm(r["id"], escalate=True):
                cnt["crm"] += 1
    db.log("mai", "Chấm lại theo điều kiện của sếp",
           f"Chấm lại {cnt['checked']} tài khoản: {cnt['fail']} không đạt điều kiện, {cnt['crm']} khách mới vào mục Khách hàng")
    return cnt


# ---------------------------------------------------------------- sếp dạy kỹ năng tìm kiếm
def understand(text: str) -> dict:
    """Mai đọc bài sếp dạy, rút ra gợi ý áp dụng được. Có khóa Claude thì nhờ Claude đọc; chưa có thì đọc theo mẫu câu."""
    from llm import llm
    if llm.live:
        try:
            from agents import system_prompt
            d = llm.json(system_prompt("mai", db.get_settings()),
                         "Sếp vừa dạy bạn cách tìm khách sỉ trên Facebook:\n\"\"\"" + text[:3000] + "\"\"\"\n"
                         "Rút ra những điều có thể cài vào phần mềm. Trả JSON: {\"keywords\": [từ khóa để gõ vào ô tìm kiếm Facebook], "
                         "\"ads_keywords\": [từ khóa tìm quảng cáo], \"must\": [chữ bắt buộc phải có], \"exclude\": [chữ phải loại], "
                         "\"bonus\": [chữ ưu tiên], \"fit\": [ngành hàng phù hợp], \"regions\": [tỉnh thành ưu tiên], "
                         "\"search_kinds\": [trong pages, posts, posts_recent, people], \"summary\": \"tóm tắt điều em học được, 1-2 câu, xưng em\"}. "
                         "Chỉ lấy điều sếp nói, không tự thêm.", mock=None, max_tokens=700, task="knowledge")
            if isinstance(d, dict):
                return {k: _clean_list(d.get(k), k not in ("keywords", "ads_keywords")) if k not in ("summary", "search_kinds") else d.get(k) for k in
                        ("keywords", "ads_keywords", "must", "exclude", "bonus", "fit", "regions", "search_kinds", "summary")} | \
                       {"groups": re.findall(r"https?://\S*/groups/[^\s,]+", text)}
        except Exception as e:
            print("[mai understand]", e)
    low = text.lower()
    quoted = [q.strip() for q in re.findall(r"[\"“”']([^\"“”']{2,60})[\"“”']", text)]
    out = {"keywords": [], "ads_keywords": [], "must": [], "exclude": [], "bonus": [], "fit": [], "regions": [], "search_kinds": [],
           "groups": re.findall(r"https?://\S*/groups/[^\s,]+", text)}
    for line in re.split(r"[\n.;]+", text):
        l = line.lower()
        qs = [q.strip() for q in re.findall(r"[\"“”']([^\"“”']{2,60})[\"“”']", line)]
        after = lambda rx: [x.strip() for x in re.split(r",| và | hoặc |/", re.split(rx, line, maxsplit=1, flags=re.I)[1])
                            if 1 < len(x.strip()) <= 40] if re.search(rx, line, re.I) else []
        if re.search(r"\b(loại|bỏ qua|không lấy|không tìm|tránh)\b", l):
            out["exclude"] += qs or after(r"\b(?:loại|bỏ qua|không lấy|không tìm|tránh)\b\s*(?:các|những|người|shop|bán)?\s*:?")
        elif re.search(r"\b(phải có|bắt buộc|chỉ lấy|chỉ tìm)\b", l):
            out["must"] += qs or after(r"\b(?:bắt buộc\s*(?:phải\s*có)?|phải có|chỉ lấy|chỉ tìm)\b\s*:?")
        elif re.search(r"\b(ưu tiên)\b", l):
            out["bonus"] += qs or after(r"\bưu tiên\b\s*(?:người|shop|các)?\s*:?")
        elif re.search(r"quảng cáo", l) and qs:
            out["ads_keywords"] += qs
        elif qs:
            out["keywords"] += qs
        if re.search(r"gần đây|mới nhất", l):
            out["search_kinds"].append("posts_recent")
        if re.search(r"\bmọi người\b|trang cá nhân|người dùng", l):
            out["search_kinds"].append("people")
    out["regions"] += [re.sub(r"^(ở|tại|khu vực)\s+", "", x, flags=re.I) for x in out["bonus"] if re.match(r"(ở|tại|khu vực)\s+", x, re.I)]
    out["bonus"] = [x for x in out["bonus"] if not re.match(r"(ở|tại|khu vực)\s+", x, re.I)]
    if not any(out[k] for k in ("keywords", "must", "exclude", "bonus")) and quoted:
        out["keywords"] = quoted
    out = {k: (_clean_list(v, k not in ("keywords", "ads_keywords")) if isinstance(v, list) and k not in ("groups", "search_kinds") else v)
           for k, v in out.items()}
    out["search_kinds"] = sorted(set(out["search_kinds"]))
    n = sum(len(out[k]) for k in ("keywords", "ads_keywords", "must", "exclude", "bonus", "groups"))
    out["summary"] = ("Em đã ghi bài này vào sổ kiến thức và sẽ làm theo khi đi tìm khách." +
                      (f" Em thấy {n} điều cài được vào phần mềm, sếp xem và bấm Áp dụng nhé." if n else ""))
    return out


def add_lesson(text: str) -> dict:
    import knowledge
    import learning
    text = (text or "").strip()
    if len(text) < 10:
        raise ValueError("Bài dạy quá ngắn")
    sug = understand(text)
    kid = knowledge.save("mai", "Sếp dạy: " + re.sub(r"\s+", " ", text)[:70], text, question="Sếp dạy cách tìm khách sỉ trên Facebook",
                         keywords="sep day tim khach si facebook " + " ".join(sug.get("keywords", [])[:5]), source="boss", kind="guide")
    lid = db.run("INSERT INTO prospect_lessons(text, suggest, applied, knowledge_id, created_at) VALUES (?,?,0,?,?)",
                 (text[:4000], json.dumps(sug, ensure_ascii=False), kid, db.now()))
    learning.award("mai", 5, "Sếp dạy kỹ năng tìm khách")
    db.log("mai", "Học kiến thức mới", "Sếp dạy: " + text[:150])
    return lesson(lid)


def lesson(lid: int) -> dict | None:
    r = db.one("SELECT * FROM prospect_lessons WHERE id=?", (lid,))
    if r:
        r["suggest"] = json.loads(r["suggest"] or "{}")
    return r


def apply_lesson(lid: int) -> dict:
    """Cài gợi ý Mai rút ra từ bài dạy vào điều kiện và từ khóa tìm kiếm."""
    import prospect
    r = lesson(lid)
    if not r:
        raise ValueError("Không tìm thấy bài dạy")
    sg = r["suggest"]
    c = get()
    upd = {k: c[k] + [x for x in sg.get(k, []) if plain(x) not in [plain(y) for y in c[k]]] for k in LIST_KEYS if sg.get(k)}
    if sg.get("search_kinds"):
        upd["search_kinds"] = sorted(set(c["search_kinds"]) | set(k for k in sg["search_kinds"] if k in SEARCH_KINDS))
    if upd:
        save(upd)
    kws = prospect.keywords()
    if sg.get("keywords"):  # từ khóa sếp dạy: đưa lên đầu hướng 1 (Mai tìm trước)
        kws[1] = _clean_list(sg["keywords"] + kws.get(1, []), False)[:12]
    if sg.get("ads_keywords"):
        kws[5] = _clean_list(sg["ads_keywords"] + kws.get(5, []), False)[:12]
    if sg.get("keywords") or sg.get("ads_keywords"):
        db.set_setting("prospect_keywords", json.dumps({str(k): v for k, v in kws.items()}, ensure_ascii=False))
    added = 0
    for u in sg.get("groups", []):
        import browser_poster as B
        url, err = B.check_group_url(u)
        if err or db.one("SELECT id FROM groups WHERE url=?", (url,)):
            continue
        db.run("INSERT INTO groups(name, url, topic, created_at, source, note) VALUES (?,?,?,?,'boss',?)",
               (url.rsplit("/", 1)[-1], url, "Sếp dạy Mai đọc nhóm này", db.now(), "Sếp đưa trong bài dạy Mai"))
        added += 1
    db.run("UPDATE prospect_lessons SET applied=1 WHERE id=?", (lid,))
    db.log("mai", "Áp dụng bài sếp dạy", f"Cài vào điều kiện tìm khách: {summary()[:300]}" + (f"; thêm {added} nhóm để đọc bình luận" if added else ""))
    return {"criteria": get(), "groups_added": added}


def lessons() -> list[dict]:
    out = []
    for r in db.q("SELECT * FROM prospect_lessons ORDER BY id DESC LIMIT 50"):
        r["suggest"] = json.loads(r["suggest"] or "{}")
        out.append(r)
    return out


def delete_lesson(lid: int):
    r = db.one("SELECT knowledge_id FROM prospect_lessons WHERE id=?", (lid,))
    if r and r["knowledge_id"]:
        db.run("DELETE FROM knowledge WHERE id=?", (r["knowledge_id"],))
    db.run("DELETE FROM prospect_lessons WHERE id=?", (lid,))

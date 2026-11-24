"""Phòng ban: Giám đốc (CEO quản lý toàn công ty), Kinh doanh, Hội nhóm, Trang Facebook, Website.

- Mỗi phòng có trưởng phòng (agent có sẵn được thăng chức), mục tiêu riêng, chỉ số riêng.
- Trưởng phòng tự đánh giá phòng mỗi tuần (mặc định thứ Hai 08:40, hoặc sếp bấm): đọc chỉ số, tìm nút thắt, lên 3 việc tuần này,
  và nếu số liệu cho thấy phòng thiếu sức làm thì đề xuất tuyển 1 vị trí (có Claude thì trưởng phòng tự suy nghĩ theo vai của mình;
  không có thì theo luật số liệu).
- CEO xét đề xuất: đủ số liệu chứng minh thiếu người, phòng chưa đủ người, vốn còn đủ nuôi agent 60 ngày → theo quyền CEO
  (tự quyết: tuyển luôn rồi báo sếp; chờ sếp duyệt: sếp bấm Duyệt / Không ở mục Phòng ban).
- Nhân viên tuyển vào làm việc thật theo vị trí (POSITIONS): mỗi vị trí gắn với việc có sẵn của phòng và tăng sức làm của phòng.
"""
import json
import math
import random
import re

import db

DEPTS = {
    "director": {"name": "Phòng Giám đốc", "head": "ceo", "core": ["ceo", "khoa"], "color": "#d4af37",
                 "goal": "Điều hành toàn công ty: vốn, doanh thu, nhân sự, xét đề xuất của các phòng"},
    "sales": {"name": "Phòng Kinh doanh", "head": "minh", "core": ["minh", "lan", "ha", "mai"], "color": "#2f5d3a",
              "goal": "Khách sỉ có số điện thoại và đơn hàng"},
    "groups": {"name": "Phòng Hội nhóm", "head": "tuan", "core": ["tuan", "bao"], "color": "#f08a24",
               "goal": "Nhóm đăng được, nhóm tương tác cao, bình luận có ích, không để nick bị chặn"},
    "pages": {"name": "Phòng Trang Facebook", "head": "nhi", "core": ["nhi"], "color": "#e0559b",
              "goal": "Trang mới theo xu hướng bền, người theo dõi và tương tác bài Trang tăng đều"},
    "website": {"name": "Phòng Website", "head": "vy", "core": ["vy", "huong", "khai"], "color": "#3c6fd8",
                "goal": "Bài website chuẩn SEO đúng hạn, website luôn lên đúng hosting"},
}
ORDER = ["director", "sales", "groups", "pages", "website"]

POSITIONS = {
    "seo_writer": {"dept": "website", "title": "Biên tập viên SEO", "max": 2,
                   "does": "Viết thêm 1 bài website chuẩn SEO mỗi tuần, bài ghi tên người viết, trưởng phòng / sếp duyệt như bài của Vy"},
    "page_editor": {"dept": "pages", "title": "Biên tập Trang", "max": 2,
                    "does": "Viết bài (kèm prompt ảnh) cho một phần các Trang đang chạy; phòng được tự tạo thêm 1 Trang mỗi 7 ngày (tối đa 3)"},
    "group_scout": {"dept": "groups", "title": "Chuyên viên rà soát nhóm", "max": 2,
                    "does": "Mỗi lượt rà soát đánh giá thêm 6 nhóm trong các nick, để nhóm kém được thoát sớm và nhóm tốt được đăng nhiều hơn"},
    "sale": {"dept": "sales", "title": "Nhân viên sale", "max": None,
             "does": "Giữ 3–5 nick Facebook: đăng bài, up bài, quét bình luận (sếp cần thêm nick cho người mới)"},
}
DESKS = {"groups": [18, 19], "website": [20, 21], "pages": [22, 23]}  # bàn trống trong khu của phòng (frontend/js/world3d.js)
NAMES = ["Thảo", "Quân", "Ngân", "Phúc", "Trâm", "Duy", "Yến", "Khánh", "Hân", "Sơn", "My", "Tâm"]
MINDSET = {
    "ceo": "Bạn nhìn cả công ty: tiền vốn, doanh thu, chi phí AI. Chỉ đồng ý tuyển khi số liệu chứng minh thiếu người và vốn đủ nuôi.",
    "minh": "Bạn nghĩ bằng phễu: số khách có SĐT → sếp gọi → chốt đơn. Nút thắt nằm ở bước nào thì dồn sức vào bước đó.",
    "tuan": "Bạn nghĩ bằng an toàn và chất lượng nhóm: nhóm tương tác cao, đúng tệp, nick không bị chặn quan trọng hơn số bài.",
    "nhi": "Bạn nghĩ bằng xu hướng bền và tương tác thật: Trang nào được hưởng ứng thì chăm thêm, Trang chậm thì đổi cách viết trước khi mở Trang mới.",
    "vy": "Bạn là SEO Leader, nghĩ bằng doanh thu: từ khóa nào đưa người bán hàng tới Zalo của xưởng, thứ hạng và lượt bấm từ Google, "
          "mỗi chủ đề một trang mạnh; Hương lo nội dung, Khải lo kỹ thuật, bạn duyệt và chọn việc ưu tiên.",
}


def _s() -> dict:
    return db.get_settings()


def dept_of(agent_id: str) -> str | None:
    for k, d in DEPTS.items():
        if agent_id in d["core"]:
            return k
    if agent_id.startswith("sale-"):
        return "sales"
    if agent_id.startswith("st-"):
        r = db.one("SELECT dept FROM staff WHERE id=?", (_sid(agent_id),))
        return r["dept"] if r else None
    return None


def _sid(agent_id: str) -> int:
    try:
        return int(agent_id[3:])
    except ValueError:
        return 0


def staff(dept: str | None = None, position: str | None = None) -> list[dict]:
    sql, p = "SELECT * FROM staff WHERE status='active'", []
    if dept:
        sql, p = sql + " AND dept=?", p + [dept]
    if position:
        sql, p = sql + " AND position=?", p + [position]
    return db.q(sql + " ORDER BY id", tuple(p))


def count(position: str) -> int:
    try:
        return db.one("SELECT COUNT(*) n FROM staff WHERE status='active' AND position=?", (position,))["n"]
    except Exception:
        return 0


def staff_agents() -> list[dict]:
    """Nhân viên tuyển thêm, dạng agent (văn phòng 3D, danh sách đội, lời dặn)."""
    import agents
    out = []
    for r in staff():
        look = json.loads(r["look"]) if r.get("look") else agents.SALE_LOOKS[r["id"] % len(agents.SALE_LOOKS)]
        pos = POSITIONS.get(r["position"], {})
        out.append({"id": f"st-{r['id']}", "kind": "staff", "name": r["name"], "role": f"{pos.get('title', r['position'])} · {DEPTS[r['dept']]['name']}",
                    "short": pos.get("does", ""), "personality": "Chăm chỉ, làm đúng việc trưởng phòng giao, báo lại bằng số liệu.",
                    "look": look, "desk": r["desk"], "dept": r["dept"], "face": agents.face_of(f"st-{r['id']}")})
    return out


def prompt_block(agent_id: str) -> str:
    """Phòng ban trong lời dặn của agent: thuộc phòng nào, ai là trưởng phòng, trưởng phòng nghĩ theo cách riêng."""
    k = dept_of(agent_id)
    if not k:
        return ""
    import agents
    d = DEPTS[k]
    head = agents.name_of(d["head"])
    out = f"\n\nPhòng ban: bạn thuộc {d['name']} (mục tiêu: {d['goal']})."
    if agent_id == d["head"]:
        out += (" Bạn là trưởng phòng: chịu trách nhiệm kết quả của phòng, báo cáo cho CEO, tự đánh giá phòng mỗi tuần và đề xuất tuyển "
                "người khi số liệu cho thấy phòng thiếu sức làm. " + MINDSET.get(agent_id, ""))
    else:
        out += f" Trưởng phòng là {head}; làm theo việc trưởng phòng giao, báo lại bằng số liệu."
    return out


# ---------------------------------------------------------------- chỉ số + nhu cầu người của từng phòng
def _ago(days: int) -> str:
    from datetime import timedelta
    return (db.clock() - timedelta(days=days)).strftime("%Y-%m-%d %H:%M:%S")


def metrics(dept: str) -> dict:
    one = lambda sql, p=(): (db.one(sql, p) or {}).get("n") or 0
    m = {}
    if dept == "website":
        week = int(_s().get("site_posts_week") or 3) + count("seo_writer")
        m = {"bai_moi_tuan": week, "bai_viet_14_ngay": one("SELECT COUNT(*) n FROM site_posts WHERE created_at>=?", (_ago(14),)),
             "bai_da_dang_14_ngay": one("SELECT COUNT(*) n FROM site_posts WHERE published_at>=?", (_ago(14),)),
             "diem_seo_tb": round(one("SELECT AVG(seo_score) n FROM site_posts WHERE created_at>=?", (_ago(30),)) or 0),
             "tu_khoa_cho_viet": one("SELECT COUNT(*) n FROM site_keywords WHERE status='planned'"),
             "bai_cho_duyet": one("SELECT COUNT(*) n FROM site_posts WHERE status='review'")}
        m["tuan_de_viet_het_tu_khoa"] = round(m["tu_khoa_cho_viet"] / max(1, week), 1)
    elif dept == "pages":
        eds = count("page_editor")
        m = {"trang_dang_chay": one("SELECT COUNT(*) n FROM fb_pages WHERE status='active'"),
             "y_tuong_cho_tao": one("SELECT COUNT(*) n FROM fb_pages WHERE status='idea'"),
             "bai_trang_7_ngay": one("SELECT COUNT(*) n FROM posts WHERE fb_page_ref IS NOT NULL AND status='posted' AND posted_at>=?", (_ago(7),)),
             "bai_bo_vi_thieu_anh_7_ngay": one("SELECT COUNT(*) n FROM posts WHERE fb_page_ref IS NOT NULL AND status='rejected' AND created_at>=?", (_ago(7),)),
             "nguoi_viet": 1 + eds}
        m["trang_moi_nguoi_viet"] = round(m["trang_dang_chay"] / m["nguoi_viet"], 1)
    elif dept == "groups":
        per = int(_s().get("mygroups_review_per_run") or 8) + 6 * count("group_scout")
        m = {"nhom_trong_nick": one("SELECT COUNT(DISTINCT group_id) n FROM account_groups"),
             "nhom_chua_danh_gia_7_ngay": one("""SELECT COUNT(DISTINCT ag.group_id) n FROM account_groups ag JOIN groups g ON g.id=ag.group_id
                                               WHERE COALESCE(g.reviewed_at,'') < ?""", (_ago(7),)),
             "danh_gia_moi_luot": per,
             "bai_bi_go_14_ngay": one("SELECT COUNT(*) n FROM posts WHERE permalink_status='removed' AND posted_at>=?", (_ago(14),)),
             "nick_bi_chan_14_ngay": one("SELECT COUNT(*) n FROM fb_accounts WHERE rest_until>=?", (_ago(0),))}
        m["luot_de_xem_het"] = round(m["nhom_chua_danh_gia_7_ngay"] / max(1, per), 1)
    elif dept == "sales":
        m = {"khach_co_sdt_14_ngay": one("SELECT COUNT(*) n FROM leads WHERE phone IS NOT NULL AND phone!='' AND created_at>=?", (_ago(14),)),
             "don_14_ngay": one("SELECT COUNT(*) n FROM orders WHERE created_at>=?", (_ago(14),)),
             "khach_cho_sep_goi": one("SELECT COUNT(*) n FROM leads WHERE status='new' AND phone IS NOT NULL AND phone!=''")}
        try:
            import ceo
            m["so_sale"] = ceo.headcount()["total"]
            p = ceo.potential()
            m["tiem_nang_tuyen_sale"] = p.get("verdict")
            m["_ready"] = bool(p.get("ready"))
        except Exception as e:
            print("[dept]", e)
    elif dept == "director":
        try:
            import company
            f = company.finance()
            m = {"von_con": f["left"], "chi_ai_tb_ngay": f["avg_day"], "von_du_ngay": f["runway_days"], "doanh_thu": f["revenue"]}
        except Exception as e:
            print("[dept]", e)
    return m


def need(dept: str, m: dict | None = None) -> tuple[str | None, str]:
    """Luật số liệu: phòng có thiếu sức làm không → (vị trí nên tuyển, bằng chứng)."""
    m = m or metrics(dept)
    if dept == "website" and m.get("tuan_de_viet_het_tu_khoa", 0) >= 4 and m.get("diem_seo_tb", 0) >= 75 and m.get("bai_cho_duyet", 0) <= 3:
        return "seo_writer", (f"Còn {m['tu_khoa_cho_viet']} từ khóa chờ viết, với {m['bai_moi_tuan']} bài/tuần phải mất {m['tuan_de_viet_het_tu_khoa']} tuần; "
                              f"bài đang đạt SEO trung bình {m['diem_seo_tb']}/100 nên viết thêm vẫn giữ chất lượng")
    if dept == "pages" and m.get("trang_moi_nguoi_viet", 0) > 3:
        return "page_editor", f"{m['trang_dang_chay']} Trang đang chạy mà chỉ {m['nguoi_viet']} người viết ({m['trang_moi_nguoi_viet']} Trang mỗi người)"
    if dept == "groups" and m.get("luot_de_xem_het", 0) >= 3 and m.get("nhom_chua_danh_gia_7_ngay", 0) >= 20:
        return "group_scout", (f"{m['nhom_chua_danh_gia_7_ngay']} nhóm trong nick chưa được đánh giá 7 ngày qua, mỗi lượt chỉ xem "
                               f"{m['danh_gia_moi_luot']} nhóm ({m['luot_de_xem_het']} lượt mới xem hết)")
    if dept == "sales" and m.get("_ready"):
        return "sale", f"Tiềm năng Facebook đủ để thêm người: {m.get('tiem_nang_tuyen_sale') or ''}"
    return None, ""


# ---------------------------------------------------------------- trưởng phòng tự đánh giá
LABEL = {"bai_moi_tuan": "bài/tuần", "bai_viet_14_ngay": "bài viết 14 ngày", "bai_da_dang_14_ngay": "bài đã đăng 14 ngày",
         "diem_seo_tb": "điểm SEO TB", "tu_khoa_cho_viet": "từ khóa chờ viết", "bai_cho_duyet": "bài chờ duyệt",
         "tuan_de_viet_het_tu_khoa": "tuần để viết hết từ khóa", "trang_dang_chay": "Trang đang chạy", "y_tuong_cho_tao": "ý tưởng chờ tạo",
         "bai_trang_7_ngay": "bài Trang 7 ngày", "bai_bo_vi_thieu_anh_7_ngay": "bài bỏ vì thiếu ảnh 7 ngày", "nguoi_viet": "người viết",
         "trang_moi_nguoi_viet": "Trang mỗi người viết", "nhom_trong_nick": "nhóm trong nick", "nhom_chua_danh_gia_7_ngay": "nhóm chưa đánh giá 7 ngày",
         "danh_gia_moi_luot": "nhóm đánh giá mỗi lượt", "bai_bi_go_14_ngay": "bài bị gỡ 14 ngày", "nick_bi_chan_14_ngay": "nick đang nghỉ sau sự cố",
         "luot_de_xem_het": "lượt để xem hết", "khach_co_sdt_14_ngay": "khách có SĐT 14 ngày", "don_14_ngay": "đơn 14 ngày",
         "khach_cho_sep_goi": "khách chờ sếp gọi", "so_sale": "số sale", "tiem_nang_tuyen_sale": "tiềm năng tuyển sale",
         "von_con": "vốn còn", "chi_ai_tb_ngay": "chi AI TB/ngày", "von_du_ngay": "vốn đủ (ngày)", "doanh_thu": "doanh thu"}


def _rule_review(dept: str, m: dict) -> dict:
    pos, ev = need(dept, m)
    show = {k: v for k, v in m.items() if not k.startswith("_")}
    summary = "; ".join(f"{LABEL.get(k, k)}: {v}" for k, v in list(show.items())[:5] if k != "tiem_nang_tuyen_sale")
    return {"summary": summary, "bottleneck": ev or "Chưa thấy nút thắt rõ trong số liệu tuần này",
            "plan": [], "proposals": [{"position": pos, "reason": ev, "expected": POSITIONS[pos]["does"]}] if pos else []}


def review(dept: str) -> dict:
    """Trưởng phòng đánh giá phòng: chỉ số → nút thắt → kế hoạch tuần → (nếu cần) đề xuất tuyển, CEO xét ngay."""
    import workflows
    from llm import llm
    d = DEPTS[dept]
    head = d["head"]
    m = metrics(dept)
    rule = _rule_review(dept, m)
    r = rule
    workflows.set_status(head, "working", f"Đánh giá {d['name']}")
    try:
        if llm.live and dept != "director":
            from agents import system_prompt
            cats = {k: f"{v['title']}: {v['does']}" for k, v in POSITIONS.items() if v["dept"] == dept}
            ask = f"""Đầu tuần, bạn tự đánh giá {d['name']} (mục tiêu: {d['goal']}).
Số liệu thật: {json.dumps({k: v for k, v in m.items() if not k.startswith('_')}, ensure_ascii=False)}
Nhân viên phòng: {', '.join(d['core'])} + {len(staff(dept))} người tuyển thêm.
Vị trí phòng được tuyển: {json.dumps(cats, ensure_ascii=False)}
Luật số liệu của công ty: {('cho thấy nên tuyển ' + POSITIONS[rule['proposals'][0]['position']]['title'] + ' vì ' + rule['proposals'][0]['reason']) if rule['proposals'] else 'chưa thấy phòng thiếu người'}.
Yêu cầu: "summary" 1–2 câu tình hình bằng số; "bottleneck" nút thắt lớn nhất; "plan" đúng 3 việc tuần này (ai làm, đo bằng gì);
"proposals": tối đa 1 đề xuất tuyển, CHỈ khi số liệu chứng minh phòng thiếu sức làm (thiếu người chứ không phải thiếu nick, thiếu ảnh hay
luật Facebook giới hạn), position là mã trong danh sách trên, kèm reason có số và expected. Không đề xuất tăng số bài đăng của nick hay lách luật.
JSON: {{"summary":"...","bottleneck":"...","plan":["..."],"proposals":[{{"position":"...","reason":"...","expected":"..."}}]}}"""
            got = llm.json(system_prompt(head, _s()), ask, mock=None, max_tokens=700, task="learning")
            if isinstance(got, dict) and got.get("summary"):
                r = {"summary": str(got.get("summary"))[:400], "bottleneck": str(got.get("bottleneck") or "")[:300],
                     "plan": [str(x)[:200] for x in (got.get("plan") or [])][:3],
                     "proposals": [p for p in (got.get("proposals") or []) if isinstance(p, dict) and POSITIONS.get(p.get("position"), {}).get("dept") == dept][:1]}
        rid = db.run("INSERT INTO dept_reviews(dept, head, summary, bottleneck, plan, metrics, created_at) VALUES (?,?,?,?,?,?,?)",
                     (dept, head, r["summary"], r["bottleneck"], json.dumps(r["plan"], ensure_ascii=False),
                      json.dumps({k: v for k, v in m.items() if not k.startswith("_")}, ensure_ascii=False), db.now()))
        db.log(head, "Đánh giá phòng", f"{d['name']}: {r['summary'][:200]}")
        out = {"review_id": rid, **r, "decisions": []}
        for p in r["proposals"]:
            out["decisions"].append(propose(dept, p["position"], str(p.get("reason") or ""), str(p.get("expected") or ""), m))
        return out
    finally:
        workflows.set_status(head, "idle", "Đang sẵn sàng")


def propose(dept: str, position: str, reason: str, expected: str = "", m: dict | None = None) -> dict:
    head = DEPTS[dept]["head"]
    if db.one("SELECT id FROM dept_proposals WHERE dept=? AND position=? AND status='pending'", (dept, position)):
        return {"status": "skip", "why": "Đã có đề xuất vị trí này đang chờ"}
    pid = db.run("""INSERT INTO dept_proposals(dept, head, position, reason, expected, status, created_at) VALUES (?,?,?,?,?, 'pending', ?)""",
                 (dept, head, position, reason[:500], expected[:300], db.now()))
    import agents
    db.log(head, "Đề xuất tuyển người", f"{agents.name_of(head)} đề xuất tuyển {POSITIONS[position]['title']}: {reason[:200]}")
    return ceo_decide(pid, m)


def ceo_decide(pid: int, m: dict | None = None) -> dict:
    """CEO xét đề xuất bằng số liệu + vốn; quyền CEO 'tự quyết' thì làm luôn, 'chờ sếp duyệt' thì để sếp bấm."""
    import ceo
    p = db.one("SELECT * FROM dept_proposals WHERE id=?", (pid,))
    pos = POSITIONS[p["position"]]
    no = None
    if pos["max"] is not None and count(p["position"]) >= pos["max"]:
        no = f"{DEPTS[p['dept']]['name']} đã đủ {pos['max']} {pos['title']}"
    if not no:
        n, ev = need(p["dept"], m)
        if n != p["position"]:
            no = "Số liệu chưa chứng minh phòng thiếu người ở vị trí này, làm tốt với người hiện có trước"
    if not no:
        try:
            import company
            run = company.finance()["runway_days"]
            if run is not None and run < ceo.MIN_RUNWAY_DAYS:
                no = f"Vốn chỉ đủ nuôi agent khoảng {run} ngày (cần từ {ceo.MIN_RUNWAY_DAYS} ngày)"
        except Exception as e:
            print("[dept]", e)
    if no:
        _close(pid, "rejected", no)
        return {"status": "rejected", "why": no, "proposal_id": pid}
    if ceo.mode() == "approve":
        db.run("UPDATE dept_proposals SET ceo_note=? WHERE id=?", ("CEO đồng ý, chờ sếp duyệt", pid))
        ceo._tg(f"👔 <b>{DEPTS[p['dept']]['name']} đề xuất tuyển {pos['title']}</b>\n{_e(p['reason'])}\nCEO đồng ý. Sếp duyệt ở mục <b>Phòng ban</b>.")
        return {"status": "pending", "proposal_id": pid}
    return approve(pid, by="ceo")


def _e(t) -> str:
    import html
    return html.escape(str(t or ""))


def _close(pid: int, status: str, note: str, staff_id: int | None = None):
    db.run("UPDATE dept_proposals SET status=?, ceo_note=?, decided_at=?, staff_id=? WHERE id=?", (status, note[:300], db.now(), staff_id, pid))
    p = db.one("SELECT * FROM dept_proposals WHERE id=?", (pid,))
    if status == "rejected":
        db.log("ceo", "Không tuyển", f"{DEPTS[p['dept']]['name']} xin {POSITIONS[p['position']]['title']}: {note}")


def approve(pid: int, by: str = "boss") -> dict:
    p = db.one("SELECT * FROM dept_proposals WHERE id=? AND status='pending'", (pid,))
    if not p:
        raise ValueError("Đề xuất này đã được xử lý")
    pos = POSITIONS[p["position"]]
    if p["position"] == "sale":
        import ceo
        got = ceo.hire(f"{DEPTS['sales']['name']} đề xuất: {p['reason']}", "dept")
        if not got:
            _close(pid, "rejected", "Không tuyển được sale (văn phòng đã đủ chỗ)")
            return {"status": "rejected", "proposal_id": pid}
        _close(pid, "done", "CEO tuyển" if by == "ceo" else "Sếp duyệt")
        return {"status": "done", "proposal_id": pid, "name": got.get("name")}
    used = {r["desk"] for r in staff(p["dept"])}
    desk = next((d for d in DESKS[p["dept"]] if d not in used), None)
    if desk is None:
        _close(pid, "rejected", "Khu làm việc của phòng đã kín bàn")
        return {"status": "rejected", "proposal_id": pid}
    import agents
    taken = {a["name"].lower() for a in agents.public_list()}
    name = next((n for n in random.sample(NAMES, len(NAMES)) if n.lower() not in taken), f"NV{pid}")
    look = dict(random.choice(agents.SALE_LOOKS), shirt=DEPTS[p["dept"]]["color"])
    sid = db.run("INSERT INTO staff(dept, position, name, look, desk, status, hired_at, proposal_id, reason) VALUES (?,?,?,?,?, 'active', ?,?,?)",
                 (p["dept"], p["position"], name, json.dumps(look), desk, db.now(), pid, p["reason"]))
    _close(pid, "done", "CEO tuyển" if by == "ceo" else "Sếp duyệt", sid)
    head = agents.name_of(DEPTS[p["dept"]]["head"])
    db.log("ceo", "Tuyển nhân viên", f"{name} vào {DEPTS[p['dept']]['name']} làm {pos['title']} (đề xuất của {head})")
    import ceo
    ceo._tg(f"🧑‍💼 <b>Tuyển {name} làm {pos['title']}</b> · {DEPTS[p['dept']]['name']}\nĐề xuất của trưởng phòng {_e(head)}: {_e(p['reason'])}\n"
            f"Việc: {_e(pos['does'])}\n" + ("CEO tự quyết theo số liệu và vốn." if by == "ceo" else "Sếp đã duyệt."))
    return {"status": "done", "proposal_id": pid, "staff_id": sid, "name": name}


def reject(pid: int, note: str = "Sếp không duyệt") -> dict:
    _close(pid, "rejected", note)
    return {"status": "rejected"}


def let_go(staff_id: int) -> dict:
    r = db.one("SELECT * FROM staff WHERE id=? AND status='active'", (staff_id,))
    if not r:
        raise ValueError("Không tìm thấy nhân viên")
    db.run("UPDATE staff SET status='left', left_at=? WHERE id=?", (db.now(), staff_id))
    db.log("ceo", "Cho nghỉ việc", f"{r['name']} ({POSITIONS[r['position']]['title']}) rời {DEPTS[r['dept']]['name']}")
    return {"ok": True}


# ---------------------------------------------------------------- nhân viên làm việc thật
def writers(position: str, head: str) -> list[str]:
    return [head] + [f"st-{r['id']}" for r in staff(position=position)]


def writer_for_page(page_id: int) -> str:
    """Bài của Trang nào do ai viết: chia đều các Trang cho Nhi và các Biên tập Trang."""
    w = writers("page_editor", "nhi")
    return w[page_id % len(w)]


def tick(now):
    st = _s()
    if st.get("dept_on", "1") != "1":
        return
    if now.isoweekday() != int(st.get("dept_review_weekday") or 1) or now.strftime("%H:%M") < (st.get("dept_review_time") or "08:40"):
        return
    if st.get("dept_review_last") == db.today():
        return
    db.set_setting("dept_review_last", db.today())
    import threading
    threading.Thread(target=review_all, daemon=True).start()


def review_all() -> list[dict]:
    out = []
    for k in ORDER:
        if k == "director":
            continue
        try:
            out.append({"dept": k, **review(k)})
        except Exception as e:
            import errors
            errors.report_exc("departments", f"{DEPTS[k]['name']} đánh giá lỗi", e, screen="depts")
    return out


def overview() -> dict:
    import agents
    names = {a["id"]: a for a in agents.public_list()}
    out = []
    for k in ORDER:
        d = DEPTS[k]
        mem = [{"id": i, "name": names.get(i, {}).get("name", i), "role": names.get(i, {}).get("role", ""), "head": i == d["head"]} for i in d["core"]]
        mem += [{"id": a["id"], "name": a["name"], "role": a["role"], "staff_id": _sid(a["id"]), "head": False}
                for a in staff_agents() if a["dept"] == k]
        if k == "sales":
            mem += [{"id": a["id"], "name": a["name"], "role": a["role"], "head": False} for a in names.values() if a.get("kind") == "sale"]
        rv = db.one("SELECT * FROM dept_reviews WHERE dept=? ORDER BY id DESC LIMIT 1", (k,))
        if rv:
            rv["plan"] = json.loads(rv["plan"] or "[]")
            rv["metrics"] = json.loads(rv["metrics"] or "{}")
        out.append({"key": k, "name": d["name"], "goal": d["goal"], "color": d["color"], "head": d["head"],
                    "head_name": names.get(d["head"], {}).get("name", d["head"]), "members": mem, "review": rv,
                    "positions": [{"key": p, **v, "have": count(p)} for p, v in POSITIONS.items() if v["dept"] == k],
                    "proposals": db.q("SELECT * FROM dept_proposals WHERE dept=? ORDER BY id DESC LIMIT 5", (k,))})
    st = _s()
    import ceo
    return {"depts": out, "ceo_mode": ceo.mode(),
            "settings": {k: st.get(k, "") for k in ("dept_on", "dept_review_weekday", "dept_review_time")}}

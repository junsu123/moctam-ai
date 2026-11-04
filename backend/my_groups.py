"""Nhóm có sẵn trong nick Facebook: Tuấn rà soát, chọn nhóm đăng, thoát nhóm kém, chăm sóc nhóm mình quản lý.

Sếp chốt:
- Đăng bài vào các nhóm nick ĐÃ THAM GIA SẴN trong tài khoản. Nhóm nick mới vào (do phần mềm xin vào) nghỉ N ngày
  (mặc định 7) rồi mới đăng, tránh bị coi là nick vào nhóm chỉ để spam.
- Mỗi ngày sale mở danh sách nhóm của từng nick (Facebook → Nhóm → Nhóm bạn đã tham gia), phần mềm lưu lại:
  nhóm nào nick là quản trị viên, nhóm nào là thành viên.
- Tuấn đánh giá từng nhóm (khảo sát trang Giới thiệu + bảng tin như khi tìm nhóm mới, cộng thêm kiểm tra nhóm có liên
  quan bán hàng/thực phẩm không): Nên đăng / Đăng ít / Thoát nhóm.
- Tự thoát nhóm không liên quan hoặc tương tác kém (tối đa 3 nhóm/nick/ngày). Không bao giờ thoát: nhóm nick quản lý,
  nhóm đã mang về khách, nhóm sếp bấm "Giữ nhóm".
- Nhóm nick QUẢN LÝ: mỗi ngày đăng 5–10 bài/nhóm (sếp chỉnh được), nửa bài bán hàng đã duyệt, nửa bài chăm sóc nhóm
  (thảo luận, mẹo bán hàng, kiến thức sản phẩm, chào thành viên mới) để nhóm sôi nổi. Bài trong nhóm mình không tính vào
  giới hạn số bài/ngày của nick khi đăng nhóm người khác.
"""
import json
import random
import re
from datetime import datetime, timedelta

import db
from knowledge import plain

REL_RX = re.compile(r"(ban hang|kinh doanh|nguon hang|\bsi\b|si le|buon|online|livestream|\blive\b|shopee|tiktok|lazada|"
                    r"thuc pham|do an|an vat|healthy|eat clean|an kieng|giam can|\btra\b|ca phe|cafe|ngu coc|hat dinh duong|cac loai hat|me bim|me va be|"
                    r"\bcho\b|rao vat|mua ban|dai ly|ctv|cong tac vien|khoi nghiep|order|ship|dac san|nong san|noi tro|nau an|"
                    r"tap hoa|startup|quang cao|ads|marketing|nha phan phoi|tmdt|thuong mai)")
ADMIN_RX = re.compile(r"(cong cu quan tri|admin tools|quan ly nhom|manage group|ban la quan tri vien|you're an admin|"
                      r"thong tin chi tiet ve nhom|group insights|bang dieu khien quan tri|admin home)")
VERDICT_TXT = {"post": "Nên đăng", "keep": "Đăng ít", "leave": "Thoát nhóm", "rest": "Mới vào, đang nghỉ", "manage": "Nhóm mình quản lý",
               "pending": "Chưa rà soát", "left": "Đã thoát"}
SKIP_SLUGS = {"feed", "discover", "joins", "create", "notifications", "search", "you", "learning", "browse"}

LIST_JS = r"""(skip) => {
  const out = []; let admin = false; const seen = new Set();
  const walker = document.createTreeWalker(document.body, NodeFilter.SHOW_ELEMENT);
  for (let el = walker.currentNode; el; el = walker.nextNode()) {
    const tag = el.tagName;
    if (/^H[1-4]$/.test(tag) || el.getAttribute('role') === 'heading') {
      const t = (el.innerText || '').trim().toLowerCase();
      if (/quản lý|bạn quản lý|you manage|do bạn quản lý/.test(t)) admin = true;
      else if (/đã tham gia|you've joined|you have joined|nhóm của bạn|tham gia/.test(t)) admin = false;
      continue;
    }
    if (tag !== 'A') continue;
    const m = (el.href || '').match(/\/groups\/([^/?#]+)/); if (!m) continue;
    const slug = decodeURIComponent(m[1]); if (skip.includes(slug.toLowerCase())) continue;
    const name = (el.innerText || '').trim().split('\n')[0];
    if (!name || name.length < 3 || /^(xem nhóm|view group|truy cập)/i.test(name)) continue;
    if (seen.has(slug)) { if (admin) { const o = out.find(x => x.slug === slug); if (o) o.admin = true; } continue; }
    seen.add(slug); out.push({slug, name, admin});
  }
  return out;
}"""


def s() -> dict:
    return db.get_settings()


def _base() -> str:
    import browser_poster as B
    return B.FB_BASE


def slug_of(url: str) -> str:
    m = re.search(r"/groups/([^/?#]+)", url or "")
    return m.group(1).lower() if m else ""


def group_url(slug: str) -> str:
    return f"{_base()}/groups/{slug}"


# ---------------------------------------------------------------- đăng vào nhóm nào được
def rest_until(j: dict) -> datetime | None:
    """Nhóm nick mới vào: ngày được đăng bài đầu tiên."""
    if (j.get("origin") or "") != "app" or not j.get("joined_at"):
        return None
    t = datetime.strptime(j["joined_at"][:19], "%Y-%m-%d %H:%M:%S") + timedelta(days=int(s().get("new_group_rest_days") or 7))
    return t if t > db.clock() else None


def membership(g: dict, aid: int) -> str:
    """'ok' (đăng được), 'rest' (mới vào, đang nghỉ), 'leave' (Tuấn cho thoát), 'no' (nick không ở nhóm), 'unknown'."""
    j = db.one("SELECT * FROM account_groups WHERE group_id=? AND account_id=?", (g["id"], aid))
    if j and j["status"] == "joined":
        if j.get("verdict") == "leave" and not g.get("pinned"):
            return "leave"
        return "rest" if rest_until(j) else "ok"
    acc = db.one("SELECT groups_synced_at FROM fb_accounts WHERE id=?", (aid,))
    if acc and acc.get("groups_synced_at"):
        return "no"  # đã đọc danh sách nhóm thật của nick: chỉ đăng nhóm nick đang ở
    return "unknown"


# ---------------------------------------------------------------- đọc danh sách nhóm của nick
def list_groups(page) -> list[dict]:
    import browser_poster as B
    page.goto(f"{_base()}/groups/joins/?nav_source=tab", wait_until="domcontentloaded", timeout=60000)
    page.wait_for_timeout(int(random.uniform(3.5, 6) * 1000))
    B._check_blocked(page)
    last = -1
    for _ in range(12):  # danh sách dài: cuộn tới khi không thêm nhóm mới
        rows = page.evaluate(LIST_JS, sorted(SKIP_SLUGS))
        if len(rows) == last:
            break
        last = len(rows)
        page.mouse.wheel(0, random.randint(1500, 2200))
        page.wait_for_timeout(int(random.uniform(1.5, 3) * 1000))
    return page.evaluate(LIST_JS, sorted(SKIP_SLUGS))


def find_group(slug: str) -> dict | None:
    r = db.one("SELECT * FROM groups WHERE slug=?", (slug,))
    if r:
        return r
    for g in db.q("SELECT * FROM groups WHERE COALESCE(url,'')!=''"):
        if slug_of(g["url"]) == slug:
            db.run("UPDATE groups SET slug=? WHERE id=?", (slug, g["id"]))
            return g
    return None


def upsert(aid: int, rows: list[dict]) -> dict:
    """Lưu danh sách nhóm của nick. Nhóm có sẵn trong nick (không do phần mềm xin vào) đăng được ngay."""
    import group_finder
    now = db.now()
    res = {"total": len(rows), "admin": 0, "new": 0, "gone": 0}
    seen = set()
    for r in rows:
        slug = r["slug"].lower()
        seen.add(slug)
        g = find_group(slug)
        if not g:
            gid = db.run("""INSERT INTO groups(name, url, slug, topic, members, rules, min_days_between_posts, note, created_at, source)
                            VALUES (?,?,?,?,0,'',?,?,?,'account')""",
                         (r["name"][:150], group_url(slug), slug, "Nhóm có sẵn trong nick", 2,
                          "Nhóm nick đã tham gia sẵn trên Facebook", now, ))
            g = db.one("SELECT * FROM groups WHERE id=?", (gid,))
            res["new"] += 1
        j = db.one("SELECT * FROM account_groups WHERE group_id=? AND account_id=?", (g["id"], aid))
        if not j or j["status"] != "joined":
            # phần mềm từng xin vào nhóm này (đang chờ duyệt) -> nhóm mới vào, phải nghỉ; còn lại là nhóm có sẵn trong nick
            origin = "app" if (j and j["status"] == "requested") else "existing"
            group_finder.set_join(g["id"], aid, "joined", "Có trong danh sách nhóm của nick", origin=origin)
        role = "admin" if r.get("admin") else (j or {}).get("role") or "member"
        db.run("UPDATE account_groups SET role=?, seen_at=? WHERE group_id=? AND account_id=?", (role, now, g["id"], aid))
        if role == "admin":
            res["admin"] += 1
            db.run("UPDATE groups SET managed=1 WHERE id=?", (g["id"],))
    # nhóm nick không còn ở (tự rời, bị xóa khỏi nhóm): bỏ khỏi danh sách đăng của nick
    for j in db.q("""SELECT j.group_id, g.url, g.slug FROM account_groups j JOIN groups g ON g.id=j.group_id
                     WHERE j.account_id=? AND j.status='joined'""", (aid,)):
        if (j["slug"] or slug_of(j["url"])) not in seen and rows:
            group_finder.set_join(j["group_id"], aid, "none", "Không còn trong danh sách nhóm của nick")
            res["gone"] += 1
    db.run("UPDATE fb_accounts SET groups_synced_at=? WHERE id=?", (now, aid))
    _sync_managed()
    return res


def _sync_managed():
    db.run("""UPDATE groups SET managed = CASE WHEN EXISTS (SELECT 1 FROM account_groups j WHERE j.group_id=groups.id
              AND j.role='admin' AND j.status='joined') THEN 1 ELSE 0 END""")


# ---------------------------------------------------------------- Tuấn đánh giá
def relevance(g: dict) -> float:
    return 1.0 if REL_RX.search(plain(f"{g.get('name') or ''} {g.get('topic') or ''} {g.get('rules_note') or ''}")) else 0.0


def decide(g: dict, j: dict, ev: dict | None) -> tuple[str, str]:
    """Quyết định của Tuấn cho một nick trong một nhóm."""
    if j.get("role") == "admin":
        return "manage", "Nick là quản trị viên: chăm sóc nhóm, đăng đều mỗi ngày"
    if not ev:
        return "pending", ""
    note = ev["reasons"]
    if ev["verdict"] == "skip":
        if g.get("pinned"):
            return "keep", "Sếp giữ nhóm. " + note
        if int(g.get("leads_count") or 0) > 0:
            return "keep", f"Nhóm đã mang về {g['leads_count']} khách nên giữ lại. " + note
        return "leave", note
    if rest_until(j):
        return "rest", f"Nick mới vào nhóm, nghỉ đến {rest_until(j).strftime('%d/%m')} rồi mới đăng. " + note
    return ("post" if ev["verdict"] == "join" else "keep"), note


def review(g: dict, m: dict | None = None) -> dict:
    import group_finder
    import group_review
    if m:
        group_finder._save_metrics("groups", g["id"], m)
        g = db.one("SELECT * FROM groups WHERE id=?", (g["id"],))
    rel = relevance(g)
    ev = group_review.evaluate({**g, "relevance": rel})
    if rel <= 0:
        ev["reasons"] = "Loại: nhóm không liên quan bán hàng, nguồn hàng hay thực phẩm" + (
            "; " + ev["reasons"].removeprefix("Loại: ") if ev["reasons"].startswith("Loại:") and "không khớp chủ đề" not in ev["reasons"] else "")
        ev["reasons"] = ev["reasons"].replace("; tên nhóm không khớp chủ đề đang tìm", "")
    group_review._save("groups", g["id"], ev)
    return ev


def apply_decisions(aid: int | None = None):
    """Cập nhật quyết định của Tuấn cho mọi (nick, nhóm) theo đánh giá nhóm mới nhất."""
    sql = "SELECT group_id, account_id FROM account_groups WHERE status='joined'"
    rows = db.q(sql + (" AND account_id=?" if aid else ""), (aid,) if aid else ())
    for r in rows:
        gv = db.one("SELECT verdict, review_note, eng_score, reviewed_at FROM groups WHERE id=?", (r["group_id"],))
        ev = {"verdict": gv["verdict"], "reasons": gv["review_note"] or ""} if gv and gv["reviewed_at"] else None
        j = db.one("SELECT * FROM account_groups WHERE group_id=? AND account_id=?", (r["group_id"], r["account_id"]))
        g = db.one("SELECT * FROM groups WHERE id=?", (r["group_id"],))
        v, note = decide(g, j, ev)
        db.run("UPDATE account_groups SET verdict=?, verdict_note=? WHERE group_id=? AND account_id=?",
               (v, note[:600], r["group_id"], r["account_id"]))


def is_admin_page(page) -> bool:
    try:
        return bool(ADMIN_RX.search(plain(page.inner_text("body")[:8000])))
    except Exception:
        return False


# ---------------------------------------------------------------- thoát nhóm
LEAVE_BTN = ["Đã tham gia", "Joined", "Thành viên"]
LEAVE_ITEM = ["Rời nhóm", "Leave group", "Leave Group", "Rời khỏi nhóm"]


def leave_group(page, url: str) -> tuple[bool, str]:
    import browser_poster as B
    page.goto(B.fb_url(url), wait_until="domcontentloaded", timeout=60000)
    page.wait_for_timeout(int(random.uniform(3, 5) * 1000))
    B._check_blocked(page)
    if is_admin_page(page):
        return False, "nick là quản trị viên nhóm này, không tự thoát"
    if not B._wait_click(page, LEAVE_BTN, timeout=12):
        return False, "không thấy nút Đã tham gia (có thể nick đã rời nhóm)"
    page.wait_for_timeout(int(random.uniform(1, 2) * 1000))
    if not (B._wait_click(page, LEAVE_ITEM, timeout=8, role="menuitem")):
        return False, "không thấy mục Rời nhóm"
    page.wait_for_timeout(int(random.uniform(1, 2) * 1000))
    dlg = page.locator('[role="dialog"]').last
    btn = B._visible_first(dlg, LEAVE_ITEM, "button") if dlg.count() else None
    if not btn:
        return False, "không thấy nút xác nhận Rời nhóm"
    btn.click()
    page.wait_for_timeout(int(random.uniform(2.5, 4) * 1000))
    return True, ""


def leaves_today(aid: int) -> int:
    return db.one("SELECT COUNT(*) n FROM account_groups WHERE account_id=? AND left_at LIKE ?", (aid, db.today() + "%"))["n"]


# ---------------------------------------------------------------- việc của sale trên trình duyệt
def job_sync(pw, aid: int, notify: str | None = None, only_leave: list[int] | None = None):
    """Sale mở danh sách nhóm của nick, Tuấn rà soát vài nhóm, rồi thoát nhóm kém (nếu sếp bật tự thoát)."""
    import browser_poster as B
    import group_finder
    import workflows
    acc, sale, agent = B._ctx_names(aid)
    ctx, page = B._open(pw, aid)
    res = {"list": None, "reviewed": [], "left": [], "leave_fail": []}
    try:
        if not B._logged_in(ctx):
            raise RuntimeError("Nick chưa đăng nhập. Vào Nhân viên sale → Mở Chrome để đăng nhập lại")
        if not only_leave:
            workflows.set_status(agent, "working", f"Mở danh sách nhóm của nick {acc['name']}")
            workflows.set_status("tuan", "working", f"Rà soát nhóm trong nick {acc['name']}")
            rows = list_groups(page)
            if rows:
                res["list"] = upsert(aid, rows)
            n = int(s().get("mygroups_review_per_run") or 8)
            todo = db.q("""SELECT g.*, j.role FROM account_groups j JOIN groups g ON g.id=j.group_id
                           WHERE j.account_id=? AND j.status='joined' AND (g.reviewed_at IS NULL OR g.reviewed_at < ?)
                           ORDER BY (j.role='admin') DESC, g.reviewed_at IS NOT NULL, COALESCE(g.reviewed_at,'') LIMIT ?""",
                        (aid, (db.clock() - timedelta(days=7)).strftime("%Y-%m-%d %H:%M:%S"), n))
            for g in todo:
                workflows.set_status(agent, "working", f"Xem nhóm {g['name'][:40]} cho Tuấn")
                try:
                    m = group_finder.scout(page, g["url"])
                    if is_admin_page(page):
                        db.run("UPDATE account_groups SET role='admin' WHERE group_id=? AND account_id=?", (g["id"], aid))
                        db.run("UPDATE groups SET managed=1 WHERE id=?", (g["id"],))
                except B.Blocked:
                    raise
                except Exception as e:
                    print("[my_groups scout]", g["url"], e)
                    m = {"scouted_at": db.now(), "sampled_posts": 0}
                ev = review(g, m)
                res["reviewed"].append({"name": g["name"], **ev})
                B._pause(page, 5, 12)
            apply_decisions(aid)
        # thoát nhóm
        if s().get("auto_leave", "1") == "1" or only_leave:
            cap = int(s().get("leave_per_nick_day") or 3)
            q = """SELECT g.*, j.verdict_note FROM account_groups j JOIN groups g ON g.id=j.group_id WHERE j.account_id=?
                   AND j.status='joined' AND j.verdict='leave' AND COALESCE(g.pinned,0)=0 AND COALESCE(j.role,'member')!='admin'"""
            rows = db.q(q + (f" AND g.id IN ({','.join('?' * len(only_leave))})" if only_leave else "") + " ORDER BY g.eng_score",
                        (aid, *(only_leave or [])))
            for g in rows[:max(0, cap - leaves_today(aid)) if not only_leave else len(rows)]:
                workflows.set_status(agent, "working", f"Thoát nhóm {g['name'][:40]} theo đánh giá của Tuấn")
                try:
                    ok, why = leave_group(page, g["url"])
                except B.Blocked:
                    raise
                except Exception as e:
                    ok, why = False, str(e)[:120]
                if ok:
                    group_finder.set_join(g["id"], aid, "left", "Tuấn cho thoát: " + (g["verdict_note"] or "")[:150])
                    db.run("UPDATE account_groups SET left_at=?, verdict='left' WHERE group_id=? AND account_id=?",
                           (db.now(), g["id"], aid))
                    res["left"].append(g)
                else:
                    res["leave_fail"].append((g, why))
                B._pause(page, 6, 14)
    except B.Blocked as e:
        B._block(aid, str(e))
    finally:
        try:
            ctx.close()
        except Exception:
            pass
        workflows.set_status(agent, "idle", "Chờ việc tiếp theo")
        workflows.set_status("tuan", "idle", "Xong rà soát nhóm")
    _report(acc, res, notify)
    try:
        plan_admin()  # có nhóm quản lý mới phát hiện: xếp bài chăm sóc ngay
    except Exception as e:
        print("[plan_admin]", e)
    return res


def _report(acc: dict, res: dict, notify: str | None):
    parts = []
    L = res.get("list")
    if L:
        parts.append(f"nick {acc['name']} đang ở {L['total']} nhóm ({L['admin']} nhóm quản lý"
                     + (f", {L['new']} nhóm mới ghi nhận" if L["new"] else "") + (f", {L['gone']} nhóm không còn" if L["gone"] else "") + ")")
    if res["reviewed"]:
        cnt = {}
        for r in res["reviewed"]:
            cnt[r["verdict"]] = cnt.get(r["verdict"], 0) + 1
        parts.append(f"đánh giá {len(res['reviewed'])} nhóm: nên đăng {cnt.get('join', 0)}, đăng ít {cnt.get('consider', 0)}, "
                     f"không đạt {cnt.get('skip', 0)}")
    if res["left"]:
        parts.append("đã thoát " + ", ".join(f"{g['name'][:40]} ({(g['verdict_note'] or '').removeprefix('Loại: ')[:70]})"
                                             for g in res["left"]))
    if res["leave_fail"]:
        parts.append(f"chưa thoát được {len(res['leave_fail'])} nhóm ({res['leave_fail'][0][1]})")
    if not parts:
        parts.append(f"chưa đọc được danh sách nhóm của nick {acc['name']}")
    msg = "Tuấn rà soát nhóm: " + "; ".join(parts) + "."
    db.log("tuan", "Rà soát nhóm của nick", msg[:700])
    if res["left"]:
        db.log("tuan", "Thoát nhóm", f"Nick {acc['name']} thoát {len(res['left'])} nhóm không liên quan hoặc tương tác kém")
    if notify:
        import ceo_orders
        ceo_orders.followup(msg, notify)


def start_sync(notify: str | None = None, aids: list[int] | None = None) -> int:
    import browser_poster as B
    import group_finder
    n = 0
    for a in group_finder._working_accounts():
        if aids and a["id"] not in aids:
            continue
        B.submit(a["sale_id"], {"kind": "mygroups", "account": a["id"], "notify": notify})
        n += 1
    return n


def leave_now(gid: int, aid: int) -> None:
    import browser_poster as B
    acc = db.one("SELECT * FROM fb_accounts WHERE id=?", (aid,))
    if not acc:
        raise ValueError("Không tìm thấy nick")
    db.run("UPDATE account_groups SET verdict='leave', verdict_note=COALESCE(verdict_note,'') || ' (sếp bấm thoát)' "
           "WHERE group_id=? AND account_id=?", (gid, aid))
    B.submit(acc["sale_id"], {"kind": "mygroups", "account": aid, "leave": [gid]})


# ---------------------------------------------------------------- chăm sóc nhóm mình quản lý
CARE = [
    "💬 THẢO LUẬN HÔM NAY\nCác shop đang bán {cat} online: dạo này kênh nào ra đơn tốt nhất với mọi người, livestream, chạy quảng cáo hay đăng nhóm? Chia sẻ để cả nhóm học hỏi nhé 👇",
    "👋 CHÀO MỪNG THÀNH VIÊN MỚI\nCảm ơn các bạn đã tham gia nhóm! Mọi người giới thiệu ngắn: shop mình đang bán gì, bán ở kênh nào, để các thành viên kết nối với nhau nhé 👇",
    "❓ HỎI NHANH\nKhách của các shop thích {cat} vị gì nhất? Mua để dùng hằng ngày hay làm quà? Bình luận để nhóm tổng hợp xu hướng tuần này nhé.",
    "📌 MẸO BÁN HÀNG\n{tip}\n\nCác shop có mẹo nào hay, chia sẻ thêm dưới bình luận nha.",
    "📚 GÓC KIẾN THỨC SẢN PHẨM\n{fact}\n\nAi đang bán dòng này có thể lưu lại để tư vấn khách.",
    "🗳️ BÌNH CHỌN\nTuần này các shop muốn nhóm chia sẻ chủ đề nào?\n1. Cách livestream bán đồ uống, ngũ cốc\n2. Cách chụp ảnh sản phẩm bằng điện thoại\n3. Cách tính giá bán lẻ để có lãi\nBình luận số 1, 2 hoặc 3 nhé!",
    "🤝 GÓC KẾT NỐI\nShop nào đang cần nguồn {cat}, hoặc đang tìm cộng tác viên bán cùng, để lại bình luận để mọi người hỗ trợ nhau nhé.",
    "🔥 CÂU CHUYỆN BÁN HÀNG\nĐơn hàng đáng nhớ nhất của bạn tuần này là gì? Khách khó tính, khách quay lại lần 3 hay đơn sỉ đầu tiên? Kể nghe với 😄",
    "📷 THỬ THÁCH CUỐI TUẦN\nĐăng 1 tấm ảnh sản phẩm bạn chụp đẹp nhất tuần này dưới bình luận. Nhóm sẽ góp ý cách chụp để ảnh bán hàng hút khách hơn.",
    "💡 HỎI ĐÁP\nBạn đang gặp khó khăn gì khi bán {cat} online: tìm khách, giữ khách, hay tính giá? Viết câu hỏi dưới bình luận, admin và các thành viên sẽ trả lời.",
    "📅 LỊCH NHÓM\nMỗi ngày nhóm có bài chủ đề riêng: sáng chia sẻ kinh nghiệm, trưa hỏi đáp, tối kết nối mua bán. Mọi người đăng đúng chủ đề để nhóm gọn gàng nhé ❤️",
    "✅ NHẮC NỘI QUY\nNhóm ưu tiên bài chia sẻ thật, ảnh thật, không spam link. Bài rao bán vui lòng ghi rõ sản phẩm và khu vực. Cảm ơn cả nhà đã cùng giữ nhóm chất lượng!",
]


def _cats() -> list[str]:
    cats = [r["category"].lower() for r in db.q("SELECT DISTINCT category FROM products WHERE COALESCE(category,'')!=''")]
    return cats or ["trà túi lọc", "ngũ cốc"]


def _tips() -> list[str]:
    rows = db.q("""SELECT content FROM knowledge WHERE status='active' AND agent_id IN ('lan','ha')
                   AND LENGTH(content) BETWEEN 60 AND 420 ORDER BY RANDOM() LIMIT 20""")
    return [r["content"] for r in rows] or ["Ảnh thật, video pha thử và giá rõ ràng giúp khách tin và chốt nhanh hơn ảnh mạng."]


def _facts() -> list[str]:
    rows = db.q("SELECT name, description FROM products WHERE COALESCE(description,'')!='' ORDER BY hot DESC, RANDOM() LIMIT 10")
    return [f"{r['name']}: {r['description']}" for r in rows] or ["Trà túi lọc tiện pha, hợp dân văn phòng; ngũ cốc hợp bữa sáng nhanh."]


def care_posts(g: dict, n: int) -> list[str]:
    """Bài chăm sóc nhóm (không bán hàng). Có khóa Claude: Lan viết mới; chưa có: Lan ghép từ mẫu + sổ kiến thức + sản phẩm."""
    if n <= 0:
        return []
    recent = {plain(r["content"] or "")[:80] for r in db.q(
        "SELECT content FROM posts WHERE group_id=? AND managed=1 AND created_at >= ?",
        (g["id"], (db.clock() - timedelta(days=14)).strftime("%Y-%m-%d")))}
    out: list[str] = []
    from llm import llm
    if llm.live and s().get("admin_care_ai", "1") == "1":
        try:
            from agents import system_prompt
            data = llm.json(system_prompt("lan", s()),
                            f"Viết {n} bài đăng KHÁC NHAU để chăm sóc nhóm Facebook “{g['name']}” do xưởng quản lý (thành viên là người "
                            f"bán hàng online). Mỗi bài 40–90 chữ, mở bằng 1 emoji và tiêu đề viết hoa, kêu gọi bình luận. Loại bài: "
                            "thảo luận, hỏi đáp, mẹo bán hàng online, kiến thức sản phẩm (trà, ngũ cốc), chào thành viên mới, bình chọn. "
                            "KHÔNG rao bán, không ghi giá, không hứa công dụng chữa bệnh. Trả JSON {\"posts\": [\"...\"]}.",
                            mock=None, max_tokens=300 * n, task="posts")
            out = [p.strip() for p in (data or {}).get("posts", []) if isinstance(p, str) and len(p.strip()) > 30]
        except Exception as e:
            print("[care ai]", e)
    rnd = random.Random(f"{db.today()}-{g['id']}")
    pool = CARE[:]
    rnd.shuffle(pool)
    tips, facts, cats = _tips(), _facts(), _cats()
    for tpl in pool * 2:
        if len(out) >= n:
            break
        txt = tpl.format(cat=rnd.choice(cats), tip=rnd.choice(tips), fact=rnd.choice(facts))
        if plain(txt)[:80] in recent or txt in out:
            continue
        out.append(txt)
    from ceo_orders import REVIEW_BAD
    return [t for t in out if not REVIEW_BAD.search(t)][:n]


def target_today(gid: int) -> int:
    lo = int(s().get("admin_posts_min") or 5)
    hi = max(lo, int(s().get("admin_posts_max") or 10))
    return random.Random(f"{db.today()}-{gid}").randint(lo, hi)


def admin_pairs() -> list[dict]:
    """Mỗi nhóm mình quản lý: chọn 1 nick quản trị đang làm việc để đăng."""
    import accounts
    accs = {a["id"]: a for a in accounts.working()}
    out, seen = [], set()
    for r in db.q("""SELECT j.group_id, j.account_id, g.name, g.url FROM account_groups j JOIN groups g ON g.id=j.group_id
                     WHERE j.role='admin' AND j.status='joined' AND COALESCE(g.url,'')!='' ORDER BY j.group_id, j.account_id"""):
        if r["group_id"] in seen or r["account_id"] not in accs:
            continue
        seen.add(r["group_id"])
        out.append({**r, "acc": accs[r["account_id"]]})
    return out


def done_today(gid: int) -> int:
    return db.one("""SELECT COUNT(*) n FROM posts WHERE group_id=? AND managed=1 AND status IN ('scheduled','posting','posted')
                     AND COALESCE(posted_at, scheduled_for) LIKE ?""", (gid, db.today() + "%"))["n"]


def _today_rows(gid: int) -> list[dict]:
    return db.q("""SELECT COALESCE(source,'') source, COALESCE(posted_at, scheduled_for) t FROM posts WHERE group_id=? AND managed=1
                   AND status IN ('scheduled','posting','posted') AND COALESCE(posted_at, scheduled_for) LIKE ?""",
                (gid, db.today() + "%"))


def plan_admin() -> list[dict]:
    """Xếp bài cho nhóm mình quản lý: đủ 5–10 bài/ngày/nhóm, rải đều trong khung giờ của nick quản trị.
    Sếp chốt: chỉ đăng bài tìm khách sỉ / gia công theo mẫu của sếp (mỗi bài một biến thể), không đăng bài linh tinh."""
    if s().get("mygroups_enabled", "1") != "1":
        return []
    import workflows
    now, today = db.clock(), db.today()
    plan = []
    for p in admin_pairs():
        gid, acc = p["group_id"], p["acc"]
        target = target_today(gid)
        rows = _today_rows(gid)
        need = target - len(rows)
        if need <= 0:
            continue
        start = max(now + timedelta(minutes=5), datetime.strptime(f"{today} {acc['active_from'] or '08:00'}", "%Y-%m-%d %H:%M"))
        end = datetime.strptime(f"{today} {acc['active_to'] or '22:00'}", "%Y-%m-%d %H:%M")
        if start >= end:
            continue
        need = min(need, int((end - start).total_seconds() // (30 * 60)) + 1)  # chỉ làm số bài còn kịp đăng hôm nay
        import post_template
        src_sql = " AND source='template'" if post_template.enabled() else ""
        items = db.q(f"SELECT * FROM posts WHERE status='approved' AND target_type='group'{src_sql} ORDER BY id LIMIT ?", (need,))
        if len(items) < need and post_template.enabled():  # Lan làm thêm bài theo mẫu của sếp cho đủ chỉ tiêu
            items += post_template.make_posts(need - len(items))
        if not items:
            continue
        taken = [datetime.strptime(r["t"][:16], "%Y-%m-%d %H:%M") for r in rows if r["t"]]
        step = (end - start) / need
        slots = [start + step * i for i in range(need)]
        made = 0
        for i, it in enumerate(items):
            t = slots[i * need // len(items)] + timedelta(minutes=random.randint(0, 8))
            while any(abs((t - x).total_seconds()) < 25 * 60 for x in taken):  # cách bài khác trong nhóm ít nhất 25 phút
                t += timedelta(minutes=25)
            if t > end:
                break
            taken.append(t)
            when = t.strftime("%Y-%m-%d %H:%M")
            if isinstance(it, dict):
                db.run("""UPDATE posts SET sale_id=?, account_id=?, group_id=?, scheduled_for=?, status='scheduled', managed=1,
                          error=NULL WHERE id=?""", (acc["sale_id"], acc["id"], gid, when, it["id"]))
            else:
                db.run("""INSERT INTO posts(agent_id, target_type, group_id, angle, title, content, hashtags, status, scheduled_for,
                          sale_id, account_id, managed, source, created_at, bump_enabled) VALUES ('lan','group',?,'cham_soc',?,?,'',
                          'scheduled',?,?,?,1,'care',?,0)""",
                       (gid, it.split("\n")[0][:80], it, when, acc["sale_id"], acc["id"], db.now()))
            made += 1
        if made:
            plan.append({"group": p["name"], "account": acc["name"], "count": made, "target": target,
                         "sell": sum(isinstance(x, dict) for x in items[:made])})
    if plan:
        db.log("lan", "Chăm sóc nhóm quản lý", "; ".join(
            f"{x['group'][:40]}: xếp thêm {x['count']} bài tìm khách sỉ theo mẫu (mục tiêu {x['target']} bài/ngày, nick {x['account']})" for x in plan))
        workflows.set_status("lan", "idle", "Đã xếp bài chăm sóc nhóm quản lý")
    return plan


def admin_sell_need() -> int:
    """Số bài bán hàng Lan cần viết thêm cho nhóm quản lý hôm nay (phần còn lại là bài chăm sóc nhóm)."""
    import post_template
    if post_template.enabled():
        return 0  # nhóm quản lý đăng bài theo mẫu của sếp, Lan làm ngay khi xếp lịch
    share = max(0, min(100, int(s().get("admin_sell_share") or 50))) / 100
    return sum(max(0, round(target_today(p["group_id"]) * share) - sum(r["source"] != "care" for r in _today_rows(p["group_id"])))
               for p in admin_pairs())


# ---------------------------------------------------------------- lịch
def tick(now: datetime):
    st = s()
    if st.get("mygroups_enabled", "1") != "1":
        return
    if st.get("mygroups_last") != db.today() and now.strftime("%H:%M") >= (st.get("mygroups_time") or "09:15"):
        db.set_setting("mygroups_last", db.today())
        start_sync()
    if now.minute % 30 == 0 and now.second < 30 and now.hour >= 7:  # nửa giờ một lần: bù bài cho nhóm quản lý
        try:
            plan_admin()
        except Exception as e:
            print("[plan_admin]", e)


# ---------------------------------------------------------------- giao diện
def overview() -> dict:
    import accounts
    rows = db.q("""SELECT j.group_id, j.account_id, j.status, j.role, j.origin, j.joined_at, j.verdict, j.verdict_note, j.left_at,
                   g.name, g.url, g.members, g.eng_score, g.review_note, g.reviewed_at, g.pinned, g.leads_count, g.posts_today,
                   g.posts_month, g.avg_reactions, g.avg_comments, g.sampled_posts, a.name nick, s.name sale
                   FROM account_groups j JOIN groups g ON g.id=j.group_id JOIN fb_accounts a ON a.id=j.account_id
                   JOIN sales s ON s.id=a.sale_id WHERE j.status IN ('joined','left') AND COALESCE(s.is_sample,0)=0
                   ORDER BY (j.role='admin') DESC, j.status='left', COALESCE(g.eng_score,-1) DESC""")
    for r in rows:
        r["rest_until"] = (lambda x: x.strftime("%Y-%m-%d") if x else None)(rest_until(r)) if r["status"] == "joined" else None
        r["verdict"] = "left" if r["status"] == "left" else (r["verdict"] or "pending")
        if r["role"] == "admin" and r["status"] == "joined":
            r["today"] = done_today(r["group_id"])
            r["target"] = target_today(r["group_id"])
    cnt = {}
    for r in rows:
        cnt[r["verdict"]] = cnt.get(r["verdict"], 0) + 1
    nicks = []
    for a in accounts.working():
        mine = [r for r in rows if r["account_id"] == a["id"] and r["status"] == "joined"]
        nicks.append({"id": a["id"], "name": a["name"], "sale": a["sale_name"], "synced_at": a.get("groups_synced_at"),
                      "groups": len(mine), "admin": sum(r["role"] == "admin" for r in mine),
                      "post": sum(r["verdict"] in ("post", "keep") for r in mine), "leave": sum(r["verdict"] == "leave" for r in mine),
                      "left_today": leaves_today(a["id"])})
    return {"items": rows, "counts": cnt, "nicks": nicks, "verdicts": VERDICT_TXT,
            "settings": {k: v for k, v in s().items() if k in ("mygroups_enabled", "mygroups_time", "auto_leave", "leave_per_nick_day",
                                                              "new_group_rest_days", "mygroups_review_per_run", "admin_posts_min",
                                                              "admin_posts_max", "admin_sell_share")},
            "last": db.one("SELECT detail, created_at FROM activity WHERE action='Rà soát nhóm của nick' ORDER BY id DESC LIMIT 1")}

"""Lướt bảng tin nhóm (facebook.com/groups/feed/): mỗi nick đọc ít nhất 20 bài của các nhóm nick đang ở, Bảo lọc 3 lớp và
viết sẵn bình luận CHỜ SẾP DUYỆT, rồi nick gửi theo nhịp của replies.py (giờ làm, giãn cách 45–90 phút, trần mỗi ngày).

Hai loại bài được bình luận:
- buyer: người đang HỎI MUA / hỏi nguồn hàng hợp ngành -> câu trả lời + 1 ảnh ngẫu nhiên trong thư mục ảnh + dòng Zalo.
- seller: người đang BÁN HÀNG ONLINE hỏi chuyện khác (tài khoản quảng cáo, chạy ads, livestream...) -> chỉ chữ, chào nhẹ
  bám vào điều họ viết + dòng Zalo. Bị báo cáo nhiều hơn nên: luôn chờ duyệt, trần riêng thấp (mặc định 2/nick/ngày),
  mỗi người chỉ một nick chào một lần, không chào ở nhóm cấm bán hàng, nhóm từng xóa bình luận chào thì ngừng 30 ngày.
- general (bật “Bình luận mọi bài”, mặc định bật): mọi bài còn lại trong nhóm, không cần từ khóa liên quan -> Claude viết
  bình luận đúng nội dung bài, giới thiệu nhẹ là xưởng + dòng Zalo (nhóm cấm bán hàng / từng xóa bình luận: không kèm Zalo).
  Chia đều theo nhóm: nhóm ít được bình luận nhất được ưu tiên; bình luận theo nhóm chỉ thêm khi nhóm chưa đủ
  feed_per_group_day câu/ngày (người hỏi mua, người bán online vẫn theo trần riêng của chúng).
Không bình luận: bài của nhà cung cấp khác / bán dịch vụ, người trong danh sách data rác, nhóm sếp đã loại.
Số lượt lướt mỗi ngày do luật Facebook của nick quyết định (plan), không chạy ban đêm.
"""
import random
import re
from datetime import datetime, timedelta

import db
import junk
from knowledge import plain

SELLER_RX = re.compile(r"(tai khoan quang cao|\btkqc\b|chay (ads|quang cao|qc)\b|\bads\b|quang cao (facebook|fb|tiktok)|"
                       r"\bbm\b|\bvia\b|ngan sach|livestream|\blive\b|len don|chot don|ra don|ship cod|ban hang online|ban online|"
                       r"\bshop (minh|em|toi|nha)|tiktok shop|shopee|lazada|nguon hang|\bctv\b|dropship|don hang|tep khach)")
ASK_RX = re.compile(r"(\bai (co|biet|giup|chi|tung|da)\b|bao nhieu|duoc khong|sao (vay|a|nhi)\b|moi nguoi oi|cho (minh|em|toi|chi|anh) hoi|\bhoi (chut|ve|xiu|cac|moi)\b|"
                    r"xin (y kien|kinh nghiem|tu van|review|loi khuyen)|giup (minh|em|toi)|tu van|nen (dung|chon|lam|chay)|"
                    r"lam sao|the nao|o dau|co ai|bi (khoa|han che|chan|die)|khong (chay|len|duyet))")
VENDOR_RX = re.compile(r"(ban (via|bm|tai khoan|tkqc|clone)|cho thue|nhan (chay|cham|setup|lam|khang)|dich vu|"
                       r"cung cap (via|bm|tai khoan|tkqc)|inbox (em|minh) (nhan|ho tro)|bao gia (chay|dich vu)|khoa hoc)")
SELLER_TPL = [
    "Chào bạn, mình bên xưởng {p}, nếu shop cần thêm mặt hàng đồ uống để bán online thì mình gửi catalog tham khảo nhé",
    "Chúc shop chạy đơn đều nha. Bên mình sản xuất {p}, shop muốn thêm mặt hàng thì mình gửi mẫu thử",
    "Mình làm xưởng {p}, nhiều shop online đang lấy về bán kèm, bạn cần thì mình gửi thông tin nhé",
    "Bạn bán online thì tham khảo thêm {p} tận xưởng nha, mình gửi catalog và mẫu thử được",
    "Góp thêm một nguồn hàng cho shop: bên mình là xưởng {p}, cần tư vấn mặt hàng cứ nhắn mình nhé",
    "Shop đang đẩy đơn online thì có thể thử thêm {p}, bên mình là nhà máy, cần mẫu cứ nhắn mình",
]
LIVE_TPL = [
    "Shop hay livestream thì {p} lên live cũng dễ chốt, bên mình là xưởng sản xuất, cần mẫu cứ nhắn mình nhé",
    "Chúc phiên live của shop đông khách. Bên mình sản xuất {p}, shop muốn thêm hàng lên live thì mình gửi mẫu thử",
]
FEED_META_JS = r"""() => [...document.querySelectorAll('[role="article"]')].filter(a => !a.parentElement.closest('[role="article"]')).slice(0, 150).map(a => {
  const pl = a.querySelector('a[href*="/posts/"],a[href*="permalink"],a[href*="story_fbid"]');
  const g = [...a.querySelectorAll('a[href*="/groups/"]')].find(x => /\/groups\/[^/?#]+\/?(\?|#|$)/.test(x.href) && (x.innerText || '').trim().length > 1);
  const join = [...a.querySelectorAll('[role="button"],button')].some(b => /^(tham gia( nhóm)?|join( group)?)$/i.test((b.getAttribute('aria-label') || b.innerText || '').trim()));
  return {link: pl ? pl.href.split('?')[0] : '', gname: g ? g.innerText.trim().split('\n')[0] : '', ghref: g ? g.href : '', join: join};
})"""


def s() -> dict:
    return db.get_settings()


def _i(k: str, d: int) -> int:
    try:
        return int(s().get(k) or d)
    except ValueError:
        return d


# ---------------------------------------------------------------- nick lướt bao nhiêu lượt (do luật Facebook quyết định)
def plan(aid: int) -> dict:
    """Hôm nay nick lướt feed mấy lượt, lượt kế tiếp lúc nào, vì sao. Không phải sếp đặt tay: suy từ luật của nick."""
    import fb_policy
    import replies
    acc = db.one("SELECT * FROM fb_accounts WHERE id=?", (aid,)) or {}
    out = {"scans": 0, "done": 0, "next": None, "due": False, "why": ""}
    if s().get("feed_enabled", "1") != "1":
        return {**out, "why": "Sếp đang tắt lướt bảng tin nhóm"}
    if acc.get("rest_until") and acc["rest_until"] > db.now():
        return {**out, "why": f"Nick đang nghỉ sau sự cố tới {acc['rest_until'][11:16]} {acc['rest_until'][8:10]}/{acc['rest_until'][5:7]}"}
    f = fb_policy.factor(acc)
    scans = max(1, round(_i("feed_scans_day", 2) * f))  # nick mới / vừa bị chặn: 1 lượt
    today = db.today()
    db.run("UPDATE feed_scans SET status='lost' WHERE status IN ('queued','running') AND created_at < ?",
           ((db.clock() - timedelta(hours=3)).strftime("%Y-%m-%d %H:%M:%S"),))
    rows = db.q("SELECT status, created_at FROM feed_scans WHERE account_id=? AND created_at >= ? AND status!='lost' ORDER BY id",
                (aid, today))
    out.update(scans=scans, done=len(rows))
    if any(r["status"] in ("queued", "running") for r in rows):
        return {**out, "why": "Đang lướt bảng tin nhóm"}
    q = replies.quota(aid)
    pending = db.one("SELECT COUNT(*) n FROM reply_tasks WHERE account_id=? AND status IN ('draft','approved')", (aid,))["n"]
    if pending >= q["limit"]:
        return {**out, "why": f"Đã có {pending} câu chờ duyệt / chờ gửi, đủ cho {q['limit']} câu/ngày của nick, chưa cần lướt thêm"}
    if len(rows) >= scans:
        return {**out, "why": f"Đã lướt đủ {scans} lượt hôm nay theo luật của nick"}
    now = db.clock()
    day = now.strftime("%Y-%m-%d")
    af = datetime.strptime(f"{day} {acc.get('active_from') or '08:00'}", "%Y-%m-%d %H:%M")
    at = datetime.strptime(f"{day} {acc.get('active_to') or '22:00'}", "%Y-%m-%d %H:%M")
    nxt = af + timedelta(minutes=20 + (aid * 37) % 90)  # các nick lệch nhau, không cùng mở Facebook một lúc
    if rows:
        nxt = max(nxt, datetime.strptime(rows[-1]["created_at"][:16], "%Y-%m-%d %H:%M")
                  + timedelta(hours=_i("feed_gap_hours", 3), minutes=(aid * 13) % 40))
    if nxt > at - timedelta(minutes=30):
        return {**out, "why": "Hết giờ làm của nick hôm nay"}
    out["next"] = nxt.strftime("%Y-%m-%d %H:%M")
    out["due"] = nxt <= now
    out["why"] = f"Lượt {len(rows) + 1}/{scans} lúc {out['next'][11:]}"
    return out


def _queue(acc: dict, notify: str | None = None) -> int:
    import browser_poster as B
    sid = db.run("INSERT INTO feed_scans(account_id, status, created_at) VALUES (?, 'queued', ?)", (acc["id"], db.now()))
    sid = sid if isinstance(sid, int) else db.one("SELECT MAX(id) i FROM feed_scans")["i"]
    B.submit(acc["sale_id"], {"kind": "feedscan", "account": acc["id"], "scan_id": sid, "notify": notify})
    return sid


def tick(now):
    """Mỗi phút: nick nào tới lượt lướt feed (theo plan) thì xếp cho sale. Sale đang bận nhiều việc thì để phút sau."""
    import accounts
    import browser_poster as B
    if s().get("feed_enabled", "1") != "1":
        return
    for a in accounts.working():
        try:
            if B.queued(a["sale_id"]) > 1:
                continue
            if plan(a["id"])["due"]:
                _queue(a)
        except Exception as e:
            print("[feed tick]", e)


def start(aid: int | None = None, notify: str | None = None) -> dict:
    """Sếp bấm Lướt feed ngay / nhắn CEO: mọi nick đang làm việc (hoặc một nick) lướt một lượt ngay."""
    import accounts
    accs = [a for a in accounts.working() if not aid or a["id"] == aid]
    if not accs:
        raise ValueError("Chưa có nick nào đăng nhập và đang làm việc để lướt bảng tin nhóm")
    queued, skipped = [], []
    for a in accs:
        p = plan(a["id"])
        if p["why"].startswith(("Nick đang nghỉ", "Đang lướt", "Sếp đang tắt")):
            skipped.append(f"{accounts.label(a)}: {p['why']}")
            continue
        _queue(a, notify)
        queued.append(accounts.label(a))
    return {"queued": queued, "skipped": skipped}


# ---------------------------------------------------------------- đọc bảng tin
def read_feed(page, need: int) -> list[dict]:
    """Cuộn bảng tin nhóm tới khi đọc đủ `need` bài (tối đa 16 lần cuộn). Chỉ đọc, không bấm thích, không bấm gì."""
    import browser_poster as B
    import prospect
    page.goto(B.FB_BASE + "/groups/feed/", wait_until="domcontentloaded", timeout=60000)
    page.wait_for_timeout(int(random.uniform(4, 6.5) * 1000))
    B._check_blocked(page)
    got: dict[str, dict] = {}
    for i in range(16):
        try:
            rows = page.evaluate(prospect.GROUP_JS)
            meta = {m["link"]: m for m in page.evaluate(FEED_META_JS) if m["link"]}
        except Exception as e:
            print("[feed read]", e)
            rows, meta = [], {}
        for r in rows:
            if r.get("comment"):
                continue
            key = r.get("link") or plain(r.get("text") or "")[:80]
            if key and key not in got:
                got[key] = {**r, **{k: v for k, v in (meta.get(r.get("link")) or {}).items() if k != "link"}}
        if len(got) >= need:
            break
        page.mouse.wheel(0, random.randint(1100, 1700))
        page.wait_for_timeout(int(random.uniform(2.2, 4.5) * 1000))
    return list(got.values())


# ---------------------------------------------------------------- lớp 1: lọc bằng chữ (không tốn tiền)
def _sim(a: str, b: str) -> float:
    x, y = set(plain(a).split()), set(plain(b).split())
    return len(x & y) / max(1, len(x | y))


def comment_all() -> bool:
    return s().get("feed_comment_all", "1") == "1"


def rule(text: str, name: str = "") -> dict | None:
    """{'kind','score','reason'} hoặc None nếu bài chỉ đọc qua."""
    import prospect
    import prospect_rules
    p = plain(text)
    if not p or len(p) < 8 or prospect.SUPPLY_RX.search(p) or VENDOR_RX.search(p):
        return None  # người chào bán / tuyển đại lý / bán dịch vụ: nhà cung cấp khác
    r = None
    if prospect.DEMAND_RX.search(p) and prospect.fit_text(text):
        r = {"kind": "buyer", "score": 78, "reason": "Đang hỏi nguồn hàng hợp ngành"}
    else:
        extra = [w for w in re.split(r"[,;\n]+", s().get("feed_seller_words") or "") if w.strip()]
        sig = SELLER_RX.search(p) or (extra and prospect_rules.hits(p, extra))
        if s().get("feed_seller_enabled", "1") == "1" and sig and (ASK_RX.search(p) or "?" in text) and not prospect_rules.excluded(text):
            word = sig.group(0) if hasattr(sig, "group") else sig[0]
            r = {"kind": "seller", "score": 72 + (10 if prospect.fit_text(text) else 0),
                 "reason": f"Người bán online đang hỏi (“{word.strip()}”)"}
    if r is None:
        if not comment_all():
            return None
        r = {"kind": "general", "score": 60, "reason": "Bình luận đều mọi nhóm (không cần từ khóa liên quan)"}
    pen, why, ban = junk.check(text, name)
    if ban:
        return None
    if pen:
        r["score"] -= pen
        r["reason"] += f"; {why}"
    for x in db.q("""SELECT post_text FROM reply_tasks WHERE origin='feed' AND status='skipped' ORDER BY id DESC LIMIT 80"""):
        if _sim(text, x["post_text"] or "") >= 0.5:  # lớp 3: giống bài sếp đã bỏ qua
            r["score"] -= 20
            r["reason"] += "; giống bài sếp từng bỏ qua"
            break
    return r


# ---------------------------------------------------------------- lớp 2: Claude đọc hiểu bài, viết câu chào cho người bán
def _examples() -> str:
    ok = db.q("SELECT kind, post_text FROM reply_tasks WHERE origin='feed' AND status IN ('approved','sent') ORDER BY id DESC LIMIT 4")
    no = db.q("SELECT kind, post_text FROM reply_tasks WHERE origin='feed' AND status='skipped' ORDER BY id DESC LIMIT 4")
    t = ""
    if ok:
        t += " Sếp đã DUYỆT các bài như: " + " | ".join(re.sub(r"\s+", " ", x["post_text"] or "")[:90] for x in ok) + "."
    if no:
        t += " Sếp đã BỎ QUA các bài như: " + " | ".join(re.sub(r"\s+", " ", x["post_text"] or "")[:90] for x in no) + "."
    return t


def judge(items: list[dict]) -> list[dict]:
    """Claude chấm từng bài (loại, điểm, lý do) và viết câu chào cho người bán online. Lỗi / chưa có khóa: giữ điểm lớp 1."""
    from llm import llm
    import agents
    import prospect_rules
    if not items or not llm.live:
        return items
    ask = ("Bạn là Bảo, nhân viên của nhà máy sản xuất trà túi lọc, ngũ cốc, cà phê, bột (bán sỉ, gia công thương hiệu riêng). "
           "Dưới đây là các bài trong nhóm Facebook. Với MỖI bài, xác định: type = 'buyer' nếu người đăng đang cần mua / nhập / tìm "
           "nguồn trà, ngũ cốc, đồ uống, thực phẩm; 'seller' nếu người đăng đang tự kinh doanh online (chạy quảng cáo, hỏi tài khoản "
           "quảng cáo, livestream, chốt đơn, ship COD...) và đang hỏi điều gì đó, có thể muốn thêm mặt hàng; 'none' nếu là người bán "
           "dịch vụ / nhà cung cấp khác, bài kể chuyện, bài không phải kinh doanh, hoặc bán ngành không hợp (quần áo, mỹ phẩm...). "
           "score 0–100 = khả năng đây là khách sỉ tiềm năng của nhà máy; reason = một câu ngắn tiếng Việt. "
           "Riêng bài 'seller': viết reply 15–35 chữ, chào nhẹ, bám vào đúng điều họ viết (không trả lời thay chuyên môn quảng cáo), "
           "giới thiệu mình là xưởng, mời nhắn nếu cần thêm mặt hàng; KHÔNG ghi số điện thoại / Zalo / giá / chiết khấu, không hứa "
           "công dụng, không viết hoa cả câu, không hashtag, mỗi câu khác nhau. Bài 'buyer' để reply rỗng."
           + (" Bài KHÔNG phải buyer / seller nhưng là bài bình thường của thành viên nhóm (chia sẻ, hỏi đáp, khoe hàng, tâm sự...): "
              "type = 'general', viết reply 12–30 chữ bình luận tự nhiên, đúng nội dung bài (đồng cảm, góp ý, chúc mừng, hỏi thêm), "
              "câu cuối giới thiệu nhẹ mình bên xưởng trà, ngũ cốc nếu hợp; KHÔNG ghi số điện thoại / Zalo / giá, không chào bán ép, "
              "không lặp câu. Chỉ để 'none' với bài lừa đảo, bán dịch vụ, nhà cung cấp khác, bài tang, tai nạn, chính trị."
              if comment_all() else "")
           + _examples() + " " + prospect_rules.prompt_block()[:600] + " Các bài: "
           + " | ".join(f"{i + 1}. {' '.join(it['post_text'].split())[:320]}" for i, it in enumerate(items))
           + '. Trả về JSON {"items": [{"i": 1, "type": "...", "score": 0, "reason": "...", "reply": "..."}]}.')
    try:
        d = llm.json(agents.system_prompt("bao", s(), with_learning=False), ask, mock=None, max_tokens=1800, task="posts") or {}
    except Exception as e:
        print("[feed judge]", e)
        return items
    for x in d.get("items") or []:
        try:
            it = items[int(x.get("i")) - 1]
        except (TypeError, ValueError, IndexError):
            continue
        kind = str(x.get("type") or "").lower()
        it["kind"] = kind if kind in ("buyer", "seller") or (kind == "general" and comment_all()) else "none"
        try:
            it["score"] = max(0, min(100, int(x.get("score"))))
        except (TypeError, ValueError):
            pass
        it["reason"] = (str(x.get("reason") or "").strip() or it["reason"])[:200]
        rep = re.sub(r"\s+", " ", str(x.get("reply") or "")).strip().strip('"“”')
        if rep and not re.search(r"(?i)zalo|sđt|sdt|hotline|\d[\d .]{7,}\d", rep):
            it["draft"] = " ".join(rep.split()[:40])
        it["by"] = "claude"
    return items


def seller_text(it: dict, avoid: set[str]) -> str:
    """Câu chào nhẹ khi Claude không viết: theo mẫu, không lặp câu nick đã dùng 14 ngày qua."""
    import replies
    p = replies.product_guess(it["post_text"])
    pool = (LIVE_TPL if re.search(r"livestream|\blive\b", plain(it["post_text"])) else []) + SELLER_TPL
    random.shuffle(pool)
    for t in pool:
        x = t.format(p=p)
        if plain(x) not in avoid:
            return x
    return pool[0].format(p=p)


# ---------------------------------------------------------------- chọn bài, nhóm, ảnh
def _group(aid: int, r: dict) -> dict | None:
    """Nhóm của bài trên feed. Feed chỉ hiện nhóm nick đang ở (bài 'gợi ý' có nút Tham gia thì bỏ)."""
    import group_finder
    import my_groups
    if r.get("join"):
        return None
    slug = my_groups.slug_of(r.get("link") or "") or my_groups.slug_of(r.get("ghref") or "")
    if not slug:
        return None
    g = my_groups.find_group(slug)
    if not g:
        gid = db.run("""INSERT INTO groups(name, url, slug, topic, members, rules, min_days_between_posts, note, created_at, source)
                        VALUES (?,?,?,?,0,'',2,?,?,'account')""",
                     ((r.get("gname") or slug)[:150], my_groups.group_url(slug), slug, "Nhóm có sẵn trong nick",
                      "Thấy trên bảng tin nhóm của nick", db.now()))
        g = db.one("SELECT * FROM groups WHERE id=?", (gid if isinstance(gid, int) else db.one("SELECT MAX(id) i FROM groups")["i"],))
    st = my_groups.membership(g, aid)
    if st == "leave":
        return None
    if st in ("no", "unknown"):
        group_finder.set_join(g["id"], aid, "joined", "Thấy bài của nhóm trên bảng tin nhóm của nick", origin="existing")
    return g


def image_for(text: str, group_id: int | None) -> str | None:
    """1 ảnh ngẫu nhiên trong thư mục ảnh (sản phẩm người hỏi cần, không thì thư mục chung), ưu tiên ảnh chưa dùng ở nhóm này."""
    import media_folder as M
    import post_care
    import replies
    name = replies.product_guess(text)
    pid = next((p["id"] for p in db.q("SELECT id, name FROM products WHERE COALESCE(is_general,0)=0")
                if post_care._short_name(p["name"]) == name), None)
    pool = M.pool_for({"product_id": pid}) or M.pool_for({})
    if not pool:
        return None
    u = M._usage(pool)
    fresh = [p for p in pool if group_id not in u[str(p)]["groups"]] or pool
    return str(M._rank(fresh, u)[0])


def pick(rows: list[dict], aid: int) -> list[dict]:
    import group_target
    import prospect
    import replies
    me = prospect.our_names()
    ours = {(r["posted_url"] or "").split("?")[0].rstrip("/") for r in db.q("SELECT posted_url FROM posts WHERE posted_url IS NOT NULL")}
    have = {r["post_url"] for r in db.q("SELECT post_url FROM reply_tasks")}
    greeted = {(r["author_url"] or plain(r["author"] or "")) for r in db.q("SELECT author, author_url FROM reply_tasks WHERE kind='seller'")}
    out, seen = [], set()
    for r in rows:
        link = (r.get("link") or "").split("?")[0].rstrip("/")
        name = (r.get("author") or "").strip()
        if not link or link in have or link in seen or link in ours or not name or plain(name) in me:
            continue
        text = (r.get("text") or "").replace(name, "", 1)
        if r.get("gname"):
            text = text.replace(r["gname"], "", 1)
        text = re.sub(r"\s+", " ", text).strip()
        url = prospect.canon(r.get("href") or "") or ""
        if url and junk.blocked(url, name=name):
            continue
        k = rule(text, name)
        if not k:
            continue
        g = _group(aid, r)
        if not g or group_target.classify(g)[0] == "exclude":
            continue
        quiet = int(g.get("no_selling") or 0) or (g.get("no_pitch_until") or "") > db.now()
        if k["kind"] == "general" and quiet:
            k = {**k, "no_contact": True, "reason": k["reason"] + "; nhóm cấm bán hàng: bình luận không kèm Zalo"}
        if k["kind"] == "seller":
            if quiet:
                continue  # nhóm cấm bán hàng / từng xóa bình luận chào: không chào người bán ở đây
            if (url or plain(name)) in greeted:
                continue  # mỗi người chỉ một nick chào một lần
        seen.add(link)
        out.append({"account_id": aid, "group_id": g["id"], "post_url": link, "author": name[:80], "author_url": url,
                    "post_text": text[:900], **k})
    return out


def save(items: list[dict], aid: int) -> dict:
    """Lớp 2 rồi lưu bình luận chờ duyệt. Không tạo nhiều hơn số câu nick gửi được trong khoảng 2 ngày."""
    import replies
    q = replies.quota(aid)
    room = max(0, q["limit"] * 2 - db.one("SELECT COUNT(*) n FROM reply_tasks WHERE account_id=? AND status IN ('draft','approved')",
                                         (aid,))["n"])
    per_g = _i("feed_per_group_day", 2)
    since = (db.clock() - timedelta(hours=24)).strftime("%Y-%m-%d %H:%M:%S")
    used_g = {r["group_id"]: (r["n"], r["last"] or "") for r in db.q(
        """SELECT group_id, SUM(created_at>=? OR status IN ('draft','approved')) n, MAX(COALESCE(sent_at, created_at)) last
           FROM reply_tasks WHERE status!='skipped' GROUP BY group_id""", (since,))}
    # nhóm ít được bình luận nhất lên trước; bài hỏi mua / người bán vẫn ưu tiên trong cùng nhóm
    rank = {"buyer": 0, "seller": 1, "general": 2}
    items = sorted(items, key=lambda x: (used_g.get(x["group_id"], (0, ""))[0], used_g.get(x["group_id"], (0, ""))[1],
                                         rank.get(x["kind"], 3), -x["score"]))
    take, cnt = [], {}
    for x in items:  # bình luận theo nhóm: mỗi nhóm tối đa per_g câu (tính cả câu chờ duyệt / chờ gửi); người hỏi mua luôn được trả lời
        n = used_g.get(x["group_id"], (0, ""))[0] + cnt.get(x["group_id"], 0)
        if x["kind"] == "general" and n >= per_g:
            continue
        cnt[x["group_id"]] = cnt.get(x["group_id"], 0) + 1
        take.append(x)
    items = judge(take[:max(room, 0) + 4])
    lo = _i("feed_min_score", 70)
    items = [x for x in items if (x["kind"] in ("buyer", "seller") and x["score"] >= lo) or (x["kind"] == "general" and x.get("draft"))]
    sellers = [x for x in items if x["kind"] == "seller"][:q["seller_limit"] * 2]
    items = [x for x in items if x["kind"] != "seller" or x in sellers][:room]
    res = {"buyer": 0, "seller": 0, "general": 0}
    buyers = [x for x in items if x["kind"] == "buyer"]
    for it, (reply, src) in zip(buyers, replies.write(buyers)):
        it["reply"], it["source"] = reply, src
        it["image"] = image_for(it["post_text"], it["group_id"]) if s().get("feed_buyer_image", "1") == "1" else None
    avoid = {plain(re.sub(r"\s*👉.*$", "", r["reply"] or "")) for r in db.q(
        "SELECT reply FROM reply_tasks WHERE account_id=? AND kind='seller' AND created_at >= ?",
        (aid, (db.clock() - timedelta(days=14)).strftime("%Y-%m-%d")))}
    c = replies.contact()
    for it in items:
        if it["kind"] == "seller":
            x = it.get("draft") or seller_text(it, avoid)
            avoid.add(plain(x))
            it["reply"], it["source"] = x.rstrip(" .") + (". 👉 " + c if c else ""), it.get("by") or "bao"
        elif it["kind"] == "general":
            x = it.get("draft") or ""
            if not x or plain(x) in avoid:
                continue
            avoid.add(plain(x))
            it["reply"], it["source"] = x.rstrip(" .") + (". 👉 " + c if c and not it.get("no_contact") else ""), it.get("by") or "claude"
        if not it.get("reply"):
            continue
        try:
            db.run("""INSERT INTO reply_tasks(account_id, group_id, post_url, author, author_url, post_text, reply, source, status,
                      created_at, kind, origin, image, score, reason) VALUES (?,?,?,?,?,?,?,?,'draft',?,?,'feed',?,?,?)""",
                   (it["account_id"], it["group_id"], it["post_url"], it["author"], it["author_url"], it["post_text"], it["reply"],
                    it["source"], db.now(), it["kind"], it.get("image"), it["score"], it["reason"]))
            res[it["kind"]] += 1
        except Exception as e:
            print("[feed save]", e)
    return res


# ---------------------------------------------------------------- nhóm có xóa bình luận chào không
def check_removed(page, aid: int, n: int = 2) -> int:
    """Mở lại vài bình luận chào người bán đã gửi trên 6 giờ: không còn thấy thì coi như nhóm xóa, ngừng chào ở nhóm đó 30 ngày."""
    import browser_poster as B
    rows = db.q("""SELECT * FROM reply_tasks WHERE account_id=? AND kind IN ('seller','general') AND status='sent' AND COALESCE(removed,0)=0
                   AND checked_at IS NULL AND sent_at <= ? ORDER BY sent_at LIMIT ?""",
                (aid, (db.clock() - timedelta(hours=6)).strftime("%Y-%m-%d %H:%M:%S"), n))
    gone = 0
    for r in rows:
        try:
            page.goto(B.fb_url(r["post_url"]), wait_until="domcontentloaded", timeout=60000)
            page.wait_for_timeout(int(random.uniform(3, 5) * 1000))
            B._check_blocked(page)
            body = page.inner_text("body")
            mine = plain(re.sub(r"\s*👉.*$", "", r["reply"] or ""))[:40]
            if any(t.lower() in body.lower() for t in B.selectors()["removed_texts"]) or not mine or mine in plain(body):
                db.run("UPDATE reply_tasks SET checked_at=? WHERE id=?", (db.now(), r["id"]))
                continue
            until = (db.clock() + timedelta(days=30)).strftime("%Y-%m-%d %H:%M:%S")
            db.run("UPDATE reply_tasks SET checked_at=?, removed=1 WHERE id=?", (db.now(), r["id"]))
            db.run("UPDATE groups SET no_pitch_until=? WHERE id=?", (until, r["group_id"]))
            g = db.one("SELECT name FROM groups WHERE id=?", (r["group_id"],)) or {}
            db.log("bao", "Nhóm xóa bình luận chào",
                   f"Bình luận chào {r['author']} ở nhóm {g.get('name')} không còn: ngừng chào người bán ở nhóm này 30 ngày")
            gone += 1
        except B.Blocked:
            raise
        except Exception as e:
            print("[feed check]", e)
        B._pause(page, 4, 10)
    return gone


def job(pw, aid: int, scan_id: int | None = None, notify: str | None = None) -> dict:
    import browser_poster as B
    import workflows
    acc, sale, agent = B._ctx_names(aid)
    if scan_id:
        db.run("UPDATE feed_scans SET status='running' WHERE id=?", (scan_id,))
    res = {"read": 0, "buyer": 0, "seller": 0, "removed": 0}
    note = ""
    ctx, page = B._open(pw, aid)
    try:
        if not B._logged_in(ctx):
            raise RuntimeError("Nick chưa đăng nhập. Vào Nhân viên sale → Mở Chrome để đăng nhập lại")
        workflows.set_status(agent, "working", f"Lướt bảng tin nhóm (nick {acc.get('name')})")
        workflows.set_status("bao", "working", "Đọc bảng tin nhóm tìm người hỏi mua, người bán online")
        res["removed"] = check_removed(page, aid)
        rows = read_feed(page, _i("feed_min_posts", 20))
        res["read"] = len(rows)
        res.update(save(pick(rows, aid), aid))
    except B.Blocked as e:
        B._block(aid, str(e))
        note = "Nick bị Facebook kiểm tra nên dừng"
    except Exception as e:
        note = str(e).splitlines()[0][:200]
        raise
    finally:
        try:
            ctx.close()
        except Exception:
            pass
        if scan_id:
            db.run("UPDATE feed_scans SET status=?, done_at=?, read=?, buyers=?, sellers=?, note=? WHERE id=?",
                   ("failed" if note else "done", db.now(), res["read"], res["buyer"], res["seller"], note, scan_id))
        workflows.set_status("bao", "idle", "Chờ sếp duyệt bình luận")
        workflows.set_status(agent, "idle", "Chờ việc tiếp theo")
    msg = (f"Nick {acc.get('name')} lướt bảng tin nhóm, đọc {res['read']} bài: {res['buyer']} người hỏi mua (bình luận kèm ảnh), "
           f"{res['seller']} người bán online (chào nhẹ kèm Zalo). Sếp duyệt ở trang Trả lời khách.")
    if res["removed"]:
        msg += f" {res['removed']} bình luận chào cũ đã bị nhóm xóa: ngừng chào ở nhóm đó."
    if note:
        msg += " " + note
    db.log("bao", "Lướt bảng tin nhóm", msg)
    if notify:
        import ceo_orders
        ceo_orders.followup(msg, notify)
    return res


def overview() -> dict:
    import accounts
    import replies
    today = db.today()
    nicks = []
    for a in accounts.working():
        d = db.one("""SELECT COUNT(*) n, SUM(read) read, SUM(buyers) b, SUM(sellers) s FROM feed_scans
                      WHERE account_id=? AND created_at >= ? AND status='done'""", (a["id"], today))
        q = replies.quota(a["id"])
        nicks.append({"id": a["id"], "name": accounts.label(a), "plan": plan(a["id"]), "scans": d["n"] or 0, "read": d["read"] or 0,
                      "buyers": d["b"] or 0, "sellers": d["s"] or 0, "limit": q["limit"], "left": q["left"],
                      "seller_limit": q["seller_limit"], "seller_left": q["seller_left"]})
    recent = db.q("""SELECT f.*, a.name nick FROM feed_scans f LEFT JOIN fb_accounts a ON a.id=f.account_id
                     WHERE f.status IN ('done','failed') ORDER BY f.id DESC LIMIT 8""")
    stop = db.q("SELECT id, name, no_pitch_until FROM groups WHERE no_pitch_until > ? ORDER BY name", (db.now(),))
    return {"nicks": nicks, "recent": recent, "no_pitch": stop,
            "settings": {k: s().get(k) for k in ("feed_enabled", "feed_min_posts", "feed_scans_day", "feed_min_score",
                                                 "feed_buyer_image", "feed_seller_enabled", "feed_seller_per_nick_day",
                                                 "feed_seller_words", "feed_comment_all", "feed_per_group_day",
                                                 "reply_gap_min")}}

"""Lan chỉnh bài theo nhóm sắp đăng, dựa trên dữ liệu thật của chính nhóm đó.

Bài được viết trước khi biết đăng nhóm nào (Tuấn xếp lịch sau). Khi bài đã có nhóm và giờ đăng, nếu nhóm có đủ dữ liệu thật
(câu người trong nhóm hỏi mua mà nick đọc được, bình luận của khách dưới bài mình từng đăng ở nhóm, bài của mình từng ra khách
ở nhóm), Lan nhờ Claude sửa câu mở đầu và thứ tự ý cho trúng điều người nhóm đó đang hỏi.

Giữ an toàn: không thêm thông tin mới (giá, chứng nhận, số liệu), giữ dòng liên hệ Zalo, độ dài gần bài gốc. Bản chỉnh phạm
luật Facebook, mất dòng liên hệ hay lệch quá xa thì giữ bài gốc. Bài gốc được lưu (orig_content); bài đổi sang nhóm khác thì
chỉnh lại từ bài gốc, nhóm mới chưa đủ dữ liệu thì trả về bài gốc.
"""
import threading
from datetime import datetime, timedelta

import db

_lock = threading.Lock()
_running = False


def s() -> dict:
    return db.get_settings()


def enabled() -> bool:
    return s().get("group_fit", "1") == "1"


def _since(days: int) -> str:
    return (db.clock() - timedelta(days=days)).strftime("%Y-%m-%d %H:%M:%S")


def context(group_id: int) -> dict:
    """Dữ liệu thật của nhóm: câu hỏi mua, bình luận khách dưới bài mình, bài mình từng ra khách."""
    g = db.one("SELECT * FROM groups WHERE id=?", (group_id,)) or {}
    asks = [r["post_text"] for r in db.q(
        """SELECT post_text FROM reply_tasks WHERE group_id=? AND COALESCE(kind,'buyer')='buyer' AND COALESCE(post_text,'')!=''
           AND created_at>=? ORDER BY id DESC LIMIT 6""", (group_id, _since(45)))]
    comments = [r["need"] for r in db.q(
        """SELECT l.need FROM leads l JOIN posts p ON p.id=l.post_id WHERE p.group_id=? AND COALESCE(l.need,'')!=''
           AND COALESCE(l.is_sample,0)=0 AND l.created_at>=? ORDER BY l.id DESC LIMIT 6""", (group_id, _since(60)))]
    wins = [r for r in db.q(
        """SELECT content, leads, comments FROM posts WHERE group_id=? AND status='posted' AND (COALESCE(leads,0)>0 OR COALESCE(comments,0)>=3)
           ORDER BY COALESCE(leads,0) DESC, COALESCE(comments,0) DESC LIMIT 2""", (group_id,))]
    return {"group": g, "asks": asks, "comments": comments, "wins": wins,
            "signals": len(asks) + len(comments) + 2 * len(wins)}


def ready(ctx: dict) -> bool:
    return ctx["signals"] >= int(s().get("group_fit_min") or 2)


def _clip(t: str, n: int = 220) -> str:
    t = " ".join((t or "").split())
    return t[:n] + ("…" if len(t) > n else "")


def _prompt(base: str, ctx: dict) -> str:
    g = ctx["group"]
    lines = [f"Bài dưới đây sắp đăng vào nhóm Facebook “{g.get('name', '')}”"
             + (f" (chủ đề: {g['topic']})" if g.get("topic") else "") + "."]
    if g.get("rules_note"):
        lines.append(f"Luật nhóm: {_clip(g['rules_note'], 300)}")
    if ctx["asks"]:
        lines.append("Người trong nhóm này vừa đăng hỏi mua / tìm nguồn (nguyên văn):")
        lines += [f"- {_clip(a)}" for a in ctx["asks"]]
    if ctx["comments"]:
        lines.append("Khách bình luận dưới bài mình từng đăng ở nhóm này (nguyên văn):")
        lines += [f"- {_clip(c, 160)}" for c in ctx["comments"]]
    if ctx["wins"]:
        lines.append("Bài mình từng đăng ở nhóm này có khách / nhiều bình luận (học cách mở đầu, không chép):")
        lines += [f"- ({w['leads'] or 0} khách, {w['comments'] or 0} bình luận) {_clip(w['content'], 260)}" for w in ctx["wins"]]
    lines.append(f"\nBÀI GỐC:\n{base}\n")
    lines.append("Sửa bài cho trúng điều người trong nhóm này đang hỏi: viết lại câu mở đầu nhắm vào nhu cầu họ nêu, "
                 "đưa ý họ quan tâm lên trước, dùng cách gọi tên hàng giống họ. BẮT BUỘC: chỉ dùng thông tin có trong BÀI GỐC, "
                 "không thêm giá, con số, chứng nhận, chính sách, quà tặng mới; giữ nguyên dòng liên hệ Zalo và số điện thoại; "
                 "độ dài gần bằng bài gốc; không nhắc tên người hỏi; không hứa công dụng chữa bệnh.")
    lines.append('Trả về JSON {"content": "bài đã sửa", "note": "1 câu: đã sửa gì cho nhóm này"}')
    return "\n".join(lines)


def _words(t: str) -> int:
    return len((t or "").split())


def adapt(post: dict, ctx: dict | None = None) -> dict:
    """Chỉnh 1 bài theo nhóm của nó. Trả {status: fitted|kept|restored|skip, note}."""
    import fb_policy
    import pricing
    from agents import system_prompt
    from llm import llm
    gid = post.get("group_id")
    base = post.get("orig_content") or post["content"]
    if not gid:
        return {"status": "skip", "note": "chưa có nhóm"}
    ctx = ctx or context(gid)

    def keep(status: str, note: str):
        db.run("UPDATE posts SET content=?, fit_group_id=?, fit_note=? WHERE id=?",
               (base, gid, note[:300], post["id"]))
        return {"status": status, "note": note}
    if not ready(ctx):
        return keep("restored" if post.get("orig_content") and post["content"] != base else "kept",
                    "Nhóm chưa đủ dữ liệu thật (câu hỏi mua, bình luận khách) để chỉnh, giữ bài gốc")
    d = llm.json(system_prompt("lan", s()), _prompt(base, ctx), mock=None, max_tokens=1200, task="posts")
    new = (d or {}).get("content", "").strip() if isinstance(d, dict) else ""
    if not new:
        return keep("kept", "Claude chưa chỉnh được, giữ bài gốc")
    new = pricing.sanitize(new)
    why = ""
    if pricing.has_contact(base) and not pricing.has_contact(new):
        why = "bản chỉnh mất dòng liên hệ Zalo"
    elif not 0.6 <= _words(new) / max(1, _words(base)) <= 1.5:
        why = "bản chỉnh dài / ngắn quá so với bài gốc"
    else:
        bad = fb_policy.blocking(fb_policy.check_text(new, post["id"], post.get("account_id")))
        if bad:
            why = "bản chỉnh phạm luật Facebook: " + fb_policy.summary(bad)
    if why:
        return keep("kept", f"Giữ bài gốc vì {why}")
    note = f"Chỉnh theo nhóm ({len(ctx['asks'])} câu hỏi mua, {len(ctx['comments'])} bình luận khách, {len(ctx['wins'])} bài tốt): " \
           + _clip((d or {}).get("note") or "sửa mở đầu theo điều người trong nhóm hỏi", 160)
    db.run("UPDATE posts SET orig_content=COALESCE(orig_content, ?), content=?, fit_group_id=?, fit_note=? WHERE id=?",
           (base, new, gid, note[:300], post["id"]))
    return {"status": "fitted", "note": note}


def due() -> list[dict]:
    """Bài đã có nhóm, chưa chỉnh cho đúng nhóm đó, còn ít nhất 3 phút nữa mới đăng."""
    soon = (db.clock() + timedelta(minutes=3)).strftime("%Y-%m-%d %H:%M")
    return db.q("""SELECT * FROM posts WHERE status='scheduled' AND target_type='group' AND group_id IS NOT NULL
                   AND COALESCE(managed,0)=0 AND COALESCE(fit_group_id,0)!=group_id AND scheduled_for>=?
                   ORDER BY scheduled_for LIMIT 30""", (soon,))


def run() -> dict:
    global _running
    from llm import llm
    with _lock:
        if _running:
            return {"busy": True}
        _running = True
    out = {"fitted": 0, "kept": 0, "restored": 0}
    try:
        cache = {}
        for p in due():
            if not enabled() or not llm.live:  # tắt / chưa có khóa: dùng bài gốc (đổi nhóm thì không để bài của nhóm cũ)
                db.run("UPDATE posts SET content=COALESCE(orig_content, content), fit_group_id=group_id, fit_note=NULL WHERE id=?",
                       (p["id"],))
                continue
            cur = db.one("SELECT status, group_id FROM posts WHERE id=?", (p["id"],))
            if not cur or cur["status"] != "scheduled" or cur["group_id"] != p["group_id"]:
                continue  # sale vừa bắt đầu đăng / Tuấn vừa đổi nhóm
            r = adapt(p, cache.setdefault(p["group_id"], context(p["group_id"])))
            out[r["status"]] = out.get(r["status"], 0) + 1
        if out["fitted"]:
            db.log("lan", "Chỉnh bài theo nhóm", f"Chỉnh {out['fitted']} bài cho trúng điều người trong nhóm đang hỏi"
                   + (f"; giữ bài gốc {out['kept'] + out['restored']} bài (nhóm chưa đủ dữ liệu hoặc bản chỉnh chưa đạt)"
                      if out["kept"] + out["restored"] else ""))
    except Exception as e:
        import errors
        errors.report_exc("ai", "Lan chỉnh bài theo nhóm bị lỗi", e, screen="posts")
    finally:
        with _lock:
            _running = False
    return out


def tick(now: datetime | None = None):
    if due():
        threading.Thread(target=run, daemon=True).start()

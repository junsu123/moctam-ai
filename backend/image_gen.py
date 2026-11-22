"""Nhi tự làm ảnh: tạo ảnh AI miễn phí bằng Cloudflare Workers AI (FLUX.1 schnell, 10.000 neurons/ngày ≈ 150 ảnh),
dự phòng lấy ảnh thật miễn phí trên Pixabay (theo chủ đề bài, tải về máy, ghi nguồn). Không làm được thì vẫn xin ảnh sếp như cũ.

Dùng cho: ảnh bài Trang (bài chờ ảnh), logo + banner Trang Nhi mới tạo. Ảnh vừa làm gửi lên Telegram để sếp xem;
sếp trả lời tin đó bằng ảnh khác là đổi ảnh.
"""
import base64
import io
import random
import re
import threading

import httpx

import db

CF_MODEL = "@cf/black-forest-labs/flux-1-schnell"
SAFE = ", no text, no letters, no watermark, no logo of real brands, no real people faces"
RATIO = {"post": (4, 5), "avatar": (1, 1), "cover": (1640, 624)}
_lock = threading.Lock()
SYNC = False  # test: làm ảnh ngay, không chạy nền


def _s() -> dict:
    return db.get_settings()


def cf_ready() -> bool:
    s = _s()
    return bool((s.get("cf_account_id") or "").strip() and (s.get("cf_api_token") or "").strip())


def pixabay_ready() -> bool:
    return bool((_s().get("pixabay_key") or "").strip())


def on() -> bool:
    return _s().get("img_auto", "1") == "1" and (cf_ready() or pixabay_ready())


def _crop(data: bytes, kind: str) -> bytes:
    """Cắt ảnh về đúng tỉ lệ (bài 4:5, logo vuông, banner ngang). Máy chưa có Pillow thì giữ nguyên."""
    try:
        from PIL import Image
    except ImportError:
        return data
    try:
        im = Image.open(io.BytesIO(data)).convert("RGB")
        rw, rh = RATIO.get(kind, (1, 1))
        w, h = im.size
        if w / h > rw / rh:
            nw = int(h * rw / rh)
            im = im.crop(((w - nw) // 2, 0, (w - nw) // 2 + nw, h))
        else:
            nh = int(w * rh / rw)
            im = im.crop((0, (h - nh) // 2, w, (h - nh) // 2 + nh))
        if kind == "cover":  # Facebook khuyên ảnh bìa 1640×624
            im = im.resize((1640, 624), Image.LANCZOS)
        out = io.BytesIO()
        im.save(out, "JPEG", quality=90)
        return out.getvalue()
    except Exception:
        return data


# ---------------------------------------------------------------- Cloudflare Workers AI
def cf_generate(prompt: str, steps: int = 4) -> bytes:
    s = _s()
    acc, tok = (s.get("cf_account_id") or "").strip(), (s.get("cf_api_token") or "").strip()
    if not (acc and tok):
        raise RuntimeError("Chưa cài Cloudflare")
    r = httpx.post(f"https://api.cloudflare.com/client/v4/accounts/{acc}/ai/run/{CF_MODEL}",
                   headers={"Authorization": f"Bearer {tok}"}, json={"prompt": (prompt or "")[:2000] + SAFE, "steps": max(1, min(8, steps))}, timeout=90)
    try:
        d = r.json()
    except Exception:
        raise RuntimeError(f"Cloudflare trả lỗi {r.status_code}")
    if not d.get("success", r.status_code == 200) or not (d.get("result") or {}).get("image"):
        msg = "; ".join(str(x.get("message") or x) for x in (d.get("errors") or [])) or f"HTTP {r.status_code}"
        if r.status_code == 429 or "neuron" in msg.lower() or "limit" in msg.lower():
            raise RuntimeError(f"Cloudflare hết lượt miễn phí hôm nay ({msg[:120]})")
        raise RuntimeError(f"Cloudflare lỗi: {msg[:200]}")
    return base64.b64decode(d["result"]["image"])


# ---------------------------------------------------------------- Pixabay
def _used_ids() -> set:
    return {r["s"] for r in db.q("SELECT image_src s FROM posts WHERE image_src LIKE 'pixabay:%' AND created_at >= date('now','-120 day')")}


def pixabay_search(query: str, kind: str = "post") -> list[dict]:
    key = (_s().get("pixabay_key") or "").strip()
    if not key or not (query or "").strip():
        return []
    orient = {"cover": "horizontal", "post": "vertical"}.get(kind, "all")
    out = []
    for lang, q in (("vi", query), ("en", query)):
        r = httpx.get("https://pixabay.com/api/", params={"key": key, "q": q[:100], "image_type": "photo", "safesearch": "true",
                                                         "per_page": 30, "lang": lang, "orientation": orient}, timeout=30)
        if r.status_code == 400 and "key" in r.text.lower():
            raise RuntimeError("Khóa Pixabay không đúng")
        r.raise_for_status()
        out = r.json().get("hits") or []
        if out:
            break
    return out


def pixabay_pick(query: str, kind: str = "post", rnd=None) -> tuple[bytes, str, str] | None:
    """Ảnh Pixabay hợp chủ đề, chưa dùng trong 120 ngày: (ảnh, mã nguồn, dòng ghi nguồn)."""
    hits = pixabay_search(query, kind)
    used = _used_ids()
    fresh = [h for h in hits if f"pixabay:{h.get('id')}" not in used] or hits
    if not fresh:
        return None
    h = (rnd or random).choice(fresh[:10])
    url = h.get("largeImageURL") or h.get("webformatURL")
    data = httpx.get(url, timeout=60).content
    return data, f"pixabay:{h.get('id')}", f"Ảnh: {h.get('user') or 'Pixabay'} / Pixabay"


def _query(text: str) -> list[str]:
    """Từ khóa tìm ảnh: cụm chủ đề trước, rồi vài chữ đầu của prompt tiếng Anh."""
    out = []
    for t in text.split("|"):
        t = re.sub(r"[^\w\s]", " ", t or "").strip()
        if t:
            out.append(" ".join(t.split()[:5]))
    return out


# ---------------------------------------------------------------- dùng chung
def make(prompt: str, query: str, kind: str = "post") -> tuple[bytes, str, str]:
    """(ảnh, nguồn, ghi chú). Thử Cloudflare trước, lỗi / hết lượt thì Pixabay. Không được thì RuntimeError (lý do)."""
    why = []
    if _s().get("img_auto", "1") != "1":
        raise RuntimeError("Sếp đang tắt Nhi tự làm ảnh")
    if cf_ready() and prompt:
        try:
            with _lock:
                return _crop(cf_generate(prompt), kind), "cloudflare", "Ảnh AI (Cloudflare)"
        except Exception as ex:
            why.append(str(ex))
    if pixabay_ready():
        for q in _query(query):
            try:
                r = pixabay_pick(q, kind)
            except Exception as ex:
                why.append(f"Pixabay: {ex}")
                break
            if r:
                return _crop(r[0], kind), r[1], r[2]
        else:
            why.append("Pixabay không có ảnh hợp chủ đề")
    if not why:
        why.append("chưa cài Cloudflare hoặc Pixabay")
    raise RuntimeError("; ".join(why))


def for_post(post_id: int, notify: bool = True) -> bool:
    """Bài Trang chờ ảnh: Nhi tự làm ảnh, gắn vào bài, gửi Telegram cho sếp xem. False nếu không làm được (khi đó xin ảnh sếp)."""
    import trend_pages
    p = db.one("SELECT p.*, f.name page_name, f.niche FROM posts p LEFT JOIN fb_pages f ON f.id=p.fb_page_ref WHERE p.id=?", (post_id,))
    if not p or p["status"] != "need_image":
        return False
    try:
        data, src, note = make(p.get("image_prompt") or "", f"{p.get('trend_topic') or p.get('page_kw') or ''}|{p.get('niche') or ''}|{p.get('image_prompt') or ''}")
        p2 = trend_pages.set_image(post_id, data, "jpg", by_boss=False)
    except Exception as ex:
        db.run("UPDATE posts SET error=? WHERE id=?", (f"Nhi chưa tự làm được ảnh: {str(ex)[:200]}", post_id))
        db.log("nhi", "Chưa tự làm được ảnh", f"Bài #{post_id}: {str(ex)[:160]}, xin ảnh sếp")
        return False
    db.run("UPDATE posts SET image_src=?, error=NULL WHERE id=?", (src, post_id))
    db.log("nhi", "Tự làm ảnh bài Trang", f"Bài #{post_id} ({p['page_name']}): {note}, đăng lúc {(p2['scheduled_for'] or '')[11:16]}")
    if notify:
        import nhi_tg
        mid = nhi_tg.send_photo(p2["image_path"], f"🖼 Nhi làm ảnh cho bài #{post_id} · Trang <b>{nhi_tg.e(p['page_name'])}</b> · {nhi_tg.e(note)} · "
                                f"đăng {nhi_tg._hm(p2['scheduled_for'] or '')}\nMuốn đổi: <b>trả lời tin này bằng ảnh khác</b>.")
        if mid:
            db.run("UPDATE posts SET img_req_msg=? WHERE id=?", (mid, post_id))
    return True


def for_page(pid: int) -> int:
    """Trang Nhi mới tạo: tự làm logo và banner theo prompt đã soạn. Trả về số ảnh làm được."""
    import trend_create
    p = db.one("SELECT * FROM fb_pages WHERE id=?", (pid,))
    if not p:
        return 0
    n = 0
    for k in trend_create.KIND:
        if p.get(f"{k}_path") or p.get(f"{k}_done"):
            continue
        try:
            data, src, note = make(p.get(f"{k}_prompt") or "", f"{p.get('niche') or ''}|{p.get('name') or ''}", kind=k)
            trend_create.set_page_image(pid, k, data, "jpg")
            n += 1
            import nhi_tg
            mid = nhi_tg.send_photo(db.one(f"SELECT {k}_path x FROM fb_pages WHERE id=?", (pid,))["x"],
                                    f"🖼 Nhi làm {trend_create.KIND[k][0]} cho Trang <b>{nhi_tg.e(p['name'])}</b> ({nhi_tg.e(note)}). "
                                    "Muốn đổi: <b>trả lời tin này bằng ảnh khác</b>.")
            if mid:
                db.run(f"UPDATE fb_pages SET {k}_msg=? WHERE id=?", (mid, pid))
        except Exception as ex:
            db.log("nhi", "Chưa tự làm được ảnh Trang", f"{p['name']} · {k}: {str(ex)[:160]}")
    return n


def test() -> dict:
    """Kiểm tra khóa: Cloudflare tạo thử 1 ảnh nhỏ (1 bước), Pixabay tìm thử."""
    out = {}
    if cf_ready():
        try:
            out["cloudflare"] = f"OK, tạo được ảnh ({len(cf_generate('a cup of tea on a wooden table', steps=1)) // 1024} KB)"
        except Exception as ex:
            out["cloudflare"] = f"Lỗi: {ex}"
    else:
        out["cloudflare"] = "Chưa cài"
    if pixabay_ready():
        try:
            out["pixabay"] = f"OK, tìm thấy {len(pixabay_search('trà', 'post'))} ảnh"
        except Exception as ex:
            out["pixabay"] = f"Lỗi: {ex}"
    else:
        out["pixabay"] = "Chưa cài"
    return out


def status() -> dict:
    s = _s()
    tok = (s.get("cf_api_token") or "").strip()
    key = (s.get("pixabay_key") or "").strip()
    made = db.one("""SELECT SUM(image_src='cloudflare') cf, SUM(image_src LIKE 'pixabay:%') px FROM posts
                     WHERE image_src IS NOT NULL AND created_at >= date('now','-30 day')""") or {}
    return {"on": s.get("img_auto", "1") == "1", "cf_account_id": s.get("cf_account_id") or "",
            "cf_token": (tok[:4] + "…" + tok[-4:]) if tok else "", "pixabay_key": (key[:4] + "…" + key[-4:]) if key else "",
            "cf_ready": cf_ready(), "pixabay_ready": pixabay_ready(), "made_cf": made.get("cf") or 0, "made_px": made.get("px") or 0}

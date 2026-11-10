"""Đăng bài lên Fanpage qua Facebook Graph API (cách chính thức, an toàn).

Lưu ý: Meta đã gỡ Groups API từ 4/2024 và không cho ứng dụng đăng lên trang cá nhân,
nên bài cho hội nhóm/trang cá nhân được hệ thống chuẩn bị sẵn để nhân viên bấm đăng.
"""
import json
import os

import httpx

import db

GRAPH = f"https://graph.facebook.com/{os.getenv('FB_GRAPH_VERSION', 'v23.0')}"


def configured() -> bool:
    s = db.get_settings()
    return bool(s.get("fb_page_id") and s.get("fb_page_token"))


def _upload_photo(s: dict, path) -> str:
    """Tải 1 ảnh lên Fanpage ở chế độ chưa đăng, trả về id ảnh để gắn vào bài."""
    with open(path, "rb") as f:
        r = httpx.post(f"{GRAPH}/{s['fb_page_id']}/photos", data={"published": "false", "access_token": s["fb_page_token"]},
                       files={"source": (os.path.basename(str(path)), f)}, timeout=120)
    data = r.json()
    if r.status_code != 200 or not data.get("id"):
        raise RuntimeError("Tải ảnh lên Fanpage lỗi: " + str(data.get("error", {}).get("message", r.text))[:200])
    return data["id"]


def publish_page(message: str, images: list | None = None) -> dict:
    """Đăng bài kèm ảnh lên Fanpage. Sếp quy định bài phải có ảnh: không có ảnh thì không đăng."""
    import json

    import media_folder
    s = db.get_settings()
    if not configured():
        return {"ok": False, "error": "Chưa cấu hình Page ID và Page Access Token trong Cài đặt"}
    images = list(images or [])
    if not images and media_folder.required():
        return {"ok": False, "no_image": True, "error": "Bài chưa có ảnh nên không đăng lên Fanpage (sếp quy định bài phải có ảnh)"}
    try:
        data = {"message": message, "access_token": s["fb_page_token"]}
        ids = [_upload_photo(s, p) for p in images]
        for i, fid in enumerate(ids):
            data[f"attached_media[{i}]"] = json.dumps({"media_fbid": fid})
        r = httpx.post(f"{GRAPH}/{s['fb_page_id']}/feed", data=data, timeout=30)
        data = r.json()
        if r.status_code == 200 and data.get("id"):
            return {"ok": True, "id": data["id"], "url": f"https://facebook.com/{data['id']}", "images": [str(p) for p in images]}
        err = data.get("error", {}).get("message", r.text)
    except Exception as e:
        err = str(e)
    import errors
    errors.report("fanpage", "Đăng Fanpage bị lỗi", str(err)[:400], screen="setup")
    return {"ok": False, "error": err}


def comments(post_id: str, limit: int = 100) -> list[dict]:
    """Bình luận dưới một bài của Fanpage (Graph API, quyền pages_read_engagement). Chỉ đọc."""
    s = db.get_settings()
    r = httpx.get(f"{GRAPH}/{post_id}/comments", params={"fields": "from,message,created_time", "limit": limit,
                                                          "filter": "stream", "access_token": s["fb_page_token"]}, timeout=30)
    d = r.json()
    if "error" in d:
        raise RuntimeError(d["error"].get("message", "Graph API lỗi"))
    return d.get("data") or []


def publish_post(post: dict) -> dict:
    """Chọn ảnh cho bài rồi đăng lên Fanpage; ghi lại ảnh đã dùng để lần sau không trùng."""
    import media_folder
    imgs, _ = media_folder.pick_for_post(post)
    if not imgs and media_folder.required():
        why = media_folder.missing(post) or "Bài chưa có ảnh nên không đăng lên Fanpage (sếp quy định bài phải có ảnh)"
        db.run("UPDATE posts SET status='approved', scheduled_for=NULL, error=? WHERE id=?", (why[:300], post["id"]))
        return {"ok": False, "no_image": True, "error": why}
    res = publish_page(f"{post['content']}\n\n{post.get('hashtags') or ''}".strip(), imgs)
    if res["ok"]:
        media_folder.record(imgs, "post", post)
        db.run("UPDATE posts SET images_used=? WHERE id=?", (json.dumps([str(i) for i in imgs], ensure_ascii=False), post["id"]))
    return res

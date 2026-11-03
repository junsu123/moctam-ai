"""Đăng bài lên Fanpage qua Facebook Graph API (cách chính thức, an toàn).

Lưu ý: Meta đã gỡ Groups API từ 4/2024 và không cho ứng dụng đăng lên trang cá nhân,
nên bài cho hội nhóm/trang cá nhân được hệ thống chuẩn bị sẵn để nhân viên bấm đăng.
"""
import os

import httpx

import db

GRAPH = f"https://graph.facebook.com/{os.getenv('FB_GRAPH_VERSION', 'v23.0')}"


def configured() -> bool:
    s = db.get_settings()
    return bool(s.get("fb_page_id") and s.get("fb_page_token"))


def publish_page(message: str) -> dict:
    s = db.get_settings()
    if not configured():
        return {"ok": False, "error": "Chưa cấu hình Page ID và Page Access Token trong Cài đặt"}
    try:
        r = httpx.post(f"{GRAPH}/{s['fb_page_id']}/feed",
                       data={"message": message, "access_token": s["fb_page_token"]}, timeout=30)
        data = r.json()
        if r.status_code == 200 and data.get("id"):
            return {"ok": True, "id": data["id"], "url": f"https://facebook.com/{data['id']}"}
        err = data.get("error", {}).get("message", r.text)
    except Exception as e:
        err = str(e)
    import errors
    errors.report("fanpage", "Đăng Fanpage bị lỗi", str(err)[:400], screen="setup")
    return {"ok": False, "error": err}

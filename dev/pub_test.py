"""Chạy thẳng _publish với Facebook giả lập các kiểu giao diện thật."""
import os, sys, time, json
os.environ["FB_BASE_URL"] = "http://localhost:8098"
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "backend"))
from pathlib import Path
SP = Path(__import__("os").environ.get("MT_WORK") or Path(__file__).resolve().parent / "work")
import db
db.DB_PATH = SP / "pub.db"; db.DB_PATH.unlink(missing_ok=True); db.PROFILES_DIR = SP / "pub_profiles"; db.SHOTS_DIR = SP / "pub_shots"; db.SHOTS_DIR.mkdir(exist_ok=True); db.init()
import browser_poster as B
from playwright.sync_api import sync_playwright
imgs = sorted((SP / "pubimg").glob("*.png"))[:2]
cases = [("nhóm thật", "http://localhost:8098/groups/real", "group"),
         ("trang cá nhân (Tiếp → Đăng)", "http://localhost:8098/realme", "profile"),
         ("nhóm chưa tham gia", "http://localhost:8098/groups/notmember", "group"),
         ("nhóm cũ (mock đơn giản)", "http://localhost:8098/groups/abc", "group")]
post = {"id": 1, "target_type": "group", "content": "Trà gừng mật ong 🌿\nGiá sỉ tận xưởng\n\nInbox nhé", "hashtags": "#trasi"}
with sync_playwright() as pw:
    for name, url, kind in cases[int(sys.argv[1]) if len(sys.argv) > 1 else 0:][: (1 if len(sys.argv) > 1 else 9)]:
        ctx = B._launch(pw, 1, headless=True); page = ctx.new_page()
        t = time.time()
        try:
            post["target_type"] = kind; r = B._publish(page, post, url, B.selectors()[f"{kind}_composer"], False, imgs)
            print("OK ", name, r, f"{time.time()-t:.0f}s")
        except Exception as e:
            print("ERR", name, "->", str(e).splitlines()[0][:220], f"{time.time()-t:.0f}s")
        ctx.close()
print(open(SP / "mockfb_log.jsonl").read().strip().splitlines()[-2:])

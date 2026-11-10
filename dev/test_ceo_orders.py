"""Sếp giao việc cho CEO (chế độ chưa có khóa AI): hiểu lệnh, chia việc, sửa agent, chỉ đạo, tự duyệt bài."""
import sys, time
from pathlib import Path
sys.path.insert(0, "/home/claude/ai-sales-company/backend")
SP = Path(__import__("os").environ.get("MT_WORK") or Path(__file__).resolve().parent / "work")
import db
db.DB_PATH = SP / "orders.db"; db.DB_PATH.unlink(missing_ok=True); db.init()
db.set_setting("browser_headless","1"); db.run("INSERT INTO sales(name, fb_name, login_status, auto_post, created_at) VALUES ('Linh','Linh Nguyễn','ok',1,?)", (db.now(),))
import accounts; accounts.set_login(accounts.create(1, "Linh Nguyễn")["id"], "ok")
import ceo_orders as O, agents
for t in ["Tình hình hôm nay thế nào?", "Viết 2 bài về trà gừng mật ong", "Lan viết bài dài quá, viết dưới 150 chữ thôi",
          "Tuấn xếp lịch sai nhóm, đừng đăng nhóm du lịch", "Từ nay bài nào cũng nhắc giao hàng toàn quốc",
          "Tạm dừng Linh", "Bật lại Linh", "Tìm nhóm theo chủ đề “hội chạy quảng cáo facebook”, “sỉ trà túi lọc”",
          "Họp về giá sỉ mùa Tết", "abc xyz"]:
    r = O.handle(t)
    print(f"» {t}\n  {r['reply'].replace(chr(10), ' | ')[:230]}")
    time.sleep(0.3)
time.sleep(3)
print("Bài học ghim của Lan:", [l["text"][:50] for l in db.q("SELECT text FROM lessons WHERE agent_id='lan' AND pinned=1")])
print("Chỉ đạo đang áp dụng:", [(o["agent"], o["text"][:40]) for o in O.orders()])
print("Prompt của Lan có chỉ đạo:", "giao hàng toàn quốc" in agents.system_prompt("lan", {}), "| có bài học:", "150 chữ" in agents.system_prompt("lan", {}))
# CEO tự duyệt bài
db.run("UPDATE posts SET created_at=datetime('now','-1 hour','localtime')")
pid = db.run("INSERT INTO posts(agent_id, target_type, title, content, status, created_at) VALUES ('lan','group','x',?, 'draft', datetime('now','-1 hour','localtime'))",
             ("Trà gừng giúp chữa khỏi bệnh dạ dày " * 10,))
print("Trước khi duyệt:", db.q("SELECT status, COUNT(*) n FROM posts GROUP BY status"))
print("CEO duyệt:", O.review_drafts(), "| bài hứa chữa bệnh:", db.one("SELECT status FROM posts WHERE id=?", (pid,))["status"],
      "| lý do:", db.one("SELECT reason FROM feedback WHERE post_id=? AND kind='reject'", (pid,))["reason"])

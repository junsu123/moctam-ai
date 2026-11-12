import sys, shutil, json, itertools
import os; sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "backend"))
from pathlib import Path
from datetime import timedelta
SP = Path(__import__("os").environ.get("MT_WORK") or Path(__file__).resolve().parent / "work")
import db
db.DB_PATH = SP / "policy.db"; db.DB_PATH.unlink(missing_ok=True)
db.PROFILES_DIR = SP / "policy_profiles"; shutil.rmtree(db.PROFILES_DIR, ignore_errors=True); db.PROFILES_DIR.mkdir()
db.init(); db.set_setting("bump_folder", str(SP / "img2_folder"))
import fb_policy as F, accounts, workflows, post_template, ceo_review, browser_poster as B
from fastapi.testclient import TestClient
import main
c = TestClient(main.app)
print("1. luật đã dạy:", {a: db.one("SELECT COUNT(*) n FROM knowledge WHERE agent_id=? AND topic LIKE 'Luật Facebook:%'", (a,))["n"] for a in ("lan", "ceo", "tuan", "sale", "vy")})
print("   lời dặn agent có luật:", "LUẬT FACEBOOK" in __import__("agents").system_prompt("lan", db.get_settings()))
bad = ("Trà detox giảm 5kg trong 7 ngày, chữa dứt điểm mỡ máu! Tốt nhất thị trường, cam kết 100% hiệu quả. Like và share để nhận quà, "
       "tag 3 người bạn. Xem thêm bit.ly/abc #tra #detox #giamcan #healthy #eatclean #sach #ngon #re")
for i in F.check_text(bad): print(f"   [{i['level']}] {i['rule']}: {i['msg']} ({i['hit']})")
good = post_template.make_posts(1)[0]["content"] if post_template.make_posts else ""
print("2. bài mẫu của sếp:", F.check_text(good) or "không phạm luật")
# 3. biến thể bài mẫu giống nhau bao nhiêu
vs = [post_template.variant(post_template.samples(True)[0]["content"]) for _ in range(8)]
sims = [F._similar(a, b) for a, b in itertools.combinations(vs, 2)]
print(f"3. độ giống giữa các biến thể bài mẫu: thấp nhất {min(sims):.2f}, cao nhất {max(sims):.2f}, trung bình {sum(sims)/len(sims):.2f}")
# 4. giới hạn nick
sid = c.post("/api/sales", json={"name": "Linh", "fb_name": "Linh Nguyễn"}).json()["id"]; aid = accounts.of_sale(sid)[0]["id"]
db.run("UPDATE fb_accounts SET created_at=? WHERE id=?", ((db.clock() - timedelta(days=60)).strftime("%Y-%m-%d %H:%M:%S"), aid))
acc = db.one("SELECT * FROM fb_accounts WHERE id=?", (aid,)); print("4. giới hạn nick cũ:", F.limits(acc))
db.run("UPDATE fb_accounts SET created_at=? WHERE id=?", (db.now(), aid)); print("   nick mới tạo:", F.limits(db.one("SELECT * FROM fb_accounts WHERE id=?", (aid,))))
db.run("UPDATE fb_accounts SET created_at=? WHERE id=?", ((db.clock() - timedelta(days=60)).strftime("%Y-%m-%d %H:%M:%S"), aid))
g = db.run("INSERT INTO groups(name, url, created_at) VALUES ('Nhóm A','https://www.facebook.com/groups/a',?)", (db.now(),))
t1 = (db.clock() - timedelta(minutes=10)).strftime("%Y-%m-%d %H:%M:%S")
db.run("INSERT INTO posts(agent_id, target_type, group_id, title, content, status, account_id, sale_id, posted_at, created_at) VALUES ('lan','group',?,?,?,'posted',?,?,?,?)",
       (g, "x", "bài cũ", aid, sid, t1, t1))
print("   vừa đăng 10 phút trước:", F.allow(aid, "post"))
db.run("UPDATE posts SET posted_at=? WHERE account_id=?", ((db.clock() - timedelta(hours=2)).strftime("%Y-%m-%d %H:%M:%S"), aid))
print("   cùng nhóm 2 giờ trước:", F.allow(aid, "post", g)[:2], "| nhóm khác:", F.allow(aid, "post", None)[:2])
for k in range(5):
    tk = (db.clock() - timedelta(hours=3, minutes=k * 40)).strftime("%Y-%m-%d %H:%M:%S")
    if tk[:10] == db.today():
        db.run("INSERT INTO posts(agent_id, target_type, title, content, status, account_id, sale_id, posted_at, created_at) VALUES ('lan','profile','x',?, 'posted',?,?,?,?)", (f"b{k}", aid, sid, tk, tk))
print("   đăng đủ trần:", F.used_today(aid)["posts"], F.allow(aid, "post")[:2])
# 5. sự cố
print("5. nick bị chặn:", F.on_block(aid, "Facebook báo bạn thao tác quá nhanh")["lesson"])
print("   sau đó:", F.allow(aid, "post")[:2], "| hệ số:", F.limits(db.one("SELECT * FROM fb_accounts WHERE id=?", (aid,)))["factor"])
for k in range(2):
    pid = db.run("INSERT INTO posts(agent_id, target_type, group_id, title, content, status, account_id, created_at) VALUES ('lan','group',?,'x','y','posted',?,?)", (g, aid, db.now()))
    F.on_removed(db.one("SELECT * FROM posts WHERE id=?", (pid,)))
print("   nhóm gỡ 2 bài:", F.rest_group_until(g), "| bài học:", db.one("SELECT lesson FROM fb_incidents ORDER BY id DESC LIMIT 1")["lesson"][:90])
# 6. giữ bài lúc đăng
db.run("UPDATE fb_accounts SET rest_until=NULL WHERE id=?", (aid,))
bp = db.run("INSERT INTO posts(agent_id, target_type, title, content, status, account_id, sale_id, scheduled_for, created_at) VALUES ('lan','profile','x',?, 'scheduled',?,?,?,?)",
            ("Trà gừng chữa khỏi bệnh dạ dày, inbox Zalo 0386992326", aid, sid, db.now()[:16], db.now()))
print("6. bài hứa chữa bệnh lúc đăng: giữ =", B._policy_hold(db.one("SELECT * FROM posts WHERE id=?", (bp,)), aid, "sale-1"),
      db.one("SELECT status, policy_note FROM posts WHERE id=?", (bp,)))
op = db.run("INSERT INTO posts(agent_id, target_type, title, content, status, account_id, sale_id, scheduled_for, created_at) VALUES ('lan','profile','x',?, 'scheduled',?,?,?,?)",
            ("MỘC TÂM nhận gia công trà túi lọc, ib Zalo 0386992326 nhận catalog", aid, sid, db.now()[:16], db.now()))
print("   bài sạch nhưng nick hết trần: giữ =", B._policy_hold(db.one("SELECT * FROM posts WHERE id=?", (op,)), aid, "sale-1"),
      db.one("SELECT status, scheduled_for, error FROM posts WHERE id=?", (op,)))
# 7. CEO duyệt
r = ceo_review.review(bad); print("7. CEO chấm bài xấu:", r["score"], r["ok"], [x[:60] for x in r["reasons"][:3]])
# 8. theo dõi chính sách (giả trang)
pages = {"v": 1}
fake = lambda url: ("Chính sách Spam\n" + "\n".join(f"Dòng luật {i}" for i in range(40)) + ("\nDòng mới: cấm đăng quá 10 nhóm/giờ" if pages["v"] == 2 and "spam/" in url else ""))
print("8. lần 1:", F.check_sources(fetch=fake))
pages["v"] = 2
print("   lần 2:", {k: v for k, v in F.check_sources(fetch=fake).items() if k != "new"}, db.q("SELECT name, summary FROM fb_policy_changes"))
print("   watch_due ngay sau khi đọc:", F.watch_due())
o = c.get("/api/fb-policy").json(); print("9. API:", len(o["rules"]), "luật,", len(o["sources"]), "nguồn,", len(o["incidents"]), "sự cố,", len(o["nicks"]), "nick,", o["flagged"], "bài bị gắn cờ")
print("   kiểm chữ:", c.post("/api/fb-policy/check", json={"text": "Số 1 Việt Nam"}).json())
c.post("/api/fb-policy/rules", json={"title": "Không nhắc đối thủ", "phrases": ["Trà Phúc Long"], "level": "high"})
print("   luật sếp thêm:", F.check_text("Ngon hơn Trà Phúc Long"), "| có trong lời dặn:", "Không nhắc đối thủ" in F.prompt_rule())
print("   sửa giới hạn:", c.put("/api/fb-policy/settings", json={"fbp_posts_day": "5"}).json()["settings"]["fbp_posts_day"], c.put("/api/fb-policy/settings", json={"xx": 1}).status_code)
print("lỗi:", [e["title"] for e in db.q("SELECT title FROM errors")])

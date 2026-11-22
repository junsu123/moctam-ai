"""Các Trang của Nhi: từ khóa sếp đặt, chia chủ đề cho các Trang, sếp duyệt / sửa / loại, Nhi ghi nhớ theo sếp (không cần Chrome)."""
import os, sys
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "backend"))
from pathlib import Path
from datetime import timedelta
SP = Path(os.environ.get("MT_WORK") or Path(__file__).resolve().parent / "work")
import db
db.DB_PATH = SP / "pagebrain.db"; db.DB_PATH.unlink(missing_ok=True)
db.init(); db.set_setting("anthropic_api_key", "")
from fastapi.testclient import TestClient
import main, accounts, trend_pages as T, telegram_bot as TG, page_brain as B
c = TestClient(main.app)
ok = []
def chk(name, cond, extra=""):
    ok.append(bool(cond)); print(("   ✓ " if cond else "   ✗ ") + name, extra)
sent = []
TG.configured = lambda: True
TG.send = lambda text, *a, **k: sent.append(text) or [{"message_id": 700 + len(sent)}]
sid = c.post("/api/sales", json={"name": "Linh", "fb_name": "Linh Nguyễn"}).json()["id"]
aid = accounts.of_sale(sid)[0]["id"]
def page(name, niche):
    pid = db.run("INSERT INTO fb_pages(name, niche, status, url, admin_account_id, posts_per_day, times, created_at) VALUES (?,?,'active',?,?,2,'09:00,19:30',?)",
                 (name, niche, "https://facebook.com/" + name.replace(" ", ""), aid, db.now()))
    return pid
bep, meo = page("Bếp Nhà Mình", "nấu ăn gia đình"), page("Góc Thú Cưng", "nuôi chó mèo")
r = c.put(f"/api/nhi-pages/{bep}", json={"keywords": "món chay, canh chua; mẹo nấu cơm, món chay", "avoid": "rượu bia", "boss_note": "Giọng thân mật, xưng mình"}).json()
chk("sếp đặt từ khóa cho Trang (bỏ trùng), chủ đề tránh, lời dặn", r["keywords"] == "món chay, canh chua, mẹo nấu cơm" and r["avoid"] == "rượu bia", r["keywords"])
c.put(f"/api/nhi-pages/{meo}", json={"keywords": "chăm mèo con, hạt cho chó"})
for t, s, n in [("mẹo nuôi mèo con", 88, "thú cưng"), ("canh chua cá lóc", 80, "ẩm thực"), ("rượu bia ngày tết", 75, "ẩm thực")]:
    db.run("INSERT INTO trend_hot(day, title, score, niche, why, created_at) VALUES (?,?,?,?,?,?)", (db.today(), t, s, n, "tăng mạnh", db.now()))
pb, pm = db.one("SELECT * FROM fb_pages WHERE id=?", (bep,)), db.one("SELECT * FROM fb_pages WHERE id=?", (meo,))
cb, cm = B.choose(pb), B.choose(pm)
chk("tin nóng giao đúng Trang hợp nhất (canh chua → Bếp, mèo con → Thú Cưng)", cb["topic"] == "canh chua cá lóc" and cm["topic"] == "mẹo nuôi mèo con"
    and cb["kw"] == "canh chua", (cb["topic"], cm["topic"]))
n0 = len(sent)
when = (db.clock() + timedelta(hours=2)).strftime("%Y-%m-%d %H:%M")
p1 = T.write_post(pb, when)
chk("bật duyệt: bài chờ sếp duyệt, gửi Telegram tin duyệt (chưa xin ảnh), lưu từ khóa và bản nháp", p1["status"] == "page_review" and len(sent) == n0 + 1
    and "Bài chờ duyệt" in sent[-1] and "Cần ảnh" not in sent[-1]
    and p1["page_kw"] == "canh chua" and p1["nhi_draft"] == p1["content"], p1["status"])
p2 = T.write_post(db.one("SELECT * FROM fb_pages WHERE id=?", (bep,)), when)
chk("tin nóng đã dùng không giao lại; tin có chủ đề sếp tránh bị bỏ; bài sau viết theo từ khóa", p2["trend_kind"] == "evergreen"
    and p2["page_kw"] in ("món chay", "mẹo nấu cơm") and "rượu" not in (p2["trend_topic"] or ""), (p2["trend_topic"], p2["page_kw"]))
br = B.brief(pb, "món chay")
chk("đề bài có ngành nghề, từ khóa, chủ đề tránh, lời dặn sếp", "nấu ăn gia đình" in br and "món chay" in br and "rượu bia" in br and "xưng mình" in br)
d = c.get("/api/nhi-pages").json()
chk("màn Các Trang của Nhi: 2 Trang, hàng chờ duyệt 2 bài, thống kê từ khóa", len(d["pages"]) == 2 and len(d["queue"]) == 2 and d["review"]
    and next(p for p in d["pages"] if p["id"] == bep)["kw"][0]["kw"] == "món chay")
a = c.post(f"/api/nhi-pages/posts/{p1['id']}/review", json={"action": "approve"}).json()
chk("duyệt ngay: bài chờ ảnh, gửi prompt ảnh lên Telegram", a["status"] == "need_image" and a["review_result"] == "ok" and "Cần ảnh" in sent[-1])
short = "Canh chua cá lóc kiểu miền Tây, mình nấu 15 phút là xong. Nhà bạn hay nấu với cá gì?"
B.review(p2["id"], "approve", short, wait=True)
mem = B.memory(bep)
chk("sếp sửa rồi duyệt: lưu bản sếp, Nhi rút bài học (ngắn hơn)", db.one("SELECT content, review_result FROM posts WHERE id=?", (p2["id"],))["review_result"] == "edit"
    and any(m["kind"] == "lesson" and "ngắn" in m["text"] for m in mem), [m["text"] for m in mem])
p3 = T.write_post(db.one("SELECT * FROM fb_pages WHERE id=?", (bep,)), when)
e = c.post(f"/api/nhi-pages/posts/{p3['id']}/review", json={"action": "approve", "content": "Uống trà này chữa khỏi tiểu đường"})
chk("bản sửa phạm Luật Facebook thì không duyệt được", e.status_code == 400, e.text[:80])
c.post(f"/api/nhi-pages/posts/{p3['id']}/review", json={"action": "reject", "reason": "Giọng văn chưa hợp"})
br = B.brief(db.one("SELECT * FROM fb_pages WHERE id=?", (bep,)), None)
chk("sếp loại có lý do: Nhi ghi nhớ, đề bài lần sau có bài học + bản sếp sửa", "Giọng văn chưa hợp" in br and "ngắn" in br and "15 phút" in br)
c.put(f"/api/nhi-pages/{bep}", json={"teach": "Luôn gợi ý món hợp mùa"})
mid = next(m["id"] for m in B.memory(bep) if m["kind"] == "note")
c.delete(f"/api/nhi-pages/memory/{mid}")
chk("sếp dạy thêm / xóa điều Nhi ghi nhớ", not any(m["kind"] == "note" for m in B.memory(bep)))
s = B.smartness()
chk("Nhi hiểu ý sếp: 1/3 duyệt ngay, chưa đủ 20 lần nên chưa gợi ý tắt duyệt", s["n"] == 3 and s["ok"] == 1 and s["pct"] == 33 and not s["suggest_off"], s)
for i in range(20):
    db.run("INSERT INTO posts(fb_page_ref, source, status, review_result, reviewed_at, created_at) VALUES (?, 'trend_page', 'posted', 'ok', ?, ?)", (meo, db.now(), db.now()))
chk("đủ 20 lần duyệt, từ 85% duyệt ngay: gợi ý sếp tắt duyệt", B.smartness()["suggest_off"])
kws = c.post(f"/api/nhi-pages/{bep}/suggest").json()["keywords"]
chk("Nhi gợi ý thêm từ khóa, không trùng từ khóa đã có", kws and not any(k in ("món chay", "canh chua", "mẹo nấu cơm") for k in kws), kws)
c.put("/api/nhi-pages/settings", json={"review": False})
n1 = len(sent)
p4 = T.write_post(db.one("SELECT * FROM fb_pages WHERE id=?", (meo,)), when)
chk("tắt duyệt: Nhi tự xin ảnh, không chờ sếp", p4["status"] == "need_image" and len(sent) == n1 + 1)
c.put("/api/nhi-pages/settings", json={"review": True})
db.run("UPDATE fb_pages SET posts_per_day=1, times='23:59'"); db.run("DELETE FROM posts WHERE fb_page_ref IS NOT NULL AND status != 'posted'")
db.set_setting("trend_plan_day", "")
n = T.plan_today(force=True)
q = c.get("/api/nhi-pages").json()["queue"]
chk("lên lịch hôm nay: mỗi Trang đủ bài, báo Telegram chờ duyệt", n >= 1 and any("chờ sếp duyệt" in t for t in sent) and q, n)
r = c.post("/api/nhi-pages/approve-all").json()
chk("duyệt tất cả", r["approved"] == len(q) and not c.get("/api/nhi-pages").json()["queue"])
print(f"XONG {sum(ok)}/{len(ok)}" if all(ok) else f"CÓ LỖI {sum(ok)}/{len(ok)}")

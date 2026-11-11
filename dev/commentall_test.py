"""Bình luận đều mọi nhóm: bỏ luật chỉ bình luận bài có từ khóa liên quan, chia đều theo nhóm, giãn cách thời gian gửi."""
import os, sys
from pathlib import Path
from types import SimpleNamespace as NS
from datetime import datetime
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "backend"))
SP = Path(os.environ.get("MT_WORK") or Path(__file__).resolve().parent / "work"); SP.mkdir(exist_ok=True)
import db
db.DB_PATH = SP / "commentall.db"; db.DB_PATH.unlink(missing_ok=True); db.init(); db.set_setting("anthropic_api_key", "")
import group_feed as F, replies, llm as L

ok = []
def check(name, cond): ok.append(bool(cond)); print(("OK  " if cond else "LỖI ") + name)
aid = db.run("INSERT INTO fb_accounts(name, login_status, active_from, active_to, created_at) VALUES ('Nick A','ok','08:00','22:00','2025-01-01 00:00:00')")
db.set_setting("replies_per_nick_day", "10"); db.set_setting("reply_contact", "Zalo 0386992326")
g = [db.run("INSERT INTO groups(name, url, slug, created_at) VALUES (?,?,?,?)", (f"Nhóm {i}", f"https://fb.com/groups/g{i}", f"g{i}", db.now())) for i in range(3)]
db.run("UPDATE groups SET no_selling=1 WHERE id=?", (g[2],))

normal = "Hôm nay shop em vừa khai trương chi nhánh mới ở Thủ Đức, cảm ơn mọi người ủng hộ nhiều nha"
check("bài không có từ khóa liên quan: vẫn bình luận", (F.rule(normal) or {}).get("kind") == "general")
check("bài bán dịch vụ / nhà cung cấp: vẫn bỏ", F.rule("Nhận chạy quảng cáo facebook giá rẻ, bán via bm") is None)
db.set_setting("feed_comment_all", "0")
check("tắt: quay lại luật cũ (chỉ bài liên quan)", F.rule(normal) is None)
db.set_setting("feed_comment_all", "1")

def rows(gi, n, start):
    return [{"link": f"https://fb.com/groups/g{gi}/posts/{start + k}", "author": f"Người {gi}-{k}", "gname": f"Nhóm {gi}",
             "text": f"Người {gi}-{k} Nhóm {gi} " + normal + f" lần {k}", "href": f"https://fb.com/u{gi}{k}", "group_href": f"https://fb.com/groups/g{gi}"}
            for k in range(n)]
F._group = lambda a, r: db.one("SELECT * FROM groups WHERE slug=?", (r["group_href"].rsplit("/", 1)[-1],))
items = F.pick(rows(0, 6, 0) + rows(1, 1, 100) + rows(2, 2, 200), aid)
check(f"chọn {len(items)} bài từ 3 nhóm", len(items) == 9 and {i["kind"] for i in items} == {"general"})

class Fake:
    def create(self, **kw):
        n = kw["messages"][0]["content"].count(" lần ")
        items = [{"i": i + 1, "type": "general", "score": 55, "reason": "bài khai trương", "reply": f"Chúc mừng shop khai trương, buôn may bán đắt nha {i}"} for i in range(n)]
        return NS(stop_reason="tool_use", usage=NS(input_tokens=5, output_tokens=5), content=[NS(type="tool_use", input={"ket_qua": {"items": items}})])
L.llm.client = NS(messages=Fake())
res = F.save(items, aid)
tasks = db.q("SELECT group_id, reply FROM reply_tasks")
by = {x: sum(1 for t in tasks if t["group_id"] == x) for x in g}
check(f"chia đều: mỗi nhóm tối đa 2 câu {by} ({res})", by[g[0]] == 2 and by[g[1]] == 1 and by[g[2]] == 2)
check("kèm Zalo ở nhóm thường", all("Zalo" in t["reply"] for t in tasks if t["group_id"] != g[2]))
check("nhóm cấm bán hàng: không kèm Zalo", all("Zalo" not in t["reply"] for t in tasks if t["group_id"] == g[2]))
res2 = F.save(F.pick(rows(0, 6, 50), aid), aid)
check("nhóm đã đủ 2 câu hôm nay: không thêm", res2["general"] == 0)

# giãn cách: 08–22 = 840 phút / 10 câu = 84 phút (± 15%), không dưới 60
a = db.one("SELECT * FROM fb_accounts WHERE id=?", (aid,))
gaps = [replies.gap_minutes(a, 10) for _ in range(200)]
check(f"giãn cách dàn đều giờ làm: {min(gaps)}–{max(gaps)} phút", 70 <= min(gaps) and max(gaps) <= 97)
db.set_setting("reply_gap_min", "120")
check("giãn cách tối thiểu sếp đặt 120 phút", min(replies.gap_minutes(a, 10) for _ in range(100)) >= 102)
ids = [r["id"] for r in db.q("SELECT id FROM reply_tasks ORDER BY id")]
_d = db.today(); db.clock = lambda: datetime.strptime(_d + " 09:00", "%Y-%m-%d %H:%M")
times = [replies.approve(i)["scheduled_for"] for i in ids[:3]]
ts = [datetime.strptime(t, "%Y-%m-%d %H:%M") for t in times if t]
check(f"lịch gửi: {times}", len(ts) == 3 and all((b - a_).total_seconds() / 60 >= 102 for a_, b in zip(ts, ts[1:])))

from fastapi.testclient import TestClient
import main
c = TestClient(main.app)
check("cài đặt: mỗi nhóm tối đa 3", c.put("/api/feed-settings", json={"feed_per_group_day": "5"}).status_code == 400
      and c.put("/api/feed-settings", json={"feed_per_group_day": "1", "reply_gap_min": "90", "feed_comment_all": "1"}).status_code == 200)
print(("XONG" if all(ok) else "CÓ LỖI") + f" {sum(ok)}/{len(ok)}")

"""Bảng sức khỏe từng nick: điểm từ dấu hiệu rủi ro, tự giảm trần nick xấu, báo Telegram (không cần Chrome)."""
import os, sys
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "backend"))
from pathlib import Path
from datetime import timedelta
SP = Path(os.environ.get("MT_WORK") or Path(__file__).resolve().parent / "work")
import db
db.DB_PATH = SP / "nickhealth.db"; db.DB_PATH.unlink(missing_ok=True)
db.init(); db.set_setting("anthropic_api_key", "")
from fastapi.testclient import TestClient
import main, accounts, fb_policy, nick_health
c = TestClient(main.app)
ok = []
def chk(name, cond, extra=""):
    ok.append(bool(cond)); print(("   ✓ " if cond else "   ✗ ") + name, extra)
sid = c.post("/api/sales", json={"name": "Linh", "fb_name": "Nick Khỏe"}).json()["id"]
a1 = accounts.of_sale(sid)[0]["id"]
a2 = accounts.create(sid, "Nick Hay Bị Xóa")["id"]
a3 = accounts.create(sid, "Nick Vừa Bị Chặn")["id"]
db.run("UPDATE fb_accounts SET login_status='ok', created_at='2025-01-01 00:00:00'")
ago = lambda **kw: (db.clock() - timedelta(**kw)).strftime("%Y-%m-%d %H:%M:%S")
L0 = fb_policy.limits(accounts.get(a2))
# nick 2: 3 bài bị gỡ, 3 bình luận bị nhóm xóa, mời kết bạn 12 người chỉ 2 người đồng ý
for i in range(3):
    db.run("INSERT INTO fb_incidents(account_id, kind, detail, created_at) VALUES (?, 'removed', 'x', ?)", (a2, ago(days=i + 1)))
    db.run("INSERT INTO bumps(post_id, account_id, status, removed, checked_at, created_at) VALUES (1, ?, 'done', 1, ?, ?)", (a2, ago(days=i), ago(days=i)))
for i in range(12):
    db.run("INSERT INTO friend_suggestions(account_id, name, profile_url, status, sent_at, created_at) VALUES (?,?,?,?,?,?)",
           (a2, f"n{i}", f"u{i}", "accepted" if i < 2 else "sent", ago(days=2), ago(days=2)))
# nick 3: bị chặn hôm qua + đang checkpoint
db.run("INSERT INTO fb_incidents(account_id, kind, detail, created_at) VALUES (?, 'block', 'checkpoint', ?)", (a3, ago(days=1)))
db.run("UPDATE fb_accounts SET login_status='checkpoint' WHERE id=?", (a3,))
nick_health._cache.clear()
d = c.get("/api/nick-health").json()
by = {r["id"]: r for r in d["items"]}
chk("nick sạch: 100 điểm, Khỏe, chạy đủ trần", by[a1]["score"] == 100 and by[a1]["level"] == "good" and by[a1]["factor"] == 1, by[a1]["score"])
chk("nick hay bị xóa: Cần để ý / Nguy hiểm, có lý do và việc nên làm", by[a2]["level"] in ("warn", "bad") and len(by[a2]["signals"]) == 3
    and by[a2]["advice"], (by[a2]["score"], [s["text"] for s in by[a2]["signals"]]))
chk("nick vừa bị chặn + checkpoint: Nguy hiểm, xếp đầu bảng", by[a3]["level"] == "bad" and d["items"][0]["id"] == a3, by[a3]["score"])
L1 = fb_policy.limits(accounts.get(a2))
chk("nick xấu tự giảm trần Luật Facebook", L1["bumps"] < L0["bumps"] and L1["gap"] > L0["gap"], (L0, L1))
c.put("/api/nick-health/settings", json={"auto": 0})
chk("tắt tự giảm: chạy đủ trần lại", fb_policy.limits(accounts.get(a2))["bumps"] == L0["bumps"])
c.put("/api/nick-health/settings", json={"auto": 1})
sent = []
import telegram_bot
telegram_bot.configured = lambda: True; telegram_bot.send = lambda t, *a, **k: sent.append(t) or []
db.set_setting("tg_alert_nick", "1")
nick_health.tick(db.clock()); nick_health.tick(db.clock())
chk("nick Nguy hiểm báo Telegram một lần", len(sent) == len([r for r in d["items"] if r["level"] == "bad"]) >= 1 and "Vừa Bị Chặn" in sent[0], sent[:1])
db.set_setting("nick_health_last", "")
nick_health.tick(db.clock())
chk("giờ sau không báo lại trong ngày", len(sent) == len([r for r in d["items"] if r["level"] == "bad"]))
print(("XONG" if all(ok) else "CÓ LỖI") + f" {sum(ok)}/{len(ok)}")

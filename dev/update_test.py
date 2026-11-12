"""Sếp nhắn CEO “cập nhật phần mềm” / /capnhat: git pull bản mới, chờ rảnh, tự khởi động lại, chạy xong báo lại."""
import os, sys, shutil, subprocess, time, json
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "backend"))
SP = Path(os.environ.get("MT_WORK") or Path(__file__).resolve().parent / "work"); SP.mkdir(exist_ok=True)
os.environ["UPDATE_CHECK_ALIVE_S"] = "1"
import db
db.DB_PATH = SP / "update.db"; db.DB_PATH.unlink(missing_ok=True); db.init(); db.set_setting("anthropic_api_key", "")
import updater as U, ceo_orders, telegram_bot

ok = []
def check(name, cond): ok.append(bool(cond)); print(("OK  " if cond else "LỖI ") + name)
said = []
ceo_orders.followup = lambda text, via="web": said.append((text, via))
def g(cwd, *a): return subprocess.run(["git", "-C", str(cwd), "-c", "user.email=t@t", "-c", "user.name=t", *a], capture_output=True, text=True)

W = SP / "upd"; shutil.rmtree(W, ignore_errors=True); W.mkdir()
remote, dev, app = W / "remote.git", W / "dev", W / "app"
g(W, "init", "-q", "--bare", "-b", "main", str(remote)); g(W, "clone", "-q", str(remote), str(dev))
(dev / "backend").mkdir(); (dev / "backend" / "x.py").write_text("A=1\n"); (dev / "README.md").write_text("v1\n")
g(dev, "add", "-A"); g(dev, "commit", "-qm", "bản đầu"); g(dev, "push", "-q", "origin", "HEAD:main")
g(W, "clone", "-q", str(remote), str(app))
U.ROOT = app
restarts = []; idle = {"v": True}
U.restart_hook = lambda reason: restarts.append(reason) or True
U.idle_hook = lambda: idle["v"]

r = ceo_orders.handle("cập nhật phần mềm", via="telegram")
check("đang mới nhất: báo không cần khởi động lại", "mới nhất" in r["reply"] and not restarts)

(dev / "backend" / "x.py").write_text("A=2\n"); g(dev, "commit", "-qam", "Sửa lỗi đăng bài"); g(dev, "push", "-q", "origin", "HEAD:main")
r = ceo_orders.handle("Cập nhật phần mềm giúp anh", via="telegram")
time.sleep(2.5)
check("tải bản mới về máy", (app / "backend" / "x.py").read_text() == "A=2\n")
check("CEO báo nội dung bản mới", "Sửa lỗi đăng bài" in r["reply"] and "khởi động lại" in r["reply"])
check("tự khởi động lại khi rảnh", restarts == ["update"])
check("bản mới không lên: báo vẫn chạy bản cũ", any("chưa chạy được" in t for t, v in said) and said[-1][1] == "telegram")

said.clear(); restarts.clear()
(dev / "README.md").write_text("v2\n"); g(dev, "commit", "-qam", "Sửa hướng dẫn"); g(dev, "push", "-q", "origin", "HEAD:main")
r = ceo_orders.handle("update code", via="web")
check("chỉ đổi tài liệu: không khởi động lại", "không cần khởi động lại" in r["reply"] and not restarts)

(dev / "backend" / "x.py").write_text("A=3\n"); g(dev, "commit", "-qam", "Thêm tính năng"); g(dev, "push", "-q", "origin", "HEAD:main")
idle["v"] = False; U.WAIT_IDLE_S = 0
r = ceo_orders.handle("cập nhật phần mềm", via="web")
check("sale đang bận: chờ xong việc", "đang làm dở" in r["reply"])
time.sleep(2.5); idle["v"] = True

# bản mới chạy lên: báo lại sếp
said.clear()
db.set_setting("update_pending", json.dumps({"to": U._head(), "via": "telegram"}))
U.after_start(); time.sleep(5.5)
check("bản mới chạy: báo đã cập nhật xong", said and "Đã cập nhật xong" in said[0][0] and said[0][1] == "telegram"
      and not db.get_settings().get("update_pending"))

# sếp sửa tay file trùng bản mới: không ghi đè
(app / "backend" / "x.py").write_text("A=sếp sửa\n")
(dev / "backend" / "x.py").write_text("A=4\n"); g(dev, "commit", "-qam", "bản 4"); g(dev, "push", "-q", "origin", "HEAD:main")
r = U.pull()
check("file sửa tay: không ghi đè, nói rõ file", not r["ok"] and "backend/x.py" in r["msg"]
      and (app / "backend" / "x.py").read_text() == "A=sếp sửa\n")

U.ROOT = W / "khong-git"; U.ROOT.mkdir()
check("không phải thư mục git: hướng dẫn tải bằng git clone", "git clone" in U.pull()["msg"])

check("Telegram có lệnh /capnhat", "/capnhat" in telegram_bot.HELP)
check("câu khác không bị hiểu nhầm là cập nhật", not __import__("re").search(ceo_orders.UPDATE_RX, "viết 3 bài về trà gừng"))
print(f"XONG {sum(ok)}/{len(ok)}")

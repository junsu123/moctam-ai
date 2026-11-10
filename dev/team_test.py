"""Sếp đổi tên và ảnh mặt agent: tên mới vào lời dặn, CEO hiểu tên mới, ảnh cắt vuông, về mặc định."""
import os, sys, io, base64
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "backend"))
SP = Path(os.environ.get("MT_WORK") or Path(__file__).resolve().parent / "work"); SP.mkdir(exist_ok=True)
import db
db.DB_PATH = SP / "team.db"; db.DB_PATH.unlink(missing_ok=True); db.DATA_DIR = SP / "team_data"; db.init(); db.set_setting("anthropic_api_key", "")
import agents, ceo_orders
from fastapi.testclient import TestClient
import main
c = TestClient(main.app)
from PIL import Image

ok = []
def check(name, cond): ok.append(bool(cond)); print(("OK  " if cond else "LỖI ") + name)

r = c.put("/api/agents/lan", json={"name": "  Ngọc  "})
check("đổi tên Lan -> Ngọc", r.status_code == 200 and r.json()["name"] == "Ngọc")
check("lời dặn: agent tự gọi tên mới", "Bạn tên là Ngọc" in agents.system_prompt("lan", db.get_settings())
      and "Ngọc viết bài" in agents.system_prompt("ha", db.get_settings()))
check("danh sách agent trả tên mới + tên gốc", next(a for a in c.get("/api/agents").json() if a["id"] == "lan")["default_name"] == "Lan")
p = ceo_orders._rule_plan("Ngọc viết bài dài quá, viết dưới 150 chữ thôi")
check(f"CEO hiểu tên mới ({p['actions'][:1]})", any(a.get("agent") == "lan" for a in p["actions"]))
p = ceo_orders._rule_plan("Lan viết bài dài quá, viết dưới 150 chữ thôi")
check("CEO vẫn hiểu tên cũ", any(a.get("agent") == "lan" for a in p["actions"]))
check("trùng tên người khác bị từ chối", c.put("/api/agents/ha", json={"name": "ngọc"}).status_code == 400)
check("tên rỗng / quá dài bị từ chối", c.put("/api/agents/ha", json={"name": ""}).status_code == 400
      and c.put("/api/agents/ha", json={"name": "x" * 21}).status_code == 400)

sid = c.post("/api/sales", json={"name": "Linh", "fb_name": "Linh Nguyễn"}).json()["id"]
check("đổi tên nhân viên sale", c.put(f"/api/agents/sale-{sid}", json={"name": "Thảo"}).status_code == 200
      and db.one("SELECT name FROM sales WHERE id=?", (sid,))["name"] == "Thảo")

def data_url(w, h, color=(200, 120, 80)):
    b = io.BytesIO(); Image.new("RGB", (w, h), color).save(b, "PNG"); return "data:image/png;base64," + base64.b64encode(b.getvalue()).decode()
r = c.put("/api/agents/lan", json={"face": data_url(800, 500)})
f = agents.faces_dir() / "lan.jpg"
check("ảnh mặt: cắt vuông 320", r.status_code == 200 and r.json()["face"].startswith("/faces/lan.jpg") and Image.open(f).size == (320, 320))
check("ảnh mặt có trong danh sách agent", next(a for a in c.get("/api/agents").json() if a["id"] == "lan")["face"].startswith("/faces/"))
check("ảnh mặt cho nhân viên sale", c.put(f"/api/agents/sale-{sid}", json={"face": data_url(300, 300)}).status_code == 200
      and next(a for a in c.get("/api/agents").json() if a["id"] == f"sale-{sid}")["face"])
check("ảnh hỏng / quá nhỏ bị từ chối", c.put("/api/agents/ha", json={"face": "data:image/png;base64,AAAA"}).status_code == 400
      and c.put("/api/agents/ha", json={"face": data_url(20, 20)}).status_code == 400)
check("không cho agent lạ", c.put("/api/agents/hacker", json={"name": "X"}).status_code == 400)

r = c.delete("/api/agents/lan/profile").json()
check("về mặc định: tên Lan, xóa ảnh", r["name"] == "Lan" and not r["face"] and not f.exists()
      and "Bạn tên là Lan" in agents.system_prompt("lan", db.get_settings()))
print(("XONG" if all(ok) else "CÓ LỖI") + f" {sum(ok)}/{len(ok)}")

"""Kiểm tra chọn ảnh ngẫu nhiên, xoay vòng, chống trùng theo nhóm/nick."""
import struct, sys, zlib
from collections import Counter
from pathlib import Path
import os; sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "backend"))
SP = Path(__import__("os").environ.get("MT_WORK") or Path(__file__).resolve().parent / "work")
import db
db.DB_PATH = SP / "img.db"
db.DB_PATH.unlink(missing_ok=True)
db.init()
import media_folder as M


def png(path, rgb):
    raw = b"".join(b"\x00" + bytes(rgb) * 8 for _ in range(8))
    ch = lambda t, d: struct.pack(">I", len(d)) + t + d + struct.pack(">I", zlib.crc32(t + d) & 0xffffffff)
    path.write_bytes(b"\x89PNG\r\n\x1a\n" + ch(b"IHDR", struct.pack(">IIBBBBB", 8, 8, 8, 2, 0, 0, 0)) + ch(b"IDAT", zlib.compress(raw)) + ch(b"IEND", b""))


folder = SP / "AnhSanPham" / "Tra gung mat ong"
import shutil; shutil.rmtree(SP / "AnhSanPham", ignore_errors=True)
(folder / "hop").mkdir(parents=True)
for i in range(9):
    png((folder / "hop" if i > 6 else folder) / f"gung{i}.png", (i * 20, 100, 50))
(folder / "ghi-chu.txt").write_text("không phải ảnh")
db.run("UPDATE products SET image_folder=? WHERE id=1", (str(folder),))
db.set_setting("images_min", "2"); db.set_setting("images_max", "3")
prod = db.one("SELECT * FROM products WHERE id=1")
print("thư mục:", {k: v for k, v in M.folder_info(prod).items() if k != "samples"})

# 3 bài cùng nhóm 1 bằng nick 1, rồi nhóm 2 bằng nick 1, rồi nhóm 1 bằng nick 2
used_g1 = []
for n, (gid, sid) in enumerate([(1, 1), (1, 1), (1, 1), (2, 1), (1, 2), (3, 2)]):
    post = {"id": 100 + n, "product_id": 1, "group_id": gid, "sale_id": sid}
    imgs, warn = M.pick_for_post(post, sid)
    M.record(imgs, "post", post, sid)
    names = [p.name for p in imgs]
    if gid == 1:
        used_g1 += names
    print(f"bài {n+1} nhóm {gid} nick {sid}: {names} {'| ' + warn if warn else ''}")
c = Counter(used_g1)
print("ảnh lặp trong nhóm 1:", [k for k, v in c.items() if v > 1] or "không có", f"({len(used_g1)} lượt / 9 ảnh)")
# up bài: không lặp ảnh trên cùng bài
post = {"id": 100, "product_id": 1}
b1 = M.pick(post); M.record([b1], "bump", post, 1, 1); b2 = M.pick(post)
print("up bài lần 1, 2:", b1.name, b2.name, "| trùng" if b1 == b2 else "| khác nhau")
# chặn đọc file ngoài thư mục
print("chặn ../:", M.safe_file("../../img.db", prod), "| ảnh hợp lệ:", M.safe_file("gung1.png", prod).name)
# sản phẩm chưa có thư mục riêng -> dùng thư mục chung, thư mục con trùng tên
db.set_setting("bump_folder", str(SP / "AnhSanPham"))
p2 = dict(db.one("SELECT * FROM products WHERE id=1")); p2["image_folder"] = ""
print("dự phòng thư mục chung:", M.product_folder(p2)[1], M.product_folder(p2)[0].name)

"""Thư mục ảnh sản phẩm trên máy sếp, dùng để bình luận "up bài".

Cách xếp ảnh (khuyên dùng):
    D:\\AnhSanPham\\
        Tra gung mat ong\\       <- thư mục con đặt theo tên sản phẩm (có dấu hay không dấu đều được)
        Bot ngu coc\\
        anh-chung-1.jpg         <- ảnh để thẳng trong thư mục gốc: dùng cho mọi sản phẩm
Sale sẽ ưu tiên ảnh trong thư mục con khớp với sản phẩm của bài, và không dùng lại ảnh
đã bình luận ở chính bài đó cho tới khi dùng hết ảnh.
"""
import random
import re
import unicodedata
from pathlib import Path

import db

IMG_EXT = {".jpg", ".jpeg", ".png", ".webp"}


def slug(s: str) -> str:
    s = unicodedata.normalize("NFD", (s or "").lower().replace("đ", "d"))
    s = "".join(c for c in s if unicodedata.category(c) != "Mn")
    return re.sub(r"[^a-z0-9]+", "", s)


def root() -> Path | None:
    p = (db.get_settings().get("bump_folder") or "").strip().strip('"')
    if not p:
        return None
    r = Path(p).expanduser()
    return r if r.is_dir() else None


def _images(d: Path, recursive=False) -> list[Path]:
    it = d.rglob("*") if recursive else d.iterdir()
    return sorted(f for f in it if f.is_file() and f.suffix.lower() in IMG_EXT)


def images_for(product: dict | None) -> list[Path]:
    r = root()
    if not r:
        return []
    if product:
        ps = slug(product.get("name", ""))
        for sub in sorted(x for x in r.iterdir() if x.is_dir()):
            ss = slug(sub.name)
            if ss and (ss in ps or ps in ss or sub.name.split()[0] == str(product.get("id"))):
                imgs = _images(sub, recursive=True)
                if imgs:
                    return imgs
    imgs = _images(r)
    return imgs or _images(r, recursive=True)


def pick(post: dict) -> Path | None:
    product = db.one("SELECT * FROM products WHERE id=?", (post.get("product_id"),)) if post.get("product_id") else None
    imgs = images_for(product)
    if not imgs:
        return None
    used = {r["image"] for r in db.q("SELECT image FROM bumps WHERE post_id=? AND status='done'", (post["id"],))}
    fresh = [i for i in imgs if str(i) not in used]
    return random.choice(fresh or imgs)


def info() -> dict:
    raw = (db.get_settings().get("bump_folder") or "").strip()
    r = root()
    if not r:
        return {"path": raw, "exists": False, "count": 0, "products": [], "samples": []}
    allimgs = _images(r, recursive=True)
    prods = []
    for p in db.q("SELECT id, name FROM products ORDER BY id"):
        own = [i for i in images_for(p) if i.parent != r]
        prods.append({"id": p["id"], "name": p["name"], "count": len(own)})
    return {"path": str(r), "exists": True, "count": len(allimgs), "root_count": len(_images(r)), "products": prods,
            "samples": [str(i.relative_to(r)) for i in allimgs[:12]]}


def safe_file(rel: str) -> Path | None:
    """Chỉ trả ảnh nằm trong thư mục đã cài (chặn đọc file khác trên máy)."""
    r = root()
    if not r:
        return None
    f = (r / rel).resolve()
    try:
        f.relative_to(r.resolve())
    except ValueError:
        return None
    return f if f.is_file() and f.suffix.lower() in IMG_EXT else None

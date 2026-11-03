"""Ảnh sản phẩm trên máy sếp: chọn ngẫu nhiên, xoay vòng, tránh đăng trùng.

Mỗi sản phẩm có một THƯ MỤC ẢNH riêng (trang Sản phẩm), ví dụ:
    D:\\AnhSanPham\\Tra gung mat ong\\      (bao nhiêu ảnh cũng được, kể cả thư mục con)
Nếu sản phẩm chưa có thư mục riêng, dùng thư mục chung ở Cài đặt → Up bài:
    thư mục con có tên giống tên sản phẩm (có dấu hay không dấu đều được), hoặc ảnh để thẳng trong thư mục chung.

Chống trùng lặp khi đăng bài (theo thứ tự ưu tiên):
1. Không dùng lại ảnh đã đăng ở CÙNG NHÓM trong N ngày (mặc định 14).
2. Không dùng lại ảnh mà CÙNG NICK đã đăng trong N ngày.
3. Ưu tiên ảnh chưa đăng lần nào, rồi tới ảnh lâu chưa dùng nhất; trong cùng mức thì chọn ngẫu nhiên.
4. Mỗi bài lấy ngẫu nhiên từ "tối thiểu" đến "tối đa" ảnh, thứ tự ảnh cũng ngẫu nhiên.
Khi thư mục ít ảnh tới mức không đủ ảnh mới, hệ thống nới dần điều kiện (bỏ điều kiện 2, rồi 1) thay vì đăng không ảnh,
và nhắc sếp bổ sung ảnh.
"""
import json
import random
import re
import unicodedata
from datetime import datetime, timedelta
from pathlib import Path

import db

IMG_EXT = {".jpg", ".jpeg", ".png", ".webp"}


def slug(s: str) -> str:
    s = unicodedata.normalize("NFD", (s or "").lower().replace("đ", "d"))
    s = "".join(c for c in s if unicodedata.category(c) != "Mn")
    return re.sub(r"[^a-z0-9]+", "", s)


def _dir(p: str | None) -> Path | None:
    p = (p or "").strip().strip('"')
    if not p:
        return None
    d = Path(p).expanduser()
    return d if d.is_dir() else None


def root() -> Path | None:
    return _dir(db.get_settings().get("bump_folder"))


def _images(d: Path, recursive=False) -> list[Path]:
    it = d.rglob("*") if recursive else d.iterdir()
    try:
        return sorted(f for f in it if f.is_file() and f.suffix.lower() in IMG_EXT and not f.name.startswith("."))
    except OSError:
        return []


def product_folder(product: dict | None) -> tuple[Path | None, str]:
    """Thư mục ảnh của sản phẩm và nguồn: 'product' | 'shared-sub' | 'shared' | ''."""
    if product and _dir(product.get("image_folder")):
        return _dir(product.get("image_folder")), "product"
    r = root()
    if not r:
        return None, ""
    if product:
        ps = slug(product.get("name", ""))
        for sub in sorted(x for x in r.iterdir() if x.is_dir()):
            ss = slug(sub.name)
            if ss and (ss in ps or ps in ss):
                return sub, "shared-sub"
    return r, "shared"


def images_for(product: dict | None) -> list[Path]:
    d, src = product_folder(product)
    if not d:
        return []
    if src == "shared":
        return _images(d) or _images(d, recursive=True)
    return _images(d, recursive=True)


def _product(product_id) -> dict | None:
    return db.one("SELECT * FROM products WHERE id=?", (product_id,)) if product_id else None


def _usage(paths: list[Path]) -> dict:
    """Lịch sử dùng của từng ảnh: số lần, lần gần nhất, nhóm và nick đã dùng gần đây."""
    if not paths:
        return {}
    days = int(db.get_settings().get("image_reuse_days") or 14)
    since = (datetime.now() - timedelta(days=days)).strftime("%Y-%m-%d %H:%M:%S")
    out = {str(p): {"n": 0, "last": "", "groups": set(), "sales": set()} for p in paths}
    rows = db.q("SELECT path, group_id, sale_id, used_at FROM image_usage WHERE path IN (%s)" % ",".join("?" * len(out)),
                tuple(out))
    for r in rows:
        u = out[r["path"]]
        u["n"] += 1
        u["last"] = max(u["last"], r["used_at"] or "")
        if (r["used_at"] or "") >= since:
            if r["group_id"]:
                u["groups"].add(r["group_id"])
            if r["sale_id"]:
                u["sales"].add(r["sale_id"])
    return out


def _rank(paths: list[Path], usage: dict) -> list[Path]:
    """Chưa dùng trước, rồi lâu chưa dùng nhất; trộn ngẫu nhiên trong cùng mức."""
    keyed = [(usage[str(p)]["n"] > 0, usage[str(p)]["last"], random.random(), p) for p in paths]
    return [k[-1] for k in sorted(keyed)]


def pick_for_post(post: dict, sale_id: int | None = None) -> tuple[list[Path], str | None]:
    """Chọn ảnh cho một bài đăng. Trả về (danh sách ảnh, cảnh báo nếu phải dùng lại ảnh)."""
    s = db.get_settings()
    if s.get("attach_images") != "1":
        return [], None
    product = _product(post.get("product_id"))
    pool = images_for(product)
    if not pool and product:  # dự phòng: ảnh tải lên trong phần mềm
        pool = [db.DATA_DIR / rel for rel in json.loads(product.get("images") or "[]") if (db.DATA_DIR / rel).exists()]
    if not pool:
        return [], None
    lo = max(1, int(s.get("images_min") or 2))
    hi = max(lo, min(10, int(s.get("images_max") or 4)))  # Facebook nhận tối đa nhiều ảnh, giữ 10 cho gọn
    want = min(random.randint(lo, hi), len(pool))
    usage = _usage(pool)
    gid, sid = post.get("group_id"), sale_id or post.get("sale_id")
    tiers = [
        [p for p in pool if gid not in usage[str(p)]["groups"] and sid not in usage[str(p)]["sales"]],
        [p for p in pool if gid not in usage[str(p)]["groups"]],
        pool,
    ]
    chosen, warn = [], None
    for i, tier in enumerate(tiers):
        for p in _rank([p for p in tier if p not in chosen], usage):
            if len(chosen) >= want:
                break
            chosen.append(p)
        if len(chosen) >= want:
            if i == 2:
                warn = "Thư mục ảnh của sản phẩm này đã dùng hết ảnh mới cho nhóm này, phải dùng lại ảnh cũ. Nên bổ sung ảnh."
            elif i == 1:
                warn = "Một số ảnh nick này đã đăng gần đây (ở nhóm khác). Nên bổ sung ảnh cho sản phẩm."
            break
    random.shuffle(chosen)
    return chosen, warn


def pick(post: dict) -> Path | None:
    """Chọn 1 ảnh để bình luận up bài: không lặp ảnh trên cùng bài, ưu tiên ảnh ít dùng nhất."""
    pool = images_for(_product(post.get("product_id")))
    if not pool:
        return None
    used_here = {r["path"] for r in db.q("SELECT path FROM image_usage WHERE post_id=?", (post["id"],))}
    used_here |= {r["image"] for r in db.q("SELECT image FROM bumps WHERE post_id=? AND status='done'", (post["id"],))}
    fresh = [p for p in pool if str(p) not in used_here] or pool
    return _rank(fresh, _usage(fresh))[0]


def record(paths: list, kind: str, post: dict | None = None, sale_id: int | None = None, bump_id: int | None = None):
    for p in paths:
        db.run("""INSERT INTO image_usage(path, product_id, post_id, bump_id, sale_id, group_id, kind, used_at)
                  VALUES (?,?,?,?,?,?,?,?)""",
               (str(p), (post or {}).get("product_id"), (post or {}).get("id"), bump_id,
                sale_id or (post or {}).get("sale_id"), (post or {}).get("group_id"), kind, db.now()))


def folder_info(product: dict) -> dict:
    d, src = product_folder(product)
    raw = (product.get("image_folder") or "").strip()
    if not d:
        return {"path": raw, "exists": False, "source": src, "count": 0, "fresh": 0, "samples": [],
                "error": "Không tìm thấy thư mục này trên máy chạy phần mềm" if raw else None}
    imgs = images_for(product)
    usage = _usage(imgs)
    return {"path": str(d), "exists": True, "source": src, "count": len(imgs),
            "fresh": sum(1 for p in imgs if usage[str(p)]["n"] == 0),
            "posts_left": len([p for p in imgs if usage[str(p)]["n"] == 0]) // max(1, int(db.get_settings().get("images_min") or 2)),
            "error": None if src == "product" or not raw else "Không tìm thấy thư mục riêng, đang dùng thư mục chung",
            "samples": [str(p.relative_to(d)) for p in imgs[:10]]}


def info() -> dict:
    """Thư mục chung (Cài đặt → Up bài)."""
    raw = (db.get_settings().get("bump_folder") or "").strip()
    r = root()
    if not r:
        return {"path": raw, "exists": False, "count": 0, "products": [], "samples": []}
    allimgs = _images(r, recursive=True)
    prods = []
    for p in db.q("SELECT * FROM products ORDER BY id"):
        d, src = product_folder(p)
        prods.append({"id": p["id"], "name": p["name"], "count": len(images_for(p)) if src in ("product", "shared-sub") else 0})
    return {"path": str(r), "exists": True, "count": len(allimgs), "root_count": len(_images(r)), "products": prods,
            "samples": [str(i.relative_to(r)) for i in allimgs[:12]]}


def safe_file(rel: str, product: dict | None = None) -> Path | None:
    """Chỉ trả ảnh nằm trong thư mục đã cài (chặn đọc file khác trên máy)."""
    base = product_folder(product)[0] if product else root()
    if not base:
        return None
    f = (base / rel).resolve()
    try:
        f.relative_to(base.resolve())
    except ValueError:
        return None
    return f if f.is_file() and f.suffix.lower() in IMG_EXT else None

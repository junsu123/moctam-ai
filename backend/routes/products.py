# ------------------------------------------------------------------ sản phẩm
class Product(BaseModel):
    name: str
    category: str = ""
    description: str = ""
    wholesale_price: str = ""
    retail_price: str = ""
    moq: str = ""
    selling_points: str = ""
    uses: str = ""  # công dụng: Nhi dựa vào đây để chọn sản phẩm cho bài, viết và tạo ảnh
    image_folder: str = ""
    hot: bool = False
    hot_note: str = ""
    is_general: bool = False


class ProductPatch(BaseModel):
    name: str | None = None
    category: str | None = None
    description: str | None = None
    wholesale_price: str | None = None
    retail_price: str | None = None
    moq: str | None = None
    selling_points: str | None = None
    uses: str | None = None
    image_folder: str | None = None
    hot: bool | None = None
    hot_note: str | None = None
    is_general: bool | None = None


def _set_general(pid: int, on: bool):
    """Chỉ 1 mục ảnh tổng hợp: tích mục này thì bỏ tích mục khác."""
    if on:
        db.run("UPDATE products SET is_general=CASE WHEN id=? THEN 1 ELSE 0 END", (pid,))
    else:
        db.run("UPDATE products SET is_general=0 WHERE id=?", (pid,))
    media_folder._count_cache.clear()
    p = db.one("SELECT name FROM products WHERE id=?", (pid,))
    db.log("tuan", "Ảnh đăng bài", f"Từ giờ mọi bài đăng chỉ lấy ảnh ngẫu nhiên trong “{p['name']}” (ảnh tổng hợp nhà máy)" if on
           else f"Bỏ ảnh tổng hợp “{p['name']}”: bài đăng lấy ảnh theo đúng sản phẩm của bài")


def _set_hot(pid: int, hot: bool, by: str = "boss"):
    import products as P
    P.set_hot(pid, hot, by)


@app.get("/api/products")
def products():
    return [{**p, "folder": media_folder.folder_info(p)}
            for p in db.q("SELECT * FROM products ORDER BY COALESCE(is_general,0) DESC, hot DESC, id")]


@app.post("/api/products")
def add_product(p: Product):
    if not p.name.strip():
        raise HTTPException(400, "Nhập tên sản phẩm")
    if db.one("SELECT id FROM products WHERE lower(name)=lower(?)", (p.name.strip(),)):
        raise HTTPException(400, "Đã có sản phẩm cùng tên. Sửa sản phẩm đó thay vì thêm mới")
    pid = db.run("""INSERT INTO products(name, category, description, wholesale_price, retail_price, moq,
                    selling_points, uses, image_folder, hot_note, created_at) VALUES (?,?,?,'','',?,?,?,?,?,?)""",
                 (p.name.strip(), p.category, p.description, p.moq, p.selling_points, p.uses.strip(),
                  p.image_folder.strip().strip('"'), p.hot_note.strip(), db.now()))
    db.log("minh", "Thêm sản phẩm", f"{p.name.strip()}: Lan có thể viết bài, Hà tư vấn sản phẩm này từ giờ")
    if p.hot:
        _set_hot(pid, True)
    if p.is_general:
        _set_general(pid, True)
    prod = db.one("SELECT * FROM products WHERE id=?", (pid,))
    return {**prod, "folder": media_folder.folder_info(prod)}


@app.patch("/api/products/{pid}")
def patch_product(pid: int, p: ProductPatch):
    if not db.one("SELECT id FROM products WHERE id=?", (pid,)):
        raise HTTPException(404, "Không tìm thấy sản phẩm")
    data = p.model_dump()
    hot = data.pop("hot")
    gen = data.pop("is_general")
    data.pop("wholesale_price", None), data.pop("retail_price", None)  # sếp chốt: không lưu giá, giá liên hệ Zalo
    fields = {k: (v.strip().strip('"') if k == "image_folder" else v.strip() if isinstance(v, str) else v)
              for k, v in data.items() if v is not None}
    if "name" in fields and not fields["name"]:
        raise HTTPException(400, "Tên sản phẩm không được để trống")
    if "name" in fields and db.one("SELECT id FROM products WHERE lower(name)=lower(?) AND id!=?", (fields["name"], pid)):
        raise HTTPException(400, "Đã có sản phẩm khác cùng tên")
    if hot is not None:
        _set_hot(pid, hot)
    if gen is not None:
        _set_general(pid, gen)
    if fields:
        fields["is_sample"] = 0  # sếp đã sửa -> thành dữ liệu thật
        db.run(f"UPDATE products SET {', '.join(k + '=?' for k in fields)} WHERE id=?", (*fields.values(), pid))
        media_folder._count_cache.clear()  # đổi thư mục ảnh: số ảnh sẵn để đăng tính lại ngay
    prod = db.one("SELECT * FROM products WHERE id=?", (pid,))
    if not prod:
        raise HTTPException(404)
    return {**prod, "folder": media_folder.folder_info(prod)}


@app.get("/api/products/{pid}/folder")
def product_folder(pid: int):
    prod = db.one("SELECT * FROM products WHERE id=?", (pid,))
    if not prod:
        raise HTTPException(404)
    return media_folder.folder_info(prod)


@app.get("/api/products/{pid}/folder-image")
def product_folder_image(pid: int, name: str):
    f = media_folder.safe_file(name, db.one("SELECT * FROM products WHERE id=?", (pid,)))
    if not f:
        raise HTTPException(404)
    return FileResponse(f)


@app.get("/api/image")
def used_image(path: str):
    """Ảnh đã đăng (để xem lại trên thẻ bài): chỉ trả file đã ghi trong lịch sử đăng ảnh."""
    if not db.one("""SELECT id FROM image_usage WHERE path=? UNION SELECT id FROM posts WHERE images_used LIKE ?
                     UNION SELECT id FROM reply_tasks WHERE image=?""",
                  (path, f'%{json.dumps(path, ensure_ascii=False)[1:-1]}%', path)):
        raise HTTPException(404)
    f = Path(path)
    if not f.is_file() or f.suffix.lower() not in media_folder.IMG_EXT:
        raise HTTPException(404)
    return FileResponse(f)


@app.delete("/api/products/{pid}")
def del_product(pid: int):
    p = db.one("SELECT name FROM products WHERE id=?", (pid,))
    if not p:
        raise HTTPException(404, "Không tìm thấy sản phẩm")
    drafts = db.one("SELECT COUNT(*) n FROM posts WHERE product_id=? AND status IN ('draft','approved')", (pid,))["n"]
    db.run("UPDATE posts SET status='rejected' WHERE product_id=? AND status IN ('draft','approved')", (pid,))
    db.run("DELETE FROM products WHERE id=?", (pid,))
    media_folder._count_cache.clear()
    db.log("minh", "Xóa sản phẩm", f"{p['name']}" + (f", bỏ {drafts} bài nháp/chờ đăng của sản phẩm này" if drafts else ""))
    return {"ok": True, "drafts_removed": drafts}


# ------------------------------------------------------------------ ảnh 3D sản phẩm (Nhi ghép vào ảnh bài Trang)
@app.post("/api/products/{pid}/images3d")
def add_image3d(pid: int, data: dict):
    import base64 as b64
    import os as _os
    import image_gen
    try:
        raw = b64.b64decode((data.get("data") or "").split(",", 1)[-1])
        return {"images3d": image_gen.add_3d(pid, raw, _os.path.splitext(data.get("filename") or "a.png")[1] or ".png")}
    except (ValueError, b64.binascii.Error) as e:
        raise HTTPException(400, str(e) or "Ảnh hỏng")


@app.delete("/api/products/{pid}/images3d")
def del_image3d(pid: int, path: str):
    import image_gen
    return {"images3d": image_gen.del_3d(pid, path)}

"""Ghép giao diện từ nhiều file nhỏ trong frontend/ (khuôn app.html + css/ views/ js/).

app.html có các dòng `@@include <đường dẫn>`: mỗi dòng được thay bằng nguyên nội dung file đó (ghép chữ, không xử lý gì thêm),
nên toàn bộ JS vẫn chạy trong một thẻ <script> như bản một file trước đây. Sửa một trang chỉ cần mở đúng file nhỏ của trang đó.
"""
import re
from pathlib import Path

FRONTEND = Path(__file__).resolve().parent.parent / "frontend"
_INC = re.compile(r"^[ \t]*@@include[ \t]+(\S+)[ \t]*\r?\n", re.M)
_cache = {"key": None, "html": ""}


def files(root: Path = FRONTEND) -> list[Path]:
    """Mọi file làm nên giao diện (để biết khi nào có bản mới)."""
    return [root / "app.html"] + sorted(p for d in ("css", "views", "js") for p in (root / d).rglob("*") if p.is_file())


def build(root: Path = FRONTEND) -> str:
    def inc(m):
        f = (root / m.group(1)).resolve()
        if root.resolve() not in f.parents:
            raise ValueError(f"@@include ra ngoài thư mục frontend: {m.group(1)}")
        if not f.is_file():
            raise FileNotFoundError(f"Thiếu file giao diện frontend/{m.group(1)}")
        return f.read_text(encoding="utf-8")
    return _INC.sub(inc, (root / "app.html").read_text(encoding="utf-8"))


def page() -> str:
    """Giao diện đã ghép (ghép lại khi có file đổi)."""
    key = tuple((str(f), f.stat().st_mtime_ns, f.stat().st_size) for f in files() if f.exists())
    if key != _cache["key"]:
        _cache.update(key=key, html=build())
    return _cache["html"]


if __name__ == "__main__":  # python backend/ui.py out.html : ghi bản một file (xem trước, đăng artifact)
    import sys
    out = Path(sys.argv[1] if len(sys.argv) > 1 else "index.html")
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text("<!DOCTYPE html>\n" + build(), encoding="utf-8")
    print(out)

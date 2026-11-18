#!/usr/bin/env bash
# Kiểm tra cú pháp nhanh (vài giây): Python theo cú pháp 3.10 cho backend/ và dev/, ghép giao diện rồi node --check phần JS.
# Ghép xong có luôn bản một file dev/work/preview/index.html (dùng để xem trước, chụp ảnh, đăng artifact).
set -e
cd "$(dirname "$0")/.."
python3 - <<'PY'
import ast, sys, pathlib
bad = 0
for f in sorted(pathlib.Path("backend").rglob("*.py")) + sorted(pathlib.Path("dev").glob("*.py")):
    try:
        ast.parse(f.read_text(encoding="utf-8"), str(f), feature_version=(3, 10))
    except SyntaxError as e:
        print("LỖI CÚ PHÁP:", f, e); bad += 1
sys.exit(1 if bad else 0)
PY
python3 backend/ui.py dev/work/preview/index.html > /dev/null
python3 -c "import re;s=open('dev/work/preview/index.html',encoding='utf-8').read();open('dev/work/preview/app.js','w',encoding='utf-8').write('\n'.join(re.findall(r'<script>(.*?)</script>',s,re.S)))"
node --check dev/work/preview/app.js
echo "Cú pháp OK (Python 3.10 + JS giao diện)"

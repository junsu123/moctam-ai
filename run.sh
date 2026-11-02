#!/usr/bin/env bash
cd "$(dirname "$0")"
[ -d .venv ] || python3 -m venv .venv
source .venv/bin/activate
pip install -q -r requirements.txt
[ -f .venv/.pw_ok ] || { python -m playwright install chromium && touch .venv/.pw_ok; }
cd backend
echo "Mở trình duyệt: http://localhost:8000"
python main.py

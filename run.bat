@echo off
chcp 65001 >nul
cd /d %~dp0
if not exist .venv (
  echo Dang tao moi truong Python...
  python -m venv .venv
)
call .venv\Scripts\activate
pip install -q -r requirements.txt
if not exist .venv\.pw_ok (
  echo Cai trinh duyet du phong cho nhan vien sale, chi lan dau...
  python -m playwright install chromium && echo ok> .venv\.pw_ok
)
cd backend
echo Mo trinh duyet: http://localhost:8000
start http://localhost:8000
python main.py

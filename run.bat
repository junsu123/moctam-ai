@echo off
chcp 65001 >nul
cd /d %~dp0
title Moc Tam AI - Phong kinh doanh
where python >nul 2>nul || (
  echo Chua cai Python. Tai Python 3.10 tro len o https://www.python.org/downloads/
  echo Khi cai, nho tick "Add python.exe to PATH". Cai xong chay lai run.bat.
  pause
  exit /b 1
)
if not exist .venv (
  echo Dang tao moi truong Python...
  python -m venv .venv || (
    echo Khong tao duoc moi truong Python. Chup man hinh nay gui cho nguoi ho tro.
    pause
    exit /b 1
  )
)
call .venv\Scripts\activate
pip install -q -r requirements.txt
if not exist .venv\.pw_ok (
  echo Cai trinh duyet du phong cho nhan vien sale, chi lan dau...
  python -m playwright install chromium && echo ok> .venv\.pw_ok
)
cd backend
if /I "%1"=="restart" (
  echo Dang khoi dong lai phan mem voi ban moi...
) else (
  echo Mo trinh duyet: http://localhost:8000
  start http://localhost:8000
)
python main.py
if exist "%~dp0data\replaced.flag" (
  del "%~dp0data\replaced.flag" >nul 2>nul
  exit
)
if errorlevel 1 (
  echo.
  echo ============================================================
  echo  Phan mem da dung vi loi o tren. Chup man hinh cua so nay
  echo  gui cho nguoi ho tro, roi bam phim bat ky de dong.
  echo ============================================================
  pause
)

@echo off
chcp 65001 > nul
cd /d "%~dp0"
if not exist .venv (
  echo [PC Link] 최초 설치 중입니다. 잠시 기다려 주세요...
  py -3 -m venv .venv || python -m venv .venv
  .venv\Scripts\python -m pip install --upgrade pip
  .venv\Scripts\python -m pip install -r requirements.txt -r requirements-optional.txt
)
.venv\Scripts\python -m pclink %*
pause

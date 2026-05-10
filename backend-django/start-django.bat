@echo off
setlocal

cd /d "%~dp0"

if not exist .venv\Scripts\python.exe (
  echo Creating venv for Django backend...
  py -3 -m venv .venv
)

.venv\Scripts\python.exe -m pip install -U pip
.venv\Scripts\pip.exe install -r requirements.txt

REM Ensure DB is ready (SQLite by default)
.venv\Scripts\python.exe manage.py migrate

echo Starting ASGI server (uvicorn) on http://localhost:8000 ...
.venv\Scripts\uvicorn.exe lineguard.asgi:application --host 0.0.0.0 --port 8000


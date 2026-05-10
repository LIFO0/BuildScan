@echo off
setlocal

cd /d "%~dp0"

if not exist .venv\Scripts\python.exe (
  echo Creating venv for YOLO service (current Python)...
  py -3 -m venv .venv
)

.venv\Scripts\python.exe -m pip install -U pip
.venv\Scripts\pip.exe install -r requirements.txt

REM Model path: repo_root\models\best.pt
for %%I in ("%~dp0..") do set "REPO_ROOT=%%~fI"
set "MODEL_PATH=%REPO_ROOT%\models\best.pt"
set "PORT=8001"

echo Starting YOLOv8 service on http://localhost:%PORT% ...
.venv\Scripts\python.exe -m app.main


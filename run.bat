@echo off
setlocal EnableExtensions EnableDelayedExpansion
chcp 65001 >nul

rem ============================================================================
rem LineGuard - unified launcher (Windows)
rem ----------------------------------------------------------------------------
rem Usage:
rem   run.bat                 -> start all (no Docker)
rem   run.bat start           -> same as above
rem   run.bat stop            -> stop processes by ports (best-effort)
rem   run.bat docker          -> start via docker compose (if Docker installed)
rem   run.bat frontend|django|yolo -> start only one service (no Docker)
rem ============================================================================

set "ROOT=%~dp0"
set "CMD=%~1"
if not defined CMD set "CMD=start"

if /i "%CMD%"=="stop" (
  call :stop_ports
  exit /b %errorlevel%
)

if /i "%CMD%"=="docker" (
  call :check_cmd docker "Docker"
  if errorlevel 1 exit /b 1
  call :check_cmd docker-compose "Docker Compose (docker-compose.exe)" >nul 2>nul
  pushd "%ROOT%" >nul
  docker compose up --build
  popd >nul
  exit /b %errorlevel%
)

call :check_cmd node "Node.js"
if errorlevel 1 goto :fatal
call :check_cmd npm "npm"
if errorlevel 1 goto :fatal
call :check_cmd py "Python launcher (py)"
if errorlevel 1 goto :fatal

call :pick_python
if errorlevel 1 goto :fatal

rem Install deps (only when missing)
call :frontend_deps
if errorlevel 1 goto :fatal
call :django_deps
if errorlevel 1 goto :fatal
call :yolo_deps
if errorlevel 1 goto :fatal

if /i "%CMD%"=="frontend" (
  set "FE=%ROOT%frontend-service"
  start "LineGuard Frontend" /D "%FE%" cmd /k npm run dev -- --host 127.0.0.1 --port 5173
  exit /b 0
)
if /i "%CMD%"=="django" (
  set "BE=%ROOT%backend-django"
  start "LineGuard Django API" /D "%BE%" cmd /k .venv\Scripts\uvicorn.exe lineguard.asgi:application --host 127.0.0.1 --port 8000
  exit /b 0
)
if /i "%CMD%"=="yolo" (
  set "YO=%ROOT%yolov8-model-service"
  set "MODEL=%ROOT%models\best.pt"
  start "LineGuard YOLOv8 Service" /D "%YO%" cmd /k set "MODEL_PATH=%MODEL%" ^& set "PORT=8001" ^& .venv\Scripts\python.exe -m app.main
  exit /b 0
)

rem Default: start everything
set "FE=%ROOT%frontend-service"
set "BE=%ROOT%backend-django"
set "YO=%ROOT%yolov8-model-service"
set "MODEL=%ROOT%models\best.pt"

start "LineGuard Frontend" /D "%FE%" cmd /k npm run dev -- --host 127.0.0.1 --port 5173
start "LineGuard Django API" /D "%BE%" cmd /k .venv\Scripts\uvicorn.exe lineguard.asgi:application --host 127.0.0.1 --port 8000
start "LineGuard YOLOv8 Service" /D "%YO%" cmd /k set "MODEL_PATH=%MODEL%" ^& set "PORT=8001" ^& .venv\Scripts\python.exe -m app.main

echo.
call :ok   "Started."
call :info "Open in browser (not plain http://localhost - use port 5173):"
echo   UI   : http://127.0.0.1:5173
echo   API  : http://127.0.0.1:8000/api/health
echo   YOLO : http://127.0.0.1:8001/health
echo.
call :warn "Keep the three titled cmd windows open (Frontend / Django / YOLO). Closing them stops the app - browser will show ERR_CONNECTION_REFUSED."
echo.
exit /b 0

rem ============================================================================
rem FUNCTIONS
rem ============================================================================

:check_cmd
where %~1 >nul 2>nul
if errorlevel 1 (
  call :err "Missing tool: %~2 (%~1). Install it and ensure it's in PATH."
  exit /b 1
)
exit /b 0

:pick_python
set "PY_LAUNCH="
py -3.14 -c "import sys; assert sys.version_info[:2]==(3,14)" >nul 2>nul
if errorlevel 1 (
  call :err "Python 3.14 is required. Install Python 3.14 and ensure 'py -3.14' works."
  exit /b 1
)
set "PY_LAUNCH=py -3.14"
exit /b 0

:frontend_deps
set "FE=%ROOT%frontend-service"
if not exist "%FE%\package.json" (
  call :err "frontend-service\package.json not found."
  exit /b 1
)
if exist "%FE%\node_modules" exit /b 0
call :info "Installing frontend deps (npm install)..."
pushd "%FE%" >nul
npm install
set "rc=%errorlevel%"
popd >nul
exit /b %rc%

:django_deps
set "BE=%ROOT%backend-django"
if not exist "%BE%\manage.py" (
  call :err "backend-django\manage.py not found."
  exit /b 1
)
if not exist "%BE%\.venv\Scripts\python.exe" (
  call :info "Creating Django venv..."
  pushd "%BE%" >nul
  %PY_LAUNCH% -m venv .venv
  set "rc=%errorlevel%"
  popd >nul
  if not "%rc%"=="0" exit /b %rc%
)
if exist "%BE%\.venv\.deps_ok" exit /b 0
call :info "Installing Django deps..."
pushd "%BE%" >nul
.\.venv\Scripts\python.exe -m pip install -U pip >nul
.\.venv\Scripts\pip.exe install -r requirements.txt
set "rc=%errorlevel%"
if "%rc%"=="0" (
  .\.venv\Scripts\python.exe manage.py migrate >nul
  set "rc=%errorlevel%"
)
if "%rc%"=="0" echo ok> ".venv\.deps_ok"
popd >nul
exit /b %rc%

:yolo_deps
set "YO=%ROOT%yolov8-model-service"
if not exist "%YO%\requirements.txt" (
  call :err "yolov8-model-service\requirements.txt not found."
  exit /b 1
)
if not exist "%YO%\.venv\Scripts\python.exe" (
  call :info "Creating YOLO venv..."
  pushd "%YO%" >nul
  %PY_LAUNCH% -m venv .venv
  set "rc=%errorlevel%"
  popd >nul
  if not "%rc%"=="0" exit /b %rc%
)
if exist "%YO%\.venv\.deps_ok" exit /b 0

call :info "Installing YOLO deps (torch is large)..."
pushd "%YO%" >nul
.\.venv\Scripts\python.exe -m pip install -U pip wheel >nul

rem requirements.txt may pin a torch build that is unavailable on your Python.
rem First try the repo requirements; if it fails, fall back to a compatible CPU install.
.\.venv\Scripts\pip.exe install -r requirements.txt
set "rc=%errorlevel%"
if not "%rc%"=="0" (
  call :warn "Pinned torch build not found; installing compatible CPU torch..."
  .\.venv\Scripts\pip.exe install "setuptools<82"
  .\.venv\Scripts\pip.exe install fastapi uvicorn[standard] python-multipart pydantic pydantic-settings pillow numpy ultralytics requests rawpy imageio imageio-ffmpeg pyyaml torch torchvision
  if errorlevel 1 (
    set "rc=1"
  ) else (
    set "rc=0"
  )
)

if "%rc%"=="0" echo ok> ".venv\.deps_ok"
popd >nul
exit /b %rc%

:start_frontend
set "FE=%ROOT%frontend-service"
start "LineGuard Frontend" /D "%FE%" cmd /k npm run dev -- --host 127.0.0.1 --port 5173
exit /b 0

:start_django
set "BE=%ROOT%backend-django"
start "LineGuard Django API" /D "%BE%" cmd /k .venv\Scripts\uvicorn.exe lineguard.asgi:application --host 127.0.0.1 --port 8000
exit /b 0

:start_yolo
set "YO=%ROOT%yolov8-model-service"
set "MODEL=%ROOT%models\best.pt"
start "LineGuard YOLOv8 Service" /D "%YO%" cmd /k set "MODEL_PATH=%MODEL%" ^& set "PORT=8001" ^& .venv\Scripts\python.exe -m app.main
exit /b 0

:stop_ports
echo Stopping LineGuard processes (by ports, best-effort)...
powershell -NoProfile -Command ^
  "$ports = @(5173,8000,8001); foreach($p in $ports){ $conns = Get-NetTCPConnection -State Listen -LocalPort $p -ErrorAction SilentlyContinue; foreach($c in $conns){ try { Stop-Process -Id $c.OwningProcess -Force -ErrorAction SilentlyContinue } catch {} } }"
exit /b 0

:ok
set "LG_MSG=%~1"
powershell -NoProfile -Command "Write-Host '[OK]' -ForegroundColor Green -NoNewline; Write-Host (' ' + $env:LG_MSG)"
exit /b 0

:warn
set "LG_MSG=%~1"
powershell -NoProfile -Command "Write-Host '[WARN]' -ForegroundColor Yellow -NoNewline; Write-Host (' ' + $env:LG_MSG)"
exit /b 0

:err
set "LG_MSG=%~1"
powershell -NoProfile -Command "Write-Host '[ERROR]' -ForegroundColor Red -NoNewline; Write-Host (' ' + $env:LG_MSG)"
exit /b 0

:info
set "LG_MSG=%~1"
powershell -NoProfile -Command "Write-Host '[INFO]' -ForegroundColor Cyan -NoNewline; Write-Host (' ' + $env:LG_MSG)"
exit /b 0

:fatal
echo.
call :err "Startup failed. Fix the error above and re-run."
echo.
exit /b 1


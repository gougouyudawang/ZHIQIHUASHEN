@echo off
setlocal

set "PROJECT_DIR=%~dp0"
if "%PROJECT_DIR:~-1%"=="\" set "PROJECT_DIR=%PROJECT_DIR:~0,-1%"
set "PYTHON_EXE=%PROJECT_DIR%\.venv312\Scripts\python.exe"
set "PYTHONPATH=%PROJECT_DIR%"
set "USE_FIXED_KEYS=1"
set "PORT=8112"

cd /d "%PROJECT_DIR%"
echo Cleaning port %PORT%...
powershell -NoProfile -ExecutionPolicy Bypass -Command "$c=Get-NetTCPConnection -LocalPort %PORT% -State Listen -ErrorAction SilentlyContinue; if ($c) { $c | Select-Object -ExpandProperty OwningProcess -Unique | ForEach-Object { Stop-Process -Id $_ -Force -ErrorAction SilentlyContinue } }"
echo Starting AP service on http://127.0.0.1:8112
"%PYTHON_EXE%" -m uvicorn app.ap_app:app --host 127.0.0.1 --port 8112

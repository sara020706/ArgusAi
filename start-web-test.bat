@echo off
setlocal

set PYTHON=C:\Users\e parthasarathy\AppData\Local\Programs\Python\Python312\python.exe
set PROJECT_DIR=%~dp0
set NODE=node
set NPM=npm

echo.
echo  ================================
echo   ARGUS  ^|  Web Test App
echo  ================================
echo.

:: ── Check Python ─────────────────────────────────────────────────────────────
if not exist "%PYTHON%" (
    echo [ERROR] Python not found at:
    echo         %PYTHON%
    echo         Edit PYTHON= at the top of this file to point to your Python.
    pause
    exit /b 1
)

:: ── Check Node / npm ─────────────────────────────────────────────────────────
where npm >nul 2>&1
if %errorlevel% neq 0 (
    echo [ERROR] npm not found. Install Node.js from https://nodejs.org
    pause
    exit /b 1
)

:: ── Install JS deps if node_modules is missing ───────────────────────────────
if not exist "%PROJECT_DIR%web-test\node_modules" (
    echo [0/3] Installing web-test dependencies ^(first run only^)...
    pushd "%PROJECT_DIR%web-test"
    call npm install
    popd
    echo     Done.
    echo.
)

:: ── Start API server ──────────────────────────────────────────────────────────
echo [1/3] Starting Argus API on http://localhost:8000 ...
start "Argus API" cmd /k "cd /d "%PROJECT_DIR%" && "%PYTHON%" -m uvicorn argus.api.server:create_app --factory --host 0.0.0.0 --port 8000"

:: ── Wait for API to be ready (poll /health up to 20 s) ───────────────────────
echo     Waiting for API to be ready...
set /a attempts=0
:wait_loop
timeout /t 1 /nobreak >nul
"%PYTHON%" -c "import urllib.request; urllib.request.urlopen('http://localhost:8000/health', timeout=2)" >nul 2>&1
if %errorlevel%==0 goto api_ready
set /a attempts+=1
if %attempts% lss 20 goto wait_loop
echo [WARN] API did not respond after 20 s — web test will show offline mode.

:api_ready
echo     API is up.
echo.

:: ── Start web test dev server ─────────────────────────────────────────────────
echo [2/3] Starting Web Test App on http://localhost:3000 ...
start "Argus Web Test" cmd /k "cd /d "%PROJECT_DIR%web-test" && npm run dev"

:: ── Open browser ──────────────────────────────────────────────────────────────
echo [3/3] Opening browser...
timeout /t 3 /nobreak >nul
start "" "http://localhost:3000"

echo.
echo  ================================
echo   Services running:
echo   API       : http://localhost:8000
echo   API docs  : http://localhost:8000/docs
echo   Web Test  : http://localhost:3000
echo.
echo   See web-test\TESTING.md for what to test.
echo   Close the two console windows to stop.
echo  ================================
echo.
endlocal

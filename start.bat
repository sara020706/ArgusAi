@echo off
setlocal

set PYTHON=C:\Users\e parthasarathy\AppData\Local\Programs\Python\Python312\python.exe
set PROJECT_DIR=%~dp0
set ARGUS_API_URL=http://localhost:8000

echo.
echo  ================================
echo   ARGUS  ^|  Insider Threat Detection
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

:: ── Start API server in a new window ─────────────────────────────────────────
echo [1/2] Starting Argus API server on http://localhost:8000 ...
start "Argus API" cmd /k "cd /d "%PROJECT_DIR%" && "%PYTHON%" -m uvicorn argus.api.server:create_app --factory --host 0.0.0.0 --port 8000"

:: ── Wait for the API to become ready (poll /health up to 15 s) ───────────────
echo     Waiting for API to be ready...
set /a attempts=0
:wait_loop
timeout /t 1 /nobreak >nul
"%PYTHON%" -c "import urllib.request; urllib.request.urlopen('http://localhost:8000/health', timeout=2)" >nul 2>&1
if %errorlevel%==0 goto api_ready
set /a attempts+=1
if %attempts% lss 15 goto wait_loop
echo [WARN] API did not respond after 15 s — dashboard may not connect immediately.

:api_ready
echo     API is up.
echo.

:: ── Start dashboard in a new window ──────────────────────────────────────────
echo [2/2] Starting Argus Dashboard on http://localhost:8501 ...
start "Argus Dashboard" cmd /k "cd /d "%PROJECT_DIR%" && set ARGUS_API_URL=%ARGUS_API_URL% && "%PYTHON%" -m streamlit run argus\dashboard\app.py --server.port 8501 --server.headless true"

:: ── Open browser ─────────────────────────────────────────────────────────────
timeout /t 3 /nobreak >nul
echo.
echo  Opening dashboard in browser...
start "" "http://localhost:8501"

echo.
echo  ================================
echo   Both services are running.
echo   API       : http://localhost:8000
echo   Dashboard : http://localhost:8501
echo   API docs  : http://localhost:8000/docs
echo.
echo   Close the two console windows to stop.
echo  ================================
echo.
endlocal

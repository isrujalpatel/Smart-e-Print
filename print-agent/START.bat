@echo off
title Smart E-Print — Print Agent [Online]
color 0B
echo.
echo  ======================================================
echo    Smart E-Print — Local Print Agent
echo    Listening on: http://127.0.0.1:8765
echo    Shop: Umiya Graphics and Printing
echo    Press Ctrl+C in this window to stop the agent.
echo  ======================================================
echo.

:: 1. Check Python
python --version >nul 2>&1
if errorlevel 1 (
    echo  [ERROR] Python is not installed or not in PATH!
    echo.
    echo  Please install Python 3.8 - 3.12 from:
    echo  https://www.python.org/downloads/
    echo.
    echo  IMPORTANT: Check the box "Add Python to PATH" during install!
    echo.
    pause
    start https://www.python.org/downloads/
    exit /b 1
)

:: 2. Auto-kill any stale process on port 8765 to prevent Errno 10048 bind errors
for /f "tokens=5" %%p in ('netstat -aon 2^>nul ^| findstr /r ":8765 .*LISTENING"') do (
    echo  [INFO] Port 8765 was occupied by PID %%p. Freeing port for fresh start...
    taskkill /f /pid %%p >nul 2>&1
)
timeout /t 1 /nobreak >nul 2>&1

:: 3. Check if packages are installed
python -c "import fastapi, uvicorn" >nul 2>&1
if errorlevel 1 (
    echo  [INFO] Installing required packages...
    call INSTALL.bat
)

:: 4. Verify SumatraPDF exists in tools/
if not exist "tools\SumatraPDF.exe" (
    echo  [INFO] Initializing silent print engine...
    call INSTALL.bat
)

:: 5. Launch agent
echo.
echo  [READY] Launching print agent on http://127.0.0.1:8765 ...
echo  Keep this black window OPEN while printing orders.
echo.

python -m uvicorn agent:app --host 127.0.0.1 --port 8765 --log-level info

if errorlevel 1 (
    echo.
    echo  ======================================================
    echo  [ERROR] Agent stopped unexpectedly.
    echo  Try running INSTALL.bat to repair dependencies.
    echo  ======================================================
) else (
    echo.
    echo  Print Agent stopped cleanly.
)
pause

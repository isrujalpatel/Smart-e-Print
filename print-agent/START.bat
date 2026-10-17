@echo off
title Smart E-Print — Print Agent  [Running]
color 0B
echo.
echo  ============================================
echo   Smart E-Print Print Agent
echo   Listening on http://127.0.0.1:8765
echo   Press Ctrl+C to stop.
echo  ============================================
echo.

:: 1. Check Python
python --version >nul 2>&1
if errorlevel 1 (
    echo  [ERROR] Python is not installed or not in PATH!
    echo.
    echo  Please download and install Python from:
    echo  https://www.python.org/downloads/
    echo.
    echo  IMPORTANT: Check "Add Python to PATH" during install.
    echo.
    pause
    start https://www.python.org/downloads/
    exit /b 1
)

:: 2. Check if dependencies are installed; auto-run INSTALL.bat if needed
python -c "import fastapi, uvicorn" >nul 2>&1
if errorlevel 1 (
    echo  [INFO] Required packages not found. Running automatic setup...
    call INSTALL.bat
)

:: 3. Run the agent using python -m uvicorn (reliable on all Windows PATH configs)
echo.
echo  Starting agent on http://127.0.0.1:8765 ...
python -m uvicorn agent:app --host 127.0.0.1 --port 8765 --log-level info

if errorlevel 1 (
    echo.
    echo  [ERROR] Agent stopped with an error. Please verify INSTALL.bat.
) else (
    echo.
    echo  Agent stopped.
)
pause


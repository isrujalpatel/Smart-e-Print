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

:: Check Python
python --version >nul 2>&1
if errorlevel 1 (
    echo  [ERROR] Python not found. Please run INSTALL.bat first!
    pause
    exit
)

:: Run the agent
uvicorn agent:app --host 127.0.0.1 --port 8765 --log-level warning

echo.
echo  Agent stopped.
pause

@echo off
:: Smart E-Print — Print Agent Launcher
:: Double-click this file on the Admin Windows PC to start the agent.
:: It will listen on http://127.0.0.1:8765 (localhost only).

title Smart E-Print Print Agent

:: Optional: set your secret token and backend URL here
:: set AGENT_TOKEN=your-secret-token-here
:: set BACKEND_URL=https://smart-e-print.onrender.com/api

echo.
echo  ██████  Smart E-Print Print Agent
echo  Starting on http://127.0.0.1:8765 ...
echo  Press Ctrl+C to stop.
echo.

:: Activate virtual environment if present
if exist venv\Scripts\activate.bat (
    call venv\Scripts\activate.bat
)

uvicorn agent:app --host 127.0.0.1 --port 8765 --log-level info

pause

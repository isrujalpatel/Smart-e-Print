@echo off
title Smart E-Print — Setup
color 0A
echo.
echo  ============================================
echo   Smart E-Print Print Agent — First-time Setup
echo  ============================================
echo.
echo  This will install everything needed.
echo  Please wait...
echo.

:: Check Python
python --version >nul 2>&1
if errorlevel 1 (
    echo  [ERROR] Python is not installed!
    echo.
    echo  Please download and install Python from:
    echo  https://www.python.org/downloads/
    echo.
    echo  IMPORTANT: Check "Add Python to PATH" during install.
    echo.
    pause
    start https://www.python.org/downloads/
    exit
)

echo  [OK] Python found.
echo.

:: Install packages
echo  Installing required packages...
pip install fastapi uvicorn pywin32 >nul 2>&1

echo  [OK] Packages installed.
echo.

:: Install SumatraPDF if not present
if not exist "C:\Program Files\SumatraPDF\SumatraPDF.exe" (
    if not exist "C:\Program Files (x86)\SumatraPDF\SumatraPDF.exe" (
        echo  [INFO] Opening SumatraPDF download page...
        echo         Please install it for best PDF printing.
        echo         Install to default location.
        echo.
        start https://www.sumatrapdfreader.org/free-pdf-reader
        echo  After installing SumatraPDF, close this window and run INSTALL.bat again.
        echo  (Or skip this — it will still work, just may show a print dialog)
        echo.
    )
) else (
    echo  [OK] SumatraPDF found.
)

echo.
echo  ============================================
echo   Setup Complete!
echo   Now double-click START.bat to run the agent.
echo  ============================================
echo.
pause

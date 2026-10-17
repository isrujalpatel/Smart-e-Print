@echo off
title Smart E-Print — Setup
color 0A
echo.
echo  ============================================
echo   Smart E-Print Print Agent — First-time Setup
echo  ============================================
echo.
echo  This will install everything needed automatically.
echo  Please wait...
echo.

:: ── Check Python ──────────────────────────────────────────────────────────────
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

:: ── Install Python packages ───────────────────────────────────────────────────
echo  Installing required packages (fastapi, uvicorn, pywin32, pydantic)...
python -m pip install -r requirements.txt
if errorlevel 1 (
    echo  [WARNING] Retrying install with direct package names...
    python -m pip install fastapi "uvicorn[standard]" pywin32 pydantic
)
echo  [OK] Packages installed.
echo.

:: ── Auto-Download SumatraPDF (portable, no install needed) ───────────────────
set SUMATRA_SYSTEM_64=C:\Program Files\SumatraPDF\SumatraPDF.exe
set SUMATRA_SYSTEM_86=C:\Program Files (x86)\SumatraPDF\SumatraPDF.exe
set SUMATRA_LOCAL=tools\SumatraPDF.exe
set SUMATRA_URL=https://www.sumatrapdfreader.org/dl/rel/3.5.2/SumatraPDF-3.5.2-64.exe

:: Check if already installed system-wide
if exist "%SUMATRA_SYSTEM_64%" (
    echo  [OK] SumatraPDF found at Program Files.
    goto sumatra_done
)
if exist "%SUMATRA_SYSTEM_86%" (
    echo  [OK] SumatraPDF found at Program Files (x86).
    goto sumatra_done
)

:: Check if already downloaded locally
if exist "%SUMATRA_LOCAL%" (
    echo  [OK] SumatraPDF already downloaded locally at: %SUMATRA_LOCAL%
    goto sumatra_done
)

:: Auto-download using PowerShell (built-in on all modern Windows)
echo  [INFO] SumatraPDF not found. Auto-downloading portable version...
echo         URL : %SUMATRA_URL%
echo         Dest: %SUMATRA_LOCAL%
echo.

if not exist "tools" mkdir tools

powershell -NoProfile -ExecutionPolicy Bypass -Command ^
  "$ProgressPreference='SilentlyContinue'; ^
   Write-Host '  Downloading SumatraPDF...'; ^
   try { ^
     Invoke-WebRequest -Uri '%SUMATRA_URL%' -OutFile '%SUMATRA_LOCAL%' -UseBasicParsing; ^
     Write-Host '  [OK] SumatraPDF downloaded successfully.'; ^
   } catch { ^
     Write-Host ('  [ERROR] Download failed: ' + $_.Exception.Message); ^
     exit 1; ^
   }"

if exist "%SUMATRA_LOCAL%" (
    echo  [OK] SumatraPDF saved to: %SUMATRA_LOCAL%
) else (
    echo  [WARNING] SumatraPDF download failed.
    echo            PDF printing will still work via Windows default handler,
    echo            but a print dialog may appear.
)

:sumatra_done
echo.
echo  ============================================
echo   Setup Complete!
echo   Now double-click start-agent.bat to run.
echo  ============================================
echo.
pause

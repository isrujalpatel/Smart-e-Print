@echo off
title Smart E-Print — Setup & Repair
color 0A
echo.
echo  ======================================================
echo    Smart E-Print Print Agent — Automated Setup
echo  ======================================================
echo.
echo  Checking requirements and dependencies...
echo.

:: 1. Check Python
python --version >nul 2>&1
if errorlevel 1 (
    echo  [ERROR] Python is not installed or not in PATH!
    echo.
    echo  Please install Python from https://www.python.org/downloads/
    echo  and check "Add Python to PATH".
    echo.
    pause
    start https://www.python.org/downloads/
    exit /b 1
)

for /f "tokens=*" %%v in ('python --version') do echo  [OK] %%v detected.
echo.

:: 2. Upgrade pip and install requirements
echo  Installing required Python libraries...
python -m pip install --upgrade pip >nul 2>&1
python -m pip install -r requirements.txt
if errorlevel 1 (
    echo  [RETRY] Installing packages individually...
    python -m pip install fastapi "uvicorn[standard]" pywin32 pydantic
)
echo  [OK] Python libraries installed successfully.
echo.

:: 3. Setup SumatraPDF
set SUMATRA_LOCAL=tools\SumatraPDF.exe
if exist "%SUMATRA_LOCAL%" (
    echo  [OK] SumatraPDF silent print engine is already installed at: %SUMATRA_LOCAL%
    goto finish
)

echo  [INFO] Setting up SumatraPDF portable...
if not exist "tools" mkdir tools

powershell -NoProfile -ExecutionPolicy Bypass -Command ^
  "$ProgressPreference='SilentlyContinue'; ^
   [Net.ServicePointManager]::SecurityProtocol = [Net.SecurityProtocolType]::Tls12; ^
   $urls = @( ^
     'https://files.sumatrapdfreader.org/software/sumatrapdf/rel/3.5.2/SumatraPDF-3.5.2-64.exe', ^
     'https://github.com/sumatrapdfreader/sumatrapdf/releases/download/v3.5.2/SumatraPDF-3.5.2-64.exe', ^
     'https://www.sumatrapdfreader.org/dl/rel/3.5.2/SumatraPDF-3.5.2-64.exe' ^
   ); ^
   $done = $false; ^
   foreach ($u in $urls) { ^
     try { ^
       Write-Host ('  Attempting download from: ' + $u); ^
       $req = [System.Net.HttpWebRequest]::Create($u); ^
       $req.UserAgent = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'; ^
       $resp = $req.GetResponse(); ^
       $stream = $resp.GetResponseStream(); ^
       $file = [System.IO.File]::Create('%SUMATRA_LOCAL%'); ^
       $stream.CopyTo($file); ^
       $file.Close(); ^
       $stream.Close(); ^
       $resp.Close(); ^
       if ((Get-Item '%SUMATRA_LOCAL%').Length -gt 1000000) { ^
         Write-Host '  [OK] Downloaded SumatraPDF successfully!'; ^
         $done = $true; ^
         break; ^
       } ^
     } catch { ^
       Write-Host ('  Failed mirror: ' + $_.Exception.Message); ^
     } ^
   }; ^
   if (-not $done) { exit 1; }"

if exist "%SUMATRA_LOCAL%" (
    echo  [OK] SumatraPDF ready at: %SUMATRA_LOCAL%
) else (
    echo  [WARNING] Could not auto-download SumatraPDF.
    echo  PDF printing will fall back to Windows ShellExecute.
)

:finish
echo.
echo  ======================================================
echo    Setup Completed Successfully!
echo    You can now double-click start-agent.bat to run.
echo  ======================================================
echo.
pause

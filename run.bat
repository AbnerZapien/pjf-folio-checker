@echo off
setlocal enabledelayedexpansion

cd /d "%~dp0"

echo ==========================================
echo   PJF Folio Checker - Windows Launcher
echo ==========================================
echo.

REM Prefer Windows Python launcher (py). Avoid MSYS2 python.
set "PY=py"
where py >nul 2>nul
if errorlevel 1 (
  set "PY=python"
  where python >nul 2>nul || (
    echo ERROR: Python not found.
    echo.
    echo Install Python 3.10+ (64-bit) from python.org
    echo and make sure "Add python.exe to PATH" is enabled.
    echo.
    pause
    exit /b 1
  )
)

REM Validate python is runnable
%PY% --version >nul 2>nul || (
  echo ERROR: Python is not runnable.
  pause
  exit /b 1
)

REM Create venv if missing
if not exist ".venv" (
  echo Creating virtual environment...
  %PY% -m venv .venv || (
    echo ERROR: Failed to create venv.
    pause
    exit /b 1
  )
)

call .venv\Scripts\activate.bat

REM Ensure pip exists
python -m ensurepip --upgrade >nul 2>nul

echo Upgrading pip...
python -m pip install --upgrade pip || (
  echo ERROR: pip is not working. Fix your Python installation (pip missing).
  pause
  exit /b 1
)

echo Installing requirements...
python -m pip install -r requirements.txt || (
  echo ERROR: Failed to install requirements.
  pause
  exit /b 1
)

REM Install Playwright Chromium only if missing
set "PW_CACHE=%LOCALAPPDATA%\ms-playwright"
dir /b "%PW_CACHE%\chromium-*" >nul 2>nul
if errorlevel 1 (
  echo Installing Playwright Chromium (first run only)...
  python -m playwright install chromium || (
    echo ERROR: Playwright browser install failed.
    pause
    exit /b 1
  )
) else (
  echo Playwright Chromium already installed.
)

echo.
echo Starting wizard...
python pjf_wizard.py

echo.
pause

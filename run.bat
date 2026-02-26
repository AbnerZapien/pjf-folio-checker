@echo off
setlocal
cd /d %~dp0

where python >nul 2>nul
if errorlevel 1 (
  echo Python not found. Install Python 3.9+ from python.org and re-run.
  pause
  exit /b 1
)

if not exist .venv (
  python -m venv .venv
)

call .venv\Scripts\activate.bat
python -m pip install --upgrade pip
python -m pip install -r requirements.txt

REM Install Playwright Chromium only if not already present
dir /b "%LOCALAPPDATA%\ms-playwright\chromium-*" >nul 2>nul
if errorlevel 1 (
  python -m playwright install chromium
) else (
  echo Playwright Chromium already installed.
)

python pjf_wizard.py
pause

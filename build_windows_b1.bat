@echo off
setlocal
cd /d "%~dp0"

echo ==========================================
echo   BUILD: PJF Folio Checker (Windows B1)
echo ==========================================
echo.

where py >nul 2>nul
if errorlevel 1 (
  echo ERROR: py.exe not found. Install Python 3.11+ from python.org
  pause
  exit /b 1
)

REM Build venv
if not exist .buildvenv (
  py -3.11 -m venv .buildvenv || exit /b 1
)
call .buildvenv\Scripts\activate.bat || exit /b 1

python -m pip install --upgrade pip || exit /b 1
python -m pip install -r requirements.txt pyinstaller || exit /b 1

REM Ensure Playwright Chromium is downloaded (local cache)
python -m playwright install chromium || exit /b 1

REM Copy ALL ms-playwright cache (simplest reliable B1)
rmdir /s /q build_assets 2>nul
mkdir build_assets\ms-playwright
xcopy /E /I /Y "%LOCALAPPDATA%\ms-playwright\*" "build_assets\ms-playwright\" || exit /b 1

REM Build onedir exe
rmdir /s /q dist build 2>nul
pyinstaller --clean --noconfirm --onedir --name "PJF-Folio-Checker" ^
  --collect-all playwright ^
  --collect-all openpyxl ^
  --collect-all rich ^
  --add-data "build_assets\ms-playwright;ms-playwright" ^
  pjf_wizard.py || exit /b 1

REM Zip it
powershell -NoProfile -Command "Compress-Archive -Path 'dist\PJF-Folio-Checker\*' -DestinationPath 'PJF-Folio-Checker-Windows-B1.zip' -Force" || exit /b 1

echo.
echo Built: PJF-Folio-Checker-Windows-B1.zip
echo.
pause

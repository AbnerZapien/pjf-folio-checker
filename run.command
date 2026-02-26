#!/bin/bash
set -euo pipefail

cd "$(dirname "$0")"

echo "=========================================="
echo "  PJF Folio Checker - macOS Launcher"
echo "=========================================="
echo

if ! command -v python3 >/dev/null 2>&1; then
  echo "ERROR: python3 not found."
  echo "Install Python 3.10+ from python.org and re-run."
  echo
  read -r -p "Press Enter to close..."
  exit 1
fi

if [ ! -d ".venv" ]; then
  echo "Creating virtual environment..."
  python3 -m venv .venv
fi

source .venv/bin/activate

echo "Upgrading pip..."
python3 -m pip install --upgrade pip

echo "Installing requirements..."
python3 -m pip install -r requirements.txt

CACHE1="$HOME/Library/Caches/ms-playwright"
CACHE2="$HOME/.cache/ms-playwright"
if ls "$CACHE1/chromium-"* "$CACHE2/chromium-"* >/dev/null 2>&1; then
  echo "Playwright Chromium already installed."
else
  echo "Installing Playwright Chromium (first run only)..."
  python3 -m playwright install chromium
fi

echo
echo "Starting wizard..."
python3 pjf_wizard.py

echo
read -r -p "Press Enter to close..."

cd "$(dirname "$0")"

python3 -V >/dev/null 2>&1
if [ $? -ne 0 ]; then
  echo "python3 not found. Install Python 3.9+ and re-run."
  read -r
  exit 1
fi

if [ ! -d ".venv" ]; then
  python3 -m venv .venv
fi

. .venv/bin/activate
python3 -m pip install --upgrade pip
python3 -m pip install -r requirements.txt
python3 -m playwright install chromium

python3 pjf_wizard.py
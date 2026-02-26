from pathlib import Path
import re

p = Path("pjf_checker.py")
s = p.read_text(encoding="utf-8")

defaults = r'''
# --- Safe defaults (so run_plan won't crash if constants were removed by a restore/patch) ---
try:
    CIRCUITO_TARGET
except NameError:
    CIRCUITO_TARGET = "SEXTO CIRCUITO"

try:
    FILTER_TITLE
except NameError:
    FILTER_TITLE = "Filtro Expediente"

try:
    NOT_FOUND_TEXT
except NameError:
    NOT_FOUND_TEXT = "No existen datos para el expediente"
# --- End defaults ---
'''

if "Safe defaults (so run_plan" not in s:
    # insert right after the initial import block
    m = re.search(r"^(?:import[^\n]*\n)+\n", s, flags=re.M)
    if not m:
        s = defaults + "\n" + s
    else:
        s = s[:m.end()] + defaults + "\n" + s[m.end():]

p.write_text(s, encoding="utf-8")
print("Patched pjf_checker.py: added safe default constants.")

from pathlib import Path
import re

p = Path("pjf_checker.py")
s = p.read_text(encoding="utf-8")

# Ensure constants exist (only if missing)
if "FILTER_TITLE" not in s:
    s = 'FILTER_TITLE = "Filtro Expediente"\n' + s

if "CIRCUITO_TARGET" not in s:
    s = 'CIRCUITO_TARGET = "SEXTO CIRCUITO"\n' + s

# Add helper functions only if missing
if "def select_circuito(" not in s:
    helpers = r'''
def select_circuito(page, circuito_text: str):
    # Click the circuito control next to label "Circuito:" and select by typing + Enter
    label = page.locator("xpath=//*[normalize-space()='Circuito:']")
    label.wait_for(timeout=20000)
    ctrl = label.locator("xpath=following::*[self::div or self::span or self::input][1]")
    ctrl.click(force=True)
    page.keyboard.type(circuito_text, delay=25)
    page.keyboard.press("Enter")

def wait_for_filter_modal(page):
    page.get_by_text(FILTER_TITLE, exact=False).wait_for(timeout=20000)
'''
    # Insert after the first block of imports
    m = re.search(r"^(?:import[^\n]*\n)+\n", s, flags=re.M)
    if m:
        s = s[:m.end()] + helpers + "\n" + s[m.end():]
    else:
        s = helpers + "\n" + s

p.write_text(s, encoding="utf-8")
print("Patched pjf_checker.py: added select_circuito() + wait_for_filter_modal().")

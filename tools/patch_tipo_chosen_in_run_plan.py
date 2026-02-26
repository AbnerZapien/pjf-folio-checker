from pathlib import Path
import re

p = Path("pjf_checker.py")
s = p.read_text(encoding="utf-8")

# Add helper if missing
if "def _set_tipo_via_chosen" not in s:
    helper = r'''
def _set_tipo_via_chosen(modal, page, tipo_label: str):
    # Works even when the real <select> is hidden by Chosen
    chosen = modal.locator("#ddlTipoAsunto_chosen").first
    if chosen.count() == 0:
        # fallback: chosen container after select
        chosen = modal.locator("select#ddlTipoAsunto").locator("xpath=following-sibling::div[contains(@class,'chosen-container')][1]").first
    chosen.wait_for(state="attached", timeout=10000)
    chosen.click(force=True)

    search = chosen.locator("input[type='text']").first
    try:
        search.wait_for(state="attached", timeout=5000)
        search.fill(tipo_label)
    except Exception:
        page.keyboard.type(tipo_label, delay=25)

    page.keyboard.press("Enter")
    page.wait_for_timeout(200)
'''
    # Insert near other helpers: before run_plan definition
    s = re.sub(r"^def run_plan\(", helper + "\n\ndef run_plan(", s, flags=re.M)

# In run_plan loop, replace the select_option fallback with chosen helper
# Replace this block:
# else:
#     modal.locator("#ddlTipoAsunto").select_option(label=chosen_tipo)
s2 = re.sub(
    r'else:\n\s*modal\.locator\("#ddlTipoAsunto"\)\.select_option\(label=chosen_tipo\)',
    'else:\n                    _set_tipo_via_chosen(modal, page, chosen_tipo)',
    s,
)

p.write_text(s2, encoding="utf-8")
print("Patched pjf_checker.py: run_plan now uses Chosen-based tipo selection.")

from pathlib import Path
import re

p = Path("pjf_checker.py")
s = p.read_text(encoding="utf-8")

# If it already exists, do nothing.
if "def auto_login_if_needed(" in s:
    print("auto_login_if_needed() already exists. No change.")
    raise SystemExit(0)

login_block = r'''
import re

BASE_URL = "https://www.serviciosenlinea.pjf.gob.mx/"
LOGIN_MENU_TEXT = "Ingresa al Portal"
LOGIN_TARGET_TEXT = "Juzgados de Distrito y Tribunales de Circuito"

def _setup_auto_dialog_accept(page):
    def _on_dialog(d):
        try:
            d.accept()
        except Exception:
            pass
    page.on("dialog", _on_dialog)

def _is_logged_in(page) -> bool:
    return page.get_by_text("Consulta de datos públicos de expedientes", exact=False).count() > 0

def _cleanup_backdrops(page):
    try:
        page.evaluate("""
          document.querySelectorAll('.modal-backdrop').forEach(e => e.remove());
          document.body.classList.remove('modal-open');
          document.body.style.removeProperty('padding-right');
        """)
    except Exception:
        pass

def auto_login_if_needed(page, user: str, password: str):
    _setup_auto_dialog_accept(page)

    page.goto(BASE_URL, wait_until="domcontentloaded")

    if _is_logged_in(page):
        return

    # Open the dropdown
    page.get_by_text(re.compile(r"Ingresa al Portal|Ingresar al Portal", re.I), exact=False).click()

    # Click the dropdown link (use role=link to avoid strict-mode collisions with description text)
    page.get_by_role("link", name=re.compile(r"Juzgados de Distrito", re.I)).click()

    # Login form
    u = page.locator("#UserName")
    pw = page.locator("#UserPassword")
    u.wait_for(state="visible", timeout=20000)
    pw.wait_for(state="visible", timeout=20000)

    u.fill(user)
    pw.fill(password)

    page.get_by_role("button", name=re.compile(r"^Ingresar$", re.I)).click()

    # Profile modal: click Persona Física (sometimes appears a second later)
    try:
        page.get_by_text("Seleccione un perfil", exact=False).wait_for(timeout=20000)

        # Prefer clicking the tile container; fallback to any text match
        try:
            page.locator("span.btnDemandaA", has_text=re.compile(r"Persona\s+F[ií]sica", re.I)).first.click(force=True, timeout=15000)
        except Exception:
            page.get_by_text(re.compile(r"Persona\s+F[ií]sica", re.I), exact=False).first.click(force=True, timeout=15000)

        # Alert after selecting profile is auto-accepted by dialog handler

        # Wait for modal to disappear (best effort, then force-clean overlays)
        try:
            page.locator("#modalModalidad").wait_for(state="hidden", timeout=12000)
        except Exception:
            pass
        _cleanup_backdrops(page)

    except Exception:
        # Sometimes it skips profile selection and goes straight in
        _cleanup_backdrops(page)

    # Confirm we are in
    page.get_by_text("Consulta de datos públicos de expedientes", exact=False).wait_for(timeout=30000)
'''

# Insert right after imports (before other constants), safest placement.
# We find the first blank line after imports and insert.
m = re.search(r"^(?:import[^\n]*\n)+\n", s, flags=re.M)
if not m:
    # fallback: insert at top
    s = login_block + "\n" + s
else:
    s = s[:m.end()] + login_block + "\n" + s[m.end():]

p.write_text(s, encoding="utf-8")
print("Patched pjf_checker.py: added auto_login_if_needed() and helpers.")

from pathlib import Path
import re

p = Path("pjf_checker.py")
s = p.read_text(encoding="utf-8")

if "_ensure_modalidad_closed(" not in s:
    helper = r'''
def _js_click(locator):
    loc = locator.first
    loc.wait_for(state="attached", timeout=15000)
    loc.evaluate("el => el.click()")

def _ensure_modalidad_closed(page):
    for _ in range(10):
        try:
            visible = page.evaluate("""
() => {
  const m = document.getElementById('modalModalidad');
  if (!m) return false;
  const st = window.getComputedStyle(m);
  const shown = st && st.display !== 'none' && st.visibility !== 'hidden' && st.opacity !== '0';
  const cls = m.classList.contains('in') || m.classList.contains('show');
  const disp = (m.style && (m.style.display === 'block'));
  return shown && (cls || disp);
}
""")
            if not visible:
                try:
                    page.evaluate("""
() => {
  const m = document.getElementById('modalModalidad');
  if (m) { m.classList.remove('in','show'); m.style.display='none'; m.setAttribute('aria-hidden','true'); }
  document.querySelectorAll('.modal-backdrop').forEach(e => e.remove());
  document.body.classList.remove('modal-open');
  document.body.style.removeProperty('padding-right');
}
""")
                except Exception:
                    pass
                return

            try:
                page.keyboard.press("Escape")
            except Exception:
                pass

            try:
                page.evaluate("""
() => {
  const m = document.getElementById('modalModalidad');
  if (m) { m.classList.remove('in','show'); m.style.display='none'; m.setAttribute('aria-hidden','true'); }
  document.querySelectorAll('.modal-backdrop').forEach(e => e.remove());
  document.body.classList.remove('modal-open');
  document.body.style.removeProperty('padding-right');
}
""")
            except Exception:
                pass

            try:
                _cleanup_backdrops(page)
            except Exception:
                pass

            page.wait_for_timeout(200)
        except Exception:
            try:
                page.evaluate("""
() => {
  const m = document.getElementById('modalModalidad');
  if (m) { m.classList.remove('in','show'); m.style.display='none'; m.setAttribute('aria-hidden','true'); }
  document.querySelectorAll('.modal-backdrop').forEach(e => e.remove());
  document.body.classList.remove('modal-open');
  document.body.style.removeProperty('padding-right');
}
""")
            except Exception:
                pass
            try:
                _cleanup_backdrops(page)
            except Exception:
                pass
            page.wait_for_timeout(200)

    try:
        _cleanup_backdrops(page)
    except Exception:
        pass
'''
    s = re.sub(r"^def auto_login_if_needed\(", helper + "\n\ndef auto_login_if_needed(", s, flags=re.M)
    if "_ensure_modalidad_closed(" not in s:
        raise SystemExit("Could not insert helper before auto_login_if_needed().")

menu_line = 'page.get_by_text("Consulta de datos públicos de expedientes", exact=False).click()'
if menu_line in s:
    s = s.replace(
        menu_line,
        '_ensure_modalidad_closed(page)\n        _js_click(page.get_by_text("Consulta de datos públicos de expedientes", exact=False))'
    )
else:
    raise SystemExit("Could not find menu click line to patch in run_plan().")

p.write_text(s, encoding="utf-8")
print("Patched pjf_checker.py: close modalModalidad before clicking menu + JS click.")

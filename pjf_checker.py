import re
import time
from datetime import datetime
from pathlib import Path
from openpyxl import load_workbook, Workbook
from playwright.sync_api import sync_playwright, TimeoutError as PWTimeout

BASE_URL = "https://www.serviciosenlinea.pjf.gob.mx/"
LOGIN_MENU_REGEX = re.compile(r"Ingres(a|ar)\s+al\s+Portal", re.I)
LOGIN_TARGET_TEXT = "Juzgados de Distrito y Tribunales de Circuito"

FILTER_TITLE = "Filtro Expediente"
NOT_FOUND_TEXT = "No existen datos para el expediente"

EXP_RE = re.compile(r"^\s*(\d{1,6})\s*/\s*(\d{4})\s*$")

def _normalize_folio(v):
    if v is None:
        return None
    s = str(v).strip()
    m = EXP_RE.match(s)
    if not m:
        return None
    return f"{int(m.group(1))}/{m.group(2)}"

def read_folios_by_tipo_xlsx(excel_path: str) -> dict[str, list[str]]:
    wb = load_workbook(excel_path, data_only=True)
    ws = wb.active

    tipos: dict[str, list[str]] = {}
    for col in range(1, ws.max_column + 1):
        header = ws.cell(row=1, column=col).value
        if header is None:
            continue
        tipo = str(header).strip()
        if not tipo:
            continue

        folios: list[str] = []
        row = 2
        while True:
            v = ws.cell(row=row, column=col).value
            if v is None:
                break
            nf = _normalize_folio(v)
            if nf:
                folios.append(nf)
            row += 1

        seen, out = set(), []
        for f in folios:
            if f not in seen:
                seen.add(f)
                out.append(f)

        if out:
            tipos[tipo] = out

    return tipos

def _write_outputs(rows, out_dir: Path):
    out_full = out_dir / "Folios_results.xlsx"
    out_missing = out_dir / "Folios_missing.xlsx"

    wb1 = Workbook()
    ws1 = wb1.active
    ws1.title = "Results"
    ws1.append(["Tipo", "Folio", "Found", "Status", "CheckedAt", "Notes"])
    for r in rows:
        ws1.append([r["tipo"], r["folio"], r["found"], r["status"], r["checked_at"], r["notes"] or ""])
    wb1.save(out_full)

    missing = [r for r in rows if (not r["found"] and r["status"] in ("NOT_FOUND", "ERROR"))]
    wb2 = Workbook()
    ws2 = wb2.active
    ws2.title = "MissingOrError"
    ws2.append(["Tipo", "Folio", "Status"])
    for r in missing:
        ws2.append([r["tipo"], r["folio"], r["status"]])
        ws2.cell(row=ws2.max_row, column=2).number_format = "@"
    wb2.save(out_missing)

    return out_full, out_missing

def _cleanup_overlays(page):
    try:
        page.evaluate("""
          document.querySelectorAll('.modal-backdrop').forEach(e => e.remove());
          document.body.classList.remove('modal-open');
          document.body.style.removeProperty('padding-right');
        """)
    except Exception:
        pass

def _close_extra_pages(context, main_page):
    for p in list(context.pages):
        if p is main_page:
            continue
        try:
            p.close()
        except Exception:
            pass

def _setup_auto_dialog_accept(page):
    def _on_dialog(d):
        try:
            d.accept()
        except Exception:
            pass
    page.on("dialog", _on_dialog)

def _is_logged_in(page) -> bool:
    return page.get_by_text("Consulta de datos públicos de expedientes", exact=False).count() > 0

def _click_login_entry(page):
    locs = [
        page.get_by_text(LOGIN_MENU_REGEX, exact=False),
        page.get_by_role("link", name=re.compile("Ingres", re.I)),
        page.get_by_role("button", name=re.compile("Ingres", re.I)),
        page.locator("a:has-text('Ingres')"),
        page.locator("button:has-text('Ingres')"),
    ]
    for loc in locs:
        try:
            if loc.count() > 0:
                loc.first.click(force=True, timeout=8000)
                return
        except Exception:
            pass
    raise RuntimeError("Could not click login entry (Ingresa al Portal).")

def _ensure_profile_selected(page):
    # Optimized but stable timeouts (your latest values)
    modal = page.locator("#modalModalidad")
    try:
        modal.wait_for(state="visible", timeout=4000)
    except PWTimeout:
        return

    for _ in range(6):
        try:
            page.evaluate("""
              const m = document.getElementById('modalModalidad');
              if (!m) return;
              const norm = s => (s||'').replace(/\\s+/g,' ').trim().toLowerCase();
              const leafs = Array.from(m.querySelectorAll('*')).filter(el => el.children.length === 0);
              const node = leafs.find(el => {
                const t = norm(el.textContent);
                return t === 'persona física' || t === 'persona fisica';
              });
              if (node) {
                const clickable = node.closest('[onclick]') || node.closest('a,button') || node.closest('div') || node;
                clickable.click();
              }
            """)
        except Exception:
            pass

        try:
            modal.wait_for(state="hidden", timeout=1200)
            _cleanup_overlays(page)
            return
        except Exception:
            _cleanup_overlays(page)
            page.wait_for_timeout(250)

    # last resort: hide to unblock
    try:
        page.evaluate("""
          const m = document.getElementById("modalModalidad");
          if (m) { m.style.display="none"; m.classList.remove("in","show"); }
        """)
    except Exception:
        pass
    _cleanup_overlays(page)

def _auto_login_if_needed(page, user: str, password: str):
    page.goto(BASE_URL, wait_until="domcontentloaded")
    page.wait_for_timeout(300)

    if _is_logged_in(page):
        return

    _click_login_entry(page)
    page.wait_for_timeout(250)

    page.get_by_role("link", name=re.compile(LOGIN_TARGET_TEXT, re.I)).click(timeout=15000)
    page.wait_for_load_state("domcontentloaded")

    u = page.locator("#UserName")
    p = page.locator("#UserPassword")
    u.wait_for(state="visible", timeout=20000)
    p.wait_for(state="visible", timeout=20000)

    u.fill(user)
    p.fill(password)
    page.get_by_role("button", name=re.compile(r"^Ingresar$", re.I)).click()

    _ensure_profile_selected(page)

    marker = page.get_by_text("Consulta de datos públicos de expedientes", exact=False)
    try:
        marker.wait_for(timeout=8000)
    except PWTimeout:
        marker.wait_for(timeout=30000)

def _click_menu_consulta(page):
    _cleanup_overlays(page)
    page.get_by_text("Consulta de datos públicos de expedientes", exact=False).first.evaluate("el => el.click()")

def _select_circuito(page, circuito_text):
    label = page.locator("xpath=//*[normalize-space()='Circuito:']")
    label.wait_for(timeout=12000)
    ctrl = label.locator("xpath=following::*[self::div or self::span or self::input][1]")
    ctrl.click(force=True)
    page.keyboard.type(circuito_text, delay=25)
    page.keyboard.press("Enter")

def _wait_for_filter_modal(page):
    page.get_by_text(FILTER_TITLE, exact=False).wait_for(timeout=12000)

def _modal_root(page):
    m = page.locator("xpath=//*[contains(normalize-space(),'Filtro Expediente')]/ancestor::*[contains(@class,'modal')][1]")
    if m.count() == 0:
        m = page.locator("xpath=//*[contains(normalize-space(),'Filtro Expediente')]/ancestor::*[1]")
    return m.first

def _set_tipo_chosen(modal, page, tipo_text):
    chosen = modal.locator("#ddlTipoAsunto_chosen")
    if chosen.count() == 0:
        chosen = modal.locator("select#ddlTipoAsunto").locator("xpath=following-sibling::div[contains(@class,'chosen-container')][1]")
    chosen.first.wait_for(timeout=10000)
    chosen.first.click(force=True)
    search = chosen.first.locator("input[type='text']")
    if search.count() > 0:
        search.first.fill(tipo_text)
    else:
        page.keyboard.type(tipo_text, delay=25)
    page.keyboard.press("Enter")

def _fill_folio(modal, folio):
    inp = modal.get_by_placeholder("Ejemplo: 1/2026", exact=False)
    inp.wait_for(timeout=10000)
    inp.fill(folio)

def _click_buscar(modal):
    btn = modal.locator("button:has-text('Buscar'), a:has-text('Buscar')").first
    btn.wait_for(state="attached", timeout=10000)
    btn.evaluate("el => el.click()")

def _advertencia_visible_js(page) -> bool:
    try:
        return bool(page.evaluate("""
          (txt) => {
            const visible = (el) => {
              if (!el) return false;
              const s = getComputedStyle(el);
              if (!s) return false;
              if (s.display === 'none' || s.visibility === 'hidden' || Number(s.opacity||'1') === 0) return false;
              const r = el.getBoundingClientRect();
              return r.width > 0 && r.height > 0;
            };
            const m = Array.from(document.querySelectorAll('.modal'))
              .find(x => visible(x) && (x.innerText||'').includes(txt));
            return !!m;
          }
        """, NOT_FOUND_TEXT))
    except Exception:
        return False

def _dismiss_advertencia_js(page):
    if not _advertencia_visible_js(page):
        return False
    try:
        page.evaluate("""
          (txt) => {
            const visible = (el) => {
              if (!el) return false;
              const s = getComputedStyle(el);
              if (!s) return false;
              if (s.display === 'none' || s.visibility === 'hidden' || Number(s.opacity||'1') === 0) return false;
              const r = el.getBoundingClientRect();
              return r.width > 0 && r.height > 0;
            };
            const m = Array.from(document.querySelectorAll('.modal'))
              .find(x => visible(x) && (x.innerText||'').includes(txt));
            if (!m) return;
            const btn = Array.from(m.querySelectorAll('button,a'))
              .find(b => (b.textContent||'').includes('Aceptar'));
            btn?.click();
            document.querySelectorAll('.modal-backdrop').forEach(e => e.remove());
            document.body.classList.remove('modal-open');
            document.body.style.removeProperty('padding-right');
          }
        """, NOT_FOUND_TEXT)
    except Exception:
        pass
    page.wait_for_timeout(200)
    _cleanup_overlays(page)
    return True

def run(excel_path: str, user: str, password: str, circuito: str = CIRCUITO_TARGET,
        profile_dir: str = "pw_profile_pjf_multi", on_progress=None):
    tipos = read_folios_by_tipo_xlsx(excel_path)
    if not tipos:
        raise RuntimeError("No tipos/folios found. Headers must be in row 1; folios start row 2.")

    out_dir = Path(excel_path).expanduser().resolve().parent
    rows = []

    total = sum(len(v) for v in tipos.values())
    done = 0

    with sync_playwright() as p:
        context = p.chromium.launch_persistent_context(
            user_data_dir=str((Path.cwd() / profile_dir).resolve()),
            headless=False,
            ignore_https_errors=True,
        )
        page = context.pages[0] if context.pages else context.new_page()
        _setup_auto_dialog_accept(page)

        _auto_login_if_needed(page, user, password)
        _ensure_profile_selected(page)

        _click_menu_consulta(page)
        page.wait_for_timeout(300)

        _select_circuito(page, circuito)
        _wait_for_filter_modal(page)
        modal = _modal_root(page)

        try:
            for tipo, folios in tipos.items():
                _set_tipo_chosen(modal, page, tipo)

                for folio in folios:
                    done += 1
                    _close_extra_pages(context, page)
                    _dismiss_advertencia_js(page)

                    if page.get_by_text(FILTER_TITLE, exact=False).count() == 0:
                        _select_circuito(page, circuito)
                        _wait_for_filter_modal(page)
                        modal = _modal_root(page)
                        _set_tipo_chosen(modal, page, tipo)

                    found = False
                    status = "ERROR"
                    notes = ""

                    _fill_folio(modal, folio)

                    before_pages = list(context.pages)
                    before_count = len(before_pages)

                    _click_buscar(modal)

                    deadline = time.time() + 8.0
                    new_tab = None

                    while time.time() < deadline:
                        if _advertencia_visible_js(page):
                            _dismiss_advertencia_js(page)
                            found = False
                            status = "NOT_FOUND"
                            break

                        pages_now = list(context.pages)
                        if len(pages_now) > before_count:
                            for p2 in pages_now[::-1]:
                                if p2 not in before_pages and p2 is not page:
                                    new_tab = p2
                                    break
                            if new_tab:
                                break

                        time.sleep(0.15)

                    if new_tab:
                        try:
                            new_tab.wait_for_load_state("domcontentloaded", timeout=15000)
                        except Exception:
                            pass
                        try:
                            new_tab.close()
                        except Exception:
                            pass
                        _close_extra_pages(context, page)
                        found = True
                        status = "FOUND"

                    if status == "ERROR":
                        notes = "No visible Advertencia and no new tab within 8s."

                    row = {
                        "tipo": tipo,
                        "folio": folio,
                        "found": found,
                        "status": status,
                        "checked_at": datetime.now().isoformat(timespec="seconds"),
                        "notes": notes,
                    }
                    rows.append(row)

                    if on_progress:
                        on_progress(done, total, row)

        finally:
            try:
                context.close()
            except Exception:
                pass

    out_full, out_missing = _write_outputs(rows, out_dir)
    return out_full, out_missing
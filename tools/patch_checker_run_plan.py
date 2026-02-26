from pathlib import Path
import re

p = Path("pjf_checker.py")
s = p.read_text(encoding="utf-8")

# Ensure ORGANO_TARGET_VALUE exists
if "ORGANO_TARGET_VALUE" not in s:
    s = 'ORGANO_TARGET_VALUE = "3457"  # Juzgado Octavo...\\n' + s

# Only add once
if "def run_plan(" in s:
    print("run_plan() already exists. No change.")
    raise SystemExit(0)

insert = r'''
def _force_organo_octavo(modal, page):
    # ddlOrgano is hidden by Chosen, so set via JS
    sel = modal.locator("#ddlOrgano").first
    if sel.count() == 0:
        return False
    sel.evaluate("(el, v) => { el.value=v; el.dispatchEvent(new Event('change', {bubbles:true})); }", ORGANO_TARGET_VALUE)
    page.wait_for_timeout(250)
    try:
        page.evaluate("() => { const el=document.querySelector('#ddlOrgano'); try { if (window.jQuery && el) window.jQuery(el).trigger('chosen:updated'); } catch(e) {} }")
    except Exception:
        pass
    return True


def run_plan(*, plan, expected_dates, excel_label, user, password, out_dir, on_progress=None):
    # plan: {tipo: [folio,...]}
    # expected_dates: {(tipo, folio): "YYYY-MM-DD"}  (optional)

    cases = []
    for tipo, folios in plan.items():
        for f in folios:
            cases.append((tipo, f, expected_dates.get((tipo, f))))

    from datetime import datetime
    import time
    from playwright.sync_api import sync_playwright

    rows = []
    total = len(cases)
    done = 0

    with sync_playwright() as pwp:
        context = pwp.chromium.launch_persistent_context(
            user_data_dir="pw_profile_pjf_batch",
            headless=False,
            ignore_https_errors=True,
        )
        page = context.pages[0] if context.pages else context.new_page()

        if "auto_login_if_needed" in globals():
            auto_login_if_needed(page, user, password)
        else:
            raise RuntimeError("auto_login_if_needed() not found in pjf_checker.py")

        page.get_by_text("Consulta de datos públicos de expedientes", exact=False).click()
        page.wait_for_load_state("domcontentloaded")

        if "select_circuito" in globals():
            select_circuito(page, CIRCUITO_TARGET)
        else:
            raise RuntimeError("select_circuito() not found in pjf_checker.py")

        if "wait_for_filter_modal" in globals():
            wait_for_filter_modal(page)
        else:
            raise RuntimeError("wait_for_filter_modal() not found in pjf_checker.py")

        # Grab visible modal robustly
        modal = page.locator("div.modal:visible").filter(has_text=FILTER_TITLE).first

        _force_organo_octavo(modal, page)

        tipo_sel = modal.locator("#ddlTipoAsunto").first
        tipo_opts = tipo_sel.evaluate("el => Array.from(el.options).map(o => (o.textContent||'').trim())") if tipo_sel.count() else []

        def norm(x):
            x = (x or "").lower()
            x = x.replace("á","a").replace("é","e").replace("í","i").replace("ó","o").replace("ú","u").replace("ü","u")
            return " ".join(x.split())

        def pick_tipo(excel_tipo: str):
            et = norm(excel_tipo)
            for t in tipo_opts:
                if norm(t) == et:
                    return t
            for t in tipo_opts:
                if et and et in norm(t):
                    return t
            return excel_tipo

        for tipo, folio, expected_iso in cases:
            done += 1
            status = "ERROR"
            notes = ""
            found = False

            try:
                # ensure modal exists
                if page.get_by_text(FILTER_TITLE, exact=False).count() == 0:
                    select_circuito(page, CIRCUITO_TARGET)
                    wait_for_filter_modal(page)
                    modal = page.locator("div.modal:visible").filter(has_text=FILTER_TITLE).first

                _force_organo_octavo(modal, page)

                chosen_tipo = pick_tipo(tipo)
                if "set_tipo_chosen" in globals():
                    set_tipo_chosen(modal, page, chosen_tipo)
                else:
                    modal.locator("#ddlTipoAsunto").select_option(label=chosen_tipo)

                if "fill_folio" in globals():
                    fill_folio(modal, folio)
                else:
                    modal.get_by_placeholder("Ejemplo: 1/2026", exact=False).fill(folio)

                before_pages = list(context.pages)
                before_count = len(before_pages)

                if "click_buscar" in globals():
                    click_buscar(modal)
                else:
                    modal.locator("button:has-text('Buscar')").first.click()

                deadline = time.time() + 12.0
                new_tab = None

                while time.time() < deadline:
                    if page.locator(f"text={NOT_FOUND_TEXT}").count() > 0:
                        status = "NOT_FOUND"
                        found = False
                        break

                    pages_now = list(context.pages)
                    if len(pages_now) > before_count:
                        for p2 in pages_now[::-1]:
                            if p2 not in before_pages:
                                new_tab = p2
                                break
                        if new_tab:
                            break

                    time.sleep(0.2)

                if new_tab:
                    try:
                        new_tab.wait_for_load_state("domcontentloaded", timeout=15000)
                    except Exception:
                        pass
                    found = True
                    status = "FOUND"
                    try:
                        new_tab.close()
                    except Exception:
                        pass
                elif status != "NOT_FOUND":
                    status = "ERROR"
                    notes = "No advertencia and no new tab detected."

            except Exception as e:
                status = "ERROR"
                notes = f"{type(e).__name__}: {e}"

            row = {
                "tipo": tipo,
                "folio": folio,
                "found": found,
                "status": status,
                "expected_fecha_iso": expected_iso,
                "checked_at": datetime.now().isoformat(timespec="seconds"),
                "notes": notes,
            }
            rows.append(row)

            if on_progress:
                on_progress(done, total, row)

        try:
            context.close()
        except Exception:
            pass

    # If existing write_outputs exists, prefer it
    if "write_outputs" in globals():
        out_full = str(Path(out_dir) / "Folios_results.xlsx")
        out_missing = str(Path(out_dir) / "Folios_missing.xlsx")
        write_outputs(rows, out_full=out_full, out_missing=out_missing)
        return out_full, out_missing

    # Fallback writer
    import openpyxl
    out_full = Path(out_dir) / "Folios_results.xlsx"
    out_missing = Path(out_dir) / "Folios_missing.xlsx"

    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "Results"
    ws.append(["Excel", "Tipo", "Folio", "Status", "ExpectedFechaISO", "CheckedAt", "Notes"])
    for r in rows:
        ws.append([excel_label, r["tipo"], r["folio"], r["status"], r.get("expected_fecha_iso"), r["checked_at"], r.get("notes") or ""])
    wb.save(out_full)

    wb2 = openpyxl.Workbook()
    ws2 = wb2.active
    ws2.title = "Missing"
    ws2.append(["Tipo", "Folio"])
    for r in rows:
        if r["status"] == "NOT_FOUND":
            ws2.append([r["tipo"], r["folio"]])
    wb2.save(out_missing)

    return str(out_full), str(out_missing)
'''

# Insert before def run(...)
s = re.sub(r"^def run\(", insert + "\n\ndef run(", s, flags=re.M)

p.write_text(s, encoding="utf-8")
print("Patched pjf_checker.py: added run_plan() + forces ddlOrgano=3457.")

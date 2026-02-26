# PJF Folio Checker (Multi-Tipo)

Checks which folios exist in the PJF public expediente search, grouped by **Tipo de Expediente**, using an Excel file.

## Quick start (no Git needed)
1) Open the repo on GitHub
2) Click **Code → Download ZIP**
3) Unzip the folder
4) Run:
   - **Windows:** double-click `run.bat`
   - **macOS:** right-click `run.command` → **Open**

## Excel format
- Row 1: each column header is a **Tipo de Expediente** label (e.g. `Amparo Indirecto`)
- Row 2..N: folios like `123/2025`

## Output files
Saved in the **same folder as your Excel**:
- `Folios_results.xlsx`
- `Folios_missing.xlsx`

## Notes
- First run may take longer (installs dependencies + browser).
- Drag & drop paths are supported (macOS Terminal paths with `\ ` are handled).

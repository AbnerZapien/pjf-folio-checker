import os
import sys
import re
import getpass
import platform
import subprocess
from pathlib import Path

from rich.console import Console
from rich.panel import Panel
from rich.prompt import Prompt
from rich.table import Table
from rich.progress import Progress, BarColumn, TextColumn, TimeElapsedColumn, TimeRemainingColumn

import pjf_checker

console = Console()

def normalize_path_input(raw: str) -> str:
    s = raw.strip().strip('"').strip("'")
    # If it's a mac/Linux path, unescape Terminal drag&drop sequences (\ , \(, \), etc.)
    if s.startswith('/'):
        s = re.sub(r"\\([ ()\[\]{}&;\"'#$!])", r"\1", s)
    return s


def open_folder(path: Path):
    try:
        if platform.system() == "Windows":
            os.startfile(str(path))  # type: ignore[attr-defined]
        elif platform.system() == "Darwin":
            subprocess.run(["open", str(path)], check=False)
        else:
            subprocess.run(["xdg-open", str(path)], check=False)
    except Exception:
        pass

def main():
    console.print(Panel.fit("[bold cyan]PJF Folio Checker[/bold cyan]\n[dim]Multi-tipo scan from Excel columns[/dim]"))

    console.print("\n[bold]Step 1[/bold] — Excel file")
    console.print("[dim]Tip: drag & drop the file into this terminal and press Enter.[/dim]")
    excel_path = normalize_path_input(Prompt.ask("Excel file path"))
    p = Path(excel_path).expanduser()
    if not p.exists():
        console.print(f"[bold red]File not found:[/bold red] {p}")
        sys.exit(1)

    console.print("\n[bold]Step 2[/bold] — Portal credentials")
    user = os.environ.get("PJF_USER") or Prompt.ask("Portal user").strip()
    password = os.environ.get("PJF_PASS") or getpass.getpass("Portal password: ")

    out_dir = p.resolve().parent
    console.print(f"\n[bold]Outputs will be saved to:[/bold] {out_dir}")

    # Pre-read tipos to show what will be checked
    tipos = pjf_checker.read_folios_by_tipo_xlsx(str(p))
    if not tipos:
        console.print("[bold red]No columns detected.[/bold red] Make sure headers are in row 1 and folios start in row 2.")
        sys.exit(1)

    t = Table(title="Plan (Excel Columns)")
    t.add_column("Tipo", style="cyan")
    t.add_column("Folios", justify="right")
    total = 0
    for tipo, folios in tipos.items():
        t.add_row(tipo, str(len(folios)))
        total += len(folios)
    console.print(t)

    console.print("\n[bold]Step 3[/bold] — Running (browser will open)")

    counts = {}  # tipo -> dict(found, not_found, error)

    def on_progress(done, total, row):
        tipo = row["tipo"]
        counts.setdefault(tipo, {"FOUND": 0, "NOT_FOUND": 0, "ERROR": 0})
        counts[tipo][row["status"]] += 1

        prog.update(task_id, completed=done)
        prog.update(status_id, description=f"[dim]{tipo}[/dim]  [bold]{row['folio']}[/bold] → {row['status']}")

    with Progress(
        TextColumn("[bold]{task.description}"),
        BarColumn(),
        TextColumn("{task.completed}/{task.total}"),
        TimeElapsedColumn(),
        TimeRemainingColumn(),
        console=console,
    ) as prog:
        task_id = prog.add_task("Checking folios", total=total)
        status_id = prog.add_task("Status", total=1)
        try:
            out_full, out_missing = pjf_checker.run(
                excel_path=str(p),
                user=user,
                password=password,
                profile_dir="pw_profile_pjf_multi",
                on_progress=on_progress,
            )
        except KeyboardInterrupt:
            console.print("\n[bold yellow]Interrupted.[/bold yellow]")
            sys.exit(1)

    console.print("\n[bold green]Done.[/bold green]")

    summary = Table(title="Summary by Tipo")
    summary.add_column("Tipo", style="cyan")
    summary.add_column("FOUND", justify="right")
    summary.add_column("NOT_FOUND", justify="right")
    summary.add_column("ERROR", justify="right")
    for tipo, c in counts.items():
        summary.add_row(tipo, str(c["FOUND"]), str(c["NOT_FOUND"]), str(c["ERROR"]))
    console.print(summary)

    console.print(f"\n[bold]Results:[/bold]\n- {out_full}\n- {out_missing}")
    open_folder(out_dir)

if __name__ == "__main__":
    main()
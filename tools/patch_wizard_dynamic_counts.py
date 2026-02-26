from pathlib import Path
import re

p = Path("pjf_wizard.py")
s = p.read_text(encoding="utf-8")

# Replace counts default and increment to be dynamic
# Old:
# counts = defaultdict(lambda: {"FOUND": 0, "NOT_FOUND": 0, "ERROR": 0})
# counts[row["tipo"]][st] += 1
s = re.sub(
    r'counts\s*=\s*defaultdict\(lambda:\s*\{"FOUND":\s*0,\s*"NOT_FOUND":\s*0,\s*"ERROR":\s*0\}\)\s*',
    'counts = defaultdict(lambda: {})\n',
    s
)

s = re.sub(
    r'counts\[row\["tipo"\]\]\[st\]\s*\+=\s*1',
    'counts[row["tipo"]][st] = counts[row["tipo"]].get(st, 0) + 1',
    s
)

# Replace the fixed summary table to include common statuses, but safely with .get
# We'll show: FOUND_MATCH, FOUND_MISMATCH, FOUND_NO_FECHA, FOUND, NOT_FOUND, ERROR
s = re.sub(
    r'summary\s*=\s*Table\(title="Summary by Tipo"\)[\s\S]*?console\.print\(summary\)',
    '''summary = Table(title="Summary by Tipo")
    summary.add_column("Tipo", style="cyan")
    for col in ["FOUND_MATCH","FOUND_MISMATCH","FOUND_NO_FECHA","FOUND","NOT_FOUND","ERROR"]:
        summary.add_column(col, justify="right")

    for tipo in sorted(counts.keys()):
        c = counts[tipo]
        summary.add_row(
            tipo,
            str(c.get("FOUND_MATCH", 0)),
            str(c.get("FOUND_MISMATCH", 0)),
            str(c.get("FOUND_NO_FECHA", 0)),
            str(c.get("FOUND", 0)),
            str(c.get("NOT_FOUND", 0)),
            str(c.get("ERROR", 0)),
        )
    console.print(summary)''',
    s,
    flags=re.M
)

p.write_text(s, encoding="utf-8")
print("Patched pjf_wizard.py: dynamic status counts + expanded summary columns.")

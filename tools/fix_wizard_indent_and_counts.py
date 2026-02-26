from pathlib import Path
import re

p = Path("pjf_wizard.py")
src = p.read_text(encoding="utf-8")

# Backup
bak = p.with_suffix(".py.bak")
bak.write_text(src, encoding="utf-8")
print("Backup written:", bak)

# 1) Normalize tabs to 4 spaces to avoid indentation mismatch
s = src.replace("\t", "    ")

# 2) Make counts dynamic (prevents KeyError on FOUND_NO_FECHA, FOUND_MATCH, etc.)
s = re.sub(
    r'counts\s*=\s*defaultdict\(\s*lambda:\s*\{"FOUND":\s*0,\s*"NOT_FOUND":\s*0,\s*"ERROR":\s*0\}\s*\)',
    'counts = defaultdict(lambda: {})',
    s
)
s = re.sub(
    r'counts\[row\["tipo"\]\]\[st\]\s*\+=\s*1',
    'counts[row["tipo"]][st] = counts[row["tipo"]].get(st, 0) + 1',
    s
)

# 3) Replace the Summary by Tipo block safely, preserving file indentation
# Find from 'summary = Table(title="Summary by Tipo")' up to 'console.print(summary)'
pat = re.compile(
    r'^(?P<indent>[ ]*)summary\s*=\s*Table\(title="Summary by Tipo"\)[\s\S]*?^(?P=indent)console\.print\(summary\)\s*$',
    re.M
)
m = pat.search(s)
if not m:
    raise SystemExit("Could not locate the Summary by Tipo block to fix. (No changes applied beyond counts normalization.)")

indent = m.group("indent")

new_block = (
    f'{indent}summary = Table(title="Summary by Tipo")\n'
    f'{indent}summary.add_column("Tipo", style="cyan")\n'
    f'{indent}for col in ["FOUND_MATCH","FOUND_MISMATCH","FOUND_NO_FECHA","FOUND","NOT_FOUND","ERROR"]:\n'
    f'{indent}    summary.add_column(col, justify="right")\n'
    f'\n'
    f'{indent}for tipo in sorted(counts.keys()):\n'
    f'{indent}    c = counts[tipo]\n'
    f'{indent}    summary.add_row(\n'
    f'{indent}        tipo,\n'
    f'{indent}        str(c.get("FOUND_MATCH", 0)),\n'
    f'{indent}        str(c.get("FOUND_MISMATCH", 0)),\n'
    f'{indent}        str(c.get("FOUND_NO_FECHA", 0)),\n'
    f'{indent}        str(c.get("FOUND", 0)),\n'
    f'{indent}        str(c.get("NOT_FOUND", 0)),\n'
    f'{indent}        str(c.get("ERROR", 0)),\n'
    f'{indent}    )\n'
    f'{indent}console.print(summary)\n'
)

s = pat.sub(new_block.rstrip(), s, count=1)

p.write_text(s, encoding="utf-8")
print("Patched pjf_wizard.py (counts + summary indentation fixed).")

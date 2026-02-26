from pathlib import Path

p = Path("pjf_checker.py")
s = p.read_text(encoding="utf-8")

bak = p.with_suffix(".py.bak_fecha_regex")
bak.write_text(s, encoding="utf-8")
print("Backup:", bak)

# Fix the double-escaped pattern inside run_plan
s2 = s.replace(r'DATE = _re.compile(r"(\\d{2})/(\\d{2})/(\\d{4})")',
               r'DATE = _re.compile(r"(\d{2})/(\d{2})/(\d{4})")')

# Also handle single-quote variant if present
s2 = s2.replace(r"DATE = _re.compile(r'(\\d{2})/(\\d{2})/(\\d{4})')",
                r"DATE = _re.compile(r'(\d{2})/(\d{2})/(\d{4})')")

if s2 == s:
    raise SystemExit("Did not find the double-escaped DATE regex to patch.")

p.write_text(s2, encoding="utf-8")
print("Patched DATE regex (\\d -> \d).")

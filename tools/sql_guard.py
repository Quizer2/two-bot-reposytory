import sys, re
from pathlib import Path

root = Path(__file__).resolve().parents[1]
bad = []
warn = []
for p in root.rglob("*.py"):
    rel = p.relative_to(root).as_posix()
    if rel.startswith("tests/"):
        continue
    if rel == "tools/sql_guard.py":
        continue
    s = p.read_text(encoding="utf-8", errors="ignore")
    # Detect non-parameterized SQL usage: f-strings or string .format within SQL execution calls
    if re.search(r"execute\(\s*f['\"]", s):
        bad.append((rel, "execute(f-string)"))
    if re.search(r"executemany\(\s*f['\"]", s):
        bad.append((rel, "executemany(f-string)"))
    if re.search(r"execute\(\s*[^)]*?\.\s*format\(", s, flags=re.DOTALL):
        bad.append((rel, "execute(string.format)"))
    if re.search(r"executemany\(\s*[^)]*?\.\s*format\(", s, flags=re.DOTALL):
        bad.append((rel, "executemany(string.format)"))
    # Detect %-operator formatting inside execute/executemany (e.g., '...'%var)
    if re.search(r"execute\(\s*['\"][^'\"]*['\"]\s*%", s, flags=re.DOTALL):
        bad.append((rel, "execute(%-format string)"))
    if re.search(r"executemany\(\s*['\"][^'\"]*['\"]\s*%", s, flags=re.DOTALL):
        bad.append((rel, "executemany(%-format string)"))
    # Detect dynamic SQL concatenation inside execute/executemany calls (review recommended)
    if re.search(r"execute\(\s*[^)]*?\+[^)]*?\)", s, flags=re.DOTALL):
        warn.append((rel, "execute(string concatenation)"))
    if re.search(r"executemany\(\s*[^)]*?\+[^)]*?\)", s, flags=re.DOTALL):
        warn.append((rel, "executemany(string concatenation)"))

    # Detect building SQL in variables then passing to execute/executemany
    # Flag f-strings assigned to 'sql' or 'query' and later used in execute/executemany
    assigned_fvars = re.findall(r"\b(sql|query)\s*=\s*f['\"]", s)
    for var in set(assigned_fvars):
        if re.search(rf"\bexecute\(\s*{var}\b", s) or re.search(rf"\bexecutemany\(\s*{var}\b", s):
            bad.append((rel, f"execute({var} f-string)"))
    # Flag string.format assigned to 'sql' or 'query'
    assigned_fmt_vars = re.findall(r"\b(sql|query)\s*=\s*[^=]*?\.format\(", s, flags=re.DOTALL)
    for var in set(assigned_fmt_vars):
        if re.search(rf"\bexecute\(\s*{var}\b", s) or re.search(rf"\bexecutemany\(\s*{var}\b", s):
            bad.append((rel, f"execute({var} .format)"))
    # Warn on '+' concatenation assigned to 'sql' or 'query' then used
    assigned_plus_vars = re.findall(r"\b(sql|query)\s*=\s*[^\n]*\+[^\n]*", s)
    for var in set(assigned_plus_vars):
        name = var if isinstance(var, str) else var[0]
        if re.search(rf"\bexecute\(\s*{name}\b", s) or re.search(rf"\bexecutemany\(\s*{name}\b", s):
            warn.append((rel, f"execute({name} with '+')"))

if bad:
    print("[SQL GUARD] Found non-parameterized SQL patterns:")
    for rel, kind in bad:
        print(f" - {rel}: {kind}")
    sys.exit(1)

if warn:
    print("[SQL GUARD] WARNING: Found dynamic SQL concatenations (review recommended):")
    for rel, kind in warn:
        print(f" - {rel}: {kind}")

print("[SQL GUARD] OK")

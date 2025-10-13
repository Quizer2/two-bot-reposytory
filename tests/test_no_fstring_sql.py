import re, pathlib

def test_no_fstring_sql_patterns():
    root = pathlib.Path(__file__).resolve().parents[1]
    offenders = []
    for p in root.rglob('*.py'):
        if 'ui/' in p.as_posix() or 'tests/' in p.as_posix():
            continue
        s = p.read_text(encoding='utf-8', errors='ignore')
        # naive guard: execute(f"...{var}...")
        if re.search(r"execute\(\s*f['\"]", s):
            offenders.append(p.as_posix())
        if '.format(' in s and 'execute(' in s:
            offenders.append(p.as_posix())
    assert not offenders, f"SQL string formatting found: {offenders[:10]}"


import sqlite3
import re

def ensure_column(conn: sqlite3.Connection, table: str, column: str, decl: str):
    # Prosta walidacja nazw identyfikatorów (tabela/kolumna)
    ident_re = re.compile(r'^[A-Za-z_][A-Za-z0-9_]*$')
    if not ident_re.match(table) or not ident_re.match(column):
        raise ValueError("Invalid table/column name")
    # PRAGMA bez f-stringa
    sql_pragma = "PRAGMA table_info(" + table + ")"
    cur = conn.execute(sql_pragma)
    cols = [r[1] for r in cur.fetchall()]
    if column not in cols:
        # ALTER TABLE bez f-stringa
        sql_alter = "ALTER TABLE " + table + " ADD COLUMN " + column + " " + decl
        conn.execute(sql_alter)
        conn.commit()

# --- Centralne helpery SQL (bezpieczna budowa klauzul) ---
_ident_re = re.compile(r'^[A-Za-z_][A-Za-z0-9_]*$')

def validate_identifiers(*names: str) -> None:
    """Waliduj nazwy identyfikatorów SQL (tabele/kolumny)."""
    for n in names:
        if not isinstance(n, str) or not _ident_re.match(n):
            raise ValueError(f"Invalid SQL identifier: {n}")

def build_where_clause(filters: dict, allowed_columns: set | None = None) -> tuple[str, list]:
    """Zbuduj bezpieczną klauzulę WHERE i listę parametrów.
    - Waliduje klucze względem allowed_columns (jeśli podane)
    - Zwraca (clause, params), gdzie clause to '1=1' lub połączone 'col = ?'
    """
    if not filters:
        return "1=1", []
    clauses: list[str] = []
    params: list = []
    for key, val in filters.items():
        if allowed_columns is not None and key not in allowed_columns:
            raise ValueError(f"Column not allowed in WHERE: {key}")
        validate_identifiers(key)
        clauses.append(key + " = ?")
        params.append(val)
    return " AND ".join(clauses), params

def build_set_clause(updates: dict, allowed_columns: set | None = None) -> tuple[str, list]:
    """Zbuduj bezpieczną klauzulę SET do UPDATE wraz z parametrami."""
    if not updates:
        raise ValueError("No updates provided")
    sets: list[str] = []
    params: list = []
    for key, val in updates.items():
        if allowed_columns is not None and key not in allowed_columns:
            raise ValueError(f"Column not allowed in SET: {key}")
        validate_identifiers(key)
        sets.append(key + " = ?")
        params.append(val)
    return ", ".join(sets), params

# Uwaga: Helpery budują tylko tekst SQL i parametry; wartości ZAWSZE muszą być
# przekazywane jako parametry do execute/ executemany. Nigdy nie używaj f-stringów
# w zapytaniach SQL. Korzystaj z tych helperów w miejscach, gdzie powstaje dynamiczny
# WHERE/SET.

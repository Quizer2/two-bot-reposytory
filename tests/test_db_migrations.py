import sqlite3
import tempfile
import os
from pathlib import Path

from utils.db_migrations import apply_migrations


def test_positions_constraints_migration_adds_checks_and_filters_invalid_rows():
    # Utwórz tymczasową bazę bez nowych CHECK constraintów
    tmp = tempfile.NamedTemporaryFile(delete=False, suffix='.db')
    tmp.close()
    db_path = tmp.name

    con = sqlite3.connect(db_path)
    try:
        con.execute('PRAGMA foreign_keys=OFF')
        con.execute('''
          CREATE TABLE positions (
              id INTEGER PRIMARY KEY AUTOINCREMENT,
              bot_id INTEGER NOT NULL,
              symbol TEXT NOT NULL,
              side TEXT NOT NULL CHECK (side IN ('buy','sell')),
              size REAL NOT NULL CHECK (size > 0),
              entry_price REAL NOT NULL,
              current_price REAL,
              unrealized_pnl REAL DEFAULT 0.0,
              realized_pnl REAL DEFAULT 0.0,
              stop_loss_price REAL,
              take_profit_price REAL,
              trailing_stop_price REAL,
              opened_at DATETIME DEFAULT CURRENT_TIMESTAMP,
              closed_at DATETIME,
              status TEXT DEFAULT 'open' CHECK (status IN ('open','closed'))
          )
        ''')
        # Rekord poprawny wg nowych reguł
        con.execute(
            'INSERT INTO positions (bot_id, symbol, side, size, entry_price, status) VALUES (?,?,?,?,?,?)',
            (1, 'BTC/USDT', 'buy', 1.0, 100.0, 'open')
        )
        # Rekord z entry_price < 0 (do odrzucenia przez migrację)
        con.execute(
            'INSERT INTO positions (bot_id, symbol, side, size, entry_price, status) VALUES (?,?,?,?,?,?)',
            (1, 'ETH/USDT', 'sell', 1.0, -5.0, 'open')
        )
        # Rekord z closed_at != NULL gdy status='open' (do odrzucenia przez migrację)
        con.execute(
            "INSERT INTO positions (bot_id, symbol, side, size, entry_price, status, closed_at) VALUES (?,?,?,?,?,?,CURRENT_TIMESTAMP)",
            (1, 'XRP/USDT', 'buy', 1.0, 10.0, 'open')
        )
        con.commit()
    finally:
        con.close()

    # Zastosuj migracje
    apply_migrations(Path(db_path))

    # Zweryfikuj wynik
    con = sqlite3.connect(db_path)
    try:
        cur = con.execute("SELECT sql FROM sqlite_master WHERE type='table' AND name='positions'")
        row = cur.fetchone()
        assert row is not None
        sql = row[0] or ''
        assert "CHECK (entry_price >= 0)" in sql
        assert "CHECK (status = 'closed' OR closed_at IS NULL)" in sql

        cur = con.execute("SELECT COUNT(*) FROM positions")
        cnt = cur.fetchone()[0]
        assert cnt == 1

        cur = con.execute("SELECT symbol, entry_price, status, closed_at FROM positions")
        sym, ep, st, closed_at = cur.fetchone()
        assert sym == 'BTC/USDT'
        assert ep == 100.0
        assert st == 'open'
        assert closed_at is None
    finally:
        con.close()
        os.unlink(db_path)
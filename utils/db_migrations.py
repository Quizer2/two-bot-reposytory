import sqlite3
from pathlib import Path
from utils.logger import get_logger, LogType
logger = get_logger(__name__, LogType.SECURITY)

def _has_positions_constraints(con: sqlite3.Connection) -> bool:
    cur = con.execute("SELECT sql FROM sqlite_master WHERE type='table' AND name='positions'")
    row = cur.fetchone()
    if not row:
        # Brak tabeli -> brak potrzeby migracji w tym kroku
        return True
    sql = row[0] or ''
    checks = [
        "CHECK (side IN ('buy', 'sell'))",
        "CHECK (status IN ('open', 'closed'))",
        "CHECK (size > 0)",
        "CHECK (entry_price >= 0)",
        "CHECK (status = 'closed' OR closed_at IS NULL)",
    ]
    return all(s in sql for s in checks)


def _migrate_positions_constraints(con: sqlite3.Connection):
    # Tworzymy nową tabelę z pełnym zestawem CHECK i przenosimy poprawne dane
    logger.info("Starting positions constraints migration")
    con.execute('BEGIN')
    try:
        con.execute('''
            CREATE TABLE positions_new (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                bot_id INTEGER NOT NULL,
                symbol TEXT NOT NULL,
                side TEXT NOT NULL CHECK (side IN ('buy', 'sell')),
                size REAL NOT NULL CHECK (size > 0),
                entry_price REAL NOT NULL CHECK (entry_price >= 0),
                current_price REAL,
                unrealized_pnl REAL DEFAULT 0.0,
                realized_pnl REAL DEFAULT 0.0,
                stop_loss_price REAL,
                take_profit_price REAL,
                trailing_stop_price REAL,
                opened_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                closed_at DATETIME,
                status TEXT DEFAULT 'open' CHECK (status IN ('open', 'closed')),
                CHECK (status = 'closed' OR closed_at IS NULL),
                FOREIGN KEY (bot_id) REFERENCES bots (id) ON DELETE CASCADE
            )
        ''')
        con.execute('''
            INSERT INTO positions_new (
                id, bot_id, symbol, side, size, entry_price, current_price, unrealized_pnl,
                realized_pnl, stop_loss_price, take_profit_price, trailing_stop_price,
                opened_at, closed_at, status
            )
            SELECT 
                id, bot_id, symbol, side, size, entry_price, current_price, unrealized_pnl,
                realized_pnl, stop_loss_price, take_profit_price, trailing_stop_price,
                opened_at, closed_at, status
            FROM positions
            WHERE side IN ('buy','sell') AND status IN ('open','closed') AND size > 0 AND entry_price >= 0 AND (status = 'closed' OR closed_at IS NULL)
        ''')
        con.execute('DROP TABLE positions')
        con.execute('ALTER TABLE positions_new RENAME TO positions')
        con.commit()
        logger.info("Positions constraints migration completed successfully")
    except Exception as e:
        logger.error(f"Migration failed, attempting rollback: {e}", exc_info=True)
        try:
            con.rollback()
            logger.info("Rollback successful after migration failure")
        except Exception as re:
            logger.error(f"Rollback failed: {re}", exc_info=True)
        raise


def apply_migrations(db_path: Path):
    logger.info(f"Applying migrations on {db_path}")
    con = sqlite3.connect(db_path)
    try:
        # meta tabela
        con.execute("CREATE TABLE IF NOT EXISTS meta (key TEXT PRIMARY KEY, value TEXT)")
        cur = con.execute("SELECT value FROM meta WHERE key='schema_version'")
        row = cur.fetchone()
        ver = int(row[0]) if row else 0

        # v1 - przykładowa migracja (pozostawiamy dla kompatybilności)
        if ver < 1:
            con.execute("CREATE TABLE IF NOT EXISTS healthcheck (ts INTEGER, note TEXT)")
            ver = 1

        # v2 - ujednolicenie CHECK constraints dla positions
        if not _has_positions_constraints(con):
            _migrate_positions_constraints(con)
            ver = max(ver, 2)

        con.execute("INSERT OR REPLACE INTO meta(key, value) VALUES ('schema_version', ?)", (str(ver),))
        con.commit()
        logger.info(f"Migrations applied. Current schema_version={ver}")
    except Exception as e:
        logger.error(f"Error applying migrations: {e}", exc_info=True)
        try:
            con.rollback()
            logger.info("Rollback successful during apply_migrations")
        except Exception as re:
            logger.error(f"Rollback failed during apply_migrations: {re}", exc_info=True)
        raise
    finally:
        con.close()
        logger.debug("Database connection closed after migrations")

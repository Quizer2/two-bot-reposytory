
import sqlite3, time
import logging
from pathlib import Path
from . import runtime_metrics as rt

logger = logging.getLogger(__name__)

DB = Path(__file__).resolve().parents[1] / "data" / "metrics.db"
DB.parent.mkdir(parents=True, exist_ok=True)


def _connect(db_path: Path | str | None = None) -> sqlite3.Connection:
    path = db_path or DB
    con = sqlite3.connect(path, timeout=30.0)
    # SQLite performance and concurrency pragmas
    con.execute("PRAGMA journal_mode=WAL")
    con.execute("PRAGMA synchronous=NORMAL")
    con.execute("PRAGMA busy_timeout=3000")
    return con


def _init(con: sqlite3.Connection):
    con.execute("CREATE TABLE IF NOT EXISTS equity (ts REAL, value REAL)")
    con.execute("CREATE INDEX IF NOT EXISTS ix_equity_ts ON equity(ts)")
    con.execute("CREATE TABLE IF NOT EXISTS equity_bot (ts REAL, bot TEXT, value REAL)")
    con.execute("CREATE INDEX IF NOT EXISTS ix_equity_bot ON equity_bot(bot, ts)")
    con.execute("CREATE TABLE IF NOT EXISTS equity_strategy (ts REAL, strategy TEXT, value REAL)")
    con.execute("CREATE INDEX IF NOT EXISTS ix_equity_strategy ON equity_strategy(strategy, ts)")
    con.execute("CREATE TABLE IF NOT EXISTS latency (ts REAL, p50 REAL, p95 REAL)")
    con.execute("CREATE INDEX IF NOT EXISTS ix_latency_ts ON latency(ts)")
    con.commit()


def _p(lat: list[float], q: int) -> float:
    if not lat:
        return 0.0
    lat = sorted(lat)
    k = int(round((q / 100.0) * (len(lat) - 1)))
    return float(lat[k])


def save_snapshot(max_retries: int = 3, retry_sleep_s: float = 0.2) -> bool:
    """Persist current runtime metrics snapshot to SQLite with simple retries.

    Returns True on success, False otherwise.
    """
    for attempt in range(max_retries):
        con = None
        try:
            con = _connect()
            _init(con)
            snap = rt.snapshot()
            eq = snap.get("equity_curve", [])
            if eq:
                ts, val = eq[-1]
                con.execute("INSERT INTO equity(ts,value) VALUES(?,?)", (ts, val))
            ebot = snap.get("equity_curve_per_bot", {}) or {}
            for b, seq in ebot.items():
                if seq:
                    ts, val = seq[-1]
                    con.execute("INSERT INTO equity_bot(ts,bot,value) VALUES(?,?,?)", (ts, b, val))
            estr = snap.get("equity_curve_per_strategy", {}) or {}
            for s, seq in estr.items():
                if seq:
                    ts, val = seq[-1]
                    con.execute("INSERT INTO equity_strategy(ts,strategy,value) VALUES(?,?,?)", (ts, s, val))
            lat = snap.get("http_latency_ms", [])
            if lat:
                con.execute(
                    "INSERT INTO latency(ts,p50,p95) VALUES(?,?,?)",
                    (time.time(), _p(lat, 50), _p(lat, 95)),
                )
            con.commit()
            return True
        except sqlite3.OperationalError as e:
            # Retry on database lock or transient I/O error
            msg = str(e).lower()
            if ("locked" in msg or "busy" in msg or "database is locked" in msg) and attempt < max_retries - 1:
                time.sleep(retry_sleep_s * (attempt + 1))
                continue
            logger.warning(f"save_snapshot failed: {e}")
            return False
        except Exception as e:
            logger.error(f"Unexpected error in save_snapshot: {e}")
            return False
        finally:
            if con:
                try:
                    con.close()
                except Exception:
                    pass


# Convenience function for tests and one-shot persistence

def snapshot_now() -> bool:
    return save_snapshot()

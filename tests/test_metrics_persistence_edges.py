import sqlite3
import time
from pathlib import Path

import pytest

from utils import metrics_persistence as mp
from utils import runtime_metrics as rt
from utils.runtime_metrics import record_fill, mark_price


# ---- Percentile (_p) edge-case tests ----

def test_p_empty_returns_zero():
    assert mp._p([], 50) == 0.0
    assert mp._p([], 95) == 0.0


def test_p_singleton_returns_value():
    assert mp._p([10.0], 0) == 10.0
    assert mp._p([10.0], 50) == 10.0
    assert mp._p([10.0], 95) == 10.0


def test_p_even_length_rounding_behavior():
    # Sorted list of 4 elements
    lat = [1.0, 2.0, 3.0, 4.0]
    # k = round((q/100)*(n-1)), n=4 -> (q/100)*3
    # q=50 -> 1.5 -> round 2 -> lat[2] == 3.0
    assert mp._p(lat, 50) == 3.0
    # q=25 -> 0.75 -> round 1 -> lat[1] == 2.0
    assert mp._p(lat, 25) == 2.0
    # q=75 -> 2.25 -> round 2 -> lat[2] == 3.0
    assert mp._p(lat, 75) == 3.0
    # q=95 -> 2.85 -> round 3 -> lat[3] == 4.0
    assert mp._p(lat, 95) == 4.0


def test_p_odd_length_expected_values():
    lat = [1.0, 2.0, 3.0, 4.0, 5.0]
    # n=5 -> (q/100)*4
    # q=50 -> 2.0 -> round 2 -> 3.0
    assert mp._p(lat, 50) == 3.0
    # q=5 -> 0.2 -> round 0 -> 1.0
    assert mp._p(lat, 5) == 1.0
    # q=95 -> 3.8 -> round 4 -> 5.0
    assert mp._p(lat, 95) == 5.0


# ---- Schema correctness tests ----

def test_metrics_persistence_schema_tables_and_indexes(tmp_path, monkeypatch):
    test_db = tmp_path / "metrics_schema.db"
    monkeypatch.setattr(mp, "DB", test_db)

    # Populate runtime metrics minimally to ensure inserts
    rt.record_http_latency_ms(10.0)
    rt.record_http_latency_ms(40.0)
    # Equity per bot/strategy via a fill + mark_price
    record_fill("binance", "BTCUSDT", "buy", 30000.0, 0.001, bot_id="bot-schema", strategy="strat-schema")
    mark_price("BTCUSDT", 30500.0)

    mp.save_snapshot()

    assert test_db.exists(), "Brak pliku bazy metrics po save_snapshot()"

    con = sqlite3.connect(test_db)
    cur = con.cursor()

    # Verify tables exist
    cur.execute("SELECT name FROM sqlite_master WHERE type='table'")
    tables = {row[0] for row in cur.fetchall()}
    assert {"equity", "equity_bot", "equity_strategy", "latency"}.issubset(tables)

    # Verify columns using PRAGMA table_info
    def cols(table):
        cur.execute(f"PRAGMA table_info({table})")
        return [r[1] for r in cur.fetchall()]

    assert cols("equity") == ["ts", "value"]
    assert cols("equity_bot") == ["ts", "bot", "value"]
    assert cols("equity_strategy") == ["ts", "strategy", "value"]
    assert cols("latency") == ["ts", "p50", "p95"]

    # Verify indexes exist
    cur.execute("SELECT name, tbl_name FROM sqlite_master WHERE type='index'")
    idx = {row[0]: row[1] for row in cur.fetchall()}
    assert idx.get("ix_equity_ts") == "equity"
    assert idx.get("ix_equity_bot") == "equity_bot"
    assert idx.get("ix_equity_strategy") == "equity_strategy"
    assert idx.get("ix_latency_ts") == "latency"

    con.close()


def test_metrics_persistence_snapshot_inserts_rows(tmp_path, monkeypatch):
    test_db = tmp_path / "metrics_rows.db"
    monkeypatch.setattr(mp, "DB", test_db)

    # Populate runtime metrics
    rt.record_http_latency_ms(12.0)
    rt.record_http_latency_ms(36.0)
    record_fill("binance", "ETHUSDT", "sell", 2000.0, 0.01, bot_id="bot-rows", strategy="strat-rows")
    mark_price("ETHUSDT", 1990.0)

    mp.save_snapshot()

    con = sqlite3.connect(test_db)
    cur = con.cursor()
    cur.execute("SELECT COUNT(*) FROM equity")
    eq = cur.fetchone()[0]
    cur.execute("SELECT COUNT(*) FROM equity_bot")
    ebot = cur.fetchone()[0]
    cur.execute("SELECT COUNT(*) FROM equity_strategy")
    estr = cur.fetchone()[0]
    cur.execute("SELECT COUNT(*) FROM latency")
    lat = cur.fetchone()[0]
    con.close()

    assert eq >= 1
    assert ebot >= 1
    assert estr >= 1
    assert lat >= 1
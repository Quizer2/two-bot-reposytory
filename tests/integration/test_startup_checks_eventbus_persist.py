import sqlite3
import time
from pathlib import Path

import importlib

from utils.event_bus import get_event_bus, publish
from utils import metrics_persistence as mp
from utils import runtime_metrics as rt


def test_startup_checks_eventbus_subscriptions_and_persist_loop(tmp_path, monkeypatch):
    # Patch metrics DB to temporary file BEFORE importing startup_checks to avoid writing to real DB
    test_db = tmp_path / "startup_checks_metrics.db"
    monkeypatch.setattr(mp, "DB", test_db)

    # Import startup_checks (this sets up EventBus subscriptions and defines _persist_loop)
    startup_checks = importlib.import_module("bootstrap.startup_checks")

    bus = get_event_bus()

    # Verify that core subscriptions exist
    # We expect listeners for these events to be registered by startup_checks
    expected_events = [
        "ORDER_FILLED",
        "TradeFilled",
        "OrderExecuted",
        "MarketDataUpdate",
        "Retry",
        "ReconnectAttempt",
    ]
    for ev in expected_events:
        count = bus.get_listeners_count(ev) if hasattr(bus, "get_listeners_count") else 0
        assert count >= 1, f"Brak subskrybentów dla {ev} (count={count})"

    # Simulate events to populate runtime_metrics
    publish("ORDER_FILLED", {
        "exchange": "binance",
        "symbol": "BTCUSDT",
        "side": "buy",
        "price": 30000.0,
        "qty": 0.001,
        "bot_id": "bot-startup",
        "strategy": "strat-startup",
    })
    publish("MarketDataUpdate", {"symbol": "BTCUSDT", "price": 30400.0})
    rt.record_http_latency_ms(12.0)
    rt.record_http_latency_ms(36.0)

    # Monkeypatch persist loop to run a single iteration
    def _one_shot_persist():
        mp.save_snapshot()
    monkeypatch.setattr(startup_checks, "_persist_loop", _one_shot_persist)

    # Run the one-shot persist
    startup_checks._persist_loop()

    # Verify SQLite writes
    assert test_db.exists(), "Brak pliku bazy metrics po persist"

    con = sqlite3.connect(test_db)
    cur = con.cursor()

    cur.execute("SELECT name FROM sqlite_master WHERE type='table'")
    tables = {row[0] for row in cur.fetchall()}
    assert {"equity", "equity_bot", "equity_strategy", "latency"}.issubset(tables)

    cur.execute("SELECT COUNT(*) FROM equity")
    eq_count = cur.fetchone()[0]
    cur.execute("SELECT COUNT(*) FROM equity_bot")
    ebot_count = cur.fetchone()[0]
    cur.execute("SELECT COUNT(*) FROM equity_strategy")
    estr_count = cur.fetchone()[0]
    cur.execute("SELECT COUNT(*) FROM latency")
    lat_count = cur.fetchone()[0]
    con.close()

    assert eq_count >= 1
    assert ebot_count >= 1
    assert estr_count >= 1
    assert lat_count >= 1

    # Verify that runtime_metrics snapshot reflects bot/strategy from ORDER_FILLED
    snap = rt.snapshot()
    assert "bot-startup" in snap.get("bots", []), f"Brak 'bot-startup' w bots: {snap.get('bots', [])}"
    assert "strat-startup" in snap.get("strategies", []), f"Brak 'strat-startup' w strategies: {snap.get('strategies', [])}"
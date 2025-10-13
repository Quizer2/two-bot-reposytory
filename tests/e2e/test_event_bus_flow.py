import sqlite3
import json
from pathlib import Path
import time

import pytest

from utils import runtime_metrics as rt
from utils import metrics_persistence as mp
from utils.event_bus import get_event_bus, publish


@pytest.fixture()
def event_bus_clean():
    bus = get_event_bus()
    # Ensure clean state for listeners
    if hasattr(bus, "clear"):
        bus.clear()
    return bus


def test_event_bus_runtime_metrics_persistence_and_audit(tmp_path, monkeypatch, event_bus_clean):
    # Patch metrics DB to temporary path to avoid touching real DB
    test_db = tmp_path / "metrics_e2e.db"
    monkeypatch.setattr(mp, "DB", test_db)

    bus = event_bus_clean

    # Handlers emulating startup subscriptions
    def on_order_filled(p):
        try:
            ex = (p.get("exchange") if isinstance(p, dict) else None) or "na"
            sym = p.get("symbol") or "NA"
            side = p.get("side") or "NA"
            price = float(p.get("price") or 0.0)
            qty = float(p.get("qty") or 0.0)
            bot_id = p.get("bot_id")
            strategy = p.get("strategy")
            from utils.runtime_metrics import record_fill
            record_fill(ex, sym, side, price, qty, bot_id, strategy)
            rt.record_order_event(ex, sym, side)
        except Exception:
            # keep test robust even if payload changes
            pass

    def on_market_tick(p):
        try:
            sym = p.get("symbol") or "NA"
            price = p.get("price") or p.get("bid") or p.get("ask")
            if price is not None:
                from utils.runtime_metrics import mark_price
                mark_price(sym, float(price))
        except Exception:
            pass

    def on_retry(p):
        rt.record_event_name("Retry")

    def on_reconnect(p):
        rt.record_event_name("ReconnectAttempt")

    # Subscribe handlers
    bus.subscribe("ORDER_FILLED", on_order_filled)
    bus.subscribe("MarketDataUpdate", on_market_tick)
    bus.subscribe("Retry", on_retry)
    bus.subscribe("ReconnectAttempt", on_reconnect)

    # Generate events via EventBus
    publish("ORDER_FILLED", {
        "exchange": "binance",
        "symbol": "BTCUSDT",
        "side": "buy",
        "price": 30000.0,
        "qty": 0.001,
        "bot_id": "bot-e2e",
        "strategy": "strat-e2e",
    })
    publish("MarketDataUpdate", {"symbol": "BTCUSDT", "price": 30500.0})
    publish("Retry", {"reason": "test"})
    publish("ReconnectAttempt", {"endpoint": "ws"})

    # Also provide latency samples so persistence writes to latency table
    rt.record_http_latency_ms(10.0)
    rt.record_http_latency_ms(25.0)

    # Persist snapshot
    mp.save_snapshot()

    # Assertions: runtime_metrics snapshot updated
    snap = rt.snapshot()
    assert "bot-e2e" in snap.get("bots", []), f"Brak 'bot-e2e' w bots: {snap.get('bots', [])}"
    assert "strat-e2e" in snap.get("strategies", []), f"Brak 'strat-e2e' w strategies: {snap.get('strategies', [])}"
    assert isinstance(snap.get("equity_curve", []), list) and len(snap.get("equity_curve", [])) >= 1, "Pusta equity_curve"
    assert len(snap.get("equity_curve_per_bot", {}).get("bot-e2e", [])) >= 1, "Pusta equity_curve_per_bot dla bot-e2e"
    assert len(snap.get("equity_curve_per_strategy", {}).get("strat-e2e", [])) >= 1, "Pusta equity_curve_per_strategy dla strat-e2e"

    # Check event counters
    events_total = snap.get("events_total", {})
    assert events_total.get("Retry", 0) >= 1, f"Brak licznika Retry: {events_total}"
    assert events_total.get("ReconnectAttempt", 0) >= 1, f"Brak licznika ReconnectAttempt: {events_total}"

    # Assertions: SQLite persistence
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

    # Assertions: audit log contains our events (publish is monkey-patched to log JSONL)
    log_file = Path("logs") / "events.jsonl"
    assert log_file.exists(), "Brak pliku audytu zdarzeń"
    # read last lines and ensure our events are present
    lines = log_file.read_text(encoding="utf-8").splitlines()
    # allow some time if file writing is slightly delayed
    if not lines:
        time.sleep(0.05)
        lines = log_file.read_text(encoding="utf-8").splitlines()
    recent = lines[-50:] if len(lines) > 50 else lines
    events = []
    for ln in recent:
        try:
            rec = json.loads(ln)
            events.append(rec.get("event"))
        except Exception:
            continue
    assert "ORDER_FILLED" in events, f"Brak ORDER_FILLED w audycie: {events}"
    assert "MarketDataUpdate" in events, f"Brak MarketDataUpdate w audycie: {events}"

    # Cleanup: remove our handlers
    bus.unsubscribe("ORDER_FILLED", on_order_filled)
    bus.unsubscribe("MarketDataUpdate", on_market_tick)
    bus.unsubscribe("Retry", on_retry)
    bus.unsubscribe("ReconnectAttempt", on_reconnect)
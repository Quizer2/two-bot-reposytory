import threading
import time
import sqlite3
from pathlib import Path

import pytest

from utils import runtime_metrics as rt
from utils import metrics_persistence as mp


def test_runtime_metrics_snapshot_consistency_under_concurrency(tmp_path, monkeypatch):
    # Patch DB to temporary path
    test_db = tmp_path / "metrics_concurrency.db"
    monkeypatch.setattr(mp, "DB", test_db)

    stop = threading.Event()

    def producer_events():
        i = 0
        while not stop.is_set() and i < 500:
            # Alternate fills and price marks, plus http latency
            rt.record_http_latency_ms(5.0 + (i % 10))
            rt.record_event_name("Retry" if i % 7 == 0 else "MarketDataUpdate")
            rt.record_order_event("binance", "BTCUSDT", "buy")
            rt.record_fill("binance", "BTCUSDT", "buy", 30000.0 + (i % 20), 0.0005, bot_id="bot-conc", strategy="strat-conc")
            rt.mark_price("BTCUSDT", 30050.0 + (i % 20))
            i += 1
            if i % 50 == 0:
                time.sleep(0.005)

    def snapshotter_and_persist():
        # Rapid snapshots and occasional DB writes
        for j in range(20):
            snap = rt.snapshot()
            # Snapshot should be internally consistent (lengths match semantics)
            eq = snap.get("equity_curve", [])
            bots = snap.get("bots", [])
            strategies = snap.get("strategies", [])
            # If equity_curve has points, bot/strategy specific curves should also have entries for known ids
            if eq:
                ebot = snap.get("equity_curve_per_bot", {}).get("bot-conc", [])
                estr = snap.get("equity_curve_per_strategy", {}).get("strat-conc", [])
                assert len(ebot) >= 1
                assert len(estr) >= 1
            # Persist intermittently
            if j % 5 == 0:
                mp.save_snapshot()
            time.sleep(0.01)

    t1 = threading.Thread(target=producer_events)
    t2 = threading.Thread(target=snapshotter_and_persist)

    t1.start(); t2.start()
    t1.join(); t2.join()

    stop.set()

    # Final snapshot consistency checks
    snap = rt.snapshot()
    assert "bot-conc" in snap.get("bots", [])
    assert "strat-conc" in snap.get("strategies", [])
    assert len(snap.get("equity_curve", [])) >= 1
    assert len(snap.get("equity_curve_per_bot", {}).get("bot-conc", [])) >= 1
    assert len(snap.get("equity_curve_per_strategy", {}).get("strat-conc", [])) >= 1

    # Verify DB has entries
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
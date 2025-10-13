import time
import sqlite3
import pytest

from utils import runtime_metrics as rt
import utils.net_wrappers as nw
import utils.metrics_persistence as mp


def test_net_guard_success_labels(monkeypatch):
    calls = []

    def fake_inc_http(exchange: str, method: str, endpoint: str, status: str = "OK"):
        calls.append(("inc_http", exchange, method, endpoint, status))

    def fake_set_circuit(exchange: str, endpoint: str, open_state: bool):
        calls.append(("set_circuit", exchange, endpoint, open_state))

    # Podmień funkcje eksportera metryk wewnątrz net_wrappers
    monkeypatch.setattr(nw, "inc_http", fake_inc_http)
    monkeypatch.setattr(nw, "set_circuit", fake_set_circuit)

    @nw.net_guard("binance:rest:/api/v3/order")
    def place_order():
        time.sleep(0.002)
        return "ok"

    res = place_order()
    assert res == "ok"

    # Sprawdź poprawne etykiety
    assert any(
        c for c in calls
        if c[0] == "inc_http" and c[1] == "binance" and c[2] == "REST" and c[3] == "/api/v3/order" and c[4] == "OK"
    )
    assert any(
        c for c in calls
        if c[0] == "set_circuit" and c[1] == "binance" and c[2] == "/api/v3/order" and (c[3] is False or c[3] == 0)
    )

    snap = rt.snapshot()
    assert snap["http_requests"] >= 1
    assert len(snap["http_latency_ms"]) >= 1


def test_net_guard_error_labels(monkeypatch):
    calls = []

    def fake_inc_http(exchange: str, method: str, endpoint: str, status: str = "OK"):
        calls.append(("inc_http", exchange, method, endpoint, status))

    def fake_set_circuit(exchange: str, endpoint: str, open_state: bool):
        calls.append(("set_circuit", exchange, endpoint, open_state))

    monkeypatch.setattr(nw, "inc_http", fake_inc_http)
    monkeypatch.setattr(nw, "set_circuit", fake_set_circuit)

    @nw.net_guard("binance:rest:/api/v3/order")
    def fail_order():
        raise ValueError("boom")

    with pytest.raises(ValueError):
        fail_order()

    # Sprawdź etykiety i status ERR
    assert any(
        c for c in calls
        if c[0] == "inc_http" and c[1] == "binance" and c[2] == "REST" and c[3] == "/api/v3/order" and c[4] == "ERR"
    )
    assert any(
        c for c in calls
        if c[0] == "set_circuit" and c[1] == "binance" and c[2] == "/api/v3/order" and (c[3] is False or c[3] == 0)
    )


def test_metrics_persistence_snapshot_writes_sqlite(tmp_path, monkeypatch):
    # Skieruj zapis do tymczasowej bazy
    test_db = tmp_path / "metrics_test.db"
    monkeypatch.setattr(mp, "DB", test_db)

    # Wygeneruj proste dane runtime: latency + equity
    rt.record_http_latency_ms(10.0)
    rt.record_http_latency_ms(25.0)

    from utils.runtime_metrics import record_fill, mark_price

    # Zapis transakcji powoduje zmianę equity
    record_fill("binance", "BTCUSDT", "buy", 30000.0, 0.001, bot_id="bot1", strategy="stratA")
    mark_price("BTCUSDT", 30500.0)

    # Zapis snapshotu
    mp.save_snapshot()

    # Weryfikacja tabel i wpisów
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
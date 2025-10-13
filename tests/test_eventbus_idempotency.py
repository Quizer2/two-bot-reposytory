import importlib
import pytest

from utils.event_bus import get_event_bus
from utils import metrics_persistence as mp


@pytest.fixture()
def event_bus_with_startup(tmp_path, monkeypatch):
    # Ensure metrics persistence writes to a temp DB to avoid touching real DB
    test_db = tmp_path / "eventbus_idem_metrics.db"
    monkeypatch.setattr(mp, "DB", test_db)
    # Import startup_checks to install default subscribers and the clear() hook
    importlib.import_module("bootstrap.startup_checks")
    bus = get_event_bus()
    return bus


def test_subscribe_idempotency_no_duplicates(event_bus_with_startup):
    bus = event_bus_with_startup
    # Use a named function to ensure identity comparison works
    def _cb(payload):
        return None
    base = bus.get_listeners_count("MarketDataUpdate") if hasattr(bus, "get_listeners_count") else 0
    # Subscribe the same callback twice for the same event
    bus.subscribe("MarketDataUpdate", _cb)
    bus.subscribe("MarketDataUpdate", _cb)
    after = bus.get_listeners_count("MarketDataUpdate") if hasattr(bus, "get_listeners_count") else 0
    # Expect only one increase due to idempotent subscription behavior
    assert after == base + 1, f"Expected one listener increase, got base={base}, after={after}"


def test_clear_idempotency_no_duplicate_reinstall(event_bus_with_startup):
    bus = event_bus_with_startup
    expected_events = [
        "ORDER_FILLED",
        "TradeFilled",
        "OrderExecuted",
        "MarketDataUpdate",
        "Retry",
        "ReconnectAttempt",
    ]
    # Baseline counts after startup_checks installation
    baseline = {ev: bus.get_listeners_count(ev) if hasattr(bus, "get_listeners_count") else 0 for ev in expected_events}
    # Call clear() multiple times; hook will reinstall defaults each time
    for _ in range(3):
        bus.clear()
    after = {ev: bus.get_listeners_count(ev) if hasattr(bus, "get_listeners_count") else 0 for ev in expected_events}
    # Counts should not increase due to idempotent subscribe inside EventBus; ensure at least one listener exists
    for ev in expected_events:
        assert after[ev] >= 1, f"Expected at least one listener for {ev} after clear() reinstall"
        assert after[ev] <= baseline[ev], (
            f"Listener count for {ev} should not increase after repeated clear(): baseline={baseline[ev]}, after={after[ev]}"
        )


def test_global_subscribe_duplicate_ignored(event_bus_with_startup):
    bus = event_bus_with_startup
    from utils.event_bus import subscribe as global_subscribe

    def _dup_cb(payload):
        return None

    base = bus.get_listeners_count("Retry") if hasattr(bus, "get_listeners_count") else 0
    bus.subscribe("Retry", _dup_cb)
    # Try to subscribe the same callback via convenience function; should be ignored as duplicate
    global_subscribe("Retry", _dup_cb)
    after = bus.get_listeners_count("Retry") if hasattr(bus, "get_listeners_count") else 0
    assert after == base + 1, f"Duplicate global subscribe should be ignored: base={base}, after={after}"
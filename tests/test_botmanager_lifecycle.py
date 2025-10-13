import pytest

from utils.event_bus import get_event_bus, EventTypes
from core.bot_manager import get_bot_manager, reset_bot_manager, BotType, BotStatus
from utils import runtime_metrics as rt


def test_botmanager_lifecycle_events_affect_runtime_metrics():
    # Ensure clean EventBus and BotManager
    bus = get_event_bus()
    bus.clear()
    reset_bot_manager()
    bm = get_bot_manager()

    # Subscribe runtime metrics recording to BOT_* events
    bus.subscribe(EventTypes.BOT_STARTED, lambda payload: rt.record_event_name(EventTypes.BOT_STARTED))
    bus.subscribe(EventTypes.BOT_STOPPED, lambda payload: rt.record_event_name(EventTypes.BOT_STOPPED))
    bus.subscribe(EventTypes.BOT_UPDATED, lambda payload: rt.record_event_name(EventTypes.BOT_UPDATED))

    # Baseline metrics snapshot
    snap0 = rt.snapshot()
    started0 = snap0["events_total"].get(EventTypes.BOT_STARTED, 0)
    stopped0 = snap0["events_total"].get(EventTypes.BOT_STOPPED, 0)
    updated0 = snap0["events_total"].get(EventTypes.BOT_UPDATED, 0)

    # Create bot with minimal valid config
    bot_id = "bot-1"
    config = {"symbol": "BTCUSDT", "strategy": "scalping", "risk_management": {"max_drawdown": 0.2}}
    assert bm.create_bot(bot_id, BotType.SCALPING, config) is True
    assert bm.get_bot_status(bot_id) == BotStatus.STOPPED

    # Start bot -> should publish BOT_STARTED and update status
    assert bm.start_bot(bot_id) is True
    assert bm.get_bot_status(bot_id) == BotStatus.RUNNING

    # Stop bot -> should publish BOT_STOPPED and update status
    assert bm.stop_bot(bot_id) is True
    assert bm.get_bot_status(bot_id) == BotStatus.STOPPED

    # Simulate bot update event through EventBus
    bus.publish(EventTypes.BOT_UPDATED, {"bot_id": bot_id, "field": "status", "value": "stopped"})

    # Validate runtime_metrics counters increased accordingly
    snap1 = rt.snapshot()
    assert snap1["events_total"].get(EventTypes.BOT_STARTED, 0) == started0 + 1
    assert snap1["events_total"].get(EventTypes.BOT_STOPPED, 0) == stopped0 + 1
    assert snap1["events_total"].get(EventTypes.BOT_UPDATED, 0) == updated0 + 1

    # Record a trade fill to ensure bot appears in seen_bots and equity tracking updates
    rt.record_fill("binance", "BTCUSDT", "buy", 100.0, 0.1, bot_id=bot_id, strategy="scalping")
    snap2 = rt.snapshot()
    assert bot_id in snap2["bots"]
    assert "scalping" in snap2["strategies"]
    assert bot_id in snap2["equity_curve_per_bot"]
    assert len(snap2["equity_curve_per_bot"][bot_id]) >= 1

    # Running bots list should be empty after stop
    assert bm.get_running_bots() == []
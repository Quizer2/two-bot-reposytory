import pytest

from utils.event_bus import get_event_bus, EventTypes, publish_event
from utils import runtime_metrics as rt
from core.trading_engine import get_trading_engine, OrderResponse, OrderStatus


def test_tradingengine_cancel_flow_and_metrics():
    bus = get_event_bus(); bus.clear()
    # Record cancel events via runtime_metrics
    bus.subscribe(EventTypes.ORDER_CANCELLED, lambda payload: rt.record_event_name(EventTypes.ORDER_CANCELLED))

    base = rt.snapshot()
    canc0 = base["events_total"].get(EventTypes.ORDER_CANCELLED, 0)

    te = get_trading_engine()
    import asyncio
    # Place a limit order (NEW) in demo
    resp: OrderResponse = asyncio.get_event_loop().run_until_complete(te.submit_order("ETHUSDT","sell",0.002, price=2000.0, order_type='limit'))
    assert resp.status in (OrderStatus.NEW, OrderStatus.FILLED)

    # Register order in active_orders to allow cancel
    te.active_orders[resp.order_id] = resp

    # Cancel the order
    ok = asyncio.get_event_loop().run_until_complete(te.cancel_order(resp.order_id, symbol=resp.symbol))
    assert ok is True

    # Publish cancel event canonical
    publish_event(EventTypes.ORDER_CANCELLED, {"bot_id":"TBOT","symbol":resp.symbol,"order_id":resp.order_id})

    snap = rt.snapshot()
    assert snap["events_total"].get(EventTypes.ORDER_CANCELLED, 0) == canc0 + 1
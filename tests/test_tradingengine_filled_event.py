import asyncio
import pytest

from utils.event_bus import get_event_bus, publish_event
from utils import runtime_metrics as rt
from core.trading_engine import get_trading_engine, OrderStatus, OrderResponse


def test_tradingengine_filled_flow_and_metrics():
    bus = get_event_bus(); bus.clear()

    def on_order_filled(payload: dict):
        rt.record_event_name("ORDER_FILLED")
        try:
            ex = payload.get("exchange", "demo")
            sym = payload.get("symbol", "BTCUSDT")
            side = payload.get("side", "BUY")
            price = float(payload.get("price", 0.0))
            qty = float(payload.get("qty") or payload.get("quantity") or 0.0)
            rt.record_fill(ex, sym, side, price, qty, bot_id=payload.get("bot_id"), strategy=payload.get("strategy"))
        except Exception:
            pass

    # Subscribe to ORDER_FILLED and TradeFilled variants
    bus.subscribe("ORDER_FILLED", on_order_filled)
    bus.subscribe("TradeFilled", on_order_filled)

    base = rt.snapshot()
    ev0 = base["events_total"].get("ORDER_FILLED", 0)
    cash0 = base["cash"]
    pos0 = base["positions"].get("BTCUSDT", 0.0)
    eq0 = len(base["equity_curve"]) if base.get("equity_curve") is not None else 0

    te = get_trading_engine()
    # Submit market BUY order in demo mode (should be FILLED)
    resp: OrderResponse = asyncio.get_event_loop().run_until_complete(
        te.submit_order("BTCUSDT", "buy", 0.001, order_type='market', price=29000.0)
    )
    assert resp is not None
    assert resp.status == OrderStatus.FILLED

    # Publish ORDER_FILLED with payload used by runtime_metrics
    publish_event("ORDER_FILLED", {
        "exchange": "demo",
        "symbol": resp.symbol,
        "side": "BUY",
        "price": 29000.0,
        "qty": 0.001,
        "bot_id": "TBOT",
        "strategy": "unit"
    })

    snap = rt.snapshot()
    assert snap["events_total"].get("ORDER_FILLED", 0) == ev0 + 1
    assert snap["cash"] < cash0
    assert snap["positions"].get("BTCUSDT", 0.0) > pos0
    eq1 = len(snap["equity_curve"]) if snap.get("equity_curve") is not None else 0
    assert eq1 >= eq0 + 1
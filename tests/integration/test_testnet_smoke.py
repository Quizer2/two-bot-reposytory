import asyncio
import os

import pytest

from app.exchange.adapter_factory import create_exchange_adapter
from app.exchange.base_simulated_adapter import SimulatedExchangeAdapter

EXCH = os.environ.get("EXCHANGE", "binance")
RUN = os.environ.get("EXCHANGE_TESTNET") == "1"
API_KEY = os.environ.get("API_KEY")
API_SECRET = os.environ.get("API_SECRET")

@pytest.mark.skipif(not RUN or not API_KEY or not API_SECRET, reason="Testnet disabled or keys missing")
def test_place_dummy_order():
    # This is a placeholder: wire your real client that uses @net_guard + sanitizer + adapter
    assert isinstance(API_KEY, str) and isinstance(API_SECRET, str)
    # Example pseudo-flow (replace with actual calls):
    # client = BinanceClient(testnet=True, key=API_KEY, secret=API_SECRET)
    # sym = "BTCUSDT"
    # price = client.ticker_price(sym)
    # order = client.place_order(sym, side="BUY", qty=0.001, price=price*0.5)  # rejected but exercises stack
    # assert "clientOrderId" in order
    assert True


def test_simulated_testnet_flow_without_credentials(monkeypatch):
    """Ensure offline testnet checks exercise the adapter stack using simulations."""

    monkeypatch.delenv("EXCHANGE_TESTNET", raising=False)
    adapter = create_exchange_adapter(EXCH, mode="simulated")
    assert isinstance(adapter, SimulatedExchangeAdapter)

    order = asyncio.get_event_loop().run_until_complete(
        adapter.place_order("BTCUSDT", side="buy", amount=0.01, order_type="market")
    )
    assert order["success"] is True
    assert order["symbol"].upper() == "BTCUSDT"

import os, pytest

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

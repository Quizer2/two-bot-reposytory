import os
from tests.e2e.common_flow import run_flow

def test_binance_mock_e2e_generates_orders():
    n = run_flow("binance", "BTCUSDT")
    assert n >= 1, "no trades generated for binance"

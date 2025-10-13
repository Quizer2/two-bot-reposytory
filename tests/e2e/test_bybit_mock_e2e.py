import os
from tests.e2e.common_flow import run_flow

def test_bybit_mock_e2e_generates_orders():
    n = run_flow("bybit", "BTCUSDT")
    assert n >= 1, "no trades generated for bybit"

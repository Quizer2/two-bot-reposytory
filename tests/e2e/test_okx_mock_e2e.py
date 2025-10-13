import os
from tests.e2e.common_flow import run_flow

def test_okx_mock_e2e_generates_orders():
    n = run_flow("okx", "BTC-USDT")
    assert n >= 1, "no trades generated for okx"

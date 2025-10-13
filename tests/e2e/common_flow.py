# Shared E2E helpers: synthetic market, simple SMA signal, order via adapters, publish to event bus
from utils.event_bus import publish_event
from utils.adapters.exchange_adapter import ExchangeAdapter
from utils.orders import build_order

def synthetic_prices(start=100.0, steps=50):
    out = []
    px = start
    for i in range(steps):
        # simple wave
        px += (1 if i%10<5 else -1)
        out.append(px)
    return out

def sma(prices, n):
    out = []
    acc=0.0
    for i,p in enumerate(prices):
        acc+=p
        if i>=n: acc-=prices[i-n]
        out.append(acc/min(i+1,n))
    return out

def run_flow(exchange: str, symbol: str):
    prices = synthetic_prices()
    sma_short = sma(prices, 3)
    sma_long = sma(prices, 7)
    adapter = ExchangeAdapter()
    # set generic rules
    adapter.set_rules(symbol, min_qty=0.001, step_size=0.001, tick_size=0.01)
    trades = 0
    for i in range(1, len(prices)):
        if sma_short[i-1] <= sma_long[i-1] and sma_short[i] > sma_long[i]:
            # cross up -> buy
            order = build_order(adapter, bot_id="E2E", symbol=symbol, side="buy", qty=0.001, price=prices[i])
            order['exchange'] = exchange
            publish_event("OrderSubmitted", order)
            trades += 1
    return trades

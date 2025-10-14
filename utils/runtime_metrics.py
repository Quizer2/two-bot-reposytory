from __future__ import annotations
import threading, time
import math
from collections import defaultdict, deque
from typing import Deque, Dict, Tuple

class _RuntimeMetrics:
    START_CASH = 10000.0
    def __init__(self):
        self._lock = threading.RLock()
        self.events_total: Dict[str,int] = defaultdict(int)
        self.orders_total: Dict[Tuple[str,str,str], int] = defaultdict(int)  # (exchange,symbol,side) -> count
        self.rate_drops: Dict[Tuple[str,str], int] = defaultdict(int)        # (exchange,endpoint) -> drops
        self.circuit_open: Dict[Tuple[str,str], bool] = defaultdict(bool)    # (exchange,endpoint) -> open
        self.http_latency_ms: Deque[float] = deque(maxlen=500)               # recent latencies
        self.http_latency_per_exchange: Dict[str, Deque[float]] = defaultdict(lambda: deque(maxlen=300))
        self.http_latency_per_endpoint: Dict[Tuple[str, str], Deque[float]] = defaultdict(lambda: deque(maxlen=200))
        self.http_requests: int = 0
        self.retries: int = 0
        self.reconnects: int = 0
        # equity tracking
        self.equity_curve: Deque[Tuple[float,float]] = deque(maxlen=10000)
        self.cash: float = self.START_CASH
        self.positions = defaultdict(float)
        self.last_price = defaultdict(float)
        # seen identifiers
        self.seen_exchanges: set[str] = set()
        self.seen_bots: set[str] = set()
        self.seen_strategies: set[str] = set()
        # per-entity equity curves
        self.equity_curve_per_bot = defaultdict(lambda: deque(maxlen=10000))
        self.equity_curve_per_strategy = defaultdict(lambda: deque(maxlen=10000))

    def snapshot(self):
        with self._lock:
            latency_summary = self._build_latency_summary()
            return {
                "events_total": dict(self.events_total),
                "orders_total": dict(self.orders_total),
                "rate_drops": dict(self.rate_drops),
                "circuit_open": dict(self.circuit_open),
                "http_requests": self.http_requests,
                "http_latency_ms": list(self.http_latency_ms),
                "latency_summary": latency_summary,
                "retries": self.retries,
                "reconnects": self.reconnects,
                "equity_curve": list(self.equity_curve),
                "cash": self.cash,
                "positions": dict(self.positions),
                "last_price": dict(self.last_price),
                "exchanges": list(self.seen_exchanges),
                "bots": list(self.seen_bots),
                "strategies": list(self.seen_strategies),
                "http_latency_per_exchange": {k: list(v) for k, v in self.http_latency_per_exchange.items()},
                "http_latency_per_endpoint": {f"{k[0]}::{k[1]}": list(v) for k, v in self.http_latency_per_endpoint.items()},
                "equity_curve_per_bot": {k:list(v) for k,v in self.equity_curve_per_bot.items()},
                "equity_curve_per_strategy": {k:list(v) for k,v in self.equity_curve_per_strategy.items()},
            }

    def record_http(self, latency_ms: float, exchange: str | None = None, endpoint: str | None = None):
        with self._lock:
            self.http_requests += 1
            self.http_latency_ms.append(float(latency_ms))
            if exchange:
                key = str(exchange).lower()
                self.http_latency_per_exchange[key].append(float(latency_ms))
                if endpoint:
                    endpoint_key = (key, str(endpoint))
                    self.http_latency_per_endpoint[endpoint_key].append(float(latency_ms))

    def record_rate_drop(self, exchange: str, endpoint: str):
        with self._lock:
            self.rate_drops[(exchange, endpoint)] += 1

    def record_order(self, exchange: str, symbol: str, side: str):
        with self._lock:
            key = ((exchange or "na"), (symbol or "NA"), (side or "NA"))
            self.orders_total[key] += 1

    def set_circuit(self, exchange: str, endpoint: str, open_state: bool):
        with self._lock:
            self.circuit_open[(exchange, endpoint)] = bool(open_state)

    def record_event(self, ev: str):
        with self._lock:
            self.events_total[str(ev)] += 1
            lo = str(ev).lower()
            if lo.startswith("reconnect"):
                self.reconnects += 1
            if lo.startswith("retry"):
                self.retries += 1

    def _build_latency_summary(self):
        def _summary(seq):
            data = list(seq)
            if not data:
                return {
                    "count": 0,
                    "avg": 0.0,
                    "p50": 0.0,
                    "p95": 0.0,
                    "max": 0.0,
                    "min": 0.0,
                    "latest": 0.0,
                }

            data_sorted = sorted(data)
            count = len(data_sorted)
            avg = sum(data_sorted) / count if count else 0.0

            def _percentile(values, percentile):
                if not values:
                    return 0.0
                if len(values) == 1:
                    return float(values[0])
                k = (len(values) - 1) * percentile
                f = math.floor(k)
                c = math.ceil(k)
                if f == c:
                    return float(values[int(k)])
                d0 = values[f] * (c - k)
                d1 = values[c] * (k - f)
                return float(d0 + d1)

            return {
                "count": count,
                "avg": float(avg),
                "p50": float(_percentile(data_sorted, 0.50)),
                "p95": float(_percentile(data_sorted, 0.95)),
                "max": float(max(data_sorted)),
                "min": float(min(data_sorted)),
                "latest": float(data[-1]),
            }

        global_summary = _summary(self.http_latency_ms)
        per_exchange = {ex: _summary(samples) for ex, samples in self.http_latency_per_exchange.items()}
        return {"global": global_summary, "per_exchange": per_exchange}


_METRICS = _RuntimeMetrics()

# wrappers
def snapshot():
    return _METRICS.snapshot()

def record_http_latency_ms(ms: float, exchange: str | None = None, endpoint: str | None = None):
    _METRICS.record_http(ms, exchange=exchange, endpoint=endpoint)

def record_rate_drop(exchange: str, endpoint: str):
    _METRICS.record_rate_drop(exchange, endpoint)

def set_circuit_state(exchange: str, endpoint: str, open_state: bool):
    _METRICS.set_circuit(exchange, endpoint, open_state)

def record_event_name(name: str):
    _METRICS.record_event(name)

def record_order_event(exchange: str, symbol: str, side: str):
    _METRICS.record_order(exchange, symbol, side)

# fills and mark-to-market
def record_fill(exchange: str, symbol: str, side: str, price: float, qty: float, bot_id: str | None=None, strategy: str | None=None):
    with _METRICS._lock:
        if exchange:
            _METRICS.seen_exchanges.add(exchange.lower())
        if bot_id:
            _METRICS.seen_bots.add(str(bot_id))
        if strategy:
            _METRICS.seen_strategies.add(str(strategy))
        p = float(price); q = float(qty)
        if str(side).lower() == "buy":
            _METRICS.cash -= p * q
            _METRICS.positions[symbol] += q
        else:
            _METRICS.cash += p * q
            _METRICS.positions[symbol] -= q
        _METRICS.last_price[symbol] = p
        eq = _METRICS.cash + sum(qty * _METRICS.last_price.get(sym, 0.0) for sym, qty in _METRICS.positions.items())
        now = time.time()
        _METRICS.equity_curve.append((now, eq))
        if bot_id:
            _METRICS.equity_curve_per_bot[str(bot_id)].append((now, eq))
        if strategy:
            _METRICS.equity_curve_per_strategy[str(strategy)].append((now, eq))

def mark_price(symbol: str, price: float):
    with _METRICS._lock:
        _METRICS.last_price[symbol] = float(price)
        eq = _METRICS.cash + sum(qty * _METRICS.last_price.get(sym, 0.0) for sym, qty in _METRICS.positions.items())
        _METRICS.equity_curve.append((time.time(), eq))

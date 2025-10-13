from __future__ import annotations
from prometheus_client import Counter, Gauge, start_http_server
import logging

logger = logging.getLogger(__name__)

HTTP_REQUESTS = Counter(
    "http_requests_total",
    "HTTP requests by exchange/method/endpoint/status",
    ["exchange","method","endpoint","status"]
)
RATE_LIMIT_DROPS = Counter(
    "rate_limit_drops_total",
    "Dropped operations due to rate limit",
    ["exchange","endpoint"]
)
CIRCUIT_OPEN = Gauge(
    "circuit_open",
    "Circuit breaker open state (1=open, 0=closed)",
    ["exchange","endpoint"]
)
EVENTS_TOTAL = Counter(
    "events_total",
    "Published events by name",
    ["event"]
)
ORDERS_TOTAL = Counter(
    "orders_total",
    "Orders by exchange/symbol/side",
    ["exchange","symbol","side"]
)

def start_metrics_server(port:int=8000):
    try:
        start_http_server(port)
        logger.info("Prometheus metrics exporter on :%s", port)
    except Exception as e:
        logger.warning("Cannot start metrics exporter: %s", e)

def inc_http(exchange:str, method:str, endpoint:str, status:str="OK"):
    try:
        HTTP_REQUESTS.labels(exchange, method, endpoint, status).inc()
    except Exception:
        pass

def inc_rate_drop(exchange:str, endpoint:str):
    try:
        RATE_LIMIT_DROPS.labels(exchange, endpoint).inc()
    except Exception:
        pass

def set_circuit(exchange:str, endpoint:str, open_state:bool):
    try:
        CIRCUIT_OPEN.labels(exchange, endpoint).set(1 if open_state else 0)
    except Exception:
        pass

def on_event(ev_name:str, payload):
    try:
        EVENTS_TOTAL.labels(ev_name).inc()
        if ev_name in ("OrderSubmitted","ORDER_SUBMITTED"):
            ex = (payload.get("exchange") if isinstance(payload, dict) else None) or "na"
            sym = (payload.get("symbol") if isinstance(payload, dict) else None) or "na"
            side = (payload.get("side") if isinstance(payload, dict) else None) or "na"
            ORDERS_TOTAL.labels(ex, sym, side).inc()
    except Exception:
        pass

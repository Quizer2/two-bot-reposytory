from __future__ import annotations
import time
from utils import runtime_metrics as rt
from utils.metrics_exporter import inc_http, inc_rate_drop, set_circuit
import threading
from functools import wraps
from typing import Callable, Dict, Tuple
import logging
from pathlib import Path
from .rate_limit import TokenBucket
from .circuit_breaker import CircuitBreaker
from .yaml_loader import safe_load
import inspect
import asyncio

logger = logging.getLogger(__name__)

def _resolve_endpoint_from_fn(exch: str, fn: str) -> tuple[str,str]:
    # returns (method, path) or ('NA', fn)
    try:
        cfg_path = Path(__file__).resolve().parents[1] / "config" / "endpoint_map.yaml"
        data = safe_load(cfg_path.read_text(encoding="utf-8")) or {}
        ex = (data.get("exchanges") or {}).get(exch.lower()) or {}
        mp = ex.get(fn)
        if mp and mp.get("method") and mp.get("path"):
            return str(mp["method"]).upper(), str(mp["path"])
    except Exception:
        pass
    return "NA", fn

_buckets: Dict[str, TokenBucket] = {}
_breakers: Dict[str, CircuitBreaker] = {}
_lock = threading.Lock()

def _load_limits():
    cfg_path = Path(__file__).resolve().parents[1] / "config" / "rate_limits.yaml"
    if not cfg_path.exists():
        return {}
    return safe_load(cfg_path.read_text(encoding="utf-8")) or {}

def get_guard(name: str) -> Tuple[TokenBucket, CircuitBreaker]:
    # name may be 'exchange:op' or 'exchange:rest:/api/v3/order'
    key = name.lower()
    with _lock:
        if key in _buckets and key in _breakers:
            return _buckets[key], _breakers[key]
        cfg = _load_limits()
        parts = key.split(":", 1)
        exch = parts[0]
        ex_all = (cfg.get('exchanges') or {}).get(exch) or {}
        ex_cfg = ex_all.get('default') or {}
        rate = float(ex_cfg.get("rate_per_sec", 10))
        cap = float(ex_cfg.get("capacity", rate))
        failure_threshold = int(ex_cfg.get("failure_threshold", 5))
        recovery_time = float(ex_cfg.get("recovery_time", 30.0))
        
        # endpoint override (if name contains ':rest:' or ':ws:' with a path)
        endpoint = None
        if ':' in key:
            parts2 = key.split(':', 2)
            if len(parts2) >= 3:
                endpoint = parts2[2]
        if endpoint and ex_all.get('patterns'):
            for pat in ex_all['patterns']:
                if str(pat.get('path')) == endpoint:
                    ex_cfg = {**ex_cfg, **{k: v for k, v in pat.items() if k in ('rate_per_sec','capacity')}} 
                    break
    
        tb = TokenBucket(rate, cap)
        br = CircuitBreaker(failure_threshold, recovery_time)
        _buckets[key] = tb
        _breakers[key] = br
        return tb, br

def _resolve_guard_name(base_name: str, args: tuple) -> str:
    if base_name.startswith("exchange:") and args:
        instance = args[0]
        namespace = getattr(instance, "guard_namespace", None) or getattr(
            instance, "EXCHANGE_SLUG", None
        ) or getattr(instance, "exchange_id", None) or getattr(instance, "name", None)
        if namespace:
            prefix, rest = base_name.split(":", 1)
            if namespace:
                return f"{str(namespace).lower()}:{rest}"
    return base_name


def net_guard(name: str) -> Callable:
    def deco(fn: Callable):
        is_coro = inspect.iscoroutinefunction(fn)

        @wraps(fn)
        async def async_wrapper(*args, **kwargs):
            resolved_name = _resolve_guard_name(name, args)
            bucket, breaker = get_guard(resolved_name)
            # Rate limit
            ex = resolved_name.split(':', 1)[0]
            method_label = 'NA'
            endpoint_label = 'NA'
            try:
                parts2 = resolved_name.split(':', 2)
                if len(parts2) >= 3:
                    method_label = 'REST' if 'rest' in parts2[1] else ('WS' if 'ws' in parts2[1] else parts2[1].upper())
                    endpoint_label = parts2[2]
                else:
                    m, p = _resolve_endpoint_from_fn(ex, fn.__name__)
                    method_label = m or 'NA'
                    endpoint_label = p or fn.__name__
            except Exception:
                pass

            if not bucket.consume(1.0):
                try:
                    inc_rate_drop(ex, endpoint_label)
                    rt.record_rate_drop(ex, endpoint_label)
                except Exception:
                    pass
                raise RuntimeError(f"rate_limited:{resolved_name}")
            status_label = 'OK'
            t0 = time.monotonic()
            try:
                res = await breaker.call_async(lambda *a, **k: fn(*a, **k), *args, **kwargs)
                return res
            except Exception:
                status_label = 'ERR'
                raise
            finally:
                dt = (time.monotonic() - t0) * 1000.0
                try:
                    inc_http(ex, method_label, endpoint_label, status_label)
                except Exception:
                    pass
                try:
                    rt.record_http_latency_ms(dt)
                except Exception:
                    pass
                try:
                    set_circuit(ex, endpoint_label, breaker.is_open())
                    rt.set_circuit_state(ex, endpoint_label, breaker.is_open())
                except Exception:
                    pass

        @wraps(fn)
        def sync_wrapper(*args, **kwargs):
            resolved_name = _resolve_guard_name(name, args)
            bucket, breaker = get_guard(resolved_name)
            # Rate limit
            ex = resolved_name.split(':', 1)[0]
            method_label = 'NA'
            endpoint_label = 'NA'
            try:
                parts2 = resolved_name.split(':', 2)
                if len(parts2) >= 3:
                    method_label = 'REST' if 'rest' in parts2[1] else ('WS' if 'ws' in parts2[1] else parts2[1].upper())
                    endpoint_label = parts2[2]
                else:
                    m, p = _resolve_endpoint_from_fn(ex, fn.__name__)
                    method_label = m or 'NA'
                    endpoint_label = p or fn.__name__
            except Exception:
                pass

            if not bucket.consume(1.0):
                try:
                    inc_rate_drop(ex, endpoint_label)
                    rt.record_rate_drop(ex, endpoint_label)
                except Exception:
                    pass
                raise RuntimeError(f"rate_limited:{resolved_name}")
            status_label = 'OK'
            t0 = time.monotonic()
            try:
                res = breaker.call(lambda: fn(*args, **kwargs))
                return res
            except Exception:
                status_label = 'ERR'
                raise
            finally:
                dt = (time.monotonic() - t0) * 1000.0
                try:
                    inc_http(ex, method_label, endpoint_label, status_label)
                except Exception:
                    pass
                try:
                    rt.record_http_latency_ms(dt)
                except Exception:
                    pass
                try:
                    set_circuit(ex, endpoint_label, breaker.is_open())
                    rt.set_circuit_state(ex, endpoint_label, breaker.is_open())
                except Exception:
                    pass

        if is_coro:
            return async_wrapper
        else:
            return sync_wrapper
    return deco

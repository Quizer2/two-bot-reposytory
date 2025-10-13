from dataclasses import dataclass
from typing import Dict, Any
import math, time, hashlib, os

@dataclass
class SymbolRules:
    min_qty: float
    step_size: float
    tick_size: float

class ExchangeAdapter:
    def __init__(self, rules: Dict[str, SymbolRules] | None=None, client_id_prefix:str="CB"):
        self.rules = rules or {}
        self.client_id_prefix = client_id_prefix

    def set_rules(self, symbol: str, min_qty: float, step_size: float, tick_size: float):
        self.rules[symbol.upper()] = SymbolRules(min_qty, step_size, tick_size)

    def _round_step(self, value: float, step: float) -> float:
        if step <= 0: 
            return value
        return math.floor(value / step) * step

    def normalize_order(self, symbol: str, side: str, qty: float, price: float | None) -> Dict[str, Any]:
        sym = symbol.upper()
        r = self.rules.get(sym)
        out = {"symbol": sym, "side": side}
        if r:
            q = max(qty, r.min_qty)
            q = self._round_step(q, r.step_size)
            out["qty"] = float(f"{q:.10f}")
            if price is not None:
                p = self._round_step(price, r.tick_size)
                out["price"] = float(f"{p:.10f}")
        else:
            out["qty"] = qty
            if price is not None:
                out["price"] = price
        return out

    def client_order_id(self, bot_id: str, symbol: str) -> str:
        nonce = int(time.time() * 1000)
        seed = f"{self.client_id_prefix}|{bot_id}|{symbol}|{nonce}|{os.getpid()}"
        digest = hashlib.sha1(seed.encode()).hexdigest()[:16]
        return f"{self.client_id_prefix}-{digest}"

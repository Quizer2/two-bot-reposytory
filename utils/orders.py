from typing import Optional, Dict, Any
from .adapters.exchange_adapter import ExchangeAdapter

def build_order(adapter: ExchangeAdapter, bot_id: str, symbol: str, side: str, qty: float, price: Optional[float]=None) -> Dict[str, Any]:
    norm = adapter.normalize_order(symbol, side, qty, price)
    cid = adapter.client_order_id(bot_id, norm['symbol'])
    norm['clientOrderId'] = cid
    return norm

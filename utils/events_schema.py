from pydantic import BaseModel, Field
from typing import Optional

class OrderSubmitted(BaseModel):
    bot_id: str
    symbol: str
    side: str  # 'buy' | 'sell'
    qty: float
    price: Optional[float] = None

class OrderFilled(BaseModel):
    bot_id: str
    order_id: str
    symbol: str
    qty: float
    price: float

class BotStatus(BaseModel):
    bot_id: str
    status: str  # 'starting'|'running'|'paused'|'stopped'|'error'
    message: Optional[str] = None

class MarketDataTick(BaseModel):
    symbol: str
    bid: float
    ask: float
    ts: int = Field(description="epoch millis")

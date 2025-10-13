"""Lightweight simulated exchange adapters used in offline tests."""

from __future__ import annotations

import asyncio
import itertools
from dataclasses import dataclass
from datetime import datetime
from typing import Dict, Optional

from utils.rate_limiter import RateLimitExceeded, RateLimiter


@dataclass
class SimulatedOrder:
    order_id: str
    symbol: str
    side: str
    amount: float
    price: Optional[float]
    order_type: str
    timestamp: datetime


class SimulatedExchangeAdapter:
    """Generic adapter mimicking a subset of the async exchange API."""

    def __init__(self, name: str, base_price: float = 100.0) -> None:
        self.name = name
        self.base_price = base_price
        self._balances: Dict[str, float] = {
            'USDT': 10_000.0,
            'BTC': 2.0,
            'ETH': 20.0,
        }
        self._orders: Dict[str, SimulatedOrder] = {}
        self._id_seq = itertools.count(1)
        self.request_delay = 0.1
        self.max_requests_per_second = 15
        self.rate_limiter = RateLimiter()
        self.rate_limiter.configure_scope(
            f"{self.name}:requests",
            limit=self.max_requests_per_second,
            period=1.0,
        )

    async def test_connection(self) -> bool:
        await asyncio.sleep(0)
        return True

    async def wait_for_rate_limit(self) -> None:
        try:
            self.rate_limiter.check(
                f"{self.name}:requests",
                metadata={"adapter": self.name},
            )
        except RateLimitExceeded:
            await asyncio.sleep(self.request_delay)
            try:
                self.rate_limiter.check(
                    f"{self.name}:requests",
                    metadata={"adapter": self.name, "recheck": True},
                )
            except RateLimitExceeded:
                # W warunkach testowych po prostu wstrzymaj się dodatkowo
                await asyncio.sleep(self.request_delay)

    async def get_server_time(self) -> datetime:
        await asyncio.sleep(0)
        return datetime.utcnow()

    async def get_balance(self, currency: Optional[str] = None):
        await asyncio.sleep(0)
        if currency:
            return {
                'free': float(self._balances.get(currency.upper(), 0.0)),
                'locked': 0.0,
                'total': float(self._balances.get(currency.upper(), 0.0)),
            }
        return {
            asset: {
                'free': float(amount),
                'locked': 0.0,
                'total': float(amount),
            }
            for asset, amount in self._balances.items()
        }

    async def get_current_price(self, symbol: str) -> float:
        await asyncio.sleep(0)
        return self.base_price

    async def place_order(
        self,
        symbol: str,
        side: str,
        amount: float,
        price: Optional[float] = None,
        order_type: str = 'market',
        **_: dict,
    ) -> Dict[str, object]:
        await self.wait_for_rate_limit()
        await asyncio.sleep(0)
        order_id = f"{self.name}-{next(self._id_seq)}"
        order = SimulatedOrder(
            order_id=order_id,
            symbol=symbol,
            side=side,
            amount=float(amount),
            price=price,
            order_type=order_type,
            timestamp=datetime.utcnow(),
        )
        self._orders[order_id] = order
        return {
            'order_id': order_id,
            'status': 'filled' if order_type == 'market' else 'open',
            'symbol': symbol,
            'side': side,
            'amount': float(amount),
            'price': price or self.base_price,
            'timestamp': order.timestamp.isoformat(),
            'success': True,
        }

    async def cancel_order(self, order_id: str) -> bool:
        await asyncio.sleep(0)
        return self._orders.pop(order_id, None) is not None

    async def get_order_status(self, order_id: str):
        await asyncio.sleep(0)
        order = self._orders.get(order_id)
        if not order:
            return None
        return {
            'order_id': order.order_id,
            'symbol': order.symbol,
            'side': order.side,
            'amount': order.amount,
            'price': order.price,
            'status': 'open',
            'timestamp': order.timestamp.isoformat(),
        }


__all__ = ['SimulatedExchangeAdapter', 'SimulatedOrder']

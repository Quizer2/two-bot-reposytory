"""
BaseExchange - clean abstract base class for all exchange adapters.
Corrupted decorators and indentation were removed and rebuilt safely.
"""

from __future__ import annotations

import asyncio
import time
import logging
logger = logging.getLogger(__name__)
from abc import ABC, abstractmethod
from typing import Dict, List, Optional, Any


class BaseExchange(ABC):
    def __init__(self, api_key: str, api_secret: str, testnet: bool = False):
        self.api_key = api_key
        self.api_secret = api_secret
        self.testnet = testnet
        self.session = None  # placeholder for aiohttp.ClientSession
        self.ws_connections: Dict[str, Any] = {}
        self.ws_callbacks: Dict[str, Any] = {}
        self.is_connected: bool = False
        self.min_request_interval: float = 0.2
        self.last_request_time: float = 0.0

    async def connect(self) -> None:
        """Establish connections/resources if needed."""
        self.is_connected = True
        self.last_request_time = time.time()

    async def disconnect(self) -> None:
        """Close resources and mark disconnected."""
        try:
            # Close websockets if any
            for _, ws in list(self.ws_connections.items()):
                try:
                    if hasattr(ws, "closed") and not ws.closed:
                        await ws.close()
                except Exception as e:
                    logger.warning(f"WebSocket close failed: {e}", exc_info=True)
            # After closing all websockets, clear maps
            self.ws_connections.clear()
            self.ws_callbacks.clear()
            # Close HTTP session
            if self.session:
                try:
                    await self.session.close()
                except Exception as e:
                    logger.debug(f"HTTP session close failed: {e}", exc_info=True)
                self.session = None
            self.is_connected = False
        except Exception as e:
            # Never let disconnect raise
            logger.warning(f"Disconnect encountered error but continuing: {e}", exc_info=True)

    async def rate_limit(self) -> None:
        """Ensure minimal interval between requests."""
        current_time = time.time()
        elapsed = current_time - self.last_request_time
        if elapsed < self.min_request_interval:
            await asyncio.sleep(self.min_request_interval - elapsed)
        self.last_request_time = time.time()

    # ---- Abstract interface ----
    @abstractmethod
    async def test_connection(self) -> bool:
        pass

    @abstractmethod
    async def load_exchange_info(self) -> None:
        pass

    @abstractmethod
    def generate_signature(self, params: str) -> str:
        pass

    @abstractmethod
    async def get_balance(self, currency: Optional[str] = None) -> Dict:
        pass

    @abstractmethod
    async def get_current_price(self, pair: str) -> float:
        pass

    @abstractmethod
    async def get_order_book(self, pair: str, limit: int = 50) -> Dict:
        pass

    @abstractmethod
    async def get_order_status(self, order_id: str) -> Dict:
        pass

    @abstractmethod
    async def get_open_orders(self, pair: Optional[str] = None) -> List[Dict]:
        pass

    @abstractmethod
    async def get_trade_history(self, pair: Optional[str] = None, limit: int = 100) -> List[Dict]:
        pass

    @abstractmethod
    async def get_klines(self, pair: str, interval: str = "1m", limit: int = 100) -> List[Dict]:
        pass

    @abstractmethod
    async def get_symbol_info(self, pair: str) -> Dict:
        pass

    @abstractmethod
    async def get_websocket_statistics(self) -> Dict:
        pass

    @abstractmethod
    async def get_exchange_name(self) -> str:
        pass

    @abstractmethod
    async def place_order(self, pair: str, side: str, order_type: str, quantity: float, price: Optional[float] = None) -> Dict:
        pass

    @abstractmethod
    async def cancel_order(self, order_id: str) -> bool:
        pass

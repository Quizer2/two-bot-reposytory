"""CCXT-based live exchange adapter implementation.

The adapter is intentionally lightweight – it only relies on ``ccxt``
(optional dependency) and exposes the minimal async interface required by
:mod:`core.trading_engine`.  When ``ccxt`` is not installed the caller
should fall back to the simulated adapter.  All potentially blocking
operations are delegated to the asyncio-friendly ``ccxt.async_support``
module so the adapter can be safely used inside the existing async flows.
"""

from __future__ import annotations

import asyncio
import logging
from typing import Any, Dict, Optional

logger = logging.getLogger(__name__)

try:  # pragma: no cover - optional production dependency
    import ccxt.async_support as ccxt_async  # type: ignore
except Exception:  # pragma: no cover - graceful degradation
    ccxt_async = None  # type: ignore


class LiveCCXTAdapter:
    """Thin wrapper around a ``ccxt`` exchange client."""

    def __init__(
        self,
        exchange_id: str,
        *,
        api_key: Optional[str] = None,
        secret: Optional[str] = None,
        password: Optional[str] = None,
        sandbox: bool = False,
        options: Optional[Dict[str, Any]] = None,
        loop: Optional[asyncio.AbstractEventLoop] = None,
    ) -> None:
        if ccxt_async is None:
            raise RuntimeError(
                "ccxt is required for live adapters – install the optional 'live' dependencies"
            )

        try:
            exchange_cls = getattr(ccxt_async, exchange_id)
        except AttributeError as exc:  # pragma: no cover - invalid exchange id
            raise ValueError(f"Exchange '{exchange_id}' is not supported by ccxt") from exc

        credentials: Dict[str, Any] = {"enableRateLimit": True}
        if api_key:
            credentials["apiKey"] = api_key
        if secret:
            credentials["secret"] = secret
        if password:
            credentials["password"] = password
        if options:
            credentials["options"] = options

        if loop is not None:
            self._loop = loop
        else:  # pragma: no cover - loop selection depends on runtime
            try:
                self._loop = asyncio.get_running_loop()
            except RuntimeError:
                self._loop = asyncio.new_event_loop()
        self._client = exchange_cls(credentials)
        if sandbox and hasattr(self._client, "set_sandbox_mode"):
            try:
                self._client.set_sandbox_mode(True)
            except Exception:  # pragma: no cover - defensive logging
                logger.exception("Sandbox mode enabling failed for %s", exchange_id)
        self.exchange_id = exchange_id

    # ------------------------------------------------------------------
    # Convenience helpers mirroring the simulated adapter API
    # ------------------------------------------------------------------
    async def test_connection(self) -> bool:
        try:
            await self._client.fetch_time()
            return True
        except Exception as exc:  # pragma: no cover - depends on network
            logger.error("Connection test for %s failed: %s", self.exchange_id, exc)
            return False

    async def get_balance(self, currency: Optional[str] = None) -> Dict[str, Any]:
        balances = await self._client.fetch_balance()
        if currency:
            asset = balances.get(currency) or {}
            return {
                "free": float(asset.get("free", 0.0)),
                "locked": float(asset.get("used", 0.0)),
                "total": float(asset.get("total", asset.get("free", 0.0))),
            }
        normalised: Dict[str, Any] = {}
        for asset, info in balances.items():
            if not isinstance(info, dict):
                continue
            normalised[asset] = {
                "free": float(info.get("free", 0.0)),
                "locked": float(info.get("used", 0.0)),
                "total": float(info.get("total", info.get("free", 0.0))),
            }
        return normalised

    async def get_current_price(self, symbol: str) -> float:
        ticker = await self._client.fetch_ticker(symbol)
        return float(ticker.get("last") or ticker.get("close") or ticker.get("ask") or 0.0)

    async def fetch_ticker(self, symbol: str) -> Dict[str, Any]:
        return await self._client.fetch_ticker(symbol)

    async def place_order(
        self,
        symbol: str,
        side: str,
        amount: float,
        price: Optional[float] = None,
        order_type: str = "market",
        **kwargs: Any,
    ) -> Dict[str, Any]:
        params = dict(kwargs or {})
        logger.debug(
            "Submitting live order: exchange=%s symbol=%s side=%s type=%s amount=%s price=%s",
            self.exchange_id,
            symbol,
            side,
            order_type,
            amount,
            price,
        )
        order = await self._client.create_order(symbol, order_type, side, amount, price, params)
        return {
            "id": order.get("id"),
            "status": order.get("status"),
            "symbol": order.get("symbol", symbol),
            "side": order.get("side", side),
            "amount": float(order.get("amount", amount)),
            "price": float(order.get("price", price or 0.0)),
            "timestamp": order.get("timestamp"),
            "info": order.get("info", {}),
        }

    async def cancel_order(self, order_id: str, symbol: Optional[str] = None) -> bool:
        try:
            await self._client.cancel_order(order_id, symbol)
            return True
        except Exception as exc:  # pragma: no cover - depends on exchange state
            logger.warning(
                "Cancel order failed on %s (order=%s, symbol=%s): %s",
                self.exchange_id,
                order_id,
                symbol,
                exc,
            )
            return False

    async def get_order_status(self, order_id: str, symbol: Optional[str] = None) -> Dict[str, Any]:
        order = await self._client.fetch_order(order_id, symbol)
        return {
            "order_id": order.get("id", order_id),
            "symbol": order.get("symbol", symbol),
            "status": order.get("status"),
            "price": order.get("price"),
            "amount": order.get("amount"),
            "filled": order.get("filled"),
            "remaining": order.get("remaining"),
        }

    async def get_open_orders(self, symbol: Optional[str] = None):
        return await self._client.fetch_open_orders(symbol)

    async def fetch_order_book(self, symbol: str, limit: Optional[int] = None) -> Dict[str, Any]:
        return await self._client.fetch_order_book(symbol, limit)

    async def fetch_ohlcv(
        self,
        symbol: str,
        *,
        timeframe: str = "1m",
        limit: int = 200,
    ) -> list[dict[str, Any]]:
        """Fetch OHLCV candles using the underlying ccxt client.

        The method normalises the response to a list of dictionaries so the
        rest of the application (including the dashboard and AI data
        provider) can consume it without depending on ccxt internals.
        """

        if not hasattr(self._client, "fetch_ohlcv"):
            raise RuntimeError(
                f"Exchange {self.exchange_id} does not expose fetch_ohlcv"
            )

        raw_candles = await self._client.fetch_ohlcv(
            symbol, timeframe=timeframe, limit=limit
        )
        normalised: list[dict[str, Any]] = []
        for entry in raw_candles or []:
            if not isinstance(entry, (list, tuple)) or len(entry) < 6:
                continue
            try:
                ts, o, h, l, c, v = entry[:6]
                normalised.append(
                    {
                        "timestamp": int(ts),
                        "open": float(o),
                        "high": float(h),
                        "low": float(l),
                        "close": float(c),
                        "volume": float(v),
                    }
                )
            except Exception:
                logger.debug("Skipping malformed OHLCV entry: %s", entry)
        return normalised

    async def close(self) -> None:
        try:
            await self._client.close()
        except Exception:  # pragma: no cover - best effort cleanup
            logger.debug("Closing ccxt client %s failed", self.exchange_id)

    # ------------------------------------------------------------------
    # Utilities
    # ------------------------------------------------------------------
    @classmethod
    def is_supported(cls) -> bool:
        return ccxt_async is not None


__all__ = ["LiveCCXTAdapter"]

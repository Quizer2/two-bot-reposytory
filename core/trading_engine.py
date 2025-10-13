"""Simplified trading engine with deterministic demo flow.

This module replaces the previously fragmented implementation with
an opinionated version that focuses on providing deterministic,
network-free behaviour for tests and local development.  The real
exchange integrations stay stubbed via exchange adapters – the engine
only needs them to expose a consistent async API.
"""

from __future__ import annotations

import asyncio
import logging
import os
import time
from dataclasses import dataclass, field, asdict
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple, Union

from app.exchange.adapter_factory import create_exchange_adapter
from app.exchange.live_ccxt_adapter import LiveCCXTAdapter
from utils.config_manager import get_config_manager
from utils.event_bus import EventTypes, get_event_bus
from utils.rate_limiter import RateLimitExceeded, RateLimiter

logger = logging.getLogger(__name__)


class OrderType(Enum):
    """Supported order types."""

    MARKET = "MARKET"
    LIMIT = "LIMIT"
    STOP_LOSS = "STOP_LOSS"
    TAKE_PROFIT = "TAKE_PROFIT"


class OrderSide(Enum):
    """Order direction."""

    BUY = "BUY"
    SELL = "SELL"


class OrderStatus(Enum):
    """Lifecycle states tracked for demo orders."""

    NEW = "NEW"
    PARTIALLY_FILLED = "PARTIALLY_FILLED"
    FILLED = "FILLED"
    CANCELED = "CANCELED"
    REJECTED = "REJECTED"
    EXPIRED = "EXPIRED"


@dataclass
class OrderRequest:
    """High level order request container used across the code base."""

    symbol: str
    side: OrderSide
    order_type: OrderType
    quantity: float
    price: Optional[float] = None
    stop_price: Optional[float] = None
    time_in_force: str = "GTC"
    client_order_id: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class OrderResponse:
    """Standardised response returned by :meth:`TradingEngine.place_order`."""

    success: bool
    order_id: str
    symbol: str
    side: OrderSide
    order_type: OrderType
    quantity: float
    price: Optional[float]
    status: OrderStatus
    filled_quantity: float
    remaining_quantity: float
    average_price: Optional[float]
    commission: float
    commission_asset: str
    timestamp: datetime
    error: Optional[str] = None
    client_order_id: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)

    def get(self, key: str, default: Any = None) -> Any:
        """Dictionary-like accessor used by legacy test helpers."""

        return getattr(self, key, default)

    def to_dict(self) -> Dict[str, Any]:
        """Return a serialisable representation for reporting."""

        payload = asdict(self)
        payload["side"] = self.side.value
        payload["order_type"] = self.order_type.value
        payload["status"] = self.status.value
        return payload


@dataclass
class Balance:
    asset: str
    free: float
    locked: float

    @property
    def total(self) -> float:
        return self.free + self.locked


@dataclass
class Trade:
    trade_id: str
    order_id: str
    symbol: str
    side: OrderSide
    quantity: float
    price: float
    commission: float
    commission_asset: str
    timestamp: datetime


class TradingEngine:
    """Core trading orchestration logic used by tests and bot managers."""

    def __init__(self) -> None:
        self.demo_mode: bool = True
        self.trading_mode: str = "auto"
        self.exchange_configs: Dict[str, Dict[str, Any]] = {}
        self._live_adapter_count: int = 0
        self.has_live_price_source: bool = False
        self.execute_live_orders: bool = False
        self.exchanges: Dict[str, Any] = {}
        self.active_orders: Dict[str, OrderResponse] = {}
        self.trade_history: List[Trade] = []
        self.balances: Dict[str, Balance] = {
            "USDT": Balance("USDT", free=10_000.0, locked=0.0),
            "BTC": Balance("BTC", free=1.0, locked=0.0),
            "ETH": Balance("ETH", free=10.0, locked=0.0),
        }
        self._order_sequence: int = 0
        self.event_bus = get_event_bus()
        self.rate_limiter = RateLimiter(self.event_bus)
        self._configure_rate_limits_from_config()
        self._load_exchange_configuration()
        self._install_exchange_adapters()

    # ------------------------------------------------------------------
    # Setup helpers
    # ------------------------------------------------------------------
    def configure_rate_limits(self, config: Optional[Dict[str, Any]] = None) -> None:
        """Applies provided konfiguracja limiterów (np. z UI)."""

        self.rate_limiter = RateLimiter(self.event_bus)
        self._apply_rate_limit_config(config or {})

    def get_rate_limit_snapshot(self) -> Dict[str, dict]:
        """Returns aktualne wykorzystanie limitów dla potrzeb UI/logowania."""

        return self.rate_limiter.snapshot()

    def _configure_rate_limits_from_config(self) -> None:
        try:
            cfg = get_config_manager().get_setting("trading", "rate_limiting", {}) or {}
        except Exception as exc:  # pragma: no cover - brak configu podczas testów jednostkowych
            logger.debug("Rate limit config unavailable, using defaults: %s", exc)
            cfg = {}
        self.configure_rate_limits(cfg)

    def _load_exchange_configuration(self) -> None:
        """Load trading/exchange configuration from config manager and env."""

        try:
            trading_cfg = get_config_manager().get_setting("trading") or {}
        except Exception:
            trading_cfg = {}

        env_mode = os.environ.get("TRADING_MODE")
        mode = str(env_mode or trading_cfg.get("mode") or "auto").lower()
        self.trading_mode = mode
        paper_trading = bool(trading_cfg.get("paper_trading", False))

        # Demo mode is disabled only if we explicitly run live and have live adapters.
        self.demo_mode = not (mode == "live" and not paper_trading)

        try:
            exchanges_cfg = get_config_manager().get_setting("exchanges") or {}
        except Exception:
            exchanges_cfg = {}

        available = exchanges_cfg.get("available") or []
        if isinstance(available, dict):
            available = list(available.keys())
        default_exchange = exchanges_cfg.get("default") or trading_cfg.get("default_exchange")

        if default_exchange and default_exchange not in available:
            available.insert(0, default_exchange)

        if not available:
            # Backwards compatibility – ensure at least one simulated adapter exists.
            available = [default_exchange or "binance"]

        for priority, exchange_name in enumerate(available, start=1):
            if not exchange_name:
                continue
            exchange_name = str(exchange_name).lower()
            self.exchange_configs.setdefault(
                exchange_name,
                {
                    "enabled": True,
                    "priority": priority,
                },
            )

    def _install_exchange_adapters(self) -> None:
        self._live_adapter_count = 0
        self.has_live_price_source = False
        try:
            loop = asyncio.get_running_loop()
        except RuntimeError:
            loop = None

        for name, cfg in self.exchange_configs.items():
            if not cfg.get("enabled", True):
                continue
            if name in self.exchanges:
                if isinstance(self.exchanges[name], LiveCCXTAdapter):
                    self._live_adapter_count += 1
                continue
            try:
                adapter = create_exchange_adapter(name, mode=self.trading_mode, event_loop=loop)
                self.register_exchange_adapter(name, adapter)
            except Exception as exc:
                logger.error("Failed to initialise adapter %s: %s", name, exc)

        self.execute_live_orders = self.trading_mode == "live" and self._live_adapter_count > 0
        if self.execute_live_orders:
            self.demo_mode = False
        else:
            self.demo_mode = True
            if self.trading_mode == "live":
                logger.warning("Live trading mode requested but no live adapters available – keeping demo mode")

    def _apply_rate_limit_config(self, config: Dict[str, Any]) -> None:
        def as_int(value: Any, default: int) -> int:
            try:
                return int(value)
            except Exception:
                return int(default)

        def as_float(value: Any, default: float) -> float:
            try:
                return float(value)
            except Exception:
                return float(default)

        global_cfg = config.get("global") or {}
        global_limit = max(as_int(global_cfg.get("limit", 60), 60), 1)
        global_period = max(as_float(global_cfg.get("period", 60.0), 60.0), 1.0)
        global_warning = as_float(global_cfg.get("warning_threshold", 0.8), 0.8)
        self.rate_limiter.configure_scope(
            "global",
            limit=global_limit,
            period=global_period,
            warning_threshold=global_warning,
        )

        wildcard_cfg = config.get("per_symbol_default") or {}
        wildcard_limit = wildcard_cfg.get("limit")
        wildcard_period = wildcard_cfg.get("period")
        if wildcard_limit is not None and wildcard_period is not None:
            self.rate_limiter.configure_scope(
                "symbol:*",
                limit=max(as_int(wildcard_limit, global_limit), 1),
                period=max(as_float(wildcard_period, global_period), 1.0),
                warning_threshold=as_float(wildcard_cfg.get("warning_threshold", global_warning), global_warning),
            )

        for symbol, cfg in (config.get("per_symbol") or {}).items():
            if not symbol:
                continue
            limit = cfg.get("limit", wildcard_limit if wildcard_limit is not None else global_limit)
            period = cfg.get("period", wildcard_period if wildcard_period is not None else global_period)
            warning = cfg.get(
                "warning_threshold",
                wildcard_cfg.get("warning_threshold", global_warning),
            )
            self.rate_limiter.configure_scope(
                f"symbol:{str(symbol).upper()}",
                limit=max(as_int(limit, global_limit), 1),
                period=max(as_float(period, global_period), 1.0),
                warning_threshold=as_float(warning, global_warning),
            )

    def _enforce_rate_limits(self, request: OrderRequest) -> None:
        metadata = {
            "symbol": request.symbol,
            "side": request.side.value,
            "client_order_id": request.client_order_id,
        }
        self.rate_limiter.check("global", metadata=metadata)
        self.rate_limiter.check("symbol:*", metadata=metadata)
        self.rate_limiter.check(f"symbol:{request.symbol}", metadata=metadata)

    def _build_rate_limited_response(self, request: OrderRequest, exc: RateLimitExceeded) -> OrderResponse:
        metadata = dict(request.metadata or {})
        metadata.setdefault(
            "rate_limit",
            {"scope": exc.scope, "limit": exc.limit, "period": exc.period},
        )
        return OrderResponse(
            success=False,
            order_id=f"rate_limited_{int(time.time() * 1000)}",
            symbol=request.symbol,
            side=request.side,
            order_type=request.order_type,
            quantity=request.quantity,
            price=request.price,
            status=OrderStatus.REJECTED,
            filled_quantity=0.0,
            remaining_quantity=request.quantity,
            average_price=None,
            commission=0.0,
            commission_asset="USDT",
            timestamp=datetime.utcnow(),
            error=str(exc),
            client_order_id=request.client_order_id,
            metadata=metadata,
        )

    async def initialize(self, exchange_configs: Optional[Dict[str, Dict[str, Any]]] = None) -> None:
        """Initialise the engine and probe configured exchanges."""

        if exchange_configs:
            self.exchange_configs.update(exchange_configs)

        for name, cfg in self.exchange_configs.items():
            if not cfg.get("enabled"):
                continue
            adapter = self.exchanges.get(name)
            if adapter is None:
                logger.warning("Exchange '%s' enabled but no adapter registered", name)
                continue
            try:
                result = await self._test_exchange_connection(adapter)
                if result:
                    logger.info("✅ Exchange %s connection verified", name)
                else:
                    logger.warning("⚠️ Exchange %s connection test failed", name)
            except Exception as exc:  # pragma: no cover - defensive logging
                logger.exception("Exchange %s connection probe failed: %s", name, exc)

    def register_exchange_adapter(self, name: str, adapter: Any) -> None:
        """Register an exchange adapter used in live mode."""

        self.exchanges[name.lower()] = adapter
        if isinstance(adapter, LiveCCXTAdapter):
            self._live_adapter_count += 1
            self.has_live_price_source = True

    # ------------------------------------------------------------------
    # Public API used by tests
    # ------------------------------------------------------------------
    async def place_order(
        self,
        order: Optional[Union[OrderRequest, Dict[str, Any]]] = None,
        **kwargs: Any,
    ) -> OrderResponse:
        """Place an order using either an :class:`OrderRequest` or keyword args."""

        if order is None:
            payload: Dict[str, Any] = {}
        elif isinstance(order, OrderRequest):
            payload = {
                "symbol": order.symbol,
                "side": order.side,
                "order_type": order.order_type,
                "quantity": order.quantity,
                "price": order.price,
                "stop_price": order.stop_price,
                "time_in_force": order.time_in_force,
                "client_order_id": order.client_order_id,
                "metadata": order.metadata,
            }
        elif isinstance(order, dict):
            payload = dict(order)
        else:  # pragma: no cover - unexpected usage
            raise TypeError("Unsupported order payload type")

        if kwargs:
            payload.update(kwargs)

        normalised = self._normalise_order_payload(payload)

        try:
            self._enforce_rate_limits(normalised)
        except RateLimitExceeded as exc:
            logger.warning("Order rejected due to rate limit: %s", exc)
            response = self._build_rate_limited_response(normalised, exc)
            self.event_bus.publish(EventTypes.ORDER_SUBMITTED, {**response.to_dict(), "rate_limited": True})
            return response

        if self.demo_mode:
            response = await self._place_demo_order(normalised)
        else:
            response = await self._route_to_exchange(normalised)

        self.active_orders[response.order_id] = response
        if response.status in (OrderStatus.FILLED, OrderStatus.PARTIALLY_FILLED):
            self._record_trade(response)
        self.event_bus.publish(EventTypes.ORDER_SUBMITTED, response.to_dict())
        return response

    async def submit_order(self, symbol: str, side: str, amount: float, **kwargs: Any) -> OrderResponse:
        """Legacy helper kept for backward compatibility."""

        return await self.place_order(
            symbol=symbol,
            side=side,
            quantity=amount,
            price=kwargs.get("price"),
            order_type=kwargs.get("order_type", "market"),
            client_order_id=kwargs.get("client_order_id"),
            metadata={k: v for k, v in kwargs.items() if k not in {"price", "order_type", "client_order_id"}},
        )

    async def cancel_order(self, order_id: str, symbol: Optional[str] = None) -> bool:
        response = self.active_orders.get(order_id)
        if not response:
            return False
        response.status = OrderStatus.CANCELED
        self.active_orders[order_id] = response
        logger.info("Order %s canceled", order_id)
        return True

    async def get_order_status(self, order_id: str, symbol: Optional[str] = None) -> Optional[OrderResponse]:
        return self.active_orders.get(order_id)

    async def get_open_orders(self, symbol: Optional[str] = None) -> List[OrderResponse]:
        orders = [o for o in self.active_orders.values() if o.status in {OrderStatus.NEW, OrderStatus.PARTIALLY_FILLED}]
        if symbol:
            orders = [o for o in orders if o.symbol == symbol]
        return orders

    async def get_balance(self, asset: str) -> Optional[Balance]:
        return self.balances.get(asset.upper())

    async def get_balances(self) -> Dict[str, Balance]:
        return dict(self.balances)

    async def get_trade_history(self, symbol: Optional[str] = None, limit: int = 100) -> List[Trade]:
        trades = self.trade_history if symbol is None else [t for t in self.trade_history if t.symbol == symbol]
        return trades[-limit:]

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------
    def _normalise_order_payload(self, payload: Dict[str, Any]) -> OrderRequest:
        if "symbol" not in payload:
            raise ValueError("Order payload requires 'symbol'")
        if "side" not in payload:
            raise ValueError("Order payload requires 'side'")
        quantity = payload.get("quantity")
        if quantity is None:
            quantity = payload.get("amount")
        if quantity is None:
            raise ValueError("Order payload requires 'quantity'")

        def _coerce_side(value: Any) -> OrderSide:
            if isinstance(value, OrderSide):
                return value
            return OrderSide.BUY if str(value).lower() == "buy" else OrderSide.SELL

        def _coerce_type(value: Any) -> OrderType:
            if isinstance(value, OrderType):
                return value
            mapping = {
                "market": OrderType.MARKET,
                "limit": OrderType.LIMIT,
                "stop_loss": OrderType.STOP_LOSS,
                "take_profit": OrderType.TAKE_PROFIT,
            }
            return mapping.get(str(value).lower(), OrderType.MARKET)

        metadata = payload.get("metadata") or {}
        if not isinstance(metadata, dict):  # pragma: no cover - defensive
            metadata = {"raw_metadata": metadata}

        return OrderRequest(
            symbol=str(payload["symbol"]).upper(),
            side=_coerce_side(payload["side"]),
            order_type=_coerce_type(payload.get("order_type", OrderType.MARKET)),
            quantity=float(quantity),
            price=None if payload.get("price") in (None, "") else float(payload.get("price")),
            stop_price=None if payload.get("stop_price") in (None, "") else float(payload.get("stop_price")),
            time_in_force=str(payload.get("time_in_force", "GTC")),
            client_order_id=payload.get("client_order_id"),
            metadata=metadata,
        )

    async def _place_demo_order(self, request: OrderRequest) -> OrderResponse:
        self._order_sequence += 1
        order_id = f"demo_{int(time.time() * 1000)}_{self._order_sequence}"
        live_price = await self._get_live_price(request.symbol) if self.has_live_price_source else None
        metadata = dict(request.metadata or {})
        if live_price is not None:
            metadata.setdefault("price_source", "live_market_data")
        else:
            metadata.setdefault("price_source", "simulated")
        if request.order_type is OrderType.MARKET:
            status = OrderStatus.FILLED
            filled_qty = request.quantity
            remaining = 0.0
            average_price = request.price or live_price or self._mock_price(request.symbol)
        else:
            status = OrderStatus.NEW
            filled_qty = 0.0
            remaining = request.quantity
            average_price = request.price or live_price

        commission_asset = "USDT"
        commission = filled_qty * 0.0005 if average_price else 0.0

        response = OrderResponse(
            success=True,
            order_id=order_id,
            symbol=request.symbol,
            side=request.side,
            order_type=request.order_type,
            quantity=request.quantity,
            price=request.price,
            status=status,
            filled_quantity=filled_qty,
            remaining_quantity=remaining,
            average_price=average_price,
            commission=commission,
            commission_asset=commission_asset,
            timestamp=datetime.utcnow(),
            client_order_id=request.client_order_id,
            metadata=metadata,
        )
        return response

    async def _route_to_exchange(self, request: OrderRequest) -> OrderResponse:
        """Attempt to submit an order via the first enabled adapter."""

        enabled = sorted(
            (name for name, cfg in self.exchange_configs.items() if cfg.get("enabled")),
            key=lambda name: self.exchange_configs[name].get("priority", 100),
        )
        live_adapters: List[Tuple[str, LiveCCXTAdapter]] = [
            (name, self.exchanges[name])
            for name in enabled
            if isinstance(self.exchanges.get(name), LiveCCXTAdapter)
        ]

        if not live_adapters:
            logger.warning("No live adapters available – using demo execution for %s", request.symbol)
            return await self._place_demo_order(request)

        if not self.execute_live_orders:
            price = await self._get_live_price(request.symbol, live_adapters)
            average_price = request.price or price or self._mock_price(request.symbol)
            metadata = dict(request.metadata or {})
            metadata.update(
                {
                    "executed": "paper",
                    "price_source": "live_market_data" if price is not None else metadata.get("price_source", "simulated"),
                }
            )
            return OrderResponse(
                success=True,
                order_id=f"paper_{int(time.time() * 1000)}",
                symbol=request.symbol,
                side=request.side,
                order_type=request.order_type,
                quantity=request.quantity,
                price=request.price,
                status=OrderStatus.FILLED,
                filled_quantity=request.quantity,
                remaining_quantity=0.0,
                average_price=average_price,
                commission=0.0,
                commission_asset="USDT",
                timestamp=datetime.utcnow(),
                client_order_id=request.client_order_id,
                metadata=metadata,
            )

        for name, adapter in live_adapters:
            try:
                result = await adapter.place_order(
                    symbol=request.symbol,
                    side=request.side.value.lower(),
                    amount=request.quantity,
                    price=request.price,
                    order_type=request.order_type.value.lower(),
                )
                payload = result if isinstance(result, dict) else {}
                return self._build_live_order_response(request, payload, name)
            except Exception as exc:  # pragma: no cover - depends on adapter behaviour
                logger.exception("Exchange %s order placement failed: %s", name, exc)

        logger.warning("Falling back to demo order placement for %s", request.symbol)
        return await self._place_demo_order(request)

    async def _get_live_price(
        self,
        symbol: str,
        adapters: Optional[List[Tuple[str, LiveCCXTAdapter]]] = None,
    ) -> Optional[float]:
        sources = adapters or [
            (name, adapter)
            for name, adapter in self.exchanges.items()
            if isinstance(adapter, LiveCCXTAdapter)
        ]
        for name, adapter in sources:
            try:
                ticker = await adapter.fetch_ticker(symbol)
                price = float(
                    ticker.get("last")
                    or ticker.get("close")
                    or ticker.get("ask")
                    or ticker.get("bid")
                    or 0.0
                )
                if price > 0:
                    return price
            except Exception as exc:
                logger.debug("Live price fetch failed for %s via %s: %s", symbol, name, exc)
        return None

    def _build_live_order_response(
        self, request: OrderRequest, result: Dict[str, Any], adapter_name: str
    ) -> OrderResponse:
        status_raw = str(result.get("status", "filled")).lower()
        status_map = {
            "open": OrderStatus.NEW,
            "new": OrderStatus.NEW,
            "closed": OrderStatus.FILLED,
            "filled": OrderStatus.FILLED,
            "canceled": OrderStatus.CANCELED,
            "cancelled": OrderStatus.CANCELED,
            "rejected": OrderStatus.REJECTED,
            "expired": OrderStatus.EXPIRED,
            "partial": OrderStatus.PARTIALLY_FILLED,
            "partially_filled": OrderStatus.PARTIALLY_FILLED,
        }
        status = status_map.get(status_raw, OrderStatus.FILLED)

        filled = float(result.get("filled") or result.get("amount") or (request.quantity if status == OrderStatus.FILLED else 0.0))
        remaining = max(request.quantity - filled, 0.0)
        average = result.get("average") or result.get("avgPrice") or result.get("price")
        try:
            average_price = float(average) if average not in (None, "") else None
        except Exception:
            average_price = None
        if average_price is None:
            average_price = request.price or self._mock_price(request.symbol)

        commission = float(result.get("fee") or 0.0)
        commission_asset = str(result.get("feeAsset") or result.get("fee_asset") or "USDT")

        metadata = dict(request.metadata or {})
        metadata.update(
            {
                "adapter": adapter_name,
                "live": True,
                "exchange_response": result,
            }
        )

        return OrderResponse(
            success=status not in {OrderStatus.REJECTED, OrderStatus.CANCELED, OrderStatus.EXPIRED},
            order_id=str(result.get("id") or result.get("order_id") or f"{adapter_name}_{int(time.time() * 1000)}"),
            symbol=request.symbol,
            side=request.side,
            order_type=request.order_type,
            quantity=request.quantity,
            price=request.price,
            status=status,
            filled_quantity=filled,
            remaining_quantity=remaining,
            average_price=average_price,
            commission=commission,
            commission_asset=commission_asset,
            timestamp=datetime.utcnow(),
            client_order_id=request.client_order_id,
            metadata=metadata,
        )

    async def _test_exchange_connection(self, adapter: Any) -> bool:
        if hasattr(adapter, "test_connection"):
            result = adapter.test_connection
            if asyncio.iscoroutinefunction(adapter.test_connection):  # type: ignore[union-attr]
                return bool(await adapter.test_connection())  # type: ignore[union-attr]
            if asyncio.iscoroutine(result):  # pragma: no cover - defensive
                return bool(await result)
            try:
                return bool(adapter.test_connection())  # type: ignore[operator]
            except TypeError:
                return bool(adapter.test_connection)  # type: ignore[misc]
        return True

    def _record_trade(self, response: OrderResponse) -> None:
        trade = Trade(
            trade_id=f"trade_{response.order_id}",
            order_id=response.order_id,
            symbol=response.symbol,
            side=response.side,
            quantity=response.filled_quantity,
            price=response.average_price or response.price or self._mock_price(response.symbol),
            commission=response.commission,
            commission_asset=response.commission_asset,
            timestamp=response.timestamp,
        )
        self.trade_history.append(trade)

    def _mock_price(self, symbol: str) -> float:
        base_prices = {
            "BTCUSDT": 50_000.0,
            "ETHUSDT": 3_000.0,
            "ADAUSDT": 1.5,
            "SOLUSDT": 150.0,
        }
        return base_prices.get(symbol.upper(), 100.0)


_trading_engine_instance: Optional[TradingEngine] = None


def get_trading_engine() -> TradingEngine:
    """Return a lazily created singleton instance."""

    global _trading_engine_instance
    if _trading_engine_instance is None:
        _trading_engine_instance = TradingEngine()
    return _trading_engine_instance


__all__ = [
    "TradingEngine",
    "OrderType",
    "OrderSide",
    "OrderStatus",
    "OrderRequest",
    "OrderResponse",
    "Balance",
    "Trade",
    "get_trading_engine",
]

"""Factory utilities for producing exchange adapters."""

from __future__ import annotations

import json
import logging
import os
from pathlib import Path
from typing import Any, Dict, Optional

from utils.config_manager import get_config_manager

try:  # pragma: no cover - optional dependency for tests
    from app.api_config_manager import get_api_config_manager
except Exception:  # pragma: no cover - fallback when manager is unavailable
    get_api_config_manager = None  # type: ignore

from .base_simulated_adapter import SimulatedExchangeAdapter
from .live_ccxt_adapter import LiveCCXTAdapter

logger = logging.getLogger(__name__)

_BASE_PRICE_MAP = {
    "binance": 50_000.0,
    "bybit": 50_100.0,
    "kucoin": 49_950.0,
    "coinbase": 50_050.0,
    "kraken": 49_900.0,
    "bitfinex": 50_200.0,
}


def _load_credentials(exchange: str) -> Dict[str, Any]:
    payload: Dict[str, Any] = {}

    if get_api_config_manager is not None:
        try:
            cfg = get_api_config_manager().get_exchange_config(exchange)
            if cfg:
                payload.update(
                    {
                        "api_key": cfg.get("api_key"),
                        "secret": cfg.get("secret"),
                        "password": cfg.get("passphrase") or cfg.get("password"),
                        "sandbox": cfg.get("sandbox", False),
                        "enabled": cfg.get("enabled", False),
                        "options": cfg.get("options", {}),
                    }
                )
        except Exception as exc:  # pragma: no cover - defensywne logowanie
            logger.debug("APIConfigManager unavailable for %s: %s", exchange, exc)

    credentials_file = Path("config/exchange_credentials.json")
    if credentials_file.exists():
        try:
            with credentials_file.open("r", encoding="utf-8") as handle:
                file_payload = json.load(handle)
        except Exception as exc:
            logger.error("Unable to read credentials file %s: %s", credentials_file, exc)
            file_payload = {}
        exchange_data = file_payload.get(exchange) or {}
        payload.setdefault("api_key", exchange_data.get("api_key"))
        payload.setdefault("secret", exchange_data.get("secret"))
        payload.setdefault("password", exchange_data.get("password"))
        payload.setdefault("sandbox", exchange_data.get("sandbox", False))
        payload.setdefault("options", exchange_data.get("options", {}))
        payload.setdefault("enabled", exchange_data.get("enabled", payload.get("enabled", False)))
    else:
        logger.info("Exchange credentials file %s missing – expecting env vars", credentials_file)

    payload.setdefault("api_key", os.environ.get(f"{exchange.upper()}_API_KEY"))
    payload.setdefault("secret", os.environ.get(f"{exchange.upper()}_API_SECRET"))
    payload.setdefault("password", os.environ.get(f"{exchange.upper()}_API_PASSWORD"))
    payload.setdefault("sandbox", False)
    payload.setdefault("options", {})
    payload.setdefault("enabled", True)
    return payload


def _resolve_mode(explicit_mode: Optional[str] = None) -> str:
    if explicit_mode:
        return explicit_mode

    try:
        trading_cfg = get_config_manager().get_setting("trading") or {}
    except Exception:
        trading_cfg = {}

    mode = str(trading_cfg.get("mode") or "auto").lower()
    paper_trading = bool(trading_cfg.get("paper_trading", False))
    if paper_trading and mode == "live":
        return "paper"
    return mode


def create_exchange_adapter(
    exchange: str,
    *,
    mode: Optional[str] = None,
    event_loop=None,
    intent: str = "trade",
) -> SimulatedExchangeAdapter | LiveCCXTAdapter:
    """Return an exchange adapter for the requested venue.

    Parameters
    ----------
    exchange:
        Nazwa giełdy (np. ``binance``).
    mode:
        Wymuszony tryb pracy.  Jeżeli ``None`` zostanie użyty tryb z konfiguracji.
    event_loop:
        Pętla asynchroniczna przekazywana do CCXT.
    intent:
        ``"trade"`` dla wykonywania zleceń lub ``"market_data"`` dla pobierania cen.
    """

    exchange = exchange.lower()
    resolved_mode = _resolve_mode(mode)

    credentials = _load_credentials(exchange)
    enabled = credentials.pop("enabled", True)
    has_keys = bool(credentials.get("api_key")) and bool(credentials.get("secret"))

    if intent != "market_data" and not enabled:
        logger.info("Exchange %s disabled in configuration – using simulated adapter", exchange)
        return SimulatedExchangeAdapter(exchange, base_price=_BASE_PRICE_MAP.get(exchange, 100.0))

    if resolved_mode in {"simulated", "paper"}:
        logger.info(
            "Initialising simulated adapter for %s in %s mode (intent=%s)",
            exchange,
            resolved_mode,
            intent,
        )
        return SimulatedExchangeAdapter(exchange, base_price=_BASE_PRICE_MAP.get(exchange, 100.0))

    if resolved_mode in {"live", "auto"}:
        if not LiveCCXTAdapter.is_supported():
            if resolved_mode == "live":
                raise RuntimeError("ccxt is not installed – cannot run in live trading mode")
            logger.warning("ccxt unavailable – falling back to simulated adapter for %s", exchange)
            return SimulatedExchangeAdapter(exchange, base_price=_BASE_PRICE_MAP.get(exchange, 100.0))

        if intent != "market_data" and not has_keys:
            if resolved_mode == "live":
                raise RuntimeError(
                    f"Missing API credentials for {exchange}. Populate config/exchange_credentials.json or environment variables"
                )
            logger.warning("Credentials missing for %s – using simulated adapter", exchange)
            return SimulatedExchangeAdapter(exchange, base_price=_BASE_PRICE_MAP.get(exchange, 100.0))

        logger.info("Initialising live adapter for %s in mode=%s", exchange, resolved_mode)
        filtered_credentials = {k: v for k, v in credentials.items() if v is not None}
        return LiveCCXTAdapter(exchange, loop=event_loop, **filtered_credentials)

    logger.warning("Unknown trading mode '%s' – using simulated adapter", resolved_mode)
    return SimulatedExchangeAdapter(exchange, base_price=_BASE_PRICE_MAP.get(exchange, 100.0))


__all__ = ["create_exchange_adapter"]


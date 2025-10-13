"""
Exchange adapters package (lazy imports).
"""

from __future__ import annotations

from importlib import import_module
import os
from typing import Dict, Type

from .base_exchange import BaseExchange
from utils.secure_store import get_exchange_credentials
import logging
logger = logging.getLogger(__name__)

# Map exchange names to (module, class) for lazy import
_AVAILABLE: Dict[str, tuple[str, str]] = {
    "binance": ("app.exchange.binance", "BinanceExchange"),
    "bybit": ("app.exchange.bybit", "BybitExchange"),
    "kucoin": ("app.exchange.kucoin", "KuCoinExchange"),
    "coinbase": ("app.exchange.coinbase", "CoinbaseExchange"),
    "kraken": ("app.exchange.kraken", "KrakenExchange"),
    "bitfinex": ("app.exchange.bitfinex", "BitfinexExchange"),
}

def get_exchange_adapter(exchange_name: str, **kwargs) -> BaseExchange:
    name = (exchange_name or "").lower()
    if name not in _AVAILABLE:
        raise ValueError(f"Unsupported exchange: {exchange_name}")
    mod_name, cls_name = _AVAILABLE[name]
    mod = import_module(mod_name)
    cls: Type[BaseExchange] = getattr(mod, cls_name)
    return cls(**kwargs)

# Factory expected by tests
def create_exchange(config: Dict) -> BaseExchange:
    name = (config.get('exchange') or '').lower()
    kwargs = {k: v for k, v in config.items() if k != 'exchange'}
    # Map 'sandbox' to constructor's 'testnet' for adapters
    if 'sandbox' in kwargs:
        kwargs['testnet'] = bool(kwargs.pop('sandbox'))
    # Prefer explicit config values; if missing and not public_only, load via secure store / env
    public_only = bool(config.get('public_only', False))
    testnet = bool(kwargs.get('testnet', False))
    if not public_only and name in _AVAILABLE:
        need_api_key = not kwargs.get('api_key')
        need_api_secret = not kwargs.get('api_secret')
        need_passphrase = not kwargs.get('passphrase')
        if need_api_key or need_api_secret or need_passphrase:
            try:
                master_pw = os.environ.get('CRYPTOBOT_MASTER_PASSWORD')
                creds = get_exchange_credentials(name, master_password=master_pw, testnet=testnet) or {}
                # merge only missing fields
                if need_api_key and creds.get('api_key'):
                    kwargs['api_key'] = creds['api_key']
                if need_api_secret and creds.get('api_secret'):
                    kwargs['api_secret'] = creds['api_secret']
                if need_passphrase and creds.get('passphrase'):
                    kwargs['passphrase'] = creds['passphrase']
            except Exception:
                # Do not fail here; let adapter handle missing credentials if public-only flows are allowed
                logger.debug("Secure store credentials load failed; continuing without credentials", exc_info=True)
    # Try instantiating; if adapter doesn't accept 'passphrase', retry without and set attribute post-creation
    try:
        return get_exchange_adapter(name, **kwargs)
    except TypeError:
        passphrase_val = kwargs.pop('passphrase', None)
        inst = get_exchange_adapter(name, **kwargs)
        if passphrase_val:
            try:
                setattr(inst, 'passphrase', passphrase_val)
            except Exception:
                # If adapter doesn't allow setting passphrase, silently ignore
                logger.debug("Adapter does not allow setting passphrase attribute; ignoring", exc_info=True)
        return inst

# Backward-compat alias
AVAILABLE_EXCHANGES = _AVAILABLE

__all__ = ["BaseExchange", "AVAILABLE_EXCHANGES", "get_exchange_adapter", "create_exchange"]

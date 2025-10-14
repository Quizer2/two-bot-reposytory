"""Binance adapter with automatic live/simulated selection."""

from __future__ import annotations

from typing import Any

from .adapter_factory import create_exchange_adapter


class BinanceAdapter:
    """Delegating wrapper returning the configured adapter implementation."""

    def __init__(self, *, mode: str | None = None, **kwargs: Any) -> None:
        self._delegate = create_exchange_adapter("binance", mode=mode, **kwargs)

    def __getattr__(self, item: str):
        return getattr(self._delegate, item)


__all__ = ["BinanceAdapter"]

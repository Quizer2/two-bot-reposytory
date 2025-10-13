"""Coinbase adapter delegating to live/simulated factory."""

from __future__ import annotations

from typing import Any

from .adapter_factory import create_exchange_adapter


class CoinbaseAdapter:
    def __init__(self, *, mode: str | None = None, **kwargs: Any) -> None:
        self._delegate = create_exchange_adapter("coinbase", mode=mode, **kwargs)

    def __getattr__(self, item: str):
        return getattr(self._delegate, item)


__all__ = ["CoinbaseAdapter"]

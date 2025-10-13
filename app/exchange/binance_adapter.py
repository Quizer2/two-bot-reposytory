"""Simplified Binance adapter used for offline integration tests."""

from __future__ import annotations

from .base_simulated_adapter import SimulatedExchangeAdapter


class BinanceAdapter(SimulatedExchangeAdapter):
    def __init__(self) -> None:
        super().__init__('binance', base_price=50000.0)


__all__ = ['BinanceAdapter']

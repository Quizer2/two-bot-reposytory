"""Simplified Coinbase adapter."""

from __future__ import annotations

from .base_simulated_adapter import SimulatedExchangeAdapter


class CoinbaseAdapter(SimulatedExchangeAdapter):
    def __init__(self) -> None:
        super().__init__('coinbase', base_price=49500.0)


__all__ = ['CoinbaseAdapter']

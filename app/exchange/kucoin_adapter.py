"""Simplified KuCoin adapter."""

from __future__ import annotations

from .base_simulated_adapter import SimulatedExchangeAdapter


class KuCoinAdapter(SimulatedExchangeAdapter):
    def __init__(self) -> None:
        super().__init__('kucoin', base_price=47000.0)


__all__ = ['KuCoinAdapter']

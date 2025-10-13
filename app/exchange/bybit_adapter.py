"""Simplified Bybit adapter."""

from __future__ import annotations

from .base_simulated_adapter import SimulatedExchangeAdapter


class BybitAdapter(SimulatedExchangeAdapter):
    def __init__(self) -> None:
        super().__init__('bybit', base_price=48000.0)


__all__ = ['BybitAdapter']

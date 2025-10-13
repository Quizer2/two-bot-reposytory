"""Prosty limiter zapytań wykorzystywany przez TradingEngine i adaptery."""
from __future__ import annotations

import time
from collections import defaultdict, deque
from dataclasses import dataclass
from typing import Deque, Dict, Optional

from utils.event_bus import get_event_bus, EventTypes


@dataclass
class _LimitConfig:
    limit: int
    period: float
    warning_threshold: float = 0.8


class RateLimitExceeded(RuntimeError):
    """Wyjątek rzucany, gdy przekroczono limit zapytań."""

    def __init__(self, scope: str, limit: int, period: float) -> None:
        super().__init__(f"Rate limit exceeded for {scope}: {limit}/{period}s")
        self.scope = scope
        self.limit = limit
        self.period = period


class RateLimiter:
    """Token bucket dla kontroli liczby żądań."""

    def __init__(self, event_bus=None) -> None:
        self._event_bus = event_bus or get_event_bus()
        self._limits: Dict[str, _LimitConfig] = {}
        self._hits: Dict[str, Deque[float]] = defaultdict(deque)

    def configure_scope(
        self,
        scope: str,
        *,
        limit: int,
        period: float,
        warning_threshold: float | None = None,
    ) -> None:
        """Rejestruje limit dla konkretnego zakresu."""

        if limit <= 0 or period <= 0:
            raise ValueError("Limit i okres muszą być dodatnie")
        threshold = warning_threshold if warning_threshold is not None else 0.8
        self._limits[scope] = _LimitConfig(limit=limit, period=period, warning_threshold=threshold)

    def clear_scope(self, scope: str) -> None:
        self._limits.pop(scope, None)
        self._hits.pop(scope, None)

    def check(self, scope: str, *, metadata: Optional[dict] = None) -> None:
        """Sprawdza i rejestruje użycie limitu.

        Raises:
            RateLimitExceeded: gdy limit został przekroczony.
        """

        config = self._limits.get(scope)
        if not config:
            return

        now = time.monotonic()
        bucket = self._hits[scope]
        while bucket and now - bucket[0] > config.period:
            bucket.popleft()

        usage = (len(bucket) + 1) / config.limit
        payload = {"scope": scope, "usage": min(usage, 1.0), "limit": config.limit, "period": config.period}
        if metadata:
            payload.update(metadata)

        if len(bucket) >= config.limit:
            self._event_bus.publish(EventTypes.RATE_LIMIT_BLOCKED, payload)
            raise RateLimitExceeded(scope, config.limit, config.period)

        bucket.append(now)

        if usage >= config.warning_threshold:
            self._event_bus.publish(EventTypes.RATE_LIMIT_WARNING, payload)

    def snapshot(self) -> Dict[str, dict]:
        """Zwraca aktualny stan wykorzystania limitów."""

        snapshot: Dict[str, dict] = {}
        now = time.monotonic()
        for scope, config in self._limits.items():
            bucket = self._hits.get(scope, deque())
            valid_hits = [hit for hit in bucket if now - hit <= config.period]
            snapshot[scope] = {
                "limit": config.limit,
                "period": config.period,
                "usage": len(valid_hits) / config.limit,
                "count": len(valid_hits),
            }
        return snapshot


__all__ = ["RateLimiter", "RateLimitExceeded"]

import time
from typing import Callable

class CircuitBreaker:
    def __init__(self, failure_threshold:int=5, recovery_time:float=30.0):
        self.failure_threshold = failure_threshold
        self.recovery_time = recovery_time
        self.failures = 0
        self.opened_at: float | None = None

    def is_open(self) -> bool:
        """Zwraca True jeśli wyłącznik jest otwarty (przerwa), False w przeciwnym wypadku."""
        if self.opened_at is None:
            return False
        # Jeśli minęło mniej niż recovery_time od otwarcia, obwód jest nadal otwarty
        return (time.time() - self.opened_at) < self.recovery_time

    def reset(self) -> None:
        """Zamyka wyłącznik i resetuje licznik błędów."""
        self.failures = 0
        self.opened_at = None

    def record_failure(self) -> None:
        """Rejestruje błąd i otwiera obwód po przekroczeniu progu."""
        self.failures += 1
        if self.failures >= self.failure_threshold:
            self.opened_at = time.time()

    def call(self, fn: Callable, *args, **kwargs):
        now = time.time()
        if self.opened_at is not None:
            if now - self.opened_at < self.recovery_time:
                raise RuntimeError("circuit_open")
            else:
                # half-open
                pass
        try:
            res = fn(*args, **kwargs)
            self.reset()
            return res
        except Exception:
            self.record_failure()
            raise

    async def call_async(self, fn: Callable, *args, **kwargs):
        """Asynchroniczna wersja wywołania przez wyłącznik."""
        now = time.time()
        if self.opened_at is not None:
            if now - self.opened_at < self.recovery_time:
                raise RuntimeError("circuit_open")
            else:
                # half-open
                pass
        try:
            res = await fn(*args, **kwargs)
            self.reset()
            return res
        except Exception:
            self.record_failure()
            raise

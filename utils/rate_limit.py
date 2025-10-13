import time
from typing import Optional

class TokenBucket:
    def __init__(self, rate_per_sec: float, capacity: Optional[float]=None):
        self.rate = rate_per_sec
        self.capacity = capacity if capacity is not None else rate_per_sec
        self.tokens = self.capacity
        self.last = time.monotonic()

    def consume(self, amount: float=1.0) -> bool:
        now = time.monotonic()
        elapsed = now - self.last
        self.last = now
        self.tokens = min(self.capacity, self.tokens + elapsed * self.rate)
        if self.tokens >= amount:
            self.tokens -= amount
            return True
        return False

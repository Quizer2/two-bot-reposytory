import time, threading

class TokenBucket:
    def __init__(self, rate_per_sec: float, capacity: int|float):
        self.rate = rate_per_sec
        self.capacity = capacity
        self.tokens = capacity
        self.timestamp = time.time()
        self.lock = threading.Lock()

    def consume(self, amount: float=1.0) -> bool:
        with self.lock:
            now = time.time()
            delta = now - self.timestamp
            self.timestamp = now
            self.tokens = min(self.capacity, self.tokens + delta*self.rate)
            if self.tokens >= amount:
                self.tokens -= amount
                return True
            return False

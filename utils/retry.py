import time
import random
from typing import Callable, Type, Tuple

def exponential_backoff(retries:int, base:float=0.5, cap:float=15.0, jitter:bool=True) -> float:
    d = min(cap, base * (2 ** retries))
    if jitter:
        d = random.uniform(0, d)
    return d

def retryable(fn: Callable, max_retries:int=5, exceptions:Tuple[Type[BaseException], ...]=(Exception,), on_retry:Callable[[int, BaseException], None] | None=None):
    def wrapper(*args, **kwargs):
        attempt = 0
        while True:
            try:
                return fn(*args, **kwargs)
            except exceptions as e:
                if attempt >= max_retries:
                    raise
                if on_retry:
                    try:
                        on_retry(attempt+1, e)
                    except Exception:
                        pass
                time.sleep(exponential_backoff(attempt))
                attempt += 1
    return wrapper

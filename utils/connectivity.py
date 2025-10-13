from typing import Callable, Any
from .retry import exponential_backoff
import time
from utils.logger import get_logger

class ConnectivityManager:
    def __init__(self, on_status: Callable[[str, bool], None] | None=None):
        self.on_status = on_status or (lambda name, ok: None)
        self.logger = get_logger(__name__)

    def update(self, name: str, ok: bool):
        try:
            self.on_status(name, ok)
        except Exception:
            # Logujemy błąd callbacku statusu zamiast cichego pominięcia
            self.logger.error("on_status callback failed", exc_info=True)

    def reconnect_loop(self, name: str, connect_fn: Callable[[], Any], max_retries:int=5):
        for attempt in range(max_retries+1):
            try:
                obj = connect_fn()
                self.update(name, True)
                return obj
            except Exception:
                self.update(name, False)
                delay = exponential_backoff(attempt)
                # Informacyjny log o próbie ponownego połączenia z opóźnieniem
                self.logger.warning(f"Reconnect attempt {attempt} for '{name}' failed. Retrying in {delay:.2f}s", exc_info=True)
                time.sleep(delay)
        # Po wyczerpaniu prób, zgłoś błąd
        self.logger.error(f"Failed to connect after {max_retries} retries: {name}")
        raise RuntimeError(f"Failed to connect: {name}")

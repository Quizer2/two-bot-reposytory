"""
EventBus - prosty system pub/sub dla komunikacji między komponentami
"""
import logging
from typing import Dict, List, Callable, Any
from threading import Lock

logger = logging.getLogger(__name__)

class EventBus:
    """Prosty system pub/sub dla komunikacji między komponentami"""
    
    def __init__(self):
        self._listeners: Dict[str, List[Callable]] = {}
        self._lock = Lock()
    
    def subscribe(self, event_type: str, callback: Callable[[Any], None]) -> None:
        """
        Subskrybuje zdarzenie
        
        Args:
            event_type: Typ zdarzenia (np. 'config.updated', 'risk.reloaded')
            callback: Funkcja callback do wywołania
        """
        with self._lock:
            if event_type not in self._listeners:
                self._listeners[event_type] = []
            # Idempotent subscription: avoid duplicates
            if callback in self._listeners[event_type]:
                logger.debug(f"Listener dla {event_type} już istnieje - pomijam duplikat")
            else:
                self._listeners[event_type].append(callback)
                logger.debug(f"Dodano listener dla {event_type}")
    
    def unsubscribe(self, event_type: str, callback: Callable[[Any], None]) -> None:
        """
        Usuwa subskrypcję zdarzenia
        
        Args:
            event_type: Typ zdarzenia
            callback: Funkcja callback do usunięcia
        """
        with self._lock:
            if event_type in self._listeners:
                try:
                    self._listeners[event_type].remove(callback)
                    logger.debug(f"Usunięto listener dla {event_type}")
                except ValueError:
                    logger.warning(f"Nie znaleziono listenera dla {event_type}")
    
    def publish(self, event_type: str, data: Any = None, **kwargs) -> None:
        """
        Publikuje zdarzenie

        Args:
            event_type: Typ zdarzenia
            data: Dane do przekazania listenerom
        """
        payload = data
        if payload is None and kwargs:
            payload = kwargs

        with self._lock:
            listeners = self._listeners.get(event_type, []).copy()

        logger.debug(f"Publikowanie zdarzenia {event_type} z danymi: {payload}")

        for callback in listeners:
            try:
                callback(payload)
            except Exception as e:
                logger.error(f"Błąd w callback dla {event_type}: {e}")
    
    def clear(self) -> None:
        """Usuwa wszystkich listenerów"""
        with self._lock:
            self._listeners.clear()
            logger.debug("Wyczyszczono wszystkich listenerów")
        # hook: allow re-installing default subscribers after clear
        try:
            _hook = get_on_cleared_hook()
            if _hook:
                _hook(get_event_bus())
        except Exception:
            pass
    
    def get_listeners_count(self, event_type: str = None) -> int:
        """
        Zwraca liczbę listenerów
        
        Args:
            event_type: Typ zdarzenia (None = wszystkie)
            
        Returns:
            Liczba listenerów
        """
        with self._lock:
            if event_type:
                return len(self._listeners.get(event_type, []))
            return sum(len(listeners) for listeners in self._listeners.values())

# Globalna instancja EventBus
_global_event_bus = None

# Hook po clear
_on_cleared_hook: Callable[[EventBus], None] | None = None

def register_on_cleared_hook(cb: Callable[[EventBus], None]) -> None:
    """Rejestruje callback wywoływany po wyczyszczeniu EventBus (bus.clear())."""
    global _on_cleared_hook
    _on_cleared_hook = cb


def get_on_cleared_hook() -> Callable[[EventBus], None] | None:
    return _on_cleared_hook


def get_event_bus() -> EventBus:
    """Zwraca globalną instancję EventBus (singleton)"""
    global _global_event_bus
    if _global_event_bus is None:
        _global_event_bus = EventBus()
    return _global_event_bus

# Convenience functions
def subscribe(event_type: str, callback: Callable[[Any], None]) -> None:
    """Subskrybuje zdarzenie w globalnym EventBus"""
    get_event_bus().subscribe(event_type, callback)

def unsubscribe(event_type: str, callback: Callable[[Any], None]) -> None:
    """Usuwa subskrypcję w globalnym EventBus"""
    get_event_bus().unsubscribe(event_type, callback)

def publish(event_type: str, data: Any = None, **kwargs) -> None:
    """Publikuje zdarzenie w globalnym EventBus"""
    get_event_bus().publish(event_type, data, **kwargs)

# Stałe dla typów zdarzeń
class EventTypes:
    """Stałe typów zdarzeń"""
    CONFIG_UPDATED = "config.updated"
    CONFIG_APP_UPDATED = "config.app.updated"
    CONFIG_UI_UPDATED = "config.ui.updated"
    CONFIG_RISK_UPDATED = "config.risk.updated"
    RISK_RELOADED = "risk.reloaded"
    ORDER_SUBMITTED = "order.submitted"
    ORDER_CANCELLED = "order.cancelled"
    BOT_STARTED = "bot.started"
    BOT_STOPPED = "bot.stopped"
    BOT_UPDATED = "bot.updated"
    DATA_UPDATED = "data.updated"
    RATE_LIMIT_WARNING = "rate.limit.warning"
    RATE_LIMIT_BLOCKED = "rate.limit.blocked"
    RISK_ALERT = "risk.alert"
    RISK_ESCALATION = "risk.escalation"
    AI_SNAPSHOT_READY = "ai.snapshot.ready"

from typing import Union
try:
    from pydantic import BaseModel as _PydanticBaseModel
except ImportError:
    _PydanticBaseModel = None


def publish_event(event: Union[str, object], payload: dict | None = None):
    """Helper: publish event from either a string or a Pydantic model instance.
    Obsługuje Pydantic v1 (dict) i v2 (model_dump). Gdy Pydantic niedostępny, wymaga nazwy typu jako string.
    """
    from . import event_bus
    if isinstance(event, str):
        event_bus.get_event_bus().publish(event, payload or {})
    elif _PydanticBaseModel is not None and isinstance(event, _PydanticBaseModel):
        name = event.__class__.__name__
        try:
            data = event.dict()  # Pydantic v1
        except Exception:
            try:
                data = event.model_dump()  # Pydantic v2
            except Exception:
                data = {}
        event_bus.get_event_bus().publish(name, data)
    else:
        raise TypeError(f"Unsupported event type: {type(event)}")


# --- audit logging hook ---
try:
    from .audit_log import log_event as _audit_log_event
except Exception:
    _audit_log_event = None

# Monkey-patch publish to also log JSONL (keep original behavior)
if hasattr(get_event_bus(), "publish"):
    _orig_publish = get_event_bus().publish
    def _wrapped_publish(event_name, payload=None, *args, **kwargs):
        if _audit_log_event is not None:
            try:
                audit_payload = payload
                if audit_payload is None and kwargs:
                    audit_payload = kwargs
                if not isinstance(audit_payload, dict):
                    audit_payload = {"data": str(audit_payload)}
                _audit_log_event(str(event_name), audit_payload)
            except Exception:
                pass
        return _orig_publish(event_name, payload, *args, **kwargs)
    get_event_bus().publish = _wrapped_publish

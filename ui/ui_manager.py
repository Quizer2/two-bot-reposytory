"""
UI Manager - Zarządzanie interfejsem użytkownika

Centralny manager do zarządzania wszystkimi komponentami UI,
koordynacji między widgetami i obsługi zdarzeń UI.
"""

import logging
from typing import Dict, List, Any, Optional, Callable
from datetime import datetime

try:
    from PyQt6.QtWidgets import QApplication, QMainWindow, QWidget
    from PyQt6.QtCore import QObject, pyqtSignal, QTimer
    PYQT_AVAILABLE = True
except ImportError:
    PYQT_AVAILABLE = False
    # Fallback classes for testing
    class QObject:
        pass
    class QMainWindow:
        pass
    class QWidget:
        pass

from utils.logger import get_logger, LogType
from utils.event_bus import get_event_bus, EventTypes
from utils.config_manager import get_config_manager

logger = get_logger("ui_manager", LogType.SYSTEM)

class UIManager(QObject):
    """
    Manager interfejsu użytkownika
    
    Zarządza wszystkimi komponentami UI, koordynuje komunikację
    między widgetami i obsługuje zdarzenia systemowe.
    """
    
    # Sygnały PyQt6
    if PYQT_AVAILABLE:
        ui_updated = pyqtSignal(str, dict)
        status_changed = pyqtSignal(str)
        error_occurred = pyqtSignal(str, str)
    
    def __init__(self, main_window=None):
        if PYQT_AVAILABLE:
            super().__init__()
        
        self.main_window = main_window
        self.config_manager = get_config_manager()
        self.event_bus = get_event_bus()
        
        # Rejestr komponentów UI
        self.ui_components: Dict[str, QWidget] = {}
        self.ui_callbacks: Dict[str, List[Callable]] = {
            'portfolio_update': [],
            'bot_status_update': [],
            'price_update': [],
            'market_data_update': [],
            'order_update': [],
            'risk_alert': [],
            'system_status_update': [],
            'notification': []
        }
        
        # Stan UI
        self.ui_state = {
            'current_tab': 'dashboard',
            'theme': 'dark',
            'notifications_enabled': True,
            'auto_refresh': True,
            'refresh_interval': 5000  # ms
        }
        
        # Timer do odświeżania UI
        if PYQT_AVAILABLE:
            self.refresh_timer = QTimer()
            self.refresh_timer.timeout.connect(self._refresh_ui)
        
        # Subskrypcje na zdarzenia systemowe
        self._setup_event_subscriptions()
        
        logger.info("UIManager initialized successfully")
    
    def _setup_event_subscriptions(self):
        """Konfiguruje subskrypcje na zdarzenia systemowe"""
        try:
            self.event_bus.subscribe(EventTypes.CONFIG_UPDATED, self._on_config_updated)
            self.event_bus.subscribe(EventTypes.BOT_UPDATED, self._on_bot_updated)
            self.event_bus.subscribe(EventTypes.BOT_STARTED, self._on_bot_status_changed)
            self.event_bus.subscribe(EventTypes.BOT_STOPPED, self._on_bot_status_changed)
            self.event_bus.subscribe(EventTypes.DATA_UPDATED, self._on_data_updated)
            
            logger.debug("Event subscriptions configured")
        except Exception as e:
            logger.error(f"Error setting up event subscriptions: {e}")
    
    def register_component(self, name: str, component: QWidget):
        """
        Rejestruje komponent UI
        
        Args:
            name: Nazwa komponentu
            component: Instancja komponentu UI
        """
        try:
            self.ui_components[name] = component
            logger.debug(f"Registered UI component: {name}")
            
            if PYQT_AVAILABLE:
                self.ui_updated.emit(name, {'action': 'registered'})
        except Exception as e:
            logger.error(f"Error registering component {name}: {e}")
    
    def unregister_component(self, name: str):
        """
        Usuwa rejestrację komponentu UI
        
        Args:
            name: Nazwa komponentu
        """
        try:
            if name in self.ui_components:
                del self.ui_components[name]
                logger.debug(f"Unregistered UI component: {name}")
                
                if PYQT_AVAILABLE:
                    self.ui_updated.emit(name, {'action': 'unregistered'})
        except Exception as e:
            logger.error(f"Error unregistering component {name}: {e}")
    
    def get_component(self, name: str) -> Optional[QWidget]:
        """
        Pobiera komponent UI
        
        Args:
            name: Nazwa komponentu
            
        Returns:
            Instancja komponentu lub None
        """
        return self.ui_components.get(name)
    
    def subscribe_to_updates(self, event_type: str, callback: Callable):
        """
        Subskrybuje aktualizacje UI
        
        Args:
            event_type: Typ zdarzenia
            callback: Funkcja callback
        """
        try:
            if event_type in self.ui_callbacks:
                self.ui_callbacks[event_type].append(callback)
                logger.debug(f"Added UI callback for {event_type}")
        except Exception as e:
            logger.error(f"Error subscribing to UI updates: {e}")
    
    def notify_ui_update(self, event_type: str, data: Any = None):
        """
        Powiadamia o aktualizacji UI
        
        Args:
            event_type: Typ zdarzenia
            data: Dane do przekazania
        """
        try:
            callbacks = self.ui_callbacks.get(event_type, [])
            for callback in callbacks:
                try:
                    callback(data)
                except Exception as e:
                    logger.error(f"Error in UI callback for {event_type}: {e}")
            
            if PYQT_AVAILABLE:
                self.ui_updated.emit(event_type, data or {})
                
        except Exception as e:
            logger.error(f"Error notifying UI update: {e}")
    
    def start_auto_refresh(self):
        """Uruchamia automatyczne odświeżanie UI"""
        try:
            if PYQT_AVAILABLE and self.ui_state['auto_refresh']:
                interval = self.ui_state['refresh_interval']
                self.refresh_timer.start(interval)
                logger.debug(f"Started auto-refresh with interval {interval}ms")
        except Exception as e:
            logger.error(f"Error starting auto-refresh: {e}")
    
    def stop_auto_refresh(self):
        """Zatrzymuje automatyczne odświeżanie UI"""
        try:
            if PYQT_AVAILABLE:
                self.refresh_timer.stop()
                logger.debug("Stopped auto-refresh")
        except Exception as e:
            logger.error(f"Error stopping auto-refresh: {e}")
    
    def _refresh_ui(self):
        """Odświeża wszystkie komponenty UI"""
        try:
            self.notify_ui_update('system_status_update', {
                'timestamp': datetime.now().isoformat(),
                'components_count': len(self.ui_components)
            })
        except Exception as e:
            logger.error(f"Error refreshing UI: {e}")
    
    def _on_config_updated(self, data):
        """Obsługuje zdarzenie aktualizacji konfiguracji"""
        try:
            logger.debug("Config updated - refreshing UI")
            self.notify_ui_update('portfolio_update', data)
        except Exception as e:
            logger.error(f"Error handling config update: {e}")
    
    def _on_bot_updated(self, data):
        """Obsługuje zdarzenie aktualizacji bota"""
        try:
            logger.debug("Bot updated - refreshing UI")
            self.notify_ui_update('bot_status_update', data)
        except Exception as e:
            logger.error(f"Error handling bot update: {e}")
    
    def _on_bot_status_changed(self, data):
        """Obsługuje zdarzenie zmiany statusu bota"""
        try:
            logger.debug("Bot status changed - refreshing UI")
            self.notify_ui_update('bot_status_update', data)
        except Exception as e:
            logger.error(f"Error handling bot status change: {e}")
    
    def _on_data_updated(self, data):
        """Obsługuje zdarzenie aktualizacji danych"""
        try:
            logger.debug("Data updated - refreshing UI")
            self.notify_ui_update('market_data_update', data)
        except Exception as e:
            logger.error(f"Error handling data update: {e}")
    
    def show_notification(self, title: str, message: str, notification_type: str = "info"):
        """
        Wyświetla powiadomienie
        
        Args:
            title: Tytuł powiadomienia
            message: Treść powiadomienia
            notification_type: Typ powiadomienia (info, warning, error, success)
        """
        try:
            notification_data = {
                'title': title,
                'message': message,
                'type': notification_type,
                'timestamp': datetime.now().isoformat()
            }
            
            self.notify_ui_update('notification', notification_data)
            logger.debug(f"Showed notification: {title}")
        except Exception as e:
            logger.error(f"Error showing notification: {e}")
    
    def get_ui_state(self) -> Dict[str, Any]:
        """
        Zwraca aktualny stan UI
        
        Returns:
            Słownik ze stanem UI
        """
        return self.ui_state.copy()
    
    def update_ui_state(self, updates: Dict[str, Any]):
        """
        Aktualizuje stan UI
        
        Args:
            updates: Słownik z aktualizacjami stanu
        """
        try:
            self.ui_state.update(updates)
            logger.debug(f"Updated UI state: {updates}")
            
            # Jeśli zmieniono interwał odświeżania, restart timer
            if 'refresh_interval' in updates and PYQT_AVAILABLE:
                if self.refresh_timer.isActive():
                    self.refresh_timer.stop()
                    self.refresh_timer.start(self.ui_state['refresh_interval'])
                    
        except Exception as e:
            logger.error(f"Error updating UI state: {e}")

# Globalna instancja UIManager
_ui_manager = None

def get_ui_manager(main_window=None) -> UIManager:
    """
    Zwraca globalną instancję UIManager (singleton)
    
    Args:
        main_window: Główne okno aplikacji (tylko przy pierwszym wywołaniu)
        
    Returns:
        Instancja UIManager
    """
    global _ui_manager
    if _ui_manager is None:
        _ui_manager = UIManager(main_window)
    return _ui_manager

def reset_ui_manager():
    """Resetuje globalną instancję UIManager (do testów)"""
    global _ui_manager
    _ui_manager = None
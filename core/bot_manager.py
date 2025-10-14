"""
Bot Manager - Zarządzanie botami tradingowymi

Centralny manager do zarządzania wszystkimi botami tradingowymi,
ich konfiguracją, uruchamianiem, zatrzymywaniem i monitorowaniem.
"""

import logging
import asyncio
from typing import Dict, List, Any, Optional, Callable
from datetime import datetime
from enum import Enum

from utils.logger import get_logger, LogType
from utils.event_bus import get_event_bus, EventTypes
from utils.config_manager import get_config_manager

logger = get_logger("bot_manager")

class BotStatus(Enum):
    """Status bota"""
    STOPPED = "stopped"
    STARTING = "starting"
    RUNNING = "running"
    STOPPING = "stopping"
    ERROR = "error"
    PAUSED = "paused"

class BotType(Enum):
    """Typ bota"""
    SCALPING = "scalping"
    SWING = "swing"
    ARBITRAGE = "arbitrage"
    GRID = "grid"
    DCA = "dca"
    CUSTOM = "custom"
    AI = "ai"

class BotManager:
    """
    Manager botów tradingowych
    
    Zarządza wszystkimi botami, ich konfiguracją, statusem
    i koordynuje ich działanie z innymi komponentami systemu.
    """
    
    def __init__(self, database_manager=None, exchange=None, notification_manager=None, data_manager=None):
        """
        Inicjalizuje BotManager
        
        Args:
            database_manager: Manager bazy danych
            exchange: Instancja giełdy
            notification_manager: Manager powiadomień
            data_manager: Manager danych
        """
        self.database_manager = database_manager
        self.exchange = exchange
        self.notification_manager = notification_manager
        self.data_manager = data_manager
        
        self.config_manager = get_config_manager()
        self.event_bus = get_event_bus()
        
        # Rejestr botów
        self.bots: Dict[str, Dict[str, Any]] = {}
        self.bot_configs: Dict[str, Dict[str, Any]] = {}
        self.bot_statistics: Dict[str, Dict[str, Any]] = {}
        
        # Callbacks dla zdarzeń botów
        self.bot_callbacks: Dict[str, List[Callable]] = {
            'bot_started': [],
            'bot_stopped': [],
            'bot_error': [],
            'bot_updated': [],
            'bot_profit': [],
            'bot_loss': []
        }
        
        # Globalne ustawienia
        self.global_settings = {
            'max_concurrent_bots': 10,
            'auto_restart_on_error': True,
            'emergency_stop_enabled': True,
            'risk_management_enabled': True,
            'logging_enabled': True
        }
        
        # Subskrypcje na zdarzenia systemowe
        self._setup_event_subscriptions()
        
        logger.info("BotManager initialized successfully")
    
    def _setup_event_subscriptions(self):
        """Konfiguruje subskrypcje na zdarzenia systemowe"""
        try:
            self.event_bus.subscribe(EventTypes.CONFIG_UPDATED, self._on_config_updated)
            self.event_bus.subscribe(EventTypes.RISK_RELOADED, self._on_risk_reloaded)
            self.event_bus.subscribe(EventTypes.DATA_UPDATED, self._on_data_updated)
            
            logger.debug("Event subscriptions configured")
        except Exception as e:
            logger.error(f"Error setting up event subscriptions: {e}")
    
    def create_bot(self, bot_id: str, bot_type: BotType, config: Dict[str, Any]) -> bool:
        """
        Tworzy nowego bota
        
        Args:
            bot_id: Unikalny identyfikator bota
            bot_type: Typ bota
            config: Konfiguracja bota
            
        Returns:
            True jeśli bot został utworzony pomyślnie
        """
        try:
            if bot_id in self.bots:
                logger.warning(f"Bot {bot_id} already exists")
                return False
            
            # Walidacja konfiguracji
            if not self._validate_bot_config(config):
                logger.error(f"Invalid configuration for bot {bot_id}")
                return False
            
            # Tworzenie bota
            bot_data = {
                'id': bot_id,
                'type': bot_type,
                'status': BotStatus.STOPPED,
                'created_at': datetime.now(),
                'last_updated': datetime.now(),
                'total_trades': 0,
                'successful_trades': 0,
                'total_profit': 0.0,
                'current_position': None,
                'error_count': 0,
                'last_error': None
            }
            
            self.bots[bot_id] = bot_data
            self.bot_configs[bot_id] = config.copy()
            self.bot_statistics[bot_id] = {
                'start_time': None,
                'uptime': 0,
                'trades_per_hour': 0,
                'win_rate': 0,
                'max_drawdown': 0,
                'sharpe_ratio': 0
            }
            
            logger.info(f"Created bot {bot_id} of type {bot_type.value}")
            self._notify_bot_event('bot_updated', bot_id, bot_data)
            
            return True
            
        except Exception as e:
            logger.error(f"Error creating bot {bot_id}: {e}")
            return False
    
    def start_bot(self, bot_id: str) -> bool:
        """
        Uruchamia bota
        
        Args:
            bot_id: Identyfikator bota
            
        Returns:
            True jeśli bot został uruchomiony pomyślnie
        """
        try:
            if bot_id not in self.bots:
                logger.error(f"Bot {bot_id} not found")
                return False
            
            bot = self.bots[bot_id]
            
            if bot['status'] == BotStatus.RUNNING:
                logger.warning(f"Bot {bot_id} is already running")
                return True
            
            # Sprawdzenie warunków uruchomienia
            if not self._can_start_bot(bot_id):
                logger.error(f"Cannot start bot {bot_id} - conditions not met")
                return False
            
            # Zmiana statusu
            bot['status'] = BotStatus.STARTING
            bot['last_updated'] = datetime.now()
            
            # Uruchomienie logiki bota (symulacja)
            success = self._start_bot_logic(bot_id)
            
            if success:
                bot['status'] = BotStatus.RUNNING
                self.bot_statistics[bot_id]['start_time'] = datetime.now()
                
                logger.info(f"Started bot {bot_id}")
                self._notify_bot_event('bot_started', bot_id, bot)
                self.event_bus.publish(EventTypes.BOT_STARTED, {'bot_id': bot_id})
                
                return True
            else:
                bot['status'] = BotStatus.ERROR
                bot['error_count'] += 1
                bot['last_error'] = "Failed to start bot logic"
                
                logger.error(f"Failed to start bot {bot_id}")
                self._notify_bot_event('bot_error', bot_id, bot)
                
                return False
                
        except Exception as e:
            logger.error(f"Error starting bot {bot_id}: {e}")
            if bot_id in self.bots:
                self.bots[bot_id]['status'] = BotStatus.ERROR
                self.bots[bot_id]['last_error'] = str(e)
            return False
    
    def stop_bot(self, bot_id: str) -> bool:
        """
        Zatrzymuje bota
        
        Args:
            bot_id: Identyfikator bota
            
        Returns:
            True jeśli bot został zatrzymany pomyślnie
        """
        try:
            if bot_id not in self.bots:
                logger.error(f"Bot {bot_id} not found")
                return False
            
            bot = self.bots[bot_id]
            
            if bot['status'] == BotStatus.STOPPED:
                logger.warning(f"Bot {bot_id} is already stopped")
                return True
            
            # Zmiana statusu
            bot['status'] = BotStatus.STOPPING
            bot['last_updated'] = datetime.now()
            
            # Zatrzymanie logiki bota
            success = self._stop_bot_logic(bot_id)
            
            if success:
                bot['status'] = BotStatus.STOPPED
                
                # Aktualizacja statystyk
                if self.bot_statistics[bot_id]['start_time']:
                    uptime = datetime.now() - self.bot_statistics[bot_id]['start_time']
                    self.bot_statistics[bot_id]['uptime'] += uptime.total_seconds()
                    self.bot_statistics[bot_id]['start_time'] = None
                
                logger.info(f"Stopped bot {bot_id}")
                self._notify_bot_event('bot_stopped', bot_id, bot)
                self.event_bus.publish(EventTypes.BOT_STOPPED, {'bot_id': bot_id})
                
                return True
            else:
                bot['status'] = BotStatus.ERROR
                bot['error_count'] += 1
                bot['last_error'] = "Failed to stop bot logic"
                
                logger.error(f"Failed to stop bot {bot_id}")
                return False
                
        except Exception as e:
            logger.error(f"Error stopping bot {bot_id}: {e}")
            return False
    
    def delete_bot(self, bot_id: str) -> bool:
        """
        Usuwa bota
        
        Args:
            bot_id: Identyfikator bota
            
        Returns:
            True jeśli bot został usunięty pomyślnie
        """
        try:
            if bot_id not in self.bots:
                logger.error(f"Bot {bot_id} not found")
                return False
            
            # Zatrzymanie bota jeśli jest uruchomiony
            if self.bots[bot_id]['status'] == BotStatus.RUNNING:
                self.stop_bot(bot_id)
            
            # Usunięcie bota
            del self.bots[bot_id]
            del self.bot_configs[bot_id]
            del self.bot_statistics[bot_id]
            
            logger.info(f"Deleted bot {bot_id}")
            return True
            
        except Exception as e:
            logger.error(f"Error deleting bot {bot_id}: {e}")
            return False
    
    def get_bot_status(self, bot_id: str) -> Optional[BotStatus]:
        """
        Pobiera status bota
        
        Args:
            bot_id: Identyfikator bota
            
        Returns:
            Status bota lub None jeśli bot nie istnieje
        """
        if bot_id in self.bots:
            return self.bots[bot_id]['status']
        return None
    
    def get_bot_info(self, bot_id: str) -> Optional[Dict[str, Any]]:
        """
        Pobiera informacje o bocie
        
        Args:
            bot_id: Identyfikator bota
            
        Returns:
            Słownik z informacjami o bocie lub None
        """
        if bot_id in self.bots:
            return {
                'bot': self.bots[bot_id].copy(),
                'config': self.bot_configs[bot_id].copy(),
                'statistics': self.bot_statistics[bot_id].copy()
            }
        return None
    
    def get_all_bots(self) -> Dict[str, Dict[str, Any]]:
        """
        Pobiera informacje o wszystkich botach
        
        Returns:
            Słownik z informacjami o wszystkich botach
        """
        result = {}
        for bot_id in self.bots:
            result[bot_id] = self.get_bot_info(bot_id)
        return result
    
    def get_running_bots(self) -> List[str]:
        """
        Pobiera listę uruchomionych botów
        
        Returns:
            Lista identyfikatorów uruchomionych botów
        """
        return [bot_id for bot_id, bot in self.bots.items() 
                if bot['status'] == BotStatus.RUNNING]
    
    def emergency_stop_all(self) -> bool:
        """
        Awaryjne zatrzymanie wszystkich botów
        
        Returns:
            True jeśli wszystkie boty zostały zatrzymane
        """
        try:
            logger.warning("Emergency stop initiated for all bots")
            
            running_bots = self.get_running_bots()
            success_count = 0
            
            for bot_id in running_bots:
                if self.stop_bot(bot_id):
                    success_count += 1
            
            logger.info(f"Emergency stop completed: {success_count}/{len(running_bots)} bots stopped")
            return success_count == len(running_bots)
            
        except Exception as e:
            logger.error(f"Error during emergency stop: {e}")
            return False
    
    def subscribe_to_bot_events(self, event_type: str, callback: Callable):
        """
        Subskrybuje zdarzenia botów
        
        Args:
            event_type: Typ zdarzenia
            callback: Funkcja callback
        """
        try:
            if event_type in self.bot_callbacks:
                self.bot_callbacks[event_type].append(callback)
                logger.debug(f"Added bot callback for {event_type}")
        except Exception as e:
            logger.error(f"Error subscribing to bot events: {e}")
    
    def _validate_bot_config(self, config: Dict[str, Any]) -> bool:
        """Waliduje konfigurację bota"""
        required_fields = ['symbol', 'strategy', 'risk_management']
        return all(field in config for field in required_fields)
    
    def _can_start_bot(self, bot_id: str) -> bool:
        """Sprawdza czy bot może zostać uruchomiony"""
        # Sprawdzenie limitu botów
        running_count = len(self.get_running_bots())
        if running_count >= self.global_settings['max_concurrent_bots']:
            return False
        
        # Sprawdzenie połączenia z giełdą
        if self.exchange and not hasattr(self.exchange, 'is_connected'):
            return False
        
        return True
    
    def _start_bot_logic(self, bot_id: str) -> bool:
        """Uruchamia logikę bota (symulacja)"""
        try:
            # Symulacja uruchomienia bota
            logger.debug(f"Starting bot logic for {bot_id}")
            return True
        except Exception as e:
            logger.error(f"Error in bot logic for {bot_id}: {e}")
            return False
    
    def _stop_bot_logic(self, bot_id: str) -> bool:
        """Zatrzymuje logikę bota (symulacja)"""
        try:
            # Symulacja zatrzymania bota
            logger.debug(f"Stopping bot logic for {bot_id}")
            return True
        except Exception as e:
            logger.error(f"Error stopping bot logic for {bot_id}: {e}")
            return False
    
    def _notify_bot_event(self, event_type: str, bot_id: str, data: Any):
        """Powiadamia o zdarzeniu bota"""
        try:
            callbacks = self.bot_callbacks.get(event_type, [])
            for callback in callbacks:
                try:
                    callback(bot_id, data)
                except Exception as e:
                    logger.error(f"Error in bot callback for {event_type}: {e}")
        except Exception as e:
            logger.error(f"Error notifying bot event: {e}")
    
    def _on_config_updated(self, data):
        """Obsługuje zdarzenie aktualizacji konfiguracji"""
        try:
            logger.debug("Config updated - checking bot configurations")
            # Aktualizacja konfiguracji botów jeśli potrzebna
        except Exception as e:
            logger.error(f"Error handling config update: {e}")
    
    def _on_risk_reloaded(self, data):
        """Obsługuje zdarzenie przeładowania zarządzania ryzykiem"""
        try:
            logger.debug("Risk management reloaded - updating bot risk settings")
            # Aktualizacja ustawień ryzyka dla botów
        except Exception as e:
            logger.error(f"Error handling risk reload: {e}")
    
    def _on_data_updated(self, data):
        """Obsługuje zdarzenie aktualizacji danych"""
        try:
            logger.debug("Data updated - notifying bots")
            self.event_bus.publish(EventTypes.BOT_UPDATED, {
                'timestamp': datetime.now().isoformat(),
                'data_update': data
            })
        except Exception as e:
            logger.error(f"Error handling data update: {e}")
    
    async def shutdown(self):
        """Zamyka BotManager i zatrzymuje wszystkie boty"""
        try:
            logger.info("Shutting down BotManager...")
            
            # Zatrzymaj wszystkie uruchomione boty
            running_bots = self.get_running_bots()
            for bot_id in running_bots:
                self.stop_bot(bot_id)
            
            # Wyczyść rejestry
            self.bots.clear()
            self.bot_configs.clear()
            self.bot_statistics.clear()
            
            logger.info("BotManager shutdown completed")
            
        except Exception as e:
            logger.error(f"Error during BotManager shutdown: {e}")

# Globalna instancja BotManager
_bot_manager = None

def get_bot_manager(database_manager=None, exchange=None, notification_manager=None, data_manager=None) -> BotManager:
    """
    Zwraca globalną instancję BotManager (singleton)
    
    Args:
        database_manager: Manager bazy danych (tylko przy pierwszym wywołaniu)
        exchange: Instancja giełdy (tylko przy pierwszym wywołaniu)
        notification_manager: Manager powiadomień (tylko przy pierwszym wywołaniu)
        data_manager: Manager danych (tylko przy pierwszym wywołaniu)
        
    Returns:
        Instancja BotManager
    """
    global _bot_manager
    if _bot_manager is None:
        _bot_manager = BotManager(database_manager, exchange, notification_manager, data_manager)
    return _bot_manager

def reset_bot_manager():
    """Resetuje globalną instancję BotManager (do testów)"""
    global _bot_manager
    _bot_manager = None
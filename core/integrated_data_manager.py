"""Integrated Data Manager - Centralny punkt zarządzania danymi z integracją wszystkich komponentów"""

import asyncio
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional, Callable
from dataclasses import dataclass

from .data_manager import DataManager, PortfolioData, BotData, RiskMetrics, LogEntry, AlertEntry, get_data_manager
from .portfolio_manager import PortfolioManager, PortfolioSummary
from .market_data_manager import MarketDataManager, PriceData
from .trading_engine import TradingEngine, OrderRequest, OrderResponse, Balance
from .strategy_engine import StrategyEngine, StrategyConfig, StrategyType, TradingSignal
from .updated_risk_manager import UpdatedRiskManager
from .unified_data_manager import UnifiedDataManager, get_unified_data_manager, UnifiedSystemStatus
import os
from utils.helpers import get_or_create_event_loop, schedule_coro_safely

logger = logging.getLogger(__name__)

@dataclass
class SystemStatus:
    """Status całego systemu"""
    initialized: bool
    trading_mode: str
    total_bots: int
    active_bots: int
    total_profit: float
    portfolio_value: float
    market_data_connected: bool
    trading_engine_ready: bool
    risk_manager_active: bool
    last_updated: datetime

class IntegratedDataManager:
    """
    Zintegrowany Manager Danych - centralny punkt komunikacji między wszystkimi komponentami
    
    Przepływ danych zgodnie z architekturą:
    UI Widgets → IntegratedDataManager → UnifiedDataManager → Komponenty Backend → Giełdy/Baza danych
    
    UWAGA: Ta klasa jest teraz wrapper'em dla UnifiedDataManager dla zachowania kompatybilności
    """
    
    def __init__(self, config_manager, database_manager, risk_manager: UpdatedRiskManager):
        self.config_manager = config_manager
        self.database_manager = database_manager
        self.risk_manager = risk_manager
        
        # Główny UnifiedDataManager
        self.unified_data_manager = get_unified_data_manager()
        
        # Kompatybilność - delegacja do UnifiedDataManager
        if self.unified_data_manager is not None:
            self.data_manager = self.unified_data_manager.data_manager
        else:
            # Fallback - utwórz podstawowy data_manager
            from .data_manager import get_data_manager
            self.data_manager = get_data_manager()
            logger.warning("UnifiedDataManager not available, using fallback DataManager")
        
        self.portfolio_manager = None  # Będzie ustawiony po inicjalizacji
        self.market_data_manager = None  # Będzie ustawiony po inicjalizacji
        self.trading_engine = None
        self.strategy_engine = None
        
        # Subskrypcje i callbacki
        self.ui_callbacks: Dict[str, List[Callable]] = {
            'portfolio_update': [],
            'bot_status_update': [],
            'price_update': [],
            'market_data_update': [],  # Dodany callback dla danych rynkowych
            'ticker_update': [],       # Dodany callback dla ticker
            'order_update': [],
            'risk_alert': [],
            'system_status_update': [],
            'strategy_signal': [],
            'strategy_execution': [],
            'balance_update': [],      # Dodany callback dla sald
            'transaction_update': [],  # Dodany callback dla transakcji
            'bot_created': [],         # Dodany callback dla nowych botów
            'bot_deleted': [],         # Dodany callback dla usuniętych botów
            'trade_update': []         # Dodany callback dla transakcji
        }
        
        # Cache i stan
        self.system_status = None
        self.last_portfolio_update = None
        self.last_price_updates: Dict[str, datetime] = {}
        
        # Flagi inicjalizacji
        self.initialized = False
        self.components_ready = {
            'data_manager': False,
            'portfolio_manager': False,
            'market_data_manager': False,
            'trading_engine': False,
            'strategy_engine': False
        }
        # Track background asyncio tasks for clean shutdown
        self._portfolio_task = None
        self._system_status_task = None
        
        # Flaga trybu produkcyjnego (z ConfigManager z fallbackiem do ENV)
        try:
            self.production_mode = bool(self.config_manager.get_setting("app", "production_mode", False))
        except Exception:
            env_val = os.environ.get("PRODUCTION_MODE", "false").lower()
            self.production_mode = env_val in ("1", "true", "yes")

    def _is_production_mode(self) -> bool:
        """Zwraca informację czy aplikacja działa w trybie produkcyjnym.
        Preferuje ustawienie z ConfigManager; fallback do zmiennych środowiskowych.
        """
        try:
            cfg_val = self.config_manager.get_setting("app", "production_mode", None)
            if cfg_val is not None:
                self.production_mode = bool(cfg_val)
                return self.production_mode
        except Exception as e:
            logger.debug(f"Error reading production_mode from config: {e}")
        env_val = os.environ.get("PRODUCTION_MODE")
        if env_val is not None:
            self.production_mode = env_val.lower() in ("1", "true", "yes")
            return self.production_mode
        # TEST_MODE oznacza środowisko testowe, nie produkcyjne
        test_mode = os.environ.get("TEST_MODE", "").lower() in ("1", "true", "yes", "startup")
        if test_mode:
            self.production_mode = False
            return False
        return bool(getattr(self, "production_mode", False))

    async def initialize(self, config: Dict[str, Any] = None):
        """Inicjalizuje wszystkie komponenty systemu przez UnifiedDataManager"""
        try:
            logger.info("Initializing IntegratedDataManager...")
            
            if self.unified_data_manager is not None:
                logger.info("Using UnifiedDataManager for initialization...")
                # 1. Inicjalizuj UnifiedDataManager (deleguje do wszystkich komponentów)
                success = await self.unified_data_manager.initialize(config)
                if not success:
                    raise Exception("Failed to initialize UnifiedDataManager")
                
                # 2. Ustaw referencje dla kompatybilności
                self.portfolio_manager = self.unified_data_manager.portfolio_manager
                self.market_data_manager = self.unified_data_manager.market_data_manager
                self.trading_engine = self.unified_data_manager.trading_engine
                self.strategy_engine = self.unified_data_manager.strategy_engine
                # Upewnij się, że data_manager został ustawiony po inicjalizacji UnifiedDataManager
                self.data_manager = self.unified_data_manager.data_manager
                
                # 3. Skopiuj status komponentów
                self.components_ready = self.unified_data_manager.components_ready.copy()
                # Upewnij się, że flaga data_manager odzwierciedla aktualny stan
                self.components_ready['data_manager'] = bool(self.data_manager)
                
                # 4. Skonfiguruj subskrypcje UI przez UnifiedDataManager
                for event_type, callbacks in self.ui_callbacks.items():
                    for callback in callbacks:
                        self.unified_data_manager.subscribe_to_ui_updates(event_type, callback)
            else:
                logger.warning("UnifiedDataManager not available, using fallback initialization...")
                # Fallback - inicjalizuj podstawowe komponenty
                await self.data_manager.initialize()
                self.components_ready['data_manager'] = True
                
                # Ustaw podstawowe komponenty jako None (będą obsłużone przez fallback metody)
                self.portfolio_manager = None
                self.market_data_manager = None
                self.trading_engine = None
                self.strategy_engine = None
            
            # 5. Skonfiguruj subskrypcje danych rynkowych (jeśli potrzeba)
            if self.market_data_manager:
                # Ustaw referencję do siebie dla propagacji danych (kompatybilność)
                if hasattr(self.market_data_manager, 'set_integrated_data_manager'):
                    self.market_data_manager.set_integrated_data_manager(self)
                await self._setup_market_data_subscriptions()
            
            # 6. Uruchom pętle aktualizacji
            loop = get_or_create_event_loop()
            self._portfolio_task = schedule_coro_safely(lambda: self._portfolio_update_loop())
            self._system_status_task = schedule_coro_safely(lambda: self._system_status_update_loop())
            
            self.initialized = True
            logger.info("IntegratedDataManager fully initialized")
            
            # Powiadom UI o inicjalizacji
            await self._notify_ui_callbacks('system_status_update', await self.get_system_status())
            
        except Exception as e:
            logger.error(f"Error initializing IntegratedDataManager: {e}")
            raise
    
    async def start_data_loops(self):
        """Uruchamia pętle aktualizacji danych"""
        try:
            logger.info("Starting data update loops...")
            
            # Uruchom pętle w tle
            loop = get_or_create_event_loop()
            self._portfolio_task = schedule_coro_safely(lambda: self._portfolio_update_loop())
            self._system_status_task = schedule_coro_safely(lambda: self._system_status_update_loop())
            
            logger.info("Data update loops started successfully")
            
        except Exception as e:
            logger.error(f"Error starting data loops: {e}")
            raise

    async def stop_data_loops(self):
        """Zatrzymuje pętle aktualizacji danych i czyści zadania"""
        try:
            # Ustaw flagę initialized na False aby przerwać pętle
            self.initialized = False
            tasks = [getattr(self, '_portfolio_task', None), getattr(self, '_system_status_task', None)]
            for t in tasks:
                try:
                    if t and not t.done():
                        t.cancel()
                        # Nie próbuj await na innym loopie
                        try:
                            current_loop = None
                            try:
                                current_loop = asyncio.get_running_loop()
                            except RuntimeError:
                                current_loop = None
                            task_loop = t.get_loop() if hasattr(t, 'get_loop') else None
                            if current_loop and task_loop and current_loop is task_loop:
                                await t
                        except asyncio.CancelledError:
                            pass
                        except Exception as e:
                            logger.warning(f"Error awaiting cancelled task: {e}")
                except Exception as e:
                    logger.warning(f"Error cancelling task: {e}")
            # Wyczyść referencje
            self._portfolio_task = None
            self._system_status_task = None
        except Exception as e:
            logger.error(f"Error stopping data loops: {e}")

    async def shutdown(self):
        """Gracefully shutdown IntegratedDataManager background activities"""
        try:
            await self.stop_data_loops()
            # Zatrzymaj MarketDataManager jeśli dostępny
            try:
                if self.market_data_manager and hasattr(self.market_data_manager, 'stop'):
                    await self.market_data_manager.stop()
            except Exception as e:
                logger.warning(f"Error stopping MarketDataManager: {e}")
        except Exception as e:
            logger.error(f"Error during IntegratedDataManager shutdown: {e}")
    
    # === METODY DLA UI WIDGETS ===
    
    def subscribe_to_updates(self, event_type: str, callback: Callable):
        """Subskrybuje aktualizacje dla UI widgets"""
        if event_type in self.ui_callbacks:
            self.ui_callbacks[event_type].append(callback)
            logger.info(f"UI subscribed to {event_type} updates")
            # Propaguj rejestrację także do UnifiedDataManager (spójność przepływu zdarzeń)
            try:
                if self.unified_data_manager is not None and hasattr(self.unified_data_manager, 'subscribe_to_ui_updates'):
                    self.unified_data_manager.subscribe_to_ui_updates(event_type, callback)
            except Exception as e:
                logger.warning(f"UnifiedDataManager subscribe_to_ui_updates failed: {e}")
    
    def unsubscribe_from_updates(self, event_type: str, callback: Callable):
        """Anuluje subskrypcję aktualizacji"""
        if event_type in self.ui_callbacks and callback in self.ui_callbacks[event_type]:
            self.ui_callbacks[event_type].remove(callback)
        # Propaguj wyrejestrowanie także do UnifiedDataManager
        try:
            if self.unified_data_manager is not None and hasattr(self.unified_data_manager, 'unsubscribe_from_ui_updates'):
                self.unified_data_manager.unsubscribe_from_ui_updates(event_type, callback)
        except Exception as e:
            logger.warning(f"UnifiedDataManager unsubscribe_from_ui_updates failed: {e}")
    
    def subscribe_to_ui_updates(self, event_type: str, callback: Callable):
        """Alias dla subscribe_to_updates - kompatybilność z UI komponentami"""
        self.subscribe_to_updates(event_type, callback)
    
    async def get_dashboard_data(self) -> Dict[str, Any]:
        """Pobiera dane dla Dashboard widget"""
        try:
            # Bezpieczny fallback, gdy komponenty nie są jeszcze dostępne
            if self.portfolio_manager is None or self.data_manager is None:
                logger.warning("PortfolioManager or DataManager not available - returning basic dashboard data")
                system_status = await self.get_system_status()
                return {
                    'portfolio': {
                        'total_value': 0.0,
                        'daily_change': 0.0,
                        'daily_change_percent': 0.0,
                        'profit_loss': 0.0,
                        'profit_loss_percent': 0.0
                    },
                    'bots': {
                        'total': 0,
                        'active': 0,
                        'total_profit': 0.0
                    },
                    'system': system_status,
                    'last_updated': datetime.now()
                }
            
            portfolio_summary = await self.portfolio_manager.get_portfolio_summary()
            dm = getattr(self, 'data_manager', None)
            bots_data = []
            try:
                if dm is not None and hasattr(dm, 'get_bots_data'):
                    bots_data = await dm.get_bots_data()
            except Exception as e:
                logger.warning(f"get_bots_data failed, using empty list: {e}")
                bots_data = []
            system_status = await self.get_system_status()
            
            return {
                'portfolio': {
                    'total_value': portfolio_summary.total_value if portfolio_summary else 0.0,
                    'daily_change': portfolio_summary.daily_change if portfolio_summary else 0.0,
                    'daily_change_percent': portfolio_summary.daily_change_percent if portfolio_summary else 0.0,
                    'profit_loss': portfolio_summary.total_profit_loss if portfolio_summary else 0.0,
                    'profit_loss_percent': portfolio_summary.total_profit_loss_percent if portfolio_summary else 0.0
                },
                'bots': {
                    'total': len(bots_data),
                    'active': len([bot for bot in bots_data if getattr(bot, 'active', False)]),
                    'total_profit': sum(getattr(bot, 'profit', 0.0) for bot in bots_data)
                },
                'system': system_status,
                'last_updated': datetime.now()
            }
            
        except Exception as e:
            logger.error(f"Error getting dashboard data: {e}")
            return {}
    
    async def get_portfolio_summary(self):
        """Pobiera podsumowanie portfolio - wymagane przez UpdatedRiskManager"""
        try:
            return await self.portfolio_manager.get_portfolio_summary()
        except Exception as e:
            logger.error(f"Error getting portfolio summary: {e}")
            return None
    
    async def get_portfolio_positions(self):
        """Pobiera pozycje portfolio - wymagane przez UpdatedRiskManager"""
        try:
            portfolio_summary = await self.portfolio_manager.get_portfolio_summary()
            return portfolio_summary.positions if portfolio_summary else []
        except Exception as e:
            logger.error(f"Error getting portfolio positions: {e}")
            return []
    
    async def get_portfolio_widget_data(self) -> Dict[str, Any]:
        """Pobiera dane dla Portfolio widget"""
        try:
            # Sprawdź czy komponenty są dostępne
            if self.portfolio_manager is None or self.trading_engine is None:
                logger.warning("Portfolio manager or trading engine not available - returning empty portfolio widget data")
                return {
                    'summary': None,
                    'balances': [],
                    'positions': [],
                    'last_updated': datetime.now()
                }
            
            portfolio_summary = await self.portfolio_manager.get_portfolio_summary()
            balances = await self.trading_engine.get_balances()
            
            return {
                'summary': portfolio_summary,
                'balances': balances,
                'positions': portfolio_summary.positions if portfolio_summary else [],
                'last_updated': datetime.now()
            }
            
        except Exception as e:
            logger.error(f"Error getting portfolio widget data: {e}")
            return {
                'summary': None,
                'balances': [],
                'positions': [],
                'last_updated': datetime.now()
            }
    
    async def get_bot_management_data(self) -> Dict[str, Any]:
        """Pobiera dane dla Bot Management widget"""
        try:
            dm = getattr(self, 'data_manager', None)
            bots_data = []
            trading_mode = 'unknown'
            try:
                if dm is not None and hasattr(dm, 'get_bots_data'):
                    bots_data = await dm.get_bots_data()
                if dm is not None and hasattr(dm, 'get_trading_mode'):
                    trading_mode = await dm.get_trading_mode()
            except Exception as e:
                logger.warning(f"DataManager not ready in get_bot_management_data: {e}")
            
            return {
                'bots': bots_data,
                'trading_mode': trading_mode,
                'last_updated': datetime.now()
            }
            
        except Exception as e:
            logger.error(f"Error getting bot management data: {e}")
            return {}
    
    async def get_bots_data(self, limit: int = 100) -> List[BotData]:
        """Deleguje pobieranie danych botów do DataManager dla kompatybilności z UI."""
        try:
            dm = getattr(self, 'data_manager', None)
            if dm is not None and hasattr(dm, 'get_bots_data'):
                return await dm.get_bots_data(limit)
            logger.warning("DataManager does not provide get_bots_data; returning empty list")
            return []
        except Exception as e:
            logger.warning(f"get_bots_data delegate failed: {e}")
            return []
    
    async def _get_sample_bots_data(self, limit: int = 100) -> List[BotData]:
        """Usunięte generowanie danych przykładowych – zwraca pustą listę."""
        return []
    
    async def get_recent_trades(self, limit: int = 50) -> List[Dict[str, Any]]:
        """Pobiera ostatnie transakcje dla UI.
        Próbuje delegować do DataManager (lub UnifiedDataManager), a w razie błędu zwraca lokalny fallback.
        """
        try:
            # Preferuj UnifiedDataManager jeśli dostępny i posiada DataManager z metodą
            if getattr(self, 'unified_data_manager', None) is not None:
                udm = self.unified_data_manager
                dm = getattr(udm, 'data_manager', None)
                if dm is not None and hasattr(dm, 'get_recent_trades'):
                    return await dm.get_recent_trades(limit)
            
            # Fallback do lokalnego DataManager
            if getattr(self, 'data_manager', None) is not None and hasattr(self.data_manager, 'get_recent_trades'):
                return await self.data_manager.get_recent_trades(limit)
            
            # Ostateczny fallback: w trybie produkcyjnym zwróć pustą listę zamiast sample
            if self._is_production_mode():
                logger.info("Production mode enabled: disabling sample recent trades fallback")
                return []
            return self._get_sample_trades(limit)
        except Exception as e:
            logger.error(f"Error getting recent trades: {e}")
            # W trybie produkcyjnym nie zwracaj sample
            if self._is_production_mode():
                return []
            return self._get_sample_trades(limit)
    
    def _get_sample_trades(self, limit: int = 10) -> List[Dict[str, Any]]:
        """Szybki fallback: przykładowe transakcje w formacie zgodnym z tabelą UI"""
        try:
            # Blokuj sample w trybie produkcyjnym
            if self._is_production_mode():
                return []
            now = datetime.now()
            sample = [
                {
                    'time': (now - timedelta(minutes=5)).strftime('%H:%M:%S'),
                    'bot': 'Scalper',
                    'pair': 'BTC/USDT',
                    'side': 'BUY',
                    'amount': 0.010,
                    'price': 42500.0
                },
                {
                    'time': (now - timedelta(minutes=15)).strftime('%H:%M:%S'),
                    'bot': 'DCA',
                    'pair': 'ETH/USDT',
                    'side': 'SELL',
                    'amount': 0.50,
                    'price': 2800.0
                }
            ]
            return sample[:limit]
        except Exception:
            return []
    
    # === METODY DLA BOTÓW I STRATEGY ENGINE ===
    
    async def execute_trade_order(self, bot_id: str, order_request: OrderRequest) -> OrderResponse:
        """Wykonuje zlecenie handlowe dla bota (przez RiskManager)"""
        try:
            # Tutaj powinno być sprawdzenie przez RiskManager
            # Na razie bezpośrednio do TradingEngine
            
            logger.info(f"Executing trade order for bot {bot_id}: {order_request.symbol} {order_request.side.value}")
            
            # Wykonaj zlecenie
            order_response = await self.trading_engine.place_order(order_request)
            
            # Aktualizuj portfolio jeśli zlecenie wykonane
            if order_response.status.value in ['FILLED', 'PARTIALLY_FILLED']:
                await self.portfolio_manager.update_position(
                    symbol=order_response.symbol,
                    amount=order_response.filled_quantity,
                    price=order_response.average_price or 0,
                    transaction_type="buy" if order_response.side.value == "BUY" else "sell"
                )
                
                # Powiadom UI o aktualizacji portfolio
                portfolio_data = await self.get_portfolio_widget_data()
                await self._notify_ui_callbacks('portfolio_update', portfolio_data)
            
            # Powiadom UI o zleceniu
            await self._notify_ui_callbacks('order_update', {
                'bot_id': bot_id,
                'order': order_response,
                'timestamp': datetime.now()
            })
            
            return order_response
            
        except Exception as e:
            logger.error(f"Error executing trade order for bot {bot_id}: {e}")
            raise
    
    async def get_market_data_for_bot(self, bot_id: str, symbol: str) -> Optional[PriceData]:
        """Pobiera dane rynkowe dla bota"""
        try:
            return await self.market_data_manager.get_current_price(symbol)
            
        except Exception as e:
            logger.error(f"Error getting market data for bot {bot_id}, symbol {symbol}: {e}")
            return None
    
    async def update_bot_status(self, bot_id: str, status: str, active: bool = None):
        """Aktualizuje status bota"""
        try:
            await self.data_manager.update_bot_status(bot_id, status, active)
            
            # Powiadom UI o zmianie statusu
            bot_data = await self.get_bot_management_data()
            await self._notify_ui_callbacks('bot_status_update', bot_data)
            
        except Exception as e:
            logger.error(f"Error updating bot status: {e}")
    
    # === STRATEGY ENGINE METHODS ===
    
    async def register_strategy(self, bot_id: str, strategy_config: StrategyConfig) -> bool:
        """Zarejestruj strategię dla bota"""
        try:
            return await self.strategy_engine.register_strategy(bot_id, strategy_config)
        except Exception as e:
            logger.error(f"Błąd rejestracji strategii dla bota {bot_id}: {e}")
            return False
    
    async def start_strategy(self, bot_id: str) -> bool:
        """Uruchom strategię dla bota"""
        try:
            return await self.strategy_engine.start_strategy(bot_id)
        except Exception as e:
            logger.error(f"Błąd uruchamiania strategii dla bota {bot_id}: {e}")
            return False
    
    async def stop_strategy(self, bot_id: str) -> bool:
        """Zatrzymaj strategię dla bota"""
        try:
            return await self.strategy_engine.stop_strategy(bot_id)
        except Exception as e:
            logger.error(f"Błąd zatrzymywania strategii dla bota {bot_id}: {e}")
            return False
    
    async def get_strategy_state(self, bot_id: str) -> Optional[Dict[str, Any]]:
        """Pobierz stan strategii"""
        try:
            return await self.strategy_engine.get_strategy_state(bot_id)
        except Exception as e:
            logger.error(f"Błąd pobierania stanu strategii dla bota {bot_id}: {e}")
            return None
    
    async def update_strategy_config(self, bot_id: str, config: StrategyConfig) -> bool:
        """Zaktualizuj konfigurację strategii"""
        try:
            return await self.strategy_engine.update_strategy_config(bot_id, config)
        except Exception as e:
            logger.error(f"Błąd aktualizacji konfiguracji strategii dla bota {bot_id}: {e}")
            return False
    
    # === METODY DLA USTAWIEŃ ===
    
    async def update_risk_settings(self, settings: Dict[str, Any]):
        """Aktualizuje ustawienia ryzyka"""
        try:
            await self.data_manager.update_risk_settings(settings)
            logger.info("Risk settings updated")
            
        except Exception as e:
            logger.error(f"Error updating risk settings: {e}")
    
    async def update_trading_mode(self, mode: str):
        """Aktualizuje tryb handlowy"""
        try:
            await self.data_manager.update_trading_mode(mode)
            logger.info(f"Trading mode updated to: {mode}")
            
            # Powiadom UI
            system_status = await self.get_system_status()
            await self._notify_ui_callbacks('system_status_update', system_status)
            
        except Exception as e:
            logger.error(f"Error updating trading mode: {e}")
    
    # === METODY WEWNĘTRZNE ===
    
    async def _setup_market_data_subscriptions(self):
        """Konfiguruje subskrypcje danych rynkowych"""
        try:
            # Jeśli MarketDataManager już propaguje dane do IDM, nie rób manualnych subskrypcji
            if hasattr(self, 'market_data_manager') and self.market_data_manager and \
               hasattr(self.market_data_manager, 'integrated_data_manager') and \
               self.market_data_manager.integrated_data_manager is self:
                logger.info("Market data propagation enabled - manual subscriptions skipped")
                # Skonfiguruj callbacki Strategy Engine mimo wszystko
                await self._setup_callbacks()
                logger.info("Market data subscriptions configured (propagation mode)")
                return
            # Subskrybuj główne pary
            symbols = ['BTCUSDT', 'ETHUSDT', 'ADAUSDT', 'DOTUSDT']
            
            for symbol in symbols:
                self.market_data_manager.subscribe_to_price(
                    symbol, 
                    lambda price_data, sym=symbol: schedule_coro_safely(lambda: self._handle_price_update(sym, price_data))
                )
            
            # Skonfiguruj callbacki Strategy Engine
            await self._setup_callbacks()
            
            logger.info("Market data subscriptions configured")
            
        except Exception as e:
            logger.error(f"Error setting up market data subscriptions: {e}")
    
    async def _setup_callbacks(self):
        """Skonfiguruj callbacki między komponentami"""
        try:
            # Sprawdź czy strategy_engine jest dostępny
            if self.strategy_engine is None:
                logger.warning("Strategy engine is not available - skipping callback setup")
                return
            
            # Strategy Engine -> UI (sygnały)
            if hasattr(self.strategy_engine, 'subscribe_to_signals'):
                self.strategy_engine.subscribe_to_signals(
                    lambda signal: schedule_coro_safely(lambda: self._notify_ui_callbacks('strategy_signal', signal))
                )
            
            # Strategy Engine -> UI (wykonania)
            if hasattr(self.strategy_engine, 'subscribe_to_executions'):
                self.strategy_engine.subscribe_to_executions(
                    lambda execution: schedule_coro_safely(lambda: self._notify_ui_callbacks('strategy_execution', execution))
                )
            
            logger.info("Callbacki skonfigurowane pomyślnie")
            
        except Exception as e:
            logger.error(f"Błąd konfiguracji callbacków: {e}")
            # Nie rzucamy wyjątku - callbacki są opcjonalne
    
    async def _handle_price_update(self, symbol: str, price_data: PriceData):
        """Obsługuje aktualizacje cen"""
        try:
            self.last_price_updates[symbol] = datetime.now()
            
            # Przygotuj dane do wysłania
            update_data = {
                'symbol': symbol,
                'price_data': price_data,
                'price': price_data.price,
                'bid': price_data.bid,
                'ask': price_data.ask,
                'volume_24h': price_data.volume_24h,
                'change_24h': price_data.change_24h,
                'change_24h_percent': price_data.change_24h_percent,
                'timestamp': price_data.timestamp
            }
            
            # Powiadom UI o aktualizacji cen - wszystkie odpowiednie callbacki
            await self._notify_ui_callbacks('price_update', update_data)
            await self._notify_ui_callbacks('market_data_update', update_data)
            await self._notify_ui_callbacks('ticker_update', update_data)
            
            logger.debug(f"Price update propagated for {symbol}: {price_data.price}")
            
        except Exception as e:
            logger.error(f"Error handling price update for {symbol}: {e}")
    
    async def _portfolio_update_loop(self):
        """Pętla aktualizacji portfolio"""
        while self.initialized:
            try:
                # Aktualizuj portfolio co 30 sekund
                portfolio_data = await self.get_portfolio_widget_data()
                await self._notify_ui_callbacks('portfolio_update', portfolio_data)
                
                self.last_portfolio_update = datetime.now()
                await asyncio.sleep(30)
                
            except Exception as e:
                logger.error(f"Error in portfolio update loop: {e}")
                await asyncio.sleep(60)  # Czekaj dłużej przy błędzie
    
    async def _system_status_update_loop(self):
        """Pętla aktualizacji statusu systemu"""
        while self.initialized:
            try:
                # Aktualizuj status co 10 sekund
                system_status = await self.get_system_status()
                await self._notify_ui_callbacks('system_status_update', system_status)
                
                await asyncio.sleep(10)
                
            except Exception as e:
                logger.error(f"Error in system status update loop: {e}")
                await asyncio.sleep(30)
    
    async def _notify_ui_callbacks(self, event_type: str, data: Any):
        """Powiadamia UI callbacks o aktualizacjach z centralną propagacją przez UnifiedDataManager"""
        try:
            # Upewnij się, że UI otrzymuje słownik, zgodnie z oczekiwaniami widoków
            payload = data
            try:
                from dataclasses import asdict, is_dataclass
                if is_dataclass(data):
                    payload = asdict(data)
            except Exception:
                pass
            # Dodatkowy fallback dla system_status_update
            if event_type == 'system_status_update' and not isinstance(payload, dict):
                try:
                    payload = {
                        'initialized': getattr(data, 'initialized', False),
                        'trading_mode': getattr(data, 'trading_mode', 'unknown'),
                        'total_bots': getattr(data, 'total_bots', 0),
                        'active_bots': getattr(data, 'active_bots', 0),
                        'total_profit': getattr(data, 'total_profit', 0.0),
                        'portfolio_value': getattr(data, 'portfolio_value', 0.0),
                        'market_data_connected': getattr(data, 'market_data_connected', False),
                        'trading_engine_ready': getattr(data, 'trading_engine_ready', False),
                        'risk_manager_active': getattr(data, 'risk_manager_active', False),
                        'last_updated': getattr(data, 'last_updated', datetime.now())
                    }
                except Exception:
                    payload = {'error': 'invalid system status payload'}
            
            # Jeśli UnifiedDataManager jest dostępny, deleguj powiadomienie
            try:
                if self.unified_data_manager is not None and hasattr(self.unified_data_manager, 'notify_ui_update'):
                    await self.unified_data_manager.notify_ui_update(event_type, payload)
                    return  # uniknij podwójnego powiadomienia
            except Exception as e:
                logger.warning(f"UnifiedDataManager notify_ui_update failed, using local callbacks: {e}")
            
            # Lokalny fallback gdy UDM nie jest dostępny
            if event_type in self.ui_callbacks:
                for callback in self.ui_callbacks[event_type]:
                    try:
                        if asyncio.iscoroutinefunction(callback):
                            await callback(payload)
                        else:
                            callback(payload)
                    except Exception as e:
                        logger.error(f"Error in UI callback for {event_type}: {e}")
                        
        except Exception as e:
            logger.error(f"Error notifying UI callbacks: {e}")
    
    async def get_system_status(self) -> SystemStatus:
        """Pobiera status całego systemu"""
        try:
            # Sprawdź czy data_manager jest dostępny
            if self.data_manager is None:
                logger.warning("DataManager is not available - returning basic system status")
                return SystemStatus(
                    initialized=False,
                    trading_mode="unknown",
                    total_bots=0,
                    active_bots=0,
                    total_profit=0.0,
                    portfolio_value=0.0,
                    market_data_connected=self.components_ready.get('market_data_manager', False),
                    trading_engine_ready=self.components_ready.get('trading_engine', False),
                    risk_manager_active=False,
                    last_updated=datetime.now()
                )
            
            dm = getattr(self, 'data_manager', None)
            portfolio_data = None
            bots_data = []
            trading_mode = 'unknown'
            try:
                if dm is not None and hasattr(dm, 'get_portfolio_data'):
                    portfolio_data = await dm.get_portfolio_data()
                if dm is not None and hasattr(dm, 'get_bots_data'):
                    bots_data = await dm.get_bots_data()
                if dm is not None and hasattr(dm, 'get_trading_mode'):
                    trading_mode = await dm.get_trading_mode()
            except Exception as e:
                logger.warning(f"DataManager calls failed in get_system_status: {e}")
            
            return SystemStatus(
                initialized=self.initialized,
                trading_mode=trading_mode,
                total_bots=len(bots_data),
                active_bots=len([bot for bot in bots_data if getattr(bot, 'active', False)]),
                total_profit=sum(getattr(bot, 'profit', 0.0) for bot in bots_data),
                portfolio_value=portfolio_data.total_value if portfolio_data else 0.0,
                market_data_connected=self.components_ready['market_data_manager'],
                trading_engine_ready=self.components_ready['trading_engine'],
                risk_manager_active=True,  # Będzie aktualizowane gdy RiskManager będzie gotowy
                last_updated=datetime.now()
            )
            
        except Exception as e:
            logger.error(f"Error getting system status: {e}")
            return SystemStatus(
                initialized=False,
                trading_mode="unknown",
                total_bots=0,
                active_bots=0,
                total_profit=0.0,
                portfolio_value=0.0,
                market_data_connected=False,
                trading_engine_ready=False,
                risk_manager_active=False,
                last_updated=datetime.now()
            )
    
    # === METODY WYMAGANE PRZEZ TESTY ===
    
    async def update_market_data(self, symbol: str, price_data: Dict[str, Any]):
        """Aktualizuje dane rynkowe dla symbolu"""
        try:
            if self.market_data_manager:
                # Konwertuj dict na PriceData jeśli potrzeba
                if isinstance(price_data, dict):
                    price_data_obj = PriceData(
                        symbol=price_data.get('symbol', symbol),
                        price=price_data.get('price', 0.0),
                        bid=price_data.get('bid', price_data.get('price', 0.0)),
                        ask=price_data.get('ask', price_data.get('price', 0.0)),
                        volume_24h=price_data.get('volume_24h', price_data.get('volume', 0.0)),
                        change_24h=price_data.get('change_24h', 0.0),
                        change_24h_percent=price_data.get('change_24h_percent', 0.0),
                        timestamp=price_data.get('timestamp', datetime.now())
                    )
                else:
                    price_data_obj = price_data
                
                await self.market_data_manager.update_price_data(symbol, price_data_obj)
                logger.info(f"Market data updated for {symbol}")
                
                # Powiadom UI o aktualizacji
                await self._notify_ui_callbacks('market_data_update', {
                    'symbol': symbol,
                    'data': price_data_obj
                })
                
        except Exception as e:
            logger.error(f"Error updating market data for {symbol}: {e}")
            raise
    
    async def get_market_data(self, symbol: str) -> Optional[Dict[str, Any]]:
        """Pobiera dane rynkowe dla symbolu - deleguje do UnifiedDataManager"""
        try:
            # Sprawdź czy unified_data_manager jest dostępny
            if self.unified_data_manager is not None:
                # Delegacja do UnifiedDataManager
                price_data = await self.unified_data_manager.get_market_data(symbol)
                if price_data:
                    return {
                        'symbol': price_data.symbol,
                        'price': price_data.price,
                        'timestamp': price_data.timestamp,
                        'volume': price_data.volume,
                        'change_24h': price_data.change_24h
                    }
            
            # Fallback do starej implementacji dla kompatybilności
            if self.market_data_manager:
                price_data = await self.market_data_manager.get_current_price(symbol)
                if price_data:
                    return {
                        'symbol': price_data.symbol,
                        'price': price_data.price,
                        'timestamp': price_data.timestamp,
                        'volume': price_data.volume_24h,
                        'change_24h': price_data.change_24h
                    }
            return None
        except Exception as e:
            logger.error(f"Error getting market data for {symbol}: {e}")
            return None
    
    async def get_portfolio_data(self) -> Optional[Dict[str, Any]]:
        """Pobiera dane portfela - deleguje do UnifiedDataManager"""
        try:
            # Sprawdź czy unified_data_manager jest dostępny
            if self.unified_data_manager is None:
                logger.warning("UnifiedDataManager is not available")
                return self._get_fallback_portfolio_data()
            
            # Delegacja do UnifiedDataManager
            portfolio_data = await self.unified_data_manager.get_portfolio_data()
            if portfolio_data:
                return {
                    'total_value': portfolio_data.get('total_value', 0.0),
                    'available_balance': portfolio_data.get('available_balance', 0.0),
                    'positions': portfolio_data.get('positions', []),
                    'profit_loss': portfolio_data.get('profit_loss', 0.0),
                    'last_updated': datetime.now().isoformat()
                }
            
            # Fallback do starszej implementacji
            return self._get_fallback_portfolio_data()
            
        except Exception as e:
            logger.error(f"Błąd pobierania danych portfolio: {e}")
            return self._get_fallback_portfolio_data()
    
    async def get_risk_metrics(self):
        """Pobiera metryki ryzyka w ujednoliconym formacie dla UI"""
        try:
            # Preferuj DataManager jeśli dostępny
            if hasattr(self, 'data_manager') and self.data_manager and hasattr(self.data_manager, 'get_risk_metrics'):
                return await self.data_manager.get_risk_metrics()
            
            # Fallback do UpdatedRiskManager jeśli dostępny (konwersja do RiskMetrics z data_manager)
            if hasattr(self, 'risk_manager') and self.risk_manager and hasattr(self.risk_manager, 'get_risk_metrics'):
                metrics = await self.risk_manager.get_risk_metrics()
                try:
                    # Konwersja do zgodnego formatu
                    from .data_manager import RiskMetrics as DMRiskMetrics
                    return DMRiskMetrics(
                        var_1d=getattr(metrics, 'var_95', 0.0) or 0.0,
                        var_7d=0.0,
                        sharpe_ratio=getattr(metrics, 'sharpe_ratio', 0.0) or 0.0,
                        max_drawdown=getattr(metrics, 'total_drawdown', 0.0) or 0.0,
                        volatility=0.0,
                        beta=0.0,
                        last_calculated=datetime.now()
                    )
                except Exception:
                    pass
            return None
        except Exception as e:
            logger.error(f"Błąd pobierania metryk ryzyka: {e}")
            return None
    
    def _get_fallback_portfolio_data(self) -> Optional[Dict[str, Any]]:
        """Fallback dla danych portfolio"""
        try:
            if hasattr(self, 'portfolio_manager') and self.portfolio_manager:
                summary = self.portfolio_manager.get_portfolio_summary()
                if asyncio.iscoroutine(summary):
                    # Jeśli to coroutine, zwróć podstawowe dane
                    return {
                        'total_value': 0.0,
                        'available_balance': 0.0,
                        'positions': [],
                        'profit_loss': 0.0,
                        'last_updated': datetime.now().isoformat()
                    }
                return {
                    'total_value': summary.total_value if summary else 0.0,
                    'available_balance': summary.available_balance if summary else 0.0,
                    'positions': [],
                    'profit_loss': summary.total_pnl if summary else 0.0,
                    'last_updated': datetime.now().isoformat()
                }
            
            # Zwróć podstawowe dane jeśli nic nie jest dostępne
            return {
                'total_value': 0.0,
                'available_balance': 0.0,
                'positions': [],
                'profit_loss': 0.0,
                'last_updated': datetime.now().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Błąd w fallback portfolio data: {e}")
            return None
    
    async def get_balance_data(self) -> Optional[Dict[str, Any]]:
        """Pobiera dane sald - deleguje do UnifiedDataManager"""
        try:
            # Sprawdź czy unified_data_manager jest dostępny
            if self.unified_data_manager is None:
                logger.warning("UnifiedDataManager is not available")
                return self._get_fallback_balance_data()
            
            # Delegacja do UnifiedDataManager
            balance_data = await self.unified_data_manager.get_balance_data()
            if balance_data:
                return balance_data
            
            # Fallback do starej implementacji dla kompatybilności
            return self._get_fallback_balance_data()
            
        except Exception as e:
            logger.error(f"Error getting balance data: {e}")
            return self._get_fallback_balance_data()
    
    def _get_fallback_balance_data(self) -> Optional[Dict[str, Any]]:
        """Fallback dla danych sald"""
        try:
            if hasattr(self, 'balance_data'):
                return self.balance_data
            
            if hasattr(self, 'trading_engine') and self.trading_engine:
                # Nie możemy używać await w synchronicznej metodzie
                # Zwróć podstawowe dane
                return {
                    'USDT': {'balance': 0.0, 'free': 0.0, 'locked': 0.0},
                    'BTC': {'balance': 0.0, 'free': 0.0, 'locked': 0.0}
                }
            
            # Zwróć podstawowe dane jeśli nic nie jest dostępne
            return {
                'USDT': {'balance': 0.0, 'free': 0.0, 'locked': 0.0}
            }
            
        except Exception as e:
            logger.error(f"Błąd w fallback balance data: {e}")
            return None
    
    async def create_bot(self, bot_config: Dict[str, Any]) -> bool:
        """Tworzy nowego bota"""
        try:
            # Import bot manager
            from .updated_bot_manager import get_updated_bot_manager
            bot_manager = get_updated_bot_manager()
            
            if bot_manager:
                # Konwertuj konfigurację na odpowiedni format
                from .updated_bot_manager import BotType
                
                bot_type = BotType.DCA if bot_config.get('strategy') == 'DCA' else BotType.GRID
                
                bot_id = await bot_manager.create_bot(
                    name=bot_config['name'],
                    bot_type=bot_type,
                    symbol=bot_config['symbol'],
                    parameters={
                        'position_size': bot_config.get('position_size', 100.0),
                        'stop_loss': bot_config.get('stop_loss', 5.0),
                        'take_profit': bot_config.get('take_profit', 10.0)
                    },
                    risk_settings={}
                )
                
                logger.info(f"Bot created with ID: {bot_id}")
                return True
            return False
        except Exception as e:
            logger.error(f"Error creating bot: {e}")
            return False
    
    async def start_bot(self, bot_name: str) -> bool:
        """Uruchamia bota"""
        try:
            from .updated_bot_manager import get_updated_bot_manager
            bot_manager = get_updated_bot_manager()
            
            if bot_manager:
                # Znajdź bot po nazwie (uproszczona implementacja)
                bots = await bot_manager.get_all_bots()
                for bot in bots:
                    if bot['name'] == bot_name:
                        return await bot_manager.start_bot(bot['id'])
            return False
        except Exception as e:
            logger.error(f"Error starting bot {bot_name}: {e}")
            return False
    
    async def stop_bot(self, bot_name: str) -> bool:
        """Zatrzymuje bota"""
        try:
            from .updated_bot_manager import get_updated_bot_manager
            bot_manager = get_updated_bot_manager()
            
            if bot_manager:
                # Znajdź bot po nazwie (uproszczona implementacja)
                bots = await bot_manager.get_all_bots()
                for bot in bots:
                    if bot['name'] == bot_name:
                        return await bot_manager.stop_bot(bot['id'])
            return False
        except Exception as e:
            logger.error(f"Error stopping bot {bot_name}: {e}")
            return False
    
    # === METODY HISTORIA I ALOKACJA PORTFELA ===

    async def get_performance_history(self) -> List[Dict[str, Any]]:
        """Pobiera historię wydajności portfela (lista punktów: date, value).
        Preferuje UnifiedDataManager, w przeciwnym razie stosuje sensowny fallback.
        """
        try:
            # 1) UnifiedDataManager delegacja, jeśli dostarczona
            if self.unified_data_manager is not None and hasattr(self.unified_data_manager, 'get_performance_history'):
                history = await self.unified_data_manager.get_performance_history()
                if history:
                    return history
            
            # 2) PortfolioManager nie ma wbudowanej historii – spróbuj oszacować lub fallback
            # Fallback: w trybie produkcyjnym nie zwracaj przykładowej historii
            if self._is_production_mode():
                logger.info("Production mode enabled: disabling sample performance history fallback")
                return []
            
            # 3) Symulacja ostatnich 30 dni na bazie wzrostów i wahań (tylko w trybie nie-produkcyjnym)
            now = datetime.now()
            historical_data: List[Dict[str, Any]] = []
            for i in range(30):
                date = now - timedelta(days=29 - i)
                value = 10000 + (i * 100) + ((i % 7) * 50)
                historical_data.append({'date': date, 'value': value})
            return historical_data
        except Exception as e:
            logger.error(f"Error getting performance history: {e}")
            if self._is_production_mode():
                return []
            # Fallback w trybie nie-produkcyjnym
            try:
                now = datetime.now()
                historical_data: List[Dict[str, Any]] = []
                for i in range(30):
                    date = now - timedelta(days=29 - i)
                    value = 10000 + (i * 100) + ((i % 7) * 50)
                    historical_data.append({'date': date, 'value': value})
                return historical_data
            except Exception:
                return []

    async def get_portfolio_allocation(self) -> Dict[str, float]:
        """Pobiera alokację portfela jako procenty per symbol.
        Deleguje do UnifiedDataManager jeśli dostępne, w przeciwnym razie wylicza z PortfolioManager lub stosuje fallback.
        """
        try:
            # 1) UnifiedDataManager delegacja, jeśli dostępna
            if self.unified_data_manager is not None and hasattr(self.unified_data_manager, 'get_portfolio_allocation'):
                allocation = await self.unified_data_manager.get_portfolio_allocation()
                if allocation:
                    return allocation
            
            # 2) Oblicz z PortfolioManager, jeśli dostępny
            if self.portfolio_manager is not None and hasattr(self.portfolio_manager, 'get_portfolio_summary'):
                summary = await self.portfolio_manager.get_portfolio_summary()
                if summary and getattr(summary, 'positions', None):
                    total_value = getattr(summary, 'total_value', 0.0) or 0.0
                    if total_value > 0:
                        allocation: Dict[str, float] = {}
                        for pos in summary.positions:
                            try:
                                symbol = getattr(pos, 'symbol', None) or getattr(pos, 'asset', 'UNKNOWN')
                                value = float(getattr(pos, 'value', 0.0) or 0.0)
                                percent = (value / total_value) * 100.0 if total_value > 0 else 0.0
                                allocation[symbol] = round(percent, 2)
                            except Exception:
                                continue
                        # Normalizacja (w razie błędów zaokrągleń)
                        total_percent = sum(allocation.values())
                        if total_percent > 0:
                            for k in list(allocation.keys()):
                                allocation[k] = round(allocation[k] * (100.0 / total_percent), 2)
                        return allocation
            
            # 3) Fallback: w trybie produkcyjnym nie zwracaj przykładowej alokacji
            if self._is_production_mode():
                logger.info("Production mode enabled: disabling sample portfolio allocation fallback")
                return {}
            return {
                'BTC': 45.0,
                'ETH': 25.0,
                'ADA': 15.0,
                'DOT': 10.0,
                'USDT': 5.0
            }
        except Exception as e:
            logger.error(f"Error getting portfolio allocation: {e}")
            return {}

    # === METODY DLA LOGS I ALERTS ===
    
    async def get_logs(self, limit: int = 100, level: str = None) -> List[LogEntry]:
        """Pobiera logi z systemu - delegacja do data_manager"""
        try:
            if self.data_manager is None:
                logger.warning("data_manager is None, returning empty logs")
                return []
            return await self.data_manager.get_logs(limit=limit, level=level)
        except Exception as e:
            logger.error(f"Error getting logs: {e}")
            return []
    
    async def get_alerts(self, limit: int = 50, unread_only: bool = False) -> List[AlertEntry]:
        """Pobiera alerty z systemu - delegacja do data_manager"""
        try:
            if self.data_manager is None:
                logger.warning("data_manager is None, returning empty alerts")
                return []
            return await self.data_manager.get_alerts(limit=limit, unread_only=unread_only)
        except Exception as e:
            logger.error(f"Error getting alerts: {e}")
            return []

# Singleton instance
_integrated_data_manager = None

def get_integrated_data_manager() -> IntegratedDataManager:
    """Zwraca singleton instance IntegratedDataManager"""
    global _integrated_data_manager
    if _integrated_data_manager is None:
        # Lazy import to avoid circular dependencies
        from .updated_risk_manager import get_updated_risk_manager
        from utils.config_manager import get_config_manager
        from app.database import DatabaseManager
        import asyncio
        
        # Create proper components
        config_manager = get_config_manager()
        database_manager = DatabaseManager()
        
        # Create IntegratedDataManager first
        _integrated_data_manager = IntegratedDataManager(config_manager, database_manager, None)
        
        # Then create risk manager with reference to data manager
        risk_manager = get_updated_risk_manager(_integrated_data_manager)
        _integrated_data_manager.risk_manager = risk_manager
        
        # Initialize the IntegratedDataManager
        try:
            # Detect running event loop and initialize accordingly
            try:
                asyncio.get_running_loop()
                # We're in an async context; schedule initialization
                schedule_coro_safely(lambda: _integrated_data_manager.initialize())
            except RuntimeError:
                # No running loop; run initialization synchronously
                asyncio.run(_integrated_data_manager.initialize())
        except Exception as e:
            logger.error(f"Failed to initialize IntegratedDataManager: {e}")
        
    return _integrated_data_manager
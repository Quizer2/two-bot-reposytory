"""
Updated Bot Manager - Zarządzanie botami z integracją z nowym systemem danych
"""

import asyncio
import logging
from datetime import datetime
from typing import Dict, List, Optional, Any
from dataclasses import dataclass
from enum import Enum

from .integrated_data_manager import get_integrated_data_manager, IntegratedDataManager
from .unified_data_manager import get_unified_data_manager, UnifiedDataManager
from .trading_engine import OrderRequest, OrderSide, OrderType, TradingEngine
from .market_data_manager import PriceData
from utils.event_bus import get_event_bus, EventTypes
from utils.config_manager import get_config_manager
from utils.helpers import get_or_create_event_loop, schedule_coro_safely

logger = logging.getLogger(__name__)

class BotStatus(Enum):
    STOPPED = "stopped"
    RUNNING = "running"
    ERROR = "error"
    PAUSED = "paused"
    STARTING = "starting"
    STOPPING = "stopping"

class BotType(Enum):
    DCA = "dca"
    GRID = "grid"
    SCALPING = "scalping"
    CUSTOM = "custom"

@dataclass
class BotConfig:
    """Konfiguracja bota"""
    id: str
    name: str
    bot_type: BotType
    symbol: str
    parameters: Dict[str, Any]
    risk_settings: Dict[str, Any]
    active: bool
    created_at: datetime

@dataclass
class BotPerformance:
    """Wydajność bota"""
    total_trades: int
    successful_trades: int
    profit_loss: float
    profit_loss_percent: float
    win_rate: float
    max_drawdown: float
    sharpe_ratio: float
    last_trade: Optional[datetime]

class BaseBot:
    """Bazowa klasa bota"""
    
    def __init__(self, bot_id: str, config: BotConfig, data_manager: IntegratedDataManager):
        self.bot_id = bot_id
        self.config = config
        self.data_manager = data_manager
        self.status = BotStatus.STOPPED
        self.running = False
        self.logger = logging.getLogger(f"Strategy.{bot_id}")
        
        # Jawnie przekazywane managery
        self.risk_manager = None
        self.db_manager = None
        self.notification_manager = None
        
        # Statystyki
        self.trades_count = 0
        self.successful_trades = 0
        self.total_profit = 0.0
        self.last_trade_time = None
    
    def set_risk_manager(self, risk_manager):
        """Ustawia RiskManager dla bota"""
        self.risk_manager = risk_manager
        self.logger.info(f"🤖 FLOW: RiskManager ustawiony dla bota {self.bot_id}")
    
    def set_db_manager(self, db_manager):
        """Ustawia DatabaseManager dla bota"""
        self.db_manager = db_manager
        self.logger.info(f"🤖 FLOW: DatabaseManager ustawiony dla bota {self.bot_id}")
    
    def set_notification_manager(self, notification_manager):
        """Ustawia NotificationManager dla bota"""
        self.notification_manager = notification_manager
        self.logger.info(f"🤖 FLOW: NotificationManager ustawiony dla bota {self.bot_id}")
        
    async def start(self):
        """Uruchamia strategię"""
        try:
            self.status = BotStatus.STARTING
            await self.data_manager.update_bot_status(self.bot_id, self.status.value, True)
            
            self.running = True
            self.status = BotStatus.RUNNING
            await self.data_manager.update_bot_status(self.bot_id, self.status.value, True)
            
            # Uruchom główną pętlę strategii
            schedule_coro_safely(lambda: self._strategy_loop())
            
            self.logger.info(f"Strategy {self.bot_id} started")
            
        except Exception as e:
            self.status = BotStatus.ERROR
            await self.data_manager.update_bot_status(self.bot_id, self.status.value, False)
            self.logger.error(f"Error starting strategy {self.bot_id}: {e}")
    
    async def stop(self):
        """Zatrzymuje strategię"""
        try:
            self.status = BotStatus.STOPPING
            await self.data_manager.update_bot_status(self.bot_id, self.status.value, True)
            
            self.running = False
            self.status = BotStatus.STOPPED
            await self.data_manager.update_bot_status(self.bot_id, self.status.value, False)
            
            self.logger.info(f"Strategy {self.bot_id} stopped")
            
        except Exception as e:
            self.status = BotStatus.ERROR
            self.logger.error(f"Error stopping strategy {self.bot_id}: {e}")
    
    async def pause(self):
        """Pauzuje strategię"""
        self.status = BotStatus.PAUSED
        await self.data_manager.update_bot_status(self.bot_id, self.status.value, True)
        self.logger.info(f"Strategy {self.bot_id} paused")
    
    async def resume(self):
        """Wznawia strategię"""
        self.status = BotStatus.RUNNING
        await self.data_manager.update_bot_status(self.bot_id, self.status.value, True)
        self.logger.info(f"Strategy {self.bot_id} resumed")
    
    async def _strategy_loop(self):
        """Główna pętla strategii - do implementacji w klasach pochodnych"""
        while self.running:
            try:
                if self.status == BotStatus.RUNNING:
                    await self._execute_strategy_logic()
                
                await asyncio.sleep(1)  # Podstawowy interwał
                
            except Exception as e:
                self.logger.error(f"Error in strategy loop for {self.bot_id}: {e}")
                self.status = BotStatus.ERROR
                await self.data_manager.update_bot_status(self.bot_id, self.status.value, False)
                break
    
    async def _execute_strategy_logic(self):
        """Logika strategii - do implementacji w klasach pochodnych"""
        pass
    
    async def _place_order(self, side: OrderSide, quantity: float, price: float = None, order_type: OrderType = OrderType.MARKET):
        """Składa zlecenie przez IntegratedDataManager z walidacją RiskManager"""
        try:
            order_request = OrderRequest(
                symbol=self.config.symbol,
                side=side,
                order_type=order_type,
                quantity=quantity,
                price=price,
                client_order_id=f"{self.bot_id}_{int(datetime.now().timestamp())}"
            )
            
            # Walidacja przez RiskManager jeśli dostępny
            if self.risk_manager:
                self.logger.info(f"🤖 FLOW: Walidacja zlecenia przez RiskManager dla bota {self.bot_id}")
                is_valid = await self.risk_manager.validate_order(order_request, self.bot_id)
                if not is_valid:
                    self.logger.warning(f"🚫 FLOW: Zlecenie odrzucone przez RiskManager dla bota {self.bot_id}")
                    return None
                self.logger.info(f"✅ FLOW: Zlecenie zatwierdzone przez RiskManager dla bota {self.bot_id}")
            else:
                self.logger.warning(f"⚠️ FLOW: Brak RiskManager - zlecenie bez walidacji dla bota {self.bot_id}")
            
            self.logger.info(f"📤 FLOW: Wysyłanie zlecenia do API dla bota {self.bot_id}")
            order_response = await self.data_manager.execute_trade_order(self.bot_id, order_request)
            
            # Aktualizuj statystyki
            if order_response and order_response.status.value in ['FILLED', 'PARTIALLY_FILLED']:
                self.trades_count += 1
                self.last_trade_time = datetime.now()
                
                # Oblicz zysk/stratę (uproszczona logika)
                if side == OrderSide.SELL:
                    # Przy sprzedaży oblicz zysk
                    profit = quantity * (order_response.average_price or 0) * 0.01  # Przykładowy zysk 1%
                    self.total_profit += profit
                    if profit > 0:
                        self.successful_trades += 1
                
                self.logger.info(f"✅ FLOW: Zlecenie wykonane pomyślnie dla bota {self.bot_id}")
            
            return order_response
            
        except Exception as e:
            self.logger.error(f"❌ FLOW: Błąd podczas składania zlecenia dla bota {self.bot_id}: {e}")
            return None
    
    async def get_current_price(self) -> Optional[PriceData]:
        """Pobiera aktualną cenę"""
        return await self.data_manager.get_market_data_for_bot(self.bot_id, self.config.symbol)

class DCAStrategy(BaseBot):
    """Strategia DCA (Dollar Cost Averaging)"""
    
    async def _execute_strategy_logic(self):
        """Logika strategii DCA"""
        try:
            # Pobierz parametry DCA
            buy_amount = self.config.parameters.get('buy_amount', 100.0)
            interval_minutes = self.config.parameters.get('interval_minutes', 60)
            
            # Sprawdź czy czas na kolejny zakup
            if self._should_execute_dca():
                price_data = await self.get_current_price()
                if price_data:
                    quantity = buy_amount / price_data.price
                    
                    order_response = await self._place_order(
                        side=OrderSide.BUY,
                        quantity=quantity,
                        order_type=OrderType.MARKET
                    )
                    
                    if order_response:
                        self.logger.info(f"DCA buy executed: {quantity} {self.config.symbol} at {price_data.price}")
            
        except Exception as e:
            self.logger.error(f"Error in DCA strategy logic: {e}")
    
    def _should_execute_dca(self) -> bool:
        """Sprawdza czy czas na wykonanie DCA"""
        interval_minutes = self.config.parameters.get('interval_minutes', 60)
        
        if not self.last_trade_time:
            return True
        
        time_since_last = datetime.now() - self.last_trade_time
        return time_since_last.total_seconds() >= (interval_minutes * 60)

class GridStrategy(BaseBot):
    """Strategia Grid Trading"""
    
    def __init__(self, bot_id: str, config: BotConfig, data_manager: IntegratedDataManager):
        super().__init__(bot_id, config, data_manager)
        self.grid_levels = []
        self.active_orders = {}
    
    async def _execute_strategy_logic(self):
        """Logika strategii Grid"""
        try:
            # Pobierz parametry Grid
            grid_size = self.config.parameters.get('grid_size', 10)
            grid_spacing = self.config.parameters.get('grid_spacing', 0.01)  # 1%
            
            price_data = await self.get_current_price()
            if price_data:
                await self._update_grid_orders(price_data.price, grid_size, grid_spacing)
            
        except Exception as e:
            self.logger.error(f"Error in Grid strategy logic: {e}")
    
    async def _update_grid_orders(self, current_price: float, grid_size: int, grid_spacing: float):
        """Aktualizuje zlecenia grid"""
        # Uproszczona implementacja Grid
        # W pełnej implementacji byłyby zlecenia limit na różnych poziomach
        self.logger.info(f"Grid strategy monitoring price: {current_price}")

class ScalpingStrategy(BaseBot):
    """Strategia Scalping"""
    
    async def _execute_strategy_logic(self):
        """Logika strategii Scalping"""
        try:
            # Pobierz parametry Scalping
            profit_target = self.config.parameters.get('profit_target', 0.005)  # 0.5%
            stop_loss = self.config.parameters.get('stop_loss', 0.002)  # 0.2%
            
            price_data = await self.get_current_price()
            if price_data:
                # Uproszczona logika scalping
                await self._check_scalping_signals(price_data, profit_target, stop_loss)
            
        except Exception as e:
            self.logger.error(f"Error in Scalping strategy logic: {e}")
    
    async def _check_scalping_signals(self, price_data: PriceData, profit_target: float, stop_loss: float):
        """Sprawdza sygnały scalping"""
        # Uproszczona implementacja
        self.logger.info(f"Scalping strategy monitoring: {price_data.symbol} at {price_data.price}")

class UpdatedBotManager:
    """Zaktualizowany Manager Botów z integracją z UnifiedDataManager"""

    def __init__(
        self,
        risk_manager=None,
        data_manager=None,
        db_manager=None,
        notification_manager=None,
        *,
        config_manager=None,
        trading_engine: Optional[TradingEngine] = None,
        market_data_manager=None,
    ):
        # Konfiguracja aplikacji (fallback do globalnego ConfigManagera)
        self.config_manager = config_manager or get_config_manager()

        # Główny UnifiedDataManager
        self.unified_data_manager = get_unified_data_manager()

        # Kompatybilność - IntegratedDataManager jako wrapper
        self.data_manager: IntegratedDataManager = data_manager or get_integrated_data_manager()
        if hasattr(self.data_manager, "config_manager"):
            self.data_manager.config_manager = self.config_manager

        # Jawne przekazywanie managerów z zachowaniem kompatybilności
        self.trading_engine: Optional[TradingEngine] = trading_engine or getattr(self.data_manager, "trading_engine", None)
        if self.trading_engine and hasattr(self.data_manager, "trading_engine"):
            self.data_manager.trading_engine = self.trading_engine

        self.market_data_manager = market_data_manager or getattr(self.data_manager, "market_data_manager", None)
        if self.market_data_manager and hasattr(self.data_manager, "market_data_manager"):
            self.data_manager.market_data_manager = self.market_data_manager

        self.risk_manager = risk_manager or getattr(self.data_manager, "risk_manager", None)
        if self.risk_manager is None and self.unified_data_manager and hasattr(self.unified_data_manager, "risk_manager"):
            self.risk_manager = getattr(self.unified_data_manager, "risk_manager")

        self.db_manager = db_manager or getattr(self.data_manager, "database_manager", None)
        self.notification_manager = notification_manager

        # Boty i konfiguracje
        self.active_bots: Dict[str, BaseBot] = {}
        self.bot_configs: Dict[str, BotConfig] = {}
        self.event_bus = get_event_bus()
        
        # Subskrypcja na zmiany konfiguracji
        self.event_bus.subscribe(EventTypes.CONFIG_UPDATED, self._on_config_updated)
        
        # Mapowanie typów strategii
        self.strategy_classes = {
            BotType.DCA: DCAStrategy,
            BotType.GRID: GridStrategy,
            BotType.SCALPING: ScalpingStrategy,
            BotType.CUSTOM: BaseBot  # Fallback
        }
        
        logger.info("UpdatedBotManager initialized with UnifiedDataManager")
    
    async def initialize(self):
        """Inicjalizuje BotManager"""
        try:
            logger.info("Initializing UpdatedBotManager...")
            
            # Załaduj zapisane boty
            await self._load_saved_bots()
            
            logger.info("UpdatedBotManager initialized")
            
        except Exception as e:
            logger.error(f"Error initializing UpdatedBotManager: {e}")
    
    async def create_bot(self, name: str, bot_type: BotType, symbol: str, parameters: Dict[str, Any], risk_settings: Dict[str, Any] = None) -> str:
        """Tworzy nowego bota z walidacją przez RiskManager"""
        try:
            logger.info(f"🤖 FLOW: BotManager.create_bot({name}, {bot_type}, {symbol}) - rozpoczęcie")
            
            bot_id = f"bot_{int(datetime.now().timestamp())}"
            
            # Walidacja przez RiskManager jeśli dostępny
            if self.risk_manager and hasattr(self.risk_manager, 'validate_bot_config'):
                logger.info(f"🤖 FLOW: Walidacja konfiguracji bota przez RiskManager...")
                validation_result = await self.risk_manager.validate_bot_config({
                    'symbol': symbol,
                    'parameters': parameters,
                    'risk_settings': risk_settings or {}
                })
                if not validation_result.get('valid', True):
                    logger.error(f"🤖 FLOW ERROR: RiskManager odrzucił konfigurację: {validation_result.get('reason')}")
                    raise ValueError(f"Konfiguracja bota odrzucona przez RiskManager: {validation_result.get('reason')}")
                logger.info(f"🤖 FLOW: RiskManager zatwierdził konfigurację bota")
            
            config = BotConfig(
                id=bot_id,
                name=name,
                bot_type=bot_type,
                symbol=symbol,
                parameters=parameters,
                risk_settings=risk_settings or {},
                active=False,
                created_at=datetime.now()
            )
            
            self.bot_configs[bot_id] = config
            
            # Zapisz do bazy danych przez DatabaseManager
            if self.db_manager and hasattr(self.db_manager, 'save_bot_config'):
                logger.info(f"🤖 FLOW: Zapisywanie konfiguracji bota do bazy danych...")
                await self.db_manager.save_bot_config(config)
                logger.info(f"🤖 FLOW: Konfiguracja bota zapisana w bazie danych")
            
            logger.info(f"🤖 FLOW: Bot utworzony: {bot_id} ({name})")
            return bot_id
            
        except Exception as e:
            logger.error(f"🤖 FLOW ERROR: Błąd tworzenia bota: {e}")
            raise
    
    async def start_bot(self, bot_id: str) -> bool:
        """Uruchamia bota z jawnymi managerami"""
        try:
            logger.info(f"🤖 FLOW: BotManager.start_bot({bot_id}) - rozpoczęcie")
            
            if bot_id not in self.bot_configs:
                logger.error(f"Bot {bot_id} not found")
                return False
            
            if bot_id in self.active_bots:
                logger.warning(f"Bot {bot_id} is already running")
                return True
            
            config = self.bot_configs[bot_id]
            strategy_class = self.strategy_classes.get(config.bot_type, BaseBot)
            
            # Przekazanie jawnych managerów do strategii
            logger.info(f"🤖 FLOW: Tworzenie strategii {config.bot_type} z managerami:")
            logger.info(f"  - data_manager: {type(self.data_manager).__name__}")
            logger.info(f"  - risk_manager: {type(self.risk_manager).__name__ if self.risk_manager else 'None'}")
            logger.info(f"  - db_manager: {type(self.db_manager).__name__ if self.db_manager else 'None'}")
            
            strategy = strategy_class(bot_id, config, self.data_manager)
            
            # Jeśli strategia ma metody do ustawienia managerów, użyj ich
            if hasattr(strategy, 'set_risk_manager') and self.risk_manager:
                strategy.set_risk_manager(self.risk_manager)
                logger.info(f"🤖 FLOW: RiskManager przekazany do bota {bot_id}")
                
            if hasattr(strategy, 'set_db_manager') and self.db_manager:
                strategy.set_db_manager(self.db_manager)
                logger.info(f"🤖 FLOW: DatabaseManager przekazany do bota {bot_id}")
                
            if hasattr(strategy, 'set_notification_manager') and self.notification_manager:
                strategy.set_notification_manager(self.notification_manager)
                logger.info(f"🤖 FLOW: NotificationManager przekazany do bota {bot_id}")
            
            self.active_bots[bot_id] = strategy
            
            logger.info(f"🤖 FLOW: Uruchamianie strategii {bot_id}...")
            await strategy.start()
            
            logger.info(f"🤖 FLOW: Bot {bot_id} uruchomiony pomyślnie")
            return True
            
        except Exception as e:
            logger.error(f"🤖 FLOW ERROR: Błąd uruchamiania bota {bot_id}: {e}")
            return False
    
    async def stop_bot(self, bot_id: str) -> bool:
        """Zatrzymuje bota"""
        try:
            if bot_id not in self.active_bots:
                logger.warning(f"Bot {bot_id} is not running")
                return True
            
            strategy = self.active_bots[bot_id]
            await strategy.stop()
            
            del self.active_bots[bot_id]
            
            logger.info(f"Bot {bot_id} stopped successfully")
            return True
            
        except Exception as e:
            logger.error(f"Error stopping bot {bot_id}: {e}")
            return False
    
    async def pause_bot(self, bot_id: str) -> bool:
        """Pauzuje bota"""
        try:
            if bot_id in self.active_bots:
                await self.active_bots[bot_id].pause()
                return True
            return False
            
        except Exception as e:
            logger.error(f"Error pausing bot {bot_id}: {e}")
            return False
    
    async def resume_bot(self, bot_id: str) -> bool:
        """Wznawia bota"""
        try:
            if bot_id in self.active_bots:
                await self.active_bots[bot_id].resume()
                return True
            return False
            
        except Exception as e:
            logger.error(f"Error resuming bot {bot_id}: {e}")
            return False
    
    async def get_bot_status(self, bot_id: str) -> Dict[str, Any]:
        """Pobiera status bota"""
        try:
            if bot_id not in self.bot_configs:
                return {"error": "Bot not found"}
            
            config = self.bot_configs[bot_id]
            strategy = self.active_bots.get(bot_id)
            
            status = {
                "id": bot_id,
                "name": config.name,
                "type": config.bot_type.value,
                "symbol": config.symbol,
                "status": strategy.status.value if strategy else BotStatus.STOPPED.value,
                "active": bot_id in self.active_bots,
                "created_at": config.created_at.isoformat(),
                "parameters": config.parameters
            }
            
            if strategy:
                status.update({
                    "trades_count": strategy.trades_count,
                    "successful_trades": strategy.successful_trades,
                    "total_profit": strategy.total_profit,
                    "last_trade": strategy.last_trade_time.isoformat() if strategy.last_trade_time else None
                })
            
            return status
            
        except Exception as e:
            logger.error(f"Error getting bot status for {bot_id}: {e}")
            return {"error": str(e)}
    
    async def get_all_bots_status(self) -> List[Dict[str, Any]]:
        """Pobiera status wszystkich botów"""
        try:
            statuses = []
            for bot_id in self.bot_configs:
                status = await self.get_bot_status(bot_id)
                statuses.append(status)
            return statuses
            
        except Exception as e:
            logger.error(f"Error getting all bots status: {e}")
            return []
    
    async def get_all_bots(self) -> List[Dict[str, Any]]:
        """Pobiera wszystkie boty (alias dla get_all_bots_status)"""
        return await self.get_all_bots_status()
    
    async def delete_bot(self, bot_id: str) -> bool:
        """Usuwa bota"""
        try:
            # Zatrzymaj bota jeśli działa
            if bot_id in self.active_bots:
                await self.stop_bot(bot_id)
            
            # Usuń konfigurację
            if bot_id in self.bot_configs:
                del self.bot_configs[bot_id]
            
            # Usuń z bazy danych
            # await self.data_manager.delete_bot_config(bot_id)
            
            logger.info(f"Bot {bot_id} deleted")
            return True
            
        except Exception as e:
            logger.error(f"Error deleting bot {bot_id}: {e}")
            return False
    
    async def _load_saved_bots(self):
        """Ładuje zapisane boty z bazy danych"""
        try:
            # Tutaj będzie implementacja ładowania z bazy
            # Na razie tworzymy przykładowe boty
            
            # Przykładowy bot DCA
            await self.create_bot(
                name="DCA BTC Bot",
                bot_type=BotType.DCA,
                symbol="BTCUSDT",
                parameters={
                    "buy_amount": 100.0,
                    "interval_minutes": 60
                }
            )
            
            logger.info("Saved bots loaded")
            
        except Exception as e:
            logger.error(f"Error loading saved bots: {e}")
    
    def _on_config_updated(self, event_data: dict):
        """Callback na zmianę konfiguracji"""
        try:
            logger.info(f"BotManager received config update: {event_data}")

            # Sprawdź czy zmiana dotyczy botów
            if 'bot' in str(event_data).lower() or 'strategy' in str(event_data).lower():
                logger.info("Config change affects bots - reloading bot configurations")
                # Tutaj można dodać logikę przeładowania konfiguracji botów

            # Aktualizacja limiterów TradingEngine
            if (
                isinstance(event_data, dict)
                and event_data.get('config_type') == 'app'
                and self.trading_engine
                and hasattr(self.trading_engine, 'configure_rate_limits')
            ):
                new_config = event_data.get('new_config') or {}
                trading_cfg = new_config.get('trading', {})
                if 'rate_limiting' in trading_cfg:
                    self.trading_engine.configure_rate_limits(trading_cfg['rate_limiting'])
                    logger.info("TradingEngine rate limits reloaded from configuration event")

        except Exception as e:
            logger.error(f"Error handling config update in BotManager: {e}")

# Singleton instance
_updated_bot_manager = None

def get_updated_bot_manager(risk_manager=None, data_manager=None, db_manager=None, notification_manager=None) -> UpdatedBotManager:
    """Zwraca singleton instance UpdatedBotManager z jawnymi managerami"""
    global _updated_bot_manager
    if _updated_bot_manager is None:
        # Jeśli nie przekazano managerów, pobierz je z systemu
        if risk_manager is None:
            from .updated_risk_manager import get_updated_risk_manager
            risk_manager = get_updated_risk_manager()
        
        if data_manager is None:
            data_manager = get_integrated_data_manager()
            
        if db_manager is None:
            from core.database_manager import DatabaseManager
            db_manager = DatabaseManager()
            
        if notification_manager is None:
            # TODO: Dodać NotificationManager gdy będzie dostępny
            notification_manager = None
            
        _updated_bot_manager = UpdatedBotManager(
            risk_manager=risk_manager,
            data_manager=data_manager, 
            db_manager=db_manager,
            notification_manager=notification_manager
        )
        logger.info("UpdatedBotManager singleton created with explicit managers")
    return _updated_bot_manager

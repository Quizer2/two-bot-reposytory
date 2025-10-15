"""
Updated Bot Manager - Zarządzanie botami z integracją z nowym systemem danych
"""

import asyncio
import contextlib
import logging
import secrets
from collections import deque
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

try:
    from app.strategy.ai_trading_bot import AITradingBot
    AI_COMPONENTS_AVAILABLE = True
except Exception as exc:  # pragma: no cover - środowisko bez komponentów AI
    AITradingBot = None  # type: ignore[assignment]
    AI_COMPONENTS_AVAILABLE = False

try:
    from app.strategy.arbitrage import ArbitrageStrategy as AdvancedArbitrageStrategy
    ARBITRAGE_COMPONENTS_AVAILABLE = True
except Exception:  # pragma: no cover - środowisko zależne od środowiska testowego
    AdvancedArbitrageStrategy = None  # type: ignore[assignment]
    ARBITRAGE_COMPONENTS_AVAILABLE = False

try:
    from app.strategy.swing import SwingStrategy as AdvancedSwingStrategy
    SWING_COMPONENTS_AVAILABLE = True
except Exception:  # pragma: no cover - opcjonalna zależność
    AdvancedSwingStrategy = None  # type: ignore[assignment]
    SWING_COMPONENTS_AVAILABLE = False

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
    AI = "ai"
    ARBITRAGE = "arbitrage"
    SWING = "swing"
    MOMENTUM = "momentum"
    MEAN_REVERSION = "mean_reversion"
    BREAKOUT = "breakout"

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

    async def update_parameters(self, parameters: Dict[str, Any]):
        """Aktualizuje parametry strategii w locie."""
        if parameters:
            self.config.parameters.update(parameters)
            self.logger.info("🤖 FLOW: Parametry zaktualizowane dla bota %s", self.bot_id)

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

    def _register_manual_profit(self, response: Any, quantity: float, actual_profit: float) -> None:
        """Koryguje statystyki po ręcznym wyliczeniu zysku/straty."""

        if response is None:
            return

        status = getattr(response, "status", None)
        status_value = getattr(status, "value", getattr(status, "name", "")) if status else ""
        if str(status_value).lower() not in {"filled", "partially_filled"}:
            return

        try:
            average_price = float(getattr(response, "average_price", 0.0) or 0.0)
        except (TypeError, ValueError):
            average_price = 0.0

        default_profit = quantity * average_price * 0.01
        self.total_profit -= default_profit
        self.total_profit += actual_profit

        if actual_profit < 0 and self.successful_trades > 0:
            self.successful_trades -= 1

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


class AIStrategy(BaseBot):
    """Strategia sterująca botem AI Trading Bot."""

    def __init__(self, bot_id: str, config: BotConfig, data_manager: IntegratedDataManager):
        super().__init__(bot_id, config, data_manager)
        self.ai_bot: Optional[AITradingBot] = None
        self._ai_task: Optional[asyncio.Task] = None
        self._initialized = False

        if AI_COMPONENTS_AVAILABLE:
            parameters = dict(config.parameters or {})
            parameters.setdefault('pair', config.symbol)
            if 'budget' not in parameters and 'buy_amount' in parameters:
                parameters['budget'] = parameters['buy_amount']
            self.ai_bot = AITradingBot(bot_id, parameters)
        else:
            self.logger.warning("AI Trading components are unavailable – AIStrategy will remain idle")

    async def start(self):
        if AI_COMPONENTS_AVAILABLE:
            await self._ensure_ai_started()
        else:
            self.logger.error("AI components missing – cannot start AI strategy")
        await super().start()

    async def stop(self):
        if self._ai_task is not None:
            if self.ai_bot is not None:
                with contextlib.suppress(Exception):
                    await self.ai_bot.stop()
            self._ai_task.cancel()
            with contextlib.suppress(asyncio.CancelledError):
                await self._ai_task
            self._ai_task = None
        await super().stop()

    async def update_parameters(self, parameters: Dict[str, Any]):
        await super().update_parameters(parameters)
        if self.ai_bot and parameters:
            self.ai_bot.parameters.update(parameters)
            if 'budget' in parameters:
                try:
                    self.ai_bot.max_budget = float(parameters['budget'])
                except (TypeError, ValueError):
                    self.logger.debug("Invalid budget provided for AI bot update")

    async def _ensure_ai_started(self) -> bool:
        if not AI_COMPONENTS_AVAILABLE or self.ai_bot is None:
            return False
        if not self._initialized:
            db_manager = self.db_manager or getattr(self.data_manager, 'database_manager', None)
            risk_manager = self.risk_manager or getattr(self.data_manager, 'risk_manager', None)
            exchange = None
            trading_engine = getattr(self.data_manager, 'trading_engine', None)
            if trading_engine is not None and hasattr(trading_engine, 'exchange'):
                exchange = getattr(trading_engine, 'exchange')
            data_manager_ref = getattr(self.data_manager, 'data_manager', None)
            try:
                await self.ai_bot.initialize(db_manager, risk_manager, exchange, data_manager_ref)
                self._initialized = True
            except Exception as exc:
                self.logger.error(f"Failed to initialize AI Trading Bot: {exc}")
                return False
        if self._ai_task is None or self._ai_task.done():
            loop = asyncio.get_running_loop()
            self._ai_task = loop.create_task(self.ai_bot.start())
        return True

    async def _execute_strategy_logic(self):
        if AI_COMPONENTS_AVAILABLE:
            await self._ensure_ai_started()
        await asyncio.sleep(1)


class ArbitrageBotStrategy(BaseBot):
    """Strategia arbitrażowa działająca równolegle na wielu giełdach."""

    def __init__(self, bot_id: str, config: BotConfig, data_manager: IntegratedDataManager):
        super().__init__(bot_id, config, data_manager)
        params = dict(config.parameters or {})
        exchanges = params.get('exchanges') or []
        if isinstance(exchanges, str):
            exchanges = [segment.strip() for segment in exchanges.split(',') if segment.strip()]
        if not exchanges:
            primary = params.get('primary_exchange') or params.get('exchange') or 'binance'
            secondary = params.get('secondary_exchange') or 'coinbase'
            exchanges = [primary]
            if secondary and secondary != primary:
                exchanges.append(secondary)
        if len(exchanges) < 2:
            exchanges.append('kraken')
        self.exchanges: List[str] = exchanges
        min_spread_value = params.get('min_spread_percentage') or params.get('min_spread') or 0.5
        if isinstance(min_spread_value, (int, float)) and float(min_spread_value) < 1:
            min_spread_value = float(min_spread_value) * 100
        self.min_spread_pct = float(min_spread_value)

        max_slippage_value = params.get('max_slippage_percentage') or 0.25
        if isinstance(max_slippage_value, (int, float)) and float(max_slippage_value) < 1:
            max_slippage_value = float(max_slippage_value) * 100
        self.max_slippage_pct = float(max_slippage_value)
        self.trade_amount = float(params.get('trade_amount') or params.get('amount') or 50.0)
        self._price_offsets: Dict[str, float] = {}
        self._tick = 0
        self._last_opportunity: Optional[Dict[str, Any]] = None
        self._advanced_strategy = None

        if ARBITRAGE_COMPONENTS_AVAILABLE and AdvancedArbitrageStrategy:
            try:
                init_kwargs: Dict[str, Any] = {
                    'symbol': config.symbol,
                    'exchanges': list(self.exchanges),
                }
                for key in (
                    'min_spread_percentage', 'max_spread_percentage', 'min_volume', 'max_position_size',
                    'execution_timeout_seconds', 'price_update_interval_ms', 'opportunity_expiry_seconds',
                    'min_confidence_score', 'max_slippage_percentage', 'enable_triangular',
                    'balance_threshold_percentage', 'risk_per_trade_percentage', 'max_concurrent_trades',
                ):
                    if key in params:
                        init_kwargs[key] = params[key]
                self._advanced_strategy = AdvancedArbitrageStrategy(**init_kwargs)
            except Exception as exc:  # pragma: no cover - zależy od środowiska
                logger.warning(f"Failed to initialize advanced arbitrage strategy for {bot_id}: {exc}")
                self._advanced_strategy = None

    async def _execute_strategy_logic(self):
        price_data = await self.get_current_price()
        if not price_data or not price_data.price or price_data.price <= 0:
            return

        base_price = float(price_data.price)
        simulated_quotes: Dict[str, float] = {}
        noise_basis = max(self.min_spread_pct, 0.1) / 200.0
        self._tick += 1

        for idx, exchange in enumerate(self.exchanges):
            offset = self._price_offsets.get(exchange)
            if offset is None:
                offset = (idx - (len(self.exchanges) / 2)) * noise_basis
                self._price_offsets[exchange] = offset
            direction = 1 if (self._tick + idx) % 2 == 0 else -1
            simulated_price = base_price * (1 + direction * abs(offset))
            simulated_quotes[exchange] = max(simulated_price, 0.01)

        if len(simulated_quotes) < 2:
            return

        best_bid_exchange, best_bid = max(simulated_quotes.items(), key=lambda item: item[1])
        best_ask_exchange, best_ask = min(simulated_quotes.items(), key=lambda item: item[1])
        if best_ask <= 0:
            return

        spread_pct = ((best_bid - best_ask) / best_ask) * 100.0
        self.logger.debug(
            "Arbitrage check %s: best bid %.4f @ %s vs ask %.4f @ %s (spread %.4f%%)",
            self.bot_id,
            best_bid,
            best_bid_exchange,
            best_ask,
            best_ask_exchange,
            spread_pct,
        )

        if spread_pct >= self.min_spread_pct:
            quantity = max(self.trade_amount / base_price, 0.0)
            profit = quantity * (best_bid - best_ask)
            self.trades_count += 1
            if profit >= 0:
                self.successful_trades += 1
            self.total_profit += profit
            self.last_trade_time = datetime.now()
            self._last_opportunity = {
                'buy_exchange': best_ask_exchange,
                'sell_exchange': best_bid_exchange,
                'spread_pct': spread_pct,
                'profit_estimate': profit,
            }
            self.logger.info(
                "✅ FLOW: Wykryto okazję arbitrażową %.2f%% między %s a %s (zysk %.4f)",
                spread_pct,
                best_ask_exchange,
                best_bid_exchange,
                profit,
            )
        await asyncio.sleep(0)


class SwingBotStrategy(BaseBot):
    """Strategia swing trading wykorzystująca prostą analizę trendu."""

    def __init__(self, bot_id: str, config: BotConfig, data_manager: IntegratedDataManager):
        super().__init__(bot_id, config, data_manager)
        params = dict(config.parameters or {})
        self.trade_amount = float(params.get('amount') or params.get('position_size') or 250.0)
        self.short_window = max(int(params.get('short_window', 5)), 2)
        self.long_window = max(int(params.get('long_window', 20)), self.short_window + 1)
        self.trend_buffer = float(params.get('trend_buffer', 0.001))
        self.take_profit_ratio = float(params.get('take_profit_ratio', 2.0))
        stop_loss_value = params.get('stop_loss_percentage', 1.5)
        if isinstance(stop_loss_value, (int, float)) and float(stop_loss_value) < 1:
            stop_loss_value = float(stop_loss_value) * 100
        self.stop_loss_pct = float(stop_loss_value)
        self._price_history: deque = deque(maxlen=max(self.long_window * 4, 50))
        self._current_position: Optional[str] = None
        self._entry_price: Optional[float] = None
        self._advanced_strategy = None

        if SWING_COMPONENTS_AVAILABLE and AdvancedSwingStrategy:
            try:
                init_kwargs: Dict[str, Any] = {'symbol': config.symbol}
                for key in (
                    'timeframe', 'amount', 'sma_short', 'sma_medium', 'sma_long', 'rsi_period', 'rsi_oversold',
                    'rsi_overbought', 'macd_fast', 'macd_slow', 'macd_signal', 'bb_period', 'bb_std',
                    'stoch_k', 'stoch_d', 'atr_period', 'min_trend_strength', 'stop_loss_atr_multiplier',
                    'take_profit_ratio', 'stop_loss_percentage', 'max_position_time_hours', 'volume_confirmation',
                ):
                    if key in params:
                        init_kwargs[key] = params[key]
                self._advanced_strategy = AdvancedSwingStrategy(**init_kwargs)
            except Exception as exc:  # pragma: no cover - zależy od środowiska
                logger.warning(f"Failed to initialize advanced swing strategy for {bot_id}: {exc}")
                self._advanced_strategy = None

    async def _execute_strategy_logic(self):
        price_data = await self.get_current_price()
        if not price_data or not price_data.price or price_data.price <= 0:
            return

        price = float(price_data.price)
        self._price_history.append(price)
        if len(self._price_history) < self.long_window:
            return

        short_avg = sum(list(self._price_history)[-self.short_window:]) / self.short_window
        long_avg = sum(self._price_history) / len(self._price_history)
        threshold = long_avg * self.trend_buffer

        if short_avg > long_avg + threshold:
            await self._ensure_position('long', price)
        elif short_avg < long_avg - threshold:
            await self._ensure_position('short', price)

        if self._current_position and self._entry_price:
            change_pct = ((price - self._entry_price) / self._entry_price) * 100.0
            if self._current_position == 'long' and change_pct >= self.take_profit_ratio:
                await self._close_position(price)
            elif self._current_position == 'long' and change_pct <= -self.stop_loss_pct:
                await self._close_position(price)
            elif self._current_position == 'short' and change_pct <= -self.take_profit_ratio:
                await self._close_position(price)
            elif self._current_position == 'short' and change_pct >= self.stop_loss_pct:
                await self._close_position(price)

        await asyncio.sleep(0)

    async def _ensure_position(self, direction: str, price: float) -> None:
        if self._current_position == direction:
            return
        if self._current_position and self._current_position != direction:
            await self._close_position(price)
        quantity = max(self.trade_amount / price, 0.0)
        if quantity <= 0:
            return
        self._current_position = direction
        self._entry_price = price
        self.last_trade_time = datetime.now()
        self.logger.info(
            "📈 FLOW: %s otwiera pozycję %s @ %.2f (qty %.6f)",
            self.bot_id,
            direction,
            price,
            quantity,
        )

    async def _close_position(self, price: float) -> None:
        if self._current_position is None or self._entry_price is None:
            return
        direction = self._current_position
        entry_price = self._entry_price
        quantity = max(self.trade_amount / entry_price, 0.0)
        pnl = (price - entry_price) * quantity
        if direction == 'short':
            pnl = -pnl

        self.trades_count += 1
        if pnl > 0:
            self.successful_trades += 1
        self.total_profit += pnl
        self.last_trade_time = datetime.now()

        self.logger.info(
            "📉 FLOW: %s zamyka pozycję %s @ %.2f (wejście %.2f, PnL %.4f)",
            self.bot_id,
            direction,
            price,
            entry_price,
            pnl,
        )

        self._current_position = None
        self._entry_price = None


class MomentumBotStrategy(BaseBot):
    """Strategia momentum wykorzystująca relację średnich kroczących."""

    def __init__(self, bot_id: str, config: BotConfig, data_manager: IntegratedDataManager):
        super().__init__(bot_id, config, data_manager)
        params = dict(config.parameters or {})
        self.short_window = max(int(params.get('short_window', 8)), 2)
        self.long_window = max(int(params.get('long_window', 21)), self.short_window + 1)
        threshold = float(params.get('momentum_threshold', 0.25))
        if threshold > 1:
            threshold = threshold / 100.0
        self.momentum_threshold = max(threshold, 0.0005)
        self.trade_amount = float(params.get('trade_amount', 250.0))
        self.cooldown_seconds = max(float(params.get('cooldown_seconds', 60.0)), 0.0)
        self._price_history: deque = deque(maxlen=max(self.long_window * 4, 120))
        self._position_size = 0.0
        self._entry_price: Optional[float] = None
        self._last_trade_time: Optional[datetime] = None

    async def _execute_strategy_logic(self):
        price_data = await self.get_current_price()
        if not price_data or not price_data.price or price_data.price <= 0:
            return

        price = float(price_data.price)
        self._price_history.append(price)
        if len(self._price_history) < self.long_window:
            return

        long_avg = sum(self._price_history) / len(self._price_history)
        if long_avg <= 0:
            return

        short_avg = sum(list(self._price_history)[-self.short_window:]) / self.short_window
        momentum = (short_avg - long_avg) / long_avg
        now = datetime.now()

        if self._last_trade_time and self.cooldown_seconds > 0:
            if (now - self._last_trade_time).total_seconds() < self.cooldown_seconds:
                return

        if self._position_size <= 0 and momentum >= self.momentum_threshold:
            quantity = max(self.trade_amount / price, 0.0)
            if quantity <= 0:
                return
            response = await self._place_order(OrderSide.BUY, quantity, price)
            if response:
                self._position_size = quantity
                self._entry_price = price
                self._last_trade_time = now
        elif self._position_size > 0 and momentum <= -self.momentum_threshold / 2:
            quantity = self._position_size
            response = await self._place_order(OrderSide.SELL, quantity, price)
            if response:
                actual_profit = (price - (self._entry_price or price)) * quantity
                self._register_manual_profit(response, quantity, actual_profit)
                self._position_size = 0.0
                self._entry_price = None
                self._last_trade_time = now

        await asyncio.sleep(0)


class MeanReversionBotStrategy(BaseBot):
    """Strategia mean reversion reagująca na odchylenia od średniej."""

    def __init__(self, bot_id: str, config: BotConfig, data_manager: IntegratedDataManager):
        super().__init__(bot_id, config, data_manager)
        params = dict(config.parameters or {})
        window = int(params.get('lookback_window', 30))
        self.lookback_window = max(window, 5)
        deviation = float(params.get('deviation_threshold', 1.0))
        if deviation > 1:
            deviation = deviation / 100.0
        self.deviation_threshold = max(deviation, 0.001)
        self.trade_amount = float(params.get('trade_amount', 300.0))
        self.max_position_minutes = max(int(params.get('max_position_minutes', 240)), 1)
        self.position_scaling = bool(params.get('position_scaling', False))
        self._price_history: deque = deque(maxlen=max(self.lookback_window * 4, 200))
        self._position_size = 0.0
        self._entry_price: Optional[float] = None
        self._position_open_time: Optional[datetime] = None

    async def _execute_strategy_logic(self):
        price_data = await self.get_current_price()
        if not price_data or not price_data.price or price_data.price <= 0:
            return

        price = float(price_data.price)
        self._price_history.append(price)
        if len(self._price_history) < self.lookback_window:
            return

        mean_price = sum(self._price_history) / len(self._price_history)
        if mean_price <= 0:
            return

        deviation = (price - mean_price) / mean_price
        now = datetime.now()

        if self._position_size <= 0 and deviation <= -self.deviation_threshold:
            quantity = max(self.trade_amount / price, 0.0)
            if quantity <= 0:
                return
            response = await self._place_order(OrderSide.BUY, quantity, price)
            if response:
                self._position_size = quantity
                self._entry_price = price
                self._position_open_time = now
        elif self._position_size > 0:
            if self.position_scaling and deviation <= -self.deviation_threshold * 1.5:
                addition = max(self.trade_amount / price, 0.0)
                if addition > 0:
                    response = await self._place_order(OrderSide.BUY, addition, price)
                    if response:
                        total_quantity = self._position_size + addition
                        if total_quantity > 0:
                            weighted_entry = (self._position_size * (self._entry_price or price)) + (addition * price)
                            self._entry_price = weighted_entry / total_quantity
                        self._position_size = total_quantity
                        self._position_open_time = now

            should_close = deviation >= self.deviation_threshold
            if not should_close and self._position_open_time:
                elapsed = (now - self._position_open_time).total_seconds()
                should_close = elapsed >= self.max_position_minutes * 60

            if should_close:
                await self._close_position(price)

        await asyncio.sleep(0)

    async def _close_position(self, price: float) -> None:
        if self._position_size <= 0:
            return
        quantity = self._position_size
        response = await self._place_order(OrderSide.SELL, quantity, price)
        if response:
            entry = self._entry_price or price
            actual_profit = (price - entry) * quantity
            self._register_manual_profit(response, quantity, actual_profit)
        self._position_size = 0.0
        self._entry_price = None
        self._position_open_time = None


class BreakoutBotStrategy(BaseBot):
    """Strategia breakout wykorzystująca potwierdzenia wybicia i trailing stop."""

    def __init__(self, bot_id: str, config: BotConfig, data_manager: IntegratedDataManager):
        super().__init__(bot_id, config, data_manager)
        params = dict(config.parameters or {})
        window = int(params.get('lookback_window', 40))
        self.lookback_window = max(window, 10)
        buffer_value = float(params.get('breakout_buffer', 0.3))
        if buffer_value > 1:
            buffer_value = buffer_value / 100.0
        self.breakout_buffer = max(buffer_value, 0.0005)
        trailing_value = float(params.get('trailing_stop_percentage', 0.8))
        if trailing_value > 1:
            trailing_value = trailing_value / 100.0
        self.trailing_stop = max(trailing_value, 0.0005)
        self.trade_amount = float(params.get('trade_amount', 350.0))
        self.confirmation_candles = max(int(params.get('confirmation_candles', 2)), 1)
        self._price_history: deque = deque(maxlen=max(self.lookback_window * 3, 150))
        self._position_size = 0.0
        self._entry_price: Optional[float] = None
        self._peak_price: Optional[float] = None
        self._confirmation_counter = 0

    async def _execute_strategy_logic(self):
        price_data = await self.get_current_price()
        if not price_data or not price_data.price or price_data.price <= 0:
            return

        price = float(price_data.price)
        self._price_history.append(price)
        if len(self._price_history) < self.lookback_window:
            return

        window = list(self._price_history)[-self.lookback_window:]
        window_high = max(window)
        window_low = min(window)
        upper_trigger = window_high * (1 + self.breakout_buffer)
        lower_trigger = window_low * (1 - self.breakout_buffer)

        if self._position_size <= 0:
            if price >= upper_trigger:
                self._confirmation_counter += 1
                if self._confirmation_counter >= self.confirmation_candles:
                    quantity = max(self.trade_amount / price, 0.0)
                    if quantity > 0:
                        response = await self._place_order(OrderSide.BUY, quantity, price)
                        if response:
                            self._position_size = quantity
                            self._entry_price = price
                            self._peak_price = price
                            self._confirmation_counter = 0
            else:
                self._confirmation_counter = 0
        else:
            if price > (self._peak_price or price):
                self._peak_price = price

            stop_price = (self._peak_price or price) * (1 - self.trailing_stop)
            exit_due_stop = price <= stop_price
            exit_due_failure = price <= lower_trigger

            if exit_due_stop or exit_due_failure:
                quantity = self._position_size
                response = await self._place_order(OrderSide.SELL, quantity, price)
                if response:
                    entry_price = self._entry_price or price
                    actual_profit = (price - entry_price) * quantity
                    self._register_manual_profit(response, quantity, actual_profit)
                self._position_size = 0.0
                self._entry_price = None
                self._peak_price = None
                self._confirmation_counter = 0

        await asyncio.sleep(0)


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

        self._default_user_id: Optional[int] = None
        self._bot_type_db_map = {
            BotType.DCA: "DCA",
            BotType.GRID: "Grid",
            BotType.SCALPING: "Scalping",
            BotType.CUSTOM: "Custom",
            BotType.AI: "AI",
            BotType.ARBITRAGE: "Arbitrage",
            BotType.SWING: "Swing",
            BotType.MOMENTUM: "Momentum",
            BotType.MEAN_REVERSION: "MeanReversion",
            BotType.BREAKOUT: "Breakout",
        }
        self._bot_type_reverse_map = {value.lower(): key for key, value in self._bot_type_db_map.items()}

        # Subskrypcja na zmiany konfiguracji
        self.event_bus.subscribe(EventTypes.CONFIG_UPDATED, self._on_config_updated)

        # Mapowanie typów strategii
        self.strategy_classes = {
            BotType.DCA: DCAStrategy,
            BotType.GRID: GridStrategy,
            BotType.SCALPING: ScalpingStrategy,
            BotType.AI: AIStrategy,
            BotType.ARBITRAGE: ArbitrageBotStrategy,
            BotType.SWING: SwingBotStrategy,
            BotType.MOMENTUM: MomentumBotStrategy,
            BotType.MEAN_REVERSION: MeanReversionBotStrategy,
            BotType.BREAKOUT: BreakoutBotStrategy,
            BotType.CUSTOM: BaseBot  # Fallback
        }

        logger.info("UpdatedBotManager initialized with UnifiedDataManager")

    def set_notification_manager(self, notification_manager) -> None:
        """Przypina NotificationManager do managera i aktywnych strategii."""
        self.notification_manager = notification_manager
        for strategy in self.active_bots.values():
            if hasattr(strategy, 'set_notification_manager'):
                try:
                    strategy.set_notification_manager(notification_manager)
                except Exception as exc:
                    logger.warning(f"Failed to attach NotificationManager to bot {strategy.bot_id}: {exc}")

    def _extract_db_id(self, bot_id: str) -> Optional[int]:
        if not bot_id:
            return None
        if isinstance(bot_id, str) and bot_id.startswith("bot_"):
            candidate = bot_id.split("_", 1)[1]
            try:
                return int(candidate)
            except (TypeError, ValueError):
                return None
        try:
            return int(bot_id)
        except (TypeError, ValueError):
            return None

    def _map_bot_type_to_db(self, bot_type: BotType) -> str:
        return self._bot_type_db_map.get(bot_type, "Custom")

    def _map_db_type_to_enum(self, db_type: Any) -> BotType:
        if isinstance(db_type, BotType):
            return db_type
        label = str(db_type or "custom").lower()
        return self._bot_type_reverse_map.get(label, BotType.CUSTOM)

    def _parse_datetime(self, value: Any) -> datetime:
        if isinstance(value, datetime):
            return value
        if value in (None, ""):
            return datetime.now()
        if isinstance(value, (int, float)):
            try:
                return datetime.fromtimestamp(float(value))
            except Exception:
                return datetime.now()
        text = str(value)
        for fmt in ("%Y-%m-%d %H:%M:%S", "%Y-%m-%dT%H:%M:%S", "%Y-%m-%d %H:%M:%S.%f", "%Y-%m-%dT%H:%M:%S.%f"):
            with contextlib.suppress(ValueError):
                return datetime.strptime(text, fmt)
        with contextlib.suppress(Exception):
            return datetime.fromisoformat(text)
        return datetime.now()

    def _determine_exchange(self, parameters: Dict[str, Any]) -> str:
        exchange = parameters.get('exchange') if parameters else None
        if exchange:
            return str(exchange)
        if self.config_manager:
            cfg_exchange = self.config_manager.get_setting('trading', 'default_exchange', None)
            if cfg_exchange:
                return str(cfg_exchange)
            cfg_exchange = self.config_manager.get_setting('exchanges', 'default', None)
            if cfg_exchange:
                return str(cfg_exchange)
        return 'binance'

    async def _resolve_default_user_id(self) -> Optional[int]:
        if self._default_user_id is not None:
            return self._default_user_id
        if not self.db_manager:
            return None

        candidate = None
        if self.config_manager:
            for scope, path in (("app", "user.default_id"), ("app", "auth.default_user_id"), ("user", "default_id")):
                candidate = self.config_manager.get_setting(scope, path, None)
                if candidate is not None:
                    break
        if candidate is not None:
            try:
                candidate_id = int(candidate)
                user = await self.db_manager.get_user(candidate_id)
                if user:
                    self._default_user_id = candidate_id
                    return self._default_user_id
            except Exception:
                pass

        first_user = await self.db_manager.get_first_user()
        if first_user:
            self._default_user_id = first_user['id']
            return self._default_user_id

        username = None
        email = None
        password = None
        if self.config_manager:
            username = self.config_manager.get_setting('user', 'default_username', None)
            email = self.config_manager.get_setting('user', 'default_email', None)
            password = self.config_manager.get_setting('user', 'default_password', None)
        if not username:
            username = 'operator'
        if not password:
            password = secrets.token_urlsafe(16)

        created = await self.db_manager.create_user(username, password, email)
        if created:
            self._default_user_id = created
            return created

        existing = await self.db_manager.get_user_by_username(username)
        if existing:
            self._default_user_id = existing['id']
            return self._default_user_id

        return None

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

            db_id: Optional[int] = None
            persistence_error: Optional[str] = None

            stored_parameters = dict(parameters or {})
            risk_payload = dict(risk_settings or {})
            if risk_payload:
                stored_parameters.setdefault('risk_settings', risk_payload)

            exchange = self._determine_exchange(stored_parameters)

            if self.db_manager:
                user_id = await self._resolve_default_user_id()
                if user_id is not None:
                    try:
                        db_id = await self.db_manager.create_bot(
                            user_id=user_id,
                            name=name,
                            bot_type=self._map_bot_type_to_db(bot_type),
                            exchange=exchange,
                            pair=symbol,
                            parameters=stored_parameters,
                        )
                    except Exception as exc:
                        persistence_error = str(exc)
                        logger.error(f"🤖 FLOW ERROR: Nie udało się zapisać bota w bazie: {exc}")
                else:
                    logger.warning("🤖 FLOW: Brak zdefiniowanego użytkownika – pomijam zapis w bazie")

            if not db_id:
                db_id = int(datetime.now().timestamp())
                if persistence_error:
                    logger.warning(
                        "🤖 FLOW: Używam tymczasowego ID %s dla bota %s z powodu błędu bazy danych",
                        db_id,
                        name,
                    )

            bot_id = f"bot_{db_id}"
            config = BotConfig(
                id=bot_id,
                name=name,
                bot_type=bot_type,
                symbol=symbol,
                parameters=dict(parameters or {}),
                risk_settings=risk_payload,
                active=False,
                created_at=datetime.now()
            )

            self.bot_configs[bot_id] = config

            logger.info(f"🤖 FLOW: Bot utworzony: {bot_id} ({name})")
            return bot_id

        except Exception as e:
            logger.error(f"🤖 FLOW ERROR: Błąd tworzenia bota: {e}")
            raise

    async def update_bot(self, bot_id: str, *, name: Optional[str] = None, bot_type: Optional[BotType] = None,
                          symbol: Optional[str] = None, parameters: Optional[Dict[str, Any]] = None,
                          risk_settings: Optional[Dict[str, Any]] = None) -> bool:
        """Aktualizuje konfigurację istniejącego bota."""
        try:
            if bot_id not in self.bot_configs:
                logger.error(f"Bot {bot_id} not found for update")
                return False

            config = self.bot_configs[bot_id]
            if name is not None:
                config.name = name
            if bot_type is not None:
                config.bot_type = bot_type
            if symbol is not None:
                config.symbol = symbol
            if parameters:
                config.parameters.update(parameters)
            if risk_settings is not None:
                config.risk_settings = dict(risk_settings)

            self.bot_configs[bot_id] = config

            if bot_id in self.active_bots:
                await self.active_bots[bot_id].update_parameters(parameters or {})

            if self.db_manager:
                db_id = self._extract_db_id(bot_id)
                if db_id is not None:
                    stored_parameters = dict(config.parameters or {})
                    if config.risk_settings:
                        stored_parameters['risk_settings'] = dict(config.risk_settings)
                    exchange = self._determine_exchange(stored_parameters)
                    with contextlib.suppress(Exception):
                        await self.db_manager.update_bot_config(
                            db_id,
                            name=config.name,
                            bot_type=self._map_bot_type_to_db(config.bot_type),
                            pair=config.symbol,
                            exchange=exchange,
                            parameters=stored_parameters,
                        )

            with contextlib.suppress(Exception):
                self.event_bus.publish(EventTypes.BOT_UPDATED, {'bot_id': bot_id, 'config': config})

            logger.info(f"🤖 FLOW: Bot {bot_id} updated")
            return True
        except Exception as exc:
            logger.error(f"🤖 FLOW ERROR: Failed to update bot {bot_id}: {exc}")
            return False

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

    async def shutdown(self, pause_only: bool = False) -> bool:
        """Zatrzymuje lub pauzuje wszystkie aktywne boty."""
        try:
            for bot_id in list(self.active_bots.keys()):
                strategy = self.active_bots.get(bot_id)
                if pause_only and strategy and hasattr(strategy, 'pause'):
                    try:
                        await strategy.pause()
                    except Exception as exc:
                        logger.warning(f"Error pausing bot {bot_id} during shutdown: {exc}")
                    continue

                await self.stop_bot(bot_id)

            if not pause_only:
                self.active_bots.clear()

            return True
        except Exception as exc:
            logger.error(f"Error during bot manager shutdown: {exc}")
            return False

    def get_running_bot_ids(self) -> List[str]:
        """Zwraca listę identyfikatorów aktualnie uruchomionych botów."""
        return [str(bot_id) for bot_id in self.active_bots.keys()]
    
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
            self.bot_configs.clear()

            if not self.db_manager:
                logger.info("Brak warstwy bazy danych – pomijam ładowanie botów")
                return

            user_id = await self._resolve_default_user_id()
            bots = await self.db_manager.get_all_bots(user_id=user_id)

            for bot in bots:
                db_id = bot.get('id')
                if db_id is None:
                    continue
                bot_id = f"bot_{db_id}"
                parameters = dict(bot.get('parameters') or {})
                risk_payload = parameters.pop('risk_settings', parameters.pop('_risk_settings', {}))
                config = BotConfig(
                    id=bot_id,
                    name=bot.get('name', bot_id),
                    bot_type=self._map_db_type_to_enum(bot.get('type')),
                    symbol=bot.get('pair', ''),
                    parameters=parameters,
                    risk_settings=dict(risk_payload or {}),
                    active=str(bot.get('status', '')).lower() == 'active',
                    created_at=self._parse_datetime(bot.get('created_at')),
                )
                self.bot_configs[bot_id] = config

            logger.info("Saved bots loaded: %d", len(self.bot_configs))

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

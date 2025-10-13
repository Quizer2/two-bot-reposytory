"""
Grid Trading Strategy - Strategia handlowa oparta na siatce zleceń
"""

import asyncio
import time
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple, Any
from dataclasses import dataclass
from enum import Enum

from ..exchange.base_exchange import BaseExchange
from ..database import DatabaseManager
from ..risk_management import RiskManager
from utils.logger import get_logger
from utils.helpers import FormatHelper, CalculationHelper
import logging
logger = logging.getLogger(__name__)


class GridStatus(Enum):
    """Status strategii Grid"""
    INACTIVE = "inactive"
    ACTIVE = "active"
    PAUSED = "paused"
    STOPPED = "stopped"
    ERROR = "error"
    COMPLETED = "completed"


@dataclass
class GridLevel:
    """Poziom siatki"""
    price: float
    buy_order_id: Optional[str] = None
    sell_order_id: Optional[str] = None
    buy_filled: bool = False
    sell_filled: bool = False
    amount: float = 0.0


@dataclass
class GridOrder:
    """Zlecenie Grid"""
    id: str
    timestamp: datetime
    level: int
    side: str  # 'buy' lub 'sell'
    price: float
    amount: float
    status: str  # 'pending', 'filled', 'cancelled'
    exchange_order_id: Optional[str] = None
    profit: float = 0.0


@dataclass
class GridStatistics:
    """Statystyki strategii Grid"""
    total_trades: int = 0
    successful_trades: int = 0
    failed_trades: int = 0
    total_profit: float = 0.0
    total_fees: float = 0.0
    net_profit: float = 0.0
    profit_percentage: float = 0.0
    active_orders: int = 0
    filled_levels: int = 0
    current_price: float = 0.0
    price_range_utilization: float = 0.0


class GridStrategy:
    """
    Strategia Grid Trading
    
    Tworzy siatkę zleceń kupna i sprzedaży w określonym zakresie cenowym.
    Gdy zlecenie zostanie zrealizowane, automatycznie tworzy nowe zlecenie
    na przeciwnym poziomie.
    """
    
    def __init__(self, bot_id: str, parameters: Dict[str, Any]):
        """
        Inicjalizacja strategii Grid
        
        Args:
            bot_id: Identyfikator bota
            parameters: Parametry strategii zawierające:
                - pair: Para handlowa (np. 'BTC/USDT')
                - min_price: Minimalna cena siatki
                - max_price: Maksymalna cena siatki
                - grid_levels: Liczba poziomów siatki
                - investment_amount: Kwota inwestycji
                - trailing_stop: Czy używać trailing stop (opcjonalne)
                - dynamic_grid: Czy używać dynamicznej siatki (opcjonalne)
                - stop_loss: Procent stop loss (opcjonalne)
                - take_profit: Procent take profit (opcjonalne)
        """
        self.bot_id = bot_id
        self.parameters = parameters
        self.logger = get_logger(f"GridStrategy_{bot_id}")
        
        # Walidacja parametrów
        self._validate_parameters()
        
        # Status strategii
        self.status = GridStatus.INACTIVE
        self.is_running = False
        self.should_stop = False
        
        # Komponenty
        self.exchange: Optional[BaseExchange] = None
        self.db_manager: Optional[DatabaseManager] = None
        self.risk_manager: Optional[RiskManager] = None
        
        # Dane strategii
        self.grid_levels: List[GridLevel] = []
        self.orders: List[GridOrder] = []
        self.statistics = GridStatistics()
        
        # Parametry siatki
        self.min_price = parameters['min_price']
        self.max_price = parameters['max_price']
        self.grid_count = parameters['grid_levels']
        self.investment_amount = parameters['investment_amount']
        
        # Oblicz parametry siatki
        self._calculate_grid_parameters()
    
    def _validate_parameters(self):
        """Waliduje parametry strategii"""
        required_params = ['pair', 'min_price', 'max_price', 'grid_levels', 'investment_amount']
        
        for param in required_params:
            if param not in self.parameters:
                raise ValueError(f"Missing required parameter: {param}")
        
        # Walidacja wartości
        if self.parameters['min_price'] >= self.parameters['max_price']:
            raise ValueError("min_price must be less than max_price")
        
        if self.parameters['grid_levels'] < 2:
            raise ValueError("grid_levels must be at least 2")
        
        if self.parameters['investment_amount'] <= 0:
            raise ValueError("investment_amount must be positive")
    
    def _calculate_grid_parameters(self):
        """Oblicza parametry siatki"""
        price_range = self.max_price - self.min_price
        self.grid_step = price_range / (self.grid_count - 1)
        self.amount_per_level = self.investment_amount / self.grid_count
        
        # Tworzenie poziomów siatki
        self.grid_levels = []
        for i in range(self.grid_count):
            price = self.min_price + (i * self.grid_step)
            level = GridLevel(
                price=price,
                amount=self.amount_per_level  # Kwota USD na poziom
            )
            self.grid_levels.append(level)
    
    async def initialize(self, db_manager: DatabaseManager, risk_manager: RiskManager, 
                        exchange: BaseExchange, data_manager=None):
        """Inicjalizuje strategię z komponentami"""
        self.db_manager = db_manager
        self.risk_manager = risk_manager
        self.exchange = exchange
        self.data_manager = data_manager
        
        # Załaduj historię zleceń
        await self._load_order_history()
        
        # Oblicz statystyki
        await self._calculate_statistics()
        
        self.logger.info(f"Grid strategy initialized for {self.parameters['pair']}")
    
    async def start(self):
        """Uruchamia strategię Grid"""
        if self.is_running:
            self.logger.warning("Grid strategy is already running")
            return
        
        try:
            self.is_running = True
            self.should_stop = False
            self.status = GridStatus.ACTIVE
            
            self.logger.info(f"Starting Grid strategy for {self.parameters['pair']}")
            
            # Sprawdź aktualną cenę i ustaw początkowe zlecenia
            await self._setup_initial_grid()
            
            # Główna pętla strategii
            while self.is_running and not self.should_stop:
                try:
                    # Sprawdź status zleceń
                    await self._check_order_status()
                    
                    # Zarządzaj siatką
                    await self._manage_grid()
                    
                    # Sprawdź warunki stop loss / take profit
                    await self._check_exit_conditions()
                    
                    # Aktualizuj statystyki
                    await self._calculate_statistics()
                    
                    # Pauza przed następną iteracją
                    await asyncio.sleep(30)  # Sprawdzaj co 30 sekund
                    
                except Exception as e:
                    self.logger.error(f"Error in Grid strategy loop: {e}")
                    await asyncio.sleep(60)
            
        except Exception as e:
            self.logger.error(f"Fatal error in Grid strategy: {e}")
            self.status = GridStatus.ERROR
        finally:
            self.is_running = False
            if self.status == GridStatus.ACTIVE:
                self.status = GridStatus.STOPPED
    
    async def stop(self):
        """Zatrzymuje strategię Grid"""
        self.logger.info("Stopping Grid strategy")
        self.should_stop = True
        self.is_running = False
        self.status = GridStatus.STOPPED
        
        # Anuluj wszystkie aktywne zlecenia
        await self._cancel_all_orders()
    
    async def pause(self):
        """Wstrzymuje strategię Grid"""
        self.logger.info("Pausing Grid strategy")
        self.status = GridStatus.PAUSED
    
    async def resume(self):
        """Wznawia strategię Grid"""
        self.logger.info("Resuming Grid strategy")
        self.status = GridStatus.ACTIVE
    
    async def _setup_initial_grid(self):
        """Ustawia początkową siatkę zleceń"""
        try:
            current_price = await self.exchange.get_current_price(self.parameters['pair'])
            if not current_price:
                raise Exception("Failed to get current price")
            
            self.statistics.current_price = current_price
            
            # Sprawdź czy cena jest w zakresie siatki
            if current_price < self.min_price or current_price > self.max_price:
                self.logger.warning(
                    f"Current price {current_price} is outside grid range "
                    f"[{self.min_price}, {self.max_price}]"
                )
            
            # Ustaw zlecenia kupna poniżej aktualnej ceny
            # i zlecenia sprzedaży powyżej aktualnej ceny
            for i, level in enumerate(self.grid_levels):
                if level.price < current_price:
                    # Zlecenie kupna
                    await self._place_buy_order(i, level)
                elif level.price > current_price:
                    # Zlecenie sprzedaży (jeśli mamy środki)
                    await self._place_sell_order(i, level)
            
        except Exception as e:
            self.logger.error(f"Error setting up initial grid: {e}")
            raise
    
    async def _place_buy_order(self, level_index: int, level: GridLevel):
        """Składa zlecenie kupna na danym poziomie"""
        try:
            pair = self.parameters['pair']
            
            # Oblicz ilość kryptowaluty z kwoty USD
            from utils.helpers import TradingHelpers
            crypto_amount = TradingHelpers.calculate_crypto_amount_from_usd(level.amount, level.price)
            
            # Sprawdź zarządzanie ryzykiem
            if not await self.risk_manager.check_order_risk(
                self.bot_id, pair, 'buy', crypto_amount, level.price
            ):
                self.logger.warning(f"Buy order rejected by risk management at level {level_index}")
                return
            
            # Trace log przed składaniem zlecenia
            logger.info(f"TRACE: order.submitted - symbol={pair}, side=buy, amount={crypto_amount}, type=limit, strategy=grid")
            
            # Złóż zlecenie
            order_result = await self.exchange.create_order(
                pair=pair,
                side='buy',
                amount=crypto_amount,
                price=level.price,
                order_type='limit'
            )
            
            if order_result and order_result.get('success'):
                level.buy_order_id = order_result.get('order_id')
                
                # Zapisz zlecenie
                grid_order = GridOrder(
                    id=f"grid_buy_{self.bot_id}_{level_index}_{int(time.time())}",
                    timestamp=datetime.now(),
                    level=level_index,
                    side='buy',
                    price=level.price,
                    amount=crypto_amount,
                    status='pending',
                    exchange_order_id=level.buy_order_id
                )
                
                self.orders.append(grid_order)
                await self._save_order_to_db(grid_order)
                
                self.logger.info(
                    f"Buy order placed at level {level_index}: "
                    f"{crypto_amount:.8f} crypto (${level.amount:.2f} USD) at {level.price:.8f}"
                )
            else:
                self.logger.error(f"Failed to place buy order at level {level_index}: {order_result}")
                
        except Exception as e:
            self.logger.error(f"Error placing buy order at level {level_index}: {e}")
    
    async def _place_sell_order(self, level_index: int, level: GridLevel):
        """Składa zlecenie sprzedaży na danym poziomie"""
        try:
            pair = self.parameters['pair']
            base_currency = pair.split('/')[0]  # BTC w BTC/USDT
            
            # Sprawdź saldo
            balance = await self.exchange.get_balance()
            if base_currency not in balance or balance[base_currency]['free'] < level.amount:
                self.logger.debug(f"Insufficient balance for sell order at level {level_index}")
                return
            
            # Sprawdź zarządzanie ryzykiem
            if not await self.risk_manager.check_order_risk(
                self.bot_id, pair, 'sell', level.amount, level.price
            ):
                self.logger.warning(f"Sell order rejected by risk management at level {level_index}")
                return
            
            # Trace log przed składaniem zlecenia
            logger.info(f"TRACE: order.submitted - symbol={pair}, side=sell, amount={level.amount}, type=limit, strategy=grid")
            
            # Złóż zlecenie
            order_result = await self.exchange.create_order(
                pair=pair,
                side='sell',
                amount=level.amount,
                price=level.price,
                order_type='limit'
            )
            
            if order_result and order_result.get('success'):
                level.sell_order_id = order_result.get('order_id')
                
                # Zapisz zlecenie
                grid_order = GridOrder(
                    id=f"grid_sell_{self.bot_id}_{level_index}_{int(time.time())}",
                    timestamp=datetime.now(),
                    level=level_index,
                    side='sell',
                    price=level.price,
                    amount=level.amount,
                    status='pending',
                    exchange_order_id=level.sell_order_id
                )
                
                self.orders.append(grid_order)
                await self._save_order_to_db(grid_order)
                
                self.logger.info(
                    f"Sell order placed at level {level_index}: "
                    f"{level.amount:.8f} at {level.price:.8f}"
                )
            else:
                self.logger.error(f"Failed to place sell order at level {level_index}: {order_result}")
                
        except Exception as e:
            self.logger.error(f"Error placing sell order at level {level_index}: {e}")
    
    async def _check_order_status(self):
        """Sprawdza status wszystkich aktywnych zleceń"""
        for order in self.orders:
            if order.status == 'pending' and order.exchange_order_id:
                try:
                    status = await self.exchange.get_order_status(order.exchange_order_id)
                    
                    if status and status.get('status') == 'filled':
                        order.status = 'filled'
                        
                        # Aktualizuj poziom siatki
                        level = self.grid_levels[order.level]
                        if order.side == 'buy':
                            level.buy_filled = True
                        else:
                            level.sell_filled = True
                        
                        self.logger.info(
                            f"Order filled: {order.side} {order.amount:.8f} "
                            f"at {order.price:.8f} (level {order.level})"
                        )
                        
                        # Aktualizuj w bazie danych
                        await self._update_order_in_db(order)
                        
                except Exception as e:
                    self.logger.error(f"Error checking order status {order.id}: {e}")
    
    async def _manage_grid(self):
        """Zarządza siatką - tworzy nowe zlecenia po wypełnieniu"""
        for i, level in enumerate(self.grid_levels):
            try:
                # Jeśli zlecenie kupna zostało wypełnione, utwórz zlecenie sprzedaży
                if level.buy_filled and not level.sell_order_id:
                    await self._place_sell_order(i, level)
                    level.buy_filled = False  # Reset flagi
                
                # Jeśli zlecenie sprzedaży zostało wypełnione, utwórz zlecenie kupna
                if level.sell_filled and not level.buy_order_id:
                    await self._place_buy_order(i, level)
                    level.sell_filled = False  # Reset flagi
                    
            except Exception as e:
                self.logger.error(f"Error managing grid level {i}: {e}")
    
    async def _check_exit_conditions(self):
        """Sprawdza warunki wyjścia (stop loss / take profit)"""
        try:
            current_price = await self.exchange.get_current_price(self.parameters['pair'])
            if not current_price:
                return
            
            self.statistics.current_price = current_price
            
            # Sprawdź stop loss
            if 'stop_loss' in self.parameters:
                stop_loss_percent = self.parameters['stop_loss']
                # Oblicz średnią cenę pozycji
                avg_price = self._calculate_average_position_price()
                if avg_price > 0:
                    loss_percent = ((current_price - avg_price) / avg_price) * 100
                    if loss_percent <= -stop_loss_percent:
                        await self._execute_exit("stop_loss", current_price)
                        return
            
            # Sprawdź take profit
            if 'take_profit' in self.parameters:
                take_profit_percent = self.parameters['take_profit']
                if self.statistics.profit_percentage >= take_profit_percent:
                    await self._execute_exit("take_profit", current_price)
                    return
            
            # Sprawdź czy cena wyszła poza zakres siatki
            if current_price < self.min_price * 0.9 or current_price > self.max_price * 1.1:
                self.logger.warning(
                    f"Price {current_price} is significantly outside grid range. "
                    f"Consider adjusting grid or stopping strategy."
                )
                
        except Exception as e:
            self.logger.error(f"Error checking exit conditions: {e}")
    
    def _calculate_average_position_price(self) -> float:
        """Oblicza średnią cenę pozycji"""
        filled_buy_orders = [o for o in self.orders if o.status == 'filled' and o.side == 'buy']
        
        if not filled_buy_orders:
            return 0.0
        
        total_cost = sum(o.price * o.amount for o in filled_buy_orders)
        total_amount = sum(o.amount for o in filled_buy_orders)
        
        return total_cost / total_amount if total_amount > 0 else 0.0
    
    async def _execute_exit(self, reason: str, price: float):
        """Wykonuje wyjście z pozycji"""
        try:
            self.logger.info(f"Executing exit ({reason}) at price {price}")
            
            # Anuluj wszystkie aktywne zlecenia
            await self._cancel_all_orders()
            
            # Sprzedaj wszystkie posiadane aktywa
            pair = self.parameters['pair']
            base_currency = pair.split('/')[0]
            balance = await self.exchange.get_balance()
            
            if base_currency in balance and balance[base_currency]['free'] > 0:
                amount = balance[base_currency]['free']
                
                order_result = await self.exchange.create_order(
                    pair=pair,
                    side='sell',
                    amount=amount,
                    price=None,
                    order_type='market'
                )
                
                if order_result and order_result.get('success'):
                    self.logger.info(f"Exit order executed: Sold {amount:.8f} at market price")
                else:
                    self.logger.error(f"Failed to execute exit order: {order_result}")
            
            # Zatrzymaj strategię
            self.status = GridStatus.COMPLETED
            await self.stop()
            
        except Exception as e:
            self.logger.error(f"Error executing exit: {e}")
    
    async def _cancel_all_orders(self):
        """Anuluje wszystkie aktywne zlecenia"""
        for order in self.orders:
            if order.status == 'pending' and order.exchange_order_id:
                try:
                    await self.exchange.cancel_order(order.exchange_order_id)
                    order.status = 'cancelled'
                    await self._update_order_in_db(order)
                    
                except Exception as e:
                    self.logger.error(f"Error cancelling order {order.id}: {e}")
        
        # Wyczyść ID zleceń w poziomach siatki
        for level in self.grid_levels:
            level.buy_order_id = None
            level.sell_order_id = None
    
    async def _calculate_statistics(self):
        """Oblicza statystyki strategii"""
        # Podstawowe statystyki
        self.statistics.total_trades = len([o for o in self.orders if o.status == 'filled'])
        self.statistics.successful_trades = self.statistics.total_trades
        self.statistics.failed_trades = len([o for o in self.orders if o.status == 'cancelled'])
        self.statistics.active_orders = len([o for o in self.orders if o.status == 'pending'])
        
        # Oblicz zyski
        filled_orders = [o for o in self.orders if o.status == 'filled']
        buy_orders = [o for o in filled_orders if o.side == 'buy']
        sell_orders = [o for o in filled_orders if o.side == 'sell']
        
        total_bought = sum(o.price * o.amount for o in buy_orders)
        total_sold = sum(o.price * o.amount for o in sell_orders)
        
        self.statistics.total_profit = total_sold - total_bought
        self.statistics.profit_percentage = (
            (self.statistics.total_profit / self.investment_amount) * 100
            if self.investment_amount > 0 else 0
        )
        
        # Wykorzystanie zakresu cenowego
        if self.statistics.current_price > 0:
            price_position = (self.statistics.current_price - self.min_price) / (self.max_price - self.min_price)
            self.statistics.price_range_utilization = max(0, min(100, price_position * 100))
    
    async def _load_order_history(self):
        """Ładuje historię zleceń z bazy danych"""
        try:
            # TODO: Implementuj ładowanie z bazy danych
            pass
        except Exception as e:
            self.logger.error(f"Error loading order history: {e}")
    
    async def _save_order_to_db(self, order: GridOrder):
        """Zapisuje zlecenie do bazy danych"""
        try:
            # TODO: Implementuj zapis do bazy danych
            pass
        except Exception as e:
            self.logger.error(f"Error saving order to database: {e}")
    
    async def _update_order_in_db(self, order: GridOrder):
        """Aktualizuje zlecenie w bazie danych"""
        try:
            # TODO: Implementuj aktualizację w bazie danych
            pass
        except Exception as e:
            self.logger.error(f"Error updating order in database: {e}")
    
    def get_status(self) -> Dict[str, Any]:
        """Zwraca status strategii"""
        return {
            'bot_id': self.bot_id,
            'strategy': 'Grid',
            'status': self.status.value,
            'pair': self.parameters['pair'],
            'parameters': self.parameters,
            'grid_info': {
                'min_price': self.min_price,
                'max_price': self.max_price,
                'grid_step': self.grid_step,
                'levels_count': len(self.grid_levels),
                'amount_per_level': self.amount_per_level
            },
            'statistics': {
                'total_trades': self.statistics.total_trades,
                'successful_trades': self.statistics.successful_trades,
                'failed_trades': self.statistics.failed_trades,
                'total_profit': self.statistics.total_profit,
                'profit_percentage': self.statistics.profit_percentage,
                'active_orders': self.statistics.active_orders,
                'current_price': self.statistics.current_price,
                'price_range_utilization': self.statistics.price_range_utilization
            }
        }
    
    def update_parameters(self, new_parameters: Dict[str, Any]):
        """Aktualizuje parametry strategii"""
        # Waliduj nowe parametry
        old_parameters = self.parameters.copy()
        self.parameters.update(new_parameters)
        
        try:
            self._validate_parameters()
            
            # Jeśli zmieniono parametry siatki, przelicz je
            if any(param in new_parameters for param in ['min_price', 'max_price', 'grid_levels', 'investment_amount']):
                self.min_price = self.parameters['min_price']
                self.max_price = self.parameters['max_price']
                self.grid_count = self.parameters['grid_levels']
                self.investment_amount = self.parameters['investment_amount']
                self._calculate_grid_parameters()
                
                self.logger.info("Grid parameters recalculated due to parameter update")
            
            self.logger.info("Parameters updated successfully")
            
        except Exception as e:
            # Przywróć stare parametry w przypadku błędu
            self.parameters = old_parameters
            self.logger.error(f"Failed to update parameters: {e}")
            raise
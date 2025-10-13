"""
Strategia DCA (Dollar Cost Averaging) - Uśrednianie kosztów
Regularne zakupy kryptowaluty w określonych interwałach czasowych
"""

import asyncio
import time
from datetime import datetime, timedelta
from typing import Dict, Any, Optional, List
from dataclasses import dataclass
from enum import Enum

from ..exchange import get_exchange_adapter
from ..database import DatabaseManager
from ..risk_management import RiskManager
from utils.logger import get_logger, LogType
from utils.helpers import ValidationHelper, CalculationHelper
import logging
logger = logging.getLogger(__name__)


class DCAStatus(Enum):
    """Status strategii DCA"""
    ACTIVE = "active"
    PAUSED = "paused"
    STOPPED = "stopped"
    ERROR = "error"
    COMPLETED = "completed"


@dataclass
class DCAOrder:
    """Reprezentuje pojedyncze zlecenie DCA"""
    id: str
    timestamp: datetime
    pair: str
    amount: float
    price: float
    status: str
    exchange_order_id: Optional[str] = None
    error_message: Optional[str] = None


@dataclass
class DCAStatistics:
    """Statystyki strategii DCA"""
    total_invested: float = 0.0
    total_purchased: float = 0.0
    average_price: float = 0.0
    current_value: float = 0.0
    unrealized_pnl: float = 0.0
    unrealized_pnl_percent: float = 0.0
    orders_count: int = 0
    successful_orders: int = 0
    failed_orders: int = 0


class DCAStrategy:
    """
    Strategia Dollar Cost Averaging
    
    Parametry obowiązkowe:
    - pair: Para handlowa (np. BTC/USDT)
    - amount: Kwota zakupu w walucie bazowej
    - interval: Interwał czasowy między zakupami (w minutach)
    
    Parametry opcjonalne:
    - stop_loss: Procent stop loss
    - take_profit: Procent take profit
    - max_position: Maksymalna pozycja
    - max_orders: Maksymalna liczba zleceń
    - start_time: Czas rozpoczęcia
    - end_time: Czas zakończenia
    """
    
    def __init__(self, bot_id: str, exchange_name: str, parameters: Dict[str, Any]):
        self.bot_id = bot_id
        self.exchange_name = exchange_name
        self.parameters = parameters
        self.status = DCAStatus.STOPPED
        
        # Komponenty
        self.exchange = None
        self.db_manager = None
        self.risk_manager = None
        self.logger = get_logger(f"dca_bot_{bot_id}", LogType.BOT)
        
        # Stan strategii
        self.orders: List[DCAOrder] = []
        self.statistics = DCAStatistics()
        self.last_order_time: Optional[datetime] = None
        self.next_order_time: Optional[datetime] = None
        
        # Flagi kontrolne
        self.is_running = False
        self.should_stop = False
        
        # Walidacja parametrów
        self._validate_parameters()
    
    def _validate_parameters(self):
        """Waliduje parametry strategii"""
        required_params = ['pair', 'amount', 'interval']
        
        for param in required_params:
            if param not in self.parameters:
                raise ValueError(f"Missing required parameter: {param}")
        
        # Walidacja pary handlowej
        if not ValidationHelper.validate_trading_pair(self.parameters['pair']):
            raise ValueError(f"Invalid trading pair: {self.parameters['pair']}")
        
        # Walidacja kwoty
        if not ValidationHelper.validate_amount(self.parameters['amount']):
            raise ValueError(f"Invalid amount: {self.parameters['amount']}")
        
        # Walidacja interwału
        interval = self.parameters['interval']
        if not isinstance(interval, (int, float)) or interval <= 0:
            raise ValueError(f"Invalid interval: {interval}")
        
        # Walidacja parametrów opcjonalnych
        if 'stop_loss' in self.parameters:
            if not ValidationHelper.validate_percentage(self.parameters['stop_loss']):
                raise ValueError(f"Invalid stop_loss: {self.parameters['stop_loss']}")
        
        if 'take_profit' in self.parameters:
            if not ValidationHelper.validate_percentage(self.parameters['take_profit']):
                raise ValueError(f"Invalid take_profit: {self.parameters['take_profit']}")
    
    async def initialize(self, db_manager: DatabaseManager, risk_manager: RiskManager, exchange=None, data_manager=None):
        """Inicjalizuje strategię"""
        try:
            self.db_manager = db_manager
            self.risk_manager = risk_manager
            self.data_manager = data_manager
            
            # Inicjalizacja adaptera giełdy
            if exchange:
                self.exchange = exchange
            else:
                # Fallback - tworzenie exchange bez kluczy API (tryb demo)
                self.exchange = get_exchange_adapter(self.exchange_name)
            
            if not self.exchange:
                raise Exception(f"Failed to get exchange adapter for {self.exchange_name}")
            
            # Ładowanie historii zleceń
            await self._load_order_history()
            
            # Obliczenie statystyk
            await self._calculate_statistics()
            
            # Ustawienie czasu następnego zlecenia
            self._calculate_next_order_time()
            
            self.logger.info(f"DCA strategy initialized for {self.parameters['pair']}")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to initialize DCA strategy: {e}")
            return False
    
    async def start(self):
        """Uruchamia strategię DCA"""
        if self.is_running:
            self.logger.warning("DCA strategy is already running")
            return
        
        try:
            self.is_running = True
            self.should_stop = False
            self.status = DCAStatus.ACTIVE
            
            self.logger.info(f"Starting DCA strategy for {self.parameters['pair']}")
            
            # Główna pętla strategii
            while self.is_running and not self.should_stop:
                try:
                    # Sprawdź czy czas na następne zlecenie
                    if self._should_place_order():
                        await self._place_dca_order()
                    
                    # Sprawdź warunki stop loss / take profit
                    await self._check_exit_conditions()
                    
                    # Sprawdź limity
                    if await self._check_limits():
                        break
                    
                    # Aktualizuj statystyki
                    await self._calculate_statistics()
                    
                    # Pauza przed następną iteracją
                    await asyncio.sleep(60)  # Sprawdzaj co minutę
                    
                except Exception as e:
                    self.logger.error(f"Error in DCA strategy loop: {e}")
                    await asyncio.sleep(60)
            
        except Exception as e:
            self.logger.error(f"Fatal error in DCA strategy: {e}")
            self.status = DCAStatus.ERROR
        finally:
            self.is_running = False
            if self.status == DCAStatus.ACTIVE:
                self.status = DCAStatus.STOPPED
    
    async def stop(self):
        """Zatrzymuje strategię DCA"""
        self.logger.info("Stopping DCA strategy")
        self.should_stop = True
        self.is_running = False
        self.status = DCAStatus.STOPPED
    
    async def pause(self):
        """Wstrzymuje strategię DCA"""
        self.logger.info("Pausing DCA strategy")
        self.status = DCAStatus.PAUSED
    
    async def resume(self):
        """Wznawia strategię DCA"""
        self.logger.info("Resuming DCA strategy")
        self.status = DCAStatus.ACTIVE
    
    def _should_place_order(self) -> bool:
        """Sprawdza czy należy złożyć zlecenie"""
        if self.status != DCAStatus.ACTIVE:
            return False
        
        if not self.next_order_time:
            return True
        
        return datetime.now() >= self.next_order_time
    
    async def _place_dca_order(self):
        """Składa zlecenie DCA"""
        try:
            pair = self.parameters['pair']
            amount = self.parameters['amount']
            
            # Sprawdź saldo
            balance = await self.exchange.get_balance()
            base_currency = pair.split('/')[1]  # USDT w BTC/USDT
            
            if base_currency not in balance or balance[base_currency]['free'] < amount:
                self.logger.warning(f"Insufficient balance for DCA order. Required: {amount} {base_currency}")
                return
            
            # Pobierz aktualną cenę
            current_price = await self.exchange.get_current_price(pair)
            if not current_price:
                self.logger.error(f"Failed to get current price for {pair}")
                return
            
            # Oblicz ilość do zakupu
            quantity = amount / current_price
            
            # Sprawdź zarządzanie ryzykiem
            if not await self.risk_manager.check_order_risk(
                self.bot_id, pair, 'buy', quantity, current_price
            ):
                self.logger.warning("Order rejected by risk management")
                return
            
            # Złóż zlecenie
            logger.info(f"TRACE: order.submitted - symbol={pair}, side=buy, amount={quantity}, type=market, strategy=DCA")
            order_result = await self.exchange.create_order(
                pair=pair,
                side='buy',
                amount=quantity,
                price=None,  # Market order
                order_type='market'
            )
            
            if order_result and order_result.get('success'):
                # Zapisz zlecenie
                dca_order = DCAOrder(
                    id=f"dca_{self.bot_id}_{int(time.time())}",
                    timestamp=datetime.now(),
                    pair=pair,
                    amount=amount,
                    price=current_price,
                    status='filled',
                    exchange_order_id=order_result.get('order_id')
                )
                
                self.orders.append(dca_order)
                
                # Zapisz do bazy danych
                await self._save_order_to_db(dca_order)
                
                # Aktualizuj czasy
                self.last_order_time = datetime.now()
                self._calculate_next_order_time()
                
                self.logger.info(
                    f"DCA order placed: {quantity:.8f} {pair.split('/')[0]} "
                    f"at {current_price:.8f} for {amount} {base_currency}"
                )
                
            else:
                self.logger.error(f"Failed to place DCA order: {order_result}")
                
        except Exception as e:
            self.logger.error(f"Error placing DCA order: {e}")
    
    async def _check_exit_conditions(self):
        """Sprawdza warunki wyjścia (stop loss / take profit)"""
        if not self.orders or self.statistics.total_purchased == 0:
            return
        
        try:
            pair = self.parameters['pair']
            current_price = await self.exchange.get_current_price(pair)
            
            if not current_price:
                return
            
            # Sprawdź stop loss
            if 'stop_loss' in self.parameters:
                stop_loss_percent = self.parameters['stop_loss']
                loss_percent = ((current_price - self.statistics.average_price) / self.statistics.average_price) * 100
                
                if loss_percent <= -stop_loss_percent:
                    await self._execute_exit("stop_loss", current_price)
                    return
            
            # Sprawdź take profit
            if 'take_profit' in self.parameters:
                take_profit_percent = self.parameters['take_profit']
                profit_percent = ((current_price - self.statistics.average_price) / self.statistics.average_price) * 100
                
                if profit_percent >= take_profit_percent:
                    await self._execute_exit("take_profit", current_price)
                    return
                    
        except Exception as e:
            self.logger.error(f"Error checking exit conditions: {e}")
    
    async def _execute_exit(self, reason: str, price: float):
        """Wykonuje wyjście z pozycji"""
        try:
            pair = self.parameters['pair']
            
            # Sprzedaj całą pozycję
            order_result = await self.exchange.create_order(
                pair=pair,
                side='sell',
                amount=self.statistics.total_purchased,
                price=None,
                order_type='market'
            )
            
            if order_result and order_result.get('success'):
                self.logger.info(
                    f"Exit executed ({reason}): Sold {self.statistics.total_purchased:.8f} "
                    f"at {price:.8f} (avg buy: {self.statistics.average_price:.8f})"
                )
                
                # Zatrzymaj strategię
                self.status = DCAStatus.COMPLETED
                await self.stop()
            else:
                self.logger.error(f"Failed to execute exit: {order_result}")
                
        except Exception as e:
            self.logger.error(f"Error executing exit: {e}")
    
    async def _check_limits(self) -> bool:
        """Sprawdza limity strategii"""
        # Sprawdź maksymalną liczbę zleceń
        if 'max_orders' in self.parameters:
            if len(self.orders) >= self.parameters['max_orders']:
                self.logger.info("Maximum number of orders reached")
                self.status = DCAStatus.COMPLETED
                return True
        
        # Sprawdź maksymalną pozycję
        if 'max_position' in self.parameters:
            if self.statistics.total_invested >= self.parameters['max_position']:
                self.logger.info("Maximum position reached")
                self.status = DCAStatus.COMPLETED
                return True
        
        # Sprawdź czas zakończenia
        if 'end_time' in self.parameters:
            end_time = datetime.fromisoformat(self.parameters['end_time'])
            if datetime.now() >= end_time:
                self.logger.info("End time reached")
                self.status = DCAStatus.COMPLETED
                return True
        
        return False
    
    def _calculate_next_order_time(self):
        """Oblicza czas następnego zlecenia"""
        interval_minutes = self.parameters['interval']
        
        if self.last_order_time:
            self.next_order_time = self.last_order_time + timedelta(minutes=interval_minutes)
        else:
            # Pierwsze zlecenie
            if 'start_time' in self.parameters:
                self.next_order_time = datetime.fromisoformat(self.parameters['start_time'])
            else:
                self.next_order_time = datetime.now()
    
    async def _calculate_statistics(self):
        """Oblicza statystyki strategii"""
        if not self.orders:
            return
        
        # Podstawowe statystyki
        self.statistics.orders_count = len(self.orders)
        self.statistics.successful_orders = len([o for o in self.orders if o.status == 'filled'])
        self.statistics.failed_orders = self.statistics.orders_count - self.statistics.successful_orders
        
        filled_orders = [o for o in self.orders if o.status == 'filled']
        
        if filled_orders:
            self.statistics.total_invested = sum(o.amount for o in filled_orders)
            self.statistics.total_purchased = sum(o.amount / o.price for o in filled_orders)
            self.statistics.average_price = self.statistics.total_invested / self.statistics.total_purchased
            
            # Aktualna wartość i P&L
            try:
                current_price = await self.exchange.get_current_price(self.parameters['pair'])
                if current_price:
                    self.statistics.current_value = self.statistics.total_purchased * current_price
                    self.statistics.unrealized_pnl = self.statistics.current_value - self.statistics.total_invested
                    self.statistics.unrealized_pnl_percent = (
                        (self.statistics.unrealized_pnl / self.statistics.total_invested) * 100
                        if self.statistics.total_invested > 0 else 0
                    )
            except Exception as e:
                self.logger.error(f"Error calculating current value: {e}")
    
    async def _load_order_history(self):
        """Ładuje historię zleceń z bazy danych"""
        try:
            # TODO: Implementuj ładowanie z bazy danych
            pass
        except Exception as e:
            self.logger.error(f"Error loading order history: {e}")
    
    async def _save_order_to_db(self, order: DCAOrder):
        """Zapisuje zlecenie do bazy danych"""
        try:
            # TODO: Implementuj zapis do bazy danych
            pass
        except Exception as e:
            self.logger.error(f"Error saving order to database: {e}")
    
    def get_status(self) -> Dict[str, Any]:
        """Zwraca status strategii"""
        return {
            'bot_id': self.bot_id,
            'strategy': 'DCA',
            'status': self.status.value,
            'pair': self.parameters['pair'],
            'parameters': self.parameters,
            'statistics': {
                'total_invested': self.statistics.total_invested,
                'total_purchased': self.statistics.total_purchased,
                'average_price': self.statistics.average_price,
                'current_value': self.statistics.current_value,
                'unrealized_pnl': self.statistics.unrealized_pnl,
                'unrealized_pnl_percent': self.statistics.unrealized_pnl_percent,
                'orders_count': self.statistics.orders_count,
                'successful_orders': self.statistics.successful_orders,
                'failed_orders': self.statistics.failed_orders
            },
            'next_order_time': self.next_order_time.isoformat() if self.next_order_time else None,
            'last_order_time': self.last_order_time.isoformat() if self.last_order_time else None
        }
    
    def update_parameters(self, new_parameters: Dict[str, Any]):
        """Aktualizuje parametry strategii"""
        # Waliduj nowe parametry
        old_parameters = self.parameters.copy()
        self.parameters.update(new_parameters)
        
        try:
            self._validate_parameters()
            self.logger.info("Parameters updated successfully")
        except Exception as e:
            # Przywróć stare parametry w przypadku błędu
            self.parameters = old_parameters
            self.logger.error(f"Failed to update parameters: {e}")
            raise
    
    async def get_statistics(self) -> Dict:
        """Pobranie statystyk bota"""
        try:
            current_price = await self.exchange.get_current_price(self.pair) if self.exchange else 0
            
            current_value = self.total_amount * current_price if current_price else 0
            unrealized_pnl = current_value - self.total_invested if self.total_invested > 0 else 0
            unrealized_pnl_percent = (unrealized_pnl / self.total_invested) * 100 if self.total_invested > 0 else 0
            
            return {
                'total_invested': self.total_invested,
                'total_amount': self.total_amount,
                'average_price': self.average_price,
                'current_price': current_price,
                'current_value': current_value,
                'unrealized_pnl': unrealized_pnl,
                'unrealized_pnl_percent': unrealized_pnl_percent,
                'position_count': self.position_count,
                'last_purchase': self.last_purchase_time.isoformat() if self.last_purchase_time else None
            }
            
        except Exception as e:
            self.logger.error(f"Błąd podczas pobierania statystyk: {e}")
            return {}
    
    async def load_state(self):
        """Załadowanie stanu bota z bazy danych"""
        try:
            if not self.bot_id:
                return
            
            # Pobranie historii zleceń
            orders = await self.db_manager.get_bot_orders(self.bot_id)
            
            total_buy_cost = 0.0
            total_buy_amount = 0.0
            total_sell_amount = 0.0
            
            for order in orders:
                if order['side'] == 'buy' and order['status'] == 'filled':
                    cost = order['amount'] * order['price']
                    total_buy_cost += cost
                    total_buy_amount += order['amount']
                    self.position_count += 1
                    
                    # Aktualizacja czasu ostatniego zakupu
                    order_time = datetime.fromisoformat(order['timestamp'])
                    if not self.last_purchase_time or order_time > self.last_purchase_time:
                        self.last_purchase_time = order_time
                        
                elif order['side'] == 'sell' and order['status'] == 'filled':
                    total_sell_amount += order['amount']
            
            # Obliczenie aktualnej pozycji
            self.total_amount = total_buy_amount - total_sell_amount
            self.total_invested = total_buy_cost * (self.total_amount / total_buy_amount) if total_buy_amount > 0 else 0
            self.average_price = total_buy_cost / total_buy_amount if total_buy_amount > 0 else 0
            
            self.logger.info(f"Załadowano stan DCA Bot: pozycja {self.total_amount}, średnia cena {self.average_price}")
            
        except Exception as e:
            self.logger.error(f"Błąd podczas ładowania stanu: {e}")
    
    async def save_state(self):
        """Zapisanie stanu bota"""
        try:
            if not self.bot_id:
                return
            
            # Aktualizacja parametrów w bazie danych
            parameters = {
                'amount': self.amount,
                'interval': self.interval,
                'stop_loss_percent': self.stop_loss_percent,
                'take_profit_percent': self.take_profit_percent,
                'max_position': self.max_position,
                'total_invested': self.total_invested,
                'total_amount': self.total_amount,
                'average_price': self.average_price,
                'position_count': self.position_count
            }
            
            await self.db_manager.update_bot_parameters(self.bot_id, parameters)
            
        except Exception as e:
            self.logger.error(f"Błąd podczas zapisywania stanu: {e}")
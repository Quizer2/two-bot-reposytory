"""
Scalping Strategy Implementation
Strategia scalpingowa wykorzystująca wskaźniki techniczne do krótkoterminowego handlu
"""

import asyncio
import json
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass, asdict
from collections import deque
from enum import Enum

from app.exchange.base_exchange import BaseExchange
from core.database_manager import DatabaseManager
from app.risk_management import RiskManager
from utils.logger import get_logger
from utils.helpers import FormatHelper, CalculationHelper
import logging
logger = logging.getLogger(__name__)


class ScalpingStatus(Enum):
    """Status strategii scalpingowej"""
    STOPPED = "stopped"
    RUNNING = "running"
    PAUSED = "paused"
    ERROR = "error"


@dataclass
class ScalpingIndicators:
    """Wskaźniki techniczne dla scalpingu"""
    rsi: Optional[float] = None
    ema_fast: Optional[float] = None
    ema_slow: Optional[float] = None
    macd: Optional[float] = None
    macd_signal: Optional[float] = None
    macd_histogram: Optional[float] = None
    bb_upper: Optional[float] = None
    bb_middle: Optional[float] = None
    bb_lower: Optional[float] = None
    volume_avg: Optional[float] = None


@dataclass
class ScalpingPosition:
    """Pozycja scalpingowa"""
    order_id: str
    side: str  # 'buy' lub 'sell'
    amount: float
    entry_price: float
    entry_time: datetime
    current_price: Optional[float] = None
    unrealized_pnl: Optional[float] = None
    unrealized_pnl_percentage: Optional[float] = None


@dataclass
class ScalpingTrade:
    """Zakończona transakcja scalpingowa"""
    entry_order_id: str
    exit_order_id: str
    side: str
    amount: float
    entry_price: float
    exit_price: float
    entry_time: datetime
    exit_time: datetime
    pnl: float
    pnl_percentage: float
    duration_seconds: int
    exit_reason: str


@dataclass
class ScalpingStatistics:
    """Statystyki strategii scalpingowej"""
    total_trades: int = 0
    winning_trades: int = 0
    losing_trades: int = 0
    total_pnl: float = 0.0
    total_pnl_percentage: float = 0.0
    win_rate: float = 0.0
    avg_win: float = 0.0
    avg_loss: float = 0.0
    avg_trade_duration: float = 0.0
    max_drawdown: float = 0.0
    sharpe_ratio: float = 0.0
    profit_factor: float = 0.0
    best_trade: float = 0.0
    worst_trade: float = 0.0
    avg_daily_trades: float = 0.0
    total_volume: float = 0.0


class ScalpingStrategy:
    """
    Strategia scalpingowa wykorzystująca wskaźniki techniczne
    """
    
    def __init__(
        self,
        symbol: str,
        timeframe: str = "1m",
        amount: float = 100.0,
        rsi_period: int = 14,
        rsi_oversold: float = 30.0,
        rsi_overbought: float = 70.0,
        ema_fast: int = 12,
        ema_slow: int = 26,
        macd_signal: int = 9,
        bb_period: int = 20,
        bb_std: float = 2.0,
        min_profit_percentage: float = 0.5,
        max_position_time: int = 300,  # 5 minut
        stop_loss_percentage: Optional[float] = None,
        take_profit_percentage: Optional[float] = None,
        max_daily_trades: Optional[int] = None,
        start_time: Optional[str] = None,
        end_time: Optional[str] = None,
        bot_id: Optional[int] = None
    ):
        # Podstawowe parametry
        self.symbol = symbol
        self.timeframe = timeframe
        self.amount = amount
        
        # Parametry wskaźników
        self.rsi_period = rsi_period
        self.rsi_oversold = rsi_oversold
        self.rsi_overbought = rsi_overbought
        self.ema_fast = ema_fast
        self.ema_slow = ema_slow
        self.macd_signal = macd_signal
        self.bb_period = bb_period
        self.bb_std = bb_std
        
        # Parametry zarządzania pozycją
        self.min_profit_percentage = min_profit_percentage
        self.max_position_time = max_position_time
        self.stop_loss_percentage = stop_loss_percentage
        self.take_profit_percentage = take_profit_percentage
        self.max_daily_trades = max_daily_trades
        
        # Ograniczenia czasowe
        self.start_time = start_time
        self.end_time = end_time
        
        # Stan strategii
        self.status = ScalpingStatus.STOPPED
        self.is_running = False
        self.is_paused = False

        # Kontekst identyfikatora bota
        self.bot_id: Optional[int] = bot_id

        # Komponenty
        self.exchange: Optional[BaseExchange] = None
        self.db_manager: Optional[DatabaseManager] = None
        self.risk_manager: Optional[RiskManager] = None
        
        # Dane rynkowe
        self.price_history = deque(maxlen=200)
        self.volume_history = deque(maxlen=200)
        self.indicators = ScalpingIndicators()
        
        # Pozycje i transakcje
        self.current_position: Optional[ScalpingPosition] = None
        self.trade_history: List[ScalpingTrade] = []
        self.statistics = ScalpingStatistics()
        self._position_record_id: Optional[str] = None
        
        # Liczniki
        self.daily_trades = 0
        self.last_trade_date = None
        
        # Walidacja parametrów
        self._validate_parameters()
    
    def _validate_parameters(self):
        """Walidacja parametrów strategii"""
        if self.amount <= 0:
            raise ValueError("Kwota musi być większa od 0")
        
        if self.rsi_period < 2:
            raise ValueError("Okres RSI musi być >= 2")
        
        if not (0 < self.rsi_oversold < 50):
            raise ValueError("RSI oversold musi być między 0 a 50")
        
        if not (50 < self.rsi_overbought < 100):
            raise ValueError("RSI overbought musi być między 50 a 100")
        
        if self.ema_fast >= self.ema_slow:
            raise ValueError("EMA fast musi być mniejsza od EMA slow")
        
        if self.min_profit_percentage <= 0:
            raise ValueError("Minimalny procent zysku musi być > 0")
        
        if self.max_position_time <= 0:
            raise ValueError("Maksymalny czas pozycji musi być > 0")
    
    async def initialize(
        self,
        db_manager: DatabaseManager,
        risk_manager: RiskManager,
        exchange: BaseExchange,
        data_manager=None,
        bot_id: Optional[int] = None
    ):
        """Inicjalizacja strategii"""
        try:
            self.db_manager = db_manager
            self.risk_manager = risk_manager
            self.exchange = exchange
            self.data_manager = data_manager
            if bot_id is not None:
                self.bot_id = bot_id

            # Wczytanie historii transakcji
            await self._load_trade_history()
            
            # Obliczenie statystyk
            await self._calculate_statistics()
            
            logger.info(f"Strategia Scalping zainicjalizowana dla {self.symbol}")
            
        except Exception as e:
            logger.error(f"Błąd inicjalizacji strategii Scalping: {e}")
            raise
    
    async def start(self):
        """Uruchomienie strategii"""
        try:
            if self.status == ScalpingStatus.RUNNING:
                logger.warning("Strategia Scalping już działa")
                return
            
            self.status = ScalpingStatus.RUNNING
            self.is_running = True
            self.is_paused = False
            
            logger.info(f"Uruchamianie strategii Scalping dla {self.symbol}")
            
            # Główna pętla strategii
            while self.is_running:
                try:
                    if not self.is_paused:
                        await self._trading_loop()
                    
                    await asyncio.sleep(1)  # Sprawdzanie co sekundę
                    
                except Exception as e:
                    logger.error(f"Błąd w pętli handlowej: {e}")
                    await asyncio.sleep(5)
            
            self.status = ScalpingStatus.STOPPED
            
        except Exception as e:
            self.status = ScalpingStatus.ERROR
            logger.error(f"Błąd strategii Scalping: {e}")
            raise
    
    async def stop(self):
        """Zatrzymanie strategii"""
        try:
            logger.info("Zatrzymywanie strategii Scalping")
            
            self.is_running = False
            self.is_paused = False
            
            # Zamknięcie otwartej pozycji
            if self.current_position:
                await self._close_position("Strategy stopped")
            
            self.status = ScalpingStatus.STOPPED
            logger.info("Strategia Scalping zatrzymana")
            
        except Exception as e:
            logger.error(f"Błąd zatrzymywania strategii: {e}")
    
    async def pause(self):
        """Wstrzymanie strategii"""
        if self.status == ScalpingStatus.RUNNING:
            self.is_paused = True
            logger.info("Strategia Scalping wstrzymana")
    
    async def resume(self):
        """Wznowienie strategii"""
        if self.status == ScalpingStatus.RUNNING and self.is_paused:
            self.is_paused = False
            logger.info("Strategia Scalping wznowiona")
    
    async def _trading_loop(self):
        """Główna pętla handlowa"""
        try:
            # Sprawdzenie ograniczeń czasowych
            if not self._is_trading_time():
                return
            
            # Sprawdzenie limitu dziennych transakcji
            if not self._can_trade_today():
                return
            
            # Aktualizacja danych rynkowych
            await self._update_market_data()
            
            # Obliczenie wskaźników
            await self._calculate_indicators()
            
            # Sprawdzenie aktualnej pozycji
            if self.current_position:
                await self._manage_position()
            else:
                # Szukanie sygnałów wejścia
                await self._check_entry_signals()
            
        except Exception as e:
            logger.error(f"Błąd w pętli handlowej: {e}")
    
    async def _update_market_data(self):
        """Aktualizacja danych rynkowych"""
        try:
            # Pobranie aktualnej ceny
            ticker = await self.exchange.get_ticker(self.symbol)
            current_price = float(ticker['last'])
            
            # Dodanie do historii
            self.price_history.append(current_price)
            
            # Pobranie wolumenu (jeśli dostępny)
            if 'volume' in ticker:
                self.volume_history.append(float(ticker['volume']))
            
        except Exception as e:
            logger.error(f"Błąd aktualizacji danych rynkowych: {e}")
    
    async def _calculate_indicators(self):
        """Obliczenie wskaźników technicznych"""
        try:
            if len(self.price_history) < max(self.rsi_period, self.ema_slow, self.bb_period):
                return
            
            prices = list(self.price_history)
            
            # RSI
            self.indicators.rsi = self._calculate_rsi(prices, self.rsi_period)
            
            # EMA
            self.indicators.ema_fast = self._calculate_ema(prices, self.ema_fast)
            self.indicators.ema_slow = self._calculate_ema(prices, self.ema_slow)
            
            # MACD
            macd_data = self._calculate_macd(prices, self.ema_fast, self.ema_slow, self.macd_signal)
            self.indicators.macd = macd_data['macd']
            self.indicators.macd_signal = macd_data['signal']
            self.indicators.macd_histogram = macd_data['histogram']
            
            # Bollinger Bands
            bb_data = self._calculate_bollinger_bands(prices, self.bb_period, self.bb_std)
            self.indicators.bb_upper = bb_data['upper']
            self.indicators.bb_middle = bb_data['middle']
            self.indicators.bb_lower = bb_data['lower']
            
            # Średni wolumen
            if self.volume_history:
                self.indicators.volume_avg = sum(self.volume_history) / len(self.volume_history)
            
        except Exception as e:
            logger.error(f"Błąd obliczania wskaźników: {e}")
    
    def _calculate_rsi(self, prices: List[float], period: int) -> Optional[float]:
        """Obliczenie RSI"""
        try:
            if len(prices) < period + 1:
                return None
            
            deltas = [prices[i] - prices[i-1] for i in range(1, len(prices))]
            gains = [d if d > 0 else 0 for d in deltas]
            losses = [-d if d < 0 else 0 for d in deltas]
            
            avg_gain = sum(gains[-period:]) / period
            avg_loss = sum(losses[-period:]) / period
            
            if avg_loss == 0:
                return 100
            
            rs = avg_gain / avg_loss
            rsi = 100 - (100 / (1 + rs))
            
            return rsi
            
        except Exception:
            return None
    
    def _calculate_ema(self, prices: List[float], period: int) -> Optional[float]:
        """Obliczenie EMA"""
        try:
            if len(prices) < period:
                return None
            
            multiplier = 2 / (period + 1)
            ema = sum(prices[:period]) / period
            
            for price in prices[period:]:
                ema = (price * multiplier) + (ema * (1 - multiplier))
            
            return ema
            
        except Exception:
            return None
    
    def _calculate_macd(self, prices: List[float], fast: int, slow: int, signal: int) -> Dict:
        """Obliczenie MACD"""
        try:
            ema_fast = self._calculate_ema(prices, fast)
            ema_slow = self._calculate_ema(prices, slow)
            
            if ema_fast is None or ema_slow is None:
                return {'macd': None, 'signal': None, 'histogram': None}
            
            macd = ema_fast - ema_slow
            
            # Obliczenie sygnału (EMA z MACD)
            macd_history = [macd]  # W rzeczywistości potrzebujemy historii MACD
            signal_line = self._calculate_ema(macd_history, signal)
            
            histogram = macd - signal_line if signal_line else None
            
            return {
                'macd': macd,
                'signal': signal_line,
                'histogram': histogram
            }
            
        except Exception:
            return {'macd': None, 'signal': None, 'histogram': None}
    
    def _calculate_bollinger_bands(self, prices: List[float], period: int, std_dev: float) -> Dict:
        """Obliczenie Bollinger Bands"""
        try:
            if len(prices) < period:
                return {'upper': None, 'middle': None, 'lower': None}
            
            recent_prices = prices[-period:]
            middle = sum(recent_prices) / period
            
            variance = sum((p - middle) ** 2 for p in recent_prices) / period
            std = variance ** 0.5
            
            upper = middle + (std * std_dev)
            lower = middle - (std * std_dev)
            
            return {
                'upper': upper,
                'middle': middle,
                'lower': lower
            }
            
        except Exception:
            return {'upper': None, 'middle': None, 'lower': None}
    
    async def _check_entry_signals(self):
        """Sprawdzenie sygnałów wejścia"""
        try:
            if not self._all_indicators_available():
                return
            
            current_price = self.price_history[-1]
            
            # Sygnał kupna
            buy_signal = (
                self.indicators.rsi < self.rsi_oversold and
                self.indicators.ema_fast > self.indicators.ema_slow and
                current_price <= self.indicators.bb_lower and
                self.indicators.macd_histogram > 0
            )
            
            # Sygnał sprzedaży (short)
            sell_signal = (
                self.indicators.rsi > self.rsi_overbought and
                self.indicators.ema_fast < self.indicators.ema_slow and
                current_price >= self.indicators.bb_upper and
                self.indicators.macd_histogram < 0
            )
            
            if buy_signal:
                await self._enter_position('buy', current_price)
            elif sell_signal:
                await self._enter_position('sell', current_price)
            
        except Exception as e:
            logger.error(f"Błąd sprawdzania sygnałów wejścia: {e}")
    
    async def _enter_position(self, side: str, price: float):
        """Wejście w pozycję"""
        try:
            # Oblicz ilość kryptowaluty z kwoty USD
            from utils.helpers import TradingHelpers
            crypto_amount = TradingHelpers.calculate_crypto_amount_from_usd(self.amount, price)
            
            # Sprawdzenie zarządzania ryzykiem
            if not await self.risk_manager.can_open_position(
                self.symbol, side, crypto_amount, price
            ):
                logger.warning("Zarządzanie ryzykiem odrzuciło pozycję")
                return
            
            # Trace log przed składaniem zlecenia
            logger.info(f"TRACE: order.submitted - symbol={self.symbol}, side={side}, amount={crypto_amount}, type=market, strategy=scalping")
            
            # Złożenie zlecenia
            order = await self.exchange.create_market_order(
                symbol=self.symbol,
                side=side,
                amount=crypto_amount
            )
            
            if order and order.get('status') == 'filled':
                # Utworzenie pozycji
                self.current_position = ScalpingPosition(
                    order_id=order['id'],
                    side=side,
                    amount=float(order['filled']),
                    entry_price=float(order['average']),
                    entry_time=datetime.now()
                )
                
                logger.info(
                    f"Otwarto pozycję {side}: {self.current_position.amount} "
                    f"po cenie {self.current_position.entry_price}"
                )
                
                # Zapisanie do bazy danych
                await self._save_position_to_db()
            
        except Exception as e:
            logger.error(f"Błąd wejścia w pozycję: {e}")
    
    async def _manage_position(self):
        """Zarządzanie otwartą pozycją"""
        try:
            if not self.current_position:
                return
            
            current_price = self.price_history[-1]
            position_duration = (datetime.now() - self.current_position.entry_time).total_seconds()
            
            # Aktualizacja PnL
            if self.current_position.side == 'buy':
                pnl_percentage = ((current_price - self.current_position.entry_price) / 
                                self.current_position.entry_price) * 100
            else:
                pnl_percentage = ((self.current_position.entry_price - current_price) / 
                                self.current_position.entry_price) * 100
            
            self.current_position.current_price = current_price
            self.current_position.unrealized_pnl_percentage = pnl_percentage
            
            # Sprawdzenie warunków wyjścia
            should_exit, reason = await self._check_exit_conditions(pnl_percentage, position_duration)
            
            if should_exit:
                await self._close_position(reason)
            
        except Exception as e:
            logger.error(f"Błąd zarządzania pozycją: {e}")
    
    async def _check_exit_conditions(self, pnl_percentage: float, duration: float) -> Tuple[bool, str]:
        """Sprawdzenie warunków wyjścia z pozycji"""
        try:
            # Take profit
            if (self.take_profit_percentage and 
                pnl_percentage >= self.take_profit_percentage):
                return True, "Take profit"
            
            # Stop loss
            if (self.stop_loss_percentage and 
                pnl_percentage <= -self.stop_loss_percentage):
                return True, "Stop loss"
            
            # Maksymalny czas pozycji
            if duration >= self.max_position_time:
                return True, "Max time"
            
            # Minimalny zysk po określonym czasie
            if (duration >= self.max_position_time * 0.8 and 
                pnl_percentage >= self.min_profit_percentage):
                return True, "Min profit reached"
            
            # Sygnały techniczne wyjścia
            if await self._check_technical_exit():
                return True, "Technical signal"
            
            return False, ""
            
        except Exception as e:
            logger.error(f"Błąd sprawdzania warunków wyjścia: {e}")
            return False, ""
    
    async def _check_technical_exit(self) -> bool:
        """Sprawdzenie technicznych sygnałów wyjścia"""
        try:
            if not self._all_indicators_available() or not self.current_position:
                return False
            
            current_price = self.price_history[-1]
            
            if self.current_position.side == 'buy':
                # Wyjście z pozycji długiej
                return (
                    self.indicators.rsi > self.rsi_overbought or
                    self.indicators.ema_fast < self.indicators.ema_slow or
                    current_price >= self.indicators.bb_upper or
                    self.indicators.macd_histogram < 0
                )
            else:
                # Wyjście z pozycji krótkiej
                return (
                    self.indicators.rsi < self.rsi_oversold or
                    self.indicators.ema_fast > self.indicators.ema_slow or
                    current_price <= self.indicators.bb_lower or
                    self.indicators.macd_histogram > 0
                )
            
        except Exception:
            return False
    
    async def _close_position(self, reason: str):
        """Zamknięcie pozycji"""
        try:
            if not self.current_position:
                return
            
            # Określenie strony zlecenia zamykającego
            close_side = 'sell' if self.current_position.side == 'buy' else 'buy'
            
            # Trace log przed składaniem zlecenia
            logger.info(f"TRACE: order.submitted - symbol={self.symbol}, side={close_side}, amount={self.current_position.amount}, type=market, strategy=scalping")
            
            # Złożenie zlecenia zamykającego
            order = await self.exchange.create_market_order(
                symbol=self.symbol,
                side=close_side,
                amount=self.current_position.amount
            )
            
            if order and order.get('status') == 'filled':
                exit_price = float(order['average'])
                exit_time = datetime.now()
                
                # Obliczenie PnL
                if self.current_position.side == 'buy':
                    pnl = (exit_price - self.current_position.entry_price) * self.current_position.amount
                    pnl_percentage = ((exit_price - self.current_position.entry_price) / 
                                    self.current_position.entry_price) * 100
                else:
                    pnl = (self.current_position.entry_price - exit_price) * self.current_position.amount
                    pnl_percentage = ((self.current_position.entry_price - exit_price) / 
                                    self.current_position.entry_price) * 100
                
                duration = int((exit_time - self.current_position.entry_time).total_seconds())
                
                # Utworzenie rekordu transakcji
                trade = ScalpingTrade(
                    entry_order_id=self.current_position.order_id,
                    exit_order_id=order['id'],
                    side=self.current_position.side,
                    amount=self.current_position.amount,
                    entry_price=self.current_position.entry_price,
                    exit_price=exit_price,
                    entry_time=self.current_position.entry_time,
                    exit_time=exit_time,
                    pnl=pnl,
                    pnl_percentage=pnl_percentage,
                    duration_seconds=duration,
                    exit_reason=reason
                )
                
                # Dodanie do historii
                self.trade_history.append(trade)
                
                # Aktualizacja liczników
                self._update_daily_counter()
                
                # Zapisanie do bazy danych
                await self._save_trade_to_db(trade)

                if self.db_manager:
                    bot_db_id = self._resolve_bot_id()
                    if bot_db_id is not None and self._position_record_id:
                        position_payload = {
                            'strategy': 'scalping',
                            'kind': 'position',
                            'order_id': trade.entry_order_id,
                            'side': trade.side,
                            'amount': trade.amount,
                            'entry_price': trade.entry_price,
                            'entry_time': trade.entry_time.isoformat(),
                            'exit_price': trade.exit_price,
                            'exit_time': trade.exit_time.isoformat(),
                            'pnl': trade.pnl,
                            'pnl_percentage': trade.pnl_percentage,
                        }
                        await self.db_manager.upsert_strategy_order(
                            bot_db_id,
                            self._position_record_id,
                            position_payload,
                            'closed'
                        )
                        self._position_record_id = None

                # Aktualizacja statystyk
                await self._calculate_statistics()
                
                logger.info(
                    f"Zamknięto pozycję: {reason}, PnL: {pnl_percentage:.2f}%, "
                    f"Czas: {duration}s"
                )
                
                # Wyczyszczenie pozycji
                self.current_position = None
            
        except Exception as e:
            logger.error(f"Błąd zamykania pozycji: {e}")
    
    def _all_indicators_available(self) -> bool:
        """Sprawdzenie czy wszystkie wskaźniki są dostępne"""
        return all([
            self.indicators.rsi is not None,
            self.indicators.ema_fast is not None,
            self.indicators.ema_slow is not None,
            self.indicators.macd is not None,
            self.indicators.bb_upper is not None
        ])
    
    def _is_trading_time(self) -> bool:
        """Sprawdzenie czy jest czas handlu"""
        if not self.start_time or not self.end_time:
            return True
        
        now = datetime.now().time()
        start = datetime.strptime(self.start_time, "%H:%M").time()
        end = datetime.strptime(self.end_time, "%H:%M").time()
        
        if start <= end:
            return start <= now <= end
        else:
            return now >= start or now <= end
    
    def _can_trade_today(self) -> bool:
        """Sprawdzenie czy można handlować dzisiaj"""
        if not self.max_daily_trades:
            return True
        
        today = datetime.now().date()
        
        # Reset licznika jeśli nowy dzień
        if self.last_trade_date != today:
            self.daily_trades = 0
            self.last_trade_date = today
        
        return self.daily_trades < self.max_daily_trades
    
    def _update_daily_counter(self):
        """Aktualizacja licznika dziennych transakcji"""
        today = datetime.now().date()
        
        if self.last_trade_date != today:
            self.daily_trades = 1
            self.last_trade_date = today
        else:
            self.daily_trades += 1
    
    async def _calculate_statistics(self):
        """Obliczenie statystyk"""
        try:
            if not self.trade_history:
                return
            
            trades = self.trade_history
            
            # Podstawowe statystyki
            self.statistics.total_trades = len(trades)
            self.statistics.winning_trades = len([t for t in trades if t.pnl > 0])
            self.statistics.losing_trades = len([t for t in trades if t.pnl < 0])
            
            # PnL
            self.statistics.total_pnl = sum(t.pnl for t in trades)
            self.statistics.total_pnl_percentage = sum(t.pnl_percentage for t in trades)
            
            # Win rate
            if self.statistics.total_trades > 0:
                self.statistics.win_rate = (self.statistics.winning_trades / 
                                          self.statistics.total_trades) * 100
            
            # Średnie zyski/straty
            winning_trades = [t.pnl for t in trades if t.pnl > 0]
            losing_trades = [t.pnl for t in trades if t.pnl < 0]
            
            if winning_trades:
                self.statistics.avg_win = sum(winning_trades) / len(winning_trades)
            
            if losing_trades:
                self.statistics.avg_loss = sum(losing_trades) / len(losing_trades)
            
            # Średni czas transakcji
            if trades:
                self.statistics.avg_trade_duration = sum(t.duration_seconds for t in trades) / len(trades)
            
            # Najlepsza/najgorsza transakcja
            if trades:
                self.statistics.best_trade = max(t.pnl for t in trades)
                self.statistics.worst_trade = min(t.pnl for t in trades)
            
            # Profit factor
            total_wins = sum(winning_trades) if winning_trades else 0
            total_losses = abs(sum(losing_trades)) if losing_trades else 0
            
            if total_losses > 0:
                self.statistics.profit_factor = total_wins / total_losses
            
            # Wolumen
            self.statistics.total_volume = sum(t.amount * t.entry_price for t in trades)
            
            # Średnia dzienna liczba transakcji
            if trades:
                days = (trades[-1].exit_time - trades[0].entry_time).days + 1
                self.statistics.avg_daily_trades = len(trades) / max(days, 1)
            
        except Exception as e:
            logger.error(f"Błąd obliczania statystyk: {e}")
    
    async def _load_trade_history(self):
        """Wczytanie historii transakcji z bazy danych"""
        try:
            if not self.db_manager:
                return

            bot_db_id = self._resolve_bot_id()
            if bot_db_id is None:
                return

            records = await self.db_manager.list_strategy_orders(bot_db_id, limit=500)
            history: List[ScalpingTrade] = []

            for record in records:
                payload = record.get('payload') if isinstance(record, dict) else {}
                if not payload:
                    continue

                if payload.get('strategy') not in {'scalping', 'scalping_trade'}:
                    continue
                if payload.get('kind') not in {'trade', 'scalping_trade'}:
                    continue

                try:
                    entry_time = datetime.fromisoformat(payload.get('entry_time')) if payload.get('entry_time') else datetime.utcnow()
                except Exception:
                    entry_time = datetime.utcnow()

                try:
                    exit_time = datetime.fromisoformat(payload.get('exit_time')) if payload.get('exit_time') else entry_time
                except Exception:
                    exit_time = entry_time

                trade = ScalpingTrade(
                    entry_order_id=str(payload.get('entry_order_id') or payload.get('order_id') or record.get('order_id') or ''),
                    exit_order_id=str(payload.get('exit_order_id') or payload.get('order_id') or ''),
                    side=str(payload.get('side') or payload.get('direction') or 'buy'),
                    amount=float(payload.get('amount') or 0.0),
                    entry_price=float(payload.get('entry_price') or payload.get('price') or 0.0),
                    exit_price=float(payload.get('exit_price') or payload.get('price') or 0.0),
                    entry_time=entry_time,
                    exit_time=exit_time,
                    pnl=float(payload.get('pnl') or 0.0),
                    pnl_percentage=float(payload.get('pnl_percentage') or 0.0),
                    duration_seconds=int(payload.get('duration_seconds') or 0),
                    exit_reason=str(payload.get('exit_reason') or 'unknown'),
                )
                history.append(trade)

            if history:
                self.trade_history = sorted(history, key=lambda t: t.exit_time)

        except Exception as e:
            logger.error(f"Błąd wczytywania historii transakcji: {e}")

    async def _save_position_to_db(self):
        """Zapisanie pozycji do bazy danych"""
        try:
            if not self.db_manager or not self.current_position:
                return

            bot_db_id = self._resolve_bot_id()
            if bot_db_id is None:
                return

            payload = {
                'strategy': 'scalping',
                'kind': 'position',
                'order_id': self.current_position.order_id,
                'side': self.current_position.side,
                'amount': self.current_position.amount,
                'entry_price': self.current_position.entry_price,
                'entry_time': self.current_position.entry_time.isoformat(),
                'current_price': self.current_position.current_price,
                'unrealized_pnl': self.current_position.unrealized_pnl,
                'unrealized_pnl_percentage': self.current_position.unrealized_pnl_percentage,
            }

            record_id = f"position_{self.current_position.order_id}"
            await self.db_manager.upsert_strategy_order(bot_db_id, record_id, payload, 'open')
            self._position_record_id = record_id

        except Exception as e:
            logger.error(f"Błąd zapisywania pozycji: {e}")

    async def _save_trade_to_db(self, trade: ScalpingTrade):
        """Zapisanie transakcji do bazy danych"""
        try:
            if not self.db_manager:
                return

            bot_db_id = self._resolve_bot_id()
            if bot_db_id is None:
                return

            payload = {
                'strategy': 'scalping',
                'kind': 'trade',
                'entry_order_id': trade.entry_order_id,
                'exit_order_id': trade.exit_order_id,
                'side': trade.side,
                'amount': trade.amount,
                'entry_price': trade.entry_price,
                'exit_price': trade.exit_price,
                'entry_time': trade.entry_time.isoformat(),
                'exit_time': trade.exit_time.isoformat(),
                'pnl': trade.pnl,
                'pnl_percentage': trade.pnl_percentage,
                'duration_seconds': trade.duration_seconds,
                'exit_reason': trade.exit_reason,
            }

            record_id = f"trade_{trade.exit_order_id or trade.entry_order_id}"
            await self.db_manager.upsert_strategy_order(bot_db_id, record_id, payload, 'closed')

        except Exception as e:
            logger.error(f"Błąd zapisywania transakcji: {e}")

    def _resolve_bot_id(self) -> Optional[int]:
        if self.bot_id is None:
            return None

        try:
            return int(self.bot_id)
        except (TypeError, ValueError):
            if isinstance(self.bot_id, str) and self.bot_id.startswith('bot_'):
                candidate = self.bot_id.split('_', 1)[1]
                try:
                    return int(candidate)
                except (TypeError, ValueError):
                    pass

        logger.warning("Nie można zinterpretować bot_id='%s' dla strategii Scalping", self.bot_id)
        return None
    
    def get_status(self) -> Dict:
        """Pobranie statusu strategii"""
        return {
            'status': self.status.value,
            'is_running': self.is_running,
            'is_paused': self.is_paused,
            'symbol': self.symbol,
            'timeframe': self.timeframe,
            'current_position': asdict(self.current_position) if self.current_position else None,
            'indicators': asdict(self.indicators),
            'statistics': asdict(self.statistics),
            'daily_trades': self.daily_trades,
            'max_daily_trades': self.max_daily_trades
        }
    
    def get_statistics(self) -> ScalpingStatistics:
        """Pobranie statystyk strategii"""
        return self.statistics
    
    async def update_parameters(self, parameters: Dict):
        """Aktualizacja parametrów strategii"""
        try:
            # Walidacja nowych parametrów
            old_params = {
                'amount': self.amount,
                'rsi_period': self.rsi_period,
                'rsi_oversold': self.rsi_oversold,
                'rsi_overbought': self.rsi_overbought,
                'ema_fast': self.ema_fast,
                'ema_slow': self.ema_slow,
                'min_profit_percentage': self.min_profit_percentage,
                'max_position_time': self.max_position_time
            }
            
            # Aktualizacja parametrów
            for key, value in parameters.items():
                if hasattr(self, key):
                    setattr(self, key, value)
            
            # Walidacja
            try:
                self._validate_parameters()
                logger.info("Parametry strategii Scalping zaktualizowane")
            except ValueError as e:
                # Przywrócenie starych parametrów
                for key, value in old_params.items():
                    setattr(self, key, value)
                raise e
            
        except Exception as e:
            logger.error(f"Błąd aktualizacji parametrów: {e}")
            raise
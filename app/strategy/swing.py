"""
Swing Trading Strategy Implementation
Strategia swing trading wykorzystująca analizę techniczną do średnioterminowego handlu
"""

import asyncio
import json
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple, Union
from dataclasses import dataclass, asdict
from collections import deque
from enum import Enum

from app.exchange.base_exchange import BaseExchange
from core.database_manager import DatabaseManager
from app.risk_management import RiskManager
from utils.logger import get_logger
from utils.helpers import FormatHelper, CalculationHelper


class SwingStatus(Enum):
    """Status strategii swing trading"""
    STOPPED = "stopped"
    RUNNING = "running"
    PAUSED = "paused"
    ERROR = "error"


class SwingTrend(Enum):
    """Kierunek trendu"""
    UPTREND = "uptrend"
    DOWNTREND = "downtrend"
    SIDEWAYS = "sideways"
    UNKNOWN = "unknown"


@dataclass
class SwingIndicators:
    """Wskaźniki techniczne dla swing trading"""
    sma_20: Optional[float] = None
    sma_50: Optional[float] = None
    sma_200: Optional[float] = None
    ema_12: Optional[float] = None
    ema_26: Optional[float] = None
    rsi: Optional[float] = None
    macd: Optional[float] = None
    macd_signal: Optional[float] = None
    macd_histogram: Optional[float] = None
    bb_upper: Optional[float] = None
    bb_middle: Optional[float] = None
    bb_lower: Optional[float] = None
    stoch_k: Optional[float] = None
    stoch_d: Optional[float] = None
    atr: Optional[float] = None
    volume_sma: Optional[float] = None


@dataclass
class SwingPosition:
    """Pozycja swing trading"""
    order_id: str
    side: str  # 'buy' lub 'sell'
    amount: float
    entry_price: float
    entry_time: datetime
    stop_loss: Optional[float] = None
    take_profit: Optional[float] = None
    current_price: Optional[float] = None
    unrealized_pnl: Optional[float] = None
    unrealized_pnl_percentage: Optional[float] = None
    trend_at_entry: Optional[SwingTrend] = None


@dataclass
class SwingTrade:
    """Zakończona transakcja swing"""
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
    duration_hours: float
    exit_reason: str
    trend_at_entry: SwingTrend
    trend_at_exit: SwingTrend


@dataclass
class SwingStatistics:
    """Statystyki strategii swing trading"""
    total_trades: int = 0
    winning_trades: int = 0
    losing_trades: int = 0
    total_pnl: float = 0.0
    total_pnl_percentage: float = 0.0
    win_rate: float = 0.0
    avg_win: float = 0.0
    avg_loss: float = 0.0
    avg_trade_duration_hours: float = 0.0
    max_drawdown: float = 0.0
    sharpe_ratio: float = 0.0
    profit_factor: float = 0.0
    best_trade: float = 0.0
    worst_trade: float = 0.0
    avg_weekly_trades: float = 0.0
    total_volume: float = 0.0
    trend_accuracy: float = 0.0


class SwingStrategy:
    """
    Strategia swing trading wykorzystująca analizę techniczną
    do średnioterminowego handlu (1-7 dni)
    """
    
    def __init__(
        self,
        symbol: str,
        timeframe: str = "4h",
        amount: float = 500.0,
        sma_short: int = 20,
        sma_medium: int = 50,
        sma_long: int = 200,
        rsi_period: int = 14,
        rsi_oversold: float = 30.0,
        rsi_overbought: float = 70.0,
        macd_fast: int = 12,
        macd_slow: int = 26,
        macd_signal: int = 9,
        bb_period: int = 20,
        bb_std: float = 2.0,
        stoch_k: int = 14,
        stoch_d: int = 3,
        atr_period: int = 14,
        min_trend_strength: float = 0.6,
        stop_loss_atr_multiplier: float = 2.0,
        take_profit_ratio: float = 2.0,  # Risk:Reward ratio
        stop_loss_percentage: float = 1.0,
        max_position_time_hours: int = 168,  # 7 dni
        volume_confirmation: bool = True,
        trend_confirmation_periods: int = 3,
        max_weekly_trades: Optional[int] = 5,
        max_daily_trades: Optional[int] = 5,
        start_time: Optional[str] = None,
        end_time: Optional[str] = None
    ):
        # Podstawowe parametry
        self.symbol = symbol
        self.timeframe = timeframe
        self.amount = amount
        
        # Parametry średnich kroczących
        self.sma_short = sma_short
        self.sma_medium = sma_medium
        self.sma_long = sma_long
        
        # Parametry wskaźników
        self.rsi_period = rsi_period
        self.rsi_oversold = rsi_oversold
        self.rsi_overbought = rsi_overbought
        self.macd_fast = macd_fast
        self.macd_slow = macd_slow
        self.macd_signal = macd_signal
        self.bb_period = bb_period
        self.bb_std = bb_std
        self.stoch_k = stoch_k
        self.stoch_d = stoch_d
        self.atr_period = atr_period
        
        # Parametry zarządzania pozycją
        self.min_trend_strength = min_trend_strength
        self.stop_loss_atr_multiplier = stop_loss_atr_multiplier
        self.take_profit_ratio = take_profit_ratio
        self.stop_loss_percentage = stop_loss_percentage
        self.max_position_time_hours = max_position_time_hours
        self.volume_confirmation = volume_confirmation
        self.trend_confirmation_periods = trend_confirmation_periods
        self.max_weekly_trades = max_weekly_trades
        self.max_daily_trades = max_daily_trades
        
        # Ograniczenia czasowe
        self.start_time = start_time
        self.end_time = end_time
        
        # Stan strategii
        self.status = SwingStatus.STOPPED
        self.is_running = False
        self.is_paused = False
        
        # Komponenty
        self.exchange: Optional[BaseExchange] = None
        self.db_manager: Optional[DatabaseManager] = None
        self.risk_manager: Optional[RiskManager] = None
        
        # Dane strategii
        self.current_position: Optional[SwingPosition] = None
        self.trade_history: List[SwingTrade] = []
        self.statistics = SwingStatistics()
        self.price_history: deque = deque(maxlen=200)  # Ostatnie 200 świec
        self.indicators_history: deque = deque(maxlen=50)
        
        # Logger
        self.logger = get_logger(f"SwingStrategy_{symbol}")
        
        # Inicjalizacja
        self._initialize_strategy()
    
    async def initialize(self, db_manager: 'DatabaseManager', risk_manager: 'RiskManager', 
                        exchange: 'BaseExchange', data_manager=None):
        """Inicjalizuje strategię z komponentami"""
        self.db_manager = db_manager
        self.risk_manager = risk_manager
        self.exchange = exchange
        self.data_manager = data_manager
        
        self.logger.info(f"Swing Strategy zainicjalizowana dla {self.symbol}")
        return True

    def _initialize_strategy(self):
        """Inicjalizacja strategii"""
        self.logger.info(f"Inicjalizacja Swing Strategy dla {self.symbol}")
        self.logger.info(f"Timeframe: {self.timeframe}, Amount: {self.amount}")
        self.logger.info(f"SMA: {self.sma_short}/{self.sma_medium}/{self.sma_long}")
        self.logger.info(f"RSI: {self.rsi_period} ({self.rsi_oversold}-{self.rsi_overbought})")
        self.logger.info(f"Stop Loss: {self.stop_loss_atr_multiplier}x ATR")
        self.logger.info(f"Take Profit Ratio: 1:{self.take_profit_ratio}")
    
    async def start(self):
        """Uruchomienie strategii (nieblokujące, pojedynczy cykl w testach)"""
        try:
            if self.status == SwingStatus.RUNNING:
                self.logger.warning("Strategia już działa")
                return True
            self.status = SwingStatus.RUNNING
            self.is_running = True
            self.is_paused = False
            self.logger.info("Swing Strategy uruchomiona")
            # Wykonaj pojedynczy cykl, aby testy nie blokowały się
            await self._execute_strategy_cycle()
            return True
        except Exception as e:
            self.logger.error(f"Błąd w strategii swing: {e}")
            self.status = SwingStatus.ERROR
            return False
        finally:
            # Nie kończ od razu biegu; pozostaw is_running=True aż do stop()
            pass

    async def stop(self):
        """Zatrzymanie strategii"""
        self.logger.info("Zatrzymywanie Swing Strategy...")
        self.is_running = False
        self.status = SwingStatus.STOPPED
        # Zamknij otwarte pozycje jeśli to konieczne
        if self.current_position:
            await self._close_position("strategy_stop")
        return True

    async def _get_market_data(self) -> Optional[Dict]:
        """Pobierz dane rynkowe i ustandaryzuj format świec"""
        try:
            if not self.exchange:
                return None
            candles = await self.exchange.get_ohlcv(self.symbol, self.timeframe, limit=200)
            if not candles or len(candles) < 50:
                self.logger.warning("Niewystarczające dane rynkowe")
                return None
            # Ustandaryzuj do listy dictów
            std_candles = []
            for c in candles:
                if isinstance(c, dict):
                    std_candles.append(c)
                elif isinstance(c, (list, tuple)) and len(c) >= 6:
                    std_candles.append({
                        'timestamp': c[0],
                        'open': float(c[1]),
                        'high': float(c[2]),
                        'low': float(c[3]),
                        'close': float(c[4]),
                        'volume': float(c[5])
                    })
            return {
                'candles': std_candles,
                'current_price': std_candles[-1]['close'],
                'volume': std_candles[-1]['volume'],
                'timestamp': datetime.now()
            }
        except Exception as e:
            self.logger.error(f"Błąd pobierania danych rynkowych: {e}")
            return None

    def _calculate_moving_average(self, ohlcv: List[Union[List, Dict]], period: int) -> List[float]:
        """Prosta średnia krocząca z danych OHLCV (lista wartości dla kolejnych świec)"""
        closes: List[float] = []
        for row in ohlcv:
            if isinstance(row, dict) and 'close' in row:
                closes.append(float(row['close']))
            elif isinstance(row, (list, tuple)) and len(row) >= 5:
                closes.append(float(row[4]))
        if len(closes) < period:
            return []
        ma: List[float] = []
        for i in range(period, len(closes)+1):
            window = closes[i-period:i]
            ma.append(sum(window) / period)
        return ma

    def _calculate_bollinger_bands(self, ohlcv: List[Union[List, Dict]], period: int, std_dev: float) -> Tuple[float, float, float]:
        """Oblicz Bollinger Bands (zwraca wartości dla ostatniego okna)"""
        closes: List[float] = []
        for row in ohlcv:
            if isinstance(row, dict) and 'close' in row:
                closes.append(float(row['close']))
            elif isinstance(row, (list, tuple)) and len(row) >= 5:
                closes.append(float(row[4]))
        if len(closes) < period:
            return 0.0, 0.0, 0.0
        window = closes[-period:]
        sma = sum(window) / period
        variance = sum((x - sma) ** 2 for x in window) / period
        std = variance ** 0.5
        bb_middle = sma
        bb_upper = sma + std_dev * std
        bb_lower = sma - std_dev * std
        return bb_upper, bb_middle, bb_lower

    def _can_trade_today(self, daily_trades: int, max_daily: Optional[int] = None) -> bool:
        """Sprawdź czy można handlować dziś zgodnie z limitem dziennym"""
        if max_daily is None:
            max_daily = self.max_daily_trades if hasattr(self, 'max_daily_trades') and self.max_daily_trades is not None else 0
        return daily_trades < max_daily

    def _calculate_stop_loss(self, entry_price: float, side: str) -> float:
        """Oblicz stop loss na podstawie procentowego limitu"""
        pct = self.stop_loss_percentage / 100.0
        if side.lower() == 'buy':
            return entry_price * (1 - pct)
        else:
            return entry_price * (1 + pct)

    def _should_buy(self, market_data: Dict) -> bool:
        """Prosty sygnał kupna na podstawie RSI i średnich"""
        rsi = float(market_data.get('rsi', 50))
        ma_fast = float(market_data.get('ma_fast', 0))
        ma_slow = float(market_data.get('ma_slow', 0))
        price = float(market_data.get('price', 0))
        bb_lower = float(market_data.get('bb_lower', 0))
        trend_strength = float(market_data.get('trend_strength', 0))
        conditions = [
            rsi <= self.rsi_oversold + 5,        # blisko wyprzedania
            ma_fast >= ma_slow,                   # krótsza MA powyżej dłuższej
            price >= bb_lower,                    # cena powyżej dolnego pasma
            trend_strength >= self.min_trend_strength
        ]
        return sum(1 for c in conditions if c) >= 3

    def _should_sell(self, market_data: Dict) -> bool:
        """Prosty sygnał sprzedaży na podstawie RSI i średnich"""
        rsi = float(market_data.get('rsi', 50))
        ma_fast = float(market_data.get('ma_fast', 0))
        ma_slow = float(market_data.get('ma_slow', 0))
        price = float(market_data.get('price', 0))
        bb_upper = float(market_data.get('bb_upper', 0))
        trend_strength = float(market_data.get('trend_strength', 0))
        conditions = [
            rsi >= self.rsi_overbought - 5,      # blisko przekupienia
            ma_fast <= ma_slow,                   # krótsza MA poniżej dłuższej
            price <= bb_upper,                    # cena poniżej górnego pasma
            trend_strength >= self.min_trend_strength
        ]
        return sum(1 for c in conditions if c) >= 3

    async def _open_position(self, position_data: Dict) -> Optional[Dict]:
        """Otwórz pozycję przy użyciu giełdy i ustaw stan bieżącej pozycji"""
        try:
            if not self.exchange:
                return None
            symbol = position_data.get('symbol', self.symbol)
            side = position_data.get('side', 'buy')
            amount = float(position_data.get('amount', 0.0))
            price = float(position_data.get('price', 0.0))
            order = None
            if hasattr(self.exchange, 'create_order'):
                order = await self.exchange.create_order(symbol, 'market', side, amount, price=price)
            elif hasattr(self.exchange, 'place_order'):
                order = await self.exchange.place_order(symbol=symbol, side=side, amount=amount, price=price, order_type='market')
            if not order:
                return None
            # Ustaw bieżącą pozycję
            stop_loss = self._calculate_stop_loss(price, side)
            if side == 'buy':
                take_profit = price + (price - stop_loss) * self.take_profit_ratio
            else:
                take_profit = price - (stop_loss - price) * self.take_profit_ratio
            self.current_position = SwingPosition(
                order_id=order.get('id') or order.get('order_id', 'unknown'),
                side=side,
                amount=amount,
                entry_price=price,
                entry_time=datetime.now(),
                stop_loss=stop_loss,
                take_profit=take_profit,
                trend_at_entry=SwingTrend.UNKNOWN
            )
            return order
        except Exception as e:
            self.logger.error(f"Błąd otwierania pozycji: {e}")
            return None

    async def _update_position(self, market_data: Dict, indicators: SwingIndicators):
        """Aktualizuj istniejącą pozycję"""
        try:
            if not self.current_position:
                return
            
            current_price = market_data['current_price']
            position = self.current_position
            
            # Aktualizuj cenę i P&L
            position.current_price = current_price
            
            if position.side == 'buy':
                position.unrealized_pnl = (current_price - position.entry_price) * position.amount
            else:  # sell
                position.unrealized_pnl = (position.entry_price - current_price) * position.amount
            
            position.unrealized_pnl_percentage = (position.unrealized_pnl / (position.entry_price * position.amount)) * 100
            
            # Sprawdź warunki zamknięcia
            should_close, reason = self._should_close_position(current_price, indicators)
            
            if should_close:
                await self._close_position(reason)
                
        except Exception as e:
            self.logger.error(f"Błąd aktualizacji pozycji: {e}")
    
    def _should_close_position(self, current_price: float, indicators: SwingIndicators) -> Tuple[bool, str]:
        """Sprawdź czy zamknąć pozycję"""
        if not self.current_position:
            return False, ""
        
        position = self.current_position
        
        # Stop Loss
        if position.side == 'buy' and current_price <= position.stop_loss:
            return True, "stop_loss"
        elif position.side == 'sell' and current_price >= position.stop_loss:
            return True, "stop_loss"
        
        # Take Profit
        if position.side == 'buy' and current_price >= position.take_profit:
            return True, "take_profit"
        elif position.side == 'sell' and current_price <= position.take_profit:
            return True, "take_profit"
        
        # Maksymalny czas pozycji
        time_in_position = datetime.now() - position.entry_time
        if time_in_position.total_seconds() / 3600 > self.max_position_time_hours:
            return True, "max_time"
        
        # Zmiana trendu
        current_trend = self._identify_trend(indicators)
        if (position.side == 'buy' and current_trend == SwingTrend.DOWNTREND) or \
           (position.side == 'sell' and current_trend == SwingTrend.UPTREND):
            return True, "trend_change"
        
        return False, ""
    
    async def _close_position(self, reason: str):
        """Zamknij pozycję"""
        try:
            if not self.current_position or not self.exchange:
                return None
            position = self.current_position
            close_side = 'sell' if position.side == 'buy' else 'buy'
            self.logger.debug(f"TRACE: order.submitted - symbol={self.symbol}, side={close_side}, amount={position.amount}, type=market, strategy=swing")
            order_result = None
            if hasattr(self.exchange, 'place_order'):
                order_result = await self.exchange.place_order(
                    symbol=self.symbol,
                    side=close_side,
                    amount=position.amount,
                    order_type='market'
                )
            elif hasattr(self.exchange, 'create_order'):
                order_result = await self.exchange.create_order(
                    self.symbol,
                    'market',
                    close_side,
                    position.amount,
                    price=position.current_price or position.entry_price
                )
            else:
                self.logger.error("Exchange nie obsługuje składania zleceń")
                return None
            if order_result:
                exit_price = order_result.get('price', position.current_price or position.entry_price)
                exit_time = datetime.now()
                if position.side == 'buy':
                    pnl = (exit_price - position.entry_price) * position.amount
                else:
                    pnl = (position.entry_price - exit_price) * position.amount
                pnl_percentage = (pnl / (position.entry_price * position.amount)) * 100
                duration_hours = (exit_time - position.entry_time).total_seconds() / 3600
                trade = SwingTrade(
                    entry_order_id=position.order_id,
                    exit_order_id=order_result.get('order_id') or order_result.get('id', 'unknown'),
                    side=position.side,
                    amount=position.amount,
                    entry_price=position.entry_price,
                    exit_price=exit_price,
                    entry_time=position.entry_time,
                    exit_time=exit_time,
                    pnl=pnl,
                    pnl_percentage=pnl_percentage,
                    duration_hours=duration_hours,
                    exit_reason=reason,
                    trend_at_entry=position.trend_at_entry,
                    trend_at_exit=self._identify_trend(self.indicators_history[-1]) if self.indicators_history else SwingTrend.UNKNOWN
                )
                self.trade_history.append(trade)
                self.current_position = None
            return order_result
        except Exception as e:
            self.logger.error(f"Błąd zamykania pozycji: {e}")
            return None
    
    def _is_trading_time(self) -> bool:
        """Sprawdź czy to czas handlu"""
        if not self.start_time or not self.end_time:
            return True
        
        current_time = datetime.now().time()
        start_time = datetime.strptime(self.start_time, "%H:%M").time()
        end_time = datetime.strptime(self.end_time, "%H:%M").time()
        
        return start_time <= current_time <= end_time
    
    def _check_trade_limits(self) -> bool:
        """Sprawdź limity transakcji"""
        if not self.max_weekly_trades:
            return True
        
        # Policz transakcje z ostatniego tygodnia
        week_ago = datetime.now() - timedelta(days=7)
        recent_trades = [t for t in self.trade_history if t.entry_time >= week_ago]
        
        return len(recent_trades) < self.max_weekly_trades
    
    def _update_statistics(self):
        """Aktualizuj statystyki"""
        if not self.trade_history:
            return
        
        stats = self.statistics
        trades = self.trade_history
        
        stats.total_trades = len(trades)
        stats.winning_trades = len([t for t in trades if t.pnl > 0])
        stats.losing_trades = len([t for t in trades if t.pnl < 0])
        stats.total_pnl = sum(t.pnl for t in trades)
        stats.total_pnl_percentage = sum(t.pnl_percentage for t in trades)
        stats.win_rate = (stats.winning_trades / stats.total_trades) * 100 if stats.total_trades > 0 else 0
        
        winning_trades = [t for t in trades if t.pnl > 0]
        losing_trades = [t for t in trades if t.pnl < 0]
        
        stats.avg_win = sum(t.pnl for t in winning_trades) / len(winning_trades) if winning_trades else 0
        stats.avg_loss = sum(t.pnl for t in losing_trades) / len(losing_trades) if losing_trades else 0
        stats.avg_trade_duration_hours = sum(t.duration_hours for t in trades) / len(trades)
        
        stats.best_trade = max(t.pnl for t in trades) if trades else 0
        stats.worst_trade = min(t.pnl for t in trades) if trades else 0
        stats.total_volume = sum(t.amount * t.entry_price for t in trades)
        
        # Profit factor
        total_wins = sum(t.pnl for t in winning_trades)
        total_losses = abs(sum(t.pnl for t in losing_trades))
        stats.profit_factor = total_wins / total_losses if total_losses > 0 else 0
        
        # Trend accuracy
        correct_trends = len([t for t in trades if 
                            (t.side == 'buy' and t.trend_at_entry == SwingTrend.UPTREND and t.pnl > 0) or
                            (t.side == 'sell' and t.trend_at_entry == SwingTrend.DOWNTREND and t.pnl > 0)])
        stats.trend_accuracy = (correct_trends / stats.total_trades) * 100 if stats.total_trades > 0 else 0
    
    async def _save_position_to_db(self):
        """Zapisz pozycję do bazy danych"""
        try:
            if not self.db_manager or not self.current_position:
                return
            
            position_data = {
                'strategy_type': 'swing',
                'symbol': self.symbol,
                'position_data': json.dumps(asdict(self.current_position), default=str),
                'created_at': datetime.now()
            }
            
            await self.db_manager.save_position(position_data)
            
        except Exception as e:
            self.logger.error(f"Błąd zapisu pozycji do DB: {e}")
    
    async def _save_trade_to_db(self, trade: SwingTrade):
        """Zapisz transakcję do bazy danych"""
        try:
            if not self.db_manager:
                return
            
            trade_data = {
                'strategy_type': 'swing',
                'symbol': self.symbol,
                'side': trade.side,
                'amount': trade.amount,
                'entry_price': trade.entry_price,
                'exit_price': trade.exit_price,
                'pnl': trade.pnl,
                'pnl_percentage': trade.pnl_percentage,
                'entry_time': trade.entry_time,
                'exit_time': trade.exit_time,
                'duration_hours': trade.duration_hours,
                'exit_reason': trade.exit_reason,
                'metadata': json.dumps({
                    'trend_at_entry': trade.trend_at_entry.value,
                    'trend_at_exit': trade.trend_at_exit.value
                })
            }
            
            await self.db_manager.save_trade(trade_data)
            
        except Exception as e:
            self.logger.error(f"Błąd zapisu transakcji do DB: {e}")
    
    def get_status(self) -> Dict:
        """Pobierz status strategii"""
        return {
            'status': self.status.value,
            'symbol': self.symbol,
            'timeframe': self.timeframe,
            'is_running': self.is_running,
            'is_paused': self.is_paused,
            'current_position': asdict(self.current_position) if self.current_position else None,
            'statistics': asdict(self.statistics),
            'total_trades': len(self.trade_history),
            'last_update': datetime.now().isoformat()
        }
    
    def get_performance_summary(self) -> Dict:
        """Pobierz podsumowanie wydajności"""
        return {
            'total_pnl': self.statistics.total_pnl,
            'total_pnl_percentage': self.statistics.total_pnl_percentage,
            'win_rate': self.statistics.win_rate,
            'total_trades': self.statistics.total_trades,
            'avg_trade_duration_hours': self.statistics.avg_trade_duration_hours,
            'profit_factor': self.statistics.profit_factor,
            'trend_accuracy': self.statistics.trend_accuracy,
            'sharpe_ratio': self.statistics.sharpe_ratio
        }
    
    # Metody konfiguracji
    def set_exchange(self, exchange: BaseExchange):
        """Ustaw giełdę"""
        self.exchange = exchange
        self.logger.info(f"Ustawiono giełdę: {exchange.__class__.__name__}")
    
    def set_db_manager(self, db_manager: DatabaseManager):
        """Ustaw menedżer bazy danych"""
        self.db_manager = db_manager
        self.logger.info("Ustawiono menedżer bazy danych")
    
    def set_risk_manager(self, risk_manager: RiskManager):
        """Ustaw menedżer ryzyka"""
        self.risk_manager = risk_manager
        self.logger.info("Ustawiono menedżer ryzyka")

    def _calculate_rsi(self, ohlcv: List[Union[List, Dict]], period: Optional[int] = None) -> List[float]:
        """Oblicz RSI z danych OHLCV, zwraca listę wartości RSI"""
        try:
            if period is None:
                period = self.rsi_period
            closes: List[float] = []
            for row in ohlcv:
                if isinstance(row, dict) and 'close' in row:
                    closes.append(float(row['close']))
                elif isinstance(row, (list, tuple)) and len(row) >= 5:
                    closes.append(float(row[4]))
            if len(closes) < period + 1:
                return []
            deltas = [closes[i] - closes[i - 1] for i in range(1, len(closes))]
            gains = [max(d, 0.0) for d in deltas]
            losses = [abs(min(d, 0.0)) for d in deltas]
            avg_gain = sum(gains[:period]) / period
            avg_loss = sum(losses[:period]) / period
            rsi_values: List[float] = []
            # Pierwsza wartość RSI po początkowym oknie
            rs = (avg_gain / avg_loss) if avg_loss > 0 else float('inf')
            rsi_values.append(100 - (100 / (1 + rs)))
            for i in range(period, len(deltas)):
                avg_gain = ((avg_gain * (period - 1)) + gains[i]) / period
                avg_loss = ((avg_loss * (period - 1)) + losses[i]) / period
                if avg_loss == 0:
                    rsi = 100.0
                else:
                    rs = avg_gain / avg_loss
                    rsi = 100 - (100 / (1 + rs))
                rsi_values.append(rsi)
            return rsi_values
        except Exception as e:
            self.logger.error(f"Błąd obliczania RSI: {e}")
            return []

    def _identify_trend(self, indicators: SwingIndicators) -> SwingTrend:
        """Zidentyfikuj trend na podstawie wskaźników"""
        try:
            if indicators.sma_20 is not None and indicators.sma_50 is not None:
                if indicators.sma_20 > indicators.sma_50:
                    return SwingTrend.UPTREND
                elif indicators.sma_20 < indicators.sma_50:
                    return SwingTrend.DOWNTREND
                else:
                    return SwingTrend.SIDEWAYS
            # Fallback do MACD jeżeli dostępny
            if indicators.macd is not None and indicators.macd_signal is not None:
                if indicators.macd > indicators.macd_signal:
                    return SwingTrend.UPTREND
                elif indicators.macd < indicators.macd_signal:
                    return SwingTrend.DOWNTREND
                else:
                    return SwingTrend.SIDEWAYS
            return SwingTrend.UNKNOWN
        except Exception as e:
            self.logger.error(f"Błąd identyfikacji trendu: {e}")
            return SwingTrend.UNKNOWN

    async def _execute_strategy_cycle(self):
        """Wykonaj pojedynczy cykl strategii: pobierz dane, oblicz wskaźniki, zaktualizuj pozycję"""
        try:
            if not self.is_running:
                return False
            market_data = await self._get_market_data()
            if not market_data:
                return False
            ohlcv = market_data['candles']
            # Oblicz podstawowe wskaźniki
            ma_fast_list = self._calculate_moving_average(ohlcv, self.sma_short)
            ma_slow_list = self._calculate_moving_average(ohlcv, self.sma_medium)
            ma_fast = ma_fast_list[-1] if ma_fast_list else None
            ma_slow = ma_slow_list[-1] if ma_slow_list else None
            rsi_values = self._calculate_rsi(ohlcv, self.rsi_period)
            rsi = rsi_values[-1] if rsi_values else None
            bb_upper, bb_middle, bb_lower = self._calculate_bollinger_bands(ohlcv, self.bb_period, self.bb_std)
            indicators = SwingIndicators(
                sma_20=ma_fast,
                sma_50=ma_slow,
                rsi=rsi,
                bb_upper=bb_upper,
                bb_middle=bb_middle,
                bb_lower=bb_lower
            )
            self.indicators_history.append(indicators)
            # Aktualizacja pozycji jeśli istnieje
            await self._update_position({
                'current_price': market_data['current_price'],
                'volume': market_data['volume'],
                'timestamp': market_data['timestamp']
            }, indicators)
            return True
        except Exception as e:
            self.logger.error(f"Błąd cyklu strategii: {e}")
            return False
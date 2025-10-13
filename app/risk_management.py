"""
Risk Management - Zaawansowany system zarządzania ryzykiem w tradingu
"""

import asyncio
import json
import math
import statistics
import threading
from dataclasses import dataclass, asdict
from datetime import datetime, timedelta
from decimal import Decimal, ROUND_DOWN
from enum import Enum
from pathlib import Path
from typing import Any, Callable, Coroutine, Dict, List, Optional, Tuple, Union

from utils.logger import get_logger
from utils.event_bus import get_event_bus, EventTypes
import logging
logger = logging.getLogger(__name__)

class RiskLevel(Enum):
    """Poziomy ryzyka"""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"

class RiskEventType(Enum):
    """Typy zdarzeń ryzyka"""
    STOP_LOSS = "stop_loss"
    TAKE_PROFIT = "take_profit"
    TRAILING_STOP = "trailing_stop"
    DAILY_LOSS_LIMIT = "daily_loss_limit"
    DAILY_PROFIT_LIMIT = "daily_profit_limit"
    POSITION_SIZE_LIMIT = "position_size_limit"
    MARKET_VOLATILITY = "market_volatility"
    DRAWDOWN_LIMIT = "drawdown_limit"
    CORRELATION_RISK = "correlation_risk"
    EMERGENCY_STOP = "emergency_stop"

@dataclass
class RiskEvent:
    """Zdarzenie ryzyka"""
    bot_id: int
    event_type: RiskEventType
    level: RiskLevel
    message: str
    timestamp: datetime
    data: Dict[str, Any]
    
    def to_dict(self) -> Dict[str, Any]:
        """Konwersja do słownika"""
        return {
            'bot_id': self.bot_id,
            'event_type': self.event_type.value,
            'level': self.level.value,
            'message': self.message,
            'timestamp': self.timestamp.isoformat(),
            'data': self.data
        }

@dataclass
class RiskMetrics:
    """Metryki ryzyka"""
    daily_pnl: float = 0.0
    daily_loss: float = 0.0
    daily_profit: float = 0.0
    max_drawdown: float = 0.0
    current_drawdown: float = 0.0
    win_rate: float = 0.0
    profit_factor: float = 0.0
    sharpe_ratio: float = 0.0
    var_95: float = 0.0  # Value at Risk 95%
    exposure: float = 0.0
    correlation_risk: float = 0.0
    
    def to_dict(self) -> Dict[str, Any]:
        """Konwersja do słownika"""
        return asdict(self)

@dataclass
class RiskLimits:
    """Limity ryzyka"""
    daily_loss_limit: float = 0.0
    daily_profit_limit: float = 0.0
    max_drawdown_limit: float = 0.0
    position_size_limit: float = 0.0
    max_open_positions: int = 0
    max_correlation: float = 0.8
    volatility_threshold: float = 10.0
    var_limit: float = 0.0
    
    def to_dict(self) -> Dict[str, Any]:
        """Konwersja do słownika"""
        return asdict(self)

@dataclass
class PositionRisk:
    """Ryzyko pozycji"""
    position_id: str
    bot_id: int
    pair: str
    size: float
    entry_price: float
    current_price: float
    unrealized_pnl: float
    risk_amount: float
    stop_loss_price: Optional[float] = None
    take_profit_price: Optional[float] = None
    trailing_stop_price: Optional[float] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Konwersja do słownika"""
        return asdict(self)

class RiskManager:
    """Zaawansowany manager zarządzania ryzykiem"""
    
    def __init__(self, db_manager=None):
        self.logger = get_logger("RiskManager")
        self.db_manager = db_manager
        self.event_bus = get_event_bus()
        
        # Subskrypcja na zmiany konfiguracji
        self.event_bus.subscribe(EventTypes.CONFIG_UPDATED, self._on_config_updated)
        self.event_bus.subscribe(EventTypes.CONFIG_RISK_UPDATED, self._on_config_updated)
        
        # Synchronizacja
        self._lock = threading.RLock()
        self._async_lock = asyncio.Lock()
        
        # Cache dla limitów i metryk
        self.limits_cache: Dict[int, RiskLimits] = {}
        self.metrics_cache: Dict[int, RiskMetrics] = {}
        self.positions_cache: Dict[int, List[PositionRisk]] = {}
        
        # Historia zdarzeń ryzyka
        self.risk_events: List[RiskEvent] = []
        
        # Flaga działania
        self.is_running = False
        self._monitoring_task = None
        
        # Korelacje między parami
        self.correlation_matrix: Dict[Tuple[str, str], float] = {}
        
        # Domyślne limity
        self.default_limits = RiskLimits(
            daily_loss_limit=1000.0,
            daily_profit_limit=5000.0,
            max_drawdown_limit=20.0,
            position_size_limit=10000.0,
            max_open_positions=10,
            max_correlation=0.8,
            volatility_threshold=10.0,
            var_limit=500.0
        )
        self.static_limits_map = self._load_static_limits()
        self.historical_metrics = self._load_historical_metrics()
        
    async def initialize(self) -> bool:
        """Inicjalizacja managera ryzyka"""
        try:
            async with self._async_lock:
                self.logger.info("Inicjalizacja Risk Manager...")
                
                # Sprawdzenie dostępności bazy danych
                if not self.db_manager:
                    self.logger.warning("Brak połączenia z bazą danych - używam trybu offline")
                    return True
                
                # Załadowanie limitów dla wszystkich botów
                await self._load_all_risk_limits()
                
                # Załadowanie aktualnych pozycji
                await self._load_current_positions()
                
                # Obliczenie korelacji
                await self._calculate_correlations()
                
                self.is_running = True
                self.logger.info("Risk Manager zainicjalizowany pomyślnie")
                return True
                
        except Exception as e:
            self.logger.error(f"Błąd podczas inicjalizacji Risk Manager: {e}")
            return False
    
    async def start_monitoring(self):
        """Uruchomienie monitorowania ryzyka"""
        try:
            if not self.is_running:
                await self.initialize()
            
            if self._monitoring_task and not self._monitoring_task.done():
                self.logger.warning("Monitorowanie już działa")
                return
            
            self.logger.info("Uruchamianie monitorowania ryzyka...")
            self._monitoring_task = asyncio.create_task(self._monitoring_loop())
            
        except Exception as e:
            self.logger.error(f"Błąd podczas uruchamiania monitorowania: {e}")
    
    async def stop_monitoring(self):
        """Zatrzymanie monitorowania ryzyka"""
        try:
            self.logger.info("Zatrzymywanie monitorowania ryzyka...")
            self.is_running = False
            
            if self._monitoring_task and not self._monitoring_task.done():
                self._monitoring_task.cancel()
                try:
                    await self._monitoring_task
                except asyncio.CancelledError:
                    pass
                    
        except Exception as e:
            self.logger.error(f"Błąd podczas zatrzymywania monitorowania: {e}")
    
    async def _monitoring_loop(self):
        """Główna pętla monitorowania"""
        while self.is_running:
            try:
                await self._monitor_all_risks()
                await self._update_risk_metrics()
                await self._check_correlation_risks()
                await asyncio.sleep(5)  # Sprawdzanie co 5 sekund
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                self.logger.error(f"Błąd w pętli monitorowania ryzyka: {e}")
                await asyncio.sleep(10)
    
    # === SPRAWDZANIE RYZYKA POZYCJI ===
    
    async def check_position_risk(self, bot_id: int, position: PositionRisk) -> List[RiskEvent]:
        """Sprawdzenie ryzyka pojedynczej pozycji"""
        events = []
        
        try:
            # Stop Loss
            if position.stop_loss_price and self._check_stop_loss_trigger(
                position.current_price, position.entry_price, position.stop_loss_price
            ):
                events.append(RiskEvent(
                    bot_id=bot_id,
                    event_type=RiskEventType.STOP_LOSS,
                    level=RiskLevel.HIGH,
                    message=f"Stop Loss triggered for {position.pair}",
                    timestamp=datetime.now(),
                    data={"position_id": position.position_id, "price": position.current_price}
                ))
            
            # Take Profit
            if position.take_profit_price and self._check_take_profit_trigger(
                position.current_price, position.entry_price, position.take_profit_price
            ):
                events.append(RiskEvent(
                    bot_id=bot_id,
                    event_type=RiskEventType.TAKE_PROFIT,
                    level=RiskLevel.LOW,
                    message=f"Take Profit triggered for {position.pair}",
                    timestamp=datetime.now(),
                    data={"position_id": position.position_id, "price": position.current_price}
                ))
            
            # Trailing Stop
            if position.trailing_stop_price:
                should_trigger, new_trailing_price = self._check_trailing_stop_trigger(
                    position.current_price, position.trailing_stop_price
                )
                if should_trigger:
                    events.append(RiskEvent(
                        bot_id=bot_id,
                        event_type=RiskEventType.TRAILING_STOP,
                        level=RiskLevel.MEDIUM,
                        message=f"Trailing Stop triggered for {position.pair}",
                        timestamp=datetime.now(),
                        data={"position_id": position.position_id, "price": position.current_price}
                    ))
                else:
                    # Aktualizacja trailing stop
                    position.trailing_stop_price = new_trailing_price
            
            return events
            
        except Exception as e:
            self.logger.error(f"Błąd podczas sprawdzania ryzyka pozycji: {e}")
            return []
    
    def _check_stop_loss_trigger(self, current_price: float, entry_price: float, stop_loss_price: float) -> bool:
        """Sprawdzenie czy należy wykonać stop loss"""
        try:
            # Dla pozycji długiej
            if entry_price > 0 and current_price <= stop_loss_price:
                loss_percent = ((entry_price - current_price) / entry_price) * 100
                self.logger.warning(
                    f"Stop Loss triggered! Entry: {entry_price}, Current: {current_price}, "
                    f"Stop Loss: {stop_loss_price}, Loss: {loss_percent:.2f}%"
                )
                return True
            return False
            
        except Exception as e:
            self.logger.error(f"Błąd podczas sprawdzania stop loss: {e}")
            return False
    
    def _check_take_profit_trigger(self, current_price: float, entry_price: float, take_profit_price: float) -> bool:
        """Sprawdzenie czy należy wykonać take profit"""
        try:
            # Dla pozycji długiej
            if entry_price > 0 and current_price >= take_profit_price:
                profit_percent = ((current_price - entry_price) / entry_price) * 100
                self.logger.info(
                    f"Take Profit triggered! Entry: {entry_price}, Current: {current_price}, "
                    f"Take Profit: {take_profit_price}, Profit: {profit_percent:.2f}%"
                )
                return True
            return False
            
        except Exception as e:
            self.logger.error(f"Błąd podczas sprawdzania take profit: {e}")
            return False
    
    def _check_trailing_stop_trigger(self, current_price: float, trailing_stop_price: float, 
                                   trailing_percent: float = 2.0) -> Tuple[bool, float]:
        """Sprawdzenie trailing stop i aktualizacja"""
        try:
            # Obliczenie nowego trailing stop
            new_trailing_stop = current_price * (1 - trailing_percent / 100)
            
            # Aktualizacja trailing stop tylko w górę
            updated_trailing_stop = max(trailing_stop_price, new_trailing_stop)
            
            # Sprawdzenie czy należy wykonać trailing stop
            if current_price <= trailing_stop_price:
                self.logger.info(
                    f"Trailing Stop triggered! Current: {current_price}, Trailing Stop: {trailing_stop_price}"
                )
                return True, updated_trailing_stop
                
            return False, updated_trailing_stop
            
        except Exception as e:
            self.logger.error(f"Błąd podczas sprawdzania trailing stop: {e}")
            return False, trailing_stop_price
    
    # === SPRAWDZANIE LIMITÓW DZIENNYCH ===
    
    async def check_daily_limits(self, bot_id: int) -> List[RiskEvent]:
        """Sprawdzenie dziennych limitów"""
        events = []
        
        try:
            limits = await self.get_risk_limits(bot_id)
            metrics = await self.get_risk_metrics(bot_id)
            
            # Sprawdzenie limitu dziennych strat
            if limits.daily_loss_limit > 0 and metrics.daily_loss >= limits.daily_loss_limit:
                events.append(RiskEvent(
                    bot_id=bot_id,
                    event_type=RiskEventType.DAILY_LOSS_LIMIT,
                    level=RiskLevel.CRITICAL,
                    message=f"Daily loss limit exceeded: {metrics.daily_loss:.2f}",
                    timestamp=datetime.now(),
                    data={"limit": limits.daily_loss_limit, "actual": metrics.daily_loss}
                ))
            
            # Sprawdzenie limitu dziennych zysków
            if limits.daily_profit_limit > 0 and metrics.daily_profit >= limits.daily_profit_limit:
                events.append(RiskEvent(
                    bot_id=bot_id,
                    event_type=RiskEventType.DAILY_PROFIT_LIMIT,
                    level=RiskLevel.MEDIUM,
                    message=f"Daily profit limit reached: {metrics.daily_profit:.2f}",
                    timestamp=datetime.now(),
                    data={"limit": limits.daily_profit_limit, "actual": metrics.daily_profit}
                ))
            
            # Sprawdzenie limitu drawdown
            if limits.max_drawdown_limit > 0 and metrics.current_drawdown >= limits.max_drawdown_limit:
                events.append(RiskEvent(
                    bot_id=bot_id,
                    event_type=RiskEventType.DRAWDOWN_LIMIT,
                    level=RiskLevel.CRITICAL,
                    message=f"Drawdown limit exceeded: {metrics.current_drawdown:.2f}%",
                    timestamp=datetime.now(),
                    data={"limit": limits.max_drawdown_limit, "actual": metrics.current_drawdown}
                ))
            
            return events
            
        except Exception as e:
            self.logger.error(f"Błąd podczas sprawdzania dziennych limitów: {e}")
            return []
    
    async def check_position_size_limit(self, bot_id: int, position_size: float, 
                                      available_balance: float) -> bool:
        """Sprawdzenie czy rozmiar pozycji nie przekracza limitów"""
        try:
            limits = await self.get_risk_limits(bot_id)
            
            # Sprawdzenie dostępnego salda
            if position_size > available_balance:
                await self._log_risk_event(
                    bot_id, RiskEventType.POSITION_SIZE_LIMIT, RiskLevel.HIGH,
                    f"Position size {position_size} exceeds available balance {available_balance}"
                )
                return False
            
            # Sprawdzenie limitu rozmiaru pozycji
            if limits.position_size_limit > 0 and position_size > limits.position_size_limit:
                await self._log_risk_event(
                    bot_id, RiskEventType.POSITION_SIZE_LIMIT, RiskLevel.HIGH,
                    f"Position size {position_size} exceeds limit {limits.position_size_limit}"
                )
                return False
            
            return True
            
        except Exception as e:
            self.logger.error(f"Błąd podczas sprawdzania rozmiaru pozycji: {e}")
            return False
    
    # === SPRAWDZANIE RYZYKA RYNKOWEGO ===
    
    async def check_market_volatility(self, pair: str, current_price: float) -> bool:
        """Sprawdzenie zmienności rynku"""
        try:
            if not self.db_manager:
                return True  # Brak danych - pozwalamy na handel
            
            # Symulacja sprawdzenia zmienności (w rzeczywistej implementacji pobieramy dane z bazy)
            # Dla celów demonstracyjnych zwracamy True
            volatility = 5.0  # Przykładowa zmienność
            volatility_threshold = 10.0
            
            if volatility > volatility_threshold:
                self.logger.warning(f"High market volatility detected for {pair}: {volatility:.2f}%")
                return False
                
            return True
            
        except Exception as e:
            self.logger.error(f"Błąd podczas sprawdzania zmienności rynku: {e}")
            return True
    
    async def _check_correlation_risks(self):
        """Sprawdzenie ryzyka korelacji między pozycjami"""
        try:
            for bot_id in self.positions_cache:
                positions = self.positions_cache[bot_id]
                
                if len(positions) < 2:
                    continue
                
                # Sprawdzenie korelacji między parami
                high_correlation_pairs = []
                
                for i in range(len(positions)):
                    for j in range(i + 1, len(positions)):
                        pair1 = positions[i].pair
                        pair2 = positions[j].pair
                        
                        correlation = self.correlation_matrix.get((pair1, pair2), 0.0)
                        
                        if abs(correlation) > 0.8:  # Wysoka korelacja
                            high_correlation_pairs.append((pair1, pair2, correlation))
                
                if high_correlation_pairs:
                    await self._log_risk_event(
                        bot_id, RiskEventType.CORRELATION_RISK, RiskLevel.MEDIUM,
                        f"High correlation detected: {high_correlation_pairs}"
                    )
            
        except Exception as e:
            self.logger.error(f"Błąd podczas sprawdzania ryzyka korelacji: {e}")
    
    # === OBLICZENIA RYZYKA ===
    
    def calculate_position_size(self, balance: float, risk_percent: float, 
                              entry_price: float, stop_loss_price: float) -> float:
        """Obliczenie rozmiaru pozycji na podstawie zarządzania ryzykiem"""
        try:
            if stop_loss_price >= entry_price or entry_price <= 0:
                return 0.0
            
            # Obliczenie ryzyka na jednostkę
            risk_per_unit = entry_price - stop_loss_price
            
            # Obliczenie maksymalnego ryzyka
            max_risk = balance * (risk_percent / 100)
            
            # Obliczenie rozmiaru pozycji
            position_size = max_risk / risk_per_unit
            
            # Ograniczenie do dostępnego salda
            max_position_size = balance / entry_price
            
            return min(position_size, max_position_size)
            
        except Exception as e:
            self.logger.error(f"Błąd podczas obliczania rozmiaru pozycji: {e}")
            return 0.0
    
    def calculate_risk_reward_ratio(self, entry_price: float, stop_loss_price: float, 
                                  take_profit_price: float) -> float:
        """Obliczenie stosunku ryzyko/zysk"""
        try:
            if entry_price <= 0 or stop_loss_price >= entry_price or take_profit_price <= entry_price:
                return 0.0
            
            risk = entry_price - stop_loss_price
            reward = take_profit_price - entry_price
            
            return reward / risk if risk > 0 else 0.0
            
        except Exception as e:
            self.logger.error(f"Błąd podczas obliczania stosunku ryzyko/zysk: {e}")
            return 0.0
    
    async def calculate_value_at_risk(self, bot_id: int, confidence_level: float = 0.95) -> float:
        """Obliczenie Value at Risk (VaR)"""
        try:
            if not self.db_manager:
                metrics = self._get_static_metrics(bot_id)
                if metrics:
                    return metrics.var_95
                return 0.0

            # Symulacja obliczeń VaR (w rzeczywistej implementacji pobieramy dane z bazy)
            # Dla celów demonstracyjnych zwracamy przykładową wartość
            return 100.0
            
        except Exception as e:
            self.logger.error(f"Błąd podczas obliczania VaR: {e}")
            return 0.0
    
    # === ZARZĄDZANIE LIMITAMI I METRYKAMI ===
    
    async def get_risk_limits(self, bot_id: int) -> RiskLimits:
        """Pobranie limitów ryzyka dla bota"""
        try:
            with self._lock:
                if bot_id in self.limits_cache:
                    return self.limits_cache[bot_id]
            
            # Załaduj z bazy danych
            limits = await self.load_limits_from_db(bot_id)
            return limits
            
        except Exception as e:
            self.logger.error(f"Błąd podczas pobierania limitów ryzyka: {e}")
            return self.default_limits
    
    async def update_risk_limits(self, bot_id: int, limits: RiskLimits):
        """Aktualizacja limitów ryzyka"""
        try:
            if self.db_manager:
                # Symulacja aktualizacji w bazie danych
                pass
            
            # Aktualizacja cache
            with self._lock:
                self.limits_cache[bot_id] = limits
            
            self.logger.info(f"Zaktualizowano limity ryzyka dla bota {bot_id}")
            
        except Exception as e:
            self.logger.error(f"Błąd podczas aktualizacji limitów ryzyka: {e}")
    
    async def get_risk_metrics(self, bot_id: int) -> RiskMetrics:
        """Pobranie metryk ryzyka dla bota"""
        try:
            with self._lock:
                if bot_id in self.metrics_cache:
                    return self.metrics_cache[bot_id]
            
            # Obliczenie metryk
            metrics = await self._calculate_risk_metrics(bot_id)
            
            with self._lock:
                self.metrics_cache[bot_id] = metrics
            
            return metrics
            
        except Exception as e:
            self.logger.error(f"Błąd podczas pobierania metryk ryzyka: {e}")
            return RiskMetrics()
    
    async def _calculate_risk_metrics(self, bot_id: int) -> RiskMetrics:
        """Obliczenie metryk ryzyka"""
        try:
            if not self.db_manager:
                metrics = self._get_static_metrics(bot_id)
                if metrics:
                    return metrics
                # Zwróć domyślne metryki jeśli brak bazy danych
                return RiskMetrics()

            # Symulacja obliczeń metryk (w rzeczywistej implementacji pobieramy dane z bazy)
            return RiskMetrics(
                daily_pnl=0.0,
                daily_loss=0.0,
                daily_profit=0.0,
                max_drawdown=0.0,
                current_drawdown=0.0,
                win_rate=0.0,
                var_95=0.0
            )
            
        except Exception as e:
            self.logger.error(f"Błąd podczas obliczania metryk ryzyka: {e}")
            return RiskMetrics()
    
    def calculate_drawdown(self, equity_curve: List[float]) -> Tuple[float, float]:
        """Obliczenie drawdown"""
        try:
            if not equity_curve:
                return 0.0, 0.0
            
            max_equity = equity_curve[0]
            max_drawdown = 0.0
            
            for equity in equity_curve:
                if equity > max_equity:
                    max_equity = equity
                
                drawdown = (max_equity - equity) / max_equity * 100 if max_equity > 0 else 0.0
                max_drawdown = max(max_drawdown, drawdown)
            
            # Obecny drawdown
            current_equity = equity_curve[-1]
            current_max = max(equity_curve)
            current_drawdown = (current_max - current_equity) / current_max * 100 if current_max > 0 else 0.0
            
            return max_drawdown, current_drawdown
            
        except Exception as e:
            self.logger.error(f"Błąd podczas obliczania drawdown: {e}")
            return 0.0, 0.0
    
    # === POMOCNICZE METODY ===
    
    async def _load_all_risk_limits(self):
        """Załadowanie limitów ryzyka dla wszystkich botów"""
        try:
            if not self.db_manager:
                self.logger.info("Brak bazy danych - używam domyślnych limitów")
                return
            
            # Symulacja ładowania limitów
            self.logger.info("Załadowano limity ryzyka")
            
        except Exception as e:
            self.logger.error(f"Błąd podczas ładowania limitów ryzyka: {e}")
    
    async def _load_current_positions(self):
        """Załadowanie aktualnych pozycji"""
        try:
            if not self.db_manager:
                self.logger.info("Brak bazy danych - brak pozycji do załadowania")
                return
            
            # Symulacja ładowania pozycji
            self.logger.info("Załadowano aktualne pozycje")
            
        except Exception as e:
            self.logger.error(f"Błąd podczas ładowania pozycji: {e}")
    
    async def _calculate_correlations(self):
        """Obliczenie korelacji między parami walutowymi"""
        try:
            if not self.db_manager:
                self.logger.info("Brak bazy danych - brak danych do obliczenia korelacji")
                return
            
            # Symulacja obliczania korelacji
            self.logger.info("Obliczono korelacje między parami")
            
        except Exception as e:
            self.logger.error(f"Błąd podczas obliczania korelacji: {e}")
    
    async def _monitor_all_risks(self):
        """Monitorowanie wszystkich rodzajów ryzyka"""
        try:
            for bot_id in self.positions_cache:
                # Sprawdzenie limitów dziennych
                daily_events = await self.check_daily_limits(bot_id)
                self.risk_events.extend(daily_events)
                
                # Sprawdzenie ryzyka pozycji
                positions = self.positions_cache[bot_id]
                for position in positions:
                    position_events = await self.check_position_risk(bot_id, position)
                    self.risk_events.extend(position_events)
                
                # Przetworzenie zdarzeń ryzyka
                await self._process_risk_events(bot_id)
            
        except Exception as e:
            self.logger.error(f"Błąd podczas monitorowania ryzyka: {e}")
    
    async def _process_risk_events(self, bot_id: int):
        """Przetworzenie zdarzeń ryzyka"""
        try:
            bot_events = [event for event in self.risk_events if event.bot_id == bot_id]
            
            for event in bot_events:
                # Logowanie zdarzenia
                await self._log_risk_event(
                    event.bot_id, event.event_type, event.level, event.message
                )
                
                # Akcje w zależności od poziomu ryzyka
                if event.level == RiskLevel.CRITICAL:
                    await self._emergency_stop_bot(event.bot_id, event.message)
                elif event.level == RiskLevel.HIGH:
                    await self._pause_bot_trading(event.bot_id, event.message)
            
            # Usunięcie przetworzonych zdarzeń
            self.risk_events = [event for event in self.risk_events if event.bot_id != bot_id]
            
        except Exception as e:
            self.logger.error(f"Błąd podczas przetwarzania zdarzeń ryzyka: {e}")
    
    async def _update_risk_metrics(self):
        """Aktualizacja metryk ryzyka"""
        try:
            for bot_id in self.positions_cache:
                metrics = await self._calculate_risk_metrics(bot_id)
                with self._lock:
                    self.metrics_cache[bot_id] = metrics
            
        except Exception as e:
            self.logger.error(f"Błąd podczas aktualizacji metryk ryzyka: {e}")
    
    async def _log_risk_event(self, bot_id: int, event_type: RiskEventType,
                           level: RiskLevel, message: str):
        """Logowanie zdarzenia ryzyka"""
        try:
            if self.db_manager:
                # Symulacja logowania do bazy danych
                pass

            # Logowanie w konsoli
            if level == RiskLevel.CRITICAL:
                self.logger.critical(f"Bot {bot_id}: {message}")
            elif level == RiskLevel.HIGH:
                self.logger.error(f"Bot {bot_id}: {message}")
            elif level == RiskLevel.MEDIUM:
                self.logger.warning(f"Bot {bot_id}: {message}")
            else:
                self.logger.info(f"Bot {bot_id}: {message}")

            self._publish_risk_event(bot_id, event_type, level, message)

        except Exception as e:
            self.logger.error(f"Błąd podczas logowania zdarzenia ryzyka: {e}")
    
    async def _emergency_stop_bot(self, bot_id: int, reason: str):
        """Awaryjne zatrzymanie bota"""
        try:
            self.logger.critical(f"EMERGENCY STOP for bot {bot_id}: {reason}")
            
            if self.db_manager:
                # Symulacja aktualizacji statusu bota
                pass
            
            # Zamknięcie wszystkich otwartych pozycji
            await self._close_all_positions(bot_id, "Emergency stop")
            
            # Powiadomienie
            await self._send_risk_notification(bot_id, "EMERGENCY STOP", reason, RiskLevel.CRITICAL)
            
        except Exception as e:
            self.logger.error(f"Błąd podczas awaryjnego zatrzymania bota: {e}")
    
    async def _pause_bot_trading(self, bot_id: int, reason: str):
        """Wstrzymanie tradingu bota"""
        try:
            self.logger.warning(f"PAUSING trading for bot {bot_id}: {reason}")
            
            if self.db_manager:
                # Symulacja aktualizacji statusu bota
                pass
            
            # Powiadomienie
            await self._send_risk_notification(bot_id, "TRADING PAUSED", reason, RiskLevel.HIGH)
            
        except Exception as e:
            self.logger.error(f"Błąd podczas wstrzymywania tradingu bota: {e}")
    
    async def _close_all_positions(self, bot_id: int, reason: str):
        """Zamknięcie wszystkich pozycji bota"""
        try:
            positions = self.positions_cache.get(bot_id, [])
            
            for position in positions:
                if self.db_manager:
                    # Symulacja zamykania pozycji w bazie danych
                    pass
            
            # Wyczyszczenie cache pozycji
            with self._lock:
                self.positions_cache[bot_id] = []
            
            self.logger.info(f"Zamknięto {len(positions)} pozycji dla bota {bot_id}")
            
        except Exception as e:
            self.logger.error(f"Błąd podczas zamykania pozycji: {e}")
    
    async def _send_risk_notification(self, bot_id: int, title: str, message: str, level: RiskLevel):
        """Wysłanie powiadomienia o ryzyku"""
        try:
            # Implementacja systemu powiadomień
            self.logger.info(f"Risk notification: {title} - {message}")
            
        except Exception as e:
            self.logger.error(f"Błąd podczas wysyłania powiadomienia o ryzyku: {e}")
    
    async def get_risk_report(self, bot_id: int) -> Dict[str, Any]:
        """Generowanie raportu ryzyka"""
        try:
            limits = await self.get_risk_limits(bot_id)
            metrics = await self.get_risk_metrics(bot_id)
            positions = self.positions_cache.get(bot_id, [])
            
            return {
                "bot_id": bot_id,
                "timestamp": datetime.now().isoformat(),
                "limits": limits.to_dict(),
                "metrics": metrics.to_dict(),
                "positions": [pos.to_dict() for pos in positions],
                "recent_events": [
                    event.to_dict() for event in self.risk_events[-10:] 
                    if event.bot_id == bot_id
                ]
            }
            
        except Exception as e:
            self.logger.error(f"Błąd podczas generowania raportu ryzyka: {e}")
            return {}
    
    async def clear_cache(self):
        """Czyszczenie cache (wywoływane codziennie o północy)"""
        try:
            with self._lock:
                self.metrics_cache.clear()
                self.risk_events.clear()
            
            self.logger.info("Cache Risk Manager został wyczyszczony")
            
        except Exception as e:
            self.logger.error(f"Błąd podczas czyszczenia cache: {e}")
    
    # === METODY BAZY DANYCH ===
    
    async def load_limits_from_db(self, bot_id: int) -> RiskLimits:
        """Ładowanie limitów ryzyka z bazy danych"""
        try:
            if not self.db_manager:
                fallback = self._get_static_limit(bot_id)
                if fallback:
                    return fallback
                self.logger.warning("Brak db_manager - używam domyślnych limitów")
                return self.default_limits

            conn = await self.db_manager.get_connection()
            if conn is None:
                self.logger.warning("Brak połączenia z bazą danych - używam domyślnych limitów")
                return self.default_limits

            query = (
                "SELECT max_daily_loss_percent, max_daily_profit_percent, max_drawdown_percent, "
                "max_position_size_percent, stop_loss_percent, take_profit_percent, "
                "max_correlation, var_confidence_level "
                "FROM risk_limits WHERE bot_id = ? ORDER BY updated_at DESC LIMIT 1"
            )

            async with conn.execute(query, (bot_id,)) as cursor:
                row = await cursor.fetchone()

            if row:
                limits = self._map_row_to_limits(row)
                with self._lock:
                    self.limits_cache[bot_id] = limits
                self.logger.info("Załadowano limity z bazy danych dla bota %s", bot_id)
                return limits

            fallback = self._get_static_limit(bot_id)
            if fallback:
                self.logger.info("Brak limitów w bazie dla bota %s - używam statycznych", bot_id)
                return fallback

            self.logger.info("Brak limitów w bazie dla bota %s - używam domyślnych", bot_id)
            with self._lock:
                self.limits_cache[bot_id] = self.default_limits
            return self.default_limits

        except Exception as e:
            self.logger.exception("Błąd podczas ładowania limitów z bazy danych: %s", e)
            return self.default_limits
    
    async def reload_limits(self, bot_id: int):
        """Przeładowanie limitów dla konkretnego bota"""
        try:
            self.logger.info("Przeładowuję limity dla bota %s", bot_id)

            with self._lock:
                self.limits_cache.pop(bot_id, None)

            limits = await self.load_limits_from_db(bot_id)

            self.logger.info("TRACE: risk.reloaded - scope=bot bot_id=%s", bot_id)

            self.event_bus.publish(
                EventTypes.RISK_RELOADED,
                {
                    'bot_id': bot_id,
                    'timestamp': datetime.now().isoformat(),
                    'action': 'reload_limits',
                    'limits': limits.to_dict()
                }
            )

        except Exception as e:
            self.logger.error("Błąd podczas przeładowania limitów dla bota %s: %s", bot_id, e)

    async def reload_all_limits(self):
        """Przeładowanie limitów dla wszystkich botów"""
        try:
            self.logger.info("Przeładowuję limity dla wszystkich botów")

            bot_ids = await self._get_known_bot_ids()

            with self._lock:
                self.limits_cache.clear()

            for bot_id in bot_ids:
                await self.load_limits_from_db(bot_id)

            self.logger.info("TRACE: risk.reloaded - scope=all count=%s", len(bot_ids))

            self.event_bus.publish(
                EventTypes.RISK_RELOADED,
                {
                    'bot_ids': bot_ids,
                    'count': len(bot_ids),
                    'timestamp': datetime.now().isoformat(),
                    'action': 'reload_all_limits'
                }
            )

        except Exception as e:
            self.logger.error("Błąd podczas przeładowania wszystkich limitów: %s", e)

    def _on_config_updated(self, event_data: dict):
        """Callback na zmianę konfiguracji"""
        try:
            logger.info(f"TRACE: config.updated received in RiskManager: {event_data}")

            if not event_data:
                return

            if isinstance(event_data, dict):
                namespace = event_data.get('namespace')
                path = str(event_data.get('path', '')).lower()
                meta = event_data.get('meta') or {}
                bot_id = meta.get('bot_id')

                if namespace == 'risk' or 'risk' in path:
                    if bot_id is not None:
                        try:
                            bot_identifier = int(bot_id)
                        except (TypeError, ValueError):
                            bot_identifier = None
                        if bot_identifier is not None:
                            self._schedule_reload_limits(bot_identifier)
                            return
                    self._schedule_reload_limits()
                    return

                if 'new_config' in event_data or 'old_config' in event_data:
                    if self._risk_section_changed(event_data.get('old_config'), event_data.get('new_config')):
                        self._schedule_reload_limits()
                        return

            text = str(event_data).lower()
            if 'risk' in text or 'limit' in text:
                self._schedule_reload_limits()

        except Exception as e:
            self.logger.error(f"Błąd w _on_config_updated: {e}")

    def _map_row_to_limits(self, row: Any) -> RiskLimits:
        def _get_value(key: str, default: Any) -> Any:
            try:
                value = row[key]
            except (KeyError, IndexError, TypeError):
                return default
            return default if value is None else value

        return RiskLimits(
            daily_loss_limit=float(_get_value('max_daily_loss_percent', self.default_limits.daily_loss_limit)),
            daily_profit_limit=float(_get_value('max_daily_profit_percent', self.default_limits.daily_profit_limit)),
            max_drawdown_limit=float(_get_value('max_drawdown_percent', self.default_limits.max_drawdown_limit)),
            position_size_limit=float(_get_value('max_position_size_percent', self.default_limits.position_size_limit)),
            max_open_positions=int(_get_value('max_open_positions', self.default_limits.max_open_positions)),
            max_correlation=float(_get_value('max_correlation', self.default_limits.max_correlation)),
            volatility_threshold=float(_get_value('volatility_threshold', self.default_limits.volatility_threshold)),
            var_limit=float(_get_value('var_confidence_level', self.default_limits.var_limit))
        )

    async def _get_known_bot_ids(self) -> List[int]:
        bot_ids: List[int] = []
        if not self.db_manager:
            return list(self.limits_cache.keys())

        try:
            conn = await self.db_manager.get_connection()
            if conn is None:
                return list(self.limits_cache.keys())

            async with conn.execute(
                "SELECT DISTINCT bot_id FROM risk_limits WHERE bot_id IS NOT NULL"
            ) as cursor:
                rows = await cursor.fetchall()
                bot_ids.extend(int(row[0]) for row in rows if row and row[0] is not None)

            if not bot_ids:
                async with conn.execute("SELECT id FROM bots") as cursor:
                    rows = await cursor.fetchall()
                    bot_ids.extend(int(row[0]) for row in rows if row and row[0] is not None)

        except Exception as exc:
            self.logger.error("Błąd podczas pobierania identyfikatorów botów: %s", exc)

        if not bot_ids:
            bot_ids.extend(self.limits_cache.keys())

        unique_ids: List[int] = []
        seen: set[int] = set()
        for bot_id in bot_ids:
            if bot_id not in seen:
                seen.add(bot_id)
                unique_ids.append(bot_id)
        return unique_ids

    def _schedule_reload_limits(self, bot_id: Optional[int] = None) -> None:
        if bot_id is None:
            self._schedule_coro(lambda: self.reload_all_limits())
        else:
            self._schedule_coro(lambda: self.reload_limits(bot_id))

    def _schedule_coro(self, coro_factory: Callable[[], Coroutine[Any, Any, Any]]) -> None:
        try:
            loop = asyncio.get_running_loop()
            loop.create_task(coro_factory())
        except RuntimeError:
            thread = threading.Thread(
                target=self._run_coro_threadsafe,
                args=(coro_factory,),
                daemon=True
            )
            thread.start()

    def _run_coro_threadsafe(self, coro_factory: Callable[[], Coroutine[Any, Any, Any]]) -> None:
        try:
            asyncio.run(coro_factory())
        except Exception as exc:
            self.logger.error("Błąd podczas uruchamiania zadania async: %s", exc)

    def _risk_section_changed(self, old_config: Optional[Dict[str, Any]], new_config: Optional[Dict[str, Any]]) -> bool:
        return self._extract_risk_section(old_config) != self._extract_risk_section(new_config)

    def _extract_risk_section(self, config: Optional[Dict[str, Any]]) -> Dict[str, Any]:
        if not isinstance(config, dict):
            return {}

        trading = config.get('trading')
        if isinstance(trading, dict):
            risk_section = trading.get('risk_management') or trading.get('risk')
            if isinstance(risk_section, dict):
                return risk_section

        risk_root = config.get('risk_management')
        if isinstance(risk_root, dict):
            return risk_root

        return {}

    def _publish_risk_event(
        self,
        bot_id: int,
        event_type: RiskEventType,
        level: RiskLevel,
        message: str,
        extra: Optional[Dict[str, Any]] = None,
    ) -> None:
        try:
            payload = {
                'bot_id': bot_id,
                'event_type': event_type.value,
                'level': level.value,
                'message': message,
                'timestamp': datetime.utcnow().isoformat(),
            }
            if extra:
                payload.update(extra)
            self.event_bus.publish(EventTypes.RISK_ALERT, payload)
            if level in {RiskLevel.HIGH, RiskLevel.CRITICAL}:
                self.event_bus.publish(EventTypes.RISK_ESCALATION, payload)
        except Exception as exc:  # pragma: no cover - defensive logging
            self.logger.error("Błąd podczas publikacji zdarzenia ryzyka: %s", exc)

    def _load_static_limits(self) -> Dict[int, RiskLimits]:
        path = Path("config/risk_limits.json")
        if not path.exists():
            return {}
        try:
            with path.open("r", encoding="utf-8") as handle:
                payload = json.load(handle)
        except Exception as exc:
            self.logger.error("Nie można odczytać pliku limitów ryzyka %s: %s", path, exc)
            return {}

        result: Dict[int, RiskLimits] = {}
        default_cfg = payload.get('default')
        if isinstance(default_cfg, dict):
            self.default_limits = self._dict_to_limits(default_cfg)

        bots_cfg = payload.get('bots')
        if isinstance(bots_cfg, dict):
            iterator = bots_cfg.items()
        else:
            iterator = ((entry.get('bot_id'), entry) for entry in (bots_cfg or []))

        for bot_identifier, cfg in iterator:
            if bot_identifier is None or not isinstance(cfg, dict):
                continue
            try:
                bot_id = int(bot_identifier)
            except (TypeError, ValueError):
                continue
            result[bot_id] = self._dict_to_limits(cfg)
        return result

    def _dict_to_limits(self, cfg: Dict[str, Any]) -> RiskLimits:
        return RiskLimits(
            daily_loss_limit=float(cfg.get('daily_loss_limit', self.default_limits.daily_loss_limit)),
            daily_profit_limit=float(cfg.get('daily_profit_limit', self.default_limits.daily_profit_limit)),
            max_drawdown_limit=float(cfg.get('max_drawdown_limit', self.default_limits.max_drawdown_limit)),
            position_size_limit=float(cfg.get('position_size_limit', self.default_limits.position_size_limit)),
            max_open_positions=int(cfg.get('max_open_positions', self.default_limits.max_open_positions)),
            max_correlation=float(cfg.get('max_correlation', self.default_limits.max_correlation)),
            volatility_threshold=float(cfg.get('volatility_threshold', self.default_limits.volatility_threshold)),
            var_limit=float(cfg.get('var_limit', self.default_limits.var_limit)),
        )

    def _get_static_limit(self, bot_id: int) -> Optional[RiskLimits]:
        limit = self.static_limits_map.get(bot_id)
        if not limit:
            return None
        with self._lock:
            self.limits_cache[bot_id] = limit
        return limit

    def _load_historical_metrics(self) -> Dict[int, RiskMetrics]:
        path = Path("analytics/historical_metrics.json")
        if not path.exists():
            return {}
        try:
            with path.open("r", encoding="utf-8") as handle:
                payload = json.load(handle)
        except Exception as exc:
            self.logger.error("Nie można odczytać pliku metryk historycznych %s: %s", path, exc)
            return {}

        result: Dict[int, RiskMetrics] = {}
        records = payload.get('bots') if isinstance(payload, dict) else payload
        if isinstance(records, dict):
            iterator = records.items()
        else:
            iterator = ((entry.get('bot_id'), entry) for entry in (records or []))

        for bot_identifier, data in iterator:
            if bot_identifier is None or not isinstance(data, dict):
                continue
            try:
                bot_id = int(bot_identifier)
            except (TypeError, ValueError):
                continue
            result[bot_id] = RiskMetrics(
                daily_pnl=float(data.get('daily_pnl', 0.0)),
                daily_loss=float(data.get('daily_loss', 0.0)),
                daily_profit=float(data.get('daily_profit', 0.0)),
                max_drawdown=float(data.get('max_drawdown', 0.0)),
                current_drawdown=float(data.get('current_drawdown', 0.0)),
                win_rate=float(data.get('win_rate', 0.0)),
                profit_factor=float(data.get('profit_factor', 0.0)),
                sharpe_ratio=float(data.get('sharpe_ratio', 0.0)),
                var_95=float(data.get('var_95', 0.0)),
                exposure=float(data.get('exposure', 0.0)),
                correlation_risk=float(data.get('correlation_risk', 0.0)),
            )
        return result

    def _get_static_metrics(self, bot_id: int) -> Optional[RiskMetrics]:
        metrics = self.historical_metrics.get(bot_id)
        if metrics:
            return metrics
        return None

    async def validate_order(self, order_request: Any, bot_id: int) -> bool:
        try:
            limits = await self.get_risk_limits(bot_id)
            quantity = float(getattr(order_request, 'quantity', 0.0))
            price = getattr(order_request, 'price', None)
            if price is None and hasattr(order_request, 'metadata'):
                metadata = getattr(order_request, 'metadata') or {}
                price = metadata.get('reference_price')
            price = float(price or 0.0)
            notional = quantity * price if price > 0 else quantity

            if limits.max_open_positions and len(self.positions_cache.get(bot_id, [])) >= limits.max_open_positions:
                await self._log_risk_event(
                    bot_id,
                    RiskEventType.POSITION_SIZE_LIMIT,
                    RiskLevel.HIGH,
                    f"Max open positions reached for bot {bot_id}",
                )
                return False

            limit_value = limits.position_size_limit
            if limit_value and limit_value > 0 and notional > float(limit_value):
                await self._log_risk_event(
                    bot_id,
                    RiskEventType.POSITION_SIZE_LIMIT,
                    RiskLevel.HIGH,
                    f"Order size {notional:.2f} exceeds limit {limit_value}",
                )
                return False

            return True
        except Exception as exc:
            self.logger.error("Błąd podczas walidacji zlecenia: %s", exc)
            return False


_risk_manager_lock = threading.RLock()
_risk_manager: Optional[RiskManager] = None


def get_risk_manager(db_manager=None):
    """Pobieranie instancji RiskManager (singleton)"""
    global _risk_manager
    
    with _risk_manager_lock:
        if _risk_manager is None:
            _risk_manager = RiskManager(db_manager)
        return _risk_manager
"""
Updated Risk Manager - Zarządzanie ryzykiem z integracją z nowym systemem
"""

import asyncio
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass
from enum import Enum

from .trading_engine import OrderRequest, OrderSide, OrderType, OrderResponse
from .portfolio_manager import AssetPosition, PortfolioSummary
from utils.helpers import get_or_create_event_loop, schedule_coro_safely

logger = logging.getLogger(__name__)

class RiskLevel(Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"

class RiskCheckResult(Enum):
    APPROVED = "approved"
    REJECTED = "rejected"
    WARNING = "warning"
    REQUIRES_CONFIRMATION = "requires_confirmation"

@dataclass
class RiskLimits:
    """Limity ryzyka"""
    max_position_size: float  # Maksymalny rozmiar pozycji (% portfela)
    max_daily_loss: float     # Maksymalna dzienna strata (% portfela)
    max_total_exposure: float # Maksymalna ekspozycja (% portfela)
    max_drawdown: float       # Maksymalny drawdown (% portfela)
    stop_loss_percent: float  # Stop loss (%)
    take_profit_percent: float # Take profit (%)
    max_trades_per_hour: int  # Maksymalna liczba transakcji na godzinę
    max_trades_per_day: int   # Maksymalna liczba transakcji dziennie
    min_balance_reserve: float # Minimalna rezerwa salda (USDT)

@dataclass
class RiskMetrics:
    """Metryki ryzyka"""
    current_exposure: float
    daily_pnl: float
    total_drawdown: float
    var_95: float  # Value at Risk 95%
    sharpe_ratio: float
    max_consecutive_losses: int
    current_risk_level: RiskLevel

@dataclass
class RiskAlert:
    """Alert ryzyka"""
    id: str
    timestamp: datetime
    level: RiskLevel
    message: str
    bot_id: Optional[str]
    symbol: Optional[str]
    action_required: bool
    resolved: bool

@dataclass
class TradeRiskAssessment:
    """Ocena ryzyka transakcji"""
    result: RiskCheckResult
    risk_score: float  # 0-100
    warnings: List[str]
    recommendations: List[str]
    max_allowed_quantity: Optional[float]

class UpdatedRiskManager:
    """Zaktualizowany Manager Ryzyka"""
    
    def __init__(self, data_manager=None):
        self.data_manager = data_manager
        
        # Domyślne limity ryzyka
        self.default_limits = RiskLimits(
            max_position_size=10.0,      # 10% portfela na pozycję
            max_daily_loss=5.0,          # 5% dzienna strata
            max_total_exposure=50.0,     # 50% całkowita ekspozycja
            max_drawdown=15.0,           # 15% maksymalny drawdown
            stop_loss_percent=3.0,       # 3% stop loss
            take_profit_percent=6.0,     # 6% take profit
            max_trades_per_hour=10,      # 10 transakcji na godzinę
            max_trades_per_day=100,      # 100 transakcji dziennie
            min_balance_reserve=100.0    # 100 USDT rezerwy
        )
        
        # Limity dla poszczególnych botów
        self.bot_limits: Dict[str, RiskLimits] = {}
        
        # Historia transakcji dla kontroli częstotliwości
        self.trade_history: List[Dict[str, Any]] = []
        
        # Aktywne alerty
        self.active_alerts: Dict[str, RiskAlert] = {}
        
        # Cache metryk ryzyka
        self.risk_metrics_cache: Optional[RiskMetrics] = None
        self.cache_timestamp: Optional[datetime] = None
        
        # Flagi bezpieczeństwa
        self.emergency_stop = False
        self.trading_paused = False
        
        # Task monitoringu
        self._monitoring_task = None
    
    async def initialize(self):
        """Inicjalizuje RiskManager"""
        try:
            logger.info("Initializing UpdatedRiskManager...")
            
            # Załaduj limity z bazy danych
            await self._load_risk_settings()
            
            # Uruchom monitoring ryzyka
            self._monitoring_task = schedule_coro_safely(lambda: self._risk_monitoring_loop())
            
            logger.info("UpdatedRiskManager initialized")
            
        except Exception as e:
            logger.error(f"Error initializing UpdatedRiskManager: {e}")
    
    async def stop_monitoring(self):
        """Zatrzymuje monitoring ryzyka"""
        try:
            logger.info("Stopping UpdatedRiskManager monitoring...")
            
            # Zatrzymaj pętlę monitoringu
            if hasattr(self, '_monitoring_task') and self._monitoring_task and not self._monitoring_task.done():
                self._monitoring_task.cancel()
                try:
                    await self._monitoring_task
                except asyncio.CancelledError:
                    pass
            
            logger.info("UpdatedRiskManager monitoring stopped")
            
        except Exception as e:
            logger.error(f"Error stopping UpdatedRiskManager monitoring: {e}")
    
    def set_data_manager(self, data_manager):
        """Ustawia data manager po inicjalizacji"""
        self.data_manager = data_manager
        logger.info("Data manager set for UpdatedRiskManager")
    
    async def validate_trade_order(self, bot_id: str, order_request: OrderRequest) -> TradeRiskAssessment:
        """Waliduje zlecenie handlowe pod kątem ryzyka"""
        try:
            warnings = []
            recommendations = []
            risk_score = 0.0
            
            # Pobierz limity dla bota
            limits = self.bot_limits.get(bot_id, self.default_limits)
            
            # Sprawdź czy data_manager jest dostępny
            if not self.data_manager:
                return TradeRiskAssessment(
                    result=RiskCheckResult.REJECTED,
                    risk_score=100.0,
                    warnings=["Data manager not available"],
                    recommendations=["Initialize data manager"],
                    max_allowed_quantity=None
                )
            
            # Pobierz dane portfela
            portfolio = await self.data_manager.get_portfolio_summary()
            if not portfolio:
                return TradeRiskAssessment(
                    result=RiskCheckResult.REJECTED,
                    risk_score=100.0,
                    warnings=["Cannot access portfolio data"],
                    recommendations=["Check data connection"],
                    max_allowed_quantity=None
                )
            
            # 1. Sprawdź stan awaryjny
            if self.emergency_stop:
                return TradeRiskAssessment(
                    result=RiskCheckResult.REJECTED,
                    risk_score=100.0,
                    warnings=["Emergency stop activated"],
                    recommendations=["Resolve emergency conditions"],
                    max_allowed_quantity=None
                )
            
            # 2. Sprawdź czy trading jest wstrzymany
            if self.trading_paused:
                return TradeRiskAssessment(
                    result=RiskCheckResult.REJECTED,
                    risk_score=80.0,
                    warnings=["Trading is paused"],
                    recommendations=["Resume trading when conditions improve"],
                    max_allowed_quantity=None
                )
            
            # 3. Sprawdź saldo i rezerwę
            balance_check = await self._check_balance_limits(order_request, limits, portfolio)
            risk_score += balance_check[0]
            warnings.extend(balance_check[1])
            recommendations.extend(balance_check[2])
            
            # 4. Sprawdź rozmiar pozycji
            position_check = await self._check_position_size(order_request, limits, portfolio)
            risk_score += position_check[0]
            warnings.extend(position_check[1])
            recommendations.extend(position_check[2])
            
            # 5. Sprawdź ekspozycję
            exposure_check = await self._check_exposure_limits(order_request, limits, portfolio)
            risk_score += exposure_check[0]
            warnings.extend(exposure_check[1])
            recommendations.extend(exposure_check[2])
            
            # 6. Sprawdź częstotliwość transakcji
            frequency_check = await self._check_trade_frequency(bot_id, limits)
            risk_score += frequency_check[0]
            warnings.extend(frequency_check[1])
            recommendations.extend(frequency_check[2])
            
            # 7. Sprawdź dzienny P&L
            pnl_check = await self._check_daily_pnl(limits, portfolio)
            risk_score += pnl_check[0]
            warnings.extend(pnl_check[1])
            recommendations.extend(pnl_check[2])
            
            # Oblicz maksymalną dozwoloną ilość
            max_quantity = await self._calculate_max_allowed_quantity(order_request, limits, portfolio)
            
            # Określ wynik na podstawie risk_score
            if risk_score >= 80:
                result = RiskCheckResult.REJECTED
            elif risk_score >= 60:
                result = RiskCheckResult.REQUIRES_CONFIRMATION
            elif risk_score >= 30:
                result = RiskCheckResult.WARNING
            else:
                result = RiskCheckResult.APPROVED
            
            # Jeśli ilość przekracza limit, zmniejsz ją
            if max_quantity and order_request.quantity > max_quantity:
                warnings.append(f"Order quantity reduced from {order_request.quantity} to {max_quantity}")
                recommendations.append("Consider splitting large orders")
            
            assessment = TradeRiskAssessment(
                result=result,
                risk_score=risk_score,
                warnings=warnings,
                recommendations=recommendations,
                max_allowed_quantity=max_quantity
            )
            
            # Loguj ocenę ryzyka
            logger.info(f"Trade risk assessment for {bot_id}: {result.value} (score: {risk_score:.1f})")
            
            return assessment
            
        except Exception as e:
            logger.error(f"Error validating trade order: {e}")
            return TradeRiskAssessment(
                result=RiskCheckResult.REJECTED,
                risk_score=100.0,
                warnings=[f"Risk validation error: {str(e)}"],
                recommendations=["Check risk management system"],
                max_allowed_quantity=None
            )
    
    async def _check_balance_limits(self, order_request: OrderRequest, limits: RiskLimits, portfolio: PortfolioSummary) -> Tuple[float, List[str], List[str]]:
        """Sprawdza limity salda"""
        risk_score = 0.0
        warnings = []
        recommendations = []
        
        try:
            # Sprawdź rezerwę salda
            if portfolio.available_balance < limits.min_balance_reserve:
                risk_score += 30.0
                warnings.append(f"Balance below minimum reserve: {portfolio.available_balance:.2f} < {limits.min_balance_reserve}")
                recommendations.append("Increase account balance")
            
            # Sprawdź czy wystarczy środków na transakcję
            if order_request.side == OrderSide.BUY:
                required_balance = order_request.quantity * (order_request.price or 0)
                if required_balance > portfolio.available_balance * 0.9:  # 90% salda
                    risk_score += 25.0
                    warnings.append("Order requires significant portion of balance")
                    recommendations.append("Consider smaller position size")
            
        except Exception as e:
            logger.error(f"Error checking balance limits: {e}")
            risk_score += 20.0
            warnings.append("Error checking balance limits")
        
        return risk_score, warnings, recommendations
    
    async def _check_position_size(self, order_request: OrderRequest, limits: RiskLimits, portfolio: PortfolioSummary) -> Tuple[float, List[str], List[str]]:
        """Sprawdza rozmiar pozycji"""
        risk_score = 0.0
        warnings = []
        recommendations = []
        
        try:
            # Sprawdź czy data_manager jest dostępny
            if not self.data_manager:
                warnings.append("Data manager not available for position check")
                return 20.0, warnings, recommendations
            
            # Pobierz aktualną pozycję
            positions = await self.data_manager.get_portfolio_positions()
            current_position = 0.0
            
            for position in positions:
                if position.symbol == order_request.symbol:
                    current_position = position.amount
                    break
            
            # Oblicz nową pozycję
            if order_request.side == OrderSide.BUY:
                new_position = current_position + order_request.quantity
            else:
                new_position = current_position - order_request.quantity
            
            # Oblicz wartość pozycji jako % portfela
            position_value = abs(new_position) * (order_request.price or 0)
            position_percent = (position_value / portfolio.total_value) * 100
            
            if position_percent > limits.max_position_size:
                risk_score += 40.0
                warnings.append(f"Position size exceeds limit: {position_percent:.1f}% > {limits.max_position_size}%")
                recommendations.append("Reduce position size")
            elif position_percent > limits.max_position_size * 0.8:
                risk_score += 20.0
                warnings.append(f"Position size approaching limit: {position_percent:.1f}%")
                recommendations.append("Monitor position size")
            
        except Exception as e:
            logger.error(f"Error checking position size: {e}")
            risk_score += 15.0
            warnings.append("Error checking position size")
        
        return risk_score, warnings, recommendations
    
    async def _check_exposure_limits(self, order_request: OrderRequest, limits: RiskLimits, portfolio: PortfolioSummary) -> Tuple[float, List[str], List[str]]:
        """Sprawdza limity ekspozycji"""
        risk_score = 0.0
        warnings = []
        recommendations = []
        
        try:
            # Sprawdź czy data_manager jest dostępny
            if not self.data_manager:
                warnings.append("Data manager not available for exposure check")
                return 20.0, warnings, recommendations
            
            # Oblicz całkowitą ekspozycję
            total_exposure = 0.0
            positions = await self.data_manager.get_portfolio_positions()
            
            for position in positions:
                if position.current_price:
                    exposure = abs(position.amount) * position.current_price
                    total_exposure += exposure
            
            # Dodaj nową ekspozycję
            if order_request.price:
                new_exposure = order_request.quantity * order_request.price
                total_exposure += new_exposure
            
            exposure_percent = (total_exposure / portfolio.total_value) * 100
            
            if exposure_percent > limits.max_total_exposure:
                risk_score += 35.0
                warnings.append(f"Total exposure exceeds limit: {exposure_percent:.1f}% > {limits.max_total_exposure}%")
                recommendations.append("Reduce overall exposure")
            elif exposure_percent > limits.max_total_exposure * 0.8:
                risk_score += 15.0
                warnings.append(f"Total exposure approaching limit: {exposure_percent:.1f}%")
        
        except Exception as e:
            logger.error(f"Error checking exposure limits: {e}")
            risk_score += 10.0
            warnings.append("Error checking exposure limits")
        
        return risk_score, warnings, recommendations
    
    async def _check_trade_frequency(self, bot_id: str, limits: RiskLimits) -> Tuple[float, List[str], List[str]]:
        """Sprawdza częstotliwość transakcji"""
        risk_score = 0.0
        warnings = []
        recommendations = []
        
        try:
            now = datetime.now()
            hour_ago = now - timedelta(hours=1)
            day_ago = now - timedelta(days=1)
            
            # Filtruj transakcje dla tego bota
            bot_trades = [t for t in self.trade_history if t.get('bot_id') == bot_id]
            
            # Sprawdź transakcje w ostatniej godzinie
            hourly_trades = [t for t in bot_trades if t.get('timestamp', datetime.min) > hour_ago]
            if len(hourly_trades) >= limits.max_trades_per_hour:
                risk_score += 30.0
                warnings.append(f"Hourly trade limit reached: {len(hourly_trades)}/{limits.max_trades_per_hour}")
                recommendations.append("Reduce trading frequency")
            
            # Sprawdź transakcje w ostatnim dniu
            daily_trades = [t for t in bot_trades if t.get('timestamp', datetime.min) > day_ago]
            if len(daily_trades) >= limits.max_trades_per_day:
                risk_score += 25.0
                warnings.append(f"Daily trade limit reached: {len(daily_trades)}/{limits.max_trades_per_day}")
                recommendations.append("Pause trading until tomorrow")
        
        except Exception as e:
            logger.error(f"Error checking trade frequency: {e}")
            risk_score += 10.0
            warnings.append("Error checking trade frequency")
        
        return risk_score, warnings, recommendations
    
    async def _check_daily_pnl(self, limits: RiskLimits, portfolio: PortfolioSummary) -> Tuple[float, List[str], List[str]]:
        """Sprawdza dzienny P&L"""
        risk_score = 0.0
        warnings = []
        recommendations = []
        
        try:
            daily_pnl_percent = portfolio.daily_change_percent
            
            if daily_pnl_percent < -limits.max_daily_loss:
                risk_score += 50.0
                warnings.append(f"Daily loss limit exceeded: {daily_pnl_percent:.1f}% < -{limits.max_daily_loss}%")
                recommendations.append("Stop trading for today")
                
                # Aktywuj wstrzymanie tradingu
                self.trading_paused = True
                await self._create_risk_alert(
                    level=RiskLevel.CRITICAL,
                    message=f"Daily loss limit exceeded: {daily_pnl_percent:.1f}%",
                    action_required=True
                )
            elif daily_pnl_percent < -limits.max_daily_loss * 0.7:
                risk_score += 25.0
                warnings.append(f"Approaching daily loss limit: {daily_pnl_percent:.1f}%")
                recommendations.append("Consider reducing position sizes")
        
        except Exception as e:
            logger.error(f"Error checking daily P&L: {e}")
            risk_score += 10.0
            warnings.append("Error checking daily P&L")
        
        return risk_score, warnings, recommendations
    
    async def _calculate_max_allowed_quantity(self, order_request: OrderRequest, limits: RiskLimits, portfolio: PortfolioSummary) -> Optional[float]:
        """Oblicza maksymalną dozwoloną ilość"""
        try:
            if not order_request.price:
                return order_request.quantity
            
            # Oblicz maksymalną wartość pozycji
            max_position_value = portfolio.total_value * (limits.max_position_size / 100)
            
            # Oblicz maksymalną ilość
            max_quantity = max_position_value / order_request.price
            
            # Uwzględnij rezerwę
            if order_request.side == OrderSide.BUY:
                available_balance = portfolio.available_balance - limits.min_balance_reserve
                max_quantity_by_balance = available_balance / order_request.price
                max_quantity = min(max_quantity, max_quantity_by_balance)
            
            return min(max_quantity, order_request.quantity)
            
        except Exception as e:
            logger.error(f"Error calculating max allowed quantity: {e}")
            return order_request.quantity
    
    async def record_trade_execution(self, bot_id: str, order_request: OrderRequest, order_response: OrderResponse):
        """Rejestruje wykonaną transakcję"""
        try:
            trade_record = {
                'bot_id': bot_id,
                'timestamp': datetime.now(),
                'symbol': order_request.symbol,
                'side': order_request.side.value,
                'quantity': order_request.quantity,
                'price': order_response.average_price or order_request.price,
                'status': order_response.status.value
            }
            
            self.trade_history.append(trade_record)
            
            # Ogranicz historię do ostatnich 1000 transakcji
            if len(self.trade_history) > 1000:
                self.trade_history = self.trade_history[-1000:]
            
            logger.debug(f"Trade recorded: {bot_id} {order_request.side.value} {order_request.quantity} {order_request.symbol}")
            
        except Exception as e:
            logger.error(f"Error recording trade execution: {e}")
    
    async def get_risk_metrics(self) -> RiskMetrics:
        """Pobiera aktualne metryki ryzyka"""
        try:
            # Sprawdź cache
            if (self.risk_metrics_cache and self.cache_timestamp and 
                datetime.now() - self.cache_timestamp < timedelta(minutes=5)):
                return self.risk_metrics_cache
            
            # Sprawdź czy data_manager jest dostępny
            if not self.data_manager:
                logger.warning("Data manager not available for risk metrics")
                return RiskMetrics(
                    current_exposure=0.0,
                    daily_pnl=0.0,
                    total_drawdown=0.0,
                    var_95=0.0,
                    sharpe_ratio=0.0,
                    max_consecutive_losses=0,
                    current_risk_level=RiskLevel.LOW
                )
            
            # Oblicz metryki
            portfolio = await self.data_manager.get_portfolio_summary()
            if not portfolio:
                return RiskMetrics(
                    current_exposure=0.0,
                    daily_pnl=0.0,
                    total_drawdown=0.0,
                    var_95=0.0,
                    sharpe_ratio=0.0,
                    max_consecutive_losses=0,
                    current_risk_level=RiskLevel.LOW
                )
            
            # Oblicz ekspozycję
            positions = await self.data_manager.get_portfolio_positions()
            total_exposure = sum(abs(p.amount) * (p.current_price or 0) for p in positions)
            exposure_percent = (total_exposure / portfolio.total_value) * 100 if portfolio.total_value > 0 else 0
            
            # Określ poziom ryzyka
            risk_level = RiskLevel.LOW
            if exposure_percent > 70:
                risk_level = RiskLevel.CRITICAL
            elif exposure_percent > 50:
                risk_level = RiskLevel.HIGH
            elif exposure_percent > 30:
                risk_level = RiskLevel.MEDIUM
            
            metrics = RiskMetrics(
                current_exposure=exposure_percent,
                daily_pnl=portfolio.daily_change_percent,
                total_drawdown=abs(min(0, portfolio.daily_change_percent)),
                var_95=0.0,  # Uproszczone - wymagałoby historycznych danych
                sharpe_ratio=0.0,  # Uproszczone - wymagałoby historycznych danych
                max_consecutive_losses=0,  # Uproszczone - wymagałoby analizy historii
                current_risk_level=risk_level
            )
            
            # Zapisz w cache
            self.risk_metrics_cache = metrics
            self.cache_timestamp = datetime.now()
            
            return metrics
            
        except Exception as e:
            logger.error(f"Error getting risk metrics: {e}")
            return RiskMetrics(
                current_exposure=0.0,
                daily_pnl=0.0,
                total_drawdown=0.0,
                var_95=0.0,
                sharpe_ratio=0.0,
                max_consecutive_losses=0,
                current_risk_level=RiskLevel.LOW
            )
    
    async def _create_risk_alert(self, level: RiskLevel, message: str, bot_id: str = None, symbol: str = None, action_required: bool = False):
        """Tworzy alert ryzyka"""
        try:
            alert_id = f"alert_{int(datetime.now().timestamp())}"
            alert = RiskAlert(
                id=alert_id,
                timestamp=datetime.now(),
                level=level,
                message=message,
                bot_id=bot_id,
                symbol=symbol,
                action_required=action_required,
                resolved=False
            )
            
            self.active_alerts[alert_id] = alert
            
            logger.warning(f"Risk alert created: {level.value} - {message}")
            
        except Exception as e:
            logger.error(f"Error creating risk alert: {e}")
    
    async def _risk_monitoring_loop(self):
        """Główna pętla monitoringu ryzyka"""
        while True:
            try:
                # Sprawdź metryki ryzyka
                metrics = await self.get_risk_metrics()
                
                # Sprawdź czy nie przekroczono limitów
                if metrics.current_risk_level == RiskLevel.CRITICAL:
                    if not self.trading_paused:
                        self.trading_paused = True
                        await self._create_risk_alert(
                            level=RiskLevel.CRITICAL,
                            message="Critical risk level reached - trading paused",
                            action_required=True
                        )
                
                # Sprawdź czy można wznowić trading
                elif metrics.current_risk_level in [RiskLevel.LOW, RiskLevel.MEDIUM] and self.trading_paused:
                    self.trading_paused = False
                    logger.info("Risk level improved - trading resumed")
                
                await asyncio.sleep(30)  # Sprawdzaj co 30 sekund
                
            except Exception as e:
                logger.error(f"Error in risk monitoring loop: {e}")
                await asyncio.sleep(60)
    
    async def _load_risk_settings(self):
        """Ładuje ustawienia ryzyka z bazy danych"""
        try:
            # Tutaj będzie implementacja ładowania z bazy
            logger.info("Risk settings loaded")
            
        except Exception as e:
            logger.error(f"Error loading risk settings: {e}")
    
    async def set_bot_risk_limits(self, bot_id: str, limits: RiskLimits):
        """Ustawia limity ryzyka dla konkretnego bota"""
        self.bot_limits[bot_id] = limits
        logger.info(f"Risk limits set for bot {bot_id}")
    
    async def get_active_alerts(self) -> List[RiskAlert]:
        """Pobiera aktywne alerty"""
        return [alert for alert in self.active_alerts.values() if not alert.resolved]
    
    async def resolve_alert(self, alert_id: str):
        """Rozwiązuje alert"""
        if alert_id in self.active_alerts:
            self.active_alerts[alert_id].resolved = True
            logger.info(f"Alert {alert_id} resolved")
    
    async def emergency_stop_all(self):
        """Awaryjne zatrzymanie wszystkich operacji"""
        self.emergency_stop = True
        self.trading_paused = True
        
        await self._create_risk_alert(
            level=RiskLevel.CRITICAL,
            message="Emergency stop activated",
            action_required=True
        )
        
        logger.critical("EMERGENCY STOP ACTIVATED")
    
    async def resume_operations(self):
        """Wznawia operacje po awaryjnym zatrzymaniu"""
        self.emergency_stop = False
        self.trading_paused = False
        
        logger.info("Operations resumed after emergency stop")

# Singleton instance
_updated_risk_manager = None

def get_updated_risk_manager(data_manager=None) -> UpdatedRiskManager:
    """Zwraca singleton instance UpdatedRiskManager"""
    global _updated_risk_manager
    if _updated_risk_manager is None:
        _updated_risk_manager = UpdatedRiskManager(data_manager)
    elif data_manager is not None and _updated_risk_manager.data_manager is None:
        # Aktualizuj data_manager jeśli nie był wcześniej ustawiony
        _updated_risk_manager.data_manager = data_manager
    return _updated_risk_manager
"""
Updated Portfolio Manager - Rozszerzona wersja managera portfela

Ulepszona wersja PortfolioManager z dodatkowymi funkcjami,
lepszą integracją z systemem i zaawansowanymi obliczeniami.
"""

import asyncio
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Tuple, Union
from dataclasses import dataclass, asdict
from decimal import Decimal
from enum import Enum

from .portfolio_manager import PortfolioManager, AssetPosition, PortfolioSummary
from .data_manager import DataManager, PortfolioData
from utils.logger import get_logger, LogType
from utils.event_bus import get_event_bus, EventTypes
from utils.config_manager import get_config_manager

logger = get_logger("updated_portfolio_manager", LogType.SYSTEM)

class PositionType(Enum):
    """Typ pozycji"""
    LONG = "long"
    SHORT = "short"
    NEUTRAL = "neutral"

class RiskLevel(Enum):
    """Poziom ryzyka"""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    EXTREME = "extreme"

@dataclass
class EnhancedAssetPosition(AssetPosition):
    """Rozszerzona pozycja w aktywie"""
    position_type: PositionType = PositionType.LONG
    risk_level: RiskLevel = RiskLevel.MEDIUM
    stop_loss: Optional[float] = None
    take_profit: Optional[float] = None
    entry_date: Optional[datetime] = None
    holding_period: Optional[timedelta] = None
    volatility: float = 0.0
    beta: float = 1.0
    sharpe_ratio: float = 0.0
    max_drawdown: float = 0.0
    
    def __post_init__(self):
        """Oblicza dodatkowe metryki po inicjalizacji"""
        if self.entry_date:
            self.holding_period = datetime.now() - self.entry_date

@dataclass
class EnhancedPortfolioSummary(PortfolioSummary):
    """Rozszerzone podsumowanie portfela"""
    weekly_change: float = 0.0
    weekly_change_percent: float = 0.0
    monthly_change: float = 0.0
    monthly_change_percent: float = 0.0
    yearly_change: float = 0.0
    yearly_change_percent: float = 0.0
    sharpe_ratio: float = 0.0
    sortino_ratio: float = 0.0
    max_drawdown: float = 0.0
    volatility: float = 0.0
    beta: float = 1.0
    alpha: float = 0.0
    var_95: float = 0.0  # Value at Risk 95%
    cvar_95: float = 0.0  # Conditional Value at Risk 95%
    total_fees_paid: float = 0.0
    total_trades: int = 0
    winning_trades: int = 0
    losing_trades: int = 0
    win_rate: float = 0.0
    avg_win: float = 0.0
    avg_loss: float = 0.0
    profit_factor: float = 0.0
    recovery_factor: float = 0.0
    calmar_ratio: float = 0.0

class UpdatedPortfolioManager(PortfolioManager):
    """
    Rozszerzona wersja PortfolioManager
    
    Dodaje zaawansowane funkcje analizy portfela, zarządzania ryzykiem,
    obliczania metryk wydajności i integracji z systemem zdarzeń.
    """
    
    def __init__(self, data_manager: Optional[DataManager] = None):
        """
        Inicjalizuje UpdatedPortfolioManager
        
        Args:
            data_manager: Manager danych (opcjonalny)
        """
        # Jeśli nie podano data_manager, użyj domyślnego
        if data_manager is None:
            from .data_manager import get_data_manager
            data_manager = get_data_manager()
        
        super().__init__(data_manager)
        
        self.config_manager = get_config_manager()
        self.event_bus = get_event_bus()
        
        # Rozszerzone dane
        self.enhanced_positions: Dict[str, EnhancedAssetPosition] = {}
        self.historical_values: List[Dict[str, Any]] = []
        self.performance_metrics: Dict[str, float] = {}
        self.risk_metrics: Dict[str, float] = {}
        
        # Ustawienia
        self.settings = {
            'auto_calculate_metrics': True,
            'risk_free_rate': 0.02,  # 2% roczna stopa wolna od ryzyka
            'benchmark_return': 0.08,  # 8% roczny zwrot benchmarku
            'max_position_size': 0.1,  # Maksymalnie 10% portfela w jednej pozycji
            'rebalance_threshold': 0.05,  # 5% próg rebalansowania
            'stop_loss_default': 0.05,  # 5% domyślny stop loss
            'take_profit_default': 0.15,  # 15% domyślny take profit
        }
        
        # Cache dla obliczeń
        self.metrics_cache: Dict[str, Any] = {}
        self.metrics_cache_duration = timedelta(minutes=5)
        self.last_metrics_update: Optional[datetime] = None
        
        # Subskrypcje na zdarzenia
        self._setup_event_subscriptions()
        
        logger.info("UpdatedPortfolioManager initialized successfully")
    
    def _setup_event_subscriptions(self):
        """Konfiguruje subskrypcje na zdarzenia systemowe"""
        try:
            self.event_bus.subscribe(EventTypes.CONFIG_UPDATED, self._on_config_updated)
            self.event_bus.subscribe(EventTypes.DATA_UPDATED, self._on_data_updated)
            self.event_bus.subscribe(EventTypes.ORDER_SUBMITTED, self._on_order_submitted)
            
            logger.debug("Event subscriptions configured")
        except Exception as e:
            logger.error(f"Error setting up event subscriptions: {e}")
    
    async def get_enhanced_portfolio_summary(self) -> EnhancedPortfolioSummary:
        """
        Pobiera rozszerzone podsumowanie portfela
        
        Returns:
            Rozszerzone podsumowanie portfela z dodatkowymi metrykami
        """
        try:
            # Pobierz podstawowe podsumowanie
            basic_summary = await self.get_portfolio_summary()
            
            # Oblicz dodatkowe metryki
            enhanced_metrics = await self._calculate_enhanced_metrics()
            
            # Utwórz rozszerzone podsumowanie
            enhanced_summary = EnhancedPortfolioSummary(
                total_value=basic_summary.total_value,
                available_balance=basic_summary.available_balance,
                invested_amount=basic_summary.invested_amount,
                total_profit_loss=basic_summary.total_profit_loss,
                total_profit_loss_percent=basic_summary.total_profit_loss_percent,
                daily_change=basic_summary.daily_change,
                daily_change_percent=basic_summary.daily_change_percent,
                positions=basic_summary.positions,
                last_updated=basic_summary.last_updated,
                **enhanced_metrics
            )
            
            return enhanced_summary
            
        except Exception as e:
            logger.error(f"Error getting enhanced portfolio summary: {e}")
            # Fallback do podstawowego podsumowania
            basic_summary = await self.get_portfolio_summary()
            return EnhancedPortfolioSummary(
                total_value=basic_summary.total_value,
                available_balance=basic_summary.available_balance,
                invested_amount=basic_summary.invested_amount,
                total_profit_loss=basic_summary.total_profit_loss,
                total_profit_loss_percent=basic_summary.total_profit_loss_percent,
                daily_change=basic_summary.daily_change,
                daily_change_percent=basic_summary.daily_change_percent,
                positions=basic_summary.positions,
                last_updated=basic_summary.last_updated
            )
    
    async def _calculate_enhanced_metrics(self) -> Dict[str, Any]:
        """Oblicza rozszerzone metryki portfela"""
        try:
            # Sprawdź cache
            if self._is_metrics_cache_valid():
                return self.metrics_cache
            
            metrics = {}
            
            # Pobierz dane historyczne
            historical_data = await self._get_historical_portfolio_data()
            
            if len(historical_data) < 2:
                # Nie ma wystarczających danych historycznych
                return self._get_default_metrics()
            
            # Oblicz zwroty
            returns = self._calculate_returns(historical_data)
            
            # Oblicz podstawowe metryki czasowe
            metrics.update(self._calculate_time_based_metrics(historical_data))
            
            # Oblicz metryki ryzyka i wydajności
            metrics.update(self._calculate_risk_metrics(returns))
            
            # Oblicz metryki tradingowe
            metrics.update(await self._calculate_trading_metrics())
            
            # Zapisz w cache
            self.metrics_cache = metrics
            self.last_metrics_update = datetime.now()
            
            return metrics
            
        except Exception as e:
            logger.error(f"Error calculating enhanced metrics: {e}")
            return self._get_default_metrics()
    
    def _is_metrics_cache_valid(self) -> bool:
        """Sprawdza czy cache metryk jest aktualny"""
        if not self.last_metrics_update:
            return False
        return datetime.now() - self.last_metrics_update < self.metrics_cache_duration
    
    def _get_default_metrics(self) -> Dict[str, Any]:
        """Zwraca domyślne metryki gdy brak danych"""
        return {
            'weekly_change': 0.0,
            'weekly_change_percent': 0.0,
            'monthly_change': 0.0,
            'monthly_change_percent': 0.0,
            'yearly_change': 0.0,
            'yearly_change_percent': 0.0,
            'sharpe_ratio': 0.0,
            'sortino_ratio': 0.0,
            'max_drawdown': 0.0,
            'volatility': 0.0,
            'beta': 1.0,
            'alpha': 0.0,
            'var_95': 0.0,
            'cvar_95': 0.0,
            'total_fees_paid': 0.0,
            'total_trades': 0,
            'winning_trades': 0,
            'losing_trades': 0,
            'win_rate': 0.0,
            'avg_win': 0.0,
            'avg_loss': 0.0,
            'profit_factor': 0.0,
            'recovery_factor': 0.0,
            'calmar_ratio': 0.0
        }
    
    async def _get_historical_portfolio_data(self) -> List[Dict[str, Any]]:
        """Pobiera dane historyczne portfela"""
        try:
            # Symulacja danych historycznych
            now = datetime.now()
            historical_data = []
            
            for i in range(30):  # Ostatnie 30 dni
                date = now - timedelta(days=i)
                value = 10000 + (i * 100) + (i % 7 * 50)  # Symulacja wzrostu z wahaniami
                historical_data.append({
                    'date': date,
                    'value': value,
                    'change': 50 if i % 3 == 0 else -25
                })
            
            return list(reversed(historical_data))
            
        except Exception as e:
            logger.error(f"Error getting historical portfolio data: {e}")
            return []
    
    def _calculate_returns(self, historical_data: List[Dict[str, Any]]) -> List[float]:
        """Oblicza zwroty z danych historycznych"""
        if len(historical_data) < 2:
            return []
        
        returns = []
        for i in range(1, len(historical_data)):
            prev_value = historical_data[i-1]['value']
            curr_value = historical_data[i]['value']
            if prev_value > 0:
                return_rate = (curr_value - prev_value) / prev_value
                returns.append(return_rate)
        
        return returns
    
    def _calculate_time_based_metrics(self, historical_data: List[Dict[str, Any]]) -> Dict[str, float]:
        """Oblicza metryki czasowe (tygodniowe, miesięczne, roczne)"""
        if len(historical_data) < 2:
            return {
                'weekly_change': 0.0,
                'weekly_change_percent': 0.0,
                'monthly_change': 0.0,
                'monthly_change_percent': 0.0,
                'yearly_change': 0.0,
                'yearly_change_percent': 0.0
            }
        
        current_value = historical_data[-1]['value']
        
        # Znajdź wartości z różnych okresów
        weekly_value = self._find_value_by_days_ago(historical_data, 7)
        monthly_value = self._find_value_by_days_ago(historical_data, 30)
        yearly_value = self._find_value_by_days_ago(historical_data, 365)
        
        return {
            'weekly_change': current_value - weekly_value,
            'weekly_change_percent': ((current_value - weekly_value) / weekly_value * 100) if weekly_value > 0 else 0,
            'monthly_change': current_value - monthly_value,
            'monthly_change_percent': ((current_value - monthly_value) / monthly_value * 100) if monthly_value > 0 else 0,
            'yearly_change': current_value - yearly_value,
            'yearly_change_percent': ((current_value - yearly_value) / yearly_value * 100) if yearly_value > 0 else 0
        }
    
    def _find_value_by_days_ago(self, historical_data: List[Dict[str, Any]], days: int) -> float:
        """Znajduje wartość sprzed określonej liczby dni"""
        target_date = datetime.now() - timedelta(days=days)
        
        # Znajdź najbliższą datę
        closest_data = min(historical_data, 
                          key=lambda x: abs((x['date'] - target_date).total_seconds()))
        
        return closest_data['value']
    
    def _calculate_risk_metrics(self, returns: List[float]) -> Dict[str, float]:
        """Oblicza metryki ryzyka"""
        if not returns:
            return {
                'sharpe_ratio': 0.0,
                'sortino_ratio': 0.0,
                'max_drawdown': 0.0,
                'volatility': 0.0,
                'beta': 1.0,
                'alpha': 0.0,
                'var_95': 0.0,
                'cvar_95': 0.0
            }
        
        import statistics
        
        # Podstawowe statystyki
        mean_return = statistics.mean(returns)
        volatility = statistics.stdev(returns) if len(returns) > 1 else 0.0
        
        # Sharpe Ratio
        risk_free_rate = self.settings['risk_free_rate'] / 365  # Dzienna stopa
        sharpe_ratio = (mean_return - risk_free_rate) / volatility if volatility > 0 else 0.0
        
        # Sortino Ratio (tylko negatywne zwroty)
        negative_returns = [r for r in returns if r < 0]
        downside_deviation = statistics.stdev(negative_returns) if len(negative_returns) > 1 else 0.0
        sortino_ratio = (mean_return - risk_free_rate) / downside_deviation if downside_deviation > 0 else 0.0
        
        # Max Drawdown
        max_drawdown = self._calculate_max_drawdown(returns)
        
        # VaR 95% (Value at Risk)
        sorted_returns = sorted(returns)
        var_index = int(len(sorted_returns) * 0.05)
        var_95 = sorted_returns[var_index] if var_index < len(sorted_returns) else 0.0
        
        # CVaR 95% (Conditional Value at Risk)
        cvar_returns = sorted_returns[:var_index] if var_index > 0 else [0.0]
        cvar_95 = statistics.mean(cvar_returns) if cvar_returns else 0.0
        
        return {
            'sharpe_ratio': sharpe_ratio,
            'sortino_ratio': sortino_ratio,
            'max_drawdown': max_drawdown,
            'volatility': volatility * 100,  # Procenty
            'beta': 1.0,  # Placeholder - wymagałby danych benchmarku
            'alpha': mean_return * 365 * 100,  # Roczny alpha w procentach
            'var_95': var_95 * 100,  # Procenty
            'cvar_95': cvar_95 * 100  # Procenty
        }
    
    def _calculate_max_drawdown(self, returns: List[float]) -> float:
        """Oblicza maksymalny drawdown"""
        if not returns:
            return 0.0
        
        cumulative = 1.0
        peak = 1.0
        max_drawdown = 0.0
        
        for return_rate in returns:
            cumulative *= (1 + return_rate)
            if cumulative > peak:
                peak = cumulative
            drawdown = (peak - cumulative) / peak
            max_drawdown = max(max_drawdown, drawdown)
        
        return max_drawdown * 100  # Procenty
    
    async def _calculate_trading_metrics(self) -> Dict[str, float]:
        """Oblicza metryki tradingowe"""
        try:
            # Symulacja danych tradingowych
            total_trades = 50
            winning_trades = 32
            losing_trades = 18
            
            win_rate = (winning_trades / total_trades * 100) if total_trades > 0 else 0.0
            avg_win = 150.0  # Średni zysk
            avg_loss = -75.0  # Średnia strata
            
            profit_factor = abs(avg_win * winning_trades / (avg_loss * losing_trades)) if losing_trades > 0 else 0.0
            recovery_factor = abs(avg_win / avg_loss) if avg_loss != 0 else 0.0
            
            return {
                'total_fees_paid': 250.0,
                'total_trades': total_trades,
                'winning_trades': winning_trades,
                'losing_trades': losing_trades,
                'win_rate': win_rate,
                'avg_win': avg_win,
                'avg_loss': avg_loss,
                'profit_factor': profit_factor,
                'recovery_factor': recovery_factor,
                'calmar_ratio': 1.5  # Placeholder
            }
            
        except Exception as e:
            logger.error(f"Error calculating trading metrics: {e}")
            return {
                'total_fees_paid': 0.0,
                'total_trades': 0,
                'winning_trades': 0,
                'losing_trades': 0,
                'win_rate': 0.0,
                'avg_win': 0.0,
                'avg_loss': 0.0,
                'profit_factor': 0.0,
                'recovery_factor': 0.0,
                'calmar_ratio': 0.0
            }
    
    async def analyze_position_risk(self, symbol: str) -> Dict[str, Any]:
        """
        Analizuje ryzyko konkretnej pozycji
        
        Args:
            symbol: Symbol aktywa
            
        Returns:
            Analiza ryzyka pozycji
        """
        try:
            position = await self.get_position(symbol)
            if not position:
                return {'error': f'Position {symbol} not found'}
            
            # Oblicz metryki ryzyka dla pozycji
            risk_analysis = {
                'symbol': symbol,
                'current_value': position.value,
                'profit_loss': position.profit_loss,
                'profit_loss_percent': position.profit_loss_percent,
                'risk_level': self._assess_position_risk_level(position),
                'recommended_action': self._get_position_recommendation(position),
                'stop_loss_suggestion': position.current_price * (1 - self.settings['stop_loss_default']),
                'take_profit_suggestion': position.current_price * (1 + self.settings['take_profit_default']),
                'position_size_percent': (position.value / await self._get_total_portfolio_value()) * 100,
                'volatility_estimate': self._estimate_position_volatility(symbol),
                'correlation_with_portfolio': self._calculate_position_correlation(symbol)
            }
            
            return risk_analysis
            
        except Exception as e:
            logger.error(f"Error analyzing position risk for {symbol}: {e}")
            return {'error': str(e)}
    
    def _assess_position_risk_level(self, position: AssetPosition) -> str:
        """Ocenia poziom ryzyka pozycji"""
        # Prosty algorytm oceny ryzyka
        if abs(position.profit_loss_percent) > 20:
            return "HIGH"
        elif abs(position.profit_loss_percent) > 10:
            return "MEDIUM"
        else:
            return "LOW"
    
    def _get_position_recommendation(self, position: AssetPosition) -> str:
        """Generuje rekomendację dla pozycji"""
        if position.profit_loss_percent > 15:
            return "CONSIDER_TAKING_PROFIT"
        elif position.profit_loss_percent < -10:
            return "CONSIDER_STOP_LOSS"
        else:
            return "HOLD"
    
    async def _get_total_portfolio_value(self) -> float:
        """Pobiera całkowitą wartość portfela"""
        try:
            summary = await self.get_portfolio_summary()
            return summary.total_value
        except:
            return 10000.0  # Fallback
    
    def _estimate_position_volatility(self, symbol: str) -> float:
        """Szacuje zmienność pozycji"""
        # Placeholder - w rzeczywistości wymagałby danych historycznych
        volatility_map = {
            'BTC': 0.8,
            'ETH': 0.7,
            'ADA': 1.2,
            'DOT': 1.0
        }
        return volatility_map.get(symbol, 0.5)
    
    def _calculate_position_correlation(self, symbol: str) -> float:
        """Oblicza korelację pozycji z portfelem"""
        # Placeholder - w rzeczywistości wymagałby analizy korelacji
        return 0.6
    
    async def rebalance_portfolio(self, target_allocations: Dict[str, float]) -> Dict[str, Any]:
        """
        Rebalansuje portfel zgodnie z docelowymi alokacjami
        
        Args:
            target_allocations: Słownik z docelowymi alokacjami (symbol -> procent)
            
        Returns:
            Wyniki rebalansowania
        """
        try:
            current_summary = await self.get_portfolio_summary()
            total_value = current_summary.total_value
            
            rebalance_actions = []
            
            for symbol, target_percent in target_allocations.items():
                target_value = total_value * (target_percent / 100)
                
                # Znajdź aktualną pozycję
                current_position = None
                for position in current_summary.positions:
                    if position.symbol == symbol:
                        current_position = position
                        break
                
                current_value = current_position.value if current_position else 0.0
                difference = target_value - current_value
                
                if abs(difference) > total_value * self.settings['rebalance_threshold']:
                    action = {
                        'symbol': symbol,
                        'current_value': current_value,
                        'target_value': target_value,
                        'difference': difference,
                        'action': 'BUY' if difference > 0 else 'SELL',
                        'amount': abs(difference)
                    }
                    rebalance_actions.append(action)
            
            return {
                'total_value': total_value,
                'actions_needed': len(rebalance_actions),
                'actions': rebalance_actions,
                'estimated_cost': sum(action['amount'] * 0.001 for action in rebalance_actions)  # 0.1% fee
            }
            
        except Exception as e:
            logger.error(f"Error rebalancing portfolio: {e}")
            return {'error': str(e)}
    
    def _on_config_updated(self, data):
        """Obsługuje zdarzenie aktualizacji konfiguracji"""
        try:
            logger.debug("Config updated - clearing metrics cache")
            self.metrics_cache.clear()
            self.last_metrics_update = None
        except Exception as e:
            logger.error(f"Error handling config update: {e}")
    
    def _on_data_updated(self, data):
        """Obsługuje zdarzenie aktualizacji danych"""
        try:
            logger.debug("Data updated - clearing cache")
            self._clear_cache()
            self.metrics_cache.clear()
            self.last_metrics_update = None
        except Exception as e:
            logger.error(f"Error handling data update: {e}")
    
    def _on_order_submitted(self, data):
        """Obsługuje zdarzenie złożenia zlecenia"""
        try:
            logger.debug("Order submitted - will update portfolio after execution")
            # Cache zostanie wyczyszczony po wykonaniu zlecenia
        except Exception as e:
            logger.error(f"Error handling order submission: {e}")

# Globalna instancja UpdatedPortfolioManager
_updated_portfolio_manager = None

def get_updated_portfolio_manager(data_manager: Optional[DataManager] = None) -> UpdatedPortfolioManager:
    """
    Zwraca globalną instancję UpdatedPortfolioManager (singleton)
    
    Args:
        data_manager: Manager danych (tylko przy pierwszym wywołaniu)
        
    Returns:
        Instancja UpdatedPortfolioManager
    """
    global _updated_portfolio_manager
    if _updated_portfolio_manager is None:
        _updated_portfolio_manager = UpdatedPortfolioManager(data_manager)
    return _updated_portfolio_manager

def reset_updated_portfolio_manager():
    """Resetuje globalną instancję UpdatedPortfolioManager (do testów)"""
    global _updated_portfolio_manager
    _updated_portfolio_manager = None
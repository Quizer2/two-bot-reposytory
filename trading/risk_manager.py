"""
System zarządzania ryzykiem dla aplikacji tradingowej
"""

import json
import os
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass
import numpy as np

@dataclass
class RiskMetrics:
    """Klasa przechowująca metryki ryzyka"""
    current_drawdown: float = 0.0
    max_drawdown: float = 0.0
    var_1day: float = 0.0
    sharpe_ratio: float = 0.0
    win_rate: float = 0.0
    profit_factor: float = 0.0
    beta: float = 0.0
    sortino_ratio: float = 0.0
    calmar_ratio: float = 0.0

@dataclass
class RiskSettings:
    """Klasa przechowująca ustawienia zarządzania ryzykiem"""
    max_position_size: float = 10.0
    max_open_positions: int = 5
    max_daily_trades: int = 20
    default_stop_loss: float = 2.0
    default_take_profit: float = 4.0
    trailing_stop_enabled: bool = False
    trailing_stop_distance: float = 1.0
    max_daily_loss: float = 5.0
    max_drawdown: float = 15.0
    emergency_stop_enabled: bool = True
    risk_per_trade: float = 1.0
    kelly_criterion_enabled: bool = False
    compound_profits: bool = True

class RiskManager:
    """Główna klasa zarządzania ryzykiem"""
    
    def __init__(self, config_path: str = "config/risk_settings.json"):
        self.config_path = config_path
        self.settings = RiskSettings()
        self.metrics = RiskMetrics()
        self.daily_trades_count = 0
        self.daily_loss = 0.0
        self.open_positions_count = 0
        self.emergency_stop_active = False
        self.last_reset_date = datetime.now().date()
        
        # Historia transakcji dla obliczeń metryk
        self.trade_history = []
        self.portfolio_values = []
        
        # Załaduj ustawienia
        self.load_settings()
        
        # Konfiguracja logowania
        logging.basicConfig(level=logging.INFO)
        self.logger = logging.getLogger(__name__)
    
    def load_settings(self) -> bool:
        """Ładuje ustawienia z pliku konfiguracyjnego"""
        try:
            if os.path.exists(self.config_path):
                with open(self.config_path, 'r') as f:
                    data = json.load(f)
                
                # Aktualizuj ustawienia
                for key, value in data.items():
                    if hasattr(self.settings, key):
                        setattr(self.settings, key, value)
                
                self.logger.info("Ustawienia zarządzania ryzykiem załadowane pomyślnie")
                return True
            else:
                self.logger.warning(f"Plik konfiguracyjny {self.config_path} nie istnieje")
                return False
                
        except Exception as e:
            self.logger.error(f"Błąd podczas ładowania ustawień: {e}")
            return False
    
    def save_settings(self) -> bool:
        """Zapisuje ustawienia do pliku konfiguracyjnego"""
        try:
            # Utwórz folder config jeśli nie istnieje
            os.makedirs(os.path.dirname(self.config_path), exist_ok=True)
            
            # Konwertuj ustawienia do słownika
            settings_dict = {
                'max_position_size': self.settings.max_position_size,
                'max_open_positions': self.settings.max_open_positions,
                'max_daily_trades': self.settings.max_daily_trades,
                'default_stop_loss': self.settings.default_stop_loss,
                'default_take_profit': self.settings.default_take_profit,
                'trailing_stop_enabled': self.settings.trailing_stop_enabled,
                'trailing_stop_distance': self.settings.trailing_stop_distance,
                'max_daily_loss': self.settings.max_daily_loss,
                'max_drawdown': self.settings.max_drawdown,
                'emergency_stop_enabled': self.settings.emergency_stop_enabled,
                'risk_per_trade': self.settings.risk_per_trade,
                'kelly_criterion_enabled': self.settings.kelly_criterion_enabled,
                'compound_profits': self.settings.compound_profits
            }
            
            with open(self.config_path, 'w') as f:
                json.dump(settings_dict, f, indent=4)
            
            self.logger.info("Ustawienia zarządzania ryzykiem zapisane pomyślnie")
            return True
            
        except Exception as e:
            self.logger.error(f"Błąd podczas zapisywania ustawień: {e}")
            return False
    
    def update_settings(self, new_settings: Dict) -> bool:
        """Aktualizuje ustawienia zarządzania ryzykiem"""
        try:
            for key, value in new_settings.items():
                if hasattr(self.settings, key):
                    setattr(self.settings, key, value)
            
            # Zapisz do pliku
            return self.save_settings()
            
        except Exception as e:
            self.logger.error(f"Błąd podczas aktualizacji ustawień: {e}")
            return False
    
    def check_position_size_limit(self, position_size_percent: float) -> bool:
        """Sprawdza czy rozmiar pozycji nie przekracza limitu"""
        return position_size_percent <= self.settings.max_position_size
    
    def check_open_positions_limit(self) -> bool:
        """Sprawdza czy liczba otwartych pozycji nie przekracza limitu"""
        return self.open_positions_count < self.settings.max_open_positions
    
    def check_daily_trades_limit(self) -> bool:
        """Sprawdza czy liczba dziennych transakcji nie przekracza limitu"""
        self._reset_daily_counters_if_needed()
        return self.daily_trades_count < self.settings.max_daily_trades
    
    def check_daily_loss_limit(self) -> bool:
        """Sprawdza czy dzienna strata nie przekracza limitu"""
        self._reset_daily_counters_if_needed()
        return self.daily_loss < self.settings.max_daily_loss
    
    def check_drawdown_limit(self) -> bool:
        """Sprawdza czy drawdown nie przekracza limitu"""
        return self.metrics.current_drawdown < self.settings.max_drawdown
    
    def can_open_position(self, position_size_percent: float) -> Tuple[bool, str]:
        """Sprawdza czy można otworzyć pozycję"""
        if self.emergency_stop_active:
            return False, "Aktywne awaryjne zatrzymanie"
        
        if not self.check_position_size_limit(position_size_percent):
            return False, f"Rozmiar pozycji ({position_size_percent}%) przekracza limit ({self.settings.max_position_size}%)"
        
        if not self.check_open_positions_limit():
            return False, f"Przekroczono limit otwartych pozycji ({self.settings.max_open_positions})"
        
        if not self.check_daily_trades_limit():
            return False, f"Przekroczono dzienny limit transakcji ({self.settings.max_daily_trades})"
        
        if not self.check_daily_loss_limit():
            return False, f"Przekroczono dzienny limit strat ({self.settings.max_daily_loss}%)"
        
        if not self.check_drawdown_limit():
            return False, f"Przekroczono limit drawdown ({self.settings.max_drawdown}%)"
        
        return True, "OK"
    
    def calculate_position_size(self, account_balance: float, risk_amount: float = None) -> float:
        """Oblicza rozmiar pozycji na podstawie zarządzania kapitałem"""
        if risk_amount is None:
            risk_amount = account_balance * (self.settings.risk_per_trade / 100)
        
        if self.settings.kelly_criterion_enabled:
            # Implementacja kryterium Kelly'ego
            kelly_fraction = self._calculate_kelly_fraction()
            if kelly_fraction > 0:
                position_size = account_balance * min(kelly_fraction, self.settings.max_position_size / 100)
            else:
                position_size = risk_amount
        else:
            position_size = risk_amount
        
        # Ograniczenie do maksymalnego rozmiaru pozycji
        max_position_value = account_balance * (self.settings.max_position_size / 100)
        return min(position_size, max_position_value)
    
    def _calculate_kelly_fraction(self) -> float:
        """Oblicza frakcję Kelly'ego na podstawie historii transakcji"""
        if len(self.trade_history) < 10:  # Minimum 10 transakcji
            return 0.0
        
        try:
            returns = [trade['return_pct'] for trade in self.trade_history[-50:]]  # Ostatnie 50 transakcji
            
            if not returns:
                return 0.0
            
            win_rate = len([r for r in returns if r > 0]) / len(returns)
            avg_win = np.mean([r for r in returns if r > 0]) if any(r > 0 for r in returns) else 0
            avg_loss = abs(np.mean([r for r in returns if r < 0])) if any(r < 0 for r in returns) else 1
            
            if avg_loss == 0:
                return 0.0
            
            # Formuła Kelly'ego: f = (bp - q) / b
            # gdzie: b = avg_win/avg_loss, p = win_rate, q = 1-win_rate
            b = avg_win / avg_loss
            kelly_fraction = (b * win_rate - (1 - win_rate)) / b
            
            # Ograniczenie do rozsądnych wartości
            return max(0.0, min(kelly_fraction, 0.25))  # Maksymalnie 25%
            
        except Exception as e:
            self.logger.error(f"Błąd podczas obliczania frakcji Kelly'ego: {e}")
            return 0.0
    
    def record_trade(self, trade_data: Dict):
        """Rejestruje transakcję w historii"""
        try:
            trade_record = {
                'timestamp': datetime.now(),
                'symbol': trade_data.get('symbol', ''),
                'side': trade_data.get('side', ''),
                'size': trade_data.get('size', 0),
                'price': trade_data.get('price', 0),
                'pnl': trade_data.get('pnl', 0),
                'return_pct': trade_data.get('return_pct', 0)
            }
            
            self.trade_history.append(trade_record)
            
            # Aktualizuj liczniki
            self._reset_daily_counters_if_needed()
            self.daily_trades_count += 1
            
            if trade_record['pnl'] < 0:
                self.daily_loss += abs(trade_record['return_pct'])
            
            # Ograniczenie historii do ostatnich 1000 transakcji
            if len(self.trade_history) > 1000:
                self.trade_history = self.trade_history[-1000:]
            
            # Aktualizuj metryki
            self._update_metrics()
            
        except Exception as e:
            self.logger.error(f"Błąd podczas rejestrowania transakcji: {e}")
    
    def update_portfolio_value(self, portfolio_value: float):
        """Aktualizuje wartość portfela i oblicza metryki"""
        try:
            self.portfolio_values.append({
                'timestamp': datetime.now(),
                'value': portfolio_value
            })
            
            # Ograniczenie historii do ostatnich 1000 wartości
            if len(self.portfolio_values) > 1000:
                self.portfolio_values = self.portfolio_values[-1000:]
            
            # Aktualizuj metryki
            self._update_metrics()
            
        except Exception as e:
            self.logger.error(f"Błąd podczas aktualizacji wartości portfela: {e}")
    
    def _update_metrics(self):
        """Aktualizuje metryki ryzyka"""
        try:
            if len(self.portfolio_values) < 2:
                return
            
            values = [pv['value'] for pv in self.portfolio_values]
            
            # Oblicz drawdown
            peak = values[0]
            max_dd = 0
            current_dd = 0
            
            for value in values:
                if value > peak:
                    peak = value
                    current_dd = 0
                else:
                    current_dd = (peak - value) / peak * 100
                    max_dd = max(max_dd, current_dd)
            
            self.metrics.current_drawdown = current_dd
            self.metrics.max_drawdown = max_dd
            
            # Oblicz zwroty
            returns = []
            for i in range(1, len(values)):
                ret = (values[i] - values[i-1]) / values[i-1]
                returns.append(ret)
            
            if returns:
                # Sharpe Ratio (zakładając 0% risk-free rate)
                mean_return = np.mean(returns)
                std_return = np.std(returns)
                self.metrics.sharpe_ratio = (mean_return / std_return * np.sqrt(252)) if std_return > 0 else 0
                
                # Sortino Ratio
                negative_returns = [r for r in returns if r < 0]
                downside_std = np.std(negative_returns) if negative_returns else 0
                self.metrics.sortino_ratio = (mean_return / downside_std * np.sqrt(252)) if downside_std > 0 else 0
                
                # Calmar Ratio
                annualized_return = mean_return * 252
                self.metrics.calmar_ratio = (annualized_return / (max_dd / 100)) if max_dd > 0 else 0
                
                # VaR (95% confidence, 1 day)
                if len(returns) >= 20:
                    var_95 = np.percentile(returns, 5)
                    self.metrics.var_1day = abs(var_95 * values[-1])
            
            # Oblicz metryki z historii transakcji
            if self.trade_history:
                winning_trades = [t for t in self.trade_history if t['pnl'] > 0]
                losing_trades = [t for t in self.trade_history if t['pnl'] < 0]
                
                total_trades = len(self.trade_history)
                self.metrics.win_rate = (len(winning_trades) / total_trades * 100) if total_trades > 0 else 0
                
                total_wins = sum(t['pnl'] for t in winning_trades)
                total_losses = abs(sum(t['pnl'] for t in losing_trades))
                self.metrics.profit_factor = (total_wins / total_losses) if total_losses > 0 else 0
            
        except Exception as e:
            self.logger.error(f"Błąd podczas aktualizacji metryk: {e}")
    
    def _reset_daily_counters_if_needed(self):
        """Resetuje dzienne liczniki jeśli minął dzień"""
        current_date = datetime.now().date()
        if current_date > self.last_reset_date:
            self.daily_trades_count = 0
            self.daily_loss = 0.0
            self.last_reset_date = current_date
    
    def activate_emergency_stop(self, reason: str = ""):
        """Aktywuje awaryjne zatrzymanie"""
        self.emergency_stop_active = True
        self.logger.warning(f"Aktywowano awaryjne zatrzymanie. Powód: {reason}")
    
    def deactivate_emergency_stop(self):
        """Dezaktywuje awaryjne zatrzymanie"""
        self.emergency_stop_active = False
        self.logger.info("Dezaktywowano awaryjne zatrzymanie")
    
    def get_risk_status(self) -> Dict:
        """Zwraca aktualny status ryzyka"""
        return {
            'emergency_stop_active': self.emergency_stop_active,
            'daily_trades_count': self.daily_trades_count,
            'daily_trades_limit': self.settings.max_daily_trades,
            'daily_loss': self.daily_loss,
            'daily_loss_limit': self.settings.max_daily_loss,
            'open_positions_count': self.open_positions_count,
            'open_positions_limit': self.settings.max_open_positions,
            'current_drawdown': self.metrics.current_drawdown,
            'max_drawdown_limit': self.settings.max_drawdown,
            'metrics': {
                'current_drawdown': self.metrics.current_drawdown,
                'max_drawdown': self.metrics.max_drawdown,
                'var_1day': self.metrics.var_1day,
                'sharpe_ratio': self.metrics.sharpe_ratio,
                'win_rate': self.metrics.win_rate,
                'profit_factor': self.metrics.profit_factor,
                'beta': self.metrics.beta,
                'sortino_ratio': self.metrics.sortino_ratio,
                'calmar_ratio': self.metrics.calmar_ratio
            }
        }
    
    def update_open_positions_count(self, count: int):
        """Aktualizuje liczbę otwartych pozycji"""
        self.open_positions_count = count
    
    def should_use_trailing_stop(self) -> bool:
        """Sprawdza czy należy używać trailing stop"""
        return self.settings.trailing_stop_enabled
    
    def get_trailing_stop_distance(self) -> float:
        """Zwraca odległość trailing stop"""
        return self.settings.trailing_stop_distance
    
    def get_default_stop_loss(self) -> float:
        """Zwraca domyślny stop loss"""
        return self.settings.default_stop_loss
    
    def get_default_take_profit(self) -> float:
        """Zwraca domyślny take profit"""
        return self.settings.default_take_profit
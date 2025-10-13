"""
from utils.logger import get_logger
logger = get_logger(__name__)

Custom Strategy - Strategia handlowa z konfigurowalnymi warunkami
"""

import asyncio
import json
import operator
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Callable, Union
from collections import deque
from dataclasses import dataclass, asdict
from enum import Enum

from ..exchange.base_exchange import BaseExchange
from ..database import DatabaseManager
from ..risk_management import RiskManager
from utils.logger import get_logger
from utils.helpers import FormatHelper, CalculationHelper


class CustomStatus(Enum):
    """Status strategii Custom"""
    STOPPED = "stopped"
    RUNNING = "running"
    PAUSED = "paused"
    ERROR = "error"


@dataclass
class CustomRule:
    """Reguła Custom"""
    name: str
    conditions: List[Dict]
    action: Dict
    enabled: bool = True
    triggered_count: int = 0
    success_count: int = 0
    last_triggered: Optional[datetime] = None


@dataclass
class CustomCondition:
    """Warunek Custom"""
    indicator: str
    operator: str
    value: Union[float, tuple]
    timeframe: str = "1m"
    period: int = 14


@dataclass
class CustomAction:
    """Akcja Custom"""
    type: str  # buy, sell, close_position, notify
    amount: float
    amount_type: str = "currency"  # currency, percentage
    message: Optional[str] = None


@dataclass
class CustomStatistics:
    """Statystyki strategii Custom"""
    total_rules: int = 0
    enabled_rules: int = 0
    rules_triggered: int = 0
    successful_actions: int = 0
    failed_actions: int = 0
    total_profit: float = 0.0
    last_rule_triggered: Optional[str] = None
    last_action_time: Optional[datetime] = None
    rules_performance: Dict[str, Dict] = None

    def __post_init__(self):
        if self.rules_performance is None:
            self.rules_performance = {}


class CustomStrategy:
    """
    Strategia Custom - konfigurowalne warunki handlowe
    
    Pozwala użytkownikowi definiować własne warunki handlowe używając
    różnych wskaźników technicznych i operatorów logicznych.
    """

    def __init__(self, pair: str, custom_rules: List[Dict], 
                 check_interval: int = 30, **kwargs):
        """
        Inicjalizacja strategii Custom
        
        Args:
            pair: Para handlowa (np. 'BTC/USDT')
            custom_rules: Lista reguł handlowych
            check_interval: Interwał sprawdzania warunków (sekundy)
        """
        self.pair = pair
        self.custom_rules = [CustomRule(**rule) for rule in custom_rules]
        self.check_interval = check_interval
        
        # Komponenty
        self.exchange: Optional[BaseExchange] = None
        self.db_manager: Optional[DatabaseManager] = None
        self.risk_manager: Optional[RiskManager] = None
        
        # Status
        self.status = CustomStatus.STOPPED
        self.is_running = False
        self.is_paused = False
        
        # Dostępne wskaźniki
        self.available_indicators = {
            'price': self._get_price_indicator,
            'rsi': self._get_rsi_indicator,
            'ema': self._get_ema_indicator,
            'sma': self._get_sma_indicator,
            'macd': self._get_macd_indicator,
            'volume': self._get_volume_indicator,
            'bollinger_upper': self._get_bollinger_upper_indicator,
            'bollinger_lower': self._get_bollinger_lower_indicator,
            'atr': self._get_atr_indicator,
            'stochastic': self._get_stochastic_indicator,
            'balance': self._get_balance_indicator,
            'profit_loss': self._get_profit_loss_indicator,
            'time': self._get_time_indicator
        }
        
        # Dostępne operatory
        self.available_operators = {
            '>': operator.gt,
            '<': operator.lt,
            '>=': operator.ge,
            '<=': operator.le,
            '==': operator.eq,
            '!=': operator.ne,
            'between': self._between_operator,
            'crosses_above': self._crosses_above_operator,
            'crosses_below': self._crosses_below_operator
        }
        
        # Historia danych
        self.price_history = deque(maxlen=500)
        self.volume_history = deque(maxlen=500)
        self.indicator_cache = {}
        self.last_indicator_values = {}
        
        # Statystyki
        self.statistics = CustomStatistics()
        self._initialize_rule_statistics()
        
        logger.info(f"Inicjalizacja Custom Strategy: {pair}, reguły: {len(self.custom_rules)}")

    def _initialize_rule_statistics(self):
        """Inicjalizacja statystyk dla reguł"""
        for rule in self.custom_rules:
            self.statistics.rules_performance[rule.name] = {
                'triggered': 0,
                'successful': 0,
                'failed': 0,
                'profit': 0.0
            }

    async def validate_parameters(self) -> bool:
        """Walidacja parametrów strategii"""
        try:
            if not self.custom_rules:
                logger.error("Brak zdefiniowanych reguł")
                return False
            
            for i, rule in enumerate(self.custom_rules):
                if not await self._validate_rule(rule, i):
                    return False
            
            return True
            
        except Exception as e:
            logger.error(f"Błąd walidacji parametrów Custom: {e}")
            return False

    async def _validate_rule(self, rule: CustomRule, rule_index: int) -> bool:
        """Walidacja pojedynczej reguły"""
        try:
            # Sprawdzenie warunków
            if not rule.conditions:
                logger.error(f"Reguła {rule_index}: brak warunków")
                return False
            
            for j, condition in enumerate(rule.conditions):
                if not await self._validate_condition(condition, rule_index, j):
                    return False
            
            # Sprawdzenie akcji
            if not await self._validate_action(rule.action, rule_index):
                return False
            
            return True
            
        except Exception as e:
            logger.error(f"Błąd walidacji reguły {rule_index}: {e}")
            return False

    async def _validate_condition(self, condition: Dict, rule_index: int, condition_index: int) -> bool:
        """Walidacja warunku"""
        try:
            required_fields = ['indicator', 'operator', 'value']
            for field in required_fields:
                if field not in condition:
                    logger.error(f"Reguła {rule_index}, warunek {condition_index}: brakuje pola '{field}'")
                    return False
            
            # Sprawdzenie wskaźnika
            if condition['indicator'] not in self.available_indicators:
                logger.error(f"Nieznany wskaźnik: {condition['indicator']}")
                return False
            
            # Sprawdzenie operatora
            if condition['operator'] not in self.available_operators:
                logger.error(f"Nieznany operator: {condition['operator']}")
                return False
            
            return True
            
        except Exception as e:
            logger.error(f"Błąd walidacji warunku: {e}")
            return False

    async def _validate_action(self, action: Dict, rule_index: int) -> bool:
        """Walidacja akcji"""
        try:
            required_fields = ['type', 'amount']
            for field in required_fields:
                if field not in action:
                    logger.error(f"Reguła {rule_index}: brakuje pola '{field}' w akcji")
                    return False
            
            if action['type'] not in ['buy', 'sell', 'close_position', 'notify']:
                logger.error(f"Nieznany typ akcji: {action['type']}")
                return False
            
            if not isinstance(action['amount'], (int, float)) or action['amount'] <= 0:
                logger.error(f"Nieprawidłowa kwota: {action['amount']}")
                return False
            
            return True
            
        except Exception as e:
            logger.error(f"Błąd walidacji akcji: {e}")
            return False

    async def initialize(self, db_manager: DatabaseManager, risk_manager: RiskManager,
                        exchange: BaseExchange, data_manager=None) -> bool:
        """Inicjalizacja strategii"""
        try:
            self.db_manager = db_manager
            self.risk_manager = risk_manager
            self.exchange = exchange
            self.data_manager = data_manager
            
            # Walidacja parametrów
            if not await self.validate_parameters():
                return False
            
            # Wczytanie historii danych
            await self._load_initial_data()
            
            # Aktualizacja statystyk
            self.statistics.total_rules = len(self.custom_rules)
            self.statistics.enabled_rules = len([r for r in self.custom_rules if r.enabled])
            
            logger.info("Custom Strategy zainicjalizowana pomyślnie")
            return True
            
        except Exception as e:
            logger.error(f"Błąd inicjalizacji Custom Strategy: {e}")
            return False

    async def start(self):
        """Uruchomienie strategii"""
        try:
            if self.status == CustomStatus.RUNNING:
                logger.warning("Custom Strategy już działa")
                return
            
            self.is_running = True
            self.is_paused = False
            self.status = CustomStatus.RUNNING
            
            logger.info("Uruchamianie Custom Strategy")
            
            # Główna pętla
            while self.is_running:
                try:
                    if not self.is_paused:
                        await self._update_market_data()
                        await self._check_all_rules()
                        await self._update_statistics()
                    
                    await asyncio.sleep(self.check_interval)
                    
                except Exception as e:
                    logger.error(f"Błąd w pętli Custom Strategy: {e}")
                    await asyncio.sleep(60)
            
        except Exception as e:
            logger.error(f"Krytyczny błąd Custom Strategy: {e}")
            self.status = CustomStatus.ERROR
            raise

    async def stop(self):
        """Zatrzymanie strategii"""
        try:
            logger.info("Zatrzymywanie Custom Strategy")
            
            self.is_running = False
            self.is_paused = False
            self.status = CustomStatus.STOPPED
            
            # Zapisanie stanu
            await self._save_state()
            
            logger.info("Custom Strategy zatrzymana")
            
        except Exception as e:
            logger.error(f"Błąd podczas zatrzymywania Custom Strategy: {e}")

    async def pause(self):
        """Wstrzymanie strategii"""
        if self.status == CustomStatus.RUNNING:
            self.is_paused = True
            self.status = CustomStatus.PAUSED
            logger.info("Custom Strategy wstrzymana")

    async def resume(self):
        """Wznowienie strategii"""
        if self.status == CustomStatus.PAUSED:
            self.is_paused = False
            self.status = CustomStatus.RUNNING
            logger.info("Custom Strategy wznowiona")

    async def _load_initial_data(self):
        """Wczytanie początkowych danych"""
        try:
            # Pobranie historii cen
            candles = await self.exchange.get_ohlcv(self.pair, '1m', limit=500)
            
            for candle in candles:
                price = float(candle[4])  # close price
                volume = float(candle[5])  # volume
                
                self.price_history.append(price)
                self.volume_history.append(volume)
            
            # Jeśli brak historii, użyj aktualnej ceny
            if not self.price_history:
                ticker = await self.exchange.get_ticker(self.pair)
                current_price = float(ticker['last'])
                
                for _ in range(50):
                    self.price_history.append(current_price)
                    self.volume_history.append(1.0)
            
            logger.info(f"Wczytano {len(self.price_history)} punktów danych")
            
        except Exception as e:
            logger.error(f"Błąd wczytywania danych: {e}")

    async def _update_market_data(self):
        """Aktualizacja danych rynkowych"""
        try:
            ticker = await self.exchange.get_ticker(self.pair)
            current_price = float(ticker['last'])
            volume = float(ticker.get('baseVolume', 1.0))
            
            self.price_history.append(current_price)
            self.volume_history.append(volume)
            
            # Czyszczenie cache wskaźników
            self.indicator_cache.clear()
            
        except Exception as e:
            logger.error(f"Błąd aktualizacji danych: {e}")

    async def _check_all_rules(self):
        """Sprawdzenie wszystkich reguł"""
        try:
            for rule in self.custom_rules:
                if rule.enabled:
                    await self._check_rule(rule)
                    
        except Exception as e:
            logger.error(f"Błąd sprawdzania reguł: {e}")

    async def _check_rule(self, rule: CustomRule):
        """Sprawdzenie pojedynczej reguły"""
        try:
            # Sprawdzenie wszystkich warunków
            all_conditions_met = True
            
            for condition in rule.conditions:
                if not await self._evaluate_condition(condition):
                    all_conditions_met = False
                    break
            
            # Wykonanie akcji jeśli warunki spełnione
            if all_conditions_met:
                await self._execute_action(rule)
                
        except Exception as e:
            logger.error(f"Błąd sprawdzania reguły '{rule.name}': {e}")

    async def _evaluate_condition(self, condition: Dict) -> bool:
        """Ocena warunku"""
        try:
            indicator_name = condition['indicator']
            operator_name = condition['operator']
            expected_value = condition['value']
            
            # Pobranie wartości wskaźnika
            indicator_value = await self._get_indicator_value(indicator_name, condition)
            
            if indicator_value is None:
                return False
            
            # Zastosowanie operatora
            operator_func = self.available_operators[operator_name]
            
            if operator_name in ['crosses_above', 'crosses_below']:
                return operator_func(indicator_name, indicator_value, expected_value)
            else:
                return operator_func(indicator_value, expected_value)
                
        except Exception as e:
            logger.error(f"Błąd oceny warunku: {e}")
            return False

    async def _get_indicator_value(self, indicator_name: str, condition: Dict) -> Optional[float]:
        """Pobranie wartości wskaźnika"""
        try:
            # Cache key
            cache_key = f"{indicator_name}_{condition.get('timeframe', '1m')}_{condition.get('period', 14)}"
            
            if cache_key in self.indicator_cache:
                return self.indicator_cache[cache_key]
            
            # Obliczenie wskaźnika
            indicator_func = self.available_indicators[indicator_name]
            value = await indicator_func(condition)
            
            # Zapisanie w cache
            self.indicator_cache[cache_key] = value
            
            return value
            
        except Exception as e:
            logger.error(f"Błąd pobierania wskaźnika {indicator_name}: {e}")
            return None

    # Implementacje wskaźników
    async def _get_price_indicator(self, condition: Dict) -> Optional[float]:
        """Wskaźnik ceny"""
        try:
            if self.price_history:
                return self.price_history[-1]
            return None
        except Exception:
            return None

    async def _get_rsi_indicator(self, condition: Dict) -> Optional[float]:
        """Wskaźnik RSI"""
        try:
            period = condition.get('period', 14)
            
            if len(self.price_history) < period + 1:
                return None
            
            prices = list(self.price_history)[-period-1:]
            deltas = [prices[i+1] - prices[i] for i in range(len(prices)-1)]
            
            gains = [d if d > 0 else 0 for d in deltas]
            losses = [-d if d < 0 else 0 for d in deltas]
            
            avg_gain = sum(gains) / len(gains) if gains else 0
            avg_loss = sum(losses) / len(losses) if losses else 0
            
            if avg_loss == 0:
                return 100.0
            
            rs = avg_gain / avg_loss
            rsi = 100 - (100 / (1 + rs))
            
            return rsi
            
        except Exception:
            return None

    async def _get_ema_indicator(self, condition: Dict) -> Optional[float]:
        """Wskaźnik EMA"""
        try:
            period = condition.get('period', 20)
            
            if len(self.price_history) < period:
                return None
            
            prices = list(self.price_history)
            multiplier = 2 / (period + 1)
            ema = prices[0]
            
            for price in prices[1:]:
                ema = (price * multiplier) + (ema * (1 - multiplier))
            
            return ema
            
        except Exception:
            return None

    async def _get_sma_indicator(self, condition: Dict) -> Optional[float]:
        """Wskaźnik SMA"""
        try:
            period = condition.get('period', 20)
            
            if len(self.price_history) < period:
                return None
            
            prices = list(self.price_history)[-period:]
            return sum(prices) / len(prices)
            
        except Exception:
            return None

    async def _get_macd_indicator(self, condition: Dict) -> Optional[float]:
        """Wskaźnik MACD"""
        try:
            fast_period = condition.get('fast_period', 12)
            slow_period = condition.get('slow_period', 26)
            
            ema_fast = await self._get_ema_indicator({'period': fast_period})
            ema_slow = await self._get_ema_indicator({'period': slow_period})
            
            if ema_fast is None or ema_slow is None:
                return None
            
            return ema_fast - ema_slow
            
        except Exception:
            return None

    async def _get_volume_indicator(self, condition: Dict) -> Optional[float]:
        """Wskaźnik wolumenu"""
        try:
            if self.volume_history:
                return self.volume_history[-1]
            return None
        except Exception:
            return None

    async def _get_bollinger_upper_indicator(self, condition: Dict) -> Optional[float]:
        """Górna linia Bollinger Bands"""
        try:
            period = condition.get('period', 20)
            std_dev = condition.get('std_dev', 2.0)
            
            if len(self.price_history) < period:
                return None
            
            prices = list(self.price_history)[-period:]
            sma = sum(prices) / len(prices)
            variance = sum((p - sma) ** 2 for p in prices) / len(prices)
            std = variance ** 0.5
            
            return sma + (std * std_dev)
            
        except Exception:
            return None

    async def _get_bollinger_lower_indicator(self, condition: Dict) -> Optional[float]:
        """Dolna linia Bollinger Bands"""
        try:
            period = condition.get('period', 20)
            std_dev = condition.get('std_dev', 2.0)
            
            if len(self.price_history) < period:
                return None
            
            prices = list(self.price_history)[-period:]
            sma = sum(prices) / len(prices)
            variance = sum((p - sma) ** 2 for p in prices) / len(prices)
            std = variance ** 0.5
            
            return sma - (std * std_dev)
            
        except Exception:
            return None

    async def _get_atr_indicator(self, condition: Dict) -> Optional[float]:
        """Wskaźnik ATR"""
        try:
            period = condition.get('period', 14)
            
            if len(self.price_history) < period + 1:
                return None
            
            prices = list(self.price_history)[-period-1:]
            true_ranges = []
            
            for i in range(1, len(prices)):
                tr = abs(prices[i] - prices[i-1])
                true_ranges.append(tr)
            
            return sum(true_ranges) / len(true_ranges) if true_ranges else None
            
        except Exception:
            return None

    async def _get_stochastic_indicator(self, condition: Dict) -> Optional[float]:
        """Wskaźnik Stochastic"""
        try:
            period = condition.get('period', 14)
            
            if len(self.price_history) < period:
                return None
            
            prices = list(self.price_history)[-period:]
            current_price = prices[-1]
            lowest_low = min(prices)
            highest_high = max(prices)
            
            if highest_high == lowest_low:
                return 50.0
            
            stoch_k = ((current_price - lowest_low) / (highest_high - lowest_low)) * 100
            return stoch_k
            
        except Exception:
            return None

    async def _get_balance_indicator(self, condition: Dict) -> Optional[float]:
        """Wskaźnik salda"""
        try:
            currency = condition.get('currency', self.pair.split('/')[1])
            balance = await self.exchange.get_balance()
            return float(balance.get(currency, {}).get('free', 0))
        except Exception:
            return None

    async def _get_profit_loss_indicator(self, condition: Dict) -> Optional[float]:
        """Wskaźnik P&L"""
        try:
            return self.statistics.total_profit
        except Exception:
            return None

    async def _get_time_indicator(self, condition: Dict) -> Optional[float]:
        """Wskaźnik czasu"""
        try:
            time_type = condition.get('time_type', 'hour')
            now = datetime.now()
            
            if time_type == 'hour':
                return float(now.hour)
            elif time_type == 'minute':
                return float(now.minute)
            elif time_type == 'day_of_week':
                return float(now.weekday())
            
            return None
            
        except Exception:
            return None

    # Operatory
    def _between_operator(self, value: float, range_tuple: tuple) -> bool:
        """Operator 'between'"""
        try:
            min_val, max_val = range_tuple
            return min_val <= value <= max_val
        except Exception:
            return False

    def _crosses_above_operator(self, indicator_name: str, current_value: float, threshold: float) -> bool:
        """Operator 'crosses_above'"""
        try:
            last_value = self.last_indicator_values.get(indicator_name)
            
            if last_value is None:
                self.last_indicator_values[indicator_name] = current_value
                return False
            
            result = last_value <= threshold < current_value
            self.last_indicator_values[indicator_name] = current_value
            
            return result
            
        except Exception:
            return False

    def _crosses_below_operator(self, indicator_name: str, current_value: float, threshold: float) -> bool:
        """Operator 'crosses_below'"""
        try:
            last_value = self.last_indicator_values.get(indicator_name)
            
            if last_value is None:
                self.last_indicator_values[indicator_name] = current_value
                return False
            
            result = last_value >= threshold > current_value
            self.last_indicator_values[indicator_name] = current_value
            
            return result
            
        except Exception:
            return False

    async def _execute_action(self, rule: CustomRule):
        """Wykonanie akcji"""
        try:
            action = rule.action
            action_type = action['type']
            amount = action['amount']
            amount_type = action.get('amount_type', 'currency')
            
            logger.info(f"Wykonywanie akcji dla reguły '{rule.name}': {action_type}")
            
            # Aktualizacja statystyk reguły
            rule.triggered_count += 1
            rule.last_triggered = datetime.now()
            
            self.statistics.rules_triggered += 1
            self.statistics.last_rule_triggered = rule.name
            self.statistics.last_action_time = datetime.now()
            
            rule_stats = self.statistics.rules_performance[rule.name]
            rule_stats['triggered'] += 1
            
            success = False
            
            if action_type == 'buy':
                success = await self._execute_buy_action(amount, amount_type)
            elif action_type == 'sell':
                success = await self._execute_sell_action(amount, amount_type)
            elif action_type == 'close_position':
                success = await self._execute_close_position_action()
            elif action_type == 'notify':
                success = await self._execute_notify_action(rule.name, action)
            
            # Aktualizacja statystyk sukcesu
            if success:
                self.statistics.successful_actions += 1
                rule_stats['successful'] += 1
                rule.success_count += 1
            else:
                self.statistics.failed_actions += 1
                rule_stats['failed'] += 1
                
        except Exception as e:
            logger.error(f"Błąd wykonywania akcji: {e}")

    async def _execute_buy_action(self, amount: float, amount_type: str) -> bool:
        """Wykonanie akcji kupna"""
        try:
            if amount_type == 'percentage':
                base_currency = self.pair.split('/')[1]
                balance = await self.exchange.get_balance()
                available_balance = float(balance.get(base_currency, {}).get('free', 0))
                investment_amount = available_balance * (amount / 100)
            else:
                investment_amount = amount
            
            # Sprawdzenie przez risk manager
            if not await self.risk_manager.check_trade_risk(
                self.pair, 'buy', investment_amount, None
            ):
                logger.warning("Transakcja odrzucona przez risk manager")
                return False
            
            # Złożenie zlecenia
            logger.debug(f"TRACE: order.submitted - symbol={self.pair}, side=buy, amount={investment_amount}, type=market, strategy=custom")
            order = await self.exchange.create_market_buy_order(self.pair, None, investment_amount)
            
            if order:
                logger.info(f"Zlecenie kupna wykonane: {order['id']}")
                return True
            
            return False
            
        except Exception as e:
            logger.error(f"Błąd wykonywania akcji kupna: {e}")
            return False

    async def _execute_sell_action(self, amount: float, amount_type: str) -> bool:
        """Wykonanie akcji sprzedaży"""
        try:
            if amount_type == 'percentage':
                quote_currency = self.pair.split('/')[0]
                balance = await self.exchange.get_balance()
                available_balance = float(balance.get(quote_currency, {}).get('free', 0))
                sell_amount = available_balance * (amount / 100)
            else:
                sell_amount = amount
            
            # Sprawdzenie przez risk manager
            ticker = await self.exchange.get_ticker(self.pair)
            current_price = float(ticker['last'])
            
            if not await self.risk_manager.check_trade_risk(
                self.pair, 'sell', sell_amount, current_price
            ):
                logger.warning("Transakcja odrzucona przez risk manager")
                return False
            
            # Złożenie zlecenia
            logger.debug(f"TRACE: order.submitted - symbol={self.pair}, side=sell, amount={sell_amount}, type=market, strategy=custom")
            order = await self.exchange.create_market_sell_order(self.pair, sell_amount)
            
            if order:
                logger.info(f"Zlecenie sprzedaży wykonane: {order['id']}")
                return True
            
            return False
            
        except Exception as e:
            logger.error(f"Błąd wykonywania akcji sprzedaży: {e}")
            return False

    async def _execute_close_position_action(self) -> bool:
        """Wykonanie akcji zamknięcia pozycji"""
        try:
            quote_currency = self.pair.split('/')[0]
            balance = await self.exchange.get_balance()
            available_balance = float(balance.get(quote_currency, {}).get('free', 0))
            
            if available_balance > 0:
                logger.debug(f"TRACE: order.submitted - symbol={self.pair}, side=sell, amount={available_balance}, type=market, strategy=custom")
                order = await self.exchange.create_market_sell_order(self.pair, available_balance)
                
                if order:
                    logger.info(f"Pozycja zamknięta: {order['id']}")
                    return True
            
            return True
            
        except Exception as e:
            logger.error(f"Błąd zamykania pozycji: {e}")
            return False

    async def _execute_notify_action(self, rule_name: str, action: Dict) -> bool:
        """Wykonanie akcji powiadomienia"""
        try:
            message = action.get('message', f"Reguła '{rule_name}' została aktywowana")
            logger.info(f"Powiadomienie: {message}")
            return True
            
        except Exception as e:
            logger.error(f"Błąd wysyłania powiadomienia: {e}")
            return False

    async def _update_statistics(self):
        """Aktualizacja statystyk"""
        try:
            self.statistics.total_rules = len(self.custom_rules)
            self.statistics.enabled_rules = len([r for r in self.custom_rules if r.enabled])
            
        except Exception as e:
            logger.error(f"Błąd aktualizacji statystyk: {e}")

    async def _save_state(self):
        """Zapisanie stanu strategii"""
        try:
            if not self.db_manager:
                return
            
            state = {
                'custom_rules': [asdict(rule) for rule in self.custom_rules],
                'check_interval': self.check_interval,
                'statistics': asdict(self.statistics),
                'last_indicator_values': self.last_indicator_values,
                'price_history': list(self.price_history),
                'volume_history': list(self.volume_history)
            }
            
            # Zapisanie do bazy danych (placeholder)
            # await self.db_manager.save_strategy_state('custom', self.pair, state)
            
            logger.info("Stan Custom Strategy zapisany")
            
        except Exception as e:
            logger.error(f"Błąd zapisywania stanu: {e}")

    def get_status(self) -> Dict:
        """Pobranie statusu strategii"""
        return {
            'status': self.status.value,
            'pair': self.pair,
            'is_running': self.is_running,
            'is_paused': self.is_paused,
            'total_rules': len(self.custom_rules),
            'enabled_rules': len([r for r in self.custom_rules if r.enabled]),
            'check_interval': self.check_interval,
            'last_rule_triggered': self.statistics.last_rule_triggered,
            'last_action_time': self.statistics.last_action_time.isoformat() if self.statistics.last_action_time else None
        }

    def get_statistics(self) -> Dict:
        """Pobranie statystyk strategii"""
        stats_dict = asdict(self.statistics)
        
        # Konwersja datetime do string
        if stats_dict['last_action_time']:
            stats_dict['last_action_time'] = stats_dict['last_action_time'].isoformat()
        
        return {
            'strategy_type': 'custom',
            'pair': self.pair,
            'available_indicators': list(self.available_indicators.keys()),
            'available_operators': list(self.available_operators.keys()),
            **stats_dict
        }

    async def update_parameters(self, **kwargs):
        """Aktualizacja parametrów strategii"""
        try:
            if 'custom_rules' in kwargs:
                self.custom_rules = [CustomRule(**rule) for rule in kwargs['custom_rules']]
                self._initialize_rule_statistics()
            
            if 'check_interval' in kwargs:
                self.check_interval = kwargs['check_interval']
            
            logger.info("Parametry Custom Strategy zaktualizowane")
            
        except Exception as e:
            logger.error(f"Błąd aktualizacji parametrów: {e}")

    # Metody zarządzania regułami
    def add_rule(self, rule_dict: Dict):
        """Dodanie nowej reguły"""
        rule = CustomRule(**rule_dict)
        self.custom_rules.append(rule)
        
        self.statistics.rules_performance[rule.name] = {
            'triggered': 0,
            'successful': 0,
            'failed': 0,
            'profit': 0.0
        }

    def remove_rule(self, rule_name: str):
        """Usunięcie reguły"""
        self.custom_rules = [r for r in self.custom_rules if r.name != rule_name]
        self.statistics.rules_performance.pop(rule_name, None)

    def enable_rule(self, rule_name: str):
        """Włączenie reguły"""
        for rule in self.custom_rules:
            if rule.name == rule_name:
                rule.enabled = True
                break

    def disable_rule(self, rule_name: str):
        """Wyłączenie reguły"""
        for rule in self.custom_rules:
            if rule.name == rule_name:
                rule.enabled = False
                break
"""
AI Trading Bot - Zaawansowany bot wykorzystujący machine learning
do automatycznego doboru strategii i maksymalizacji zysków
"""

import asyncio
import numpy as np
import pandas as pd
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple, Any
import json
import pickle
from dataclasses import dataclass
import logging

# Machine Learning imports
try:
    from sklearn.ensemble import RandomForestRegressor, GradientBoostingRegressor
    from sklearn.model_selection import train_test_split
    from sklearn.preprocessing import StandardScaler
    from sklearn.metrics import mean_squared_error
    import joblib
    ML_AVAILABLE = True
except ImportError:
    ML_AVAILABLE = False

from .base_bot import BaseBot
from .dca import DCAStrategy
from .grid import GridStrategy
from .scalping import ScalpingStrategy
from ..risk_management import RiskManager
from ..notifications import NotificationManager
from utils.logger import get_logger


@dataclass
class MarketCondition:
    """Warunki rynkowe"""
    volatility: float
    trend_strength: float
    volume_ratio: float
    rsi: float
    macd_signal: float
    bollinger_position: float
    market_sentiment: str  # 'bullish', 'bearish', 'neutral'
    
    
@dataclass
class StrategyPerformance:
    """Wydajność strategii"""
    strategy_name: str
    total_trades: int
    win_rate: float
    avg_profit: float
    max_drawdown: float
    sharpe_ratio: float
    last_updated: datetime


class AITradingBot(BaseBot):
    """
    Zaawansowany AI Trading Bot z machine learning
    
    Funkcje:
    - Automatyczny dobór strategii na podstawie warunków rynkowych
    - Uczenie maszynowe z historii transakcji
    - Dynamiczne zarządzanie ryzykiem
    - Analiza sentymentu rynku
    - Optymalizacja parametrów w czasie rzeczywistym
    """
    
    def __init__(self, bot_id: str, parameters: Dict[str, Any]):
        """
        Inicjalizacja AI Trading Bot
        
        Args:
            bot_id: Identyfikator bota
            parameters: Parametry strategii zawierające:
                - pair: Para handlowa (np. 'BTC/USDT')
                - budget: Budżet do inwestowania
                - risk_tolerance: Tolerancja ryzyka (0.01-0.1)
                - target_hourly_profit: Docelowy zysk godzinowy
                - inne parametry AI...
        """
        # Wyciągnij wymagane parametry dla BaseBot
        pair = parameters.get('pair', 'BTC/USDT')
        
        # Inicjalizuj z pustymi managerami - będą ustawione w initialize()
        super().__init__(pair, None, None, None, bot_id)
        
        # Przechowaj parametry
        self.bot_id = bot_id
        self.parameters = parameters
        
        # Exchange będzie ustawiony w initialize()
        self.exchange = None
        
        self.logger = get_logger(f"AIBot_{self.bot_id}")
        self.target_hourly_profit = parameters.get('target_hourly_profit', 2.0)  # $2/h
        self.max_budget = parameters.get('budget', 1000.0)
        self.risk_tolerance = parameters.get('risk_tolerance', 0.02)  # 2%
        
        # Strategie dostępne do wyboru
        self.available_strategies = {
            'dca': DCAStrategy,
            'grid': GridStrategy,
            'scalping': ScalpingStrategy
        }
        
        # Aktywne strategie
        self.active_strategies: Dict[str, BaseBot] = {}
        self.strategy_allocations: Dict[str, float] = {}
        
        # Machine Learning komponenty
        self.ml_model = None
        self.scaler = StandardScaler() if ML_AVAILABLE else None
        self.feature_columns = []
        
        # Dane historyczne
        self.market_history: List[MarketCondition] = []
        self.performance_history: List[StrategyPerformance] = []
        self.trade_history: List[Dict] = []
        
        # Analiza rynku
        self.current_market_condition: Optional[MarketCondition] = None
        self.last_analysis_time = None
        
        # Zarządzanie ryzykiem - użyj z BaseBot lub utwórz nowy
        if not self.risk_manager:
            self.risk_manager = RiskManager()
        self.daily_loss_limit = parameters.get('daily_loss_limit', 50.0)  # $50
        self.current_daily_pnl = 0.0
        
        # Powiadomienia - użyj z BaseBot lub utwórz nowy
        if not self.notification_manager:
            # Dla testów używamy prostej implementacji
            try:
                from ..notifications import NotificationManager
                from ..database import DatabaseManager
                from utils.encryption import EncryptionManager
                
                # Tymczasowe managery dla testów
                temp_db = DatabaseManager()
                temp_encryption = EncryptionManager()
                self.notification_manager = NotificationManager(temp_db, temp_encryption)
            except ImportError:
                # Fallback - prosta implementacja
                self.notification_manager = None
        
        # Ustawienia uczenia
        self.learning_enabled = True
        self.retrain_interval = timedelta(hours=6)
        self.last_retrain_time = None
        self.learning_rate = parameters.get('learning_rate', 0.001)
        self.model_update_frequency = parameters.get('model_update_frequency', 100)  # co 100 transakcji
        self.use_reinforcement_learning = parameters.get('use_reinforcement_learning', False)
        
        # Feature engineering
        self.feature_engineering_enabled = parameters.get('feature_engineering_enabled', True)
        self.sentiment_analysis_enabled = parameters.get('sentiment_analysis_enabled', False)
        self.ensemble_models = parameters.get('ensemble_models', False)
        
        # Status
        self.last_trade_time = None
        self.total_trades = 0
        self.successful_trades = 0
        
        self.logger.info(f"AI Trading Bot zainicjalizowany - cel: ${self.target_hourly_profit}/h")
    
    async def initialize(self, db_manager, risk_manager, exchange, data_manager=None):
        """
        Inicjalizuje AI Trading Bot z komponentami systemu
        
        Args:
            db_manager: Manager bazy danych
            risk_manager: Manager zarządzania ryzykiem
            exchange: Adapter giełdy
            data_manager: Manager danych (opcjonalny)
        """
        try:
            # Ustaw managery
            self.db_manager = db_manager
            self.risk_manager = risk_manager
            self.exchange = exchange
            self.data_manager = data_manager
            
            # Aktualizuj atrybuty BaseBot bez wywoływania konstruktora ponownie
            self.notification_manager = self.notification_manager or None
            
            self.logger.info("Inicjalizacja AI Trading Bot...")
            
            # Załaduj historyczne dane
            await self._load_historical_data()
            
            # Zainicjalizuj model ML
            if ML_AVAILABLE:
                await self._initialize_ml_model()
            else:
                self.logger.warning("Biblioteki ML niedostępne - używanie uproszczonej logiki")
            
            # Przeprowadź początkową analizę rynku
            await self._analyze_market_conditions()
            
            # Wybierz początkowe strategie
            await self._select_initial_strategies()
            
            self.logger.info(f"AI Trading Bot zainicjalizowany pomyślnie dla {self.parameters['pair']} z giełdą {exchange.__class__.__name__}")
            return True
            
        except Exception as e:
            self.logger.error(f"Błąd inicjalizacji AI bota: {e}")
            return False
    
    async def start(self):
        """Uruchomienie AI bota"""
        try:
            self.logger.info("Uruchamianie AI Trading Bot...")
            self.is_running = True
            
            # Główna pętla AI bota
            while self.is_running:
                try:
                    # Analiza warunków rynkowych
                    await self._analyze_market_conditions()
                    
                    # Ocena wydajności aktywnych strategii
                    await self._evaluate_strategy_performance()
                    
                    # Optymalizacja alokacji budżetu
                    await self._optimize_budget_allocation()
                    
                    # Sprawdzenie czy potrzeba zmiany strategii
                    await self._check_strategy_changes()
                    
                    # Zarządzanie ryzykiem
                    await self._manage_risk()
                    
                    # Uczenie modelu (jeśli czas)
                    if self._should_retrain_model():
                        await self._retrain_model()
                    
                    # Raportowanie postępów
                    await self._report_progress()
                    
                    # Czekaj przed następną iteracją
                    await asyncio.sleep(60)  # Analiza co minutę
                    
                except Exception as e:
                    self.logger.error(f"Błąd w głównej pętli AI bota: {e}")
                    await asyncio.sleep(30)
                    
        except Exception as e:
            self.logger.error(f"Krytyczny błąd AI bota: {e}")
        finally:
            await self.stop()
    
    async def _analyze_market_conditions(self) -> MarketCondition:
        """Analiza aktualnych warunków rynkowych"""
        try:
            pair = self.parameters['pair']
            
            # Pobierz dane OHLCV
            ohlcv_data = await self.exchange.get_ohlcv(pair, '1h', limit=100)
            if not ohlcv_data:
                return self.current_market_condition
            
            df = pd.DataFrame(ohlcv_data, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
            
            # Oblicz wskaźniki techniczne
            volatility = self._calculate_volatility(df)
            trend_strength = self._calculate_trend_strength(df)
            volume_ratio = self._calculate_volume_ratio(df)
            rsi = self._calculate_rsi(df)
            macd_signal = self._calculate_macd(df)
            bollinger_position = self._calculate_bollinger_position(df)
            market_sentiment = self._analyze_sentiment(df)
            
            # Utwórz obiekt warunków rynkowych
            market_condition = MarketCondition(
                volatility=volatility,
                trend_strength=trend_strength,
                volume_ratio=volume_ratio,
                rsi=rsi,
                macd_signal=macd_signal,
                bollinger_position=bollinger_position,
                market_sentiment=market_sentiment
            )
            
            self.current_market_condition = market_condition
            self.market_history.append(market_condition)
            
            # Ogranicz historię do ostatnich 1000 zapisów
            if len(self.market_history) > 1000:
                self.market_history = self.market_history[-1000:]
            
            self.last_analysis_time = datetime.now()
            
            self.logger.debug(f"Warunki rynkowe: volatility={volatility:.4f}, trend={trend_strength:.4f}, sentiment={market_sentiment}")
            
            return market_condition
            
        except Exception as e:
            self.logger.error(f"Błąd analizy warunków rynkowych: {e}")
            return self.current_market_condition
    
    def _calculate_volatility(self, df: pd.DataFrame) -> float:
        """Oblicz zmienność rynku"""
        if len(df) < 20:
            return 0.0
        
        returns = df['close'].pct_change().dropna()
        return float(returns.std() * np.sqrt(24))  # Annualized volatility
    
    def _calculate_trend_strength(self, df: pd.DataFrame) -> float:
        """Oblicz siłę trendu"""
        if len(df) < 20:
            return 0.0
        
        # Użyj EMA do określenia trendu
        ema_short = df['close'].ewm(span=12).mean()
        ema_long = df['close'].ewm(span=26).mean()
        
        trend_diff = (ema_short.iloc[-1] - ema_long.iloc[-1]) / ema_long.iloc[-1]
        return float(np.tanh(trend_diff * 10))  # Normalizacja do [-1, 1]
    
    def _calculate_volume_ratio(self, df: pd.DataFrame) -> float:
        """Oblicz stosunek wolumenu"""
        if len(df) < 20:
            return 1.0
        
        current_volume = df['volume'].iloc[-1]
        avg_volume = df['volume'].rolling(20).mean().iloc[-1]
        
        return float(current_volume / avg_volume) if avg_volume > 0 else 1.0
    
    def _calculate_rsi(self, df: pd.DataFrame, period: int = 14) -> float:
        """Oblicz RSI"""
        if len(df) < period + 1:
            return 50.0
        
        delta = df['close'].diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=period).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=period).mean()
        
        rs = gain / loss
        rsi = 100 - (100 / (1 + rs))
        
        return float(rsi.iloc[-1]) if not np.isnan(rsi.iloc[-1]) else 50.0
    
    def _calculate_macd(self, df: pd.DataFrame) -> float:
        """Oblicz MACD signal"""
        if len(df) < 26:
            return 0.0
        
        ema_12 = df['close'].ewm(span=12).mean()
        ema_26 = df['close'].ewm(span=26).mean()
        macd = ema_12 - ema_26
        signal = macd.ewm(span=9).mean()
        
        return float(macd.iloc[-1] - signal.iloc[-1])
    
    def _calculate_bollinger_position(self, df: pd.DataFrame, period: int = 20) -> float:
        """Oblicz pozycję w pasmach Bollingera"""
        if len(df) < period:
            return 0.5
        
        sma = df['close'].rolling(period).mean()
        std = df['close'].rolling(period).std()
        
        upper_band = sma + (2 * std)
        lower_band = sma - (2 * std)
        
        current_price = df['close'].iloc[-1]
        band_width = upper_band.iloc[-1] - lower_band.iloc[-1]
        
        if band_width == 0:
            return 0.5
        
        position = (current_price - lower_band.iloc[-1]) / band_width
        return float(np.clip(position, 0, 1))
    
    def _analyze_sentiment(self, df: pd.DataFrame) -> str:
        """Analiza sentymentu rynku"""
        if len(df) < 10:
            return 'neutral'
        
        # Prosta analiza na podstawie ostatnich świec
        recent_closes = df['close'].tail(10)
        price_change = (recent_closes.iloc[-1] - recent_closes.iloc[0]) / recent_closes.iloc[0]
        
        if price_change > 0.02:  # +2%
            return 'bullish'
        elif price_change < -0.02:  # -2%
            return 'bearish'
        else:
            return 'neutral'
    
    async def _select_initial_strategies(self):
        """Wybór początkowych strategii na podstawie warunków rynkowych"""
        try:
            if not self.current_market_condition:
                await self._analyze_market_conditions()
            
            # Logika wyboru strategii na podstawie warunków rynkowych
            selected_strategies = self._determine_best_strategies(self.current_market_condition)
            
            # Alokacja budżetu między strategie
            total_allocation = 0.0
            for strategy_name, allocation in selected_strategies.items():
                if total_allocation + allocation <= 1.0:
                    await self._activate_strategy(strategy_name, allocation)
                    total_allocation += allocation
            
            self.logger.info(f"Aktywowano strategie: {list(self.active_strategies.keys())}")
            
        except Exception as e:
            self.logger.error(f"Błąd wyboru początkowych strategii: {e}")
    
    def _determine_best_strategies(self, market_condition: MarketCondition) -> Dict[str, float]:
        """Określ najlepsze strategie dla aktualnych warunków rynkowych"""
        strategies = {}
        
        # Logika wyboru na podstawie warunków rynkowych
        if market_condition.market_sentiment == 'bullish' and market_condition.trend_strength > 0.3:
            # Silny trend wzrostowy - DCA i Grid
            strategies['dca'] = 0.4
            strategies['grid'] = 0.3
            if market_condition.volatility > 0.02:
                strategies['scalping'] = 0.3
        
        elif market_condition.market_sentiment == 'bearish' and market_condition.trend_strength < -0.3:
            # Silny trend spadkowy - ostrożnie
            strategies['grid'] = 0.5
            if market_condition.volatility > 0.03:
                strategies['scalping'] = 0.5
        
        elif market_condition.volatility > 0.03:
            # Wysoka zmienność - scalping
            strategies['scalping'] = 0.6
            strategies['grid'] = 0.4
        
        else:
            # Neutralny rynek - DCA i Grid
            strategies['dca'] = 0.5
            strategies['grid'] = 0.5
        
        return strategies
    
    async def _activate_strategy(self, strategy_name: str, allocation: float):
        """Aktywuj strategię z określoną alokacją budżetu"""
        try:
            if strategy_name not in self.available_strategies:
                self.logger.error(f"Nieznana strategia: {strategy_name}")
                return
            
            # Oblicz budżet dla strategii
            strategy_budget = self.max_budget * allocation
            
            # Parametry strategii na podstawie warunków rynkowych
            strategy_params = self._get_strategy_parameters(strategy_name, strategy_budget)
            
            # Utwórz instancję strategii
            strategy_class = self.available_strategies[strategy_name]
            strategy_instance = strategy_class(self.exchange, strategy_params)
            
            # Zainicjalizuj strategię
            if await strategy_instance.initialize():
                self.active_strategies[strategy_name] = strategy_instance
                self.strategy_allocations[strategy_name] = allocation
                
                # Uruchom strategię w tle
                asyncio.create_task(strategy_instance.start())
                
                self.logger.info(f"Aktywowano strategię {strategy_name} z budżetem ${strategy_budget:.2f}")
            else:
                self.logger.error(f"Nie udało się zainicjalizować strategii {strategy_name}")
                
        except Exception as e:
            self.logger.error(f"Błąd aktywacji strategii {strategy_name}: {e}")
    
    def _get_strategy_parameters(self, strategy_name: str, budget: float) -> Dict[str, Any]:
        """Pobierz parametry strategii dostosowane do warunków rynkowych"""
        base_params = {
            'pair': self.parameters['pair'],
            'budget': budget,
            'exchange': self.exchange.name if hasattr(self.exchange, 'name') else 'unknown'
        }
        
        if strategy_name == 'dca':
            return {
                **base_params,
                'amount_per_order': min(budget * 0.1, 50.0),  # 10% budżetu lub max $50
                'interval_hours': 1,  # Co godzinę dla szybkich zysków
                'stop_loss_percent': 5.0,
                'take_profit_percent': 3.0,  # Niższy take profit dla częstszych transakcji
                'max_orders': int(budget / 10)  # Max orders based on budget
            }
        
        elif strategy_name == 'grid':
            return {
                **base_params,
                'grid_levels': min(int(budget / 20), 20),  # Więcej poziomów dla większego budżetu
                'grid_spacing_percent': 0.5,  # 0.5% między poziomami
                'stop_loss_percent': 8.0,
                'take_profit_percent': 15.0
            }
        
        elif strategy_name == 'scalping':
            return {
                **base_params,
                'timeframe': '1m',  # 1-minutowe świece dla szybkiego scalpingu
                'rsi_oversold': 30,
                'rsi_overbought': 70,
                'profit_target_percent': 0.5,  # 0.5% profit target
                'stop_loss_percent': 0.3,  # 0.3% stop loss
                'max_positions': 3
            }
        
        return base_params
    
    async def _evaluate_strategy_performance(self):
        """Ocena wydajności aktywnych strategii"""
        try:
            for strategy_name, strategy in self.active_strategies.items():
                if hasattr(strategy, 'statistics') and strategy.statistics:
                    stats = strategy.statistics
                    
                    # Oblicz metryki wydajności
                    total_trades = getattr(stats, 'total_trades', 0)
                    win_rate = getattr(stats, 'win_rate', 0.0)
                    total_profit = getattr(stats, 'total_profit', 0.0)
                    max_drawdown = getattr(stats, 'max_drawdown', 0.0)
                    
                    # Oblicz Sharpe ratio (uproszczona wersja)
                    sharpe_ratio = self._calculate_sharpe_ratio(strategy)
                    
                    # Zapisz wydajność
                    performance = StrategyPerformance(
                        strategy_name=strategy_name,
                        total_trades=total_trades,
                        win_rate=win_rate,
                        avg_profit=total_profit / max(total_trades, 1),
                        max_drawdown=max_drawdown,
                        sharpe_ratio=sharpe_ratio,
                        last_updated=datetime.now()
                    )
                    
                    # Aktualizuj historię wydajności
                    self._update_performance_history(performance)
                    
        except Exception as e:
            self.logger.error(f"Błąd oceny wydajności strategii: {e}")
    
    def _calculate_sharpe_ratio(self, strategy) -> float:
        """Oblicz uproszczony Sharpe ratio"""
        try:
            if not hasattr(strategy, 'trade_history') or len(strategy.trade_history) < 2:
                return 0.0
            
            # Pobierz zwroty z transakcji
            returns = [trade.get('profit_percent', 0.0) for trade in strategy.trade_history[-30:]]  # Ostatnie 30 transakcji
            
            if not returns:
                return 0.0
            
            mean_return = np.mean(returns)
            std_return = np.std(returns)
            
            return mean_return / std_return if std_return > 0 else 0.0
            
        except Exception:
            return 0.0
    
    def _update_performance_history(self, performance: StrategyPerformance):
        """Aktualizuj historię wydajności"""
        # Usuń starsze wpisy dla tej samej strategii
        self.performance_history = [p for p in self.performance_history 
                                  if p.strategy_name != performance.strategy_name]
        
        # Dodaj nowy wpis
        self.performance_history.append(performance)
        
        # Ogranicz historię
        if len(self.performance_history) > 100:
            self.performance_history = self.performance_history[-100:]
    
    async def _optimize_budget_allocation(self):
        """Optymalizacja alokacji budżetu między strategie"""
        try:
            if len(self.performance_history) < 2:
                return
            
            # Znajdź najlepiej działające strategie
            best_performers = sorted(self.performance_history, 
                                   key=lambda x: x.sharpe_ratio, reverse=True)
            
            # Realokuj budżet na podstawie wydajności
            new_allocations = {}
            total_allocation = 0.0
            
            for i, performance in enumerate(best_performers[:3]):  # Top 3 strategie
                if performance.win_rate > 0.6 and performance.sharpe_ratio > 0.5:
                    # Przydziel więcej budżetu lepszym strategiom
                    allocation = max(0.2, 0.5 - i * 0.15)
                    if total_allocation + allocation <= 1.0:
                        new_allocations[performance.strategy_name] = allocation
                        total_allocation += allocation
            
            # Zastosuj nowe alokacje
            await self._apply_new_allocations(new_allocations)
            
        except Exception as e:
            self.logger.error(f"Błąd optymalizacji alokacji budżetu: {e}")
    
    async def _apply_new_allocations(self, new_allocations: Dict[str, float]):
        """Zastosuj nowe alokacje budżetu"""
        try:
            for strategy_name, new_allocation in new_allocations.items():
                current_allocation = self.strategy_allocations.get(strategy_name, 0.0)
                
                # Jeśli zmiana jest znacząca (>10%)
                if abs(new_allocation - current_allocation) > 0.1:
                    self.logger.info(f"Zmiana alokacji {strategy_name}: {current_allocation:.2f} -> {new_allocation:.2f}")
                    
                    # Aktualizuj alokację
                    self.strategy_allocations[strategy_name] = new_allocation
                    
                    # Jeśli strategia jest aktywna, zaktualizuj jej budżet
                    if strategy_name in self.active_strategies:
                        strategy = self.active_strategies[strategy_name]
                        new_budget = self.max_budget * new_allocation
                        
                        # Zaktualizuj budżet strategii (jeśli ma taką metodę)
                        if hasattr(strategy, 'update_budget'):
                            await strategy.update_budget(new_budget)
                            
        except Exception as e:
            self.logger.error(f"Błąd zastosowania nowych alokacji: {e}")
    
    async def _check_strategy_changes(self):
        """Sprawdź czy potrzeba zmienić strategie"""
        try:
            # Sprawdź czy warunki rynkowe się zmieniły znacząco
            if self._market_conditions_changed():
                self.logger.info("Wykryto znaczące zmiany warunków rynkowych")
                
                # Określ nowe optymalne strategie
                new_strategies = self._determine_best_strategies(self.current_market_condition)
                
                # Porównaj z aktualnymi strategiami
                current_strategies = set(self.active_strategies.keys())
                new_strategy_names = set(new_strategies.keys())
                
                # Strategie do usunięcia
                to_remove = current_strategies - new_strategy_names
                # Strategie do dodania
                to_add = new_strategy_names - current_strategies
                
                # Usuń nieoptymalne strategie
                for strategy_name in to_remove:
                    await self._deactivate_strategy(strategy_name)
                
                # Dodaj nowe strategie
                for strategy_name in to_add:
                    allocation = new_strategies[strategy_name]
                    await self._activate_strategy(strategy_name, allocation)
                    
        except Exception as e:
            self.logger.error(f"Błąd sprawdzania zmian strategii: {e}")
    
    def _market_conditions_changed(self) -> bool:
        """Sprawdź czy warunki rynkowe zmieniły się znacząco"""
        if len(self.market_history) < 10:
            return False
        
        # Porównaj ostatnie warunki z średnią z ostatnich 10 pomiarów
        recent_conditions = self.market_history[-10:]
        current = self.current_market_condition
        
        avg_volatility = np.mean([c.volatility for c in recent_conditions])
        avg_trend = np.mean([c.trend_strength for c in recent_conditions])
        
        # Sprawdź znaczące zmiany
        volatility_change = abs(current.volatility - avg_volatility) > 0.01
        trend_change = abs(current.trend_strength - avg_trend) > 0.2
        
        return volatility_change or trend_change
    
    async def _deactivate_strategy(self, strategy_name: str):
        """Dezaktywuj strategię"""
        try:
            if strategy_name in self.active_strategies:
                strategy = self.active_strategies[strategy_name]
                
                # Zatrzymaj strategię
                if hasattr(strategy, 'stop'):
                    await strategy.stop()
                
                # Usuń z aktywnych strategii
                del self.active_strategies[strategy_name]
                del self.strategy_allocations[strategy_name]
                
                self.logger.info(f"Dezaktywowano strategię: {strategy_name}")
                
        except Exception as e:
            self.logger.error(f"Błąd dezaktywacji strategii {strategy_name}: {e}")
    
    async def _manage_risk(self):
        """Zarządzanie ryzykiem"""
        try:
            # Sprawdź dzienny P&L
            daily_pnl = await self._calculate_daily_pnl()
            
            if daily_pnl < -self.daily_loss_limit:
                self.logger.warning(f"Osiągnięto dzienny limit strat: ${daily_pnl:.2f}")
                await self._emergency_stop()
                return
            
            # Sprawdź wydajność każdej strategii
            for strategy_name, strategy in self.active_strategies.items():
                if hasattr(strategy, 'statistics') and strategy.statistics:
                    # Jeśli strategia ma zbyt duże straty, zatrzymaj ją
                    if getattr(strategy.statistics, 'total_profit', 0) < -100:  # $100 strata
                        self.logger.warning(f"Strategia {strategy_name} ma duże straty - zatrzymywanie")
                        await self._deactivate_strategy(strategy_name)
                        
        except Exception as e:
            self.logger.error(f"Błąd zarządzania ryzykiem: {e}")
    
    async def _calculate_daily_pnl(self) -> float:
        """Oblicz dzienny P&L"""
        try:
            total_pnl = 0.0
            
            for strategy in self.active_strategies.values():
                if hasattr(strategy, 'statistics') and strategy.statistics:
                    strategy_pnl = getattr(strategy.statistics, 'total_profit', 0.0)
                    total_pnl += strategy_pnl
            
            return total_pnl
            
        except Exception as e:
            self.logger.error(f"Błąd obliczania dziennego P&L: {e}")
            return 0.0
    
    async def _emergency_stop(self):
        """Awaryjne zatrzymanie wszystkich strategii"""
        try:
            self.logger.critical("AWARYJNE ZATRZYMANIE - osiągnięto limit strat")
            
            # Zatrzymaj wszystkie strategie
            for strategy_name in list(self.active_strategies.keys()):
                await self._deactivate_strategy(strategy_name)
            
            # Wyślij powiadomienie
            await self.notification_manager.send_notification(
                "🚨 AWARYJNE ZATRZYMANIE AI BOTA",
                f"Bot został zatrzymany z powodu przekroczenia limitu strat: ${self.daily_loss_limit}"
            )
            
            # Zatrzymaj główną pętlę
            self.is_running = False
            
        except Exception as e:
            self.logger.error(f"Błąd awaryjnego zatrzymania: {e}")
    
    def _should_retrain_model(self) -> bool:
        """Sprawdź czy czas na ponowne trenowanie modelu"""
        if not ML_AVAILABLE or not self.learning_enabled:
            return False
        
        if self.last_retrain_time is None:
            return len(self.market_history) > 50  # Minimum danych do trenowania
        
        return datetime.now() - self.last_retrain_time > self.retrain_interval
    
    async def _retrain_model(self):
        """Ponowne trenowanie modelu ML"""
        try:
            if not ML_AVAILABLE:
                return
            
            self.logger.info("Rozpoczynam ponowne trenowanie modelu ML...")
            
            # Przygotuj dane treningowe
            X, y = self._prepare_training_data()
            
            if len(X) < 20:  # Minimum danych
                self.logger.warning("Za mało danych do trenowania modelu")
                return
            
            # Podziel dane na treningowe i testowe
            X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42)
            
            # Normalizacja danych
            X_train_scaled = self.scaler.fit_transform(X_train)
            X_test_scaled = self.scaler.transform(X_test)
            
            # Trenowanie modelu
            self.ml_model = GradientBoostingRegressor(n_estimators=100, random_state=42)
            self.ml_model.fit(X_train_scaled, y_train)
            
            # Ocena modelu
            y_pred = self.ml_model.predict(X_test_scaled)
            mse = mean_squared_error(y_test, y_pred)
            
            self.logger.info(f"Model przeszkolony - MSE: {mse:.4f}")
            
            # Zapisz model
            await self._save_model()
            
            self.last_retrain_time = datetime.now()
            
        except Exception as e:
            self.logger.error(f"Błąd trenowania modelu: {e}")
    
    def _prepare_training_data(self) -> Tuple[np.ndarray, np.ndarray]:
        """Przygotuj dane treningowe dla modelu ML"""
        try:
            features = []
            targets = []
            
            # Użyj historii warunków rynkowych i wydajności strategii
            for i, market_condition in enumerate(self.market_history[:-1]):  # Bez ostatniego
                # Features: warunki rynkowe
                feature_vector = [
                    market_condition.volatility,
                    market_condition.trend_strength,
                    market_condition.volume_ratio,
                    market_condition.rsi / 100.0,  # Normalizacja
                    market_condition.macd_signal,
                    market_condition.bollinger_position,
                    1.0 if market_condition.market_sentiment == 'bullish' else 
                    -1.0 if market_condition.market_sentiment == 'bearish' else 0.0
                ]
                
                # Target: przyszła rentowność (uproszczona)
                if i < len(self.market_history) - 1:
                    next_condition = self.market_history[i + 1]
                    # Prosta metrika: zmiana trendu jako target
                    target = next_condition.trend_strength - market_condition.trend_strength
                    
                    features.append(feature_vector)
                    targets.append(target)
            
            self.feature_columns = [
                'volatility', 'trend_strength', 'volume_ratio', 'rsi_norm', 
                'macd_signal', 'bollinger_position', 'sentiment_score'
            ]
            
            return np.array(features), np.array(targets)
            
        except Exception as e:
            self.logger.error(f"Błąd przygotowania danych treningowych: {e}")
            return np.array([]), np.array([])
    
    async def _save_model(self):
        """Zapisz model ML do pliku"""
        try:
            model_data = {
                'model': self.ml_model,
                'scaler': self.scaler,
                'feature_columns': self.feature_columns,
                'last_updated': datetime.now()
            }
            
            model_path = f"data/ai_model_{self.bot_id}.pkl"
            joblib.dump(model_data, model_path)
            
            self.logger.info(f"Model zapisany: {model_path}")
            
        except Exception as e:
            self.logger.error(f"Błąd zapisywania modelu: {e}")
    
    async def _load_historical_data(self):
        """Załaduj historyczne dane"""
        try:
            # Załaduj model jeśli istnieje
            model_path = f"data/ai_model_{self.bot_id}.pkl"
            try:
                model_data = joblib.load(model_path)
                self.ml_model = model_data['model']
                self.scaler = model_data['scaler']
                self.feature_columns = model_data['feature_columns']
                self.logger.info("Załadowano zapisany model ML")
            except FileNotFoundError:
                self.logger.info("Brak zapisanego modelu - zostanie utworzony nowy")
            
        except Exception as e:
            self.logger.error(f"Błąd ładowania danych historycznych: {e}")
    
    async def _initialize_ml_model(self):
        """Inicjalizacja modelu ML"""
        try:
            if self.ml_model is None:
                # Utwórz nowy model
                self.ml_model = GradientBoostingRegressor(n_estimators=50, random_state=42)
                self.logger.info("Utworzono nowy model ML")
            
        except Exception as e:
            self.logger.error(f"Błąd inicjalizacji modelu ML: {e}")
    
    async def _report_progress(self):
        """Raportowanie postępów"""
        try:
            # Oblicz aktualny P&L
            current_pnl = await self._calculate_daily_pnl()
            
            # Oblicz zysk na godzinę
            if hasattr(self, 'start_time'):
                hours_running = (datetime.now() - self.start_time).total_seconds() / 3600
                hourly_profit = current_pnl / max(hours_running, 0.1)
            else:
                hourly_profit = 0.0
                self.start_time = datetime.now()
            
            # Loguj postęp co 15 minut
            if not hasattr(self, 'last_report_time') or \
               datetime.now() - self.last_report_time > timedelta(minutes=15):
                
                self.logger.info(
                    f"AI Bot Status - P&L: ${current_pnl:.2f}, "
                    f"Zysk/h: ${hourly_profit:.2f}, "
                    f"Cel: ${self.target_hourly_profit:.2f}/h, "
                    f"Aktywne strategie: {len(self.active_strategies)}"
                )
                
                # Wyślij powiadomienie jeśli osiągnięto cel
                if hourly_profit >= self.target_hourly_profit:
                    await self.notification_manager.send_notification(
                        "🎯 CEL OSIĄGNIĘTY!",
                        f"AI Bot osiągnął cel ${self.target_hourly_profit}/h! "
                        f"Aktualny zysk: ${hourly_profit:.2f}/h"
                    )
                
                self.last_report_time = datetime.now()
                
        except Exception as e:
            self.logger.error(f"Błąd raportowania postępów: {e}")
    
    async def stop(self):
        """Zatrzymanie AI bota"""
        try:
            self.logger.info("Zatrzymywanie AI Trading Bot...")
            self.is_running = False
            
            # Zatrzymaj wszystkie aktywne strategie
            for strategy_name in list(self.active_strategies.keys()):
                await self._deactivate_strategy(strategy_name)
            
            # Zapisz model jeśli został wytrenowany
            if self.ml_model is not None:
                await self._save_model()
            
            self.logger.info("AI Trading Bot zatrzymany")
            
        except Exception as e:
            self.logger.error(f"Błąd zatrzymywania AI bota: {e}")
    
    async def get_status(self) -> Dict[str, Any]:
        """Pobierz status AI bota"""
        try:
            current_pnl = await self._calculate_daily_pnl()
            
            return {
                'bot_id': self.bot_id,
                'is_running': self.is_running,
                'target_hourly_profit': self.target_hourly_profit,
                'current_pnl': current_pnl,
                'active_strategies': list(self.active_strategies.keys()),
                'strategy_allocations': self.strategy_allocations,
                'market_condition': {
                    'volatility': self.current_market_condition.volatility if self.current_market_condition else 0,
                    'trend_strength': self.current_market_condition.trend_strength if self.current_market_condition else 0,
                    'sentiment': self.current_market_condition.market_sentiment if self.current_market_condition else 'unknown'
                },
                'ml_model_trained': self.ml_model is not None,
                'last_analysis': self.last_analysis_time.isoformat() if self.last_analysis_time else None
            }
            
        except Exception as e:
            self.logger.error(f"Błąd pobierania statusu: {e}")
            return {'error': str(e)}
    
    async def run(self):
        """Główna pętla AI bota - implementacja abstrakcyjnej metody z BaseBot"""
        await self.start()
    
    async def get_statistics(self) -> Dict[str, Any]:
        """Pobranie statystyk AI bota - implementacja abstrakcyjnej metody z BaseBot"""
        try:
            current_pnl = await self._calculate_daily_pnl()
            
            # Oblicz łączne statystyki ze wszystkich aktywnych strategii
            total_trades = 0
            successful_trades = 0
            total_profit = 0.0
            
            for strategy in self.active_strategies.values():
                if hasattr(strategy, 'get_statistics'):
                    stats = await strategy.get_statistics()
                    total_trades += stats.get('total_trades', 0)
                    successful_trades += stats.get('successful_trades', 0)
                    total_profit += stats.get('total_profit', 0.0)
            
            win_rate = (successful_trades / total_trades * 100) if total_trades > 0 else 0.0
            
            return {
                'bot_id': self.bot_id,
                'bot_type': 'ai_trading',
                'is_running': self.is_running,
                'total_trades': total_trades,
                'successful_trades': successful_trades,
                'failed_trades': total_trades - successful_trades,
                'win_rate': win_rate,
                'total_profit': total_profit,
                'current_pnl': current_pnl,
                'target_hourly_profit': self.target_hourly_profit,
                'active_strategies_count': len(self.active_strategies),
                'active_strategies': list(self.active_strategies.keys()),
                'strategy_allocations': self.strategy_allocations,
                'ml_model_trained': self.ml_model is not None,
                'market_condition': self.current_market_condition.market_sentiment if self.current_market_condition else 'unknown',
                'last_analysis': self.last_analysis_time.isoformat() if self.last_analysis_time else None
            }
            
        except Exception as e:
            self.logger.error(f"Błąd pobierania statystyk: {e}")
            return {
                'bot_id': self.bot_id,
                'bot_type': 'ai_trading',
                'error': str(e),
                'total_trades': 0,
                'successful_trades': 0,
                'failed_trades': 0,
                'win_rate': 0.0,
                'total_profit': 0.0
            }
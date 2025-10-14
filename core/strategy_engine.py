"""
Strategy Engine - Pośredniczy między botami a TradingEngine

Wykonuje logikę strategii (DCA, Grid, Scalping) i zarządza sygnałami handlowymi.
Odbiera dane rynkowe z MarketDataManager i wysyła zlecenia do TradingEngine.
"""

import asyncio
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Callable
from dataclasses import dataclass, field, asdict, is_dataclass
from enum import Enum
import json

# Import komponentów systemu
from core.market_data_manager import MarketDataManager, PriceData
from core.trading_engine import TradingEngine, OrderRequest, OrderType, OrderSide
from core.updated_risk_manager import UpdatedRiskManager, TradeRiskAssessment
from core.strategy_base import BaseStrategy, StrategyConfig, TradingSignal, SignalType, StrategyState
from utils.logger import get_logger

# Import nowych strategii
try:
    from app.strategy.swing import SwingStrategy
    from app.strategy.arbitrage import ArbitrageStrategy
    from app.strategy.ai_strategy_adapter import AIStrategyAdapter, AIStrategyConfig
except ImportError as e:
    logging.warning(f"Nie można zaimportować nowych strategii: {e}")
    SwingStrategy = None
    ArbitrageStrategy = None
    AIStrategyAdapter = None

logger = get_logger("strategy_engine")

class StrategyType(Enum):
    """Typy strategii"""
    DCA = "dca"
    GRID = "grid"
    SCALPING = "scalping"
    CUSTOM = "custom"
    SWING = "swing"
    ARBITRAGE = "arbitrage"
    AI = "ai"

# Klasy zaimportowane z strategy_base.py

class DCAStrategy(BaseStrategy):
    """Strategia Dollar Cost Averaging"""
    
    def __init__(self, strategy_id: str, bot_id: str, config: StrategyConfig):
        super().__init__(strategy_id, bot_id, config)
        self.last_buy_time = None
        self.buy_interval = config.parameters.get('buy_interval_minutes', 60)
        self.price_drop_threshold = config.parameters.get('price_drop_threshold', 0.02)
        
    async def analyze_market(self, price_data: PriceData, market_data: Dict[str, Any]) -> Optional[TradingSignal]:
        """Logika DCA - kupuj regularnie lub przy spadkach"""
        try:
            current_time = datetime.now()
            
            # Sprawdź czy minął odpowiedni czas od ostatniego zakupu
            time_condition = (
                self.last_buy_time is None or 
                (current_time - self.last_buy_time).total_seconds() >= self.buy_interval * 60
            )
            
            # Sprawdź czy cena spadła wystarczająco
            price_condition = False
            if self.state.average_price > 0:
                price_drop = (self.state.average_price - price_data.price) / self.state.average_price
                price_condition = price_drop >= self.price_drop_threshold
            else:
                price_condition = True  # Pierwszy zakup
            
            # Sprawdź limity pozycji
            position_condition = self.state.current_position < self.config.max_position_size
            
            if (time_condition or price_condition) and position_condition:
                quantity = self.config.base_amount / price_data.price
                
                signal = TradingSignal(
                    signal_type=SignalType.BUY,
                    symbol=self.config.symbol,
                    price=price_data.price,
                    quantity=quantity,
                    strategy_id=self.strategy_id,
                    bot_id=self.bot_id,
                    confidence=0.8,
                    metadata={
                        'strategy_type': 'DCA',
                        'reason': 'time_interval' if time_condition else 'price_drop'
                    }
                )
                
                self.last_buy_time = current_time
                return signal
                
        except Exception as e:
            self.logger.error(f"Error in DCA analysis: {e}")
            
        return None

class GridStrategy(BaseStrategy):
    """Strategia Grid Trading"""
    
    def __init__(self, strategy_id: str, bot_id: str, config: StrategyConfig):
        super().__init__(strategy_id, bot_id, config)
        self.grid_levels = config.parameters.get('grid_levels', 10)
        self.grid_spacing = config.parameters.get('grid_spacing_percent', 0.01)
        self.base_price = config.parameters.get('base_price', 0.0)
        self.buy_orders = []
        self.sell_orders = []
        
    async def analyze_market(self, price_data: PriceData, market_data: Dict[str, Any]) -> Optional[TradingSignal]:
        """Logika Grid - umieszcza zlecenia na różnych poziomach"""
        try:
            if self.base_price == 0:
                self.base_price = price_data.price
                
            current_price = price_data.price
            
            # Sprawdź poziomy grid poniżej aktualnej ceny (zlecenia kupna)
            for i in range(1, self.grid_levels + 1):
                buy_price = self.base_price * (1 - self.grid_spacing * i)
                
                if current_price <= buy_price and not self._has_order_at_level(buy_price, 'buy'):
                    quantity = self.config.base_amount / buy_price
                    
                    return TradingSignal(
                        signal_type=SignalType.BUY,
                        symbol=self.config.symbol,
                        price=buy_price,
                        quantity=quantity,
                        strategy_id=self.strategy_id,
                        bot_id=self.bot_id,
                        confidence=0.7,
                        metadata={
                            'strategy_type': 'GRID',
                            'grid_level': i,
                            'order_type': 'limit'
                        }
                    )
            
            # Sprawdź poziomy grid powyżej aktualnej ceny (zlecenia sprzedaży)
            if self.state.current_position > 0:
                for i in range(1, self.grid_levels + 1):
                    sell_price = self.base_price * (1 + self.grid_spacing * i)
                    
                    if current_price >= sell_price and not self._has_order_at_level(sell_price, 'sell'):
                        quantity = min(self.state.current_position * 0.1, self.state.current_position)
                        
                        return TradingSignal(
                            signal_type=SignalType.SELL,
                            symbol=self.config.symbol,
                            price=sell_price,
                            quantity=quantity,
                            strategy_id=self.strategy_id,
                            bot_id=self.bot_id,
                            confidence=0.7,
                            metadata={
                                'strategy_type': 'GRID',
                                'grid_level': i,
                                'order_type': 'limit'
                            }
                        )
                        
        except Exception as e:
            self.logger.error(f"Error in Grid analysis: {e}")
            
        return None
    
    def _has_order_at_level(self, price: float, side: str) -> bool:
        """Sprawdza czy istnieje zlecenie na danym poziomie"""
        tolerance = max(price * 0.0001, 1e-8)

        # Najpierw sprawdź zlecenia zapamiętane w stanie strategii
        orders: List[Any] = getattr(self.state, "open_orders", [])
        for order in orders or []:
            order_side = getattr(order, "side", getattr(order, "order_side", None))
            if order_side and str(order_side).lower() != side.lower():
                continue

            status = str(getattr(order, "status", "pending")).lower()
            if status in {"cancelled", "canceled", "closed"}:
                continue

            try:
                order_price = float(getattr(order, "price", price))
            except Exception:
                order_price = price

            if abs(order_price - price) <= tolerance:
                return True

        # Jeżeli TradingEngine jest dostępny, spróbuj sprawdzić aktywne zlecenia na giełdzie
        try:
            if self.trading_engine and hasattr(self.trading_engine, "get_open_orders"):
                loop = asyncio.get_event_loop()
                if loop.is_running():
                    open_orders = self.trading_engine.get_cached_open_orders(self.config.symbol) if hasattr(self.trading_engine, "get_cached_open_orders") else []
                else:
                    open_orders = loop.run_until_complete(self.trading_engine.get_open_orders(self.config.symbol))

                for order in open_orders or []:
                    order_side = str(order.get('side') or order.get('type') or '').lower()
                    if order_side and order_side != side.lower():
                        continue
                    try:
                        order_price = float(order.get('price') or order.get('limit_price') or 0.0)
                    except Exception:
                        order_price = 0.0
                    if order_price and abs(order_price - price) <= tolerance:
                        status = str(order.get('status') or 'pending').lower()
                        if status not in {"cancelled", "canceled", "closed"}:
                            return True
        except Exception as exc:
            self.logger.debug(f"Falling back to local order cache in _has_order_at_level: {exc}")

        return False

class ScalpingStrategy(BaseStrategy):
    """Strategia Scalping"""
    
    def __init__(self, strategy_id: str, bot_id: str, config: StrategyConfig):
        super().__init__(strategy_id, bot_id, config)
        self.profit_target = config.parameters.get('profit_target_percent', 0.005)
        self.stop_loss = config.parameters.get('stop_loss_percent', 0.002)
        self.min_volume = config.parameters.get('min_volume', 1000000)
        self.price_history = []
        
    async def analyze_market(self, price_data: PriceData, market_data: Dict[str, Any]) -> Optional[TradingSignal]:
        """Logika Scalping - szybkie transakcje na małych ruchach"""
        try:
            self.price_history.append(price_data.price)
            if len(self.price_history) > 20:
                self.price_history.pop(0)
                
            if len(self.price_history) < 10:
                return None
                
            # Sprawdź wolumen
            volume = market_data.get('volume_24h', 0)
            if volume < self.min_volume:
                return None
                
            # Analiza momentum
            recent_prices = self.price_history[-5:]
            older_prices = self.price_history[-10:-5]
            
            recent_avg = sum(recent_prices) / len(recent_prices)
            older_avg = sum(older_prices) / len(older_prices)
            
            momentum = (recent_avg - older_avg) / older_avg
            
            # Sygnał kupna przy pozytywnym momentum
            if momentum > 0.001 and self.state.current_position == 0:
                quantity = self.config.base_amount / price_data.price
                
                return TradingSignal(
                    signal_type=SignalType.BUY,
                    symbol=self.config.symbol,
                    price=price_data.price,
                    quantity=quantity,
                    strategy_id=self.strategy_id,
                    bot_id=self.bot_id,
                    confidence=0.6,
                    metadata={
                        'strategy_type': 'SCALPING',
                        'momentum': momentum,
                        'entry_price': price_data.price
                    }
                )
            
            # Sygnał sprzedaży przy osiągnięciu celu lub stop loss
            elif self.state.current_position > 0:
                entry_price = self.state.metadata.get('entry_price', self.state.average_price)
                price_change = (price_data.price - entry_price) / entry_price
                
                if price_change >= self.profit_target or price_change <= -self.stop_loss:
                    return TradingSignal(
                        signal_type=SignalType.SELL,
                        symbol=self.config.symbol,
                        price=price_data.price,
                        quantity=self.state.current_position,
                        strategy_id=self.strategy_id,
                        bot_id=self.bot_id,
                        confidence=0.9,
                        metadata={
                            'strategy_type': 'SCALPING',
                            'reason': 'profit_target' if price_change >= self.profit_target else 'stop_loss',
                            'price_change': price_change
                        }
                    )
                    
        except Exception as e:
            self.logger.error(f"Error in Scalping analysis: {e}")
            
        return None

class StrategyEngine:
    """Główny silnik strategii"""
    
    def __init__(self, market_data_manager: MarketDataManager, 
                 trading_engine: TradingEngine, risk_manager: UpdatedRiskManager, db_manager=None):
        self.market_data_manager = market_data_manager
        self.trading_engine = trading_engine
        self.risk_manager = risk_manager
        self.db_manager = db_manager
        self.strategies: Dict[str, BaseStrategy] = {}
        self.active = False
        self.logger = get_logger("strategy_engine")
        
        # Callbacks dla UI
        self.signal_callbacks: List[Callable] = []
        self.execution_callbacks: List[Callable] = []
        
    async def initialize(self):
        """Inicjalizuje silnik strategii"""
        try:
            await self.market_data_manager.initialize()
            await self.trading_engine.initialize()
            self.logger.info("Strategy Engine initialized successfully")
            
        except Exception as e:
            self.logger.error(f"Failed to initialize Strategy Engine: {e}")
            raise
    
    def register_strategy(self, bot_id: str, config: StrategyConfig) -> str:
        """Rejestruje nową strategię"""
        try:
            strategy_id = f"{bot_id}_{config.strategy_type.value}_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
            
            if config.strategy_type == StrategyType.DCA:
                strategy = DCAStrategy(strategy_id, bot_id, config)
            elif config.strategy_type == StrategyType.GRID:
                strategy = GridStrategy(strategy_id, bot_id, config)
            elif config.strategy_type == StrategyType.SCALPING:
                strategy = ScalpingStrategy(strategy_id, bot_id, config)
            elif config.strategy_type == StrategyType.SWING:
                if SwingStrategy is None:
                    raise ValueError("Swing Strategy nie jest dostępna - sprawdź import")
                strategy = SwingStrategy(strategy_id, bot_id, config)
            elif config.strategy_type == StrategyType.ARBITRAGE:
                if ArbitrageStrategy is None:
                    raise ValueError("Arbitrage Strategy nie jest dostępna - sprawdź import")
                strategy = ArbitrageStrategy(strategy_id, bot_id, config)
            elif config.strategy_type == StrategyType.AI:
                if AIStrategyAdapter is None:
                    raise ValueError("AI Strategy nie jest dostępna - sprawdź import")
                # Konwertuj StrategyConfig na AIStrategyConfig jeśli potrzeba
                if isinstance(config, AIStrategyConfig):
                    ai_config = config
                else:
                    ai_config = AIStrategyConfig(
                        strategy_type=config.strategy_type,
                        symbol=config.symbol,
                        base_amount=config.base_amount,
                        max_position_size=config.max_position_size,
                        risk_percentage=config.risk_percentage,
                        parameters=config.parameters,
                        target_hourly_profit=config.parameters.get('target_hourly_profit', 2.0),
                        risk_tolerance=config.parameters.get('risk_tolerance', 0.02),
                        learning_enabled=config.parameters.get('learning_enabled', True),
                        use_reinforcement_learning=config.parameters.get('use_reinforcement_learning', False),
                        feature_engineering_enabled=config.parameters.get('feature_engineering_enabled', True),
                        sentiment_analysis_enabled=config.parameters.get('sentiment_analysis_enabled', False),
                        ensemble_models=config.parameters.get('ensemble_models', False),
                        learning_rate=config.parameters.get('learning_rate', 0.001),
                        model_update_frequency=config.parameters.get('model_update_frequency', 100),
                        daily_loss_limit=config.parameters.get('daily_loss_limit', 50.0)
                    )
                strategy = AIStrategyAdapter(strategy_id, bot_id, ai_config)
            else:
                raise ValueError(f"Unsupported strategy type: {config.strategy_type}")
            
            self.strategies[strategy_id] = strategy
            self.logger.info(f"Registered strategy {strategy_id} for bot {bot_id}")
            
            return strategy_id
            
        except Exception as e:
            self.logger.error(f"Failed to register strategy: {e}")
            raise
    
    def unregister_strategy(self, strategy_id: str):
        """Wyrejestrowuje strategię"""
        if strategy_id in self.strategies:
            del self.strategies[strategy_id]
            self.logger.info(f"Unregistered strategy {strategy_id}")
    
    async def start_strategy(self, strategy_id: str):
        """Uruchamia strategię"""
        if strategy_id in self.strategies:
            strategy = self.strategies[strategy_id]
            
            # Inicjalizuj AI Strategy jeśli potrzeba
            if isinstance(strategy, AIStrategyAdapter) and hasattr(strategy, 'initialize'):
                try:
                    # Przekaż potrzebne komponenty do AI Strategy
                    await strategy.initialize(self.db_manager, self.risk_manager, self.trading_engine.exchange)
                    self.logger.info(f"AI Strategy {strategy_id} zainicjalizowana")
                except Exception as e:
                    self.logger.error(f"Błąd inicjalizacji AI Strategy {strategy_id}: {e}")
                    return
            
            strategy.state.active = True
            
            # Subskrybuj dane rynkowe dla symbolu strategii
            symbol = strategy.config.symbol
            await self.market_data_manager.subscribe_to_price_feed(symbol, self._on_price_update)
            
            self.logger.info(f"Started strategy {strategy_id}")
    
    async def stop_strategy(self, strategy_id: str):
        """Zatrzymuje strategię"""
        if strategy_id in self.strategies:
            self.strategies[strategy_id].state.active = False
            self.logger.info(f"Stopped strategy {strategy_id}")
    
    async def _on_price_update(self, symbol: str, price_data: PriceData):
        """Obsługuje aktualizacje cen"""
        try:
            # Pobierz dodatkowe dane rynkowe
            market_data = await self.market_data_manager.get_market_data(symbol)
            
            # Przetwórz wszystkie aktywne strategie dla tego symbolu
            for strategy_id, strategy in self.strategies.items():
                if strategy.config.symbol == symbol and strategy.state.active:
                    # Aktualizuj stan strategii
                    await strategy.update_state(price_data)
                    
                    # Analizuj rynek i generuj sygnały
                    signal = await strategy.analyze_market(price_data, market_data)
                    
                    if signal:
                        # Powiadom UI o nowym sygnale
                        for callback in self.signal_callbacks:
                            try:
                                await callback(signal)
                            except Exception as e:
                                self.logger.error(f"Error in signal callback: {e}")
                        
                        # Wykonaj sygnał
                        await self._execute_signal(signal, strategy)
                        
        except Exception as e:
            self.logger.error(f"Error processing price update for {symbol}: {e}")
    
    async def _execute_signal(self, signal: TradingSignal, strategy: BaseStrategy):
        """Wykonuje sygnał handlowy"""
        try:
            # Sprawdź ryzyko przed wykonaniem
            risk_assessment = await self.risk_manager.validate_trade_order(
                symbol=signal.symbol,
                side=signal.signal_type.value,
                quantity=signal.quantity,
                price=signal.price,
                bot_id=signal.bot_id
            )
            
            if not risk_assessment.approved:
                self.logger.warning(f"Trade rejected by risk manager: {risk_assessment.rejection_reason}")
                return
            
            # Utwórz zlecenie
            order_type = OrderType.MARKET if signal.metadata.get('order_type') == 'market' else OrderType.LIMIT
            order_side = OrderSide.BUY if signal.signal_type == SignalType.BUY else OrderSide.SELL
            
            order_request = OrderRequest(
                symbol=signal.symbol,
                side=order_side,
                order_type=order_type,
                quantity=signal.quantity,
                price=signal.price if order_type == OrderType.LIMIT else None,
                metadata={
                    'strategy_id': signal.strategy_id,
                    'bot_id': signal.bot_id,
                    'signal_confidence': signal.confidence
                }
            )
            
            # Wykonaj zlecenie
            response = await self.trading_engine.place_order(order_request)
            
            if response.success:
                # Aktualizuj stan strategii
                if signal.signal_type == SignalType.BUY:
                    strategy.state.current_position += signal.quantity
                    strategy.state.total_invested += signal.quantity * signal.price
                    strategy.state.average_price = strategy.state.total_invested / strategy.state.current_position
                elif signal.signal_type == SignalType.SELL:
                    strategy.state.current_position -= signal.quantity
                    if strategy.state.current_position <= 0:
                        strategy.state.current_position = 0
                        strategy.state.total_invested = 0
                        strategy.state.average_price = 0
                
                strategy.state.last_signal = signal
                
                # Powiadom UI o wykonaniu
                for callback in self.execution_callbacks:
                    try:
                        await callback(signal, response)
                    except Exception as e:
                        self.logger.error(f"Error in execution callback: {e}")
                
                self.logger.info(f"Successfully executed signal for strategy {signal.strategy_id}")
            else:
                self.logger.error(f"Failed to execute signal: {response.error}")
                
        except Exception as e:
            self.logger.error(f"Error executing signal: {e}")
    
    def subscribe_to_signals(self, callback: Callable):
        """Subskrybuje powiadomienia o sygnałach"""
        self.signal_callbacks.append(callback)
    
    def subscribe_to_executions(self, callback: Callable):
        """Subskrybuje powiadomienia o wykonaniach"""
        self.execution_callbacks.append(callback)
    
    def get_strategy_state(self, strategy_id: str) -> Optional[StrategyState]:
        """Pobiera stan strategii"""
        if strategy_id in self.strategies:
            return self.strategies[strategy_id].state
        return None
    
    def get_all_strategies(self) -> Dict[str, StrategyState]:
        """Pobiera stany wszystkich strategii"""
        return {sid: strategy.state for sid, strategy in self.strategies.items()}

    def describe_strategies(self) -> List[Dict[str, Any]]:
        """Zwraca opis wszystkich aktywnych i zarejestrowanych strategii."""
        catalog: List[Dict[str, Any]] = []
        for strategy_id, strategy in self.strategies.items():
            config = getattr(strategy, "config", None)
            state = getattr(strategy, "state", None)
            entry: Dict[str, Any] = {
                "strategy_id": strategy_id,
                "bot_id": getattr(strategy, "bot_id", getattr(config, "bot_id", None)),
                "symbol": getattr(config, "symbol", getattr(strategy, "symbol", None)),
                "name": getattr(config, "name", strategy_id),
                "active": getattr(state, "active", getattr(strategy, "is_running", False)),
                "metadata": getattr(state, "metadata", {}),
            }
            strategy_type = getattr(config, "strategy_type", None)
            entry["strategy_type"] = (
                strategy_type.value if hasattr(strategy_type, "value") else strategy_type
            )
            last_update = getattr(state, "last_update", None)
            if isinstance(last_update, datetime):
                entry["last_update"] = last_update.isoformat()
            else:
                entry["last_update"] = last_update
            if state is not None:
                entry["state"] = {
                    "current_position": getattr(state, "current_position", None),
                    "total_profit": getattr(state, "total_profit", None),
                    "total_invested": getattr(state, "total_invested", None),
                }
                entry["last_signal"] = self._serialise_signal(getattr(state, "last_signal", None))
            catalog.append(entry)
        return catalog
    
    async def shutdown(self):
        """Zamyka silnik strategii"""
        try:
            # Zatrzymaj wszystkie strategie
            for strategy_id in list(self.strategies.keys()):
                await self.stop_strategy(strategy_id)

            self.strategies.clear()
            self.active = False

            self.logger.info("Strategy Engine shutdown completed")

        except Exception as e:
            self.logger.error(f"Error during Strategy Engine shutdown: {e}")

    def _serialise_signal(self, signal: Any) -> Optional[Dict[str, Any]]:
        if signal is None:
            return None
        if is_dataclass(signal):
            data = asdict(signal)
        elif isinstance(signal, dict):
            data = dict(signal)
        elif hasattr(signal, "to_dict"):
            data = signal.to_dict()
        else:
            data = {
                "symbol": getattr(signal, "symbol", None),
                "signal_type": getattr(signal, "signal_type", None),
                "price": getattr(signal, "price", None),
                "quantity": getattr(signal, "quantity", None),
                "confidence": getattr(signal, "confidence", None),
                "reason": getattr(signal, "reason", None),
                "timestamp": getattr(signal, "timestamp", None),
            }
        timestamp = data.get("timestamp")
        if isinstance(timestamp, datetime):
            data["timestamp"] = timestamp.isoformat()
        return data
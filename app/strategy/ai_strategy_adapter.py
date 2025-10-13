"""
AI Strategy Adapter - Adapter dla integracji AI Trading Bot z StrategyEngine
"""

import asyncio
from datetime import datetime
from typing import Dict, Any, Optional
from dataclasses import dataclass

from core.strategy_base import BaseStrategy, StrategyConfig, TradingSignal, SignalType, PriceData
from .ai_trading_bot import AITradingBot
from utils.logger import get_logger


@dataclass
class AIStrategyConfig(StrategyConfig):
    """Konfiguracja strategii AI"""
    target_hourly_profit: float = 2.0
    risk_tolerance: float = 0.02
    learning_enabled: bool = True
    use_reinforcement_learning: bool = False
    feature_engineering_enabled: bool = True
    sentiment_analysis_enabled: bool = False
    ensemble_models: bool = False
    learning_rate: float = 0.001
    model_update_frequency: int = 100
    daily_loss_limit: float = 50.0


class AIStrategyAdapter(BaseStrategy):
    """
    Adapter dla AI Trading Bot do integracji z StrategyEngine
    
    Ten adapter umożliwia AI Trading Bot działanie w ramach StrategyEngine,
    zapewniając spójny przepływ danych i integrację z systemem.
    """
    
    def __init__(self, strategy_id: str, bot_id: str, config: AIStrategyConfig):
        super().__init__(strategy_id, bot_id, config)
        
        self.logger = get_logger(f"ai_strategy_adapter_{strategy_id}")
        
        # Przygotuj parametry dla AI Trading Bot
        ai_parameters = {
            'pair': config.symbol,
            'budget': config.max_position_size,
            'target_hourly_profit': config.target_hourly_profit,
            'risk_tolerance': config.risk_tolerance,
            'learning_enabled': config.learning_enabled,
            'use_reinforcement_learning': config.use_reinforcement_learning,
            'feature_engineering_enabled': config.feature_engineering_enabled,
            'sentiment_analysis_enabled': config.sentiment_analysis_enabled,
            'ensemble_models': config.ensemble_models,
            'learning_rate': config.learning_rate,
            'model_update_frequency': config.model_update_frequency,
            'daily_loss_limit': config.daily_loss_limit
        }
        
        # Utwórz instancję AI Trading Bot
        self.ai_bot = AITradingBot(bot_id, ai_parameters)
        
        # Stan adaptera
        self.initialized = False
        self.last_signal_time = None
        self.signal_cooldown = 60  # Minimum 60 sekund między sygnałami
        
        self.logger.info(f"AI Strategy Adapter utworzony dla {config.symbol}")
    
    async def initialize(self, db_manager, risk_manager, exchange):
        """Inicjalizuje AI Trading Bot"""
        try:
            await self.ai_bot.initialize(db_manager, risk_manager, exchange)
            self.initialized = True
            self.logger.info("AI Strategy Adapter zainicjalizowany")
            return True
        except Exception as e:
            self.logger.error(f"Błąd inicjalizacji AI Strategy Adapter: {e}")
            return False
    
    async def analyze_market(self, price_data: PriceData, market_data: Dict[str, Any]) -> Optional[TradingSignal]:
        """
        Analizuje rynek używając AI Trading Bot i generuje sygnały
        
        Args:
            price_data: Dane cenowe
            market_data: Dodatkowe dane rynkowe
            
        Returns:
            TradingSignal lub None
        """
        try:
            if not self.initialized:
                self.logger.warning("AI Strategy Adapter nie został zainicjalizowany")
                return None
            
            # Sprawdź cooldown między sygnałami
            current_time = datetime.now()
            if (self.last_signal_time and 
                (current_time - self.last_signal_time).total_seconds() < self.signal_cooldown):
                return None
            
            # Aktualizuj AI bot z nowymi danymi rynkowymi
            await self._update_ai_bot_market_data(price_data, market_data)
            
            # Przeprowadź analizę AI
            ai_decision = await self._get_ai_decision()
            
            if ai_decision:
                signal = self._convert_ai_decision_to_signal(ai_decision, price_data)
                if signal:
                    self.last_signal_time = current_time
                    self.logger.info(f"AI Strategy wygenerował sygnał: {signal.signal_type.value} {signal.quantity} {signal.symbol}")
                    return signal
            
            return None
            
        except Exception as e:
            self.logger.error(f"Błąd analizy rynku AI Strategy: {e}")
            return None
    
    async def update_state(self, price_data: PriceData):
        """Aktualizuje stan strategii i AI bot"""
        try:
            # Aktualizuj stan bazowy
            await super().update_state(price_data)
            
            # Aktualizuj AI bot z nowymi danymi
            if self.initialized and self.ai_bot:
                # Przekaż informacje o aktualnej pozycji do AI bot
                self.ai_bot.current_position = self.state.current_position
                self.ai_bot.total_invested = self.state.total_invested
                self.ai_bot.average_price = self.state.average_price
                
                # Aktualizuj historię cen w AI bot
                await self._update_ai_price_history(price_data)
                
        except Exception as e:
            self.logger.error(f"Błąd aktualizacji stanu AI Strategy: {e}")
    
    async def _update_ai_bot_market_data(self, price_data: PriceData, market_data: Dict[str, Any]):
        """Aktualizuje AI bot z nowymi danymi rynkowymi"""
        try:
            # Konwertuj dane do formatu oczekiwanego przez AI bot
            market_update = {
                'price': price_data.price,
                'timestamp': price_data.timestamp,
                'volume': market_data.get('volume', 0),
                'high': market_data.get('high', price_data.price),
                'low': market_data.get('low', price_data.price),
                'open': market_data.get('open', price_data.price),
                'close': price_data.price
            }
            
            # Aktualizuj AI bot (jeśli ma metodę do aktualizacji danych rynkowych)
            if hasattr(self.ai_bot, 'update_market_data'):
                await self.ai_bot.update_market_data(market_update)
            
        except Exception as e:
            self.logger.error(f"Błąd aktualizacji danych rynkowych AI bot: {e}")
    
    async def _update_ai_price_history(self, price_data: PriceData):
        """Aktualizuje historię cen w AI bot"""
        try:
            if hasattr(self.ai_bot, 'price_history'):
                if not hasattr(self.ai_bot, 'price_history') or self.ai_bot.price_history is None:
                    self.ai_bot.price_history = []
                
                self.ai_bot.price_history.append({
                    'price': price_data.price,
                    'timestamp': price_data.timestamp
                })
                
                # Ogranicz historię do ostatnich 1000 punktów
                if len(self.ai_bot.price_history) > 1000:
                    self.ai_bot.price_history = self.ai_bot.price_history[-1000:]
                    
        except Exception as e:
            self.logger.error(f"Błąd aktualizacji historii cen AI bot: {e}")
    
    async def _get_ai_decision(self) -> Optional[Dict[str, Any]]:
        """Pobiera decyzję z AI Trading Bot"""
        try:
            if not self.ai_bot or not hasattr(self.ai_bot, 'current_market_condition'):
                return None
            
            # Sprawdź czy AI bot ma aktualną analizę rynku
            if self.ai_bot.current_market_condition is None:
                await self.ai_bot._analyze_market_conditions()
            
            # Pobierz rekomendację strategii
            if hasattr(self.ai_bot, '_get_strategy_recommendation'):
                recommendation = await self.ai_bot._get_strategy_recommendation()
                return recommendation
            
            # Fallback - prosta logika na podstawie warunków rynkowych
            market_condition = self.ai_bot.current_market_condition
            if market_condition:
                return self._simple_ai_decision(market_condition)
            
            return None
            
        except Exception as e:
            self.logger.error(f"Błąd pobierania decyzji AI: {e}")
            return None
    
    def _simple_ai_decision(self, market_condition) -> Optional[Dict[str, Any]]:
        """Prosta logika decyzyjna na podstawie warunków rynkowych"""
        try:
            # Logika kupna - niskie RSI i pozytywny trend
            if (market_condition.rsi < 30 and 
                market_condition.trend_strength > 0.5 and
                market_condition.market_sentiment in ['bullish', 'neutral']):
                
                return {
                    'action': 'buy',
                    'confidence': 0.7,
                    'reason': 'oversold_with_positive_trend',
                    'quantity_ratio': 0.1  # 10% dostępnego budżetu
                }
            
            # Logika sprzedaży - wysokie RSI lub negatywny trend
            elif (market_condition.rsi > 70 or 
                  market_condition.trend_strength < -0.3 or
                  market_condition.market_sentiment == 'bearish'):
                
                return {
                    'action': 'sell',
                    'confidence': 0.6,
                    'reason': 'overbought_or_negative_trend',
                    'quantity_ratio': 0.5  # Sprzedaj 50% pozycji
                }
            
            return None
            
        except Exception as e:
            self.logger.error(f"Błąd prostej logiki AI: {e}")
            return None
    
    def _convert_ai_decision_to_signal(self, ai_decision: Dict[str, Any], price_data: PriceData) -> Optional[TradingSignal]:
        """Konwertuje decyzję AI na sygnał handlowy"""
        try:
            action = ai_decision.get('action')
            confidence = ai_decision.get('confidence', 0.5)
            quantity_ratio = ai_decision.get('quantity_ratio', 0.1)
            reason = ai_decision.get('reason', 'ai_decision')
            
            if action == 'buy':
                # Oblicz ilość do kupienia
                available_budget = self.config.max_position_size - self.state.total_invested
                quantity = (available_budget * quantity_ratio) / price_data.price
                
                if quantity > 0:
                    return TradingSignal(
                        signal_type=SignalType.BUY,
                        symbol=self.config.symbol,
                        price=price_data.price,
                        quantity=quantity,
                        strategy_id=self.strategy_id,
                        bot_id=self.bot_id,
                        confidence=confidence,
                        metadata={
                            'strategy_type': 'AI',
                            'reason': reason,
                            'ai_confidence': confidence
                        }
                    )
            
            elif action == 'sell' and self.state.current_position > 0:
                # Oblicz ilość do sprzedania
                quantity = self.state.current_position * quantity_ratio
                
                if quantity > 0:
                    return TradingSignal(
                        signal_type=SignalType.SELL,
                        symbol=self.config.symbol,
                        price=price_data.price,
                        quantity=quantity,
                        strategy_id=self.strategy_id,
                        bot_id=self.bot_id,
                        confidence=confidence,
                        metadata={
                            'strategy_type': 'AI',
                            'reason': reason,
                            'ai_confidence': confidence
                        }
                    )
            
            return None
            
        except Exception as e:
            self.logger.error(f"Błąd konwersji decyzji AI na sygnał: {e}")
            return None
    
    async def stop(self):
        """Zatrzymuje AI Strategy Adapter"""
        try:
            if self.ai_bot and hasattr(self.ai_bot, 'stop'):
                await self.ai_bot.stop()
            
            self.initialized = False
            self.logger.info("AI Strategy Adapter zatrzymany")
            
        except Exception as e:
            self.logger.error(f"Błąd zatrzymywania AI Strategy Adapter: {e}")
    
    def get_performance_metrics(self) -> Dict[str, Any]:
        """Zwraca metryki wydajności AI Strategy"""
        try:
            base_metrics = {
                'strategy_id': self.strategy_id,
                'bot_id': self.bot_id,
                'symbol': self.config.symbol,
                'current_position': self.state.current_position,
                'total_invested': self.state.total_invested,
                'profit_loss': self.state.profit_loss,
                'average_price': self.state.average_price,
                'active': self.state.active
            }
            
            # Dodaj metryki AI jeśli dostępne
            if self.ai_bot:
                ai_metrics = {
                    'ai_total_trades': getattr(self.ai_bot, 'total_trades', 0),
                    'ai_successful_trades': getattr(self.ai_bot, 'successful_trades', 0),
                    'ai_win_rate': (getattr(self.ai_bot, 'successful_trades', 0) / 
                                   max(getattr(self.ai_bot, 'total_trades', 1), 1)) * 100,
                    'ai_current_daily_pnl': getattr(self.ai_bot, 'current_daily_pnl', 0.0),
                    'ai_learning_enabled': getattr(self.ai_bot, 'learning_enabled', False)
                }
                base_metrics.update(ai_metrics)
            
            return base_metrics
            
        except Exception as e:
            self.logger.error(f"Błąd pobierania metryki wydajności: {e}")
            return {}
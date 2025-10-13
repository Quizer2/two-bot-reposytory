"""
Podstawowe klasy dla strategii tradingowych
"""

import asyncio
import logging
from datetime import datetime
from typing import Dict, Any, Optional, List
from dataclasses import dataclass
from enum import Enum

from utils.logger import get_logger

logger = get_logger("strategy_base")

class SignalType(Enum):
    """Typ sygnału tradingowego"""
    BUY = "buy"
    SELL = "sell"
    HOLD = "hold"

@dataclass
class PriceData:
    """Dane cenowe"""
    symbol: str
    price: float
    volume: float
    timestamp: datetime
    high_24h: Optional[float] = None
    low_24h: Optional[float] = None
    change_24h: Optional[float] = None

@dataclass
class TradingSignal:
    """Sygnał tradingowy"""
    symbol: str
    signal_type: SignalType
    price: float
    quantity: float
    confidence: float
    timestamp: datetime
    reason: str = ""
    metadata: Dict[str, Any] = None

    def __post_init__(self):
        if self.metadata is None:
            self.metadata = {}

@dataclass
class StrategyConfig:
    """Konfiguracja strategii"""
    name: str
    symbol: str
    enabled: bool = True
    parameters: Dict[str, Any] = None
    
    def __post_init__(self):
        if self.parameters is None:
            self.parameters = {}

@dataclass
class StrategyState:
    """Stan strategii"""
    current_position: float = 0.0
    total_invested: float = 0.0
    total_profit: float = 0.0
    last_signal: Optional[TradingSignal] = None
    last_update: Optional[datetime] = None
    metadata: Dict[str, Any] = None
    
    def __post_init__(self):
        if self.metadata is None:
            self.metadata = {}

class BaseStrategy:
    """Bazowa klasa strategii tradingowej"""
    
    def __init__(self, config: StrategyConfig):
        self.config = config
        self.state = StrategyState()
        self.logger = get_logger(f"strategy_{config.name}")
        
    async def analyze_market(self, market_data: Dict[str, PriceData]) -> Optional[TradingSignal]:
        """
        Analizuje dane rynkowe i generuje sygnał tradingowy
        Musi być zaimplementowana przez podklasy
        """
        raise NotImplementedError("Subclasses must implement analyze_market method")
    
    def update_state(self, signal: TradingSignal, executed: bool = False):
        """Aktualizuje stan strategii po wykonaniu sygnału"""
        self.state.last_signal = signal
        self.state.last_update = datetime.now()
        
        if executed:
            if signal.signal_type == SignalType.BUY:
                self.state.current_position += signal.quantity
                self.state.total_invested += signal.quantity * signal.price
            elif signal.signal_type == SignalType.SELL:
                self.state.current_position -= signal.quantity
                # Oblicz zysk/stratę
                if self.state.current_position >= 0:
                    profit = signal.quantity * (signal.price - (self.state.total_invested / (self.state.current_position + signal.quantity)))
                    self.state.total_profit += profit
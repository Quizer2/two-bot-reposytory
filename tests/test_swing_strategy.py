#!/usr/bin/env python3
"""
Test strategii Swing Trading

Testuje:
- Inicjalizację strategii
- Analizę warunków rynkowych
- Generowanie sygnałów handlowych
- Zarządzanie pozycjami
- Obliczanie wskaźników technicznych
"""

import asyncio
import unittest
from unittest.mock import AsyncMock, MagicMock, patch
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.strategy.swing import SwingStrategy, SwingStatus
from core.database_manager import DatabaseManager
from app.risk_management import RiskManager
import logging
logger = logging.getLogger(__name__)


class MockExchange:
    """Mock exchange dla testów"""
    
    def __init__(self):
        self.name = "mock_exchange"
        self.current_price = 45000.0
        
    async def get_balance(self, symbol):
        return {"free": 1000.0, "used": 0.0, "total": 1000.0}
    
    async def create_order(self, symbol, type, side, amount, price=None):
        return {"id": "mock_order_123", "status": "filled"}
    
    async def get_current_price(self, symbol):
        return self.current_price
    
    async def get_ohlcv(self, symbol, timeframe, limit=100):
        """Mock OHLCV data"""
        import random
        base_price = self.current_price
        ohlcv_data = []
        
        for i in range(limit):
            open_price = base_price + random.uniform(-500, 500)
            high_price = open_price + random.uniform(0, 200)
            low_price = open_price - random.uniform(0, 200)
            close_price = open_price + random.uniform(-100, 100)
            volume = random.uniform(100, 1000)
            
            ohlcv_data.append([
                1640995200000 + i * 3600000,  # timestamp
                open_price,
                high_price,
                low_price,
                close_price,
                volume
            ])
            base_price = close_price
            
        return ohlcv_data


class MockDatabaseManager:
    """Mock database manager"""
    
    async def get_orders_by_bot_id(self, bot_id):
        return []
    
    async def save_order(self, order_data):
        return True
    
    async def get_strategy_state(self, bot_id):
        return {}
    
    async def save_strategy_state(self, bot_id, state):
        return True


class MockRiskManager:
    """Mock risk manager"""
    
    def __init__(self):
        pass
    
    async def check_risk_limits(self, order_data):
        return True
    
    async def calculate_position_size(self, symbol, price, risk_percentage):
        return 0.001


class TestSwingStrategy(unittest.IsolatedAsyncioTestCase):
    """Test case dla strategii Swing Trading"""
    
    def setUp(self):
        """Konfiguracja przed każdym testem"""
        self.mock_exchange = MockExchange()
        self.mock_db = MockDatabaseManager()
        self.mock_risk = MockRiskManager()
        
        # Parametry strategii
        self.strategy_params = {
            'symbol': 'BTC/USDT',
            'timeframe': '4h',
            'amount': 100.0,
            'rsi_period': 14,
            'rsi_oversold': 30.0,
            'rsi_overbought': 70.0,
            'sma_short': 20,
            'sma_medium': 50,
            'bb_period': 20,
            'bb_std': 2.0,
            'atr_period': 14,
            'min_trend_strength': 0.6,
            'stop_loss_atr_multiplier': 2.0,
            'take_profit_ratio': 2.0,
            'max_position_time_hours': 168,
            'max_weekly_trades': 5,
            'max_daily_trades': 5,
            'stop_loss_percentage': 1.0
        }
    
    def test_strategy_initialization(self):
        """Test inicjalizacji strategii"""
        logger.info("Test inicjalizacji strategii Swing Trading...")
        
        strategy = SwingStrategy(**self.strategy_params)
        
        # Sprawdź podstawowe parametry
        self.assertEqual(strategy.symbol, 'BTC/USDT')
        self.assertEqual(strategy.timeframe, '4h')
        self.assertEqual(strategy.amount, 100.0)
        self.assertEqual(strategy.rsi_period, 14)
        self.assertEqual(strategy.sma_short, 20)
        self.assertEqual(strategy.sma_medium, 50)
        
        # Sprawdź status początkowy
        self.assertEqual(strategy.status, SwingStatus.STOPPED)
        self.assertFalse(strategy.is_running)
        self.assertEqual(strategy.status, SwingStatus.STOPPED)
        logger.info("✅ Inicjalizacja strategii: OK")
    
    async def test_strategy_start_stop(self):
        """Test uruchamiania i zatrzymywania strategii"""
        logger.info("Test uruchamiania/zatrzymywania strategii...")
        
        strategy = SwingStrategy(**self.strategy_params)
        
        # Inicjalizuj strategię
        await strategy.initialize(self.mock_db, self.mock_risk, self.mock_exchange)
        
        # Test uruchomienia
        await strategy.start()
        self.assertTrue(strategy.is_running)
        self.assertEqual(strategy.status, SwingStatus.RUNNING)
        
        # Test zatrzymania
        await strategy.stop()
        self.assertFalse(strategy.is_running)
        self.assertEqual(strategy.status, SwingStatus.STOPPED)
        logger.info("✅ Uruchamianie/zatrzymywanie: OK")
    
    async def test_technical_indicators(self):
        """Test obliczania wskaźników technicznych"""
        logger.info("Test wskaźników technicznych...")
        
        strategy = SwingStrategy(**self.strategy_params)
        await strategy.initialize(self.mock_db, self.mock_risk, self.mock_exchange)
        
        # Pobierz dane OHLCV
        ohlcv_data = await self.mock_exchange.get_ohlcv('BTC/USDT', '4h', 100)
        
        # Test obliczania RSI
        rsi_values = strategy._calculate_rsi(ohlcv_data)
        self.assertIsNotNone(rsi_values)
        self.assertGreater(len(rsi_values), 0)
        
        # Test obliczania średnich kroczących
        ma_fast = strategy._calculate_moving_average(ohlcv_data, self.strategy_params['sma_short'])
        ma_slow = strategy._calculate_moving_average(ohlcv_data, self.strategy_params['sma_medium'])
        
        self.assertIsNotNone(ma_fast)
        self.assertIsNotNone(ma_slow)
        self.assertGreater(len(ma_fast), 0)
        self.assertGreater(len(ma_slow), 0)
        
        # Test Bollinger Bands
        bb_upper, bb_middle, bb_lower = strategy._calculate_bollinger_bands(
            ohlcv_data, 
            self.strategy_params['bb_period'], 
            self.strategy_params['bb_std']
        )
        
        self.assertIsNotNone(bb_upper)
        self.assertIsNotNone(bb_middle)
        self.assertIsNotNone(bb_lower)
        logger.info("✅ Wskaźniki techniczne: OK")
    
    async def test_signal_generation(self):
        """Test generowania sygnałów handlowych"""
        logger.info("Test generowania sygnałów...")
        
        strategy = SwingStrategy(**self.strategy_params)
        await strategy.initialize(self.mock_db, self.mock_risk, self.mock_exchange)
        
        # Symuluj warunki rynkowe
        market_data = {
            'price': 45000.0,
            'rsi': 25.0,  # Wyprzedanie
            'ma_fast': 44800.0,
            'ma_slow': 44500.0,
            'bb_upper': 46000.0,
            'bb_lower': 44000.0,
            'volume': 500.0,
            'trend_strength': 0.7
        }
        
        # Test sygnału kupna
        buy_signal = strategy._should_buy(market_data)
        self.assertIsInstance(buy_signal, bool)
        
        # Test sygnału sprzedaży
        sell_signal = strategy._should_sell(market_data)
        self.assertIsInstance(sell_signal, bool)
        logger.info("✅ Generowanie sygnałów: OK")
    
    async def test_position_management(self):
        """Test zarządzania pozycjami"""
        logger.info("Test zarządzania pozycjami...")
        
        strategy = SwingStrategy(**self.strategy_params)
        await strategy.initialize(self.mock_db, self.mock_risk, self.mock_exchange)
        
        # Test otwierania pozycji
        position_data = {
            'symbol': 'BTC/USDT',
            'side': 'buy',
            'amount': 0.001,
            'price': 45000.0,
            'timestamp': 1640995200000
        }
        
        result = await strategy._open_position(position_data)
        self.assertIsNotNone(result)
        
        # Test zamykania pozycji
        close_result = await strategy._close_position('mock_order_123')
        self.assertIsNotNone(close_result)
        logger.info("✅ Zarządzanie pozycjami: OK")
    
    async def test_risk_management(self):
        """Test zarządzania ryzykiem"""
        logger.info("Test zarządzania ryzykiem...")
        
        strategy = SwingStrategy(**self.strategy_params)
        await strategy.initialize(self.mock_db, self.mock_risk, self.mock_exchange)
        
        # Test sprawdzania limitów dziennych
        daily_trades = 2
        max_daily = self.strategy_params['max_daily_trades']
        
        can_trade = strategy._can_trade_today(daily_trades, max_daily)
        self.assertTrue(can_trade)
        
        # Test przekroczenia limitu
        daily_trades = 5
        can_trade = strategy._can_trade_today(daily_trades, max_daily)
        self.assertFalse(can_trade)
        
        # Test obliczania stop loss
        entry_price = 45000.0
        stop_loss_price = strategy._calculate_stop_loss(entry_price, 'buy')
        expected_stop_loss = entry_price * (1 - self.strategy_params['stop_loss_percentage'] / 100)
        
        self.assertAlmostEqual(stop_loss_price, expected_stop_loss, places=2)
        logger.info("✅ Zarządzanie ryzykiem: OK")


async def run_swing_strategy_tests():
    """Uruchom wszystkie testy strategii Swing Trading"""
    logger.info("\n🔄 Uruchamianie testów strategii Swing Trading...")
    
    test_case = TestSwingStrategy()
    test_case.setUp()
    
    try:
        # Test inicjalizacji
        test_case.test_strategy_initialization()
        
        # Testy asynchroniczne
        await test_case.test_strategy_start_stop()
        await test_case.test_technical_indicators()
        await test_case.test_signal_generation()
        await test_case.test_position_management()
        await test_case.test_risk_management()
        logger.info("✅ Wszystkie testy strategii Swing Trading zakończone pomyślnie!")
        return True
        
    except Exception as e:
        pass
        logger.info(f"❌ Błąd podczas testów strategii Swing Trading: {e}")
        import traceback
        traceback.print_exc()
        return False


    pass
if __name__ == "__main__":
    asyncio.run(run_swing_strategy_tests())
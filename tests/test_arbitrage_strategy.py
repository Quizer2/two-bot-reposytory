#!/usr/bin/env python3
"""
Test strategii Arbitrage

Testuje:
- Inicjalizację strategii
- Monitorowanie różnic cenowych między giełdami
- Wykrywanie okazji arbitrażowych
- Wykonywanie transakcji arbitrażowych
- Zarządzanie ryzykiem
"""

import asyncio
import unittest
from unittest.mock import AsyncMock, MagicMock, patch
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.strategy.arbitrage import ArbitrageStrategy, ArbitrageStatus
from core.database_manager import DatabaseManager
from app.risk_management import RiskManager
import logging
logger = logging.getLogger(__name__)
from datetime import datetime, timedelta
from app.strategy.arbitrage import ArbitrageTrade


class MockExchange:
    """Mock exchange dla testów"""
    
    def __init__(self, name, base_price=45000.0, spread_factor=1.0):
        self.name = name
        self.base_price = base_price
        self.spread_factor = spread_factor
        
    async def get_balance(self, symbol):
        return {"free": 1000.0, "used": 0.0, "total": 1000.0}
    
    async def create_order(self, symbol, type, side, amount, price=None):
        return {"id": f"mock_order_{self.name}_123", "status": "filled"}
    
    async def get_current_price(self, symbol):
        return self.base_price * self.spread_factor
    
    async def get_orderbook(self, symbol, limit=10):
        """Mock orderbook data"""
        base_price = self.base_price * self.spread_factor
        
        bids = []
        asks = []
        
        for i in range(limit):
            bid_price = base_price - (i + 1) * 10
            ask_price = base_price + (i + 1) * 10
            amount = 0.1 + i * 0.05
            
            bids.append([bid_price, amount])
            asks.append([ask_price, amount])
        
        return {
            'bids': bids,
            'asks': asks,
            'timestamp': 1640995200000
        }
    
    async def get_trading_fees(self):
        return {'maker': 0.001, 'taker': 0.001}


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
    
    async def save_arbitrage_opportunity(self, opportunity_data):
        return True


class MockRiskManager:
    """Mock risk manager"""
    
    def __init__(self):
        pass
    
    async def check_risk_limits(self, order_data):
        return True
    
    async def calculate_position_size(self, symbol, price, risk_percentage):
        return 0.001


class TestArbitrageStrategy(unittest.IsolatedAsyncioTestCase):
    """Test case dla strategii Arbitrage"""
    
    def setUp(self):
        """Konfiguracja przed każdym testem"""
        # Tworzenie mock exchanges z różnymi cenami
        self.exchange1 = MockExchange("binance", 45000.0, 1.0)
        self.exchange2 = MockExchange("bybit", 45000.0, 1.002)  # 0.2% wyższa cena
        self.exchanges = [self.exchange1, self.exchange2]
        
        self.mock_db = MockDatabaseManager()
        self.mock_risk = MockRiskManager()
        
        # Parametry strategii
        self.strategy_params = {
            'symbol': 'BTC/USDT',
            'exchanges': ['binance', 'bybit'],
            'min_spread_percentage': 0.1,
            'max_position_size': 100.0,
            'min_volume': 1.0,
            'execution_timeout_seconds': 30,
            'max_slippage_percentage': 0.05,
            'max_daily_trades': 10,
            'max_position_time': 300
        }
    
    def test_strategy_initialization(self):
        """Test inicjalizacji strategii"""
        logger.info("Test inicjalizacji strategii Arbitrage...")
        
        strategy = ArbitrageStrategy(**self.strategy_params)
        
        # Sprawdź podstawowe parametry
        self.assertEqual(strategy.symbol, 'BTC/USDT')
        self.assertEqual(strategy.exchanges, ['binance', 'bybit'])
        self.assertEqual(strategy.min_spread_percentage, 0.1)
        self.assertEqual(strategy.max_position_size, 100.0)
        self.assertEqual(strategy.min_volume, 1.0)
        
        # Sprawdź status początkowy
        self.assertEqual(strategy.status, ArbitrageStatus.STOPPED)
        self.assertFalse(strategy.is_running)
        logger.info("✅ Inicjalizacja strategii: OK")
    
    async def test_strategy_start_stop(self):
        """Test uruchamiania i zatrzymywania strategii"""
        logger.info("Test uruchamiania/zatrzymywania strategii...")
        
        strategy = ArbitrageStrategy(**self.strategy_params)
        
        # Inicjalizuj strategię
        await strategy.initialize(self.mock_db, self.mock_risk, self.exchanges)
        
        # Test uruchomienia
        await strategy.start()
        self.assertTrue(strategy.is_running)
        self.assertEqual(strategy.status, ArbitrageStatus.RUNNING)
        
        # Test zatrzymania
        await strategy.stop()
        self.assertFalse(strategy.is_running)
        self.assertEqual(strategy.status, ArbitrageStatus.STOPPED)
        logger.info("✅ Uruchamianie/zatrzymywanie: OK")
    
    async def test_price_monitoring(self):
        """Test monitorowania cen na różnych giełdach"""
        logger.info("Test monitorowania cen...")
        
        strategy = ArbitrageStrategy(**self.strategy_params)
        await strategy.initialize(self.mock_db, self.mock_risk, self.exchanges)
        
        # Pobierz ceny z wszystkich giełd
        prices = await strategy._get_prices_from_exchanges()
        
        self.assertIsInstance(prices, dict)
        self.assertEqual(len(prices), 2)
        self.assertIn("binance", prices)
        self.assertIn("bybit", prices)
        
        # Sprawdź czy ceny są różne (symulacja spreadu)
        binance_price = prices["binance"]
        bybit_price = prices["bybit"]
        
        self.assertNotEqual(binance_price, bybit_price)
        self.assertGreater(bybit_price, binance_price)
        logger.info("✅ Monitorowanie cen: OK")
    
    async def test_spread_calculation(self):
        """Test obliczania spreadów między giełdami"""
        logger.info("Test obliczania spreadów...")
        
        strategy = ArbitrageStrategy(**self.strategy_params)
        await strategy.initialize(self.mock_db, self.mock_risk, self.exchanges)
        
        # Symuluj ceny
        prices = {
            "binance": 45000.0,
            "bybit": 45090.0  # 0.2% spread
        }
        
        # Oblicz spread
        spread_data = strategy._calculate_spreads(prices)
        
        self.assertIsInstance(spread_data, list)
        self.assertGreater(len(spread_data), 0)
        
        # Sprawdź pierwszy spread
        first_spread = spread_data[0]
        self.assertIn('buy_exchange', first_spread)
        self.assertIn('sell_exchange', first_spread)
        self.assertIn('spread_percentage', first_spread)
        self.assertIn('profit_potential', first_spread)
        
        # Sprawdź czy spread jest poprawnie obliczony
        expected_spread = ((45090.0 - 45000.0) / 45000.0) * 100
        self.assertAlmostEqual(first_spread['spread_percentage'], expected_spread, places=2)
        logger.info("✅ Obliczanie spreadów: OK")
    
    async def test_opportunity_detection(self):
        """Test wykrywania okazji arbitrażowych"""
        logger.info("Test wykrywania okazji...")
        
        strategy = ArbitrageStrategy(**self.strategy_params)
        await strategy.initialize(self.mock_db, self.mock_risk, self.exchanges)
        
        # Symuluj duży spread (powyżej minimum)
        spread_data = {
            'buy_exchange': 'binance',
            'sell_exchange': 'bybit',
            'buy_price': 45000.0,
            'sell_price': 45090.0,
            'spread_percentage': 0.2,
            'profit_potential': 90.0
        }
        
        # Test czy okazja jest wykryta
        is_opportunity = strategy._is_arbitrage_opportunity(spread_data)
        self.assertTrue(is_opportunity)
        
        # Test małego spreadu (poniżej minimum)
        small_spread_data = {
            'buy_exchange': 'binance',
            'sell_exchange': 'bybit',
            'buy_price': 45000.0,
            'sell_price': 45020.0,
            'spread_percentage': 0.044,  # Poniżej 0.1%
            'profit_potential': 20.0
        }
        
        is_small_opportunity = strategy._is_arbitrage_opportunity(small_spread_data)
        self.assertFalse(is_small_opportunity)
        logger.info("✅ Wykrywanie okazji: OK")
    
    async def test_arbitrage_execution(self):
        """Test wykonywania transakcji arbitrażowych"""
        logger.info("Test wykonywania arbitrażu...")
        
        strategy = ArbitrageStrategy(**self.strategy_params)
        await strategy.initialize(self.mock_db, self.mock_risk, self.exchanges)
        
        # Symuluj okazję arbitrażową
        opportunity = {
            'buy_exchange': 'binance',
            'sell_exchange': 'bybit',
            'buy_price': 45000.0,
            'sell_price': 45090.0,
            'spread_percentage': 0.2,
            'profit_potential': 90.0,
            'amount': 0.001
        }
        
        # Test wykonania arbitrażu
        result = await strategy._execute_arbitrage(opportunity)
        
        self.assertIsNotNone(result)
        self.assertIn('buy_order', result)
        self.assertIn('sell_order', result)
        self.assertIn('profit', result)
        logger.info("✅ Wykonywanie arbitrażu: OK")
    
    async def test_risk_management(self):
        """Test zarządzania ryzykiem"""
        logger.info("Test zarządzania ryzykiem...")
        
        strategy = ArbitrageStrategy(**self.strategy_params)
        await strategy.initialize(self.mock_db, self.mock_risk, self.exchanges)
        
        # Test sprawdzania limitów dziennych
        daily_trades = 5
        max_daily = self.strategy_params['max_daily_trades']
        
        can_trade = strategy._can_trade_today(daily_trades, max_daily)
        self.assertTrue(can_trade)
        
        # Test przekroczenia limitu
        daily_trades = 15
        can_trade = strategy._can_trade_today(daily_trades, max_daily)
        self.assertFalse(can_trade)
        
        # Test sprawdzania czasu pozycji
        position_time = 200  # 200 sekund
        max_time = self.strategy_params['max_position_time']
        
        is_time_ok = strategy._check_position_time(position_time, max_time)
        self.assertTrue(is_time_ok)
        
        # Test przekroczenia czasu
        position_time = 400  # 400 sekund
        is_time_ok = strategy._check_position_time(position_time, max_time)
        self.assertFalse(is_time_ok)
        logger.info("✅ Zarządzanie ryzykiem: OK")
    
    async def test_fee_calculation(self):
        """Test obliczania opłat"""
        logger.info("Test obliczania opłat...")
        
        strategy = ArbitrageStrategy(**self.strategy_params)
        await strategy.initialize(self.mock_db, self.mock_risk, self.exchanges)
        
        # Symuluj dane transakcji
        trade_data = {
            'buy_amount': 0.001,
            'buy_price': 45000.0,
            'sell_amount': 0.001,
            'sell_price': 45090.0,
            'buy_exchange': 'binance',
            'sell_exchange': 'bybit'
        }
        
        # Oblicz opłaty
        total_fees = await strategy._calculate_total_fees(trade_data)
        
        self.assertIsInstance(total_fees, float)
        self.assertGreater(total_fees, 0)
        
        # Sprawdź czy opłaty są rozsądne (powinny być małe)
        trade_value = trade_data['buy_amount'] * trade_data['buy_price']
        fee_percentage = (total_fees / trade_value) * 100
        self.assertLess(fee_percentage, 1.0)  # Opłaty powinny być < 1%
        logger.info("✅ Obliczanie opłat: OK")

    async def test_enforce_max_position_time_cancels_trades(self):
        """Aktywne transakcje przekraczające max_position_time powinny być anulowane i usunięte."""
        strategy = ArbitrageStrategy(**self.strategy_params)
        await strategy.initialize(self.mock_db, self.mock_risk, self.exchanges)

        # Utwórz transakcję starszą niż dopuszczalny limit
        old_trade = ArbitrageTrade(
            opportunity_id="opp-timeout",
            symbol=self.strategy_params['symbol'],
            amount=0.001,
            buy_exchange='binance',
            sell_exchange='bybit',
            buy_order_id='buy-older',
            sell_order_id='sell-older',
            buy_price=45000.0,
            sell_price=45100.0,
            buy_time=datetime.now() - timedelta(seconds=1000),  # starsza niż 300s
            sell_time=datetime.now(),
            gross_profit=0.0,
            fees_paid=0.0,
            net_profit=0.0,
            profit_percentage=0.0,
            execution_time_ms=0.0,
            slippage=0.0,
            status='partial'
        )
        strategy.active_trades.append(old_trade)

        # Podmień metody cancel_order w adapterach na AsyncMock
        strategy.exchange_adapters['binance'].cancel_order = AsyncMock(return_value=True)
        strategy.exchange_adapters['bybit'].cancel_order = AsyncMock(return_value=True)

        # Wymuś sprawdzenie limitu czasu i anulowanie
        await strategy._enforce_position_time_limits()

        # Oczekujemy, że transakcja zostanie anulowana i usunięta z active_trades
        self.assertEqual(len(strategy.active_trades), 0)
        strategy.exchange_adapters['binance'].cancel_order.assert_awaited()
        strategy.exchange_adapters['bybit'].cancel_order.assert_awaited()



async def run_arbitrage_strategy_tests():
    """Uruchom wszystkie testy strategii Arbitrage"""
    logger.info("\n🔄 Uruchamianie testów strategii Arbitrage...")
    
    test_case = TestArbitrageStrategy()
    test_case.setUp()
    
    try:
        # Test inicjalizacji
        test_case.test_strategy_initialization()
        
        # Testy asynchroniczne
        await test_case.test_strategy_start_stop()
        await test_case.test_price_monitoring()
        await test_case.test_spread_calculation()
        await test_case.test_opportunity_detection()
        await test_case.test_arbitrage_execution()
        await test_case.test_risk_management()
        await test_case.test_fee_calculation()
        await test_case.test_enforce_max_position_time_cancels_trades()
        
        logger.info("✅ Wszystkie testy strategii Arbitrage zakończone pomyślnie!")
        return True
        
    except Exception as e:
        logger.exception(f"❌ Błąd podczas testów strategii Arbitrage: {e}")
        return False


if __name__ == "__main__":
    asyncio.run(run_arbitrage_strategy_tests())
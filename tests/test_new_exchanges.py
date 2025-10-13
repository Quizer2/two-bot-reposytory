#!/usr/bin/env python3
"""
Test nowych giełd: Kraken i Bitfinex

Testuje:
- Inicjalizację połączeń z giełdami
- Pobieranie danych rynkowych
- Składanie zleceń
- Sprawdzanie sald
- Obsługę błędów
"""

import asyncio
import unittest
from unittest.mock import AsyncMock, MagicMock, patch
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.exchange.kraken import KrakenExchange
from app.exchange.bitfinex import BitfinexExchange
import logging
logger = logging.getLogger(__name__)


class TestKrakenExchange(unittest.IsolatedAsyncioTestCase):
    """Test case dla giełdy Kraken"""
    
    def setUp(self):
        """Konfiguracja przed każdym testem"""
        self.api_credentials = {
            'api_key': 'test_api_key',
            'api_secret': 'test_api_secret',
            'testnet': True
        }
    
    def test_kraken_initialization(self):
        """Test inicjalizacji połączenia z Kraken"""
        logger.info("Test inicjalizacji Kraken...")
        
        exchange = KrakenExchange(**self.api_credentials)
        
        # Sprawdź podstawowe właściwości
        self.assertEqual(exchange.name, 'kraken')
        self.assertTrue(exchange.testnet)
        self.assertIsNotNone(exchange.api_key)
        self.assertIsNotNone(exchange.api_secret)
        logger.info("✅ Inicjalizacja Kraken: OK")
    
    async def test_kraken_connection(self):
        """Test połączenia z Kraken"""
        logger.info("Test połączenia z Kraken...")
        
        exchange = KrakenExchange(**self.api_credentials)
        
        # Mock odpowiedzi API
        with patch.object(exchange, '_make_request') as mock_request:
            mock_request.return_value = {
                'error': [],
                'result': {
                    'XXBTZUSD': {
                        'a': ['45000.0', '1', '1.000'],
                        'b': ['44990.0', '1', '1.000'],
                        'c': ['45005.0', '0.001'],
                        'v': ['100.0', '1000.0'],
                        'p': ['45000.0', '44500.0'],
                        't': [50, 500],
                        'l': ['44000.0', '43000.0'],
                        'h': ['46000.0', '47000.0'],
                        'o': '44500.0'
                    }
                }
            }
            
            # Test pobierania ceny
            price = await exchange.get_current_price('BTC/USD')
            self.assertIsInstance(price, float)
            self.assertGreater(price, 0)
        logger.info("✅ Połączenie z Kraken: OK")
    
    async def test_kraken_balance(self):
        """Test pobierania salda z Kraken"""
        logger.info("Test salda Kraken...")
        
        exchange = KrakenExchange(**self.api_credentials)
        
        # Mock odpowiedzi API
        with patch.object(exchange, '_make_request') as mock_request:
            mock_request.return_value = {
                'error': [],
                'result': {
                    'ZUSD': '1000.0000',
                    'XXBT': '0.0100'
                }
            }
            
            # Test pobierania salda
            balance = await exchange.get_balance('BTC')
            
            self.assertIsInstance(balance, dict)
            self.assertIn('free', balance)
            self.assertIn('used', balance)
            self.assertIn('total', balance)
            self.assertGreaterEqual(balance['free'], 0)
        logger.info("✅ Saldo Kraken: OK")
    
    async def test_kraken_order_creation(self):
        """Test składania zleceń na Kraken"""
        logger.info("Test zleceń Kraken...")
        
        exchange = KrakenExchange(**self.api_credentials)
        
        # Mock odpowiedzi API
        with patch.object(exchange, '_make_request') as mock_request:
            mock_request.return_value = {
                'error': [],
                'result': {
                    'txid': ['OQCLML-BW3P3-BUCMWZ']
                }
            }
            
            # Test składania zlecenia
            order = await exchange.create_order(
                symbol='BTC/USD',
                type='limit',
                side='buy',
                amount=0.001,
                price=45000.0
            )
            
            self.assertIsInstance(order, dict)
            self.assertIn('id', order)
            self.assertIsNotNone(order['id'])
        logger.info("✅ Zlecenia Kraken: OK")
    
    async def test_kraken_error_handling(self):
        """Test obsługi błędów Kraken"""
        logger.info("Test błędów Kraken...")
        
        exchange = KrakenExchange(**self.api_credentials)
        
        # Mock błędu API
        with patch.object(exchange, '_make_request') as mock_request:
            mock_request.return_value = {
                'error': ['EGeneral:Invalid arguments']
            }
            
            # Test obsługi błędu
            with self.assertRaises(Exception):
                await exchange.get_current_price('INVALID/PAIR')
        logger.info("✅ Obsługa błędów Kraken: OK")


class TestBitfinexExchange(unittest.IsolatedAsyncioTestCase):
    """Test case dla giełdy Bitfinex"""
    
    def setUp(self):
        """Konfiguracja przed każdym testem"""
        self.api_credentials = {
            'api_key': 'test_api_key',
            'api_secret': 'test_api_secret',
            'testnet': True
        }
    
    def test_bitfinex_initialization(self):
        """Test inicjalizacji połączenia z Bitfinex"""
        logger.info("Test inicjalizacji Bitfinex...")
        
        exchange = BitfinexExchange(**self.api_credentials)
        
        # Sprawdź podstawowe właściwości
        self.assertEqual(exchange.name, 'bitfinex')
        self.assertTrue(exchange.testnet)
        self.assertIsNotNone(exchange.api_key)
        self.assertIsNotNone(exchange.api_secret)
        logger.info("✅ Inicjalizacja Bitfinex: OK")
    
    async def test_bitfinex_connection(self):
        """Test połączenia z Bitfinex"""
        logger.info("Test połączenia z Bitfinex...")
        
        exchange = BitfinexExchange(**self.api_credentials)
        
        # Mock odpowiedzi API
        with patch.object(exchange, '_make_request') as mock_request:
            mock_request.return_value = [
                45000.0,  # bid
                45010.0,  # bid_size
                45020.0,  # ask
                45030.0,  # ask_size
                -50.0,    # daily_change
                -0.0011,  # daily_change_relative
                45005.0,  # last_price
                1000.0,   # volume
                46000.0,  # high
                44000.0   # low
            ]
            
            # Test pobierania ceny
            price = await exchange.get_current_price('BTC/USD')
            self.assertIsInstance(price, float)
            self.assertGreater(price, 0)
        logger.info("✅ Połączenie z Bitfinex: OK")
    
    async def test_bitfinex_balance(self):
        """Test pobierania salda z Bitfinex"""
        logger.info("Test salda Bitfinex...")
        
        exchange = BitfinexExchange(**self.api_credentials)
        
        # Mock odpowiedzi API
        with patch.object(exchange, '_make_request') as mock_request:
            mock_request.return_value = [
                ['exchange', 'USD', 1000.0, 0.0, None],
                ['exchange', 'BTC', 0.01, 0.0, None]
            ]
            
            # Test pobierania salda
            balance = await exchange.get_balance('BTC')
            
            self.assertIsInstance(balance, dict)
            self.assertIn('free', balance)
            self.assertIn('used', balance)
            self.assertIn('total', balance)
            self.assertGreaterEqual(balance['free'], 0)
        logger.info("✅ Saldo Bitfinex: OK")
    
    async def test_bitfinex_order_creation(self):
        """Test składania zleceń na Bitfinex"""
        logger.info("Test zleceń Bitfinex...")
        
        exchange = BitfinexExchange(**self.api_credentials)
        
        # Mock odpowiedzi API
        with patch.object(exchange, '_make_request') as mock_request:
            mock_request.return_value = [
                123456789,    # order_id
                None,         # gid
                None,         # cid
                'tBTCUSD',    # symbol
                1640995200000, # mts_create
                1640995200000, # mts_update
                0.001,        # amount
                0.001,        # amount_orig
                'EXCHANGE LIMIT', # type
                None,         # type_prev
                None,         # mts_tif
                None,         # flags
                'ACTIVE',     # order_status
                None,         # price
                45000.0,      # price_avg
                None,         # price_trailing
                None,         # price_aux_limit
                None,         # notify
                None,         # hidden
                None,         # placed_id
                None,         # routing
                None,         # meta
            ]
            
            # Test składania zlecenia
            order = await exchange.create_order(
                symbol='BTC/USD',
                type='limit',
                side='buy',
                amount=0.001,
                price=45000.0
            )
            
            self.assertIsInstance(order, dict)
            self.assertIn('id', order)
            self.assertIsNotNone(order['id'])
        logger.info("✅ Zlecenia Bitfinex: OK")
    
    async def test_bitfinex_error_handling(self):
        """Test obsługi błędów Bitfinex"""
        logger.info("Test błędów Bitfinex...")
        
        exchange = BitfinexExchange(**self.api_credentials)
        
        # Mock błędu API
        with patch.object(exchange, '_make_request') as mock_request:
            mock_request.side_effect = Exception("API Error: Invalid symbol")
            
            # Test obsługi błędu
            with self.assertRaises(Exception):
                await exchange.get_current_price('INVALID/PAIR')
        logger.info("✅ Obsługa błędów Bitfinex: OK")


class TestExchangeIntegration(unittest.IsolatedAsyncioTestCase):
    """Test integracji nowych giełd z systemem"""
    
    async def test_exchange_factory(self):
        """Test factory pattern dla nowych giełd"""
        logger.info("Test factory pattern...")
        
        # Import factory
        from app.exchange import create_exchange
        
        # Test tworzenia Kraken
        kraken_config = {
            'exchange': 'kraken',
            'api_key': 'test_key',
            'api_secret': 'test_secret',
            'sandbox': True
        }
        
        kraken_exchange = create_exchange(kraken_config)
        self.assertIsInstance(kraken_exchange, KrakenExchange)
        self.assertEqual(kraken_exchange.name, 'kraken')
        
        # Test tworzenia Bitfinex
        bitfinex_config = {
            'exchange': 'bitfinex',
            'api_key': 'test_key',
            'api_secret': 'test_secret',
            'sandbox': True
        }
        
        bitfinex_exchange = create_exchange(bitfinex_config)
        self.assertIsInstance(bitfinex_exchange, BitfinexExchange)
        self.assertEqual(bitfinex_exchange.name, 'bitfinex')
        logger.info("✅ Factory pattern: OK")
    
    async def test_exchange_compatibility(self):
        """Test kompatybilności z istniejącym systemem"""
        logger.info("Test kompatybilności...")
        
        # Test czy nowe giełdy implementują wymagane metody
        required_methods = [
            'get_current_price',
            'get_balance',
            'create_order',
            'cancel_order',
            'get_order_status'
        ]
        
        for exchange_class in [KrakenExchange, BitfinexExchange]:
            exchange = exchange_class(
                api_key='test',
                api_secret='test',
                sandbox=True
            )
            
            for method_name in required_methods:
                self.assertTrue(hasattr(exchange, method_name))
                self.assertTrue(callable(getattr(exchange, method_name)))
        logger.info("✅ Kompatybilność: OK")


async def run_new_exchanges_tests():
    """Uruchom wszystkie testy nowych giełd"""
    logger.info("\n🔄 Uruchamianie testów nowych giełd...")
    
    try:
        # Testy Kraken
        kraken_test = TestKrakenExchange()
        kraken_test.setUp()
        kraken_test.test_kraken_initialization()
        await kraken_test.test_kraken_connection()
        await kraken_test.test_kraken_balance()
        await kraken_test.test_kraken_order_creation()
        await kraken_test.test_kraken_error_handling()
        
        # Testy Bitfinex
        bitfinex_test = TestBitfinexExchange()
        bitfinex_test.setUp()
        bitfinex_test.test_bitfinex_initialization()
        await bitfinex_test.test_bitfinex_connection()
        await bitfinex_test.test_bitfinex_balance()
        await bitfinex_test.test_bitfinex_order_creation()
        await bitfinex_test.test_bitfinex_error_handling()
        
        # Testy integracji
        integration_test = TestExchangeIntegration()
        await integration_test.test_exchange_factory()
        await integration_test.test_exchange_compatibility()
        logger.info("✅ Wszystkie testy nowych giełd zakończone pomyślnie!")
        return True
        
    except Exception as e:
        logger.exception(f"❌ Błąd podczas testów nowych giełd: {e}")
        import traceback
        traceback.print_exc()
        return False


    pass
if __name__ == "__main__":
    asyncio.run(run_new_exchanges_tests())
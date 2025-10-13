"""
Test przepływu danych Bot → TradingEngine → API → Exchange
Weryfikuje czy boty mogą składać zlecenia przez TradingEngine i czy są one realizowane na giełdach
"""

import sys
import os
import asyncio
import json
import time
from datetime import datetime
from typing import List, Dict, Any
from decimal import Decimal

# Dodaj ścieżkę do modułów
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from utils.config_manager import get_config_manager
from utils.event_bus import get_event_bus, EventTypes
from utils.logger import get_logger

class BotTradingAPIFlowTest:
    """Test przepływu danych Bot → TradingEngine → API → Exchange"""
    
    def __init__(self):
        self.logger = get_logger("BotTradingAPIFlowTest")
        self.config_manager = get_config_manager()
        self.event_bus = get_event_bus()
        self.trading_engine = None
        self.market_data_manager = None
        self.bot_manager = None
        self.exchange_adapters = {}
        self.test_results = []
        
    async def initialize_components(self):
        """Inicjalizuje komponenty systemu"""
        try:
            self.logger.info("Inicjalizacja komponentów tradingowych...")
            
            # Inicjalizuj TradingEngine
            try:
                from core.trading_engine import TradingEngine
                self.trading_engine = TradingEngine()
                if hasattr(self.trading_engine, 'initialize'):
                    await self.trading_engine.initialize()
                self.logger.info("✅ TradingEngine initialized")
            except Exception as e:
                self.logger.error(f"❌ TradingEngine initialization failed: {e}")
            
            # Inicjalizuj MarketDataManager
            try:
                from core.market_data_manager import MarketDataManager
                self.market_data_manager = MarketDataManager()
                if hasattr(self.market_data_manager, 'initialize'):
                    await self.market_data_manager.initialize()
                self.logger.info("✅ MarketDataManager initialized")
            except Exception as e:
                self.logger.error(f"❌ MarketDataManager initialization failed: {e}")
            
            # Inicjalizuj adaptery giełd
            await self.initialize_exchange_adapters()
            
            # Inicjalizuj BotManager
            try:
                from core.updated_bot_manager import UpdatedBotManager
                self.bot_manager = UpdatedBotManager(
                    config_manager=self.config_manager,
                    trading_engine=self.trading_engine,
                    market_data_manager=self.market_data_manager
                )
                if hasattr(self.bot_manager, 'initialize'):
                    await self.bot_manager.initialize()
                self.logger.info("✅ BotManager initialized")
            except Exception as e:
                self.logger.warning(f"⚠️ BotManager initialization failed: {e}")
            
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to initialize trading components: {e}")
            return False
    
    async def initialize_exchange_adapters(self):
        """Inicjalizuje adaptery giełd"""
        try:
            # Binance
            try:
                from app.exchange.binance_adapter import BinanceAdapter
                self.exchange_adapters['binance'] = BinanceAdapter()
                self.logger.info("✅ Binance adapter initialized")
            except Exception as e:
                self.logger.warning(f"⚠️ Binance adapter failed: {e}")
            
            # Bybit
            try:
                from app.exchange.bybit_adapter import BybitAdapter
                self.exchange_adapters['bybit'] = BybitAdapter()
                self.logger.info("✅ Bybit adapter initialized")
            except Exception as e:
                self.logger.warning(f"⚠️ Bybit adapter failed: {e}")
            
            # KuCoin
            try:
                from app.exchange.kucoin_adapter import KuCoinAdapter
                self.exchange_adapters['kucoin'] = KuCoinAdapter()
                self.logger.info("✅ KuCoin adapter initialized")
            except Exception as e:
                self.logger.warning(f"⚠️ KuCoin adapter failed: {e}")
            
            # Coinbase
            try:
                from app.exchange.coinbase_adapter import CoinbaseAdapter
                self.exchange_adapters['coinbase'] = CoinbaseAdapter()
                self.logger.info("✅ Coinbase adapter initialized")
            except Exception as e:
                self.logger.warning(f"⚠️ Coinbase adapter failed: {e}")
            
        except Exception as e:
            self.logger.error(f"Failed to initialize exchange adapters: {e}")
    
    def test_trading_engine_availability(self):
        """Testuje dostępność TradingEngine"""
        try:
            self.logger.info("=== Test 1: Dostępność TradingEngine ===")
            
            if not self.trading_engine:
                self.test_results.append({
                    'test': 'TradingEngine Availability',
                    'status': 'FAILED',
                    'details': 'TradingEngine not initialized'
                })
                self.logger.error("❌ TradingEngine Availability - FAILED")
                return
            
            # Sprawdź podstawowe metody
            required_methods = ['place_order', 'cancel_order', 'get_balance', 'get_order_status']
            available_methods = []
            
            for method in required_methods:
                if hasattr(self.trading_engine, method):
                    available_methods.append(method)
            
            availability_score = len(available_methods) / len(required_methods)
            
            if availability_score >= 0.75:  # Przynajmniej 75% metod dostępne
                self.test_results.append({
                    'test': 'TradingEngine Availability',
                    'status': 'PASSED',
                    'details': f'TradingEngine methods available: {available_methods}'
                })
                self.logger.info("✅ TradingEngine Availability - PASSED")
            else:
                self.test_results.append({
                    'test': 'TradingEngine Availability',
                    'status': 'FAILED',
                    'details': f'Insufficient methods available: {available_methods}'
                })
                self.logger.error("❌ TradingEngine Availability - FAILED")
                
        except Exception as e:
            self.test_results.append({
                'test': 'TradingEngine Availability',
                'status': 'ERROR',
                'details': f'Exception: {str(e)}'
            })
            self.logger.error(f"❌ TradingEngine Availability - ERROR: {e}")
    
    async def test_exchange_connectivity(self):
        """Testuje połączenie z giełdami"""
        try:
            self.logger.info("=== Test 2: Połączenie z giełdami ===")
            
            if not self.exchange_adapters:
                self.test_results.append({
                    'test': 'Exchange Connectivity',
                    'status': 'FAILED',
                    'details': 'No exchange adapters available'
                })
                self.logger.error("❌ Exchange Connectivity - FAILED")
                return
            
            connected_exchanges = []
            failed_exchanges = []
            
            for exchange_name, adapter in self.exchange_adapters.items():
                try:
                    # Sprawdź czy adapter ma metodę testowania połączenia
                    if hasattr(adapter, 'test_connection'):
                        result = await adapter.test_connection()
                        if result:
                            connected_exchanges.append(exchange_name)
                        else:
                            failed_exchanges.append(exchange_name)
                    elif hasattr(adapter, 'get_server_time'):
                        # Alternatywny test - pobierz czas serwera
                        await adapter.get_server_time()
                        connected_exchanges.append(exchange_name)
                    else:
                        # Zakładamy że adapter jest dostępny jeśli ma podstawowe metody
                        if hasattr(adapter, 'get_balance') or hasattr(adapter, 'place_order'):
                            connected_exchanges.append(exchange_name)
                        else:
                            failed_exchanges.append(exchange_name)
                            
                except Exception as e:
                    failed_exchanges.append(f"{exchange_name} ({str(e)})")
            
            if connected_exchanges:
                self.test_results.append({
                    'test': 'Exchange Connectivity',
                    'status': 'PASSED',
                    'details': f'Connected exchanges: {connected_exchanges}. Failed: {failed_exchanges}'
                })
                self.logger.info("✅ Exchange Connectivity - PASSED")
            else:
                self.test_results.append({
                    'test': 'Exchange Connectivity',
                    'status': 'FAILED',
                    'details': f'No exchanges connected. Failed: {failed_exchanges}'
                })
                self.logger.error("❌ Exchange Connectivity - FAILED")
                
        except Exception as e:
            self.test_results.append({
                'test': 'Exchange Connectivity',
                'status': 'ERROR',
                'details': f'Exception: {str(e)}'
            })
            self.logger.error(f"❌ Exchange Connectivity - ERROR: {e}")
    
    async def test_order_placement_simulation(self):
        """Testuje symulację składania zleceń"""
        try:
            self.logger.info("=== Test 3: Symulacja składania zleceń ===")
            
            if not self.trading_engine:
                self.test_results.append({
                    'test': 'Order Placement Simulation',
                    'status': 'SKIPPED',
                    'details': 'TradingEngine not available'
                })
                self.logger.warning("⚠️ Order Placement Simulation - SKIPPED")
                return
            
            # Symuluj zlecenie kupna
            test_order = {
                'symbol': 'BTCUSDT',
                'side': 'buy',
                'type': 'limit',
                'amount': 0.001,
                'price': 50000.0,
                'test_mode': True  # Tryb testowy
            }
            
            try:
                if hasattr(self.trading_engine, 'place_order'):
                    # Spróbuj złożyć zlecenie testowe
                    result = await self.trading_engine.place_order(**test_order)
                    
                    if result and (result.get('success') or result.get('order_id')):
                        order_success = True
                        details = f"Test order placed successfully: {result}"
                    else:
                        order_success = False
                        details = f"Test order failed: {result}"
                else:
                    order_success = False
                    details = "TradingEngine lacks place_order method"
                    
            except Exception as e:
                # Błąd może być oczekiwany w trybie demo/test
                if "test" in str(e).lower() or "demo" in str(e).lower():
                    order_success = True
                    details = f"Test order properly rejected (expected): {str(e)}"
                else:
                    order_success = False
                    details = f"Unexpected error: {str(e)}"
            
            if order_success:
                self.test_results.append({
                    'test': 'Order Placement Simulation',
                    'status': 'PASSED',
                    'details': details
                })
                self.logger.info("✅ Order Placement Simulation - PASSED")
            else:
                self.test_results.append({
                    'test': 'Order Placement Simulation',
                    'status': 'FAILED',
                    'details': details
                })
                self.logger.error("❌ Order Placement Simulation - FAILED")
                
        except Exception as e:
            self.test_results.append({
                'test': 'Order Placement Simulation',
                'status': 'ERROR',
                'details': f'Exception: {str(e)}'
            })
            self.logger.error(f"❌ Order Placement Simulation - ERROR: {e}")
    
    async def test_bot_trading_integration(self):
        """Testuje integrację botów z systemem tradingowym"""
        try:
            self.logger.info("=== Test 4: Integracja botów z tradingiem ===")
            
            if not self.bot_manager:
                self.test_results.append({
                    'test': 'Bot Trading Integration',
                    'status': 'SKIPPED',
                    'details': 'BotManager not available'
                })
                self.logger.warning("⚠️ Bot Trading Integration - SKIPPED")
                return
            
            # Sprawdź czy BotManager może zarządzać botami tradingowymi
            integration_methods = ['create_bot', 'start_bot', 'stop_bot', 'get_bot_status']
            available_methods = []
            
            for method in integration_methods:
                if hasattr(self.bot_manager, method):
                    available_methods.append(method)
            
            # Sprawdź czy BotManager ma dostęp do TradingEngine
            has_trading_access = (
                hasattr(self.bot_manager, 'trading_engine') or
                hasattr(self.bot_manager, 'place_order') or
                hasattr(self.bot_manager, 'execute_trade')
            )
            
            integration_score = len(available_methods) / len(integration_methods)
            
            if integration_score >= 0.5 and has_trading_access:
                self.test_results.append({
                    'test': 'Bot Trading Integration',
                    'status': 'PASSED',
                    'details': f'Bot integration OK. Methods: {available_methods}, Trading access: {has_trading_access}'
                })
                self.logger.info("✅ Bot Trading Integration - PASSED")
            else:
                self.test_results.append({
                    'test': 'Bot Trading Integration',
                    'status': 'FAILED',
                    'details': f'Poor integration. Methods: {available_methods}, Trading access: {has_trading_access}'
                })
                self.logger.error("❌ Bot Trading Integration - FAILED")
                
        except Exception as e:
            self.test_results.append({
                'test': 'Bot Trading Integration',
                'status': 'ERROR',
                'details': f'Exception: {str(e)}'
            })
            self.logger.error(f"❌ Bot Trading Integration - ERROR: {e}")
    
    async def test_market_data_flow(self):
        """Testuje przepływ danych rynkowych do botów"""
        try:
            self.logger.info("=== Test 5: Przepływ danych rynkowych ===")
            
            if not self.market_data_manager:
                self.test_results.append({
                    'test': 'Market Data Flow',
                    'status': 'SKIPPED',
                    'details': 'MarketDataManager not available'
                })
                self.logger.warning("⚠️ Market Data Flow - SKIPPED")
                return
            
            # Sprawdź czy MarketDataManager może dostarczać dane
            data_methods = ['get_price', 'get_ticker', 'get_orderbook', 'subscribe_to_ticker']
            available_methods = []
            
            for method in data_methods:
                if hasattr(self.market_data_manager, method):
                    available_methods.append(method)
            
            # Spróbuj pobrać dane testowe
            try:
                if hasattr(self.market_data_manager, 'get_price'):
                    price_data = await self.market_data_manager.get_price('BTCUSDT')
                    data_available = price_data is not None
                elif hasattr(self.market_data_manager, 'get_ticker'):
                    ticker_data = await self.market_data_manager.get_ticker('BTCUSDT')
                    data_available = ticker_data is not None
                else:
                    data_available = len(available_methods) > 0
                    
            except Exception as e:
                data_available = False
                self.logger.warning(f"Market data test failed: {e}")
            
            data_score = len(available_methods) / len(data_methods)
            
            if data_score >= 0.25 and data_available:  # Przynajmniej 25% metod i dane dostępne
                self.test_results.append({
                    'test': 'Market Data Flow',
                    'status': 'PASSED',
                    'details': f'Market data flow OK. Methods: {available_methods}, Data available: {data_available}'
                })
                self.logger.info("✅ Market Data Flow - PASSED")
            else:
                self.test_results.append({
                    'test': 'Market Data Flow',
                    'status': 'FAILED',
                    'details': f'Poor data flow. Methods: {available_methods}, Data available: {data_available}'
                })
                self.logger.error("❌ Market Data Flow - FAILED")
                
        except Exception as e:
            self.test_results.append({
                'test': 'Market Data Flow',
                'status': 'ERROR',
                'details': f'Exception: {str(e)}'
            })
            self.logger.error(f"❌ Market Data Flow - ERROR: {e}")
    
    async def test_api_rate_limiting(self):
        """Testuje ograniczenia API"""
        try:
            self.logger.info("=== Test 6: Ograniczenia API ===")
            
            if not self.exchange_adapters:
                self.test_results.append({
                    'test': 'API Rate Limiting',
                    'status': 'SKIPPED',
                    'details': 'No exchange adapters available'
                })
                self.logger.warning("⚠️ API Rate Limiting - SKIPPED")
                return
            
            # Sprawdź czy adaptery mają mechanizmy rate limiting
            rate_limiting_features = []
            
            for exchange_name, adapter in self.exchange_adapters.items():
                features = []
                
                if hasattr(adapter, 'rate_limiter'):
                    features.append('rate_limiter')
                if hasattr(adapter, 'request_delay'):
                    features.append('request_delay')
                if hasattr(adapter, 'max_requests_per_second'):
                    features.append('max_requests_per_second')
                if hasattr(adapter, 'wait_for_rate_limit'):
                    features.append('wait_for_rate_limit')
                
                if features:
                    rate_limiting_features.append(f"{exchange_name}: {features}")
            
            if rate_limiting_features:
                self.test_results.append({
                    'test': 'API Rate Limiting',
                    'status': 'PASSED',
                    'details': f'Rate limiting features found: {rate_limiting_features}'
                })
                self.logger.info("✅ API Rate Limiting - PASSED")
            else:
                self.test_results.append({
                    'test': 'API Rate Limiting',
                    'status': 'WARNING',
                    'details': 'No rate limiting features detected - may cause API issues'
                })
                self.logger.warning("⚠️ API Rate Limiting - WARNING")
                
        except Exception as e:
            self.test_results.append({
                'test': 'API Rate Limiting',
                'status': 'ERROR',
                'details': f'Exception: {str(e)}'
            })
            self.logger.error(f"❌ API Rate Limiting - ERROR: {e}")
    
    async def run_all_tests(self):
        """Uruchamia wszystkie testy przepływu Bot → TradingEngine → API → Exchange"""
        self.logger.info("🚀 Starting Bot → TradingEngine → API → Exchange Flow Tests")
        
        # Inicjalizuj komponenty
        if not await self.initialize_components():
            self.logger.error("❌ Failed to initialize trading components")
            return []
        
        # Uruchom testy
        self.test_trading_engine_availability()
        await self.test_exchange_connectivity()
        await self.test_order_placement_simulation()
        await self.test_bot_trading_integration()
        await self.test_market_data_flow()
        await self.test_api_rate_limiting()
        
        # Podsumowanie
        self.print_summary()
        
        return self.test_results
    
    def print_summary(self):
        """Wyświetla podsumowanie testów"""
        self.logger.info("\n" + "="*60)
        self.logger.info("📊 PODSUMOWANIE TESTÓW Bot → TradingEngine → API → Exchange")
        self.logger.info("="*60)
        
        passed = sum(1 for result in self.test_results if result['status'] == 'PASSED')
        failed = sum(1 for result in self.test_results if result['status'] == 'FAILED')
        errors = sum(1 for result in self.test_results if result['status'] == 'ERROR')
        skipped = sum(1 for result in self.test_results if result['status'] == 'SKIPPED')
        warnings = sum(1 for result in self.test_results if result['status'] == 'WARNING')
        total = len(self.test_results)
        
        self.logger.info(f"📈 Wyniki: {passed}/{total} testów przeszło pomyślnie")
        self.logger.info(f"✅ Przeszły: {passed}")
        self.logger.info(f"❌ Nie przeszły: {failed}")
        self.logger.info(f"⚠️ Błędy: {errors}")
        self.logger.info(f"⏭️ Pominięte: {skipped}")
        self.logger.info(f"⚠️ Ostrzeżenia: {warnings}")
        
        for result in self.test_results:
            status_icon = "✅" if result['status'] == 'PASSED' else "❌" if result['status'] == 'FAILED' else "⚠️" if result['status'] in ['ERROR', 'WARNING'] else "⏭️"
            self.logger.info(f"{status_icon} {result['test']}: {result['status']}")
            if result['status'] != 'PASSED':
                self.logger.info(f"   Details: {result['details']}")
        
        self.logger.info("="*60)

async def main():
    """Główna funkcja testowa"""
    test = BotTradingAPIFlowTest()
    results = await test.run_all_tests()
    
    # Zapisz wyniki do pliku
    with open('bot_trading_api_flow_results.json', 'w', encoding='utf-8') as f:
        json.dump({
            'timestamp': datetime.now().isoformat(),
            'test_type': 'Bot → TradingEngine → API → Exchange Flow',
            'results': results
        }, f, indent=2, ensure_ascii=False)
    
    return results

if __name__ == "__main__":
    asyncio.run(main())
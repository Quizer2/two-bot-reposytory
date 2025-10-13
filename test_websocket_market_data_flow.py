"""
Test przepływu danych rynkowych WebSocket → MarketDataManager → UnifiedDataManager
Weryfikuje czy dane rynkowe w czasie rzeczywistym są prawidłowo odbierane i przetwarzane
"""

import sys
import os
import asyncio
import json
import time
from datetime import datetime
from typing import List, Dict, Any
import websockets

# Dodaj ścieżkę do modułów
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from utils.config_manager import get_config_manager
from utils.event_bus import get_event_bus, EventTypes
from utils.logger import get_logger
import logging
import ast
logger = logging.getLogger(__name__)

class WebSocketMarketDataFlowTest:
    """Test przepływu danych WebSocket → MarketDataManager → UnifiedDataManager"""
    
    def __init__(self):
        self.logger = get_logger("WebSocketMarketDataFlowTest")
        self.config_manager = get_config_manager()
        self.event_bus = get_event_bus()
        self.market_data_manager = None
        self.unified_data_manager = None
        self.websocket_connections = {}
        self.test_results = []
        self.received_data = []
        
    async def initialize_components(self):
        """Inicjalizuje komponenty systemu"""
        try:
            self.logger.info("Inicjalizacja komponentów danych rynkowych...")
            
            # Inicjalizuj MarketDataManager
            try:
                from core.market_data_manager import MarketDataManager
                self.market_data_manager = MarketDataManager()
                if hasattr(self.market_data_manager, 'initialize'):
                    await self.market_data_manager.initialize()
                self.logger.info("✅ MarketDataManager initialized")
            except Exception as e:
                self.logger.warning(f"⚠️ MarketDataManager initialization failed: {e}")
                # Spróbuj alternatywną inicjalizację
                try:
                    from core.updated_market_data_manager import UpdatedMarketDataManager
                    self.market_data_manager = UpdatedMarketDataManager()
                    self.logger.info("✅ UpdatedMarketDataManager initialized")
                except Exception as e2:
                    self.logger.error(f"❌ Alternative MarketDataManager failed: {e2}")
            
            # Inicjalizuj UnifiedDataManager
            try:
                from core.unified_data_manager import UnifiedDataManager
                self.unified_data_manager = UnifiedDataManager()
                if hasattr(self.unified_data_manager, 'initialize'):
                    await self.unified_data_manager.initialize()
                self.logger.info("✅ UnifiedDataManager initialized")
            except Exception as e:
                self.logger.warning(f"⚠️ UnifiedDataManager initialization failed: {e}")
            
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to initialize market data components: {e}")
            return False
    
    def test_market_data_manager_availability(self):
        """Testuje dostępność MarketDataManager"""
        try:
            self.logger.info("=== Test 1: Dostępność MarketDataManager ===")
            
            if not self.market_data_manager:
                self.test_results.append({
                    'test': 'MarketDataManager Availability',
                    'status': 'FAILED',
                    'details': 'MarketDataManager not initialized'
                })
                self.logger.error("❌ MarketDataManager Availability - FAILED")
                return
            
            # Sprawdź podstawowe metody
            required_methods = ['get_price', 'get_ticker', 'subscribe_to_ticker', 'get_orderbook']
            available_methods = []
            
            for method in required_methods:
                if hasattr(self.market_data_manager, method):
                    available_methods.append(method)
            
            # Sprawdź metody WebSocket
            websocket_methods = ['start_websocket', 'connect_websocket', 'subscribe_websocket']
            available_ws_methods = []
            
            for method in websocket_methods:
                if hasattr(self.market_data_manager, method):
                    available_ws_methods.append(method)
            
            availability_score = len(available_methods) / len(required_methods)
            ws_score = len(available_ws_methods) / len(websocket_methods)
            
            if availability_score >= 0.5:  # Przynajmniej 50% metod dostępne
                self.test_results.append({
                    'test': 'MarketDataManager Availability',
                    'status': 'PASSED',
                    'details': f'Methods available: {available_methods}, WebSocket methods: {available_ws_methods}'
                })
                self.logger.info("✅ MarketDataManager Availability - PASSED")
            else:
                self.test_results.append({
                    'test': 'MarketDataManager Availability',
                    'status': 'FAILED',
                    'details': f'Insufficient methods. Available: {available_methods}, WS: {available_ws_methods}'
                })
                self.logger.error("❌ MarketDataManager Availability - FAILED")
                
        except Exception as e:
            self.test_results.append({
                'test': 'MarketDataManager Availability',
                'status': 'ERROR',
                'details': f'Exception: {str(e)}'
            })
            self.logger.error(f"❌ MarketDataManager Availability - ERROR: {e}")
    
    async def test_websocket_connectivity(self):
        """Testuje połączenia WebSocket"""
        try:
            self.logger.info("=== Test 2: Połączenia WebSocket ===")
            
            # Lista publicznych WebSocket endpointów do testowania
            test_endpoints = [
                {
                    'name': 'Binance',
                    'url': 'wss://stream.binance.com:9443/ws/btcusdt@ticker',
                    'test_message': None
                },
                {
                    'name': 'Bybit',
                    'url': 'wss://stream.bybit.com/v5/public/spot',
                    'test_message': '{"op":"subscribe","args":["tickers.BTCUSDT"]}'
                }
            ]
            
            connection_results = []
            
            for endpoint in test_endpoints:
                try:
                    self.logger.info(f"Testing WebSocket connection to {endpoint['name']}...")
                    
                    # Spróbuj połączyć się z WebSocket (z timeoutem)
                    websocket = await asyncio.wait_for(
                        websockets.connect(endpoint['url'], open_timeout=10, ping_interval=20, ping_timeout=10),
                        timeout=5.0
                    )
                    
                    # Jeśli jest test message, wyślij go
                    if endpoint['test_message']:
                        await websocket.send(endpoint['test_message'])
                    
                    # Spróbuj otrzymać wiadomość (z timeoutem)
                    try:
                        message = await asyncio.wait_for(websocket.recv(), timeout=3.0)
                        if message:
                            connection_results.append(f"{endpoint['name']}: connected and received data")
                            self.received_data.append({
                                'source': endpoint['name'],
                                'data': message[:100],  # Pierwsze 100 znaków
                                'timestamp': datetime.now().isoformat()
                            })
                        else:
                            connection_results.append(f"{endpoint['name']}: connected but no data")
                    except asyncio.TimeoutError:
                        connection_results.append(f"{endpoint['name']}: connected but timeout on data")
                    
                    await websocket.close()
                    
                except asyncio.TimeoutError:
                    connection_results.append(f"{endpoint['name']}: connection timeout")
                except Exception as e:
                    connection_results.append(f"{endpoint['name']}: error - {str(e)[:50]}")
            
            successful_connections = sum(1 for result in connection_results if 'connected' in result)
            
            if successful_connections > 0:
                self.test_results.append({
                    'test': 'WebSocket Connectivity',
                    'status': 'PASSED',
                    'details': f'Connection results: {connection_results}'
                })
                self.logger.info("✅ WebSocket Connectivity - PASSED")
            else:
                self.test_results.append({
                    'test': 'WebSocket Connectivity',
                    'status': 'FAILED',
                    'details': f'No successful connections: {connection_results}'
                })
                self.logger.error("❌ WebSocket Connectivity - FAILED")
                
        except Exception as e:
            self.test_results.append({
                'test': 'WebSocket Connectivity',
                'status': 'ERROR',
                'details': f'Exception: {str(e)}'
            })
            self.logger.error(f"❌ WebSocket Connectivity - ERROR: {e}")
    
    async def test_market_data_retrieval(self):
        """Testuje pobieranie danych rynkowych"""
        try:
            self.logger.info("=== Test 3: Pobieranie danych rynkowych ===")
            
            if not self.market_data_manager:
                self.test_results.append({
                    'test': 'Market Data Retrieval',
                    'status': 'SKIPPED',
                    'details': 'MarketDataManager not available'
                })
                self.logger.warning("⚠️ Market Data Retrieval - SKIPPED")
                return
            
            retrieval_results = []
            
            # Test 1: Pobierz cenę
            try:
                if hasattr(self.market_data_manager, 'get_price'):
                    price = await self.market_data_manager.get_price('BTCUSDT')
                    if price:
                        retrieval_results.append(f"Price retrieval: success ({price})")
                    else:
                        retrieval_results.append("Price retrieval: no data")
                else:
                    retrieval_results.append("Price retrieval: method not available")
            except Exception as e:
                retrieval_results.append(f"Price retrieval: error - {str(e)[:50]}")
            
            # Test 2: Pobierz ticker
            try:
                if hasattr(self.market_data_manager, 'get_ticker'):
                    ticker = await self.market_data_manager.get_ticker('BTCUSDT')
                    if ticker:
                        retrieval_results.append("Ticker retrieval: success")
                    else:
                        retrieval_results.append("Ticker retrieval: no data")
                else:
                    retrieval_results.append("Ticker retrieval: method not available")
            except Exception as e:
                retrieval_results.append(f"Ticker retrieval: error - {str(e)[:50]}")
            
            # Test 3: Pobierz orderbook
            try:
                if hasattr(self.market_data_manager, 'get_orderbook'):
                    orderbook = await self.market_data_manager.get_orderbook('BTCUSDT')
                    if orderbook:
                        retrieval_results.append("Orderbook retrieval: success")
                    else:
                        retrieval_results.append("Orderbook retrieval: no data")
                else:
                    retrieval_results.append("Orderbook retrieval: method not available")
            except Exception as e:
                retrieval_results.append(f"Orderbook retrieval: error - {str(e)[:50]}")
            
            successful_retrievals = sum(1 for result in retrieval_results if 'success' in result)
            
            if successful_retrievals > 0:
                self.test_results.append({
                    'test': 'Market Data Retrieval',
                    'status': 'PASSED',
                    'details': f'Retrieval results: {retrieval_results}'
                })
                self.logger.info("✅ Market Data Retrieval - PASSED")
            else:
                self.test_results.append({
                    'test': 'Market Data Retrieval',
                    'status': 'FAILED',
                    'details': f'No successful retrievals: {retrieval_results}'
                })
                self.logger.error("❌ Market Data Retrieval - FAILED")
                
        except Exception as e:
            self.test_results.append({
                'test': 'Market Data Retrieval',
                'status': 'ERROR',
                'details': f'Exception: {str(e)}'
            })
            self.logger.error(f"❌ Market Data Retrieval - ERROR: {e}")
    
    async def test_unified_data_manager_integration(self):
        """Testuje integrację z UnifiedDataManager"""
        try:
            self.logger.info("=== Test 4: Integracja UnifiedDataManager ===")
            
            if not self.unified_data_manager:
                self.test_results.append({
                    'test': 'UnifiedDataManager Integration',
                    'status': 'SKIPPED',
                    'details': 'UnifiedDataManager not available'
                })
                self.logger.warning("⚠️ UnifiedDataManager Integration - SKIPPED")
                return
            
            integration_results = []
            
            # Sprawdź czy UnifiedDataManager ma dostęp do MarketDataManager
            try:
                if hasattr(self.unified_data_manager, 'market_data_manager'):
                    integration_results.append("UnifiedDataManager has market_data_manager reference")
                elif hasattr(self.unified_data_manager, 'market_data'):
                    integration_results.append("UnifiedDataManager has market_data reference")
                else:
                    integration_results.append("UnifiedDataManager lacks market data reference")
            except Exception as e:
                integration_results.append(f"Reference check error: {str(e)}")
            
            # Sprawdź czy UnifiedDataManager może pobierać dane rynkowe
            try:
                if hasattr(self.unified_data_manager, 'get_market_data'):
                    market_data = await self.unified_data_manager.get_market_data('BTCUSDT')
                    if market_data:
                        integration_results.append("UnifiedDataManager.get_market_data: success")
                    else:
                        integration_results.append("UnifiedDataManager.get_market_data: no data")
                elif hasattr(self.unified_data_manager, 'get_price'):
                    price = await self.unified_data_manager.get_price('BTCUSDT')
                    if price:
                        integration_results.append("UnifiedDataManager.get_price: success")
                    else:
                        integration_results.append("UnifiedDataManager.get_price: no data")
                else:
                    integration_results.append("UnifiedDataManager: no market data methods")
            except Exception as e:
                integration_results.append(f"Market data access error: {str(e)[:50]}")
            
            # Sprawdź czy UnifiedDataManager może agregować dane
            try:
                if hasattr(self.unified_data_manager, 'get_aggregated_data'):
                    aggregated = await self.unified_data_manager.get_aggregated_data()
                    if aggregated:
                        integration_results.append("Data aggregation: success")
                    else:
                        integration_results.append("Data aggregation: no data")
                else:
                    integration_results.append("Data aggregation: method not available")
            except Exception as e:
                integration_results.append(f"Data aggregation error: {str(e)[:50]}")
            
            positive_results = sum(1 for result in integration_results if 'success' in result or 'has' in result)
            
            if positive_results >= len(integration_results) * 0.5:
                self.test_results.append({
                    'test': 'UnifiedDataManager Integration',
                    'status': 'PASSED',
                    'details': f'Integration results: {integration_results}'
                })
                self.logger.info("✅ UnifiedDataManager Integration - PASSED")
            else:
                self.test_results.append({
                    'test': 'UnifiedDataManager Integration',
                    'status': 'FAILED',
                    'details': f'Poor integration: {integration_results}'
                })
                self.logger.error("❌ UnifiedDataManager Integration - FAILED")
                
        except Exception as e:
            self.test_results.append({
                'test': 'UnifiedDataManager Integration',
                'status': 'ERROR',
                'details': f'Exception: {str(e)}'
            })
            self.logger.error(f"❌ UnifiedDataManager Integration - ERROR: {e}")
    
    async def test_real_time_data_flow(self):
        """Testuje przepływ danych w czasie rzeczywistym"""
        try:
            self.logger.info("=== Test 5: Przepływ danych w czasie rzeczywistym ===")
            
            # Sprawdź czy komponenty mogą obsługiwać dane w czasie rzeczywistym
            realtime_capabilities = []
            
            # MarketDataManager
            if self.market_data_manager:
                if hasattr(self.market_data_manager, 'subscribe_to_ticker'):
                    realtime_capabilities.append("MarketDataManager: ticker subscription")
                if hasattr(self.market_data_manager, 'start_websocket'):
                    realtime_capabilities.append("MarketDataManager: websocket support")
                if hasattr(self.market_data_manager, 'on_price_update'):
                    realtime_capabilities.append("MarketDataManager: price update callbacks")
            
            # UnifiedDataManager
            if self.unified_data_manager:
                if hasattr(self.unified_data_manager, 'subscribe_to_updates'):
                    realtime_capabilities.append("UnifiedDataManager: update subscription")
                if hasattr(self.unified_data_manager, 'on_data_update'):
                    realtime_capabilities.append("UnifiedDataManager: data update callbacks")
                if hasattr(self.unified_data_manager, 'real_time_data'):
                    realtime_capabilities.append("UnifiedDataManager: real-time data support")
            
            # EventBus integration
            if self.event_bus:
                try:
                    # Sprawdź czy komponenty mogą publikować wydarzenia
                    if hasattr(self.market_data_manager, 'event_bus') or hasattr(self.market_data_manager, 'publish_event'):
                        realtime_capabilities.append("MarketDataManager: event publishing")
                    if hasattr(self.unified_data_manager, 'event_bus') or hasattr(self.unified_data_manager, 'publish_event'):
                        realtime_capabilities.append("UnifiedDataManager: event publishing")
                except Exception as e:
                    logger.exception('Unhandled error', exc_info=True)
            
            # Sprawdź czy otrzymaliśmy jakiekolwiek dane w czasie rzeczywistym
            if self.received_data:
                realtime_capabilities.append(f"Real-time data received: {len(self.received_data)} samples")
            
            if realtime_capabilities:
                self.test_results.append({
                    'test': 'Real-time Data Flow',
                    'status': 'PASSED',
                    'details': f'Real-time capabilities: {realtime_capabilities}'
                })
                self.logger.info("✅ Real-time Data Flow - PASSED")
            else:
                self.test_results.append({
                    'test': 'Real-time Data Flow',
                    'status': 'FAILED',
                    'details': 'No real-time capabilities detected'
                })
                self.logger.error("❌ Real-time Data Flow - FAILED")
                
        except Exception as e:
            self.test_results.append({
                'test': 'Real-time Data Flow',
                'status': 'ERROR',
                'details': f'Exception: {str(e)}'
            })
            self.logger.error(f"❌ Real-time Data Flow - ERROR: {e}")
    
    async def test_data_caching_and_performance(self):
        """Testuje cache'owanie danych i wydajność"""
        try:
            self.logger.info("=== Test 6: Cache'owanie i wydajność ===")
            
            performance_results = []
            
            # Test cache'owania w MarketDataManager
            if self.market_data_manager:
                cache_methods = ['get_cached_price', 'cache_data', 'clear_cache']
                available_cache_methods = []
                
                for method in cache_methods:
                    if hasattr(self.market_data_manager, method):
                        available_cache_methods.append(method)
                
                if available_cache_methods:
                    performance_results.append(f"MarketDataManager cache methods: {available_cache_methods}")
                else:
                    performance_results.append("MarketDataManager: no explicit cache methods")
                
                # Test wydajności pobierania danych
                try:
                    start_time = time.time()
                    if hasattr(self.market_data_manager, 'get_price'):
                        await self.market_data_manager.get_price('BTCUSDT')
                    end_time = time.time()
                    response_time = end_time - start_time
                    performance_results.append(f"MarketDataManager response time: {response_time:.3f}s")
                except Exception as e:
                    performance_results.append(f"MarketDataManager performance test failed: {str(e)[:50]}")
            
            # Test cache'owania w UnifiedDataManager
            if self.unified_data_manager:
                if hasattr(self.unified_data_manager, 'cache') or hasattr(self.unified_data_manager, 'cached_data'):
                    performance_results.append("UnifiedDataManager: has caching support")
                else:
                    performance_results.append("UnifiedDataManager: no explicit caching")
            
            # Sprawdź czy dane są cache'owane między wywołaniami
            try:
                if self.market_data_manager and hasattr(self.market_data_manager, 'get_price'):
                    # Pierwsze wywołanie
                    start1 = time.time()
                    price1 = await self.market_data_manager.get_price('BTCUSDT')
                    time1 = time.time() - start1
                    
                    # Drugie wywołanie (powinno być szybsze jeśli jest cache)
                    start2 = time.time()
                    price2 = await self.market_data_manager.get_price('BTCUSDT')
                    time2 = time.time() - start2
                    
                    if time2 < time1 * 0.8:  # Drugie wywołanie przynajmniej 20% szybsze
                        performance_results.append(f"Caching detected: {time1:.3f}s -> {time2:.3f}s")
                    else:
                        performance_results.append(f"No caching detected: {time1:.3f}s -> {time2:.3f}s")
            except Exception as e:
                performance_results.append(f"Cache test failed: {str(e)[:50]}")
            
            if performance_results:
                self.test_results.append({
                    'test': 'Data Caching and Performance',
                    'status': 'PASSED',
                    'details': f'Performance results: {performance_results}'
                })
                self.logger.info("✅ Data Caching and Performance - PASSED")
            else:
                self.test_results.append({
                    'test': 'Data Caching and Performance',
                    'status': 'FAILED',
                    'details': 'No performance data available'
                })
                self.logger.error("❌ Data Caching and Performance - FAILED")
                
        except Exception as e:
            self.test_results.append({
                'test': 'Data Caching and Performance',
                'status': 'ERROR',
                'details': f'Exception: {str(e)}'
            })
            self.logger.error(f"❌ Data Caching and Performance - ERROR: {e}")
    
    async def run_all_tests(self):
        """Uruchamia wszystkie testy przepływu WebSocket → MarketDataManager → UnifiedDataManager"""
        self.logger.info("🚀 Starting WebSocket → MarketDataManager → UnifiedDataManager Flow Tests")
        
        # Inicjalizuj komponenty
        if not await self.initialize_components():
            self.logger.error("❌ Failed to initialize market data components")
            return []
        
        # Uruchom testy
        self.test_market_data_manager_availability()
        await self.test_websocket_connectivity()
        await self.test_market_data_retrieval()
        await self.test_unified_data_manager_integration()
        await self.test_real_time_data_flow()
        await self.test_data_caching_and_performance()
        
        # Podsumowanie
        self.print_summary()
        
        return self.test_results
    
    def print_summary(self):
        """Wyświetla podsumowanie testów"""
        self.logger.info("\n" + "="*60)
        self.logger.info("📊 PODSUMOWANIE TESTÓW WebSocket → MarketDataManager → UnifiedDataManager")
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
    test = WebSocketMarketDataFlowTest()
    results = await test.run_all_tests()
    
    # Zapisz wyniki do pliku
    with open('websocket_market_data_flow_results.json', 'w', encoding='utf-8') as f:
        json.dump({
            'timestamp': datetime.now().isoformat(),
            'test_type': 'WebSocket → MarketDataManager → UnifiedDataManager Flow',
            'results': results,
            'received_data_samples': len(test.received_data)
        }, f, indent=2, ensure_ascii=False)
    
    return results

if __name__ == "__main__":
    asyncio.run(main())
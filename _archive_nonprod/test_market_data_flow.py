#!/usr/bin/env python3
"""
Test przepływu danych rynkowych od giełd do UI
"""

import asyncio
import sys
import os
import time
from datetime import datetime
from typing import Dict, Any

# Dodaj ścieżkę do modułów
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from core.integrated_data_manager import IntegratedDataManager
from core.market_data_manager import MarketDataManager
from core.websocket_callback_manager import WebSocketCallbackManager, WebSocketEventType, StandardizedTickerData
from core.updated_risk_manager import UpdatedRiskManager
from utils.config_manager import ConfigManager
from core.database_manager import DatabaseManager
from utils.logger import get_logger
import logging
logger = logging.getLogger(__name__)

logger = get_logger("test_market_data_flow")

class MarketDataFlowTester:
    """Tester przepływu danych rynkowych"""
    
    def __init__(self):
        self.received_ui_updates = []
        self.received_price_updates = []
        self.test_results = {}
        
    async def test_complete_data_flow(self):
        """Test kompletnego przepływu danych"""
        logger.info("🚀 Rozpoczynam test przepływu danych rynkowych")
        
        try:
            # 1. Inicjalizuj komponenty
            logger.info("📊 Inicjalizuję komponenty...")
            
            # Utwórz wymagane komponenty
            config_manager = ConfigManager()
            database_manager = DatabaseManager()
            await database_manager.initialize()
            
            risk_manager = UpdatedRiskManager()
            await risk_manager.initialize()
            
            # Utwórz IntegratedDataManager
            integrated_manager = IntegratedDataManager(
                config_manager=config_manager,
                database_manager=database_manager,
                risk_manager=risk_manager
            )
            await integrated_manager.initialize()
            
            # 2. Zarejestruj callbacki UI
            logger.info("🔗 Rejestruję callbacki UI...")
            self._register_ui_callbacks(integrated_manager)
            
            # 3. Test propagacji przez WebSocket callback manager
            logger.info("📡 Testuję propagację przez WebSocket...")
            await self._test_websocket_propagation(integrated_manager)
            
            # 4. Test propagacji przez MarketDataManager
            logger.info("💹 Testuję propagację przez MarketDataManager...")
            await self._test_market_data_propagation(integrated_manager)
            
            # 5. Test aktualizacji UI
            logger.info("🖥️ Testuję aktualizacje UI...")
            await self._test_ui_updates(integrated_manager)
            
            # 6. Analiza wyników
            self._analyze_results()
            
        except Exception as e:
            logger.error(f"❌ Błąd w teście przepływu danych: {e}")
            self.test_results['error'] = str(e)
        
        return self.test_results
    
    def _register_ui_callbacks(self, integrated_manager):
        """Rejestruje callbacki UI do testowania"""
        
        def ui_callback(event_type: str, data: Dict[str, Any]):
            """Callback UI do testowania"""
            self.received_ui_updates.append({
                'event_type': event_type,
                'data': data,
                'timestamp': datetime.now()
            })
            logger.info(f"📨 Otrzymano aktualizację UI: {event_type}")
        
        # Rejestruj różne typy callbacków
        callback_types = [
            'market_data_update',
            'ticker_update', 
            'price_update',
            'portfolio_update',
            'balance_update'
        ]
        
        for callback_type in callback_types:
            integrated_manager.subscribe_to_updates(callback_type, ui_callback)
    
    async def _test_websocket_propagation(self, integrated_manager):
        """Test propagacji przez WebSocket callback manager"""
        try:
            # Pobierz WebSocket callback manager z MarketDataManager
            ws_manager = integrated_manager.market_data_manager.ws_callback_manager
            
            # Symuluj dane ticker
            test_ticker = StandardizedTickerData(
                symbol='BTCUSDT',
                price=45000.0,
                price_change=1000.0,
                price_change_percent=2.27,
                high_24h=46000.0,
                low_24h=44000.0,
                volume_24h=1000000.0,
                timestamp=datetime.now(),
                exchange='binance',
                raw_data={}
            )
            
            # Wywołaj callback bezpośrednio
            await ws_manager.process_ticker_data('binance', test_ticker)
            
            # Czekaj na propagację
            await asyncio.sleep(0.5)
            
            self.test_results['websocket_propagation'] = {
                'status': 'success',
                'test_data': test_ticker.__dict__
            }
            
        except Exception as e:
            logger.error(f"❌ Błąd w teście WebSocket: {e}")
            self.test_results['websocket_propagation'] = {
                'status': 'error',
                'error': str(e)
            }
    
    async def _test_market_data_propagation(self, integrated_manager):
        """Test propagacji przez MarketDataManager"""
        try:
            market_manager = integrated_manager.market_data_manager
            
            # Test aktualizacji danych rynkowych
            test_data = {
                'ETHUSDT': {
                    'price': 2700.0,
                    'bid': 2699.0,
                    'ask': 2701.0,
                    'volume_24h': 500000.0,
                    'change_24h': 50.0,
                    'change_24h_percent': 1.89
                }
            }
            
            # Wywołaj aktualizację przez IntegratedDataManager
            await integrated_manager.update_market_data(test_data)
            
            # Czekaj na propagację
            await asyncio.sleep(0.5)
            
            self.test_results['market_data_propagation'] = {
                'status': 'success',
                'test_data': test_data
            }
            
        except Exception as e:
            logger.error(f"❌ Błąd w teście MarketDataManager: {e}")
            self.test_results['market_data_propagation'] = {
                'status': 'error',
                'error': str(e)
            }
    
    async def _test_ui_updates(self, integrated_manager):
        """Test aktualizacji UI"""
        try:
            # Sprawdź czy callbacki UI zostały wywołane
            ui_updates_count = len(self.received_ui_updates)
            
            # Test bezpośredniego wywołania callbacków UI
            test_price_data = {
                'symbol': 'ADAUSDT',
                'price': 0.55,
                'bid': 0.549,
                'ask': 0.551,
                'volume_24h': 100000.0,
                'change_24h': 0.01,
                'change_24h_percent': 1.85,
                'timestamp': datetime.now().isoformat()
            }
            
            # Wywołaj callback bezpośrednio
            integrated_manager._notify_ui_callbacks('market_data_update', test_price_data)
            
            # Czekaj na propagację
            await asyncio.sleep(0.2)
            
            final_updates_count = len(self.received_ui_updates)
            
            self.test_results['ui_updates'] = {
                'status': 'success',
                'initial_updates': ui_updates_count,
                'final_updates': final_updates_count,
                'new_updates': final_updates_count - ui_updates_count,
                'test_data': test_price_data
            }
            
        except Exception as e:
            logger.error(f"❌ Błąd w teście UI: {e}")
            self.test_results['ui_updates'] = {
                'status': 'error',
                'error': str(e)
            }
    
    def _analyze_results(self):
        """Analiza wyników testów"""
        logger.info("📊 Analiza wyników testów:")
        
        total_tests = 0
        passed_tests = 0
        
        for test_name, result in self.test_results.items():
            if test_name == 'error':
                continue
                
            total_tests += 1
            status = result.get('status', 'unknown')
            
            if status == 'success':
                passed_tests += 1
                logger.info(f"✅ {test_name}: PASSED")
            else:
                logger.error(f"❌ {test_name}: FAILED - {result.get('error', 'Unknown error')}")
        
        # Analiza callbacków UI
        logger.info(f"📨 Otrzymano {len(self.received_ui_updates)} aktualizacji UI:")
        for update in self.received_ui_updates:
            logger.info(f"   - {update['event_type']} w {update['timestamp']}")
        
        # Podsumowanie
        success_rate = (passed_tests / total_tests * 100) if total_tests > 0 else 0
        logger.info(f"📈 Wyniki: {passed_tests}/{total_tests} testów przeszło ({success_rate:.1f}%)")
        
        self.test_results['summary'] = {
            'total_tests': total_tests,
            'passed_tests': passed_tests,
            'success_rate': success_rate,
            'ui_updates_received': len(self.received_ui_updates)
        }

async def main():
    """Główna funkcja testowa"""
logger.info("🔍 Test przepływu danych rynkowych")
logger.info("=" * 50)
    
    tester = MarketDataFlowTester()
    results = await tester.test_complete_data_flow()
logger.info("\n📋 Podsumowanie wyników:")
logger.info("=" * 50)
    
    if 'summary' in results:
        summary = results['summary']
logger.info(f"Testy: {summary['passed_tests']}/{summary['total_tests']}")
logger.info(f"Sukces: {summary['success_rate']:.1f}%")
logger.info(f"Aktualizacje UI: {summary['ui_updates_received']}")
    
    if 'error' in results:
        pass
logger.info(f"❌ Błąd główny: {results['error']}")
    
    return results

    pass
if __name__ == "__main__":
    asyncio.run(main())
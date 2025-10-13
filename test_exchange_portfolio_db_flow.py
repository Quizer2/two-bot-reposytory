"""
Test przepływu danych Exchange → PortfolioManager → DatabaseManager
Weryfikuje czy aktualizacje portfela po transakcjach są prawidłowo zapisywane w bazie danych
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

class ExchangePortfolioDBFlowTest:
    """Test przepływu danych Exchange → PortfolioManager → DatabaseManager"""
    
    def __init__(self):
        self.logger = get_logger("ExchangePortfolioDBFlowTest")
        self.config_manager = get_config_manager()
        self.event_bus = get_event_bus()
        self.portfolio_manager = None
        self.database_manager = None
        self.exchange_adapters = {}
        self.test_results = []
        
    async def initialize_components(self):
        """Inicjalizuje komponenty systemu"""
        try:
            self.logger.info("Inicjalizacja komponentów portfela i bazy danych...")
            
            # Inicjalizuj DatabaseManager
            try:
                from core.database_manager import DatabaseManager
                self.database_manager = DatabaseManager()
                if hasattr(self.database_manager, 'initialize'):
                    await self.database_manager.initialize()
                self.logger.info("✅ DatabaseManager initialized")
            except Exception as e:
                self.logger.error(f"❌ DatabaseManager initialization failed: {e}")
            
            # Inicjalizuj PortfolioManager
            try:
                from core.portfolio_manager import PortfolioManager
                self.portfolio_manager = PortfolioManager(
                    database_manager=self.database_manager
                )
                if hasattr(self.portfolio_manager, 'initialize'):
                    await self.portfolio_manager.initialize()
                self.logger.info("✅ PortfolioManager initialized")
            except Exception as e:
                self.logger.warning(f"⚠️ PortfolioManager initialization failed: {e}")
                # Spróbuj alternatywną inicjalizację
                try:
                    from core.updated_portfolio_manager import UpdatedPortfolioManager
                    self.portfolio_manager = UpdatedPortfolioManager()
                    self.logger.info("✅ UpdatedPortfolioManager initialized")
                except Exception as e2:
                    self.logger.error(f"❌ Alternative PortfolioManager failed: {e2}")
            
            # Inicjalizuj adaptery giełd
            await self.initialize_exchange_adapters()
            
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to initialize portfolio components: {e}")
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
            
        except Exception as e:
            self.logger.error(f"Failed to initialize exchange adapters: {e}")
    
    def test_database_availability(self):
        """Testuje dostępność bazy danych"""
        try:
            self.logger.info("=== Test 1: Dostępność bazy danych ===")
            
            if not self.database_manager:
                self.test_results.append({
                    'test': 'Database Availability',
                    'status': 'FAILED',
                    'details': 'DatabaseManager not initialized'
                })
                self.logger.error("❌ Database Availability - FAILED")
                return
            
            # Sprawdź podstawowe metody bazy danych
            required_methods = ['get_portfolio', 'save_portfolio', 'get_trades', 'save_trade']
            available_methods = []
            
            for method in required_methods:
                if hasattr(self.database_manager, method):
                    available_methods.append(method)
            
            # Sprawdź czy baza danych jest dostępna
            try:
                if hasattr(self.database_manager, 'test_connection'):
                    db_connected = self.database_manager.test_connection()
                elif hasattr(self.database_manager, 'get_portfolio'):
                    # Spróbuj pobrać portfel jako test
                    portfolio = self.database_manager.get_portfolio()
                    db_connected = True
                else:
                    db_connected = len(available_methods) > 0
                    
            except Exception as e:
                db_connected = False
                self.logger.warning(f"Database connection test failed: {e}")
            
            availability_score = len(available_methods) / len(required_methods)
            
            if availability_score >= 0.5 and db_connected:  # Przynajmniej 50% metod i połączenie
                self.test_results.append({
                    'test': 'Database Availability',
                    'status': 'PASSED',
                    'details': f'Database methods available: {available_methods}, Connected: {db_connected}'
                })
                self.logger.info("✅ Database Availability - PASSED")
            else:
                self.test_results.append({
                    'test': 'Database Availability',
                    'status': 'FAILED',
                    'details': f'Insufficient database access. Methods: {available_methods}, Connected: {db_connected}'
                })
                self.logger.error("❌ Database Availability - FAILED")
                
        except Exception as e:
            self.test_results.append({
                'test': 'Database Availability',
                'status': 'ERROR',
                'details': f'Exception: {str(e)}'
            })
            self.logger.error(f"❌ Database Availability - ERROR: {e}")
    
    async def test_portfolio_manager_functionality(self):
        """Testuje funkcjonalność PortfolioManager"""
        try:
            self.logger.info("=== Test 2: Funkcjonalność PortfolioManager ===")
            
            if not self.portfolio_manager:
                self.test_results.append({
                    'test': 'PortfolioManager Functionality',
                    'status': 'FAILED',
                    'details': 'PortfolioManager not initialized'
                })
                self.logger.error("❌ PortfolioManager Functionality - FAILED")
                return
            
            # Sprawdź podstawowe metody PortfolioManager
            required_methods = ['get_balance', 'update_balance', 'get_portfolio_value', 'add_transaction']
            available_methods = []
            
            for method in required_methods:
                if hasattr(self.portfolio_manager, method):
                    available_methods.append(method)
            
            # Sprawdź czy PortfolioManager może pobierać dane
            try:
                if hasattr(self.portfolio_manager, 'get_portfolio_summary'):
                    portfolio_data = await self.portfolio_manager.get_portfolio_summary()
                    data_available = portfolio_data is not None
                elif hasattr(self.portfolio_manager, 'get_balance'):
                    balance_data = await self.portfolio_manager.get_balance('USDT')
                    data_available = balance_data is not None
                else:
                    data_available = len(available_methods) > 0
                    
            except Exception as e:
                data_available = False
                self.logger.warning(f"Portfolio data test failed: {e}")
            
            functionality_score = len(available_methods) / len(required_methods)
            
            if functionality_score >= 0.5 and data_available:
                self.test_results.append({
                    'test': 'PortfolioManager Functionality',
                    'status': 'PASSED',
                    'details': f'Portfolio methods available: {available_methods}, Data available: {data_available}'
                })
                self.logger.info("✅ PortfolioManager Functionality - PASSED")
            else:
                self.test_results.append({
                    'test': 'PortfolioManager Functionality',
                    'status': 'FAILED',
                    'details': f'Poor functionality. Methods: {available_methods}, Data available: {data_available}'
                })
                self.logger.error("❌ PortfolioManager Functionality - FAILED")
                
        except Exception as e:
            self.test_results.append({
                'test': 'PortfolioManager Functionality',
                'status': 'ERROR',
                'details': f'Exception: {str(e)}'
            })
            self.logger.error(f"❌ PortfolioManager Functionality - ERROR: {e}")
    
    async def test_exchange_balance_sync(self):
        """Testuje synchronizację sald z giełd"""
        try:
            self.logger.info("=== Test 3: Synchronizacja sald z giełd ===")
            
            if not self.exchange_adapters:
                self.test_results.append({
                    'test': 'Exchange Balance Sync',
                    'status': 'SKIPPED',
                    'details': 'No exchange adapters available'
                })
                self.logger.warning("⚠️ Exchange Balance Sync - SKIPPED")
                return
            
            sync_results = []
            
            for exchange_name, adapter in self.exchange_adapters.items():
                try:
                    # Sprawdź czy adapter może pobierać salda
                    if hasattr(adapter, 'get_balance'):
                        balance = await adapter.get_balance()
                        if balance:
                            sync_results.append(f"{exchange_name}: balance retrieved")
                        else:
                            sync_results.append(f"{exchange_name}: no balance data")
                    elif hasattr(adapter, 'get_account_info'):
                        account_info = await adapter.get_account_info()
                        if account_info:
                            sync_results.append(f"{exchange_name}: account info retrieved")
                        else:
                            sync_results.append(f"{exchange_name}: no account data")
                    else:
                        sync_results.append(f"{exchange_name}: no balance methods")
                        
                except Exception as e:
                    sync_results.append(f"{exchange_name}: error - {str(e)}")
            
            # Sprawdź czy PortfolioManager może aktualizować salda z giełd
            portfolio_sync = False
            if self.portfolio_manager:
                if hasattr(self.portfolio_manager, 'sync_with_exchange'):
                    portfolio_sync = True
                elif hasattr(self.portfolio_manager, 'update_from_exchange'):
                    portfolio_sync = True
                elif hasattr(self.portfolio_manager, 'refresh_balances'):
                    portfolio_sync = True
            
            successful_syncs = sum(1 for result in sync_results if 'retrieved' in result)
            
            if successful_syncs > 0 and portfolio_sync:
                self.test_results.append({
                    'test': 'Exchange Balance Sync',
                    'status': 'PASSED',
                    'details': f'Sync results: {sync_results}, Portfolio sync capability: {portfolio_sync}'
                })
                self.logger.info("✅ Exchange Balance Sync - PASSED")
            elif successful_syncs > 0:
                self.test_results.append({
                    'test': 'Exchange Balance Sync',
                    'status': 'WARNING',
                    'details': f'Exchange data available but portfolio sync limited. Results: {sync_results}'
                })
                self.logger.warning("⚠️ Exchange Balance Sync - WARNING")
            else:
                self.test_results.append({
                    'test': 'Exchange Balance Sync',
                    'status': 'FAILED',
                    'details': f'No successful syncs. Results: {sync_results}'
                })
                self.logger.error("❌ Exchange Balance Sync - FAILED")
                
        except Exception as e:
            self.test_results.append({
                'test': 'Exchange Balance Sync',
                'status': 'ERROR',
                'details': f'Exception: {str(e)}'
            })
            self.logger.error(f"❌ Exchange Balance Sync - ERROR: {e}")
    
    async def test_transaction_recording(self):
        """Testuje zapisywanie transakcji"""
        try:
            self.logger.info("=== Test 4: Zapisywanie transakcji ===")
            
            if not self.portfolio_manager or not self.database_manager:
                self.test_results.append({
                    'test': 'Transaction Recording',
                    'status': 'SKIPPED',
                    'details': 'PortfolioManager or DatabaseManager not available'
                })
                self.logger.warning("⚠️ Transaction Recording - SKIPPED")
                return
            
            # Symuluj transakcję
            test_transaction = {
                'id': f'test_tx_{int(time.time())}',
                'symbol': 'BTCUSDT',
                'side': 'buy',
                'amount': 0.001,
                'price': 50000.0,
                'timestamp': datetime.now().isoformat(),
                'exchange': 'test_exchange'
            }
            
            recording_success = False
            recording_details = []
            
            try:
                # Spróbuj zapisać przez PortfolioManager
                if hasattr(self.portfolio_manager, 'add_transaction'):
                    result = await self.portfolio_manager.add_transaction(test_transaction)
                    if result:
                        recording_details.append("PortfolioManager.add_transaction: success")
                        recording_success = True
                    else:
                        recording_details.append("PortfolioManager.add_transaction: failed")
                elif hasattr(self.portfolio_manager, 'record_trade'):
                    result = await self.portfolio_manager.record_trade(test_transaction)
                    if result:
                        recording_details.append("PortfolioManager.record_trade: success")
                        recording_success = True
                    else:
                        recording_details.append("PortfolioManager.record_trade: failed")
                else:
                    recording_details.append("PortfolioManager: no transaction methods")
                
                # Spróbuj zapisać przez DatabaseManager
                if hasattr(self.database_manager, 'save_trade'):
                    result = self.database_manager.save_trade(test_transaction)
                    if result:
                        recording_details.append("DatabaseManager.save_trade: success")
                        recording_success = True
                    else:
                        recording_details.append("DatabaseManager.save_trade: failed")
                elif hasattr(self.database_manager, 'add_transaction'):
                    result = self.database_manager.add_transaction(test_transaction)
                    if result:
                        recording_details.append("DatabaseManager.add_transaction: success")
                        recording_success = True
                    else:
                        recording_details.append("DatabaseManager.add_transaction: failed")
                else:
                    recording_details.append("DatabaseManager: no transaction methods")
                    
            except Exception as e:
                recording_details.append(f"Transaction recording error: {str(e)}")
            
            if recording_success:
                self.test_results.append({
                    'test': 'Transaction Recording',
                    'status': 'PASSED',
                    'details': f'Transaction recording successful: {recording_details}'
                })
                self.logger.info("✅ Transaction Recording - PASSED")
            else:
                self.test_results.append({
                    'test': 'Transaction Recording',
                    'status': 'FAILED',
                    'details': f'Transaction recording failed: {recording_details}'
                })
                self.logger.error("❌ Transaction Recording - FAILED")
                
        except Exception as e:
            self.test_results.append({
                'test': 'Transaction Recording',
                'status': 'ERROR',
                'details': f'Exception: {str(e)}'
            })
            self.logger.error(f"❌ Transaction Recording - ERROR: {e}")
    
    async def test_portfolio_persistence(self):
        """Testuje trwałość danych portfela"""
        try:
            self.logger.info("=== Test 5: Trwałość danych portfela ===")
            
            if not self.database_manager:
                self.test_results.append({
                    'test': 'Portfolio Persistence',
                    'status': 'SKIPPED',
                    'details': 'DatabaseManager not available'
                })
                self.logger.warning("⚠️ Portfolio Persistence - SKIPPED")
                return
            
            persistence_tests = []
            
            # Test 1: Sprawdź czy można pobrać dane portfela
            try:
                if hasattr(self.database_manager, 'get_portfolio'):
                    portfolio_data = self.database_manager.get_portfolio()
                    if portfolio_data is not None:
                        persistence_tests.append("Portfolio retrieval: success")
                    else:
                        persistence_tests.append("Portfolio retrieval: no data")
                else:
                    persistence_tests.append("Portfolio retrieval: method not available")
            except Exception as e:
                persistence_tests.append(f"Portfolio retrieval: error - {str(e)}")
            
            # Test 2: Sprawdź czy można zapisać dane portfela
            try:
                test_portfolio = {
                    'balances': {'USDT': 1000.0, 'BTC': 0.01},
                    'total_value': 1500.0,
                    'last_updated': datetime.now().isoformat()
                }
                
                if hasattr(self.database_manager, 'save_portfolio'):
                    result = self.database_manager.save_portfolio(test_portfolio)
                    if result:
                        persistence_tests.append("Portfolio saving: success")
                    else:
                        persistence_tests.append("Portfolio saving: failed")
                else:
                    persistence_tests.append("Portfolio saving: method not available")
            except Exception as e:
                persistence_tests.append(f"Portfolio saving: error - {str(e)}")
            
            # Test 3: Sprawdź czy można pobrać historię transakcji
            try:
                if hasattr(self.database_manager, 'get_trades'):
                    trades_data = self.database_manager.get_trades()
                    if trades_data is not None:
                        persistence_tests.append("Trades retrieval: success")
                    else:
                        persistence_tests.append("Trades retrieval: no data")
                else:
                    persistence_tests.append("Trades retrieval: method not available")
            except Exception as e:
                persistence_tests.append(f"Trades retrieval: error - {str(e)}")
            
            successful_tests = sum(1 for test in persistence_tests if 'success' in test)
            total_tests = len(persistence_tests)
            
            if successful_tests >= total_tests * 0.6:  # Przynajmniej 60% testów przeszło
                self.test_results.append({
                    'test': 'Portfolio Persistence',
                    'status': 'PASSED',
                    'details': f'Persistence tests: {persistence_tests}'
                })
                self.logger.info("✅ Portfolio Persistence - PASSED")
            else:
                self.test_results.append({
                    'test': 'Portfolio Persistence',
                    'status': 'FAILED',
                    'details': f'Poor persistence. Tests: {persistence_tests}'
                })
                self.logger.error("❌ Portfolio Persistence - FAILED")
                
        except Exception as e:
            self.test_results.append({
                'test': 'Portfolio Persistence',
                'status': 'ERROR',
                'details': f'Exception: {str(e)}'
            })
            self.logger.error(f"❌ Portfolio Persistence - ERROR: {e}")
    
    async def test_data_consistency(self):
        """Testuje spójność danych między komponentami"""
        try:
            self.logger.info("=== Test 6: Spójność danych ===")
            
            if not self.portfolio_manager or not self.database_manager:
                self.test_results.append({
                    'test': 'Data Consistency',
                    'status': 'SKIPPED',
                    'details': 'Required components not available'
                })
                self.logger.warning("⚠️ Data Consistency - SKIPPED")
                return
            
            consistency_checks = []
            
            # Sprawdź czy PortfolioManager i DatabaseManager używają tych samych danych
            try:
                # Pobierz dane z PortfolioManager
                portfolio_data = None
                if hasattr(self.portfolio_manager, 'get_portfolio_summary'):
                    portfolio_data = await self.portfolio_manager.get_portfolio_summary()
                elif hasattr(self.portfolio_manager, 'get_balances'):
                    portfolio_data = await self.portfolio_manager.get_balances()
                
                # Pobierz dane z DatabaseManager
                db_data = None
                if hasattr(self.database_manager, 'get_portfolio'):
                    db_data = self.database_manager.get_portfolio()
                
                if portfolio_data and db_data:
                    consistency_checks.append("Both components have data")
                    # Sprawdź czy dane są podobne (podstawowa weryfikacja)
                    if isinstance(portfolio_data, dict) and isinstance(db_data, dict):
                        common_keys = set(portfolio_data.keys()) & set(db_data.keys())
                        if common_keys:
                            consistency_checks.append(f"Common data keys: {list(common_keys)}")
                        else:
                            consistency_checks.append("No common data keys")
                    else:
                        consistency_checks.append("Data format consistency check skipped")
                elif portfolio_data:
                    consistency_checks.append("Only PortfolioManager has data")
                elif db_data:
                    consistency_checks.append("Only DatabaseManager has data")
                else:
                    consistency_checks.append("No data available from either component")
                    
            except Exception as e:
                consistency_checks.append(f"Data comparison error: {str(e)}")
            
            # Sprawdź czy komponenty mogą komunikować się ze sobą
            try:
                if hasattr(self.portfolio_manager, 'database_manager'):
                    consistency_checks.append("PortfolioManager has database reference")
                elif hasattr(self.portfolio_manager, 'db'):
                    consistency_checks.append("PortfolioManager has db reference")
                else:
                    consistency_checks.append("PortfolioManager lacks database reference")
            except Exception as e:
                consistency_checks.append(f"Component integration error: {str(e)}")
            
            positive_checks = sum(1 for check in consistency_checks if any(word in check.lower() for word in ['has', 'common', 'both', 'success']))
            
            if positive_checks >= len(consistency_checks) * 0.5:
                self.test_results.append({
                    'test': 'Data Consistency',
                    'status': 'PASSED',
                    'details': f'Consistency checks: {consistency_checks}'
                })
                self.logger.info("✅ Data Consistency - PASSED")
            else:
                self.test_results.append({
                    'test': 'Data Consistency',
                    'status': 'FAILED',
                    'details': f'Poor consistency. Checks: {consistency_checks}'
                })
                self.logger.error("❌ Data Consistency - FAILED")
                
        except Exception as e:
            self.test_results.append({
                'test': 'Data Consistency',
                'status': 'ERROR',
                'details': f'Exception: {str(e)}'
            })
            self.logger.error(f"❌ Data Consistency - ERROR: {e}")
    
    async def run_all_tests(self):
        """Uruchamia wszystkie testy przepływu Exchange → PortfolioManager → DatabaseManager"""
        self.logger.info("🚀 Starting Exchange → PortfolioManager → DatabaseManager Flow Tests")
        
        # Inicjalizuj komponenty
        if not await self.initialize_components():
            self.logger.error("❌ Failed to initialize portfolio components")
            return []
        
        # Uruchom testy
        self.test_database_availability()
        await self.test_portfolio_manager_functionality()
        await self.test_exchange_balance_sync()
        await self.test_transaction_recording()
        await self.test_portfolio_persistence()
        await self.test_data_consistency()
        
        # Podsumowanie
        self.print_summary()
        
        return self.test_results
    
    def print_summary(self):
        """Wyświetla podsumowanie testów"""
        self.logger.info("\n" + "="*60)
        self.logger.info("📊 PODSUMOWANIE TESTÓW Exchange → PortfolioManager → DatabaseManager")
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
    test = ExchangePortfolioDBFlowTest()
    results = await test.run_all_tests()
    
    # Zapisz wyniki do pliku
    with open('exchange_portfolio_db_flow_results.json', 'w', encoding='utf-8') as f:
        json.dump({
            'timestamp': datetime.now().isoformat(),
            'test_type': 'Exchange → PortfolioManager → DatabaseManager Flow',
            'results': results
        }, f, indent=2, ensure_ascii=False)
    
    return results

if __name__ == "__main__":
    asyncio.run(main())
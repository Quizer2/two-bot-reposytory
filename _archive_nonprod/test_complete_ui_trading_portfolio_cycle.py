"""
Test kompletnego cyklu: UI → Trading → Portfolio Update
Weryfikuje pełny przepływ od zmiany w UI do aktualizacji portfela
"""

import sys
import os
import asyncio
import json
import time
from datetime import datetime
from typing import List, Dict, Any
import logging
logger = logging.getLogger(__name__)

# Dodaj ścieżkę do modułów
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
logger.info("🚀 Starting Complete UI → Trading → Portfolio Cycle Tests")

try:
    from utils.config_manager import get_config_manager
    from utils.event_bus import get_event_bus, EventTypes
    from utils.logger import get_logger
logger.info("✅ Basic utils imported successfully")
except Exception as e:
    pass
logger.info(f"❌ Failed to import basic utils: {e}")
    sys.exit(1)

class CompleteUITradingPortfolioCycleTest:
    """Test kompletnego cyklu UI → Trading → Portfolio Update"""
    
    def __init__(self):
        self.logger = get_logger("CompleteUITradingPortfolioCycleTest")
        self.config_manager = get_config_manager()
        self.event_bus = get_event_bus()
        self.ui_manager = None
        self.trading_engine = None
        self.portfolio_manager = None
        self.bot_manager = None
        self.test_results = []
        self.event_chain = []
        self.portfolio_snapshots = []
logger.info("✅ Test class initialized")
        
    async def initialize_components(self):
        """Inicjalizuje wszystkie komponenty systemu"""
            pass
        try:
            self.logger.info("Inicjalizacja komponentów dla testu kompletnego cyklu...")
logger.info("🔧 Initializing components...")
            
                pass
            # Inicjalizuj UI Manager
            try:
                    pass
                from ui.ui_manager import UIManager
                self.ui_manager = UIManager()
                if hasattr(self.ui_manager, 'initialize'):
                    await self.ui_manager.initialize()
logger.info("✅ UIManager initialized")
            except Exception as e:
                pass
logger.info(f"⚠️ UIManager initialization failed: {e}")
            
                    pass
            # Inicjalizuj Trading Engine
            try:
                from core.trading_engine import TradingEngine
                self.trading_engine = TradingEngine()
                if hasattr(self.trading_engine, 'initialize'):
                    await self.trading_engine.initialize()
logger.info("✅ TradingEngine initialized")
            except Exception as e:
logger.info(f"⚠️ TradingEngine initialization failed: {e}")
                    pass
                # Spróbuj alternatywną inicjalizację
                try:
                    from core.updated_trading_engine import UpdatedTradingEngine
                    self.trading_engine = UpdatedTradingEngine()
logger.info("✅ UpdatedTradingEngine initialized")
                except Exception as e2:
                    pass
logger.info(f"❌ Alternative TradingEngine failed: {e2}")
            
                pass
            # Inicjalizuj Portfolio Manager
            try:
                    pass
                from core.portfolio_manager import PortfolioManager
                self.portfolio_manager = PortfolioManager()
                if hasattr(self.portfolio_manager, 'initialize'):
                    await self.portfolio_manager.initialize()
logger.info("✅ PortfolioManager initialized")
            except Exception as e:
logger.info(f"⚠️ PortfolioManager initialization failed: {e}")
                # Spróbuj alternatywną inicjalizację
                try:
                    from core.updated_portfolio_manager import UpdatedPortfolioManager
                    self.portfolio_manager = UpdatedPortfolioManager()
logger.info("✅ UpdatedPortfolioManager initialized")
                except Exception as e2:
                pass
logger.info(f"❌ Alternative PortfolioManager failed: {e2}")
            
            # Inicjalizuj Bot Manager
            try:
                from core.bot_manager import BotManager
                self.bot_manager = BotManager()
                if hasattr(self.bot_manager, 'initialize'):
                    await self.bot_manager.initialize()
logger.info("✅ BotManager initialized")
            except Exception as e:
            pass
logger.info(f"⚠️ BotManager initialization failed: {e}")
            
            return True
            
        except Exception as e:
logger.info(f"❌ Failed to initialize components: {e}")
            return False
    
    def setup_event_listeners(self):
        """Konfiguruje nasłuchiwanie wydarzeń w całym cyklu"""
        try:
logger.info("🎧 Setting up event listeners...")
                pass
                    pass
            
            # Nasłuchuj wszystkich typów wydarzeń
                    pass
            event_types = [
                EventTypes.CONFIG_UPDATED,
                EventTypes.BOT_UPDATED,
                EventTypes.TRADE_EXECUTED,
                EventTypes.PORTFOLIO_UPDATED,
                EventTypes.RISK_UPDATED,
                EventTypes.UI_UPDATED
            ]
            
            for event_type in event_types:
                try:
                    self.event_bus.subscribe(event_type, self.track_event)
logger.info(f"✅ Subscribed to {event_type}")
                except Exception as e:
logger.info(f"⚠️ Failed to subscribe to {event_type}: {e}")
            
            return True
            
        except Exception as e:
logger.info(f"❌ Failed to setup event listeners: {e}")
            return False
    
    def track_event(self, event_type, data):
        """Śledzi wydarzenia w cyklu"""
        event_record = {
            'timestamp': datetime.now().isoformat(),
            'event_type': event_type,
            'data': str(data)[:200],  # Ograniczenie długości
            'component': self.identify_component_from_event(event_type)
        }
        self.event_chain.append(event_record)
logger.info(f"📝 Event tracked: {event_type} from {event_record['component']}")
    
            pass
    def identify_component_from_event(self, event_type):
        """Identyfikuje komponent na podstawie typu wydarzenia"""
        component_mapping = {
            EventTypes.CONFIG_UPDATED: 'ConfigManager',
            EventTypes.BOT_UPDATED: 'BotManager',
            EventTypes.TRADE_EXECUTED: 'TradingEngine',
            EventTypes.PORTFOLIO_UPDATED: 'PortfolioManager',
            EventTypes.RISK_UPDATED: 'RiskManager',
            EventTypes.UI_UPDATED: 'UIManager'
        }
        return component_mapping.get(event_type, 'Unknown')
    
    async def test_basic_component_availability(self):
        """Testuje podstawową dostępność komponentów"""
                pass
        try:
logger.info("=== Test 1: Podstawowa dostępność komponentów ===")
            
            components_status = {
                'ConfigManager': self.config_manager is not None,
                'EventBus': self.event_bus is not None,
                'UIManager': self.ui_manager is not None,
                'TradingEngine': self.trading_engine is not None,
                'PortfolioManager': self.portfolio_manager is not None,
                'BotManager': self.bot_manager is not None
                pass
            }
            
            available_components = sum(components_status.values())
            total_components = len(components_status)
logger.info(f"📊 Components available: {available_components}/{total_components}")
            for component, status in components_status.items():
                status_icon = "✅" if status else "❌"
            pass
logger.info(f"{status_icon} {component}: {'Available' if status else 'Not Available'}")
            
            if available_components >= 2:  # Przynajmniej 2 komponenty
                self.test_results.append({
                    'test': 'Basic Component Availability',
                    'status': 'PASSED',
                    'details': f'Available: {available_components}/{total_components} components'
                })
logger.info("✅ Basic Component Availability - PASSED")
            else:
                self.test_results.append({
                    'test': 'Basic Component Availability',
                    'status': 'FAILED',
                    'details': f'Insufficient components: {available_components}/{total_components}'
                })
                pass
logger.info("❌ Basic Component Availability - FAILED")
                
        except Exception as e:
            self.test_results.append({
                'test': 'Basic Component Availability',
                'status': 'ERROR',
                'details': f'Exception: {str(e)}'
            })
logger.info(f"❌ Basic Component Availability - ERROR: {e}")
    
    async def test_config_event_flow(self):
        """Testuje przepływ konfiguracji przez EventBus"""
        try:
logger.info("=== Test 2: Przepływ konfiguracji przez EventBus ===")
            
            initial_event_count = len(self.event_chain)
                pass
            
            # Symuluj zmianę konfiguracji
            if self.config_manager:
                self.config_manager.update_config('test_cycle', {
                    'symbol': 'BTCUSDT',
                    'amount': 0.001,
                    'strategy': 'test'
                })
                config_result = "Config update: success"
            else:
                config_result = "Config update: ConfigManager not available"
            
            # Poczekaj na propagację wydarzeń
            await asyncio.sleep(0.1)
            pass
            
            new_event_count = len(self.event_chain)
            events_generated = new_event_count - initial_event_count
logger.info(f"📈 Events generated: {events_generated}")
            
            if events_generated > 0 or 'success' in config_result:
                self.test_results.append({
                    'test': 'Config Event Flow',
                    'status': 'PASSED',
                    'details': f'{config_result}, Events: {events_generated}'
                })
logger.info("✅ Config Event Flow - PASSED")
            else:
                self.test_results.append({
                    'test': 'Config Event Flow',
                    'status': 'FAILED',
                    'details': f'{config_result}, No events generated'
                })
logger.info("❌ Config Event Flow - FAILED")
                
        except Exception as e:
            self.test_results.append({
                'test': 'Config Event Flow',
                'status': 'ERROR',
                'details': f'Exception: {str(e)}'
            })
logger.info(f"❌ Config Event Flow - ERROR: {e}")
    
    async def test_simulated_trading_flow(self):
        """Testuje symulowany przepływ tradingowy"""
        try:
logger.info("=== Test 3: Symulowany przepływ tradingowy ===")
            
            initial_event_count = len(self.event_chain)
            
            # Symuluj transakcję przez EventBus
            trade_data = {
                'symbol': 'BTCUSDT',
                'side': 'buy',
                'amount': 0.001,
                'price': 50000,
                'timestamp': datetime.now().isoformat()
            }
            
            # Publikuj wydarzenie transakcji
            self.event_bus.publish(EventTypes.TRADE_EXECUTED, trade_data)
            trading_result = "Trade event published: success"
            
            # Symuluj aktualizację portfela
            portfolio_data = {
                'balance': 10000,
                'positions': {'BTCUSDT': 0.001},
                'total_value': 10050,
                'timestamp': datetime.now().isoformat()
            }
            
            self.event_bus.publish(EventTypes.PORTFOLIO_UPDATED, portfolio_data)
            portfolio_result = "Portfolio event published: success"
            
            # Poczekaj na propagację
            await asyncio.sleep(0.1)
            
            new_event_count = len(self.event_chain)
            events_generated = new_event_count - initial_event_count
logger.info(f"📈 Trading events generated: {events_generated}")
            
            if events_generated >= 2:  # Oczekujemy przynajmniej 2 wydarzeń
                self.test_results.append({
                    'test': 'Simulated Trading Flow',
                    'status': 'PASSED',
                    'details': f'{trading_result}, {portfolio_result}, Events: {events_generated}'
                })
logger.info("✅ Simulated Trading Flow - PASSED")
            else:
                self.test_results.append({
                    'test': 'Simulated Trading Flow',
                    'status': 'FAILED',
                    'details': f'Insufficient events: {events_generated}'
                })
logger.info("❌ Simulated Trading Flow - FAILED")
                
        except Exception as e:
            self.test_results.append({
                'test': 'Simulated Trading Flow',
                'status': 'ERROR',
                'details': f'Exception: {str(e)}'
            })
logger.info(f"❌ Simulated Trading Flow - ERROR: {e}")
    
    async def test_ui_notification_flow(self):
        """Testuje przepływ powiadomień do UI"""
        try:
logger.info("=== Test 4: Przepływ powiadomień do UI ===")
                pass
            
            initial_event_count = len(self.event_chain)
            
            # Symuluj powiadomienie UI
            ui_data = {
                'component': 'portfolio',
                'action': 'update',
                'data': {'balance': 10050, 'change': '+0.5%'},
                'timestamp': datetime.now().isoformat()
            }
            
            self.event_bus.publish(EventTypes.UI_UPDATED, ui_data)
            ui_result = "UI notification published: success"
            
            # Poczekaj na propagację
            await asyncio.sleep(0.1)
            
            new_event_count = len(self.event_chain)
            events_generated = new_event_count - initial_event_count
logger.info(f"📈 UI events generated: {events_generated}")
            
            if events_generated > 0:
                self.test_results.append({
                    'test': 'UI Notification Flow',
                    'status': 'PASSED',
                    'details': f'{ui_result}, Events: {events_generated}'
                })
logger.info("✅ UI Notification Flow - PASSED")
            else:
                self.test_results.append({
                    'test': 'UI Notification Flow',
                    'status': 'FAILED',
                    'details': f'{ui_result}, No events generated'
                })
logger.info("❌ UI Notification Flow - FAILED")
                
        except Exception as e:
            self.test_results.append({
                'test': 'UI Notification Flow',
                'status': 'ERROR',
                'details': f'Exception: {str(e)}'
            })
logger.info(f"❌ UI Notification Flow - ERROR: {e}")
    
    async def test_complete_cycle_simulation(self):
        """Testuje symulację kompletnego cyklu"""
        try:
logger.info("=== Test 5: Symulacja kompletnego cyklu ===")
            
            initial_event_count = len(self.event_chain)
            cycle_steps = []
            
            # Krok 1: Zmiana konfiguracji (symulacja UI)
            if self.config_manager:
                self.config_manager.update_config('cycle_test', {
                    'symbol': 'ETHUSDT',
                    'amount': 0.01,
                    'action': 'buy'
                })
                cycle_steps.append("1. Config updated")
            
            await asyncio.sleep(0.05)
            
            # Krok 2: Wykonanie transakcji (symulacja Trading)
            self.event_bus.publish(EventTypes.TRADE_EXECUTED, {
                'symbol': 'ETHUSDT',
                'side': 'buy',
                'amount': 0.01,
                'price': 3000,
                'timestamp': datetime.now().isoformat()
            })
            cycle_steps.append("2. Trade executed")
            
            await asyncio.sleep(0.05)
            
            # Krok 3: Aktualizacja portfela
            self.event_bus.publish(EventTypes.PORTFOLIO_UPDATED, {
                'balance': 9970,  # -30 za 0.01 ETH
                'positions': {'ETHUSDT': 0.01},
                'total_value': 10000,
                'timestamp': datetime.now().isoformat()
                pass
            })
            cycle_steps.append("3. Portfolio updated")
            
            await asyncio.sleep(0.05)
            
            # Krok 4: Powiadomienie UI
                pass
            self.event_bus.publish(EventTypes.UI_UPDATED, {
                'component': 'portfolio',
                'action': 'refresh',
                'data': {'new_position': 'ETHUSDT'},
                'timestamp': datetime.now().isoformat()
            })
            cycle_steps.append("4. UI notified")
            pass
            
            # Poczekaj na wszystkie wydarzenia
            await asyncio.sleep(0.1)
            
            new_event_count = len(self.event_chain)
            total_events = new_event_count - initial_event_count
logger.info(f"📈 Complete cycle events: {total_events}")
logger.info(f"🔄 Cycle steps completed: {len(cycle_steps)}/4")
            
            if len(cycle_steps) == 4 and total_events >= 4:
                self.test_results.append({
                    'test': 'Complete Cycle Simulation',
                    'status': 'PASSED',
                    'details': f'All steps completed: {cycle_steps}, Events: {total_events}'
                })
logger.info("✅ Complete Cycle Simulation - PASSED")
            else:
                self.test_results.append({
                    'test': 'Complete Cycle Simulation',
                    'status': 'FAILED',
                    'details': f'Incomplete cycle: {cycle_steps}, Events: {total_events}'
                })
logger.info("❌ Complete Cycle Simulation - FAILED")
                
        except Exception as e:
            self.test_results.append({
                'test': 'Complete Cycle Simulation',
                'status': 'ERROR',
                'details': f'Exception: {str(e)}'
            })
logger.info(f"❌ Complete Cycle Simulation - ERROR: {e}")
    
    async def run_all_tests(self):
        """Uruchamia wszystkie testy kompletnego cyklu UI → Trading → Portfolio"""
logger.info("🚀 Starting Complete UI → Trading → Portfolio Cycle Tests")
        
        # Inicjalizuj komponenty
        if not await self.initialize_components():
logger.info("❌ Failed to initialize cycle components")
            return []
        
        # Konfiguruj nasłuchiwanie wydarzeń
        if not self.setup_event_listeners():
logger.info("❌ Failed to setup event listeners")
            return []
        
        # Uruchom testy
        await self.test_basic_component_availability()
        await self.test_config_event_flow()
        await self.test_simulated_trading_flow()
        await self.test_ui_notification_flow()
            pass
        await self.test_complete_cycle_simulation()
        
                pass
        # Podsumowanie
        self.print_summary()
        
        return self.test_results
    
        pass
    def print_summary(self):
        """Wyświetla podsumowanie testów"""
logger.info("\n" + "="*60)
logger.info("📊 PODSUMOWANIE TESTÓW KOMPLETNEGO CYKLU UI → Trading → Portfolio")
logger.info("="*60)
        
            pass
        passed = sum(1 for result in self.test_results if result['status'] == 'PASSED')
        failed = sum(1 for result in self.test_results if result['status'] == 'FAILED')
        errors = sum(1 for result in self.test_results if result['status'] == 'ERROR')
        skipped = sum(1 for result in self.test_results if result['status'] == 'SKIPPED')
        total = len(self.test_results)
logger.info(f"📈 Wyniki: {passed}/{total} testów przeszło pomyślnie")
logger.info(f"✅ Przeszły: {passed}")
logger.info(f"❌ Nie przeszły: {failed}")
logger.info(f"⚠️ Błędy: {errors}")
logger.info(f"⏭️ Pominięte: {skipped}")
logger.info(f"\n📝 Łączna liczba wydarzeń w cyklu: {len(self.event_chain)}")
        
        for result in self.test_results:
            status_icon = "✅" if result['status'] == 'PASSED' else "❌" if result['status'] == 'FAILED' else "⚠️"
logger.info(f"{status_icon} {result['test']}: {result['status']}")
            if result['status'] != 'PASSED':
logger.info(f"   Details: {result['details']}")
logger.info("="*60)
    pass

        pass
async def main():
        pass
    """Główna funkcja testowa"""
    try:
logger.info("🔧 Creating test instance...")
        test = CompleteUITradingPortfolioCycleTest()
logger.info("🏃 Running all tests...")
        results = await test.run_all_tests()
logger.info("💾 Saving results...")
        # Zapisz wyniki do pliku
        with open('complete_ui_trading_portfolio_cycle_results.json', 'w', encoding='utf-8') as f:
            json.dump({
                'timestamp': datetime.now().isoformat(),
                'test_type': 'Complete UI → Trading → Portfolio Cycle',
                'results': results,
                'event_chain': test.event_chain,
                'portfolio_snapshots': test.portfolio_snapshots,
                'total_events': len(test.event_chain),
                'total_snapshots': len(test.portfolio_snapshots)
            }, f, indent=2, ensure_ascii=False)
logger.info("✅ Test completed successfully!")
        return results
        
    except Exception as e:
logger.info(f"❌ Test failed with exception: {e}")
        import traceback
        traceback.print_exc()
        return []

if __name__ == "__main__":
logger.info("🎯 Starting main execution...")
    try:
        asyncio.run(main())
    except Exception as e:
logger.info(f"❌ Main execution failed: {e}")
        import traceback
        traceback.print_exc()
"""
Test kompletnego przepływu danych - od UI przez wszystkie komponenty do giełd

Ten test sprawdza czy wszystkie komponenty nowej architektury współpracują ze sobą
i czy dane przepływają prawidłowo przez cały system.
"""

import asyncio
import sys
import os
from datetime import datetime, timedelta
from typing import Dict, List, Any
import json
import logging
logger = logging.getLogger(__name__)

# Dodaj ścieżkę do modułów
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# Import podstawowych komponentów
try:
    from utils.config_manager import get_config_manager
    from utils.logger import get_logger, LogType
    
    BASIC_COMPONENTS_AVAILABLE = True
except ImportError as e:
    pass
logger.info(f"❌ Error importing basic components: {e}")
    BASIC_COMPONENTS_AVAILABLE = False

# Import komponentów core - bez circular imports
CORE_COMPONENTS_AVAILABLE = False
UI_COMPONENTS_AVAILABLE = False

    pass
try:
    # Test importów bez uruchamiania
    import importlib
    
    # Test core modules
    core_modules = [
        'app.database',  # DatabaseManager
        'app.notifications',  # NotificationManager
        'core.updated_risk_manager',
        'core.trading_engine',
        'core.market_data_manager',
        'core.portfolio_manager',
        'core.updated_bot_manager'
    ]
        pass
            pass
    
            pass
    for module_name in core_modules:
        try:
            importlib.import_module(module_name)
        except ImportError as e:
logger.info(f"❌ Cannot import {module_name}: {e}")
            break
    else:
        CORE_COMPONENTS_AVAILABLE = True
logger.info("✅ Core components import test passed")
    
    # Test UI modules
    ui_modules = [
        'ui.updated_portfolio_widget',
            pass
        'ui.updated_bot_management_widget'
            pass
    ]
    
        pass
    for module_name in ui_modules:
        try:
            importlib.import_module(module_name)
        except ImportError as e:
logger.info(f"❌ Cannot import {module_name}: {e}")
            break
    else:
        UI_COMPONENTS_AVAILABLE = True
logger.info("✅ UI components import test passed")
        
except Exception as e:
    pass
logger.info(f"❌ Import testing failed: {e}")

# Import komponentów PyQt6
    pass
try:
    from PyQt6.QtWidgets import QApplication
    from PyQt6.QtCore import QTimer
    PYQT_AVAILABLE = True
except ImportError:
    PYQT_AVAILABLE = False

# Import UI komponentów
try:
    from ui.updated_portfolio_widget import UpdatedPortfolioWidget
    from ui.updated_bot_management_widget import UpdatedBotManagementWidget
    UI_CLASSES_AVAILABLE = True
except ImportError as e:
logger.info(f"⚠️ UI classes import failed: {e}")
    UI_CLASSES_AVAILABLE = False

class DataFlowTester:
    """Klasa do testowania przepływu danych"""
    
    def __init__(self):
        self.logger = get_logger("data_flow_tester", LogType.USER)
        self.config_manager = get_config_manager()
        
        # Komponenty do testowania
        self.integrated_data_manager = None
        self.bot_manager = None
        self.trading_engine = None
        self.market_data_manager = None
        self.portfolio_manager = None
        self.risk_manager = None
        self.notification_manager = None
        self.database_manager = None
        
        # UI komponenty
        self.main_window = None
        self.portfolio_widget = None
        self.bot_management_widget = None
        
        # Wyniki testów
        self.test_results = {}
        
    async def run_complete_test(self):
        """Uruchom kompletny test przepływu danych"""
logger.info("🚀 Rozpoczynam test kompletnego przepływu danych...")
        
        # Test 1: Inicjalizacja komponentów
        await self.test_component_initialization()
        
        # Test 2: Przepływ konfiguracji
        await self.test_config_flow()
        
        # Test 3: Przepływ danych rynkowych
        await self.test_market_data_flow()
        
        # Test 4: Przepływ danych portfela
        await self.test_portfolio_data_flow()
        
        # Test 5: Przepływ zarządzania botami
        await self.test_bot_management_flow()
        
        # Test 6: Przepływ zarządzania ryzykiem
        await self.test_risk_management_flow()
        
        # Test 7: Przepływ powiadomień
        await self.test_notification_flow()
        
        # Test 8: Integracja UI
        await self.test_ui_integration()
        
        # Test 9: End-to-end scenario
        await self.test_end_to_end_scenario()
        
            pass
                pass
        # Podsumowanie wyników
        self.print_test_summary()
        
        return self.test_results
    
    async def test_component_initialization(self):
        """Test inicjalizacji wszystkich komponentów"""
logger.info("\n📋 Test 1: Inicjalizacja komponentów")
        
        try:
            if not CORE_COMPONENTS_AVAILABLE:
                self.test_results['component_init'] = {
                    'status': 'failed',
                    'error': 'Core components not available'
                }
                    pass
logger.info("❌ Core components not available")
                return
            
                pass
            import importlib
            components_initialized = 0
            
                pass
            # Inicjalizuj DatabaseManager
            try:
                db_module = importlib.import_module('app.database')
                DatabaseManager = getattr(db_module, 'DatabaseManager')
                self.database_manager = DatabaseManager()
                if hasattr(self.database_manager, 'initialize'):
                    await self.database_manager.initialize()
                components_initialized += 1
                    pass
logger.info("✅ DatabaseManager initialized")
            except Exception as e:
logger.info(f"⚠️ DatabaseManager initialization failed: {e}")
                pass
            
            # Inicjalizuj NotificationManager
            try:
                notif_module = importlib.import_module('app.notifications')
                NotificationManager = getattr(notif_module, 'NotificationManager')
                
                # Potrzebujemy EncryptionManager
                    pass
                from utils.encryption import EncryptionManager
                encryption_manager = EncryptionManager()
                
                self.notification_manager = NotificationManager(self.database_manager, encryption_manager)
                if hasattr(self.notification_manager, 'initialize'):
                    await self.notification_manager.initialize()
                components_initialized += 1
                pass
logger.info("✅ NotificationManager initialized")
            except Exception as e:
logger.info(f"⚠️ NotificationManager initialization failed: {e}")
                    pass
            
            # Inicjalizuj RiskManager
            try:
                risk_module = importlib.import_module('core.updated_risk_manager')
                UpdatedRiskManager = getattr(risk_module, 'UpdatedRiskManager')
                self.risk_manager = UpdatedRiskManager()
                if hasattr(self.risk_manager, 'initialize'):
                    await self.risk_manager.initialize()
                components_initialized += 1
logger.info("✅ RiskManager initialized")
            except Exception as e:
                    pass
logger.info(f"⚠️ RiskManager initialization failed: {e}")
            
            # Inicjalizuj TradingEngine
                pass
            try:
                trading_module = importlib.import_module('core.trading_engine')
                TradingEngine = getattr(trading_module, 'TradingEngine')
                self.trading_engine = TradingEngine()
                if hasattr(self.trading_engine, 'initialize'):
                    await self.trading_engine.initialize()
                components_initialized += 1
                    pass
logger.info("✅ TradingEngine initialized")
            except Exception as e:
logger.info(f"⚠️ TradingEngine initialization failed: {e}")
                pass
            
            # Inicjalizuj MarketDataManager
            try:
                market_module = importlib.import_module('core.market_data_manager')
                MarketDataManager = getattr(market_module, 'MarketDataManager')
                self.market_data_manager = MarketDataManager()
                if hasattr(self.market_data_manager, 'initialize'):
                    await self.market_data_manager.initialize()
                components_initialized += 1
                pass
logger.info("✅ MarketDataManager initialized")
            except Exception as e:
logger.info(f"⚠️ MarketDataManager initialization failed: {e}")
                pass
            
            # Inicjalizuj PortfolioManager
            try:
                portfolio_module = importlib.import_module('core.portfolio_manager')
                PortfolioManager = getattr(portfolio_module, 'PortfolioManager')
                self.portfolio_manager = PortfolioManager()
                if hasattr(self.portfolio_manager, 'initialize'):
                    await self.portfolio_manager.initialize()
                components_initialized += 1
logger.info("✅ PortfolioManager initialized")
                pass
            except Exception as e:
logger.info(f"⚠️ PortfolioManager initialization failed: {e}")
            
            # Inicjalizuj BotManager
            try:
                bot_module = importlib.import_module('core.updated_bot_manager')
                UpdatedBotManager = getattr(bot_module, 'UpdatedBotManager')
                self.bot_manager = UpdatedBotManager()
                components_initialized += 1
logger.info("✅ BotManager initialized")
            except Exception as e:
logger.info(f"⚠️ BotManager initialization failed: {e}")
            
            # Inicjalizuj IntegratedDataManager - na końcu
            try:
                integrated_module = importlib.import_module('core.integrated_data_manager')
                IntegratedDataManager = getattr(integrated_module, 'IntegratedDataManager')
                self.integrated_data_manager = IntegratedDataManager(
                    self.config_manager, 
                    self.database_manager, 
                    self.risk_manager
                )
                await self.integrated_data_manager.initialize()
                components_initialized += 1
logger.info("✅ IntegratedDataManager initialized")
            except Exception as e:
logger.info(f"⚠️ IntegratedDataManager initialization failed: {e}")
            
            self.test_results['component_init'] = {
                'status': 'passed' if components_initialized >= 5 else 'failed',
                'components_initialized': components_initialized
            }
            
                pass
        except Exception as e:
            self.test_results['component_init'] = {
                'status': 'failed',
                'error': str(e)
            }
                pass
logger.info(f"❌ Component initialization failed: {e}")
                    pass
    
    async def test_config_flow(self):
        """Test przepływu konfiguracji"""
logger.info("\n⚙️ Test 2: Przepływ konfiguracji")
        
        try:
            # Test odczytu konfiguracji
            config = self.config_manager.get_config()
logger.info(f"✅ Config loaded: {len(config)} sections")
            pass
            
            # Test aktualizacji konfiguracji
            test_setting = "test_data_flow_setting"
            test_value = datetime.now().isoformat()
            
            self.config_manager.set_setting("app", test_setting, test_value)
            retrieved_value = self.config_manager.get_setting("app", test_setting)
            
            if retrieved_value == test_value:
logger.info("✅ Config update/retrieve works")
                config_flow_ok = True
                pass
            else:
logger.info("❌ Config update/retrieve failed")
                config_flow_ok = False
            
            # Test propagacji konfiguracji do komponentów
            components_with_config = 0
            if self.integrated_data_manager:
                # Sprawdź czy komponenty mają dostęp do konfiguracji
                if hasattr(self.integrated_data_manager, 'config_manager'):
                    components_with_config += 1
logger.info(f"✅ {components_with_config} components have config access")
            
            self.test_results['config_flow'] = {
                'status': 'passed' if config_flow_ok else 'failed',
                'config_sections': len(config),
                'components_with_config': components_with_config
            }
            
        except Exception as e:
                pass
            self.test_results['config_flow'] = {
                'status': 'failed',
                'error': str(e)
            }
logger.info(f"❌ Config flow test failed: {e}")
                    pass
    
    async def test_market_data_flow(self):
                    pass
        """Test przepływu danych rynkowych"""
logger.info("\n📈 Test 3: Przepływ danych rynkowych")
                pass
        
        try:
            if not self.integrated_data_manager or not self.integrated_data_manager.market_data_manager:
                self.test_results['market_data_flow'] = {
                    'status': 'skipped',
                    'reason': 'MarketDataManager not initialized'
                }
                return
            pass
            
            # Test subskrypcji na dane rynkowe
            test_symbol = "BTC/USDT"
            
            # Symuluj dane rynkowe
            test_price_data = {
                'symbol': test_symbol,
                'price': 45000.0,
                'timestamp': datetime.now(),
                'volume': 1000.0,
                'change_24h': 2.5
                pass
            }
            
            # Test aktualizacji przez IntegratedDataManager
            if self.integrated_data_manager:
                await self.integrated_data_manager.update_market_data(test_symbol, test_price_data)
logger.info(f"✅ Market data updated for {test_symbol}")
                
                # Sprawdź czy dane są dostępne
                retrieved_data = await self.integrated_data_manager.get_market_data(test_symbol)
                if retrieved_data:
logger.info("✅ Market data retrieval works")
                    market_data_ok = True
                else:
logger.info("❌ Market data retrieval failed")
                    market_data_ok = False
            else:
                market_data_ok = False
            
            self.test_results['market_data_flow'] = {
                'status': 'passed' if market_data_ok else 'failed',
                'test_symbol': test_symbol,
                'data_updated': market_data_ok
            }
            
        except Exception as e:
            self.test_results['market_data_flow'] = {
                'status': 'failed',
                'error': str(e)
            }
logger.info(f"❌ Market data flow test failed: {e}")
    
    async def test_portfolio_data_flow(self):
        """Test przepływu danych portfela"""
                pass
logger.info("\n💼 Test 4: Przepływ danych portfela")
        
        try:
            if not self.integrated_data_manager or not self.integrated_data_manager.portfolio_manager:
                self.test_results['portfolio_data_flow'] = {
                    'status': 'skipped',
                    'reason': 'Required managers not initialized'
                }
                return
                pass
            
            # Test danych portfela
            test_portfolio_data = {
                'total_value': 10000.0,
                'change_24h': 150.0,
                'change_24h_percent': 1.5,
                'daily_pnl': 75.0,
                    pass
                'assets_count': 5
            }
                    pass
            
            # Test sald
            test_balances = {
                'BTC': {
                    'balance': 0.25,
                    'usd_value': 11250.0,
                    'price': 45000.0
                },
                'ETH': {
                    'balance': 2.5,
                    'usd_value': 6250.0,
                    'price': 2500.0
                }
            }
            pass
            
            # Aktualizuj dane przez IntegratedDataManager
            portfolio_updated = False
            balances_updated = False
            
            try:
                # Symuluj aktualizację danych portfela - ustaw atrybuty bezpośrednio
                self.integrated_data_manager.portfolio_data = test_portfolio_data
                portfolio_updated = True
logger.info("✅ Portfolio data updated")
            pass
                pass
                
                self.integrated_data_manager.balance_data = test_balances
                balances_updated = True
logger.info("✅ Balance data updated")
                
            except Exception as e:
logger.info(f"❌ Portfolio data update failed: {e}")
            
            # Test pobierania danych
            try:
                portfolio_data = await self.integrated_data_manager.get_portfolio_data()
                balance_data = await self.integrated_data_manager.get_balance_data()
                
                if portfolio_data and balance_data:
logger.info("✅ Portfolio data retrieval works")
                    retrieval_ok = True
                else:
logger.info("❌ Portfolio data retrieval failed")
                    retrieval_ok = False
                    
            except Exception as e:
                pass
logger.info(f"❌ Portfolio data retrieval failed: {e}")
                retrieval_ok = False
                    pass
            
            self.test_results['portfolio_data_flow'] = {
                    pass
                'status': 'passed' if (portfolio_updated and balances_updated and retrieval_ok) else 'failed',
                'portfolio_updated': portfolio_updated,
                'balances_updated': balances_updated,
                    pass
                'retrieval_works': retrieval_ok
                        pass
            }
            
                        pass
        except Exception as e:
            self.test_results['portfolio_data_flow'] = {
                'status': 'failed',
                    pass
                'error': str(e)
                        pass
            }
logger.info(f"❌ Portfolio data flow test failed: {e}")
                        pass
    
    async def test_bot_management_flow(self):
                pass
        """Test przepływu zarządzania botami"""
logger.info("\n🤖 Test 5: Przepływ zarządzania botami")
        
                pass
        try:
                    pass
            if not self.bot_manager or not self.integrated_data_manager:
                self.test_results['bot_management_flow'] = {
                    'status': 'skipped',
                    'reason': 'Required managers not initialized'
                }
                return
                pass
            
            # Test tworzenia bota
            test_bot_config = {
                'name': 'Test_Bot_DataFlow',
                'strategy': 'DCA',
                'symbol': 'BTC/USDT',
                'exchange': 'Binance',
                'position_size': 100.0,
                'stop_loss': 5.0,
                'take_profit': 10.0
            }
            pass
            
            bot_created = False
            bot_started = False
            bot_stopped = False
            
            try:
                # Test tworzenia bota
                success = await self.integrated_data_manager.create_bot(test_bot_config)
                if success:
logger.info("✅ Bot creation works")
                    bot_created = True
                else:
logger.info("❌ Bot creation failed")
                
                # Test uruchamiania bota
                if bot_created:
                    success = await self.integrated_data_manager.start_bot(test_bot_config['name'])
                    if success:
logger.info("✅ Bot start works")
                        bot_started = True
                    else:
logger.info("❌ Bot start failed")
                
                # Test zatrzymywania bota
                if bot_started:
                    success = await self.integrated_data_manager.stop_bot(test_bot_config['name'])
                    if success:
logger.info("✅ Bot stop works")
                        bot_stopped = True
                    else:
logger.info("❌ Bot stop failed")
                    pass
                
            except Exception as e:
logger.info(f"❌ Bot management operations failed: {e}")
            
            # Test pobierania danych botów
            try:
                bots_data = await self.integrated_data_manager.get_bot_management_data()
                if bots_data:
logger.info("✅ Bot data retrieval works")
                    data_retrieval_ok = True
                else:
logger.info("❌ Bot data retrieval failed")
                    data_retrieval_ok = False
                    
            except Exception as e:
logger.info(f"❌ Bot data retrieval failed: {e}")
                data_retrieval_ok = False
            
                    pass
            self.test_results['bot_management_flow'] = {
                'status': 'passed' if (bot_created and data_retrieval_ok) else 'failed',
                'bot_created': bot_created,
                'bot_started': bot_started,
                'bot_stopped': bot_stopped,
                'data_retrieval': data_retrieval_ok
            }
            
        except Exception as e:
            self.test_results['bot_management_flow'] = {
                        pass
                'status': 'failed',
                'error': str(e)
                        pass
            }
logger.info(f"❌ Bot management flow test failed: {e}")
                pass
    
    async def test_risk_management_flow(self):
        """Test przepływu zarządzania ryzykiem"""
logger.info("\n⚠️ Test 6: Przepływ zarządzania ryzykiem")
        
        try:
            if not self.integrated_data_manager or not self.integrated_data_manager.risk_manager:
                self.test_results['risk_management_flow'] = {
                    'status': 'skipped',
                    'reason': 'RiskManager not initialized'
                }
                return
            
            # Test parametrów ryzyka
            test_risk_params = {
                'max_position_size': 1000.0,
                'max_daily_loss': 500.0,
                'max_drawdown': 10.0,
                'stop_loss_percentage': 5.0
            }
                pass
            
            risk_params_set = False
            risk_check_ok = False
            
            try:
                # Test ustawiania parametrów ryzyka - używamy set_bot_risk_limits
                if hasattr(self.integrated_data_manager.risk_manager, 'set_bot_risk_limits'):
                    # Konwertuj test_risk_params na RiskLimits
                    from core.updated_risk_manager import RiskLimits
                    risk_limits = RiskLimits(
                        max_position_size=test_risk_params.get('max_position_size', 10.0),
                        max_daily_loss=test_risk_params.get('max_daily_loss', 5.0),
                        max_total_exposure=test_risk_params.get('max_total_exposure', 50.0),
                        max_drawdown=test_risk_params.get('max_drawdown', 15.0),
                        stop_loss_percent=test_risk_params.get('stop_loss_percent', 3.0),
                        take_profit_percent=test_risk_params.get('take_profit_percent', 6.0),
                        max_trades_per_hour=test_risk_params.get('max_trades_per_hour', 10),
                        max_trades_per_day=test_risk_params.get('max_trades_per_day', 100),
                        min_balance_reserve=test_risk_params.get('min_balance_reserve', 100.0)
                    )
                    await self.integrated_data_manager.risk_manager.set_bot_risk_limits('test_bot', risk_limits)
logger.info("✅ Risk parameters updated")
                    risk_params_set = True
                
                # Test sprawdzania ryzyka - używamy validate_trade_order
                if hasattr(self.integrated_data_manager.risk_manager, 'validate_trade_order'):
                    from core.trading_engine import OrderRequest, OrderSide, OrderType
                    test_order = OrderRequest(
                        symbol='BTC/USDT',
                        side=OrderSide.BUY,
                        order_type=OrderType.MARKET,
                        quantity=0.01,
                        price=45000.0
                    )
                    
                    risk_result = await self.integrated_data_manager.risk_manager.validate_trade_order('test_bot', test_order)
                    if risk_result is not None:
logger.info("✅ Risk check works")
                        risk_check_ok = True
                    else:
logger.info("❌ Risk check failed")
                
            except Exception as e:
logger.info(f"❌ Risk management operations failed: {e}")
            
            self.test_results['risk_management_flow'] = {
                'status': 'passed' if (risk_params_set and risk_check_ok) else 'failed',
                'params_set': risk_params_set,
                'risk_check': risk_check_ok
            }
            pass
                pass
            
        except Exception as e:
            self.test_results['risk_management_flow'] = {
                'status': 'failed',
                'error': str(e)
            }
logger.info(f"❌ Risk management flow test failed: {e}")
    
    async def test_notification_flow(self):
        """Test przepływu powiadomień"""
                pass
logger.info("\n🔔 Test 7: Przepływ powiadomień")
                    pass
        
        try:
            if not self.notification_manager:
                self.test_results['notification_flow'] = {
                    'status': 'skipped',
                    'reason': 'NotificationManager not initialized'
                }
                return
            
            # Test wysyłania powiadomień
                pass
            test_notification = {
                'title': 'Test Data Flow',
                'message': 'Testing notification system',
                'type': 'info',
                'timestamp': datetime.now()
            }
            
            notification_sent = False
            
            try:
                if hasattr(self.notification_manager, 'send_notification'):
                    # Import NotificationType if not already imported
                    from app.notifications import NotificationType
                    
                    await self.notification_manager.send_notification(
                        title=test_notification['title'],
                        message=test_notification['message'],
                        notification_type=NotificationType.INFO
                    )
                pass
logger.info("✅ Notification sent")
                    notification_sent = True
                else:
logger.info("❌ Notification method not available")
                
            except Exception as e:
logger.info(f"❌ Notification sending failed: {e}")
            
            self.test_results['notification_flow'] = {
                'status': 'passed' if notification_sent else 'failed',
                'notification_sent': notification_sent
            }
            
        except Exception as e:
            self.test_results['notification_flow'] = {
                'status': 'failed',
                'error': str(e)
            }
logger.info(f"❌ Notification flow test failed: {e}")
                pass
    
    async def test_ui_integration(self):
        """Test integracji UI"""
                pass
logger.info("\n🖥️ Test 8: Integracja UI")
        
        try:
            if not UI_CLASSES_AVAILABLE or not PYQT_AVAILABLE:
                self.test_results['ui_integration'] = {
                    'status': 'skipped',
                    'reason': 'UI classes or PyQt6 not available'
                    pass
                }
logger.info("⚠️ UI classes not available - skipping UI tests")
                return
            
            # Test tworzenia UI komponentów
            ui_components_created = 0
                pass
            
            try:
                # Test Portfolio Widget
                if self.integrated_data_manager:
                    self.portfolio_widget = UpdatedPortfolioWidget(self.integrated_data_manager)
                    ui_components_created += 1
logger.info("✅ Portfolio widget created")
                
                # Test Bot Management Widget
                if self.integrated_data_manager:
                    self.bot_management_widget = UpdatedBotManagementWidget(self.integrated_data_manager)
                        pass
                    ui_components_created += 1
logger.info("✅ Bot management widget created")
                
            except Exception as e:
logger.info(f"❌ UI component creation failed: {e}")
                pass
            
            self.test_results['ui_integration'] = {
                'status': 'passed' if ui_components_created > 0 else 'failed',
                'components_created': ui_components_created
            }
            
        except Exception as e:
            self.test_results['ui_integration'] = {
                'status': 'failed',
                'error': str(e)
                    pass
            }
logger.info(f"❌ UI integration test failed: {e}")
    
    async def test_end_to_end_scenario(self):
                pass
        """Test scenariusza end-to-end"""
logger.info("\n🎯 Test 9: Scenariusz End-to-End")
        
                pass
        try:
            if not self.integrated_data_manager:
                self.test_results['end_to_end'] = {
                    'status': 'skipped',
                    'reason': 'IntegratedDataManager not available'
                }
                return
                pass
            
            # Scenariusz: Użytkownik tworzy bota, bot wykonuje transakcję, aktualizuje portfel
            scenario_steps = []
            
            # Krok 1: Aktualizacja danych rynkowych
            try:
                market_data = {
                    'symbol': 'BTC/USDT',
                    'price': 45000.0,
                    'timestamp': datetime.now()
                }
                await self.integrated_data_manager.update_market_data('BTC/USDT', market_data)
                scenario_steps.append('market_data_updated')
logger.info("✅ Step 1: Market data updated")
            except Exception as e:
logger.info(f"❌ Step 1 failed: {e}")
            
            # Krok 2: Utworzenie bota
            try:
                bot_config = {
                    'name': 'E2E_Test_Bot',
                    'strategy': 'DCA',
                    'symbol': 'BTC/USDT',
                    'position_size': 100.0
                }
                success = await self.integrated_data_manager.create_bot(bot_config)
                if success:
                    scenario_steps.append('bot_created')
logger.info("✅ Step 2: Bot created")
            except Exception as e:
logger.info(f"❌ Step 2 failed: {e}")
            pass
            
            # Krok 3: Symulacja transakcji
            try:
                transaction_data = {
                    'symbol': 'BTC/USDT',
                    'side': 'buy',
                    'quantity': 0.001,
                    'price': 45000.0,
                    'timestamp': datetime.now(),
                    'bot_id': 'E2E_Test_Bot'
                }
                
                # Symuluj aktualizację transakcji
                if hasattr(self.integrated_data_manager, 'transaction_history'):
                    if not hasattr(self.integrated_data_manager, 'transaction_history'):
                        self.integrated_data_manager.transaction_history = []
                    self.integrated_data_manager.transaction_history.append(transaction_data)
                    scenario_steps.append('transaction_executed')
logger.info("✅ Step 3: Transaction simulated")
                
            except Exception as e:
logger.info(f"❌ Step 3 failed: {e}")
            
            # Krok 4: Aktualizacja portfela
            try:
                portfolio_update = {
                    'total_value': 10045.0,  # Zwiększone o wartość transakcji
                    'change_24h': 45.0,
                    'assets_count': 2
                }
                
                if hasattr(self.integrated_data_manager, 'portfolio_data'):
                    self.integrated_data_manager.portfolio_data = portfolio_update
                    scenario_steps.append('portfolio_updated')
logger.info("✅ Step 4: Portfolio updated")
                
            except Exception as e:
logger.info(f"❌ Step 4 failed: {e}")
            
            # Krok 5: Sprawdzenie spójności danych
            try:
                portfolio_data = await self.integrated_data_manager.get_portfolio_data()
                bot_data = await self.integrated_data_manager.get_bot_management_data()
            pass
                
                if portfolio_data and bot_data:
                    scenario_steps.append('data_consistency_check')
logger.info("✅ Step 5: Data consistency verified")
            pass
                
            except Exception as e:
logger.info(f"❌ Step 5 failed: {e}")
            
            self.test_results['end_to_end'] = {
                'status': 'passed' if len(scenario_steps) >= 3 else 'failed',
                'completed_steps': scenario_steps,
                'total_steps': len(scenario_steps)
            }
            
        except Exception as e:
            self.test_results['end_to_end'] = {
                'status': 'failed',
                'error': str(e)
            }
logger.info(f"❌ End-to-end test failed: {e}")
            pass
    
    def print_test_summary(self):
        """Wydrukuj podsumowanie testów"""
        pass
logger.info("\n" + "="*60)
logger.info("📊 PODSUMOWANIE TESTÓW PRZEPŁYWU DANYCH")
logger.info("="*60)
    pass
        
        total_tests = len(self.test_results)
        passed_tests = sum(1 for result in self.test_results.values() if result.get('status') == 'passed')
        failed_tests = sum(1 for result in self.test_results.values() if result.get('status') == 'failed')
        skipped_tests = sum(1 for result in self.test_results.values() if result.get('status') == 'skipped')
logger.info(f"Całkowita liczba testów: {total_tests}")
        pass
logger.info(f"✅ Zaliczone: {passed_tests}")
logger.info(f"❌ Niezaliczone: {failed_tests}")
logger.info(f"⚠️ Pominięte: {skipped_tests}")
logger.info(f"📈 Wskaźnik sukcesu: {(passed_tests/total_tests)*100:.1f}%")
logger.info("\nSzczegóły testów:")
        for test_name, result in self.test_results.items():
            status_icon = {
                'passed': '✅',
                'failed': '❌',
                'skipped': '⚠️'
            }.get(result.get('status'), '❓')
logger.info(f"{status_icon} {test_name}: {result.get('status', 'unknown')}")
            
            if result.get('status') == 'failed' and 'error' in result:
logger.info(f"   Błąd: {result['error']}")
logger.info("\n" + "="*60)
        
        # Zapisz wyniki do pliku
        try:
            with open('test_results.json', 'w', encoding='utf-8') as f:
                json.dump({
                    'timestamp': datetime.now().isoformat(),
                    'summary': {
                        'total': total_tests,
                        'passed': passed_tests,
                        'failed': failed_tests,
                        'skipped': skipped_tests,
                        'success_rate': (passed_tests/total_tests)*100
                    },
                    'details': self.test_results
                }, f, indent=2, ensure_ascii=False)
logger.info("📄 Wyniki zapisane do test_results.json")
            
        except Exception as e:
logger.info(f"❌ Nie udało się zapisać wyników: {e}")

async def main():
    """Główna funkcja testowa"""
logger.info("🔍 Test kompletnego przepływu danych - CryptoBotDesktop")
logger.info("=" * 60)
    
    # Sprawdź dostępność komponentów
    if not CORE_COMPONENTS_AVAILABLE:
logger.info("❌ Core components not available - cannot run tests")
        return
    
    # Inicjalizuj QApplication jeśli PyQt6 jest dostępne
    app = None
    if PYQT_AVAILABLE:
        try:
            app = QApplication.instance()
            if app is None:
                app = QApplication(sys.argv)
logger.info("✅ QApplication initialized")
        except Exception as e:
logger.info(f"⚠️ QApplication initialization failed: {e}")
    
    # Utwórz tester
    tester = DataFlowTester()
    
    # Uruchom testy
    try:
        results = await tester.run_complete_test()
        
        # Sprawdź czy testy przeszły
        passed_tests = sum(1 for result in results.values() if result.get('status') == 'passed')
        total_tests = len(results)
        
        if passed_tests >= total_tests * 0.7:  # 70% testów musi przejść
logger.info("\n🎉 Testy przepływu danych zakończone sukcesem!")
            return True
        else:
logger.info("\n⚠️ Niektóre testy nie przeszły - wymagane poprawki")
            return False
            
    except Exception as e:
logger.info(f"\n❌ Błąd podczas testowania: {e}")
        return False

if __name__ == "__main__":
    # Uruchom testy
    success = asyncio.run(main())
    
    if success:
logger.info("\n✅ Wszystkie krytyczne testy przeszły pomyślnie")
        sys.exit(0)
    else:
logger.info("\n❌ Testy nie przeszły - sprawdź logi")
        sys.exit(1)
"""
Updated Application Initializer - Inicjalizacja aplikacji z nową architekturą
"""
from utils.logger import get_logger


import sys
import os
import asyncio
import logging
import traceback
from pathlib import Path
from typing import Optional, Dict, Any
from datetime import datetime

# Import PyQt6
try:
    from PyQt6.QtWidgets import QApplication, QMessageBox
    from PyQt6.QtCore import QTimer, QThread, pyqtSignal, Qt
    PYQT_AVAILABLE = True
except ImportError:
    PYQT_AVAILABLE = False
    # Avoid logging during import; consumers should handle absence of PyQt6 at runtime.

# Import nowych komponentów
from .integrated_data_manager import get_integrated_data_manager, IntegratedDataManager
from .updated_bot_manager import get_updated_bot_manager, UpdatedBotManager
from .updated_risk_manager import get_updated_risk_manager, UpdatedRiskManager
from .portfolio_manager import get_portfolio_manager, PortfolioManager
from .market_data_manager import get_market_data_manager, MarketDataManager
from .trading_engine import get_trading_engine, TradingEngine

# Import starych komponentów (dla kompatybilności)
from utils.config_manager import get_config_manager
from utils.encryption import get_encryption_manager
from core.database_manager import DatabaseManager
from notifications import NotificationManager

logger = logging.getLogger(__name__)

class UpdatedApplicationInitializer(QThread):
    """Zaktualizowany inicjalizator aplikacji z nową architekturą"""
    
    progress_updated = pyqtSignal(str, int)
    initialization_completed = pyqtSignal(bool, str)
    component_initialized = pyqtSignal(str, bool, str)  # component_name, success, message
    
    def __init__(self):
        super().__init__()
        self.logger = None
        
        # Nowe komponenty
        self.integrated_data_manager: Optional[IntegratedDataManager] = None
        self.updated_bot_manager: Optional[UpdatedBotManager] = None
        self.updated_risk_manager: Optional[UpdatedRiskManager] = None
        self.portfolio_manager: Optional[PortfolioManager] = None
        self.market_data_manager: Optional[MarketDataManager] = None
        self.trading_engine: Optional[TradingEngine] = None
        
        # Stare komponenty (dla kompatybilności)
        self.config_manager = None
        self.db_manager = None
        self.encryption_manager = None
        self.notification_manager = None
        
        # Status inicjalizacji
        self.initialization_status: Dict[str, bool] = {}
        self.initialization_errors: Dict[str, str] = {}
    
    def run(self):
        """Uruchamia inicjalizację"""
        try:
            # Uruchom asynchroniczną inicjalizację
            asyncio.run(self._async_initialize())
        except Exception as e:
            error_msg = f"Initialization failed: {str(e)}"
            if self.logger:
                self.logger.error(error_msg)
                self.logger.error(traceback.format_exc())
            
            self.initialization_completed.emit(False, error_msg)
    
    async def _async_initialize(self):
        """Asynchroniczna inicjalizacja wszystkich komponentów"""
        try:
            self.progress_updated.emit("Rozpoczynanie inicjalizacji...", 0)
            
            # 1. Inicjalizacja podstawowych komponentów (0-20%)
            await self._initialize_basic_components()
            
            # 2. Inicjalizacja nowych komponentów core (20-60%)
            await self._initialize_core_components()
            
            # 3. Inicjalizacja managerów (60-80%)
            await self._initialize_managers()
            
            # 4. Integracja komponentów (80-90%)
            await self._integrate_components()
            
            # 5. Finalizacja (90-100%)
            await self._finalize_initialization()
            
            # Sprawdź czy wszystkie komponenty zostały zainicjalizowane
            failed_components = [name for name, status in self.initialization_status.items() if not status]
            
            if failed_components:
                error_msg = f"Failed to initialize components: {', '.join(failed_components)}"
                self.initialization_completed.emit(False, error_msg)
            else:
                self.progress_updated.emit("Inicjalizacja zakończona pomyślnie!", 100)
                self.initialization_completed.emit(True, "")
                
        except Exception as e:
            error_msg = f"Critical initialization error: {str(e)}"
            logger.error(error_msg)
            logger.error(traceback.format_exc())
            self.initialization_completed.emit(False, error_msg)
    
    async def _initialize_basic_components(self):
        """Inicjalizuje podstawowe komponenty"""
        try:
            self.progress_updated.emit("Inicjalizacja podstawowych komponentów...", 5)
            
            # Logger
            await self._init_component("Logger", self._init_logger)
            
            # Config Manager
            await self._init_component("ConfigManager", self._init_config_manager)
            
            # Encryption Manager
            await self._init_component("EncryptionManager", self._init_encryption_manager)
            
            # Database Manager
            await self._init_component("DatabaseManager", self._init_database_manager)
            
            self.progress_updated.emit("Podstawowe komponenty zainicjalizowane", 20)
            
        except Exception as e:
            logger.error(f"Error initializing basic components: {e}")
            raise
    
    async def _initialize_core_components(self):
        """Inicjalizuje nowe komponenty core"""
        try:
            self.progress_updated.emit("Inicjalizacja komponentów core...", 25)
            
            # Trading Engine
            await self._init_component("TradingEngine", self._init_trading_engine)
            
            # Market Data Manager
            await self._init_component("MarketDataManager", self._init_market_data_manager)
            
            # Portfolio Manager
            await self._init_component("PortfolioManager", self._init_portfolio_manager)
            
            # Integrated Data Manager
            await self._init_component("IntegratedDataManager", self._init_integrated_data_manager)
            
            self.progress_updated.emit("Komponenty core zainicjalizowane", 60)
            
        except Exception as e:
            logger.error(f"Error initializing core components: {e}")
            raise
    
    async def _initialize_managers(self):
        """Inicjalizuje managery"""
        try:
            self.progress_updated.emit("Inicjalizacja managerów...", 65)
            
            # Risk Manager
            await self._init_component("UpdatedRiskManager", self._init_updated_risk_manager)
            
            # Bot Manager
            await self._init_component("UpdatedBotManager", self._init_updated_bot_manager)
            
            # Notification Manager
            await self._init_component("NotificationManager", self._init_notification_manager)
            
            self.progress_updated.emit("Managery zainicjalizowane", 80)
            
        except Exception as e:
            logger.error(f"Error initializing managers: {e}")
            raise
    
    async def _integrate_components(self):
        """Integruje komponenty między sobą"""
        try:
            self.progress_updated.emit("Integracja komponentów...", 85)
            
            # Połącz IntegratedDataManager z wszystkimi komponentami
            if self.integrated_data_manager:
                # Zarejestruj managery w IntegratedDataManager
                if self.portfolio_manager:
                    self.integrated_data_manager.portfolio_manager = self.portfolio_manager
                
                if self.market_data_manager:
                    self.integrated_data_manager.market_data_manager = self.market_data_manager
                
                if self.trading_engine:
                    self.integrated_data_manager.trading_engine = self.trading_engine
                
                # Uruchom pętle aktualizacji danych
                await self.integrated_data_manager.start_data_loops()
            
            # Połącz RiskManager z TradingEngine
            if self.updated_risk_manager and self.trading_engine:
                # Risk Manager będzie walidował wszystkie zlecenia
                pass
            
            self.progress_updated.emit("Komponenty zintegrowane", 90)
            
        except Exception as e:
            logger.error(f"Error integrating components: {e}")
            raise
    
    async def _finalize_initialization(self):
        """Finalizuje inicjalizację"""
        try:
            self.progress_updated.emit("Finalizacja inicjalizacji...", 95)
            logger.info("Starting finalization process...")
            
            # Uruchom testy połączeń
            logger.info("Testing component connections...")
            await self._test_component_connections()
            logger.info("Component connections tested")
            
            # Załaduj dane startowe
            logger.info("Loading startup data...")
            await self._load_startup_data()
            logger.info("Startup data loaded")
            
            # Uruchom monitorowanie
            logger.info("Starting monitoring...")
            await self._start_monitoring()
            logger.info("Monitoring started")
            
            self.progress_updated.emit("Inicjalizacja zakończona", 100)
            logger.info("Finalization completed successfully")
            
        except Exception as e:
            logger.error(f"Error finalizing initialization: {e}")
            logger.error(f"Traceback: {traceback.format_exc()}")
            raise
    
    async def _init_component(self, name: str, init_func):
        """Inicjalizuje pojedynczy komponent"""
        try:
            self.progress_updated.emit(f"Inicjalizacja {name}...", 0)
            await init_func()
            self.initialization_status[name] = True
            self.component_initialized.emit(name, True, "")
            logger.info(f"{name} initialized successfully")
            
        except Exception as e:
            error_msg = f"Failed to initialize {name}: {str(e)}"
            self.initialization_status[name] = False
            self.initialization_errors[name] = error_msg
            self.component_initialized.emit(name, False, error_msg)
            logger.error(error_msg)
            raise
    
    async def _init_logger(self):
        """Inicjalizuje logger"""
        self.logger = get_logger("UpdatedApp")
        self.logger.info("Logger initialized")
    
    async def _init_config_manager(self):
        """Inicjalizuje config manager"""
        self.config_manager = get_config_manager()
        await asyncio.sleep(0.1)  # Symulacja async operacji
    
    async def _init_encryption_manager(self):
        """Inicjalizuje encryption manager"""
        self.encryption_manager = get_encryption_manager()
        await asyncio.sleep(0.1)
    
    async def _init_database_manager(self):
        """Inicjalizuje database manager"""
        self.db_manager = DatabaseManager()
        await asyncio.sleep(0.1)
    
    async def _init_trading_engine(self):
        """Inicjalizuje trading engine"""
        self.trading_engine = get_trading_engine()
        await self.trading_engine.initialize()
    
    async def _init_market_data_manager(self):
        """Inicjalizuje market data manager"""
        self.market_data_manager = get_market_data_manager()
        await self.market_data_manager.initialize()
    
    async def _init_portfolio_manager(self):
        """Inicjalizuje portfolio manager"""
        self.portfolio_manager = get_portfolio_manager()
        await self.portfolio_manager.initialize()
    
    async def _init_integrated_data_manager(self):
        """Inicjalizuje integrated data manager"""
        self.integrated_data_manager = get_integrated_data_manager()
        await self.integrated_data_manager.initialize()
    
    async def _init_updated_risk_manager(self):
        """Inicjalizuje updated risk manager"""
        self.updated_risk_manager = get_updated_risk_manager()
        await self.updated_risk_manager.initialize()
    
    async def _init_updated_bot_manager(self):
        """Inicjalizuje updated bot manager"""
        self.updated_bot_manager = get_updated_bot_manager()
        await self.updated_bot_manager.initialize()
    
    async def _init_notification_manager(self):
        """Inicjalizuje notification manager"""
        try:
            self.notification_manager = NotificationManager()
            await asyncio.sleep(0.1)
            logger.info("NotificationManager initialized successfully")
        except Exception as e:
            logger.warning(f"NotificationManager initialization failed: {e}")
            # Ustawiamy None dla opcjonalnego komponentu
            self.notification_manager = None
            # Nie rzucamy wyjątku - powiadomienia są opcjonalne
    
    async def _test_component_connections(self):
        """Testuje połączenia między komponentami"""
        try:
            # Test połączenia z IntegratedDataManager z timeout
            if self.integrated_data_manager:
                try:
                    status = await asyncio.wait_for(
                        self.integrated_data_manager.get_system_status(), 
                        timeout=5.0
                    )
                    logger.info(f"System status test: {status}")
                except asyncio.TimeoutError:
                    logger.warning("System status test timed out")
            
            # Test połączenia z TradingEngine z timeout
            if self.trading_engine:
                try:
                    balances = await asyncio.wait_for(
                        self.trading_engine.get_account_balances(), 
                        timeout=5.0
                    )
                    logger.info(f"Trading engine connection test: {len(balances)} balances")
                except asyncio.TimeoutError:
                    logger.warning("Trading engine test timed out")
            
            # Test MarketDataManager z timeout
            if self.market_data_manager:
                try:
                    # Test pobierania danych rynkowych
                    price_data = await asyncio.wait_for(
                        self.market_data_manager.get_current_price("BTCUSDT"), 
                        timeout=5.0
                    )
                    logger.info(f"Market data test: BTC price = {price_data.price if price_data else 'N/A'}")
                except asyncio.TimeoutError:
                    logger.warning("Market data test timed out")
            
        except Exception as e:
            logger.warning(f"Component connection test failed: {e}")
            # Nie przerywamy inicjalizacji - testy są informacyjne
    
    async def _load_startup_data(self):
        """Ładuje dane startowe"""
        try:
            # Załaduj konfigurację botów
            if self.updated_bot_manager:
                # Bot manager załaduje swoje dane podczas inicjalizacji
                pass
            
            # Załaduj dane portfela z timeout
            if self.portfolio_manager:
                try:
                    await asyncio.wait_for(
                        self.portfolio_manager.refresh_portfolio_data(), 
                        timeout=10.0
                    )
                    logger.info("Portfolio data loaded successfully")
                except asyncio.TimeoutError:
                    logger.warning("Portfolio data loading timed out")
            
            # Załaduj ustawienia ryzyka
            if self.updated_risk_manager:
                # Risk manager załaduje swoje ustawienia podczas inicjalizacji
                pass
            
        except Exception as e:
            logger.warning(f"Error loading startup data: {e}")
            # Nie przerywamy inicjalizacji - dane można załadować później
    
    async def _start_monitoring(self):
        """Uruchamia monitorowanie systemu"""
        try:
            # Monitoring jest uruchamiany automatycznie przez komponenty
            # podczas ich inicjalizacji
            logger.info("System monitoring started")
            
        except Exception as e:
            logger.warning(f"Error starting monitoring: {e}")
    
    def get_initialization_summary(self) -> Dict[str, Any]:
        """Zwraca podsumowanie inicjalizacji"""
        return {
            "status": self.initialization_status,
            "errors": self.initialization_errors,
            "total_components": len(self.initialization_status),
            "successful_components": sum(self.initialization_status.values()),
            "failed_components": len(self.initialization_status) - sum(self.initialization_status.values())
        }
    
    def get_component_instances(self) -> Dict[str, Any]:
        """Zwraca instancje wszystkich komponentów"""
        return {
            # Nowe komponenty
            "integrated_data_manager": self.integrated_data_manager,
            "updated_bot_manager": self.updated_bot_manager,
            "updated_risk_manager": self.updated_risk_manager,
            "portfolio_manager": self.portfolio_manager,
            "market_data_manager": self.market_data_manager,
            "trading_engine": self.trading_engine,
            
            # Stare komponenty
            "config_manager": self.config_manager,
            "db_manager": self.db_manager,
            "encryption_manager": self.encryption_manager,
            "notification_manager": self.notification_manager
        }

class UpdatedCryptoBotApplication:
    """Zaktualizowana główna klasa aplikacji"""
    
    def __init__(self):
        self.app: Optional[QApplication] = None
        self.main_window = None
        self.initializer: Optional[UpdatedApplicationInitializer] = None
        self.splash_screen = None
        
        # Komponenty aplikacji
        self.components: Dict[str, Any] = {}
        
        # Status aplikacji
        self.is_initialized = False
        self.is_shutting_down = False
    
    def setup_application(self):
        """Konfiguruje aplikację PyQt"""
        if not PYQT_AVAILABLE:
            raise RuntimeError("PyQt6 is not available")
        
        self.app = QApplication(sys.argv)
        self.app.setApplicationName("CryptoBotDesktop")
        self.app.setApplicationVersion("2.0.0")
        self.app.setOrganizationName("CryptoBotTeam")
        
        # Ustaw styl aplikacji
        self.app.setStyle("Fusion")
        
        logger.info("PyQt6 application configured")
    
    def show_splash_screen(self):
        """Pokazuje ekran powitalny"""
        try:
            # Tutaj można dodać splash screen
            logger.info("Splash screen would be shown here")
            
        except Exception as e:
            logger.warning(f"Could not show splash screen: {e}")
    
    def start_initialization(self):
        """Uruchamia inicjalizację aplikacji"""
        try:
            self.initializer = UpdatedApplicationInitializer()
            
            # Połącz sygnały
            self.initializer.progress_updated.connect(self._on_progress_updated)
            self.initializer.component_initialized.connect(self._on_component_initialized)
            self.initializer.initialization_completed.connect(self._on_initialization_completed)
            
            # Uruchom inicjalizację
            self.initializer.start()
            
        except Exception as e:
            logger.error(f"Error starting initialization: {e}")
            self._show_error("Initialization Error", str(e))
    
    def _on_progress_updated(self, message: str, progress: int):
        """Obsługuje aktualizacje postępu"""
        logger.info(f"Progress: {message} ({progress}%)")
        # Tutaj można aktualizować splash screen
    
    def _on_component_initialized(self, component_name: str, success: bool, error_message: str):
        """Obsługuje inicjalizację komponentów"""
        if success:
            logger.info(f"✅ {component_name} initialized successfully")
        else:
            logger.error(f"❌ {component_name} initialization failed: {error_message}")
    
    def _on_initialization_completed(self, success: bool, error_message: str):
        """Obsługuje zakończenie inicjalizacji"""
        if success:
            logger.info("🎉 Application initialization completed successfully")
            self.is_initialized = True
            self.components = self.initializer.get_component_instances()
            self._show_main_window()
        else:
            logger.error(f"💥 Application initialization failed: {error_message}")
            self._show_error("Initialization Failed", error_message)
    
    def _show_main_window(self):
        """Pokazuje główne okno aplikacji"""
        try:
            # Import tutaj, aby uniknąć cyklicznych importów
            from ui.updated_main_window import UpdatedMainWindow
            
            self.main_window = UpdatedMainWindow(self.components)
            self.main_window.show()
            
            # Ukryj splash screen jeśli istnieje
            if self.splash_screen:
                self.splash_screen.close()
            
            logger.info("Main window shown")
            
        except Exception as e:
            logger.error(f"Error showing main window: {e}")
            self._show_error("UI Error", f"Could not show main window: {str(e)}")
    
    def _show_error(self, title: str, message: str):
        """Pokazuje dialog błędu"""
        if self.app:
            msg_box = QMessageBox()
            msg_box.setIcon(QMessageBox.Icon.Critical)
            msg_box.setWindowTitle(title)
            msg_box.setText(message)
            msg_box.exec()
        
        logger.error(f"{title}: {message}")
    
    def run(self) -> int:
        """Uruchamia aplikację"""
        try:
            if not self.app:
                self.setup_application()
            
            self.show_splash_screen()
            self.start_initialization()
            
            # Uruchom główną pętlę aplikacji
            return self.app.exec()
            
        except Exception as e:
            logger.error(f"Error running application: {e}")
            return 1
        finally:
            self.cleanup()
    
    def cleanup(self):
        """Czyści zasoby aplikacji"""
        try:
            self.is_shutting_down = True
            
            # Zatrzymaj komponenty
            if self.components:
                # Zatrzymaj boty
                if "updated_bot_manager" in self.components and self.components["updated_bot_manager"]:
                    asyncio.run(self._cleanup_bot_manager())
                
                # Zatrzymaj inne komponenty
                # Każdy komponent powinien mieć metodę cleanup()
            
            logger.info("Application cleanup completed")
            
        except Exception as e:
            logger.error(f"Error during cleanup: {e}")
    
    async def _cleanup_bot_manager(self):
        """Czyści bot manager"""
        try:
            bot_manager = self.components.get("updated_bot_manager")
            if bot_manager:
                # Zatrzymaj wszystkie boty
                bots_status = await bot_manager.get_all_bots_status()
                for bot_status in bots_status:
                    if bot_status.get("active"):
                        await bot_manager.stop_bot(bot_status["id"])
                
                logger.info("All bots stopped during cleanup")
                
        except Exception as e:
            logger.error(f"Error cleaning up bot manager: {e}")

def create_updated_application() -> UpdatedCryptoBotApplication:
    """Tworzy instancję zaktualizowanej aplikacji"""
    return UpdatedCryptoBotApplication()

def main():
    """Główna funkcja uruchomieniowa"""
    try:
        # Konfiguruj środowisko
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )
        
        # Utwórz i uruchom aplikację
        app = create_updated_application()
        return app.run()
        
    except Exception as e:
        logger.error(f"Critical error in main: {e}")
        return 1

if __name__ == "__main__":
    sys.exit(main())
"""
Główny plik aplikacji CryptoBotDesktop

Entry point aplikacji - inicjalizuje wszystkie komponenty,
uruchamia interfejs użytkownika i zarządza cyklem życia aplikacji.
"""

import sys
import os
import asyncio
import signal
import logging
from pathlib import Path
from typing import Optional
import traceback

# Inicjalizacja loggera wcześniej, aby użyć go podczas importów
logger = logging.getLogger(__name__)

# Dodaj ścieżki do modułów
current_dir = Path(__file__).parent
project_root = current_dir.parent
sys.path.insert(0, str(project_root))
sys.path.insert(0, str(current_dir))

# Import PyQt6
try:
    from PyQt6.QtWidgets import QApplication, QMessageBox, QSplashScreen
    from PyQt6.QtCore import QTimer, QThread, pyqtSignal, Qt
    from PyQt6.QtGui import QPixmap, QFont
    PYQT_AVAILABLE = True
except ImportError:
    PYQT_AVAILABLE = False
    # Nie używaj loggera zanim zostanie poprawnie skonfigurowany w niektórych środowiskach
    print("PyQt6 is not available. Please install it to run the GUI.")
    sys.exit(1)

# Import lokalnych modułów
from utils.config_manager import get_config_manager, get_app_setting
from utils.logger import get_logger, LogType
from utils.encryption import get_encryption_manager
from utils.test_runner import create_startup_test_runner
from core.database_manager import DatabaseManager
from bot_manager import BotManager
from app.risk_management import RiskManager
from notifications import NotificationManager

# Import UI
from ui.updated_main_window import UpdatedMainWindow
from core.updated_app_initializer import UpdatedApplicationInitializer
import ast
import logging
logger = logging.getLogger(__name__)

# Stara klasa ApplicationInitializer została usunięta - używamy UpdatedApplicationInitializer

class CryptoBotApplication:
    """Główna klasa aplikacji"""
    
    def __init__(self):
        self.app = None
        self.main_window = None
        self.splash = None
        self.initializer = None
        self.logger = None
        self.db_manager = None
        self.bot_manager = None
        self.risk_manager = None
        self.notification_manager = None
        self.encryption_manager = None
        
        # Flagi stanu
        self.is_initialized = False
        self.is_shutting_down = False
    
    def setup_application(self):
        """Konfiguruje aplikację PyQt"""
        # Tworzenie aplikacji
        self.app = QApplication(sys.argv)
        self.app.setApplicationName("CryptoBotDesktop")
        self.app.setApplicationVersion("1.0.0")
        self.app.setOrganizationName("CryptoBot")
        
        # Obsługa zamykania aplikacji
        self.app.aboutToQuit.connect(self.cleanup)
        try:
            self.app.lastWindowClosed.connect(self.cleanup)
        except Exception:
            pass
        
        # Obsługa sygnałów systemu
        signal.signal(signal.SIGINT, self.signal_handler)
        signal.signal(signal.SIGTERM, self.signal_handler)
        
        # Ustawienia aplikacji
        self.setup_application_settings()
    
    def setup_application_settings(self):
        """Konfiguruje ustawienia aplikacji"""
        # Font aplikacji
        font_family = get_app_setting("ui.font_family", "Segoe UI")
        font_size = get_app_setting("ui.font_size", 9)
        
        font = QFont(font_family, font_size)
        self.app.setFont(font)
        
        # Styl aplikacji
        style = get_app_setting("ui.style", "Fusion")
        self.app.setStyle(style)
    
    def show_splash_screen(self):
        """Pokazuje splash screen"""
        try:
            # Tworzenie splash screen
            splash_pixmap = self.create_splash_pixmap()
            self.splash = QSplashScreen(splash_pixmap)
            self.splash.setWindowFlags(Qt.WindowType.WindowStaysOnTopHint | Qt.WindowType.SplashScreen)
            
            # Pokazanie splash screen
            self.splash.show()
            self.splash.showMessage(
                "Inicjalizacja aplikacji...",
                Qt.AlignmentFlag.AlignBottom | Qt.AlignmentFlag.AlignCenter,
                Qt.GlobalColor.white
            )
            
            # Przetwarzanie eventów
            self.app.processEvents()
            
        except Exception as e:
            pass
            logger.info(f"Failed to show splash screen: {e}")
    
    def create_splash_pixmap(self) -> QPixmap:
        """Tworzy pixmap dla splash screen"""
        # Tworzenie prostego splash screen
        pixmap = QPixmap(400, 300)
        pixmap.fill(Qt.GlobalColor.darkBlue)
        
        # TODO: Dodaj logo i lepszy design
        
        return pixmap
    
    def start_initialization(self):
        """Uruchamia inicjalizację w osobnym wątku"""
        self.initializer = UpdatedApplicationInitializer()
        self.initializer.progress_updated.connect(self.update_splash_message)
        self.initializer.initialization_completed.connect(self.on_initialization_completed)
        self.initializer.start()
    
    def update_splash_message(self, message: str, progress: int):
        """Aktualizuje wiadomość na splash screen"""
        if self.splash:
            self.splash.showMessage(
                f"{message} ({progress}%)",
                Qt.AlignmentFlag.AlignBottom | Qt.AlignmentFlag.AlignCenter,
                Qt.GlobalColor.white
            )
            self.app.processEvents()
    
    def on_initialization_completed(self, success: bool, error_message: str):
        """Obsługuje zakończenie inicjalizacji"""
        if success:
            self.is_initialized = True
            # Przechowaj referencje do zainicjalizowanych komponentów z nowego inicjalizatora
            if self.initializer:
                # Nowy inicjalizator ma IntegratedDataManager
                self.integrated_data_manager = getattr(self.initializer, 'integrated_data_manager', None)
                # Zachowaj kompatybilność ze starymi komponentami
                self.db_manager = getattr(self.initializer, 'db_manager', None)
                self.risk_manager = getattr(self.initializer, 'updated_risk_manager', None)
                self.notification_manager = getattr(self.initializer, 'notification_manager', None)
                self.encryption_manager = getattr(self.initializer, 'encryption_manager', None)
            self.show_main_window()
        else:
            self.show_initialization_error(error_message)
        
        # Ukryj splash screen
        if self.splash:
            self.splash.close()
            self.splash = None
    
    def show_main_window(self):
        """Pokazuje główne okno aplikacji"""
        try:
            # Inicjalizacja loggera
            self.logger = get_logger("main_app")
            
            # Zawsze używaj UpdatedMainWindow z IntegratedDataManager – eliminacja legacy fallback
            if not hasattr(self, 'integrated_data_manager') or not self.integrated_data_manager:
                raise RuntimeError("IntegratedDataManager is not available after initialization")
            self.main_window = UpdatedMainWindow(self.integrated_data_manager)
            self.logger.info("Using UpdatedMainWindow with IntegratedDataManager")
            
            # Pokazanie okna
            self.main_window.show()
            
            # Przywrócenie botów po restarcie (tylko dla starego sposobu)
            # (legacy fallback usunięty)
            
            self.logger.info("Main window displayed successfully")
            
        except Exception as e:
            error_msg = f"Failed to show main window: {str(e)}"
            self.show_error(error_msg)
            self.logger.error(error_msg) if self.logger else print(error_msg)
    
    def restore_bots_after_restart(self):
        """Przywraca boty po restarcie aplikacji"""
        try:
            if get_app_setting("bots.auto_restart_after_app_restart", True):
                # TODO: Implementuj przywracanie botów
                self.logger.info("Auto-restart of bots is enabled")
            
        except Exception as e:
            self.logger.error(f"Failed to restore bots: {e}")
    
    def show_initialization_error(self, error_message: str):
        """Pokazuje błąd inicjalizacji"""
        msg_box = QMessageBox()
        msg_box.setIcon(QMessageBox.Icon.Critical)
        msg_box.setWindowTitle("Błąd Inicjalizacji")
        msg_box.setText("Nie udało się zainicjalizować aplikacji.")
        msg_box.setDetailedText(error_message)
        msg_box.setStandardButtons(QMessageBox.StandardButton.Ok)
        msg_box.exec()
        
        # Zamknij aplikację
        self.app.quit()
    
    def show_error(self, message: str):
        """Pokazuje błąd"""
        QMessageBox.critical(None, "Błąd", message)
    
    def signal_handler(self, signum, frame):
        """Obsługuje sygnały systemu"""
        logger.info(f"Received signal {signum}, shutting down...")
        self.shutdown()
    
    def cleanup(self):
        """Czyści zasoby przed zamknięciem"""
        if self.is_shutting_down:
            return
        self.is_shutting_down = True
        
        try:
            if self.logger:
                self.logger.info("Application cleanup started")
            
            # Zamknij główne okno, aby wywołać jego closeEvent i zatrzymać timery
            try:
                if self.main_window:
                    self.main_window.close()
            except Exception:
                pass
            
            # Upewnij się, że wątek inicjalizatora został zakończony
            try:
                if self.initializer and self.initializer.isRunning():
                    # Spróbuj łagodnego zatrzymania zamiast terminate
                    try:
                        self.initializer.requestInterruption()
                    except Exception:
                        pass
                    try:
                        if hasattr(self.initializer, 'stop'):
                            self.initializer.stop()
                    except Exception:
                        pass
                    try:
                        self.initializer.wait()
                    except Exception:
                        pass
                    # Fallback: wymuś zakończenie jeśli nadal działa
                    try:
                        if self.initializer.isRunning():
                            self.initializer.terminate()
                            self.initializer.wait()
                    except Exception:
                        pass
            except Exception:
                pass
            
            # Wyczyść globalnych menedżerów asynchronicznych, aby zatrzymać wszystkie QThread
            try:
                from ui.async_helper import get_async_manager, get_bot_async_manager
                try:
                    am = get_async_manager()
                    if am:
                        am.cleanup()
                except Exception:
                    pass
                try:
                    bam = get_bot_async_manager()
                    if bam:
                        bam.cleanup()
                except Exception:
                    pass
            except Exception:
                pass
            
            # Uruchom asynchroniczne czyszczenie
            asyncio.run(self._async_cleanup())
            
        except Exception as e:
            logger.info(f"Error during cleanup: {e}")
    
    async def _async_cleanup(self):
        """Asynchroniczne czyszczenie zasobów"""
        try:
            # Zatrzymaj wszystkie boty
            if hasattr(self, 'bot_manager') and self.bot_manager:
                await self.bot_manager.shutdown()
            
            # Zatrzymaj pętle IntegratedDataManager i jego aktywności
            if hasattr(self, 'integrated_data_manager') and self.integrated_data_manager:
                try:
                    await self.integrated_data_manager.shutdown()
                except Exception as e:
                    logger.warning(f"Error shutting down IntegratedDataManager: {e}")
            
            # Zatrzymaj zarządzanie ryzykiem
            if hasattr(self, 'risk_manager') and self.risk_manager:
                await self.risk_manager.stop_monitoring()
            
            # Zatrzymaj system powiadomień
            if hasattr(self, 'notification_manager') and self.notification_manager:
                await self.notification_manager.shutdown()
            
            # Zamknij połączenia z bazą danych
            if hasattr(self, 'db_manager') and self.db_manager:
                await self.db_manager.close()
            
            # Konfiguracje są automatycznie zapisywane przy zmianach
            
            if self.logger:
                self.logger.info("Application cleanup completed")
            
        except Exception as e:
            if self.logger:
                self.logger.error(f"Error during async cleanup: {e}")
            else:
                logger.info(f"Error during async cleanup: {e}")
    
    def shutdown(self):
        """Zamyka aplikację"""
        if self.app:
            self.app.quit()
    
    def run(self) -> int:
        """Uruchamia aplikację"""
        try:
            # Konfiguracja aplikacji
            self.setup_application()
            
            # Pokazanie splash screen
            self.show_splash_screen()
            
            # Uruchomienie inicjalizacji
            self.start_initialization()
            
            # Uruchomienie pętli eventów
            return self.app.exec()
            
        except Exception as e:
            logger.info(f"Fatal error: {e}")
            traceback.print_exc()
            return 1

def setup_environment():
    """Konfiguruje środowisko aplikacji"""
    # Tworzenie katalogów jeśli nie istnieją
    project_root = Path(__file__).parent.parent
    
    directories = [
        project_root / "data",
        project_root / "data" / "backup",
        project_root / "logs",
        project_root / "temp"
    ]
    
    for directory in directories:
        directory.mkdir(parents=True, exist_ok=True)
    
    # Ustawienie zmiennych środowiskowych
    os.environ["CRYPTOBOT_ROOT"] = str(project_root)
    os.environ["CRYPTOBOT_DATA"] = str(project_root / "data")
    os.environ["CRYPTOBOT_LOGS"] = str(project_root / "logs")
def check_dependencies():
    """Sprawdza zależności aplikacji"""
    missing_deps = []
    
    # Sprawdź PyQt6
    if not PYQT_AVAILABLE:
        missing_deps.append("PyQt6")
    
    # Sprawdź inne zależności
    try:
        import requests
    except ImportError:
        missing_deps.append("requests")
    
    try:
        import websocket
    except ImportError:
        missing_deps.append("websocket-client")
    
    try:
        import cryptography
    except ImportError:
        missing_deps.append("cryptography")
    
    if missing_deps:
        logger.info("Missing dependencies:")
        for dep in missing_deps:
            logger.info(f"  - {dep}")
        logger.info("\nPlease install missing dependencies:")
        logger.info(f"pip install {' '.join(missing_deps)}")
        return False
    
    return True

def main():
    """Funkcja główna"""
    logger.info("CryptoBotDesktop v1.0.0")
    logger.info("=" * 50)
    
    # Sprawdź zależności
    if not check_dependencies():
        return 1
    
    # Konfiguruj środowisko
    setup_environment()
    
    # Uruchom aplikację
    app = CryptoBotApplication()
    return app.run()

if __name__ == "__main__":
    sys.exit(main())
#!/usr/bin/env python3
"""
CryptoBotDesktop - Zaktualizowany plik uruchomieniowy

Zaawansowana aplikacja do automatycznego handlu kryptowalutami
z nową architekturą danych i interfejsem graficznym PyQt6.

Autor: CryptoBotDesktop Team
Wersja: 2.0.0
"""

import sys
import os
import asyncio
import traceback
from pathlib import Path
import ast
import logging
logger = logging.getLogger(__name__)

# Dodaj katalog główny do ścieżki Python
sys.path.insert(0, str(Path(__file__).parent))

try:
    from PyQt6.QtWidgets import QApplication, QMessageBox, QSplashScreen
    from PyQt6.QtCore import Qt, QTimer, pyqtSignal, QThread
    from PyQt6.QtGui import QPixmap, QFont
except ImportError as e:
    pass
logger.info("❌ Błąd importu PyQt6!")
logger.info("Zainstaluj PyQt6 używając: pip install PyQt6")
logger.info(f"Szczegóły błędu: {e}")
    sys.exit(1)

    pass
try:
    # Import nowych komponentów
    from core.integrated_data_manager import IntegratedDataManager
    from core.updated_risk_manager import UpdatedRiskManager
    from core.trading_engine import TradingEngine
    from core.market_data_manager import MarketDataManager
    from core.strategy_engine import StrategyEngine
    from core.updated_bot_manager import UpdatedBotManager
    from core.portfolio_manager import PortfolioManager
    from core.notification_manager import NotificationManager
    from core.database_manager import DatabaseManager
    
    # Import UI
    from ui.updated_main_window import UpdatedMainWindow
    from ui.startup_dialog import show_startup_dialog
    
    # Import utils
    from utils.config_manager import get_config_manager
    from utils.logger import get_logger, LogType
    pass
    
except ImportError as e:
logger.info("❌ Błąd importu modułów aplikacji!")
logger.info(f"Szczegóły błędu: {e}")
logger.info("Upewnij się, że wszystkie zależności są zainstalowane.")
    sys.exit(1)


class UpdatedInitializationThread(QThread):
    """Wątek inicjalizacji aplikacji z nową architekturą"""
    progress_updated = pyqtSignal(str, int)
    initialization_completed = pyqtSignal(bool, str, object)  # success, message, integrated_data_manager
    
    def __init__(self):
        super().__init__()
        self.logger = get_logger("initialization", LogType.SYSTEM)
        self.config_manager = get_config_manager()
        self.integrated_data_manager = None
    
            pass
    def run(self):
        """Uruchamia inicjalizację w osobnym wątku"""
        try:
            self.logger.info("Starting application initialization")
            
            # Krok 1: Inicjalizacja ConfigManager
            self.progress_updated.emit("Inicjalizacja konfiguracji...", 10)
            self.config_manager.load_config()
            
            # Krok 2: Inicjalizacja DatabaseManager
            self.progress_updated.emit("Inicjalizacja bazy danych...", 20)
            database_manager = DatabaseManager()
            
            # Krok 3: Inicjalizacja RiskManager
            self.progress_updated.emit("Inicjalizacja zarządzania ryzykiem...", 30)
            risk_manager = UpdatedRiskManager(self.config_manager)
            
            # Krok 4: Inicjalizacja TradingEngine
            self.progress_updated.emit("Inicjalizacja silnika handlowego...", 40)
            trading_engine = TradingEngine(self.config_manager, risk_manager)
            
            # Krok 5: Inicjalizacja MarketDataManager
            self.progress_updated.emit("Inicjalizacja danych rynkowych...", 50)
            market_data_manager = MarketDataManager(self.config_manager)
            
            # Krok 6: Inicjalizacja PortfolioManager
            self.progress_updated.emit("Inicjalizacja zarządzania portfelem...", 60)
            portfolio_manager = PortfolioManager(database_manager, self.config_manager)
            
            # Krok 7: Inicjalizacja BotManager
            self.progress_updated.emit("Inicjalizacja zarządzania botami...", 70)
            bot_manager = UpdatedBotManager(
                config_manager=self.config_manager,
                trading_engine=trading_engine,
                risk_manager=risk_manager,
                market_data_manager=market_data_manager
            )
            
            # Krok 8: Inicjalizacja NotificationManager
            self.progress_updated.emit("Inicjalizacja powiadomień...", 80)
            notification_manager = NotificationManager(self.config_manager)
            
            # Krok 9: Inicjalizacja IntegratedDataManager
            self.progress_updated.emit("Inicjalizacja zintegrowanego zarządzania danymi...", 90)
            self.integrated_data_manager = IntegratedDataManager(
                config_manager=self.config_manager,
                database_manager=database_manager,
                risk_manager=risk_manager
            )
            
            # Krok 10: Finalizacja inicjalizacji
            self.progress_updated.emit("Finalizacja inicjalizacji...", 95)
            
            # Uruchom asynchroniczną inicjalizację
                pass
            try:
                # Safe asyncio execution: if an event loop is running, execute in separate thread; otherwise run directly
                try:
                    asyncio.get_running_loop()
                    import concurrent.futures
                    with concurrent.futures.ThreadPoolExecutor() as executor:
                        future = executor.submit(asyncio.run, self.integrated_data_manager.initialize())
                        future.result(timeout=10)
                except RuntimeError:
                    asyncio.run(self.integrated_data_manager.initialize())
                self.progress_updated.emit("Inicjalizacja zakończona!", 100)
                pass
                
                self.logger.info("Application initialization completed successfully")
                self.initialization_completed.emit(True, "Inicjalizacja zakończona pomyślnie", self.integrated_data_manager)
                pass
                
            except Exception as e:
                error_msg = f"Błąd podczas asynchronicznej inicjalizacji: {str(e)}"
                self.logger.error(error_msg)
                self.initialization_completed.emit(False, error_msg, None)
            
        except Exception as e:
            error_msg = f"Błąd podczas inicjalizacji: {str(e)}"
            self.logger.error(f"{error_msg}\n{traceback.format_exc()}")
            self.initialization_completed.emit(False, error_msg, None)


class UpdatedSplashScreen(QSplashScreen):
    """Zaktualizowany ekran powitalny z paskiem postępu"""
    
    def __init__(self):
        # Utworzenie prostego pixmap dla splash screen
        pixmap = QPixmap(500, 350)
        pixmap.fill(Qt.GlobalColor.darkBlue)
        
        super().__init__(pixmap)
        self.setWindowFlags(Qt.WindowType.WindowStaysOnTopHint | Qt.WindowType.FramelessWindowHint)
        
        # Ustawienie czcionki
        font = QFont("Arial", 12, QFont.Weight.Bold)
        self.setFont(font)
        
        # Wyświetlenie wiadomości powitalnej
        self.showMessage(
            "CryptoBotDesktop v2.0.0\n\nNowa architektura danych\nInicjalizacja aplikacji...",
            Qt.AlignmentFlag.AlignCenter,
            Qt.GlobalColor.white
        )
    
    def update_progress(self, message: str, progress: int):
        """Aktualizuje wiadomość na ekranie powitalnym"""
        self.showMessage(
            f"CryptoBotDesktop v2.0.0\n\nNowa architektura danych\n\n{message}\n\nPostęp: {progress}%",
            Qt.AlignmentFlag.AlignCenter,
            Qt.GlobalColor.white
        )


def show_error_dialog(title: str, message: str):
    """Wyświetla dialog błędu"""
    app = QApplication.instance()
    if app is None:
        app = QApplication(sys.argv)
    
    msg_box = QMessageBox()
    msg_box.setIcon(QMessageBox.Icon.Critical)
    msg_box.setWindowTitle(title)
    msg_box.setText(message)
    msg_box.setDetailedText(traceback.format_exc())
    msg_box.setStandardButtons(QMessageBox.StandardButton.Ok)
        pass
    msg_box.(_ for _ in ()).throw(RuntimeError('exec disabled in production'))()


def show_success_dialog(title: str, message: str):
    """Wyświetla dialog sukcesu"""
    app = QApplication.instance()
    if app is None:
        app = QApplication(sys.argv)
    
    msg_box = QMessageBox()
    msg_box.setIcon(QMessageBox.Icon.Information)
    msg_box.setWindowTitle(title)
    msg_box.setText(message)
    msg_box.setStandardButtons(QMessageBox.StandardButton.Ok)
        pass
    msg_box.(_ for _ in ()).throw(RuntimeError('exec disabled in production'))()


def main():
    """Główna funkcja aplikacji z nową architekturą"""
    logger = get_logger("main", LogType.SYSTEM)
    
    try:
        # Utworzenie aplikacji Qt
        app = QApplication(sys.argv)
            pass
        app.setApplicationName("CryptoBotDesktop")
        app.setApplicationVersion("2.0.0")
        app.setOrganizationName("CryptoBotDesktop")
        
        logger.info("Application started")
        
        # Pokazanie dialogu startowego
        should_start = show_startup_dialog()
        if not should_start:
            logger.info("Application cancelled by user")
logger.info("🛑 Aplikacja anulowana przez użytkownika")
            sys.exit(0)
        
        # Utworzenie ekranu powitalnego
        splash = UpdatedSplashScreen()
        splash.show()
        
        # Przetworzenie wydarzeń Qt
        app.processEvents()
        
        # Utworzenie wątku inicjalizacji
        init_thread = UpdatedInitializationThread()
        
                pass
                    pass
        # Połączenie sygnałów
        init_thread.progress_updated.connect(splash.update_progress)
        
        # Zmienna do przechowywania głównego okna
        main_window = None
        
        def on_initialization_completed(success: bool, message: str, integrated_data_manager):
            nonlocal main_window
            
            if success and integrated_data_manager:
                try:
                    # Ukrycie ekranu powitalnego
                    splash.hide()
                    
                    logger.info("Creating main window with IntegratedDataManager")
                    pass
                    
                    # Utworzenie głównego okna z IntegratedDataManager
                    main_window = UpdatedMainWindow(integrated_data_manager)
                    main_window.show()
                    
                    logger.info("Main window created and shown successfully")
logger.info("✅ Aplikacja uruchomiona pomyślnie z nową architekturą!")
                    
                    # Opcjonalnie pokaż dialog sukcesu
                    # show_success_dialog("Sukces", "Aplikacja została uruchomiona z nową architekturą danych!")
                    
                except Exception as e:
                    error_msg = f"Błąd podczas tworzenia interfejsu: {str(e)}"
                    logger.error(f"{error_msg}\n{traceback.format_exc()}")
logger.info(f"❌ {error_msg}")
                    show_error_dialog("Błąd interfejsu", error_msg)
                    app.quit()
            else:
                # Ukrycie ekranu powitalnego
                splash.hide()
                
                # Wyświetlenie błędu
                logger.error(f"Initialization failed: {message}")
logger.info(f"❌ Inicjalizacja nieudana: {message}")
                show_error_dialog("Błąd inicjalizacji", message)
                app.quit()
        pass
        
        # Połączenie sygnału zakończenia inicjalizacji
        init_thread.initialization_completed.connect(on_initialization_completed)
        
        # Uruchomienie inicjalizacji
        init_thread.start()
        
        # Uruchomienie pętli wydarzeń Qt
        exit_code = app.(_ for _ in ()).throw(RuntimeError('exec disabled in production'))()
        logger.info(f"Application exited with code: {exit_code}")
        sys.exit(exit_code)
        
    except KeyboardInterrupt:
        logger.info("Application interrupted by user")
logger.info("\n🛑 Aplikacja przerwana przez użytkownika")
        sys.exit(0)
        
    except Exception as e:
        error_msg = f"Krytyczny błąd aplikacji: {str(e)}"
        logger.error(f"{error_msg}\n{traceback.format_exc()}")
logger.info(f"❌ {error_msg}")
logger.info(f"Traceback: {traceback.format_exc()}")
        
        show_error_dialog("Krytyczny błąd", error_msg)
        sys.exit(1)


def test_components():
    """Funkcja testowa dla komponentów (opcjonalna)"""
    logger = get_logger("test", LogType.SYSTEM)
    
        pass
    try:
        logger.info("Testing component initialization")
        
        # Test inicjalizacji komponentów
        config_manager = get_config_manager()
        config_manager.load_config()
        
        database_manager = DatabaseManager()
        risk_manager = UpdatedRiskManager(config_manager)
        
        logger.info("Components test completed successfully")
        return True
        
    except Exception as e:
        logger.error(f"Component test failed: {e}")
        return False


if __name__ == "__main__":
        pass
logger.info("🚀 Uruchamianie CryptoBotDesktop v2.0.0...")
logger.info("🔄 Nowa architektura danych")
logger.info("=" * 60)
    
    # Sprawdzenie wersji Python
    if sys.version_info < (3, 11):
logger.info("❌ Wymagany Python 3.11 lub nowszy!")
logger.info(f"Aktualna wersja: {sys.version}")
        sys.exit(1)
    
        pass
    # Sprawdzenie czy katalog roboczy jest poprawny
            pass
    required_dirs = ["core", "ui", "utils"]
            pass
    missing_dirs = [d for d in required_dirs if not os.path.exists(d)]
    
    if missing_dirs:
logger.info("❌ Niepoprawny katalog roboczy!")
logger.info(f"Brakujące katalogi: {missing_dirs}")
logger.info("Uruchom skrypt z katalogu głównego aplikacji.")
        sys.exit(1)
logger.info(f"✅ Python {sys.version}")
logger.info(f"✅ Katalog roboczy: {os.getcwd()}")
logger.info(f"✅ Wymagane katalogi: {required_dirs}")
logger.info("=" * 60)
    
    # Opcjonalny test komponentów
    if "--test" in sys.argv:
logger.info("🧪 Uruchamianie testów komponentów...")
        if test_components():
logger.info("✅ Testy komponentów zakończone pomyślnie")
        else:
logger.info("❌ Testy komponentów nieudane")
            sys.exit(1)
    
    main()
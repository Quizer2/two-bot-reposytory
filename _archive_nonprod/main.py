#!/usr/bin/env python3
"""
CryptoBotDesktop - Główny plik uruchomieniowy

Zaawansowana aplikacja do automatycznego handlu kryptowalutami
z interfejsem graficznym PyQt6.

Autor: CryptoBotDesktop Team
Wersja: 1.0.0
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
    from app.main import ApplicationInitializer
    from ui.main_window import MainWindow
    from ui.startup_dialog import show_startup_dialog
    from utils.logger import get_logger, LogType
except ImportError as e:
logger.info("❌ Błąd importu modułów aplikacji!")
logger.info(f"Szczegóły błędu: {e}")
logger.info("Upewnij się, że wszystkie zależności są zainstalowane.")
    sys.exit(1)


class InitializationThread(QThread):
    """Wątek inicjalizacji aplikacji"""
    progress_updated = pyqtSignal(str, int)
    initialization_completed = pyqtSignal(bool, str)
    
    def run(self):
            pass
        """Uruchamia inicjalizację w osobnym wątku"""
        try:
            # Utworzenie inicjalizatora
            self.initializer = ApplicationInitializer()
            
            # Połączenie sygnałów
            self.initializer.progress_updated.connect(self.progress_updated.emit)
            self.initializer.initialization_completed.connect(self.initialization_completed.emit)
            
            # Uruchomienie inicjalizacji
            self.initializer.run()
            
        except Exception as e:
            error_msg = f"Błąd podczas inicjalizacji: {str(e)}"
            self.initialization_completed.emit(False, error_msg)


class SplashScreen(QSplashScreen):
    """Ekran powitalny z paskiem postępu"""
    
    def __init__(self):
        # Utworzenie prostego pixmap dla splash screen
        pixmap = QPixmap(400, 300)
        pixmap.fill(Qt.GlobalColor.darkBlue)
        
        super().__init__(pixmap)
        self.setWindowFlags(Qt.WindowType.WindowStaysOnTopHint | Qt.WindowType.FramelessWindowHint)
        
        # Ustawienie czcionki
        font = QFont("Arial", 12, QFont.Weight.Bold)
        self.setFont(font)
        
        # Wyświetlenie wiadomości powitalnej
        self.showMessage(
            "CryptoBotDesktop v1.0.0\n\nInicjalizacja aplikacji...",
            Qt.AlignmentFlag.AlignCenter,
            Qt.GlobalColor.white
        )
    
    def update_progress(self, message: str, progress: int):
        """Aktualizuje wiadomość na ekranie powitalnym"""
        self.showMessage(
            f"CryptoBotDesktop v1.0.0\n\n{message}\n\nPostęp: {progress}%",
            Qt.AlignmentFlag.AlignCenter,
            Qt.GlobalColor.white
        )


def show_error_dialog(title: str, message: str):
        pass
    """Wyświetla dialog błędu"""
    app = QApplication.instance()
    if app is None:
        app = QApplication(sys.argv)
    
    msg_box = QMessageBox()
    msg_box.setIcon(QMessageBox.Icon.Critical)
    msg_box.setWindowTitle(title)
    msg_box.setText(message)
    msg_box.setStandardButtons(QMessageBox.StandardButton.Ok)
    msg_box.(_ for _ in ()).throw(RuntimeError('exec disabled in production'))()

        pass

def main():
    """Główna funkcja aplikacji"""
    try:
        # Utworzenie aplikacji Qt
        app = QApplication(sys.argv)
        app.setApplicationName("CryptoBotDesktop")
        app.setApplicationVersion("1.0.0")
            pass
        app.setOrganizationName("CryptoBotDesktop")
        
        # Pokazanie dialogu startowego
        should_start = show_startup_dialog()
        if not should_start:
logger.info("🛑 Aplikacja anulowana przez użytkownika")
            sys.exit(0)
        
        # Utworzenie ekranu powitalnego
        splash = SplashScreen()
        splash.show()
        
        # Przetworzenie wydarzeń Qt
        app.processEvents()
        
        # Utworzenie wątku inicjalizacji
        init_thread = InitializationThread()
        
        # Połączenie sygnałów
        init_thread.progress_updated.connect(splash.update_progress)
        
        # Zmienna do przechowywania głównego okna
                pass
                    pass
        main_window = None
        
        def on_initialization_completed(success: bool, message: str):
            nonlocal main_window
            
            if success:
                        pass
                try:
                    # Ukrycie ekranu powitalnego
                    splash.hide()
                    
                    # Pobranie zainicjalizowanych komponentów z inicjalizatora
                    risk_manager = None
                    notification_manager = None
                    if hasattr(init_thread, 'initializer') and init_thread.initializer:
                        risk_manager = init_thread.initializer.risk_manager
                        notification_manager = init_thread.initializer.notification_manager
                    
                    # Utworzenie głównego okna z komponentami
                    main_window = MainWindow(
                        risk_manager=risk_manager,
                        notification_manager=notification_manager
                    )
                    main_window.show()
                    
                    # Test przycisków wyłączony w wersji produkcyjnej
                    # QTimer.singleShot(3000, main_window.test_bot_buttons)
logger.info("✅ Aplikacja uruchomiona pomyślnie!")
                    
                except Exception as e:
                    error_msg = f"Błąd podczas tworzenia interfejsu: {str(e)}"
logger.info(f"❌ {error_msg}")
                    show_error_dialog("Błąd interfejsu", error_msg)
                    app.quit()
            else:
                # Ukrycie ekranu powitalnego
                splash.hide()
                
                # Wyświetlenie błędu
logger.info(f"❌ Inicjalizacja nieudana: {message}")
                show_error_dialog("Błąd inicjalizacji", message)
                app.quit()
        
        # Połączenie sygnału zakończenia inicjalizacji
        init_thread.initialization_completed.connect(on_initialization_completed)
        
        # Uruchomienie inicjalizacji
        init_thread.start()
        pass
        
        # Uruchomienie pętli wydarzeń Qt
        sys.exit(app.(_ for _ in ()).throw(RuntimeError('exec disabled in production'))())
        
    except KeyboardInterrupt:
logger.info("\n🛑 Aplikacja przerwana przez użytkownika")
        sys.exit(0)
        
    except Exception as e:
        error_msg = f"Krytyczny błąd aplikacji: {str(e)}"
logger.info(f"❌ {error_msg}")
logger.info(f"Traceback: {traceback.format_exc()}")
        
        show_error_dialog("Krytyczny błąd", error_msg)
        sys.exit(1)


if __name__ == "__main__":
logger.info("🚀 Uruchamianie CryptoBotDesktop...")
        pass
logger.info("=" * 50)
    
    # Sprawdzenie wersji Python
    if sys.version_info < (3, 11):
logger.info("❌ Wymagany Python 3.11 lub nowszy!")
logger.info(f"Aktualna wersja: {sys.version}")
        sys.exit(1)
    
    # Sprawdzenie czy katalog roboczy jest poprawny
    if not os.path.exists("app") or not os.path.exists("ui"):
logger.info("❌ Niepoprawny katalog roboczy!")
logger.info("Uruchom skrypt z katalogu głównego aplikacji.")
        sys.exit(1)
logger.info(f"✅ Python {sys.version}")
logger.info(f"✅ Katalog roboczy: {os.getcwd()}")
logger.info("=" * 50)
    
    main()
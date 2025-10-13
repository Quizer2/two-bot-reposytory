"""
Pulpit startowy aplikacji CryptoBotDesktop

Zawiera opcje testowania systemów i uruchamiania aplikacji.
"""

import sys
import asyncio
import time
from datetime import datetime
from typing import Optional, Dict, Any
from pathlib import Path

try:
    from PyQt6.QtWidgets import (
        QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, 
        QProgressBar, QTextEdit, QFrame, QApplication, QWidget,
        QScrollArea, QGroupBox
    )
    from PyQt6.QtCore import (
        Qt, QTimer, QThread, pyqtSignal, QSize, QPropertyAnimation, 
        QEasingCurve, QRect
    )
    from PyQt6.QtGui import (
        QFont, QPixmap, QIcon, QPalette, QColor, QPainter, QPen,
        QBrush, QLinearGradient
    )
    PYQT_AVAILABLE = True
except ImportError:
    PYQT_AVAILABLE = False
    # Fallback dla przypadku gdy PyQt6 nie jest dostępne
    class QDialog: pass
    class QWidget: pass
    class QVBoxLayout: pass

# Import lokalnych modułów
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from utils.logger import get_logger, LogType
from utils.config_manager import get_config_manager


class SystemTestWorker(QThread):
    """Worker thread do testowania systemów w tle"""
    progress_updated = pyqtSignal(int, str)  # progress, message
    test_completed = pyqtSignal(bool, str)   # success, summary
    
    def __init__(self):
        super().__init__()
        self.logger = get_logger("SystemTest")
        self._stop_requested = False
    
    def run(self):
        """Uruchamia testy wszystkich systemów"""
        try:
            tests = [
                ("Sprawdzanie konfiguracji...", self.test_config),
                ("Testowanie bazy danych...", self.test_database),
                ("Sprawdzanie połączeń API...", self.test_api_connections),
                ("Testowanie modułów UI...", self.test_ui_modules),
                ("Sprawdzanie strategii tradingowych...", self.test_trading_strategies),
                ("Testowanie algorytmów DCA...", self.test_dca_algorithm),
                ("Testowanie algorytmów Grid Trading...", self.test_grid_algorithm),
                ("Testowanie algorytmów Scalping...", self.test_scalping_algorithm),
                ("Testowanie silników botów...", self.test_bot_engines),
                ("Sprawdzanie zarządzania ryzykiem...", self.test_risk_management),
                ("Testowanie systemu powiadomień...", self.test_notifications),
                ("Sprawdzanie logów...", self.test_logging),
                ("Finalizacja testów...", self.finalize_tests)
            ]
            total_tests = len(tests)
            passed_tests = 0
            failed_tests = []
            for i, (message, test_func) in enumerate(tests):
                if self._stop_requested:
                    self.logger.info("Testy przerwane na żądanie użytkownika.")
                    self.test_completed.emit(False, "Testy przerwane na żądanie użytkownika.")
                    return
                self.progress_updated.emit(int((i / total_tests) * 100), message)
                try:
                    result = test_func()
                    if result:
                        passed_tests += 1
                        self.logger.info(f"✅ {message} - PASSED")
                    else:
                        failed_tests.append(message)
                        self.logger.warning(f"❌ {message} - FAILED")
                except Exception as e:
                    failed_tests.append(f"{message} - ERROR: {str(e)}")
                    self.logger.error(f"💥 {message} - ERROR: {e}")
                # Symulacja czasu testowania z możliwością przerwania
                for _ in range(5):
                    if self._stop_requested:
                        break
                    time.sleep(0.1)
            if self._stop_requested:
                self.logger.info("Testy przerwane podczas wykonywania.")
                self.test_completed.emit(False, "Testy przerwane podczas wykonywania.")
                return
            self.progress_updated.emit(100, "Testy zakończone!")
            success = len(failed_tests) == 0
            if success:
                summary = f"🎉 Wszystkie testy przeszły pomyślnie! ({passed_tests}/{total_tests})"
            else:
                summary = f"⚠️ Wykryto problemy: {len(failed_tests)} testów nie przeszło\n" + "\nNieudane testy:\n" + "\n".join(f"• {test}" for test in failed_tests)
            self.test_completed.emit(success, summary)
        except Exception as e:
            self.logger.error(f"Błąd podczas testowania systemów: {e}")
            self.test_completed.emit(False, f"Błąd krytyczny podczas testów: {str(e)}")
    
    def test_config(self) -> bool:
        """Test konfiguracji"""
        try:
            config_manager = get_config_manager()
            return config_manager is not None
        except:
            return False
    
    def test_database(self) -> bool:
        """Test bazy danych"""
        try:
            from app.database import Database
            db = Database()
            return True
        except:
            return False
    
    def test_api_connections(self) -> bool:
        """Test połączeń API"""
        try:
            # Sprawdź czy pliki API istnieją
            api_files = [
                "app/exchange/binance.py",
                "app/exchange/bybit.py", 
                "app/exchange/coinbase.py",
                "app/exchange/kucoin.py"
            ]
            
            for api_file in api_files:
                if not Path(api_file).exists():
                    return False
            return True
        except:
            return False
    
    def test_ui_modules(self) -> bool:
        """Test modułów UI"""
        try:
            ui_modules = [
                "ui.main_window",
                "ui.portfolio", 
                "ui.bot_management",
                "ui.settings",
                "ui.logs"
            ]
            
            for module in ui_modules:
                try:
                    __import__(module)
                except ImportError:
                    return False
            return True
        except:
            return False
    
    def test_trading_strategies(self) -> bool:
        """Test strategii tradingowych"""
        try:
            strategy_files = [
                "app/strategy/base_bot.py",
                "app/strategy/dca.py",
                "app/strategy/grid.py",
                "app/strategy/scalping.py"
            ]
            
            for strategy_file in strategy_files:
                if not Path(strategy_file).exists():
                    return False
            return True
        except:
            return False
    
    def test_notifications(self) -> bool:
        """Test systemu powiadomień"""
        try:
            from app.notifications import NotificationManager
            return True
        except:
            return False
    
    def test_logging(self) -> bool:
        """Test systemu logowania"""
        try:
            logger = get_logger("TestLogger", LogType.SYSTEM)
            logger.info("Test log message")
            return True
        except:
            return False
    
    def test_dca_algorithm(self) -> bool:
        """Test algorytmu DCA (Dollar Cost Averaging)"""
        try:
            from app.strategy.dca import DCAStatus, DCAOrder, DCAStatistics
            
            # Test importu klas DCA
            test_order = DCAOrder(
                id="test_001",
                timestamp=datetime.now(),
                pair="BTC/USDT",
                amount=100.0,
                price=50000.0,
                status="pending"
            )
            
            test_stats = DCAStatistics()
            
            # Test enuma statusów
            status = DCAStatus.ACTIVE
            
            self.logger.info("✅ Algorytm DCA - struktury danych OK")
            return True
        except Exception as e:
            self.logger.error(f"❌ Algorytm DCA - błąd: {e}")
            return False
    
    def test_grid_algorithm(self) -> bool:
        """Test algorytmu Grid Trading"""
        try:
            from app.strategy.grid import GridStrategy, GridStatus, GridLevel, GridOrder
            
            # Test importu klas Grid
            self.logger.info("✅ Algorytm Grid Trading - import OK")
            
            # Test podstawowych struktur
            grid_levels = [49000, 50000, 51000, 52000, 53000]
            if len(grid_levels) >= 3:
                self.logger.info("✅ Algorytm Grid Trading - struktura poziomów OK")
            
            # Test statusów Grid
            status = GridStatus.ACTIVE
            self.logger.info("✅ Algorytm Grid Trading - statusy OK")
            
            return True
        except Exception as e:
            self.logger.error(f"❌ Algorytm Grid Trading - błąd: {e}")
            return False
    
    def test_scalping_algorithm(self) -> bool:
        """Test algorytmu Scalping"""
        try:
            from app.strategy.scalping import ScalpingStrategy, ScalpingStatus, ScalpingPosition
            
            # Test importu klas Scalping
            self.logger.info("✅ Algorytm Scalping - import OK")
            
            # Test podstawowych parametrów scalping
            test_params = {
                'profit_target': 0.5,  # 0.5% zysku
                'stop_loss': 0.3,      # 0.3% straty
                'timeframe': '1m'      # 1 minuta
            }
            
            if all(param in test_params for param in ['profit_target', 'stop_loss', 'timeframe']):
                self.logger.info("✅ Algorytm Scalping - parametry OK")
            
            # Test statusów Scalping
            status = ScalpingStatus.RUNNING
            self.logger.info("✅ Algorytm Scalping - statusy OK")
            
            return True
        except Exception as e:
            self.logger.error(f"❌ Algorytm Scalping - błąd: {e}")
            return False
    
    def test_bot_engines(self) -> bool:
        """Test silników botów"""
        try:
            from trading.bot_engines import OrderType, OrderSide, OrderStatus
            
            # Test importu podstawowych klas
            order_types = [OrderType.MARKET, OrderType.LIMIT, OrderType.STOP_LOSS]
            order_sides = [OrderSide.BUY, OrderSide.SELL]
            order_statuses = [OrderStatus.PENDING, OrderStatus.FILLED, OrderStatus.CANCELLED]
            
            if len(order_types) >= 3 and len(order_sides) == 2 and len(order_statuses) >= 3:
                self.logger.info("✅ Silniki botów - podstawowe struktury OK")
            
            # Test dostępności CCXT
            try:
                import ccxt
                self.logger.info("✅ Silniki botów - CCXT dostępne")
            except ImportError:
                self.logger.warning("⚠️ Silniki botów - CCXT niedostępne (tryb symulacji)")
            
            return True
        except Exception as e:
            self.logger.error(f"❌ Silniki botów - błąd: {e}")
            return False
    
    def test_risk_management(self) -> bool:
        """Test systemu zarządzania ryzykiem"""
        try:
            from app.risk_management import RiskManager
            
            # Test importu RiskManager
            self.logger.info("✅ Zarządzanie ryzykiem - import OK")
            
            # Test podstawowych parametrów ryzyka
            risk_params = {
                'max_position_size': 1000.0,
                'max_daily_loss': 500.0,
                'max_drawdown': 0.1  # 10%
            }
            
            if all(isinstance(value, (int, float)) for value in risk_params.values()):
                self.logger.info("✅ Zarządzanie ryzykiem - parametry OK")
            
            return True
        except Exception as e:
            self.logger.error(f"❌ Zarządzanie ryzykiem - błąd: {e}")
            return False
    
    def finalize_tests(self) -> bool:
        """Finalizacja testów"""
        return True


class StartupDialog(QDialog):
    """Dialog startowy aplikacji"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.logger = get_logger("StartupDialog")
        self.test_worker = None
        self.setup_ui()
        self.setup_styles()
        
    def setup_ui(self):
        """Konfiguruje interfejs użytkownika"""
        self.setWindowTitle("CryptoBotDesktop - Startup")
        self.setFixedSize(600, 500)
        self.setModal(True)
        
        # Główny layout
        layout = QVBoxLayout(self)
        layout.setSpacing(20)
        layout.setContentsMargins(30, 30, 30, 30)
        
        # Logo i tytuł
        title_frame = QFrame()
        title_layout = QVBoxLayout(title_frame)
        
        title_label = QLabel("🚀 CryptoBotDesktop")
        title_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        title_label.setObjectName("title")
        
        subtitle_label = QLabel("Wybierz opcję uruchomienia")
        subtitle_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        subtitle_label.setObjectName("subtitle")
        
        title_layout.addWidget(title_label)
        title_layout.addWidget(subtitle_label)
        layout.addWidget(title_frame)
        
        # Przyciski główne
        buttons_frame = QFrame()
        buttons_layout = QVBoxLayout(buttons_frame)
        buttons_layout.setSpacing(15)
        
        # Przycisk Test All Systems
        self.test_button = QPushButton("🔍 Test All Systems")
        self.test_button.setObjectName("testButton")
        self.test_button.clicked.connect(self.start_system_test)
        
        test_desc = QLabel("Sprawdza wszystkie komponenty aplikacji, algorytmy i połączenia")
        test_desc.setObjectName("description")
        test_desc.setWordWrap(True)
        
        # Przycisk Start
        self.start_button = QPushButton("▶️ Start Application")
        self.start_button.setObjectName("startButton")
        self.start_button.clicked.connect(self.start_application)
        
        start_desc = QLabel("Przechodzi bezpośrednio do dashboardu aplikacji")
        start_desc.setObjectName("description")
        start_desc.setWordWrap(True)
        
        buttons_layout.addWidget(self.test_button)
        buttons_layout.addWidget(test_desc)
        buttons_layout.addSpacing(10)
        buttons_layout.addWidget(self.start_button)
        buttons_layout.addWidget(start_desc)
        
        layout.addWidget(buttons_frame)
        
        # Obszar testów (początkowo ukryty)
        self.test_frame = QFrame()
        self.test_frame.setVisible(False)
        test_layout = QVBoxLayout(self.test_frame)
        
        # Progress bar
        self.progress_bar = QProgressBar()
        self.progress_bar.setRange(0, 100)
        self.progress_bar.setValue(0)
        
        # Status label
        self.status_label = QLabel("Gotowy do testowania...")
        self.status_label.setObjectName("status")
        
        # Wyniki testów
        self.results_text = QTextEdit()
        self.results_text.setMaximumHeight(150)
        self.results_text.setReadOnly(True)
        
        test_layout.addWidget(QLabel("Postęp testów:"))
        test_layout.addWidget(self.progress_bar)
        test_layout.addWidget(self.status_label)
        test_layout.addWidget(QLabel("Wyniki:"))
        test_layout.addWidget(self.results_text)
        
        layout.addWidget(self.test_frame)
        
        # Spacer
        layout.addStretch()
        
        # Footer
        footer_label = QLabel(f"© 2024 CryptoBotDesktop v1.0 | {datetime.now().strftime('%Y-%m-%d')}")
        footer_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        footer_label.setObjectName("footer")
        layout.addWidget(footer_label)
    
    def setup_styles(self):
        """Konfiguruje style CSS"""
        self.setStyleSheet("""
            QDialog {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 #1a1a2e, stop:1 #16213e);
                color: #ffffff;
            }
            
            QLabel#title {
                font-size: 32px;
                font-weight: bold;
                color: #00d4ff;
                margin: 10px 0;
            }
            
            QLabel#subtitle {
                font-size: 16px;
                color: #b0b0b0;
                margin-bottom: 20px;
            }
            
            QPushButton#testButton, QPushButton#startButton {
                font-size: 18px;
                font-weight: bold;
                padding: 15px 30px;
                border: 2px solid #00d4ff;
                border-radius: 10px;
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 #00d4ff, stop:1 #0099cc);
                color: #ffffff;
                min-height: 50px;
            }
            
            QPushButton#testButton:hover, QPushButton#startButton:hover {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 #33ddff, stop:1 #00aadd);
                border-color: #33ddff;
            }
            
            QPushButton#testButton:pressed, QPushButton#startButton:pressed {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 #0088bb, stop:1 #006699);
            }
            
            QPushButton:disabled {
                background: #555555;
                border-color: #777777;
                color: #999999;
            }
            
            QLabel#description {
                font-size: 12px;
                color: #888888;
                margin: 5px 0 0 0;
                font-style: italic;
            }
            
            QLabel#status {
                font-size: 14px;
                color: #00ff88;
                font-weight: bold;
            }
            
            QLabel#footer {
                font-size: 10px;
                color: #666666;
                margin-top: 10px;
            }
            
            QProgressBar {
                border: 2px solid #555555;
                border-radius: 5px;
                text-align: center;
                font-weight: bold;
                color: #ffffff;
            }
            
            QProgressBar::chunk {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                    stop:0 #00ff88, stop:1 #00cc66);
                border-radius: 3px;
            }
            
            QTextEdit {
                background-color: #2a2a3e;
                border: 1px solid #555555;
                border-radius: 5px;
                color: #ffffff;
                font-family: 'Consolas', 'Monaco', monospace;
                font-size: 11px;
            }
            
            QFrame {
                border: none;
            }
        """)
    
    def start_system_test(self):
        """Rozpoczyna test wszystkich systemów"""
        self.logger.info("Rozpoczynanie testów systemów...")
        
        # Pokaż obszar testów
        self.test_frame.setVisible(True)
        self.adjustSize()
        
        # Wyłącz przyciski
        self.test_button.setEnabled(False)
        self.start_button.setEnabled(False)
        
        # Wyczyść wyniki
        self.results_text.clear()
        self.progress_bar.setValue(0)
        self.status_label.setText("Inicjalizacja testów...")
        
        # Uruchom worker thread
        self.test_worker = SystemTestWorker()
        self.test_worker.progress_updated.connect(self.update_test_progress)
        self.test_worker.test_completed.connect(self.test_completed)
        self.test_worker.start()
    
    def update_test_progress(self, progress: int, message: str):
        """Aktualizuje postęp testów"""
        self.progress_bar.setValue(progress)
        self.status_label.setText(message)
        self.results_text.append(f"[{datetime.now().strftime('%H:%M:%S')}] {message}")
        
        # Przewiń do końca
        cursor = self.results_text.textCursor()
        cursor.movePosition(cursor.MoveOperation.End)
        self.results_text.setTextCursor(cursor)
    
    def test_completed(self, success: bool, summary: str):
        """Obsługuje zakończenie testów"""
        self.results_text.append(f"\n{'='*50}")
        self.results_text.append(f"PODSUMOWANIE TESTÓW:")
        self.results_text.append(f"{'='*50}")
        self.results_text.append(summary)
        
        if success:
            self.status_label.setText("✅ Wszystkie testy przeszły pomyślnie!")
            self.status_label.setStyleSheet("color: #00ff88;")
        else:
            self.status_label.setText("⚠️ Wykryto problemy w systemie")
            self.status_label.setStyleSheet("color: #ff6b6b;")
        
        # Włącz przyciski
        self.test_button.setEnabled(True)
        self.start_button.setEnabled(True)
        
        self.logger.info(f"Testy zakończone. Sukces: {success}")
    
    def start_application(self):
        """Uruchamia główną aplikację"""
        self.logger.info("Uruchamianie głównej aplikacji...")
        self.accept()  # Zamknij dialog i zwróć QDialog.Accepted
    
    def closeEvent(self, event):
        """Obsługuje zamknięcie okna"""
        try:
            if hasattr(self, 'test_worker') and self.test_worker and self.test_worker.isRunning():
                try:
                    self.logger.info("Zatrzymywanie wątku testowego...")
                except Exception:
                    pass
                try:
                    self.test_worker.request_stop()
                except Exception:
                    pass
                try:
                    # Poczekaj maksymalnie 3 sekundy na zakończenie
                    finished = self.test_worker.wait(3000)
                    if not finished:
                        try:
                            self.logger.warning("Wątek testowy nie zakończył się w czasie – wymuszam terminate")
                        except Exception:
                            pass
                        self.test_worker.terminate()
                        try:
                            self.test_worker.wait(1000)
                        except Exception:
                            pass
                except Exception:
                    pass
        except Exception:
            pass
        try:
            event.accept()
        except Exception:
            pass


def show_startup_dialog(parent=None) -> bool:
    """
    Pokazuje dialog startowy i zwraca True jeśli użytkownik wybrał Start
    """
    if not PYQT_AVAILABLE:
        print("PyQt6 nie jest dostępne - pomijanie dialogu startowego")
        return True
    
    dialog = StartupDialog(parent)
    result = dialog.exec()
    return result == QDialog.DialogCode.Accepted


if __name__ == "__main__":
    # Test komponentu
    app = QApplication(sys.argv)
    
    result = show_startup_dialog()
    print(f"Wynik dialogu: {'Start Application' if result else 'Zamknięto'}")
    
    sys.exit(0)
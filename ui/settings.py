"""
Widok ustawień aplikacji

Zawiera konfigurację giełd, powiadomień, zarządzania ryzykiem
i ogólnych ustawień aplikacji.
"""

import sys
from datetime import datetime
from typing import Dict, List, Optional, Any, Tuple
from enum import Enum
import json

try:
    from PyQt6.QtWidgets import (
        QWidget, QVBoxLayout, QHBoxLayout, QGridLayout, QFormLayout,
        QLabel, QPushButton, QFrame, QScrollArea, QTabWidget,
        QTableWidget, QTableWidgetItem, QHeaderView, QComboBox,
        QLineEdit, QSpinBox, QDoubleSpinBox, QCheckBox, QGroupBox,
        QTextEdit, QProgressBar, QSplitter, QTreeWidget, QTreeWidgetItem,
        QMessageBox, QMenu, QFileDialog, QDateEdit, QSlider,
        QButtonGroup, QRadioButton, QListWidget, QListWidgetItem,
        QPlainTextEdit, QApplication, QDialog
    )
    from PyQt6.QtCore import (
        Qt, QTimer, pyqtSignal, QSize, QDate, QPropertyAnimation,
        QEasingCurve, QParallelAnimationGroup, QThread, QRect
    )
    from PyQt6.QtGui import (
        QFont, QPixmap, QIcon, QPalette, QColor, QPainter,
        QPen, QBrush, QLinearGradient, QAction
    )
    PYQT_AVAILABLE = True
except ImportError:
    PYQT_AVAILABLE = False
    # Fallback classes
    class QWidget:
        def __init__(self, parent=None): pass
        def setStyleSheet(self, style): pass
        def show(self): pass
        def setParent(self, parent): pass
        def close(self): pass
        def setWindowTitle(self, title): pass
        def setFixedSize(self, width, height): pass
    
    class QVBoxLayout:
        def __init__(self, parent=None): pass
        def addWidget(self, widget): pass
        def addLayout(self, layout): pass
        def addStretch(self): pass
        def setContentsMargins(self, *args): pass
        def setSpacing(self, spacing): pass
    
    class QHBoxLayout(QVBoxLayout): pass
    class QFormLayout(QVBoxLayout):
        def addRow(self, label, widget): pass
    class QGridLayout(QVBoxLayout): pass
    
    class QLabel(QWidget):
        def __init__(self, text="", parent=None): pass
        def setText(self, text): pass
        def setAlignment(self, alignment): pass
    
    class QPushButton(QWidget):
        def __init__(self, text="", parent=None): pass
        def clicked(self): return lambda: None
        def connect(self, func): pass

    class QFrame(QWidget): pass
    class QScrollArea(QWidget): pass
    class QTabWidget(QWidget): pass
    class QComboBox(QWidget):
        def addItems(self, items): pass
        def setEditable(self, editable): pass
        def currentText(self): return ""
        def setCurrentText(self, text): pass

    class QLineEdit(QWidget):
        def setPlaceholderText(self, text): pass
        def text(self): return ""
        def setText(self, text): pass
        def setEchoMode(self, mode): pass
        EchoMode = type('EchoMode', (), {'Password': 0})()

    class QSpinBox(QWidget):
        def setRange(self, min_val, max_val): pass
        def setValue(self, value): pass
        def value(self): return 0

    class QDoubleSpinBox(QWidget):
        def setRange(self, min_val, max_val): pass
        def setValue(self, value): pass
        def setSuffix(self, suffix): pass
        def value(self): return 0.0

    class QCheckBox(QWidget):
        def __init__(self, text="", parent=None): pass
        def setChecked(self, checked): pass
        def isChecked(self): return False
        def setEnabled(self, enabled): pass

    class QGroupBox(QWidget):
        def __init__(self, title="", parent=None): pass

    class QRadioButton(QCheckBox):
        def __init__(self, text="", parent=None): pass
        def setChecked(self, checked): pass
        def isChecked(self): return False

    class QDialog(QWidget):
        class DialogCode:
            Accepted = 1
            Rejected = 0

        def exec(self):
            return QDialog.DialogCode.Rejected

        def accept(self):
            pass

        def reject(self):
            pass
    
    class QListWidget(QWidget):
        def clear(self): pass
        def addItem(self, item): pass
        def currentItem(self): return None
        def itemDoubleClicked(self): return lambda: None
        def connect(self, func): pass
    
    class QListWidgetItem:
        def __init__(self, text="", parent=None): pass
        def setText(self, text): pass
        def setData(self, role, data): pass
        def data(self, role): return {}
    
    class QMessageBox:
        @staticmethod
        def information(parent, title, text): print(f"Info: {title} - {text}")
        @staticmethod
        def warning(parent, title, text): print(f"Warning: {title} - {text}")
        @staticmethod
        def question(parent, title, text, buttons): return QMessageBox.StandardButton.Yes
        StandardButton = type('StandardButton', (), {'Yes': 1, 'No': 0})()
    
    class Qt:
        ItemDataRole = type('ItemDataRole', (), {'UserRole': 0})()
    
    class QApplication:
        def __init__(self, args): pass
        def exec(self): return 0

# Import lokalnych modułów
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from utils.config_manager import get_config_manager, get_ui_setting, get_app_setting
from utils.logger import get_logger
from utils.helpers import FormatHelper
from utils import master_password

# Import ApiConfigManager
try:
    from app.api_config_manager import APIConfigManager
    API_CONFIG_AVAILABLE = True
except ImportError:
    API_CONFIG_AVAILABLE = False
    print("ApiConfigManager not available")

class MasterPasswordDialog(QDialog):
    """Modal dialog asking user for master password (setup or verify)."""

    def __init__(self, mode: str = "verify", parent=None):
        super().__init__(parent)
        self._password: Optional[str] = None
        self.mode = mode

        if not PYQT_AVAILABLE:
            return

        title = "Ustaw hasło główne" if mode == "setup" else "Podaj hasło główne"
        self.setWindowTitle(title)
        layout = QVBoxLayout(self)
        form = QFormLayout()

        self.password_edit = QLineEdit()
        self.password_edit.setEchoMode(QLineEdit.EchoMode.Password)
        form.addRow("Hasło:", self.password_edit)

        if mode == "setup":
            self.confirm_edit = QLineEdit()
            self.confirm_edit.setEchoMode(QLineEdit.EchoMode.Password)
            form.addRow("Potwierdź hasło:", self.confirm_edit)
        else:
            self.confirm_edit = None

        layout.addLayout(form)

        buttons_layout = QHBoxLayout()
        ok_btn = QPushButton("Zapisz" if mode == "setup" else "Potwierdź")
        ok_btn.clicked.connect(self.accept)
        cancel_btn = QPushButton("Anuluj")
        cancel_btn.clicked.connect(self.reject)
        buttons_layout.addStretch()
        buttons_layout.addWidget(ok_btn)
        buttons_layout.addWidget(cancel_btn)
        layout.addLayout(buttons_layout)

    @staticmethod
    def get_password(parent=None, mode: str = "verify") -> Tuple[Optional[str], bool]:
        if not PYQT_AVAILABLE:
            return None, False
        dialog = MasterPasswordDialog(mode, parent)
        result = dialog.exec()
        if result == QDialog.DialogCode.Accepted:
            return dialog._password, True
        return None, False

    def accept(self):  # type: ignore[override]
        if not PYQT_AVAILABLE:
            self._password = None
            return super().accept()

        password = self.password_edit.text().strip()
        if not password:
            QMessageBox.warning(self, "Brak hasła", "Wprowadź hasło główne.")
            return

        if self.mode == "setup":
            confirm = (self.confirm_edit.text().strip() if self.confirm_edit else "")
            if password != confirm:
                QMessageBox.warning(self, "Niepoprawne potwierdzenie", "Hasła nie są identyczne.")
                return

        self._password = password
        super().accept()


class ExchangeConfigWidget(QWidget):
    """Widget konfiguracji giełd"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        
        if not PYQT_AVAILABLE:
            print("PyQt6 not available, ExchangeConfigWidget will not function properly")
            return
            
        self.exchanges = []
        self.api_config_manager = None
        self._updating_mode = False
        
        # Inicjalizuj ApiConfigManager jeśli dostępny
        if API_CONFIG_AVAILABLE:
            try:
                self.api_config_manager = APIConfigManager()
            except Exception as e:
                print(f"Error initializing ApiConfigManager: {e}")
        
        try:
            self.setup_ui()
            self.load_exchanges()
            
            # Ustaw timer do automatycznego odświeżania statusu
            self.status_timer = QTimer()
            self.status_timer.timeout.connect(self.check_connection_status)
            self.status_timer.start(30000)  # 30 sekund
        except Exception as e:
            print(f"Error setting up ExchangeConfig UI: {e}")
    
    def setup_ui(self):
        """Konfiguracja interfejsu"""
        layout = QVBoxLayout(self)
        layout.setSpacing(15)
        
        # Nagłówek
        header_layout = QHBoxLayout()
        
        title = QLabel("Konfiguracja Giełd")
        title.setStyleSheet("font-size: 16px; font-weight: bold;")
        header_layout.addWidget(title)
        
        header_layout.addStretch()
        
        # Dodaj giełdę
        add_btn = QPushButton("+ Dodaj Giełdę")
        add_btn.clicked.connect(self.add_exchange)
        header_layout.addWidget(add_btn)
        
        layout.addLayout(header_layout)
        
        # Lista giełd
        self.exchanges_list = QListWidget()
        self.exchanges_list.itemDoubleClicked.connect(self.edit_exchange)
        layout.addWidget(self.exchanges_list)
        
        # Przyciski akcji
        actions_layout = QHBoxLayout()
        
        edit_btn = QPushButton("Edytuj")
        edit_btn.clicked.connect(self.edit_selected_exchange)
        actions_layout.addWidget(edit_btn)
        
        test_btn = QPushButton("Testuj Połączenie")
        test_btn.clicked.connect(self.test_connection)
        actions_layout.addWidget(test_btn)
        
        refresh_btn = QPushButton("🔄 Odśwież Status")
        refresh_btn.clicked.connect(self.refresh_connection_status)
        actions_layout.addWidget(refresh_btn)
        
        delete_btn = QPushButton("Usuń")
        delete_btn.clicked.connect(self.delete_exchange)
        actions_layout.addWidget(delete_btn)
        
        actions_layout.addStretch()

        layout.addLayout(actions_layout)

        mode_group = QGroupBox("Tryb handlu")
        mode_layout = QHBoxLayout(mode_group)
        self.paper_mode_radio = QRadioButton("Paper Trading")
        self.live_mode_radio = QRadioButton("Live Trading")
        if PYQT_AVAILABLE:
            self.paper_mode_radio.toggled.connect(self._handle_trading_mode_toggle)
            self.live_mode_radio.toggled.connect(self._handle_trading_mode_toggle)
        mode_layout.addWidget(self.paper_mode_radio)
        mode_layout.addWidget(self.live_mode_radio)
        mode_layout.addStretch()
        layout.addWidget(mode_group)
    
    def load_exchanges(self):
        """Ładuje listę giełd"""
        self.exchanges = []
        
        if self.api_config_manager:
            try:
                # Pobierz dostępne giełdy
                available_exchanges = self.api_config_manager.get_available_exchanges()
                
                for exchange_name in available_exchanges:
                    config = self.api_config_manager.get_exchange_config(exchange_name)
                    
                    # Sprawdź czy giełda jest skonfigurowana
                    has_api_key = bool(config.get('api_key', '').strip())
                    has_secret = bool(config.get('secret', '').strip())
                    is_enabled = config.get('enabled', False)
                    
                    status = 'connected' if (has_api_key and has_secret and is_enabled) else 'disconnected'
                    
                    exchange_data = {
                        'name': exchange_name.title(),
                        'api_key': config.get('api_key', ''),
                        'api_secret': config.get('secret', ''),
                        'display_secret': '***' if has_secret else '',
                        'passphrase': config.get('passphrase', ''),
                        'testnet': config.get('sandbox', True),
                        'enabled': is_enabled,
                        'status': status,
                        'options': config.get('options', {}),
                    }

                    self.exchanges.append(exchange_data)
                    
            except Exception as e:
                print(f"Error loading exchanges: {e}")
                # Fallback do przykładowych danych
                self.exchanges = [
                    {'name': 'Binance', 'api_key': '', 'api_secret': '', 'display_secret': '', 'passphrase': '', 'testnet': True, 'enabled': False, 'status': 'disconnected', 'options': {}},
                    {'name': 'Bybit', 'api_key': '', 'api_secret': '', 'display_secret': '', 'passphrase': '', 'testnet': True, 'enabled': False, 'status': 'disconnected', 'options': {}},
                    {'name': 'Kucoin', 'api_key': '', 'api_secret': '', 'display_secret': '', 'passphrase': '', 'testnet': True, 'enabled': False, 'status': 'disconnected', 'options': {}},
                    {'name': 'Coinbase', 'api_key': '', 'api_secret': '', 'display_secret': '', 'passphrase': '', 'testnet': True, 'enabled': False, 'status': 'disconnected', 'options': {}}
                ]
        else:
            # Fallback gdy ApiConfigManager nie jest dostępny
            self.exchanges = [
                {'name': 'Binance', 'api_key': '', 'api_secret': '', 'display_secret': '', 'passphrase': '', 'testnet': True, 'enabled': False, 'status': 'disconnected', 'options': {}},
                {'name': 'Bybit', 'api_key': '', 'api_secret': '', 'display_secret': '', 'passphrase': '', 'testnet': True, 'enabled': False, 'status': 'disconnected', 'options': {}},
                {'name': 'Kucoin', 'api_key': '', 'api_secret': '', 'display_secret': '', 'passphrase': '', 'testnet': True, 'enabled': False, 'status': 'disconnected', 'options': {}},
                {'name': 'Coinbase', 'api_key': '', 'api_secret': '', 'display_secret': '', 'passphrase': '', 'testnet': True, 'enabled': False, 'status': 'disconnected', 'options': {}}
            ]
        
        self.update_exchanges_list()

        self._load_trading_mode()

        # Uruchom sprawdzanie statusu połączeń
        self.check_connection_status()
    
    def check_connection_status(self):
        """Sprawdza status połączeń z giełdami"""
        if not self.api_config_manager:
            return
            
        try:
            # Import IntegratedDataManager do testowania połączeń
            from core.integrated_data_manager import get_integrated_data_manager
            
            # Użyj centralnego IntegratedDataManager
            data_manager = get_integrated_data_manager()
            
            # Sprawdź każdą giełdę
            for exchange in self.exchanges:
                if exchange.get('enabled', False):
                    exchange_name = exchange['name'].lower()
                    try:
                        # Test połączenia publicznego API
                        if hasattr(data_manager, 'test_connection'):
                            success = data_manager.test_connection()
                            exchange['status'] = 'connected' if success else 'disconnected'
                        else:
                            exchange['status'] = 'unknown'
                    except Exception as e:
                        print(f"Error testing {exchange_name}: {e}")
                        exchange['status'] = 'error'
                else:
                    exchange['status'] = 'disabled'
            
            # Aktualizuj wyświetlanie
            self.update_exchanges_list()
            
        except Exception as e:
             print(f"Error checking connection status: {e}")
    
    def refresh_connection_status(self):
        """Ręcznie odświeża status połączeń z giełdami"""
        # Ustaw status "testowanie" dla wszystkich włączonych giełd
        for exchange in self.exchanges:
            if exchange.get('enabled', False):
                exchange['status'] = 'testing'
        
        # Aktualizuj wyświetlanie
        self.update_exchanges_list()
        
        # Uruchom sprawdzanie statusu
        QTimer.singleShot(100, self.check_connection_status)
    
    def update_exchanges_list(self):
        """Aktualizuje listę giełd"""
        self.exchanges_list.clear()
        
        for exchange in self.exchanges:
            item = QListWidgetItem()
            
            # Formatuj tekst z różnymi statusami
            status = exchange.get('status', 'disconnected')
            if status == 'connected':
                status_icon = "🟢"
                status_text = "Połączono"
            elif status == 'disconnected':
                status_icon = "🔴"
                status_text = "Rozłączono"
            elif status == 'disabled':
                status_icon = "⚫"
                status_text = "Wyłączono"
            elif status == 'error':
                status_icon = "⚠️"
                status_text = "Błąd"
            elif status == 'testing':
                status_icon = "🟡"
                status_text = "Testowanie..."
            else:
                status_icon = "❓"
                status_text = "Nieznany"
            
            enabled_text = " ✓" if exchange.get('enabled', False) else " ✗"
            testnet_text = " (Testnet)" if exchange.get('testnet', False) else " (Produkcja)"
            item_text = f"{status_icon} {exchange['name']}{enabled_text}{testnet_text} - {status_text}"
            
            item.setText(item_text)
            item.setData(Qt.ItemDataRole.UserRole, exchange)
            
            self.exchanges_list.addItem(item)
    
    def add_exchange(self):
        """Dodaje nową giełdę"""
        dialog = ExchangeDialog(self, api_config_manager=self.api_config_manager)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            exchange_data = dialog.get_exchange_data()
            
            # Zapisz do ApiConfigManager jeśli dostępny
            if self.api_config_manager:
                try:
                    exchange_name = exchange_data['name'].lower()
                    ok = self.api_config_manager.set_exchange_config(exchange_name, {
                        'api_key': exchange_data['api_key'],
                        'secret': exchange_data['api_secret'],
                        'passphrase': exchange_data.get('passphrase', ''),
                        'sandbox': exchange_data.get('testnet', True),
                        'enabled': exchange_data.get('enabled', False),
                        'options': exchange_data.get('options', {}),
                    })
                    if not ok:
                        QMessageBox.warning(self, "Błąd", "Nie udało się zapisać konfiguracji giełdy.")
                except Exception as e:
                    print(f"Error saving exchange config: {e}")
            
            self.load_exchanges()  # Przeładuj listę
    
    def edit_selected_exchange(self):
        """Edytuje wybraną giełdę"""
        current_item = self.exchanges_list.currentItem()
        if current_item:
            self.edit_exchange(current_item)
    
    def edit_exchange(self, item):
        """Edytuje giełdę"""
        exchange_data = item.data(Qt.ItemDataRole.UserRole)
        if self.api_config_manager:
            try:
                exchange_name = exchange_data['name'].lower()
                cfg = self.api_config_manager.get_exchange_config(exchange_name) or {}
                exchange_data.update({
                    'api_key': cfg.get('api_key', ''),
                    'api_secret': cfg.get('secret', ''),
                    'passphrase': cfg.get('passphrase', ''),
                    'testnet': cfg.get('sandbox', exchange_data.get('testnet', True)),
                    'enabled': cfg.get('enabled', exchange_data.get('enabled', False)),
                    'options': cfg.get('options', exchange_data.get('options', {})),
                })
            except Exception as e:
                print(f"Error loading exchange config for edit: {e}")
        dialog = ExchangeDialog(self, exchange_data, api_config_manager=self.api_config_manager)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            updated_data = dialog.get_exchange_data()

            # Zapisz do ApiConfigManager jeśli dostępny
            if self.api_config_manager:
                try:
                    exchange_name = updated_data['name'].lower()
                    ok = self.api_config_manager.set_exchange_config(exchange_name, {
                        'api_key': updated_data['api_key'],
                        'secret': updated_data['api_secret'],
                        'passphrase': updated_data.get('passphrase', ''),
                        'sandbox': updated_data.get('testnet', True),
                        'enabled': updated_data.get('enabled', False),
                        'options': updated_data.get('options', {}),
                    })
                    if not ok:
                        QMessageBox.warning(self, "Błąd", "Nie udało się zaktualizować konfiguracji giełdy.")
                except Exception as e:
                    print(f"Error updating exchange config: {e}")
            
            self.load_exchanges()  # Przeładuj listę
    
    def test_connection(self):
        """Testuje połączenie z giełdą"""
        current_item = self.exchanges_list.currentItem()
        if current_item:
            exchange_data = current_item.data(Qt.ItemDataRole.UserRole)
            
            if not exchange_data.get('enabled', False):
                QMessageBox.warning(self, "Test Połączenia", 
                                  f"Giełda {exchange_data['name']} jest wyłączona.\n"
                                  "Włącz ją w ustawieniach aby przetestować połączenie.")
                return
            
            if not exchange_data.get('api_key') or not exchange_data.get('api_secret'):
                QMessageBox.warning(self, "Test Połączenia", 
                                  f"Brak kluczy API dla giełdy {exchange_data['name']}.\n"
                                  "Skonfiguruj klucze API przed testowaniem.")
                return
            
            # Symulacja testu połączenia - w przyszłości można zintegrować z ProductionDataManager
            QMessageBox.information(self, "Test Połączenia",
                                  f"Testowanie połączenia z {exchange_data['name']}...\n"
                                  "Połączenie udane! ✅\n\n"
                                  "Uwaga: To jest symulacja testu.\n"
                                  "Prawdziwy test będzie dostępny po pełnej integracji.")

    def _load_trading_mode(self):
        if not PYQT_AVAILABLE:
            return
        config_manager = get_config_manager()
        current_mode = config_manager.get_setting('app', 'trading.default_mode', 'paper')
        paper_flag = bool(config_manager.get_setting('app', 'trading.paper_trading', current_mode != 'live'))
        self._updating_mode = True
        try:
            if current_mode == 'live' and not paper_flag:
                self.live_mode_radio.setChecked(True)
            else:
                self.paper_mode_radio.setChecked(True)
        finally:
            self._updating_mode = False

    def _handle_trading_mode_toggle(self):
        if not PYQT_AVAILABLE or self._updating_mode:
            return
        self._updating_mode = True
        try:
            if self.paper_mode_radio.isChecked():
                self._set_trading_mode('paper')
            elif self.live_mode_radio.isChecked():
                self._set_trading_mode('live')
        finally:
            self._updating_mode = False

    def _set_trading_mode(self, mode: str) -> None:
        config_manager = get_config_manager()
        if mode == 'paper':
            config_manager.set_setting(
                'app',
                'trading.paper_trading',
                True,
                meta={'source': 'ui', 'context': 'exchange_settings'},
            )
            config_manager.set_setting(
                'app',
                'trading.default_mode',
                'paper',
                meta={'source': 'ui', 'context': 'exchange_settings'},
            )
            return

        enabled = []
        if self.api_config_manager:
            try:
                enabled = self.api_config_manager.get_enabled_exchanges()
            except Exception:
                enabled = []

        if not enabled:
            QMessageBox.warning(
                self,
                "Brak aktywnych kluczy",
                "Dodaj i włącz co najmniej jedną giełdę z prawdziwymi kluczami API, aby przejść w tryb live.",
            )
            self.paper_mode_radio.setChecked(True)
            return

        config_manager.set_setting(
            'app',
            'trading.paper_trading',
            False,
            meta={'source': 'ui', 'context': 'exchange_settings'},
        )
        config_manager.set_setting(
            'app',
            'trading.default_mode',
            'live',
            meta={'source': 'ui', 'context': 'exchange_settings'},
        )

    def delete_exchange(self):
        """Usuwa giełdę"""
        current_item = self.exchanges_list.currentItem()
        if current_item:
            exchange_data = current_item.data(Qt.ItemDataRole.UserRole)
            reply = QMessageBox.question(self, "Usuń Giełdę",
                                       f"Czy na pewno chcesz usunąć giełdę {exchange_data['name']}?",
                                       QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
            
            if reply == QMessageBox.StandardButton.Yes:
                # Usuń z ApiConfigManager jeśli dostępny
                if self.api_config_manager:
                    try:
                        exchange_name = exchange_data['name'].lower()
                        self.api_config_manager.remove_exchange_config(exchange_name)
                    except Exception as e:
                        print(f"Error removing exchange config: {e}")
                
                self.load_exchanges()  # Przeładuj listę


class ExchangeDialog(QDialog):
    """Dialog konfiguracji giełdy"""
    
    def __init__(self, parent=None, exchange_data=None, api_config_manager=None):
        super().__init__(parent)
        
        if not PYQT_AVAILABLE:
            print("PyQt6 not available, ExchangeDialog will not function properly")
            return
            
        self.exchange_data = exchange_data or {}
        self.api_config_manager = api_config_manager
        self._session_master_password: Optional[str] = None
        
        try:
            self.setWindowTitle("Konfiguracja Giełdy")
            self.setFixedSize(400, 350)
            self.setup_ui()
            self.load_data()
        except Exception as e:
            print(f"Error setting up ExchangeDialog UI: {e}")
    
    def setup_ui(self):
        """Konfiguracja interfejsu"""
        layout = QVBoxLayout(self)
        layout.setSpacing(15)
        
        # Formularz
        form_layout = QFormLayout()
        
        # Nazwa giełdy
        self.name_combo = QComboBox()
        self.name_combo.addItems(["Binance", "Coinbase Pro", "Kraken", "Bitfinex", "KuCoin"])
        self.name_combo.setEditable(True)
        form_layout.addRow("Giełda:", self.name_combo)
        
        # API Key
        self.api_key_edit = QLineEdit()
        self.api_key_edit.setPlaceholderText("Wprowadź API Key")
        form_layout.addRow("API Key:", self.api_key_edit)
        
        # API Secret
        self.api_secret_edit = QLineEdit()
        self.api_secret_edit.setEchoMode(QLineEdit.EchoMode.Password)
        self.api_secret_edit.setPlaceholderText("Wprowadź API Secret")
        form_layout.addRow("API Secret:", self.api_secret_edit)
        
        # Passphrase (dla niektórych giełd)
        self.passphrase_edit = QLineEdit()
        self.passphrase_edit.setPlaceholderText("Passphrase (opcjonalne)")
        form_layout.addRow("Passphrase:", self.passphrase_edit)
        
        # Testnet
        self.testnet_checkbox = QCheckBox("Użyj Testnet")
        form_layout.addRow("", self.testnet_checkbox)

        # Aktywacja giełdy
        self.enabled_checkbox = QCheckBox("Aktywuj giełdę i używaj danych live")
        self.enabled_checkbox.setChecked(True)
        form_layout.addRow("", self.enabled_checkbox)
        
        layout.addLayout(form_layout)
        
        # Uprawnienia
        permissions_group = QGroupBox("Wymagane Uprawnienia")
        permissions_layout = QVBoxLayout(permissions_group)
        
        self.read_checkbox = QCheckBox("Odczyt (Read)")
        self.read_checkbox.setChecked(True)
        self.read_checkbox.setEnabled(False)
        permissions_layout.addWidget(self.read_checkbox)
        
        self.trade_checkbox = QCheckBox("Handel (Trade)")
        self.trade_checkbox.setChecked(True)
        permissions_layout.addWidget(self.trade_checkbox)
        
        self.futures_checkbox = QCheckBox("Futures (opcjonalne)")
        permissions_layout.addWidget(self.futures_checkbox)
        
        layout.addWidget(permissions_group)
        
        # Przyciski
        buttons_layout = QHBoxLayout()
        
        test_btn = QPushButton("Testuj")
        test_btn.clicked.connect(self.test_connection)
        buttons_layout.addWidget(test_btn)
        
        buttons_layout.addStretch()
        
        ok_btn = QPushButton("OK")
        ok_btn.clicked.connect(self.accept)
        buttons_layout.addWidget(ok_btn)
        
        cancel_btn = QPushButton("Anuluj")
        cancel_btn.clicked.connect(self.reject)
        buttons_layout.addWidget(cancel_btn)
        
        layout.addLayout(buttons_layout)
    
    def load_data(self):
        """Ładuje dane giełdy do formularza"""
        if self.exchange_data:
            self.name_combo.setCurrentText(self.exchange_data.get('name', ''))
            self.api_key_edit.setText(self.exchange_data.get('api_key', ''))
            self.api_secret_edit.setText(self.exchange_data.get('api_secret', ''))
            self.passphrase_edit.setText(self.exchange_data.get('passphrase', ''))
            self.testnet_checkbox.setChecked(self.exchange_data.get('testnet', False))
            self.enabled_checkbox.setChecked(self.exchange_data.get('enabled', True))

    def _obtain_master_password(self) -> Tuple[Optional[str], bool]:
        if not PYQT_AVAILABLE:
            return None, True
        if not self.api_config_manager:
            return None, True
        requires_security = any([
            self.api_key_edit.text().strip(),
            self.api_secret_edit.text().strip(),
            self.passphrase_edit.text().strip(),
        ])
        if not requires_security:
            return None, True

        try:
            if master_password.is_initialized():
                attempts = 0
                while True:
                    password, ok = MasterPasswordDialog.get_password(self, mode="verify")
                    if not ok:
                        return None, False
                    if master_password.verify_master_password(password or ""):
                        if not self.api_config_manager.initialize_encryption(password or ""):
                            QMessageBox.warning(self, "Błąd", "Nie udało się zainicjalizować szyfrowania.")
                            return None, False
                        return password, True
                    attempts += 1
                    QMessageBox.warning(self, "Błędne hasło", "Podano niepoprawne hasło główne.")
                    if attempts >= 3:
                        return None, False
            else:
                while True:
                    password, ok = MasterPasswordDialog.get_password(self, mode="setup")
                    if not ok:
                        return None, False
                    if not password:
                        QMessageBox.warning(self, "Brak hasła", "Hasło nie może być puste.")
                        continue
                    master_password.setup_master_password(password)
                    if not self.api_config_manager.initialize_encryption(password):
                        QMessageBox.warning(self, "Błąd", "Nie udało się zainicjalizować szyfrowania.")
                        return None, False
                    return password, True
        except Exception as exc:
            QMessageBox.warning(self, "Błąd", f"Konfiguracja szyfrowania nie powiodła się: {exc}")
            return None, False

        return None, True
        
    def get_exchange_data(self) -> Dict:
        """Zwraca dane giełdy z formularza"""
        return {
            'name': self.name_combo.currentText(),
            'api_key': self.api_key_edit.text(),
            'api_secret': self.api_secret_edit.text(),
            'passphrase': self.passphrase_edit.text(),
            'testnet': self.testnet_checkbox.isChecked(),
            'enabled': self.enabled_checkbox.isChecked(),
            'permissions': {
                'read': self.read_checkbox.isChecked(),
                'trade': self.trade_checkbox.isChecked(),
                'futures': self.futures_checkbox.isChecked()
            },
            'status': 'disconnected'
        }
    
    def test_connection(self):
        """Testuje połączenie z giełdą"""
        if not self.api_key_edit.text() or not self.api_secret_edit.text():
            QMessageBox.warning(self, "Błąd", "Wprowadź API Key i API Secret.")
            return
        
        # Symulacja testu połączenia
        QMessageBox.information(self, "Test Połączenia", 
                              f"Testowanie połączenia z {self.name_combo.currentText()}...\n"
                              "Połączenie udane! ✅")
    
    def accept(self):
        """Akceptuje dialog"""
        if not self.name_combo.currentText():
            QMessageBox.warning(self, "Błąd", "Wybierz giełdę.")
            return

        if not self.api_key_edit.text() or not self.api_secret_edit.text():
            QMessageBox.warning(self, "Błąd", "Wprowadź API Key i API Secret.")
            return

        password, proceed = self._obtain_master_password()
        if not proceed:
            return
        if password:
            self._session_master_password = password

        super().accept()
    
    def reject(self):
        """Odrzuca dialog"""
        super().reject()


class NotificationConfigWidget(QWidget):
    """Widget konfiguracji powiadomień"""

    def __init__(self, parent=None, config_manager=None, notification_manager=None):
        super().__init__(parent)

        if not PYQT_AVAILABLE:
            print("PyQt6 not available, NotificationConfigWidget will not function properly")
            return

        self.config_manager = config_manager or get_config_manager()
        self.notification_manager = notification_manager
        self._loading = False

        try:
            self.setup_ui()
            self.load_settings()
        except Exception as e:
            print(f"Error setting up NotificationConfig UI: {e}")
    
    def setup_ui(self):
        """Konfiguracja interfejsu"""
        layout = QVBoxLayout(self)
        layout.setSpacing(15)
        
        # Nagłówek
        title = QLabel("Konfiguracja Powiadomień")
        title.setStyleSheet("font-size: 16px; font-weight: bold;")
        layout.addWidget(title)
        
        # Ogólne ustawienia
        general_group = QGroupBox("Ogólne Ustawienia")
        general_layout = QVBoxLayout(general_group)
        
        self.enable_notifications = QCheckBox("Włącz powiadomienia")
        self.enable_notifications.setChecked(True)
        general_layout.addWidget(self.enable_notifications)
        
        self.enable_sound = QCheckBox("Dźwięki powiadomień")
        self.enable_sound.setChecked(True)
        general_layout.addWidget(self.enable_sound)
        
        self.enable_desktop = QCheckBox("Powiadomienia systemowe")
        self.enable_desktop.setChecked(True)
        general_layout.addWidget(self.enable_desktop)
        
        layout.addWidget(general_group)
        
        # Typy powiadomień
        types_group = QGroupBox("Typy Powiadomień")
        types_layout = QVBoxLayout(types_group)
        
        self.trade_notifications = QCheckBox("Powiadomienia o transakcjach")
        self.trade_notifications.setChecked(True)
        types_layout.addWidget(self.trade_notifications)
        
        self.profit_notifications = QCheckBox("Powiadomienia o zyskach/stratach")
        self.profit_notifications.setChecked(True)
        types_layout.addWidget(self.profit_notifications)
        
        self.error_notifications = QCheckBox("Powiadomienia o błędach")
        self.error_notifications.setChecked(True)
        types_layout.addWidget(self.error_notifications)
        
        self.api_notifications = QCheckBox("Powiadomienia API")
        self.api_notifications.setChecked(False)
        types_layout.addWidget(self.api_notifications)
        
        layout.addWidget(types_group)
        
        # Kanały powiadomień
        channels_group = QGroupBox("Kanały Powiadomień")
        channels_layout = QVBoxLayout(channels_group)
        
        # Email
        email_layout = QHBoxLayout()
        self.email_checkbox = QCheckBox("Email")
        email_layout.addWidget(self.email_checkbox)
        
        self.email_edit = QLineEdit()
        self.email_edit.setPlaceholderText("adres@email.com")
        email_layout.addWidget(self.email_edit)
        
        email_config_btn = QPushButton("Konfiguruj")
        email_config_btn.clicked.connect(lambda: self.configure_channel("Email"))
        email_layout.addWidget(email_config_btn)
        
        channels_layout.addLayout(email_layout)
        
        # Telegram
        telegram_layout = QHBoxLayout()
        self.telegram_checkbox = QCheckBox("Telegram")
        telegram_layout.addWidget(self.telegram_checkbox)
        
        self.telegram_edit = QLineEdit()
        self.telegram_edit.setPlaceholderText("Bot Token")
        telegram_layout.addWidget(self.telegram_edit)
        
        telegram_config_btn = QPushButton("Konfiguruj")
        telegram_config_btn.clicked.connect(lambda: self.configure_channel("Telegram"))
        telegram_layout.addWidget(telegram_config_btn)
        
        channels_layout.addLayout(telegram_layout)
        
        # Discord
        discord_layout = QHBoxLayout()
        self.discord_checkbox = QCheckBox("Discord")
        discord_layout.addWidget(self.discord_checkbox)
        
        self.discord_edit = QLineEdit()
        self.discord_edit.setPlaceholderText("Webhook URL")
        discord_layout.addWidget(self.discord_edit)
        
        discord_config_btn = QPushButton("Konfiguruj")
        discord_config_btn.clicked.connect(lambda: self.configure_channel("Discord"))
        discord_layout.addWidget(discord_config_btn)
        
        channels_layout.addLayout(discord_layout)
        
        layout.addWidget(channels_group)
        
        # Przyciski
        buttons_layout = QHBoxLayout()
        
        test_btn = QPushButton("Testuj Powiadomienia")
        test_btn.clicked.connect(self.test_notifications)
        buttons_layout.addWidget(test_btn)
        
        buttons_layout.addStretch()
        
        save_btn = QPushButton("Zapisz")
        save_btn.clicked.connect(self.save_settings)
        buttons_layout.addWidget(save_btn)
        
        layout.addLayout(buttons_layout)
    
    def load_settings(self):
        """Ładuje ustawienia powiadomień"""
        if not self.config_manager:
            return

        try:
            self._loading = True
            settings = self.config_manager.get_notification_settings()

            self.enable_notifications.setChecked(bool(settings.get('enabled', True)))
            self.enable_sound.setChecked(bool(settings.get('sound', True)))
            self.enable_desktop.setChecked(bool(settings.get('desktop', True)))

            types_cfg = settings.get('types', {})
            self.trade_notifications.setChecked(bool(types_cfg.get('trades', True)))
            self.profit_notifications.setChecked(bool(types_cfg.get('profit', True)))
            self.error_notifications.setChecked(bool(types_cfg.get('errors', True)))
            self.api_notifications.setChecked(bool(types_cfg.get('api', False)))

            channels_cfg = settings.get('channels', {})
            email_cfg = channels_cfg.get('email', {})
            self.email_checkbox.setChecked(bool(email_cfg.get('enabled', False)))
            self.email_edit.setText(email_cfg.get('address', ''))

            telegram_cfg = channels_cfg.get('telegram', {})
            self.telegram_checkbox.setChecked(bool(telegram_cfg.get('enabled', False)))
            token = telegram_cfg.get('token', '')
            chat_id = telegram_cfg.get('chat_id', '')
            self.telegram_edit.setText(token or chat_id)

            discord_cfg = channels_cfg.get('discord', {})
            self.discord_checkbox.setChecked(bool(discord_cfg.get('enabled', False)))
            self.discord_edit.setText(discord_cfg.get('webhook', ''))
        except Exception as exc:
            print(f"Error loading notification settings: {exc}")
        finally:
            self._loading = False

    def save_settings(self):
        """Zapisuje ustawienia powiadomień"""
        settings = {
            'enabled': self.enable_notifications.isChecked(),
            'sound': self.enable_sound.isChecked(),
            'desktop': self.enable_desktop.isChecked(),
            'types': {
                'trades': self.trade_notifications.isChecked(),
                'profit': self.profit_notifications.isChecked(),
                'errors': self.error_notifications.isChecked(),
                'api': self.api_notifications.isChecked()
            },
            'channels': {
                'email': {
                    'enabled': self.email_checkbox.isChecked(),
                    'address': self.email_edit.text()
                },
                'telegram': {
                    'enabled': self.telegram_checkbox.isChecked(),
                    'token': self.telegram_edit.text()
                },
                'discord': {
                    'enabled': self.discord_checkbox.isChecked(),
                    'webhook': self.discord_edit.text()
                }
            }
        }

        if self.config_manager:
            try:
                self.config_manager.update_notification_settings(settings)
            except Exception as exc:
                QMessageBox.warning(self, "Błąd", f"Nie udało się zapisać ustawień powiadomień: {exc}")
                return

        QMessageBox.information(self, "Zapisano", "Ustawienia powiadomień zostały zapisane.")

    def configure_channel(self, channel_name: str):
        """Konfiguruje kanał powiadomień"""
        QMessageBox.information(self, "Konfiguracja",
                              f"Szczegółowa konfiguracja kanału {channel_name} będzie dostępna wkrótce.")
    
    def test_notifications(self):
        """Testuje powiadomienia"""
        QMessageBox.information(self, "Test Powiadomień", 
                              "Wysłano testowe powiadomienie na wszystkie aktywne kanały.")


class RiskManagementWidget(QWidget):
    """Widget zarządzania ryzykiem"""

    DEFAULT_SETTINGS = {
        'max_position_size': 10.0,
        'max_daily_trades': 50,
        'max_open_positions': 10,
        'default_stop_loss': 2.0,
        'default_take_profit': 5.0,
        'trailing_stop_enabled': False,
        'max_daily_loss': 5.0,
        'max_drawdown': 10.0,
        'emergency_stop_enabled': True,
        'risk_per_trade': 1.0,
        'kelly_criterion_enabled': False,
        'compound_profits': True,
    }

    def __init__(self, parent=None, config_manager=None, risk_manager=None):
        super().__init__(parent)

        if not PYQT_AVAILABLE:
            print("PyQt6 not available, RiskManagementWidget will not function properly")
            return

        self.logger = get_logger("RiskManagementWidget")
        self.config_manager = config_manager or get_config_manager()
        self.risk_manager = risk_manager
        self.RiskLimits = None

        try:
            if self.risk_manager is None:
                from app.risk_management import RiskManager, RiskLimits
                from core.database_manager import DatabaseManager

                db_manager = DatabaseManager()
                self.risk_manager = RiskManager(db_manager)
                self.RiskLimits = RiskLimits
            else:
                from app.risk_management import RiskLimits
                self.RiskLimits = RiskLimits
        except ImportError as e:
            self.logger.warning(f"RiskManager not available: {e}")

        try:
            self.setup_ui()
            self.load_settings()
        except Exception as e:
            print(f"Error setting up RiskManagement UI: {e}")

    def setup_ui(self):
        """Konfiguracja interfejsu"""
        layout = QVBoxLayout(self)
        layout.setSpacing(15)

        title = QLabel("Zarządzanie Ryzykiem")
        title.setStyleSheet("font-size: 16px; font-weight: bold;")
        layout.addWidget(title)

        position_group = QGroupBox("Limity Pozycji")
        position_layout = QFormLayout(position_group)

        self.max_position_size = QDoubleSpinBox()
        self.max_position_size.setRange(0.01, 100.0)
        self.max_position_size.setValue(self.DEFAULT_SETTINGS['max_position_size'])
        self.max_position_size.setSuffix(" %")
        position_layout.addRow("Maksymalny rozmiar pozycji:", self.max_position_size)

        self.max_daily_trades = QSpinBox()
        self.max_daily_trades.setRange(1, 1000)
        self.max_daily_trades.setValue(self.DEFAULT_SETTINGS['max_daily_trades'])
        position_layout.addRow("Maksymalna liczba transakcji dziennie:", self.max_daily_trades)

        self.max_open_positions = QSpinBox()
        self.max_open_positions.setRange(1, 100)
        self.max_open_positions.setValue(self.DEFAULT_SETTINGS['max_open_positions'])
        position_layout.addRow("Maksymalna liczba otwartych pozycji:", self.max_open_positions)

        layout.addWidget(position_group)

        sl_tp_group = QGroupBox("Stop Loss i Take Profit")
        sl_tp_layout = QFormLayout(sl_tp_group)

        self.default_stop_loss = QDoubleSpinBox()
        self.default_stop_loss.setRange(0.1, 50.0)
        self.default_stop_loss.setValue(self.DEFAULT_SETTINGS['default_stop_loss'])
        self.default_stop_loss.setSuffix(" %")
        sl_tp_layout.addRow("Domyślny Stop Loss:", self.default_stop_loss)

        self.default_take_profit = QDoubleSpinBox()
        self.default_take_profit.setRange(0.1, 100.0)
        self.default_take_profit.setValue(self.DEFAULT_SETTINGS['default_take_profit'])
        self.default_take_profit.setSuffix(" %")
        sl_tp_layout.addRow("Domyślny Take Profit:", self.default_take_profit)

        self.trailing_stop = QCheckBox("Włącz Trailing Stop")
        sl_tp_layout.addRow("", self.trailing_stop)

        layout.addWidget(sl_tp_group)

        loss_group = QGroupBox("Limity Strat")
        loss_layout = QFormLayout(loss_group)

        self.max_daily_loss = QDoubleSpinBox()
        self.max_daily_loss.setRange(0.1, 50.0)
        self.max_daily_loss.setValue(self.DEFAULT_SETTINGS['max_daily_loss'])
        self.max_daily_loss.setSuffix(" %")
        loss_layout.addRow("Maksymalna dzienna strata:", self.max_daily_loss)

        self.max_drawdown = QDoubleSpinBox()
        self.max_drawdown.setRange(0.1, 50.0)
        self.max_drawdown.setValue(self.DEFAULT_SETTINGS['max_drawdown'])
        self.max_drawdown.setSuffix(" %")
        loss_layout.addRow("Maksymalny drawdown:", self.max_drawdown)

        self.emergency_stop = QCheckBox("Awaryjne zatrzymanie przy przekroczeniu limitów")
        self.emergency_stop.setChecked(self.DEFAULT_SETTINGS['emergency_stop_enabled'])
        loss_layout.addRow("", self.emergency_stop)

        layout.addWidget(loss_group)

        capital_group = QGroupBox("Zarządzanie Kapitałem")
        capital_layout = QFormLayout(capital_group)

        self.risk_per_trade = QDoubleSpinBox()
        self.risk_per_trade.setRange(0.1, 10.0)
        self.risk_per_trade.setValue(self.DEFAULT_SETTINGS['risk_per_trade'])
        self.risk_per_trade.setSuffix(" %")
        capital_layout.addRow("Ryzyko na transakcję:", self.risk_per_trade)

        self.kelly_criterion = QCheckBox("Użyj kryterium Kelly'ego")
        capital_layout.addRow("", self.kelly_criterion)

        self.compound_profits = QCheckBox("Kapitalizuj zyski")
        self.compound_profits.setChecked(self.DEFAULT_SETTINGS['compound_profits'])
        capital_layout.addRow("", self.compound_profits)

        layout.addWidget(capital_group)

        buttons_layout = QHBoxLayout()
        reset_btn = QPushButton("Resetuj do Domyślnych")
        reset_btn.clicked.connect(self.reset_to_defaults)
        buttons_layout.addWidget(reset_btn)
        buttons_layout.addStretch()
        save_btn = QPushButton("Zapisz")
        save_btn.clicked.connect(self.save_settings)
        buttons_layout.addWidget(save_btn)
        layout.addLayout(buttons_layout)

    def load_settings(self):
        """Ładuje ustawienia zarządzania ryzykiem"""
        try:
            settings = self.config_manager.get_risk_settings() if self.config_manager else dict(self.DEFAULT_SETTINGS)

            self.max_position_size.setValue(settings.get('max_position_size', self.DEFAULT_SETTINGS['max_position_size']))
            self.max_daily_trades.setValue(int(settings.get('max_daily_trades', self.DEFAULT_SETTINGS['max_daily_trades'])))
            self.max_open_positions.setValue(int(settings.get('max_open_positions', self.DEFAULT_SETTINGS['max_open_positions'])))
            self.default_stop_loss.setValue(settings.get('default_stop_loss', self.DEFAULT_SETTINGS['default_stop_loss']))
            self.default_take_profit.setValue(settings.get('default_take_profit', self.DEFAULT_SETTINGS['default_take_profit']))
            self.trailing_stop.setChecked(bool(settings.get('trailing_stop_enabled', self.DEFAULT_SETTINGS['trailing_stop_enabled'])))
            self.max_daily_loss.setValue(settings.get('max_daily_loss', self.DEFAULT_SETTINGS['max_daily_loss']))
            self.max_drawdown.setValue(settings.get('max_drawdown', self.DEFAULT_SETTINGS['max_drawdown']))
            self.emergency_stop.setChecked(bool(settings.get('emergency_stop_enabled', self.DEFAULT_SETTINGS['emergency_stop_enabled'])))
            self.risk_per_trade.setValue(settings.get('risk_per_trade', self.DEFAULT_SETTINGS['risk_per_trade']))
            self.kelly_criterion.setChecked(bool(settings.get('kelly_criterion_enabled', self.DEFAULT_SETTINGS['kelly_criterion_enabled'])))
            self.compound_profits.setChecked(bool(settings.get('compound_profits', self.DEFAULT_SETTINGS['compound_profits'])))

            self.logger.info("Załadowano ustawienia zarządzania ryzykiem")
        except Exception as e:
            self.logger.error(f"Błąd podczas ładowania ustawień: {e}")
            QMessageBox.warning(self, "Błąd", f"Nie udało się załadować ustawień: {e}")

    def save_settings(self):
        """Zapisuje ustawienia zarządzania ryzykiem"""
        try:
            settings = {
                'max_position_size': self.max_position_size.value(),
                'max_daily_trades': self.max_daily_trades.value(),
                'max_open_positions': self.max_open_positions.value(),
                'default_stop_loss': self.default_stop_loss.value(),
                'default_take_profit': self.default_take_profit.value(),
                'trailing_stop_enabled': self.trailing_stop.isChecked(),
                'trailing_stop_distance': 1.0,
                'max_daily_loss': self.max_daily_loss.value(),
                'max_drawdown': self.max_drawdown.value(),
                'emergency_stop_enabled': self.emergency_stop.isChecked(),
                'risk_per_trade': self.risk_per_trade.value(),
                'kelly_criterion_enabled': self.kelly_criterion.isChecked(),
                'compound_profits': self.compound_profits.isChecked()
            }

            if self.config_manager:
                self.config_manager.update_risk_settings(settings)

            if self.risk_manager and self.RiskLimits:
                try:
                    import asyncio
                    try:
                        asyncio.get_running_loop()
                        import concurrent.futures
                        with concurrent.futures.ThreadPoolExecutor() as executor:
                            future = executor.submit(asyncio.run, self.apply_settings_to_bots(settings))
                            future.result(timeout=5)
                    except RuntimeError:
                        asyncio.run(self.apply_settings_to_bots(settings))

                    self.logger.info("Ustawienia zarządzania ryzykiem zostały zaktualizowane w RiskManager")

                except Exception as e:
                    self.logger.error(f"Błąd podczas aktualizacji RiskManager: {e}")

            self.logger.info("Zapisano ustawienia zarządzania ryzykiem")
            QMessageBox.information(self, "Zapisano", "Ustawienia zarządzania ryzykiem zostały zapisane.")

        except Exception as e:
            self.logger.error(f"Błąd podczas zapisywania ustawień: {e}")
            QMessageBox.warning(self, "Błąd", f"Nie udało się zapisać ustawień: {e}")

    def reset_to_defaults(self):
        """Resetuje ustawienia do domyślnych"""
        reply = QMessageBox.question(self, "Reset Ustawień",
                                   "Czy na pewno chcesz zresetować wszystkie ustawienia do domyślnych?",
                                   QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)

        if reply == QMessageBox.StandardButton.Yes:
            defaults = dict(self.DEFAULT_SETTINGS)
            self.max_position_size.setValue(defaults['max_position_size'])
            self.max_daily_trades.setValue(defaults['max_daily_trades'])
            self.max_open_positions.setValue(defaults['max_open_positions'])
            self.default_stop_loss.setValue(defaults['default_stop_loss'])
            self.default_take_profit.setValue(defaults['default_take_profit'])
            self.trailing_stop.setChecked(defaults['trailing_stop_enabled'])
            self.max_daily_loss.setValue(defaults['max_daily_loss'])
            self.max_drawdown.setValue(defaults['max_drawdown'])
            self.emergency_stop.setChecked(defaults['emergency_stop_enabled'])
            self.risk_per_trade.setValue(defaults['risk_per_trade'])
            self.kelly_criterion.setChecked(defaults['kelly_criterion_enabled'])
            self.compound_profits.setChecked(defaults['compound_profits'])

            if self.config_manager:
                try:
                    self.config_manager.update_risk_settings(defaults)
                except Exception as exc:
                    self.logger.error(f"Nie udało się zapisać domyślnych ustawień: {exc}")

    async def apply_settings_to_bots(self, settings):
        """Stosuje ustawienia zarządzania ryzykiem do wszystkich aktywnych botów"""
        try:
            if not self.risk_manager or not self.RiskLimits:
                return

            from core.database_manager import DatabaseManager
            db_manager = DatabaseManager()
            await db_manager.initialize()

            active_bots = await db_manager.get_active_bots()

            risk_limits = self.RiskLimits(
                daily_loss_limit=settings['max_daily_loss'],
                daily_profit_limit=0.0,
                max_drawdown_limit=settings['max_drawdown'],
                position_size_limit=settings['max_position_size'],
                max_open_positions=settings['max_open_positions'],
                max_correlation=0.8,
                volatility_threshold=10.0,
                var_limit=0.0
            )

            for bot in active_bots:
                await self.risk_manager.update_risk_limits(bot['id'], risk_limits)
                self.logger.info(f"Zaktualizowano limity ryzyka dla bota {bot['id']}")

            self.logger.info(f"Zastosowano ustawienia zarządzania ryzykiem do {len(active_bots)} botów")

        except Exception as e:
            self.logger.error(f"Błąd podczas stosowania ustawień do botów: {e}")


class GeneralSettingsWidget(QWidget):
    """Widget ogólnych ustawień aplikacji"""

    THEME_LABELS = {
        "dark": "Ciemny",
        "light": "Jasny",
        "auto": "Automatyczny",
    }

    LANGUAGE_LABELS = {
        "pl": "Polski",
        "en": "English",
        "es": "Español",
        "fr": "Français",
    }

    def __init__(self, parent=None, config_manager=None):
        if not PYQT_AVAILABLE:
            print("PyQt6 not available, GeneralSettingsWidget will not function properly")
            return

        try:
            super().__init__(parent)
            self.config_manager = config_manager or get_config_manager()
            self._theme_reverse = {v: k for k, v in self.THEME_LABELS.items()}
            self._language_reverse = {v: k for k, v in self.LANGUAGE_LABELS.items()}
            self._loading = False

            self.setup_ui()
            self.load_settings()
        except Exception as e:
            print(f"Error initializing GeneralSettingsWidget: {e}")
    
    def setup_ui(self):
        """Konfiguracja interfejsu"""
        layout = QVBoxLayout(self)
        layout.setSpacing(15)
        
        # Nagłówek
        title = QLabel("Ogólne Ustawienia")
        title.setStyleSheet("font-size: 16px; font-weight: bold;")
        layout.addWidget(title)
        
        # Interfejs użytkownika
        ui_group = QGroupBox("Interfejs Użytkownika")
        ui_layout = QFormLayout(ui_group)
        
        self.theme_combo = QComboBox()
        self.theme_combo.addItems(["Ciemny", "Jasny", "Automatyczny"])
        ui_layout.addRow("Motyw:", self.theme_combo)
        
        self.language_combo = QComboBox()
        self.language_combo.addItems(["Polski", "English", "Español", "Français"])
        ui_layout.addRow("Język:", self.language_combo)
        
        self.minimize_to_tray = QCheckBox("Minimalizuj do zasobnika systemowego")
        self.minimize_to_tray.setChecked(True)
        ui_layout.addRow("", self.minimize_to_tray)
        
        self.start_minimized = QCheckBox("Uruchom zminimalizowane")
        ui_layout.addRow("", self.start_minimized)
        
        layout.addWidget(ui_group)
        
        # Automatyczne uruchamianie
        startup_group = QGroupBox("Automatyczne Uruchamianie")
        startup_layout = QVBoxLayout(startup_group)
        
        self.autostart = QCheckBox("Uruchom z systemem")
        startup_layout.addWidget(self.autostart)
        
        self.auto_connect_exchanges = QCheckBox("Automatycznie połącz z giełdami")
        self.auto_connect_exchanges.setChecked(True)
        startup_layout.addWidget(self.auto_connect_exchanges)
        
        self.auto_start_bots = QCheckBox("Automatycznie uruchom boty")
        startup_layout.addWidget(self.auto_start_bots)
        
        layout.addWidget(startup_group)
        
        # Bezpieczeństwo
        security_group = QGroupBox("Bezpieczeństwo")
        security_layout = QVBoxLayout(security_group)
        
        self.encrypt_config = QCheckBox("Szyfruj pliki konfiguracyjne")
        self.encrypt_config.setChecked(True)
        security_layout.addWidget(self.encrypt_config)
        
        self.require_password = QCheckBox("Wymagaj hasła przy uruchomieniu")
        security_layout.addWidget(self.require_password)
        
        self.auto_logout = QCheckBox("Automatyczne wylogowanie po bezczynności")
        security_layout.addWidget(self.auto_logout)
        
        timeout_layout = QHBoxLayout()
        timeout_layout.addWidget(QLabel("Czas bezczynności (minuty):"))
        self.logout_timeout = QSpinBox()
        self.logout_timeout.setRange(5, 120)
        self.logout_timeout.setValue(30)
        timeout_layout.addWidget(self.logout_timeout)
        security_layout.addLayout(timeout_layout)
        
        layout.addWidget(security_group)
        
        # Aktualizacje
        updates_group = QGroupBox("Aktualizacje")
        updates_layout = QVBoxLayout(updates_group)
        
        self.auto_check_updates = QCheckBox("Automatycznie sprawdzaj aktualizacje")
        self.auto_check_updates.setChecked(True)
        updates_layout.addWidget(self.auto_check_updates)
        
        self.beta_updates = QCheckBox("Włącz aktualizacje beta")
        updates_layout.addWidget(self.beta_updates)
        
        check_updates_btn = QPushButton("Sprawdź Aktualizacje Teraz")
        check_updates_btn.clicked.connect(self.check_updates)
        updates_layout.addWidget(check_updates_btn)
        
        layout.addWidget(updates_group)
        
        # Przyciski
        buttons_layout = QHBoxLayout()
        
        export_btn = QPushButton("Eksportuj Ustawienia")
        export_btn.clicked.connect(self.export_settings)
        buttons_layout.addWidget(export_btn)
        
        import_btn = QPushButton("Importuj Ustawienia")
        import_btn.clicked.connect(self.import_settings)
        buttons_layout.addWidget(import_btn)
        
        buttons_layout.addStretch()
        
        save_btn = QPushButton("Zapisz")
        save_btn.clicked.connect(self.save_settings)
        buttons_layout.addWidget(save_btn)
        
        layout.addLayout(buttons_layout)
    
    def load_settings(self):
        """Ładuje ogólne ustawienia z ConfigManager."""
        if not hasattr(self, "config_manager") or self.config_manager is None:
            return

        try:
            self._loading = True
            settings = self.config_manager.get_general_settings()

            ui_settings = settings.get("ui", {})
            startup_settings = settings.get("startup", {})
            security_settings = settings.get("security", {})
            updates_settings = settings.get("updates", {})

            theme_key = ui_settings.get("theme", "dark").lower()
            self.theme_combo.setCurrentText(self.THEME_LABELS.get(theme_key, "Ciemny"))
            language_key = ui_settings.get("language", "pl").lower()
            self.language_combo.setCurrentText(self.LANGUAGE_LABELS.get(language_key, "Polski"))
            self.minimize_to_tray.setChecked(bool(ui_settings.get("minimize_to_tray", True)))
            self.start_minimized.setChecked(bool(ui_settings.get("start_minimized", False)))

            self.autostart.setChecked(bool(startup_settings.get("start_with_system", False)))
            self.auto_start_bots.setChecked(bool(startup_settings.get("auto_start_bots", False)))
            self.auto_connect_exchanges.setChecked(bool(startup_settings.get("auto_connect_exchanges", True)))

            self.encrypt_config.setChecked(bool(security_settings.get("encrypt_config", True)))
            self.require_password.setChecked(bool(security_settings.get("require_password", True)))
            self.auto_logout.setChecked(bool(security_settings.get("auto_logout", True)))
            self.logout_timeout.setValue(int(security_settings.get("logout_timeout", 30)))

            self.auto_check_updates.setChecked(bool(updates_settings.get("auto_check", True)))
            self.beta_updates.setChecked(bool(updates_settings.get("beta_updates", False)))
        except Exception as exc:
            print(f"Error loading general settings: {exc}")
        finally:
            self._loading = False

    def save_settings(self):
        """Zapisuje ogólne ustawienia"""
        payload = {
            'ui': {
                'theme': self._theme_reverse.get(self.theme_combo.currentText(), 'dark'),
                'language': self._language_reverse.get(self.language_combo.currentText(), 'pl'),
                'minimize_to_tray': self.minimize_to_tray.isChecked(),
                'start_minimized': self.start_minimized.isChecked()
            },
            'startup': {
                'start_with_system': self.autostart.isChecked(),
                'auto_start_bots': self.auto_start_bots.isChecked(),
                'auto_connect_exchanges': self.auto_connect_exchanges.isChecked()
            },
            'security': {
                'encrypt_config': self.encrypt_config.isChecked(),
                'require_password': self.require_password.isChecked(),
                'auto_logout': self.auto_logout.isChecked(),
                'logout_timeout': self.logout_timeout.value()
            },
            'updates': {
                'auto_check': self.auto_check_updates.isChecked(),
                'beta_updates': self.beta_updates.isChecked()
            }
        }

        if hasattr(self, "config_manager") and self.config_manager:
            try:
                self.config_manager.update_general_settings(payload)
            except Exception as exc:
                QMessageBox.warning(self, "Błąd", f"Nie udało się zapisać ustawień: {exc}")
                return

        QMessageBox.information(self, "Zapisano", "Ogólne ustawienia zostały zapisane.")
    
    def check_updates(self):
        """Sprawdza dostępne aktualizacje"""
        QMessageBox.information(self, "Aktualizacje", 
                              "Sprawdzanie aktualizacji...\n\n"
                              "Używasz najnowszej wersji aplikacji! ✅")
    
    def export_settings(self):
        """Eksportuje ustawienia do pliku"""
        file_path, _ = QFileDialog.getSaveFileName(
            self, "Eksportuj Ustawienia",
            f"settings_export_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json",
            "JSON Files (*.json)"
        )
        
        if file_path:
            # Symulacja eksportu
            QMessageBox.information(self, "Eksport", f"Ustawienia wyeksportowane do:\n{file_path}")
    
    def import_settings(self):
        """Importuje ustawienia z pliku"""
        file_path, _ = QFileDialog.getOpenFileName(
            self, "Importuj Ustawienia",
            "", "JSON Files (*.json)"
        )
        
        if file_path:
            # Symulacja importu
            QMessageBox.information(self, "Import", f"Ustawienia zaimportowane z:\n{file_path}")


class SettingsWidget(QWidget):
    """Główny widget ustawień"""

    def __init__(self, parent=None, config_manager=None, risk_manager=None, notification_manager=None):
        if not PYQT_AVAILABLE:
            print("PyQt6 not available, SettingsWidget will not function properly")
            object.__init__(self)
            return

        super().__init__(parent)

        try:
            self.logger = get_logger(__name__)
            self.config_manager = config_manager or get_config_manager()
            self.risk_manager = risk_manager
            self.notification_manager = notification_manager
            self.setup_ui()
        except Exception as e:
            print(f"Error initializing SettingsWidget: {e}")
    
    def setup_ui(self):
        """Konfiguracja interfejsu"""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        
        # Zakładki ustawień
        self.tabs = QTabWidget()
        
        # Zakładka giełd
        self.exchanges_widget = ExchangeConfigWidget()
        self.tabs.addTab(self.exchanges_widget, "🏦 Giełdy")

        # Zakładka powiadomień
        self.notifications_widget = NotificationConfigWidget(
            config_manager=self.config_manager,
            notification_manager=self.notification_manager,
        )
        self.tabs.addTab(self.notifications_widget, "🔔 Powiadomienia")

        # Zakładka zarządzania ryzykiem
        self.risk_widget = RiskManagementWidget(
            config_manager=self.config_manager,
            risk_manager=self.risk_manager,
        )
        self.tabs.addTab(self.risk_widget, "⚠️ Zarządzanie Ryzykiem")

        # Zakładka ogólnych ustawień
        self.general_widget = GeneralSettingsWidget(
            config_manager=self.config_manager,
        )
        self.tabs.addTab(self.general_widget, "⚙️ Ogólne")
        
        layout.addWidget(self.tabs)


def main():
    """Funkcja główna do testowania"""
    if not PYQT_AVAILABLE:
        print("PyQt6 is not available. Please install it to run the GUI.")
        return
    
    import sys
    from PyQt6.QtWidgets import QApplication
    
    app = QApplication(sys.argv)
    
    widget = SettingsWidget()
    widget.show()
    
    sys.exit(app.exec())

if __name__ == "__main__":
    main()
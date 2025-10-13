"""
Interfejs konfiguracji botów

Zawiera kreatory i edytory dla różnych typów botów handlowych.
"""

import sys
import json
from typing import Dict, List, Optional, Any, Tuple
from datetime import datetime
from pathlib import Path

try:
    from PyQt6.QtWidgets import (
        QWidget, QVBoxLayout, QHBoxLayout, QGridLayout, QFormLayout,
        QLabel, QPushButton, QFrame, QScrollArea, QTabWidget,
        QComboBox, QLineEdit, QSpinBox, QDoubleSpinBox, QCheckBox,
        QGroupBox, QTextEdit, QSlider, QProgressBar, QMessageBox,
        QDialog, QDialogButtonBox, QTableWidget, QTableWidgetItem,
        QHeaderView, QSplitter, QStackedWidget, QButtonGroup,
        QRadioButton, QListWidget, QListWidgetItem, QTreeWidget,
        QTreeWidgetItem, QFileDialog, QColorDialog
    )
    from PyQt6.QtCore import (
        Qt, QTimer, pyqtSignal, QSize, QPropertyAnimation,
        QEasingCurve, QParallelAnimationGroup, QThread
    )
    from PyQt6.QtGui import (
        QFont, QPixmap, QIcon, QPalette, QColor, QPainter,
        QPen, QBrush, QLinearGradient, QValidator, QIntValidator,
        QDoubleValidator, QRegularExpressionValidator
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
    
    class QVBoxLayout:
        def __init__(self, parent=None): pass
        def addWidget(self, widget): pass
        def addLayout(self, layout): pass
        def addStretch(self): pass
        def setContentsMargins(self, *args): pass
        def setSpacing(self, spacing): pass
        def count(self): return 0
        def itemAt(self, index): return None
    
    class QHBoxLayout(QVBoxLayout): pass
    class QGridLayout(QVBoxLayout): 
        def addWidget(self, widget, row, col): pass
    
    class QLabel(QWidget):
        def __init__(self, text="", parent=None): pass
        def setText(self, text): pass
        def setAlignment(self, alignment): pass
    
    class QPushButton(QWidget):
        def __init__(self, text="", parent=None): pass
        def clicked(self): return lambda: None
        def connect(self, func): pass
    
    class QFrame(QWidget):
        def setFrameStyle(self, style): pass
        Shape = type('Shape', (), {'StyledPanel': 0})()
    
    class QScrollArea(QWidget):
        def setWidgetResizable(self, resizable): pass
        def setHorizontalScrollBarPolicy(self, policy): pass
        def setWidget(self, widget): pass
    
    class QSplitter(QWidget):
        def __init__(self, orientation=None): pass
        def addWidget(self, widget): pass
        def setSizes(self, sizes): pass
    
    class QMessageBox:
        @staticmethod
        def information(parent, title, text): print(f"Info: {title} - {text}")
        @staticmethod
        def question(parent, title, text, buttons): return QMessageBox.StandardButton.Yes
        StandardButton = type('StandardButton', (), {'Yes': 1, 'No': 0})()
    
    class QFileDialog:
        @staticmethod
        def getOpenFileName(parent, caption, directory, filter): return ("", "")
        @staticmethod
        def getSaveFileName(parent, caption, filename, filter): return ("", "")
    
    class Qt:
        Orientation = type('Orientation', (), {'Horizontal': 1, 'Vertical': 2})()
        ScrollBarPolicy = type('ScrollBarPolicy', (), {'ScrollBarAlwaysOff': 0})()
        AlignmentFlag = type('AlignmentFlag', (), {'AlignCenter': 0})()
    
    class QTimer:
        def timeout(self): return lambda: None
        def connect(self, func): pass
        def start(self, interval): pass
    
    class QApplication:
        def __init__(self, args): pass
        def exec(self): return 0

# Import lokalnych modułów
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from utils.config_manager import get_config_manager, get_ui_setting, get_app_setting
from utils.logger import get_logger, LogType
from utils.helpers import ValidationHelper, FormatHelper

class BotConfigWidget(QWidget):
    """Główny widget konfiguracji botów"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        
        if not PYQT_AVAILABLE:
            print("PyQt6 not available, BotConfigWidget will not function properly")
            return
            
        try:
            self.config_manager = get_config_manager()
            self.logger = get_logger("BotConfig")
        except Exception as e:
            print(f"Error initializing config/logger: {e}")
            self.config_manager = None
            self.logger = None
        
        # Przechowywanie stanu botów
        self.bots_data = []
        
        try:
            self.setup_ui()
            self.load_sample_bots()
        except Exception as e:
            print(f"Error setting up BotConfig UI: {e}")
            if hasattr(self, 'logger') and self.logger:
                self.logger.error(f"BotConfig UI setup failed: {e}")
    
    def setup_ui(self):
        """Konfiguracja interfejsu"""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(10, 10, 10, 10)  # Zmniejszone marginesy
        layout.setSpacing(10)  # Zmniejszone odstępy
        
        # Kompaktowy nagłówek
        header_layout = QHBoxLayout()
        
        title = QLabel("Zarządzanie Botami")
        title.setStyleSheet("font-size: 18px; font-weight: bold; color: #2c3e50;")  # Mniejszy font
        header_layout.addWidget(title)
        
        header_layout.addStretch()
        
        # Kompaktowe przyciski akcji
        self.new_bot_btn = QPushButton("+ Nowy")
        self.new_bot_btn.setStyleSheet("""
            QPushButton {
                background-color: #3498db;
                color: white;
                border: none;
                padding: 6px 12px;
                border-radius: 4px;
                font-weight: bold;
                font-size: 12px;
                min-width: 60px;
            }
            QPushButton:hover {
                background-color: #2980b9;
            }
        """)
        self.new_bot_btn.clicked.connect(self.create_new_bot)
        header_layout.addWidget(self.new_bot_btn)
        
        self.import_btn = QPushButton("Import")
        self.import_btn.setStyleSheet("""
            QPushButton {
                background-color: #95a5a6;
                color: white;
                border: none;
                padding: 6px 12px;
                border-radius: 4px;
                font-weight: bold;
                font-size: 12px;
                min-width: 60px;
            }
            QPushButton:hover {
                background-color: #7f8c8d;
            }
        """)
        self.import_btn.clicked.connect(self.import_bot_config)
        header_layout.addWidget(self.import_btn)
        
        self.export_btn = QPushButton("Export")
        self.export_btn.setStyleSheet("""
            QPushButton {
                background-color: #95a5a6;
                color: white;
                border: none;
                padding: 6px 12px;
                border-radius: 4px;
                font-weight: bold;
                font-size: 12px;
                min-width: 60px;
            }
            QPushButton:hover {
                background-color: #7f8c8d;
            }
        """)
        self.export_btn.clicked.connect(self.export_bot_config)
        header_layout.addWidget(self.export_btn)
        
        layout.addLayout(header_layout)
        
        # Główny splitter z mniejszymi proporcjami
        splitter = QSplitter(Qt.Orientation.Horizontal)
        
        # Lista botów (lewa strona) - kompaktowa
        bots_frame = QFrame()
        bots_frame.setFrameStyle(QFrame.Shape.StyledPanel)
        bots_frame.setStyleSheet("""
            QFrame {
                border: 1px solid #bdc3c7;
                border-radius: 6px;
                background-color: #ecf0f1;
                padding: 8px;
            }
        """)
        bots_layout = QVBoxLayout(bots_frame)
        bots_layout.setContentsMargins(8, 8, 8, 8)
        bots_layout.setSpacing(8)
        
        bots_header = QLabel("Aktywne Boty")
        bots_header.setStyleSheet("font-size: 14px; font-weight: bold; margin-bottom: 5px; color: #2c3e50;")
        bots_layout.addWidget(bots_header)
        
        # Scroll area dla listy botów
        self.bots_scroll = QScrollArea()
        self.bots_scroll.setWidgetResizable(True)
        self.bots_scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.bots_scroll.setMaximumHeight(400)  # Ograniczenie wysokości
        
        self.bots_widget = QWidget()
        self.bots_layout = QVBoxLayout(self.bots_widget)
        self.bots_layout.setSpacing(5)  # Mniejsze odstępy między kartami
        
        self.bots_scroll.setWidget(self.bots_widget)
        bots_layout.addWidget(self.bots_scroll)
        
        splitter.addWidget(bots_frame)
        
        # Panel konfiguracji (prawa strona) - rozwijane sekcje
        config_frame = QFrame()
        config_frame.setFrameStyle(QFrame.Shape.StyledPanel)
        config_frame.setStyleSheet("""
            QFrame {
                border: 1px solid #bdc3c7;
                border-radius: 6px;
                background-color: #ecf0f1;
                padding: 8px;
            }
        """)
        config_layout = QVBoxLayout(config_frame)
        config_layout.setContentsMargins(8, 8, 8, 8)
        config_layout.setSpacing(8)
        
        config_header = QLabel("Konfiguracja Bota")
        config_header.setStyleSheet("font-size: 14px; font-weight: bold; margin-bottom: 5px; color: #2c3e50;")
        config_layout.addWidget(config_header)
        
        # Rozwijane sekcje konfiguracji
        self.config_scroll = QScrollArea()
        self.config_scroll.setWidgetResizable(True)
        self.config_scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        
        self.config_widget = QWidget()
        self.config_widget_layout = QVBoxLayout(self.config_widget)
        self.config_widget_layout.setSpacing(8)
        
        # Placeholder dla konfiguracji
        self.config_placeholder = QLabel("Wybierz bota z listy aby edytować jego konfigurację")
        self.config_placeholder.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.config_placeholder.setStyleSheet("color: #7f8c8d; font-size: 12px; padding: 20px;")
        self.config_widget_layout.addWidget(self.config_placeholder)
        
        self.config_scroll.setWidget(self.config_widget)
        config_layout.addWidget(self.config_scroll)
        
        splitter.addWidget(config_frame)
        
        # Ustaw mniejsze proporcje splitter
        splitter.setSizes([250, 400])  # Zmniejszone rozmiary
        layout.addWidget(splitter)
    
    def load_sample_bots(self):
        """Ładuje przykładowe boty"""
        # Jeśli bots_data jest puste, załaduj przykładowe dane
        if not self.bots_data:
            self.bots_data = [
                {
                    "id": "bot_001",
                    "name": "DCA Bitcoin",
                    "type": "dca",
                    "pair": "BTC/USDT",
                    "status": "running",
                    "profit": 245.67,
                    "created": "2024-01-15"
                },
                {
                    "id": "bot_002", 
                    "name": "Grid ETH",
                    "type": "grid",
                    "pair": "ETH/USDT",
                    "status": "stopped",
                    "profit": -12.34,
                    "created": "2024-01-20"
                },
                {
                    "id": "bot_003",
                    "name": "Scalping ADA",
                    "type": "scalping", 
                    "pair": "ADA/USDT",
                    "status": "running",
                    "profit": 89.12,
                    "created": "2024-01-25"
                }
            ]
        
        self.refresh_bots_display()
    
    def refresh_bots_display(self):
        """Odświeża wyświetlanie botów"""
        if not PYQT_AVAILABLE or not hasattr(self, 'bots_layout'):
            return
            
        try:
            # Wyczyść istniejące boty
            for i in reversed(range(self.bots_layout.count())):
                child = self.bots_layout.itemAt(i).widget()
                if child:
                    child.setParent(None)
            
            # Dodaj boty z aktualnych danych
            for bot_data in self.bots_data:
                try:
                    bot_card = self.create_bot_card(bot_data)
                    self.bots_layout.addWidget(bot_card)
                except Exception as e:
                    print(f"Error creating bot card: {e}")
                    if hasattr(self, 'logger') and self.logger:
                        self.logger.error(f"Failed to create bot card: {e}")
            
            self.bots_layout.addStretch()
        except Exception as e:
            print(f"Error refreshing bots display: {e}")
            if hasattr(self, 'logger') and self.logger:
                self.logger.error(f"Failed to refresh bots display: {e}")
    
    def get_bot_data(self):
        """Pobiera dane bota z formularza"""
        try:
            # Sprawdź czy formularz istnieje
            if not hasattr(self, 'form_widget') or not self.form_widget:
                return None
            
            # Pobierz dane z pól formularza
            bot_data = {
                'name': getattr(self, 'name_input', QLineEdit()).text() or f"Bot_{len(self.bots_data) + 1}",
                'type': getattr(self, 'type_combo', QComboBox()).currentText() or "DCA",
                'pair': getattr(self, 'pair_combo', QComboBox()).currentText() or "BTC/USDT",
                'status': 'stopped',
                'id': len(self.bots_data) + 1,
                'pnl': 0.0,
                'created_at': datetime.now().isoformat()
            }
            
            # Dodaj dodatkowe parametry w zależności od typu bota
            if hasattr(self, 'amount_input'):
                try:
                    bot_data['amount'] = float(self.amount_input.text() or "100")
                except ValueError:
                    bot_data['amount'] = 100.0
            
            if hasattr(self, 'interval_combo'):
                bot_data['interval'] = self.interval_combo.currentText() or "1h"
            
            return bot_data
            
        except Exception as e:
            print(f"Error getting bot data: {e}")
            if hasattr(self, 'logger') and self.logger:
                self.logger.error(f"Failed to get bot data: {e}")
            return None
    
    def create_bot_card(self, bot_data: Dict) -> QFrame:
        """Tworzy kompaktową kartę bota"""
        card = QFrame()
        card.setFrameStyle(QFrame.Shape.StyledPanel)
        card.setStyleSheet("""
            QFrame {
                border: 1px solid #34495e;
                border-radius: 6px;
                background-color: #2c3e50;
                padding: 8px;
                margin: 2px;
                max-height: 120px;
            }
            QFrame:hover {
                border-color: #3498db;
                background-color: #34495e;
            }
        """)
        
        layout = QVBoxLayout(card)
        layout.setSpacing(4)
        layout.setContentsMargins(6, 6, 6, 6)
        
        # Kompaktowy nagłówek z nazwą i statusem
        header_layout = QHBoxLayout()
        
        name_label = QLabel(bot_data.get("name", f"Bot {bot_data['id']}"))
        name_label.setStyleSheet("font-weight: bold; font-size: 12px; color: white;")
        header_layout.addWidget(name_label)
        
        header_layout.addStretch()
        
        # Kompaktowy status
        status = bot_data.get("status", "unknown")
        status_label = QLabel(status.upper())
        if status == "running":
            status_label.setStyleSheet("color: #2ecc71; font-weight: bold; background-color: #27ae60; padding: 2px 6px; border-radius: 3px; font-size: 10px;")
        elif status == "stopped":
            status_label.setStyleSheet("color: white; font-weight: bold; background-color: #e74c3c; padding: 2px 6px; border-radius: 3px; font-size: 10px;")
        else:
            status_label.setStyleSheet("color: #2c3e50; font-weight: bold; background-color: #f39c12; padding: 2px 6px; border-radius: 3px; font-size: 10px;")
        
        header_layout.addWidget(status_label)
        layout.addLayout(header_layout)
        
        # Kompaktowe informacje o bocie
        info_layout = QHBoxLayout()
        
        # Typ strategii i para w jednej linii
        strategy_label = QLabel(f"{bot_data.get('type', '').upper()} • {bot_data.get('pair', 'N/A')}")
        strategy_label.setStyleSheet("color: #bdc3c7; font-size: 10px;")
        info_layout.addWidget(strategy_label)
        
        info_layout.addStretch()
        
        # Zysk/Strata
        profit = bot_data.get("profit", 0)
        profit_label = QLabel(f"${profit:.2f}")
        if profit >= 0:
            profit_label.setStyleSheet("color: #27ae60; font-weight: bold; font-size: 11px;")
        else:
            profit_label.setStyleSheet("color: #e74c3c; font-weight: bold; font-size: 11px;")
        info_layout.addWidget(profit_label)
        
        layout.addLayout(info_layout)
        
        # Kompaktowe przyciski akcji
        buttons_layout = QHBoxLayout()
        buttons_layout.setSpacing(4)
        
        edit_btn = QPushButton("Edytuj")
        edit_btn.setStyleSheet("""
            QPushButton {
                background-color: #3498db;
                color: white;
                border: none;
                padding: 4px 8px;
                border-radius: 3px;
                font-weight: bold;
                font-size: 10px;
                min-width: 40px;
            }
            QPushButton:hover {
                background-color: #2980b9;
            }
        """)
        edit_btn.clicked.connect(lambda: self.edit_bot(bot_data))
        buttons_layout.addWidget(edit_btn)
        
        if status == "running":
            stop_btn = QPushButton("Stop")
            stop_btn.setStyleSheet("""
                QPushButton {
                    background-color: #e74c3c;
                    color: white;
                    border: none;
                    padding: 4px 8px;
                    border-radius: 3px;
                    font-weight: bold;
                    font-size: 10px;
                    min-width: 40px;
                }
                QPushButton:hover {
                    background-color: #c0392b;
                }
            """)
            stop_btn.clicked.connect(lambda: self.toggle_bot(bot_data))
            buttons_layout.addWidget(stop_btn)
        else:
            start_btn = QPushButton("Start")
            start_btn.setStyleSheet("""
                QPushButton {
                    background-color: #27ae60;
                    color: white;
                    border: none;
                    padding: 4px 8px;
                    border-radius: 3px;
                    font-weight: bold;
                    font-size: 10px;
                    min-width: 40px;
                }
                QPushButton:hover {
                    background-color: #229954;
                }
            """)
            start_btn.clicked.connect(lambda: self.toggle_bot(bot_data))
            buttons_layout.addWidget(start_btn)
        
        delete_btn = QPushButton("×")
        delete_btn.setStyleSheet("""
            QPushButton {
                background-color: #95a5a6;
                color: white;
                border: none;
                padding: 4px 6px;
                border-radius: 3px;
                font-weight: bold;
                font-size: 12px;
                min-width: 20px;
                max-width: 20px;
            }
            QPushButton:hover {
                background-color: #e74c3c;
            }
        """)
        delete_btn.clicked.connect(lambda: self.delete_bot(bot_data))
        buttons_layout.addWidget(delete_btn)
        
        layout.addLayout(buttons_layout)
        
        return card
    
    def create_collapsible_section(self, title: str, content_widget: QWidget) -> QFrame:
        """Tworzy rozwijalną sekcję"""
        section = QFrame()
        section.setStyleSheet("""
            QFrame {
                border: 1px solid #bdc3c7;
                border-radius: 4px;
                background-color: #ffffff;
                margin: 2px;
            }
        """)
        
        layout = QVBoxLayout(section)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        
        # Nagłówek z przyciskiem rozwijania
        header = QPushButton(f"▼ {title}")
        header.setStyleSheet("""
            QPushButton {
                background-color: #34495e;
                color: white;
                border: none;
                padding: 8px 12px;
                text-align: left;
                font-weight: bold;
                font-size: 12px;
            }
            QPushButton:hover {
                background-color: #2c3e50;
            }
        """)
        
        # Kontener na zawartość
        content_container = QFrame()
        content_container.setStyleSheet("background-color: #ffffff; padding: 8px;")
        content_layout = QVBoxLayout(content_container)
        content_layout.addWidget(content_widget)
        
        # Funkcja przełączania widoczności
        def toggle_section():
            is_visible = content_container.isVisible()
            content_container.setVisible(not is_visible)
            header.setText(f"{'▲' if not is_visible else '▼'} {title}")
        
        header.clicked.connect(toggle_section)
        
        layout.addWidget(header)
        layout.addWidget(content_container)
        
        # Domyślnie zwinięte
        content_container.setVisible(False)
        header.setText(f"▼ {title}")
        
        return section
    
    def create_bot_config_form(self, bot_data: Dict) -> QWidget:
        """Tworzy formularz konfiguracji bota"""
        form_widget = QWidget()
        form_layout = QVBoxLayout(form_widget)
        form_layout.setSpacing(8)
        
        # Podstawowe informacje
        basic_info = QWidget()
        basic_layout = QFormLayout(basic_info)
        basic_layout.setSpacing(4)
        
        # Nazwa bota
        name_edit = QLineEdit(bot_data.get("name", ""))
        name_edit.setStyleSheet("padding: 4px; border: 1px solid #bdc3c7; border-radius: 3px;")
        basic_layout.addRow("Nazwa:", name_edit)
        
        # Typ strategii
        strategy_combo = QComboBox()
        strategy_combo.addItems(["DCA", "Grid", "Scalping", "Custom"])
        strategy_combo.setCurrentText(bot_data.get("type", "").upper())
        strategy_combo.setStyleSheet("padding: 4px; border: 1px solid #bdc3c7; border-radius: 3px;")
        basic_layout.addRow("Strategia:", strategy_combo)
        
        # Para handlowa
        pair_edit = QLineEdit(bot_data.get("pair", ""))
        pair_edit.setStyleSheet("padding: 4px; border: 1px solid #bdc3c7; border-radius: 3px;")
        basic_layout.addRow("Para:", pair_edit)
        
        basic_section = self.create_collapsible_section("Podstawowe ustawienia", basic_info)
        form_layout.addWidget(basic_section)
        
        # Ustawienia handlowe
        trading_info = QWidget()
        trading_layout = QFormLayout(trading_info)
        trading_layout.setSpacing(4)
        
        # Kwota inwestycji
        amount_spin = QDoubleSpinBox()
        amount_spin.setRange(0.01, 100000.0)
        amount_spin.setValue(100.0)
        amount_spin.setStyleSheet("padding: 4px; border: 1px solid #bdc3c7; border-radius: 3px;")
        trading_layout.addRow("Kwota (USDT):", amount_spin)
        
        # Take Profit
        tp_spin = QDoubleSpinBox()
        tp_spin.setRange(0.1, 100.0)
        tp_spin.setValue(2.0)
        tp_spin.setSuffix("%")
        tp_spin.setStyleSheet("padding: 4px; border: 1px solid #bdc3c7; border-radius: 3px;")
        trading_layout.addRow("Take Profit:", tp_spin)
        
        # Stop Loss
        sl_spin = QDoubleSpinBox()
        sl_spin.setRange(0.1, 100.0)
        sl_spin.setValue(5.0)
        sl_spin.setSuffix("%")
        sl_spin.setStyleSheet("padding: 4px; border: 1px solid #bdc3c7; border-radius: 3px;")
        trading_layout.addRow("Stop Loss:", sl_spin)
        
        trading_section = self.create_collapsible_section("Ustawienia handlowe", trading_info)
        form_layout.addWidget(trading_section)
        
        # Zaawansowane ustawienia
        advanced_info = QWidget()
        advanced_layout = QFormLayout(advanced_info)
        advanced_layout.setSpacing(4)
        
        # Maksymalne zlecenia
        max_orders_spin = QSpinBox()
        max_orders_spin.setRange(1, 50)
        max_orders_spin.setValue(10)
        max_orders_spin.setStyleSheet("padding: 4px; border: 1px solid #bdc3c7; border-radius: 3px;")
        advanced_layout.addRow("Max. zlecenia:", max_orders_spin)
        
        # Interwał
        interval_combo = QComboBox()
        interval_combo.addItems(["1m", "5m", "15m", "1h", "4h", "1d"])
        interval_combo.setCurrentText("5m")
        interval_combo.setStyleSheet("padding: 4px; border: 1px solid #bdc3c7; border-radius: 3px;")
        advanced_layout.addRow("Interwał:", interval_combo)
        
        advanced_section = self.create_collapsible_section("Ustawienia zaawansowane", advanced_info)
        form_layout.addWidget(advanced_section)
        
        # Przyciski akcji
        buttons_widget = QWidget()
        buttons_layout = QHBoxLayout(buttons_widget)
        
        save_btn = QPushButton("Zapisz")
        save_btn.setStyleSheet("""
            QPushButton {
                background-color: #27ae60;
                color: white;
                border: none;
                padding: 8px 16px;
                border-radius: 4px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #229954;
            }
        """)
        save_btn.clicked.connect(lambda: self.save_bot_config(bot_data))
        buttons_layout.addWidget(save_btn)
        
        cancel_btn = QPushButton("Anuluj")
        cancel_btn.setStyleSheet("""
            QPushButton {
                background-color: #95a5a6;
                color: white;
                border: none;
                padding: 8px 16px;
                border-radius: 4px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #7f8c8d;
            }
        """)
        cancel_btn.clicked.connect(self.cancel_bot_edit)
        buttons_layout.addWidget(cancel_btn)
        
        form_layout.addWidget(buttons_widget)
        form_layout.addStretch()
        
        return form_widget
    
    def save_bot_config(self, bot_data: Dict):
        """Zapisuje konfigurację bota"""
        QMessageBox.information(self, "Zapisano", f"Konfiguracja bota '{bot_data.get('name', 'Unknown')}' została zapisana.")
        self.cancel_bot_edit()
    
    def cancel_bot_edit(self):
        """Anuluje edycję bota"""
        # Przywróć placeholder
        for i in reversed(range(self.config_widget_layout.count())):
            child = self.config_widget_layout.itemAt(i).widget()
            if child:
                child.setParent(None)
        
        self.config_widget_layout.addWidget(self.config_placeholder)
    
    def edit_bot(self, bot_data: Dict):
        """Edytuje konfigurację bota z pełnym formularzem"""
        # Wyczyść obecną zawartość
        for i in reversed(range(self.config_widget_layout.count())):
            child = self.config_widget_layout.itemAt(i).widget()
            if child:
                child.setParent(None)
        
        # Dodaj formularz konfiguracji
        config_form = self.create_bot_config_form(bot_data)
        self.config_widget_layout.addWidget(config_form)
    
    def create_new_bot(self):
        """Tworzy nowego bota"""
        try:
            # Przykładowe dane nowego bota
            new_bot_data = {
                "id": len(self.bots_data) + 1,
                "name": f"Nowy Bot {len(self.bots_data) + 1}",
                "type": "dca",
                "pair": "BTC/USDT",
                "status": "stopped",
                "profit": 0.0,
                "trades": 0
            }
            
            # Dodaj do listy botów
            self.bots_data.append(new_bot_data)
            
            # Odśwież wyświetlanie
            self.refresh_bots_display()
            
            # Otwórz formularz edycji dla nowego bota
            self.edit_bot(new_bot_data)
            
            if hasattr(self, 'logger') and self.logger:
                self.logger.info(f"Created new bot: {new_bot_data['name']}")
                
        except Exception as e:
            print(f"Error creating new bot: {e}")
            if hasattr(self, 'logger') and self.logger:
                self.logger.error(f"Failed to create new bot: {e}")
    
    def import_bot_config(self):
        """Importuje konfigurację bota"""
        try:
            from PyQt6.QtWidgets import QFileDialog
            file_path, _ = QFileDialog.getOpenFileName(
                self, 
                "Importuj konfigurację bota", 
                "", 
                "JSON files (*.json);;All files (*.*)"
            )
            
            if file_path:
                import json
                with open(file_path, 'r', encoding='utf-8') as f:
                    bot_config = json.load(f)
                
                # Dodaj do listy botów
                self.bots_data.append(bot_config)
                self.refresh_bots_display()
                
                QMessageBox.information(self, "Sukces", "Konfiguracja bota została zaimportowana.")
                
                if hasattr(self, 'logger') and self.logger:
                    self.logger.info(f"Imported bot config from: {file_path}")
                    
        except Exception as e:
            QMessageBox.critical(self, "Błąd", f"Nie udało się zaimportować konfiguracji: {str(e)}")
            if hasattr(self, 'logger') and self.logger:
                self.logger.error(f"Failed to import bot config: {e}")
    
    def export_bot_config(self):
        """Eksportuje konfigurację botów"""
        try:
            from PyQt6.QtWidgets import QFileDialog
            file_path, _ = QFileDialog.getSaveFileName(
                self, 
                "Eksportuj konfigurację botów", 
                "bots_config.json", 
                "JSON files (*.json);;All files (*.*)"
            )
            
            if file_path:
                import json
                with open(file_path, 'w', encoding='utf-8') as f:
                    json.dump(self.bots_data, f, indent=2, ensure_ascii=False)
                
                QMessageBox.information(self, "Sukces", "Konfiguracja botów została wyeksportowana.")
                
                if hasattr(self, 'logger') and self.logger:
                    self.logger.info(f"Exported bots config to: {file_path}")
                    
        except Exception as e:
            QMessageBox.critical(self, "Błąd", f"Nie udało się wyeksportować konfiguracji: {str(e)}")
            if hasattr(self, 'logger') and self.logger:
                self.logger.error(f"Failed to export bots config: {e}")
    
    def toggle_bot(self, bot_data: Dict):
        """Przełącza status bota (start/stop)"""
        try:
            current_status = bot_data.get("status", "stopped")
            new_status = "stopped" if current_status == "running" else "running"
            
            # Aktualizuj status w danych
            for bot in self.bots_data:
                if bot.get("id") == bot_data.get("id"):
                    bot["status"] = new_status
                    break
            
            # Odśwież wyświetlanie
            self.refresh_bots_display()
            
            action = "uruchomiony" if new_status == "running" else "zatrzymany"
            QMessageBox.information(self, "Status", f"Bot '{bot_data.get('name')}' został {action}.")
            
            if hasattr(self, 'logger') and self.logger:
                self.logger.info(f"Bot {bot_data.get('name')} status changed to: {new_status}")
                
        except Exception as e:
            QMessageBox.critical(self, "Błąd", f"Nie udało się zmienić statusu bota: {str(e)}")
            if hasattr(self, 'logger') and self.logger:
                self.logger.error(f"Failed to toggle bot status: {e}")
    
    def delete_bot(self, bot_data: Dict):
        """Usuwa bota"""
        try:
            from PyQt6.QtWidgets import QMessageBox
            reply = QMessageBox.question(
                self, 
                "Potwierdzenie", 
                f"Czy na pewno chcesz usunąć bota '{bot_data.get('name')}'?",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                QMessageBox.StandardButton.No
            )
            
            if reply == QMessageBox.StandardButton.Yes:
                # Usuń z listy botów
                self.bots_data = [bot for bot in self.bots_data if bot.get("id") != bot_data.get("id")]
                
                # Odśwież wyświetlanie
                self.refresh_bots_display()
                
                QMessageBox.information(self, "Sukces", f"Bot '{bot_data.get('name')}' został usunięty.")
                
                if hasattr(self, 'logger') and self.logger:
                    self.logger.info(f"Deleted bot: {bot_data.get('name')}")
                    
        except Exception as e:
            QMessageBox.critical(self, "Błąd", f"Nie udało się usunąć bota: {str(e)}")
            if hasattr(self, 'logger') and self.logger:
                 self.logger.error(f"Failed to delete bot: {e}")
    
    def refresh_bots_display(self):
        """Odświeża wyświetlanie listy botów"""
        try:
            # Wyczyść obecny layout
            for i in reversed(range(self.bots_layout.count())):
                child = self.bots_layout.itemAt(i).widget()
                if child:
                    child.setParent(None)
            
            # Dodaj karty botów na nowo
            for bot_data in self.bots_data:
                bot_card = self.create_bot_card(bot_data)
                self.bots_layout.addWidget(bot_card)
            
            # Dodaj spacer na końcu
            self.bots_layout.addStretch()
            
            if hasattr(self, 'logger') and self.logger:
                self.logger.debug(f"Refreshed bots display with {len(self.bots_data)} bots")
                
        except Exception as e:
            print(f"Error refreshing bots display: {e}")
            if hasattr(self, 'logger') and self.logger:
                self.logger.error(f"Failed to refresh bots display: {e}")
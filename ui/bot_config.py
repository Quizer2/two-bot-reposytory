"""
Interfejs konfiguracji botów

Zawiera kreatory i edytory dla różnych typów botów handlowych.
"""

import sys
import json
import asyncio
import threading
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

        self.available_pairs = self._load_supported_pairs()
        self.strategy_definitions = self.get_strategy_definitions()

        # Przechowywanie stanu botów
        self.bots_data: List[Dict[str, Any]] = []

        try:
            self.setup_ui()
            self.reload_backend_state()
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
    
    def reload_backend_state(self):
        """Pobiera dane botów z warstwy zarządzania i aktualizuje widok."""
        try:
            self.bots_data = self._fetch_bots_from_backend()
        except Exception as exc:
            if self.logger:
                self.logger.error("Nie udało się pobrać danych botów: %s", exc)
            self.bots_data = []
        self.refresh_bots_display()

    def _fetch_bots_from_backend(self) -> List[Dict[str, Any]]:
        """Zwraca listę botów pobranych z UpdatedBotManager."""
        bots: List[Dict[str, Any]] = []
        try:
            from core.updated_bot_manager import get_updated_bot_manager
            manager = get_updated_bot_manager()
        except Exception as exc:
            if self.logger:
                self.logger.error("Błąd inicjalizacji UpdatedBotManager: %s", exc)
            return []

        if not manager:
            return []

        for bot_id, config in getattr(manager, 'bot_configs', {}).items():
            parameters = dict(getattr(config, 'parameters', {}) or {})
            trading_settings = dict(parameters.get('trading_settings', {}) or {})
            parameters.pop('trading_settings', None)

            status = 'stopped'
            profit = 0.0
            if bot_id in getattr(manager, 'active_bots', {}):
                active_bot = manager.active_bots[bot_id]
                status_value = getattr(active_bot, 'status', 'running')
                status = getattr(status_value, 'value', str(status_value))
                profit = float(getattr(active_bot, 'total_profit', 0.0) or 0.0)

            bots.append(
                {
                    'id': bot_id,
                    'name': getattr(config, 'name', bot_id),
                    'strategy': getattr(config.bot_type, 'value', str(getattr(config, 'bot_type', 'custom'))),
                    'pair': getattr(config, 'symbol', ''),
                    'status': status,
                    'profit': profit,
                    'parameters': parameters,
                    'trading_settings': trading_settings,
                }
            )

        return bots
    
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

            if not self.bots_data:
                placeholder = QLabel("Brak skonfigurowanych botów.")
                placeholder.setStyleSheet("color: #7f8c8d; font-style: italic; padding: 12px;")
                placeholder.setAlignment(Qt.AlignmentFlag.AlignCenter)
                self.bots_layout.addWidget(placeholder)
            else:
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
            type_widget = getattr(self, 'type_combo', QComboBox())
            selected_type = None
            if hasattr(type_widget, 'currentData'):
                selected_type = type_widget.currentData()
            pair_widget = getattr(self, 'pair_combo', QComboBox())
            selected_pair = pair_widget.currentText() if hasattr(pair_widget, 'currentText') else ""

            bot_data = {
                'name': getattr(self, 'name_input', QLineEdit()).text() or f"Bot_{len(self.bots_data) + 1}",
                'type': (selected_type or getattr(type_widget, 'currentText', lambda: "DCA")() or "DCA"),
                'pair': selected_pair or "BTC/USDT",
                'status': 'stopped',
                'id': len(self.bots_data) + 1,
                'pnl': 0.0,
                'created_at': datetime.now().isoformat()
            }

            # Dodaj dodatkowe parametry w zależności od typu bota
            if hasattr(self, 'amount_input'):
                amount_widget = getattr(self, 'amount_input')
                if isinstance(amount_widget, QDoubleSpinBox):
                    bot_data['amount'] = float(amount_widget.value())
                else:
                    try:
                        bot_data['amount'] = float(amount_widget.text() or "100")
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
        
        display_name = bot_data.get("name") or (f"Bot {bot_data.get('id')}" if bot_data.get('id') else "Nowy Bot")
        name_label = QLabel(display_name)
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
        strategy_code = (bot_data.get('strategy') or bot_data.get('type') or "").upper()
        strategy_label = QLabel(f"{strategy_code} • {bot_data.get('pair', 'N/A')}")
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
    
    def create_collapsible_section(self, title: str, content_widget: QWidget, *, expanded: bool = False) -> QFrame:
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
        header = QPushButton()
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

        # Domyślna widoczność
        content_container.setVisible(expanded)
        header.setText(f"{'▲' if expanded else '▼'} {title}")

        return section


    def _load_supported_pairs(self) -> List[str]:
        """Ładuje listę wspieranych par handlowych z konfiguracji."""

        fallback_pairs = ["BTC/USDT", "ETH/USDT", "BTC/EUR", "ETH/EUR"]
        try:
            if self.config_manager is None:
                return fallback_pairs

            pairs = self.config_manager.get_supported_trading_pairs()
            if pairs:
                return pairs
        except Exception as exc:
            if self.logger:
                self.logger.warning(f"Nie udało się pobrać listy par handlowych: {exc}")

        return fallback_pairs


    def get_strategy_definitions(self) -> Dict[str, Dict[str, Any]]:
        """Zwraca definicje dostępnych strategii oraz ich pola konfiguracyjne."""
        return {
            "dca": {
                "label": "DCA",
                "description": "Dollar Cost Averaging – cykliczne zakupy po ustalonym interwale.",
                "fields": [
                    {
                        "name": "interval_minutes",
                        "label": "Interwał zakupów (min)",
                        "type": "int",
                        "min": 5,
                        "max": 1440,
                        "step": 5,
                        "default": 60,
                    },
                    {
                        "name": "buy_amount",
                        "label": "Kwota pojedynczego zakupu (USDT)",
                        "type": "float",
                        "min": 1.0,
                        "max": 100000.0,
                        "decimals": 2,
                        "step": 1.0,
                        "default": 100.0,
                    },
                    {
                        "name": "take_profit",
                        "label": "Take profit (%)",
                        "type": "float",
                        "min": 0.1,
                        "max": 100.0,
                        "decimals": 2,
                        "step": 0.1,
                        "default": 2.0,
                        "suffix": "%",
                    },
                    {
                        "name": "stop_loss",
                        "label": "Stop loss (%)",
                        "type": "float",
                        "min": 0.1,
                        "max": 100.0,
                        "decimals": 2,
                        "step": 0.1,
                        "default": 5.0,
                        "suffix": "%",
                    },
                ],
            },
            "grid": {
                "label": "Grid",
                "description": "Strategia siatkowa z automatycznym rozmieszczeniem zleceń.",
                "fields": [
                    {
                        "name": "grid_size",
                        "label": "Liczba poziomów",
                        "type": "int",
                        "min": 2,
                        "max": 25,
                        "default": 6,
                    },
                    {
                        "name": "grid_spacing",
                        "label": "Rozstaw siatki (%)",
                        "type": "float",
                        "min": 0.1,
                        "max": 20.0,
                        "decimals": 2,
                        "step": 0.1,
                        "default": 0.8,
                        "suffix": "%",
                    },
                    {
                        "name": "price_floor",
                        "label": "Dolna granica ceny",
                        "type": "float",
                        "min": 0.0,
                        "max": 1000000.0,
                        "decimals": 4,
                        "step": 0.5,
                        "default": 1800.0,
                    },
                    {
                        "name": "price_ceiling",
                        "label": "Górna granica ceny",
                        "type": "float",
                        "min": 0.0,
                        "max": 1000000.0,
                        "decimals": 4,
                        "step": 0.5,
                        "default": 2200.0,
                    },
                ],
            },
            "scalping": {
                "label": "Scalping",
                "description": "Szybkie transakcje na podstawie wąskich progów zysku i stop loss.",
                "fields": [
                    {
                        "name": "profit_target",
                        "label": "Docelowy zysk (%)",
                        "type": "float",
                        "min": 0.1,
                        "max": 10.0,
                        "decimals": 2,
                        "step": 0.1,
                        "default": 0.5,
                        "suffix": "%",
                    },
                    {
                        "name": "stop_loss",
                        "label": "Stop loss (%)",
                        "type": "float",
                        "min": 0.1,
                        "max": 10.0,
                        "decimals": 2,
                        "step": 0.1,
                        "default": 0.3,
                        "suffix": "%",
                    },
                    {
                        "name": "cooldown_seconds",
                        "label": "Czas odnowienia (s)",
                        "type": "int",
                        "min": 5,
                        "max": 3600,
                        "step": 5,
                        "default": 30,
                    },
                ],
            },
            "swing": {
                "label": "Swing",
                "description": "Strategia swing trading z analizą trendu i zarządzaniem pozycją.",
                "fields": [
                    {
                        "name": "timeframe",
                        "label": "Interwał analizy",
                        "type": "select",
                        "options": ["1h", "4h", "1d"],
                        "default": "4h",
                    },
                    {
                        "name": "amount",
                        "label": "Kwota pozycji (USDT)",
                        "type": "float",
                        "min": 10.0,
                        "max": 100000.0,
                        "decimals": 2,
                        "step": 10.0,
                        "default": 500.0,
                    },
                    {
                        "name": "take_profit_ratio",
                        "label": "Take profit (RR)",
                        "type": "float",
                        "min": 0.5,
                        "max": 10.0,
                        "decimals": 2,
                        "step": 0.1,
                        "default": 2.0,
                    },
                    {
                        "name": "stop_loss_percentage",
                        "label": "Stop loss (%)",
                        "type": "float",
                        "min": 0.1,
                        "max": 20.0,
                        "decimals": 2,
                        "step": 0.1,
                        "default": 1.5,
                        "suffix": "%",
                    },
                    {
                        "name": "short_window",
                        "label": "Krótkie okno średniej",
                        "type": "int",
                        "min": 3,
                        "max": 50,
                        "default": 5,
                    },
                    {
                        "name": "long_window",
                        "label": "Długie okno średniej",
                        "type": "int",
                        "min": 6,
                        "max": 200,
                        "default": 20,
                    },
                ],
            },
            "momentum": {
                "label": "Momentum",
                "description": "Wykorzystuje różnicę pomiędzy szybką i wolną średnią kroczącą do łapania trendów.",
                "fields": [
                    {
                        "name": "short_window",
                        "label": "Szybka średnia (świece)",
                        "type": "int",
                        "min": 3,
                        "max": 120,
                        "default": 8,
                    },
                    {
                        "name": "long_window",
                        "label": "Wolna średnia (świece)",
                        "type": "int",
                        "min": 6,
                        "max": 360,
                        "default": 21,
                    },
                    {
                        "name": "momentum_threshold",
                        "label": "Próg momentum (%)",
                        "type": "float",
                        "min": 0.05,
                        "max": 5.0,
                        "decimals": 2,
                        "step": 0.05,
                        "default": 0.25,
                        "suffix": "%",
                    },
                    {
                        "name": "trade_amount",
                        "label": "Kwota transakcji (USDT)",
                        "type": "float",
                        "min": 10.0,
                        "max": 100000.0,
                        "decimals": 2,
                        "step": 10.0,
                        "default": 250.0,
                    },
                    {
                        "name": "cooldown_seconds",
                        "label": "Minimalny czas między transakcjami (s)",
                        "type": "int",
                        "min": 10,
                        "max": 3600,
                        "step": 5,
                        "default": 60,
                    },
                ],
            },
            "mean_reversion": {
                "label": "Mean Reversion",
                "description": "Poluje na odchylenia od średniej i gra na powrót ceny do równowagi.",
                "fields": [
                    {
                        "name": "lookback_window",
                        "label": "Okno średniej (świece)",
                        "type": "int",
                        "min": 5,
                        "max": 360,
                        "default": 30,
                    },
                    {
                        "name": "deviation_threshold",
                        "label": "Próg odchylenia (%)",
                        "type": "float",
                        "min": 0.1,
                        "max": 5.0,
                        "decimals": 2,
                        "step": 0.05,
                        "default": 1.0,
                        "suffix": "%",
                    },
                    {
                        "name": "trade_amount",
                        "label": "Kwota transakcji (USDT)",
                        "type": "float",
                        "min": 10.0,
                        "max": 100000.0,
                        "decimals": 2,
                        "step": 10.0,
                        "default": 300.0,
                    },
                    {
                        "name": "max_position_minutes",
                        "label": "Maks. czas pozycji (min)",
                        "type": "int",
                        "min": 15,
                        "max": 1440,
                        "step": 5,
                        "default": 240,
                    },
                    {
                        "name": "position_scaling",
                        "label": "Skalowanie pozycji",
                        "type": "bool",
                        "default": False,
                    },
                ],
            },
            "breakout": {
                "label": "Breakout",
                "description": "Monitoruje konsolidacje i dołącza do ruchu po wybiciu z zakresu.",
                "fields": [
                    {
                        "name": "lookback_window",
                        "label": "Zakres analizy (świece)",
                        "type": "int",
                        "min": 10,
                        "max": 360,
                        "default": 40,
                    },
                    {
                        "name": "breakout_buffer",
                        "label": "Bufor wybicia (%)",
                        "type": "float",
                        "min": 0.1,
                        "max": 5.0,
                        "decimals": 2,
                        "step": 0.05,
                        "default": 0.3,
                        "suffix": "%",
                    },
                    {
                        "name": "trade_amount",
                        "label": "Kwota transakcji (USDT)",
                        "type": "float",
                        "min": 10.0,
                        "max": 100000.0,
                        "decimals": 2,
                        "step": 10.0,
                        "default": 350.0,
                    },
                    {
                        "name": "trailing_stop_percentage",
                        "label": "Trailing stop (%)",
                        "type": "float",
                        "min": 0.1,
                        "max": 10.0,
                        "decimals": 2,
                        "step": 0.1,
                        "default": 0.8,
                        "suffix": "%",
                    },
                    {
                        "name": "confirmation_candles",
                        "label": "Świece potwierdzenia",
                        "type": "int",
                        "min": 1,
                        "max": 10,
                        "step": 1,
                        "default": 2,
                    },
                ],
            },
            "arbitrage": {
                "label": "Arbitrage",
                "description": "Strategia arbitrażu między giełdami z kontrolą spreadu.",
                "fields": [
                    {
                        "name": "exchanges",
                        "label": "Giełdy (lista)",
                        "type": "text",
                        "default": "Binance, Kraken",
                        "placeholder": "np. Binance, Kraken, Coinbase",
                    },
                    {
                        "name": "min_spread_percentage",
                        "label": "Minimalny spread (%)",
                        "type": "float",
                        "min": 0.1,
                        "max": 10.0,
                        "decimals": 2,
                        "step": 0.1,
                        "default": 0.5,
                        "suffix": "%",
                    },
                    {
                        "name": "max_slippage_percentage",
                        "label": "Maks. poślizg (%)",
                        "type": "float",
                        "min": 0.05,
                        "max": 5.0,
                        "decimals": 2,
                        "step": 0.05,
                        "default": 0.25,
                        "suffix": "%",
                    },
                    {
                        "name": "trade_amount",
                        "label": "Kwota transakcji (USDT)",
                        "type": "float",
                        "min": 10.0,
                        "max": 100000.0,
                        "decimals": 2,
                        "step": 10.0,
                        "default": 100.0,
                    },
                ],
            },
            "ai": {
                "label": "AI",
                "description": "Strategia AI wykorzystująca modele ML do adaptacyjnego handlu.",
                "fields": [
                    {
                        "name": "target_hourly_profit",
                        "label": "Docelowy zysk godzinowy (USDT)",
                        "type": "float",
                        "min": 0.1,
                        "max": 1000.0,
                        "decimals": 2,
                        "step": 0.1,
                        "default": 2.0,
                    },
                    {
                        "name": "risk_tolerance",
                        "label": "Tolerancja ryzyka",
                        "type": "float",
                        "min": 0.001,
                        "max": 0.2,
                        "decimals": 3,
                        "step": 0.001,
                        "default": 0.02,
                    },
                    {
                        "name": "learning_rate",
                        "label": "Learning rate",
                        "type": "float",
                        "min": 0.0001,
                        "max": 0.05,
                        "decimals": 4,
                        "step": 0.0005,
                        "default": 0.001,
                    },
                    {
                        "name": "model_update_frequency",
                        "label": "Aktualizacja modelu (transakcje)",
                        "type": "int",
                        "min": 10,
                        "max": 1000,
                        "step": 10,
                        "default": 100,
                    },
                    {
                        "name": "daily_loss_limit",
                        "label": "Dzienne ograniczenie straty (USDT)",
                        "type": "float",
                        "min": 10.0,
                        "max": 100000.0,
                        "decimals": 2,
                        "step": 5.0,
                        "default": 50.0,
                    },
                    {
                        "name": "learning_enabled",
                        "label": "Włącz uczenie adaptacyjne",
                        "type": "bool",
                        "default": True,
                    },
                    {
                        "name": "use_reinforcement_learning",
                        "label": "Użyj reinforcement learning",
                        "type": "bool",
                        "default": False,
                    },
                    {
                        "name": "feature_engineering_enabled",
                        "label": "Zaawansowana inżynieria cech",
                        "type": "bool",
                        "default": True,
                    },
                    {
                        "name": "sentiment_analysis_enabled",
                        "label": "Analiza sentymentu",
                        "type": "bool",
                        "default": False,
                    },
                    {
                        "name": "ensemble_models",
                        "label": "Łączenie modeli",
                        "type": "bool",
                        "default": False,
                    },
                ],
            },
            "custom": {
                "label": "Custom",
                "description": "Własna strategia definiowana przez użytkownika lub skrypty.",
                "fields": [],
            },
        }

    def _create_strategy_field_widget(self, field_spec: Dict[str, Any], value: Optional[Any]):
        """Buduje widget dla pola strategii."""
        field_type = field_spec.get("type", "text")
        effective_value = value if value is not None else field_spec.get("default")

        if field_type == "int":
            widget = QSpinBox()
            widget.setRange(field_spec.get("min", 0), field_spec.get("max", 100000))
            if "step" in field_spec:
                widget.setSingleStep(field_spec["step"])
            widget.setValue(int(effective_value if effective_value is not None else 0))
            widget.setStyleSheet("padding: 4px; border: 1px solid #bdc3c7; border-radius: 3px;")
            return widget

        if field_type == "float":
            widget = QDoubleSpinBox()
            widget.setRange(field_spec.get("min", 0.0), field_spec.get("max", 1000000.0))
            widget.setDecimals(field_spec.get("decimals", 2))
            widget.setSingleStep(field_spec.get("step", 0.1))
            if field_spec.get("suffix") == "%" and effective_value is not None and abs(float(effective_value)) <= 1:
                effective_value = float(effective_value) * 100.0
            widget.setValue(float(effective_value if effective_value is not None else 0.0))
            if field_spec.get("suffix"):
                widget.setSuffix(str(field_spec["suffix"]))
            widget.setStyleSheet("padding: 4px; border: 1px solid #bdc3c7; border-radius: 3px;")
            return widget

        if field_type == "bool":
            widget = QCheckBox()
            widget.setChecked(bool(effective_value))
            return widget

        if field_type in {"choice", "select"}:
            widget = QComboBox()
            choices = field_spec.get("choices") or field_spec.get("options", [])
            widget.addItems(choices)
            if effective_value in choices:
                widget.setCurrentText(str(effective_value))
            widget.setStyleSheet("padding: 4px; border: 1px solid #bdc3c7; border-radius: 3px;")
            return widget

        widget = QLineEdit()
        widget.setText(str(effective_value or ""))
        if field_spec.get("placeholder"):
            widget.setPlaceholderText(str(field_spec["placeholder"]))
        widget.setStyleSheet("padding: 4px; border: 1px solid #bdc3c7; border-radius: 3px;")
        return widget

    def _collect_strategy_field_values(self, strategy_state: Dict[str, Any]) -> Dict[str, Any]:
        """Pobiera wartości z aktualnych pól konfiguracji strategii."""
        values: Dict[str, Any] = {}
        widgets = strategy_state.get("widgets", {})
        specs = {spec["name"]: spec for spec in strategy_state.get("specs", [])}

        for field_name, widget in widgets.items():
            spec = specs.get(field_name, {})
            field_type = spec.get("type", "text")

            if isinstance(widget, QSpinBox):
                values[field_name] = int(widget.value())
            elif isinstance(widget, QDoubleSpinBox):
                raw_value = float(widget.value())
                if spec.get("suffix") == "%":
                    values[field_name] = raw_value / 100.0
                else:
                    values[field_name] = raw_value
            elif isinstance(widget, QCheckBox):
                values[field_name] = widget.isChecked()
            elif isinstance(widget, QComboBox):
                values[field_name] = widget.currentText()
            else:
                values[field_name] = widget.text()

        return values

    def _compose_parameters(
        self,
        strategy_key: str,
        strategy_values: Dict[str, Any],
        trading_values: Dict[str, Any],
        symbol: str,
    ) -> Dict[str, Any]:
        params = dict(strategy_values)

        if strategy_key == "dca":
            if trading_values.get("amount") is not None:
                params.setdefault("buy_amount", trading_values["amount"])
            interval_minutes = params.get("interval_minutes")
            if interval_minutes is None and trading_values.get("interval"):
                interval_minutes = self._parse_interval_to_minutes(trading_values["interval"])
            if interval_minutes:
                params["interval_minutes"] = interval_minutes
            if "take_profit" not in params and trading_values.get("take_profit") is not None:
                params["take_profit"] = self._percentage_to_decimal(trading_values["take_profit"])
            if "stop_loss" not in params and trading_values.get("stop_loss") is not None:
                params["stop_loss"] = self._percentage_to_decimal(trading_values["stop_loss"])
        elif strategy_key == "scalping":
            if "profit_target" not in params and trading_values.get("take_profit") is not None:
                params["profit_target"] = self._percentage_to_decimal(trading_values["take_profit"])
            if "stop_loss" not in params and trading_values.get("stop_loss") is not None:
                params["stop_loss"] = self._percentage_to_decimal(trading_values["stop_loss"])
        elif strategy_key == "swing":
            if trading_values.get("amount") is not None and "amount" not in params:
                params["amount"] = trading_values["amount"]
            stop_loss_value = params.get("stop_loss_percentage")
            if stop_loss_value is not None and stop_loss_value < 1:
                params["stop_loss_percentage"] = stop_loss_value * 100
        elif strategy_key == "arbitrage":
            exchanges_value = params.get("exchanges")
            if isinstance(exchanges_value, str):
                params["exchanges"] = [segment.strip() for segment in exchanges_value.split(',') if segment.strip()]
            elif exchanges_value is None:
                params["exchanges"] = []
            for key in ("min_spread_percentage", "max_slippage_percentage"):
                value = params.get(key)
                if value is not None and value < 1:
                    params[key] = value * 100
            if trading_values.get("amount") is not None and "trade_amount" not in params:
                params["trade_amount"] = trading_values["amount"]
        elif strategy_key == "ai":
            params.setdefault("pair", symbol)
            if trading_values.get("amount") is not None:
                params.setdefault("budget", trading_values["amount"])
        elif strategy_key in {"momentum", "mean_reversion", "breakout"}:
            if trading_values.get("amount") is not None and "trade_amount" not in params:
                params["trade_amount"] = trading_values["amount"]
            if strategy_key == "mean_reversion" and trading_values.get("max_position_minutes") is not None and "max_position_minutes" not in params:
                params["max_position_minutes"] = trading_values["max_position_minutes"]
            if strategy_key == "breakout" and trading_values.get("take_profit") is not None and "trailing_stop_percentage" not in params:
                params["trailing_stop_percentage"] = self._percentage_to_decimal(trading_values["take_profit"])

        return params

    def _parse_interval_to_minutes(self, interval: Any) -> int:
        if interval is None:
            return 0
        if isinstance(interval, (int, float)):
            return int(interval)
        label = str(interval).strip().lower()
        if label.endswith("m"):
            return int(float(label[:-1] or 0))
        if label.endswith("h"):
            return int(float(label[:-1] or 0) * 60)
        if label.endswith("d"):
            return int(float(label[:-1] or 0) * 1440)
        try:
            return int(float(label))
        except ValueError:
            return 0

    def _format_interval_from_minutes(self, minutes: Any) -> str:
        try:
            minutes = int(minutes)
        except (TypeError, ValueError):
            return "5m"
        if minutes <= 0:
            return "5m"
        if minutes % 1440 == 0:
            days = minutes // 1440
            return f"{max(days, 1)}d"
        if minutes % 60 == 0:
            hours = minutes // 60
            return f"{max(hours, 1)}h"
        return f"{minutes}m"

    def _percentage_to_decimal(self, value: Any) -> float:
        if value is None:
            return 0.0
        return float(value) / 100.0

    def _decimal_to_percentage(self, value: Any) -> Optional[float]:
        if value is None:
            return None
        try:
            return float(value) * 100.0
        except (TypeError, ValueError):
            return None

    def _persist_bot_config(self, payload: Dict[str, Any]) -> bool:
        try:
            from core.integrated_data_manager import get_integrated_data_manager

            manager = get_integrated_data_manager()
            if not manager:
                raise RuntimeError("IntegratedDataManager is unavailable")

            try:
                return asyncio.run(manager.create_bot(payload))
            except RuntimeError:
                import threading

                result: Dict[str, Any] = {}

                def runner():
                    result["value"] = asyncio.run(manager.create_bot(payload))

                thread = threading.Thread(target=runner, daemon=True)
                thread.start()
                thread.join()
                return bool(result.get("value"))

        except Exception as exc:
            if self.logger:
                self.logger.error("Persisting bot config failed: %s", exc)
            raise
    
    def create_bot_config_form(self, bot_data: Dict) -> QWidget:
        """Tworzy formularz konfiguracji bota"""
        form_widget = QWidget()
        form_layout = QVBoxLayout(form_widget)
        form_layout.setSpacing(8)

        parameters = dict(bot_data.get("parameters", {}))
        trading_defaults = dict(bot_data.get("trading_settings", {}))
        
        # Podstawowe informacje
        basic_info = QWidget()
        basic_layout = QFormLayout(basic_info)
        basic_layout.setSpacing(4)
        
        # Nazwa bota
        name_edit = QLineEdit(bot_data.get("name", ""))
        name_edit.setStyleSheet("padding: 4px; border: 1px solid #bdc3c7; border-radius: 3px;")
        basic_layout.addRow("Nazwa:", name_edit)
        self.name_input = name_edit

        # Typ strategii
        strategy_combo = QComboBox()
        available_strategies = list(self.strategy_definitions.keys())
        for key in available_strategies:
            meta = self.strategy_definitions[key]
            strategy_combo.addItem(meta.get("label", key.capitalize()), userData=key)

        current_strategy = (bot_data.get("strategy") or bot_data.get("type") or (available_strategies[0] if available_strategies else "")).lower()
        if current_strategy in available_strategies:
            index = strategy_combo.findData(current_strategy)
            if index >= 0:
                strategy_combo.setCurrentIndex(index)
        elif available_strategies:
            strategy_combo.setCurrentIndex(0)
            current_strategy = available_strategies[0]
        strategy_combo.setStyleSheet("padding: 4px; border: 1px solid #bdc3c7; border-radius: 3px;")
        basic_layout.addRow("Strategia:", strategy_combo)
        self.type_combo = strategy_combo

        # Para handlowa
        pair_combo = QComboBox()
        pair_combo.setEditable(True)
        if hasattr(QComboBox, "InsertPolicy"):
            try:
                pair_combo.setInsertPolicy(QComboBox.InsertPolicy.NoInsert)
            except Exception:
                pass
        for pair in self.available_pairs:
            pair_combo.addItem(pair)
        current_pair = bot_data.get("pair") or bot_data.get("symbol") or ""
        if current_pair:
            normalised_pair = str(current_pair).strip().upper().replace("-", "/").replace(" ", "")
            if normalised_pair not in self.available_pairs:
                pair_combo.addItem(normalised_pair)
            pair_combo.setCurrentText(normalised_pair)
        elif self.available_pairs:
            pair_combo.setCurrentIndex(0)
        pair_combo.setStyleSheet("padding: 4px; border: 1px solid #bdc3c7; border-radius: 3px;")
        basic_layout.addRow("Para:", pair_combo)
        self.pair_combo = pair_combo

        basic_section = self.create_collapsible_section("Podstawowe ustawienia", basic_info)
        form_layout.addWidget(basic_section)
        
        # Ustawienia handlowe
        trading_info = QWidget()
        trading_layout = QFormLayout(trading_info)
        trading_layout.setSpacing(4)
        
        # Kwota inwestycji
        amount_spin = QDoubleSpinBox()
        amount_spin.setRange(0.01, 100000.0)
        amount_value = trading_defaults.get("amount", parameters.get("buy_amount", 100.0))
        amount_spin.setValue(float(amount_value if amount_value is not None else 0.0))
        amount_spin.setStyleSheet("padding: 4px; border: 1px solid #bdc3c7; border-radius: 3px;")
        trading_layout.addRow("Kwota (USDT):", amount_spin)
        self.amount_input = amount_spin

        # Take Profit
        tp_spin = QDoubleSpinBox()
        tp_spin.setRange(0.1, 100.0)
        tp_default = trading_defaults.get("take_profit")
        if tp_default is None:
            tp_default = self._decimal_to_percentage(parameters.get("take_profit"))
        tp_spin.setValue(float(tp_default if tp_default is not None else 2.0))
        tp_spin.setSuffix("%")
        tp_spin.setStyleSheet("padding: 4px; border: 1px solid #bdc3c7; border-radius: 3px;")
        trading_layout.addRow("Take Profit:", tp_spin)

        # Stop Loss
        sl_spin = QDoubleSpinBox()
        sl_spin.setRange(0.1, 100.0)
        sl_default = trading_defaults.get("stop_loss")
        if sl_default is None:
            sl_default = self._decimal_to_percentage(parameters.get("stop_loss"))
        sl_spin.setValue(float(sl_default if sl_default is not None else 5.0))
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
        max_orders_spin.setValue(int(trading_defaults.get("max_orders", 10)))
        max_orders_spin.setStyleSheet("padding: 4px; border: 1px solid #bdc3c7; border-radius: 3px;")
        advanced_layout.addRow("Max. zlecenia:", max_orders_spin)

        # Interwał
        interval_combo = QComboBox()
        interval_options = ["1m", "5m", "15m", "1h", "4h", "1d"]
        interval_combo.addItems(interval_options)
        interval_value = trading_defaults.get("interval")
        if not interval_value:
            minutes = parameters.get("interval_minutes")
            if minutes is not None:
                interval_value = self._format_interval_from_minutes(minutes)
        if interval_value and interval_value in interval_options:
            interval_combo.setCurrentText(interval_value)
        else:
            interval_combo.setCurrentText("5m")
        interval_combo.setStyleSheet("padding: 4px; border: 1px solid #bdc3c7; border-radius: 3px;")
        advanced_layout.addRow("Interwał:", interval_combo)
        self.interval_combo = interval_combo
        
        advanced_section = self.create_collapsible_section("Ustawienia zaawansowane", advanced_info)
        form_layout.addWidget(advanced_section)

        # Parametry strategii
        strategy_info = QWidget()
        strategy_layout = QFormLayout(strategy_info)
        strategy_layout.setSpacing(4)

        strategy_state: Dict[str, Any] = {
            "widgets": {},
            "specs": [],
            "cache": {},
            "active": None,
            "initial_strategy": current_strategy,
            "initial_settings": dict(bot_data.get("parameters", {})),
        }

        def refresh_strategy_fields(strategy_key: Optional[str]):
            if not strategy_key:
                return
            # Zachowaj aktualne wartości strategii zanim przełączymy widok
            if strategy_state.get("active"):
                cached_values = self._collect_strategy_field_values(strategy_state)
                strategy_state.setdefault("cache", {})[strategy_state["active"]] = cached_values

            # Wyczyść obecne pola
            while strategy_layout.count():
                item = strategy_layout.takeAt(0)
                widget = item.widget()
                if widget:
                    widget.deleteLater()

            definition = self.strategy_definitions.get(strategy_key, {})
            strategy_state["specs"] = definition.get("fields", [])
            strategy_state["widgets"] = {}
            strategy_state["active"] = strategy_key

            description = definition.get("description")
            if description:
                description_label = QLabel(description)
                description_label.setWordWrap(True)
                description_label.setStyleSheet("color: #7f8c8d; font-size: 11px;")
                strategy_layout.addRow(description_label)

            if not strategy_state["specs"]:
                empty_label = QLabel("Brak dodatkowych pól konfiguracyjnych dla tej strategii.")
                empty_label.setStyleSheet("color: #7f8c8d; font-style: italic;")
                strategy_layout.addRow(empty_label)
                return

            existing_settings = {}
            cache = strategy_state.get("cache", {})
            if strategy_key in cache:
                existing_settings = dict(cache[strategy_key])
            elif strategy_key == strategy_state.get("initial_strategy"):
                existing_settings = dict(strategy_state.get("initial_settings", {}))
            else:
                existing_settings = {}

            for field_spec in strategy_state["specs"]:
                field_name = field_spec.get("name")
                widget = self._create_strategy_field_widget(
                    field_spec,
                    existing_settings.get(field_name),
                )
                strategy_state["widgets"][field_name] = widget
                label_text = field_spec.get("label", field_name)
                strategy_layout.addRow(f"{label_text}:", widget)

        if available_strategies:
            refresh_strategy_fields(strategy_combo.currentData() or available_strategies[0])
        strategy_combo.currentIndexChanged.connect(lambda _: refresh_strategy_fields(strategy_combo.currentData()))

        strategy_section = self.create_collapsible_section(
            "Parametry strategii",
            strategy_info,
            expanded=True,
        )
        form_layout.addWidget(strategy_section)
        
        # Przygotowanie stanu formularza do zapisu
        form_state: Dict[str, Any] = {
            "name": name_edit,
            "pair": pair_combo,
            "strategy_combo": strategy_combo,
            "amount": amount_spin,
            "take_profit": tp_spin,
            "stop_loss": sl_spin,
            "max_orders": max_orders_spin,
            "interval": interval_combo,
            "strategy_state": strategy_state,
        }

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
        save_btn.clicked.connect(lambda: self.save_bot_config(bot_data, form_state))
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
    
    def save_bot_config(self, bot_data: Dict, form_state: Dict[str, Any]):
        """Zapisuje konfigurację bota wraz z parametrami strategii."""
        try:
            name_widget = form_state.get("name") if form_state else None
            pair_widget = form_state.get("pair") if form_state else None
            strategy_combo = form_state.get("strategy_combo") if form_state else None
            strategy_state = form_state.get("strategy_state", {}) if form_state else {}

            name_value = name_widget.text().strip() if isinstance(name_widget, QLineEdit) else bot_data.get("name", "")
            if not name_value:
                name_value = bot_data.get("name", f"Bot_{bot_data.get('id', len(self.bots_data) + 1)}")

            pair_value = pair_widget.text().strip() if isinstance(pair_widget, QLineEdit) else bot_data.get("pair", "")

            selected_strategy_key = strategy_combo.currentData() if isinstance(strategy_combo, QComboBox) else (bot_data.get("strategy") or bot_data.get("type") or "dca")
            if not selected_strategy_key:
                selected_strategy_key = "dca"

            strategy_settings = self._collect_strategy_field_values(strategy_state)
            if strategy_state is not None:
                strategy_state.setdefault("cache", {})[selected_strategy_key] = dict(strategy_settings)

            amount_widget = form_state.get("amount") if form_state else None
            tp_widget = form_state.get("take_profit") if form_state else None
            sl_widget = form_state.get("stop_loss") if form_state else None
            max_orders_widget = form_state.get("max_orders") if form_state else None
            interval_widget = form_state.get("interval") if form_state else None

            trading_settings = {
                "amount": float(amount_widget.value()) if isinstance(amount_widget, QDoubleSpinBox) else bot_data.get("trading_settings", {}).get("amount", 0.0),
                "take_profit": float(tp_widget.value()) if isinstance(tp_widget, QDoubleSpinBox) else bot_data.get("trading_settings", {}).get("take_profit"),
                "stop_loss": float(sl_widget.value()) if isinstance(sl_widget, QDoubleSpinBox) else bot_data.get("trading_settings", {}).get("stop_loss"),
                "interval": interval_widget.currentText() if isinstance(interval_widget, QComboBox) else bot_data.get("trading_settings", {}).get("interval"),
                "max_orders": int(max_orders_widget.value()) if isinstance(max_orders_widget, QSpinBox) else bot_data.get("trading_settings", {}).get("max_orders"),
            }
            parameters_payload = self._compose_parameters(selected_strategy_key, strategy_settings, trading_settings, pair_value)

            payload = {
                "id": bot_data.get("id"),
                "name": name_value,
                "symbol": pair_value,
                "strategy": selected_strategy_key,
                "parameters": parameters_payload,
                "trading_settings": trading_settings,
            }

            success = self._persist_bot_config(payload)

            if success and self.logger:
                self.logger.info(
                    "Zapisano konfigurację bota %s (%s)",
                    payload["name"],
                    selected_strategy_key,
                )

            if success:
                self.reload_backend_state()
                QMessageBox.information(
                    self,
                    "Zapisano",
                    f"Konfiguracja bota '{payload['name']}' została zapisana.",
                )
            else:
                raise RuntimeError("Persisting bot configuration zwróciło False")
        except Exception as exc:
            error_message = f"Nie udało się zapisać konfiguracji bota: {exc}"
            print(error_message)
            if self.logger:
                self.logger.error(error_message)
            QMessageBox.information(self, "Błąd", error_message)
        finally:
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
            new_bot_data = {
                "id": None,
                "name": "",
                "strategy": "dca",
                "pair": "",
                "status": "stopped",
                "parameters": {},
                "trading_settings": {},
            }

            self.edit_bot(new_bot_data)

            if hasattr(self, 'logger') and self.logger:
                self.logger.info("Opened configurator for new bot")

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
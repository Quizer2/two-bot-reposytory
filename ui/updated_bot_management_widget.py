"""
Updated Bot Management Widget - Zintegrowany z nową architekturą

Widget zarządzania botami używający IntegratedDataManager i UpdatedBotManager
dla spójnego przepływu danych.
"""

import sys
import asyncio
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Tuple
from decimal import Decimal

from utils.qt_compat import load_qt_names

_QT_IMPORTS = {
    "QtWidgets": (
        "QWidget",
        "QVBoxLayout",
        "QHBoxLayout",
        "QGridLayout",
        "QFormLayout",
        "QLabel",
        "QPushButton",
        "QFrame",
        "QScrollArea",
        "QTabWidget",
        "QTableWidget",
        "QTableWidgetItem",
        "QHeaderView",
        "QComboBox",
        "QLineEdit",
        "QSpinBox",
        "QDoubleSpinBox",
        "QCheckBox",
        "QGroupBox",
        "QTextEdit",
        "QProgressBar",
        "QSplitter",
        "QTreeWidget",
        "QTreeWidgetItem",
        "QMessageBox",
        "QMenu",
        "QFileDialog",
        "QDateEdit",
        "QApplication",
        "QDialog",
        "QDialogButtonBox",
        "QAbstractItemView",
        "QSizePolicy",
    ),
    "QtCore": (
        "Qt",
        "QTimer",
        "pyqtSignal",
        "QSize",
        "QDate",
        "QPropertyAnimation",
        "QEasingCurve",
        "QParallelAnimationGroup",
        "QThread",
        "pyqtSlot",
    ),
    "QtGui": (
        "QFont",
        "QPixmap",
        "QIcon",
        "QPalette",
        "QColor",
        "QPainter",
        "QPen",
        "QBrush",
        "QLinearGradient",
        "QAction",
        "QContextMenuEvent",
    ),
}

PYQT_AVAILABLE, _qt_objects = load_qt_names(_QT_IMPORTS)
globals().update(_qt_objects)
del _qt_objects

import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from utils.config_manager import get_config_manager, get_ui_setting, get_app_setting
from utils.logger import get_logger, LogType
from utils.helpers import FormatHelper, CalculationHelper

try:
    from ui.styles import COLORS
except ImportError:
    COLORS = {
        'primary': '#667eea',
        'secondary': '#764ba2'
    }

# Import UI components
try:
    from ui.flow_layout import FlowLayout
    FLOW_LAYOUT_AVAILABLE = True
except ImportError:
    FLOW_LAYOUT_AVAILABLE = False

STRATEGY_DISPLAY_NAMES = {
    "dca": "DCA",
    "grid": "Grid Trading",
    "scalping": "Scalping",
    "swing": "Swing Trading",
    "arbitrage": "Arbitrage",
    "ai": "AI",
    "custom": "Custom",
    "momentum": "Momentum",
    "mean_reversion": "Mean Reversion",
    "meanreversion": "Mean Reversion",
    "breakout": "Breakout",
    "breakout_bot": "Breakout",
}


def format_strategy_label(value: Any) -> str:
    if value is None:
        return "N/A"
    text = str(value).strip()
    if not text:
        return "N/A"
    normalized = text.lower().replace('-', '_').replace(' ', '_')
    return STRATEGY_DISPLAY_NAMES.get(normalized, text)


class BotCard(QWidget):
    """Karta pojedynczego bota z nowoczesnym designem"""
    
    start_bot_signal = pyqtSignal(str)
    stop_bot_signal = pyqtSignal(str)
    edit_bot_signal = pyqtSignal(str)
    delete_bot_signal = pyqtSignal(str)
    
    def __init__(self, bot_id: str, bot_data: Dict[str, Any], parent=None):
        super().__init__(parent)
        self.bot_id = bot_id
        self.bot_data = bot_data
        self.setup_ui()
        self.apply_style()
        self.update_data(bot_data)

    @staticmethod
    def _format_symbol(value: Any) -> str:
        if not value:
            return "N/A"
        return str(value).strip().upper().replace('-', '/').replace(' ', '') or "N/A"

    def setup_ui(self):
        """Konfiguracja UI karty bota"""
        self.setObjectName("botCard")
        layout = QVBoxLayout(self)
        layout.setContentsMargins(15, 15, 15, 15)
        layout.setSpacing(12)
        
        # Header z nazwą i statusem
        header_layout = QHBoxLayout()
        
        # Nazwa bota
        self.name_label = QLabel(self.bot_data.get('name', 'Unknown Bot'))
        self.name_label.setObjectName("botName")
        header_layout.addWidget(self.name_label)
        
        header_layout.addStretch()
        
        # Status indicator
        self.status_indicator = QLabel("●")
        self.status_indicator.setObjectName("statusIndicator")
        header_layout.addWidget(self.status_indicator)
        
        layout.addLayout(header_layout)
        
        # Informacje o bocie
        info_layout = QGridLayout()
        info_layout.setSpacing(8)
        
        # Strategia
        strategy_label = QLabel("Strategia:")
        strategy_label.setObjectName("infoLabel")
        self.strategy_value = QLabel(format_strategy_label(self.bot_data.get('strategy', 'N/A')))
        self.strategy_value.setObjectName("infoValue")
        info_layout.addWidget(strategy_label, 0, 0)
        info_layout.addWidget(self.strategy_value, 0, 1)

        # Para handlowa
        symbol_label = QLabel("Para:")
        symbol_label.setObjectName("infoLabel")
        self.symbol_value = QLabel(self._format_symbol(self.bot_data.get('symbol', 'N/A')))
        self.symbol_value.setObjectName("infoValue")
        info_layout.addWidget(symbol_label, 1, 0)
        info_layout.addWidget(self.symbol_value, 1, 1)
        
        # P&L
        pnl_label = QLabel("P&L:")
        pnl_label.setObjectName("infoLabel")
        self.pnl_value = QLabel("$0.00")
        self.pnl_value.setObjectName("pnlValue")
        info_layout.addWidget(pnl_label, 2, 0)
        info_layout.addWidget(self.pnl_value, 2, 1)
        
        # Liczba transakcji
        trades_label = QLabel("Transakcje:")
        trades_label.setObjectName("infoLabel")
        self.trades_value = QLabel("0")
        self.trades_value.setObjectName("infoValue")
        info_layout.addWidget(trades_label, 3, 0)
        info_layout.addWidget(self.trades_value, 3, 1)
        
        layout.addLayout(info_layout)
        
        # Przyciski akcji
        buttons_layout = QHBoxLayout()
        buttons_layout.setSpacing(8)
        
        self.start_stop_btn = QPushButton()
        self.start_stop_btn.setObjectName("actionButton")
        self.start_stop_btn.clicked.connect(self.toggle_bot)
        buttons_layout.addWidget(self.start_stop_btn)
        
        edit_btn = QPushButton("⚙️")
        edit_btn.setObjectName("iconButton")
        edit_btn.setToolTip("Edytuj konfigurację")
        edit_btn.clicked.connect(lambda: self.edit_bot_signal.emit(self.bot_id))
        buttons_layout.addWidget(edit_btn)
        
        delete_btn = QPushButton("🗑️")
        delete_btn.setObjectName("iconButton")
        delete_btn.setToolTip("Usuń bota")
        delete_btn.clicked.connect(lambda: self.delete_bot_signal.emit(self.bot_id))
        buttons_layout.addWidget(delete_btn)
        
        layout.addLayout(buttons_layout)
    
    def apply_style(self):
        """Zastosuj style do karty"""
        primary = COLORS.get('primary', '#667eea')
        secondary = COLORS.get('secondary', '#764ba2')

        self.setStyleSheet(
            f"""
            QWidget {{
                background-color: #1a1a1a;
                border: 1px solid #2a2a2a;
                border-radius: 12px;
                margin: 5px;
                color: #eaeaea;
            }}
            QWidget:hover {{
                border-color: {primary};
            }}
            QLabel#botName {{
                font-size: 16px;
                font-weight: bold;
                color: #ffffff;
            }}
            QLabel#statusIndicator {{
                font-size: 20px;
                margin-left: 5px;
            }}
            QLabel#infoLabel {{
                font-size: 12px;
                color: #c9c9c9;
                font-weight: 500;
            }}
            QLabel#infoValue {{
                font-size: 12px;
                color: #f0f0f0;
            }}
            QLabel#pnlValue {{
                font-size: 12px;
                font-weight: 600;
            }}
            QPushButton#actionButton {{
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                    stop:0 {primary}, stop:1 {secondary});
                color: white;
                border: none;
                border-radius: 10px;
                padding: 8px 18px;
                font-weight: 600;
                min-width: 120px;
                min-height: 36px;
            }}
            QPushButton#actionButton:hover {{
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                    stop:0 rgba(102, 126, 234, 0.9), stop:1 rgba(118, 75, 162, 0.9));
            }}
            QPushButton#iconButton {{
                background: rgba(102, 126, 234, 0.08);
                border: none;
                color: {primary};
                font-size: 16px;
                padding: 6px 10px;
                min-width: 34px;
                min-height: 34px;
                border-radius: 8px;
            }}
            QPushButton#iconButton:hover {{
                background: rgba(102, 126, 234, 0.16);
            }}
            """
        )
        self._start_button_style = (
            f"""
            QPushButton#actionButton {{
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                    stop:0 {primary}, stop:1 {secondary});
                color: white;
                border: none;
                border-radius: 10px;
                padding: 8px 18px;
                font-weight: 600;
                min-width: 120px;
                min-height: 36px;
            }}
            QPushButton#actionButton:hover {{
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                    stop:0 rgba(102, 126, 234, 0.9), stop:1 rgba(118, 75, 162, 0.9));
            }}
            """
        )
        self._stop_button_style = """
            QPushButton#actionButton {
                background-color: #667eea;
                color: white;
                border: none;
                border-radius: 8px;
                padding: 6px 12px;
                font-weight: 600;
                min-width: 60px;
            }
            QPushButton#actionButton:hover {
                background-color: #576bd6;
            }
            QPushButton#actionButton:pressed {
                background-color: #4a5bc0;
            }
            QPushButton#iconButton {
                background-color: #2a2a2a;
                border: 1px solid #3a3a3a;
                border-radius: 6px;
                padding: 4px;
                min-width: 30px;
                max-width: 30px;
                min-height: 30px;
                max-height: 30px;
            }
            QPushButton#iconButton:hover {
                background-color: #3a3a3a;
            }
        """
        if hasattr(self, 'start_stop_btn'):
            self.start_stop_btn.setStyleSheet(self._start_button_style)
    
    def update_data(self, bot_data: Dict[str, Any]):
        """Aktualizuj dane karty"""
        self.bot_data = bot_data
        
        # Nazwa
        self.name_label.setText(bot_data.get('name', 'Unknown Bot'))
        
        # Status
        status = bot_data.get('status', 'stopped')
        if status == 'running':
            self.status_indicator.setStyleSheet("color: #4CAF50;")
            self.start_stop_btn.setText("⏸️ Stop")
            if hasattr(self, '_stop_button_style'):
                self.start_stop_btn.setStyleSheet(self._stop_button_style)
        elif status == 'error':
            self.status_indicator.setStyleSheet("color: #FF9800;")
            self.start_stop_btn.setText("▶️ Start")
            if hasattr(self, '_start_button_style'):
                self.start_stop_btn.setStyleSheet(self._start_button_style)
        else:  # stopped
            self.status_indicator.setStyleSheet("color: #9E9E9E;")
            self.start_stop_btn.setText("▶️ Start")
            if hasattr(self, '_start_button_style'):
                self.start_stop_btn.setStyleSheet(self._start_button_style)
        
        # Strategia
        self.strategy_value.setText(format_strategy_label(bot_data.get('strategy', 'N/A')))

        # Para
        self.symbol_value.setText(self._format_symbol(bot_data.get('symbol', 'N/A')))
        
        # P&L
        pnl = bot_data.get('pnl', 0.0)
        pnl_color = "#4CAF50" if pnl >= 0 else "#F44336"
        pnl_sign = "+" if pnl >= 0 else ""
        self.pnl_value.setText(f"{pnl_sign}${pnl:.2f}")
        self.pnl_value.setStyleSheet(f"color: {pnl_color}; font-weight: 600;")
        
        # Transakcje
        trades = bot_data.get('trades_count', 0)
        self.trades_value.setText(str(trades))
    
    def toggle_bot(self):
        """Przełącz status bota"""
        status = self.bot_data.get('status', 'stopped')
        if status == 'running':
            self.stop_bot_signal.emit(self.bot_id)
        else:
            self.start_bot_signal.emit(self.bot_id)

class BotConfigDialog(QDialog):
    """Dialog konfiguracji nowego bota"""
    
    def __init__(self, parent=None, bot_data=None):
        super().__init__(parent)
        self.bot_data = bot_data or {}
        self.setWindowTitle("Konfiguracja Bota" if not bot_data else "Edycja Bota")
        self.setModal(True)
        self.resize(500, 600)
        try:
            self.config_manager = get_config_manager()
        except Exception:
            self.config_manager = None
        self.supported_pairs = self._load_supported_pairs()
        self.setup_ui()

    def _load_supported_pairs(self) -> List[str]:
        fallback = ["BTC/USDT", "ETH/USDT", "BTC/EUR"]
        manager = getattr(self, "config_manager", None)
        if manager is None:
            return fallback
        try:
            pairs = manager.get_supported_trading_pairs()
            if pairs:
                return pairs
        except Exception:
            pass
        return fallback

    def setup_ui(self):
        """Konfiguracja UI dialogu"""
        layout = QVBoxLayout(self)
        
        # Scroll area
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        
        form_widget = QWidget()
        form_layout = QFormLayout(form_widget)
        form_layout.setSpacing(15)
        
        # Podstawowe ustawienia
        basic_group = QGroupBox("Podstawowe Ustawienia")
        basic_layout = QFormLayout(basic_group)
        
        self.name_edit = QLineEdit(self.bot_data.get('name', ''))
        self.name_edit.setPlaceholderText("Nazwa bota")
        basic_layout.addRow("Nazwa:", self.name_edit)
        
        self.exchange_combo = QComboBox()
        self.exchange_combo.addItems(["Binance", "Bybit", "OKX", "KuCoin"])
        self.exchange_combo.setCurrentText(self.bot_data.get('exchange', 'Binance'))
        basic_layout.addRow("Giełda:", self.exchange_combo)
        
        self.symbol_combo = QComboBox()
        self.symbol_combo.setEditable(True)
        if hasattr(QComboBox, "InsertPolicy"):
            try:
                self.symbol_combo.setInsertPolicy(QComboBox.InsertPolicy.NoInsert)
            except Exception:
                pass
        for pair in self.supported_pairs:
            self.symbol_combo.addItem(pair)
        current_symbol = self.bot_data.get('symbol') or 'BTC/USDT'
        normalised_symbol = str(current_symbol).strip().upper().replace('-', '/').replace(' ', '')
        if normalised_symbol not in self.supported_pairs:
            self.symbol_combo.addItem(normalised_symbol)
        self.symbol_combo.setCurrentText(normalised_symbol)
        basic_layout.addRow("Para:", self.symbol_combo)
        
        form_layout.addRow(basic_group)
        
        # Strategia
        strategy_group = QGroupBox("Strategia")
        strategy_layout = QFormLayout(strategy_group)
        
        self.strategy_combo = QComboBox()
        self._strategy_options = [
            ("DCA", "dca"),
            ("Grid Trading", "grid"),
            ("Scalping", "scalping"),
            ("Swing Trading", "swing"),
            ("Momentum", "momentum"),
            ("Mean Reversion", "mean_reversion"),
            ("Breakout", "breakout"),
            ("Arbitrage", "arbitrage"),
            ("AI", "ai"),
            ("Custom", "custom"),
        ]
        for label, key in self._strategy_options:
            self.strategy_combo.addItem(label, userData=key)
        raw_strategy = str(self.bot_data.get('strategy', 'dca')).strip().lower()
        normalized_strategy = raw_strategy.replace('-', '_').replace(' ', '_')
        alias_map = {
            'grid_trading': 'grid',
            'swing_trading': 'swing',
            'ai_trading': 'ai',
            'meanreversion': 'mean_reversion',
            'mean_reversion': 'mean_reversion',
        }
        normalized_strategy = alias_map.get(normalized_strategy, normalized_strategy)
        for idx, (label, key) in enumerate(self._strategy_options):
            if normalized_strategy in {key, label.lower().replace(' ', '_')}:
                self.strategy_combo.setCurrentIndex(idx)
                break
        strategy_layout.addRow("Typ strategii:", self.strategy_combo)
        
        form_layout.addRow(strategy_group)
        
        # Zarządzanie ryzykiem
        risk_group = QGroupBox("Zarządzanie Ryzykiem")
        risk_layout = QFormLayout(risk_group)
        
        self.position_size_spin = QDoubleSpinBox()
        self.position_size_spin.setRange(0.01, 10000.0)
        self.position_size_spin.setValue(self.bot_data.get('position_size', 100.0))
        self.position_size_spin.setSuffix(" USDT")
        risk_layout.addRow("Wielkość pozycji:", self.position_size_spin)
        
        self.stop_loss_spin = QDoubleSpinBox()
        self.stop_loss_spin.setRange(0.1, 50.0)
        self.stop_loss_spin.setValue(self.bot_data.get('stop_loss', 5.0))
        self.stop_loss_spin.setSuffix(" %")
        risk_layout.addRow("Stop Loss:", self.stop_loss_spin)
        
        self.take_profit_spin = QDoubleSpinBox()
        self.take_profit_spin.setRange(0.1, 100.0)
        self.take_profit_spin.setValue(self.bot_data.get('take_profit', 10.0))
        self.take_profit_spin.setSuffix(" %")
        risk_layout.addRow("Take Profit:", self.take_profit_spin)
        
        form_layout.addRow(risk_group)
        
        scroll.setWidget(form_widget)
        layout.addWidget(scroll)
        
        # Przyciski
        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)
    
    def get_config(self) -> Dict[str, Any]:
        """Pobierz konfigurację z formularza"""
        symbol_text = self.symbol_combo.currentText() if hasattr(self, 'symbol_combo') else ''
        symbol_value = str(symbol_text).strip().upper().replace('-', '/').replace(' ', '') or 'BTC/USDT'
        return {
            'name': self.name_edit.text(),
            'exchange': self.exchange_combo.currentText(),
            'symbol': symbol_value,
            'strategy': self.strategy_combo.currentData() or self.strategy_combo.currentText().lower(),
            'position_size': self.position_size_spin.value(),
            'stop_loss': self.stop_loss_spin.value(),
            'take_profit': self.take_profit_spin.value()
        }

class UpdatedBotManagementWidget(QWidget):
    """
    Zaktualizowany widget zarządzania botami z integracją IntegratedDataManager
    """
    
    def __init__(self, integrated_data_manager, parent=None):
        if not PYQT_AVAILABLE:
            print("PyQt6 not available, UpdatedBotManagementWidget will not function properly")
            return
            
        super().__init__(parent)
        
        self.integrated_data_manager = integrated_data_manager
        self.config_manager = get_config_manager()
        self.logger = get_logger("updated_bot_management", LogType.USER)

        # Dane botów
        self.bots_data = {}
        self.bot_cards = {}
        self.ai_last_snapshot = None
        # Throttling odświeżania
        self._refresh_in_progress = False
        self._last_refresh_time = None
        self._refresh_min_interval = 1.0  # sekundy

        # Timer odświeżania
        self.refresh_timer = QTimer()
        self.refresh_timer.timeout.connect(self.refresh_data)
        
        self.setup_ui()
        self.setup_data_callbacks()
        self.apply_theme()
        self.start_refresh_timer()
        
        self.logger.info("Updated bot management widget initialized")
    
    def setup_ui(self):
        """Konfiguracja interfejsu"""
        # Główny layout z przewijaniem całej strony
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)

        page_widget = QWidget()
        page_layout = QVBoxLayout(page_widget)
        page_layout.setSpacing(20)
        page_layout.setContentsMargins(20, 20, 20, 20)
        
        # Header
        header_layout = QHBoxLayout()
        
        title = QLabel("Zarządzanie Botami")
        title.setObjectName("pageTitle")
        title.setFont(QFont("Segoe UI", 20, QFont.Weight.Bold))
        title.setStyleSheet("color: #1f2a44;")
        title_box.addWidget(title)

        subtitle = QLabel("Twórz, uruchamiaj i monitoruj boty w jednym miejscu. Wszystkie akcje są powiązane z danymi systemu.")
        subtitle.setObjectName("cardSubtitle")
        subtitle.setWordWrap(True)
        title_box.addWidget(subtitle)
        title_box.addStretch()
        header_layout.addLayout(title_box, stretch=3)

        controls_layout = QVBoxLayout()
        controls_layout.setSpacing(10)

        # Przyciski akcji
        add_bot_btn = QPushButton("➕ Dodaj bota")
        add_bot_btn.setObjectName("inlineAction")
        add_bot_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        add_bot_btn.clicked.connect(self.add_new_bot)
        controls_layout.addWidget(add_bot_btn)

        refresh_ai_btn = QPushButton("🔄 Odśwież dane AI")
        refresh_ai_btn.setObjectName("inlineAction")
        refresh_ai_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        refresh_ai_btn.clicked.connect(self.trigger_ai_refresh)
        controls_layout.addWidget(refresh_ai_btn)
        self.refresh_ai_btn = refresh_ai_btn

        buttons_row = QHBoxLayout()
        buttons_row.setSpacing(10)

        start_all_btn = QPushButton("▶️ Start wszystkie")
        start_all_btn.setObjectName("inlineAction")
        start_all_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        start_all_btn.clicked.connect(self.start_all_bots)
        buttons_row.addWidget(start_all_btn)

        stop_all_btn = QPushButton("⏸️ Stop wszystkie")
        stop_all_btn.setObjectName("inlineAction")
        stop_all_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        stop_all_btn.clicked.connect(self.stop_all_bots)
        header_layout.addWidget(stop_all_btn)
        
        page_layout.addLayout(header_layout)
        
        # Statystyki
        self.setup_stats_section(page_layout)
        page_layout.addSpacing(12)

        # Panel danych AI
        self.setup_ai_insights_section(page_layout)
        page_layout.addSpacing(12)

        # Boty
        self.setup_bots_section(page_layout)

        scroll_area.setWidget(page_widget)
        layout.addWidget(scroll_area)

    def setup_stats_section(self, parent_layout):
        """Konfiguracja sekcji statystyk"""
        stats_frame = QFrame()
        stats_frame.setObjectName("sectionCard")
        stats_layout = QHBoxLayout(stats_frame)
        stats_layout.setSpacing(18)
        stats_layout.setContentsMargins(24, 24, 24, 24)
        
        # Całkowita liczba botów
        total_card = self.create_stat_card("Wszystkie Boty", "0", "#2196F3")
        self.total_bots_label = total_card.findChild(QLabel, "statValue")
        stats_layout.addWidget(total_card)
        
        # Aktywne boty
        active_card = self.create_stat_card("Aktywne", "0", "#4CAF50")
        self.active_bots_label = active_card.findChild(QLabel, "statValue")
        stats_layout.addWidget(active_card)
        
        # Zatrzymane boty
        stopped_card = self.create_stat_card("Zatrzymane", "0", "#9E9E9E")
        self.stopped_bots_label = stopped_card.findChild(QLabel, "statValue")
        stats_layout.addWidget(stopped_card)
        
        # Całkowity P&L
        pnl_card = self.create_stat_card("Całkowity P&L", "$0.00", "#FF9800")
        self.total_pnl_label = pnl_card.findChild(QLabel, "statValue")
        stats_layout.addWidget(pnl_card)
        
        parent_layout.addWidget(stats_frame)

    def setup_ai_insights_section(self, parent_layout):
        ai_group = QGroupBox("Panel danych AI bota")
        ai_group.setObjectName("aiInsightsGroup")
        ai_group.setStyleSheet("""
            QGroupBox#aiInsightsGroup {
                background: #ffffff;
                border: 1px solid rgba(29, 53, 87, 0.08);
                border-radius: 18px;
                margin-top: 16px;
                padding-top: 24px;
            }
            QGroupBox#aiInsightsGroup::title {
                subcontrol-origin: margin;
                subcontrol-position: top left;
                padding: 0 18px;
                margin-top: 0;
                font-weight: 600;
                color: #1f2a44;
            }
        """)
        ai_layout = QVBoxLayout(ai_group)
        ai_layout.setSpacing(14)
        ai_layout.setContentsMargins(18, 18, 18, 18)
        ai_group.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)

        self.ai_status_label = QLabel("Oczekiwanie na dane AI ...")
        self.ai_status_label.setObjectName("aiStatusLabel")
        self.ai_status_label.setWordWrap(True)
        ai_layout.addWidget(self.ai_status_label)

        self.ai_price_table = QTableWidget(0, 6)
        self.ai_price_table.setObjectName("aiPriceTable")
        self.ai_price_table.setHorizontalHeaderLabels([
            "Symbol",
            "Cena",
            "Bid",
            "Ask",
            "Zmiana 24h",
            "Wolumen 24h",
        ])
        self.ai_price_table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.ai_price_table.horizontalHeader().setStretchLastSection(True)
        self.ai_price_table.verticalHeader().setVisible(False)
        self.ai_price_table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.ai_price_table.setAlternatingRowColors(True)
        self.ai_price_table.verticalHeader().setDefaultSectionSize(30)
        self.ai_price_table.setShowGrid(False)
        self.ai_price_table.setSelectionMode(QAbstractItemView.SelectionMode.NoSelection)
        self.ai_price_table.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)
        ai_layout.addWidget(self.ai_price_table)
        ai_layout.addSpacing(10)

        self.ai_risk_table = QTableWidget(0, 6)
        self.ai_risk_table.setObjectName("aiRiskTable")
        self.ai_risk_table.setHorizontalHeaderLabels([
            "Bot",
            "Symbol",
            "Ryzyko",
            "Max DD",
            "VaR 95%",
            "Ekspozycja",
        ])
        self.ai_risk_table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.ai_risk_table.horizontalHeader().setStretchLastSection(True)
        self.ai_risk_table.verticalHeader().setVisible(False)
        self.ai_risk_table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.ai_risk_table.setAlternatingRowColors(True)
        self.ai_risk_table.verticalHeader().setDefaultSectionSize(30)
        self.ai_risk_table.setShowGrid(False)
        self.ai_risk_table.setSelectionMode(QAbstractItemView.SelectionMode.NoSelection)
        self.ai_risk_table.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)
        ai_layout.addWidget(self.ai_risk_table)
        ai_layout.addSpacing(10)

        self.ai_indicator_table = QTableWidget(0, 7)
        self.ai_indicator_table.setObjectName("aiIndicatorTable")
        self.ai_indicator_table.setHorizontalHeaderLabels([
            "Symbol",
            "Trend",
            "Siła trendu",
            "RSI",
            "MACD",
            "ATR",
            "Zmienność",
        ])
        self.ai_indicator_table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.ai_indicator_table.horizontalHeader().setStretchLastSection(True)
        self.ai_indicator_table.verticalHeader().setVisible(False)
        self.ai_indicator_table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.ai_indicator_table.setAlternatingRowColors(True)
        self.ai_indicator_table.verticalHeader().setDefaultSectionSize(30)
        self.ai_indicator_table.setShowGrid(False)
        self.ai_indicator_table.setSelectionMode(QAbstractItemView.SelectionMode.NoSelection)
        self.ai_indicator_table.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)
        ai_layout.addWidget(self.ai_indicator_table)
        ai_layout.addSpacing(10)

        self.ai_feature_table = QTableWidget(0, 9)
        self.ai_feature_table.setObjectName("aiFeatureTable")
        self.ai_feature_table.setHorizontalHeaderLabels([
            "Bot",
            "Symbol",
            "Cena",
            "RSI",
            "ATR",
            "VaR 95%",
            "Ekspozycja",
            "Strategie",
            "Pewność",
        ])
        self.ai_feature_table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.ai_feature_table.horizontalHeader().setStretchLastSection(True)
        self.ai_feature_table.verticalHeader().setVisible(False)
        self.ai_feature_table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.ai_feature_table.setAlternatingRowColors(True)
        self.ai_feature_table.verticalHeader().setDefaultSectionSize(30)
        self.ai_feature_table.setShowGrid(False)
        self.ai_feature_table.setSelectionMode(QAbstractItemView.SelectionMode.NoSelection)
        self.ai_feature_table.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)
        ai_layout.addWidget(self.ai_feature_table)
        ai_layout.addSpacing(10)

        self.ai_risk_events = QTreeWidget()
        self.ai_risk_events.setObjectName("aiRiskEvents")
        self.ai_risk_events.setHeaderLabels([
            "Bot",
            "Poziom",
            "Typ",
            "Wiadomość",
            "Czas",
        ])
        self.ai_risk_events.setRootIsDecorated(False)
        self.ai_risk_events.setMinimumHeight(160)
        self.ai_risk_events.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)
        ai_layout.addWidget(self.ai_risk_events)

        self.ai_recommendations = QTextEdit()
        self.ai_recommendations.setObjectName("aiRecommendations")
        self.ai_recommendations.setReadOnly(True)
        self.ai_recommendations.setPlaceholderText("Rekomendacje AI oraz wykryte anomalie pojawią się tutaj")
        self.ai_recommendations.setMinimumHeight(280)
        self.ai_recommendations.setLineWrapMode(QTextEdit.LineWrapMode.WidgetWidth)
        self.ai_recommendations.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)
        ai_layout.addWidget(self.ai_recommendations)

        parent_layout.addWidget(ai_group)
        self.ai_group_box = ai_group
    
    def create_stat_card(self, title: str, value: str, color: str) -> QWidget:
        """Utwórz kartę statystyki"""
        card = QWidget()
        card.setObjectName("statCard")
        card.setStyleSheet("""
            QWidget#statCard {
                background: #ffffff;
                border: 1px solid rgba(29, 53, 87, 0.08);
                border-radius: 16px;
                padding: 4px;
                box-shadow: 0 8px 24px rgba(15, 23, 42, 0.08);
            }
            QLabel#statTitle {
                font-size: 12px;
                color: #5f6c7b;
                font-weight: 600;
                letter-spacing: 0.02em;
            }
            QLabel#statValue {
                font-size: 26px;
                color: #0f172a;
                font-weight: 700;
            }
        """)
        layout = QVBoxLayout(card)
        layout.setSpacing(5)
        layout.setContentsMargins(15, 15, 15, 15)
        
        title_label = QLabel(title)
        title_label.setObjectName("statTitle")
        layout.addWidget(title_label)
        
        value_label = QLabel(value)
        value_label.setObjectName("statValue")
        value_label.setStyleSheet(f"color: {color};")
        layout.addWidget(value_label)

        return card
    
    def setup_bots_section(self, parent_layout):
        """Konfiguracja sekcji botów"""
        bots_frame = QFrame()
        bots_frame.setObjectName("sectionCard")
        bots_layout = QVBoxLayout(bots_frame)
        bots_layout.setContentsMargins(24, 24, 24, 24)
        bots_layout.setSpacing(18)

        # Header sekcji
        bots_header = QLabel("Twoje boty")
        bots_header.setObjectName("sectionTitle")
        bots_layout.addWidget(bots_header)

        bots_description = QLabel("Każda karta reprezentuje zapisane ustawienia bota. Akcje start/stop są powiązane z aktualnym stanem w bazie danych.")
        bots_description.setObjectName("cardSubtitle")
        bots_description.setWordWrap(True)
        bots_layout.addWidget(bots_description)

        # Scroll area dla kart botów
        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)

        # Widget zawierający karty
        self.bots_container = QWidget()

        if FLOW_LAYOUT_AVAILABLE:
            self.bots_layout = FlowLayout(self.bots_container)
        else:
            self.bots_layout = QGridLayout(self.bots_container)

        scroll_area.setWidget(self.bots_container)
        bots_layout.addWidget(scroll_area)

        parent_layout.addWidget(bots_frame)
    
    def setup_data_callbacks(self):
        """Konfiguracja callbacków dla aktualizacji danych"""
        # Subskrypcje na aktualizacje danych botów
        self.integrated_data_manager.subscribe_to_ui_updates(
            'bot_status_update', self.on_bot_status_update
        )
        self.integrated_data_manager.subscribe_to_ui_updates(
            'bot_created', self.on_bot_created
        )
        self.integrated_data_manager.subscribe_to_ui_updates(
            'bot_deleted', self.on_bot_deleted
        )
        self.integrated_data_manager.subscribe_to_ui_updates(
            'strategy_signal', self.on_strategy_signal
        )
        self.integrated_data_manager.subscribe_to_ui_updates(
            'ai_snapshot', self.on_ai_snapshot
        )

    def on_ai_snapshot(self, snapshot):
        try:
            if snapshot is None:
                return

            def _apply():
                try:
                    self.ai_last_snapshot = snapshot
                    self._update_ai_insights(snapshot)
                except Exception as exc:
                    self.logger.error(f"Error applying AI snapshot: {exc}")

            if QThread.currentThread() != self.thread():
                QTimer.singleShot(0, _apply)
            else:
                _apply()

        except Exception as e:
            self.logger.error(f"Error processing AI snapshot: {e}")

    def _update_ai_insights(self, snapshot: Dict[str, Any]):
        try:
            generated_at = snapshot.get('generated_at', '')
            sentiment = snapshot.get('market_sentiment', 'unknown')
            learning = snapshot.get('learning', {}) or {}
            datasets = learning.get('dataset_count', 0)
            features = learning.get('feature_count', 0)
            status_parts = [
                f"Ostatnia aktualizacja: {generated_at}",
                f"Sentiment: {sentiment}",
                f"Zestawy danych: {datasets}",
                f"Cechy: {features}",
            ]
            equity_summary = learning.get('equity_summary') or {}
            if equity_summary:
                status_parts.append(
                    f"Sharpe: {equity_summary.get('sharpe', 0.0)} | Max DD: {equity_summary.get('max_drawdown', 0.0)}"
                )
            strategy_catalog = snapshot.get('strategy_catalog', []) or []
            if strategy_catalog:
                active_count = sum(1 for entry in strategy_catalog if entry.get('active'))
                status_parts.append(f"Strategie aktywne: {active_count}/{len(strategy_catalog)}")
            self.ai_status_label.setText(" | ".join(status_parts))

            # Aktualizacja tabeli cen
            market_overview = snapshot.get('market_overview', []) or []
            self.ai_price_table.setRowCount(len(market_overview))
            for row, entry in enumerate(market_overview):
                values = [
                    entry.get('symbol', ''),
                    f"{entry.get('price', 0.0):,.2f}",
                    f"{entry.get('bid', 0.0):,.2f}",
                    f"{entry.get('ask', 0.0):,.2f}",
                    f"{entry.get('change_24h_percent', 0.0):.2f}%",
                    f"{entry.get('volume_24h', 0.0):,.0f}",
                ]
                for col, value in enumerate(values):
                    item = QTableWidgetItem(value)
                    if col > 0:
                        item.setTextAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
                    self.ai_price_table.setItem(row, col, item)

            # Aktualizacja tabeli ryzyka
            risk_entries = snapshot.get('risk_metrics', []) or []
            self.ai_risk_table.setRowCount(len(risk_entries))
            for row, entry in enumerate(risk_entries):
                values = [
                    entry.get('name') or entry.get('bot_id', ''),
                    entry.get('symbol', ''),
                    entry.get('risk_level', 'unknown'),
                    f"{entry.get('max_drawdown', entry.get('total_drawdown', 0.0)):.2f}%",
                    f"{entry.get('var_95', 0.0):.2f}",
                    f"{entry.get('exposure', entry.get('current_exposure', 0.0)):.2f}",
                ]
                for col, value in enumerate(values):
                    item = QTableWidgetItem(value)
                    if col >= 3:
                        item.setTextAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
                    self.ai_risk_table.setItem(row, col, item)

            indicators = snapshot.get('technical_indicators', {}) or {}
            indicator_items = list(indicators.items())
            self.ai_indicator_table.setRowCount(len(indicator_items))
            for row, (symbol, data) in enumerate(indicator_items):
                values = [
                    symbol,
                    data.get('trend', ''),
                    f"{data.get('trend_strength', 0.0):.2f}",
                    f"{data.get('rsi', 0.0):.2f}" if data.get('rsi') is not None else '—',
                    f"{data.get('macd', 0.0):.4f}" if data.get('macd') is not None else '—',
                    f"{data.get('atr', 0.0):.4f}" if data.get('atr') is not None else '—',
                    f"{data.get('volatility', 0.0):.4f}",
                ]
                for col, value in enumerate(values):
                    item = QTableWidgetItem(str(value))
                    if col >= 2:
                        item.setTextAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
                    self.ai_indicator_table.setItem(row, col, item)

            features = snapshot.get('feature_matrix', []) or []
            self.ai_feature_table.setRowCount(len(features))
            for row, entry in enumerate(features):
                strategy_summary = entry.get('strategy_summary') or []
                strategy_names = []
                for strategy in strategy_summary:
                    name = strategy.get('name') or strategy.get('strategy_id')
                    status = 'ON' if strategy.get('active') else 'OFF'
                    strategy_names.append(f"{name} ({status})")
                values = [
                    entry.get('name', entry.get('bot_id', '')),
                    entry.get('symbol', ''),
                    f"{entry.get('price', 0.0):,.2f}" if entry.get('price') is not None else '—',
                    f"{entry.get('rsi', 0.0):.2f}" if entry.get('rsi') is not None else '—',
                    f"{entry.get('atr', 0.0):.4f}" if entry.get('atr') is not None else '—',
                    f"{entry.get('var_95', 0.0):.2f}" if entry.get('var_95') is not None else '—',
                    f"{entry.get('exposure', 0.0):.2f}" if entry.get('exposure') is not None else '—',
                    "\n".join(strategy_names) if strategy_names else entry.get('strategy', ''),
                    f"{(entry.get('strategy_confidence') or 0.0) * 100:.0f}%",
                ]
                for col, value in enumerate(values):
                    item = QTableWidgetItem(str(value))
                    if col in (2, 3, 4, 5, 6, 8):
                        item.setTextAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
                    self.ai_feature_table.setItem(row, col, item)

            self.ai_risk_events.clear()
            risk_reports = snapshot.get('risk_reports', []) or []
            for report in risk_reports:
                bot_id = str(report.get('bot_id', ''))
                level = report.get('recent_events', [{}])[-1].get('level', '') if report.get('recent_events') else ''
                top_item = QTreeWidgetItem([
                    bot_id,
                    level,
                    '',
                    '',
                    report.get('timestamp', ''),
                ])
                for event in report.get('recent_events', []) or []:
                    child = QTreeWidgetItem([
                        bot_id,
                        event.get('level', ''),
                        event.get('event_type', ''),
                        event.get('message', ''),
                        event.get('timestamp', ''),
                    ])
                    top_item.addChild(child)
                self.ai_risk_events.addTopLevelItem(top_item)
            self.ai_risk_events.expandAll()

            # Sekcja rekomendacji i alertów
            lines: List[str] = []
            for rec in snapshot.get('strategy_recommendations', []) or []:
                confidence = int(float(rec.get('confidence', 0.0)) * 100)
                line = (
                    f"[{rec.get('bot_name') or rec.get('bot_id')}] ({rec.get('symbol', 'N/A')}) "
                    f"→ {rec.get('recommendation', '')} (pewność {confidence}%)"
                )
                lines.append(line)

            spikes = snapshot.get('price_spikes', []) or []
            if spikes:
                lines.append("\nWykryte iglice cenowe:")
                for spike in spikes:
                    lines.append(
                        f" - {spike.get('symbol')}: {spike.get('change_percent', 0.0):.2f}% ({spike.get('direction')})"
                    )

            correlations = snapshot.get('correlations', []) or []
            if correlations:
                lines.append("\nKorelacje (ostatnie 240 próbek):")
                for corr in correlations[:5]:
                    lines.append(
                        f" - {corr.get('pair')}: {corr.get('correlation', 0.0):.2f} (n={corr.get('sample_size', 0)})"
                    )

            if not lines:
                lines.append("Brak rekomendacji – czekam na dane z rynku.")

            self.ai_recommendations.setPlainText("\n".join(lines))

        except Exception as exc:
            self.logger.error(f"Error updating AI insights UI: {exc}")

    def trigger_ai_refresh(self):
        try:
            if not hasattr(self, 'integrated_data_manager') or not self.integrated_data_manager:
                return
            import asyncio

            coro = self.integrated_data_manager.refresh_ai_snapshot()
            try:
                loop = asyncio.get_running_loop()
                loop.create_task(coro)
            except RuntimeError:
                self._run_coroutine_in_thread(coro)
        except Exception as exc:
            self.logger.error(f"Error triggering AI refresh: {exc}")
    
    def on_bot_status_update(self, bot_data):
        """Callback dla aktualizacji statusu bota"""
        try:
            bot_id = bot_data.get('id') or bot_data.get('name')
            if not bot_id:
                return
            
            # Aktualizuj dane bota
            if bot_id in self.bots_data:
                self.bots_data[bot_id].update(bot_data)
            else:
                self.bots_data[bot_id] = bot_data
            
            # Aktualizuj kartę bota
            if bot_id in self.bot_cards:
                self.bot_cards[bot_id].update_data(self.bots_data[bot_id])
            else:
                self.create_bot_card(bot_id, self.bots_data[bot_id])
            
            # Aktualizuj statystyki
            self.update_stats()
            
            self.logger.info(f"Bot status updated: {bot_id}")
            
        except Exception as e:
            self.logger.error(f"Error updating bot status: {e}")
    
    def on_bot_created(self, bot_data):
        """Callback dla utworzenia nowego bota"""
        try:
            bot_id = bot_data.get('id') or bot_data.get('name')
            if not bot_id:
                return
            
            self.bots_data[bot_id] = bot_data
            self.create_bot_card(bot_id, bot_data)
            self.update_stats()
            
            self.logger.info(f"New bot created: {bot_id}")
            
        except Exception as e:
            self.logger.error(f"Error creating bot: {e}")
    
    def on_bot_deleted(self, bot_id):
        """Callback dla usunięcia bota"""
        try:
            if bot_id in self.bot_cards:
                self.bot_cards[bot_id].setParent(None)
                del self.bot_cards[bot_id]
            
            if bot_id in self.bots_data:
                del self.bots_data[bot_id]
            
            self.update_stats()
            
            self.logger.info(f"Bot deleted: {bot_id}")
            
        except Exception as e:
            self.logger.error(f"Error deleting bot: {e}")
    
    def on_strategy_signal(self, signal_data):
        """Callback dla sygnałów strategii"""
        try:
            bot_id = signal_data.get('bot_id')
            if bot_id and bot_id in self.bots_data:
                # Aktualizuj dane bota na podstawie sygnału
                if 'pnl' in signal_data:
                    self.bots_data[bot_id]['pnl'] = signal_data['pnl']
                if 'trades_count' in signal_data:
                    self.bots_data[bot_id]['trades_count'] = signal_data['trades_count']
                
                # Odśwież kartę
                if bot_id in self.bot_cards:
                    self.bot_cards[bot_id].update_data(self.bots_data[bot_id])
            
        except Exception as e:
            self.logger.error(f"Error processing strategy signal: {e}")
    
    def create_bot_card(self, bot_id: str, bot_data: Dict[str, Any]):
        """Utwórz kartę bota"""
        try:
            card = BotCard(bot_id, bot_data)
            
            # Połącz sygnały
            card.start_bot_signal.connect(self.start_bot)
            card.stop_bot_signal.connect(self.stop_bot)
            card.edit_bot_signal.connect(self.edit_bot)
            card.delete_bot_signal.connect(self.delete_bot)
            
            self.bot_cards[bot_id] = card
            
            if FLOW_LAYOUT_AVAILABLE:
                self.bots_layout.addWidget(card)
            else:
                row = len(self.bot_cards) // 3
                col = len(self.bot_cards) % 3
                self.bots_layout.addWidget(card, row, col)
            
        except Exception as e:
            self.logger.error(f"Error creating bot card: {e}")
    
    def update_stats(self):
        """Aktualizuj statystyki"""
        try:
            total_bots = len(self.bots_data)
            active_bots = sum(1 for bot in self.bots_data.values() if bot.get('status') == 'running')
            stopped_bots = total_bots - active_bots
            total_pnl = sum(bot.get('pnl', 0.0) for bot in self.bots_data.values())
            
            self.total_bots_label.setText(str(total_bots))
            self.active_bots_label.setText(str(active_bots))
            self.stopped_bots_label.setText(str(stopped_bots))
            
            pnl_color = "#4CAF50" if total_pnl >= 0 else "#F44336"
            pnl_sign = "+" if total_pnl >= 0 else ""
            self.total_pnl_label.setText(f"{pnl_sign}${total_pnl:.2f}")
            self.total_pnl_label.setStyleSheet(f"color: {pnl_color}; font-size: 24px; font-weight: bold;")
            
        except Exception as e:
            self.logger.error(f"Error updating stats: {e}")
    
    def add_new_bot(self):
        """Dodaj nowego bota"""
        try:
            dialog = BotConfigDialog(self)
            if dialog.exec() == QDialog.DialogCode.Accepted:
                config = dialog.get_config()
                
                # Wyślij żądanie utworzenia bota do IntegratedDataManager
                import asyncio, threading
                try:
                    loop = asyncio.get_running_loop()
                    loop.create_task(self._async_create_bot(config))
                except RuntimeError:
                    threading.Thread(target=lambda: self._run_coroutine_in_thread(self._async_create_bot(config)), daemon=True).start()
                
        except Exception as e:
            self.logger.error(f"Error adding new bot: {e}")
            QMessageBox.critical(self, "Błąd", f"Nie udało się dodać bota: {e}")
    
    def _run_coroutine_in_thread(self, coro):
        """Uruchom dowolną coroutine w osobnym wątku z nową pętlą event loop"""
        try:
            import asyncio
            asyncio.run(coro)
        except Exception as e:
            self.logger.error(f"Error running coroutine in thread: {e}")
    
    async def _async_create_bot(self, config: Dict[str, Any]):
        """Asynchroniczne tworzenie bota"""
        try:
            success = await self.integrated_data_manager.create_bot(config)
            if success:
                self.logger.info(f"Bot created successfully: {config['name']}")
            else:
                self.logger.error(f"Failed to create bot: {config['name']}")
                
        except Exception as e:
            self.logger.error(f"Error in async bot creation: {e}")
    
    def start_bot(self, bot_id: str):
        """Uruchom bota"""
        try:
            import asyncio, threading
            try:
                loop = asyncio.get_running_loop()
                loop.create_task(self._async_start_bot(bot_id))
            except RuntimeError:
                threading.Thread(target=lambda: self._run_coroutine_in_thread(self._async_start_bot(bot_id)), daemon=True).start()
        except Exception as e:
            self.logger.error(f"Error starting bot {bot_id}: {e}")
    
    async def _async_start_bot(self, bot_id: str):
        """Asynchroniczne uruchamianie bota"""
        try:
            success = await self.integrated_data_manager.start_bot(bot_id)
            if success:
                self.logger.info(f"Bot started successfully: {bot_id}")
            else:
                self.logger.error(f"Failed to start bot: {bot_id}")
                
        except Exception as e:
            self.logger.error(f"Error in async bot start: {e}")
    
    def stop_bot(self, bot_id: str):
        """Zatrzymaj bota"""
        try:
            import asyncio, threading
            try:
                loop = asyncio.get_running_loop()
                loop.create_task(self._async_stop_bot(bot_id))
            except RuntimeError:
                threading.Thread(target=lambda: self._run_coroutine_in_thread(self._async_stop_bot(bot_id)), daemon=True).start()
        except Exception as e:
            self.logger.error(f"Error stopping bot {bot_id}: {e}")
    
    async def _async_stop_bot(self, bot_id: str):
        """Asynchroniczne zatrzymywanie bota"""
        try:
            success = await self.integrated_data_manager.stop_bot(bot_id)
            if success:
                self.logger.info(f"Bot stopped successfully: {bot_id}")
            else:
                self.logger.error(f"Failed to stop bot: {bot_id}")
                
        except Exception as e:
            self.logger.error(f"Error in async bot stop: {e}")
    
    def edit_bot(self, bot_id: str):
        """Edytuj konfigurację bota"""
        try:
            bot_data = self.bots_data.get(bot_id, {})
            dialog = BotConfigDialog(self, bot_data)
            
            if dialog.exec() == QDialog.DialogCode.Accepted:
                config = dialog.get_config()
                import asyncio, threading
                try:
                    loop = asyncio.get_running_loop()
                    loop.create_task(self._async_update_bot(bot_id, config))
                except RuntimeError:
                    threading.Thread(target=lambda: self._run_coroutine_in_thread(self._async_update_bot(bot_id, config)), daemon=True).start()
                
        except Exception as e:
            self.logger.error(f"Error editing bot {bot_id}: {e}")
    
    async def _async_update_bot(self, bot_id: str, config: Dict[str, Any]):
        """Asynchroniczne aktualizowanie bota"""
        try:
            success = await self.integrated_data_manager.update_bot_config(bot_id, config)
            if success:
                self.logger.info(f"Bot updated successfully: {bot_id}")
            else:
                self.logger.error(f"Failed to update bot: {bot_id}")
                
        except Exception as e:
            self.logger.error(f"Error in async bot update: {e}")
    
    def delete_bot(self, bot_id: str):
        """Usuń bota"""
        try:
            reply = QMessageBox.question(
                self,
                "Potwierdzenie",
                f"Czy na pewno chcesz usunąć bota '{bot_id}'?",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
            )
            
            if reply == QMessageBox.StandardButton.Yes:
                import asyncio, threading
                try:
                    loop = asyncio.get_running_loop()
                    loop.create_task(self._async_delete_bot(bot_id))
                except RuntimeError:
                    threading.Thread(target=lambda: self._run_coroutine_in_thread(self._async_delete_bot(bot_id)), daemon=True).start()
                
        except Exception as e:
            self.logger.error(f"Error deleting bot {bot_id}: {e}")
    
    async def _async_delete_bot(self, bot_id: str):
        """Asynchroniczne usuwanie bota"""
        try:
            success = await self.integrated_data_manager.delete_bot(bot_id)
            if success:
                self.logger.info(f"Bot deleted successfully: {bot_id}")
            else:
                self.logger.error(f"Failed to delete bot: {bot_id}")
                
        except Exception as e:
            self.logger.error(f"Error in async bot deletion: {e}")
    
    def start_all_bots(self):
        """Uruchom wszystkie boty"""
        try:
            for bot_id in self.bots_data:
                if self.bots_data[bot_id].get('status') != 'running':
                    self.start_bot(bot_id)
                    
        except Exception as e:
            self.logger.error(f"Error starting all bots: {e}")
    
    def stop_all_bots(self):
        """Zatrzymaj wszystkie boty"""
        try:
            for bot_id in self.bots_data:
                if self.bots_data[bot_id].get('status') == 'running':
                    self.stop_bot(bot_id)
                    
        except Exception as e:
            self.logger.error(f"Error stopping all bots: {e}")
    
    def refresh_data(self):
        """Odśwież dane botów"""
        try:
            # Prosty throttling i ochrona przed równoległym wywołaniem
            from datetime import datetime
            if self._refresh_in_progress:
                return
            if self._last_refresh_time is not None:
                if (datetime.now() - self._last_refresh_time).total_seconds() < self._refresh_min_interval:
                    return
            self._refresh_in_progress = True
            self._last_refresh_time = datetime.now()

            if not self.integrated_data_manager.initialized:
                self.logger.warning("IntegratedDataManager not initialized")
                self._refresh_in_progress = False
                return
            
            # Uruchom asynchroniczne odświeżanie danych, uwzględniając brak działającej pętli
            import asyncio, threading
            try:
                loop = asyncio.get_running_loop()
                loop.create_task(self._async_refresh_data())
            except RuntimeError:
                # Brak uruchomionej pętli - odpal w osobnym wątku z własną pętlą
                threading.Thread(target=self._run_async_refresh_in_thread, daemon=True).start()
            
        except Exception as e:
            self.logger.error(f"Error refreshing bot data: {e}")
            # W razie błędu resetuj flagę throttlingu
            self._refresh_in_progress = False
    
    def _run_async_refresh_in_thread(self):
        """Uruchomienie _async_refresh_data w nowej pętli event loop (w osobnym wątku)"""
        try:
            import asyncio
            asyncio.run(self._async_refresh_data())
        except Exception as e:
            self.logger.error(f"Error running async refresh in thread: {e}")
    
    async def _async_refresh_data(self):
        """Asynchroniczne odświeżanie danych botów"""
        try:
            # Pobierz dane botów
            bots_data = await self.integrated_data_manager.get_bot_management_data()
            if bots_data and 'bots' in bots_data:
                bots = bots_data['bots']
                # Obsłuż zarówno słownik jak i listę struktur BotData/dict
                if isinstance(bots, dict):
                    for _, bot_info in bots.items():
                        # Normalizacja kluczy: zamień profit -> pnl jeśli potrzebne
                        if isinstance(bot_info, dict) and 'pnl' not in bot_info and 'profit' in bot_info:
                            bot_info = {**bot_info, 'pnl': bot_info.get('profit', 0.0)}
                        self.on_bot_status_update(bot_info)
                elif isinstance(bots, list):
                    for bot in bots:
                        if isinstance(bot, dict):
                            # Normalizacja kluczy dla dict
                            normalized = dict(bot)
                            if 'pnl' not in normalized and 'profit' in normalized:
                                normalized['pnl'] = normalized.get('profit', 0.0)
                            normalized.setdefault('strategy', normalized.get('strategy', 'N/A'))
                            normalized.setdefault('symbol', normalized.get('symbol', 'N/A'))
                        else:
                            # Przekształć obiekt (np. dataclass BotData) na dict zgodny z UI
                            try:
                                normalized = {
                                    'id': getattr(bot, 'id', None),
                                    'name': getattr(bot, 'name', None),
                                    'status': getattr(bot, 'status', 'stopped'),
                                    'active': getattr(bot, 'active', False),
                                    'pnl': getattr(bot, 'profit', 0.0),
                                    'profit_percent': getattr(bot, 'profit_percent', 0.0),
                                    'trades_count': getattr(bot, 'trades_count', 0),
                                    'risk_level': getattr(bot, 'risk_level', 'medium'),
                                    'created_at': getattr(bot, 'created_at', None),
                                    'strategy': getattr(bot, 'strategy', 'N/A'),
                                    'symbol': getattr(bot, 'symbol', 'N/A'),
                                }
                            except Exception:
                                continue
                        self.on_bot_status_update(normalized)
            
        except Exception as e:
            self.logger.error(f"Error in async bot data refresh: {e}")
        finally:
            # Resetuj flagę po zakończeniu odświeżania
            self._refresh_in_progress = False
    
    def apply_theme(self):
        """Zastosuj motyw"""
        self.setStyleSheet("""
            QWidget {
                background-color: #121212;
                color: #eaeaea;
            }
            QLabel#pageTitle {
                font-size: 24px;
                font-weight: bold;
                color: #ffffff;
                margin-bottom: 10px;
            }
            QLabel#sectionTitle {
                font-size: 18px;
                font-weight: 600;
                color: #d6d6d6;
                margin: 10px 0;
            }
            QPushButton#actionButton {
                background-color: #667eea;
                color: white;
                border: none;
                border-radius: 8px;
                padding: 8px 16px;
                font-weight: 600;
                margin: 2px;
            }
            QPushButton#actionButton:hover {
                background-color: #576bd6;
            }
            QPushButton#actionButton:pressed {
                background-color: #4a5bc0;
            }
            QFrame#statsFrame {
                background-color: #1a1a1a;
                border: 1px solid #2a2a2a;
                border-radius: 10px;
                padding: 12px;
            }
            QWidget#statCard {
                background-color: #181818;
                border: 1px solid #2a2a2a;
                border-radius: 8px;
                margin: 6px;
            }
            QLabel#statTitle {
                font-size: 12px;
                color: #c9c9c9;
                font-weight: 500;
            }
            /* Styl sekcji AI – czytelniejsze tabele i większe pole rekomendacji */
            QGroupBox#aiInsightsGroup {
                background-color: #1a1a1a;
                border: 1px solid #2a2a2a;
                border-radius: 12px;
                padding: 12px;
                margin-top: 8px;
            }
            QGroupBox#aiInsightsGroup::title {
                subcontrol-origin: margin;
                subcontrol-position: top left;
                padding: 0 6px;
                color: #ffffff;
                font-weight: 600;
            }
            QTableWidget#aiPriceTable,
            QTableWidget#aiRiskTable,
            QTableWidget#aiIndicatorTable,
            QTableWidget#aiFeatureTable {
                background-color: #181818;
                border: 1px solid #2b2b2b;
                border-radius: 8px;
                gridline-color: #2b2b2b;
            }
            QHeaderView::section {
                background-color: #222222;
                color: #dddddd;
                padding: 6px 8px;
                border: 1px solid #2b2b2b;
                font-weight: 600;
            }
            QTableWidget::item {
                padding: 6px 8px;
            }
            QTreeWidget#aiRiskEvents {
                background-color: #181818;
                border: 1px solid #2b2b2b;
                border-radius: 8px;
            }
            QTextEdit#aiRecommendations {
                background-color: #141414;
                border: 1px solid #2b2b2b;
                border-radius: 8px;
                padding: 10px;
                color: #eaeaea;
                font-size: 14px;
            }
        """)
    
    def start_refresh_timer(self):
        """Uruchom timer odświeżania"""
        try:
            # Odśwież dane natychmiast
            self.refresh_data()
            
            # Ustaw timer na odświeżanie co 10 sekund
            refresh_interval = get_app_setting('bot_refresh_interval', 10000)  # ms
            self.refresh_timer.start(refresh_interval)
            
            self.logger.info("Bot management refresh timer started")
            
        except Exception as e:
            self.logger.error(f"Error starting refresh timer: {e}")
    
    def closeEvent(self, event):
        """Obsługa zamknięcia widgetu"""
        try:
            # Zatrzymaj timer
            if self.refresh_timer.isActive():
                self.refresh_timer.stop()
            
            self.logger.info("Bot management widget closed")
            event.accept()
            
        except Exception as e:
            self.logger.error(f"Error closing bot management widget: {e}")
            event.accept()
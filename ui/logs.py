"""
Widok logów i alertów

Zawiera logi systemowe, alerty bezpieczeństwa,
historię działań botów i powiadomienia.
"""

import sys
from datetime import datetime, timedelta
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
        QPlainTextEdit
    )
    from PyQt6.QtCore import (
        Qt, QTimer, pyqtSignal, QSize, QDate, QPropertyAnimation,
        QEasingCurve, QParallelAnimationGroup, QThread, QRect,
        QSortFilterProxyModel, QAbstractTableModel, QModelIndex
    )
    from PyQt6.QtGui import (
        QFont, QPixmap, QIcon, QPalette, QColor, QPainter,
        QPen, QBrush, QLinearGradient, QAction, QContextMenuEvent,
        QTextCharFormat, QTextCursor
    )
    try:
        from PyQt6.QtGui import QSyntaxHighlighter, QTextDocument
        SYNTAX_HIGHLIGHTER_AVAILABLE = True
    except ImportError:
        SYNTAX_HIGHLIGHTER_AVAILABLE = False
        class QSyntaxHighlighter: pass
        class QTextDocument: pass
    PYQT_AVAILABLE = True
except ImportError:
    PYQT_AVAILABLE = False
    SYNTAX_HIGHLIGHTER_AVAILABLE = False
    # Fallback
    class QWidget: pass
    class QVBoxLayout: pass
    class QSyntaxHighlighter: pass
    class QTextDocument: pass
    class QAbstractTableModel: pass
    class QModelIndex: pass
    class QSortFilterProxyModel: pass
    class QTextCharFormat: pass
    class QListWidgetItem: pass
    class QColor: pass
    class QIcon: pass
    class Qt:
        class ItemDataRole:
            DisplayRole = 0
            UserRole = 256
        class AlignmentFlag:
            AlignCenter = 0x0004
    def pyqtSignal(*args, **kwargs):
        return lambda: None

# Import lokalnych modułów
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from utils.config_manager import get_config_manager, get_ui_setting, get_app_setting
from utils.logger import get_logger, LogType, LogLevel
from utils.helpers import FormatHelper

class LogLevel(Enum):
    """Poziomy logów"""
    DEBUG = "DEBUG"
    INFO = "INFO"
    WARNING = "WARNING"
    ERROR = "ERROR"
    CRITICAL = "CRITICAL"

class LogType(Enum):
    """Typy logów"""
    SYSTEM = "SYSTEM"
    BOT = "BOT"
    TRADE = "TRADE"
    API = "API"
    SECURITY = "SECURITY"
    USER = "USER"

class LogHighlighter(QSyntaxHighlighter):
    """Podświetlanie składni logów"""
    
    def __init__(self, document: QTextDocument):
        super().__init__(document)
        self.setup_formats()
    
    def setup_formats(self):
        """Konfiguruje formaty podświetlania"""
        self.formats = {}
        
        # DEBUG - jasnoszary, lepiej widoczny
        debug_format = QTextCharFormat()
        debug_format.setForeground(QColor("#B0B0B0"))
        self.formats['DEBUG'] = debug_format
        
        # INFO - jasnoniebieski, lepszy kontrast
        info_format = QTextCharFormat()
        info_format.setForeground(QColor("#64B5F6"))
        self.formats['INFO'] = info_format
        
        # WARNING - żółto-pomarańczowy, lepiej widoczny
        warning_format = QTextCharFormat()
        warning_format.setForeground(QColor("#FFB74D"))
        warning_format.setFontWeight(QFont.Weight.Bold)
        self.formats['WARNING'] = warning_format
        
        # ERROR - jasnoczerwonawy, lepszy kontrast
        error_format = QTextCharFormat()
        error_format.setForeground(QColor("#EF5350"))
        error_format.setFontWeight(QFont.Weight.Bold)
        self.formats['ERROR'] = error_format
        
        # CRITICAL - intensywny czerwony z tłem
        critical_format = QTextCharFormat()
        critical_format.setForeground(QColor("#FFFFFF"))
        critical_format.setFontWeight(QFont.Weight.Bold)
        critical_format.setBackground(QColor("#D32F2F"))
        self.formats['CRITICAL'] = critical_format
        
        # SUCCESS - zielony dla pozytywnych komunikatów
        success_format = QTextCharFormat()
        success_format.setForeground(QColor("#66BB6A"))
        success_format.setFontWeight(QFont.Weight.Bold)
        self.formats['SUCCESS'] = success_format
        
        # Timestamp - średnio szary, lepiej widoczny
        timestamp_format = QTextCharFormat()
        timestamp_format.setForeground(QColor("#9E9E9E"))
        self.formats['TIMESTAMP'] = timestamp_format
    
    def highlightBlock(self, text: str):
        """Podświetla blok tekstu"""
        # Podświetl timestamp
        if text.startswith('['):
            end_bracket = text.find(']')
            if end_bracket > 0:
                self.setFormat(0, end_bracket + 1, self.formats['TIMESTAMP'])
        
        # Podświetl poziom logu
        for level in LogLevel:
            if level.value in text:
                start = text.find(level.value)
                if start >= 0:
                    self.setFormat(start, len(level.value), self.formats[level.value])
                break

class LogTableModel(QAbstractTableModel):
    """Model tabeli logów"""
    
    def __init__(self, logs: List[Dict] = None):
        if not PYQT_AVAILABLE:
            return
        try:
            super().__init__()
            self.logs = logs or []
            self.headers = ["Czas", "Poziom", "Typ", "Bot", "Wiadomość"]
        except Exception as e:
            print(f"Error initializing LogTableModel: {e}")

    def rowCount(self, parent=QModelIndex()):
        return len(self.logs)
    
    def columnCount(self, parent=QModelIndex()):
        return len(self.headers)
    
    def data(self, index, role=Qt.ItemDataRole.DisplayRole):
        if not index.isValid() or index.row() >= len(self.logs):
            return None
        
        log = self.logs[index.row()]
        column = index.column()
        
        if role == Qt.ItemDataRole.DisplayRole:
            if column == 0:  # Czas
                timestamp = log.get('timestamp', datetime.now())
                if isinstance(timestamp, str):
                    timestamp = datetime.fromisoformat(timestamp.replace('Z', '+00:00'))
                return timestamp.strftime("%Y-%m-%d %H:%M:%S")
            elif column == 1:  # Poziom
                return log.get('level', 'INFO')
            elif column == 2:  # Typ
                return log.get('type', 'SYSTEM')
            elif column == 3:  # Bot
                bot_id = log.get('bot_id')
                return f"Bot #{bot_id}" if bot_id else "System"
            elif column == 4:  # Wiadomość
                return log.get('message', '')
        
        elif role == Qt.ItemDataRole.BackgroundRole:
            level = log.get('level', 'INFO')
            if level == 'ERROR':
                return QColor("#FFEBEE")
            elif level == 'WARNING':
                return QColor("#FFF8E1")
            elif level == 'CRITICAL':
                return QColor("#FFCDD2")
        
        elif role == Qt.ItemDataRole.ForegroundRole:
            level = log.get('level', 'INFO')
            if level == 'ERROR':
                return QColor("#D32F2F")
            elif level == 'WARNING':
                return QColor("#F57C00")
            elif level == 'CRITICAL':
                return QColor("#B71C1C")
            elif level == 'DEBUG':
                return QColor("#666666")
        
        return None
    
    def headerData(self, section, orientation, role=Qt.ItemDataRole.DisplayRole):
        if orientation == Qt.Orientation.Horizontal and role == Qt.ItemDataRole.DisplayRole:
            return self.headers[section]
        return None
    
    def update_logs(self, logs: List[Dict]):
        """Aktualizuje logi"""
        self.beginResetModel()
        self.logs = logs
        self.endResetModel()

class LogFilterWidget(QWidget):
    """Widget filtrowania logów"""
    
    filter_changed = pyqtSignal()
    
    def __init__(self, parent=None):
        if not PYQT_AVAILABLE:
            return
        try:
            super().__init__(parent)
            self.setup_ui()
        except Exception as e:
            print(f"Error initializing LogFilterWidget: {e}")

    def setup_ui(self):
        """Konfiguracja interfejsu"""
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(10)
        
        # Wyszukiwanie
        layout.addWidget(QLabel("Szukaj:"))
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("Wpisz tekst do wyszukania...")
        self.search_input.textChanged.connect(self.filter_changed.emit)
        layout.addWidget(self.search_input)
        
        # Poziom
        layout.addWidget(QLabel("Poziom:"))
        self.level_combo = QComboBox()
        self.level_combo.addItems(["Wszystkie", "DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"])
        self.level_combo.currentTextChanged.connect(self.filter_changed.emit)
        layout.addWidget(self.level_combo)
        
        # Typ
        layout.addWidget(QLabel("Typ:"))
        self.type_combo = QComboBox()
        self.type_combo.addItems(["Wszystkie", "SYSTEM", "BOT", "TRADE", "API", "SECURITY", "USER"])
        self.type_combo.currentTextChanged.connect(self.filter_changed.emit)
        layout.addWidget(self.type_combo)
        
        # Bot
        layout.addWidget(QLabel("Bot:"))
        self.bot_combo = QComboBox()
        self.bot_combo.addItems(["Wszystkie", "System"])
        self.bot_combo.currentTextChanged.connect(self.filter_changed.emit)
        layout.addWidget(self.bot_combo)
        
        # Okres
        layout.addWidget(QLabel("Okres:"))
        self.period_combo = QComboBox()
        self.period_combo.addItems(["Wszystkie", "Ostatnia godzina", "Ostatnie 24h", "Ostatni tydzień", "Ostatni miesiąc"])
        self.period_combo.currentTextChanged.connect(self.filter_changed.emit)
        layout.addWidget(self.period_combo)
        
        layout.addStretch()
        
        # Wyczyść filtry
        clear_btn = QPushButton("Wyczyść")
        clear_btn.clicked.connect(self.clear_filters)
        layout.addWidget(clear_btn)
    
    def get_filters(self) -> Dict:
        """Zwraca aktualne filtry"""
        return {
            'search': self.search_input.text(),
            'level': self.level_combo.currentText(),
            'type': self.type_combo.currentText(),
            'bot': self.bot_combo.currentText(),
            'period': self.period_combo.currentText()
        }
    
    def clear_filters(self):
        """Czyści wszystkie filtry"""
        self.search_input.clear()
        self.level_combo.setCurrentText("Wszystkie")
        self.type_combo.setCurrentText("Wszystkie")
        self.bot_combo.setCurrentText("Wszystkie")
        self.period_combo.setCurrentText("Wszystkie")
    
    def update_bots(self, bots: List[str]):
        """Aktualizuje listę botów"""
        current = self.bot_combo.currentText()
        self.bot_combo.clear()
        self.bot_combo.addItem("Wszystkie")
        self.bot_combo.addItem("System")
        
        for bot in bots:
            self.bot_combo.addItem(f"Bot #{bot}")
        
        # Przywróć poprzedni wybór jeśli możliwe
        index = self.bot_combo.findText(current)
        if index >= 0:
            self.bot_combo.setCurrentIndex(index)

class LogTableWidget(QWidget):
    """Widget tabeli logów"""
    
    def __init__(self, parent=None):
        if not PYQT_AVAILABLE:
            return
        try:
            super().__init__(parent)
            self.logs = []
            self.filtered_logs = []
            self.setup_ui()
        except Exception as e:
            print(f"Error initializing LogTableWidget: {e}")

    def setup_ui(self):
        """Konfiguracja interfejsu"""
        layout = QVBoxLayout(self)
        layout.setSpacing(10)
        
        # Filtry
        self.filter_widget = LogFilterWidget()
        self.filter_widget.filter_changed.connect(self.apply_filters)
        layout.addWidget(self.filter_widget)
        
        # Tabela
        self.table = QTableWidget()
        self.model = LogTableModel()
        
        # Konfiguracja tabeli
        self.table.setColumnCount(5)
        self.table.setHorizontalHeaderLabels(["Czas", "Poziom", "Typ", "Bot", "Wiadomość"])
        
        # Kompaktowe ustawienia tabeli
        self.table.setMinimumHeight(200)
        self.table.setMaximumHeight(350)
        self.table.verticalHeader().setDefaultSectionSize(26)
        self.table.verticalHeader().setVisible(False)
        self.table.setShowGrid(False)
        
        # Kompaktowe rozmiary kolumn
        header = self.table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.ResizeMode.Fixed)
        header.resizeSection(0, 90)   # Czas
        header.setSectionResizeMode(1, QHeaderView.ResizeMode.Fixed)
        header.resizeSection(1, 70)   # Poziom
        header.setSectionResizeMode(2, QHeaderView.ResizeMode.Fixed)
        header.resizeSection(2, 60)   # Typ
        header.setSectionResizeMode(3, QHeaderView.ResizeMode.Fixed)
        header.resizeSection(3, 80)   # Bot
        header.setSectionResizeMode(4, QHeaderView.ResizeMode.Stretch)  # Wiadomość
        
        self.table.setAlternatingRowColors(False)
        self.table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.table.setSortingEnabled(True)
        
        # Nowoczesny styl tabeli
        self.table.setObjectName("logsTable")
        self.table.setStyleSheet("""
            QTableWidget#logsTable {
                font-size: 12px;
                background-color: #1a1a1a;
                border: 1px solid #2a2a2a;
                border-radius: 8px;
                gridline-color: #2a2a2a;
            }
            QTableWidget#logsTable::item {
                padding: 6px 8px;
                border-bottom: 1px solid #2a2a2a;
                color: #ffffff;
            }
            QTableWidget#logsTable::item:selected {
                background-color: #333333;
            }
            QTableWidget#logsTable::item:hover {
                background-color: #222222;
            }
            QHeaderView::section {
                background-color: #1a1a1a;
                color: #cccccc;
                padding: 8px 10px;
                border: none;
                border-bottom: 2px solid #2a2a2a;
                font-size: 11px;
                font-weight: 500;
            }
        """)
        
        # Menu kontekstowe
        self.table.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.table.customContextMenuRequested.connect(self.show_context_menu)
        
        layout.addWidget(self.table)
        
        # Przyciski akcji
        actions_layout = QHBoxLayout()
        actions_layout.addStretch()
        
        # Przycisk wyczyść logi
        clear_logs_btn = QPushButton("🗑️ Wyczyść logi")
        clear_logs_btn.setStyleSheet("""
            QPushButton {
                background-color: #d32f2f;
                color: white;
                border: none;
                padding: 8px 16px;
                border-radius: 4px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #b71c1c;
            }
            QPushButton:pressed {
                background-color: #8e0000;
            }
        """)
        clear_logs_btn.clicked.connect(self.clear_logs)
        actions_layout.addWidget(clear_logs_btn)
        
        layout.addLayout(actions_layout)
        
        # Statystyki
        self.setup_stats(layout)
    
    def setup_stats(self, layout):
        """Konfiguruje statystyki logów"""
        stats_layout = QHBoxLayout()
        
        self.total_logs_label = QLabel("Łącznie: 0")
        stats_layout.addWidget(self.total_logs_label)
        
        stats_layout.addStretch()
        
        self.errors_label = QLabel("Błędy: 0")
        self.errors_label.setStyleSheet("color: #F44336; font-weight: bold;")
        stats_layout.addWidget(self.errors_label)
        
        self.warnings_label = QLabel("Ostrzeżenia: 0")
        self.warnings_label.setStyleSheet("color: #FF9800; font-weight: bold;")
        stats_layout.addWidget(self.warnings_label)
        
        layout.addLayout(stats_layout)
    
    def load_logs(self, logs: List[Dict]):
        """Ładuje logi"""
        self.logs = logs
        self.apply_filters()
        self.update_stats()
        
        # Aktualizuj listę botów w filtrach
        bots = set()
        for log in logs:
            bot_id = log.get('bot_id')
            if bot_id:
                bots.add(str(bot_id))
        
        self.filter_widget.update_bots(sorted(bots))
    
    def apply_filters(self):
        """Aplikuje filtry do logów"""
        filters = self.filter_widget.get_filters()
        self.filtered_logs = []
        
        for log in self.logs:
            # Filtr wyszukiwania
            if filters['search']:
                search_text = filters['search'].lower()
                message = log.get('message', '').lower()
                if search_text not in message:
                    continue
            
            # Filtr poziomu
            if filters['level'] != "Wszystkie":
                if log.get('level') != filters['level']:
                    continue
            
            # Filtr typu
            if filters['type'] != "Wszystkie":
                if log.get('type') != filters['type']:
                    continue
            
            # Filtr bota
            if filters['bot'] != "Wszystkie":
                if filters['bot'] == "System":
                    if log.get('bot_id') is not None:
                        continue
                else:
                    bot_id = filters['bot'].replace("Bot #", "")
                    if str(log.get('bot_id', '')) != bot_id:
                        continue
            
            # Filtr okresu
            if filters['period'] != "Wszystkie":
                timestamp = log.get('timestamp', datetime.now())
                if isinstance(timestamp, str):
                    timestamp = datetime.fromisoformat(timestamp.replace('Z', '+00:00'))
                
                now = datetime.now()
                if filters['period'] == "Ostatnia godzina":
                    if timestamp < now - timedelta(hours=1):
                        continue
                elif filters['period'] == "Ostatnie 24h":
                    if timestamp < now - timedelta(days=1):
                        continue
                elif filters['period'] == "Ostatni tydzień":
                    if timestamp < now - timedelta(weeks=1):
                        continue
                elif filters['period'] == "Ostatni miesiąc":
                    if timestamp < now - timedelta(days=30):
                        continue
            
            self.filtered_logs.append(log)
        
        # Aktualizuj tabelę
        self.update_table()
    
    def update_table(self):
        """Aktualizuje tabelę logów"""
        self.table.setRowCount(len(self.filtered_logs))
        
        for row, log in enumerate(self.filtered_logs):
            # Czas
            timestamp = log.get('timestamp', datetime.now())
            if isinstance(timestamp, str):
                timestamp = datetime.fromisoformat(timestamp.replace('Z', '+00:00'))
            
            time_item = QTableWidgetItem(timestamp.strftime("%Y-%m-%d %H:%M:%S"))
            self.table.setItem(row, 0, time_item)
            
            # Poziom
            level = log.get('level', 'INFO')
            level_item = QTableWidgetItem(level)
            level_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            level_item.setFont(QFont("Arial", 11, QFont.Weight.Bold))
            
            # Ulepszone kolorowanie poziomu dla lepszej czytelności
            if level == 'ERROR':
                level_item.setBackground(QColor(239, 83, 80, 40))  # Jasnoczerwony z przezroczystością
                level_item.setForeground(QColor("#EF5350"))
            elif level == 'WARNING':
                level_item.setBackground(QColor(255, 183, 77, 40))  # Żółto-pomarańczowy z przezroczystością
                level_item.setForeground(QColor("#FFB74D"))
            elif level == 'CRITICAL':
                level_item.setBackground(QColor(211, 47, 47, 100))  # Intensywny czerwony
                level_item.setForeground(QColor("#FFFFFF"))
            elif level == 'INFO':
                level_item.setBackground(QColor(100, 181, 246, 40))  # Jasnoniebieski z przezroczystością
                level_item.setForeground(QColor("#64B5F6"))
            elif level == 'DEBUG':
                level_item.setBackground(QColor(176, 176, 176, 30))  # Jasnoszary z przezroczystością
                level_item.setForeground(QColor("#B0B0B0"))
            elif level == 'SUCCESS':
                level_item.setBackground(QColor(102, 187, 106, 40))  # Jasnozielony z przezroczystością
                level_item.setForeground(QColor("#66BB6A"))
            
            self.table.setItem(row, 1, level_item)
            
            # Typ
            type_item = QTableWidgetItem(log.get('type', 'SYSTEM'))
            type_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            type_item.setFont(QFont("Arial", 10, QFont.Weight.Medium))
            
            # Ulepszone kolorowanie typu dla lepszej widoczności
            log_type = log.get('type', 'SYSTEM')
            if log_type == 'TRADE':
                type_item.setBackground(QColor(102, 187, 106, 40))  # Jasnozielony z tłem
                type_item.setForeground(QColor("#66BB6A"))
            elif log_type == 'API':
                type_item.setBackground(QColor(100, 181, 246, 40))  # Jasnoniebieski z tłem
                type_item.setForeground(QColor("#64B5F6"))
            elif log_type == 'SYSTEM':
                type_item.setBackground(QColor(171, 71, 188, 40))  # Jasnofioletowy z tłem
                type_item.setForeground(QColor("#AB47BC"))
            elif log_type == 'ERROR':
                type_item.setBackground(QColor(239, 83, 80, 40))  # Jasnoczerwony z tłem
                type_item.setForeground(QColor("#EF5350"))
            
            self.table.setItem(row, 2, type_item)
            
            # Bot
            bot_id = log.get('bot_id')
            bot_item = QTableWidgetItem(f"Bot #{bot_id}" if bot_id else "System")
            bot_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            bot_item.setFont(QFont("Arial", 10, QFont.Weight.Medium))
            
            if bot_id:
                bot_item.setBackground(QColor(255, 193, 7, 40))   # Żółte tło z przezroczystością
                bot_item.setForeground(QColor("#FFC107"))         # Jasnożółty dla botów
            else:
                bot_item.setBackground(QColor(158, 158, 158, 30)) # Szare tło z przezroczystością
                bot_item.setForeground(QColor("#B0B0B0"))         # Jasnoszary dla systemu
            
            self.table.setItem(row, 3, bot_item)
            
            # Wiadomość
            message_item = QTableWidgetItem(log.get('message', ''))
            message_item.setFont(QFont("Consolas", 11))  # Monospace font dla wiadomości
            
            # Ulepszone kolorowanie wiadomości dla lepszej czytelności
            if level == 'ERROR':
                message_item.setForeground(QColor("#FFCDD2"))  # Jasnoróżowy dla błędów
            elif level == 'CRITICAL':
                message_item.setForeground(QColor("#FFFFFF"))   # Biały dla krytycznych
                message_item.setBackground(QColor("#D32F2F"))   # Czerwone tło
            elif level == 'WARNING':
                message_item.setForeground(QColor("#FFF3C4"))   # Jasnożółty dla ostrzeżeń
            elif level == 'SUCCESS':
                message_item.setForeground(QColor("#C8E6C9"))   # Jasnozielony dla sukcesu
            elif level == 'DEBUG':
                message_item.setForeground(QColor("#E0E0E0"))   # Jasnoszary dla debug
            else:  # INFO
                message_item.setForeground(QColor("#E3F2FD"))   # Jasnoniebieski dla info
            
            self.table.setItem(row, 4, message_item)
        
        self.update_stats()
    
    def update_stats(self):
        """Aktualizuje statystyki"""
        total = len(self.filtered_logs)
        errors = len([log for log in self.filtered_logs if log.get('level') == 'ERROR'])
        warnings = len([log for log in self.filtered_logs if log.get('level') == 'WARNING'])
        
        self.total_logs_label.setText(f"Łącznie: {total}")
        self.errors_label.setText(f"Błędy: {errors}")
        self.warnings_label.setText(f"Ostrzeżenia: {warnings}")
    
    def show_context_menu(self, position):
        """Pokazuje menu kontekstowe"""
        if self.table.itemAt(position) is None:
            return
        
        menu = QMenu(self)
        
        # Szczegóły
        details_action = QAction("Szczegóły", self)
        details_action.triggered.connect(self.show_log_details)
        menu.addAction(details_action)
        
        menu.addSeparator()
        
        # Kopiuj
        copy_action = QAction("Kopiuj", self)
        copy_action.triggered.connect(self.copy_log)
        menu.addAction(copy_action)
        
        # Kopiuj wszystkie
        copy_all_action = QAction("Kopiuj wszystkie widoczne", self)
        copy_all_action.triggered.connect(self.copy_all_logs)
        menu.addAction(copy_all_action)
        
        menu.exec(self.table.mapToGlobal(position))
    
    def show_log_details(self):
        """Pokazuje szczegóły logu"""
        current_row = self.table.currentRow()
        if current_row >= 0 and current_row < len(self.filtered_logs):
            log = self.filtered_logs[current_row]
            
            details = json.dumps(log, indent=2, default=str, ensure_ascii=False)
            
            dialog = QMessageBox(self)
            dialog.setWindowTitle("Szczegóły Logu")
            dialog.setText("Szczegóły logu:")
            dialog.setDetailedText(details)
            dialog.exec()
    
    def copy_log(self):
        """Kopiuje log do schowka"""
        current_row = self.table.currentRow()
        if current_row >= 0 and current_row < len(self.filtered_logs):
            log = self.filtered_logs[current_row]
            
            # Formatuj log do kopiowania
            log_text = f"[{log.get('timestamp', '')}] {log.get('level', '')} - {log.get('message', '')}"
            if log.get('details'):
                log_text += f"\nSzczegóły: {log['details']}"
            
            # Kopiuj do schowka
            from PyQt6.QtWidgets import QApplication
            clipboard = QApplication.clipboard()
            clipboard.setText(log_text)
            
            QMessageBox.information(self, "Kopiuj", "Log skopiowany do schowka.")
    
    def copy_all_logs(self):
        """Kopiuje wszystkie widoczne logi"""
        if not self.filtered_logs:
            QMessageBox.information(self, "Kopiuj", "Brak logów do skopiowania.")
            return
        
        # Formatuj wszystkie logi
        all_logs_text = []
        for log in self.filtered_logs:
            log_text = f"[{log.get('timestamp', '')}] {log.get('level', '')} - {log.get('message', '')}"
            if log.get('details'):
                log_text += f"\nSzczegóły: {log['details']}"
            all_logs_text.append(log_text)
        
        # Kopiuj do schowka
        from PyQt6.QtWidgets import QApplication
        clipboard = QApplication.clipboard()
        clipboard.setText('\n\n'.join(all_logs_text))
        
        QMessageBox.information(self, "Kopiuj", f"{len(self.filtered_logs)} logów skopiowanych do schowka.")
    
    def clear_logs(self):
        """Czyści wszystkie logi z tabeli"""
        reply = QMessageBox.question(
            self, "Wyczyść Logi",
            "Czy na pewno chcesz wyczyścić wszystkie logi z tabeli?\n\nTa operacja nie może być cofnięta.",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No
        )
        
        if reply == QMessageBox.StandardButton.Yes:
            self.logs.clear()
            self.filtered_logs.clear()
            self.table.setRowCount(0)
            self.update_stats()
            QMessageBox.information(self, "Logi wyczyszczone", "Wszystkie logi zostały usunięte z tabeli.")

class LogTextWidget(QWidget):
    """Widget tekstowy logów (konsola)"""
    
    def __init__(self, parent=None):
        if not PYQT_AVAILABLE:
            return
        try:
            super().__init__(parent)
            self.logs = []
            self.setup_ui()
        except Exception as e:
            print(f"Error initializing LogTextWidget: {e}")

    def setup_ui(self):
        """Konfiguracja interfejsu"""
        layout = QVBoxLayout(self)
        layout.setSpacing(10)
        
        # Kontrolki
        controls_layout = QHBoxLayout()
        
        # Auto-scroll
        self.auto_scroll_checkbox = QCheckBox("Auto-scroll")
        self.auto_scroll_checkbox.setChecked(True)
        controls_layout.addWidget(self.auto_scroll_checkbox)
        
        # Wrap text
        self.wrap_text_checkbox = QCheckBox("Zawijaj tekst")
        self.wrap_text_checkbox.setChecked(True)
        self.wrap_text_checkbox.toggled.connect(self.toggle_wrap_text)
        controls_layout.addWidget(self.wrap_text_checkbox)
        
        controls_layout.addStretch()
        
        # Wyczyść
        clear_btn = QPushButton("Wyczyść")
        clear_btn.clicked.connect(self.clear_logs)
        controls_layout.addWidget(clear_btn)
        
        # Zapisz
        save_btn = QPushButton("Zapisz")
        save_btn.clicked.connect(self.save_logs)
        controls_layout.addWidget(save_btn)
        
        layout.addLayout(controls_layout)
        
        # Obszar tekstowy
        self.text_area = QPlainTextEdit()
        self.text_area.setReadOnly(True)
        self.text_area.setFont(QFont("Consolas", 9))
        self.text_area.setStyleSheet("""
            QPlainTextEdit {
                background-color: #1e1e1e;
                color: #ffffff;
                border: 1px solid #333;
                border-radius: 5px;
            }
        """)
        
        # Podświetlanie składni
        self.highlighter = LogHighlighter(self.text_area.document())
        
        layout.addWidget(self.text_area)
    
    def add_log(self, log: Dict):
        """Dodaje log do widoku tekstowego"""
        timestamp = log.get('timestamp', datetime.now())
        if isinstance(timestamp, str):
            timestamp = datetime.fromisoformat(timestamp.replace('Z', '+00:00'))
        
        level = log.get('level', 'INFO')
        log_type = log.get('type', 'SYSTEM')
        bot_id = log.get('bot_id')
        message = log.get('message', '')
        
        # Formatuj log
        bot_part = f" [Bot #{bot_id}]" if bot_id else ""
        log_line = f"[{timestamp.strftime('%Y-%m-%d %H:%M:%S')}] {level} {log_type}{bot_part}: {message}"
        
        # Dodaj do obszaru tekstowego
        self.text_area.appendPlainText(log_line)
        
        # Auto-scroll
        if self.auto_scroll_checkbox.isChecked():
            cursor = self.text_area.textCursor()
            cursor.movePosition(QTextCursor.MoveOperation.End)
            self.text_area.setTextCursor(cursor)
    
    def load_logs(self, logs: List[Dict]):
        """Ładuje logi do widoku tekstowego"""
        self.logs = logs
        self.text_area.clear()
        
        for log in logs:
            self.add_log(log)
    
    def toggle_wrap_text(self, enabled: bool):
        """Przełącza zawijanie tekstu"""
        if enabled:
            self.text_area.setLineWrapMode(QPlainTextEdit.LineWrapMode.WidgetWidth)
        else:
            self.text_area.setLineWrapMode(QPlainTextEdit.LineWrapMode.NoWrap)
    
    def clear_logs(self):
        """Czyści logi"""
        reply = QMessageBox.question(
            self, "Wyczyść Logi",
            "Czy na pewno chcesz wyczyścić wszystkie logi z widoku?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        
        if reply == QMessageBox.StandardButton.Yes:
            self.text_area.clear()
    
    def save_logs(self):
        """Zapisuje logi do pliku"""
        file_path, _ = QFileDialog.getSaveFileName(
            self, "Zapisz Logi",
            f"logs_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt",
            "Text Files (*.txt);;All Files (*)"
        )
        
        if file_path:
            try:
                with open(file_path, 'w', encoding='utf-8') as f:
                    f.write(self.text_area.toPlainText())
                
                QMessageBox.information(self, "Zapisz", f"Logi zapisane do:\n{file_path}")
            except Exception as e:
                QMessageBox.critical(self, "Błąd", f"Nie udało się zapisać logów:\n{e}")

class AlertsWidget(QWidget):
    """Widget alertów i powiadomień"""
    
    def __init__(self, parent=None):
        if not PYQT_AVAILABLE:
            return
        try:
            super().__init__(parent)
            self.alerts = []
            self.setup_ui()
        except Exception as e:
            print(f"Error initializing AlertsWidget: {e}")

    def setup_ui(self):
        """Konfiguracja interfejsu"""
        layout = QVBoxLayout(self)
        layout.setSpacing(15)
        
        # Nagłówek
        header_layout = QHBoxLayout()
        
        title = QLabel("Alerty i Powiadomienia")
        title.setStyleSheet("font-size: 14px; font-weight: bold; color: #ffffff;")
        header_layout.addWidget(title)
        
        header_layout.addStretch()
        
        # Oznacz wszystkie jako przeczytane
        mark_read_btn = QPushButton("Oznacz jako przeczytane")
        mark_read_btn.clicked.connect(self.mark_all_read)
        header_layout.addWidget(mark_read_btn)
        
        # Wyczyść
        clear_btn = QPushButton("Wyczyść")
        clear_btn.clicked.connect(self.clear_alerts)
        header_layout.addWidget(clear_btn)
        
        layout.addLayout(header_layout)
        
        # Lista alertów
        self.alerts_list = QListWidget()
        self.alerts_list.itemClicked.connect(self.alert_clicked)
        self.alerts_list.setStyleSheet("""
            QListWidget {
                background-color: #1a1a1a;
                border: 1px solid #333333;
                border-radius: 5px;
                color: #ffffff;
                font-size: 12px;
            }
            QListWidget::item {
                padding: 8px;
                border-bottom: 1px solid #2a2a2a;
            }
            QListWidget::item:hover {
                background-color: #2a2a2a;
            }
            QListWidget::item:selected {
                background-color: #333333;
            }
        """)
        layout.addWidget(self.alerts_list)
        
        # Statystyki
        stats_layout = QHBoxLayout()
        
        self.total_alerts_label = QLabel("Łącznie: 0")
        stats_layout.addWidget(self.total_alerts_label)
        
        stats_layout.addStretch()
        
        self.unread_alerts_label = QLabel("Nieprzeczytane: 0")
        self.unread_alerts_label.setStyleSheet("color: #F44336; font-weight: bold;")
        stats_layout.addWidget(self.unread_alerts_label)
        
        layout.addLayout(stats_layout)
    
    def add_alert(self, alert: Dict):
        """Dodaje alert"""
        self.alerts.append(alert)
        self.update_alerts_list()
    
    def load_alerts(self, alerts: List[Dict]):
        """Ładuje alerty"""
        self.alerts = alerts
        self.update_alerts_list()
    
    def update_alerts_list(self):
        """Aktualizuje listę alertów"""
        self.alerts_list.clear()
        
        for i, alert in enumerate(self.alerts):
            item = QListWidgetItem()
            
            # Formatuj alert
            timestamp = alert.get('timestamp', datetime.now())
            if isinstance(timestamp, str):
                timestamp = datetime.fromisoformat(timestamp.replace('Z', '+00:00'))
            
            title = alert.get('title', 'Alert')
            message = alert.get('message', '')
            severity = alert.get('severity', 'info')
            is_read = alert.get('is_read', False)
            
            # Tekst alertu
            time_str = timestamp.strftime("%H:%M:%S")
            item_text = f"[{time_str}] {title}"
            if message:
                item_text += f": {message[:100]}{'...' if len(message) > 100 else ''}"
            
            item.setText(item_text)
            
            # Ikona i kolory na podstawie ważności (dostosowane do ciemnego motywu)
            if severity == 'critical':
                item.setIcon(QIcon("🔴"))
                item.setBackground(QColor("#4a1a1a"))  # Ciemny czerwony
                item.setForeground(QColor("#ff6b6b"))  # Jasny czerwony tekst
            elif severity == 'warning':
                item.setIcon(QIcon("🟡"))
                item.setBackground(QColor("#4a3a1a"))  # Ciemny żółty
                item.setForeground(QColor("#ffd93d"))  # Jasny żółty tekst
            elif severity == 'info':
                item.setIcon(QIcon("🔵"))
                item.setBackground(QColor("#1a2a4a"))  # Ciemny niebieski
                item.setForeground(QColor("#6bb6ff"))  # Jasny niebieski tekst
            elif severity == 'success':
                item.setIcon(QIcon("🟢"))
                item.setBackground(QColor("#1a4a1a"))  # Ciemny zielony
                item.setForeground(QColor("#6bff6b"))  # Jasny zielony tekst
            
            # Oznacz nieprzeczytane
            if not is_read:
                font = item.font()
                font.setBold(True)
                item.setFont(font)
            
            # Zapisz indeks alertu
            item.setData(Qt.ItemDataRole.UserRole, i)
            
            self.alerts_list.addItem(item)
        
        # Aktualizuj statystyki
        self.update_stats()
    
    def update_stats(self):
        """Aktualizuje statystyki alertów"""
        total = len(self.alerts)
        unread = len([alert for alert in self.alerts if not alert.get('is_read', False)])
        
        self.total_alerts_label.setText(f"Łącznie: {total}")
        self.unread_alerts_label.setText(f"Nieprzeczytane: {unread}")
    
    def alert_clicked(self, item: QListWidgetItem):
        """Obsługuje kliknięcie alertu"""
        alert_index = item.data(Qt.ItemDataRole.UserRole)
        if alert_index is not None and alert_index < len(self.alerts):
            alert = self.alerts[alert_index]
            
            # Oznacz jako przeczytany
            alert['is_read'] = True
            
            # Pokaż szczegóły
            self.show_alert_details(alert)
            
            # Odśwież listę
            self.update_alerts_list()
    
    def show_alert_details(self, alert: Dict):
        """Pokazuje szczegóły alertu"""
        timestamp = alert.get('timestamp', datetime.now())
        if isinstance(timestamp, str):
            timestamp = datetime.fromisoformat(timestamp.replace('Z', '+00:00'))
        
        title = alert.get('title', 'Alert')
        message = alert.get('message', '')
        severity = alert.get('severity', 'info')
        
        details = f"""
Czas: {timestamp.strftime('%Y-%m-%d %H:%M:%S')}
Ważność: {severity.upper()}
Tytuł: {title}

Wiadomość:
{message}
        """.strip()
        
        QMessageBox.information(self, "Szczegóły Alertu", details)
    
    def mark_all_read(self):
        """Oznacza wszystkie alerty jako przeczytane"""
        for alert in self.alerts:
            alert['is_read'] = True
        
        self.update_alerts_list()
    
    def clear_alerts(self):
        """Czyści wszystkie alerty"""
        reply = QMessageBox.question(
            self, "Wyczyść Alerty",
            "Czy na pewno chcesz usunąć wszystkie alerty?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        
        if reply == QMessageBox.StandardButton.Yes:
            self.alerts.clear()
            self.update_alerts_list()

class LogsWidget(QWidget):
    """Widget do wyświetlania logów"""
    
    def __init__(self, parent=None):
        if not PYQT_AVAILABLE:
            print("PyQt6 not available, LogsWidget will not function properly")
            # Gdy PyQt6 nie jest dostępne, utwórz podstawowy obiekt
            object.__init__(self)
            return
            
        super().__init__(parent)
            
        try:
            self.config_manager = get_config_manager()
            self.logger = get_logger("logs_ui")
            
            # DataManager do pobierania logów
            try:
                from core.integrated_data_manager import get_integrated_data_manager
                self.data_manager = get_integrated_data_manager()
            except ImportError as e:
                self.logger.error(f"Failed to import DataManager: {e}")
                self.data_manager = None
            
            # Timer odświeżania
            self.refresh_timer = QTimer()
            self.refresh_timer.timeout.connect(self.refresh_logs)
            
            self.setup_ui()
            self.start_refresh_timer()
        except Exception as e:
            print(f"Error initializing LogsWidget: {e}")
    
    def setup_ui(self):
        """Konfiguracja interfejsu"""
        layout = QVBoxLayout(self)
        layout.setSpacing(20)
        
        # Nagłówek
        header_layout = QHBoxLayout()
        
        title = QLabel("Logi i Alerty")
        title.setStyleSheet("font-size: 18px; font-weight: bold; color: #ffffff;")
        header_layout.addWidget(title)
        
        header_layout.addStretch()
        
        # Przyciski akcji
        refresh_btn = QPushButton("🔄 Odśwież")
        refresh_btn.clicked.connect(self.refresh_logs)
        header_layout.addWidget(refresh_btn)
        
        export_btn = QPushButton("📁 Eksportuj")
        export_btn.clicked.connect(self.export_logs)
        header_layout.addWidget(export_btn)
        
        settings_btn = QPushButton("⚙️ Ustawienia")
        settings_btn.clicked.connect(self.show_settings)
        header_layout.addWidget(settings_btn)
        
        layout.addLayout(header_layout)
        
        # Tabs
        self.tabs = QTabWidget()
        
        # Tab: Tabela logów
        self.log_table = LogTableWidget()
        self.tabs.addTab(self.log_table, "Tabela Logów")
        
        # Tab: Konsola
        self.log_text = LogTextWidget()
        self.tabs.addTab(self.log_text, "Konsola")
        
        # Tab: Alerty
        self.alerts = AlertsWidget()
        self.tabs.addTab(self.alerts, "Alerty")
        
        layout.addWidget(self.tabs)
    
    def start_refresh_timer(self):
        """Uruchamia timer odświeżania"""
        interval = get_ui_setting("logs.refresh_interval_seconds", 5) * 1000
        self.refresh_timer.start(interval)
        
        # Pierwsze odświeżenie
        self.refresh_logs()
    
    def refresh_logs(self):
        """Odświeża logi"""
        try:
            # Pobierz rzeczywiste logi z DataManager
            if self.data_manager:
                try:
                    # Pobierz logi asynchronicznie
                    import asyncio
                    try:
                        # Jeśli istnieje działająca pętla, uruchom w osobnym wątku
                        asyncio.get_running_loop()
                        import concurrent.futures
                        with concurrent.futures.ThreadPoolExecutor() as executor:
                            future = executor.submit(asyncio.run, self.data_manager.get_logs(limit=200))
                            try:
                                log_entries = future.result(timeout=3)
                            except concurrent.futures.TimeoutError:
                                self.logger.warning("Timeout fetching logs from DataManager")
                                log_entries = []
                    except RuntimeError:
                        # Brak pętli – uruchom bezpośrednio
                        log_entries = asyncio.run(self.data_manager.get_logs(limit=200))
                    
                    # Konwertuj LogEntry na format Dict dla UI
                    logs = []
                    for entry in log_entries:
                        logs.append({
                            'timestamp': entry.timestamp,
                            'level': entry.level,
                            'type': entry.type,
                            'bot_id': entry.bot_id,
                            'message': entry.message,
                            'details': entry.details
                        })
                    
                except Exception as e:
                    self.logger.error(f"Error getting logs from DataManager: {e}")
                    # Fallback do przykładowych logów
                    logs = self.load_sample_logs()
            else:
                # Fallback gdy DataManager nie jest dostępny
                logs = self.load_sample_logs()
            
            # Pobierz alerty z DataManager
            if self.data_manager:
                try:
                    # Pobierz alerty asynchronicznie
                    import asyncio
                    try:
                        asyncio.get_running_loop()
                        import concurrent.futures
                        with concurrent.futures.ThreadPoolExecutor() as executor:
                            future = executor.submit(asyncio.run, self.data_manager.get_alerts(limit=50))
                            try:
                                alert_entries = future.result(timeout=3)
                            except concurrent.futures.TimeoutError:
                                self.logger.warning("Timeout fetching alerts from DataManager")
                                alert_entries = []
                    except RuntimeError:
                        alert_entries = asyncio.run(self.data_manager.get_alerts(limit=50))
                    
                    # Konwertuj AlertEntry na format Dict dla UI
                    alerts = []
                    for entry in alert_entries:
                        alerts.append({
                            'id': entry.id,
                            'timestamp': entry.timestamp,
                            'title': entry.title,
                            'message': entry.message,
                            'severity': entry.severity,
                            'is_read': entry.is_read,
                            'bot_id': entry.bot_id,
                            'alert_type': entry.alert_type
                        })
                    
                except Exception as e:
                    self.logger.error(f"Error getting alerts from DataManager: {e}")
                    # Fallback do przykładowych alertów
                    alerts = self.load_sample_alerts()
            else:
                # Fallback gdy DataManager nie jest dostępny
                alerts = self.load_sample_alerts()
            
            # Aktualizuj widoki
            self.log_table.load_logs(logs)
            self.log_text.load_logs(logs)
            self.alerts.load_alerts(alerts)
            
            self.logger.debug("Logs refreshed")
            
        except Exception as e:
            self.logger.error(f"Error refreshing logs: {e}")
    
    def load_sample_logs(self) -> List[Dict]:
        """Ładuje przykładowe logi (do usunięcia po implementacji bazy danych)"""
        logs = []
        
        # Przykładowe logi
        base_time = datetime.now()
        
        sample_logs = [
            {
                'timestamp': base_time - timedelta(minutes=1),
                'level': 'INFO',
                'type': 'SYSTEM',
                'message': 'Aplikacja uruchomiona pomyślnie'
            },
            {
                'timestamp': base_time - timedelta(minutes=2),
                'level': 'INFO',
                'type': 'BOT',
                'bot_id': 1,
                'message': 'Bot DCA rozpoczął handel na parze BTC/USDT'
            },
            {
                'timestamp': base_time - timedelta(minutes=3),
                'level': 'WARNING',
                'type': 'API',
                'message': 'Limit API Binance: 80% wykorzystania'
            },
            {
                'timestamp': base_time - timedelta(minutes=5),
                'level': 'ERROR',
                'type': 'TRADE',
                'bot_id': 2,
                'message': 'Nie udało się złożyć zlecenia: Insufficient balance'
            },
            {
                'timestamp': base_time - timedelta(minutes=10),
                'level': 'INFO',
                'type': 'TRADE',
                'bot_id': 1,
                'message': 'Zlecenie kupna wykonane: 0.001 BTC za $45.23'
            }
        ]
        
        return sample_logs
    
    def load_sample_alerts(self) -> List[Dict]:
        """Ładuje przykładowe alerty"""
        alerts = []
        
        base_time = datetime.now()
        
        sample_alerts = [
            {
                'timestamp': base_time - timedelta(minutes=1),
                'title': 'Błąd bota',
                'message': 'Bot #2 zatrzymany z powodu błędu API',
                'severity': 'critical',
                'is_read': False
            },
            {
                'timestamp': base_time - timedelta(minutes=5),
                'title': 'Limit API',
                'message': 'Osiągnięto 80% limitu API na giełdzie Binance',
                'severity': 'warning',
                'is_read': False
            },
            {
                'timestamp': base_time - timedelta(minutes=15),
                'title': 'Zysk osiągnięty',
                'message': 'Bot #1 osiągnął dzienny cel zysku: +5.2%',
                'severity': 'success',
                'is_read': True
            }
        ]
        
        return sample_alerts
    
    def export_logs(self):
        """Eksportuje logi"""
        file_path, file_filter = QFileDialog.getSaveFileName(
            self, "Eksportuj Logi",
            f"logs_export_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json",
            "JSON Files (*.json);;CSV Files (*.csv);;Text Files (*.txt)"
        )
        
        if file_path:
            try:
                # Pobierz aktualne logi z tabeli
                current_logs = self.table_widget.filtered_logs if hasattr(self.table_widget, 'filtered_logs') else []
                
                if not current_logs:
                    QMessageBox.warning(self, "Eksport", "Brak logów do eksportowania.")
                    return
                
                # Eksportuj w zależności od formatu
                if file_filter.startswith("JSON"):
                    self._export_to_json(file_path, current_logs)
                elif file_filter.startswith("CSV"):
                    self._export_to_csv(file_path, current_logs)
                elif file_filter.startswith("Text"):
                    self._export_to_txt(file_path, current_logs)
                
                QMessageBox.information(self, "Eksport", f"Logi wyeksportowane do:\n{file_path}")
            except Exception as e:
                QMessageBox.critical(self, "Błąd", f"Nie udało się wyeksportować logów:\n{e}")
    
    def _export_to_json(self, file_path: str, logs: List[Dict]):
        """Eksportuje logi do formatu JSON"""
        import json
        
        # Konwertuj datetime na string
        export_logs = []
        for log in logs:
            export_log = log.copy()
            if 'timestamp' in export_log and isinstance(export_log['timestamp'], datetime):
                export_log['timestamp'] = export_log['timestamp'].isoformat()
            export_logs.append(export_log)
        
        with open(file_path, 'w', encoding='utf-8') as f:
            json.dump(export_logs, f, indent=2, ensure_ascii=False)
    
    def _export_to_csv(self, file_path: str, logs: List[Dict]):
        """Eksportuje logi do formatu CSV"""
        import csv
        
        with open(file_path, 'w', newline='', encoding='utf-8') as f:
            if not logs:
                return
            
            # Nagłówki
            fieldnames = ['timestamp', 'level', 'type', 'message', 'bot_id', 'details']
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            
            # Dane
            for log in logs:
                row = {}
                for field in fieldnames:
                    value = log.get(field, '')
                    if field == 'timestamp' and isinstance(value, datetime):
                        value = value.strftime('%Y-%m-%d %H:%M:%S')
                    row[field] = value
                writer.writerow(row)
    
    def _export_to_txt(self, file_path: str, logs: List[Dict]):
        """Eksportuje logi do formatu tekstowego"""
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write("=== EKSPORT LOGÓW ===\n")
            f.write(f"Data eksportu: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
            f.write(f"Liczba logów: {len(logs)}\n\n")
            
            for log in logs:
                timestamp = log.get('timestamp', '')
                if isinstance(timestamp, datetime):
                    timestamp = timestamp.strftime('%Y-%m-%d %H:%M:%S')
                
                f.write(f"[{timestamp}] {log.get('level', '')} - {log.get('type', '')}\n")
                f.write(f"Wiadomość: {log.get('message', '')}\n")
                
                if log.get('bot_id'):
                    f.write(f"Bot ID: {log['bot_id']}\n")
                
                if log.get('details'):
                    f.write(f"Szczegóły: {log['details']}\n")
                
                f.write("-" * 50 + "\n\n")
    
    def show_settings(self):
        """Pokazuje ustawienia logów"""
        dialog = LogSettingsDialog(self)
        if dialog.exec() == dialog.DialogCode.Accepted:
            # Zastosuj nowe ustawienia
            settings = dialog.get_settings()
            self.apply_settings(settings)
    
    def apply_settings(self, settings: Dict):
        """Stosuje nowe ustawienia logów"""
        try:
            # Aktualizuj poziom logowania
            if 'log_level' in settings:
                # TODO: Zaktualizuj poziom logowania w systemie
                pass
            
            # Aktualizuj auto-refresh
            if 'auto_refresh' in settings:
                if settings['auto_refresh']:
                    self.refresh_timer.start(settings.get('refresh_interval', 5000))
                else:
                    self.refresh_timer.stop()
            
            # Aktualizuj maksymalną liczbę logów
            if 'max_logs' in settings:
                # TODO: Zastosuj limit logów
                pass
            
            QMessageBox.information(self, "Ustawienia", "Ustawienia zostały zastosowane.")
        except Exception as e:
            QMessageBox.critical(self, "Błąd", f"Nie udało się zastosować ustawień:\n{e}")


class LogSettingsDialog(QWidget):
    """Dialog ustawień logów"""
    
    def __init__(self, parent=None):
        if not PYQT_AVAILABLE:
            return
        try:
            super().__init__(parent)
            self.setWindowTitle("Ustawienia Logów")
            self.setFixedSize(400, 300)
            self.setup_ui()
        except Exception as e:
            print(f"Error initializing LogSettingsDialog: {e}")
    
    def setup_ui(self):
        """Konfiguracja interfejsu"""
        layout = QVBoxLayout(self)
        layout.setSpacing(15)
        
        # Poziom logowania
        level_group = QGroupBox("Poziom Logowania")
        level_layout = QVBoxLayout(level_group)
        
        self.level_combo = QComboBox()
        self.level_combo.addItems(["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"])
        self.level_combo.setCurrentText("INFO")
        level_layout.addWidget(self.level_combo)
        
        layout.addWidget(level_group)
        
        # Automatyczne odświeżanie
        refresh_group = QGroupBox("Automatyczne Odświeżanie")
        refresh_layout = QVBoxLayout(refresh_group)
        
        self.auto_refresh_checkbox = QCheckBox("Włącz automatyczne odświeżanie")
        self.auto_refresh_checkbox.setChecked(True)
        refresh_layout.addWidget(self.auto_refresh_checkbox)
        
        interval_layout = QHBoxLayout()
        interval_layout.addWidget(QLabel("Interwał (sekundy):"))
        self.interval_spinbox = QSpinBox()
        self.interval_spinbox.setRange(1, 60)
        self.interval_spinbox.setValue(5)
        interval_layout.addWidget(self.interval_spinbox)
        refresh_layout.addLayout(interval_layout)
        
        layout.addWidget(refresh_group)
        
        # Przechowywanie logów
        storage_group = QGroupBox("Przechowywanie Logów")
        storage_layout = QVBoxLayout(storage_group)
        
        max_logs_layout = QHBoxLayout()
        max_logs_layout.addWidget(QLabel("Maksymalna liczba logów:"))
        self.max_logs_spinbox = QSpinBox()
        self.max_logs_spinbox.setRange(100, 10000)
        self.max_logs_spinbox.setValue(1000)
        max_logs_layout.addWidget(self.max_logs_spinbox)
        storage_layout.addLayout(max_logs_layout)
        
        self.save_to_file_checkbox = QCheckBox("Zapisuj logi do pliku")
        self.save_to_file_checkbox.setChecked(True)
        storage_layout.addWidget(self.save_to_file_checkbox)
        
        layout.addWidget(storage_group)
        
        # Przyciski
        buttons_layout = QHBoxLayout()
        
        ok_btn = QPushButton("OK")
        ok_btn.clicked.connect(self.accept)
        buttons_layout.addWidget(ok_btn)
        
        cancel_btn = QPushButton("Anuluj")
        cancel_btn.clicked.connect(self.reject)
        buttons_layout.addWidget(cancel_btn)
        
        layout.addLayout(buttons_layout)
    
    def get_settings(self) -> Dict:
        """Zwraca aktualne ustawienia"""
        return {
            'log_level': self.level_combo.currentText(),
            'auto_refresh': self.auto_refresh_checkbox.isChecked(),
            'refresh_interval': self.interval_spinbox.value() * 1000,  # Konwersja na ms
            'max_logs': self.max_logs_spinbox.value(),
            'save_to_file': self.save_to_file_checkbox.isChecked()
        }
    
    def accept(self):
        """Akceptuje dialog"""
        self.close()
        return self.DialogCode.Accepted
    
    def reject(self):
        """Odrzuca dialog"""
        self.close()
        return self.DialogCode.Rejected
    
    class DialogCode:
        Accepted = 1
        Rejected = 0
    
    def exec(self):
        """Wykonuje dialog"""
        self.show()
        return self.DialogCode.Accepted

def main():
    """Funkcja główna do testowania"""
    if not PYQT_AVAILABLE:
        print("PyQt6 is not available. Please install it to run the GUI.")
        return
    
    import sys
    from PyQt6.QtWidgets import QApplication
    
    app = QApplication(sys.argv)
    
    widget = LogsWidget()
    widget.show()
    
    sys.exit(app.exec())

if __name__ == "__main__":
    main()
"""
Widok portfela

Zawiera informacje o balansach, historii transakcji,
statystykach i wydajności portfela.
"""

import sys
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Tuple
from decimal import Decimal

try:
    from PyQt6.QtWidgets import (
        QWidget, QVBoxLayout, QHBoxLayout, QGridLayout, QFormLayout,
        QLabel, QPushButton, QFrame, QScrollArea, QTabWidget,
        QTableWidget, QTableWidgetItem, QHeaderView, QComboBox,
        QLineEdit, QSpinBox, QDoubleSpinBox, QCheckBox, QGroupBox,
        QTextEdit, QProgressBar, QSplitter, QTreeWidget, QTreeWidgetItem,
        QMessageBox, QMenu, QFileDialog, QDateEdit, QApplication
    )
    from PyQt6.QtCore import (
        Qt, QTimer, pyqtSignal, QSize, QDate, QPropertyAnimation,
        QEasingCurve, QParallelAnimationGroup, QThread
    )
    from PyQt6.QtGui import (
        QFont, QPixmap, QIcon, QPalette, QColor, QPainter,
        QPen, QBrush, QLinearGradient, QAction, QContextMenuEvent
    )
    PYQT_AVAILABLE = True
    
    # Import FlowLayout dla responsywności
    try:
        from ui.flow_layout import FlowLayout
        FLOW_LAYOUT_AVAILABLE = True
    except ImportError:
        FLOW_LAYOUT_AVAILABLE = False
except ImportError as e:
    print(f"PyQt6 import error in portfolio.py: {e}")
    PYQT_AVAILABLE = False
    # Fallback classes
    class QWidget: 
        def __init__(self, parent=None): pass
        def setStyleSheet(self, style): pass
        def show(self): pass
    class QVBoxLayout: 
        def __init__(self, parent=None): pass
        def addWidget(self, widget): pass
        def addLayout(self, layout): pass
        def setSpacing(self, spacing): pass
        def setContentsMargins(self, *args): pass
        def addStretch(self): pass
    class QHBoxLayout: 
        def __init__(self): pass
        def addWidget(self, widget): pass
        def addStretch(self): pass
    class QGridLayout: 
        def __init__(self, parent=None): pass
        def addWidget(self, widget, row, col): pass
        def setSpacing(self, spacing): pass
        def setRowStretch(self, row, stretch): pass
        def count(self): return 0
        def itemAt(self, index): return None
    class QFormLayout: 
        def __init__(self, parent=None): pass
        def addRow(self, label, widget): pass
    class QLabel: 
        def __init__(self, text="", parent=None): pass
        def setText(self, text): pass
        def setStyleSheet(self, style): pass
        def setAlignment(self, alignment): pass
        def setMinimumHeight(self, height): pass
        def setBackground(self, color): pass
    class QPushButton: 
        def __init__(self, text="", parent=None): pass
        def clicked(self): return lambda: None
        def connect(self, func): pass
    class QFrame: 
        def __init__(self, parent=None): pass
        def setFrameStyle(self, style): pass
        def setFrameShape(self, shape): pass
        def setFrameShadow(self, shadow): pass
        def setStyleSheet(self, style): pass
        class Shape:
            StyledPanel = 1
            VLine = 2
        class Shadow:
            Sunken = 1
    class QScrollArea: 
        def __init__(self, parent=None): pass
        def setWidgetResizable(self, resizable): pass
        def setHorizontalScrollBarPolicy(self, policy): pass
        def setWidget(self, widget): pass
    class QTabWidget: 
        def __init__(self, parent=None): pass
        def addTab(self, widget, title): pass
    class QTableWidget: 
        def __init__(self, parent=None): pass
        def setColumnCount(self, count): pass
        def setRowCount(self, count): pass
        def setHorizontalHeaderLabels(self, labels): pass
        def horizontalHeader(self): return QHeaderView()
        def setAlternatingRowColors(self, alternate): pass
        def setSelectionBehavior(self, behavior): pass
        def setSortingEnabled(self, enabled): pass
        def setContextMenuPolicy(self, policy): pass
        def customContextMenuRequested(self): return lambda: None
        def connect(self, func): pass
        def setItem(self, row, col, item): pass
        def itemAt(self, pos): return None
        def currentRow(self): return 0
        def mapToGlobal(self, pos): return pos
        class SelectionBehavior:
            SelectRows = 1
    class QTableWidgetItem: 
        def __init__(self, text=""): pass
        def setBackground(self, color): pass
    class QHeaderView: 
        def __init__(self): pass
        def setSectionResizeMode(self, section, mode): pass
        class ResizeMode:
            ResizeToContents = 1
            Stretch = 2
    class QComboBox: 
        def __init__(self, parent=None): pass
        def addItems(self, items): pass
        def currentText(self): return ""
        def currentTextChanged(self): return lambda: None
        def connect(self, func): pass
        def isChecked(self): return False
    class QCheckBox: 
        def __init__(self, text="", parent=None): pass
        def toggled(self): return lambda: None
        def connect(self, func): pass
        def isChecked(self): return False
    class QGroupBox: 
        def __init__(self, title="", parent=None): pass
    class QMessageBox: 
        @staticmethod
        def information(parent, title, text): pass
        @staticmethod
        def critical(parent, title, text): pass
        @staticmethod
        def warning(parent, title, text): pass
    class QMenu: 
        def __init__(self, parent=None): pass
        def addAction(self, action): pass
        def addSeparator(self): pass
        def exec(self, pos): pass
    class QAction: 
        def __init__(self, text, parent=None): pass
        def triggered(self): return lambda: None
        def connect(self, func): pass
    class QFileDialog: 
        @staticmethod
        def getSaveFileName(parent, caption, directory, filter=""): return ("", "")
    class QApplication:
        @staticmethod
        def clipboard(): return QClipboard()
    class QClipboard:
        def setText(self, text): pass
    class QTimer: 
        def __init__(self): pass
        def timeout(self): return lambda: None
        def connect(self, func): pass
        def start(self, interval): pass
    class QColor: 
        def __init__(self, color): pass
    class Qt:
        class AlignmentFlag:
            AlignCenter = 1
        class ScrollBarPolicy:
            ScrollBarAlwaysOff = 1
        class ContextMenuPolicy:
            CustomContextMenu = 1
    class pyqtSignal: pass

# Import lokalnych modułów
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from utils.config_manager import get_config_manager, get_ui_setting, get_app_setting
from utils.logger import get_logger, LogType
from utils.helpers import FormatHelper, CalculationHelper

# Import bazy danych
try:
    from app.database import DatabaseManager
    DATABASE_AVAILABLE = True
except ImportError as e:
    print(f"Database import error: {e}")
    DATABASE_AVAILABLE = False

# Import nowych kart
try:
    from ui.balance_card import BalanceCard
    from ui.portfolio_summary_card import PortfolioSummaryCard, StatCard
    CARDS_AVAILABLE = True
except ImportError as e:
    print(f"Cards import error: {e}")
    CARDS_AVAILABLE = False

# Stara klasa BalanceCard została zastąpiona nową implementacją w balance_card.py

class TransactionHistoryWidget(QWidget):
    """Widget historii transakcji"""
    
    def __init__(self, parent=None):
        if not PYQT_AVAILABLE:
            print("PyQt6 not available, TransactionHistoryWidget will not function properly")
            return
            
        try:
            super().__init__(parent)
            self.transactions = []
            self.setup_ui()
        except Exception as e:
            print(f"Error initializing TransactionHistoryWidget: {e}")
    
    def setup_ui(self):
        """Konfiguracja interfejsu"""
        layout = QVBoxLayout(self)
        layout.setSpacing(15)
        
        # Nagłówek z filtrami
        header_layout = QHBoxLayout()
        
        title = QLabel("Historia Transakcji")
        title.setStyleSheet("font-size: 18px; font-weight: bold;")
        header_layout.addWidget(title)
        
        header_layout.addStretch()
        
        # Filtry
        self.filter_combo = QComboBox()
        self.filter_combo.addItems(["Wszystkie", "Kupno", "Sprzedaż", "Ostatnie 24h", "Ostatni tydzień"])
        self.filter_combo.currentTextChanged.connect(self.apply_filter)
        header_layout.addWidget(QLabel("Filtr:"))
        header_layout.addWidget(self.filter_combo)
        
        # Przycisk eksportu
        export_btn = QPushButton("Eksportuj")
        export_btn.clicked.connect(self.export_transactions)
        header_layout.addWidget(export_btn)
        
        layout.addLayout(header_layout)
        
        # Tabela transakcji
        self.transactions_table = QTableWidget()
        self.transactions_table.setColumnCount(8)
        self.transactions_table.setHorizontalHeaderLabels([
            "Data/Czas", "Bot", "Para", "Typ", "Kwota", "Cena", "Wartość", "Status"
        ])
        
        # Kompaktowa konfiguracja tabeli
        self.transactions_table.setMinimumHeight(200)
        self.transactions_table.setMaximumHeight(300)
        
        # Konfiguracja nagłówków
        header = self.transactions_table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.ResizeMode.Fixed)
        header.resizeSection(0, 120)  # Data/Czas
        header.setSectionResizeMode(1, QHeaderView.ResizeMode.Fixed)
        header.resizeSection(1, 80)   # Bot
        header.setSectionResizeMode(2, QHeaderView.ResizeMode.Fixed)
        header.resizeSection(2, 80)   # Para
        header.setSectionResizeMode(3, QHeaderView.ResizeMode.Fixed)
        header.resizeSection(3, 60)   # Typ
        header.setSectionResizeMode(4, QHeaderView.ResizeMode.Fixed)
        header.resizeSection(4, 100)  # Kwota
        header.setSectionResizeMode(5, QHeaderView.ResizeMode.Fixed)
        header.resizeSection(5, 100)  # Cena
        header.setSectionResizeMode(6, QHeaderView.ResizeMode.Stretch)  # Wartość
        header.setSectionResizeMode(7, QHeaderView.ResizeMode.Fixed)
        header.resizeSection(7, 80)   # Status
        
        # Konfiguracja wierszy
        vertical_header = self.transactions_table.verticalHeader()
        vertical_header.setDefaultSectionSize(28)
        vertical_header.setVisible(False)
        
        self.transactions_table.setAlternatingRowColors(False)
        self.transactions_table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.transactions_table.setSortingEnabled(True)
        self.transactions_table.setShowGrid(False)
        
        # Nowoczesny styl tabeli
        self.transactions_table.setObjectName("modernTable")
        self.transactions_table.setStyleSheet("""
            QTableWidget#modernTable {
                font-size: 12px;
                background-color: #1a1a1a;
                border: 1px solid #2a2a2a;
                border-radius: 8px;
                gridline-color: #2a2a2a;
            }
            QTableWidget#modernTable::item {
                padding: 6px 8px;
                border-bottom: 1px solid #2a2a2a;
                color: #ffffff;
            }
            QTableWidget#modernTable::item:selected {
                background-color: #333333;
            }
            QTableWidget#modernTable::item:hover {
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
        self.transactions_table.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.transactions_table.customContextMenuRequested.connect(self.show_context_menu)
        
        layout.addWidget(self.transactions_table)
        
        # Podsumowanie
        summary_layout = QHBoxLayout()
        
        self.total_transactions_label = QLabel("Transakcje: 0")
        summary_layout.addWidget(self.total_transactions_label)
        
        summary_layout.addStretch()
        
        self.total_volume_label = QLabel("Wolumen: $0.00")
        summary_layout.addWidget(self.total_volume_label)
        
        self.total_fees_label = QLabel("Opłaty: $0.00")
        summary_layout.addWidget(self.total_fees_label)
        
        layout.addLayout(summary_layout)
    
    def load_transactions(self, transactions: List[Dict]):
        """Ładuje transakcje do tabeli"""
        self.transactions = transactions
        self.update_table()
    
    def update_table(self):
        """Aktualizuje tabelę transakcji"""
        filtered_transactions = self.get_filtered_transactions()
        
        self.transactions_table.setRowCount(len(filtered_transactions))
        
        for row, transaction in enumerate(filtered_transactions):
            # Data/Czas
            timestamp = transaction.get('timestamp', datetime.now())
            if isinstance(timestamp, str):
                timestamp = datetime.fromisoformat(timestamp.replace('Z', '+00:00'))
            
            date_item = QTableWidgetItem(timestamp.strftime("%Y-%m-%d %H:%M:%S"))
            self.transactions_table.setItem(row, 0, date_item)
            
            # Bot
            bot_item = QTableWidgetItem(f"Bot #{transaction.get('bot_id', 'N/A')}")
            self.transactions_table.setItem(row, 1, bot_item)
            
            # Para
            pair_item = QTableWidgetItem(transaction.get('pair', 'N/A'))
            self.transactions_table.setItem(row, 2, pair_item)
            
            # Typ
            side = transaction.get('side', 'N/A')
            type_item = QTableWidgetItem(side.upper())
            
            # Nowoczesne kolorowanie typu
            if side.lower() == 'buy':
                type_item.setBackground(QColor(76, 175, 80, 51))  # Zielony z przezroczystością
                type_item.setForeground(QColor("#4CAF50"))
            elif side.lower() == 'sell':
                type_item.setBackground(QColor(244, 67, 54, 51))  # Czerwony z przezroczystością
                type_item.setForeground(QColor("#F44336"))
            
            type_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            self.transactions_table.setItem(row, 3, type_item)
            
            # Kwota
            amount = transaction.get('amount', 0)
            amount_item = QTableWidgetItem(f"{amount:.8f}")
            amount_item.setTextAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
            amount_item.setFont(QFont("Courier New", 12, QFont.Weight.Bold))
            self.transactions_table.setItem(row, 4, amount_item)
            
            # Cena
            price = transaction.get('price', 0)
            price_item = QTableWidgetItem(f"${price:,.2f}")
            price_item.setTextAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
            price_item.setFont(QFont("Courier New", 12, QFont.Weight.Bold))
            price_item.setForeground(QColor("#FFD700"))  # Złoty kolor dla cen
            self.transactions_table.setItem(row, 5, price_item)
            
            # Wartość
            value = amount * price
            value_item = QTableWidgetItem(f"${value:,.2f}")
            value_item.setTextAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
            value_item.setFont(QFont("Courier New", 12, QFont.Weight.Bold))
            value_item.setForeground(QColor("#FFD700"))  # Złoty kolor dla wartości
            self.transactions_table.setItem(row, 6, value_item)
            
            # Status
            status = transaction.get('status', 'unknown')
            status_item = QTableWidgetItem(status.title())
            status_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            
            # Nowoczesne kolorowanie statusu
            if status.lower() == 'filled':
                status_item.setBackground(QColor(76, 175, 80, 51))  # Zielony
                status_item.setForeground(QColor("#4CAF50"))
            elif status.lower() == 'cancelled':
                status_item.setBackground(QColor(244, 67, 54, 51))  # Czerwony
                status_item.setForeground(QColor("#F44336"))
            elif status.lower() == 'pending':
                status_item.setBackground(QColor(255, 152, 0, 51))  # Pomarańczowy
                status_item.setForeground(QColor("#FF9800"))
            
            status_item.setFont(QFont("Arial", 11, QFont.Weight.Bold))
            self.transactions_table.setItem(row, 7, status_item)
        
        # Aktualizuj podsumowanie
        self.update_summary(filtered_transactions)
    
    def get_filtered_transactions(self) -> List[Dict]:
        """Zwraca przefiltrowane transakcje"""
        filter_text = self.filter_combo.currentText()
        
        if filter_text == "Wszystkie":
            return self.transactions
        elif filter_text == "Kupno":
            return [t for t in self.transactions if t.get('side', '').lower() == 'buy']
        elif filter_text == "Sprzedaż":
            return [t for t in self.transactions if t.get('side', '').lower() == 'sell']
        elif filter_text == "Ostatnie 24h":
            cutoff = datetime.now() - timedelta(hours=24)
            return [t for t in self.transactions if self.parse_timestamp(t.get('timestamp')) >= cutoff]
        elif filter_text == "Ostatni tydzień":
            cutoff = datetime.now() - timedelta(days=7)
            return [t for t in self.transactions if self.parse_timestamp(t.get('timestamp')) >= cutoff]
        
        return self.transactions
    
    def parse_timestamp(self, timestamp) -> datetime:
        """Parsuje timestamp do datetime"""
        if isinstance(timestamp, datetime):
            return timestamp
        elif isinstance(timestamp, str):
            try:
                return datetime.fromisoformat(timestamp.replace('Z', '+00:00'))
            except:
                return datetime.now()
        else:
            return datetime.now()
    
    def update_summary(self, transactions: List[Dict]):
        """Aktualizuje podsumowanie transakcji"""
        total_count = len(transactions)
        total_volume = sum(t.get('amount', 0) * t.get('price', 0) for t in transactions)
        total_fees = sum(t.get('fee', 0) for t in transactions)
        
        self.total_transactions_label.setText(f"Transakcje: {total_count}")
        self.total_volume_label.setText(f"Wolumen: ${total_volume:,.2f}")
        self.total_fees_label.setText(f"Opłaty: ${total_fees:,.2f}")
    
    def apply_filter(self):
        """Aplikuje filtr do transakcji"""
        self.update_table()
    
    def show_context_menu(self, position):
        """Pokazuje menu kontekstowe"""
        if self.transactions_table.itemAt(position) is None:
            return
        
        menu = QMenu(self)
        
        view_details_action = QAction("Szczegóły", self)
        view_details_action.triggered.connect(self.view_transaction_details)
        menu.addAction(view_details_action)
        
        menu.addSeparator()
        
        copy_action = QAction("Kopiuj", self)
        copy_action.triggered.connect(self.copy_transaction)
        menu.addAction(copy_action)
        
        menu.exec(self.transactions_table.mapToGlobal(position))
    
    def view_transaction_details(self):
        """Pokazuje szczegóły transakcji"""
        current_row = self.transactions_table.currentRow()
        if current_row >= 0:
            filtered_transactions = self.get_filtered_transactions()
            if current_row < len(filtered_transactions):
                transaction = filtered_transactions[current_row]
                
                # Formatuj szczegóły transakcji
                details = f"""
Szczegóły Transakcji:

ID: {transaction.get('id', 'N/A')}
Data/Czas: {transaction.get('timestamp', 'N/A')}
Bot: {transaction.get('bot_name', 'N/A')}
Para: {transaction.get('symbol', 'N/A')}
Typ: {transaction.get('side', 'N/A').upper()}
Kwota: {transaction.get('amount', 0):.8f}
Cena: ${transaction.get('price', 0):.8f}
Wartość: ${transaction.get('amount', 0) * transaction.get('price', 0):.2f}
Opłata: ${transaction.get('fee', 0):.8f}
Status: {transaction.get('status', 'N/A')}
Giełda: {transaction.get('exchange', 'N/A')}
Order ID: {transaction.get('order_id', 'N/A')}
                """.strip()
                
                QMessageBox.information(self, "Szczegóły Transakcji", details)
    
    def copy_transaction(self):
        """Kopiuje dane transakcji"""
        current_row = self.transactions_table.currentRow()
        if current_row >= 0:
            filtered_transactions = self.get_filtered_transactions()
            if current_row < len(filtered_transactions):
                transaction = filtered_transactions[current_row]
                
                # Formatuj dane do kopiowania
                data = f"{transaction.get('timestamp', '')}\t{transaction.get('bot_name', '')}\t{transaction.get('symbol', '')}\t{transaction.get('side', '').upper()}\t{transaction.get('amount', 0):.8f}\t{transaction.get('price', 0):.8f}\t${transaction.get('amount', 0) * transaction.get('price', 0):.2f}\t{transaction.get('status', '')}"
                
                # Kopiuj do schowka
                try:
                    from PyQt6.QtWidgets import QApplication
                    clipboard = QApplication.clipboard()
                    clipboard.setText(data)
                    QMessageBox.information(self, "Kopiuj", "Dane transakcji skopiowane do schowka.")
                except Exception as e:
                    QMessageBox.warning(self, "Błąd", f"Nie udało się skopiować: {e}")
    
    def export_transactions(self):
        """Eksportuje transakcje do pliku"""
        file_path, file_type = QFileDialog.getSaveFileName(
            self, "Eksportuj Transakcje", 
            f"transactions_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
            "CSV Files (*.csv);;JSON Files (*.json)"
        )
        
        if file_path:
            try:
                filtered_transactions = self.get_filtered_transactions()
                
                if file_type == "CSV Files (*.csv)" or file_path.endswith('.csv'):
                    # Eksport CSV
                    import csv
                    with open(file_path, 'w', newline='', encoding='utf-8') as csvfile:
                        fieldnames = ['timestamp', 'bot_name', 'symbol', 'side', 'amount', 'price', 'value', 'fee', 'status', 'exchange', 'order_id']
                        writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
                        
                        writer.writeheader()
                        for transaction in filtered_transactions:
                            row = {
                                'timestamp': transaction.get('timestamp', ''),
                                'bot_name': transaction.get('bot_name', ''),
                                'symbol': transaction.get('symbol', ''),
                                'side': transaction.get('side', '').upper(),
                                'amount': transaction.get('amount', 0),
                                'price': transaction.get('price', 0),
                                'value': transaction.get('amount', 0) * transaction.get('price', 0),
                                'fee': transaction.get('fee', 0),
                                'status': transaction.get('status', ''),
                                'exchange': transaction.get('exchange', ''),
                                'order_id': transaction.get('order_id', '')
                            }
                            writer.writerow(row)
                else:
                    # Eksport JSON
                    import json
                    with open(file_path, 'w', encoding='utf-8') as jsonfile:
                        json.dump(filtered_transactions, jsonfile, indent=2, ensure_ascii=False, default=str)
                
                QMessageBox.information(self, "Eksport", f"Transakcje wyeksportowane do:\n{file_path}")
            except Exception as e:
                QMessageBox.critical(self, "Błąd", f"Nie udało się wyeksportować:\n{e}")

class PortfolioStatsWidget(QWidget):
    """Widget statystyk portfela"""
    
    def __init__(self, parent=None):
        if not PYQT_AVAILABLE:
            print("PyQt6 not available, PortfolioStatsWidget will not function properly")
            return
            
        try:
            super().__init__(parent)
            self.setup_ui()
        except Exception as e:
            print(f"Error initializing PortfolioStatsWidget: {e}")
    
    def setup_ui(self):
        """Konfiguracja interfejsu"""
        layout = QVBoxLayout(self)
        layout.setSpacing(20)
        
        # Nagłówek
        title = QLabel("Statystyki Portfela")
        title.setStyleSheet("font-size: 18px; font-weight: bold;")
        layout.addWidget(title)
        
        # Grid ze statystykami
        stats_grid = QGridLayout()
        stats_grid.setSpacing(15)
        
        # Statystyki ogólne
        self.create_stat_group("Ogólne", [
            ("Całkowita wartość", "$0.00"),
            ("Zmiana 24h", "$0.00 (0.00%)"),
            ("Zmiana 7d", "$0.00 (0.00%)"),
            ("Zmiana 30d", "$0.00 (0.00%)")
        ], stats_grid, 0, 0)
        
        # Statystyki handlowe
        self.create_stat_group("Handel", [
            ("Całkowity P&L", "$0.00"),
            ("Dzienny P&L", "$0.00"),
            ("Liczba transakcji", "0"),
            ("Wskaźnik wygranych", "0.00%")
        ], stats_grid, 0, 1)
        
        # Alokacja
        self.create_stat_group("Alokacja", [
            ("Największa pozycja", "N/A (0.00%)"),
            ("Liczba aktywów", "0"),
            ("Dywersyfikacja", "N/A"),
            ("Wolne środki", "$0.00")
        ], stats_grid, 1, 0)
        
        # Ryzyko
        self.create_stat_group("Ryzyko", [
            ("Maksymalny drawdown", "0.00%"),
            ("Volatility (30d)", "0.00%"),
            ("Sharpe Ratio", "N/A"),
            ("Beta", "N/A")
        ], stats_grid, 1, 1)
        
        layout.addLayout(stats_grid)
        
        # Wykres alokacji
        allocation_title = QLabel("Alokacja Portfela")
        allocation_title.setStyleSheet("font-size: 16px; font-weight: bold; margin-top: 20px;")
        layout.addWidget(allocation_title)
        
        try:
            from ui.charts import create_chart_widget
            self.allocation_chart = create_chart_widget("allocation")
            layout.addWidget(self.allocation_chart)
        except ImportError as e:
            self.allocation_chart = QLabel("Błąd ładowania wykresu alokacji")
            self.allocation_chart.setAlignment(Qt.AlignmentFlag.AlignCenter)
            self.allocation_chart.setStyleSheet("""
                background-color: #f5f5f5;
                border: 2px dashed #ccc;
                border-radius: 5px;
                padding: 40px;
                color: #666;
            """)
            self.allocation_chart.setMinimumHeight(200)
            layout.addWidget(self.allocation_chart)
        
        layout.addStretch()
    
    def create_stat_group(self, title: str, stats: List[Tuple[str, str]], 
                         grid: QGridLayout, row: int, col: int):
        """Tworzy grupę statystyk"""
        group = QGroupBox(title)
        group_layout = QFormLayout(group)
        
        for stat_name, stat_value in stats:
            label = QLabel(stat_value)
            label.setStyleSheet("font-weight: bold;")
            group_layout.addRow(stat_name + ":", label)
        
        grid.addWidget(group, row, col)
    
    def update_stats(self, portfolio_data: Dict):
        """Aktualizuje statystyki portfela"""
        # TODO: Implementuj aktualizację statystyk na podstawie danych
        pass

class PortfolioWidget(QWidget):
    """Główny widget portfela"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        
        if not PYQT_AVAILABLE:
            print("PyQt6 not available, PortfolioWidget will not function properly")
            return
            
        try:
            self.config_manager = get_config_manager()
            self.logger = get_logger("portfolio")
        except Exception as e:
            print(f"Error initializing config/logger: {e}")
            self.config_manager = None
            self.logger = None
        
        # Dane portfela
        self.portfolio_data = {}
        self.balances = {}
        self.transactions = []
        self.balance_data = []  # Lista danych o balansach dla kart
        
        # Timer odświeżania
        try:
            self.refresh_timer = QTimer()
            self.refresh_timer.timeout.connect(self.refresh_data)
        except Exception as e:
            print(f"Error creating refresh timer: {e}")
            self.refresh_timer = None
        
        try:
            self.setup_ui()
            self.load_current_trading_mode()
            self.start_refresh_timer()
        except Exception as e:
            print(f"Error setting up Portfolio UI: {e}")
            if hasattr(self, 'logger') and self.logger:
                self.logger.error(f"Portfolio UI setup failed: {e}")
    
    def setup_ui(self):
        """Konfiguracja interfejsu"""
        layout = QVBoxLayout(self)
        layout.setSpacing(20)
        
        # Nagłówek
        header_layout = QHBoxLayout()
        
        title = QLabel("Portfel")
        title.setStyleSheet("font-size: 24px; font-weight: bold;")
        header_layout.addWidget(title)
        
        header_layout.addStretch()
        
        # Przyciski akcji
        refresh_btn = QPushButton("🔄 Odśwież")
        refresh_btn.clicked.connect(self.refresh_data)
        header_layout.addWidget(refresh_btn)
        
        export_btn = QPushButton("📊 Eksportuj")
        export_btn.clicked.connect(self.export_portfolio)
        header_layout.addWidget(export_btn)
        
        layout.addLayout(header_layout)
        
        # Podsumowanie portfela
        self.setup_portfolio_summary(layout)
        
        # Tabs dla różnych widoków
        self.tabs = QTabWidget()
        
        # Tab: Salda
        self.setup_balances_tab()
        self.tabs.addTab(self.balances_widget, "Salda")
        
        # Tab: Historia transakcji
        self.transaction_history = TransactionHistoryWidget()
        self.tabs.addTab(self.transaction_history, "Historia Transakcji")
        
        # Tab: Statystyki
        self.portfolio_stats = PortfolioStatsWidget()
        self.tabs.addTab(self.portfolio_stats, "Statystyki")
        
        layout.addWidget(self.tabs)
    
    def setup_portfolio_summary(self, layout):
        """Konfiguruje podsumowanie portfela"""
        # Dodaj przełącznik trybu tradingowego
        self.setup_trading_mode_switch(layout)
        
        if CARDS_AVAILABLE:
            # Używaj nowej karty podsumowania
            self.portfolio_summary_card = PortfolioSummaryCard()
            layout.addWidget(self.portfolio_summary_card)
        else:
            # Fallback do starego stylu
            summary_frame = QFrame()
            summary_frame.setFrameStyle(QFrame.Shape.StyledPanel)
            summary_frame.setStyleSheet("""
                QFrame {
                    background-color: #f8f9fa;
                    border: 1px solid #dee2e6;
                    border-radius: 8px;
                    padding: 15px;
                }
            """)
            
            summary_layout = QHBoxLayout(summary_frame)
            
            # Całkowita wartość
            total_value_layout = QVBoxLayout()
            
            self.total_value_label = QLabel("$0.00")
            self.total_value_label.setStyleSheet("font-size: 32px; font-weight: bold; color: #2196F3;")
            total_value_layout.addWidget(self.total_value_label)
            
            total_value_title = QLabel("Całkowita Wartość Portfela")
            total_value_title.setStyleSheet("font-size: 14px; color: #666;")
            total_value_layout.addWidget(total_value_title)
            
            summary_layout.addLayout(total_value_layout)
            
            # Separator
            separator = QFrame()
            separator.setFrameShape(QFrame.Shape.VLine)
            separator.setFrameShadow(QFrame.Shadow.Sunken)
            summary_layout.addWidget(separator)
            
            # Zmiana 24h
            change_24h_layout = QVBoxLayout()
            
            self.change_24h_label = QLabel("$0.00 (0.00%)")
            self.change_24h_label.setStyleSheet("font-size: 18px; font-weight: bold;")
            change_24h_layout.addWidget(self.change_24h_label)
            
            change_24h_title = QLabel("Zmiana 24h")
            change_24h_title.setStyleSheet("font-size: 14px; color: #666;")
            change_24h_layout.addWidget(change_24h_title)
            
            summary_layout.addLayout(change_24h_layout)
            
            # Separator
            separator2 = QFrame()
            separator2.setFrameShape(QFrame.Shape.VLine)
            separator2.setFrameShadow(QFrame.Shadow.Sunken)
            summary_layout.addWidget(separator2)
            
            # P&L dzienny
            daily_pnl_layout = QVBoxLayout()
            
            self.daily_pnl_label = QLabel("$0.00")
            self.daily_pnl_label.setStyleSheet("font-size: 18px; font-weight: bold;")
            daily_pnl_layout.addWidget(self.daily_pnl_label)
            
            daily_pnl_title = QLabel("P&L Dzienny")
            daily_pnl_title.setStyleSheet("font-size: 14px; color: #666;")
            daily_pnl_layout.addWidget(daily_pnl_title)
            
            summary_layout.addLayout(daily_pnl_layout)
            
            summary_layout.addStretch()
            
            layout.addWidget(summary_frame)
    
    def setup_trading_mode_switch(self, layout):
        """Tworzy przełącznik trybu tradingowego"""
        if not PYQT_AVAILABLE:
            return
            
        try:
            # Kontener dla przełącznika
            mode_frame = QFrame()
            mode_frame.setStyleSheet("""
                QFrame {
                    background-color: #1a1a1a;
                    border: 1px solid #333333;
                    border-radius: 8px;
                    padding: 10px;
                    margin-bottom: 10px;
                }
            """)
            
            mode_layout = QHBoxLayout(mode_frame)
            
            # Etykieta trybu
            mode_label = QLabel("Tryb Trading:")
            mode_label.setStyleSheet("""
                QLabel {
                    color: #cccccc;
                    font-size: 12px;
                    font-weight: 500;
                }
            """)
            mode_layout.addWidget(mode_label)
            
            # Przełącznik Paper/Live
            self.trading_mode_combo = QComboBox()
            self.trading_mode_combo.addItems(["Paper Trading", "Live Trading"])
            self.trading_mode_combo.setStyleSheet("""
                QComboBox {
                    background-color: #2a2a2a;
                    color: #ffffff;
                    border: 1px solid #444444;
                    border-radius: 4px;
                    padding: 5px 10px;
                    min-width: 120px;
                }
                QComboBox::drop-down {
                    border: none;
                    width: 20px;
                }
                QComboBox::down-arrow {
                    image: none;
                    border-left: 5px solid transparent;
                    border-right: 5px solid transparent;
                    border-top: 5px solid #cccccc;
                    margin-right: 5px;
                }
                QComboBox QAbstractItemView {
                    background-color: #2a2a2a;
                    color: #ffffff;
                    border: 1px solid #444444;
                    selection-background-color: #444444;
                }
            """)
            self.trading_mode_combo.currentTextChanged.connect(self.on_trading_mode_changed)
            mode_layout.addWidget(self.trading_mode_combo)
            
            # Status trybu
            self.mode_status_label = QLabel("Paper Trading - Fikcyjne środki")
            self.mode_status_label.setStyleSheet("""
                QLabel {
                    color: #4CAF50;
                    font-size: 11px;
                    font-style: italic;
                }
            """)
            mode_layout.addWidget(self.mode_status_label)
            
            mode_layout.addStretch()
            
            # Przycisk odświeżania
            refresh_btn = QPushButton("🔄 Odśwież")
            refresh_btn.setStyleSheet("""
                QPushButton {
                    background-color: #007acc;
                    color: white;
                    border: none;
                    border-radius: 4px;
                    padding: 5px 10px;
                    font-size: 11px;
                }
                QPushButton:hover {
                    background-color: #005a9e;
                }
                QPushButton:pressed {
                    background-color: #004578;
                }
            """)
            refresh_btn.clicked.connect(self.refresh_data)
            mode_layout.addWidget(refresh_btn)
            
            layout.addWidget(mode_frame)
            
        except Exception as e:
            if hasattr(self, 'logger'):
                self.logger.error(f"Error creating trading mode switch: {e}")
            print(f"Trading mode switch error: {e}")
    
    def on_trading_mode_changed(self, mode_text):
        """Obsługuje zmianę trybu tradingowego"""
        try:
            if not hasattr(self, 'trading_manager'):
                from app.trading_mode_manager import TradingModeManager
                config = get_config_manager()
                self.trading_manager = TradingModeManager(config)
            
            # Ustaw tryb
            if mode_text == "Paper Trading":
                import asyncio
                from app.trading_mode_manager import TradingMode
                asyncio.run(self.trading_manager.switch_mode(TradingMode.PAPER))
                self.mode_status_label.setText("Paper Trading - Fikcyjne środki")
                self.mode_status_label.setStyleSheet("""
                    QLabel {
                        color: #4CAF50;
                        font-size: 11px;
                        font-style: italic;
                    }
                """)
            else:  # Live Trading
                import asyncio
                from app.trading_mode_manager import TradingMode
                asyncio.run(self.trading_manager.switch_mode(TradingMode.LIVE))
                self.mode_status_label.setText("Live Trading - Prawdziwe środki!")
                self.mode_status_label.setStyleSheet("""
                    QLabel {
                        color: #FF5722;
                        font-size: 11px;
                        font-style: italic;
                        font-weight: bold;
                    }
                """)
            
            # Odśwież dane po zmianie trybu
            self.refresh_data()
            
            if hasattr(self, 'logger'):
                self.logger.info(f"Trading mode changed to: {mode_text}")
                
        except Exception as e:
            if hasattr(self, 'logger'):
                self.logger.error(f"Error changing trading mode: {e}")
            print(f"Trading mode change error: {e}")
    
    def load_current_trading_mode(self):
        """Ładuje aktualny tryb trading z konfiguracji"""
        try:
            if not hasattr(self, 'trading_mode_combo'):
                return
                
            # Pobierz aktualny tryb z konfiguracji
            current_mode = self.config_manager.get_setting('app', 'trading.default_mode', 'paper')
            
            # Ustaw odpowiednią wartość w combobox
            if current_mode == 'paper':
                self.trading_mode_combo.setCurrentText("Paper Trading")
                self.mode_status_label.setText("Paper Trading - Fikcyjne środki")
                self.mode_status_label.setStyleSheet("""
                    QLabel {
                        color: #4CAF50;
                        font-size: 11px;
                        font-style: italic;
                    }
                """)
            else:  # live
                self.trading_mode_combo.setCurrentText("Live Trading")
                self.mode_status_label.setText("Live Trading - Prawdziwe środki!")
                self.mode_status_label.setStyleSheet("""
                    QLabel {
                        color: #FF5722;
                        font-size: 11px;
                        font-style: italic;
                        font-weight: bold;
                    }
                """)
                
            if hasattr(self, 'logger'):
                self.logger.info(f"Loaded trading mode from config: {current_mode}")
                
        except Exception as e:
            if hasattr(self, 'logger'):
                self.logger.error(f"Error loading trading mode: {e}")
            print(f"Trading mode load error: {e}")
    
    def setup_balances_tab(self):
        """Konfiguruje tab z saldami"""
        self.balances_widget = QWidget()
        layout = QVBoxLayout(self.balances_widget)
        layout.setSpacing(15)
        
        # Filtry i sortowanie
        controls_layout = QHBoxLayout()
        
        # Filtr ukrywania małych sald
        self.hide_small_balances = QCheckBox("Ukryj małe salda (< $1)")
        self.hide_small_balances.toggled.connect(self.update_balances_display)
        controls_layout.addWidget(self.hide_small_balances)
        
        controls_layout.addStretch()
        
        # Sortowanie
        controls_layout.addWidget(QLabel("Sortuj:"))
        self.sort_combo = QComboBox()
        self.sort_combo.addItems(["Wartość USD", "Saldo", "Symbol", "Zmiana 24h"])
        self.sort_combo.currentTextChanged.connect(self.update_balances_display)
        controls_layout.addWidget(self.sort_combo)
        
        layout.addLayout(controls_layout)
        
        # Scroll area dla kart sald
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        
        self.balances_container = QWidget()
        
        # Używaj FlowLayout dla responsywności jeśli dostępny
        if FLOW_LAYOUT_AVAILABLE:
            self.balances_layout = FlowLayout(self.balances_container)
            self.balances_layout.setSpacing(20)
            self.balances_layout.setContentsMargins(20, 20, 20, 20)
        else:
            # Fallback do QGridLayout
            self.balances_layout = QGridLayout(self.balances_container)
            self.balances_layout.setSpacing(20)
            self.balances_layout.setContentsMargins(20, 20, 20, 20)
        
        scroll.setWidget(self.balances_container)
        layout.addWidget(scroll)
    
    def start_refresh_timer(self):
        """Uruchamia timer odświeżania"""
        if not PYQT_AVAILABLE or not hasattr(self, 'refresh_timer') or not self.refresh_timer:
            return
            
        try:
            interval = get_ui_setting("portfolio.refresh_interval_seconds", 30) * 1000
            self.refresh_timer.start(interval)
            
            # Pierwsze odświeżenie
            self.refresh_data()
        except Exception as e:
            print(f"Error starting refresh timer: {e}")
            if hasattr(self, 'logger') and self.logger:
                self.logger.error(f"Failed to start refresh timer: {e}")
    
    def refresh_data(self):
        """Odświeża dane portfela"""
        if not PYQT_AVAILABLE:
            return
            
        if hasattr(self, 'logger'):
            self.logger.info("Portfolio refresh started - loading data from API")
            
        try:
            # Ładuj prawdziwe dane z API
            import asyncio
            try:
                if hasattr(self, 'logger'):
                    self.logger.info("Attempting to load real portfolio data from exchange API")
                asyncio.run(self.load_real_data())
            except RuntimeError:
                # Jeśli już jesteśmy w pętli asyncio, użyj synchronicznej wersji
                if hasattr(self, 'logger'):
                    self.logger.info("AsyncIO runtime error - falling back to sample data")
                asyncio.run(self.load_empty_data())
                
            if hasattr(self, 'logger'):
                self.logger.info("Updating portfolio UI components")
                
            self.update_portfolio_summary()
            self.update_balances_display()
            self.update_transaction_history()
            
            if hasattr(self, 'logger'):
                self.logger.info("Portfolio data refreshed successfully - UI updated")
            
        except Exception as e:
            if hasattr(self, 'logger'):
                self.logger.error(f"Error refreshing portfolio data: {e}")
            print(f"Portfolio refresh error: {e}")
            # Fallback do pustych danych
            import asyncio
            asyncio.run(self.load_empty_data())
    
    async def load_real_data(self):
        """Ładuje prawdziwe dane portfolio z API"""
        try:
            if hasattr(self, 'production_manager') and self.production_manager:
                # Pobierz prawdziwe saldo
                balance = await self.production_manager.get_real_balance()
                
                if balance:
                    # Oblicz wartość portfolio
                    total_value = 0.0
                    real_balances = {}
                    
                    for currency, data in balance.items():
                        if data['total'] > 0:
                            # Pobierz aktualną cenę
                            if currency != 'USDT':
                                price = await self.production_manager.get_real_price(f"{currency}/USDT")
                                if price:
                                    usd_value = data['total'] * price
                                    total_value += usd_value
                                    
                                    real_balances[currency] = {
                                        'balance': data['total'],
                                        'usd_value': usd_value,
                                        'change_24h': 0.0,  # TODO: Oblicz zmianę 24h
                                        'price': price
                                    }
                            else:
                                # USDT = 1:1
                                total_value += data['total']
                                real_balances[currency] = {
                                    'balance': data['total'],
                                    'usd_value': data['total'],
                                    'change_24h': 0.0,
                                    'price': 1.0
                                }
                    
                    self.portfolio_data = {
                        'total_value': total_value,
                        'change_24h': 0.0,  # TODO: Oblicz zmianę 24h
                        'change_24h_percent': 0.0,
                        'daily_pnl': 0.0
                    }
                    
                    self.balances = real_balances
                    
                    # Aktualizuj balance_data dla kart portfela
                    self.balance_data = []
                    for symbol, data in self.balances.items():
                        balance_entry = data.copy()
                        balance_entry['symbol'] = symbol
                        balance_entry['exchange'] = 'Production'  # Produkcyjna giełda
                        balance_entry['last_update'] = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                        self.balance_data.append(balance_entry)
                    
                    self.update_portfolio_display()
                    return
            
            # Fallback do pustych danych
            import asyncio
            asyncio.run(self.load_empty_data())
            
        except Exception as e:
            print(f"Błąd ładowania prawdziwych danych portfolio: {e}")
            import asyncio
            asyncio.run(self.load_empty_data())
    
    def set_production_manager(self, manager):
        """Ustawia Production Data Manager"""
        self.production_manager = manager
    
    async def load_binance_balances(self):
        """Pobiera rzeczywiste salda z API Binance"""
        try:
            # Import modułów API
            from app.api_config_manager import APIConfigManager
            from app.exchange import get_exchange_adapter
            
            # Pobierz konfigurację API
            api_manager = APIConfigManager()
            binance_config = api_manager.get_exchange_config('binance')
            
            if not binance_config or not binance_config.get('enabled'):
                if hasattr(self, 'logger'):
                    self.logger.info("Binance API nie jest skonfigurowane lub wyłączone")
                return None
            
            if not binance_config.get('api_key') or not binance_config.get('secret'):
                if hasattr(self, 'logger'):
                    self.logger.warning("Brak kluczy API Binance")
                return None
            
            # Utwórz adapter Binance
            binance = get_exchange_adapter(
                'binance',
                api_key=binance_config['api_key'],
                api_secret=binance_config['secret'],
                testnet=binance_config.get('sandbox', True)
            )
            
            # Połącz z giełdą
            await binance.connect()
            
            # Pobierz salda
            raw_balances = await binance.get_balance()
            
            if not raw_balances:
                if hasattr(self, 'logger'):
                    self.logger.warning("Nie udało się pobrać sald z Binance")
                return None
            
            # Konwertuj salda do formatu portfolio
            balances = {}
            total_value = 0.0
            
            # Lista głównych kryptowalut do wyświetlenia
            major_cryptos = ['BTC', 'ETH', 'BNB', 'ADA', 'DOT', 'LINK', 'LTC', 'XRP', 'SOL', 'AVAX']
            
            for currency, balance_info in raw_balances.items():
                balance = balance_info.get('total', 0.0)
                
                # Pomiń zerowe salda i bardzo małe kwoty (poniżej $1)
                if balance <= 0 or (currency != 'USDT' and balance < 0.001):
                    continue
                
                # Pobierz aktualną cenę
                current_price = 0.0
                if currency == 'USDT':
                    current_price = 1.0
                else:
                    try:
                        price = await binance.get_current_price(f"{currency}/USDT")
                        current_price = price if price else 0.0
                    except:
                        current_price = 0.0
                
                usd_value = balance * current_price
                
                # Dodaj tylko jeśli wartość USD > $1 lub to główna kryptowaluta
                if usd_value > 1.0 or currency in major_cryptos:
                    balances[currency] = {
                        'balance': balance,
                        'usd_value': usd_value,
                        'change_24h': 0.0,  # TODO: Pobierz rzeczywistą zmianę 24h
                        'price': current_price
                    }
                    total_value += usd_value
            
            # Zamknij połączenie
            await binance.disconnect()
            
            portfolio_data = {
                'total_value': total_value,
                'change_24h': 0.0,  # TODO: Oblicz rzeczywistą zmianę 24h
                'change_24h_percent': 0.0,
                'daily_pnl': 0.0  # TODO: Oblicz rzeczywisty PnL
            }
            
            if hasattr(self, 'logger'):
                self.logger.info(f"Loaded real balances from Binance: {len(balances)} currencies, total value: ${total_value:.2f}")
            
            return {
                'balances': balances,
                'portfolio_data': portfolio_data
            }
            
        except Exception as e:
            if hasattr(self, 'logger'):
                self.logger.error(f"Error loading Binance balances: {e}")
            print(f"Binance API error: {e}")
            return None
    
    async def load_database_data(self):
        """Ładuje dane z bazy danych i API Binance"""
        if not DATABASE_AVAILABLE:
            await self.load_empty_data()
            return
            
        try:
            # Najpierw spróbuj pobrać rzeczywiste salda z API Binance
            real_balances = await self.load_binance_balances()
            
            if real_balances:
                # Jeśli udało się pobrać z API, użyj tych danych
                self.balances = real_balances['balances']
                self.portfolio_data = real_balances['portfolio_data']
                
                # Pobierz transakcje z bazy danych dla historii
                db = Database()
                orders = await db.get_bot_orders(bot_id=1, status='filled', limit=1000)
                
                transactions = []
                if orders:
                    for order in orders:
                        transaction = {
                            'timestamp': order.get('timestamp', datetime.now().isoformat()),
                            'bot_id': order.get('bot_id', 'unknown'),
                            'pair': order.get('symbol', 'UNKNOWN'),
                            'side': order.get('side', 'buy'),
                            'amount': float(order.get('amount', 0)),
                            'price': float(order.get('price', 0)),
                            'status': order.get('status', 'filled'),
                            'fee': float(order.get('fee', 0))
                        }
                        transactions.append(transaction)
                
                self.transactions = transactions
                
                # Aktualizuj balance_data dla kart portfela
                self.balance_data = []
                for symbol, data in self.balances.items():
                    balance_entry = data.copy()
                    balance_entry['symbol'] = symbol
                    balance_entry['exchange'] = 'Binance'  # Rzeczywista giełda
                    balance_entry['last_update'] = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                    self.balance_data.append(balance_entry)
                
                if hasattr(self, 'logger'):
                    self.logger.info(f"Loaded real balances from Binance API and {len(transactions)} transactions from database")
                return
            
            # Fallback: ładuj dane z bazy danych jak wcześniej
            db = Database()
            orders = await db.get_bot_orders(bot_id=1, status='filled', limit=1000)
            
            total_value = 0.0
            balances = {}
            transactions = []
            
            if orders:
                for order in orders:
                    transaction = {
                        'timestamp': order.get('timestamp', datetime.now().isoformat()),
                        'bot_id': order.get('bot_id', 'unknown'),
                        'pair': order.get('symbol', 'UNKNOWN'),
                        'side': order.get('side', 'buy'),
                        'amount': float(order.get('amount', 0)),
                        'price': float(order.get('price', 0)),
                        'status': order.get('status', 'filled'),
                        'fee': float(order.get('fee', 0))
                    }
                    transactions.append(transaction)
                    
                    # Oblicz saldo dla każdej waluty
                    symbol = order.get('symbol', 'UNKNOWN')
                    if symbol.endswith('USDT'):
                        base_currency = symbol[:-4]  # Usuń USDT
                        amount = float(order.get('amount', 0))
                        price = float(order.get('price', 0))
                        
                        if base_currency not in balances:
                            balances[base_currency] = {
                                'balance': 0.0,
                                'usd_value': 0.0,
                                'change_24h': 0.0,
                                'price': price
                            }
                        
                        if order.get('side') == 'buy':
                            balances[base_currency]['balance'] += amount
                        else:
                            balances[base_currency]['balance'] -= amount
                        
                        balances[base_currency]['usd_value'] = balances[base_currency]['balance'] * price
                        total_value += balances[base_currency]['usd_value']
            
            # Jeśli nie ma danych w bazie, użyj pustych danych
            if not orders:
                await self.load_empty_data()
                return
                
            self.portfolio_data = {
                'total_value': total_value,
                'change_24h': total_value * 0.05,  # 5% przykładowa zmiana
                'change_24h_percent': 5.0,
                'daily_pnl': total_value * 0.02  # 2% przykładowy PnL
            }
            
            self.balances = balances
            self.transactions = transactions
            
            # Aktualizuj balance_data dla kart portfela
            self.balance_data = []
            for symbol, data in self.balances.items():
                balance_entry = data.copy()
                balance_entry['symbol'] = symbol
                balance_entry['exchange'] = 'Binance'  # Przykładowa giełda
                balance_entry['last_update'] = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                self.balance_data.append(balance_entry)
            
            if hasattr(self, 'logger'):
                self.logger.info(f"Loaded {len(transactions)} transactions from database (fallback mode)")
                
        except Exception as e:
            if hasattr(self, 'logger'):
                self.logger.error(f"Error loading database data: {e}")
            print(f"Database load error: {e}")
            # Fallback do pustych danych
            await self.load_empty_data()

    async def load_real_data(self):
        """Ładuje prawdziwe dane z API przez TradingModeManager"""
        try:
            if not hasattr(self, 'trading_manager'):
                from app.trading_mode_manager import TradingModeManager
                config = get_config_manager()
                self.trading_manager = TradingModeManager(config)
                await self.trading_manager.initialize()
            
            # Pobierz aktualne salda w zależności od trybu (Paper/Live)
            self.balances = await self.trading_manager.get_current_balances()
            
            # Pobierz statystyki handlowe
            stats = await self.trading_manager.get_trading_statistics()
            
            # Oblicz dane portfela
            total_value = stats.get('total_value', 0.0)
            total_pnl = stats.get('total_pnl', 0.0)
            
            self.portfolio_data = {
                'total_value': total_value,
                'change_24h': total_pnl,
                'change_24h_percent': (total_pnl / (total_value - total_pnl)) * 100 if total_value > total_pnl else 0.0,
                'daily_pnl': total_pnl,
                'mode': stats.get('mode', 'paper'),
                'trades_count': stats.get('trades_count', 0),
                'initial_balance': stats.get('initial_balance', 0.0)
            }
            
            # Aktualizuj balance_data dla kart portfela
            self.balance_data = []
            for symbol, data in self.balances.items():
                balance_entry = data.copy()
                balance_entry['symbol'] = symbol
                balance_entry['exchange'] = 'Binance'  # Domyślna giełda
                balance_entry['last_update'] = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                self.balance_data.append(balance_entry)
            
            self.logger.info(f"Załadowano prawdziwe dane portfela w trybie: {self.portfolio_data.get('mode', 'unknown')}")
            
        except Exception as e:
            self.logger.error(f"Błąd ładowania prawdziwych danych: {e}")
            # Fallback do pustych danych
            await self.load_empty_data()
    
    async def load_empty_data(self):
        """Ładuje puste dane jako fallback"""
        self.portfolio_data = {
            'total_value': 0.0,
            'change_24h': 0.0,
            'change_24h_percent': 0.0,
            'daily_pnl': 0.0,
            'mode': 'paper',
            'trades_count': 0,
            'initial_balance': 0.0
        }
        
        self.balances = {}
        self.balance_data = []

        # Więcej przykładowych transakcji
        self.transactions = [
            {
                'timestamp': datetime.now() - timedelta(minutes=30),
                'bot_id': 1,
                'pair': 'BTC/USDT',
                'side': 'buy',
                'amount': 0.002,
                'price': 45230.00,
                'status': 'filled',
                'fee': 0.90
            },
            {
                'timestamp': datetime.now() - timedelta(hours=1),
                'bot_id': 2,
                'pair': 'ETH/USDT',
                'side': 'sell',
                'amount': 0.15,
                'price': 2995.00,
                'status': 'filled',
                'fee': 0.45
            },
            {
                'timestamp': datetime.now() - timedelta(hours=2),
                'bot_id': 3,
                'pair': 'SOL/USDT',
                'side': 'buy',
                'amount': 5.0,
                'price': 149.80,
                'status': 'filled',
                'fee': 0.75
            },
            {
                'timestamp': datetime.now() - timedelta(hours=3),
                'bot_id': 1,
                'pair': 'ADA/USDT',
                'side': 'buy',
                'amount': 1000,
                'price': 0.495,
                'status': 'filled',
                'fee': 0.25
            },
            {
                'timestamp': datetime.now() - timedelta(hours=4),
                'bot_id': 2,
                'pair': 'DOT/USDT',
                'side': 'sell',
                'amount': 50,
                'price': 7.15,
                'status': 'filled',
                'fee': 0.18
            },
            {
                'timestamp': datetime.now() - timedelta(hours=6),
                'bot_id': 3,
                'pair': 'BTC/USDT',
                'side': 'buy',
                'amount': 0.001,
                'price': 44890.00,
                'status': 'filled',
                'fee': 0.45
            },
            {
                'timestamp': datetime.now() - timedelta(hours=8),
                'bot_id': 1,
                'pair': 'ETH/USDT',
                'side': 'sell',
                'amount': 0.2,
                'price': 3010.00,
                'status': 'filled',
                'fee': 0.60
            },
            {
                'timestamp': datetime.now() - timedelta(hours=12),
                'bot_id': 2,
                'pair': 'SOL/USDT',
                'side': 'buy',
                'amount': 10,
                'price': 148.50,
                'status': 'filled',
                'fee': 1.49
            },
            {
                'timestamp': datetime.now() - timedelta(days=1),
                'bot_id': 3,
                'pair': 'ADA/USDT',
                'side': 'sell',
                'amount': 500,
                'price': 0.505,
                'status': 'filled',
                'fee': 0.13
            },
            {
                'timestamp': datetime.now() - timedelta(days=1, hours=2),
                'bot_id': 1,
                'pair': 'DOT/USDT',
                'side': 'buy',
                'amount': 70,
                'price': 6.95,
                'status': 'filled',
                'fee': 0.49
            }
        ]
        
        # Dodaj logowanie dla debugowania
        if hasattr(self, 'logger') and self.logger:
            self.logger.info(f"Loaded sample data: {len(self.balances)} balances, {len(self.transactions)} transactions")
            self.logger.info(f"Total portfolio value: ${self.portfolio_data['total_value']:,.2f}")

    def update_portfolio_summary(self):
        """Aktualizuje podsumowanie portfela"""
        total_value = self.portfolio_data.get('total_value', 0)
        change_24h = self.portfolio_data.get('change_24h', 0)
        change_24h_percent = self.portfolio_data.get('change_24h_percent', 0)
        daily_pnl = self.portfolio_data.get('daily_pnl', 0)
        mode = self.portfolio_data.get('mode', 'paper')
        trades_count = self.portfolio_data.get('trades_count', 0)
        initial_balance = self.portfolio_data.get('initial_balance', 0)
        
        # Aktualizuj przełącznik trybu
        if hasattr(self, 'trading_mode_combo'):
            current_mode = "Paper Trading" if mode == 'paper' else "Live Trading"
            if self.trading_mode_combo.currentText() != current_mode:
                self.trading_mode_combo.blockSignals(True)
                self.trading_mode_combo.setCurrentText(current_mode)
                self.trading_mode_combo.blockSignals(False)
        
        if hasattr(self, 'mode_status_label'):
            if mode == 'paper':
                self.mode_status_label.setText(f"Paper Trading - Fikcyjne środki (Start: ${initial_balance:,.2f})")
                self.mode_status_label.setStyleSheet("""
                    QLabel {
                        color: #4CAF50;
                        font-size: 11px;
                        font-style: italic;
                    }
                """)
            else:
                self.mode_status_label.setText(f"Live Trading - Prawdziwe środki! ({trades_count} transakcji)")
                self.mode_status_label.setStyleSheet("""
                    QLabel {
                        color: #FF5722;
                        font-size: 11px;
                        font-style: italic;
                        font-weight: bold;
                    }
                """)
        
        if CARDS_AVAILABLE and hasattr(self, 'portfolio_summary_card'):
            # Używaj nowej karty
            summary_data = {
                'total_value': total_value,
                'change_24h': change_24h,
                'change_24h_percent': change_24h_percent,
                'daily_pnl': daily_pnl,
                'asset_count': len(self.balances),
                'best_performer': self.get_best_performer(),
                'mode': mode,
                'trades_count': trades_count,
                'initial_balance': initial_balance
            }
            self.portfolio_summary_card.update_data(summary_data)
        else:
            # Fallback do starych etykiet
            if hasattr(self, 'total_value_label'):
                self.total_value_label.setText(f"${total_value:,.2f}")
            
            # Zmiana 24h z kolorami
            if hasattr(self, 'change_24h_label'):
                change_color = "#4CAF50" if change_24h >= 0 else "#F44336"
                self.change_24h_label.setText(f"${change_24h:+,.2f} ({change_24h_percent:+.2f}%)")
                self.change_24h_label.setStyleSheet(f"font-size: 18px; font-weight: bold; color: {change_color};")
            
            # P&L dzienny z kolorami
            if hasattr(self, 'daily_pnl_label'):
                pnl_color = "#4CAF50" if daily_pnl >= 0 else "#F44336"
                self.daily_pnl_label.setText(f"${daily_pnl:+,.2f}")
                self.daily_pnl_label.setStyleSheet(f"font-size: 18px; font-weight: bold; color: {pnl_color};")
    
    def update_balances_display(self):
        """Aktualizuje wyświetlanie sald"""
        if not PYQT_AVAILABLE or not hasattr(self, 'balances_layout'):
            return
            
        try:
            # Wyczyść obecne karty
            for i in reversed(range(self.balances_layout.count())):
                item = self.balances_layout.itemAt(i)
                if item:
                    child = item.widget()
                    if child:
                        child.setParent(None)
            
            # Filtruj i sortuj salda
            filtered_balances = self.get_filtered_sorted_balances()
            
            # Dodaj karty sald
            if FLOW_LAYOUT_AVAILABLE:
                # Używaj FlowLayout - dodawaj karty bezpośrednio
                for symbol, balance_data in filtered_balances.items():
                    try:
                        if CARDS_AVAILABLE:
                            # Używaj nowej karty - dodaj symbol do balance_data
                            balance_data_with_symbol = balance_data.copy()
                            balance_data_with_symbol['symbol'] = symbol
                            card = BalanceCard(balance_data_with_symbol)
                            # Podłącz sygnały - używaj domyślnych argumentów w lambda
                            card.trade_requested.connect(lambda s, symbol=symbol: self.handle_trade_request(symbol))
                            card.details_requested.connect(lambda s, symbol=symbol: self.handle_details_request(symbol))
                        else:
                            # Fallback do prostego widgetu
                            card = QLabel(f"{symbol}: {balance_data.get('balance', 0):.8f}")
                            card.setStyleSheet("border: 1px solid #ccc; padding: 10px; border-radius: 5px;")
                        
                        self.balances_layout.addWidget(card)
                        
                    except Exception as e:
                        print(f"Error creating balance card for {symbol}: {e}")
                        continue
            else:
                # Fallback do QGridLayout
                row, col = 0, 0
                max_cols = 3
                
                for symbol, balance_data in filtered_balances.items():
                    try:
                        if CARDS_AVAILABLE:
                            # Używaj nowej karty - dodaj symbol do balance_data
                            balance_data_with_symbol = balance_data.copy()
                            balance_data_with_symbol['symbol'] = symbol
                            card = BalanceCard(balance_data_with_symbol)
                            # Podłącz sygnały - używaj domyślnych argumentów w lambda
                            card.trade_requested.connect(lambda s, symbol=symbol: self.handle_trade_request(symbol))
                            card.details_requested.connect(lambda s, symbol=symbol: self.handle_details_request(symbol))
                        else:
                            # Fallback do prostego widgetu
                            card = QLabel(f"{symbol}: {balance_data.get('balance', 0):.8f}")
                            card.setStyleSheet("border: 1px solid #ccc; padding: 10px; border-radius: 5px;")
                        
                        self.balances_layout.addWidget(card, row, col)
                        
                        col += 1
                        if col >= max_cols:
                            col = 0
                            row += 1
                    except Exception as e:
                        print(f"Error creating balance card for {symbol}: {e}")
                        continue
                
                # Dodaj stretch na końcu
                try:
                    self.balances_layout.setRowStretch(row + 1, 1)
                except:
                    pass
                
        except Exception as e:
            print(f"Error updating balances display: {e}")
    
    def get_filtered_sorted_balances(self) -> Dict:
        """Zwraca przefiltrowane i posortowane salda"""
        filtered = {}
        
        for symbol, data in self.balances.items():
            # Filtruj małe salda jeśli włączone
            if self.hide_small_balances.isChecked():
                if data.get('usd_value', 0) < 1.0:
                    continue
            
            filtered[symbol] = data
        
        # Sortuj
        sort_by = self.sort_combo.currentText()
        
        if sort_by == "Wartość USD":
            filtered = dict(sorted(filtered.items(), 
                                 key=lambda x: x[1].get('usd_value', 0), 
                                 reverse=True))
        elif sort_by == "Saldo":
            filtered = dict(sorted(filtered.items(), 
                                 key=lambda x: x[1].get('balance', 0), 
                                 reverse=True))
        elif sort_by == "Symbol":
            filtered = dict(sorted(filtered.items()))
        elif sort_by == "Zmiana 24h":
            filtered = dict(sorted(filtered.items(), 
                                 key=lambda x: x[1].get('change_24h', 0), 
                                 reverse=True))
        
        return filtered
    
    def update_transaction_history(self):
        """Aktualizuje historię transakcji"""
        self.transaction_history.load_transactions(self.transactions)
    
    def export_portfolio(self):
        """Eksportuje dane portfela"""
        file_path, file_type = QFileDialog.getSaveFileName(
            self, "Eksportuj Portfel", 
            f"portfolio_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json",
            "JSON Files (*.json);;CSV Files (*.csv)"
        )
        
        if file_path:
            try:
                # Przygotuj dane do eksportu
                portfolio_data = {
                    'timestamp': datetime.now().isoformat(),
                    'total_value': sum(data.get('usd_value', 0) for data in self.balances.values()),
                    'balances': self.balances,
                    'transactions': self.transactions,
                    'summary': {
                        'total_assets': len(self.balances),
                        'total_transactions': len(self.transactions),
                        'daily_pnl': sum(data.get('change_24h_usd', 0) for data in self.balances.values())
                    }
                }
                
                if file_type == "CSV Files (*.csv)" or file_path.endswith('.csv'):
                    # Eksport CSV - tylko salda
                    import csv
                    with open(file_path, 'w', newline='', encoding='utf-8') as csvfile:
                        fieldnames = ['symbol', 'balance', 'usd_value', 'change_24h', 'change_24h_usd']
                        writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
                        
                        writer.writeheader()
                        for symbol, data in self.balances.items():
                            row = {
                                'symbol': symbol,
                                'balance': data.get('balance', 0),
                                'usd_value': data.get('usd_value', 0),
                                'change_24h': data.get('change_24h', 0),
                                'change_24h_usd': data.get('change_24h_usd', 0)
                            }
                            writer.writerow(row)
                else:
                    # Eksport JSON
                    import json
                    with open(file_path, 'w', encoding='utf-8') as jsonfile:
                        json.dump(portfolio_data, jsonfile, indent=2, ensure_ascii=False, default=str)
                
                QMessageBox.information(self, "Eksport", f"Portfel wyeksportowany do:\n{file_path}")
            except Exception as e:
                QMessageBox.critical(self, "Błąd", f"Nie udało się wyeksportować:\n{e}")

    def get_best_performer(self):
        """Zwraca najlepiej radzący sobie asset"""
        if not self.balances:
            return "N/A"
        
        best_symbol = max(self.balances.keys(), 
                         key=lambda x: self.balances[x].get('change_24h', 0))
        best_change = self.balances[best_symbol].get('change_24h', 0)
        return f"{best_symbol} (+{best_change:.2f}%)"
    
    def handle_trade_request(self, symbol):
        """Obsługuje żądanie handlu dla danego symbolu"""
        try:
            from PyQt6.QtWidgets import QMessageBox
            
            # Tworzymy okno dialogowe z opcjami handlu
            msg = QMessageBox(self)
            msg.setWindowTitle(f"Handel - {symbol}")
            msg.setText(f"Wybierz akcję dla {symbol}:")
            msg.setInformativeText("Co chcesz zrobić z tym zasobem?")
            
            # Dodajemy przyciski
            buy_btn = msg.addButton("💰 Kup więcej", QMessageBox.ButtonRole.ActionRole)
            sell_btn = msg.addButton("💸 Sprzedaj", QMessageBox.ButtonRole.ActionRole)
            cancel_btn = msg.addButton("❌ Anuluj", QMessageBox.ButtonRole.RejectRole)
            
            msg.setDefaultButton(cancel_btn)
            msg.exec()
            
            # Obsługujemy wybór użytkownika
            if msg.clickedButton() == buy_btn:
                self.show_buy_dialog(symbol)
            elif msg.clickedButton() == sell_btn:
                self.show_sell_dialog(symbol)
                
        except Exception as e:
            print(f"Błąd podczas obsługi żądania handlu: {e}")
    
    def handle_details_request(self, symbol):
        """Obsługuje żądanie szczegółów dla danego symbolu"""
        try:
            from PyQt6.QtWidgets import QMessageBox
            
            # Pobieramy dane o symbolu
            balance_data = None
            for data in self.balance_data:
                if data.get('symbol') == symbol:
                    balance_data = data
                    break
            
            if not balance_data:
                QMessageBox.warning(self, "Błąd", f"Nie znaleziono danych dla {symbol}")
                return
            
            # Tworzymy szczegółowe okno informacyjne
            msg = QMessageBox(self)
            msg.setWindowTitle(f"Szczegóły - {symbol}")
            
            # Formatujemy szczegółowe informacje
            details = f"""
📊 Szczegółowe informacje o {symbol}:

💰 Saldo: {balance_data.get('balance', 'N/A')}
💵 Wartość USD: ${balance_data.get('value_usd', 'N/A')}
📈 Zmiana 24h: {balance_data.get('change_24h', 'N/A')}%
🏷️ Cena: ${balance_data.get('price', 'N/A')}

📍 Giełda: {balance_data.get('exchange', 'N/A')}
🔄 Ostatnia aktualizacja: {balance_data.get('last_update', 'N/A')}
            """
            
            msg.setText(details)
            msg.setIcon(QMessageBox.Icon.Information)
            msg.exec()
            
        except Exception as e:
            print(f"Błąd podczas wyświetlania szczegółów: {e}")
    
    def show_buy_dialog(self, symbol):
        """Pokazuje dialog kupna"""
        from PyQt6.QtWidgets import QInputDialog, QMessageBox
        
        try:
            amount, ok = QInputDialog.getDouble(
                self, 
                f"Kup {symbol}", 
                f"Ile {symbol} chcesz kupić?",
                0.0, 0.0, 999999.99, 8
            )
            
            if ok and amount > 0:
                QMessageBox.information(
                    self, 
                    "Zlecenie kupna", 
                    f"Zlecenie kupna {amount} {symbol} zostało wysłane!\n\n"
                    f"(To jest demo - prawdziwe zlecenie nie zostało wykonane)"
                )
            
        except Exception as e:
            QMessageBox.critical(self, "Błąd", f"Błąd podczas składania zlecenia: {e}")
    
    def show_sell_dialog(self, symbol):
        """Pokazuje dialog sprzedaży"""
        from PyQt6.QtWidgets import QInputDialog, QMessageBox
        
        try:
            # Pobieramy aktualne saldo
            current_balance = 0.0
            for data in self.balance_data:
                if data.get('symbol') == symbol:
                    try:
                        current_balance = float(data.get('balance', 0))
                    except (ValueError, TypeError):
                        current_balance = 0.0
                    break
            
            if current_balance <= 0:
                QMessageBox.warning(self, "Błąd", f"Nie masz wystarczającego salda {symbol} do sprzedaży")
                return
            
            amount, ok = QInputDialog.getDouble(
                self, 
                f"Sprzedaj {symbol}", 
                f"Ile {symbol} chcesz sprzedać?\nDostępne: {current_balance}",
                0.0, 0.0, current_balance, 8
            )
            
            if ok and amount > 0:
                if amount <= current_balance:
                    QMessageBox.information(
                        self, 
                        "Zlecenie sprzedaży", 
                        f"Zlecenie sprzedaży {amount} {symbol} zostało wysłane!\n\n"
                        f"(To jest demo - prawdziwe zlecenie nie zostało wykonane)"
                    )
                else:
                    QMessageBox.warning(self, "Błąd", "Nie masz wystarczającego salda!")
            
        except Exception as e:
            QMessageBox.critical(self, "Błąd", f"Błąd podczas składania zlecenia: {e}")




def main():
    """Funkcja główna do testowania"""
    if not PYQT_AVAILABLE:
        print("PyQt6 is not available. Please install it to run the GUI.")
        return
    
    import sys
    from PyQt6.QtWidgets import QApplication
    
    app = QApplication(sys.argv)
    
    widget = PortfolioWidget()
    widget.show()
    
    sys.exit(app.exec())

if __name__ == "__main__":
    main()
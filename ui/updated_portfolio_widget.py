"""
Updated Portfolio Widget - Zintegrowany z nową architekturą danych

Widget portfela używający IntegratedDataManager dla spójnego przepływu danych.
"""

import sys
import asyncio
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
except ImportError as e:
    print(f"PyQt6 import error in updated_portfolio_widget.py: {e}")
    PYQT_AVAILABLE = False
    # Fallback classes
    class QWidget: pass
    class QVBoxLayout: pass
    class QHBoxLayout: pass
    class QLabel: pass
    class QPushButton: pass

import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from utils.config_manager import get_config_manager, get_ui_setting, get_app_setting
from utils.logger import get_logger, LogType
from utils.helpers import FormatHelper, CalculationHelper

# Import UI components
try:
    from ui.flow_layout import FlowLayout
    FLOW_LAYOUT_AVAILABLE = True
except ImportError:
    FLOW_LAYOUT_AVAILABLE = False

try:
    from ui.balance_card import BalanceCard
    from ui.portfolio_summary_card import PortfolioSummaryCard, StatCard
    CARDS_AVAILABLE = True
except ImportError:
    CARDS_AVAILABLE = False

class PortfolioSummaryCard(QWidget):
    """Karta podsumowania portfela z animacjami"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setup_ui()
        self.apply_style()
    
    def setup_ui(self):
        """Konfiguracja UI karty podsumowania"""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(15)
        
        # Tytuł
        title = QLabel("Podsumowanie Portfela")
        title.setObjectName("summaryTitle")
        layout.addWidget(title)
        
        # Główne metryki
        metrics_layout = QHBoxLayout()
        
        # Całkowita wartość
        self.total_value_label = QLabel("$0.00")
        self.total_value_label.setObjectName("totalValue")
        metrics_layout.addWidget(self.total_value_label)
        
        # Zmiana 24h
        self.change_24h_label = QLabel("$0.00 (0.00%)")
        self.change_24h_label.setObjectName("change24h")
        metrics_layout.addWidget(self.change_24h_label)
        
        # Dzienny P&L
        self.daily_pnl_label = QLabel("$0.00")
        self.daily_pnl_label.setObjectName("dailyPnL")
        metrics_layout.addWidget(self.daily_pnl_label)
        
        layout.addLayout(metrics_layout)
        
        # Liczba aktywów
        self.assets_count_label = QLabel("0 aktywów")
        self.assets_count_label.setObjectName("assetsCount")
        layout.addWidget(self.assets_count_label)
    
    def apply_style(self):
        """Zastosuj style do karty"""
        self.setStyleSheet("""
            QWidget {
                background-color: #ffffff;
                border: 1px solid #e0e0e0;
                border-radius: 12px;
                margin: 5px;
            }
            QLabel#summaryTitle {
                font-size: 18px;
                font-weight: bold;
                color: #333333;
            }
            QLabel#totalValue {
                font-size: 24px;
                font-weight: bold;
                color: #2196F3;
            }
            QLabel#change24h {
                font-size: 16px;
                font-weight: 500;
            }
            QLabel#dailyPnL {
                font-size: 16px;
                font-weight: 500;
            }
            QLabel#assetsCount {
                font-size: 14px;
                color: #666666;
            }
        """)
    
    def update_data(self, portfolio_data: Dict[str, Any]):
        """Aktualizuj dane w karcie"""
        try:
            # Całkowita wartość
            total_value = portfolio_data.get('total_value', 0.0)
            self.total_value_label.setText(f"${total_value:,.2f}")
            
            # Zmiana 24h
            change_24h = portfolio_data.get('change_24h', 0.0)
            change_24h_percent = portfolio_data.get('change_24h_percent', 0.0)
            change_color = "#4CAF50" if change_24h >= 0 else "#F44336"
            change_sign = "+" if change_24h >= 0 else ""
            
            self.change_24h_label.setText(f"{change_sign}${change_24h:.2f} ({change_sign}{change_24h_percent:.2f}%)")
            self.change_24h_label.setStyleSheet(f"color: {change_color};")
            
            # Dzienny P&L
            daily_pnl = portfolio_data.get('daily_pnl', 0.0)
            pnl_color = "#4CAF50" if daily_pnl >= 0 else "#F44336"
            pnl_sign = "+" if daily_pnl >= 0 else ""
            
            self.daily_pnl_label.setText(f"{pnl_sign}${daily_pnl:.2f}")
            self.daily_pnl_label.setStyleSheet(f"color: {pnl_color};")
            
            # Liczba aktywów
            assets_count = portfolio_data.get('assets_count', 0)
            self.assets_count_label.setText(f"{assets_count} aktywów")
            
        except Exception as e:
            print(f"Error updating portfolio summary: {e}")

class BalanceCard(QWidget):
    """Karta pojedynczego balansu"""
    
    def __init__(self, symbol: str, balance_data: Dict[str, Any], parent=None):
        super().__init__(parent)
        self.symbol = symbol
        self.balance_data = balance_data
        self.setup_ui()
        self.apply_style()
    
    def setup_ui(self):
        """Konfiguracja UI karty balansu"""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(15, 15, 15, 15)
        layout.setSpacing(8)
        
        # Symbol
        symbol_label = QLabel(self.symbol)
        symbol_label.setObjectName("symbolLabel")
        layout.addWidget(symbol_label)
        
        # Balance
        balance = self.balance_data.get('balance', 0.0)
        self.balance_label = QLabel(f"{balance:.8f}")
        self.balance_label.setObjectName("balanceLabel")
        layout.addWidget(self.balance_label)
        
        # USD Value
        usd_value = self.balance_data.get('usd_value', 0.0)
        self.usd_value_label = QLabel(f"${usd_value:.2f}")
        self.usd_value_label.setObjectName("usdValueLabel")
        layout.addWidget(self.usd_value_label)
        
        # Price
        price = self.balance_data.get('price', 0.0)
        self.price_label = QLabel(f"${price:.4f}")
        self.price_label.setObjectName("priceLabel")
        layout.addWidget(self.price_label)
    
    def apply_style(self):
        """Zastosuj style do karty"""
        self.setStyleSheet("""
            QWidget {
                background-color: #ffffff;
                border: 1px solid #e0e0e0;
                border-radius: 8px;
                margin: 3px;
            }
            QWidget:hover {
                border-color: #2196F3;
                box-shadow: 0 2px 8px rgba(33, 150, 243, 0.3);
            }
            QLabel#symbolLabel {
                font-size: 16px;
                font-weight: bold;
                color: #333333;
            }
            QLabel#balanceLabel {
                font-size: 14px;
                color: #666666;
            }
            QLabel#usdValueLabel {
                font-size: 14px;
                font-weight: 500;
                color: #2196F3;
            }
            QLabel#priceLabel {
                font-size: 12px;
                color: #999999;
            }
        """)
    
    def update_data(self, balance_data: Dict[str, Any]):
        """Aktualizuj dane karty"""
        self.balance_data = balance_data
        
        balance = balance_data.get('balance', 0.0)
        self.balance_label.setText(f"{balance:.8f}")
        
        usd_value = balance_data.get('usd_value', 0.0)
        self.usd_value_label.setText(f"${usd_value:.2f}")
        
        price = balance_data.get('price', 0.0)
        self.price_label.setText(f"${price:.4f}")

class TransactionHistoryWidget(QWidget):
    """Widget historii transakcji"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setup_ui()
    
    def setup_ui(self):
        """Konfiguracja UI historii transakcji"""
        layout = QVBoxLayout(self)
        
        # Header
        header_layout = QHBoxLayout()
        
        title = QLabel("Historia Transakcji")
        title.setObjectName("sectionTitle")
        header_layout.addWidget(title)
        
        header_layout.addStretch()
        
        # Filtry
        filter_combo = QComboBox()
        filter_combo.addItems(["Wszystkie", "Kupno", "Sprzedaż", "Ostatnie 24h", "Ostatni tydzień"])
        header_layout.addWidget(filter_combo)
        
        layout.addLayout(header_layout)
        
        # Tabela transakcji
        self.transactions_table = QTableWidget()
        self.transactions_table.setColumnCount(6)
        self.transactions_table.setHorizontalHeaderLabels([
            "Data", "Para", "Typ", "Ilość", "Cena", "Wartość"
        ])
        
        # Konfiguracja tabeli
        header = self.transactions_table.horizontalHeader()
        header.setStretchLastSection(True)
        
        self.transactions_table.setAlternatingRowColors(True)
        self.transactions_table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        
        layout.addWidget(self.transactions_table)
    
    def update_transactions(self, transactions: List[Dict[str, Any]]):
        """Aktualizuj listę transakcji"""
        try:
            self.transactions_table.setRowCount(len(transactions))
            
            for row, transaction in enumerate(transactions):
                # Data
                timestamp = transaction.get('timestamp', datetime.now())
                if isinstance(timestamp, str):
                    timestamp = datetime.fromisoformat(timestamp)
                
                self.transactions_table.setItem(row, 0, QTableWidgetItem(
                    timestamp.strftime('%Y-%m-%d %H:%M:%S')
                ))
                
                # Para
                self.transactions_table.setItem(row, 1, QTableWidgetItem(
                    transaction.get('symbol', 'N/A')
                ))
                
                # Typ
                side = transaction.get('side', 'unknown')
                self.transactions_table.setItem(row, 2, QTableWidgetItem(side.upper()))
                
                # Ilość
                quantity = transaction.get('quantity', 0.0)
                self.transactions_table.setItem(row, 3, QTableWidgetItem(f"{quantity:.8f}"))
                
                # Cena
                price = transaction.get('price', 0.0)
                self.transactions_table.setItem(row, 4, QTableWidgetItem(f"${price:.4f}"))
                
                # Wartość
                value = quantity * price
                self.transactions_table.setItem(row, 5, QTableWidgetItem(f"${value:.2f}"))
                
        except Exception as e:
            print(f"Error updating transactions: {e}")

class PortfolioStatsWidget(QWidget):
    """Widget statystyk portfela"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setup_ui()
    
    def setup_ui(self):
        """Konfiguracja UI statystyk"""
        layout = QVBoxLayout(self)
        
        # Placeholder
        placeholder = QLabel("Statystyki portfela będą tutaj")
        placeholder.setAlignment(Qt.AlignmentFlag.AlignCenter)
        placeholder.setObjectName("placeholderText")
        layout.addWidget(placeholder)

class UpdatedPortfolioWidget(QWidget):
    """
    Zaktualizowany widget portfela z integracją IntegratedDataManager
    """
    
    def __init__(self, integrated_data_manager, parent=None):
        if not PYQT_AVAILABLE:
            print("PyQt6 not available, UpdatedPortfolioWidget will not function properly")
            return
            
        super().__init__(parent)
        
        self.integrated_data_manager = integrated_data_manager
        self.config_manager = get_config_manager()
        self.logger = get_logger("updated_portfolio", LogType.USER)
        
        # Dane portfela
        self.portfolio_data = {}
        self.balances = {}
        self.transactions = []
        self.balance_cards = {}
        
        # Timer odświeżania
        self.refresh_timer = QTimer()
        self.refresh_timer.timeout.connect(self.refresh_data)
        
        self.setup_ui()
        self.setup_data_callbacks()
        self.apply_theme()
        self.start_refresh_timer()
        
        self.logger.info("Updated portfolio widget initialized")
    
    def setup_ui(self):
        """Konfiguracja interfejsu"""
        layout = QVBoxLayout(self)
        layout.setSpacing(20)
        layout.setContentsMargins(20, 20, 20, 20)
        
        # Header
        header_layout = QHBoxLayout()
        
        title = QLabel("Portfel")
        title.setObjectName("pageTitle")
        header_layout.addWidget(title)
        
        header_layout.addStretch()
        
        # Przyciski akcji
        refresh_btn = QPushButton("🔄 Odśwież")
        refresh_btn.setObjectName("actionButton")
        refresh_btn.clicked.connect(self.refresh_data)
        header_layout.addWidget(refresh_btn)
        
        export_btn = QPushButton("📊 Eksportuj")
        export_btn.setObjectName("actionButton")
        export_btn.clicked.connect(self.export_portfolio)
        header_layout.addWidget(export_btn)
        
        layout.addLayout(header_layout)
        
        # Podsumowanie portfela
        self.portfolio_summary_card = PortfolioSummaryCard()
        layout.addWidget(self.portfolio_summary_card)
        
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
    
    def setup_balances_tab(self):
        """Konfiguracja zakładki sald"""
        self.balances_widget = QWidget()
        layout = QVBoxLayout(self.balances_widget)
        
        # Header sald
        balances_header = QLabel("Salda Kryptowalut")
        balances_header.setObjectName("sectionTitle")
        layout.addWidget(balances_header)
        
        # Scroll area dla kart sald
        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        
        # Widget zawierający karty
        self.balances_container = QWidget()
        
        if FLOW_LAYOUT_AVAILABLE:
            self.balances_layout = FlowLayout(self.balances_container)
        else:
            self.balances_layout = QGridLayout(self.balances_container)
        
        scroll_area.setWidget(self.balances_container)
        layout.addWidget(scroll_area)
    
    def setup_data_callbacks(self):
        """Konfiguracja callbacków dla aktualizacji danych"""
        # Subskrypcje na aktualizacje danych portfela
        self.integrated_data_manager.subscribe_to_ui_updates(
            'portfolio_update', self.on_portfolio_update
        )
        self.integrated_data_manager.subscribe_to_ui_updates(
            'balance_update', self.on_balance_update
        )
        self.integrated_data_manager.subscribe_to_ui_updates(
            'transaction_update', self.on_transaction_update
        )
    
    def on_portfolio_update(self, portfolio_data):
        """Callback dla aktualizacji danych portfela"""
        try:
            def _apply():
                try:
                    self.portfolio_data = portfolio_data
                    self.portfolio_summary_card.update_data(portfolio_data)
                    self.logger.info("Portfolio data updated from IntegratedDataManager")
                except Exception as exc:
                    self.logger.error(f"Error applying portfolio data: {exc}")

            # Zapewnij wykonanie w głównym wątku UI
            if PYQT_AVAILABLE and QThread.currentThread() != self.thread():
                QTimer.singleShot(0, _apply)
            else:
                _apply()
        except Exception as e:
            self.logger.error(f"Error updating portfolio data: {e}")
    
    def on_balance_update(self, balance_data):
        """Callback dla aktualizacji sald"""
        try:
            def _apply():
                try:
                    self.balances = balance_data
                    self.update_balance_cards()
                    self.logger.info("Balance data updated from IntegratedDataManager")
                except Exception as exc:
                    self.logger.error(f"Error applying balance data: {exc}")

            # Zapewnij wykonanie w głównym wątku UI
            if PYQT_AVAILABLE and QThread.currentThread() != self.thread():
                QTimer.singleShot(0, _apply)
            else:
                _apply()
        except Exception as e:
            self.logger.error(f"Error updating balance data: {e}")
    
    def on_transaction_update(self, transaction_data):
        """Callback dla aktualizacji transakcji"""
        try:
            def _normalize(tx: Dict[str, Any]) -> Dict[str, Any]:
                # Map fields from various possible sources to the expected structure
                ts = tx.get('timestamp')
                if not ts:
                    time_str = tx.get('time')
                    if isinstance(time_str, str):
                        try:
                            today = datetime.now().date()
                            h, m, s = [int(part) for part in time_str.split(':')]
                            ts = datetime(today.year, today.month, today.day, h, m, s)
                        except Exception:
                            ts = datetime.now()
                    else:
                        ts = datetime.now()
                elif isinstance(ts, str):
                    try:
                        ts = datetime.fromisoformat(ts)
                    except Exception:
                        ts = datetime.now()
                symbol = tx.get('symbol') or tx.get('pair') or 'N/A'
                side = tx.get('side', 'unknown')
                quantity = tx.get('quantity', tx.get('amount', 0.0)) or 0.0
                price = tx.get('price', 0.0) or 0.0
                return {
                    'timestamp': ts,
                    'symbol': symbol,
                    'side': side,
                    'quantity': float(quantity) if isinstance(quantity, (int, float)) else 0.0,
                    'price': float(price) if isinstance(price, (int, float)) else 0.0,
                }

            def _apply():
                try:
                    if isinstance(transaction_data, list):
                        self.transactions = [_normalize(tx) for tx in transaction_data]
                    else:
                        normalized = _normalize(transaction_data)
                        self.transactions.insert(0, normalized)
                        self.transactions = self.transactions[:100]
                    self.transaction_history.update_transactions(self.transactions)
                    self.logger.info("Transaction data updated from IntegratedDataManager")
                except Exception as exc:
                    self.logger.error(f"Error applying transaction data: {exc}")

            # Zapewnij wykonanie w głównym wątku UI
            if PYQT_AVAILABLE and QThread.currentThread() != self.thread():
                QTimer.singleShot(0, _apply)
            else:
                _apply()
        except Exception as e:
            self.logger.error(f"Error updating transaction data: {e}")
    
    def update_balance_cards(self):
        """Aktualizuj karty sald"""
        try:
            # Usuń stare karty
            for card in self.balance_cards.values():
                card.setParent(None)
            self.balance_cards.clear()
            
            # Dodaj nowe karty
            for symbol, balance_data in self.balances.items():
                if balance_data.get('balance', 0) > 0:  # Pokaż tylko niezerowe salda
                    card = BalanceCard(symbol, balance_data)
                    self.balance_cards[symbol] = card
                    
                    if FLOW_LAYOUT_AVAILABLE:
                        self.balances_layout.addWidget(card)
                    else:
                        row = len(self.balance_cards) // 4
                        col = len(self.balance_cards) % 4
                        self.balances_layout.addWidget(card, row, col)
            
            # Jeśli brak sald, pokaż placeholder
            if not self.balance_cards:
                placeholder = QLabel("Brak sald do wyświetlenia")
                placeholder.setAlignment(Qt.AlignmentFlag.AlignCenter)
                placeholder.setObjectName("placeholderText")
                self.balances_layout.addWidget(placeholder)
                
        except Exception as e:
            self.logger.error(f"Error updating balance cards: {e}")
    
    def refresh_data(self):
        """Odśwież dane portfela"""
        try:
            if not self.integrated_data_manager.initialized:
                self.logger.warning("IntegratedDataManager not initialized")
                return
            
            # Uruchom asynchroniczne odświeżanie danych, uwzględniając brak działającej pętli
            import asyncio, threading
            try:
                loop = asyncio.get_running_loop()
                loop.create_task(self._async_refresh_data())
            except RuntimeError:
                threading.Thread(target=self._run_async_refresh_in_thread, daemon=True).start()
            
        except Exception as e:
            self.logger.error(f"Error refreshing portfolio data: {e}")
    
    def _run_async_refresh_in_thread(self):
        """Uruchomienie _async_refresh_data w nowej pętli event loop (w osobnym wątku)"""
        try:
            import asyncio
            asyncio.run(self._async_refresh_data())
        except Exception as e:
            self.logger.error(f"Error running async refresh in thread: {e}")
    
    async def _async_refresh_data(self):
        """Asynchroniczne odświeżanie danych portfela"""
        try:
            # Pobierz dane portfela
            portfolio_data = await self.integrated_data_manager.get_portfolio_data()
            if portfolio_data:
                self.on_portfolio_update(portfolio_data)
            
            # Pobierz salda
            balance_data = await self.integrated_data_manager.get_balance_data()
            if balance_data:
                self.on_balance_update(balance_data)
            
            # Pobierz historię transakcji (użyj get_recent_trades zamiast nieistniejącego get_transaction_history)
            recent_trades = await self.integrated_data_manager.get_recent_trades(limit=50)
            if recent_trades:
                self.on_transaction_update(recent_trades)
            
        except Exception as e:
            self.logger.error(f"Error in async portfolio refresh: {e}")
    
    def export_portfolio(self):
        """Eksportuj dane portfela"""
        try:
            # Placeholder dla funkcji eksportu
            QMessageBox.information(
                self,
                "Eksport",
                "Funkcja eksportu zostanie wkrótce dodana"
            )
            
        except Exception as e:
            self.logger.error(f"Error exporting portfolio: {e}")
    
    def apply_theme(self):
        """Zastosuj motyw"""
        # Ciemny, spójny motyw zgodny z globalnymi stylami
        self.setStyleSheet("""
            QWidget {
                background-color: #1a1a1a;
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
                color: #e0e0e0;
                margin: 10px 0;
            }
            QPushButton#actionButton {
                background-color: #667eea;
                color: white;
                border: none;
                border-radius: 8px;
                padding: 8px 16px;
                font-weight: 600;
            }
            QPushButton#actionButton:hover {
                background-color: #576bd6;
            }
            QPushButton#actionButton:pressed {
                background-color: #4a5bc0;
            }
            QLabel#placeholderText {
                color: #9aa0a6;
                font-size: 16px;
                padding: 40px;
            }
            QTabWidget::pane {
                border: 1px solid #3a3a3a;
                border-radius: 10px;
                background-color: #181818;
            }
            QTabBar::tab {
                background-color: #2b2b2b;
                color: #e6e6e6;
                padding: 10px 18px;
                margin-right: 3px;
                border-top-left-radius: 10px;
                border-top-right-radius: 10px;
                font-weight: 600;
            }
            QTabBar::tab:selected {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                    stop:0 #667eea, stop:1 #764ba2);
                color: #ffffff;
                border-bottom: 2px solid #667eea;
            }
        """)
    
    def start_refresh_timer(self):
        """Uruchom timer odświeżania"""
        try:
            # Odśwież dane natychmiast
            self.refresh_data()
            
            # Ustaw timer na odświeżanie co 30 sekund
            refresh_interval = get_app_setting('portfolio_refresh_interval', 30000)  # ms
            self.refresh_timer.start(refresh_interval)
            
            self.logger.info("Portfolio refresh timer started")
            
        except Exception as e:
            self.logger.error(f"Error starting refresh timer: {e}")
    
    def closeEvent(self, event):
        """Obsługa zamknięcia widgetu"""
        try:
            # Zatrzymaj timer
            if self.refresh_timer.isActive():
                self.refresh_timer.stop()
            
            self.logger.info("Portfolio widget closed")
            event.accept()
            
        except Exception as e:
            self.logger.error(f"Error closing portfolio widget: {e}")
            event.accept()
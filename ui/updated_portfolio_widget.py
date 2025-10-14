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

try:
    from ui.styles import COLORS
except ImportError:
    COLORS = {
        'success': '#4CAF50',
        'danger': '#F44336'
    }

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
        self.setObjectName("portfolioSummaryCard")
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
            QWidget#portfolioSummaryCard {
                background: #ffffff;
                border: 1px solid rgba(29, 53, 87, 0.08);
                border-radius: 18px;
                margin: 4px 0;
                padding: 4px;
                box-shadow: 0 12px 32px rgba(15, 23, 42, 0.06);
            }
            QLabel#summaryTitle {
                font-size: 18px;
                font-weight: 600;
                color: #1f2a44;
            }
            QLabel#totalValue {
                font-size: 28px;
                font-weight: 700;
                color: #0f172a;
            }
            QLabel#change24h, QLabel#dailyPnL {
                font-size: 15px;
                font-weight: 600;
                color: #64748b;
            }
            QLabel#assetsCount {
                font-size: 13px;
                color: #5f6c7b;
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
            change_color = COLORS.get('success', '#4CAF50') if change_24h >= 0 else COLORS.get('danger', '#F44336')
            change_sign = "+" if change_24h >= 0 else ""
            
            self.change_24h_label.setText(f"{change_sign}${change_24h:.2f} ({change_sign}{change_24h_percent:.2f}%)")
            self.change_24h_label.setStyleSheet(f"color: {change_color};")
            
            # Dzienny P&L
            daily_pnl = portfolio_data.get('daily_pnl', 0.0)
            pnl_color = COLORS.get('success', '#4CAF50') if daily_pnl >= 0 else COLORS.get('danger', '#F44336')
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
        self.setObjectName("balanceCard")
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
            QWidget#balanceCard {
                background: #ffffff;
                border: 1px solid rgba(29, 53, 87, 0.08);
                border-radius: 16px;
                margin: 4px 0;
                padding: 4px;
                box-shadow: 0 8px 24px rgba(15, 23, 42, 0.06);
            }
            QLabel#symbolLabel {
                font-size: 16px;
                font-weight: 600;
                color: #1f2a44;
            }
            QLabel#balanceLabel {
                font-size: 15px;
                color: #0f172a;
                font-weight: 600;
            }
            QLabel#usdValueLabel {
                font-size: 14px;
                font-weight: 600;
                color: #2563eb;
            }
            QLabel#priceLabel {
                font-size: 12px;
                color: #5f6c7b;
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

        frame = QFrame()
        frame.setObjectName("sectionCard")
        frame_layout = QVBoxLayout(frame)
        frame_layout.setContentsMargins(24, 24, 24, 24)
        frame_layout.setSpacing(18)

        header_layout = QHBoxLayout()

        title = QLabel("Historia transakcji")
        title.setObjectName("sectionTitle")
        header_layout.addWidget(title)

        header_layout.addStretch()

        filter_combo = QComboBox()
        filter_combo.addItems(["Wszystkie", "Kupno", "Sprzedaż", "Ostatnie 24h", "Ostatni tydzień"])
        header_layout.addWidget(filter_combo)

        frame_layout.addLayout(header_layout)

        description = QLabel("Rejestrowane zdarzenia handlowe synchronizowane są z modułem transakcyjnym. Wybierz filtr, aby zawęzić listę.")
        description.setObjectName("cardSubtitle")
        description.setWordWrap(True)
        frame_layout.addWidget(description)

        self.transactions_table = QTableWidget()
        self.transactions_table.setColumnCount(6)
        self.transactions_table.setHorizontalHeaderLabels([
            "Data", "Para", "Typ", "Ilość", "Cena", "Wartość"
        ])

        header = self.transactions_table.horizontalHeader()
        header.setStretchLastSection(True)

        self.transactions_table.setAlternatingRowColors(True)
        self.transactions_table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.transactions_table.setSelectionMode(QTableWidget.SelectionMode.NoSelection)

        frame_layout.addWidget(self.transactions_table)
        layout.addWidget(frame)
    
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

        frame = QFrame()
        frame.setObjectName("sectionCard")
        frame_layout = QVBoxLayout(frame)
        frame_layout.setContentsMargins(24, 24, 24, 24)
        frame_layout.setSpacing(12)

        title = QLabel("Zaawansowane statystyki")
        title.setObjectName("sectionTitle")
        frame_layout.addWidget(title)

        placeholder = QLabel("Statystyki portfela będą tutaj")
        placeholder.setAlignment(Qt.AlignmentFlag.AlignCenter)
        placeholder.setObjectName("placeholderText")
        placeholder.setStyleSheet("color: #5f6c7b; font-style: italic;")
        frame_layout.addWidget(placeholder)

        layout.addWidget(frame)

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
        layout.setSpacing(18)
        layout.setContentsMargins(24, 24, 24, 24)

        header_frame = QFrame()
        header_frame.setObjectName("sectionCard")
        header_layout = QHBoxLayout(header_frame)
        header_layout.setContentsMargins(24, 24, 24, 24)
        header_layout.setSpacing(16)

        header_texts = QVBoxLayout()
        title = QLabel("Stan portfela")
        title.setObjectName("pageTitle")
        title.setFont(QFont("Segoe UI", 20, QFont.Weight.Bold))
        title.setStyleSheet("color: #1f2a44;")
        header_texts.addWidget(title)

        subtitle = QLabel("Kontroluj wyceny aktywów, historię transakcji oraz agregowane statystyki w jednym miejscu.")
        subtitle.setObjectName("cardSubtitle")
        subtitle.setWordWrap(True)
        header_texts.addWidget(subtitle)
        header_texts.addStretch()
        header_layout.addLayout(header_texts, stretch=3)

        actions_layout = QVBoxLayout()
        actions_layout.setSpacing(10)

        refresh_btn = QPushButton("🔄 Odśwież")
        refresh_btn.setObjectName("inlineAction")
        refresh_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        refresh_btn.clicked.connect(self.refresh_data)
        actions_layout.addWidget(refresh_btn)

        export_btn = QPushButton("📊 Eksportuj")
        export_btn.setObjectName("inlineAction")
        export_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        export_btn.clicked.connect(self.export_portfolio)
        actions_layout.addWidget(export_btn)
        actions_layout.addStretch()

        header_layout.addLayout(actions_layout, stretch=1)

        layout.addWidget(header_frame)

        content_scroll = QScrollArea()
        content_scroll.setWidgetResizable(True)
        content_scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        try:
            content_scroll.setFrameShape(QFrame.Shape.NoFrame)
        except Exception:
            pass

        content_widget = QWidget()
        content_layout = QVBoxLayout(content_widget)
        content_layout.setSpacing(24)
        content_layout.setContentsMargins(4, 4, 4, 24)

        # Podsumowanie portfela
        self.portfolio_summary_card = PortfolioSummaryCard()
        content_layout.addWidget(self.portfolio_summary_card)

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

        content_layout.addWidget(self.tabs)
        content_layout.addStretch()
        content_scroll.setWidget(content_widget)
        layout.addWidget(content_scroll)
    
    def setup_balances_tab(self):
        """Konfiguracja zakładki sald"""
        self.balances_widget = QWidget()
        layout = QVBoxLayout(self.balances_widget)

        balances_frame = QFrame()
        balances_frame.setObjectName("sectionCard")
        balances_layout = QVBoxLayout(balances_frame)
        balances_layout.setContentsMargins(24, 24, 24, 24)
        balances_layout.setSpacing(18)

        balances_header = QLabel("Salda kryptowalut")
        balances_header.setObjectName("sectionTitle")
        balances_layout.addWidget(balances_header)

        balances_description = QLabel("Poniższe karty pobierane są z aktualnego stanu konta. Dane są synchronizowane z IntegratedDataManager.")
        balances_description.setObjectName("cardSubtitle")
        balances_description.setWordWrap(True)
        balances_layout.addWidget(balances_description)

        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)

        self.balances_container = QWidget()

        if FLOW_LAYOUT_AVAILABLE:
            self.balances_layout = FlowLayout(self.balances_container)
        else:
            self.balances_layout = QGridLayout(self.balances_container)

        scroll_area.setWidget(self.balances_container)
        balances_layout.addWidget(scroll_area)

        layout.addWidget(balances_frame)
    
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
            self.portfolio_data = portfolio_data
            self.portfolio_summary_card.update_data(portfolio_data)
            
            self.logger.info("Portfolio data updated from IntegratedDataManager")
            
        except Exception as e:
            self.logger.error(f"Error updating portfolio data: {e}")
    
    def on_balance_update(self, balance_data):
        """Callback dla aktualizacji sald"""
        try:
            self.balances = balance_data
            self.update_balance_cards()
            
            self.logger.info("Balance data updated from IntegratedDataManager")
            
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
                        # Combine today's date with provided time string
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

            if isinstance(transaction_data, list):
                # Normalize list of transactions
                self.transactions = [_normalize(tx) for tx in transaction_data]
            else:
                # Normalize single transaction and prepend
                normalized = _normalize(transaction_data)
                self.transactions.insert(0, normalized)
                # Ogranicz do 100 ostatnich transakcji
                self.transactions = self.transactions[:100]
            
            self.transaction_history.update_transactions(self.transactions)
            
            self.logger.info("Transaction data updated from IntegratedDataManager")
            
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
        try:
            from ui.styles import get_theme_style
            self.setStyleSheet(get_theme_style(dark_mode=False))
        except Exception:
            self.setStyleSheet("""
                QWidget {
                    background-color: #f4f6fb;
                }
                QLabel#pageTitle {
                    font-size: 24px;
                    font-weight: bold;
                    color: #1f2a44;
                    margin-bottom: 10px;
                }
                QLabel#sectionTitle {
                    font-size: 18px;
                    font-weight: 600;
                    color: #1f2a44;
                    margin: 10px 0;
                }
                QPushButton#inlineAction, QPushButton#actionButton {
                    background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                        stop:0 #667eea, stop:1 #764ba2);
                    color: white;
                    border: none;
                    border-radius: 10px;
                    padding: 10px 20px;
                    font-weight: 600;
                }
                QLabel#placeholderText {
                    color: #5f6c7b;
                    font-size: 16px;
                    padding: 40px;
                }
                QTabWidget::pane {
                    border: 1px solid rgba(15, 23, 42, 0.08);
                    border-radius: 12px;
                    background-color: white;
                }
                QTabBar::tab {
                    background-color: #e9ecfb;
                    padding: 10px 18px;
                    margin-right: 2px;
                    border-top-left-radius: 10px;
                    border-top-right-radius: 10px;
                    color: #465165;
                }
                QTabBar::tab:selected {
                    background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                        stop:0 #667eea, stop:1 #764ba2);
                    color: white;
                    font-weight: 600;
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
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

try:
    from PyQt6.QtWidgets import (
        QWidget, QVBoxLayout, QHBoxLayout, QGridLayout, QFormLayout,
        QLabel, QPushButton, QFrame, QScrollArea, QTabWidget,
        QTableWidget, QTableWidgetItem, QHeaderView, QComboBox,
        QLineEdit, QSpinBox, QDoubleSpinBox, QCheckBox, QGroupBox,
        QTextEdit, QProgressBar, QSplitter, QTreeWidget, QTreeWidgetItem,
        QMessageBox, QMenu, QFileDialog, QDateEdit, QApplication,
        QDialog, QDialogButtonBox
    )
    from PyQt6.QtCore import (
        Qt, QTimer, pyqtSignal, QSize, QDate, QPropertyAnimation,
        QEasingCurve, QParallelAnimationGroup, QThread, pyqtSlot
    )
    from PyQt6.QtGui import (
        QFont, QPixmap, QIcon, QPalette, QColor, QPainter,
        QPen, QBrush, QLinearGradient, QAction, QContextMenuEvent
    )
    PYQT_AVAILABLE = True
except ImportError as e:
    print(f"PyQt6 import error in updated_bot_management_widget.py: {e}")
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
    
    def setup_ui(self):
        """Konfiguracja UI karty bota"""
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
        self.strategy_value = QLabel(self.bot_data.get('strategy', 'N/A'))
        self.strategy_value.setObjectName("infoValue")
        info_layout.addWidget(strategy_label, 0, 0)
        info_layout.addWidget(self.strategy_value, 0, 1)
        
        # Para handlowa
        symbol_label = QLabel("Para:")
        symbol_label.setObjectName("infoLabel")
        self.symbol_value = QLabel(self.bot_data.get('symbol', 'N/A'))
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
        self.setStyleSheet("""
            QWidget {
                background-color: #ffffff;
                border: 1px solid #e0e0e0;
                border-radius: 12px;
                margin: 5px;
            }
            QWidget:hover {
                border-color: #2196F3;
                box-shadow: 0 4px 12px rgba(33, 150, 243, 0.2);
            }
            QLabel#botName {
                font-size: 16px;
                font-weight: bold;
                color: #333333;
            }
            QLabel#statusIndicator {
                font-size: 20px;
                margin-left: 5px;
            }
            QLabel#infoLabel {
                font-size: 12px;
                color: #666666;
                font-weight: 500;
            }
            QLabel#infoValue {
                font-size: 12px;
                color: #333333;
            }
            QLabel#pnlValue {
                font-size: 12px;
                font-weight: 600;
            }
            QPushButton#actionButton {
                background-color: #2196F3;
                color: white;
                border: none;
                border-radius: 6px;
                padding: 6px 12px;
                font-weight: 500;
                min-width: 60px;
            }
            QPushButton#actionButton:hover {
                background-color: #1976D2;
            }
            QPushButton#actionButton:pressed {
                background-color: #1565C0;
            }
            QPushButton#iconButton {
                background-color: #f5f5f5;
                border: 1px solid #ddd;
                border-radius: 4px;
                padding: 4px;
                min-width: 30px;
                max-width: 30px;
                min-height: 30px;
                max-height: 30px;
            }
            QPushButton#iconButton:hover {
                background-color: #e0e0e0;
            }
        """)
    
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
            self.start_stop_btn.setStyleSheet("""
                QPushButton#actionButton {
                    background-color: #F44336;
                }
                QPushButton#actionButton:hover {
                    background-color: #D32F2F;
                }
            """)
        elif status == 'error':
            self.status_indicator.setStyleSheet("color: #FF9800;")
            self.start_stop_btn.setText("▶️ Start")
            self.start_stop_btn.setStyleSheet("""
                QPushButton#actionButton {
                    background-color: #4CAF50;
                }
                QPushButton#actionButton:hover {
                    background-color: #388E3C;
                }
            """)
        else:  # stopped
            self.status_indicator.setStyleSheet("color: #9E9E9E;")
            self.start_stop_btn.setText("▶️ Start")
            self.start_stop_btn.setStyleSheet("""
                QPushButton#actionButton {
                    background-color: #4CAF50;
                }
                QPushButton#actionButton:hover {
                    background-color: #388E3C;
                }
            """)
        
        # Strategia
        self.strategy_value.setText(bot_data.get('strategy', 'N/A'))
        
        # Para
        self.symbol_value.setText(bot_data.get('symbol', 'N/A'))
        
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
        self.setup_ui()
    
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
        
        self.symbol_edit = QLineEdit(self.bot_data.get('symbol', 'BTC/USDT'))
        self.symbol_edit.setPlaceholderText("Para handlowa")
        basic_layout.addRow("Para:", self.symbol_edit)
        
        form_layout.addRow(basic_group)
        
        # Strategia
        strategy_group = QGroupBox("Strategia")
        strategy_layout = QFormLayout(strategy_group)
        
        self.strategy_combo = QComboBox()
        self.strategy_combo.addItems(["DCA", "Grid Trading", "Scalping", "Custom"])
        self.strategy_combo.setCurrentText(self.bot_data.get('strategy', 'DCA'))
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
        return {
            'name': self.name_edit.text(),
            'exchange': self.exchange_combo.currentText(),
            'symbol': self.symbol_edit.text(),
            'strategy': self.strategy_combo.currentText(),
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
        layout = QVBoxLayout(self)
        layout.setSpacing(20)
        layout.setContentsMargins(20, 20, 20, 20)
        
        # Header
        header_layout = QHBoxLayout()
        
        title = QLabel("Zarządzanie Botami")
        title.setObjectName("pageTitle")
        header_layout.addWidget(title)
        
        header_layout.addStretch()
        
        # Przyciski akcji
        add_bot_btn = QPushButton("➕ Dodaj Bota")
        add_bot_btn.setObjectName("actionButton")
        add_bot_btn.clicked.connect(self.add_new_bot)
        header_layout.addWidget(add_bot_btn)
        
        start_all_btn = QPushButton("▶️ Start Wszystkie")
        start_all_btn.setObjectName("actionButton")
        start_all_btn.clicked.connect(self.start_all_bots)
        header_layout.addWidget(start_all_btn)
        
        stop_all_btn = QPushButton("⏸️ Stop Wszystkie")
        stop_all_btn.setObjectName("actionButton")
        stop_all_btn.clicked.connect(self.stop_all_bots)
        header_layout.addWidget(stop_all_btn)
        
        layout.addLayout(header_layout)
        
        # Statystyki
        self.setup_stats_section(layout)
        
        # Boty
        self.setup_bots_section(layout)
    
    def setup_stats_section(self, parent_layout):
        """Konfiguracja sekcji statystyk"""
        stats_frame = QFrame()
        stats_frame.setObjectName("statsFrame")
        stats_layout = QHBoxLayout(stats_frame)
        stats_layout.setSpacing(20)
        
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
    
    def create_stat_card(self, title: str, value: str, color: str) -> QWidget:
        """Utwórz kartę statystyki"""
        card = QWidget()
        card.setObjectName("statCard")
        layout = QVBoxLayout(card)
        layout.setSpacing(5)
        layout.setContentsMargins(15, 15, 15, 15)
        
        title_label = QLabel(title)
        title_label.setObjectName("statTitle")
        layout.addWidget(title_label)
        
        value_label = QLabel(value)
        value_label.setObjectName("statValue")
        value_label.setStyleSheet(f"color: {color}; font-size: 24px; font-weight: bold;")
        layout.addWidget(value_label)
        
        return card
    
    def setup_bots_section(self, parent_layout):
        """Konfiguracja sekcji botów"""
        # Header sekcji
        bots_header = QLabel("Lista Botów")
        bots_header.setObjectName("sectionTitle")
        parent_layout.addWidget(bots_header)
        
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
        parent_layout.addWidget(scroll_area)
    
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
            if not self.integrated_data_manager.initialized:
                self.logger.warning("IntegratedDataManager not initialized")
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
    
    def apply_theme(self):
        """Zastosuj motyw"""
        self.setStyleSheet("""
            QWidget {
                background-color: #f5f5f5;
            }
            QLabel#pageTitle {
                font-size: 24px;
                font-weight: bold;
                color: #333333;
                margin-bottom: 10px;
            }
            QLabel#sectionTitle {
                font-size: 18px;
                font-weight: 600;
                color: #444444;
                margin: 10px 0;
            }
            QPushButton#actionButton {
                background-color: #2196F3;
                color: white;
                border: none;
                border-radius: 6px;
                padding: 8px 16px;
                font-weight: 500;
                margin: 2px;
            }
            QPushButton#actionButton:hover {
                background-color: #1976D2;
            }
            QPushButton#actionButton:pressed {
                background-color: #1565C0;
            }
            QFrame#statsFrame {
                background-color: white;
                border: 1px solid #e0e0e0;
                border-radius: 8px;
                padding: 10px;
            }
            QWidget#statCard {
                background-color: #f8f9fa;
                border: 1px solid #dee2e6;
                border-radius: 6px;
                margin: 5px;
            }
            QLabel#statTitle {
                font-size: 12px;
                color: #666666;
                font-weight: 500;
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
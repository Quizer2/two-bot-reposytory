"""
Interfejs zarządzania botami handlowymi

Zawiera GUI do konfiguracji, uruchamiania i monitorowania
botów handlowych na różnych giełdach.
"""

import asyncio
import sys
from datetime import datetime
from typing import Dict, List, Optional, Any
import json

try:
    from PyQt6.QtWidgets import (
        QWidget, QVBoxLayout, QHBoxLayout, QGridLayout,
        QLabel, QPushButton, QFrame, QComboBox, QLineEdit,
        QSpinBox, QDoubleSpinBox, QCheckBox, QGroupBox,
        QTableWidget, QTableWidgetItem, QHeaderView,
        QTabWidget, QTextEdit, QProgressBar, QMessageBox,
        QDialog, QFormLayout, QDialogButtonBox, QSplitter,
        QScrollArea
    )
    from PyQt6.QtCore import Qt, QTimer, pyqtSignal, QThread, pyqtSlot
    from PyQt6.QtGui import QFont, QColor, QPalette
    from .flow_layout import FlowLayout
    PYQT_AVAILABLE = True
except ImportError:
    PYQT_AVAILABLE = False
    print("PyQt6 not available for bot management")

# Import bot engines
try:
    from trading.bot_engines import (
        BotManager, TradingBot, ExchangeConnector,
        MovingAverageCrossStrategy, RSIStrategy,
        OrderSide, OrderStatus, OrderType
    )
    BOT_ENGINES_AVAILABLE = True
except ImportError:
    BOT_ENGINES_AVAILABLE = False
    print("Bot engines not available")

# Import nowej klasy BotCard
try:
    from ui.bot_card import BotCard
    BOT_CARD_AVAILABLE = True
except ImportError:
    BOT_CARD_AVAILABLE = False
    print("BotCard not available - using fallback")

# Import async helper
try:
    from ui.async_helper import get_bot_async_manager, BotAsyncManager
    ASYNC_HELPER_AVAILABLE = True
except ImportError:
    ASYNC_HELPER_AVAILABLE = False
    print("Async helper not available")

# Import logger
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from utils.logger import get_logger, LogType
from utils.config_manager import get_config_manager


class BotConfigDialog(QDialog):
    """Dialog konfiguracji nowego bota"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Konfiguracja Nowego Bota")
        self.setModal(True)
        self.resize(700, 900)
        
        # Ustaw style dla całego dialogu
        self.setStyleSheet("""
            QDialog {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:1,
                    stop:0 rgba(42, 42, 42, 0.95), stop:1 rgba(60, 60, 60, 0.95));
                color: #ffffff;
                border: 1px solid rgba(102, 126, 234, 0.3);
                border-radius: 12px;
            }
            QLabel {
                color: #ffffff;
                font-weight: 500;
                font-size: 14px;
                padding: 4px 0px;
            }
            QLineEdit, QComboBox, QSpinBox, QDoubleSpinBox {
                background: rgba(255, 255, 255, 0.1);
                border: 1px solid rgba(102, 126, 234, 0.3);
                border-radius: 6px;
                padding: 8px 12px;
                color: #ffffff;
                font-size: 14px;
                min-height: 20px;
            }
            QLineEdit:focus, QComboBox:focus, QSpinBox:focus, QDoubleSpinBox:focus {
                border: 1px solid rgba(102, 126, 234, 0.7);
                background: rgba(255, 255, 255, 0.15);
                outline: none;
            }
            QLineEdit:hover, QComboBox:hover, QSpinBox:hover, QDoubleSpinBox:hover {
                border: 1px solid rgba(102, 126, 234, 0.5);
            }
            QComboBox::drop-down {
                border: none;
                width: 30px;
            }
            QComboBox::down-arrow {
                image: none;
                border-left: 5px solid transparent;
                border-right: 5px solid transparent;
                border-top: 5px solid #cccccc;
                margin-right: 5px;
            }
            QCheckBox {
                color: #ffffff;
                spacing: 8px;
                font-size: 14px;
            }
            QCheckBox::indicator {
                width: 18px;
                height: 18px;
                border: 2px solid rgba(102, 126, 234, 0.5);
                border-radius: 4px;
                background: rgba(255, 255, 255, 0.1);
            }
            QCheckBox::indicator:checked {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                    stop:0 rgba(102, 126, 234, 0.8), 
                    stop:1 rgba(118, 75, 162, 0.8));
                border: 2px solid rgba(102, 126, 234, 0.8);
            }
        """)
        
        self.setup_ui()
    
    def setup_ui(self):
        """Konfiguracja interfejsu"""
        layout = QVBoxLayout(self)
        layout.setSpacing(15)
        layout.setContentsMargins(20, 20, 20, 20)
        
        # Nagłówek
        header_label = QLabel("Utwórz Nowego Bota Handlowego")
        header_label.setStyleSheet("""
            font-size: 18px;
            font-weight: bold;
            color: #ffffff;
            padding: 12px;
            background: transparent;
            border: none;
        """)
        header_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(header_label)
        
        # Właściwy scroll area dla długich formularzy
        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        scroll_area.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        scroll_area.setStyleSheet("""
            QScrollArea {
                border: none;
                background-color: transparent;
            }
            QScrollBar:vertical {
                background-color: #f0f0f0;
                width: 12px;
                border-radius: 6px;
            }
            QScrollBar::handle:vertical {
                background-color: #3498db;
                border-radius: 6px;
                min-height: 20px;
            }
            QScrollBar::handle:vertical:hover {
                background-color: #2980b9;
            }
        """)
        
        scroll_widget = QWidget()
        scroll_layout = QVBoxLayout(scroll_widget)
        scroll_layout.setSpacing(20)
        scroll_layout.setContentsMargins(10, 10, 10, 10)
        
        # Podstawowa konfiguracja
        basic_group = QGroupBox("Podstawowa Konfiguracja")
        basic_group.setStyleSheet("""
            QGroupBox {
                font-weight: bold;
                font-size: 16px;
                border: 1px solid rgba(102, 126, 234, 0.3);
                border-radius: 10px;
                margin-top: 15px;
                padding-top: 15px;
                background: rgba(255, 255, 255, 0.05);
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 15px;
                padding: 0 10px 0 10px;
                color: #ffffff;
                background: transparent;
            }
        """)
        basic_layout = QFormLayout(basic_group)
        basic_layout.setSpacing(12)
        basic_layout.setLabelAlignment(Qt.AlignmentFlag.AlignRight)
        basic_layout.setContentsMargins(20, 25, 20, 20)
        
        # Nazwa bota
        self.name_edit = QLineEdit()
        self.name_edit.setPlaceholderText("Np. MA_Bot_BTC_001")
        basic_layout.addRow("Nazwa bota:", self.name_edit)
        
        # Giełda
        self.exchange_combo = QComboBox()
        self.exchange_combo.addItems(["binance", "bybit", "okx", "kucoin", "bitget", "kraken", "bitfinex"])
        basic_layout.addRow("Giełda:", self.exchange_combo)
        
        # Para handlowa
        self.symbol_combo = QComboBox()
        self.symbol_combo.addItems(["BTC/USDT", "ETH/USDT", "BNB/USDT", "ADA/USDT", "SOL/USDT"])
        self.symbol_combo.setEditable(True)
        basic_layout.addRow("Para handlowa:", self.symbol_combo)
        
        # Strategia
        self.strategy_combo = QComboBox()
        self.strategy_combo.addItems([
            "AI Trading Bot", 
            "Scalping", 
            "DCA (Dollar Cost Averaging)", 
            "Grid Trading", 
            "Swing Trading",
            "Arbitrage",
            "Custom Strategy",
            "Moving Average Cross", 
            "RSI Strategy", 
            "MACD Strategy"
        ])
        self.strategy_combo.currentTextChanged.connect(self.on_strategy_changed)
        basic_layout.addRow("Strategia:", self.strategy_combo)
        
        scroll_layout.addWidget(basic_group)
        
        # Konfiguracja API
        api_group = QGroupBox("Konfiguracja API Giełdy")
        api_group.setStyleSheet("""
            QGroupBox {
                font-weight: bold;
                font-size: 16px;
                border: 1px solid rgba(102, 126, 234, 0.3);
                border-radius: 10px;
                margin-top: 15px;
                padding-top: 15px;
                background: rgba(255, 255, 255, 0.05);
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 15px;
                padding: 0 10px 0 10px;
                color: #ffffff;
                background: transparent;
            }
        """)
        api_layout = QFormLayout(api_group)
        api_layout.setSpacing(12)
        api_layout.setLabelAlignment(Qt.AlignmentFlag.AlignRight)
        api_layout.setContentsMargins(20, 25, 20, 20)
        
        self.api_key_edit = QLineEdit()
        self.api_key_edit.setEchoMode(QLineEdit.EchoMode.Password)
        self.api_key_edit.setPlaceholderText("Wprowadź klucz API")
        api_layout.addRow("API Key:", self.api_key_edit)
        
        self.secret_edit = QLineEdit()
        self.secret_edit.setEchoMode(QLineEdit.EchoMode.Password)
        self.secret_edit.setPlaceholderText("Wprowadź sekret API")
        api_layout.addRow("Secret:", self.secret_edit)
        
        self.passphrase_edit = QLineEdit()
        self.passphrase_edit.setEchoMode(QLineEdit.EchoMode.Password)
        self.passphrase_edit.setPlaceholderText("Tylko dla KuCoin")
        api_layout.addRow("Passphrase:", self.passphrase_edit)
        
        self.sandbox_checkbox = QCheckBox("Tryb testowy (Sandbox) - Zalecane dla testów")
        self.sandbox_checkbox.setChecked(True)
        self.sandbox_checkbox.setStyleSheet("""
            QCheckBox {
                color: #27ae60;
                font-weight: bold;
                font-size: 14px;
                padding: 8px;
                background: transparent;
                border: none;
            }
            QCheckBox::indicator {
                width: 20px;
                height: 20px;
                border: 2px solid #27ae60;
                border-radius: 4px;
                background: rgba(255, 255, 255, 0.1);
            }
            QCheckBox::indicator:checked {
                background: #27ae60;
                border-color: #27ae60;
            }
        """)
        api_layout.addRow("", self.sandbox_checkbox)
        
        scroll_layout.addWidget(api_group)
        
        # Parametry strategii
        self.strategy_group = QGroupBox("Parametry Strategii")
        self.strategy_group.setStyleSheet("""
            QGroupBox {
                font-weight: bold;
                font-size: 16px;
                border: 1px solid rgba(102, 126, 234, 0.3);
                border-radius: 10px;
                margin-top: 15px;
                padding-top: 15px;
                background: rgba(255, 255, 255, 0.05);
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 15px;
                padding: 0 10px 0 10px;
                color: #ffffff;
                background: transparent;
            }
        """)
        self.strategy_layout = QFormLayout(self.strategy_group)
        self.strategy_layout.setSpacing(12)
        self.strategy_layout.setLabelAlignment(Qt.AlignmentFlag.AlignRight)
        self.strategy_layout.setContentsMargins(20, 25, 20, 20)
        scroll_layout.addWidget(self.strategy_group)
        
        # Zarządzanie ryzykiem
        risk_group = QGroupBox("Zarządzanie Ryzykiem")
        risk_group.setStyleSheet("""
            QGroupBox {
                font-weight: bold;
                font-size: 16px;
                border: 1px solid rgba(102, 126, 234, 0.3);
                border-radius: 10px;
                margin-top: 15px;
                padding-top: 15px;
                background: rgba(255, 255, 255, 0.05);
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 15px;
                padding: 0 10px 0 10px;
                color: #ffffff;
                background: transparent;
            }
        """)
        risk_layout = QFormLayout(risk_group)
        risk_layout.setSpacing(12)
        risk_layout.setLabelAlignment(Qt.AlignmentFlag.AlignRight)
        risk_layout.setContentsMargins(20, 25, 20, 20)
        
        self.position_size_spin = QDoubleSpinBox()
        self.position_size_spin.setRange(10.0, 10000.0)
        self.position_size_spin.setValue(100.0)
        self.position_size_spin.setDecimals(2)
        self.position_size_spin.setSuffix(" USD")
        risk_layout.addRow("Kwota pozycji:", self.position_size_spin)
        
        self.stop_loss_spin = QDoubleSpinBox()
        self.stop_loss_spin.setRange(0.1, 10.0)
        self.stop_loss_spin.setValue(2.0)
        self.stop_loss_spin.setSuffix("%")
        risk_layout.addRow("Stop Loss:", self.stop_loss_spin)
        
        self.take_profit_spin = QDoubleSpinBox()
        self.take_profit_spin.setRange(0.1, 20.0)
        self.take_profit_spin.setValue(4.0)
        self.take_profit_spin.setSuffix("%")
        risk_layout.addRow("Take Profit:", self.take_profit_spin)
        
        scroll_layout.addWidget(risk_group)
        
        # Dodaj scroll_widget do scroll_area i scroll_area do głównego layoutu
        scroll_area.setWidget(scroll_widget)
        layout.addWidget(scroll_area)
        
        # Przyciski na dole
        button_layout = QHBoxLayout()
        button_layout.setSpacing(15)
        button_layout.setContentsMargins(0, 15, 0, 0)
        button_layout.addStretch()
        
        cancel_btn = QPushButton("❌ Anuluj")
        cancel_btn.setStyleSheet("""
            QPushButton {
                background-color: #e74c3c;
                color: white;
                border: none;
                padding: 12px 25px;
                border-radius: 8px;
                font-weight: bold;
                font-size: 14px;
                min-width: 120px;
            }
            QPushButton:hover {
                background-color: #c0392b;
            }
            QPushButton:pressed {
                background-color: #a93226;
            }
        """)
        cancel_btn.clicked.connect(self.reject)
        button_layout.addWidget(cancel_btn)
        
        create_btn = QPushButton("✅ Utwórz Bota")
        create_btn.setStyleSheet("""
            QPushButton {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                    stop:0 rgba(102, 126, 234, 0.8), 
                    stop:1 rgba(118, 75, 162, 0.8));
                color: white;
                border: 1px solid rgba(102, 126, 234, 0.5);
                padding: 12px 25px;
                border-radius: 8px;
                font-weight: bold;
                font-size: 14px;
                min-width: 120px;
            }
            QPushButton:hover {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                    stop:0 rgba(102, 126, 234, 1.0), 
                    stop:1 rgba(118, 75, 162, 1.0));
            }
            QPushButton:pressed {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                    stop:0 rgba(82, 106, 214, 0.9), 
                    stop:1 rgba(98, 55, 142, 0.9));
            }
        """)
        create_btn.clicked.connect(self.accept)
        button_layout.addWidget(create_btn)
        
        layout.addLayout(button_layout)
        
        # Ustaw domyślne parametry strategii
        self.on_strategy_changed("AI Trading Bot")
    
    def on_strategy_changed(self, strategy_name):
        """Aktualizuje parametry strategii"""
        # Wyczyść poprzednie parametry
        for i in reversed(range(self.strategy_layout.count())):
            self.strategy_layout.itemAt(i).widget().setParent(None)
        
        if strategy_name == "Scalping":
            # Parametry RSI
            self.rsi_period_spin = QSpinBox()
            self.rsi_period_spin.setRange(5, 50)
            self.rsi_period_spin.setValue(14)
            self.strategy_layout.addRow("Okres RSI:", self.rsi_period_spin)
            
            self.rsi_oversold_spin = QDoubleSpinBox()
            self.rsi_oversold_spin.setRange(10.0, 40.0)
            self.rsi_oversold_spin.setValue(30.0)
            self.strategy_layout.addRow("RSI Wyprzedanie:", self.rsi_oversold_spin)
            
            self.rsi_overbought_spin = QDoubleSpinBox()
            self.rsi_overbought_spin.setRange(60.0, 90.0)
            self.rsi_overbought_spin.setValue(70.0)
            self.strategy_layout.addRow("RSI Wykupienie:", self.rsi_overbought_spin)
            
            # Parametry EMA
            self.ema_fast_spin = QSpinBox()
            self.ema_fast_spin.setRange(5, 50)
            self.ema_fast_spin.setValue(12)
            self.strategy_layout.addRow("EMA Szybka:", self.ema_fast_spin)
            
            self.ema_slow_spin = QSpinBox()
            self.ema_slow_spin.setRange(10, 100)
            self.ema_slow_spin.setValue(26)
            self.strategy_layout.addRow("EMA Wolna:", self.ema_slow_spin)
            
            # Parametry zysku
            self.min_profit_spin = QDoubleSpinBox()
            self.min_profit_spin.setRange(0.1, 5.0)
            self.min_profit_spin.setValue(0.5)
            self.min_profit_spin.setSuffix("%")
            self.strategy_layout.addRow("Min. zysk:", self.min_profit_spin)
            
            # Maksymalny czas pozycji
            self.max_position_time_spin = QSpinBox()
            self.max_position_time_spin.setRange(60, 1800)
            self.max_position_time_spin.setValue(300)
            self.max_position_time_spin.setSuffix(" sek")
            self.strategy_layout.addRow("Max czas pozycji:", self.max_position_time_spin)
            
        elif strategy_name == "DCA (Dollar Cost Averaging)":
            # Kwota zakupu
            self.dca_amount_spin = QDoubleSpinBox()
            self.dca_amount_spin.setRange(10.0, 10000.0)
            self.dca_amount_spin.setValue(100.0)
            self.dca_amount_spin.setSuffix(" USDT")
            self.strategy_layout.addRow("Kwota zakupu:", self.dca_amount_spin)
            
            # Interwał czasowy
            self.dca_interval_spin = QSpinBox()
            self.dca_interval_spin.setRange(1, 10080)  # 1 minuta do 1 tygodnia
            self.dca_interval_spin.setValue(60)
            self.dca_interval_spin.setSuffix(" min")
            self.strategy_layout.addRow("Interwał:", self.dca_interval_spin)
            
            # Maksymalna liczba zleceń
            self.dca_max_orders_spin = QSpinBox()
            self.dca_max_orders_spin.setRange(1, 1000)
            self.dca_max_orders_spin.setValue(10)
            self.strategy_layout.addRow("Max zleceń:", self.dca_max_orders_spin)
            
            # Take profit
            self.dca_take_profit_spin = QDoubleSpinBox()
            self.dca_take_profit_spin.setRange(1.0, 100.0)
            self.dca_take_profit_spin.setValue(10.0)
            self.dca_take_profit_spin.setSuffix("%")
            self.strategy_layout.addRow("Take Profit:", self.dca_take_profit_spin)
            
        elif strategy_name == "Grid Trading":
            # Minimalna cena siatki
            self.grid_min_price_spin = QDoubleSpinBox()
            self.grid_min_price_spin.setRange(0.01, 100000.0)
            self.grid_min_price_spin.setValue(30000.0)
            self.grid_min_price_spin.setDecimals(2)
            self.strategy_layout.addRow("Min cena:", self.grid_min_price_spin)
            
            # Maksymalna cena siatki
            self.grid_max_price_spin = QDoubleSpinBox()
            self.grid_max_price_spin.setRange(0.01, 200000.0)
            self.grid_max_price_spin.setValue(50000.0)
            self.grid_max_price_spin.setDecimals(2)
            self.strategy_layout.addRow("Max cena:", self.grid_max_price_spin)
            
            # Liczba poziomów siatki
            self.grid_levels_spin = QSpinBox()
            self.grid_levels_spin.setRange(3, 100)
            self.grid_levels_spin.setValue(10)
            self.strategy_layout.addRow("Poziomy siatki:", self.grid_levels_spin)
            
            # Kwota inwestycji
            self.grid_investment_spin = QDoubleSpinBox()
            self.grid_investment_spin.setRange(100.0, 100000.0)
            self.grid_investment_spin.setValue(1000.0)
            self.grid_investment_spin.setSuffix(" USDT")
            self.strategy_layout.addRow("Kwota inwestycji:", self.grid_investment_spin)
            
        elif strategy_name == "Custom Strategy":
            # Interwał sprawdzania
            self.custom_interval_spin = QSpinBox()
            self.custom_interval_spin.setRange(5, 3600)
            self.custom_interval_spin.setValue(30)
            self.custom_interval_spin.setSuffix(" sek")
            self.strategy_layout.addRow("Interwał sprawdzania:", self.custom_interval_spin)
            
            # Informacja o regułach
            info_label = QLabel("Reguły handlowe można skonfigurować po utworzeniu bota")
            info_label.setStyleSheet("color: #888; font-style: italic;")
            self.strategy_layout.addRow("", info_label)
            
        elif strategy_name == "Swing Trading":
            # Timeframe
            self.swing_timeframe_combo = QComboBox()
            self.swing_timeframe_combo.addItems(["1h", "4h", "1d"])
            self.swing_timeframe_combo.setCurrentText("4h")
            self.strategy_layout.addRow("Timeframe:", self.swing_timeframe_combo)
            
            # Parametry RSI
            self.swing_rsi_period_spin = QSpinBox()
            self.swing_rsi_period_spin.setRange(5, 50)
            self.swing_rsi_period_spin.setValue(14)
            self.strategy_layout.addRow("Okres RSI:", self.swing_rsi_period_spin)
            
            self.swing_rsi_oversold_spin = QDoubleSpinBox()
            self.swing_rsi_oversold_spin.setRange(10.0, 40.0)
            self.swing_rsi_oversold_spin.setValue(30.0)
            self.strategy_layout.addRow("RSI Wyprzedanie:", self.swing_rsi_oversold_spin)
            
            self.swing_rsi_overbought_spin = QDoubleSpinBox()
            self.swing_rsi_overbought_spin.setRange(60.0, 90.0)
            self.swing_rsi_overbought_spin.setValue(70.0)
            self.strategy_layout.addRow("RSI Wykupienie:", self.swing_rsi_overbought_spin)
            
            # Średnie kroczące
            self.swing_ma_fast_spin = QSpinBox()
            self.swing_ma_fast_spin.setRange(5, 100)
            self.swing_ma_fast_spin.setValue(20)
            self.strategy_layout.addRow("MA Szybka:", self.swing_ma_fast_spin)
            
            self.swing_ma_slow_spin = QSpinBox()
            self.swing_ma_slow_spin.setRange(20, 200)
            self.swing_ma_slow_spin.setValue(50)
            self.strategy_layout.addRow("MA Wolna:", self.swing_ma_slow_spin)
            
            # Parametry zysku/straty
            self.swing_min_profit_spin = QDoubleSpinBox()
            self.swing_min_profit_spin.setRange(0.5, 10.0)
            self.swing_min_profit_spin.setValue(2.0)
            self.swing_min_profit_spin.setSuffix("%")
            self.strategy_layout.addRow("Min. zysk:", self.swing_min_profit_spin)
            
            self.swing_stop_loss_spin = QDoubleSpinBox()
            self.swing_stop_loss_spin.setRange(0.5, 5.0)
            self.swing_stop_loss_spin.setValue(1.5)
            self.swing_stop_loss_spin.setSuffix("%")
            self.strategy_layout.addRow("Stop Loss:", self.swing_stop_loss_spin)
            
            self.swing_take_profit_spin = QDoubleSpinBox()
            self.swing_take_profit_spin.setRange(1.0, 15.0)
            self.swing_take_profit_spin.setValue(3.0)
            self.swing_take_profit_spin.setSuffix("%")
            self.strategy_layout.addRow("Take Profit:", self.swing_take_profit_spin)
            
            # Maksymalne transakcje dziennie
            self.swing_max_daily_trades_spin = QSpinBox()
            self.swing_max_daily_trades_spin.setRange(1, 10)
            self.swing_max_daily_trades_spin.setValue(3)
            self.strategy_layout.addRow("Max transakcji/dzień:", self.swing_max_daily_trades_spin)
            
        elif strategy_name == "Arbitrage":
            # Minimalna różnica cenowa
            self.arbitrage_min_spread_spin = QDoubleSpinBox()
            self.arbitrage_min_spread_spin.setRange(0.1, 5.0)
            self.arbitrage_min_spread_spin.setValue(0.5)
            self.arbitrage_min_spread_spin.setSuffix("%")
            self.strategy_layout.addRow("Min. spread:", self.arbitrage_min_spread_spin)
            
            # Maksymalny czas pozycji
            self.arbitrage_max_position_time_spin = QSpinBox()
            self.arbitrage_max_position_time_spin.setRange(60, 3600)
            self.arbitrage_max_position_time_spin.setValue(300)
            self.arbitrage_max_position_time_spin.setSuffix(" sek")
            self.strategy_layout.addRow("Max czas pozycji:", self.arbitrage_max_position_time_spin)
            
            # Maksymalne transakcje dziennie
            self.arbitrage_max_daily_trades_spin = QSpinBox()
            self.arbitrage_max_daily_trades_spin.setRange(1, 50)
            self.arbitrage_max_daily_trades_spin.setValue(10)
            self.strategy_layout.addRow("Max transakcji/dzień:", self.arbitrage_max_daily_trades_spin)
            
            # Próg siły trendu
            self.arbitrage_trend_threshold_spin = QDoubleSpinBox()
            self.arbitrage_trend_threshold_spin.setRange(0.1, 1.0)
            self.arbitrage_trend_threshold_spin.setValue(0.6)
            self.strategy_layout.addRow("Próg siły trendu:", self.arbitrage_trend_threshold_spin)
            
            # Informacja o arbitrażu
            info_label = QLabel("⚡ Arbitraż wymaga połączenia z wieloma giełdami")
            info_label.setStyleSheet("""
                color: #f39c12; 
                font-style: italic; 
                font-size: 12px;
                padding: 10px;
                background: rgba(243, 156, 18, 0.1);
                border-radius: 5px;
                border: 1px solid rgba(243, 156, 18, 0.3);
            """)
            info_label.setWordWrap(True)
            self.strategy_layout.addRow("", info_label)
            
        elif strategy_name == "Moving Average Cross":
            self.fast_period_spin = QSpinBox()
            self.fast_period_spin.setRange(5, 50)
            self.fast_period_spin.setValue(10)
            self.strategy_layout.addRow("Szybka MA:", self.fast_period_spin)
            
            self.slow_period_spin = QSpinBox()
            self.slow_period_spin.setRange(10, 200)
            self.slow_period_spin.setValue(20)
            self.strategy_layout.addRow("Wolna MA:", self.slow_period_spin)
            
        elif strategy_name == "RSI Strategy":
            self.rsi_period_spin = QSpinBox()
            self.rsi_period_spin.setRange(5, 50)
            self.rsi_period_spin.setValue(14)
            self.strategy_layout.addRow("Okres RSI:", self.rsi_period_spin)
            
            self.oversold_spin = QSpinBox()
            self.oversold_spin.setRange(10, 40)
            self.oversold_spin.setValue(30)
            self.strategy_layout.addRow("Poziom wyprzedania:", self.oversold_spin)
            
            self.overbought_spin = QSpinBox()
            self.overbought_spin.setRange(60, 90)
            self.overbought_spin.setValue(70)
            self.strategy_layout.addRow("Poziom wykupienia:", self.overbought_spin)
            
        elif strategy_name == "AI Trading Bot":
            # Maksymalny budżet
            self.ai_budget_spin = QDoubleSpinBox()
            self.ai_budget_spin.setRange(50.0, 50000.0)
            self.ai_budget_spin.setValue(1000.0)
            self.ai_budget_spin.setSuffix(" USD")
            self.ai_budget_spin.setDecimals(2)
            self.ai_budget_spin.setStyleSheet("""
                QDoubleSpinBox {
                    background: rgba(255, 255, 255, 0.15);
                    border: 2px solid rgba(102, 126, 234, 0.5);
                    border-radius: 8px;
                    padding: 10px;
                    color: #ffffff;
                    font-size: 14px;
                    font-weight: bold;
                }
            """)
            self.strategy_layout.addRow("💰 Maksymalny budżet:", self.ai_budget_spin)
            
            # Cel zysku na godzinę
            self.ai_hourly_target_spin = QDoubleSpinBox()
            self.ai_hourly_target_spin.setRange(0.1, 100.0)
            self.ai_hourly_target_spin.setValue(2.0)
            self.ai_hourly_target_spin.setSuffix(" USD/h")
            self.ai_hourly_target_spin.setDecimals(2)
            self.ai_hourly_target_spin.setStyleSheet("""
                QDoubleSpinBox {
                    background: rgba(255, 255, 255, 0.15);
                    border: 2px solid rgba(46, 204, 113, 0.5);
                    border-radius: 8px;
                    padding: 10px;
                    color: #ffffff;
                    font-size: 14px;
                    font-weight: bold;
                }
            """)
            self.strategy_layout.addRow("🎯 Cel zysku/godzinę:", self.ai_hourly_target_spin)
            
            # Limit dziennych strat
            self.ai_loss_limit_spin = QDoubleSpinBox()
            self.ai_loss_limit_spin.setRange(10.0, 1000.0)
            self.ai_loss_limit_spin.setValue(100.0)
            self.ai_loss_limit_spin.setSuffix(" USD")
            self.ai_loss_limit_spin.setStyleSheet("""
                QDoubleSpinBox {
                    background: rgba(255, 255, 255, 0.15);
                    border: 2px solid rgba(231, 76, 60, 0.5);
                    border-radius: 8px;
                    padding: 10px;
                    color: #ffffff;
                    font-size: 14px;
                    font-weight: bold;
                }
            """)
            self.strategy_layout.addRow("🛡️ Limit dziennych strat:", self.ai_loss_limit_spin)
            
            # Włącz uczenie maszynowe
            self.ai_learning_checkbox = QCheckBox("Włącz uczenie maszynowe")
            self.ai_learning_checkbox.setChecked(True)
            self.ai_learning_checkbox.setStyleSheet("""
                QCheckBox {
                    color: #ffffff;
                    spacing: 8px;
                    font-size: 14px;
                }
                QCheckBox::indicator {
                    width: 18px;
                    height: 18px;
                    border: 2px solid rgba(102, 126, 234, 0.5);
                    border-radius: 4px;
                    background: rgba(255, 255, 255, 0.1);
                }
                QCheckBox::indicator:checked {
                    background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                        stop:0 rgba(102, 126, 234, 0.8), 
                        stop:1 rgba(118, 75, 162, 0.8));
                    border: 2px solid rgba(102, 126, 234, 0.8);
                }
            """)
            self.strategy_layout.addRow("", self.ai_learning_checkbox)
            
            # Informacja o AI
            info_label = QLabel("🤖 AI Bot automatycznie wybiera i optymalizuje strategie na podstawie warunków rynkowych")
            info_label.setStyleSheet("""
                color: #3498db; 
                font-style: italic; 
                font-size: 12px;
                padding: 10px;
                background: rgba(52, 152, 219, 0.1);
                border-radius: 5px;
                border: 1px solid rgba(52, 152, 219, 0.3);
            """)
            info_label.setWordWrap(True)
            self.strategy_layout.addRow("", info_label)
            
        elif strategy_name == "MACD Strategy":
            self.macd_fast_spin = QSpinBox()
            self.macd_fast_spin.setRange(5, 50)
            self.macd_fast_spin.setValue(12)
            self.strategy_layout.addRow("MACD Szybka:", self.macd_fast_spin)
            
            self.macd_slow_spin = QSpinBox()
            self.macd_slow_spin.setRange(10, 100)
            self.macd_slow_spin.setValue(26)
            self.strategy_layout.addRow("MACD Wolna:", self.macd_slow_spin)
            
            self.macd_signal_spin = QSpinBox()
            self.macd_signal_spin.setRange(5, 50)
            self.macd_signal_spin.setValue(9)
            self.strategy_layout.addRow("MACD Sygnał:", self.macd_signal_spin)
    
    def get_config(self) -> Dict[str, Any]:
        """Zwraca konfigurację bota"""
        config = {
            'name': self.name_edit.text(),
            'exchange': self.exchange_combo.currentText(),
            'symbol': self.symbol_combo.currentText(),
            'strategy': self.strategy_combo.currentText(),
            'api_key': self.api_key_edit.text(),
            'secret': self.secret_edit.text(),
            'passphrase': self.passphrase_edit.text(),
            'sandbox': self.sandbox_checkbox.isChecked(),
            'position_size': self.position_size_spin.value(),
            'stop_loss': self.stop_loss_spin.value() / 100,
            'take_profit': self.take_profit_spin.value() / 100,
        }
        
        # Dodaj parametry strategii
        strategy_name = self.strategy_combo.currentText()
        if strategy_name == "Scalping":
            config.update({
                'rsi_period': self.rsi_period_spin.value(),
                'rsi_oversold': self.rsi_oversold_spin.value(),
                'rsi_overbought': self.rsi_overbought_spin.value(),
                'ema_fast': self.ema_fast_spin.value(),
                'ema_slow': self.ema_slow_spin.value(),
                'min_profit_percentage': self.min_profit_spin.value(),
                'max_position_time': self.max_position_time_spin.value()
            })
        elif strategy_name == "DCA (Dollar Cost Averaging)":
            config.update({
                'amount': self.dca_amount_spin.value(),
                'interval': self.dca_interval_spin.value(),
                'max_orders': self.dca_max_orders_spin.value(),
                'take_profit': self.dca_take_profit_spin.value()
            })
        elif strategy_name == "Grid Trading":
            config.update({
                'min_price': self.grid_min_price_spin.value(),
                'max_price': self.grid_max_price_spin.value(),
                'grid_levels': self.grid_levels_spin.value(),
                'investment_amount': self.grid_investment_spin.value()
            })
        elif strategy_name == "Custom Strategy":
            config.update({
                'check_interval': self.custom_interval_spin.value()
            })
        elif strategy_name == "Moving Average Cross":
            config.update({
                'fast_period': self.fast_period_spin.value(),
                'slow_period': self.slow_period_spin.value()
            })
        elif strategy_name == "RSI Strategy":
            config.update({
                'rsi_period': self.rsi_period_spin.value(),
                'oversold': self.oversold_spin.value(),
                'overbought': self.overbought_spin.value()
            })
        elif strategy_name == "AI Trading Bot":
            config.update({
                'ai_max_budget': self.ai_budget_spin.value(),
                'ai_hourly_target': self.ai_hourly_target_spin.value(),
                'ai_loss_limit': self.ai_loss_limit_spin.value(),
                'ai_learning_enabled': self.ai_learning_checkbox.isChecked()
            })
        elif strategy_name == "MACD Strategy":
            config.update({
                'macd_fast': self.macd_fast_spin.value(),
                'macd_slow': self.macd_slow_spin.value(),
                'macd_signal': self.macd_signal_spin.value()
            })
        elif strategy_name == "Swing Trading":
            config.update({
                'timeframe': self.swing_timeframe_combo.currentText(),
                'rsi_period': self.swing_rsi_period_spin.value(),
                'rsi_oversold': self.swing_rsi_oversold_spin.value(),
                'rsi_overbought': self.swing_rsi_overbought_spin.value(),
                'ma_fast': self.swing_ma_fast_spin.value(),
                'ma_slow': self.swing_ma_slow_spin.value(),
                'min_profit_percentage': self.swing_min_profit_spin.value(),
                'stop_loss_percentage': self.swing_stop_loss_spin.value(),
                'take_profit_percentage': self.swing_take_profit_spin.value(),
                'max_daily_trades': self.swing_max_daily_trades_spin.value()
            })
        elif strategy_name == "Arbitrage":
            config.update({
                'min_spread_percentage': self.arbitrage_min_spread_spin.value(),
                'max_position_time': self.arbitrage_max_position_time_spin.value(),
                'max_daily_trades': self.arbitrage_max_daily_trades_spin.value(),
                'trend_strength_threshold': self.arbitrage_trend_threshold_spin.value()
            })
        
        return config


class BotStatusWidget(QWidget):
    """Widget statusu pojedynczego bota z nowoczesnym designem kafelkowym"""
    
    def __init__(self, bot_name: str, parent=None):
        super().__init__(parent)
        self.bot_name = bot_name
        self.is_running = False
        self.param_cards = {}
        self.setup_ui()
    
    def setup_ui(self):
        """Konfiguracja interfejsu"""
        layout = QVBoxLayout(self)
        layout.setSpacing(15)
        layout.setContentsMargins(20, 20, 20, 20)
        
        # Stylowanie głównego widgetu
        self.setStyleSheet("""
            BotStatusWidget {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 #ffffff, stop:1 #f8f9fa);
                border: 2px solid #dee2e6;
                border-radius: 15px;
                margin: 10px;
            }
            BotStatusWidget:hover {
                border-color: #3498db;
                box-shadow: 0 8px 25px rgba(52, 152, 219, 0.15);
            }
        """)
        
        # Nagłówek z ikoną i nazwą bota
        header_widget = QWidget()
        header_widget.setStyleSheet("""
            QWidget {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                    stop:0 #3498db, stop:1 #2980b9);
                border-radius: 12px;
                padding: 15px;
                margin: 0px;
            }
            QLabel {
                color: white;
                background: transparent;
            }
        """)
        header_layout = QHBoxLayout(header_widget)
        header_layout.setContentsMargins(20, 15, 20, 15)
        
        # Ikona bota
        bot_icon = QLabel("🤖")
        bot_icon.setStyleSheet("font-size: 24px; margin-right: 10px;")
        header_layout.addWidget(bot_icon)
        
        # Nazwa bota
        self.name_label = QLabel(self.bot_name)
        self.name_label.setStyleSheet("""
            font-size: 18px;
            font-weight: bold;
            color: white;
        """)
        header_layout.addWidget(self.name_label)
        
        header_layout.addStretch()
        
        # Status indicator
        self.status_label = QLabel("●")
        self.status_label.setStyleSheet("""
            color: #dc3545; 
            font-size: 24px;
        """)
        header_layout.addWidget(self.status_label)
        
        layout.addWidget(header_widget)
        
        # Sekcja informacji w kartach
        info_widget = QWidget()
        info_widget.setStyleSheet("""
            QWidget {
                background-color: white;
                border-radius: 12px;
                border: 1px solid #e9ecef;
                padding: 20px;
                margin: 0px;
            }
        """)
        info_layout = QVBoxLayout(info_widget)
        info_layout.setSpacing(15)
        
        # Nagłówek sekcji informacji
        info_header = QLabel("📊 Informacje o Bocie")
        info_header.setStyleSheet("""
            font-size: 16px;
            font-weight: bold;
            color: #495057;
            padding: 10px;
            background-color: #f8f9fa;
            border-radius: 8px;
            border: 1px solid #dee2e6;
        """)
        info_layout.addWidget(info_header)
        
        # Responsywny layout kart informacyjnych
        try:
            cards_layout = FlowLayout()
            cards_layout.setSpacing(15)
            cards_layout.setContentsMargins(5, 5, 5, 5)
            FLOW_AVAILABLE = True
        except:
            # Fallback do QGridLayout
            cards_layout = QGridLayout()
            cards_layout.setSpacing(15)
            FLOW_AVAILABLE = False
        
        # Karty informacyjne
        info_cards = [
            ("Strategia", "Moving Average", "#3498db"),
            ("Para", "BTC/USDT", "#17a2b8"),
            ("P&L", "$0.00", "#28a745"),
            ("Pozycja", "Brak", "#ffc107")
        ]
        
        for i, (label, value, color) in enumerate(info_cards):
            card = self.create_info_card(label, value, color)
            self.param_cards[label.lower()] = card
            
            if FLOW_AVAILABLE:
                cards_layout.addWidget(card)
            else:
                row = i // 2
                col = i % 2
                cards_layout.addWidget(card, row, col)
        
        info_layout.addLayout(cards_layout)
        layout.addWidget(info_widget)
        
        # Sekcja przycisków akcji
        self.buttons_widget = QWidget()
        self.buttons_widget.setStyleSheet("""
            QWidget {
                background-color: #f8f9fa;
                border-radius: 12px;
                border: 1px solid #e9ecef;
                padding: 20px;
                margin: 0px;
            }
        """)
        self.buttons_layout = QHBoxLayout(self.buttons_widget)
        self.buttons_layout.setSpacing(15)
        self.buttons_layout.setContentsMargins(15, 15, 15, 15)
        
        layout.addWidget(self.buttons_widget)
        
        # Utwórz przyciski na podstawie statusu
        self.create_action_buttons()
    
    def create_info_card(self, label: str, value: str, color: str) -> QWidget:
        """Tworzy kartę informacyjną"""
        card = QWidget()
        card.setStyleSheet(f"""
            QWidget {{
                background-color: white;
                border: 2px solid {color};
                border-radius: 10px;
                padding: 15px;
                min-height: 80px;
            }}
            QWidget:hover {{
                background-color: #f8f9fa;
                border-color: {color};
                box-shadow: 0 4px 12px rgba(0,0,0,0.1);
            }}
        """)
        
        layout = QVBoxLayout(card)
        layout.setSpacing(8)
        layout.setContentsMargins(15, 12, 15, 12)
        
        # Etykieta
        label_widget = QLabel(label)
        label_widget.setStyleSheet(f"""
            font-size: 12px;
            font-weight: bold;
            color: {color};
        """)
        layout.addWidget(label_widget)
        
        # Wartość
        value_widget = QLabel(value)
        value_widget.setObjectName("value")
        value_widget.setStyleSheet("""
            font-size: 16px;
            font-weight: bold;
            color: #2c3e50;
        """)
        layout.addWidget(value_widget)
        
        return card
    
    def create_action_buttons(self):
        """Tworzy przyciski akcji w zależności od statusu bota"""
        # Usuń wszystkie istniejące przyciski
        for i in reversed(range(self.buttons_layout.count())):
            child = self.buttons_layout.itemAt(i).widget()
            if child:
                child.setParent(None)
        
        if self.is_running:
            # Bot działa - pokaż Stop i Ustawienia
            self.stop_btn = QPushButton("⏹ Stop")
            self.stop_btn.setStyleSheet("""
                QPushButton {
                    background-color: #dc3545;
                    color: white;
                    min-width: 120px;
                    min-height: 50px;
                    font-size: 16px;
                    font-weight: bold;
                    border-radius: 12px;
                    padding: 15px 25px;
                    border: none;
                }
                QPushButton:hover {
                    background-color: #c82333;
                    box-shadow: 0 6px 20px rgba(220, 53, 69, 0.4);
                }
                QPushButton:pressed {
                    background-color: #bd2130;
                }
            """)
            self.stop_btn.clicked.connect(self.stop_bot)
            self.buttons_layout.addWidget(self.stop_btn)
            
            self.settings_btn = QPushButton("⚙️ Ustawienia")
            self.settings_btn.setStyleSheet("""
                QPushButton {
                    background-color: #6c757d;
                    color: white;
                    min-width: 120px;
                    min-height: 50px;
                    font-size: 16px;
                    font-weight: bold;
                    border-radius: 12px;
                    padding: 15px 25px;
                    border: none;
                }
                QPushButton:hover {
                    background-color: #5a6268;
                    box-shadow: 0 6px 20px rgba(108, 117, 125, 0.4);
                }
                QPushButton:pressed {
                    background-color: #545b62;
                }
            """)
            self.settings_btn.clicked.connect(self.edit_bot)
            self.buttons_layout.addWidget(self.settings_btn)
            
        else:
            # Bot zatrzymany - pokaż Start, Edytuj i Usuń
            self.start_btn = QPushButton("▶ Start")
            self.start_btn.setStyleSheet("""
                QPushButton {
                    background-color: #28a745;
                    color: white;
                    min-width: 100px;
                    min-height: 50px;
                    font-size: 16px;
                    font-weight: bold;
                    border-radius: 12px;
                    padding: 15px 20px;
                    border: none;
                }
                QPushButton:hover {
                    background-color: #218838;
                    box-shadow: 0 6px 20px rgba(40, 167, 69, 0.4);
                }
                QPushButton:pressed {
                    background-color: #1e7e34;
                }
            """)
            self.start_btn.clicked.connect(self.start_bot)
            self.buttons_layout.addWidget(self.start_btn)
            
            self.edit_btn = QPushButton("✏️ Edytuj")
            self.edit_btn.setStyleSheet("""
                QPushButton {
                    background-color: #3498db;
                    color: white;
                    min-width: 100px;
                    min-height: 50px;
                    font-size: 16px;
                    font-weight: bold;
                    border-radius: 12px;
                    padding: 15px 20px;
                    border: none;
                }
                QPushButton:hover {
                    background-color: #2980b9;
                    box-shadow: 0 6px 20px rgba(52, 152, 219, 0.4);
                }
                QPushButton:pressed {
                    background-color: #21618c;
                }
            """)
            self.edit_btn.clicked.connect(self.edit_bot)
            self.buttons_layout.addWidget(self.edit_btn)
            
            self.delete_btn = QPushButton("🗑️ Usuń")
            self.delete_btn.setStyleSheet("""
                QPushButton {
                    background-color: #e74c3c;
                    color: white;
                    min-width: 100px;
                    min-height: 50px;
                    font-size: 16px;
                    font-weight: bold;
                    border-radius: 12px;
                    padding: 15px 20px;
                    border: none;
                }
                QPushButton:hover {
                    background-color: #c0392b;
                    box-shadow: 0 6px 20px rgba(231, 76, 60, 0.4);
                }
                QPushButton:pressed {
                    background-color: #a93226;
                }
            """)
            self.delete_btn.clicked.connect(self.delete_bot)
            self.buttons_layout.addWidget(self.delete_btn)
        
        self.buttons_layout.addStretch()
    
    def update_status(self, status: Dict[str, Any]):
        """Aktualizuje status bota"""
        self.is_running = status.get('running', False)
        
        # Aktualizuj wskaźnik statusu
        if self.is_running:
            self.status_label.setStyleSheet("""
                color: #28a745; 
                font-size: 24px;
            """)
        else:
            self.status_label.setStyleSheet("""
                color: #dc3545; 
                font-size: 24px;
            """)
        
        # Aktualizuj informacje w kartach
        strategy = status.get('strategy', 'Moving Average')
        symbol = status.get('symbol', 'BTC/USDT')
        pnl = status.get('pnl', 0)
        positions = status.get('positions', 0)
        
        # Aktualizuj wartości w kartach
        if 'strategia' in self.param_cards:
            self.update_card_value(self.param_cards['strategia'], strategy)
        if 'para' in self.param_cards:
            self.update_card_value(self.param_cards['para'], symbol)
        if 'p&l' in self.param_cards:
            self.update_card_value(self.param_cards['p&l'], f"${pnl:.2f}")
        if 'pozycja' in self.param_cards:
            self.update_card_value(self.param_cards['pozycja'], f"{positions} pozycji" if positions > 0 else "Brak")
        
        # Przebuduj przyciski w zależności od statusu
        self.create_action_buttons()
    
    def update_card_value(self, card: QWidget, new_value: str):
        """Aktualizuje wartość w karcie"""
        value_labels = card.findChildren(QLabel)
        for label in value_labels:
            if label.objectName() == "value":
                label.setText(new_value)
                break
    
    def start_bot(self):
        """Uruchamia bota"""
        if hasattr(self.parent(), 'start_bot_signal'):
            self.parent().start_bot_signal.emit(self.bot_name)
        else:
            QMessageBox.information(self, "Start", f"Uruchamianie bota {self.bot_name}")
    
    def stop_bot(self):
        """Zatrzymuje bota"""
        if hasattr(self.parent(), 'stop_bot_signal'):
            self.parent().stop_bot_signal.emit(self.bot_name)
        else:
            QMessageBox.information(self, "Stop", f"Zatrzymywanie bota {self.bot_name}")
    
    def edit_bot(self):
        """Edytuje ustawienia bota"""
        QMessageBox.information(self, "Edycja", f"Edycja ustawień bota {self.bot_name}")
    
    def delete_bot(self):
        """Usuwa bota"""
        reply = QMessageBox.question(
            self, 
            "Potwierdzenie", 
            f"Czy na pewno chcesz usunąć bota {self.bot_name}?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No
        )
        if reply == QMessageBox.StandardButton.Yes:
            if hasattr(self.parent(), 'delete_bot_signal'):
                self.parent().delete_bot_signal.emit(self.bot_name)
            else:
                QMessageBox.information(self, "Usuń", f"Usuwanie bota {self.bot_name}")


class BotManagementWidget(QWidget):
    """Nowoczesny widget zarządzania botami z kartami"""
    
    start_bot_signal = pyqtSignal(str)
    stop_bot_signal = pyqtSignal(str)
    delete_bot_signal = pyqtSignal(str)
    
    def __init__(self, parent=None):
        super().__init__(parent)
        print("🏗️ Tworzę BotManagementWidget...")
        
        # Inicjalizuj logger
        self.logger = get_logger("bot_management")
        self.logger.info("FLOW: Inicjalizacja BotManagementWidget")
        
        # Inicjalizuj bot manager
        if BOT_ENGINES_AVAILABLE:
            self.bot_manager = BotManager()
            self.logger.info("FLOW: BotManager zainicjalizowany")
        else:
            self.bot_manager = None
            self.logger.warning("FLOW: BotManager niedostępny")
        
        # Inicjalizuj async manager
        if ASYNC_HELPER_AVAILABLE:
            self.async_manager = get_bot_async_manager()
            # Połącz sygnały async managera
            self.async_manager.bot_started.connect(self.on_bot_started)
            self.async_manager.bot_stopped.connect(self.on_bot_stopped)
            self.async_manager.bot_error.connect(self.on_bot_error)
            self.async_manager.bot_status_updated.connect(self.on_bot_status_updated)
        else:
            self.async_manager = None
        
        self.bot_cards = []  # Lista kart botów
        self.bots_data = {}  # Słownik do przechowywania danych botów
        self.setup_ui()
        
        # Timer do aktualizacji statusu (tylko jeśli nie ma async managera)
        if not ASYNC_HELPER_AVAILABLE:
            self.status_timer = QTimer()
            self.status_timer.timeout.connect(self.update_bots_status)
            self.status_timer.start(5000)  # Co 5 sekund
        
        # Timer do aktualizacji statystyk botów
        self.stats_timer = QTimer()
        self.stats_timer.timeout.connect(self.update_bot_statistics)
        self.stats_timer.start(3000)  # Co 3 sekundy
        
        # Połącz sygnały
        self.start_bot_signal.connect(self.start_bot)
        self.stop_bot_signal.connect(self.stop_bot)
        self.delete_bot_signal.connect(self.delete_bot)
        
        # Dodaj przykładowe boty dla demonstracji
        self.load_sample_bots()
        
    def closeEvent(self, event):
        """Zapewnia bezpieczne zatrzymanie timerów i czyszczenie asynchroniczne"""
        try:
            if hasattr(self, 'stats_timer') and self.stats_timer:
                try:
                    self.stats_timer.stop()
                except Exception:
                    pass
            if hasattr(self, 'status_timer') and self.status_timer:
                try:
                    self.status_timer.stop()
                except Exception:
                    pass
            if hasattr(self, 'async_manager') and self.async_manager:
                try:
                    self.async_manager.cleanup()
                except Exception:
                    pass
            if hasattr(self, 'bot_manager') and self.bot_manager:
                try:
                    # jeśli bot_manager ma metodę shutdown, wywołaj ją asynchronicznie
                    if hasattr(self.bot_manager, 'shutdown'):
                        try:
                            import asyncio
                            import concurrent.futures
                            # Wykryj czy pętla asyncio już działa
                            loop_running = False
                            try:
                                asyncio.get_running_loop()
                                loop_running = True
                            except RuntimeError:
                                loop_running = False
                            if loop_running:
                                # Uruchom shutdown w osobnym wątku z asyncio.run
                                with concurrent.futures.ThreadPoolExecutor() as executor:
                                    future = executor.submit(lambda: asyncio.run(self.bot_manager.shutdown()))
                                    try:
                                        future.result(timeout=5)
                                    except Exception:
                                        pass
                            else:
                                asyncio.run(self.bot_manager.shutdown())
                        except Exception:
                            pass
                except Exception:
                    pass
        except Exception as e:
            try:
                self.logger.warning(f"BotManagementWidget cleanup encountered an issue: {e}")
            except Exception:
                pass
        finally:
            try:
                super().closeEvent(event)
            except Exception:
                pass
    
    def __del__(self):
        """Dodatkowe zabezpieczenie przed pozostawieniem działających wątków"""
        try:
            if hasattr(self, 'stats_timer') and self.stats_timer:
                try:
                    self.stats_timer.stop()
                except Exception:
                    pass
            if hasattr(self, 'status_timer') and self.status_timer:
                try:
                    self.status_timer.stop()
                except Exception:
                    pass
            if hasattr(self, 'async_manager') and self.async_manager:
                try:
                    self.async_manager.cleanup()
                except Exception:
                    pass
        except Exception:
            pass
    
    def update_bot_statistics(self):
        """Aktualizuje statystyki botów z prawdziwymi danymi lub symulacją"""
        import random
        print("📊 Aktualizuję statystyki botów...")
        
        for bot_id, bot_data in self.bots_data.items():
            try:
                # Sprawdź czy mamy prawdziwy bot
                if BOT_ENGINES_AVAILABLE and hasattr(self, 'bot_manager') and bot_id in self.bot_manager.bots:
                    # Użyj prawdziwych danych z silnika bota
                    real_bot = self.bot_manager.bots[bot_id]
                    
                    # Aktualizuj dane z prawdziwego bota
                    bot_data['profit'] = real_bot.pnl
                    bot_data['trades'] = len(real_bot.orders)
                    bot_data['status'] = 'running' if real_bot.is_running else 'stopped'
                    
                    # Oblicz win rate na podstawie zleceń
                    if real_bot.orders:
                        profitable_orders = sum(1 for order in real_bot.orders if hasattr(order, 'profit') and order.profit > 0)
                        bot_data['win_rate'] = (profitable_orders / len(real_bot.orders)) * 100
                    else:
                        bot_data['win_rate'] = 0.0
                    
                    # Aktualizuj balance
                    if real_bot.balance:
                        total_balance = sum(balance.total for balance in real_bot.balance.values())
                        bot_data['balance'] = total_balance
                    
                    print(f"📊 Zaktualizowano prawdziwe dane dla {bot_id}: P&L={real_bot.pnl:.2f}, Trades={len(real_bot.orders)}")
                
                else:
                    # Użyj symulowanych danych dla botów demo
                    if bot_data.get('status') == 'running':
                        current_profit = bot_data.get('profit', 0)
                        current_trades = bot_data.get('trades', 0)
                        
                        # Losowa zmiana zysku (-5 do +10 USD)
                        profit_change = random.uniform(-5, 10)
                        new_profit = current_profit + profit_change
                        
                        # Losowa szansa na nowy trade (20%)
                        if random.random() < 0.2:
                            current_trades += 1
                            # Aktualizuj win rate na podstawie nowego trade'a
                            win_rate = bot_data.get('win_rate', 50)
                            if profit_change > 0:
                                # Wygrany trade - zwiększ win rate
                                win_rate = min(100, win_rate + random.uniform(0.5, 2))
                            else:
                                # Przegrany trade - zmniejsz win rate
                                win_rate = max(0, win_rate - random.uniform(0.5, 2))
                            
                            bot_data['win_rate'] = win_rate
                        
                        # Aktualizuj dane
                        bot_data['profit'] = new_profit
                        bot_data['trades'] = current_trades
                        
                        # Aktualizuj balance na podstawie zysku
                        initial_balance = 1000  # Początkowy balans
                        bot_data['balance'] = initial_balance + new_profit
                        
                        print(f"📊 Zaktualizowano symulowane dane dla {bot_id}: P&L={new_profit:.2f}, Trades={current_trades}")
                
            except Exception as e:
                print(f"❌ Błąd aktualizacji statystyk dla {bot_id}: {e}")
        
        # Odśwież wyświetlanie
        self.refresh_bots_display()
    
    def setup_ui(self):
        """Konfiguruje nowoczesny interfejs użytkownika z kartami"""
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(20, 20, 20, 20)
        main_layout.setSpacing(20)
        
        # Ustaw self.layout dla kompatybilności z innymi metodami
        self.layout = main_layout
        
        # Nowoczesne stylowanie
        self.setStyleSheet("""
            QWidget {
                background: transparent;
                color: #ffffff;
                font-family: 'Segoe UI', Arial, sans-serif;
            }
            
            QPushButton {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 #667eea, stop:1 #764ba2);
                border: none;
                border-radius: 12px;
                color: white;
                font-weight: 600;
                padding: 12px 24px;
                font-size: 14px;
                min-width: 120px;
            }
            
            QPushButton:hover {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 #7c8ef5, stop:1 #8a5fb5);
            }
            
            QPushButton:pressed {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 #5a6fd8, stop:1 #6b4190);
            }
        """)
        
        # Header z gradientem
        header_widget = QWidget()
        header_widget.setStyleSheet("""
            QWidget {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                    stop:0 #667eea, stop:1 #764ba2);
                border-radius: 16px;
                padding: 20px;
                margin-bottom: 10px;
            }
        """)
        header_layout = QHBoxLayout(header_widget)
        header_layout.setContentsMargins(20, 20, 20, 20)
        
        # Tytuł z ikoną
        title_layout = QHBoxLayout()
        title_label = QLabel("🤖 Zarządzanie Botami")
        title_label.setStyleSheet("""
            QLabel {
                font-size: 28px;
                font-weight: bold;
                color: white;
                margin: 0;
                padding: 0;
            }
        """)
        
        subtitle_label = QLabel("Nowoczesne zarządzanie botami handlowymi")
        subtitle_label.setStyleSheet("""
            QLabel {
                font-size: 14px;
                color: rgba(255, 255, 255, 0.8);
                margin-top: 5px;
            }
        """)
        
        title_container = QVBoxLayout()
        title_container.addWidget(title_label)
        title_container.addWidget(subtitle_label)
        title_container.setSpacing(5)
        
        title_layout.addLayout(title_container)
        title_layout.addStretch()
        
        # Przyciski akcji z nowoczesnymi ikonami
        actions_layout = QHBoxLayout()
        actions_layout.setSpacing(15)
        
        add_bot_btn = QPushButton("➕ Dodaj Bota")
        start_all_btn = QPushButton("▶️ Uruchom Wszystkie")
        stop_all_btn = QPushButton("⏹️ Zatrzymaj Wszystkie")
        
        actions_layout.addWidget(add_bot_btn)
        actions_layout.addWidget(start_all_btn)
        actions_layout.addWidget(stop_all_btn)
        
        header_layout.addLayout(title_layout)
        header_layout.addLayout(actions_layout)
        
        main_layout.addWidget(header_widget)
        
        # Połącz sygnały
        add_bot_btn.clicked.connect(self.add_new_bot)
        start_all_btn.clicked.connect(self.start_all_bots)
        stop_all_btn.clicked.connect(self.stop_all_bots)
        
        # Konfiguruj siatkę kart botów
        self.setup_bots_grid()
        
        # Główny layout z kartami
        main_layout.addWidget(self.bots_scroll_area)
    
    def setup_bots_grid(self):
        """Konfiguruje siatkę kart botów z responsywnym układem"""
        # Scroll area dla kart
        self.bots_scroll_area = QScrollArea()
        self.bots_scroll_area.setWidgetResizable(True)
        self.bots_scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.bots_scroll_area.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        self.bots_scroll_area.setStyleSheet("""
            QScrollArea {
                border: none;
                background-color: transparent;
                padding: 0px;
                margin: 0px;
            }
            QScrollBar:vertical {
                background-color: rgba(42, 42, 42, 0.8);
                width: 8px;
                border-radius: 4px;
                margin: 2px;
            }
            QScrollBar::handle:vertical {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 rgba(102, 126, 234, 0.8), stop:1 rgba(118, 75, 162, 0.8));
                border-radius: 4px;
                min-height: 20px;
                margin: 1px;
            }
            QScrollBar::handle:vertical:hover {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 rgba(124, 142, 245, 0.9), stop:1 rgba(138, 95, 181, 0.9));
            }
            QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
                height: 0px;
            }
        """)
        
        # Widget kontener z lepszym układem
        self.bots_container = QWidget()
        self.bots_container.setStyleSheet("""
            QWidget {
                background-color: transparent;
                padding: 0px;
                margin: 0px;
            }
        """)
        
        # FlowLayout dla responsywnego zawijania kart
        self.bots_flow_layout = FlowLayout(self.bots_container, margin=15, spacing=15)
        self.bots_container.setLayout(self.bots_flow_layout)
        
        self.bots_scroll_area.setWidget(self.bots_container)
    
    def add_bot_card(self, bot_data):
        """Dodaje nową kartę bota do responsywnego układu z zawijaniem"""
        if BOT_CARD_AVAILABLE:
            try:
                bot_card = BotCard(bot_data, self)
                self.bot_cards.append(bot_card)
                
                print(f"🃏 Dodaję kartę dla bota: {bot_data.get('name', 'Unknown')} do responsywnego układu")
                print(f"📐 Rozmiar karty: {bot_card.size()}")
                print(f"📊 Liczba elementów w layoutu przed dodaniem: {self.bots_flow_layout.count()}")
                
                # Dodaj kartę do FlowLayout - automatyczne zawijanie
                self.bots_flow_layout.addWidget(bot_card)
                
                print(f"📊 Liczba elementów w layoutu po dodaniu: {self.bots_flow_layout.count()}")
                print(f"✅ Karta dodana do layoutu")
                
                # Połącz sygnały
                print(f"🔗 Łączę sygnały dla bota: {bot_data.get('name', 'Unknown')}")
                bot_card.start_requested.connect(lambda bot_id, card=bot_card: self.start_bot_wrapper(bot_id, card))
                bot_card.stop_requested.connect(lambda bot_id, card=bot_card: self.stop_bot_wrapper(bot_id, card))
                bot_card.edit_requested.connect(lambda bot_id: self.edit_bot(bot_id))
                bot_card.delete_requested.connect(lambda bot_id: self.delete_bot(bot_id))
                
                return bot_card
            except Exception as e:
                print(f"❌ Błąd tworzenia BotCard: {e}")
                return self.add_fallback_bot_widget(bot_data)
        else:
            return self.add_fallback_bot_widget(bot_data)
    
    def add_fallback_bot_widget(self, bot_data):
        """Fallback widget gdy BotCard nie jest dostępny"""
        fallback_widget = QWidget()
        fallback_widget.setStyleSheet("""
            QWidget {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 #2a2a2a, stop:1 #1a1a1a);
                border-radius: 12px;
                border: 1px solid #3a3a3a;
                padding: 15px;
                margin: 5px;
            }
        """)
        
        layout = QVBoxLayout(fallback_widget)
        
        # Nazwa bota
        name_label = QLabel(bot_data.get('name', 'Bot'))
        name_label.setStyleSheet("""
            QLabel {
                font-size: 16px;
                font-weight: bold;
                color: #ffffff;
                margin-bottom: 5px;
            }
        """)
        
        # Status
        status_label = QLabel(f"Status: {bot_data.get('status', 'Nieaktywny')}")
        status_label.setStyleSheet("""
            QLabel {
                font-size: 12px;
                color: #cccccc;
            }
        """)
        
        layout.addWidget(name_label)
        layout.addWidget(status_label)
        
        # Oblicz pozycję w siatce
        row = len(self.bot_cards) // 3
        col = len(self.bot_cards) % 3
        
        self.bots_grid_layout.addWidget(fallback_widget, row, col)
        self.bot_cards.append(fallback_widget)
        
        return fallback_widget
    
    def clear_bots_grid(self):
        """Czyści siatkę botów"""
        for card in self.bot_cards:
            card.setParent(None)
        self.bot_cards.clear()
    
    def refresh_bots_display(self):
        """Odświeża wyświetlanie botów"""
        print("🔄 Odświeżanie wyświetlania botów...")
        
        # Sprawdź czy mamy karty do aktualizacji
        existing_cards = {card.bot_id: card for card in self.bot_cards if hasattr(card, 'bot_id')}
        
        # Aktualizuj istniejące karty lub dodaj nowe
        for bot_id, bot_data in self.bots_data.items():
            if bot_id in existing_cards:
                # Aktualizuj istniejącą kartę
                print(f"🔄 Aktualizuję kartę dla bota: {bot_id}")
                existing_cards[bot_id].update_data(bot_data)
            else:
                # Dodaj nową kartę
                print(f"🃏 Dodaję nową kartę dla bota: {bot_id}")
                self.add_bot_card(bot_data)
        
        # Usuń karty dla botów, które już nie istnieją
        for card in self.bot_cards[:]:  # Kopia listy
            if hasattr(card, 'bot_id') and card.bot_id not in self.bots_data:
                print(f"🗑️ Usuwam kartę dla nieistniejącego bota: {card.bot_id}")
                card.setParent(None)
                self.bot_cards.remove(card)
        

    
    def create_stat_card(self, icon: str, title: str, value: str, color: str) -> QWidget:
        """Tworzy kartę statystyki"""
        card = QWidget()
        card.setStyleSheet(f"""
            QWidget {{
                background-color: white;
                border: 2px solid {color};
                border-radius: 10px;
                padding: 15px;
            }}
        """)
        
        layout = QVBoxLayout(card)
        layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        
        # Ikona
        icon_label = QLabel(icon)
        icon_label.setStyleSheet(f"font-size: 24px; color: {color};")
        icon_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(icon_label)
        
        # Tytuł
        title_label = QLabel(title)
        title_label.setStyleSheet("font-size: 12px; color: #6c757d; font-weight: bold;")
        title_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(title_label)
        
        # Wartość
        value_label = QLabel(value)
        value_label.setObjectName("value")
        value_label.setStyleSheet(f"font-size: 18px; color: {color}; font-weight: bold;")
        value_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(value_label)
        
        return card
    
    def add_new_bot(self):
        """Dodaje nowego bota"""
        dialog = BotConfigDialog(self)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            config = dialog.get_config()
            
            if not config['name']:
                QMessageBox.warning(self, "Błąd", "Nazwa bota jest wymagana!")
                return
            
            if config['name'] in self.bot_widgets:
                QMessageBox.warning(self, "Błąd", "Bot o tej nazwie już istnieje!")
                return
            
            self.create_bot_from_config(config)
    
    def create_bot_from_config(self, config: Dict[str, Any]):
        """Tworzy bota z konfiguracji"""
        try:
            # Zapisz konfigurację bota przez ConfigManager
            config_manager = get_config_manager()
            current_config = config_manager.get_config('app')
            
            # Dodaj konfigurację bota do sekcji bots
            if 'bots' not in current_config:
                current_config['bots'] = {}
            
            bot_id = f"bot_{config['name']}_{int(datetime.now().timestamp())}"
            current_config['bots'][bot_id] = {
                'name': config['name'],
                'exchange': config['exchange'],
                'symbol': config['symbol'],
                'strategy': config['strategy'],
                'position_size': config['position_size'],
                'stop_loss': config['stop_loss'],
                'take_profit': config['take_profit'],
                'api_key': config.get('api_key', ''),
                'secret': config.get('secret', ''),
                'passphrase': config.get('passphrase', ''),
                'sandbox': config.get('sandbox', True),
                'created_at': datetime.now().isoformat(),
                'active': False
            }
            
            # Zapisz przez ConfigManager - to wyśle event CONFIG_UPDATED
            config_manager.save_config('app', current_config)
            self.log_message(f"✅ Konfiguracja bota {config['name']} zapisana przez ConfigManager")
            
            if not BOT_ENGINES_AVAILABLE:
                self.log_message("Bot engines nie są dostępne - tryb symulacji")
                return
            
            # Utwórz connector giełdy
            exchange = ExchangeConnector(
                exchange_name=config['exchange'],
                api_key=config['api_key'],
                secret=config['secret'],
                passphrase=config['passphrase'],
                sandbox=config['sandbox']
            )
            
            # Utwórz strategię
            strategy = None
            if config['strategy'] == "Moving Average Cross":
                strategy = MovingAverageCrossStrategy(
                    fast_period=config.get('fast_period', 10),
                    slow_period=config.get('slow_period', 20),
                    symbol=config['symbol']
                )
            elif config['strategy'] == "RSI Strategy":
                strategy = RSIStrategy(
                    period=config.get('rsi_period', 14),
                    oversold=config.get('oversold', 30),
                    overbought=config.get('overbought', 70),
                    symbol=config['symbol']
                )
            elif config['strategy'] == "AI Trading Bot":
                from app.strategy.ai_trading_bot import AITradingBot
                strategy = AITradingBot(
                    symbol=config['symbol'],
                    max_budget=config.get('ai_max_budget', 100.0),
                    hourly_target=config.get('ai_hourly_target', 2.0),
                    daily_loss_limit=config.get('ai_loss_limit', 100.0),
                    learning_enabled=config.get('ai_learning_enabled', True)
                )
            
            if not strategy:
                QMessageBox.warning(self, "Błąd", "Nieznana strategia!")
                return
            
            # Utwórz bota
            bot = TradingBot(config['name'], exchange, strategy, config['symbol'])
            bot.max_position_size = config['position_size']
            bot.stop_loss_pct = config['stop_loss']
            bot.take_profit_pct = config['take_profit']
            
            # Dodaj do menedżera
            self.bot_manager.add_bot(bot)
            
            # Utwórz widget
            bot_widget = BotStatusWidget(config['name'], self)
            self.bot_widgets[config['name']] = bot_widget
            
            # Dodaj do layoutu
            self.bots_layout.insertWidget(self.bots_layout.count() - 1, bot_widget)
            
            self.log_message(f"✅ Utworzono bota: {config['name']}")
            
        except Exception as e:
            QMessageBox.critical(self, "Błąd", f"Nie udało się utworzyć bota: {str(e)}")
            self.log_message(f"❌ Błąd tworzenia bota: {str(e)}")
    
    @pyqtSlot(str)
    def start_bot(self, bot_name: str):
        """Uruchamia bota"""
        self.logger.info(f"FLOW: UI -> Żądanie uruchomienia bota: {bot_name}")
        
        if not self.bot_manager or bot_name not in self.bot_manager.bots:
            self.logger.error(f"FLOW: Bot {bot_name} nie istnieje w BotManager")
            self.log_message(f"❌ Bot {bot_name} nie istnieje")
            return
        
        bot = self.bot_manager.bots[bot_name]
        self.logger.info(f"FLOW: Bot {bot_name} znaleziony w BotManager")
        
        if self.async_manager:
            # Użyj async managera
            self.logger.info(f"FLOW: Przekazywanie bota {bot_name} do AsyncManager")
            self.async_manager.start_bot(bot, bot_name)
            self.log_message(f"🚀 Uruchamianie bota: {bot_name}")
        else:
            # Fallback - stary sposób (może powodować problemy)
            self.logger.warning(f"FLOW: AsyncManager niedostępny, używam fallback dla {bot_name}")
            try:
                self._run_coroutine_in_thread(bot.start())
                self.log_message(f"🚀 Uruchomiono bota: {bot_name}")
            except Exception as e:
                self.logger.error(f"FLOW: Błąd uruchamiania bota {bot_name}: {str(e)}")
                self.log_message(f"❌ Błąd uruchamiania bota {bot_name}: {str(e)}")
    
    @pyqtSlot(str)
    def stop_bot(self, bot_name: str):
        """Zatrzymuje bota"""
        self.logger.info(f"FLOW: UI -> Żądanie zatrzymania bota: {bot_name}")
        
        if not self.bot_manager or bot_name not in self.bot_manager.bots:
            self.logger.error(f"FLOW: Bot {bot_name} nie istnieje w BotManager")
            self.log_message(f"❌ Bot {bot_name} nie istnieje")
            return
        
        self.logger.info(f"FLOW: Bot {bot_name} znaleziony w BotManager")
        
        if self.async_manager:
            # Użyj async managera
            self.logger.info(f"FLOW: Przekazywanie żądania zatrzymania bota {bot_name} do AsyncManager")
            self.async_manager.stop_bot(bot_name)
            self.log_message(f"🛑 Zatrzymywanie bota: {bot_name}")
        else:
            # Fallback - stary sposób
            self.logger.warning(f"FLOW: AsyncManager niedostępny, używam fallback dla {bot_name}")
            try:
                bot = self.bot_manager.bots[bot_name]
                self._run_coroutine_in_thread(bot.stop())
                self.log_message(f"🛑 Zatrzymano bota: {bot_name}")
            except Exception as e:
                self.logger.error(f"FLOW: Błąd zatrzymywania bota {bot_name}: {str(e)}")
                self.log_message(f"❌ Błąd zatrzymywania bota {bot_name}: {str(e)}")
    
    @pyqtSlot(str)
    def delete_bot(self, bot_name: str):
        """Usuwa bota"""
        if bot_name in self.bot_widgets:
            # Zatrzymaj bota jeśli działa
            self.stop_bot(bot_name)
            
            # Usuń widget
            widget = self.bot_widgets[bot_name]
            widget.setParent(None)
            del self.bot_widgets[bot_name]
            
            # Usuń z menedżera
            if self.bot_manager:
                self.bot_manager.remove_bot(bot_name)
            
            self.log_message(f"🗑️ Usunięto bota: {bot_name}")
    

    
    def update_bots_status(self):
        """Aktualizuje status botów"""
        if not self.bot_manager:
            return
        
        status_data = self.bot_manager.get_bots_status()
        
        active_count = 0
        total_pnl = 0.0
        total_positions = 0
        
        for bot_name, status in status_data.items():
            if bot_name in self.bot_widgets:
                self.bot_widgets[bot_name].update_status(status)
            
            if status['running']:
                active_count += 1
            
            total_pnl += status['pnl']
            total_positions += status['positions']
        
        # Aktualizuj statystyki
        if hasattr(self, 'active_bots_label'):
            self.active_bots_label.setText(str(active_count))
        
        if hasattr(self, 'total_pnl_label'):
            pnl_color = "#28a745" if total_pnl >= 0 else "#dc3545"
            self.total_pnl_label.setText(f"${total_pnl:.2f}")
            self.total_pnl_label.setStyleSheet(f"color: {pnl_color}; font-weight: bold; font-size: 24px;")
        
        if hasattr(self, 'total_positions_label'):
            self.total_positions_label.setText(str(total_positions))
        
        # Aktualizuj status połączenia
        if hasattr(self, 'connection_label'):
            if active_count > 0:
                self.connection_label.setStyleSheet("color: #28a745; font-size: 16px;")
            else:
                self.connection_label.setStyleSheet("color: #dc3545; font-size: 16px;")
    
    def log_message(self, message: str):
        """Dodaje wiadomość do logów"""
        timestamp = datetime.now().strftime("%H:%M:%S")
        formatted_message = f"[{timestamp}] {message}"
        
        if hasattr(self, 'logs_text'):
            self.logs_text.append(formatted_message)
            
            # Przewiń do końca
            cursor = self.logs_text.textCursor()
            cursor.movePosition(cursor.MoveOperation.End)
            self.logs_text.setTextCursor(cursor)
    
    def load_sample_bots(self):
        """Ładuje przykładowe boty z prawdziwymi silnikami"""
        print("📦 LOAD_SAMPLE_BOTS wywołane w bot_management.py")
        
        if not BOT_ENGINES_AVAILABLE:
            print("⚠️ Silniki botów niedostępne, ładuję dane demo")
            self.load_demo_bots()
            return
        
        try:
            # Utwórz prawdziwe boty z silnikami
            from trading.bot_engines import ExchangeConnector, TradingBot, MovingAverageCrossStrategy, RSIStrategy, BollingerBandsStrategy
            
            # Konfiguracja giełd (sandbox mode)
            binance_exchange = ExchangeConnector("binance", sandbox=True)
            bybit_exchange = ExchangeConnector("bybit", sandbox=True)
            kucoin_exchange = ExchangeConnector("kucoin", sandbox=True)
            
            # Strategie
            scalping_strategy = MovingAverageCrossStrategy(fast_period=5, slow_period=15)
            dca_strategy = RSIStrategy(period=14, oversold=30, overbought=70)
            grid_strategy = BollingerBandsStrategy(period=20, std_dev=2)
            
            # Boty
            bots_config = [
                {
                    'name': 'Scalping Pro',
                    'exchange_connector': binance_exchange,
                    'strategy': scalping_strategy,
                    'symbol': 'BTC/USDT',
                    'exchange': 'Binance'
                },
                {
                    'name': 'DCA Master',
                    'exchange_connector': bybit_exchange,
                    'strategy': dca_strategy,
                    'symbol': 'ETH/USDT',
                    'exchange': 'Bybit'
                },
                {
                    'name': 'Grid Trading',
                    'exchange_connector': kucoin_exchange,
                    'strategy': grid_strategy,
                    'symbol': 'ADA/USDT',
                    'exchange': 'KuCoin'
                }
            ]
            
            for config in bots_config:
                # Utwórz bota
                bot = TradingBot(
                    name=config['name'],
                    exchange_connector=config['exchange_connector'],
                    strategy=config['strategy'],
                    symbol=config['symbol']
                )
                
                # Dodaj do menedżera
                self.bot_manager.add_bot(bot)
                
                # Przygotuj dane dla UI
                bot_data = {
                    'name': config['name'],
                    'exchange': config['exchange'],
                    'symbol': config['symbol'],
                    'strategy': config['strategy'].name,
                    'status': 'stopped',
                    'profit': 0.0,
                    'trades': 0,
                    'win_rate': 0.0,
                    'balance': 1000.0
                }
                
                self.add_demo_bot_card(bot_data)
                
            print("✅ Załadowano boty z prawdziwymi silnikami")
            
        except Exception as e:
            print(f"❌ Błąd ładowania silników botów: {e}")
            print("⚠️ Przełączam na tryb demo")
            self.load_demo_bots()
    
    def load_demo_bots(self):
        """Ładuje przykładowe boty demo"""
        demo_bots = [
            {
                'name': 'Scalping Pro',
                'exchange': 'Binance',
                'symbol': 'BTC/USDT',
                'strategy': 'Scalping',
                'status': 'running',
                'profit': 125.50,
                'trades': 47,
                'win_rate': 68.5,
                'balance': 1250.00
            },
            {
                'name': 'DCA Master',
                'exchange': 'Bybit',
                'symbol': 'ETH/USDT',
                'strategy': 'DCA',
                'status': 'stopped',
                'profit': -23.75,
                'trades': 12,
                'win_rate': 41.7,
                'balance': 976.25
            },
            {
                'name': 'Grid Trading',
                'exchange': 'KuCoin',
                'symbol': 'ADA/USDT',
                'strategy': 'Grid',
                'status': 'running',
                'profit': 89.30,
                'trades': 156,
                'win_rate': 72.1,
                'balance': 1089.30
            }
        ]
        
        for bot_data in demo_bots:
            self.add_demo_bot_card(bot_data)
    
    def add_demo_bot_card(self, bot_data: Dict[str, Any]):
        """Dodaje kartę przykładowego bota"""
        # Sprawdź, czy bot już istnieje
        bot_id = bot_data['name']
        if bot_id in self.bots_data:
            print(f"⚠️ Bot {bot_id} już istnieje, pomijam duplikat")
            return
        
        # Zapisz dane bota
        self.bots_data[bot_id] = bot_data
        
        # Dodaj kartę bota
        bot_card = self.add_bot_card(bot_data)
        
        # Loguj dodanie bota
        print(f"✅ Dodano bota: {bot_data['name']} ({bot_data['strategy']} na {bot_data['exchange']})")
    

    
    def start_bot_wrapper(self, bot_id, card):
        """Wrapper dla start_bot z dodatkowym logowaniem"""
        print(f"🎯 KLIKNIĘTO Start dla bota: {bot_id}")
        print(f"🃏 Karta bota: {card}")
        self.start_bot(bot_id)
    
    def stop_bot_wrapper(self, bot_id, card):
        """Wrapper dla stop_bot z dodatkowym logowaniem"""
        print(f"🎯 KLIKNIĘTO Stop dla bota: {bot_id}")
        print(f"🃏 Karta bota: {card}")
        self.stop_bot(bot_id)
    
    def _run_coroutine_in_thread(self, coro):
        """Uruchamia coroutine w osobnym wątku z nową pętlą asyncio, bez wymagania aktywnej pętli w głównym wątku"""
        import asyncio
        import threading
        
        def worker():
            try:
                asyncio.run(coro)
            except Exception as e:
                try:
                    self.log_message(f"❌ Błąd uruchamiania coroutine: {e}")
                except Exception:
                    print(f"❌ Błąd uruchamiania coroutine: {e}")
        
        threading.Thread(target=worker, daemon=True).start()
    
    def start_bot(self, bot_id):
        """Uruchamia bota"""
        print(f"🔥 WYWOŁANO start_bot dla: {bot_id}")
        print(f"📊 Dostępne boty: {list(self.bots_data.keys())}")
        
        if bot_id not in self.bots_data:
            print(f"❌ Bot {bot_id} nie znaleziony w bots_data!")
            return
        
        # Aktualizuj status w UI
        self.bots_data[bot_id]['status'] = 'running'
        
        # Uruchom prawdziwy bot jeśli dostępny
        if BOT_ENGINES_AVAILABLE and hasattr(self, 'bot_manager') and bot_id in self.bot_manager.bots:
            bot = self.bot_manager.bots[bot_id]
            if hasattr(self, 'async_manager') and self.async_manager:
                # Użyj async managera
                self.async_manager.start_bot(bot, bot_id)
                print(f"🚀 Uruchomiono prawdziwy bot: {bot_id}")
            else:
                # Uruchom bezpośrednio
                import asyncio
                try:
                    self._run_coroutine_in_thread(bot.start())
                    print(f"🚀 Uruchomiono prawdziwy bot: {bot_id}")
                except Exception as e:
                    print(f"❌ Błąd uruchamiania bota {bot_id}: {e}")
        else:
            print(f"⚠️ Bot {bot_id} działa w trybie symulacji")
        
        # Odśwież wyświetlanie
        self.refresh_bots_display()
        print(f"✅ Bot {bot_id} uruchomiony")
    
    def stop_bot(self, bot_id):
        """Zatrzymuje bota"""
        print(f"🔥 WYWOŁANO stop_bot dla: {bot_id}")
        print(f"📊 Dostępne boty: {list(self.bots_data.keys())}")
        
        if bot_id not in self.bots_data:
            print(f"❌ Bot {bot_id} nie znaleziony w bots_data!")
            return
        
        # Aktualizuj status w UI
        self.bots_data[bot_id]['status'] = 'stopped'
        
        # Zatrzymaj prawdziwy bot jeśli dostępny
        if BOT_ENGINES_AVAILABLE and hasattr(self, 'bot_manager') and bot_id in self.bot_manager.bots:
            bot = self.bot_manager.bots[bot_id]
            if hasattr(self, 'async_manager') and self.async_manager:
                # Użyj async managera
                self.async_manager.stop_bot(bot_id)
                print(f"🛑 Zatrzymano prawdziwy bot: {bot_id}")
            else:
                # Zatrzymaj bezpośrednio
                import asyncio
                try:
                    self._run_coroutine_in_thread(bot.stop())
                    print(f"🛑 Zatrzymano prawdziwy bot: {bot_id}")
                except Exception as e:
                    print(f"❌ Błąd zatrzymywania bota {bot_id}: {e}")
        else:
            print(f"⚠️ Bot {bot_id} zatrzymany w trybie symulacji")
        
        # Odśwież wyświetlanie
        self.refresh_bots_display()
        print(f"✅ Bot {bot_id} zatrzymany")
    
    def edit_bot(self, bot_id):
        """Edytuje bota"""
        print(f"✏️ Edytowanie bota: {bot_id}")
        
        if bot_id not in self.bots_data:
            print(f"❌ Bot {bot_id} nie znaleziony!")
            return
        
        try:
            # Pobierz dane bota
            bot_data = self.bots_data[bot_id].copy()
            
            # Otwórz dialog edycji
            dialog = BotConfigDialog(self, bot_data=bot_data, edit_mode=True)
            
            if dialog.exec() == QDialog.DialogCode.Accepted:
                # Pobierz zaktualizowane dane
                updated_data = dialog.get_bot_data()
                
                # Aktualizuj dane bota
                self.bots_data[bot_id].update(updated_data)
                
                # Jeśli zmieniono nazwę, zaktualizuj klucz
                if updated_data.get('name') != bot_id:
                    new_name = updated_data['name']
                    self.bots_data[new_name] = self.bots_data.pop(bot_id)
                    
                    # Aktualizuj również w bot_manager jeśli istnieje
                    if BOT_ENGINES_AVAILABLE and hasattr(self, 'bot_manager') and bot_id in self.bot_manager.bots:
                        bot = self.bot_manager.bots.pop(bot_id)
                        bot.name = new_name
                        self.bot_manager.bots[new_name] = bot
                
                # Odśwież wyświetlanie
                self.refresh_bots_display()
                print(f"✅ Zaktualizowano bota: {bot_id}")
                
        except Exception as e:
            print(f"❌ Błąd edycji bota {bot_id}: {e}")
            # Pokaż komunikat błędu użytkownikowi
            from PyQt6.QtWidgets import QMessageBox
            QMessageBox.warning(self, "Błąd", f"Nie można edytować bota:\n{str(e)}")
    
    def delete_bot(self, bot_id):
        """Usuwa bota"""
        print(f"🗑️ Usuwanie bota: {bot_id}")
        
        if bot_id not in self.bots_data:
            print(f"❌ Bot {bot_id} nie znaleziony!")
            return
        
        # Pokaż dialog potwierdzenia
        from PyQt6.QtWidgets import QMessageBox
        reply = QMessageBox.question(
            self, 
            "Potwierdzenie usunięcia",
            f"Czy na pewno chcesz usunąć bota '{bot_id}'?\n\nTa operacja jest nieodwracalna.",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No
        )
        
        if reply == QMessageBox.StandardButton.Yes:
            try:
                # Zatrzymaj bota jeśli działa
                if self.bots_data[bot_id].get('status') == 'running':
                    self.stop_bot(bot_id)
                
                # Usuń z bot_manager jeśli istnieje
                if BOT_ENGINES_AVAILABLE and hasattr(self, 'bot_manager') and bot_id in self.bot_manager.bots:
                    self.bot_manager.remove_bot(bot_id)
                    print(f"🗑️ Usunięto bota z menedżera: {bot_id}")
                
                # Usuń dane bota
                del self.bots_data[bot_id]
                
                # Odśwież wyświetlanie
                self.refresh_bots_display()
                print(f"✅ Usunięto bota: {bot_id}")
                
            except Exception as e:
                print(f"❌ Błąd usuwania bota {bot_id}: {e}")
                QMessageBox.warning(self, "Błąd", f"Nie można usunąć bota:\n{str(e)}")
        else:
            print(f"❌ Anulowano usuwanie bota: {bot_id}")
    
    def start_all_bots(self):
        """Uruchamia wszystkie boty"""
        print("▶️ Uruchamianie wszystkich botów...")
        
        if hasattr(self, 'async_manager') and self.async_manager:
            # Użyj async managera do uruchomienia wszystkich botów
            for bot_id in self.bots_data:
                if BOT_ENGINES_AVAILABLE and bot_id in self.bot_manager.bots:
                    bot = self.bot_manager.bots[bot_id]
                    self.async_manager.start_bot(bot)
                    self.log_message(f"🚀 Uruchamianie bota: {bot_id}")
                else:
                    # Fallback - tylko aktualizuj status w UI
                    self.bots_data[bot_id]['status'] = 'running'
        else:
            # Fallback bez async managera
            if BOT_ENGINES_AVAILABLE and hasattr(self, 'bot_manager'):
                for bot_id in self.bots_data:
                    if bot_id in self.bot_manager.bots:
                        bot = self.bot_manager.bots[bot_id]
                        try:
                            self._run_coroutine_in_thread(bot.start())
                            self.log_message(f"🚀 Uruchamianie bota: {bot_id}")
                        except Exception as e:
                            self.log_message(f"❌ Błąd uruchamiania bota {bot_id}: {e}")
            else:
                # Tylko aktualizuj status w UI
                for bot_id in self.bots_data:
                    self.bots_data[bot_id]['status'] = 'running'
        
        self.refresh_bots_display()
    
    def stop_all_bots(self):
        """Zatrzymuje wszystkie boty"""
        print("⏹️ Zatrzymywanie wszystkich botów...")
        
        if hasattr(self, 'async_manager') and self.async_manager:
            # Użyj async managera do zatrzymania wszystkich botów
            for bot_id in self.bots_data:
                if BOT_ENGINES_AVAILABLE and bot_id in self.bot_manager.bots:
                    bot = self.bot_manager.bots[bot_id]
                    self.async_manager.stop_bot(bot)
                    self.log_message(f"🛑 Zatrzymywanie bota: {bot_id}")
                else:
                    # Fallback - tylko aktualizuj status w UI
                    self.bots_data[bot_id]['status'] = 'stopped'
        else:
            # Fallback bez async managera
            if BOT_ENGINES_AVAILABLE and hasattr(self, 'bot_manager'):
                for bot_id in self.bots_data:
                    if bot_id in self.bot_manager.bots:
                        bot = self.bot_manager.bots[bot_id]
                        try:
                            self._run_coroutine_in_thread(bot.stop())
                            self.log_message(f"🛑 Zatrzymywanie bota: {bot_id}")
                        except Exception as e:
                            self.log_message(f"❌ Błąd zatrzymywania bota {bot_id}: {e}")
            else:
                # Tylko aktualizuj status w UI
                for bot_id in self.bots_data:
                    self.bots_data[bot_id]['status'] = 'stopped'
        
        self.refresh_bots_display()
    
    # Metody obsługi sygnałów z async managera
    @pyqtSlot(str)
    def on_bot_started(self, bot_name: str):
        """Obsługuje sygnał uruchomienia bota"""
        self.log_message(f"✅ Bot {bot_name} uruchomiony pomyślnie")
        # Aktualizuj status w UI
        if bot_name in self.bots_data:
            self.bots_data[bot_name]['status'] = 'running'
            self.refresh_bots_display()
    
    @pyqtSlot(str)
    def on_bot_stopped(self, bot_name: str):
        """Obsługuje sygnał zatrzymania bota"""
        self.log_message(f"🛑 Bot {bot_name} zatrzymany")
        # Aktualizuj status w UI
        if bot_name in self.bots_data:
            self.bots_data[bot_name]['status'] = 'stopped'
            self.refresh_bots_display()
    
    @pyqtSlot(str, str)
    def on_bot_error(self, bot_name: str, error: str):
        """Obsługuje błędy botów"""
        self.log_message(f"❌ Błąd bota {bot_name}: {error}")
        # Aktualizuj status w UI
        if bot_name in self.bots_data:
            self.bots_data[bot_name]['status'] = 'error'
            self.refresh_bots_display()
    
    @pyqtSlot(str, dict)
    def on_bot_status_updated(self, bot_name: str, status: dict):
        """Obsługuje aktualizację statusu bota"""
        if bot_name in self.bots_data:
            # Aktualizuj dane bota
            self.bots_data[bot_name].update({
                'status': 'running' if status.get('running', False) else 'stopped',
                'symbol': status.get('symbol', 'N/A'),
                'strategy': status.get('strategy', 'N/A'),
                'trades': status.get('positions', 0) + status.get('orders', 0),
                'profit': status.get('pnl', 0.0)
            })
            self.refresh_bots_display()


# Klasa BotManagementWidget jest główną klasą tego modułu


def main():
    """Funkcja testowa"""
    if not PYQT_AVAILABLE:
        print("PyQt6 is not available. Please install it to run the GUI.")
        return
    
    import sys
    from PyQt6.QtWidgets import QApplication
    
    app = QApplication(sys.argv)
    
    widget = BotManagementWidget()
    widget.show()
    
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
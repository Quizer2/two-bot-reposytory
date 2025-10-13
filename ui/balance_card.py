"""
Moduł zawierający klasę BalanceCard - nowoczesną kartę salda kryptowaluty
"""

from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel, 
                             QPushButton, QFrame, QSizePolicy)
from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QFont
from typing import Dict, Any

# Import stylów
try:
    from ui.styles import get_card_style, get_button_style, COLORS
    STYLES_AVAILABLE = True
except ImportError:
    STYLES_AVAILABLE = False


class BalanceCard(QWidget):
    """Nowoczesna karta salda kryptowaluty z gradientami i animacjami"""
    
    # Sygnały
    trade_requested = pyqtSignal(str)
    details_requested = pyqtSignal(str)
    
    def __init__(self, balance_data: Dict[str, Any], parent=None):
        super().__init__(parent)
        self.balance_data = balance_data
        self.symbol = balance_data.get('symbol', 'UNKNOWN')
        self.setup_ui()
        self.update_data(balance_data)
    
    def setup_ui(self):
        """Konfiguruje responsywny interfejs karty"""
        # Ustawienia rozmiaru - kompaktowe ale czytelne
        self.setMinimumSize(240, 180)
        self.setMaximumSize(280, 220)
        self.setFixedHeight(210)
        self.setSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Fixed)
        
        # Główny layout
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)
        
        # Styl podobny do kafelków botów - prostszy i bardziej kompaktowy
        self.setStyleSheet("""
            BalanceCard {
                background-color: #2a2a2a;
                border: 1px solid #555;
                border-radius: 12px;
                margin: 5px;
                padding: 0px;
            }
            BalanceCard:hover {
                border: 1px solid #667eea;
                background-color: #2e2e2e;
            }
        """)
        
        # Header z symbolem i ikoną - bardziej kompaktowy
        header_frame = QFrame()
        header_frame.setFixedHeight(50)
        header_frame.setStyleSheet("""
            QFrame {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                    stop:0 rgba(102, 126, 234, 0.85), stop:0.5 rgba(118, 75, 162, 0.85), stop:1 rgba(102, 126, 234, 0.85));
                border-radius: 14px 14px 0 0;
                border: none;
            }
        """)
        header_layout = QHBoxLayout(header_frame)
        header_layout.setContentsMargins(12, 8, 12, 8)
        
        # Symbol kryptowaluty
        self.symbol_label = QLabel("BTC")
        self.symbol_label.setStyleSheet("""
            QLabel {
                color: white;
                font-size: 18px;
                font-weight: 700;
                background: transparent;
                letter-spacing: 0.5px;
            }
        """)
        
        # Ikona kryptowaluty
        self.crypto_icon = QLabel("₿")
        self.crypto_icon.setStyleSheet("""
            QLabel {
                color: white;
                font-size: 20px;
                font-weight: bold;
                background: transparent;
            }
        """)
        
        header_layout.addWidget(self.crypto_icon)
        header_layout.addWidget(self.symbol_label)
        header_layout.addStretch()
        
        # Content area - bardziej kompaktowy
        content_frame = QFrame()
        content_frame.setStyleSheet("""
            QFrame {
                background-color: #2a2a2a;
                border: none;
                border-radius: 0px 0px 12px 12px;
                padding: 8px;
                margin: 0px;
            }
        """)
        content_layout = QVBoxLayout(content_frame)
        content_layout.setContentsMargins(12, 8, 12, 8)
        content_layout.setSpacing(6)
        
        # Info rows podobne do kafelków botów - kompaktowe
        self.info_labels = {}
        info_data = [
            ("Saldo:", "0.00000000", 'balance'),
            ("Wartość:", "$0.00", 'value'),
            ("Zmiana 24h:", "+0.00%", 'change')
        ]
        
        for label_text, value_text, key in info_data:
            row_frame = QFrame()
            row_frame.setStyleSheet("""
                QFrame {
                    background-color: #3a3a3a;
                    border: 1px solid #555;
                    border-radius: 6px;
                    margin: 1px 0px;
                    padding: 4px;
                    min-height: 28px;
                    max-height: 32px;
                }
            """)
            
            row_layout = QHBoxLayout(row_frame)
            row_layout.setContentsMargins(6, 3, 6, 3)
            row_layout.setSpacing(8)
            
            label = QLabel(label_text)
            label.setStyleSheet("""
                QLabel {
                    color: #cccccc;
                    font-size: 11px;
                    font-weight: bold;
                    background-color: transparent;
                    min-width: 50px;
                    max-width: 70px;
                }
            """)
            
            value = QLabel(value_text)
            value.setStyleSheet("""
                QLabel {
                    color: #ffffff;
                    font-size: 11px;
                    font-weight: bold;
                    background-color: transparent;
                }
            """)
            value.setAlignment(Qt.AlignmentFlag.AlignRight)
            
            # Przechowuj referencję do etykiety wartości
            self.info_labels[key] = value
            
            row_layout.addWidget(label)
            row_layout.addStretch()
            row_layout.addWidget(value)
            content_layout.addWidget(row_frame)
        
        content_layout.addStretch()
        
        # Control buttons - bardziej kompaktowe
        buttons_layout = QHBoxLayout()
        buttons_layout.setSpacing(6)
        
        self.trade_btn = QPushButton("💱")
        self.details_btn = QPushButton("ℹ️")
        
        # Upewnij się, że przyciski są włączone i interaktywne
        self.trade_btn.setEnabled(True)
        self.details_btn.setEnabled(True)
        
        # Ustaw cursor na pointer dla lepszej interakcji
        self.trade_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.details_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        
        # Styl przycisków podobny do kafelków botów
        button_style = """
            QPushButton {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 #4CAF50, stop:1 #45a049);
                color: white;
                border: none;
                border-radius: 12px;
                font-size: 14px;
                font-weight: bold;
                min-width: 35px;
                max-width: 35px;
                min-height: 25px;
                max-height: 25px;
            }
            QPushButton:hover {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 #5CBF60, stop:1 #55b059);
            }
            QPushButton:pressed {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 #3e8e41, stop:1 #357a38);
            }
        """
        
        self.trade_btn.setStyleSheet(button_style)
        
        self.details_btn.setStyleSheet("""
            QPushButton {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 #ff9800, stop:1 #f57c00);
                color: white;
                border: none;
                border-radius: 15px;
                font-size: 16px;
                font-weight: bold;
                min-width: 40px;
                max-width: 40px;
                min-height: 30px;
                max-height: 30px;
                padding: 2px;
            }
            QPushButton:hover {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 #ffb74d, stop:1 #ff9800);
            }
            QPushButton:pressed {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 #f57c00, stop:1 #e65100);
            }
        """)
        
        buttons_layout.addWidget(self.trade_btn)
        buttons_layout.addStretch()
        buttons_layout.addWidget(self.details_btn)
        
        content_layout.addLayout(buttons_layout)
        
        # Dodaj do głównego layoutu
        main_layout.addWidget(header_frame)
        main_layout.addWidget(content_frame)
        
        # Połącz sygnały z debugiem
        self.trade_btn.clicked.connect(lambda: self._handle_trade_click())
        self.details_btn.clicked.connect(lambda: self._handle_details_click())
    
    def _handle_trade_click(self):
        """Obsługuje kliknięcie przycisku Trade z debugiem"""
        print(f"🔄 Trade button clicked for symbol: {self.symbol}")
        self.trade_requested.emit(self.symbol)
    
    def _handle_details_click(self):
        """Obsługuje kliknięcie przycisku Details z debugiem"""
        print(f"🔍 Details button clicked for symbol: {self.symbol}")
        self.details_requested.emit(self.symbol)
    
    def update_data(self, balance_data: Dict[str, Any]):
        """Aktualizuje dane karty"""
        self.balance_data = balance_data
        self.symbol = balance_data.get('symbol', 'UNKNOWN')
        
        # Aktualizuj symbol
        self.symbol_label.setText(self.symbol)
        
        # Aktualizuj ikonę na podstawie symbolu
        crypto_icons = {
            'BTC': '₿',
            'ETH': 'Ξ',
            'USDT': '₮',
            'USDC': '$',
            'BNB': '🔶',
            'ADA': '🔷',
            'DOT': '⚫',
            'LINK': '🔗',
            'LTC': 'Ł',
            'BCH': '₿',
            'XRP': '◊',
            'DOGE': '🐕',
            'MATIC': '🔺',
            'SOL': '☀️',
            'AVAX': '🔺',
            'UNI': '🦄',
            'ATOM': '⚛️',
            'FTT': '🔥',
            'NEAR': '🌐',
            'ALGO': '🔺'
        }
        icon = crypto_icons.get(self.symbol, '💰')
        self.crypto_icon.setText(icon)
        
        # Aktualizuj saldo
        balance = balance_data.get('balance', 0.0)
        if balance >= 1:
            balance_text = f"{balance:.4f}"
        elif balance >= 0.01:
            balance_text = f"{balance:.6f}"
        else:
            balance_text = f"{balance:.8f}"
        
        # Aktualizuj wartość USD
        usd_value = balance_data.get('usd_value', 0.0)
        
        # Aktualizuj zmianę 24h
        change_24h = balance_data.get('change_24h', 0.0)
        change_text = f"{change_24h:+.2f}%"
        change_color = "#4CAF50" if change_24h >= 0 else "#F44336"
        value_color = "#4CAF50" if change_24h >= 0 else "#F44336"
        
        # Aktualizuj etykiety w nowym systemie
        if 'balance' in self.info_labels:
            self.info_labels['balance'].setText(balance_text)
            
        if 'value' in self.info_labels:
            self.info_labels['value'].setText(f"${usd_value:.2f}")
            self.info_labels['value'].setStyleSheet(f"""
                QLabel {{
                    color: {value_color};
                    font-size: 11px;
                    font-weight: bold;
                    background-color: transparent;
                }}
            """)
            
        if 'change' in self.info_labels:
            self.info_labels['change'].setText(change_text)
            self.info_labels['change'].setStyleSheet(f"""
                QLabel {{
                    color: {change_color};
                    font-size: 11px;
                    font-weight: bold;
                    background-color: transparent;
                }}
            """)
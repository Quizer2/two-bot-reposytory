"""
Moduł zawierający klasę PortfolioSummaryCard - nowoczesną kartę podsumowania portfela
"""

try:
    from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel, 
                                 QFrame, QSizePolicy, QGridLayout)
    from PyQt6.QtCore import Qt
    from PyQt6.QtGui import QFont
    PYQT_AVAILABLE = True
except ImportError:
    PYQT_AVAILABLE = False

# Import stylów
try:
    from ui.styles import get_card_style, COLORS
    STYLES_AVAILABLE = True
except ImportError:
    STYLES_AVAILABLE = False

from typing import Dict, Any


class PortfolioSummaryCard(QWidget):
    """Nowoczesna karta podsumowania portfela z gradientami"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setup_ui()
        self.update_data({})
    
    def setup_ui(self):
        """Konfiguruje interfejs karty"""
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        self.setMinimumHeight(180)
        
        # Główny layout
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)
        
        # Stylowanie karty
        if STYLES_AVAILABLE:
            self.setStyleSheet(get_card_style("blue"))
            self.setProperty("class", "card")
        else:
            # Fallback style
            self.setStyleSheet("""
                PortfolioSummaryCard {
                    background: qlineargradient(x1:0, y1:0, x2:1, y2:1,
                        stop:0 #667eea, stop:0.5 #764ba2, stop:1 #667eea);
                    border-radius: 20px;
                    border: 3px solid rgba(255, 255, 255, 0.1);
                    margin: 10px;
                }
            """)
        
        # Content area
        content_frame = QFrame()
        content_frame.setStyleSheet("""
            QFrame {
                background: transparent;
                padding: 25px;
                margin: 3px;
            }
        """)
        content_layout = QGridLayout(content_frame)
        content_layout.setContentsMargins(25, 25, 25, 25)
        content_layout.setSpacing(20)
        
        # Główna wartość portfela
        main_value_layout = QVBoxLayout()
        main_value_layout.setSpacing(5)
        
        portfolio_title = QLabel("Całkowita Wartość Portfela")
        portfolio_title.setStyleSheet("""
            QLabel {
                font-size: 16px;
                color: rgba(255, 255, 255, 0.9);
                background: transparent;
                font-weight: 500;
            }
        """)
        
        self.total_value_label = QLabel("$0.00")
        self.total_value_label.setStyleSheet("""
            QLabel {
                font-size: 42px;
                font-weight: bold;
                color: white;
                background: transparent;
            }
        """)
        
        main_value_layout.addWidget(portfolio_title)
        main_value_layout.addWidget(self.total_value_label)
        main_value_layout.addStretch()
        
        content_layout.addLayout(main_value_layout, 0, 0, 2, 1)
        
        # Statystyki
        self.create_stat_item(content_layout, "Zmiana 24h", "change_24h", 0, 1)
        self.create_stat_item(content_layout, "P&L Dzienny", "daily_pnl", 0, 2)
        self.create_stat_item(content_layout, "Liczba Aktywów", "assets_count", 1, 1)
        self.create_stat_item(content_layout, "Najlepszy Aktyw", "best_performer", 1, 2)
        
        # Dodaj do głównego layoutu
        main_layout.addWidget(content_frame)
    
    def create_stat_item(self, layout: QGridLayout, title: str, key: str, row: int, col: int):
        """Tworzy element statystyki"""
        stat_layout = QVBoxLayout()
        stat_layout.setSpacing(5)
        
        # Tytuł
        title_label = QLabel(title)
        title_label.setStyleSheet("""
            QLabel {
                font-size: 12px;
                color: rgba(255, 255, 255, 0.8);
                background: transparent;
                font-weight: 500;
            }
        """)
        
        # Wartość
        value_label = QLabel("N/A")
        value_label.setStyleSheet("""
            QLabel {
                font-size: 18px;
                font-weight: bold;
                color: white;
                background: transparent;
            }
        """)
        value_label.setObjectName(f"value_{key}")
        
        stat_layout.addWidget(title_label)
        stat_layout.addWidget(value_label)
        stat_layout.addStretch()
        
        # Wrapper widget
        stat_widget = QWidget()
        stat_widget.setLayout(stat_layout)
        
        layout.addWidget(stat_widget, row, col)
    
    def update_data(self, portfolio_data: Dict[str, Any]):
        """Aktualizuje dane karty"""
        # Całkowita wartość
        total_value = portfolio_data.get('total_value', 0.0)
        self.total_value_label.setText(f"${total_value:,.2f}")
        
        # Zmiana 24h
        change_24h = portfolio_data.get('change_24h', 0.0)
        change_percent = portfolio_data.get('change_24h_percent', 0.0)
        change_text = f"${change_24h:+,.2f} ({change_percent:+.2f}%)"
        change_color = "#4CAF50" if change_24h >= 0 else "#F44336"
        
        change_label = self.findChild(QLabel, "value_change_24h")
        if change_label:
            change_label.setText(change_text)
            change_label.setStyleSheet(f"""
                QLabel {{
                    font-size: 18px;
                    font-weight: bold;
                    color: {change_color};
                    background: transparent;
                }}
            """)
        
        # P&L dzienny
        daily_pnl = portfolio_data.get('daily_pnl', 0.0)
        pnl_text = f"${daily_pnl:+,.2f}"
        pnl_color = "#4CAF50" if daily_pnl >= 0 else "#F44336"
        
        pnl_label = self.findChild(QLabel, "value_daily_pnl")
        if pnl_label:
            pnl_label.setText(pnl_text)
            pnl_label.setStyleSheet(f"""
                QLabel {{
                    font-size: 18px;
                    font-weight: bold;
                    color: {pnl_color};
                    background: transparent;
                }}
            """)
        
        # Liczba aktywów
        assets_count = portfolio_data.get('assets_count', 0)
        assets_label = self.findChild(QLabel, "value_assets_count")
        if assets_label:
            assets_label.setText(str(assets_count))
        
        # Najlepszy aktyw
        best_performer = portfolio_data.get('best_performer', 'N/A')
        best_label = self.findChild(QLabel, "value_best_performer")
        if best_label:
            best_label.setText(str(best_performer))


class StatCard(QWidget):
    """Mała karta statystyki"""
    
    def __init__(self, title: str, value: str = "0", icon: str = "📊", color: str = "#2196F3", parent=None):
        super().__init__(parent)
        self.title = title
        self.value = value
        self.icon = icon
        self.color = color
        self.setup_ui()
    
    def setup_ui(self):
        """Konfiguruje interfejs karty"""
        self.setFixedSize(200, 120)
        self.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Fixed)
        
        # Główny layout
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)
        
        # Stylowanie karty
        self.setStyleSheet(f"""
            StatCard {{
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 #2a2a2a, stop:1 #1a1a1a);
                border-radius: 12px;
                border: 2px solid {self.color};
                margin: 5px;
            }}
            StatCard:hover {{
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 #3a3a3a, stop:1 #2a2a2a);
                border: 2px solid {self.color};
            }}
        """)
        
        # Content area
        content_frame = QFrame()
        content_frame.setStyleSheet("""
            QFrame {
                background: transparent;
                padding: 15px;
                margin: 2px;
            }
        """)
        content_layout = QVBoxLayout(content_frame)
        content_layout.setContentsMargins(15, 15, 15, 15)
        content_layout.setSpacing(8)
        
        # Header z ikoną
        header_layout = QHBoxLayout()
        
        icon_label = QLabel(self.icon)
        icon_label.setStyleSheet(f"""
            QLabel {{
                font-size: 24px;
                color: {self.color};
                background: transparent;
            }}
        """)
        
        header_layout.addWidget(icon_label)
        header_layout.addStretch()
        
        content_layout.addLayout(header_layout)
        
        # Wartość
        self.value_label = QLabel(self.value)
        self.value_label.setStyleSheet("""
            QLabel {
                font-size: 20px;
                font-weight: bold;
                color: #ffffff;
                background: transparent;
            }
        """)
        content_layout.addWidget(self.value_label)
        
        # Tytuł
        title_label = QLabel(self.title)
        title_label.setStyleSheet("""
            QLabel {
                font-size: 12px;
                color: #cccccc;
                background: transparent;
                font-weight: 500;
            }
        """)
        content_layout.addWidget(title_label)
        
        content_layout.addStretch()
        
        # Dodaj do głównego layoutu
        main_layout.addWidget(content_frame)
    
    def update_value(self, value: str):
        """Aktualizuje wartość karty"""
        self.value = value
        self.value_label.setText(value)
"""
Moduł zawierający klasę BotCard - nowoczesną kartę bota
"""

from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel, 
                             QPushButton, QFrame, QSizePolicy)
from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QFont
from typing import Dict, Any


class BotCard(QWidget):
    """Nowoczesna karta bota z gradientami i animacjami"""
    
    # Sygnały
    start_requested = pyqtSignal(str)
    stop_requested = pyqtSignal(str)
    edit_requested = pyqtSignal(str)
    delete_requested = pyqtSignal(str)
    
    def __init__(self, bot_data: Dict[str, Any], parent=None):
        super().__init__(parent)
        self.bot_data = bot_data
        self.bot_id = bot_data.get('name', 'Unknown Bot')
        print(f"🎯 Tworzę BotCard dla: {self.bot_id}")
        self.setup_ui()
        self.update_data(bot_data)
        print(f"✅ BotCard utworzona dla: {self.bot_id}")
    
    def setup_ui(self):
        """Konfiguruje interfejs karty"""
        # Responsywne rozmiary z lepszym wykorzystaniem przestrzeni - zwiększone dla lepszego wyświetlania
        self.setMinimumSize(340, 320)
        self.setMaximumSize(400, 380)
        self.setSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Fixed)
        
        # Główny layout
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)
        
        # Główna ramka karty - ładny ale prosty styl
        self.setStyleSheet("""
            BotCard {
                background-color: #2a2a2a;
                border: 1px solid #555;
                border-radius: 12px;
                margin: 5px;
                padding: 0px;
            }
            BotCard:hover {
                border: 1px solid #667eea;
                background-color: #2e2e2e;
            }
        """)
        
        # Nagłówek - bardziej kompaktowy
        header_frame = QFrame()
        header_frame.setFixedHeight(60)
        header_layout = QHBoxLayout(header_frame)
        header_layout.setContentsMargins(16, 12, 16, 12)
        
        # Nowoczesne stylowanie nagłówka z gradientem
        header_frame.setStyleSheet("""
            QFrame {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                    stop:0 rgba(102, 126, 234, 0.85), stop:0.5 rgba(118, 75, 162, 0.85), stop:1 rgba(102, 126, 234, 0.85));
                border-radius: 14px 14px 0 0;
                border: none;
            }
        """)
        
        # Nazwa bota
        self.name_label = QLabel("Bot Name")
        self.name_label.setStyleSheet("""
            QLabel {
                color: white;
                font-size: 24px;
                font-weight: 700;
                background: transparent;
                letter-spacing: 0.5px;
            }
        """)
        
        # Wskaźnik statusu
        self.status_indicator = QLabel("●")
        self.status_indicator.setFixedSize(28, 28)
        self.status_indicator.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.status_indicator.setStyleSheet("""
            QLabel {
                color: #ff6b6b;
                font-size: 24px;
                font-weight: bold;
                background: rgba(255, 107, 107, 0.2);
                border-radius: 14px;
                border: 2px solid rgba(255, 107, 107, 0.5);
            }
        """)
        
        header_layout.addWidget(self.name_label)
        header_layout.addStretch()
        header_layout.addWidget(self.status_indicator)
        
        # Obszar zawartości - bardziej kompaktowy
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
        content_layout.setContentsMargins(16, 12, 16, 12)
        content_layout.setSpacing(6)
        
        # Info rows z nowoczesnymi stylami - przechowuj referencje do wartości
        self.info_labels = {}
        info_data = [
            ("Exchange:", "N/A", 'exchange'),
            ("Symbol:", "N/A", 'symbol'),
            ("Strategy:", "N/A", 'strategy'),
            ("P&L:", "$0.00", 'profit'),
            ("Trades:", "0", 'trades'),
            ("Win Rate:", "0.0%", 'win_rate')
        ]
        
        for label_text, value_text, key in info_data:
            row_frame = QFrame()
            row_frame.setStyleSheet("""
                QFrame {
                    background-color: #3a3a3a;
                    border: 1px solid #555;
                    border-radius: 6px;
                    margin: 2px 0px;
                    padding: 6px;
                    min-height: 32px;
                    max-height: 38px;
                }
            """)
            
            row_layout = QHBoxLayout(row_frame)
            row_layout.setContentsMargins(8, 4, 8, 4)
            row_layout.setSpacing(10)
            
            label = QPushButton(label_text)
            label.setStyleSheet("""
                QPushButton {
                    color: #cccccc;
                    font-size: 12px;
                    font-weight: bold;
                    background-color: transparent;
                    border: none;
                    padding: 2px 4px;
                    min-width: 60px;
                    max-width: 80px;
                    min-height: 20px;
                    max-height: 25px;
                    text-align: left;
                }
            """)
            
            value = QPushButton(value_text)
            value.setStyleSheet("""
                QPushButton {
                    color: #ffffff;
                    font-size: 12px;
                    font-weight: bold;
                    background-color: transparent;
                    border: none;
                    padding: 2px 4px;
                    min-width: 80px;
                    max-width: 120px;
                    min-height: 20px;
                    max-height: 25px;
                    text-align: right;
                }
            """)
            
            # Przechowuj referencję do etykiety wartości
            self.info_labels[key] = value
            
            row_layout.addWidget(label)
            row_layout.addStretch()
            row_layout.addWidget(value)
            content_layout.addWidget(row_frame)
        
        content_layout.addStretch()
        
        # Przyciski kontrolne - bardziej kompaktowe
        buttons_layout = QHBoxLayout()
        buttons_layout.setSpacing(6)
        
        # Przycisk Start - bardziej kompaktowy
        self.start_btn = QPushButton("▶")
        self.start_btn.setFixedSize(45, 30)
        self.start_btn.setToolTip("Uruchom bota")
        self.start_btn.setStyleSheet("""
            QPushButton {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 #4CAF50, stop:1 #45a049);
                color: white;
                border: none;
                border-radius: 15px;
                font-size: 16px;
                font-weight: bold;
            }
            QPushButton:hover {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 #5CBF60, stop:1 #55b059);
            }
            QPushButton:pressed {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 #3e8e41, stop:1 #357a38);
            }
        """)
        
        # Przycisk Stop - bardziej kompaktowy
        self.stop_btn = QPushButton("⏹")
        self.stop_btn.setFixedSize(45, 30)
        self.stop_btn.setToolTip("Zatrzymaj bota")
        self.stop_btn.setStyleSheet("""
            QPushButton {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 #f44336, stop:1 #d32f2f);
                color: white;
                border: none;
                border-radius: 15px;
                font-size: 16px;
                font-weight: bold;
            }
            QPushButton:hover {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 #f66356, stop:1 #e53935);
            }
            QPushButton:pressed {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 #c62828, stop:1 #b71c1c);
            }
        """)
        
        # Przycisk Edit - bardziej kompaktowy
        self.edit_btn = QPushButton("✏")
        self.edit_btn.setFixedSize(45, 30)
        self.edit_btn.setToolTip("Edytuj bota")
        self.edit_btn.setStyleSheet("""
            QPushButton {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 #ff9800, stop:1 #f57c00);
                color: white;
                border: none;
                border-radius: 15px;
                font-size: 16px;
                font-weight: bold;
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
        
        # Przycisk Delete - bardziej kompaktowy
        self.delete_btn = QPushButton("🗑")
        self.delete_btn.setFixedSize(45, 30)
        self.delete_btn.setToolTip("Usuń bota")
        self.delete_btn.setStyleSheet("""
            QPushButton {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 #6c757d, stop:1 #495057);
                color: white;
                border: none;
                border-radius: 15px;
                font-size: 16px;
                font-weight: bold;
            }
            QPushButton:hover {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 #868e96, stop:1 #6c757d);
            }
            QPushButton:pressed {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 #495057, stop:1 #343a40);
            }
        """)
        
        buttons_layout.addWidget(self.start_btn)
        buttons_layout.addWidget(self.stop_btn)
        buttons_layout.addStretch()
        buttons_layout.addWidget(self.edit_btn)
        buttons_layout.addWidget(self.delete_btn)
        
        content_layout.addLayout(buttons_layout)
        
        # Dodaj do głównego layoutu
        main_layout.addWidget(header_frame)
        main_layout.addWidget(content_frame)
        
        # Połącz sygnały
        print(f"🔗 Łączę sygnały przycisków dla bota: {self.bot_id}")
        self.start_btn.clicked.connect(lambda: self.on_start_clicked())
        self.stop_btn.clicked.connect(lambda: self.on_stop_clicked())
        self.edit_btn.clicked.connect(lambda: self.edit_requested.emit(self.bot_id))
        self.delete_btn.clicked.connect(lambda: self.delete_requested.emit(self.bot_id))
    

    
    def update_data(self, bot_data: Dict[str, Any]):
        """Aktualizuje dane bota"""
        print(f"🔄 UPDATE_DATA wywoływane dla bota: {bot_data.get('name', 'Unknown')}")
        self.bot_data = bot_data
        self.name_label.setText(bot_data.get('name', 'Bot'))
        
        # Aktualizuj status
        self.update_status(bot_data.get('status', 'stopped'))
        
        # Aktualizuj statystyki
        self.update_statistics(bot_data)
        print(f"✅ UPDATE_DATA zakończone dla bota: {bot_data.get('name', 'Unknown')}")

    def update_status(self, status: str):
        """Aktualizuje status bota"""
        print(f"📊 UPDATE_STATUS wywoływane: {status}")
        status_colors = {
            'running': '#4CAF50',
            'stopped': '#ff6b6b',
            'error': '#ff5722',
            'paused': '#ff9800'
        }
        
        color = status_colors.get(status, '#9e9e9e')
        self.status_indicator.setStyleSheet(f"""
            QLabel {{
                color: {color};
                font-size: 24px;
                font-weight: bold;
                background: rgba({color[1:3]}, {color[3:5]}, {color[5:7]}, 0.2);
                border-radius: 14px;
                border: 2px solid rgba({color[1:3]}, {color[3:5]}, {color[5:7]}, 0.5);
            }}
        """)
        print(f"✅ Status zaktualizowany na: {status} z kolorem: {color}")

    def update_statistics(self, bot_data: Dict[str, Any]):
        """Aktualizuje statystyki bota"""
        print(f"📈 UPDATE_STATISTICS wywoływane dla: {bot_data.get('name', 'Unknown')}")
        
        # Mapowanie danych na klucze
        stats_mapping = {
            'exchange': bot_data.get('exchange', 'N/A'),
            'symbol': bot_data.get('symbol', 'N/A'),
            'strategy': bot_data.get('strategy', 'N/A'),
            'profit': f"${bot_data.get('profit', 0.0):.2f}",
            'trades': str(bot_data.get('trades', 0)),
            'win_rate': f"{bot_data.get('win_rate', 0.0):.1f}%"
        }
        
        print(f"📊 Dane do aktualizacji: {stats_mapping}")
        
        # Aktualizuj każdą etykietę
        for key, value in stats_mapping.items():
            if key in self.info_labels:
                print(f"🔄 Aktualizuję {key}: {value}")
                self.info_labels[key].setText(str(value))
                print(f"✅ Zaktualizowano {key} na: {self.info_labels[key].text()}")
            else:
                print(f"⚠️ Nie znaleziono etykiety dla klucza: {key}")
        
        print(f"✅ UPDATE_STATISTICS zakończone")
    
    def on_start_clicked(self):
        """Obsługuje kliknięcie przycisku Start"""
        print(f"🎯 KLIKNIĘTO Start w karcie bota: {self.bot_id}")
        self.start_requested.emit(self.bot_id)
    
    def on_stop_clicked(self):
        """Obsługuje kliknięcie przycisku Stop"""
        print(f"🎯 KLIKNIĘTO Stop w karcie bota: {self.bot_id}")
        self.stop_requested.emit(self.bot_id)
    
    def update_info_row(self, row_widget: QWidget, value: str):
        """Aktualizuje wartość w rzędzie informacji"""
        value_label = row_widget.findChild(QLabel, "value")
        if value_label:
            value_label.setText(str(value))
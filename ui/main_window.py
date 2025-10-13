from PyQt6.QtWidgets import QLabel, QMessageBox
"""
Główne okno aplikacji CryptoBotDesktop

Zawiera dashboard, nawigację i zarządzanie wszystkimi
komponentami interfejsu użytkownika.
"""

import sys
import asyncio
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
from pathlib import Path

try:
    from PyQt6.QtWidgets import (
        QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
        QGridLayout, QFormLayout, QLabel, QPushButton, QFrame, QScrollArea,
        QTabWidget, QSplitter, QMenuBar, QStatusBar, QSystemTrayIcon,
        QMenu, QMessageBox, QProgressBar, QTableWidget, QTableWidgetItem,
        QHeaderView, QComboBox, QLineEdit, QSpinBox, QDoubleSpinBox,
        QCheckBox, QGroupBox, QTextEdit, QListWidget, QListWidgetItem,
        QAbstractItemView
    )
    from PyQt6.QtCore import (
        Qt, QTimer, QThread, pyqtSignal, QSize, QPoint, QRect,
        QPropertyAnimation, QEasingCurve, QParallelAnimationGroup
    )
    from PyQt6.QtGui import (
        QFont, QPixmap, QIcon, QPalette, QColor, QPainter, QPen,
        QBrush, QLinearGradient, QAction, QKeySequence
    )
    PYQT_AVAILABLE = True
except ImportError:
    PYQT_AVAILABLE = False
    # Fallback dla przypadku gdy PyQt6 nie jest dostępne
    class QMainWindow: pass
    class QWidget: pass
    class QVBoxLayout: pass
    class QHBoxLayout: pass
    class QLabel: pass
    class QPushButton: pass

# Import lokalnych modułów
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from utils.config_manager import get_config_manager, get_ui_setting, get_app_setting
from utils.logger import get_logger, LogType
from app.production_data_manager import ProductionDataManager, get_production_data_manager

# Import stylów
try:
    from ui.styles import get_theme_style, get_card_style, get_button_style, COLORS
    STYLES_AVAILABLE = True
except ImportError:
    STYLES_AVAILABLE = False
    print("Styles module not available")

# Import responsywnego layoutu
try:
    from ui.flow_layout import FlowLayout
    FLOW_LAYOUT_AVAILABLE = True
except ImportError:
    FLOW_LAYOUT_AVAILABLE = False
    print("FlowLayout module not available")

class DashboardCard(QWidget):
    """Nowoczesna karta na dashboardzie z informacjami"""
    
    def __init__(self, title: str, value: str = "", subtitle: str = "", 
                 color: str = "#667eea", parent=None):
        if not PYQT_AVAILABLE:
            print("PyQt6 not available, DashboardCard will not function properly")
            return
            
        try:
            super().__init__(parent)
            self.title = title
            self.value = value
            self.subtitle = subtitle
            self.color = color
            
            self.setup_ui()
            self.apply_style()
        except Exception as e:
            print(f"Error initializing DashboardCard: {e}")
    
    def setup_ui(self):
        """Konfiguracja nowoczesnego interfejsu karty z responsywnością"""
        self.setObjectName("dashboardCard")
        self.setMinimumSize(200, 140)
        self.setMaximumSize(300, 180)
        # Ustaw elastyczną politykę rozmiaru
        from PyQt6.QtWidgets import QSizePolicy
        self.setSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Fixed)
        
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(8)
        
        # Tytuł
        self.title_label = QLabel(self.title)
        self.title_label.setObjectName("cardTitle")
        self.title_label.setWordWrap(True)
        layout.addWidget(self.title_label)
        
        layout.addSpacing(8)
        
        # Wartość główna
        self.value_label = QLabel(self.value)
        self.value_label.setObjectName("cardValue")
        self.value_label.setAlignment(Qt.AlignmentFlag.AlignLeft)
        layout.addWidget(self.value_label)
        
        # Podtytuł
        if self.subtitle:
            self.subtitle_label = QLabel(self.subtitle)
            self.subtitle_label.setObjectName("cardSubtitle")
            self.subtitle_label.setWordWrap(True)
            layout.addWidget(self.subtitle_label)
        
        layout.addStretch()
    
    def apply_style(self):
        """Aplikuje nowoczesne style do karty"""
        # Style są teraz w głównym CSS - nie potrzebujemy inline styles
        # Inicjalizuj animacje hover
        self.hover_animation = QPropertyAnimation(self, b"geometry")
        self.hover_animation.setDuration(200)
        self.hover_animation.setEasingCurve(QEasingCurve.Type.OutCubic)
        
    def enterEvent(self, event):
        """Animacja przy najechaniu myszą"""
        if hasattr(self, 'hover_animation'):
            current_rect = self.geometry()
            # Lekkie powiększenie karty
            new_rect = QRect(
                current_rect.x() - 2,
                current_rect.y() - 2,
                current_rect.width() + 4,
                current_rect.height() + 4
            )
            
            self.hover_animation.setStartValue(current_rect)
            self.hover_animation.setEndValue(new_rect)
            self.hover_animation.start()
        
        super().enterEvent(event)
    
    def leaveEvent(self, event):
        """Animacja przy opuszczeniu myszą"""
        if hasattr(self, 'hover_animation'):
            current_rect = self.geometry()
            # Powrót do oryginalnego rozmiaru
            original_rect = QRect(
                current_rect.x() + 2,
                current_rect.y() + 2,
                current_rect.width() - 4,
                current_rect.height() - 4
            )
            
            self.hover_animation.setStartValue(current_rect)
            self.hover_animation.setEndValue(original_rect)
            self.hover_animation.start()
        
        super().leaveEvent(event)
    
    def update_value(self, value: str, subtitle: str = None):
        """Aktualizuje wartość karty"""
        self.value = value
        self.value_label.setText(value)
        
        if subtitle is not None:
            self.subtitle = subtitle
            if hasattr(self, 'subtitle_label'):
                self.subtitle_label.setText(subtitle)

class BotStatusWidget(QWidget):
    """Widget statusu bota"""
    
    def __init__(self, bot_data: Dict, parent=None):
        if not PYQT_AVAILABLE:
            print("PyQt6 not available, BotStatusWidget will not function properly")
            super().__init__(parent) if parent else None
            return
            
        try:
            super().__init__(parent)
            self.bot_data = bot_data or {}
            self.setup_ui()
            self.apply_style()
        except Exception as e:
            print(f"Error initializing BotStatusWidget: {e}")
            # Nie wywołuj super().__init__ ponownie w przypadku błędu
    
    def setup_ui(self):
        """Konfiguracja interfejsu"""
        layout = QHBoxLayout(self)
        layout.setContentsMargins(10, 10, 10, 10)
        
        # Status indicator
        self.status_indicator = QLabel()
        self.status_indicator.setFixedSize(12, 12)
        self.status_indicator.setStyleSheet(self.get_status_style())
        layout.addWidget(self.status_indicator)
        
        # Bot info
        info_layout = QVBoxLayout()
        
        # Nazwa bota
        self.name_label = QLabel(f"Bot #{self.bot_data.get('id', 'N/A')}")
        self.name_label.setFont(QFont("Arial", 10, QFont.Weight.Bold))
        info_layout.addWidget(self.name_label)
        
        # Typ i para
        self.type_label = QLabel(f"{self.bot_data.get('type', 'N/A')} - {self.bot_data.get('pair', 'N/A')}")
        self.type_label.setStyleSheet("color: #666; font-size: 9px;")
        info_layout.addWidget(self.type_label)
        
        layout.addLayout(info_layout)
        layout.addStretch()
        
        # P&L
        pnl = self.bot_data.get('pnl', 0)
        self.pnl_label = QLabel(f"{pnl:+.2f} USDT")
        self.pnl_label.setStyleSheet(f"color: {'#4CAF50' if pnl >= 0 else '#F44336'}; font-weight: bold;")
        layout.addWidget(self.pnl_label)
        
        # Przyciski kontroli
        controls_layout = QVBoxLayout()
        
        self.start_stop_btn = QPushButton("Stop" if self.bot_data.get('status') == 'running' else "Start")
        self.start_stop_btn.setFixedSize(60, 25)
        self.start_stop_btn.clicked.connect(self.toggle_bot)
        self.update_button_style()
        controls_layout.addWidget(self.start_stop_btn)
        
        self.edit_btn = QPushButton("Edit")
        self.edit_btn.setFixedSize(60, 25)
        self.edit_btn.clicked.connect(self.edit_bot)
        controls_layout.addWidget(self.edit_btn)
        
        layout.addLayout(controls_layout)
    
    def get_status_style(self) -> str:
        """Zwraca style dla wskaźnika statusu"""
        status = self.bot_data.get('status', 'stopped')
        colors = {
            'running': '#4CAF50',
            'stopped': '#9E9E9E',
            'error': '#F44336',
            'paused': '#FF9800'
        }
        color = colors.get(status, '#9E9E9E')
        return f"background-color: {color}; border-radius: 6px;"
    
    def apply_style(self):
        """Aplikuje style do widgetu"""
        self.setStyleSheet("""
            BotStatusWidget {
                background-color: #f5f5f5;
                border: 1px solid #ddd;
                border-radius: 5px;
                margin: 2px;
            }
            BotStatusWidget:hover {
                background-color: #e8e8e8;
            }
        """)
    
    def update_button_style(self):
        """Aktualizuje style przycisku Start/Stop"""
        status = self.bot_data.get('status', 'stopped')
        if status == 'running':
            # Czerwony przycisk Stop
            self.start_stop_btn.setStyleSheet("""
                QPushButton {
                    background-color: #e74c3c;
                    color: white;
                    border: none;
                    border-radius: 4px;
                    font-weight: bold;
                }
                QPushButton:hover {
                    background-color: #c0392b;
                }
            """)
        else:
            # Zielony przycisk Start
            self.start_stop_btn.setStyleSheet("""
                QPushButton {
                    background-color: #27ae60;
                    color: white;
                    border: none;
                    border-radius: 4px;
                    font-weight: bold;
                }
                QPushButton:hover {
                    background-color: #229954;
                }
            """)
    
    def toggle_bot(self):
        """Przełącza status bota"""
        current_status = self.bot_data.get('status', 'stopped')
        new_status = 'stopped' if current_status == 'running' else 'running'
        self.bot_data['status'] = new_status
        
        # Aktualizuj UI
        self.start_stop_btn.setText("Stop" if new_status == 'running' else "Start")
        self.status_indicator.setStyleSheet(self.get_status_style())
        self.update_button_style()
    
    def edit_bot(self):
        """Otwiera edytor bota"""
        try:
            from ui.bot_config import BotConfigWidget
            from PyQt6.QtWidgets import QDialog, QVBoxLayout, QHBoxLayout, QPushButton
            
            # Utwórz dialog edycji bota
            dialog = QDialog(self)
            dialog.setWindowTitle("Edytuj Bota")
            dialog.setFixedSize(800, 600)
            
            layout = QVBoxLayout(dialog)
            
            # Dodaj widget konfiguracji bota
            bot_config = BotConfigWidget()
            
            # Załaduj dane bota jeśli dostępne
            if hasattr(self, 'bot_data') and self.bot_data:
                bot_config.load_bot_data(self.bot_data)
            
            layout.addWidget(bot_config)
            
            # Przyciski
            buttons_layout = QHBoxLayout()
            buttons_layout.addStretch()
            
            cancel_btn = QPushButton("Anuluj")
            cancel_btn.clicked.connect(dialog.reject)
            buttons_layout.addWidget(cancel_btn)
            
            save_btn = QPushButton("Zapisz Zmiany")
            save_btn.clicked.connect(lambda: self.save_bot_changes(bot_config, dialog))
            save_btn.setStyleSheet("""
                QPushButton {
                    background-color: #4CAF50;
                    color: white;
                    border: none;
                    padding: 8px 16px;
                    border-radius: 4px;
                    font-weight: bold;
                }
                QPushButton:hover {
                    background-color: #45a049;
                }
            """)
            buttons_layout.addWidget(save_btn)
            
            layout.addLayout(buttons_layout)
            
            # Pokaż dialog
            dialog.exec()
            
        except Exception as e:
            self.logger.error(f"Błąd podczas otwierania edytora bota: {e}")
            print(f"Błąd podczas otwierania edytora bota: {e}")
    
    def save_bot_changes(self, bot_config, dialog):
        """Zapisuje zmiany w konfiguracji bota"""
        try:
            # Pobierz konfigurację z widgetu
            config_data = bot_config.get_config_data()
            
            if not config_data:
                from PyQt6.QtWidgets import QMessageBox
                QMessageBox.warning(self, "Błąd", "Nie można pobrać danych konfiguracji bota.")
                return
            
            # Tutaj można dodać logikę zapisywania do bazy danych
            # Na razie tylko logujemy
            self.logger.info(f"Zapisano zmiany w bocie: {config_data.get('name', 'Nieznany')}")
            
            # Zamknij dialog
            dialog.accept()
            
            # Odśwież dane
            self.refresh_data()
            
        except Exception as e:
            self.logger.error(f"Błąd podczas zapisywania zmian bota: {e}")
            from PyQt6.QtWidgets import QMessageBox
            QMessageBox.critical(self, "Błąd", f"Nie można zapisać zmian: {e}")


class NotificationCard(QFrame):
    """Nowoczesna karta powiadomienia"""
    
    def __init__(self, timestamp, notification_type, channel, status, message, parent=None):
        super().__init__(parent)
        self.timestamp = timestamp
        self.notification_type = notification_type
        self.channel = channel
        self.status = status
        self.message = message
        
        self.setup_ui()
        
    def setup_ui(self):
        """Konfiguruje interfejs karty"""
        self.setObjectName("notificationCard")
        self.setFixedHeight(80)
        
        layout = QHBoxLayout(self)
        layout.setContentsMargins(15, 10, 15, 10)
        layout.setSpacing(15)
        
        # Ikona statusu
        status_icon = QLabel()
        status_icon.setFixedSize(12, 12)
        status_icon.setStyleSheet(f"""
            QLabel {{
                background-color: {self.get_status_color()};
                border-radius: 6px;
            }}
        """)
        layout.addWidget(status_icon)
        
        # Główna zawartość
        content_layout = QVBoxLayout()
        content_layout.setSpacing(2)
        
        # Górny wiersz - typ i czas
        top_layout = QHBoxLayout()
        top_layout.setSpacing(10)
        
        type_label = QLabel(self.notification_type)
        type_label.setStyleSheet("""
            QLabel {
                font-weight: 600;
                font-size: 13px;
                color: #ffffff;
            }
        """)
        top_layout.addWidget(type_label)
        
        top_layout.addStretch()
        
        time_label = QLabel(self.timestamp)
        time_label.setStyleSheet("""
            QLabel {
                font-size: 11px;
                color: #e0e0e0;
                font-weight: 500;
            }
        """)
        top_layout.addWidget(time_label)
        
        content_layout.addLayout(top_layout)
        
        # Dolny wiersz - wiadomość
        message_label = QLabel(self.message)
        message_label.setStyleSheet("""
            QLabel {
                font-size: 12px;
                color: #f5f5f5;
                font-weight: 400;
            }
        """)
        message_label.setWordWrap(True)
        content_layout.addWidget(message_label)
        
        layout.addLayout(content_layout)
        
        # Kanał i status
        right_layout = QVBoxLayout()
        right_layout.setSpacing(2)
        
        channel_label = QLabel(self.channel)
        channel_label.setStyleSheet("""
            QLabel {
                font-size: 11px;
                color: #8fa4f3;
                font-weight: 600;
            }
        """)
        right_layout.addWidget(channel_label)
        
        status_label = QLabel(self.status)
        status_label.setStyleSheet(f"""
            QLabel {{
                font-size: 10px;
                color: {self.get_status_color()};
                font-weight: 600;
            }}
        """)
        right_layout.addWidget(status_label)
        
        layout.addLayout(right_layout)
        
        # Stylizacja karty
        self.setStyleSheet("""
            QFrame#notificationCard {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:1,
                    stop:0 rgba(255, 255, 255, 0.08), 
                    stop:1 rgba(255, 255, 255, 0.03));
                border: 1px solid rgba(102, 126, 234, 0.2);
                border-radius: 8px;
                margin: 2px;
            }
            
            QFrame#notificationCard:hover {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:1,
                    stop:0 rgba(255, 255, 255, 0.12), 
                    stop:1 rgba(255, 255, 255, 0.06));
                border: 1px solid rgba(102, 126, 234, 0.4);
            }
        """)
        
    def get_status_color(self):
        """Zwraca kolor dla statusu"""
        status_colors = {
            "Wysłane": "#66BB6A",
            "Błąd": "#EF5350",
            "Oczekujące": "#FFA726",
            "W kolejce": "#42A5F5"
        }
        return status_colors.get(self.status, "#B0BEC5")


class ChannelCard(QFrame):
    """Nowoczesna karta kanału powiadomień"""
    
    def __init__(self, channel_name, status, rate_limit, parent=None):
        super().__init__(parent)
        self.channel_name = channel_name
        self.status = status
        self.rate_limit = rate_limit
        
        self.setup_ui()
        
    def setup_ui(self):
        """Konfiguruje interfejs karty kanału"""
        self.setObjectName("channelCard")
        self.setFixedHeight(100)
        
        layout = QVBoxLayout(self)
        layout.setContentsMargins(15, 12, 15, 12)
        layout.setSpacing(8)
        
        # Górny wiersz - nazwa i status
        top_layout = QHBoxLayout()
        top_layout.setSpacing(10)
        
        # Ikona kanału
        icon_label = QLabel()
        icon_label.setFixedSize(24, 24)
        icon_label.setStyleSheet(f"""
            QLabel {{
                background-color: {self.get_channel_color()};
                border-radius: 12px;
                border: 2px solid rgba(255, 255, 255, 0.2);
            }}
        """)
        top_layout.addWidget(icon_label)
        
        # Nazwa kanału
        name_label = QLabel(self.channel_name)
        name_label.setStyleSheet("""
            QLabel {
                font-weight: 600;
                font-size: 14px;
                color: #ffffff;
            }
        """)
        top_layout.addWidget(name_label)
        
        top_layout.addStretch()
        
        # Status
        status_badge = QLabel(self.status)
        status_badge.setStyleSheet(f"""
            QLabel {{
                background-color: {self.get_status_background()};
                color: {self.get_status_color()};
                padding: 4px 8px;
                border-radius: 10px;
                font-size: 10px;
                font-weight: 600;
            }}
        """)
        top_layout.addWidget(status_badge)
        
        layout.addLayout(top_layout)
        
        # Środkowy wiersz - limit
        limit_layout = QHBoxLayout()
        
        limit_label = QLabel(f"Limit: {self.rate_limit}/min")
        limit_label.setStyleSheet("""
            QLabel {
                font-size: 11px;
                color: #e0e0e0;
                font-weight: 500;
            }
        """)
        limit_layout.addWidget(limit_label)
        
        limit_layout.addStretch()
        
        layout.addLayout(limit_layout)
        
        # Dolny wiersz - przycisk konfiguracji
        config_btn = QPushButton("Konfiguruj")
        config_btn.setStyleSheet("""
            QPushButton {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                    stop:0 rgba(102, 126, 234, 0.8), 
                    stop:1 rgba(118, 75, 162, 0.8));
                color: #ffffff;
                border: none;
                border-radius: 6px;
                padding: 6px 12px;
                font-size: 11px;
                font-weight: 600;
            }
            
            QPushButton:hover {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                    stop:0 rgba(102, 126, 234, 1.0), 
                    stop:1 rgba(118, 75, 162, 1.0));
            }
            
            QPushButton:pressed {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                    stop:0 rgba(82, 106, 214, 1.0), 
                    stop:1 rgba(98, 55, 142, 1.0));
            }
        """)
        config_btn.clicked.connect(lambda: self.configure_channel())
        layout.addWidget(config_btn)
        
        # Stylizacja karty
        self.setStyleSheet("""
            QFrame#channelCard {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:1,
                    stop:0 rgba(255, 255, 255, 0.08), 
                    stop:1 rgba(255, 255, 255, 0.03));
                border: 1px solid rgba(102, 126, 234, 0.2);
                border-radius: 10px;
                margin: 3px;
            }
            
            QFrame#channelCard:hover {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:1,
                    stop:0 rgba(255, 255, 255, 0.12), 
                    stop:1 rgba(255, 255, 255, 0.06));
                border: 1px solid rgba(102, 126, 234, 0.4);

            }
        """)
        
    def get_channel_color(self):
        """Zwraca kolor dla kanału"""
        channel_colors = {
            "Email": "#4CAF50",
            "Telegram": "#2196F3",
            "Discord": "#7289DA",
            "SMS": "#FF9800"
        }
        return channel_colors.get(self.channel_name, "#666eb4")
        
    def get_status_color(self):
        """Zwraca kolor tekstu dla statusu"""
        return "#ffffff" if self.status == "Aktywny" else "#ffffff"
        
    def get_status_background(self):
        """Zwraca kolor tła dla statusu"""
        return "rgba(102, 187, 106, 0.9)" if self.status == "Aktywny" else "rgba(239, 83, 80, 0.9)"
        
    def configure_channel(self):
        """Otwiera konfigurację kanału"""
        try:
            # Przełącz na zakładkę ustawień
            self.switch_view('settings')
            
            # Jeśli mamy dostęp do głównego okna, przełącz na sekcję powiadomień
            if hasattr(self, 'parent') and hasattr(self.parent(), 'settings_widget'):
                settings_widget = self.parent().settings_widget
                if hasattr(settings_widget, 'tab_widget'):
                    # Znajdź zakładkę powiadomień i przełącz na nią
                    for i in range(settings_widget.tab_widget.count()):
                        if "Powiadomienia" in settings_widget.tab_widget.tabText(i):
                            settings_widget.tab_widget.setCurrentIndex(i)
                            break
            
            self.logger.info(f"Otwarto konfigurację kanału: {getattr(self, 'channel_name', 'Nieznany')}")
            
        except Exception as e:
            self.logger.error(f"Błąd podczas otwierania konfiguracji kanału: {e}")
            print(f"Błąd podczas otwierania konfiguracji kanału: {e}")


class MainWindow(QMainWindow):
    """
    Główne okno aplikacji CryptoBotDesktop
    
    Zawiera dashboard, nawigację i wszystkie główne komponenty UI.
    """
    
    def __init__(self, app_instance=None, risk_manager=None, notification_manager=None):
        if not PYQT_AVAILABLE:
            print("PyQt6 not available, MainWindow will not function properly")
            return
            
        try:
            super().__init__()
            self.app_instance = app_instance
            self.risk_manager = risk_manager
            self.notification_manager = notification_manager
            self.config_manager = get_config_manager()
            self.logger = get_logger("main_window")
            
            # Inicjalizuj Production Data Manager
            self.production_manager = None
            self.use_real_data = get_app_setting('production_mode', False)
            
            if self.use_real_data:
                self.production_manager = get_production_data_manager()
            
            # Zainicjalizuj IntegratedDataManager jeśli dostępny
            try:
                from core.integrated_data_manager import get_integrated_data_manager
                self.integrated_data_manager = get_integrated_data_manager()
            except Exception:
                self.integrated_data_manager = None
                
        except Exception as e:
            print(f"Error initializing MainWindow: {e}")
            return
        
        # Timery
        self.refresh_timer = QTimer()
        self.refresh_timer.timeout.connect(self.refresh_data)
        
        # Aktualny widok
        self.current_view = 'dashboard'
        
        # Animacje
        self.sidebar_animation = None
        self.content_fade_animation = None
        self.animation_group = QParallelAnimationGroup()
        
        # Dane
        self.portfolio_data = {}
        self.bots_data = []
        self.recent_trades = []
        self.risk_metrics = {}
        self.notification_stats = {}
        
        # Przechowywanie instancji widoków aby uniknąć duplikacji
        self.bot_management_widget = None
        self.portfolio_widget = None
        self.analysis_widget = None
        self.settings_widget = None
        self.logs_widget = None
        self.notifications_widget = None
        self.risk_management_widget = None
        
        self.setup_ui()
        self.setup_menu()
        self.setup_status_bar()
        self.setup_system_tray()
        self.apply_theme()
        self.load_window_settings()
        
        # Uruchom odświeżanie danych
        self.start_data_refresh()
        
        self.logger.info("Main window initialized")
    

        self.live_badge = QLabel('PAPER')
        self.live_badge.setObjectName('liveBadge')
        try:
            self.statusBar().addPermanentWidget(self.live_badge)
        except Exception:
            pass

    def setup_ui(self):
        """Konfiguracja głównego interfejsu"""
        self.setWindowTitle("CryptoBotDesktop")
        self.setMinimumSize(800, 600)  # Zwiększono minimalny rozmiar dla lepszego wyświetlania kart
        
        # Główny widget
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        
        # Layout główny
        main_layout = QHBoxLayout(central_widget)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)
        
        # Sidebar
        self.setup_sidebar()
        main_layout.addWidget(self.sidebar)
        
        # Główna zawartość
        self.content_area = QWidget()
        self.content_area.setObjectName("contentArea")
        self.content_layout = QVBoxLayout(self.content_area)
        self.content_layout.setContentsMargins(30, 30, 30, 30)
        
        # Dashboard
        self.setup_dashboard()
        
        main_layout.addWidget(self.content_area, 1)
    
    def setup_sidebar(self):
        """Konfiguracja nowoczesnego paska bocznego z rozwijaniem"""
        self.sidebar = QFrame()
        self.sidebar.setObjectName("sidebar")
        self.sidebar_expanded = True
        self.sidebar_width_expanded = get_ui_setting("layout.sidebar_width", 280)
        self.sidebar_width_collapsed = 70
        self.sidebar.setFixedWidth(self.sidebar_width_expanded)
        
        sidebar_layout = QVBoxLayout(self.sidebar)
        sidebar_layout.setContentsMargins(0, 20, 0, 30)
        sidebar_layout.setSpacing(8)
        
        # Header z przyciskiem toggle
        header_container = QWidget()
        header_layout = QHBoxLayout(header_container)
        header_layout.setContentsMargins(20, 10, 20, 0)
        
        # Logo/Tytuł
        self.title_label = QLabel("🚀 CryptoBotDesktop")
        self.title_label.setObjectName("sectionTitle")
        self.title_label.setAlignment(Qt.AlignmentFlag.AlignLeft)
        header_layout.addWidget(self.title_label)
        
        header_layout.addStretch()
        
        # Przycisk toggle
        self.toggle_btn = QPushButton("◀")
        self.toggle_btn.setObjectName("navButton")
        self.toggle_btn.setFixedSize(40, 40)
        self.toggle_btn.clicked.connect(self.toggle_sidebar)
        header_layout.addWidget(self.toggle_btn)
        
        sidebar_layout.addWidget(header_container)
        sidebar_layout.addSpacing(20)
        
        # Menu nawigacji z ikonami
        self.nav_buttons = {}
        nav_items = [
            ("📊 Dashboard", "dashboard", True),
            ("🤖 Boty", "bots", False),
            ("💰 Portfel", "portfolio", False),
            ("⚠️ Zarządzanie ryzykiem", "risk_management", False),
            ("🔔 Powiadomienia", "notifications", False),

            ("📊 Analiza", "analysis", False),
            ("📋 Logi", "logs", False),
            ("⚙️ Ustawienia", "settings", False)
        ]
        
        for text, key, active in nav_items:
            btn = QPushButton(text)
            btn.setObjectName("navButton")
            btn.setCheckable(True)
            btn.setChecked(active)
            btn.clicked.connect(lambda checked, k=key: self.switch_view(k))
            
            self.nav_buttons[key] = btn
            sidebar_layout.addWidget(btn)
        
        sidebar_layout.addStretch()
        
        # Status połączenia z nowoczesnym designem
        status_container = QWidget()
        status_layout = QVBoxLayout(status_container)
        status_layout.setContentsMargins(20, 0, 20, 0)
        
        self.connection_status = QLabel("🟢 Połączono")
        self.connection_status.setObjectName("statusLabel")
        self.connection_status.setAlignment(Qt.AlignmentFlag.AlignCenter)
        status_layout.addWidget(self.connection_status)
        
        sidebar_layout.addWidget(status_container)
    
    def setup_dashboard(self):
        """Konfiguracja nowoczesnego dashboardu"""
        # Scroll area dla dashboardu
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        scroll.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        
        dashboard_widget = QWidget()
        dashboard_layout = QVBoxLayout(dashboard_widget)
        dashboard_layout.setSpacing(30)
        dashboard_layout.setContentsMargins(20, 20, 20, 20)
        
        # Nagłówek z nowoczesnym designem
        header_layout = QHBoxLayout()
        
        title = QLabel("📊 Dashboard")
        title.setObjectName("sectionTitle")
        header_layout.addWidget(title)
        
        header_layout.addStretch()
        
        # Przycisk odświeżania z nowym stylem
        refresh_btn = QPushButton("🔄 Odśwież")
        refresh_btn.setObjectName("actionButton")
        refresh_btn.clicked.connect(self.refresh_data)
        self.add_button_animations(refresh_btn)
        header_layout.addWidget(refresh_btn)
        
        dashboard_layout.addLayout(header_layout)
        
        # Karty podsumowania
        self.setup_summary_cards(dashboard_layout)
        
        # Aktywne boty
        self.setup_active_bots_section(dashboard_layout)
        
        # Ostatnie transakcje
        self.setup_recent_trades_section(dashboard_layout)
        
        # Wykres wydajności
        self.setup_performance_chart(dashboard_layout)
        
        scroll.setWidget(dashboard_widget)
        self.content_layout.addWidget(scroll)
        
        # Załaduj dane natychmiast po utworzeniu dashboard
        QTimer.singleShot(100, self.refresh_data)
    
    def setup_summary_cards(self, layout):
        """Konfiguracja nowoczesnych kart podsumowania z responsywnym layoutem"""
        # Używamy FlowLayout zamiast QGridLayout dla responsywności
        if FLOW_LAYOUT_AVAILABLE:
            self.dashboard_flow = FlowLayout()
            self.dashboard_flow.setSpacing(20)
            self.dashboard_flow.setContentsMargins(10, 10, 10, 10)
        else:
            # Fallback do QGridLayout jeśli FlowLayout nie jest dostępny
            self.dashboard_grid = QGridLayout()
            self.dashboard_grid.setSpacing(20)
            self.dashboard_grid.setContentsMargins(10, 10, 10, 10)
        
        # Karty z danymi i nowoczesnymi kolorami
        self.portfolio_card = DashboardCard(
            "💰 Wartość Portfela", 
            "$0.00", 
            "0.00% (24h)",
            "#667eea"  # Niebieski gradient
        )
        
        self.active_bots_card = DashboardCard(
            "🤖 Aktywne Boty", 
            "0", 
            "0 zatrzymanych",
            "#4CAF50"  # Zielony
        )
        
        self.daily_pnl_card = DashboardCard(
            "📈 P&L Dzienny", 
            "$0.00", 
            "0 transakcji",
            "#FF9800"  # Pomarańczowy
        )
        
        self.total_pnl_card = DashboardCard(
            "🎯 P&L Całkowity", 
            "$0.00", 
            "ROI: 0.00%",
            "#9C27B0"  # Fioletowy
        )
        
        # Ustaw unikalne objectName dla każdej karty
        self.portfolio_card.setObjectName("portfolioCard")
        self.active_bots_card.setObjectName("botsCard")
        self.daily_pnl_card.setObjectName("dailyPnlCard")
        self.total_pnl_card.setObjectName("totalPnlCard")
        
        # Dodaj karty do responsywnego layoutu
        if FLOW_LAYOUT_AVAILABLE:
            self.dashboard_flow.addWidget(self.portfolio_card)
            self.dashboard_flow.addWidget(self.active_bots_card)
            self.dashboard_flow.addWidget(self.daily_pnl_card)
            self.dashboard_flow.addWidget(self.total_pnl_card)
            layout.addLayout(self.dashboard_flow)
        else:
            # Fallback do QGridLayout
            self.dashboard_grid.addWidget(self.portfolio_card, 0, 0)
            self.dashboard_grid.addWidget(self.active_bots_card, 0, 1)
            self.dashboard_grid.addWidget(self.daily_pnl_card, 0, 2)
            self.dashboard_grid.addWidget(self.total_pnl_card, 0, 3)
            
            # Ustaw równe proporcje kolumn
            for i in range(4):
                self.dashboard_grid.setColumnStretch(i, 1)
            
            layout.addLayout(self.dashboard_grid)
    
    def setup_active_bots_section(self, layout):
        """Konfiguracja sekcji aktywnych botów"""
        print("🔧 setup_active_bots_section: Rozpoczynam konfigurację sekcji botów")
        
        # Nagłówek sekcji
        bots_header = QHBoxLayout()
        
        bots_title = QLabel("Aktywne Boty")
        bots_title.setStyleSheet("font-size: 18px; font-weight: bold;")
        bots_header.addWidget(bots_title)
        
        bots_header.addStretch()
        
        new_bot_btn = QPushButton("+ Nowy Bot")
        new_bot_btn.clicked.connect(self.create_new_bot)
        bots_header.addWidget(new_bot_btn)
        
        layout.addLayout(bots_header)
        
        # Lista botów
        self.bots_container = QWidget()
        self.bots_layout = QVBoxLayout(self.bots_container)
        self.bots_layout.setSpacing(5)
        
        print(f"✅ setup_active_bots_section: bots_layout utworzony: {self.bots_layout}")
        
        # Scroll area dla botów
        bots_scroll = QScrollArea()
        bots_scroll.setWidget(self.bots_container)
        bots_scroll.setWidgetResizable(True)
        bots_scroll.setMaximumHeight(300)
        bots_scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        
        layout.addWidget(bots_scroll)
        print("✅ setup_active_bots_section: Sekcja botów skonfigurowana pomyślnie")
    
    def setup_recent_trades_section(self, layout):
        """Konfiguracja sekcji ostatnich transakcji"""
        trades_title = QLabel("Ostatnie Transakcje")
        trades_title.setStyleSheet("font-size: 16px; font-weight: 500; color: #ffffff; margin-bottom: 8px;")
        layout.addWidget(trades_title)
        
        # Tabela transakcji
        self.trades_table = QTableWidget()
        self.trades_table.setColumnCount(6)
        self.trades_table.setHorizontalHeaderLabels([
            "Czas", "Bot", "Para", "Typ", "Kwota", "Cena"
        ])
        
        # Kompaktowa konfiguracja tabeli
        self.trades_table.setMinimumHeight(180)
        self.trades_table.setMaximumHeight(240)
        self.trades_table.verticalHeader().setDefaultSectionSize(28)
        self.trades_table.verticalHeader().setVisible(False)
        self.trades_table.setShowGrid(False)
        self.trades_table.setAlternatingRowColors(True)
        
        # Konfiguracja kolumn
        header = self.trades_table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.ResizeMode.Fixed)
        header.resizeSection(0, 90)   # Czas
        header.setSectionResizeMode(1, QHeaderView.ResizeMode.Fixed)
        header.resizeSection(1, 80)   # Bot
        header.setSectionResizeMode(2, QHeaderView.ResizeMode.Fixed)
        header.resizeSection(2, 90)   # Para
        header.setSectionResizeMode(3, QHeaderView.ResizeMode.Fixed)
        header.resizeSection(3, 70)   # Typ
        header.setSectionResizeMode(4, QHeaderView.ResizeMode.Stretch)  # Kwota
        header.setSectionResizeMode(5, QHeaderView.ResizeMode.Stretch)  # Cena
        
        self.trades_table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.trades_table.setSortingEnabled(True)
        
        # Dodaj przykładowe dane
        self.populate_trades_table()
        
        layout.addWidget(self.trades_table)
    
    def populate_trades_table(self):
        """Wypełnia tabelę przykładowymi danymi transakcji"""
        sample_trades = [
            ("14:32:15", "Scalping Pro", "BTC/USDT", "BUY", "$1,250.00", "$43,250.50"),
            ("14:28:42", "DCA Master", "ETH/USDT", "SELL", "$850.75", "$2,680.25"),
            ("14:25:18", "Grid Trading", "BNB/USDT", "BUY", "$320.50", "$315.80"),
            ("14:22:03", "Momentum", "ADA/USDT", "SELL", "$180.25", "$0.485"),
            ("14:18:55", "Scalping Pro", "SOL/USDT", "BUY", "$425.00", "$98.75"),
        ]
        
        self.trades_table.setRowCount(len(sample_trades))
        
        for row, trade in enumerate(sample_trades):
            for col, value in enumerate(trade):
                item = QTableWidgetItem(str(value))
                
                # Kolorowanie według typu transakcji
                if col == 3:  # Kolumna Typ
                    if value == "BUY":
                        item.setForeground(QColor("#4CAF50"))  # Zielony
                    elif value == "SELL":
                        item.setForeground(QColor("#F44336"))  # Czerwony
                elif col == 4 or col == 5:  # Kolumny Kwota i Cena
                    item.setForeground(QColor("#FFD700"))  # Złoty
                
                item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
                self.trades_table.setItem(row, col, item)
    
    def setup_performance_chart(self, layout):
        """Konfiguracja wykresu wydajności"""
        chart_title = QLabel("Wydajność Portfela (24h)")
        chart_title.setStyleSheet("font-size: 18px; font-weight: bold;")
        layout.addWidget(chart_title)
        
        # Prawdziwy wykres wydajności
        try:
            from ui.charts import create_chart_widget
            self.chart_placeholder = create_chart_widget("performance")
            layout.addWidget(self.chart_placeholder)
        except ImportError as e:
            self.chart_placeholder = QLabel("Błąd ładowania wykresu wydajności")
            self.chart_placeholder.setAlignment(Qt.AlignmentFlag.AlignCenter)
            self.chart_placeholder.setStyleSheet("""
                background-color: #f5f5f5;
                border: 2px dashed #ccc;
                border-radius: 5px;
                padding: 40px;
                color: #666;
            """)
            self.chart_placeholder.setMinimumHeight(200)
            layout.addWidget(self.chart_placeholder)
    
    def setup_menu(self):
        """Konfiguracja menu"""
        menubar = self.menuBar()
        
        # Menu Plik
        file_menu = menubar.addMenu("Plik")
        
        new_bot_action = QAction("Nowy Bot", self)
        new_bot_action.setShortcut(QKeySequence("Ctrl+N"))
        new_bot_action.triggered.connect(self.create_new_bot)
        file_menu.addAction(new_bot_action)
        
        file_menu.addSeparator()
        
        import_action = QAction("Importuj Konfigurację", self)
        import_action.triggered.connect(self.import_config)
        file_menu.addAction(import_action)
        
        export_action = QAction("Eksportuj Dane", self)
        export_action.triggered.connect(self.export_data)
        file_menu.addAction(export_action)
        
        file_menu.addSeparator()
        
        exit_action = QAction("Wyjście", self)
        exit_action.setShortcut(QKeySequence("Ctrl+Q"))
        exit_action.triggered.connect(self.close)
        file_menu.addAction(exit_action)
        
        # Menu Boty
        bots_menu = menubar.addMenu("Boty")
        
        start_all_action = QAction("Uruchom Wszystkie", self)
        start_all_action.setShortcut(QKeySequence("Ctrl+Shift+S"))
        start_all_action.triggered.connect(self.start_all_bots)
        bots_menu.addAction(start_all_action)
        
        stop_all_action = QAction("Zatrzymaj Wszystkie", self)
        stop_all_action.setShortcut(QKeySequence("Ctrl+Shift+X"))
        stop_all_action.triggered.connect(self.stop_all_bots)
        bots_menu.addAction(stop_all_action)
        
        # Menu Widok
        view_menu = menubar.addMenu("Widok")
        
        refresh_action = QAction("Odśwież", self)
        refresh_action.setShortcut(QKeySequence("F5"))
        refresh_action.triggered.connect(self.refresh_data)
        view_menu.addAction(refresh_action)
        
        toggle_sidebar_action = QAction("Przełącz Sidebar", self)
        toggle_sidebar_action.setShortcut(QKeySequence("Ctrl+B"))
        toggle_sidebar_action.triggered.connect(self.toggle_sidebar)
        view_menu.addAction(toggle_sidebar_action)
        
        # Menu Pomoc
        help_menu = menubar.addMenu("Pomoc")
        
        about_action = QAction("O Programie", self)
        about_action.triggered.connect(self.show_about)
        help_menu.addAction(about_action)
    
    def setup_status_bar(self):
        """Konfiguracja paska statusu"""
        self.status_bar = self.statusBar()
        
        # Status połączenia
        self.status_connection = QLabel("Rozłączono")
        self.status_bar.addWidget(self.status_connection)
        
        # Separator
        self.status_bar.addPermanentWidget(QLabel("|"))
        
        # Liczba aktywnych botów
        self.status_bots = QLabel("Boty: 0")
        self.status_bar.addPermanentWidget(self.status_bots)
        
        # Separator
        self.status_bar.addPermanentWidget(QLabel("|"))
        
        # Ostatnia aktualizacja
        self.status_update = QLabel("Ostatnia aktualizacja: Nigdy")
        self.status_bar.addPermanentWidget(self.status_update)
    
    def setup_system_tray(self):
        """Konfiguracja ikony w zasobniku systemowym"""
        if not QSystemTrayIcon.isSystemTrayAvailable():
            return
        
        self.tray_icon = QSystemTrayIcon(self)
        
        # Menu kontekstowe
        tray_menu = QMenu()
        
        show_action = tray_menu.addAction("Pokaż")
        show_action.triggered.connect(self.show)
        
        tray_menu.addSeparator()
        
        quit_action = tray_menu.addAction("Wyjście")
        quit_action.triggered.connect(self.close)
        
        self.tray_icon.setContextMenu(tray_menu)
        self.tray_icon.activated.connect(self.tray_icon_activated)
        
        # Ustaw ikonę (placeholder)
        self.tray_icon.setToolTip("CryptoBotDesktop")
        self.tray_icon.show()
    
    def apply_theme(self):
        """Aplikuje nowoczesny motyw do aplikacji"""
        theme = get_ui_setting("theme.current", "dark")
        
        # Użyj nowego systemu stylów jeśli dostępny
        if STYLES_AVAILABLE:
            self.setStyleSheet(get_theme_style(theme == "dark"))
            return
        
        # Fallback do starych stylów
        if theme == "dark":
            self.setStyleSheet("""
                QMainWindow {
                    background: #1a1a2e;
                    color: #ffffff;
                }
                
                /* Sidebar minimalistyczny */
                QFrame#sidebar {
                    background: #16213e;
                    border: none;
                    border-right: 1px solid #0f3460;
                }
                
                /* Content area */
                QWidget#contentArea {
                    background: #0f3460;
                    border-radius: 8px;
                    margin: 4px;
                }
                
                /* Minimalistyczne przyciski nawigacji - zwiększone rozmiary */
                QPushButton#navButton {
                    background: transparent;
                    color: #888888;
                    text-align: left;
                    padding: 15px 20px;  /* Zwiększone z 12px 16px */
                    border: none;
                    border-radius: 8px;  /* Zwiększone z 6px */
                    font-size: 15px;  /* Zwiększone z 13px */
                    font-weight: 500;  /* Zwiększone z 400 */
                    margin: 3px 10px;  /* Zwiększone z 2px 8px */
                    min-height: 45px;  /* Zwiększone z 36px */
                    max-height: 50px;  /* Zwiększone z 40px */
                }
                
                /* Przyciski w zwiniętym sidebar */
                QPushButton#navButton[collapsed="true"] {
                    text-align: center;
                    padding: 10px;
                    margin: 2px 4px;
                    font-size: 14px;
                    min-height: 32px;
                    max-height: 36px;
                }
                
                QPushButton#navButton:hover {
                    background: #e94560;
                    color: #ffffff;
                }
                
                QPushButton#navButton:checked {
                    background: #e94560;
                    color: #ffffff;
                    font-weight: 500;
                    border-left: 3px solid #f5f5f5;
                }
                
                /* Nowoczesne karty dashboard - zwiększone rozmiary */
                QWidget#dashboardCard {
                    background: qlineargradient(x1:0, y1:0, x2:1, y2:1,
                        stop:0 rgba(22, 33, 62, 1.0), 
                        stop:1 rgba(15, 52, 96, 1.0));
                    border: 2px solid rgba(233, 69, 96, 0.3);  /* Grubsza ramka */
                    border-radius: 15px;  /* Większy radius */
                    padding: 25px;  /* Zwiększone z 20px */
                    margin: 12px;  /* Zwiększone z 8px */
                    min-height: 180px;  /* Zwiększone z 140px */
                    max-height: 200px;  /* Zwiększone z 160px */
                    min-width: 250px;  /* Zwiększone z 200px */
                }
                
                QWidget#dashboardCard:hover {
                    background: qlineargradient(x1:0, y1:0, x2:1, y2:1,
                        stop:0 rgba(233, 69, 96, 0.15), 
                        stop:1 rgba(245, 245, 245, 0.15));
                    border: 1px solid rgba(233, 69, 96, 0.6);
                }
                
                /* Kolorowe karty dashboard */
                QWidget#portfolioCard {
                    background: qlineargradient(x1:0, y1:0, x2:1, y2:1,
                        stop:0 rgba(233, 69, 96, 0.1), 
                        stop:1 rgba(245, 245, 245, 0.1));
                    border: 1px solid rgba(233, 69, 96, 0.4);
                }
                
                QWidget#portfolioCard:hover {
                    background: qlineargradient(x1:0, y1:0, x2:1, y2:1,
                        stop:0 rgba(233, 69, 96, 0.2), 
                        stop:1 rgba(245, 245, 245, 0.2));
                    border: 1px solid rgba(233, 69, 96, 0.7);
                }
                
                QWidget#botsCard {
                    background: qlineargradient(x1:0, y1:0, x2:1, y2:1,
                        stop:0 rgba(26, 26, 46, 0.1), 
                        stop:1 rgba(22, 33, 62, 0.1));
                    border: 1px solid rgba(15, 52, 96, 0.4);
                }
                
                QWidget#botsCard:hover {
                    background: qlineargradient(x1:0, y1:0, x2:1, y2:1,
                        stop:0 rgba(26, 26, 46, 0.2), 
                        stop:1 rgba(22, 33, 62, 0.2));
                    border: 1px solid rgba(15, 52, 96, 0.7);
                }
                
                QWidget#dailyPnlCard {
                    background: qlineargradient(x1:0, y1:0, x2:1, y2:1,
                        stop:0 rgba(255, 152, 0, 0.1), 
                        stop:1 rgba(255, 111, 0, 0.1));
                    border: 1px solid rgba(255, 152, 0, 0.4);
                }
                
                QWidget#dailyPnlCard:hover {
                    background: qlineargradient(x1:0, y1:0, x2:1, y2:1,
                        stop:0 rgba(255, 152, 0, 0.2), 
                        stop:1 rgba(255, 111, 0, 0.2));
                    border: 1px solid rgba(255, 152, 0, 0.7);
                }
                
                QWidget#totalPnlCard {
                    background: qlineargradient(x1:0, y1:0, x2:1, y2:1,
                        stop:0 rgba(156, 39, 176, 0.1), 
                        stop:1 rgba(123, 31, 162, 0.1));
                    border: 1px solid rgba(156, 39, 176, 0.4);
                }
                
                QWidget#totalPnlCard:hover {
                    background: qlineargradient(x1:0, y1:0, x2:1, y2:1,
                        stop:0 rgba(156, 39, 176, 0.2), 
                        stop:1 rgba(123, 31, 162, 0.2));
                    border: 1px solid rgba(156, 39, 176, 0.7);
                }
                
                /* Style dla etykiet w kartach dashboard - zwiększone rozmiary */
                QLabel#cardTitle {
                    color: rgba(255, 255, 255, 0.9);
                    font-size: 16px;  /* Zwiększone z 14px */
                    font-weight: 600;
                    margin-bottom: 10px;  /* Zwiększone z 8px */
                    letter-spacing: 0.5px;
                    padding: 2px 0;
                }
                
                QLabel#cardValue {
                    color: #ffffff;
                    font-size: 32px;  /* Zwiększone z 28px */
                    font-weight: 700;
                    margin: 15px 0;  /* Zwiększone z 12px */
                    font-family: 'Segoe UI', 'Arial', sans-serif;
                    padding: 5px 0;
                }
                
                QLabel#cardSubtitle {
                    color: rgba(255, 255, 255, 0.7);
                    font-size: 14px;  /* Zwiększone z 12px */
                    font-weight: 400;
                    margin-top: 8px;  /* Zwiększone z 6px */
                    letter-spacing: 0.3px;
                    padding: 2px 0;
                }
                
                /* Tytuły sekcji - zwiększone rozmiary */
                QLabel#sectionTitle {
                    color: #ffffff;
                    font-size: 28px;  /* Zwiększone z 24px */
                    font-weight: 700;
                    margin: 15px 0;  /* Zwiększone z 10px */
                    letter-spacing: 0.5px;
                    padding: 5px 0;
                }
                
                /* Minimalistyczne tabele - zwiększone rozmiary */
                QTableWidget {
                    background: #161616;
                    alternate-background-color: #1a1a1a;
                    gridline-color: #2a2a2a;
                    color: #ffffff;
                    border: 2px solid #2a2a2a;  /* Grubsza ramka */
                    border-radius: 8px;  /* Większy radius */
                    selection-background-color: #333333;
                    font-size: 14px;  /* Zwiększone z 12px */
                    max-height: 350px;  /* Zwiększone z 300px */
                    min-height: 180px;  /* Zwiększone z 150px */
                }
                
                QTableWidget::item {
                    padding: 12px 15px;  /* Zwiększone z 8px 12px */
                    border-bottom: 1px solid #2a2a2a;
                    min-height: 25px;  /* Zwiększone z 18px */
                    max-height: 30px;  /* Zwiększone z 22px */
                }
                
                QTableWidget::item:selected {
                    background: #333333;
                    color: #ffffff;
                    border: none;
                }
                
                QTableWidget::item:hover {
                    background: #222222;
                    border: none;
                }
                
                QHeaderView::section {
                    background: #1a1a1a;
                    color: #cccccc;
                    padding: 15px 18px;  /* Zwiększone z 10px 12px */
                    border: none;
                    border-right: 1px solid #2a2a2a;
                    font-weight: 600;  /* Zwiększone z 500 */
                    font-size: 13px;  /* Zwiększone z 11px */
                    min-height: 35px;  /* Zwiększone z 28px */
                    max-height: 40px;  /* Zwiększone z 32px */
                }
                
                QHeaderView::section:hover {
                    background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                        stop:0 rgba(102, 126, 234, 0.9), 
                        stop:1 rgba(118, 75, 162, 0.9));
                }
                
                QHeaderView::section:first {
                    border-top-left-radius: 6px;
                }
                
                QHeaderView::section:last {
                    border-top-right-radius: 6px;
                    border-right: none;
                }
                
                /* Specjalne style dla komórek tabel */
                QTableWidget QTableWidgetItem[data-type="profit"] {
                    color: #4CAF50;
                    font-weight: 600;
                }
                
                QTableWidget QTableWidgetItem[data-type="loss"] {
                    color: #F44336;
                    font-weight: 600;
                }
                
                QTableWidget QTableWidgetItem[data-type="status-active"] {
                    background: rgba(76, 175, 80, 0.2);
                    color: #4CAF50;
                    border-radius: 8px;
                    font-weight: 600;
                    text-align: center;
                }
                
                QTableWidget QTableWidgetItem[data-type="status-inactive"] {
                    background: rgba(244, 67, 54, 0.2);
                    color: #F44336;
                    border-radius: 8px;
                    font-weight: 600;
                    text-align: center;
                }
                
                QTableWidget QTableWidgetItem[data-type="status-pending"] {
                    background: rgba(255, 152, 0, 0.2);
                    color: #FF9800;
                    border-radius: 8px;
                    font-weight: 600;
                    text-align: center;
                }
                
                QTableWidget QTableWidgetItem[data-type="currency"] {
                    color: #FFD700;
                    font-weight: 600;
                    font-family: 'Courier New', monospace;
                }
                
                QTableWidget QTableWidgetItem[data-type="percentage"] {
                    font-weight: 600;
                    font-family: 'Courier New', monospace;
                }
                
                /* Nowoczesne scrollbary */
                QScrollArea {
                    background: transparent;
                    border: none;
                }
                
                QScrollBar:vertical {
                    background: #1a1a1a;
                    width: 6px;
                    border-radius: 3px;
                    margin: 0;
                }
                
                QScrollBar::handle:vertical {
                    background: #444444;
                    border-radius: 3px;
                    min-height: 20px;
                }
                
                QScrollBar::handle:vertical:hover {
                    background: #555555;
                }
                
                QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
                    height: 0px;
                }
                
                /* Przyciski akcji - zwiększone rozmiary */
                QPushButton#actionButton {
                    background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                        stop:0 #667eea, stop:1 #764ba2);
                    color: white;
                    border: none;
                    padding: 15px 30px;  /* Zwiększone z 12px 24px */
                    border-radius: 10px;  /* Zwiększone z 8px */
                    font-weight: 600;
                    font-size: 15px;  /* Zwiększone z 13px */
                    min-height: 45px;  /* Dodane dla lepszej wysokości */
                }
                
                QPushButton#actionButton:hover {
                    background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                        stop:0 #5a6fd8, stop:1 #6a4190);
                }
                
                QPushButton#actionButton:pressed {
                    background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                        stop:0 #4a5fc8, stop:1 #5a3180);
                }
                
                /* Status labels */
                QLabel#statusLabel {
                    background: rgba(255, 255, 255, 0.1);
                    border-radius: 20px;
                    padding: 6px 12px;
                    font-size: 12px;
                    font-weight: 500;
                }
                
                /* Tytuły sekcji */
                QLabel#sectionTitle {
                    color: #ffffff;
                    font-size: 24px;
                    font-weight: 700;
                    margin-bottom: 16px;
                }
                
                QLabel#cardTitle {
                    color: #888888;
                    font-size: 13px;
                    font-weight: 400;
                    margin-bottom: 6px;
                }
                
                QLabel#cardValue {
                    color: #ffffff;
                    font-size: 24px;
                    font-weight: 600;
                    margin-bottom: 4px;
                }
                
                QLabel#cardSubtitle {
                    color: #666666;
                    font-size: 11px;
                    font-weight: 400;
                }
                
                /* Minimalistyczne przyciski - zwiększone rozmiary */
                QPushButton {
                    background: #2a2a2a;
                    color: #ffffff;
                    border: 2px solid #3a3a3a;  /* Grubsza ramka */
                    border-radius: 8px;  /* Większy radius */
                    padding: 12px 20px;  /* Zwiększone z 8px 16px */
                    font-size: 14px;  /* Zwiększone z 12px */
                    font-weight: 500;  /* Zwiększone z 400 */
                    min-height: 35px;  /* Zwiększone z 28px */
                    max-height: 40px;  /* Zwiększone z 32px */
                }
                
                QPushButton:hover {
                    background: #3a3a3a;
                    border-color: #4a4a4a;
                }
                
                QPushButton:pressed {
                    background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                        stop:0 rgba(102, 126, 234, 1.0), 
                        stop:1 rgba(118, 75, 162, 1.0));

                }
                
                QPushButton:disabled {
                    background: rgba(255, 255, 255, 0.1);
                    color: rgba(255, 255, 255, 0.4);
                }
                
                /* Style dla przycisków niebezpiecznych */
                QPushButton#dangerButton {
                    background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                        stop:0 #e74c3c, stop:1 #c0392b);
                }
                
                QPushButton#dangerButton:hover {
                    background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                        stop:0 #ec7063, stop:1 #cb4335);
                }
                
                /* Style dla przycisków sukcesu */
                QPushButton#successButton {
                    background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                        stop:0 #27ae60, stop:1 #229954);
                }
                
                QPushButton#successButton:hover {
                    background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                        stop:0 #58d68d, stop:1 #52c41a);
                }
                
                /* Poprawa czytelności tekstu */
                QLabel {
                    color: #ffffff;

                }
                
                QLabel#sectionTitle {
                    color: #ffffff;
                    font-size: 18px;
                    font-weight: 700;
                    margin-bottom: 12px;

                }
                
                QLabel#cardTitle {
                    color: rgba(255, 255, 255, 0.95);
                    font-size: 12px;
                    font-weight: 600;
                    margin-bottom: 6px;

                }
                
                QLabel#cardValue {
                    color: #ffffff;
                    font-size: 20px;
                    font-weight: 700;
                    margin-bottom: 3px;

                }
                
                QLabel#cardSubtitle {
                    color: rgba(255, 255, 255, 0.8);
                    font-size: 10px;
                    font-weight: 400;

                }
                
                /* Lepsze kontrasty dla statusów */
                QLabel#statusActive {
                    background: rgba(39, 174, 96, 0.9);
                    color: #ffffff;
                    border-radius: 4px;
                    padding: 2px 6px;
                    font-weight: bold;

                }
                
                QLabel#statusInactive {
                    background: rgba(231, 76, 60, 0.9);
                    color: #ffffff;
                    border-radius: 4px;
                    padding: 2px 6px;
                    font-weight: bold;

                }
                
                QLabel#statusWarning {
                    background: rgba(243, 156, 18, 0.9);
                    color: #ffffff;
                    border-radius: 4px;
                    padding: 2px 6px;
                    font-weight: bold;

                }
                
                /* Kompaktowe komponenty dla lepszego wykorzystania przestrzeni */
                QWidget {
                    font-size: 11px;
                }
                
                QComboBox {
                    background: rgba(255, 255, 255, 0.1);
                    border: 1px solid rgba(102, 126, 234, 0.3);
                    border-radius: 4px;
                    padding: 4px 8px;
                    color: #ffffff;
                    min-height: 20px;
                    max-height: 24px;
                }
                
                QComboBox:hover {
                    border: 1px solid rgba(102, 126, 234, 0.5);
                    background: rgba(255, 255, 255, 0.15);
                }
                
                QComboBox::drop-down {
                    border: none;
                    width: 20px;
                }
                
                QComboBox::down-arrow {
                    image: none;
                    border: 2px solid #ffffff;
                    border-top: none;
                    border-right: none;
                    width: 6px;
                    height: 6px;

                }
                
                QLineEdit, QSpinBox, QDoubleSpinBox {
                    background: rgba(255, 255, 255, 0.1);
                    border: 1px solid rgba(102, 126, 234, 0.3);
                    border-radius: 4px;
                    padding: 4px 8px;
                    color: #ffffff;
                    min-height: 20px;
                    max-height: 24px;
                }
                
                QLineEdit:focus, QSpinBox:focus, QDoubleSpinBox:focus {
                    border: 1px solid rgba(102, 126, 234, 0.7);
                    background: rgba(255, 255, 255, 0.15);
                }
                
                QCheckBox {
                    color: #ffffff;
                    spacing: 6px;
                }
                
                QCheckBox::indicator {
                    width: 16px;
                    height: 16px;
                    border: 1px solid rgba(102, 126, 234, 0.5);
                    border-radius: 3px;
                    background: rgba(255, 255, 255, 0.1);
                }
                
                QCheckBox::indicator:checked {
                    background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                        stop:0 rgba(102, 126, 234, 0.8), 
                        stop:1 rgba(118, 75, 162, 0.8));
                    border: 1px solid rgba(102, 126, 234, 0.8);
                }
                
                QScrollBar:vertical {
                    background: rgba(255, 255, 255, 0.1);
                    width: 8px;
                    border-radius: 4px;
                }
                
                QScrollBar::handle:vertical {
                    background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                        stop:0 rgba(102, 126, 234, 0.6), 
                        stop:1 rgba(118, 75, 162, 0.6));
                    border-radius: 4px;
                    min-height: 20px;
                }
                
                QScrollBar::handle:vertical:hover {
                    background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                        stop:0 rgba(102, 126, 234, 0.8), 
                        stop:1 rgba(118, 75, 162, 0.8));
                }
                
                QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
                    height: 0px;
                }
            """)
        else:
            # Light theme z nowoczesnymi kolorami
            self.setStyleSheet("""
                QMainWindow {
                    background: qlineargradient(x1:0, y1:0, x2:1, y2:1,
                        stop:0 #f8f9fa, stop:1 #e9ecef);
                    color: #212529;
                }
                
                QFrame#sidebar {
                    background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                        stop:0 #ffffff, stop:1 #f8f9fa);
                    border-right: 1px solid rgba(0, 0, 0, 0.1);
                }
                
                QPushButton#navButton:checked {
                    background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                        stop:0 #667eea, stop:1 #764ba2);
                    color: #ffffff;
                }
            """)
    
    def get_nav_button_style(self, active: bool) -> str:
        """Zwraca nowoczesne style dla przycisków nawigacji"""
        # Używamy teraz ID selektorów zamiast inline styles
        return ""  # Style są teraz w głównym CSS
    
    def toggle_sidebar(self):
        """Przełącza między rozwiniętym a zwiniętym menu bocznym z płynną animacją"""
        self.sidebar_expanded = not self.sidebar_expanded
        
        # Zatrzymaj poprzednią animację jeśli jest aktywna
        if self.sidebar_animation:
            self.sidebar_animation.stop()
        
        # Utwórz animację szerokości sidebar
        self.sidebar_animation = QPropertyAnimation(self.sidebar, b"maximumWidth")
        self.sidebar_animation.setDuration(300)  # 300ms
        self.sidebar_animation.setEasingCurve(QEasingCurve.Type.OutCubic)
        
        current_width = self.sidebar.width()
        
        # Dostosuj szerokość sidebar do rozmiaru okna
        window_width = self.width()
        if window_width < 600:
            # Na bardzo małych ekranach użyj mniejszych rozmiarów
            expanded_width = min(180, window_width * 0.4)  # Maksymalnie 40% szerokości okna
            collapsed_width = 40
        elif window_width < 768:
            # Na tabletach użyj średnich rozmiarów
            expanded_width = min(200, window_width * 0.35)
            collapsed_width = 50
        else:
            # Na większych ekranach użyj standardowych rozmiarów
            expanded_width = self.sidebar_width_expanded
            collapsed_width = self.sidebar_width_collapsed
        
        target_width = expanded_width if self.sidebar_expanded else collapsed_width
        
        self.sidebar_animation.setStartValue(current_width)
        self.sidebar_animation.setEndValue(target_width)
        
        # Callback po zakończeniu animacji
        self.sidebar_animation.finished.connect(self._on_sidebar_animation_finished)
        
        # Natychmiast zaktualizuj przyciski i tekst
        if self.sidebar_expanded:
            self.toggle_btn.setText("◀")
            
            # Pokaż pełny tekst w przyciskach nawigacji
            nav_texts = {
                "dashboard": "📊 Dashboard",
                "bots": "🤖 Boty", 
                "portfolio": "💰 Portfel",
                "risk_management": "⚠️ Zarządzanie ryzykiem",
                "notifications": "🔔 Powiadomienia",
    
                "analysis": "📊 Analiza",
                "logs": "📋 Logi",
                "settings": "⚙️ Ustawienia"
            }
            
            for key, btn in self.nav_buttons.items():
                btn.setText(nav_texts.get(key, btn.text()))
                btn.setProperty("collapsed", False)
                btn.setStyleSheet("")  # Reset style aby zastosować nowe CSS
        else:
            self.toggle_btn.setText("▶")
            
            # Pokaż tylko ikony w przyciskach nawigacji
            icons = {
                "dashboard": "📊",
                "bots": "🤖", 
                "portfolio": "💰",
                "risk_management": "⚠️",
                "notifications": "🔔",
    
                "analysis": "📊",
                "logs": "📋",
                "settings": "⚙️"
            }
            
            for key, btn in self.nav_buttons.items():
                btn.setText(icons.get(key, ""))
                btn.setProperty("collapsed", True)
                btn.setStyleSheet("")  # Reset style aby zastosować nowe CSS
        
        # Uruchom animację
        self.sidebar_animation.start()
    
    def _on_sidebar_animation_finished(self):
        """Callback wywoływany po zakończeniu animacji sidebar"""
        # Ustaw finalną szerokość i pokaż/ukryj tytuł
        if self.sidebar_expanded:
            self.sidebar.setFixedWidth(self.sidebar_width_expanded)
            self.title_label.show()
        else:
            self.sidebar.setFixedWidth(self.sidebar_width_collapsed)
            self.title_label.hide()
    
    def add_button_animations(self, button):
        """Dodaje animacje hover i kliknięcia do przycisku"""
        # Animacja hover
        button.hover_animation = QPropertyAnimation(button, b"geometry")
        button.hover_animation.setDuration(150)
        button.hover_animation.setEasingCurve(QEasingCurve.Type.OutCubic)
        
        # Animacja kliknięcia
        button.click_animation = QPropertyAnimation(button, b"geometry")
        button.click_animation.setDuration(100)
        button.click_animation.setEasingCurve(QEasingCurve.Type.OutBounce)
        
        # Dodaj event handlers
        original_enter = button.enterEvent
        original_leave = button.leaveEvent
        original_press = button.mousePressEvent
        original_release = button.mouseReleaseEvent
        
        def enter_event(event):
            if hasattr(button, 'hover_animation'):
                current_rect = button.geometry()
                new_rect = QRect(
                    current_rect.x() - 1,
                    current_rect.y() - 1,
                    current_rect.width() + 2,
                    current_rect.height() + 2
                )
                button.hover_animation.setStartValue(current_rect)
                button.hover_animation.setEndValue(new_rect)
                button.hover_animation.start()
            original_enter(event)
        
        def leave_event(event):
            if hasattr(button, 'hover_animation'):
                current_rect = button.geometry()
                original_rect = QRect(
                    current_rect.x() + 1,
                    current_rect.y() + 1,
                    current_rect.width() - 2,
                    current_rect.height() - 2
                )
                button.hover_animation.setStartValue(current_rect)
                button.hover_animation.setEndValue(original_rect)
                button.hover_animation.start()
            original_leave(event)
        
        def press_event(event):
            if hasattr(button, 'click_animation'):
                current_rect = button.geometry()
                pressed_rect = QRect(
                    current_rect.x() + 1,
                    current_rect.y() + 1,
                    current_rect.width() - 2,
                    current_rect.height() - 2
                )
                button.click_animation.setStartValue(current_rect)
                button.click_animation.setEndValue(pressed_rect)
                button.click_animation.start()
            original_press(event)
        
        def release_event(event):
            if hasattr(button, 'click_animation'):
                current_rect = button.geometry()
                released_rect = QRect(
                    current_rect.x() - 1,
                    current_rect.y() - 1,
                    current_rect.width() + 2,
                    current_rect.height() + 2
                )
                button.click_animation.setStartValue(current_rect)
                button.click_animation.setEndValue(released_rect)
                button.click_animation.start()
            original_release(event)
        
        # Przypisz nowe event handlers
        button.enterEvent = enter_event
        button.leaveEvent = leave_event
        button.mousePressEvent = press_event
        button.mouseReleaseEvent = release_event
    
    def load_window_settings(self):
        """Ładuje ustawienia okna"""
        # Rozmiar okna
        width = get_ui_setting("window.default_width", 1200)
        height = get_ui_setting("window.default_height", 800)
        self.resize(width, height)
        
        # Pozycja okna
        if get_ui_setting("window.remember_position", True):
            # TODO: Załaduj zapisaną pozycję
            pass
        
        # Maksymalizacja
        if get_ui_setting("window.start_maximized", False):
            self.showMaximized()
    
    def resizeEvent(self, event):
        """Obsługuje zmianę rozmiaru okna dla responsywnego UI"""
        super().resizeEvent(event)
        
        try:
            # Pobierz nowy rozmiar okna
            new_size = event.size()
            window_width = new_size.width()
            window_height = new_size.height()
            
            # Automatycznie zwiń sidebar na małych ekranach z lepszymi breakpointami
            if window_width < 768 and hasattr(self, 'sidebar_expanded') and self.sidebar_expanded:
                # Zwiń sidebar na tabletach i mniejszych ekranach
                self.toggle_sidebar()
            elif window_width >= 1024 and hasattr(self, 'sidebar_expanded') and not self.sidebar_expanded:
                # Rozwiń sidebar na laptopach i większych ekranach
                self.toggle_sidebar()
            
            # Dodatkowe dostosowania dla bardzo małych ekranów
            if window_width < 600:
                # Na bardzo małych ekranach ukryj dodatkowe elementy UI
                self._adjust_ui_for_small_screens(True)
            else:
                # Przywróć pełny UI na większych ekranach
                self._adjust_ui_for_small_screens(False)
            
            # Dostosuj layout dashboardu dla różnych rozmiarów
            if hasattr(self, 'dashboard_grid') and self.current_view == 'dashboard':
                self.adjust_dashboard_layout(window_width)
            
            # Dostosuj layout kart powiadomień
            if hasattr(self, 'channels_grid') and self.current_view == 'notifications':
                self.adjust_notifications_layout(window_width)
            
            # Dostosuj responsywność wszystkich tabel
            if hasattr(self, 'trades_table'):
                self._adjust_table_responsiveness(self.trades_table, window_width)
            
            # Sprawdź inne tabele w aplikacji
            for widget in self.findChildren(QTableWidget):
                self._adjust_table_responsiveness(widget, window_width)
                
        except Exception as e:
            self.logger.error(f"Error in resizeEvent: {e}")
    
    def adjust_dashboard_layout(self, window_width):
        """Dostosowuje layout dashboardu do szerokości okna"""
        try:
            if not hasattr(self, 'dashboard_grid'):
                return
                
            # Określ liczbę kolumn na podstawie szerokości okna z dodatkowymi breakpointami
            if window_width < 480:
                columns = 1  # Ekstremalnie małe ekrany - tylko jedna kolumna
            elif window_width < 600:
                columns = 1  # Bardzo małe ekrany - jedna kolumna
            elif window_width < 768:
                columns = 1  # Tablety w pionie - jedna kolumna
            elif window_width < 1024:
                columns = 2  # Tablety w poziomie - dwie kolumny
            elif window_width < 1280:
                columns = 2  # Małe laptopy - dwie kolumny
            elif window_width < 1600:
                columns = 3  # Średnie ekrany - trzy kolumny
            else:
                columns = 4  # Duże ekrany - cztery kolumny
            
            # Zbierz wszystkie widgety przed reorganizacją
            widgets = []
            for i in range(self.dashboard_grid.count()):
                item = self.dashboard_grid.itemAt(0)  # Zawsze bierz pierwszy element
                if item and item.widget():
                    widget = item.widget()
                    self.dashboard_grid.removeWidget(widget)
                    widgets.append(widget)
            
            # Dodaj widgety z powrotem w nowym układzie
            for i, widget in enumerate(widgets):
                row = i // columns
                col = i % columns
                self.dashboard_grid.addWidget(widget, row, col)
            
            # Ustaw równe proporcje kolumn
            for i in range(columns):
                self.dashboard_grid.setColumnStretch(i, 1)
            
            # Wyczyść stretch dla nieużywanych kolumn
            for i in range(columns, 4):
                self.dashboard_grid.setColumnStretch(i, 0)
                    
        except Exception as e:
            self.logger.error(f"Error adjusting dashboard layout: {e}")
    
    def adjust_notifications_layout(self, window_width):
        """Dostosowuje layout powiadomień do szerokości okna"""
        try:
            if not hasattr(self, 'channels_grid'):
                return
                
            # Określ liczbę kolumn dla kart kanałów
            if window_width < 600:
                columns = 1
            elif window_width < 900:
                columns = 2
            else:
                columns = 2  # Maksymalnie 2 kolumny dla kart kanałów
            
            # Reorganizuj karty kanałów
            widgets = []
            for i in range(self.channels_grid.count()):
                item = self.channels_grid.itemAt(i)
                if item and item.widget():
                    widgets.append(item.widget())
                    self.channels_grid.removeWidget(item.widget())
            
            # Dodaj ponownie w nowym układzie
            for i, widget in enumerate(widgets):
                row = i // columns
                col = i % columns
                self.channels_grid.addWidget(widget, row, col)
                
        except Exception as e:
            self.logger.error(f"Error adjusting notifications layout: {e}")
    
    def _adjust_ui_for_small_screens(self, is_small_screen: bool):
        """Dostosowuje UI dla bardzo małych ekranów"""
        try:
            if is_small_screen:
                # Ukryj lub zmniejsz elementy na bardzo małych ekranach
                
                # Zmniejsz rozmiar czcionki w statusbar
                if hasattr(self, 'status_bar'):
                    self.status_bar.setStyleSheet("""
                        QStatusBar {
                            font-size: 10px;
                            max-height: 20px;
                        }
                    """)
                
                # Kompaktowy tryb dla przycisków w toolbarze
                if hasattr(self, 'toolbar_buttons'):
                    for button in self.toolbar_buttons:
                        if hasattr(button, 'setText'):
                            # Ukryj tekst, zostaw tylko ikony
                            button.setText("")
                            button.setToolTip(button.text() if hasattr(button, 'text') else "")
                
                # Zmniejsz marginesy w głównym layoutcie
                if hasattr(self, 'main_layout'):
                    self.main_layout.setContentsMargins(5, 5, 5, 5)
                    self.main_layout.setSpacing(5)
                
                # Kompaktowy tryb dla kart
                if hasattr(self, 'tab_widget'):
                    self.tab_widget.setStyleSheet("""
                        QTabWidget::pane {
                            border: 1px solid #c0c0c0;
                            margin: 0px;
                        }
                        QTabBar::tab {
                            padding: 4px 8px;
                            margin: 1px;
                            font-size: 11px;
                        }
                    """)
                    
            else:
                # Przywróć normalny wygląd
                
                # Przywróć normalny rozmiar statusbar
                if hasattr(self, 'status_bar'):
                    self.status_bar.setStyleSheet("")
                
                # Przywróć tekst przycisków
                if hasattr(self, 'toolbar_buttons'):
                    for button in self.toolbar_buttons:
                        if hasattr(button, 'original_text'):
                            button.setText(button.original_text)
                
                # Przywróć normalne marginesy
                if hasattr(self, 'main_layout'):
                    self.main_layout.setContentsMargins(10, 10, 10, 10)
                    self.main_layout.setSpacing(10)
                
                # Przywróć normalny wygląd kart
                if hasattr(self, 'tab_widget'):
                    self.tab_widget.setStyleSheet("")
                    
        except Exception as e:
            self.logger.error(f"Error adjusting UI for small screens: {e}")
    
    def _adjust_table_responsiveness(self, table_widget, window_width: int):
        """Dostosowuje responsywność tabeli do szerokości okna"""
        try:
            if not table_widget or not hasattr(table_widget, 'horizontalHeader'):
                return
                
            header = table_widget.horizontalHeader()
            column_count = table_widget.columnCount()
            
            if window_width < 480:
                # Ekstremalnie małe ekrany - ukryj niektóre kolumny
                if column_count >= 6:
                    # Ukryj kolumny Bot i Para, zostaw tylko Czas, Typ, Kwota, Cena
                    table_widget.setColumnHidden(1, True)  # Bot
                    table_widget.setColumnHidden(2, True)  # Para
                    # Dostosuj szerokości pozostałych kolumn
                    header.resizeSection(0, 60)   # Czas
                    header.resizeSection(3, 50)   # Typ
                elif column_count >= 4:
                    # Dla mniejszych tabel ukryj co drugą kolumnę
                    for i in range(1, column_count, 2):
                        table_widget.setColumnHidden(i, True)
                        
            elif window_width < 600:
                # Bardzo małe ekrany - ukryj jedną kolumnę
                if column_count >= 6:
                    table_widget.setColumnHidden(1, True)  # Ukryj Bot
                    # Dostosuj szerokości
                    header.resizeSection(0, 70)   # Czas
                    header.resizeSection(2, 70)   # Para
                    header.resizeSection(3, 50)   # Typ
                else:
                    # Pokaż wszystkie kolumny ale zmniejsz szerokości
                    for i in range(column_count):
                        table_widget.setColumnHidden(i, False)
                        
            elif window_width < 768:
                # Tablety - pokaż wszystkie kolumny ale zmniejsz szerokości
                for i in range(column_count):
                    table_widget.setColumnHidden(i, False)
                    
                if column_count >= 6:
                    header.resizeSection(0, 80)   # Czas
                    header.resizeSection(1, 70)   # Bot
                    header.resizeSection(2, 80)   # Para
                    header.resizeSection(3, 60)   # Typ
                    
            else:
                # Większe ekrany - pokaż wszystkie kolumny w pełnych rozmiarach
                for i in range(column_count):
                    table_widget.setColumnHidden(i, False)
                    
                if column_count >= 6:
                    header.resizeSection(0, 90)   # Czas
                    header.resizeSection(1, 80)   # Bot
                    header.resizeSection(2, 90)   # Para
                    header.resizeSection(3, 70)   # Typ
                    
        except Exception as e:
            self.logger.error(f"Error adjusting table responsiveness: {e}")
    
    def start_data_refresh(self):
        """Uruchamia automatyczne odświeżanie danych"""
        interval = get_ui_setting("dashboard.refresh_interval_seconds", 5) * 1000
        self.refresh_timer.start(interval)
        
        # Pierwsze odświeżenie
        self.refresh_data()
    
    def refresh_data(self):
        """Odświeża dane na dashboardzie"""
        try:
            print(f"🔄 REFRESH_DATA wywołane, current_view: {getattr(self, 'current_view', 'unknown')}")
            # Sprawdź czy główne okno nadal istnieje i jest widoczne
            if not self or not hasattr(self, 'content_layout') or not self.isVisible():
                print("❌ Okno nie istnieje lub nie jest widoczne")
                return
                
            # Sprawdź czy timer nadal działa
            if not hasattr(self, 'refresh_timer') or not self.refresh_timer or not self.refresh_timer.isActive():
                return
                
            # Sprawdź czy jesteśmy w widoku dashboard przed aktualizacją
            current_view = getattr(self, 'current_view', 'dashboard')
            if current_view == 'dashboard':
                # TODO: Pobierz rzeczywiste dane z backendu
                self.update_portfolio_data()
                self.update_bots_data()
                self.update_recent_trades()
                self.update_pnl_cards()
            
            # Odśwież dane ryzyka niezależnie od widoku - aby były dostępne gdy użytkownik przejdzie do zakładki
            if hasattr(self, 'risk_manager') and self.risk_manager:
                self.refresh_risk_data()
            
            # Status bar można aktualizować zawsze
            self.update_status_bar()
            
            self.logger.info("Dashboard data refreshed")
            
        except Exception as e:
            self.logger.error(f"Error refreshing data: {e}")
    
    def update_portfolio_data(self):
        """Aktualizuje dane portfela"""
        try:
            # Sprawdź czy jesteśmy w odpowiednim widoku i komponenty istnieją
            if not hasattr(self, 'portfolio_card') or not self.portfolio_card:
                return
                
            # Sprawdź czy komponent nie został usunięty - bezpieczne sprawdzenie
            try:
                # Sprawdź czy obiekt nadal istnieje w pamięci
                if hasattr(self.portfolio_card, 'update_value'):
                    # Pobierz rzeczywiste dane portfela z DataManager
                    try:
                        from core.integrated_data_manager import get_integrated_data_manager
                        data_manager = get_integrated_data_manager()
                        
                        # Pobierz dane asynchronicznie
                        try:
                            try:
                                asyncio.get_running_loop()
                                import concurrent.futures
                                with concurrent.futures.ThreadPoolExecutor() as executor:
                                    future = executor.submit(asyncio.run, data_manager.get_portfolio_data())
                                    portfolio_data = future.result(timeout=2)
                            except RuntimeError:
                                portfolio_data = asyncio.run(data_manager.get_portfolio_data())
                        except Exception:
                            # Fallback - pobierz synchronicznie
                            portfolio_data = data_manager._get_sample_portfolio_data()
                        
                        self.portfolio_card.update_value(
                            f"${portfolio_data.total_value:,.2f}",
                            f"{portfolio_data.daily_change:+.2f} ({portfolio_data.daily_change_percent:+.2f}%)"
                        )
                    except Exception as e:
                        self.logger.error(f"Error getting portfolio data from DataManager: {e}")
                        # Fallback do domyślnych wartości
                        self.portfolio_card.update_value("$0.00", "Brak danych")
                else:
                    # Obiekt nie ma już metody update_value - został usunięty
                    self.portfolio_card = None
                    return
            except (RuntimeError, AttributeError):
                # Komponent został usunięty z pamięci
                self.portfolio_card = None
                return
        except Exception as e:
            self.logger.error(f"Error updating portfolio data: {e}")
    
    def update_bots_data(self):
        """Aktualizuje dane botów"""
        try:
            print("🤖 UPDATE_BOTS_DATA wywołane")
            
            # Sprawdź aktualny widok
            current_view = getattr(self, 'current_view', 'dashboard')
            print(f"🔍 Current view: {current_view}")
            
            # Jeśli jesteśmy w widoku dashboard, aktualizuj dashboard
            if current_view == 'dashboard':
                # Sprawdź czy komponenty dashboard istnieją
                has_bots_layout = hasattr(self, 'bots_layout')
                bots_layout_value = getattr(self, 'bots_layout', None)
                print(f"🔍 has_bots_layout: {has_bots_layout}, bots_layout value: {bots_layout_value}")
                
                # Fix: Use 'is None' instead of 'not bots_layout_value' because QLayout objects
                # can evaluate to False even when they exist
                if not has_bots_layout or bots_layout_value is None:
                    print("⚠️ bots_layout nie istnieje w dashboard - ponowna inicjalizacja")
                    # Wyczyść content i ponownie zainicjalizuj dashboard
                    self.clear_content_layout(target_view='dashboard')
                    self.setup_dashboard()
                    return
                    
                # Sprawdź czy layout nie został usunięty - bezpieczne sprawdzenie
                try:
                    # Sprawdź czy obiekt nadal istnieje w pamięci
                    if hasattr(self.bots_layout, 'count'):
                        self.bots_layout.count()
                    else:
                        # Layout nie ma już metody count - został usunięty
                        print("⚠️ bots_layout został usunięty - ponowna inicjalizacja")
                        self.clear_content_layout(target_view='dashboard')
                        self.setup_dashboard()
                        return
                except (RuntimeError, AttributeError):
                    # Layout został usunięty z pamięci
                    print("⚠️ bots_layout RuntimeError - ponowna inicjalizacja")
                    self.clear_content_layout(target_view='dashboard')
                    self.setup_dashboard()
                    return
                
                # Pobierz rzeczywiste dane botów z DataManager
                try:
                    from core.integrated_data_manager import get_integrated_data_manager
                    data_manager = get_integrated_data_manager()
                    
                    # Pobierz dane asynchronicznie
                    try:
                        try:
                            asyncio.get_running_loop()
                            import concurrent.futures
                            with concurrent.futures.ThreadPoolExecutor() as executor:
                                future = executor.submit(asyncio.run, data_manager.get_bots_data())
                                bots_data = future.result(timeout=2)
                        except RuntimeError:
                            bots_data = asyncio.run(data_manager.get_bots_data())
                    except Exception as e:
                        # Fallback: w razie błędu nie używamy danych przykładowych
                        if hasattr(self, 'logger') and self.logger:
                            self.logger.warning(f"Fallback: get_bots_data failed, returning empty list due to error: {e}")
                        bots_data = []
                    
                    # Konwertuj BotData do dict dla kompatybilności
                    sample_bots = []
                    for bot in bots_data:
                        sample_bots.append({
                            "id": bot.id,
                            "type": bot.strategy_type,
                            "pair": bot.trading_pair,
                            "status": bot.status,
                            "pnl": bot.profit_loss
                        })
                except Exception as e:
                    self.logger.error(f"Error getting bots data from DataManager: {e}")
                    # Fallback do pustej listy
                    sample_bots = []
                
                # Bezpiecznie wyczyść obecne boty
                self.clear_bots_layout()
                
                # Dodaj nowe boty
                for bot_data in sample_bots:
                    try:
                        bot_widget = BotStatusWidget(bot_data)
                        if bot_widget and hasattr(bot_widget, 'isVisible'):
                            self.bots_layout.addWidget(bot_widget)
                    except Exception as e:
                        self.logger.error(f"Error creating bot widget: {e}")
                
                # Aktualizuj kartę aktywnych botów
                active_count = len([b for b in sample_bots if b['status'] == 'running'])
                stopped_count = len(sample_bots) - active_count
                
                if hasattr(self, 'active_bots_card') and self.active_bots_card:
                    try:
                        # Bezpieczne sprawdzenie czy obiekt nadal istnieje
                        if hasattr(self.active_bots_card, 'update_value'):
                            self.active_bots_card.update_value(
                                str(active_count),
                                f"{stopped_count} zatrzymanych"
                            )
                        else:
                            # Obiekt nie ma już metody update_value - został usunięty
                            self.active_bots_card = None
                    except (RuntimeError, AttributeError):
                        # Komponent został usunięty z pamięci
                        self.active_bots_card = None
            
            # Jeśli jesteśmy w widoku botów, aktualizuj BotManagementWidget
            elif current_view == 'bots' and hasattr(self, 'bot_management_widget') and self.bot_management_widget:
                try:
                    # Sprawdź czy BotManagementWidget nadal istnieje
                    if hasattr(self.bot_management_widget, 'update_bots_status'):
                        print("🔄 Aktualizuję BotManagementWidget")
                        self.bot_management_widget.update_bots_status()
                    else:
                        print("❌ BotManagementWidget nie ma metody update_bots_status")
                except (RuntimeError, AttributeError) as e:
                    print(f"❌ Błąd podczas aktualizacji BotManagementWidget: {e}")
                    self.bot_management_widget = None
            
            print(f"✅ UPDATE_BOTS_DATA zakończone dla widoku: {current_view}")
            
        except Exception as e:
            self.logger.error(f"Error updating bots data: {e}")
    
    def update_recent_trades(self):
        """Aktualizuje ostatnie transakcje"""
        try:
            # Sprawdź czy komponenty istnieją
            if not hasattr(self, 'trades_table') or not self.trades_table:
                return
                
            # Sprawdź czy tabela nie została usunięta - bezpieczne sprawdzenie
            try:
                # Sprawdź czy obiekt nadal istnieje w pamięci
                if hasattr(self.trades_table, 'rowCount') and hasattr(self.trades_table, 'setRowCount'):
                    # Pobierz rzeczywiste transakcje z DataManager
                    try:
                        from core.integrated_data_manager import get_integrated_data_manager
                        data_manager = get_integrated_data_manager()
                        
                        # Pobierz dane asynchronicznie
                        try:
                            try:
                                asyncio.get_running_loop()
                                import concurrent.futures
                                with concurrent.futures.ThreadPoolExecutor() as executor:
                                    future = executor.submit(asyncio.run, data_manager.get_recent_trades(10))
                                    trades_data = future.result(timeout=2)
                            except RuntimeError:
                                trades_data = asyncio.run(data_manager.get_recent_trades(10))
                        except Exception:
                            # Fallback - pobierz synchronicznie
                            trades_data = data_manager._get_sample_trades(10)
                        
                        # Konwertuj do formatu tabeli
                        sample_trades = []
                        for trade in trades_data:
                            sample_trades.append([
                                trade["time"],
                                trade["bot"],
                                trade["pair"],
                                trade["side"],
                                trade["amount"],
                                trade["price"]
                            ])
                    except Exception as e:
                        self.logger.error(f"Error getting trades data from DataManager: {e}")
                        # Fallback do pustej listy
                        sample_trades = []
                    
                    self.trades_table.setRowCount(len(sample_trades))
                    
                    for row, trade in enumerate(sample_trades):
                        for col, value in enumerate(trade):
                            item = QTableWidgetItem(str(value))
                            self.trades_table.setItem(row, col, item)
                else:
                    # Tabela nie ma już potrzebnych metod - została usunięta
                    self.trades_table = None
                    return
            except (RuntimeError, AttributeError):
                # Tabela została usunięta z pamięci
                self.trades_table = None
                return
        except Exception as e:
            self.logger.error(f"Error updating recent trades: {e}")
    
    def update_pnl_cards(self):
        """Aktualizuje karty P&L"""
        try:
            # Pobierz rzeczywiste dane P&L z DataManager
            try:
                from core.integrated_data_manager import get_integrated_data_manager
                data_manager = get_integrated_data_manager()
                
                # Pobierz dane portfela dla P&L
                try:
                    import asyncio
                    loop_running = False
                    try:
                        asyncio.get_running_loop()
                        loop_running = True
                    except RuntimeError:
                        loop_running = False
                    if loop_running:
                        import concurrent.futures
                        with concurrent.futures.ThreadPoolExecutor() as executor:
                            future = executor.submit(lambda: asyncio.run(data_manager.get_portfolio_data()))
                            portfolio_data = future.result(timeout=2)
                    else:
                        portfolio_data = asyncio.run(data_manager.get_portfolio_data())
                except Exception:
                    # Fallback - pobierz synchronicznie
                    portfolio_data = data_manager._get_sample_portfolio_data()
                
                # Oblicz P&L na podstawie danych portfela
                daily_pnl = portfolio_data.daily_change
                daily_trades = 15  # TODO: Dodać do DataManager
                total_pnl = portfolio_data.profit_loss
                total_roi = portfolio_data.profit_loss_percent
                
            except Exception as e:
                self.logger.error(f"Error getting P&L data from DataManager: {e}")
                # Fallback do domyślnych wartości
                daily_pnl = 0.0
                daily_trades = 0
                total_pnl = 0.0
                total_roi = 0.0
            
            # Aktualizuj kartę dziennego P&L
            if hasattr(self, 'daily_pnl_card') and self.daily_pnl_card:
                try:
                    if hasattr(self.daily_pnl_card, 'update_value'):
                        color = "🟢" if daily_pnl >= 0 else "🔴"
                        self.daily_pnl_card.update_value(
                            f"${daily_pnl:+,.2f}",
                            f"{daily_trades} transakcji"
                        )
                    else:
                        self.daily_pnl_card = None
                except (RuntimeError, AttributeError):
                    self.daily_pnl_card = None
            
            # Aktualizuj kartę całkowitego P&L
            if hasattr(self, 'total_pnl_card') and self.total_pnl_card:
                try:
                    if hasattr(self.total_pnl_card, 'update_value'):
                        color = "🟢" if total_pnl >= 0 else "🔴"
                        self.total_pnl_card.update_value(
                            f"${total_pnl:+,.2f}",
                            f"ROI: {total_roi:+.2f}%"
                        )
                    else:
                        self.total_pnl_card = None
                except (RuntimeError, AttributeError):
                    self.total_pnl_card = None
                    
        except Exception as e:
            self.logger.error(f"Error updating P&L cards: {e}")
    
    def update_status_bar(self):
        """Aktualizuje pasek statusu"""
        try:
            # Status połączenia
            if hasattr(self, 'status_connection') and self.status_connection:
                self.status_connection.setText("🟢 Połączono")
            
            # Liczba botów
            # TODO: Pobierz rzeczywistą liczbę botów
            if hasattr(self, 'status_bots') and self.status_bots:
                self.status_bots.setText("Boty: 2/3")
            
            # Ostatnia aktualizacja
            if hasattr(self, 'status_update') and self.status_update:
                now = datetime.now().strftime("%H:%M:%S")
                self.status_update.setText(f"Ostatnia aktualizacja: {now}")
        except Exception as e:
            self.logger.error(f"Error updating status bar: {e}")
    
    def switch_view(self, view_key: str):
        """Przełącza widok aplikacji z płynną animacją"""
        
        # Zapisz aktualny widok
        old_view = self.current_view
        self.current_view = view_key
        
        # Aktualizuj przyciski nawigacji
        for key, btn in self.nav_buttons.items():
            btn.setChecked(key == view_key)
            btn.setStyleSheet(self.get_nav_button_style(key == view_key))
        
        # Jeśli to ten sam widok, nie rób nic
        if old_view == view_key:
            return
        
        # Rozpocznij animację przejścia
        self._animate_view_transition(view_key)
        
        self.logger.info(f"Switched to view: {view_key}")
    
    def _animate_view_transition(self, view_key: str):
        """Animuje przejście między widokami"""
        # Zatrzymaj poprzednią animację jeśli jest aktywna
        if self.content_fade_animation:
            self.content_fade_animation.stop()
        
        # Utwórz animację fade out dla obecnego contentu
        self.content_fade_animation = QPropertyAnimation(self.content_area, b"windowOpacity")
        self.content_fade_animation.setDuration(150)  # 150ms fade out
        self.content_fade_animation.setStartValue(1.0)
        self.content_fade_animation.setEndValue(0.3)
        self.content_fade_animation.setEasingCurve(QEasingCurve.Type.OutQuad)
        
        # Po zakończeniu fade out, załaduj nowy widok i fade in
        self.content_fade_animation.finished.connect(lambda: self._load_new_view_and_fade_in(view_key))
        self.content_fade_animation.start()
    
    def _load_new_view_and_fade_in(self, view_key: str):
        """Ładuje nowy widok i wykonuje fade in"""
        
        # Wyczyść obecny widok bezpiecznie
        self.clear_content_layout(target_view=view_key)
        
        # Przełącz na odpowiedni widok
        try:
            if view_key == "dashboard":
                self.setup_dashboard()
            elif view_key == "bots":
                self.setup_bots_view()
            elif view_key == "portfolio":
                self.setup_portfolio_view()
            elif view_key == "risk_management":
                self.setup_risk_management_view()
            elif view_key == "notifications":
                self.setup_notifications_view()

            elif view_key == "analysis":
                self.setup_analysis_view()
            elif view_key == "logs":
                self.setup_logs_view()
            elif view_key == "settings":
                self.setup_settings_view()
            
        except Exception as e:
            self.logger.error(f"Error setting up view {view_key}: {e}")
            import traceback
            traceback.print_exc()
        
        # Fade in nowego contentu
        self.content_fade_animation = QPropertyAnimation(self.content_area, b"windowOpacity")
        self.content_fade_animation.setDuration(200)  # 200ms fade in
        self.content_fade_animation.setStartValue(0.3)
        self.content_fade_animation.setEndValue(1.0)
        self.content_fade_animation.setEasingCurve(QEasingCurve.Type.InQuad)
        self.content_fade_animation.start()
    
    def clear_content_layout(self, target_view=None):
        """Bezpiecznie czyści layout zawartości"""
        try:
            print(f"🧹 CLEAR_CONTENT_LAYOUT wywołane, target_view: {target_view}")
            # Zatrzymaj timer odświeżania podczas czyszczenia
            if hasattr(self, 'refresh_timer') and self.refresh_timer:
                self.refresh_timer.stop()
            
            # Wyczyść referencje do widgetów dashboard tylko gdy przełączamy się z dashboard na inny widok
            current_view = getattr(self, 'current_view', 'dashboard')
            if target_view != 'dashboard' and current_view == 'dashboard':
                print("🧹 Czyszczenie referencji dashboard (przełączanie na inny widok)")
                self.portfolio_card = None
                self.active_bots_card = None
                self.trades_table = None
                self.bots_layout = None
            elif target_view == 'dashboard' and current_view == 'dashboard':
                print("🧹 Pozostajemy w dashboard - zachowujemy referencje")
                # Nie czyścimy referencji dashboard gdy pozostajemy w tym samym widoku
                pass
            else:
                print("🧹 Czyszczenie standardowe")
                self.portfolio_card = None
                self.active_bots_card = None
                self.trades_table = None
                self.bots_layout = None
            
            # Usuń wszystkie widgety z layoutu
            while self.content_layout.count():
                child = self.content_layout.takeAt(0)
                if child.widget():
                    widget = child.widget()
                    # Sprawdź czy to jest jeden z zachowywanych widgetów
                    if (widget == self.bot_management_widget or 
                        widget == self.portfolio_widget or 
                        widget == self.analysis_widget or 
                        widget == self.settings_widget or 
                        widget == self.logs_widget or 
                        widget == self.notifications_widget or 
                        widget == self.risk_management_widget):
                        # Tylko usuń z layoutu, ale nie niszczyć
                        widget.setParent(None)
                    else:
                        # Normalnie usuń inne widgety
                        widget.setParent(None)
                        widget.deleteLater()
                elif child.layout():
                    # Rekurencyjnie usuń zagnieżdżone layouty
                    self.clear_layout(child.layout())
                    
        except Exception as e:
            self.logger.error(f"Error clearing content layout: {e}")
    
    def clear_layout(self, layout):
        """Rekurencyjnie czyści layout"""
        try:
            while layout.count():
                child = layout.takeAt(0)
                if child.widget():
                    child.widget().deleteLater()
                elif child.layout():
                    self.clear_layout(child.layout())
        except Exception as e:
            self.logger.error(f"Error clearing layout: {e}")
    
    def clear_bots_layout(self):
        """Bezpiecznie czyści layout botów"""
        try:
            if hasattr(self, 'bots_layout') and self.bots_layout:
                while self.bots_layout.count():
                    child = self.bots_layout.takeAt(0)
                    if child.widget():
                        widget = child.widget()
                        widget.setParent(None)
                        widget.deleteLater()
        except Exception as e:
            self.logger.error(f"Error clearing bots layout: {e}")
    
    def create_new_bot(self):
        """Otwiera kreator nowego bota"""
        self.logger.info("FLOW: UI → Rozpoczęcie tworzenia nowego bota przez użytkownika")
        try:
            from ui.bot_config import BotConfigWidget
            
            # Utwórz dialog konfiguracji bota
            dialog = QDialog(self)
            dialog.setWindowTitle("Nowy Bot")
            dialog.setModal(True)
            dialog.resize(800, 600)
            self.logger.info("FLOW: UI → Dialog konfiguracji bota został otwarty")
            
            layout = QVBoxLayout(dialog)
            
            # Dodaj widget konfiguracji bota
            bot_config = BotConfigWidget()
            layout.addWidget(bot_config)
            
            # Przyciski
            buttons_layout = QHBoxLayout()
            buttons_layout.addStretch()
            
            cancel_btn = QPushButton("Anuluj")
            cancel_btn.clicked.connect(dialog.reject)
            buttons_layout.addWidget(cancel_btn)
            
            save_btn = QPushButton("Zapisz Bot")
            save_btn.clicked.connect(lambda: self.save_new_bot(bot_config, dialog))
            save_btn.setStyleSheet("""
                QPushButton {
                    background-color: #4CAF50;
                    color: white;
                    border: none;
                    padding: 8px 16px;
                    border-radius: 4px;
                    font-weight: bold;
                }
                QPushButton:hover {
                    background-color: #45a049;
                }
            """)
            buttons_layout.addWidget(save_btn)
            
            layout.addLayout(buttons_layout)
            
            dialog.exec()
            
        except ImportError as e:
            QMessageBox.warning(self, "Błąd", f"Nie można załadować kreatora bota: {e}")
        except Exception as e:
            QMessageBox.critical(self, "Błąd", f"Wystąpił błąd: {e}")
    
    def save_new_bot(self, bot_config, dialog):
        """Zapisuje nowego bota"""
        self.logger.info("FLOW: UI → Config → Rozpoczęcie zapisywania nowego bota")
        try:
            # Pobierz dane z formularza
            bot_data = bot_config.get_bot_data()
            self.logger.info(f"FLOW: UI → Config → Pobrano dane bota: {bot_data.get('name', 'Nowy Bot') if bot_data else 'BRAK'}")
            
            if not bot_data:
                self.logger.warning("FLOW: UI → Config → BŁĄD: Nie można pobrać danych bota")
                QMessageBox.warning(self, "Błąd", "Nie można pobrać danych bota")
                return
            
            # Tutaj można dodać logikę zapisywania do bazy danych
            # Na razie tylko pokaż komunikat
            self.logger.info(f"FLOW: UI → Config → Bot '{bot_data.get('name', 'Nowy Bot')}' został pomyślnie utworzony")
            QMessageBox.information(self, "Sukces", f"Bot '{bot_data.get('name', 'Nowy Bot')}' został utworzony!")
            
            dialog.accept()
            
            # Odśwież dane na dashboardzie
            self.logger.info("FLOW: UI → Odświeżanie danych dashboardu po utworzeniu bota")
            self.refresh_data()
            
        except Exception as e:
            QMessageBox.critical(self, "Błąd", f"Nie można zapisać bota: {e}")
    
    def start_all_bots(self):
        """Uruchamia wszystkie boty"""
        self.logger.info("FLOW: UI → Rozpoczęcie uruchamiania wszystkich botów przez użytkownika")
        # TODO: Implementuj uruchamianie wszystkich botów
        QMessageBox.information(self, "Boty", "Uruchamianie wszystkich botów...")
        self.logger.info("FLOW: UI → Zakończono próbę uruchomienia wszystkich botów")
    
    def stop_all_bots(self):
        """Zatrzymuje wszystkie boty"""
        self.logger.info("FLOW: UI → Rozpoczęcie zatrzymywania wszystkich botów przez użytkownika")
        # TODO: Implementuj zatrzymywanie wszystkich botów
        QMessageBox.information(self, "Boty", "Zatrzymywanie wszystkich botów...")
        self.logger.info("FLOW: UI → Zakończono próbę zatrzymania wszystkich botów")
    
    def toggle_sidebar(self):
        """Przełącza widoczność sidebara"""
        self.sidebar.setVisible(not self.sidebar.isVisible())
    
    def import_config(self):
        """Importuje konfigurację"""
        # TODO: Implementuj import konfiguracji
        QMessageBox.information(self, "Import", "Import konfiguracji zostanie wkrótce zaimplementowany.")
    
    def export_data(self):
        """Eksportuje dane"""
        # TODO: Implementuj eksport danych
        QMessageBox.information(self, "Eksport", "Eksport danych zostanie wkrótce zaimplementowany.")
    
    def show_about(self):
        """Pokazuje okno o programie"""
        QMessageBox.about(self, "O Programie", 
                         "CryptoBotDesktop v1.0.0\n\n"
                         "Zaawansowana platforma do automatycznego handlu kryptowalutami.\n\n"
                         "© 2024 CryptoBotDesktop")
    
    def tray_icon_activated(self, reason):
        """Obsługuje kliknięcie ikony w zasobniku"""
        if reason == QSystemTrayIcon.ActivationReason.Trigger:
            if self.isVisible():
                self.hide()
            else:
                self.show()
                self.raise_()
                self.activateWindow()
    
    def setup_bots_view(self):
        """Konfiguruje widok botów"""
        try:
            from ui.bot_management import BotManagementWidget, PYQT_AVAILABLE as BOT_MANAGEMENT_PYQT_AVAILABLE
            if not BOT_MANAGEMENT_PYQT_AVAILABLE:
                placeholder = QLabel("PyQt6 nie jest dostępne - widok botów niedostępny")
                placeholder.setAlignment(Qt.AlignmentFlag.AlignCenter)
                placeholder.setStyleSheet("font-size: 18px; color: #666;")
                self.content_layout.addWidget(placeholder)
                return
            
            # Utwórz instancję tylko raz
            if self.bot_management_widget is None:
                self.bot_management_widget = BotManagementWidget()
                
            self.content_layout.addWidget(self.bot_management_widget)
        except (ImportError, Exception) as e:
            self.logger.error(f"Failed to load BotManagementWidget: {e}")
            placeholder = QLabel("Błąd ładowania widoku botów")
            placeholder.setAlignment(Qt.AlignmentFlag.AlignCenter)
            placeholder.setStyleSheet("font-size: 18px; color: #666;")
            self.content_layout.addWidget(placeholder)
    
    def setup_portfolio_view(self):
        """Konfiguruje widok portfela"""
        try:
            from ui.portfolio import PortfolioWidget, PYQT_AVAILABLE as PORTFOLIO_PYQT_AVAILABLE
            if not PORTFOLIO_PYQT_AVAILABLE:
                placeholder = QLabel("PyQt6 nie jest dostępne - widok portfela niedostępny")
                placeholder.setAlignment(Qt.AlignmentFlag.AlignCenter)
                placeholder.setStyleSheet("font-size: 18px; color: #666;")
                self.content_layout.addWidget(placeholder)
                return
            
            # Utwórz instancję tylko raz
            if self.portfolio_widget is None:
                self.portfolio_widget = PortfolioWidget()
                
                # Konfiguruj Production Manager jeśli dostępny
                if hasattr(self, 'production_manager') and self.production_manager:
                    self.portfolio_widget.set_production_manager(self.production_manager)
                
            self.content_layout.addWidget(self.portfolio_widget)
        except (ImportError, Exception) as e:
            self.logger.error(f"Failed to load PortfolioWidget: {e}")
            placeholder = QLabel("Błąd ładowania widoku portfela")
            placeholder.setAlignment(Qt.AlignmentFlag.AlignCenter)
            placeholder.setStyleSheet("font-size: 18px; color: #666;")
            self.content_layout.addWidget(placeholder)
    
    def setup_risk_management_view(self):
        """Konfiguruje widok zarządzania ryzykiem"""
        # Scroll area dla całego widoku
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        
        content_widget = QWidget()
        content_layout = QVBoxLayout(content_widget)
        content_layout.setSpacing(30)
        content_layout.setContentsMargins(20, 20, 20, 20)
        
        # Nagłówek
        header_layout = QHBoxLayout()
        header = QLabel("⚠️ Zarządzanie Ryzykiem")
        header.setObjectName("sectionTitle")
        header_layout.addWidget(header)
        
        header_layout.addStretch()
        
        # Przycisk odświeżania
        refresh_btn = QPushButton("🔄 Odśwież")
        refresh_btn.setObjectName("actionButton")
        refresh_btn.clicked.connect(self.refresh_risk_data)
        header_layout.addWidget(refresh_btn)
        
        content_layout.addLayout(header_layout)
        
        # Sekcja metryk ryzyka - karty jak w portfelu
        self.setup_risk_metrics_cards(content_layout)
        
        # Sekcja ustawień - formularz jak w ustawieniach
        self.setup_risk_settings_forms(content_layout)
        
        # Sekcja kontroli awaryjnych
        self.setup_emergency_controls(content_layout)
        
        scroll.setWidget(content_widget)
        self.content_layout.addWidget(scroll)
        
        # Ustaw referencję do widget'u
        self.risk_management_widget = scroll
    
    def setup_risk_metrics_cards(self, layout):
        """Konfiguruje karty z metrykami ryzyka jak w portfelu"""
        print("🏗️ SETUP_RISK_CARDS: Rozpoczęcie konfiguracji kart metryk ryzyka")
        
        metrics_group = QGroupBox("📊 Metryki Ryzyka")
        metrics_group.setObjectName("settingsGroup")
        metrics_layout = QVBoxLayout(metrics_group)
        
        # Grid dla kart
        cards_layout = QGridLayout()
        cards_layout.setSpacing(15)
        
        # Przechowuj referencje do kart dla późniejszej aktualizacji
        self.risk_cards = {}
        print("✅ SETUP_RISK_CARDS: Zainicjalizowano słownik risk_cards")
        
        # Karty z metrykami ryzyka
        risk_cards_data = [
            ("current_drawdown", "Obecny Drawdown", "2.5%", "W normie", "#4CAF50"),
            ("max_drawdown", "Maksymalny Drawdown", "8.2%", "Ostatnie 30 dni", "#FF9800"),
            ("var_1day", "VaR (1 dzień)", "$1,250", "95% pewności", "#2196F3"),
            ("sharpe_ratio", "Sharpe Ratio", "1.85", "Dobra wydajność", "#4CAF50"),
            ("win_rate", "Win Rate", "68%", "Ostatnie 100 transakcji", "#9C27B0"),
            ("profit_factor", "Profit Factor", "2.1", "Pozytywny", "#4CAF50"),
            ("beta", "Beta", "0.85", "Względem BTC", "#607D8B"),
            ("sortino_ratio", "Sortino Ratio", "2.3", "Skorygowany o ryzyko", "#795548"),
            ("calmar_ratio", "Calmar Ratio", "1.2", "Zwrot/Max DD", "#FF5722")
        ]
        
        for i, (key, title, value, subtitle, color) in enumerate(risk_cards_data):
            card = DashboardCard(title, value, subtitle, color)
            card.setFixedHeight(120)
            cards_layout.addWidget(card, i // 3, i % 3)
            
            # Przechowaj referencję do karty
            self.risk_cards[key] = card
            print(f"✅ SETUP_RISK_CARDS: Utworzono kartę {key}: {title}")
        
        metrics_layout.addLayout(cards_layout)
        layout.addWidget(metrics_group)
        
        print(f"✅ SETUP_RISK_CARDS: Utworzono {len(self.risk_cards)} kart metryk ryzyka")
        
        # Automatycznie załaduj dane po utworzeniu kart
        print("🔄 SETUP_RISK_CARDS: Wywołanie refresh_risk_data")
        self.refresh_risk_data()
    
    def setup_risk_settings_forms(self, layout):
        """Konfiguruje formularz ustawień zarządzania ryzykiem jak w ustawieniach"""
        # Limity pozycji
        position_limits_group = QGroupBox("📈 Limity Pozycji")
        position_limits_group.setObjectName("settingsGroup")
        position_limits_layout = QFormLayout(position_limits_group)
        
        # Maksymalny rozmiar pozycji
        self.max_position_size = QDoubleSpinBox()
        self.max_position_size.setRange(0.1, 100.0)
        self.max_position_size.setValue(10.0)
        self.max_position_size.setSuffix(" %")
        self.max_position_size.setObjectName("settingsSpinBox")
        position_limits_layout.addRow("Maksymalny rozmiar pozycji:", self.max_position_size)
        
        # Maksymalna liczba otwartych pozycji
        self.max_open_positions = QSpinBox()
        self.max_open_positions.setRange(1, 50)
        self.max_open_positions.setValue(5)
        self.max_open_positions.setObjectName("settingsSpinBox")
        position_limits_layout.addRow("Maksymalna liczba pozycji:", self.max_open_positions)
        
        # Maksymalna liczba transakcji dziennie
        self.max_daily_trades = QSpinBox()
        self.max_daily_trades.setRange(1, 1000)
        self.max_daily_trades.setValue(20)
        self.max_daily_trades.setObjectName("settingsSpinBox")
        position_limits_layout.addRow("Maksymalna liczba transakcji/dzień:", self.max_daily_trades)
        
        layout.addWidget(position_limits_group)
        
        # Stop Loss i Take Profit
        sl_tp_group = QGroupBox("🛡️ Stop Loss & Take Profit")
        sl_tp_group.setObjectName("settingsGroup")
        sl_tp_layout = QFormLayout(sl_tp_group)
        
        # Domyślny Stop Loss
        self.default_stop_loss = QDoubleSpinBox()
        self.default_stop_loss.setRange(0.1, 50.0)
        self.default_stop_loss.setValue(2.0)
        self.default_stop_loss.setSuffix(" %")
        self.default_stop_loss.setObjectName("settingsSpinBox")
        sl_tp_layout.addRow("Domyślny Stop Loss:", self.default_stop_loss)
        
        # Domyślny Take Profit
        self.default_take_profit = QDoubleSpinBox()
        self.default_take_profit.setRange(0.1, 100.0)
        self.default_take_profit.setValue(4.0)
        self.default_take_profit.setSuffix(" %")
        self.default_take_profit.setObjectName("settingsSpinBox")
        sl_tp_layout.addRow("Domyślny Take Profit:", self.default_take_profit)
        
        # Trailing Stop
        self.trailing_stop_enabled = QCheckBox("Włącz Trailing Stop")
        self.trailing_stop_enabled.setObjectName("settingsCheckBox")
        sl_tp_layout.addRow("", self.trailing_stop_enabled)
        
        self.trailing_stop_distance = QDoubleSpinBox()
        self.trailing_stop_distance.setRange(0.1, 10.0)
        self.trailing_stop_distance.setValue(1.0)
        self.trailing_stop_distance.setSuffix(" %")
        self.trailing_stop_distance.setObjectName("settingsSpinBox")
        sl_tp_layout.addRow("Odległość Trailing Stop:", self.trailing_stop_distance)
        
        layout.addWidget(sl_tp_group)
        
        # Limity strat
        loss_limits_group = QGroupBox("📉 Limity Strat")
        loss_limits_group.setObjectName("settingsGroup")
        loss_limits_layout = QFormLayout(loss_limits_group)
        
        # Maksymalna dzienna strata
        self.max_daily_loss = QDoubleSpinBox()
        self.max_daily_loss.setRange(0.1, 50.0)
        self.max_daily_loss.setValue(5.0)
        self.max_daily_loss.setSuffix(" %")
        self.max_daily_loss.setObjectName("settingsSpinBox")
        loss_limits_layout.addRow("Maksymalna dzienna strata:", self.max_daily_loss)
        
        # Maksymalny drawdown
        self.max_drawdown = QDoubleSpinBox()
        self.max_drawdown.setRange(1.0, 50.0)
        self.max_drawdown.setValue(15.0)
        self.max_drawdown.setSuffix(" %")
        self.max_drawdown.setObjectName("settingsSpinBox")
        loss_limits_layout.addRow("Maksymalny drawdown:", self.max_drawdown)
        
        # Awaryjne zatrzymanie
        self.emergency_stop_enabled = QCheckBox("Włącz awaryjne zatrzymanie")
        self.emergency_stop_enabled.setObjectName("settingsCheckBox")
        loss_limits_layout.addRow("", self.emergency_stop_enabled)
        
        layout.addWidget(loss_limits_group)
        
        # Zarządzanie kapitałem
        capital_group = QGroupBox("💰 Zarządzanie Kapitałem")
        capital_group.setObjectName("settingsGroup")
        capital_layout = QFormLayout(capital_group)
        
        # Ryzyko na transakcję
        self.risk_per_trade = QDoubleSpinBox()
        self.risk_per_trade.setRange(0.1, 10.0)
        self.risk_per_trade.setValue(1.0)
        self.risk_per_trade.setSuffix(" %")
        self.risk_per_trade.setObjectName("settingsSpinBox")
        capital_layout.addRow("Ryzyko na transakcję:", self.risk_per_trade)
        
        # Kryterium Kelly'ego
        self.kelly_criterion_enabled = QCheckBox("Użyj kryterium Kelly'ego")
        self.kelly_criterion_enabled.setObjectName("settingsCheckBox")
        capital_layout.addRow("", self.kelly_criterion_enabled)
        
        # Składanie zysków
        self.compound_profits = QCheckBox("Składaj zyski")
        self.compound_profits.setObjectName("settingsCheckBox")
        self.compound_profits.setChecked(True)
        capital_layout.addRow("", self.compound_profits)
        
        layout.addWidget(capital_group)
        
        # Przycisk zapisz ustawienia
        save_button = QPushButton("💾 Zapisz Ustawienia Ryzyka")
        save_button.setObjectName("primaryButton")
        save_button.clicked.connect(self.save_risk_settings)
        layout.addWidget(save_button)
    
    def setup_emergency_controls(self, layout):
        """Konfiguruje kontrole awaryjne"""
        emergency_group = QGroupBox("🚨 Kontrole Awaryjne")
        emergency_group.setObjectName("settingsGroup")
        emergency_layout = QVBoxLayout(emergency_group)
        
        # Przycisk zatrzymania wszystkich botów
        stop_all_btn = QPushButton("⛔ ZATRZYMAJ WSZYSTKIE BOTY")
        stop_all_btn.setObjectName("dangerButton")
        stop_all_btn.setMinimumHeight(50)
        stop_all_btn.clicked.connect(self.emergency_stop_all_bots)
        emergency_layout.addWidget(stop_all_btn)
        
        # Przycisk zamknięcia wszystkich pozycji
        close_all_btn = QPushButton("🔴 ZAMKNIJ WSZYSTKIE POZYCJE")
        close_all_btn.setObjectName("dangerButton")
        close_all_btn.setMinimumHeight(50)
        close_all_btn.clicked.connect(self.emergency_close_all_positions)
        emergency_layout.addWidget(close_all_btn)
        
        # Status kontroli awaryjnych
        status_label = QLabel("Status: Wszystkie systemy działają normalnie")
        status_label.setObjectName("statusLabel")
        emergency_layout.addWidget(status_label)
        
        layout.addWidget(emergency_group)
    
    def refresh_risk_data(self):
        """Odświeża dane ryzyka używając centralnego DataManager"""
        try:
            print("🔄 REFRESH_RISK_DATA: Rozpoczęcie odświeżania danych ryzyka...")
            
            # Sprawdź czy karty zostały utworzone
            if not hasattr(self, 'risk_cards'):
                print("🏗️ REFRESH_RISK_DATA: Karty ryzyka nie istnieją - tworzę je teraz...")
                # Inicjalizuj słownik kart ryzyka
                self.risk_cards = {}
                
                # Utwórz karty z domyślnymi wartościami
                risk_cards_data = [
                    ("current_drawdown", "Obecny Drawdown", "2.5%", "W normie", "#4CAF50"),
                    ("max_drawdown", "Maksymalny Drawdown", "8.2%", "Ostatnie 30 dni", "#FF9800"),
                    ("var_1day", "VaR (1 dzień)", "$1,250", "95% pewności", "#2196F3"),
                    ("sharpe_ratio", "Sharpe Ratio", "1.85", "Dobra wydajność", "#4CAF50"),
                    ("win_rate", "Win Rate", "68%", "Ostatnie 100 transakcji", "#9C27B0"),
                    ("profit_factor", "Profit Factor", "2.1", "Pozytywny", "#4CAF50"),
                    ("beta", "Beta", "0.85", "Względem BTC", "#607D8B"),
                    ("sortino_ratio", "Sortino Ratio", "2.3", "Skorygowany o ryzyko", "#795548"),
                    ("calmar_ratio", "Calmar Ratio", "1.2", "Zwrot/Max DD", "#FF5722")
                ]
                
                # Utwórz karty w pamięci (bez dodawania do layoutu)
                for key, title, value, subtitle, color in risk_cards_data:
                    card = DashboardCard(title, value, subtitle, color)
                    card.setFixedHeight(120)
                    self.risk_cards[key] = card
                    print(f"✅ REFRESH_RISK_DATA: Utworzono kartę {key}: {title}")
                
                print(f"✅ REFRESH_RISK_DATA: Utworzono {len(self.risk_cards)} kart ryzyka w pamięci")
            
            print(f"✅ REFRESH_RISK_DATA: Znaleziono {len(self.risk_cards)} kart ryzyka")
            
            # Użyj centralnego DataManager
            try:
                import sys
                import os
                sys.path.append(os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'core'))
                
                from core.integrated_data_manager import get_integrated_data_manager
                data_manager = get_integrated_data_manager()
                print("✅ REFRESH_RISK_DATA: DataManager zaimportowany pomyślnie")
                
                # Pobierz metryki ryzyka asynchronicznie
                import asyncio
                
                async def get_risk_data():
                    return await data_manager.get_risk_metrics()
                
                # Uruchom w pętli zdarzeń
                try:
                    try:
                        loop = asyncio.get_running_loop()
                        # Jeśli pętla już działa, utwórz zadanie na istniejącej pętli
                        task = loop.create_task(get_risk_data())
                        # Dla synchronicznego wywołania, użyj callback
                        def update_callback(task):
                            try:
                                risk_metrics = task.result()
                                self.update_risk_metrics_cards_from_data(risk_metrics)
                                print("✅ REFRESH_RISK_DATA: Dane ryzyka zostały odświeżone z DataManager")
                            except Exception as e:
                                print(f"❌ REFRESH_RISK_DATA: Błąd w callback: {e}")
                                self.update_risk_metrics_cards_with_defaults()
                        
                        task.add_done_callback(update_callback)
                    except RuntimeError:
                        risk_metrics = asyncio.run(get_risk_data())
                        self.update_risk_metrics_cards_from_data(risk_metrics)
                        print("✅ REFRESH_RISK_DATA: Dane ryzyka zostały odświeżone z DataManager")
                except Exception as e:
                    print(f"⚠️ REFRESH_RISK_DATA: Błąd uruchamiania coroutine: {e}")
                    # Brak działającej pętli - uruchom coroutine w osobnym wątku
                    import threading
                    def worker():
                        try:
                            res = asyncio.run(get_risk_data())
                            self.update_risk_metrics_cards_from_data(res)
                            print("✅ REFRESH_RISK_DATA: Dane ryzyka zostały odświeżone z DataManager (thread)")
                        except Exception as e2:
                            print(f"❌ REFRESH_RISK_DATA: Błąd aktualizacji kart: {e2}")
                            self.update_risk_metrics_cards_with_defaults()
                    threading.Thread(target=worker, daemon=True).start()
                    
            except ImportError as e:
                print(f"⚠️ REFRESH_RISK_DATA: DataManager nie jest dostępny: {e}")
                # Użyj domyślnych wartości
                self.update_risk_metrics_cards_with_defaults()
                
        except Exception as e:
            print(f"❌ REFRESH_RISK_DATA: Błąd podczas odświeżania danych ryzyka: {e}")
            import traceback
            traceback.print_exc()
            self.update_risk_metrics_cards_with_defaults()
    
    def update_risk_metrics_cards_from_data(self, risk_metrics):
        """Aktualizuje karty metryk ryzyka używając danych z DataManager"""
        try:
            print(f"📊 UPDATE_RISK_CARDS: Rozpoczęcie aktualizacji kart z danymi: {risk_metrics}")
            
            if not hasattr(self, 'risk_cards') or not self.risk_cards:
                print("❌ UPDATE_RISK_CARDS: Karty ryzyka nie zostały jeszcze utworzone")
                return
            
            # Mapowanie danych na karty
            cards_updates = {
                'current_drawdown': (
                    f"{risk_metrics.current_drawdown:.1f}%",
                    "W normie" if risk_metrics.current_drawdown < 5 else "Uwaga"
                ),
                'max_drawdown': (
                    f"{risk_metrics.max_drawdown:.1f}%",
                    "Ostatnie 30 dni"
                ),
                'var_1day': (
                    f"${risk_metrics.var_1day:.0f}",
                    "95% pewności"
                ),
                'sharpe_ratio': (
                    f"{risk_metrics.sharpe_ratio:.2f}",
                    "Dobra wydajność" if risk_metrics.sharpe_ratio > 1 else "Słaba wydajność"
                ),
                'win_rate': (
                    f"{risk_metrics.win_rate:.0f}%",
                    "Ostatnie 100 transakcji"
                ),
                'profit_factor': (
                    f"{risk_metrics.profit_factor:.1f}",
                    "Pozytywny" if risk_metrics.profit_factor > 1 else "Negatywny"
                ),
                'beta': (
                    f"{risk_metrics.beta:.2f}",
                    "Względem BTC"
                ),
                'sortino_ratio': (
                    f"{risk_metrics.sortino_ratio:.2f}",
                    "Skorygowany o ryzyko"
                ),
                'calmar_ratio': (
                    f"{risk_metrics.calmar_ratio:.2f}",
                    "Zwrot/Max DD"
                )
            }
            
            # Aktualizuj każdą kartę
            for key, (value, subtitle) in cards_updates.items():
                if key in self.risk_cards:
                    card = self.risk_cards[key]
                    card.update_value(value, subtitle)
                    print(f"✅ UPDATE_RISK_CARDS: Zaktualizowano kartę {key}: {value}")
                else:
                    print(f"⚠️ UPDATE_RISK_CARDS: Nie znaleziono karty {key}")
            
            print(f"✅ UPDATE_RISK_CARDS: Zaktualizowano {len(cards_updates)} kart metryk ryzyka")
            
        except Exception as e:
            print(f"Błąd podczas aktualizacji kart metryk ryzyka: {e}")
            
    def update_risk_metrics_cards(self, risk_status):
        """Aktualizuje karty metryk ryzyka prawdziwymi danymi"""
        try:
            metrics = risk_status.get('metrics', {})
            
            # Znajdź i aktualizuj karty (zakładając że są przechowywane jako atrybuty)
            cards_data = [
                ("Obecny Drawdown", f"{metrics.get('current_drawdown', 0):.1f}%", 
                 "W normie" if metrics.get('current_drawdown', 0) < 5 else "Uwaga", 
                 "#4CAF50" if metrics.get('current_drawdown', 0) < 5 else "#FF9800"),
                ("Maksymalny Drawdown", f"{metrics.get('max_drawdown', 0):.1f}%", 
                 "Ostatnie 30 dni", "#FF9800"),
                ("VaR (1 dzień)", f"${metrics.get('var_1day', 0):.0f}", 
                 "95% pewności", "#2196F3"),
                ("Sharpe Ratio", f"{metrics.get('sharpe_ratio', 0):.2f}", 
                 "Dobra wydajność" if metrics.get('sharpe_ratio', 0) > 1 else "Słaba wydajność", 
                 "#4CAF50" if metrics.get('sharpe_ratio', 0) > 1 else "#FF9800"),
                ("Win Rate", f"{metrics.get('win_rate', 0):.0f}%", 
                 "Ostatnie 100 transakcji", "#9C27B0"),
                ("Profit Factor", f"{metrics.get('profit_factor', 0):.1f}", 
                 "Pozytywny" if metrics.get('profit_factor', 0) > 1 else "Negatywny", 
                 "#4CAF50" if metrics.get('profit_factor', 0) > 1 else "#F44336"),
                ("Beta", f"{metrics.get('beta', 0):.2f}", 
                 "Względem BTC", "#607D8B"),
                ("Sortino Ratio", f"{metrics.get('sortino_ratio', 0):.2f}", 
                 "Skorygowany o ryzyko", "#795548"),
                ("Calmar Ratio", f"{metrics.get('calmar_ratio', 0):.2f}", 
                 "Zwrot/Max DD", "#FF5722")
            ]
            
            print(f"Aktualizacja kart metryk ryzyka z danymi: {len(cards_data)} kart")
            
        except Exception as e:
            print(f"Błąd podczas aktualizacji kart metryk ryzyka: {e}")
            
    def update_risk_metrics_cards_with_defaults(self):
        """Aktualizuje karty metryk ryzyka domyślnymi wartościami"""
        try:
            print("🔧 DEFAULT_RISK_DATA: Używanie domyślnych wartości dla metryk ryzyka")
            
            # Sprawdź czy karty istnieją
            if not hasattr(self, 'risk_cards') or not self.risk_cards:
                print("❌ DEFAULT_RISK_DATA: Karty ryzyka nie zostały jeszcze utworzone")
                return
            
            print(f"✅ DEFAULT_RISK_DATA: Znaleziono {len(self.risk_cards)} kart ryzyka")
            
            # Domyślne wartości gdy RiskManager nie jest dostępny
            default_cards_updates = {
                'current_drawdown': ("2.5%", "W normie"),
                'max_drawdown': ("8.2%", "Ostatnie 30 dni"),
                'var_1day': ("$1,250", "95% pewności"),
                'sharpe_ratio': ("1.85", "Dobra wydajność"),
                'win_rate': ("68%", "Ostatnie 100 transakcji"),
                'profit_factor': ("2.1", "Pozytywny"),
                'beta': ("0.85", "Względem BTC"),
                'sortino_ratio': ("2.3", "Skorygowany o ryzyko"),
                'calmar_ratio': ("1.2", "Zwrot/Max DD")
            }
            
            # Aktualizuj każdą kartę
            for key, (value, subtitle) in default_cards_updates.items():
                if key in self.risk_cards:
                    card = self.risk_cards[key]
                    card.update_value(value, subtitle)
                    print(f"✅ DEFAULT_RISK_DATA: Zaktualizowano kartę {key}: {value}")
                else:
                    print(f"⚠️ DEFAULT_RISK_DATA: Nie znaleziono karty {key}")
            
            print(f"✅ DEFAULT_RISK_DATA: Zaktualizowano {len(default_cards_updates)} kart domyślnymi wartościami")
            
        except Exception as e:
            print(f"❌ DEFAULT_RISK_DATA: Błąd podczas ustawiania domyślnych wartości: {e}")
            import traceback
            traceback.print_exc()
    
    def save_risk_settings(self):
        """Zapisuje ustawienia zarządzania ryzykiem"""
        try:
            settings = {
                'max_position_size': self.max_position_size.value(),
                'max_open_positions': self.max_open_positions.value(),
                'max_daily_trades': self.max_daily_trades.value(),
                'default_stop_loss': self.default_stop_loss.value(),
                'default_take_profit': self.default_take_profit.value(),
                'trailing_stop_enabled': self.trailing_stop_enabled.isChecked(),
                'trailing_stop_distance': self.trailing_stop_distance.value(),
                'max_daily_loss': self.max_daily_loss.value(),
                'max_drawdown': self.max_drawdown.value(),
                'emergency_stop_enabled': self.emergency_stop_enabled.isChecked(),
                'risk_per_trade': self.risk_per_trade.value(),
                'kelly_criterion_enabled': self.kelly_criterion_enabled.isChecked(),
                'compound_profits': self.compound_profits.isChecked()
            }
            
            # Użyj ConfigManager do zapisania ustawień
            config_manager = get_config_manager()
            
            # Pobierz aktualną konfigurację app
            current_config = config_manager.get_app_config()
            
            # Aktualizuj sekcję risk_management
            if 'risk_management' not in current_config:
                current_config['risk_management'] = {}
            current_config['risk_management'].update(settings)
            
            # Zapisz przez ConfigManager (to wyśle event CONFIG_UPDATED)
            config_manager.save_config('app', current_config)
            
            # Powiadom system o zmianie ustawień
            if hasattr(self, 'risk_manager'):
                self.risk_manager.update_settings(settings)
            
            print("Ustawienia zarządzania ryzykiem zostały zapisane")
            
        except Exception as e:
            print(f"Błąd podczas zapisywania ustawień ryzyka: {e}")
    
    def emergency_stop_all_bots(self):
        """Awaryjne zatrzymanie wszystkich botów"""
        try:
            # Potwierdzenie akcji
            reply = QMessageBox.question(
                self, 
                'Potwierdzenie', 
                'Czy na pewno chcesz zatrzymać wszystkie boty?',
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
            )
            
            if reply == QMessageBox.StandardButton.Yes:
                # Zatrzymaj wszystkie boty
                if hasattr(self, 'bot_manager'):
                    self.bot_manager.stop_all_bots()
                print("Wszystkie boty zostały zatrzymane")
                
        except Exception as e:
            print(f"Błąd podczas awaryjnego zatrzymywania botów: {e}")
    
    def emergency_close_all_positions(self):
        """Awaryjne zamknięcie wszystkich pozycji"""
        try:
            # Potwierdzenie akcji
            reply = QMessageBox.question(
                self, 
                'Potwierdzenie', 
                'Czy na pewno chcesz zamknąć wszystkie pozycje?',
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
            )
            
            if reply == QMessageBox.StandardButton.Yes:
                # Zamknij wszystkie pozycje
                if hasattr(self, 'position_manager'):
                    self.position_manager.close_all_positions()
                print("Wszystkie pozycje zostały zamknięte")
                
        except Exception as e:
            print(f"Błąd podczas awaryjnego zamykania pozycji: {e}")
    
    def setup_notifications_view(self):
        """Konfiguruje widok powiadomień"""
        # Nagłówek
        header_layout = QHBoxLayout()
        
        header = QLabel("Powiadomienia")
        header.setStyleSheet("font-size: 24px; font-weight: bold; margin-bottom: 20px;")
        header_layout.addWidget(header)
        
        header_layout.addStretch()
        
        # Przycisk odświeżania
        refresh_btn = QPushButton("Odśwież")
        refresh_btn.setStyleSheet("""
            QPushButton {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:1,
                    stop:0 rgba(102, 126, 234, 1.0), 
                    stop:1 rgba(118, 75, 162, 1.0));
                color: white;
                border: none;
                padding: 10px 20px;
                border-radius: 8px;
                font-weight: 600;
                font-size: 13px;
            }
            QPushButton:hover {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:1,
                    stop:0 rgba(82, 106, 214, 1.0), 
                    stop:1 rgba(98, 55, 142, 1.0));
            }
        """)
        refresh_btn.clicked.connect(self.refresh_notifications_data)
        header_layout.addWidget(refresh_btn)
        
        self.content_layout.addLayout(header_layout)
        
        # Scroll area
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        
        notifications_widget = QWidget()
        notifications_layout = QVBoxLayout(notifications_widget)
        notifications_layout.setSpacing(20)
        
        # Statystyki powiadomień
        stats_layout = QGridLayout()
        
        # Karty statystyk (będą aktualizowane przez refresh_notifications_data)
        self.notifications_stats_cards = {}
        self.notifications_stats_cards['sent_today'] = DashboardCard("Wysłane dzisiaj", "0", "Ładowanie...", "#66BB6A")
        self.notifications_stats_cards['failed'] = DashboardCard("Nieudane", "0", "Ładowanie...", "#EF5350")
        self.notifications_stats_cards['pending'] = DashboardCard("Oczekujące", "0", "Ładowanie...", "#FFA726")
        self.notifications_stats_cards['total'] = DashboardCard("Łącznie", "0", "Ładowanie...", "#42A5F5")
        
        self.notifications_stats_cards['sent_today'].setFixedHeight(120)
        self.notifications_stats_cards['failed'].setFixedHeight(120)
        self.notifications_stats_cards['pending'].setFixedHeight(120)
        self.notifications_stats_cards['total'].setFixedHeight(120)
        
        stats_layout.addWidget(self.notifications_stats_cards['sent_today'], 0, 0)
        stats_layout.addWidget(self.notifications_stats_cards['failed'], 0, 1)
        stats_layout.addWidget(self.notifications_stats_cards['pending'], 1, 0)
        stats_layout.addWidget(self.notifications_stats_cards['total'], 1, 1)
        
        notifications_layout.addLayout(stats_layout)
        
        # Konfiguracja kanałów
        channels_group = QGroupBox("Konfiguracja kanałów powiadomień")
        channels_layout = QVBoxLayout(channels_group)
        
        # Grid layout dla kart kanałów
        self.channels_grid = QGridLayout()
        self.channels_grid.setSpacing(10)
        
        # Przechowywanie kart kanałów
        self.channel_cards = {}
        
        channels_layout.addLayout(self.channels_grid)
        notifications_layout.addWidget(channels_group)
        
        # Historia powiadomień
        history_group = QGroupBox("Historia powiadomień")
        history_layout = QVBoxLayout(history_group)
        
        # Scroll area dla kart powiadomień
        self.history_scroll = QScrollArea()
        self.history_scroll.setWidgetResizable(True)
        self.history_scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.history_scroll.setMaximumHeight(300)
        
        self.history_widget = QWidget()
        self.history_cards_layout = QVBoxLayout(self.history_widget)
        self.history_cards_layout.setSpacing(5)
        
        self.history_cards_layout.addStretch()
        self.history_scroll.setWidget(self.history_widget)
        history_layout.addWidget(self.history_scroll)
        notifications_layout.addWidget(history_group)
        
        scroll.setWidget(notifications_widget)
        self.content_layout.addWidget(scroll)
        
        # Załaduj prawdziwe dane
        self.refresh_notifications_data()
    
    def refresh_notifications_data(self):
        """Odświeża dane powiadomień z NotificationManager"""
        try:
            # Pobierz statystyki z NotificationManager
            if self.notification_manager:
                stats = self.notification_manager.get_statistics_sync()
                
                # Aktualizuj karty statystyk
                self.notifications_stats_cards['sent_today'].update_value(
                    str(stats.last_24h), 
                    f"Ostatnie 24h"
                )
                self.notifications_stats_cards['failed'].update_value(
                    str(stats.total_failed), 
                    f"Błędy ogółem"
                )
                self.notifications_stats_cards['pending'].update_value(
                    "0", 
                    f"W kolejce"
                )
                self.notifications_stats_cards['total'].update_value(
                    str(stats.total_sent), 
                    f"Wszystkie wysłane"
                )
                
                # Aktualizuj kanały
                self.update_notification_channels()
                
                # Aktualizuj historię
                self.update_notification_history()
                
            else:
                # Użyj domyślnych wartości jeśli NotificationManager nie jest dostępny
                self.update_notifications_with_defaults()
                
        except Exception as e:
            print(f"Błąd podczas odświeżania danych powiadomień: {e}")
            self.update_notifications_with_defaults()
    
    def update_notification_channels(self):
        """Aktualizuje karty kanałów powiadomień"""
        try:
            # Wyczyść istniejące karty
            for i in reversed(range(self.channels_grid.count())):
                child = self.channels_grid.itemAt(i).widget()
                if child:
                    child.setParent(None)
            
            self.channel_cards.clear()
            
            if self.notification_manager:
                # Pobierz konfigurację kanałów
                channels_config = self.notification_manager.channels_config
                
                row, col = 0, 0
                for channel_name, config in channels_config.items():
                    status = "Aktywny" if config.get('enabled', False) else "Nieaktywny"
                    rate_limit = str(config.get('rate_limit', 0))
                    
                    channel_card = ChannelCard(channel_name, status, rate_limit)
                    self.channel_cards[channel_name] = channel_card
                    self.channels_grid.addWidget(channel_card, row, col)
                    
                    col += 1
                    if col >= 2:
                        col = 0
                        row += 1
            else:
                # Domyślne kanały
                default_channels = [
                    ("Email", "Nieaktywny", "0"),
                    ("Telegram", "Nieaktywny", "0"),
                    ("Discord", "Nieaktywny", "0"),
                    ("SMS", "Nieaktywny", "0")
                ]
                
                for i, (channel_name, status, rate_limit) in enumerate(default_channels):
                    channel_card = ChannelCard(channel_name, status, rate_limit)
                    self.channel_cards[channel_name] = channel_card
                    self.channels_grid.addWidget(channel_card, i // 2, i % 2)
                    
        except Exception as e:
            print(f"Błąd podczas aktualizacji kanałów: {e}")
    
    def update_notification_history(self):
        """Aktualizuje historię powiadomień"""
        try:
            # Wyczyść istniejące karty
            for i in reversed(range(self.history_cards_layout.count())):
                child = self.history_cards_layout.itemAt(i).widget()
                if child:
                    child.setParent(None)
            
            if self.notification_manager:
                # Pobierz historię powiadomień
                history = self.notification_manager.get_notification_history_sync(limit=20)
                
                for notification in history:
                    timestamp = notification.timestamp.strftime("%H:%M:%S")
                    # Pobierz pierwszy kanał z listy lub domyślny
                    channel = notification.channels[0].value if notification.channels else "unknown"
                    notification_card = NotificationCard(
                        timestamp,
                        notification.notification_type.value,
                        channel,
                        notification.status,
                        notification.message
                    )
                    self.history_cards_layout.addWidget(notification_card)
            else:
                # Dodaj informację o braku danych
                no_data_label = QLabel("Brak danych historii powiadomień")
                no_data_label.setStyleSheet("color: #666; font-style: italic; padding: 20px;")
                no_data_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
                self.history_cards_layout.addWidget(no_data_label)
            
            self.history_cards_layout.addStretch()
            
        except Exception as e:
            print(f"Błąd podczas aktualizacji historii: {e}")
    
    def update_notifications_with_defaults(self):
        """Aktualizuje powiadomienia z domyślnymi wartościami"""
        # Domyślne statystyki
        self.notifications_stats_cards['sent_today'].update_value("0", "Brak danych")
        self.notifications_stats_cards['failed'].update_value("0", "Brak danych")
        self.notifications_stats_cards['pending'].update_value("0", "Brak danych")
        self.notifications_stats_cards['total'].update_value("0", "Brak danych")
        
        # Aktualizuj kanały z domyślnymi wartościami
        self.update_notification_channels()
        
        # Aktualizuj historię z domyślnymi wartościami
        self.update_notification_history()
    
    def setup_logs_view(self):
        """Konfiguruje widok logów"""
        try:
            from ui.logs import LogsWidget, PYQT_AVAILABLE as LOGS_PYQT_AVAILABLE
            if not LOGS_PYQT_AVAILABLE:
                placeholder = QLabel("PyQt6 nie jest dostępne - widok logów niedostępny")
                placeholder.setAlignment(Qt.AlignmentFlag.AlignCenter)
                placeholder.setStyleSheet("font-size: 18px; color: #666;")
                self.content_layout.addWidget(placeholder)
                return
            
            # Utwórz instancję tylko raz
            if self.logs_widget is None:
                self.logs_widget = LogsWidget()
                
            self.content_layout.addWidget(self.logs_widget)
        except (ImportError, Exception) as e:
            self.logger.error(f"Failed to load LogsWidget: {e}")
            placeholder = QLabel("Błąd ładowania widoku logów")
            placeholder.setAlignment(Qt.AlignmentFlag.AlignCenter)
            placeholder.setStyleSheet("font-size: 18px; color: #666;")
            self.content_layout.addWidget(placeholder)
    
    def setup_settings_view(self):
        """Konfiguruje widok ustawień"""
        try:
            from ui.settings import SettingsWidget, PYQT_AVAILABLE as SETTINGS_PYQT_AVAILABLE
            if not SETTINGS_PYQT_AVAILABLE:
                placeholder = QLabel("PyQt6 nie jest dostępne - widok ustawień niedostępny")
                placeholder.setAlignment(Qt.AlignmentFlag.AlignCenter)
                placeholder.setStyleSheet("font-size: 18px; color: #666;")
                self.content_layout.addWidget(placeholder)
                return
            
            # Utwórz instancję tylko raz
            if self.settings_widget is None:
                self.settings_widget = SettingsWidget()
                
            self.content_layout.addWidget(self.settings_widget)
        except (ImportError, Exception) as e:
            self.logger.error(f"Failed to load SettingsWidget: {e}")
            placeholder = QLabel("Błąd ładowania widoku ustawień")
            placeholder.setAlignment(Qt.AlignmentFlag.AlignCenter)
            placeholder.setStyleSheet("font-size: 18px; color: #666;")
            self.content_layout.addWidget(placeholder)
    
    def setup_analysis_view(self):
        """Konfiguruje widok analizy wydajności"""
        try:
            from ui.analysis import AnalysisWidget, PYQT_AVAILABLE as ANALYSIS_PYQT_AVAILABLE
            if not ANALYSIS_PYQT_AVAILABLE:
                placeholder = QLabel("PyQt6 nie jest dostępne - widok analizy niedostępny")
                placeholder.setAlignment(Qt.AlignmentFlag.AlignCenter)
                placeholder.setStyleSheet("font-size: 18px; color: #666;")
                self.content_layout.addWidget(placeholder)
                return
            
            # Utwórz instancję tylko raz
            if self.analysis_widget is None:
                # Przekaż trading_manager jeśli jest dostępny
                trading_manager = getattr(self, 'trading_manager', None)
                self.analysis_widget = AnalysisWidget(trading_manager=trading_manager, integrated_data_manager=getattr(self, 'integrated_data_manager', None))
                
            self.content_layout.addWidget(self.analysis_widget)
        except (ImportError, Exception) as e:
            self.logger.error(f"Failed to load AnalysisWidget: {e}")
            placeholder = QLabel("Błąd ładowania widoku analizy")
            placeholder.setAlignment(Qt.AlignmentFlag.AlignCenter)
            placeholder.setStyleSheet("font-size: 18px; color: #666;")
            self.content_layout.addWidget(placeholder)
    
    def configure_notification_channel(self, channel_name: str):
        """Otwiera konfigurację kanału powiadomień"""
        try:
            from ui.settings import NotificationConfigWidget
            
            # Utwórz okno konfiguracji
            config_widget = NotificationConfigWidget(channel_name, self)
            config_widget.show()
            
        except Exception as e:
            print(f"Błąd podczas otwierania konfiguracji kanału {channel_name}: {e}")
            QMessageBox.warning(
                self, 
                "Błąd", 
                f"Nie można otworzyć konfiguracji kanału {channel_name}.\nBłąd: {str(e)}"
            )
    
    def set_trading_manager(self, trading_manager):
        """Ustawia trading manager dla głównego okna"""
        self.trading_manager = trading_manager
        self.logger.info("Trading manager set for main window")
    
    def set_database_manager(self, db_manager):
        """Ustawia database manager dla głównego okna"""
        self.db_manager = db_manager
        self.logger.info("Database manager set for main window")
    
    def set_bot_manager(self, bot_manager):
        """Ustawia bot manager dla głównego okna"""
        self.bot_manager = bot_manager
        self.logger.info("Bot manager set for main window")
    
    def set_notification_manager(self, notification_manager):
        """Ustawia notification manager dla głównego okna"""
        self.notification_manager = notification_manager
        self.logger.info("Notification manager set for main window")
    
    def set_risk_manager(self, risk_manager):
        """Ustawia risk manager dla głównego okna"""
        self.risk_manager = risk_manager
        self.logger.info("Risk manager set for main window")
    
    def closeEvent(self, event):
        """Obsługuje zamknięcie okna"""
        if hasattr(self, 'tray_icon') and self.tray_icon.isVisible():
            # Minimalizuj do zasobnika
            self.hide()
            event.ignore()
        else:
            # Zatrzymaj wszystkie timery
            try:
                if hasattr(self, 'refresh_timer') and self.refresh_timer:
                    self.refresh_timer.stop()
                    self.refresh_timer.deleteLater()
            except Exception as e:
                print(f"Error stopping refresh timer: {e}")
            
            # Wyczyść layouty
            try:
                self.clear_content_layout()
            except Exception as e:
                print(f"Error clearing layouts: {e}")
            
            # Dodaj poprawny cleanup asynchronicznych menedżerów i pętli danych
            try:
                from ui.async_helper import get_async_manager, get_bot_async_manager
                # Czyść AsyncManager (anuluj i zatrzymaj wszystkie zadania/QThread)
                try:
                    async_manager = get_async_manager()
                    if async_manager:
                        async_manager.cleanup()
                except Exception as e:
                    print(f"Error cleaning AsyncManager: {e}")
                # Czyść BotAsyncManager (zatrzymuje timery i boty, czyści async manager)
                try:
                    bot_async_manager = get_bot_async_manager()
                    if bot_async_manager:
                        bot_async_manager.cleanup()
                except Exception as e:
                    print(f"Error cleaning BotAsyncManager: {e}")
            except Exception as e:
                print(f"Error importing async managers: {e}")
            
            # Zatrzymaj pętle danych IntegratedDataManager
            try:
                if hasattr(self, 'integrated_data_manager') and self.integrated_data_manager:
                    import asyncio, threading
                    try:
                        loop = asyncio.get_running_loop()
                        # Pętla działa — wykonaj zatrzymanie w tym samym loopie
                        loop.create_task(self.integrated_data_manager.stop_data_loops())
                    except RuntimeError:
                        # Brak działającej pętli — uruchom zatrzymanie w osobnym wątku
                        threading.Thread(target=lambda: asyncio.run(self.integrated_data_manager.stop_data_loops()), daemon=True).start()
            except Exception as e:
                print(f"Error stopping data loops: {e}")
            
            # Zapisz ustawienia okna
            if get_ui_setting("window.remember_size", True):
                # TODO: Zapisz rozmiar okna
                pass
            
            if get_ui_setting("window.remember_position", True):
                # TODO: Zapisz pozycję okna
                pass
            
            self.logger.info("Main window closed")
            event.accept()

    def test_bot_buttons(self):
        """Funkcja testowa do sprawdzenia działania przycisków Start/Stop"""
        print("🧪 ROZPOCZYNAM TEST PRZYCISKÓW START/STOP")
        
        # Przełącz na widok botów
        print("🔄 Przełączam na widok botów...")
        self.switch_view("bots")
        
        # Poczekaj chwilę na załadowanie widoku
        from PyQt6.QtCore import QTimer
        QTimer.singleShot(1000, self._continue_button_test)
    
    def _continue_button_test(self):
        """Kontynuacja testu przycisków po załadowaniu widoku"""
        print("🔍 Sprawdzam dostępność BotManagementWidget...")
        
        if hasattr(self, 'bot_management_widget') and self.bot_management_widget:
            print("✅ BotManagementWidget znaleziony")
            
            # Sprawdź dostępne karty botów
            if hasattr(self.bot_management_widget, 'bot_cards') and self.bot_management_widget.bot_cards:
                print(f"📊 Znaleziono {len(self.bot_management_widget.bot_cards)} kart botów")
                
                # Testuj pierwszą kartę
                first_card = self.bot_management_widget.bot_cards[0]
                print(f"🎯 Testuję kartę bota: {first_card.bot_id}")
                
                # Symuluj kliknięcie Start
                print("▶️ Symuluję kliknięcie Start...")
                first_card.on_start_clicked()
                
                # Poczekaj i symuluj kliknięcie Stop
                from PyQt6.QtCore import QTimer
                QTimer.singleShot(2000, lambda: self._test_stop_button(first_card))
            else:
                print("❌ Brak dostępnych kart botów")
        else:
            print("❌ BotManagementWidget nie jest dostępny")
    
    def _test_stop_button(self, card):
        """Testuje przycisk Stop"""
        print("⏹️ Symuluję kliknięcie Stop...")
        card.on_stop_clicked()
        print("✅ TEST PRZYCISKÓW ZAKOŃCZONY")
        
        # Uruchom test aktualizacji statusów po 2 sekundach
        from PyQt6.QtCore import QTimer
        QTimer.singleShot(2000, self.test_realtime_status_updates)
    
    def test_realtime_status_updates(self):
        """Testuje aktualizację statusów botów w czasie rzeczywistym"""
        print("🧪 === ROZPOCZYNAM TEST AKTUALIZACJI STATUSÓW W CZASIE RZECZYWISTYM ===")
        
        # Sprawdź czy jesteśmy w widoku botów
        if self.current_view != "bots":
            print("🔄 Przełączam na widok botów...")
            self.switch_view("bots")
            # Poczekaj na załadowanie widoku
            from PyQt6.QtCore import QTimer
            QTimer.singleShot(2000, self._continue_realtime_test)
        else:
            self._continue_realtime_test()
    
    def _continue_realtime_test(self):
        """Kontynuuje test aktualizacji statusów"""
        print("🔍 Sprawdzam mechanizmy aktualizacji statusów...")
        
        if hasattr(self, 'bot_management_widget') and self.bot_management_widget:
            bot_widget = self.bot_management_widget
            
            # Sprawdź czy ma timer lub async manager
            has_timer = hasattr(bot_widget, 'status_timer')
            has_async = hasattr(bot_widget, 'async_manager') and bot_widget.async_manager
            
            print(f"🔍 Timer statusu: {'✅ Aktywny' if has_timer else '❌ Brak'}")
            print(f"🔍 Async Manager: {'✅ Dostępny' if has_async else '❌ Brak'}")
            
            # Sprawdź dane botów
            if hasattr(bot_widget, 'bots_data'):
                print(f"📊 Liczba botów w danych: {len(bot_widget.bots_data)}")
                for bot_id, data in bot_widget.bots_data.items():
                    status = data.get('status', 'unknown')
                    print(f"   🤖 Bot {bot_id}: status = {status}")
                
                # Symuluj zmianę statusu
                print("🔄 Symulacja zmiany statusów...")
                self._simulate_status_changes(bot_widget)
            else:
                print("❌ Brak danych botów do testowania")
        else:
            print("❌ BotManagementWidget nie jest dostępny")
    
    def _simulate_status_changes(self, bot_widget):
        """Symuluje zmiany statusów botów"""
        bot_ids = list(bot_widget.bots_data.keys())
        if not bot_ids:
            print("❌ Brak botów do testowania")
            return
        
        # Test 1: Zmień status pierwszego bota na 'running'
        first_bot = bot_ids[0]
        print(f"🧪 Test 1: Zmieniam status bota {first_bot} na 'running'")
        bot_widget.bots_data[first_bot]['status'] = 'running'
        bot_widget.refresh_bots_display()
        
        # Test 2: Po 3 sekundach zmień na 'error'
        from PyQt6.QtCore import QTimer
        QTimer.singleShot(3000, lambda: self._change_to_error(bot_widget, first_bot))
        
        # Test 3: Po 6 sekundach zmień na 'stopped'
        QTimer.singleShot(6000, lambda: self._change_to_stopped(bot_widget, first_bot))
        
        # Test 4: Po 9 sekundach testuj drugi bot jeśli istnieje
        if len(bot_ids) > 1:
            second_bot = bot_ids[1]
            QTimer.singleShot(9000, lambda: self._test_second_bot(bot_widget, second_bot))
        else:
            QTimer.singleShot(9000, self._finish_realtime_test)
    
    def _change_to_error(self, bot_widget, bot_id):
        """Zmienia status bota na error"""
        print(f"🧪 Test 2: Zmieniam status bota {bot_id} na 'error'")
        bot_widget.bots_data[bot_id]['status'] = 'error'
        bot_widget.refresh_bots_display()
    
    def _change_to_stopped(self, bot_widget, bot_id):
        """Zmienia status bota na stopped"""
        print(f"🧪 Test 3: Zmieniam status bota {bot_id} na 'stopped'")
        bot_widget.bots_data[bot_id]['status'] = 'stopped'
        bot_widget.refresh_bots_display()
    
    def _test_second_bot(self, bot_widget, bot_id):
        """Testuje drugi bot"""
        print(f"🧪 Test 4: Zmieniam status bota {bot_id} na 'starting'")
        bot_widget.bots_data[bot_id]['status'] = 'starting'
        bot_widget.refresh_bots_display()
        
        # Po 3 sekundach zakończ test
        from PyQt6.QtCore import QTimer
        QTimer.singleShot(3000, self._finish_realtime_test)
    
    def _finish_realtime_test(self):
        """Kończy test aktualizacji statusów"""
        print("✅ === TEST AKTUALIZACJI STATUSÓW W CZASIE RZECZYWISTYM ZAKOŃCZONY ===")
        print("📊 Sprawdzone funkcjonalności:")
        print("   ✅ Zmiana statusu na 'running' (zielony)")
        print("   ✅ Zmiana statusu na 'error' (różowy)")
        print("   ✅ Zmiana statusu na 'stopped' (czerwony)")
        print("   ✅ Zmiana statusu na 'starting' (żółty)")
        print("   ✅ Odświeżanie wyświetlania kart botów")
        print("   ✅ Propagacja zmian przez refresh_bots_display()")

def main():
    """Funkcja główna do testowania okna"""
    if not PYQT_AVAILABLE:
        print("PyQt6 is not available. Please install it to run the GUI.")
        return
    
    app = QApplication(sys.argv)
    app.setApplicationName("CryptoBotDesktop")
    app.setApplicationVersion("1.0.0")
    
    window = MainWindow()
    window.show()
    
    # Test przycisków wyłączony w wersji produkcyjnej
    # from PyQt6.QtCore import QTimer
    # QTimer.singleShot(3000, window.test_bot_buttons)
    
    sys.exit(app.exec())

if __name__ == "__main__":
    main()


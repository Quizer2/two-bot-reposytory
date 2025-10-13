
from __future__ import annotations

try:
    from PyQt6.QtWidgets import (
        QMainWindow,
        QWidget,
        QTabWidget,
        QVBoxLayout,
        QHBoxLayout,
        QLabel,
        QDockWidget,
        QPushButton,
        QScrollArea,
        QFrame,
        QGridLayout,
        QSizePolicy,
        QTableWidget,
        QTableWidgetItem,
        QHeaderView,
    )
    from PyQt6.QtCore import Qt, QTimer, QPropertyAnimation, QEasingCurve, QRect
    from PyQt6.QtGui import QFont, QBrush, QColor
except Exception as exc:  # pragma: no cover - zależne od środowiska (np. brak libGL)
    from utils.pyqt_stubs import install_pyqt_stubs

    install_pyqt_stubs(force=True)
    from PyQt6.QtWidgets import (
        QMainWindow,
        QWidget,
        QTabWidget,
        QVBoxLayout,
        QHBoxLayout,
        QLabel,
        QDockWidget,
        QPushButton,
        QScrollArea,
        QFrame,
        QGridLayout,
        QSizePolicy,
        QTableWidget,
        QTableWidgetItem,
        QHeaderView,
    )
    from PyQt6.QtCore import Qt, QTimer, QPropertyAnimation, QEasingCurve, QRect
    from PyQt6.QtGui import QFont, QBrush, QColor

from utils.logger import get_logger
from utils.config_manager import get_config_manager
from ui.async_helper import get_async_manager

# Import additional widgets for tabs
from ui.updated_bot_management_widget import UpdatedBotManagementWidget
from ui.updated_portfolio_widget import UpdatedPortfolioWidget
from ui.analysis import AnalysisWidget

# Inicjalizuj logger przed importami
logger = get_logger(__name__)

class DashboardCard(QWidget):
    """Nowoczesna karta na dashboardzie z informacjami"""
    
    def __init__(self, title: str, value: str = "", subtitle: str = "",
                 color: str = "#667eea", parent=None):
        try:
            super().__init__(parent)
            self.title = title
            self.value = value
            self.subtitle = subtitle
            self.color = color
            
            self.setup_ui()
            self.apply_style()
        except Exception as e:
            logger.error(f"Error initializing DashboardCard: {e}")
    
    def setup_ui(self):
        """Konfiguracja nowoczesnego interfejsu karty z responsywnością"""
        self.setObjectName("dashboardCard")
        self.setMinimumSize(200, 140)
        self.setMaximumSize(300, 180)
        # Ustaw elastyczną politykę rozmiaru
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
        """Aplikuje nowoczesny styl do karty dashboardu."""
        try:
            # Styl ogólny karty z delikatnym gradientem opartym o color
            self.setStyleSheet(f"""
                QWidget#dashboardCard {{
                    background: qlineargradient(x1:0, y1:0, x2:1, y2:1,
                        stop:0 rgba(255,255,255,0.06), stop:1 rgba(255,255,255,0.02));
                    border: 1px solid rgba(255,255,255,0.08);
                    border-radius: 14px;
                }}
                QLabel#cardTitle {{
                    font-size: 14px;
                    font-weight: 600;
                    color: #e0e0e0;
                }}
                QLabel#cardValue {{
                    font-size: 22px;
                    font-weight: 700;
                    color: #ffffff;
                }}
                QLabel#cardSubtitle {{
                    font-size: 12px;
                    color: #a0a0a0;
                }}
            """)
        except Exception as e:
            logger.warning(f"DashboardCard.apply_style failed: {e}")
    
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

# DashboardCard jest teraz zdefiniowana lokalnie
DASHBOARD_COMPONENTS_AVAILABLE = True
logger.info("Dashboard components available locally")

try:
    from ui.flow_layout import FlowLayout
    FLOW_LAYOUT_AVAILABLE = True
    logger.info("FlowLayout imported successfully")
except ImportError as e:
    FLOW_LAYOUT_AVAILABLE = False
    logger.warning(f"FlowLayout not available: {e}")

try:
    from ui.styles import get_theme_style, DARK_THEME, COLORS
    STYLES_AVAILABLE = True
    logger.info("Styles imported successfully")
except ImportError as e:
    STYLES_AVAILABLE = False
    logger.warning(f"Styles not available: {e}")

class UpdatedMainWindow(QMainWindow):
    """Minimal, clean main window that keeps compatibility and loads dashboard extensions."""
    def __init__(self, integrated_data_manager=None, parent=None):
        super().__init__(parent)
        self.integrated_data_manager = integrated_data_manager
        self.config_manager = get_config_manager()
        self._is_closing = False
        
        # Async manager + bufor danych
        self.async_manager = get_async_manager()
        self.async_manager.task_finished.connect(self._on_async_task_finished)
        self.async_manager.task_error.connect(self._on_async_task_error)
        self._latest_trades = []
        
        # Okresowe odświeżanie
        self.refresh_timer = QTimer(self)
        self.refresh_timer.setInterval(15000)
        self.refresh_timer.timeout.connect(self.refresh_data)
        self.refresh_timer.start()
        
        # Subskrypcje aktualizacji z IntegratedDataManager
        try:
            if self.integrated_data_manager is not None:
                self.integrated_data_manager.subscribe_to_ui_updates('system_status_update', self._apply_system_status)
                self.integrated_data_manager.subscribe_to_ui_updates('portfolio_update', self._on_portfolio_update)
                self.integrated_data_manager.subscribe_to_ui_updates('bot_status_update', self._on_bot_status_update)
        except Exception as e:
            logger.warning(f"Subskrypcja aktualizacji UI nie powiodła się: {e}")
        
        # Ustawienia okna
        self.setWindowTitle("CryptoBot Desktop - Trading Application")
        self.setup_window_properties()
        
        # Główny widget
        central = QWidget(self)
        self.setCentralWidget(central)

        # Layout główny
        self.tabs = QTabWidget(central)
        # Ensure tabs are visible and consistently styled
        try:
            self.tabs.setDocumentMode(False)
            self.tabs.setTabPosition(QTabWidget.TabPosition.North)
            self.tabs.setUsesScrollButtons(True)
            self.tabs.setMovable(False)
            self.tabs.setTabShape(QTabWidget.TabShape.Rounded)
            # Wymuszenie braku autoukrywania i pełnej ekspansji
            try:
                self.tabs.setTabBarAutoHide(False)
            except Exception:
                pass
            try:
                self.tabs.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
            except Exception:
                pass
            tb = self.tabs.tabBar()
            tb.setVisible(True)
            tb.setMinimumHeight(36)
            tb.setExpanding(False)
            # Ensure tab texts are not elided/hidden
            try:
                tb.setElideMode(Qt.TextElideMode.ElideNone)
            except Exception:
                pass
            try:
                tb.setAutoHide(False)
            except Exception:
                pass
        except Exception as e:
            logger.warning(f"TabWidget configuration fallback: {e}")
        layout = QVBoxLayout(central)
        layout.setContentsMargins(10, 10, 10, 10)
        layout.addWidget(self.tabs)

        # Tworzenie zakładek z zawartością
        self.setup_tabs()
        
        # Upewnij się, że zakładka Overview jest aktywna
        try:
            self.tabs.setCurrentIndex(0)
            logger.info(f"Tabs count: {self.tabs.count()}, current index: {self.tabs.currentIndex()}, current text: {self.tabs.tabText(self.tabs.currentIndex())}")
        except Exception as e:
            logger.warning(f"Setting current tab failed: {e}")

        # Install optional extensions (risk metrics, correlations)
        try:
            from ui import dashboard_extensions
            dashboard_extensions.install(self)
        except Exception as e:
            logger.info(f"Extensions not installed: {e}")

        # Ustawienie stylów
        self.setup_styles()
        # Nadpisanie lokalnych styli dla zakładek, aby zapewnić widoczność i kontrast
        try:
            self.tabs.setStyleSheet(
                "QTabWidget::pane { border: 1px solid #2a2a2a; border-radius: 8px; background: #1a1a1a; }\n"
                "QTabWidget::tab-bar { alignment: left; }\n"
                "QTabBar::tab { background: #2a2a2a; color: #eeeeee; padding: 10px 16px; margin-right: 2px; border-top-left-radius: 8px; border-top-right-radius: 8px; font-weight: 600; min-height: 32px; min-width: 80px; }\n"
                "QTabBar::tab:selected { background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #667eea, stop:1 #764ba2); color: white; }\n"
                "QTabBar::tab:hover:!selected { background: rgba(102,126,234,0.35); color: white; }\n"
                "QTabBar { qproperty-drawBase: 1; }"
            )
            logger.info("Applied local tab styles override for visibility")
        except Exception as e:
            logger.warning(f"Failed to apply local tab styles: {e}")
        
        logger.info("UpdatedMainWindow initialized successfully")

    # --- Obsługa wyników zadań asynchronicznych ---
    def _on_async_task_finished(self, task_id: str, result):
        try:
            if task_id == 'dashboard_refresh':
                self._apply_dashboard_data(result or {})
            elif task_id == 'recent_trades_refresh':
                self._latest_trades = result or []
                self.populate_trades_table()
        except Exception as e:
            logger.error(f"Błąd obsługi zakończenia zadania {task_id}: {e}")

    def _on_async_task_error(self, task_id: str, error: str):
        logger.error(f"Async task '{task_id}' error: {error}")

    def _apply_dashboard_data(self, data: dict):
        try:
            portfolio = data.get('portfolio', {})
            bots = data.get('bots', {})
            # Portfolio value + daily change
            if hasattr(self, 'portfolio_card'):
                total_val = portfolio.get('total_value', 0.0)
                daily_pct = portfolio.get('daily_change_percent', 0.0)
                self.portfolio_card.update_value(f"${total_val:,.2f}", f"{daily_pct:+.2f}% (24h)")
            # Daily P&L
            if hasattr(self, 'daily_pnl_card'):
                daily = portfolio.get('daily_change', 0.0)
                daily_pct = portfolio.get('daily_change_percent', 0.0)
                self.daily_pnl_card.update_value(f"{daily:+,.2f}", f"{daily_pct:+.2f}%")
            # Active bots
            if hasattr(self, 'active_bots_card'):
                active = bots.get('active', 0)
                total = bots.get('total', 0)
                self.active_bots_card.update_value(str(active), f"{total} łącznie")
            # Total P&L (jeśli karta istnieje)
            if hasattr(self, 'total_pnl_card'):
                total_pnl = portfolio.get('profit_loss', 0.0)
                total_pnl_pct = portfolio.get('profit_loss_percent', 0.0)
                self.total_pnl_card.update_value(f"{total_pnl:+,.2f}", f"ROI {total_pnl_pct:+.2f}%")
        except Exception as e:
            logger.error(f"Błąd aktualizacji kart dashboardu: {e}")

    def _apply_system_status(self, status):
        try:
            # Znormalizuj status do słownika dla kompatybilności
            if not isinstance(status, dict):
                try:
                    from dataclasses import asdict, is_dataclass
                    if is_dataclass(status):
                        status = asdict(status)
                    else:
                        status = {
                            'active_bots': getattr(status, 'active_bots', 0),
                            'total_bots': getattr(status, 'total_bots', 0)
                        }
                except Exception:
                    status = {}
            
            if hasattr(self, 'active_bots_card') and status:
                active = status.get('active_bots', 0)
                total = status.get('total_bots', 0)
                self.active_bots_card.update_value(str(active), f"{total} łącznie")
        except Exception as e:
            logger.warning(f"Nie udało się zastosować statusu systemu: {e}")
    
    def _on_portfolio_update(self, data):
        try:
            if not getattr(self, '_is_closing', False):
                self.refresh_data()
        except Exception:
            pass
    
    def _on_bot_status_update(self, data):
        try:
            if not getattr(self, '_is_closing', False):
                self.refresh_data()
        except Exception:
            pass

    def setup_window_properties(self):
        """Ustawia właściwości okna - rozmiar, pozycję itp."""
        try:
            # Pobierz ustawienia z konfiguracji
            ui_config = self.config_manager.get_config().get('ui', {})
            window_config = ui_config.get('window', {})
            
            # Domyślne rozmiary
            default_width = window_config.get('default_width', 1200)
            default_height = window_config.get('default_height', 800)
            min_width = window_config.get('min_width', 800)
            min_height = window_config.get('min_height', 600)
            
            # Ustaw rozmiary
            self.resize(default_width, default_height)
            self.setMinimumSize(min_width, min_height)
            
            # Wyśrodkuj okno na ekranie
            screen = self.screen().availableGeometry()
            x = (screen.width() - default_width) // 2
            y = (screen.height() - default_height) // 2
            self.move(x, y)
            
            logger.info(f"Window properties set: {default_width}x{default_height}, min: {min_width}x{min_height}")
            
        except Exception as e:
            logger.error(f"Error setting window properties: {e}")
            # Fallback do domyślnych wartości
            self.resize(1200, 800)
            self.setMinimumSize(800, 600)

    def setup_tabs(self):
        """Tworzy zakładki z podstawową zawartością"""
        try:
            # Zakładka Overview
            overview_widget = self.create_overview_tab()
            self.tabs.addTab(overview_widget, "📊 Dashboard")
            
            # Zakładka Portfolio
            try:
                if self.integrated_data_manager is not None:
                    portfolio_widget = UpdatedPortfolioWidget(self.integrated_data_manager, self)
                else:
                    portfolio_widget = QWidget()
                self.tabs.addTab(portfolio_widget, "💼 Portfolio")
            except Exception as e:
                logger.error(f"Error initializing Portfolio widget: {e}")
                self.tabs.addTab(QWidget(), "💼 Portfolio")
            
            # Zakładka Bots
            try:
                if self.integrated_data_manager is not None:
                    bots_widget = UpdatedBotManagementWidget(self.integrated_data_manager, self)
                else:
                    bots_widget = self.create_bots_tab()
                self.tabs.addTab(bots_widget, "🤖 Bots")
            except Exception as e:
                logger.error(f"Error initializing Bot Management widget: {e}")
                self.tabs.addTab(self.create_bots_tab(), "🤖 Bots")
            
            # Zakładka Analysis
            try:
                trading_manager = getattr(self, 'trading_manager', None)
                analysis_widget = AnalysisWidget(parent=self, trading_manager=trading_manager, integrated_data_manager=getattr(self, 'integrated_data_manager', None))
                self.tabs.addTab(analysis_widget, "📈 Analysis")
            except Exception as e:
                logger.error(f"Error initializing AnalysisWidget: {e}")
                strategies_widget = self.create_strategies_tab()
                self.tabs.addTab(strategies_widget, "📈 Strategies")
            
            logger.info("Tabs created successfully")
            
        except Exception as e:
            logger.error(f"Error creating tabs: {e}")

    def create_overview_tab(self):
        """Tworzy zawartość zakładki Overview z nowoczesnym dashboardem"""
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setSpacing(20)
        layout.setContentsMargins(20, 20, 20, 20)
        
        # Nagłówek z przyciskiem odświeżania
        header_layout = QHBoxLayout()
        
        header = QLabel("📊 Dashboard")
        header.setFont(QFont("Arial", 18, QFont.Weight.Bold))
        header.setObjectName("sectionTitle")
        header_layout.addWidget(header)
        
        header_layout.addStretch()
        
        # Przycisk odświeżania
        refresh_btn = QPushButton("🔄 Odśwież")
        refresh_btn.setObjectName("actionButton")
        refresh_btn.clicked.connect(self.refresh_data)
        header_layout.addWidget(refresh_btn)
        
        layout.addLayout(header_layout)
        
        # Sekcja z kartami podsumowania
        self.setup_summary_cards(layout)
        
        # Sekcja aktywnych botów
        self.setup_active_bots_section(layout)
        
        # Sekcja ostatnich transakcji
        self.setup_recent_trades_section(layout)
        
        # Dodanie wykresów jako dodatkowe panele (docki)
        try:
            from ui.charts import create_chart_widget
            if hasattr(self, 'integrated_data_manager') and self.integrated_data_manager:
                perf_widget = create_chart_widget('performance', parent=self, integrated_data_manager=self.integrated_data_manager)
                alloc_widget = create_chart_widget('allocation', parent=self, integrated_data_manager=self.integrated_data_manager)
            else:
                perf_widget = create_chart_widget('performance', parent=self)
                alloc_widget = create_chart_widget('allocation', parent=self)
            # Zachowaj referencje do widżetów wykresów, aby umożliwić ręczne odświeżanie
            self.performance_chart_widget = perf_widget
            self.allocation_chart_widget = alloc_widget
            # Dodaj jako panele dokowane po prawej stronie
            self.add_custom_panel("Performance", perf_widget)
            self.add_custom_panel("Allocation", alloc_widget)
        except Exception as e:
            logger.warning(f"Nie udało się dodać wykresów do dashboardu: {e}")
        
        return widget

    def setup_summary_cards(self, layout):
        """Konfiguracja nowoczesnych kart podsumowania z responsywnym layoutem"""
        # Używamy lokalnie zdefiniowanych DashboardCard
        cards_frame = QFrame()
        cards_layout = QGridLayout(cards_frame)
        cards_layout.setSpacing(20)
        cards_layout.setContentsMargins(10, 10, 10, 10)
        
        # Tworzenie kart z odpowiednimi objectName dla stylów
        self.portfolio_card = DashboardCard("Wartość Portfela", "$0.00", "0.00% (24h)", "#667eea")
        self.portfolio_card.setObjectName("portfolioCard")
        self.portfolio_card.title_label.setText("Wartość Portfela")
        cards_layout.addWidget(self.portfolio_card, 0, 0)
        
        self.daily_pnl_card = DashboardCard("P&L Dzienny", "$0.00", "0.00%", "#f093fb")
        self.daily_pnl_card.setObjectName("dailyPnlCard")
        self.daily_pnl_card.title_label.setText("P&L Dzienny")
        cards_layout.addWidget(self.daily_pnl_card, 0, 1)
        
        self.active_bots_card = DashboardCard("Aktywne Boty", "0", "0 łącznie", "#4facfe")
        self.active_bots_card.setObjectName("botsCard")
        self.active_bots_card.title_label.setText("Aktywne Boty")
        cards_layout.addWidget(self.active_bots_card, 1, 0)
        
        # Zamiast karty transakcji dodajemy P&L Całkowity
        self.total_pnl_card = DashboardCard("P&L Całkowity", "$0.00", "ROI 0.00%", "#43e97b")
        self.total_pnl_card.setObjectName("totalPnlCard")
        self.total_pnl_card.title_label.setText("P&L Całkowity")
        cards_layout.addWidget(self.total_pnl_card, 1, 1)
        
        # Ustaw równe proporcje kolumn
        for i in range(2):
            cards_layout.setColumnStretch(i, 1)
        
        layout.addWidget(cards_frame)
        logger.info("Dashboard cards created successfully with local DashboardCard and proper styling")

    def setup_active_bots_section(self, layout):
        """Konfiguracja sekcji aktywnych botów"""
        # Nagłówek sekcji
        bots_header = QHBoxLayout()
        
        bots_title = QLabel("Aktywne Boty")
        bots_title.setFont(QFont("Arial", 16, QFont.Weight.Bold))
        bots_title.setStyleSheet("color: #ffffff; margin: 10px 0;")
        bots_header.addWidget(bots_title)
        
        bots_header.addStretch()
        
        new_bot_btn = QPushButton("+ Nowy Bot")
        new_bot_btn.setObjectName("actionButton")
        new_bot_btn.clicked.connect(self.create_new_bot)
        bots_header.addWidget(new_bot_btn)
        
        layout.addLayout(bots_header)
        
        # Lista botów
        self.bots_container = QWidget()
        self.bots_layout = QVBoxLayout(self.bots_container)
        self.bots_layout.setSpacing(5)
        
        # Placeholder dla botów
        placeholder = QLabel("Brak aktywnych botów. Kliknij 'Nowy Bot' aby rozpocząć.")
        placeholder.setAlignment(Qt.AlignmentFlag.AlignCenter)
        placeholder.setStyleSheet("color: #666; font-size: 14px; padding: 30px;")
        self.bots_layout.addWidget(placeholder)
        
        # Scroll area dla botów
        bots_scroll = QScrollArea()
        bots_scroll.setWidget(self.bots_container)
        bots_scroll.setWidgetResizable(True)
        bots_scroll.setMaximumHeight(200)
        bots_scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        
        layout.addWidget(bots_scroll)

    def setup_recent_trades_section(self, layout):
        """Konfiguracja sekcji ostatnich transakcji"""
        trades_title = QLabel("📊 Ostatnie Transakcje")
        trades_title.setFont(QFont("Arial", 16, QFont.Weight.Bold))
        trades_title.setStyleSheet("color: #ffffff; margin: 10px 0;")
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
        
        layout.addWidget(self.trades_table)

    def populate_trades_table(self):
        """Wypełnia tabelę danymi transakcji (z bufora lub fallback)."""
        try:
            trades = self._latest_trades if hasattr(self, '_latest_trades') and self._latest_trades else [
                { 'time': "14:32:15", 'bot': "Scalping Pro", 'pair': "BTC/USDT", 'side': "BUY",  'amount': 1250.00, 'price': 43250.50 },
                { 'time': "14:28:42", 'bot': "DCA Master",   'pair': "ETH/USDT", 'side': "SELL", 'amount': 850.75,  'price': 2680.25 },
                { 'time': "14:25:18", 'bot': "Grid Trading",  'pair': "BNB/USDT", 'side': "BUY",  'amount': 320.50,  'price': 315.80 },
                { 'time': "14:22:03", 'bot': "Momentum",      'pair': "ADA/USDT", 'side': "SELL", 'amount': 180.25,  'price': 0.485   },
            ]
            self.trades_table.setRowCount(len(trades))
            for row, tr in enumerate(trades):
                values = [
                    str(tr.get('time', '')),
                    str(tr.get('bot', '')),
                    str(tr.get('pair', '')),
                    str(tr.get('side', '')),
                    f"{tr.get('amount', 0):,.4f}",
                    f"{tr.get('price', 0):,.4f}"
                ]
                for col, v in enumerate(values):
                    item = QTableWidgetItem(v)
                    if col == 3:
                        f = item.font(); f.setBold(True); item.setFont(f)
                    self.trades_table.setItem(row, col, item)
                side = str(tr.get('side', '')).upper()
                if side == 'SELL':
                    bg = QBrush(QColor(0xF4, 0x43, 0x36, 180))
                else:
                    bg = QBrush(QColor(0x4C, 0xAF, 0x50, 140))
                for col in range(6):
                    it = self.trades_table.item(row, col)
                    if it:
                        it.setBackground(bg)
        except Exception as e:
            logger.error(f"Nie udało się wypełnić tabeli transakcji: {e}")

    def refresh_data(self):
        """Odświeża dane dashboardu asynchronicznie z IntegratedDataManager."""
        if getattr(self, '_is_closing', False):
            logger.info("Skipping refresh_data; window is closing")
            return
        logger.info("Refreshing dashboard data (async)...")
        try:
            if self.integrated_data_manager is not None:
                # Dashboard summary i transakcje w tle
                self.async_manager.run_async(self.integrated_data_manager.get_dashboard_data(), task_id='dashboard_refresh')
                self.async_manager.run_async(self.integrated_data_manager.get_recent_trades(limit=50), task_id='recent_trades_refresh')
                # Ręczne odświeżenie wykresów (jeśli istnieją)
                try:
                    if hasattr(self, 'performance_chart_widget') and self.performance_chart_widget:
                        self.performance_chart_widget.load_data()
                except Exception as e:
                    logger.warning(f"Nie udało się odświeżyć wykresu wydajności: {e}")
                try:
                    if hasattr(self, 'allocation_chart_widget') and self.allocation_chart_widget:
                        self.allocation_chart_widget.load_data()
                except Exception as e:
                    logger.warning(f"Nie udało się odświeżyć wykresu alokacji: {e}")
                # Odświeżenie paneli rozszerzeń (jeśli zainstalowane)
                try:
                    if hasattr(self, 'risk_metrics_widget') and hasattr(self.risk_metrics_widget, 'refresh'):
                        self.risk_metrics_widget.refresh()
                except Exception as e:
                    logger.warning(f"Nie udało się odświeżyć panelu ryzyka: {e}")
                try:
                    if hasattr(self, 'correlation_widget') and hasattr(self.correlation_widget, 'refresh'):
                        self.correlation_widget.refresh()
                except Exception as e:
                    logger.warning(f"Nie udało się odświeżyć panelu korelacji: {e}")
            else:
                # Fallback: przykładowe wartości
                if hasattr(self, 'portfolio_card'):
                    self.portfolio_card.update_value("$1,234.56", "+2.34% (24h)")
                if hasattr(self, 'active_bots_card'):
                    self.active_bots_card.update_value("3", "2 aktywne")
                if hasattr(self, 'daily_pnl_card'):
                    self.daily_pnl_card.update_value("+$45.67", "5 transakcji")
                if hasattr(self, 'trades_card'):
                    self.trades_card.update_value("12", "Last 24h")
                self.populate_trades_table()
        except Exception as e:
            logger.error(f"Error refreshing dashboard data: {e}")

    def create_new_bot(self):
        """Otwiera konfigurator bota i tworzy nowego bota po akceptacji"""
        try:
            from PyQt6.QtWidgets import QDialog, QMessageBox
            from ui.updated_bot_management_widget import BotConfigDialog

            dialog = BotConfigDialog(self)
            if dialog.exec() == QDialog.DialogCode.Accepted:
                config = dialog.get_config()
                if getattr(self, 'integrated_data_manager', None) is not None:
                    # Utwórz bota asynchronicznie; aktualizacje pojawią się poprzez callbacki z IntegratedDataManager
                    try:
                        self.async_manager.run_async(self.integrated_data_manager.create_bot(config), task_id='create_bot')
                    except Exception as e:
                        logger.error(f"Nie udało się uruchomić zadania tworzenia bota: {e}")
                        QMessageBox.critical(self, "Błąd", f"Nie udało się utworzyć bota: {e}")
                else:
                    QMessageBox.information(self, "Informacja", "IntegratedDataManager niedostępny. Konfiguracja nie została zapisana.")
        except Exception as e:
            logger.error(f"Create new bot error: {e}")
            try:
                from PyQt6.QtWidgets import QMessageBox
                QMessageBox.critical(self, "Błąd", f"Wystąpił błąd podczas otwierania konfiguratora bota: {e}")
            except Exception:
                pass

    def create_bots_tab(self):
        """Tworzy zawartość zakładki Bots"""
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setSpacing(20)
        layout.setContentsMargins(20, 20, 20, 20)
        
        # Nagłówek
        header_layout = QHBoxLayout()
        header = QLabel("Bot Management")
        header.setFont(QFont("Arial", 18, QFont.Weight.Bold))
        header_layout.addWidget(header)
        
        header_layout.addStretch()
        
        # Przycisk dodawania bota
        add_bot_btn = QPushButton("+ Add Bot")
        add_bot_btn.setStyleSheet("""
            QPushButton {
                background-color: #4CAF50;
                color: white;
                border: none;
                padding: 10px 20px;
                border-radius: 5px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #45a049;
            }
        """)
        add_bot_btn.clicked.connect(self.create_new_bot)
        header_layout.addWidget(add_bot_btn)
        
        layout.addLayout(header_layout)
        
        # Placeholder dla listy botów
        bots_info = QLabel("No bots configured yet.\nClick 'Add Bot' to create your first trading bot.")
        bots_info.setAlignment(Qt.AlignmentFlag.AlignCenter)
        bots_info.setStyleSheet("color: #666; font-size: 14px; padding: 50px;")
        layout.addWidget(bots_info)
        
        layout.addStretch()
        
        return widget

    def create_strategies_tab(self):
        """Tworzy zawartość zakładki Strategies"""
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setSpacing(20)
        layout.setContentsMargins(20, 20, 20, 20)
        
        # Nagłówek
        header = QLabel("Trading Strategies")
        header.setFont(QFont("Arial", 18, QFont.Weight.Bold))
        header.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(header)
        
        # Placeholder dla strategii
        strategies_info = QLabel("Strategy management coming soon.\nThis section will allow you to configure and monitor trading strategies.")
        strategies_info.setAlignment(Qt.AlignmentFlag.AlignCenter)
        strategies_info.setStyleSheet("color: #666; font-size: 14px; padding: 50px;")
        layout.addWidget(strategies_info)
        
        layout.addStretch()
        
        return widget

    def create_summary_card(self, title: str, value: str, description: str):
        """Tworzy kartę podsumowania"""
        card = QFrame()
        card.setFrameStyle(QFrame.Shape.Box)
        card.setStyleSheet("""
            QFrame {
                background-color: #f8f9fa;
                border: 1px solid #dee2e6;
                border-radius: 8px;
                padding: 15px;
                margin: 5px;
            }
        """)
        
        layout = QVBoxLayout(card)
        layout.setSpacing(5)
        
        # Tytuł
        title_label = QLabel(title)
        title_label.setFont(QFont("Arial", 12, QFont.Weight.Bold))
        title_label.setStyleSheet("color: #495057;")
        layout.addWidget(title_label)
        
        # Wartość
        value_label = QLabel(value)
        value_label.setFont(QFont("Arial", 20, QFont.Weight.Bold))
        value_label.setStyleSheet("color: #212529;")
        layout.addWidget(value_label)
        
        # Opis
        desc_label = QLabel(description)
        desc_label.setFont(QFont("Arial", 10))
        desc_label.setStyleSheet("color: #6c757d;")
        layout.addWidget(desc_label)
        
        card.setMinimumSize(200, 120)
        card.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        
        return card

    def setup_styles(self):
        """Ustawia nowoczesne style dla głównego okna"""
        if STYLES_AVAILABLE:
            # Używamy nowoczesnego ciemnego motywu
            self.setStyleSheet(DARK_THEME)
            logger.info("Applied modern dark theme styles")
        else:
            # Fallback do podstawowych stylów
            self.setStyleSheet("""
                QMainWindow {
                    background: qlineargradient(x1:0, y1:0, x2:1, y2:1,
                        stop:0 #1a1a1a, stop:1 #2d2d2d);
                    color: #ffffff;
                    font-family: 'Segoe UI', Arial, sans-serif;
                }
                QTabWidget::pane {
                    border: 1px solid #2a2a2a;
                    border-radius: 8px;
                    background: #1a1a1a;
                }
                QTabWidget::tab-bar {
                    alignment: left;
                }
                QTabBar::tab {
                    background: #2a2a2a;
                    color: #cccccc;
                    padding: 12px 20px;
                    margin-right: 2px;
                    border-top-left-radius: 8px;
                    border-top-right-radius: 8px;
                    font-weight: 500;
                }
                QTabBar::tab:selected {
                    background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                        stop:0 #667eea, stop:1 #764ba2);
                    color: white;
                    font-weight: 600;
                }
                QTabBar::tab:hover:!selected {
                    background: rgba(102, 126, 234, 0.3);
                    color: white;
                }
                QPushButton[objectName="actionButton"] {
                    background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                        stop:0 #667eea, stop:1 #764ba2);
                    color: white;
                    border: none;
                    border-radius: 8px;
                    padding: 12px 24px;
                    font-size: 14px;
                    font-weight: 600;
                    min-height: 36px;
                }
                QPushButton[objectName="actionButton"]:hover {
                    background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                        stop:0 rgba(102, 126, 234, 0.9), 
                        stop:1 rgba(118, 75, 162, 0.9));
                }
                QLabel[objectName="sectionTitle"] {
                    font-size: 24px;
                    font-weight: bold;
                    color: #ffffff;
                    margin-bottom: 16px;
                }
            """)
            logger.warning("Using fallback styles - styles.py not available")

    # Optional API used by extensions
    def add_custom_panel(self, title: str, widget: QWidget):
        try:
            dock = QDockWidget(title, self)
            dock.setWidget(widget)
            self.addDockWidget(Qt.DockWidgetArea.RightDockWidgetArea, dock)
            logger.info(f"Custom panel '{title}' added successfully")
        except Exception as e:
            logger.error(f"add_custom_panel failed: {e}")

    def toggle_theme(self):
        """Przełącza motyw aplikacji (ciemny/jasny) i aplikuje style."""
        try:
            current = getattr(self, "_current_theme", "dark")
            new_theme = "light" if current == "dark" else "dark"
            self._current_theme = new_theme
            # Jeśli mamy styles.py z get_theme_style, użyj go
            if STYLES_AVAILABLE:
                from ui.styles import get_theme_style
                self.setStyleSheet(get_theme_style(new_theme == "dark"))
            else:
                # Fallback: ponownie zastosuj setup_styles()
                self.setup_styles()
            logger.info(f"Theme toggled to {new_theme}")
        except Exception as e:
            logger.warning(f"toggle_theme failed: {e}")

    def set_status(self, api: bool, ws: bool, db: bool):
        """Ustawia statusy systemu używane przez rozszerzenia dashboardu i nagłówek."""
        try:
            status_text = f"API: {'OK' if api else 'ERR'} | WS: {'OK' if ws else 'ERR'} | DB: {'OK' if db else 'ERR'}"
            # Jeśli mamy pasek statusu, pokaż komunikat
            try:
                self.statusBar().showMessage(status_text, 3000)
            except Exception:
                pass
            logger.info(f"System status set: {status_text}")
        except Exception as e:
            logger.warning(f"set_status failed: {e}")

    def closeEvent(self, event):
        """Zapewnia bezpieczne zatrzymanie zadań asynchronicznych i timerów przy zamykaniu okna."""
        try:
            # Oznacz zamykanie okna, aby zatrzymać nowe odświeżenia i handler'y
            self._is_closing = True
            # Odsubskrybuj aktualizacje z IntegratedDataManager aby uniknąć wywołań na zniszczone UI
            try:
                if hasattr(self, 'integrated_data_manager') and self.integrated_data_manager:
                    try:
                        # Poprawny alias odsubskrybowania
                        self.integrated_data_manager.unsubscribe_from_updates('system_status_update', self._apply_system_status)
                        self.integrated_data_manager.unsubscribe_from_updates('portfolio_update', self._on_portfolio_update)
                        self.integrated_data_manager.unsubscribe_from_updates('bot_status_update', self._on_bot_status_update)
                    except Exception:
                        pass
            except Exception:
                pass
            
            if hasattr(self, 'refresh_timer') and self.refresh_timer:
                self.refresh_timer.stop()
            if hasattr(self, 'async_manager') and self.async_manager:
                try:
                    # Anuluj aktywne zadania odświeżania przed sprzątaniem
                    try:
                        self.async_manager.cancel_task('dashboard_refresh')
                    except Exception:
                        pass
                    try:
                        self.async_manager.cancel_task('recent_trades_refresh')
                    except Exception:
                        pass
                    self.async_manager.cleanup()
                except Exception:
                    pass
            # Zatrzymaj pętle danych jeśli dostępny IntegratedDataManager
            try:
                if hasattr(self, 'integrated_data_manager') and self.integrated_data_manager:
                    import asyncio
                    try:
                        asyncio.get_running_loop()
                        import concurrent.futures
                        with concurrent.futures.ThreadPoolExecutor() as executor:
                            future = executor.submit(asyncio.run, self.integrated_data_manager.stop_data_loops())
                            future.result(timeout=5)
                    except RuntimeError:
                        try:
                            asyncio.run(self.integrated_data_manager.stop_data_loops())
                        except Exception:
                            pass
            except Exception:
                pass
            logger.info("UpdatedMainWindow cleanup completed (timers, async tasks and data loops stopped)")
        except Exception as e:
            logger.warning(f"UpdatedMainWindow cleanup encountered an issue: {e}")
        finally:
            try:
                super().closeEvent(event)
            except Exception:
                pass

    def __del__(self):
        """Dodatkowe zabezpieczenie przed pozostawieniem działających wątków."""
        try:
            if hasattr(self, 'refresh_timer') and self.refresh_timer:
                try:
                    self.refresh_timer.stop()
                except Exception:
                    pass
            if hasattr(self, 'async_manager') and self.async_manager:
                try:
                    self.async_manager.cleanup()
                except Exception:
                    pass
        except Exception:
            pass

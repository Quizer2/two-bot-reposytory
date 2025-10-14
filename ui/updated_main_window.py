
from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, List

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
        QFrame,
        QGridLayout,
        QSizePolicy,
        QTableWidget,
        QTableWidgetItem,
        QHeaderView,
        QScrollArea,
    )
    from PyQt6.QtCore import Qt, QTimer
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
        QFrame,
        QGridLayout,
        QSizePolicy,
        QTableWidget,
        QTableWidgetItem,
        QHeaderView,
        QScrollArea,
    )
    from PyQt6.QtCore import Qt, QTimer
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
        self.setMinimumSize(220, 150)
        # Ustaw elastyczną politykę rozmiaru
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(10)
        
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
            accent = self.color or "#667eea"
            self.setStyleSheet(f"""
                QWidget#dashboardCard {{
                    background: #ffffff;
                    border: 1px solid rgba(102, 126, 234, 0.18);
                    border-radius: 18px;
                    padding: 18px;
                    box-shadow: 0 12px 32px rgba(15, 23, 42, 0.06);
                    border-top: 3px solid {accent};
                }}
                QLabel#cardTitle {{
                    font-size: 13px;
                    font-weight: 600;
                    color: #465165;
                }}
                QLabel#cardValue {{
                    font-size: 26px;
                    font-weight: 700;
                    color: #0f172a;
                }}
                QLabel#cardSubtitle {{
                    font-size: 12px;
                    color: #64748b;
                }}
            """)
        except Exception as e:
            logger.warning(f"DashboardCard.apply_style failed: {e}")
    
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
    from ui.styles import get_theme_style, COLORS
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
        self.portfolio_kpi_labels: Dict[str, tuple] = {}
        self.portfolio_kpi_formatters: Dict[str, Any] = {}
        self.telemetry_labels: Dict[str, tuple] = {}
        self.telemetry_formatters: Dict[str, Any] = {}
        
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
            if hasattr(self, 'weekly_pnl_card'):
                weekly = portfolio.get('weekly_change', 0.0)
                weekly_pct = portfolio.get('weekly_change_percent', 0.0)
                self.weekly_pnl_card.update_value(f"${weekly:+,.2f}", f"{weekly_pct:+.2f}% (7d)")
            if hasattr(self, 'monthly_pnl_card'):
                monthly = portfolio.get('monthly_change', 0.0)
                monthly_pct = portfolio.get('monthly_change_percent', 0.0)
                self.monthly_pnl_card.update_value(f"${monthly:+,.2f}", f"{monthly_pct:+.2f}% (30d)")
            # Active bots
            if hasattr(self, 'active_bots_card'):
                active = bots.get('active', 0)
                total = bots.get('total', 0)
                self.active_bots_card.update_value(str(active), f"{total} łącznie")
            if hasattr(self, 'bots_table'):
                self.update_active_bots_table(bots.get('entries', []))
            # Total P&L (jeśli karta istnieje)
            if hasattr(self, 'total_pnl_card'):
                total_pnl = portfolio.get('profit_loss', 0.0)
                total_pnl_pct = portfolio.get('profit_loss_percent', 0.0)
                self.total_pnl_card.update_value(f"{total_pnl:+,.2f}", f"ROI {total_pnl_pct:+.2f}%")

            self._update_portfolio_kpis(data.get('portfolio_kpis', {}))
            self._update_telemetry_section(data.get('telemetry', {}))
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
        scroll = QScrollArea()
        scroll.setObjectName("dashboardScroll")
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        try:
            scroll.setFrameShape(QFrame.Shape.NoFrame)
        except Exception:
            pass

        container = QWidget()
        layout = QVBoxLayout(container)
        layout.setSpacing(24)
        layout.setContentsMargins(32, 32, 32, 32)

        hero_frame = QFrame()
        hero_frame.setObjectName("sectionCard")
        hero_layout = QHBoxLayout(hero_frame)
        hero_layout.setContentsMargins(24, 24, 24, 24)
        hero_layout.setSpacing(16)

        hero_texts = QVBoxLayout()
        hero_title = QLabel("Przegląd aplikacji CryptoBot")
        hero_title.setObjectName("sectionTitle")
        hero_title.setFont(QFont("Segoe UI", 22, QFont.Weight.Bold))
        hero_texts.addWidget(hero_title)

        hero_subtitle = QLabel(
            "Spójny podgląd kondycji portfela, botów i ostatnich zleceń. Odświeżaj dane, aby "
            "widzieć najnowsze wyniki na żywo."
        )
        hero_subtitle.setObjectName("cardSubtitle")
        hero_subtitle.setWordWrap(True)
        hero_texts.addWidget(hero_subtitle)
        hero_texts.addStretch()

        hero_layout.addLayout(hero_texts, stretch=3)

        refresh_btn = QPushButton("🔄 Odśwież dane")
        refresh_btn.setObjectName("inlineAction")
        refresh_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        refresh_btn.clicked.connect(self.refresh_data)
        hero_layout.addWidget(refresh_btn, alignment=Qt.AlignmentFlag.AlignTop)

        layout.addWidget(hero_frame)

        self.setup_summary_cards(layout)
        self.setup_portfolio_metrics_section(layout)
        self.setup_telemetry_section(layout)
        self.setup_active_bots_section(layout)
        self.setup_recent_trades_section(layout)

        container.setLayout(layout)
        scroll.setWidget(container)

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
        
        return scroll

    def setup_summary_cards(self, layout):
        """Konfiguracja nowoczesnych kart podsumowania z responsywnym layoutem"""
        # Używamy lokalnie zdefiniowanych DashboardCard
        cards_frame = QFrame()
        cards_frame.setObjectName("sectionCard")
        cards_layout = QGridLayout(cards_frame)
        cards_layout.setSpacing(18)
        cards_layout.setContentsMargins(24, 24, 24, 24)
        
        # Tworzenie kart z odpowiednimi objectName dla stylów
        self.portfolio_card = DashboardCard("Wartość Portfela", "$0.00", "0.00% (24h)", "#667eea")
        self.portfolio_card.setObjectName("portfolioCard")
        self.portfolio_card.title_label.setText("Wartość Portfela")
        cards_layout.addWidget(self.portfolio_card, 0, 0)
        
        self.daily_pnl_card = DashboardCard("P&L Dzienny", "$0.00", "0.00%", "#f093fb")
        self.daily_pnl_card.setObjectName("dailyPnlCard")
        self.daily_pnl_card.title_label.setText("P&L Dzienny")
        cards_layout.addWidget(self.daily_pnl_card, 0, 1)

        self.weekly_pnl_card = DashboardCard("Zmiana 7 dni", "$0.00", "0.00%", "#ffcf78")
        self.weekly_pnl_card.setObjectName("weeklyPnlCard")
        self.weekly_pnl_card.title_label.setText("Zmiana 7 dni")
        cards_layout.addWidget(self.weekly_pnl_card, 0, 2)

        self.active_bots_card = DashboardCard("Aktywne Boty", "0", "0 łącznie", "#4facfe")
        self.active_bots_card.setObjectName("botsCard")
        self.active_bots_card.title_label.setText("Aktywne Boty")
        cards_layout.addWidget(self.active_bots_card, 1, 0)

        # Zamiast karty transakcji dodajemy P&L Całkowity
        self.total_pnl_card = DashboardCard("P&L Całkowity", "$0.00", "ROI 0.00%", "#43e97b")
        self.total_pnl_card.setObjectName("totalPnlCard")
        self.total_pnl_card.title_label.setText("P&L Całkowity")
        cards_layout.addWidget(self.total_pnl_card, 1, 1)

        self.monthly_pnl_card = DashboardCard("Zmiana 30 dni", "$0.00", "0.00%", "#f76b8a")
        self.monthly_pnl_card.setObjectName("monthlyPnlCard")
        self.monthly_pnl_card.title_label.setText("Zmiana 30 dni")
        cards_layout.addWidget(self.monthly_pnl_card, 1, 2)

        # Ustaw równe proporcje kolumn
        for i in range(3):
            cards_layout.setColumnStretch(i, 1)

        layout.addWidget(cards_frame)
        logger.info("Dashboard cards created successfully with local DashboardCard and proper styling")

    def setup_portfolio_metrics_section(self, layout):
        section_frame = QFrame()
        section_frame.setObjectName("sectionCard")
        section_layout = QVBoxLayout(section_frame)
        section_layout.setContentsMargins(24, 24, 24, 24)
        section_layout.setSpacing(16)

        header = QLabel("Metryki portfela i ryzyka")
        header.setObjectName("sectionTitle")
        header.setFont(QFont("Segoe UI", 16, QFont.Weight.Bold))
        section_layout.addWidget(header)

        subtitle = QLabel("Analiza wydajności strategii, efektywności zarządzania ryzykiem oraz kosztów handlu.")
        subtitle.setObjectName("cardSubtitle")
        subtitle.setWordWrap(True)
        section_layout.addWidget(subtitle)

        grid = QGridLayout()
        grid.setContentsMargins(0, 0, 0, 0)
        grid.setSpacing(16)

        metrics = [
            ("Win rate", "win_rate", lambda v: f"{float(v):.1f}%"),
            ("Profit factor", "profit_factor", lambda v: f"{float(v):.2f}"),
            ("Transakcje", "total_trades", lambda v: f"{int(float(v)):,}".replace(",", " ")),
            ("Opłaty", "total_fees_paid", lambda v: f"${float(v):,.2f}"),
            ("Średni zysk", "avg_win", lambda v: f"${float(v):,.2f}"),
            ("Średnia strata", "avg_loss", lambda v: f"${float(v):,.2f}"),
            ("Sharpe", "sharpe_ratio", lambda v: f"{float(v):.2f}"),
            ("Max drawdown", "max_drawdown", lambda v: f"{float(v):.2f}%"),
        ]

        for idx, (title, key, formatter) in enumerate(metrics):
            container, value_label, caption_label = self._create_metric_pill(title, object_name="kpiPill")
            grid.addWidget(container, idx // 4, idx % 4)
            self.portfolio_kpi_labels[key] = (value_label, caption_label)
            self.portfolio_kpi_formatters[key] = formatter

        for col in range(4):
            grid.setColumnStretch(col, 1)

        section_layout.addLayout(grid)
        layout.addWidget(section_frame)

    def setup_telemetry_section(self, layout):
        section_frame = QFrame()
        section_frame.setObjectName("sectionCard")
        section_layout = QVBoxLayout(section_frame)
        section_layout.setContentsMargins(24, 24, 24, 24)
        section_layout.setSpacing(16)

        header_layout = QHBoxLayout()
        header_layout.setContentsMargins(0, 0, 0, 0)
        header_layout.setSpacing(12)

        header = QLabel("Telemetria połączeń i stabilność botów")
        header.setObjectName("sectionTitle")
        header.setFont(QFont("Segoe UI", 16, QFont.Weight.Bold))
        header_layout.addWidget(header)

        header_layout.addStretch()
        section_layout.addLayout(header_layout)

        subtitle = QLabel("Monitoruj opóźnienia, ponowienia zapytań oraz stan obwodów zabezpieczających dla każdej giełdy.")
        subtitle.setObjectName("cardSubtitle")
        subtitle.setWordWrap(True)
        section_layout.addWidget(subtitle)

        grid = QGridLayout()
        grid.setContentsMargins(0, 0, 0, 0)
        grid.setSpacing(16)

        telemetry_metrics = [
            ("p95 opóźnienia", "latency_p95", lambda v: f"{float(v):.1f} ms"),
            ("Max opóźnienie", "latency_max", lambda v: f"{float(v):.1f} ms"),
            ("Średnie opóźnienie", "latency_avg", lambda v: f"{float(v):.1f} ms"),
            ("Żądania HTTP", "http_requests", lambda v: f"{int(float(v)):,}".replace(",", " ")),
            ("Ponowienia", "http_retries", lambda v: f"{int(float(v)):,}".replace(",", " ")),
            ("Reconnecty", "http_reconnects", lambda v: f"{int(float(v)):,}".replace(",", " ")),
            ("Otwarte obwody", "open_circuits", lambda v: f"{int(float(v)):,}".replace(",", " ")),
            ("Rate drops", "rate_drops_total", lambda v: f"{int(float(v)):,}".replace(",", " ")),
        ]

        for idx, (title, key, formatter) in enumerate(telemetry_metrics):
            container, value_label, caption_label = self._create_metric_pill(title, object_name="metricPill")
            grid.addWidget(container, idx // 4, idx % 4)
            self.telemetry_labels[key] = (value_label, caption_label)
            self.telemetry_formatters[key] = formatter

        for col in range(4):
            grid.setColumnStretch(col, 1)

        section_layout.addLayout(grid)

        self.exchange_latency_table = QTableWidget()
        self.exchange_latency_table.setObjectName("latencyTable")
        self.exchange_latency_table.setColumnCount(7)
        self.exchange_latency_table.setHorizontalHeaderLabels([
            "Giełda",
            "Żądania",
            "p50 (ms)",
            "p95 (ms)",
            "Max (ms)",
            "Rate drops",
            "Circuit open"
        ])
        self.exchange_latency_table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.exchange_latency_table.setSelectionMode(QTableWidget.SelectionMode.NoSelection)
        self.exchange_latency_table.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self.exchange_latency_table.setAlternatingRowColors(True)
        self.exchange_latency_table.verticalHeader().setVisible(False)
        self.exchange_latency_table.setMinimumHeight(220)

        header = self.exchange_latency_table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(1, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(2, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(3, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(4, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(5, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(6, QHeaderView.ResizeMode.Stretch)

        section_layout.addWidget(self.exchange_latency_table)

        self.latency_empty_label = QLabel("Brak zarejestrowanych próbek telemetrii dla połączeń API.")
        self.latency_empty_label.setObjectName("emptyStateLabel")
        self.latency_empty_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.latency_empty_label.setWordWrap(True)
        section_layout.addWidget(self.latency_empty_label)

        self.exchange_latency_table.hide()

        layout.addWidget(section_frame)

    def setup_active_bots_section(self, layout):
        """Konfiguracja sekcji aktywnych botów"""
        section_frame = QFrame()
        section_frame.setObjectName("sectionCard")
        section_layout = QVBoxLayout(section_frame)
        section_layout.setContentsMargins(24, 24, 24, 24)
        section_layout.setSpacing(18)

        header_layout = QHBoxLayout()
        header_title = QLabel("Aktywne boty")
        header_title.setObjectName("sectionTitle")
        header_title.setFont(QFont("Arial", 16, QFont.Weight.Bold))
        header_layout.addWidget(header_title)

        header_layout.addStretch()

        manage_bots_btn = QPushButton("Zarządzaj botami")
        manage_bots_btn.setObjectName("inlineAction")
        manage_bots_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        manage_bots_btn.clicked.connect(self.create_new_bot)
        header_layout.addWidget(manage_bots_btn)

        section_layout.addLayout(header_layout)

        helper_label = QLabel("Zobacz status każdej strategii, wynik finansowy i ostatnią aktywność.")
        helper_label.setObjectName("cardSubtitle")
        helper_label.setWordWrap(True)
        section_layout.addWidget(helper_label)

        self.bots_table = QTableWidget()
        self.bots_table.setColumnCount(6)
        self.bots_table.setHorizontalHeaderLabels([
            "Bot",
            "Status",
            "P&L",
            "Zmiana %",
            "Transakcje",
            "Ostatnia transakcja"
        ])
        self.bots_table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.bots_table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.bots_table.setSelectionMode(QTableWidget.SelectionMode.NoSelection)
        self.bots_table.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self.bots_table.setAlternatingRowColors(True)
        self.bots_table.verticalHeader().setVisible(False)
        self.bots_table.setMinimumHeight(240)

        header = self.bots_table.horizontalHeader()
        header.setStretchLastSection(False)
        header.setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        header.setSectionResizeMode(1, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(2, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(3, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(4, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(5, QHeaderView.ResizeMode.Stretch)

        section_layout.addWidget(self.bots_table)

        self.bots_empty_label = QLabel("Brak skonfigurowanych botów. Użyj przycisku powyżej, aby dodać nową strategię.")
        self.bots_empty_label.setObjectName("emptyStateLabel")
        self.bots_empty_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.bots_empty_label.setWordWrap(True)
        section_layout.addWidget(self.bots_empty_label)

        self.bots_table.hide()

        footer_label = QLabel("Wskazówka: kliknij \"Zarządzaj botami\", aby przejść bezpośrednio do konfiguratora.")
        footer_label.setObjectName("cardSubtitle")
        footer_label.setAlignment(Qt.AlignmentFlag.AlignLeft)
        footer_label.setWordWrap(True)
        section_layout.addWidget(footer_label)

        layout.addWidget(section_frame)

    @staticmethod
    def _normalize_bot_entry(entry: Any) -> Dict[str, Any]:
        try:
            if isinstance(entry, dict):
                return entry
            from dataclasses import asdict, is_dataclass
            if is_dataclass(entry):
                return asdict(entry)
        except Exception:
            pass
        return {
            'id': getattr(entry, 'id', ''),
            'name': getattr(entry, 'name', ''),
            'status': getattr(entry, 'status', ''),
            'active': bool(getattr(entry, 'active', False)),
            'profit': getattr(entry, 'profit', 0.0),
            'profit_percent': getattr(entry, 'profit_percent', 0.0),
            'trades_count': getattr(entry, 'trades_count', 0),
            'last_trade': getattr(entry, 'last_trade', None),
            'risk_level': getattr(entry, 'risk_level', '')
        }

    def update_active_bots_table(self, bots: Any):
        """Aktualizuje tabelę aktywnych botów danymi z menedżera."""
        if not hasattr(self, 'bots_table'):
            return

        try:
            entries: List[Dict[str, Any]]
            if isinstance(bots, dict):
                entries = [self._normalize_bot_entry(v) for v in bots.values()]
            else:
                entries = [self._normalize_bot_entry(item) for item in (bots or [])]

            if not entries:
                self.bots_table.setRowCount(0)
                self.bots_table.hide()
                if hasattr(self, 'bots_empty_label'):
                    self.bots_empty_label.show()
                return

            if hasattr(self, 'bots_empty_label'):
                self.bots_empty_label.hide()
            self.bots_table.show()

            self.bots_table.setRowCount(len(entries))

            for row, entry in enumerate(entries):
                name = entry.get('name') or '—'
                status_raw = entry.get('status') or ''
                active = bool(entry.get('active', False))
                status_text = 'Aktywny' if active else 'Wstrzymany'

                profit = float(entry.get('profit', 0.0) or 0.0)
                profit_percent = float(entry.get('profit_percent', 0.0) or 0.0)
                trades_count = int(entry.get('trades_count', 0) or 0)
                last_trade_display = '—'
                last_trade_value = entry.get('last_trade')
                if last_trade_value:
                    try:
                        if isinstance(last_trade_value, str):
                            dt = datetime.fromisoformat(last_trade_value)
                        else:
                            dt = last_trade_value
                        last_trade_display = dt.strftime('%Y-%m-%d %H:%M')
                    except Exception:
                        last_trade_display = str(last_trade_value)

                items = [
                    QTableWidgetItem(name),
                    QTableWidgetItem(status_text),
                    QTableWidgetItem(f"{profit:+,.2f}"),
                    QTableWidgetItem(f"{profit_percent:+.2f}%"),
                    QTableWidgetItem(str(trades_count)),
                    QTableWidgetItem(last_trade_display)
                ]

                tooltip_parts = []
                if status_raw and status_raw.lower() != status_text.lower():
                    tooltip_parts.append(f"Status systemowy: {status_raw}")
                risk_level = entry.get('risk_level')
                if risk_level:
                    tooltip_parts.append(f"Profil ryzyka: {risk_level}")
                tooltip = "\n".join(tooltip_parts) if tooltip_parts else ''

                for col, item in enumerate(items):
                    if tooltip:
                        item.setToolTip(tooltip)
                    if col == 2:
                        color = QColor(0x76, 0xEF, 0x76) if profit >= 0 else QColor(0xF4, 0x43, 0x36)
                        item.setForeground(QBrush(color))
                    if col == 3:
                        color = QColor(0x76, 0xEF, 0xD3) if profit_percent >= 0 else QColor(0xFF, 0x85, 0x85)
                        item.setForeground(QBrush(color))
                    item.setTextAlignment(Qt.AlignmentFlag.AlignVCenter | (Qt.AlignmentFlag.AlignRight if col in (2, 3, 4, 5) else Qt.AlignmentFlag.AlignLeft))
                    self.bots_table.setItem(row, col, item)

            self.bots_table.resizeRowsToContents()

        except Exception as error:
            logger.error(f"Nie udało się zaktualizować tabeli botów: {error}")
            self.bots_table.setRowCount(0)
            self.bots_table.hide()
            if hasattr(self, 'bots_empty_label'):
                self.bots_empty_label.show()

    def setup_recent_trades_section(self, layout):
        """Konfiguracja sekcji ostatnich transakcji"""
        section_frame = QFrame()
        section_frame.setObjectName("sectionCard")
        section_layout = QVBoxLayout(section_frame)
        section_layout.setContentsMargins(24, 24, 24, 24)
        section_layout.setSpacing(18)

        header_layout = QHBoxLayout()
        trades_title = QLabel("Ostatnie transakcje")
        trades_title.setObjectName("sectionTitle")
        trades_title.setFont(QFont("Arial", 16, QFont.Weight.Bold))
        header_layout.addWidget(trades_title)

        header_layout.addStretch()

        section_layout.addLayout(header_layout)

        description = QLabel("Lista najnowszych zleceń wysłanych przez boty wraz z kwotą i ceną wykonania.")
        description.setObjectName("cardSubtitle")
        description.setWordWrap(True)
        section_layout.addWidget(description)

        self.trades_table = QTableWidget()
        self.trades_table.setColumnCount(6)
        self.trades_table.setHorizontalHeaderLabels([
            "Czas",
            "Bot",
            "Para",
            "Typ",
            "Kwota",
            "Cena"
        ])
        self.trades_table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.trades_table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.trades_table.setSelectionMode(QTableWidget.SelectionMode.NoSelection)
        self.trades_table.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self.trades_table.setShowGrid(False)
        self.trades_table.setAlternatingRowColors(True)
        self.trades_table.verticalHeader().setVisible(False)
        self.trades_table.setMinimumHeight(260)

        header = self.trades_table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(1, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(2, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(3, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(4, QHeaderView.ResizeMode.Stretch)
        header.setSectionResizeMode(5, QHeaderView.ResizeMode.Stretch)

        section_layout.addWidget(self.trades_table)

        self.trades_empty_label = QLabel("Brak transakcji do wyświetlenia w wybranym przedziale czasu.")
        self.trades_empty_label.setObjectName("emptyStateLabel")
        self.trades_empty_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.trades_empty_label.setWordWrap(True)
        section_layout.addWidget(self.trades_empty_label)

        self.trades_table.hide()

        layout.addWidget(section_frame)

    def populate_trades_table(self):
        """Wypełnia tabelę danymi transakcji (z bufora lub fallback)."""
        try:
            trades = self._latest_trades if getattr(self, '_latest_trades', None) else []

            if not trades:
                self.trades_table.setRowCount(0)
                self.trades_table.hide()
                if hasattr(self, 'trades_empty_label'):
                    self.trades_empty_label.show()
                return

            if hasattr(self, 'trades_empty_label'):
                self.trades_empty_label.hide()
            self.trades_table.show()

            self.trades_table.setRowCount(len(trades))
            for row, tr in enumerate(trades):
                time_val = tr.get('time') or tr.get('executed_at') or ''
                bot_name = tr.get('bot') or tr.get('bot_name') or '—'
                pair = tr.get('pair') or tr.get('symbol') or '—'
                side = str(tr.get('side') or tr.get('direction') or '').upper() or '—'
                amount = float(tr.get('amount', tr.get('qty', 0.0)) or 0.0)
                price = float(tr.get('price', tr.get('avg_price', 0.0)) or 0.0)

                values = [
                    str(time_val),
                    bot_name,
                    pair,
                    side,
                    f"{amount:,.4f}",
                    f"{price:,.4f}"
                ]

                for col, value in enumerate(values):
                    item = QTableWidgetItem(value)
                    if col == 3:
                        font = item.font()
                        font.setBold(True)
                        item.setFont(font)
                        color = QColor(0x4C, 0xAF, 0x50) if side != 'SELL' else QColor(0xF4, 0x43, 0x36)
                        item.setForeground(QBrush(color))
                        item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
                    elif col in (4, 5):
                        item.setTextAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
                    else:
                        item.setTextAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)
                    self.trades_table.setItem(row, col, item)

            self.trades_table.resizeRowsToContents()
        except Exception as e:
            logger.error(f"Nie udało się wypełnić tabeli transakcji: {e}")

    def _create_metric_pill(self, title: str, object_name: str = "metricPill"):
        container = QFrame()
        container.setObjectName(object_name)
        pill_layout = QVBoxLayout(container)
        pill_layout.setContentsMargins(16, 12, 16, 12)
        pill_layout.setSpacing(6)

        title_label = QLabel(title)
        title_label.setObjectName("metricTitle")
        title_label.setWordWrap(True)
        pill_layout.addWidget(title_label)

        value_label = QLabel("--")
        value_label.setObjectName("metricValue")
        value_label.setAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)
        pill_layout.addWidget(value_label)

        caption_label = QLabel("")
        caption_label.setObjectName("metricCaption")
        caption_label.setWordWrap(True)
        pill_layout.addWidget(caption_label)

        return container, value_label, caption_label

    def populate_latency_table(self, entries: List[Dict[str, Any]]):
        if not hasattr(self, 'exchange_latency_table'):
            return

        table = self.exchange_latency_table
        if not entries:
            table.setRowCount(0)
            table.hide()
            if hasattr(self, 'latency_empty_label'):
                self.latency_empty_label.show()
            return

        table.show()
        if hasattr(self, 'latency_empty_label'):
            self.latency_empty_label.hide()

        table.setRowCount(len(entries))
        for row, entry in enumerate(entries):
            exchange = entry.get('exchange', '') or '—'
            requests = int(entry.get('requests', 0) or 0)
            p50 = float(entry.get('p50', 0.0) or 0.0)
            p95 = float(entry.get('p95', 0.0) or 0.0)
            max_latency = float(entry.get('max', 0.0) or 0.0)
            rate_drops = int(entry.get('rate_drops', 0) or 0)
            open_circuits = int(entry.get('open_circuits', 0) or 0)

            row_values = [
                exchange.upper(),
                f"{requests:,}".replace(",", " "),
                f"{p50:.1f}",
                f"{p95:.1f}",
                f"{max_latency:.1f}",
                str(rate_drops),
                str(open_circuits),
            ]

            for col, value in enumerate(row_values):
                item = QTableWidgetItem(value)
                alignment = Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter
                if col >= 1:
                    alignment = Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter
                item.setTextAlignment(alignment)

                if col in (3, 4):
                    try:
                        metric_val = float(value)
                        if metric_val > 800:
                            item.setForeground(QBrush(QColor(0xDC, 0x26, 0x26)))
                        elif metric_val > 400:
                            item.setForeground(QBrush(QColor(0xD9, 0x77, 0x06)))
                        else:
                            item.setForeground(QBrush(QColor(0x0f, 0x17, 0x2a)))
                    except Exception:
                        pass

                if col == 5 and rate_drops > 0:
                    item.setForeground(QBrush(QColor(0xD9, 0x77, 0x06)))
                if col == 6 and open_circuits > 0:
                    item.setForeground(QBrush(QColor(0xDC, 0x26, 0x26)))

                table.setItem(row, col, item)

        table.resizeRowsToContents()

    def _set_kpi_value(self, key: str, value: Any, caption: str | None = None):
        labels = self.portfolio_kpi_labels.get(key)
        if not labels:
            return
        value_label, caption_label = labels
        formatter = self.portfolio_kpi_formatters.get(key, lambda v: str(v))
        text = "--"
        color = "#0f172a"
        numeric_value = None

        if value is not None:
            try:
                numeric_value = float(value)
            except Exception:
                numeric_value = None
            try:
                text = formatter(value)
            except Exception:
                text = str(value)

        value_label.setText(text)

        if numeric_value is None and value is None:
            color = "#94a3b8"
        elif key in ('avg_win', 'win_rate', 'profit_factor') and numeric_value is not None and numeric_value > 0:
            color = "#16a34a"
        elif key in ('avg_loss',) and numeric_value is not None and numeric_value < 0:
            color = "#dc2626"
        elif key == 'max_drawdown' and numeric_value is not None:
            color = "#d97706" if numeric_value > 20 else "#0f172a"

        value_label.setStyleSheet(f"color: {color};")

        if caption_label is not None:
            caption_label.setText(caption or "")

    def _update_portfolio_kpis(self, kpis: Dict[str, Any]):
        if not self.portfolio_kpi_labels:
            return

        total_trades = int(kpis.get('total_trades', 0) or 0)
        winning_trades = int(kpis.get('winning_trades', 0) or 0)
        losing_trades = int(kpis.get('losing_trades', 0) or 0)
        sortino = kpis.get('sortino_ratio', 0.0)
        recovery = kpis.get('recovery_factor', 0.0)

        if total_trades:
            win_caption = f"Wygrane {winning_trades}/{total_trades}"
        else:
            win_caption = "Brak historii"
        self._set_kpi_value('win_rate', kpis.get('win_rate'), caption=win_caption)

        loss_caption = f"Przegrane {losing_trades}" if losing_trades else "Brak strat"
        self._set_kpi_value('profit_factor', kpis.get('profit_factor'), caption=loss_caption)

        self._set_kpi_value('total_trades', total_trades, caption="Łącznie od startu")
        self._set_kpi_value('total_fees_paid', kpis.get('total_fees_paid'), caption="Sumaryczne opłaty")
        self._set_kpi_value('avg_win', kpis.get('avg_win'), caption="na transakcję")
        self._set_kpi_value('avg_loss', kpis.get('avg_loss'), caption="na transakcję")

        try:
            sortino_val = float(sortino)
        except Exception:
            sortino_val = 0.0
        self._set_kpi_value('sharpe_ratio', kpis.get('sharpe_ratio'), caption=f"Sortino {sortino_val:.2f}")

        try:
            recovery_val = float(recovery)
        except Exception:
            recovery_val = 0.0
        self._set_kpi_value('max_drawdown', kpis.get('max_drawdown'), caption=f"Recovery {recovery_val:.2f}")

    def _set_telemetry_value(self, key: str, value: Any, caption: str | None = None):
        labels = self.telemetry_labels.get(key)
        if not labels:
            return
        value_label, caption_label = labels
        formatter = self.telemetry_formatters.get(key, lambda v: str(v))
        text = "--"
        numeric_value = None
        if value is not None:
            try:
                numeric_value = float(value)
            except Exception:
                numeric_value = None
            try:
                text = formatter(value)
            except Exception:
                text = str(value)

        value_label.setText(text)

        color = "#0f172a"
        if key.startswith('latency') and numeric_value is not None:
            if numeric_value > 800:
                color = "#dc2626"
            elif numeric_value > 400:
                color = "#d97706"
        elif key in ('http_retries', 'http_reconnects', 'rate_drops_total') and numeric_value:
            color = "#d97706"
        elif key == 'open_circuits' and numeric_value:
            color = "#dc2626"

        value_label.setStyleSheet(f"color: {color};")

        if caption_label is not None:
            caption_label.setText(caption or "")

    def _update_telemetry_section(self, telemetry: Dict[str, Any]):
        if not self.telemetry_labels:
            return

        telemetry = telemetry or {}
        latency = telemetry.get('latency', {}) or {}
        global_latency = latency.get('global', {}) or {}
        per_exchange = latency.get('per_exchange', []) or []

        count = int(global_latency.get('count', 0) or 0)
        latest = global_latency.get('latest', 0.0)
        try:
            latest_val = float(latest or 0.0)
        except Exception:
            latest_val = 0.0

        self._set_telemetry_value('latency_p95', global_latency.get('p95'), caption=f"{count} próbek (5m)")
        self._set_telemetry_value('latency_max', global_latency.get('max'), caption=f"ostatni {latest_val:.1f} ms")
        self._set_telemetry_value('latency_avg', global_latency.get('avg'), caption="średnia z próbek")

        self._set_telemetry_value('http_requests', telemetry.get('http_requests'), caption="od startu aplikacji")
        self._set_telemetry_value('http_retries', telemetry.get('retries'), caption="łączna liczba prób")
        self._set_telemetry_value('http_reconnects', telemetry.get('reconnects'), caption="zdarzenia reconnect")

        open_circuits = telemetry.get('open_circuits', []) or []
        open_caption = f"{len(open_circuits)} endpointy" if open_circuits else "Brak"
        self._set_telemetry_value('open_circuits', telemetry.get('open_circuit_count'), caption=open_caption)
        self._set_telemetry_value('rate_drops_total', telemetry.get('rate_drops_total'), caption="łączna liczba ograniczeń")

        self.populate_latency_table(per_exchange)

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
                # Fallback: wyświetl puste wartości, zachowując przejrzystość UI
                if hasattr(self, 'portfolio_card'):
                    self.portfolio_card.update_value("$0.00", "0.00% (24h)")
                if hasattr(self, 'active_bots_card'):
                    self.active_bots_card.update_value("0", "0 łącznie")
                if hasattr(self, 'daily_pnl_card'):
                    self.daily_pnl_card.update_value("$0.00", "Brak transakcji")
                if hasattr(self, 'weekly_pnl_card'):
                    self.weekly_pnl_card.update_value("$0.00", "0.00% (7d)")
                if hasattr(self, 'monthly_pnl_card'):
                    self.monthly_pnl_card.update_value("$0.00", "0.00% (30d)")
                if hasattr(self, 'total_pnl_card'):
                    self.total_pnl_card.update_value("$0.00", "ROI 0.00%")
                self.update_active_bots_table([])
                self._latest_trades = []
                self.populate_trades_table()
                self._update_portfolio_kpis({})
                self._update_telemetry_section({})
                if hasattr(self, 'exchange_latency_table'):
                    self.populate_latency_table([])
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
            # Domyślnie stosujemy jasny, czytelny motyw
            try:
                self.setStyleSheet(get_theme_style(dark_mode=False))
            except Exception as exc:
                logger.warning(f"Falling back to base light theme: {exc}")
                from ui.styles import LIGHT_THEME  # type: ignore
                self.setStyleSheet(LIGHT_THEME)
            else:
                logger.info("Applied modern light theme styles")
        else:
            # Fallback do podstawowych stylów
            self.setStyleSheet("""
                QMainWindow {
                    background: #f4f6fb;
                    color: #1f2a44;
                    font-family: 'Segoe UI', Arial, sans-serif;
                }
                QTabWidget::pane {
                    border: 1px solid rgba(15, 23, 42, 0.08);
                    border-radius: 12px;
                    background: #ffffff;
                }
                QTabWidget::tab-bar {
                    alignment: left;
                }
                QTabBar::tab {
                    background: #e9ecfb;
                    color: #465165;
                    padding: 12px 20px;
                    margin-right: 2px;
                    border-top-left-radius: 10px;
                    border-top-right-radius: 10px;
                    font-weight: 500;
                }
                QTabBar::tab:selected {
                    background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                        stop:0 #667eea, stop:1 #764ba2);
                    color: white;
                    font-weight: 600;
                }
                QTabBar::tab:hover:!selected {
                    background: rgba(102, 126, 234, 0.18);
                    color: #1f2a44;
                }
                QPushButton[objectName="actionButton"], QPushButton[objectName="inlineAction"] {
                    background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                        stop:0 #667eea, stop:1 #764ba2);
                    color: white;
                    border: none;
                    border-radius: 10px;
                    padding: 12px 24px;
                    font-size: 14px;
                    font-weight: 600;
                    min-height: 40px;
                }
                QPushButton[objectName="actionButton"]:hover, QPushButton[objectName="inlineAction"]:hover {
                    background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                        stop:0 rgba(102, 126, 234, 0.9),
                        stop:1 rgba(118, 75, 162, 0.9));
                }
                QLabel[objectName="sectionTitle"] {
                    font-size: 24px;
                    font-weight: bold;
                    color: #1f2a44;
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

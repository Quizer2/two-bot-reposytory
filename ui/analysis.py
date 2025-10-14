"""
Moduł analizy wydajności botów i strategii
Zawiera szczegółowe analizy zysków, strat i wydajności wszystkich botów
"""

import sys
import os
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
import json

try:
    from PyQt6.QtWidgets import (
        QWidget, QVBoxLayout, QHBoxLayout, QGridLayout, QLabel, 
        QPushButton, QFrame, QScrollArea, QTabWidget, QSplitter,
        QTableWidget, QTableWidgetItem, QHeaderView, QComboBox,
        QGroupBox, QProgressBar, QTextEdit, QListWidget, QListWidgetItem
    )
    from PyQt6.QtCore import Qt, QTimer, pyqtSignal, QThread
    from PyQt6.QtGui import QFont, QColor, QPalette
    PYQT_AVAILABLE = True
except ImportError:
    PYQT_AVAILABLE = False
    print("PyQt6 not available")

# Dodaj ścieżkę do głównego katalogu
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from utils.logger import get_logger, LogType
from utils.config_manager import get_config_manager, get_app_setting
from ui.async_helper import get_async_manager
from core.data_manager import get_data_manager

logger = get_logger(__name__)

class PerformanceCard(QWidget):
    """Karta wyświetlająca metryki wydajności"""
    
    def __init__(self, title: str, value: str = "", change: str = "", 
                 color: str = "#4CAF50", parent=None):
        super().__init__(parent)
        self.title = title
        self.value = value
        self.change = change
        self.color = color
        self.setup_ui()
        self.apply_style()
    
    def setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 15, 20, 15)
        layout.setSpacing(8)
        
        # Tytuł
        self.title_label = QLabel(self.title)
        self.title_label.setObjectName("performance_card_title")
        layout.addWidget(self.title_label)
        
        # Wartość główna
        self.value_label = QLabel(self.value)
        self.value_label.setObjectName("performance_card_value")
        layout.addWidget(self.value_label)
        
        # Zmiana (wzrost/spadek)
        if self.change:
            self.change_label = QLabel(self.change)
            self.change_label.setObjectName("performance_card_change")
            layout.addWidget(self.change_label)
    
    def apply_style(self):
        self.setStyleSheet(f"""
            PerformanceCard {{
                background: qlineargradient(x1:0, y1:0, x2:1, y2:1,
                    stop:0 {self.color}, stop:1 {self.color}AA);
                border: 1px solid {self.color}44;
                border-radius: 12px;
                margin: 5px;
            }}
            
            QLabel#performance_card_title {{
                color: white;
                font-size: 12px;
                font-weight: 500;
                margin-bottom: 5px;
            }}
            
            QLabel#performance_card_value {{
                color: white;
                font-size: 24px;
                font-weight: bold;
                margin-bottom: 3px;
            }}
            
            QLabel#performance_card_change {{
                color: #E8F5E8;
                font-size: 11px;
                font-weight: 500;
            }}
        """)
    
    def update_values(self, value: str, change: str = None):
        """Aktualizuj wartości karty"""
        self.value_label.setText(value)
        if change and hasattr(self, 'change_label'):
            self.change_label.setText(change)

class BotAnalysisWidget(QWidget):
    """Widget analizy pojedynczego bota"""
    
    def __init__(self, bot_data: Dict, parent=None):
        super().__init__(parent)
        self.bot_data = bot_data
        self.setup_ui()
        self.apply_style()
    
    def setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(15, 15, 15, 15)
        layout.setSpacing(10)
        
        # Nagłówek z nazwą bota
        header_layout = QHBoxLayout()
        
        self.bot_name = QLabel(f"🤖 {self.bot_data.get('name', 'Bot')}")
        self.bot_name.setObjectName("bot_analysis_name")
        header_layout.addWidget(self.bot_name)
        
        self.bot_status = QLabel(self.bot_data.get('status', 'Nieaktywny'))
        self.bot_status.setObjectName("bot_analysis_status")
        header_layout.addWidget(self.bot_status)
        
        header_layout.addStretch()
        layout.addLayout(header_layout)
        
        # Metryki wydajności
        metrics_layout = QGridLayout()
        
        # Zysk całkowity
        total_profit = self.bot_data.get('total_profit', 0)
        profit_color = "#4CAF50" if total_profit >= 0 else "#F44336"
        self.profit_card = PerformanceCard(
            "Zysk całkowity", 
            f"{total_profit:+.2f} USDT",
            f"{self.bot_data.get('profit_percentage', 0):+.2f}%",
            profit_color
        )
        metrics_layout.addWidget(self.profit_card, 0, 0)
        
        # Liczba transakcji
        self.trades_card = PerformanceCard(
            "Transakcje",
            str(self.bot_data.get('total_trades', 0)),
            f"Sukces: {self.bot_data.get('win_rate', 0):.1f}%",
            "#2196F3"
        )
        metrics_layout.addWidget(self.trades_card, 0, 1)
        
        # Maksymalny drawdown
        self.drawdown_card = PerformanceCard(
            "Max Drawdown",
            f"{self.bot_data.get('max_drawdown', 0):.2f}%",
            "Ryzyko",
            "#FF9800"
        )
        metrics_layout.addWidget(self.drawdown_card, 0, 2)
        
        # Sharpe Ratio
        self.sharpe_card = PerformanceCard(
            "Sharpe Ratio",
            f"{self.bot_data.get('sharpe_ratio', 0):.2f}",
            "Efektywność",
            "#9C27B0"
        )
        metrics_layout.addWidget(self.sharpe_card, 0, 3)
        
        layout.addLayout(metrics_layout)
        
        # Szczegółowe statystyki
        details_group = QGroupBox("Szczegółowe statystyki")
        details_layout = QVBoxLayout(details_group)
        
        self.details_table = QTableWidget(0, 2)
        self.details_table.setHorizontalHeaderLabels(["Metryka", "Wartość"])
        self.details_table.horizontalHeader().setStretchLastSection(True)
        self.details_table.setAlternatingRowColors(True)
        
        # Dodaj szczegółowe dane
        self.populate_details_table()
        
        details_layout.addWidget(self.details_table)
        layout.addWidget(details_group)
    
    def populate_details_table(self):
        """Wypełnij tabelę szczegółowymi danymi"""
        details = [
            ("Strategia", self.bot_data.get('strategy', 'N/A')),
            ("Para walutowa", self.bot_data.get('symbol', 'N/A')),
            ("Kapitał początkowy", f"{self.bot_data.get('initial_capital', 0):.2f} USDT"),
            ("Kapitał aktualny", f"{self.bot_data.get('current_capital', 0):.2f} USDT"),
            ("Średni zysk na transakcję", f"{self.bot_data.get('avg_profit_per_trade', 0):.2f} USDT"),
            ("Średnia strata na transakcję", f"{self.bot_data.get('avg_loss_per_trade', 0):.2f} USDT"),
            ("Najdłuższa seria wygranych", str(self.bot_data.get('longest_win_streak', 0))),
            ("Najdłuższa seria przegranych", str(self.bot_data.get('longest_loss_streak', 0))),
            ("Czas działania", self.bot_data.get('runtime', 'N/A')),
            ("Ostatnia transakcja", self.bot_data.get('last_trade_time', 'N/A'))
        ]
        
        self.details_table.setRowCount(len(details))
        for i, (metric, value) in enumerate(details):
            self.details_table.setItem(i, 0, QTableWidgetItem(metric))
            self.details_table.setItem(i, 1, QTableWidgetItem(str(value)))
    
    def apply_style(self):
        self.setStyleSheet("""
            BotAnalysisWidget {
                background-color: #1e1e1e;
                border: 1px solid #333;
                border-radius: 8px;
                margin: 5px;
            }
            
            QLabel#bot_analysis_name {
                color: #ffffff;
                font-size: 16px;
                font-weight: bold;
            }
            
            QLabel#bot_analysis_status {
                color: #4CAF50;
                font-size: 12px;
                font-weight: 500;
                padding: 4px 8px;
                background-color: #4CAF5022;
                border-radius: 4px;
            }
            
            QGroupBox {
                color: #ffffff;
                font-weight: bold;
                border: 1px solid #444;
                border-radius: 5px;
                margin-top: 10px;
                padding-top: 10px;
            }
            
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 10px;
                padding: 0 5px 0 5px;
            }
            
            QTableWidget {
                background-color: #2a2a2a;
                color: #ffffff;
                border: 1px solid #444;
                border-radius: 4px;
                gridline-color: #444;
            }
            
            QTableWidget::item {
                padding: 8px;
                border-bottom: 1px solid #333;
            }
            
            QTableWidget::item:selected {
                background-color: #0078d4;
            }
            
            QHeaderView::section {
                background-color: #333;
                color: #ffffff;
                padding: 8px;
                border: none;
                font-weight: bold;
            }
        """)

class AnalysisWidget(QWidget):
    """Główny widget analizy wydajności"""
    
    def __init__(self, parent=None, trading_manager=None, integrated_data_manager=None):
        super().__init__(parent)
        self.config_manager = get_config_manager()
        self.trading_manager = trading_manager
        self.integrated_data_manager = integrated_data_manager
        self.setup_ui()
        self.apply_style()
        self.load_analysis_data()
        # Uruchom automatyczne odświeżanie danych analizy
        self.start_refresh_timer()
    
    def setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(15)
        
        # Nagłówek
        header_layout = QHBoxLayout()
        
        self.title_label = QLabel("📊 Analiza wydajności")
        self.title_label.setObjectName("analysis_title")
        header_layout.addWidget(self.title_label)
        
        header_layout.addStretch()
        
        # Przycisk odświeżania
        self.refresh_btn = QPushButton("🔄 Odśwież")
        self.refresh_btn.setObjectName("refresh_button")
        self.refresh_btn.clicked.connect(self.refresh_analysis)
        header_layout.addWidget(self.refresh_btn)
        
        layout.addLayout(header_layout)
        
        # Zakładki analizy
        self.tab_widget = QTabWidget()
        self.tab_widget.setObjectName("analysis_tabs")
        
        # Zakładka przeglądu ogólnego
        self.overview_tab = self.create_overview_tab()
        self.tab_widget.addTab(self.overview_tab, "📈 Przegląd ogólny")
        
        # Zakładka analizy botów
        self.bots_tab = self.create_bots_tab()
        self.tab_widget.addTab(self.bots_tab, "🤖 Analiza botów")
        
        # Zakładka analizy strategii
        self.strategies_tab = self.create_strategies_tab()
        self.tab_widget.addTab(self.strategies_tab, "🎯 Analiza strategii")
        
        # Zakładka ryzyka
        self.risk_tab = self.create_risk_tab()
        self.tab_widget.addTab(self.risk_tab, "⚠️ Analiza ryzyka")
        
        # Zakładka wykresów cenowych
        self.charts_tab = self.create_charts_tab()
        self.tab_widget.addTab(self.charts_tab, "📊 Wykresy cenowe")
        
        layout.addWidget(self.tab_widget)
    
    def create_overview_tab(self):
        """Utwórz zakładkę przeglądu ogólnego"""
        tab = QWidget()
        layout = QVBoxLayout(tab)
        layout.setSpacing(15)
        
        # Karty z głównymi metrykami
        metrics_layout = QGridLayout()
        
        self.total_profit_card = PerformanceCard(
            "Zysk całkowity", "0.00 USDT", "+0.00%", "#4CAF50"
        )
        metrics_layout.addWidget(self.total_profit_card, 0, 0)
        
        self.active_bots_card = PerformanceCard(
            "Aktywne boty", "0", "Działające", "#2196F3"
        )
        metrics_layout.addWidget(self.active_bots_card, 0, 1)
        
        self.total_trades_card = PerformanceCard(
            "Transakcje dzisiaj", "0", "Wszystkie boty", "#FF9800"
        )
        metrics_layout.addWidget(self.total_trades_card, 0, 2)
        
        self.win_rate_card = PerformanceCard(
            "Średni win rate", "0%", "Wszystkie strategie", "#9C27B0"
        )
        metrics_layout.addWidget(self.win_rate_card, 0, 3)
        
        layout.addLayout(metrics_layout)
        
        # Wykres wydajności
        performance_group = QGroupBox("Wykres wydajności w czasie")
        performance_layout = QVBoxLayout(performance_group)
        
        try:
            from ui.charts import create_chart_widget
            self.performance_chart = create_chart_widget("performance")
            performance_layout.addWidget(self.performance_chart)
        except Exception as e:
            try:
                logger.error(f"Błąd ładowania wykresu wydajności: {e}")
            except Exception:
                pass
            self.performance_chart = QLabel("📈 Błąd ładowania wykresu wydajności")
            self.performance_chart.setAlignment(Qt.AlignmentFlag.AlignCenter)
            self.performance_chart.setMinimumHeight(300)
            self.performance_chart.setStyleSheet("""
                QLabel {
                    background-color: #2a2a2a;
                    border: 1px solid #444;
                    border-radius: 8px;
                    color: #888;
                    font-size: 16px;
                }
            """)
            performance_layout.addWidget(self.performance_chart)
        
        layout.addWidget(performance_group)
        
        return tab
    
    def create_bots_tab(self):
        """Utwórz zakładkę analizy botów"""
        tab = QWidget()
        layout = QVBoxLayout(tab)
        
        # Filtr botów
        filter_layout = QHBoxLayout()
        
        filter_layout.addWidget(QLabel("Filtruj boty:"))
        
        self.bot_filter = QComboBox()
        self.bot_filter.addItems(["Wszystkie", "Aktywne", "Nieaktywne", "Zyskowne", "Stratne"])
        self.bot_filter.currentTextChanged.connect(self.filter_bots)
        filter_layout.addWidget(self.bot_filter)
        
        filter_layout.addStretch()
        layout.addLayout(filter_layout)
        
        # Scroll area dla botów
        self.bots_scroll = QScrollArea()
        self.bots_scroll.setWidgetResizable(True)
        self.bots_scroll.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        
        self.bots_container = QWidget()
        self.bots_layout = QVBoxLayout(self.bots_container)
        self.bots_layout.setSpacing(10)
        
        self.bots_scroll.setWidget(self.bots_container)
        layout.addWidget(self.bots_scroll)
        
        return tab
    
    def create_strategies_tab(self):
        """Utwórz zakładkę analizy strategii"""
        tab = QWidget()
        layout = QVBoxLayout(tab)
        
        # Tabela strategii
        self.strategies_table = QTableWidget(0, 6)
        self.strategies_table.setHorizontalHeaderLabels([
            "Strategia", "Boty", "Zysk całkowity", "Win Rate", "Avg Profit", "Max Drawdown"
        ])
        self.strategies_table.horizontalHeader().setStretchLastSection(True)
        self.strategies_table.setAlternatingRowColors(True)
        
        layout.addWidget(self.strategies_table)
        
        return tab
    
    def create_risk_tab(self):
        """Utwórz zakładkę analizy ryzyka"""
        tab = QWidget()
        layout = QVBoxLayout(tab)
        
        # Metryki ryzyka
        risk_metrics_layout = QGridLayout()
        
        self.portfolio_risk_card = PerformanceCard(
            "Ryzyko portfela", "Średnie", "Ocena ogólna", "#FF9800"
        )
        risk_metrics_layout.addWidget(self.portfolio_risk_card, 0, 0)
        
        self.max_drawdown_card = PerformanceCard(
            "Max Drawdown", "0%", "Wszystkie boty", "#F44336"
        )
        risk_metrics_layout.addWidget(self.max_drawdown_card, 0, 1)
        
        self.var_card = PerformanceCard(
            "Value at Risk", "0 USDT", "95% VaR", "#9C27B0"
        )
        risk_metrics_layout.addWidget(self.var_card, 0, 2)
        
        layout.addLayout(risk_metrics_layout)
        
        # Szczegółowa analiza ryzyka
        risk_details = QGroupBox("Szczegółowa analiza ryzyka")
        risk_details_layout = QVBoxLayout(risk_details)
        
        self.risk_text = QTextEdit()
        self.risk_text.setReadOnly(True)
        self.risk_text.setMaximumHeight(200)
        self.risk_text.setText("Analiza ryzyka zostanie wygenerowana na podstawie danych z botów...")
        
        risk_details_layout.addWidget(self.risk_text)
        layout.addWidget(risk_details)
        
        return tab
    
    def load_analysis_data(self):
        """Załaduj dane analizy bez blokowania wątku UI"""
        try:
            self.sample_bots_data = []
            async_manager = get_async_manager()

            # 1) Asynchroniczne pobranie danych botów
            bots_task_id = async_manager.run_async(self.get_real_bots_data())

            def _on_bots_finished(tid, result):
                if tid != bots_task_id:
                    return
                try:
                    # Odłącz slot po obsłudze, by uniknąć duplikacji
                    try:
                        async_manager.task_finished.disconnect(_on_bots_finished)
                    except Exception:
                        pass

                    bot_data = result or []
                    if bot_data:
                        self.sample_bots_data = bot_data
                        self.update_overview_metrics()
                        self.populate_bots_analysis()
                        self.populate_strategies_analysis()
                        self.update_risk_metrics()
                        return

                    # 2) Fallback do statystyk trybu (paper/live)
                    if hasattr(self, 'trading_manager') and self.trading_manager:
                        async def _fetch_stats():
                            try:
                                if self.trading_manager.is_paper_mode():
                                    stats = await self.trading_manager.get_paper_statistics()
                                    return stats, "Paper Trading", "#4CAF50"
                                stats = await self.trading_manager.get_live_statistics()
                                return stats, "Live Trading", "#FF5722"
                            except Exception as exc:
                                logger.warning(f"Error fetching trading stats: {exc}")
                                return None

                        stats_task_id = async_manager.run_async(_fetch_stats())

                        def _on_stats_finished(stid, sresult):
                            if stid != stats_task_id:
                                return
                            try:
                                try:
                                    async_manager.task_finished.disconnect(_on_stats_finished)
                                except Exception:
                                    pass
                                if not sresult:
                                    self.update_overview_metrics()
                                    self.populate_bots_analysis()
                                    self.populate_strategies_analysis()
                                    self.update_risk_metrics()
                                    return
                                stats, mode_text, mode_color = sresult
                                self.sample_bots_data = [{
                                    'name': f'System - {mode_text}',
                                    'status': 'Aktywny',
                                    'strategy': mode_text,
                                    'symbol': 'SYSTEM',
                                    'total_profit': stats.get('total_pnl', 0.0),
                                    'profit_percentage': stats.get('total_return', 0.0),
                                    'total_trades': stats.get('trades_count', 0),
                                    'win_rate': 0.0,
                                    'max_drawdown': 0.0,
                                    'sharpe_ratio': 0.0,
                                    'initial_capital': stats.get('initial_balance', 10000.0),
                                    'current_capital': stats.get('total_value', 10000.0),
                                    'avg_profit_per_trade': 0.0,
                                    'avg_loss_per_trade': 0.0,
                                    'longest_win_streak': 0,
                                    'longest_loss_streak': 0,
                                    'runtime': 'Aktywny',
                                    'last_trade_time': datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                                    'mode': mode_text,
                                    'mode_color': mode_color
                                }]
                                self.update_overview_metrics()
                                self.populate_bots_analysis()
                                self.populate_strategies_analysis()
                                self.update_risk_metrics()
                            except Exception as exc2:
                                logger.error(f"Error applying trading stats: {exc2}")
                                self.update_overview_metrics()
                                self.populate_bots_analysis()
                                self.populate_strategies_analysis()
                                self.update_risk_metrics()

                        async_manager.task_finished.connect(_on_stats_finished)
                    else:
                        self.update_overview_metrics()
                        self.populate_bots_analysis()
                        self.populate_strategies_analysis()
                        self.update_risk_metrics()
                except Exception as e:
                    logger.error(f"Błąd przetwarzania danych analizy: {e}")
                    self.update_overview_metrics()
                    self.populate_bots_analysis()
                    self.populate_strategies_analysis()
                    self.update_risk_metrics()

            async_manager.task_finished.connect(_on_bots_finished)

        except Exception as e:
            logger.error(f"Błąd podczas ładowania danych analizy: {e}")
    
    async def get_real_bots_data(self):
        """Pobierz prawdziwe dane botów z bazy danych"""
        try:
            # Najpierw spróbuj pobrać dane z IntegratedDataManager
            if hasattr(self, 'integrated_data_manager') and self.integrated_data_manager:
                try:
                    bots = await self.integrated_data_manager.get_bots_data()
                    if bots:
                        bots_data = []
                        for bot in bots:
                            bots_data.append(self.convert_botdata_to_dict(bot))
                        return bots_data
                    else:
                        return []
                except Exception as e:
                    logger.warning(f"Błąd pobierania danych z IntegratedDataManager: {e}")
                    # Fallback do trading_manager poniżej
            
            # Sprawdź czy mamy dostęp do trading managera
            if hasattr(self, 'trading_manager') and self.trading_manager:
                # Sprawdź czy trading_manager ma metodę get_active_bots
                if hasattr(self.trading_manager, 'get_active_bots'):
                    try:
                        # Pobierz aktywne boty
                        active_bots = await self.trading_manager.get_active_bots()
                        
                        if not active_bots:
                            return []
                        
                        bots_data = []
                        for bot in active_bots:
                            try:
                                # Pobierz statystyki bota
                                bot_stats = await self.trading_manager.get_bot_statistics(bot.get('id'))
                                
                                bot_data = {
                                    'name': bot.get('name', 'Nieznany Bot'),
                                    'status': 'Aktywny' if bot.get('active', False) else 'Nieaktywny',
                                    'strategy': bot.get('strategy', 'N/A'),
                                    'symbol': bot.get('symbol', 'N/A'),
                                    'total_profit': bot_stats.get('total_pnl', 0.0),
                                    'profit_percentage': bot_stats.get('return_percentage', 0.0),
                                    'total_trades': bot_stats.get('trades_count', 0),
                                    'win_rate': bot_stats.get('win_rate', 0.0),
                                    'max_drawdown': bot_stats.get('max_drawdown', 0.0),
                                    'sharpe_ratio': bot_stats.get('sharpe_ratio', 0.0),
                                    'initial_capital': bot_stats.get('initial_balance', 0.0),
                                    'current_capital': bot_stats.get('current_balance', 0.0),
                                    'avg_profit_per_trade': bot_stats.get('avg_profit', 0.0),
                                    'avg_loss_per_trade': bot_stats.get('avg_loss', 0.0),
                                    'longest_win_streak': bot_stats.get('max_win_streak', 0),
                                    'longest_loss_streak': bot_stats.get('max_loss_streak', 0),
                                    'runtime': bot_stats.get('runtime', 'N/A'),
                                    'last_trade_time': bot_stats.get('last_trade_time', 'N/A')
                                }
                                
                                bots_data.append(bot_data)
                                
                            except Exception as e:
                                logger.warning(f"Błąd pobierania statystyk bota {bot.get('name', 'Unknown')}: {e}")
                                continue
                        
                        return bots_data
                        
                    except Exception as e:
                        logger.warning(f"Błąd wywołania get_active_bots: {e}")
                        # Fallback: brak danych
                        return []
                else:
                    logger.info("Trading manager nie ma metody get_active_bots – brak danych")
                    return []
            else:
                logger.info("Brak trading managera – brak danych")
                return []
                
        except Exception as e:
            logger.error(f"Błąd pobierania danych botów: {e}")
            return []
    
    def update_overview_metrics(self):
        """Aktualizuj metryki przeglądu ogólnego"""
        total_profit = sum(bot['total_profit'] for bot in self.sample_bots_data)
        active_bots = len([bot for bot in self.sample_bots_data if bot['status'] == 'Aktywny'])
        total_trades = sum(bot['total_trades'] for bot in self.sample_bots_data)
        count = len(self.sample_bots_data)
        avg_win_rate = (sum(bot['win_rate'] for bot in self.sample_bots_data) / count) if count > 0 else 0.0
        
        self.total_profit_card.update_values(f"{total_profit:+.2f} USDT")
        self.active_bots_card.update_values(str(active_bots))
        self.total_trades_card.update_values(str(total_trades))
        self.win_rate_card.update_values(f"{avg_win_rate:.1f}%")
    
    def populate_bots_analysis(self):
        """Wypełnij analizę botów"""
        # Wyczyść poprzednie elementy bezpiecznie (widgety i spacery)
        for i in reversed(range(self.bots_layout.count())):
            item = self.bots_layout.itemAt(i)
            try:
                w = item.widget()
            except Exception:
                w = None
            if w is not None:
                try:
                    w.setParent(None)
                except Exception:
                    pass
            else:
                try:
                    self.bots_layout.removeItem(item)
                except Exception:
                    pass
        
        # Jeśli brak danych – pokaż przyjazny pusty stan
        if not self.sample_bots_data or len(self.sample_bots_data) == 0:
            from PyQt6.QtWidgets import QLabel
            from PyQt6.QtCore import Qt
            empty_label = QLabel("Brak danych botów do analizy")
            empty_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
            empty_label.setStyleSheet("color: #9E9E9E; font-size: 14px; padding: 16px;")
            self.bots_layout.addWidget(empty_label)
            self.bots_layout.addStretch()
            return
        
        # Dodaj widgety analizy dla każdego bota
        for bot_data in self.sample_bots_data:
            bot_widget = BotAnalysisWidget(bot_data)
            self.bots_layout.addWidget(bot_widget)
        
        self.bots_layout.addStretch()
        
    def populate_strategies_analysis(self):
        """Wypełnij analizę strategii"""
        strategies = {}
        
        # Jeśli brak danych – wyczyść tabelę i zakończ
        if len(self.sample_bots_data) == 0:
            self.strategies_table.setRowCount(0)
            return
        
        # Grupuj boty według strategii
        for bot in self.sample_bots_data:
            strategy = bot.get('strategy', 'Nieznana')
            if strategy not in strategies:
                strategies[strategy] = {
                    'bots': 0,
                    'total_profit': 0.0,
                    'total_trades': 0,
                    'win_rates': [],
                    'drawdowns': []
                }
            # agregacja metryk dla strategii
            strategies[strategy]['bots'] += 1
            strategies[strategy]['total_profit'] += float(bot.get('total_profit', 0.0))
            strategies[strategy]['total_trades'] += int(bot.get('total_trades', 0))
            win_rate = bot.get('win_rate', 0.0)
            if win_rate is not None:
                strategies[strategy]['win_rates'].append(float(win_rate))
            drawdown = bot.get('max_drawdown', 0.0)
            if drawdown is not None:
                strategies[strategy]['drawdowns'].append(float(drawdown))
        
        # Wypełnij tabelę
        self.strategies_table.setRowCount(len(strategies))
        for i, (strategy, data) in enumerate(strategies.items()):
            win_rates_count = len(data['win_rates'])
            avg_win_rate = (sum(data['win_rates']) / win_rates_count) if win_rates_count > 0 else 0.0
            avg_profit = (data['total_profit'] / data['total_trades']) if data['total_trades'] > 0 else 0.0
            max_drawdown = max(data['drawdowns']) if len(data['drawdowns']) > 0 else 0.0
            
            self.strategies_table.setItem(i, 0, QTableWidgetItem(strategy))
            self.strategies_table.setItem(i, 1, QTableWidgetItem(str(data['bots'])))
            self.strategies_table.setItem(i, 2, QTableWidgetItem(f"{data['total_profit']:+.2f} USDT"))
            self.strategies_table.setItem(i, 3, QTableWidgetItem(f"{avg_win_rate:.1f}%"))
            self.strategies_table.setItem(i, 4, QTableWidgetItem(f"{avg_profit:.2f} USDT"))
            self.strategies_table.setItem(i, 5, QTableWidgetItem(f"{max_drawdown:.2f}%"))
    
    def update_risk_metrics(self):
        """Aktualizuj metryki ryzyka w zakładce ryzyka"""
        try:
            import asyncio
            metrics = None
            portfolio_value = 0.0

            # Preferuj IntegratedDataManager – bez fallbacku na DataManager (żeby nie wstawiać fałszywych danych)
            try:
                if hasattr(self, 'integrated_data_manager') and self.integrated_data_manager:
                    if hasattr(self.integrated_data_manager, 'get_risk_metrics'):
                        try:
                            asyncio.get_running_loop()
                            import concurrent.futures
                            with concurrent.futures.ThreadPoolExecutor() as executor:
                                future = executor.submit(asyncio.run, self.integrated_data_manager.get_risk_metrics())
                                metrics = future.result(timeout=4)
                        except RuntimeError:
                            metrics = asyncio.run(self.integrated_data_manager.get_risk_metrics())
                    if hasattr(self.integrated_data_manager, 'get_portfolio_summary'):
                        try:
                            asyncio.get_running_loop()
                            import concurrent.futures
                            with concurrent.futures.ThreadPoolExecutor() as executor:
                                future = executor.submit(asyncio.run, self.integrated_data_manager.get_portfolio_summary())
                                summary = future.result(timeout=4)
                        except RuntimeError:
                            summary = asyncio.run(self.integrated_data_manager.get_portfolio_summary())
                        if summary is not None:
                            if isinstance(summary, dict):
                                portfolio_value = summary.get('total_value', 0.0) or 0.0
                            else:
                                portfolio_value = getattr(summary, 'total_value', 0.0) or 0.0
            except Exception as e:
                logger.warning(f"Błąd pobierania metryk ryzyka z IntegratedDataManager: {e}")
                metrics = None

            # Zawsze aktualizuj widok, nawet gdy brak metryk – wówczas pokaż 0.00/0%
            try:
                var_percent_1d = (getattr(metrics, 'var_1d', 0.0) or 0.0)
                var_percent_7d = (getattr(metrics, 'var_7d', 0.0) or 0.0)
                sharpe = (getattr(metrics, 'sharpe_ratio', 0.0) or 0.0)
                max_dd = (getattr(metrics, 'max_drawdown', 0.0) or 0.0)
                volatility = (getattr(metrics, 'volatility', 0.0) or 0.0)
                beta = (getattr(metrics, 'beta', 0.0) or 0.0)
                last_calc = getattr(metrics, 'last_calculated', None) if metrics else None

                # VaR w USDT (jeśli brak wartości portfela, traktuj jak 0)
                var_usdt_1d = (portfolio_value or 0.0) * var_percent_1d

                # Określ poziom ryzyka na podstawie DD/volatility – przy braku danych (0) będzie to niskie
                vol_pct = volatility * 100.0
                md_pct = max_dd * 100.0
                if md_pct < 10 and vol_pct < 20:
                    risk_level_text = "Niskie"
                elif md_pct < 20 and vol_pct < 35:
                    risk_level_text = "Średnie"
                else:
                    risk_level_text = "Wysokie"

                # Aktualizacje kart – zawsze pokazuj wartości (z zerowym fallbackiem)
                self.portfolio_risk_card.update_values(risk_level_text, f"Sharpe {sharpe:.2f}, Vol {vol_pct:.1f}%")
                self.max_drawdown_card.update_values(f"{md_pct:.2f}%", "Wszystkie boty")
                self.var_card.update_values(f"{var_usdt_1d:,.2f} USDT", "95% VaR")

                # Tekst szczegółowy
                details_lines = []
                if last_calc:
                    try:
                        ts = last_calc if isinstance(last_calc, datetime) else datetime.fromisoformat(str(last_calc))
                        details_lines.append(f"Ostatnia kalkulacja: {ts.strftime('%Y-%m-%d %H:%M:%S')}")
                    except Exception:
                        pass
                details_lines.append(f"VaR 1d: {var_percent_1d*100:.2f}% (~{var_usdt_1d:,.2f} USDT)")
                details_lines.append(f"VaR 7d: {var_percent_7d*100:.2f}%")
                details_lines.append(f"Max Drawdown: {md_pct:.2f}%")
                details_lines.append(f"Sharpe Ratio: {sharpe:.2f}")
                details_lines.append(f"Volatility: {vol_pct:.2f}%")
                details_lines.append(f"Beta: {beta:.2f}")

                self.risk_text.setText("\n".join(details_lines))
            except Exception as e:
                logger.error(f"Błąd aktualizacji kart ryzyka: {e}")
        except Exception as e:
            logger.error(f"Błąd w update_risk_metrics: {e}")
    
    def filter_bots(self, filter_text):
        """Filtruj boty według wybranego kryterium"""
        # Implementacja filtrowania botów
        pass
    
    def refresh_analysis(self):
        """Odśwież dane analizy"""
        self.load_analysis_data()
        logger.info("Dane analizy zostały odświeżone")
    
    def create_charts_tab(self):
        """Utwórz zakładkę wykresów cenowych"""
        tab = QWidget()
        layout = QVBoxLayout(tab)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(15)
        
        # Tytuł
        title = QLabel("📊 Wykresy cenowe")
        title.setStyleSheet("font-size: 20px; font-weight: bold; color: white; margin-bottom: 15px;")
        layout.addWidget(title)
        
        # Wykres świecowy
        try:
            from ui.charts import create_chart_widget
            candlestick_chart = create_chart_widget("candlestick", symbol="BTCUSDT")
            layout.addWidget(candlestick_chart)
        except Exception as e:
            try:
                logger.error(f"Błąd ładowania wykresów cenowych: {e}")
            except Exception:
                pass
            placeholder = QLabel("📈 Błąd ładowania wykresów cenowych")
            placeholder.setAlignment(Qt.AlignmentFlag.AlignCenter)
            placeholder.setMinimumHeight(400)
            placeholder.setStyleSheet("""
                QLabel {
                    background-color: #2a2a2a;
                    border: 1px solid #444;
                    border-radius: 8px;
                    color: #888;
                    font-size: 16px;
                }
            """)
            layout.addWidget(placeholder)
        
        return tab
    
    def apply_style(self):
        self.setStyleSheet("""
            AnalysisWidget {
                background-color: #1a1a1a;
                color: #ffffff;
            }
            
            QLabel#analysis_title {
                color: #ffffff;
                font-size: 24px;
                font-weight: bold;
                margin-bottom: 10px;
            }
            
            QPushButton#refresh_button {
                background-color: #0078d4;
                color: white;
                border: none;
                border-radius: 6px;
                padding: 8px 16px;
                font-weight: 500;
                font-size: 13px;
            }
            
            QPushButton#refresh_button:hover {
                background-color: #106ebe;
            }
            
            QPushButton#refresh_button:pressed {
                background-color: #005a9e;
            }
            
            QTabWidget#analysis_tabs {
                background-color: #1e1e1e;
                border: none;
            }
            
            QTabWidget#analysis_tabs::pane {
                border: 1px solid #333;
                border-radius: 8px;
                background-color: #1e1e1e;
            }
            
            QTabWidget#analysis_tabs::tab-bar {
                alignment: left;
            }
            
            QTabBar::tab {
                background-color: #2a2a2a;
                color: #ffffff;
                border: 1px solid #444;
                border-bottom: none;
                border-top-left-radius: 6px;
                border-top-right-radius: 6px;
                padding: 8px 16px;
                margin-right: 2px;
                font-weight: 500;
            }
            
            QTabBar::tab:selected {
                background-color: #0078d4;
                border-color: #0078d4;
            }
            
            QTabBar::tab:hover:!selected {
                background-color: #333;
            }
            
            QScrollArea {
                border: none;
                background-color: transparent;
            }
            
            QComboBox {
                background-color: #2a2a2a;
                color: #ffffff;
                border: 1px solid #444;
                border-radius: 4px;
                padding: 6px 12px;
                min-width: 120px;
            }
            
            QComboBox::drop-down {
                border: none;
                width: 20px;
            }
            
            QComboBox::down-arrow {
                image: none;
                border-left: 5px solid transparent;
                border-right: 5px solid transparent;
                border-top: 5px solid #ffffff;
                margin-right: 5px;
            }
            
            QComboBox QAbstractItemView {
                background-color: #2a2a2a;
                color: #ffffff;
                border: 1px solid #444;
                selection-background-color: #0078d4;
            }
        """)

    def convert_botdata_to_dict(self, bot_obj):
        """Konwertuje obiekt BotData do słownika oczekiwanego przez UI"""
        try:
            status_text = 'Aktywny' if bool(getattr(bot_obj, 'active', False)) else 'Nieaktywny'
            last_trade_dt = getattr(bot_obj, 'last_trade', None)
            last_trade_str = last_trade_dt.strftime("%Y-%m-%d %H:%M:%S") if last_trade_dt else 'N/A'
            return {
                'name': getattr(bot_obj, 'name', 'Nieznany Bot'),
                'status': status_text,
                'strategy': getattr(bot_obj, 'risk_level', 'Standard'),
                'symbol': 'N/A',
                'total_profit': float(getattr(bot_obj, 'profit', 0.0) or 0.0),
                'profit_percentage': float(getattr(bot_obj, 'profit_percent', 0.0) or 0.0),
                'total_trades': int(getattr(bot_obj, 'trades_count', 0) or 0),
                'win_rate': 0.0,
                'max_drawdown': 0.0,
                'sharpe_ratio': 0.0,
                'initial_capital': 0.0,
                'current_capital': 0.0,
                'avg_profit_per_trade': 0.0,
                'avg_loss_per_trade': 0.0,
                'longest_win_streak': 0,
                'longest_loss_streak': 0,
                'runtime': 'N/A',
                'last_trade_time': last_trade_str
            }
        except Exception as e:
            logger.warning(f"Błąd konwersji BotData: {e}")
            return {
                'name': 'Nieznany Bot',
                'status': 'Nieaktywny',
                'strategy': 'N/A',
                'symbol': 'N/A',
                'total_profit': 0.0,
                'profit_percentage': 0.0,
                'total_trades': 0,
                'win_rate': 0.0,
                'max_drawdown': 0.0,
                'sharpe_ratio': 0.0,
                'initial_capital': 0.0,
                'current_capital': 0.0,
                'avg_profit_per_trade': 0.0,
                'avg_loss_per_trade': 0.0,
                'longest_win_streak': 0,
                'longest_loss_streak': 0,
                'runtime': 'N/A',
                'last_trade_time': 'N/A'
            }
    

    def start_refresh_timer(self):
        """Uruchamia automatyczne odświeżanie danych analizy"""
        try:
            if not hasattr(self, 'refresh_timer') or self.refresh_timer is None:
                self.refresh_timer = QTimer(self)
                self.refresh_timer.timeout.connect(self.refresh_analysis)
            interval = get_app_setting('analysis_refresh_interval', 30000)  # domyślnie 30s
            self.refresh_timer.start(interval)
            logger.info(f"Analysis auto-refresh started (interval: {interval} ms)")
        except Exception as e:
            logger.error(f"Błąd uruchamiania timera analizy: {e}")
    
    def closeEvent(self, event):
        """Zatrzymuje timer odświeżania przy zamknięciu widgetu"""
        try:
            if hasattr(self, 'refresh_timer') and self.refresh_timer and self.refresh_timer.isActive():
                self.refresh_timer.stop()
                logger.info("Analysis auto-refresh stopped")
        except Exception as e:
            logger.error(f"Błąd zatrzymywania timera analizy: {e}")
        try:
            super().closeEvent(event)
        except Exception:
            pass
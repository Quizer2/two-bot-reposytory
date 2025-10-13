"""
Moduł wykresów dla aplikacji trading bot
Zawiera implementacje wykresów cenowych, wydajności i alokacji portfela
"""

import sys
import os
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Tuple
import json
from utils.config_manager import get_app_setting

try:
    import pandas as pd
    import numpy as np
    PANDAS_AVAILABLE = True
except ImportError:
    PANDAS_AVAILABLE = False
    print("Pandas not available")

try:
    import matplotlib.pyplot as plt
    import matplotlib.dates as mdates
    from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
    from matplotlib.figure import Figure
    import mplfinance as mpf
    MATPLOTLIB_AVAILABLE = True
except ImportError:
    MATPLOTLIB_AVAILABLE = False
    print("Matplotlib not available")

try:
    from PyQt6.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QComboBox
    from PyQt6.QtCore import Qt, QTimer, pyqtSignal
    from PyQt6.QtGui import QFont
    PYQT_AVAILABLE = True
except ImportError:
    PYQT_AVAILABLE = False
    print("PyQt6 not available")

# Dodaj ścieżkę do głównego katalogu
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from utils.logger import get_logger
from api.binance_api import BinanceAPI

logger = get_logger(__name__)

class CandlestickChart(QWidget):
    """Widget wykresu świecowego z danymi cenowymi"""
    
    def __init__(self, symbol: str = "BTCUSDT", parent=None):
        super().__init__(parent)
        self.symbol = symbol
        self.timeframe = "1h"
        self.api = BinanceAPI()
        self.setup_ui()
        self.load_data()
        self.start_refresh_timer()
    
    def setup_ui(self):
        """Konfiguruje interfejs użytkownika"""
        layout = QVBoxLayout(self)
        
        # Panel kontrolny
        controls_layout = QHBoxLayout()
        
        # Wybór symbolu
        self.symbol_combo = QComboBox()
        self.symbol_combo.addItems(["BTCUSDT", "ETHUSDT", "ADAUSDT", "DOTUSDT", "LINKUSDT"])
        self.symbol_combo.setCurrentText(self.symbol)
        self.symbol_combo.currentTextChanged.connect(self.on_symbol_changed)
        controls_layout.addWidget(QLabel("Symbol:"))
        controls_layout.addWidget(self.symbol_combo)
        
        # Wybór timeframe
        self.timeframe_combo = QComboBox()
        self.timeframe_combo.addItems(["1m", "5m", "15m", "1h", "4h", "1d"])
        self.timeframe_combo.setCurrentText(self.timeframe)
        self.timeframe_combo.currentTextChanged.connect(self.on_timeframe_changed)
        controls_layout.addWidget(QLabel("Timeframe:"))
        controls_layout.addWidget(self.timeframe_combo)
        
        # Przycisk odświeżania
        refresh_btn = QPushButton("Odśwież")
        refresh_btn.clicked.connect(self.load_data)
        controls_layout.addWidget(refresh_btn)
        
        controls_layout.addStretch()
        layout.addLayout(controls_layout)
        
        # Wykres
        if MATPLOTLIB_AVAILABLE:
            self.figure = Figure(figsize=(12, 8), facecolor='#2b2b2b')
            self.canvas = FigureCanvas(self.figure)
            layout.addWidget(self.canvas)
        else:
            placeholder = QLabel("Matplotlib nie jest dostępne - wykres niedostępny")
            placeholder.setAlignment(Qt.AlignmentFlag.AlignCenter)
            placeholder.setStyleSheet("font-size: 16px; color: #666; padding: 50px;")
            layout.addWidget(placeholder)
    
    def on_symbol_changed(self, symbol: str):
        """Obsługuje zmianę symbolu"""
        self.symbol = symbol
        self.load_data()
    
    def on_timeframe_changed(self, timeframe: str):
        """Obsługuje zmianę timeframe"""
        self.timeframe = timeframe
        self.load_data()
    
    def load_data(self):
        """Ładuje dane cenowe z API"""
        if not MATPLOTLIB_AVAILABLE:
            return
            
        try:
            # Pobierz dane z Binance - get_klines już zwraca gotowy DataFrame
            df = self.api.get_klines(self.symbol, self.timeframe, limit=100)
            
            if df.empty:
                logger.warning(f"Brak danych dla {self.symbol}")
                self.plot_error_message(f"Brak danych dla {self.symbol}")
                return
            
            logger.info(f"Załadowano {len(df)} świec dla {self.symbol}")
            self.plot_candlestick(df)
            
        except Exception as e:
            logger.error(f"Błąd podczas ładowania danych: {e}")
            self.plot_error_message(str(e))
    
    def plot_candlestick(self, df: pd.DataFrame):
        """Rysuje wykres świecowy"""
        try:
            self.figure.clear()
            
            # Konfiguracja stylu
            style = mpf.make_mpf_style(
                base_mpl_style='dark_background',
                marketcolors=mpf.make_marketcolors(
                    up='#00ff88', down='#ff4444',
                    edge='inherit',
                    wick={'up': '#00ff88', 'down': '#ff4444'},
                    volume='in'
                )
            )
            
            # Rysuj wykres
            ax = self.figure.add_subplot(111)
            mpf.plot(df, type='candle', style=style, ax=ax, volume=False)
            
            # Konfiguracja osi
            ax.set_title(f'{self.symbol} - {self.timeframe}', color='white', fontsize=14, pad=20)
            ax.tick_params(colors='white')
            ax.grid(True, alpha=0.3)
            
            # Formatowanie dat na osi X
            ax.xaxis.set_major_formatter(mdates.DateFormatter('%H:%M' if self.timeframe in ['1m', '5m', '15m'] else '%m-%d'))
            ax.xaxis.set_major_locator(mdates.HourLocator(interval=4) if self.timeframe in ['1m', '5m', '15m'] else mdates.DayLocator())
            
            self.figure.tight_layout()
            self.canvas.draw()
            
        except Exception as e:
            logger.error(f"Błąd podczas rysowania wykresu: {e}")
            self.plot_error_message(str(e))
    
    def plot_error_message(self, error_msg: str):
        """Wyświetla komunikat o błędzie na wykresie"""
        self.figure.clear()
        ax = self.figure.add_subplot(111)
        ax.text(0.5, 0.5, f'Błąd ładowania danych:\n{error_msg}', 
                horizontalalignment='center', verticalalignment='center',
                transform=ax.transAxes, color='red', fontsize=12)
        ax.set_facecolor('#2b2b2b')
        self.canvas.draw()
    
    def start_refresh_timer(self):
        """Uruchamia automatyczne odświeżanie danych wykresu świecowego"""
        try:
            if not PYQT_AVAILABLE or not MATPLOTLIB_AVAILABLE:
                return
            if not hasattr(self, 'refresh_timer') or self.refresh_timer is None:
                self.refresh_timer = QTimer(self)
                self.refresh_timer.timeout.connect(self.load_data)
            interval = get_app_setting('charts_refresh_interval', 60000)  # domyślnie 60s
            self.refresh_timer.start(interval)
            logger.info(f"Candlestick chart auto-refresh started (interval: {interval} ms)")
        except Exception as e:
            logger.error(f"Błąd uruchamiania timera wykresu świecowego: {e}")
    
    def closeEvent(self, event):
        """Zatrzymuje timer odświeżania przy zamknięciu widgetu"""
        try:
            if hasattr(self, 'refresh_timer') and self.refresh_timer and self.refresh_timer.isActive():
                self.refresh_timer.stop()
                logger.info("Candlestick chart auto-refresh stopped")
        except Exception as e:
            logger.error(f"Błąd zatrzymywania timera wykresu świecowego: {e}")
        try:
            super().closeEvent(event)
        except Exception:
            pass


class PerformanceChart(QWidget):
    """Widget wykresu wydajności portfela"""
    
    def __init__(self, parent=None, integrated_data_manager=None):
        super().__init__(parent)
        self.integrated_data_manager = integrated_data_manager
        self.refresh_timer = None
        self.setup_ui()
        # Jeśli nie ma IDM, ładuj sample, inaczej spróbuj realnych danych
        if self.integrated_data_manager is None:
            self.load_sample_data()
        else:
            self.load_data()
            self.start_refresh_timer()
    
    def setup_ui(self):
        """Konfiguruje interfejs użytkownika"""
        layout = QVBoxLayout(self)
        
        # Tytuł
        title = QLabel("Wydajność Portfela")
        title.setStyleSheet("font-size: 18px; font-weight: bold; color: white; margin-bottom: 10px;")
        layout.addWidget(title)
        
        # Wykres
        if MATPLOTLIB_AVAILABLE:
            self.figure = Figure(figsize=(10, 6), facecolor='#2b2b2b')
            self.canvas = FigureCanvas(self.figure)
            layout.addWidget(self.canvas)
        else:
            placeholder = QLabel("Matplotlib nie jest dostępne - wykres niedostępny")
            placeholder.setAlignment(Qt.AlignmentFlag.AlignCenter)
            placeholder.setStyleSheet("font-size: 16px; color: #666; padding: 50px;")
            layout.addWidget(placeholder)
    
    def start_refresh_timer(self):
        try:
            if not PYQT_AVAILABLE or not MATPLOTLIB_AVAILABLE:
                return
            if self.refresh_timer is None:
                self.refresh_timer = QTimer(self)
                self.refresh_timer.timeout.connect(self.load_data)
            interval = get_app_setting('charts_refresh_interval', 60000)
            self.refresh_timer.start(interval)
            logger.info(f"Performance chart auto-refresh started (interval: {interval} ms)")
        except Exception as e:
            logger.error(f"Błąd uruchamiania timera wykresu wydajności: {e}")
    
    def closeEvent(self, event):
        try:
            if self.refresh_timer and self.refresh_timer.isActive():
                self.refresh_timer.stop()
                logger.info("Performance chart auto-refresh stopped")
        except Exception as e:
            logger.error(f"Błąd zatrzymywania timera wykresu wydajności: {e}")
        try:
            super().closeEvent(event)
        except Exception:
            pass
    
    def load_data(self):
        if not MATPLOTLIB_AVAILABLE:
            return
        try:
            if self.integrated_data_manager is None:
                self.load_sample_data()
                return
            # Asynchroniczne pobranie danych z IntegratedDataManager
            from ui.async_helper import get_async_manager
            async_manager = get_async_manager()
            async def _fetch():
                try:
                    return await self.integrated_data_manager.get_performance_history()
                except Exception as e:
                    logger.error(f"Error fetching performance history: {e}")
                    return None
            task_id = async_manager.run_async(_fetch())
            def on_finished(tid, result):
                if tid != task_id:
                    return
                try:
                    if not result:
                        self.load_sample_data()
                        return
                    # result: List[Dict[str, Any]] with 'date' and 'value'
                    dates = [x['date'] for x in result]
                    values = [x['value'] for x in result]
                    self.plot_performance(pd.DatetimeIndex(dates), values)
                except Exception as e:
                    logger.error(f"Error processing performance history: {e}")
                    self.load_sample_data()
            async_manager.task_finished.connect(on_finished)
        except Exception as e:
            logger.error(f"Błąd podczas ładowania danych wydajności: {e}")
            self.load_sample_data()
    
    def load_sample_data(self):
        """Ładuje przykładowe dane wydajności"""
        if not MATPLOTLIB_AVAILABLE:
            return
        try:
            dates = pd.date_range(start=datetime.now() - timedelta(days=30), end=datetime.now(), freq='D')
            np.random.seed(42)
            returns = np.random.normal(0.001, 0.02, len(dates))
            portfolio_value = [10000]
            for ret in returns[1:]:
                portfolio_value.append(portfolio_value[-1] * (1 + ret))
            self.plot_performance(dates, portfolio_value)
        except Exception as e:
            logger.error(f"Błąd podczas ładowania danych wydajności: {e}")
    
    def plot_performance(self, dates: pd.DatetimeIndex, values: List[float]):
        """Rysuje wykres wydajności"""
        try:
            self.figure.clear()
            ax = self.figure.add_subplot(111)
            ax.set_facecolor('#2b2b2b')
            self.figure.patch.set_facecolor('#2b2b2b')
            ax.plot(dates, values, color='#00ff88', linewidth=2, label='Wartość portfela')
            ax.axhline(y=values[0], color='#666', linestyle='--', alpha=0.7, label='Wartość początkowa')
            ax.set_title('Wydajność Portfela (30 dni)', color='white', fontsize=14, pad=20)
            ax.set_xlabel('Data', color='white')
            ax.set_ylabel('Wartość (USDT)', color='white')
            ax.tick_params(colors='white')
            ax.grid(True, alpha=0.3)
            ax.legend()
            ax.xaxis.set_major_formatter(mdates.DateFormatter('%m-%d'))
            ax.xaxis.set_major_locator(mdates.DayLocator(interval=5))
            total_return = (values[-1] - values[0]) / values[0] * 100
            ax.text(0.02, 0.98, f'Całkowity zwrot: {total_return:.2f}%', 
                    transform=ax.transAxes, color='white', fontsize=10,
                    verticalalignment='top', bbox=dict(boxstyle='round', facecolor='black', alpha=0.7))
            self.figure.tight_layout()
            self.canvas.draw()
        except Exception as e:
            logger.error(f"Błąd podczas rysowania wykresu wydajności: {e}")


class AllocationChart(QWidget):
    """Widget wykresu alokacji portfela (wykres kołowy)"""
    
    def __init__(self, parent=None, integrated_data_manager=None):
        super().__init__(parent)
        self.integrated_data_manager = integrated_data_manager
        self.refresh_timer = None
        self.setup_ui()
        if self.integrated_data_manager is None:
            self.load_sample_data()
        else:
            self.load_data()
            self.start_refresh_timer()
    
    def setup_ui(self):
        layout = QVBoxLayout(self)
        title = QLabel("Alokacja Portfela")
        title.setStyleSheet("font-size: 18px; font-weight: bold; color: white; margin-bottom: 10px;")
        layout.addWidget(title)
        if MATPLOTLIB_AVAILABLE:
            self.figure = Figure(figsize=(8, 8), facecolor='#2b2b2b')
            self.canvas = FigureCanvas(self.figure)
            layout.addWidget(self.canvas)
        else:
            placeholder = QLabel("Matplotlib nie jest dostępne - wykres niedostępny")
            placeholder.setAlignment(Qt.AlignmentFlag.AlignCenter)
            placeholder.setStyleSheet("font-size: 16px; color: #666; padding: 50px;")
            layout.addWidget(placeholder)
    
    def start_refresh_timer(self):
        try:
            if not PYQT_AVAILABLE or not MATPLOTLIB_AVAILABLE:
                return
            if self.refresh_timer is None:
                self.refresh_timer = QTimer(self)
                self.refresh_timer.timeout.connect(self.load_data)
            interval = get_app_setting('charts_refresh_interval', 60000)
            self.refresh_timer.start(interval)
            logger.info(f"Allocation chart auto-refresh started (interval: {interval} ms)")
        except Exception as e:
            logger.error(f"Błąd uruchamiania timera wykresu alokacji: {e}")
    
    def closeEvent(self, event):
        try:
            if self.refresh_timer and self.refresh_timer.isActive():
                self.refresh_timer.stop()
                logger.info("Allocation chart auto-refresh stopped")
        except Exception as e:
            logger.error(f"Błąd zatrzymywania timera wykresu alokacji: {e}")
        try:
            super().closeEvent(event)
        except Exception:
            pass
    
    def load_data(self):
        if not MATPLOTLIB_AVAILABLE:
            return
        try:
            if self.integrated_data_manager is None:
                self.load_sample_data()
                return
            from ui.async_helper import get_async_manager
            async_manager = get_async_manager()
            async def _fetch():
                try:
                    return await self.integrated_data_manager.get_portfolio_allocation()
                except Exception as e:
                    logger.error(f"Error fetching portfolio allocation: {e}")
                    return None
            task_id = async_manager.run_async(_fetch())
            def on_finished(tid, result):
                if tid != task_id:
                    return
                try:
                    if not result:
                        self.load_sample_data()
                        return
                    self.plot_allocation(result)
                except Exception as e:
                    logger.error(f"Error processing allocation data: {e}")
                    self.load_sample_data()
            async_manager.task_finished.connect(on_finished)
        except Exception as e:
            logger.error(f"Błąd podczas ładowania danych alokacji: {e}")
            self.load_sample_data()
    
    def load_sample_data(self):
        if not MATPLOTLIB_AVAILABLE:
            return
        try:
            allocations = {
                'BTC': 45.0,
                'ETH': 25.0,
                'ADA': 15.0,
                'DOT': 10.0,
                'USDT': 5.0
            }
            self.plot_allocation(allocations)
        except Exception as e:
            logger.error(f"Błąd podczas ładowania danych alokacji: {e}")
    
    def plot_allocation(self, allocations: Dict[str, float]):
        try:
            self.figure.clear()
            ax = self.figure.add_subplot(111)
            ax.set_facecolor('#2b2b2b')
            self.figure.patch.set_facecolor('#2b2b2b')
            labels = list(allocations.keys())
            sizes = list(allocations.values())
            colors = ['#ff6b6b', '#4ecdc4', '#45b7d1', '#96ceb4', '#feca57']
            wedges, texts, autotexts = ax.pie(sizes, labels=labels, colors=colors, autopct='%1.1f%%',
                                              startangle=90, textprops={'color': 'white'})
            for autotext in autotexts:
                autotext.set_color('white')
                autotext.set_fontweight('bold')
            ax.set_title('Alokacja Portfela', color='white', fontsize=14, pad=20)
            self.figure.tight_layout()
            self.canvas.draw()
        except Exception as e:
            logger.error(f"Błąd podczas rysowania wykresu alokacji: {e}")


def create_chart_widget(chart_type: str, **kwargs) -> QWidget:
    """Factory function do tworzenia wykresów"""
    if not PYQT_AVAILABLE or not MATPLOTLIB_AVAILABLE:
        placeholder = QLabel(f"Wymagane biblioteki niedostępne - {chart_type} wykres niedostępny")
        placeholder.setAlignment(Qt.AlignmentFlag.AlignCenter)
        placeholder.setStyleSheet("font-size: 16px; color: #666; padding: 50px;")
        return placeholder
    
    if chart_type == "candlestick":
        return CandlestickChart(kwargs.get('symbol', 'BTCUSDT'))
    elif chart_type == "performance":
        return PerformanceChart(kwargs.get('parent', None), kwargs.get('integrated_data_manager', None))
    elif chart_type == "allocation":
        return AllocationChart(kwargs.get('parent', None), kwargs.get('integrated_data_manager', None))
    else:
        raise ValueError(f"Nieznany typ wykresu: {chart_type}")
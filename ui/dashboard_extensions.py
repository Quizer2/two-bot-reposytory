
from __future__ import annotations
from typing import List
import random
import os, importlib.util, importlib.machinery

try:
    from PyQt6.QtWidgets import QWidget, QVBoxLayout, QLabel, QGroupBox
except Exception:
    QWidget = object
    def QVBoxLayout(*a, **k): return None
    def QLabel(*a, **k): return None
    def QGroupBox(*a, **k): return None

# Robust import of summarize_equity
def _load_summarize():
    try:
        from analytics.performance_metrics import summarize_equity as f
        return f
    except Exception:
        # Fallback: load by path
        base_dir = os.path.dirname(__file__)
        p = os.path.abspath(os.path.join(base_dir, "..", "analytics", "performance_metrics.py"))
        spec = importlib.util.spec_from_loader("analytics.performance_metrics", importlib.machinery.SourceFileLoader("analytics.performance_metrics", p))
        m = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(m)
        return m.summarize_equity

summarize_equity = _load_summarize()

from utils.logger import get_logger
logger = get_logger(__name__)

class RiskMetricsWidget(QWidget):
    def __init__(self, parent=None, equity_series: List[float] | None = None):
        super().__init__()
        self.setObjectName("RiskMetricsWidget")
        if equity_series is None:
            equity_series = [1000 + i*0.3 + random.uniform(-2,2) for i in range(120)]
        summary = summarize_equity(equity_series)
        try:
            layout = QVBoxLayout()
            box = QGroupBox("Risk Metrics")
            box_layout = QVBoxLayout()
            box.setLayout(box_layout)
            box_layout.addWidget(QLabel(f"Sharpe: {summary['sharpe']}"))
            box_layout.addWidget(QLabel(f"Sortino: {summary['sortino']}"))
            box_layout.addWidget(QLabel(f"Max Drawdown: {summary['max_drawdown']}"))
            box_layout.addWidget(QLabel(f"Final Equity: {summary['final_equity']}  (PnL: {summary['pnl']})"))
            layout.addWidget(box)
            self.setLayout(layout)
        except Exception as e:
            logger.info(f"RiskMetricsWidget init in stub mode: {e}")

class CorrelationWidget(QWidget):
    def __init__(self, parent=None, symbols=None):
        super().__init__()
        self.setObjectName("CorrelationWidget")
        try:
            layout = QVBoxLayout()
            gb = QGroupBox("Correlation (sample)")
            gb.setLayout(QVBoxLayout())
            gb.layout().addWidget(QLabel("BTC-ETH: 0.82"))
            gb.layout().addWidget(QLabel("BTC-LTC: 0.65"))
            gb.layout().addWidget(QLabel("ETH-LTC: 0.70"))
            layout.addWidget(gb)
            self.setLayout(layout)
        except Exception:
            pass

def install(main_window):
    try:
        if hasattr(main_window, "add_custom_panel"):
            main_window.add_custom_panel("Risk", RiskMetricsWidget(main_window))
            main_window.add_custom_panel("Correlation", CorrelationWidget(main_window))
        else:
            main_window._extra_risk_widget = RiskMetricsWidget(main_window)
            main_window._extra_corr_widget = CorrelationWidget(main_window)
        logger.info("Dashboard extensions installed.")
    except Exception as e:
        logger.info(f"Dashboard extensions install failed: {e}")

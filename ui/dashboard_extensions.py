
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

try:
    from analytics.ai_bot_data_provider import get_ai_bot_data_provider
except Exception:  # pragma: no cover - optional dependency
    get_ai_bot_data_provider = None  # type: ignore

try:
    from core.integrated_data_manager import get_integrated_data_manager
except Exception:  # pragma: no cover - fallback when IDM unavailable
    get_integrated_data_manager = None  # type: ignore

class RiskMetricsWidget(QWidget):
    def __init__(self, parent=None, equity_series: List[float] | None = None, provider=None, snapshot=None):
        super().__init__()
        self.setObjectName("RiskMetricsWidget")
        self.provider = provider
        if equity_series is None:
            equity_series = self._derive_equity_curve(snapshot)
        if not equity_series and provider is not None:
            equity_series = self._derive_equity_curve(provider.get_last_snapshot())
        if not equity_series:
            equity_series = [1000 + i * 0.3 + random.uniform(-2, 2) for i in range(120)]
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

    def _derive_equity_curve(self, snapshot):
        try:
            if not snapshot:
                return []
            learning = snapshot.get('learning') if isinstance(snapshot, dict) else {}
            if isinstance(learning, dict) and learning.get('equity_curve'):
                return list(learning['equity_curve'])
            symbols = snapshot.get('symbols') if isinstance(snapshot, dict) else []
            if symbols and self.provider is not None:
                history = self.provider.get_price_history(symbols[0], limit=240)
                return self._history_to_equity(history)
            if symbols:
                # Brak providera - spróbuj zainicjalizować teraz
                if get_ai_bot_data_provider and get_integrated_data_manager:
                    try:
                        provider = get_ai_bot_data_provider(get_integrated_data_manager())
                        history = provider.get_price_history(symbols[0], limit=240)
                        return self._history_to_equity(history)
                    except Exception:
                        pass
        except Exception as exc:
            logger.debug(f"Equity derivation failed: {exc}")
        return []

    def _history_to_equity(self, history):
        if not history:
            return []
        baseline = history[0][1] or 1.0
        return [round(1000.0 * (price / baseline), 2) for _, price in history]

class CorrelationWidget(QWidget):
    def __init__(self, parent=None, symbols=None, provider=None, snapshot=None):
        super().__init__()
        self.setObjectName("CorrelationWidget")
        try:
            layout = QVBoxLayout()
            gb = QGroupBox("Correlation (sample)")
            gb.setLayout(QVBoxLayout())
            correlations = []
            if snapshot and isinstance(snapshot, dict):
                correlations = snapshot.get('correlations') or []
            if not correlations and provider is not None:
                last = provider.get_last_snapshot()
                if last:
                    correlations = last.get('correlations') or []
            if correlations:
                for entry in correlations[:5]:
                    gb.layout().addWidget(
                        QLabel(
                            f"{entry.get('pair')}: {entry.get('correlation', 0.0):.2f} (n={entry.get('sample_size', 0)})"
                        )
                    )
            else:
                gb.layout().addWidget(QLabel("BTC-ETH: 0.82"))
                gb.layout().addWidget(QLabel("BTC-LTC: 0.65"))
                gb.layout().addWidget(QLabel("ETH-LTC: 0.70"))
            layout.addWidget(gb)
            self.setLayout(layout)
        except Exception:
            pass

def install(main_window):
    try:
        provider = None
        snapshot = None
        if get_ai_bot_data_provider and get_integrated_data_manager:
            try:
                idm = get_integrated_data_manager()
                provider = get_ai_bot_data_provider(idm)
                snapshot = provider.get_last_snapshot()
            except Exception as exc:
                logger.debug(f"AI provider unavailable during dashboard install: {exc}")

        if hasattr(main_window, "add_custom_panel"):
            main_window.add_custom_panel("Risk", RiskMetricsWidget(main_window, provider=provider, snapshot=snapshot))
            main_window.add_custom_panel("Correlation", CorrelationWidget(main_window, provider=provider, snapshot=snapshot))
        else:
            main_window._extra_risk_widget = RiskMetricsWidget(main_window, provider=provider, snapshot=snapshot)
            main_window._extra_corr_widget = CorrelationWidget(main_window, provider=provider, snapshot=snapshot)
        logger.info("Dashboard extensions installed.")
    except Exception as e:
        logger.info(f"Dashboard extensions install failed: {e}")

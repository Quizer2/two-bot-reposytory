from __future__ import annotations
from PyQt6.QtWidgets import QWidget, QVBoxLayout, QLabel, QSizePolicy
from PyQt6.QtCore import QTimer, Qt
from PyQt6.QtGui import QFont

from utils import runtime_metrics as rt

# Optional: Matplotlib embed for line chart
try:
    from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
    from matplotlib.figure import Figure
    _HAS_MPL_QT = True
except Exception:
    # Fallback dla środowisk headless/bez PyQt6-sip: użyj prostych atrap
    _HAS_MPL_QT = False
    class _AxesStub:
        def __init__(self):
            self.lines = []
            self._title = "Latency Sparkline (ms)"
        def clear(self):
            self.lines = []
        def set_title(self, t, color=None, fontsize=None):
            self._title = t
        def get_title(self):
            return self._title
        def grid(self, *args, **kwargs):
            pass
        def plot(self, xs, ys, linewidth=1.8):
            self.lines.append((xs, ys, linewidth))
    class Figure:
        def __init__(self, *args, **kwargs):
            self._ax = _AxesStub()
        def add_subplot(self, *args, **kwargs):
            return self._ax
    class FigureCanvas(QWidget):
        def __init__(self, fig=None, parent=None):
            super().__init__(parent)
            layout = QVBoxLayout(self)
            label = QLabel("(Sparkline offscreen)")
            if hasattr(label, "setAlignment"):
                label.setAlignment(Qt.AlignmentFlag.AlignCenter)
            layout.addWidget(label)
        def draw_idle(self):
            pass

class StatTile(QWidget):
    def __init__(self, title: str, getter, fmt: str = "{:,.0f}", parent=None):
        super().__init__(parent)
        self.getter = getter
        self._last_text = "--"
        layout = QVBoxLayout(self)
        layout.setContentsMargins(10,10,10,10)
        self.title = QLabel(title)
        if hasattr(self.title, "setAlignment"):
            self.title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        if hasattr(self.title, "setStyleSheet"):
            self.title.setStyleSheet("color:#C9B6FF; font-weight:600;")
        self.value = QLabel("--")
        if hasattr(self.value, "setAlignment"):
            self.value.setAlignment(Qt.AlignmentFlag.AlignCenter)
        f = QFont();
        if hasattr(f, "setPointSize"): f.setPointSize(18)
        if hasattr(f, "setBold"): f.setBold(True)
        if hasattr(self.value, "setFont"):
            self.value.setFont(f)
        layout.addWidget(self.title); layout.addWidget(self.value)
        self.fmt = fmt
        self.timer = QTimer(self); self.timer.setInterval(1500); self.timer.timeout.connect(self.refresh); self.timer.start()
        try:
            self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        except Exception:
            pass

    def refresh(self):
        try:
            v = self.getter()
            if v is None: v = 0
            if isinstance(v, float):
                txt = self.fmt.format(v)
            else:
                txt = str(v)
            self._last_text = txt
            if hasattr(self.value, "setText"):
                self.value.setText(txt)
        except Exception:
            self._last_text = "--"
            if hasattr(self.value, "setText"):
                self.value.setText("--")

class LineChart(QWidget):
    def __init__(self, title: str, series_getter, parent=None):
        super().__init__(parent)
        self.series_getter = series_getter
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0,0,0,0)
        self.fig = Figure(figsize=(4,2))
        self.canvas = FigureCanvas(self.fig)
        layout.addWidget(self.canvas)
        self.ax = self.fig.add_subplot(111)
        self.ax.set_title(title, color="#C9B6FF", fontsize=10)
        self.ax.grid(True, alpha=0.2)
        self.timer = QTimer(self); self.timer.setInterval(2000); self.timer.timeout.connect(self.refresh); self.timer.start()
        self.refresh()

    def refresh(self):
        try:
            data = self.series_getter() or []
            xs = [t for (t, v) in data]
            ys = [v for (t, v) in data]
            self.ax.clear()
            self.ax.set_title(self.ax.get_title(), color="#C9B6FF", fontsize=10)
            self.ax.grid(True, alpha=0.2)
            if xs and ys:
                # normalize time to last 5 minutes for visual smoothness
                t0 = xs[0]
                xsn = [(x - t0)/60.0 for x in xs]
                self.ax.plot(xsn, ys, linewidth=1.8)
            self.canvas.draw_idle()
        except Exception:
            pass

# Convenience getters for built-in tiles
def get_events_total():
    s = rt.snapshot()["events_total"]
    return sum(s.values())

def get_orders_total():
    s = rt.snapshot()["orders_total"]
    return sum(s.values())

def get_open_circuits():
    s = rt.snapshot()["circuit_open"]
    return sum(1 for v in s.values() if v)

def get_rate_drops():
    s = rt.snapshot()["rate_drops"]
    return sum(s.values())

def get_latency_p95():
    import numpy as np
    lat = rt.snapshot()["http_latency_ms"]
    if not lat: return 0.0
    return float(np.percentile(lat, 95))


class LatencySparkline(LineChart):
    def __init__(self, parent=None):
        super().__init__("Latency Sparkline (ms)", self._series, parent)
    def _series(self):
        snap = rt.snapshot()
        lat = snap.get("http_latency_ms", [])
        import time as _t
        t0 = _t.time() - 300
        xs = []
        ys = []
        step = max(1, len(lat)//100) if lat else 1
        for i, v in enumerate(lat[::step]):
            xs.append(t0 + i*3)
            ys.append(float(v))
        return list(zip(xs, ys))

def get_bots_list():
    return rt.snapshot().get("bots", [])

def get_strategies_list():
    return rt.snapshot().get("strategies", [])

def make_bot_equity_getter(bot_id: str):
    def _g():
        return rt.snapshot().get("equity_curve_per_bot", {}).get(bot_id, [])
    return _g

def make_strategy_equity_getter(strategy: str):
    def _g():
        return rt.snapshot().get("equity_curve_per_strategy", {}).get(strategy, [])
    return _g

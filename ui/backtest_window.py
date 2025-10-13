from pathlib import Path
from typing import List
from PyQt6.QtWidgets import QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QFileDialog, QSpinBox, QMessageBox, QFormLayout
from PyQt6.QtCore import Qt
from backtesting.backtester import load_ohlcv_csv, sma_cross_strategy, backtest

class BacktestWindow(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Backtester")
        self.resize(480, 280)
        self.csv_path: Path | None = None
        self._build_ui()

    def _build_ui(self):
        layout = QVBoxLayout(self)
        form = QFormLayout()
        self.short_spin = QSpinBox()
        self.short_spin.setRange(2, 500)
        self.short_spin.setValue(10)
        self.long_spin = QSpinBox()
        self.long_spin.setRange(2, 1000)
        self.long_spin.setValue(20)
        form.addRow("SMA short:", self.short_spin)
        form.addRow("SMA long:", self.long_spin)
        layout.addLayout(form)

        self.path_label = QLabel("Plik CSV: (nie wybrano)")
        self.path_label.setAlignment(Qt.AlignmentFlag.AlignLeft)
        layout.addWidget(self.path_label)

        btns = QHBoxLayout()
        choose = QPushButton("Wybierz CSV")
        choose.clicked.connect(self._choose_csv)
        run = QPushButton("Uruchom backtest")
        run.clicked.connect(self._run_backtest)
        btns.addWidget(choose)
        btns.addWidget(run)
        layout.addLayout(btns)

        self.result = QLabel("Wyniki pojawią się tutaj...")
        self.result.setAlignment(Qt.AlignmentFlag.AlignLeft)
        self.result.setWordWrap(True)
        layout.addWidget(self.result)

    def _choose_csv(self):
        path, _ = QFileDialog.getOpenFileName(self, "Wybierz plik OHLCV CSV", "", "CSV Files (*.csv)")
        if path:
            self.csv_path = Path(path)
            self.path_label.setText(f"Plik CSV: {self.csv_path.name}")

    def _run_backtest(self):
        if not self.csv_path or not self.csv_path.exists():
            QMessageBox.warning(self, "Brak pliku", "Wybierz poprawny plik CSV z danymi OHLCV.")
            return
        candles = load_ohlcv_csv(self.csv_path)
        sig = sma_cross_strategy(self.short_spin.value(), self.long_spin.value())
        res = backtest(candles, sig)
        m = res['metrics']
        text = (
            f"Transakcji: {m['num_trades']}\n"
            f"Total PnL: {m['total_pnl']:.2%}\n"
            f"Win rate: {m['win_rate']:.1%}\n"
            f"Max Drawdown: {m['max_drawdown']:.1%}\n"
            f"Sharpe: {m['sharpe']:.2f}"
        )
        self.result.setText(text)

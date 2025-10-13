from pathlib import Path
import json
from typing import Dict, Any
from PyQt6.QtWidgets import QDialog, QVBoxLayout, QLabel, QPushButton, QHBoxLayout, QFileDialog, QMessageBox
from PyQt6.QtCore import Qt

LOG_FILE = Path(__file__).resolve().parents[1] / "logs" / "events.jsonl"

class TelemetryWindow(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Telemetria botów")
        self.resize(520, 240)
        self._build_ui()

    def _build_ui(self):
        layout = QVBoxLayout(self)
        self.summary = QLabel("Brak danych. Wygeneruj zdarzenia lub zaimportuj log.")
        self.summary.setAlignment(Qt.AlignmentFlag.AlignLeft)
        self.summary.setWordWrap(True)
        layout.addWidget(self.summary)

        btns = QHBoxLayout()
        refresh = QPushButton("Odśwież z aktualnego logu")
        refresh.clicked.connect(self._refresh_from_log)
        import_btn = QPushButton("Zaimportuj inny plik .jsonl")
        import_btn.clicked.connect(self._import_log)
        btns.addWidget(refresh)
        btns.addWidget(import_btn)
        layout.addLayout(btns)

    def _parse_log(self, path: Path) -> Dict[str, Any]:
        stats = {"orders": 0, "fills": 0, "symbols": set(), "bots": set()}
        if not path.exists():
            return stats
        with path.open("r", encoding="utf-8") as f:
            for line in f:
                line=line.strip()
                if not line:
                    continue
                try:
                    rec = json.loads(line)
                except Exception:
                    continue
                ev = rec.get("event","")
                payload = rec.get("payload",{})
                if ev in ("ORDER_FILLED","OrderFilled"):
                    stats["fills"] += 1
                if "symbol" in payload:
                    stats["symbols"].add(payload["symbol"])
                if "bot_id" in payload:
                    stats["bots"].add(payload["bot_id"])
                if ev in ("ORDER_SUBMITTED","OrderSubmitted"):
                    stats["orders"] += 1
        stats["symbols"] = sorted(list(stats["symbols"]))
        stats["bots"] = sorted(list(stats["bots"]))
        return stats

    def _refresh_from_log(self):
        stats = self._parse_log(LOG_FILE)
        text = (
            f"Złożone zlecenia: {stats['orders']}\n"
            f"Zrealizowane zlecenia: {stats['fills']}\n"
            f"Unikalne symbole: {', '.join(stats['symbols']) or '-'}\n"
            f"Aktywne boty: {', '.join(stats['bots']) or '-'}"
        )
        self.summary.setText(text)

    def _import_log(self):
        path, _ = QFileDialog.getOpenFileName(self, "Wybierz plik .jsonl z logami", "", "JSON Lines (*.jsonl)")
        if not path:
            return
        stats = self._parse_log(Path(path))
        text = (
            f"Złożone zlecenia: {stats['orders']}\n"
            f"Zrealizowane zlecenia: {stats['fills']}\n"
            f"Unikalne symbole: {', '.join(stats['symbols']) or '-'}\n"
            f"Aktywne boty: {', '.join(stats['bots']) or '-'}"
        )
        self.summary.setText(text)

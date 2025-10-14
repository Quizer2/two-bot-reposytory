"""Utilities to capture lightweight UI structure snapshots for regression checks."""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict

import sys

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from ui.updated_bot_management_widget import BotCard

_SAMPLE_BOT = {
    "name": "Momentum Pro",
    "strategy": "Grid Trading",
    "symbol": "BTC/USDT",
    "status": "running",
    "pnl": 253.42,
    "trades_count": 128,
}


def _normalise_stylesheet(value: str) -> str:
    """Return compact stylesheet string for deterministic comparisons."""

    return "".join(line.strip() for line in (value or "").splitlines())


def capture_bot_card_snapshot(bot_data: Dict[str, Any] | None = None) -> Dict[str, Any]:
    """Instantiate :class:`BotCard` and summarise its key visual attributes."""

    payload = dict(_SAMPLE_BOT if bot_data is None else bot_data)
    card = BotCard("bot-demo", payload)

    def _collect_icon_buttons(layout) -> list[str]:
        texts: list[str] = []
        for entry in getattr(layout, "_items", []):
            kind = entry[0]
            if kind == "widget":
                widget = entry[1]
                if isinstance(widget, type(card.start_stop_btn)) and widget is not card.start_stop_btn:
                    texts.append(widget.text())
            elif kind == "layout":
                texts.extend(_collect_icon_buttons(entry[1]))
        return texts

    snapshot = {
        "object_name": card.objectName(),
        "style": _normalise_stylesheet(card.styleSheet()),
        "status_indicator_style": _normalise_stylesheet(card.status_indicator.styleSheet()),
        "labels": {
            "name": card.name_label.text(),
            "strategy": card.strategy_value.text(),
            "symbol": card.symbol_value.text(),
            "pnl": card.pnl_value.text(),
            "trades": card.trades_value.text(),
        },
        "button_texts": {
            "primary": card.start_stop_btn.text(),
            "icons": _collect_icon_buttons(card.layout()),
        },
    }
    return snapshot


def dump_snapshot(destination: Path) -> Dict[str, Any]:
    """Write the snapshot to *destination* and return the captured dictionary."""

    snapshot = capture_bot_card_snapshot()
    destination.write_text(json.dumps(snapshot, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    return snapshot


def main() -> None:  # pragma: no cover - exercised via CLI in CI artefacts
    import argparse

    parser = argparse.ArgumentParser(description="Generate BotCard UI snapshot")
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("analytics/ui_bot_card_snapshot.json"),
        help="Destination file for the snapshot",
    )
    args = parser.parse_args()
    dump_snapshot(args.output)


if __name__ == "__main__":  # pragma: no cover - CLI entry point
    main()

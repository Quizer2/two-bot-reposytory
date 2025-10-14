"""Synchronizacja limitów ryzyka pomiędzy plikami konfiguracyjnymi."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

DEFAULT_CONFIG = Path("config/app_config.json")
RISK_LIMITS = Path("config/risk_limits.json")


def load_json(path: Path) -> dict:
    if not path.exists():
        raise FileNotFoundError(f"Brak pliku: {path}")
    return json.loads(path.read_text(encoding="utf-8"))


def persist_json(path: Path, data: dict) -> None:
    path.write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def sync(config_path: Path) -> None:
    config = load_json(config_path)
    risk_limits = load_json(RISK_LIMITS)

    config.setdefault("risk", {})["limits"] = risk_limits
    persist_json(config_path, config)
    print(f"Zsynchronizowano limity ryzyka w {config_path}")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--config",
        default=str(DEFAULT_CONFIG),
        help="Ścieżka do pliku konfiguracyjnego bota",
    )
    args = parser.parse_args()
    sync(Path(args.config))


if __name__ == "__main__":
    main()

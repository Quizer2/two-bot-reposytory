"""Command-line utility to exercise CryptoBot trading workflows in sandbox modes."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys


def load_config(path: Path) -> dict:
    if not path.exists():
        raise FileNotFoundError(f"Config not found: {path}")
    return json.loads(path.read_text(encoding="utf-8"))


def run_bot(config: dict, dry_run: bool, force_error: bool) -> int:
    mode = config.get("mode", "paper")
    exchange = config.get("exchange", "unknown")
    print(f"Launching CryptoBot Desktop bot in mode={mode}, exchange={exchange}")
    if dry_run:
        print("Dry-run enabled: no orders will be sent.")
    if force_error:
        raise RuntimeError("Forced error for telemetry validation")
    print("Bot run completed successfully.")
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", default="config/app_config.json", help="Ścieżka do pliku konfiguracyjnego")
    parser.add_argument("--dry-run", action="store_true", help="Uruchom bez wysyłania zleceń")
    parser.add_argument("--force-error", action="store_true", help="Wymuś wyjątek dla testów alertingu")
    args = parser.parse_args(argv)

    config = load_config(Path(args.config))
    return run_bot(config, args.dry_run, args.force_error)


if __name__ == "__main__":
    sys.exit(main())

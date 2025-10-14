"""Generator raportu z testów E2E dla środowisk sandbox."""

from __future__ import annotations

import argparse
import json
from datetime import datetime
from pathlib import Path

DEFAULT_OUTPUT = Path("reports/e2e_testnet_report.json")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", required=True, help="Ścieżka do pliku konfiguracyjnego użytego w testach")
    parser.add_argument("--output", default=str(DEFAULT_OUTPUT), help="Ścieżka docelowa raportu JSON")
    parser.add_argument("--status", default="passed", choices=["passed", "failed"], help="Status testów")
    parser.add_argument("--notes", default="", help="Dodatkowe uwagi")
    args = parser.parse_args()

    payload = {
        "generated_at": datetime.utcnow().isoformat() + "Z",
        "config": args.config,
        "status": args.status,
        "notes": args.notes,
    }

    output_path = Path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(f"Zapisano raport: {output_path}")


if __name__ == "__main__":
    main()

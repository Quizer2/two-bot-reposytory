"""Unified release checklist runner.

The script executes the critical pre-release checks and produces a JSON
report that can be archived by CI/CD pipelines.  By default it performs:

* runtime dependency verification (`tools/check_runtime_dependencies.py`)
* unit/integration tests (`pytest -q`)
* optional smoke tests (user provided commands via CLI)

Usage::

    python ops/release_checklist.py --output build/release_report.json
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from datetime import datetime
from pathlib import Path
from typing import List

DEFAULT_SMOKE_TESTS: List[List[str]] = [
    [sys.executable, "tests/full_system_test.py"],
]


def run_command(command: List[str]) -> dict:
    start = datetime.utcnow().isoformat()
    try:
        completed = subprocess.run(command, capture_output=True, text=True, check=False)
        return {
            "command": command,
            "start": start,
            "end": datetime.utcnow().isoformat(),
            "returncode": completed.returncode,
            "stdout": completed.stdout,
            "stderr": completed.stderr,
            "success": completed.returncode == 0,
        }
    except FileNotFoundError as exc:
        return {
            "command": command,
            "start": start,
            "end": datetime.utcnow().isoformat(),
            "returncode": None,
            "stdout": "",
            "stderr": str(exc),
            "success": False,
        }


def build_report(args: argparse.Namespace) -> dict:
    report = {
        "generated_at": datetime.utcnow().isoformat(),
        "checks": [],
    }

    dependency_check = run_command([sys.executable, "tools/check_runtime_dependencies.py", "--json"])
    report["checks"].append({"name": "runtime_dependencies", **dependency_check})

    readiness_check = run_command([sys.executable, "tools/check_distribution_readiness.py", "--json"])
    report["checks"].append({"name": "distribution_readiness", **readiness_check})

    if not args.skip_tests:
        report["checks"].append({"name": "pytest", **run_command([sys.executable, "-m", "pytest", "-q"])})

    smoke_commands = [cmd.split() for cmd in args.smoke] if args.smoke else DEFAULT_SMOKE_TESTS
    for idx, command in enumerate(smoke_commands, start=1):
        report["checks"].append({"name": f"smoke_{idx}", **run_command(command)})

    return report


def parse_args(argv: List[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run the release readiness checklist")
    parser.add_argument("--output", type=Path, help="Optional path to JSON report")
    parser.add_argument(
        "--skip-tests",
        action="store_true",
        help="Skip running pytest (useful when tests already executed in the pipeline)",
    )
    parser.add_argument(
        "--smoke",
        action="append",
        help="Additional smoke test command (can be provided multiple times)",
    )
    return parser.parse_args(argv)


def main(argv: List[str] | None = None) -> int:
    args = parse_args(argv or sys.argv[1:])
    report = build_report(args)

    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(json.dumps(report, indent=2), encoding="utf-8")
    else:
        print(json.dumps(report, indent=2))

    success = all(item.get("success") for item in report["checks"] if item["name"] != "runtime_dependencies")
    return 0 if success else 1


if __name__ == "__main__":
    raise SystemExit(main())

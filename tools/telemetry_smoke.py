"""Smoke tests for telemetry integrations.

This script intentionally avoids external network access. Instead it validates
that configuration files exist and simulates telemetry emission so operators can
verify alerting pipelines end-to-end.
"""

from __future__ import annotations

import argparse
import json
import pathlib
import sys
import time

CONFIG_DIR = pathlib.Path("config")
RUNTIME_OVERRIDES = CONFIG_DIR / "runtime_overrides.json"


def _ensure_runtime_overrides() -> dict:
    if not RUNTIME_OVERRIDES.exists():
        raise SystemExit(
            "runtime_overrides.json not found. Run tools/check_runtime_dependencies.py "
            "--sync-sentry first."
        )
    with RUNTIME_OVERRIDES.open("r", encoding="utf-8") as handle:
        data = json.load(handle)
    if "sentry" not in data:
        raise SystemExit("Sentry configuration missing from runtime overrides.")
    return data


def _simulate_metric_push(metric: str) -> None:
    timestamp = int(time.time())
    line = f"{metric}{{service=\"cryptobot_desktop\"}} {timestamp}"
    monitoring_dir = pathlib.Path("ops") / "monitoring"
    monitoring_dir.mkdir(parents=True, exist_ok=True)
    metrics_log = monitoring_dir / "telemetry_smoke.prom"
    with metrics_log.open("a", encoding="utf-8") as handle:
        handle.write(line + "\n")
    print(f"Wrote synthetic metric sample to {metrics_log}")


def _trigger_exception() -> None:
    try:
        raise RuntimeError("Sentry smoke test exception")
    except RuntimeError as exc:
        print(f"Captured exception: {exc}")
        raise


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Telemetry smoke checks")
    parser.add_argument(
        "--raise-exception",
        action="store_true",
        help="Raise a RuntimeError to verify exception tracking",
    )
    parser.add_argument(
        "--alert-demo",
        action="store_true",
        help="Emit synthetic metrics for alerting pipeline tests",
    )
    args = parser.parse_args(argv)

    overrides = _ensure_runtime_overrides()
    print("Loaded runtime overrides:", overrides)

    if args.alert_demo:
        _simulate_metric_push("cryptobot_orders_failed_total")

    if args.raise_exception:
        _trigger_exception()

    return 0


if __name__ == "__main__":
    sys.exit(main())

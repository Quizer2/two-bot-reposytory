"""Wielofunkcyjny punkt wejścia aplikacji CryptoBotDesktop.

Pozwala wystartować interfejs graficzny (`run`) lub uruchomić inspekcję
środowiska (`check-deps`) bez konieczności zapamiętywania odrębnych skryptów.
"""

from __future__ import annotations

import argparse
from typing import Iterable, List


def _run_gui() -> int:
    """Odroczony import właściwej aplikacji, aby nie ładować PyQt6 przy testach."""

    from app.main import main as run_app  # lokalny import, aby uniknąć kosztów startu

    return run_app()


def _run_dependency_check(args: argparse.Namespace) -> int:
    """Deleguje do skryptu checkerowego, zachowując pełną kompatybilność flag."""

    from tools import check_runtime_dependencies as checker

    forwarded: List[str] = []
    if getattr(args, "sync_sentry", False):
        forwarded.append("--sync-sentry")
    if getattr(args, "env_file", None):
        forwarded.extend(["--env-file", args.env_file])
    if getattr(args, "json", False):
        forwarded.append("--json")
    if getattr(args, "write_report", False):
        forwarded.append("--write-report")
    report_path = getattr(args, "report_path", None)
    if report_path:
        forwarded.extend(["--report-path", report_path])

    return checker.main(forwarded)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    subparsers = parser.add_subparsers(dest="command")
    parser.set_defaults(command="run")

    subparsers.add_parser("run", help="Uruchom aplikację wraz z interfejsem graficznym")

    check_parser = subparsers.add_parser(
        "check-deps", help="Uruchom checker zależności runtime i generuj raport"
    )
    check_parser.add_argument(
        "--sync-sentry",
        action="store_true",
        help="Zsynchronizuj konfigurację Sentry z pliku production.env",
    )
    check_parser.add_argument(
        "--env-file",
        help="Ścieżka do niestandardowego pliku .env używanego przy synchronizacji Sentry",
    )
    check_parser.add_argument(
        "--json",
        action="store_true",
        help="Utrzymaj zgodność z pipeline'ami oczekującymi flagi --json",
    )
    check_parser.add_argument(
        "--write-report",
        action="store_true",
        help="Zapisz wynik kontroli do pliku runtime_dependency_report.json",
    )
    check_parser.add_argument(
        "--report-path",
        help="Ścieżka do raportu (domyślnie runtime_dependency_report.json)",
    )

    return parser


def main(argv: Iterable[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(list(argv) if argv is not None else None)

    if args.command == "check-deps":
        return _run_dependency_check(args)
    if args.command == "run":
        return _run_gui()

    parser.error(f"Nieznana komenda: {args.command}")
    return 2


if __name__ == "__main__":
    raise SystemExit(main())

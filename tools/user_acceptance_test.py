#!/usr/bin/env python3
"""High-level user acceptance runner for CryptoBotDesktop.

This script orchestrates the same steps that an end user should perform
before the first launch: dependency validation, smoke tests, bytecode
compilation and a headless GUI startup check.  It aggregates the results
into a concise summary that can be consumed in CI or manually.
"""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, Iterable, List, Optional

REPO_ROOT = Path(__file__).resolve().parents[1]
PYTHON = sys.executable


@dataclass
class StepResult:
    name: str
    command: List[str]
    returncode: int
    stdout: str
    stderr: str
    extra: Optional[Dict[str, object]] = None

    @property
    def succeeded(self) -> bool:
        return self.returncode == 0


def run_command(cmd: Iterable[str], env: Optional[Dict[str, str]] = None) -> StepResult:
    command = list(cmd)
    proc = subprocess.run(
        command,
        cwd=REPO_ROOT,
        env=env,
        capture_output=True,
        text=True,
        check=False,
    )
    return StepResult(
        name=" ".join(command),
        command=command,
        returncode=proc.returncode,
        stdout=proc.stdout.strip(),
        stderr=proc.stderr.strip(),
    )


def run_dependency_check() -> StepResult:
    step = run_command([PYTHON, "tools/check_runtime_dependencies.py", "--json"])
    extra: Dict[str, object] = {}
    if step.succeeded:
        try:
            payload = json.loads(step.stdout or "{}")
        except json.JSONDecodeError as exc:  # pragma: no cover - defensive path
            step.returncode = 1
            extra["error"] = f"Niepoprawny JSON z checkera: {exc}"
        else:
            failures = {}
            for group in ("modules", "system_libraries"):
                for name, meta in payload.get(group, {}).items():
                    status = meta.get("status")
                    if status not in {"ok", "bundled", "not_required"}:
                        failures[name] = status
            if failures:
                step.returncode = 1
                extra["failures"] = failures
            extra["report"] = payload
    step.extra = extra or None
    return step


def run_pytest(pytest_args: Iterable[str]) -> StepResult:
    return run_command([PYTHON, "-m", "pytest", *pytest_args])


def run_compileall() -> StepResult:
    paths = ["app", "core", "trading", "ui", "utils"]
    return run_command([PYTHON, "-m", "compileall", *paths])


def run_headless_gui() -> StepResult:
    env = os.environ.copy()
    env.setdefault("QT_QPA_PLATFORM", "offscreen")
    return run_command([PYTHON, "main.py", "run"], env=env)


def format_summary(results: List[StepResult]) -> str:
    lines = ["Podsumowanie testów użytkownika:"]
    for result in results:
        status = "OK" if result.succeeded else "FAIL"
        lines.append(f"- [{status}] {' '.join(result.command)}")
        if result.extra:
            lines.append(f"    -> {json.dumps(result.extra, ensure_ascii=False, indent=2)}")
        if result.stderr and not result.succeeded:
            lines.append(f"    stderr: {result.stderr}")
    return "\n".join(lines)


def parse_args(argv: Optional[Iterable[str]] = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Uruchamia sekwencję kroków przygotowujących środowisko i"
            " weryfikujących aplikację z perspektywy użytkownika końcowego."
        )
    )
    parser.add_argument(
        "--pytest-args",
        nargs=argparse.REMAINDER,
        help=(
            "Dodatkowe argumenty przekazywane do pytest (domyślnie `-q`)."
            " Użyj `--` aby oddzielić je od opcji skryptu."
        ),
    )
    parser.add_argument(
        "--json-output",
        type=Path,
        help="Opcjonalna ścieżka do zapisania szczegółowego raportu w formacie JSON.",
    )
    return parser.parse_args(list(argv) if argv is not None else None)


def main(argv: Optional[Iterable[str]] = None) -> int:
    args = parse_args(argv)
    results: List[StepResult] = []

    dep_step = run_dependency_check()
    results.append(dep_step)

    pytest_args = args.pytest_args if args.pytest_args else ["-q"]
    pytest_step = run_pytest(pytest_args)
    results.append(pytest_step)

    compile_step = run_compileall()
    results.append(compile_step)

    gui_step = run_headless_gui()
    results.append(gui_step)

    summary = format_summary(results)
    print(summary)

    if args.json_output:
        payload = {
            "results": [
                {
                    "name": res.name,
                    "command": res.command,
                    "returncode": res.returncode,
                    "stdout": res.stdout,
                    "stderr": res.stderr,
                    "extra": res.extra,
                }
                for res in results
            ],
        }
        args.json_output.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")

    exit_code = 0 if all(step.succeeded for step in results) else 1
    return exit_code


if __name__ == "__main__":
    sys.exit(main())

"""Sprawdzenie gotowości aplikacji do dystrybucji."""

from __future__ import annotations

import argparse
import json
from dataclasses import dataclass
import re
import subprocess
from pathlib import Path
from typing import Any, Dict, List

CONFIG_DIR = Path("config")
APP_CONFIG_FILE = CONFIG_DIR / "app_config.json"
CREDENTIALS_FILE = CONFIG_DIR / "exchange_credentials.json"
RISK_LIMITS_FILE = CONFIG_DIR / "risk_limits.json"


@dataclass
class CheckResult:
    """Wynik pojedynczego sprawdzenia."""

    name: str
    status: str
    message: str
    details: Dict[str, Any]

    def to_dict(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "status": self.status,
            "message": self.message,
            "details": self.details,
        }


MASKED_VALUES = {"***", "MASKED", "HIDDEN", "REDACTED"}


def _load_json(path: Path, default: Dict[str, Any] | None = None) -> Dict[str, Any]:
    if not path.exists():
        return default.copy() if isinstance(default, dict) else {}
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise ValueError(f"Niepoprawny JSON w pliku {path}: {exc}") from exc


def _has_secret(value: Any) -> bool:
    if value is None:
        return False
    text = str(value).strip()
    if not text:
        return False
    return text not in MASKED_VALUES


def _check_trading_mode(app_config: Dict[str, Any], credentials: Dict[str, Any]) -> CheckResult:
    trading_cfg = app_config.get("trading", {}) if isinstance(app_config, dict) else {}
    default_mode = str(trading_cfg.get("default_mode", "paper")).lower()
    paper_flag = bool(trading_cfg.get("paper_trading", default_mode != "live"))

    exchange_results: List[Dict[str, Any]] = []
    enabled_missing: Dict[str, List[str]] = {}
    live_ready = False

    for exchange, cfg in sorted(credentials.items()):
        if not isinstance(cfg, dict):
            exchange_results.append(
                {
                    "exchange": exchange,
                    "status": "error",
                    "reason": "Niepoprawny format konfiguracji",
                }
            )
            enabled_missing[exchange] = ["config"]
            continue

        enabled = bool(cfg.get("enabled"))
        sandbox = bool(cfg.get("sandbox", True))
        required_fields = ["api_key", "secret"]
        if exchange in {"coinbase", "kucoin"}:
            required_fields.append("password")
        missing = [field for field in required_fields if not _has_secret(cfg.get(field))]

        status = "disabled"
        if enabled:
            if missing:
                status = "error"
                enabled_missing[exchange] = missing
            else:
                status = "ready"
                if not sandbox:
                    live_ready = True
        exchange_results.append(
            {
                "exchange": exchange,
                "status": status,
                "enabled": enabled,
                "sandbox": sandbox,
                "missing": missing,
            }
        )

    if enabled_missing:
        message = (
            "Co najmniej jedna włączona giełda ma nieuzupełnione pola: "
            + ", ".join(f"{ex}: {', '.join(fields)}" for ex, fields in enabled_missing.items())
        )
        return CheckResult(
            name="trading_mode",
            status="error",
            message=message,
            details={"exchanges": exchange_results, "default_mode": default_mode, "paper": paper_flag},
        )

    if default_mode == "live" or not paper_flag:
        if live_ready:
            message = "Tryb live aktywny i dostępna jest przynajmniej jedna w pełni skonfigurowana giełda."
            status = "ok"
        else:
            message = (
                "Tryb live jest aktywny, ale brak w pełni skonfigurowanych giełd (sandbox=false). "
                "Uzupełnij klucze API oraz wyłącz sandbox."
            )
            status = "error"
    else:
        status = "ok"
        if live_ready:
            message = (
                "Tryb domyślny to paper, ale dostępna jest co najmniej jedna giełda live. "
                "Można przełączyć tryb w ustawieniach."
            )
        else:
            message = (
                "Aplikacja uruchomi się w trybie paper trading do czasu uzupełnienia kluczy API i wyłączenia sandbox."
            )

    return CheckResult(
        name="trading_mode",
        status=status,
        message=message,
        details={"exchanges": exchange_results, "default_mode": default_mode, "paper": paper_flag},
    )


def _validate_limits(profile: Dict[str, Any]) -> Dict[str, str]:
    errors: Dict[str, str] = {}
    required_fields = {
        "daily_loss_limit": (float, 0.0, None),
        "daily_profit_limit": (float, 0.0, None),
        "max_drawdown_limit": (float, 0.0, 100.0),
        "position_size_limit": (float, 0.0, None),
        "max_open_positions": (int, 0, None),
        "max_correlation": (float, 0.0, 1.0),
        "volatility_threshold": (float, 0.0, None),
        "var_limit": (float, 0.0, None),
    }
    for key, (expected_type, min_value, max_value) in required_fields.items():
        value = profile.get(key)
        if value is None:
            errors[key] = "brak wartości"
            continue
        try:
            numeric_value = float(value) if expected_type is float else int(value)
        except (TypeError, ValueError):
            errors[key] = "nieprawidłowy typ"
            continue
        if min_value is not None and numeric_value <= min_value:
            errors[key] = "wartość musi być większa od zera"
        if max_value is not None and numeric_value > max_value:
            errors[key] = f"wartość musi być ≤ {max_value}"
    return errors


def _check_risk_limits(risk_limits: Dict[str, Any]) -> CheckResult:
    if not risk_limits:
        return CheckResult(
            name="risk_limits",
            status="error",
            message="Brak pliku z limitami ryzyka lub jest pusty.",
            details={},
        )

    profiles = {"default": risk_limits.get("default", {})}
    bots_section = risk_limits.get("bots")
    if isinstance(bots_section, dict):
        profiles.update({f"bot_{bot_id}": cfg for bot_id, cfg in bots_section.items() if isinstance(cfg, dict)})

    invalid: Dict[str, Dict[str, str]] = {}
    for name, profile in profiles.items():
        issues = _validate_limits(profile)
        if issues:
            invalid[name] = issues

    if invalid:
        message = "Wykryto niepoprawne wartości limitów ryzyka – uzupełnij wskazane pola."
        return CheckResult(
            name="risk_limits",
            status="error",
            message=message,
            details={"invalid": invalid},
        )

    return CheckResult(
        name="risk_limits",
        status="ok",
        message="Limity ryzyka wyglądają poprawnie.",
        details={"profiles": list(profiles.keys())},
    )


def _list_tracked_files() -> List[Path]:
    try:
        completed = subprocess.run(
            ["git", "ls-files"],
            capture_output=True,
            text=True,
            check=True,
        )
    except (FileNotFoundError, subprocess.CalledProcessError):
        return []
    return [Path(line) for line in completed.stdout.splitlines() if line.strip()]


_CONFLICT_PREFIX = "<" * 7
_CONFLICT_SEPARATOR = "=" * 7
_CONFLICT_SUFFIX = ">" * 7

CONFLICT_REGEX = re.compile(
    rf"^({re.escape(_CONFLICT_PREFIX)}(?: .+)?|{re.escape(_CONFLICT_SEPARATOR)}|{re.escape(_CONFLICT_SUFFIX)}(?: .+)?)$",
    re.MULTILINE,
)


def _check_conflict_markers(tracked_files: List[Path] | None = None) -> CheckResult:
    tracked = tracked_files if tracked_files is not None else _list_tracked_files()
    conflicted: List[str] = []
    for path in tracked:
        if not path.is_file():
            continue
        try:
            content = path.read_text(encoding="utf-8", errors="ignore")
        except OSError:
            continue
        if CONFLICT_REGEX.search(content):
            conflicted.append(str(path))

    if conflicted:
        return CheckResult(
            name="conflict_markers",
            status="error",
            message="Wykryto znaczniki konfliktów Gita – usuń je przed wydaniem.",
            details={"files": conflicted},
        )

    return CheckResult(
        name="conflict_markers",
        status="ok",
        message="Brak znaczników konfliktów w śledzonych plikach.",
        details={},
    )


def run_checks() -> List[CheckResult]:
    app_config = _load_json(APP_CONFIG_FILE, default={})
    credentials = _load_json(CREDENTIALS_FILE, default={})
    risk_limits = _load_json(RISK_LIMITS_FILE, default={})

    return [
        _check_conflict_markers(),
        _check_trading_mode(app_config, credentials),
        _check_risk_limits(risk_limits),
    ]


def build_report() -> Dict[str, Any]:
    checks = run_checks()
    return {
        "checks": [check.to_dict() for check in checks],
        "has_errors": any(check.status == "error" for check in checks),
    }


def format_human(report: Dict[str, Any]) -> str:
    lines = []
    for item in report["checks"]:
        lines.append(f"- {item['name']}: {item['status'].upper()} – {item['message']}")
    if report["has_errors"]:
        lines.append("Wykryto błędy – popraw konfigurację przed wydaniem.")
    else:
        lines.append("Brak krytycznych błędów konfiguracyjnych.")
    return "\n".join(lines)


def parse_args(argv: List[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Sprawdź gotowość dystrybucyjną aplikacji")
    parser.add_argument("--json", action="store_true", help="Zwróć wynik w formacie JSON")
    return parser.parse_args(argv)


def main(argv: List[str] | None = None) -> int:
    args = parse_args(argv)
    report = build_report()

    if args.json:
        print(json.dumps(report, indent=2, ensure_ascii=False))
    else:
        print(format_human(report))

    return 1 if report["has_errors"] else 0


if __name__ == "__main__":
    raise SystemExit(main())

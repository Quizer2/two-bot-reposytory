#!/usr/bin/env python3
"""Szybki checker zależności runtime wymaganych przed dystrybucją."""
from __future__ import annotations

import importlib
import json
import platform
from ctypes.util import find_library
from pathlib import Path
from typing import Dict

RUNTIME_MODULES = {
    "aiosqlite": "pip install aiosqlite",
    "websockets": "pip install websockets",
    "PyQt6": "pip install PyQt6",
}

SYSTEM_LIBRARIES = {
    "libGL.so.1": "sudo apt-get install -y libgl1",
    "libOpenGL.so.0": "sudo apt-get install -y libopengl0",
}


def check_modules() -> Dict[str, Dict[str, str]]:
    results: Dict[str, Dict[str, str]] = {}
    for module, install_hint in RUNTIME_MODULES.items():
        try:
            importlib.import_module(module)
            results[module] = {"status": "ok"}
        except Exception as exc:  # pragma: no cover - zależy od środowiska
            results[module] = {
                "status": "missing",
                "error": str(exc),
                "install": install_hint,
            }
    return results


def check_libraries() -> Dict[str, Dict[str, str]]:
    results: Dict[str, Dict[str, str]] = {}
    for lib, install_hint in SYSTEM_LIBRARIES.items():
        found = find_library(lib.replace(".so", "")) or find_library(lib)
        if found:
            results[lib] = {"status": "ok", "resolved": found}
        else:  # pragma: no cover - zależy od środowiska CI
            results[lib] = {
                "status": "missing",
                "install": install_hint,
            }
    return results


def main() -> None:
    payload = {
        "platform": platform.platform(),
        "python": platform.python_version(),
        "modules": check_modules(),
        "system_libraries": check_libraries(),
        "notes": (
            "Uruchom ten skrypt na maszynie docelowej. Jeśli zależności są brakujące,"
            " wykonaj sugerowane komendy instalacyjne przed wydaniem."
        ),
    }
    output = json.dumps(payload, indent=2, ensure_ascii=False)
    print(output)
    Path("runtime_dependency_report.json").write_text(output + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()

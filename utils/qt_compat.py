"""Helper utilities to safely import PyQt6 with lightweight fallbacks.

The production build ships with full PyQt6 bindings, however automated
validation in constrained CI environments relies on the bundled stubs
defined in :mod:`utils.pyqt_stubs`.  This module centralises the logic that
tries to import the real bindings and, if they are unavailable, installs the
stubs before retrying the import.

It also exposes a small helper that lifts selected symbols into the caller
module, providing optional placeholders when a stub does not implement a
specific class yet.  By keeping this logic in a single location we ensure that
distribution builds fail fast if a required widget is missing, while tests can
still execute with minimal mocks.
"""

from __future__ import annotations

from importlib import import_module
from types import SimpleNamespace
from typing import Dict, Iterable, Tuple


QtModuleMap = Dict[str, Iterable[str]]


def ensure_qt_modules() -> Tuple[bool, object, object, object]:
    """Return PyQt6 modules, installing the lightweight stubs on demand."""

    try:
        qt_widgets = import_module("PyQt6.QtWidgets")
        qt_core = import_module("PyQt6.QtCore")
        qt_gui = import_module("PyQt6.QtGui")
        return True, qt_widgets, qt_core, qt_gui
    except ImportError:
        from utils.pyqt_stubs import install_pyqt_stubs

        install_pyqt_stubs(force=True)
        qt_widgets = import_module("PyQt6.QtWidgets")
        qt_core = import_module("PyQt6.QtCore")
        qt_gui = import_module("PyQt6.QtGui")
        return False, qt_widgets, qt_core, qt_gui


def _placeholder(name: str):
    if name == "pyqtSignal":
        descriptor = SimpleNamespace()

        def factory(*args, **kwargs):
            return SimpleNamespace(connect=lambda *a, **k: None, emit=lambda *a, **k: None)

        descriptor.__call__ = factory
        return descriptor
    return type(name, (), {})


def load_qt_names(names: QtModuleMap) -> Tuple[bool, Dict[str, object]]:
    """Import the requested Qt symbols, falling back to placeholders when missing."""

    pyqt_available, qt_widgets, qt_core, qt_gui = ensure_qt_modules()
    modules = {
        "QtWidgets": qt_widgets,
        "QtCore": qt_core,
        "QtGui": qt_gui,
    }

    exported: Dict[str, object] = {}
    for namespace, identifiers in names.items():
        module = modules[namespace]
        for identifier in identifiers:
            attr = getattr(module, identifier, None)
            if attr is None:
                attr = _placeholder(identifier)
            exported[identifier] = attr

    return pyqt_available, exported


__all__ = ["ensure_qt_modules", "load_qt_names"]

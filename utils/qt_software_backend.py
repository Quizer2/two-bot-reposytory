"""Helpers for configuring Qt to use the software rendering backend."""
from __future__ import annotations

import os
import threading
from typing import Final

from utils.qt_compat import load_qt_names

_QT_IMPORTS = {"QtCore": ["Qt"], "QtWidgets": ["QApplication"]}

_PYQT_AVAILABLE, _qt_objects = load_qt_names(_QT_IMPORTS)

Qt = _qt_objects["Qt"]
QApplication = _qt_objects["QApplication"]

_SOFTWARE_ENV: Final[dict[str, str]] = {
    "QT_OPENGL": "software",
    "QT_QUICK_BACKEND": "software",
    "QT_XCB_FORCE_SOFTWARE_OPENGL": "1",
}

# Ensure we only configure once even if called from different modules
_config_lock = threading.Lock()
_configured = False


def enable_software_rendering() -> None:
    """Force Qt to use the software renderer.

    This avoids the requirement for system wide OpenGL libraries (libGL.so.1 /
    libOpenGL.so.0) by instructing Qt to rely on its built-in software backend.
    The function is idempotent and safe to call multiple times.
    """

    global _configured
    if _configured:
        return

    with _config_lock:
        if _configured:
            return

        for key, value in _SOFTWARE_ENV.items():
            os.environ.setdefault(key, value)

        # The attribute must be set before the QApplication instance is created.
        if hasattr(QApplication, "setAttribute") and hasattr(Qt, "ApplicationAttribute"):
            QApplication.setAttribute(
                Qt.ApplicationAttribute.AA_UseSoftwareOpenGL, True
            )
            QApplication.setAttribute(
                Qt.ApplicationAttribute.AA_ShareOpenGLContexts, True
            )

        _configured = True

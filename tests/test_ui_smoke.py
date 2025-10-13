import os
os.environ['QT_QPA_PLATFORM'] = 'offscreen'

# Fallback: if PyQt6 import fails, inject stubs via tests/repro_ui_import
try:
    from PyQt6.QtWidgets import QApplication
except Exception:
    import tests.repro_ui_import  # registers PyQt6 stubs in sys.modules
    from PyQt6.QtWidgets import QApplication

from importlib import import_module

def test_mainwindow_smoke():
    app = QApplication.instance() or QApplication([])
    umw = import_module('ui.updated_main_window')
    # find UpdatedMainWindow class
    cls = None
    for k, v in umw.__dict__.items():
        try:
            from PyQt6.QtWidgets import QMainWindow
            if isinstance(v, type) and issubclass(v, QMainWindow) and 'UpdatedMainWindow' in v.__name__:
                cls = v
        except Exception:
            pass
    assert cls is not None, 'UpdatedMainWindow not found'
    w = cls()
    # exercise a few methods
    w.toggle_theme()
    w.toggle_theme()
    w.set_status(api=True, ws=True, db=True)
    # just make sure it doesn't crash
    assert True

import sys, types, traceback
from types import SimpleNamespace

# Ensure project root in path
sys.path.insert(0, r"F:\new bot 1")

# Centralized stubs provided by tests/conftest.py

# Try import and instantiate
try:
    import importlib
    umw = importlib.import_module("ui.updated_main_window")
    from PyQt6.QtWidgets import QMainWindow as QM
    target = getattr(umw, "UpdatedMainWindow", None)
    if target is None:
        # fallback: first class that is subclass of QMainWindow
        import inspect
        for name, obj in vars(umw).items():
            try:
                if inspect.isclass(obj) and issubclass(obj, QM):
                    target=obj; break
            except Exception:
                pass
    print("Target:", getattr(target, "__name__", None))
    win = target()
    print("Instantiated:", type(win).__name__)
except Exception as e:
    print("ERROR:", e)
    traceback.print_exc()
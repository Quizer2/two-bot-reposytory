# Centralized PyQt6 stubs for tests
import sys, types
import asyncio
import pytest
from types import SimpleNamespace

# Do not override real PyQt6 if present
if "PyQt6" not in sys.modules:
    mod = types.ModuleType("PyQt6")
    qtcore = types.ModuleType("PyQt6.QtCore")
    qtwidgets = types.ModuleType("PyQt6.QtWidgets")
    qtgui = types.ModuleType("PyQt6.QtGui")

    # Core base classes
    class QObject:
        def __init__(self, parent=None):
            self._parent = parent
    class QWidget(QObject):
        def __init__(self, parent=None):
            super().__init__(parent)
        # Basic QWidget API used by app
        def setObjectName(self, name): self._object_name = name
        def setMinimumSize(self, w, h): self._min_size = (w, h)
        def setMaximumSize(self, w, h): self._max_size = (w, h)
        def setSizePolicy(self, h, v): self._size_policy = (h, v)
        def setStyleSheet(self, style): self._style = style
        def resize(self, w, h): self._size = (w, h)
        def move(self, x, y): self._pos = (x, y)
        def screen(self): return SimpleNamespace(availableGeometry=lambda: QRect(0,0,1920,1080))
    class QMainWindow(QWidget):
        def __init__(self, parent=None):
            super().__init__(parent)
        # Basic QMainWindow API used by app
        def setWindowTitle(self, title): self._title = title
        def setCentralWidget(self, widget): self._central = widget
        def statusBar(self):
            if not hasattr(self, "_status_bar"):
                self._status_bar = QStatusBar()
            return self._status_bar
        def menuBar(self):
            if not hasattr(self, "_menu_bar"):
                self._menu_bar = QMenuBar()
            return self._menu_bar
        def setStatusBar(self, bar): self._status_bar = bar
        def setMenuBar(self, bar): self._menu_bar = bar

    class QApplication:
        _inst = None
        def __init__(self, args=None):
            type(self)._inst = self
        def exec(self): return 0
        @staticmethod
        def instance():
            return QApplication._inst

    # Threading and timers
    class QThread(QObject):
        def __init__(self, parent=None):
            super().__init__(parent)
        def start(self): pass
        def wait(self): pass
        def quit(self): pass
        def deleteLater(self): pass
    class QTimer(QObject):
        def __init__(self, parent=None):
            super().__init__(parent)
            self.interval = 0
            # emulate Qt signal attribute like PyQt6
            self.timeout = SimpleNamespace(connect=lambda f: None)
        def setInterval(self, i): self.interval = i
        def start(self): pass

    # Signals/slots
    def pyqtSignal(*args, **kwargs):
        return SimpleNamespace(connect=lambda *a, **kw: None, emit=lambda *a, **kw: None)
    def pyqtSlot(*decorator_args, **decorator_kwargs):
        def decorator(fn): return fn
        return decorator

    # Common widgets
    class QTabBar(QObject):
        def __init__(self):
            self._visible = True
            self._min_height = 0
        def setVisible(self, v): self._visible = bool(v)
        def setMinimumHeight(self, h): self._min_height = int(h)
        def setExpanding(self, v): self._expanding = bool(v)
        def setElideMode(self, mode): self._elide_mode = mode
        def setAutoHide(self, v): self._auto_hide = bool(v)
    class QTabWidget(QWidget):
        class TabPosition:
            North = 0; South = 1; East = 2; West = 3
        class TabShape:
            Rounded = 0; Triangular = 1
        def __init__(self, parent=None):
            super().__init__(parent)
            self._tb = QTabBar()
            self._tabs = []
            self._current = 0
        def setDocumentMode(self, b): self._doc_mode = bool(b)
        def setTabPosition(self, pos): self._tab_pos = pos
        def setUsesScrollButtons(self, b): self._uses_scroll = bool(b)
        def setMovable(self, b): self._movable = bool(b)
        def setTabShape(self, s): self._shape = s
        def setTabBarAutoHide(self, b): self._auto_hide = bool(b)
        def setSizePolicy(self, h, v): self._size_policy = (h, v)
        def tabBar(self): return self._tb
        def addTab(self, widget, label):
            self._tabs.append((widget, label))
            return len(self._tabs) - 1
        def count(self): return len(self._tabs)
        def setCurrentIndex(self, idx):
            if 0 <= idx < len(self._tabs): self._current = idx
        def currentIndex(self): return self._current
        def tabText(self, idx):
            try:
                return self._tabs[idx][1]
            except Exception:
                return ""
        def setTabText(self, idx, text):
            try:
                w, _ = self._tabs[idx]
                self._tabs[idx] = (w, text)
            except Exception:
                pass
    class QDockWidget(QWidget): pass
    class QLabel(QWidget): pass
    class QPushButton(QWidget): pass
    class QListWidget(QWidget): pass
    class QTableWidget(QWidget):
        def __init__(self, *args, **kwargs): pass
        def horizontalHeader(self): return QHeaderView()
    class QTableWidgetItem:
        def __init__(self, *args, **kwargs): pass
    class QHeaderView(QObject):
        class ResizeMode:
            Fixed = 0
            Stretch = 1
        def setSectionResizeMode(self, *args, **kwargs): pass
    class QComboBox(QWidget): pass
    class QLineEdit(QWidget): pass
    class QProgressBar(QWidget): pass
    class QCheckBox(QWidget): pass
    class QSpinBox(QWidget): pass
    class QDoubleSpinBox(QWidget): pass
    class QSplitter(QWidget): pass
    class QFrame(QWidget): pass
    class QGridLayout(QObject):
        def __init__(self, *args, **kwargs): pass
        def addWidget(self, *args, **kwargs): pass
        def addLayout(self, *args, **kwargs): pass
        def addSpacing(self, *args, **kwargs): pass
        def addStretch(self, *args, **kwargs): pass
        def setContentsMargins(self, *args, **kwargs): pass
        def setAlignment(self, *args, **kwargs): pass
    class QVBoxLayout(QGridLayout): pass
    class QHBoxLayout(QGridLayout): pass
    class QSizePolicy:
        Expanding = 1; Preferred = 0
        def __init__(self, *args, **kwargs): pass
        class Policy:
            Expanding = 1; Preferred = 0
    class QMenuBar(QWidget): pass
    class QAction(QWidget): pass
    class QStatusBar(QWidget):
        def __init__(self, *args, **kwargs): pass
        def showMessage(self, *args, **kwargs): pass
        def addPermanentWidget(self, *args, **kwargs): pass
    class QScrollArea(QWidget): pass
    class QGroupBox(QWidget): pass
    class QDialog(QWidget): pass
    class QMessageBox(QWidget): pass
    class QTreeWidget(QWidget): pass
    class QTreeWidgetItem:
        def __init__(self, *args, **kwargs): pass
    class QFileDialog(QWidget): pass
    class QColorDialog(QWidget): pass
    class QMenu(QWidget): pass
    class QDateEdit(QWidget): pass
    class QTextEdit(QWidget):
        def __init__(self, *args, **kwargs): pass
        def setPlainText(self, *args, **kwargs): pass
        def toPlainText(self): return ""
    class QPlainTextEdit(QTextEdit): pass
    class QTextBrowser(QWidget): pass
    class QDialogButtonBox(QWidget):
        Ok = 1; Cancel = 2; Save = 3; Close = 4
        def __init__(self, *args, **kwargs): pass
        def accepted(self): return SimpleNamespace(connect=lambda f: None)
        def rejected(self): return SimpleNamespace(connect=lambda f: None)
    class QFormLayout(QGridLayout):
        def __init__(self, *args, **kwargs): pass
        def addRow(self, *args, **kwargs): pass

    # QtCore helpers
    class QDate: pass
    class QSize: pass
    class QPoint: pass
    class QParallelAnimationGroup(QObject):
        def __init__(self, *args, **kwargs): self._anims=[]
        def addAnimation(self, anim): self._anims.append(anim)
        def start(self, *args, **kwargs): pass
    class Qt:
        class AlignmentFlag:
            AlignLeft = 0; AlignRight = 1; AlignCenter = 2
        class Orientation:
            Horizontal = 1; Vertical = 2
        class MouseButton:
            LeftButton = 1; RightButton = 2
        class FocusPolicy:
            NoFocus = 0; StrongFocus = 1
        class TextElideMode:
            ElideNone = 0
    class QRect:
        def __init__(self, x=0, y=0, w=0, h=0):
            self._x, self._y, self._w, self._h = x, y, w, h
        def x(self): return self._x
        def y(self): return self._y
        def width(self): return self._w
        def height(self): return self._h
    class QEasingCurve:
        class Type:
            Linear = 0; InOutQuad = 1
        def __init__(self, *args, **kwargs): pass
    class QPropertyAnimation(QObject):
        def __init__(self, *args, **kwargs): self._start=None; self._end=None
        def setStartValue(self, v): self._start = v
        def setEndValue(self, v): self._end = v
        def start(self): pass

    # QtGui stubs
    class QFont:
        class Weight:
            Thin=0; ExtraLight=12; Light=25; Normal=50; Medium=57; DemiBold=63; Bold=75; Black=87
        def __init__(self, *args, **kwargs): self.pointSize=None; self.bold=False
        def setPointSize(self, size): self.pointSize = size
        def setBold(self, is_bold): self.bold = bool(is_bold)
    class QColor:
        def __init__(self, *args, **kwargs): self.value = args if args else kwargs
    class QBrush:
        def __init__(self, color=None): self.color = color
    class QIcon:
        def __init__(self, *args, **kwargs): self.source = args[0] if args else None
    class QPalette:
        class ColorRole:
            Window=0; WindowText=1; Base=2; AlternateBase=3; ToolTipBase=4; ToolTipText=5; Text=6; Button=7; ButtonText=8; BrightText=9; Highlight=10; HighlightedText=11
        def __init__(self): self.colors = {}
        def setColor(self, role, color): self.colors[role] = color
    class QPixmap:
        def __init__(self, *args, **kwargs): self.source = args[0] if args else None
    class QSyntaxHighlighter:
        def __init__(self, *args, **kwargs): self.document = args[0] if args else None
        def setDocument(self, doc): self.document = doc
    class QTextDocument: pass
    class QPainter: pass
    class QPen: pass
    class QContextMenuEvent: pass

    # Export classes to Qt modules
    qtcore.QObject=QObject; qtcore.QTimer=QTimer
    qtcore.QThread=QThread; qtcore.pyqtSignal=pyqtSignal; qtcore.pyqtSlot=pyqtSlot
    qtcore.QDate=QDate; qtcore.QSize=QSize; qtcore.QPoint=QPoint; qtcore.QParallelAnimationGroup=QParallelAnimationGroup
    qtcore.Qt=Qt; qtcore.QRect=QRect; qtcore.QPropertyAnimation=QPropertyAnimation; qtcore.QEasingCurve=QEasingCurve
    for name, cls in list(locals().items()):
        if name in ["QTabWidget","QDockWidget","QLabel","QPushButton","QListWidget","QTableWidget","QTableWidgetItem","QComboBox","QLineEdit","QProgressBar","QCheckBox","QSpinBox","QDoubleSpinBox","QSplitter","QFrame","QVBoxLayout","QHBoxLayout","QGridLayout","QWidget","QMainWindow","QApplication","QSizePolicy","QMenuBar","QAction","QStatusBar","QScrollArea","QGroupBox","QHeaderView","QDialog","QMessageBox","QTreeWidget","QTreeWidgetItem","QFileDialog","QColorDialog","QFormLayout","QTextEdit","QPlainTextEdit","QTextBrowser","QDialogButtonBox","QMenu","QDateEdit"]:
            setattr(qtwidgets, name, cls)
    for name, cls in list(locals().items()):
        if name in ["QFont","QBrush","QColor","QIcon","QPalette","QPixmap","QSyntaxHighlighter","QTextDocument","QPainter","QPen","QContextMenuEvent"]:
            setattr(qtgui, name, cls)
    sys.modules["PyQt6"]=mod; sys.modules["PyQt6.QtCore"]=qtcore; sys.modules["PyQt6.QtWidgets"]=qtwidgets; sys.modules["PyQt6.QtGui"]=qtgui

@pytest.fixture(autouse=True)
def ensure_event_loop():
    """Ensure there's an event loop available for tests that use asyncio.get_event_loop()."""
    try:
        loop = asyncio.get_running_loop()
    except RuntimeError:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
    yield
    # Do not close the loop here; tests may schedule tasks across modules.
    # Leaving it managed by pytest process avoids dangling loop issues.
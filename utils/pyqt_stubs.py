"""Narzędzia do instalacji stubów PyQt6 używane w testach i narzędziach CLI.

Funkcja :func:`install_pyqt_stubs` rejestruje minimalne klasy wymagane
przez UI bez konieczności posiadania systemowych bibliotek (np. libGL).
"""
from __future__ import annotations

import sys
import types
from importlib.machinery import ModuleSpec
from types import SimpleNamespace


def install_pyqt_stubs(force: bool = False) -> bool:
    """Instaluje stuby PyQt6, jeśli prawdziwe moduły nie są dostępne.

    Args:
        force: Wymusza instalację stubów nawet jeśli PyQt6 jest dostępny.

    Returns:
        ``True`` jeśli zainstalowano stuby, ``False`` w przeciwnym wypadku.
    """
    should_install = force
    if not should_install:
        try:
            import PyQt6  # type: ignore  # noqa: F401
            from PyQt6 import QtWidgets  # type: ignore  # noqa: F401
        except Exception:
            should_install = True
        else:
            return False

    if "PyQt6" in sys.modules:
        if not should_install:
            return False
        # Usuń resztki niepełnych importów PyQt6
        del sys.modules["PyQt6"]
        for key in [name for name in sys.modules if name.startswith("PyQt6.")]:
            del sys.modules[key]

    mod = types.ModuleType("PyQt6")
    mod.__path__ = []  # traktuj moduł jako pakiet
    mod.__spec__ = ModuleSpec("PyQt6", loader=None, is_package=True)
    qtcore = types.ModuleType("PyQt6.QtCore")
    qtwidgets = types.ModuleType("PyQt6.QtWidgets")
    qtgui = types.ModuleType("PyQt6.QtGui")
    qtcore.__package__ = "PyQt6"
    qtwidgets.__package__ = "PyQt6"
    qtgui.__package__ = "PyQt6"
    qtcore.__spec__ = ModuleSpec("PyQt6.QtCore", loader=None, is_package=False)
    qtwidgets.__spec__ = ModuleSpec("PyQt6.QtWidgets", loader=None, is_package=False)
    qtgui.__spec__ = ModuleSpec("PyQt6.QtGui", loader=None, is_package=False)

    class QObject:
        def __init__(self, parent=None):
            self._parent = parent

    class QWidget(QObject):
        def __init__(self, parent=None):
            super().__init__(parent)
            self._object_name = None
            self._min_size = None
            self._max_size = None
            self._size_policy = None
            self._style = ""
            self._size = None
            self._pos = None
            self._layout = None
            self._children = []
            if parent is not None and hasattr(parent, "_children"):
                parent._children.append(self)

        def setObjectName(self, name):
            self._object_name = name

        def objectName(self):
            return self._object_name

        def setMinimumSize(self, w, h):
            self._min_size = (w, h)

        def setMaximumSize(self, w, h):
            self._max_size = (w, h)

        def setSizePolicy(self, h, v):
            self._size_policy = (h, v)

        def setStyleSheet(self, style):
            self._style = style or ""

        def styleSheet(self):
            return self._style

        def resize(self, w, h):
            self._size = (w, h)

        def move(self, x, y):
            self._pos = (x, y)

        def setLayout(self, layout):
            self._layout = layout
            if hasattr(layout, "_set_parent"):
                layout._set_parent(self)

        def layout(self):
            return self._layout

        def children(self):
            return list(self._children)

        def findChildren(self, cls):
            return [child for child in self._children if isinstance(child, cls)]

        def screen(self):
            return SimpleNamespace(availableGeometry=lambda: QRect(0, 0, 1920, 1080))

    class QSplashScreen(QWidget):
        def __init__(self, pixmap=None):
            super().__init__()
            self._pixmap = pixmap
            self._window_flags = 0
            self._message = ""
            self._alignment = None
            self._color = None

        def setWindowFlags(self, flags):
            self._window_flags = flags

        def show(self):
            return None

        def showMessage(self, message, alignment=None, color=None):
            self._message = message
            self._alignment = alignment
            self._color = color

        def clearMessage(self):
            self._message = ""

        def finish(self, widget):
            return None

    class QMainWindow(QWidget):
        def __init__(self, parent=None):
            super().__init__(parent)
            self._central = None
            self._status_bar = None
            self._menu_bar = None
            self._title = None

        def setWindowTitle(self, title):
            self._title = title

        def setCentralWidget(self, widget):
            self._central = widget

        def statusBar(self):
            if not hasattr(self, "_status_bar") or self._status_bar is None:
                self._status_bar = QStatusBar()
            return self._status_bar

        def menuBar(self):
            if not hasattr(self, "_menu_bar") or self._menu_bar is None:
                self._menu_bar = QMenuBar()
            return self._menu_bar

        def setStatusBar(self, bar):
            self._status_bar = bar

        def setMenuBar(self, bar):
            self._menu_bar = bar

    class QApplication:
        _inst = None

        def __init__(self, args=None):
            type(self)._inst = self
            self._application_name = ""
            self._application_version = ""
            self._organization_name = ""
            self._style = "Fusion"
            self._font = None
            self.aboutToQuit = SimpleNamespace(connect=lambda callback: None)
            self.lastWindowClosed = SimpleNamespace(connect=lambda callback: None)

        def setApplicationName(self, name):
            self._application_name = name

        def setApplicationVersion(self, version):
            self._application_version = version

        def setOrganizationName(self, name):
            self._organization_name = name

        def setStyle(self, style):
            self._style = style

        def setFont(self, font):
            self._font = font

        def processEvents(self):
            return None

        def exec(self):  # pragma: no cover - nie używane w testach
            return 0

        @staticmethod
        def instance():
            return QApplication._inst

    class QThread(QObject):
        def start(self):
            pass

        def wait(self):
            pass

        def quit(self):
            pass

        def deleteLater(self):
            pass

    class QTimer(QObject):
        def __init__(self, parent=None):
            super().__init__(parent)
            self.interval = 0
            self.timeout = SimpleNamespace(connect=lambda f: None)

        def setInterval(self, interval):
            self.interval = interval

        def start(self):
            pass

    class QLayout(QObject):
        def __init__(self, parent=None):
            super().__init__(parent)
            self._items = []
            self._margins = (0, 0, 0, 0)
            self._spacing = 0
            self._parent_widget = parent
            if parent is not None and hasattr(parent, "setLayout"):
                try:
                    parent.setLayout(self)
                except Exception:
                    self._parent_widget = parent

        def _set_parent(self, widget):
            self._parent_widget = widget

        def addWidget(self, widget, *args, **kwargs):
            self._items.append(("widget", widget, args, kwargs))
            if hasattr(widget, "_children") and self._parent_widget is not None:
                if widget not in self._parent_widget._children:
                    self._parent_widget._children.append(widget)

        def addLayout(self, layout, *args, **kwargs):
            self._items.append(("layout", layout, args, kwargs))
            if hasattr(layout, "_set_parent"):
                layout._set_parent(self._parent_widget)

        def addItem(self, item, *args, **kwargs):
            self._items.append(("item", item, args, kwargs))

        def addStretch(self, *args, **kwargs):
            self._items.append(("stretch", args, kwargs))

        def setContentsMargins(self, left, top, right, bottom):
            self._margins = (left, top, right, bottom)

        def contentsMargins(self):
            return self._margins

        def setSpacing(self, spacing):
            self._spacing = spacing

        def spacing(self):
            return self._spacing

    class QLayoutItem:
        def __init__(self, *args, **kwargs):
            pass

    class QParallelAnimationGroup(QObject):
        def __init__(self, parent=None):
            super().__init__(parent)
            self._anims = []

        def addAnimation(self, animation):
            self._anims.append(animation)

        def start(self):
            pass

    class QDate:
        @staticmethod
        def currentDate():
            return QDate()

        def toString(self, fmt=None):
            return "1970-01-01"

    class QPoint:
        def __init__(self, x=0, y=0):
            self._x = x
            self._y = y

        def x(self):
            return self._x

        def y(self):
            return self._y

    class QSize:
        def __init__(self, w=0, h=0):
            self._w = w
            self._h = h

        def width(self):
            return self._w

        def height(self):
            return self._h

    class QEasingCurve:
        class Type:
            Linear = 0
            InOutQuad = 1

        def __init__(self, *args, **kwargs):
            pass

    class QPropertyAnimation(QObject):
        def __init__(self, *args, **kwargs):
            super().__init__(kwargs.get("parent"))
            self._start = None
            self._end = None
            self._curve = None

        def setStartValue(self, value):
            self._start = value

        def setEndValue(self, value):
            self._end = value

        def setEasingCurve(self, curve):
            self._curve = curve

        def start(self):
            pass

    class Qt:
        class AlignmentFlag:
            AlignLeft = 0
            AlignRight = 1
            AlignCenter = 2
            AlignBottom = 3

        class Orientation:
            Horizontal = 1
            Vertical = 2

        class MouseButton:
            LeftButton = 1
            RightButton = 2

        class FocusPolicy:
            NoFocus = 0
            StrongFocus = 1

        class TextElideMode:
            ElideNone = 0

        class GlobalColor:
            white = "#ffffff"
            darkBlue = "#00008b"
            transparent = 0

        class PenStyle:
            NoPen = 0

        class WindowType:
            WindowStaysOnTopHint = 0x00040000
            SplashScreen = 0x00000001

    class _BoundSignal:
        """Minimalna implementacja sygnału PyQt dla środowiska testowego."""

        def __init__(self):
            self._slots = []

        def connect(self, slot):  # pragma: no cover - prosta implementacja
            if callable(slot) and slot not in self._slots:
                self._slots.append(slot)
            return slot

        def emit(self, *args, **kwargs):  # pragma: no cover - prosta implementacja
            for slot in list(self._slots):
                slot(*args, **kwargs)

        def disconnect(self, slot=None):  # pragma: no cover - prosta implementacja
            if slot is None:
                self._slots.clear()
            else:
                self._slots = [s for s in self._slots if s != slot]

    class _SignalDescriptor:
        def __init__(self):
            self._name = None

        def __set_name__(self, owner, name):
            self._name = name

        def __get__(self, instance, owner):
            if instance is None:
                return self
            if self._name is None:
                raise AttributeError("Signal descriptor is missing a name")
            signals = instance.__dict__.setdefault("__qt_signals__", {})
            if self._name not in signals:
                signals[self._name] = _BoundSignal()
            return signals[self._name]

        def __call__(self, *args, **kwargs):
            return self

    def pyqtSignal(*args, **kwargs):
        return _SignalDescriptor()

    def pyqtSlot(*decorator_args, **decorator_kwargs):
        def decorator(fn):
            return fn

        return decorator

    class QTabBar(QObject):
        def __init__(self):
            super().__init__()
            self._visible = True
            self._min_height = 0

        def setVisible(self, visible):
            self._visible = bool(visible)

        def setMinimumHeight(self, height):
            self._min_height = int(height)

        def setExpanding(self, expanding):
            self._expanding = bool(expanding)

        def setElideMode(self, mode):
            self._elide_mode = mode

        def setAutoHide(self, auto_hide):
            self._auto_hide = bool(auto_hide)

    class QTabWidget(QWidget):
        class TabPosition:
            North = 0
            South = 1
            East = 2
            West = 3

        class TabShape:
            Rounded = 0
            Triangular = 1

        def __init__(self, parent=None):
            super().__init__(parent)
            self._tb = QTabBar()
            self._tabs = []
            self._current = 0

        def setDocumentMode(self, enabled):
            self._doc_mode = bool(enabled)

        def setTabPosition(self, position):
            self._tab_pos = position

        def setUsesScrollButtons(self, enabled):
            self._uses_scroll = bool(enabled)

        def setMovable(self, movable):
            self._movable = bool(movable)

        def setTabShape(self, shape):
            self._shape = shape

        def setTabBarAutoHide(self, enabled):
            self._auto_hide = bool(enabled)

        def setSizePolicy(self, h, v):
            self._size_policy = (h, v)

        def tabBar(self):
            return self._tb

        def addTab(self, widget, label):
            self._tabs.append((widget, label))
            return len(self._tabs) - 1

        def count(self):
            return len(self._tabs)

        def setCurrentIndex(self, idx):
            if 0 <= idx < len(self._tabs):
                self._current = idx

        def currentIndex(self):
            return self._current

        def tabText(self, idx):
            try:
                return self._tabs[idx][1]
            except Exception:
                return ""

        def setTabText(self, idx, text):
            try:
                widget, _ = self._tabs[idx]
                self._tabs[idx] = (widget, text)
            except Exception:
                pass

    class QDockWidget(QWidget):
        pass

    class QLabel(QWidget):
        def __init__(self, text="", parent=None):
            super().__init__(parent)
            self._text = str(text)
            self._alignment = None
            self._word_wrap = False

        def setText(self, text):
            self._text = str(text)

        def text(self):
            return self._text

        def setAlignment(self, alignment):
            self._alignment = alignment

        def alignment(self):
            return self._alignment

        def setWordWrap(self, enabled):
            self._word_wrap = bool(enabled)

        def wordWrap(self):
            return self._word_wrap

    class QPushButton(QWidget):
        clicked = pyqtSignal()

        def __init__(self, text="", parent=None):
            super().__init__(parent)
            self._text = str(text)
            self._tooltip = ""

        def setText(self, text):
            self._text = str(text)

        def text(self):
            return self._text

        def setToolTip(self, tooltip):
            self._tooltip = tooltip or ""

        def toolTip(self):
            return self._tooltip

    class QListWidget(QWidget):
        pass

    class QTableWidget(QWidget):
        def __init__(self, *args, **kwargs):
            super().__init__(*args, **kwargs)

        def horizontalHeader(self):
            return QHeaderView()

    class QTableWidgetItem:
        def __init__(self, *args, **kwargs):
            pass

    class QHeaderView(QObject):
        class ResizeMode:
            Fixed = 0
            Stretch = 1

        def setSectionResizeMode(self, *args, **kwargs):
            pass

    class QComboBox(QWidget):
        pass

    class QLineEdit(QWidget):
        pass

    class QProgressBar(QWidget):
        pass

    class QCheckBox(QWidget):
        pass

    class QSpinBox(QWidget):
        pass

    class QDoubleSpinBox(QWidget):
        pass

    class QSplitter(QWidget):
        pass

    class QFrame(QWidget):
        pass

    class QGridLayout(QLayout):
        def addWidget(self, widget, *args, **kwargs):
            super().addWidget(widget, *args, **kwargs)

        def addLayout(self, layout, *args, **kwargs):
            super().addLayout(layout, *args, **kwargs)

        def addSpacing(self, value):
            self._items.append(("spacing", value))

        def addStretch(self, stretch=0):
            super().addStretch(stretch)

        def setContentsMargins(self, left, top, right, bottom):
            self._margins = (left, top, right, bottom)

        def contentsMargins(self):
            return self._margins

        def setSpacing(self, spacing):
            self._spacing = spacing

        def spacing(self):
            return self._spacing

        def setAlignment(self, *args, **kwargs):
            self._items.append(("alignment", args, kwargs))

    class QVBoxLayout(QGridLayout):
        pass

    class QHBoxLayout(QGridLayout):
        pass

    class QSizePolicy:
        Expanding = 1
        Preferred = 0

        def __init__(self, *args, **kwargs):
            pass

        class Policy:
            Expanding = 1
            Preferred = 0

    class QMenuBar(QWidget):
        pass

    class QAction(QWidget):
        pass

    class QStatusBar(QWidget):
        def showMessage(self, *args, **kwargs):
            pass

        def addPermanentWidget(self, *args, **kwargs):
            pass

    class QScrollArea(QWidget):
        pass

    class QGroupBox(QWidget):
        pass

    class QDialog(QWidget):
        pass

    class QMessageBox(QWidget):
        pass

    class QTreeWidget(QWidget):
        pass

    class QTreeWidgetItem:
        def __init__(self, *args, **kwargs):
            pass

    class QFileDialog(QWidget):
        pass

    class QColorDialog(QWidget):
        pass

    class QMenu(QWidget):
        pass

    class QDateEdit(QWidget):
        pass

    class QTextEdit(QWidget):
        def setPlainText(self, *args, **kwargs):
            pass

        def toPlainText(self):
            return ""

    class QPlainTextEdit(QTextEdit):
        pass

    class QTextBrowser(QWidget):
        pass

    class QDialogButtonBox(QWidget):
        Ok = 1
        Cancel = 2
        Save = 3
        Close = 4

        def accepted(self):
            return SimpleNamespace(connect=lambda f: None)

        def rejected(self):
            return SimpleNamespace(connect=lambda f: None)

    class QFormLayout(QGridLayout):
        pass

    class QRect:
        def __init__(self, x, y, w, h):
            self.x = x
            self.y = y
            self.w = w
            self.h = h

    class QFont:
        class Weight:
            Thin = 0
            ExtraLight = 12
            Light = 25
            Normal = 50
            Medium = 57
            DemiBold = 63
            Bold = 75
            Black = 87

        def __init__(self, *args, **kwargs):
            self.point_size = None
            self.bold = False

        def setPointSize(self, size):
            self.point_size = size

        def setBold(self, is_bold):
            self.bold = bool(is_bold)

    class QColor:
        def __init__(self, *args, **kwargs):
            self.value = args or kwargs

    class QBrush:
        def __init__(self, color=None):
            self.color = color

    class QIcon:
        def __init__(self, *args, **kwargs):
            self.source = args[0] if args else None

    class QPalette:
        class ColorRole:
            Window = 0
            WindowText = 1
            Base = 2
            AlternateBase = 3
            ToolTipBase = 4
            ToolTipText = 5
            Text = 6
            Button = 7
            ButtonText = 8
            BrightText = 9
            Highlight = 10
            HighlightedText = 11

        def __init__(self):
            self.colors = {}

        def setColor(self, role, color):
            self.colors[role] = color

    class QPixmap:
        def __init__(self, width=0, height=0):
            self._width = int(width)
            self._height = int(height)
            self._fill = None

        def fill(self, color):
            self._fill = color

        def width(self):
            return self._width

        def height(self):
            return self._height

    class QSyntaxHighlighter:
        def __init__(self, *args, **kwargs):
            self.document = args[0] if args else None

        def setDocument(self, doc):
            self.document = doc

    class QTextDocument:
        pass

    class QPainter:
        Antialiasing = 1

        def __init__(self, target=None):
            self._target = target
            self._pen = None
            self._brush = None

        def setRenderHint(self, *args, **kwargs):
            pass

        def setBrush(self, brush):
            self._brush = brush

        def setPen(self, pen):
            self._pen = pen

        def drawRoundedRect(self, *args, **kwargs):
            pass

        def drawText(self, *args, **kwargs):
            pass

        def fillRect(self, *args, **kwargs):
            pass

        def end(self):
            pass

    class QPen:
        def __init__(self, color=None):
            self.color = color

    class QContextMenuEvent:
        pass

    class QLinearGradient:
        def __init__(self, *args, **kwargs):
            self.points = args
            self.colors = []

        def setColorAt(self, position, color):
            self.colors.append((position, color))

    qtcore.QObject = QObject
    qtcore.QTimer = QTimer
    qtcore.QThread = QThread
    qtcore.QDate = QDate
    qtcore.QPoint = QPoint
    qtcore.QSize = QSize
    qtcore.QRect = QRect
    qtcore.pyqtSignal = pyqtSignal
    qtcore.pyqtSlot = pyqtSlot
    qtcore.Qt = Qt
    qtcore.QEasingCurve = QEasingCurve
    qtcore.QPropertyAnimation = QPropertyAnimation
    qtcore.QParallelAnimationGroup = QParallelAnimationGroup

    qtwidgets.QApplication = QApplication
    qtwidgets.QWidget = QWidget
    qtwidgets.QMainWindow = QMainWindow
    qtwidgets.QTabWidget = QTabWidget
    qtwidgets.QTabBar = QTabBar
    qtwidgets.QDockWidget = QDockWidget
    qtwidgets.QLabel = QLabel
    qtwidgets.QPushButton = QPushButton
    qtwidgets.QListWidget = QListWidget
    qtwidgets.QTableWidget = QTableWidget
    qtwidgets.QTableWidgetItem = QTableWidgetItem
    qtwidgets.QHeaderView = QHeaderView
    qtwidgets.QComboBox = QComboBox
    qtwidgets.QLineEdit = QLineEdit
    qtwidgets.QProgressBar = QProgressBar
    qtwidgets.QCheckBox = QCheckBox
    qtwidgets.QSpinBox = QSpinBox
    qtwidgets.QDoubleSpinBox = QDoubleSpinBox
    qtwidgets.QSplitter = QSplitter
    qtwidgets.QFrame = QFrame
    qtwidgets.QGridLayout = QGridLayout
    qtwidgets.QVBoxLayout = QVBoxLayout
    qtwidgets.QHBoxLayout = QHBoxLayout
    qtwidgets.QSizePolicy = QSizePolicy
    qtwidgets.QMenuBar = QMenuBar
    qtwidgets.QAction = QAction
    qtwidgets.QStatusBar = QStatusBar
    qtwidgets.QScrollArea = QScrollArea
    qtwidgets.QGroupBox = QGroupBox
    qtwidgets.QDialog = QDialog
    qtwidgets.QMessageBox = QMessageBox
    qtwidgets.QSplashScreen = QSplashScreen
    qtwidgets.QTreeWidget = QTreeWidget
    qtwidgets.QTreeWidgetItem = QTreeWidgetItem
    qtwidgets.QFileDialog = QFileDialog
    qtwidgets.QColorDialog = QColorDialog
    qtwidgets.QMenu = QMenu
    qtwidgets.QDateEdit = QDateEdit
    qtwidgets.QTextEdit = QTextEdit
    qtwidgets.QPlainTextEdit = QPlainTextEdit
    qtwidgets.QTextBrowser = QTextBrowser
    qtwidgets.QDialogButtonBox = QDialogButtonBox
    qtwidgets.QFormLayout = QFormLayout
    qtwidgets.QLayout = QLayout
    qtwidgets.QLayoutItem = QLayoutItem

    qtgui.QFont = QFont
    qtgui.QColor = QColor
    qtgui.QBrush = QBrush
    qtgui.QIcon = QIcon
    qtgui.QPalette = QPalette
    qtgui.QPixmap = QPixmap
    qtgui.QSyntaxHighlighter = QSyntaxHighlighter
    qtgui.QTextDocument = QTextDocument
    qtgui.QPainter = QPainter
    qtgui.QPen = QPen
    qtgui.QContextMenuEvent = QContextMenuEvent
    qtgui.QLinearGradient = QLinearGradient
    qtgui.QAction = QAction

    mod.QtCore = qtcore
    mod.QtWidgets = qtwidgets
    mod.QtGui = qtgui

    sys.modules["PyQt6"] = mod
    sys.modules["PyQt6.QtCore"] = qtcore
    sys.modules["PyQt6.QtWidgets"] = qtwidgets
    sys.modules["PyQt6.QtGui"] = qtgui

    return True


__all__ = ["install_pyqt_stubs"]

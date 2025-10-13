from PyQt6.QtWidgets import QWidget, QLabel
from PyQt6.QtCore import Qt, QTimer, QPoint, QEasingCurve
from PyQt6.QtGui import QPalette

class Toast(QWidget):
    def __init__(self, parent: QWidget, text: str, timeout_ms: int = 3000):
        super().__init__(parent)
        self.setWindowFlags(Qt.WindowType.FramelessWindowHint | Qt.WindowType.ToolTip)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, True)
        self.label = QLabel(text, self)
        self.label.setWordWrap(True)
        self.label.setStyleSheet("""
            background: rgba(0,0,0,0.85);
            color: #fff;
            padding: 10px 14px;
            border-radius: 10px;
            font-size: 13px;
            max-width: 380px;
        """)
        self.adjustSize()
        # position: bottom-right corner of parent
        pw = parent.width()
        ph = parent.height()
        sw = self.sizeHint().width()
        sh = self.sizeHint().height()
        self.setGeometry(pw - sw - 24, ph - sh - 24, sw, sh)
        self.show()
        QTimer.singleShot(timeout_ms, self.close)

def show_toast(parent: QWidget, text: str, timeout_ms: int = 3000):
    if parent is None:
        return
    Toast(parent, text, timeout_ms)

"""
FlowLayout - responsywny układ z zawijaniem elementów
Umożliwia automatyczne zawijanie widgetów do nowych wierszy
"""

from PyQt6.QtCore import Qt, QRect, QSize, QPoint
from PyQt6.QtWidgets import QLayout, QLayoutItem, QSizePolicy


class FlowLayout(QLayout):
    """Responsywny układ z zawijaniem elementów do nowych wierszy"""
    
    def __init__(self, parent=None, margin=0, spacing=-1):
        super().__init__(parent)
        
        if parent is not None:
            self.setContentsMargins(margin, margin, margin, margin)
        
        self.setSpacing(spacing)
        self.item_list = []
    
    def __del__(self):
        item = self.takeAt(0)
        while item:
            item = self.takeAt(0)
    
    def addItem(self, item):
        """Dodaje element do układu"""
        self.item_list.append(item)
    
    def count(self):
        """Zwraca liczbę elementów"""
        return len(self.item_list)
    
    def itemAt(self, index):
        """Zwraca element na danym indeksie"""
        if 0 <= index < len(self.item_list):
            return self.item_list[index]
        return None
    
    def takeAt(self, index):
        """Usuwa i zwraca element na danym indeksie"""
        if 0 <= index < len(self.item_list):
            return self.item_list.pop(index)
        return None
    
    def expandingDirections(self):
        """Określa kierunki rozszerzania"""
        return Qt.Orientation(0)
    
    def hasHeightForWidth(self):
        """Określa czy układ ma wysokość zależną od szerokości"""
        return True
    
    def heightForWidth(self, width):
        """Oblicza wysokość dla danej szerokości"""
        height = self.doLayout(QRect(0, 0, width, 0), True)
        return height
    
    def setGeometry(self, rect):
        """Ustawia geometrię układu"""
        super().setGeometry(rect)
        self.doLayout(rect, False)
    
    def sizeHint(self):
        """Zwraca sugerowany rozmiar"""
        return self.minimumSize()
    
    def minimumSize(self):
        """Zwraca minimalny rozmiar"""
        size = QSize()
        
        for item in self.item_list:
            size = size.expandedTo(item.minimumSize())
        
        size += QSize(2 * self.contentsMargins().top(), 2 * self.contentsMargins().top())
        return size
    
    def doLayout(self, rect, testOnly):
        x = rect.x()
        y = rect.y()
        lineHeight = 0

        for i in range(self.count()):
            item = self.itemAt(i)
            wid = item.widget()
            spaceX = self.spacing() + wid.style().layoutSpacing(
                QSizePolicy.ControlType.PushButton, QSizePolicy.ControlType.PushButton, Qt.Orientation.Horizontal)
            spaceY = self.spacing() + wid.style().layoutSpacing(
                QSizePolicy.ControlType.PushButton, QSizePolicy.ControlType.PushButton, Qt.Orientation.Vertical)
            nextX = x + item.sizeHint().width() + spaceX
            if nextX - spaceX > rect.right() and lineHeight > 0:
                x = rect.x()
                y = y + lineHeight + spaceY
                nextX = x + item.sizeHint().width() + spaceX
                lineHeight = 0

            if not testOnly:
                item.setGeometry(QRect(QPoint(x, y), item.sizeHint()))

            x = nextX
            lineHeight = max(lineHeight, item.sizeHint().height())

        return y + lineHeight - rect.y()
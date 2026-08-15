"""Compact in-flight toast notification."""

from PySide6.QtCore import Qt, QTimer
from PySide6.QtGui import QColor, QFont, QPainter, QPen
from PySide6.QtWidgets import QWidget


class PopupWidget(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.text = ""
        self.hide()
        self.timer = QTimer(self)
        self.timer.setSingleShot(True)
        self.timer.timeout.connect(self.hide)
        self.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)
        self.setAttribute(Qt.WidgetAttribute.WA_NoSystemBackground)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)

    def show_message(self, text: str, timeout_ms: int = 1500):
        self.text = text
        self.show()
        self.raise_()
        self.update()
        self.timer.start(timeout_ms)

    def paintEvent(self, event):
        if not self.text:
            return
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        width, height = 430, 58
        x = (self.width() - width) // 2
        y = 78
        painter.setBrush(QColor(8, 12, 15, 224))
        painter.setPen(QPen(QColor(255, 255, 255, 48), 1))
        painter.drawRoundedRect(x, y, width, height, 12, 12)
        painter.setPen(QColor(250, 252, 253))
        painter.setFont(QFont("Sans Serif", 14, QFont.Weight.DemiBold))
        painter.drawText(x, y, width, height, Qt.AlignmentFlag.AlignCenter, self.text)

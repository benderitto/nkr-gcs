from PySide6.QtCore import (
    Qt,
    QTimer,
)

from PySide6.QtGui import (
    QPainter,
    QColor,
    QFont,
)

from PySide6.QtWidgets import QWidget


class PopupWidget(QWidget):

    def __init__(
        self,
        parent=None,
    ):

        super().__init__(parent)

        self.text = ""

        self.hide()

        self.timer = QTimer(self)

        self.timer.setSingleShot(True)

        self.timer.timeout.connect(
            self.hide
        )

        self.setAttribute(
            Qt.WA_TransparentForMouseEvents
        )

        self.setAttribute(
            Qt.WA_NoSystemBackground
        )

        self.setAttribute(
            Qt.WA_TranslucentBackground
        )

    def show_message(
        self,
        text: str,
        timeout_ms: int = 1500,
    ):

        self.text = text

        self.show()

        self.raise_()

        self.update()

        self.timer.start(timeout_ms)

    def paintEvent(
        self,
        event,
    ):

        if not self.text:
            return

        painter = QPainter(self)

        painter.setRenderHint(
            QPainter.Antialiasing
        )

        w = 500
        h = 90

        x = (self.width() - w) // 2
        y = 70

        painter.setBrush(
            QColor(0, 0, 0, 180)
        )

        painter.setPen(Qt.NoPen)

        painter.drawRoundedRect(
            x,
            y,
            w,
            h,
            18,
            18,
        )

        painter.setPen(
            QColor(255, 255, 255)
        )

        font = QFont()

        font.setPointSize(22)

        font.setBold(True)

        painter.setFont(font)

        painter.drawText(
            x,
            y,
            w,
            h,
            Qt.AlignCenter,
            self.text,
        )
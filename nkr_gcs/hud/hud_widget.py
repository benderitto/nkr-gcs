from PySide6.QtCore import Qt
from PySide6.QtGui import QColor
from PySide6.QtGui import QFont
from PySide6.QtGui import QPainter
from PySide6.QtWidgets import QWidget


class HUDWidget(QWidget):

    def __init__(self, parent=None):

        super().__init__(parent)

        self.state = None

        self.setAttribute(
            Qt.WidgetAttribute.WA_TransparentForMouseEvents
        )

        self.setAttribute(
            Qt.WidgetAttribute.WA_TranslucentBackground
        )

    def paintEvent(self, event):

        if self.state is None:
            return

        painter = QPainter(self)

        painter.setPen(QColor(255, 255, 255))

        painter.setFont(QFont("Arial", 18))

        painter.drawText(
            20,
            35,
            f"CAM: {self.state.camera}"
        )

        painter.drawText(
            20,
            65,
            f"MODE: {self.state.drive_mode}"
        )

        painter.drawText(
            20,
            95,
            f"BATT: {self.state.battery_percent}%"
        )

        painter.drawText(
            20,
            125,
            f"SAT: {self.state.satellites}"
        )
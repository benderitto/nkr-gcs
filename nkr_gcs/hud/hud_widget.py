from PySide6.QtCore import Qt, QRectF
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

        safety = "E-STOP" if self.state.estop else (
            "ARMED" if self.state.armed else "DISARMED"
        )
        values = (
            (f"CAM {self.state.camera}", 190),
            (f"VIDEO {self.state.video_state}", 145),
            (f"LIGHT {self.state.light_mode}", 125),
            (f"BATT {self.state.battery_percent}%", 115),
            (f"{self.state.speed:.0f} km/h", 108),
            (f"{self.state.bitrate_mbps:.1f} Mbit/s", 128),
            (f"SAT {self.state.satellites}", 84),
            (self.state.link_type, 82),
            (self.state.drive_mode, 130),
            (safety, 95),
        )
        x = 16
        y = 14
        height = 42
        painter.setFont(QFont("Arial", 13, QFont.DemiBold))
        for text, width in values:
            if x + width > self.width() - 86:
                break
            rect = QRectF(x, y, width, height)
            color = QColor(151, 29, 42, 220) if text == "E-STOP" else QColor(14, 21, 28, 172)
            painter.setBrush(color)
            painter.setPen(QColor(255, 255, 255, 72))
            painter.drawRoundedRect(rect, 10, 10)
            painter.setPen(QColor(255, 255, 255, 245))
            painter.drawText(rect, Qt.AlignCenter, text)
            x += width + 8

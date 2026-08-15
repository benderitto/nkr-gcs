"""DJI-inspired, video-first telemetry overlay for the operator view."""

from PySide6.QtCore import Qt, QRectF
from PySide6.QtGui import QColor, QFont, QLinearGradient, QPainter, QPen
from PySide6.QtWidgets import QWidget


WHITE = QColor(250, 252, 253)
MUTED = QColor(210, 217, 222, 215)
PANEL = QColor(8, 12, 15, 188)
GREEN = QColor(22, 194, 115)
RED = QColor(239, 68, 68)
AMBER = QColor(245, 180, 46)


class HUDWidget(QWidget):
    """Paint only essential state over the full-screen video feed."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.state = None
        self.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)

    def paintEvent(self, event):
        if self.state is None:
            return
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        self._paint_readability_gradients(painter)
        self._paint_top_bar(painter)
        self._paint_bottom_bar(painter)

    def _paint_readability_gradients(self, painter):
        top = QLinearGradient(0, 0, 0, 104)
        top.setColorAt(0, QColor(0, 0, 0, 190))
        top.setColorAt(1, QColor(0, 0, 0, 0))
        painter.fillRect(QRectF(0, 0, self.width(), 104), top)
        bottom = QLinearGradient(0, self.height() - 108, 0, self.height())
        bottom.setColorAt(0, QColor(0, 0, 0, 0))
        bottom.setColorAt(1, QColor(0, 0, 0, 185))
        painter.fillRect(QRectF(0, self.height() - 108, self.width(), 108), bottom)

    def _paint_top_bar(self, painter):
        y, height = 17, 46
        self._label(painter, QRectF(20, y, 72, height), "NKR", bold=True)
        safety = "E-STOP" if self.state.estop else (
            "ARMED" if self.state.armed else "DISARMED"
        )
        safety_color = RED if self.state.estop else (
            GREEN if self.state.armed else QColor(70, 78, 85)
        )
        self._pill(painter, QRectF(100, y, 124, height), safety, safety_color)
        mode_width = 184
        self._pill(
            painter,
            QRectF((self.width() - mode_width) / 2, y, mode_width, height),
            self.state.drive_mode,
            QColor(9, 15, 19, 196),
        )
        right = self.width() - 86
        items = (
            (f"{self.state.battery_percent}%", 72, self._battery_color()),
            (self.state.link_type, 66, PANEL),
            (self._video_label(), 112, PANEL),
        )
        for text, width, color in items:
            right -= width
            self._pill(painter, QRectF(right, y, width, height), text, color)
            right -= 8

    def _paint_bottom_bar(self, painter):
        y = self.height() - 70
        self._pill(
            painter, QRectF(20, y, 184, 48),
            f"●  CAM {self.state.camera}", PANEL,
            accent=GREEN if self.state.video_state == "LIVE" else AMBER,
        )
        stats = (
            ("SPEED", f"{self.state.speed:.1f} km/h"),
            ("LINK", f"{self.state.bitrate_mbps:.1f} Mbit/s"),
            (
                "LATENCY",
                "—" if self.state.latency_ms is None
                else f"{self.state.latency_ms} ms",
            ),
        )
        total_width = 3 * 146
        x = (self.width() - total_width) / 2
        for caption, value in stats:
            self._metric(painter, QRectF(x, y - 3, 146, 54), caption, value)
            x += 146
        right_text = f"SAT {self.state.satellites}   •   LIGHT {self.state.light_mode}"
        self._label(
            painter, QRectF(self.width() - 292, y, 272, 48), right_text,
            align=Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter,
        )

    def _pill(self, painter, rect, text, color, accent=None):
        painter.setPen(QPen(QColor(255, 255, 255, 42), 1))
        painter.setBrush(color)
        painter.drawRoundedRect(rect, rect.height() / 2, rect.height() / 2)
        painter.setPen(accent or WHITE)
        painter.setFont(QFont("Sans Serif", 12, QFont.Weight.DemiBold))
        painter.drawText(rect, Qt.AlignmentFlag.AlignCenter, text)

    def _metric(self, painter, rect, caption, value):
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(QColor(6, 9, 12, 158))
        painter.drawRoundedRect(rect, 8, 8)
        painter.setPen(MUTED)
        painter.setFont(QFont("Sans Serif", 8, QFont.Weight.DemiBold))
        painter.drawText(QRectF(rect.x(), rect.y() + 5, rect.width(), 16),
                         Qt.AlignmentFlag.AlignCenter, caption)
        painter.setPen(WHITE)
        painter.setFont(QFont("Sans Serif", 12, QFont.Weight.DemiBold))
        painter.drawText(QRectF(rect.x(), rect.y() + 20, rect.width(), 28),
                         Qt.AlignmentFlag.AlignCenter, value)

    def _label(self, painter, rect, text, bold=False,
               align=Qt.AlignmentFlag.AlignCenter):
        painter.setPen(WHITE)
        painter.setFont(QFont(
            "Sans Serif", 15 if bold else 11,
            QFont.Weight.Bold if bold else QFont.Weight.DemiBold,
        ))
        painter.drawText(rect, align, text)

    def _video_label(self):
        return "●  LIVE" if self.state.video_state == "LIVE" else self.state.video_state

    def _battery_color(self):
        if self.state.battery_percent <= 15:
            return RED
        if self.state.battery_percent <= 30:
            return AMBER
        return PANEL

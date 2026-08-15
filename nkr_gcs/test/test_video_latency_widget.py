import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtCore import QRect
from PySide6.QtGui import QColor, QImage, QPainter
from PySide6.QtWidgets import QApplication

from nkr_gcs.video.latency_marker import (
    BLOCK_WIDTH,
    DATA_WIDTH,
    MARKER_HEIGHT,
    PREAMBLE,
    TIMESTAMP_BITS,
)
from nkr_gcs.video.video_widget import VideoWidget


def _app():
    return QApplication.instance() or QApplication([])


def test_widget_reports_latency_and_hides_marker():
    _app()
    captured_ms = 1_786_820_123_450
    ticks = (captured_ms // 10) % (1 << TIMESTAMP_BITS)
    gray = ticks ^ (ticks >> 1)
    bits = list(PREAMBLE) + [
        (gray >> bit) & 1 for bit in range(TIMESTAMP_BITS)
    ]

    image = QImage(640, 480, QImage.Format.Format_RGB888)
    background = QColor(90, 100, 110)
    image.fill(background)
    painter = QPainter(image)
    for index, bit in enumerate(bits):
        painter.fillRect(
            QRect(
                index * BLOCK_WIDTH, image.height() - MARKER_HEIGHT,
                DATA_WIDTH, MARKER_HEIGHT,
            ),
            QColor("white") if bit else QColor("black"),
        )
    painter.end()

    measured = []
    widget = VideoWidget()
    widget.set_synchronized_time_source(lambda: captured_ms + 83)
    widget.set_latency_listener(measured.append)
    widget._on_frame(image)

    assert measured == [83]
    assert image.pixelColor(2, image.height() - 2) == background
    widget.close()

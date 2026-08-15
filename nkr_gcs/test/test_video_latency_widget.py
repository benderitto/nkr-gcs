import os
import threading

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


def test_portable_worker_is_joined_before_reconnect():
    _app()
    widget = VideoWidget()
    stop_event = threading.Event()
    stopped = threading.Event()

    def worker():
        stop_event.wait(1.0)
        stopped.set()

    thread = threading.Thread(target=worker)
    thread.start()
    widget._av_stop = stop_event
    widget._av_thread = thread
    generation = widget._video_generation

    assert widget._stop_pipeline() is True
    assert stopped.is_set()
    assert not thread.is_alive()
    assert widget._video_generation == generation + 1
    widget.close()


def test_stale_latest_frame_is_ignored_after_camera_switch():
    _app()
    widget = VideoWidget()
    image = QImage(640, 480, QImage.Format.Format_RGB888)
    widget._video_generation = 4

    widget._publish_latest_frame(3, image)
    widget._on_latest_frame(3)

    assert widget._frame is None
    widget.close()


def test_frame_mailbox_keeps_only_the_latest_frame():
    _app()
    widget = VideoWidget()
    widget._video_generation = 2
    first = QImage(640, 480, QImage.Format.Format_RGB888)
    second = QImage(640, 480, QImage.Format.Format_RGB888)
    first.fill(QColor("red"))
    second.fill(QColor("blue"))

    widget._publish_latest_frame(2, first)
    widget._publish_latest_frame(2, second)
    widget._on_latest_frame(2)

    assert widget._frame.pixelColor(20, 20) == QColor("blue")
    widget.close()

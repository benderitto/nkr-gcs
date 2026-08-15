"""Low-latency native GStreamer video display for the operator GCS."""

from collections import deque
from enum import Enum
import logging
import statistics
import threading
import time

from PySide6.QtCore import QRect, QTimer, Qt, Signal
from PySide6.QtGui import QColor, QFont, QImage, QPainter
from PySide6.QtWidgets import QWidget

try:
    import gi

    gi.require_version("Gst", "1.0")
    from gi.repository import Gst

    Gst.init(None)
except (ImportError, ValueError):
    Gst = None

try:
    import av
except ImportError:
    av = None

from .video_config import CAMERA_STREAMS, build_stream_url, retry_delay, stream_changed
from .latency_marker import (
    BLOCK_WIDTH, DATA_WIDTH, MARKER_HEIGHT, MARKER_WIDTH,
    calculate_video_latency_ms, measure_video_latency_ms,
)

logger = logging.getLogger(__name__)


class VideoState(Enum):
    DISABLED = "DISABLED"
    CONNECTING = "CONNECTING"
    LIVE = "LIVE"
    RECONNECTING = "RECONNECTING"
    VIDEO_LOST = "VIDEO LOST"


class VideoWidget(QWidget):
    """Render the newest decoded frame without a browser or queued old frames."""

    frame_ready = Signal(QImage)
    pyav_frame_ready = Signal(int, QImage)
    backend_failed = Signal(int, str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setStyleSheet("background-color: black;")
        self.settings = None
        self.stream = None
        self.state = VideoState.DISABLED
        self._pipeline = None
        self._bus = None
        self._frame = None
        self._av_stop = None
        self._av_thread = None
        self._video_generation = 0
        self._shutting_down = False
        self._retry_attempt = 0
        self._popup = None
        self._state_listener = None
        self._latency_listener = None
        self._synchronized_now_ms = lambda: None
        self._latency_samples = deque(maxlen=5)
        self._invalid_latency_frames = 0
        self._last_latency_warning = 0.0
        self._last_popup = {}
        self.frame_ready.connect(self._on_frame, Qt.ConnectionType.QueuedConnection)
        self.pyav_frame_ready.connect(
            self._on_pyav_frame, Qt.ConnectionType.QueuedConnection)
        self.backend_failed.connect(
            self._on_backend_failed, Qt.ConnectionType.QueuedConnection)
        self._retry_timer = QTimer(self)
        self._retry_timer.setSingleShot(True)
        self._retry_timer.timeout.connect(self.reconnect)
        self._bus_timer = QTimer(self)
        self._bus_timer.setInterval(100)
        self._bus_timer.timeout.connect(self._poll_bus)

    def configure(self, settings) -> None:
        self.settings = settings
        if not settings.video_enabled:
            self._stop_pipeline()
            self._set_state(VideoState.DISABLED)
            return
        if settings.video_default_stream not in CAMERA_STREAMS:
            raise ValueError("video_default_stream is not whitelisted")
        if self.stream is None:
            self.stream = settings.video_default_stream
        self._connect_current_stream()

    def set_popup(self, popup) -> None:
        self._popup = popup

    def set_state_listener(self, listener) -> None:
        self._state_listener = listener

    def set_latency_listener(self, listener) -> None:
        self._latency_listener = listener

    def set_synchronized_time_source(self, now_ms) -> None:
        self._synchronized_now_ms = now_ms

    def set_stream(self, stream: str) -> None:
        if self._shutting_down:
            return
        if not stream_changed(self.stream, stream):
            return
        self.stream = stream
        self._retry_attempt = 0
        self._retry_timer.stop()
        if self.settings is not None and self.settings.video_enabled:
            self._connect_current_stream()

    def reconnect(self) -> None:
        if (self._shutting_down or self.settings is None
                or not self.settings.video_enabled or self.stream is None):
            return
        self._connect_current_stream(reconnecting=True)

    def shutdown(self) -> None:
        if self._shutting_down:
            return
        self._shutting_down = True
        self._retry_timer.stop()
        self._stop_pipeline()

    def closeEvent(self, event) -> None:
        self.shutdown()
        super().closeEvent(event)

    def paintEvent(self, event) -> None:
        painter = QPainter(self)
        painter.fillRect(self.rect(), QColor("black"))
        if self.state is VideoState.LIVE and self._frame is not None:
            target = self._frame.size().scaled(
                self.size(), Qt.AspectRatioMode.KeepAspectRatio)
            x = (self.width() - target.width()) // 2
            y = (self.height() - target.height()) // 2
            painter.drawImage(x, y, self._frame.scaled(
                target,
                Qt.AspectRatioMode.KeepAspectRatio,
                Qt.TransformationMode.FastTransformation,
            ))
            return
        painter.setPen(QColor("white"))
        painter.setFont(QFont("Arial", 20))
        if self.state is VideoState.VIDEO_LOST:
            stream = self.stream.replace("cam_", "").upper() if self.stream else "UNKNOWN"
            text = f"VIDEO LOST — {stream}"
        elif self.state is VideoState.DISABLED:
            text = "VIDEO DISABLED"
        else:
            text = "VIDEO CONNECTING"
        painter.drawText(
            self.rect(),
            Qt.AlignmentFlag.AlignHCenter | Qt.AlignmentFlag.AlignVCenter,
            text,
        )

    def _connect_current_stream(self, reconnecting=False) -> None:
        if self._shutting_down:
            return
        if Gst is None and av is None:
            logger.error("Neither GStreamer nor PyAV is available")
            self._set_lost()
            return
        if not self._stop_pipeline():
            logger.error("Previous portable video worker did not stop in time")
            self._set_lost()
            return
        url = build_stream_url(
            self.settings.video_host, self.settings.video_port, self.stream)
        self._set_state(
            VideoState.RECONNECTING if reconnecting else VideoState.CONNECTING)
        if Gst is None:
            self._start_pyav(url)
            return
        description = (
            "rtspsrc name=source protocols=tcp latency=0 drop-on-latency=true "
            "tcp-timeout=3000000 ! rtph264depay ! h264parse ! "
            "avdec_h264 max-threads=1 ! videoconvert n-threads=1 ! "
            "video/x-raw,format=RGB ! appsink name=sink emit-signals=true "
            "max-buffers=1 drop=true sync=false"
        )
        try:
            self._pipeline = Gst.parse_launch(description)
            self._pipeline.get_by_name("source").set_property("location", url)
            sink = self._pipeline.get_by_name("sink")
            sink.connect("new-sample", self._new_sample)
            self._bus = self._pipeline.get_bus()
            result = self._pipeline.set_state(Gst.State.PLAYING)
            if result == Gst.StateChangeReturn.FAILURE:
                raise RuntimeError("GStreamer rejected PLAYING state")
            self._bus_timer.start()
            logger.info("Native low-latency video connecting to %s", url)
        except Exception:
            logger.exception("Unable to start native video pipeline")
            self._stop_pipeline()
            self._set_lost()

    def _start_pyav(self, url: str) -> None:
        """Start the portable FFmpeg backend used on Windows."""
        logger.info(
            "PyAV backend version=%s libraries=%s",
            getattr(av, "__version__", "unknown"),
            getattr(av, "library_versions", "unknown"),
        )
        stop_event = threading.Event()
        generation = self._video_generation
        self._av_stop = stop_event
        self._av_thread = threading.Thread(
            target=self._run_pyav,
            args=(url, stop_event, generation),
            name=f"nkr-video-{generation}",
            daemon=True,
        )
        self._av_thread.start()
        logger.info("Portable low-latency video connecting to %s", url)

    def _run_pyav(
        self, url: str, stop_event: threading.Event, generation: int,
    ) -> None:
        container = None
        try:
            container = av.open(
                url,
                options={
                    "rtsp_transport": "tcp",
                    "fflags": "nobuffer",
                    "flags": "low_delay",
                    "probesize": "32",
                    "analyzeduration": "0",
                    "stimeout": "3000000",
                    "rw_timeout": "1000000",
                },
                timeout=(3.0, 1.0),
            )
            if stop_event.is_set():
                return
            for frame in container.decode(video=0):
                if stop_event.is_set():
                    break
                rgb = frame.reformat(format="rgb24")
                plane = rgb.planes[0]
                image = QImage(
                    bytes(plane), rgb.width, rgb.height, plane.line_size,
                    QImage.Format.Format_RGB888,
                ).copy()
                self.pyav_frame_ready.emit(generation, image)
            if not stop_event.is_set():
                self.backend_failed.emit(
                    generation, "Portable video stream ended")
        except Exception as exc:
            if not stop_event.is_set():
                logger.exception("Portable video backend failed for %s", url)
                self.backend_failed.emit(
                    generation,
                    f"Portable video error: {type(exc).__name__}: {exc}",
                )
        finally:
            if container is not None:
                container.close()

    def _on_pyav_frame(self, generation: int, image: QImage) -> None:
        if generation != self._video_generation or self._shutting_down:
            return
        self._on_frame(image)

    def _on_backend_failed(self, generation: int, message: str) -> None:
        if generation != self._video_generation or self._shutting_down:
            return
        logger.warning("%s", message)
        self._stop_pipeline()
        self._set_lost()

    def _new_sample(self, sink):
        sample = sink.emit("pull-sample")
        if sample is None:
            return Gst.FlowReturn.ERROR
        buffer = sample.get_buffer()
        caps = sample.get_caps().get_structure(0)
        width = caps.get_value("width")
        height = caps.get_value("height")
        success, mapped = buffer.map(Gst.MapFlags.READ)
        if not success:
            return Gst.FlowReturn.ERROR
        try:
            pixels = bytes(mapped.data)
            stride = len(pixels) // height
            image = QImage(
                pixels, width, height, stride, QImage.Format.Format_RGB888).copy()
        finally:
            buffer.unmap(mapped)
        self.frame_ready.emit(image)
        return Gst.FlowReturn.OK

    def _on_frame(self, image: QImage) -> None:
        self._update_latency(image)
        self._hide_latency_marker(image)
        self._frame = image
        if self.state is not VideoState.LIVE:
            self._retry_attempt = 0
            self._set_state(VideoState.LIVE)
            self._show_popup(f"VIDEO CONNECTED: {self._camera_name()}")
        self.update()

    def _update_latency(self, image: QImage) -> None:
        if image.width() < MARKER_WIDTH or image.height() < MARKER_HEIGHT:
            return
        levels = []
        sample_y = (
            image.height() - MARKER_HEIGHT + 1,
            image.height() - MARKER_HEIGHT // 2,
            image.height() - 2,
        )
        for block in range(MARKER_WIDTH // BLOCK_WIDTH):
            start_x = block * BLOCK_WIDTH
            values = []
            for x in range(start_x, start_x + DATA_WIDTH):
                for y in sample_y:
                    color = image.pixelColor(x, y)
                    values.append(
                        (color.red() + color.green() + color.blue()) / 3,
                    )
            levels.append(sum(values) / len(values))
        synchronized_now_ms = self._synchronized_now_ms()
        latency = calculate_video_latency_ms(levels, synchronized_now_ms)
        if latency is None:
            self._invalid_latency_frames += 1
            if self._invalid_latency_frames >= 15:
                self._latency_samples.clear()
                if self._latency_listener is not None:
                    self._latency_listener(None)
            raw_latency = measure_video_latency_ms(levels, synchronized_now_ms)
            now = time.monotonic()
            if (raw_latency is not None
                    and now - self._last_latency_warning >= 5.0):
                logger.warning(
                    "Rejected video timestamp: signed latency=%d ms",
                    raw_latency,
                )
                self._last_latency_warning = now
            return
        self._invalid_latency_frames = 0
        self._latency_samples.append(latency)
        displayed = round(statistics.median(self._latency_samples))
        if self._latency_listener is not None:
            self._latency_listener(displayed)

    @staticmethod
    def _hide_latency_marker(image: QImage) -> None:
        if image.width() < MARKER_WIDTH or image.height() <= MARKER_HEIGHT:
            return
        replacement = image.copy(
            0, image.height() - MARKER_HEIGHT - 1, MARKER_WIDTH, 1,
        )
        painter = QPainter(image)
        painter.drawImage(
            QRect(0, image.height() - MARKER_HEIGHT, MARKER_WIDTH, MARKER_HEIGHT),
            replacement,
        )
        painter.end()

    def _poll_bus(self) -> None:
        if self._bus is None:
            return
        message = self._bus.pop_filtered(Gst.MessageType.ERROR | Gst.MessageType.EOS)
        if message is None:
            return
        if message.type == Gst.MessageType.ERROR:
            error, debug = message.parse_error()
            logger.warning("Native video error: %s (%s)", error, debug)
        else:
            logger.warning("Native video stream ended")
        self._stop_pipeline()
        self._set_lost()

    def _stop_pipeline(self) -> bool:
        # Invalidate queued frames/errors before stopping native backends.
        self._video_generation += 1
        self._bus_timer.stop()
        stop_event = self._av_stop
        worker = self._av_thread
        if stop_event is not None:
            stop_event.set()
        worker_stopped = True
        if worker is not None and worker is not threading.current_thread():
            worker.join(timeout=4.0)
            worker_stopped = not worker.is_alive()
        if worker_stopped:
            self._av_stop = None
            self._av_thread = None
        pipeline, self._pipeline = self._pipeline, None
        self._bus = None
        if pipeline is not None and Gst is not None:
            pipeline.set_state(Gst.State.NULL)
        self._latency_samples.clear()
        self._invalid_latency_frames = 0
        if self._latency_listener is not None:
            self._latency_listener(None)
        return worker_stopped

    def _set_lost(self) -> None:
        self._set_state(VideoState.VIDEO_LOST)
        self._show_popup(f"VIDEO LOST: {self._camera_name()}")
        if (not self._shutting_down and self.settings is not None
                and self.settings.video_enabled):
            delay = retry_delay(self._retry_attempt)
            self._retry_attempt += 1
            self._retry_timer.start(delay * 1000)

    def _set_state(self, state: VideoState) -> None:
        self.state = state
        if self._state_listener is not None:
            self._state_listener(state)
        self.update()

    def _show_popup(self, text: str) -> None:
        if self._popup is None:
            return
        now = time.monotonic()
        if now - self._last_popup.get(text, float("-inf")) < 5.0:
            return
        self._last_popup[text] = now
        self._popup.show_message(text)

    def _camera_name(self) -> str:
        return self.stream.replace("cam_", "").upper() if self.stream else "UNKNOWN"

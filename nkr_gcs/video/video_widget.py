"""Low-latency native GStreamer video display for the operator GCS."""

from enum import Enum
import logging
import threading
import time

from PySide6.QtCore import QTimer, Qt, Signal
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
    backend_failed = Signal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setStyleSheet("background-color: black;")
        self.settings = None
        self.stream = None
        self.state = VideoState.DISABLED
        self._pipeline = None
        self._bus = None
        self._frame = None
        self._av_container = None
        self._av_stop = threading.Event()
        self._av_thread = None
        self._retry_attempt = 0
        self._popup = None
        self._state_listener = None
        self._last_popup = {}
        self.frame_ready.connect(self._on_frame, Qt.ConnectionType.QueuedConnection)
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

    def set_stream(self, stream: str) -> None:
        if not stream_changed(self.stream, stream):
            return
        self.stream = stream
        self._retry_attempt = 0
        self._retry_timer.stop()
        if self.settings is not None and self.settings.video_enabled:
            self._connect_current_stream()

    def reconnect(self) -> None:
        if self.settings is None or not self.settings.video_enabled or self.stream is None:
            return
        self._connect_current_stream(reconnecting=True)

    def close(self) -> bool:
        self._retry_timer.stop()
        self._stop_pipeline()
        return super().close()

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
        if Gst is None and av is None:
            logger.error("Neither GStreamer nor PyAV is available")
            self._set_lost()
            return
        self._stop_pipeline()
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
        self._av_stop.clear()
        self._av_thread = threading.Thread(
            target=self._run_pyav, args=(url,), name="nkr-video", daemon=True)
        self._av_thread.start()
        logger.info("Portable low-latency video connecting to %s", url)

    def _run_pyav(self, url: str) -> None:
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
                },
            )
            self._av_container = container
            for frame in container.decode(video=0):
                if self._av_stop.is_set():
                    break
                rgb = frame.reformat(format="rgb24")
                plane = rgb.planes[0]
                image = QImage(
                    bytes(plane), rgb.width, rgb.height, plane.line_size,
                    QImage.Format.Format_RGB888,
                ).copy()
                self.frame_ready.emit(image)
            if not self._av_stop.is_set():
                self.backend_failed.emit("Portable video stream ended")
        except Exception as exc:
            if not self._av_stop.is_set():
                self.backend_failed.emit(f"Portable video error: {exc}")
        finally:
            container = self._av_container
            self._av_container = None
            if container is not None:
                container.close()

    def _on_backend_failed(self, message: str) -> None:
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
        self._frame = image
        if self.state is not VideoState.LIVE:
            self._retry_attempt = 0
            self._set_state(VideoState.LIVE)
            self._show_popup(f"VIDEO CONNECTED: {self._camera_name()}")
        self.update()

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

    def _stop_pipeline(self) -> None:
        self._bus_timer.stop()
        self._av_stop.set()
        container, self._av_container = self._av_container, None
        if container is not None:
            container.close()
        pipeline, self._pipeline = self._pipeline, None
        self._bus = None
        if pipeline is not None and Gst is not None:
            pipeline.set_state(Gst.State.NULL)

    def _set_lost(self) -> None:
        self._set_state(VideoState.VIDEO_LOST)
        self._show_popup(f"VIDEO LOST: {self._camera_name()}")
        if self.settings is not None and self.settings.video_enabled:
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

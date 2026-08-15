"""Low-latency native GStreamer video display for the operator GCS."""

from collections import deque
from enum import Enum
import logging
import os
import statistics
import subprocess
import threading
import time
from pathlib import Path

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
from .gstreamer_process import (
    build_gstreamer_command,
    find_gst_launch,
    gstreamer_environment,
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

    latest_frame_ready = Signal(int)
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
        self._gst_process = None
        self._gst_process_stop = None
        self._gst_process_thread = None
        self._active_backend = None
        self._current_url = None
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
        self._latest_frame_lock = threading.Lock()
        self._latest_frame = None
        self._latest_notification_pending = False
        self.latest_frame_ready.connect(
            self._on_latest_frame, Qt.ConnectionType.QueuedConnection)
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
            painter.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform, True)
            painter.drawImage(QRect(x, y, target.width(), target.height()), self._frame)
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
        gst_launch = find_gst_launch() if Gst is None else None
        if Gst is None and gst_launch is None and av is None:
            logger.error("Neither GStreamer nor PyAV is available")
            self._set_lost()
            return
        if not self._stop_pipeline():
            logger.error("Previous portable video worker did not stop in time")
            self._set_lost()
            return
        url = build_stream_url(
            self.settings.video_host, self.settings.video_port, self.stream)
        self._current_url = url
        self._set_state(
            VideoState.RECONNECTING if reconnecting else VideoState.CONNECTING)
        if Gst is None and gst_launch is not None:
            self._start_gstreamer_process(url, gst_launch)
            return
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
            self._active_backend = "gstreamer-native"
            self._pipeline.get_by_name("source").set_property("location", url)
            sink = self._pipeline.get_by_name("sink")
            sink.connect("new-sample", self._new_sample, self._video_generation)
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

    def _start_gstreamer_process(self, url: str, executable: Path) -> None:
        """Start the bundled GStreamer runtime without requiring PyGObject."""
        command = build_gstreamer_command(
            executable, url, self.settings.video_width, self.settings.video_height,
        )
        environment = gstreamer_environment(executable)
        creationflags = (
            getattr(subprocess, "CREATE_NO_WINDOW", 0)
            if os.name == "nt" else 0
        )
        try:
            process = subprocess.Popen(
                command,
                stdin=subprocess.DEVNULL,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                bufsize=0,
                env=environment,
                creationflags=creationflags,
            )
        except OSError:
            logger.exception("Unable to start bundled GStreamer")
            self._start_pyav(url)
            return
        stop_event = threading.Event()
        generation = self._video_generation
        self._gst_process = process
        self._gst_process_stop = stop_event
        self._active_backend = "gstreamer-process"
        self._gst_process_thread = threading.Thread(
            target=self._run_gstreamer_process,
            args=(process, stop_event, generation),
            name=f"nkr-gstreamer-{generation}",
            daemon=True,
        )
        self._gst_process_thread.start()
        logger.info(
            "Bundled GStreamer connecting to %s at %dx%d",
            url, self.settings.video_width, self.settings.video_height,
        )

    def _run_gstreamer_process(
        self, process, stop_event: threading.Event, generation: int,
    ) -> None:
        width = self.settings.video_width
        height = self.settings.video_height
        frame_size = width * height * 3
        failure = None
        stderr_chunks = deque(maxlen=64)
        stderr_worker = threading.Thread(
            target=self._drain_pipe,
            args=(process.stderr, stderr_chunks),
            name=f"nkr-gstreamer-errors-{generation}",
            daemon=True,
        )
        stderr_worker.start()
        try:
            while not stop_event.is_set():
                pixels = self._read_exact(process.stdout, frame_size, stop_event)
                if pixels is None:
                    break
                image = QImage(
                    pixels, width, height, width * 3,
                    QImage.Format.Format_RGB888,
                ).copy()
                self._publish_latest_frame(generation, image)
        except Exception as exc:
            failure = f"Bundled GStreamer read error: {type(exc).__name__}: {exc}"
        finally:
            if process.poll() is None and not stop_event.is_set():
                try:
                    process.wait(timeout=2.0)
                except subprocess.TimeoutExpired:
                    failure = failure or "Bundled GStreamer did not exit after EOF"
                    process.terminate()
                    try:
                        process.wait(timeout=1.0)
                    except subprocess.TimeoutExpired:
                        process.kill()
                        process.wait(timeout=1.0)
            stderr_worker.join(timeout=1.0)
            if not stop_event.is_set():
                stderr = b"".join(stderr_chunks)
                detail = stderr.decode("utf-8", errors="replace").strip()[-1000:]
                message = failure or "Bundled GStreamer stream ended"
                if detail:
                    message = f"{message}: {detail}"
                self.backend_failed.emit(generation, message)

    @staticmethod
    def _read_exact(pipe, size: int, stop_event: threading.Event):
        data = bytearray(size)
        view = memoryview(data)
        position = 0
        while position < size and not stop_event.is_set():
            count = pipe.readinto(view[position:])
            if not count:
                return None
            position += count
        return bytes(data) if position == size else None

    @staticmethod
    def _drain_pipe(pipe, chunks) -> None:
        """Keep bounded subprocess diagnostics without blocking video output."""
        if pipe is None:
            return
        try:
            while True:
                chunk = pipe.read(4096)
                if not chunk:
                    return
                chunks.append(chunk)
        except OSError:
            return

    def _start_pyav(self, url: str) -> None:
        """Start the portable FFmpeg fallback backend."""
        if av is None:
            logger.error("PyAV fallback is unavailable")
            self._set_lost()
            return
        logger.info(
            "PyAV backend version=%s libraries=%s",
            getattr(av, "__version__", "unknown"),
            getattr(av, "library_versions", "unknown"),
        )
        stop_event = threading.Event()
        generation = self._video_generation
        self._av_stop = stop_event
        self._active_backend = "pyav"
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
                self._publish_latest_frame(generation, image)
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

    def _publish_latest_frame(self, generation: int, image: QImage) -> None:
        """Replace an undrawn frame so the Qt event queue cannot add latency."""
        should_notify = False
        with self._latest_frame_lock:
            self._latest_frame = (generation, image)
            if not self._latest_notification_pending:
                self._latest_notification_pending = True
                should_notify = True
        if should_notify:
            self.latest_frame_ready.emit(generation)

    def _on_latest_frame(self, _generation: int) -> None:
        with self._latest_frame_lock:
            frame = self._latest_frame
            self._latest_frame = None
            self._latest_notification_pending = False
        if frame is None:
            return
        generation, image = frame
        if generation != self._video_generation or self._shutting_down:
            return
        self._on_frame(image)

    def _on_backend_failed(self, generation: int, message: str) -> None:
        if generation != self._video_generation or self._shutting_down:
            return
        logger.warning("%s", message)
        failed_backend = self._active_backend
        url = self._current_url
        self._stop_pipeline()
        if failed_backend == "gstreamer-process" and url is not None and av is not None:
            logger.warning("Bundled GStreamer failed; falling back to PyAV")
            self._set_state(VideoState.RECONNECTING)
            self._current_url = url
            self._start_pyav(url)
            return
        self._set_lost()

    def _new_sample(self, sink, generation: int):
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
        self._publish_latest_frame(generation, image)
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
        process_stop = self._gst_process_stop
        process_worker = self._gst_process_thread
        process = self._gst_process
        if process_stop is not None:
            process_stop.set()
        if process is not None and process.poll() is None:
            process.terminate()
            try:
                process.wait(timeout=2.0)
            except subprocess.TimeoutExpired:
                process.kill()
                process.wait(timeout=1.0)
        process_stopped = process is None or process.poll() is not None
        if (process_worker is not None
                and process_worker is not threading.current_thread()):
            process_worker.join(timeout=2.0)
            process_stopped = process_stopped and not process_worker.is_alive()
        if process_stopped:
            self._gst_process = None
            self._gst_process_stop = None
            self._gst_process_thread = None
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
        self._active_backend = None
        with self._latest_frame_lock:
            self._latest_frame = None
            self._latest_notification_pending = False
        if self._latency_listener is not None:
            self._latency_listener(None)
        return process_stopped and worker_stopped

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

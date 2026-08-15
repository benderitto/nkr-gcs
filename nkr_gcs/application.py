from PySide6.QtCore import QObject, QTimer
import logging
import time

from .model.operator_model import OperatorModel
from .input.input_manager import InputManager
from .network.network_manager import NetworkManager
from .robot_state_notifier import RobotStateNotifier
from .video.camera_controller import CameraController
from .settings import load_settings, save_setting
from .presentation_controller import PresentationController
from .osd_menu_controller import OSDMenuController
from .time_sync import NetworkTimeSynchronizer

logger = logging.getLogger(__name__)


class Application(QObject):

    def __init__(self, window):

        super().__init__()

        self.window = window
        self.settings = load_settings()
        logger.info(
            "Configuration loaded: robot=%s:%d video=%s:%d/%s input=%s",
            self.settings.robot_host, self.settings.robot_port,
            self.settings.video_host, self.settings.video_port,
            self.settings.video_default_stream, self.settings.input_device,
        )

        self.operator = OperatorModel()

        self.input = InputManager(input_device=self.settings.input_device)
        self.network = NetworkManager(settings=self.settings, robot=self.window.robot)
        self.time_sync = NetworkTimeSynchronizer()
        self.time_sync.start()
        self.robot_notifier = RobotStateNotifier(self.window.popup, self.window.robot)
        self.window.video.set_popup(self.window.popup)
        self.window.video.set_state_listener(
            lambda state: setattr(self.window.robot, "video_state", state.value),
        )
        self.window.video.set_latency_listener(
            lambda latency: setattr(self.window.robot, "latency_ms", latency),
        )
        self.window.video.set_synchronized_time_source(self.time_sync.now_ms)
        self.window.video.configure(self.settings)
        self.camera = CameraController(
            self.window.video, self.window.popup, self.window.robot,
        )
        self.window.osd_menu.set_callbacks(
            drive=self._select_drive_mode,
            camera=self.camera.select_stream,
            language=self.window.osd_menu.set_language,
            input_device=self._select_input_device,
        )
        self.presentation = PresentationController(self.window)
        self.osd_menu = OSDMenuController(self.window.osd_menu, self.presentation)

        #
        # Main loop (100 Hz)
        #

        self.timer = QTimer()
        self._last_stage_error = {}
        self._first_update = True

        self.timer.timeout.connect(self.update)

        self.timer.start(10)  # GUI cadence; network itself sends at 50 Hz.

    def update(self):
        if self._first_update:
            logger.info("Main update loop started")
            self._first_update = False

        input_ok = self._run_stage("controller input", self.input.read_controller)
        if not input_ok:
            # Never keep an old actuator command after an input failure.
            self.input.suppress_operator(self.operator)

        self._run_stage(
            "local presentation",
            lambda: self.presentation.update(self.input.controller),
        )
        self._run_stage(
            "OSD menu",
            lambda: self.osd_menu.update(self.input.controller),
        )

        if input_ok:
            if self.window.osd_menu.is_open:
                self.input.suppress_operator(self.operator)
            else:
                if self._run_stage(
                    "operator mapping",
                    lambda: self.input.map_operator(self.operator),
                ):
                    self._run_stage(
                        "camera controls",
                        lambda: self.camera.update(self.input.controller),
                    )

        robot_updated = [False]
        self._run_stage(
            "UDP network",
            lambda: robot_updated.__setitem__(
                0, self.network.update(self.operator),
            ),
        )
        if robot_updated[0]:
            # Runs from the Qt timer, so popup work remains on the GUI thread.
            self._run_stage(
                "robot state notification",
                lambda: self.robot_notifier.update(self.window.robot),
            )

        self._run_stage("GUI refresh", lambda: self.window.refresh(self.operator))

    def _run_stage(self, name, callback) -> bool:
        """Keep independent control stages alive and persist their tracebacks."""
        try:
            callback()
            return True
        except Exception:
            now = time.monotonic()
            if now - self._last_stage_error.get(name, float("-inf")) >= 5.0:
                logger.exception("Main-loop stage failed: %s", name)
                self._last_stage_error[name] = now
            return False

    def close(self):
        self.timer.stop()
        self.network.close()
        self.time_sync.stop()
        self.window.video.close()

    def _select_drive_mode(self, mode: int):
        self.input.select_drive_mode(mode)
        self.operator.requested_drive_mode = mode
        logger.info("Operator requested_drive_mode=%d", mode)

    def _select_input_device(self, input_device: str):
        self.input.select_input_device(input_device)
        save_setting("input_device", input_device)
        self.window.popup.show_message(f"INPUT: {input_device.upper()}")

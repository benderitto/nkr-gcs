from PySide6.QtCore import QObject, QTimer
import logging

from .model.operator_model import OperatorModel
from .input.input_manager import InputManager
from .network.network_manager import NetworkManager
from .robot_state_notifier import RobotStateNotifier
from .video.camera_controller import CameraController
from .settings import load_settings, save_setting
from .presentation_controller import PresentationController
from .osd_menu_controller import OSDMenuController

logger = logging.getLogger(__name__)


class Application(QObject):

    def __init__(self, window):

        super().__init__()

        self.window = window
        self.settings = load_settings()

        self.operator = OperatorModel()

        self.input = InputManager(input_device=self.settings.input_device)
        self.network = NetworkManager(settings=self.settings, robot=self.window.robot)
        self.robot_notifier = RobotStateNotifier(self.window.popup, self.window.robot)
        self.window.video.set_popup(self.window.popup)
        self.window.video.set_state_listener(
            lambda state: setattr(self.window.robot, "video_state", state.value),
        )
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

        self.timer.timeout.connect(self.update)

        self.timer.start(10)  # GUI cadence; network itself sends at 50 Hz.

    def update(self):

        #
        # Read controller
        #

        self.input.read_controller()
        self.presentation.update(self.input.controller)
        self.osd_menu.update(self.input.controller)

        if self.window.osd_menu.is_open:
            self.input.suppress_operator(self.operator)
        else:
            self.input.map_operator(self.operator)
            self.camera.update(self.input.controller)

        if self.network.update(self.operator):
            # Runs from the Qt timer, so popup work remains on the GUI thread.
            self.robot_notifier.update(self.window.robot)

        #
        # Update GUI
        #

        self.window.refresh(self.operator)

    def close(self):
        self.timer.stop()
        self.network.close()
        self.window.video.close()

    def _select_drive_mode(self, mode: int):
        self.input.select_drive_mode(mode)
        self.operator.requested_drive_mode = mode
        logger.info("Operator requested_drive_mode=%d", mode)

    def _select_input_device(self, input_device: str):
        self.input.select_input_device(input_device)
        save_setting("input_device", input_device)
        self.window.popup.show_message(f"INPUT: {input_device.upper()}")

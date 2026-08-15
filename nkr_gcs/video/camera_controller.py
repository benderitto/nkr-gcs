"""Local Steam Deck camera selection, independent of the UDP control loop."""

CAMERA_STREAMS = ("cam_front", "cam_rear", "cam_night", "cam_thermal")
CAMERA_NAMES = {
    "cam_front": "FRONT",
    "cam_rear": "REAR",
    "cam_night": "NIGHT",
    "cam_thermal": "THERMAL",
}


class CameraController:
    """Owns persistent selection and temporary rear-camera hold override."""

    def __init__(self, video_widget, popup, robot, streams=CAMERA_STREAMS):
        self.video_widget = video_widget
        self.popup = popup
        self.robot = robot
        self.streams = tuple(streams)
        self.selected_stream = self.streams[0]
        self.displayed_stream = None
        self._y_pressed = False
        self._rear_hold = False
        self._set_displayed(self.selected_stream)

    def update(self, controller) -> None:
        """Handle only controller edges; safe to call at the 100 Hz GUI rate."""
        if controller.y and not self._y_pressed:
            self._select_next()
        self._y_pressed = controller.y

        if controller.dpad_left and not self._rear_hold:
            self._rear_hold = True
            if self._set_displayed("cam_rear", hold=True):
                self.popup.show_message("REAR CAMERA [HOLD]")
        elif not controller.dpad_left and self._rear_hold:
            self._rear_hold = False
            if self._set_displayed(self.selected_stream):
                self.popup.show_message(
                    f"CAMERA RESTORED: {CAMERA_NAMES[self.selected_stream]}",
                )

    def _select_next(self) -> None:
        index = self.streams.index(self.selected_stream)
        self.selected_stream = self.streams[(index + 1) % len(self.streams)]
        if not self._rear_hold:
            self._set_displayed(self.selected_stream)
        self.popup.show_message(
            f"CAMERA SELECTED: {CAMERA_NAMES[self.selected_stream]}",
        )

    def select_stream(self, stream: str) -> None:
        if stream not in self.streams:
            raise ValueError(f"Unknown camera stream: {stream}")
        if stream == self.selected_stream:
            return
        self.selected_stream = stream
        if not self._rear_hold:
            self._set_displayed(stream)
        self.popup.show_message(f"CAMERA SELECTED: {CAMERA_NAMES[stream]}")

    def _set_displayed(self, stream: str, hold: bool = False) -> bool:
        if stream == self.displayed_stream:
            # Avoid needless video reconnects and matching duplicate popups.
            self._set_hud_camera(stream, hold)
            return False
        self.displayed_stream = stream
        self.video_widget.set_stream(stream)
        self._set_hud_camera(stream, hold)
        return True

    def _set_hud_camera(self, stream: str, hold: bool) -> None:
        label = CAMERA_NAMES[stream]
        self.robot.camera = f"{label} [HOLD]" if hold else label

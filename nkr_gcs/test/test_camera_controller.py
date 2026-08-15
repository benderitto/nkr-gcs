from nkr_gcs.input.controller import ControllerState
from nkr_gcs.model.robot_model import RobotModel
from nkr_gcs.video.camera_controller import CameraController


class Video:
    def __init__(self):
        self.streams = []

    def set_stream(self, stream):
        self.streams.append(stream)


class Popup:
    def __init__(self):
        self.messages = []

    def show_message(self, text, timeout_ms=1500):
        self.messages.append((text, timeout_ms))


def camera():
    video, popup, robot = Video(), Popup(), RobotModel()
    return CameraController(video, popup, robot), video, popup, robot


def test_y_cycles_selected_camera_on_press_edges_only():
    controller, video, popup, robot = camera()
    assert (controller.selected_stream, controller.displayed_stream) == (
        "cam_front", "cam_front",
    )
    controller.update(ControllerState(y=True))
    assert (controller.selected_stream, controller.displayed_stream, robot.camera) == (
        "cam_rear", "cam_rear", "REAR",
    )
    controller.update(ControllerState(y=True))
    assert video.streams == ["cam_front", "cam_rear"]
    controller.update(ControllerState())
    controller.update(ControllerState(y=True))
    assert controller.selected_stream == "cam_night"
    assert popup.messages[-1][0] == "CAMERA SELECTED: NIGHT"


def test_rear_hold_restores_selected_camera_without_repeat_switches():
    controller, video, popup, robot = camera()
    controller.update(ControllerState(dpad_left=True))
    assert (controller.displayed_stream, robot.camera) == ("cam_rear", "REAR [HOLD]")
    controller.update(ControllerState(dpad_left=True))
    assert video.streams == ["cam_front", "cam_rear"]
    controller.update(ControllerState())
    assert controller.displayed_stream == "cam_front"
    assert popup.messages[-1][0] == "CAMERA RESTORED: FRONT"


def test_y_during_rear_hold_changes_selection_but_not_display():
    controller, video, popup, robot = camera()
    controller.update(ControllerState(dpad_left=True))
    controller.update(ControllerState(y=True, dpad_left=True))
    assert (controller.selected_stream, controller.displayed_stream, robot.camera) == (
        "cam_rear", "cam_rear", "REAR [HOLD]",
    )
    controller.update(ControllerState(dpad_left=True))
    controller.update(ControllerState())
    assert video.streams == ["cam_front", "cam_rear"]
    assert not any("RESTORED" in message[0] for message in popup.messages)


def test_hold_on_selected_rear_has_no_popup_or_reconnect():
    controller, video, popup, _robot = camera()
    controller.update(ControllerState(y=True))  # selected rear
    baseline_streams = list(video.streams)
    baseline_messages = list(popup.messages)
    controller.update(ControllerState(dpad_left=True))
    controller.update(ControllerState())
    assert video.streams == baseline_streams
    assert popup.messages == baseline_messages


def test_setting_the_same_stream_does_not_reconnect_video():
    controller, video, _popup, _robot = camera()
    controller._set_displayed("cam_front")
    assert video.streams == ["cam_front"]


def test_menu_can_select_specific_camera_stream():
    controller, video, popup, robot = camera()
    controller.select_stream("cam_thermal")
    assert (controller.selected_stream, controller.displayed_stream, robot.camera) == (
        "cam_thermal", "cam_thermal", "THERMAL",
    )
    assert popup.messages[-1][0] == "CAMERA SELECTED: THERMAL"

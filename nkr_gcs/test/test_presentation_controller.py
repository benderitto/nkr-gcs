from nkr_gcs.input.controller import ControllerState
from nkr_gcs.presentation_controller import PresentationController


class Window:
    def __init__(self):
        self.events = []

    def enter_kiosk_mode(self):
        self.events.append("kiosk")

    def enter_desktop_mode(self):
        self.events.append("desktop")


def test_view_button_toggles_kiosk_on_edges_only():
    window = Window()
    controller = PresentationController(window)
    assert window.events == ["kiosk"]
    controller.update(ControllerState(back=True))
    assert window.events == ["kiosk", "desktop"]
    controller.update(ControllerState(back=True))
    assert window.events == ["kiosk", "desktop"]
    controller.update(ControllerState())
    controller.update(ControllerState(back=True))
    assert window.events == ["kiosk", "desktop", "kiosk"]

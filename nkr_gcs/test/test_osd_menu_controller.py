from nkr_gcs.input.controller import ControllerState
from nkr_gcs.osd_menu_controller import OSDMenuController


class Presentation:
    def __init__(self, kiosk_active=True):
        self.kiosk_active = kiosk_active


class Menu:
    def __init__(self):
        self.is_open = False
        self.toggles = 0
        self.navigation = []
        self.activated = 0
        self.adjustments = []

    def toggle(self, source="local"):
        self.is_open = not self.is_open
        self.toggles += 1

    def set_open(self, value):
        self.is_open = value

    def navigate(self, delta):
        self.navigation.append(delta)

    def adjust(self, direction):
        self.adjustments.append(direction)

    def activate(self):
        self.activated += 1

    def back(self):
        self.is_open = False


def test_r4_opens_menu_only_in_kiosk_on_press_edge():
    menu, presentation = Menu(), Presentation()
    control = OSDMenuController(menu, presentation)
    control.update(ControllerState(r4=True))
    control.update(ControllerState(r4=True))
    assert menu.is_open and menu.toggles == 1
    control.update(ControllerState())
    control.update(ControllerState(r4=True))
    assert not menu.is_open and menu.toggles == 2


def test_menu_closes_and_r4_is_ignored_outside_kiosk():
    menu, presentation = Menu(), Presentation(False)
    menu.is_open = True
    OSDMenuController(menu, presentation).update(ControllerState(r4=True))
    assert not menu.is_open and menu.toggles == 0


def test_open_menu_consumes_dpad_a_and_b_on_edges():
    menu, presentation = Menu(), Presentation()
    menu.is_open = True
    control = OSDMenuController(menu, presentation)
    control.update(ControllerState(dpad_down=True, dpad_right=True, a=True))
    control.update(ControllerState(dpad_down=True, dpad_right=True, a=True))
    assert menu.navigation == [1]
    assert menu.adjustments == [1]
    assert menu.activated == 1
    control.update(ControllerState())
    control.update(ControllerState(b=True))
    assert not menu.is_open

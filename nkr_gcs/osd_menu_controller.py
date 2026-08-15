"""R4-button edge handling for the local OSD menu."""

import logging


logger = logging.getLogger(__name__)


class OSDMenuController:
    def __init__(self, menu, presentation):
        self.menu = menu
        self.presentation = presentation
        self._r4_pressed = False
        self._pressed = {}

    def update(self, controller) -> None:
        if controller.r4 and not self._r4_pressed and self.presentation.kiosk_active:
            logger.info("OSD menu R4 toggle: open=%s", not self.menu.is_open)
            self.menu.toggle(source="r4")
        self._r4_pressed = controller.r4
        if not self.presentation.kiosk_active and self.menu.is_open:
            self.menu.set_open(False)
        if not self.menu.is_open:
            self._remember(controller)
            return
        if self._edge("dpad_up", controller.dpad_up):
            self.menu.navigate(-1)
        if self._edge("dpad_down", controller.dpad_down):
            self.menu.navigate(1)
        if self._edge("dpad_left", controller.dpad_left):
            self.menu.adjust(-1)
        if self._edge("dpad_right", controller.dpad_right):
            self.menu.adjust(1)
        if self._edge("a", controller.a):
            self.menu.activate()
        if self._edge("b", controller.b):
            self.menu.back()

    def _edge(self, name, pressed):
        previous = self._pressed.get(name, False)
        self._pressed[name] = pressed
        return pressed and not previous

    def _remember(self, controller):
        for name in ("dpad_up", "dpad_down", "dpad_left", "dpad_right", "a", "b"):
            self._pressed[name] = getattr(controller, name)

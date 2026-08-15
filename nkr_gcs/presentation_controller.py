"""Toggle GCS kiosk presentation from the Steam Deck View button."""


class PresentationController:
    """Edge-triggered local window mode; independent of SDL/UDP internals."""

    def __init__(self, window):
        self.window = window
        self.kiosk_active = True
        self._view_pressed = False
        self.window.enter_kiosk_mode()

    def update(self, controller) -> None:
        if controller.back and not self._view_pressed:
            self.kiosk_active = not self.kiosk_active
            if self.kiosk_active:
                self.window.enter_kiosk_mode()
            else:
                self.window.enter_desktop_mode()
        self._view_pressed = controller.back

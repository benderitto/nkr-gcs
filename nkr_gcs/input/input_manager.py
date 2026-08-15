from ..model.operator_model import OperatorModel

import logging

from .controller import ControllerState
from .mapping import InputMapping
from .sdl_driver import SDLDriver

logger = logging.getLogger(__name__)


class InputManager:

    def __init__(self, input_device=InputMapping.STEAMDECK):

        self.controller = ControllerState()

        self.mapping = InputMapping(input_device=input_device)

        self.driver = SDLDriver()

        self._suppress_until_released = False

        self.driver.initialize()

    def update(
        self,
        operator: OperatorModel,
    ):

        self.read_controller()
        self.map_operator(operator)

    def read_controller(self):
        self.driver.update(self.controller)

    def map_operator(self, operator: OperatorModel):
        if self._suppress_until_released:
            if not self._is_neutral():
                self.suppress_operator(operator)
                return
            self._suppress_until_released = False
            logger.info("Menu input released; operator mapping resumed")
        self.mapping.update(self.controller, operator)

    def suppress_operator(self, operator: OperatorModel):
        """Keep menu input local; NetworkManager receives a neutral command."""
        self._suppress_until_released = True
        operator.throttle = 0.0
        operator.steering = 0.0
        operator.brake = 0.0
        operator.requested_drive_mode = 0
        operator.buttons = 0
        operator.buttons_changed = 0

    def select_drive_mode(self, mode: int) -> None:
        self.mapping.mode_selector.set_mode(mode)
        logger.info("Menu selected drive mode=%d", mode)

    def select_input_device(self, input_device: str) -> None:
        self.mapping.set_input_device(input_device)

    def _is_neutral(self) -> bool:
        """Whether menu buttons were released.

        This gate deliberately does not include sticks or triggers.  Steam
        Deck analogue controls can have a small centre drift, and requiring
        their mathematical zero leaves the GCS permanently in the safe-menu
        state after a menu action.  Buttons still have to be released so a
        held menu key cannot leak into the robot command stream.
        """
        c = self.controller
        buttons = (c.a, c.b, c.x, c.y, c.l1, c.r1, c.r4,
                   c.left_stick, c.right_stick, c.back, c.start, c.guide,
                   c.misc1, c.dpad_up, c.dpad_down, c.dpad_left, c.dpad_right)
        return not any(buttons)

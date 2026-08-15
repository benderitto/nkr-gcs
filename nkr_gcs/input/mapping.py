from ..model.operator_model import OperatorModel

import logging

from .controller import ControllerState
from .mode_selector import ModeSelector
from nkr_protocol.constants import (
    BUTTON_A, BUTTON_B, BUTTON_X, BUTTON_Y, BUTTON_L1, BUTTON_R1,
    BUTTON_VIEW, BUTTON_MENU, BUTTON_STEAM,
)

logger = logging.getLogger(__name__)


class InputMapping:
    """
    Converts controller state
    into operator commands.
    """

    def __init__(self):

        self.mode_selector = ModeSelector()
        self._last_logged_mode = None

    def update(
        self,
        controller: ControllerState,
        operator: OperatorModel,
    ):
        #
        # Driving
        #

        operator.throttle = self._clamp(
            controller.right_trigger -
            controller.left_trigger
        )
        
        #
        # Brake
        #

        operator.brake = self._clamp(1.0 if controller.l1 else 0.0)

        #
        # Steering
        #

        operator.steering = self._clamp(controller.left_x)

        #
        # Drive mode
        #

        operator.requested_drive_mode = (
            self.mode_selector.update(
                controller.dpad_up
            )
        )
        if operator.requested_drive_mode != self._last_logged_mode:
            logger.info("Input requested_drive_mode=%d", operator.requested_drive_mode)
            self._last_logged_mode = operator.requested_drive_mode

        buttons = self._buttons(controller)
        # This preserves input-frame edges for local consumers.  NetworkManager
        # separately computes the edge against the last *sent* packet, because
        # input is 100 Hz while UDP control is 50 Hz.
        previous_buttons = operator.buttons
        operator.buttons_changed = buttons ^ previous_buttons
        operator.buttons = buttons
        if operator.buttons_changed:
            # One record per press/release edge, never one per input frame.
            logger.info("NKR input: buttons=0x%04X changed=0x%04X",
                        operator.buttons, operator.buttons_changed)

    @staticmethod
    def _clamp(value: float) -> float:
        return max(-1.0, min(1.0, value))

    @staticmethod
    def _buttons(controller: ControllerState) -> int:
        buttons = 0

        # Steam Deck system buttons.  These explicit assignments are kept
        # separate from the generic controller buttons because Gateway safety
        # consumes these masks directly.
        if controller.back or controller.misc1:  # "..." / View
            buttons |= BUTTON_VIEW
        if controller.start:      # "☰" / Menu
            buttons |= BUTTON_MENU
        if controller.guide:      # Steam button
            buttons |= BUTTON_STEAM

        for pressed, mask in (
            (controller.a, BUTTON_A), (controller.b, BUTTON_B),
            (controller.x, BUTTON_X), (controller.y, BUTTON_Y),
            (controller.l1, BUTTON_L1), (controller.r1, BUTTON_R1),
        ):
            if pressed:
                buttons |= mask
        return buttons

from ..model.operator_model import OperatorModel

import logging
import time

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

    STEAMDECK = "steamdeck"
    XBOX = "xbox"
    DUALSENSE = "dualsense"
    INPUT_DEVICES = (STEAMDECK, XBOX, DUALSENSE)

    def __init__(self, input_device=STEAMDECK, clock=time.monotonic):

        self.mode_selector = ModeSelector()
        self._last_logged_mode = None
        self._clock = clock
        self._input_device = self.STEAMDECK
        self._safety_pressed_at = None
        self._arm_sent = False
        self._disarm_until = 0.0
        self.set_input_device(input_device)

    @property
    def input_device(self):
        return self._input_device

    def set_input_device(self, input_device):
        if input_device not in self.INPUT_DEVICES:
            raise ValueError(f"Unsupported input device: {input_device}")
        self._input_device = input_device
        self._safety_pressed_at = None
        self._arm_sent = False
        self._disarm_until = 0.0
        logger.info("Input profile selected: %s", input_device)

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

    def _buttons(self, controller: ControllerState) -> int:
        buttons = 0

        # Steam Deck system buttons.  These explicit assignments are kept
        # separate from the generic controller buttons because Gateway safety
        # consumes these masks directly.
        if self._input_device == self.STEAMDECK:
            if controller.back or controller.misc1:  # "..." / View
                buttons |= BUTTON_VIEW
            if controller.start:      # "☰" / Menu
                buttons |= BUTTON_MENU
        else:
            buttons |= self._combined_arm_disarm(controller.start)
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

    def _combined_arm_disarm(self, pressed: bool) -> int:
        """Hold Menu/Options for 2 s to arm; tap it to disarm."""
        now = self._clock()
        if pressed:
            if self._safety_pressed_at is None:
                self._safety_pressed_at = now
                self._arm_sent = False
            if now - self._safety_pressed_at >= 2.0:
                self._arm_sent = True
                return BUTTON_MENU
            return 0
        if self._safety_pressed_at is not None:
            if not self._arm_sent:
                # Keep the synthetic press long enough for the 50 Hz network
                # loop to observe it even though input is sampled at 100 Hz.
                self._disarm_until = now + 0.1
            self._safety_pressed_at = None
            self._arm_sent = False
        if now < self._disarm_until:
            return BUTTON_VIEW
        return 0

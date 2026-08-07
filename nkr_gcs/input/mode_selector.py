"""
Drive mode selector.
"""

from nkr_protocol.nkr_protocol.constants import (
    MODE_FRONT_STEER,
    MODE_TANK,
    MODE_CRAB,
    MODE_FRONT_DRIVE,
    MODE_REAR_DRIVE,
)


class ModeSelector:

    def __init__(self):

        self.modes = [

            MODE_FRONT_STEER,
            MODE_TANK,
            MODE_CRAB,
            MODE_FRONT_DRIVE,
            MODE_REAR_DRIVE,

        ]

        self.index = 0

        self.last_button = False

    @property
    def current_mode(self):

        return self.modes[self.index]

    def update(
        self,
        button_pressed: bool,
    ) -> int:

        #
        # Rising edge
        #

        if button_pressed and not self.last_button:

            self.index += 1

            if self.index >= len(self.modes):
                self.index = 0

        self.last_button = button_pressed

        return self.current_mode
from dataclasses import dataclass

from nkr_protocol.constants import LIGHT_DARK


@dataclass
class OperatorModel:

    #
    # Motion
    #

    throttle: float = 0.0
    steering: float = 0.0
    brake: float = 0.0

    #
    # Requested vehicle state
    #

    requested_drive_mode: int = 0

    requested_camera: int = 0

    requested_light_mode: int = LIGHT_DARK

    #
    # Buttons
    #

    buttons: int = 0
    buttons_changed: int = 0

    #
    # Link
    #

    connected: bool = False

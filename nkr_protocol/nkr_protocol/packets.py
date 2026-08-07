from dataclasses import dataclass


@dataclass
class ControlPacket:

    sequence: int = 0

    throttle: int = 0

    steering: int = 0

    brake: int = 0

    requested_mode: int = 0

    buttons: int = 0

    buttons_changed: int = 0
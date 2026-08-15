from dataclasses import dataclass


@dataclass
class ControlPacket:

    session_id: int = 0

    sequence: int = 0

    throttle: int = 0

    steering: int = 0

    brake: int = 0

    requested_mode: int = 0

    buttons: int = 0

    buttons_changed: int = 0


@dataclass
class SessionPacket:
    """A decoded session challenge or response packet."""

    packet_type: int
    session_id: int
    challenge: int


@dataclass
class RobotStatePacket:
    session_id: int = 0
    active_mode: int = 0
    flags: int = 0

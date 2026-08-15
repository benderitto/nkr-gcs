from dataclasses import dataclass

from nkr_protocol.constants import MODE_FRONT_STEER

MODE_NAMES = {
    1: "FRONT STEER",
    2: "TANK",
    3: "CRAB",
    4: "FRONT DRIVE",
    5: "REAR DRIVE",
}


@dataclass
class RobotModel:

    #
    # Motion
    #

    speed: float = 0.0              # km/h

    heading: float = 0.0            # degrees

    drive_mode: str = "FRONT STEER"
    active_mode: int = MODE_FRONT_STEER
    armed: bool = False
    estop: bool = False

    #
    # Cameras
    #

    camera: str = "MAIN"
    video_state: str = "DISABLED"

    #
    # Lights
    #

    light_mode: str = "DRK"

    #
    # Battery
    #

    battery_percent: int = 100

    battery_voltage: float = 24.0

    #
    # GPS
    #

    satellites: int = 0

    latitude: float = 0.0

    longitude: float = 0.0

    #
    # Link
    #

    link_type: str = "LTE"

    bitrate_mbps: float = 0.0

    packet_quality: int = 100

    latency_ms: int | None = None

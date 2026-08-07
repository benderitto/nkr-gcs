from dataclasses import dataclass


@dataclass
class RobotModel:

    #
    # Motion
    #

    speed: float = 0.0              # km/h

    heading: float = 0.0            # degrees

    drive_mode: str = "FRONT_STEER"

    #
    # Cameras
    #

    camera: str = "MAIN"

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

    latency_ms: int = 0
SteamDeck
        │
        ▼
 UDP Packet

Robot
        │
        ▼
 UDP Packet

Protocol Version
Packet Types
Heartbeat 100 ms
Control Packet 50 Hz
Telemetry Packet 20 Hz
Video Stream
Future Packets

CONTROL
    sequence
    throttle
    steering
    brake
    requested_mode
    buttons
    buttons_changed
TELEMETRY
    timestamp
    battery_percent
    battery_voltage
    battery_current
    speed
    heading
    roll
    pitch
    yaw
    gps_lat
    gps_lon
    gps_alt
    gps_sat
    mode
    light_mode
    camera
    link_quality
    bitrate
    latency
    errors
    flags

# NKR UDP Protocol v3

The ROS2-independent GCS sends UDP to the robot ROS2 Gateway at its configured
address, normally over Tailscale. All multi-byte fields are little-endian.
`MAGIC = 0x4E4B`, `VERSION = 3`, and every packet ends with a
little-endian CRC-16/CCITT-FALSE calculated over the preceding payload.

## Session

The GCS uses one long-lived UDP socket because the Gateway binds a session to
the GCS `(IP, port)`.

1. GCS sends hello: `<HBB` (`TYPE_SESSION_HELLO = 5`) plus CRC.
2. Gateway responds with challenge: `<HBBII` (`TYPE_SESSION_CHALLENGE = 6`),
   containing `session_id` and `challenge`, plus CRC.
3. GCS validates magic, version, type and CRC, then sends response `<HBBII`
   (`TYPE_SESSION_RESPONSE = 7`) with the same `session_id` and challenge.
4. GCS sends control only after the response has been sent. Socket errors reset
   the session and cause the hello handshake to be retried.

## Control

Control packet is `<HBBIHhhhBBHH` plus CRC (`TYPE_CONTROL = 1`):

| Field | Type |
| --- | --- |
| magic, version, type | `uint16`, `uint8`, `uint8` |
| session_id, sequence | `uint32`, `uint16` |
| throttle, steering, brake | `int16`, each `-1000..1000` |
| requested_mode | `uint8` |
| requested_light_mode | `uint8` |
| buttons, buttons_changed | `uint16`, `uint16` |

Input throttle is right trigger minus left trigger. Brake is L1 (1.0 is full
brake). All axes are clamped to `[-1.0, 1.0]` before conversion to protocol
values. `buttons_changed = current_buttons XOR previous_buttons`; Back/View,
Start/Menu, and Steam map to `BUTTON_VIEW`, `BUTTON_MENU`, and `BUTTON_STEAM`.

## Robot-state telemetry

The Gateway sends robot state over the same authenticated UDP socket:
`<HBBIBBB` plus CRC (`TYPE_TELEMETRY = 2`). Fields are `magic`, `version`,
`packet_type`, `session_id`, `active_mode`, `active_light_mode`, and `flags`.
GCS checks CRC,
magic, version, type, and that `session_id` matches its active session; stale
or foreign-session telemetry is ignored.

Flags are `ROBOT_STATE_ARMED = 1 << 0` and `ROBOT_STATE_ESTOP = 1 << 1`.
Modes 1–5 are FRONT STEER, TANK, CRAB, FRONT DRIVE, and REAR DRIVE. Valid
telemetry refreshes the active-session timeout and updates GCS state/popups.

Light mode 0 means KEEP for a suppressed control frame. Selectable modes are
1 DARK, 2 LOW BEAM, 3 HIGH BEAM, 4 SEARCHLIGHT, and 5 PARKING LIGHTS.

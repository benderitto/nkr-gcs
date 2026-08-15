"""NKR UDP Protocol v2 packing and validation (little-endian)."""

import struct

from .constants import (
    MAGIC,
    VERSION,
    TYPE_CONTROL,
    TYPE_TELEMETRY,
    TYPE_SESSION_HELLO,
    TYPE_SESSION_CHALLENGE,
    TYPE_SESSION_RESPONSE,
)

from .crc import crc16
from .packets import ControlPacket, RobotStatePacket, SessionPacket


#
# Packet layout:
#
# uint16 magic
# uint8  version
# uint8  packet_type
# uint32 session_id
# uint16 sequence
# int16  throttle
# int16  steering
# int16  brake
# uint8  requested_mode
# uint16 buttons
# uint16 buttons_changed
#

CONTROL_STRUCT = struct.Struct("<HBBIHhhhBHH")
HELLO_STRUCT = struct.Struct("<HBB")
SESSION_STRUCT = struct.Struct("<HBBII")
ROBOT_STATE_STRUCT = struct.Struct("<HBBIBB")

CRC_STRUCT = struct.Struct("<H")


def pack_control(packet: ControlPacket) -> bytes:

    _validate_control(packet)

    payload = CONTROL_STRUCT.pack(
        MAGIC,
        VERSION,
        TYPE_CONTROL,
        packet.session_id,
        packet.sequence,
        packet.throttle,
        packet.steering,
        packet.brake,
        packet.requested_mode,
        packet.buttons,
        packet.buttons_changed,
    )

    crc = crc16(payload)

    return payload + CRC_STRUCT.pack(crc)


def _validate_control(packet: ControlPacket) -> None:
    """Reject values the gateway would consider malformed before serializing."""
    for name, value, lower, upper in (
        ("session_id", packet.session_id, 0, 0xFFFFFFFF),
        ("sequence", packet.sequence, 0, 0xFFFF),
        ("throttle", packet.throttle, -1000, 1000),
        ("steering", packet.steering, -1000, 1000),
        ("brake", packet.brake, -1000, 1000),
        ("requested_mode", packet.requested_mode, 0, 0xFF),
        ("buttons", packet.buttons, 0, 0xFFFF),
        ("buttons_changed", packet.buttons_changed, 0, 0xFFFF),
    ):
        if not isinstance(value, int) or not lower <= value <= upper:
            raise ValueError(f"Invalid {name}: {value!r}")


def unpack_control(data: bytes) -> ControlPacket:

    if len(data) != CONTROL_STRUCT.size + CRC_STRUCT.size:
        raise ValueError("Invalid packet size")

    payload = data[:-2]

    received_crc = CRC_STRUCT.unpack(data[-2:])[0]

    calculated_crc = crc16(payload)

    if received_crc != calculated_crc:
        raise ValueError("CRC mismatch")

    (
        magic,
        version,
        packet_type,
        session_id,
        sequence,
        throttle,
        steering,
        brake,
        requested_mode,
        buttons,
        buttons_changed,
    ) = CONTROL_STRUCT.unpack(payload)

    if magic != MAGIC:
        raise ValueError("Invalid magic")

    if version != VERSION:
        raise ValueError("Unsupported protocol version")

    if packet_type != TYPE_CONTROL:
        raise ValueError("Unexpected packet type")

    _validate_control(ControlPacket(
        session_id=session_id, sequence=sequence, throttle=throttle,
        steering=steering, brake=brake, requested_mode=requested_mode,
        buttons=buttons, buttons_changed=buttons_changed,
    ))

    return ControlPacket(
        session_id=session_id,
        sequence=sequence,
        throttle=throttle,
        steering=steering,
        brake=brake,
        requested_mode=requested_mode,
        buttons=buttons,
        buttons_changed=buttons_changed,
    )


def pack_session_hello() -> bytes:
    return _append_crc(HELLO_STRUCT.pack(MAGIC, VERSION, TYPE_SESSION_HELLO))


def pack_session_response(session_id: int, challenge: int) -> bytes:
    _validate_uint32("session_id", session_id)
    _validate_uint32("challenge", challenge)
    return _append_crc(SESSION_STRUCT.pack(
        MAGIC, VERSION, TYPE_SESSION_RESPONSE, session_id, challenge,
    ))


def unpack_session_challenge(data: bytes) -> SessionPacket:
    """Validate and decode a v2 challenge received from the gateway."""
    _validate_packet(data, SESSION_STRUCT)
    magic, version, packet_type, session_id, challenge = SESSION_STRUCT.unpack(data[:-2])
    if magic != MAGIC:
        raise ValueError("Invalid magic")
    if version != VERSION:
        raise ValueError("Unsupported protocol version")
    if packet_type != TYPE_SESSION_CHALLENGE:
        raise ValueError("Unexpected packet type")
    return SessionPacket(packet_type, session_id, challenge)


def pack_robot_state(packet: RobotStatePacket) -> bytes:
    _validate_uint32("session_id", packet.session_id)
    _validate_uint8("active_mode", packet.active_mode)
    _validate_uint8("flags", packet.flags)
    return _append_crc(ROBOT_STATE_STRUCT.pack(
        MAGIC, VERSION, TYPE_TELEMETRY, packet.session_id,
        packet.active_mode, packet.flags,
    ))


def unpack_robot_state(data: bytes) -> RobotStatePacket:
    _validate_packet(data, ROBOT_STATE_STRUCT)
    magic, version, packet_type, session_id, active_mode, flags = (
        ROBOT_STATE_STRUCT.unpack(data[:-2])
    )
    if magic != MAGIC:
        raise ValueError("Invalid magic")
    if version != VERSION:
        raise ValueError("Unsupported protocol version")
    if packet_type != TYPE_TELEMETRY:
        raise ValueError("Unexpected packet type")
    return RobotStatePacket(session_id, active_mode, flags)


def _append_crc(payload: bytes) -> bytes:
    return payload + CRC_STRUCT.pack(crc16(payload))


def _validate_packet(data: bytes, payload_struct: struct.Struct) -> None:
    if len(data) != payload_struct.size + CRC_STRUCT.size:
        raise ValueError("Invalid packet size")
    if CRC_STRUCT.unpack(data[-2:])[0] != crc16(data[:-2]):
        raise ValueError("CRC mismatch")


def _validate_uint32(name: str, value: int) -> None:
    if not isinstance(value, int) or not 0 <= value <= 0xFFFFFFFF:
        raise ValueError(f"Invalid {name}: {value!r}")


def _validate_uint8(name: str, value: int) -> None:
    if not isinstance(value, int) or not 0 <= value <= 0xFF:
        raise ValueError(f"Invalid {name}: {value!r}")

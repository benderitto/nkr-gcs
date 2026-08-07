"""
NKR Protocol v1.
"""

import struct

from .constants import (
    MAGIC,
    VERSION,
    TYPE_CONTROL,
)

from .crc import crc16
from .packets import ControlPacket


#
# Packet layout:
#
# uint16 magic
# uint8  version
# uint8  packet_type
# uint16 sequence
# int16  throttle
# int16  steering
# int16  brake
# uint8  requested_mode
# uint16 buttons
# uint16 buttons_changed
#

CONTROL_STRUCT = struct.Struct(
    "<HBBHhhhBHH"
)

CRC_STRUCT = struct.Struct("<H")


def pack_control(packet: ControlPacket) -> bytes:

    payload = CONTROL_STRUCT.pack(
        MAGIC,
        VERSION,
        TYPE_CONTROL,
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

    return ControlPacket(
        sequence=sequence,
        throttle=throttle,
        steering=steering,
        brake=brake,
        requested_mode=requested_mode,
        buttons=buttons,
        buttons_changed=buttons_changed,
    )
import struct

import pytest

from nkr_protocol.protocol import (
    CONTROL_STRUCT, CRC_STRUCT, pack_control, pack_session_hello,
    pack_session_response, pack_robot_state, unpack_control,
    unpack_robot_state, unpack_session_challenge,
)

from nkr_protocol.packets import ControlPacket

from nkr_protocol.constants import *
from nkr_protocol.crc import crc16
from nkr_protocol.packets import RobotStatePacket


def test_pack_unpack():

    pkt = ControlPacket()

    pkt.sequence = 123

    pkt.throttle = 800

    pkt.steering = -250

    pkt.brake = 350

    pkt.requested_mode = MODE_CRAB

    pkt.buttons = BUTTON_A | BUTTON_L1

    pkt.buttons_changed = BUTTON_A

    raw = pack_control(pkt)

    decoded = unpack_control(raw)

    assert decoded == pkt

from nkr_protocol.axis import encode_axis, decode_axis


def test_axis_conversion():

    assert encode_axis(0.0) == 0

    assert encode_axis(1.0) == 1000

    assert encode_axis(-1.0) == -1000

    assert decode_axis(1000) == 1.0

    assert decode_axis(-1000) == -1.0

    assert decode_axis(500) == 0.5


def test_control_crc_version_type_and_axis_validation():
    packet = ControlPacket(session_id=1, throttle=1001)
    with pytest.raises(ValueError, match="throttle"):
        pack_control(packet)

    raw = bytearray(pack_control(ControlPacket(session_id=1)))
    raw[-1] ^= 1
    with pytest.raises(ValueError, match="CRC"):
        unpack_control(bytes(raw))

    payload = CONTROL_STRUCT.pack(MAGIC, VERSION + 1, TYPE_CONTROL, 1, 0,
                                  0, 0, 0, 0, 0, 0)
    with pytest.raises(ValueError, match="version"):
        unpack_control(payload + CRC_STRUCT.pack(crc16(payload)))

    payload = CONTROL_STRUCT.pack(MAGIC, VERSION, TYPE_TELEMETRY, 1, 0,
                                  0, 0, 0, 0, 0, 0)
    with pytest.raises(ValueError, match="type"):
        unpack_control(payload + CRC_STRUCT.pack(crc16(payload)))


def test_session_packet_pack_unpack():
    hello = pack_session_hello()
    assert hello == struct.pack("<HBBH", MAGIC, VERSION, TYPE_SESSION_HELLO,
                                crc16(hello[:-2]))
    payload = struct.pack("<HBBII", MAGIC, VERSION, TYPE_SESSION_CHALLENGE,
                          42, 99)
    decoded = unpack_session_challenge(payload + CRC_STRUCT.pack(crc16(payload)))
    assert (decoded.session_id, decoded.challenge) == (42, 99)
    response = pack_session_response(42, 99)
    assert response[:-2] == struct.pack("<HBBII", MAGIC, VERSION,
                                         TYPE_SESSION_RESPONSE, 42, 99)


def test_robot_state_round_trip_and_validation():
    packet = RobotStatePacket(session_id=42, active_mode=MODE_TANK,
                              flags=ROBOT_STATE_ARMED | ROBOT_STATE_ESTOP)
    raw = pack_robot_state(packet)
    assert unpack_robot_state(raw) == packet

    corrupted = bytearray(raw)
    corrupted[-1] ^= 1
    with pytest.raises(ValueError, match="CRC"):
        unpack_robot_state(bytes(corrupted))

    for magic, version, packet_type, message in (
        (MAGIC + 1, VERSION, TYPE_TELEMETRY, "magic"),
        (MAGIC, VERSION + 1, TYPE_TELEMETRY, "version"),
        (MAGIC, VERSION, TYPE_CONTROL, "type"),
    ):
        payload = struct.pack("<HBBIBB", magic, version, packet_type, 42, 1, 0)
        with pytest.raises(ValueError, match=message):
            unpack_robot_state(payload + CRC_STRUCT.pack(crc16(payload)))

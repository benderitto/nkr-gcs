from nkr_protocol.protocol import pack_control, unpack_control

from nkr_protocol.packets import ControlPacket

from nkr_protocol.constants import *


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
from nkr_gcs.model.operator_model import OperatorModel
from nkr_gcs.input.controller import ControllerState
from nkr_gcs.input.mapping import InputMapping
from nkr_gcs.network.network_manager import NetworkManager
from nkr_gcs.network.session_client import SessionState
from nkr_gcs.settings import Settings
from nkr_gcs.model.robot_model import RobotModel
from nkr_protocol.constants import (
    BUTTON_MENU, MAGIC, MODE_CRAB, ROBOT_STATE_ARMED, ROBOT_STATE_ESTOP,
    TYPE_SESSION_CHALLENGE, VERSION,
)
from nkr_protocol.crc import crc16
from nkr_protocol.protocol import (
    CONTROL_STRUCT, CRC_STRUCT, pack_robot_state, unpack_control,
)
from nkr_protocol.packets import RobotStatePacket

import struct


class FakeClient:
    def __init__(self):
        self.sent = []
        self.incoming = []
        self.closed = False

    def send(self, data):
        self.sent.append(data)

    def receive(self):
        packets = self.incoming
        self.incoming = []
        return packets

    def close(self):
        self.closed = True


def challenge(session_id=1234, challenge_value=5678):
    payload = struct.pack("<HBBII", MAGIC, VERSION, TYPE_SESSION_CHALLENGE,
                          session_id, challenge_value)
    return payload + CRC_STRUCT.pack(crc16(payload))


def manager(client, clock):
    return NetworkManager(Settings("192.168.1.24", 9999, 50), client, clock)


def test_control_is_not_sent_before_handshake():
    now = [0.0]
    client = FakeClient()
    net = manager(client, lambda: now[0])
    net.update(OperatorModel())
    assert len(client.sent) == 1  # hello only
    assert len(client.sent[0]) == 6
    assert net.session.state is SessionState.WAIT_CHALLENGE


def test_challenge_response_sets_session_and_control_uses_it():
    now = [0.0]
    client = FakeClient()
    net = manager(client, lambda: now[0])
    net.update(OperatorModel())  # hello; no control while waiting
    client.incoming.append(challenge())
    net.update(OperatorModel(throttle=2.0, steering=-2.0, brake=2.0))
    assert net.session.session_id == 1234
    assert net.session.state is SessionState.ACTIVE
    assert [len(packet) for packet in client.sent] == [6, 14]
    now[0] = 0.02
    net.update(OperatorModel(throttle=2.0, steering=-2.0, brake=2.0))
    assert len(client.sent) == 3  # hello, response, control
    control = unpack_control(client.sent[-1])
    assert control.session_id == 1234
    assert (control.throttle, control.steering, control.brake) == (1000, -1000, 1000)


def test_sequence_wraps_and_socket_is_reused():
    now = [0.0]
    client = FakeClient()
    net = manager(client, lambda: now[0])
    net.sequence = 0xFFFF
    net.update(OperatorModel())
    client.incoming.append(challenge())
    net.update(OperatorModel())
    now[0] = 0.02
    net.update(OperatorModel())
    first = unpack_control(client.sent[-1])
    now[0] = 0.04
    net.update(OperatorModel())
    second = unpack_control(client.sent[-1])
    assert (first.sequence, second.sequence, net.sequence) == (0xFFFF, 0, 1)
    assert net.client is client


def test_handshake_timeout_restarts_with_hello_and_never_controls():
    now = [0.0]
    client = FakeClient()
    net = manager(client, lambda: now[0])
    net.update(OperatorModel())
    now[0] = 1.0
    net.update(OperatorModel())
    assert [len(packet) for packet in client.sent] == [6, 6]
    assert net.session.state is SessionState.WAIT_CHALLENGE


def test_start_button_is_sent_as_button_menu_in_control_packet():
    now = [0.0]
    client = FakeClient()
    net = manager(client, lambda: now[0])
    operator = OperatorModel()
    InputMapping().update(ControllerState(start=True), operator)
    assert operator.buttons == BUTTON_MENU
    assert operator.buttons_changed == BUTTON_MENU

    net.update(operator)
    client.incoming.append(challenge())
    net.update(operator)
    now[0] = 0.02
    net.update(operator)
    control = unpack_control(client.sent[-1])
    assert control.buttons == BUTTON_MENU
    assert control.buttons_changed == BUTTON_MENU


def test_button_edge_is_computed_against_last_sent_packet():
    now = [0.0]
    client = FakeClient()
    net = manager(client, lambda: now[0])
    operator = OperatorModel()
    net.update(operator)
    client.incoming.append(challenge())
    net.update(operator)

    # The press and its input-frame edge happen before the next 50 Hz send.
    operator.buttons = BUTTON_MENU
    operator.buttons_changed = 0
    now[0] = 0.02
    net.update(operator)
    pressed = unpack_control(client.sent[-1])
    assert (pressed.buttons, pressed.buttons_changed) == (BUTTON_MENU, BUTTON_MENU)

    # Likewise, release remains visible in the next packet.
    operator.buttons = 0
    now[0] = 0.04
    net.update(operator)
    released = unpack_control(client.sent[-1])
    assert (released.buttons, released.buttons_changed) == (0, BUTTON_MENU)


def test_application_owns_and_updates_network_manager():
    source = open("nkr_gcs/application.py", encoding="utf-8").read()
    assert "self.network = NetworkManager(settings=self.settings, robot=self.window.robot)" in source
    assert "self.network.update(self.operator)" in source


def test_telemetry_updates_robot_model_and_stale_session_is_ignored():
    now = [0.0]
    client = FakeClient()
    robot = RobotModel()
    net = NetworkManager(Settings("192.168.1.24", 9999, 50), client,
                         lambda: now[0], robot=robot)
    net.update(OperatorModel())
    client.incoming.append(challenge(session_id=1234))
    net.update(OperatorModel())
    stale = pack_robot_state(RobotStatePacket(9, MODE_CRAB, ROBOT_STATE_ARMED))
    current = pack_robot_state(RobotStatePacket(
        1234, MODE_CRAB, ROBOT_STATE_ARMED | ROBOT_STATE_ESTOP,
    ))
    client.incoming.extend([stale, current])
    now[0] = 0.02
    assert net.update(OperatorModel()) is True
    assert (robot.active_mode, robot.drive_mode, robot.armed, robot.estop) == (
        MODE_CRAB, "CRAB", True, True,
    )
    assert net.session._last_gateway_packet_at == now[0]

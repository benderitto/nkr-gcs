import multiprocessing
import time

from nkr_gcs.model.operator_model import OperatorModel
from nkr_gcs.network.control_worker import (
    ControlWorker, _ControlLoop, _read_operator_mailbox,
    _read_robot_mailbox, _write_operator_mailbox, _write_robot_mailbox,
)
from nkr_gcs.model.robot_model import RobotModel
from nkr_gcs.settings import Settings
from nkr_protocol.constants import (
    BUTTON_MENU, LIGHT_HIGH_BEAM, LIGHT_KEEP, MODE_CRAB, MODE_KEEP,
)


class FakeSettings:
    control_rate_hz = 50


class FakeNetwork:
    def __init__(self):
        self.settings = FakeSettings()
        self.operators = []
        self.closed = False
        self.updated = False

    def update(self, operator):
        self.operators.append(operator)
        result = self.updated
        self.updated = False
        return result

    def close(self):
        self.closed = True


def test_worker_uses_latest_immutable_operator_snapshot():
    now = [10.0]
    network = FakeNetwork()
    worker = _ControlLoop(network, clock=lambda: now[0])
    operator = OperatorModel(
        throttle=0.7, steering=-0.2, requested_drive_mode=MODE_CRAB,
        requested_light_mode=LIGHT_HIGH_BEAM, buttons=BUTTON_MENU,
    )
    worker.submit(operator)
    operator.throttle = 0.0

    worker.network_cycle()

    sent = network.operators[-1]
    assert sent.throttle == 0.7
    assert sent.steering == -0.2
    assert sent.buttons == BUTTON_MENU


def test_stale_gui_snapshot_brakes_without_dropping_network_session():
    now = [0.0]
    network = FakeNetwork()
    worker = _ControlLoop(
        network, operator_stale_timeout=0.25, clock=lambda: now[0],
    )
    worker.submit(OperatorModel(
        throttle=1.0, steering=0.5, requested_drive_mode=MODE_CRAB,
        requested_light_mode=LIGHT_HIGH_BEAM, buttons=BUTTON_MENU,
    ))
    worker.network_cycle()
    now[0] = 0.251
    worker.network_cycle()

    sent = network.operators[-1]
    assert (sent.throttle, sent.steering, sent.brake) == (0.0, 0.0, 1.0)
    assert sent.requested_drive_mode == MODE_KEEP
    assert sent.requested_light_mode == LIGHT_KEEP
    assert sent.buttons == 0
    assert len(network.operators) == 2


def test_loop_reports_telemetry_update():
    network = FakeNetwork()
    worker = _ControlLoop(network)
    network.updated = True
    assert worker.network_cycle() is True
    assert worker.network_cycle() is False


def test_shared_mailboxes_return_atomic_latest_values():
    context = multiprocessing.get_context("spawn")
    operator_mailbox = context.Array("d", 10, lock=True)
    expected = OperatorModel(throttle=0.8, buttons=BUTTON_MENU)
    _write_operator_mailbox(operator_mailbox, expected, 12.5)
    operator, updated_at = _read_operator_mailbox(operator_mailbox)
    assert (operator.throttle, operator.buttons, updated_at) == (
        0.8, BUTTON_MENU, 12.5,
    )

    robot_mailbox = context.Array("q", 5, lock=True)
    robot = RobotModel(active_mode=MODE_CRAB, armed=True)
    _write_robot_mailbox(robot_mailbox, robot)
    generation, snapshot = _read_robot_mailbox(robot_mailbox)
    assert (generation, snapshot.active_mode, snapshot.armed) == (
        1, MODE_CRAB, True,
    )


def test_isolated_control_process_starts_and_stops():
    settings = Settings(
        robot_host="127.0.0.1", robot_port=59999,
        video_enabled=False, video_host="127.0.0.1",
    )
    worker = ControlWorker(settings)
    deadline = time.monotonic() + 5.0
    while not worker._process.is_alive() and time.monotonic() < deadline:
        time.sleep(0.01)
    assert worker._process.is_alive()
    worker.submit(OperatorModel(throttle=0.5))
    worker.close()

    assert worker._process.exitcode == 0

from nkr_gcs.model.operator_model import OperatorModel
from nkr_gcs.network.control_worker import ControlWorker
from nkr_protocol.constants import (
    BUTTON_MENU, LIGHT_HIGH_BEAM, LIGHT_KEEP, MODE_CRAB, MODE_KEEP,
)


class Settings:
    control_rate_hz = 50


class FakeNetwork:
    def __init__(self):
        self.settings = Settings()
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
    worker = ControlWorker(network, clock=lambda: now[0], autostart=False)
    operator = OperatorModel(
        throttle=0.7, steering=-0.2, requested_drive_mode=MODE_CRAB,
        requested_light_mode=LIGHT_HIGH_BEAM, buttons=BUTTON_MENU,
    )
    worker.submit(operator)
    operator.throttle = 0.0

    worker._network_cycle()

    sent = network.operators[-1]
    assert sent.throttle == 0.7
    assert sent.steering == -0.2
    assert sent.buttons == BUTTON_MENU


def test_stale_gui_snapshot_brakes_without_dropping_network_session():
    now = [0.0]
    network = FakeNetwork()
    worker = ControlWorker(
        network, operator_stale_timeout=0.25,
        clock=lambda: now[0], autostart=False,
    )
    worker.submit(OperatorModel(
        throttle=1.0, steering=0.5, requested_drive_mode=MODE_CRAB,
        requested_light_mode=LIGHT_HIGH_BEAM, buttons=BUTTON_MENU,
    ))
    worker._network_cycle()
    now[0] = 0.251
    worker._network_cycle()

    sent = network.operators[-1]
    assert (sent.throttle, sent.steering, sent.brake) == (0.0, 0.0, 1.0)
    assert sent.requested_drive_mode == MODE_KEEP
    assert sent.requested_light_mode == LIGHT_KEEP
    assert sent.buttons == 0
    assert len(network.operators) == 2


def test_worker_reports_telemetry_edge_once_and_closes_transport():
    network = FakeNetwork()
    worker = ControlWorker(network, autostart=False)
    network.updated = True
    worker._network_cycle()

    assert worker.take_robot_updated() is True
    assert worker.take_robot_updated() is False
    worker.close()
    assert network.closed is True

"""Control transport isolated from the Qt/video process."""

from dataclasses import dataclass, replace
from logging.handlers import QueueHandler, QueueListener
import logging
import multiprocessing
import time

from nkr_protocol.constants import LIGHT_KEEP, MODE_KEEP

from ..model.operator_model import OperatorModel
from ..model.robot_model import LIGHT_MODE_NAMES, MODE_NAMES, RobotModel
from .network_manager import NetworkManager


logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class NetworkRobotSnapshot:
    active_mode: int
    drive_mode: str
    active_light_mode: int
    light_mode: str
    armed: bool
    estop: bool


class _ControlLoop:
    """Deterministic control loop used inside the isolated process."""

    def __init__(self, network, operator_stale_timeout=0.25,
                 clock=time.monotonic):
        if operator_stale_timeout <= 0:
            raise ValueError("operator_stale_timeout must be positive")
        self.network = network
        self.operator_stale_timeout = float(operator_stale_timeout)
        self._clock = clock
        self._operator = OperatorModel()
        self._operator_updated_at = self._clock()
        self._operator_stale = False
        self._last_error_log_at = float("-inf")

    def submit(self, operator, updated_at=None):
        self._operator = replace(operator)
        self._operator_updated_at = (
            self._clock() if updated_at is None else updated_at
        )

    def network_cycle(self):
        operator, stale = self._operator_snapshot()
        if stale != self._operator_stale:
            if stale:
                logger.warning(
                    "GUI operator snapshot stale; sending brake while keeping session alive"
                )
            else:
                logger.info("Fresh GUI operator snapshots resumed")
            self._operator_stale = stale
        try:
            return self.network.update(operator)
        except Exception:
            now = self._clock()
            if now - self._last_error_log_at >= 5.0:
                logger.exception("Control process network cycle failed")
                self._last_error_log_at = now
            return False

    def _operator_snapshot(self):
        operator = replace(self._operator)
        age = self._clock() - self._operator_updated_at
        if age <= self.operator_stale_timeout:
            return operator, False
        operator.throttle = 0.0
        operator.steering = 0.0
        operator.brake = 1.0
        operator.requested_drive_mode = MODE_KEEP
        operator.requested_light_mode = LIGHT_KEEP
        operator.buttons = 0
        operator.buttons_changed = 0
        return operator, True


class ControlWorker:
    """Own a spawned process that keeps the authenticated control link alive.

    A separate process is intentional: a long-running Qt, SDL, or GStreamer
    Python callback may hold the GIL and pause every thread in the UI process.
    The control process has its own interpreter, GIL, monotonic scheduler, and
    UDP socket.
    """

    def __init__(self, settings, poll_rate_hz=100.0,
                 operator_stale_timeout=0.25, context=None, autostart=True):
        if poll_rate_hz <= 0:
            raise ValueError("poll_rate_hz must be positive")
        if operator_stale_timeout <= 0:
            raise ValueError("operator_stale_timeout must be positive")
        self.settings = settings
        self.poll_rate_hz = float(poll_rate_hz)
        self.operator_stale_timeout = float(operator_stale_timeout)
        self._context = context or multiprocessing.get_context("spawn")
        self._operator_mailbox = None
        self._robot_mailbox = None
        self._robot_generation = 0
        self._log_queue = None
        self._stop = None
        self._process = None
        self._log_listener = None
        self._closed = False
        self._process_failure_logged = False
        if autostart:
            self.start()

    def start(self):
        if self._process is not None:
            return
        self._operator_mailbox = self._context.Array("d", 10, lock=True)
        _write_operator_mailbox(
            self._operator_mailbox, OperatorModel(), time.monotonic(),
        )
        self._robot_mailbox = self._context.Array("q", 5, lock=True)
        self._log_queue = self._context.Queue()
        self._stop = self._context.Event()
        handlers = tuple(logging.getLogger().handlers)
        if handlers:
            self._log_listener = QueueListener(
                self._log_queue, *handlers, respect_handler_level=True,
            )
            self._log_listener.start()
        self._process = self._context.Process(
            target=_control_process_main,
            args=(
                self.settings,
                self.poll_rate_hz,
                self.operator_stale_timeout,
                self._operator_mailbox,
                self._robot_mailbox,
                self._log_queue,
                self._stop,
            ),
            name="nkr-control-network",
            daemon=True,
        )
        self._process.start()
        logger.info(
            "Control process started: pid=%d poll=%.1f Hz send=%.1f Hz stale=%.3f s",
            self._process.pid,
            self.poll_rate_hz,
            self.settings.control_rate_hz,
            self.operator_stale_timeout,
        )

    def submit(self, operator):
        """Publish the latest operator intent without blocking the Qt loop."""
        self._check_process()
        if self._operator_mailbox is not None:
            _write_operator_mailbox(
                self._operator_mailbox, operator, time.monotonic(),
            )

    def take_robot_update(self):
        """Return the newest network-owned robot state, if one is available."""
        self._check_process()
        if self._robot_mailbox is None:
            return None
        generation, snapshot = _read_robot_mailbox(self._robot_mailbox)
        if generation == self._robot_generation:
            return None
        self._robot_generation = generation
        return snapshot

    def close(self):
        if self._closed:
            return
        self._closed = True
        if self._stop is not None:
            self._stop.set()
        process = self._process
        if process is not None:
            process.join(timeout=3.0)
            if process.is_alive():
                logger.error("Control process did not stop within 3 seconds; terminating")
                process.terminate()
                process.join(timeout=2.0)
        if self._log_listener is not None:
            self._log_listener.stop()
        if self._log_queue is not None:
            self._log_queue.close()
            self._log_queue.cancel_join_thread()
        logger.info("Control process stopped")

    def _check_process(self):
        process = self._process
        if (process is not None and process.exitcode is not None
                and not self._process_failure_logged and not self._closed):
            logger.error("Control process exited unexpectedly with code %s",
                         process.exitcode)
            self._process_failure_logged = True


def _control_process_main(settings, poll_rate_hz, operator_stale_timeout,
                          operator_mailbox, robot_mailbox, log_queue, stop_event):
    """Spawn-safe child entry point; do not import or construct Qt here."""
    root_logger = logging.getLogger()
    root_logger.handlers.clear()
    root_logger.addHandler(QueueHandler(log_queue))
    root_logger.setLevel(logging.INFO)

    robot = RobotModel()
    network = NetworkManager(settings=settings, robot=robot)
    loop = _ControlLoop(network, operator_stale_timeout)
    period = 1.0 / poll_rate_hz
    deadline = time.monotonic()
    logger.info("Isolated control process ready")
    try:
        while not stop_event.is_set():
            operator, updated_at = _read_operator_mailbox(operator_mailbox)
            loop.submit(operator, updated_at)
            if loop.network_cycle():
                _write_robot_mailbox(robot_mailbox, robot)
            deadline += period
            delay = deadline - time.monotonic()
            if delay <= 0:
                deadline = time.monotonic()
                continue
            stop_event.wait(delay)
    finally:
        network.close()
        logger.info("Isolated control process stopped")


def _write_operator_mailbox(mailbox, operator, updated_at):
    """Atomically replace the operator snapshot in shared memory."""
    values = (
        operator.throttle,
        operator.steering,
        operator.brake,
        operator.requested_drive_mode,
        operator.requested_camera,
        operator.requested_light_mode,
        operator.buttons,
        operator.buttons_changed,
        float(operator.connected),
        updated_at,
    )
    with mailbox.get_lock():
        mailbox[:] = values


def _read_operator_mailbox(mailbox):
    with mailbox.get_lock():
        values = mailbox[:]
    return OperatorModel(
        throttle=values[0],
        steering=values[1],
        brake=values[2],
        requested_drive_mode=int(values[3]),
        requested_camera=int(values[4]),
        requested_light_mode=int(values[5]),
        buttons=int(values[6]),
        buttons_changed=int(values[7]),
        connected=bool(values[8]),
    ), values[9]


def _write_robot_mailbox(mailbox, robot):
    with mailbox.get_lock():
        generation = mailbox[4] + 1
        mailbox[:] = (
            robot.active_mode,
            robot.active_light_mode,
            int(robot.armed),
            int(robot.estop),
            generation,
        )


def _read_robot_mailbox(mailbox):
    with mailbox.get_lock():
        active_mode, active_light_mode, armed, estop, generation = mailbox[:]
    return generation, NetworkRobotSnapshot(
        active_mode=active_mode,
        drive_mode=MODE_NAMES.get(active_mode, "UNKNOWN"),
        active_light_mode=active_light_mode,
        light_mode=LIGHT_MODE_NAMES.get(active_light_mode, "UNKNOWN"),
        armed=bool(armed),
        estop=bool(estop),
    )

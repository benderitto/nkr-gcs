"""Control transport isolated from the Qt/video event loop."""

from dataclasses import replace
import logging
import threading
import time

from nkr_protocol.constants import LIGHT_KEEP, MODE_KEEP

from ..model.operator_model import OperatorModel


logger = logging.getLogger(__name__)


class ControlWorker:
    """Keep the authenticated control link alive on a dedicated thread.

    The GUI publishes immutable snapshots into a latest-value mailbox. If the
    GUI stops updating that mailbox, the worker keeps the UDP session alive but
    replaces motion with brake after ``operator_stale_timeout``. This avoids
    repeating stale throttle while also preventing video/UI stalls from
    destroying the authenticated session.
    """

    def __init__(
        self,
        network,
        poll_rate_hz=100.0,
        operator_stale_timeout=0.25,
        clock=time.monotonic,
        autostart=True,
    ):
        if poll_rate_hz <= 0:
            raise ValueError("poll_rate_hz must be positive")
        if operator_stale_timeout <= 0:
            raise ValueError("operator_stale_timeout must be positive")
        self.network = network
        self.poll_rate_hz = float(poll_rate_hz)
        self.operator_stale_timeout = float(operator_stale_timeout)
        self._clock = clock
        self._lock = threading.Lock()
        self._operator = OperatorModel()
        self._operator_updated_at = self._clock()
        self._robot_updated = False
        self._operator_stale = False
        self._last_error_log_at = float("-inf")
        self._stop = threading.Event()
        self._thread = None
        if autostart:
            self.start()

    def start(self):
        if self._thread is not None:
            return
        self._thread = threading.Thread(
            target=self._run,
            name="nkr-control-network",
            daemon=True,
        )
        self._thread.start()
        logger.info(
            "Control worker started: poll=%.1f Hz send=%.1f Hz stale=%.3f s",
            self.poll_rate_hz,
            self.network.settings.control_rate_hz,
            self.operator_stale_timeout,
        )

    def submit(self, operator):
        """Publish the latest operator intent without sharing mutable state."""
        snapshot = replace(operator)
        now = self._clock()
        with self._lock:
            self._operator = snapshot
            self._operator_updated_at = now

    def take_robot_updated(self):
        """Return and clear the telemetry-updated edge for the GUI thread."""
        with self._lock:
            updated = self._robot_updated
            self._robot_updated = False
        return updated

    def close(self):
        self._stop.set()
        thread = self._thread
        if thread is not None and thread is not threading.current_thread():
            thread.join(timeout=2.0)
            if thread.is_alive():
                logger.error("Control worker did not stop within 2 seconds")
        self.network.close()
        logger.info("Control worker stopped")

    def _run(self):
        period = 1.0 / self.poll_rate_hz
        deadline = self._clock()
        while not self._stop.is_set():
            self._network_cycle()
            deadline += period
            delay = deadline - self._clock()
            if delay <= 0:
                deadline = self._clock()
                continue
            self._stop.wait(delay)

    def _network_cycle(self):
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
            robot_updated = self.network.update(operator)
        except Exception:
            now = self._clock()
            if now - self._last_error_log_at >= 5.0:
                logger.exception("Control worker network cycle failed")
                self._last_error_log_at = now
            return
        if robot_updated:
            with self._lock:
                self._robot_updated = True

    def _operator_snapshot(self):
        now = self._clock()
        with self._lock:
            operator = replace(self._operator)
            age = now - self._operator_updated_at
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

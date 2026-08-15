"""UDP control transport, deliberately separate from SDL and Qt UI."""

import logging
import time

from nkr_protocol.axis import encode_axis
from nkr_protocol.packets import ControlPacket
from nkr_protocol.protocol import pack_control
from nkr_protocol.constants import ROBOT_STATE_ARMED, ROBOT_STATE_ESTOP

from ..model.robot_model import MODE_NAMES
from ..settings import load_settings
from .session_client import SessionClient, SessionState
from .udp_client import UDPClient


logger = logging.getLogger(__name__)


class NetworkManager:
    def __init__(self, settings=None, client=None, clock=time.monotonic, robot=None):
        self.settings = settings or load_settings()
        self.client = client or UDPClient(
            host=self.settings.robot_host, port=self.settings.robot_port,
        )
        self.session = SessionClient(self.client, clock=clock)
        self.sequence = 0
        self._last_sent_buttons = 0
        self._active_session_id = None
        self._clock = clock
        self._last_control_at = None
        self._control_period = 1.0 / self.settings.control_rate_hz
        self.robot = robot
        self._last_logged_requested_mode = None

    def update(self, operator) -> bool:
        # SessionClient is the sole authority that may enter ACTIVE.  In
        # particular, control cannot leave this method while DISCONNECTED or
        # while waiting for a gateway challenge.
        state_before_update = self.session.state
        self.session.update()
        robot_updated = self._update_robot_model()
        # Response and the first control are deliberately different event-loop
        # iterations.  This makes the required wire ordering unambiguous.
        if state_before_update is not SessionState.ACTIVE:
            return robot_updated
        if self.session.state is not SessionState.ACTIVE:
            return robot_updated
        if self.session.session_id is None or not self._control_due():
            return robot_updated
        if self._active_session_id != self.session.session_id:
            # A new gateway session must see held safety buttons as new input.
            self._last_sent_buttons = 0
            self._active_session_id = self.session.session_id
        packet = ControlPacket(
            session_id=self.session.session_id,
            sequence=self.sequence,
            throttle=encode_axis(operator.throttle),
            steering=encode_axis(operator.steering),
            brake=encode_axis(operator.brake),
            requested_mode=operator.requested_drive_mode,
            buttons=operator.buttons,
            # Edges must survive input frames that occur between 50 Hz UDP
            # transmissions.  Gateway evaluates pressed as buttons & changed.
            buttons_changed=operator.buttons ^ self._last_sent_buttons,
        )
        try:
            self.client.send(pack_control(packet))
        except OSError:
            self.session.transport_error()
            return robot_updated
        self.sequence = (self.sequence + 1) & 0xFFFF
        self._last_sent_buttons = operator.buttons
        self._last_control_at = self._clock()
        if packet.requested_mode != self._last_logged_requested_mode:
            logger.info(
                "UDP control requested_mode=%d (session=%d)",
                packet.requested_mode, packet.session_id,
            )
            self._last_logged_requested_mode = packet.requested_mode
        return robot_updated

    def _update_robot_model(self) -> bool:
        """Apply valid state packets; UI is notified by Application, not here."""
        states = self.session.pop_robot_states()
        if not states or self.robot is None:
            return bool(states)
        for packet in states:
            self.robot.active_mode = packet.active_mode
            self.robot.drive_mode = MODE_NAMES.get(packet.active_mode, "UNKNOWN")
            self.robot.armed = bool(packet.flags & ROBOT_STATE_ARMED)
            self.robot.estop = bool(packet.flags & ROBOT_STATE_ESTOP)
        return True

    def _control_due(self) -> bool:
        return self._last_control_at is None or (
            self._clock() - self._last_control_at >= self._control_period
        )

    def close(self) -> None:
        self.client.close()

"""Strict state machine for the NKR v2 UDP session handshake."""

from enum import Enum, auto
import logging
import time

from nkr_protocol.protocol import (
    pack_session_hello, pack_session_response, unpack_robot_state,
    unpack_session_challenge,
)

logger = logging.getLogger(__name__)


class SessionState(Enum):
    DISCONNECTED = auto()
    WAIT_CHALLENGE = auto()
    ACTIVE = auto()


class SessionClient:
    """Session state over one UDP socket (the gateway keys sessions by peer)."""

    def __init__(self, client, handshake_timeout: float = 1.0,
                 active_timeout: float = 5.0, clock=time.monotonic):
        self.client = client
        self.handshake_timeout = handshake_timeout
        self.active_timeout = active_timeout
        self.clock = clock
        self.state = SessionState.DISCONNECTED
        self.session_id = None
        self._state_since = None
        self._last_gateway_packet_at = None
        self._robot_states = []

    @property
    def ready(self) -> bool:
        return self.state is SessionState.ACTIVE and self.session_id is not None

    def update(self) -> None:
        """Progress handshake; never transitions to ACTIVE without response."""
        now = self.clock()
        try:
            for raw in self.client.receive():
                self._handle_datagram(raw, now)
        except OSError:
            self._recover_socket()
            return

        if self.state is SessionState.DISCONNECTED:
            self._send_hello(now)
        elif self.state is SessionState.WAIT_CHALLENGE:
            if now - self._state_since >= self.handshake_timeout:
                self.disconnect()
                self._send_hello(now)
        elif now - self._last_gateway_packet_at >= self.active_timeout:
            # The v2 control stream has no acknowledgement.  Re-authenticate
            # periodically if the gateway has gone silent instead of continuing
            # to transmit a potentially stale session_id forever.
            self.disconnect()
            self._send_hello(now)

    def _send_hello(self, now: float) -> None:
        try:
            self.client.send(pack_session_hello())
        except OSError:
            self._recover_socket()
            return
        self.state = SessionState.WAIT_CHALLENGE
        self._state_since = now
        logger.info("NKR UDP session: hello sent; waiting for challenge")

    def _handle_datagram(self, raw: bytes, now: float) -> None:
        try:
            challenge = unpack_session_challenge(raw)
        except ValueError:
            self._handle_telemetry(raw, now)
            return
        self._last_gateway_packet_at = now
        # A challenge is accepted only while negotiating.  This prevents an
        # unsolicited/old datagram from authorizing control packets.
        if self.state is not SessionState.WAIT_CHALLENGE:
            return
        try:
            self.client.send(pack_session_response(
                challenge.session_id, challenge.challenge,
            ))
        except OSError:
            self._recover_socket()
            return
        self.session_id = challenge.session_id
        self.state = SessionState.ACTIVE
        self._state_since = now
        logger.info("NKR UDP session: response sent; session %d active",
                    self.session_id)

    def _handle_telemetry(self, raw: bytes, now: float) -> None:
        """Accept telemetry only from the gateway session currently in use."""
        if self.state is not SessionState.ACTIVE or self.session_id is None:
            return
        try:
            robot_state = unpack_robot_state(raw)
        except ValueError:
            return
        if robot_state.session_id != self.session_id:
            return
        self._last_gateway_packet_at = now
        self._robot_states.append(robot_state)

    def pop_robot_states(self):
        states, self._robot_states = self._robot_states, []
        return states

    def disconnect(self) -> None:
        if self.state is not SessionState.DISCONNECTED:
            logger.warning("NKR UDP session: reset to disconnected")
        self.state = SessionState.DISCONNECTED
        self.session_id = None
        self._state_since = None
        self._last_gateway_packet_at = None
        self._robot_states.clear()

    def transport_error(self) -> None:
        """Reset session and socket after an OS-level UDP error."""
        self._recover_socket()

    def _recover_socket(self) -> None:
        """A reopened socket has a new peer tuple, so discard its session."""
        self.disconnect()
        reopen = getattr(self.client, "reopen", None)
        if reopen is not None:
            try:
                reopen()
            except OSError:
                pass

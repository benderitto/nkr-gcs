"""Small privilege-free SNTP clock used for video latency measurement."""

import logging
import socket
import struct
import threading
import time


logger = logging.getLogger(__name__)

NTP_EPOCH_DELTA = 2_208_988_800
NTP_PACKET_SIZE = 48
DEFAULT_SERVERS = (
    "time.cloudflare.com",
    "time.google.com",
    "pool.ntp.org",
)


def _encode_ntp_timestamp(unix_seconds: float) -> bytes:
    ntp_seconds = unix_seconds + NTP_EPOCH_DELTA
    whole = int(ntp_seconds)
    fraction = int((ntp_seconds - whole) * (1 << 32))
    return struct.pack("!II", whole, fraction)


def _decode_ntp_timestamp(raw: bytes) -> float:
    whole, fraction = struct.unpack("!II", raw)
    return whole - NTP_EPOCH_DELTA + fraction / float(1 << 32)


def parse_sntp_response(
    packet: bytes,
    request_timestamp: bytes,
    sent_at: float,
    received_at: float,
) -> tuple[float, float]:
    """Return `(clock_offset_seconds, round_trip_seconds)` for a reply."""
    if len(packet) < NTP_PACKET_SIZE:
        raise ValueError("short SNTP response")
    mode = packet[0] & 0x07
    stratum = packet[1]
    if mode not in (4, 5) or not 1 <= stratum <= 15:
        raise ValueError("invalid SNTP server response")
    if packet[24:32] != request_timestamp:
        raise ValueError("SNTP originate timestamp mismatch")

    server_received = _decode_ntp_timestamp(packet[32:40])
    server_sent = _decode_ntp_timestamp(packet[40:48])
    offset = ((server_received - sent_at) + (server_sent - received_at)) / 2.0
    round_trip = (received_at - sent_at) - (server_sent - server_received)
    return offset, max(0.0, round_trip)


def query_sntp(server: str, timeout: float = 1.0) -> tuple[float, float]:
    # DNS lookup is intentionally outside the four-timestamp measurement.
    # Including resolver latency would bias the calculated clock offset.
    address = socket.gethostbyname(server)

    with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as sock:
        sock.settimeout(timeout)
        sent_at = time.time()
        request_timestamp = _encode_ntp_timestamp(sent_at)
        request = bytearray(NTP_PACKET_SIZE)
        request[0] = 0x23  # LI=0, version=4, client mode.
        request[40:48] = request_timestamp
        sock.sendto(request, (address, 123))
        packet, _address = sock.recvfrom(512)
    received_at = time.time()
    return parse_sntp_response(
        packet, request_timestamp, sent_at, received_at,
    )


class NetworkTimeSynchronizer:
    """Maintain a UTC correction without changing the operating-system clock."""

    def __init__(
        self,
        servers=DEFAULT_SERVERS,
        refresh_seconds: float = 300.0,
        stale_seconds: float = 900.0,
        retry_seconds: float = 30.0,
    ):
        self.servers = tuple(servers)
        self.refresh_seconds = refresh_seconds
        self.stale_seconds = stale_seconds
        self.retry_seconds = retry_seconds
        self._offset_seconds = None
        self._synchronized_at = None
        self._lock = threading.Lock()
        self._stop = threading.Event()
        self._thread = None

    def start(self) -> None:
        if self._thread is not None and self._thread.is_alive():
            return
        self._stop.clear()
        self._thread = threading.Thread(
            target=self._run, name="nkr-time-sync", daemon=True,
        )
        self._thread.start()

    def stop(self) -> None:
        self._stop.set()
        if self._thread is not None:
            self._thread.join(timeout=2.0)

    def now_ms(self) -> int | None:
        with self._lock:
            offset = self._offset_seconds
            synchronized_at = self._synchronized_at
        if offset is None or synchronized_at is None:
            return None
        if time.monotonic() - synchronized_at > self.stale_seconds:
            return None
        return round((time.time() + offset) * 1000)

    def _run(self) -> None:
        while not self._stop.is_set():
            samples = []
            for server in self.servers:
                if self._stop.is_set():
                    return
                try:
                    offset, round_trip = query_sntp(server)
                    samples.append((round_trip, offset, server))
                except (OSError, ValueError) as exc:
                    logger.warning("SNTP query failed for %s: %s", server, exc)
            if samples:
                round_trip, offset, server = min(samples)
                with self._lock:
                    self._offset_seconds = offset
                    self._synchronized_at = time.monotonic()
                logger.info(
                    "UTC synchronized via %s: offset=%+.1f ms, RTT=%.1f ms",
                    server, offset * 1000, round_trip * 1000,
                )
                delay = self.refresh_seconds
            else:
                delay = self.retry_seconds
            self._stop.wait(delay)

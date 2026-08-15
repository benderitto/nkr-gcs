"""Decode the capture timestamp embedded in NKR video frames."""

from collections.abc import Sequence


PREAMBLE = (1, 0, 1, 1, 0, 1, 0, 0)
TIMESTAMP_BITS = 12
BLOCK_WIDTH = 5
DATA_WIDTH = 4
MARKER_HEIGHT = 8
MARKER_WIDTH = (len(PREAMBLE) + TIMESTAMP_BITS) * BLOCK_WIDTH
TIMESTAMP_QUANTUM_MS = 10
MIN_CONTRAST = 80.0
MAX_VALID_LATENCY_MS = 10_000


def decode_timestamp_ticks(levels: Sequence[float]) -> int | None:
    """Decode Gray-coded Unix-centisecond ticks modulo the marker period."""
    expected = len(PREAMBLE) + TIMESTAMP_BITS
    if len(levels) < expected:
        return None

    white = [levels[index] for index, bit in enumerate(PREAMBLE) if bit]
    black = [levels[index] for index, bit in enumerate(PREAMBLE) if not bit]
    white_level = sum(white) / len(white)
    black_level = sum(black) / len(black)
    if white_level - black_level < MIN_CONTRAST:
        return None
    threshold = (white_level + black_level) / 2.0

    decoded_preamble = tuple(
        int(levels[index] >= threshold) for index in range(len(PREAMBLE))
    )
    if decoded_preamble != PREAMBLE:
        return None

    gray = 0
    offset = len(PREAMBLE)
    for bit in range(TIMESTAMP_BITS):
        if levels[offset + bit] >= threshold:
            gray |= 1 << bit

    binary = gray
    shifted = gray >> 1
    while shifted:
        binary ^= shifted
        shifted >>= 1
    return binary


def measure_video_latency_ms(
    levels: Sequence[float],
    synchronized_now_ms: int | None,
) -> int | None:
    """Return the signed clock delta for diagnostics and validation."""
    if synchronized_now_ms is None:
        return None
    captured_ticks = decode_timestamp_ticks(levels)
    if captured_ticks is None:
        return None
    now_ticks = synchronized_now_ms // TIMESTAMP_QUANTUM_MS
    period = 1 << TIMESTAMP_BITS
    cycle_start = now_ticks - (now_ticks % period)
    candidates = (
        cycle_start + captured_ticks,
        cycle_start + captured_ticks - period,
        cycle_start + captured_ticks + period,
    )
    reconstructed_ticks = min(
        candidates, key=lambda candidate: abs(now_ticks - candidate),
    )
    captured_ms = reconstructed_ticks * TIMESTAMP_QUANTUM_MS
    return synchronized_now_ms - captured_ms


def calculate_video_latency_ms(
    levels: Sequence[float],
    synchronized_now_ms: int | None,
) -> int | None:
    """Return capture-to-display delay, rejecting impossible timestamps."""
    latency = measure_video_latency_ms(levels, synchronized_now_ms)
    if latency is None or latency <= 0 or latency > MAX_VALID_LATENCY_MS:
        return None
    return latency

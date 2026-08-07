"""
Axis encoding/decoding helpers.
"""

from .constants import AXIS_SCALE, AXIS_MIN, AXIS_MAX


def clamp(value: float,
          minimum: float,
          maximum: float) -> float:

    return max(minimum, min(maximum, value))


def encode_axis(value: float) -> int:
    """
    Convert normalized axis [-1.0..1.0]
    into protocol int16.
    """

    value = clamp(value, AXIS_MIN, AXIS_MAX)

    return int(round(value * AXIS_SCALE))


def decode_axis(value: int) -> float:
    """
    Convert protocol int16
    into normalized float.
    """

    value = max(
        int(AXIS_MIN * AXIS_SCALE),
        min(
            int(AXIS_MAX * AXIS_SCALE),
            value,
        ),
    )

    return value / AXIS_SCALE

"""Pure native-video configuration helpers (no Qt dependency)."""

from urllib.parse import urlunparse

CAMERA_STREAMS = ("cam_front", "cam_rear", "cam_night", "cam_thermal")
RETRY_BACKOFF_SECONDS = (1, 2, 5, 10)


def build_stream_url(host: str, port: int, stream: str) -> str:
    """Build the sole permitted MediaMTX RTSP URL."""
    if stream not in CAMERA_STREAMS:
        raise ValueError(f"Unknown camera stream: {stream}")
    if not host or not isinstance(port, int) or not 1 <= port <= 65535:
        raise ValueError("Invalid video host or port")
    return urlunparse(("rtsp", f"{host}:{port}", f"/{stream}", "", "", ""))


def retry_delay(attempt: int) -> int:
    return RETRY_BACKOFF_SECONDS[min(max(attempt, 0), len(RETRY_BACKOFF_SECONDS) - 1)]


def stream_changed(current: str | None, requested: str) -> bool:
    """Validate a stream selection and report whether it needs reconnecting."""
    if requested not in CAMERA_STREAMS:
        raise ValueError(f"Unknown camera stream: {requested}")
    return requested != current

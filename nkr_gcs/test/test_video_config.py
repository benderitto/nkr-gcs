import pytest

from nkr_gcs.video.video_config import (
    CAMERA_STREAMS, build_stream_url, retry_delay, stream_changed,
)


def test_whitelisted_stream_url_builder():
    assert build_stream_url("100.72.220.66", 8554, "cam_front") == (
        "rtsp://100.72.220.66:8554/cam_front"
    )
    assert set(CAMERA_STREAMS) == {
        "cam_front", "cam_rear", "cam_night", "cam_thermal",
    }


def test_unknown_stream_is_rejected():
    with pytest.raises(ValueError, match="Unknown camera stream"):
        build_stream_url("192.168.1.24", 8889, "https://evil.example/")


def test_retry_backoff_caps_at_ten_seconds():
    assert [retry_delay(attempt) for attempt in range(6)] == [1, 2, 5, 10, 10, 10]


def test_same_stream_does_not_require_reconnect():
    assert stream_changed("cam_front", "cam_front") is False
    assert stream_changed("cam_front", "cam_rear") is True

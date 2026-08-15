from io import BytesIO
import os
from pathlib import Path
import threading

import pytest

from nkr_gcs.video.gstreamer_process import (
    build_gstreamer_command,
    gstreamer_environment,
)
from nkr_gcs.video.video_widget import VideoWidget


def test_gstreamer_command_is_bounded_and_uses_configured_dimensions():
    command = build_gstreamer_command(
        Path("gst-launch-1.0.exe"),
        "rtsp://100.72.220.66:8554/cam_front",
        1920,
        1080,
    )

    assert "latency=0" in command
    assert "drop-on-latency=true" in command
    assert "leaky=downstream" in command
    assert "max-size-buffers=1" in command
    assert "video/x-raw,format=RGB,width=1920,height=1080" in command
    assert command[-4:] == ["fdsink", "fd=1", "sync=false", "async=false"]


def test_gstreamer_command_rejects_unbounded_dimensions():
    with pytest.raises(ValueError, match="dimensions"):
        build_gstreamer_command(Path("gst-launch-1.0"), "rtsp://robot/cam", 0, 480)


def test_private_gstreamer_environment_uses_adjacent_plugins(tmp_path):
    executable = tmp_path / "gstreamer" / "bin" / "gst-launch-1.0.exe"
    executable.parent.mkdir(parents=True)
    executable.touch()
    plugins = tmp_path / "gstreamer" / "lib" / "gstreamer-1.0"
    plugins.mkdir(parents=True)

    environment = gstreamer_environment(executable)

    assert environment["PATH"].split(os.pathsep)[0] == str(executable.parent)
    assert environment["GST_PLUGIN_SYSTEM_PATH_1_0"] == str(plugins)
    assert environment["GST_PLUGIN_PATH_1_0"] == ""


def test_raw_frame_reader_returns_one_complete_frame():
    stop_event = threading.Event()
    assert VideoWidget._read_exact(BytesIO(b"abcdef"), 6, stop_event) == b"abcdef"
    assert VideoWidget._read_exact(BytesIO(b"abc"), 6, stop_event) is None


def test_diagnostic_pipe_reader_keeps_subprocess_output():
    chunks = []
    VideoWidget._drain_pipe(BytesIO(b"gstreamer error"), chunks)
    assert b"".join(chunks) == b"gstreamer error"

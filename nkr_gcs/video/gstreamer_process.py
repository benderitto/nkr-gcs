"""Locate and launch the private GStreamer runtime used by Windows builds."""

import os
from pathlib import Path
import shutil
import sys


def find_gst_launch() -> Path | None:
    """Return the bundled/system gst-launch executable, if available."""
    override = os.environ.get("NKR_GCS_GST_LAUNCH")
    if override:
        candidate = Path(override).expanduser()
        return candidate if candidate.is_file() else None

    bundle_root = Path(getattr(sys, "_MEIPASS", Path(__file__).resolve().parents[2]))
    names = ("gst-launch-1.0.exe", "gst-launch-1.0")
    for name in names:
        candidate = bundle_root / "gstreamer" / "bin" / name
        if candidate.is_file():
            return candidate

    system = shutil.which("gst-launch-1.0")
    return Path(system) if system else None


def gstreamer_environment(executable: Path) -> dict[str, str]:
    """Build a private plugin/DLL search environment for gst-launch."""
    environment = os.environ.copy()
    bin_dir = executable.parent
    root = bin_dir.parent
    plugin_dir = root / "lib" / "gstreamer-1.0"
    environment["PATH"] = str(bin_dir) + os.pathsep + environment.get("PATH", "")
    if plugin_dir.is_dir():
        environment["GST_PLUGIN_SYSTEM_PATH_1_0"] = str(plugin_dir)
        environment["GST_PLUGIN_PATH_1_0"] = ""
    environment.setdefault("GST_DEBUG", "1")
    return environment


def build_gstreamer_command(
    executable: Path,
    url: str,
    width: int,
    height: int,
) -> list[str]:
    """Return a bounded-latency raw-RGB pipeline for the Windows helper."""
    if not 1 <= width <= 7680 or not 1 <= height <= 4320:
        raise ValueError("Invalid video dimensions")
    caps = f"video/x-raw,format=RGB,width={width},height={height}"
    return [
        str(executable), "-q",
        "rtspsrc", f"location={url}", "protocols=tcp", "latency=0",
        "drop-on-latency=true", "tcp-timeout=3000000",
        "!", "rtph264depay",
        "!", "h264parse",
        "!", "avdec_h264", "max-threads=1",
        "!", "videoconvert", "n-threads=1",
        "!", caps,
        "!", "queue", "leaky=downstream", "max-size-buffers=1",
        "max-size-bytes=0", "max-size-time=0",
        "!", "fdsink", "fd=1", "sync=false", "async=false",
    ]

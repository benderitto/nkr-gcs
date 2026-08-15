"""Small dependency-free loader for the cross-platform GCS settings file."""

from dataclasses import dataclass
import os
from pathlib import Path
import sys


@dataclass(frozen=True)
class Settings:
    robot_host: str = "100.72.220.66"
    robot_port: int = 9999
    control_rate_hz: int = 50
    video_enabled: bool = True
    video_host: str | None = None
    video_port: int = 8554
    video_default_stream: str = "cam_front"
    video_low_latency_mode: bool = True
    video_width: int = 640
    video_height: int = 480
    input_device: str = "steamdeck"

    def __post_init__(self):
        if self.video_host is None:
            object.__setattr__(self, "video_host", self.robot_host)
        if not 1 <= self.video_width <= 7680 or not 1 <= self.video_height <= 4320:
            raise ValueError("Invalid configured video dimensions")


def load_settings(path: Path | None = None) -> Settings:
    path = path or settings_path()
    if not path.exists():
        _write_default_settings(path)
    values = {}
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        key, value = line.split(":", maxsplit=1)
        values[key.strip()] = value.strip()
    robot_host = values.get("robot_host", Settings.robot_host)
    return Settings(
        robot_host=robot_host,
        robot_port=int(values.get("robot_port", Settings.robot_port)),
        control_rate_hz=int(values.get("control_rate_hz", Settings.control_rate_hz)),
        video_enabled=_as_bool(values.get("video_enabled", Settings.video_enabled)),
        video_host=values.get("video_host", robot_host),
        video_port=int(values.get("video_port", Settings.video_port)),
        video_default_stream=values.get("video_default_stream", Settings.video_default_stream),
        video_low_latency_mode=_as_bool(
            values.get("video_low_latency_mode", Settings.video_low_latency_mode),
        ),
        video_width=int(values.get("video_width", Settings.video_width)),
        video_height=int(values.get("video_height", Settings.video_height)),
        input_device=values.get("input_device", Settings.input_device),
    )


def settings_path() -> Path:
    """Return a persistent per-user path on Linux, SteamOS, and Windows."""
    override = os.environ.get("NKR_GCS_CONFIG")
    if override:
        return Path(override).expanduser()
    if sys.platform == "win32":
        root = Path(os.environ.get("APPDATA", Path.home() / "AppData/Roaming"))
        return root / "NKR-GCS" / "settings.yaml"
    root = Path(os.environ.get("XDG_CONFIG_HOME", Path.home() / ".config"))
    return root / "nkr-gcs" / "settings.yaml"


def _write_default_settings(path: Path) -> None:
    defaults = Settings()
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        "# NKR GCS user configuration\n"
        f"robot_host: {defaults.robot_host}\n"
        f"robot_port: {defaults.robot_port}\n"
        f"control_rate_hz: {defaults.control_rate_hz}\n"
        f"video_enabled: {str(defaults.video_enabled).lower()}\n"
        f"video_host: {defaults.video_host}\n"
        f"video_port: {defaults.video_port}\n"
        f"video_default_stream: {defaults.video_default_stream}\n"
        f"video_low_latency_mode: {str(defaults.video_low_latency_mode).lower()}\n"
        f"video_width: {defaults.video_width}\n"
        f"video_height: {defaults.video_height}\n"
        f"input_device: {defaults.input_device}\n",
        encoding="utf-8",
    )


def save_setting(key: str, value: str, path: Path | None = None) -> None:
    """Update one scalar setting without discarding user-owned values."""
    path = path or settings_path()
    if not path.exists():
        _write_default_settings(path)
    lines = path.read_text(encoding="utf-8").splitlines()
    prefix = f"{key}:"
    replacement = f"{key}: {value}"
    for index, line in enumerate(lines):
        if line.strip().startswith(prefix):
            lines[index] = replacement
            break
    else:
        lines.append(replacement)
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def _as_bool(value) -> bool:
    if isinstance(value, bool):
        return value
    if str(value).lower() in ("true", "yes", "1"):
        return True
    if str(value).lower() in ("false", "no", "0"):
        return False
    raise ValueError(f"Invalid boolean setting: {value!r}")

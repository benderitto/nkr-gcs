"""Run GCS from a source checkout or its isolated Flatpak."""

import importlib.util
import os
import shutil
import subprocess
import sys
from pathlib import Path

# nkr_protocol is a standalone ROS Python package kept in this repository.
# Add its package root when running without an installed workspace overlay.
_ROOT = Path(__file__).resolve().parent
_PROTOCOL_ROOT = _ROOT / "nkr_protocol"
if str(_PROTOCOL_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROTOCOL_ROOT))

FLATPAK_APP_ID = "ua.nkr.GCS"
GRAPHICAL_ENVIRONMENT = (
    "DISPLAY", "WAYLAND_DISPLAY", "XDG_RUNTIME_DIR", "DBUS_SESSION_BUS_ADDRESS",
)


def _host_dependencies_available() -> bool:
    return importlib.util.find_spec("PySide6") is not None


def _flatpak_is_installed() -> bool:
    if sys.platform == "win32" or shutil.which("flatpak") is None:
        return False
    result = subprocess.run(
        ["flatpak", "info", FLATPAK_APP_ID],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        check=False,
    )
    return result.returncode == 0


def _inherit_graphical_session_environment() -> None:
    """Allow an SSH invocation to open the app in the logged-in Deck session."""
    if os.environ.get("DISPLAY") or os.environ.get("WAYLAND_DISPLAY"):
        return
    result = subprocess.run(
        ["systemctl", "--user", "show-environment"],
        capture_output=True,
        text=True,
        check=False,
    )
    if result.returncode != 0:
        return
    allowed = set(GRAPHICAL_ENVIRONMENT)
    for line in result.stdout.splitlines():
        key, separator, value = line.partition("=")
        if separator and key in allowed:
            os.environ[key] = value


def main() -> None:
    if not _host_dependencies_available() and _flatpak_is_installed():
        print("System Python has no GCS UI dependencies; launching the Flatpak.")
        _inherit_graphical_session_environment()
        os.execvp("flatpak", ["flatpak", "run", FLATPAK_APP_ID])

    try:
        from nkr_gcs.app import main as app_main
    except ModuleNotFoundError as exc:
        if exc.name in {"PySide6", "sdl2", "gi"}:
            raise SystemExit(
                f"Missing development dependency: {exc.name}. "
                "Install the project environment as described in INSTALL.md, "
                f"or install the {FLATPAK_APP_ID} Flatpak."
            ) from exc
        raise
    app_main()


if __name__ == "__main__":
    main()

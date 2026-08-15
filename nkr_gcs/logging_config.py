"""Persistent diagnostics for graphical and packaged GCS builds."""

from logging.handlers import RotatingFileHandler
import logging
from pathlib import Path
import sys

from .settings import settings_path


LOG_FILENAME = "nkr-gcs.log"


def log_path() -> Path:
    """Keep the log beside settings in the platform user-data directory."""
    return settings_path().parent / LOG_FILENAME


def configure_logging(path: Path | None = None) -> Path:
    """Send diagnostics to a bounded file, including for windowed executables."""
    path = path or log_path()
    path.parent.mkdir(parents=True, exist_ok=True)

    root = logging.getLogger()
    root.setLevel(logging.INFO)
    formatter = logging.Formatter(
        "%(asctime)s %(levelname)s %(name)s: %(message)s",
    )

    # main() is normally called once, but avoiding duplicate handlers makes
    # source-level tests and embedded launchers deterministic.
    resolved = path.resolve()
    for handler in root.handlers:
        if isinstance(handler, logging.FileHandler):
            if Path(handler.baseFilename).resolve() == resolved:
                return path

    handler = RotatingFileHandler(
        path,
        maxBytes=2 * 1024 * 1024,
        backupCount=2,
        encoding="utf-8",
    )
    handler.setFormatter(formatter)
    root.addHandler(handler)

    # Source launches retain terminal output. A PyInstaller --windowed build
    # has no stderr, so the persistent file above is its primary diagnostic.
    if sys.stderr is not None and not any(
        isinstance(item, logging.StreamHandler)
        and not isinstance(item, logging.FileHandler)
        for item in root.handlers
    ):
        console = logging.StreamHandler()
        console.setFormatter(formatter)
        root.addHandler(console)
    return path

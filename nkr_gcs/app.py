import sys
import logging
import os
import platform

from PySide6.QtCore import QTimer
from PySide6.QtWidgets import QApplication

from .main_window import MainWindow
from .application import Application
from .logging_config import configure_logging
from .settings import settings_path


def main():
    diagnostic_log = configure_logging()
    logger = logging.getLogger(__name__)
    logger.info(
        "NKR GCS starting (platform=%s, python=%s, frozen=%s)",
        platform.platform(), platform.python_version(),
        bool(getattr(sys, "frozen", False)),
    )
    logger.info("Settings: %s", settings_path())
    logger.info("Diagnostic log: %s", diagnostic_log)

    app = QApplication(sys.argv)

    window = MainWindow()
    controller = Application(window)
    app.aboutToQuit.connect(controller.close)

    smoke_exit_ms = os.environ.get("NKR_GCS_SMOKE_EXIT_MS")
    if smoke_exit_ms:
        QTimer.singleShot(int(smoke_exit_ms), app.quit)

    try:
        exit_code = app.exec()
    finally:
        controller.close()
    sys.exit(exit_code)

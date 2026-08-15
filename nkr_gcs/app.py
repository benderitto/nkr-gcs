import sys
import logging

from PySide6.QtWidgets import QApplication

from .main_window import MainWindow
from .application import Application


def main():

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(message)s",
    )

    app = QApplication(sys.argv)

    window = MainWindow()
    controller = Application(window)
    app.aboutToQuit.connect(controller.close)

    sys.exit(app.exec())

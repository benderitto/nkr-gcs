from PySide6.QtCore import QObject, QTimer

from .model.operator_model import OperatorModel
from .input.input_manager import InputManager


class Application(QObject):

    def __init__(self, window):

        super().__init__()

        self.window = window

        self.operator = OperatorModel()

        self.input = InputManager()

        #
        # Main loop (100 Hz)
        #

        self.timer = QTimer()

        self.timer.timeout.connect(self.update)

        self.timer.start(10)

    def update(self):

        #
        # Read controller
        #

        self.input.update(
            self.operator
        )

        #
        # Update GUI
        #

        self.window.update(self.operator)
from PySide6.QtWidgets import (
    QMainWindow,
    QWidget,
)

from .video.video_widget import VideoWidget
from .hud.hud_widget import HUDWidget
from .hud.popup_widget import PopupWidget

from .model.robot_model import RobotModel
from .model.operator_model import OperatorModel
from .input.input_manager import InputManager
from PySide6.QtCore import QTimer
from .network.network_manager import NetworkManager


class MainWindow(QMainWindow):

    def __init__(self):

        super().__init__()

        self.setWindowTitle("NKR Ground Control Station")

        self.resize(1280, 800)

        #
        # Shared application state.
        #

        self.robot = RobotModel()
        
        self.operator = OperatorModel()
        
        self.input = InputManager()
        
        self.network = NetworkManager()
        
        self.timer = QTimer(self)

        self.timer.timeout.connect(self.update)

        self.timer.start(10)

        #
        # Central container.
        #

        container = QWidget()

        self.setCentralWidget(container)

        #
        # Video.
        #

        self.video = VideoWidget(container)

        #
        # HUD.
        #

        self.hud = HUDWidget(container)
        
        #
        # Popup notifications
        #

        self.popup = PopupWidget(container)

        #
        # Передаємо HUD доступ до стану.
        #

        self.hud.robot = self.robot
        
        self.popup.show_message(
        "NKR READY"
        )

    def resizeEvent(self, event):

        super().resizeEvent(event)

        rect = self.centralWidget().rect()

        self.video.setGeometry(rect)

        self.hud.setGeometry(rect)
        
        self.popup.setGeometry(rect)
    
    def update(self):

        #
        # Read operator input
        #

        self.input.update(
            self.operator
        )

        self.network.update(
            self.operator
        )

        #
        # Refresh HUD
        #

        self.hud.update()
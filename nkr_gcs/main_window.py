from PySide6.QtWidgets import (
    QMainWindow,
    QWidget,
)
from PySide6.QtCore import Qt

from .video.video_widget import VideoWidget
from .hud.hud_widget import HUDWidget
from .hud.popup_widget import PopupWidget
from .hud.osd_menu import OSDMenu

from .model.robot_model import RobotModel


class MainWindow(QMainWindow):

    def __init__(self):

        super().__init__()

        self.setWindowTitle("NKR Ground Control Station")

        self.resize(1280, 800)

        #
        # Shared application state.
        #

        self.robot = RobotModel()
        
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
        self.osd_menu = OSDMenu(container)

        #
        # Передаємо HUD доступ до стану.
        #

        self.hud.state = self.robot
        
        self.popup.show_message(
        "NKR READY"
        )

    def resizeEvent(self, event):

        super().resizeEvent(event)

        rect = self.centralWidget().rect()

        self.video.setGeometry(rect)

        self.hud.setGeometry(rect)
        
        self.popup.setGeometry(rect)
        self.osd_menu.setGeometry(rect)

    def closeEvent(self, event):
        # Stop pending WebRTC reconnects even if this is not the final Qt window.
        self.video.close()
        super().closeEvent(event)

    def enter_kiosk_mode(self):
        """Fullscreen presentation: no desktop panels or competing windows."""
        self.setWindowFlag(Qt.WindowStaysOnTopHint, True)
        self.setWindowFlag(Qt.FramelessWindowHint, True)
        self.showFullScreen()
        self.raise_()
        self.activateWindow()

    def enter_desktop_mode(self):
        """Release kiosk presentation so Steam Deck desktop remains accessible."""
        self.setWindowFlag(Qt.WindowStaysOnTopHint, False)
        self.setWindowFlag(Qt.FramelessWindowHint, False)
        self.showNormal()

    def refresh(self, operator):
        """Refresh visual components from the application-owned state."""
        self.hud.update()

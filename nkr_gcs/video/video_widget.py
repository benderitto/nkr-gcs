from PySide6.QtWidgets import QWidget


class VideoWidget(QWidget):

    def __init__(self, parent=None):

        super().__init__(parent)

        self.setStyleSheet("""
            background-color: black;
        """)
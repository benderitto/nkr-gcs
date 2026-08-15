"""Touch-friendly hierarchical in-flight OSD menu overlay."""

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import QFrame, QLabel, QPushButton, QVBoxLayout, QWidget
import logging

from nkr_protocol.constants import (
    MODE_CRAB, MODE_FRONT_DRIVE, MODE_FRONT_STEER, MODE_REAR_DRIVE, MODE_TANK,
)

logger = logging.getLogger(__name__)


LANGUAGES = {
    "en": {"root": "GCS MENU", "drive": "DRIVE MODE", "camera": "CAM MODE",
           "light": "LIGHT MODE", "network": "NETWORK", "platform": "PLATFORM SETTINGS",
           "app": "APP SETTINGS", "language": "LANGUAGE", "pending": "NOT AVAILABLE ON ROBOT"},
    "uk": {"root": "МЕНЮ GCS", "drive": "РЕЖИМ РУХУ", "camera": "РЕЖИМ КАМЕРИ",
           "light": "РЕЖИМ ОСВІТЛЕННЯ", "network": "МЕРЕЖА", "platform": "НАЛАШТУВАННЯ ПЛАТФОРМИ",
           "app": "НАЛАШТУВАННЯ ДОДАТКУ", "language": "МОВА", "pending": "НЕДОСТУПНО НА НРК"},
    "qya": {"root": "GCS MÁNA", "drive": "RÁTE MÁQUA", "camera": "CENYEL RÁTE",
            "light": "CALMA RÁTE", "network": "RAHTA", "platform": "PALANTÍR SETTINGS",
            "app": "APP SETTINGS", "language": "LAMBË", "pending": "ÚVA NÁ NKR"},
}


class OSDMenu(QWidget):
    visibility_changed = Signal(bool)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.language = "en"
        self._callbacks = {}
        self._stack = ["root"]
        self.selected_index = 0
        self.entries = []
        self.button = QPushButton("☰", self)
        self.button.setAccessibleName("Open GCS menu")
        # SDL is read directly by InputManager.  Menu buttons must therefore
        # never acquire keyboard focus or react to a Steam Input keyboard
        # emulation event (for example a synthetic Y key).
        self.button.setFocusPolicy(Qt.NoFocus)
        self.button.setFixedSize(58, 52)
        self.button.setStyleSheet("QPushButton { color:white; background:rgba(20,26,32,185); border:1px solid rgba(255,255,255,90); border-radius:12px; font-size:29px; font-weight:600; }")
        self.button.clicked.connect(lambda: self.toggle(source="touch"))
        self.panel = QFrame(self)
        self.panel.setStyleSheet("QFrame { background:rgba(16,21,27,235); border-radius:14px; border:1px solid rgba(255,255,255,60); } QLabel { color:white; }")
        self.layout = QVBoxLayout(self.panel)
        self.layout.setContentsMargins(24, 20, 24, 20)
        self.layout.setSpacing(10)
        self.title = QLabel()
        self.title.setStyleSheet("font-size:18px; font-weight:700;")
        self.layout.addWidget(self.title)
        self.status = QLabel("")
        self.status.setStyleSheet("color:rgba(255,255,255,180); font-size:13px;")
        self.layout.addWidget(self.status)
        self.items = []
        self._render()
        self.panel.hide()

    @property
    def is_open(self):
        return self.panel.isVisible()

    def set_callbacks(self, **callbacks):
        self._callbacks.update(callbacks)

    def toggle(self, source="local"):
        logger.info("OSD menu toggle source=%s open=%s", source, not self.is_open)
        self.set_open(not self.is_open)

    def set_open(self, open_):
        if open_:
            self._stack = ["root"]
            self.selected_index = 0
            self._render()
            self.panel.show()
        else:
            self.panel.hide()
        self.visibility_changed.emit(open_)

    def navigate(self, delta):
        self.selected_index = (self.selected_index + delta) % len(self.entries)
        self._update_selection()

    def adjust(self, _direction):
        pass  # Reserved for slider entries.

    def activate(self, index=None):
        if index is not None:
            self.selected_index = index
        entry = self.entries[self.selected_index]
        if entry[0] == "page":
            logger.info("OSD menu open page=%s", entry[1])
            self._stack.append(entry[1])
            self.selected_index = 0
            self._render()
        elif entry[0] == "action":
            logger.info("OSD menu action=%s value=%s", entry[1], entry[2])
            callback = self._callbacks.get(entry[1])
            if callback:
                callback(entry[2])
            self.set_open(False)
        else:
            self.status.setText(self._t("pending"))

    def back(self):
        if len(self._stack) == 1:
            self.set_open(False)
        else:
            self._stack.pop()
            self.selected_index = 0
            self._render()

    def _t(self, key):
        return LANGUAGES[self.language][key]

    def _menu_entries(self, page):
        if page == "root":
            return [("page", "drive", self._t("drive")), ("page", "camera", self._t("camera")),
                    ("page", "light", self._t("light")), ("page", "network", self._t("network")),
                    ("page", "platform", self._t("platform")), ("page", "app", self._t("app"))]
        if page == "drive":
            return [("action", "drive", mode, name) for mode, name in ((MODE_FRONT_STEER, "FRONT STEER"), (MODE_TANK, "TANK"), (MODE_CRAB, "CRAB"), (MODE_FRONT_DRIVE, "FRONT DRIVE"), (MODE_REAR_DRIVE, "REAR DRIVE"))]
        if page == "camera":
            return [("action", "camera", stream, name) for stream, name in (("cam_front", "FRONT"), ("cam_rear", "REAR"), ("cam_night", "NIGHT"), ("cam_thermal", "THERMAL"))]
        if page == "app":
            return [("page", "language", self._t("language"))]
        if page == "language":
            return [("action", "language", code, label) for code, label in (("en", "English (USA)"), ("uk", "Українська"), ("qya", "Quenya / qya"))]
        if page == "light":
            labels = ("LOW BEAM", "HIGH BEAM", "SEARCHLIGHT", "PARKING LIGHTS", "DARK MODE")
        elif page == "network":
            labels = ("LTE", "STARLINK")
        else:
            labels = ("RESTART NODES", "REBOOT PLATFORM")
        return [("pending", label) for label in labels]

    def _render(self):
        self.entries = self._menu_entries(self._stack[-1])
        self.title.setText(self._t("root") if self._stack[-1] == "root" else self._entry_label(self._stack[-1]))
        self.status.setText("")
        for item in self.items:
            self.layout.removeWidget(item)
            item.deleteLater()
        self.items = []
        for index, entry in enumerate(self.entries):
            item = QPushButton(entry[-1])
            item.setFocusPolicy(Qt.NoFocus)
            item.setFixedHeight(50)
            item.clicked.connect(lambda checked=False, i=index: self.activate(i))
            self.items.append(item)
            self.layout.addWidget(item)
        self._update_selection()

    def _entry_label(self, page):
        return {"drive": self._t("drive"), "camera": self._t("camera"), "light": self._t("light"), "network": self._t("network"), "platform": self._t("platform"), "app": self._t("app"), "language": self._t("language")}[page]

    def _update_selection(self):
        for index, item in enumerate(self.items):
            selected = index == self.selected_index
            item.setStyleSheet(f"QPushButton {{ color:white; text-align:left; padding-left:18px; background:{'rgba(65,146,224,205)' if selected else 'rgba(255,255,255,17)'}; border:1px solid {'rgba(255,255,255,195)' if selected else 'transparent'}; border-radius:9px; font-size:17px; font-weight:600; }}")

    def set_language(self, code):
        self.language = code
        self._render()

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self.button.move(self.width() - self.button.width() - 18, 16)
        self.panel.setGeometry(self.width() - 622, 78, 604, 470)

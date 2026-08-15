"""Touch-friendly DJI-inspired hierarchical in-flight side panel."""

import logging

from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QColor, QPainter
from PySide6.QtWidgets import (
    QFrame, QHBoxLayout, QLabel, QPushButton, QVBoxLayout, QWidget,
)

from nkr_protocol.constants import (
    MODE_CRAB, MODE_FRONT_DRIVE, MODE_FRONT_STEER, MODE_REAR_DRIVE, MODE_TANK,
)

logger = logging.getLogger(__name__)

LANGUAGES = {
    "en": {"root": "GCS MENU", "drive": "DRIVE MODE", "camera": "CAM MODE",
           "light": "LIGHT MODE", "network": "NETWORK", "platform": "PLATFORM SETTINGS",
           "app": "APP SETTINGS", "language": "LANGUAGE", "input_device": "INPUT DEVICE",
           "pending": "NOT AVAILABLE ON ROBOT"},
    "uk": {"root": "МЕНЮ GCS", "drive": "РЕЖИМ РУХУ", "camera": "РЕЖИМ КАМЕРИ",
           "light": "РЕЖИМ ОСВІТЛЕННЯ", "network": "МЕРЕЖА", "platform": "НАЛАШТУВАННЯ ПЛАТФОРМИ",
           "app": "НАЛАШТУВАННЯ ДОДАТКУ", "language": "МОВА", "input_device": "ПРИСТРІЙ КЕРУВАННЯ",
           "pending": "НЕДОСТУПНО НА НРК"},
    "qya": {"root": "GCS MÁNA", "drive": "RÁTE MÁQUA", "camera": "CENYEL RÁTE",
            "light": "CALMA RÁTE", "network": "RAHTA", "platform": "PALANTÍR SETTINGS",
            "app": "APP SETTINGS", "language": "LAMBË", "input_device": "INPUT DEVICE",
            "pending": "ÚVA NÁ NKR"},
}

PAGE_ICONS = {
    "drive": "↔", "camera": "◉", "light": "☼", "network": "⌁",
    "platform": "◆", "app": "⚙", "input_device": "⌘", "language": "文",
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
        self.items = []
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)

        self.button = QPushButton("☰", self)
        self.button.setAccessibleName("Open GCS menu")
        self.button.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self.button.setFixedSize(58, 52)
        self.button.setStyleSheet(
            "QPushButton { color:white; background:rgba(7,11,14,205); "
            "border:1px solid rgba(255,255,255,65); border-radius:26px; "
            "font-size:26px; font-weight:500; } "
            "QPushButton:pressed { background:rgba(255,255,255,45); }"
        )
        self.button.clicked.connect(lambda: self.toggle(source="touch"))

        self.panel = QFrame(self)
        self.panel.setObjectName("menuPanel")
        self.panel.setStyleSheet(
            "QFrame#menuPanel { background:rgba(7,10,13,250); "
            "border-left:1px solid rgba(255,255,255,55); } "
            "QLabel { color:white; background:transparent; }"
        )
        self.layout = QVBoxLayout(self.panel)
        self.layout.setContentsMargins(30, 24, 28, 28)
        self.layout.setSpacing(5)

        header = QHBoxLayout()
        header.setSpacing(14)
        self.back_button = QPushButton("‹")
        self.back_button.setAccessibleName("Back")
        self.back_button.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self.back_button.setFixedSize(48, 48)
        self.back_button.setStyleSheet(
            "QPushButton { color:white; background:transparent; border:none; "
            "font-size:38px; font-weight:300; }"
        )
        self.back_button.clicked.connect(self.back)
        header.addWidget(self.back_button)
        self.title = QLabel()
        self.title.setStyleSheet("font-size:22px; font-weight:700; letter-spacing:1px;")
        header.addWidget(self.title, 1)
        header.addSpacing(58)
        self.layout.addLayout(header)

        self.status = QLabel("")
        self.status.setFixedHeight(28)
        self.status.setStyleSheet("color:rgba(255,255,255,155); font-size:12px; padding-left:62px;")
        self.layout.addWidget(self.status)
        self.items_container = QWidget()
        self.items_layout = QVBoxLayout(self.items_container)
        self.items_layout.setContentsMargins(0, 8, 0, 0)
        self.items_layout.setSpacing(0)
        self.layout.addWidget(self.items_container, 1)
        self.hint = QLabel("D-PAD  NAVIGATE     A  SELECT     B  BACK")
        self.hint.setFixedHeight(30)
        self.hint.setStyleSheet(
            "color:rgba(255,255,255,105); font-size:11px; letter-spacing:1px;"
        )
        self.layout.addWidget(self.hint)
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
            self.panel.raise_()
            self.button.setText("×")
            self.button.raise_()
        else:
            self.panel.hide()
            self.button.setText("☰")
        self.update()
        self.visibility_changed.emit(open_)

    def navigate(self, delta):
        self.selected_index = (self.selected_index + delta) % len(self.entries)
        self._update_selection()

    def adjust(self, _direction):
        pass

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
            return [("action", "drive", mode, name) for mode, name in
                    ((MODE_FRONT_STEER, "FRONT STEER"), (MODE_TANK, "TANK"),
                     (MODE_CRAB, "CRAB"), (MODE_FRONT_DRIVE, "FRONT DRIVE"),
                     (MODE_REAR_DRIVE, "REAR DRIVE"))]
        if page == "camera":
            return [("action", "camera", stream, name) for stream, name in
                    (("cam_front", "FRONT"), ("cam_rear", "REAR"),
                     ("cam_night", "NIGHT"), ("cam_thermal", "THERMAL"))]
        if page == "app":
            return [("page", "input_device", self._t("input_device")),
                    ("page", "language", self._t("language"))]
        if page == "input_device":
            return [("action", "input_device", code, label) for code, label in
                    (("steamdeck", "Steam Deck"), ("xbox", "Xbox Controller"),
                     ("dualsense", "DualSense"))]
        if page == "language":
            return [("action", "language", code, label) for code, label in
                    (("en", "English (USA)"), ("uk", "Українська"),
                     ("qya", "Quenya / qya"))]
        if page == "light":
            labels = ("LOW BEAM", "HIGH BEAM", "SEARCHLIGHT", "PARKING LIGHTS", "DARK MODE")
        elif page == "network":
            labels = ("LTE", "STARLINK")
        else:
            labels = ("RESTART NODES", "REBOOT PLATFORM")
        return [("pending", label) for label in labels]

    def _render(self):
        page = self._stack[-1]
        self.entries = self._menu_entries(page)
        self.title.setText(self._t("root") if page == "root" else self._entry_label(page))
        self.status.setText("")
        self.back_button.setVisible(page != "root")
        self.back_button.setText("‹")
        while self.items_layout.count():
            child = self.items_layout.takeAt(0)
            if child.widget() is not None:
                child.widget().hide()
                child.widget().deleteLater()
        self.items = []
        for index, entry in enumerate(self.entries):
            icon = PAGE_ICONS.get(entry[1], "○") if entry[0] == "page" else "○"
            suffix = "›" if entry[0] == "page" else ""
            item = QPushButton(f"{icon}    {entry[-1]}                                      {suffix}")
            item.setFocusPolicy(Qt.FocusPolicy.NoFocus)
            item.setFixedHeight(72)
            item.clicked.connect(lambda checked=False, i=index: self.activate(i))
            self.items.append(item)
            self.items_layout.addWidget(item)
        self.items_layout.addStretch(1)
        self._update_selection()

    def _entry_label(self, page):
        return {"drive": self._t("drive"), "camera": self._t("camera"),
                "light": self._t("light"), "network": self._t("network"),
                "platform": self._t("platform"), "app": self._t("app"),
                "language": self._t("language"),
                "input_device": self._t("input_device")}[page]

    def _update_selection(self):
        for index, item in enumerate(self.items):
            selected = index == self.selected_index
            item.setStyleSheet(
                "QPushButton { color:%s; text-align:left; padding-left:20px; "
                "background:%s; border:none; border-bottom:1px solid rgba(255,255,255,28); "
                "font-size:17px; font-weight:%s; }"
                % ("white" if selected else "rgba(255,255,255,220)",
                   "rgba(255,255,255,35)" if selected else "transparent",
                   "700" if selected else "500")
            )

    def set_language(self, code):
        self.language = code
        self._render()

    def paintEvent(self, event):
        if self.is_open:
            painter = QPainter(self)
            painter.fillRect(0, 0, max(0, self.width() - 560), self.height(),
                             QColor(0, 0, 0, 92))

    def resizeEvent(self, event):
        super().resizeEvent(event)
        panel_width = min(560, max(460, int(self.width() * 0.44)))
        self.panel.setGeometry(self.width() - panel_width, 0, panel_width, self.height())
        self.button.move(self.width() - self.button.width() - 18, 14)

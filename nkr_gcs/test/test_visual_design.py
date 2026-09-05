import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtGui import QImage
from PySide6.QtWidgets import QApplication

from nkr_gcs.hud.hud_widget import HUDWidget
from nkr_gcs.hud.osd_menu import OSDMenu
from nkr_gcs.main_window import MainWindow
from nkr_gcs.model.robot_model import RobotModel
from nkr_protocol.constants import (
    LIGHT_DARK, LIGHT_HIGH_BEAM, LIGHT_LOW_BEAM, LIGHT_PARKING,
    LIGHT_SEARCHLIGHT,
)


def _app():
    return QApplication.instance() or QApplication([])


def test_side_panel_uses_touch_sized_dji_layout():
    app = _app()
    menu = OSDMenu()
    menu.resize(1280, 800)
    menu.show()
    menu.set_open(True)
    app.processEvents()
    assert menu.panel.geometry().getRect() == (720, 0, 560, 800)
    assert len(menu.items) == 6
    assert all(item.height() == 72 for item in menu.items)
    assert menu.button.text() == "×"
    assert not menu.back_button.isVisible()
    menu.activate(0)
    app.processEvents()
    assert menu.back_button.isVisible()
    menu.close()


def test_hud_renders_armed_live_state():
    _app()
    hud = HUDWidget()
    hud.resize(1280, 800)
    hud.state = RobotModel(armed=True, video_state="LIVE", battery_percent=72)
    image = QImage(hud.size(), QImage.Format.Format_ARGB32)
    image.fill(0)
    hud.render(image)
    assert image.pixelColor(110, 40).alpha() > 0
    assert image.pixelColor(640, 40).alpha() > 0


def test_light_menu_exposes_real_mode_actions():
    _app()
    menu = OSDMenu()
    selected = []
    menu.set_callbacks(light=selected.append)
    menu._stack = ["root", "light"]
    menu._render()
    assert [entry[:3] for entry in menu.entries] == [
        ("action", "light", LIGHT_LOW_BEAM),
        ("action", "light", LIGHT_HIGH_BEAM),
        ("action", "light", LIGHT_SEARCHLIGHT),
        ("action", "light", LIGHT_PARKING),
        ("action", "light", LIGHT_DARK),
    ]
    menu.activate(4)
    assert selected == [LIGHT_DARK]
    menu.close()


def test_main_window_has_application_quit_shortcut():
    _app()
    window = MainWindow()

    assert window.quit_shortcut.key().toString() == "Ctrl+Shift+Q"
    window.close()

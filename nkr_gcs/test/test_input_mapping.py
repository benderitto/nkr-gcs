from nkr_gcs.input.controller import ControllerState
from nkr_gcs.input.mapping import InputMapping
from nkr_gcs.model.operator_model import OperatorModel
from nkr_protocol.constants import BUTTON_MENU, BUTTON_STEAM, BUTTON_VIEW
from nkr_protocol.constants import MODE_REAR_DRIVE


def test_mapping_clamps_axes_and_tracks_button_edges():
    mapping = InputMapping()
    operator = OperatorModel()
    controller = ControllerState(right_trigger=2.0, left_trigger=-2.0,
                                 left_x=-2.0, back=True, start=True, guide=True)
    mapping.update(controller, operator)
    assert (operator.throttle, operator.steering, operator.brake) == (1.0, -1.0, 0.0)
    assert operator.buttons == BUTTON_VIEW | BUTTON_MENU | BUTTON_STEAM
    assert operator.buttons_changed == operator.buttons
    mapping.update(controller, operator)
    assert operator.buttons_changed == 0


def test_steam_deck_safety_buttons_are_mapped_to_protocol_masks():
    mapping = InputMapping()
    operator = OperatorModel()
    mapping.update(ControllerState(back=True, start=True, guide=True), operator)
    expected = BUTTON_VIEW | BUTTON_MENU | BUTTON_STEAM
    assert operator.buttons == expected
    assert operator.buttons_changed == expected


def test_steam_deck_misc1_is_also_mapped_to_view():
    operator = OperatorModel()
    InputMapping().update(ControllerState(misc1=True), operator)
    assert operator.buttons == BUTTON_VIEW


def test_menu_can_set_persistent_drive_mode():
    mapping = InputMapping()
    mapping.mode_selector.set_mode(MODE_REAR_DRIVE)
    operator = OperatorModel()
    mapping.update(ControllerState(), operator)
    assert operator.requested_drive_mode == MODE_REAR_DRIVE


def test_xbox_short_menu_press_disarms_and_hold_arms():
    now = [10.0]
    mapping = InputMapping(input_device="xbox", clock=lambda: now[0])
    operator = OperatorModel()

    mapping.update(ControllerState(start=True), operator)
    assert operator.buttons == 0
    now[0] += 0.25
    mapping.update(ControllerState(), operator)
    assert operator.buttons == BUTTON_VIEW
    now[0] += 0.11
    mapping.update(ControllerState(), operator)
    assert operator.buttons == 0

    mapping.update(ControllerState(start=True), operator)
    now[0] += 1.99
    mapping.update(ControllerState(start=True), operator)
    assert operator.buttons == 0
    now[0] += 0.01
    mapping.update(ControllerState(start=True), operator)
    assert operator.buttons == BUTTON_MENU
    mapping.update(ControllerState(), operator)
    assert operator.buttons == 0  # A completed hold must not also disarm.


def test_dualsense_uses_same_safety_timing_as_xbox():
    now = [0.0]
    mapping = InputMapping(input_device="dualsense", clock=lambda: now[0])
    operator = OperatorModel()
    mapping.update(ControllerState(start=True), operator)
    now[0] = 2.0
    mapping.update(ControllerState(start=True, back=True), operator)
    assert operator.buttons == BUTTON_MENU

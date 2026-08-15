from nkr_gcs.input.controller import ControllerState
from nkr_gcs.input.input_manager import InputManager
from nkr_gcs.model.operator_model import OperatorModel


def test_menu_suppression_sends_neutral_operator_until_input_released():
    manager = InputManager.__new__(InputManager)
    manager.controller = ControllerState(dpad_up=True, a=True)
    manager._suppress_until_released = False
    operator = OperatorModel(throttle=1.0, steering=1.0, brake=1.0,
                             requested_drive_mode=2, buttons=123)
    manager.suppress_operator(operator)
    assert (operator.throttle, operator.steering, operator.brake,
            operator.requested_drive_mode, operator.buttons) == (0.0, 0.0, 0.0, 0, 0)
    assert manager._is_neutral() is False
    manager.controller = ControllerState()
    assert manager._is_neutral() is True


def test_menu_release_gate_ignores_analog_stick_drift():
    manager = InputManager.__new__(InputManager)
    manager.controller = ControllerState(left_x=0.18, right_trigger=0.04)

    assert manager._is_neutral() is True

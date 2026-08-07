from ..model.operator_model import OperatorModel

from .controller import ControllerState
from .mode_selector import ModeSelector


class InputMapping:
    """
    Converts controller state
    into operator commands.
    """

    def __init__(self):

        self.mode_selector = ModeSelector()

    def update(
        self,
        controller: ControllerState,
        operator: OperatorModel,
    ):
        print("NEW INPUT MAPPING")
        #
        # Driving
        #

        operator.throttle = (
            controller.right_trigger -
            controller.left_trigger
        )

        print(
            f"R2={controller.right_trigger:.2f} "
            f"L2={controller.left_trigger:.2f} "
            f"T={operator.throttle:.2f}"
        )
        
        #
        # Brake
        #

        operator.brake = 1.0 if controller.l1 else 0.0

        #
        # Steering
        #

        operator.steering = controller.left_x

        #
        # Drive mode
        #

        operator.requested_drive_mode = (
            self.mode_selector.update(
                controller.dpad_up
            )
        )
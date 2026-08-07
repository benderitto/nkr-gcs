from ..model.operator_model import OperatorModel

from .controller import ControllerState
from .mapping import InputMapping
from .sdl_driver import SDLDriver


class InputManager:

    def __init__(self):

        self.controller = ControllerState()

        self.mapping = InputMapping()

        self.driver = SDLDriver()

        self.driver.initialize()

    def update(
        self,
        operator: OperatorModel,
    ):

        self.driver.update(
            self.controller
        )

        self.mapping.update(
            self.controller,
            operator,
        )
from dataclasses import dataclass


@dataclass
class ControllerState:
    """
    Universal controller state.

    Independent from Steam Deck, Xbox,
    DualSense or any other controller.
    """

    #
    # Analog axes
    #

    left_x: float = 0.0
    left_y: float = 0.0

    right_x: float = 0.0
    right_y: float = 0.0

    left_trigger: float = 0.0
    right_trigger: float = 0.0

    #
    # Face buttons
    #

    a: bool = False
    b: bool = False
    x: bool = False
    y: bool = False

    #
    # Shoulder buttons
    #

    l1: bool = False
    r1: bool = False
    r4: bool = False

    #
    # Stick buttons
    #

    left_stick: bool = False
    right_stick: bool = False

    #
    # Menu buttons
    #

    back: bool = False
    start: bool = False
    guide: bool = False
    # SDL MISC1 is the Steam Deck Quick Access / "..." button on mappings
    # where it is not exposed as the traditional BACK button.
    misc1: bool = False

    #
    # D-Pad
    #

    dpad_up: bool = False
    dpad_down: bool = False
    dpad_left: bool = False
    dpad_right: bool = False

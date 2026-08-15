import logging

# On Windows the pysdl2-dll wheel sets PYSDL2_DLL_PATH to its bundled native
# libraries.  Import it before PySDL2; Linux/Flatpak uses the system SDL and
# therefore legitimately has no sdl2dll module.
try:
    import sdl2dll  # noqa: F401
except ImportError:
    pass

import sdl2

from .controller import ControllerState

logger = logging.getLogger(__name__)


class SDLDriver:

    def __init__(self):

        self.controller = None
        self.connected = False
        self._debug_button_state = None

    def initialize(self):

        if sdl2.SDL_Init(
            sdl2.SDL_INIT_GAMECONTROLLER
        ) != 0:
            raise RuntimeError(
                "SDL initialization failed"
            )

        #
        # Find first controller
        #

        for index in range(
            sdl2.SDL_NumJoysticks()
        ):

            if not sdl2.SDL_IsGameController(index):
                continue

            self.controller = (
                sdl2.SDL_GameControllerOpen(index)
            )

            if self.controller:

                self.connected = True
                return

    def update(
        self,
        state: ControllerState,
    ):

        if not self.connected:
            return

        sdl2.SDL_GameControllerUpdate()

        #
        # Analog sticks
        #

        state.left_x = (
            sdl2.SDL_GameControllerGetAxis(
                self.controller,
                sdl2.SDL_CONTROLLER_AXIS_LEFTX,
            ) / 32767.0
        )

        state.left_y = (
            sdl2.SDL_GameControllerGetAxis(
                self.controller,
                sdl2.SDL_CONTROLLER_AXIS_LEFTY,
            ) / 32767.0
        )

        state.right_x = (
            sdl2.SDL_GameControllerGetAxis(
                self.controller,
                sdl2.SDL_CONTROLLER_AXIS_RIGHTX,
            ) / 32767.0
        )

        state.right_y = (
            sdl2.SDL_GameControllerGetAxis(
                self.controller,
                sdl2.SDL_CONTROLLER_AXIS_RIGHTY,
            ) / 32767.0
        )

        #
        # Triggers
        #

        state.left_trigger = (
            sdl2.SDL_GameControllerGetAxis(
                self.controller,
                sdl2.SDL_CONTROLLER_AXIS_TRIGGERLEFT,
            ) / 32767.0
        )

        state.right_trigger = (
            sdl2.SDL_GameControllerGetAxis(
                self.controller,
                sdl2.SDL_CONTROLLER_AXIS_TRIGGERRIGHT,
            ) / 32767.0
        )

        #
        # Face buttons
        #

        state.a = bool(
            sdl2.SDL_GameControllerGetButton(
                self.controller,
                sdl2.SDL_CONTROLLER_BUTTON_A,
            )
        )

        state.b = bool(
            sdl2.SDL_GameControllerGetButton(
                self.controller,
                sdl2.SDL_CONTROLLER_BUTTON_B,
            )
        )

        state.x = bool(
            sdl2.SDL_GameControllerGetButton(
                self.controller,
                sdl2.SDL_CONTROLLER_BUTTON_X,
            )
        )

        state.y = bool(
            sdl2.SDL_GameControllerGetButton(
                self.controller,
                sdl2.SDL_CONTROLLER_BUTTON_Y,
            )
        )

        #
        # Shoulder buttons
        #

        state.l1 = bool(
            sdl2.SDL_GameControllerGetButton(
                self.controller,
                sdl2.SDL_CONTROLLER_BUTTON_LEFTSHOULDER,
            )
        )

        state.r1 = bool(
            sdl2.SDL_GameControllerGetButton(
                self.controller,
                sdl2.SDL_CONTROLLER_BUTTON_RIGHTSHOULDER,
            )
        )

        # On this Steam Deck mapping, physical R4 is SDL Paddle 1. SDL2's
        # Paddle 1 enum is 16; never fall back to a D-Pad enum value.
        state.r4 = bool(
            sdl2.SDL_GameControllerGetButton(
                self.controller,
                getattr(sdl2, "SDL_CONTROLLER_BUTTON_PADDLE1", 16),
            )
        )

        #
        # Stick buttons
        #

        state.left_stick = bool(
            sdl2.SDL_GameControllerGetButton(
                self.controller,
                sdl2.SDL_CONTROLLER_BUTTON_LEFTSTICK,
            )
        )

        state.right_stick = bool(
            sdl2.SDL_GameControllerGetButton(
                self.controller,
                sdl2.SDL_CONTROLLER_BUTTON_RIGHTSTICK,
            )
        )

        #
        # Menu buttons
        #

        state.back = bool(
            sdl2.SDL_GameControllerGetButton(
                self.controller,
                sdl2.SDL_CONTROLLER_BUTTON_BACK,
            )
        )

        state.start = bool(
            sdl2.SDL_GameControllerGetButton(
                self.controller,
                sdl2.SDL_CONTROLLER_BUTTON_START,
            )
        )

        state.guide = bool(
            sdl2.SDL_GameControllerGetButton(
                self.controller,
                sdl2.SDL_CONTROLLER_BUTTON_GUIDE,
            )
        )

        # Steam Deck "..." may be reported as MISC1 rather than BACK,
        # depending on the installed SDL controller mapping database.
        state.misc1 = bool(
            sdl2.SDL_GameControllerGetButton(
                self.controller,
                getattr(sdl2, "SDL_CONTROLLER_BUTTON_MISC1", 11),
            )
        )

        #
        # D-Pad
        #

        state.dpad_up = bool(
            sdl2.SDL_GameControllerGetButton(
                self.controller,
                sdl2.SDL_CONTROLLER_BUTTON_DPAD_UP,
            )
        )

        state.dpad_down = bool(
            sdl2.SDL_GameControllerGetButton(
                self.controller,
                sdl2.SDL_CONTROLLER_BUTTON_DPAD_DOWN,
            )
        )

        state.dpad_left = bool(
            sdl2.SDL_GameControllerGetButton(
                self.controller,
                sdl2.SDL_CONTROLLER_BUTTON_DPAD_LEFT,
            )
        )

        state.dpad_right = bool(
            sdl2.SDL_GameControllerGetButton(
                self.controller,
                sdl2.SDL_CONTROLLER_BUTTON_DPAD_RIGHT,
            )
        )

        self._log_menu_input_edges(state)

    def _log_menu_input_edges(self, state: ControllerState):
        """Temporary edge diagnostics for Steam Deck SDL button mapping."""
        current = (state.y, state.r4, state.dpad_up, state.dpad_down)
        if current != self._debug_button_state:
            logger.info("SDL menu inputs: Y=%s R4=%s DPadUp=%s DPadDown=%s",
                        *current)
            self._debug_button_state = current

import nkr_gcs.input.sdl_driver as sdl_driver_module
from nkr_gcs.input.sdl_driver import SDLDriver


def test_sdl_native_handles_are_closed_once(monkeypatch):
    closed = []
    quit_subsystems = []
    monkeypatch.setattr(
        sdl_driver_module.sdl2,
        "SDL_GameControllerClose",
        closed.append,
    )
    monkeypatch.setattr(
        sdl_driver_module.sdl2,
        "SDL_QuitSubSystem",
        quit_subsystems.append,
    )
    driver = SDLDriver()
    controller = object()
    driver.controller = controller
    driver.connected = True
    driver._initialized = True

    driver.close()
    driver.close()

    assert closed == [controller]
    assert quit_subsystems == [
        sdl_driver_module.sdl2.SDL_INIT_GAMECONTROLLER,
    ]
    assert driver.controller is None
    assert driver.connected is False

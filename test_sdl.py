import time

import sdl2


def axis(value):

    return round(value / 32767.0, 2)


if sdl2.SDL_Init(sdl2.SDL_INIT_GAMECONTROLLER) != 0:
    raise RuntimeError("SDL init failed")


print("Joysticks:", sdl2.SDL_NumJoysticks())


controller = None

for i in range(sdl2.SDL_NumJoysticks()):

    print("Checking", i)

    if not sdl2.SDL_IsGameController(i):
        continue

    controller = sdl2.SDL_GameControllerOpen(i)

    if controller:
        print("Connected:", sdl2.SDL_GameControllerName(controller))
        break


if controller is None:
    raise RuntimeError("No controller")


while True:

    sdl2.SDL_GameControllerUpdate()

    lx = axis(
        sdl2.SDL_GameControllerGetAxis(
            controller,
            sdl2.SDL_CONTROLLER_AXIS_LEFTX,
        )
    )

    r2 = axis(
        sdl2.SDL_GameControllerGetAxis(
            controller,
            sdl2.SDL_CONTROLLER_AXIS_TRIGGERRIGHT,
        )
    )

    l2 = axis(
        sdl2.SDL_GameControllerGetAxis(
            controller,
            sdl2.SDL_CONTROLLER_AXIS_TRIGGERLEFT,
        )
    )

    print(
        f"LX={lx:5.2f}  "
        f"L2={l2:5.2f}  "
        f"R2={r2:5.2f}",
        end="\r",
    )

    time.sleep(0.01)
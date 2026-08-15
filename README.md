# NKR Ground Control Station

GCS is a cross-platform PySide6 application for Steam Deck, Linux, and Windows.
It reads SDL2 controller input, converts it to operator intent, and sends NKR
UDP Protocol v2 control packets to the robot's ROS2 Gateway over Tailscale.
The same long-lived UDP socket receives authenticated robot-state telemetry for
the HUD and state-change popups; GCS still has no ROS2 dependency.

## Install

Use the isolated Flatpak build on SteamOS/Linux or the self-contained Windows
build. See [INSTALL.md](INSTALL.md) for complete installation, autostart,
configuration, controller, and build instructions.

## Development run

Install the Python dependencies used by the UI/SDL environment, then run from
the repository root:

```bash
python3 -m venv .venv
. .venv/bin/activate
pip install -e '.[test]'
NKR_GCS_CONFIG="$PWD/config/settings.yaml" nkr-gcs
```

Video uses native low-latency RTSP rather than a browser. Linux uses GStreamer;
Windows uses the bundled PyAV/FFmpeg backend. The receive queue keeps only the
newest frame.

GCS starts in kiosk presentation mode: fullscreen, frameless, and above normal
desktop windows. Press the Steam Deck View (`□ □`) button once to release the
window to normal desktop mode; release it and press once more to return to
kiosk mode. This does not change the UDP View button mapping. In kiosk mode,
R4 opens/closes the in-flight OSD menu; the same menu opens by
tapping the top-right hamburger icon.

Select a controller profile in **GCS Menu → App Settings → Input Device**.
Steam Deck keeps the existing bindings. On Xbox Controller, hold Menu for two
seconds to arm or tap it to disarm; View retains the Steam Deck View function.
On DualSense the same rule uses Options, while Share replaces Xbox View. All
other axes and buttons keep the Steam Deck bindings. The selection persists
across application restarts.

Video options in `config/settings.yaml` are `video_enabled`, `video_host`,
`video_port`, `video_default_stream`, and `video_low_latency_mode`. The host
defaults to `robot_host` when omitted.

Network settings are explicit in `config/settings.yaml`. The GCS opens one
long-lived non-blocking UDP socket, sends a session hello on startup, accepts a
gateway challenge, and responds with the same challenge. Only then does it send
control packets at 50 Hz. To verify the session, inspect the gateway log for a
hello/challenge/response followed by v2 controls from the Steam Deck address;
the GCS sends no controls before that exchange completes.

Gateway telemetry is accepted only while the session is active and when its
`session_id` matches. It updates active drive mode, armed/disarmed, and E-stop
state in the GCS UI.

Run the tests with:

```bash
pytest
```

# Installing NKR GCS

NKR GCS uses one Python/PySide6 codebase on SteamOS, Linux, and Windows. Linux
packages use the native GStreamer video backend. Windows packages use the
bundled PyAV/FFmpeg backend. Controller input is provided by SDL2 on every
platform.

## Steam Deck (recommended)

Flatpak is isolated from SteamOS system packages, so an operating-system update
does not remove the application's Python, PySide6, SDL2, GStreamer, or H.264
decoder dependencies.

1. Download `nkr-gcs.flatpak` from the latest GitHub Actions build or release.
2. In Desktop Mode, install it for the current user:

   ```bash
   flatpak install --user ./nkr-gcs.flatpak
   ```

3. Start it:

   ```bash
   flatpak run ua.nkr.GCS
   ```

4. To start GCS automatically in Desktop Mode:

   ```bash
   ./packaging/linux/enable-autostart.sh
   ```

To use it from Gaming Mode, add `flatpak run ua.nkr.GCS` as a non-Steam game.
The Flatpak has network access for Tailscale and device access for the built-in
Steam Deck controls and external SDL2-compatible controllers.

Settings persist outside application updates at:

```text
~/.var/app/ua.nkr.GCS/config/nkr-gcs/settings.yaml
```

No `pacman` packages are required after the Flatpak is installed.

## Other Linux PCs

Install Flatpak and add Flathub once, using the instructions for the Linux
distribution. Then use the same `flatpak install --user ./nkr-gcs.flatpak` and
`flatpak run ua.nkr.GCS` commands shown above. The configuration is stored at
the same sandbox-relative path.

For source development on a conventional Linux distribution, install Python
3.11+, Qt/PySide6, SDL2, GStreamer, the GStreamer libav plugin, and PyGObject,
then run:

```bash
python3 -m venv .venv
. .venv/bin/activate
pip install -e '.[test]'
NKR_GCS_CONFIG="$PWD/config/settings.yaml" nkr-gcs
```

## Windows 10/11 x64

1. Install Tailscale and sign in to the robot's tailnet.
2. Connect an Xbox or DualSense controller before starting GCS.
3. Download and extract the `nkr-gcs-windows-x64` GitHub artifact/release.
4. Start `nkr-gcs.exe` from the extracted directory.

The Windows package contains Python, Qt, SDL2, and FFmpeg/PyAV. It does not
require a system Python or GStreamer installation. Settings are created at:

```text
%APPDATA%\NKR-GCS\settings.yaml
```

To build the Windows package locally, use PowerShell on Windows:

```powershell
./packaging/windows/build.ps1
```

## Configuration

The first run creates a user configuration with the current defaults:

```yaml
robot_host: 100.72.220.66
robot_port: 9999
control_rate_hz: 50
video_enabled: true
video_host: 100.72.220.66
video_port: 8554
video_default_stream: cam_front
video_low_latency_mode: true
```

Set `NKR_GCS_CONFIG` to use an explicit configuration file during development
or diagnostics. Never expose the robot control or video endpoints directly to
the public internet; use Tailscale or another trusted VPN.

## Supported controllers

SDL2 supports the Steam Deck controls, Xbox controllers, DualSense/DualShock,
and other SDL-compatible gamepads. The current release opens the first
compatible controller. Device selection, calibration, and editable button
profiles are planned follow-up features.

## Building the Flatpak

The GitHub workflow builds the bundle automatically on every push to `main`.
For a local build, install `flatpak-builder`, the KDE 6.10 runtime/SDK, and the
PySide BaseApp, then run:

```bash
flatpak-builder --user --install --force-clean build-dir ua.nkr.GCS.yml
flatpak run ua.nkr.GCS
```

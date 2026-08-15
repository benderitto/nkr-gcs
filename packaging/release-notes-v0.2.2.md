# NKR Ground Control Station 0.2.2

Windows diagnostics and control-loop resilience update.

## Improved

- Write a rotating diagnostic log to `%APPDATA%\NKR-GCS\nkr-gcs.log` on Windows.
- Record the effective robot, video, and input configuration at startup.
- Record full PyAV/FFmpeg errors when the Windows video backend cannot open a stream.
- Isolate input, UI, camera, and network stages so a non-network UI error cannot stop UDP control negotiation.
- Keep operator commands neutral if reading the input device fails.

## Downloads

- **Steam Deck / Linux:** `nkr-gcs-linux-x86_64.flatpak`
- **Windows 10/11 x64:** `nkr-gcs-windows-x64.zip`
- **Verification:** `SHA256SUMS.txt`

See [INSTALL.md](https://github.com/benderitto/nkr-gcs/blob/v0.2.2/INSTALL.md) for installation and Tailscale setup.

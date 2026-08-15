# NKR Ground Control Station 0.2.3

Windows control and video diagnostics update.

## Fixed

- Send the UDP session hello before attempting the first non-blocking receive.
  This prevents a Windows WinSock receive error from blocking session negotiation.
- Keep the UDP network stage alive when an independent input, camera, or UI stage fails.
- Keep operator commands neutral after an input-device error.

## Diagnostics

- Write a rotating diagnostic log to `%APPDATA%\NKR-GCS\nkr-gcs.log` on Windows.
- Record effective connection settings, PyAV/FFmpeg versions, video exceptions,
  and WinSock error codes.
- Verify in CI that the packaged Windows executable enters the Qt update loop
  and starts UDP negotiation.

## Downloads

- **Steam Deck / Linux:** `nkr-gcs-linux-x86_64.flatpak`
- **Windows 10/11 x64:** `nkr-gcs-windows-x64.zip`
- **Verification:** `SHA256SUMS.txt`

See [INSTALL.md](https://github.com/benderitto/nkr-gcs/blob/v0.2.3/INSTALL.md) for installation and Tailscale setup.

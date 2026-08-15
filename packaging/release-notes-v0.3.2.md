# NKR Ground Control Station 0.3.2

Windows video switching and shutdown reliability update.

## Fixed

- Give each PyAV camera connection its own stop event and reject queued frames
  from an obsolete connection.
- Join the FFmpeg/PyAV decode worker before opening another camera or exiting.
- Release the SDL game-controller handle and subsystem before Windows unloads
  the bundled native DLLs.
- Reject impossible future video timestamps instead of displaying a false
  `0 ms` latency value.
- Clear stale latency after invalid timestamp frames and record the signed
  value in the diagnostic log.

## Added

- Close GCS cleanly with `Ctrl+Shift+Q` on every platform.
- Make Windows CI exercise graceful packaged-application shutdown.

## Downloads

- **Steam Deck / Linux:** `nkr-gcs-linux-x86_64.flatpak`
- **Windows 10/11 x64:** `nkr-gcs-windows-x64.zip`
- **Verification:** `SHA256SUMS.txt`

See [INSTALL.md](https://github.com/benderitto/nkr-gcs/blob/v0.3.2/INSTALL.md) for installation and Tailscale setup.

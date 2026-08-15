# NKR Ground Control Station 0.4.1

Bounded native video delivery on Steam Deck and Linux.

## Improved

- Route native in-process GStreamer frames through the same latest-frame
  mailbox used by the Windows GStreamer backend.
- Replace an unpainted Linux/SteamOS frame instead of adding another Qt event.
- Keep camera-generation checks so a late frame from the previous stream
  cannot appear after a camera switch.

## Validation

- Run the complete automated test suite on Linux and Windows.
- Smoke-test the native GStreamer RTSP path inside the Steam Deck Flatpak.

## Downloads

- **Steam Deck / Linux:** `nkr-gcs-linux-x86_64.flatpak`
- **Windows 10/11 x64:** `nkr-gcs-windows-x64.zip`
- **Verification:** `SHA256SUMS.txt`

See [INSTALL.md](https://github.com/benderitto/nkr-gcs/blob/v0.4.1/INSTALL.md) for installation and Tailscale setup.

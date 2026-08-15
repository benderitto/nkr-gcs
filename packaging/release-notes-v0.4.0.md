# NKR Ground Control Station 0.4.0

Native low-latency GStreamer video on Windows.

## Added

- Ship the official GStreamer 1.26.11 MSVC x64 runtime inside the Windows ZIP.
- Prefer the same bounded-latency GStreamer RTSP/H.264 pipeline on Windows and
  Steam Deck, while retaining PyAV as an automatic fallback.
- Add explicit `video_width` and `video_height` settings for the current
  640×480 camera and future native 1920×1080 cameras.

## Improved

- Replace queued portable frames with the newest decoded frame.
- Paint video directly with Qt smooth scaling instead of creating a fast,
  visibly pixelated intermediate image.
- Verify the bundled GStreamer runtime, required plugins, backend selection,
  and graceful application shutdown in Windows CI.

## Downloads

- **Steam Deck / Linux:** `nkr-gcs-linux-x86_64.flatpak`
- **Windows 10/11 x64:** `nkr-gcs-windows-x64.zip`
- **Verification:** `SHA256SUMS.txt`

See [INSTALL.md](https://github.com/benderitto/nkr-gcs/blob/v0.4.0/INSTALL.md) for installation and Tailscale setup.

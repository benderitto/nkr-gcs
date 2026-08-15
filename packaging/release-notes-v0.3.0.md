# NKR Ground Control Station 0.3.0

Real capture-to-display video latency measurement.

## Added

- Decode the machine-readable UTC timestamp embedded in each robot video frame.
- Show actual capture-to-display delay in the HUD `LATENCY` field.
- Synchronize GCS time against Cloudflare, Google, and pool.ntp.org using SNTP
  without requiring administrator privileges or changing the system clock.
- Hide the timestamp marker before painting the video frame.
- Show `—` when time synchronization or a valid marker is unavailable.

## Validation

- Gray-code marker and SNTP calculations have deterministic unit tests.
- Windows packaging now runs the complete GCS test suite before its executable
  smoke test.

## Downloads

- **Steam Deck / Linux:** `nkr-gcs-linux-x86_64.flatpak`
- **Windows 10/11 x64:** `nkr-gcs-windows-x64.zip`
- **Verification:** `SHA256SUMS.txt`

See [INSTALL.md](https://github.com/benderitto/nkr-gcs/blob/v0.3.0/INSTALL.md) for installation and Tailscale setup.

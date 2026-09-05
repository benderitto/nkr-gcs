# NKR Ground Control Station 0.5.1

Reliable Steam Deck control transport and complete lighting controls.

## Added

- Add Protocol v3 lighting commands for Dark Mode, low beam, high beam,
  searchlight, and parking lights.
- Add the in-flight **LIGHT MODE** menu and controller X low/high-beam toggle.
- Show the active lighting mode in authenticated robot telemetry and the HUD.
- Prevent multiple GCS instances from competing for the robot session.

## Improved

- Run authenticated UDP control on a dedicated worker, independent of Qt and
  video rendering.
- Apply full brake while controller snapshots are stale, while preserving the
  authenticated session for automatic recovery.
- Document the iwd roaming-scan and Wi-Fi power-saving fix for dedicated Steam
  Deck operator stations.

## Validation

- Pass the protocol, input-mapping, network, and control-worker test suites.
- Run a two-minute armed driving test over Tailscale with zero packet loss and
  no operator timeout after applying the Steam Deck Wi-Fi fix.
- Smoke-test the Flatpak on SteamOS with native GStreamer video.

## Downloads

- **Steam Deck / Linux:** `nkr-gcs-linux-x86_64.flatpak`
- **Windows 10/11 x64:** `nkr-gcs-windows-x64.zip`
- **Verification:** `SHA256SUMS.txt`

See [INSTALL.md](https://github.com/benderitto/nkr-gcs/blob/v0.5.1/INSTALL.md) for installation, Tailscale, controller, and Steam Deck Wi-Fi setup.

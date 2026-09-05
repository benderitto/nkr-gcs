# NKR Ground Control Station 0.5.2

Hard isolation for safety-critical control traffic.

## Fixed

- Move authenticated UDP send/receive from a Python thread to a spawned
  process with its own interpreter, GIL, scheduler, and socket.
- Keep control traffic running when Qt, SDL, or GStreamer holds the UI
  process GIL.
- Preserve the 250 ms stale-controller brake watchdog across process IPC.

## Validation

- Pass protocol, input, network, mailbox, and spawned-process tests.
- Smoke-test isolated process startup inside the Steam Deck Flatpak.
- Complete an armed driving test while monitoring gateway and safety logs.

## Downloads

- **Steam Deck / Linux:** `nkr-gcs-linux-x86_64.flatpak`
- **Windows 10/11 x64:** `nkr-gcs-windows-x64.zip`
- **Verification:** `SHA256SUMS.txt`

See [INSTALL.md](https://github.com/benderitto/nkr-gcs/blob/v0.5.2/INSTALL.md) for installation and Steam Deck network setup.

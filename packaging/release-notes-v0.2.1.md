# NKR Ground Control Station 0.2.1

Windows packaging hotfix for the first cross-platform release.

## Fixed

- Bundle the native `SDL2.dll` supplied by `pysdl2-dll` in the Windows x64 package.
- Initialize the bundled SDL2 library before importing PySDL2.
- Smoke-test the packaged Windows executable in CI before publishing it.

## Downloads

- **Steam Deck / Linux:** `nkr-gcs-linux-x86_64.flatpak`
- **Windows 10/11 x64:** `nkr-gcs-windows-x64.zip`
- **Verification:** `SHA256SUMS.txt`

See [INSTALL.md](https://github.com/benderitto/nkr-gcs/blob/v0.2.1/INSTALL.md) for installation and Tailscale setup.

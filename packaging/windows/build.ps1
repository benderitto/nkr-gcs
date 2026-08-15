$ErrorActionPreference = "Stop"
Set-Location (Resolve-Path "$PSScriptRoot\..\..")
python -m pip install --upgrade pip
python -m pip install -r requirements-windows.txt "pyinstaller>=6,<7"
python -m PyInstaller --noconfirm --clean --windowed `
  --name nkr-gcs `
  --paths nkr_protocol `
  --collect-all av `
  --collect-all sdl2 `
  --collect-all sdl2dll `
  run.py
Write-Host "Windows bundle created in dist\nkr-gcs"

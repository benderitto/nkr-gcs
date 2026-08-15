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

$gstVersion = "1.26.11"
$gstName = "gstreamer-1.0-msvc-x86_64-$gstVersion.msi"
$gstUrl = "https://gstreamer.freedesktop.org/data/pkg/windows/$gstVersion/msvc/$gstName"
$gstSha256 = "31cbc21fa0950b5c1e79c80959b2799805cb05a7a35953a13a9f790776137605"
$gstInstaller = Join-Path $PWD "build\$gstName"
$gstInstallRoot = Join-Path $PWD "build\gstreamer-runtime"
$gstFeatures = @(
  "_gstreamer_1.0",
  "_gstreamer_1.0_core",
  "_gstreamer_1.0_system",
  "_gstreamer_1.0_playback",
  "_gstreamer_1.0_codecs",
  "_gstreamer_1.0_net",
  "_gstreamer_1.0_libav"
) -join ","

Write-Host "Downloading official GStreamer $gstVersion MSVC runtime"
Invoke-WebRequest -Uri $gstUrl -OutFile $gstInstaller
$actualSha256 = (Get-FileHash $gstInstaller -Algorithm SHA256).Hash.ToLowerInvariant()
if ($actualSha256 -ne $gstSha256) {
  throw "GStreamer installer checksum mismatch: $actualSha256"
}
if (Test-Path $gstInstallRoot) {
  Remove-Item $gstInstallRoot -Recurse -Force
}

$installer = Start-Process msiexec.exe -Wait -PassThru -ArgumentList @(
  "/i",
  "`"$gstInstaller`"",
  "/qn",
  "/norestart",
  "INSTALLDIR=`"$gstInstallRoot`"",
  "ADDLOCAL=$gstFeatures"
)
if ($installer.ExitCode -notin @(0, 3010)) {
  throw "GStreamer runtime installer failed with code $($installer.ExitCode)"
}

$gstLaunch = Get-ChildItem $gstInstallRoot -Recurse -Filter "gst-launch-1.0.exe" |
  Select-Object -First 1
if (-not $gstLaunch) {
  throw "Installed GStreamer runtime does not contain gst-launch-1.0.exe"
}
$gstPrefix = Split-Path (Split-Path $gstLaunch.FullName -Parent) -Parent
$gstDestination = Join-Path $PWD "dist\nkr-gcs\_internal\gstreamer"
Copy-Item $gstPrefix $gstDestination -Recurse -Force

$bundledBin = Join-Path $gstDestination "bin"
$bundledPlugins = Join-Path $gstDestination "lib\gstreamer-1.0"
$env:PATH = "$bundledBin;$env:PATH"
$env:GST_PLUGIN_SYSTEM_PATH_1_0 = $bundledPlugins
$env:GST_PLUGIN_PATH_1_0 = ""
foreach ($element in @("rtspsrc", "rtph264depay", "h264parse", "avdec_h264", "videoconvert", "fdsink")) {
  & (Join-Path $bundledBin "gst-inspect-1.0.exe") $element | Out-Null
  if ($LASTEXITCODE -ne 0) {
    throw "Bundled GStreamer element is unavailable: $element"
  }
}
Write-Host "Windows bundle created in dist\nkr-gcs"

#!/bin/sh
set -eu
autostart_dir="${XDG_CONFIG_HOME:-$HOME/.config}/autostart"
mkdir -p "$autostart_dir"
cat >"$autostart_dir/ua.nkr.GCS.desktop" <<'EOF'
[Desktop Entry]
Type=Application
Name=NKR Ground Control Station
Exec=flatpak run ua.nkr.GCS
Icon=ua.nkr.GCS
Terminal=false
X-GNOME-Autostart-enabled=true
EOF
echo "NKR GCS autostart enabled: $autostart_dir/ua.nkr.GCS.desktop"

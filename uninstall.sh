#!/bin/sh
# Remove a ./install.sh install. Settings in ~/.config/xway-screensaver are kept.
set -eu

SHARE=${XDG_DATA_HOME:-$HOME/.local/share}
UNITS=${XDG_CONFIG_HOME:-$HOME/.config}/systemd/user

systemctl --user disable --now xway-screensaver.service 2>/dev/null || true
rm -f "$UNITS/xway-screensaver.service" "$HOME/.local/bin/xway-screensaver" \
      "$SHARE/applications/io.github.geomextric.XwayScreensaver.desktop" \
      "$SHARE/icons/hicolor/scalable/apps/io.github.geomextric.XwayScreensaver.svg"
rm -rf "$SHARE/xway-screensaver"
systemctl --user daemon-reload
echo "xway-screensaver removed. Delete ~/.config/xway-screensaver too to drop your settings."

#!/bin/sh
# Install xway-screensaver for the current user. Re-run to update.
#   ./install.sh          copy the files (the checkout can be deleted afterwards)
#   ./install.sh --link   symlink the checkout instead, for working on the code
set -eu

SRC=$(cd "$(dirname "$0")" && pwd)
APP_ID=io.github.geomextric.XwayScreensaver
SHARE=${XDG_DATA_HOME:-$HOME/.local/share}
DEST=$SHARE/xway-screensaver
BIN=$HOME/.local/bin
UNITS=${XDG_CONFIG_HOME:-$HOME/.config}/systemd/user

rm -rf "$DEST"
if [ "${1:-}" = "--link" ]; then
    mkdir -p "$(dirname "$DEST")"
    ln -s "$SRC" "$DEST"
else
    mkdir -p "$DEST"
    cp -r "$SRC/bin" "$SRC/xway_screensaver" "$DEST/"
    find "$DEST" -name __pycache__ -prune -exec rm -rf {} +
fi

ICONS=$SHARE/icons/hicolor/scalable/apps
mkdir -p "$BIN" "$UNITS" "$SHARE/applications" "$ICONS"
ln -sf "$DEST/bin/xway-screensaver" "$BIN/xway-screensaver"
install -m 644 "$SRC/data/$APP_ID.svg" "$ICONS/$APP_ID.svg"
sed "s|@BIN@|$BIN/xway-screensaver|" "$SRC/data/xway-screensaver.service.in" > "$UNITS/xway-screensaver.service"
sed "s|@BIN@|$BIN/xway-screensaver|" "$SRC/data/$APP_ID.desktop.in" > "$SHARE/applications/$APP_ID.desktop"

systemctl --user daemon-reload
systemctl --user try-restart xway-screensaver.service

echo "Installed to $DEST"
echo "Open xway-screensaver from your app menu (or run: xway-screensaver settings)."

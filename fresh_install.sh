#!/bin/bash
# Clean all VLC player code and systemd units, then run a fresh bootstrap.
# Usage: sudo ./fresh_install.sh
# (Run from the repo or any directory; bootstrap is fetched from GitHub.)
set -e

# --- Same user/home detection as bootstrap.sh ---------------------------------
if [ -n "$SUDO_USER" ]; then
  USER="$SUDO_USER"
elif [ "$USER" != "root" ] && [ -n "$USER" ]; then
  USER="$USER"
else
  USER=$(logname 2>/dev/null || echo "")
  if [ -z "$USER" ] || [ "$USER" = "root" ]; then
    USER=$(getent passwd | awk -F: '$3 >= 1000 && $1 != "nobody" {print $1; exit}')
    [ -z "$USER" ] && USER="pi"
  fi
fi

HOME_DIR=$(getent passwd "$USER" | cut -d: -f6)
[ -z "$HOME_DIR" ] || [ ! -d "$HOME_DIR" ] && HOME_DIR="/home/$USER"
DIR="$HOME_DIR/vlc-player"

UNITS=(
  vlc-player.service
  vlc-maintenance.service
  vlc-maintenance.timer
  vlc-code-update.service
  vlc-code-update.timer
)

echo "=== VLC Player – Full clean and fresh install ==="
echo "User: $USER"
echo "Dir:  $DIR"
echo ""

# 1) Stop and disable all units
echo "[1/4] Stopping and disabling systemd units..."
for u in "${UNITS[@]}"; do
  systemctl stop "$u" 2>/dev/null || true
  systemctl disable "$u" 2>/dev/null || true
done

# 2) Remove unit files from systemd
echo "[2/4] Removing systemd unit files..."
for u in "${UNITS[@]}"; do
  rm -f "/etc/systemd/system/$u"
done
systemctl daemon-reload

# 3) Remove code directory (full clean)
echo "[3/4] Removing install directory..."
if [ -d "$DIR" ]; then
  rm -rf "$DIR"
  echo "  Removed $DIR"
else
  echo "  Directory not present, skipping."
fi

# 4) Run fresh bootstrap from GitHub
echo "[4/4] Running bootstrap.sh from GitHub..."
curl -sSL https://raw.githubusercontent.com/Digital-Out-Of-Home/Berlin-dooh-device/main/scripts/bootstrap.sh | sudo bash

echo ""
echo "=== Done. Fresh install completed via bootstrap. ==="

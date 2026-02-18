#!/bin/bash
set -e

# Ensure this script is executable for future runs
if [ ! -x "$0" ]; then
  chmod +x "$0" 2>/dev/null || true
fi

# Detect the appropriate user for X authority
if [ -n "$SUDO_USER" ]; then
  USERNAME="$SUDO_USER"
else
  USERNAME="${USER:-pi}"
fi

# Resolve the home directory for the user
HOME_DIR=$(getent passwd "$USERNAME" | cut -d: -f6)
if [ -z "$HOME_DIR" ] || [ ! -d "$HOME_DIR" ]; then
  HOME_DIR="/home/$USERNAME"
fi

export DISPLAY="${DISPLAY:-:0}"
export XAUTHORITY="${XAUTHORITY:-$HOME_DIR/.Xauthority}"

# Find primary output, or fall back to first connected output
PRIMARY=$(xrandr --query | awk '/ connected primary/{print $1; exit}')
if [ -z "$PRIMARY" ]; then
  PRIMARY=$(xrandr --query | awk '/ connected/{print $1; exit}')
fi

if [ -z "$PRIMARY" ]; then
  echo "No connected display found."
  exit 1
fi

# Rotate 90° clockwise (right)
xrandr --output "$PRIMARY" --rotate right
echo "Rotated display '$PRIMARY' to the right."


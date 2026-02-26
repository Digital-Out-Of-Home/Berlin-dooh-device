#!/bin/bash
set -euo pipefail

# Disable power schedule timers to stop power/schedule-related logs.
# This stops the timers but does NOT uninstall services.
# Usage: sudo ./scripts/disable_power_schedule_logs.sh

if [ "$(id -u)" -ne 0 ]; then
  echo "This script must be run as root (use sudo)." >&2
  exit 1
fi

echo "=== Disabling power schedule timers (vlc-power-control.timer, vlc-scheduler-sync.timer) ==="

for unit in vlc-power-control.timer vlc-scheduler-sync.timer; do
  if systemctl list-unit-files | grep -q "^${unit}"; then
    echo "--- $unit ---"
    systemctl stop "$unit" || true
    systemctl disable "$unit" || true
  else
    echo "$unit is not installed."
  fi
done

echo
echo "Timers disabled. Existing log files are not removed."
echo "Re-enable with:"
echo "  sudo systemctl enable vlc-power-control.timer vlc-scheduler-sync.timer"
echo "  sudo systemctl start vlc-power-control.timer vlc-scheduler-sync.timer"


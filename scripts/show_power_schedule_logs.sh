#!/bin/bash
set -euo pipefail

# Show recent logs related to power schedule (scheduler + power control).
# Usage: ./scripts/show_power_schedule_logs.sh

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

echo "=== Power schedule logs (scheduler + power_control) ==="
echo

echo "--- vlc-scheduler-sync.service (last 50 lines) ---"
if command -v journalctl >/dev/null 2>&1; then
  if systemctl list-unit-files | grep -q '^vlc-scheduler-sync.service'; then
    journalctl -u vlc-scheduler-sync.service -n 50 --no-pager || echo "No journal entries for vlc-scheduler-sync.service yet."
  else
    echo "vlc-scheduler-sync.service not installed."
  fi
else
  echo "journalctl not available."
fi

echo
echo "--- vlc-power-control.service (last 50 lines) ---"
if command -v journalctl >/dev/null 2>&1; then
  if systemctl list-unit-files | grep -q '^vlc-power-control.service'; then
    journalctl -u vlc-power-control.service -n 50 --no-pager || echo "No journal entries for vlc-power-control.service yet."
  else
    echo "vlc-power-control.service not installed."
  fi
else
  echo "journalctl not available."
fi

echo
LOG_DIR="${ROOT_DIR}/logs"
if [ -d "$LOG_DIR" ]; then
  latest_log="$(ls -1t "$LOG_DIR"/vlc-power-control-*.log 2>/dev/null | head -n 1 || true)"
  if [ -n "${latest_log:-}" ]; then
    echo "--- Latest power_control file log: ${latest_log} (last 50 lines) ---"
    tail -n 50 "$latest_log" || echo "Failed to read ${latest_log}"
  else
    echo "No power_control log files found in $LOG_DIR."
  fi
else
  echo "Log directory $LOG_DIR does not exist."
fi

echo
SCHEDULE_FILE="${ROOT_DIR}/media/schedule.json"
if [ -f "$SCHEDULE_FILE" ]; then
  echo "--- Current schedule.json ---"
  cat "$SCHEDULE_FILE"
else
  echo "No schedule.json found at $SCHEDULE_FILE."
fi


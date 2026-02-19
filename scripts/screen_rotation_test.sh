#!/bin/bash
set -e

# Screen rotation test helper using wlr-randr.
# Run this from a graphical Wayland session as the logged-in user (e.g. on the Pi desktop),
# otherwise wlr-randr may fail with "failed to connect to display".
#
# Usage:
#   ./screen_rotation_test.sh            # uses default output HDMI-A-1
#   ./screen_rotation_test.sh HDMI-A-2   # test another output name

OUTPUT_NAME="${1:-HDMI-A-1}"

echo "=== Screen rotation test ==="
echo "WAYLAND_DISPLAY=${WAYLAND_DISPLAY:-<not set>}"
echo "XDG_RUNTIME_DIR=${XDG_RUNTIME_DIR:-<not set>}"
echo ""

if ! command -v wlr-randr >/dev/null 2>&1; then
  echo "wlr-randr is not installed. Install it first (e.g. via bootstrap)."
  exit 1
fi

echo "--- Available outputs (wlr-randr) ---"
wlr-randr
echo ""

echo "--- Rotating output ${OUTPUT_NAME} to 90 degrees ---"
wlr-randr --output "${OUTPUT_NAME}" --transform 90
echo "Done."


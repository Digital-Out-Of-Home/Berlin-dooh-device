#!/bin/bash
# Stop VLC Player systemd services
# Usage: sudo ./stop_vlc.sh

echo "Stopping VLC Player services..."

# Stop the timer first (prevents new maintenance runs)
echo "Stopping vlc-maintenance.timer..."
systemctl stop vlc-maintenance.timer
systemctl disable vlc-maintenance.timer 2>/dev/null || true

# Stop the VLC player service
echo "Stopping vlc-player service..."
systemctl stop vlc-player
systemctl disable vlc-player 2>/dev/null || true

# Kill any remaining VLC processes
echo "Killing any remaining VLC processes..."
pkill -9 vlc 2>/dev/null || true
pkill -9 -f "main.py" 2>/dev/null || true

# Show status
echo ""
echo "Service status:"
systemctl status vlc-player --no-pager | head -3 || true
systemctl status vlc-maintenance.timer --no-pager | head -3 || true

echo ""
echo "VLC services stopped ✓"


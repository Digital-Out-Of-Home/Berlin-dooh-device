#!/bin/bash
# Cleanup Legacy Bootstrap Items
# Removes items that are no longer needed after bootstrap changes
# Usage: sudo ./cleanup_bootstrap.sh

# Auto-detect user
if [ -n "$SUDO_USER" ]; then
    USER="$SUDO_USER"
elif [ "$USER" = "root" ] || [ -z "$USER" ]; then
    USER=$(getent passwd | awk -F: '$3 >= 1000 && $1 != "nobody" {print $1; exit}')
    [ -z "$USER" ] && USER="user"
fi

echo "=== Cleaning Up Legacy Bootstrap Items ==="
echo "User: $USER"
echo ""

# 1. Remove watchdog cron
echo "1. Removing watchdog cron..."
if crontab -u "$USER" -l 2>/dev/null | grep -q "vlc-player"; then
    crontab -u "$USER" -l 2>/dev/null | grep -v "vlc-player" | crontab -u "$USER" -
    echo "  ✓ Watchdog cron removed"
else
    echo "  ✓ No watchdog cron found"
fi

# 2. Remove hostname entries from /etc/hosts (optional - safe to remove)
echo ""
echo "2. Cleaning /etc/hosts..."
# Get DEVICE_ID from config if available
CONFIG_FILE="/home/$USER/vlc-player/config.env"
if [ -f "$CONFIG_FILE" ]; then
    DEVICE_ID=$(grep "^DEVICE_ID=" "$CONFIG_FILE" 2>/dev/null | cut -d'=' -f2- | sed 's/^[[:space:]]*//;s/[[:space:]]*$//')
    if [ -n "$DEVICE_ID" ]; then
        # Remove entries for this device ID
        if grep -q "127.0.0.1.*$DEVICE_ID\|$DEVICE_ID.*127.0.0.1" /etc/hosts 2>/dev/null; then
            sed -i "/$DEVICE_ID/d" /etc/hosts
            echo "  ✓ Removed $DEVICE_ID from /etc/hosts"
        else
            echo "  ✓ No entries found for $DEVICE_ID"
        fi
    fi
fi

# Also check current hostname
CURRENT_HOSTNAME=$(hostname)
if [ -n "$CURRENT_HOSTNAME" ] && [ "$CURRENT_HOSTNAME" != "raspberrypi" ] && [ "$CURRENT_HOSTNAME" != "localhost" ]; then
    if grep -q "127.0.0.1.*$CURRENT_HOSTNAME\|$CURRENT_HOSTNAME.*127.0.0.1" /etc/hosts 2>/dev/null; then
        # Only remove if it's not the standard localhost entry
        if ! grep -q "^127.0.0.1.*localhost.*$CURRENT_HOSTNAME\|^127.0.0.1.*$CURRENT_HOSTNAME.*localhost" /etc/hosts 2>/dev/null; then
            sed -i "/127.0.0.1.*$CURRENT_HOSTNAME\|$CURRENT_HOSTNAME.*127.0.0.1/d" /etc/hosts
            echo "  ✓ Removed $CURRENT_HOSTNAME from /etc/hosts"
        else
            echo "  ✓ $CURRENT_HOSTNAME is part of standard localhost entry (keeping)"
        fi
    fi
fi

echo ""
echo "=== Cleanup Complete ==="
echo "Legacy items have been removed."
echo "Run verify_bootstrap.sh to verify the cleanup."


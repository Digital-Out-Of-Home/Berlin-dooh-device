#!/bin/bash
# Bootstrap Verification Script
# Checks if all bootstrap operations completed successfully
# Usage: sudo ./verify_bootstrap.sh

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Counters
PASSED=0
FAILED=0
WARNINGS=0

# Auto-detect user and directory (same logic as bootstrap.sh)
if [ -n "$SUDO_USER" ]; then
    USER="$SUDO_USER"
elif [ "$USER" = "root" ] || [ -z "$USER" ]; then
    USER=$(getent passwd | awk -F: '$3 >= 1000 && $1 != "nobody" {print $1; exit}')
    [ -z "$USER" ] && USER="user"
fi
HOME_DIR="/home/$USER"
DIR="$HOME_DIR/vlc-player"
CONFIG_FILE="$DIR/config.env"

echo "=== Bootstrap Verification ==="
echo "User: $USER"
echo "Install directory: $DIR"
echo ""

# Function to check and report
check() {
    if [ $? -eq 0 ]; then
        echo -e "${GREEN}✓${NC} $1"
        ((PASSED++))
        return 0
    else
        echo -e "${RED}✗${NC} $1"
        ((FAILED++))
        return 1
    fi
}

warn() {
    echo -e "${YELLOW}⚠${NC} $1"
    ((WARNINGS++))
}

# ============================================================================
# 1. SYSTEM CONFIGURATION
# ============================================================================

echo "=== 1. System Configuration ==="

# Check hostname
DEVICE_ID=$(hostname)
if [ -n "$DEVICE_ID" ] && [ "$DEVICE_ID" != "raspberrypi" ]; then
    check "Hostname set to: $DEVICE_ID"
else
    warn "Hostname not set or still default"
fi

# Check /etc/hosts
if grep -q "127.0.0.1.*$DEVICE_ID\|$DEVICE_ID.*127.0.0.1" /etc/hosts 2>/dev/null; then
    check "Hostname in /etc/hosts"
else
    warn "Hostname not in /etc/hosts"
fi

# Check VLC installation
if command -v vlc &> /dev/null; then
    VLC_VERSION=$(vlc --version 2>/dev/null | head -1 || echo "installed")
    check "VLC installed ($VLC_VERSION)"
else
    warn "VLC not installed"
fi

echo ""

# ============================================================================
# 2. FILE STRUCTURE
# ============================================================================

echo "=== 2. File Structure ==="

# Check directory exists
[ -d "$DIR" ] && check "Install directory exists: $DIR" || warn "Install directory missing: $DIR"

# Required code files
REQUIRED_FILES=(
    "main.py"
    "config.py"
    "media_sync.py"
    "code_update.py"
    "bootstrap.sh"
    "stop_vlc.sh"
    "config.env"
)

for file in "${REQUIRED_FILES[@]}"; do
    if [ -f "$DIR/$file" ]; then
        check "File exists: $file"
        
        # Check if executable (for Python/Shell scripts)
        if [[ "$file" == *.py ]] || [[ "$file" == *.sh ]]; then
            if [ -x "$DIR/$file" ]; then
                check "  → Executable permission set"
            else
                warn "  → Missing executable permission"
            fi
        fi
    else
        warn "File missing: $file"
    fi
done

# Check systemd directory
if [ -d "$DIR/systemd" ]; then
    check "Systemd directory exists"
    
    # Check systemd files
    for file in "vlc-player.service" "vlc-maintenance.service" "vlc-maintenance.timer"; do
        if [ -f "$DIR/systemd/$file" ]; then
            check "Systemd file exists: $file"
        else
            warn "Systemd file missing: $file"
        fi
    done
else
    warn "Systemd directory missing"
fi

# Check ownership
if [ -d "$DIR" ]; then
    OWNER=$(stat -c '%U' "$DIR" 2>/dev/null || stat -f '%Su' "$DIR" 2>/dev/null)
    if [ "$OWNER" = "$USER" ]; then
        check "Directory owned by $USER"
    else
        warn "Directory owned by $OWNER (expected $USER)"
    fi
fi

echo ""

# ============================================================================
# 3. CONFIGURATION
# ============================================================================

echo "=== 3. Configuration ==="

if [ -f "$CONFIG_FILE" ]; then
    check "Config file exists: $CONFIG_FILE"
    
    # Check for required config values
    source "$CONFIG_FILE" 2>/dev/null || true
    
    [ -n "$DROPBOX_URL" ] && check "  → DROPBOX_URL configured" || warn "  → DROPBOX_URL missing"
    [ -n "$DEVICE_ID" ] && check "  → DEVICE_ID configured ($DEVICE_ID)" || warn "  → DEVICE_ID missing"
    [ -n "$GITHUB_REPO_OWNER" ] && check "  → GITHUB_REPO_OWNER configured" || warn "  → GITHUB_REPO_OWNER missing"
else
    warn "Config file missing: $CONFIG_FILE"
fi

echo ""

# ============================================================================
# 4. MEDIA
# ============================================================================

echo "=== 4. Media ==="

if [ -d "$DIR/media" ]; then
    check "Media directory exists"
    
    if [ -f "$DIR/media/playlist.m3u" ]; then
        check "Playlist exists: playlist.m3u"
        
        # Count media files
        MEDIA_COUNT=$(find "$DIR/media" -type f \( -name "*.mp4" -o -name "*.avi" -o -name "*.mkv" \) 2>/dev/null | wc -l)
        if [ "$MEDIA_COUNT" -gt 0 ]; then
            check "Media files found: $MEDIA_COUNT"
        else
            warn "No media files found in media directory"
        fi
    else
        warn "Playlist missing (media sync may have failed)"
    fi
else
    warn "Media directory missing (media sync may have failed)"
fi

echo ""

# ============================================================================
# 5. SYSTEMD SERVICES
# ============================================================================

echo "=== 5. Systemd Services ==="

# Check if services exist in /etc/systemd/system/
for service in "vlc-player.service" "vlc-maintenance.service" "vlc-maintenance.timer"; do
    if [ -f "/etc/systemd/system/$service" ]; then
        check "Service file installed: $service"
        
        # Check if placeholders are replaced
        if grep -q "__USER__\|__DIR__" "/etc/systemd/system/$service" 2>/dev/null; then
            warn "  → Placeholders not replaced in $service"
        else
            check "  → Placeholders replaced"
        fi
        
        # Check if enabled
        if systemctl is-enabled "$service" &>/dev/null; then
            check "  → Service enabled"
        else
            warn "  → Service not enabled"
        fi
    else
        warn "Service file missing: $service"
    fi
done

# Check service status
if systemctl is-active --quiet vlc-player 2>/dev/null; then
    check "vlc-player service is running"
else
    warn "vlc-player service not running"
fi

if systemctl is-active --quiet vlc-maintenance.timer 2>/dev/null; then
    check "vlc-maintenance.timer is active"
else
    warn "vlc-maintenance.timer not active"
fi

echo ""

# ============================================================================
# 6. CRON JOB
# ============================================================================

echo "=== 6. Watchdog Cron ==="

if crontab -u "$USER" -l 2>/dev/null | grep -q "vlc-player"; then
    check "Watchdog cron installed"
else
    warn "Watchdog cron not found"
fi

echo ""

# ============================================================================
# SUMMARY
# ============================================================================

echo "=== Summary ==="
echo -e "${GREEN}Passed: $PASSED${NC}"
echo -e "${RED}Failed: $FAILED${NC}"
echo -e "${YELLOW}Warnings: $WARNINGS${NC}"
echo ""

if [ $FAILED -eq 0 ] && [ $WARNINGS -eq 0 ]; then
    echo -e "${GREEN}✓ All checks passed! Bootstrap completed successfully.${NC}"
    exit 0
elif [ $FAILED -eq 0 ]; then
    echo -e "${YELLOW}⚠ Bootstrap completed with warnings.${NC}"
    exit 0
else
    echo -e "${RED}✗ Bootstrap has failures. Please review above.${NC}"
    exit 1
fi


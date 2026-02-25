#!/bin/bash
# Bootstrap VLC Player for Raspberry Pi using git clone
# Usage (one-liner):
#   curl -sSL https://raw.githubusercontent.com/Digital-Out-Of-Home/Berlin-dooh-device/main/bootstrap.sh | sudo bash
# Or from repo root (config.env must be in current directory):
#   cd ~/vlc-player && sudo ./bootstrap.sh
set -e

# --- Detect user/home/dir -----------------------------------------------------
if [ -n "$SUDO_USER" ]; then
  USER="$SUDO_USER"
elif [ "$USER" != "root" ] && [ -n "$USER" ]; then
  # Already running as a non-root user
  USER="$USER"
else
  # Running as root, try to detect the actual user
  # First try to get the user from the process that invoked sudo
  USER=$(logname 2>/dev/null || echo "")
  if [ -z "$USER" ] || [ "$USER" = "root" ]; then
    # Fallback: find first non-root user with UID >= 1000
    USER=$(getent passwd | awk -F: '$3 >= 1000 && $1 != "nobody" {print $1; exit}')
    [ -z "$USER" ] && USER="pi"
  fi
fi

# Get the actual home directory for this user (don't assume /home/$USER)
HOME_DIR=$(getent passwd "$USER" | cut -d: -f6)
if [ -z "$HOME_DIR" ] || [ ! -d "$HOME_DIR" ]; then
  # Fallback to /home/$USER if getent fails
  HOME_DIR="/home/$USER"
fi

DIR="$HOME_DIR/vlc-player"
USER_UID=$(id -u "$USER")
# Track whether we changed rotation-related settings (for optional reboot)
ROTATION_CHANGED=false
WAYFIRE_REMOVED=false

# Installation log on user's Desktop
INSTALL_LOG="$HOME_DIR/Desktop/berlin-dooh-bootstrap.log"
mkdir -p "$(dirname "$INSTALL_LOG")"
touch "$INSTALL_LOG"
chown "$USER:$USER" "$(dirname "$INSTALL_LOG")" "$INSTALL_LOG" 2>/dev/null || true
exec > >(tee -a "$INSTALL_LOG") 2>&1
echo "[$(date -Iseconds)] === Bootstrap started (user=$USER, dir=$DIR) ==="

echo "=== VLC Player Bootstrap ==="
echo "User: $USER"
echo "Install directory: $DIR"

# --- Force kernel-level 90° rotation on HDMI-A-1 (Pi 5 / Wayland) ------------
CMDLINE_PATH="/boot/firmware/cmdline.txt"
ROTATE_ARG="video=HDMI-A-1:rotate=90"

if [ -f "$CMDLINE_PATH" ]; then
  if grep -q "$ROTATE_ARG" "$CMDLINE_PATH"; then
    echo "Kernel rotation already present in $CMDLINE_PATH"
  else
    echo "Adding kernel rotation to $CMDLINE_PATH: $ROTATE_ARG"
    # Append to the single existing line (no new line created)
    sudo sed -i "s|\$| $ROTATE_ARG|" "$CMDLINE_PATH"
    ROTATION_CHANGED=true
  fi
else
  echo "WARNING: $CMDLINE_PATH not found; skipping kernel rotation config."
fi

# --- Clean up Wayfire compositor overrides ------------------------------------
WAYFIRE_INI="$HOME_DIR/.config/wayfire.ini"
if [ -f "$WAYFIRE_INI" ]; then
  echo "Removing cached Wayfire config at $WAYFIRE_INI"
  sudo rm -f "$WAYFIRE_INI" || true
  WAYFIRE_REMOVED=true
fi

# --- Install dependencies -----------------------------------------------------
echo "[1/3] Installing dependencies (git, vlc, wlr-randr, raindrop, cec-utils)..."
apt update
apt install -y git vlc wlr-randr raindrop cec-utils
echo "[$(date -Iseconds)] [1/3] Dependencies: OK"

# --- Clone or update repo -----------------------------------------------------
echo "[2/3] Fetching code from GitHub..."

REPO_URL="https://github.com/Digital-Out-Of-Home/Berlin-dooh-device.git"

if [ -d "$DIR/.git" ]; then
  echo "Repo already exists, updating..."
  cd "$DIR"
  git remote set-url origin "$REPO_URL"
  git fetch origin
  git reset --hard origin/test-power-schedule
  git clean -fd
else
  echo "Cloning fresh copy..."
  sudo -u "$USER" git clone "$REPO_URL" "$DIR"
  cd "$DIR"
fi

chown -R "$USER:$USER" "$DIR"

echo "[$(date -Iseconds)] [2/3] Repo clone/update: OK"

# --- Config: No longer using .env files (configured via environment variables) ---
echo "[$(date -Iseconds)] Config: Skipped (using environment variables)"

# --- Install systemd services -------------------------------------------------
echo "[3/3] Installing systemd services..."

# Replace placeholders in service files before copying
for service_file in "$DIR/systemd/"*.service "$DIR/systemd/"*.timer; do
  if [ -f "$service_file" ]; then
    sed -i "s|__USER__|$USER|g" "$service_file"
    sed -i "s|__DIR__|$DIR|g" "$service_file"
    sed -i "s|__USER_UID__|$USER_UID|g" "$service_file"
  fi
done

cp "$DIR/systemd/"*.service "$DIR/systemd/"*.timer /etc/systemd/system/
systemctl daemon-reload

echo "Running initial setup scripts before enabling services..."

# Load environment variables if they are set system-wide
if [ -f /etc/environment ]; then
  set -a; source /etc/environment; set +a
fi

# Run the python scripts as $USER but preserve the environment variables (-E)
sudo -E -u "$USER" python3 "$DIR/src/media_sync.py" || true
sudo -E -u "$USER" python3 "$DIR/src/scheduler_sync.py" || true
sudo -E -u "$USER" python3 "$DIR/src/main.py" &

# Enable only units with [Install]: main service + timers (oneshot services are triggered by timers)
echo "Enabling service: vlc-player.service"
systemctl enable vlc-player.service
for f in "$DIR/systemd/"*.timer; do
  if [ -f "$f" ]; then
    echo "Enabling timer: $(basename "$f")"
    systemctl enable "$(basename "$f")"
  fi
done
# Start the long-running service and all timers
echo "Starting service: vlc-player.service"
systemctl start vlc-player
for f in "$DIR/systemd/"*.timer; do
  if [ -f "$f" ]; then
    echo "Starting timer: $(basename "$f")"
    systemctl start "$(basename "$f")"
  fi
done
echo "[$(date -Iseconds)] [3/3] Systemd services installed and started: OK"

# --- Desktop helper for manual screen rotation (optional) ----------------------
DESKTOP_DIR="$HOME_DIR/Desktop"
ROTATE_HELPER="$DESKTOP_DIR/RotateScreen.desktop"

mkdir -p "$DESKTOP_DIR"
chown "$USER:$USER" "$DESKTOP_DIR" 2>/dev/null || true

sudo -u "$USER" tee "$ROTATE_HELPER" >/dev/null <<EOF
[Desktop Entry]
Type=Application
Name=Rotate Screen 90°
Comment=Rotate HDMI-A-1 to 90° using wlr-randr
Exec=$DIR/scripts/rotate_screen_right.sh
Terminal=true
Icon=display
EOF

sudo -u "$USER" chmod +x "$ROTATE_HELPER" 2>/dev/null || true
echo "Desktop helper created: $ROTATE_HELPER (double-click to rotate)"

# --- Executable permissions (once after all steps that may overwrite files) ------
[ -f "$DIR/bootstrap.sh" ] && chmod +x "$DIR/bootstrap.sh"
find "$DIR/src" -maxdepth 1 -type f -name "*.py" -exec chmod +x {} \;
find "$DIR/scripts" -maxdepth 1 -type f -name "*.sh" -exec chmod +x {} \;

if [ "$ROTATION_CHANGED" = true ] || [ "$WAYFIRE_REMOVED" = true ]; then
  echo "Rotation settings applied. Rebooting in 5 seconds..."
  sleep 5
  sudo reboot
fi

echo "[$(date -Iseconds)] === Bootstrap finished ==="
echo ""
echo "=== Bootstrap Complete ==="
echo "User:   $USER"
echo "Dir:    $DIR"

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
CONFIG_FILE="$DIR/config.env"
SECRETS_FILE="$DIR/secrets.env"
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
echo "[1/3] Installing dependencies (git, vlc, wlr-randr, raindrop)..."
apt update
apt install -y git vlc wlr-randr raindrop
echo "[$(date -Iseconds)] [1/3] Dependencies: OK"

# --- Clone or update repo -----------------------------------------------------
echo "[2/3] Fetching code from GitHub..."

REPO_URL="https://github.com/Digital-Out-Of-Home/Berlin-dooh-device.git"

if [ -d "$DIR/.git" ]; then
  echo "Repo already exists, updating..."
  cd "$DIR"
  git remote set-url origin "$REPO_URL"
  git fetch origin
  git reset --hard origin/main
  git clean -fd
else
  echo "Cloning fresh copy..."
  sudo -u "$USER" git clone "$REPO_URL" "$DIR"
  cd "$DIR"
fi

chown -R "$USER:$USER" "$DIR"

echo "[$(date -Iseconds)] [2/3] Repo clone/update: OK"

# --- Config: config.env (static, from repo) + secrets.env (copy from USB) -------
# config.env is in the repo and already in $DIR after clone; code_update will overwrite it (OK).
# secrets.env is NOT in Git: copy from USB to $DIR after bootstrap, or from PWD if present now.

if [ ! -f "$CONFIG_FILE" ]; then
  echo "ERROR: config.env missing in $DIR (expected from repo after clone)."
  exit 1
fi
echo "Static config: $CONFIG_FILE (from repo)"

if [ -f "$PWD/secrets.env" ]; then
  cp "$PWD/secrets.env" "$SECRETS_FILE"
  chmod 600 "$SECRETS_FILE"
  chown "$USER:$USER" "$SECRETS_FILE"
  echo "Secrets installed from current directory: $SECRETS_FILE"
elif [ -f "$SECRETS_FILE" ]; then
  echo "Secrets already in place: $SECRETS_FILE"
else
  echo "WARNING: No secrets.env found. Copy secrets.env from USB to $DIR after bootstrap (DEVICE_ID, API_TOKEN)."
fi
echo "[$(date -Iseconds)] Config: OK"

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

# Enable only units with [Install]: main service + timers (oneshot services are triggered by timers)
systemctl enable vlc-player.service
for f in "$DIR/systemd/"*.timer; do
  [ -f "$f" ] && systemctl enable "$(basename "$f")"
done
# Start the long-running service and all timers
systemctl start vlc-player
for f in "$DIR/systemd/"*.timer; do
  [ -f "$f" ] && systemctl start "$(basename "$f")"
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
echo "Config: $CONFIG_FILE"

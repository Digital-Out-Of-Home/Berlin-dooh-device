#!/bin/bash
# VLC Player Install for Raspberry Pi. Run: sudo ./install.sh
set -e
DIR="/home/pi/vlc-player"
mkdir -p "$DIR"
cp main.py "$DIR/"
chmod +x "$DIR/main.py"
cp systemd/*.service systemd/*.timer /etc/systemd/system/
systemctl daemon-reload
systemctl enable vlc-sync.timer vlc-player
systemctl start vlc-sync.timer vlc-player
echo "Installed! Commands:"
echo "  systemctl status vlc-player"
echo "  python3 $DIR/main.py sync"

# VLC Playlist Player

Syncs media from a ZIP URL (e.g. Dropbox) and plays on loop using VLC. Designed for Raspberry Pi digital signage, but works on any Linux box with VLC.

### Configuration

All configuration lives in `config.env`:

```bash
# Device-specific
DEVICE_ID=berlin1

# Content ZIP URL (e.g. Dropbox ?dl=1 link)
DROPBOX_URL=https://www.dropbox.com/scl/fo/YOUR_FOLDER_ID/...?dl=1
```

Place `config.env` in the same directory as the Python scripts.

### Manual Installation (Recommended)

1. Copy the project folder (e.g. `vlc-player/`) to the device:
   - `main.py`
   - `media_sync.py`
   - `config.py`
   - `config.env`
   - `systemd/` (with service + timer units)
2. Install VLC:
   ```bash
   sudo apt update && sudo apt install -y vlc
   ```
3. Enable the services:
   ```bash
   sudo cp systemd/*.service systemd/*.timer /etc/systemd/system/
   sudo systemctl daemon-reload
   sudo systemctl enable vlc-player vlc-maintenance.timer
   sudo systemctl start vlc-player vlc-maintenance.timer
   ```

### Usage

- **Manual sync**:
  ```bash
  python3 ~/vlc-player/media_sync.py
  ```
- **Manual playback**:
  ```bash
  python3 ~/vlc-player/main.py
  ```
- **Service management**:
  ```bash
  systemctl status vlc-player
  systemctl status vlc-maintenance.timer
  systemctl restart vlc-player
  journalctl -u vlc-player -f
  journalctl -u vlc-maintenance -f
  ```

### How It Works

- `media_sync.py` downloads a ZIP from `DROPBOX_URL`, extracts into a staging directory, checks that at least one `.m3u` playlist exists, then atomically swaps it into `media/`.
- `main.py` looks for `media/playlist.m3u` and starts VLC in fullscreen loop mode.
- `vlc-maintenance.timer` runs `media_sync.py` periodically so content stays up to date.

### File Structure

```text
~/vlc-player/  (or /home/<username>/vlc-player/)
├── main.py              # VLC player script (play only)
├── media_sync.py        # Media sync script (downloads ZIP + extracts)
├── config.py            # Shared configuration utilities
├── config.env           # Configuration file (DEVICE_ID, DROPBOX_URL)
├── media/               # Downloaded media
│   ├── playlist.m3u
│   └── *.mp4
└── systemd/             # Service files
    ├── vlc-maintenance.service
    ├── vlc-maintenance.timer
    └── vlc-player.service
```

### Requirements

- Raspberry Pi (or any Linux device with display)
- Raspberry Pi OS / Debian-based distro
- VLC (`sudo apt install vlc`)
- Internet connection (for content sync)

### Troubleshooting

- **No video playing?**
  ```bash
  journalctl -u vlc-player -n 50
  python3 ~/vlc-player/media_sync.py
  ls ~/vlc-player/media/
  ```
- **Sync not working?**
  ```bash
  systemctl status vlc-maintenance.timer
  journalctl -u vlc-maintenance -f
  cat ~/vlc-player/config.env
  ```

## License

MIT

# VLC Playlist Player

Syncs media from an API (Smart Sync) and plays on loop using VLC. Designed for Raspberry Pi digital signage, but works on any Linux box with VLC or via Docker.

### Configuration

All configuration lives in `config.env`. The system uses the following variables:

```bash
# Device Identity
DEVICE_ID=berlin1

# API Configuration
API_URL=https://your-backend-api.com/api/v1/campaign/playlist/
API_TOKEN=your_secure_api_token
HOST_URL=https://your-backend-api.com
# Optional Health Check
HEALTHCHECK_URL=https://hc-ping.com/your-uuid-here
```

Place `config.env` in the same directory as the Python scripts.

### One-Line Install (Recommended, Raspberry Pi)

On a fresh device:

1. Create a `config.env` file in your current directory with your device settings.
2. Run the bootstrap script:

```bash
curl -sSL https://raw.githubusercontent.com/Digital-Out-Of-Home/Berlin-dooh-device/main/scripts/bootstrap.sh | sudo bash
```

This will:

- Install `git` and `vlc`
- Clone/update the repo to `~/vlc-player`
- Create `config.env` with your provided secrets (chmod 600)
- Install + enable `vlc-player.service`, `vlc-maintenance.timer`, and `vlc-healthcheck.timer`
- Start playback and periodic media sync

### Docker Support

You can run the player in a container (useful for testing or containerized deployments).

1. **Build and Run**:
   ```bash
   docker-compose up --build -d
   ```

2. **Configuration**:
   Create a `config.env` file in the project root before running.

### Manual Installation (Alternative)

1. Copy the project folder (e.g. `vlc-player/`) to the device.
2. Create `config.env` with the required variables (see Configuration above).
3. Install VLC and Git:
   ```bash
   sudo apt update && sudo apt install -y vlc git
   ```
4. Enable the services:
   ```bash
   cd ~/vlc-player
   sudo cp systemd/*.service systemd/*.timer /etc/systemd/system/
   sudo systemctl daemon-reload
   sudo systemctl enable vlc-player vlc-maintenance.timer vlc-healthcheck.timer
   sudo systemctl start vlc-player vlc-maintenance.timer vlc-healthcheck.timer
   ```

### Usage

- **Manual media sync**:
  ```bash
  python3 src/media_sync.py
  ```
- **Manual playback**:
  ```bash
  python3 src/main.py
  ```
- **Service management**:
  ```bash
  systemctl status vlc-player
  systemctl status vlc-maintenance.timer
  journalctl -u vlc-player -f
  ```

### Automatic Code Updates (Every 4 Hours, Optional)

Code updates are git-based and handled by `src/code_update.py`.

1. Install the code-update units:
   ```bash
   cd ~/vlc-player
   sudo cp systemd/vlc-code-update.service systemd/vlc-code-update.timer /etc/systemd/system/
   sudo systemctl daemon-reload
   sudo systemctl enable vlc-code-update.timer
   sudo systemctl start vlc-code-update.timer
   ```

2. To trigger a manual update at any time:

   ```bash
   cd ~/vlc-player
   python3 code_update.py
   ```

This will run `git fetch` + `git reset --hard origin/main` and restart `vlc-player` and `vlc-maintenance.timer`.

### Migrating Existing Devices to Git-Based Setup

On a device that already has an older `vlc-player` install:

```bash
cd /home/pi
curl -sSL https://raw.githubusercontent.com/Digital-Out-Of-Home/Berlin-dooh-device/main/migrate_to_git.sh -o migrate_to_git.sh
chmod +x migrate_to_git.sh
sudo ./migrate_to_git.sh
```

The script will:

- Stop existing services
- Back up the old `~/vlc-player` to `~/vlc-player-old-<timestamp>`
- Run the latest `bootstrap.sh` from GitHub
- Restore `config.env` and `media/` from the backup (if present)
- Restart `vlc-player` and `vlc-maintenance.timer`

You can then optionally enable the 4‑hour code update timer as described above.
2. This will run `git fetch` + `git reset --hard origin/main` and restart services.

### How It Works

- **`src/media_sync.py`** (Smart Sync):
  1. Authenticates with `API_TOKEN` and fetches the active campaign playlist for `DEVICE_ID` from `API_URL`.
  2. Compares the list of required media files against files currently on disk.
  3. Downloads *only* the missing files from `HOST_URL`.
  4. Removes any files on disk that are no longer in the campaign.
  5. Generates a local `playlist.m3u` for VLC.
- **`src/main.py`**: Starts VLC in headless/fullscreen mode playing `media/playlist.m3u`.
- **`vlc-maintenance.timer`**: Runs `media_sync.py` periodically so content stays up to date.

### File Structure

```text
~/vlc-player/
├── config.env                # Secrets (GitIgnored)
├── Dockerfile                # Container build definition
├── docker-compose.yml        # Container orchestration
├── src/
│   ├── main.py               # VLC player script
│   ├── media_sync.py         # Smart media sync
│   ├── health_check.py       # Health check script
│   ├── code_update.py        # Git-based updater
│   └── config.py             # Configuration loader
├── scripts/
│   ├── bootstrap.sh          # Installer
│   └── verify_bootstrap.sh   # Verification
├── media/                    # Local content cache
│   ├── playlist.m3u
│   └── *.mp4
└── systemd/                  # Service units
```

### License
MIT

### Testing

To run the unit tests:

```bash
python3 -m unittest discover tests
```

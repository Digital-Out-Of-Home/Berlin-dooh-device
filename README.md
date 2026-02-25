# VLC Playlist Player

Syncs media from an API (Smart Sync) and plays on loop using VLC. Designed for Raspberry Pi digital signage, but works on any Linux box with VLC.

### Configuration

Configuration is provided via the following environment variables:

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


### One-Line Install (Recommended, Raspberry Pi)

On a fresh device:

1. Ensure environment variables (`DEVICE_ID`, `API_TOKEN`, etc.) are provided. 
   *(Note: Export them in your terminal beforehand and use `sudo -E` to preserve them during bootstrap, or place them globally in `/etc/environment`)*
2. Run the bootstrap script:

```bash
curl -sSL https://raw.githubusercontent.com/Digital-Out-Of-Home/Berlin-dooh-device/main/bootstrap.sh | sudo -E bash
```

This will:

- Install required packages (`git`, `vlc`, `wlr-randr`, `raindrop`, `cec-utils`)
- Clone/update the repo to `~/vlc-player`
- Install all `systemd` unit files from `systemd/`
- Enable `vlc-player.service` and all `*.timer` units
  (maintenance, code-update, scheduler-sync, power-control)
- Start `vlc-player` and all enabled timers

### Manual Installation (Alternative)

1. Copy the project folder (e.g. `vlc-player/`) to the device.
2. Ensure environment variables are exposed to the user/systemd (see Configuration above).
3. Install VLC and Git:
   ```bash
   sudo apt update && sudo apt install -y vlc git
   ```
4. Enable the services:
   ```bash
   cd ~/vlc-player
   sudo cp systemd/*.service systemd/*.timer /etc/systemd/system/
   sudo systemctl daemon-reload
   # Always enable the main service and maintenance timer:
   sudo systemctl enable vlc-player vlc-maintenance.timer
   sudo systemctl start vlc-player vlc-maintenance.timer

   # Optional but recommended timers:
   # - vlc-code-update.timer: periodic git-based code updates
   # - vlc-scheduler-sync.timer: fetch power schedule from backend
   # - vlc-power-control.timer: enforce power schedule via HDMI-CEC
   sudo systemctl enable vlc-code-update.timer vlc-scheduler-sync.timer vlc-power-control.timer
   sudo systemctl start vlc-code-update.timer vlc-scheduler-sync.timer vlc-power-control.timer
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
   python3 src/code_update.py
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
- Restore `media/` from the backup (if present)
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
- **`src/health_check.py`** (optional): Pings a configured `HEALTHCHECK_URL`. If you want this to run automatically, you can add your own `vlc-healthcheck.service`/`.timer` units.
- **`src/code_update.py`**: Performs git-based updates (`origin/main`) and restarts services. Triggered by `vlc-code-update.timer` if installed.
- **`src/scheduler_sync.py`**: Fetches the device's operating schedule from the backend (`/api/devices/{DEVICE_ID}/`) and writes it to `media/schedule.json`.
- **`src/power_control.py`**: Reads `media/schedule.json`, decides whether the display should be on or off for the current time/day, and sends HDMI‑CEC commands via `cec-client`.
- **`vlc-scheduler-sync.timer`**: Runs `scheduler_sync.py` periodically (default: every 15 minutes).
- **`vlc-power-control.timer`**: Runs `power_control.py` every minute to enforce the current schedule.

### File Structure

```text
~/vlc-player/
├── bootstrap.sh              # Installer (run from here)
├── src/
│   ├── main.py               # VLC player script
│   ├── media_sync.py         # Smart media sync
│   ├── health_check.py       # Health check script (manual or custom timer)
│   ├── code_update.py        # Git-based updater
│   ├── scheduler_sync.py     # Schedule fetcher (device operating hours)
│   ├── power_control.py      # HDMI-CEC power control based on schedule
│   └── config.py             # Configuration loader
├── scripts/
│   └── verify_bootstrap.sh   # Verification
├── media/                    # Local content cache
│   ├── playlist.m3u
│   ├── schedule.json         # Cached power schedule
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

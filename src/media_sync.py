#!/usr/bin/env python3
"""Media Sync from Dropbox with safety measures. Usage: python media_sync.py"""
import os
import sys
import tempfile
import time
import json
import urllib.error
from pathlib import Path
from urllib.request import Request, urlopen
from urllib.parse import urljoin

from config import BASE_DIR, get_device_id, load_config, create_http_opener

# ============================================================================
# CONFIGURATION
# ============================================================================

config = load_config()

MEDIA_DIR = BASE_DIR / "media"
STAGING_DIR = BASE_DIR / ".media_staging"
SYNC_LOCK = Path("/tmp/vlc-sync.lock")
LOCK_STALE_SECONDS = 60 * 60  # 1 hour before lock is considered stale

DROPBOX_URL = "" # Deprecated
API_URL = config["API_URL"]
API_TOKEN = config["API_TOKEN"]
HOST_URL = config["HOST_URL"]

# ============================================================================
# HELPER FUNCTIONS
# ============================================================================

def is_process_running(pid: int) -> bool:
    """Best-effort check whether a PID is currently running."""
    try:
        os.kill(pid, 0)
    except ProcessLookupError:
        return False  # no such process
    except PermissionError:
        return True   # process exists but we can't signal it
    else:
        return True


def acquire_lock(force: bool) -> bool:
    """
    Acquire the sync lock with stale detection.

    Returns:
        True  - lock acquired, safe to run
        False - another (likely active) sync is running, should skip
    """
    # Fast path: no lock yet
    if not SYNC_LOCK.exists():
        pid = os.getpid()
        now = time.time()
        SYNC_LOCK.write_text(f"{pid}:{now}\n")
        return True

    # Lock exists: inspect it
    try:
        content = SYNC_LOCK.read_text().strip()
        pid_str, ts_str = content.split(":", 1)
        old_pid = int(pid_str)
        old_ts = float(ts_str)
    except Exception:
        print("Lock file is corrupt; treating as stale and overriding it.")
        old_pid = None
        old_ts = 0.0

    now = time.time()
    age = now - old_ts if old_ts else None
    is_stale = age is not None and age > LOCK_STALE_SECONDS
    running = old_pid is not None and is_process_running(old_pid)

    if running and not is_stale:
        # Active sync detected
        if force:
            print(
                f"Sync appears to be running (PID {old_pid}); "
                "not overriding lock even with --force."
            )
        else:
            print(f"Sync already in progress (PID {old_pid}), skipping...")
        return False

    # No active process or stale lock – safe to override
    if is_stale:
        print(
            f"Stale lock detected (PID {old_pid}, age ~{int(age)}s); "
            "overriding and starting new sync."
        )
    else:
        print("Lock file present but no active process; overriding lock.")

    SYNC_LOCK.unlink(missing_ok=True)
    pid = os.getpid()
    SYNC_LOCK.write_text(f"{pid}:{now}\n")
    return True


def download_with_retry():
    """Download from Dropbox with single retry (with progress)."""
    if not DROPBOX_URL or not DROPBOX_URL.strip():
        raise Exception("DROPBOX_URL is not configured in config.env")
    
    for attempt in [1, 2]:
        zip_path = None
        try:
            print(f"Downloading from Dropbox... (attempt {attempt}/2)")
            if len(DROPBOX_URL) > 80:
                print(f"URL: {DROPBOX_URL[:80]}...")
            else:
                print(f"URL: {DROPBOX_URL}")
            
            opener = create_http_opener()
            req = Request(DROPBOX_URL, headers={"User-Agent": "Mozilla/5.0"})
            
            # Download with basic progress reporting
            response = opener.open(req, timeout=300)
            total_size = response.headers.get("Content-Length")
            total_size = int(total_size) if total_size else None
            
            print("  Downloading...", end="", flush=True)
            data = b""
            chunk_size = 8192
            downloaded = 0
            
            while True:
                chunk = response.read(chunk_size)
                if not chunk:
                    break
                data += chunk
                downloaded += len(chunk)
                
                if total_size:
                    percent = (downloaded / total_size) * 100
                    size_mb = downloaded / (1024 * 1024)
                    total_mb = total_size / (1024 * 1024)
                    print(
                        f"\r  Downloading... {percent:.1f}% ({size_mb:.1f} MB / {total_mb:.1f} MB)",
                        end="",
                        flush=True,
                    )
                else:
                    size_mb = downloaded / (1024 * 1024)
                    print(f"\r  Downloading... {size_mb:.1f} MB", end="", flush=True)
            
            print()  # newline after progress
            
            # Write to temp file
            with tempfile.NamedTemporaryFile(suffix=".zip", delete=False) as f:
                f.write(data)
                zip_path = Path(f.name)
            
            size_mb = len(data) / (1024 * 1024)
            print(f"  Download complete: {size_mb:.1f} MB")
            
            return zip_path
        except Exception as e:
            # Clean up temp file on error
            if zip_path and zip_path.exists():
                zip_path.unlink(missing_ok=True)
            
            print(f"  Failed: {e}")
            if "unknown url type" in str(e).lower():
                print("  Error: Invalid DROPBOX_URL format. Check config file.")
                raise
            if attempt < 2:
                print("  Retrying...")
                time.sleep(5)
            else:
                raise Exception("Download failed after 2 attempts")


def fetch_campaigns(device_id: str):
    """Fetch campaigns from API for the given device ID."""
    if not API_URL:
        raise Exception("API_URL is not configured")

    url = f"{API_URL}?device_id={device_id}"

    print(f"Fetching playlist from: {url}")
    
    headers = {
        "User-Agent": "Berlin-DOOH-Device/1.0",
        "Accept": "application/json"
    }
    
    if API_TOKEN:
        headers["Authorization"] = f"Bearer {API_TOKEN}"
        
    req = Request(url, headers=headers)
    
    try:
        with urlopen(req, timeout=30) as response:
            if response.status != 200:
                # Try to read error body if possible
                try:
                    error_body = response.read().decode('utf-8')
                except Exception:
                    error_body = "<no content>"
                raise Exception(f"API returned status {response.status}: {error_body}")
            data = response.read()
            return json.loads(data)
    except urllib.error.HTTPError as e:
        raise Exception(f"API HTTP Error: {e.code} {e.reason}")
    except urllib.error.URLError as e:
        raise Exception(f"API Connection Error: {e.reason}")
    except json.JSONDecodeError:
        raise Exception("Failed to decode API response JSON")


def generate_playlist_content(campaigns):
    """
    Generate m3u content from list of campaigns using local paths.
    Expected API response structure:
    [
      { "media_file": "string", ... }, ...
    ]
    """
    lines = ["#EXTM3U"]
    for item in campaigns:
        media_file = item.get("media_file")
        if media_file:
            # item['media_file'] is the relative path from server, e.g. "campaigns/video.mp4"
            filename = media_file.split("/")[-1]
            local_path = MEDIA_DIR / filename
            
            # Add metadata
            # #EXTINF:-1 server-url="campaigns/video.mp4",video.mp4
            lines.append(f'#EXTINF:-1 server-url="{media_file}",name="{filename}"')
            lines.append(str(local_path))
    
    return "\n".join(lines) + "\n"


def download_media_file(server_path):
    """Download a single media file from the CMS."""
    if not HOST_URL:
        print(f"  Error: HOST_URL not set, cannot download {server_path}")
        return False

    filename = Path(server_path).name
    url = urljoin(HOST_URL, server_path)
    target_path = MEDIA_DIR / filename
    
    print(f"  Downloading missing file: {filename} from {url}")
    
    try:
        opener = create_http_opener()
        req = Request(url, headers={"User-Agent": "Berlin-DOOH-Device/1.0"})
        
        with opener.open(req, timeout=300) as response:
            with open(target_path, "wb") as f:
                while True:
                    chunk = response.read(8192)
                    if not chunk:
                        break
                    f.write(chunk)
        print(f"  Successfully downloaded {filename}")
        return True
    except Exception as e:
        print(f"  Failed to download {filename}: {e}")
        # Clean up partial file
        if target_path.exists():
            target_path.unlink()
        return False


def get_playlist_media_names(playlist_path):
    """Extract set of media filenames from an existing m3u file."""
    if not playlist_path.exists():
        return set()
    
    filenames = set()
    try:
        lines = playlist_path.read_text(encoding="utf-8").splitlines()
        for line in lines:
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            # Handle both full paths and URLs by taking the name
            filenames.add(Path(line).name)
    except Exception:
        pass
    return filenames


def sync(force: bool = False):
    """
    Sync Logic:
    1. Fetch current campaigns via API
    2. Check if the media file names are same in the existing playlist
    3. If there is a difference:
        3.1 Download the missing media
        3.2 Remove the non-used media
        3.3 Update the playlist.m3u with local media file names/path
    4. If it's same, stop process
    """
    # Lock file to prevent concurrent syncs
    if not acquire_lock(force=force):
        return

    try:
        device_id = get_device_id()
        print(f"=== Media Sync (Smart) ===")
        print(f"Device: {device_id}")
        
        # 1. Fetch current campaigns via API
        try:
            campaigns = fetch_campaigns(device_id)
            print(f"  Fetched {len(campaigns)} campaign items")
        except Exception as e:
            print(f"  Error fetching campaigns: {e}")
            sys.exit(1)

        # Create map {basename: server_path} to handle download logic
        target_filenames = set()
        target_files_map = {}
        for item in campaigns:
            mfile = item.get("media_file")
            if mfile:
                basename = Path(mfile).name
                target_files_map[basename] = mfile
                target_filenames.add(basename)

        # 2. Check if the media file names are same in the existing playlist
        playlist_path = MEDIA_DIR / "playlist.m3u"
        current_filenames = get_playlist_media_names(playlist_path)
        
        if target_filenames == current_filenames:
            # 4. If it's same, stop process
            print("  Playlist and campaign files match. No changes needed.")
            print("=== Sync Complete ===")
            return

        print("  Differences detected. Starting sync process...")
        
        # Ensure media dir exists
        MEDIA_DIR.mkdir(parents=True, exist_ok=True)

        # 3. If there is a difference:
        
        # 3.1 Download the missing media
        # We check what is missing from DISK, not just playlist
        existing_files_on_disk = set(f.name for f in MEDIA_DIR.iterdir() if f.is_file() and f.name != "playlist.m3u")
        
        missing_files = target_filenames - existing_files_on_disk
        if missing_files:
            print(f"  Missing files to download: {missing_files}")
            for filename in missing_files:
                server_path = target_files_map[filename]
                download_media_file(server_path)
        else:
            print("  No missing media files to download.")

        # 3.2 Remove the non-used media
        unused_files = existing_files_on_disk - target_filenames
        if unused_files:
            print(f"  Unused files to remove: {unused_files}")
            for filename in unused_files:
                file_path = MEDIA_DIR / filename
                try:
                    file_path.unlink()
                    print(f"  Removed {filename}")
                except Exception as e:
                    print(f"  Error removing {filename}: {e}")
        else:
            print("  No unused media files to remove.")
            
        # 5. Update the playlist.m3u with local media file names/path
        new_content = generate_playlist_content(campaigns)
        try:
            playlist_path.write_text(new_content, encoding="utf-8")
            print(f"  Updated {playlist_path}")
        except Exception as e:
            print(f"  Error writing playlist: {e}")

        print("=== Sync Complete ===")
        
    except Exception as e:
        print(f"=== Sync Failed: {e} ===")
        sys.exit(1)
    
    finally:
        SYNC_LOCK.unlink(missing_ok=True)


if __name__ == "__main__":
    # Simple flag parser for manual overrides
    force = "--force" in sys.argv or "-f" in sys.argv
    sync(force=force)


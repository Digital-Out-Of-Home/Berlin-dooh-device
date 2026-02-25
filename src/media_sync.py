#!/usr/bin/env python3
"""Media Sync from Dropbox with safety measures. Usage: python media_sync.py"""
import logging
import os
import sys
import tempfile
import time
import json
import urllib.error
from pathlib import Path
from urllib.request import Request, urlopen
from urllib.parse import urljoin

from config import BASE_DIR, get_device_id, load_config, create_http_opener, setup_logging

setup_logging()
logger = logging.getLogger(__name__)

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
        return False
    except PermissionError:
        return True
    else:
        return True


def acquire_lock(force: bool) -> bool:
    """
    Acquire the sync lock with stale detection.

    Returns:
        True  - lock acquired, safe to run
        False - another (likely active) sync is running, should skip
    """
    if not SYNC_LOCK.exists():
        pid = os.getpid()
        now = time.time()
        SYNC_LOCK.write_text(f"{pid}:{now}\n")
        return True

    try:
        content = SYNC_LOCK.read_text().strip()
        pid_str, ts_str = content.split(":", 1)
        old_pid = int(pid_str)
        old_ts = float(ts_str)
    except Exception:
        logger.warning("Lock file is corrupt; treating as stale and overriding it.")
        old_pid = None
        old_ts = 0.0

    now = time.time()
    age = now - old_ts if old_ts else None
    is_stale = age is not None and age > LOCK_STALE_SECONDS
    running = old_pid is not None and is_process_running(old_pid)

    if running and not is_stale:
        if force:
            logger.warning(
                "Sync appears to be running (PID %s); not overriding lock even with --force.",
                old_pid,
            )
        else:
            logger.info("Sync already in progress (PID %s), skipping...", old_pid)
        return False

    if is_stale:
        logger.info(
            "Stale lock detected (PID %s, age ~%ss); overriding and starting new sync.",
            old_pid,
            int(age) if age else 0,
        )
    else:
        logger.debug("Lock file present but no active process; overriding lock.")

    SYNC_LOCK.unlink(missing_ok=True)
    pid = os.getpid()
    SYNC_LOCK.write_text(f"{pid}:{now}\n")
    return True


def download_with_retry():
    """Download from Dropbox with single retry (with progress)."""
    if not DROPBOX_URL or not DROPBOX_URL.strip():
        raise Exception("DROPBOX_URL is not configured")

    for attempt in [1, 2]:
        zip_path = None
        try:
            logger.info("Downloading from Dropbox... (attempt %s/2)", attempt)
            logger.debug("URL: %s", DROPBOX_URL[:80] + "..." if len(DROPBOX_URL) > 80 else DROPBOX_URL)

            opener = create_http_opener()
            req = Request(DROPBOX_URL, headers={"User-Agent": "Mozilla/5.0"})

            response = opener.open(req, timeout=300)
            total_size = response.headers.get("Content-Length")
            total_size = int(total_size) if total_size else None

            data = b""
            chunk_size = 8192
            downloaded = 0

            while True:
                chunk = response.read(chunk_size)
                if not chunk:
                    break
                data += chunk
                downloaded += len(chunk)
                if total_size and downloaded % (1024 * 1024) < chunk_size:
                    size_mb = downloaded / (1024 * 1024)
                    logger.debug("Downloading... %.1f MB", size_mb)

            with tempfile.NamedTemporaryFile(suffix=".zip", delete=False) as f:
                f.write(data)
                zip_path = Path(f.name)

            size_mb = len(data) / (1024 * 1024)
            logger.info("Download complete: %.1f MB", size_mb)
            return zip_path
        except Exception as e:
            if zip_path and zip_path.exists():
                zip_path.unlink(missing_ok=True)
            logger.warning("Download failed: %s", e)
            if "unknown url type" in str(e).lower():
                logger.error("Invalid DROPBOX_URL format. Check config file.")
                raise
            if attempt < 2:
                logger.info("Retrying...")
                time.sleep(5)
            else:
                raise Exception("Download failed after 2 attempts")


def fetch_campaigns(device_id: str):
    """Fetch campaigns from API for the given device ID."""
    if not API_URL:
        raise Exception("API_URL is not configured")

    url = f"{API_URL}?device_id={device_id}"
    logger.debug("Fetching playlist from: %s", url)

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
    """
    lines = ["#EXTM3U"]
    for item in campaigns:
        media_file = item.get("media_file")
        if media_file:
            filename = media_file.split("/")[-1]
            local_path = MEDIA_DIR / filename
            lines.append(f'#EXTINF:-1 server-url="{media_file}",name="{filename}"')
            lines.append(str(local_path))
    return "\n".join(lines) + "\n"


def download_media_file(server_path):
    """Download a single media file from the CMS."""
    if not HOST_URL:
        logger.error("HOST_URL not set, cannot download %s", server_path)
        return False

    filename = Path(server_path).name
    url = urljoin(HOST_URL, server_path)
    logger.info("Downloading missing file: %s", filename)

    try:
        opener = create_http_opener()
        req = Request(url, headers={"User-Agent": "Berlin-DOOH-Device/1.0"})

        with opener.open(req, timeout=300) as response:
            with open(MEDIA_DIR / filename, "wb") as f:
                while True:
                    chunk = response.read(8192)
                    if not chunk:
                        break
                    f.write(chunk)
        logger.info("Downloaded %s", filename)
        return True
    except Exception as e:
        logger.warning("Failed to download %s: %s", filename, e)
        target_path = MEDIA_DIR / filename
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
            filenames.add(Path(line).name)
    except Exception:
        pass
    return filenames


def sync(force: bool = False):
    """
    Sync Logic:
    1. Fetch current campaigns via API
    2. Check if the media file names are same in the existing playlist
    3. If there is a difference: download missing, remove unused, update playlist
    4. If same, stop
    """
    if not acquire_lock(force=force):
        return

    try:
        device_id = get_device_id()
        logger.info("Media sync starting (device: %s)", device_id)

        try:
            campaigns = fetch_campaigns(device_id)
            logger.debug("Fetched %s campaign items", len(campaigns))
        except Exception as e:
            logger.error("Error fetching campaigns: %s", e)
            sys.exit(1)

        target_filenames = set()
        target_files_map = {}
        for item in campaigns:
            mfile = item.get("media_file")
            if mfile:
                basename = Path(mfile).name
                target_files_map[basename] = mfile
                target_filenames.add(basename)

        playlist_path = MEDIA_DIR / "playlist.m3u"
        current_filenames = get_playlist_media_names(playlist_path)

        if target_filenames == current_filenames:
            logger.debug("Playlist and campaign match. No changes needed.")
            return

        logger.info("Differences detected; syncing...")
        MEDIA_DIR.mkdir(parents=True, exist_ok=True)

        existing_files_on_disk = set(
            f.name for f in MEDIA_DIR.iterdir()
            if f.is_file() and f.name != "playlist.m3u"
        )
        missing_files = target_filenames - existing_files_on_disk
        if missing_files:
            logger.debug("Missing files: %s", missing_files)
            for filename in missing_files:
                server_path = target_files_map[filename]
                download_media_file(server_path)
        else:
            logger.debug("No missing media files.")

        unused_files = existing_files_on_disk - target_filenames
        if unused_files:
            logger.debug("Unused files to remove: %s", unused_files)
            for filename in unused_files:
                file_path = MEDIA_DIR / filename
                try:
                    file_path.unlink()
                    logger.info("Removed %s", filename)
                except Exception as e:
                    logger.warning("Error removing %s: %s", filename, e)
        else:
            logger.debug("No unused media files to remove.")

        new_content = generate_playlist_content(campaigns)
        try:
            playlist_path.write_text(new_content, encoding="utf-8")
            logger.info("Updated playlist")
        except Exception as e:
            logger.error("Error writing playlist: %s", e)

        logger.info("Sync complete")
    except Exception as e:
        logger.error("Sync failed: %s", e)
        sys.exit(1)
    finally:
        SYNC_LOCK.unlink(missing_ok=True)


if __name__ == "__main__":
    force = "--force" in sys.argv or "-f" in sys.argv
    sync(force=force)

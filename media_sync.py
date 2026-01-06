#!/usr/bin/env python3
"""Media Sync from Dropbox with safety measures. Usage: python media_sync.py"""

import shutil
import subprocess
import sys
import tempfile
import time
import zipfile
from pathlib import Path
from urllib.request import Request

from config import BASE_DIR, get_device_id, load_config, create_http_opener

# ============================================================================
# CONFIGURATION
# ============================================================================

config = load_config()

MEDIA_DIR = BASE_DIR / "media"
STAGING_DIR = BASE_DIR / ".media_staging"
SYNC_LOCK = Path("/tmp/vlc-sync.lock")

DROPBOX_URL = config["DROPBOX_URL"]

# ============================================================================
# HELPER FUNCTIONS
# ============================================================================

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


def check_playlist_exists(media_dir):
    """Simple check: playlist exists and has at least one media file."""
    playlists = list(media_dir.glob("*.m3u"))
    if not playlists:
        return False
    
    # Quick check: playlist has at least one non-comment line
    for playlist in playlists:
        try:
            content = playlist.read_text()
            if any(line.strip() and not line.startswith("#") 
                   for line in content.splitlines()):
                return True
        except Exception:
            continue
    return False


# ============================================================================
# MAIN SYNC FUNCTION
# ============================================================================

def sync():
    """Download from Dropbox and safely swap media (simplified)."""
    # Lock file to prevent concurrent syncs (atomic creation)
    try:
        SYNC_LOCK.touch(exist_ok=False)  # Fails if file already exists
    except FileExistsError:
        print("Sync already in progress, skipping...")
        return
    
    try:
        device_id = get_device_id()
        print(f"=== Media Sync ===")
        print(f"Device: {device_id}")
        
        # Validate DROPBOX_URL
        if not DROPBOX_URL or not DROPBOX_URL.strip():
            raise Exception("DROPBOX_URL is not configured in config.env")
        
        # Clean staging directory
        if STAGING_DIR.exists():
            shutil.rmtree(STAGING_DIR, ignore_errors=True)
        STAGING_DIR.mkdir(parents=True, exist_ok=True)
        
        # Download and extract
        zip_path = download_with_retry()
        
        print("Extracting archive...")
        extracted_files = []
        with zipfile.ZipFile(zip_path) as zf:
            file_list = zf.namelist()
            total_files = len(file_list)
            print(f"  Found {total_files} file(s) in archive")
            
            for i, member in enumerate(file_list, 1):
                zf.extract(member, STAGING_DIR)
                extracted_files.append(member)
                if i % 10 == 0 or i == total_files:
                    # Show progress every 10 files or at the end
                    end_char = "\r" if i < total_files else "\n"
                    print(f"  Extracted {i}/{total_files} files...", end=end_char, flush=True)
        zip_path.unlink()
        print(f"  Extraction complete: {len(extracted_files)} file(s)")
        
        # Show file statistics
        media_files = [f for f in STAGING_DIR.rglob("*") if f.is_file()]
        total_size = sum(f.stat().st_size for f in media_files)
        total_size_mb = total_size / (1024 * 1024) if total_size else 0
        print(f"  Total size: {total_size_mb:.1f} MB ({len(media_files)} file(s))")
        
        # Quick playlist check
        if not check_playlist_exists(STAGING_DIR):
            raise Exception("No valid playlist found in downloaded content")
        
        # Atomic swap: staging → media
        # VLC with --loop will automatically pick up the new playlist on next cycle
        print("Performing atomic swap...")
        if MEDIA_DIR.exists():
            shutil.rmtree(MEDIA_DIR, ignore_errors=True)
        STAGING_DIR.rename(MEDIA_DIR)
        print(f"Media synced to {MEDIA_DIR} ✓")
        print("VLC will pick up the new playlist on next loop cycle")
        
        print("=== Sync Complete ===")
        
    except Exception as e:
        print(f"=== Sync Failed: {e} ===")
        print("Device will be without media until next successful sync")
        sys.exit(1)
    
    finally:
        SYNC_LOCK.unlink(missing_ok=True)
        # Clean up staging if it still exists (shouldn't after successful swap)
        if STAGING_DIR.exists():
            shutil.rmtree(STAGING_DIR, ignore_errors=True)


if __name__ == "__main__":
    sync()


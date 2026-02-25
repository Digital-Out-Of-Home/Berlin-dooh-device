#!/usr/bin/env python3
"""VLC Playlist Player."""

import logging
import subprocess
import sys
from pathlib import Path

from config import BASE_DIR, get_device_id, setup_logging

setup_logging()
logger = logging.getLogger(__name__)

# ============================================================================
# CONSTANTS
# ============================================================================

MEDIA_DIR = BASE_DIR / "media"
VLC = Path("/usr/bin/vlc")
VERSION = "1.9.2"


# ============================================================================
# MAIN PLAY FUNCTION
# ============================================================================

def play():
    """Play playlist with VLC."""
    device_id = get_device_id()
    logger.info("Device: %s (v%s)", device_id, VERSION)

    playlist = MEDIA_DIR / "playlist.m3u"
    if not playlist.exists():
        sys.exit("No playlist found. Run: python media_sync.py")

    logger.info("Playing %s", playlist)

    vlc_args = [
        str(VLC),
        "--intf", "dummy",
        "--fullscreen",
        "--no-mouse-events",
        "--no-keyboard-events",
        "--loop",
        "--quiet",
        "--no-osd",
        "--no-xlib",
        "--aout", "alsa",
        str(playlist)
    ]

    try:
        result = subprocess.run(
            vlc_args,
            stderr=subprocess.PIPE,
            stdout=None,
            text=True,
            check=False
        )
        if result.returncode != 0:
            if result.stderr:
                logger.error("VLC stderr: %s", result.stderr)
            sys.exit(f"VLC failed with exit code {result.returncode}")
    except Exception as e:
        logger.exception("Error running VLC: %s", e)
        sys.exit(1)


if __name__ == "__main__":
    play()

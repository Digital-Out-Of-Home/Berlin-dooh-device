#!/usr/bin/env python3
"""VLC Playlist Player."""

import logging
import signal
import sys
import time
from pathlib import Path

import vlc

from config import BASE_DIR, get_device_id, setup_logging

setup_logging()
logger = logging.getLogger(__name__)

# ============================================================================
# CONSTANTS
# ============================================================================

MEDIA_DIR = BASE_DIR / "media"
VERSION = "1.10.0"


# ============================================================================
# MAIN PLAY FUNCTION
# ============================================================================

def play():
    """Play playlist with VLC using python-vlc bindings."""
    device_id = get_device_id()
    logger.info("Device: %s (v%s)", device_id, VERSION)

    playlist = MEDIA_DIR / "playlist.m3u"
    if not playlist.exists():
        sys.exit("No playlist found. Run: python media_sync.py")

    logger.info("Playing %s", playlist)

    # Create VLC instance matching the old subprocess flags
    instance = vlc.Instance(
        "--intf", "dummy",
        "--fullscreen",
        "--no-mouse-events",
        "--no-keyboard-events",
        "--loop",
        "--quiet",
        "--verbose=0",
        "--no-osd",
        "--aout", "alsa",
    )

    # Build a media list from the playlist file
    media_list = instance.media_list_new()
    media = instance.media_new(str(playlist))
    media_list.add_media(media)

    # Create list player and set it to loop
    list_player = instance.media_list_player_new()
    list_player.set_media_list(media_list)
    list_player.set_playback_mode(vlc.PlaybackMode.loop)

    player = list_player.get_media_player()

    # Start playback
    list_player.play()
    time.sleep(2)

    # Set fullscreen after playback starts (before start causes parent window error)
    player.set_fullscreen(True)

    state = player.get_state()
    if state == vlc.State.Error:
        logger.error("VLC failed to start playback")
        sys.exit(1)


    # Handle graceful shutdown
    def _shutdown(signum, frame):
        logger.info("Received signal %s, stopping playback...", signum)
        list_player.stop()
        sys.exit(0)

    signal.signal(signal.SIGINT, _shutdown)
    signal.signal(signal.SIGTERM, _shutdown)

    # Keep the process alive while VLC is playing
    try:
        while True:
            state = player.get_state()
            if state in (vlc.State.Ended, vlc.State.Error):
                if state == vlc.State.Error:
                    logger.error("VLC playback error")
                    sys.exit(1)
                break
            time.sleep(1)
    except Exception as e:
        logger.exception("Error during VLC playback: %s", e)
        list_player.stop()
        sys.exit(1)


if __name__ == "__main__":
    play()

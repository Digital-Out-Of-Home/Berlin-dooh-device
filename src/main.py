#!/usr/bin/env python3
"""VLC Playlist Player with seamless playlist hot-reload."""

import atexit
import logging
import os
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
PID_FILE = Path("/tmp/vlc-player.pid")
VERSION = "1.11.0"

# Flag set by the SIGUSR1 handler to request a playlist reload
_playlist_reload_requested = False


# ============================================================================
# HELPER FUNCTIONS
# ============================================================================

def _write_pid_file():
    """Write process PID to file so media_sync can signal us."""
    PID_FILE.write_text(str(os.getpid()))
    logger.debug("PID file written: %s", PID_FILE)


def _remove_pid_file():
    """Remove PID file on exit."""
    PID_FILE.unlink(missing_ok=True)
    logger.debug("PID file removed")


def _handle_reload_signal(signum, frame):
    """SIGUSR1 handler — just set the flag, actual reload happens in the main loop."""
    global _playlist_reload_requested
    _playlist_reload_requested = True
    logger.info("Playlist reload requested (SIGUSR1)")


def _build_media_list(instance, playlist_path):
    """Parse the m3u playlist and build a VLC MediaList with individual items."""
    media_list = instance.media_list_new()

    try:
        lines = playlist_path.read_text(encoding="utf-8").splitlines()
    except Exception as e:
        logger.error("Failed to read playlist %s: %s", playlist_path, e)
        return media_list

    for line in lines:
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        media = instance.media_new(line)
        media_list.add_media(media)

    logger.debug("Built media list with %d items", media_list.count())
    return media_list


# ============================================================================
# MAIN PLAY FUNCTION
# ============================================================================

def play():
    """Play playlist with VLC using python-vlc bindings."""
    global _playlist_reload_requested

    device_id = get_device_id()
    logger.info("Device: %s (v%s)", device_id, VERSION)

    playlist = MEDIA_DIR / "playlist.m3u"
    if not playlist.exists():
        sys.exit("No playlist found. Run: python media_sync.py")

    logger.info("Playing %s", playlist)

    # PID file for IPC with media_sync
    _write_pid_file()
    atexit.register(_remove_pid_file)

    # Ensure Wayland display is available (Pi 5 uses Wayfire compositor)
    os.environ.setdefault("WAYLAND_DISPLAY", "wayland-1")
    os.environ.setdefault("XDG_RUNTIME_DIR", f"/run/user/{os.getuid()}")

    # Create VLC instance
    instance = vlc.Instance(
        "--intf", "dummy",
        "--fullscreen",
        "--no-mouse-events",
        "--no-keyboard-events",
        "--no-osd",
        "--no-video-title-show",
        "--no-xlib",
        "--aout", "alsa",
    )

    # Suppress VLC's direct-to-terminal log output
    instance.log_unset()

    # Build the media list from individual playlist entries (not the m3u as a single item)
    media_list = _build_media_list(instance, playlist)

    # Create list player and set it to loop
    list_player = instance.media_list_player_new()
    list_player.set_media_list(media_list)
    list_player.set_playback_mode(vlc.PlaybackMode.loop)

    player = list_player.get_media_player()
    player.set_fullscreen(True)

    # Start playback
    list_player.play()
    time.sleep(2)

    state = player.get_state()
    if state == vlc.State.Error:
        logger.error("VLC failed to start playback")
        sys.exit(1)

    # Register signal handlers
    signal.signal(signal.SIGUSR1, _handle_reload_signal)

    def _shutdown(signum, frame):
        logger.info("Received signal %s, stopping playback...", signum)
        list_player.stop()
        _remove_pid_file()
        sys.exit(0)

    signal.signal(signal.SIGINT, _shutdown)
    signal.signal(signal.SIGTERM, _shutdown)

    # Keep the process alive while VLC is playing
    try:
        while True:
            state = player.get_state()

            if state == vlc.State.Error:
                logger.error("VLC playback error")
                sys.exit(1)

            # Hot-reload: when a reload is requested, wait for the current
            # clip to reach its end, then swap in the new playlist.
            if _playlist_reload_requested and state == vlc.State.Ended:
                logger.info("Current clip ended — reloading playlist")
                _playlist_reload_requested = False

                new_media_list = _build_media_list(instance, playlist)
                if new_media_list.count() > 0:
                    list_player.set_media_list(new_media_list)
                    list_player.play()
                    time.sleep(1)
                    logger.info("Playlist reloaded, playback resumed")
                else:
                    logger.warning("New playlist is empty, keeping current playback")

            # If playback ended naturally (no reload pending), just restart the loop
            if not _playlist_reload_requested and state == vlc.State.Ended:
                list_player.play()
                time.sleep(1)

            time.sleep(0.5)
    except Exception as e:
        logger.exception("Error during VLC playback: %s", e)
        list_player.stop()
        sys.exit(1)


if __name__ == "__main__":
    play()


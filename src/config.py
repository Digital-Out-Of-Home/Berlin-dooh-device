#!/usr/bin/env python3
"""Shared configuration utilities for VLC Player scripts."""

import logging
import os
import socket
from pathlib import Path
from http.cookiejar import CookieJar
from urllib.request import build_opener, HTTPCookieProcessor, HTTPRedirectHandler

# ============================================================================
# CONSTANTS
# ============================================================================

BASE_DIR = Path(__file__).parent.parent
CONFIG_FILE = "/home/pi/config.env"

# ============================================================================
# LOGGING
# ============================================================================

_logging_configured = False


def get_log_level():
    """Return log level: DEBUG if VLC_DEBUG=1, else LOG_LEVEL env or INFO."""
    if os.environ.get("VLC_DEBUG"):
        return logging.DEBUG
    level_name = (os.environ.get("LOG_LEVEL") or "INFO").upper()
    return getattr(logging, level_name, logging.INFO)


def setup_logging():
    """Configure root logger once. Call from main script entry points."""
    global _logging_configured
    if _logging_configured:
        return
    logging.basicConfig(
        level=get_log_level(),
        format="%(levelname)s: %(message)s",
    )
    _logging_configured = True


# ============================================================================
# CONFIGURATION FUNCTIONS
# ============================================================================


def _read_env_file(filepath):
    """Read a simple .env file without external dependencies."""
    config = {}
    try:
        with open(filepath, 'r') as f:
            for line in f:
                line = line.strip()
                if not line or line.startswith('#'):
                    continue
                if '=' in line:
                    key, value = line.split('=', 1)
                    key = key.strip()
                    value = value.strip().strip('"\'')
                    config[key] = value
    except FileNotFoundError:
        pass
    return config


def load_config():
    """Load configuration directly from /home/pi/config.env."""
    env_config = _read_env_file(CONFIG_FILE)
    # Minimal config used by the scripts
    return {
        "API_URL": "https://piapi.speakinprivate.com/api/v1/campaign/playlist/",
        "API_TOKEN": env_config.get("API_TOKEN", ""),
        "DEVICE_ID": get_device_id(),
        "HOST_URL": "https://piapi.speakinprivate.com",
        "HEALTHCHECK_URL": "",
    }


def get_device_id():
    """Get hostname as a device ID."""
    return socket.gethostname()


def create_http_opener():
    """Create HTTP opener with cookie and redirect handling.
    
    Returns:
        OpenerDirector: Configured opener for HTTP requests.
    """
    return build_opener(HTTPCookieProcessor(CookieJar()), HTTPRedirectHandler())


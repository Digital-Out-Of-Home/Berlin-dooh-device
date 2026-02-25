#!/usr/bin/env python3
"""Shared configuration utilities for VLC Player scripts."""

import os
import socket
from pathlib import Path
from http.cookiejar import CookieJar
from urllib.request import build_opener, HTTPCookieProcessor, HTTPRedirectHandler

# ============================================================================
# CONSTANTS
# ============================================================================

BASE_DIR = Path(__file__).parent.parent
CONFIG_FILE = "/home/config.env"

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
    """Load configuration directly from /home/config.env."""
    env_config = _read_env_file(CONFIG_FILE)
    # Minimal config used by the scripts
    return {
        "API_URL": env_config.get("API_URL", "https://piapi.speakinprivate.com/api/v1/campaign/playlist/"),
        "API_TOKEN": env_config.get("API_TOKEN", ""),
        "DEVICE_ID": env_config.get("DEVICE_ID", ""),
        "HOST_URL": env_config.get("HOST_URL", "https://piapi.speakinprivate.com"),
        "HEALTHCHECK_URL": env_config.get("HEALTHCHECK_URL", ""),
    }


def get_device_id():
    """Get device ID from /home/config.env or fall back to hostname.
    
    Returns:
        str: Device ID from config, or hostname if not configured.
    """
    env_config = _read_env_file(CONFIG_FILE)
    device_id = env_config.get("DEVICE_ID", "")
    return device_id if device_id else socket.gethostname()


def create_http_opener():
    """Create HTTP opener with cookie and redirect handling.
    
    Returns:
        OpenerDirector: Configured opener for HTTP requests.
    """
    return build_opener(HTTPCookieProcessor(CookieJar()), HTTPRedirectHandler())


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

# ============================================================================
# CONFIGURATION FUNCTIONS
# ============================================================================

def load_config():
    """Load configuration from local config.env file.

    - Parses KEY=VALUE lines (ignores comments/blank lines)
    - Sets them in os.environ
    - Returns a minimal dict with just the keys the player actually needs
    """
    config_file = BASE_DIR / "config.env"
    content = ""

    if config_file.exists():
        try:
            content = config_file.read_text()
        except Exception as e:
            print(f"Warning: Could not read config file: {e}")

    if content:
        for line in content.splitlines():
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            key, value = line.split("=", 1)
            os.environ[key.strip()] = value.strip()

    # Minimal config used by the scripts
    return {
        "API_URL": os.environ.get("API_URL", "http://localhost:8000/api/v1/campaign/playlist/"),
        "API_TOKEN": os.environ.get("API_TOKEN", ""),
        "DEVICE_ID": os.environ.get("DEVICE_ID", ""),
        "HOST_URL": os.environ.get("HOST_URL", "http://localhost:8000"),
        "HEALTHCHECK_URL": os.environ.get("HEALTHCHECK_URL", ""),
    }


def get_device_id():
    """Get device ID from config or fall back to hostname.
    
    Returns:
        str: Device ID from config, or hostname if not configured.
    """
    device_id = os.environ.get("DEVICE_ID", "")
    return device_id if device_id else socket.gethostname()


def create_http_opener():
    """Create HTTP opener with cookie and redirect handling.
    
    Returns:
        OpenerDirector: Configured opener for HTTP requests.
    """
    return build_opener(HTTPCookieProcessor(CookieJar()), HTTPRedirectHandler())


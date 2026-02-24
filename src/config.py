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
    """Load configuration directly from environment variables."""
    # Minimal config used by the scripts
    return {
        "API_URL": os.environ.get("API_URL", "https://piapi.speakinprivate.com/api/v1/campaign/playlist/"),
        "API_TOKEN": os.environ.get("API_TOKEN", ""),
        "DEVICE_ID": os.environ.get("DEVICE_ID", ""),
        "HOST_URL": os.environ.get("HOST_URL", "https://piapi.speakinprivate.com"),
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


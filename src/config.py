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


def _load_env_file(path: Path) -> None:
    """Parse KEY=VALUE from a file and set os.environ. Skips comments and blank lines."""
    if not path.exists():
        return
    try:
        content = path.read_text()
    except Exception as e:
        print(f"Warning: Could not read {path}: {e}")
        return
    for line in content.splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        os.environ[key.strip()] = value.strip()


# region agent log
def _debug_log(hypothesis_id: str, message: str, data: dict) -> None:
    """Append a single NDJSON debug log line. Fail-safe: ignores all errors.

    NOTE: This is for local debugging only; errors are swallowed so it is safe on devices.
    """
    log_path = Path("/Users/azeraliyev/source/DOOH2/.cursor/debug.log")
    payload = {
        "id": f"log_config_{int(__import__('time').time()*1000)}",
        "timestamp": int(__import__("time").time() * 1000),
        "location": "src/config.py",
        "message": message,
        "data": data,
        "runId": "pre-fix",
        "hypothesisId": hypothesis_id,
    }
    try:
        # Avoid importing json at top-level just for debug mode
        import json as _json

        log_path.parent.mkdir(parents=True, exist_ok=True)
        with log_path.open("a", encoding="utf-8") as f:
            f.write(_json.dumps(payload) + "\n")
    except Exception:
        # Logging must never break the player
        pass
# endregion


def load_config():
    """Load configuration from config.env (static) then secrets.env (device-specific).

    - config.env: API_URL, HOST_URL, etc. (in Git, shared across devices)
    - secrets.env: DEVICE_ID, API_TOKEN (per-device secrets, not in Git)
    - Later file overrides earlier for the same key.
    """
    config_path = BASE_DIR / "config.env"
    secrets_path = BASE_DIR / "secrets.env"

    # First, static config (shared)
    print(f"[config] BASE_DIR={BASE_DIR}")
    print(f"[config] Trying config.env at: {config_path} (exists={config_path.exists()})")
    _load_env_file(config_path)
    print(f"[config] After config.env, DEVICE_ID={repr(os.environ.get('DEVICE_ID'))}")
    _debug_log(
        "H1",
        "After loading config.env",
        {"has_device_id": bool(os.environ.get("DEVICE_ID"))},
    )

    # Then, device-specific secrets (override)
    print(f"[config] Trying secrets.env at: {secrets_path} (exists={secrets_path.exists()})")
    _load_env_file(secrets_path)
    print(f"[config] After secrets.env, DEVICE_ID={repr(os.environ.get('DEVICE_ID'))}")
    _debug_log(
        "H1",
        "After loading secrets.env",
        {"has_device_id": bool(os.environ.get("DEVICE_ID"))},
    )

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


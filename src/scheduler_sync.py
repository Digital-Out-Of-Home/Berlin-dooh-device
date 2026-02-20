#!/usr/bin/env python3
"""
Scheduler Sync Script

Fetches the device's turn-on/shut-down schedule from the backend API and saves it
locally as JSON. The local file is then used by power-control logic to decide
whether the display should be on or off at a given time.
"""

import json
import sys
from pathlib import Path
from urllib.request import Request, urlopen
from urllib.error import URLError, HTTPError

from config import BASE_DIR, load_config, get_device_id


# ============================================================================
# CONFIG & PATHS
# ============================================================================

config = load_config()
API_TOKEN = config.get("API_TOKEN")
DEVICE_ID = get_device_id()

MEDIA_DIR = BASE_DIR / "media"
SCHEDULE_FILE = MEDIA_DIR / "schedule.json"


# ============================================================================
# CORE LOGIC
# ============================================================================

def fetch_schedule():
    """
    Fetch schedule for this device from the backend API.

    Expected backend contract (see schedule-api-usage.md):
    - Endpoint:  {HOST_URL.rstrip('/')}/api/devices/{DEVICE_ID}/
    - Response JSON contains "schedules": [...]
    """
    host_url = config.get("HOST_URL")
    if not host_url:
        print("Error: HOST_URL is not configured.")
        sys.exit(1)

    base = host_url.rstrip("/")
    url = f"{base}/api/v1/device/detail/c/{DEVICE_ID}/"

    print(f"[scheduler_sync] Fetching device data from: {url}")

    headers = {
        "User-Agent": "Berlin-DOOH-Device/1.0",
        "Accept": "application/json",
        "Content-Type": "application/json",
    }
    if API_TOKEN:
        headers["Authorization"] = f"Bearer {API_TOKEN}"

    req = Request(url, headers=headers)

    try:
        with urlopen(req, timeout=30) as response:
            if response.status != 200:
                print(f"[scheduler_sync] Error: API returned status {response.status}")
                sys.exit(1)
            data = response.read()
            device_data = json.loads(data)

            schedules = device_data.get("schedules", [])
            return schedules

    except (HTTPError, URLError) as e:
        print(f"[scheduler_sync] Error fetching device data: {e}")
        sys.exit(1)
    except json.JSONDecodeError:
        print("[scheduler_sync] Error: Failed to decode API response JSON")
        sys.exit(1)


def save_schedule(schedule_data):
    """Save schedule data to local JSON file."""
    MEDIA_DIR.mkdir(parents=True, exist_ok=True)
    try:
        with SCHEDULE_FILE.open("w", encoding="utf-8") as f:
            json.dump(schedule_data, f, indent=2)
        print(f"[scheduler_sync] Schedule saved to {SCHEDULE_FILE}")
    except OSError as e:
        print(f"[scheduler_sync] Error saving schedule file: {e}")


def main():
    print("=== Schedule Sync ===")
    schedule_data = fetch_schedule()
    if schedule_data:
        save_schedule(schedule_data)
    else:
        print("[scheduler_sync] No schedule data received.")


if __name__ == "__main__":
    main()


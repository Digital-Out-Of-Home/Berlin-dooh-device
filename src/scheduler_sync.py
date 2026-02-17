#!/usr/bin/env python3
"""
Scheduler Sync Script
Fetches the device's turn-on/shut-down schedule from the API and saves it locally.
"""
import json
import sys
import os
from pathlib import Path
from urllib.request import Request, urlopen
from urllib.error import URLError, HTTPError

from config import BASE_DIR, load_config, get_device_id

# Load configuration
config = load_config()
API_TOKEN = config.get("API_TOKEN")
DEVICE_ID = get_device_id()

# File paths
MEDIA_DIR = BASE_DIR / "media"
SCHEDULE_FILE = MEDIA_DIR / "schedule.json"

def fetch_schedule():
    """Fetch schedule from API."""
    # Construct URL for Device API
    # API Structure: HOST_URL/api/devices/{DEVICE_ID}/
    # We use HOST_URL from config, which should be the backend base.
    
    host_url = config.get("HOST_URL")
    if not host_url:
         print("Error: HOST_URL is not configured.")
         sys.exit(1)

    # Ensure no double slashes if host_url has trailing slash
    base = host_url.rstrip("/")
    url = f"{base}/api/devices/{DEVICE_ID}/"

    print(f"Fetching device data from: {url}")

    headers = {
        "User-Agent": "Berlin-DOOH-Device/1.0",
        "Accept": "application/json",
        "Content-Type": "application/json"
    }
    if API_TOKEN:
        headers["Authorization"] = f"Bearer {API_TOKEN}"

    req = Request(url, headers=headers)

    try:
        with urlopen(req, timeout=30) as response:
            if response.status != 200:
                print(f"Error: API returned status {response.status}")
                sys.exit(1)
            data = response.read()
            device_data = json.loads(data)
            
            # Extract schedules from device object
            schedules = device_data.get("schedules", [])
            return schedules
            
    except (HTTPError, URLError) as e:
        print(f"Error fetching device data: {e}")
        sys.exit(1)
    except json.JSONDecodeError:
        print("Error: Failed to decode API response JSON")
        sys.exit(1)

def save_schedule(schedule_data):
    """Save schedule data to local file."""
    MEDIA_DIR.mkdir(parents=True, exist_ok=True)
    try:
        with open(SCHEDULE_FILE, 'w') as f:
            json.dump(schedule_data, f, indent=2)
        print(f"Schedule saved to {SCHEDULE_FILE}")
    except IOError as e:
        print(f"Error saving schedule file: {e}")

def main():
    print("=== Schedule Sync ===")
    schedule_data = fetch_schedule()
    # Basic validation of data structure could happen here
    if schedule_data:
        save_schedule(schedule_data)
    else:
        print("No schedule data received.")

if __name__ == "__main__":
    main()

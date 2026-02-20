#!/usr/bin/env python3
"""
Power Control Script

Reads the local schedule JSON and turns the TV on or off using HDMI-CEC
(`cec-client`). Intended to be run periodically via systemd timer.
"""

import datetime
import json
import subprocess
import sys
from pathlib import Path

from config import BASE_DIR


# ============================================================================
# PATHS
# ============================================================================

MEDIA_DIR = BASE_DIR / "media"
SCHEDULE_FILE = MEDIA_DIR / "schedule.json"


# ============================================================================
# HDMI-CEC HELPERS
# ============================================================================

def set_tv_power(state: str) -> None:
    """
    Turn TV on or off using cec-client.

    state:
        "on"  -> send 'on 0'
        "off" -> send 'standby 0'
    """
    cmd = "on 0" if state == "on" else "standby 0"
    print(f"[power_control] Turning TV {state} (cec-client '{cmd}')")
    try:
        subprocess.run(
            ["cec-client", "-s", "-d", "1"],
            input=cmd.encode("utf-8"),
            capture_output=True,
            timeout=10,
            check=False,
        )
    except Exception as e:  # noqa: BLE001
        print(f"[power_control] Error setting TV power: {e}")


# ============================================================================
# SCHEDULE HELPERS
# ============================================================================

def load_schedule():
    """Load schedule from local JSON file."""
    if not SCHEDULE_FILE.exists():
        print("[power_control] No schedule file found; skipping power control.")
        return None
    try:
        with SCHEDULE_FILE.open("r", encoding="utf-8") as f:
            return json.load(f)
    except Exception as e:  # noqa: BLE001
        print(f"[power_control] Error loading schedule: {e}")
        return None


def parse_api_time(t_str: str) -> datetime.time:
    """
    Parse API time string, supporting both HH:MM and HH:MM:SS.
    """
    has_seconds = t_str.count(":") == 2
    fmt = "%H:%M:%S" if has_seconds else "%H:%M"
    return datetime.datetime.strptime(t_str, fmt).time()


def decide_power_state(schedule) -> bool:
    """
    Decide whether the TV should be ON (True) or OFF (False) right now.

    Expected schedule format (list of items):
    [
      {
        "day_of_week": 1,
        "turn_on_time": "07:00:00",
        "shut_down_time": "23:00:00",
        "is_active": true
      },
      ...
    ]
    """
    if not schedule:
        print("[power_control] Empty or missing schedule; leaving state unchanged.")
        return False

    if not isinstance(schedule, list):
        print("[power_control] Invalid schedule format (expected list).")
        return False

    now = datetime.datetime.now()
    # Python weekday: 0=Mon..6=Sun; API: 1=Mon..7=Sun
    current_day_int = now.weekday() + 1
    current_time = now.time()

    should_be_on = False
    rule_found = False

    for item in schedule:
        if not item.get("is_active", True):
            continue

        item_day = item.get("day_of_week")
        if item_day != current_day_int:
            continue

        start_str = item.get("turn_on_time")
        end_str = item.get("shut_down_time")
        if not start_str or not end_str:
            continue

        try:
            start_time = parse_api_time(start_str)
            end_time = parse_api_time(end_str)
        except ValueError as e:
            print(f"[power_control] Error parsing time for day {item_day}: {e}")
            continue

        rule_found = True

        if start_time <= end_time:
            # Same-day window, e.g. 07:00–23:00
            if start_time <= current_time <= end_time:
                should_be_on = True
        else:
            # Overnight window, e.g. 23:00–06:00
            if start_time <= current_time or current_time <= end_time:
                should_be_on = True

        # Only one rule per day is expected; stop after first matching entry
        break

    if not rule_found:
        print(
            f"[power_control] No active schedule found for today "
            f"(day={current_day_int}); defaulting to OFF.",
        )
        should_be_on = False

    state_str = "ON" if should_be_on else "OFF"
    print(
        f"[power_control] Schedule decision: {state_str} "
        f"(day={current_day_int}, time={current_time.strftime('%H:%M:%S')})",
    )

    return should_be_on


def main() -> None:
    schedule = load_schedule()
    should_be_on = decide_power_state(schedule)
    set_tv_power("on" if should_be_on else "off")


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        sys.exit(1)


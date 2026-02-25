#!/usr/bin/env python3
"""
Power Control Script

Reads the local schedule JSON and turns the TV on or off using HDMI-CEC
(`cec-client`). Intended to be run periodically via systemd timer.
Logs only when state changes or on error to reduce log volume.

Usage:
  python3 src/power_control.py           # normal (quiet unless state change)
  python3 src/power_control.py --debug    # verbose: schedule decision, cec-client, etc.
"""

import datetime
import json
import subprocess
import sys
import os
from pathlib import Path
from typing import Optional

from config import BASE_DIR, setup_logging

# --debug: enable DEBUG logging and show cec-client output in terminal
if "--debug" in sys.argv:
    sys.argv.remove("--debug")
    os.environ["LOG_LEVEL"] = "DEBUG"

setup_logging()
import logging
logger = logging.getLogger(__name__)


# ============================================================================
# PATHS
# ============================================================================

MEDIA_DIR = BASE_DIR / "media"
SCHEDULE_FILE = MEDIA_DIR / "schedule.json"
POWER_STATE_FILE = MEDIA_DIR / ".power_state"


# ============================================================================
# HDMI-CEC HELPERS
# ============================================================================


def set_tv_power(state: str, debug: bool = False) -> None:
    cmd = "on 0" if state == "on" else "standby 0"
    logger.debug("cec-client cmd: %s", cmd)

    cec_device = os.getenv("CEC_DEVICE", "/dev/cec1")
    base_cmd = ["cec-client", "-s", "-d", "1"]
    if cec_device:
        base_cmd.append(cec_device)
    logger.debug("base_cmd: %s", base_cmd)

    try:
        result = subprocess.run(
            base_cmd,
            input=cmd,
            capture_output=not debug,
            timeout=10,
            check=False,
            text=True,
        )
        if result.returncode != 0:
            logger.warning(
                "cec-client exit code %s%s",
                result.returncode,
                f" stderr: {result.stderr}" if result.stderr else "",
            )
    except Exception as e:
        logger.error("Error setting TV power: %s", e)


def read_last_power_state() -> Optional[str]:
    """Return last applied state: 'on', 'off', or None if unknown."""
    if not POWER_STATE_FILE.exists():
        return None
    try:
        s = POWER_STATE_FILE.read_text().strip().lower()
        return s if s in ("on", "off") else None
    except Exception:
        return None


def write_power_state(state: str) -> None:
    """Persist applied state for next run."""
    try:
        MEDIA_DIR.mkdir(parents=True, exist_ok=True)
        POWER_STATE_FILE.write_text(state)
    except OSError as e:
        logger.debug("Could not write power state file: %s", e)


# ============================================================================
# SCHEDULE HELPERS
# ============================================================================

def load_schedule():
    """Load schedule from local JSON file."""
    if not SCHEDULE_FILE.exists():
        logger.debug("No schedule file found; skipping power control.")
        return None
    try:
        with SCHEDULE_FILE.open("r", encoding="utf-8") as f:
            return json.load(f)
    except Exception as e:
        logger.warning("Error loading schedule: %s", e)
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
        logger.debug("Empty or missing schedule; leaving state unchanged.")
        return False

    if not isinstance(schedule, list):
        logger.warning("Invalid schedule format (expected list).")
        return False

    now = datetime.datetime.now()
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
            logger.warning("Error parsing time for day %s: %s", item_day, e)
            continue

        rule_found = True

        if start_time <= end_time:
            if start_time <= current_time <= end_time:
                should_be_on = True
        else:
            if start_time <= current_time or current_time <= end_time:
                should_be_on = True

        break

    if not rule_found:
        logger.debug(
            "No active schedule for today (day=%s); defaulting to OFF.",
            current_day_int,
        )
        should_be_on = False

    logger.debug(
        "Schedule decision: %s (day=%s, time=%s)",
        "ON" if should_be_on else "OFF",
        current_day_int,
        current_time.strftime("%H:%M:%S"),
    )
    return should_be_on


def main() -> None:
    schedule = load_schedule()
    should_be_on = decide_power_state(schedule)
    desired = "on" if should_be_on else "off"
    last = read_last_power_state()

    if last == desired:
        logger.debug("TV already %s; no change.", desired)
        return

    logger.info("Turning TV %s (was %s)", desired, last or "unknown")
    set_tv_power(desired, debug=logger.isEnabledFor(logging.DEBUG))
    write_power_state(desired)


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        sys.exit(1)

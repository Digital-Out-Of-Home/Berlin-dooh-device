                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                #!/usr/bin/env python3
"""
Power Control Script

Reads the local schedule JSON and turns the TV on or off using HDMI-CEC
(`cec-client`). Intended to be run periodically via systemd timer.
Sends the CEC command every run (no stored state), so the display stays in sync
with the schedule even if turned on/off manually.

Usage:
  python3 src/power_control.py           # normal (one INFO line per run)
  python3 src/power_control.py --debug   # verbose: schedule decision, cec-client, etc.
"""

import datetime
import json
import subprocess
import sys
import os
from pathlib import Path

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


# ============================================================================
# HDMI-CEC HELPERS
# ============================================================================


def set_tv_power(state: str, debug: bool = False) -> None:
    cmd = "on 0" if state == "on" else "standby 0"
    logger.debug("cec-client cmd: %s", cmd)

    cec_device = os.getenv("CEC_DEVICE", "/dev/cec0")
    base_cmd = ["cec-client", "-s", "-d", "1"]
    if cec_device:
        base_cmd.append(cec_device)
    logger.debug("base_cmd: %s", base_cmd)

    try:
        result = subprocess.run(
            base_cmd,
            input=cmd + "\n",
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


# ============================================================================
# TV STATE HELPERS
# ============================================================================


def get_tv_power_state() -> str | None:
    """Best-effort query of TV power state via CEC.

    Returns:
        "on", "standby", or None if unknown/error.
    """
    cec_device = os.getenv("CEC_DEVICE", "/dev/cec0")
    base_cmd = ["cec-client", "-s", "-d", "1"]
    if cec_device:
        base_cmd.append(cec_device)

    try:
        result = subprocess.run(
            base_cmd,
            input="pow 0\n",
            capture_output=True,
            timeout=5,
            check=False,
            text=True,
        )
    except Exception as e:  # noqa: BLE001
        logger.warning("[power_control] Failed to query TV power state: %s", e)
        return None

    if result.returncode != 0:
        logger.warning(
            "[power_control] pow 0 failed (exit %s): %s",
            result.returncode,
            result.stderr,
        )
        return None

    stdout = result.stdout or ""
    for line in stdout.splitlines():
        lower = line.strip().lower()
        if "power status" in lower:
            if "standby" in lower:
                return "standby"
            if "on" in lower:
                return "on"

    logger.debug(
        "[power_control] Could not parse TV power state from pow 0 output.",
    )
    return None


def wake_tv_aggressive(debug: bool = False) -> None:
    """Wake TV using a stronger CEC sequence for stubborn devices.

    Sequence:
      - on 0        (Power On)
      - tx 10:04    (Image View On)
      - as          (Active Source)
    """
    cec_device = os.getenv("CEC_DEVICE", "/dev/cec0")
    base_cmd = ["cec-client", "-s", "-d", "1"]
    if cec_device:
        base_cmd.append(cec_device)

    sequence = "on 0\ntx 10:04\nas\n"
    logger.debug(
        "[power_control] Aggressive wake via cec-client: %s", base_cmd,
    )
    try:
        result = subprocess.run(
            base_cmd,
            input=sequence,
            capture_output=not debug,
            timeout=10,
            check=False,
            text=True,
        )
        if result.returncode != 0:
            logger.warning(
                "[power_control] Aggressive wake exit code %s%s",
                result.returncode,
                f" stderr: {result.stderr}" if result.stderr else "",
            )
    except Exception as e:  # noqa: BLE001
        logger.error("[power_control] Error during aggressive wake: %s", e)


# ============================================================================
# SCHEDULE HELPERS
# ============================================================================

def load_schedule():
    """Load schedule from local JSON file."""
    if not SCHEDULE_FILE.exists():
        logger.info("[power_control] No schedule file found; skipping power control.")
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

    logger.info(
        "[power_control] Schedule decision: %s (day=%s, time=%s)",
        "ON" if should_be_on else "OFF",
        current_day_int,
        current_time.strftime("%H:%M:%S"),
    )
    return should_be_on


def main() -> None:
    schedule = load_schedule()
    if schedule is None:
        # No schedule available; leave TV state unchanged.
        return
    should_be_on = decide_power_state(schedule)
    desired_label = "ON" if should_be_on else "OFF"

    actual_state = get_tv_power_state()
    logger.info(
        "[power_control] Schedule wants %s, TV reported state: %s",
        desired_label,
        actual_state or "unknown",
    )

    if should_be_on:
        if actual_state == "standby":
            logger.info(
                "[power_control] TV in standby; sending aggressive wake sequence.",
            )
            wake_tv_aggressive(debug=logger.isEnabledFor(logging.DEBUG))
        elif actual_state == "on":
            logger.info(
                "[power_control] TV already ON; no action taken.",
            )
        else:
            logger.info(
                "[power_control] TV state unknown; sending simple ON command.",
            )
            set_tv_power("on", debug=logger.isEnabledFor(logging.DEBUG))
    else:
        if actual_state == "on":
            logger.info(
                "[power_control] TV ON but schedule=OFF; turning OFF.",
            )
            set_tv_power("off", debug=logger.isEnabledFor(logging.DEBUG))
        else:
            logger.info(
                "[power_control] Schedule=OFF and TV state %s; no action.",
                actual_state or "unknown",
            )


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        sys.exit(1)

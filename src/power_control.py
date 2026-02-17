#!/usr/bin/env python3
"""
Power Control Script
Reads the local schedule and turns the TV on or off using cec-client.
"""
import json
import sys
import subprocess
import datetime
from pathlib import Path
from config import BASE_DIR

# File paths
MEDIA_DIR = BASE_DIR / "media"
SCHEDULE_FILE = MEDIA_DIR / "schedule.json"

def get_tv_status():
    """Check if TV is currently on using cec-client."""
    # echo 'pow 0' | cec-client -s -d 1
    # Output line looks like: "power status: on" or "power status: standby"
    try:
        result = subprocess.run(
            ['cec-client', '-s', '-d', '1'],
            input='pow 0'.encode('utf-8'),
            capture_output=True,
            timeout=10
        )
        output = result.stdout.decode('utf-8').lower()
        if "power status: on" in output:
            return "on"
        elif "power status: standby" in output:
            return "standby"
        else:
            return "unknown"
    except (subprocess.TimeoutExpired, FileNotFoundError, Exception) as e:
        print(f"Error checking TV status: {e}")
        return "error"

def set_tv_power(state):
    """Turn TV on or off."""
    cmd = 'on 0' if state == "on" else 'standby 0'
    print(f"Turning TV {state}...")
    try:
        subprocess.run(
            ['cec-client', '-s', '-d', '1'],
            input=cmd.encode('utf-8'),
            capture_output=True,  # Suppress heavy output
            timeout=10
        )
    except Exception as e:
        print(f"Error setting TV power: {e}")

def load_schedule():
    """Load schedule from local file."""
    if not SCHEDULE_FILE.exists():
        print("No schedule file found.")
        return None
    try:
        with open(SCHEDULE_FILE, 'r') as f:
            return json.load(f)
    except Exception as e:
        print(f"Error loading schedule: {e}")
        return None

def is_time_in_range(now_time, start_str, end_str):
    """Check if now_time is between start_str and end_str."""
    try:
        start = datetime.datetime.strptime(start_str, "%H:%M").time()
        end = datetime.datetime.strptime(end_str, "%H:%M").time()
        
        # Handle overnight range (e.g. 23:00 to 06:00)
        if start <= end:
            return start <= now_time <= end
        else:
            return start <= now_time or now_time <= end
    except ValueError:
        print(f"Invalid time format: {start_str} or {end_str}")
        return False

def check_schedule_and_act():
    schedule = load_schedule()
    if not schedule:
        return

    # Expected schedule format from Device API:
    # [
    #   { 
    #     "day_of_week": 1, 
    #     "turn_on_time": "07:00:00", 
    #     "shut_down_time": "23:00:00", 
    #     "is_active": true 
    #   },
    #   ...
    # ]

    schedule_list = []
    if isinstance(schedule, list):
        schedule_list = schedule
    else:
        # Fallback/Safety
        print("Invalid schedule format (expected list).")
        return

    if not schedule_list:
        print("No schedule items found.")
        # If no schedule, default to OFF? Or stay as is? 
        # Requirement says "should be ... based on the schedule". 
        # If no schedule, usually implies no active operation -> OFF.
        # But let's be safe.
        return

    # Normalize current day/time
    now = datetime.datetime.now()
    # Python weekday: 0=Monday, 6=Sunday
    # API day_of_week: 1=Monday, 7=Sunday
    current_day_int = now.weekday() + 1
    current_time = now.time()
    
    should_be_on = False
    rule_found = False

    for item in schedule_list:
        # Check active status
        if not item.get("is_active", True):
            continue

        # Check day match
        item_day = item.get("day_of_week")
        
        if item_day == current_day_int:
            start_str = item.get("turn_on_time")
            end_str = item.get("shut_down_time")
            
            if start_str and end_str:
                rule_found = True
                # Parse times "HH:MM:SS"
                try:
                    # Handle "HH:MM" or "HH:MM:SS"
                    # We can reuse is_time_in_range or parse here.
                    # is_time_in_range uses %H:%M, API sends %H:%M:%S usually.
                    # Let's adjust parsing in is_time_in_range or strip seconds?
                    # Adjusting validation to be robust.
                    
                    # Quick fix: strip seconds for comparison or parse properly
                    def parse_api_time(t_str):
                        has_seconds = t_str.count(':') == 2
                        fmt = "%H:%M:%S" if has_seconds else "%H:%M"
                        return datetime.datetime.strptime(t_str, fmt).time()

                    start_time = parse_api_time(start_str)
                    end_time = parse_api_time(end_str)
                    
                    if start_time <= end_time:
                         if start_time <= current_time <= end_time:
                             should_be_on = True
                    else:
                        # Overnight
                        if start_time <= current_time or current_time <= end_time:
                            should_be_on = True
                            
                except ValueError as e:
                    print(f"Error parsing time for day {item_day}: {e}")
                    continue
                
                break # Found the specific rule for today

    if not rule_found:
        print(f"No active schedule found for today (Day {current_day_int}). Defaulting to OFF.")
        should_be_on = False

    target_state = "on" if should_be_on else "standby"
    print(f"Schedule decision: {target_state.upper()} (DayInt: {current_day_int}, Time: {current_time.strftime('%H:%M:%S')})")

    set_tv_power("on" if should_be_on else "off")

if __name__ == "__main__":
    check_schedule_and_act()

# Device Schedule API Usage

## Overview

The device fetches its operating schedule from the backend `Device` API and stores
it locally as `media/schedule.json`. The local file is used by `power_control.py`
to decide when to turn the display on or off.

## Backend Model (Conceptual)

A `DeviceSchedule` model stores operating hours for each day of the week:

- `day_of_week` (1–7)
- `turn_on_time` (`HH:MM:SS`)
- `shut_down_time` (`HH:MM:SS`)
- `is_active` (boolean)

Validation rules (backend side):

- `turn_on_time` must be before `shut_down_time` for same-day intervals.
- There is at most one schedule per device per day.

## API Shape

### Create Device with Schedules

`POST /api/devices/`

```json
{
  "name": "Device 1",
  "location": "Main Street",
  "venue_id": 1,
  "status": "active",
  "schedules": [
    {
      "day_of_week": 1,
      "turn_on_time": "07:00:00",
      "shut_down_time": "23:00:00",
      "is_active": true
    },
    {
      "day_of_week": 2,
      "turn_on_time": "07:00:00",
      "shut_down_time": "23:00:00",
      "is_active": true
    }
  ]
}
```

### Update Device with Schedules

`PUT /api/devices/{id}/`

```json
{
  "name": "Device 1 Updated",
  "schedules": [
    {
      "id": 1,
      "day_of_week": 1,
      "turn_on_time": "06:00:00",
      "shut_down_time": "22:00:00",
      "is_active": true
    },
    {
      "day_of_week": 6,
      "turn_on_time": "11:00:00",
      "shut_down_time": "19:00:00",
      "is_active": true
    }
  ]
}
```

### Retrieve Device with Schedules

`GET /api/devices/{id}/`

Example response:

```json
{
  "id": 1,
  "name": "Device 1",
  "schedules": [
    {
      "id": 1,
      "day_of_week": 1,
      "day_of_week_display": "Monday",
      "turn_on_time": "07:00:00",
      "shut_down_time": "23:00:00",
      "is_active": true
    }
  ]
}
```

## Day of Week Values

- 1 = Monday
- 2 = Tuesday
- 3 = Wednesday
- 4 = Thursday
- 5 = Friday
- 6 = Saturday
- 7 = Sunday

## Notes

- Schedules are optional when creating/updating devices.
- When updating, include `id` on existing schedules to update them.
- Schedules without `id` are created as new.
- Existing schedules not included in an update request are deleted.
- Time format is `"HH:MM:SS"` (24-hour format).


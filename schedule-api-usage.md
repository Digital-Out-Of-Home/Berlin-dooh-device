# Device Schedule API Usage

## Overview
I've updated the Device APIs to handle schedules with nested data. The implementation follows Django REST Framework best practices with nested serializers.

## What Changed

### 1. **New Model: DeviceSchedule**
- Stores operating hours for each day of the week
- Fields: `day_of_week`, `turn_on_time`, `shut_down_time`, `is_active`
- Validation: Turn on time must be before shut down time
- Unique constraint: One schedule per device per day

### 2. **Updated Serializers**
- `DeviceScheduleSerializer`: Handles schedule validation
- `DeviceSerializer`: Now includes nested `schedules` field with create/update logic

### 3. **Updated Views**
- All device views now prefetch schedules for optimal performance
- No separate endpoints needed - schedules are managed through device endpoints

## API Examples

### **Create Device with Schedules**
```http
POST /api/devices/
```
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

### **Update Device with Schedules**
```http
PUT /api/devices/{id}/
```
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

### **Retrieve Device with Schedules**
```http
GET /api/devices/{id}/
```
Response includes all schedules:
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
- Schedules are optional when creating/updating devices
- When updating, include `id` field to update existing schedules
- Schedules without `id` are created as new
- Existing schedules not included in update request are deleted
- Time format: "HH:MM:SS" (24-hour format)

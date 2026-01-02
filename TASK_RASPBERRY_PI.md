# Task Description: Raspberry Pi Device Updates for Django API Integration

## Project Overview

Update Raspberry Pi devices to integrate with the Django backend API instead of Dropbox. Devices will call the API for content downloads and submit status/heartbeat updates.

## Current State

**Current Implementation:**
- Downloads ZIP from Dropbox URL
- Extracts to `media/` directory
- Creates `playlist_local.m3u`
- Sends heartbeat to Healthchecks.io
- Plays with VLC in loop mode

**Target State:**
- Call Django API for content ZIP
- Authenticate with shared API token
- Submit status/heartbeat to API
- Maintain existing VLC playback functionality

## Tech Stack

- Python 3.x
- Existing `main.py` script
- VLC media player
- systemd services
- Existing bootstrap script

## Core Requirements

### 1. Configuration Updates

**Task 1.1: Add API Configuration**
- [ ] Replace `DROPBOX_URL` with `API_BASE_URL` configuration
- [ ] Add `API_TOKEN` configuration (shared token for all devices)
- [ ] Keep existing `DEVICE_ID` configuration (from `.device` file)
- [ ] Update config file structure to support API settings
- [ ] Add retry configuration for API calls

**Task 1.2: Environment Configuration**
- [ ] Create config file template (e.g., `config.json` or `.env`)
- [ ] Document required configuration values:
  - `API_BASE_URL` (e.g., `https://api.example.com`)
  - `API_TOKEN` (shared token for all devices)
  - `DEVICE_ID` (already exists in `.device` file)
- [ ] Update bootstrap script to handle API configuration

### 2. API Client Implementation

**Task 2.1: Create API Client Module**
- [ ] Create new module `api_client.py` or update `main.py`
- [ ] Implement `get_content(device_id, api_token)` function
  - Calls `GET /api/v1/devices/{device_id}/content/`
  - Includes `Authorization: Bearer <token>` header
  - Handles authentication errors (401, 403)
  - Returns ZIP file content
- [ ] Implement `submit_status(device_id, api_token, status_data)` function
  - Calls `POST /api/v1/devices/{device_id}/status/`
  - Includes authentication header
  - Sends heartbeat data (timestamp, status, etc.)
  - Handles errors gracefully

**Task 2.2: Error Handling**
- [ ] Implement retry logic for API calls (similar to current Dropbox retry)
  - Retry up to 3 times with exponential backoff
  - Handle network errors, timeouts
- [ ] Handle HTTP errors (401, 403, 404, 500, etc.)
- [ ] Log API errors for debugging
- [ ] Fallback behavior if API is unavailable (keep playing existing content)

**Task 2.3: Time Slot Handling (Optional for MVP)**
- [ ] Add time checking logic for time-slot campaigns
- [ ] Determine current time slot
- [ ] Request appropriate ZIP based on time slot
- [ ] Handle time slot transitions

### 3. Update Sync Function

**Task 3.1: Replace Dropbox Download with API Call**
- [ ] Update `sync()` function to call API instead of Dropbox
- [ ] Remove Dropbox-specific code
- [ ] Use API client to download ZIP
- [ ] Keep existing extraction logic (extract to temp, atomic swap)

**Task 3.2: Update Playlist Generation**
- [ ] Keep existing `playlist_local.m3u` creation logic
- [ ] Ensure playlist format matches current VLC requirements
- [ ] Verify playlist paths are correct after extraction

**Task 3.3: Update Heartbeat**
- [ ] Replace Healthchecks.io ping with API status submission
- [ ] Send heartbeat data to `POST /api/v1/devices/{device_id}/status/`
- [ ] Include device status, timestamp, uptime (if available)
- [ ] Keep Healthchecks.io as backup (optional) or remove

### 4. Status Submission

**Task 4.1: Implement Status Endpoint Call**
- [ ] Create status data structure:
  ```python
  {
    "heartbeat": {
      "timestamp": "2024-01-15T10:30:00Z",
      "status": "online",
      "uptime_seconds": 86400,
      "free_disk_space_mb": 5120,
      "current_playing": "video1.mp4"
    }
  }
  ```
- [ ] Collect device metrics:
  - Timestamp (current time)
  - Status ("online")
  - Uptime (if available)
  - Free disk space
  - Current playing file (if available)
- [ ] Submit status after successful sync
- [ ] Handle submission errors (log but don't fail sync)

**Task 4.2: Status Submission Frequency**
- [ ] Submit status after each successful sync (every 5 minutes)
- [ ] Ensure status submission doesn't block sync operation
- [ ] Handle status submission failures gracefully

### 5. Bootstrap Script Updates

**Task 5.1: Update Bootstrap Script**
- [ ] Remove Dropbox URL configuration
- [ ] Add API configuration prompts or environment variables
- [ ] Update device setup to include API token
- [ ] Test bootstrap with new API configuration

**Task 5.2: Configuration File Generation**
- [ ] Generate config file with API settings during bootstrap
- [ ] Store API token securely (file permissions 600)
- [ ] Document configuration process

### 6. Testing & Validation

**Task 6.1: Local Testing**
- [ ] Test API client with Django backend (local or staging)
- [ ] Verify ZIP download and extraction
- [ ] Test authentication (valid/invalid tokens)
- [ ] Test error handling (API down, network issues)
- [ ] Test retry logic

**Task 6.2: Device Testing**
- [ ] Test on actual Raspberry Pi device
- [ ] Verify content download and playback
- [ ] Test status submission
- [ ] Test retry logic and error handling
- [ ] Verify playlist generation and VLC playback
- [ ] Test with no active campaigns (empty playlist)

**Task 6.3: Edge Cases**
- [ ] Test with API unavailable (fallback behavior)
- [ ] Test with invalid token (error handling)
- [ ] Test with network interruptions
- [ ] Test time slot transitions (if implemented)

### 7. Documentation Updates

**Task 7.1: Update README**
- [ ] Update installation instructions
- [ ] Document API configuration
- [ ] Update troubleshooting section
- [ ] Add API endpoint documentation
- [ ] Update device setup instructions

**Task 7.2: Configuration Documentation**
- [ ] Document required API configuration
- [ ] Provide example config file
- [ ] Document how to obtain API token
- [ ] Update bootstrap script documentation

### 8. Migration Strategy

**Task 8.1: Backward Compatibility (Optional)**
- [ ] Consider supporting both Dropbox and API (transition period)
- [ ] Or: Clean break (remove Dropbox support)
- [ ] Decide on migration approach

**Task 8.2: Rollout Plan**
- [ ] Test on one device first
- [ ] Verify all functionality works
- [ ] Roll out to all devices
- [ ] Monitor for issues

## Implementation Details

### API Endpoints to Integrate

**1. Content Endpoint**
```
GET /api/v1/devices/{device_id}/content/
Headers:
  Authorization: Bearer <api_token>
Response:
  Content-Type: application/zip
  Body: ZIP file with playlist.m3u + media files
```

**2. Status Endpoint**
```
POST /api/v1/devices/{device_id}/status/
Headers:
  Authorization: Bearer <api_token>
  Content-Type: application/json
Body:
  {
    "heartbeat": {
      "timestamp": "2024-01-15T10:30:00Z",
      "status": "online",
      "uptime_seconds": 86400,
      "free_disk_space_mb": 5120,
      "current_playing": "video1.mp4"
    }
  }
```

### Code Changes Summary

**Files to Modify:**
- `main.py` - Update sync, add API client, update heartbeat
- `bootstrap.sh` - Update configuration setup
- `README.md` - Update documentation

**New Files (Optional):**
- `api_client.py` - Separate API client module
- `config.py` - Configuration management
- `.env.example` - Example configuration file

**Files to Remove (if dropping Dropbox):**
- Dropbox URL configuration
- Healthchecks.io integration (or keep as backup)

### Key Implementation Notes

- Keep existing VLC playback logic unchanged
- Maintain atomic file swap for media updates
- Ensure backward compatibility during transition (if needed)
- Test thoroughly on actual Raspberry Pi hardware
- Consider keeping Healthchecks.io as backup monitoring
- Maintain existing retry logic pattern
- Keep existing systemd service structure

## Timeline Estimate

**Total Estimate: 8-12 hours**

**Breakdown:**
- Configuration updates: 1-2 hours
- API client implementation: 2-3 hours
- Sync function updates: 2-3 hours
- Status submission: 1-2 hours
- Testing: 2-3 hours
- Documentation: 1 hour

## Implementation Priority

### Phase 1: Core Functionality (MVP)
1. Configuration updates (Task 1)
2. API client implementation (Task 2.1, 2.2)
3. Update sync function (Task 3.1, 3.2)
4. Basic status submission (Task 4.1)
5. Testing (Task 6.1, 6.2)

### Phase 2: Enhancements
1. Time slot handling (Task 2.3, 3.3)
2. Enhanced status data (Task 4.2)
3. Bootstrap script updates (Task 5)
4. Documentation (Task 7)

## Deliverables

1. Updated `main.py` with API integration
2. Updated `bootstrap.sh` with API configuration
3. API client module (if separate file)
4. Updated README with API setup instructions
5. Configuration file template
6. Tested and verified on Raspberry Pi device

## Notes

- Maintain existing reliability features (retry logic, watchdog, auto-update)
- Ensure minimal disruption to existing functionality
- Keep code maintainable and well-documented
- Test on actual hardware before deployment
- Consider gradual rollout strategy


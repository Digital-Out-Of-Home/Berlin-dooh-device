# Task Description: Django Admin Panel & Backend API for DOOH Platform

## Project Overview

Build an admin panel and backend API for a Digital Out-of-Home (DOOH) advertising platform. The system manages screens/devices, campaigns, and serves content to Raspberry Pi devices.

## Tech Stack

**Backend:**
- Django 4.2+ with Django REST Framework
- PostgreSQL
- Python 3.10+

**Frontend:**
- React 18+ with TypeScript
- Tailwind CSS
- React Hook Form + Zod
- TanStack Query (React Query)
- Leaflet React (maps)
- Recharts (charts)

**Infrastructure:**
- Docker + Docker Compose (development)
- VPS deployment (production)
- Environment variables for configuration

## Core Requirements

### 1. Authentication & Authorization

- Admin-only access
- Username + password authentication
- Session-based authentication for admin panel
- Token-based authentication for device API (shared token for all devices during pilot)

### 2. Screen/Device Management

**Admin Panel Features:**
- Create, edit, delete screens/devices
- Fields required:
  - Device ID/Name (unique identifier)
  - Location (address, coordinates, district)
  - Status (Active/Inactive/Maintenance)
  - Description (text field)
  - Notes (text field)
  - Photo (image upload)
  - Payment/Commission info:
    - Bank account number
    - IBAN
    - Bank name
    - Account holder name
    - Commission type (dropdown: % or fixed fee)
    - Commission amount (per month)
    - Tax ID
    - VAT number

**Screen Selection Features:**
- Multi-select from list
- Filter by location/district
- Show availability/conflicts
- Select all screens in a district at once

### 3. Campaign Management

**Campaign Types:**
- All-Day Campaign (no time slots)
- Time-Slot Campaign (custom time ranges)

**Campaign Fields:**
- Campaign Name
- Campaign Type (dropdown: "all_day" or "time_slot")
- Start Date / End Date (date pickers)
- Time Slots (only for "time_slot" campaigns):
  - Custom time picker (HH:MM format)
  - Start time / End time
  - No overlap validation (first match wins)
- Screen Selection (many-to-many relationship)
- Budget:
  - Slot price: €0.50 default (editable per campaign)
  - Maximum daily budget
  - Total budget
  - Budget limit behavior: checkbox flag
    - Checked (default): Pause campaign when budget reached
    - Unchecked: Track spending but don't pause
- Media File:
  - Video upload only (vertical format)
  - Formats: Raspberry Pi compatible (MP4, MOV, etc.)
  - One campaign = One media file
  - File size limits: TBD (100MB mentioned in mockups)

**Campaign Status Flow:**
- Draft → Review → Active → Paused → Completed

**Campaign Review & Launch:**
- Review screen showing:
  - Campaign Summary (with edit button)
  - Targeting & Locations (with edit button)
  - Ad Content & Creative (with preview, replace creative button)
  - Settings & Schedule (with edit button)
- Terms of Service checkbox
- "Back to Edit" and "Launch Campaign" buttons
- Campaign not active until launched

### 4. Playlist Generation

**Logic:**
- All active campaigns for a screen → combined into one rotating playlist
- Equal rotation (campaign A, B, C, A, B, C...)
- For Time-Slot campaigns: Pre-generate ZIPs per time slot
- Playlist format: M3U (text format)
- Include playlist.m3u in ZIP file with media files

**Time Slot Handling:**
- For "time_slot" campaigns: Pre-generate ZIPs for each time slot
- Device receives appropriate ZIP based on current time
- Single timezone (no timezone conversion needed)
- Simple HH:MM format

## API Specifications

### API Versioning
- All device API endpoints under `/api/v1/`
- Admin API can be unversioned or versioned
- Auto-generated Swagger/OpenAPI docs (DRF built-in)

### Device API Endpoints

**Authentication:**
- Shared API token for all devices (pilot phase)
- Token passed in `Authorization: Bearer <token>` header

**1. Content Endpoint**
```
GET /api/v1/devices/{device_id}/content/
```
- Returns: ZIP file containing:
  - `playlist.m3u` (M3U format with all active campaigns for device)
  - All media files for active campaigns
- For time-slot campaigns: Pre-generated ZIPs, return appropriate one based on current time
- Content-Type: `application/zip`

**2. Status Endpoint**
```
POST /api/v1/devices/{device_id}/status/
```
- Combined endpoint for heartbeat + proof of play (proof of play deferred for now)
- Request body structure (TBD - deferred)
- For MVP: Can be simple heartbeat with timestamp

### Admin API Endpoints

- Standard CRUD endpoints for Screens, Campaigns, Media files
- Use Django REST Framework
- Authentication: Session-based or JWT (TBD)

## Data Models

### Screen/Device Model
- Device ID/Name (unique)
- Location fields
- Status (Active/Inactive/Maintenance)
- Description, Notes
- Photo (FileField)
- Payment/Commission fields (as listed above)

### Campaign Model
- Campaign name
- Campaign type ("all_day" or "time_slot")
- Start date, End date
- Screens (many-to-many relationship)
- Status (Draft/Review/Active/Paused/Completed)
- Budget fields (slot price, daily budget, total budget, pause flag)
- Media file (FileField)
- Time slots (for "time_slot" campaigns):
  - Start time, End time (HH:MM format)

### Time Slot Model (if needed)
- Campaign (ForeignKey)
- Start time, End time
- Or store as JSON field on Campaign model

## Admin Panel UI Requirements

### Key Pages (from mockups):

**1. Dashboard**
- Metrics cards (Active Campaigns, Impressions, Ad Spend)
- Charts (Daily Impressions line chart)
- Map with location pins
- Recent campaigns table
- Date range selector

**2. Campaign Creation Flow**
- Step 1: Details & Targeting
  - Campaign details form
  - Map with location pins for screen selection
  - Venue filter dropdown
  - Selected locations list
- Step 2: Targeting (if needed)
- Step 3: Ad Content Upload
  - Drag & drop file upload
  - Rich text editor for ad copy (if needed)
  - Media preview
  - Live preview of ad on digital screen
- Step 4: Review & Launch
  - Review all campaign details
  - Launch button

**3. Screen Management**
- List view with filters
- Create/Edit forms with all required fields
- Map integration for location selection

## Implementation Details

### File Storage
- Django FileField (local server storage)
- Media files stored in Django media directory
- ZIP generation: On-the-fly or pre-generated (for time slots)

### Error Handling
- Retry logic on device side (already implemented)
- Budget exceeded: Depends on campaign flag (pause if checked, track if unchecked)
- Standard HTTP error codes for API

### Logging (Minimal)
- Device API errors (failed requests, auth failures)
- Campaign state changes (launched, paused, completed, budget reached)
- All exceptions/errors
- Critical admin actions (screen/campaign create/delete)
- Structured logging (JSON format recommended)
- File-based logging (Django default)

### Testing
- Unit tests for critical business logic:
  - Playlist generation
  - Budget tracking
  - Campaign pause logic
  - ZIP generation
  - Time slot filtering
  - Campaign-to-screen assignment

## Deployment

### Environment Setup
- Development + Production only (no staging)
- Environment variables for secrets (`.env` files)
- Use `python-decouple` or `django-environ`
- Database migrations (standard Django)
- No seed data (manual admin user creation)

### Deployment Configuration
- Docker + Docker Compose for development
- VPS deployment for production
- Simple deployment process (Git push → manual deploy, or Docker)

## Excluded from MVP

- Reporting/dashboards (SQL queries for now)
- Payment processing (future release)
- Proof of play details (deferred)
- Real-time metrics
- Alerts/notifications (logging only)

## Timeline Estimate

**Total Estimate: 37-54 hours**

**Breakdown:**
- Django Backend: 15-20 hours
- DRF API Endpoints: 5-8 hours
- React Frontend: 10-15 hours
- Database Setup: 2-3 hours
- File Handling: 2-3 hours
- Deployment Setup: 3-5 hours

## Deliverables

1. Django backend with REST API
2. React + TypeScript admin panel
3. Database schema and migrations
4. API documentation (Swagger/OpenAPI)
5. Basic deployment setup
6. Unit tests for critical business logic
7. README with setup instructions

## Notes

- Focus on MVP functionality first
- UI should match provided mockups
- Code should be maintainable and well-structured
- Use best practices for Django and React
- Consider future scalability but prioritize MVP delivery


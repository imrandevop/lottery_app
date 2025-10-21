# User Activity Tracking API - Testing Guide

## API Endpoint
**URL:** `POST /users/track-activity/`

## Purpose
Track active users for the "lotto" and "lotto lite" applications separately to:
- Count unique users accessing each app today
- Track how many times each user accessed the app
- Identify if users are new (joined today) or existing

## Request Body

### Example 1: Lotto app with phone number
```json
{
  "unique_id": "device_12345",
  "phone_number": "+919876543210",
  "app_name": "lotto"
}
```

### Example 2: Lotto Lite app without phone number
```json
{
  "unique_id": "android_xyz789",
  "app_name": "lotto lite"
}
```

### Example 3: With phone number normalization (10 digits)
```json
{
  "unique_id": "iphone_abc456",
  "phone_number": "9876543210",
  "app_name": "lotto"
}
```
*Note: Phone number will be automatically normalized to +919876543210*

### Example 4: UUID format (also supported)
```json
{
  "unique_id": "123e4567-e89b-12d3-a456-426614174000",
  "phone_number": "+919876543210",
  "app_name": "lotto"
}
```
*Note: unique_id can be any string (max 255 characters)*

## Response

### Success Response (200 OK)
```json
{
  "status": "success",
  "message": "User activity recorded successfully"
}
```

### Error Response (400 Bad Request)
```json
{
  "status": "error",
  "message": "Invalid data",
  "errors": {
    "app_name": ["Invalid app_name. Must be 'lotto' or 'lotto lite'"]
  }
}
```

## Testing with cURL

### Test 1: First access (Lotto app with phone)
```bash
curl -X POST http://127.0.0.1:8000/users/track-activity/ \
  -H "Content-Type: application/json" \
  -d '{
    "unique_id": "device_12345",
    "phone_number": "+919876543210",
    "app_name": "lotto"
  }'
```

### Test 2: Second access (same user - access count increments)
```bash
curl -X POST http://127.0.0.1:8000/users/track-activity/ \
  -H "Content-Type: application/json" \
  -d '{
    "unique_id": "device_12345",
    "phone_number": "+919876543210",
    "app_name": "lotto"
  }'
```

### Test 3: Lotto Lite app without phone number
```bash
curl -X POST http://127.0.0.1:8000/users/track-activity/ \
  -H "Content-Type: application/json" \
  -d '{
    "unique_id": "android_xyz789",
    "app_name": "lotto lite"
  }'
```

### Test 4: Invalid app name (should fail)
```bash
curl -X POST http://127.0.0.1:8000/users/track-activity/ \
  -H "Content-Type: application/json" \
  -d '{
    "unique_id": "device_test",
    "app_name": "invalid_app"
  }'
```

## Testing with Postman

1. **Method:** POST
2. **URL:** `http://127.0.0.1:8000/users/track-activity/`
3. **Headers:**
   - Content-Type: `application/json`
4. **Body (raw JSON):**
```json
{
  "unique_id": "device_12345",
  "phone_number": "+919876543210",
  "app_name": "lotto"
}
```

## What Happens Behind the Scenes

### First Access (New User)
1. API receives request with unique_id, phone_number, and app_name
2. System creates new record in UserActivity table:
   - `access_count = 1`
   - `first_access = current timestamp`
   - `last_access = current timestamp`
3. Returns success message

### Subsequent Access (Existing User)
1. API receives request with same unique_id and app_name
2. System finds existing record and:
   - Increments `access_count` by 1
   - Updates `last_access` to current timestamp
   - Updates `phone_number` if it's now provided and wasn't before
3. Returns success message

## Admin Panel Features

After accessing `/admin/users/useractivity/`, you'll see:

### Statistics Dashboard (Top of page)
- **Lotto App:**
  - Today's unique users: X
  - Total users all-time: Y

- **Lotto Lite App:**
  - Today's unique users: X
  - Total users all-time: Y

### User Activity List
Shows each record with:
- **Unique ID:** Device identifier (shortened if > 20 chars, e.g., "device_12345" or "123e4567-e89b-12d3...")
- **Phone Number:** Full phone number or "None"
- **App Name:** lotto or lotto lite
- **Access Count:** How many times accessed (increments on each API call)
- **User Status:**
  - ✓ New User (green) - if phone number joined today
  - Existing User (blue) - if phone number joined before today
  - No Phone (gray) - if no phone number provided
- **First Access:** First time this device accessed the app (IST)
- **Last Access:** Most recent access time (IST)

### Filtering Options
- Filter by app_name (lotto / lotto lite)
- Filter by first_access date
- Filter by last_access date
- Search by unique_id or phone_number

## Field Descriptions

| Field | Required | Description | Example |
|-------|----------|-------------|---------|
| unique_id | Yes | Any string identifier from mobile app (device/installation ID, max 255 chars) | "device_12345", "android_xyz", "123e4567-e89b-12d3-a456-426614174000" |
| phone_number | No | User phone number (only for apps with auth) | "+919876543210" or null |
| app_name | Yes | Application name | "lotto" or "lotto lite" |

## Phone Number Normalization

The API automatically normalizes phone numbers:
- `9876543210` → `+919876543210`
- `919876543210` → `+919876543210`
- `+919876543210` → `+919876543210` (no change)

## How "New vs Existing User" is Determined

If phone number is provided:
1. System looks up the phone number in the User table
2. Checks the `date_joined` field
3. Compares with today's date (in IST timezone)
4. If joined today → "New User"
5. If joined before today → "Existing User"
6. If not found in User table → "New User"

If no phone number is provided:
- Status shows "No Phone" (gray)

## Important Notes

1. **Unique Constraint:** One record per (unique_id, app_name) combination
   - Same unique_id can exist for both "lotto" and "lotto lite" separately

2. **Timezone:** All timestamps use IST (Asia/Kolkata)

3. **Access Count:** Increments on every API call, regardless of phone number

4. **Phone Number Update:** If a device initially doesn't have a phone number but provides one later, it will be updated

5. **Today's Count:** Resets daily at midnight IST

## Example Scenarios

### Scenario 1: Lotto app user with phone auth
- User opens app (1st time): `access_count = 1`
- User closes and reopens: `access_count = 2`
- User reopens again: `access_count = 3`
- Admin panel shows: "Access Count: 3"

### Scenario 2: Lotto Lite app user without phone
- User opens app: Record created with `phone_number = null`
- Admin panel shows: "No Phone" status

### Scenario 3: Same device, different apps
- Device ID "device_123" uses Lotto app → Creates record 1
- Same device uses Lotto Lite app → Creates record 2 (separate tracking)

## Troubleshooting

### Error: "Invalid app_name"
- **Cause:** app_name is not "lotto" or "lotto lite"
- **Solution:** Use exact values "lotto" or "lotto lite" (lowercase)

### Error: "Invalid data"
- **Cause:** Missing required field or empty unique_id
- **Solution:** Ensure unique_id is not empty and app_name is provided

### Phone number not showing in admin
- **Cause:** Phone number not provided in request or is null/empty
- **Solution:** Include phone_number in request body for apps with auth

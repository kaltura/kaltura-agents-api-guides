# Kaltura User Profile API

The User Profile service manages per-application user profiles, primarily for the Events Platform attendance lifecycle. Each profile ties a Kaltura user to a specific app instance (registered in the [App Registry](KALTURA_APP_REGISTRY_API.md)) and tracks profile data, login activity, event attendance status, and application-specific metadata.

A user has one profile per app — the same `userId` can have separate profiles across different events, each with its own registration data and attendance status.

**Base URL:** `https://user.nvp1.ovp.kaltura.com/api/v1` (production NVP region)  
**Auth:** `Authorization: Bearer <KS>` header (ADMIN KS, type=2, requires `ADMIN_BASE` permission)  
**Format:** JSON request/response bodies, all endpoints use POST  
**Regions:** NVP (default `nvp1`), EU (`irp2`), DE (`frp2`)  


# 1. Authentication

All `user-profile/*` endpoints require an ADMIN KS (type=2) with `ADMIN_BASE` permission:

```
Authorization: Bearer <your_kaltura_session>
```

The `reports/eventDataStats` endpoint accepts KS with either `ANALYTICS_BASE` or `EP_USER_ANALYTICS` permission.

Generate an ADMIN KS via `session.start` (see [Session Guide](KALTURA_SESSION_GUIDE.md)) or `appToken.startSession` (see [AppTokens Guide](KALTURA_APPTOKENS_API.md)).

```bash
# Set up environment
export KALTURA_USER_PROFILE_URL="https://user.nvp1.ovp.kaltura.com/api/v1"
```


# 2. Prerequisites

Before creating user profiles:

1. **The user must exist** as a KalturaUser in your partner account (created via `user.add` in API v3). The service validates this by calling `user.get` internally.
2. **The app must be registered and enabled** in the [App Registry](KALTURA_APP_REGISTRY_API.md) — the `appGuid` must reference a valid registered app for your partner. Validation results are cached for up to 24 hours.


# 3. User Profile Entity

| Field | Type | Description |
|-------|------|-------------|
| `id` | string | Auto-generated profile ID (read-only) |
| `partnerId` | integer | Partner ID from KS (read-only) |
| `appGuid` | string | App Registry GUID this profile belongs to (immutable after creation) |
| `userId` | string | Kaltura user ID (immutable after creation) |
| `status` | string | `enabled`, `disabled`, or `deleted` |
| `profileData` | object | Custom JSON — registration form data, user attributes, etc. |
| `loginData` | object | Login tracking (see section 3.1) |
| `eventData` | object | Event attendance lifecycle (see section 3.2) |
| `appData` | object | Application-specific JSON metadata |
| `createdAt` | string | ISO 8601 timestamp, e.g. `"2026-04-09T04:56:27.940Z"` (read-only) |
| `updatedAt` | string | ISO 8601 timestamp, e.g. `"2026-04-09T04:56:27.940Z"` (read-only) |
| `deletedAt` | string | ISO 8601 timestamp, set on soft-delete (read-only) |
| `objectType` | string | Always `"UserProfile"` in responses (read-only) |

A profile is uniquely identified by the combination of `partnerId` + `appGuid` + `userId`. Each user can have one active (non-deleted) profile per app. After a profile is soft-deleted, a new one can be created for the same user + app combination.

### User ID Case Sensitivity

User IDs containing `@` (email addresses) are matched **case-insensitively** — creating a profile for `User@Example.com` when one already exists for `user@example.com` returns `USER_ALREADY_ASSOCIATED_TO_APP_GUID`. User IDs without `@` are matched **case-sensitively**.

## 3.1 Login Data

Tracks the user's most recent login activity. Not auto-updated — must be set explicitly via `add` or `update`.

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `lastLoginDate` | string | Yes (within loginData) | ISO 8601 timestamp of last login |
| `lastLoginType` | string | Yes (within loginData) | Login method: `sso`, `emailPass`, `magicLink`, `simpleLogin`, or `guestLogin` |

## 3.2 Event Data

Tracks the user's event attendance lifecycle. This is the primary use case for Events Platform integrations.

| Field | Type | Writable | Description |
|-------|------|----------|-------------|
| `regOrigin` | string | Yes | How the user registered (see values below) |
| `attendanceStatus` | string | Yes | Current attendance status (see lifecycle in section 4) |
| `userRegistrationType` | string | Yes | Attendance type requested: `virtualAttendanceRequest`, `inPersonAttendanceRequest`, or `both` |
| `attendanceType` | string | Yes | Confirmed attendance type: `virtualAttendanceConfirmed`, `inPersonAttendanceConfirmed`, `both`, or `none` |
| `allowedAttendanceType` | string | Yes | Allowed attendance: `virtualAttendanceAllowed`, `inPersonAttendanceAllowed`, `both`, or `none` |
| `isRegistered` | boolean | Yes | Registration flag (default: `false`) |
| `previousAttendanceStatus` | string | Read-only | Auto-set to previous status on each `attendanceStatus` change |
| `statusUpdateTime` | string | Read-only | ISO 8601 timestamp, auto-set when `attendanceStatus` changes |
| `firstAttendedStatusTime` | string | Read-only | ISO 8601 timestamp, auto-set on first transition to `attended` or higher. **Set only once — never overwritten.** |

### Registration Origin Values

| Value | Description |
|-------|-------------|
| `registration` | Self-registered via form |
| `invite` | Invited by organizer |
| `webhook` | Registered via webhook/integration |
| `sso` | Registered via SSO |
| `admin` | Registered by administrator |


# 4. Attendance Status Lifecycle

The `attendanceStatus` field tracks user progression through the event lifecycle. Any status can transition to any other status — there are no enforced transition restrictions.

```
created --> registered --> confirmed --> attended --> participated --> participatedPostEvent
                |              |
                v              v
           unregistered     blocked

invited --> invitedPendingRegistration --> registered --> ...
```

| Status | Description |
|--------|-------------|
| `created` | Profile created, no registration activity yet |
| `registered` | User has registered for the event |
| `unregistered` | User cancelled their registration |
| `invited` | User was invited to the event |
| `invitedPendingRegistration` | Invited but registration not yet completed |
| `confirmed` | User confirmed attendance |
| `autoConfirmed` | System auto-confirmed the user |
| `attended` | User attended the event |
| `participated` | User actively participated during the event |
| `participatedPostEvent` | User engaged with content after the event ended |
| `blocked` | User blocked from attending |

### Automatic Side Effects

Every `attendanceStatus` change triggers:
1. `previousAttendanceStatus` is set to the old status value
2. `statusUpdateTime` is set to the current timestamp

The statuses `attended`, `participated`, and `participatedPostEvent` are considered **"high attendance"** — when a profile first transitions to any of these, `firstAttendedStatusTime` is automatically recorded. This timestamp is set only once and never overwritten, even if the status later changes.


# 5. Create a User Profile

```
POST /api/v1/user-profile/add
Content-Type: application/json
Authorization: Bearer <KS>
```

```json
{
  "appGuid": "app-guid-from-registry",
  "userId": "user@example.com",
  "profileData": {
    "name": "Jane Doe",
    "company": "Acme Corp",
    "role": "Speaker"
  },
  "loginData": {
    "lastLoginDate": "2025-06-15T10:30:00Z",
    "lastLoginType": "sso"
  },
  "eventData": {
    "regOrigin": "registration",
    "attendanceStatus": "registered",
    "userRegistrationType": "virtualAttendanceRequest"
  }
}
```

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `appGuid` | string | Yes | App Registry GUID (must be registered and enabled) |
| `userId` | string | Yes | Kaltura user ID (must exist in your account) |
| `profileData` | object | Yes | Custom user attributes (any valid JSON) |
| `loginData` | object | No | Login tracking (both subfields required if provided) |
| `eventData` | object | No | Event attendance data |
| `appData` | object | No | App-specific metadata |
| `status` | string | No | Default: `enabled` |

If `eventData.attendanceStatus` is set to `attended`, `participated`, or `participatedPostEvent` at creation time, `firstAttendedStatusTime` is automatically recorded.

**Response:** Full user profile object with generated `id`.

```bash
curl -X POST "$KALTURA_USER_PROFILE_URL/user-profile/add" \
  -H "Authorization: Bearer $KALTURA_KS" \
  -H "Content-Type: application/json" \
  -d "{
    \"appGuid\": \"$APP_GUID\",
    \"userId\": \"user@example.com\",
    \"profileData\": {
      \"name\": \"Jane Doe\",
      \"company\": \"Acme Corp\"
    },
    \"eventData\": {
      \"regOrigin\": \"registration\",
      \"attendanceStatus\": \"registered\"
    }
  }"
```

### Error Codes

| Code | Meaning |
|------|---------|
| `USER_ALREADY_ASSOCIATED_TO_APP_GUID` | Profile already exists for this appGuid + userId (active, non-deleted) |
| `USER_ALREADY_EXIST` | Duplicate key error (concurrent creation race) |
| `OBJECT_NOT_FOUND` | appGuid not found or not enabled in App Registry |
| `USER_ID_NOT_FOUND` | userId does not exist in your Kaltura account |


# 6. Bulk Create User Profiles

Create multiple profiles in a single request. All profiles must belong to the same app.

```
POST /api/v1/user-profile/bulkAdd
Content-Type: application/json
Authorization: Bearer <KS>
```

```json
[
  {
    "appGuid": "app-guid",
    "userId": "user1@example.com",
    "profileData": {"name": "Alice"}
  },
  {
    "appGuid": "app-guid",
    "userId": "user2@example.com",
    "profileData": {"name": "Bob"}
  }
]
```

**Constraints:**

- All items must have the **same `appGuid`** (mixed appGuids return `NOT_YET_SUPPORTED`)
- Array size: minimum 1, maximum 50 (configurable per deployment)
- The app is validated once for the shared `appGuid`; user IDs are validated in bulk via `user.list`

**Response:** Array of results **in the same order** as input. Each element is either a user profile object (on success) or an error object (on failure). Partial success is possible — HTTP 200 even if some items fail.

```json
[
  {"id": "...", "userId": "user1@example.com", "objectType": "UserProfile", ...},
  {"code": "USER_ALREADY_ASSOCIATED_TO_APP_GUID", "message": "...", "objectType": "KalturaAPIException"}
]
```

```bash
curl -X POST "$KALTURA_USER_PROFILE_URL/user-profile/bulkAdd" \
  -H "Authorization: Bearer $KALTURA_KS" \
  -H "Content-Type: application/json" \
  -d "[
    {\"appGuid\": \"$APP_GUID\", \"userId\": \"user1@example.com\", \"profileData\": {\"name\": \"Alice\"}},
    {\"appGuid\": \"$APP_GUID\", \"userId\": \"user2@example.com\", \"profileData\": {\"name\": \"Bob\"}}
  ]"
```


# 7. Get a User Profile

## 7.1 Get by ID

```bash
curl -X POST "$KALTURA_USER_PROFILE_URL/user-profile/get" \
  -H "Authorization: Bearer $KALTURA_KS" \
  -H "Content-Type: application/json" \
  -d "{\"id\": \"$PROFILE_ID\"}"
```

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `id` | string | Yes | User profile ID |

**Response:** Full user profile object. Returns `USER_PROFILE_NOT_FOUND` if the ID does not exist or the profile is deleted.

## 7.2 Get by Filter

Returns the **first matching** profile (internally calls `list` with `limit: 1`). Use this to look up a user within a specific app:

```bash
curl -X POST "$KALTURA_USER_PROFILE_URL/user-profile/getByFilter" \
  -H "Authorization: Bearer $KALTURA_KS" \
  -H "Content-Type: application/json" \
  -d "{
    \"appGuidIn\": [\"$APP_GUID\"],
    \"userIdIn\": [\"user@example.com\"],
    \"status\": \"enabled\"
  }"
```

Filter fields are the same as those used in `list` (see section 9). Returns `null` if no match is found.


# 8. Update a User Profile

```
POST /api/v1/user-profile/update
Content-Type: application/json
Authorization: Bearer <KS>
```

```json
{
  "id": "profile-id",
  "eventData": {
    "attendanceStatus": "attended"
  },
  "profileData": {
    "name": "Jane Doe",
    "company": "Updated Corp"
  }
}
```

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `id` | string | Yes | Profile ID to update |
| `status` | string | No | Update status |
| `profileData` | object | No | Replace profile data |
| `loginData` | object | No | Update login tracking |
| `eventData` | object | No | Update attendance data |
| `appData` | object | No | Update app-specific data |

The `partnerId`, `appGuid`, `userId`, and timestamp fields cannot be modified.

### Merge Behavior

`eventData` and `loginData` are **shallow-merged** with the existing values. Updating `eventData.attendanceStatus` preserves the existing `regOrigin`, `userRegistrationType`, etc. You only need to send the fields you want to change.

`profileData` and `appData` are **replaced entirely** — send the complete object, not just the fields you want to change.

```bash
# Mark a user as "attended"
curl -X POST "$KALTURA_USER_PROFILE_URL/user-profile/update" \
  -H "Authorization: Bearer $KALTURA_KS" \
  -H "Content-Type: application/json" \
  -d "{
    \"id\": \"$PROFILE_ID\",
    \"eventData\": {
      \"attendanceStatus\": \"attended\"
    }
  }"
```

When `attendanceStatus` changes, `previousAttendanceStatus` and `statusUpdateTime` are automatically updated. On the first transition to `attended`, `participated`, or `participatedPostEvent`, `firstAttendedStatusTime` is recorded (once only).


# 9. List User Profiles

```
POST /api/v1/user-profile/list
Content-Type: application/json
Authorization: Bearer <KS>
```

```json
{
  "filter": {
    "appGuidIn": ["app-guid"],
    "attendanceStatus": "registered"
  },
  "pager": {
    "offset": 0,
    "limit": 100
  },
  "orderBy": "-createdAt",
  "includeTotalCount": true
}
```

Deleted profiles are **always excluded** from list results — this is hardcoded and cannot be overridden with a status filter.

## 9.1 Filter Fields

All filter fields are optional. Provided fields are AND'd together.

| Field | Type | Description |
|-------|------|-------------|
| `idIn` | string[] | Filter by profile IDs. Invalid IDs silently ignored. |
| `appGuidIn` | string[] | Filter by app GUIDs |
| `userIdIn` | string[] | Filter by user IDs. Email addresses (containing `@`) are matched case-insensitively. Non-email IDs are matched case-sensitively. |
| `status` | string | `enabled` or `disabled` (deleted always excluded) |
| `attendanceStatus` | string | Filter by current attendance status |
| `regOriginIn` | string[] | Filter by registration origins |
| `previousAttendanceStatus` | string | Filter by previous status |
| `userRegistrationType` | string | Filter by requested attendance type |
| `attendanceType` | string | Filter by confirmed attendance type |
| `allowedAttendanceType` | string | Filter by allowed attendance type |
| `createdAtGreaterThanOrEqual` | string | ISO 8601 minimum creation date |
| `createdAtLessThanOrEqual` | string | ISO 8601 maximum creation date |
| `updatedAtGreaterThanOrEqual` | string | ISO 8601 minimum update date |
| `updatedAtLessThanOrEqual` | string | ISO 8601 maximum update date |

> **Deprecated:** The `regOrigin` (singular) filter field still works but is superseded by `regOriginIn` (array). If both are provided, `regOriginIn` takes precedence.

## 9.2 Pager

| Field | Type | Default | Description |
|-------|------|---------|-------------|
| `offset` | integer | 0 | Number of records to skip |
| `limit` | integer | 50 | Maximum records to return |

## 9.3 Sorting

Use `orderBy` with a field name. Prefix with `-` for descending order:

- `"createdAt"` — oldest first
- `"-createdAt"` — newest first
- `"-updatedAt"` — recently updated first

## 9.4 Total Count

Set `"includeTotalCount": true` (default) to include the total number of matching records. Set to `false` for faster queries — `totalCount` returns `-1` when disabled.

**Response:**

```json
{
  "objects": [
    {
      "id": "...",
      "appGuid": "...",
      "userId": "user@example.com",
      "profileData": {"name": "Jane Doe"},
      "eventData": {"attendanceStatus": "registered"},
      "objectType": "UserProfile",
      ...
    }
  ],
  "totalCount": 250
}
```

```bash
# List all registered users for an event app
curl -X POST "$KALTURA_USER_PROFILE_URL/user-profile/list" \
  -H "Authorization: Bearer $KALTURA_KS" \
  -H "Content-Type: application/json" \
  -d "{
    \"filter\": {
      \"appGuidIn\": [\"$APP_GUID\"],
      \"attendanceStatus\": \"registered\"
    },
    \"pager\": {\"offset\": 0, \"limit\": 100},
    \"orderBy\": \"-createdAt\"
  }"
```


# 10. Delete a User Profile

Soft-deletes the profile — sets `status` to `"deleted"` and records a `deletedAt` timestamp. The record remains in the database but is excluded from all queries.

```bash
curl -X POST "$KALTURA_USER_PROFILE_URL/user-profile/delete" \
  -H "Authorization: Bearer $KALTURA_KS" \
  -H "Content-Type: application/json" \
  -d "{\"id\": \"$PROFILE_ID\"}"
```

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `id` | string | Yes | Profile ID to delete |

**Response:** Empty body on success (HTTP 200). Returns `USER_PROFILE_NOT_FOUND` if the ID does not exist.

After soft-deletion, a **new profile can be created** for the same `userId` + `appGuid` combination. The deleted profile's `deletedAt` timestamp makes it unique in the database, allowing the new profile.

When a KalturaUser is deleted from your account, all of their non-deleted user profiles across all apps are automatically soft-deleted.


# 11. Reports

The reports controller provides aggregate statistics over user profiles.

## 11.1 Event Data Statistics

Get attendance and registration statistics grouped by dimensions.

```
POST /api/v1/reports/eventDataStats
Content-Type: application/json
Authorization: Bearer <KS>
```

This endpoint requires `ANALYTICS_BASE` or `EP_USER_ANALYTICS` permission (different from the `ADMIN_BASE` required by other endpoints).

```json
{
  "filter": {
    "appGuidIn": ["app-guid-1", "app-guid-2"],
    "attendanceStatusIn": ["attended", "participated"],
    "regOriginIn": ["registration", "invite"]
  },
  "dimensions": ["attendanceStatus", "regOrigin"]
}
```

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `filter.appGuidIn` | string[] | Yes | One or more app GUIDs (at least one required) |
| `filter.attendanceStatusIn` | string[] | No | Filter by attendance statuses |
| `filter.regOriginIn` | string[] | No | Filter by registration origins |
| `dimensions` | string[] | Yes | Grouping dimensions (at least one): `attendanceStatus`, `regOrigin`, or both |

**Response:**

```json
{
  "results": [
    {
      "appGuid": "app-guid-1",
      "dimensions": {
        "attendanceStatus": "attended",
        "regOrigin": "registration"
      },
      "count": 45
    },
    {
      "appGuid": "app-guid-1",
      "dimensions": {
        "attendanceStatus": "participated",
        "regOrigin": "invite"
      },
      "count": 23
    }
  ],
  "sum": 68
}
```

```bash
# Get attendance breakdown for an event
curl -X POST "$KALTURA_USER_PROFILE_URL/reports/eventDataStats" \
  -H "Authorization: Bearer $KALTURA_KS" \
  -H "Content-Type: application/json" \
  -d "{
    \"filter\": {
      \"appGuidIn\": [\"$APP_GUID\"]
    },
    \"dimensions\": [\"attendanceStatus\"]
  }"
```

## 11.2 First Attendance Per App

Get counts of users who reached "attended" status or higher, grouped by app. Uses the `firstAttendedStatusTime` timestamp.

```
POST /api/v1/user-profile/firstAttendanceStatusPerApp
Content-Type: application/json
Authorization: Bearer <KS>
```

```json
{
  "fromDate": "2025-01-01T00:00:00Z",
  "toDate": "2025-12-31T23:59:59Z"
}
```

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `fromDate` | string | No | ISO 8601 start date (filters `firstAttendedStatusTime`) |
| `toDate` | string | No | ISO 8601 end date |

**Response:** Object keyed by `appGuid` with attendance counts:

```json
{
  "app-guid-1": 145,
  "app-guid-2": 82
}
```

```bash
curl -X POST "$KALTURA_USER_PROFILE_URL/user-profile/firstAttendanceStatusPerApp" \
  -H "Authorization: Bearer $KALTURA_KS" \
  -H "Content-Type: application/json" \
  -d '{
    "fromDate": "2025-01-01T00:00:00Z",
    "toDate": "2025-12-31T23:59:59Z"
  }'
```


# 12. Error Handling

Application-level errors return HTTP 200 with an error object:

```json
{
  "code": "USER_PROFILE_NOT_FOUND",
  "message": "Description of the error",
  "objectType": "KalturaAPIException"
}
```

Validation errors (missing required fields, invalid enum values) return HTTP 400.

| Error Code | Meaning |
|------------|---------|
| `USER_PROFILE_NOT_FOUND` | Profile ID not found or deleted |
| `USER_ALREADY_ASSOCIATED_TO_APP_GUID` | Active profile already exists for this appGuid + userId |
| `USER_ALREADY_EXIST` | Duplicate key error (race condition on concurrent creation) |
| `OBJECT_NOT_FOUND` | appGuid not found or not enabled in App Registry |
| `USER_ID_NOT_FOUND` | userId does not exist in your Kaltura account |
| `NOT_YET_SUPPORTED` | bulkAdd with mixed appGuids |
| `AMOUNT_OF_USERS_SENT_NOT_IN_ALLOWED_RANGE` | bulkAdd array size outside 1-50 range |
| `SESSION_START_FAILED` | Internal session validation failure |

**Retry strategy:** For transient errors (HTTP 5xx, timeouts, `SESSION_START_FAILED`), retry with exponential backoff: 1s, 2s, 4s, with jitter, up to 3 retries. For client errors (HTTP 400, `USER_PROFILE_NOT_FOUND`, `USER_ALREADY_ASSOCIATED_TO_APP_GUID`, `USER_ID_NOT_FOUND`), fix the request before retrying — these will not resolve on their own.


# 13. Common Integration Patterns

## 13.1 Event Registration Flow

```bash
# 1. Register the app in App Registry (one-time setup)
APP_GUID=$(curl -s -X POST "$KALTURA_APP_REGISTRY_URL/app-registry/add" \
  -H "Authorization: Bearer $KALTURA_KS" \
  -H "Content-Type: application/json" \
  -d '{"appCustomId": "webinar-2025-q4", "appType": "ep", "appCustomName": "Q4 Webinar"}' \
  | jq -r '.id')

# 2. Create user profile when they register
PROFILE_ID=$(curl -s -X POST "$KALTURA_USER_PROFILE_URL/user-profile/add" \
  -H "Authorization: Bearer $KALTURA_KS" \
  -H "Content-Type: application/json" \
  -d "{
    \"appGuid\": \"$APP_GUID\",
    \"userId\": \"attendee@example.com\",
    \"profileData\": {\"name\": \"John Smith\", \"company\": \"Tech Corp\"},
    \"eventData\": {
      \"regOrigin\": \"registration\",
      \"attendanceStatus\": \"registered\",
      \"userRegistrationType\": \"virtualAttendanceRequest\"
    }
  }" | jq -r '.id')

# 3. Confirm attendance
curl -s -X POST "$KALTURA_USER_PROFILE_URL/user-profile/update" \
  -H "Authorization: Bearer $KALTURA_KS" \
  -H "Content-Type: application/json" \
  -d "{
    \"id\": \"$PROFILE_ID\",
    \"eventData\": {\"attendanceStatus\": \"confirmed\"}
  }"

# 4. Mark as attended (during event — triggers firstAttendedStatusTime)
curl -s -X POST "$KALTURA_USER_PROFILE_URL/user-profile/update" \
  -H "Authorization: Bearer $KALTURA_KS" \
  -H "Content-Type: application/json" \
  -d "{
    \"id\": \"$PROFILE_ID\",
    \"eventData\": {\"attendanceStatus\": \"attended\"}
  }"

# 5. Get attendance stats
curl -s -X POST "$KALTURA_USER_PROFILE_URL/reports/eventDataStats" \
  -H "Authorization: Bearer $KALTURA_KS" \
  -H "Content-Type: application/json" \
  -d "{
    \"filter\": {\"appGuidIn\": [\"$APP_GUID\"]},
    \"dimensions\": [\"attendanceStatus\"]
  }"
```

## 13.2 Bulk Import Attendees

```bash
# Import a batch of invited users
curl -X POST "$KALTURA_USER_PROFILE_URL/user-profile/bulkAdd" \
  -H "Authorization: Bearer $KALTURA_KS" \
  -H "Content-Type: application/json" \
  -d "[
    {\"appGuid\": \"$APP_GUID\", \"userId\": \"vip1@example.com\", \"profileData\": {\"name\": \"VIP One\"}, \"eventData\": {\"regOrigin\": \"invite\", \"attendanceStatus\": \"invited\"}},
    {\"appGuid\": \"$APP_GUID\", \"userId\": \"vip2@example.com\", \"profileData\": {\"name\": \"VIP Two\"}, \"eventData\": {\"regOrigin\": \"invite\", \"attendanceStatus\": \"invited\"}}
  ]"
```

## 13.3 Cross-Service Registration Data Retrieval

The full workflow for extracting registration data for a virtual event spans multiple services. The key linkage is that `appCustomId` in the App Registry equals the `virtualEventId`:

```bash
# Step 1: List virtual events to get event IDs
VIRTUAL_EVENT_ID=$(curl -s -X POST "$KALTURA_SERVICE_URL/service/virtualevent_virtualevent/action/list" \
  -d "ks=$KALTURA_KS" -d "format=1" | jq -r '.objects[0].id')

# Step 2: Resolve virtual event ID → App GUID via App Registry
APP_GUID=$(curl -s -X POST "$KALTURA_APP_REGISTRY_URL/app-registry/list" \
  -H "Authorization: Bearer $KALTURA_KS" \
  -H "Content-Type: application/json" \
  -d "{\"filter\": {\"appCustomIdIn\": [\"$VIRTUAL_EVENT_ID\"]}}" \
  | jq -r '.objects[0].id')

# Step 3: Pull registration/attendance data
RESPONSE=$(curl -s -X POST "$KALTURA_USER_PROFILE_URL/user-profile/list" \
  -H "Authorization: Bearer $KALTURA_KS" \
  -H "Content-Type: application/json" \
  -d "{
    \"filter\": {\"appGuidIn\": [\"$APP_GUID\"]},
    \"pager\": {\"offset\": 0, \"limit\": 500},
    \"orderBy\": \"createdAt\",
    \"includeTotalCount\": true
  }")

# Step 4: Join with core user data for complete profiles
# User Profile has eventData (attendance) and profileData (custom fields)
# Core fields (email, firstName, lastName, company, jobTitle) are in user.list
USER_IDS=$(echo "$RESPONSE" | jq -r '[.objects[].userId] | join(",")')
curl -s -X POST "$KALTURA_SERVICE_URL/service/user/action/list" \
  -d "ks=$KALTURA_KS" -d "format=1" \
  -d "filter[objectType]=KalturaUserFilter" \
  -d "filter[idIn]=$USER_IDS"
```

See the [App Registry API](KALTURA_APP_REGISTRY_API.md) section 12.4 for the complete cross-service diagram.

## 13.4 Incremental Data Pull

Use `updatedAtGreaterThanOrEqual` to pull only profiles changed since your last sync — essential for large-scale integrations:

```bash
# Pull profiles updated since your last watermark
LAST_SYNC="2025-06-14T00:00:00Z"
curl -s -X POST "$KALTURA_USER_PROFILE_URL/user-profile/list" \
  -H "Authorization: Bearer $KALTURA_KS" \
  -H "Content-Type: application/json" \
  -d "{
    \"filter\": {
      \"appGuidIn\": [\"$APP_GUID\"],
      \"updatedAtGreaterThanOrEqual\": \"$LAST_SYNC\"
    },
    \"pager\": {\"offset\": 0, \"limit\": 500},
    \"orderBy\": \"updatedAt\"
  }"
# Store the last record's updatedAt as your new watermark
```

For very large datasets (10K+ records), combine pagination with time-based windowing — use `updatedAtLessThanOrEqual` alongside `updatedAtGreaterThanOrEqual` to partition queries into daily or hourly windows.

## 13.5 Paginated Export

```bash
OFFSET=0
LIMIT=100
while true; do
  RESPONSE=$(curl -s -X POST "$KALTURA_USER_PROFILE_URL/user-profile/list" \
    -H "Authorization: Bearer $KALTURA_KS" \
    -H "Content-Type: application/json" \
    -d "{
      \"filter\": {\"appGuidIn\": [\"$APP_GUID\"]},
      \"pager\": {\"offset\": $OFFSET, \"limit\": $LIMIT},
      \"orderBy\": \"createdAt\"
    }")

  COUNT=$(echo "$RESPONSE" | jq '.objects | length')
  echo "Fetched $COUNT profiles (offset=$OFFSET)"

  # Process profiles...

  [ "$COUNT" -lt "$LIMIT" ] && break
  OFFSET=$((OFFSET + LIMIT))
done
```

## 13.6 Re-register After Cancellation

After a user unregisters and their profile is soft-deleted, create a new profile to re-register them:

```bash
# Original profile was deleted (soft-delete)
# Create a fresh profile for the same user + app
curl -X POST "$KALTURA_USER_PROFILE_URL/user-profile/add" \
  -H "Authorization: Bearer $KALTURA_KS" \
  -H "Content-Type: application/json" \
  -d "{
    \"appGuid\": \"$APP_GUID\",
    \"userId\": \"returning-user@example.com\",
    \"profileData\": {\"name\": \"Returning User\"},
    \"eventData\": {
      \"regOrigin\": \"registration\",
      \"attendanceStatus\": \"registered\"
    }
  }"
```


## 13.7 PII Deletion and Cleanup

When deleting event data for compliance (GDPR, data retention), follow this order:

1. **Resolve the event** — Get the `appGuid` from App Registry using `appCustomIdIn: [virtualEventId]`
2. **List user profiles** for the event — `user-profile/list` with `appGuidIn: [appGuid]`
3. **Check multi-event registration** — For each userId, query `user-profile/list` *without* appGuid filter to find profiles in other events. Flag users registered to multiple events.
4. **Delete user profiles** — `user-profile/delete` for each profile in this event
5. **Delete KalturaUsers** — Only delete users from `user.delete` if they have **no profiles in other events**. Flagged users retain their core user record.

User profiles **must** be deleted before deleting the KalturaUser. If you delete the KalturaUser first, re-inviting the same user to a future event will fail because the user profile creation validates the user exists via `user.get`.

```bash
# Delete a profile, then check if the user can be fully deleted
curl -s -X POST "$KALTURA_USER_PROFILE_URL/user-profile/delete" \
  -H "Authorization: Bearer $KALTURA_KS" \
  -H "Content-Type: application/json" \
  -d "{\"id\": \"$PROFILE_ID\"}"

# Check if user has profiles in other events before deleting the core user
OTHER_PROFILES=$(curl -s -X POST "$KALTURA_USER_PROFILE_URL/user-profile/list" \
  -H "Authorization: Bearer $KALTURA_KS" \
  -H "Content-Type: application/json" \
  -d "{
    \"filter\": {\"userIdIn\": [\"$USER_ID\"]},
    \"pager\": {\"offset\": 0, \"limit\": 1},
    \"includeTotalCount\": true
  }" | jq '.totalCount')

if [ "$OTHER_PROFILES" -eq 0 ]; then
  # Safe to delete the core user
  curl -s -X POST "$KALTURA_SERVICE_URL/service/user/action/delete" \
    -d "ks=$KALTURA_KS" -d "format=1" -d "userId=$USER_ID"
fi
```


# 14. Registration Reports (Reports Service)

For CSV-based registration and engagement reports, the platform provides an async Reports Service. This is separate from the User Profile API's `eventDataStats` endpoint and produces downloadable CSV files.

**Reports Base URL:** `https://reports.nvp1.ovp.kaltura.com/api/v1`  
**Auth:** `Authorization: Bearer <KS>`

## 14.1 Generate a Report

```bash
REPORTS_URL="https://reports.nvp1.ovp.kaltura.com/api/v1"

# Request report generation
SESSION_ID=$(curl -s -X POST "$REPORTS_URL/report/generate" \
  -H "Authorization: Bearer $KALTURA_KS" \
  -H "Content-Type: application/json" \
  -d "{
    \"reportParameters\": {\"appGuid\": \"$APP_GUID\"},
    \"reportName\": \"registration\"
  }" | jq -r '.sessionId')
```

## 14.2 Poll and Download

The generate call returns a `sessionId`. Poll the serve endpoint until the report is ready:

```bash
# Poll until ready (statusOnly: true returns status without CSV)
while true; do
  STATUS=$(curl -s -X POST "$REPORTS_URL/report/serve" \
    -H "Authorization: Bearer $KALTURA_KS" \
    -H "Content-Type: application/json" \
    -d "{\"sessionId\": \"$SESSION_ID\", \"statusOnly\": true}" \
    | jq -r '.status')

  [ "$STATUS" = "completed" ] && break
  sleep 2
done

# Download the CSV
curl -s -X POST "$REPORTS_URL/report/serve" \
  -H "Authorization: Bearer $KALTURA_KS" \
  -H "Content-Type: application/json" \
  -d "{\"sessionId\": \"$SESSION_ID\", \"statusOnly\": false}"
```

Reports may reflect cached data with a freshness window of 10-15 minutes. For real-time attendance status, use the User Profile `list` endpoint directly.

## 14.3 Engagement Reports (API v3)

Per-user session engagement data is available via the core Kaltura Reports API using specific report IDs:

| Report ID | Purpose | Key Fields |
|-----------|---------|------------|
| 3030 | Live/VOD engagement summary | user_id, email, plays, sum_minutes_viewed, live_engagement_rate |
| 3035 | Device/OS breakdown | device_used, os_used, view_time, total_completion_rate |
| 3037 | Per-user session detail | date, user_id, entry_id, entry_name, sum_minutes_viewed |
| 6000 | Meeting Room session reports | entry_id, entry_name, session_start_time, session_end_time |
| 6001 | Meeting Room attendee reports | entry_id, user_id, user_name, user_type, meeting_view_time |

```bash
# Get per-user session engagement for a virtual event
curl -s -X POST "$KALTURA_SERVICE_URL/service/report/action/getCsvFromStringParams" \
  -d "ks=$KALTURA_KS" \
  -d "format=1" \
  -d "id=3037" \
  -d "params=from_date=$FROM_UNIX;to_date=$TO_UNIX;virtual_event_ids=$VIRTUAL_EVENT_ID"
```


# 15. Best Practices

- **Use `bulkAdd` for batch registration.** Up to 50 profiles per request — significantly faster than individual calls for event registration imports.
- **Resolve virtual event ID → appGuid via App Registry first.** Use `appCustomIdIn` filter to map event IDs to app GUIDs before managing profiles (see [App Registry API](KALTURA_APP_REGISTRY_API.md)).
- **Use status transitions to track attendance lifecycle.** Progress users through `created → registered → confirmed → attended → participated` for accurate reporting.
- **Use `getFiltered` for reporting and analytics.** Filter by status, date range, and fields to build attendance dashboards without downloading all profiles.
- **Use AppTokens for production access.** Generate KS via `appToken.startSession` with HMAC — keep admin secrets off application servers.

# 16. Related Guides

- **[App Registry API](KALTURA_APP_REGISTRY_API.md)** — Register and manage application instances (prerequisite for user profiles)
- **[Session Guide](KALTURA_SESSION_GUIDE.md)** — KS generation and management
- **[AppTokens API](KALTURA_APPTOKENS_API.md)** — Secure server-to-server auth
- **[Events Platform API](KALTURA_EVENTS_PLATFORM_API.md)** — Virtual events (complementary to user profile management)
- **[Messaging API](KALTURA_MESSAGING_API.md)** — Template-based email messaging (triggered by user profile events)
- **[Webhooks API](KALTURA_WEBHOOKS_API.md)** — Event-driven HTTP callbacks for user and content events
- **[eSearch API](KALTURA_ESEARCH_API.md)** — Search entries and users across your account
- **[User Management API](KALTURA_USER_MANAGEMENT_API.md)** — Core user CRUD, roles, and groups (the account-level user records that User Profile extends per-app)
- **[Analytics Reports](KALTURA_ANALYTICS_REPORTS_API.md)** — `reports/eventDataStats` for attendance analytics
- **[Gamification](KALTURA_GAMIFICATION_API.md)** — User profiles drive gamification scoring

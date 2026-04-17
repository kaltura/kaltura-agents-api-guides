# Kaltura Virtual Events Platform API

The Virtual Events Platform has a dedicated modern REST API (OAS 3.0) for creating and managing virtual events — town halls, webinars, conferences, and training sessions. This is separate from the main Kaltura API v3 and uses a different base URL with JSON request bodies.

**Base URL:** `https://events-api.nvp1.ovp.kaltura.com/api/v1` (production NVP region)  
**Auth:** `Authorization: Bearer <KS>` header (standard Kaltura Session)  
**Format:** JSON request/response bodies, all endpoints use POST  
**Regions:** NVP (default), EU (`irp2`), DE (`frp2`)  


# 1. When to Use

- **Event producers** creating and managing virtual town halls, webinars, and hybrid conferences programmatically  
- **Enterprise communications teams** scheduling recurring all-hands meetings with session tracks and speaker management  
- **Training organizations** building event-driven learning experiences with registration and attendance tracking  
- **Integration developers** connecting Kaltura events with external calendars, CRM systems, or marketing automation  
- **Conference platforms** orchestrating multi-session events with templates, team member roles, and event duplication


# 2. Prerequisites

- **KS type:** ADMIN KS (type=2) with a `userId` set (required by the Events Platform API)  
- **Plugins:** Virtual Events Platform must be enabled on the partner account  
- **Session guide:** Generate a KS using `session.start` or `appToken.startSession` (see [Session Guide](KALTURA_SESSION_GUIDE.md))


# 3. Authentication

All requests require a valid KS in the `Authorization` header:

```
Authorization: Bearer <your_kaltura_session>
```

**The KS must have a `userId` set.** Generate a KS with `userId` via `session.start` (see [Session Guide](KALTURA_SESSION_GUIDE.md)) or `appToken.startSession` (see [AppTokens Guide](KALTURA_APPTOKENS_API.md)).

For production, use `appToken.startSession` with a `userId` privilege.

See [Session Guide](KALTURA_SESSION_GUIDE.md) for full details on KS generation.


# 4. Regional Endpoints

| Region | Base URL |
|--------|----------|
| NVP (default) | `https://events-api.nvp1.ovp.kaltura.com/api/v1` |
| EU | `https://events-api.irp2.ovp.kaltura.com/api/v1` |
| DE | `https://events-api.frp2.ovp.kaltura.com/api/v1` |

Use the region that matches your Kaltura account deployment.


# 5. Events API

## 5.1 Create an Event

```
POST /api/v1/events/create
Content-Type: application/json
Authorization: Bearer <KS>
```

```json
{
  "name": "Q4 All-Hands Town Hall",
  "templateId": "tm2000",
  "startDate": "2024-12-15T14:00:00.000Z",
  "endDate": "2024-12-15T16:00:00.000Z",
  "timezone": "America/New_York",
  "description": "Quarterly company update and Q&A"
}
```

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `name` | string | Yes | Event display name |
| `templateId` | string | Yes | Template to use (see section 8) |
| `startDate` | string | Yes | ISO 8601 start date |
| `endDate` | string | Yes | ISO 8601 end date |
| `timezone` | string | Yes | IANA timezone (e.g., `America/New_York`, `Europe/London`) |
| `description` | string | No | Event description |

Set `doorsOpenDate` via `events/update` after the event is created.

**Resilience:** If `events/create` returns HTTP 500, the event may still have been created server-side. Verify by calling `events/list` with a `searchTerm` matching your event name.

**Response example:**

```json
{
  "id": 56789,
  "name": "API Demo Webinar",
  "status": "draft",
  "templateId": "tm2000",
  "startDate": "2024-12-20T15:00:00.000Z",
  "endDate": "2024-12-20T16:00:00.000Z",
  "timezone": "America/New_York",
  "description": "Created via Events Platform API",
  "labels": [],
  "createdAt": "2024-11-01T10:00:00.000Z",
  "updatedAt": "2024-11-01T10:00:00.000Z"
}
```

The response contains the full event object. Save the `id` field (integer) for subsequent API calls.

```bash
curl -X POST "$KALTURA_EVENTS_API_URL/events/create" \
  -H "Authorization: Bearer $KALTURA_KS" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "API Demo Webinar",
    "templateId": "tm2000",
    "startDate": "2024-12-20T15:00:00.000Z",
    "endDate": "2024-12-20T16:00:00.000Z",
    "timezone": "America/New_York",
    "description": "Created via Events Platform API"
  }'
```

Save the `id` from the response as `EVENT_ID`.

## 5.2 List Events

```
POST /api/v1/events/list
```

```json
{
  "filter": {
    "searchTerm": "town hall",
    "labels": ["quarterly"],
    "idIn": [12345, 67890]
  },
  "pager": {
    "offset": 0,
    "limit": 15
  },
  "orderBy": "-startDate"
}
```

| Filter Field | Type | Description |
|-------------|------|-------------|
| `searchTerm` | string | Free-text search across name and description |
| `labels` | array | Filter by label tags |
| `idIn` | array | Filter by specific event IDs |

| Pager Field | Type | Description |
|-------------|------|-------------|
| `offset` | int | Number of results to skip |
| `limit` | int | Max results to return (max 15) |

| `orderBy` | Description |
|-----------|-------------|
| `+startDate` | Ascending by start date |
| `-startDate` | Descending by start date (newest first) |
| `+createdAt` | Ascending by creation date |
| `-createdAt` | Descending by creation date |
| `+name` | Alphabetical |
| `-name` | Reverse alphabetical |

**Response example:**

```json
{
  "events": [
    {
      "id": 56789,
      "name": "Q4 All-Hands Town Hall",
      "status": "scheduled",
      "startDate": "2024-12-15T14:00:00.000Z",
      "endDate": "2024-12-15T16:00:00.000Z",
      "timezone": "America/New_York",
      "labels": ["quarterly"]
    }
  ],
  "totalCount": 1
}
```

```bash
curl -X POST "$KALTURA_EVENTS_API_URL/events/list" \
  -H "Authorization: Bearer $KALTURA_KS" \
  -H "Content-Type: application/json" \
  -d '{
    "filter": {},
    "pager": {"offset": 0, "limit": 10},
    "orderBy": "-startDate"
  }'
```

The response contains an `events` array and `totalCount`.

## 5.3 Update an Event

```
POST /api/v1/events/update
```

```json
{
  "id": 12345,
  "name": "Updated Event Name",
  "description": "Updated description",
  "startDate": "2024-12-15T15:00:00.000Z",
  "endDate": "2024-12-15T17:00:00.000Z",
  "doorsOpenDate": "2024-12-15T14:45:00.000Z",
  "timezone": "America/New_York",
  "labels": ["updated", "quarterly"],
  "logoEntryId": "0_abc123",
  "bannerEntryId": "0_def456"
}
```

| Field | Type | Description |
|-------|------|-------------|
| `id` | integer | **Required.** Event ID to update |
| `name` | string | Updated name |
| `description` | string | Updated description |
| `startDate` | string | Updated start date |
| `endDate` | string | Updated end date |
| `doorsOpenDate` | string | Updated doors-open time |
| `timezone` | string | Updated timezone |
| `labels` | array | Updated labels/tags |
| `logoEntryId` | string | Kaltura entry ID for event logo image |
| `bannerEntryId` | string | Kaltura entry ID for event banner image |

Only include the fields you want to change. Fields not included remain unchanged.

**Response:** The updated event object.

```bash
curl -X POST "$KALTURA_EVENTS_API_URL/events/update" \
  -H "Authorization: Bearer $KALTURA_KS" \
  -H "Content-Type: application/json" \
  -d "{
    \"id\": $EVENT_ID,
    \"name\": \"Updated Event Name\",
    \"labels\": [\"updated\", \"quarterly\"]
  }"
```

## 5.4 Delete an Event

```
POST /api/v1/events/delete
```

```json
{
  "id": 12345
}
```

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `id` | integer | Yes | Event ID to delete |

Permanently deletes the event and all its sessions. Returns an empty response on success (HTTP 200).

**Category cleanup:** The Events Platform auto-creates root categories for each event (e.g., `{eventId}EP{hex}`, `ep_agenda_{eventId}`, `ep_private_{eventId}`). Deleting an event removes the event record and its sessions, but does **not** cascade-delete these categories. Clean them up separately via `category.delete` using the category IDs, or list root categories filtered by the event ID pattern.

```bash
curl -X POST "$KALTURA_EVENTS_API_URL/events/delete" \
  -H "Authorization: Bearer $KALTURA_KS" \
  -H "Content-Type: application/json" \
  -d "{\"id\": $EVENT_ID}"
```

## 5.5 Duplicate an Event

```
POST /api/v1/events/duplicate
```

```json
{
  "sourceEventId": 12345
}
```

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `sourceEventId` | integer | Yes | The numeric ID of the event to duplicate |

Creates a copy of the event with all its configuration. Returns a job object with a `jobId`.

**Response:**
```json
{
  "jobId": "job_xyz789"
}
```

## 5.6 Check Duplication Status

```
POST /api/v1/events/duplicateStatus
```

```json
{
  "jobId": "job_xyz789"
}
```

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `jobId` | string | Yes | Job ID returned by `events/duplicate` |

**Response:** Contains `status` (see table below) and, on completion, `eventId` with the new event's integer ID.

| Status | Description |
|--------|-------------|
| `completed` | Duplication finished successfully |
| `failed` | Duplication failed |
| `paused` | Job paused |
| `repeat` | Job being retried |
| `wait` | Job queued, waiting to start |
| `unknown` | Status cannot be determined |

```bash
# Start duplication
curl -X POST "$KALTURA_EVENTS_API_URL/events/duplicate" \
  -H "Authorization: Bearer $KALTURA_KS" \
  -H "Content-Type: application/json" \
  -d '{"sourceEventId": 12345}'
# Save the "jobId" from the response as JOB_ID

# Poll for completion
curl -X POST "$KALTURA_EVENTS_API_URL/events/duplicateStatus" \
  -H "Authorization: Bearer $KALTURA_KS" \
  -H "Content-Type: application/json" \
  -d "{\"jobId\": \"$JOB_ID\"}"
# Repeat until "status" is "completed" or "failed"
```


# 6. Sessions API

Sessions are the individual rooms/streams within an event. Each event can have multiple sessions of different types.

## 6.1 Session Types

| Type | Description |
|------|-------------|
| `MeetingEntry` | Interactive room — bidirectional audio/video for all participants |
| `LiveWebcast` | Live webcast — presenter streams to viewers, chat/Q&A for interaction |
| `SimuLive` | Simulive — pre-recorded VOD played as a live stream on schedule |
| `LiveKME` | DIY live — bring your own encoder (RTMP/SRT ingest) |
| `VirtualLearningRoom` | Virtual classroom with interactive learning tools |

## 6.2 Create a Session

```
POST /api/v1/sessions/create
```

**Important:** Session fields must be nested inside a `session` object. The `eventId` is at the top level.

```json
{
  "eventId": 12345,
  "session": {
    "name": "Keynote Presentation",
    "type": "LiveWebcast",
    "startDate": "2024-12-15T14:00:00.000Z",
    "endDate": "2024-12-15T15:00:00.000Z",
    "description": "Opening keynote by CEO",
    "visibility": "published"
  }
}
```

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `eventId` | integer | Yes | Parent event ID (top level) |
| `session.name` | string | Yes | Session name |
| `session.type` | string | Yes | Session type (see table above) |
| `session.startDate` | string | Yes | ISO 8601 start date |
| `session.endDate` | string | Yes | ISO 8601 end date |
| `session.description` | string | No | Session description |
| `session.visibility` | string | No | `published` (default), `unlisted`, or `private` |
| `session.sourceEntryId` | string | No | VOD entry ID for SimuLive sessions |

**Response example:**

```json
{
  "session": {
    "id": 67890,
    "name": "Keynote Presentation",
    "type": "LiveWebcast",
    "startDate": "2024-12-15T14:00:00.000Z",
    "endDate": "2024-12-15T15:00:00.000Z",
    "description": "Opening keynote by CEO",
    "visibility": "published"
  },
  "status": "ok"
}
```

The session object is nested inside the `session` key. Save `session.id` for subsequent calls.

**SimuLive example** (pre-recorded content played as live):
```json
{
  "eventId": 12345,
  "session": {
    "name": "Pre-recorded Demo",
    "type": "SimuLive",
    "startDate": "2024-12-15T15:00:00.000Z",
    "endDate": "2024-12-15T15:30:00.000Z",
    "sourceEntryId": "0_prerecorded123"
  }
}
```

```bash
curl -X POST "$KALTURA_EVENTS_API_URL/sessions/create" \
  -H "Authorization: Bearer $KALTURA_KS" \
  -H "Content-Type: application/json" \
  -d '{
    "eventId": 12345,
    "session": {
      "name": "Main Webcast",
      "type": "LiveWebcast",
      "startDate": "2024-12-20T15:00:00.000Z",
      "endDate": "2024-12-20T16:00:00.000Z",
      "description": "Main presentation",
      "visibility": "published"
    }
  }'
```

The response contains a `session` object with `id`, `name`, `type`, and other fields.

## 6.3 List Sessions for an Event

```
POST /api/v1/sessions/list
```

```json
{
  "eventId": 12345
}
```

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `eventId` | integer | Yes | Parent event ID |

Returns all sessions belonging to the event. Response uses the `sessions` key.

**Response example:**

```json
{
  "sessions": [
    {
      "id": 67890,
      "name": "Keynote Presentation",
      "type": "LiveWebcast",
      "startDate": "2024-12-15T14:00:00.000Z",
      "endDate": "2024-12-15T15:00:00.000Z",
      "visibility": "published"
    }
  ]
}
```

```bash
curl -X POST "$KALTURA_EVENTS_API_URL/sessions/list" \
  -H "Authorization: Bearer $KALTURA_KS" \
  -H "Content-Type: application/json" \
  -d '{"eventId": 12345}'
```

The response contains a `sessions` array with each session's `id`, `name`, `type`, and `visibility`.

## 6.4 List Speakers for a Session

```
POST /api/v1/sessions/speakerList
```

```json
{
  "eventId": 12345,
  "sessionId": 67890
}
```

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `eventId` | integer | Yes | Parent event ID |
| `sessionId` | integer | Yes | Session ID to list speakers for |

Returns the list of speakers assigned to the session.


# 7. Team Members API

Manage team members (organizers, admins, content managers) for events. Team members are managed at the account level — no `eventId` is needed for create or list.

**Roles:**

| Role | Description |
|------|-------------|
| `Admin` | Full administrative access |
| `Organizer` | Can manage event content and sessions |
| `ContentManager` | Can manage content within events |

## 7.1 Add a Team Member

```
POST /api/v1/team-members/create
```

```json
{
  "email": "user@example.com",
  "role": "Organizer",
  "firstName": "Jane",
  "lastName": "Doe"
}
```

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `email` | string | Yes | Team member's email address |
| `role` | string | Yes | One of: `Admin`, `Organizer`, `ContentManager` |
| `firstName` | string | Yes | First name |
| `lastName` | string | Yes | Last name |

## 7.2 List Team Members

```
POST /api/v1/team-members/list
```

```json
{}
```

No parameters required. Returns all team members for the account.

**Response example:**

```json
{
  "teamMembers": [
    {
      "id": "abc123",
      "email": "user@example.com",
      "role": "Organizer",
      "firstName": "Jane",
      "lastName": "Doe"
    }
  ]
}
```

## 7.3 Update a Team Member

```
POST /api/v1/team-members/update
```

```json
{
  "teamMemberId": "abc123",
  "role": "Admin"
}
```

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `teamMemberId` | string | Yes | Team member ID to update |
| `role` | string | No | Updated role: `Admin`, `Organizer`, or `ContentManager` |
| `firstName` | string | No | Updated first name |
| `lastName` | string | No | Updated last name |

Only include the fields you want to change. Returns the updated team member object.

## 7.4 Delete a Team Member

```
POST /api/v1/team-members/delete
```

```json
{
  "teamMemberId": "abc123"
}
```

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `teamMemberId` | string | Yes | Team member ID to delete |

Permanently removes the team member from the account. Returns an empty response on success (HTTP 200).


# 8. Event Templates

Templates pre-configure events with specific session types and settings.

| Template ID | Description | Included Session |
|-------------|-------------|-----------------|
| `tm0000` | Blank event | No sessions |
| `tm1000` | Interactive room | MeetingEntry |
| `tm2000` | Live webcast | LiveWebcast |
| `tm3000` | Simulive | SimuLive |
| `tm4000` | Room broadcasting to webcast | MeetingEntry + LiveWebcast |


# 9. Event Status Values

| Status | Description |
|--------|-------------|
| `draft` | Event created but not published |
| `scheduled` | Event published and upcoming |
| `live` | Event currently in progress |
| `ended` | Event has concluded |
| `cancelled` | Event was cancelled |


# 10. Complete Example — Event Lifecycle

Generate a KS with `userId` via `session.start` (see [Session Guide](KALTURA_SESSION_GUIDE.md)) and set the shell variables:

```bash
# Prerequisites: set these shell variables before running the commands below
# KALTURA_EVENTS_API_URL="https://events-api.nvp1.ovp.kaltura.com/api/v1"
# KALTURA_KS="<your KS with userId>"
```

```bash
# --- Step 1: Create an event ---
curl -X POST "$KALTURA_EVENTS_API_URL/events/create" \
  -H "Authorization: Bearer $KALTURA_KS" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "API Demo Event",
    "templateId": "tm0000",
    "startDate": "2024-12-22T15:00:00.000Z",
    "endDate": "2024-12-22T17:00:00.000Z",
    "timezone": "America/New_York",
    "description": "Created via Events Platform API"
  }'
# Save the "id" from the response as EVENT_ID

# --- Step 2: Add a live webcast session ---
curl -X POST "$KALTURA_EVENTS_API_URL/sessions/create" \
  -H "Authorization: Bearer $KALTURA_KS" \
  -H "Content-Type: application/json" \
  -d "{
    \"eventId\": $EVENT_ID,
    \"session\": {
      \"name\": \"Main Stage\",
      \"type\": \"LiveWebcast\",
      \"startDate\": \"2024-12-22T15:00:00.000Z\",
      \"endDate\": \"2024-12-22T17:00:00.000Z\",
      \"visibility\": \"published\"
    }
  }"

# --- Step 3: List all events ---
curl -X POST "$KALTURA_EVENTS_API_URL/events/list" \
  -H "Authorization: Bearer $KALTURA_KS" \
  -H "Content-Type: application/json" \
  -d '{
    "filter": {},
    "pager": {"offset": 0, "limit": 5},
    "orderBy": "-startDate"
  }'

# --- Step 4: Update the event ---
curl -X POST "$KALTURA_EVENTS_API_URL/events/update" \
  -H "Authorization: Bearer $KALTURA_KS" \
  -H "Content-Type: application/json" \
  -d "{
    \"id\": $EVENT_ID,
    \"name\": \"Updated API Demo Event\",
    \"labels\": [\"demo\", \"api-test\"]
  }"

# --- Step 5: Delete the event ---
curl -X POST "$KALTURA_EVENTS_API_URL/events/delete" \
  -H "Authorization: Bearer $KALTURA_KS" \
  -H "Content-Type: application/json" \
  -d "{\"id\": $EVENT_ID}"
```


# 11. Error Handling

| HTTP Status / Error | Meaning | Resolution |
|---------------------|---------|------------|
| `401 Unauthorized` | Invalid or expired KS | Generate a fresh KS with `userId` set — Events Platform requires it |
| `403 Forbidden` | KS lacks required permissions | Use an admin KS (type=2) with the user's `userId` |
| `404 Not Found` | Event, session, or team member ID does not exist | Verify the integer ID; resource may have been deleted |
| `400 Bad Request` | Missing required field or invalid date format | Dates must be ISO 8601 format (e.g., `2025-06-15T09:00:00.000Z`). Event IDs are integers. |
| Duplication job stuck | `duplicateStatus` returns `IN_PROGRESS` indefinitely | Poll with timeout (5 minutes recommended); if stuck, create the event manually |

**Retry strategy:** For transient errors (HTTP 5xx, timeouts), retry with exponential backoff: 1s, 2s, 4s, with jitter, up to 3 retries. For client errors (`401 Unauthorized`, `403 Forbidden`, `400 Bad Request`), fix the request before retrying — these will not resolve on their own. For async operations (event duplication), poll with increasing intervals (5s, 10s, 30s) rather than tight loops.

# 12. Best Practices

- **Use templates for consistent events.** Clone from preset templates (`tm1000` for interactive room, `tm2000` for live webcast, `tm3000` for simulive) to inherit default session configuration.
- **Set `doorsOpenDate`** before `startDate` to allow early attendee access (e.g., 15 minutes before start).
- **Use User Profile API for attendee management.** Registration, attendance tracking, and engagement analytics are handled by the User Profile service, not the Events Platform directly.
- **Use Messaging API for event communications.** Send invitations, reminders, and follow-ups through the template-based Messaging service rather than building custom email logic.
- **Use the correct regional endpoint.** Events are region-specific: NVP1 (US), IRP2 (EU), FRP2 (DE). Use the endpoint matching your account's region.
- **Use AppTokens for production integrations.** Create a scoped AppToken for event management automation.
- **Set up webhooks for event lifecycle.** Use the Webhooks API to receive callbacks when sessions start/end, recordings become available, or attendee status changes.

# 13. Related Guides

- **[Session Guide](KALTURA_SESSION_GUIDE.md)** — Generate the KS needed for Bearer auth (must include `userId`)
- **[AppTokens Guide](KALTURA_APPTOKENS_API.md)** — Secure token-based auth for integrations
- **[Upload & Delivery Guide](KALTURA_UPLOAD_AND_DELIVERY_API.md)** — Upload logo/banner assets for events
- **[Player Embed Guide](KALTURA_PLAYER_EMBED_GUIDE.md)** — Embed event recordings
- **[REACH Guide](KALTURA_REACH_API.md)** — Enrichment services: auto-caption, translate, and enrich event session recordings
- **[Agents Manager](KALTURA_AGENTS_MANAGER_API.md)** — Auto-process event content with triggers and actions
- **[AI Genie](KALTURA_AI_GENIE_API.md)** — Conversational AI search over event content
- **[App Registry API](KALTURA_APP_REGISTRY_API.md)** — Application instance registry (events auto-register apps)
- **[User Profile API](KALTURA_USER_PROFILE_API.md)** — Per-event attendee profiles and attendance tracking
- **[Messaging API](KALTURA_MESSAGING_API.md)** — Email invitations, reminders, and follow-ups for event attendees
- **[Webhooks API](KALTURA_WEBHOOKS_API.md)** — HTTP callbacks for event-related content changes (entry ready, metadata changed)  
- **[Chat & Collaborate](KALTURA_CNC_API.md)** — Real-time chat, Q&A, and polls embedded in event sessions  
- **[Embeddable Analytics](KALTURA_ANALYTICS_EMBED_API.md)** — Event analytics dashboards via iframe embed

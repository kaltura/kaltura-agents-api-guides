# Kaltura App Registry API

The App Registry is a centralized service for registering and managing Kaltura application instances — KMS sites, Events Platform instances, custom applications, and more. Each registered app gets a unique GUID (`id`) used by other platform services (such as the [User Profile API](KALTURA_USER_PROFILE_API.md)) to associate data with specific application contexts.

When you create a virtual event through the Events Platform, an app is automatically registered with `appType: "epmEvent"`. You can also register apps directly for custom integrations.

**Base URL:** `https://app-registry.nvp1.ovp.kaltura.com/api/v1` (production NVP region)  
**Auth:** `Authorization: Bearer <KS>` header (ADMIN KS, type=2, requires `ADMIN_BASE` permission)  
**Format:** JSON request/response bodies, all endpoints use POST  
**Regions:** NVP (default `nvp1`), EU (`irp2`), DE (`frp2`)  

<!-- Sections: 1.When to Use | 2.Prerequisites | 3.Authentication | 4.App Entity | 5.Register an App | 6.Get an App | 7.Update an App | 8.Delete an App | 9.Enable / Disable an App | 10.List Apps | 11.Find Apps by Organization Domain | 12.Versioning | 13.Error Handling | 14.Best Practices | 15.Related Guides -->


# 1. When to Use

- **Partner application management** — Platform administrators registering and tracking all application instances (KMS sites, Events Platform portals, custom integrations) across the organization  
- **SSO and domain-based routing** — Developers configuring organization domain bindings so users are automatically directed to the correct application instance based on their email domain  
- **Developer app lifecycle** — Development teams registering custom application instances, enabling/disabling them across environments, and syncing app metadata with external systems  
- **Cross-service context linking** — Backend systems resolving virtual event IDs to app GUIDs for use with the User Profile API, Messaging API, and other services that associate data with specific application contexts  


# 2. Prerequisites

- An ADMIN KS (type=2) with `ADMIN_BASE` permission for all write operations, or `ANALYTICS_BASE` for read-only list access (see [Session Guide](KALTURA_SESSION_GUIDE.md))  
- A Kaltura account with App Registry access enabled  
- For production integrations, use AppTokens for secure KS generation (see [AppTokens API](KALTURA_APPTOKENS_API.md))  


# 3. Authentication

All requests require an ADMIN KS (type=2) with `ADMIN_BASE` permission in the `Authorization` header:

```
Authorization: Bearer <your_kaltura_session>
```

The `list` endpoint also accepts KS with `ANALYTICS_BASE` permission.

Generate an ADMIN KS via `session.start` (see [Session Guide](KALTURA_SESSION_GUIDE.md)) or `appToken.startSession` (see [AppTokens Guide](KALTURA_APPTOKENS_API.md)).

```bash
# Set up environment
export KALTURA_APP_REGISTRY_URL="https://app-registry.nvp1.ovp.kaltura.com/api/v1"
```


# 4. App Entity

Every registered application has this structure:

| Field | Type | Description |
|-------|------|-------------|
| `id` | string | Auto-generated GUID (read-only) |
| `partnerId` | integer | Partner ID extracted from KS (read-only) |
| `appCustomId` | string | Your custom identifier for this app instance |
| `appCustomName` | string | Display name for the app instance |
| `appType` | string | Application type (see enum below) |
| `status` | string | `enabled` or `disabled` |
| `version` | integer | Starts at 0, increments on each update (read-only) |
| `createdAt` | string | ISO 8601 timestamp, e.g. `"2026-04-09T04:56:27.940Z"` (read-only) |
| `updatedAt` | string | ISO 8601 timestamp, e.g. `"2026-04-09T04:56:27.940Z"` (read-only) |
| `organizationDomain` | object | Optional organization/domain binding |
| `objectType` | string | Always `"App"` in responses (read-only) |

## 4.1 App Types

| Value | Description |
|-------|-------------|
| `kms` | Kaltura MediaSpace (KMS) |
| `kmc` | Kaltura Management Console |
| `ep` | Events Platform |
| `sites` | Kaltura Sites |
| `pitch` | Kaltura Pitch |
| `test` | Test application |
| `games` | Kaltura Games |
| `empAccount` | Employee account |
| `epmEvent` | Events Platform Manager — Event (auto-created when a virtual event is created) |
| `epmSystem` | Events Platform Manager — System |
| `mr` | Meeting Room |
| `kalturaServer` | Kaltura Server |

## 4.2 Organization Domain

Optional object for binding an app instance to a specific domain and organization:

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `organizationId` | string | No | Organization identifier (max 255 chars) |
| `domain` | string | Yes | Domain name (max 255 chars, comma-separated for multiple). Whitespace is automatically stripped. |


# 5. Register an App

```
POST /api/v1/app-registry/add
Content-Type: application/json
Authorization: Bearer <KS>
```

```json
{
  "appCustomId": "my-events-site-01",
  "appType": "ep",
  "appCustomName": "Annual Conference Portal"
}
```

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `appCustomId` | string | Yes | Custom identifier (unique per partner) |
| `appType` | string | Yes | Application type (see section 4.1) |
| `appCustomName` | string | Yes | Display name |
| `organizationDomain` | object | No | Domain binding (see section 4.2) |

The `status` is always set to `"enabled"` on creation (cannot be overridden). The `version` starts at `0`. The `partnerId` is extracted from the KS — it cannot be set in the request body.

**Response:** Full app object with generated `id`.

```json
{
  "id": "6f8a3c12-4b5d-4e9f-a1c7-8d2e3f4a5b6c",
  "partnerId": 1234567,
  "appCustomId": "my-events-site-01",
  "appCustomName": "Annual Conference Portal",
  "appType": "ep",
  "status": "enabled",
  "version": 0,
  "createdAt": "2026-04-09T04:56:27.940Z",
  "updatedAt": "2026-04-09T04:56:27.940Z",
  "objectType": "App"
}
```

```bash
curl -X POST "$KALTURA_APP_REGISTRY_URL/app-registry/add" \
  -H "Authorization: Bearer $KALTURA_KS" \
  -H "Content-Type: application/json" \
  -d '{
    "appCustomId": "my-events-site-01",
    "appType": "ep",
    "appCustomName": "Annual Conference Portal"
  }'
```

Save the `id` from the response — this is the `appGuid` used by other services like the [User Profile API](KALTURA_USER_PROFILE_API.md).

### Uniqueness Constraints

- `appCustomId` must be unique within your partner account
- If `organizationDomain` is provided, the combination of `organizationId` + `domain` + `appType` must be globally unique. Each comma-separated domain in the `domain` field is validated individually.

### Error Codes

| Code | Meaning |
|------|---------|
| `APP_REGISTRY_ALREADY_EXISTS_WITH_THIS_APP_CUSTOM_ID` | Duplicate `appCustomId` for your partner |
| `ORGANIZATION_ID_DOMAIN_AND_APP_TYPE_MUST_BE_UNIQUE` | Domain/org/type combination already exists |


# 6. Get an App

```
POST /api/v1/app-registry/get
Content-Type: application/json
Authorization: Bearer <KS>
```

```json
{
  "id": "app-guid-here"
}
```

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `id` | string | Yes | App GUID to retrieve |

**Response:** Full app object.

```json
{
  "id": "6f8a3c12-4b5d-4e9f-a1c7-8d2e3f4a5b6c",
  "partnerId": 1234567,
  "appCustomId": "my-events-site-01",
  "appCustomName": "Annual Conference Portal",
  "appType": "ep",
  "status": "enabled",
  "version": 0,
  "createdAt": "2026-04-09T04:56:27.940Z",
  "updatedAt": "2026-04-09T04:56:27.940Z",
  "objectType": "App"
}
```

```bash
curl -X POST "$KALTURA_APP_REGISTRY_URL/app-registry/get" \
  -H "Authorization: Bearer $KALTURA_KS" \
  -H "Content-Type: application/json" \
  -d "{\"id\": \"$APP_GUID\"}"
```

Returns `OBJECT_NOT_FOUND` if the app does not exist or belongs to a different partner.


# 7. Update an App

```
POST /api/v1/app-registry/update
Content-Type: application/json
Authorization: Bearer <KS>
```

```json
{
  "id": "app-guid-here",
  "appCustomName": "Updated Conference Portal"
}
```

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `id` | string | Yes | App GUID to update |
| `appCustomId` | string | No | Updated custom identifier |
| `appCustomName` | string | No | Updated display name |
| `appType` | string | No | Updated app type |
| `organizationDomain` | object | No | Updated domain binding |

Fields not included in the request body (or set to `null`) remain unchanged. The `partnerId`, `status`, `version`, `createdAt`, and `updatedAt` fields cannot be set — `status` is managed via enable/disable, `version` auto-increments.

**Response:** Full app object with `version` incremented by 1 and `updatedAt` refreshed.

```json
{
  "id": "6f8a3c12-4b5d-4e9f-a1c7-8d2e3f4a5b6c",
  "partnerId": 1234567,
  "appCustomId": "my-events-site-01",
  "appCustomName": "Updated Conference Portal",
  "appType": "ep",
  "status": "enabled",
  "version": 1,
  "createdAt": "2026-04-09T04:56:27.940Z",
  "updatedAt": "2026-04-09T05:12:44.310Z",
  "objectType": "App"
}
```

```bash
curl -X POST "$KALTURA_APP_REGISTRY_URL/app-registry/update" \
  -H "Authorization: Bearer $KALTURA_KS" \
  -H "Content-Type: application/json" \
  -d "{
    \"id\": \"$APP_GUID\",
    \"appCustomName\": \"Updated Conference Portal\"
  }"
```


# 8. Delete an App

Permanently removes the app registration.

```
POST /api/v1/app-registry/delete
Content-Type: application/json
Authorization: Bearer <KS>
```

```json
{
  "id": "app-guid-here"
}
```

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `id` | string | Yes | App GUID to delete |

**Response:** Empty body on success (HTTP 200). Returns `OBJECT_NOT_FOUND` if the app does not exist for your partner.

```bash
curl -X POST "$KALTURA_APP_REGISTRY_URL/app-registry/delete" \
  -H "Authorization: Bearer $KALTURA_KS" \
  -H "Content-Type: application/json" \
  -d "{\"id\": \"$APP_GUID\"}"
```


# 9. Enable / Disable an App

Toggle an app's status without deleting it. Disabled apps remain in the registry but are excluded from `list` results when filtering by `status: "enabled"`.

## 9.1 Enable

```bash
curl -X POST "$KALTURA_APP_REGISTRY_URL/app-registry/enable" \
  -H "Authorization: Bearer $KALTURA_KS" \
  -H "Content-Type: application/json" \
  -d "{\"id\": \"$APP_GUID\"}"
```

## 9.2 Disable

```bash
curl -X POST "$KALTURA_APP_REGISTRY_URL/app-registry/disable" \
  -H "Authorization: Bearer $KALTURA_KS" \
  -H "Content-Type: application/json" \
  -d "{\"id\": \"$APP_GUID\"}"
```

Both endpoints accept a single parameter:

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `id` | string | Yes | App GUID to enable or disable |

**Response:** Full app object with updated status.

```json
{
  "id": "6f8a3c12-4b5d-4e9f-a1c7-8d2e3f4a5b6c",
  "partnerId": 1234567,
  "appCustomId": "my-events-site-01",
  "appCustomName": "Annual Conference Portal",
  "appType": "ep",
  "status": "disabled",
  "version": 2,
  "createdAt": "2026-04-09T04:56:27.940Z",
  "updatedAt": "2026-04-09T05:30:12.880Z",
  "objectType": "App"
}
```

The `version` increments only if the status actually changed. Enabling an already-enabled app (or disabling an already-disabled one) returns the current state without incrementing `version`.


# 10. List Apps

```
POST /api/v1/app-registry/list
Content-Type: application/json
Authorization: Bearer <KS>
```

```json
{
  "filter": {
    "appType": "ep",
    "status": "enabled"
  },
  "pager": {
    "offset": 0,
    "limit": 25
  }
}
```

All filter fields are optional. If no filter is provided, all apps for your partner are returned.

## 10.1 Filter Fields

| Field | Type | Description |
|-------|------|-------------|
| `idIn` | string[] | Filter by app GUIDs. Invalid IDs are silently ignored; if all IDs are invalid, returns empty results. |
| `appCustomIdIn` | string[] | Filter by custom IDs |
| `appCustomNameIn` | string[] | Filter by custom names |
| `appType` | string | Filter by app type |
| `status` | string | `enabled` or `disabled` |
| `domain` | string | Filter by organization domain |
| `organizationId` | string | Filter by organization ID |
| `createdAtGreaterThanOrEqual` | string | ISO 8601 minimum creation date |
| `createdAtLessThanOrEqual` | string | ISO 8601 maximum creation date |
| `updatedAtGreaterThanOrEqual` | string | ISO 8601 minimum update date |
| `updatedAtLessThanOrEqual` | string | ISO 8601 maximum update date |

## 10.2 Pager

| Field | Type | Default | Constraints | Description |
|-------|------|---------|-------------|-------------|
| `offset` | integer | 0 | min: 0 | Number of records to skip |
| `limit` | integer | 30 | min: 1, max: 5000 | Maximum records to return |

If the pager is omitted entirely, defaults of `offset: 0, limit: 30` are used.

**Response:**

```json
{
  "objects": [
    {
      "id": "6f8a3c12-4b5d-4e9f-a1c7-8d2e3f4a5b6c",
      "partnerId": 1234567,
      "appCustomId": "my-events-site-01",
      "appCustomName": "Annual Conference Portal",
      "appType": "ep",
      "status": "enabled",
      "version": 0,
      "createdAt": "2026-04-09T04:56:27.940Z",
      "updatedAt": "2026-04-09T04:56:27.940Z",
      "objectType": "App"
    }
  ],
  "totalCount": 42
}
```

```bash
# List all enabled Events Platform apps
curl -X POST "$KALTURA_APP_REGISTRY_URL/app-registry/list" \
  -H "Authorization: Bearer $KALTURA_KS" \
  -H "Content-Type: application/json" \
  -d '{
    "filter": {
      "appType": "ep",
      "status": "enabled"
    },
    "pager": {
      "offset": 0,
      "limit": 50
    }
  }'
```


# 11. Find Apps by Organization Domain

Look up app instances bound to a specific domain and app type.

```
POST /api/v1/app-registry/findByOrganizationDomain
Content-Type: application/json
Authorization: Bearer <KS>
```

```json
{
  "domain": "example.com",
  "appType": "kms",
  "organizationId": "org-123"
}
```

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `domain` | string | Yes | Domain to search (max 255 chars, whitespace auto-stripped) |
| `appType` | string | Yes | App type to filter by |
| `organizationId` | string | No | Organization to filter by |
| `pager` | object | No | Pagination (offset/limit, same defaults as list) |

**Response:** Same `{ objects, totalCount }` structure as `list`:

```json
{
  "objects": [
    {
      "id": "a2b3c4d5-6e7f-8a9b-0c1d-2e3f4a5b6c7d",
      "partnerId": 1234567,
      "appCustomId": "kms-main",
      "appCustomName": "Corporate MediaSpace",
      "appType": "kms",
      "status": "enabled",
      "version": 3,
      "organizationDomain": {
        "organizationId": "org-123",
        "domain": "example.com"
      },
      "createdAt": "2026-03-15T10:22:00.000Z",
      "updatedAt": "2026-04-01T14:30:00.000Z",
      "objectType": "App"
    }
  ],
  "totalCount": 1
}
```

The domain search supports comma-separated domain lists in app records — a search for `example.com` matches apps registered with `example.com`, `example.com,other.com`, etc.

```bash
curl -X POST "$KALTURA_APP_REGISTRY_URL/app-registry/findByOrganizationDomain" \
  -H "Authorization: Bearer $KALTURA_KS" \
  -H "Content-Type: application/json" \
  -d '{
    "domain": "example.com",
    "appType": "kms"
  }'
```


# 12. Versioning

Each app record has a `version` field (starts at 0). The version increments by 1 on each successful `update`, `enable`, or `disable` call that changes the record. Use versioning to detect concurrent modifications — if you read an app at version 3 and update it, the response returns version 4.

The version does NOT increment if an `enable`/`disable` call matches the current status (idempotent no-op).


# 13. Error Handling

Application-level errors return HTTP 200 with an error object:

```json
{
  "code": "OBJECT_NOT_FOUND",
  "message": "Object not found",
  "objectType": "KalturaAPIException"
}
```

Validation errors (missing required fields, invalid enum values) return HTTP 400:

```json
{
  "code": "VALIDATION_ERROR",
  "message": "appCustomId is required",
  "objectType": "KalturaAPIException"
}
```

| Error Code | Meaning |
|------------|---------|
| `OBJECT_NOT_FOUND` | App not found for your partner |
| `APP_REGISTRY_ALREADY_EXISTS_WITH_THIS_APP_CUSTOM_ID` | Duplicate `appCustomId` |
| `ORGANIZATION_ID_DOMAIN_AND_APP_TYPE_MUST_BE_UNIQUE` | Domain/org/type combination already taken |
| `APP_CANNOT_BE_ASSIGNED_TO_PARTNER` | Invalid app type for your partner |
| `UNKNOWN_PARTNER_ID` | KS does not contain a valid partner ID |

**Retry strategy:** For transient errors (HTTP 5xx, timeouts), retry with exponential backoff: 1s, 2s, 4s, with jitter, up to 3 retries. For client errors (HTTP 400, `OBJECT_NOT_FOUND`, `APP_REGISTRY_ALREADY_EXISTS_WITH_THIS_APP_CUSTOM_ID`), fix the request before retrying — these will not resolve on their own.


# 14. Best Practices

- **Use `appCustomId` for external system mapping.** Map virtual event IDs or external identifiers to app GUIDs for cross-service lookups (e.g., Events Platform auto-registers with `appCustomId` = virtual event ID).
- **Track `version` numbers for concurrency detection.** The version increments on each state change — use it to detect concurrent modifications.
- **Enable apps after configuration is complete.** Create and configure first, then enable — other services (User Profile, Messaging) only interact with enabled apps.
- **Use the delta sync pattern for production integrations.** Filter by `updatedAt` range and paginate to keep your system in sync without full re-scans.
- **Use AppTokens for production access.** Generate KS via `appToken.startSession` with HMAC — keep admin secrets off application servers.

## Common Integration Patterns

### Virtual Event ID to App GUID Mapping

When the Events Platform creates a virtual event, it automatically registers an app in the App Registry with `appType: "epmEvent"` and sets the `appCustomId` to the **virtual event ID**. This is the primary cross-service linkage — to work with registration data for a specific event, resolve the virtual event ID to an `appGuid` first:

```bash
# Step 1: Get the virtual event ID
# (from virtualEvent_virtualEvent/action/list or an existing workflow)
VIRTUAL_EVENT_ID="12345"

# Step 2: Resolve to App GUID via appCustomIdIn filter
APP_GUID=$(curl -s -X POST "$KALTURA_APP_REGISTRY_URL/app-registry/list" \
  -H "Authorization: Bearer $KALTURA_KS" \
  -H "Content-Type: application/json" \
  -d "{
    \"filter\": {
      \"appCustomIdIn\": [\"$VIRTUAL_EVENT_ID\"]
    },
    \"pager\": {\"offset\": 0, \"limit\": 1}
  }" | jq -r '.objects[0].id')

echo "App GUID for event $VIRTUAL_EVENT_ID: $APP_GUID"
# Use this APP_GUID with the User Profile API to get registration/attendance data
```

The `appCustomIdIn` filter accepts an array, so you can resolve multiple events in a single call:

```bash
# Resolve multiple virtual events at once
curl -s -X POST "$KALTURA_APP_REGISTRY_URL/app-registry/list" \
  -H "Authorization: Bearer $KALTURA_KS" \
  -H "Content-Type: application/json" \
  -d '{
    "filter": {
      "appCustomIdIn": ["12345", "12346", "12347"]
    }
  }'
```

### Register App for Custom Integration

For custom integrations outside the Events Platform, register apps explicitly:

```bash
APP_GUID=$(curl -s -X POST "$KALTURA_APP_REGISTRY_URL/app-registry/add" \
  -H "Authorization: Bearer $KALTURA_KS" \
  -H "Content-Type: application/json" \
  -d '{
    "appCustomId": "annual-conference-2025",
    "appType": "ep",
    "appCustomName": "Annual Conference 2025"
  }' | jq -r '.id')

echo "App GUID: $APP_GUID"
```

### Register App -> Manage User Profiles

The [User Profile API](KALTURA_USER_PROFILE_API.md) associates user data with specific app instances. The `appGuid` parameter in user profile operations must reference a registered, enabled app:

```bash
# Use the app GUID from registration when creating user profiles
curl -X POST "$KALTURA_USER_PROFILE_URL/user-profile/add" \
  -H "Authorization: Bearer $KALTURA_KS" \
  -H "Content-Type: application/json" \
  -d "{
    \"appGuid\": \"$APP_GUID\",
    \"userId\": \"user@example.com\",
    \"profileData\": {\"name\": \"Jane Doe\"}
  }"
```

The User Profile service validates that the `appGuid` exists and is enabled in the App Registry. Validation results are cached for up to 24 hours — if you disable or delete an app, existing user profile operations may continue to work briefly.


### Cross-Service Registration Data Retrieval

The full flow for extracting event registration and attendance data spans four services:

```bash
# Step 1: List virtual events
curl -s -X POST "$KALTURA_SERVICE_URL/service/virtualevent_virtualevent/action/list" \
  -d "ks=$KALTURA_KS" -d "format=1" | jq '.objects[] | {id, name}'
# → Get virtual event IDs

# Step 2: Resolve virtual event ID → App GUID
APP_GUID=$(curl -s -X POST "$KALTURA_APP_REGISTRY_URL/app-registry/list" \
  -H "Authorization: Bearer $KALTURA_KS" \
  -H "Content-Type: application/json" \
  -d "{\"filter\": {\"appCustomIdIn\": [\"$VIRTUAL_EVENT_ID\"]}}" \
  | jq -r '.objects[0].id')

# Step 3: Get registration/attendance data from User Profile
curl -s -X POST "$KALTURA_USER_PROFILE_URL/user-profile/list" \
  -H "Authorization: Bearer $KALTURA_KS" \
  -H "Content-Type: application/json" \
  -d "{
    \"filter\": {\"appGuidIn\": [\"$APP_GUID\"]},
    \"pager\": {\"offset\": 0, \"limit\": 500},
    \"orderBy\": \"createdAt\",
    \"includeTotalCount\": true
  }"
# → eventData has attendance status, profileData has registration form fields

# Step 4: Join with core user data (email, name, company)
# Extract userIds from step 3, then call user.list
USER_IDS="user1@example.com,user2@example.com"
curl -s -X POST "$KALTURA_SERVICE_URL/service/user/action/list" \
  -d "ks=$KALTURA_KS" -d "format=1" \
  -d "filter[objectType]=KalturaUserFilter" \
  -d "filter[idIn]=$USER_IDS"
# → firstName, lastName, email, company, jobTitle, country, state
```

For incremental syncs, use `updatedAtGreaterThanOrEqual` in both App Registry `list` and User Profile `list` filters to pull only records changed since your last sync.

### Incremental Data Sync

Use date filters for efficient delta pulls instead of full data dumps:

```bash
# Pull only apps updated since yesterday
curl -s -X POST "$KALTURA_APP_REGISTRY_URL/app-registry/list" \
  -H "Authorization: Bearer $KALTURA_KS" \
  -H "Content-Type: application/json" \
  -d '{
    "filter": {
      "updatedAtGreaterThanOrEqual": "2025-06-14T00:00:00Z",
      "appType": "epmEvent"
    },
    "pager": {"offset": 0, "limit": 500}
  }'
```

Store the last record's `updatedAt` timestamp as a watermark and use it as the start of the next sync window.


# 15. Related Guides

- **[Session Guide](KALTURA_SESSION_GUIDE.md)** — KS generation and management
- **[AppTokens API](KALTURA_APPTOKENS_API.md)** — Secure server-to-server auth
- **[User Profile API](KALTURA_USER_PROFILE_API.md)** — Per-app user profile management (depends on App Registry)
- **[Events Platform API](KALTURA_EVENTS_PLATFORM_API.md)** — Virtual events (auto-creates app registrations)
- **[Messaging API](KALTURA_MESSAGING_API.md)** — Template-based email messaging (uses appGuid for message context)
- **[Webhooks API](KALTURA_EVENT_NOTIFICATIONS_WEBHOOK_AND_EMAIL_API.md)** — Event-driven HTTP callbacks and email notifications
- **[Auth Broker](KALTURA_AUTH_BROKER_API.md)** — App subscriptions link auth profiles to registered apps

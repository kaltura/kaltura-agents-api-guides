# Kaltura Application Tokens (AppTokens) API

Application Tokens provide secure, scoped API access without exposing admin secrets. Instead of sharing your `adminSecret`, you create an AppToken with specific privileges, distribute it to integrators, and they use an HMAC exchange to obtain a KS. You can revoke access instantly by deleting the token.

**Base URL:** `https://www.kaltura.com/api_v3`  
**Auth:** Admin KS for token management; widget session + HMAC for `startSession`  
**Format:** Form-encoded POST, `format=1` for JSON responses  

<!-- Sections: 1.When to Use | 2.Prerequisites | 3.Why AppTokens Instead of Admin Secrets | 4.AppToken Object (KalturaAppToken) | 5.AppToken CRUD Operations | 6.Starting a Session with AppToken (HMAC Flow) | 7.Privilege Reference | 8.Token Rotation Pattern | 9.Hash Types | 10.Error Handling | 11.Best Practices | 12.Related Guides -->


# 1. When to Use

- **Production integrations** require revocable, scoped API credentials that can be rotated without disrupting other services or exposing admin secrets.  
- **Server-to-server microservices** authenticate with Kaltura using HMAC-based token exchange, keeping secrets strictly on the backend.  
- **Mobile and client-side applications** need API access without embedding permanent credentials in compiled binaries or client-side code.  
- **Partner and vendor onboarding** provisions isolated API access with specific privilege sets that can be revoked independently per integration.

# 2. Prerequisites

- **Kaltura Session (KS):** ADMIN KS (type=2) required for creating, listing, and managing AppTokens. See [Session Guide](KALTURA_SESSION_GUIDE.md) for generation methods.  
- **Partner ID and admin secret:** Needed for the initial ADMIN KS that creates the AppToken. Available from KMC under Settings > Integration Settings.  
- **Service URL:** Set `$KALTURA_SERVICE_URL` to your account's regional endpoint (default: `https://www.kaltura.com/api_v3`).  
- **Hash algorithm choice:** Select a hash type (SHA256 recommended) at token creation time -- it is immutable after creation.

# 3. Why AppTokens Instead of Admin Secrets

| Concern | Admin Secret | AppToken |
|---------|-------------|----------|
| Revocation | Rotate the secret → breaks ALL integrations | Delete one token → only that integration loses access |
| Privilege scope | Full admin unless you manually restrict each KS | Baked into the token at creation time |
| Secret exposure | Leaked secret = full account access | Leaked token = only scoped access, easily revocable |
| Rotation | Painful (update every integration) | Create new token, distribute, delete old one |
| Audit | Hard to tell which integration made a call | Each token has a unique ID in logs |

**Rule of thumb:** Use `session.start` only for internal backend tools where you control the environment. Use AppTokens for everything else — partner integrations, microservices, client apps.

> **API secrets are permanent.** The `adminSecret` and `secret` for a Kaltura account cannot be regenerated, rotated, or revoked. If a secret is compromised, contact Kaltura support. This makes AppTokens essential — they can be revoked and reissued independently without affecting other integrations.


# 4. AppToken Object (KalturaAppToken)

| Field | Type | Description |
|-------|------|-------------|
| `id` | string | Unique token identifier (used in `startSession`) |
| `token` | string | The secret value (used for HMAC hashing — keep server-side only) |
| `partnerId` | int | Account partner ID |
| `status` | int | `1`=DISABLED, `2`=ACTIVE, `3`=DELETED |
| `sessionType` | int | `0`=USER, `2`=ADMIN |
| `sessionDuration` | int | Max session duration in seconds (0 = account default) |
| `sessionPrivileges` | string | Comma-separated privileges baked into the token |
| `sessionUserId` | string | Fixed userId for sessions created from this token |
| `hashType` | string | Hash algorithm: `MD5`, `SHA1` (default), `SHA256`, `SHA512` |
| `expiry` | int | Token expiry as Unix timestamp (0 = never expires) |
| `description` | string | Human-readable description |
| `createdAt` | int | Unix timestamp of creation |
| `updatedAt` | int | Unix timestamp of last update |

> `sessionPrivileges` and `sessionUserId` are enforced at creation time and locked into every session minted from this token. Configure them at token creation.


# 5. AppToken CRUD Operations

## 5.1 appToken.add — Create a Token

```
POST /api_v3/service/appToken/action/add
```

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `ks` | string | Yes | Admin KS |
| `appToken[objectType]` | string | Yes | `KalturaAppToken` |
| `appToken[hashType]` | string | No | `SHA256` (recommended), `SHA1`, `SHA512`, `MD5`. Default: `SHA1`. Immutable after creation. |
| `appToken[sessionType]` | int | No | `0`=USER (recommended), `2`=ADMIN |
| `appToken[sessionDuration]` | int | No | Max session duration in seconds (0 = account default) |
| `appToken[sessionPrivileges]` | string | No | Privileges to bake in (e.g., `sview:*,list:*`) |
| `appToken[sessionUserId]` | string | No | Fixed user ID for all sessions created from this token |
| `appToken[description]` | string | No | Human-readable label |
| `appToken[expiry]` | int | No | Unix timestamp when token expires (0 = never) |

```bash
curl -X POST "$KALTURA_SERVICE_URL/service/appToken/action/add" \
  -d "ks=$KALTURA_KS" \
  -d "format=1" \
  -d "appToken[objectType]=KalturaAppToken" \
  -d "appToken[hashType]=SHA256" \
  -d "appToken[sessionType]=0" \
  -d "appToken[sessionDuration]=86400" \
  -d "appToken[sessionPrivileges]=sview:*,list:*" \
  -d "appToken[description]=My integration token"
```

**Response:**
```json
{
  "id": "1_abc123def4",
  "token": "a1b2c3d4e5f6a7b8c9d0e1f2a3b4c5d6e7f8a9b0c1d2e3f4a5b6c7d8e9f0a1b2",
  "partnerId": 123456,
  "status": 2,
  "sessionType": 0,
  "sessionDuration": 86400,
  "sessionPrivileges": "sview:*,list:*",
  "sessionUserId": "",
  "hashType": "SHA256",
  "description": "My integration token",
  "expiry": 0,
  "createdAt": 1700000000,
  "updatedAt": 1700000000,
  "objectType": "KalturaAppToken"
}
```

The response includes `id` (token ID) and `token` (the secret value — store securely on your backend server only). The `token` field is a hex string whose length depends on the hash algorithm (64 characters for SHA256).

## 5.2 appToken.get — Retrieve a Token

```
POST /api_v3/service/appToken/action/get
```

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `ks` | string | Yes | Admin KS |
| `id` | string | Yes | The AppToken ID |

Returns the full `KalturaAppToken` object. The `token` field is included only for the account admin.

```bash
curl -X POST "$KALTURA_SERVICE_URL/service/appToken/action/get" \
  -d "ks=$KALTURA_KS" \
  -d "format=1" \
  -d "id=$APP_TOKEN_ID"
```

**Response:**
```json
{
  "id": "1_abc123def4",
  "token": "a1b2c3d4e5f6a7b8c9d0e1f2a3b4c5d6e7f8a9b0c1d2e3f4a5b6c7d8e9f0a1b2",
  "partnerId": 123456,
  "status": 2,
  "sessionType": 0,
  "sessionDuration": 86400,
  "sessionPrivileges": "sview:*,list:*",
  "sessionUserId": "",
  "hashType": "SHA256",
  "description": "My integration token",
  "expiry": 0,
  "createdAt": 1700000000,
  "updatedAt": 1700000000,
  "objectType": "KalturaAppToken"
}
```

## 5.3 appToken.list — List All Tokens

```
POST /api_v3/service/appToken/action/list
```

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `ks` | string | Yes | Admin KS |
| `filter[statusEqual]` | int | No | Filter by status (`2`=ACTIVE) |
| `filter[hashTypeEqual]` | string | No | Filter by hash type |
| `filter[sessionTypeEqual]` | int | No | Filter by session type |
| `filter[idEqual]` | string | No | Filter by specific token ID |
| `pager[pageSize]` | int | No | Results per page (default 30) |
| `pager[pageIndex]` | int | No | Page number (1-based) |

```bash
curl -X POST "$KALTURA_SERVICE_URL/service/appToken/action/list" \
  -d "ks=$KALTURA_KS" \
  -d "format=1" \
  -d "filter[statusEqual]=2" \
  -d "pager[pageSize]=10"
```

**Response:**
```json
{
  "objects": [
    {
      "id": "1_abc123def4",
      "partnerId": 123456,
      "status": 2,
      "sessionType": 0,
      "sessionDuration": 86400,
      "sessionPrivileges": "sview:*,list:*",
      "hashType": "SHA256",
      "description": "My integration token",
      "expiry": 0,
      "createdAt": 1700000000,
      "updatedAt": 1700000000,
      "objectType": "KalturaAppToken"
    }
  ],
  "totalCount": 1,
  "objectType": "KalturaAppTokenListResponse"
}
```

The `token` field is included in list results only for the account admin.

## 5.4 appToken.update — Modify a Token

```
POST /api_v3/service/appToken/action/update
```

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `ks` | string | Yes | Admin KS |
| `id` | string | Yes | The AppToken ID |
| `appToken[objectType]` | string | Yes | `KalturaAppToken` |
| `appToken[description]` | string | No | Updated description |
| `appToken[sessionDuration]` | int | No | Updated max session duration |
| `appToken[sessionPrivileges]` | string | No | Updated privileges |
| `appToken[sessionUserId]` | string | No | Updated fixed user ID |

> `hashType` and `sessionType` are set at creation and locked. To use a different hash algorithm or session type, create a new token.

```bash
curl -X POST "$KALTURA_SERVICE_URL/service/appToken/action/update" \
  -d "ks=$KALTURA_KS" \
  -d "format=1" \
  -d "id=$APP_TOKEN_ID" \
  -d "appToken[objectType]=KalturaAppToken" \
  -d "appToken[description]=Updated integration token" \
  -d "appToken[sessionDuration]=43200"
```

**Response:** The updated `KalturaAppToken` object:
```json
{
  "id": "1_abc123def4",
  "partnerId": 123456,
  "status": 2,
  "sessionType": 0,
  "sessionDuration": 43200,
  "sessionPrivileges": "sview:*,list:*",
  "hashType": "SHA256",
  "description": "Updated integration token",
  "createdAt": 1700000000,
  "updatedAt": 1700001000,
  "objectType": "KalturaAppToken"
}
```

## 5.5 appToken.delete — Revoke a Token

```
POST /api_v3/service/appToken/action/delete
```

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `ks` | string | Yes | Admin KS |
| `id` | string | Yes | The AppToken ID to delete |

```bash
curl -X POST "$KALTURA_SERVICE_URL/service/appToken/action/delete" \
  -d "ks=$KALTURA_KS" \
  -d "format=1" \
  -d "id=$APP_TOKEN_ID"
```

**Response:** Empty response on success. The token's status changes to `3` (DELETED).

Immediately revokes the token. Existing KS sessions already issued from this token remain valid until their TTL expires; revoke those with `session.end` if needed.


# 6. Starting a Session with AppToken (HMAC Flow)

This is the core flow for integrations that use AppTokens instead of admin secrets.

## 6.1 The Three-Step Flow

```
session.startWidgetSession  →  HMAC(widget_ks + token_value)  →  appToken.startSession
```

1. **Get a widget session** — an unprivileged KS that identifies your partner
2. **Compute the token hash** — `HASH(widget_ks + token_value)` using the token's hash algorithm
3. **Exchange for a privileged KS** — `appToken.startSession` validates the hash and returns a scoped KS

## 6.2 appToken.startSession

```
POST /api_v3/service/appToken/action/startSession
```

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `ks` | string | Yes | The widget session KS (from `startWidgetSession`) |
| `id` | string | Yes | AppToken ID |
| `tokenHash` | string | Yes | `HASH(widget_ks + token_value)` — see section 6.3 for computation |
| `userId` | string | No | User ID for the session (overridden by token's `sessionUserId` if set) |
| `type` | int | No | Session type: `0`=USER, `2`=ADMIN (overridden by token's `sessionType`) |
| `expiry` | int | No | Session TTL in seconds (capped by token's `sessionDuration`) |
| `sessionPrivileges` | string | No | Additional privileges (merged with token's `sessionPrivileges`) |

**Response:** A JSON object containing the privileged KS string:
```json
{
  "ks": "djJ8MTIzNDU2fHh4eHh4eHh4...",
  "objectType": "KalturaSessionInfo"
}
```

## 6.3 Computing the Token Hash

The `tokenHash` is computed by concatenating the widget KS and the AppToken's `token` value, then hashing the result with the algorithm matching the token's `hashType`.

**Formula:** `tokenHash = HASH_ALGORITHM( WIDGET_KS + APP_TOKEN_VALUE )`

The input is the raw string concatenation (no separator, no encoding) of the widget KS followed by the token value. The output is the lowercase hex digest.

**Shell examples by hash type:**

```bash
# SHA256 (recommended)
TOKEN_HASH=$(echo -n "${WIDGET_KS}${APP_TOKEN_VALUE}" | shasum -a 256 | cut -d' ' -f1)

# SHA1
TOKEN_HASH=$(echo -n "${WIDGET_KS}${APP_TOKEN_VALUE}" | shasum -a 1 | cut -d' ' -f1)

# SHA512
TOKEN_HASH=$(echo -n "${WIDGET_KS}${APP_TOKEN_VALUE}" | shasum -a 512 | cut -d' ' -f1)

# MD5
TOKEN_HASH=$(echo -n "${WIDGET_KS}${APP_TOKEN_VALUE}" | md5sum | cut -d' ' -f1)
```

The `echo -n` flag is critical — it prevents a trailing newline from being included in the hash input.

## 6.4 Complete curl Example

```bash
# --- Step 1: Get a widget session (unprivileged) ---
WIDGET_RESPONSE=$(curl -s -X POST "$KALTURA_SERVICE_URL/service/session/action/startWidgetSession" \
  -d "widgetId=_$KALTURA_PARTNER_ID" \
  -d "format=1")
WIDGET_KS=$(echo "$WIDGET_RESPONSE" | jq -r '.ks')

# --- Step 2: Compute the token hash (SHA256) ---
TOKEN_HASH=$(echo -n "${WIDGET_KS}${APP_TOKEN_VALUE}" | shasum -a 256 | cut -d' ' -f1)

# --- Step 3: Exchange for a privileged KS ---
SESSION_RESPONSE=$(curl -s -X POST "$KALTURA_SERVICE_URL/service/appToken/action/startSession" \
  -d "ks=$WIDGET_KS" \
  -d "format=1" \
  -d "id=$APP_TOKEN_ID" \
  -d "tokenHash=$TOKEN_HASH" \
  -d "userId=integration-user" \
  -d "type=0" \
  -d "expiry=86400")
PRIVILEGED_KS=$(echo "$SESSION_RESPONSE" | jq -r '.ks')

# --- Use the privileged KS for API calls ---
curl -X POST "$KALTURA_SERVICE_URL/service/media/action/list" \
  -d "ks=$PRIVILEGED_KS" \
  -d "format=1" \
  -d "pager[pageSize]=5"
```

**Response (Step 1 — session.startWidgetSession):**
```json
{
  "ks": "djJ8MTIzNDU2fDlhN...",
  "partnerId": 123456,
  "userId": "0",
  "objectType": "KalturaStartWidgetSessionResponse"
}
```

**Response (Step 3 — appToken.startSession):**
```json
{
  "ks": "djJ8MTIzNDU2fHh4eHh4eHh4...",
  "objectType": "KalturaSessionInfo"
}
```

# 7. Privilege Reference

These privileges can be set on the AppToken (`sessionPrivileges`) or passed at `startSession` time.

## 7.1 Access Control Privileges

| Privilege | Description |
|-----------|-------------|
| `sview:*` | View/play all entries |
| `sview:<entryId>` | View/play a specific entry only |
| `list:*` | List entries across all owners |
| `edit:*` | Edit any entry |
| `edit:<entryId>` | Edit a specific entry only |
| `download:<entryId>` | Download a specific entry |
| `enableentitlement` | Enable entitlement checks |
| `disableentitlement` | Disable entitlement checks (use cautiously) |
| `privacycontext:<label>` | Scope to a specific privacy context |

## 7.2 Session Control Privileges

| Privilege | Description |
|-----------|-------------|
| `setrole:<roleId>` | Restrict to a specific user role |
| `actionslimit:<N>` | Max number of API calls this session can make |
| `iprestrict:<IP>` | Restrict session to a specific IP address |
| `urirestrict:<path>` | Restrict session to specific API paths |
| `sessionid:<GUID>` | Group sessions for bulk revocation |
| `appId:<name-domain>` | Tag session for analytics tracking |

## 7.3 Common Privilege Sets

```
# Read-only playback (with entitlements)
sview:*,enableentitlement,privacycontext:MY_PORTAL

# Upload integration (scoped to user's own content)
edit:*,sview:*

# Single-entry playback ticket
sview:1_abc123,setrole:PLAYBACK_BASE_ROLE,actionslimit:10

# Analytics-tagged integration
sview:*,list:*,appId:my-app-example.com
```


# 8. Token Rotation Pattern

Rotating AppTokens without downtime:

1. **Create new token** — `appToken.add` with same privileges
2. **Distribute** — update your integration to use the new token ID + value
3. **Verify** — confirm the integration works with the new token
4. **Delete old token** — `appToken.delete` on the previous token

```bash
# Step 1: Create new token
curl -X POST "$KALTURA_SERVICE_URL/service/appToken/action/add" \
  -d "ks=$KALTURA_KS" \
  -d "format=1" \
  -d "appToken[objectType]=KalturaAppToken" \
  -d "appToken[hashType]=SHA256" \
  -d "appToken[sessionType]=0" \
  -d "appToken[sessionPrivileges]=sview:*,list:*" \
  -d "appToken[description]=Rotated token - 2024-Q4"

# Step 3 (after deploying new token to integrations):
# Delete old token
curl -X POST "$KALTURA_SERVICE_URL/service/appToken/action/delete" \
  -d "ks=$KALTURA_KS" \
  -d "format=1" \
  -d "id=$OLD_TOKEN_ID"
```


# 9. Hash Types

| Hash Type | Security Level | Recommendation |
|-----------|---------------|----------------|
| `MD5` | Low | Legacy only — prefer SHA256+ |
| `SHA1` | Medium | Default, but SHA256 preferred for new tokens |
| `SHA256` | High | **Recommended** for all new tokens |
| `SHA512` | Very High | Use when extra security is needed |

> Use `SHA256` or `SHA512` for new tokens. `hashType` is locked at creation.


# 10. Error Handling

| Error Code | Meaning | Resolution |
|------------|---------|------------|
| `INVALID_APP_TOKEN_ID` | Token ID does not exist | Verify the `id` parameter; token may have been deleted |
| `INVALID_APP_TOKEN_HASH` | HMAC hash mismatch | Recompute `SHA256(widget_ks + app_token_value)` — check for encoding issues, ensure no extra whitespace |
| `APP_TOKEN_NOT_ACTIVE` | Token is disabled (status != 2) | Re-enable with `appToken.update` or create a new token |
| `EXPIRED_TOKEN` | Token has passed its `expiry` timestamp | Create a new token with a future expiry |
| `PROPERTY_VALIDATION_NOT_UPDATABLE` | Attempted to change `hashType` after creation | `hashType` is immutable — create a new token with the desired hash type |
| `INVALID_KS` | The KS used to call the API is invalid or expired | Generate a fresh admin KS via `session.start` |

**Retry strategy:** For transient errors (HTTP 5xx, timeouts), retry with exponential backoff: 1s, 2s, 4s, with jitter, up to 3 retries. For client errors (`INVALID_APP_TOKEN_HASH`, `INVALID_KS`, `EXPIRED_TOKEN`, validation errors), fix the request before retrying — these will not resolve on their own.

# 11. Best Practices

- **Use SHA256 or SHA512** for all new tokens. MD5 and SHA1 are supported for backward compatibility only.
- **Set `sessionExpiry`** on AppTokens to limit session duration (e.g., 86400 for 24 hours). Shorter is more secure.
- **Scope privileges tightly.** Use `sessionPrivileges` to restrict what the generated KS can do: `edit:entryId`, `sview:*`, `setrole:ROLE_ID`, `iprestrict:CIDR`.
- **Rotate tokens periodically.** Create a new token, migrate integrations, then delete the old one. See section 8 (Token Rotation Pattern).
- **Store tokens server-side only.** Keep AppToken IDs and token values on your backend. The HMAC exchange should happen on your server.
- **One token per integration.** Create separate AppTokens for each application or service to isolate access and simplify revocation.

# 12. Related Guides

- **[Session Guide](KALTURA_SESSION_GUIDE.md)** — KS generation, privileges, and session management
- **[Upload & Ingestion](KALTURA_UPLOAD_AND_INGESTION_API.md)** — Use AppToken-generated KS for uploads
- **[eSearch Guide](KALTURA_ESEARCH_API.md)** — Use AppToken-generated KS for search
- **[User Management API](KALTURA_USER_MANAGEMENT_API.md)** — User roles and permissions that AppTokens scope to via `setrole` privileges
- **[Player Embed](KALTURA_PLAYER_EMBED_GUIDE.md)** — Generate scoped player KS via AppToken flow
- **[REACH](KALTURA_REACH_API.md)** — Scoped tokens for enrichment service workflows (captions, translation, moderation, and more)
- **[Events Platform](KALTURA_EVENTS_PLATFORM_API.md)** — Bearer KS for events API calls
- **[Webhooks](KALTURA_WEBHOOKS_API.md)** — AppToken-based KS for webhook handler authentication
- **[Analytics Reports](KALTURA_ANALYTICS_REPORTS_API.md)** — Analytics-scoped tokens for reporting dashboards
- **[Distribution](KALTURA_DISTRIBUTION_API.md)** — Scoped tokens for distribution automation
- **[Auth Broker](KALTURA_AUTH_BROKER_API.md)** — SSO-integrated token management
- **[API Getting Started](KALTURA_API_GETTING_STARTED.md)** — Foundation guide covering API structure and authentication

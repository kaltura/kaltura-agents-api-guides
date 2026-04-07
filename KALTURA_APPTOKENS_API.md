# Kaltura Application Tokens (AppTokens) API

Application Tokens provide secure, scoped API access without exposing admin secrets. Instead of sharing your `adminSecret`, you create an AppToken with specific privileges, distribute it to integrators, and they use an HMAC exchange to obtain a KS. You can revoke access instantly by deleting the token.

**Base URL:** `https://www.kaltura.com/api_v3`
**Auth:** Admin KS for token management; widget session + HMAC for `startSession`
**Format:** Form-encoded POST, `format=1` for JSON responses


# 1. Why AppTokens Instead of Admin Secrets

| Concern | Admin Secret | AppToken |
|---------|-------------|----------|
| Revocation | Rotate the secret → breaks ALL integrations | Delete one token → only that integration loses access |
| Privilege scope | Full admin unless you manually restrict each KS | Baked into the token at creation time |
| Secret exposure | Leaked secret = full account access | Leaked token = only scoped access, easily revocable |
| Rotation | Painful (update every integration) | Create new token, distribute, delete old one |
| Audit | Hard to tell which integration made a call | Each token has a unique ID in logs |

**Rule of thumb:** Use `session.start` only for internal backend tools where you control the environment. Use AppTokens for everything else — partner integrations, microservices, client apps.


# 2. AppToken Object (KalturaAppToken)

| Field | Type | Description |
|-------|------|-------------|
| `id` | string | Unique token identifier (used in `startSession`) |
| `token` | string | The secret value (used for HMAC hashing — never expose to clients) |
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


# 3. AppToken CRUD Operations

## 3.1 appToken.add — Create a Token

```
POST /api_v3/service/appToken/action/add
```

| Parameter | Type | Description |
|-----------|------|-------------|
| `ks` | string | Admin KS |
| `appToken[objectType]` | string | `KalturaAppToken` |
| `appToken[hashType]` | string | `SHA256` (recommended), `SHA1`, `SHA512`, `MD5` |
| `appToken[sessionType]` | int | `0`=USER (recommended), `2`=ADMIN |
| `appToken[sessionDuration]` | int | Max session duration in seconds |
| `appToken[sessionPrivileges]` | string | Privileges to bake in (e.g., `sview:*,list:*`) |
| `appToken[sessionUserId]` | string | Fixed user ID (optional) |
| `appToken[description]` | string | Human-readable label |
| `appToken[expiry]` | int | Unix timestamp when token expires (0 = never) |

```bash
curl -X POST "$SERVICE_URL/service/appToken/action/add" \
  -d "ks=$KS" \
  -d "format=1" \
  -d "appToken[objectType]=KalturaAppToken" \
  -d "appToken[hashType]=SHA256" \
  -d "appToken[sessionType]=0" \
  -d "appToken[sessionDuration]=86400" \
  -d "appToken[sessionPrivileges]=sview:*,list:*" \
  -d "appToken[description]=My integration token"
```

The response includes `id` (token ID) and `token` (the secret value -- store securely, never expose to clients).

## 3.2 appToken.get — Retrieve a Token

```
POST /api_v3/service/appToken/action/get
```

| Parameter | Type | Description |
|-----------|------|-------------|
| `id` | string | The AppToken ID |

Returns the full `KalturaAppToken` object. The `token` field is included only for the account admin.

## 3.3 appToken.list — List All Tokens

```
POST /api_v3/service/appToken/action/list
```

| Parameter | Type | Description |
|-----------|------|-------------|
| `filter[statusEqual]` | int | Filter by status (`2`=ACTIVE) |
| `filter[hashTypeEqual]` | string | Filter by hash type |
| `filter[sessionTypeEqual]` | int | Filter by session type |
| `pager[pageSize]` | int | Results per page (default 30) |
| `pager[pageIndex]` | int | Page number (1-based) |

```bash
curl -X POST "$SERVICE_URL/service/appToken/action/list" \
  -d "ks=$KS" \
  -d "format=1" \
  -d "filter[statusEqual]=2" \
  -d "pager[pageSize]=10"
```

The response `objects` array contains each token with `id`, `description`, `hashType`, `expiry`, and other fields.

## 3.4 appToken.update — Modify a Token

```
POST /api_v3/service/appToken/action/update
```

| Parameter | Type | Description |
|-----------|------|-------------|
| `id` | string | The AppToken ID |
| `appToken[objectType]` | string | `KalturaAppToken` |
| `appToken[description]` | string | Updated description |
| `appToken[sessionDuration]` | int | Updated max session duration |
| `appToken[sessionPrivileges]` | string | Updated privileges |

> `hashType` is set at creation and locked. To use a different hash algorithm, create a new token.

## 3.5 appToken.delete — Revoke a Token

```
POST /api_v3/service/appToken/action/delete
```

| Parameter | Type | Description |
|-----------|------|-------------|
| `id` | string | The AppToken ID to delete |

Immediately revokes the token. Existing KS sessions already issued from this token remain valid until their TTL expires; revoke those with `session.end` if needed.


# 4. Starting a Session with AppToken (HMAC Flow)

This is the core flow for integrations that use AppTokens instead of admin secrets.

## 4.1 The Three-Step Flow

```
session.startWidgetSession  →  HMAC(widget_ks + token_value)  →  appToken.startSession
```

1. **Get a widget session** — an unprivileged KS that identifies your partner
2. **Compute the token hash** — `HASH(widget_ks + token_value)` using the token's hash algorithm
3. **Exchange for a privileged KS** — `appToken.startSession` validates the hash and returns a scoped KS

## 4.2 appToken.startSession

```
POST /api_v3/service/appToken/action/startSession
```

| Parameter | Type | Description |
|-----------|------|-------------|
| `ks` | string | The widget session KS (from `startWidgetSession`) |
| `id` | string | AppToken ID |
| `tokenHash` | string | `HASH(widget_ks + token_value)` |
| `userId` | string | User ID for the session (may be overridden by token's `sessionUserId`) |
| `type` | int | Session type: `0`=USER, `2`=ADMIN (may be overridden by token's `sessionType`) |
| `expiry` | int | Session TTL in seconds (capped by token's `sessionDuration`) |
| `sessionPrivileges` | string | Additional privileges (merged with token's `sessionPrivileges`) |

**Response:** A KS string (not a JSON object — just the session string).

## 4.3 Complete curl Example

```bash
# --- Step 1: Get a widget session (unprivileged) ---
curl -X POST "$SERVICE_URL/service/session/action/startWidgetSession" \
  -d "widgetId=_$PARTNER_ID" \
  -d "format=1"
# Save the "ks" from the response as WIDGET_KS

# --- Step 2: Compute the token hash ---
# Compute: tokenHash = HASH_TYPE(WIDGET_KS + APP_TOKEN_VALUE)
# where HASH_TYPE matches the token's hashType (e.g., SHA256).
#
# Example using shell (SHA256):
#   TOKEN_HASH=$(echo -n "${WIDGET_KS}${APP_TOKEN_VALUE}" | shasum -a 256 | cut -d' ' -f1)
#
# For other hash types, use the corresponding algorithm:
#   MD5:    echo -n "..." | md5sum | cut -d' ' -f1
#   SHA1:   echo -n "..." | shasum -a 1 | cut -d' ' -f1
#   SHA512: echo -n "..." | shasum -a 512 | cut -d' ' -f1

# --- Step 3: Exchange for a privileged KS ---
curl -X POST "$SERVICE_URL/service/appToken/action/startSession" \
  -d "ks=$WIDGET_KS" \
  -d "format=1" \
  -d "id=$APP_TOKEN_ID" \
  -d "tokenHash=$TOKEN_HASH" \
  -d "userId=integration-user" \
  -d "type=0" \
  -d "expiry=86400"
# The response is the privileged KS string. Save it as KS.

# --- Use the privileged KS for API calls ---
curl -X POST "$SERVICE_URL/service/media/action/list" \
  -d "ks=$KS" \
  -d "format=1" \
  -d "pager[pageSize]=5"
```


# 5. Privilege Reference

These privileges can be set on the AppToken (`sessionPrivileges`) or passed at `startSession` time.

## 5.1 Access Control Privileges

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

## 5.2 Session Control Privileges

| Privilege | Description |
|-----------|-------------|
| `setrole:<roleId>` | Restrict to a specific user role |
| `actionslimit:<N>` | Max number of API calls this session can make |
| `iprestrict:<IP>` | Restrict session to a specific IP address |
| `urirestrict:<path>` | Restrict session to specific API paths |
| `sessionid:<GUID>` | Group sessions for bulk revocation |
| `appId:<name-domain>` | Tag session for analytics tracking |

## 5.3 Common Privilege Sets

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


# 6. Token Rotation Pattern

Rotating AppTokens without downtime:

1. **Create new token** — `appToken.add` with same privileges
2. **Distribute** — update your integration to use the new token ID + value
3. **Verify** — confirm the integration works with the new token
4. **Delete old token** — `appToken.delete` on the previous token

```bash
# Step 1: Create new token
curl -X POST "$SERVICE_URL/service/appToken/action/add" \
  -d "ks=$KS" \
  -d "format=1" \
  -d "appToken[objectType]=KalturaAppToken" \
  -d "appToken[hashType]=SHA256" \
  -d "appToken[sessionType]=0" \
  -d "appToken[sessionPrivileges]=sview:*,list:*" \
  -d "appToken[description]=Rotated token - 2024-Q4"

# Step 3 (after deploying new token to integrations):
# Delete old token
curl -X POST "$SERVICE_URL/service/appToken/action/delete" \
  -d "ks=$KS" \
  -d "format=1" \
  -d "id=$OLD_TOKEN_ID"
```


# 7. Hash Types

| Hash Type | Security Level | Recommendation |
|-----------|---------------|----------------|
| `MD5` | Low | Legacy only — prefer SHA256+ |
| `SHA1` | Medium | Default, but SHA256 preferred for new tokens |
| `SHA256` | High | **Recommended** for all new tokens |
| `SHA512` | Very High | Use when extra security is needed |

> Use `SHA256` or `SHA512` for new tokens. `hashType` is locked at creation.


# 8. Related Guides

- **[Session Guide](KALTURA_SESSION_GUIDE.md)** — KS generation, privileges, and session management
- **[Upload & Delivery Guide](KALTURA_UPLOAD_AND_DELIVERY_API.md)** — Use AppToken-generated KS for uploads
- **[eSearch Guide](KALTURA_ESEARCH_API.md)** — Use AppToken-generated KS for search
- **Reference implementation:** [kal-apptokens-utils](https://github.com/kaltura/kal-apptokens-utils) — Python CLI for AppToken management

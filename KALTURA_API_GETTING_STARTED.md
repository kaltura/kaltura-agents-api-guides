# Kaltura API — Getting Started

The Kaltura platform exposes 100+ REST API services, a dozen client libraries, several front-end libraries, and embeddable experience components — covering content management, playback, AI enrichment, analytics, and more. This guide covers the fundamentals: how requests work, how to authenticate, how to batch calls for performance, and how to handle errors.

**Base URL:** `https://www.kaltura.com/api_v3` (may differ by region/deployment)  
**Auth:** All requests require a Kaltura Session (KS) — see [Session Guide](KALTURA_SESSION_GUIDE.md) for details  
**Format:** Form-encoded or JSON POST, `format=1` for JSON responses  


# 1. When to Use

- **First-time Kaltura API developers** use this guide to understand request structure, authentication, error handling, and the content model before diving into specific services.  
- **Integration architects** reference this guide for endpoint patterns, regional URL configuration, and best practices for batching API calls with multirequest.  
- **Development teams onboarding to Kaltura** start here to set up their environment, make their first API call, and understand how entries, assets, and sessions relate.

# 2. Prerequisites

- **Partner ID and admin secret:** Available from your Kaltura Management Console (KMC) under Settings > Integration Settings.  
- **Service URL:** Set `$KALTURA_SERVICE_URL` to your account's regional endpoint (default: `https://www.kaltura.com/api_v3`).  
- **A valid Kaltura Session (KS):** Generate one using `session.start` as described in [Session Guide](KALTURA_SESSION_GUIDE.md). All API calls require a KS.  
- **curl or an HTTP client:** All examples use curl. Any HTTP client that supports POST requests with form-encoded or JSON bodies works.

# 3. API Request Structure

Every Kaltura API v3 call follows this pattern:

```
POST {BASE_URL}/service/{SERVICE_NAME}/action/{ACTION_NAME}
```

For example, listing media entries:

```bash
curl -X POST "$KALTURA_SERVICE_URL/service/media/action/list" \
  -d "ks=$KALTURA_KS" \
  -d "format=1"
```

**Key conventions:**

- **HTTP method:** Always POST (even for read operations)  
- **Content-Type:** `application/x-www-form-urlencoded` (default) or `application/json` — the API v3 backend accepts both formats  
- **Response format:** Add `format=1` to get JSON (`format` values: `1`=JSON, `2`=XML, `3`=PHP, `9`=JSONP).  
- **Authentication:** Pass `ks=` as a form parameter or JSON field in every request  
- **Boolean parameters:** Many filter fields use `KalturaNullableBoolean`: `-1`=null/ignore, `0`=false, `1`=true. Pass integers, not string `"true"`/`"false"`.  

**Form-encoded parameters** use bracket notation for nested fields:

```bash
curl -X POST "$KALTURA_SERVICE_URL/service/media/action/list" \
  -d "ks=$KALTURA_KS" \
  -d "format=1" \
  -d "filter[objectType]=KalturaMediaEntryFilter" \
  -d "filter[nameLike]=demo" \
  -d "filter[mediaTypeEqual]=1" \
  -d "pager[pageSize]=10" \
  -d "pager[pageIndex]=1"
```

**JSON bodies** use nested objects directly:

```bash
curl -X POST "$KALTURA_SERVICE_URL/service/media/action/list" \
  -H "Content-Type: application/json" \
  -d '{
    "ks": "'$KALTURA_KS'",
    "format": 1,
    "filter": {
      "objectType": "KalturaMediaEntryFilter",
      "nameLike": "demo",
      "mediaTypeEqual": 1
    },
    "pager": { "pageSize": 10, "pageIndex": 1 }
  }'
```

Both formats produce identical results. These guides use form-encoded `curl` examples since they are easier for agents to adapt to any language, but JSON is equally supported.

The `objectType` field tells the server which object class to instantiate. Include it when the API accepts multiple object types for a parameter.

**Newer platform services** (Events Platform, Agents Manager, AI Genie) have their own dedicated REST endpoints with Bearer or KS auth headers. Each guide specifies its endpoint and auth method.


# 4. Endpoints & Regions

Kaltura operates across 6 regional deployments. Each region provides the full API and service stack. Your account is provisioned to a specific region — use the corresponding endpoints.

## 4.1 Regions

| Region | Code | API Base URL |
|--------|------|-------------|
| US (default) | `nvp1` | `https://www.kaltura.com/api_v3` |
| Frankfurt (DE) | `frp2` | `https://api.de.kaltura.com/api_v3` |
| Ireland (EU) | `irp2` | `https://api.eu.kaltura.com/api_v3` |
| Singapore | `sgp2` | `https://api.sg.kaltura.com/api_v3` |
| Canada | `cap2` | `https://api.ca.kaltura.com/api_v3` |
| Australia | `syp2` | `https://api.ap.kaltura.com/api_v3` |

## 4.2 URL Patterns

Every Kaltura service follows a dual-naming convention — an internal domain and a friendly alias that resolve to the same backend:

- **Internal:** `{service}.{regionCode}.ovp.kaltura.com` (e.g., `api.frp2.ovp.kaltura.com`)  
- **Friendly:** `{service}.{regionPrefix}.kaltura.com` (e.g., `api.de.kaltura.com`)  
- **US region:** Also supports the internal pattern (`www.nvp1.ovp.kaltura.com`), but the friendly aliases (`www.kaltura.com`) are more common. Note: in the US region, the Core API service name is `www` rather than `api` (e.g., `www.nvp1.ovp.kaltura.com/api_v3`).  
- **Microservices** follow the same `{svc}.{code}.ovp.kaltura.com` pattern in all regions, including US (`{svc}.nvp1.ovp.kaltura.com`).

## 4.3 Service Endpoints by Category

| Category | US Endpoint | Regional Pattern |
|----------|------------|-----------------|
| **Core API** | `www.kaltura.com/api_v3` (also `www.nvp1.ovp.kaltura.com/api_v3`) | `api.{region}.kaltura.com/api_v3` (internal: `api.{code}.ovp.kaltura.com/api_v3`) |
| **VOD Delivery** | `cfvod.kaltura.com` | `cfvod.{code}.ovp.kaltura.com` |
| **Live Delivery** | `cflive.kaltura.com` | `cflive.{code}.ovp.kaltura.com` |
| **Analytics** | `analytics.kaltura.com` | `analytics.{region}.kaltura.com` |
| **Upload** | `upload.kaltura.com` | `upload.{code}.ovp.kaltura.com` |
| **Push/Messaging** | `push.kaltura.com` | `push.{code}.ovp.kaltura.com` |
| **Microservices** | `{svc}.nvp1.ovp.kaltura.com` | `{svc}.{code}.ovp.kaltura.com` |

Microservices include: `messaging`, `auth`, `chat`, `connectors`, `user`, `sso`, `app-registry`.  
AI services (Agents Manager, AI Genie) follow the same microservice pattern: `agents-manager.{code}.ovp.kaltura.com`, `genie.{code}.ovp.kaltura.com`.

## 4.4 Protocols & Ports

| Protocol | Port | Usage |
|----------|------|-------|
| HTTPS | 443 | All API and delivery traffic (required) |
| HTTP | 80 | Legacy fallback (US only); use HTTPS for all production traffic |
| RTMP | 1935 | Live stream ingress |
| RTMPS | 443 | Encrypted live stream ingress |
| SRT | 7045 | Low-latency live stream ingress |

**Key considerations:**  
- **Use domain names, not IP addresses** — cloud infrastructure IPs change frequently.  
- **All traffic is outbound** — firewalls need egress rules to these endpoints, not inbound.  
- **Set `$KALTURA_SERVICE_URL`** to your region's API base URL. All guides use this variable.


# 5. Content Model: Entries and Assets

Understanding Kaltura's content model helps agents choose the right API for each task. All content in Kaltura is organized around two core concepts: **entries** and **assets**.

## 5.1 Entries — The Content Container

An **entry** is a logical container that represents a single piece of content. It holds metadata (name, description, tags, categories) and links to one or more assets (files). Every entry has a unique `id` (e.g., `1_abc12345`) and a `type` that determines its behavior.

**Entry type hierarchy:**

| Entry Class | Type Value | Service | Description |
|-------------|-----------|---------|-------------|
| `KalturaMediaEntry` | 1 | `media` | Video, audio, or image — transcoded into playable renditions (flavors) |
| `KalturaLiveStreamEntry` | 7 | `liveStream` | Live broadcast entry with streaming endpoints |
| `KalturaPlaylist` | 5 | `playlist` | Ordered collection of entries (playlistType: `3`=static list, `10`=dynamic filter) |
| `KalturaDataEntry` | 6 | `baseEntry` | Arbitrary file storage — served as-is, no transcoding |
| `KalturaDocumentEntry` | 10 | `document` | PDF, DOCX, PPTX — document conversion for web viewing |

`KalturaMediaEntry` is the most common type. It extends `KalturaPlayableEntry`, which adds playback-related fields (`plays`, `views`, `duration`, `width`, `height`). Data and document entries extend `KalturaBaseEntry` directly and have no playback fields.

## 5.2 Assets — The Files Inside an Entry

An **asset** is a file attached to an entry. Each entry can have multiple assets of different types:

| Asset Type | Service | Description |
|------------|---------|-------------|
| **Flavor asset** | `flavorAsset` | A transcoded rendition of the source video (e.g., 360p, 720p, 1080p). Created automatically by the conversion profile. The source file is also stored as a flavor (with `isOriginal=true`). |
| **Thumbnail asset** | `thumbAsset` | A thumbnail image. The default is auto-generated; additional thumbnails can be uploaded or captured from a video frame. |
| **Caption asset** | `caption_captionAsset` | A subtitle/caption file (SRT, VTT, DFXP). Can be uploaded manually or generated by REACH AI services. |
| **Attachment asset** | `attachment_attachmentAsset` | A supplementary file (PDF, JSON, etc.) linked to the entry. Shown as "Related Files" in the KMC. |

The relationship is one-to-many: one entry has many assets. Each asset has an `entryId` linking it to its parent entry.

## 5.3 Entry Lifecycle

A media entry progresses through these states:

```
media.add (creates empty entry, status=7 NO_CONTENT)
    ↓
media.addContent (attaches uploaded file to entry)
    ↓
Transcoding (status=4 PENDING — conversion profile creates flavors)
    ↓
Entry Ready (status=2 READY — all required flavors transcoded)
```

The conversion profile assigned to the entry determines which flavors to create and when the entry is considered READY (e.g., "ready when the lowest-bitrate flavor is done" vs "ready when all flavors are done").

## 5.4 Partial Updates

Update calls (`media.update`, `baseEntry.update`) apply **partial updates** — only the fields you include in the request are changed. Fields you omit are left unchanged. There is no need to `get` the entry before updating it.

```bash
# Only the tags field is updated — name, description, and all other fields remain unchanged
curl -X POST "$KALTURA_SERVICE_URL/service/media/action/update" \
  -d "ks=$KALTURA_KS" \
  -d "format=1" \
  -d "entryId=$KALTURA_ENTRY_ID" \
  -d "mediaEntry[tags]=updated,tags,here"
```


# 6. Your First API Call

Generate a KS and list your content:

```bash
# Step 1: Generate a Kaltura Session
# (In production, use AppTokens instead — see AppTokens Guide)
curl -X POST "$KALTURA_SERVICE_URL/service/session/action/start" \
  -d "format=1" \
  -d "partnerId=$KALTURA_PARTNER_ID" \
  -d "secret=$KALTURA_ADMIN_SECRET" \
  -d "type=2" \
  -d "userId=$KALTURA_USER_ID"
# Response: the KS string — save it as $KALTURA_KS

# Step 2: List media entries
curl -X POST "$KALTURA_SERVICE_URL/service/media/action/list" \
  -d "ks=$KALTURA_KS" \
  -d "format=1" \
  -d "pager[pageSize]=5"
```

The response includes `objects` (array of entries) and `totalCount`:

```json
{
  "objects": [
    {
      "id": "1_abc12345",
      "name": "My Video",
      "mediaType": 1,
      "status": 2,
      "duration": 120,
      "objectType": "KalturaMediaEntry"
    }
  ],
  "totalCount": 42,
  "objectType": "KalturaMediaListResponse"
}
```


# 7. Client Libraries

Kaltura provides a dozen official client libraries that abstract the HTTP layer:

| Language | Package |
|----------|---------|
| JavaScript/Node | `kaltura-client` (npm) |
| Python | `KalturaApiClient` (PyPI) |
| PHP | `kaltura/api-client-library` (Packagist) |
| Java | `com.kaltura:KalturaClient` (Maven) |
| Ruby | `kaltura-client` (RubyGems) |
| .NET | `Kaltura.Client` (NuGet) |
| Go | `KalturaGeneratedAPIClientsGo` |
| Swift | `KalturaGeneratedAPIClientsSwift` |
| Android/Java | `KalturaGeneratedAPIClientsAndroid` |
| Objective-C | `KalturaGeneratedAPIClientsObjectiveC` |
| TypeScript | `KalturaGeneratedAPIClientsTypescript` |
| Angular | `KalturaGeneratedAPIClientsAngular` |

Client libraries handle parameter encoding, object type mapping, and KS attachment automatically. They are auto-generated from the API schema, so they always reflect the latest API surface.  
These guides use `curl` examples so agents can adapt to any language.


# 8. Multirequest — Batching API Calls

Combine multiple API calls into a single HTTP request using the multirequest endpoint. Each sub-request can reference results from previous sub-requests using `{N:result:property}` chaining.

**Endpoint:** `POST $KALTURA_SERVICE_URL/service/multirequest`

**How it works:**

- Number each sub-request starting from 1: `1:service`, `1:action`, `2:service`, `2:action`
- Chain outputs: `2:entryId={1:result:id}` passes request 1's `id` into request 2's `entryId`
- The response is a JSON array with one result per sub-request

**Example: Create entry + add content in one call:**

```bash
curl -X POST "$KALTURA_SERVICE_URL/service/multirequest" \
  -d "format=1" \
  -d "ks=$KALTURA_KS" \
  -d "1:service=uploadToken" \
  -d "1:action=add" \
  -d "2:service=media" \
  -d "2:action=add" \
  -d "2:entry[objectType]=KalturaMediaEntry" \
  -d "2:entry[name]=My Video" \
  -d "2:entry[mediaType]=1" \
  -d "3:service=media" \
  -d "3:action=addContent" \
  -d "3:entryId={2:result:id}" \
  -d "3:resource[objectType]=KalturaUploadedFileTokenResource" \
  -d "3:resource[token]={1:result:id}"
```

**Response:** Array of results — one per sub-request:

```json
[
  { "id": "0_uploadtoken123", "objectType": "KalturaUploadToken" },
  { "id": "1_newentry456", "name": "My Video", "objectType": "KalturaMediaEntry" },
  { "id": "1_newentry456", "objectType": "KalturaMediaEntry" }
]
```

**Error handling:** Each sub-request can fail independently. Check each array element for `objectType: "KalturaAPIException"`:

```json
[
  { "id": "0_token123", "objectType": "KalturaUploadToken" },
  { "code": "INVALID_ENTRY_ID", "message": "...", "objectType": "KalturaAPIException" }
]
```

**When to use multirequest:**

- **Use when** subsequent calls depend on prior results (chaining), when reducing round trips matters for latency-sensitive operations, or when you need to guarantee atomicity of a sequence of related calls.  
- **Avoid when** calls are independent and can run in parallel from your client, when the total payload becomes very large, or when you need individual error recovery per call (a multirequest either succeeds or fails as a unit at the HTTP level, though individual sub-requests can fail independently within the response array).  
- **Common patterns:** Upload workflows (create token + entry + attach content), creating entries with metadata and categories, any sequential workflow where each step uses a result from the previous step.


# 9. Error Handling

**Error response format:**

```json
{
  "code": "INVALID_KS",
  "message": "Invalid KS \"...\" - Error: EXPIRED_KS",
  "objectType": "KalturaAPIException",
  "args": { ... }
}
```

**Common error codes:**

| Code | Meaning | Resolution |
|------|---------|------------|
| `MISSING_KS` | No KS provided | Add `ks=` parameter |
| `INVALID_KS` | KS is malformed, expired, or revoked | Generate a fresh KS |
| `SERVICE_FORBIDDEN` | KS lacks permission for this service | Use an ADMIN KS or add required privileges |
| `INVALID_OBJECT_TYPE` | Unknown `objectType` value | Check spelling and available types |
| `PROPERTY_VALIDATION_CANNOT_BE_NULL` | Required field missing | Add the required parameter |
| `SERVICE_DOES_NOT_EXISTS` | Misspelled service name | Check the service name |
| `ACTION_DOES_NOT_EXISTS` | Misspelled action name | Check the action name |

**Retry strategy:** For transient errors (HTTP 5xx, timeouts), retry with exponential backoff: 1s, 2s, 4s, with jitter, up to 3 retries. For client errors (4xx, `INVALID_KS`, `PROPERTY_VALIDATION_*`), fix the request before retrying.


# 10. Best Practices

- **Use AppTokens in production.** The `session.start` examples in this guide are for getting started. In production, use [AppTokens](KALTURA_APPTOKENS_API.md) to avoid exposing your admin secret.  
- **Always include `format=1`.** Without it, API v3 returns XML instead of JSON.  
- **Set `$KALTURA_SERVICE_URL` to your region.** All examples use this variable. Set it to your account's regional endpoint (see section 4).  
- **Check multirequest sub-results individually.** Each element in the response array can be a success or a `KalturaAPIException` — check each one.  
- **Use short-lived KS tokens.** Default to 1-4 hour expiry. Renew via AppToken flow rather than generating long-lived admin sessions.


# 11. Shell Variables

All guides in this project use these shell variables in curl examples:

| Variable | Description | Example |
|----------|------------|---------|
| `$KALTURA_SERVICE_URL` | API base URL | `https://www.kaltura.com/api_v3` |
| `$KALTURA_PARTNER_ID` | Your Kaltura account ID | `123456` |
| `$KALTURA_ADMIN_SECRET` | Admin secret (backend only) | `abc123...` |
| `$KALTURA_KS` | Active Kaltura Session token | `djJ8MTIz...` |
| `$KALTURA_USER_ID` | User identifier | `user@example.com` |
| `$KALTURA_PLAYER_ID` | Player uiConf ID | `56732362` |

Set these before running examples:

```bash
export KALTURA_SERVICE_URL="https://www.kaltura.com/api_v3"
export KALTURA_PARTNER_ID="YOUR_PARTNER_ID"
export KALTURA_ADMIN_SECRET="YOUR_ADMIN_SECRET"
```


# 12. Related Guides

- **[Session Guide](KALTURA_SESSION_GUIDE.md)** — Deep dive into KS types, creation methods, privileges, and security
- **[AppTokens](KALTURA_APPTOKENS_API.md)** — Production authentication without exposing secrets
- **[Upload & Delivery](KALTURA_UPLOAD_AND_DELIVERY_API.md)** — Upload content, manage flavors, thumbnails, and delivery
- **[eSearch](KALTURA_ESEARCH_API.md)** — Full-text search across your content library
- **[Player Embed](KALTURA_PLAYER_EMBED_GUIDE.md)** — Embed the video player in web applications
- **[Guide Map](GUIDE_MAP.md)** — Full dependency graph and "I want to..." decision tree

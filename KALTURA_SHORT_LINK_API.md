# Kaltura Short Link API

Create, manage, and resolve shortened URLs for sharing Kaltura content — player embeds, preview pages, download links, or any URL. Short links provide clean, shareable URLs with built-in expiration and status control.

**Base URL:** `$KALTURA_SERVICE_URL` (e.g., `https://www.kaltura.com/api_v3`)  
**Auth:** KS as form parameter (`-d "ks=$KALTURA_KS"`)  
**Format:** Form-encoded POST, `format=1` for JSON responses

<!-- Sections: 1.When to Use | 2.Prerequisites | 3.Create a Short Link | 4.Resolve a Short Link | 5.List Short Links | 6.Update a Short Link | 7.Delete a Short Link | 8.Common Integration Patterns | 9.Error Handling | 10.Best Practices | 11.Related Guides -->

# 1. When to Use

- **Shareable preview URLs** — Generate clean links for player preview pages, embed configurators, or content portals
- **Time-limited access** — Create expiring links for temporary content access (e.g., review links, campaign URLs)
- **URL management** — Track and manage all shortened URLs across your account with filtering by user, status, or date
- **Deep link shortening** — Shorten complex Kaltura URLs (playManifest, embed codes, portal pages) into compact IDs

# 2. Prerequisites

- A Kaltura account with Partner ID and Admin Secret
- An admin KS (type=2) with `disableentitlement` privilege for full access
- User KS (type=0) can create/list short links scoped to that user only

```bash
export KALTURA_SERVICE_URL="https://www.kaltura.com/api_v3"
export KALTURA_PARTNER_ID="your_partner_id"

KALTURA_KS=$(curl -s -X POST "$KALTURA_SERVICE_URL/service/session/action/start" \
  -d "secret=$KALTURA_ADMIN_SECRET" \
  -d "partnerId=$KALTURA_PARTNER_ID" \
  -d "type=2" \
  -d "userId=$KALTURA_USER_ID" \
  -d "privileges=disableentitlement" \
  -d "format=1" | tr -d '"')
```

# 3. Create a Short Link

```
POST /service/shortlink_shortlink/action/add
```

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `shortLink[systemName]` | string | Yes | Identifier (min 3 chars) — use a descriptive name for programmatic lookups |
| `shortLink[fullUrl]` | string | Yes | Destination URL (min 10 chars) — the URL the short link redirects to |
| `shortLink[status]` | int | No | 1=DISABLED, 2=ENABLED (default), 3=DELETED |
| `shortLink[expiresAt]` | int | No | Unix timestamp for expiration (0 or omit = never expires) |
| `shortLink[userId]` | string | No | Owner user ID (defaults to KS user) |
| `shortLink[name]` | string | No | Display name for the short link |

```bash
curl -X POST "$KALTURA_SERVICE_URL/service/shortlink_shortlink/action/add" \
  -d "ks=$KALTURA_KS" \
  -d "format=1" \
  -d "shortLink[objectType]=KalturaShortLink" \
  -d "shortLink[systemName]=PREVIEW-ENTRY-$KALTURA_ENTRY_ID" \
  -d "shortLink[fullUrl]=https://www.kaltura.com/index.php/extwidget/preview/partner_id/$KALTURA_PARTNER_ID/uiconf_id/$KALTURA_PLAYER_ID/entry_id/$KALTURA_ENTRY_ID/embed/dynamic" \
  -d "shortLink[status]=2"
```

**Response:**

```json
{
  "id": "67mk41xj",
  "createdAt": 1778429631,
  "updatedAt": 1778429631,
  "partnerId": 1234567,
  "userId": "user@example.com",
  "systemName": "PREVIEW-ENTRY-1_abc123",
  "fullUrl": "https://www.kaltura.com/index.php/extwidget/preview/partner_id/1234567/uiconf_id/56732362/entry_id/1_abc123/embed/dynamic",
  "status": 2,
  "objectType": "KalturaShortLink"
}
```

The returned `id` is the short link identifier. The shareable URL is:

```
https://{SERVICE_URL_HOST}/tiny/{id}
```

For example: `https://www.kaltura.com/tiny/67mk41xj`

## 3.1 Create an Expiring Short Link

Set `expiresAt` to a Unix timestamp. The `goto` action will reject expired links with `EXPIRED_SHORT_LINK`.

```bash
EXPIRES_AT=$(date -d "+7 days" +%s 2>/dev/null || date -v+7d +%s)

curl -X POST "$KALTURA_SERVICE_URL/service/shortlink_shortlink/action/add" \
  -d "ks=$KALTURA_KS" \
  -d "format=1" \
  -d "shortLink[objectType]=KalturaShortLink" \
  -d "shortLink[systemName]=TEMP-REVIEW-LINK" \
  -d "shortLink[fullUrl]=https://www.kaltura.com/index.php/extwidget/preview/partner_id/$KALTURA_PARTNER_ID/uiconf_id/$KALTURA_PLAYER_ID/entry_id/$KALTURA_ENTRY_ID/embed/dynamic" \
  -d "shortLink[status]=2" \
  -d "shortLink[expiresAt]=$EXPIRES_AT"
```

# 4. Resolve a Short Link

## 4.1 Browser Redirect (Primary Use)

Users access short links directly in the browser. The URL format is:

```
https://{SERVICE_URL_HOST}/tiny/{SHORT_LINK_ID}
```

This returns a `301` redirect to the API `goto` action, which then issues a `302` redirect to the `fullUrl`.

## 4.2 API `goto` Action

```
GET /service/shortlink_shortlink/action/goto/id/{SHORT_LINK_ID}
```

| Parameter | Type | Required | Default | Description |
|-----------|------|----------|---------|-------------|
| `id` | string | Yes | — | Short link ID |
| `proxy` | boolean | No | false | Proxy the response content instead of redirecting |

The `goto` action requires no KS — it is publicly accessible. It validates the link status and expiration before redirecting.

```bash
curl -s -o /dev/null -w "%{http_code} %{redirect_url}" \
  "$KALTURA_SERVICE_URL/service/shortlink_shortlink/action/goto/id/$SHORT_LINK_ID"
```

With `proxy=true`, the server fetches the destination URL and returns its content directly:

```bash
curl -s "$KALTURA_SERVICE_URL/service/shortlink_shortlink/action/goto/id/$SHORT_LINK_ID/proxy/true"
```

# 5. List Short Links

```
POST /service/shortlink_shortlink/action/list
```

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `filter[statusEqual]` | int | No | Filter by status (1=DISABLED, 2=ENABLED, 3=DELETED) |
| `filter[statusIn]` | string | No | Comma-separated status values |
| `filter[userIdEqual]` | string | No | Filter by owner user ID |
| `filter[systemNameEqual]` | string | No | Filter by exact systemName |
| `filter[systemNameIn]` | string | No | Comma-separated systemName values |
| `filter[idEqual]` | string | No | Filter by exact ID |
| `filter[idIn]` | string | No | Comma-separated IDs |
| `filter[createdAtGreaterThanOrEqual]` | int | No | Created on or after (Unix timestamp) |
| `filter[createdAtLessThanOrEqual]` | int | No | Created on or before (Unix timestamp) |
| `filter[updatedAtGreaterThanOrEqual]` | int | No | Updated on or after (Unix timestamp) |
| `filter[updatedAtLessThanOrEqual]` | int | No | Updated on or before (Unix timestamp) |
| `filter[expiresAtGreaterThanOrEqual]` | int | No | Expires on or after (Unix timestamp) |
| `filter[expiresAtLessThanOrEqual]` | int | No | Expires on or before (Unix timestamp) |
| `filter[orderBy]` | string | No | Sort: `+createdAt`, `-createdAt`, `+updatedAt`, `-updatedAt`, `+expiresAt`, `-expiresAt` |
| `pager[pageSize]` | int | No | Results per page (default 30, max 500) |
| `pager[pageIndex]` | int | No | Page number (default 1) |

```bash
curl -X POST "$KALTURA_SERVICE_URL/service/shortlink_shortlink/action/list" \
  -d "ks=$KALTURA_KS" \
  -d "format=1" \
  -d "filter[statusEqual]=2" \
  -d "filter[orderBy]=-createdAt" \
  -d "pager[pageSize]=10" \
  -d "pager[pageIndex]=1"
```

**Response:**

```json
{
  "objects": [
    {
      "id": "67mk41xj",
      "createdAt": 1778429631,
      "updatedAt": 1778429631,
      "partnerId": 1234567,
      "userId": "user@example.com",
      "systemName": "KMC-PREVIEW",
      "fullUrl": "https://www.kaltura.com/index.php/extwidget/preview/...",
      "status": 2,
      "objectType": "KalturaShortLink"
    }
  ],
  "totalCount": 70,
  "objectType": "KalturaShortLinkListResponse"
}
```

**User KS restriction:** With a user KS (type=0), the list is automatically scoped to that user's short links. An admin KS can list all short links or filter by any `userIdEqual`.

# 6. Update a Short Link

```
POST /service/shortlink_shortlink/action/update
```

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `id` | string | Yes | Short link ID to update |
| `shortLink[fullUrl]` | string | No | New destination URL |
| `shortLink[status]` | int | No | New status (1=DISABLED, 2=ENABLED) |
| `shortLink[expiresAt]` | int | No | New expiration timestamp |
| `shortLink[name]` | string | No | New display name |
| `shortLink[systemName]` | string | No | New system name |

```bash
curl -X POST "$KALTURA_SERVICE_URL/service/shortlink_shortlink/action/update" \
  -d "ks=$KALTURA_KS" \
  -d "format=1" \
  -d "id=$SHORT_LINK_ID" \
  -d "shortLink[objectType]=KalturaShortLink" \
  -d "shortLink[status]=1"
```

Setting `status=1` (DISABLED) prevents the link from resolving without deleting it.

# 7. Delete a Short Link

```
POST /service/shortlink_shortlink/action/delete
```

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `id` | string | Yes | Short link ID to delete |

```bash
curl -X POST "$KALTURA_SERVICE_URL/service/shortlink_shortlink/action/delete" \
  -d "ks=$KALTURA_KS" \
  -d "format=1" \
  -d "id=$SHORT_LINK_ID"
```

This is a soft delete — sets `status=3` (DELETED). The link stops resolving immediately.

Short links are also automatically deleted when their owner user is deleted from the system (cascade behavior).

# 8. Common Integration Patterns

## Preview and Share Links

The KMC (Rich Media CMS) creates short links for the embed preview page. The pattern:

1. Construct the full preview URL with partner ID, player uiconf, and entry ID
2. Create a short link with `systemName=KMC-PREVIEW`
3. Present the short URL (`/tiny/{id}`) to the user for sharing

```bash
FULL_URL="https://www.kaltura.com/index.php/extwidget/preview/partner_id/$KALTURA_PARTNER_ID/uiconf_id/$KALTURA_PLAYER_ID/entry_id/$KALTURA_ENTRY_ID/embed/dynamic"

curl -X POST "$KALTURA_SERVICE_URL/service/shortlink_shortlink/action/add" \
  -d "ks=$KALTURA_KS" \
  -d "format=1" \
  -d "shortLink[objectType]=KalturaShortLink" \
  -d "shortLink[systemName]=KMC-PREVIEW" \
  -d "shortLink[fullUrl]=$FULL_URL" \
  -d "shortLink[status]=2"
```

## Campaign Links with Expiration

Create time-limited links for marketing campaigns or review workflows:

```bash
EXPIRES_AT=$(date -d "+30 days" +%s 2>/dev/null || date -v+30d +%s)

curl -X POST "$KALTURA_SERVICE_URL/service/shortlink_shortlink/action/add" \
  -d "ks=$KALTURA_KS" \
  -d "format=1" \
  -d "shortLink[objectType]=KalturaShortLink" \
  -d "shortLink[systemName]=CAMPAIGN-Q4-2025" \
  -d "shortLink[fullUrl]=https://your-portal.kaltura.com/media/entry_id/$KALTURA_ENTRY_ID" \
  -d "shortLink[name]=Q4 Campaign Video" \
  -d "shortLink[status]=2" \
  -d "shortLink[expiresAt]=$EXPIRES_AT"
```

## Lookup by System Name

Use `systemNameEqual` filter to find short links by their programmatic identifier:

```bash
curl -X POST "$KALTURA_SERVICE_URL/service/shortlink_shortlink/action/list" \
  -d "ks=$KALTURA_KS" \
  -d "format=1" \
  -d "filter[systemNameEqual]=CAMPAIGN-Q4-2025" \
  -d "filter[statusEqual]=2"
```

## Bulk Cleanup of Expired Links

List and delete short links that have passed their expiration:

```bash
NOW=$(date +%s)

curl -X POST "$KALTURA_SERVICE_URL/service/shortlink_shortlink/action/list" \
  -d "ks=$KALTURA_KS" \
  -d "format=1" \
  -d "filter[statusEqual]=2" \
  -d "filter[expiresAtLessThanOrEqual]=$NOW" \
  -d "filter[expiresAtGreaterThanOrEqual]=1" \
  -d "pager[pageSize]=500"
```

# 9. Error Handling

| Error Code | Action | Description |
|------------|--------|-------------|
| `INVALID_OBJECT_ID` | get, update, delete, goto | Short link ID does not exist |
| `INVALID_SHORT_LINK` | goto | Link is DISABLED or DELETED |
| `EXPIRED_SHORT_LINK` | goto | Link has passed its `expiresAt` timestamp |
| `CANNOT_RETRIEVE_ANOTHER_USERS_SHORT_LINK` | list | User KS attempted to filter by a different user's links |
| `INVALID_USER_ID` | list | User KS with no `userId` set attempted to list |
| `PROPERTY_VALIDATION_MIN_LENGTH` | add | `systemName` < 3 chars or `fullUrl` < 10 chars |
| `MISSING_MANDATORY_PARAMETER` | add | `systemName` or `fullUrl` not provided |

# 10. Best Practices

- **Use descriptive `systemName` values.** Prefix with the context: `KMC-PREVIEW`, `CAMPAIGN-{name}`, `SHARE-{entryId}`. This enables filtering and bulk management.
- **Set `expiresAt` for temporary links.** Review links, campaign URLs, and time-sensitive access should always have an expiration. Use 0 (or omit) only for permanent links.
- **Disable rather than delete.** Set `status=1` (DISABLED) to temporarily revoke access while preserving the link for potential reactivation.
- **Use admin KS for cross-user management.** User KS can only see that user's short links. Use admin KS with `disableentitlement` for full account visibility.
- **The `goto` action is public.** It requires no authentication — treat short link IDs as semi-public identifiers. For sensitive content, rely on the destination URL's own access control (KS in player embed, access control profiles).
- **Store the `id` for programmatic access.** The short URL format is `https://{host}/tiny/{id}`. Construct it client-side after creating the link.

# 11. Related Guides

- **[Content Delivery API](KALTURA_CONTENT_DELIVERY_API.md)** — playManifest URLs and delivery profiles that short links often wrap
- **[Player Embed Guide](KALTURA_PLAYER_EMBED_GUIDE.md)** — Generate embed/preview URLs to shorten
- **[Session (KS) Guide](KALTURA_SESSION_GUIDE.md)** — KS generation for short link API access
- **[AppTokens API](KALTURA_APPTOKENS_API.md)** — Secure server-side auth for production short link services

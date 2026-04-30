# Kaltura Syndication Feeds API

Syndication feeds generate RSS/MRSS/XML feeds that external platforms pull via HTTP GET. Create a feed, configure its content scope and format, and share the feed URL — external platforms (Google, Apple Podcasts, Roku, news aggregators) fetch the XML on their own schedule. Feeds are stateless: Kaltura serves the current content each time the URL is requested.

**Base URL:** `https://www.kaltura.com/api_v3` (may differ by region/deployment)  
**Auth:** KS passed as `ks` parameter in POST form data (see [Session Guide](KALTURA_SESSION_GUIDE.md))  
**Format:** Form-encoded POST, `format=1` for JSON responses  
**Service:** `syndicationFeed`  

<!-- Sections: 1.When to Use | 2.Prerequisites | 3.Core Concepts | 4.syndicationFeed.add | 5.syndicationFeed.get | 6.syndicationFeed.list | 7.syndicationFeed.update | 8.syndicationFeed.delete | 9.syndicationFeed.getEntryCount | 10.Feed URL & XML Output | 11.Entry Filtering | 12.Feed Caching & Performance | 13.Error Handling | 14.Best Practices | 15.Common Integration Patterns | 16.API Actions Reference | 17.Related Guides -->


# 1. When to Use

- **RSS feed generation** — Automatically generate standards-compliant RSS/MRSS feeds from your Kaltura content library for distribution to external consumers  
- **Podcast distribution** — Publish audio and video content as iTunes-compatible podcast feeds for Apple Podcasts, Spotify, and other podcast platforms  
- **Content syndication to external platforms** — Distribute video content to Google (Video Sitemaps), Roku (Direct Publisher), and news aggregators via pull-based XML feeds  


# 2. Prerequisites

- A Kaltura account with an ADMIN KS (type=2) with `disableentitlement` privilege
- Syndication feed creation is available to all accounts — no additional plugin activation required


# 3. Core Concepts

## 3.1 How Syndication Feeds Work

1. **Create a feed** — choose a feed type (Google Video Sitemap, iTunes Podcast, MRSS, Roku) and optionally scope it to specific content
2. **Get the feed URL** — the API returns a `feedUrl` that serves XML at a public HTTP endpoint
3. **Share the URL** — register the feed URL with external platforms (Google Search Console, Apple Podcasts Connect, Roku Developer Dashboard)
4. **External platforms poll** — each platform fetches the feed on its own schedule; Kaltura serves the current content

## 3.2 Feed Types

| Type | Value | Object Type | Output Format |
|------|-------|-------------|---------------|
| Google Video Sitemap | 1 | `KalturaGoogleVideoSyndicationFeed` | XML sitemap with `<video:video>` elements |
| Yahoo MRSS | 2 | `KalturaYahooSyndicationFeed` | RSS 2.0 with `<media:*>` namespace |
| iTunes Podcast | 3 | `KalturaITunesSyndicationFeed` | RSS with `<itunes:*>` namespace |
| Flexible Format (XSLT) | 6 | `KalturaGenericXsltSyndicationFeed` | Custom XSLT-transformed MRSS |
| Roku Direct Publisher | 7 | `KalturaRokuSyndicationFeed` | Roku-specific MRSS |
| Opera TV | 8 | `KalturaOperaSyndicationFeed` | Opera TV format |

## 3.3 Feed Object Fields

Base fields (all feed types):

| Field | Type | Description |
|-------|------|-------------|
| `id` | string | Feed ID (auto-assigned, e.g., `1_abc12345`) |
| `feedUrl` | string | Public URL to fetch the feed XML |
| `name` | string | Feed display name |
| `type` | int | Feed type enum |
| `status` | int | Feed status |
| `playlistId` | string | Content filter — restrict to a specific playlist |
| `landingPage` | string | Template URL for video links (use `{entry_id}` placeholder) |
| `allowEmbed` | bool | Include embed URLs in feed |
| `enforceEntitlement` | bool | Apply access control to feed entries |
| `entryFilter` | object | `KalturaMediaEntryFilter` — filter by tags, mediaType, categories |
| `feedContentTypeHeader` | string | Response Content-Type (default: `text/xml; charset=utf-8`) |

**iTunes-specific fields:**

| Field | Description |
|-------|-------------|
| `feedDescription` | Channel description |
| `language` | Feed language code (e.g., `EN`) |
| `ownerName` | Podcast owner name |
| `ownerEmail` | Podcast owner email |
| `feedImageUrl` | Album art / channel logo URL |
| `feedAuthor` | Podcast author |
| `adultContent` | Explicit content flag |


# 4. syndicationFeed.add

Create a syndication feed. The `objectType` must match the desired feed type.

**Google Video Sitemap:**

```bash
curl -X POST "$KALTURA_SERVICE_URL/service/syndicationFeed/action/add" \
  -d "ks=$KALTURA_KS" \
  -d "format=1" \
  -d "syndicationFeed[objectType]=KalturaGoogleVideoSyndicationFeed" \
  -d "syndicationFeed[name]=Video Sitemap" \
  -d "syndicationFeed[type]=1" \
  -d "syndicationFeed[landingPage]=https://example.com/video/{entry_id}"
```

**Yahoo MRSS:**

```bash
curl -X POST "$KALTURA_SERVICE_URL/service/syndicationFeed/action/add" \
  -d "ks=$KALTURA_KS" \
  -d "format=1" \
  -d "syndicationFeed[objectType]=KalturaYahooSyndicationFeed" \
  -d "syndicationFeed[name]=MRSS Feed" \
  -d "syndicationFeed[type]=2"
```

**iTunes Podcast:**

```bash
curl -X POST "$KALTURA_SERVICE_URL/service/syndicationFeed/action/add" \
  -d "ks=$KALTURA_KS" \
  -d "format=1" \
  -d "syndicationFeed[objectType]=KalturaITunesSyndicationFeed" \
  -d "syndicationFeed[name]=My Podcast" \
  -d "syndicationFeed[type]=3" \
  -d "syndicationFeed[feedDescription]=A podcast feed for video content" \
  -d "syndicationFeed[language]=EN" \
  -d "syndicationFeed[ownerName]=Channel Owner" \
  -d "syndicationFeed[ownerEmail]=owner@example.com"
```

**Roku Direct Publisher:**

```bash
curl -X POST "$KALTURA_SERVICE_URL/service/syndicationFeed/action/add" \
  -d "ks=$KALTURA_KS" \
  -d "format=1" \
  -d "syndicationFeed[objectType]=KalturaRokuSyndicationFeed" \
  -d "syndicationFeed[name]=Roku Channel Feed" \
  -d "syndicationFeed[type]=7"
```

**Flexible Format (Generic XSLT):**

```bash
curl -X POST "$KALTURA_SERVICE_URL/service/syndicationFeed/action/add" \
  -d "ks=$KALTURA_KS" \
  -d "format=1" \
  -d "syndicationFeed[objectType]=KalturaGenericXsltSyndicationFeed" \
  -d "syndicationFeed[name]=Custom Feed" \
  -d "syndicationFeed[type]=6" \
  --data-urlencode 'syndicationFeed[xslt]=<?xml version="1.0"?><xsl:stylesheet version="1.0" xmlns:xsl="http://www.w3.org/1999/XSL/Transform"><xsl:output method="xml"/><xsl:template match="/"><feed><xsl:copy-of select="."/></feed></xsl:template></xsl:stylesheet>'
```

The Generic XSLT feed type requires an `xslt` parameter containing the XSLT stylesheet that transforms Kaltura's internal MRSS into the desired output format.

**Common parameters (all feed types):**

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `syndicationFeed[objectType]` | string | Yes | Must match the feed type: `KalturaGoogleVideoSyndicationFeed`, `KalturaYahooSyndicationFeed`, `KalturaITunesSyndicationFeed`, `KalturaGenericXsltSyndicationFeed`, `KalturaRokuSyndicationFeed`, `KalturaOperaSyndicationFeed` |
| `syndicationFeed[name]` | string | Yes | Feed display name |
| `syndicationFeed[type]` | integer | Yes | Feed type enum: 1=Google Video Sitemap, 2=Yahoo MRSS, 3=iTunes, 6=Generic XSLT, 7=Roku, 8=Opera TV |
| `syndicationFeed[landingPage]` | string | No | Template URL for video links — use `{entry_id}` placeholder (required for Google Video Sitemap to generate `<loc>` elements) |
| `syndicationFeed[playlistId]` | string | No | Restrict feed to entries in this playlist |
| `syndicationFeed[allowEmbed]` | boolean | No | Include embed URLs in feed entries |
| `syndicationFeed[enforceEntitlement]` | boolean | No | Apply access control to feed entries |
| `syndicationFeed[entryFilter][objectType]` | string | No | `KalturaMediaEntryFilter` — required if using entry filter fields |
| `syndicationFeed[entryFilter][tagsLike]` | string | No | Filter entries by tags |
| `syndicationFeed[feedContentTypeHeader]` | string | No | Response Content-Type header (default: `text/xml; charset=utf-8`) |

**iTunes-specific parameters** (type=3, `KalturaITunesSyndicationFeed`):

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `syndicationFeed[feedDescription]` | string | No | Podcast channel description |
| `syndicationFeed[language]` | string | No | Feed language code (e.g., `EN`) |
| `syndicationFeed[ownerName]` | string | No | Podcast owner name |
| `syndicationFeed[ownerEmail]` | string | No | Podcast owner email |
| `syndicationFeed[feedImageUrl]` | string | No | Album art / channel logo URL |
| `syndicationFeed[feedAuthor]` | string | No | Podcast author |
| `syndicationFeed[adultContent]` | string | No | Explicit content flag |

**Generic XSLT-specific parameters** (type=6, `KalturaGenericXsltSyndicationFeed`):

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `syndicationFeed[xslt]` | string | Yes | XSLT stylesheet that transforms Kaltura's internal MRSS into the desired output format |

**Response** includes the `feedUrl` for accessing the generated XML:

```json
{
  "id": "1_abc12345",
  "feedUrl": "https://www.kaltura.com/api_v3/getFeed.php?partnerId={PARTNER_ID}&feedId=1_abc12345",
  "name": "Video Sitemap",
  "type": 1,
  "objectType": "KalturaGoogleVideoSyndicationFeed"
}
```


# 5. syndicationFeed.get

Retrieve a syndication feed by ID:

```bash
curl -X POST "$KALTURA_SERVICE_URL/service/syndicationFeed/action/get" \
  -d "ks=$KALTURA_KS" \
  -d "format=1" \
  -d "id=$FEED_ID"
```

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `id` | string | Yes | Syndication feed ID (e.g., `1_abc12345`) |


# 6. syndicationFeed.list

List syndication feeds:

```bash
curl -X POST "$KALTURA_SERVICE_URL/service/syndicationFeed/action/list" \
  -d "ks=$KALTURA_KS" \
  -d "format=1"
```

All filter and pager parameters are optional. Omitting them returns all feeds on the account.

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `filter[objectType]` | string | No | `KalturaBaseSyndicationFeedFilter` or `KalturaSyndicationFeedFilter` |
| `filter[typeEqual]` | integer | No | Filter by feed type: 1=Google, 2=Yahoo, 3=iTunes, 6=Generic XSLT, 7=Roku, 8=Opera TV |
| `filter[orderBy]` | string | No | Sort field: `+createdAt`, `-createdAt`, `+name`, `-name` |
| `pager[pageSize]` | integer | No | Results per page (default 30, max 500) |
| `pager[pageIndex]` | integer | No | Page number, 1-based (default 1) |


# 7. syndicationFeed.update

Update a syndication feed:

```bash
curl -X POST "$KALTURA_SERVICE_URL/service/syndicationFeed/action/update" \
  -d "ks=$KALTURA_KS" \
  -d "format=1" \
  -d "id=$FEED_ID" \
  -d "syndicationFeed[objectType]=KalturaRokuSyndicationFeed" \
  -d "syndicationFeed[name]=Updated Feed Name"
```

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `id` | string | Yes | Syndication feed ID to update |
| `syndicationFeed[objectType]` | string | Yes | Must match the feed's original type (e.g., `KalturaRokuSyndicationFeed`) |
| `syndicationFeed[name]` | string | No | Updated feed name |
| `syndicationFeed[landingPage]` | string | No | Updated landing page URL template |
| `syndicationFeed[playlistId]` | string | No | Updated playlist scope |
| `syndicationFeed[allowEmbed]` | boolean | No | Updated embed URL inclusion |
| `syndicationFeed[enforceEntitlement]` | boolean | No | Updated entitlement enforcement |
| `syndicationFeed[entryFilter][objectType]` | string | No | `KalturaMediaEntryFilter` — required if updating entry filter |
| `syndicationFeed[entryFilter][tagsLike]` | string | No | Updated tag filter |

Pass only the fields to change. Fields not included remain unchanged. The `type` field is immutable and cannot be updated.


# 8. syndicationFeed.delete

Delete a syndication feed:

```bash
curl -X POST "$KALTURA_SERVICE_URL/service/syndicationFeed/action/delete" \
  -d "ks=$KALTURA_KS" \
  -d "format=1" \
  -d "id=$FEED_ID"
```

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `id` | string | Yes | Syndication feed ID to delete |


# 9. syndicationFeed.getEntryCount

Get the number of entries in a syndication feed:

```bash
curl -X POST "$KALTURA_SERVICE_URL/service/syndicationFeed/action/getEntryCount" \
  -d "ks=$KALTURA_KS" \
  -d "format=1" \
  -d "feedId=$FEED_ID"
```

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `feedId` | string | Yes | Syndication feed ID to count entries for |

**Response:**

```json
{
  "totalEntryCount": 27118,
  "actualEntryCount": 27118,
  "requireTranscodingCount": 0,
  "objectType": "KalturaSyndicationFeedEntryCount"
}
```

- `totalEntryCount` — entries matching the feed filter
- `actualEntryCount` — entries with required flavors available
- `requireTranscodingCount` — entries needing transcoding before inclusion


# 10. Feed URL & XML Output

All feeds are served at: `https://{service_url}/api_v3/getFeed.php?partnerId={PARTNER_ID}&feedId={FEED_ID}`

Append `&limit=N` to cap the number of entries returned (also reduces cache TTL from 24 hours to 30 minutes).

## 10.1 Roku MRSS Output

```xml
<rss xmlns:media="http://search.yahoo.com/mrss/" xmlns:atom="http://www.w3.org/2005/Atom"
     xmlns:dcterms="http://purl.org/dc/terms/" version="2.0">
  <channel>
    <title><![CDATA[Feed Name]]></title>
    <description><![CDATA[Description]]></description>
    <item>
      <guid isPermaLink="false">ENTRY_ID</guid>
      <title><![CDATA[Entry Title]]></title>
      <pubDate>Mon, 21 Jul 2014 07:20:18 -0400</pubDate>
      <media:content url="http://cdnapi.kaltura.com/.../playManifest/.../a.m3u8" duration="2969"/>
      <media:thumbnail url="https://cfvod.kaltura.com/.../thumbnail/.../width/800/height/450"/>
      <media:keywords><![CDATA[tag1, tag2]]></media:keywords>
    </item>
  </channel>
</rss>
```

## 10.2 iTunes Podcast RSS Output

```xml
<rss xmlns:itunes="http://www.itunes.com/dtds/podcast-1.0.dtd" version="2.0">
  <channel>
    <title>Feed Name</title>
    <language>EN</language>
    <itunes:owner>
      <itunes:name>Owner Name</itunes:name>
      <itunes:email>owner@example.com</itunes:email>
    </itunes:owner>
    <item>
      <title>Entry Title</title>
      <enclosure url="https://cfvod.kaltura.com/.../serveFlavor/.../name/a.mp4" type="video/mp4"/>
      <itunes:duration>1:58:18</itunes:duration>
      <itunes:image href="https://cfvod.kaltura.com/.../thumbnail/.../ext.jpg"/>
    </item>
  </channel>
</rss>
```

## 10.3 Google Video Sitemap Output

```xml
<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9"
        xmlns:video="http://www.google.com/schemas/sitemap-video/1.1">
  <url>
    <loc>https://example.com/video/ENTRY_ID</loc>
    <video:video>
      <video:title>Entry Title</video:title>
      <video:thumbnail_loc>https://cfvod.kaltura.com/.../thumbnail/...</video:thumbnail_loc>
      <video:content_loc>https://cfvod.kaltura.com/.../serveFlavor/...</video:content_loc>
    </video:video>
  </url>
</urlset>
```


# 11. Entry Filtering

Scope a syndication feed to specific content using `entryFilter` or `playlistId`.

**Filter by tags:**

```bash
curl -X POST "$KALTURA_SERVICE_URL/service/syndicationFeed/action/add" \
  -d "ks=$KALTURA_KS" \
  -d "format=1" \
  -d "syndicationFeed[objectType]=KalturaGoogleVideoSyndicationFeed" \
  -d "syndicationFeed[name]=Tagged Content Feed" \
  -d "syndicationFeed[type]=1" \
  -d "syndicationFeed[landingPage]=https://example.com/video/{entry_id}" \
  -d "syndicationFeed[entryFilter][objectType]=KalturaMediaEntryFilter" \
  -d "syndicationFeed[entryFilter][tagsLike]=webinar"
```

**Filter by playlist:**

```bash
curl -X POST "$KALTURA_SERVICE_URL/service/syndicationFeed/action/add" \
  -d "ks=$KALTURA_KS" \
  -d "format=1" \
  -d "syndicationFeed[objectType]=KalturaYahooSyndicationFeed" \
  -d "syndicationFeed[name]=Playlist Feed" \
  -d "syndicationFeed[type]=2" \
  -d "syndicationFeed[playlistId]=$PLAYLIST_ID"
```

Feeds without a `playlistId` or `entryFilter` include all account entries.


# 12. Feed Caching & Performance

- Default feed cache TTL: **24 hours**
- Adding `&limit=N` to the feed URL reduces cache to **30 minutes** and caps at N items
- Special characters in entry metadata are XML-escaped automatically
- Feeds without content filters on large accounts can include tens of thousands of entries — use `playlistId` or `entryFilter` to scope appropriately
- Google Video Sitemap feeds require a valid `landingPage` URL to generate `<loc>` elements


# 13. Error Handling

| Error Code | Meaning | Resolution |
|------------|---------|------------|
| `INVALID_FEED_ID` | Feed ID does not exist | Verify the feed ID |
| `PROPERTY_VALIDATION_CANNOT_BE_NULL` | A required field is missing (e.g., `objectType`) | Add the required parameter |
| `PROPERTY_VALIDATION_NOT_UPDATABLE` | Attempted to update an immutable field | Check which fields are read-only for the feed type |
| `SERVICE_FORBIDDEN` | KS lacks required permissions | Use an admin KS with `disableentitlement` |
| `INVALID_KS` | KS is invalid, expired, or lacks privileges | Generate a fresh admin KS |

**Retry strategy:** For transient errors (HTTP 5xx, timeouts), retry with exponential backoff: 1s, 2s, 4s, with jitter, up to 3 retries. For client errors (`INVALID_FEED_ID`, `PROPERTY_VALIDATION_*`), fix the request before retrying.


# 14. Best Practices

- **Scope feeds with filters.** Use `playlistId` or `entryFilter` to limit feed content — unscoped feeds on large accounts return all entries.
- **Add `&limit=N` to feed URLs for testing.** This reduces the cache TTL to 30 minutes and caps entries, making iteration faster during development.
- **Use HTTPS for feed URLs.** The `feedUrl` returned by the API uses `http://` — convert to `https://` in production.
- **Match objectType to feed type.** The `objectType` in `syndicationFeed.add` must correspond to the `type` value — mismatches cause validation errors.
- **Use iTunes-specific fields for podcasts.** Set `feedDescription`, `language`, `ownerName`, and `ownerEmail` for Apple Podcasts compliance.
- **Set a landingPage for Google Video Sitemaps.** The `{entry_id}` placeholder in `landingPage` generates the `<loc>` URLs that Google indexes.


# 15. Common Integration Patterns

## 15.1 Google Video Sitemap for SEO

Generate a Google-compatible video sitemap for search engine indexing:

```bash
# Create a Google Video Sitemap feed scoped to published content
curl -X POST "$KALTURA_SERVICE_URL/service/syndicationFeed/action/add" \
  -d "ks=$KALTURA_KS" \
  -d "format=1" \
  -d "syndicationFeed[objectType]=KalturaGoogleVideoSyndicationFeed" \
  -d "syndicationFeed[name]=Video Sitemap - Published" \
  -d "syndicationFeed[type]=1" \
  -d "syndicationFeed[landingPage]=https://mysite.com/watch/{entry_id}" \
  -d "syndicationFeed[entryFilter][objectType]=KalturaMediaEntryFilter" \
  -d "syndicationFeed[entryFilter][tagsLike]=published"
```

Submit the feed URL to Google Search Console as a video sitemap.

## 15.2 Podcast Feed Generation

Create an iTunes-compatible podcast feed:

```bash
curl -X POST "$KALTURA_SERVICE_URL/service/syndicationFeed/action/add" \
  -d "ks=$KALTURA_KS" \
  -d "format=1" \
  -d "syndicationFeed[objectType]=KalturaITunesSyndicationFeed" \
  -d "syndicationFeed[name]=Company Podcast" \
  -d "syndicationFeed[type]=3" \
  -d "syndicationFeed[feedDescription]=Weekly insights from our team" \
  -d "syndicationFeed[language]=EN" \
  -d "syndicationFeed[ownerName]=My Company" \
  -d "syndicationFeed[ownerEmail]=podcast@example.com" \
  -d "syndicationFeed[playlistId]=$PODCAST_PLAYLIST_ID"
```

Use `playlistId` to restrict the podcast to a curated playlist of episodes.

## 15.3 Content Syndication for News and Media

Create multiple feed formats for different distribution channels:

```bash
# MRSS for news aggregators
curl -X POST "$KALTURA_SERVICE_URL/service/syndicationFeed/action/add" \
  -d "ks=$KALTURA_KS" \
  -d "format=1" \
  -d "syndicationFeed[objectType]=KalturaYahooSyndicationFeed" \
  -d "syndicationFeed[name]=News Video Feed" \
  -d "syndicationFeed[type]=2" \
  -d "syndicationFeed[entryFilter][objectType]=KalturaMediaEntryFilter" \
  -d "syndicationFeed[entryFilter][tagsLike]=news"

# Roku feed for OTT
curl -X POST "$KALTURA_SERVICE_URL/service/syndicationFeed/action/add" \
  -d "ks=$KALTURA_KS" \
  -d "format=1" \
  -d "syndicationFeed[objectType]=KalturaRokuSyndicationFeed" \
  -d "syndicationFeed[name]=Roku Channel" \
  -d "syndicationFeed[type]=7" \
  -d "syndicationFeed[entryFilter][objectType]=KalturaMediaEntryFilter" \
  -d "syndicationFeed[entryFilter][tagsLike]=featured"
```

## 15.4 Webhook-Triggered Feed Refresh

Combine syndication with [webhooks](KALTURA_EVENT_NOTIFICATIONS_WEBHOOK_AND_EMAIL_API.md) for proactive cache management. Set up a webhook that fires when new content is published, then programmatically add `&limit=N` to your feed URL to trigger a 30-minute cache window — ensuring external platforms see new content sooner than the default 24-hour cache.


# 16. API Actions Reference

| Service | Action | Description |
|---------|--------|-------------|
| `syndicationFeed` | `add` | Create syndication feed |
| `syndicationFeed` | `get` | Get feed by ID |
| `syndicationFeed` | `list` | List feeds |
| `syndicationFeed` | `update` | Update feed config |
| `syndicationFeed` | `delete` | Delete feed |
| `syndicationFeed` | `getEntryCount` | Count entries in feed |


# 17. Related Guides

- **[Session Guide](KALTURA_SESSION_GUIDE.md)** — KS generation and management
- **[Content Distribution API](KALTURA_DISTRIBUTION_API.md)** — Push content to external platforms via connectors (push model vs syndication's pull model)
- **[Upload & Ingestion API](KALTURA_UPLOAD_AND_INGESTION_API.md)** — Content upload, flavors, and ingestion (entries that appear in feeds)
- **[Webhooks API](KALTURA_EVENT_NOTIFICATIONS_WEBHOOK_AND_EMAIL_API.md)** — Event-driven automation (trigger feed cache refresh on content events)
- **[Categories & Entitlements API](KALTURA_CATEGORIES_AND_ENTITLEMENTS_API.md)** — Content organization (used in feed entry filtering)
- **[eSearch API](KALTURA_ESEARCH_API.md)** — Full-text search (alternative to feed-based content discovery)

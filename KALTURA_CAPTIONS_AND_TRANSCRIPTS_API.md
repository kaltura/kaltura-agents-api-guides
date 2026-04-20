# Kaltura Captions & Transcripts API

The Captions & Transcripts API manages subtitle files, closed captions, and transcripts attached to media entries. It supports five caption formats (SRT, DFXP/TTML, WebVTT, CAP, SCC), on-the-fly format conversion, HLS segmented delivery, JSON serving for AI/LLM integrations, caption parameter templates, and multi-language workflows. For automated captioning, translation, and dubbing, see the [REACH API](KALTURA_REACH_API.md).

**Base URL:** `https://www.kaltura.com/api_v3` (may differ by region/deployment)  
**Auth:** KS passed as `ks` parameter in POST form data (see [Session Guide](KALTURA_SESSION_GUIDE.md))  
**Format:** Form-encoded POST, `format=1` for JSON responses  
**Services:** `caption_captionAsset` (12 actions), `caption_captionParams` (5 actions)  

**Important:** These are plugin services. The service names use underscore-prefixed compound names: `caption_captionAsset`, `caption_captionParams`.  


# 1. When to Use

- **Accessibility compliance teams** ensuring all video content meets WCAG, ADA, Section 508, or CVAA captioning requirements  
- **Content teams** adding searchable captions and transcripts to improve video discoverability across libraries  
- **Localization workflows** managing multi-language subtitle tracks for global audiences  
- **AI and automation pipelines** retrieving caption data as JSON for RAG, summarization, or knowledge-base ingestion  
- **LMS and training platforms** providing synchronized transcripts for lecture recordings and compliance training


# 2. Prerequisites

- **KS type:** ADMIN KS (type=2) with `CAPTION_PLUGIN_PERMISSION` and `CONTENT_MANAGE_BASE` permissions  
- **Plugins:** Caption plugin enabled on the partner account  
- **Session guide:** Generate a KS using `session.start` or `appToken.startSession` (see [Session Guide](KALTURA_SESSION_GUIDE.md))


# 3. Authentication

All endpoints require an ADMIN KS (type=2) with appropriate permissions:

- **Caption assets:** `CAPTION_PLUGIN_PERMISSION` + `CONTENT_MANAGE_BASE`
- **Caption parameters:** `CAPTION_PLUGIN_PERMISSION` + `ADMIN_BASE`

Generate an ADMIN KS via `session.start` (see [Session Guide](KALTURA_SESSION_GUIDE.md)) or `appToken.startSession` (see [AppTokens Guide](KALTURA_APPTOKENS_API.md)).

```bash
# Set up environment
export KALTURA_SERVICE_URL="https://www.kaltura.com/api_v3"
```


# 4. Caption Formats

## 4.1 Supported Formats

| Value | Name | Description |
|-------|------|-------------|
| 1 | SRT | SubRip subtitle format |
| 2 | DFXP | Distribution Format Exchange Profile (TTML/XML) |
| 3 | WEBVTT | Web Video Text Tracks (W3C standard) |
| 4 | CAP | Cheetah CAP (broadcast systems) |
| 5 | SCC | Scenarist Closed Captions (CEA-608, broadcast TV) |

## 4.2 Format Comparison

| Format | Best For | Styling | Positioning | Standard |
|--------|----------|---------|-------------|----------|
| SRT | Universal compatibility | Basic HTML (`<b>`, `<i>`) | No | De facto |
| WebVTT | HTML5 video, web players | CSS cue styling | Yes (line, position, align) | W3C |
| DFXP/TTML | OTT/Netflix, broadcast | Full XML styling, regions | Yes (precise regions) | W3C/SMPTE |
| SCC | Broadcast TV (CEA-608) | Roll-up/pop-on modes | Yes (row/column) | FCC |
| CAP | Broadcast (Cheetah systems) | System-specific | System-specific | Proprietary |

## 4.3 SRT Format Reference

```
1
00:00:00,000 --> 00:00:05,000
Welcome to the presentation.

2
00:00:05,000 --> 00:00:10,000
Today we cover the Kaltura API.
<i>Let's get started.</i>
```

Timing format: `HH:MM:SS,mmm --> HH:MM:SS,mmm`. Supports `<b>`, `<i>`, `<u>` HTML tags. Blank line separates cues.

## 4.4 WebVTT Format Reference

```
WEBVTT

00:00:00.000 --> 00:00:05.000 position:10% align:start
Welcome to the presentation.

00:00:05.000 --> 00:00:10.000
<v Speaker>Today we cover the Kaltura API.</v>
```

Requires `WEBVTT` header on first line. Timing uses `.` (not `,`). Supports cue settings (`position`, `line`, `align`, `size`), speaker identification (`<v>`), and CSS styling.

## 4.5 DFXP/TTML Format Reference

```xml
<?xml version="1.0" encoding="UTF-8"?>
<tt xmlns="http://www.w3.org/ns/ttml" xml:lang="en">
  <body>
    <div>
      <p begin="00:00:00.000" end="00:00:05.000">Welcome to the presentation.</p>
      <p begin="00:00:05.000" end="00:00:10.000">Today we cover the Kaltura API.</p>
    </div>
  </body>
</tt>
```

XML-based format with full region support, multi-language tracks in a single file, and precise styling via TTML profiles.

## 4.6 Browser/Player Compatibility

WebVTT is natively supported by all modern browsers. Kaltura Player v7 auto-converts all formats to WebVTT for display using `serveWebVTT`. Store captions in any supported format — the player handles conversion.

## 4.7 Format Conversion Behavior

- **SCC to SRT:** Auto-converted on upload via server batch job. SCC positioning data (row/column) is lost in the conversion.
- **Any format to WebVTT:** On-the-fly conversion via `captionAsset.serveWebVTT`. TTML regions and SCC positioning are simplified.
- **Any format to JSON:** On-the-fly conversion via `captionAsset.serveAsJson`. Structured output for programmatic consumption.

## 4.8 Caption Languages

Use `KalturaLanguage` enum values — human-readable language names: `"English"`, `"Spanish"`, `"French"`, `"German"`, `"Japanese"`, `"Chinese"`, `"Arabic"`, `"Portuguese"`, `"Russian"`, `"Korean"`, `"Italian"`, `"Dutch"`, `"Hebrew"`, `"Hindi"`, etc. (300+ languages supported).

The `languageCode` field is automatically derived as a read-only ISO 639 code from the `language` value.


# 5. Caption Asset CRUD

A `KalturaCaptionAsset` represents a subtitle or caption file attached to a media entry. Caption creation is a two-step process: first create the asset metadata (`captionAsset.add`), then upload the content (`captionAsset.setContent`).

## 5.1 KalturaCaptionAsset Object

| Field | Type | Description |
|-------|------|-------------|
| `id` | string | Auto-generated asset ID (read-only) |
| `entryId` | string | Media entry this caption belongs to |
| `label` | string | Display label (e.g., "English", "Spanish CC") |
| `language` | string | Language from KalturaLanguage enum (e.g., `"English"`) |
| `languageCode` | string | ISO 639 code, auto-derived from language (read-only) |
| `format` | integer | Caption format: 1=SRT, 2=DFXP, 3=WebVTT, 4=CAP, 5=SCC (insertOnly) |
| `status` | integer | Asset status (see 3.2) |
| `isDefault` | boolean | Whether this is the default caption for the entry |
| `accuracy` | integer | Accuracy percentage (for machine-generated captions) |
| `displayOnPlayer` | boolean | Whether the player shows this caption track |
| `captionParamsId` | integer | Caption parameter template ID (insertOnly) |
| `source` | integer | Origin: `0`=UNKNOWN, `1`=ZOOM, `2`=WEBEX (insertOnly) |
| `parentId` | string | Parent caption asset ID (insertOnly, for derived captions) |
| `associatedTranscriptIds` | string | Comma-separated IDs of linked transcript assets |
| `usage` | integer | `0`=CAPTION, `1`=EXTENDED_AUDIO_DESCRIPTION |
| `size` | integer | File size in bytes (read-only) |
| `version` | integer | Version number (read-only) |
| `partnerId` | integer | Partner ID (read-only) |
| `createdAt` | integer | Unix timestamp (read-only) |
| `updatedAt` | integer | Unix timestamp (read-only) |
| `objectType` | string | Always `"KalturaCaptionAsset"` (read-only) |

## 5.2 Caption Status Values

| Value | Name | Description |
|-------|------|-------------|
| -1 | ERROR | Processing error |
| 0 | QUEUED | Queued for processing |
| 2 | READY | Ready for use |
| 3 | DELETED | Soft-deleted |
| 7 | IMPORTING | Being imported from URL |
| 9 | EXPORTING | Being exported |

## 5.3 Create Caption Asset

```
POST /service/caption_captionAsset/action/add
```

```bash
curl -X POST "$KALTURA_SERVICE_URL/service/caption_captionAsset/action/add" \
  -d "ks=$KALTURA_KS" \
  -d "format=1" \
  -d "entryId=$ENTRY_ID" \
  -d "captionAsset[objectType]=KalturaCaptionAsset" \
  -d "captionAsset[label]=English" \
  -d "captionAsset[language]=English" \
  -d "captionAsset[format]=1" \
  -d "captionAsset[isDefault]=1"
```

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `entryId` | string | Yes | Media entry ID |
| `captionAsset[objectType]` | string | Yes | Always `KalturaCaptionAsset` |
| `captionAsset[label]` | string | No | Display label |
| `captionAsset[language]` | string | Yes | Language (KalturaLanguage enum value) |
| `captionAsset[format]` | integer | No | `1`=SRT (default), `2`=DFXP, `3`=WEBVTT, `4`=CAP, `5`=SCC. insertOnly — cannot change after creation. |
| `captionAsset[isDefault]` | boolean | No | Set as default caption for the entry |
| `captionAsset[captionParamsId]` | integer | No | Template ID — language and label auto-copied from template |

**Response:** `KalturaCaptionAsset` object with generated `id` and `status=0` (QUEUED). The format defaults to SRT (1) if not specified.

```json
{
  "id": "1_abc123de",
  "entryId": "0_xyz789ab",
  "partnerId": 1234567,
  "label": "English",
  "language": "English",
  "languageCode": "en",
  "format": 1,
  "status": 0,
  "isDefault": true,
  "displayOnPlayer": true,
  "accuracy": 0,
  "size": 0,
  "version": 0,
  "createdAt": 1712620800,
  "updatedAt": 1712620800,
  "objectType": "KalturaCaptionAsset"
}
```

## 5.4 Upload Content (Inline String)

After creating the asset, upload the caption content using `KalturaStringResource` for small files (<1 MB):

```bash
curl -X POST "$KALTURA_SERVICE_URL/service/caption_captionAsset/action/setContent" \
  -d "ks=$KALTURA_KS" \
  -d "format=1" \
  -d "id=$CAPTION_ASSET_ID" \
  -d "contentResource[objectType]=KalturaStringResource" \
  --data-urlencode 'contentResource[content]=1
00:00:00,000 --> 00:00:05,000
Welcome to the presentation.

2
00:00:05,000 --> 00:00:10,000
Today we cover the Kaltura API.'
```

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `id` | string | Yes | Caption asset ID (from `captionAsset.add`) |
| `contentResource[objectType]` | string | Yes | `KalturaStringResource` for inline content |
| `contentResource[content]` | string | Yes | Caption file content (URL-encode for special characters) |

**Response:** Updated `KalturaCaptionAsset` object. Status transitions to `2` (READY) after processing.

```json
{
  "id": "1_abc123de",
  "entryId": "0_xyz789ab",
  "partnerId": 1234567,
  "label": "English",
  "language": "English",
  "languageCode": "en",
  "format": 1,
  "status": 2,
  "isDefault": true,
  "displayOnPlayer": true,
  "size": 142,
  "version": 1,
  "createdAt": 1712620800,
  "updatedAt": 1712620860,
  "objectType": "KalturaCaptionAsset"
}
```

## 5.5 Upload Content (Upload Token)

For larger files, use the three-step upload token flow:

```bash
# Step 1: Create upload token
curl -X POST "$KALTURA_SERVICE_URL/service/uploadToken/action/add" \
  -d "ks=$KALTURA_KS" \
  -d "format=1" \
  -d "uploadToken[objectType]=KalturaUploadToken"

# Step 2: Upload file to token
curl -X POST "$KALTURA_SERVICE_URL/service/uploadToken/action/upload" \
  -d "ks=$KALTURA_KS" \
  -d "format=1" \
  -d "uploadTokenId=$UPLOAD_TOKEN_ID" \
  -F "fileData=@captions.srt"

# Step 3: Attach to caption asset
curl -X POST "$KALTURA_SERVICE_URL/service/caption_captionAsset/action/setContent" \
  -d "ks=$KALTURA_KS" \
  -d "format=1" \
  -d "id=$CAPTION_ASSET_ID" \
  -d "contentResource[objectType]=KalturaUploadedFileTokenResource" \
  -d "contentResource[token]=$UPLOAD_TOKEN_ID"
```

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `id` | string | Yes | Caption asset ID (from `captionAsset.add`) |
| `contentResource[objectType]` | string | Yes | `KalturaUploadedFileTokenResource` for upload token |
| `contentResource[token]` | string | Yes | Upload token ID (from `uploadToken.upload`) |

See [Upload & Ingestion API](KALTURA_UPLOAD_AND_INGESTION_API.md) for upload token details.

## 5.6 Upload Content (Remote URL)

Server fetches caption from a URL. Creates an async import job:

```bash
curl -X POST "$KALTURA_SERVICE_URL/service/caption_captionAsset/action/setContent" \
  -d "ks=$KALTURA_KS" \
  -d "format=1" \
  -d "id=$CAPTION_ASSET_ID" \
  -d "contentResource[objectType]=KalturaUrlResource" \
  -d "contentResource[url]=https://example.com/captions/english.srt"
```

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `id` | string | Yes | Caption asset ID (from `captionAsset.add`) |
| `contentResource[objectType]` | string | Yes | `KalturaUrlResource` for remote URL import |
| `contentResource[url]` | string | Yes | Direct URL to the caption file |

Status transitions to `7` (IMPORTING) during fetch, then `2` (READY) on completion.

## 5.7 Get Caption Asset

```bash
curl -X POST "$KALTURA_SERVICE_URL/service/caption_captionAsset/action/get" \
  -d "ks=$KALTURA_KS" \
  -d "format=1" \
  -d "captionAssetId=$CAPTION_ASSET_ID"
```

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `captionAssetId` | string | Yes | Caption asset ID to retrieve |

**Response:** Full `KalturaCaptionAsset` object. Use to poll for status after `setContent`.

## 5.8 List Caption Assets

```bash
curl -X POST "$KALTURA_SERVICE_URL/service/caption_captionAsset/action/list" \
  -d "ks=$KALTURA_KS" \
  -d "format=1" \
  -d "filter[objectType]=KalturaAssetFilter" \
  -d "filter[entryIdEqual]=$ENTRY_ID"
```

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `filter[objectType]` | string | Yes | `KalturaAssetFilter` or `KalturaCaptionAssetFilter` |
| `filter[entryIdEqual]` | string | Recommended | Filter by entry ID |
| `pager[pageSize]` | integer | No | Results per page (default 30, max 500) |
| `pager[pageIndex]` | integer | No | Page number (1-based, default 1) |

**Filter fields (`KalturaCaptionAssetFilter`):**

| Field | Description |
|-------|-------------|
| `entryIdEqual` / `entryIdIn` | Filter by entry ID (recommended) |
| `formatEqual` / `formatIn` | Filter by caption format |
| `statusEqual` / `statusIn` / `statusNotIn` | Filter by status |
| `captionParamsIdEqual` / `captionParamsIdIn` | Filter by template |
| `sizeGreaterThanOrEqual` / `sizeLessThanOrEqual` | Filter by file size |
| `createdAtGreaterThanOrEqual` / `createdAtLessThanOrEqual` | Date range |
| `updatedAtGreaterThanOrEqual` / `updatedAtLessThanOrEqual` | Date range |
| `tagsLike` | Tag-based search |
| `orderBy` | `+size`, `-size`, `+createdAt`, `-createdAt` |

**Response:**

```json
{
  "totalCount": 2,
  "objects": [
    {
      "id": "1_abc123",
      "entryId": "0_abc123",
      "label": "English",
      "language": "English",
      "languageCode": "en",
      "format": 1,
      "status": 2,
      "isDefault": true,
      "objectType": "KalturaCaptionAsset"
    }
  ],
  "objectType": "KalturaCaptionAssetListResponse"
}
```

## 5.9 Update Caption Asset

```bash
curl -X POST "$KALTURA_SERVICE_URL/service/caption_captionAsset/action/update" \
  -d "ks=$KALTURA_KS" \
  -d "format=1" \
  -d "id=$CAPTION_ASSET_ID" \
  -d "captionAsset[objectType]=KalturaCaptionAsset" \
  -d "captionAsset[label]=English (Corrected)"
```

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `id` | string | Yes | Caption asset ID |
| `captionAsset[objectType]` | string | Yes | Always `KalturaCaptionAsset` |
| `captionAsset[label]` | string | No | Updated label |
| `captionAsset[language]` | string | No | Updated language |
| `captionAsset[isDefault]` | boolean | No | Update default status |

**Response:** Updated `KalturaCaptionAsset` object.

```json
{
  "id": "1_abc123de",
  "entryId": "0_xyz789ab",
  "partnerId": 1234567,
  "label": "English (Corrected)",
  "language": "English",
  "languageCode": "en",
  "format": 1,
  "status": 2,
  "isDefault": true,
  "displayOnPlayer": true,
  "size": 142,
  "version": 2,
  "createdAt": 1712620800,
  "updatedAt": 1712621400,
  "objectType": "KalturaCaptionAsset"
}
```

The `format` field is insertOnly and cannot be changed after creation.

## 5.10 Set as Default Caption

```bash
curl -X POST "$KALTURA_SERVICE_URL/service/caption_captionAsset/action/setAsDefault" \
  -d "ks=$KALTURA_KS" \
  -d "format=1" \
  -d "captionAssetId=$CAPTION_ASSET_ID"
```

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `captionAssetId` | string | Yes | Caption asset ID to set as default |

Marks this caption asset as the default for its entry. Automatically unsets the previous default. Returns no response body on success.

## 5.11 Delete Caption Asset

```bash
curl -X POST "$KALTURA_SERVICE_URL/service/caption_captionAsset/action/delete" \
  -d "ks=$KALTURA_KS" \
  -d "format=1" \
  -d "captionAssetId=$CAPTION_ASSET_ID"
```

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `captionAssetId` | string | Yes | Caption asset ID to delete |

Returns no response body on success. The caption asset status transitions to `3` (DELETED).


# 6. Serving Captions

## 6.1 Serve Raw

Returns the caption content in its original format (SRT, DFXP, etc.):

```bash
curl "$KALTURA_SERVICE_URL/service/caption_captionAsset/action/serve?ks=$KALTURA_KS&captionAssetId=$CAPTION_ASSET_ID"
```

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `captionAssetId` | string | Yes | Caption asset ID to serve |

Returns a redirect to the CDN URL. Follow the redirect to get the raw content. The response Content-Type matches the caption format.

## 6.2 Serve as WebVTT

Converts any caption format to WebVTT on the fly. Supports HLS segmented delivery:

```bash
# Get HLS M3U8 playlist (segmentIndex omitted or null)
curl "$KALTURA_SERVICE_URL/service/caption_captionAsset/action/serveWebVTT?ks=$KALTURA_KS&captionAssetId=$CAPTION_ASSET_ID"

# Get a specific WebVTT segment
curl "$KALTURA_SERVICE_URL/service/caption_captionAsset/action/serveWebVTT?ks=$KALTURA_KS&captionAssetId=$CAPTION_ASSET_ID&segmentIndex=0"
```

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `captionAssetId` | string | — | Caption asset ID |
| `segmentDuration` | integer | 30 | Duration of each segment in seconds |
| `segmentIndex` | integer | null | Segment number. `null` returns M3U8 playlist (`application/x-mpegurl`). Integer returns WebVTT segment (`text/vtt`). |
| `localTimestamp` | integer | 10000 | Local timestamp offset |

**HLS delivery flow:**
1. Player requests M3U8 manifest via `serveWebVTT` (no `segmentIndex`)
2. Response is an HLS playlist with segment URLs
3. Player fetches individual WebVTT segments as needed

## 6.3 Serve as JSON

Returns structured JSON with timestamps in milliseconds. Ideal for AI/LLM integrations, RAG pipelines, and programmatic caption analysis:

```bash
curl -X POST "$KALTURA_SERVICE_URL/service/caption_captionAsset/action/serveAsJson" \
  -d "ks=$KALTURA_KS" \
  -d "format=1" \
  -d "captionAssetId=$CAPTION_ASSET_ID"
```

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `captionAssetId` | string | Yes | Caption asset ID to serve as JSON |

**Response:**

```json
{
  "objects": [
    {
      "startTime": 0,
      "endTime": 5000,
      "content": [{"text": "Welcome to the presentation."}]
    },
    {
      "startTime": 5000,
      "endTime": 10000,
      "content": [{"text": "Today we cover the Kaltura API."}]
    }
  ]
}
```

Times are in milliseconds. Maximum source file size: 1 MB. For larger files, use `serve` or `serveWebVTT`.

## 6.4 Serve by Entry ID

Serve the default caption for an entry without looking up the caption asset ID:

```bash
curl "$KALTURA_SERVICE_URL/service/caption_captionAsset/action/serveByEntryId?ks=$KALTURA_KS&entryId=$ENTRY_ID"
```

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `entryId` | string | Yes | Media entry ID |
| `captionParamId` | integer | No | Target a specific template instead of the default |

Returns raw caption content for the entry's default caption asset. If no default caption exists, the call returns an error.

## 6.5 Get Download URL

```bash
curl -X POST "$KALTURA_SERVICE_URL/service/caption_captionAsset/action/getUrl" \
  -d "ks=$KALTURA_KS" \
  -d "format=1" \
  -d "id=$CAPTION_ASSET_ID"
```

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `id` | string | Yes | Caption asset ID |
| `storageId` | integer | No | Storage profile ID (for multi-CDN setups) |

**Response:** A direct CDN download URL string (JSON-encoded):

```json
"https://cfvod.kaltura.com/api_v3/service/caption_captionAsset/action/serve/captionAssetId/1_abc123de/ks/..."
```

Use `getUrl` + HTTP fetch for server-side consumption — `serve` returns a redirect which requires follow-redirect handling.


# 7. Caption Parameters (Templates)

Caption parameter templates define reusable presets for caption assets. When `captionAsset.add` includes a `captionParamsId`, language and label are auto-copied from the template.

## 7.1 KalturaCaptionParams Object

| Field | Type | Description |
|-------|------|-------------|
| `id` | integer | Auto-generated ID (read-only) |
| `name` | string | Template name |
| `systemName` | string | Machine-friendly identifier |
| `description` | string | Description |
| `language` | string | Default language (insertOnly) |
| `isDefault` | boolean | Whether this is the default template |
| `label` | string | Default display label |
| `format` | integer | Default caption format (insertOnly) |
| `sourceParamsId` | integer | Source params for conversion |
| `tags` | string | Tags for filtering |
| `partnerId` | integer | Partner ID (read-only) |

## 7.2 Create Caption Params

```bash
curl -X POST "$KALTURA_SERVICE_URL/service/caption_captionParams/action/add" \
  -d "ks=$KALTURA_KS" \
  -d "format=1" \
  -d "captionParams[objectType]=KalturaCaptionParams" \
  -d "captionParams[name]=English SRT Template" \
  -d "captionParams[systemName]=en_srt_template" \
  -d "captionParams[language]=English" \
  -d "captionParams[format]=1" \
  -d "captionParams[isDefault]=1"
```

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `captionParams[objectType]` | string | Yes | Always `KalturaCaptionParams` |
| `captionParams[name]` | string | Yes | Template name |
| `captionParams[systemName]` | string | No | Machine-friendly identifier |
| `captionParams[language]` | string | No | Default language (insertOnly) |
| `captionParams[format]` | integer | No | Default caption format: `1`=SRT, `2`=DFXP, `3`=WEBVTT (insertOnly) |
| `captionParams[label]` | string | No | Default display label |
| `captionParams[isDefault]` | boolean | No | Set as default template |
| `captionParams[tags]` | string | No | Tags for filtering |
| `captionParams[description]` | string | No | Template description |
| `captionParams[sourceParamsId]` | integer | No | Source params for conversion |

**Response:** `KalturaCaptionParams` object with generated `id`.

```json
{
  "id": 12345,
  "partnerId": 1234567,
  "name": "English SRT Template",
  "systemName": "en_srt_template",
  "language": "English",
  "format": 1,
  "label": "English Subtitles",
  "isDefault": 1,
  "objectType": "KalturaCaptionParams"
}
```

## 7.3 Get / List / Update / Delete

```bash
# Get
curl -X POST "$KALTURA_SERVICE_URL/service/caption_captionParams/action/get" \
  -d "ks=$KALTURA_KS" \
  -d "format=1" \
  -d "id=$CAPTION_PARAMS_ID"

# List
curl -X POST "$KALTURA_SERVICE_URL/service/caption_captionParams/action/list" \
  -d "ks=$KALTURA_KS" \
  -d "format=1"

# Update
curl -X POST "$KALTURA_SERVICE_URL/service/caption_captionParams/action/update" \
  -d "ks=$KALTURA_KS" \
  -d "format=1" \
  -d "id=$CAPTION_PARAMS_ID" \
  -d "captionParams[objectType]=KalturaCaptionParams" \
  -d "captionParams[label]=English Subtitles"

# Delete
curl -X POST "$KALTURA_SERVICE_URL/service/caption_captionParams/action/delete" \
  -d "ks=$KALTURA_KS" \
  -d "format=1" \
  -d "id=$CAPTION_PARAMS_ID"
```

## 7.4 Template Inheritance

When `captionAsset.add` includes `captionParamsId`, the server auto-copies `language` and `label` from the template via `setFromAssetParams()`. This ensures consistency when creating caption assets programmatically across many entries.


# 8. Transcripts

## 8.1 Transcript vs Caption

- **Caption (KalturaCaptionAsset):** Timed text segments with start/end timestamps. Displayed as subtitles during playback.
- **Transcript (TranscriptAsset):** Full text document derived from the audio track. Extends `TextualAttachmentAsset` (separate from CaptionAsset). Linked to caption assets via the `associatedTranscriptIds` field.

In practice, REACH-generated captions serve as both: the timed segments display as subtitles, and the full text is available for search and download.

## 8.2 Machine Transcription via REACH

Order automatic speech recognition (ASR) via REACH:

```bash
curl -X POST "$KALTURA_SERVICE_URL/service/reach_entryVendorTask/action/add" \
  -d "ks=$KALTURA_KS" \
  -d "format=1" \
  -d "entryVendorTask[objectType]=KalturaEntryVendorTask" \
  -d "entryVendorTask[entryId]=$ENTRY_ID" \
  -d "entryVendorTask[reachProfileId]=$REACH_PROFILE_ID" \
  -d "entryVendorTask[catalogItemId]=$ASR_CATALOG_ITEM_ID"
```

- **serviceFeature:** `1` (CAPTIONS)
- **serviceType:** `2` (MACHINE)
- **Accuracy:** ~83-87%
- **Turnaround:** Near-instant (minutes)

See [REACH API](KALTURA_REACH_API.md) for full REACH task configuration.

## 8.3 Human Transcription via REACH

Order professional human transcription:

- **serviceFeature:** `1` (CAPTIONS)
- **serviceType:** `1` (HUMAN)
- **Accuracy:** 99%+
- **Turnaround:** 3-72 hours depending on vendor and turnaround tier
- **Partners:** 3Play Media, Verbit, AmberScript, dotSUB

## 8.4 Transcript Alignment via REACH

Upload existing text and let REACH align it to the audio timeline:

- **serviceFeature:** `1` (CAPTIONS)
- Provide the text via the task's `inputMetadata` field
- REACH syncs text to audio, creating timed caption segments

## 8.5 Checking Task Status

```bash
curl -X POST "$KALTURA_SERVICE_URL/service/reach_entryVendorTask/action/getJobs" \
  -d "ks=$KALTURA_KS" \
  -d "format=1" \
  -d "filter[objectType]=KalturaEntryVendorTaskFilter" \
  -d "filter[entryIdEqual]=$ENTRY_ID"
```

**Task status flow:**

| Value | Name | Description |
|-------|------|-------------|
| 8 | PENDING_ENTRY_READY | Waiting for entry to reach READY status |
| 1 | PENDING | Queued for processing |
| 3 | PROCESSING | Being transcribed |
| 2 | READY | Complete |
| 6 | ERROR | Processing failed |

With moderation enabled: `PENDING_MODERATION` (4) requires explicit approve/reject before delivery.

## 8.6 Output

When a REACH task completes, it creates a `KalturaCaptionAsset` attached to the entry automatically. The `outputObjectId` on the completed task references the created caption asset ID. The caption is set as default if no default exists.

## 8.7 Custom Vocabulary

REACH supports custom dictionaries for domain-specific terminology. Configure vocabulary lists in the REACH profile to improve accuracy for specialized content (medical, legal, technical terms). See [REACH API](KALTURA_REACH_API.md) for dictionary management.


# 9. Multi-Language Workflows

## 9.1 Multiple Caption Tracks

Each entry supports multiple caption tracks — one asset per language per entry. The player displays a language selector when multiple tracks exist:

```bash
# Add English caption
curl -X POST "$KALTURA_SERVICE_URL/service/caption_captionAsset/action/add" \
  -d "ks=$KALTURA_KS" \
  -d "format=1" \
  -d "entryId=$ENTRY_ID" \
  -d "captionAsset[objectType]=KalturaCaptionAsset" \
  -d "captionAsset[label]=English" \
  -d "captionAsset[language]=English" \
  -d "captionAsset[format]=1" \
  -d "captionAsset[isDefault]=1"

# Add Spanish caption
curl -X POST "$KALTURA_SERVICE_URL/service/caption_captionAsset/action/add" \
  -d "ks=$KALTURA_KS" \
  -d "format=1" \
  -d "entryId=$ENTRY_ID" \
  -d "captionAsset[objectType]=KalturaCaptionAsset" \
  -d "captionAsset[label]=Spanish" \
  -d "captionAsset[language]=Spanish" \
  -d "captionAsset[format]=1"
```

## 9.2 Translation via REACH

Three translation modes:

1. **From audio:** REACH transcribes audio directly in the target language
2. **From existing captions:** REACH translates an existing caption track to a new language
3. **Caption-then-translate:** Order captioning first, then chain a translation task. When the caption task completes, REACH auto-triggers the translation task.

Translation tasks reference the source caption via the task's `sourceLanguage` and target via `catalogItemId`.

## 9.3 Managing Language Variants

List all caption tracks for an entry and switch defaults:

```bash
# List all tracks
curl -X POST "$KALTURA_SERVICE_URL/service/caption_captionAsset/action/list" \
  -d "ks=$KALTURA_KS" \
  -d "format=1" \
  -d "filter[objectType]=KalturaAssetFilter" \
  -d "filter[entryIdEqual]=$ENTRY_ID" \
  -d "filter[statusEqual]=2"

# Switch default to Spanish
curl -X POST "$KALTURA_SERVICE_URL/service/caption_captionAsset/action/setAsDefault" \
  -d "ks=$KALTURA_KS" \
  -d "format=1" \
  -d "captionAssetId=$SPANISH_CAPTION_ID"
```

## 9.4 Multi-Language File Parsing

Upload a single DFXP file containing multiple language tracks with `language="Multilingual"`:

```bash
curl -X POST "$KALTURA_SERVICE_URL/service/caption_captionAsset/action/add" \
  -d "ks=$KALTURA_KS" \
  -d "format=1" \
  -d "entryId=$ENTRY_ID" \
  -d "captionAsset[objectType]=KalturaCaptionAsset" \
  -d "captionAsset[language]=Multilingual" \
  -d "captionAsset[format]=2"
```

The server auto-splits the DFXP into per-language caption assets. Each language track becomes a separate `KalturaCaptionAsset`.

## 9.5 Live Translation

Real-time translated subtitles during live streams via REACH:

- **serviceFeature:** `11` (LIVE_CAPTION)
- Provides real-time ASR with optional simultaneous translation
- Caption data delivered via the live stream's caption track


# 10. Caption Search

## 10.1 eSearch with KalturaESearchCaptionItem

Search within caption text across entries:

```bash
curl -X POST "$KALTURA_SERVICE_URL/service/elasticsearch_esearch/action/searchEntry" \
  -d "ks=$KALTURA_KS" \
  -d "format=1" \
  -d "searchParams[objectType]=KalturaESearchEntryParams" \
  -d "searchParams[searchOperator][objectType]=KalturaESearchEntryOperator" \
  -d "searchParams[searchOperator][operator]=1" \
  -d "searchParams[searchOperator][searchItems][0][objectType]=KalturaESearchCaptionItem" \
  -d "searchParams[searchOperator][searchItems][0][fieldName]=content" \
  -d "searchParams[searchOperator][searchItems][0][searchTerm]=Kaltura API" \
  -d "searchParams[searchOperator][searchItems][0][itemType]=2"
```

**Searchable fields:** `caption_asset_id`, `content`, `start_time`, `end_time`, `label`, `language`

**Item types:** `1` = EXACT_MATCH, `2` = PARTIAL, `3` = STARTS_WITH

## 10.2 Response Data

Search results include `KalturaESearchCaptionItemData` with timestamp information:

| Field | Description |
|-------|-------------|
| `line` | Matched caption text |
| `startsAt` | Start timestamp (seconds) |
| `endsAt` | End timestamp (seconds) |
| `captionAssetId` | Caption asset containing the match |
| `label` | Caption track label |
| `language` | Caption language |

## 10.3 Unified Search

Combine caption search with entry fields and metadata in a single eSearch query:

```bash
curl -X POST "$KALTURA_SERVICE_URL/service/elasticsearch_esearch/action/searchEntry" \
  -d "ks=$KALTURA_KS" \
  -d "format=1" \
  -d "searchParams[objectType]=KalturaESearchEntryParams" \
  -d "searchParams[searchOperator][objectType]=KalturaESearchEntryOperator" \
  -d "searchParams[searchOperator][operator]=2" \
  -d "searchParams[searchOperator][searchItems][0][objectType]=KalturaESearchCaptionItem" \
  -d "searchParams[searchOperator][searchItems][0][fieldName]=content" \
  -d "searchParams[searchOperator][searchItems][0][searchTerm]=tutorial" \
  -d "searchParams[searchOperator][searchItems][0][itemType]=2" \
  -d "searchParams[searchOperator][searchItems][1][objectType]=KalturaESearchEntryItem" \
  -d "searchParams[searchOperator][searchItems][1][fieldName]=name" \
  -d "searchParams[searchOperator][searchItems][1][searchTerm]=tutorial" \
  -d "searchParams[searchOperator][searchItems][1][itemType]=2"
```

Operator `2` = OR (match entries where captions OR title contain "tutorial"). See [eSearch API](KALTURA_ESEARCH_API.md) for full query syntax.

## 10.4 Deep-Linking to Video Moments

Use `startsAt` from caption search results to deep-link to the exact video position:

```
https://player.kaltura.com/p/{partnerId}/sp/{partnerId}00/embedIframeJs/uiconf_id/{playerId}/partner_id/{partnerId}?iframeembed=true&entry_id={entryId}&mediaProxy.mediaPlayFrom={startsAt}
```

Or use the Player JS API: `player.currentTime = startsAt;`


# 11. Player Integration

## 11.1 HLS Caption Delivery

Kaltura Player v7 requests captions via the HLS segmented delivery flow:

1. Player requests M3U8 manifest from `serveWebVTT` (no `segmentIndex`)
2. Manifest lists WebVTT segments with timing
3. Player fetches individual segments as the playhead advances
4. Only caption assets with `displayOnPlayer=true` are included in the manifest
5. Language codes (2-char and 3-char ISO) are based on partner configuration

## 11.2 Transcript Plugin

The `playkit-js-transcript` plugin displays a searchable, scrolling transcript alongside the player:

| Config | Values | Description |
|--------|--------|-------------|
| `expandMode` | `alongside`, `hidden`, `over` | Transcript panel position |
| `showTime` | `true` / `false` | Show timestamps per line |
| `position` | `left`, `right`, `top`, `bottom` | Panel location |
| `downloadDisabled` | `true` / `false` | Disable transcript download |
| `printDisabled` | `true` / `false` | Disable transcript print |

The transcript plugin reads caption data from `serveAsJson` for structured display. It does not support live entries.

## 11.3 Caption Track Selection

When multiple caption tracks exist, the player displays a CC button with language options. The default caption (`isDefault=true`) is auto-selected. Users can switch tracks or disable captions.

## 11.4 Player Playback Plugin Data

The player receives `KalturaCaptionPlaybackPluginData` for each track:

| Field | Description |
|-------|-------------|
| `label` | Display label |
| `format` | Caption format |
| `language` | Language name |
| `languageCode` | ISO 639 code |
| `webVttUrl` | WebVTT serving URL |
| `url` | Raw caption URL |
| `isDefault` | Default track flag |


# 12. Auto-Captioning & Automation

## 12.1 REACH Auto-Ordering Rules

REACH can auto-order captioning tasks based on triggers:

- **Entry READY status:** Auto-caption every new entry
- **Category entry addition:** Auto-caption entries added to specific categories
- **Flavor asset readiness:** Auto-caption when a specific quality version is ready
- **Caption asset READY:** Cascade to translation (caption completes → trigger translation task)

Configure rules in the REACH profile. See [REACH API](KALTURA_REACH_API.md) for rule configuration.

## 12.2 Opt-Out

Set the `blockAutoTranscript` flag on entries to prevent auto-captioning:

```bash
curl -X POST "$KALTURA_SERVICE_URL/service/media/action/update" \
  -d "ks=$KALTURA_KS" \
  -d "format=1" \
  -d "entryId=$ENTRY_ID" \
  -d "mediaEntry[objectType]=KalturaMediaEntry" \
  -d "mediaEntry[blockAutoTranscript]=1"
```

## 12.3 Caption Moderation

When a KS includes the `enableCaptionModeration` privilege, newly added captions have `displayOnPlayer=false`. Captions must be explicitly approved before the player displays them. Use this for compliance workflows that require human review before publication.

## 12.4 Accuracy-Based Deduplication

When multiple captions exist for the same entry + language, the system automatically sets `displayOnPlayer=true` on the caption with the highest `accuracy` value. This handles the machine-to-human caption upgrade path: when REACH delivers a human caption (99%+ accuracy) for an entry that already has a machine caption (~85% accuracy), the human caption automatically wins display priority.

## 12.5 Caption Copy on Trim/Clip/Replace

- **Clip/Trim:** Captions are auto-copied to the new entry with time offsets adjusted to match the clip boundaries.
- **Entry replacement:** Old captions are deleted and new captions are copied from the replacement entry.


# 13. Accessibility Compliance

## 13.1 Compliance Requirements Matrix

| Regulation | Scope | Requirement | Deadline |
|-----------|-------|-------------|----------|
| ADA Title II | US state/local government | WCAG 2.1 AA | Apr 2026 (50k+ pop), Apr 2027 (<50k) |
| Section 508 | US federal agencies | WCAG 2.1 AA | Ongoing |
| WCAG 2.1 AA | Web content | 1.2.2 (pre-recorded captions), 1.2.4 (live captions) | Standard |
| EAA | EU audiovisual services | Accessible multimedia | June 2025 |
| CVAA/FCC | US broadcast + online video | Closed captions on distributed content | Ongoing |

## 13.2 Caption Quality Standards

FCC caption quality requirements:
- **Accuracy:** Captions must match spoken words and non-speech sounds
- **Synchronicity:** Captions must coincide with dialogue and sounds
- **Completeness:** Captions must cover the entirety of the program
- **Placement:** Captions must not obscure visual content

## 13.3 Machine vs Human Accuracy

- **Machine (REACH ASR):** ~83-87% accuracy. Not sufficient for ADA/Section 508 compliance as a standalone solution. Use as a starting point for human review.
- **Human (REACH professional):** 99%+ accuracy. Meets ADA, Section 508, WCAG 2.1 AA, and FCC requirements.

Best practice: Auto-caption with machine ASR for immediate availability, then upgrade to human captions for compliance.

## 13.4 Audio Description via REACH

For visually impaired users, REACH supports audio description:

- **serviceFeature:** `4` (AUDIO_DESCRIPTION) — standard
- **serviceFeature:** `9` (EXTENDED_AUDIO_DESCRIPTION) — extended pauses
- Set `usage=1` (EXTENDED_AUDIO_DESCRIPTION) on the CaptionAsset

## 13.5 Accessibility Audit Pattern

Bulk-check caption coverage across a library:

```bash
# Step 1: List all entries
curl -X POST "$KALTURA_SERVICE_URL/service/media/action/list" \
  -d "ks=$KALTURA_KS" \
  -d "format=1" \
  -d "filter[objectType]=KalturaMediaEntryFilter" \
  -d "filter[statusEqual]=2" \
  -d "filter[mediaTypeEqual]=1" \
  -d "pager[pageSize]=500"

# Step 2: For each entry, check caption assets
curl -X POST "$KALTURA_SERVICE_URL/service/caption_captionAsset/action/list" \
  -d "ks=$KALTURA_KS" \
  -d "format=1" \
  -d "filter[objectType]=KalturaAssetFilter" \
  -d "filter[entryIdEqual]=$ENTRY_ID" \
  -d "filter[statusEqual]=2"

# Step 3: Flag entries with totalCount=0 as needing captions
# Step 4: Order REACH tasks for uncaptioned entries
```


# 14. Business Use Cases

## 14.1 Education: Lecture Auto-Captioning

Upload lecture recording → REACH ASR auto-rule triggers → captions attached → embed in LMS. Students get searchable, captioned content within minutes of upload.

## 14.2 Education: Searchable Video Library

Captions indexed in eSearch → students search by keyword → results include `startsAt` timestamp → deep-link to exact video moment. Transforms video content into a searchable knowledge base.

## 14.3 Education: Multi-Language Translation

English captions (REACH ASR) → REACH translation to Spanish, French, Mandarin → multi-track player. Configure auto-rules: caption completion triggers translation tasks.

## 14.4 Enterprise: Global Training

500+ training videos → auto-caption (machine) → upgrade to human for compliance → translate to 5 languages → generate accessibility compliance report using the audit pattern (11.5).

## 14.5 Enterprise: Town Hall Multi-Language

Live company event → REACH live captions (serviceFeature=11) → recording auto-captioned → translate to regional languages → distribute to regional MediaSpace portals.

## 14.6 Media: Broadcast-to-Web

Ingest SCC captions from broadcast feed → SCC auto-converts to SRT → serve as WebVTT for web players → FCC-compliant caption delivery for online distribution.

## 14.7 Media: OTT Caption Delivery

Store DFXP/TTML master captions (full styling, regions) → generate WebVTT for web players via `serveWebVTT` → HLS segmented delivery for adaptive streaming.

## 14.8 AI/Knowledge: LangChain/RAG Integration

Fetch captions via `serveAsJson` → chunk by time window → generate embeddings → store in vector database → RAG search returns video moments with timestamp deep-links.

```bash
# Fetch structured captions for AI processing
curl -X POST "$KALTURA_SERVICE_URL/service/caption_captionAsset/action/serveAsJson" \
  -d "ks=$KALTURA_KS" \
  -d "format=1" \
  -d "captionAssetId=$CAPTION_ASSET_ID"
```

## 14.9 AI/Knowledge: Meeting Transcripts

Record meeting → REACH auto-caption → download transcript via `serve` or `getUrl` → feed to LLM for summarization, action item extraction, and meeting notes.

## 14.10 Compliance: Accessibility Audit

Bulk list entries → check caption presence per entry → report gaps → order REACH tasks for uncaptioned entries → track completion → generate compliance report. See audit pattern in section 13.5.


# 15. Error Handling

| Error Code | Meaning |
|------------|---------|
| `CAPTION_ASSET_ID_NOT_FOUND` | Caption asset ID does not exist |
| `ENTRY_ID_NOT_FOUND` | Entry ID does not exist when creating caption asset |
| `INVALID_ENTRY_ID` | Invalid entry ID format |
| `CAPTION_ASSET_IS_NOT_READY` | Caption asset is not in READY status (cannot serve) |
| `CAPTION_ASSET_ALREADY_EXISTS` | Duplicate caption for same entry/language/format |
| `CAPTION_ASSET_FILE_NOT_FOUND` | Caption content file not found |
| `CAPTION_ASSET_INVALID_FORMAT` | Caption file content does not match declared format |
| `CAPTION_ASSET_PARSING_FAILED` | Caption file parsing error (malformed SRT, invalid XML, etc.) |
| `CAPTION_ASSET_PARAMS_ID_NOT_FOUND` | Caption params template ID not found |
| `CAPTION_ASSET_ENTRY_ID_NOT_FOUND` | Entry referenced by caption does not exist |
| `FLAVOR_ASSET_ID_NOT_FOUND` | Generic asset not found error |

**Retry strategy:** For transient errors (HTTP 5xx, timeouts), retry with exponential backoff: 1s, 2s, 4s, with jitter, up to 3 retries. For client errors (`ENTRY_ID_NOT_FOUND`, `CAPTION_ASSET_INVALID_FORMAT`), fix the request before retrying. For `CAPTION_ASSET_IS_NOT_READY`, poll with `captionAsset.get` until status reaches READY (2).


# 16. Best Practices

- **Two-step creation.** Always create the asset first (`captionAsset.add`), then upload content (`captionAsset.setContent`). This ensures the asset metadata (language, format, label) is set before content processing begins.
- **Use KalturaStringResource for small captions.** For files under ~1 MB, `KalturaStringResource` with inline content is simpler than the upload token flow. Use `KalturaUploadedFileTokenResource` for larger files.
- **Use getUrl + HTTP fetch for server-side consumption.** `serve` returns a redirect to the CDN. `getUrl` returns a direct URL string — fetch it with a standard HTTP client.
- **Use serveWebVTT for player integration.** Converts any source format to WebVTT on the fly. Use for HTML5 `<track>` elements and custom players.
- **Use serveAsJson for AI/LLM integrations.** Returns structured timestamps in milliseconds — ideal for RAG, summarization, and programmatic analysis.
- **One default caption per entry.** Use `captionAsset.setAsDefault` after uploading. The player auto-displays the default caption. Only one caption can be default per entry.
- **Set accuracy on machine-generated captions.** The `accuracy` field enables automatic deduplication when human captions replace machine captions for the same language.
- **Use REACH for automated captioning; manual API for corrections/imports.** REACH handles the transcription pipeline. Use the caption API to upload corrected files or import captions from external sources.
- **Use eSearch for caption text search.** Do not iterate over `captionAsset.list` to search caption content. Use `KalturaESearchCaptionItem` for indexed full-text search. See [eSearch API](KALTURA_ESEARCH_API.md).
- **Caption every entry for accessibility compliance.** Use REACH auto-rules to ensure all new entries get captioned. Run periodic audits (section 13.5) to catch gaps.
- **format is insertOnly.** Choose the correct caption format at creation time — it cannot be changed after the asset is created.
- **Use DFXP/TTML for multi-language single-file uploads.** Upload a single DFXP file with `language="Multilingual"` and the server auto-splits into per-language assets.
- **Use Captions Studio for interactive editing.** The Captions Studio (Captions Editor) provides a browser-based editor with synchronized video/waveform playback. Create a caption asset first, then pass its ID to the editor. See [Captions Editor Guide](KALTURA_CAPTIONS_EDITOR_API.md) for embed details.


# 17. Related Guides

- **[Captions Editor](KALTURA_CAPTIONS_EDITOR_API.md)** — Captions Studio (interactive caption editor) embed
- **[REACH API](KALTURA_REACH_API.md)** — Enrichment services marketplace: captioning, translation, dubbing, moderation, and 20+ services with automation rules
- **[eSearch API](KALTURA_ESEARCH_API.md)** — Caption search with `KalturaESearchCaptionItem`, timestamp deep-linking
- **[Player Embed Guide](KALTURA_PLAYER_EMBED_GUIDE.md)** — Caption display, track selection, transcript plugin
- **[Upload & Ingestion API](KALTURA_UPLOAD_AND_INGESTION_API.md)** — Upload tokens for `KalturaUploadedFileTokenResource`
- **[Webhooks API](KALTURA_WEBHOOKS_API.md)** — Caption asset events: `OBJECT_ADDED`, `OBJECT_DATA_CHANGED`, `OBJECT_DELETED`
- **[Custom Metadata API](KALTURA_CUSTOM_METADATA_API.md)** — Structured metadata (separate from timed text)
- **[Agents Manager API](KALTURA_AGENTS_MANAGER_API.md)** — Automated caption workflows via AI agents
- **[Session Guide](KALTURA_SESSION_GUIDE.md)** — KS generation and permission scoping
- **[AppTokens API](KALTURA_APPTOKENS_API.md)** — Secure auth without admin secrets
- **[Distribution](KALTURA_DISTRIBUTION_API.md)** — Caption assets included in distribution packages

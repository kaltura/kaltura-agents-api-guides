# Kaltura Upload, Ingest & Content Delivery API

This guide covers the complete lifecycle of getting content into Kaltura and delivering it to viewers: uploading files (including chunked/resumable uploads), creating entries, importing from URLs, and constructing playback and thumbnail URLs.

**Base URL:** `https://www.kaltura.com/api_v3`
**Auth:** All requests require a valid KS (see [Session Guide](KALTURA_SESSION_GUIDE.md))
**Format:** Form-encoded POST, `format=1` for JSON responses


# 1. Upload Lifecycle Overview

Every file upload follows this pattern:

```
uploadToken.add  -->  uploadToken.upload (one or more chunks)  -->  media.add  -->  media.addContent
```

1. **Create an upload token** -- a server-side container that will hold the file
2. **Upload file data** -- send the file bytes (single shot or chunked) to the token
3. **Create a media entry** -- the logical object (metadata, name, type)
4. **Attach content** -- link the upload token to the entry, triggering transcoding

Alternative shortcuts:
- `media.addFromUploadedFile` -- combines steps 3+4 (create entry and attach content in one call)
- `media.addFromUrl` -- skip upload entirely, import from a URL


# 2. Upload Token API

## 2.1 Create an Upload Token

```
POST /api_v3/service/uploadToken/action/add
```

| Parameter | Type | Description |
|-----------|------|-------------|
| `ks` | string | Kaltura Session |
| `uploadToken[fileName]` | string | Original file name (optional, for tracking) |
| `uploadToken[fileSize]` | int | Expected file size in bytes (optional, enables server-side validation) |

**Response:** `KalturaUploadToken` object with `id`, `status`, `fileName`, `fileSize`, `uploadedFileSize`

**Token statuses:**
| Value | Name | Meaning |
|-------|------|---------|
| 0 | PENDING | Created, no data uploaded yet |
| 1 | PARTIAL_UPLOAD | Some chunks received |
| 2 | FULL_UPLOAD | All data received |
| 3 | CLOSED | Token consumed by addContent |

```bash
curl -X POST "$KALTURA_SERVICE_URL/service/uploadToken/action/add" \
  -d "ks=$KALTURA_KS" \
  -d "format=1" \
  -d "uploadToken[fileName]=my_video.mp4" \
  -d "uploadToken[fileSize]=15728640"
```

The response includes the `id` (upload token ID) and `status` fields.

## 2.2 Upload File Data (Single or Chunked)

```
POST /api_v3/service/uploadToken/action/upload
```

| Parameter | Type | Description |
|-----------|------|-------------|
| `uploadTokenId` | string | The token ID from step 1 |
| `fileData` | file | The file or chunk (multipart form data) |
| `resume` | bool | `false` for first/only chunk, `true` for subsequent chunks |
| `resumeAt` | float | Byte offset to resume at (use `-1` or omit for first chunk) |
| `finalChunk` | bool | `true` if this is the last (or only) chunk, `false` otherwise |

### Single-file upload (small files)

```bash
curl -X POST "$KALTURA_SERVICE_URL/service/uploadToken/action/upload" \
  -F "ks=$KALTURA_KS" \
  -F "uploadTokenId=$UPLOAD_TOKEN_ID" \
  -F "resume=false" \
  -F "finalChunk=true" \
  -F "resumeAt=-1" \
  -F "fileData=@my_video.mp4;type=video/mp4"
```

### Chunked upload (large files, resumable)

Split the file into chunks (e.g., 2 MB each) and upload each chunk sequentially:

```bash
# First chunk (offset 0)
dd if=big_video.mp4 bs=2097152 count=1 skip=0 2>/dev/null | \
curl -X POST "$KALTURA_SERVICE_URL/service/uploadToken/action/upload" \
  -F "ks=$KALTURA_KS" \
  -F "uploadTokenId=$UPLOAD_TOKEN_ID" \
  -F "resume=false" \
  -F "resumeAt=0" \
  -F "finalChunk=false" \
  -F "fileData=@-;filename=chunk_0"

# Subsequent chunks (resume=true, resumeAt=byte offset)
dd if=big_video.mp4 bs=2097152 count=1 skip=1 2>/dev/null | \
curl -X POST "$KALTURA_SERVICE_URL/service/uploadToken/action/upload" \
  -F "ks=$KALTURA_KS" \
  -F "uploadTokenId=$UPLOAD_TOKEN_ID" \
  -F "resume=true" \
  -F "resumeAt=2097152" \
  -F "finalChunk=false" \
  -F "fileData=@-;filename=chunk_2097152"

# Final chunk (finalChunk=true)
dd if=big_video.mp4 bs=2097152 count=1 skip=2 2>/dev/null | \
curl -X POST "$KALTURA_SERVICE_URL/service/uploadToken/action/upload" \
  -F "ks=$KALTURA_KS" \
  -F "uploadTokenId=$UPLOAD_TOKEN_ID" \
  -F "resume=true" \
  -F "resumeAt=4194304" \
  -F "finalChunk=true" \
  -F "fileData=@-;filename=chunk_4194304"
```

Adjust `skip`, `resumeAt`, and `finalChunk` values per chunk. In a real script, loop until all bytes are uploaded.

**Resume after failure:** If a chunk upload fails, call `uploadToken.get` to check `uploadedFileSize`, then resume from that offset.

## 2.3 Check Token Status

```
POST /api_v3/service/uploadToken/action/get
```

| Parameter | Type | Description |
|-----------|------|-------------|
| `uploadTokenId` | string | The token ID |

Returns the token object with `uploadedFileSize` (bytes uploaded so far) and `status`.

## 2.4 Delete an Upload Token

```
POST /api_v3/service/uploadToken/action/delete
```

Use this to clean up abandoned uploads. Tokens are auto-deleted after consumption by `addContent`.


# 3. Creating Media Entries

## 3.1 media.add -- Create Entry Metadata

```
POST /api_v3/service/media/action/add
```

| Parameter | Type | Description |
|-----------|------|-------------|
| `entry[objectType]` | string | `KalturaMediaEntry` |
| `entry[mediaType]` | int | `1`=Video, `2`=Image, `5`=Audio |
| `entry[name]` | string | Display name |
| `entry[description]` | string | Description (optional) |
| `entry[tags]` | string | Comma-separated tags (optional) |

**Response:** `KalturaMediaEntry` with `id`, `status` (-2 = NO_CONTENT until file attached)

```bash
curl -X POST "$KALTURA_SERVICE_URL/service/media/action/add" \
  -d "ks=$KALTURA_KS" \
  -d "format=1" \
  -d "entry[objectType]=KalturaMediaEntry" \
  -d "entry[mediaType]=1" \
  -d "entry[name]=My Uploaded Video" \
  -d "entry[description]=Uploaded via API" \
  -d "entry[tags]=api,upload,demo"
```

The response includes the `id` (entry ID) and `status` fields.

## 3.2 media.addContent -- Attach Upload Token to Entry

```
POST /api_v3/service/media/action/addContent
```

| Parameter | Type | Description |
|-----------|------|-------------|
| `entryId` | string | The entry ID from media.add |
| `resource[objectType]` | string | `KalturaUploadedFileTokenResource` |
| `resource[token]` | string | The upload token ID |

This triggers transcoding. Entry status changes to `IMPORT (1)` or `CONVERTING (4)`.

```bash
curl -X POST "$KALTURA_SERVICE_URL/service/media/action/addContent" \
  -d "ks=$KALTURA_KS" \
  -d "format=1" \
  -d "entryId=$KALTURA_ENTRY_ID" \
  -d "resource[objectType]=KalturaUploadedFileTokenResource" \
  -d "resource[token]=$UPLOAD_TOKEN_ID"
```

## 3.3 media.addFromUrl -- Import from URL (No Upload Needed)

```
POST /api_v3/service/media/action/addFromUrl
```

| Parameter | Type | Description |
|-----------|------|-------------|
| `mediaEntry[objectType]` | string | `KalturaMediaEntry` |
| `mediaEntry[name]` | string | Display name |
| `mediaEntry[mediaType]` | int | `1`=Video, `2`=Image, `5`=Audio |
| `url` | string | Publicly accessible URL of the file |

Kaltura fetches the file server-side. Entry starts in `IMPORT (1)` status.

```bash
curl -X POST "$KALTURA_SERVICE_URL/service/media/action/addFromUrl" \
  -d "ks=$KALTURA_KS" \
  -d "format=1" \
  -d "mediaEntry[objectType]=KalturaMediaEntry" \
  -d "mediaEntry[name]=Imported from URL" \
  -d "mediaEntry[mediaType]=1" \
  -d "url=https://example.com/sample_video.mp4"
```

## 3.4 Entry Statuses

| Value | Name | Description |
|-------|------|-------------|
| -2 | NO_CONTENT | Entry created, no file attached |
| -1 | ERROR_CONVERTING | Transcoding failed |
| 0 | IMPORT | File being fetched/imported |
| 1 | PRECONVERT | Preparing for transcoding |
| 2 | READY | Fully processed, playable |
| 4 | CONVERTING | Transcoding in progress |
| 7 | DELETED | Entry deleted |


# 4. Content Delivery

## 4.1 playManifest -- Adaptive Streaming (HLS/DASH)

The `playManifest` URL is the primary way to get a playback URL for video/audio entries.

**URL pattern:**
```
https://cdnapisec.kaltura.com/p/{PARTNER_ID}/sp/{PARTNER_ID}00/playManifest/entryId/{ENTRY_ID}/format/{FORMAT}/protocol/https
```

| Format value | Protocol | Description |
|-------------|----------|-------------|
| `applehttp` | HLS | Apple HTTP Live Streaming (most common) |
| `mpegdash` | DASH | MPEG-DASH adaptive streaming |
| `url` | Progressive | Direct MP4 download |
| `download` | Download | Prompts file download |

**Example HLS URL:**
```
https://cdnapisec.kaltura.com/p/12345/sp/1234500/playManifest/entryId/0_abc123/format/applehttp/protocol/https
```

**With specific flavor:**
```
https://cdnapisec.kaltura.com/p/12345/sp/1234500/playManifest/entryId/0_abc123/format/download/protocol/https/flavorParamIds/0
```

**With KS for access-controlled content:**
```
https://cdnapisec.kaltura.com/p/12345/sp/1234500/playManifest/entryId/0_abc123/format/applehttp/protocol/https/ks/{KS}
```

> For access-controlled entries (entitlements, geo restrictions, etc.), append `/ks/{KS}` to the playManifest URL. Public entries work without a KS.

**Download URL from entry object:** Every `KalturaMediaEntry` has a `downloadUrl` property you can use directly.

## 4.2 Thumbnail API

Kaltura provides a dynamic thumbnail API that generates thumbnails on the fly.

**URL pattern:**
```
https://cdnapisec.kaltura.com/p/{PARTNER_ID}/thumbnail/entry_id/{ENTRY_ID}/{PARAMS}
```

| Parameter | Description |
|-----------|-------------|
| `/width/{W}` | Thumbnail width in pixels |
| `/height/{H}` | Thumbnail height in pixels |
| `/vid_sec/{S}` | Capture at specific second of video |
| `/quality/{Q}` | JPEG quality (1-100) |
| `/type/{T}` | `1`=JPEG (default), `2`=PNG |

**Examples:**
```
# Default thumbnail (auto-generated)
https://cdnapisec.kaltura.com/p/12345/thumbnail/entry_id/0_abc123

# 640x360 at 30 seconds into the video
https://cdnapisec.kaltura.com/p/12345/thumbnail/entry_id/0_abc123/width/640/height/360/vid_sec/30

# High quality PNG
https://cdnapisec.kaltura.com/p/12345/thumbnail/entry_id/0_abc123/width/1920/height/1080/quality/100/type/2
```


# 5. Flavor Assets (Transcoded Renditions)

A "flavor" is a transcoded rendition of the source file (e.g., 360p, 720p, 1080p). Kaltura automatically creates flavors based on the account's conversion profile.

## 5.1 List Flavors for an Entry

```
POST /api_v3/service/flavorAsset/action/list
```

| Parameter | Type | Description |
|-----------|------|-------------|
| `filter[entryIdEqual]` | string | The entry ID |

**Response:** List of `KalturaFlavorAsset` objects with:
- `id` -- flavor asset ID
- `flavorParamsId` -- the transcoding profile used
- `width`, `height` -- dimensions
- `bitrate` -- in kbps
- `size` -- file size in KB
- `status` -- `2`=READY, `4`=NOT_APPLICABLE, etc.
- `isOriginal` -- `true` if this is the source file

```bash
curl -X POST "$KALTURA_SERVICE_URL/service/flavorAsset/action/list" \
  -d "ks=$KALTURA_KS" \
  -d "format=1" \
  -d "filter[entryIdEqual]=$KALTURA_ENTRY_ID"
```

The response `objects` array contains each flavor with `id`, `width`, `height`, `bitrate`, `size`, `status`, and `isOriginal` fields.

## 5.2 Get Download URL for a Specific Flavor

```
POST /api_v3/service/flavorAsset/action/getUrl
```

| Parameter | Type | Description |
|-----------|------|-------------|
| `id` | string | The flavor asset ID |

Returns a direct download URL string for that specific flavor.


# 6. Bulk Upload

For ingesting many files at once, use CSV or XML bulk upload.

```
POST /api_v3/service/media/action/bulkUploadAdd
```

| Parameter | Type | Description |
|-----------|------|-------------|
| `fileData` | file | CSV or XML file with entries to create |

**CSV format** (one entry per line):
```
*action,title,description,tags,url,mediaType
1,Video Title,Description,"tag1,tag2",https://example.com/video.mp4,1
1,Another Video,Another desc,"tag3",https://example.com/video2.mp4,1
```

The `*action` column: `1`=add, `2`=update, `3`=delete.

**Note:** For bulk operations creating more than 5,000 entries, coordinate with your Kaltura representative.


# 7. Complete Example -- Chunked Upload

The following sequence of curl commands demonstrates the full chunked upload lifecycle.

```bash
# --- Step 1: Create an upload token ---
curl -X POST "$KALTURA_SERVICE_URL/service/uploadToken/action/add" \
  -d "ks=$KALTURA_KS" \
  -d "format=1" \
  -d "uploadToken[fileName]=my_video.mp4" \
  -d "uploadToken[fileSize]=6291456"
# Save the "id" from the response as UPLOAD_TOKEN_ID

# --- Step 2: Upload file in chunks ---

# Chunk 1 (first 2 MB)
dd if=my_video.mp4 bs=2097152 count=1 skip=0 2>/dev/null | \
curl -X POST "$KALTURA_SERVICE_URL/service/uploadToken/action/upload" \
  -F "ks=$KALTURA_KS" \
  -F "uploadTokenId=$UPLOAD_TOKEN_ID" \
  -F "resume=false" \
  -F "resumeAt=0" \
  -F "finalChunk=false" \
  -F "fileData=@-;filename=chunk_0"

# Chunk 2 (next 2 MB)
dd if=my_video.mp4 bs=2097152 count=1 skip=1 2>/dev/null | \
curl -X POST "$KALTURA_SERVICE_URL/service/uploadToken/action/upload" \
  -F "ks=$KALTURA_KS" \
  -F "uploadTokenId=$UPLOAD_TOKEN_ID" \
  -F "resume=true" \
  -F "resumeAt=2097152" \
  -F "finalChunk=false" \
  -F "fileData=@-;filename=chunk_2097152"

# Chunk 3 / final chunk (last 2 MB)
dd if=my_video.mp4 bs=2097152 count=1 skip=2 2>/dev/null | \
curl -X POST "$KALTURA_SERVICE_URL/service/uploadToken/action/upload" \
  -F "ks=$KALTURA_KS" \
  -F "uploadTokenId=$UPLOAD_TOKEN_ID" \
  -F "resume=true" \
  -F "resumeAt=4194304" \
  -F "finalChunk=true" \
  -F "fileData=@-;filename=chunk_4194304"

# --- Step 3: Create a media entry ---
curl -X POST "$KALTURA_SERVICE_URL/service/media/action/add" \
  -d "ks=$KALTURA_KS" \
  -d "format=1" \
  -d "entry[objectType]=KalturaMediaEntry" \
  -d "entry[mediaType]=1" \
  -d "entry[name]=my_video.mp4"
# Save the "id" from the response as ENTRY_ID

# --- Step 4: Attach the upload token to the entry ---
curl -X POST "$KALTURA_SERVICE_URL/service/media/action/addContent" \
  -d "ks=$KALTURA_KS" \
  -d "format=1" \
  -d "entryId=$KALTURA_ENTRY_ID" \
  -d "resource[objectType]=KalturaUploadedFileTokenResource" \
  -d "resource[token]=$UPLOAD_TOKEN_ID"

# The entry is now processing. Check its thumbnail at:
# https://cdnapisec.kaltura.com/p/$KALTURA_PARTNER_ID/thumbnail/entry_id/$KALTURA_ENTRY_ID
```

**Resume after failure:** Call `uploadToken.get` to check `uploadedFileSize`, then resume from that byte offset.


# 8. Key Differences: Upload Paths

| Method | Use case | Requires file locally? |
|--------|---------|----------------------|
| `uploadToken` + `media.addContent` | Full control, chunked/resumable | Yes |
| `media.addFromUploadedFile` | Shortcut (add + attach in one call) | Yes (already uploaded via token) |
| `media.addFromUrl` | Import from public URL | No |
| `media.bulkUploadAdd` | Batch ingest via CSV/XML | No (URLs in CSV) |


# 9. Related Guides

- **[Session Guide](KALTURA_SESSION_GUIDE.md)** — How to create and manage KS tokens
- **[AppTokens Guide](KALTURA_APPTOKENS_API.md)** — Secure token-based auth for upload integrations
- **[eSearch Guide](KALTURA_ESEARCH_API.md)** — Search for entries after upload
- **[Player Embed Guide](KALTURA_PLAYER_EMBED_GUIDE.md)** — Embed uploaded content
- **[REACH Guide](KALTURA_REACH_API.md)** — Auto-caption and enrich uploaded content
- **[Agents Manager](KALTURA_AGENTS_MANAGER_API.md)** — Auto-process uploaded content (triggers on ENTRY_READY)
- **[AI Genie](KALTURA_AI_GENIE_API.md)** — Search uploaded content via conversational AI
- **[Events Platform](KALTURA_EVENTS_PLATFORM_API.md)** — Upload logo/banner assets for virtual events
- **[Multi-Stream](KALTURA_MULTI_STREAM_API.md)** — Create synchronized dual/multi-screen entries using parent-child relationships
- **Reference implementation:** [kaltura_uploader](https://github.com/zoharbabin/kaltura_uploader) — Python CLI with adaptive chunked upload

# Kaltura Upload, Ingest & Content Delivery API

This guide covers the complete lifecycle of getting content into Kaltura and delivering it to viewers: uploading files (including chunked/resumable uploads), creating media, document, and data entries, importing from URLs, and constructing playback, thumbnail, and direct-serve URLs.

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
- `document.addFromUploadedFile` -- create and attach document entries (PDF, DOCX, PPTX)
- `baseEntry.addFromUploadedFile` -- create and attach data entries (any file type, no transcoding)


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
| 4 | TIMED_OUT | Token expired before upload completed |
| 5 | DELETED | Token deleted |

```bash
curl -X POST "$KALTURA_SERVICE_URL/service/uploadToken/action/add" \
  -d "ks=$KALTURA_KS" \
  -d "format=1" \
  -d "uploadToken[fileName]=my_video.mp4" \
  -d "uploadToken[fileSize]=15728640"
```

**Response:**
```json
{
  "id": "1_abcdef123456",
  "status": 0,
  "fileName": null,
  "fileSize": null,
  "objectType": "KalturaUploadToken"
}
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
  -F "format=1" \
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
  -F "format=1" \
  -F "uploadTokenId=$UPLOAD_TOKEN_ID" \
  -F "resume=false" \
  -F "resumeAt=0" \
  -F "finalChunk=false" \
  -F "fileData=@-;filename=chunk_0"

# Subsequent chunks (resume=true, resumeAt=byte offset)
dd if=big_video.mp4 bs=2097152 count=1 skip=1 2>/dev/null | \
curl -X POST "$KALTURA_SERVICE_URL/service/uploadToken/action/upload" \
  -F "ks=$KALTURA_KS" \
  -F "format=1" \
  -F "uploadTokenId=$UPLOAD_TOKEN_ID" \
  -F "resume=true" \
  -F "resumeAt=2097152" \
  -F "finalChunk=false" \
  -F "fileData=@-;filename=chunk_2097152"

# Final chunk (finalChunk=true)
dd if=big_video.mp4 bs=2097152 count=1 skip=2 2>/dev/null | \
curl -X POST "$KALTURA_SERVICE_URL/service/uploadToken/action/upload" \
  -F "ks=$KALTURA_KS" \
  -F "format=1" \
  -F "uploadTokenId=$UPLOAD_TOKEN_ID" \
  -F "resume=true" \
  -F "resumeAt=4194304" \
  -F "finalChunk=true" \
  -F "fileData=@-;filename=chunk_4194304"
```

Adjust `skip`, `resumeAt`, and `finalChunk` values per chunk. In a real script, loop until all bytes are uploaded.

**Resume after failure:** If a chunk upload fails, call `uploadToken.get` to check `uploadedFileSize`, then resume from that offset:

```bash
# Check how many bytes were successfully uploaded
curl -X POST "$KALTURA_SERVICE_URL/service/uploadToken/action/get" \
  -d "ks=$KALTURA_KS" \
  -d "format=1" \
  -d "uploadTokenId=$UPLOAD_TOKEN_ID"
# Response includes: "uploadedFileSize": 4194304

# Resume from where upload left off
RESUME_AT=4194304  # from uploadedFileSize above
dd if=largefile.mp4 bs=2097152 skip=$((RESUME_AT / 2097152)) 2>/dev/null | \
curl -X POST "$KALTURA_SERVICE_URL/service/uploadToken/action/upload" \
  -F "ks=$KALTURA_KS" \
  -F "format=1" \
  -F "uploadTokenId=$UPLOAD_TOKEN_ID" \
  -F "resume=true" \
  -F "resumeAt=$RESUME_AT" \
  -F "finalChunk=false" \
  -F "fileData=@-;filename=chunk_$RESUME_AT"
```

**Chunk sizing guidance:** Use 2-5 MB chunks for files under 100 MB and 10-50 MB chunks for larger files. Smaller chunks mean more HTTP requests but easier recovery on failure; larger chunks reduce overhead but require re-uploading more data on failure.

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

**Response:** `KalturaMediaEntry` with `id`, `status` (7 = NO_CONTENT until file attached)

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

**Response:**
```json
{
  "id": "1_xyz789",
  "name": "My Video",
  "status": 7,
  "mediaType": 1,
  "objectType": "KalturaMediaEntry"
}
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

This triggers transcoding. Entry status changes to `IMPORT (0)` or `PENDING (4)`.

```bash
curl -X POST "$KALTURA_SERVICE_URL/service/media/action/addContent" \
  -d "ks=$KALTURA_KS" \
  -d "format=1" \
  -d "entryId=$KALTURA_ENTRY_ID" \
  -d "resource[objectType]=KalturaUploadedFileTokenResource" \
  -d "resource[token]=$UPLOAD_TOKEN_ID"
```

## 3.3 media.addFromUploadedFile -- Create Entry + Attach in One Call

Combines `media.add` and `media.addContent` into a single request. The entry is created and the upload token is attached in one API call.

```
POST /api_v3/service/media/action/addFromUploadedFile
```

| Parameter | Type | Description |
|-----------|------|-------------|
| `mediaEntry[objectType]` | string | `KalturaMediaEntry` |
| `mediaEntry[name]` | string | Display name |
| `mediaEntry[mediaType]` | int | `1`=Video, `2`=Image, `5`=Audio |
| `mediaEntry[tags]` | string | Comma-separated tags (optional) |
| `uploadTokenId` | string | The upload token ID (file must already be uploaded) |

```bash
curl -X POST "$KALTURA_SERVICE_URL/service/media/action/addFromUploadedFile" \
  -d "ks=$KALTURA_KS" \
  -d "format=1" \
  -d "mediaEntry[objectType]=KalturaMediaEntry" \
  -d "mediaEntry[name]=My Uploaded Video" \
  -d "mediaEntry[mediaType]=1" \
  -d "mediaEntry[tags]=api,upload" \
  -d "uploadTokenId=$UPLOAD_TOKEN_ID"
```

This triggers transcoding immediately. Use this shortcut when you do not need to set entry metadata before attaching content.

## 3.4 media.addFromUrl -- Import from URL (No Upload Needed)

```
POST /api_v3/service/media/action/addFromUrl
```

| Parameter | Type | Description |
|-----------|------|-------------|
| `mediaEntry[objectType]` | string | `KalturaMediaEntry` |
| `mediaEntry[name]` | string | Display name |
| `mediaEntry[mediaType]` | int | `1`=Video, `2`=Image, `5`=Audio |
| `url` | string | Publicly accessible URL of the file |

Kaltura fetches the file server-side. Entry starts in `IMPORT (0)` status.

```bash
curl -X POST "$KALTURA_SERVICE_URL/service/media/action/addFromUrl" \
  -d "ks=$KALTURA_KS" \
  -d "format=1" \
  -d "mediaEntry[objectType]=KalturaMediaEntry" \
  -d "mediaEntry[name]=Imported from URL" \
  -d "mediaEntry[mediaType]=1" \
  -d "url=https://example.com/sample_video.mp4"
```

## 3.5 Entry Statuses

| Value | Name | Description |
|-------|------|-------------|
| -2 | ERROR_IMPORTING | Import failed |
| -1 | ERROR_CONVERTING | Transcoding failed |
| 0 | IMPORT | File being fetched/imported |
| 1 | PRECONVERT | Preparing for transcoding |
| 2 | READY | Fully processed, playable |
| 3 | DELETED | Entry deleted |
| 4 | PENDING | Pending processing |
| 5 | MODERATE | Awaiting moderation |
| 6 | BLOCKED | Blocked by admin |
| 7 | NO_CONTENT | Entry created, no file attached |

## 3.6 Flavor Asset Statuses

When polling flavor assets during transcoding (`flavorAsset.list` with `entryIdEqual`):

| Value | Name | Description |
|-------|------|-------------|
| -1 | ERROR | Transcoding failed for this flavor |
| 0 | QUEUED | Waiting in transcoding queue |
| 1 | CONVERTING | Transcoding in progress |
| 2 | READY | Transcoded and playable |
| 3 | DELETED | Flavor deleted |
| 4 | NOT_APPLICABLE | Flavor params exist but don't apply to this entry |
| 5 | TEMP | Temporary intermediate flavor |
| 6 | WAIT_FOR_CONVERT | Waiting for a dependency flavor to finish |
| 7 | IMPORTING | Source file being imported |
| 8 | VALIDATING | File validation in progress |
| 9 | EXPORTING | Being exported to external storage |

## 3.7 Entry Moderation Statuses

When content moderation is enabled on the account, entries have a `moderationStatus` field:

| Value | Name | Description |
|-------|------|-------------|
| 1 | PENDING_MODERATION | Awaiting moderator review |
| 2 | APPROVED | Approved for publishing |
| 3 | REJECTED | Rejected by moderator |
| 4 | DELETED | Deleted |
| 5 | FLAGGED_FOR_REVIEW | Flagged by user for review |
| 6 | AUTO_APPROVED | Automatically approved by rules |

For user flagging, moderator approve/reject, AI moderation via REACH, and category-level content gating, see the [Moderation API Guide](KALTURA_MODERATION_API.md).

## 3.8 media.get -- Retrieve Entry Details and Poll for READY

```
POST /api_v3/service/media/action/get
```

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `entryId` | string | Yes | The entry ID to retrieve |
| `version` | integer | No | Specific version to retrieve (default: latest) |

```bash
curl -X POST "$KALTURA_SERVICE_URL/service/media/action/get" \
  -d "ks=$KALTURA_KS" \
  -d "format=1" \
  -d "entryId=$KALTURA_ENTRY_ID"
```

**Response:**

```json
{
  "id": "1_xyz789",
  "name": "My Video",
  "status": 2,
  "mediaType": 1,
  "duration": 120,
  "plays": 0,
  "views": 0,
  "createdAt": 1718467200,
  "updatedAt": 1718467260,
  "thumbnailUrl": "https://cfvod.kaltura.com/p/12345/sp/1234500/thumbnail/entry_id/1_xyz789/version/100001",
  "downloadUrl": "https://cdnapisec.kaltura.com/p/12345/sp/1234500/playManifest/entryId/1_xyz789/format/download/protocol/https",
  "userId": "admin",
  "tags": "api,upload",
  "description": "Uploaded via API",
  "objectType": "KalturaMediaEntry"
}
```

**Poll for READY status after upload:** After calling `media.addContent` or `media.addFromUrl`, the entry goes through transcoding. Poll `media.get` until `status` reaches `2` (READY):

```bash
# Poll every 5 seconds until READY
while true; do
  STATUS=$(curl -s -X POST "$KALTURA_SERVICE_URL/service/media/action/get" \
    -d "ks=$KALTURA_KS" \
    -d "format=1" \
    -d "entryId=$KALTURA_ENTRY_ID" | jq -r '.status')
  echo "Status: $STATUS"
  [ "$STATUS" = "2" ] && break
  [ "$STATUS" = "-1" ] && echo "Transcoding failed" && break
  sleep 5
done
```

## 3.9 media.list -- Search and Filter Entries

```
POST /api_v3/service/media/action/list
```

| Parameter | Type | Description |
|-----------|------|-------------|
| `filter[objectType]` | string | `KalturaMediaEntryFilter` |
| `filter[nameLike]` | string | Partial name match |
| `filter[tagsMultiLikeOr]` | string | Match any of these comma-separated tags |
| `filter[mediaTypeEqual]` | integer | `1`=Video, `2`=Image, `5`=Audio |
| `filter[statusEqual]` | integer | Filter by entry status (e.g., `2` for READY) |
| `filter[createdAtGreaterThanOrEqual]` | integer | Unix timestamp — entries created after this time |
| `filter[createdAtLessThanOrEqual]` | integer | Unix timestamp — entries created before this time |
| `pager[pageSize]` | integer | Results per page (max 500) |
| `pager[pageIndex]` | integer | Page number (1-based) |

```bash
curl -X POST "$KALTURA_SERVICE_URL/service/media/action/list" \
  -d "ks=$KALTURA_KS" \
  -d "format=1" \
  -d "filter[objectType]=KalturaMediaEntryFilter" \
  -d "filter[tagsMultiLikeOr]=api,upload" \
  -d "filter[statusEqual]=2" \
  -d "pager[pageSize]=30" \
  -d "pager[pageIndex]=1"
```

**Response:**

```json
{
  "objects": [
    {
      "id": "1_xyz789",
      "name": "My Video",
      "status": 2,
      "mediaType": 1,
      "duration": 120,
      "createdAt": 1718467200,
      "objectType": "KalturaMediaEntry"
    }
  ],
  "totalCount": 1,
  "objectType": "KalturaMediaListResponse"
}
```

Results beyond 10,000 total are not pageable. Use `createdAtGreaterThanOrEqual` date windowing to iterate large datasets.

## 3.10 media.update -- Update Entry Metadata

```
POST /api_v3/service/media/action/update
```

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `entryId` | string | Yes | Entry ID to update |
| `mediaEntry[objectType]` | string | Yes | `KalturaMediaEntry` |
| `mediaEntry[name]` | string | No | Updated name |
| `mediaEntry[description]` | string | No | Updated description |
| `mediaEntry[tags]` | string | No | Updated comma-separated tags |
| `mediaEntry[referenceId]` | string | No | External reference ID |

Only include the fields you want to change — omitted fields remain unchanged (partial update).

```bash
curl -X POST "$KALTURA_SERVICE_URL/service/media/action/update" \
  -d "ks=$KALTURA_KS" \
  -d "format=1" \
  -d "entryId=$KALTURA_ENTRY_ID" \
  -d "mediaEntry[objectType]=KalturaMediaEntry" \
  -d "mediaEntry[name]=Updated Title" \
  -d "mediaEntry[tags]=updated,production"
```

## 3.11 media.delete -- Delete an Entry

```
POST /api_v3/service/media/action/delete
```

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `entryId` | string | Yes | Entry ID to delete |

```bash
curl -X POST "$KALTURA_SERVICE_URL/service/media/action/delete" \
  -d "ks=$KALTURA_KS" \
  -d "format=1" \
  -d "entryId=$KALTURA_ENTRY_ID"
```

Deletion is soft-delete (status changes to 3 = DELETED). The entry can be recovered from the Kaltura trash for a limited time.

## 3.12 Non-Media Entry Types (Documents and Data)

Kaltura supports uploading and managing non-media files as standalone entries. Use the appropriate service based on file type:

| File Type | Service | Entry Object | When to Use |
|-----------|---------|-------------|-------------|
| Video, audio, image | `media` | `KalturaMediaEntry` | Standard media content — transcoded and playable |
| PDF, Word, PowerPoint | `document` | `KalturaDocumentEntry` | Documents that benefit from Kaltura's document conversion (PDF viewer, slide sync) |
| Any other file | `baseEntry` | `KalturaDataEntry` (type=6) | Arbitrary files — stored and served as-is, no transcoding |

### Document Entries

Upload documents (PDF, DOCX, PPTX) using the `document` service. Documents go through Kaltura's document conversion pipeline.

```bash
# Create and attach document in one call
curl -X POST "$KALTURA_SERVICE_URL/service/document/action/addFromUploadedFile" \
  -d "ks=$KALTURA_KS" \
  -d "format=1" \
  -d "documentEntry[objectType]=KalturaDocumentEntry" \
  -d "documentEntry[name]=Presentation Slides" \
  -d "documentEntry[documentType]=11" \
  -d "documentEntry[tags]=slides,training" \
  -d "uploadTokenId=$UPLOAD_TOKEN_ID"
```

**Document types (`documentType`):**

| Value | Name | Description |
|-------|------|-------------|
| 11 | DOCUMENT | General document (Word, PowerPoint, etc.) |
| 12 | SWF | Flash document |
| 13 | PDF | PDF document |

### Data Entries

Upload any file type as a data entry using the `baseEntry` service. Data entries are stored and served as-is without transcoding.

```bash
# Create a data entry and attach file
curl -X POST "$KALTURA_SERVICE_URL/service/baseEntry/action/addFromUploadedFile" \
  -d "ks=$KALTURA_KS" \
  -d "format=1" \
  -d "entry[objectType]=KalturaDataEntry" \
  -d "entry[type]=6" \
  -d "entry[name]=Configuration File" \
  -d "entry[tags]=config,json" \
  -d "entry[conversionProfileId]=-1" \
  -d "uploadTokenId=$UPLOAD_TOKEN_ID"
```

Set `conversionProfileId=-1` to skip transcoding for data entries.

### Direct-Serve URL for Non-Media Entries

Non-media entries (documents and data) can be served directly via CDN using the raw serve URL:

```
https://cdnapisec.kaltura.com/p/{PARTNER_ID}/raw/entry_id/{ENTRY_ID}/direct_serve/1/forceproxy/true/{FILE_NAME}
```

This returns the original file as-is. Use this URL pattern to serve documents, JSON files, configuration data, or any non-media content stored in Kaltura.

### Choosing the Right Entry Type

- **Media entries** — Use for video, audio, and images. Kaltura transcodes and creates playable renditions (flavors). Delivered via `playManifest` URLs (HLS, DASH).  
- **Document entries** — Use for PDFs and office documents. Kaltura converts for web viewing. Use when you need document preview or slide synchronization.  
- **Data entries** — Use for any other file type (JSON, CSV, ZIP, executables, etc.). Stored and served as-is with no processing. Use when Kaltura is your file storage backend.  
- **Attachment assets** (section 4.4) — Use to attach supplementary files to an existing media entry. The attachment is linked to the parent entry, not a standalone entry.


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

## 4.2 Dynamic Thumbnail API (URL-Based)

Generate thumbnails on the fly via URL parameters. CDN-cached — use for responsive thumbnails, per-request customization, or video frame extraction.

**URL pattern:**
```
https://cdnapisec.kaltura.com/p/{PARTNER_ID}/thumbnail/entry_id/{ENTRY_ID}/param/value/...
```

**Core parameters:**

| Parameter | Description |
|-----------|-------------|
| `/width/{W}` | Width in pixels |
| `/height/{H}` | Height in pixels |
| `/type/{T}` | Crop mode: `1`=resize to fit, `2`=center + pad, `3`=center crop, `4`=top crop, `5`=stretch |
| `/quality/{Q}` | JPEG quality (0-100) |
| `/format/{F}` | Output format: `jpg`, `png`, `png8`, `png24`, `png32`, `png48`, `png64`, `bmp`, `gif`, `tif`, `psd`, `pdf` |
| `/bgcolor/{HEX}` | Background color for padding (hex, e.g., `ff0000`) |
| `/nearest_aspect_ratio/{0\|1}` | Round to nearest standard aspect ratio |

**Video frame extraction:**

| Parameter | Description |
|-----------|-------------|
| `/vid_sec/{S}` | Capture frame at specific second |
| `/vid_slice/{N}` | Extract slice N from a strip (use with `vid_slices`) |
| `/vid_slices/{TOTAL}` | Divide video into TOTAL equal segments for sprite strips |
| `/start_sec/{S}` | Start of time range (with `vid_slices`) |
| `/end_sec/{S}` | End of time range (with `vid_slices`) |

**Crop region (advanced):**

| Parameter | Description |
|-----------|-------------|
| `/src_x/{X}` | Source crop X offset |
| `/src_y/{Y}` | Source crop Y offset |
| `/src_w/{W}` | Source crop width |
| `/src_h/{H}` | Source crop height |
| `/rel_width/{W}` | Relative coordinate system width |
| `/rel_height/{H}` | Relative coordinate system height |

**Source and access:**

| Parameter | Description |
|-----------|-------------|
| `/flavor_id/{ID}` | Generate from a specific flavor (rendition) |
| `/upload_token_id/{ID}` | Generate thumbnail from an in-progress upload token |
| `/version/{V}` | Thumbnail version |
| `/ks/{KS}` | KS for access-controlled entries |
| `/referrer/{BASE64}` | Base64-encoded referrer for domain restrictions |
| `/file_name/{NAME}` | Download filename (must be last parameter) |

**Examples:**

```
# Default thumbnail
https://cdnapisec.kaltura.com/p/12345/thumbnail/entry_id/0_abc123

# Responsive: 640x360, center-cropped, at 30 seconds
https://cdnapisec.kaltura.com/p/12345/thumbnail/entry_id/0_abc123/width/640/height/360/type/3/vid_sec/30

# High-quality PNG for downloads
https://cdnapisec.kaltura.com/p/12345/thumbnail/entry_id/0_abc123/width/1920/height/1080/quality/100/format/png

# CSS sprite strip: 10 slices for hover preview
https://cdnapisec.kaltura.com/p/12345/thumbnail/entry_id/0_abc123/width/160/height/90/vid_slices/10

# Padded with white background
https://cdnapisec.kaltura.com/p/12345/thumbnail/entry_id/0_abc123/width/400/height/400/type/2/bgcolor/ffffff
```

## 4.3 thumbAsset API (Stored Thumbnails)

The `thumbAsset` service manages persistent, editorial thumbnails attached to entries. Use when you need multiple thumbnails per entry, custom-uploaded images, or saved video frame captures.

**thumbAsset.add — Upload a custom thumbnail:**

```bash
# Step 1: Create the thumb asset
curl -X POST "$KALTURA_SERVICE_URL/service/thumbAsset/action/add" \
  -d "ks=$KALTURA_KS" \
  -d "format=1" \
  -d "entryId=$KALTURA_ENTRY_ID" \
  -d "thumbAsset[objectType]=KalturaThumbAsset"

# Step 2: Upload the image using an upload token
curl -X POST "$KALTURA_SERVICE_URL/service/thumbAsset/action/setContent" \
  -d "ks=$KALTURA_KS" \
  -d "format=1" \
  -d "id=THUMB_ASSET_ID" \
  -d "contentResource[objectType]=KalturaUploadedFileTokenResource" \
  -d "contentResource[token]=$UPLOAD_TOKEN_ID"
```

**thumbAsset.generate — Capture frame from video:**

```bash
curl -X POST "$KALTURA_SERVICE_URL/service/thumbAsset/action/generate" \
  -d "ks=$KALTURA_KS" \
  -d "format=1" \
  -d "entryId=$KALTURA_ENTRY_ID" \
  -d "thumbParams[objectType]=KalturaThumbParams" \
  -d "thumbParams[videoOffset]=30"
```

**thumbAsset.setAsDefault — Set which thumbnail displays:**

```bash
curl -X POST "$KALTURA_SERVICE_URL/service/thumbAsset/action/setAsDefault" \
  -d "ks=$KALTURA_KS" \
  -d "format=1" \
  -d "thumbAssetId=THUMB_ASSET_ID"
```

**thumbAsset.list — List all thumbnails for an entry:**

```bash
curl -X POST "$KALTURA_SERVICE_URL/service/thumbAsset/action/list" \
  -d "ks=$KALTURA_KS" \
  -d "format=1" \
  -d "filter[entryIdEqual]=$KALTURA_ENTRY_ID"
```

**thumbAsset.get — Retrieve a specific thumbnail asset:**

```bash
curl -X POST "$KALTURA_SERVICE_URL/service/thumbAsset/action/get" \
  -d "ks=$KALTURA_KS" \
  -d "format=1" \
  -d "thumbAssetId=THUMB_ASSET_ID"
```

**thumbAsset.delete — Remove a thumbnail asset:**

```bash
curl -X POST "$KALTURA_SERVICE_URL/service/thumbAsset/action/delete" \
  -d "ks=$KALTURA_KS" \
  -d "format=1" \
  -d "thumbAssetId=THUMB_ASSET_ID"
```

**When to use which:**
- **Dynamic Thumbnail API** (section 4.2) — On-the-fly delivery for responsive UIs, hover previews, video frame extraction. CDN-cached, no stored assets created. Best for displaying thumbnails at different sizes.
- **thumbAsset API** (this section) — Stored editorial thumbnails when you need multiple persistent thumbnails per entry, custom-uploaded images, or specific frame captures saved permanently. Best for managing which thumbnail is the "default" for an entry.

## 4.4 Non-Media File Attachments (attachmentAsset)

Kaltura manages any file type, not just media. The `attachment_attachmentAsset` plugin service attaches non-media files to media entries (shown as "Related Files" in KMC).

```bash
# Step 1: Create the attachment asset
curl -X POST "$KALTURA_SERVICE_URL/service/attachment_attachmentAsset/action/add" \
  -d "ks=$KALTURA_KS" \
  -d "format=1" \
  -d "entryId=$KALTURA_ENTRY_ID" \
  -d "attachmentAsset[objectType]=KalturaAttachmentAsset" \
  -d "attachmentAsset[title]=Slide Deck" \
  -d "attachmentAsset[format]=3" \
  -d "attachmentAsset[fileExt]=pdf"

# Step 2: Upload the file using an upload token (same lifecycle as media)
curl -X POST "$KALTURA_SERVICE_URL/service/attachment_attachmentAsset/action/setContent" \
  -d "ks=$KALTURA_KS" \
  -d "format=1" \
  -d "id=$ATTACHMENT_ASSET_ID" \
  -d "contentResource[objectType]=KalturaUploadedFileTokenResource" \
  -d "contentResource[token]=$UPLOAD_TOKEN_ID"

# List attachments for an entry
curl -X POST "$KALTURA_SERVICE_URL/service/attachment_attachmentAsset/action/list" \
  -d "ks=$KALTURA_KS" \
  -d "format=1" \
  -d "filter[entryIdEqual]=$KALTURA_ENTRY_ID"
```

**Attachment format types:**

| Value | Name | Description |
|-------|------|-------------|
| 1 | TEXT | Plain text files |
| 2 | MEDIA | Media files not for transcoding (supplementary media) |
| 3 | DOCUMENT | Documents (PDF, DOCX, PPTX, etc.) |
| 4 | JSON | Structured JSON data |

Attachments follow the same `uploadToken` lifecycle as media uploads — create a token, upload the file, then attach it to the asset.

**Content-Type auto-detection:** Kaltura automatically detects MIME types during upload based on file content and extension. You do not need to specify Content-Type headers for the uploaded file — the server inspects the file and assigns the correct type. For media entries, this determines the transcoding pipeline (video vs. audio vs. image). For attachments, it determines the `format` value if not explicitly set.


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
  -F "format=1" \
  -F "uploadTokenId=$UPLOAD_TOKEN_ID" \
  -F "resume=false" \
  -F "resumeAt=0" \
  -F "finalChunk=false" \
  -F "fileData=@-;filename=chunk_0"

# Chunk 2 (next 2 MB)
dd if=my_video.mp4 bs=2097152 count=1 skip=1 2>/dev/null | \
curl -X POST "$KALTURA_SERVICE_URL/service/uploadToken/action/upload" \
  -F "ks=$KALTURA_KS" \
  -F "format=1" \
  -F "uploadTokenId=$UPLOAD_TOKEN_ID" \
  -F "resume=true" \
  -F "resumeAt=2097152" \
  -F "finalChunk=false" \
  -F "fileData=@-;filename=chunk_2097152"

# Chunk 3 / final chunk (last 2 MB)
dd if=my_video.mp4 bs=2097152 count=1 skip=2 2>/dev/null | \
curl -X POST "$KALTURA_SERVICE_URL/service/uploadToken/action/upload" \
  -F "ks=$KALTURA_KS" \
  -F "format=1" \
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


# 9. Error Handling

| Error Code | Meaning | Resolution |
|------------|---------|------------|
| `UPLOAD_TOKEN_NOT_FOUND` | Token ID does not exist or expired | Create a new token with `uploadToken.add` |
| `UPLOADED_FILE_NOT_FOUND_BY_TOKEN` | Upload not yet completed for this token | Complete the upload before calling `media.addContent` |
| `ENTRY_ID_NOT_FOUND` | Entry ID does not exist | Verify the entry ID; entry may have been deleted or not yet created |
| `INVALID_ENTRY_TYPE` | Operation not supported for this entry type | `media.addContent` requires a media entry created via `media.add` |
| `MAX_FILE_SIZE_EXCEEDED` | File exceeds the partner's upload limit | Use chunked upload for large files, or contact account manager for limit increase |
| Import stuck at status 0 | `addFromUrl` URL is a redirect (e.g., `playManifest`) | Use a direct MP4 download URL, not a streaming manifest URL |

**Retry strategy:** For transient errors (HTTP 5xx, timeouts), retry with exponential backoff: 1s, 2s, 4s, with jitter, up to 3 retries. For client errors (`UPLOAD_TOKEN_NOT_FOUND`, `ENTRY_ID_NOT_FOUND`, `MAX_FILE_SIZE_EXCEEDED`), fix the request before retrying — these will not resolve on their own. For async operations (entry transcoding, URL imports), poll with increasing intervals (5s, 10s, 30s) rather than tight loops.

# 10. Best Practices

- **Use chunked upload for files > 10 MB.** Chunked upload supports resume on failure via `resumeAt` parameter.
- **Use `addFromUrl` for remote files.** Provide direct MP4 download URLs — redirect URLs (playManifest, HLS) cause import failures.
- **Poll for READY status after upload.** Check `baseEntry.get` for `status=2` before performing operations on the entry.
- **Use Access Control profiles** to restrict content delivery by IP, domain, geo, or scheduling rather than implementing custom access checks.
- **Use thumbnail API for previews.** Generate thumbnails dynamically via the thumbnail API rather than storing separate image files.
- **Use AppTokens for upload services.** Scope the AppToken with `edit:*` privilege for upload-only access.
- **Set up Agents Manager or REACH automation rules** to auto-process uploaded content (captions, translation, summarization) rather than implementing manual post-upload workflows.
- **10,000 result limit on list/search.** Kaltura enforces a 10K result cap on list operations (500 results/page x 20 pages max). To traverse a full content library, use `createdAtGreaterThanOrEqual` and `createdAtLessThanOrEqual` date-window filters to page through results in batches. Move the date window forward after each batch.
- **Use multirequest for browser uploads.** Combine `uploadToken.add` + `media.add` + `media.addContent` in a single HTTP request to reduce round trips. See [API Getting Started](KALTURA_API_GETTING_STARTED.md) for multirequest syntax.

# 11. Related Guides

- **[Session Guide](KALTURA_SESSION_GUIDE.md)** — How to create and manage KS tokens
- **[AppTokens Guide](KALTURA_APPTOKENS_API.md)** — Secure token-based auth for upload integrations
- **[eSearch Guide](KALTURA_ESEARCH_API.md)** — Search for entries after upload
- **[Player Embed Guide](KALTURA_PLAYER_EMBED_GUIDE.md)** — Embed uploaded content
- **[REACH Guide](KALTURA_REACH_API.md)** — Enrichment services marketplace: captions, translation, moderation, and more for uploaded content
- **[Agents Manager](KALTURA_AGENTS_MANAGER_API.md)** — Auto-process uploaded content (triggers on ENTRY_READY)
- **[AI Genie](KALTURA_AI_GENIE_API.md)** — Search uploaded content via conversational AI
- **[Events Platform](KALTURA_EVENTS_PLATFORM_API.md)** — Upload logo/banner assets for virtual events
- **[Multi-Stream](KALTURA_MULTI_STREAM_API.md)** — Create synchronized dual/multi-screen entries using parent-child relationships
- **[Webhooks API](KALTURA_WEBHOOKS_API.md)** — Get notified when entries finish processing (HTTP callbacks on entry events)
- **[Distribution](KALTURA_DISTRIBUTION_API.md)** — Distributed content must first be uploaded and transcoded
- **[Syndication](KALTURA_SYNDICATION_API.md)** — Syndication feeds serve uploaded content via feed URLs
- **[API Getting Started](KALTURA_API_GETTING_STARTED.md)** — Foundation guide covering content model and API patterns

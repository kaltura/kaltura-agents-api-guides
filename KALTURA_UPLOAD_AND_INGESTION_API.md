# Kaltura Upload & Ingestion API

This guide covers the complete lifecycle of getting content into Kaltura: creating upload tokens, uploading files (including chunked/resumable transfers), creating media, document, and data entries, importing from URLs, copying entries, replacing content, and managing flavor assets and attachments.

**Base URL:** `$KALTURA_SERVICE_URL` (default: `https://www.kaltura.com/api_v3`)  
**Auth:** All requests require a valid KS (see [Session Guide](KALTURA_SESSION_GUIDE.md))  
**Format:** Form-encoded POST, `format=1` for JSON responses  

<!-- Sections: 1.When to Use | 2.Prerequisites | 3.Upload Lifecycle Overview | 4.Upload Token API | 5.Creating Media Entries (16 resource types, clipping, multi-flavor) | 6.Entry CRUD Operations | 7.Cross-Type Entry Operations (baseEntry.clone) | 8.Non-Media Entry Types | 9.Flavor Assets (Transcoded Renditions) | 10.Attachment Assets (Non-Media File Attachments) | 11.Bulk Upload | 12.Complete Example -- Chunked Upload Workflow | 13.Error Handling | 14.Best Practices | 15.Related Guides -->


# 1. When to Use

| Scenario | What to Use |
|----------|-------------|
| **Media onboarding pipeline** — Ingest video, audio, or images from local storage | `uploadToken` + `media.add` + `media.addContent` with `KalturaUploadedFileTokenResource` |
| **CMS integration** — Programmatic upload with progress tracking and resume | Chunked `uploadToken.upload` with `resume=true` |
| **Bulk migration** — Move thousands of files from an existing library | `media.add` + `media.addContent` with `KalturaUrlResource`, or CSV `bulkUploadAdd` |
| **Content replacement** — Swap a video's source file without changing its entry ID | `media.updateContent` |
| **Entry cloning** — Duplicate an entry with all metadata and assets | `baseEntry.clone` (full deep copy with granular options) |
| **Clipping / trimming** — Extract a time segment from an existing video | `media.addContent` with `KalturaOperationResource` + `KalturaClipAttributes` |
| **Concatenation** — Combine segments from multiple videos into one | `media.addContent` with `KalturaOperationResources` (plural) |
| **Multi-bitrate ingest** — Upload pre-transcoded renditions without re-encoding | `media.addContent` with `KalturaAssetsParamsResourceContainers` |
| **SFTP import** — Pull files from secure servers with SSH key auth | `media.addContent` with `KalturaSshUrlResource` |
| **Remote storage** — Register content on external CDN/S3 without copying | `media.addContent` with `KalturaRemoteStorageResource` |
| **Document management** — Upload PDFs, slides, or Word docs for web viewing | `documents.addContent` with `KalturaDocumentEntry` |
| **Arbitrary file storage** — Store JSON, CSV, ZIP, or config files | `data.add` with `KalturaDataEntry` (type=6) |
| **Supplementary files** — Attach transcripts, slide decks, or data files to a video | `attachmentAsset.add` + `attachmentAsset.setContent` |
| **Automated post-upload processing** — Trigger captions, translation, or AI enrichment | Upload, then use [Agents Manager](KALTURA_AGENTS_MANAGER_API.md) or [REACH](KALTURA_REACH_API.md) rules |


# 2. Prerequisites

- **Kaltura Session (KS):** ADMIN KS (type=2) for upload and entry management. See [Session Guide](KALTURA_SESSION_GUIDE.md).  
- **Partner ID and API credentials:** Available from KMC > Settings > Integration Settings.  
- **Service URL:** Set `$KALTURA_SERVICE_URL` to your regional endpoint (default: `https://www.kaltura.com/api_v3`).  
- **Permissions:** `CONTENT_MANAGE_BASE` permission for creating entries and uploading content.


# 3. Upload Lifecycle Overview

Every file upload follows this pattern:

```
uploadToken.add  -->  uploadToken.upload (one or more chunks)  -->  entry.add  -->  entry.addContent
```

1. **Create an upload token** -- a server-side container that will hold the file  
2. **Upload file data** -- send the file bytes (single shot or chunked) to the token  
3. **Create an entry** -- the logical object (metadata, name, type)  
4. **Attach content** -- link the upload token to the entry, triggering transcoding  

Alternative paths:

| Method | Use Case | Requires Local File? |
|--------|----------|---------------------|
| `uploadToken` + `media.addContent` | Full control, chunked/resumable upload | Yes |
| `media.addContent` with `KalturaUrlResource` | Import from a remote URL (Kaltura fetches the file) | No |
| `media.addContent` with `KalturaEntryResource` | Copy content from an existing entry's source flavor | No |
| `media.addContent` with `KalturaAssetResource` | Create entry from a specific transcoded rendition | No |
| `media.addContent` with `KalturaOperationResource` | Clip/trim/effects from an existing entry | No |
| `media.addContent` with `KalturaOperationResources` | Concatenate segments from multiple entries | No |
| `media.addContent` with `KalturaAssetsParamsResourceContainers` | Multi-flavor ingest (pre-transcoded files) | No (URLs) or Yes (tokens) |
| `media.addContent` with `KalturaSshUrlResource` | Import from SFTP server with SSH keys | No |
| `media.addContent` with `KalturaRemoteStorageResource` | Register on external storage without copy | No |
| `media.bulkUploadAdd` | Batch ingest via CSV or XML | No (URLs in CSV) |
| `baseEntry.clone` | Deep-clone entry with all assets and metadata | No |


# 4. Upload Token API

The `uploadToken` service manages server-side containers for receiving file data. Tokens support single-shot uploads, chunked uploads with parallel transfers, and auto-finalization.

## 4.1 Create an Upload Token

```
POST /api_v3/service/uploadToken/action/add
```

| Parameter | Type | Description |
|-----------|------|-------------|
| `uploadToken[fileName]` | string | Original file name (optional, for tracking) |
| `uploadToken[fileSize]` | float | Expected file size in bytes (optional; **required** when using `autoFinalize`) |
| `uploadToken[autoFinalize]` | int | Set to `1` to auto-complete the upload when `uploadedFileSize` matches `fileSize`. Eliminates the need to send `finalChunk=true` on the last chunk |

**Response:** `KalturaUploadToken` object:

| Field | Type | Description |
|-------|------|-------------|
| `id` | string | Unique token ID (use in subsequent upload/addContent calls) |
| `status` | int | Token status (see table below) |
| `fileName` | string | File name set at creation |
| `fileSize` | float | Expected file size |
| `uploadedFileSize` | float | Bytes uploaded so far |
| `uploadUrl` | string | DC-specific URL for upload calls (use when your account spans multiple data centers) |
| `createdAt` | int | Unix timestamp |

**Token statuses:**

| Value | Name | Meaning |
|-------|------|---------|
| 0 | PENDING | Created, no data uploaded yet |
| 1 | PARTIAL_UPLOAD | Some chunks received |
| 2 | FULL_UPLOAD | All data received |
| 3 | CLOSED | Token consumed by addContent |
| 4 | TIMED_OUT | Token expired (partial uploads expire after 7 days) |
| 5 | DELETED | Token deleted |

```bash
curl -X POST "$KALTURA_SERVICE_URL/service/uploadToken/action/add" \
  -d "ks=$KALTURA_KS" \
  -d "format=1" \
  -d "uploadToken[fileName]=my_video.mp4" \
  -d "uploadToken[fileSize]=15728640"
```

## 4.2 Upload File Data (Single or Chunked)

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

Split the file into chunks and upload each sequentially. The server accepts parallel chunk uploads — chunks can arrive out of order as long as each specifies the correct `resumeAt` offset.

**Protocol:**
1. **First chunk:** `resume=false`, `finalChunk=false`  
2. **Middle chunks:** `resume=true`, `finalChunk=false`, with `resumeAt` = byte offset  
3. **Final chunk:** `resume=true`, `finalChunk=true`, with `resumeAt` = byte offset. Can be zero-size (just signals completion)  

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

**Resume after failure:** Call `uploadToken.get` to check `uploadedFileSize`, then resume from that offset:

```bash
curl -X POST "$KALTURA_SERVICE_URL/service/uploadToken/action/get" \
  -d "ks=$KALTURA_KS" \
  -d "format=1" \
  -d "uploadTokenId=$UPLOAD_TOKEN_ID"
# Response includes: "uploadedFileSize": 4194304

RESUME_AT=4194304
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

**Chunk sizing guidance:** Use 2-5 MB chunks for files under 100 MB and 10-50 MB chunks for larger files. Smaller chunks mean more HTTP requests but easier recovery; larger chunks reduce overhead but require re-uploading more data on failure.

**Auto-finalize:** When creating a token with `autoFinalize=1` and `fileSize` set, the server automatically marks the upload complete when `uploadedFileSize` matches `fileSize`. This eliminates the need for a zero-byte final chunk.

## 4.3 Check Token Status

```
POST /api_v3/service/uploadToken/action/get
```

| Parameter | Type | Description |
|-----------|------|-------------|
| `uploadTokenId` | string | The token ID |

Returns the token object with `uploadedFileSize` (bytes uploaded so far) and `status`. User sessions are restricted to their own tokens.

## 4.4 List Upload Tokens

```
POST /api_v3/service/uploadToken/action/list
```

| Parameter | Type | Description |
|-----------|------|-------------|
| `filter[statusEqual]` | int | Filter by token status |
| `filter[statusIn]` | string | Comma-separated status values |
| `filter[fileNameEqual]` | string | Filter by file name |
| `filter[userIdEqual]` | string | Filter by user (admin only) |
| `pager[pageSize]` | int | Results per page |
| `pager[pageIndex]` | int | Page number (1-based) |

User sessions only see their own tokens.

## 4.5 Delete an Upload Token

```
POST /api_v3/service/uploadToken/action/delete
```

Use this to clean up abandoned uploads. Tokens are auto-deleted after consumption by `addContent`. Partial uploads expire after 7 days (`TIMED_OUT` status).


# 5. Creating Media Entries

## 5.1 media.add -- Create Entry Metadata

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
| `entry[referenceId]` | string | External reference ID for cross-system linking (optional) |
| `entry[conversionProfileId]` | int | Override default transcoding profile (optional) |

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

## 5.2 media.addContent -- Attach Upload Token to Entry

```
POST /api_v3/service/media/action/addContent
```

| Parameter | Type | Description |
|-----------|------|-------------|
| `entryId` | string | The entry ID from media.add |
| `resource[objectType]` | string | Resource type (see table below) |
| `resource[token]` | string | Upload token ID (for `KalturaUploadedFileTokenResource`) |

**Content resource types:** The `resource` parameter accepts any of these types:

| Resource Type | Description | Use Case |
|--------------|-------------|----------|
| `KalturaUploadedFileTokenResource` | Attach content from an upload token | Standard upload workflow (most common) |
| `KalturaUrlResource` | Import from HTTP/HTTPS/FTP URL | Remote file import |
| `KalturaEntryResource` | Copy content from another entry's flavor | Entry content duplication |
| `KalturaAssetResource` | Copy from a specific flavor asset by ID | Flavor-level content copy |
| `KalturaOperationResource` | Clip, trim, or apply effects to source content | Clipping, concatenation, effects |
| `KalturaAssetsParamsResourceContainers` | Multi-flavor ingest (multiple renditions at once) | Pre-transcoded multi-bitrate content |
| `KalturaRemoteStorageResource` | Register content on configured remote storage | External CDN/S3 content |
| `KalturaSshUrlResource` | Import via SSH/SFTP with key authentication | Secure server file transfer |
| `KalturaDropFolderFileResource` | Reference a file from a configured drop folder | Drop folder integration |
| `KalturaRemoteStorageResources` | Register content on multiple storage profiles | Multi-CDN/multi-region content |
| `KalturaStringResource` | Inline string content (text, XML, JSON) | Caption content, data entries |
| `KalturaUploadedFileResource` | Direct multipart file upload (no token) | Simple single-request upload |

Two additional types exist for internal/system use only (`KalturaServerFileResource`, `KalturaFileSyncResource`) and are not available to customer accounts.

Triggers transcoding. Entry status changes from `NO_CONTENT (7)` to `IMPORT (0)` or `PENDING (4)`.

```bash
curl -X POST "$KALTURA_SERVICE_URL/service/media/action/addContent" \
  -d "ks=$KALTURA_KS" \
  -d "format=1" \
  -d "entryId=$KALTURA_ENTRY_ID" \
  -d "resource[objectType]=KalturaUploadedFileTokenResource" \
  -d "resource[token]=$UPLOAD_TOKEN_ID"
```

## 5.3 media.updateContent -- Replace an Entry's Source File

```
POST /api_v3/service/media/action/updateContent
```

| Parameter | Type | Description |
|-----------|------|-------------|
| `entryId` | string | Entry ID to update |
| `resource[objectType]` | string | Resource type (same options as addContent) |
| `resource[token]` | string | Upload token ID |
| `conversionProfileId` | int | Override transcoding profile (optional) |

Replaces the source file while preserving the entry ID, metadata, embed codes, and analytics. The entry enters a "pending replacement" state until transcoding completes. Uses locking to prevent concurrent replacements.

```bash
curl -X POST "$KALTURA_SERVICE_URL/service/media/action/updateContent" \
  -d "ks=$KALTURA_KS" \
  -d "format=1" \
  -d "entryId=$KALTURA_ENTRY_ID" \
  -d "resource[objectType]=KalturaUploadedFileTokenResource" \
  -d "resource[token]=$UPLOAD_TOKEN_ID"
```

**Business scenario — version management:** A training team records lecture updates. They replace the video file on the existing entry so all existing playlists, embed codes, and analytics continue working with the new version.

## 5.4 media.approveReplace / media.cancelReplace

When content replacement is configured to require approval:

```bash
# Approve pending replacement
curl -X POST "$KALTURA_SERVICE_URL/service/media/action/approveReplace" \
  -d "ks=$KALTURA_KS" \
  -d "format=1" \
  -d "entryId=$KALTURA_ENTRY_ID"

# Cancel pending replacement
curl -X POST "$KALTURA_SERVICE_URL/service/media/action/cancelReplace" \
  -d "ks=$KALTURA_KS" \
  -d "format=1" \
  -d "entryId=$KALTURA_ENTRY_ID"
```

## 5.5 Import from URL (KalturaUrlResource)

Use `media.add` + `media.addContent` with `KalturaUrlResource` to import content from a remote URL. Kaltura fetches the file server-side via an async import job. Entry transitions from `NO_CONTENT (7)` → `IMPORT (0)` → `READY (2)`.

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `resource[objectType]` | string | Yes | `KalturaUrlResource` |
| `resource[url]` | string | Yes | Direct file URL (HTTP, HTTPS, or FTP) |
| `resource[urlHeaders]` | array | No | Custom HTTP headers for the download request (e.g., auth tokens) |
| `resource[forceAsyncDownload]` | bool | No | Force async import job |

```bash
curl -X POST "$KALTURA_SERVICE_URL/service/media/action/addContent" \
  -d "ks=$KALTURA_KS" \
  -d "format=1" \
  -d "entryId=$KALTURA_ENTRY_ID" \
  -d "resource[objectType]=KalturaUrlResource" \
  -d "resource[url]=https://example.com/sample_video.mp4"
```

With custom headers (e.g., for authenticated sources):

```bash
curl -X POST "$KALTURA_SERVICE_URL/service/media/action/addContent" \
  -d "ks=$KALTURA_KS" \
  -d "format=1" \
  -d "entryId=$KALTURA_ENTRY_ID" \
  -d "resource[objectType]=KalturaUrlResource" \
  -d "resource[url]=https://storage.example.com/assets/video.mp4" \
  -d "resource[urlHeaders][0]=Authorization: Bearer YOUR_TOKEN"
```

The URL must point to a direct downloadable file. Streaming manifests (HLS/DASH), redirect URLs (playManifest), and HTML pages cause import failures. Poll `media.get` until status reaches `2` (READY).

**Business scenario — content migration:** A media company migrating from another platform exports a CSV of asset URLs. A script iterates through the CSV, creating entries and attaching URL resources for each, then polls until entries reach READY status.

## 5.6 Copy from Existing Entry (KalturaEntryResource)

Use `media.add` + `media.addContent` with `KalturaEntryResource` to create a new entry by copying content from an existing one. The new entry gets its own transcoding run.

```bash
curl -X POST "$KALTURA_SERVICE_URL/service/media/action/add" \
  -d "ks=$KALTURA_KS" \
  -d "format=1" \
  -d "entry[objectType]=KalturaMediaEntry" \
  -d "entry[name]=Copy of Original"
```

Then attach the source entry's content:

```bash
curl -X POST "$KALTURA_SERVICE_URL/service/media/action/addContent" \
  -d "ks=$KALTURA_KS" \
  -d "format=1" \
  -d "entryId=$KALTURA_ENTRY_ID" \
  -d "resource[objectType]=KalturaEntryResource" \
  -d "resource[entryId]=$SOURCE_ENTRY_ID" \
  -d "resource[flavorParamsId]=0"
```

Set `resource[flavorParamsId]=0` to copy the original source flavor. Specify a different flavor params ID to copy a specific rendition only.

**Business scenario — multi-tenant content:** A SaaS platform distributes the same training video to multiple customer accounts, each needing independent analytics and access control.

## 5.7 Copy from Specific Flavor Asset (KalturaAssetResource)

Use `media.addContent` with `KalturaAssetResource` to create a new entry from a specific transcoded rendition of an existing entry. Unlike `KalturaEntryResource` (which references by entry ID + flavor params), this references a flavor asset directly by its ID.

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `resource[objectType]` | string | Yes | `KalturaAssetResource` |
| `resource[assetId]` | string | Yes | The flavor asset ID to copy from |

```bash
curl -X POST "$KALTURA_SERVICE_URL/service/media/action/addContent" \
  -d "ks=$KALTURA_KS" \
  -d "format=1" \
  -d "entryId=$KALTURA_ENTRY_ID" \
  -d "resource[objectType]=KalturaAssetResource" \
  -d "resource[assetId]=$FLAVOR_ASSET_ID"
```

**Business scenario — derivative content:** A video platform extracts the audio-only rendition from a lecture recording to create a podcast entry.

## 5.8 Import via SSH/SFTP (KalturaSshUrlResource)

Use `KalturaSshUrlResource` to import files from SSH/SFTP servers with key authentication.

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `resource[objectType]` | string | Yes | `KalturaSshUrlResource` |
| `resource[url]` | string | Yes | SFTP URL (e.g., `sftp://host/path/file.mp4`) |
| `resource[privateKey]` | string | No | SSH private key content |
| `resource[publicKey]` | string | No | SSH public key content |
| `resource[keyPassphrase]` | string | No | Passphrase for the SSH key |

```bash
curl -X POST "$KALTURA_SERVICE_URL/service/media/action/addContent" \
  -d "ks=$KALTURA_KS" \
  -d "format=1" \
  -d "entryId=$KALTURA_ENTRY_ID" \
  -d "resource[objectType]=KalturaSshUrlResource" \
  -d "resource[url]=sftp://media-server.example.com/incoming/video.mp4" \
  -d "resource[privateKey]=$SSH_PRIVATE_KEY" \
  -d "resource[publicKey]=$SSH_PUBLIC_KEY"
```

**Business scenario — broadcast ingest:** A television network's production workflow deposits finished segments on an SFTP server. An automated pipeline picks them up via `KalturaSshUrlResource` for publishing.

## 5.9 Remote Storage (KalturaRemoteStorageResource)

Use `KalturaRemoteStorageResource` to register content that lives on a configured remote storage profile (e.g., your own S3 bucket or CDN) without downloading it into Kaltura storage. The file stays in place — Kaltura creates a reference to serve it from its current location.

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `resource[objectType]` | string | Yes | `KalturaRemoteStorageResource` |
| `resource[url]` | string | Yes | Path/URL on the remote storage |
| `resource[storageProfileId]` | int | Yes | ID of the configured storage profile |

```bash
curl -X POST "$KALTURA_SERVICE_URL/service/media/action/addContent" \
  -d "ks=$KALTURA_KS" \
  -d "format=1" \
  -d "entryId=$KALTURA_ENTRY_ID" \
  -d "resource[objectType]=KalturaRemoteStorageResource" \
  -d "resource[url]=/videos/2024/keynote_1080p.mp4" \
  -d "resource[storageProfileId]=$STORAGE_PROFILE_ID"
```

Requires a storage profile configured on your account (one-time setup by your Kaltura account team). For registering the same content on multiple storage profiles simultaneously, use `KalturaRemoteStorageResources` (plural) with an array of resources.

**Business scenario — hybrid storage:** An enterprise keeps original source files in their own S3 bucket for compliance. They register these with Kaltura for playback and metadata management without moving the files.

## 5.10 Drop Folder Files (KalturaDropFolderFileResource)

Use `KalturaDropFolderFileResource` to reference a file that arrived through a configured drop folder (FTP, SFTP, S3, or local directory watched by Kaltura).

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `resource[objectType]` | string | Yes | `KalturaDropFolderFileResource` |
| `resource[dropFolderFileId]` | int | Yes | ID of the drop folder file object |

```bash
curl -X POST "$KALTURA_SERVICE_URL/service/media/action/addContent" \
  -d "ks=$KALTURA_KS" \
  -d "format=1" \
  -d "entryId=$KALTURA_ENTRY_ID" \
  -d "resource[objectType]=KalturaDropFolderFileResource" \
  -d "resource[dropFolderFileId]=$DROP_FOLDER_FILE_ID"
```

Requires the Drop Folder plugin enabled and a configured drop folder on your account. Files deposited in the drop folder are detected automatically; use this resource type when you need to manually associate a drop folder file with an entry.

## 5.11 Inline String Content (KalturaStringResource)

Use `KalturaStringResource` to create entries from inline text content. Commonly used for data entries, inline caption content, or metadata files.

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `resource[objectType]` | string | Yes | `KalturaStringResource` |
| `resource[content]` | string | Yes | The text content to store |

```bash
curl -X POST "$KALTURA_SERVICE_URL/service/data/action/addContent" \
  -d "ks=$KALTURA_KS" \
  -d "format=1" \
  -d "entryId=$DATA_ENTRY_ID" \
  -d "resource[objectType]=KalturaStringResource" \
  -d "resource[content]={\"config\": \"value\", \"version\": 2}"
```

Also used with `captionAsset.setContent` to set caption text directly:

```bash
curl -X POST "$KALTURA_SERVICE_URL/service/caption_captionAsset/action/setContent" \
  -d "ks=$KALTURA_KS" \
  -d "format=1" \
  -d "id=$CAPTION_ASSET_ID" \
  -d "resource[objectType]=KalturaStringResource" \
  -d "resource[content]=WEBVTT%0A%0A00:00:00.000 --> 00:00:05.000%0AHello world"
```

## 5.12 Direct File Upload (KalturaUploadedFileResource)

Use `KalturaUploadedFileResource` for a single-request upload where the file is sent as multipart form data directly with the `addContent` call. Simpler than the upload token flow but limited by server upload size limits.

```bash
curl -X POST "$KALTURA_SERVICE_URL/service/media/action/addContent" \
  -F "ks=$KALTURA_KS" \
  -F "format=1" \
  -F "entryId=$KALTURA_ENTRY_ID" \
  -F "resource[objectType]=KalturaUploadedFileResource" \
  -F "resource[fileData]=@/path/to/video.mp4"
```

For files larger than 100 MB, use the upload token workflow (`KalturaUploadedFileTokenResource`) with chunked upload for resumability.

## 5.13 Clipping, Effects, and Composition (KalturaOperationResource)

Use `KalturaOperationResource` to create entries by extracting a clip (time segment) from existing content. This resource type also supports fade effects, overlays, background replacement, and caption burn-in.

For a quick clip with offset and duration:

```bash
curl -X POST "$KALTURA_SERVICE_URL/service/media/action/addContent" \
  -d "ks=$KALTURA_KS" \
  -d "format=1" \
  -d "entryId=$KALTURA_ENTRY_ID" \
  -d "resource[objectType]=KalturaOperationResource" \
  -d "resource[resource][objectType]=KalturaEntryResource" \
  -d "resource[resource][entryId]=$SOURCE_ENTRY_ID" \
  -d "resource[resource][flavorParamsId]=0" \
  -d "resource[operationAttributes][0][objectType]=KalturaClipAttributes" \
  -d "resource[operationAttributes][0][offset]=60000" \
  -d "resource[operationAttributes][0][duration]=30000"
```

For comprehensive documentation of all editing operations — trim, multi-clip concat, overlays, chroma-key background replacement, caption burn-in, effects, dimension control, and audio mixing — see the **[Video Editing API](KALTURA_VIDEO_EDITING_API.md)**.

## 5.14 Multi-Clip Concatenation (KalturaOperationResources)

Use `KalturaOperationResources` (plural) to concatenate segments from multiple source entries into a single output. For full documentation including dimension normalization, chapter naming, and advanced composition, see the **[Video Editing API](KALTURA_VIDEO_EDITING_API.md)**.

```bash
curl -X POST "$KALTURA_SERVICE_URL/service/media/action/addContent" \
  -d "ks=$KALTURA_KS" \
  -d "format=1" \
  -d "entryId=$KALTURA_ENTRY_ID" \
  -d "resource[objectType]=KalturaOperationResources" \
  -d "resource[resources][0][objectType]=KalturaOperationResource" \
  -d "resource[resources][0][resource][objectType]=KalturaEntryResource" \
  -d "resource[resources][0][resource][entryId]=$SOURCE_ENTRY_1" \
  -d "resource[resources][0][resource][flavorParamsId]=0" \
  -d "resource[resources][0][operationAttributes][0][objectType]=KalturaClipAttributes" \
  -d "resource[resources][0][operationAttributes][0][offset]=0" \
  -d "resource[resources][0][operationAttributes][0][duration]=10000" \
  -d "resource[resources][1][objectType]=KalturaOperationResource" \
  -d "resource[resources][1][resource][objectType]=KalturaEntryResource" \
  -d "resource[resources][1][resource][entryId]=$SOURCE_ENTRY_2" \
  -d "resource[resources][1][resource][flavorParamsId]=0" \
  -d "resource[resources][1][operationAttributes][0][objectType]=KalturaClipAttributes" \
  -d "resource[resources][1][operationAttributes][0][offset]=0" \
  -d "resource[resources][1][operationAttributes][0][duration]=15000"
```

## 5.15 Multi-Flavor Ingest (KalturaAssetsParamsResourceContainers)

Use `KalturaAssetsParamsResourceContainers` to ingest multiple pre-transcoded renditions in a single `addContent` call. Each rendition is mapped to a specific flavor params ID.

```bash
curl -X POST "$KALTURA_SERVICE_URL/service/media/action/addContent" \
  -d "ks=$KALTURA_KS" \
  -d "format=1" \
  -d "entryId=$KALTURA_ENTRY_ID" \
  -d "resource[objectType]=KalturaAssetsParamsResourceContainers" \
  -d "resource[resources][0][objectType]=KalturaAssetParamsResourceContainer" \
  -d "resource[resources][0][assetParamsId]=0" \
  -d "resource[resources][0][resource][objectType]=KalturaUrlResource" \
  -d "resource[resources][0][resource][url]=https://example.com/source_original.mp4" \
  -d "resource[resources][1][objectType]=KalturaAssetParamsResourceContainer" \
  -d "resource[resources][1][assetParamsId]=$FLAVOR_PARAMS_720P" \
  -d "resource[resources][1][resource][objectType]=KalturaUrlResource" \
  -d "resource[resources][1][resource][url]=https://example.com/video_720p.mp4" \
  -d "resource[resources][2][objectType]=KalturaAssetParamsResourceContainer" \
  -d "resource[resources][2][assetParamsId]=$FLAVOR_PARAMS_1080P" \
  -d "resource[resources][2][resource][objectType]=KalturaUrlResource" \
  -d "resource[resources][2][resource][url]=https://example.com/video_1080p.mp4"
```

Each `KalturaAssetParamsResourceContainer` maps:
- `assetParamsId` — the target flavor params ID (use `0` for original source, or specific flavor params IDs from your conversion profile)
- `resource` — any content resource type (`KalturaUrlResource`, `KalturaUploadedFileTokenResource`, etc.)

**Business scenario — broadcast workflow:** A broadcaster already has renditions at multiple bitrates from their production pipeline. They ingest all renditions at once, skipping re-transcoding and reducing time-to-publish.

## 5.16 Entry Statuses

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

## 5.17 Flavor Asset Statuses

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

## 5.18 Entry Moderation Statuses

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


# 6. Entry CRUD Operations

## 6.1 media.get -- Retrieve Entry Details

```
POST /api_v3/service/media/action/get
```

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `entryId` | string | Yes | The entry ID to retrieve |
| `version` | int | No | Specific version to retrieve (default: latest) |

```bash
curl -X POST "$KALTURA_SERVICE_URL/service/media/action/get" \
  -d "ks=$KALTURA_KS" \
  -d "format=1" \
  -d "entryId=$KALTURA_ENTRY_ID"
```

**Poll for READY status after upload:** After calling `media.addContent`, poll `media.get` until `status` reaches `2` (READY):

```bash
while true; do
  STATUS=$(curl -s -X POST "$KALTURA_SERVICE_URL/service/media/action/get" \
    -d "ks=$KALTURA_KS" \
    -d "format=1" \
    -d "entryId=$KALTURA_ENTRY_ID" | jq -r '.status')
  echo "Status: $STATUS"
  [ "$STATUS" = "2" ] && break
  [ "$STATUS" = "-1" ] && echo "Transcoding failed" && break
  [ "$STATUS" = "-2" ] && echo "Import failed" && break
  sleep 5
done
```

## 6.2 media.list -- Search and Filter Entries

```
POST /api_v3/service/media/action/list
```

| Parameter | Type | Description |
|-----------|------|-------------|
| `filter[objectType]` | string | `KalturaMediaEntryFilter` |
| `filter[nameLike]` | string | Partial name match |
| `filter[tagsMultiLikeOr]` | string | Match any of these comma-separated tags |
| `filter[mediaTypeEqual]` | int | `1`=Video, `2`=Image, `5`=Audio |
| `filter[statusEqual]` | int | Filter by entry status (e.g., `2` for READY) |
| `filter[createdAtGreaterThanOrEqual]` | int | Unix timestamp -- entries created after |
| `filter[createdAtLessThanOrEqual]` | int | Unix timestamp -- entries created before |
| `filter[orderBy]` | string | Sort order (e.g., `-createdAt`, `+plays`) |
| `pager[pageSize]` | int | Results per page (max 500) |
| `pager[pageIndex]` | int | Page number (1-based) |

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

Results beyond 10,000 total are not pageable. Use `createdAtGreaterThanOrEqual` date windowing to iterate large datasets.

## 6.3 media.count -- Count Matching Entries

```
POST /api_v3/service/media/action/count
```

Same filter parameters as `media.list`. Returns an integer count.

## 6.4 media.update -- Update Entry Metadata

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

Only include the fields you want to change -- omitted fields remain unchanged (partial update).

```bash
curl -X POST "$KALTURA_SERVICE_URL/service/media/action/update" \
  -d "ks=$KALTURA_KS" \
  -d "format=1" \
  -d "entryId=$KALTURA_ENTRY_ID" \
  -d "mediaEntry[objectType]=KalturaMediaEntry" \
  -d "mediaEntry[name]=Updated Title" \
  -d "mediaEntry[tags]=updated,production"
```

## 6.5 media.delete -- Delete an Entry

```
POST /api_v3/service/media/action/delete
```

Deletion is soft-delete (status changes to 3 = DELETED). The entry can be recovered from the recycle bin for a limited time.

```bash
curl -X POST "$KALTURA_SERVICE_URL/service/media/action/delete" \
  -d "ks=$KALTURA_KS" \
  -d "format=1" \
  -d "entryId=$KALTURA_ENTRY_ID"
```

## 6.6 media.convert -- Trigger Transcoding

```
POST /api_v3/service/media/action/convert
```

| Parameter | Type | Description |
|-----------|------|-------------|
| `entryId` | string | Entry ID |
| `conversionProfileId` | int | Transcoding profile to use (optional; uses account default) |

Triggers conversion on an existing entry. Useful after changing the transcoding profile or when you need additional renditions.


# 7. Cross-Type Entry Operations (baseEntry)

The `baseEntry` service provides operations that work across all entry types (media, document, data).

## 7.1 baseEntry.getByIds -- Batch Retrieve Multiple Entries

```
POST /api_v3/service/baseEntry/action/getByIds
```

| Parameter | Type | Description |
|-----------|------|-------------|
| `entryIds` | string | Comma-separated entry IDs |

Returns an array of entries in a single request. More efficient than multiple `media.get` calls.

```bash
curl -X POST "$KALTURA_SERVICE_URL/service/baseEntry/action/getByIds" \
  -d "ks=$KALTURA_KS" \
  -d "format=1" \
  -d "entryIds=$ENTRY_ID_1,$ENTRY_ID_2,$ENTRY_ID_3"
```

## 7.2 baseEntry.listByReferenceId -- Find by External Reference

```
POST /api_v3/service/baseEntry/action/listByReferenceId
```

| Parameter | Type | Description |
|-----------|------|-------------|
| `refId` | string | The reference ID to search for |

**Business scenario -- CMS integration:** Your CMS stores Kaltura entry IDs alongside its own content IDs. When syncing, look up entries by your CMS's reference ID to avoid maintaining a separate mapping table.

## 7.3 baseEntry.clone -- Deep Clone an Entry

```
POST /api_v3/service/baseEntry/action/clone
```

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `entryId` | string | Yes | Entry to clone |
| `cloneOptions` | array | No | Array of clone option items controlling which components to include/exclude |

Creates a full deep copy of the entry including all metadata, flavor assets, thumbnails, captions, categories, access control, and custom metadata. The cloned entry gets a new ID with statistics reset to zero.

**Default clone (copies everything):**

```bash
curl -X POST "$KALTURA_SERVICE_URL/service/baseEntry/action/clone" \
  -d "ks=$KALTURA_KS" \
  -d "format=1" \
  -d "entryId=$SOURCE_ENTRY_ID"
```

**Clone with options — exclude specific components:**

Each clone option item has `itemType` (what component) and `rule` (0 = include, 1 = exclude):

```bash
curl -X POST "$KALTURA_SERVICE_URL/service/baseEntry/action/clone" \
  -d "ks=$KALTURA_KS" \
  -d "format=1" \
  -d "entryId=$SOURCE_ENTRY_ID" \
  -d "cloneOptions[0][objectType]=KalturaBaseEntryCloneOptionComponent" \
  -d "cloneOptions[0][itemType]=5" \
  -d "cloneOptions[0][rule]=1" \
  -d "cloneOptions[1][objectType]=KalturaBaseEntryCloneOptionComponent" \
  -d "cloneOptions[1][itemType]=2" \
  -d "cloneOptions[1][rule]=1"
```

This clones the entry while excluding custom metadata (`itemType=5`) and category assignments (`itemType=2`).

**Clone with child entries (multi-stream, parent-child hierarchies):**

```bash
curl -X POST "$KALTURA_SERVICE_URL/service/baseEntry/action/clone" \
  -d "ks=$KALTURA_KS" \
  -d "format=1" \
  -d "entryId=$SOURCE_ENTRY_ID" \
  -d "cloneOptions[0][objectType]=KalturaBaseEntryCloneOptionComponent" \
  -d "cloneOptions[0][itemType]=3" \
  -d "cloneOptions[0][rule]=0"
```

**Clone option item types:**

| itemType | Component | Default Behavior |
|----------|-----------|-----------------|
| `1` | Users (ownership) | Copied — exclude to use current KS user as owner |
| `2` | Categories | Copied — exclude to remove category assignments |
| `3` | Child entries | **NOT copied** — must explicitly include (rule=0) |
| `4` | Access control | Copied — exclude to use account default |
| `5` | Custom metadata | Copied — exclude to remove metadata profiles |
| `6` | Flavors | Copied — exclude to create entry with NO_CONTENT status |
| `7` | Captions | Copied — exclude to remove caption assets |

Plugin-provided clone options (available when cue point plugins are enabled):

| itemType | Component |
|----------|-----------|
| `adCuePoint.AD_CUE_POINTS` | Ad cue points |
| `annotation.ANNOTATION_CUE_POINTS` | Annotation cue points |
| `codeCuePoint.CODE_CUE_POINTS` | Code cue points |
| `thumbCuePoint.THUMB_CUE_POINTS` | Thumbnail cue points |

**Clone vs. KalturaEntryResource:**

| | `baseEntry.clone` | `media.addContent` with `KalturaEntryResource` |
|--|-------------------|------------------------------------------------|
| Result | Full copy with metadata, categories, captions, cue points | New entry with only the source file (content only) |
| Metadata | All fields preserved | Fresh empty entry you define |
| Flavors | All flavors copied instantly | Re-transcodes from source |
| Status | READY immediately (if source is READY) | Goes through ingestion pipeline |
| Control | Include/exclude components granularly | Only select which flavor to copy |

Use `baseEntry.clone` when duplicating a complete entry with all its assets and metadata. Use `KalturaEntryResource` when you need a new entry with independent metadata that shares only the source file.

**Business scenario — multi-tenant distribution:** A corporate training team clones a compliance video to 50 department accounts, each clone inheriting categories and custom metadata but with independent analytics tracking.

## 7.4 baseEntry.recycle / baseEntry.restoreRecycled

```bash
# Move to recycle bin (soft delete with recovery option)
curl -X POST "$KALTURA_SERVICE_URL/service/baseEntry/action/recycle" \
  -d "ks=$KALTURA_KS" \
  -d "format=1" \
  -d "entryId=$KALTURA_ENTRY_ID"

# Restore from recycle bin
curl -X POST "$KALTURA_SERVICE_URL/service/baseEntry/action/restoreRecycled" \
  -d "ks=$KALTURA_KS" \
  -d "format=1" \
  -d "entryId=$KALTURA_ENTRY_ID"
```

## 7.5 baseEntry.export -- Export to Remote Storage

```
POST /api_v3/service/baseEntry/action/export
```

| Parameter | Type | Description |
|-----------|------|-------------|
| `entryId` | string | Entry to export |
| `storageProfileId` | int | Target storage profile ID |

Exports the entry's assets to a configured remote storage profile (e.g., S3, SFTP).


# 8. Non-Media Entry Types

## 8.1 Document Entries (documents service)

Upload documents (PDF, DOCX, PPTX) using the `documents` service. Documents go through Kaltura's document conversion pipeline for web viewing.

| Action | Description |
|--------|-------------|
| `documents.addContent` | Attach content to a NO_CONTENT document entry |
| `documents.updateContent` | Replace document content |
| `documents.convert` | Trigger document conversion |
| `documents.get` | Get document entry |
| `documents.update` | Update document metadata |
| `documents.delete` | Delete document entry |
| `documents.list` | List document entries |
| `documents.serve` | Serve document file directly |
| `documents.serveByFlavorParamsId` | Serve a specific converted rendition |

**Document types (`documentType`):**

| Value | Name | Description |
|-------|------|-------------|
| 11 | DOCUMENT | General document (Word, PowerPoint, etc.) |
| 12 | SWF | Flash document |
| 13 | PDF | PDF document |

```bash
# Create a document entry and attach content
curl -X POST "$KALTURA_SERVICE_URL/service/baseEntry/action/add" \
  -d "ks=$KALTURA_KS" \
  -d "format=1" \
  -d "entry[objectType]=KalturaDocumentEntry" \
  -d "entry[name]=Presentation Slides" \
  -d "entry[documentType]=11" \
  -d "entry[tags]=slides,training"

curl -X POST "$KALTURA_SERVICE_URL/service/documents_documents/action/addContent" \
  -d "ks=$KALTURA_KS" \
  -d "format=1" \
  -d "entryId=$DOC_ENTRY_ID" \
  -d "resource[objectType]=KalturaUploadedFileTokenResource" \
  -d "resource[token]=$UPLOAD_TOKEN_ID"
```

**Business scenario -- slide sync:** A university uploads PPTX presentations that are automatically converted for web viewing and can be synchronized with recorded lectures using the [Chapters & Slides API](KALTURA_CHAPTERS_AND_SLIDES_API.md).

## 8.2 Data Entries (data service)

Upload any file type as a data entry. Data entries are stored and served as-is without transcoding.

| Action | Description |
|--------|-------------|
| `data.add` | Create a data entry (status is immediately READY) |
| `data.addContent` | Set text/XML content on an existing entry |
| `data.get` | Get data entry |
| `data.update` | Update data entry metadata |
| `data.delete` | Delete data entry |
| `data.list` | List data entries |
| `data.serve` | Serve data content as file download |

```bash
curl -X POST "$KALTURA_SERVICE_URL/service/baseEntry/action/add" \
  -d "ks=$KALTURA_KS" \
  -d "format=1" \
  -d "entry[objectType]=KalturaDataEntry" \
  -d "entry[type]=6" \
  -d "entry[name]=Configuration File" \
  -d "entry[tags]=config,json"

curl -X POST "$KALTURA_SERVICE_URL/service/baseEntry/action/addContent" \
  -d "ks=$KALTURA_KS" \
  -d "format=1" \
  -d "entryId=$DATA_ENTRY_ID" \
  -d "resource[objectType]=KalturaUploadedFileTokenResource" \
  -d "resource[token]=$UPLOAD_TOKEN_ID"
```

Set `conversionProfileId=-1` to skip transcoding for data entries.

**Business scenario -- configuration storage:** A video platform stores per-player configuration JSON as data entries, versioned alongside the media they configure.

## 8.3 Choosing the Right Entry Type

| File Type | Service | Entry Object | Transcoded? | Delivered Via |
|-----------|---------|-------------|-------------|--------------|
| Video, audio, image | `media` | `KalturaMediaEntry` | Yes | playManifest (HLS/DASH) |
| PDF, Word, PowerPoint | `documents` | `KalturaDocumentEntry` | Converted for web | documents.serve |
| Any other file | `baseEntry` | `KalturaDataEntry` (type=6) | No | Raw serve URL |
| Supplementary file on a media entry | `attachmentAsset` | `KalturaAttachmentAsset` | No | attachmentAsset.serve |


# 9. Flavor Assets (Transcoded Renditions)

A "flavor" is a transcoded rendition of the source file (e.g., 360p, 720p, 1080p). Kaltura automatically creates flavors based on the account's conversion profile.

## 9.1 flavorAsset.list -- List Flavors for an Entry

```
POST /api_v3/service/flavorAsset/action/list
```

| Parameter | Type | Description |
|-----------|------|-------------|
| `filter[entryIdEqual]` | string | The entry ID |

**Response:** List of `KalturaFlavorAsset` objects with `id`, `flavorParamsId`, `width`, `height`, `bitrate` (kbps), `size` (KB), `status`, `isOriginal`.

```bash
curl -X POST "$KALTURA_SERVICE_URL/service/flavorAsset/action/list" \
  -d "ks=$KALTURA_KS" \
  -d "format=1" \
  -d "filter[entryIdEqual]=$KALTURA_ENTRY_ID"
```

## 9.2 flavorAsset.getFlavorAssetsWithParams

```
POST /api_v3/service/flavorAsset/action/getFlavorAssetsWithParams
```

Returns all flavor assets paired with their flavor params for an entry. Includes params without assets (not yet transcoded) and assets without params (custom uploads).

## 9.3 flavorAsset.add + flavorAsset.setContent -- Upload a Custom Rendition

```bash
# Create a flavor asset on the entry
curl -X POST "$KALTURA_SERVICE_URL/service/flavorAsset/action/add" \
  -d "ks=$KALTURA_KS" \
  -d "format=1" \
  -d "entryId=$KALTURA_ENTRY_ID" \
  -d "flavorAsset[objectType]=KalturaFlavorAsset" \
  -d "flavorAsset[flavorParamsId]=0"

# Upload content to the flavor
curl -X POST "$KALTURA_SERVICE_URL/service/flavorAsset/action/setContent" \
  -d "ks=$KALTURA_KS" \
  -d "format=1" \
  -d "id=$FLAVOR_ASSET_ID" \
  -d "contentResource[objectType]=KalturaUploadedFileTokenResource" \
  -d "contentResource[token]=$UPLOAD_TOKEN_ID"
```

**Business scenario -- pre-transcoded content:** A broadcaster provides pre-transcoded renditions (already encoded at multiple bitrates). Upload each rendition as a separate flavor asset rather than re-transcoding.

## 9.4 flavorAsset.convert / flavorAsset.reconvert

```bash
# Trigger conversion for a specific flavor params
curl -X POST "$KALTURA_SERVICE_URL/service/flavorAsset/action/convert" \
  -d "ks=$KALTURA_KS" \
  -d "format=1" \
  -d "entryId=$KALTURA_ENTRY_ID" \
  -d "flavorParamsId=$FLAVOR_PARAMS_ID"

# Re-convert an existing flavor asset
curl -X POST "$KALTURA_SERVICE_URL/service/flavorAsset/action/reconvert" \
  -d "ks=$KALTURA_KS" \
  -d "format=1" \
  -d "id=$FLAVOR_ASSET_ID"
```

## 9.5 flavorAsset.getUrl -- Get Download URL

```
POST /api_v3/service/flavorAsset/action/getUrl
```

| Parameter | Type | Description |
|-----------|------|-------------|
| `id` | string | Flavor asset ID |
| `storageId` | int | Specific storage profile (optional) |
| `forceProxy` | bool | Route through proxy (optional) |

Returns a direct download URL string for that specific flavor.

## 9.6 flavorAsset.export -- Export to Remote Storage

```bash
curl -X POST "$KALTURA_SERVICE_URL/service/flavorAsset/action/export" \
  -d "ks=$KALTURA_KS" \
  -d "format=1" \
  -d "assetId=$FLAVOR_ASSET_ID" \
  -d "storageProfileId=$STORAGE_PROFILE_ID"
```

## 9.7 flavorAsset.setAsSource

Designates a specific flavor as the "original source" for the entry. Useful when you've uploaded a pre-transcoded rendition and want it treated as the source for further conversions.


# 10. Attachment Assets (Non-Media File Attachments)

The `attachment_attachmentAsset` service attaches supplementary files to media entries (shown as "Related Files" in KMC).

| Action | Description |
|--------|-------------|
| `attachment_attachmentAsset.add` | Create an attachment asset on an entry |
| `attachment_attachmentAsset.setContent` | Upload content to the attachment |
| `attachment_attachmentAsset.update` | Update attachment metadata |
| `attachment_attachmentAsset.get` | Get attachment by ID |
| `attachment_attachmentAsset.list` | List attachments for an entry |
| `attachment_attachmentAsset.delete` | Delete an attachment |
| `attachment_attachmentAsset.getUrl` | Get download URL |
| `attachment_attachmentAsset.serve` | Serve attachment file directly |

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

# Step 2: Upload the file using an upload token
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

# Get direct download URL
curl -X POST "$KALTURA_SERVICE_URL/service/attachment_attachmentAsset/action/getUrl" \
  -d "ks=$KALTURA_KS" \
  -d "format=1" \
  -d "id=$ATTACHMENT_ASSET_ID"
```

**Attachment format types:**

| Value | Name | Description |
|-------|------|-------------|
| 1 | TEXT | Plain text files |
| 2 | MEDIA | Media files not for transcoding (supplementary media) |
| 3 | DOCUMENT | Documents (PDF, DOCX, PPTX, etc.) |
| 4 | JSON | Structured JSON data |

**Business scenario -- supplementary materials:** An e-learning platform attaches PDF handouts, exercise files, and code samples to each video lecture. Learners download these via `attachmentAsset.serve` or `attachmentAsset.getUrl`.


# 11. Bulk Upload

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

**Business scenario -- content migration:** A media company migrating 50,000 videos from another platform generates a CSV with URLs and metadata, then submits it via `bulkUploadAdd`. Kaltura processes imports in parallel, handling the queue automatically.

For bulk operations creating more than 5,000 entries, coordinate with your Kaltura representative.


# 12. Complete Example -- Chunked Upload Workflow

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

# --- Step 5: Poll for READY ---
while true; do
  STATUS=$(curl -s -X POST "$KALTURA_SERVICE_URL/service/media/action/get" \
    -d "ks=$KALTURA_KS" -d "format=1" -d "entryId=$KALTURA_ENTRY_ID" | jq -r '.status')
  echo "Status: $STATUS"
  [ "$STATUS" = "2" ] && echo "READY" && break
  [ "$STATUS" = "-1" ] || [ "$STATUS" = "-2" ] && echo "Failed" && break
  sleep 5
done
```

**Resume after failure:** Call `uploadToken.get` to check `uploadedFileSize`, then resume from that byte offset.


# 13. Error Handling

| Error Code | Meaning | Resolution |
|------------|---------|------------|
| `UPLOAD_TOKEN_NOT_FOUND` | Token ID does not exist or expired | Create a new token |
| `UPLOAD_PASSED_MAX_RESUME_TIME_ALLOWED` | Partial upload expired (7-day limit) | Create a new token and re-upload |
| `MAX_ALLOWED_CHUNK_COUNT_EXCEEDED` | Too many chunks uploaded | Use larger chunk sizes |
| `UPLOAD_TOKEN_CANNOT_MATCH_EXPECTED_SIZE` | Final chunk doesn't match expected total | Retry the final chunk |
| `UPLOAD_TOKEN_FILE_TYPE_RESTRICTED` | File type not allowed | Check account file type restrictions |
| `UPLOADED_FILE_NOT_FOUND_BY_TOKEN` | Upload not yet completed | Complete the upload before calling addContent |
| `ENTRY_ID_NOT_FOUND` | Entry ID does not exist | Verify the entry ID; may have been deleted |
| `INVALID_ENTRY_TYPE` | Operation not supported for this entry type | Use the correct service for the entry type |
| `MAX_FILE_SIZE_EXCEEDED` | File exceeds the partner's upload limit | Use chunked upload or request limit increase |
| Import stuck at status 0 | URL resource points to a redirect or manifest | Use a direct file URL with `KalturaUrlResource`, not a streaming manifest or redirect URL |

**Retry strategy:** For transient errors (HTTP 5xx, timeouts), retry with exponential backoff: 1s, 2s, 4s, with jitter, up to 3 retries. For client errors (`UPLOAD_TOKEN_NOT_FOUND`, `ENTRY_ID_NOT_FOUND`), fix the request before retrying. For async operations (transcoding, URL imports), poll with increasing intervals (5s, 10s, 30s).


# 14. Best Practices

- **Use chunked upload for files > 10 MB.** Chunked upload supports resume on failure via `resumeAt`. Use `autoFinalize=1` with `fileSize` to simplify the protocol.  
- **Use `media.addContent` with `KalturaUrlResource` for remote files.** Provide direct file URLs — redirect URLs (playManifest, HLS) cause import failures. The two-step pattern (`media.add` + `media.addContent`) gives explicit control over entry metadata before triggering ingestion.  
- **Use the correct resource type for each ingestion pattern:** `KalturaUploadedFileTokenResource` for local uploads, `KalturaUrlResource` for URL imports, `KalturaEntryResource` for copying content, `KalturaOperationResource` for clipping, `KalturaAssetsParamsResourceContainers` for multi-flavor ingest.  
- **Use `baseEntry.clone` for entry duplication.** Clone provides a full deep copy (metadata, flavors, captions, cue points) with granular control over what to include. Use `KalturaEntryResource` only when you need a new entry with independent metadata.  
- **Use `KalturaOperationResource` for clips.** Create time-based clips by specifying `offset` (ms) and `duration` (ms). Source must be a READY entry. For multi-clip concatenation, use `KalturaOperationResources` (plural).  
- **Poll for READY status after upload.** Check `media.get` for `status=2` before performing operations that require processed content.  
- **Use `referenceId` for cross-system linking.** Set a reference ID matching your CMS's content ID, then use `baseEntry.listByReferenceId` to look up entries.  
- **Use `updateContent` for version management.** Replace the source file while preserving the entry ID, embed codes, and analytics history.  
- **Use Access Control profiles** to restrict content delivery by IP, domain, geo, or scheduling.  
- **Use AppTokens for upload services.** Scope the AppToken with `edit:*` privilege for upload-only access. See [AppTokens Guide](KALTURA_APPTOKENS_API.md).  
- **Set up Agents Manager or REACH rules** to auto-process uploaded content (captions, translation, summarization) rather than manual post-upload workflows.  
- **10,000 result limit on list/search.** Use `createdAtGreaterThanOrEqual` date-window filters to page through results beyond 10K.  
- **Use multirequest for browser uploads.** Combine `uploadToken.add` + `media.add` + `media.addContent` in a single HTTP request. See [API Getting Started](KALTURA_API_GETTING_STARTED.md).  
- **Content-Type auto-detection.** Kaltura detects MIME types during upload. You do not need to specify Content-Type headers for uploaded files.  


# 15. Related Guides

- **[Video Editing API](KALTURA_VIDEO_EDITING_API.md)** — Trim, clip, concat, overlay, chroma key, caption burn-in, effects  
- **[Content Delivery API](KALTURA_CONTENT_DELIVERY_API.md)** — playManifest streaming URLs, raw serve, download URLs, access control  
- **[Thumbnail & Image API](KALTURA_THUMBNAIL_API.md)** — Dynamic thumbnail generation, thumbAsset management, sprite sheets  
- **[Session Guide](KALTURA_SESSION_GUIDE.md)** — Create and manage KS tokens  
- **[AppTokens Guide](KALTURA_APPTOKENS_API.md)** — Secure token-based auth for upload integrations  
- **[API Getting Started](KALTURA_API_GETTING_STARTED.md)** — Foundation guide covering content model, multirequest, and API patterns  
- **[eSearch Guide](KALTURA_ESEARCH_API.md)** — Search for entries after upload  
- **[Player Embed Guide](KALTURA_PLAYER_EMBED_GUIDE.md)** — Embed uploaded content  
- **[REACH Guide](KALTURA_REACH_API.md)** — Enrichment services for uploaded content (captions, translation, moderation)  
- **[Agents Manager](KALTURA_AGENTS_MANAGER_API.md)** — Auto-process uploaded content (triggers on ENTRY_READY)  
- **[Multi-Stream](KALTURA_MULTI_STREAM_API.md)** — Create synchronized dual/multi-screen entries  
- **[Webhooks API](KALTURA_EVENT_NOTIFICATIONS_WEBHOOK_AND_EMAIL_API.md)** — Get notified when entries finish processing  
- **[Distribution](KALTURA_DISTRIBUTION_API.md)** — Distribute uploaded content to external platforms  
- **[Moderation API](KALTURA_MODERATION_API.md)** — Content moderation workflows  

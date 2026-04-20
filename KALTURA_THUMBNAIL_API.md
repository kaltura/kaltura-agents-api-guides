# Kaltura Thumbnail & Image Transformation API

This guide covers generating and managing thumbnails and images: the URL-based dynamic thumbnail API (31 parameters for on-the-fly resizing, cropping, format conversion, video frame extraction, and sprite sheet generation), the thumbAsset service for stored editorial thumbnails, and the thumbParams service for reusable thumbnail templates.

**CDN Base:** `https://cdnapisec.kaltura.com` (or your account's CDN host)  
**API Base:** `$SERVICE_URL` (default: `https://www.kaltura.com/api_v3`)  
**Auth:** Thumbnail URLs work without KS for public entries. Access-controlled entries require `/ks/{KS}` appended to the URL.  


# 1. When to Use

| Scenario | What to Use |
|----------|-------------|
| **Responsive thumbnails** — Serve different sizes for different screen densities | Dynamic thumbnail URL with `/width/W/height/H` |
| **Video timeline preview** — Hover scrubber showing frames across the video | Sprite strip with `/vid_slices/N` |
| **Specific video frame** — Capture a frame at a known timestamp | `/vid_sec/S` parameter |
| **Gallery grid** — Uniform thumbnails with consistent dimensions | `/type/3` (center crop) with fixed width/height |
| **Letterboxed thumbnails** — Preserve aspect ratio with padding | `/type/2` with `/bgcolor/HEX` |
| **High-quality download** — Full-resolution PNG export | `/width/1920/height/1080/quality/100/format/png` |
| **Custom editorial thumbnails** — Upload marketing images per entry | `thumbAsset.add` + `thumbAsset.setContent` |
| **Default thumbnail management** — Control which thumbnail displays for an entry | `thumbAsset.setAsDefault` |
| **Reusable thumbnail templates** — Define standard thumbnail specs (e.g., "banner 1200x630") | `thumbParams` service |
| **Region-of-interest crop** — Crop a specific area from the source image | `/src_x/X/src_y/Y/src_w/W/src_h/H` |


# 2. Dynamic Thumbnail API (URL-Based)

Generate thumbnails on the fly via URL parameters. Results are CDN-cached (1 hour for ready entries, 30 days in memcache) — use freely for responsive UIs and per-request customization.

**URL pattern:**
```
https://cdnapisec.kaltura.com/p/{PARTNER_ID}/thumbnail/entry_id/{ENTRY_ID}/{param}/{value}/...
```

## 2.1 Dimensions and Resize

| Parameter | Type | Default | Range | Description |
|-----------|------|---------|-------|-------------|
| `/width/{W}` | int | 120 | 0-10000 | Output width in pixels. If omitted with height, auto-calculates preserving aspect ratio. Default 120 when both omitted |
| `/height/{H}` | int | 90 | 0-10000 | Output height in pixels. If omitted with width, auto-calculates preserving aspect ratio. Default 90 when both omitted |
| `/def_width/{W}` | float | -1 | -1 to 10000 | Override the 120px default width when both width and height are omitted |
| `/def_height/{H}` | float | -1 | -1 to 10000 | Override the 90px default height when both width and height are omitted |
| `/type/{T}` | int | 1 | 1-5 | Resize mode (see Resize Modes below) |
| `/density/{D}` | float | 0 | 0+ | Image DPI. 0 = use partner default |

### Resize Modes (`type` parameter)

| Value | Name | Behavior |
|-------|------|----------|
| 1 | RESIZE | Resize maintaining aspect ratio. If only one dimension given, the other scales proportionally |
| 2 | RESIZE_WITH_PADDING | Fit within dimensions, pad remaining space with `bgcolor` |
| 3 | CROP | Center-crop to fill dimensions (may clip edges). Best for uniform grids |
| 4 | CROP_FROM_TOP | Like crop but anchored to top. Best for portraits and posters |
| 5 | RESIZE_WITH_FORCE | Force-resize to exact dimensions, ignoring aspect ratio (may distort) |

**Business scenario — responsive gallery:** A video catalog displays thumbnails at different sizes: 320x180 for mobile grid, 640x360 for desktop hover, 160x90 for search results. Each size is a different URL — the CDN caches each variant independently.

## 2.2 Output Format and Quality

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `/quality/{Q}` | int | 0 | JPEG quality (0-100). 0 = use partner default |
| `/format/{F}` | string | jpg | Output format: `jpg`, `png`, `bmp`, `gif` |
| `/bgcolor/{HEX}` | string | ffffff | Background color for padding (6 hex chars, e.g., `ff0000`) |
| `/strip/{S}` | string | — | Strip ICC color profiles and metadata. Null = use partner default |
| `/nearest_aspect_ratio/{0\|1}` | int | 0 | When 1, selects the thumbAsset with the closest aspect ratio, then crops to fit |

## 2.3 Video Frame Extraction

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `/vid_sec/{S}` | float | -1 | Capture frame at specific second. Capped to entry duration (out-of-range values clamp to last second) |
| `/vid_slice/{N}` | int | -1 | Extract slice N from a sprite strip (0-based, use with `vid_slices`) |
| `/vid_slices/{TOTAL}` | int | -1 | Divide video into TOTAL equal segments. When `vid_slice=-1`, generates a horizontal sprite strip of all slices |
| `/start_sec/{S}` | float | -1 | Start of time range for sprite strips (must be ≤ `end_sec`) |
| `/end_sec/{S}` | float | -1 | End of time range for sprite strips |

**Sprite strip constraint:** `width × vid_slices` and `height × vid_slices` must each be < 65,500 pixels.

**Business scenario — video timeline scrubber:** A player shows frame previews when the user hovers over the progress bar. Generate a single sprite strip image with `/vid_slices/20/width/160/height/90`, then use CSS `background-position` to show the correct frame on hover. One HTTP request serves all 20 preview frames.

## 2.4 Source Crop (Region of Interest)

| Parameter | Type | Default | Range | Description |
|-----------|------|---------|-------|-------------|
| `/src_x/{X}` | float | 0 | 0-10000 | Source crop X offset |
| `/src_y/{Y}` | float | 0 | 0-10000 | Source crop Y offset |
| `/src_w/{W}` | float | 0 | 0-10000 | Source crop width |
| `/src_h/{H}` | float | 0 | 0-10000 | Source crop height |
| `/rel_width/{W}` | float | -1 | -1 to 10000 | Reference width for coordinate normalization |
| `/rel_height/{H}` | float | -1 | -1 to 10000 | Reference height for coordinate normalization |

**Coordinate normalization:** If your crop coordinates are measured against a display size different from the original image (e.g., a 1280x720 preview pane showing a 1920x1080 image), use `rel_width` and `rel_height` to specify the coordinate system. The server automatically scales `src_*` values to match the original image dimensions.

**Business scenario — face-centered crop:** An image editor lets users draw a crop rectangle on a preview canvas. The canvas is 640x360 but the original image is 4000x2250. Send `src_x/120/src_y/80/src_w/400/src_h/200/rel_width/640/rel_height/360` — the server scales the coordinates to the full-resolution image.

## 2.5 Source and Access

| Parameter | Type | Description |
|-----------|------|-------------|
| `/flavor_id/{ID}` | string | Generate thumbnail from a specific flavor (transcoded rendition) |
| `/flavor_params_id/{ID}` | string | Use dimensions from a flavor params definition instead of explicit width/height |
| `/upload_token_id/{ID}` | string | Generate thumbnail from an in-progress upload token (preview before entry creation) |
| `/version/{V}` | int | Specific thumbnail version (0-10M) |
| `/crop_provider/{NAME}` | string | Custom crop provider plugin |
| `/ks/{KS}` | string | Kaltura Session for access-controlled entries |
| `/referrer/{BASE64}` | string | Base64-encoded referrer for domain restrictions |
| `/file_name/{NAME}` | string | Download filename (must be the last parameter in the URL) |

## 2.6 Examples

```bash
# Default thumbnail (120x90)
https://cdnapisec.kaltura.com/p/$PARTNER_ID/thumbnail/entry_id/$ENTRY_ID

# Responsive: 640x360, center-cropped, at 30 seconds
https://cdnapisec.kaltura.com/p/$PARTNER_ID/thumbnail/entry_id/$ENTRY_ID/width/640/height/360/type/3/vid_sec/30

# High-quality PNG for export
https://cdnapisec.kaltura.com/p/$PARTNER_ID/thumbnail/entry_id/$ENTRY_ID/width/1920/height/1080/quality/100/format/png

# CSS sprite strip: 10 slices for hover preview
https://cdnapisec.kaltura.com/p/$PARTNER_ID/thumbnail/entry_id/$ENTRY_ID/width/160/height/90/vid_slices/10

# Padded with white background (letterboxed)
https://cdnapisec.kaltura.com/p/$PARTNER_ID/thumbnail/entry_id/$ENTRY_ID/width/400/height/400/type/2/bgcolor/ffffff

# Sprite strip from specific time range (10s to 60s)
https://cdnapisec.kaltura.com/p/$PARTNER_ID/thumbnail/entry_id/$ENTRY_ID/width/160/height/90/vid_slices/10/start_sec/10/end_sec/60

# Individual slice from a sprite (slice 3 of 10)
https://cdnapisec.kaltura.com/p/$PARTNER_ID/thumbnail/entry_id/$ENTRY_ID/width/160/height/90/vid_slices/10/vid_slice/3

# Region-of-interest crop
https://cdnapisec.kaltura.com/p/$PARTNER_ID/thumbnail/entry_id/$ENTRY_ID/src_x/100/src_y/50/src_w/800/src_h/450/width/400/height/225

# Social media share card (1200x630, padded)
https://cdnapisec.kaltura.com/p/$PARTNER_ID/thumbnail/entry_id/$ENTRY_ID/width/1200/height/630/type/2/bgcolor/000000/quality/90

# Force exact dimensions (stretch)
https://cdnapisec.kaltura.com/p/$PARTNER_ID/thumbnail/entry_id/$ENTRY_ID/width/300/height/300/type/5

# Download as file
https://cdnapisec.kaltura.com/p/$PARTNER_ID/thumbnail/entry_id/$ENTRY_ID/width/1920/height/1080/file_name/thumbnail.jpg

# Access-controlled entry
https://cdnapisec.kaltura.com/p/$PARTNER_ID/thumbnail/entry_id/$ENTRY_ID/width/640/height/360/ks/$KS
```

## 2.7 Behavior Notes

- **KS is optional** for public entries. The endpoint auto-detects the partner from the entry ID.  
- **Image entries** (mediaType=2): The original uploaded image is used as the thumbnail source. `vid_sec`, `vid_slice`, and `vid_slices` are ignored.  
- **Audio entries**: Return a generic audio placeholder unless the partner has configured a custom `audioThumbEntryId`.  
- **Deleted entries**: Return an `ENTRY_DELETED_MODERATED` error.  
- **Caching**: Ready entries are cached for 1 hour (CDN) and 30 days (memcache). Non-ready entries are cached for 60 seconds. Access-controlled entries disable caching.  
- **`vid_sec` capping**: Values beyond the entry duration are clamped to the last second — they don't error.  
- **EXIF orientation**: Images are auto-rotated based on EXIF Orientation tags before crops/resizes.  
- **Animated GIF**: Partners with `supportAnimatedThumbnails` enabled preserve GIF animation in output.  
- **Concurrent generation limit**: The server limits parallel ImageMagick processes. Extremely high-traffic burst requests for uncached thumbnails may get `TOO_MANY_PROCESSES` errors — these are transient and resolve on retry.  


# 3. thumbAsset API (Stored Thumbnails)

The `thumbAsset` service manages persistent, editorial thumbnails attached to entries. Use when you need multiple thumbnails per entry, custom-uploaded images, or saved video frame captures.

## 3.1 Actions

| Action | Description |
|--------|-------------|
| `thumbAsset.add` | Create a thumb asset on an entry (QUEUED status) |
| `thumbAsset.setContent` | Upload image content to a thumb asset |
| `thumbAsset.addFromImage` | Create and upload in one call (file upload) |
| `thumbAsset.generate` | Capture a frame from video with inline params |
| `thumbAsset.generateByEntryId` | Capture using a stored thumbParams definition |
| `thumbAsset.regenerate` | Re-capture using existing params |
| `thumbAsset.setAsDefault` | Set which thumbnail displays for the entry |
| `thumbAsset.get` | Get a thumb asset by ID |
| `thumbAsset.list` | List all thumb assets for an entry |
| `thumbAsset.serve` | Serve the thumbnail image (with optional on-the-fly resize) |
| `thumbAsset.serveByEntryId` | Serve entry's default thumbnail (or by thumbParamsId) |
| `thumbAsset.getUrl` | Get download URL |
| `thumbAsset.update` | Update thumb asset metadata |
| `thumbAsset.delete` | Delete a thumb asset |
| `thumbAsset.export` | Export to remote storage |
| `thumbAsset.getRemotePaths` | Get remote storage paths |

## 3.2 Upload a Custom Thumbnail

```bash
# Step 1: Create the thumb asset
curl -X POST "$SERVICE_URL/service/thumbAsset/action/add" \
  -d "ks=$KS" \
  -d "format=1" \
  -d "entryId=$ENTRY_ID" \
  -d "thumbAsset[objectType]=KalturaThumbAsset" \
  -d "thumbAsset[tags]=custom,marketing"

# Step 2: Upload the image via upload token
curl -X POST "$SERVICE_URL/service/thumbAsset/action/setContent" \
  -d "ks=$KS" \
  -d "format=1" \
  -d "id=$THUMB_ASSET_ID" \
  -d "contentResource[objectType]=KalturaUploadedFileTokenResource" \
  -d "contentResource[token]=$UPLOAD_TOKEN_ID"
```

**Or upload directly with `addFromImage`:**

```bash
curl -X POST "$SERVICE_URL/service/thumbAsset/action/addFromImage" \
  -F "ks=$KS" \
  -F "format=1" \
  -F "entryId=$ENTRY_ID" \
  -F "fileData=@custom_thumb.jpg"
```

**Business scenario — marketing thumbnails:** A content team uploads custom-designed thumbnails for featured videos (e.g., with text overlays, branded frames). These are stored as thumb assets and set as default using `thumbAsset.setAsDefault`.

## 3.3 Capture Frame from Video

```bash
# Capture with inline params
curl -X POST "$SERVICE_URL/service/thumbAsset/action/generate" \
  -d "ks=$KS" \
  -d "format=1" \
  -d "entryId=$ENTRY_ID" \
  -d "thumbParams[objectType]=KalturaThumbParams" \
  -d "thumbParams[videoOffset]=30" \
  -d "thumbParams[width]=1280" \
  -d "thumbParams[height]=720" \
  -d "thumbParams[quality]=90"

# Capture using a stored thumbParams definition
curl -X POST "$SERVICE_URL/service/thumbAsset/action/generateByEntryId" \
  -d "ks=$KS" \
  -d "format=1" \
  -d "entryId=$ENTRY_ID" \
  -d "destThumbParamsId=$THUMB_PARAMS_ID"
```

`generate` and `generateByEntryId` are restricted to VIDEO entries in ERROR_CONVERTING, PRECONVERT, or READY status.

## 3.4 Set Default Thumbnail

```bash
curl -X POST "$SERVICE_URL/service/thumbAsset/action/setAsDefault" \
  -d "ks=$KS" \
  -d "format=1" \
  -d "thumbAssetId=$THUMB_ASSET_ID"
```

Sets this thumb asset as the entry's default thumbnail. Removes the default tag from all other thumb assets.

## 3.5 List Thumbnails for an Entry

```bash
curl -X POST "$SERVICE_URL/service/thumbAsset/action/list" \
  -d "ks=$KS" \
  -d "format=1" \
  -d "filter[entryIdEqual]=$ENTRY_ID"
```

## 3.6 Delete a Thumbnail

```bash
curl -X POST "$SERVICE_URL/service/thumbAsset/action/delete" \
  -d "ks=$KS" \
  -d "format=1" \
  -d "thumbAssetId=$THUMB_ASSET_ID"
```

The default thumb asset cannot be deleted — set a different one as default first.

## 3.7 Serve with On-the-Fly Resize

```bash
# Serve with specific dimensions
curl -X POST "$SERVICE_URL/service/thumbAsset/action/serve" \
  -d "ks=$KS" \
  -d "format=1" \
  -d "thumbAssetId=$THUMB_ASSET_ID" \
  -d "thumbParams[objectType]=KalturaThumbParams" \
  -d "thumbParams[width]=320" \
  -d "thumbParams[height]=180" \
  -d "thumbParams[cropType]=3"
```

## 3.8 Thumb Asset Statuses

| Value | Name | Description |
|-------|------|-------------|
| -1 | ERROR | Generation failed |
| 0 | QUEUED | Created, waiting for content |
| 1 | CAPTURING | Frame capture in progress |
| 2 | READY | Available for serving |
| 3 | DELETED | Soft-deleted |
| 4 | NOT_APPLICABLE | N/A |
| 7 | IMPORTING | Content being imported |
| 9 | EXPORTING | Being exported to remote storage |


# 4. thumbParams API (Thumbnail Templates)

The `thumbParams` service defines reusable thumbnail generation specifications that can be associated with conversion profiles for automatic thumbnail generation on upload.

## 4.1 Actions

| Action | Description |
|--------|-------------|
| `thumbParams.add` | Create a new thumbnail params definition |
| `thumbParams.get` | Get by ID (includes system defaults) |
| `thumbParams.update` | Update params |
| `thumbParams.delete` | Soft-delete |
| `thumbParams.list` | List all params (includes system defaults from partner 0) |
| `thumbParams.getByConversionProfileId` | List params for a specific conversion profile |

## 4.2 KalturaThumbParams Fields

| Field | Type | Range | Description |
|-------|------|-------|-------------|
| `cropType` | int | 1-6 | Resize mode (1-5 same as URL API type, plus 6=CROP_AFTER_RESIZE) |
| `quality` | int | 20-100 | JPEG quality |
| `width` | int | 0-10000 | Target width |
| `height` | int | 0-10000 | Target height |
| `cropX` | int | 0-10000 | Crop region X offset |
| `cropY` | int | 0-10000 | Crop region Y offset |
| `cropWidth` | int | 0-10000 | Crop region width |
| `cropHeight` | int | 0-10000 | Crop region height |
| `videoOffset` | float | ≥ 0 | Seconds into video to capture |
| `videoOffsetInPercentage` | int | 0-100 | Capture at percentage of video duration |
| `scaleWidth` | float | 0-10 | Scale multiplier for width |
| `scaleHeight` | float | 0-10 | Scale multiplier for height |
| `backgroundColor` | string | 1-6 hex | Background/padding color |
| `format` | string | — | Output format: `jpg`, `png`, `bmp` |
| `density` | int | ≥ 0 | Image DPI |
| `stripProfiles` | bool | — | Strip ICC profiles and comments |
| `interval` | int | ≥ 1 | Interval in seconds for periodic thumbnails |
| `sourceParamsId` | int | — | ID of source flavor/thumb params to capture from |

### Additional Resize Mode (thumbParams only)

| Value | Name | Behavior |
|-------|------|----------|
| 6 | CROP_AFTER_RESIZE | Force-resize to dimensions, then crop. `cropX`/`cropY` control gravity: -1=NW/W/SW, 0=N/Center/S, 1=NE/E/SE |

```bash
# Create a "social card" thumbnail template
curl -X POST "$SERVICE_URL/service/thumbParams/action/add" \
  -d "ks=$KS" \
  -d "format=1" \
  -d "thumbParams[objectType]=KalturaThumbParams" \
  -d "thumbParams[name]=Social Card 1200x630" \
  -d "thumbParams[width]=1200" \
  -d "thumbParams[height]=630" \
  -d "thumbParams[cropType]=3" \
  -d "thumbParams[quality]=90" \
  -d "thumbParams[videoOffsetInPercentage]=25"
```

**Business scenario — automatic thumbnail on upload:** Associate a thumbParams definition with a conversion profile. When new videos are uploaded, Kaltura automatically generates thumbnails at the configured dimensions, quality, and video offset — no additional API calls needed.


# 5. When to Use Which

| Need | Use | Why |
|------|-----|-----|
| Display thumbnails in a UI at various sizes | **Dynamic Thumbnail URL** | CDN-cached, no stored assets, infinite size combinations |
| Hover preview / timeline scrubber | **Dynamic Thumbnail URL** with `vid_slices` | Single HTTP request for all preview frames |
| Custom-designed marketing thumbnail | **thumbAsset.add + setContent** | Persistent, editable, independent of video content |
| Capture and save a specific video frame | **thumbAsset.generate** | Stored permanently, can be set as default |
| Auto-generate thumbnails on upload | **thumbParams** + conversion profile | Zero-touch automation |
| Change which thumbnail shows by default | **thumbAsset.setAsDefault** | Controls the entry's `thumbnailUrl` property |
| Extract a frame without storing it | **Dynamic Thumbnail URL** with `vid_sec` | Transient, CDN-cached, no asset created |


# 6. Error Handling

| Error | Meaning | Resolution |
|-------|---------|------------|
| `ENTRY_ID_NOT_FOUND` | Entry does not exist | Verify entry ID |
| `ENTRY_DELETED_MODERATED` | Entry was deleted or rejected | Entry no longer available |
| `THUMB_ASSET_ID_NOT_FOUND` | Thumb asset does not exist | Verify thumb asset ID |
| `THUMB_ASSET_IS_DEFAULT` | Cannot delete the default thumb asset | Set a different thumb as default first |
| `TOO_MANY_PROCESSES` | Server at concurrent ImageMagick process limit | Transient — retry after a brief delay |
| `FILE_DOES_NOT_EXIST_ON_CURRENT_DC` | Source file on a different data center | Request is auto-redirected; retry follows redirect |
| Blank/placeholder image | Entry not yet READY or no source for frame capture | Wait for entry to reach READY status |
| `FEATURE_BLOCK_THUMBNAIL_CAPTURE` | Frame capture blocked by access control | Entry has `LIMIT_THUMBNAIL_CAPTURE` rule |


# 7. Best Practices

- **Use the dynamic thumbnail URL for display.** Don't create stored thumb assets just to show images at different sizes — the URL API handles this with CDN caching.  
- **Use `type=3` (center crop) for uniform grids.** It guarantees exact dimensions while keeping the most important part of the image (center).  
- **Use `type=2` (resize with padding) for mixed aspect ratios.** It preserves the full image within fixed dimensions, padding with `bgcolor`.  
- **Use sprite strips for timeline scrubbers.** A single `/vid_slices/20/width/160/height/90` request creates a 3200×90 sprite. Parse in CSS with `background-position`.  
- **Use `nearest_aspect_ratio=1` for multi-thumbnail entries.** If an entry has both landscape and portrait thumb assets, this parameter automatically selects the one that best matches the requested dimensions.  
- **Set `vid_sec` for consistent thumbnails.** Without it, the server uses the entry's stored default thumbnail. Different entries may have defaults at different timestamps, creating inconsistent galleries.  
- **Use short-lived URLs for access-controlled content.** Thumbnail URLs with `/ks/{KS}` are cached per KS value. Use KS with appropriate expiry to prevent stale access.  
- **Don't exceed sprite pixel limits.** Ensure `width × vid_slices < 65,500` and `height × vid_slices < 65,500`.  
- **Upload custom thumbnails for editorial control.** Automated frame capture rarely picks the perfect frame. Upload designed thumbnails via `thumbAsset.addFromImage` for featured content.  
- **Use thumbParams for automation.** Associate thumbnail templates with conversion profiles so every upload automatically gets correctly-sized thumbnails.  


# 8. Related Guides

- **[Upload & Ingestion API](KALTURA_UPLOAD_AND_INGESTION_API.md)** — Upload content (upload tokens needed for thumbAsset.setContent)  
- **[Content Delivery API](KALTURA_CONTENT_DELIVERY_API.md)** — playManifest streaming URLs, raw serve, download URLs  
- **[Session Guide](KALTURA_SESSION_GUIDE.md)** — KS generation for access-controlled thumbnails  
- **[Player Embed Guide](KALTURA_PLAYER_EMBED_GUIDE.md)** — Player uses thumbnail URLs for poster images and scrubber previews  
- **[eSearch Guide](KALTURA_ESEARCH_API.md)** — Search results include thumbnail URLs  
- **[Chapters & Slides API](KALTURA_CHAPTERS_AND_SLIDES_API.md)** — Slide images use thumb assets  
- **[Cue Points API](KALTURA_CUE_POINTS_API.md)** — Thumbnail cue points for timed slide sync  

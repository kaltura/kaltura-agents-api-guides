# Kaltura Chapters & Slides API

Thumb cue points mark visual positions on the video timeline with optional  
thumbnail images. Chapters segment the video into navigable sections.  
Slides sync presentation images with playback for dual-screen experiences.

**Base URL:** `$KALTURA_SERVICE_URL` (e.g., `https://www.kaltura.com/api_v3`)  
**Auth:** KS via `ks` parameter (admin KS with `disableentitlement` for full access)  
**Format:** `format=1` for JSON responses  
**Service:** `cuepoint_cuepoint` (shared with all cue point types)  
**objectType:** `KalturaThumbCuePoint`  
**Prerequisite:** [Cue Points Hub](KALTURA_CUE_POINTS_API.md) for base cue point concepts and shared CRUD


# 1. When to Use

- **Video navigation** — Segment long-form videos into named chapters so viewers can jump to specific topics from a visual table of contents.  
- **Lecture and presentation indexing** — Sync slide images with recorded lectures or webinars, enabling dual-screen playback where slides update alongside the presenter video.  
- **Recorded meeting navigation** — Add chapter markers to meeting recordings so participants can quickly locate discussion topics and key decisions.  
- **Content discoverability** — Store OCR text from slides in cue point descriptions, making slide content searchable via eSearch across your entire video library.  
- **AI-powered chaptering** — Use REACH or Content Lab to automatically detect topic boundaries and generate chapters from video content.


# 2. Prerequisites

- **KS (Kaltura Session):** Admin KS (type=2) with `disableentitlement` for creating and managing chapters and slides. A USER KS (type=0) is sufficient for listing and reading cue points during playback.  
- **Cue Points plugin:** The `cuePoint` and `thumbCuePoint` server plugins must be enabled on the account (enabled by default on most accounts).  
- **Player plugins:** To render chapters and slides during playback, enable `kalturaCuepoints`, `navigation`, and optionally `dualscreen` in the player configuration.  
- **Session management:** See [Session Guide](KALTURA_SESSION_GUIDE.md) for KS generation and privilege scoping.


# 3. Sub-Types

| subType | Name | Purpose |
|---------|------|---------|
| 1 | SLIDE | Presentation slide markers (synced with dual-screen) |
| 2 | CHAPTER | Chapter markers (segment the timeline) |


# 4. Fields (in addition to base)

| Field | Type | Description |
|-------|------|-------------|
| `title` | string | Chapter/slide title (max 255 chars) |
| `description` | string | Text content (OCR text for slides) |
| `subType` | int | 1=SLIDE, 2=CHAPTER |
| `assetId` | string | Associated `timedThumbAsset` ID (the thumbnail image) |


# 5. Create a Chapter

```bash
curl -X POST "$KALTURA_SERVICE_URL/service/cuepoint_cuepoint/action/add" \
  -d "ks=$KALTURA_KS" \
  -d "format=1" \
  -d "cuePoint[objectType]=KalturaThumbCuePoint" \
  -d "cuePoint[entryId]=1_abc123" \
  -d "cuePoint[startTime]=0" \
  -d "cuePoint[subType]=2" \
  -d "cuePoint[title]=Introduction" \
  -d "cuePoint[description]=Overview of the course structure" \
  -d "cuePoint[tags]=chapter"
```


# 6. Create a Slide Marker

```bash
curl -X POST "$KALTURA_SERVICE_URL/service/cuepoint_cuepoint/action/add" \
  -d "ks=$KALTURA_KS" \
  -d "format=1" \
  -d "cuePoint[objectType]=KalturaThumbCuePoint" \
  -d "cuePoint[entryId]=1_abc123" \
  -d "cuePoint[startTime]=30000" \
  -d "cuePoint[subType]=1" \
  -d "cuePoint[title]=Slide 2: Architecture Diagram" \
  -d "cuePoint[description]=OCR text extracted from the slide goes here"
```

Thumb cue points created without a thumbnail asset get `status=4` (PENDING) instead of `status=1` (READY).


# 7. Attaching Slide Images (timedThumbAsset)

A slide cue point without an image stays in `status=4` (PENDING). To make it READY, attach a `KalturaTimedThumbAsset` with the slide image.

## 7.1 Create the timedThumbAsset

```bash
curl -X POST "$KALTURA_SERVICE_URL/service/thumbAsset/action/add" \
  -d "ks=$KALTURA_KS" \
  -d "format=1" \
  -d "entryId=$KALTURA_ENTRY_ID" \
  -d "thumbAsset[objectType]=KalturaTimedThumbAsset" \
  -d "thumbAsset[cuePointId]=1_slide_cp_id"
```

## 7.2 Upload and Set Content

```bash
# Create upload token
curl -X POST "$KALTURA_SERVICE_URL/service/uploadToken/action/add" \
  -d "ks=$KALTURA_KS" \
  -d "format=1"

# Upload the slide image file
curl -X POST "$KALTURA_SERVICE_URL/service/uploadToken/action/upload" \
  -F "ks=$KALTURA_KS" \
  -F "format=1" \
  -F "uploadTokenId=TOKEN_ID" \
  -F "fileData=@slide.png"

# Attach the uploaded image to the thumb asset
curl -X POST "$KALTURA_SERVICE_URL/service/thumbAsset/action/setContent" \
  -d "ks=$KALTURA_KS" \
  -d "format=1" \
  -d "id=THUMB_ASSET_ID" \
  -d "contentResource[objectType]=KalturaUploadedFileTokenResource" \
  -d "contentResource[token]=TOKEN_ID"
```

After `setContent`, the thumb asset reaches `status=2` (READY) and the linked cue point automatically transitions from `status=4` (PENDING) to `status=1` (READY). The cue point's `assetId` field is populated with the thumb asset ID.

## 7.3 Serve the Slide Image

```bash
curl -X POST "$KALTURA_SERVICE_URL/service/thumbAsset/action/getUrl" \
  -d "ks=$KALTURA_KS" \
  -d "format=1" \
  -d "id=THUMB_ASSET_ID"
```

Returns a CDN URL that serves the slide image directly.

## 7.4 Listing and Deleting

**Listing timedThumbAssets:** Use `thumbAsset.list` with `filter[entryIdEqual]` — both `KalturaThumbAsset` (entry thumbnails) and `KalturaTimedThumbAsset` (slide images) appear in the results.

**Deleting thumb assets:** Use `thumbAsset.delete` with the asset ID to remove a slide image directly.

**Cascade delete:** Deleting a slide cue point automatically cascade-deletes its linked `KalturaTimedThumbAsset`. No separate cleanup needed.


# 8. How Slides Are Created

Slides become cue points through several pathways:

1. **PPT/PDF upload** — Server extracts each slide as a thumbnail image, creates `KalturaThumbCuePoint` (subType=1) with OCR text in `description`, and links a `KalturaTimedThumbAsset` for the image
2. **Live sessions (KME)** — Presenter slide changes push thumb cue points with slide images to the live stream entry in real time via the API; after recording ends, they persist on the VOD entry
3. **REACH Chaptering** — AI analyzes video content and creates `KalturaThumbCuePoint` (subType=2) at detected topic boundaries (serviceFeature=5)
4. **Manual via API** — Create thumb cue points and attach images as shown in section 7
5. **Bulk XML import** — Ingest multiple cue points via `cuePoint.addFromBulk` (see [Cue Points Hub](KALTURA_CUE_POINTS_API.md))


# 9. Filtering by Sub-Type

Filter to get only chapters or only slides:

```bash
# Chapters only
curl -X POST "$KALTURA_SERVICE_URL/service/cuepoint_cuepoint/action/list" \
  -d "ks=$KALTURA_KS" \
  -d "format=1" \
  -d "filter[entryIdEqual]=1_abc123" \
  -d "filter[cuePointTypeEqual]=thumbCuePoint.Thumb" \
  -d "filter[subTypeEqual]=2"

# Slides only
curl -X POST "$KALTURA_SERVICE_URL/service/cuepoint_cuepoint/action/list" \
  -d "ks=$KALTURA_KS" \
  -d "format=1" \
  -d "filter[entryIdEqual]=1_abc123" \
  -d "filter[cuePointTypeEqual]=thumbCuePoint.Thumb" \
  -d "filter[subTypeEqual]=1"
```


# 10. Player Integration

## 10.1 Navigation Plugin

The `navigation` plugin shows a chapters tab with titles and thumbnails in the player side panel:

```javascript
plugins: {
  kalturaCuepoints: {},
  navigation: {
    expandOnFirstPlay: true,
    position: 'right',
    expandMode: 'alongside',
    itemsOrder: { Chapter: 1, Slide: 2, Caption: 3 }
  }
}
```

| Config | Type | Default | Description |
|--------|------|---------|-------------|
| `expandOnFirstPlay` | boolean | false | Auto-open panel on first play |
| `position` | string | `'right'` | Panel position: right, left, top, bottom |
| `expandMode` | string | `'alongside'` | `alongside` (shrinks video) or `over` (overlays) |
| `itemsOrder` | object | {} | Tab ordering and filtering — only listed types are shown |

## 10.2 Dual-Screen Plugin

The `dualscreen` plugin synchronizes slide display with video playback — as playback progresses, the secondary view updates to show the slide active at that time:

```javascript
plugins: {
  dualscreen: {
    layout: 'PIP',
    position: 'bottom-right',
    childSizePercentage: 30
  }
}
```

- **Chapters** (subType=2) render as colored segments on the player seekbar via the `timeline` plugin.
- **Slides** (subType=1) sync with the `dualscreen` plugin. Supports PIP, side-by-side, and single-media layouts.


# 11. REACH / Content Lab Chapter Generation

- **REACH API** — Order a chaptering task (serviceFeature=5) via `entryVendorTask.add`. AI analyzes video content and generates chapter cue points at topic boundaries. See [REACH API](KALTURA_REACH_API.md).
- **Content Lab** — The Content Lab widget provides a UI for AI-generated chapters. See [Content Lab API](KALTURA_CONTENT_LAB_API.md).


# 12. Searching Chapters and Slides

Chapter titles and slide OCR text are indexed in eSearch. Use `KalturaESearchCuePointItem` with `fieldName=text` to search slide descriptions, or `fieldName=name` for chapter/slide titles. See [Cue Points Hub — eSearch Integration](KALTURA_CUE_POINTS_API.md) for query examples.


# 13. Error Handling

| Error | Cause | Fix |
|-------|-------|-----|
| `PROPERTY_VALIDATION_CANNOT_BE_NULL` | List without identifying filter | Include `entryIdEqual`, `entryIdIn`, `idEqual`, or `idIn` |
| `INVALID_CUE_POINT_ID` | Cue point not found or already deleted | Verify ID exists and status is not DELETED |
| Thumb asset `NOT_FOUND` | Accessing cascade-deleted timedThumbAsset | Parent cue point was deleted — asset auto-removed |


# 14. Best Practices

- **Times are in milliseconds.** A cue point at 1 minute 30 seconds = `startTime=90000`.
- **Thumb cue points need assets for READY status.** Without an associated `timedThumbAsset`, thumb cue points remain in PENDING (4) status.
- **Use subType=2 for chapters, subType=1 for slides.** Chapters segment the timeline; slides sync with dual-screen.
- **Store OCR text in `description`.** This makes slide text searchable via eSearch.
- **Cascade delete is automatic.** Deleting a thumb cue point removes its linked timedThumbAsset — no separate cleanup needed.


# 15. Related Guides

- [Cue Points Hub](KALTURA_CUE_POINTS_API.md) — Base cue point concepts, shared CRUD, eSearch integration, bulk operations
- [Player Embed Guide](KALTURA_PLAYER_EMBED_GUIDE.md) — Player v7 setup, navigation and dualscreen plugins
- [REACH API](KALTURA_REACH_API.md) — AI-powered chaptering (serviceFeature=5)
- [Content Lab API](KALTURA_CONTENT_LAB_API.md) — AI chapter generation widget
- [Multi-Stream API](KALTURA_MULTI_STREAM_API.md) — Dual-screen entries with slide/camera sync
- [Upload & Delivery API](KALTURA_UPLOAD_AND_DELIVERY_API.md) — Upload token workflow for slide images

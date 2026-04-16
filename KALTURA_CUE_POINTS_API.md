# Kaltura Cue Points & Interactive Video API

Cue points are temporal metadata markers on video entries — chapters, slides, ads,  
annotations, quizzes, broadcast events, session boundaries, and custom code triggers.  
They drive player experiences (chapter navigation, slide sync, in-video quizzes,  
ad insertion) and are searchable via eSearch.

This hub guide covers the shared cue point architecture, base service, protocols,  
and cross-type features. Each cue point type has a dedicated guide with  
implementation details — see section 3 for links.

**Base URL:** `$KALTURA_SERVICE_URL` (e.g., `https://www.kaltura.com/api_v3`)  
**Auth:** KS via `ks` parameter (admin KS with `disableentitlement` for full access)  
**Format:** `format=1` for JSON responses  
**Times:** All `startTime` and `endTime` values are in **milliseconds**


# 1. Architecture Overview

Cue points are a plugin-based system. Eight server plugins extend a common `KalturaCuePoint` base:

| objectType | cuePointType | Purpose |
|------------|-------------|---------|
| `KalturaThumbCuePoint` | `thumbCuePoint.Thumb` | Chapters and slides (with thumbnail images) |
| `KalturaAnnotation` | `annotation.Annotation` | Text annotations, comments, hotspots |
| `KalturaAdCuePoint` | `adCuePoint.Ad` | Ad insertion (VAST/VPAID) |
| `KalturaCodeCuePoint` | `codeCuePoint.Code` | Custom programmatic triggers |
| `KalturaQuestionCuePoint` | `quiz.QUIZ_QUESTION` | Quiz questions |
| `KalturaAnswerCuePoint` | `quiz.QUIZ_ANSWER` | Quiz viewer answers |
| `KalturaEventCuePoint` | `eventCuePoint.Event` | Live broadcast start/end markers |
| `KalturaSessionCuePoint` | `sessionCuePoint.Session` | Recording session boundaries |

All types share a common set of base fields and are managed through a single service (`cuepoint_cuepoint`), with additional services for quiz management (`quiz_quiz`, `userEntry`).


# 2. Base Cue Point Service

**Service:** `cuepoint_cuepoint`

All cue point types are managed through this single service. The deprecated `annotation_annotation` service exists but has restricted actions — use `cuepoint_cuepoint` for all operations.

## 2.1 Actions

| Action | Description |
|--------|-------------|
| `add` | Create a cue point (pass `objectType` to specify type) |
| `get` | Retrieve by ID |
| `update` | Update fields (must include `cuePoint[objectType]`) |
| `delete` | Soft-delete (sets status to DELETED) |
| `list` | List/filter cue points (requires identifying filter) |
| `count` | Count matching cue points |
| `clone` | Copy a cue point to a different entry |
| `updateStatus` | Change cue point status directly |
| `updateCuePointsTimes` | Update start/end times without full update call |
| `addFromBulk` | Import multiple cue points via XML file upload |

## 2.2 Base Fields (shared by all types)

| Field | Type | Description |
|-------|------|-------------|
| `id` | string | Unique cue point ID (readonly) |
| `entryId` | string | Entry this cue point belongs to (insert-only) |
| `startTime` | int | Position on the timeline in **milliseconds** |
| `tags` | string | Comma-separated tags |
| `partnerData` | string | Free-form partner data (JSON-safe) |
| `systemName` | string | Unique name per entry (for stable references) |
| `forceStop` | int | 1 = pause player at this cue point |
| `status` | int | 1=READY, 2=DELETED, 3=HANDLED, 4=PENDING |
| `cuePointType` | string | Plugin type identifier (readonly) |
| `createdAt` | int | Unix timestamp (readonly) |
| `updatedAt` | int | Unix timestamp (readonly) |
| `copiedFrom` | string | Source cue point ID if cloned (readonly) |

## 2.3 Listing and Filtering

Every `list` and `count` call **requires** at least one identifying filter:

| Filter Field | Description |
|-------------|-------------|
| `entryIdEqual` / `entryIdIn` | Filter by entry (most common) |
| `idEqual` / `idIn` | Filter by cue point ID(s) |
| `cuePointTypeEqual` | Filter by type (e.g., `codeCuePoint.Code`) |
| `tagsLike` / `tagsMultiLikeOr` | Filter by tags |
| `statusEqual` / `statusIn` | Filter by status |
| `startTimeGreaterThanOrEqual` / `startTimeLessThanOrEqual` | Time range filter |

Omitting all identifying filters returns `PROPERTY_VALIDATION_CANNOT_BE_NULL`.

## 2.4 Create Example

```bash
curl -X POST "$KALTURA_SERVICE_URL/service/cuepoint_cuepoint/action/add" \
  -d "ks=$KALTURA_KS" \
  -d "format=1" \
  -d "cuePoint[objectType]=KalturaCodeCuePoint" \
  -d "cuePoint[entryId]=1_abc123" \
  -d "cuePoint[startTime]=5000" \
  -d "cuePoint[code]=marker-1" \
  -d "cuePoint[tags]=chapter"
```

## 2.5 Update (objectType required)

```bash
curl -X POST "$KALTURA_SERVICE_URL/service/cuepoint_cuepoint/action/update" \
  -d "ks=$KALTURA_KS" \
  -d "format=1" \
  -d "id=1_cp_id" \
  -d "cuePoint[objectType]=KalturaCodeCuePoint" \
  -d "cuePoint[code]=updated-marker"
```

## 2.6 Clone

```bash
curl -X POST "$KALTURA_SERVICE_URL/service/cuepoint_cuepoint/action/clone" \
  -d "ks=$KALTURA_KS" \
  -d "format=1" \
  -d "id=1_source_cp" \
  -d "entryId=1_target_entry"
```

Returns a new cue point with `copiedFrom` set to the source ID.

## 2.7 Status Enum

| Value | Name | Meaning |
|-------|------|---------|
| 1 | READY | Active, usable |
| 2 | DELETED | Soft-deleted |
| 3 | HANDLED | Processed/handled |
| 4 | PENDING | Awaiting asset (thumb cue points without images) |


# 3. Cue Point Types

Each type has a dedicated guide with fields, curl examples, and player integration details:

| Type | objectType | Dedicated Guide | Use Cases |
|------|-----------|----------------|-----------|
| Chapters & Slides | `KalturaThumbCuePoint` | [Chapters & Slides API](KALTURA_CHAPTERS_AND_SLIDES_API.md) | Timeline navigation, slide sync, timedThumbAsset images |
| Annotations | `KalturaAnnotation` | [Annotations API](KALTURA_ANNOTATIONS_API.md) | Text annotations, threaded comments, hotspots |
| Ad Cue Points | `KalturaAdCuePoint` | [Ad Cue Points API](KALTURA_AD_CUE_POINTS_API.md) | VAST/VPAID ad insertion, pre/mid/post-roll, overlays |
| Code / Event / Session | `KalturaCodeCuePoint`, `KalturaEventCuePoint`, `KalturaSessionCuePoint` | [Code, Event & Session API](KALTURA_CODE_CUE_POINTS_API.md) | Generic markers, view-change, broadcast events, recording sessions |
| Interactive Video Quiz | `KalturaQuestionCuePoint`, `KalturaAnswerCuePoint` | [Interactive Video Quiz API](KALTURA_QUIZ_API.md) | In-video quizzes with scoring, 8 question types, reports |


# 4. Protocols: REST API vs Live Push

Cue points reach the player through two protocols:

**REST API (VOD and on-demand):** The `kalturaCuepoints` player plugin calls `cuePoint.list` to load all cue points for an entry when playback starts. Updates require a page refresh or API re-query.

**Socket.io push (live streaming):** During live broadcasts, the media server pushes cue point events to connected players in real time via socket.io. This enables:
- Slide changes during live presentations (KME creates thumb cue points as the presenter advances slides)
- Broadcast start/end markers (event cue points auto-created by the media server)
- Real-time annotations and polls pushed during live sessions

The player receives `TIMED_METADATA_ADDED` events as new cue points arrive via either protocol.


# 5. Applications

Cue points are created and consumed across multiple Kaltura applications:

| Application | Creates | Consumes | Protocol |
|-------------|---------|----------|----------|
| **KMC** (management console) | Manual cue point creation via UI | — | REST |
| **Player v7** | — | Renders all types (timeline, overlays, navigation, quiz) | REST + socket.io |
| **KME** (meetings) | Slide cue points during live presentations | — | REST (push to live entry) |
| **Media server** | Event (broadcast start/end) and session cue points automatically | — | Internal |
| **REACH / Content Lab** | AI-generated chapters, quizzes, summaries | — | REST (async task → cue points) |
| **Backend integrations** | Programmatic cue point management via API | — | REST |
| **Bulk import** | `addFromBulk` XML file upload | — | REST |


# 6. eSearch Integration

Cue point content is indexed in Elasticsearch and searchable via `KalturaESearchCuePointItem`.

## 6.1 Searchable Fields

| Field Name | What It Indexes | Search Modes |
|------------|----------------|--------------|
| `id` | Cue point ID | exact |
| `name` | Title (slide/chapter title, code, ad title) | exact, partial, starts_with, exists |
| `text` | Text content (annotation text, OCR from slides) | exact, partial, starts_with, exists |
| `tags` | Tags | exact, partial, starts_with, exists |
| `type` | Cue point type | exact |
| `sub_type` | Sub-type (1=slide, 2=chapter) | exact |
| `question` | Quiz question text | exact, partial, starts_with, exists |
| `answers` | Quiz answer option text | exact, partial, starts_with, exists |
| `hint` | Quiz hint text | exact, partial, starts_with, exists |
| `explanation` | Quiz explanation text | exact, partial, starts_with, exists |
| `start_time` | Start time in milliseconds | range |
| `end_time` | End time in milliseconds | range |

## 6.2 Search Within Slide OCR Text

Find entries containing slides with specific text:

```bash
curl -X POST "$KALTURA_SERVICE_URL/service/elasticsearch_esearch/action/searchEntry" \
  -d "ks=$KALTURA_KS" \
  -d "format=1" \
  -d "searchParams[objectType]=KalturaESearchEntryParams" \
  -d "searchParams[searchOperator][objectType]=KalturaESearchEntryOperator" \
  -d "searchParams[searchOperator][operator]=1" \
  -d "searchParams[searchOperator][searchItems][0][objectType]=KalturaESearchCuePointItem" \
  -d "searchParams[searchOperator][searchItems][0][itemType]=2" \
  -d "searchParams[searchOperator][searchItems][0][fieldName]=text" \
  -d "searchParams[searchOperator][searchItems][0][searchTerm]=machine learning" \
  -d "searchParams[searchOperator][searchItems][0][addHighlight]=1"
```

`itemType`: 1=EXACT_MATCH, 2=PARTIAL, 3=STARTS_WITH, 4=EXISTS, 5=RANGE

## 6.3 Search Quiz Questions

```bash
curl -X POST "$KALTURA_SERVICE_URL/service/elasticsearch_esearch/action/searchEntry" \
  -d "ks=$KALTURA_KS" \
  -d "format=1" \
  -d "searchParams[objectType]=KalturaESearchEntryParams" \
  -d "searchParams[searchOperator][objectType]=KalturaESearchEntryOperator" \
  -d "searchParams[searchOperator][operator]=1" \
  -d "searchParams[searchOperator][searchItems][0][objectType]=KalturaESearchCuePointItem" \
  -d "searchParams[searchOperator][searchItems][0][itemType]=2" \
  -d "searchParams[searchOperator][searchItems][0][fieldName]=question" \
  -d "searchParams[searchOperator][searchItems][0][searchTerm]=design pattern"
```

## 6.4 Unified Search

`KalturaESearchUnifiedItem` automatically searches across all entry data including cue point content:

```bash
curl -X POST "$KALTURA_SERVICE_URL/service/elasticsearch_esearch/action/searchEntry" \
  -d "ks=$KALTURA_KS" \
  -d "format=1" \
  -d "searchParams[objectType]=KalturaESearchEntryParams" \
  -d "searchParams[searchOperator][objectType]=KalturaESearchEntryOperator" \
  -d "searchParams[searchOperator][operator]=1" \
  -d "searchParams[searchOperator][searchItems][0][objectType]=KalturaESearchUnifiedItem" \
  -d "searchParams[searchOperator][searchItems][0][itemType]=2" \
  -d "searchParams[searchOperator][searchItems][0][searchTerm]=dependency injection"
```


# 7. Player Plugin Ecosystem

Five Player v7 plugins form the cue point rendering ecosystem:

```
KalturaPlayer.setup({ plugins: { ... } })
  │
  ├── kalturaCuepoints    ← Core: loads data, dispatches TimedMetadata events
  │     ├── VOD: API requests (cuePoint.list)
  │     └── Live: socket.io push notifications
  │
  ├── timeline            ← Seekbar markers, chapter segments
  ├── navigation          ← Side panel (chapters, slides, captions, quiz, search)
  ├── ivq                 ← Quiz overlay, seek prevention, scoring
  └── dualscreen          ← Slide sync, PIP/side-by-side layouts
```

## 7.1 Core Plugin: kalturaCuepoints

The foundation plugin that loads cue point data and feeds it to consumer plugins:

```javascript
plugins: {
  kalturaCuepoints: {}
}
```

Consumer plugins register the types they need via `player.getService('kalturaCuepoints').registerTypes([...])`. Only registered types are fetched from the API.

**Cue point types in the player:**

| Type | Value | Source |
|------|-------|--------|
| SLIDE | `'slide'` | ThumbCuePoint (subType=1) |
| CHAPTER | `'chapter'` | ThumbCuePoint (subType=2) |
| HOTSPOT | `'hotspot'` | Annotation (tag=hotspots) |
| QUIZ | `'quiz'` | QuestionCuePoint |
| VIEW_CHANGE | `'viewchange'` | CodeCuePoint (tag=change-view-mode) |
| CAPTION | `'caption'` | Caption segments |

**Events dispatched:**
- `TIMED_METADATA_ADDED` — fired when cue points are loaded
- `TIMED_METADATA_CHANGE` — fired on each time update with active/inactive cue points

## 7.2 Full Setup Example

```javascript
var player = KalturaPlayer.setup({
  targetId: 'player-container',
  plugins: {
    kalturaCuepoints: {},
    timeline: {},
    navigation: {
      expandOnFirstPlay: true,
      position: 'right',
      itemsOrder: { Chapter: 1, Slide: 2, Caption: 3 }
    },
    ivq: {},
    dualscreen: {
      layout: 'PIP',
      position: 'bottom-right',
      childSizePercentage: 30
    }
  }
});
player.loadMedia({ entryId: '1_abc123' });
```

For plugin-specific configuration details, see the dedicated type guides:
- Navigation and dualscreen → [Chapters & Slides](KALTURA_CHAPTERS_AND_SLIDES_API.md)
- IVQ → [Interactive Video Quiz](KALTURA_QUIZ_API.md)
- Dualscreen view-change → [Code Cue Points](KALTURA_CODE_CUE_POINTS_API.md)


# 8. Bulk Operations

## 8.1 XML Import

Upload multiple cue points via `cuePoint.addFromBulk` with an XML file:

```xml
<?xml version="1.0" encoding="UTF-8"?>
<scenes>
  <scene-thumb-cue-point entryId="1_abc123">
    <sceneStartTime>00:00:05.000</sceneStartTime>
    <tags><tag>chapter</tag></tags>
    <title>Introduction</title>
    <description>Opening section</description>
    <subType>2</subType>
  </scene-thumb-cue-point>

  <scene-annotation entryId="1_abc123">
    <sceneStartTime>00:01:30.000</sceneStartTime>
    <sceneEndTime>00:02:00.000</sceneEndTime>
    <sceneText>Key concept explained here</sceneText>
    <tags><tag>important</tag></tags>
  </scene-annotation>

  <scene-code-cue-point entryId="1_abc123">
    <sceneStartTime>00:05:00.000</sceneStartTime>
    <code>section-break</code>
    <description>Topic transition</description>
  </scene-code-cue-point>

  <scene-ad-cue-point entryId="1_abc123">
    <sceneStartTime>00:03:00.000</sceneStartTime>
    <sourceUrl>https://example.com/vast.xml</sourceUrl>
    <adType>1</adType>
    <protocolType>2</protocolType>
  </scene-ad-cue-point>
</scenes>
```

XML element names: `scene-thumb-cue-point`, `scene-annotation`, `scene-code-cue-point`, `scene-ad-cue-point`, `scene-session-cue-point`, `scene-question-cue-point`, `scene-answer-cue-point`

## 8.2 Clone Support

| Type | Clonable | Clone Option Constant |
|------|----------|-----------------------|
| Ad | Yes | `AD_CUE_POINTS` |
| Annotation | Yes | `ANNOTATION_CUE_POINTS` |
| Code | Yes | `CODE_CUE_POINTS` |
| Session | Yes | `SESSION_CUE_POINTS` |
| Thumb | Yes | `THUMB_CUE_POINTS` |
| Event | No | — |
| Quiz (Question/Answer) | No | — |

## 8.3 Custom Metadata

Ad, Annotation, Code, Thumb, and Quiz cue points support custom metadata profiles (XSD schemas attached to cue points via the Metadata API). This enables structured data on individual cue points beyond the built-in fields.


# 9. Error Handling

| Error | Cause | Fix |
|-------|-------|-----|
| `PROPERTY_VALIDATION_CANNOT_BE_NULL` | List/count without identifying filter | Include `entryIdEqual`, `entryIdIn`, `idEqual`, or `idIn` |
| `INVALID_CUE_POINT_ID` | Cue point not found or already deleted | Verify ID exists and status is not DELETED |
| `CUE_POINT_SYSTEM_NAME_EXISTS` | Duplicate `systemName` on the same entry | System names must be unique per entry |
| `NO_PERMISSION_ON_ENTRY` | KS `limitEntry` privilege mismatch | Ensure KS has access to the target entry |


# 10. Best Practices

- **Times are in milliseconds.** A cue point at 1 minute 30 seconds = `startTime=90000`.
- **Use `cuepoint_cuepoint` service** for all operations. The `annotation_annotation` service is deprecated and has restricted actions.
- **Include `objectType` on updates.** The API needs it to determine which fields to apply.
- **Register cleanup before assertions** in tests. Cue points persist on entries — always clean up test cue points.
- **eSearch indexing has a delay.** Newly created cue points may take seconds to appear in search results. Use `cuePoint.list` for immediate retrieval.
- **Filter is mandatory.** Every `list`/`count` call must include at least one identifying filter field.
- **Use `forceStop=1`** to pause the player at a cue point (works for all types, not just quizzes).


# 11. Related Guides

**Dedicated type guides:**
- [Interactive Video Quiz API](KALTURA_QUIZ_API.md) — Quiz lifecycle, 8 question types, scoring, reports, IVQ plugin
- [Chapters & Slides API](KALTURA_CHAPTERS_AND_SLIDES_API.md) — Chapter/slide cue points, timedThumbAsset workflow, navigation plugin
- [Annotations API](KALTURA_ANNOTATIONS_API.md) — Text annotations, threading, hotspots
- [Ad Cue Points API](KALTURA_AD_CUE_POINTS_API.md) — VAST/VPAID ad insertion, placement, protocol immutability
- [Code, Event & Session API](KALTURA_CODE_CUE_POINTS_API.md) — Generic markers, view-change, broadcast events, recording sessions

**Cross-references:**
- [eSearch API](KALTURA_ESEARCH_API.md) — Full search syntax, `KalturaESearchCuePointItem` details
- [Player Embed Guide](KALTURA_PLAYER_EMBED_GUIDE.md) — Player v7 setup, plugin configuration
- [REACH API](KALTURA_REACH_API.md) — AI-powered chaptering (serviceFeature=5), quiz generation (serviceFeature=12)
- [Content Lab API](KALTURA_CONTENT_LAB_API.md) — AI-generated chapters and quizzes
- [Captions & Transcripts](KALTURA_CAPTIONS_AND_TRANSCRIPTS_API.md) — Caption assets (related but separate from cue points)
- [Multi-Stream API](KALTURA_MULTI_STREAM_API.md) — Dual-screen entries with slide/camera sync
- [Custom Metadata API](KALTURA_CUSTOM_METADATA_API.md) — Attaching structured metadata to cue points
- [Upload & Delivery API](KALTURA_UPLOAD_AND_DELIVERY_API.md) — Thumbnail assets for slide images
- [Analytics Reports API](KALTURA_ANALYTICS_REPORTS_API.md) — Quiz reports and engagement analytics
- [Gamification API](KALTURA_GAMIFICATION_API.md) — Quiz scores as gamification inputs

# Kaltura Cue Points & Interactive Video API

Cue points are temporal markers on video entries — chapters, slides, ads, annotations,
quizzes, broadcast events, session boundaries, and custom code triggers.
They drive player experiences (chapter navigation, slide sync, in-video quizzes,
ad insertion) and are searchable via eSearch.

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

**Player integration:** The Player v7 `kalturaCuepoints` plugin loads cue point data from the API (VOD) or via socket.io push (live). Consumer plugins — `timeline`, `navigation`, `ivq`, `dualscreen` — register the cue point types they need and render them.


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
| `updateStatus` | Change status directly |
| `updateCuePointsTimes` | Update start/end times |
| `addFromBulk` | Bulk import from XML file |

## 2.2 Base Fields (all types inherit)

| Field | Type | Access | Description |
|-------|------|--------|-------------|
| `id` | string | readonly | Unique cue point ID |
| `intId` | int | readonly | Integer ID |
| `cuePointType` | string | readonly | Type identifier (see table above) |
| `status` | int | readonly | 1=READY, 2=DELETED, 3=HANDLED, 4=PENDING |
| `entryId` | string | insert-only | Associated video entry |
| `partnerId` | int | readonly | Partner ID |
| `createdAt` | timestamp | readonly | Creation time |
| `updatedAt` | timestamp | readonly | Last update time |
| `triggeredAt` | timestamp | read/write | Trigger time (live cue points) |
| `tags` | string | read/write | Comma-separated tags (searchable) |
| `startTime` | int | read/write | Start time in **milliseconds** |
| `userId` | string | restricted | Owner user ID |
| `partnerData` | string | read/write | Custom partner data (arbitrary string) |
| `partnerSortValue` | int | read/write | Custom sort value |
| `forceStop` | int | read/write | Force player stop (-1=null, 0=false, 1=true) |
| `thumbOffset` | int | read/write | Thumbnail offset |
| `systemName` | string | read/write | System identifier (unique per entry) |
| `isMomentary` | boolean | readonly | Whether cue point is instantaneous |
| `copiedFrom` | string | readonly | Source cue point ID if cloned |

## 2.3 Listing and Filtering

**Mandatory filter constraint:** Every `list` or `count` call must include at least one of: `filter[idEqual]`, `filter[idIn]`, `filter[entryIdEqual]`, or `filter[entryIdIn]`. Omitting all four returns `PROPERTY_VALIDATION_CANNOT_BE_NULL`.

```bash
# List all cue points on an entry
curl -X POST "$KALTURA_SERVICE_URL/service/cuepoint_cuepoint/action/list" \
  -d "ks=$KALTURA_KS" \
  -d "format=1" \
  -d "filter[entryIdEqual]=1_abc123"

# Filter by type
curl -X POST "$KALTURA_SERVICE_URL/service/cuepoint_cuepoint/action/list" \
  -d "ks=$KALTURA_KS" \
  -d "format=1" \
  -d "filter[entryIdEqual]=1_abc123" \
  -d "filter[cuePointTypeEqual]=thumbCuePoint.Thumb"

# Filter by status
curl -X POST "$KALTURA_SERVICE_URL/service/cuepoint_cuepoint/action/list" \
  -d "ks=$KALTURA_KS" \
  -d "format=1" \
  -d "filter[entryIdEqual]=1_abc123" \
  -d "filter[statusEqual]=1"
```

**Filter fields:** `cuePointTypeEqual`, `cuePointTypeIn`, `statusEqual`, `statusIn`, `startTimeGreaterThanOrEqual`, `startTimeLessThanOrEqual`, `tagsLike`, `tagsMultiLikeOr`, `freeText`, `userIdEqualCurrent`

## 2.4 Create a Cue Point

The `objectType` field determines which cue point type is created:

```bash
# Create a code cue point
curl -X POST "$KALTURA_SERVICE_URL/service/cuepoint_cuepoint/action/add" \
  -d "ks=$KALTURA_KS" \
  -d "format=1" \
  -d "cuePoint[objectType]=KalturaCodeCuePoint" \
  -d "cuePoint[entryId]=1_abc123" \
  -d "cuePoint[startTime]=15000" \
  -d "cuePoint[code]=chapter-break" \
  -d "cuePoint[description]=Introduction ends here" \
  -d "cuePoint[tags]=navigation"
```

## 2.5 Update

Updates must include the `objectType` field:

```bash
curl -X POST "$KALTURA_SERVICE_URL/service/cuepoint_cuepoint/action/update" \
  -d "ks=$KALTURA_KS" \
  -d "format=1" \
  -d "id=1_cp_abc" \
  -d "cuePoint[objectType]=KalturaCodeCuePoint" \
  -d "cuePoint[startTime]=20000"
```

## 2.6 Clone

Copy a cue point to a different entry. The cloned cue point gets a new ID and `copiedFrom` references the source:

```bash
curl -X POST "$KALTURA_SERVICE_URL/service/cuepoint_cuepoint/action/clone" \
  -d "ks=$KALTURA_KS" \
  -d "format=1" \
  -d "id=1_cp_abc" \
  -d "entryId=1_target_entry"
```

Clonable types: Ad, Annotation, Code, Session, Thumb. Event and Quiz cue points are not clonable.

## 2.7 Status Enum

| Value | Name | Description |
|-------|------|-------------|
| 1 | READY | Active, usable |
| 2 | DELETED | Soft-deleted |
| 3 | HANDLED | Processed/handled |
| 4 | PENDING | Awaiting asset (thumb cue points without images) |


# 3. Thumb Cue Points — Chapters & Slides

Thumb cue points mark visual positions on the timeline with optional thumbnail images. Two sub-types:

| subType | Name | Purpose |
|---------|------|---------|
| 1 | SLIDE | Presentation slide markers (synced with dual-screen) |
| 2 | CHAPTER | Chapter markers (segment the timeline) |

## 3.1 Fields (in addition to base)

| Field | Type | Description |
|-------|------|-------------|
| `title` | string | Chapter/slide title (max 255 chars) |
| `description` | string | Text content (OCR text for slides) |
| `subType` | int | 1=SLIDE, 2=CHAPTER |
| `assetId` | string | Associated `timedThumbAsset` ID (the thumbnail image) |

## 3.2 Create a Chapter

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

## 3.3 Create a Slide Marker

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

## 3.4 Attaching Slide Images (timedThumbAsset)

A slide cue point without an image stays in `status=4` (PENDING). To make it READY, attach a `KalturaTimedThumbAsset` with the slide image:

**Step 1 — Create the timedThumbAsset linked to the cue point:**

```bash
curl -X POST "$KALTURA_SERVICE_URL/service/thumbAsset/action/add" \
  -d "ks=$KALTURA_KS" \
  -d "format=1" \
  -d "entryId=$KALTURA_ENTRY_ID" \
  -d "thumbAsset[objectType]=KalturaTimedThumbAsset" \
  -d "thumbAsset[cuePointId]=1_slide_cp_id"
```

**Step 2 — Upload the image via uploadToken and set content:**

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

**Step 3 — Serve the slide image:**

```bash
curl -X POST "$KALTURA_SERVICE_URL/service/thumbAsset/action/getUrl" \
  -d "ks=$KALTURA_KS" \
  -d "format=1" \
  -d "id=THUMB_ASSET_ID"
```

Returns a CDN URL that serves the slide image directly.

**Listing timedThumbAssets:** Use `thumbAsset.list` with `filter[entryIdEqual]` — both `KalturaThumbAsset` (entry thumbnails) and `KalturaTimedThumbAsset` (slide images) appear in the results.

**Cascade delete:** Deleting a slide cue point automatically deletes its linked `KalturaTimedThumbAsset`.

## 3.5 How Slides Are Created

Slides become cue points through several pathways:

1. **PPT/PDF upload** — Server extracts each slide as a thumbnail image, creates `KalturaThumbCuePoint` (subType=1) with OCR text in `description`, and links a `KalturaTimedThumbAsset` for the image
2. **Live sessions (KME)** — Presenter slide changes push thumb cue points with slide images to the live stream entry in real time via the API; after recording ends, they persist on the VOD entry
3. **REACH Chaptering** — AI analyzes video content and creates `KalturaThumbCuePoint` (subType=2) at detected topic boundaries (serviceFeature=5)
4. **Manual via API** — Create thumb cue points and attach images as shown in section 3.4
5. **Bulk XML import** — Ingest multiple cue points via `cuePoint.addFromBulk`

## 3.6 Player Rendering

- **Chapters** (subType=2) render as colored segments on the player seekbar via the `timeline` plugin. The `navigation` plugin shows a chapters tab with titles and thumbnails.
- **Slides** (subType=1) sync with the `dualscreen` plugin — as playback progresses, the secondary view updates to show the slide active at that time. Supports PIP, side-by-side, and single-media layouts.


# 4. Annotation Cue Points

Annotations are text-based cue points that support hierarchical threading (parent-child relationships). They are also used for **hotspots** (interactive video overlays) via the `hotspots` tag.

## 4.1 Fields (in addition to base)

| Field | Type | Description |
|-------|------|-------------|
| `text` | string | Annotation text content |
| `parentId` | string | Parent annotation ID (insert-only; 0 = no parent) |
| `endTime` | int | End time in milliseconds |
| `duration` | int | Computed from startTime to endTime (readonly) |
| `depth` | int | Nesting depth in annotation tree (readonly) |
| `childrenCount` | int | Total descendants (readonly) |
| `directChildrenCount` | int | First-level children (readonly) |
| `isPublic` | int | Public visibility (-1=null, 0=false, 1=true) |
| `searchableOnEntry` | int | Index on entry search (-1=null, 0=false, 1=true) |

## 4.2 Create an Annotation

```bash
curl -X POST "$KALTURA_SERVICE_URL/service/cuepoint_cuepoint/action/add" \
  -d "ks=$KALTURA_KS" \
  -d "format=1" \
  -d "cuePoint[objectType]=KalturaAnnotation" \
  -d "cuePoint[entryId]=1_abc123" \
  -d "cuePoint[startTime]=45000" \
  -d "cuePoint[endTime]=60000" \
  -d "cuePoint[text]=Key concept: dependency injection" \
  -d "cuePoint[isPublic]=1" \
  -d "cuePoint[searchableOnEntry]=1"
```

## 4.3 Threaded Annotations

Create child annotations by setting `parentId`:

```bash
curl -X POST "$KALTURA_SERVICE_URL/service/cuepoint_cuepoint/action/add" \
  -d "ks=$KALTURA_KS" \
  -d "format=1" \
  -d "cuePoint[objectType]=KalturaAnnotation" \
  -d "cuePoint[entryId]=1_abc123" \
  -d "cuePoint[parentId]=1_parent_cp" \
  -d "cuePoint[startTime]=45000" \
  -d "cuePoint[text]=Reply: great explanation of DI patterns"
```

The parent must exist on the same entry. The `depth`, `childrenCount`, and `directChildrenCount` fields update automatically.

## 4.4 Hotspots

Interactive video hotspots are annotation cue points with the `hotspots` tag. Creating hotspot-tagged annotations requires edit entitlement on the entry:

```bash
curl -X POST "$KALTURA_SERVICE_URL/service/cuepoint_cuepoint/action/add" \
  -d "ks=$KALTURA_KS" \
  -d "format=1" \
  -d "cuePoint[objectType]=KalturaAnnotation" \
  -d "cuePoint[entryId]=1_abc123" \
  -d "cuePoint[startTime]=10000" \
  -d "cuePoint[endTime]=20000" \
  -d "cuePoint[text]=Click here for details" \
  -d "cuePoint[tags]=hotspots"
```

The Player v7 `navigation` plugin renders hotspots as timeline markers and displays them in the side panel. Hotspot behavior (jump, pause, URL) is stored in `partnerData` as structured data.

## 4.5 Annotation Service Note

The legacy `annotation_annotation` service exists but several actions are restricted (`count`, `updateStatus`, `updateCuePointsTimes`, `clone` return SERVICE_FORBIDDEN). Use the `cuepoint_cuepoint` service for all annotation operations.

**Index delay:** Newly created annotations may take a few seconds to appear in `entryIdEqual` list queries due to search indexing. Retrieval by `idEqual` or `idIn` is immediate.


# 5. Ad Cue Points

Ad cue points define when and how advertisements play during video content.

## 5.1 Fields (in addition to base)

| Field | Type | Description |
|-------|------|-------------|
| `protocolType` | int | Ad protocol (insert-only, **immutable** after creation) |
| `sourceUrl` | string | URL to VAST/VPAID XML feed |
| `adType` | int | 1=VIDEO (linear), 2=OVERLAY (non-linear) |
| `title` | string | Ad title (max 250 chars) |
| `endTime` | int | End time in milliseconds |
| `duration` | int | Duration in milliseconds |

## 5.2 Protocol Types

| Value | Name | Description |
|-------|------|-------------|
| 0 | CUSTOM | Custom ad protocol |
| 1 | VAST | VAST 1.0 |
| 2 | VAST_2_0 | VAST 2.0 |
| 3 | VPAID | VPAID |

## 5.3 Ad Placement

| Placement | startTime | Description |
|-----------|-----------|-------------|
| Pre-roll | `0` | Plays before video content |
| Mid-roll | `N` (in ms) | Plays at position N in the video |
| Post-roll | `duration` | Plays after video content |
| Overlay | any | Non-linear overlay with `adType=2` and `startTime`/`endTime` defining the visible window |

## 5.4 Create a Mid-Roll Ad

```bash
curl -X POST "$KALTURA_SERVICE_URL/service/cuepoint_cuepoint/action/add" \
  -d "ks=$KALTURA_KS" \
  -d "format=1" \
  -d "cuePoint[objectType]=KalturaAdCuePoint" \
  -d "cuePoint[entryId]=1_abc123" \
  -d "cuePoint[startTime]=120000" \
  -d "cuePoint[protocolType]=2" \
  -d "cuePoint[sourceUrl]=https://example.com/vast/midroll.xml" \
  -d "cuePoint[adType]=1" \
  -d "cuePoint[title]=Sponsor message"
```

`protocolType` cannot be changed after creation (returns `PROPERTY_VALIDATION_NOT_UPDATABLE`).


# 6. Code Cue Points

Generic developer-defined markers that trigger player events at specific times. Used for custom interactions, view-change commands (dual-screen layout switching), and programmatic triggers.

## 6.1 Fields (in addition to base)

| Field | Type | Description |
|-------|------|-------------|
| `code` | string | Identifier code (**required**) |
| `description` | string | Free text description |
| `endTime` | int | End time in milliseconds |
| `duration` | int | Computed duration (readonly) |

## 6.2 Create a Code Cue Point

```bash
curl -X POST "$KALTURA_SERVICE_URL/service/cuepoint_cuepoint/action/add" \
  -d "ks=$KALTURA_KS" \
  -d "format=1" \
  -d "cuePoint[objectType]=KalturaCodeCuePoint" \
  -d "cuePoint[entryId]=1_abc123" \
  -d "cuePoint[startTime]=60000" \
  -d "cuePoint[code]=show-overlay" \
  -d "cuePoint[description]=Display product details overlay"
```

## 6.3 View-Change Commands

The `dualscreen` player plugin uses code cue points tagged `change-view-mode` to control layout:

| code Value | Layout |
|------------|--------|
| `locked` | Hidden (dual-screen disabled) |
| `parent-only` | Primary video only |
| `no-parent` | Secondary only (slides/camera) |
| `pip-parent-in-large` | PIP with primary large |
| `pip-parent-in-small` | PIP with secondary large |
| `sbs-parent-in-left` | Side-by-side, primary left |
| `sbs-parent-in-right` | Side-by-side, primary right |


# 7. Event Cue Points

Markers for live broadcast lifecycle events. Enabled for all partners (no plugin activation needed).

## 7.1 Fields (in addition to base)

| Field | Type | Description |
|-------|------|-------------|
| `eventType` | int | 1=BROADCAST_START, 2=BROADCAST_END |

## 7.2 Usage

Event cue points are primarily created by the Kaltura media server during live broadcasts — the server automatically inserts BROADCAST_START and BROADCAST_END markers as the stream goes live and stops. The `eventType` field requires server-level permissions to set.

You can list event cue points on a live entry to detect broadcast boundaries:

```bash
curl -X POST "$KALTURA_SERVICE_URL/service/cuepoint_cuepoint/action/list" \
  -d "ks=$KALTURA_KS" \
  -d "format=1" \
  -d "filter[entryIdEqual]=1_live_entry" \
  -d "filter[cuePointTypeEqual]=eventCuePoint.Event"
```

Event cue points are not clonable and do not support bulk XML import.


# 8. Session Cue Points

Mark session boundaries within recordings — breakout rooms, meeting segments, speaker transitions.

## 8.1 Fields (in addition to base)

| Field | Type | Description |
|-------|------|-------------|
| `name` | string | Session name/title |
| `endTime` | int | End time in milliseconds |
| `duration` | int | Computed duration (readonly) |
| `sessionOwner` | string | Owner of the session |

## 8.2 Example

```bash
curl -X POST "$KALTURA_SERVICE_URL/service/cuepoint_cuepoint/action/add" \
  -d "ks=$KALTURA_KS" \
  -d "format=1" \
  -d "cuePoint[objectType]=KalturaSessionCuePoint" \
  -d "cuePoint[entryId]=1_abc123" \
  -d "cuePoint[startTime]=0" \
  -d "cuePoint[endTime]=900000" \
  -d "cuePoint[name]=Opening Keynote" \
  -d "cuePoint[sessionOwner]=speaker@example.com"
```


# 9. Interactive Video Quiz

The quiz system uses cue points for questions and answers, with a configuration layer on the entry and a user-entry service for tracking attempts and scores.

## 9.1 Quiz Lifecycle

```
quiz.add (mark entry as quiz)
    → cuePoint.add (add KalturaQuestionCuePoint for each question)
        → userEntry.add (viewer starts attempt → KalturaQuizUserEntry)
            → cuePoint.add (viewer answers → KalturaAnswerCuePoint per question)
                → userEntry.submitQuiz (calculate score)
```

## 9.2 Mark an Entry as a Quiz

**Service:** `quiz_quiz`

```bash
curl -X POST "$KALTURA_SERVICE_URL/service/quiz_quiz/action/add" \
  -d "ks=$KALTURA_KS" \
  -d "format=1" \
  -d "entryId=1_abc123" \
  -d "quiz[objectType]=KalturaQuiz" \
  -d "quiz[showResultOnAnswer]=1" \
  -d "quiz[showCorrectAfterSubmission]=1" \
  -d "quiz[allowAnswerUpdate]=1" \
  -d "quiz[showGradeAfterSubmission]=1" \
  -d "quiz[attemptsAllowed]=3" \
  -d "quiz[scoreType]=1"
```

## 9.3 Quiz Configuration (KalturaQuiz)

| Field | Type | Description |
|-------|------|-------------|
| `version` | int | Auto-incremented on update (readonly) |
| `showResultOnAnswer` | int | Show correct/incorrect immediately (-1/0/1) |
| `showCorrectKeyOnAnswer` | int | Show correct answer key while answering |
| `allowAnswerUpdate` | int | Allow changing answers before submission |
| `showCorrectAfterSubmission` | int | Reveal correct answers after submit |
| `allowDownload` | int | Allow PDF download of quiz |
| `showGradeAfterSubmission` | int | Show score after submit |
| `attemptsAllowed` | int | Number of retakes allowed |
| `scoreType` | int | How to calculate final score across attempts |

**Score Types:**

| Value | Name | Description |
|-------|------|-------------|
| 1 | HIGHEST | Best score across all attempts |
| 2 | LOWEST | Worst score across all attempts |
| 3 | LATEST | Most recent attempt |
| 4 | FIRST | First attempt only |
| 5 | AVERAGE | Average across all attempts |

**Quiz Service Actions:**

| Action | Description |
|--------|-------------|
| `add` | Mark entry as quiz with configuration |
| `get` | Get quiz config by entryId |
| `update` | Update quiz settings (increments version) |
| `list` | List quiz entries |
| `serve` | Download quiz as PDF |
| `getUrl` | Get PDF download URL |

## 9.4 Add Quiz Questions

Questions are `KalturaQuestionCuePoint` cue points:

```bash
curl -X POST "$KALTURA_SERVICE_URL/service/cuepoint_cuepoint/action/add" \
  -d "ks=$KALTURA_KS" \
  -d "format=1" \
  -d "cuePoint[objectType]=KalturaQuestionCuePoint" \
  -d "cuePoint[entryId]=1_abc123" \
  -d "cuePoint[startTime]=30000" \
  -d "cuePoint[question]=What design pattern separates object creation from usage?" \
  -d "cuePoint[questionType]=1" \
  -d "cuePoint[hint]=Think about object creation" \
  -d "cuePoint[explanation]=The Factory pattern delegates instantiation to subclasses" \
  -d "cuePoint[optionalAnswers][0][key]=1" \
  -d "cuePoint[optionalAnswers][0][text]=Factory" \
  -d "cuePoint[optionalAnswers][0][isCorrect]=1" \
  -d "cuePoint[optionalAnswers][0][weight]=1" \
  -d "cuePoint[optionalAnswers][1][key]=2" \
  -d "cuePoint[optionalAnswers][1][text]=Singleton" \
  -d "cuePoint[optionalAnswers][1][isCorrect]=0" \
  -d "cuePoint[optionalAnswers][1][weight]=1" \
  -d "cuePoint[optionalAnswers][2][key]=3" \
  -d "cuePoint[optionalAnswers][2][text]=Observer" \
  -d "cuePoint[optionalAnswers][2][isCorrect]=0" \
  -d "cuePoint[optionalAnswers][2][weight]=1"
```

## 9.5 Question Types

| Value | Name | Description |
|-------|------|-------------|
| 1 | MULTIPLE_CHOICE_ANSWER | Single correct answer from options |
| 2 | TRUE_FALSE | True/false question |
| 3 | REFLECTION_POINT | Pause for reflection (no correct answer, not scored) |
| 4 | MULTIPLE_ANSWER_QUESTION | Multiple correct answers |
| 5 | FILL_IN_BLANK | Fill in the blank |
| 6 | HOT_SPOT | Hotspot on video frame |
| 7 | GO_TO | Navigation/branching point |
| 8 | OPEN_QUESTION | Free-text open-ended question |

## 9.6 Question Fields (in addition to base)

| Field | Type | Description |
|-------|------|-------------|
| `question` | string | Question text |
| `questionType` | int | Question type (see table above) |
| `optionalAnswers` | array | Array of answer choices |
| `hint` | string | Hint text shown to viewer |
| `explanation` | string | Explanation (hidden from non-editors) |
| `presentationOrder` | int | Display order |
| `excludeFromScore` | int | Exclude from score calculation (-1/0/1) |

Each `optionalAnswer` has: `key` (string), `text` (string), `weight` (float, default 1.0), `isCorrect` (int: -1/0/1).

**Security:** When a non-editor viewer retrieves question cue points, `isCorrect` on each answer option is returned as null and `explanation` is omitted. This prevents viewers from reading correct answers via the API.

## 9.7 Viewer Quiz Flow

**Step 1 — Start attempt:**

```bash
curl -X POST "$KALTURA_SERVICE_URL/service/userentry/action/add" \
  -d "ks=$KALTURA_KS" \
  -d "format=1" \
  -d "userEntry[objectType]=KalturaQuizUserEntry" \
  -d "userEntry[entryId]=1_abc123"
```

Returns a `KalturaQuizUserEntry` with `id`, `status=1` (ACTIVE), and `version` (attempt number).

**Step 2 — Submit answers:**

For each question, create an `KalturaAnswerCuePoint`:

```bash
curl -X POST "$KALTURA_SERVICE_URL/service/cuepoint_cuepoint/action/add" \
  -d "ks=$KALTURA_KS" \
  -d "format=1" \
  -d "cuePoint[objectType]=KalturaAnswerCuePoint" \
  -d "cuePoint[entryId]=1_abc123" \
  -d "cuePoint[parentId]=1_question_cp_id" \
  -d "cuePoint[quizUserEntryId]=12345" \
  -d "cuePoint[answerKey]=1"
```

The server auto-calculates `isCorrect` by comparing `answerKey` against the question's correct answer keys.

**Step 3 — Submit quiz for scoring:**

```bash
curl -X POST "$KALTURA_SERVICE_URL/service/userentry/action/submitQuiz" \
  -d "ks=$KALTURA_KS" \
  -d "format=1" \
  -d "id=12345"
```

Returns the `KalturaQuizUserEntry` with `score`, `calculatedScore`, and `status=quiz.3` (SUBMITTED).

## 9.8 Answer Fields

| Field | Type | Description |
|-------|------|-------------|
| `parentId` | string | Question cue point ID (insert-only, **required**) |
| `quizUserEntryId` | string | User entry ID for this attempt (insert-only, **required**) |
| `answerKey` | string | Selected answer key |
| `openAnswer` | string | Free-text answer (max 1024 chars, for open questions) |
| `isCorrect` | int | Server-computed correctness (readonly) |
| `correctAnswerKeys` | array | Correct answer keys from the question (readonly) |
| `explanation` | string | Explanation copied from question (readonly) |
| `feedback` | string | Instructor feedback (max 1024 chars, admin-only write) |

## 9.9 Quiz User Entry Fields

| Field | Type | Description |
|-------|------|-------------|
| `score` | float | Raw quiz score (readonly) |
| `calculatedScore` | float | Score based on scoreType across attempts (readonly) |
| `feedback` | string | Overall instructor feedback (max 1024 chars) |
| `version` | int | Attempt number, 0-based (readonly) |
| `status` | string | 1=ACTIVE, 2=DELETED, quiz.3=SUBMITTED |

## 9.10 Quiz Reports

The quiz plugin provides four report types accessible via `report.getTable`:

| reportType | Description |
|------------|-------------|
| `quiz.QUIZ` | Per-question correct/wrong percentage |
| `quiz.QUIZ_USER_PERCENTAGE` | Per-user overall percentage |
| `quiz.QUIZ_AGGREGATE_BY_QUESTION` | Aggregated by specific question IDs |
| `quiz.QUIZ_USER_AGGREGATE_BY_QUESTION` | Per-user per-question breakdown |


# 10. eSearch Integration

Cue point content is indexed in Elasticsearch and searchable via `KalturaESearchCuePointItem`.

## 10.1 Searchable Fields

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

## 10.2 Search Within Slide OCR Text

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

## 10.3 Search Quiz Questions

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

## 10.4 Unified Search

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


# 11. Player Integration

Five Player v7 plugins form the cue point rendering ecosystem.

## 11.1 Plugin Architecture

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

## 11.2 Core Plugin: kalturaCuepoints

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

## 11.3 Navigation Plugin

Side panel with tabs for chapters, slides, captions, hotspots, quiz questions, and full-text search:

```javascript
plugins: {
  navigation: {
    expandOnFirstPlay: true,
    position: 'right',
    expandMode: 'alongside',
    itemsOrder: {
      Chapter: 1,
      Slide: 2,
      Hotspot: 3,
      Caption: 4,
      QuizQuestion: 5
    }
  }
}
```

| Config | Type | Default | Description |
|--------|------|---------|-------------|
| `expandOnFirstPlay` | boolean | false | Auto-open panel on first play |
| `position` | string | `'right'` | Panel position: right, left, top, bottom |
| `expandMode` | string | `'alongside'` | `alongside` (shrinks video) or `over` (overlays) |
| `itemsOrder` | object | {} | Tab ordering and filtering — only listed types are shown |
| `visible` | boolean | true | Show/hide the plugin |

## 11.4 Interactive Video Quiz (IVQ) Plugin

Renders quiz questions as overlays during playback:

```javascript
plugins: {
  ivq: {}
}
```

All quiz behavior is driven by the quiz data on the entry (via `quiz.get`), not plugin config.

**Quiz player flow:**
1. Welcome screen (if `showWelcomePage` enabled) with available attempts
2. As playback reaches a question's `startTime`, video pauses and question overlay appears
3. If `preventSeek` is enabled, forward seeking is blocked (middleware intercepts `setCurrentTime`)
4. After all questions answered and video ends, submit screen appears
5. After submission, review screen shows score and correct answers (per quiz config)

**Events:** `QuizStarted`, `QuizSkipped`, `QuestionAnswered`, `QuizSubmitted`, `QuizRetake`

## 11.5 Dual-Screen Plugin

Synchronized playback of video + slides or video + secondary camera:

```javascript
plugins: {
  dualscreen: {
    layout: 'PIP',
    position: 'bottom-right',
    childSizePercentage: 30
  }
}
```

| Layout | Description |
|--------|-------------|
| `PIP` | Primary large, secondary small overlay |
| `PIPInverse` | Secondary large, primary small |
| `SideBySide` | Equal side-by-side |
| `SideBySideInverse` | Swapped positions |
| `SingleMedia` | Primary only (secondary in bottom bar) |
| `SingleMediaInverse` | Secondary only |
| `Hidden` | Dual-screen disabled |

View-change code cue points can switch layouts programmatically during playback.

## 11.6 Full Setup Example

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


# 12. Bulk Operations

## 12.1 XML Import

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

## 12.2 Clone Support

| Type | Clonable | Clone Option Constant |
|------|----------|-----------------------|
| Ad | Yes | `AD_CUE_POINTS` |
| Annotation | Yes | `ANNOTATION_CUE_POINTS` |
| Code | Yes | `CODE_CUE_POINTS` |
| Session | Yes | `SESSION_CUE_POINTS` |
| Thumb | Yes | `THUMB_CUE_POINTS` |
| Event | No | — |
| Quiz (Question/Answer) | No | — |

## 12.3 Custom Metadata

Ad, Annotation, Code, Thumb, and Quiz cue points support custom metadata profiles (XSD schemas attached to cue points via the Metadata API). This enables structured data on individual cue points beyond the built-in fields.


# 13. Error Handling

| Error | Cause | Fix |
|-------|-------|-----|
| `PROPERTY_VALIDATION_CANNOT_BE_NULL` | List/count without identifying filter | Include `entryIdEqual`, `entryIdIn`, `idEqual`, or `idIn` |
| `INVALID_CUE_POINT_ID` | Cue point not found or already deleted | Verify ID exists and status is not DELETED |
| `CUE_POINT_SYSTEM_NAME_EXISTS` | Duplicate `systemName` on the same entry | System names must be unique per entry |
| `PARENT_CUE_POINT_NOT_FOUND` | Invalid `parentId` on annotation/answer | Parent must exist on the same entry |
| `PROPERTY_VALIDATION_NOT_UPDATABLE` | Updating `protocolType` on ad cue point | `protocolType` is immutable after creation |
| `PROVIDED_ENTRY_IS_ALREADY_A_QUIZ` | Calling `quiz.add` on entry with existing quiz config | Use `quiz.update` to modify existing config |
| `NO_PERMISSION_ON_ENTRY` | KS `limitEntry` privilege mismatch | Ensure KS has access to the target entry |
| `CANNOT_APPROVE_TASK`-like for quiz | Submitting already-submitted quiz | Check `userEntry.status` before submission |


# 14. Best Practices

- **Times are in milliseconds.** A cue point at 1 minute 30 seconds = `startTime=90000`.
- **Use `cuepoint_cuepoint` service** for all operations. The `annotation_annotation` service is deprecated and has restricted actions.
- **Include `objectType` on updates.** The API needs it to determine which fields to apply.
- **Register cleanup before assertions** in tests. Cue points persist on entries — always clean up test cue points.
- **eSearch indexing has a delay.** Newly created cue points may take seconds to appear in search results. Use `cuePoint.list` for immediate retrieval.
- **Quiz answer security is server-enforced.** Non-editors cannot see `isCorrect` or `explanation` on question cue points — no client-side hiding needed.
- **Thumb cue points need assets for READY status.** Without an associated `timedThumbAsset`, thumb cue points remain in PENDING (4) status. See section 3.4 for the full attachment workflow.
- **Filter is mandatory.** Every `list`/`count` call must include at least one identifying filter field.
- **Ad `protocolType` is set once.** Plan the protocol type before creating ad cue points — it cannot be changed.
- **Use `forceStop=1`** to pause the player at a cue point (works for all types, not just quizzes).


# 15. Related Guides

- [eSearch API](KALTURA_ESEARCH_API.md) — Full search syntax, `KalturaESearchCuePointItem` details
- [Player Embed Guide](KALTURA_PLAYER_EMBED_GUIDE.md) — Player v7 setup, plugin configuration
- [REACH API](KALTURA_REACH_API.md) — AI-powered chaptering (serviceFeature=5), captions as cue point-adjacent content
- [Content Lab API](KALTURA_CONTENT_LAB_API.md) — AI-generated chapters and quizzes
- [Captions & Transcripts](KALTURA_CAPTIONS_AND_TRANSCRIPTS_API.md) — Caption assets (related but separate from cue points)
- [Multi-Stream API](KALTURA_MULTI_STREAM_API.md) — Dual-screen entries with slide/camera sync
- [Custom Metadata API](KALTURA_CUSTOM_METADATA_API.md) — Attaching structured metadata to cue points
- [Upload & Delivery API](KALTURA_UPLOAD_AND_DELIVERY_API.md) — Thumbnail assets for slide images
- [Analytics Reports API](KALTURA_ANALYTICS_REPORTS_API.md) — Quiz reports and engagement analytics
- [Gamification API](KALTURA_GAMIFICATION_API.md) — Quiz scores as gamification inputs

# Kaltura Multi-Stream (Dual/Multi-Screen) Entries API

Create synchronized multi-stream entries for dual-screen playback — Picture-in-Picture, Side-by-Side, and stream selection. A multi-stream entry consists of a parent entry (primary video with audio and timeline control) and one or more child entries linked via the `parentEntryId` field.

**Base URL:** `https://www.kaltura.com/api_v3` (may differ by region/deployment)
**Auth:** All requests require a valid KS (see [Session Guide](KALTURA_SESSION_GUIDE.md))
**Format:** Form-encoded POST, `format=1` for JSON responses

## Prerequisites

- A Kaltura account with a valid Partner ID
- A KS with appropriate privileges (see [Session Guide](KALTURA_SESSION_GUIDE.md))
- A player with the Dual Screen plugin enabled (see [Section 5](#5-player-setup))
- Video files that are in sync (same duration, same starting point)
- For uploading new files, see the [Upload & Delivery Guide](KALTURA_UPLOAD_AND_DELIVERY_API.md)


# 1. Multi-Stream Architecture

A multi-stream entry is a parent-child relationship between regular media entries:

| Role | Description |
|------|-------------|
| **Parent entry** | Primary video. Plays with audio. Controls the timeline. One per multi-stream set. |
| **Child entries** | Secondary streams. Play without audio by default. No limit on count. |

```
Parent: 1_abc123  (Speaker camera)
  Child 1: 1_def456  (Screen share)       → parentEntryId = 1_abc123
  Child 2: 1_ghi789  (Whiteboard camera)  → parentEntryId = 1_abc123
  Child 3: 1_jkl012  (Audience camera)    → parentEntryId = 1_abc123
```

Key behaviors:
- The parent entry's audio plays continuously regardless of which streams are displayed
- The timeline reflects the parent entry's duration
- Only the parent entry appears in search results and media listings by default
- The parent-child link is one-way: the child knows its parent. Use `baseEntry.list` with `parentEntryIdEqual` filter to find all children of a parent


# 2. Create a Multi-Stream Entry Set

This workflow creates a parent entry and links child entries to it. For the upload steps (`uploadToken.add`, `uploadToken.upload`, `media.add`, `media.addContent`), see the [Upload & Delivery Guide](KALTURA_UPLOAD_AND_DELIVERY_API.md) for full details including chunked/resumable uploads.

## 2.1 Create the Parent Entry

Upload and create the parent entry using the standard upload flow:

```bash
# Step 1: Create upload token
curl -X POST "$KALTURA_SERVICE_URL/service/uploadToken/action/add" \
  -d "ks=$KALTURA_KS" \
  -d "format=1"
# Save the "id" from response as PARENT_TOKEN_ID

# Step 2: Upload the file
curl -X POST "$KALTURA_SERVICE_URL/service/uploadToken/action/upload" \
  -F "ks=$KALTURA_KS" \
  -F "uploadTokenId=$PARENT_TOKEN_ID" \
  -F "resume=false" \
  -F "finalChunk=true" \
  -F "resumeAt=-1" \
  -F "fileData=@primary-video.mp4;type=video/mp4"

# Step 3: Create the media entry
curl -X POST "$KALTURA_SERVICE_URL/service/media/action/add" \
  -d "ks=$KALTURA_KS" \
  -d "format=1" \
  -d "entry[objectType]=KalturaMediaEntry" \
  -d "entry[mediaType]=1" \
  -d "entry[name]=Speaker Camera"
# Save the "id" from response as PARENT_ENTRY_ID

# Step 4: Attach the file to the entry
curl -X POST "$KALTURA_SERVICE_URL/service/media/action/addContent" \
  -d "ks=$KALTURA_KS" \
  -d "format=1" \
  -d "entryId=$PARENT_ENTRY_ID" \
  -d "resource[objectType]=KalturaUploadedFileTokenResource" \
  -d "resource[token]=$PARENT_TOKEN_ID"
```

Wait for the parent entry status to become `2` (Ready) before proceeding.

## 2.2 Create a Child Entry with parentEntryId

The key difference from a normal upload: set `entry[parentEntryId]` in the `media.add` call to link the child to the parent.

```bash
# Step 1: Create upload token for child
curl -X POST "$KALTURA_SERVICE_URL/service/uploadToken/action/add" \
  -d "ks=$KALTURA_KS" \
  -d "format=1"
# Save the "id" from response as CHILD_TOKEN_ID

# Step 2: Upload the child file
curl -X POST "$KALTURA_SERVICE_URL/service/uploadToken/action/upload" \
  -F "ks=$KALTURA_KS" \
  -F "uploadTokenId=$CHILD_TOKEN_ID" \
  -F "resume=false" \
  -F "finalChunk=true" \
  -F "resumeAt=-1" \
  -F "fileData=@screen-share.mp4;type=video/mp4"

# Step 3: Create the child entry — set parentEntryId
curl -X POST "$KALTURA_SERVICE_URL/service/media/action/add" \
  -d "ks=$KALTURA_KS" \
  -d "format=1" \
  -d "entry[objectType]=KalturaMediaEntry" \
  -d "entry[mediaType]=1" \
  -d "entry[name]=Screen Share" \
  -d "entry[parentEntryId]=$PARENT_ENTRY_ID"
# Save the "id" from response as CHILD_ENTRY_ID

# Step 4: Attach the file
curl -X POST "$KALTURA_SERVICE_URL/service/media/action/addContent" \
  -d "ks=$KALTURA_KS" \
  -d "format=1" \
  -d "entryId=$CHILD_ENTRY_ID" \
  -d "resource[objectType]=KalturaUploadedFileTokenResource" \
  -d "resource[token]=$CHILD_TOKEN_ID"
```

Repeat this step for each additional stream. Each child entry must reference the same `$PARENT_ENTRY_ID`.


# 3. Link an Existing Entry as a Child

If you already have both videos as independent entries, link them after the fact using `baseEntry.update`:

```bash
curl -X POST "$KALTURA_SERVICE_URL/service/baseEntry/action/update" \
  -d "ks=$KALTURA_KS" \
  -d "format=1" \
  -d "entryId=$ENTRY_TO_BECOME_CHILD" \
  -d "baseEntry[parentEntryId]=$PARENT_ENTRY_ID"
```

To unlink a child entry (make it independent again), clear the `parentEntryId`:

```bash
curl -X POST "$KALTURA_SERVICE_URL/service/baseEntry/action/update" \
  -d "ks=$KALTURA_KS" \
  -d "format=1" \
  -d "entryId=$CHILD_ENTRY_ID" \
  -d "baseEntry[parentEntryId]="
```


# 4. Verify and List Multi-Stream Entries

## 4.1 Verify an Entry's Parent-Child Relationship

```bash
# Get parent entry details
curl -X POST "$KALTURA_SERVICE_URL/service/baseEntry/action/get" \
  -d "ks=$KALTURA_KS" \
  -d "format=1" \
  -d "entryId=$PARENT_ENTRY_ID"

# Get child entry — confirm parentEntryId is set
curl -X POST "$KALTURA_SERVICE_URL/service/baseEntry/action/get" \
  -d "ks=$KALTURA_KS" \
  -d "format=1" \
  -d "entryId=$CHILD_ENTRY_ID"
```

Confirm:
- Both entries have `"status": 2` (Ready)
- The child entry's `parentEntryId` matches the parent's `id`
- Durations match (for synchronized playback)

## 4.2 List All Children of a Parent

Use `baseEntry.list` with the `parentEntryIdEqual` filter:

```bash
curl -X POST "$KALTURA_SERVICE_URL/service/baseEntry/action/list" \
  -d "ks=$KALTURA_KS" \
  -d "format=1" \
  -d "filter[parentEntryIdEqual]=$PARENT_ENTRY_ID"
```

The response `objects` array contains all child entries linked to the parent. The `totalCount` field shows how many children exist.


# 5. Player v7 Dual Screen Setup

The **Dual Screen plugin** (`@playkit-js/playkit-js-dual-screen`) enables synchronized multi-stream playback in Kaltura Player v7 (PlayKit). It requires the `kalturaCuepoints` plugin if showing slides.

## 5.1 Enable via KMC Studio

1. Log in to KMC and go to the **Studio** tab
2. Select the player you want to configure (or create a new one)
3. Scroll to **Engagement & Interactivity**
4. Toggle **Dual screen** on
5. Configure the default layout:
   - **Picture-in-Picture** — primary video large, secondary as overlay (default)
   - **Side-by-Side** — both streams displayed equally
   - **Single Media** — only one stream visible at a time
6. Set the **PiP position** (Top Right, Bottom Right, Top Left, Bottom Left)
7. Click **Save**

## 5.2 Enable via JavaScript Config

When using `KalturaPlayer.setup()`, add the `dualscreen` plugin to the config:

```javascript
var config = {
  targetId: 'player-container',
  plugins: {
    dualscreen: {
      layout: 'PIP',
      position: 'bottom-right',
      childSizePercentage: 30,
      childAspectRatio: { width: 16, height: 9 }
    },
    kalturaCuepoints: {}  // Required if showing slides
  }
};

var player = KalturaPlayer.setup(config);
player.loadMedia({ entryId: 'PARENT_ENTRY_ID' });
```

## 5.3 Plugin Configuration Options

| Key | Type | Default | Description |
|-----|------|---------|-------------|
| `layout` | string | `"PIP"` | Initial layout mode (see layout modes below) |
| `position` | string | `"bottom-right"` | PiP overlay position: `"bottom-left"`, `"bottom-right"`, `"top-left"`, `"top-right"` |
| `childSizePercentage` | number | `30` | Height of PiP child as percentage of parent player height |
| `childAspectRatio` | object | `{width: 16, height: 9}` | Aspect ratio of the PiP container |
| `slidesPreloadEnabled` | boolean | `true` | Preload slide images |
| `removePlayerSettings` | boolean | `false` | Hide media settings button when dual screen is active |

These values define the initial appearance on load. Viewers can interactively change layout and position during playback.

## 5.4 Layout Modes

| Layout | Description |
|--------|-------------|
| `PIP` | Primary video large, secondary as small overlay |
| `PIPInverse` | Secondary video large, primary as small overlay |
| `SideBySide` | Both streams side by side (primary on left) |
| `SideBySideInverse` | Both streams side by side (primary on right) |
| `SingleMedia` | Only primary video shown |
| `SingleMediaInverse` | Only secondary video shown |
| `Hidden` | Dual screen deactivated |

## 5.5 Programmatic Control via JavaScript API

The plugin registers a `dualScreen` service on the player instance:

```javascript
var player = KalturaPlayer.setup(config);
player.loadMedia({ entryId: 'PARENT_ENTRY_ID' });

// Access the dual screen service
var dualScreenService = player.getService('dualScreen');

// Wait for secondary media to load
dualScreenService.ready.then(function() {
  var activePlayer = dualScreenService.getActivePlayer();
  var pipPlayer = dualScreenService.getPipPlayer();
  var allPlayers = dualScreenService.getDualScreenPlayers();
});
```

**Service methods:**

| Method | Returns | Description |
|--------|---------|-------------|
| `ready` | `Promise<void>` | Resolves when secondary media is loaded |
| `getActivePlayer()` | `DualScreenPlayer` | The player in the primary (large) container |
| `getPipPlayer()` | `DualScreenPlayer` | The player in the PiP (small) container |
| `getDualScreenPlayers(types?, container?)` | `DualScreenPlayer[]` | All dual screen player instances |
| `getDualScreenThumbs(time)` | thumbnail info | Thumbnail data for both screens at a given time |

**Switch layout programmatically at runtime:**

The plugin's initial config (`layout`, `position`) is set via `KalturaPlayer.setup()`. To switch layouts at runtime, access the plugin instance via `player.plugins.dualscreen` and call its internal `_switchTo*` methods after the `dualScreen` service is ready:

```javascript
var dualScreenService = player.getService('dualScreen');

dualScreenService.ready.then(function() {
  var ds = player.plugins.dualscreen;

  // Switch to Side-by-Side
  ds._switchToSideBySide({ force: true }, true);

  // Switch to PiP
  ds._switchToPIP({ force: true }, true);

  // Switch to PiP with screens swapped (secondary becomes main)
  ds._applyInverse();
  ds._switchToPIP({ force: true }, true);

  // Switch to Single Media (primary only)
  ds._switchToSingleMedia({ force: true }, true);

  // Hide dual screen entirely
  ds._switchToHidden(true);
});
```

The first argument is `{ force: true }` to ensure the switch happens even if the plugin thinks it's already in that layout. The second argument (`true`) marks it as a user interaction so the `dualscreen_change_layout` event fires.

For the `Inverse` variants (`PIPInverse`, `SideBySideInverse`, `SingleMediaInverse`), call `ds._applyInverse()` before the `_switchTo*` method to swap which stream is primary vs. secondary.

## 5.6 Events

The plugin emits two custom events:

| Event | Description |
|-------|-------------|
| `dualscreen_change_layout` | Fired when the layout changes (user interaction or programmatic) |
| `dualscreen_side_displayed` | Fired when a side/layout is rendered |

```javascript
player.addEventListener('dualscreen_change_layout', function(event) {
  console.log('Layout changed to:', event.payload.layout);
});
```

See the [Player Embed Guide](KALTURA_PLAYER_EMBED_GUIDE.md) for full embedding details.


# 6. Playback Behavior

| Streams | Player Behavior |
|---------|----------------|
| **2 streams** | PiP or Side-by-Side toggle. Viewers can swap primary/secondary. |
| **3+ streams** | Stream selector appears (three-dot menu). Viewers choose which streams to display on each screen. |

- Viewers can drag the PiP overlay to any corner, show/hide it, or pop it out
- Child entries play without audio by default; the parent's audio track is authoritative
- Renaming the parent entry is independent of child entries


# 7. Complete Example — Multi-Stream Lifecycle

```bash
# Prerequisites: set these shell variables before running the commands below
# KALTURA_SERVICE_URL="https://www.kaltura.com/api_v3"
# KALTURA_KS="<your Kaltura Session>"

# --- Step 1: Create the parent entry (using addFromUrl for simplicity) ---
curl -X POST "$KALTURA_SERVICE_URL/service/media/action/addFromUrl" \
  -d "ks=$KALTURA_KS" \
  -d "format=1" \
  -d "mediaEntry[objectType]=KalturaMediaEntry" \
  -d "mediaEntry[name]=Speaker Camera" \
  -d "mediaEntry[mediaType]=1" \
  -d "url=https://example.com/speaker.mp4"
# Save the "id" from response as PARENT_ENTRY_ID

# --- Step 2: Create a child entry linked to the parent ---
curl -X POST "$KALTURA_SERVICE_URL/service/media/action/addFromUrl" \
  -d "ks=$KALTURA_KS" \
  -d "format=1" \
  -d "mediaEntry[objectType]=KalturaMediaEntry" \
  -d "mediaEntry[name]=Screen Share" \
  -d "mediaEntry[mediaType]=1" \
  -d "mediaEntry[parentEntryId]=$PARENT_ENTRY_ID" \
  -d "url=https://example.com/screen-share.mp4"
# Save the "id" from response as CHILD_ENTRY_ID

# --- Step 3: Verify the relationship ---
curl -X POST "$KALTURA_SERVICE_URL/service/baseEntry/action/get" \
  -d "ks=$KALTURA_KS" \
  -d "format=1" \
  -d "entryId=$CHILD_ENTRY_ID"
# Confirm parentEntryId matches PARENT_ENTRY_ID

# --- Step 4: List all children of the parent ---
curl -X POST "$KALTURA_SERVICE_URL/service/baseEntry/action/list" \
  -d "ks=$KALTURA_KS" \
  -d "format=1" \
  -d "filter[parentEntryIdEqual]=$PARENT_ENTRY_ID"

# --- Step 5: Link another existing entry as a child ---
curl -X POST "$KALTURA_SERVICE_URL/service/baseEntry/action/update" \
  -d "ks=$KALTURA_KS" \
  -d "format=1" \
  -d "entryId=$ANOTHER_ENTRY_ID" \
  -d "baseEntry[parentEntryId]=$PARENT_ENTRY_ID"

# --- Step 6: Unlink a child (make it independent) ---
curl -X POST "$KALTURA_SERVICE_URL/service/baseEntry/action/update" \
  -d "ks=$KALTURA_KS" \
  -d "format=1" \
  -d "entryId=$CHILD_ENTRY_ID" \
  -d "baseEntry[parentEntryId]="

# --- Step 7: Clean up ---
curl -X POST "$KALTURA_SERVICE_URL/service/media/action/delete" \
  -d "ks=$KALTURA_KS" \
  -d "format=1" \
  -d "entryId=$CHILD_ENTRY_ID"

curl -X POST "$KALTURA_SERVICE_URL/service/media/action/delete" \
  -d "ks=$KALTURA_KS" \
  -d "format=1" \
  -d "entryId=$PARENT_ENTRY_ID"
```


# 8. API Reference

| Action | Purpose |
|--------|---------|
| `media.add` | Create a new media entry (set `parentEntryId` here for child entries) |
| `media.addContent` | Attach an uploaded file to an entry |
| `media.addFromUrl` | Create entry and import from URL (set `parentEntryId` for child) |
| `baseEntry.update` | Link/unlink an existing entry as a child (set/clear `parentEntryId`) |
| `baseEntry.get` | Retrieve entry details to verify parent-child setup |
| `baseEntry.list` | List entries (use `filter[parentEntryIdEqual]` to find children) |
| `uploadToken.add` | Create an upload token |
| `uploadToken.upload` | Upload a file to the token |


# 9. Error Handling

| Error Code | Meaning | Resolution |
|------------|---------|------------|
| `ENTRY_ID_NOT_FOUND` | Entry ID does not exist | Verify the entry ID; entry may have been deleted |
| `INVALID_ENTRY_TYPE` | Operation not supported for this entry type | Multi-stream requires `mediaType=1` (VIDEO) entries |
| `PROPERTY_VALIDATION_NOT_UPDATABLE` | Attempted to change a read-only property | `parentEntryId` can only be set once; to re-parent, clone the entry |
| `MAX_ENTRIES_REACHED` | Partner entry limit reached | Delete unused entries or contact account manager |

**Retry strategy:** For transient errors (HTTP 5xx, timeouts), retry with exponential backoff: 1s, 2s, 4s, with jitter, up to 3 retries. For client errors (`ENTRY_ID_NOT_FOUND`, `INVALID_ENTRY_TYPE`, `PROPERTY_VALIDATION_NOT_UPDATABLE`), fix the request before retrying — these will not resolve on their own.

# 10. Best Practices

- **Create child entries with the correct `parentEntryId` from the start.** Setting `parentEntryId` during creation is more reliable than updating it later.
- **Use USER KS (type=0)** for player-side operations. The Dual Screen player needs a KS to discover child entries via the API, but a scoped user session is sufficient.
- **Poll for child entry READY status** before embedding. Multi-stream playback requires all entries to be transcoded.
- **Use `addFromUrl` with direct MP4 URLs** for child entries. Redirect URLs (e.g., `playManifest`) cause import failures.
- **Leverage REACH for all streams.** Order captions on both parent and child entries for complete accessibility coverage.

# 11. Related Guides

- **[Session Guide](KALTURA_SESSION_GUIDE.md)** — Generate the KS needed for API auth
- **[Upload & Delivery Guide](KALTURA_UPLOAD_AND_DELIVERY_API.md)** — Full upload lifecycle (chunked, resumable, import from URL)
- **[Player Embed Guide](KALTURA_PLAYER_EMBED_GUIDE.md)** — Embed the Dual Screen player
- **[eSearch Guide](KALTURA_ESEARCH_API.md)** — Search for parent entries (use `parentEntryIdEqual` filter to find child entries)
- **[Webhooks API](KALTURA_WEBHOOKS_API.md)** — Get notified when entries finish processing (HTTP callbacks)
- **[REACH Guide](KALTURA_REACH_API.md)** — Auto-caption parent and child streams
- **[Agents Manager](KALTURA_AGENTS_MANAGER_API.md)** — Automate processing of multi-stream content

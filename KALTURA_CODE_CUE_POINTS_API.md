# Kaltura Code, Event & Session Cue Points API

Code cue points are generic developer-defined markers that trigger player  
events at specific times. Event and session cue points mark broadcast  
lifecycle and recording session boundaries — they are primarily  
auto-created by the media server during live streaming.

**Base URL:** `$KALTURA_SERVICE_URL` (e.g., `https://www.kaltura.com/api_v3`)  
**Auth:** KS via `ks` parameter (admin KS with `disableentitlement` for full access)  
**Format:** `format=1` for JSON responses  
**Service:** `cuepoint_cuepoint` (shared with all cue point types)  
**Prerequisite:** [Cue Points Hub](KALTURA_CUE_POINTS_API.md) for base cue point concepts and shared CRUD


# 1. When to Use

- **Programmatic triggers during playback** — Fire custom application logic (overlays, navigation prompts, animations) at specific moments in a video by listening for code cue point events in the player.  
- **Dual-screen layout switching** — Control picture-in-picture, side-by-side, and single-view layouts during multi-stream playback by tagging code cue points with `change-view-mode`.  
- **Live broadcast markers** — Read auto-generated event cue points to detect when a live stream started and ended, enabling post-broadcast analytics and timeline segmentation.  
- **Recording session boundaries** — Mark breakout rooms, speaker transitions, or meeting segments within a recorded session for structured playback navigation.  
- **Automated action points** — Create markers that external systems consume to trigger downstream workflows (e.g., send a notification, log an interaction, update a dashboard) at precise video timestamps.


# 2. Prerequisites

- **KS (Kaltura Session):** Admin KS (type=2) with `disableentitlement` for creating and managing code and session cue points. Event cue points are auto-created by the media server and typically read-only for API consumers.  
- **Cue Points plugin:** The `cuePoint` and `codeCuePoint` server plugins must be enabled on the account (enabled by default on most accounts).  
- **Player plugins:** To respond to code cue points during playback, enable `kalturaCuepoints` and optionally `dualscreen` in the player configuration.  
- **Session management:** See [Session Guide](KALTURA_SESSION_GUIDE.md) for KS generation and privilege scoping.


# 3. Code Cue Points

Generic markers used for custom interactions, view-change commands (dual-screen layout switching), and programmatic triggers.

**objectType:** `KalturaCodeCuePoint`

## 3.1 Fields (in addition to base)

| Field | Type | Description |
|-------|------|-------------|
| `code` | string | Identifier code (**required**) |
| `description` | string | Free text description |
| `endTime` | int | End time in milliseconds |
| `duration` | int | Computed duration (readonly) |

## 3.2 Create a Code Cue Point

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

## 3.3 View-Change Commands

The `dualscreen` player plugin uses code cue points tagged `change-view-mode` to control layout:

```bash
curl -X POST "$KALTURA_SERVICE_URL/service/cuepoint_cuepoint/action/add" \
  -d "ks=$KALTURA_KS" \
  -d "format=1" \
  -d "cuePoint[objectType]=KalturaCodeCuePoint" \
  -d "cuePoint[entryId]=1_abc123" \
  -d "cuePoint[startTime]=50000" \
  -d "cuePoint[code]=pip-parent-in-large" \
  -d "cuePoint[tags]=change-view-mode"
```

| code Value | Layout |
|------------|--------|
| `locked` | Hidden (dual-screen disabled) |
| `parent-only` | Primary video only |
| `no-parent` | Secondary only (slides/camera) |
| `pip-parent-in-large` | PIP with primary large |
| `pip-parent-in-small` | PIP with secondary large |
| `sbs-parent-in-left` | Side-by-side, primary left |
| `sbs-parent-in-right` | Side-by-side, primary right |

## 3.4 systemName Uniqueness

The `systemName` field provides a human-readable identifier for cue points. It must be unique within an entry — attempting to create a second cue point with the same `systemName` on the same entry returns `CUE_POINT_SYSTEM_NAME_EXISTS`.

```bash
curl -X POST "$KALTURA_SERVICE_URL/service/cuepoint_cuepoint/action/update" \
  -d "ks=$KALTURA_KS" \
  -d "format=1" \
  -d "id=1_cp_id" \
  -d "cuePoint[objectType]=KalturaCodeCuePoint" \
  -d "cuePoint[systemName]=intro-overlay"
```

## 3.5 forceStop

Set `forceStop=1` on any cue point to pause the player when playback reaches that position. Works for all cue point types, not just quizzes:

```bash
curl -X POST "$KALTURA_SERVICE_URL/service/cuepoint_cuepoint/action/add" \
  -d "ks=$KALTURA_KS" \
  -d "format=1" \
  -d "cuePoint[objectType]=KalturaCodeCuePoint" \
  -d "cuePoint[entryId]=1_abc123" \
  -d "cuePoint[startTime]=55000" \
  -d "cuePoint[code]=pause-marker" \
  -d "cuePoint[forceStop]=1"
```


# 4. Event Cue Points

Markers for live broadcast lifecycle events. Enabled for all partners (no plugin activation needed).

**objectType:** `KalturaEventCuePoint`

## 4.1 Fields (in addition to base)

| Field | Type | Description |
|-------|------|-------------|
| `eventType` | int | 1=BROADCAST_START, 2=BROADCAST_END |

## 4.2 Usage

Event cue points are primarily created by the Kaltura media server during live broadcasts — the server automatically inserts BROADCAST_START and BROADCAST_END markers as the stream goes live and stops. The `eventType` field requires server-level permissions to set.

List event cue points on a live entry to detect broadcast boundaries:

```bash
curl -X POST "$KALTURA_SERVICE_URL/service/cuepoint_cuepoint/action/list" \
  -d "ks=$KALTURA_KS" \
  -d "format=1" \
  -d "filter[entryIdEqual]=1_live_entry" \
  -d "filter[cuePointTypeEqual]=eventCuePoint.Event"
```

Event cue points are not clonable and do not support bulk XML import.


# 5. Session Cue Points

Mark session boundaries within recordings — breakout rooms, meeting segments, speaker transitions.

**objectType:** `KalturaSessionCuePoint`

## 5.1 Fields (in addition to base)

| Field | Type | Description |
|-------|------|-------------|
| `name` | string | Session name/title |
| `endTime` | int | End time in milliseconds |
| `duration` | int | Computed duration (readonly) |
| `sessionOwner` | string | Owner of the session |

## 5.2 Create a Session Cue Point

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


# 6. Player Integration

## 6.1 Dual-Screen Plugin

The `dualscreen` plugin responds to view-change code cue points during playback, switching layouts programmatically:

```javascript
plugins: {
  kalturaCuepoints: {},
  dualscreen: {
    layout: 'PIP',
    position: 'bottom-right',
    childSizePercentage: 30
  }
}
```

As playback reaches a code cue point tagged `change-view-mode`, the plugin switches to the layout specified in the `code` field (see table in section 3.3).

## 6.2 Custom Code Handling

For non-view-change code cue points, listen to `TIMED_METADATA_CHANGE` events from the `kalturaCuepoints` plugin to trigger custom behavior when playback reaches a code cue point.


# 7. Searching

Code cue point descriptions and event/session names are indexed in eSearch. See [Cue Points Hub — eSearch Integration](KALTURA_CUE_POINTS_API.md) for query examples.


# 8. Error Handling

| Error | Cause | Fix |
|-------|-------|-----|
| `PROPERTY_VALIDATION_CANNOT_BE_NULL` | List without identifying filter | Include `entryIdEqual`, `entryIdIn`, `idEqual`, or `idIn` |
| `INVALID_CUE_POINT_ID` | Cue point not found or already deleted | Verify ID exists and status is not DELETED |
| `CUE_POINT_SYSTEM_NAME_EXISTS` | Duplicate `systemName` on the same entry | System names must be unique per entry |


# 9. Best Practices

- **Times are in milliseconds.** A cue point at 1 minute = `startTime=60000`.
- **Use `forceStop=1`** to pause the player at a cue point (works for all types, not just quizzes).
- **Tag view-change cue points with `change-view-mode`.** The dualscreen plugin only responds to this tag.
- **Event cue points are typically read-only.** They are auto-created by the media server during live broadcasts. Use them to detect broadcast boundaries, not to create artificial events.
- **Session cue points mark recording segments.** Use `sessionOwner` to track which speaker or host owns each segment.
- **`systemName` is unique per entry.** Use it as a stable identifier when you need to reference cue points by name instead of ID.


# 10. Related Guides

- [Cue Points Hub](KALTURA_CUE_POINTS_API.md) — Base cue point concepts, shared CRUD, eSearch integration, bulk operations
- [Player Embed Guide](KALTURA_PLAYER_EMBED_GUIDE.md) — Player v7 setup, dualscreen plugin configuration
- [Multi-Stream API](KALTURA_MULTI_STREAM_API.md) — Dual-screen entries with view-change layout control

# Kaltura Ad Cue Points API

Ad cue points define when and how advertisements play during video content.  
They support VAST and VPAID protocols for pre-roll, mid-roll, post-roll,  
and overlay ad insertion.

**Base URL:** `$KALTURA_SERVICE_URL` (e.g., `https://www.kaltura.com/api_v3`)  
**Auth:** KS via `ks` parameter (admin KS with `disableentitlement` for full access)  
**Format:** `format=1` for JSON responses  
**Service:** `cuepoint_cuepoint` (shared with all cue point types)  
**objectType:** `KalturaAdCuePoint`  
**Prerequisite:** [Cue Points Hub](KALTURA_CUE_POINTS_API.md) for base cue point concepts and shared CRUD


# 1. Ad Types

| Value | Name | Description |
|-------|------|-------------|
| 1 | VIDEO | Linear ad — pauses video content |
| 2 | OVERLAY | Non-linear ad — displays over video content |


# 2. Fields (in addition to base)

| Field | Type | Description |
|-------|------|-------------|
| `protocolType` | int | Ad protocol (insert-only, **immutable** after creation) |
| `sourceUrl` | string | URL to VAST/VPAID XML feed |
| `adType` | int | 1=VIDEO (linear), 2=OVERLAY (non-linear) |
| `title` | string | Ad title (max 250 chars) |
| `endTime` | int | End time in milliseconds |
| `duration` | int | Duration in milliseconds |


# 3. Protocol Types

| Value | Name | Description |
|-------|------|-------------|
| 0 | CUSTOM | Custom ad protocol |
| 1 | VAST | VAST 1.0 |
| 2 | VAST_2_0 | VAST 2.0 |
| 3 | VPAID | VPAID |


# 4. Ad Placement

| Placement | startTime | Description |
|-----------|-----------|-------------|
| Pre-roll | `0` | Plays before video content |
| Mid-roll | `N` (in ms) | Plays at position N in the video |
| Post-roll | `duration` | Plays after video content |
| Overlay | any | Non-linear overlay with `adType=2` and `startTime`/`endTime` defining the visible window |


# 5. Create a Mid-Roll Ad

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


# 6. Create an Overlay Ad

```bash
curl -X POST "$KALTURA_SERVICE_URL/service/cuepoint_cuepoint/action/add" \
  -d "ks=$KALTURA_KS" \
  -d "format=1" \
  -d "cuePoint[objectType]=KalturaAdCuePoint" \
  -d "cuePoint[entryId]=1_abc123" \
  -d "cuePoint[startTime]=30000" \
  -d "cuePoint[endTime]=45000" \
  -d "cuePoint[protocolType]=1" \
  -d "cuePoint[sourceUrl]=https://example.com/vast/overlay.xml" \
  -d "cuePoint[adType]=2" \
  -d "cuePoint[title]=Banner overlay"
```

Overlay ads use `adType=2` with both `startTime` and `endTime` to define the visible window.


# 7. Protocol Immutability

`protocolType` cannot be changed after creation — attempting to update it returns `PROPERTY_VALIDATION_NOT_UPDATABLE`. Plan the protocol type before creating ad cue points.


# 8. Player Ad Plugin Integration

The Player v7 `bumper` plugin handles ad playback based on ad cue points. Configure the player with the `kalturaCuepoints` core plugin to load ad cue point data:

```javascript
plugins: {
  kalturaCuepoints: {},
  bumper: {}
}
```

The bumper plugin reads ad cue points and triggers VAST/VPAID requests at the specified `startTime`.


# 9. Searching Ad Cue Points

Ad cue point titles are indexed in eSearch via `KalturaESearchCuePointItem` with `fieldName=name`. See [Cue Points Hub — eSearch Integration](KALTURA_CUE_POINTS_API.md) for query examples.


# 10. Error Handling

| Error | Cause | Fix |
|-------|-------|-----|
| `PROPERTY_VALIDATION_CANNOT_BE_NULL` | List without identifying filter | Include `entryIdEqual`, `entryIdIn`, `idEqual`, or `idIn` |
| `INVALID_CUE_POINT_ID` | Cue point not found or already deleted | Verify ID exists and status is not DELETED |
| `PROPERTY_VALIDATION_NOT_UPDATABLE` | Updating `protocolType` on ad cue point | `protocolType` is immutable after creation |


# 11. Best Practices

- **Times are in milliseconds.** A cue point at 2 minutes = `startTime=120000`.
- **Ad `protocolType` is set once.** Plan the protocol type before creating ad cue points — it cannot be changed.
- **Use `adType=1` for linear (video) ads** that pause content, `adType=2` for overlay (non-linear) ads.
- **Set `endTime` for overlay ads** to define the visible window. Linear ads play their full duration.
- **Use VAST 2.0 (protocolType=2)** for the most widely supported ad format.


# 12. Related Guides

- [Cue Points Hub](KALTURA_CUE_POINTS_API.md) — Base cue point concepts, shared CRUD, eSearch integration, bulk operations
- [Player Embed Guide](KALTURA_PLAYER_EMBED_GUIDE.md) — Player v7 setup, ad plugin configuration
- [Analytics Reports API](KALTURA_ANALYTICS_REPORTS_API.md) — Ad engagement analytics

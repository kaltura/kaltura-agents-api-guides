# Kaltura Annotations API

Annotations are text-based cue points that support hierarchical threading  
(parent-child relationships) and interactive hotspot overlays.  
Use annotations for timestamped comments, notes, and clickable regions on video.

**Base URL:** `$KALTURA_SERVICE_URL` (e.g., `https://www.kaltura.com/api_v3`)  
**Auth:** KS via `ks` parameter (admin KS with `disableentitlement` for full access)  
**Format:** `format=1` for JSON responses  
**Service:** `cuepoint_cuepoint` (shared with all cue point types)  
**objectType:** `KalturaAnnotation`  
**Prerequisite:** [Cue Points Hub](KALTURA_CUE_POINTS_API.md) for base cue point concepts and shared CRUD

<!-- Sections: 1.When to Use Annotations | 2.Prerequisites | 3.Fields (in addition to base) | 4.Create an Annotation | 5.Threaded Annotations | 6.Hotspot Pattern | 7.searchableOnEntry Flag | 8.Annotation Service Note | 9.Player Integration | 10.Searching Annotations | 11.Error Handling | 12.Best Practices | 13.Related Guides -->


# 1. When to Use Annotations

- **Timestamped notes** — Mark moments in a video with text commentary
- **Threaded discussions** — Build comment threads anchored to specific video times (e.g., in-video discussions where team members reply to each other's observations)
- **Peer review workflows** — Reviewers annotate specific moments with feedback, authors reply in threaded context, and all comments remain anchored to precise timestamps for iterative review cycles
- **Interactive hotspots** — Clickable regions on the video frame (via the `hotspots` tag)
- **Content tagging** — Mark segments for review, approval, or searchability
- **In-video collaboration** — Multiple participants annotate the same video for training reviews, content QA, or editorial feedback with full threading support


# 2. Prerequisites

- **Kaltura account** with cue point services enabled
- **Admin KS** with `disableentitlement` privilege for full annotation management across all entries
- **Entry ID** — annotations attach to an existing media entry (the entry must exist before creating annotations)
- **Cue Points Hub familiarity** — base cue point concepts (CRUD, filtering, status lifecycle) are covered in [Cue Points Hub](KALTURA_CUE_POINTS_API.md)

Generate a KS with the required privileges:

```bash
curl -X POST "$KALTURA_SERVICE_URL/service/session/action/start" \
  -d "format=1" \
  -d "secret=$KALTURA_ADMIN_SECRET" \
  -d "type=2" \
  -d "partnerId=$KALTURA_PARTNER_ID" \
  -d "privileges=disableentitlement"
```

For user-scoped annotations (e.g., per-viewer notes), use a USER KS (type=0) with the `userId` set — annotations created with a USER KS are owned by that user.


# 3. Fields (in addition to base)

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


# 4. Create an Annotation

```bash
curl -X POST "$KALTURA_SERVICE_URL/service/cuepoint_cuepoint/action/add" \
  -d "ks=$KALTURA_KS" \
  -d "format=1" \
  -d "cuePoint[objectType]=KalturaAnnotation" \
  -d "cuePoint[entryId]=$KALTURA_ENTRY_ID" \
  -d "cuePoint[startTime]=45000" \
  -d "cuePoint[endTime]=60000" \
  -d "cuePoint[text]=Key concept: dependency injection" \
  -d "cuePoint[isPublic]=1" \
  -d "cuePoint[searchableOnEntry]=1"
```


# 5. Threaded Annotations

Create child annotations by setting `parentId`:

```bash
curl -X POST "$KALTURA_SERVICE_URL/service/cuepoint_cuepoint/action/add" \
  -d "ks=$KALTURA_KS" \
  -d "format=1" \
  -d "cuePoint[objectType]=KalturaAnnotation" \
  -d "cuePoint[entryId]=$KALTURA_ENTRY_ID" \
  -d "cuePoint[parentId]=$PARENT_CUE_POINT_ID" \
  -d "cuePoint[startTime]=45000" \
  -d "cuePoint[text]=Reply: great explanation of DI patterns"
```

The parent must exist on the same entry. The `depth`, `childrenCount`, and `directChildrenCount` fields update automatically on both the parent and the new child.


# 6. Hotspot Pattern

Interactive video hotspots are annotation cue points with the `hotspots` tag. Creating hotspot-tagged annotations requires edit entitlement on the entry:

```bash
curl -X POST "$KALTURA_SERVICE_URL/service/cuepoint_cuepoint/action/add" \
  -d "ks=$KALTURA_KS" \
  -d "format=1" \
  -d "cuePoint[objectType]=KalturaAnnotation" \
  -d "cuePoint[entryId]=$KALTURA_ENTRY_ID" \
  -d "cuePoint[startTime]=10000" \
  -d "cuePoint[endTime]=20000" \
  -d "cuePoint[text]=Click here for details" \
  -d "cuePoint[tags]=hotspots"
```

Hotspot behavior (jump, pause, URL) and position data are stored in `partnerData` as structured JSON:

```bash
  -d "cuePoint[partnerData]={\"x\":10,\"y\":20,\"width\":30,\"height\":25}"
```

The Player v7 `navigation` plugin renders hotspots as timeline markers and displays them in the side panel.


# 7. searchableOnEntry Flag

Set `searchableOnEntry=1` to make the annotation text searchable at the entry level in eSearch. Without this flag, the annotation text is only findable via cue-point-specific search queries.


# 8. Annotation Service Note

The legacy `annotation_annotation` service exists but several actions are restricted (`count`, `updateStatus`, `updateCuePointsTimes`, `clone` return SERVICE_FORBIDDEN). Use the `cuepoint_cuepoint` service for all annotation operations.

**Index delay:** Newly created annotations may take a few seconds to appear in `entryIdEqual` list queries due to search indexing. Retrieval by `idEqual` or `idIn` is immediate.


# 9. Player Integration

The `navigation` plugin displays annotations in the side panel and renders hotspots as timeline markers:

```javascript
plugins: {
  kalturaCuepoints: {},
  navigation: {
    expandOnFirstPlay: true,
    itemsOrder: { Hotspot: 1, Chapter: 2, Caption: 3 }
  }
}
```

Only annotation types listed in `itemsOrder` are shown. Hotspot annotations appear when `Hotspot` is included.


# 10. Searching Annotations

Annotation text is indexed in eSearch via `KalturaESearchCuePointItem` with `fieldName=text`. See [Cue Points Hub — eSearch Integration](KALTURA_CUE_POINTS_API.md) for query examples.


# 11. Error Handling

| Error | Cause | Fix |
|-------|-------|-----|
| `PROPERTY_VALIDATION_CANNOT_BE_NULL` | List without identifying filter | Include `entryIdEqual`, `entryIdIn`, `idEqual`, or `idIn` |
| `INVALID_CUE_POINT_ID` | Cue point not found or already deleted | Verify ID exists and status is not DELETED |
| `PARENT_CUE_POINT_NOT_FOUND` | Invalid `parentId` | Parent must exist on the same entry |


# 12. Best Practices

- **Times are in milliseconds.** A cue point at 1 minute 30 seconds = `startTime=90000`.
- **Use `cuepoint_cuepoint` service** for all operations. The `annotation_annotation` service is deprecated and has restricted actions.
- **Set `searchableOnEntry=1`** for annotations that should be discoverable at the entry level in search.
- **Use `isPublic=1`** for viewer-visible annotations. Set to 0 for internal/editorial annotations.
- **eSearch indexing has a delay.** Newly created annotations may take seconds to appear in search results. Use `cuePoint.list` with `idEqual` for immediate retrieval.
- **Hotspot position data goes in `partnerData`.** Use structured JSON for x, y, width, height coordinates.


# 13. Related Guides

- **[Cue Points Hub](KALTURA_CUE_POINTS_API.md)** — Base cue point concepts, shared CRUD, eSearch integration, bulk operations
- **[Player Embed Guide](KALTURA_PLAYER_EMBED_GUIDE.md)** — Player v7 setup, navigation plugin configuration
- **[Custom Metadata API](KALTURA_CUSTOM_METADATA_API.md)** — Attaching structured metadata to cue points

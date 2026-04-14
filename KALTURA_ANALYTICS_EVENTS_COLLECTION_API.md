# Kaltura Analytics Events Collection API

Report playback and engagement events back to Kaltura's analytics system. The standard Kaltura Player v7 handles event collection automatically via its built-in analytics plugin — this guide is for custom players, server-side tracking, and application-level instrumentation.

**Base URL:** `https://www.kaltura.com/api_v3` (stats.collect), analytics server (trackEvent)  
**Auth:** KS passed as `ks` parameter in POST form data  
**Format:** Form-encoded POST, `format=1` for JSON responses  

**Services covered:**  

| Service | Description |
|---------|-------------|
| `stats.collect` | Server-side event collection (API v3) |
| `analytics.trackEvent` | Application-level event tracking (separate analytics server) |
| Player Analytics Plugin | Built-in event reporting in Kaltura Player v7 (reference implementation) |


# 1. Authentication

Event collection endpoints accept a KS for user attribution. Include `userId` in the KS to tie events to a specific user. Use the `appId` KS privilege for per-application segmentation.

```bash
# Set up environment
export KALTURA_SERVICE_URL="https://www.kaltura.com/api_v3"
export KALTURA_KS="your_kaltura_session"
export KALTURA_PARTNER_ID="your_partner_id"
```

For `analytics.trackEvent`, the analytics server has a separate base URL:

```bash
export KALTURA_ANALYTICS_URL="https://analytics.kaltura.com"
```

Generate a KS with `userId` via `session.start` (see [Session Guide](KALTURA_SESSION_GUIDE.md)):

```bash
# KS with user attribution
curl -X POST "$KALTURA_SERVICE_URL/service/session/action/start" \
  -d "secret=$KALTURA_ADMIN_SECRET" \
  -d "format=1" \
  -d "type=0" \
  -d "partnerId=$KALTURA_PARTNER_ID" \
  -d "userId=viewer@example.com" \
  -d "privileges=appId:my-custom-player"
```

The `appId:<name>` privilege tags all analytics from this session under a named application, enabling per-application analytics segmentation.


# 2. Player Event Types

The Kaltura Player v7 fires approximately 45 event types that feed the analytics system. Custom player implementations should report these events to achieve parity with the built-in player.

## 2.1 Core Playback Events

| Event Type | Description | When to Fire |
|------------|-------------|--------------|
| `WIDGET_LOADED` | Player widget initialized | Player DOM is ready |
| `MEDIA_LOADED` | Media metadata loaded | Source URL resolved and metadata available |
| `PLAY_REQUEST` | User initiated playback | Play button clicked or autoplay triggered |
| `PLAY` | Playback started | Media begins playing |
| `FIRST_PLAY` | First play in session | First play event in this player session |
| `PAUSE` | Playback paused | User paused or programmatic pause |
| `SEEK` | User seeked | Seek operation completed |
| `REPLAY` | User replayed | Playback restarted from beginning |

## 2.2 Progress Events (Quartiles)

| Event Type | Description | When to Fire |
|------------|-------------|--------------|
| `PLAY_REACHED_25` | 25% completion | Playhead passes 25% of duration |
| `PLAY_REACHED_50` | 50% completion | Playhead passes 50% of duration |
| `PLAY_REACHED_75` | 75% completion | Playhead passes 75% of duration |
| `PLAY_REACHED_100` | 100% completion | Playhead reaches end of content |

Fire quartile events only once per playback session. If the user seeks past a quartile point, fire the event when the playhead naturally reaches that position during forward playback.

## 2.3 Quality Events

| Event Type | Description | When to Fire |
|------------|-------------|--------------|
| `BUFFER_START` | Buffering began | Playback stalled for buffering |
| `BUFFER_END` | Buffering ended | Playback resumed after buffer |
| `ERROR` | Playback error | Fatal or recoverable playback error |
| `SOURCE_SELECTED` | Source chosen | Adaptive bitrate source selected |
| `FLAVOR_SWITCH` | Quality changed | Bitrate/quality level switched |

## 2.4 Engagement Events

| Event Type | Description | When to Fire |
|------------|-------------|--------------|
| `CAPTIONS` | Captions toggled | User enabled/disabled captions |
| `RELATED_CLICKED` | Related content clicked | User clicked a related video |
| `SHARE_CLICKED` | Share button clicked | User opened share dialog |
| `DOWNLOAD_CLICKED` | Download clicked | User initiated download |


# 3. stats.collect

Server-side event collection via the standard API v3 endpoint. Use this for backend systems, kiosks, set-top boxes, digital signage, and any non-browser playback environment.

```bash
curl -X POST "$KALTURA_SERVICE_URL/service/stats/action/collect" \
  -d "ks=$KALTURA_KS" \
  -d "format=1" \
  -d "event[objectType]=KalturaStatsEvent" \
  -d "event[partnerId]=$KALTURA_PARTNER_ID" \
  -d "event[entryId]=$ENTRY_ID" \
  -d "event[eventType]=3" \
  -d "event[sessionId]=$SESSION_ID" \
  -d "event[eventTimestamp]=$(date +%s)"
```

## 3.1 Event Type IDs

| ID | Event | Description |
|----|-------|-------------|
| 1 | WIDGET_LOADED | Player widget initialized |
| 2 | MEDIA_LOADED | Media entry loaded |
| 3 | PLAY | Playback started |
| 4 | PLAY_REACHED_25 | 25% of content played |
| 5 | PLAY_REACHED_50 | 50% of content played |
| 6 | PLAY_REACHED_75 | 75% of content played |
| 7 | PLAY_REACHED_100 | 100% of content played |
| 8 | OPEN_EDIT | Edit dialog opened |
| 9 | OPEN_VIRAL | Share dialog opened |
| 10 | OPEN_DOWNLOAD | Download dialog opened |
| 11 | OPEN_REPORT | Report dialog opened |
| 12 | BUFFER_START | Buffering started |
| 13 | BUFFER_END | Buffering ended |
| 14 | OPEN_FULL_SCREEN | Fullscreen activated |
| 15 | CLOSE_FULL_SCREEN | Fullscreen deactivated |
| 16 | REPLAY | Content replayed |
| 17 | SEEK | User seeked |
| 18 | OPEN_UPLOAD | Upload dialog opened |
| 19 | SAVE_PUBLISH | Publish action completed |
| 20 | CLOSE_EDITOR | Editor closed |
| 21 | PRE_BUMPER_PLAYED | Pre-roll bumper played |
| 22 | POST_BUMPER_PLAYED | Post-roll bumper played |
| 23 | BUMPER_CLICKED | Bumper ad clicked |
| 24 | PREROLL_STARTED | Pre-roll ad started |
| 25 | MIDROLL_STARTED | Mid-roll ad started |
| 26 | POSTROLL_STARTED | Post-roll ad started |
| 27 | OVERLAY_STARTED | Overlay ad started |
| 28 | PREROLL_CLICKED | Pre-roll ad clicked |
| 29 | MIDROLL_CLICKED | Mid-roll ad clicked |
| 30 | POSTROLL_CLICKED | Post-roll ad clicked |
| 31 | OVERLAY_CLICKED | Overlay ad clicked |
| 32 | PREROLL_25 | Pre-roll ad 25% |
| 33 | PREROLL_50 | Pre-roll ad 50% |
| 34 | PREROLL_75 | Pre-roll ad 75% |
| 35 | MIDROLL_25 | Mid-roll ad 25% |
| 36 | MIDROLL_50 | Mid-roll ad 50% |
| 37 | MIDROLL_75 | Mid-roll ad 75% |
| 38 | POSTROLL_25 | Post-roll ad 25% |
| 39 | POSTROLL_50 | Post-roll ad 50% |
| 40 | POSTROLL_75 | Post-roll ad 75% |

## 3.2 Required Fields

| Field | Type | Description |
|-------|------|-------------|
| `event[partnerId]` | int | Your Kaltura partner ID |
| `event[entryId]` | string | The media entry ID being played |
| `event[eventType]` | int | Event type ID (see table above) |
| `event[sessionId]` | string | Analytics session identifier (unique per playback session) |
| `event[eventTimestamp]` | int | Unix timestamp in seconds |

## 3.3 Optional Fields

| Field | Type | Description |
|-------|------|-------------|
| `event[uiconfId]` | int | Player configuration ID |
| `event[clientVer]` | string | Client version string |
| `event[referrer]` | string | Page URL where playback occurred |
| `event[currentPoint]` | int | Current playback position in seconds |
| `event[duration]` | int | Total content duration in seconds |
| `event[seek]` | boolean | Whether user is seeking |

## 3.4 Reporting a Complete Playback Session

Fire events in lifecycle order for a complete session:

```bash
# Generate a unique session ID for this playback
SESSION_ID="analytics_$(date +%s)_$$"

# 1. Widget loaded
curl -s -X POST "$KALTURA_SERVICE_URL/service/stats/action/collect" \
  -d "ks=$KALTURA_KS" \
  -d "format=1" \
  -d "event[objectType]=KalturaStatsEvent" \
  -d "event[partnerId]=$KALTURA_PARTNER_ID" \
  -d "event[entryId]=$ENTRY_ID" \
  -d "event[eventType]=1" \
  -d "event[sessionId]=$SESSION_ID" \
  -d "event[eventTimestamp]=$(date +%s)"

# 2. Media loaded
curl -s -X POST "$KALTURA_SERVICE_URL/service/stats/action/collect" \
  -d "ks=$KALTURA_KS" \
  -d "format=1" \
  -d "event[objectType]=KalturaStatsEvent" \
  -d "event[partnerId]=$KALTURA_PARTNER_ID" \
  -d "event[entryId]=$ENTRY_ID" \
  -d "event[eventType]=2" \
  -d "event[sessionId]=$SESSION_ID" \
  -d "event[eventTimestamp]=$(date +%s)"

# 3. Play
curl -s -X POST "$KALTURA_SERVICE_URL/service/stats/action/collect" \
  -d "ks=$KALTURA_KS" \
  -d "format=1" \
  -d "event[objectType]=KalturaStatsEvent" \
  -d "event[partnerId]=$KALTURA_PARTNER_ID" \
  -d "event[entryId]=$ENTRY_ID" \
  -d "event[eventType]=3" \
  -d "event[sessionId]=$SESSION_ID" \
  -d "event[eventTimestamp]=$(date +%s)"

# 4. Quartiles (25%, 50%, 75%, 100%)
for EVENT_TYPE in 4 5 6 7; do
  curl -s -X POST "$KALTURA_SERVICE_URL/service/stats/action/collect" \
    -d "ks=$KALTURA_KS" \
  -d "format=1" \
    -d "event[objectType]=KalturaStatsEvent" \
    -d "event[partnerId]=$KALTURA_PARTNER_ID" \
    -d "event[entryId]=$ENTRY_ID" \
    -d "event[eventType]=$EVENT_TYPE" \
    -d "event[sessionId]=$SESSION_ID" \
    -d "event[eventTimestamp]=$(date +%s)"
done
```


# 4. analytics.trackEvent

Application-level event tracking for page loads, button clicks, and custom interactions. Uses a separate analytics server endpoint.

**Required Parameters**

| Parameter | Type | Required | Description |
|---|---|---|---|
| `eventType` | int | Yes | Event type ID: `10002` (ButtonClicked) or `10003` (PageLoad) |
| `partnerId` | int | Yes | Your Kaltura partner ID |
| `entryId` | string | No | Kaltura entry ID to associate the event with (recommended for content-scoped tracking) |
| `kalturaApplication` | string | No | Application identifier for per-app segmentation (e.g., `"events-portal"`, `"mobile-app"`) |

```bash
curl -X POST "$KALTURA_ANALYTICS_URL/api_v3/index.php?service=analytics&action=trackEvent" \
  -d "ks=$KALTURA_KS" \
  -d "format=1" \
  -d "eventType=10003" \
  -d "partnerId=$KALTURA_PARTNER_ID" \
  -d "entryId=$ENTRY_ID" \
  -d "kalturaApplication=my-portal"
```

## 4.1 Event Types

| Type ID | Name | Description |
|---------|------|-------------|
| 10002 | ButtonClicked | User clicked a UI element |
| 10003 | PageLoad | Page or view was loaded |

## 4.2 Additional Fields

| Field | Description | Example |
|-------|-------------|---------|
| `kalturaApplication` | Application identifier for segmentation | `"events-portal"`, `"mobile-app"` |
| `pageType` | Page category | `"lobby"`, `"session"`, `"sponsor-booth"` |
| `pageName` | Specific page name | `"keynote-2025"` |
| `buttonType` | Button category | `"cta"`, `"download"`, `"share"` |
| `buttonName` | Specific button name | `"register-now"`, `"download-slides"` |

## 4.3 Tracking Page Loads and CTA Clicks

```bash
# Track portal page load
curl -X POST "$KALTURA_ANALYTICS_URL/api_v3/index.php?service=analytics&action=trackEvent" \
  -d "ks=$KALTURA_KS" \
  -d "format=1" \
  -d "eventType=10003" \
  -d "partnerId=$KALTURA_PARTNER_ID" \
  -d "entryId=$ENTRY_ID" \
  -d "kalturaApplication=events-portal" \
  -d "pageType=lobby" \
  -d "pageName=main-lobby"

# Track CTA button click
curl -X POST "$KALTURA_ANALYTICS_URL/api_v3/index.php?service=analytics&action=trackEvent" \
  -d "ks=$KALTURA_KS" \
  -d "format=1" \
  -d "eventType=10002" \
  -d "partnerId=$KALTURA_PARTNER_ID" \
  -d "entryId=$ENTRY_ID" \
  -d "kalturaApplication=events-portal" \
  -d "buttonType=cta" \
  -d "buttonName=register-now"
```


# 5. Event Reporting Protocol

## 5.1 Session Management

Each playback session requires a unique analytics session ID. The analytics session is separate from the Kaltura Session (KS):

- **KS** — Authentication token for API calls
- **Analytics session** — Unique identifier linking all events from one playback session

Generate a unique analytics session ID per player instance / playback session. Use a UUID or timestamp-based identifier.

## 5.2 Event Ordering

Fire events in the correct lifecycle order:

1. `WIDGET_LOADED` (player ready)
2. `MEDIA_LOADED` (media metadata available)
3. `PLAY` (playback begins)
4. `PLAY_REACHED_25` → `PLAY_REACHED_50` → `PLAY_REACHED_75` → `PLAY_REACHED_100` (as playback progresses)
5. `PAUSE`, `SEEK`, `BUFFER_START`/`BUFFER_END` (during playback as they occur)
6. `REPLAY` (if user replays)

## 5.3 Quartile Calculation

Calculate quartile events based on the actual content duration:

- Fire each quartile event only **once** per playback session
- Base quartile positions on total content duration (excluding ads)
- If the user seeks past a quartile position, do **not** retroactively fire the skipped quartile — fire it only during natural forward playback

## 5.4 Batching and Timing

- Fire events as they occur rather than batching — real-time analytics depend on timely delivery
- Include accurate `eventTimestamp` values (Unix seconds)
- If the client goes offline temporarily, queue events and send them in order when connectivity resumes


# 6. Server-Side Collection

For backend systems that play or process video without a browser.

## 6.1 Use Cases

- **Kiosks and digital signage** — Display terminals playing video content
- **Set-top boxes** — OTT/IPTV devices
- **Batch processing** — Server-side video processing that should count in analytics
- **Mobile backends** — Server-side proxy for mobile app analytics

## 6.2 Pattern

```bash
# 1. Generate a KS with userId for per-user attribution
KS=$(curl -s -X POST "$KALTURA_SERVICE_URL/service/session/action/start" \
  -d "secret=$KALTURA_ADMIN_SECRET" \
  -d "format=1" \
  -d "type=0" \
  -d "partnerId=$KALTURA_PARTNER_ID" \
  -d "userId=kiosk-001@example.com" | tr -d '"')

# 2. Report playback events via stats.collect
SESSION_ID="kiosk_$(date +%s)"

curl -s -X POST "$KALTURA_SERVICE_URL/service/stats/action/collect" \
  -d "ks=$KS" \
  -d "format=1" \
  -d "event[objectType]=KalturaStatsEvent" \
  -d "event[partnerId]=$KALTURA_PARTNER_ID" \
  -d "event[entryId]=$ENTRY_ID" \
  -d "event[eventType]=3" \
  -d "event[sessionId]=$SESSION_ID" \
  -d "event[eventTimestamp]=$(date +%s)" \
  -d "event[referrer]=kiosk://device-001"
```

Include device context in the `referrer` field for analytics segmentation.


# 7. Custom Event Context

## 7.1 Per-Application Segmentation via appId

Use the `appId` KS privilege to segment analytics by application:

```bash
# Generate KS with appId privilege
KS=$(curl -s -X POST "$KALTURA_SERVICE_URL/service/session/action/start" \
  -d "secret=$KALTURA_ADMIN_SECRET" \
  -d "format=1" \
  -d "type=0" \
  -d "partnerId=$KALTURA_PARTNER_ID" \
  -d "userId=viewer@example.com" \
  -d "privileges=appId:corporate-portal" | tr -d '"')

# All events sent with this KS are tagged under "corporate-portal"
curl -s -X POST "$KALTURA_SERVICE_URL/service/stats/action/collect" \
  -d "ks=$KS" \
  -d "format=1" \
  -d "event[objectType]=KalturaStatsEvent" \
  -d "event[partnerId]=$KALTURA_PARTNER_ID" \
  -d "event[entryId]=$ENTRY_ID" \
  -d "event[eventType]=3" \
  -d "event[sessionId]=$SESSION_ID" \
  -d "event[eventTimestamp]=$(date +%s)"
```

Pull per-application analytics via `report.getTable` with the same `appId`-scoped KS (see [Analytics Reports](KALTURA_ANALYTICS_REPORTS_API.md)).

## 7.2 Event Context Fields

| Field | Source | Description |
|-------|--------|-------------|
| `userId` | KS privilege | Ties events to a specific user |
| `appId` | KS privilege | Tags events to a named application |
| `referrer` | Event field | Page URL or device identifier |
| `clientVer` | Event field | Client application version |
| `uiconfId` | Event field | Player configuration ID |


# 8. Verification

Events have an analytics propagation delay before they appear in reports.

## 8.1 Propagation Delay

- **stats.collect** events: 10-30 minutes before appearing in `report.getTable`
- **analytics.trackEvent** events: 10-30 minutes for standard reports
- **Realtime report types** (`usersOverviewRealtime`, etc.): 20-90 seconds for live data

## 8.2 Verification Pattern

```bash
# 1. Send events
curl -s -X POST "$KALTURA_SERVICE_URL/service/stats/action/collect" \
  -d "ks=$KALTURA_KS" \
  -d "format=1" \
  -d "event[objectType]=KalturaStatsEvent" \
  -d "event[partnerId]=$KALTURA_PARTNER_ID" \
  -d "event[entryId]=$ENTRY_ID" \
  -d "event[eventType]=3" \
  -d "event[sessionId]=$SESSION_ID" \
  -d "event[eventTimestamp]=$(date +%s)"

# 2. Wait for propagation (for testing; production dashboards handle this automatically)
sleep 1800  # 30 minutes

# 3. Verify in reports
curl -X POST "$KALTURA_SERVICE_URL/service/report/action/getTable" \
  -d "ks=$KALTURA_KS" \
  -d "format=1" \
  -d "reportType=38" \
  -d "reportInputFilter[objectType]=KalturaEndUserReportInputFilter" \
  -d "reportInputFilter[fromDate]=$FROM_TIMESTAMP" \
  -d "reportInputFilter[toDate]=$TO_TIMESTAMP" \
  -d "reportInputFilter[entryIdIn]=$ENTRY_ID" \
  -d "pager[pageSize]=5" \
  -d "pager[pageIndex]=1" \
  -d "responseOptions[objectType]=KalturaReportResponseOptions" \
  -d "responseOptions[delimiter]=|"
```


# 9. Error Handling

## 9.1 stats.collect Errors

`stats.collect` is designed to be fire-and-forget. It returns a minimal response:

| Response | Meaning |
|----------|---------|
| Empty/null | Event accepted (standard behavior) |
| KalturaAPIException | Invalid KS, missing required fields |

## 9.2 analytics.trackEvent Errors

| HTTP Status | Cause | Resolution |
|-------------|-------|------------|
| 200 | Event accepted | No action needed |
| 400 | Missing required fields | Include `eventType`, `partnerId` |
| 401 | Invalid or expired KS | Generate a new KS |
| 404 | Wrong analytics server URL | Verify `$KALTURA_ANALYTICS_URL` |

## 9.3 Retry Logic

For transient failures (HTTP 500, network timeout):
- Retry up to 3 times with exponential backoff (1s, 2s, 4s)
- Queue events locally if the server is unreachable
- Send queued events in order when connectivity resumes
- Do not retry 400/401 errors (fix the request instead)


# 10. Common Integration Patterns

## 10.1 Custom Player Analytics Integration

Build a custom player that reports events back to Kaltura analytics.

```bash
# Initialize analytics session
SESSION_ID="custom_player_$(date +%s)_$$"

# Report lifecycle events in order
for EVENT in 1 2 3; do
  curl -s -X POST "$KALTURA_SERVICE_URL/service/stats/action/collect" \
    -d "ks=$KALTURA_KS" \
  -d "format=1" \
    -d "event[objectType]=KalturaStatsEvent" \
    -d "event[partnerId]=$KALTURA_PARTNER_ID" \
    -d "event[entryId]=$ENTRY_ID" \
    -d "event[eventType]=$EVENT" \
    -d "event[sessionId]=$SESSION_ID" \
    -d "event[eventTimestamp]=$(date +%s)" \
    -d "event[referrer]=https://my-app.example.com/player"
done

# Report quartiles as playback progresses
for QUARTILE in 4 5 6 7; do
  curl -s -X POST "$KALTURA_SERVICE_URL/service/stats/action/collect" \
    -d "ks=$KALTURA_KS" \
  -d "format=1" \
    -d "event[objectType]=KalturaStatsEvent" \
    -d "event[partnerId]=$KALTURA_PARTNER_ID" \
    -d "event[entryId]=$ENTRY_ID" \
    -d "event[eventType]=$QUARTILE" \
    -d "event[sessionId]=$SESSION_ID" \
    -d "event[eventTimestamp]=$(date +%s)"
done
```

## 10.2 Full Funnel Tracking (Page + Video)

Track the full user journey from portal visit through video playback.

```bash
# Page load — track portal landing
curl -s -X POST "$KALTURA_ANALYTICS_URL/api_v3/index.php?service=analytics&action=trackEvent" \
  -d "ks=$KALTURA_KS" \
  -d "format=1" \
  -d "eventType=10003" \
  -d "partnerId=$KALTURA_PARTNER_ID" \
  -d "entryId=$ENTRY_ID" \
  -d "kalturaApplication=events-portal" \
  -d "pageType=lobby"

# CTA click — user navigated to session page
curl -s -X POST "$KALTURA_ANALYTICS_URL/api_v3/index.php?service=analytics&action=trackEvent" \
  -d "ks=$KALTURA_KS" \
  -d "format=1" \
  -d "eventType=10002" \
  -d "partnerId=$KALTURA_PARTNER_ID" \
  -d "entryId=$ENTRY_ID" \
  -d "kalturaApplication=events-portal" \
  -d "buttonType=navigation" \
  -d "buttonName=view-session"

# Video playback — stats.collect handles play events
curl -s -X POST "$KALTURA_SERVICE_URL/service/stats/action/collect" \
  -d "ks=$KALTURA_KS" \
  -d "format=1" \
  -d "event[objectType]=KalturaStatsEvent" \
  -d "event[partnerId]=$KALTURA_PARTNER_ID" \
  -d "event[entryId]=$ENTRY_ID" \
  -d "event[eventType]=3" \
  -d "event[sessionId]=$SESSION_ID" \
  -d "event[eventTimestamp]=$(date +%s)"
```

## 10.3 Server-Side Playback Tracking

Backend systems report plays for unified analytics across all channels.

```bash
# Generate server-side KS with userId
KS=$(curl -s -X POST "$KALTURA_SERVICE_URL/service/session/action/start" \
  -d "secret=$KALTURA_ADMIN_SECRET" \
  -d "format=1" \
  -d "type=0" \
  -d "partnerId=$KALTURA_PARTNER_ID" \
  -d "userId=server-process@example.com" | tr -d '"')

# Report server-side playback
SESSION_ID="server_$(date +%s)"
for EVENT_TYPE in 1 2 3 4 5 6 7; do
  curl -s -X POST "$KALTURA_SERVICE_URL/service/stats/action/collect" \
    -d "ks=$KS" \
  -d "format=1" \
    -d "event[objectType]=KalturaStatsEvent" \
    -d "event[partnerId]=$KALTURA_PARTNER_ID" \
    -d "event[entryId]=$ENTRY_ID" \
    -d "event[eventType]=$EVENT_TYPE" \
    -d "event[sessionId]=$SESSION_ID" \
    -d "event[eventTimestamp]=$(date +%s)" \
    -d "event[referrer]=server://batch-process"
done
```

## 10.4 Per-Application Segmentation

Separate analytics for multiple applications on the same Kaltura account.

```bash
# Application A
KS_A=$(curl -s -X POST "$KALTURA_SERVICE_URL/service/session/action/start" \
  -d "secret=$KALTURA_ADMIN_SECRET" \
  -d "format=1" \
  -d "type=0" \
  -d "partnerId=$KALTURA_PARTNER_ID" \
  -d "userId=viewer@example.com" \
  -d "privileges=appId:corporate-portal" | tr -d '"')

# Application B
KS_B=$(curl -s -X POST "$KALTURA_SERVICE_URL/service/session/action/start" \
  -d "secret=$KALTURA_ADMIN_SECRET" \
  -d "format=1" \
  -d "type=0" \
  -d "partnerId=$KALTURA_PARTNER_ID" \
  -d "userId=viewer@example.com" \
  -d "privileges=appId:customer-education" | tr -d '"')

# Events from KS_A are tagged "corporate-portal"
# Events from KS_B are tagged "customer-education"
# Pull per-app analytics via report.getTable with the respective KS
```


# 11. Best Practices

**Event ordering matters.** Fire events in lifecycle order (WIDGET_LOADED → MEDIA_LOADED → PLAY → quartiles). Out-of-order events may cause incorrect analytics calculations (e.g., a PLAY event without a preceding WIDGET_LOADED).

**Fire quartiles once per session.** Each quartile event (25%, 50%, 75%, 100%) should fire exactly once per playback session. Seeking past a quartile does not count — only natural forward playback reaching that position should trigger the event.

**Use consistent session IDs.** All events in a single playback session must share the same `sessionId`. A new session ID is generated each time the user starts a new playback (including replays).

**Include userId for attribution.** Always include `userId` in the KS for per-user analytics. Without it, events are anonymous and cannot be correlated with user-level reports.

**Use appId for multi-app environments.** If you run multiple applications on one Kaltura account, use `appId:<name>` KS privileges to segment analytics per application. This enables separate dashboards and reports for each app.

**Kaltura Player v7 is the reference implementation.** The built-in Kaltura Player handles all event reporting automatically. When building a custom player, use the Player v7 analytics behavior as the reference for which events to fire and when. See [Player Embed Guide](KALTURA_PLAYER_EMBED_GUIDE.md).

**Gamification integration.** `viewPeriod` events (derived from playback events) feed the Gamification rules engine. Custom player events reported via `stats.collect` trigger leaderboard scoring, badge progress, and certificate tracking. See [Gamification Guide](KALTURA_GAMIFICATION_API.md).


# 12. Related Guides

- **[Player Embed](KALTURA_PLAYER_EMBED_GUIDE.md)** — Reference implementation — Player v7 fires ~45 event types automatically
- **[Analytics Reports](KALTURA_ANALYTICS_REPORTS_API.md)** — Pull the data that events collection feeds into
- **[Session Guide](KALTURA_SESSION_GUIDE.md)** — KS with `userId` and `appId` privileges for attribution
- **[AppTokens](KALTURA_APPTOKENS_API.md)** — Scoped tokens for client-side event reporting
- **[Gamification](KALTURA_GAMIFICATION_API.md)** — `viewPeriod` events from playback feed leaderboard and badge rules
- **[Events Platform](KALTURA_EVENTS_PLATFORM_API.md)** — Virtual event context for scoping events
- **[Analytics Reports: Cross-Guide Workflows](KALTURA_ANALYTICS_REPORTS_API.md)** — Full Event Lifecycle (section 13.15), Content Automation Pipeline (13.16), CRM Integration (13.17) — end-to-end orchestration patterns spanning all three analytics/gamification guides

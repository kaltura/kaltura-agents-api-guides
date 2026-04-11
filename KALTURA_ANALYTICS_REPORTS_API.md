# Kaltura Analytics Reports API

Pull analytics data out of Kaltura — content performance, viewer engagement, event attendance, and operational metrics. Multiple report surfaces exist (API v3 `report` service, Reports Microservice, live reports, stream health beacons) and this guide unifies them into a single reference.

**Services covered:**

| Service | Actions | Description |
|---------|---------|-------------|
| `report` | 7 actions | Historical analytics — tables, totals, graphs, CSV export |
| Reports Microservice | 2 endpoints | Async report generation for C&C, registration, enrichment |
| `liveReports` | `getEvents` | Real-time live stream analytics |
| `stats` | `collect` | Server-side statistics collection |
| `beacon` | `list` | Stream health diagnostics and encoder data |


# 1. Authentication

All `report` service calls use the standard API v3 pattern with a KS. Reports Microservice calls use Bearer token auth.

```bash
# Set up environment
export KALTURA_SERVICE_URL="https://www.kaltura.com/api_v3"
export KALTURA_REPORTS_URL="https://reports.nvp1.ovp.kaltura.com"
export KALTURA_KS="your_kaltura_session"
export KALTURA_PARTNER_ID="your_partner_id"
```

Generate an ADMIN KS (type=2) via `session.start` (see [Session Guide](KALTURA_SESSION_GUIDE.md)) or `appToken.startSession` (see [AppTokens Guide](KALTURA_APPTOKENS_API.md)).

Analytics access requires the `ANALYTICS_BASE` permission (ID 1085) on the KS role. See section 12 for the full permissions table.


# 2. Report Response Format

All `report` service responses use **pipe-delimited strings**, not JSON arrays.

## 2.1 Table Response

`report.getTable` returns:

| Field | Format | Description |
|-------|--------|-------------|
| `header` | Pipe-delimited | Column names: `"object_id\|entry_name\|count_plays\|sum_time_viewed"` |
| `data` | Semicolon-separated rows, pipe-delimited columns | `"1_abc123\|My Video\|150\|3600;1_def456\|Other Video\|75\|1800"` |
| `totalCount` | Integer | Total rows available (for pagination) |

Example response:

```json
{
  "header": "object_id|entry_name|count_plays|sum_time_viewed",
  "data": "1_abc123|My Video|150|3600;1_def456|Other Video|75|1800",
  "totalCount": 2,
  "objectType": "KalturaReportTable"
}
```

## 2.2 Totals Response

`report.getTotal` returns the same format as a table but with a single row (no semicolon separators).

## 2.3 Graphs Response

`report.getGraphs` returns an array of `KalturaReportGraph` objects:

```json
[
  {
    "id": "count_plays",
    "data": "2025-06-01|45;2025-06-02|62;2025-06-03|38",
    "objectType": "KalturaReportGraph"
  },
  {
    "id": "sum_time_viewed",
    "data": "2025-06-01|1200;2025-06-02|1850;2025-06-03|980",
    "objectType": "KalturaReportGraph"
  }
]
```

Each graph has an `id` (metric name) and `data` (semicolon-separated `label|value` pairs).

## 2.4 Parsing Pattern

To parse pipe-delimited report data into structured rows:

```bash
# Parse header into column names
IFS='|' read -ra COLUMNS <<< "$HEADER"

# Parse each row
IFS=';' read -ra ROWS <<< "$DATA"
for ROW in "${ROWS[@]}"; do
  IFS='|' read -ra FIELDS <<< "$ROW"
  echo "Entry: ${FIELDS[0]}, Plays: ${FIELDS[2]}"
done
```


# 3. report.getTable

Retrieves tabular analytics data with dimensions and metrics. Supports pagination.

```bash
curl -X POST "$KALTURA_SERVICE_URL/service/report/action/getTable" \
  -d "ks=$KALTURA_KS" \
  -d "format=1" \
  -d "reportType=38" \
  -d "reportInputFilter[objectType]=KalturaEndUserReportInputFilter" \
  -d "reportInputFilter[fromDate]=$FROM_TIMESTAMP" \
  -d "reportInputFilter[toDate]=$TO_TIMESTAMP" \
  -d "reportInputFilter[timeZoneOffset]=-240" \
  -d "reportInputFilter[interval]=days" \
  -d "order=-count_plays" \
  -d "pager[pageSize]=25" \
  -d "pager[pageIndex]=1" \
  -d "responseOptions[objectType]=KalturaReportResponseOptions" \
  -d "responseOptions[delimiter]=|" \
  -d "responseOptions[skipEmptyDates]=false"
```

**Required parameters:**

| Parameter | Description |
|-----------|-------------|
| `reportType` | KalturaReportType integer ID (see section 10) |
| `reportInputFilter[objectType]` | Always `KalturaEndUserReportInputFilter` |
| `reportInputFilter[fromDate]` | Start date as Unix timestamp in **seconds** |
| `reportInputFilter[toDate]` | End date as Unix timestamp in **seconds** |

**Optional parameters:**

| Parameter | Default | Description |
|-----------|---------|-------------|
| `reportInputFilter[timeZoneOffset]` | 0 | Timezone offset in minutes |
| `reportInputFilter[interval]` | `days` | Granularity: `days`, `months`, `hours`, `tenSeconds`, `years` |
| `order` | varies | Sort field with direction prefix: `-count_plays`, `+date_id` |
| `pager[pageSize]` | 25 | Results per page (max 500) |
| `pager[pageIndex]` | 1 | Page number (1-based) |
| `responseOptions[delimiter]` | `,` | Field delimiter (use `|` for consistency) |
| `responseOptions[skipEmptyDates]` | false | Omit dates with zero values |

## 3.1 Filtering by Entry

```bash
curl -X POST "$KALTURA_SERVICE_URL/service/report/action/getTable" \
  -d "ks=$KALTURA_KS" \
  -d "format=1" \
  -d "reportType=38" \
  -d "reportInputFilter[objectType]=KalturaEndUserReportInputFilter" \
  -d "reportInputFilter[fromDate]=$FROM_TIMESTAMP" \
  -d "reportInputFilter[toDate]=$TO_TIMESTAMP" \
  -d "reportInputFilter[entryIdIn]=$ENTRY_ID" \
  -d "pager[pageSize]=25" \
  -d "pager[pageIndex]=1" \
  -d "responseOptions[objectType]=KalturaReportResponseOptions" \
  -d "responseOptions[delimiter]=|"
```

## 3.2 Filtering by Category

```bash
curl -X POST "$KALTURA_SERVICE_URL/service/report/action/getTable" \
  -d "ks=$KALTURA_KS" \
  -d "format=1" \
  -d "reportType=38" \
  -d "reportInputFilter[objectType]=KalturaEndUserReportInputFilter" \
  -d "reportInputFilter[fromDate]=$FROM_TIMESTAMP" \
  -d "reportInputFilter[toDate]=$TO_TIMESTAMP" \
  -d "reportInputFilter[categoriesIdsIn]=$CATEGORY_ID" \
  -d "pager[pageSize]=25" \
  -d "pager[pageIndex]=1" \
  -d "responseOptions[objectType]=KalturaReportResponseOptions" \
  -d "responseOptions[delimiter]=|"
```

Multiple values within a filter are **pipe-separated** (e.g., `entryIdIn=1_abc123|1_def456`).

## 3.3 Filtering by Virtual Event

```bash
curl -X POST "$KALTURA_SERVICE_URL/service/report/action/getTable" \
  -d "ks=$KALTURA_KS" \
  -d "format=1" \
  -d "reportType=38" \
  -d "reportInputFilter[objectType]=KalturaEndUserReportInputFilter" \
  -d "reportInputFilter[fromDate]=$FROM_TIMESTAMP" \
  -d "reportInputFilter[toDate]=$TO_TIMESTAMP" \
  -d "reportInputFilter[virtualEventIdIn]=$VIRTUAL_EVENT_ID" \
  -d "pager[pageSize]=25" \
  -d "pager[pageIndex]=1" \
  -d "responseOptions[objectType]=KalturaReportResponseOptions" \
  -d "responseOptions[delimiter]=|"
```


# 4. report.getTotal

Retrieves aggregate totals for a report type as a single row.

```bash
curl -X POST "$KALTURA_SERVICE_URL/service/report/action/getTotal" \
  -d "ks=$KALTURA_KS" \
  -d "format=1" \
  -d "reportType=38" \
  -d "reportInputFilter[objectType]=KalturaEndUserReportInputFilter" \
  -d "reportInputFilter[fromDate]=$FROM_TIMESTAMP" \
  -d "reportInputFilter[toDate]=$TO_TIMESTAMP" \
  -d "responseOptions[objectType]=KalturaReportResponseOptions" \
  -d "responseOptions[delimiter]=|"
```

Response:

```json
{
  "header": "count_plays|unique_known_users|sum_time_viewed|avg_time_viewed",
  "data": "1250|340|45600|36.5",
  "objectType": "KalturaReportTotal"
}
```


# 5. report.getGraphs

Retrieves time-series data for charting. Returns an array of `KalturaReportGraph` objects, one per metric.

```bash
curl -X POST "$KALTURA_SERVICE_URL/service/report/action/getGraphs" \
  -d "ks=$KALTURA_KS" \
  -d "format=1" \
  -d "reportType=38" \
  -d "reportInputFilter[objectType]=KalturaEndUserReportInputFilter" \
  -d "reportInputFilter[fromDate]=$FROM_TIMESTAMP" \
  -d "reportInputFilter[toDate]=$TO_TIMESTAMP" \
  -d "reportInputFilter[interval]=days" \
  -d "responseOptions[objectType]=KalturaReportResponseOptions" \
  -d "responseOptions[delimiter]=|"
```

Use `interval=hours` for intraday granularity, `interval=months` for long-term trends, and `interval=tenSeconds` for live/realtime views.


# 6. Multi-Request Batching

A single analytics dashboard view typically combines `getTotal` + `getGraphs` + `getTable` in one HTTP call via `KalturaMultiRequest`. This reduces round trips from 3 to 1.

```bash
curl -X POST "$KALTURA_SERVICE_URL/service/multirequest" \
  -d "ks=$KALTURA_KS" \
  -d "format=1" \
  -d "1:service=report" \
  -d "1:action=getTotal" \
  -d "1:reportType=38" \
  -d "1:reportInputFilter[objectType]=KalturaEndUserReportInputFilter" \
  -d "1:reportInputFilter[fromDate]=$FROM_TIMESTAMP" \
  -d "1:reportInputFilter[toDate]=$TO_TIMESTAMP" \
  -d "1:responseOptions[objectType]=KalturaReportResponseOptions" \
  -d "1:responseOptions[delimiter]=|" \
  -d "2:service=report" \
  -d "2:action=getGraphs" \
  -d "2:reportType=38" \
  -d "2:reportInputFilter[objectType]=KalturaEndUserReportInputFilter" \
  -d "2:reportInputFilter[fromDate]=$FROM_TIMESTAMP" \
  -d "2:reportInputFilter[toDate]=$TO_TIMESTAMP" \
  -d "2:reportInputFilter[interval]=days" \
  -d "2:responseOptions[objectType]=KalturaReportResponseOptions" \
  -d "2:responseOptions[delimiter]=|" \
  -d "3:service=report" \
  -d "3:action=getTable" \
  -d "3:reportType=38" \
  -d "3:reportInputFilter[objectType]=KalturaEndUserReportInputFilter" \
  -d "3:reportInputFilter[fromDate]=$FROM_TIMESTAMP" \
  -d "3:reportInputFilter[toDate]=$TO_TIMESTAMP" \
  -d "3:order=-count_plays" \
  -d "3:pager[pageSize]=25" \
  -d "3:pager[pageIndex]=1" \
  -d "3:responseOptions[objectType]=KalturaReportResponseOptions" \
  -d "3:responseOptions[delimiter]=|"
```

Response is a JSON array with 3 elements: `[KalturaReportTotal, [KalturaReportGraph, ...], KalturaReportTable]`.


# 7. CSV Exports

## 7.1 report.getUrlForReportAsCsv

Generates a downloadable CSV export URL. The URL is valid for a limited time.

```bash
CSV_URL=$(curl -s -X POST "$KALTURA_SERVICE_URL/service/report/action/getUrlForReportAsCsv" \
  -d "ks=$KALTURA_KS" \
  -d "format=1" \
  -d "reportTitle=Content+Performance" \
  -d "reportText=Generated+report" \
  -d "headers=Entry+ID,Entry+Name,Plays,Minutes+Viewed" \
  -d "reportType=38" \
  -d "reportInputFilter[objectType]=KalturaEndUserReportInputFilter" \
  -d "reportInputFilter[fromDate]=$FROM_TIMESTAMP" \
  -d "reportInputFilter[toDate]=$TO_TIMESTAMP" \
  -d "responseOptions[objectType]=KalturaReportResponseOptions" \
  -d "responseOptions[delimiter]=|" | tr -d '"')

# Download the CSV
curl -o report.csv "$CSV_URL"
```

## 7.2 report.getCsvFromStringParams

For specialized reports (IDs 4021, 6000-6002, 3006-3008) that use semicolon-delimited parameters instead of the standard filter object.

### User Reactions Report (ID 4021)

Per-user engagement data for virtual events. Requires `virtualeventid:<EVENT_ID>` KS privilege.

```bash
curl -X POST "$KALTURA_SERVICE_URL/service/report/action/getCsvFromStringParams" \
  -d "ks=$KALTURA_KS" \
  -d "format=1" \
  -d "id=4021" \
  -d "params=from_date=$FROM;to_date=$TO;entry_ids=$ENTRY_ID;virtualeventid=$EVENT_ID"
```

**Columns returned:** `email`, `combined_live_engaged_users_play_time_ratio`, `download_attachment`, `add_to_calendar`, `raise_hand`, `mic_on`, `cam_on`, `clap_clicked_count`, `heart_clicked_count`, `think_clicked_count`, `wow_clicked_count`, `smile_clicked_count`, `total_reactions_activity`, `answered_polls`, `messages_sent_group`, `qna_threads`

### KME Room Data (ID 6000), Attendee Data (ID 6001), Breakout Sessions (ID 6002)

```bash
# Room data
curl -X POST "$KALTURA_SERVICE_URL/service/report/action/getCsvFromStringParams" \
  -d "ks=$KALTURA_KS" \
  -d "format=1" \
  -d "id=6000" \
  -d "params=from_date=$FROM;to_date=$TO"

# Attendee data (id=6001), Breakout sessions (id=6002) — same pattern
```

Use the `excludedFields` parameter to optionally exclude columns and reduce payload size.

### Enriched Reports (IDs 3006, 3007, 3008)

Reports enriched with user metadata (first name, last name, company):

| ID | Name | Key Columns |
|----|------|-------------|
| 3006 | Added to Calendar | `entry_id`, `user_id`, `email`, `count_add_to_calendar_clicked`, `first_name`, `last_name`, `company` |
| 3007 | Session Viewership | `user_id`, `email`, `entry_id`, `entry_name`, `media_type`, `view_time`, `play`, `first_name`, `last_name`, `company` |
| 3008 | Attachment Clicked | `user_id`, `email`, `entry_id`, `attachment_id`, `attachment_title`, `download_attachment_clicked`, `first_name`, `last_name`, `company` |

```bash
curl -X POST "$KALTURA_SERVICE_URL/service/report/action/getCsvFromStringParams" \
  -d "ks=$KALTURA_KS" \
  -d "format=1" \
  -d "id=3007" \
  -d "params=from_date_id=$FROM_DATE;to_date_id=$TO_DATE;timezone_offset=-240"
```

Parameters are semicolon-delimited: `from_date_id`, `to_date_id`, `timezone_offset`.


# 8. Reports Microservice

A separate async service for generating CSV reports that require cross-service data aggregation (registration data, C&C engagement, enriched analytics).

**Base URL:** `https://reports.{region}.ovp.kaltura.com` (e.g., `reports.nvp1.ovp.kaltura.com` for US production)
**Auth:** `Authorization: Bearer <KS>`

## 8.1 Two-Step Generate/Serve Pattern

```bash
# Step 1: Generate — returns a sessionId
SESSION_ID=$(curl -s -X POST "$KALTURA_REPORTS_URL/api/v1/report/generate" \
  -H "Authorization: Bearer $KALTURA_KS" \
  -H "Content-Type: application/json" \
  -d '{
    "reportName": "registration",
    "reportParameters": {"appGuid": "'$APP_GUID'"}
  }' | jq -r '.sessionId')

echo "Session: $SESSION_ID"

# Step 2: Poll until ready
while true; do
  STATUS=$(curl -s -X POST "$KALTURA_REPORTS_URL/api/v1/report/serve" \
    -H "Authorization: Bearer $KALTURA_KS" \
    -H "Content-Type: application/json" \
    -d '{"sessionId": "'$SESSION_ID'", "statusOnly": true}' \
    | jq -r '.status')
  echo "Status: $STATUS"
  [ "$STATUS" = "completed" ] && break
  sleep 2
done

# Step 3: Download CSV
curl -s -X POST "$KALTURA_REPORTS_URL/api/v1/report/serve" \
  -H "Authorization: Bearer $KALTURA_KS" \
  -H "Content-Type: application/json" \
  -d '{"sessionId": "'$SESSION_ID'"}' > report.csv
```

## 8.2 Report Types

| Report Name | Key Parameters | Description |
|-------------|----------------|-------------|
| `registration` | `appGuid` | Registration data for an event |
| `attachment` | `entries_ids`, `virtual_event_ids`, `from_date_id`, `to_date_id` | Attachment download activity |
| `reportsEnrichment` | `taskType`, `params.from_date`, `params.to_date` | Enriched analytics data |

## 8.3 Chat & Collaboration (C&C) Reports

C&C reports require `virtualeventid:<virtualEventId>` in the KS privilege string.

| Report Name | Description |
|-------------|-------------|
| `pollsActivity` | Poll participation data per question |
| `chatUserActivity` | Per-user chat engagement metrics |
| `moderatorTranscripts` | Moderator-visible chat transcripts |
| `chatModeration` | Moderation actions log |
| `groupChatTranscripts` | Group chat transcripts |
| `privateTranscripts` | Private chat transcripts |

```bash
# Generate a C&C report
SESSION_ID=$(curl -s -X POST "$KALTURA_REPORTS_URL/api/v1/report/generate" \
  -H "Authorization: Bearer $KALTURA_KS" \
  -H "Content-Type: application/json" \
  -d '{
    "reportName": "pollsActivity",
    "reportParameters": {
      "entries_ids": ["'$ENTRY_ID'"],
      "virtual_event_ids": ["'$EVENT_ID'"],
      "from_date_id": "2025-09-15",
      "to_date_id": "2025-09-16"
    }
  }' | jq -r '.sessionId')
```

Date format for C&C reports: ISO 8601 with zero-padded days (e.g., `2025-09-15`).


# 9. Live Analytics

Real-time analytics for active live streams.

## 9.1 liveReports.getEvents

```bash
# Calculate time window: now - 110s to now - 20s (90-second window)
FROM_UNIX=$(($(date +%s) - 110))
TO_UNIX=$(($(date +%s) - 20))

curl -X POST "$KALTURA_SERVICE_URL/service/liveReports/action/getEvents" \
  -d "ks=$KALTURA_KS" \
  -d "format=1" \
  -d "reportType=ENTRY_TIME_LINE" \
  -d "filter[objectType]=KalturaLiveReportInputFilter" \
  -d "filter[entryIds]=$ENTRY_ID" \
  -d "filter[fromTime]=$FROM_UNIX" \
  -d "filter[toTime]=$TO_UNIX" \
  -d "filter[live]=1"
```

The 20-second offset accounts for data propagation delay. Use the 90-second window for reliable real-time viewer counts.

## 9.2 Stream Health via beacon.list

### Health Beacons (Alerts)

```bash
curl -X POST "$KALTURA_SERVICE_URL/service/beacon/action/list" \
  -d "ks=$KALTURA_KS" \
  -d "format=1" \
  -d "filter[objectType]=KalturaBeaconFilter" \
  -d "filter[eventTypeIn]=0_healthData,1_healthData" \
  -d "filter[indexTypeEqual]=log" \
  -d "filter[relatedObjectTypeIn]=4" \
  -d "filter[objectIdIn]=$ENTRY_ID" \
  -d "filter[orderBy]=-updatedAt"
```

### Diagnostics Beacons (Encoder Data)

```bash
curl -X POST "$KALTURA_SERVICE_URL/service/beacon/action/list" \
  -d "ks=$KALTURA_KS" \
  -d "format=1" \
  -d "filter[objectType]=KalturaBeaconFilter" \
  -d "filter[eventTypeIn]=0_staticData,0_dynamicData,1_staticData,1_dynamicData" \
  -d "filter[indexTypeEqual]=state" \
  -d "filter[relatedObjectTypeIn]=4" \
  -d "filter[objectIdIn]=$ENTRY_ID"
```

**Beacon event type prefixes:** `0_` = primary stream, `1_` = backup/secondary stream.

**Stream health severity levels:**

| Level | Name | Description |
|-------|------|-------------|
| 0 | Debug | Verbose diagnostic data |
| 1 | Info | Normal operational events |
| 2 | Warning | Potential issues requiring attention |
| 3 | Error | Stream quality degradation |
| 4 | Critical | Stream failure or severe degradation |

## 9.3 Recommended Polling Intervals

| Data Type | Interval | Endpoint |
|-----------|----------|----------|
| Stream status | 5 seconds | `entryServerNode.list` |
| Stream health alerts | 10 seconds | `beacon.list` (log index) |
| Stream diagnostics | 30 seconds | `beacon.list` (state index) |
| Live viewer analytics | 30 seconds | `liveReports.getEvents` |

## 9.4 Realtime Report Types

Use these report types with `report.getTable` / `report.getGraphs` for live dashboard panels:

| ID | Name | Description |
|----|------|-------------|
| `10005` | USERS_OVERVIEW_REALTIME | Current concurrent viewers and engagement |
| `10006` | QOS_OVERVIEW_REALTIME | Quality of Experience: buffer rate, bitrate, error rate |
| `10001` | MAP_OVERLAY_COUNTRY_REALTIME | Live geographic distribution by country |
| `10002` | MAP_OVERLAY_REGION_REALTIME | Live geographic distribution by region |
| `10003` | MAP_OVERLAY_CITY_REALTIME | Live geographic distribution by city |
| `10004` | PLATFORMS_REALTIME | Live device breakdown |
| `10008` | ENTRY_LEVEL_USERS_DISCOVERY_REALTIME | Per-entry live viewer counts |
| `10011` | PLAYBACK_TYPE_REALTIME | Live vs DVR vs VOD breakdown |
| `10007` | DISCOVERY_REALTIME | Real-time content discovery metrics |


# 10. Report Types Reference

The `reportType` parameter uses **integer IDs** (KalturaReportType enum). Pass the numeric ID in your API call (e.g., `reportType=38`).

## 10.1 VOD / Historical Reports

| ID | Name | Description |
|----|------|-------------|
| `1` | TOP_CONTENT | Top videos by plays |
| `2` | CONTENT_DROPOFF | Impressions-to-play and quartile drop-off analysis |
| `6` | TOP_SYNDICATION | Syndication domains and referrers |
| `13` | USER_TOP_CONTENT | Per-user engagement tables |
| `21` | PLATFORMS | Device overview |
| `22` | OPERATING_SYSTEM | Top operating systems |
| `23` | BROWSERS | Top browsers |
| `30` | MAP_OVERLAY_CITY | Geographic distribution by city |
| `32` | OPERATING_SYSTEM_FAMILIES | OS family breakdown |
| `33` | BROWSERS_FAMILIES | Browser family breakdown |
| `34` | USER_ENGAGEMENT_TIMELINE | Per-user engagement highlights and heatmaps |
| `35` | UNIQUE_USERS_PLAY | Unique viewer counts |
| `36` | MAP_OVERLAY_COUNTRY | Geographic distribution by country |
| `37` | MAP_OVERLAY_REGION | Geographic distribution by region |
| `38` | TOP_CONTENT_CREATOR | Top content by creator, category top content |
| `39` | TOP_CONTENT_CONTRIBUTORS | Top content contributors |
| `41` | TOP_SOURCES | Upload sources |
| `45` | PLAYER_RELATED_INTERACTIONS | Content interactions (shares, downloads) |
| `46` | PLAYBACK_RATE | Playback speed statistics |
| `52` | CATEGORY_HIGHLIGHTS | Category summary metrics |
| `60` | SELF_SERVE_USAGE | Self-serve usage overview |
| `201` | PARTNER_USAGE | Partner usage and bandwidth |

## 10.2 Webcast / Events Platform Reports

| ID | Name | Description |
|----|------|-------------|
| `40001` | HIGHLIGHTS_WEBCAST | Webcast highlights summary |
| `40004` | MAP_OVERLAY_COUNTRY_WEBCAST | Geographic distribution for webcasts |
| `40007` | PLATFORMS_WEBCAST | Devices for webcasts |
| `40008` | TOP_DOMAINS_WEBCAST | Domains for webcasts |
| `40009` | TOP_USERS_WEBCAST | Top webcast viewers |
| `40011` | ENGAGMENT_TIMELINE_WEBCAST | Webcast engagement timeline |
| `60001` | EP_WEBCAST_HIGHLIGHTS | Events Platform webcast highlights |
| `60010` | EP_WEBCAST_LIVE_USER_ENGAGEMENT | Combined VOD + live engagement |

## 10.3 VPaaS (Multi-Account) Variants

Every VOD report has a VPaaS counterpart with IDs in the 20000 range (e.g., `20001` = CONTENT_DROPOFF_VPAAS, `20005` = PLATFORMS_VPAAS, `20011` = UNIQUE_USERS_PLAY_VPAAS). Multi-account partners use the VPaaS variant to aggregate across child accounts.


# 11. Filter Fields Reference

The `KalturaEndUserReportInputFilter` supports these filter fields. Multiple values within a filter are **pipe-separated**.

| Filter | Type | Description |
|--------|------|-------------|
| `fromDate` | int | Start date as Unix timestamp (seconds) |
| `toDate` | int | End date as Unix timestamp (seconds) |
| `timeZoneOffset` | int | Timezone offset in minutes |
| `interval` | enum | `days`, `months`, `hours`, `tenSeconds` (live), `years` |
| `entryIdIn` | string | Filter by entry IDs (pipe-separated) |
| `categoriesIdsIn` | string | Filter by category IDs (pipe-separated) |
| `mediaTypeIn` | string | Filter by media types (pipe-separated) |
| `countryIn` | string | Filter by country codes (pipe-separated) |
| `regionIn` | string | Geographic region drill-down |
| `citiesIn` | string | Geographic city drill-down |
| `playbackTypeIn` | string | `live`, `dvr`, `vod` |
| `deviceIn` | string | Filter by device types |
| `browserFamilyIn` | string | Filter by browser family |
| `operatingSystemFamilyIn` | string | Filter by OS family |
| `ownerIdsIn` | string | Filter by content creator IDs |
| `userIds` | string | Filter by viewer user IDs |
| `domainIn` | string | Filter by syndication domains |
| `canonicalUrlIn` | string | Filter by canonical URLs |
| `virtualEventIdIn` | string | Scope to virtual event(s) |
| `searchInTags` | string | Filter by entry tags |
| `searchInAdminTags` | string | Filter by admin tags |
| `playbackContextIdsIn` | string | Filter by category context |


# 12. Error Handling & Permissions

## 12.1 Analytics Permissions

| Permission | ID | Description |
|------------|-----|-------------|
| `ANALYTICS_BASE` | 1085 | Gate for all analytics views |
| `FEATURE_NEW_ANALYTICS_TAB` | 1125 | New analytics dashboard |
| `FEATURE_LIVE_ANALYTICS_DASHBOARD` | 1128 | Live analytics dashboard access |
| `FEATURE_MULTI_ACCOUNT_ANALYTICS` | 1130 | Multi-account (VPaaS/VAR) analytics |
| `FEATURE_LIVE_STREAM` | 1104 | Required alongside ANALYTICS_BASE for live |
| `FEATURE_END_USER_REPORTS` | 1096 | End-user level reporting |

## 12.2 Common Errors

| Error Code | Cause | Resolution |
|------------|-------|------------|
| `INVALID_KS` | Expired or malformed session | Generate a new KS |
| `SERVICE_FORBIDDEN` | KS role lacks `ANALYTICS_BASE` | Assign analytics permissions to the role |
| `REPORT_NOT_FOUND` | Invalid `reportType` value | Use a valid integer ID from section 10 |
| `INVALID_PARAMS` | Missing required filter fields | Include `fromDate` and `toDate` at minimum |

## 12.3 Reports Microservice Errors

The Reports Microservice returns HTTP status codes. A `report/serve` call with `statusOnly: true` returns `{"status": "pending"}`, `{"status": "in_progress"}`, or `{"status": "completed"}`. If generation fails, the status response includes an error message.


# 13. Common Integration Patterns

## 13.1 Event ROI Dashboard

After a virtual conference, pull aggregate attendance, per-session breakdown, and engagement trends in a single multi-request call, then export per-attendee data for BI tools.

```bash
# Set date range for the event
FROM_TIMESTAMP=$(date -d "2025-06-01" +%s 2>/dev/null || date -j -f "%Y-%m-%d" "2025-06-01" +%s)
TO_TIMESTAMP=$(date -d "2025-06-03" +%s 2>/dev/null || date -j -f "%Y-%m-%d" "2025-06-03" +%s)

# Step 1: Multi-request for dashboard data (totals + graphs + table)
curl -X POST "$KALTURA_SERVICE_URL/service/multirequest" \
  -d "ks=$KALTURA_KS" \
  -d "format=1" \
  -d "1:service=report" \
  -d "1:action=getTotal" \
  -d "1:reportType=38" \
  -d "1:reportInputFilter[objectType]=KalturaEndUserReportInputFilter" \
  -d "1:reportInputFilter[fromDate]=$FROM_TIMESTAMP" \
  -d "1:reportInputFilter[toDate]=$TO_TIMESTAMP" \
  -d "1:reportInputFilter[virtualEventIdIn]=$VIRTUAL_EVENT_ID" \
  -d "1:responseOptions[objectType]=KalturaReportResponseOptions" \
  -d "1:responseOptions[delimiter]=|" \
  -d "2:service=report" \
  -d "2:action=getGraphs" \
  -d "2:reportType=38" \
  -d "2:reportInputFilter[objectType]=KalturaEndUserReportInputFilter" \
  -d "2:reportInputFilter[fromDate]=$FROM_TIMESTAMP" \
  -d "2:reportInputFilter[toDate]=$TO_TIMESTAMP" \
  -d "2:reportInputFilter[virtualEventIdIn]=$VIRTUAL_EVENT_ID" \
  -d "2:reportInputFilter[interval]=days" \
  -d "2:responseOptions[objectType]=KalturaReportResponseOptions" \
  -d "2:responseOptions[delimiter]=|" \
  -d "3:service=report" \
  -d "3:action=getTable" \
  -d "3:reportType=38" \
  -d "3:reportInputFilter[objectType]=KalturaEndUserReportInputFilter" \
  -d "3:reportInputFilter[fromDate]=$FROM_TIMESTAMP" \
  -d "3:reportInputFilter[toDate]=$TO_TIMESTAMP" \
  -d "3:reportInputFilter[virtualEventIdIn]=$VIRTUAL_EVENT_ID" \
  -d "3:order=-count_plays" \
  -d "3:pager[pageSize]=25" \
  -d "3:pager[pageIndex]=1" \
  -d "3:responseOptions[objectType]=KalturaReportResponseOptions" \
  -d "3:responseOptions[delimiter]=|"

# Step 2: Per-attendee engagement (User Reactions Report)
curl -X POST "$KALTURA_SERVICE_URL/service/report/action/getCsvFromStringParams" \
  -d "ks=$KALTURA_KS" \
  -d "format=1" \
  -d "id=4021" \
  -d "params=from_date=$FROM_TIMESTAMP;to_date=$TO_TIMESTAMP;virtualeventid=$VIRTUAL_EVENT_ID"

# Step 3: Export full dataset for BI tools
CSV_URL=$(curl -s -X POST "$KALTURA_SERVICE_URL/service/report/action/getUrlForReportAsCsv" \
  -d "ks=$KALTURA_KS" \
  -d "format=1" \
  -d "reportTitle=Event+ROI" \
  -d "reportText=Conference+Performance" \
  -d "headers=Entry,Name,Plays,Minutes" \
  -d "reportType=38" \
  -d "reportInputFilter[objectType]=KalturaEndUserReportInputFilter" \
  -d "reportInputFilter[fromDate]=$FROM_TIMESTAMP" \
  -d "reportInputFilter[toDate]=$TO_TIMESTAMP" \
  -d "reportInputFilter[virtualEventIdIn]=$VIRTUAL_EVENT_ID" \
  -d "responseOptions[objectType]=KalturaReportResponseOptions" \
  -d "responseOptions[delimiter]=|" | tr -d '"')
curl -o event_roi.csv "$CSV_URL"
```

## 13.2 Content Performance Optimization

Identify top-performing content and drop-off points to improve engagement.

```bash
# Top content by plays
curl -X POST "$KALTURA_SERVICE_URL/service/report/action/getTable" \
  -d "ks=$KALTURA_KS" \
  -d "format=1" \
  -d "reportType=38" \
  -d "reportInputFilter[objectType]=KalturaEndUserReportInputFilter" \
  -d "reportInputFilter[fromDate]=$FROM_TIMESTAMP" \
  -d "reportInputFilter[toDate]=$TO_TIMESTAMP" \
  -d "order=-count_plays" \
  -d "pager[pageSize]=50" \
  -d "pager[pageIndex]=1" \
  -d "responseOptions[objectType]=KalturaReportResponseOptions" \
  -d "responseOptions[delimiter]=|"

# Drop-off analysis — shows impression-to-play and quartile play-through rates
curl -X POST "$KALTURA_SERVICE_URL/service/report/action/getTable" \
  -d "ks=$KALTURA_KS" \
  -d "format=1" \
  -d "reportType=2" \
  -d "reportInputFilter[objectType]=KalturaEndUserReportInputFilter" \
  -d "reportInputFilter[fromDate]=$FROM_TIMESTAMP" \
  -d "reportInputFilter[toDate]=$TO_TIMESTAMP" \
  -d "reportInputFilter[entryIdIn]=$ENTRY_ID" \
  -d "pager[pageSize]=25" \
  -d "pager[pageIndex]=1" \
  -d "responseOptions[objectType]=KalturaReportResponseOptions" \
  -d "responseOptions[delimiter]=|"

# Per-user engagement heatmap (4-tier: not viewed / once / twice / 3+ times)
curl -X POST "$KALTURA_SERVICE_URL/service/report/action/getTable" \
  -d "ks=$KALTURA_KS" \
  -d "format=1" \
  -d "reportType=34" \
  -d "reportInputFilter[objectType]=KalturaEndUserReportInputFilter" \
  -d "reportInputFilter[fromDate]=$FROM_TIMESTAMP" \
  -d "reportInputFilter[toDate]=$TO_TIMESTAMP" \
  -d "reportInputFilter[entryIdIn]=$ENTRY_ID" \
  -d "pager[pageSize]=25" \
  -d "pager[pageIndex]=1" \
  -d "responseOptions[objectType]=KalturaReportResponseOptions" \
  -d "responseOptions[delimiter]=|"
```

## 13.3 Live Stream Operations Dashboard

During a live event, poll multiple endpoints at recommended intervals to monitor stream health, viewer counts, and quality metrics.

```bash
# Stream health alerts — poll every 10 seconds
curl -X POST "$KALTURA_SERVICE_URL/service/beacon/action/list" \
  -d "ks=$KALTURA_KS" \
  -d "format=1" \
  -d "filter[objectType]=KalturaBeaconFilter" \
  -d "filter[eventTypeIn]=0_healthData,1_healthData" \
  -d "filter[indexTypeEqual]=log" \
  -d "filter[relatedObjectTypeIn]=4" \
  -d "filter[objectIdIn]=$ENTRY_ID" \
  -d "filter[orderBy]=-updatedAt"

# Live viewer count — poll every 30 seconds
FROM_UNIX=$(($(date +%s) - 110))
TO_UNIX=$(($(date +%s) - 20))
curl -X POST "$KALTURA_SERVICE_URL/service/liveReports/action/getEvents" \
  -d "ks=$KALTURA_KS" \
  -d "format=1" \
  -d "reportType=ENTRY_TIME_LINE" \
  -d "filter[objectType]=KalturaLiveReportInputFilter" \
  -d "filter[entryIds]=$ENTRY_ID" \
  -d "filter[fromTime]=$FROM_UNIX" \
  -d "filter[toTime]=$TO_UNIX" \
  -d "filter[live]=1"

# Quality of Experience — concurrent with viewer poll
curl -X POST "$KALTURA_SERVICE_URL/service/report/action/getTable" \
  -d "ks=$KALTURA_KS" \
  -d "format=1" \
  -d "reportType=10006" \
  -d "reportInputFilter[objectType]=KalturaEndUserReportInputFilter" \
  -d "reportInputFilter[fromDate]=$FROM_UNIX" \
  -d "reportInputFilter[toDate]=$TO_UNIX" \
  -d "responseOptions[objectType]=KalturaReportResponseOptions" \
  -d "responseOptions[delimiter]=|"
```

If health beacon severity >= 3 (error/critical), alert the production team for backup stream activation.

## 13.4 Compliance Training Verification

Pull per-user engagement and completion data to generate audit-ready compliance records.

```bash
# Per-user engagement by category (training library)
curl -X POST "$KALTURA_SERVICE_URL/service/report/action/getTable" \
  -d "ks=$KALTURA_KS" \
  -d "format=1" \
  -d "reportType=13" \
  -d "reportInputFilter[objectType]=KalturaEndUserReportInputFilter" \
  -d "reportInputFilter[fromDate]=$FROM_TIMESTAMP" \
  -d "reportInputFilter[toDate]=$TO_TIMESTAMP" \
  -d "reportInputFilter[categoriesIdsIn]=$TRAINING_CATEGORY_ID" \
  -d "reportInputFilter[userIds]=$USER_ID" \
  -d "pager[pageSize]=100" \
  -d "pager[pageIndex]=1" \
  -d "responseOptions[objectType]=KalturaReportResponseOptions" \
  -d "responseOptions[delimiter]=|"

# Verify completion via drop-off report (confirm 100% quartile)
curl -X POST "$KALTURA_SERVICE_URL/service/report/action/getTable" \
  -d "ks=$KALTURA_KS" \
  -d "format=1" \
  -d "reportType=2" \
  -d "reportInputFilter[objectType]=KalturaEndUserReportInputFilter" \
  -d "reportInputFilter[fromDate]=$FROM_TIMESTAMP" \
  -d "reportInputFilter[toDate]=$TO_TIMESTAMP" \
  -d "reportInputFilter[entryIdIn]=$ENTRY_ID" \
  -d "pager[pageSize]=25" \
  -d "pager[pageIndex]=1" \
  -d "responseOptions[objectType]=KalturaReportResponseOptions" \
  -d "responseOptions[delimiter]=|"

# Enriched report with employee name, email, company
curl -X POST "$KALTURA_SERVICE_URL/service/report/action/getCsvFromStringParams" \
  -d "ks=$KALTURA_KS" \
  -d "format=1" \
  -d "id=3007" \
  -d "params=from_date_id=$FROM_DATE;to_date_id=$TO_DATE;timezone_offset=-240"
```

## 13.5 Per-User Event Engagement Report

Pull granular per-attendee engagement data for follow-up campaigns.

```bash
# Step 1: User Reactions Report (per-user polls, reactions, Q&A)
curl -X POST "$KALTURA_SERVICE_URL/service/report/action/getCsvFromStringParams" \
  -d "ks=$KALTURA_KS" \
  -d "format=1" \
  -d "id=4021" \
  -d "params=from_date=$FROM;to_date=$TO;entry_ids=$ENTRY_ID;virtualeventid=$EVENT_ID"

# Step 2: C&C reports via Reports Microservice
SESSION_ID=$(curl -s -X POST "$KALTURA_REPORTS_URL/api/v1/report/generate" \
  -H "Authorization: Bearer $KALTURA_KS" \
  -H "Content-Type: application/json" \
  -d '{
    "reportName": "pollsActivity",
    "reportParameters": {
      "entries_ids": ["'$ENTRY_ID'"],
      "virtual_event_ids": ["'$EVENT_ID'"],
      "from_date_id": "'$FROM_DATE'",
      "to_date_id": "'$TO_DATE'"
    }
  }' | jq -r '.sessionId')

# Poll and download
while true; do
  STATUS=$(curl -s -X POST "$KALTURA_REPORTS_URL/api/v1/report/serve" \
    -H "Authorization: Bearer $KALTURA_KS" \
    -H "Content-Type: application/json" \
    -d '{"sessionId": "'$SESSION_ID'", "statusOnly": true}' | jq -r '.status')
  [ "$STATUS" = "completed" ] && break
  sleep 2
done
curl -s -X POST "$KALTURA_REPORTS_URL/api/v1/report/serve" \
  -H "Authorization: Bearer $KALTURA_KS" \
  -H "Content-Type: application/json" \
  -d '{"sessionId": "'$SESSION_ID'"}' > polls_report.csv

# Step 3: Enriched session viewership with user metadata
curl -X POST "$KALTURA_SERVICE_URL/service/report/action/getCsvFromStringParams" \
  -d "ks=$KALTURA_KS" \
  -d "format=1" \
  -d "id=3007" \
  -d "params=from_date_id=$FROM_DATE;to_date_id=$TO_DATE;timezone_offset=-240"
```

## 13.6 Multi-Account Analytics (VPaaS)

VPaaS resellers use VPaaS report variants to aggregate analytics across sub-accounts.

```bash
# Per-account usage
curl -X POST "$KALTURA_SERVICE_URL/service/report/action/getTable" \
  -d "ks=$KALTURA_KS" \
  -d "format=1" \
  -d "reportType=60" \
  -d "reportInputFilter[objectType]=KalturaEndUserReportInputFilter" \
  -d "reportInputFilter[fromDate]=$FROM_TIMESTAMP" \
  -d "reportInputFilter[toDate]=$TO_TIMESTAMP" \
  -d "pager[pageSize]=100" \
  -d "pager[pageIndex]=1" \
  -d "responseOptions[objectType]=KalturaReportResponseOptions" \
  -d "responseOptions[delimiter]=|"

# Bandwidth and storage totals
curl -X POST "$KALTURA_SERVICE_URL/service/report/action/getTotal" \
  -d "ks=$KALTURA_KS" \
  -d "format=1" \
  -d "reportType=201" \
  -d "reportInputFilter[objectType]=KalturaEndUserReportInputFilter" \
  -d "reportInputFilter[fromDate]=$FROM_TIMESTAMP" \
  -d "reportInputFilter[toDate]=$TO_TIMESTAMP" \
  -d "responseOptions[objectType]=KalturaReportResponseOptions" \
  -d "responseOptions[delimiter]=|"
```

## 13.7 BI Pipeline / Data Warehouse Integration

Pull analytics data on a schedule, transform pipe-delimited responses, and load into a data warehouse.

```bash
# Pull multiple report types with rolling date window
YESTERDAY=$(($(date +%s) - 86400))
TODAY=$(date +%s)

# Engagement data
curl -s -X POST "$KALTURA_SERVICE_URL/service/report/action/getTable" \
  -d "ks=$KALTURA_KS" \
  -d "format=1" \
  -d "reportType=38" \
  -d "reportInputFilter[objectType]=KalturaEndUserReportInputFilter" \
  -d "reportInputFilter[fromDate]=$YESTERDAY" \
  -d "reportInputFilter[toDate]=$TODAY" \
  -d "pager[pageSize]=500" \
  -d "pager[pageIndex]=1" \
  -d "responseOptions[objectType]=KalturaReportResponseOptions" \
  -d "responseOptions[delimiter]=|"

# Geographic data
curl -s -X POST "$KALTURA_SERVICE_URL/service/report/action/getTable" \
  -d "ks=$KALTURA_KS" \
  -d "format=1" \
  -d "reportType=36" \
  -d "reportInputFilter[objectType]=KalturaEndUserReportInputFilter" \
  -d "reportInputFilter[fromDate]=$YESTERDAY" \
  -d "reportInputFilter[toDate]=$TODAY" \
  -d "pager[pageSize]=500" \
  -d "pager[pageIndex]=1" \
  -d "responseOptions[objectType]=KalturaReportResponseOptions" \
  -d "responseOptions[delimiter]=|"

# Bulk CSV export for warehouse ingestion
CSV_URL=$(curl -s -X POST "$KALTURA_SERVICE_URL/service/report/action/getUrlForReportAsCsv" \
  -d "ks=$KALTURA_KS" \
  -d "format=1" \
  -d "reportTitle=Daily+ETL" \
  -d "reportText=Automated+export" \
  -d "headers=Entry,Name,Plays,Minutes,Unique+Viewers" \
  -d "reportType=38" \
  -d "reportInputFilter[objectType]=KalturaEndUserReportInputFilter" \
  -d "reportInputFilter[fromDate]=$YESTERDAY" \
  -d "reportInputFilter[toDate]=$TODAY" \
  -d "responseOptions[objectType]=KalturaReportResponseOptions" \
  -d "responseOptions[delimiter]=|" | tr -d '"')
curl -o daily_export.csv "$CSV_URL"
```

## 13.8 Geographic Analytics

Drill down from country to region to city for geographic distribution analysis.

```bash
# Country level
curl -X POST "$KALTURA_SERVICE_URL/service/report/action/getTable" \
  -d "ks=$KALTURA_KS" \
  -d "format=1" \
  -d "reportType=36" \
  -d "reportInputFilter[objectType]=KalturaEndUserReportInputFilter" \
  -d "reportInputFilter[fromDate]=$FROM_TIMESTAMP" \
  -d "reportInputFilter[toDate]=$TO_TIMESTAMP" \
  -d "pager[pageSize]=50" \
  -d "pager[pageIndex]=1" \
  -d "responseOptions[objectType]=KalturaReportResponseOptions" \
  -d "responseOptions[delimiter]=|"

# Drill down to region within a country
curl -X POST "$KALTURA_SERVICE_URL/service/report/action/getTable" \
  -d "ks=$KALTURA_KS" \
  -d "format=1" \
  -d "reportType=37" \
  -d "reportInputFilter[objectType]=KalturaEndUserReportInputFilter" \
  -d "reportInputFilter[fromDate]=$FROM_TIMESTAMP" \
  -d "reportInputFilter[toDate]=$TO_TIMESTAMP" \
  -d "reportInputFilter[countryIn]=US" \
  -d "pager[pageSize]=50" \
  -d "pager[pageIndex]=1" \
  -d "responseOptions[objectType]=KalturaReportResponseOptions" \
  -d "responseOptions[delimiter]=|"
```

## 13.9 Device and Technology Analytics

Analyze viewer device, browser, and OS distributions.

```bash
# Device overview
curl -X POST "$KALTURA_SERVICE_URL/service/report/action/getTable" \
  -d "ks=$KALTURA_KS" \
  -d "format=1" \
  -d "reportType=21" \
  -d "reportInputFilter[objectType]=KalturaEndUserReportInputFilter" \
  -d "reportInputFilter[fromDate]=$FROM_TIMESTAMP" \
  -d "reportInputFilter[toDate]=$TO_TIMESTAMP" \
  -d "pager[pageSize]=25" \
  -d "pager[pageIndex]=1" \
  -d "responseOptions[objectType]=KalturaReportResponseOptions" \
  -d "responseOptions[delimiter]=|"

# Top browsers
curl -X POST "$KALTURA_SERVICE_URL/service/report/action/getTable" \
  -d "ks=$KALTURA_KS" \
  -d "format=1" \
  -d "reportType=33" \
  -d "reportInputFilter[objectType]=KalturaEndUserReportInputFilter" \
  -d "reportInputFilter[fromDate]=$FROM_TIMESTAMP" \
  -d "reportInputFilter[toDate]=$TO_TIMESTAMP" \
  -d "pager[pageSize]=25" \
  -d "pager[pageIndex]=1" \
  -d "responseOptions[objectType]=KalturaReportResponseOptions" \
  -d "responseOptions[delimiter]=|"
```

## 13.10 Accessibility Coverage Reporting

Universities and government agencies subject to WCAG 2.1 AA requirements need to audit their entire video library for caption coverage, prioritize uncaptioned content by viewership, and auto-queue captioning jobs. This workflow combines eSearch for discovery, `captionAsset.list` for per-entry detail, report-based prioritization, and REACH task submission.

```bash
# Step 1: Find entries that already have captions using eSearch
#   captionAssetItems with an exists condition returns only entries with at least one caption track
curl -X POST "$KALTURA_SERVICE_URL/service/eSearch/action/searchEntry" \
  -d "ks=$KALTURA_KS" \
  -d "format=1" \
  -d "searchParams[objectType]=KalturaESearchEntryParams" \
  -d "searchParams[searchOperator][objectType]=KalturaESearchEntryOperator" \
  -d "searchParams[searchOperator][operator]=1" \
  -d "searchParams[searchOperator][searchItems][0][objectType]=KalturaESearchCaptionItem" \
  -d "searchParams[searchOperator][searchItems][0][fieldName]=content" \
  -d "searchParams[searchOperator][searchItems][0][itemType]=3" \
  -d "pager[pageSize]=500" \
  -d "pager[pageIndex]=1"

# Step 2: List caption languages for a specific entry
curl -X POST "$KALTURA_SERVICE_URL/service/captionAsset/action/list" \
  -d "ks=$KALTURA_KS" \
  -d "format=1" \
  -d "filter[objectType]=KalturaAssetFilter" \
  -d "filter[entryIdEqual]=$ENTRY_ID"

# Step 3: Rank uncaptioned content by play count for prioritization
#   Use topContentCreator (reportType=38) filtered to the list of uncaptioned entry IDs
curl -X POST "$KALTURA_SERVICE_URL/service/report/action/getTable" \
  -d "ks=$KALTURA_KS" \
  -d "format=1" \
  -d "reportType=38" \
  -d "reportInputFilter[objectType]=KalturaEndUserReportInputFilter" \
  -d "reportInputFilter[fromDate]=$FROM_TIMESTAMP" \
  -d "reportInputFilter[toDate]=$TO_TIMESTAMP" \
  -d "reportInputFilter[entryIdIn]=$UNCAPTIONED_ENTRY_IDS" \
  -d "order=-count_plays" \
  -d "pager[pageSize]=100" \
  -d "pager[pageIndex]=1" \
  -d "responseOptions[objectType]=KalturaReportResponseOptions" \
  -d "responseOptions[delimiter]=|"
```

After ranking, submit the highest-traffic entries to REACH for automatic captioning (see [REACH Guide](KALTURA_REACH_API.md) section on `entryVendorTask.add`). Track caption completion through webhooks on `ENTRY_VENDOR_TASK_STATUS_CHANGED` events (see [Webhooks Guide](KALTURA_WEBHOOKS_API.md)), then re-run the eSearch query to update the coverage dashboard.

See also: [eSearch Guide](KALTURA_ESEARCH_API.md) for advanced search operators, [Metadata & Captions Guide](KALTURA_METADATA_AND_CAPTIONS_API.md) for caption management.

## 13.11 Lecture Capture & LMS Analytics

Universities track per-student engagement to identify struggling students before they fall behind. This workflow pulls individual student viewing data scoped to a course category, analyzes drop-off patterns for specific lectures, and exports enriched reports with student name and email for LMS gradebook sync.

```bash
# Step 1: Per-student engagement for a course category
#   userTopContent (reportType=13) filtered by course category and specific students
curl -X POST "$KALTURA_SERVICE_URL/service/report/action/getTable" \
  -d "ks=$KALTURA_KS" \
  -d "format=1" \
  -d "reportType=13" \
  -d "reportInputFilter[objectType]=KalturaEndUserReportInputFilter" \
  -d "reportInputFilter[fromDate]=$FROM_TIMESTAMP" \
  -d "reportInputFilter[toDate]=$TO_TIMESTAMP" \
  -d "reportInputFilter[categoriesIdsIn]=$COURSE_CATEGORY_ID" \
  -d "reportInputFilter[userIds]=$STUDENT_USER_IDS" \
  -d "order=-sum_time_viewed" \
  -d "pager[pageSize]=200" \
  -d "pager[pageIndex]=1" \
  -d "responseOptions[objectType]=KalturaReportResponseOptions" \
  -d "responseOptions[delimiter]=|"

# Step 2: Drop-off analysis for a specific lecture
#   contentDropoff (reportType=2) shows impression-to-play ratio and quartile play-through
curl -X POST "$KALTURA_SERVICE_URL/service/report/action/getTable" \
  -d "ks=$KALTURA_KS" \
  -d "format=1" \
  -d "reportType=2" \
  -d "reportInputFilter[objectType]=KalturaEndUserReportInputFilter" \
  -d "reportInputFilter[fromDate]=$FROM_TIMESTAMP" \
  -d "reportInputFilter[toDate]=$TO_TIMESTAMP" \
  -d "reportInputFilter[entryIdIn]=$LECTURE_ENTRY_ID" \
  -d "pager[pageSize]=25" \
  -d "pager[pageIndex]=1" \
  -d "responseOptions[objectType]=KalturaReportResponseOptions" \
  -d "responseOptions[delimiter]=|"

# Step 3: Enriched per-student report with name, email, company for LMS export
#   Report ID 3007 returns CSV with user metadata joined to engagement data
curl -X POST "$KALTURA_SERVICE_URL/service/report/action/getCsvFromStringParams" \
  -d "ks=$KALTURA_KS" \
  -d "format=1" \
  -d "id=3007" \
  -d "params=from_date_id=$FROM_DATE;to_date_id=$TO_DATE;cat_ids=$COURSE_CATEGORY_ID;timezone_offset=-240"
```

Students with low quartile completion on key lectures are candidates for early intervention. Parse the `count_plays_25` through `count_plays_100` columns from the drop-off report to identify where students disengage.

See also: [Player Embed Guide](KALTURA_PLAYER_EMBED_GUIDE.md) for embedded player analytics events, [Categories & Access Control Guide](KALTURA_CATEGORIES_AND_ACCESS_CONTROL_API.md) for course category setup.

## 13.12 Investor Relations Webcast Analytics

Public companies hosting earnings webcasts need segment-level engagement heatmaps for the IR team, geographic distribution for SEC Regulation FD compliance documentation, per-user engagement for investor follow-up, and bulk CSV exports for the board package.

```bash
# Step 1: Segment-level engagement heatmap
#   userEngagementTimeline (reportType=34) returns time-based engagement data
curl -X POST "$KALTURA_SERVICE_URL/service/report/action/getTable" \
  -d "ks=$KALTURA_KS" \
  -d "format=1" \
  -d "reportType=34" \
  -d "reportInputFilter[objectType]=KalturaEndUserReportInputFilter" \
  -d "reportInputFilter[fromDate]=$FROM_TIMESTAMP" \
  -d "reportInputFilter[toDate]=$TO_TIMESTAMP" \
  -d "reportInputFilter[entryIdIn]=$WEBCAST_ENTRY_ID" \
  -d "pager[pageSize]=100" \
  -d "pager[pageIndex]=1" \
  -d "responseOptions[objectType]=KalturaReportResponseOptions" \
  -d "responseOptions[delimiter]=|"

# Step 2: Geographic distribution for Regulation FD compliance
#   mapOverlayCountry (reportType=36) provides country-level viewer breakdown
curl -X POST "$KALTURA_SERVICE_URL/service/report/action/getTable" \
  -d "ks=$KALTURA_KS" \
  -d "format=1" \
  -d "reportType=36" \
  -d "reportInputFilter[objectType]=KalturaEndUserReportInputFilter" \
  -d "reportInputFilter[fromDate]=$FROM_TIMESTAMP" \
  -d "reportInputFilter[toDate]=$TO_TIMESTAMP" \
  -d "reportInputFilter[entryIdIn]=$WEBCAST_ENTRY_ID" \
  -d "pager[pageSize]=50" \
  -d "pager[pageIndex]=1" \
  -d "responseOptions[objectType]=KalturaReportResponseOptions" \
  -d "responseOptions[delimiter]=|"

# Step 3: Per-user engagement for investor follow-up
#   Report ID 4021 (User Reactions Report) provides per-attendee interaction data
curl -X POST "$KALTURA_SERVICE_URL/service/report/action/getCsvFromStringParams" \
  -d "ks=$KALTURA_KS" \
  -d "format=1" \
  -d "id=4021" \
  -d "params=from_date=$FROM_TIMESTAMP;to_date=$TO_TIMESTAMP;entry_ids=$WEBCAST_ENTRY_ID"

# Step 4: Bulk CSV export for the board package
CSV_URL=$(curl -s -X POST "$KALTURA_SERVICE_URL/service/report/action/getUrlForReportAsCsv" \
  -d "ks=$KALTURA_KS" \
  -d "format=1" \
  -d "reportTitle=Earnings+Webcast+Analytics" \
  -d "reportText=Q2+2025+Earnings+Call" \
  -d "headers=Entry,Name,Plays,Minutes,Unique+Viewers,Avg+Completion" \
  -d "reportType=38" \
  -d "reportInputFilter[objectType]=KalturaEndUserReportInputFilter" \
  -d "reportInputFilter[fromDate]=$FROM_TIMESTAMP" \
  -d "reportInputFilter[toDate]=$TO_TIMESTAMP" \
  -d "reportInputFilter[entryIdIn]=$WEBCAST_ENTRY_ID" \
  -d "responseOptions[objectType]=KalturaReportResponseOptions" \
  -d "responseOptions[delimiter]=|" | tr -d '"')
curl -o earnings_webcast_report.csv "$CSV_URL"
```

The geographic report demonstrates that the webcast was accessible globally, which supports Regulation FD fair-disclosure documentation. The segment heatmap reveals which portions of the earnings call drew peak engagement (e.g., Q&A segment vs. prepared remarks).

See also: [Events Platform Guide](KALTURA_EVENTS_PLATFORM_API.md) for webcast setup, [User Profile Guide](KALTURA_USER_PROFILE_API.md) for attendee registration data.

## 13.13 Thumbnail A/B Testing

Content teams optimize click-through rates by testing different thumbnail images. This workflow creates thumbnail variants from video frames, rotates the active thumbnail between test periods, and uses drop-off analytics to measure the impression-to-play conversion rate for each variant.

```bash
# Step 1: Create a thumbnail variant from a specific video frame
#   addFromEntry captures a frame at the specified offset (in seconds)
curl -X POST "$KALTURA_SERVICE_URL/service/thumbAsset/action/addFromEntry" \
  -d "ks=$KALTURA_KS" \
  -d "format=1" \
  -d "entryId=$ENTRY_ID" \
  -d "thumbAsset[objectType]=KalturaThumbAsset" \
  -d "thumbAsset[tags]=ab_test_variant_b" \
  -d "thumbOffset=45"

# Step 2: Switch the active thumbnail to the new variant
#   setAsDefault makes this thumbnail the one shown in listings and embed previews
curl -X POST "$KALTURA_SERVICE_URL/service/thumbAsset/action/setAsDefault" \
  -d "ks=$KALTURA_KS" \
  -d "format=1" \
  -d "thumbAssetId=$THUMB_ASSET_ID"

# Step 3: Compare impression-to-play ratio across date ranges
#   contentDropoff (reportType=2) includes count_loads (impressions) and count_plays
#   Run this for each variant's date range and compare the plays/impressions ratio
curl -X POST "$KALTURA_SERVICE_URL/service/report/action/getTable" \
  -d "ks=$KALTURA_KS" \
  -d "format=1" \
  -d "reportType=2" \
  -d "reportInputFilter[objectType]=KalturaEndUserReportInputFilter" \
  -d "reportInputFilter[fromDate]=$VARIANT_B_START" \
  -d "reportInputFilter[toDate]=$VARIANT_B_END" \
  -d "reportInputFilter[entryIdIn]=$ENTRY_ID" \
  -d "pager[pageSize]=25" \
  -d "pager[pageIndex]=1" \
  -d "responseOptions[objectType]=KalturaReportResponseOptions" \
  -d "responseOptions[delimiter]=|"
```

Run the same `reportType=2` query with Variant A's date range, then compare the `count_plays / count_loads` ratio. A higher ratio indicates the thumbnail is more effective at converting impressions to plays. For statistically significant results, run each variant for at least 7 days with comparable traffic.

See also: [Upload & Delivery Guide](KALTURA_UPLOAD_AND_DELIVERY_API.md) for thumbnail management.

## 13.14 Webhook-Triggered Automated Reporting

Automate weekly analytics reports, real-time engagement alerts, and compliance report generation by combining webhooks with the report service. Webhooks fire on content events, trigger report generation, and route results through the messaging system.

```bash
# Step 1: Create an HTTP webhook template that fires on entry status changes
#   This webhook can trigger a report-generation endpoint when content goes live
curl -X POST "$KALTURA_SERVICE_URL/service/eventNotificationTemplate/action/add" \
  -d "ks=$KALTURA_KS" \
  -d "format=1" \
  -d "eventNotificationTemplate[objectType]=KalturaHttpNotificationTemplate" \
  -d "eventNotificationTemplate[name]=Analytics+Report+Trigger" \
  -d "eventNotificationTemplate[description]=Triggers+report+generation+on+entry+changes" \
  -d "eventNotificationTemplate[type]=httpNotification.Http" \
  -d "eventNotificationTemplate[eventType]=3" \
  -d "eventNotificationTemplate[eventObjectType]=1" \
  -d "eventNotificationTemplate[url]=$REPORT_WEBHOOK_ENDPOINT" \
  -d "eventNotificationTemplate[method]=2" \
  -d "eventNotificationTemplate[contentType][objectType]=KalturaHttpNotificationObjectData"

# Step 2: Verify the webhook template is registered
curl -X POST "$KALTURA_SERVICE_URL/service/eventNotificationTemplate/action/list" \
  -d "ks=$KALTURA_KS" \
  -d "format=1" \
  -d "filter[objectType]=KalturaEventNotificationTemplateFilter" \
  -d "filter[typeEqual]=httpNotification.Http" \
  -d "pager[pageSize]=25" \
  -d "pager[pageIndex]=1"

# Step 3: Scheduled CSV export (run weekly via cron or webhook timer)
#   Generate a full weekly report and download the CSV
CSV_URL=$(curl -s -X POST "$KALTURA_SERVICE_URL/service/report/action/getUrlForReportAsCsv" \
  -d "ks=$KALTURA_KS" \
  -d "format=1" \
  -d "reportTitle=Weekly+Content+Report" \
  -d "reportText=Automated+weekly+analytics" \
  -d "headers=Entry,Name,Plays,Minutes,Unique+Viewers" \
  -d "reportType=38" \
  -d "reportInputFilter[objectType]=KalturaEndUserReportInputFilter" \
  -d "reportInputFilter[fromDate]=$WEEK_START" \
  -d "reportInputFilter[toDate]=$WEEK_END" \
  -d "responseOptions[objectType]=KalturaReportResponseOptions" \
  -d "responseOptions[delimiter]=|" | tr -d '"')
curl -o weekly_report.csv "$CSV_URL"
```

For real-time alerting: when the webhook endpoint receives an event, call `report.getTable` with `reportType=35` (uniqueUsersPlay) to check concurrent viewer count. If the count drops below a threshold, send an alert via the Messaging service (see [Messaging Guide](KALTURA_MESSAGING_API.md)). For enriched compliance reports, use `report.getCsvFromStringParams` with IDs 3006-3008 to include user metadata.

See also: [Webhooks Guide](KALTURA_WEBHOOKS_API.md) for event notification template configuration, [Messaging Guide](KALTURA_MESSAGING_API.md) for alert delivery.

## 13.15 Cross-Guide Workflow: Full Event Lifecycle

This master workflow demonstrates how the Analytics Reports, Events Collection, and Gamification guides work together with other guides to orchestrate a complete virtual event from planning through post-event follow-up.

### Pre-Event Setup

1. **Create the virtual event** with sessions, rooms, and schedule [Events Platform](KALTURA_EVENTS_PLATFORM_API.md)
2. **Configure gamification rules** for the event — point values for watching, polling, Q&A, and networking [Gamification](KALTURA_GAMIFICATION_API.md)
3. **Set up analytics dashboards** by creating report filters scoped to the event's `virtualEventId` [Analytics Reports]
4. **Register attendees** and assign them to user groups for segmented reporting [User Profile](KALTURA_USER_PROFILE_API.md)
5. **Send invitations** with personalized join links via the messaging system [Messaging](KALTURA_MESSAGING_API.md)
6. **Configure webhooks** to fire on session start/end for automated metric collection [Webhooks](KALTURA_WEBHOOKS_API.md)

### During the Event

1. **Player fires playback events automatically** — play, pause, seek, quartile milestones, buffer events — all collected by the analytics pipeline with zero application code [Events Collection](KALTURA_ANALYTICS_EVENTS_COLLECTION_API.md)
2. **Custom portal events** are reported via `analytics.trackEvent` — page views, CTA clicks, resource downloads, booth visits [Events Collection](KALTURA_ANALYTICS_EVENTS_COLLECTION_API.md)
3. **Gamification rules engine scores in real-time** — each playback and custom event feeds the scoring engine, updating leaderboards and triggering badge awards [Gamification](KALTURA_GAMIFICATION_API.md)
4. **Production monitors stream health** via `beacon.list` for encoder data and `liveReports.getEvents` for concurrent viewer counts [Analytics Reports]
5. **Flash challenges** are launched via `scheduledGameObject` — time-limited bonus point opportunities that drive engagement spikes [Gamification](KALTURA_GAMIFICATION_API.md)
6. **Real-time leaderboard** displays on the event portal, pulling from the gamification leaderboard API [Gamification](KALTURA_GAMIFICATION_API.md)

```bash
# During-event: Monitor live stream health (poll every 10 seconds)
curl -X POST "$KALTURA_SERVICE_URL/service/beacon/action/list" \
  -d "ks=$KALTURA_KS" \
  -d "format=1" \
  -d "filter[objectType]=KalturaBeaconFilter" \
  -d "filter[eventTypeIn]=0_healthData,1_healthData" \
  -d "filter[indexTypeEqual]=log" \
  -d "filter[relatedObjectTypeIn]=4" \
  -d "filter[objectIdIn]=$LIVE_ENTRY_ID" \
  -d "filter[orderBy]=-updatedAt"

# During-event: Get concurrent viewer count (poll every 30 seconds)
FROM_UNIX=$(($(date +%s) - 110))
TO_UNIX=$(($(date +%s) - 20))
curl -X POST "$KALTURA_SERVICE_URL/service/liveReports/action/getEvents" \
  -d "ks=$KALTURA_KS" \
  -d "format=1" \
  -d "reportType=ENTRY_TIME_LINE" \
  -d "filter[objectType]=KalturaLiveReportInputFilter" \
  -d "filter[entryIds]=$LIVE_ENTRY_ID" \
  -d "filter[fromTime]=$FROM_UNIX" \
  -d "filter[toTime]=$TO_UNIX" \
  -d "filter[live]=1"
```

### Post-Event Follow-Up

1. **Generate lead scoring report** from the gamification engine — classify attendees as Hot/Warm/Cold based on total engagement score [Gamification](KALTURA_GAMIFICATION_API.md)
2. **Pull per-user engagement** via report ID 4021 (User Reactions Report) with per-attendee poll answers, reactions, and Q&A participation [Analytics Reports]
3. **Generate C&C reports** via the Reports Microservice for polls activity, registration data, and session attendance [Analytics Reports]
4. **Export badge and certificate reports** listing which attendees earned which awards [Gamification](KALTURA_GAMIFICATION_API.md)
5. **Bulk CSV export** via `report.getUrlForReportAsCsv` for import into BI tools and CRM [Analytics Reports]
6. **Send follow-up emails** segmented by engagement tier — personalized content recommendations for high-engagement attendees, re-engagement prompts for low-engagement [Messaging](KALTURA_MESSAGING_API.md)
7. **On-demand replay** continues feeding both analytics and gamification — viewers who watch the replay earn points and their engagement data flows into the same reporting pipeline [Events Collection](KALTURA_ANALYTICS_EVENTS_COLLECTION_API.md), [Gamification](KALTURA_GAMIFICATION_API.md)

```bash
# Post-event: Per-attendee engagement report
curl -X POST "$KALTURA_SERVICE_URL/service/report/action/getCsvFromStringParams" \
  -d "ks=$KALTURA_KS" \
  -d "format=1" \
  -d "id=4021" \
  -d "params=from_date=$EVENT_START;to_date=$EVENT_END;virtualeventid=$VIRTUAL_EVENT_ID"
```

## 13.16 Cross-Guide Workflow: Analytics-Driven Content Automation Pipeline

This pipeline automates the full content lifecycle from upload through performance monitoring, using webhooks to chain together processing, enrichment, and analytics-driven optimization.

1. **Upload content** via chunked upload or `addFromUrl` [Upload & Delivery](KALTURA_UPLOAD_AND_DELIVERY_API.md)
2. **Webhook fires on ENTRY_READY** when transcoding completes, triggering the enrichment pipeline [Webhooks](KALTURA_WEBHOOKS_API.md)
3. **Auto-process via REACH and AI Agents** — the webhook handler submits the entry for captioning, translation, and AI-generated metadata [REACH](KALTURA_REACH_API.md), [Agents Manager](KALTURA_AGENTS_MANAGER_API.md)
4. **Webhook fires on task completion** when captions and metadata are ready, confirming enrichment is complete [Webhooks](KALTURA_WEBHOOKS_API.md)
5. **Player fires playback events** as viewers watch the content — play, quartile, seek, and buffer events flow automatically into analytics [Events Collection](KALTURA_ANALYTICS_EVENTS_COLLECTION_API.md)
6. **Analytics accumulate** over the monitoring window — plays, watch time, engagement rate, drop-off patterns build up in the reporting pipeline [Analytics Reports]
7. **Scheduled report check** runs `report.getTable` to evaluate content performance against thresholds — if engagement rate falls below target, send an alert via Messaging [Analytics Reports], [Messaging](KALTURA_MESSAGING_API.md)
8. **Compare enriched vs. non-enriched metrics** — pull reports for entries with and without captions/AI-metadata to quantify the ROI of automated enrichment [Analytics Reports]

```bash
# Step 7: Scheduled performance check — flag underperforming content
#   topContentCreator (reportType=38) ordered by plays, filtered to recent uploads
curl -X POST "$KALTURA_SERVICE_URL/service/report/action/getTable" \
  -d "ks=$KALTURA_KS" \
  -d "format=1" \
  -d "reportType=38" \
  -d "reportInputFilter[objectType]=KalturaEndUserReportInputFilter" \
  -d "reportInputFilter[fromDate]=$MONITORING_START" \
  -d "reportInputFilter[toDate]=$MONITORING_END" \
  -d "reportInputFilter[entryIdIn]=$RECENT_ENTRY_IDS" \
  -d "order=-count_plays" \
  -d "pager[pageSize]=100" \
  -d "pager[pageIndex]=1" \
  -d "responseOptions[objectType]=KalturaReportResponseOptions" \
  -d "responseOptions[delimiter]=|"

# Step 8: Compare engagement for captioned vs. uncaptioned entries
#   Run the same report for each group and compare avg_view_drop_off and sum_time_viewed
curl -X POST "$KALTURA_SERVICE_URL/service/report/action/getTable" \
  -d "ks=$KALTURA_KS" \
  -d "format=1" \
  -d "reportType=2" \
  -d "reportInputFilter[objectType]=KalturaEndUserReportInputFilter" \
  -d "reportInputFilter[fromDate]=$MONITORING_START" \
  -d "reportInputFilter[toDate]=$MONITORING_END" \
  -d "reportInputFilter[entryIdIn]=$CAPTIONED_ENTRY_IDS" \
  -d "pager[pageSize]=100" \
  -d "pager[pageIndex]=1" \
  -d "responseOptions[objectType]=KalturaReportResponseOptions" \
  -d "responseOptions[delimiter]=|"
```

## 13.17 Cross-Guide Workflow: CRM Integration Pipeline

This pipeline connects event engagement data to CRM systems for sales follow-up, combining user registration, gamification-based lead scoring, playback analytics, and automated data export.

1. **Register attendees** via the User Profile API and capture registration metadata (company, title, interest areas) [User Profile](KALTURA_USER_PROFILE_API.md)
2. **Configure gamification rules** that assign point values to high-intent actions — watching product demos earns more than watching keynotes, booth visits earn more than passive viewing [Gamification](KALTURA_GAMIFICATION_API.md)
3. **Playback events collected automatically** as attendees watch sessions — the player reports play, quartile completion, and seek events to the analytics pipeline [Events Collection](KALTURA_ANALYTICS_EVENTS_COLLECTION_API.md)
4. **Custom engagement events tracked** via `analytics.trackEvent` — CTA clicks, resource downloads, meeting requests, and demo sign-ups [Events Collection](KALTURA_ANALYTICS_EVENTS_COLLECTION_API.md)
5. **Lead scoring report classifies attendees** into Hot/Warm/Cold tiers based on cumulative gamification score — Hot leads (top 10%) are flagged for immediate sales outreach [Gamification](KALTURA_GAMIFICATION_API.md)
6. **User Reactions Report (ID 4021)** provides per-attendee interaction detail — poll responses, Q&A questions, reactions — enriching the CRM contact record [Analytics Reports]
7. **Push to CRM** via CSV export or webhook — `getUrlForReportAsCsv` generates a downloadable file for batch import, or a webhook endpoint receives real-time score updates [Analytics Reports], [Webhooks](KALTURA_WEBHOOKS_API.md)
8. **Ongoing sync** — replay viewers continue accumulating engagement, and scheduled report runs update CRM records weekly [Analytics Reports]

```bash
# Step 6: Per-attendee interaction detail for CRM enrichment
#   User Reactions Report (ID 4021) provides poll answers, reactions, Q&A data
curl -X POST "$KALTURA_SERVICE_URL/service/report/action/getCsvFromStringParams" \
  -d "ks=$KALTURA_KS" \
  -d "format=1" \
  -d "id=4021" \
  -d "params=from_date=$EVENT_START;to_date=$EVENT_END;virtualeventid=$VIRTUAL_EVENT_ID"

# Step 7: Bulk export for CRM import
#   Generate a CSV with engagement data for all event attendees
CSV_URL=$(curl -s -X POST "$KALTURA_SERVICE_URL/service/report/action/getUrlForReportAsCsv" \
  -d "ks=$KALTURA_KS" \
  -d "format=1" \
  -d "reportTitle=CRM+Lead+Export" \
  -d "reportText=Event+Engagement+for+CRM" \
  -d "headers=User,Name,Email,Plays,Minutes,Unique+Sessions,Engagement+Score" \
  -d "reportType=38" \
  -d "reportInputFilter[objectType]=KalturaEndUserReportInputFilter" \
  -d "reportInputFilter[fromDate]=$EVENT_START" \
  -d "reportInputFilter[toDate]=$EVENT_END" \
  -d "reportInputFilter[virtualEventIdIn]=$VIRTUAL_EVENT_ID" \
  -d "responseOptions[objectType]=KalturaReportResponseOptions" \
  -d "responseOptions[delimiter]=|" | tr -d '"')
curl -o crm_lead_export.csv "$CSV_URL"
```


# 14. Best Practices

**Date handling.** All API v3 report filter dates use Unix timestamps in **seconds** (not milliseconds). For example, `Math.floor(Date.now() / 1000)` in JavaScript or `int(time.time())` in Python.

**Pipe-delimited parsing.** Always set `responseOptions[delimiter]=|` for consistency. Parse the `header` field to map column positions dynamically rather than hardcoding column indices — columns may vary by report type and account configuration.

**Multi-request for dashboards.** Batch `getTotal` + `getGraphs` + `getTable` in a single `KalturaMultiRequest` to reduce round trips. This is the standard pattern for building analytics dashboard views.

**CSV vs API tradeoffs.** Use `report.getTable` for real-time dashboard queries with pagination. Use `report.getUrlForReportAsCsv` for bulk exports, scheduled ETL jobs, and BI tool ingestion. Use `report.getCsvFromStringParams` for specialized reports (IDs 4021, 6000-6002, 3006-3008) that are not available via the standard filter interface.

**Polling intervals for live.** Follow the recommended intervals in section 9.3. Polling faster than recommended wastes resources without improving data freshness. Polling slower may miss transient issues.

**Reports Microservice polling.** Always use `statusOnly: true` for the polling loop to avoid downloading the full CSV on every check. Only omit `statusOnly` for the final download request after status shows `completed`.

**Cross-service analytics.** Use `appId:<name>` in KS privileges to tag analytics per-application. Use `virtualEventIdIn` to scope reports to specific events. Use `categoriesIdsIn` to scope by content library. See the [Session Guide](KALTURA_SESSION_GUIDE.md) for KS privilege syntax.


# 15. Related Guides

| Guide | Analytics Connection |
|-------|---------------------|
| [Session Guide](KALTURA_SESSION_GUIDE.md) | `appId:<name>` KS privilege tags analytics per-application; `userId` ties analytics to a user |
| [AppTokens](KALTURA_APPTOKENS_API.md) | Scoped tokens for analytics-only access |
| [Player Embed](KALTURA_PLAYER_EMBED_GUIDE.md) | Player v7 fires ~45 playback events that feed analytics automatically |
| [Events Collection](KALTURA_ANALYTICS_EVENTS_COLLECTION_API.md) | Report custom playback and application events back to analytics |
| [Events Platform](KALTURA_EVENTS_PLATFORM_API.md) | `virtualEventIdIn` filter scopes reports to a specific event |
| [User Profile](KALTURA_USER_PROFILE_API.md) | `reports/eventDataStats` for attendance stats; registration reports via Reports Microservice |
| [Messaging](KALTURA_MESSAGING_API.md) | `message/stats` for delivery statistics |
| [REACH](KALTURA_REACH_API.md) | `entryVendorTask.list` for task monitoring; `exportToCsv` for batch CSV |
| [User Management](KALTURA_USER_MANAGEMENT_API.md) | `ANALYTICS_BASE` role permission gates analytics access |
| [Webhooks](KALTURA_WEBHOOKS_API.md) | Trigger automated reporting on content events |
| [eSearch](KALTURA_ESEARCH_API.md) | Enrich analytics data with entry metadata, tags, categories |
| [Categories & Access Control](KALTURA_CATEGORIES_AND_ACCESS_CONTROL_API.md) | `categoriesIdsIn` filter for content library scoping |
| [Gamification](KALTURA_GAMIFICATION_API.md) | Analytics events feed the gamification rules engine |

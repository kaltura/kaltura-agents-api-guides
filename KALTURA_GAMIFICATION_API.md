# Kaltura Gamification API

The Game Services (SCM) API powers engagement mechanics for virtual events and learning platforms — leaderboards, badges, certificates, and lead scoring. A rules engine processes analytics events (playback, quizzes, polls, chat) and triggers scoring, achievement, and certification actions automatically.

**Base URL:** `https://scm.{region}.ovp.kaltura.com/api/v1/`
**Auth:** `Authorization: Bearer <KS>` header (ADMIN KS, type=2)
**Format:** JSON request/response bodies, all endpoints use POST

| Controller | Key Actions | Description |
|------------|-------------|-------------|
| `leaderboard` | create, update, get, list, delete | Leaderboard lifecycle and configuration |
| `certificate` | create, update, get, list, delete | Certificate definitions with PDF templates |
| `badge` | create, update, get, list, delete | Badge definitions with icons and rules |
| `leadScoring` | create, update, get, list, delete | Lead scoring profile configuration |
| `rule` | create, update, get, list, delete | Rules engine configuration |
| `userScore` | get, list, clear, ruleProgress | User score queries and management |
| `userBadge` | list | User badge status and progress |
| `userCertificateReport` | list | User certificate status |
| `userLeadScoring` | list | User lead scoring data |
| `event` | sendExternalEventsFromCSV | External event ingestion |
| `report` | generate | Report generation (8 types) |
| `scheduledGameObject` | create, update, list, delete | Scheduled status transitions |


# 1. Authentication

All requests require an ADMIN KS (type=2) in the `Authorization` header:

```bash
# Set up environment
export KALTURA_SCM_URL="https://scm.nvp1.ovp.kaltura.com/api/v1"
export KALTURA_KS="your_kaltura_session"
```

Generate an ADMIN KS via `session.start` (see [Session Guide](KALTURA_SESSION_GUIDE.md)) or `appToken.startSession` (see [AppTokens Guide](KALTURA_APPTOKENS_API.md)).

## 1.1 Regional Endpoints

| Region | Base URL |
|--------|----------|
| US Production | `https://scm.nvp1.ovp.kaltura.com/api/v1/` |
| EU (France) | `https://scm.frp2.ovp.kaltura.com/api/v1/` |
| EU (Ireland) | `https://scm.irp2.ovp.kaltura.com/api/v1/` |
| APAC (Singapore) | `https://scm.sgp2.ovp.kaltura.com/api/v1/` |
| APAC (Sydney) | `https://scm.syp2.ovp.kaltura.com/api/v1/` |
| Canada | `https://scm.cap2.ovp.kaltura.com/api/v1/` |

## 1.2 Permissions

| Permission | Description |
|------------|-------------|
| `GAME_BASE` | Read operations — list scores, get badges, view reports |
| `GAME_MANAGE` | Write operations — create leaderboards, define rules, manage certificates |

Enable Game Services for your partner account in Kaltura Admin Console.


# 2. Leaderboard Entity & CRUD

Leaderboards track user scores and rank users. They are scoped to virtual events via `virtualEventIds`.

## 2.1 Leaderboard Entity

| Field | Type | Description |
|-------|------|-------------|
| `id` | string | Auto-generated unique identifier (read-only) |
| `name` | string | Leaderboard display name |
| `description` | string | Description text |
| `status` | string | `scheduled`, `enabled`, `disabled` |
| `startDate` | ISO 8601 | Scoring window start |
| `endDate` | ISO 8601 | Scoring window end |
| `virtualEventIds` | int[] | Virtual event IDs this leaderboard applies to |
| `participationPolicy` | object | Controls user visibility (see section 3) |
| `subLeaderboards` | array | Segments for team/regional rankings (see section 2.4) |

**Status lifecycle:** `scheduled` → `enabled` → `disabled`. Create leaderboards as `scheduled`, then update to `enabled` when the event starts.

## 2.2 Create Leaderboard

```bash
curl -X POST "$KALTURA_SCM_URL/leaderboard/create" \
  -H "Authorization: Bearer $KALTURA_KS" \
  -H "Content-Type: application/json" \
  -d '{
    "objectType": "Leaderboard",
    "name": "Conference Engagement",
    "description": "Points for session attendance, polls, and chat",
    "status": "scheduled",
    "startDate": "2025-06-01T09:00:00.000Z",
    "endDate": "2025-06-03T18:00:00.000Z",
    "participationPolicy": {
      "userDefaultPolicy": "display",
      "policies": []
    },
    "virtualEventIds": ["$VIRTUAL_EVENT_ID"]
  }'
```

## 2.3 Get, Update, List, Delete

```bash
# Get
curl -X POST "$KALTURA_SCM_URL/leaderboard/get" \
  -H "Authorization: Bearer $KALTURA_KS" \
  -H "Content-Type: application/json" \
  -d '{"id": "'$LEADERBOARD_ID'"}'

# Update (enable when event starts)
curl -X POST "$KALTURA_SCM_URL/leaderboard/update" \
  -H "Authorization: Bearer $KALTURA_KS" \
  -H "Content-Type: application/json" \
  -d '{"id": "'$LEADERBOARD_ID'", "status": "enabled"}'

# List (paginated)
curl -X POST "$KALTURA_SCM_URL/leaderboard/list" \
  -H "Authorization: Bearer $KALTURA_KS" \
  -H "Content-Type: application/json" \
  -d '{"pager": {"pageSize": 10, "pageIndex": 1}}'

# Delete
curl -X POST "$KALTURA_SCM_URL/leaderboard/delete" \
  -H "Authorization: Bearer $KALTURA_KS" \
  -H "Content-Type: application/json" \
  -d '{"id": "'$LEADERBOARD_ID'"}'
```

## 2.4 Sub-Leaderboards

Segment users by properties (country, company, department) for team-based or regional competitions.

```bash
curl -X POST "$KALTURA_SCM_URL/leaderboard/create" \
  -H "Authorization: Bearer $KALTURA_KS" \
  -H "Content-Type: application/json" \
  -d '{
    "objectType": "Leaderboard",
    "name": "Regional Competition",
    "status": "scheduled",
    "startDate": "2025-06-01T00:00:00Z",
    "endDate": "2025-06-02T00:00:00Z",
    "participationPolicy": {"userDefaultPolicy": "display", "policies": []},
    "virtualEventIds": ["$VIRTUAL_EVENT_ID"],
    "subLeaderboards": [
      {"name": "By Country", "filterPaths": ["country"], "id": 0},
      {"name": "By Company", "filterPaths": ["company"], "id": 1}
    ]
  }'
```

`filterPaths` references user profile properties from the [User Profile API](KALTURA_USER_PROFILE_API.md). Individual scores automatically aggregate within their sub-leaderboard segment.


# 3. Participation Policies

Participation policies control user visibility across all game objects (leaderboards, badges, certificates, lead scoring).

| Policy | Description |
|--------|-------------|
| `display` | User participates; progress visible to other users |
| `do_not_display` | User participates; progress visible only to admins |
| `do_not_save` | User does not participate; no data collected |

## 3.1 Matching Criteria

| Criteria | Description |
|----------|-------------|
| `byGroup` | Match by user group ID |
| `byEmailDomain` | Match by email domain |

Policies evaluate in array order. First match wins. If no policy matches, `userDefaultPolicy` applies.

```bash
curl -X POST "$KALTURA_SCM_URL/leaderboard/create" \
  -H "Authorization: Bearer $KALTURA_KS" \
  -H "Content-Type: application/json" \
  -d '{
    "objectType": "Leaderboard",
    "name": "External Only",
    "status": "scheduled",
    "startDate": "2025-06-01T00:00:00Z",
    "endDate": "2025-06-02T00:00:00Z",
    "participationPolicy": {
      "userDefaultPolicy": "display",
      "policies": [
        {"policy": "do_not_save", "matchCriteria": "byEmailDomain", "values": ["internal-company.com"]},
        {"policy": "do_not_display", "matchCriteria": "byGroup", "values": ["speakers"]}
      ]
    },
    "virtualEventIds": ["$VIRTUAL_EVENT_ID"]
  }'
```

In this example, internal employees are excluded entirely (`do_not_save`), speakers participate but are hidden from rankings (`do_not_display`), and all other users are visible (`display`).


# 4. Rules Engine

The rules engine evaluates analytics events against configured rules and triggers scoring, achievement, and certification actions. Rules are the core abstraction that ties all gamification features together.

## 4.1 Rule Entity

| Field | Required | Description |
|-------|----------|-------------|
| `gameObjectType` | Yes | `leaderboard`, `certificate`, `badge`, `leadScoring` |
| `gameObjectId` | Yes | ID of the parent game object |
| `name` | Yes | Rule display name |
| `conditions` | Yes | Array of `{fact, operator, value}` — all must match (AND) |
| `type` | Yes | `sum`, `count`, `countUnique`, `countBoolean`, `external`, `override` |
| `mode` | Yes | `distribute_points`, `dont_distribute_points`, `block_root_rule_while_in_progress`, `block_root_rule_if_exhausted` |
| `metric` | Yes | Event field to evaluate: `playTime`, `kuserId`, `like`, `score`, `pollId` |
| `groupBy` | Yes | Scope fields, comma-separated: `kuserId`, `kuserId,entryId` |
| `goal` | Yes | Threshold to trigger point distribution |
| `points` | Yes | Fixed value (`"50"`) or dynamic event field name (`"score"`) |
| `maxPoints` | No | Cap on total points. Fixed, dynamic, or `"unlimited"` |
| `reportFormat` | No | `default` or `in_minutes` |
| `status` | No | `enabled` or `disabled` |
| `subRules` | No | Array of child rules for multi-stage logic |
| `userIdOverride` | No | Map points to a different user (e.g., upvote recipient) |

## 4.2 Rule Types

| Type | Description | Example |
|------|-------------|---------|
| `sum` | Sum the metric value across events | Sum `playTime` — when total reaches `goal` seconds, distribute points |
| `count` | Count matching events | Count `pollAnswered` events — when count reaches `goal`, distribute points |
| `countUnique` | Count unique metric values | Count unique `entryId` values — "watch N different sessions" |
| `countBoolean` | Count events where metric is truthy | Count events where `like` is true |
| `external` | Accept external/3rd-party scores | Metric must be `"score"`; points come from the event's score field |
| `override` | Replace existing score entirely | Override with new value instead of accumulating |

## 4.3 Rule Modes

| Mode | Description |
|------|-------------|
| `distribute_points` | When goal is met, distribute `points` to the user's score |
| `dont_distribute_points` | Track progress without adding to score (for badge rules that track activity separately) |
| `block_root_rule_while_in_progress` | Sub-rule must complete before the root rule can accumulate |
| `block_root_rule_if_exhausted` | Once this sub-rule reaches its max, the root rule stops accumulating |

## 4.4 Condition Operators

`equal`, `notEqual`, `lessThan`, `greaterThan`, `in`, `notIn`, `contains`, `doesNotContain`

## 4.5 Condition Facts (Event Fields)

| Fact | Description |
|------|-------------|
| `eventType` | `viewPeriod`, `quizSubmitted`, `pollAnswered`, `comment`, `like`, `registered`, etc. |
| `entryId` | Kaltura entry ID |
| `categories` | Category IDs the entry belongs to |
| `virtualEventId` | Virtual event ID |

**Single category:**
```json
{"fact": "categories", "operator": "in", "value": "325222712"}
```

**Multiple categories (OR):**
```json
{
  "any": [
    {"fact": "categories", "operator": "contains", "value": "$CATEGORY_ID_1"},
    {"fact": "categories", "operator": "contains", "value": "$CATEGORY_ID_2"}
  ]
}
```

## 4.6 Analytics Events That Feed Rules

| Source | Event Types | Example Rules |
|--------|------------|---------------|
| Playback | `viewPeriod` | Watch duration, per-session completion |
| In-Video Quizzes | `quizSubmitted` | Quiz completion, first-to-complete bonus |
| Chat & Collaboration | `pollAnswered`, `comment`, `like`/`upvote` | Poll participation, chat engagement |
| Live Q&A | `questionAsked`, `questionPromoted` | Q&A participation |
| KME | `participated`, `quizAnswer` | Meeting attendance |
| Registration | `registered` | Event registration, first-to-register bonus |

## 4.7 Rule CRUD

```bash
# Create rule for a leaderboard
curl -X POST "$KALTURA_SCM_URL/rule/create" \
  -H "Authorization: Bearer $KALTURA_KS" \
  -H "Content-Type: application/json" \
  -d '{
    "gameObjectType": "leaderboard",
    "gameObjectId": "'$LEADERBOARD_ID'",
    "name": "Watch sessions",
    "description": "10 points per 60 seconds watched",
    "conditions": [{"fact": "eventType", "operator": "equal", "value": "viewPeriod"}],
    "type": "sum",
    "mode": "distribute_points",
    "metric": "playTime",
    "groupBy": "kuserId,entryId",
    "goal": "60",
    "points": "10",
    "maxPoints": "100",
    "reportFormat": "default"
  }'

# List rules for a game object
curl -X POST "$KALTURA_SCM_URL/rule/list" \
  -H "Authorization: Bearer $KALTURA_KS" \
  -H "Content-Type: application/json" \
  -d '{"gameObjectType": "leaderboard", "gameObjectId": "'$LEADERBOARD_ID'"}'

# Update rule (enable)
curl -X POST "$KALTURA_SCM_URL/rule/update" \
  -H "Authorization: Bearer $KALTURA_KS" \
  -H "Content-Type: application/json" \
  -d '{"id": "'$RULE_ID'", "status": "enabled"}'

# Delete rule
curl -X POST "$KALTURA_SCM_URL/rule/delete" \
  -H "Authorization: Bearer $KALTURA_KS" \
  -H "Content-Type: application/json" \
  -d '{"id": "'$RULE_ID'"}'
```

## 4.8 Sub-Rules

Sub-rules enable multi-stage logic. Example: root rule awards points per upvote, sub-rule caps total upvotes per user.

```bash
curl -X POST "$KALTURA_SCM_URL/rule/create" \
  -H "Authorization: Bearer $KALTURA_KS" \
  -H "Content-Type: application/json" \
  -d '{
    "gameObjectType": "leaderboard",
    "gameObjectId": "'$LEADERBOARD_ID'",
    "name": "Upvotes on comments",
    "conditions": [{"fact": "eventType", "operator": "equal", "value": "like"}],
    "type": "count",
    "mode": "distribute_points",
    "metric": "like",
    "groupBy": "kuserId,entryId",
    "goal": "1",
    "points": "20",
    "maxPoints": "100",
    "subRules": [
      {
        "name": "Cap at 5 upvotes",
        "type": "count",
        "metric": "commentId",
        "groupBy": "kuserId",
        "goal": "1",
        "maxPoints": "5",
        "mode": "block_root_rule_if_exhausted"
      }
    ]
  }'
```


# 5. Badges

Badges reward users for completing a set of activity rules. A user either has a badge or does not — they are binary achievements.

## 5.1 Badge Entity

Rules are defined **inline** during badge creation (not via separate `rule/create` calls).

```bash
curl -X POST "$KALTURA_SCM_URL/badge/create" \
  -H "Authorization: Bearer $KALTURA_KS" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Session Attendee",
    "description": "Attend 3 sessions to earn this badge",
    "virtualEventIds": ["$VIRTUAL_EVENT_ID"],
    "iconUrl": "https://example.com/badges/attendee.png",
    "participationPolicy": {"userDefaultPolicy": "display", "policies": []},
    "rules": [
      {
        "name": "Watch 3 sessions",
        "conditions": [{"fact": "eventType", "operator": "equal", "value": "viewPeriod"}],
        "type": "countUnique",
        "metric": "entryId",
        "groupBy": "kuserId",
        "goal": "3",
        "points": "1",
        "maxPoints": "1"
      }
    ]
  }'
```

## 5.2 Badge Achievement Lifecycle

1. Analytics events are evaluated against each badge's rules
2. Per-user per-rule progress is tracked in `rulesData[]` (each has `id`, `progress`, `completed`)
3. When **all** rules have `completed: true`, badge status updates to `ACHIEVED` with `achievedTimestamp`

## 5.3 Badge CRUD

```bash
# Get badge
curl -X POST "$KALTURA_SCM_URL/badge/get" \
  -H "Authorization: Bearer $KALTURA_KS" \
  -H "Content-Type: application/json" \
  -d '{"id": "'$BADGE_ID'"}'

# List badges
curl -X POST "$KALTURA_SCM_URL/badge/list" \
  -H "Authorization: Bearer $KALTURA_KS" \
  -H "Content-Type: application/json" \
  -d '{"pager": {"pageSize": 10, "pageIndex": 1}}'

# Delete badge
curl -X POST "$KALTURA_SCM_URL/badge/delete" \
  -H "Authorization: Bearer $KALTURA_KS" \
  -H "Content-Type: application/json" \
  -d '{"id": "'$BADGE_ID'"}'
```

## 5.4 User Badge Progress

```bash
curl -X POST "$KALTURA_SCM_URL/userBadge/list" \
  -H "Authorization: Bearer $KALTURA_KS" \
  -H "Content-Type: application/json" \
  -d '{"gameObjectId": "'$BADGE_ID'", "pager": {"pageSize": 100, "pageIndex": 1}}'
```

Response:

```json
{
  "totalCount": 1,
  "objects": [{
    "userId": "user@example.com",
    "rulesData": [
      {"id": "rule1_id", "progress": 3, "completed": true}
    ],
    "status": "ACHIEVED",
    "achievedTimestamp": "2025-06-15T10:30:00Z"
  }]
}
```


# 6. Certificates

Certificates issue PDF credentials to users who complete required activities. They use the same rules engine as badges, with added PDF generation configuration.

## 6.1 Certificate Entity

| Field | Type | Description |
|-------|------|-------------|
| `name` | string | Certificate name |
| `description` | string | Description (supports HTML) |
| `status` | string | `enabled` or `disabled` |
| `externalId` | string | External reference (e.g., NASBA program ID) |
| `certificateEligibility` | string | `once` (one per user) or `perEntry` (one per user per entry) |
| `certifiedCreditsThreshold` | number | Credits required to earn the certificate |
| `host` | string | Events site URL for certificate page links |
| `outputFileConfiguration` | object | PDF template configuration (see below) |
| `creditsMapping` | string | Maps rules to credit values |
| `participationPolicy` | object | Controls user visibility |

## 6.2 PDF Template (outputFileConfiguration)

The first element is a background image URL. Subsequent elements are text overlays with positioning.

**Text element types:** `entryName`, `userFullName`, `credits`, `certificationDate`

```bash
curl -X POST "$KALTURA_SCM_URL/certificate/create" \
  -H "Authorization: Bearer $KALTURA_KS" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "CPE Certificate",
    "description": "Continuing Professional Education",
    "status": "disabled",
    "participationPolicy": {"userDefaultPolicy": "display", "policies": []},
    "externalId": "PROGRAM-12345",
    "certificateEligibility": "once",
    "certifiedCreditsThreshold": 3,
    "host": "https://mysite.events.kaltura.com",
    "outputFileConfiguration": {
      "outputFileElements": [
        {"url": "https://cfvod.kaltura.com/p/'$PARTNER_ID'/thumbnail/entry_id/'$BG_ENTRY_ID'/width/1397/height/1080"},
        {"textElementType": "userFullName", "fontSize": 30, "y": 440},
        {"textElementType": "entryName", "fontSize": 30, "y": 570},
        {"textElementType": "credits", "fontSize": 23, "x": 1060, "y": 699},
        {"textElementType": "certificationDate", "fontSize": 18, "x": 695, "y": 636}
      ]
    }
  }'
```

## 6.3 Credits Mapping

Maps rules to credit values using a newline-delimited format:

```
credits,<ruleId>
<credits_value>,<threshold>
<credits_value>,<threshold>
```

```bash
curl -X POST "$KALTURA_SCM_URL/certificate/update" \
  -H "Authorization: Bearer $KALTURA_KS" \
  -H "Content-Type: application/json" \
  -d '{
    "id": "'$CERT_ID'",
    "status": "enabled",
    "creditsMapping": "credits,'$RULE_ID'\n10.0,1\n11.5,2"
  }'
```

## 6.4 Certificate Rules

Create rules for certificates via the standard `rule/create` endpoint with `gameObjectType: "certificate"`:

```bash
curl -X POST "$KALTURA_SCM_URL/rule/create" \
  -H "Authorization: Bearer $KALTURA_KS" \
  -H "Content-Type: application/json" \
  -d '{
    "gameObjectType": "certificate",
    "gameObjectId": "'$CERT_ID'",
    "name": "Watch session",
    "conditions": [{"fact": "eventType", "operator": "equal", "value": "viewPeriod"}],
    "type": "sum",
    "mode": "distribute_points",
    "metric": "playTime",
    "groupBy": "kuserId,entryId",
    "goal": "60",
    "points": "1",
    "maxPoints": "unlimited",
    "reportFormat": "default"
  }'
```

## 6.5 User Certificate Progress

```bash
curl -X POST "$KALTURA_SCM_URL/userCertificateReport/list" \
  -H "Authorization: Bearer $KALTURA_KS" \
  -H "Content-Type: application/json" \
  -d '{"gameObjectId": "'$CERT_ID'", "pager": {"pageSize": 100, "pageIndex": 1}}'
```


# 7. Lead Scoring

Lead scoring tracks user engagement during events and segments users by likelihood to convert. Two parallel segmentation systems run simultaneously.

## 7.1 Percentage Groups (Relative Ranking)

| Group | Range | Description |
|-------|-------|-------------|
| Hot Leads | 80-100% | Top 20% of participants |
| Warm Leads | 50-79% | Middle 30% |
| Cold Leads | 0-49% | Bottom 50% |

## 7.2 Score Groups (Absolute Thresholds)

| Group | Range |
|-------|-------|
| Top Score Leads | 1000+ |
| Mid Score Leads | 500-999 |
| Low Score Leads | 0-499 |

## 7.3 Lead Scoring CRUD

```bash
# Create lead scoring profile (scoreGroups or percentageGroups required)
curl -X POST "$KALTURA_SCM_URL/leadScoring/create" \
  -H "Authorization: Bearer $KALTURA_KS" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Event Lead Scoring",
    "description": "Score attendees by engagement",
    "status": "scheduled",
    "startDate": "2025-06-01T00:00:00Z",
    "endDate": "2025-06-03T23:59:59Z",
    "participationPolicy": {
      "userDefaultPolicy": "display",
      "policies": [
        {"policy": "do_not_save", "matchCriteria": "byEmailDomain", "values": ["internal-company.com"]}
      ]
    },
    "scoreGroups": [
      {"name": "Top Score Leads", "range": [1000, 99999]},
      {"name": "Mid Score Leads", "range": [500, 999]},
      {"name": "Low Score Leads", "range": [0, 499]}
    ],
    "virtualEventIds": ["$VIRTUAL_EVENT_ID"]
  }'

# Create rules for lead scoring
curl -X POST "$KALTURA_SCM_URL/rule/create" \
  -H "Authorization: Bearer $KALTURA_KS" \
  -H "Content-Type: application/json" \
  -d '{
    "gameObjectType": "leadScoring",
    "gameObjectId": "'$LEAD_SCORING_ID'",
    "name": "Session viewership",
    "conditions": [{"fact": "eventType", "operator": "equal", "value": "viewPeriod"}],
    "type": "sum",
    "mode": "distribute_points",
    "metric": "playTime",
    "groupBy": "kuserId,entryId",
    "goal": "60",
    "points": "10",
    "maxPoints": "unlimited",
    "reportFormat": "default"
  }'
```

## 7.4 User Lead Scoring Data

```bash
curl -X POST "$KALTURA_SCM_URL/userLeadScoring/list" \
  -H "Authorization: Bearer $KALTURA_KS" \
  -H "Content-Type: application/json" \
  -d '{"gameObjectId": "'$LEAD_SCORING_ID'", "pager": {"pageSize": 100, "pageIndex": 1}}'
```

## 7.5 Lead Scoring Reports

**Summary report:** Percentage Group Name, Range, Number of Users, Average Score, Average Engagement Score, Average User Profile Score.

**Detailed report:** Absolute Rank, Total Lead Score, User Name, Email, S-Group (absolute), Rank within S-Group, P-Group (percentage), Rank within P-Group, per-rule-group scores.

Reports are exportable to CRM systems as custom objects.


# 8. User Scores & Progress

## 8.1 Get User Score

```bash
curl -X POST "$KALTURA_SCM_URL/userScore/get" \
  -H "Authorization: Bearer $KALTURA_KS" \
  -H "Content-Type: application/json" \
  -d '{"gameObjectId": "'$LEADERBOARD_ID'", "userId": "'$USER_ID'"}'
```

## 8.2 List Scores (Paginated Ranking)

```bash
curl -X POST "$KALTURA_SCM_URL/userScore/list" \
  -H "Authorization: Bearer $KALTURA_KS" \
  -H "Content-Type: application/json" \
  -d '{"gameObjectId": "'$LEADERBOARD_ID'", "pager": {"pageSize": 25, "pageIndex": 1}}'
```

## 8.3 Per-Rule Progress

```bash
curl -X POST "$KALTURA_SCM_URL/userScore/ruleProgress" \
  -H "Authorization: Bearer $KALTURA_KS" \
  -H "Content-Type: application/json" \
  -d '{"gameObjectId": "'$LEADERBOARD_ID'", "userId": "'$USER_ID'"}'
```

## 8.4 Clear Scores

```bash
curl -X POST "$KALTURA_SCM_URL/userScore/clear" \
  -H "Authorization: Bearer $KALTURA_KS" \
  -H "Content-Type: application/json" \
  -d '{"gameObjectId": "'$LEADERBOARD_ID'"}'
```

## 8.5 API v3 Game Plugin

User scores are also accessible via the standard Kaltura API v3:

```bash
curl -X POST "$KALTURA_SERVICE_URL/service/leaderboard_userscore/action/list" \
  -d "ks=$KALTURA_KS" \
  -d "format=1" \
  -d "filter[objectType]=KalturaUserScorePropertiesFilter" \
  -d "filter[gameObjectType]=1" \
  -d "filter[gameObjectId]=$LEADERBOARD_ID" \
  -d "pager[pageSize]=25" \
  -d "pager[pageIndex]=1"
```

Response: `KalturaUserScorePropertiesResponse` with `rank`, `userId`, `puserId`, `score`, `scoreTags`, `oldRank`.


# 9. External Events & CSV Import

Import scores from external systems (booth scans, external quiz platforms, physical activities) via CSV upload.

```bash
# Delta mode — add to existing score
curl -X POST "$KALTURA_SCM_URL/event/sendExternalEventsFromCSV" \
  -H "Authorization: Bearer $KALTURA_KS" \
  -F "eventAction=delta" \
  -F "csvFile=@scores.csv"

# Upsert mode — replace existing score
curl -X POST "$KALTURA_SCM_URL/event/sendExternalEventsFromCSV" \
  -H "Authorization: Bearer $KALTURA_KS" \
  -F "eventAction=upsert" \
  -F "csvFile=@scores.csv"
```

**CSV format:** Must include `userId`, `score`, and `eventType` (matching rule condition) columns, plus any context fields referenced by rule conditions.

| Mode | Description |
|------|-------------|
| `delta` | Add to existing score (booth visit adds 50 points on top of current) |
| `upsert` | Replace score (final quiz score overrides previous attempts) |

The `external` rule type is required for the leaderboard to accept external events. Set `metric: "score"` so points come from the event's score field.


# 10. Reports

Generate reports for gamification data export.

## 10.1 Report Types

| Report Type | Description |
|-------------|-------------|
| `certificate` | All certificate data |
| `entryCertificate` | Per-entry certificate data |
| `userCertificate` | Per-user certificate status |
| `entryUserCertificate` | Per-user per-entry certificate status |
| `badge` | All badge data |
| `userBadge` | Per-user badge status with per-rule progress |
| `userScore` | Leaderboard scores and rankings |
| `userLeadScoring` | Lead scoring data with group assignments |

## 10.2 Generate Report

```bash
curl -X POST "$KALTURA_SCM_URL/report/generate" \
  -H "Authorization: Bearer $KALTURA_KS" \
  -H "Content-Type: application/json" \
  -d '{
    "reportType": "userScore",
    "gameObjectId": "'$LEADERBOARD_ID'"
  }'
```


# 11. Scheduled Game Objects

Automate status transitions for game objects (e.g., enable a leaderboard at event start, disable at event end).

```bash
# Schedule leaderboard to enable at event start
curl -X POST "$KALTURA_SCM_URL/scheduledGameObject/create" \
  -H "Authorization: Bearer $KALTURA_KS" \
  -H "Content-Type: application/json" \
  -d '{
    "gameObjectType": "leaderboard",
    "gameObjectId": "'$LEADERBOARD_ID'",
    "scheduledAction": "enable",
    "scheduledDate": "2025-06-01T09:00:00Z"
  }'

# Schedule leaderboard to disable at event end
curl -X POST "$KALTURA_SCM_URL/scheduledGameObject/create" \
  -H "Authorization: Bearer $KALTURA_KS" \
  -H "Content-Type: application/json" \
  -d '{
    "gameObjectType": "leaderboard",
    "gameObjectId": "'$LEADERBOARD_ID'",
    "scheduledAction": "disable",
    "scheduledDate": "2025-06-03T18:00:00Z"
  }'

# List scheduled transitions
curl -X POST "$KALTURA_SCM_URL/scheduledGameObject/list" \
  -H "Authorization: Bearer $KALTURA_KS" \
  -H "Content-Type: application/json" \
  -d '{"pager": {"pageSize": 10, "pageIndex": 1}}'

# Delete scheduled transition
curl -X POST "$KALTURA_SCM_URL/scheduledGameObject/delete" \
  -H "Authorization: Bearer $KALTURA_KS" \
  -H "Content-Type: application/json" \
  -d '{"id": "'$SCHEDULED_ID'"}'
```


# 12. Error Handling

## 12.1 Common Errors

| Error | Cause | Resolution |
|-------|-------|------------|
| 401 Unauthorized | Invalid or expired KS | Generate a new ADMIN KS |
| 403 Forbidden | KS lacks `GAME_MANAGE` permission | Ensure the KS role includes `GAME_MANAGE` |
| 404 Not Found | Invalid game object ID | Verify the ID with a `list` call |
| 400 Bad Request | Missing required fields | Include all required fields for the endpoint |

## 12.2 Permission Errors

Read operations (`list`, `get`, `userScore/list`) require `GAME_BASE`.
Write operations (`create`, `update`, `delete`) require `GAME_MANAGE`.

If Game Services is not enabled for your partner account, all endpoints return 403. Enable via Kaltura Admin Console.

## 12.3 Standard List Filters

All `list` endpoints support these filter fields:

| Field | Type | Description |
|-------|------|-------------|
| `idIn` | string[] | Filter by specific IDs |
| `updatedAtGreaterThan` | ISO 8601 | Filter by updated date range |
| `updatedAtLessThan` | ISO 8601 | Filter by updated date range |
| `createdAtGreaterThan` | ISO 8601 | Filter by created date range |
| `createdAtLessThan` | ISO 8601 | Filter by created date range |
| `orderBy` | string | Sort field and direction |
| `pager` | object | `{pageSize, pageIndex}` for pagination |


# 13. Common Integration Patterns

## 13.1 Virtual Conference Engagement Program

Set up a complete gamification program for a multi-day virtual conference.

```bash
# 1. Create leaderboard (scheduled)
LEADERBOARD=$(curl -s -X POST "$KALTURA_SCM_URL/leaderboard/create" \
  -H "Authorization: Bearer $KALTURA_KS" \
  -H "Content-Type: application/json" \
  -d '{
    "objectType": "Leaderboard",
    "name": "Conference 2025",
    "status": "scheduled",
    "startDate": "2025-06-01T09:00:00Z",
    "endDate": "2025-06-03T18:00:00Z",
    "participationPolicy": {
      "userDefaultPolicy": "display",
      "policies": [
        {"policy": "do_not_save", "matchCriteria": "byEmailDomain", "values": ["internal.com"]}
      ]
    },
    "subLeaderboards": [{"name": "By Country", "filterPaths": ["country"], "id": 0}],
    "virtualEventIds": ["$VIRTUAL_EVENT_ID"]
  }' | jq -r '.id')

# 2. Create rules
# Viewership: 10 pts per 60 sec watched, max 100 per session
curl -s -X POST "$KALTURA_SCM_URL/rule/create" \
  -H "Authorization: Bearer $KALTURA_KS" \
  -H "Content-Type: application/json" \
  -d '{
    "gameObjectType": "leaderboard",
    "gameObjectId": "'$LEADERBOARD'",
    "name": "Watch sessions",
    "conditions": [{"fact": "eventType", "operator": "equal", "value": "viewPeriod"}],
    "type": "sum",
    "mode": "distribute_points",
    "metric": "playTime",
    "groupBy": "kuserId,entryId",
    "goal": "60",
    "points": "10",
    "maxPoints": "100"
  }'

# Polls: 25 pts per poll answered
curl -s -X POST "$KALTURA_SCM_URL/rule/create" \
  -H "Authorization: Bearer $KALTURA_KS" \
  -H "Content-Type: application/json" \
  -d '{
    "gameObjectType": "leaderboard",
    "gameObjectId": "'$LEADERBOARD'",
    "name": "Answer polls",
    "conditions": [{"fact": "eventType", "operator": "equal", "value": "pollAnswered"}],
    "type": "count",
    "mode": "distribute_points",
    "metric": "pollId",
    "groupBy": "kuserId",
    "goal": "1",
    "points": "25",
    "maxPoints": "unlimited"
  }'

# Chat: 5 pts per message, max 50
curl -s -X POST "$KALTURA_SCM_URL/rule/create" \
  -H "Authorization: Bearer $KALTURA_KS" \
  -H "Content-Type: application/json" \
  -d '{
    "gameObjectType": "leaderboard",
    "gameObjectId": "'$LEADERBOARD'",
    "name": "Chat messages",
    "conditions": [{"fact": "eventType", "operator": "equal", "value": "comment"}],
    "type": "count",
    "mode": "distribute_points",
    "metric": "comment",
    "groupBy": "kuserId",
    "goal": "1",
    "points": "5",
    "maxPoints": "50"
  }'

# 3. Create badges
curl -s -X POST "$KALTURA_SCM_URL/badge/create" \
  -H "Authorization: Bearer $KALTURA_KS" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Power Attendee",
    "description": "Watch 10 sessions",
    "virtualEventIds": ["$VIRTUAL_EVENT_ID"],
    "participationPolicy": {"userDefaultPolicy": "display", "policies": []},
    "rules": [{
      "name": "Watch 10 unique sessions",
      "conditions": [{"fact": "eventType", "operator": "equal", "value": "viewPeriod"}],
      "type": "countUnique",
      "metric": "entryId",
      "groupBy": "kuserId",
      "goal": "10",
      "points": "1",
      "maxPoints": "1"
    }]
  }'

# 4. Enable leaderboard when event starts
curl -s -X POST "$KALTURA_SCM_URL/leaderboard/update" \
  -H "Authorization: Bearer $KALTURA_KS" \
  -H "Content-Type: application/json" \
  -d '{"id": "'$LEADERBOARD'", "status": "enabled"}'
```

## 13.2 Partner Training Certification

Set up tiered certification with PDF certificates.

```bash
# 1. Create certificate with PDF template
CERT=$(curl -s -X POST "$KALTURA_SCM_URL/certificate/create" \
  -H "Authorization: Bearer $KALTURA_KS" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Partner Certified Developer",
    "description": "Complete all training modules",
    "status": "disabled",
    "certificateEligibility": "once",
    "certifiedCreditsThreshold": 3,
    "host": "https://training.example.com",
    "participationPolicy": {"userDefaultPolicy": "display", "policies": []},
    "outputFileConfiguration": {
      "outputFileElements": [
        {"url": "https://cfvod.kaltura.com/p/'$PARTNER_ID'/thumbnail/entry_id/'$BG_ENTRY'/width/1397/height/1080"},
        {"textElementType": "userFullName", "fontSize": 30, "y": 440},
        {"textElementType": "certificationDate", "fontSize": 18, "x": 695, "y": 636},
        {"textElementType": "credits", "fontSize": 23, "x": 1060, "y": 699}
      ]
    }
  }' | jq -r '.id')

# 2. Create viewership rule for the certificate
RULE=$(curl -s -X POST "$KALTURA_SCM_URL/rule/create" \
  -H "Authorization: Bearer $KALTURA_KS" \
  -H "Content-Type: application/json" \
  -d '{
    "gameObjectType": "certificate",
    "gameObjectId": "'$CERT'",
    "name": "Watch training module",
    "conditions": [{"fact": "eventType", "operator": "equal", "value": "viewPeriod"}],
    "type": "sum",
    "mode": "distribute_points",
    "metric": "playTime",
    "groupBy": "kuserId,entryId",
    "goal": "60",
    "points": "1",
    "maxPoints": "unlimited",
    "reportFormat": "default"
  }' | jq -r '.id')

# 3. Enable certificate with credits mapping
curl -s -X POST "$KALTURA_SCM_URL/certificate/update" \
  -H "Authorization: Bearer $KALTURA_KS" \
  -H "Content-Type: application/json" \
  -d '{
    "id": "'$CERT'",
    "status": "enabled",
    "creditsMapping": "credits,'$RULE'\n10.0,1\n11.5,2"
  }'
```

## 13.3 Post-Event Lead Scoring

Score attendees and export hot leads to CRM.

```bash
# 1. Create lead scoring profile
LEAD=$(curl -s -X POST "$KALTURA_SCM_URL/leadScoring/create" \
  -H "Authorization: Bearer $KALTURA_KS" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Event Lead Scoring",
    "status": "scheduled",
    "startDate": "2025-06-01T00:00:00Z",
    "endDate": "2025-06-03T23:59:59Z",
    "participationPolicy": {
      "userDefaultPolicy": "display",
      "policies": [{"policy": "do_not_save", "matchCriteria": "byEmailDomain", "values": ["internal.com"]}]
    },
    "scoreGroups": [
      {"name": "Top", "range": [1000, 99999]},
      {"name": "Mid", "range": [500, 999]},
      {"name": "Low", "range": [0, 499]}
    ],
    "virtualEventIds": ["$VIRTUAL_EVENT_ID"]
  }' | jq -r '.id')

# 2. Create rules across engagement categories
# Registration
curl -s -X POST "$KALTURA_SCM_URL/rule/create" \
  -H "Authorization: Bearer $KALTURA_KS" \
  -H "Content-Type: application/json" \
  -d '{
    "gameObjectType": "leadScoring",
    "gameObjectId": "'$LEAD'",
    "name": "Registration",
    "conditions": [{"fact": "eventType", "operator": "equal", "value": "registered"}],
    "type": "count",
    "mode": "distribute_points",
    "metric": "kuserId",
    "groupBy": "kuserId",
    "goal": "1",
    "points": "50",
    "maxPoints": "50"
  }'

# Viewership
curl -s -X POST "$KALTURA_SCM_URL/rule/create" \
  -H "Authorization: Bearer $KALTURA_KS" \
  -H "Content-Type: application/json" \
  -d '{
    "gameObjectType": "leadScoring",
    "gameObjectId": "'$LEAD'",
    "name": "Session viewership",
    "conditions": [{"fact": "eventType", "operator": "equal", "value": "viewPeriod"}],
    "type": "sum",
    "mode": "distribute_points",
    "metric": "playTime",
    "groupBy": "kuserId,entryId",
    "goal": "60",
    "points": "10",
    "maxPoints": "unlimited"
  }'

# 3. After event — generate lead scoring report
curl -s -X POST "$KALTURA_SCM_URL/report/generate" \
  -H "Authorization: Bearer $KALTURA_KS" \
  -H "Content-Type: application/json" \
  -d '{"reportType": "userLeadScoring", "gameObjectId": "'$LEAD'"}'

# 4. List user lead scores
curl -s -X POST "$KALTURA_SCM_URL/userLeadScoring/list" \
  -H "Authorization: Bearer $KALTURA_KS" \
  -H "Content-Type: application/json" \
  -d '{"gameObjectId": "'$LEAD'", "pager": {"pageSize": 100, "pageIndex": 1}}'
```

## 13.4 Flash Challenges with Scheduled Transitions

Create time-limited challenges that auto-enable and auto-disable.

```bash
# Create challenge leaderboard
CHALLENGE=$(curl -s -X POST "$KALTURA_SCM_URL/leaderboard/create" \
  -H "Authorization: Bearer $KALTURA_KS" \
  -H "Content-Type: application/json" \
  -d '{
    "objectType": "Leaderboard",
    "name": "Keynote Flash Challenge",
    "status": "scheduled",
    "startDate": "2025-06-01T14:00:00Z",
    "endDate": "2025-06-01T15:00:00Z",
    "participationPolicy": {"userDefaultPolicy": "display", "policies": []},
    "virtualEventIds": ["$VIRTUAL_EVENT_ID"]
  }' | jq -r '.id')

# Double points for this challenge
curl -s -X POST "$KALTURA_SCM_URL/rule/create" \
  -H "Authorization: Bearer $KALTURA_KS" \
  -H "Content-Type: application/json" \
  -d '{
    "gameObjectType": "leaderboard",
    "gameObjectId": "'$CHALLENGE'",
    "name": "Speed polls (double points)",
    "conditions": [{"fact": "eventType", "operator": "equal", "value": "pollAnswered"}],
    "type": "count",
    "mode": "distribute_points",
    "metric": "pollId",
    "groupBy": "kuserId",
    "goal": "1",
    "points": "50",
    "maxPoints": "unlimited"
  }'

# Schedule auto-enable at challenge start
curl -s -X POST "$KALTURA_SCM_URL/scheduledGameObject/create" \
  -H "Authorization: Bearer $KALTURA_KS" \
  -H "Content-Type: application/json" \
  -d '{
    "gameObjectType": "leaderboard",
    "gameObjectId": "'$CHALLENGE'",
    "scheduledAction": "enable",
    "scheduledDate": "2025-06-01T14:00:00Z"
  }'

# Schedule auto-disable at challenge end
curl -s -X POST "$KALTURA_SCM_URL/scheduledGameObject/create" \
  -H "Authorization: Bearer $KALTURA_KS" \
  -H "Content-Type: application/json" \
  -d '{
    "gameObjectType": "leaderboard",
    "gameObjectId": "'$CHALLENGE'",
    "scheduledAction": "disable",
    "scheduledDate": "2025-06-01T15:00:00Z"
  }'
```


# 14. Best Practices

**Rule design — use groupBy wisely.** `groupBy: "kuserId"` accumulates across all entries. `groupBy: "kuserId,entryId"` accumulates per entry per user — use this for "watch X minutes per session" rules where you want per-session caps.

**Set maxPoints caps.** Without `maxPoints`, users can accumulate unlimited points from a single rule. Use caps to prevent gaming: `"maxPoints": "100"` per session for viewership, `"maxPoints": "50"` for chat.

**Sub-rule ordering.** Sub-rules execute before the root rule evaluates. Use `block_root_rule_if_exhausted` to cap total accumulation, and `block_root_rule_while_in_progress` for prerequisite logic.

**Status lifecycle.** Create game objects as `scheduled`, enable rules, then update to `enabled` when the event starts. Use `scheduledGameObject` for automated transitions.

**Event scoping.** Scope rules to specific events or content using `virtualEventId` and `categories` conditions. Without scoping, rules apply to all partner content.

**Certificate PDF design.** Test the PDF template with a real certificate before the event. The background image URL must be publicly accessible. Text overlay positions (`x`, `y`) are in pixels from the top-left corner.

**Participation policies.** Always exclude internal staff from leaderboards and lead scoring via `byEmailDomain` with policy `do_not_save`. Speakers can participate but should be hidden via `do_not_display`.

**External events.** Use `delta` mode for incremental score additions (booth visits, check-ins). Use `upsert` mode when the external system provides final scores (exam results, external quiz platforms).


# 15. Related Guides

| Guide | Integration |
|-------|-------------|
| [Events Platform](KALTURA_EVENTS_PLATFORM_API.md) | `virtualEventIds` scope game objects to events; category IDs in rule conditions |
| [User Profile](KALTURA_USER_PROFILE_API.md) | User properties power sub-leaderboards via `filterPaths[]`; user metadata enriches reports |
| [Analytics Reports](KALTURA_ANALYTICS_REPORTS_API.md) | User Reactions Report (ID 4021) for granular per-user engagement data |
| [Events Collection](KALTURA_ANALYTICS_EVENTS_COLLECTION_API.md) | Playback events (`viewPeriod`) feed leaderboard and badge rules |
| [Messaging](KALTURA_MESSAGING_API.md) | Certificate download email delivery; winner notification emails |
| [Webhooks](KALTURA_WEBHOOKS_API.md) | Event notifications on gamification state changes |
| [Session Guide](KALTURA_SESSION_GUIDE.md) | Admin KS as Bearer token; `GAME_BASE`/`GAME_MANAGE` permissions |
| [Metadata & Captions](KALTURA_METADATA_AND_CAPTIONS_API.md) | `metadataProfileId` on certificates for PDF generation context |
| [Categories & Access Control](KALTURA_CATEGORIES_AND_ACCESS_CONTROL_API.md) | Category IDs in rule conditions for content scoping |

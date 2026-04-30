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

<!-- Sections: 1.When to Use | 2.Prerequisites | 3.Authentication | 4.Leaderboard Entity & CRUD | 5.Participation Policies | 6.Rules Engine | 7.Badges | 8.Certificates | 9.Lead Scoring | 10.User Scores & Progress | 11.External Events & CSV Import | 12.Reports | 13.Scheduled Game Objects | 14.Error Handling | 15.Common Integration Patterns | 1.Create leaderboard (scheduled) | 2.Create rules | 3.Create badges | 4.Enable leaderboard when event starts | 1.Create certificate with PDF template | 2.Create viewership rule for the certificate | 3.Enable certificate with credits mapping | 1.Create lead scoring profile | 2.Create rules across engagement categories | 3.After event — generate lead scoring report | 4.List user lead scores | 1.Create CPE certificate with per-entry eligibility | 2.Create viewership rule scoped to accredited sessions category | 3.Enable certificate with credits mapping (watch-time to CPE credit tiers) | 4.Generate per-entry certificate report for accreditation submission | 1.Create external rule on the leaderboard | 2.Import scores — delta mode (add to existing scores) | 3.Import scores — upsert mode (replace existing scores) | 1.Create leaderboard rule scoped to sponsor category | 2.Track sponsor booth page visit via analytics.trackEvent (API v3) | 3.Pull per-sponsor engagement data via report.getTable (API v3) | 4.Generate per-sponsor gamification report | 1.Create 90-day onboarding leaderboard | 2.Create module completion rule (scoped to IT Security category) | 3.Create "Security Certified" milestone badge | 4.Create HR-branded onboarding completion certificate | 5.Generate onboarding completion report for HR records | 1.Create "API Expert" badge with content + quiz requirements | 2.Query per-customer badge progress | 3.Generate badge completion report for CRM export | 1.Create leaderboard with department-based sub-leaderboards | 2.Create "Top Department" team badge | 3.Query team standings (sub-leaderboard rankings) | 16.Best Practices | 17.Related Guides -->


# 1. When to Use

- **Learning and development teams** driving training completion through leaderboards, badges, and certificates  
- **Event organizers** increasing attendee engagement with real-time scoring and achievement mechanics  
- **HR and compliance departments** issuing verifiable certificates for continuing education credits  
- **Marketing teams** implementing lead scoring based on event participation and content consumption  
- **LMS integrators** connecting gamification data (scores, badges, certificates) to external learning management systems


# 2. Prerequisites

- **KS type:** ADMIN KS (type=2) with `GAME_BASE` (read) and `GAME_MANAGE` (write) permissions  
- **Plugins:** Game Services (SCM) must be enabled on the partner account via Kaltura Admin Console  
- **Session guide:** Generate a KS using `session.start` or `appToken.startSession` (see [Session Guide](KALTURA_SESSION_GUIDE.md))


# 3. Authentication

All requests require an ADMIN KS (type=2) in the `Authorization` header:

```bash
# Set up environment
export KALTURA_SCM_URL="https://scm.nvp1.ovp.kaltura.com/api/v1"
export KALTURA_KS="your_kaltura_session"
```

Generate an ADMIN KS via `session.start` (see [Session Guide](KALTURA_SESSION_GUIDE.md)) or `appToken.startSession` (see [AppTokens Guide](KALTURA_APPTOKENS_API.md)).

## 3.1 Regional Endpoints

| Region | Base URL |
|--------|----------|
| US Production | `https://scm.nvp1.ovp.kaltura.com/api/v1/` |
| EU (France) | `https://scm.frp2.ovp.kaltura.com/api/v1/` |
| EU (Ireland) | `https://scm.irp2.ovp.kaltura.com/api/v1/` |
| APAC (Singapore) | `https://scm.sgp2.ovp.kaltura.com/api/v1/` |
| APAC (Sydney) | `https://scm.syp2.ovp.kaltura.com/api/v1/` |
| Canada | `https://scm.cap2.ovp.kaltura.com/api/v1/` |

## 3.2 Permissions

| Permission | Description |
|------------|-------------|
| `GAME_BASE` | Read operations — list scores, get badges, view reports |
| `GAME_MANAGE` | Write operations — create leaderboards, define rules, manage certificates |

Enable Game Services for your partner account in Kaltura Admin Console.


# 4. Leaderboard Entity & CRUD

Leaderboards track user scores and rank users. They are scoped to virtual events via `virtualEventIds`.

## 4.1 Leaderboard Entity

| Field | Type | Description |
|-------|------|-------------|
| `id` | string | Auto-generated unique identifier (read-only) |
| `name` | string | Leaderboard display name |
| `description` | string | Description text |
| `status` | string | `scheduled`, `enabled`, `disabled` |
| `startDate` | ISO 8601 | Scoring window start |
| `endDate` | ISO 8601 | Scoring window end |
| `virtualEventIds` | int[] | Virtual event IDs this leaderboard applies to |
| `participationPolicy` | object | Controls user visibility (see section 5) |
| `subLeaderboards` | array | Segments for team/regional rankings (see section 4.4) |

**Status lifecycle:** `scheduled` → `enabled` → `disabled`. Create leaderboards as `scheduled`, then update to `enabled` when the event starts.

## 4.2 Create Leaderboard

**Parameters**

| Parameter | Type | Required | Description |
|---|---|---|---|
| `objectType` | string | Yes | Always `"Leaderboard"` |
| `name` | string | Yes | Leaderboard display name |
| `description` | string | No | Description text |
| `status` | string | Yes | Initial status: `"scheduled"`, `"enabled"`, or `"disabled"` |
| `startDate` | string | Yes | Scoring window start in ISO 8601 format |
| `endDate` | string | Yes | Scoring window end in ISO 8601 format |
| `virtualEventIds` | array | Yes | Array of virtual event ID strings this leaderboard applies to |
| `participationPolicy` | object | No | Controls user visibility (see section 5). Default: all users visible |
| `participationPolicy.userDefaultPolicy` | string | No | Default policy: `"display"`, `"do_not_display"`, or `"do_not_save"` |
| `participationPolicy.policies` | array | No | Array of policy override objects with `policy`, `matchCriteria`, and `values` |
| `subLeaderboards` | array | No | Segment definitions for team/regional rankings (see section 4.4) |

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

**Response**

```json
{
  "id": "lb_abc123",
  "name": "Conference Engagement",
  "description": "Points for session attendance, polls, and chat",
  "status": "scheduled",
  "startDate": "2025-06-01T09:00:00.000Z",
  "endDate": "2025-06-03T18:00:00.000Z",
  "participationPolicy": {
    "userDefaultPolicy": "display",
    "policies": []
  },
  "virtualEventIds": ["12345"],
  "createdAt": "2025-05-20T10:00:00.000Z",
  "updatedAt": "2025-05-20T10:00:00.000Z"
}
```

## 4.3 Get, Update, List, Delete

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

## 4.4 Sub-Leaderboards

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


# 5. Participation Policies

Participation policies control user visibility across all game objects (leaderboards, badges, certificates, lead scoring).

| Policy | Description |
|--------|-------------|
| `display` | User participates; progress visible to other users |
| `do_not_display` | User participates; progress visible only to admins |
| `do_not_save` | User does not participate; no data collected |

## 5.1 Matching Criteria

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


# 6. Rules Engine

The rules engine evaluates analytics events against configured rules and triggers scoring, achievement, and certification actions. Rules are the core abstraction that ties all gamification features together.

## 6.1 Rule Entity

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

## 6.2 Rule Types

| Type | Description | Example |
|------|-------------|---------|
| `sum` | Sum the metric value across events | Sum `playTime` — when total reaches `goal` seconds, distribute points |
| `count` | Count matching events | Count `pollAnswered` events — when count reaches `goal`, distribute points |
| `countUnique` | Count unique metric values | Count unique `entryId` values — "watch N different sessions" |
| `countBoolean` | Count events where metric is truthy | Count events where `like` is true |
| `external` | Accept external/3rd-party scores | Metric must be `"score"`; points come from the event's score field |
| `override` | Replace existing score entirely | Override with new value instead of accumulating |

## 6.3 Rule Modes

| Mode | Description |
|------|-------------|
| `distribute_points` | When goal is met, distribute `points` to the user's score |
| `dont_distribute_points` | Track progress without adding to score (for badge rules that track activity separately) |
| `block_root_rule_while_in_progress` | Sub-rule must complete before the root rule can accumulate |
| `block_root_rule_if_exhausted` | Once this sub-rule reaches its max, the root rule stops accumulating |

## 6.4 Condition Operators

`equal`, `notEqual`, `lessThan`, `greaterThan`, `in`, `notIn`, `contains`, `doesNotContain`

## 6.5 Condition Facts (Event Fields)

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

## 6.6 Analytics Events That Feed Rules

| Source | Event Types | Example Rules |
|--------|------------|---------------|
| Playback | `viewPeriod` | Watch duration, per-session completion |
| In-Video Quizzes | `quizSubmitted` | Quiz completion, first-to-complete bonus |
| Chat & Collaboration | `pollAnswered`, `comment`, `like`/`upvote` | Poll participation, chat engagement |
| Live Q&A | `questionAsked`, `questionPromoted` | Q&A participation |
| KME | `participated`, `quizAnswer` | Meeting attendance |
| Registration | `registered` | Event registration, first-to-register bonus |

## 6.7 Rule CRUD

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

## 6.8 Sub-Rules

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


# 7. Badges

Badges reward users for completing a set of activity rules. A user either has a badge or does not — they are binary achievements.

## 7.1 Badge Entity

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

## 7.2 Badge Achievement Lifecycle

1. Analytics events are evaluated against each badge's rules
2. Per-user per-rule progress is tracked in `rulesData[]` (each has `id`, `progress`, `completed`)
3. When **all** rules have `completed: true`, badge status updates to `ACHIEVED` with `achievedTimestamp`

## 7.3 Badge CRUD

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

## 7.4 User Badge Progress

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


# 8. Certificates

Certificates issue PDF credentials to users who complete required activities. They use the same rules engine as badges, with added PDF generation configuration.

## 8.1 Certificate Entity

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

## 8.2 PDF Template (outputFileConfiguration)

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

## 8.3 Credits Mapping

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

## 8.4 Certificate Rules

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

## 8.5 User Certificate Progress

```bash
curl -X POST "$KALTURA_SCM_URL/userCertificateReport/list" \
  -H "Authorization: Bearer $KALTURA_KS" \
  -H "Content-Type: application/json" \
  -d '{"gameObjectId": "'$CERT_ID'", "pager": {"pageSize": 100, "pageIndex": 1}}'
```


# 9. Lead Scoring

Lead scoring tracks user engagement during events and segments users by likelihood to convert. Two parallel segmentation systems run simultaneously.

## 9.1 Percentage Groups (Relative Ranking)

| Group | Range | Description |
|-------|-------|-------------|
| Hot Leads | 80-100% | Top 20% of participants |
| Warm Leads | 50-79% | Middle 30% |
| Cold Leads | 0-49% | Bottom 50% |

## 9.2 Score Groups (Absolute Thresholds)

| Group | Range |
|-------|-------|
| Top Score Leads | 1000+ |
| Mid Score Leads | 500-999 |
| Low Score Leads | 0-499 |

## 9.3 Lead Scoring CRUD

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

## 9.4 User Lead Scoring Data

```bash
curl -X POST "$KALTURA_SCM_URL/userLeadScoring/list" \
  -H "Authorization: Bearer $KALTURA_KS" \
  -H "Content-Type: application/json" \
  -d '{"gameObjectId": "'$LEAD_SCORING_ID'", "pager": {"pageSize": 100, "pageIndex": 1}}'
```

## 9.5 Lead Scoring Reports

**Summary report:** Percentage Group Name, Range, Number of Users, Average Score, Average Engagement Score, Average User Profile Score.

**Detailed report:** Absolute Rank, Total Lead Score, User Name, Email, S-Group (absolute), Rank within S-Group, P-Group (percentage), Rank within P-Group, per-rule-group scores.

Reports are exportable to CRM systems as custom objects.


# 10. User Scores & Progress

## 10.1 Get User Score

**Parameters**

| Parameter | Type | Required | Description |
|---|---|---|---|
| `gameObjectId` | string | Yes | ID of the leaderboard, badge, certificate, or lead scoring profile |
| `userId` | string | Yes | Kaltura user ID to look up |

```bash
curl -X POST "$KALTURA_SCM_URL/userScore/get" \
  -H "Authorization: Bearer $KALTURA_KS" \
  -H "Content-Type: application/json" \
  -d '{"gameObjectId": "'$LEADERBOARD_ID'", "userId": "'$USER_ID'"}'
```

## 10.2 List Scores (Paginated Ranking)

```bash
curl -X POST "$KALTURA_SCM_URL/userScore/list" \
  -H "Authorization: Bearer $KALTURA_KS" \
  -H "Content-Type: application/json" \
  -d '{"gameObjectId": "'$LEADERBOARD_ID'", "pager": {"pageSize": 25, "pageIndex": 1}}'
```

## 10.3 Per-Rule Progress

```bash
curl -X POST "$KALTURA_SCM_URL/userScore/ruleProgress" \
  -H "Authorization: Bearer $KALTURA_KS" \
  -H "Content-Type: application/json" \
  -d '{"gameObjectId": "'$LEADERBOARD_ID'", "userId": "'$USER_ID'"}'
```

## 10.4 Clear Scores

**Parameters**

| Parameter | Type | Required | Description |
|---|---|---|---|
| `gameObjectId` | string | Yes | ID of the leaderboard whose scores should be cleared. Removes all user scores for this leaderboard |

```bash
curl -X POST "$KALTURA_SCM_URL/userScore/clear" \
  -H "Authorization: Bearer $KALTURA_KS" \
  -H "Content-Type: application/json" \
  -d '{"gameObjectId": "'$LEADERBOARD_ID'"}'
```

## 10.5 API v3 Game Plugin

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


# 11. External Events & CSV Import

Import scores from external systems (booth scans, external quiz platforms, physical activities) via CSV upload.

**Parameters**

| Parameter | Type | Required | Description |
|---|---|---|---|
| `eventAction` | string | Yes | `"delta"` (add to existing score) or `"upsert"` (replace existing score) |
| `csvFile` | file | Yes | CSV file upload. Must include `userId`, `score`, and `eventType` columns, plus any context fields referenced by rule conditions |

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


# 12. Reports

Generate reports for gamification data export.

## 12.1 Report Types

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

## 12.2 Generate Report

**Parameters**

| Parameter | Type | Required | Description |
|---|---|---|---|
| `reportType` | string | Yes | One of: `certificate`, `entryCertificate`, `userCertificate`, `entryUserCertificate`, `badge`, `userBadge`, `userScore`, `userLeadScoring` |
| `gameObjectId` | string | Yes | ID of the game object to generate the report for |

```bash
curl -X POST "$KALTURA_SCM_URL/report/generate" \
  -H "Authorization: Bearer $KALTURA_KS" \
  -H "Content-Type: application/json" \
  -d '{
    "reportType": "userScore",
    "gameObjectId": "'$LEADERBOARD_ID'"
  }'
```


# 13. Scheduled Game Objects

Automate status transitions for game objects (e.g., enable a leaderboard at event start, disable at event end).

**Parameters (create)**

| Parameter | Type | Required | Description |
|---|---|---|---|
| `gameObjectType` | string | Yes | Type of game object: `"leaderboard"`, `"certificate"`, `"badge"`, `"leadScoring"` |
| `gameObjectId` | string | Yes | ID of the game object to schedule |
| `scheduledAction` | string | Yes | Action to perform: `"enable"` or `"disable"` |
| `scheduledDate` | string | Yes | When to execute the action, in ISO 8601 format |

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


# 14. Error Handling

## 14.1 Common Errors

| Error | Cause | Resolution |
|-------|-------|------------|
| 401 Unauthorized | Invalid or expired KS | Generate a new ADMIN KS |
| 403 Forbidden | KS lacks `GAME_MANAGE` permission | Ensure the KS role includes `GAME_MANAGE` |
| 404 Not Found | Invalid game object ID | Verify the ID with a `list` call |
| 400 Bad Request | Missing required fields | Include all required fields for the endpoint |

## 14.2 Permission Errors

Read operations (`list`, `get`, `userScore/list`) require `GAME_BASE`.
Write operations (`create`, `update`, `delete`) require `GAME_MANAGE`.

If Game Services is not enabled for your partner account, all endpoints return 403. Enable via Kaltura Admin Console.

## 14.3 Standard List Filters

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


# 15. Common Integration Patterns

## 15.1 Virtual Conference Engagement Program

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

## 15.2 Partner Training Certification

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

## 15.3 Post-Event Lead Scoring

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

## 15.4 Flash Challenges with Scheduled Transitions

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

## 15.5 CPE / Continuing Education Credits

Track Continuing Professional Education (CPE) credits per session for accreditation bodies (medical, legal, accounting). Each session awards credits based on verified watch time, and a branded PDF certificate is generated for submission to the accreditation authority.

**Workflow:**
1. Create a certificate with `externalId` (accreditation program ID), `certificateEligibility: "perEntry"` (one certificate per session per user), and `certifiedCreditsThreshold` (minimum credits for certification)
2. Create a `sum` rule on `viewPeriod` scoped to a session category via a `categories` condition, so only content in that category contributes credits
3. Configure `creditsMapping` to map watch-time thresholds to credit values (e.g., 60 minutes = 1.0 credit, 90 minutes = 1.5 credits)
4. Set participation policies to exclude speakers from earning credits
5. Generate per-entry certificates for submission to the accreditation body

```bash
# 1. Create CPE certificate with per-entry eligibility
CERT=$(curl -s -X POST "$KALTURA_SCM_URL/certificate/create" \
  -H "Authorization: Bearer $KALTURA_KS" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "CPE Credit Certificate",
    "description": "Continuing Professional Education — 1 credit per qualifying session",
    "status": "disabled",
    "externalId": "NASBA-PROG-2025-4821",
    "certificateEligibility": "perEntry",
    "certifiedCreditsThreshold": 1,
    "host": "https://training.events.kaltura.com",
    "participationPolicy": {
      "userDefaultPolicy": "display",
      "policies": [
        {"policy": "do_not_save", "matchCriteria": "byGroup", "values": ["speakers"]}
      ]
    },
    "outputFileConfiguration": {
      "outputFileElements": [
        {"url": "https://cfvod.kaltura.com/p/'$PARTNER_ID'/thumbnail/entry_id/'$BG_ENTRY_ID'/width/1397/height/1080"},
        {"textElementType": "userFullName", "fontSize": 30, "y": 440},
        {"textElementType": "entryName", "fontSize": 30, "y": 570},
        {"textElementType": "credits", "fontSize": 23, "x": 1060, "y": 699},
        {"textElementType": "certificationDate", "fontSize": 18, "x": 695, "y": 636}
      ]
    }
  }' | jq -r '.id')

# 2. Create viewership rule scoped to accredited sessions category
RULE=$(curl -s -X POST "$KALTURA_SCM_URL/rule/create" \
  -H "Authorization: Bearer $KALTURA_KS" \
  -H "Content-Type: application/json" \
  -d '{
    "gameObjectType": "certificate",
    "gameObjectId": "'$CERT'",
    "name": "CPE session watch time",
    "conditions": [
      {"fact": "eventType", "operator": "equal", "value": "viewPeriod"},
      {"fact": "categories", "operator": "in", "value": "'$CATEGORY_ID'"}
    ],
    "type": "sum",
    "mode": "distribute_points",
    "metric": "playTime",
    "groupBy": "kuserId,entryId",
    "goal": "60",
    "points": "1",
    "maxPoints": "unlimited",
    "reportFormat": "in_minutes"
  }' | jq -r '.id')

# 3. Enable certificate with credits mapping (watch-time to CPE credit tiers)
curl -s -X POST "$KALTURA_SCM_URL/certificate/update" \
  -H "Authorization: Bearer $KALTURA_KS" \
  -H "Content-Type: application/json" \
  -d '{
    "id": "'$CERT'",
    "status": "enabled",
    "creditsMapping": "credits,'$RULE'\n1.0,1\n1.5,2\n2.0,3"
  }'

# 4. Generate per-entry certificate report for accreditation submission
curl -s -X POST "$KALTURA_SCM_URL/report/generate" \
  -H "Authorization: Bearer $KALTURA_KS" \
  -H "Content-Type: application/json" \
  -d '{"reportType": "entryCertificate", "gameObjectId": "'$CERT'"}'
```

The `categories` condition in the rule ensures only sessions within the accredited category contribute watch time. The `certificateEligibility: "perEntry"` setting generates a separate certificate per session, so each CPE credit maps to a specific session for audit purposes.

> **See also:** [Events Platform](KALTURA_EVENTS_PLATFORM_API.md) for virtual event and session category setup, [Custom Metadata](KALTURA_CUSTOM_METADATA_API.md) for attaching accreditation metadata to entries.

## 15.6 External Score Import (Hybrid Events)

Hybrid events combine in-person and digital activities on a single leaderboard. Booth visits, physical check-ins, and external quiz platforms produce scores outside the Kaltura analytics pipeline. Import those scores via CSV so they appear alongside digital engagement on the same leaderboard.

**Workflow:**
1. Create an `external` type rule (metric: `"score"`) on the leaderboard so it accepts imported events
2. Prepare a CSV file with `userId`, `score`, and `eventType` columns
3. Upload via `event/sendExternalEventsFromCSV` with `delta` mode (add to existing) or `upsert` mode (replace existing)
4. Verify imported scores in `userScore/list`

```bash
# 1. Create external rule on the leaderboard
curl -s -X POST "$KALTURA_SCM_URL/rule/create" \
  -H "Authorization: Bearer $KALTURA_KS" \
  -H "Content-Type: application/json" \
  -d '{
    "gameObjectType": "leaderboard",
    "gameObjectId": "'$LEADERBOARD_ID'",
    "name": "Booth visits and physical activities",
    "conditions": [{"fact": "eventType", "operator": "equal", "value": "boothVisit"}],
    "type": "external",
    "mode": "distribute_points",
    "metric": "score",
    "groupBy": "kuserId",
    "goal": "1",
    "points": "score",
    "maxPoints": "unlimited"
  }'

# 2. Import scores — delta mode (add to existing scores)
# CSV columns: userId, score, eventType
curl -s -X POST "$KALTURA_SCM_URL/event/sendExternalEventsFromCSV" \
  -H "Authorization: Bearer $KALTURA_KS" \
  -F "eventAction=delta" \
  -F "csvFile=@-;filename=scores.csv" <<'CSVEOF'
userId,score,eventType
user1@example.com,50,boothVisit
user2@example.com,75,boothVisit
user3@example.com,100,boothVisit
CSVEOF

# 3. Import scores — upsert mode (replace existing scores)
# Use upsert when the external system provides final scores (e.g., quiz retake)
curl -s -X POST "$KALTURA_SCM_URL/event/sendExternalEventsFromCSV" \
  -H "Authorization: Bearer $KALTURA_KS" \
  -F "eventAction=upsert" \
  -F "csvFile=@-;filename=quiz_finals.csv" <<'CSVEOF'
userId,score,eventType
user1@example.com,90,boothVisit
user2@example.com,85,boothVisit
CSVEOF
```

Use `delta` for incremental activities where each occurrence adds points (booth scans, check-ins). Use `upsert` when the external system provides a corrected or final score that should replace the previous value (exam retakes, final quiz grades).

> **See also:** Section 11 (External Events & CSV Import) for CSV format details, [Analytics Reports](KALTURA_ANALYTICS_REPORTS_API.md) for verifying imported data in analytics.

## 15.7 Sponsor Engagement Tracking & ROI Reports

Event sponsors need measurable engagement data to justify renewal. Organize sponsor content by category, track booth page visits via analytics events, score engagement on a per-sponsor leaderboard, and generate per-sponsor reports.

**Workflow:**
1. Create a category per sponsor using the [Categories & Entitlements API](KALTURA_CATEGORIES_AND_ENTITLEMENTS_API.md)
2. Create leaderboard rules with `categories` conditions scoping to each sponsor's category
3. Track booth page engagement via `analytics.trackEvent` (eventType 10003 for page loads)
4. Pull per-sponsor analytics via `report.getTable` with `categoriesIdsIn` filter
5. Generate per-sponsor gamification reports

```bash
# 1. Create leaderboard rule scoped to sponsor category
curl -s -X POST "$KALTURA_SCM_URL/rule/create" \
  -H "Authorization: Bearer $KALTURA_KS" \
  -H "Content-Type: application/json" \
  -d '{
    "gameObjectType": "leaderboard",
    "gameObjectId": "'$LEADERBOARD_ID'",
    "name": "Sponsor booth engagement",
    "conditions": [
      {"fact": "eventType", "operator": "equal", "value": "viewPeriod"},
      {"fact": "categories", "operator": "in", "value": "'$SPONSOR_CATEGORY_ID'"}
    ],
    "type": "sum",
    "mode": "distribute_points",
    "metric": "playTime",
    "groupBy": "kuserId,entryId",
    "goal": "30",
    "points": "15",
    "maxPoints": "150"
  }'

# 2. Track sponsor booth page visit via analytics.trackEvent (API v3)
curl -s -X POST "$KALTURA_SERVICE_URL/service/analytics/action/trackEvent" \
  -d "ks=$KALTURA_KS" \
  -d "format=1" \
  -d "event[objectType]=KalturaStatsEvent" \
  -d "event[eventType]=10003" \
  -d "event[entryId]=$SPONSOR_ENTRY_ID" \
  -d "event[partnerId]=$KALTURA_PARTNER_ID"

# 3. Pull per-sponsor engagement data via report.getTable (API v3)
curl -s -X POST "$KALTURA_SERVICE_URL/service/report/action/getTable" \
  -d "ks=$KALTURA_KS" \
  -d "format=1" \
  -d "reportType=38" \
  -d "reportInputFilter[objectType]=KalturaReportInputFilter" \
  -d "reportInputFilter[fromDate]=$FROM_TIMESTAMP" \
  -d "reportInputFilter[toDate]=$TO_TIMESTAMP" \
  -d "reportInputFilter[categoriesIdsIn]=$SPONSOR_CATEGORY_ID" \
  -d "pager[objectType]=KalturaFilterPager" \
  -d "pager[pageSize]=100" \
  -d "pager[pageIndex]=1"

# 4. Generate per-sponsor gamification report
curl -s -X POST "$KALTURA_SCM_URL/report/generate" \
  -H "Authorization: Bearer $KALTURA_KS" \
  -H "Content-Type: application/json" \
  -d '{"reportType": "userScore", "gameObjectId": "'$LEADERBOARD_ID'"}'
```

The `categories` condition on the rule ensures only content within the sponsor's category contributes engagement points. Combine the gamification `userScore` report with the API v3 `report.getTable` data (reportType 38 = Top Content) to build a comprehensive sponsor ROI package showing both engagement scores and detailed viewing analytics.

> **See also:** [Categories & Entitlements](KALTURA_CATEGORIES_AND_ENTITLEMENTS_API.md) for sponsor category setup, [Events Collection](KALTURA_ANALYTICS_EVENTS_COLLECTION_API.md) for analytics event tracking, [Analytics Reports](KALTURA_ANALYTICS_REPORTS_API.md) for report.getTable usage, [Events Platform](KALTURA_EVENTS_PLATFORM_API.md) for virtual event structure.

## 15.8 Employee Onboarding Gamification

Make employee onboarding engaging with module-based scoring, milestone badges, and a branded completion certificate. HR managers track cohort progress and generate records for compliance.

**Workflow:**
1. Create a leaderboard with a 90-day cohort window (startDate/endDate)
2. Create `sum` rules per onboarding module category (company culture, IT security, benefits)
3. Create milestone badges with inline rules ("Day 1 Done", "Security Certified", "Fully Onboarded")
4. Create a completion certificate with HR-branded PDF template
5. Managers query `userScore/list` for cohort progress and `report/generate` for HR records

```bash
# 1. Create 90-day onboarding leaderboard
ONBOARD_LB=$(curl -s -X POST "$KALTURA_SCM_URL/leaderboard/create" \
  -H "Authorization: Bearer $KALTURA_KS" \
  -H "Content-Type: application/json" \
  -d '{
    "objectType": "Leaderboard",
    "name": "Q2 Onboarding Cohort",
    "description": "New hire onboarding progress — 90-day window",
    "status": "scheduled",
    "startDate": "2025-04-01T00:00:00Z",
    "endDate": "2025-06-30T23:59:59Z",
    "participationPolicy": {"userDefaultPolicy": "display", "policies": []},
    "virtualEventIds": ["$VIRTUAL_EVENT_ID"]
  }' | jq -r '.id')

# 2. Create module completion rule (scoped to IT Security category)
curl -s -X POST "$KALTURA_SCM_URL/rule/create" \
  -H "Authorization: Bearer $KALTURA_KS" \
  -H "Content-Type: application/json" \
  -d '{
    "gameObjectType": "leaderboard",
    "gameObjectId": "'$ONBOARD_LB'",
    "name": "IT Security module completion",
    "conditions": [
      {"fact": "eventType", "operator": "equal", "value": "viewPeriod"},
      {"fact": "categories", "operator": "in", "value": "'$IT_SECURITY_CATEGORY_ID'"}
    ],
    "type": "sum",
    "mode": "distribute_points",
    "metric": "playTime",
    "groupBy": "kuserId,entryId",
    "goal": "60",
    "points": "20",
    "maxPoints": "100"
  }'

# 3. Create "Security Certified" milestone badge
curl -s -X POST "$KALTURA_SCM_URL/badge/create" \
  -H "Authorization: Bearer $KALTURA_KS" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Security Certified",
    "description": "Complete all IT security training modules and pass the quiz",
    "virtualEventIds": ["$VIRTUAL_EVENT_ID"],
    "iconUrl": "https://example.com/badges/security-certified.png",
    "participationPolicy": {"userDefaultPolicy": "display", "policies": []},
    "rules": [
      {
        "name": "Watch all IT security sessions",
        "conditions": [
          {"fact": "eventType", "operator": "equal", "value": "viewPeriod"},
          {"fact": "categories", "operator": "in", "value": "'$IT_SECURITY_CATEGORY_ID'"}
        ],
        "type": "countUnique",
        "metric": "entryId",
        "groupBy": "kuserId",
        "goal": "5",
        "points": "1",
        "maxPoints": "1"
      },
      {
        "name": "Pass IT security quiz",
        "conditions": [
          {"fact": "eventType", "operator": "equal", "value": "quizSubmitted"},
          {"fact": "categories", "operator": "in", "value": "'$IT_SECURITY_CATEGORY_ID'"}
        ],
        "type": "count",
        "metric": "kuserId",
        "groupBy": "kuserId",
        "goal": "1",
        "points": "1",
        "maxPoints": "1"
      }
    ]
  }'

# 4. Create HR-branded onboarding completion certificate
ONBOARD_CERT=$(curl -s -X POST "$KALTURA_SCM_URL/certificate/create" \
  -H "Authorization: Bearer $KALTURA_KS" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Onboarding Complete",
    "description": "New hire onboarding program — all modules completed",
    "status": "enabled",
    "certificateEligibility": "once",
    "certifiedCreditsThreshold": 3,
    "host": "https://onboarding.internal.example.com",
    "participationPolicy": {"userDefaultPolicy": "display", "policies": []},
    "outputFileConfiguration": {
      "outputFileElements": [
        {"url": "https://cfvod.kaltura.com/p/'$PARTNER_ID'/thumbnail/entry_id/'$HR_BG_ENTRY_ID'/width/1397/height/1080"},
        {"textElementType": "userFullName", "fontSize": 30, "y": 440},
        {"textElementType": "certificationDate", "fontSize": 18, "x": 695, "y": 636}
      ]
    }
  }' | jq -r '.id')

# 5. Generate onboarding completion report for HR records
curl -s -X POST "$KALTURA_SCM_URL/report/generate" \
  -H "Authorization: Bearer $KALTURA_KS" \
  -H "Content-Type: application/json" \
  -d '{"reportType": "userCertificate", "gameObjectId": "'$ONBOARD_CERT'"}'
```

The 90-day window on the leaderboard defines the cohort period. Each onboarding module maps to a category, so rules can target specific modules. The badge requires both watching all sessions (`countUnique` on `entryId`) and passing the quiz (`count` on `quizSubmitted`), ensuring comprehensive completion before awarding the milestone.

> **See also:** [Categories & Entitlements](KALTURA_CATEGORIES_AND_ENTITLEMENTS_API.md) for organizing onboarding modules by category, [User Management](KALTURA_USER_MANAGEMENT_API.md) for managing new hire user accounts and group assignments.

## 15.9 Customer Education Academy with Badges

Reduce support tickets by building a customer education portal with visible achievement badges. Each product area has a badge requiring both content consumption and quiz completion. Track customer progress and export completion data to CRM.

**Workflow:**
1. Organize courses by product area categories (Admin Console, API Development, Analytics)
2. Create badges per module with inline rules — `countUnique` on `entryId` for content completion, `count` on `quizSubmitted` for knowledge verification
3. Create a "Certified Administrator" certificate for customers completing all modules
4. Query `userBadge/list` for per-customer progress
5. Generate badge completion reports for CRM integration

```bash
# 1. Create "API Expert" badge with content + quiz requirements
curl -s -X POST "$KALTURA_SCM_URL/badge/create" \
  -H "Authorization: Bearer $KALTURA_KS" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "API Expert",
    "description": "Complete all API training courses and pass the certification quiz",
    "virtualEventIds": ["$VIRTUAL_EVENT_ID"],
    "iconUrl": "https://example.com/badges/api-expert.png",
    "participationPolicy": {"userDefaultPolicy": "display", "policies": []},
    "rules": [
      {
        "name": "Complete API training courses",
        "conditions": [
          {"fact": "eventType", "operator": "equal", "value": "viewPeriod"},
          {"fact": "categories", "operator": "in", "value": "'$API_TRAINING_CATEGORY_ID'"}
        ],
        "type": "countUnique",
        "metric": "entryId",
        "groupBy": "kuserId",
        "goal": "8",
        "points": "1",
        "maxPoints": "1"
      },
      {
        "name": "Pass API certification quiz",
        "conditions": [
          {"fact": "eventType", "operator": "equal", "value": "quizSubmitted"},
          {"fact": "categories", "operator": "in", "value": "'$API_TRAINING_CATEGORY_ID'"}
        ],
        "type": "count",
        "metric": "kuserId",
        "groupBy": "kuserId",
        "goal": "1",
        "points": "1",
        "maxPoints": "1"
      }
    ]
  }'

# 2. Query per-customer badge progress
curl -s -X POST "$KALTURA_SCM_URL/userBadge/list" \
  -H "Authorization: Bearer $KALTURA_KS" \
  -H "Content-Type: application/json" \
  -d '{
    "gameObjectId": "'$BADGE_ID'",
    "pager": {"pageSize": 100, "pageIndex": 1}
  }'

# 3. Generate badge completion report for CRM export
curl -s -X POST "$KALTURA_SCM_URL/report/generate" \
  -H "Authorization: Bearer $KALTURA_KS" \
  -H "Content-Type: application/json" \
  -d '{"reportType": "userBadge", "gameObjectId": "'$BADGE_ID'"}'
```

Each badge requires both content consumption (`countUnique` ensures the customer watched distinct courses, not the same one repeatedly) and quiz completion (`count` on `quizSubmitted`). The `userBadge/list` response includes per-rule `rulesData` with `progress` and `completed` fields, so your application can render a progress bar per badge. Export the `userBadge` report to your CRM to trigger follow-up workflows when customers achieve certifications.

> **See also:** [Categories & Entitlements](KALTURA_CATEGORIES_AND_ENTITLEMENTS_API.md) for product area category structure, [eSearch](KALTURA_ESEARCH_API.md) for searching entries and users by badge-related metadata.

## 15.10 Team-Based Competitions

Run department-level or regional competitions alongside individual rankings. Sub-leaderboards automatically aggregate individual scores by a user profile property (company, country, department), so team standings update in real time without separate team-level scoring logic.

**Workflow:**
1. Create a leaderboard with `subLeaderboards` using `filterPaths` referencing user profile properties (e.g., `["company"]` for department grouping)
2. Individual scores auto-aggregate within their team segment
3. Create a team-level badge to recognize the top-performing department
4. Query sub-leaderboard rankings via `userScore/list` with `gameObjectType: "leaderboard"`

```bash
# 1. Create leaderboard with department-based sub-leaderboards
TEAM_LB=$(curl -s -X POST "$KALTURA_SCM_URL/leaderboard/create" \
  -H "Authorization: Bearer $KALTURA_KS" \
  -H "Content-Type: application/json" \
  -d '{
    "objectType": "Leaderboard",
    "name": "Sales Kickoff Competition",
    "description": "Individual and department rankings for SKO 2025",
    "status": "scheduled",
    "startDate": "2025-06-01T09:00:00Z",
    "endDate": "2025-06-03T18:00:00Z",
    "participationPolicy": {
      "userDefaultPolicy": "display",
      "policies": [
        {"policy": "do_not_display", "matchCriteria": "byGroup", "values": ["executives"]}
      ]
    },
    "subLeaderboards": [
      {"name": "By Department", "filterPaths": ["company"], "id": 0}
    ],
    "virtualEventIds": ["$VIRTUAL_EVENT_ID"]
  }' | jq -r '.id')

# 2. Create "Top Department" team badge
curl -s -X POST "$KALTURA_SCM_URL/badge/create" \
  -H "Authorization: Bearer $KALTURA_KS" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Top Department",
    "description": "Awarded to every member of the highest-scoring department",
    "virtualEventIds": ["$VIRTUAL_EVENT_ID"],
    "iconUrl": "https://example.com/badges/top-department.png",
    "participationPolicy": {"userDefaultPolicy": "display", "policies": []},
    "rules": [
      {
        "name": "Department total engagement",
        "conditions": [{"fact": "eventType", "operator": "equal", "value": "viewPeriod"}],
        "type": "sum",
        "metric": "playTime",
        "groupBy": "kuserId",
        "goal": "300",
        "points": "1",
        "maxPoints": "1"
      }
    ]
  }'

# 3. Query team standings (sub-leaderboard rankings)
curl -s -X POST "$KALTURA_SCM_URL/userScore/list" \
  -H "Authorization: Bearer $KALTURA_KS" \
  -H "Content-Type: application/json" \
  -d '{
    "gameObjectId": "'$TEAM_LB'",
    "gameObjectType": "leaderboard",
    "pager": {"pageSize": 50, "pageIndex": 1}
  }'
```

The `filterPaths: ["company"]` setting on the sub-leaderboard groups users by the `company` property from their [User Profile](KALTURA_USER_PROFILE_API.md). Individual scores accumulate normally, and the sub-leaderboard aggregates them per team automatically. Use `do_not_display` for executives so they participate (their scores count toward the department total) but do not appear in individual rankings.

> **See also:** [User Profile](KALTURA_USER_PROFILE_API.md) for user properties that power `filterPaths` grouping, [Events Platform](KALTURA_EVENTS_PLATFORM_API.md) for virtual event scoping.


# 16. Best Practices

**Rule design — use groupBy wisely.** `groupBy: "kuserId"` accumulates across all entries. `groupBy: "kuserId,entryId"` accumulates per entry per user — use this for "watch X minutes per session" rules where you want per-session caps.

**Set maxPoints caps.** Without `maxPoints`, users can accumulate unlimited points from a single rule. Use caps to prevent gaming: `"maxPoints": "100"` per session for viewership, `"maxPoints": "50"` for chat.

**Sub-rule ordering.** Sub-rules execute before the root rule evaluates. Use `block_root_rule_if_exhausted` to cap total accumulation, and `block_root_rule_while_in_progress` for prerequisite logic.

**Status lifecycle.** Create game objects as `scheduled`, enable rules, then update to `enabled` when the event starts. Use `scheduledGameObject` for automated transitions.

**Event scoping.** Scope rules to specific events or content using `virtualEventId` and `categories` conditions. Without scoping, rules apply to all partner content.

**Certificate PDF design.** Test the PDF template with a real certificate before the event. The background image URL must be publicly accessible. Text overlay positions (`x`, `y`) are in pixels from the top-left corner.

**Participation policies.** Always exclude internal staff from leaderboards and lead scoring via `byEmailDomain` with policy `do_not_save`. Speakers can participate but should be hidden via `do_not_display`.

**External events.** Use `delta` mode for incremental score additions (booth visits, check-ins). Use `upsert` mode when the external system provides final scores (exam results, external quiz platforms).


# 17. Related Guides

- **[Events Platform](KALTURA_EVENTS_PLATFORM_API.md)** — `virtualEventIds` scope game objects to events; category IDs in rule conditions  
- **[User Profile](KALTURA_USER_PROFILE_API.md)** — User properties power sub-leaderboards via `filterPaths[]`; user metadata enriches reports  
- **[Analytics Reports](KALTURA_ANALYTICS_REPORTS_API.md)** — User Reactions Report (ID 4021) for granular per-user engagement data  
- **[Events Collection](KALTURA_ANALYTICS_EVENTS_COLLECTION_API.md)** — Playback events (`viewPeriod`) feed leaderboard and badge rules  
- **[Messaging](KALTURA_MESSAGING_API.md)** — Certificate download email delivery; winner notification emails  
- **[Webhooks](KALTURA_EVENT_NOTIFICATIONS_WEBHOOK_AND_EMAIL_API.md)** — Event notifications on gamification state changes  
- **[Session Guide](KALTURA_SESSION_GUIDE.md)** — Admin KS as Bearer token; `GAME_BASE`/`GAME_MANAGE` permissions  
- **[Custom Metadata](KALTURA_CUSTOM_METADATA_API.md)** — `metadataProfileId` on certificates for PDF generation context  
- **[Categories & Entitlements](KALTURA_CATEGORIES_AND_ENTITLEMENTS_API.md)** — Category IDs in rule conditions for content scoping  
- **[eSearch](KALTURA_ESEARCH_API.md)** — Search entries and users by badge-related metadata
- **[Quiz API](KALTURA_QUIZ_API.md)** — Interactive video quizzes that feed gamification scoring rules

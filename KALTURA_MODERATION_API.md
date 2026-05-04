# Kaltura Moderation API

Moderation lets administrators and AI engines review content before it becomes visible to end users. The platform provides two complementary systems: a **manual moderation queue** (community flagging, moderator approve/reject) and **AI-powered moderation via REACH** (automated policy evaluation using LLMs and computer vision). The two work together — AI screens content at scale against configurable policies, while community flagging catches context-specific issues that automated systems miss. Both systems share the same entry-level `moderationStatus` field that controls playback visibility.

**Base URL:** `$KALTURA_SERVICE_URL` (default `https://www.kaltura.com/api_v3`)  
**Auth:** KS (admin session for approve/reject; user or widget session for flagging)  
**Format:** All requests use `format=1` for JSON responses  

<!-- Sections: 1.When to Use | 2.Prerequisites | 3.Architecture | 4.Entry Moderation Status | 5.User Flagging | 6.Moderator Actions | 7.AI Moderation via REACH | 8.Moderation Policies and Rules | 9.Category Moderation | 10.Player Integration | 11.Permissions | 12.Notifications | 13.REACH Automation Rules | 14.Error Handling | 15.Best Practices | 16.Related Guides -->


# 1. When to Use

- **Content review before publishing** — Hold uploaded entries for moderator approval before they become playable  
- **User-reported content** — Let viewers flag inappropriate content via the player plugin  
- **Automated AI content screening** — Screen video transcripts and frames against moderation policies using REACH  
- **Channel-level content gating** — Require approval before content appears in specific categories/channels  
- **Compliance workflows** — Enforce corporate content policies (hate speech, PII, profanity) with configurable rules  

# 2. Prerequisites

- An ADMIN KS (type=2) with `disableentitlement` privilege for approve, reject, and moderation queue operations (see [Session Guide](KALTURA_SESSION_GUIDE.md))  
- The moderation feature enabled on your account (`moderateContent` setting) for entry-level moderation workflows  
- For AI moderation: the REACH plugin enabled with a moderation catalog item (serviceFeature=15) provisioned on your account  


# 3. Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│            ENTRY MODERATION (Manual / Community)                │
│                                                                 │
│  baseEntry.flag ──► FLAGGED_FOR_REVIEW (5)                     │
│  baseEntry.approve ──► APPROVED (2)                            │
│  baseEntry.reject ──► REJECTED (3)                             │
│  baseEntry.listFlags ──► view pending flags                    │
└─────────────────────────────────────────────────────────────────┘
           ▲                              │
           │  Manual or webhook bridge    │  entry.moderationStatus
           │                              ▼
┌─────────────────────────────────────────────────────────────────┐
│               AI MODERATION (REACH + KAI)                       │
│                                                                 │
│  entryVendorTask.add (serviceFeature=15) ──► AI analysis       │
│  Output: moderationOutputJson { violations[], summary }        │
│  Auto-action: categoryEntry.activate / categoryEntry.reject    │
└─────────────────────────────────────────────────────────────────┘
```

The AI moderation engine produces a `moderationOutputJson` report on the vendor task but does **not** automatically update `entry.moderationStatus`. To bridge AI results to entry-level moderation, either review the output manually and call `baseEntry.approve`/`reject`, or configure a webhook that reads the task result and triggers the appropriate action.


# 4. Entry Moderation Status

Every entry has a `moderationStatus` field that controls playback visibility and list inclusion.

| Value | Name | Playable | In Default List | Description |
|-------|------|----------|----------------|-------------|
| 1 | PENDING_MODERATION | No | No | Awaiting moderator review — entry is hidden |
| 2 | APPROVED | Yes | Yes | Moderator approved the entry |
| 3 | REJECTED | No | No | Moderator rejected the entry |
| 4 | DELETED | No | No | Entry deleted via moderation |
| 5 | FLAGGED_FOR_REVIEW | Yes | Yes | User flagged — entry remains playable during review |
| 6 | AUTO_APPROVED | Yes | Yes | No moderation required — default for new entries |

**Default behavior:** New entries get `AUTO_APPROVED` (6) unless the account has `moderateContent` enabled, in which case they start as `PENDING_MODERATION` (1).

**Visibility rules:** Entries with `PENDING_MODERATION` (1) or `REJECTED` (3) are excluded from `baseEntry.list` results by default. Include them explicitly with the `moderationStatusIn` or `moderationStatusEqual` filter.

**Status transitions:**

```
Entry created
  ├── moderateContent=false ──► AUTO_APPROVED (6)
  └── moderateContent=true  ──► PENDING_MODERATION (1)
                                  ├── approve ──► APPROVED (2)
                                  └── reject  ──► REJECTED (3)

AUTO_APPROVED (6) or APPROVED (2)
  └── user flags ──► FLAGGED_FOR_REVIEW (5)
                       ├── approve ──► APPROVED (2)
                       └── reject  ──► REJECTED (3)

REJECTED (3)
  └── cannot be flagged (baseEntry.flag returns ENTRY_CANNOT_BE_FLAGGED)
```


# 5. User Flagging

Users flag content via `baseEntry.flag`. This creates a moderation flag record and sets the entry status to `FLAGGED_FOR_REVIEW` (5). The entry remains playable during review.

## 5.1 baseEntry.flag — Flag an Entry

```bash
curl -X POST "$KALTURA_SERVICE_URL/service/baseEntry/action/flag" \
  -d "ks=$KALTURA_KS" \
  -d "format=1" \
  -d "moderationFlag[objectType]=KalturaModerationFlag" \
  -d "moderationFlag[flaggedEntryId]=$KALTURA_ENTRY_ID" \
  -d "moderationFlag[flagType]=1" \
  -d "moderationFlag[comments]=Contains inappropriate content"
```

**Parameters:**

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `moderationFlag[flaggedEntryId]` | string | yes | Entry ID to flag |
| `moderationFlag[flagType]` | integer | yes | Flag reason (see Flag Types below) |
| `moderationFlag[comments]` | string | no | Free-text explanation (max 1024 chars) |

**Flag types (`KalturaModerationFlagType`):**

| Value | Name | Description |
|-------|------|-------------|
| 1 | SEXUAL_CONTENT | Nudity, pornography, or suggestive content |
| 2 | VIOLENT_REPULSIVE | Violence, gore, or repulsive content |
| 3 | HARMFUL_DANGEROUS | Harmful or dangerous acts |
| 4 | SPAM_COMMERCIALS | Spam or commercial promotion |
| 5 | COPYRIGHT | Copyright infringement |
| 6 | TERMS_OF_USE_VIOLATION | Violates terms of use |

**Validation:** The entry must be in `APPROVED` (2), `AUTO_APPROVED` (6), or `FLAGGED_FOR_REVIEW` (5) status. Flagging a `REJECTED` or `PENDING_MODERATION` entry returns `ENTRY_CANNOT_BE_FLAGGED`.

**Response:** Returns a `KalturaModerationFlag` object with the generated flag ID, status `PENDING` (1), and creation timestamp.

**Side effects:**
- Entry `moderationStatus` changes to `FLAGGED_FOR_REVIEW` (5) if not already  
- Entry `moderationCount` increments by 1  
- Email notifications fire to users with `CONTENT_MODERATE_APPROVE_REJECT` permission  

**Permissions:** Flagging is broadly permitted — works with user sessions, widget sessions, and playback sessions. Anonymous flagging from widget KS is supported.

## 5.2 baseEntry.listFlags — List Pending Flags

```bash
curl -X POST "$KALTURA_SERVICE_URL/service/baseEntry/action/listFlags" \
  -d "ks=$KALTURA_KS" \
  -d "format=1" \
  -d "entryId=$KALTURA_ENTRY_ID" \
  -d "pager[pageSize]=50"
```

**Response:**

```json
{
  "totalCount": 2,
  "objects": [
    {
      "id": 12345,
      "flaggedEntryId": "0_abc123",
      "flagType": 1,
      "comments": "Inappropriate content in first 30 seconds",
      "status": 1,
      "createdAt": 1700000000,
      "objectType": "KalturaModerationFlag"
    }
  ],
  "objectType": "KalturaModerationFlagListResponse"
}
```

Returns flags with `status=PENDING` (1). After `approve` or `reject`, flags are marked `MODERATED` (2) and no longer appear in this list.

**Flag status enum (`KalturaModerationFlagStatus`):**

| Value | Name |
|-------|------|
| 1 | PENDING |
| 2 | MODERATED |

**Permission:** Requires `CONTENT_MODERATE_BASE`.


# 6. Moderator Actions

## 6.1 baseEntry.approve — Approve an Entry

```bash
curl -X POST "$KALTURA_SERVICE_URL/service/baseEntry/action/approve" \
  -d "ks=$KALTURA_KS" \
  -d "format=1" \
  -d "entryId=$KALTURA_ENTRY_ID"
```

Sets `moderationStatus` to `APPROVED` (2), resets `moderationCount` to 0, and marks all pending flags as `MODERATED`. The entry becomes playable and visible in default list results.

**Permission:** Requires `CONTENT_MODERATE_APPROVE_REJECT`.

## 6.2 baseEntry.reject — Reject an Entry

```bash
curl -X POST "$KALTURA_SERVICE_URL/service/baseEntry/action/reject" \
  -d "ks=$KALTURA_KS" \
  -d "format=1" \
  -d "entryId=$KALTURA_ENTRY_ID"
```

Sets `moderationStatus` to `REJECTED` (3), resets `moderationCount` to 0, and marks all pending flags as `MODERATED`. The entry is hidden from default list results and blocked from playback.

**Permission:** Requires `CONTENT_MODERATE_APPROVE_REJECT`.

## 6.3 Listing the Moderation Queue

```bash
curl -X POST "$KALTURA_SERVICE_URL/service/baseEntry/action/list" \
  -d "ks=$KALTURA_KS" \
  -d "format=1" \
  -d "filter[objectType]=KalturaBaseEntryFilter" \
  -d "filter[moderationStatusIn]=1,5" \
  -d "filter[statusEqual]=2" \
  -d "filter[orderBy]=+createdAt" \
  -d "pager[pageSize]=50"
```

**Filter fields for moderation:**

| Field | Description |
|-------|-------------|
| `moderationStatusEqual` | Exact status match (e.g., `1` for PENDING_MODERATION) |
| `moderationStatusNotEqual` | Exclude a specific status |
| `moderationStatusIn` | Comma-separated list (e.g., `1,5` for pending + flagged) |
| `moderationStatusNotIn` | Exclude multiple statuses |

The KMC moderation queue uses `moderationStatusIn=1,5` combined with `statusEqual=2` (READY) to show entries that are fully processed and awaiting moderation.

## 6.4 user.notifyBan — Ban a Content Creator

```bash
curl -X POST "$KALTURA_SERVICE_URL/service/user/action/notifyBan" \
  -d "ks=$KALTURA_KS" \
  -d "format=1" \
  -d "userId=$USER_ID"
```

Sends a ban notification to the content creator. Used by the KMC moderation detail panel alongside approve/reject. The user account remains active — this sends a notification only.

## 6.5 Bulk Operations

Approve or reject multiple entries in a single request using multirequest:

```bash
curl -X POST "$KALTURA_SERVICE_URL/service/multirequest" \
  -d "ks=$KALTURA_KS" \
  -d "format=1" \
  -d "1[service]=baseEntry" \
  -d "1[action]=approve" \
  -d "1[entryId]=$ENTRY_ID_1" \
  -d "2[service]=baseEntry" \
  -d "2[action]=approve" \
  -d "2[entryId]=$ENTRY_ID_2" \
  -d "3[service]=baseEntry" \
  -d "3[action]=approve" \
  -d "3[entryId]=$ENTRY_ID_3"
```

Check each sub-response for `KalturaAPIException` — one failed approval does not block the others.


# 7. AI Moderation via REACH

AI moderation uses the REACH service to analyze entry content against configurable policies. The moderation engine (KAI) evaluates transcripts with an LLM (text/caption moderation) and video frames with AWS Rekognition (visual moderation).

## 7.1 Service Feature

Moderation is `VendorServiceFeature = 15` in the REACH system, alongside other AI services like captions (1), translation (2), and summarization (13).

## 7.2 Discovering Moderation Catalog Items

```bash
curl -X POST "$KALTURA_SERVICE_URL/service/reach_vendorCatalogItem/action/list" \
  -d "ks=$KALTURA_KS" \
  -d "format=1" \
  -d "filter[objectType]=KalturaVendorCatalogItemFilter" \
  -d "filter[serviceFeatureEqual]=15"
```

Returns `KalturaVendorModerationCatalogItem` objects with pricing, turn-around time, and engine type.

## 7.3 Ordering a Moderation Task

```bash
curl -X POST "$KALTURA_SERVICE_URL/service/reach_entryVendorTask/action/add" \
  -d "ks=$KALTURA_KS" \
  -d "format=1" \
  -d "entryVendorTask[objectType]=KalturaEntryVendorTask" \
  -d "entryVendorTask[entryId]=$KALTURA_ENTRY_ID" \
  -d "entryVendorTask[catalogItemId]=$CATALOG_ITEM_ID" \
  -d "entryVendorTask[taskJobData][objectType]=KalturaModerationVendorTaskData" \
  -d "entryVendorTask[taskJobData][policyIds]=1,2" \
  -d "entryVendorTask[taskJobData][ruleIds]=" \
  -d "entryVendorTask[taskJobData][categoryIds]=$CATEGORY_ID"
```

**Task data fields (`KalturaModerationVendorTaskData`):**

| Field | Type | Description |
|-------|------|-------------|
| `ruleIds` | string | Comma-separated moderation rule IDs to apply |
| `policyIds` | string | Comma-separated moderation policy IDs to apply |
| `categoryIds` | string | Comma-separated category IDs — AI auto-activates/rejects categoryEntry based on compliance |
| `moderationOutputJson` | string | Output: JSON with violations and policy summary (populated by AI engine) |

**Task status lifecycle (`EntryVendorTaskStatus`):**

| Value | Name | Description |
|-------|------|-------------|
| 1 | PENDING | Ready for AI engine pickup |
| 2 | READY | Completed successfully — results in `moderationOutputJson` |
| 3 | PROCESSING | AI engine is analyzing content |
| 4 | PENDING_MODERATION | Task itself awaiting admin approval before execution |
| 5 | REJECTED | Admin rejected the task request |
| 6 | ERROR | Processing failed |
| 7 | ABORTED | Cancelled |
| 8 | PENDING_ENTRY_READY | Waiting for entry to finish transcoding |
| 9 | SCHEDULED | Scheduled for future execution |

**REACH profile moderation gate:** If the REACH profile has `enableMachineModeration=true`, the task starts at `PENDING_MODERATION` (4) and requires `entryVendorTask.approve` before the AI engine processes it. This controls whether to spend REACH credit on the task, not the content moderation outcome.

## 7.4 Reading Moderation Results

```bash
curl -X POST "$KALTURA_SERVICE_URL/service/reach_entryVendorTask/action/get" \
  -d "ks=$KALTURA_KS" \
  -d "format=1" \
  -d "id=$TASK_ID"
```

When the task reaches `READY` (2), the `taskJobData.moderationOutputJson` contains the AI analysis:

```json
{
  "violations": [
    {
      "id": "1",
      "rule": "Hate Speech & Discrimination",
      "text": "exact quote from content",
      "severity": 85,
      "start_time": [125.5, 340.2]
    }
  ],
  "summary": {
    "policy_1": {
      "score": 42.5,
      "comply": false,
      "critical_violation": false
    },
    "policy_2": {
      "score": 0,
      "comply": true,
      "critical_violation": false
    }
  }
}
```

Each violation includes the rule ID, violated rule name, exact text quote, severity score (0-100), and timestamps (for caption/video moderation).

Each policy summary includes the weighted score, compliance boolean, and whether a critical rule was violated.

## 7.5 Category Auto-Action

When `categoryIds` are provided in the task data, the AI engine automatically calls `categoryEntry.activate` or `categoryEntry.reject` based on policy compliance. This enables automated content gating per channel without manual intervention — entries that pass all policies are published to the category; entries that fail are rejected.


# 8. Moderation Policies and Rules

## 8.1 Predefined Text Rules

The AI engine includes 8 predefined text moderation rules:

| ID | Rule Name | Severity | Description |
|----|-----------|----------|-------------|
| 1 | Hate Speech & Discrimination | 95 | Content promoting violence or hatred based on protected characteristics |
| 2 | Explicit & Sexual Content | 90 | Sexually explicit, pornographic, or suggestive content |
| 3 | Violence & Gore | 90 | Graphic violence, self-harm, extreme cruelty |
| 4 | Profanity & Inappropriate Language | 75 | Excessive profanity, offensive language, derogatory remarks |
| 5 | Harassment & Cyberbullying | 90 | Threats, personal attacks, intimidation |
| 6 | Illegal Activities & Dangerous Behavior | 85 | Content promoting illegal activities, drug use, weapons |
| 7 | Misinformation & False Claims | 80 | Misleading information, conspiracy theories, false claims |
| 8 | Confidential & Sensitive Data | 95 | Trade secrets, financial data, PII, internal communications |

## 8.2 Predefined Visual Rules

7 visual moderation rules powered by AWS Rekognition:

| ID | Rule Name | Severity | Detection Labels |
|----|-----------|----------|-----------------|
| 20 | Explicit Nudity | 80 | Sexual activity, exposed genitalia, sex toys |
| 21 | Violence | 80 | Weapon violence, physical violence, blood, explosions |
| 22 | Hate Symbols | 80 | Nazi symbols, white supremacy, extremist imagery, middle finger |
| 23 | Drugs | 50 | Pills, smoking, drinking, alcoholic beverages |
| 24 | Self-harm / Suicide | 80 | Self-harm behavior |
| 25 | Graphic Medical Content | 50 | Surgery, emaciated bodies, corpses |
| 26 | Non-Explicit Nudity | 70 | Bare back, implied nudity, kissing, swimwear |

Visual moderation extracts video keyframes, deduplicates similar frames using perceptual hashing, and runs each unique frame through Rekognition `detect_moderation_labels` with a configurable confidence threshold (default: 80).

## 8.3 Predefined Policies

| ID | Policy Name | Type | Rules | Threshold | Runs On |
|----|-------------|------|-------|-----------|---------|
| 1 | Corporate Verbal Content Integrity & Compliance | text | Rules 1-8 (equal weight) | 0.2 (20%) | name, description, tags, captions |
| 2 | Corporate Visual Content Integrity & Compliance | video | Rules 20-26 (equal weight) | 0.6 (60%) | video frames |

## 8.4 Custom Rules and Policies

Custom rules (IDs starting at 100) allow natural-language moderation criteria evaluated by the LLM. Custom rules and policies are stored in the platform configuration system and managed through the configuration API.

**Custom rule structure:**

| Field | Type | Description |
|-------|------|-------------|
| `id` | string | Auto-assigned starting at 100 |
| `rule` | string | Natural language description — the LLM evaluates content against this text |
| `name` | string | Display name |
| `tags` | array | Categorization tags |

**Policy structure:**

| Field | Type | Description |
|-------|------|-------------|
| `id` | string | Policy identifier |
| `name` | string | Display name |
| `ruleConfs` | array | Rules with per-policy weight, criticality, and max_score |
| `threshold` | float | 0-1 compliance threshold (lower = stricter) |
| `type` | string | `"text"` or `"video"` |
| `runOnAttributes` | array | Content targets: `name`, `description`, `tags`, `captions`, `video` |

Each `ruleConf` entry:

| Field | Type | Description |
|-------|------|-------------|
| `id` | string | Rule ID reference |
| `weight` | float | Contribution to total score (all weights in a policy should sum to 1.0) |
| `critical` | boolean | If true, any violation auto-fails the policy regardless of score |
| `max_score` | float | Cap on cumulative severity for this rule (prevents one rule from dominating) |

## 8.5 Scoring Algorithm

The AI engine uses a hybrid scoring approach combining weighted scores with critical-rule overrides:

1. For each rule in the policy, sum all violation severities (each violation is 0-100)  
2. Cap the sum at `max_score` if configured  
3. Multiply the capped sum by the rule's `weight`  
4. Accumulate into the policy total score  
5. **Decision:** If any `critical` rule has violations, `comply = false` regardless of score. Otherwise, `comply = (score < threshold * 100)`  

**Severity scale:**
- 0-40: Minor (borderline violation, little impact)  
- 41-70: Moderate (clear violation, could have consequences)  
- 71-100: Severe (critical violation, high risk)  

**Post-processing:** Duplicate violations are merged, timestamps within 5 seconds are combined, and violations are capped at 10 per rule.


# 9. Category Moderation

Categories can require content approval independently of account-level moderation. This is commonly used for channel-based content gating in Content Hubs.

When category moderation is enabled, entries added to the category get `categoryEntry.status = PENDING` (1) instead of `ACTIVE` (2). Channel managers approve or reject entries at the category level.

## 9.1 categoryEntry.activate — Approve Content in Category

```bash
curl -X POST "$KALTURA_SERVICE_URL/service/categoryEntry/action/activate" \
  -d "ks=$KALTURA_KS" \
  -d "format=1" \
  -d "entryId=$KALTURA_ENTRY_ID" \
  -d "categoryId=$CATEGORY_ID"
```

Changes `categoryEntry.status` from `PENDING` (1) to `ACTIVE` (2). The entry becomes visible within that category.

## 9.2 categoryEntry.reject — Reject Content in Category

```bash
curl -X POST "$KALTURA_SERVICE_URL/service/categoryEntry/action/reject" \
  -d "ks=$KALTURA_KS" \
  -d "format=1" \
  -d "entryId=$KALTURA_ENTRY_ID" \
  -d "categoryId=$CATEGORY_ID"
```

Rejects the category-entry association. The entry is removed from the category listing.

## 9.3 Category vs Entry Moderation

| Aspect | Entry Moderation | Category Moderation |
|--------|-----------------|-------------------|
| Scope | Account-wide | Per-category |
| Status field | `entry.moderationStatus` (1-6) | `categoryEntry.status` (1=PENDING, 2=ACTIVE) |
| Actions | `baseEntry.approve` / `reject` | `categoryEntry.activate` / `reject` |
| Playback impact | PENDING/REJECTED blocks playback globally | PENDING hides entry only within that category |
| Who reviews | Account administrators | Category managers/moderators |
| AI integration | Manual bridge from REACH results | AI engine can auto-activate/reject via `categoryIds` |


# 10. Player Integration

The `playkit-js-moderation` plugin adds a "Report Content" button to the Kaltura Player v7 upper bar. Viewers can flag content without leaving the player.

## 10.1 Configuration

```javascript
var config = {
  plugins: {
    'playkit-js-moderation': {
      reportLength: 500,
      notificatonDuration: 5000,
      subtitle: '',
      moderateOptions: [
        { id: 1, label: 'Sexual Content' },
        { id: 2, label: 'Violent Or Repulsive' },
        { id: 3, label: 'Harmful Or Dangerous Act' },
        { id: 4, label: 'Spam / Commercials' },
        { id: 5, label: 'Copyright Violation' },
        { id: 6, label: 'Terms of Use Violation' }
      ]
    }
  }
};
var player = KalturaPlayer.setup(config);
```

**Plugin options:**

| Option | Type | Default | Description |
|--------|------|---------|-------------|
| `reportLength` | number | 500 | Maximum comment length |
| `notificatonDuration` | number | 5000 | Toast notification display time (ms) |
| `subtitle` | string | `''` | Extra information below the dialog title |
| `moderateOptions` | array | Types 1-4 | Customizable flag type list (id + label) |

## 10.2 Events

| Event | When Fired | Payload |
|-------|-----------|---------|
| `report_clicked` | User clicks the flag icon | None |
| `report_submitted` | User submits the report form | `{ reportType: number }` |

The plugin calls `baseEntry.flag` with the player's provider KS. It pauses playback while the modal is open and resumes on close. The plugin supports 18 languages and is accessible via keyboard navigation with ARIA attributes.


# 11. Permissions

| Permission | ID | Allows |
|-----------|-----|--------|
| `CONTENT_MODERATE_BASE` | 1076 | View moderation queue, list flags |
| `CONTENT_MODERATE_APPROVE_REJECT` | 1043 | Approve and reject entries |
| `CONTENT_MODERATE_METADATA` | 1045 | Edit metadata during moderation review |
| `CONTENT_MODERATE_CUSTOM_DATA` | 1044 | Edit custom metadata during moderation review |
| `FEATURE_KMC_VERIFY_MODERATION` | 1103 | Show confirmation dialog before approve/reject in KMC |

Flagging (`baseEntry.flag`) does not require moderation permissions — it works with any authenticated session including widget and playback sessions.


# 12. Notifications

## 12.1 Email Notification Templates

| Template | Trigger | Recipients |
|----------|---------|------------|
| `Entry_Pending_Moderation` | Entry status changes to `PENDING_MODERATION` (1) | Configured recipients |
| `New_Item_Pending_Moderation_Kmc_Moderators` | Same | Users with approve/reject permission |
| `New_Item_Flagged_For_Moderation_Kmc_Moderators` | Entry status changes to `FLAGGED_FOR_REVIEW` (5) | Users with approve/reject permission |
| `Entry_Vendor_Task_Pending_Moderation` | REACH task enters `PENDING_MODERATION` (4) | Configured recipients |

## 12.2 Webhook Integration

Monitor moderation status changes with event notification HTTP templates. The `moderationStatus` column is tracked — any change fires `OBJECT_CHANGED` event notifications configured for the entry object type.

Cross-reference: [Webhooks Guide](KALTURA_EVENT_NOTIFICATIONS_WEBHOOK_AND_EMAIL_API.md) for configuring HTTP notification templates.


# 13. REACH Automation Rules

REACH profiles can trigger moderation tasks automatically when entries match configured conditions.

**Trigger events:**
- Entry becomes READY (transcoding complete)  
- Asset becomes READY  
- Category entry becomes ACTIVE  

**Rule structure:** Each rule has conditions (entry filters, metadata conditions, event notification triggers) and actions (`kAddEntryVendorTaskAction` pointing to moderation catalog item IDs). Rules with no conditions trigger on all matching events.

**Setup flow:**
1. Create or identify a `VendorModerationCatalogItem` on the account  
2. Configure a REACH profile with a rule that references the catalog item ID  
3. Set the rule conditions (or leave empty to trigger on all new entries)  
4. New entries matching the conditions automatically get a moderation vendor task  

Cross-reference: [REACH API Guide](KALTURA_REACH_API.md) for profile and rule configuration.


# 14. Error Handling

| Error Code | Meaning | Resolution |
|-----------|---------|------------|
| `ENTRY_ID_NOT_FOUND` | Entry does not exist or was permanently deleted | Verify entry ID; check status is not 3 (DELETED) |
| `INVALID_KS` | Session expired or malformed | Generate a fresh ADMIN KS |
| `SERVICE_FORBIDDEN` | Account lacks moderation plugin | Contact account manager to enable moderation |
| `MODERATE_CONTENT` permission missing | KS lacks moderation privilege | Add `disableentitlement` or ensure admin role |
| `INVALID_ENUM_VALUE` | Invalid moderationStatus value passed | Use valid values: 1 (PENDING), 2 (APPROVED), 3 (REJECTED), 5 (FLAGGED_FOR_REVIEW), 6 (AUTO_APPROVED) |
| `CATEGORY_NOT_FOUND` | Category ID invalid for categoryEntry operations | Verify category exists and user has access |


# 15. Best Practices

- **Generate KS server-side using AppTokens** — pass short-lived, scoped tokens to client applications. See [AppTokens API](KALTURA_APPTOKENS_API.md) for production auth patterns  
- **Use category moderation for channel workflows** — `categoryEntry.activate`/`reject` provides per-channel control without affecting global entry playback  
- **Check each multirequest sub-response** — bulk approve/reject operations can partially fail. Each array element may be a `KalturaAPIException`  
- **Bridge AI results explicitly** — REACH moderation output does not auto-update `entry.moderationStatus`. Read `moderationOutputJson`, evaluate, then call `baseEntry.approve`/`reject`  
- **Set `categoryIds` for automated channel gating** — when ordering AI moderation tasks, provide category IDs to let the engine auto-activate/reject category entries based on policy compliance  
- **Filter the moderation queue with `moderationStatusIn=1,5`** — matches the KMC pattern: shows entries pending moderation and entries flagged for review  
- **Register cleanup before assertions in tests** — moderation approve/reject changes are persistent. Register cleanup of test entries before asserting moderation status  


# 16. Related Guides

| Guide | Relationship |
|-------|-------------|
| [REACH API](KALTURA_REACH_API.md) | AI moderation tasks are REACH vendor tasks with serviceFeature=15 |
| [Categories & Entitlements](KALTURA_CATEGORIES_AND_ENTITLEMENTS_API.md) | Category moderation, categoryEntry.activate/reject |
| [Webhooks](KALTURA_EVENT_NOTIFICATIONS_WEBHOOK_AND_EMAIL_API.md) | HTTP notifications on moderation status changes |
| [Upload & Ingestion](KALTURA_UPLOAD_AND_INGESTION_API.md) | Entry moderation status enum, media lifecycle |
| [Player Embed](KALTURA_PLAYER_EMBED_GUIDE.md) | playkit-js-moderation plugin configuration |
| [User Management](KALTURA_USER_MANAGEMENT_API.md) | Moderation permissions, user.notifyBan |
| [Agents Manager](KALTURA_AGENTS_MANAGER_API.md) | Automation rules can trigger moderation workflows |

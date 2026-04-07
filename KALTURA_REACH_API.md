# Kaltura REACH API Guide

Kaltura REACH is the **captioning, translation, accessibility, and content enrichment** services framework. Order processing tasks — from machine-generated captions to professional human translations — against your media entries. Results (caption files, audio tracks, chapters, metadata) are delivered directly back into Kaltura and attached to the entry automatically.

**Base URL:** `https://www.kaltura.com/api_v3` (may differ by region/deployment)
**Auth:** KS passed as `ks` parameter in POST form data (see [Session Guide](KALTURA_SESSION_GUIDE.md))
**Format:** Form-encoded POST, `format=1` for JSON responses

REACH services can be triggered manually via the API, automatically via [Kaltura Agents](KALTURA_AGENTS_MANAGER_API.md), or through the KMC/KMS management UIs.

## Prerequisites

- Know how to generate Kaltura Sessions (KS) in your backend (see [Session Guide](KALTURA_SESSION_GUIDE.md))
- Have a Kaltura account with REACH services enabled (contact your Kaltura account manager to provision)

**Endpoint pattern:**
```
POST https://www.kaltura.com/api_v3/service/{serviceName}/action/{actionName}
Content-Type: application/x-www-form-urlencoded
```

All parameters are passed as form data. Always include `ks=<YOUR_KS>` and `format=1` (JSON response).


## What REACH Provides

### Captioning & Transcription
- **Machine Captions (ASR)** — AI-powered, ~85% accuracy, up to 2-hour turnaround. Supports custom vocabularies/dictionaries for domain-specific terminology.
- **Professional (Human) Captions** — 99%+ accuracy, 3-48 hour turnaround depending on SLA tier. Compliant with closed captioning standards.
- **Live Captions** — Real-time machine-generated captions for scheduled live events.
- **Alignment** — Upload an existing transcript file and REACH syncs it to the audio timeline.

### Translation & Localization
- **Translation** — Three modes: (1) translate directly from audio, (2) translate from existing captions file, (3) order professional captions first, then translate. Supports 100+ languages.
- **Live Translation** — Real-time machine-generated subtitles in a different language during live events.
- **Dubbing** — Machine-based translated audio via text-to-speech, synced to original dialogue timing.

### Accessibility
- **Standard Audio Description** — Narration of visual elements mixed with original audio. English only.
- **Extended Audio Description** — Pauses video to allow detailed narration of visual content. Uses speech synthesis from time-coded VTT. Requires player plugin.
- **Sign Language** — Creates a child entry with sign language video (ASL or BSL) linked to the parent entry.

### Clips & Video Intelligence
- **AI Clips** — Automatically generate short clips/highlights from longer content using AI analysis. Machine-powered, immediate turnaround.
- **Quiz** — AI-generated quiz questions from video content.
- **Video Analysis** — Visual content analysis including OCR (optical character recognition).

### Content Enrichment
- **Chaptering** — AI-based chapter detection, reviewed by professionals. 24-hour turnaround, English only.
- **Summary** — AI-generated content summary with auto-chaptering.
- **Metadata Enrichment** — Automatic tags, keywords, and metadata extraction.
- **Document Enrichment** — AI-powered enrichment for document-type entries.

### Billing
REACH services are billed in **credits**, defined per REACH profile. Credit balances, usage, and limits are managed through the REACH profile configuration.


## Core Concepts

| Concept | What It Is |
|---|---|
| **REACH Profile** | Per-account configuration that defines credit allocation, output preferences (format, moderation, metadata extraction, speaker identification, profanity removal), dictionaries, and content deletion policy. |
| **Vendor Catalog Item** | A specific service offering from a vendor — e.g., "English Machine Captions, 2-hour TAT" or "Spanish Human Translation, 5 Business Days". Each has a unique `catalogItemId`. |
| **Entry Vendor Task** | A single unit of work: one service applied to one entry. Created by referencing a `catalogItemId` and an `entryId`. |

The typical flow: discover available catalog items for your account, then create a task against an entry using the desired catalog item.


## Key Enums Reference

### Service Features (`serviceFeature`)

| Value | Name | Description |
|---|---|---|
| 1 | CAPTIONS | Speech-to-text captioning |
| 2 | TRANSLATION | Caption/audio translation |
| 3 | ALIGNMENT | Transcript-to-audio alignment |
| 4 | AUDIO_DESCRIPTION | Standard audio description |
| 5 | CHAPTERING | AI chapter detection |
| 7 | DUBBING | Text-to-speech dubbing |
| 8 | LIVE_CAPTION | Real-time live captions |
| 9 | EXTENDED_AUDIO_DESCRIPTION | Extended audio description (VTT) |
| 10 | CLIPS | AI-powered clip generation from longer content |
| 11 | LIVE_TRANSLATION | Real-time live translation |
| 12 | QUIZ | Quiz generation |
| 13 | SUMMARY | Content summarization |
| 14 | VIDEO_ANALYSIS | Video content analysis |
| 15 | MODERATION | Content moderation |
| 16 | METADATA_ENRICHMENT | Metadata enrichment |
| 17 | SENTIMENT_ANALYSIS | Sentiment analysis |
| 18 | DOCUMENT_ENRICHMENT | Document enrichment |
| 19 | SIGN_LANGUAGE | Sign language video |

### Service Types (`serviceType`)

| Value | Name | Description |
|---|---|---|
| 1 | HUMAN | Professional human processing |
| 2 | MACHINE | AI/machine processing |

### Task Statuses (`status`)

| Value | Name | Description |
|---|---|---|
| 1 | PENDING | Created, waiting to be picked up |
| 2 | READY | Ready for vendor processing |
| 3 | PROCESSING | Vendor is actively working |
| 4 | PENDING_MODERATION | Completed, awaiting review |
| 5 | REJECTED | Rejected after moderation |
| 6 | ERROR | Processing failed |
| 7 | ABORTED | Cancelled |
| 8 | PENDING_ENTRY_READY | Waiting for media entry to finish processing |
| 9 | SCHEDULED | Scheduled for future execution (live events) |

### Task Status Flow

```
  Task created ──► PENDING_ENTRY_READY (8)  ──► PENDING (1)
                        (if entry not ready)        │
                                                    │
  Task created ──► PENDING (1) ─────────────────────┤
                                                    │
                        ┌───────────────────────────┤
                        │                           │
                        ▼                           ▼
                   PENDING_MODERATION (4)       READY (2)
                        │                           │
                   ┌────┴────┐                      │
                   ▼         ▼                      ▼
              REJECTED (5)  approved            PROCESSING (3)
                            │                       │
                            ▼                  ┌────┴────┐
                        READY (2) ──►...       ▼         ▼
                                           success    ERROR (6)
                                               │
                                               ▼
                                        PENDING_MODERATION (4)
                                          or READY (2)

  ABORTED (7) ◄── abort() from PENDING or PENDING_MODERATION
```

### Output Formats (`outputFormat`)

| Value | Name |
|---|---|
| 1 | SRT |
| 2 | DFXP |
| 3 | VTT |

### Turn-Around Times (`turnAroundTime`)

| Value | Name |
|---|---|
| -1 | BEST_EFFORT |
| 0 | IMMEDIATE |
| 1-7 | 1-7 BUSINESS_DAYS |
| 1800 | 30 minutes |
| 7200 | 2 hours |
| 10800 | 3 hours |
| 21600 | 6 hours |
| 28800 | 8 hours |
| 43200 | 12 hours |
| 86400 | 24 hours |
| 172800 | 48 hours |

### Processing Regions (`vendorTaskProcessingRegion`)

| Value | Name |
|---|---|
| 1 | US |
| 2 | EU |
| 3 | CA |

### Creation Mode (`creationMode`)

| Value | Name | Description |
|---|---|---|
| 1 | MANUAL | Created via API or UI by a user |
| 2 | AUTOMATIC | Created automatically by a rule or agent |


## 1. List Available Catalog Items

Discover which services are available for your account.

**`vendorCatalogItem.list`**

```
POST /api_v3/service/reach_vendorCatalogItem/action/list
```

```
ks=<YOUR_KS>
&format=1
&filter[serviceTypeEqual]=2
&filter[serviceFeatureEqual]=1
&filter[statusEqual]=2
```

**Filter parameters**

| Parameter | Type | Description |
|---|---|---|
| `filter[serviceTypeEqual]` | int | Filter by HUMAN (1) or MACHINE (2) |
| `filter[serviceFeatureEqual]` | int | Filter by feature (1=captions, 2=translation, etc.) |
| `filter[sourceLanguageEqual]` | string | Filter by source language (e.g., "English"). For best results, also filter client-side to ensure language matches. |
| `filter[statusEqual]` | int | Filter by status; use 2 (ACTIVE) for available items |
| `filter[turnAroundTimeEqual]` | int | Filter by TAT |
| `pager[pageSize]` | int | Results per page (default 30, max 500) |
| `pager[pageIndex]` | int | Page number (1-based) |

**Response**
```json
{
  "objectType": "KalturaVendorCatalogItemListResponse",
  "objects": [
    {
      "objectType": "KalturaVendorCaptionsCatalogItem",
      "id": 101,
      "vendorPartnerId": 5555,
      "name": "English Machine Captions",
      "serviceType": 2,
      "serviceFeature": 1,
      "sourceLanguage": "English",
      "turnAroundTime": 7200,
      "outputFormat": 1,
      "allowResubmission": true,
      "status": 2
    }
  ],
  "totalCount": 1
}
```

Save the `id` — this is the `catalogItemId` you use when creating tasks.

**Catalog item `objectType` by service feature:**

| Service Feature | objectType |
|---|---|
| CAPTIONS (1) | `KalturaVendorCaptionsCatalogItem` |
| TRANSLATION (2) | `KalturaVendorTranslationCatalogItem` |
| CHAPTERING (5) | `KalturaVendorChapteringCatalogItem` |
| DUBBING (7) | `KalturaVendorDubbingCatalogItem` |
| LIVE_CAPTION (8) | `KalturaVendorLiveCaptionCatalogItem` |
| CLIPS (10) | `KalturaVendorClipsCatalogItem` |
| LIVE_TRANSLATION (11) | `KalturaVendorLiveTranslationCatalogItem` |
| QUIZ (12) | `KalturaVendorQuizCatalogItem` |
| SUMMARY (13) | `KalturaVendorSummaryCatalogItem` |
| VIDEO_ANALYSIS (14) | `KalturaVendorVideoAnalysisCatalogItem` |
| MODERATION (15) | `KalturaVendorModerationCatalogItem` |
| METADATA_ENRICHMENT (16) | `KalturaVendorMetadataEnrichmentCatalogItem` |
| DOCUMENT_ENRICHMENT (18) | `KalturaVendorDocumentEnrichmentCatalogItem` |

When creating tasks via `entryVendorTask.add`, always use `objectType=KalturaEntryVendorTask` regardless of the catalog item type.


## 2. Get REACH Profile

Retrieve your REACH profile to understand account-level settings (credit balance, output preferences, dictionaries).

**`reachProfile.list`**

```
POST /api_v3/service/reach_reachProfile/action/list
```

```
ks=<YOUR_KS>
&format=1
&filter[statusEqual]=2
```

**Response**
```json
{
  "objects": [
    {
      "id": 1001,
      "name": "Production Profile",
      "status": 2,
      "profileType": 2,
      "defaultOutputFormat": 1,
      "enableMachineModeration": 0,
      "enableHumanModeration": 0,
      "autoDisplayMachineCaptionsOnPlayer": 1,
      "autoDisplayHumanCaptionsOnPlayer": 1,
      "enableMetadataExtraction": 1,
      "enableSpeakerChangeIndication": 1,
      "enableProfanityRemoval": 0,
      "maxCharactersPerCaptionLine": 42,
      "contentDeletionPolicy": 1,
      "vendorTaskProcessingRegion": 1,
      "credit": { "credit": 10000, "fromDate": 1704067200, "toDate": 1735689600 },
      "usedCredit": 1250.5,
      "dictionaries": [],
      "flavorParamsIds": ""
    }
  ],
  "totalCount": 1
}
```

**Key REACH Profile fields**

| Field | Description |
|---|---|
| `defaultOutputFormat` | Default caption format: SRT (1), DFXP (2), VTT (3) |
| `enableMachineModeration` | If true, machine results go to PENDING_MODERATION before applying |
| `enableHumanModeration` | If true, human results go to PENDING_MODERATION before applying |
| `autoDisplayMachineCaptionsOnPlayer` | Auto-display machine captions in the player |
| `autoDisplayHumanCaptionsOnPlayer` | Auto-display human captions in the player |
| `enableMetadataExtraction` | Extract tags/keywords from caption content |
| `enableSpeakerChangeIndication` | Mark speaker changes in captions |
| `enableProfanityRemoval` | Remove profanity from captions |
| `maxCharactersPerCaptionLine` | Line length limit for caption formatting |
| `contentDeletionPolicy` | When to delete source content after processing (1=never, 2=once processed, 3=after week, 4=after month, 5=after 3 months) |
| `vendorTaskProcessingRegion` | Data residency region: US (1), EU (2), CA (3) |
| `credit` | Credit allocation and validity period |
| `usedCredit` | Credits consumed so far |
| `dictionaries` | Custom vocabularies per language for machine captioning |
| `flavorParamsIds` | Preferred video flavor IDs for processing (comma-separated) |


## 3. Create a Task (Order a Service)

Submit a captioning, translation, or enrichment request for a specific entry.

**`entryVendorTask.add`**

```
POST /api_v3/service/reach_entryVendorTask/action/add
```

```
ks=<YOUR_KS>
&format=1
&entryVendorTask[objectType]=KalturaEntryVendorTask
&entryVendorTask[entryId]=1_abc123def
&entryVendorTask[reachProfileId]=1001
&entryVendorTask[catalogItemId]=101
```

**Required parameters**

| Parameter | Type | Description |
|---|---|---|
| `entryVendorTask[entryId]` | string | The media entry ID to process |
| `entryVendorTask[reachProfileId]` | int | Your REACH profile ID (from step 2) |
| `entryVendorTask[catalogItemId]` | int | The catalog item ID (from step 1) |

**Optional parameters**

| Parameter | Type | Description |
|---|---|---|
| `entryVendorTask[notes]` | string | Instructions for human vendors (terminology guidance, context) |
| `entryVendorTask[context]` | string | Task context identifier (for filtering/grouping) |
| `entryVendorTask[partnerData]` | string | JSON string with extra data for your own tracking |

**Response**
```json
{
  "id": 98765,
  "partnerId": 12345,
  "entryId": "1_abc123def",
  "status": 1,
  "reachProfileId": 1001,
  "catalogItemId": 101,
  "price": 2.5,
  "createdAt": 1712345678,
  "expectedFinishTime": 1712352878,
  "serviceType": 2,
  "serviceFeature": 1,
  "turnAroundTime": 7200,
  "creationMode": 1,
  "accessKey": "djJ8MTIzNDV8..."
}
```

The task begins in `PENDING` (1) status. If the entry is still processing, it starts in `PENDING_ENTRY_READY` (8) and moves to `PENDING` once the entry is ready. If moderation is enabled on your REACH profile, completed tasks will go to `PENDING_MODERATION` (4) before results are applied.


## 4. Check Task Status

**`entryVendorTask.get`**

```
POST /api_v3/service/reach_entryVendorTask/action/get
```

```
ks=<YOUR_KS>
&format=1
&id=98765
```

**Response** — same structure as the `add` response, with updated `status`, `finishTime`, `outputObjectId`, and `accuracy` fields once complete.

**Key fields to check:**

| Field | Description |
|---|---|
| `status` | Current status (see enum above) |
| `outputObjectId` | ID of the created output asset (caption ID, flavor ID, cue point ID, etc.) |
| `accuracy` | Result accuracy percentage (0-100) |
| `errDescription` | Error details if status is ERROR (6) |
| `finishTime` | Unix timestamp when processing completed |


## 5. List Tasks

Query tasks with filters for monitoring and reporting.

**`entryVendorTask.list`**

```
POST /api_v3/service/reach_entryVendorTask/action/list
```

```
ks=<YOUR_KS>
&format=1
&filter[entryIdEqual]=1_abc123def
&filter[statusIn]=1,2,3
&pager[pageSize]=50
```

**Common filter parameters**

| Parameter | Type | Description |
|---|---|---|
| `filter[entryIdEqual]` | string | Filter by entry ID |
| `filter[statusEqual]` | int | Filter by exact status |
| `filter[statusIn]` | string | Filter by multiple statuses (comma-separated) |
| `filter[catalogItemIdEqual]` | int | Filter by catalog item |
| `filter[reachProfileIdEqual]` | int | Filter by REACH profile |
| `filter[createdAtGreaterThanOrEqual]` | int | Unix timestamp — tasks created after |
| `filter[createdAtLessThanOrEqual]` | int | Unix timestamp — tasks created before |
| `filter[freeText]` | string | Free text search |
| `pager[pageSize]` | int | Results per page (default 30, max 500) |
| `pager[pageIndex]` | int | Page number (1-based) |

**Order by:** `+createdAt`, `-createdAt`, `+updatedAt`, `-updatedAt`, `+status`, `-status`, `+price`, `-price`, `+expectedFinishTime`, `-expectedFinishTime`


## 6. Manage Tasks

### Approve a moderated task
```
POST /api_v3/service/reach_entryVendorTask/action/approve
ks=<YOUR_KS>&format=1&id=98765
```

### Reject a moderated task
```
POST /api_v3/service/reach_entryVendorTask/action/reject
ks=<YOUR_KS>&format=1&id=98765&rejectReason=Quality+below+threshold
```

### Cancel a pending task
```
POST /api_v3/service/reach_entryVendorTask/action/abort
ks=<YOUR_KS>&format=1&id=98765&abortReason=No+longer+needed
```
Works for tasks in PENDING (1) or PENDING_MODERATION (4) status. Aborted tasks are deleted after cancellation; subsequent `get` calls return `ENTRY_VENDOR_TASK_NOT_FOUND`.

### Export tasks to CSV
```
POST /api_v3/service/reach_entryVendorTask/action/exportToCsv
ks=<YOUR_KS>&format=1&filter[statusEqual]=2
```
Creates a batch job that emails a CSV download link with the filtered tasks.


## Full Example: Order Machine Captions for an Entry

### Step-by-Step curl Example

Set up shell variables (see [Session Guide](KALTURA_SESSION_GUIDE.md) for generating a KS):

```bash
export KALTURA_SERVICE_URL="https://www.kaltura.com/api_v3"
export KALTURA_PARTNER_ID="YOUR_PARTNER_ID"
export KALTURA_KS="YOUR_KS"
```

**Step 1: Find available machine caption catalog items**

```bash
curl -X POST "$KALTURA_SERVICE_URL/service/reach_vendorCatalogItem/action/list" \
  -d "ks=$KALTURA_KS&format=1\
&filter[serviceTypeEqual]=2\
&filter[serviceFeatureEqual]=1\
&filter[sourceLanguageEqual]=English\
&filter[statusEqual]=2"
```

From the response, note the `id` of the desired catalog item (e.g., `101`). The `sourceLanguage` filter may not be enforced server-side, so verify the `sourceLanguage` field in the returned objects matches "English".

**Step 2: Get your REACH profile ID**

```bash
curl -X POST "$KALTURA_SERVICE_URL/service/reach_reachProfile/action/list" \
  -d "ks=$KALTURA_KS&format=1\
&filter[statusEqual]=2"
```

From the response, note the `id` of your active REACH profile (e.g., `1001`).

**Step 3: Order captions for an entry**

```bash
curl -X POST "$KALTURA_SERVICE_URL/service/reach_entryVendorTask/action/add" \
  -d "ks=$KALTURA_KS&format=1\
&entryVendorTask[objectType]=KalturaEntryVendorTask\
&entryVendorTask[entryId]=1_abc123def\
&entryVendorTask[reachProfileId]=1001\
&entryVendorTask[catalogItemId]=101"
```

From the response, note the task `id` (e.g., `98765`) and `expectedFinishTime`.

**Step 4: Poll for completion**

```bash
curl -X POST "$KALTURA_SERVICE_URL/service/reach_entryVendorTask/action/get" \
  -d "ks=$KALTURA_KS&format=1\
&id=98765"
```

Poll every 30 seconds until `status` is `2` (READY) or `6` (ERROR). When READY, the response includes `outputObjectId` (the caption asset ID) and `accuracy` (percentage). If ERROR, check `errDescription` for details.


## AI Clips Workflow (Content Lab)

AI Clips uses the REACH task system to analyze a video and automatically generate multiple short highlight clips with AI-generated titles, descriptions, and tags. This is exposed in the KMC as "Content Lab".

The workflow has two phases: **Generate** (AI creates clip suggestions as child entries) and **Save** (clone a clip into a standalone entry with trimmed content).

### Phase 1: Generate AI Clips

Order clip generation by creating a REACH task with `KalturaClipsVendorTaskData`:

**`entryVendorTask.add`**

```
ks=<YOUR_KS>
&format=1
&entryVendorTask[objectType]=KalturaEntryVendorTask
&entryVendorTask[entryId]=1_abc123def
&entryVendorTask[reachProfileId]=1001
&entryVendorTask[catalogItemId]=34832
&entryVendorTask[taskJobData][objectType]=KalturaClipsVendorTaskData
&entryVendorTask[taskJobData][outputLanguage]=English
&entryVendorTask[taskJobData][clipsDuration]=120
&entryVendorTask[taskJobData][instruction]=Generate highlights focusing on key announcements
&entryVendorTask[taskJobData][eventSessionContextId]=
```

**`KalturaClipsVendorTaskData` fields:**

| Field | Type | Description |
|---|---|---|
| `outputLanguage` | string | Language for generated clip titles/descriptions (e.g., "English") |
| `clipsDuration` | int | Maximum duration per clip in **seconds** |
| `instruction` | string | Free-text instruction for the AI (topic focus, style guidance) |
| `eventSessionContextId` | string | Optional session context ID for tracking |

The task starts in `PENDING` (1) and moves to `PROCESSING` (3). Poll with `entryVendorTask.get` until `READY` (2). Typical completion time is 30-60 seconds.

### Phase 2: List Generated Clips

Once the task is `READY`, the AI has created multiple child entries linked to the source. Retrieve them:

**`baseEntry.list`** — find clips by source entry ID:

```
ks=<YOUR_KS>
&format=1
&filter[rootEntryIdIn]=1_abc123def
&filter[statusIn]=1,2,4
&filter[orderBy]=-createdAt
&pager[pageSize]=500
```

Each generated clip is a full media entry with:
- AI-generated `name` (clip title)
- AI-generated `description` (clip summary)
- AI-generated `tags`
- `rootEntryId` pointing back to the source entry
- Its own `duration`, `thumbnailUrl`, etc.

**`playlist.list`** — clips may also be grouped in a path playlist:

```
ks=<YOUR_KS>
&format=1
&filter[referenceIdEqual]=1_abc123def
&filter[playListTypeEqual]=3
&pager[pageSize]=500
```

### Phase 3: Save a Clip as a Standalone Entry

To save a specific clip as an independent entry (with its own trimmed video content), use the three-step pattern: **clone → trim → set metadata**.

**Step 1: Clone the source entry**

```
ks=<YOUR_KS>
&format=1
&entryId=1_abc123def
&cloneOptions:item1:objectType=KalturaBaseEntryCloneOptionComponent
&cloneOptions:item1:itemType=5
&cloneOptions:item1:rule=1
&cloneOptions:item2:objectType=KalturaBaseEntryCloneOptionComponent
&cloneOptions:item2:itemType=2
&cloneOptions:item2:rule=1
&cloneOptions:item3:objectType=KalturaBaseEntryCloneOptionComponent
&cloneOptions:item3:itemType=6
&cloneOptions:item3:rule=1
&cloneOptions:item4:objectType=KalturaBaseEntryCloneOptionComponent
&cloneOptions:item4:itemType=7
&cloneOptions:item4:rule=1
&cloneOptions:item5:objectType=KalturaBaseEntryCloneOptionComponent
&cloneOptions:item5:itemType=1
&cloneOptions:item5:rule=1
```

Clone option `itemType` values: `1` (content), `2` (access control), `5` (categories), `6` (metadata), `7` (flavors).

**Step 2: Trim the cloned entry to clip boundaries**

Use `media.updateContent` with `KalturaClipAttributes`. Offset and duration are in **milliseconds**:

```
ks=<YOUR_KS>
&format=1
&entryId=<CLONED_ENTRY_ID>
&resource[objectType]=KalturaOperationResources
&resource[resources][0][objectType]=KalturaOperationResource
&resource[resources][0][resource][objectType]=KalturaEntryResource
&resource[resources][0][resource][entryId]=1_abc123def
&resource[resources][0][resource][flavorParamsId]=487091
&resource[resources][0][operationAttributes][0][objectType]=KalturaClipAttributes
&resource[resources][0][operationAttributes][0][offset]=350
&resource[resources][0][operationAttributes][0][duration]=205930
```

To include burned-in captions, add `captionAttributes`:

```
&resource[resources][0][operationAttributes][0][captionAttributes][0][objectType]=KalturaRenderCaptionAttributes
&resource[resources][0][operationAttributes][0][captionAttributes][0][captionAssetId]=1_vrrrcg9i
```

- `offset` — Start position in milliseconds from the source entry
- `duration` — Clip length in milliseconds
- `flavorParamsId` — Get from `flavorAsset.list` on the source entry (use the original or a ready flavor)
- `captionAssetId` — Optional; get from `captionAsset.list` to burn captions into the clip

**Step 3: Set metadata on the saved clip**

```
ks=<YOUR_KS>
&format=1
&entryId=<CLONED_ENTRY_ID>
&mediaEntry[objectType]=KalturaMediaEntry
&mediaEntry[name]=Introduction to DLI and Its Importance
&mediaEntry[description]=Stephen Wells introduces the session...
&mediaEntry[tags]=DLI, Deep Learning Institute, AI Education
&mediaEntry[displayInSearch]=1
```

The saved clip will go through server-side transcoding (status `4` = CONVERTING) and become `READY` (2) when processing completes.

### Step-by-Step curl Example: Full AI Clips Workflow

Set up shell variables (see [Session Guide](KALTURA_SESSION_GUIDE.md) for generating a KS):

```bash
export KALTURA_SERVICE_URL="https://www.kaltura.com/api_v3"
export KALTURA_PARTNER_ID="YOUR_PARTNER_ID"
export KALTURA_KS="YOUR_KS"
```

**Step 1: Order AI clip generation**

```bash
curl -X POST "$KALTURA_SERVICE_URL/service/reach_entryVendorTask/action/add" \
  -d "ks=$KALTURA_KS&format=1\
&entryVendorTask[objectType]=KalturaEntryVendorTask\
&entryVendorTask[entryId]=1_abc123def\
&entryVendorTask[reachProfileId]=1001\
&entryVendorTask[catalogItemId]=34832\
&entryVendorTask[taskJobData][objectType]=KalturaClipsVendorTaskData\
&entryVendorTask[taskJobData][outputLanguage]=English\
&entryVendorTask[taskJobData][clipsDuration]=120\
&entryVendorTask[taskJobData][instruction]=Generate+highlight+clips"
```

From the response, note the task `id` (e.g., `98765`).

**Step 2: Poll for completion**

```bash
curl -X POST "$KALTURA_SERVICE_URL/service/reach_entryVendorTask/action/get" \
  -d "ks=$KALTURA_KS&format=1\
&id=98765"
```

Poll every 30 seconds until `status` is `2` (READY) or `6` (ERROR). Typical completion time for AI clips is 30-60 seconds.

**Step 3: List generated clips**

```bash
curl -X POST "$KALTURA_SERVICE_URL/service/baseEntry/action/list" \
  -d "ks=$KALTURA_KS&format=1\
&filter[rootEntryIdIn]=1_abc123def\
&filter[statusIn]=1,2,4\
&filter[orderBy]=-createdAt\
&pager[pageSize]=500"
```

Each object in the response is a generated clip entry with AI-generated `name`, `description`, `tags`, and `duration`. Note the clip `id`, `duration`, and metadata for the next steps.

**Step 4: Save a clip as a standalone entry**

First, get a source flavor ID for trimming:

```bash
curl -X POST "$KALTURA_SERVICE_URL/service/flavorAsset/action/list" \
  -d "ks=$KALTURA_KS&format=1\
&filter[entryIdEqual]=1_abc123def"
```

From the response, find a flavor with `status` = `2` (READY) and note its `flavorParamsId` (e.g., `487091`).

Clone the source entry:

```bash
curl -X POST "$KALTURA_SERVICE_URL/service/baseEntry/action/clone" \
  -d "ks=$KALTURA_KS&format=1\
&entryId=1_abc123def\
&cloneOptions:item1:objectType=KalturaBaseEntryCloneOptionComponent\
&cloneOptions:item1:itemType=1\
&cloneOptions:item1:rule=1"
```

From the response, note the cloned entry `id` (e.g., `1_newclone99`).

Trim the cloned entry to the clip boundaries (offset and duration in **milliseconds**):

```bash
curl -X POST "$KALTURA_SERVICE_URL/service/media/action/updateContent" \
  -d "ks=$KALTURA_KS&format=1\
&entryId=1_newclone99\
&resource[objectType]=KalturaOperationResources\
&resource[resources][0][objectType]=KalturaOperationResource\
&resource[resources][0][resource][objectType]=KalturaEntryResource\
&resource[resources][0][resource][entryId]=1_abc123def\
&resource[resources][0][resource][flavorParamsId]=487091\
&resource[resources][0][operationAttributes][0][objectType]=KalturaClipAttributes\
&resource[resources][0][operationAttributes][0][offset]=0\
&resource[resources][0][operationAttributes][0][duration]=120000"
```

Set metadata on the saved clip using the AI-generated values from Step 3:

```bash
curl -X POST "$KALTURA_SERVICE_URL/service/media/action/update" \
  -d "ks=$KALTURA_KS&format=1\
&entryId=1_newclone99\
&mediaEntry[objectType]=KalturaMediaEntry\
&mediaEntry[name]=Introduction+to+DLI+and+Its+Importance\
&mediaEntry[description]=Stephen+Wells+introduces+the+session\
&mediaEntry[tags]=DLI,+Deep+Learning+Institute,+AI+Education\
&mediaEntry[displayInSearch]=1"
```

The saved clip will go through server-side transcoding (entry status `4` = CONVERTING) and become `READY` (status `2`) when processing completes.


## Output Types by Service

When a task completes, the result is automatically attached to the entry. The `outputObjectId` field tells you what was created.

| Service Feature | Output Type | How It's Attached |
|---|---|---|
| **Captions** (1) | Caption asset (SRT/DFXP/VTT) | `captionAsset` on the entry, auto-displayed if configured in REACH profile |
| **Translation** (2) | Caption asset in target language | `captionAsset` with target language |
| **Alignment** (3) | Time-synced caption asset | `captionAsset` aligned to audio |
| **Audio Description** (4) | Audio flavor track | `flavorAsset` added to the entry (narration mixed with original audio) |
| **Chaptering** (5) | Cue points | `cuePoint` entries marking chapter boundaries |
| **Dubbing** (7) | Audio flavor track | `flavorAsset` with dubbed audio in target language |
| **Live Caption** (8) | Real-time stream | Captions injected into the live HLS stream via WebSocket |
| **Extended Audio Description** (9) | VTT caption asset | `captionAsset` with `usage=1` (EAD), `displayOnPlayer=false` |
| **Clips** (10) | Child entries | New media entries linked via `rootEntryId` — each with AI-generated name/description/tags. See [AI Clips Workflow](#ai-clips-workflow-content-lab) |
| **Live Translation** (11) | Real-time stream | Translated captions injected into the live stream |
| **Quiz** (12) | Cue points | Quiz question cue points attached to the entry |
| **Summary** (13) | Metadata | Summary and auto-generated chapters applied to entry metadata |
| **Video Analysis** (14) | Metadata | OCR text and visual analysis results applied to entry metadata |
| **Moderation** (15) | Metadata | Moderation flags and scores applied to entry metadata |
| **Metadata Enrichment** (16) | Tags/keywords | Applied to entry metadata |
| **Document Enrichment** (18) | Metadata | Enriched metadata for document entries |
| **Sign Language** (19) | Child entry | New media entry linked via `parentEntryId` |


## REACH with Kaltura Agents

When used through the [Agents Manager](KALTURA_AGENTS_MANAGER_API.md), REACH tasks are created automatically. The Agents Manager's Action Definitions API returns `catalogItemId` values that map directly to the REACH `vendorCatalogItem` IDs described in this guide.

- Agents set `creationMode = 2` (AUTOMATIC) on tasks they create
- The agent handles task creation, status tracking, and retry logic
- Results are applied to entries in the same way as manual REACH orders

The Agents Manager supports these REACH services as automated actions: **captions, translation, dubbing, summary, moderation, and metadata enrichment**. For **AI Clips, Quiz, Live Captions, Live Translation, and Video Analysis**, use the REACH API directly via `entryVendorTask.add`. See the [Agents Manager guide](KALTURA_AGENTS_MANAGER_API.md#kaltura-reach--the-services-behind-agent-actions) for the full mapping.

You can mix approaches: use Agents for automated bulk processing, and the REACH API directly for on-demand or individual requests.


## Dictionaries (Custom Vocabularies)

For machine captioning, you can configure **dictionaries** on your REACH profile to improve accuracy for domain-specific terminology.

- One dictionary per language
- Maximum 8,000 characters
- Words/phrases separated by line breaks
- Configured via the `dictionaries` field on the REACH profile
- Passed automatically to the machine captioning engine with each task

For human captioning, use the `notes` field on the task to provide terminology guidance and context to the human editor.


## Error Handling

| Scenario | What Happens |
|---|---|
| Entry not ready yet | Task starts in PENDING_ENTRY_READY (8), auto-transitions to PENDING (1) when ready |
| Vendor processing fails | Task status becomes ERROR (6), check `errDescription` for details |
| Credit limit exceeded | Task creation fails with an API error |
| Access key expired | Vendor-side issue; key auto-extends based on catalog item TAT |
| KS expired / invalid | API returns 401/403; generate a new KS and retry |
| Kaltura API error | Response `objectType` is `KalturaAPIException` with `code` and `message` fields |

### Common API Error Codes

| Code | Meaning |
|---|---|
| `ENTRY_VENDOR_TASK_NOT_FOUND` | Task was cancelled/aborted (and deleted) or never existed |
| `ENTRY_NOT_READY` | Cannot order a task for an entry that has no content or is still processing |
| `SERVICE_ACCESS_CONTROL_RESTRICTED` | Missing or incorrect `serviceUrl` configuration |
| `INVALID_KS` | KS is expired, malformed, or lacks required privileges |


## Further Reading

- [REACH Overview](https://corp.kaltura.com/developer-suite/captions-enrichment-services-reach/) — product and vendor partner details
- [REACH Administration Guide](https://knowledge.kaltura.com/help/introduction-to-reach-captioning-enrichment) — service descriptions, ordering, and configuration
- [REACH Vendor API Integration](https://knowledge.kaltura.com/help/working-with-the-kaltura-api) — detailed vendor-side integration reference
- [REACH Integration FAQ](https://knowledge.kaltura.com/help/reach-integration-faq) — common questions on polling, statuses, formats, and edge cases
- [Kaltura Agents Manager](KALTURA_AGENTS_MANAGER_API.md) — automate REACH tasks with event-driven agents
- [Session Guide](KALTURA_SESSION_GUIDE.md) — generate the KS required for all REACH API calls
- [AppTokens](KALTURA_APPTOKENS_API.md) — secure server-to-server auth for production REACH integrations
- [Upload & Delivery](KALTURA_UPLOAD_AND_DELIVERY_API.md) — upload content before ordering REACH services
- [eSearch](KALTURA_ESEARCH_API.md) — search entries enriched by REACH captions and metadata
- [AI Genie](KALTURA_AI_GENIE_API.md) — conversational AI that benefits from REACH-generated transcripts
- [Player Embed](KALTURA_PLAYER_EMBED_GUIDE.md) — play entries with REACH-generated captions in the player

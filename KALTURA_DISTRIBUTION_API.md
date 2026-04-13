# Kaltura Content Distribution API

Kaltura's content distribution system pushes media to external platforms (YouTube, Facebook, FTP servers, cross-Kaltura accounts) via configurable connectors. Distribution profiles define how and when content is pushed to each target platform. Entry distributions track the per-entry lifecycle through a state machine — from validation and submission to status monitoring and error recovery.

**Base URL:** `https://www.kaltura.com/api_v3` (may differ by region/deployment)  
**Auth:** KS passed as `ks` parameter in POST form data (see [Session Guide](KALTURA_SESSION_GUIDE.md))  
**Format:** Form-encoded POST, `format=1` for JSON responses  
**Services:** `contentDistribution_distributionProvider`, `contentDistribution_distributionProfile`, `contentDistribution_entryDistribution`, `contentDistribution_genericDistributionProvider`, `contentDistribution_genericDistributionProviderAction`


# 1. Prerequisites

- A Kaltura account with the Content Distribution plugin enabled (contact your Kaltura account manager if distribution actions return `SERVICE_FORBIDDEN`)
- An ADMIN KS (type=2) with `disableentitlement` privilege for full distribution management
- At least one distribution profile configured (YouTube API, FTP, Cross-Kaltura, etc.)


# 2. Core Concepts

## 2.1 Distribution Workflow

1. **Configure a distribution profile** — defines the target platform, credentials, and automation rules
2. **Bind an entry to a profile** — creates an `entryDistribution` record linking the entry to the profile
3. **Validate** — checks that the entry meets the profile's requirements (flavors, thumbnails, metadata)
4. **Submit** — pushes the entry to the remote platform; status tracks progress through the state machine
5. **Monitor** — track status changes, dirty flags (content updated), and sunrise/sunset scheduling

## 2.2 Service Name Prefix

Distribution services use the `contentDistribution_` plugin prefix:

| Service | Full API Service Name |
|---------|----------------------|
| Distribution Provider | `contentDistribution_distributionProvider` |
| Distribution Profile | `contentDistribution_distributionProfile` |
| Entry Distribution | `contentDistribution_entryDistribution` |


# 3. Distribution Providers

## 3.1 Provider Types

Distribution providers define the available connector types. Providers are system-level (partner 0) and include built-in connectors for major platforms.

Key provider types:

| Provider Type | Name | Description |
|--------------|------|-------------|
| `1` (Generic) | Generic | Custom XSLT-based distribution |
| `2` (Syndication) | Syndication | Feed-based distribution bridge |
| `youtubeApiDistribution.YOUTUBE_API` | YouTube API | YouTube channel push via OAuth |
| `facebookDistribution.FACEBOOK` | Facebook | Facebook page push via OAuth |
| `crossKalturaDistribution.CROSS_KALTURA` | Cross-Kaltura | Multi-account content sync |
| `ftpDistribution.FTP` | FTP | FTP/SFTP/SCP/HTTPS/Aspera file push |
| `ftpDistribution.FTP_SCHEDULED` | FTP Scheduled | Scheduled FTP push |
| `podcastDistribution.PODCAST` | Podcast | Podcast RSS distribution |
| `dailymotionDistribution.DAILYMOTION` | Dailymotion | Video platform |
| `doubleClickDistribution.DOUBLECLICK` | DoubleClick | DFP/GAM ad monetization |
| `cortexApiDistribution.CORTEX_API` | Cortex API | Cortex API connector |
| `tvinciDistribution.TVINCI` | Tvinci | OTT/Tvinci platform |

## 3.2 distributionProvider.list

List all available distribution provider types on the account:

```bash
curl -X POST "$KALTURA_SERVICE_URL/service/contentDistribution_distributionProvider/action/list" \
  -d "ks=$KALTURA_KS" \
  -d "format=1"
```

**Response** includes provider objects with `type`, `name`, and `objectType` identifying the connector:

```json
{
  "objects": [
    {
      "type": 1,
      "name": "Default",
      "objectType": "KalturaGenericDistributionProvider"
    },
    {
      "type": "youtubeApiDistribution.YOUTUBE_API",
      "name": "YoutubeApi",
      "objectType": "KalturaYoutubeApiDistributionProvider"
    }
  ],
  "totalCount": 33,
  "objectType": "KalturaDistributionProviderListResponse"
}
```


# 4. Distribution Profile Management

Distribution profiles configure how content is distributed to a specific target platform. Each profile specifies the provider type, automation rules (automatic vs manual submit/update/delete), required assets, and provider-specific settings.

## 4.1 Profile Object Fields

Base fields (all `KalturaDistributionProfile` subtypes):

| Field | Type | Description |
|-------|------|-------------|
| `id` | int | Profile ID (auto-assigned) |
| `name` | string | Display name |
| `status` | int | 1=DISABLED, 2=ENABLED |
| `providerType` | string | Provider identifier (e.g., `youtubeApiDistribution.YOUTUBE_API`) |
| `submitEnabled` | int | 1=DISABLED, 2=AUTOMATIC, 3=MANUAL |
| `updateEnabled` | int | 1=DISABLED, 2=AUTOMATIC, 3=MANUAL |
| `deleteEnabled` | int | 1=DISABLED, 2=AUTOMATIC, 3=MANUAL |
| `reportEnabled` | int | 1=DISABLED, 2=AUTOMATIC |
| `requiredFlavorParamsIds` | string | Comma-separated flavor params IDs required (e.g., `"0"` = source) |
| `optionalFlavorParamsIds` | string | Comma-separated optional flavor params IDs |
| `requiredThumbDimensions` | array | Required thumbnail sizes |
| `optionalThumbDimensions` | array | Optional thumbnail sizes |
| `autoCreateFlavors` | bool | Auto-create missing flavors during validation |
| `autoCreateThumb` | bool | Auto-create missing thumbnails during validation |
| `distributeTrigger` | int | 1=ENTRY_READY, 2=MODERATION_APPROVED |
| `sunriseDefaultOffset` | int | Default sunrise offset in seconds |
| `sunsetDefaultOffset` | int | Default sunset offset in seconds |

**Action status values:**

| Value | Name | Description |
|-------|------|-------------|
| 1 | DISABLED | Action is off |
| 2 | AUTOMATIC | Triggered automatically when conditions are met |
| 3 | MANUAL | Requires an explicit API call |

## 4.2 distributionProfile.add

Create a new distribution profile. The `objectType` and provider-specific fields vary by connector type.

```bash
curl -X POST "$KALTURA_SERVICE_URL/service/contentDistribution_distributionProfile/action/add" \
  -d "ks=$KALTURA_KS" \
  -d "format=1" \
  -d "partnerId=$KALTURA_PARTNER_ID" \
  -d "distributionProfile[objectType]=KalturaYoutubeApiDistributionProfile" \
  -d "distributionProfile[name]=My YouTube Channel" \
  -d "distributionProfile[submitEnabled]=3" \
  -d "distributionProfile[updateEnabled]=2" \
  -d "distributionProfile[deleteEnabled]=2" \
  -d "distributionProfile[reportEnabled]=1" \
  -d "distributionProfile[distributeTrigger]=1" \
  -d "distributionProfile[requiredFlavorParamsIds]=0" \
  -d "distributionProfile[defaultCategory]=22" \
  -d "distributionProfile[allowComments]=allowed" \
  -d "distributionProfile[allowEmbedding]=allowed" \
  -d "distributionProfile[allowRatings]=allowed"
```

**The `partnerId` parameter is required in the request body.** The distribution plugin uses the request-level `partnerId` (not the KS) to associate the profile with your account. Omitting it creates an orphaned profile that cannot be retrieved.  

Profile creation requires provider-specific configuration (OAuth credentials for YouTube/Facebook, connection details for FTP, target account details for Cross-Kaltura). Profiles are typically configured through the KMC (Kaltura Management Console) and then managed via API.

## 4.3 distributionProfile.get

Retrieve a distribution profile by ID:

```bash
curl -X POST "$KALTURA_SERVICE_URL/service/contentDistribution_distributionProfile/action/get" \
  -d "ks=$KALTURA_KS" \
  -d "format=1" \
  -d "id=$DISTRIBUTION_PROFILE_ID"
```

**Response** includes all base fields plus provider-specific fields:

```json
{
  "id": 413741,
  "name": "YouTube Distribution Demo",
  "providerType": "youtubeApiDistribution.YOUTUBE_API",
  "status": 2,
  "submitEnabled": 3,
  "updateEnabled": 3,
  "deleteEnabled": 2,
  "requiredFlavorParamsIds": "0",
  "distributeTrigger": 1,
  "defaultCategory": 24,
  "allowComments": "allowed",
  "allowEmbedding": "allowed",
  "objectType": "KalturaYoutubeApiDistributionProfile"
}
```

## 4.4 distributionProfile.list

List distribution profiles with optional filters:

```bash
curl -X POST "$KALTURA_SERVICE_URL/service/contentDistribution_distributionProfile/action/list" \
  -d "ks=$KALTURA_KS" \
  -d "format=1"
```

Filter by status:

```bash
curl -X POST "$KALTURA_SERVICE_URL/service/contentDistribution_distributionProfile/action/list" \
  -d "ks=$KALTURA_KS" \
  -d "format=1" \
  -d "filter[objectType]=KalturaDistributionProfileFilter" \
  -d "filter[statusEqual]=2"
```

## 4.5 distributionProfile.update

Update distribution profile fields:

```bash
curl -X POST "$KALTURA_SERVICE_URL/service/contentDistribution_distributionProfile/action/update" \
  -d "ks=$KALTURA_KS" \
  -d "format=1" \
  -d "id=$DISTRIBUTION_PROFILE_ID" \
  -d "distributionProfile[objectType]=KalturaYoutubeApiDistributionProfile" \
  -d "distributionProfile[name]=Updated YouTube Channel" \
  -d "distributionProfile[submitEnabled]=2"
```

The `protocol` field on FTP profiles is immutable after creation — include it in the `add` call but do not attempt to update it. Updating `protocol` returns `PROPERTY_VALIDATION_NOT_UPDATABLE` and rejects the entire request. To change protocol, delete the profile and create a new one.

## 4.6 distributionProfile.updateStatus

Enable or disable a distribution profile:

```bash
# Disable
curl -X POST "$KALTURA_SERVICE_URL/service/contentDistribution_distributionProfile/action/updateStatus" \
  -d "ks=$KALTURA_KS" \
  -d "format=1" \
  -d "id=$DISTRIBUTION_PROFILE_ID" \
  -d "status=1"
```

```bash
# Re-enable
curl -X POST "$KALTURA_SERVICE_URL/service/contentDistribution_distributionProfile/action/updateStatus" \
  -d "ks=$KALTURA_KS" \
  -d "format=1" \
  -d "id=$DISTRIBUTION_PROFILE_ID" \
  -d "status=2"
```

## 4.7 distributionProfile.delete

Delete a distribution profile:

```bash
curl -X POST "$KALTURA_SERVICE_URL/service/contentDistribution_distributionProfile/action/delete" \
  -d "ks=$KALTURA_KS" \
  -d "format=1" \
  -d "id=$DISTRIBUTION_PROFILE_ID"
```


# 5. Entry Distribution Lifecycle

Entry distributions bind a specific media entry to a distribution profile, tracking the full lifecycle of distributing that entry to the external platform.

## 5.1 Entry Distribution Object Fields

| Field | Type | Description |
|-------|------|-------------|
| `id` | int | Entry distribution ID (auto-assigned) |
| `entryId` | string | The Kaltura entry ID |
| `distributionProfileId` | int | The distribution profile ID |
| `status` | int | Current status (see section 10.1) |
| `dirtyStatus` | int | What changed since last sync (see section 10.3) |
| `sunStatus` | int | Sunrise/sunset state (see section 10.3) |
| `thumbAssetIds` | string | Comma-separated thumbnail asset IDs to distribute |
| `flavorAssetIds` | string | Comma-separated flavor asset IDs to distribute |
| `sunrise` | int | Unix timestamp — content becomes active |
| `sunset` | int | Unix timestamp — content expires |
| `remoteId` | string | ID assigned by the remote platform (e.g., YouTube video ID) |
| `validationErrors` | array | Validation failures from the last validate call |
| `errorType` | int | Error category if status is ERROR_* |
| `errorNumber` | int | Provider-specific error code |
| `errorDescription` | string | Human-readable error message |

## 5.2 entryDistribution.add

Bind an entry to a distribution profile:

```bash
curl -X POST "$KALTURA_SERVICE_URL/service/contentDistribution_entryDistribution/action/add" \
  -d "ks=$KALTURA_KS" \
  -d "format=1" \
  -d "entryDistribution[objectType]=KalturaEntryDistribution" \
  -d "entryDistribution[entryId]=$ENTRY_ID" \
  -d "entryDistribution[distributionProfileId]=$DISTRIBUTION_PROFILE_ID"
```

The new entry distribution starts in PENDING status (0). Optionally set `thumbAssetIds` and `flavorAssetIds` to control which assets are distributed, and `sunrise`/`sunset` for time-based scheduling.

## 5.3 entryDistribution.validate

Validate an entry against the distribution profile requirements before submitting:

```bash
curl -X POST "$KALTURA_SERVICE_URL/service/contentDistribution_entryDistribution/action/validate" \
  -d "ks=$KALTURA_KS" \
  -d "format=1" \
  -d "id=$ENTRY_DISTRIBUTION_ID"
```

**Response** includes `validationErrors` array with detailed error objects:

```json
{
  "id": 93294543,
  "status": 0,
  "validationErrors": [
    {
      "objectType": "KalturaDistributionValidationErrorMissingFlavor",
      "action": 1,
      "errorType": 1,
      "flavorParamsId": "0",
      "description": "missing flavor param"
    }
  ]
}
```

Validation checks:
- **Required flavors** — entry must have all flavors listed in `requiredFlavorParamsIds`
- **Required thumbnails** — entry must have thumbnails matching `requiredThumbDimensions`
- **Required metadata** — provider-specific required fields must be present
- **Data format** — field values must pass format validation (string length, allowed values)

If `autoCreateFlavors` or `autoCreateThumb` is enabled on the profile, missing assets are automatically queued for creation.

## 5.4 entryDistribution.submitAdd

Submit an entry to the remote platform:

```bash
curl -X POST "$KALTURA_SERVICE_URL/service/contentDistribution_entryDistribution/action/submitAdd" \
  -d "ks=$KALTURA_KS" \
  -d "format=1" \
  -d "id=$ENTRY_DISTRIBUTION_ID" \
  -d "submitWhenReady=true"
```

The `submitWhenReady` parameter (boolean):
- `true` — if the entry is still processing, queue the submission until the entry reaches READY status
- `false` — submit immediately; fails if entry is not ready

The submission pipeline:
1. Checks `profile.submitEnabled` is not DISABLED
2. Validates the entry against profile requirements
3. If the entry is not ready and `submitWhenReady=true`, queues with status QUEUED (1)
4. If sunrise is in the future, queues until the sunrise time
5. If validation passes, creates a batch job and sets status to SUBMITTING (4)
6. On success, status becomes READY (2) and `remoteId` is populated with the external platform ID

## 5.5 entryDistribution.list

List entry distributions with filters:

```bash
# List all entry distributions
curl -X POST "$KALTURA_SERVICE_URL/service/contentDistribution_entryDistribution/action/list" \
  -d "ks=$KALTURA_KS" \
  -d "format=1"
```

```bash
# Filter by entry ID
curl -X POST "$KALTURA_SERVICE_URL/service/contentDistribution_entryDistribution/action/list" \
  -d "ks=$KALTURA_KS" \
  -d "format=1" \
  -d "filter[objectType]=KalturaEntryDistributionFilter" \
  -d "filter[entryIdEqual]=$ENTRY_ID"
```

```bash
# Filter by distribution profile
curl -X POST "$KALTURA_SERVICE_URL/service/contentDistribution_entryDistribution/action/list" \
  -d "ks=$KALTURA_KS" \
  -d "format=1" \
  -d "filter[objectType]=KalturaEntryDistributionFilter" \
  -d "filter[distributionProfileIdEqual]=$DISTRIBUTION_PROFILE_ID"
```

```bash
# Filter by status
curl -X POST "$KALTURA_SERVICE_URL/service/contentDistribution_entryDistribution/action/list" \
  -d "ks=$KALTURA_KS" \
  -d "format=1" \
  -d "filter[objectType]=KalturaEntryDistributionFilter" \
  -d "filter[statusEqual]=2"
```

## 5.6 entryDistribution.get

Retrieve a specific entry distribution:

```bash
curl -X POST "$KALTURA_SERVICE_URL/service/contentDistribution_entryDistribution/action/get" \
  -d "ks=$KALTURA_KS" \
  -d "format=1" \
  -d "id=$ENTRY_DISTRIBUTION_ID"
```

## 5.7 entryDistribution.update

Update entry distribution fields (sunrise/sunset scheduling, asset selection):

```bash
curl -X POST "$KALTURA_SERVICE_URL/service/contentDistribution_entryDistribution/action/update" \
  -d "ks=$KALTURA_KS" \
  -d "format=1" \
  -d "id=$ENTRY_DISTRIBUTION_ID" \
  -d "entryDistribution[objectType]=KalturaEntryDistribution" \
  -d "entryDistribution[sunrise]=$SUNRISE_TIMESTAMP" \
  -d "entryDistribution[sunset]=$SUNSET_TIMESTAMP"
```

## 5.8 entryDistribution.submitUpdate

Push metadata or content updates to the remote platform:

```bash
curl -X POST "$KALTURA_SERVICE_URL/service/contentDistribution_entryDistribution/action/submitUpdate" \
  -d "ks=$KALTURA_KS" \
  -d "format=1" \
  -d "id=$ENTRY_DISTRIBUTION_ID"
```

Valid when current status is READY (2), ERROR_UPDATING (8), ERROR_DELETING (9), or IMPORT_UPDATING (12).

## 5.9 entryDistribution.submitDelete

Remove the entry from the remote platform:

```bash
curl -X POST "$KALTURA_SERVICE_URL/service/contentDistribution_entryDistribution/action/submitDelete" \
  -d "ks=$KALTURA_KS" \
  -d "format=1" \
  -d "id=$ENTRY_DISTRIBUTION_ID"
```

Valid when current status is READY (2), ERROR_DELETING (9), or ERROR_UPDATING (8).

## 5.10 entryDistribution.submitFetchReport

Request a delivery report from the remote platform:

```bash
curl -X POST "$KALTURA_SERVICE_URL/service/contentDistribution_entryDistribution/action/submitFetchReport" \
  -d "ks=$KALTURA_KS" \
  -d "format=1" \
  -d "id=$ENTRY_DISTRIBUTION_ID"
```

Valid only when status is READY (2). The distribution profile must have `reportEnabled` set to AUTOMATIC (2).

## 5.11 entryDistribution.retrySubmit

Retry the last failed operation:

```bash
curl -X POST "$KALTURA_SERVICE_URL/service/contentDistribution_entryDistribution/action/retrySubmit" \
  -d "ks=$KALTURA_KS" \
  -d "format=1" \
  -d "id=$ENTRY_DISTRIBUTION_ID"
```

Use this when an entry distribution is in an ERROR_* status to re-attempt the failed operation.

## 5.12 entryDistribution.serveSentData / serveReturnedData

Retrieve the raw XML data sent to or received from the remote platform for debugging:

```bash
# Get XML sent to the remote platform (actionType: 1=SUBMIT, 2=UPDATE, 3=DELETE)
curl -X POST "$KALTURA_SERVICE_URL/service/contentDistribution_entryDistribution/action/serveSentData" \
  -d "ks=$KALTURA_KS" \
  -d "format=1" \
  -d "id=$ENTRY_DISTRIBUTION_ID" \
  -d "actionType=1"
```

```bash
# Get XML returned from the remote platform
curl -X POST "$KALTURA_SERVICE_URL/service/contentDistribution_entryDistribution/action/serveReturnedData" \
  -d "ks=$KALTURA_KS" \
  -d "format=1" \
  -d "id=$ENTRY_DISTRIBUTION_ID" \
  -d "actionType=1"
```

These endpoints return `text/html` with the raw XML payload. The body is empty (0 bytes) if no data exists for the given action type — this is normal for entries that have not yet been submitted or for action types that have not been executed.

**Action type values:**

| Value | Name |
|-------|------|
| 1 | SUBMIT |
| 2 | UPDATE |
| 3 | DELETE |

## 5.13 entryDistribution.delete

Delete the entry distribution record:

```bash
curl -X POST "$KALTURA_SERVICE_URL/service/contentDistribution_entryDistribution/action/delete" \
  -d "ks=$KALTURA_KS" \
  -d "format=1" \
  -d "id=$ENTRY_DISTRIBUTION_ID"
```

This removes the entry distribution record. To also remove the content from the remote platform, call `submitDelete` first.


# 6. Distribution Triggers & Automation

## 6.1 Automatic Distribution on Entry Ready

When `submitEnabled=2` (AUTOMATIC) and `distributeTrigger=1` (ENTRY_READY), entries are automatically submitted to the remote platform when they finish processing:

```bash
curl -X POST "$KALTURA_SERVICE_URL/service/contentDistribution_distributionProfile/action/update" \
  -d "ks=$KALTURA_KS" \
  -d "format=1" \
  -d "id=$DISTRIBUTION_PROFILE_ID" \
  -d "distributionProfile[objectType]=KalturaYoutubeApiDistributionProfile" \
  -d "distributionProfile[submitEnabled]=2" \
  -d "distributionProfile[distributeTrigger]=1"
```

## 6.2 Moderation-Gated Distribution

When `distributeTrigger=2` (MODERATION_APPROVED), entries are only submitted after passing content moderation:

```bash
curl -X POST "$KALTURA_SERVICE_URL/service/contentDistribution_distributionProfile/action/update" \
  -d "ks=$KALTURA_KS" \
  -d "format=1" \
  -d "id=$DISTRIBUTION_PROFILE_ID" \
  -d "distributionProfile[objectType]=KalturaYoutubeApiDistributionProfile" \
  -d "distributionProfile[distributeTrigger]=2"
```

## 6.3 Sunrise / Sunset Scheduling

Control when distributed content becomes active and expires using Unix timestamps:

```bash
curl -X POST "$KALTURA_SERVICE_URL/service/contentDistribution_entryDistribution/action/update" \
  -d "ks=$KALTURA_KS" \
  -d "format=1" \
  -d "id=$ENTRY_DISTRIBUTION_ID" \
  -d "entryDistribution[objectType]=KalturaEntryDistribution" \
  -d "entryDistribution[sunrise]=1735689600" \
  -d "entryDistribution[sunset]=1738368000"
```

The `sunStatus` field tracks the current state:

| Value | Name | Description |
|-------|------|-------------|
| 1 | BEFORE_SUNRISE | Content not yet active — queued for future activation |
| 2 | AFTER_SUNRISE | Content is active |
| 3 | AFTER_SUNSET | Content has expired |

When `submitWhenReady=true` and sunrise is in the future, the entry distribution is queued and automatically submitted at the sunrise time.

## 6.4 Dirty Status & Update Propagation

When a distributed entry changes (metadata update, new flavors, thumbnail change), the `dirtyStatus` is set:

| Value | Name | Description |
|-------|------|-------------|
| 0 | NONE | Clean — no pending changes |
| 1 | SUBMIT_REQUIRED | Content needs initial submission |
| 2 | DELETE_REQUIRED | Content needs removal from remote |
| 3 | UPDATE_REQUIRED | Metadata or content changed since last sync |
| 4 | ENABLE_REQUIRED | Distribution needs re-enabling |

When `updateEnabled=2` (AUTOMATIC), the system auto-submits updates when the dirty flag is set. When `updateEnabled=3` (MANUAL), call `submitUpdate` explicitly to push changes.

## 6.5 Status State Machine

The distribution engine enforces strict status transitions:

| Action | Valid From Statuses |
|--------|-------------------|
| `submitAdd` | PENDING (0), QUEUED (1), ERROR_SUBMITTING (7), ERROR_UPDATING (8), ERROR_DELETING (9), IMPORT_SUBMITTING (11), READY (2), REMOVED (10) |
| `submitUpdate` | READY (2), ERROR_UPDATING (8), ERROR_DELETING (9), IMPORT_UPDATING (12) |
| `submitDelete` | READY (2), ERROR_DELETING (9), ERROR_UPDATING (8) |
| `submitFetchReport` | READY (2) only |


# 7. Distribution Connector Reference

## 7.1 YouTube API Distribution

The YouTube API connector pushes video entries to a YouTube channel via OAuth 2.0.

**Profile type:** `KalturaYoutubeApiDistributionProfile`  
**Provider type:** `youtubeApiDistribution.YOUTUBE_API`

Key fields:

| Field | Description |
|-------|-------------|
| `username` | YouTube channel username |
| `defaultCategory` | Default YouTube category ID |
| `allowComments` | `allowed` or `denied` |
| `allowEmbedding` | `allowed` or `denied` |
| `allowRatings` | `allowed` or `denied` |
| `privacyStatus` | `public`, `private`, or `unlisted` |
| `googleClientId` | OAuth 2.0 client ID |
| `googleClientSecret` | OAuth 2.0 client secret |
| `apiAuthorizeUrl` | OAuth authorization URL (auto-generated) |

When an entry is successfully distributed to YouTube, the `remoteId` field on the entry distribution is populated with the YouTube video ID.

## 7.2 Facebook Distribution

The Facebook connector pushes video entries to a Facebook page.

**Profile type:** `KalturaFacebookDistributionProfile`  
**Provider type:** `facebookDistribution.FACEBOOK`

Key fields:

| Field | Description |
|-------|-------------|
| `pageId` | Target Facebook page ID |
| `pageAccessToken` | Page-level access token |
| `userAccessToken` | User-level access token |
| `apiAuthorizeUrl` | OAuth authorization URL |
| `permissions` | Requested Facebook permissions |

## 7.3 Cross-Kaltura Distribution

The Cross-Kaltura connector syncs content between Kaltura accounts, including metadata, flavors, thumbnails, captions, and cue points.

**Profile type:** `KalturaCrossKalturaDistributionProfile`  
**Provider type:** `crossKalturaDistribution.CROSS_KALTURA`

Key fields:

| Field | Description |
|-------|-------------|
| `targetServiceUrl` | Destination Kaltura API URL |
| `targetAccountId` | Destination partner ID |
| `targetLoginId` / `targetLoginPassword` | Auth credentials for target account |
| `metadataXslt` | XSLT to transform metadata between accounts |
| `distributeCaptions` | Push caption assets |
| `distributeCuePoints` | Push cue points |
| `distributeRemoteFlavorAssetContent` | Push flavor files |
| `distributeRemoteThumbAssetContent` | Push thumbnail files |
| `mapAccessControlProfileIds` | Source-to-target access control ID mapping |
| `mapConversionProfileIds` | Source-to-target conversion profile mapping |
| `mapMetadataProfileIds` | Source-to-target metadata profile mapping |

## 7.4 FTP Distribution

The FTP connector pushes content and MRSS metadata files to an FTP/SFTP/SCP server.

**Profile type:** `KalturaFtpDistributionProfile`  
**Provider type:** `ftpDistribution.FTP`

Key fields:

| Field | Description |
|-------|-------------|
| `protocol` | 1=FTP, 2=SCP, 3=SFTP, 5=HTTPS, 10=ASPERA |
| `host`, `port` | Server connection |
| `basePath` | Remote directory path |
| `username`, `password` | Auth credentials |
| `sftpPublicKey`, `sftpPrivateKey` | SFTP key-based auth |
| `metadataXslt` | XSLT for MRSS transformation |
| `flavorAssetFilenameXslt` | XSLT to generate flavor filenames |
| `thumbnailAssetFilenameXslt` | XSLT for thumbnail filenames |
| `disableMetadata` | Skip MRSS metadata file |
| `sendMetadataAfterAssets` | Send MRSS file after asset uploads |


# 8. MRSS & Field Configuration

## 8.1 MRSS Structure

Kaltura generates an internal MRSS (Media RSS) feed for each entry that includes all metadata, content URLs, thumbnails, and distribution-specific data. This MRSS is the input for distribution connectors — each connector transforms it into the provider-specific format.

Each entry's MRSS includes a `<distribution>` block per active distribution:

```xml
<distribution entryDistributionId="[ID]"
              distributionProfileId="[ID]"
              distributionProfileName="[name]"
              provider="[provider_name]">
  <remoteId>[YouTube video ID, etc.]</remoteId>
  <sunrise>[timestamp]</sunrise>
  <sunset>[timestamp]</sunset>
  <flavorAssetIds>
    <flavorAssetId>[ID]</flavorAssetId>
  </flavorAssetIds>
  <thumbAssetIds>
    <thumbAssetId>[ID]</thumbAssetId>
  </thumbAssetIds>
  <status>[status]</status>
  <dirtyStatus>[status]</dirtyStatus>
  <sunStatus>[status]</sunStatus>
</distribution>
```

## 8.2 Field Configuration (fieldConfigArray)

Configurable distribution profiles (YouTube, Facebook, etc.) use `fieldConfigArray` to map Kaltura MRSS elements to provider fields:

```json
{
  "fieldName": "MEDIA_TITLE",
  "userFriendlyFieldName": "Entry name",
  "entryMrssXslt": "<xsl:value-of select=\"string(title)\" />",
  "isRequired": 1,
  "updateOnChange": true,
  "updateParams": [{ "value": "entry.NAME" }]
}
```

| Field | Description |
|-------|-------------|
| `fieldName` | Provider field identifier (e.g., `MEDIA_TITLE`, `MEDIA_DESCRIPTION`, `MEDIA_KEYWORDS`) |
| `entryMrssXslt` | XSLT expression to extract the value from MRSS |
| `isRequired` | 1=REQUIRED, 2=NOT_REQUIRED, 3=SYSTEM |
| `updateOnChange` | When `true`, changes to the mapped entry field set the `dirtyStatus` flag |
| `updateParams` | Entry field names that trigger the update check |

When `updateOnChange=true` and the corresponding entry field changes, the `dirtyStatus` is automatically set, triggering an update cycle if `updateEnabled=AUTOMATIC`.


# 9. Building a Custom Connector

Kaltura's built-in connectors cover major platforms (YouTube, Facebook, FTP, Cross-Kaltura). For platforms not covered by a built-in connector, there are two paths:

- **Generic Distribution (XSLT-based)** — Configure a custom connector entirely through API calls. Kaltura's internal MRSS feed (section 8.1) is transformed into the target platform's expected format via XSLT and delivered over FTP, SFTP, SCP, HTTP, or HTTPS. This approach works for any target that accepts XML or file-based ingest.

- **Custom built-in connector** — For platforms requiring OAuth authentication, complex REST API interactions, or custom business logic beyond XML transformation, contact your Kaltura account manager to submit a feature request for a new built-in distribution connector. Built-in connectors are developed and maintained by Kaltura as server-side plugins.

The rest of this section covers the Generic Distribution approach.

## 9.1 Generic Distribution Provider

A Generic Distribution Provider defines a custom connector type. It specifies the provider's name, required and optional assets, and which entry fields trigger distribution updates.

```bash
curl -X POST "$KALTURA_SERVICE_URL/service/contentDistribution_genericDistributionProvider/action/add" \
  -d "ks=$KALTURA_KS" \
  -d "format=1" \
  -d "genericDistributionProvider[name]=My Custom Platform" \
  -d "genericDistributionProvider[requiredFlavorParamsIds]=0" \
  -d "genericDistributionProvider[optionalFlavorParamsIds]=487041" \
  -d "genericDistributionProvider[isDefault]=false"
```

**Response:**

```json
{
  "id": 123,
  "name": "My Custom Platform",
  "partnerId": 976461,
  "status": 1,
  "isDefault": false,
  "requiredFlavorParamsIds": "0",
  "optionalFlavorParamsIds": "487041",
  "objectType": "KalturaGenericDistributionProvider"
}
```

**Provider fields:**

| Field | Type | Description |
|-------|------|-------------|
| `id` | int | Provider ID (auto-assigned, read-only) |
| `name` | string | Display name (required) |
| `status` | int | 1=ACTIVE, 2=DELETED (read-only) |
| `isDefault` | bool | Whether this is the default generic provider |
| `requiredFlavorParamsIds` | string | Comma-separated flavor params IDs that entries must have |
| `optionalFlavorParamsIds` | string | Comma-separated optional flavor params IDs |
| `requiredThumbDimensions` | array | Required thumbnail sizes for validation |
| `optionalThumbDimensions` | array | Optional thumbnail sizes |
| `editableFields` | string | Fields users can edit per entry distribution |
| `mandatoryFields` | string | Fields that must be filled before submission |

**Other provider actions:**

```bash
# Get provider by ID
curl -X POST "$KALTURA_SERVICE_URL/service/contentDistribution_genericDistributionProvider/action/get" \
  -d "ks=$KALTURA_KS" \
  -d "format=1" \
  -d "id=$GENERIC_PROVIDER_ID"

# List providers
curl -X POST "$KALTURA_SERVICE_URL/service/contentDistribution_genericDistributionProvider/action/list" \
  -d "ks=$KALTURA_KS" \
  -d "format=1"

# Update provider
curl -X POST "$KALTURA_SERVICE_URL/service/contentDistribution_genericDistributionProvider/action/update" \
  -d "ks=$KALTURA_KS" \
  -d "format=1" \
  -d "id=$GENERIC_PROVIDER_ID" \
  -d "genericDistributionProvider[name]=Updated Platform Name"

# Delete provider
curl -X POST "$KALTURA_SERVICE_URL/service/contentDistribution_genericDistributionProvider/action/delete" \
  -d "ks=$KALTURA_KS" \
  -d "format=1" \
  -d "id=$GENERIC_PROVIDER_ID"
```

## 9.2 Provider Actions

Each provider needs one or more **actions** that define how content is delivered to the target platform. Create a separate action for each operation the connector supports.

**Action types:**

| Value | Name | Description |
|-------|------|-------------|
| 1 | SUBMIT | Initial content push to remote platform |
| 2 | UPDATE | Push metadata or content updates |
| 3 | DELETE | Remove content from remote platform |
| 4 | FETCH_REPORT | Retrieve delivery/engagement reports |

**Delivery protocols:**

| Value | Name |
|-------|------|
| 1 | FTP |
| 2 | SCP |
| 3 | SFTP |
| 4 | HTTP |
| 5 | HTTPS |

```bash
# Create a SUBMIT action that delivers XML via SFTP
curl -X POST "$KALTURA_SERVICE_URL/service/contentDistribution_genericDistributionProviderAction/action/add" \
  -d "ks=$KALTURA_KS" \
  -d "format=1" \
  -d "genericDistributionProviderAction[genericDistributionProviderId]=$GENERIC_PROVIDER_ID" \
  -d "genericDistributionProviderAction[action]=1" \
  -d "genericDistributionProviderAction[protocol]=3" \
  -d "genericDistributionProviderAction[serverAddress]=sftp.targetplatform.com" \
  -d "genericDistributionProviderAction[remotePath]=/ingest/incoming" \
  -d "genericDistributionProviderAction[remoteUsername]=kaltura_feed" \
  -d "genericDistributionProviderAction[remotePassword]=secret"
```

**Response:**

```json
{
  "id": 456,
  "genericDistributionProviderId": 123,
  "action": 1,
  "status": 1,
  "protocol": 3,
  "serverAddress": "sftp.targetplatform.com",
  "remotePath": "/ingest/incoming",
  "remoteUsername": "kaltura_feed",
  "objectType": "KalturaGenericDistributionProviderAction"
}
```

**Action fields:**

| Field | Type | Description |
|-------|------|-------------|
| `id` | int | Action ID (auto-assigned, read-only) |
| `genericDistributionProviderId` | int | Parent provider ID (insert-only) |
| `action` | int | Action type: 1=SUBMIT, 2=UPDATE, 3=DELETE, 4=FETCH_REPORT (insert-only) |
| `status` | int | 1=ACTIVE, 2=DELETED (read-only) |
| `protocol` | int | Delivery protocol (see table above) |
| `serverAddress` | string | Target server hostname or URL |
| `remotePath` | string | Path on the target server (supports `{REMOTE_ID}` placeholder) |
| `remoteUsername` | string | Authentication username |
| `remotePassword` | string | Authentication password |
| `resultsParser` | int | How to parse the remote response: 1=XSL, 2=XPATH, 3=REGEX |
| `editableFields` | string | Editable field names for this action |
| `mandatoryFields` | string | Required field names for this action |
| `mrssTransformer` | string | The XSLT transform (read-only — set via `addMrssTransform`) |
| `mrssValidator` | string | The XSD validator (read-only — set via `addMrssValidate`) |
| `resultsTransformer` | string | The results parser data (read-only — set via `addResultsTransform`) |

The `remotePath` field supports the `{REMOTE_ID}` placeholder, which is replaced with the entry distribution's `remoteId` at runtime. This is useful for UPDATE and DELETE actions that target a specific remote resource.

## 9.3 XSLT Transforms

Three transforms can be attached to each provider action to control the data pipeline:

**MRSS Transformer** — XSLT stylesheet that converts Kaltura's internal MRSS (section 8.1) into the target platform's expected XML format. This is where you map Kaltura entry fields (title, description, tags, content URLs) to the target's schema.

**MRSS Validator** — XSD schema that validates the transformed XML before delivery. If validation fails, the distribution job reports a validation error instead of sending malformed data.

**Results Transformer** — Parses the target platform's response to extract the `remoteId` (the external platform's identifier for the distributed content). Three parser types are supported:

| Value | Parser | Description |
|-------|--------|-------------|
| 1 | XSL | Apply XSLT to the response XML, extract comma-separated values |
| 2 | XPATH | Evaluate an XPath expression against the response XML |
| 3 | REGEX | Match a regular expression against the response body |

### Upload transforms

Transforms are uploaded separately after creating the action:

```bash
# Upload MRSS transform XSLT
curl -X POST "$KALTURA_SERVICE_URL/service/contentDistribution_genericDistributionProviderAction/action/addMrssTransform" \
  -d "ks=$KALTURA_KS" \
  -d "format=1" \
  -d "id=$ACTION_ID" \
  --data-urlencode "xslData=<xsl:stylesheet version=\"1.0\" xmlns:xsl=\"http://www.w3.org/1999/XSL/Transform\">
  <xsl:output method=\"xml\" indent=\"yes\"/>
  <xsl:template match=\"/\">
    <item>
      <title><xsl:value-of select=\"//item/title\"/></title>
      <description><xsl:value-of select=\"//item/description\"/></description>
      <videoUrl><xsl:value-of select=\"//item/content/@url\"/></videoUrl>
    </item>
  </xsl:template>
</xsl:stylesheet>"
```

```bash
# Upload MRSS validation XSD
curl -X POST "$KALTURA_SERVICE_URL/service/contentDistribution_genericDistributionProviderAction/action/addMrssValidate" \
  -d "ks=$KALTURA_KS" \
  -d "format=1" \
  -d "id=$ACTION_ID" \
  --data-urlencode "xsdData=<xs:schema xmlns:xs=\"http://www.w3.org/2001/XMLSchema\">
  <xs:element name=\"item\">
    <xs:complexType>
      <xs:sequence>
        <xs:element name=\"title\" type=\"xs:string\"/>
        <xs:element name=\"description\" type=\"xs:string\"/>
        <xs:element name=\"videoUrl\" type=\"xs:anyURI\"/>
      </xs:sequence>
    </xs:complexType>
  </xs:element>
</xs:schema>"
```

```bash
# Upload results transform (XPath to extract remote ID from response)
curl -X POST "$KALTURA_SERVICE_URL/service/contentDistribution_genericDistributionProviderAction/action/addResultsTransform" \
  -d "ks=$KALTURA_KS" \
  -d "format=1" \
  -d "id=$ACTION_ID" \
  --data-urlencode "transformData=//response/id"
```

Transforms can also be uploaded from files using the `addMrssTransformFromFile`, `addMrssValidateFromFile`, and `addResultsTransformFromFile` actions.

## 9.4 Creating a Generic Distribution Profile

Once the provider and its actions are configured, create a distribution profile that references the provider:

```bash
curl -X POST "$KALTURA_SERVICE_URL/service/contentDistribution_distributionProfile/action/add" \
  -d "ks=$KALTURA_KS" \
  -d "format=1" \
  -d "partnerId=$KALTURA_PARTNER_ID" \
  -d "distributionProfile[objectType]=KalturaGenericDistributionProfile" \
  -d "distributionProfile[name]=My Custom Platform Distribution" \
  -d "distributionProfile[status]=2" \
  -d "distributionProfile[genericProviderId]=$GENERIC_PROVIDER_ID" \
  -d "distributionProfile[submitEnabled]=3" \
  -d "distributionProfile[updateEnabled]=3" \
  -d "distributionProfile[deleteEnabled]=2"
```

The `genericProviderId` field links the profile to the provider you created in section 9.1. The profile inherits the provider's required assets, and the actions you defined in section 9.2 control how each operation is executed.

The `partnerId` parameter is required in the request body (same requirement as all distribution profiles — see section 4.2).

From here, the standard entry distribution workflow applies: bind an entry (section 5.2), validate (section 5.3), and submit (section 5.4).

## 9.5 Generic Distribution Data Flow

When an entry distribution is submitted against a Generic Distribution profile:

1. Kaltura generates the entry's **MRSS XML** (section 8.1), including all metadata, content URLs, thumbnails, and distribution-specific data
2. The SUBMIT action's **MRSS Transformer** XSLT is applied, converting the MRSS into the target platform's format
3. If an **MRSS Validator** XSD is configured, the transformed XML is validated — failures are reported as validation errors
4. The transformed XML is delivered to the target server via the configured **protocol** (FTP, SFTP, SCP, HTTP, or HTTPS)
5. If the target returns a response, the **Results Transformer** parses it (via XSL, XPath, or Regex) to extract the `remoteId`
6. The entry distribution status updates to READY (2) with the extracted `remoteId`

The same pipeline runs for UPDATE and DELETE actions using their respective transforms and server configurations.


# 10. Status & Error Reference

## 10.1 Entry Distribution Status Values

| Value | Name | Description |
|-------|------|-------------|
| 0 | PENDING | Awaiting submission |
| 1 | QUEUED | In processing queue (waiting for entry ready or sunrise) |
| 2 | READY | Successfully distributed to remote platform |
| 3 | DELETED | Marked for deletion |
| 4 | SUBMITTING | Actively submitting to remote |
| 5 | UPDATING | Pushing updates to remote |
| 6 | DELETING | Removing from remote |
| 7 | ERROR_SUBMITTING | Submit failed |
| 8 | ERROR_UPDATING | Update failed |
| 9 | ERROR_DELETING | Delete failed |
| 10 | REMOVED | Successfully removed from remote |
| 11 | IMPORT_SUBMITTING | Importing from remote |
| 12 | IMPORT_UPDATING | Updating import |

## 10.2 Distribution Validation Error Types

| Error Object | errorType | Description |
|-------------|-----------|-------------|
| `KalturaDistributionValidationErrorMissingFlavor` | 1 | Required flavor not found on entry |
| `KalturaDistributionValidationErrorMissingThumbnail` | 2 | Required thumbnail dimensions not found |
| `KalturaDistributionValidationErrorMissingMetadata` | 3 | Required metadata field is empty |
| `KalturaDistributionValidationErrorInvalidData` | 4 | Field value fails format validation |
| `KalturaDistributionValidationErrorMissingAsset` | 5 | Required asset not found |
| `KalturaDistributionValidationErrorConditionNotMet` | 6 | XSLT distribution condition not satisfied |

## 10.3 Dirty Status & Sun Status Flags

**Dirty status** (tracks what changed since last sync):

| Value | Name | Description |
|-------|------|-------------|
| 0 | NONE | Clean — no pending changes |
| 1 | SUBMIT_REQUIRED | Initial submission needed |
| 2 | DELETE_REQUIRED | Removal needed |
| 3 | UPDATE_REQUIRED | Metadata or content changed |
| 4 | ENABLE_REQUIRED | Re-enabling needed |

**Sun status** (sunrise/sunset state):

| Value | Name | Description |
|-------|------|-------------|
| 1 | BEFORE_SUNRISE | Content not yet active |
| 2 | AFTER_SUNRISE | Content is active |
| 3 | AFTER_SUNSET | Content has expired |


# 11. Error Handling

| Error Code | Meaning | Resolution |
|------------|---------|------------|
| `ENTRY_DISTRIBUTION_NOT_FOUND` | Entry distribution ID does not exist | Verify the ID; may have been deleted |
| `DISTRIBUTION_PROFILE_NOT_FOUND` | Distribution profile ID does not exist | Verify the profile ID |
| `DISTRIBUTION_PROFILE_DISABLED` | Profile is currently disabled (status=1) | Re-enable with `distributionProfile.updateStatus` |
| `ENTRY_NOT_FOUND` | The entry ID in the distribution binding does not exist | Verify the entry ID |
| `SERVICE_FORBIDDEN` | Content Distribution plugin not enabled | Contact your Kaltura account manager |
| `PROPERTY_VALIDATION_CANNOT_BE_NULL` | A required field is missing | Add the required parameter |
| `INVALID_KS` | KS is invalid, expired, or lacks privileges | Generate a fresh admin KS |

**Retry strategy:** For transient errors (HTTP 5xx, timeouts), retry with exponential backoff: 1s, 2s, 4s, with jitter, up to 3 retries. For client errors (`ENTRY_DISTRIBUTION_NOT_FOUND`, `SERVICE_FORBIDDEN`), fix the request before retrying. Distribution submission is asynchronous — after calling `submitAdd`, poll the entry distribution status rather than retrying the submit call.


# 12. Best Practices

- **Validate before submitting.** Call `entryDistribution.validate` before `submitAdd` to catch missing flavors, thumbnails, or metadata. Fix validation errors before attempting submission.
- **Use `submitWhenReady=true` for newly uploaded content.** Entries that are still processing will be automatically submitted once they reach READY status, avoiding timing issues.
- **Monitor dirty status for content updates.** When `updateEnabled=MANUAL`, periodically check for entry distributions with `dirtyStatus != 0` and call `submitUpdate` to push changes.
- **Use sunrise/sunset for time-based releases.** Schedule content activation and expiration via timestamps rather than manual submit/delete calls.
- **Check `serveSentData` / `serveReturnedData` for debugging.** When distribution fails, inspect the raw XML sent to and received from the remote platform.
- **Use entry distribution `list` with filters for monitoring.** Filter by `statusEqual` to find failed distributions (status 7, 8, 9) and retry or investigate.
- **Call `submitDelete` before `delete`.** To remove content from both the remote platform and Kaltura, call `submitDelete` first (removes from remote), then `delete` (removes the local record).
- **Use Generic Distribution for custom XML-based targets.** Build a custom connector via API (section 9) for any platform that accepts XML file delivery. For platforms requiring OAuth or custom REST API integration, contact your Kaltura account manager to request a new built-in connector.


# 13. Common Integration Patterns

## 13.1 Multi-Platform Publishing Pipeline

Distribute a single entry to multiple platforms simultaneously by binding it to multiple distribution profiles:

```bash
# Bind to YouTube
curl -X POST "$KALTURA_SERVICE_URL/service/contentDistribution_entryDistribution/action/add" \
  -d "ks=$KALTURA_KS" \
  -d "format=1" \
  -d "entryDistribution[objectType]=KalturaEntryDistribution" \
  -d "entryDistribution[entryId]=$ENTRY_ID" \
  -d "entryDistribution[distributionProfileId]=$YOUTUBE_PROFILE_ID"

# Bind to Facebook
curl -X POST "$KALTURA_SERVICE_URL/service/contentDistribution_entryDistribution/action/add" \
  -d "ks=$KALTURA_KS" \
  -d "format=1" \
  -d "entryDistribution[objectType]=KalturaEntryDistribution" \
  -d "entryDistribution[entryId]=$ENTRY_ID" \
  -d "entryDistribution[distributionProfileId]=$FACEBOOK_PROFILE_ID"

# Submit both with submitWhenReady
curl -X POST "$KALTURA_SERVICE_URL/service/contentDistribution_entryDistribution/action/submitAdd" \
  -d "ks=$KALTURA_KS" \
  -d "format=1" \
  -d "id=$YOUTUBE_ENTRY_DIST_ID" \
  -d "submitWhenReady=true"

curl -X POST "$KALTURA_SERVICE_URL/service/contentDistribution_entryDistribution/action/submitAdd" \
  -d "ks=$KALTURA_KS" \
  -d "format=1" \
  -d "id=$FACEBOOK_ENTRY_DIST_ID" \
  -d "submitWhenReady=true"
```

## 13.2 YouTube Channel Distribution

Full workflow for distributing content to YouTube:

1. **Get profile** — retrieve the YouTube distribution profile to verify configuration
2. **Bind entry** — create an entry distribution linking the entry to the YouTube profile
3. **Validate** — check that required flavors and metadata are present
4. **Submit** — push to YouTube; the entry gets a YouTube video ID in `remoteId`
5. **Monitor** — check status transitions; READY (2) means the video is live on YouTube

```bash
# Step 1: Verify YouTube profile
curl -X POST "$KALTURA_SERVICE_URL/service/contentDistribution_distributionProfile/action/get" \
  -d "ks=$KALTURA_KS" \
  -d "format=1" \
  -d "id=$YOUTUBE_PROFILE_ID"

# Step 2: Bind entry
curl -X POST "$KALTURA_SERVICE_URL/service/contentDistribution_entryDistribution/action/add" \
  -d "ks=$KALTURA_KS" \
  -d "format=1" \
  -d "entryDistribution[objectType]=KalturaEntryDistribution" \
  -d "entryDistribution[entryId]=$ENTRY_ID" \
  -d "entryDistribution[distributionProfileId]=$YOUTUBE_PROFILE_ID"

# Step 3: Validate
curl -X POST "$KALTURA_SERVICE_URL/service/contentDistribution_entryDistribution/action/validate" \
  -d "ks=$KALTURA_KS" \
  -d "format=1" \
  -d "id=$ENTRY_DISTRIBUTION_ID"

# Step 4: Submit
curl -X POST "$KALTURA_SERVICE_URL/service/contentDistribution_entryDistribution/action/submitAdd" \
  -d "ks=$KALTURA_KS" \
  -d "format=1" \
  -d "id=$ENTRY_DISTRIBUTION_ID" \
  -d "submitWhenReady=true"

# Step 5: Check status
curl -X POST "$KALTURA_SERVICE_URL/service/contentDistribution_entryDistribution/action/get" \
  -d "ks=$KALTURA_KS" \
  -d "format=1" \
  -d "id=$ENTRY_DISTRIBUTION_ID"
```

## 13.3 Time-Based Content Release

Schedule content to go live on a remote platform at a future date and expire automatically:

```bash
curl -X POST "$KALTURA_SERVICE_URL/service/contentDistribution_entryDistribution/action/add" \
  -d "ks=$KALTURA_KS" \
  -d "format=1" \
  -d "entryDistribution[objectType]=KalturaEntryDistribution" \
  -d "entryDistribution[entryId]=$ENTRY_ID" \
  -d "entryDistribution[distributionProfileId]=$DISTRIBUTION_PROFILE_ID" \
  -d "entryDistribution[sunrise]=$GO_LIVE_TIMESTAMP" \
  -d "entryDistribution[sunset]=$EXPIRE_TIMESTAMP"

curl -X POST "$KALTURA_SERVICE_URL/service/contentDistribution_entryDistribution/action/submitAdd" \
  -d "ks=$KALTURA_KS" \
  -d "format=1" \
  -d "id=$ENTRY_DISTRIBUTION_ID" \
  -d "submitWhenReady=true"
```

## 13.4 Monitoring Distribution Health

Find all failed distributions and retry them:

```bash
# Find distributions with ERROR_SUBMITTING status
curl -X POST "$KALTURA_SERVICE_URL/service/contentDistribution_entryDistribution/action/list" \
  -d "ks=$KALTURA_KS" \
  -d "format=1" \
  -d "filter[objectType]=KalturaEntryDistributionFilter" \
  -d "filter[statusEqual]=7"

# View what was sent to the remote platform
curl -X POST "$KALTURA_SERVICE_URL/service/contentDistribution_entryDistribution/action/serveSentData" \
  -d "ks=$KALTURA_KS" \
  -d "format=1" \
  -d "id=$FAILED_ENTRY_DIST_ID" \
  -d "actionType=1"

# Retry the submission
curl -X POST "$KALTURA_SERVICE_URL/service/contentDistribution_entryDistribution/action/retrySubmit" \
  -d "ks=$KALTURA_KS" \
  -d "format=1" \
  -d "id=$FAILED_ENTRY_DIST_ID"
```

## 13.5 Webhook-Triggered Distribution

Combine distribution with [webhooks](KALTURA_WEBHOOKS_API.md) for event-driven publishing. Set up a webhook that fires when entry metadata changes, then programmatically manage distribution updates:

1. Create a webhook template for `OBJECT_DATA_CHANGED` on `ENTRY` objects
2. In your webhook handler, check if the entry has active distributions
3. If `dirtyStatus != 0`, call `entryDistribution.submitUpdate` to push changes


# 14. API Actions Reference

| Service | Action | Description |
|---------|--------|-------------|
| `contentDistribution_distributionProvider` | `list` | List available provider types |
| `contentDistribution_distributionProfile` | `add` | Create distribution profile |
| `contentDistribution_distributionProfile` | `get` | Get profile by ID |
| `contentDistribution_distributionProfile` | `list` | List profiles (with filters) |
| `contentDistribution_distributionProfile` | `update` | Update profile fields |
| `contentDistribution_distributionProfile` | `updateStatus` | Enable/disable profile |
| `contentDistribution_distributionProfile` | `delete` | Delete profile |
| `contentDistribution_genericDistributionProvider` | `add` | Create custom generic provider |
| `contentDistribution_genericDistributionProvider` | `get` | Get provider by ID |
| `contentDistribution_genericDistributionProvider` | `list` | List generic providers |
| `contentDistribution_genericDistributionProvider` | `update` | Update provider fields |
| `contentDistribution_genericDistributionProvider` | `delete` | Delete provider |
| `contentDistribution_genericDistributionProviderAction` | `add` | Create provider action (submit/update/delete) |
| `contentDistribution_genericDistributionProviderAction` | `get` | Get action by ID |
| `contentDistribution_genericDistributionProviderAction` | `getByProviderId` | Get action by provider ID and action type |
| `contentDistribution_genericDistributionProviderAction` | `list` | List provider actions |
| `contentDistribution_genericDistributionProviderAction` | `update` | Update action fields |
| `contentDistribution_genericDistributionProviderAction` | `delete` | Delete action |
| `contentDistribution_genericDistributionProviderAction` | `addMrssTransform` | Upload XSLT transform for MRSS |
| `contentDistribution_genericDistributionProviderAction` | `addMrssValidate` | Upload XSD validation schema |
| `contentDistribution_genericDistributionProviderAction` | `addResultsTransform` | Upload results parser (XSL/XPath/Regex) |
| `contentDistribution_entryDistribution` | `add` | Bind entry to distribution profile |
| `contentDistribution_entryDistribution` | `get` | Get entry distribution by ID |
| `contentDistribution_entryDistribution` | `list` | List entry distributions (with filters) |
| `contentDistribution_entryDistribution` | `update` | Update entry distribution fields |
| `contentDistribution_entryDistribution` | `delete` | Delete entry distribution record |
| `contentDistribution_entryDistribution` | `validate` | Validate entry against profile requirements |
| `contentDistribution_entryDistribution` | `submitAdd` | Submit entry to remote platform |
| `contentDistribution_entryDistribution` | `submitUpdate` | Push updates to remote |
| `contentDistribution_entryDistribution` | `submitDelete` | Remove from remote platform |
| `contentDistribution_entryDistribution` | `submitFetchReport` | Request delivery report |
| `contentDistribution_entryDistribution` | `retrySubmit` | Retry last failed operation |
| `contentDistribution_entryDistribution` | `serveSentData` | Retrieve XML sent to remote |
| `contentDistribution_entryDistribution` | `serveReturnedData` | Retrieve XML returned from remote |


# 15. Related Guides

- **[Session Guide](KALTURA_SESSION_GUIDE.md)** — KS generation and management
- **[AppTokens API](KALTURA_APPTOKENS_API.md)** — Secure server-to-server auth for automated distribution workflows
- **[Syndication Feeds API](KALTURA_SYNDICATION_API.md)** — Generate RSS/MRSS/iTunes/Roku feeds for external platforms to pull (pull model vs distribution's push model)
- **[Upload & Delivery API](KALTURA_UPLOAD_AND_DELIVERY_API.md)** — Content upload, flavors, and delivery (entries and assets that feed distribution)
- **[Webhooks API](KALTURA_WEBHOOKS_API.md)** — Event-driven automation (trigger distribution on content events)
- **[Custom Metadata API](KALTURA_CUSTOM_METADATA_API.md)** — Structured metadata schemas (metadata mapped to distribution provider fields)
- **[Captions & Transcripts API](KALTURA_CAPTIONS_AND_TRANSCRIPTS_API.md)** — Caption assets included in distribution (Cross-Kaltura distributes captions)
- **[Categories & Access Control API](KALTURA_CATEGORIES_AND_ACCESS_CONTROL_API.md)** — Content organization (used in distribution conditions)
- **[Analytics Reports API](KALTURA_ANALYTICS_REPORTS_API.md)** — Engagement analytics for distributed content

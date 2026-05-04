# Kaltura Access Control API

The Access Control API manages content access restrictions through profiles, rules, conditions, and actions. Access control profiles are assigned to entries and enforced server-side on every playManifest, raw serve, download, and thumbnail request. Rules evaluate conditions (IP address, country, domain, user agent, authentication, scheduling, metadata) and execute actions (block, preview, limit flavors, limit delivery profiles) when conditions are met.

**Base URL:** `https://www.kaltura.com/api_v3` (may differ by region/deployment)  
**Auth:** KS passed as `ks` parameter in POST form data (see [Session Guide](KALTURA_SESSION_GUIDE.md))  
**Format:** Form-encoded POST, `format=1` for JSON responses  
**Service:** `accessControlProfile` (5 actions)

<!-- Sections: 1.When to Use | 2.Prerequisites | 3.Authentication | 4.Access Control Model | 5.KalturaAccessControlProfile Object | 6.Profile CRUD | 7.Rule Conditions | 8.Rule Actions | 9.Access Control Contexts | 10.Scheduling vs Access Control | 11.Assigning Profiles to Entries | 12.Business Scenarios | 13.Error Handling | 14.Best Practices | 15.Related Guides -->


# 1. When to Use

- **Geo-restricted content** -- Block playback outside licensed countries/regions (sports broadcasting, media licensing)  
- **Domain-locked embedding** -- Restrict video playback to specific domains (prevent unauthorized embedding)  
- **IP whitelisting** -- Allow access only from corporate networks or specific IP ranges  
- **Time-windowed availability** -- Content available only during specific scheduling windows (catch-up TV, live event replays)  
- **Device-specific restrictions** -- Different rules for mobile vs desktop, or specific device families  
- **Preview/paywall** -- Allow first N seconds of playback, then require authentication for full content  
- **Metadata-driven access** -- Dynamic rules based on entry metadata (content rating, language, format type)  
- **Download vs playback split** -- Allow streaming but block downloads, or vice versa  


# 2. Prerequisites

- **Kaltura Session (KS):** ADMIN KS (type=2) with `ACCESS_CONTROL_BASE` permission for profile CRUD  
- **Partner ID and API credentials:** From KMC > Settings > Integration Settings  
- **Service URL:** Set `$KALTURA_SERVICE_URL` to your account's regional endpoint  


# 3. Authentication

ADMIN KS (type=2) with `ACCESS_CONTROL_BASE` permission. Generate via `session.start` (see [Session Guide](KALTURA_SESSION_GUIDE.md)) or `appToken.startSession` (see [AppTokens Guide](KALTURA_APPTOKENS_API.md)).

```bash
export KALTURA_SERVICE_URL="https://www.kaltura.com/api_v3"
```


# 4. Access Control Model

## 4.1 Architecture

An access control profile (`KalturaAccessControlProfile`) contains an ordered array of rules (`KalturaRule`). Each rule has:

- **conditions** -- array of `KalturaCondition` objects (AND logic: ALL must be true)  
- **actions** -- array of `KalturaAccessControlAction` objects (what to enforce)  
- **contexts** -- array of `KalturaAccessControlContextTypeHolder` (when to evaluate: PLAY, DOWNLOAD, THUMBNAIL)  
- **message** -- message to return to the player when rule fires  
- **stopProcessing** -- if true and conditions met, skip remaining rules  

## 4.2 Rule Evaluation Logic

1. Rules evaluate in array order  
2. Each rule evaluates only if its `contexts` match the current request context (PLAY for playManifest, DOWNLOAD for raw/download, THUMBNAIL for thumbnails). A rule with no contexts evaluates in all contexts.  
3. A rule is **fulfilled** when ALL its conditions evaluate to true (AND logic)  
4. When fulfilled, the rule's actions are added to the outcome and its message is added to the outcome messages  
5. If `stopProcessing` is true on a fulfilled rule, remaining rules are skipped  
6. All accumulated actions execute  
7. If no rule matches, content is allowed (default: allow)  

## 4.3 Access Control Scope

When access control is evaluated, the server constructs a `KalturaAccessControlScope` from the request:

| Field | Type | Description |
|-------|------|-------------|
| `contexts` | array | Which contexts to test (no context = any context) |
| `ip` | string | Request IP address for geographic conditions |
| `ks` | string | Kaltura session for authentication/user conditions |
| `referrer` | string | Page URL for domain conditions |
| `time` | integer | Unix timestamp for scheduling (null = server time) |
| `userAgent` | string | Browser/client application for agent conditions |


# 5. KalturaAccessControlProfile Object

| Field | Type | Description |
|-------|------|-------------|
| `id` | integer | Auto-generated profile ID (read-only) |
| `name` | string | Profile display name |
| `description` | string | Profile description |
| `partnerId` | integer | Partner ID (read-only) |
| `isDefault` | integer | `1` if this is the default profile |
| `rules` | array | Array of `KalturaRule` objects |
| `systemName` | string | System-level name |
| `createdAt` | integer | Unix timestamp (read-only) |
| `updatedAt` | integer | Unix timestamp (read-only) |
| `objectType` | string | Always `"KalturaAccessControlProfile"` (read-only) |


# 6. Profile CRUD

## 6.1 Create a Profile

```bash
curl -X POST "$KALTURA_SERVICE_URL/service/accessControlProfile/action/add" \
  -d "ks=$KALTURA_KS" \
  -d "format=1" \
  -d "accessControlProfile[objectType]=KalturaAccessControlProfile" \
  -d "accessControlProfile[name]=Geo Restricted" \
  -d "accessControlProfile[description]=Block playback outside US"
```

**Parameters for `accessControlProfile[...]`:**

| Parameter | Required | Description |
|-----------|----------|-------------|
| `objectType` | Yes | Always `KalturaAccessControlProfile` |
| `name` | Yes | Display name for the profile |
| `description` | No | Human-readable description |
| `systemName` | No | System-level name for programmatic lookup |
| `isDefault` | No | Set to `1` to make this the default profile |
| `rules` | No | Array of `KalturaRule` objects (see section 7) |

**Response:** Full `KalturaAccessControlProfile` object with generated `id`.

## 6.2 Create a Profile with Rules

```bash
curl -X POST "$KALTURA_SERVICE_URL/service/accessControlProfile/action/add" \
  -d "ks=$KALTURA_KS" \
  -d "format=1" \
  -d "accessControlProfile[objectType]=KalturaAccessControlProfile" \
  -d "accessControlProfile[name]=US Only Playback" \
  -d "accessControlProfile[description]=Block playback outside United States" \
  -d "accessControlProfile[rules][0][objectType]=KalturaRule" \
  -d "accessControlProfile[rules][0][actions][0][objectType]=KalturaAccessControlBlockAction" \
  -d "accessControlProfile[rules][0][conditions][0][objectType]=KalturaCountryCondition" \
  -d "accessControlProfile[rules][0][conditions][0][not]=true" \
  -d "accessControlProfile[rules][0][conditions][0][values][0][objectType]=KalturaStringValue" \
  -d "accessControlProfile[rules][0][conditions][0][values][0][value]=US" \
  -d "accessControlProfile[rules][0][contexts][0][objectType]=KalturaAccessControlContextTypeHolder" \
  -d "accessControlProfile[rules][0][contexts][0][type]=1" \
  -d "accessControlProfile[rules][0][message]=Content not available in your region"
```

## 6.3 Get a Profile

```bash
curl -X POST "$KALTURA_SERVICE_URL/service/accessControlProfile/action/get" \
  -d "ks=$KALTURA_KS" \
  -d "format=1" \
  -d "id=$ACCESS_CONTROL_ID"
```

## 6.4 List Profiles

```bash
curl -X POST "$KALTURA_SERVICE_URL/service/accessControlProfile/action/list" \
  -d "ks=$KALTURA_KS" \
  -d "format=1" \
  -d "filter[objectType]=KalturaAccessControlProfileFilter" \
  -d "pager[pageSize]=50"
```

**Filter fields (`KalturaAccessControlProfileFilter`):**

| Field | Description |
|-------|-------------|
| `idEqual` | Exact profile ID |
| `idIn` | Comma-separated profile IDs |
| `systemNameEqual` | Exact system name match |
| `createdAtGreaterThanOrEqual` | Unix timestamp lower bound |
| `createdAtLessThanOrEqual` | Unix timestamp upper bound |
| `orderBy` | `+createdAt` or `-createdAt` |

## 6.5 Update a Profile

```bash
curl -X POST "$KALTURA_SERVICE_URL/service/accessControlProfile/action/update" \
  -d "ks=$KALTURA_KS" \
  -d "format=1" \
  -d "id=$ACCESS_CONTROL_ID" \
  -d "accessControlProfile[objectType]=KalturaAccessControlProfile" \
  -d "accessControlProfile[description]=Updated restrictions"
```

## 6.6 Delete a Profile

```bash
curl -X POST "$KALTURA_SERVICE_URL/service/accessControlProfile/action/delete" \
  -d "ks=$KALTURA_KS" \
  -d "format=1" \
  -d "id=$ACCESS_CONTROL_ID"
```

Entries assigned to the deleted profile revert to the partner's default access control.


# 7. Rule Conditions

## 7.1 Condition Types

| Condition ObjectType | Type Value | Description |
|---------------------|------------|-------------|
| `KalturaIpAddressCondition` | IP_ADDRESS (3) | Match by IP address or CIDR range |
| `KalturaCountryCondition` | COUNTRY (2) | Match by country code (derived from IP) |
| `KalturaSiteCondition` | SITE (4) | Match by referring domain (wildcards supported) |
| `KalturaUserAgentCondition` | USER_AGENT (5) | Match by user-agent string (regex supported) |
| `KalturaAuthenticatedCondition` | AUTHENTICATED (1) | Require valid KS with specific privileges |
| `KalturaFieldMatchCondition` | FIELD_MATCH (6) | Match text field against values |
| `KalturaFieldCompareCondition` | FIELD_COMPARE (7) | Compare numeric field against values |
| `KalturaMatchMetadataCondition` | metadata.FieldMatch | Match metadata XML field text against values |
| `KalturaCompareMetadataCondition` | metadata.FieldCompare | Compare metadata XML field number against values |

All conditions support a `not` boolean field -- when `true`, the condition matches when the test FAILS (logical negation).

## 7.2 IP Address Condition

```bash
# Block all IPs except internal network
-d "accessControlProfile[rules][0][conditions][0][objectType]=KalturaIpAddressCondition" \
-d "accessControlProfile[rules][0][conditions][0][not]=true" \
-d "accessControlProfile[rules][0][conditions][0][values][0][objectType]=KalturaStringValue" \
-d "accessControlProfile[rules][0][conditions][0][values][0][value]=192.168.1.0/24"
```

## 7.3 Country Condition

```bash
# Block viewers outside US and Canada
-d "accessControlProfile[rules][0][conditions][0][objectType]=KalturaCountryCondition" \
-d "accessControlProfile[rules][0][conditions][0][not]=true" \
-d "accessControlProfile[rules][0][conditions][0][values][0][objectType]=KalturaStringValue" \
-d "accessControlProfile[rules][0][conditions][0][values][0][value]=US" \
-d "accessControlProfile[rules][0][conditions][0][values][1][objectType]=KalturaStringValue" \
-d "accessControlProfile[rules][0][conditions][0][values][1][value]=CA"
```

## 7.4 Site/Domain Condition

```bash
# Allow only from publisher.com and subdomains
-d "accessControlProfile[rules][0][conditions][0][objectType]=KalturaSiteCondition" \
-d "accessControlProfile[rules][0][conditions][0][not]=true" \
-d "accessControlProfile[rules][0][conditions][0][values][0][objectType]=KalturaStringValue" \
-d "accessControlProfile[rules][0][conditions][0][values][0][value]=*.publisher.com"
```

## 7.5 User Agent Condition

```bash
# Match iPad devices (regex)
-d "accessControlProfile[rules][0][conditions][0][objectType]=KalturaUserAgentCondition" \
-d "accessControlProfile[rules][0][conditions][0][values][0][objectType]=KalturaStringValue" \
-d "accessControlProfile[rules][0][conditions][0][values][0][value]=.*iPad.*"
```

## 7.6 Authenticated Condition

```bash
# Require valid KS
-d "accessControlProfile[rules][0][conditions][0][objectType]=KalturaAuthenticatedCondition"
```

This condition validates at the entry level when assigned to entry-specific access control.

## 7.7 Metadata Conditions

Match or compare values from a custom metadata profile's XML fields. Metadata conditions use `profileId` (the metadata profile ID) and `xPath` (the field path within the XML).

**xPath formats:**

- Full path: `/metadata/myElementName`  
- Local-name function: `/*[local-name()='metadata']/*[local-name()='myElementName']`  
- Short form: `myElementName` (searched as `//myElementName`)  

**Match metadata text field:**

```bash
# Block if AudioLanguage is NOT French
-d "accessControlProfile[rules][0][conditions][0][objectType]=KalturaMatchMetadataCondition" \
-d "accessControlProfile[rules][0][conditions][0][xPath]=AudioLanguage" \
-d "accessControlProfile[rules][0][conditions][0][profileId]=$METADATA_PROFILE_ID" \
-d "accessControlProfile[rules][0][conditions][0][not]=true" \
-d "accessControlProfile[rules][0][conditions][0][values][0][objectType]=KalturaStringValue" \
-d "accessControlProfile[rules][0][conditions][0][values][0][value]=French"
```

**Compare metadata numeric field (scheduling):**

```bash
# Allow if current time >= entry's ipadSunrise metadata field
-d "accessControlProfile[rules][0][conditions][0][objectType]=KalturaCompareMetadataCondition" \
-d "accessControlProfile[rules][0][conditions][0][comparison]=4" \
-d "accessControlProfile[rules][0][conditions][0][xPath]=ipadSunrise" \
-d "accessControlProfile[rules][0][conditions][0][profileId]=$METADATA_PROFILE_ID" \
-d "accessControlProfile[rules][0][conditions][0][value][objectType]=KalturaTimeContextField"
```

**Comparison operators:** 1=LESS_THAN, 2=LESS_THAN_OR_EQUAL, 3=GREATER_THAN, 4=GREATER_THAN_OR_EQUAL, 5=EQUAL

## 7.8 Field Match and Compare Conditions

For generic field matching (not metadata-specific), use `KalturaFieldMatchCondition` and `KalturaFieldCompareCondition`. These use field objects:

**String field implementations:**

- `KalturaCountryContextField` -- current request's country  
- `KalturaIpAddressContextField` -- current request's IP  
- `KalturaUserAgentContextField` -- current request's user agent  
- `KalturaUserEmailContextField` -- current session's user email  

**Integer field implementations:**

- `KalturaTimeContextField` -- current server time (Unix timestamp)  


# 8. Rule Actions

| Action ObjectType | Description | Additional Fields |
|------------------|-------------|-------------------|
| `KalturaAccessControlBlockAction` | Block access entirely | -- |
| `KalturaAccessControlPreviewAction` | Allow preview only | `limit` (integer, seconds) |
| `KalturaAccessControlLimitFlavorsAction` | Restrict to specific flavors | `flavorParamsIds` (comma-separated), `isBlockedList` (boolean) |
| `KalturaAccessControlLimitDeliveryProfilesAction` | Restrict delivery profiles | `deliveryProfileIds` (comma-separated), `isBlockedList` (boolean) |
| `KalturaAccessControlLimitThumbnailCaptureAction` | Restrict thumbnail frame capture | -- |
| `KalturaAccessControlServeFromRemoteServerAction` | Force serve from specific edge | -- |

**Preview action (paywall):**

```bash
# Allow first 30 seconds only for unauthenticated users
-d "accessControlProfile[rules][0][conditions][0][objectType]=KalturaAuthenticatedCondition" \
-d "accessControlProfile[rules][0][conditions][0][not]=true" \
-d "accessControlProfile[rules][0][actions][0][objectType]=KalturaAccessControlPreviewAction" \
-d "accessControlProfile[rules][0][actions][0][limit]=30"
```

**Limit flavors action:**

```bash
# Restrict mobile devices to SD flavors only
-d "accessControlProfile[rules][0][actions][0][objectType]=KalturaAccessControlLimitFlavorsAction" \
-d "accessControlProfile[rules][0][actions][0][flavorParamsIds]=$FLAVOR_PARAMS_ID_1,$FLAVOR_PARAMS_ID_2" \
-d "accessControlProfile[rules][0][actions][0][isBlockedList]=false"
```


# 9. Access Control Contexts

Rules are evaluated based on the delivery context:

| Value | Name | Applied On |
|-------|------|------------|
| 1 | PLAY | playManifest requests (streaming playback) |
| 2 | DOWNLOAD | raw serve, download, flavorAsset.getUrl requests |
| 3 | THUMBNAIL | Dynamic thumbnail URL requests |
| 4 | METADATA | Metadata access (entry info) |

Set contexts on rules to enforce them selectively:

```bash
# Apply rule only to PLAY and DOWNLOAD contexts
-d "accessControlProfile[rules][0][contexts][0][objectType]=KalturaAccessControlContextTypeHolder" \
-d "accessControlProfile[rules][0][contexts][0][type]=1" \
-d "accessControlProfile[rules][0][contexts][1][objectType]=KalturaAccessControlContextTypeHolder" \
-d "accessControlProfile[rules][0][contexts][1][type]=2"
```

An entry can be viewable but not downloadable, or thumbnails can be accessible even when playback is restricted.


# 10. Scheduling vs Access Control

Kaltura has two mechanisms for enforcing time-based access:

**Entry-level scheduling** (simpler):

- Set `startDate` and `endDate` on the entry  
- Single start/end window  
- Enforced server-side across all devices  
- Configurable via Rich Media CMS (KMC) without API calls  

**Access control scheduling** (advanced):

- Multiple scheduling windows per entry  
- Combined with other conditions (device + time, country + time)  
- Metadata-driven scheduling (per-device availability windows)  
- Requires access control profile configuration  

Use entry-level scheduling when a single time window is sufficient. Use access control scheduling for per-device windows, multiple windows, or combined restrictions.

## 10.1 Checking Scheduling Status

Use `baseEntry.getContextData` to check whether content is currently available:

```bash
curl -X POST "$KALTURA_SERVICE_URL/service/baseEntry/action/getContextData" \
  -d "ks=$KALTURA_KS" \
  -d "format=1" \
  -d "entryId=$KALTURA_ENTRY_ID" \
  -d "contextDataParams[objectType]=KalturaEntryContextDataParams"
```

The response (`KalturaEntryContextDataResult`) includes:

- `isScheduledNow` -- boolean, whether the entry is within its scheduling window  
- `actions` -- array of access control actions that would be enforced  
- `messages` -- array of rule messages  

Use `isScheduledNow` to display user-friendly messages (e.g., "This video is available from X to Y") instead of a blank player.


# 11. Assigning Profiles to Entries

Assign an access control profile to an entry via `media.update` (or `baseEntry.update`):

```bash
curl -X POST "$KALTURA_SERVICE_URL/service/media/action/update" \
  -d "ks=$KALTURA_KS" \
  -d "format=1" \
  -d "entryId=$KALTURA_ENTRY_ID" \
  -d "mediaEntry[objectType]=KalturaMediaEntry" \
  -d "mediaEntry[accessControlId]=$ACCESS_CONTROL_ID"
```

To revert to the partner's default access control, set `accessControlId` to the partner's default profile ID. List profiles with `accessControlProfile.list` and look for `isDefault=1`.


# 12. Business Scenarios

## 12.1 Geo-Restricted Premium Content

A sports broadcaster restricts live event playback to viewers in licensed countries. Create a profile with a country condition that blocks playback outside US and Canada, applied to the PLAY context. Viewers in blocked regions receive the rule message. Viewers in authorized regions stream normally.

## 12.2 Domain-Locked Embedding

An educational publisher restricts video playback to their own domain. Create a profile with a site condition matching `*.publisher.com` with `not=true`, and a block action. Attempts to embed the player on unauthorized domains result in a playback error.

## 12.3 Device-Specific Scheduling Windows

A media company has different availability windows for iPad vs web viewers. Create rules with combined user-agent + metadata conditions:

- Rule 1: If user-agent matches iPad AND current time is between metadata sunrise/sunset fields, set `stopProcessing=true` (allow)  
- Rule 2: No conditions, block action (catch-all for everything that did not match Rule 1)  

## 12.4 Preview/Paywall

A content platform allows 30-second previews for anonymous visitors and full access for authenticated subscribers:

- Rule 1: If NOT authenticated, apply preview action with `limit=30`  
- Authenticated users pass through with no actions (full access)  

## 12.5 Block Long-Form Content on Mobile

A media company blocks feature-length content on specific mobile devices. Create a rule with two conditions: user-agent matches mobile brands AND metadata FormatType equals "Long Form". Action: block.


# 13. Error Handling

| Error Code | Meaning |
|------------|---------|
| `ACCESS_CONTROL_NOT_FOUND` | Profile ID does not exist |
| HTTP 403 on delivery | Access denied by access control rules -- check KS, referrer, IP, geo restrictions |
| `INVALID_OBJECT_TYPE` | Wrong objectType in rule, condition, or action definition |
| Empty `actions` on getContextData | No rules matched -- content is allowed |
| `isScheduledNow=false` on getContextData | Entry is outside its scheduling window |


# 14. Best Practices

- **Start simple, add complexity as needed.** Begin with basic rules (IP, country) and expand. Complex rule chains are harder to debug when access is unexpectedly blocked.  
- **Use `stopProcessing` for allow-then-block patterns.** To allow specific conditions and block everything else, create a whitelist rule with `stopProcessing=true`, followed by a catch-all block rule with no conditions.  
- **Set explicit contexts on rules.** Rules without contexts evaluate in all contexts. Set PLAY, DOWNLOAD, or THUMBNAIL explicitly to enable split access (e.g., allow thumbnails but block playback).  
- **Use `baseEntry.getContextData` for UX.** Check scheduling and access control before attempting playback to show user-friendly messages instead of blank screens.  
- **Test access control profiles.** Use `baseEntry.getContextData` with different `ip`, `referrer`, and `userAgent` scope values to simulate different access scenarios without needing actual devices.  
- **Assign profiles via `accessControlId`.** Set on entry creation or update. To revert to the partner default, set `accessControlId` to the default profile ID (found via `accessControlProfile.list` with `isDefault=1`).  
- **Server-side enforcement.** Access control is enforced on the Kaltura servers, not client-side. Rules apply regardless of which player or device is used.  


# 15. Related Guides

- **[Content Delivery API](KALTURA_CONTENT_DELIVERY_API.md)** — playManifest, raw serve, download URLs where access control is enforced  
- **[Session Guide](KALTURA_SESSION_GUIDE.md)** — KS generation for authenticated access control conditions  
- **[Categories & Entitlements API](KALTURA_CATEGORIES_AND_ENTITLEMENTS_API.md)** — Category-based content entitlements (complementary to access control)  
- **[Custom Metadata API](KALTURA_CUSTOM_METADATA_API.md)** — Metadata profiles referenced in metadata conditions  
- **[Thumbnail & Image API](KALTURA_THUMBNAIL_API.md)** — Thumbnail delivery subject to THUMBNAIL context rules  
- **[Player Embed Guide](KALTURA_PLAYER_EMBED_GUIDE.md)** — Player handles access control responses and error messages  
- **[Upload & Ingestion API](KALTURA_UPLOAD_AND_INGESTION_API.md)** — Entry creation with `accessControlId` assignment  

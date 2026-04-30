# Kaltura Webhooks & Event Notifications API

Kaltura's event notification system sends real-time HTTP webhooks or emails when events occur on your content — entry uploaded, transcoding complete, metadata changed, caption added, and more. Create notification templates that define what triggers a notification, what data to send, and where to send it. Templates fire automatically when matching events occur, or manually via the `dispatch` action. Email notifications are delivered through the Kaltura Messaging microservice, providing SendGrid-based delivery with per-recipient tracking, engagement analytics, and CAN-SPAM compliance.

**Base URL:** `https://www.kaltura.com/api_v3` (may differ by region/deployment)  
**Auth:** KS passed as `ks` parameter in POST form data (see [Session Guide](KALTURA_SESSION_GUIDE.md))  
**Format:** Form-encoded POST, `format=1` for JSON responses  
**Service:** `eventnotification_eventnotificationtemplate` (plugin service — all lowercase with plugin prefix)  

<!-- Sections: 1.When to Use | 2.Prerequisites | 3.Quick Start (2-step webhook) | 4.Core Concepts | 5.Discover System Templates | 6.Clone a System Template | 7.Create HTTP Webhook (conditions, auth, params, payload) | 8.Webhook Signing | 9.Payload Structure | 10.Email Notifications | 11.Template CRUD | 12.Manual Dispatch | 13.Integration Patterns (8) | 14.API Reference | 15.Error Handling | 16.Best Practices | 17.Related Guides -->


# 1. When to Use

- **Event-driven integrations** — Trigger automated workflows in external systems (CMS, LMS, CRM) when content events occur in Kaltura, such as upload complete or transcoding finished  
- **Real-time notifications on content changes** — Receive immediate HTTP callbacks when entries are created, updated, or deleted, enabling responsive dashboards and audit logs  
- **Workflow automation triggers** — Chain Kaltura events to downstream processing steps like caption ordering, distribution publishing, or compliance review without polling the API  


# 2. Prerequisites

- A Kaltura account with the Event Notification plugin enabled (contact your Kaltura account manager if `eventNotificationTemplate` actions return `SERVICE_FORBIDDEN`)
- An ADMIN KS (type=2) with `disableentitlement` privilege for full template management
- For HTTP webhooks: an HTTPS endpoint to receive POST callbacks
- For email notifications: valid sender/recipient email addresses (delivery via the [Messaging Service](KALTURA_MESSAGING_API.md))


# 3. Quick Start — Your First Webhook in 2 Steps

The fastest way to get a working webhook: clone a system template and point it at your URL.

**Step 1 — Find a system template to clone:**

```bash
curl -X POST "$KALTURA_SERVICE_URL/service/eventnotification_eventnotificationtemplate/action/listTemplates" \
  -d "ks=$KALTURA_KS" \
  -d "format=1" \
  -d "filter[objectType]=KalturaEventNotificationTemplateFilter" \
  -d "filter[typeEqual]=httpNotification.Http"
```

Pick the template matching your use case (e.g., "Entry Status Changed" for entry events). Note its `id`.

**Step 2 — Clone it with your URL and configuration:**

```bash
curl -X POST "$KALTURA_SERVICE_URL/service/eventnotification_eventnotificationtemplate/action/clone" \
  -d "ks=$KALTURA_KS" \
  -d "format=1" \
  -d "id=$SYSTEM_TEMPLATE_ID" \
  -d "eventNotificationTemplate[objectType]=KalturaHttpNotificationTemplate" \
  -d "eventNotificationTemplate[name]=My Webhook" \
  -d "eventNotificationTemplate[systemName]=MY_WEBHOOK" \
  -d "eventNotificationTemplate[url]=https://myapp.example.com/webhooks/kaltura" \
  -d "eventNotificationTemplate[method]=2" \
  -d "eventNotificationTemplate[data][objectType]=KalturaHttpNotificationObjectData" \
  -d "eventNotificationTemplate[data][format]=1" \
  -d "eventNotificationTemplate[data][apiObjectType]=KalturaBaseEntry" \
  -d "eventNotificationTemplate[signSecret]=my-secret-key" \
  -d "eventNotificationTemplate[secureHashingAlgo]=2"
```

The clone creates the template in DISABLED status. Activate it:

```bash
curl -X POST "$KALTURA_SERVICE_URL/service/eventnotification_eventnotificationtemplate/action/updateStatus" \
  -d "ks=$KALTURA_KS" \
  -d "format=1" \
  -d "id=$TEMPLATE_ID" \
  -d "status=2"
```

That's it. Your endpoint will now receive JSON POST requests whenever the matching event occurs. The payload is a `KalturaHttpNotification` object containing the full entry data. Verify the `X-KALTURA-SIGNATURE` header against `SHA256(signing_secret + raw_body)` to authenticate requests.

For email notifications, see section 10. For advanced conditions (fire only on specific field changes), see section 7.3.


# 4. Core Concepts

## 4.1 Template Types

Each notification template has a `type` string that determines its delivery channel:

| Type Value | Object Type | Description |
|------------|-------------|-------------|
| `httpNotification.Http` | `KalturaHttpNotificationTemplate` | Send an HTTP POST/GET to a URL when an event occurs |
| `emailNotification.Email` | `KalturaEmailNotificationTemplate` | Send an email when an event occurs (delivered via the Messaging Service) |

Use the string value (e.g., `httpNotification.Http`) when filtering by type. The system also supports additional notification types: **Boolean** templates define reusable conditions for [REACH automation rules](KALTURA_REACH_API.md#reach-automation-rules), while Push and Kafka templates are used internally by Kaltura platform services.

## 4.2 Event Types

Events that can trigger a notification (integer IDs):

| Event Type | ID | Description |
|------------|----|-------------|
| OBJECT_ADDED | 1 | A new object was created |
| OBJECT_CHANGED | 2 | An object was modified |
| OBJECT_COPIED | 3 | An object was copied |
| OBJECT_CREATED | 5 | An object was fully created (post-processing complete) |
| OBJECT_DATA_CHANGED | 6 | An object's associated data changed |
| OBJECT_DELETED | 7 | An object was deleted |
| OBJECT_ERASED | 10 | An object was permanently erased |
| OBJECT_READY_FOR_REPLACMENT | 11 | An object is ready for content replacement |
| OBJECT_READY_FOR_INDEX | 12 | An object is ready for search indexing |

Plugin-contributed event types use string IDs (e.g., `integrationEventNotifications.INTEGRATION_JOB_CLOSED`).

## 4.3 Event Object Types

The type of Kaltura object that triggers the event:

| Object Type | ID | Description |
|-------------|----|-------------|
| ENTRY | 1 | Media entries (video, audio, image, document) |
| CATEGORY | 2 | Content categories |
| ASSET | 3 | Generic assets |
| FLAVORASSET | 4 | Transcoded video flavors |
| THUMBASSET | 5 | Thumbnail assets |
| KUSER | 8 | Users |
| ACCESSCONTROL | 9 | Access control profiles |
| BATCHJOB | 10 | Batch processing jobs |
| BULKUPLOADRESULT | 11 | Bulk upload results |
| CATEGORYKUSER | 12 | Category-user assignments |
| CONVERSIONPROFILE2 | 14 | Conversion profiles |
| FLAVORPARAMS | 15 | Flavor parameters |
| PERMISSION | 18 | Permissions |
| ROLE | 20 | User roles |
| USERLOGINDATA | 22 | Login data |
| LIVE_STREAM | 38 | Live stream entries |
| SERVER_NODE | 39 | Server nodes |
| ENTRY_VENDOR_TASK | 42 | REACH enrichment service tasks (captions, translations, moderation, and more) |

Plugin-contributed object types use string IDs (available when the corresponding plugin is enabled):

| Object Type | String ID | Description |
|-------------|-----------|-------------|
| Metadata | `metadataEventNotifications.Metadata` | Custom metadata records |
| CuePoint | `cuePointEventNotifications.CuePoint` | In-video cue points |
| Annotation | `annotationEventNotifications.Annotation` | Annotation cue points |
| CaptionAsset | `captionAssetEventNotifications.CaptionAsset` | Caption/subtitle files |
| TranscriptAsset | `transcriptAssetEventNotifications.TranscriptAsset` | Transcript files |
| AttachmentAsset | `attachmentAssetEventNotifications.AttachmentAsset` | Attachment files |
| ScheduleEvent | `scheduleEventNotifications.ScheduleEvent` | Scheduled events |
| VirtualEvent | `virtualEventEventNotifications.VirtualEvent` | Virtual events |
| DropFolder | `dropFolderEventNotifications.DropFolder` | Drop folders |
| DropFolderFile | `dropFolderEventNotifications.DropFolderFile` | Drop folder files |
| EntryDistribution | `contentDistributionEventNotifications.EntryDistribution` | Content distribution records |
| AdCuePoint | `adCuePointEventNotifications.AdCuePoint` | Ad cue points |

## 4.4 Template Status

| Status | ID | Description |
|--------|----|-------------|
| DISABLED | 1 | Template exists but does not fire |
| ACTIVE | 2 | Template fires on matching events |

Status is read-only on the template object. Use the `updateStatus` action to change it (see section 11.4). Deleting a template is a hard delete — the template is permanently removed and no longer retrievable via `get`.

## 4.5 Automatic vs Manual Dispatch

- **Automatic dispatch:** The template fires whenever a matching event occurs (based on `eventType`, `eventObjectType`, and optional `eventConditions`). This is the default behavior for active templates.
- **Manual dispatch:** Call the `dispatch` action to fire a template on demand for a specific object, regardless of whether the event occurred naturally.


# 5. Discover System Templates

Kaltura provides pre-built system templates (owned by partner 0) that cover common notification scenarios. Use `listTemplates` to discover them, then `clone` to create your own copy.

## 5.1 List System Templates

```bash
curl -X POST "$KALTURA_SERVICE_URL/service/eventnotification_eventnotificationtemplate/action/listTemplates" \
  -d "ks=$KALTURA_KS" \
  -d "format=1"
```

**Response:**
```json
{
  "totalCount": 15,
  "objects": [
    {
      "id": 1234,
      "name": "Entry Ready",
      "systemName": "ENTRY_READY",
      "type": 1,
      "status": 1,
      "objectType": "KalturaHttpNotificationTemplate"
    }
  ]
}
```

Returns all system templates available for cloning. Each template includes `id`, `name`, `description`, `type`, `eventType`, and `eventObjectType`.

## 5.2 List with Filtering

Filter system templates by type or event:

```bash
curl -X POST "$KALTURA_SERVICE_URL/service/eventnotification_eventnotificationtemplate/action/listTemplates" \
  -d "ks=$KALTURA_KS" \
  -d "format=1" \
  -d "filter[objectType]=KalturaEventNotificationTemplateFilter" \
  -d "filter[typeEqual]=httpNotification.Http" \
  -d "filter[orderBy]=-createdAt"
```

| Filter Field | Description |
|-------------|-------------|
| `typeEqual` | Template type string (e.g., `httpNotification.Http`, `emailNotification.Email`) |
| `statusEqual` | Template status (1=disabled, 2=active, 3=deleted) |
| `eventTypeEqual` | Event type ID |
| `objectType` | Always `KalturaEventNotificationTemplateFilter` |
| `orderBy` | Sort field (prefix `-` for descending): `+createdAt`, `-createdAt`, `+updatedAt`, `-updatedAt`, `+id`, `-id` |

### Pager

```bash
  -d "pager[objectType]=KalturaFilterPager" \
  -d "pager[pageSize]=50" \
  -d "pager[pageIndex]=1"
```


# 6. Clone a System Template

The recommended way to create notification templates is to clone an existing system template and customize it. This inherits the correct event type, object type, and condition structure.

```bash
curl -X POST "$KALTURA_SERVICE_URL/service/eventnotification_eventnotificationtemplate/action/clone" \
  -d "ks=$KALTURA_KS" \
  -d "format=1" \
  -d "id=$SYSTEM_TEMPLATE_ID" \
  -d "eventNotificationTemplate[objectType]=KalturaHttpNotificationTemplate" \
  -d "eventNotificationTemplate[name]=My Entry Ready Webhook" \
  -d "eventNotificationTemplate[systemName]=MY_ENTRY_READY" \
  -d "eventNotificationTemplate[url]=https://example.com/webhooks/kaltura" \
  -d "eventNotificationTemplate[method]=2"
```

Cloned templates are created in DISABLED status. Activate with `updateStatus`:

```bash
curl -X POST "$KALTURA_SERVICE_URL/service/eventnotification_eventnotificationtemplate/action/updateStatus" \
  -d "ks=$KALTURA_KS" \
  -d "format=1" \
  -d "id=$TEMPLATE_ID" \
  -d "status=2"
```

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `id` | integer | Yes | System template ID to clone from |
| `eventNotificationTemplate[objectType]` | string | Yes | `KalturaHttpNotificationTemplate` or `KalturaEmailNotificationTemplate` |
| `eventNotificationTemplate[name]` | string | No | Override the template name |
| `eventNotificationTemplate[systemName]` | string | No | Unique system name (required if the source template has one) |
| `eventNotificationTemplate[url]` | string | No | Webhook URL (HTTP templates) |
| `eventNotificationTemplate[method]` | integer | No | HTTP method: 1=GET, 2=POST |

**Response (clone):**
```json
{
  "id": 26970301,
  "partnerId": 123456,
  "name": "My Entry Ready Webhook",
  "systemName": "ENTRY_READY",
  "description": "Fires when an entry changes status",
  "type": "httpNotification.Http",
  "status": 2,
  "createdAt": 1718400000,
  "updatedAt": 1718400000,
  "eventType": 2,
  "eventObjectType": "1",
  "objectType": "KalturaHttpNotificationTemplate"
}
```

The cloned template gets a new `id` owned by your partner account. The original system template remains unchanged.


# 7. Create an HTTP Webhook Template

Create a template from scratch (instead of cloning) when you need full control over every field. The `add` action requires higher privileges than `clone` — some accounts can only use `clone`. Prefer cloning system templates (section 6) for most use cases.

```bash
curl -X POST "$KALTURA_SERVICE_URL/service/eventnotification_eventnotificationtemplate/action/add" \
  -d "ks=$KALTURA_KS" \
  -d "format=1" \
  -d "eventNotificationTemplate[objectType]=KalturaHttpNotificationTemplate" \
  -d "eventNotificationTemplate[name]=Entry Ready Webhook" \
  -d "eventNotificationTemplate[description]=Fires when any entry reaches READY status" \
  -d "eventNotificationTemplate[eventType]=2" \
  -d "eventNotificationTemplate[eventObjectType]=1" \
  -d "eventNotificationTemplate[url]=https://example.com/webhooks/kaltura" \
  -d "eventNotificationTemplate[method]=2" \
  -d "eventNotificationTemplate[contentType]=2"
```

Templates are created in DISABLED status. Activate with `updateStatus` (see section 11.4) after verifying the configuration.

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `eventNotificationTemplate[objectType]` | string | Yes | `KalturaHttpNotificationTemplate` |
| `eventNotificationTemplate[name]` | string | Yes | Template display name |
| `eventNotificationTemplate[eventType]` | integer | Yes | Event type ID (see section 4.2) |
| `eventNotificationTemplate[eventObjectType]` | integer/string | Yes | Object type that triggers the event (see section 4.3) |
| `eventNotificationTemplate[url]` | string | Yes | HTTPS endpoint URL to receive webhook POSTs |
| `eventNotificationTemplate[method]` | integer | Yes | HTTP method: 1=GET, 2=POST |
| `eventNotificationTemplate[description]` | string | No | Human-readable template description |
| `eventNotificationTemplate[contentType]` | integer | No | Body content type: 1=form-encoded, 2=JSON, 3=XML, 4=text (default: 1) |
| `eventNotificationTemplate[signSecret]` | string | No | HMAC signing secret for webhook verification (see section 8) |
| `eventNotificationTemplate[secureHashingAlgo]` | integer | No | Hash algorithm: 1=SHA1, 2=SHA256, 3=SHA384, 4=SHA512, 5=MD5 |
| `eventNotificationTemplate[authUsername]` | string | No | HTTP Basic Auth username |
| `eventNotificationTemplate[authPassword]` | string | No | HTTP Basic Auth password |
| `eventNotificationTemplate[customHeaders]` | array | No | Custom HTTP headers (see section 7.4) |
| `eventNotificationTemplate[eventConditions]` | array | No | Conditions to filter when the template fires (see section 7.3) |

## 7.1 HTTP Template Fields

| Field | Type | Description |
|-------|------|-------------|
| `objectType` | string | `KalturaHttpNotificationTemplate` |
| `name` | string | Template display name |
| `description` | string | Template description |
| `eventType` | integer | Event type ID (see section 4.2) |
| `eventObjectType` | integer/string | Object type (see section 4.3) |
| `url` | string | Webhook endpoint URL (supports `{placeholder}` tokens from userParameters) |
| `method` | integer | 1=GET, 2=POST |
| `contentType` | integer | 1=`application/x-www-form-urlencoded`, 2=`application/json`, 3=`application/xml`, 4=`text/plain` |
| `data[objectType]` | string | Payload type (see section 9.4) |
| `customHeaders` | array | Custom HTTP headers (see section 7.4) |
| `authUsername` | string | HTTP authentication username (write-only — not returned in GET) |
| `authPassword` | string | HTTP authentication password (write-only — not returned in GET) |
| `authenticationMethod` | integer | HTTP auth method: 1=BASIC, 2=DIGEST, 4=GSSNEGOTIATE, 8=NTLM, 16=ANY (default: 1) |
| `sslVersion` | integer | SSL/TLS version |
| `sslCertificate` | string | Client SSL certificate |
| `sslCertificateType` | string | Certificate type (PEM, DER) |
| `sslCertificatePassword` | string | Certificate password |
| `sslKey` | string | SSL key |
| `sslKeyType` | string | Key type |
| `sslKeyPassword` | string | Key password |
| `signSecret` | string | HMAC signing secret (see section 8) |
| `secureHashingAlgo` | integer | HMAC hash algorithm: 1=SHA1, 2=SHA256, 3=SHA384, 4=SHA512, 5=MD5 |
| `eventDelayedCondition` | integer | 1=delay dispatch until entry reaches READY status (see section 7.6) |
| `userParameters` | array | Template-level custom parameters with `{placeholder}` substitution (see section 7.8) |
| `contentParameters` | array | System-evaluated dynamic parameters resolved at dispatch time (see section 7.9) |
| `status` | integer | 1=disabled, 2=active (read-only — use `updateStatus` action to change) |

## 7.2 Payload Data Configuration

System templates have no payload data configured by default — the webhook fires but sends an empty body. Configure payload data on your cloned template to include event data. See section 9.4 for the available data types (`KalturaHttpNotificationObjectData`, `KalturaHttpNotificationDataFields`) and configuration examples.

## 7.3 Event Conditions

Add conditions to control when a template fires. Conditions filter events beyond just the event type and object type.

### Which Condition Type Do I Need?

| I want to fire when... | Use this condition |
|------------------------|-------------------|
| A field has a specific value (e.g., status=READY) | `KalturaEventFieldCondition` |
| A custom metadata field changes between versions | `KalturaMetadataFieldChangedCondition` |
| Specific database columns were modified | `KalturaEventObjectChangedCondition` |
| Other boolean templates all evaluate true | `KalturaBooleanEventNotificationCondition` |

Multiple conditions on the same template are ANDed — all must be true for the notification to fire.

### Field-Value Condition (KalturaEventFieldCondition)

Fire only when a specific field has a specific value at the time of the event:

```bash
  -d "eventNotificationTemplate[eventConditions][0][objectType]=KalturaEventFieldCondition" \
  -d "eventNotificationTemplate[eventConditions][0][description]=Only when entry is READY" \
  -d "eventNotificationTemplate[eventConditions][0][field][objectType]=KalturaEvalBooleanField" \
  -d "eventNotificationTemplate[eventConditions][0][field][code]=in_array({event.object.status},array(2))"
```

This condition fires only when the object's status is 2 (READY). The `code` field uses PHP expressions with `{event.object.fieldName}` placeholders.

### Metadata Field Changed Condition (KalturaMetadataFieldChangedCondition)

Fire when a specific field in a custom metadata profile changes between versions:

```bash
  -d "eventNotificationTemplate[eventConditions][0][objectType]=KalturaMetadataFieldChangedCondition" \
  -d "eventNotificationTemplate[eventConditions][0][xPath]=/metadata/ApprovalStatus" \
  -d "eventNotificationTemplate[eventConditions][0][profileSystemName]=Content_Workflow" \
  -d "eventNotificationTemplate[eventConditions][0][versionA]=-1" \
  -d "eventNotificationTemplate[eventConditions][0][versionB]=0"
```

| Field | Type | Description |
|-------|------|-------------|
| `xPath` | string | XPath to the metadata field (e.g., `/metadata/ApprovalStatus`) |
| `profileSystemName` | string | System name of the metadata profile |
| `versionA` | string | Previous version to compare (`-1` = previous version) |
| `versionB` | string | Current version to compare (`0` = current version) |

Use this when you need to trigger a webhook specifically when a metadata field value transitions — for example, when an approval status changes from "pending" to "approved" in a custom workflow.

### Object Changed Condition (KalturaEventObjectChangedCondition)

Fire only when specific database columns on the object have changed:

```bash
  -d "eventNotificationTemplate[eventConditions][0][objectType]=KalturaEventObjectChangedCondition" \
  -d "eventNotificationTemplate[eventConditions][0][modifiedColumns]=name,description,tags"
```

| Field | Type | Description |
|-------|------|-------------|
| `modifiedColumns` | string | Comma-separated list of database column names that must have changed |

Use this with `eventType=2` (OBJECT_CHANGED) to fire only when specific fields change, rather than any update.

### Boolean Condition (KalturaBooleanEventNotificationCondition)

Reference other Boolean notification templates as reusable conditions:

```bash
  -d "eventNotificationTemplate[eventConditions][0][objectType]=KalturaBooleanEventNotificationCondition" \
  -d "eventNotificationTemplate[eventConditions][0][booleanEventNotificationIds]=101,102"
```

Boolean templates evaluate without dispatching — they return true/false. Reference them here to compose complex conditions from reusable building blocks. All referenced boolean templates must evaluate to true for the notification to fire.

## 7.4 Custom Headers

Add custom HTTP headers to webhook requests:

```bash
  -d "eventNotificationTemplate[customHeaders][0][objectType]=KalturaKeyValue" \
  -d "eventNotificationTemplate[customHeaders][0][key]=X-Custom-Header" \
  -d "eventNotificationTemplate[customHeaders][0][value]=my-value"
```

## 7.5 HTTP Authentication

Configure HTTP authentication for webhook endpoints that require credentials:

```bash
curl -X POST "$KALTURA_SERVICE_URL/service/eventnotification_eventnotificationtemplate/action/update" \
  -d "ks=$KALTURA_KS" \
  -d "format=1" \
  -d "id=$TEMPLATE_ID" \
  -d "eventNotificationTemplate[objectType]=KalturaHttpNotificationTemplate" \
  -d "eventNotificationTemplate[authUsername]=webhook-user" \
  -d "eventNotificationTemplate[authPassword]=secret-password" \
  -d "eventNotificationTemplate[authenticationMethod]=1"
```

| `authenticationMethod` Value | Method |
|-----|--------|
| 1 | HTTP Basic (default) |
| 2 | HTTP Digest |
| 4 | GSS-Negotiate |
| 8 | NTLM |
| 16 | Any (server-negotiated) |

When authentication is configured, Kaltura sends the credentials with each webhook dispatch request using the specified authentication method. The `authUsername` and `authPassword` fields are write-only — they are accepted by the API but not returned in GET responses (similar to `signSecret`).

## 7.6 Delayed Dispatch (eventDelayedCondition)

Delay notification dispatch until the entry reaches READY status. This is a native template-level flag — distinct from event conditions:

```bash
  -d "eventNotificationTemplate[eventDelayedCondition]=1"
```

When set to `1`, the system holds the notification until the entry's status becomes 2 (READY), then dispatches. Use this to avoid receiving webhooks for entries that are still processing.

Alternatively, achieve similar behavior with a field condition (useful when you need custom status checks):

```bash
  -d "eventNotificationTemplate[eventConditions][0][objectType]=KalturaEventFieldCondition" \
  -d "eventNotificationTemplate[eventConditions][0][description]=Dispatch only when entry is READY" \
  -d "eventNotificationTemplate[eventConditions][0][field][objectType]=KalturaEvalBooleanField" \
  -d "eventNotificationTemplate[eventConditions][0][field][code]={event.object.status}==2"
```

## 7.7 Parameters and Payload Data — Choosing the Right Approach

Three mechanisms control what data is included in a webhook or email. They solve different problems:

| Mechanism | Purpose | Resolved when | Use for |
|-----------|---------|---------------|---------|
| **`data`** (section 9.4) | Controls the **HTTP POST body** content | Dispatch time | Sending the full event object or specific field values in the webhook body |
| **`contentParameters`** (section 7.9) | Provides **dynamic tokens** like `{entry_id}` | Dispatch time (system-evaluated) | Email subject/body tokens, DataText placeholders |
| **`userParameters`** (section 7.8) | Provides **static tokens** like `{callback_url}` | Dispatch time (template-stored) | Making templates reusable — configure once, reference in URL/conditions |

**Decision guide:**
- Want the webhook body to contain the entry object as JSON? → Use `data` with `KalturaHttpNotificationObjectData`
- Want `{entry_name}` tokens in your email body? → Use `contentParameters` (section 7.9) with `KalturaEvalStringField`
- Want to parameterize your webhook URL or conditions? → Use `userParameters` (section 7.8) with `KalturaStringValue`
- Want a custom text body with tokens? → Use `data` with `KalturaHttpNotificationDataText` + `contentParameters`

## 7.8 User Parameters (Template-Level Custom Parameters)

User parameters are custom name/value pairs defined on the template. Their `{placeholder}` tokens are substituted in URL, conditions, and other fields at dispatch time. Use them to make templates reusable across different scenarios.

```bash
curl -X POST "$KALTURA_SERVICE_URL/service/eventnotification_eventnotificationtemplate/action/update" \
  -d "ks=$KALTURA_KS" \
  -d "format=1" \
  -d "id=$TEMPLATE_ID" \
  -d "eventNotificationTemplate[objectType]=KalturaHttpNotificationTemplate" \
  -d "eventNotificationTemplate[userParameters][0][objectType]=KalturaEventNotificationParameter" \
  -d "eventNotificationTemplate[userParameters][0][key]=metadata_field" \
  -d "eventNotificationTemplate[userParameters][0][value][objectType]=KalturaStringValue" \
  -d "eventNotificationTemplate[userParameters][0][value][value]=ApprovalStatus" \
  -d "eventNotificationTemplate[userParameters][1][objectType]=KalturaEventNotificationParameter" \
  -d "eventNotificationTemplate[userParameters][1][key]=metadata_profile" \
  -d "eventNotificationTemplate[userParameters][1][value][objectType]=KalturaStringValue" \
  -d "eventNotificationTemplate[userParameters][1][value][value]=Content_Workflow" \
  -d "eventNotificationTemplate[userParameters][2][objectType]=KalturaEventNotificationParameter" \
  -d "eventNotificationTemplate[userParameters][2][key]=callback_url" \
  -d "eventNotificationTemplate[userParameters][2][value][objectType]=KalturaStringValue" \
  -d "eventNotificationTemplate[userParameters][2][value][value]=https://myapp.example.com/hooks/approval"
```

| Field | Type | Description |
|-------|------|-------------|
| `key` | string | Parameter name — referenced as `{key}` in URL, conditions, and other template fields |
| `value[objectType]` | string | `KalturaStringValue` for static values |
| `value[value]` | string | The parameter value |
| `description` | string | Optional human-readable description |

User parameters are stored on the template and resolved at dispatch time. Reference them in the template URL: `https://myapp.example.com/hooks/{callback_url}` or in metadata conditions as `{metadata_field}`.

## 7.9 Content Parameters (System-Evaluated Dynamic Parameters)

Content parameters are resolved by the system at dispatch time from the event context. They provide dynamic values like entry names, IDs, and user details based on the triggering event.

```bash
curl -X POST "$KALTURA_SERVICE_URL/service/eventnotification_eventnotificationtemplate/action/update" \
  -d "ks=$KALTURA_KS" \
  -d "format=1" \
  -d "id=$TEMPLATE_ID" \
  -d "eventNotificationTemplate[objectType]=KalturaHttpNotificationTemplate" \
  -d "eventNotificationTemplate[contentParameters][0][objectType]=KalturaEventNotificationParameter" \
  -d "eventNotificationTemplate[contentParameters][0][key]=entry_id" \
  -d "eventNotificationTemplate[contentParameters][0][value][objectType]=KalturaEvalStringField" \
  -d "eventNotificationTemplate[contentParameters][0][value][code]={event.object.id}" \
  -d "eventNotificationTemplate[contentParameters][1][objectType]=KalturaEventNotificationParameter" \
  -d "eventNotificationTemplate[contentParameters][1][key]=entry_name" \
  -d "eventNotificationTemplate[contentParameters][1][value][objectType]=KalturaEvalStringField" \
  -d "eventNotificationTemplate[contentParameters][1][value][code]={event.object.name}" \
  -d "eventNotificationTemplate[contentParameters][2][objectType]=KalturaEventNotificationParameter" \
  -d "eventNotificationTemplate[contentParameters][2][key]=owner_id" \
  -d "eventNotificationTemplate[contentParameters][2][value][objectType]=KalturaEvalStringField" \
  -d "eventNotificationTemplate[contentParameters][2][value][code]={event.object.userId}"
```

| Value Object Type | Description |
|-------------------|-------------|
| `KalturaEvalStringField` | Evaluates a PHP expression with `{event.object.*}` placeholders |
| `KalturaStringField` | Returns a static string value |

Common `{event.object.*}` fields for entries: `id`, `name`, `description`, `userId`, `creatorId`, `tags`, `categories`, `status`, `mediaType`, `duration`, `createdAt`, `updatedAt`.

Content parameters are referenced in email subject/body as `{key}` (e.g., `{entry_id}`, `{entry_name}`) and in HTTP payload data fields.


# 8. Webhook Signing (HMAC Verification)

Secure your webhook endpoint by verifying that requests come from Kaltura using HMAC signing.

## 8.1 Configure Signing

Set a signing secret and hash algorithm on the template:

```bash
curl -X POST "$KALTURA_SERVICE_URL/service/eventnotification_eventnotificationtemplate/action/update" \
  -d "ks=$KALTURA_KS" \
  -d "format=1" \
  -d "id=$TEMPLATE_ID" \
  -d "eventNotificationTemplate[objectType]=KalturaHttpNotificationTemplate" \
  -d "eventNotificationTemplate[signSecret]=your-webhook-secret-key" \
  -d "eventNotificationTemplate[secureHashingAlgo]=2"
```

| Field | Description |
|-------|-------------|
| `signSecret` | Your shared secret for HMAC computation |
| `secureHashingAlgo` | Hash algorithm integer: 1=SHA1, 2=SHA256, 3=SHA384, 4=SHA512, 5=MD5 |

## 8.2 Verification Headers

Kaltura sends two additional headers with each webhook request:

| Header | Value |
|--------|-------|
| `X-KALTURA-SIGNATURE` | `SHA256(signing_secret + raw_body)` — hex-encoded |
| `X-KALTURA-HASH-ALGO` | The hash algorithm used (e.g., `sha256`) |

The signing key is your `signSecret` if configured, otherwise Kaltura uses your partner's admin secret as the default signing key. The `signSecret` field is write-only — it is never returned in API responses.

## 8.3 Verify on Your Server

The signature is a SHA256 hash of the signing secret concatenated with the raw POST body (not HMAC — plain concatenation):

```bash
# Verify webhook signature
EXPECTED=$(echo -n "${SIGNING_SECRET}${RAW_BODY}" | sha256sum | cut -d' ' -f1)
# Compare $EXPECTED with the X-KALTURA-SIGNATURE header value
```


# 9. Webhook Payload Structure (Verified via Live Delivery)

## 9.1 HTTP Notification Wrapper

The webhook POST body contains a JSON-serialized `KalturaHttpNotification` object. This structure has been verified by capturing actual webhook deliveries:

| Field | Type | Description |
|-------|------|-------------|
| `objectType` | string | Always `KalturaHttpNotification` |
| `object` | object | The Kaltura API object that triggered the event |
| `eventObjectType` | integer | Object type identifier (e.g., 1=ENTRY) |
| `eventType` | integer | Event type ID (e.g., 3=OBJECT_COPIED) |
| `templateId` | integer | The notification template ID that fired |
| `templateName` | string | Template display name |
| `templateSystemName` | string | Template system name |
| `eventNotificationJobId` | integer | Unique job ID for tracking this dispatch |

## 9.2 HTTP Headers

Kaltura sends these headers with each webhook request:

| Header | Example Value | Description |
|--------|--------------|-------------|
| `Content-Type` | `application/json` | JSON when using `KalturaHttpNotificationObjectData` with `format=1` |
| `X-KALTURA-SIGNATURE` | `d6b864...` | SHA256(signing_secret + body) hex digest |
| `X-KALTURA-HASH-ALGO` | `sha256` | Hash algorithm used for signature |
| `User-Agent` | `Mozilla/5.0 ...` | Kaltura's outgoing User-Agent string |

## 9.3 Example Payload (Verified)

Captured from a live webhook delivery triggered by creating an entry:

```json
{
  "object": {
    "objectType": "KalturaBaseEntry"
  },
  "eventObjectType": 1,
  "eventNotificationJobId": 33578094492,
  "templateId": 26970222,
  "templateName": "Entry Ready Webhook",
  "templateSystemName": "ENTRY_READY",
  "eventType": 3,
  "objectType": "KalturaHttpNotification"
}
```

## 9.4 Configuring Payload Data

System templates have no payload data configured by default — the webhook fires with an empty body. Configure what data to include using the `data` field on the template.

### KalturaHttpNotificationObjectData (recommended)

Sends the event object as structured JSON:

```bash
curl -X POST "$KALTURA_SERVICE_URL/service/eventnotification_eventnotificationtemplate/action/update" \
  -d "ks=$KALTURA_KS" \
  -d "format=1" \
  -d "id=$TEMPLATE_ID" \
  -d "eventNotificationTemplate[objectType]=KalturaHttpNotificationTemplate" \
  -d "eventNotificationTemplate[data][objectType]=KalturaHttpNotificationObjectData" \
  -d "eventNotificationTemplate[data][format]=1" \
  -d "eventNotificationTemplate[data][apiObjectType]=KalturaBaseEntry"
```

| Field | Type | Description |
|-------|------|-------------|
| `format` | integer | 1=JSON, 2=XML, 3=PHP serialized |
| `apiObjectType` | string | Kaltura object type to serialize (e.g., `KalturaBaseEntry`, `KalturaMediaEntry`) |
| `responseProfileId` | integer | Response profile to control which object fields are included |

The `object` field in the payload contains the API object. To get all entry fields, use a response profile or do a follow-up `media.get` call using the entry ID from the event context.

### KalturaHttpNotificationDataText

Sends a custom text body with content parameter placeholders:

```bash
  -d "eventNotificationTemplate[data][objectType]=KalturaHttpNotificationDataText" \
  -d "eventNotificationTemplate[data][content][objectType]=KalturaStringValue" \
  -d "eventNotificationTemplate[data][content][value]=Entry {entry_id} ({entry_name}) is now ready. Owner: {owner_id}"
```

The text body resolves `{placeholder}` tokens from the template's content parameters at dispatch time.

### KalturaHttpNotificationDataFields

Sends specific fields as key-value pairs in the POST body:

```bash
  -d "eventNotificationTemplate[data][objectType]=KalturaHttpNotificationDataFields" \
  -d "eventNotificationTemplate[data][fields][0][objectType]=KalturaEventNotificationParameter" \
  -d "eventNotificationTemplate[data][fields][0][key]=entryId" \
  -d "eventNotificationTemplate[data][fields][0][value][objectType]=KalturaEvalStringField" \
  -d "eventNotificationTemplate[data][fields][0][value][code]={event.object.id}" \
  -d "eventNotificationTemplate[data][fields][1][objectType]=KalturaEventNotificationParameter" \
  -d "eventNotificationTemplate[data][fields][1][key]=status" \
  -d "eventNotificationTemplate[data][fields][1][value][objectType]=KalturaEvalStringField" \
  -d "eventNotificationTemplate[data][fields][1][value][code]={event.object.status}"
```

Each field is a `KalturaEventNotificationParameter` with a `key` and a `value` evaluated at dispatch time. The result is sent as form-encoded key-value pairs in the webhook body.

## 9.5 Delivery Characteristics

| Property | Observed Value |
|----------|---------------|
| Delivery latency | ~5-15 seconds after event |
| Source IPs | Kaltura server IPs (e.g., 192.58.252.101) |
| Default body (no data config) | Empty POST, `application/x-www-form-urlencoded` |
| With ObjectData config | JSON body, `application/json` |
| Retry behavior | Up to 10 retries with exponential backoff over ~24 hours on HTTP 5xx or timeout |


# 10. Email Notifications via the Messaging Service

Email event notifications combine the event notification framework's trigger engine with the Kaltura Messaging microservice for delivery. The event notification template defines **when** to send (event type, object type, conditions) and **what** to include (subject, body, content parameters). The Messaging service handles **how** to deliver — SendGrid-based email dispatch with per-recipient tracking, engagement analytics, and CAN-SPAM compliance.

## 10.1 Architecture

The dispatch flow has two layers:

1. **Trigger layer** (Event Notification Template) — evaluates `eventType` + `eventObjectType` filters and `eventConditions`, resolves recipients from the provider configuration
2. **Delivery layer** (Messaging Service at `messaging.nvp1.ovp.kaltura.com`) — resolves template tokens, dispatches via SendGrid, tracks delivery and engagement per-recipient

When an event matches a template's conditions, the notification dispatch engine routes the email through the Messaging API, which handles template resolution, SendGrid delivery, per-recipient tracking, and CAN-SPAM compliance.

## 10.2 Create an Email Notification Template

```bash
curl -X POST "$KALTURA_SERVICE_URL/service/eventnotification_eventnotificationtemplate/action/add" \
  -d "ks=$KALTURA_KS" \
  -d "format=1" \
  -d "eventNotificationTemplate[objectType]=KalturaEmailNotificationTemplate" \
  -d "eventNotificationTemplate[name]=Entry Ready Email Alert" \
  -d "eventNotificationTemplate[eventType]=2" \
  -d "eventNotificationTemplate[eventObjectType]=1" \
  -d "eventNotificationTemplate[format]=1" \
  -d "eventNotificationTemplate[subject]=Entry {entry_id} is ready" \
  -d "eventNotificationTemplate[body]=Entry {entry_id} ({entry_name}) has finished processing and is ready for playback." \
  -d "eventNotificationTemplate[fromEmail]=notifications@example.com" \
  -d "eventNotificationTemplate[fromName]=Kaltura Notifications" \
  -d "eventNotificationTemplate[to][objectType]=KalturaEmailNotificationStaticRecipientProvider" \
  -d "eventNotificationTemplate[to][emailRecipients][0][objectType]=KalturaEmailNotificationRecipient" \
  -d "eventNotificationTemplate[to][emailRecipients][0][email][objectType]=KalturaStringValue" \
  -d "eventNotificationTemplate[to][emailRecipients][0][email][value]=admin@example.com" \
  -d "eventNotificationTemplate[to][emailRecipients][0][name][objectType]=KalturaStringValue" \
  -d "eventNotificationTemplate[to][emailRecipients][0][name][value]=Admin" \
  -d "eventNotificationTemplate[status]=1"
```

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `eventNotificationTemplate[objectType]` | string | Yes | `KalturaEmailNotificationTemplate` |
| `eventNotificationTemplate[name]` | string | Yes | Template display name |
| `eventNotificationTemplate[eventType]` | integer | Yes | Event type ID (see section 4.2) |
| `eventNotificationTemplate[eventObjectType]` | integer/string | Yes | Object type that triggers the event (see section 4.3) |
| `eventNotificationTemplate[subject]` | string | Yes | Email subject line (supports content parameters — see section 10.5) |
| `eventNotificationTemplate[body]` | string | Yes | Email body (supports content parameters and HTML when `format=1`) |
| `eventNotificationTemplate[to]` | object | Yes | Recipient provider — static, entry owner, category, or group (see section 10.4) |
| `eventNotificationTemplate[format]` | integer | No | Email format: 1=HTML, 2=plain text, 3=both (default: 1) |
| `eventNotificationTemplate[fromEmail]` | string | No | Sender email address (default: partner-configured sender) |
| `eventNotificationTemplate[fromName]` | string | No | Sender display name |
| `eventNotificationTemplate[cc]` | object | No | CC recipient provider (same structure as `to`) |
| `eventNotificationTemplate[bcc]` | object | No | BCC recipient provider (same structure as `to`) |
| `eventNotificationTemplate[status]` | integer | No | 1=disabled, 2=active (default: 1 disabled) |
| `eventNotificationTemplate[eventConditions]` | array | No | Conditions to filter when the template fires (see section 7.3) |

## 10.3 Email Template Fields

| Field | Type | Description |
|-------|------|-------------|
| `objectType` | string | `KalturaEmailNotificationTemplate` |
| `format` | integer | 1=HTML, 2=plain text, 3=both |
| `subject` | string | Email subject (supports content parameters) |
| `body` | string | Email body (supports content parameters) |
| `fromEmail` | string | Sender email address |
| `fromName` | string | Sender display name |
| `to` | object | Recipient provider (see section 10.4) |
| `cc` | object | CC recipient provider |
| `bcc` | object | BCC recipient provider |
| `status` | integer | 1=disabled, 2=active |

## 10.4 Recipient Provider Types

### Static Recipients

Send to fixed email addresses:

```bash
  -d "eventNotificationTemplate[to][objectType]=KalturaEmailNotificationStaticRecipientProvider" \
  -d "eventNotificationTemplate[to][emailRecipients][0][objectType]=KalturaEmailNotificationRecipient" \
  -d "eventNotificationTemplate[to][emailRecipients][0][email][objectType]=KalturaStringValue" \
  -d "eventNotificationTemplate[to][emailRecipients][0][email][value]=admin@example.com" \
  -d "eventNotificationTemplate[to][emailRecipients][0][name][objectType]=KalturaStringValue" \
  -d "eventNotificationTemplate[to][emailRecipients][0][name][value]=Admin User"
```

### Entry Owner

Send to the user who owns the entry (resolved at dispatch time):

```bash
  -d "eventNotificationTemplate[to][objectType]=KalturaEmailNotificationUserRecipientProvider" \
  -d "eventNotificationTemplate[to][userId][objectType]=KalturaEvalStringField" \
  -d "eventNotificationTemplate[to][userId][code]={event.object.userId}"
```

### Category Subscribers

Send to all users subscribed to a category:

```bash
  -d "eventNotificationTemplate[to][objectType]=KalturaEmailNotificationCategoryRecipientProvider" \
  -d "eventNotificationTemplate[to][categoryId][objectType]=KalturaStringValue" \
  -d "eventNotificationTemplate[to][categoryId][value]=12345"
```

### Group Members

Send to all members of a user group:

```bash
  -d "eventNotificationTemplate[to][objectType]=KalturaEmailNotificationGroupRecipientProvider" \
  -d "eventNotificationTemplate[to][groupId][objectType]=KalturaStringValue" \
  -d "eventNotificationTemplate[to][groupId][value]=content-team"
```

## 10.5 Content Parameters

Email subject and body support dynamic parameters that are resolved at dispatch time:

| Parameter | Description |
|-----------|-------------|
| `{entry_id}` | Entry ID |
| `{entry_name}` | Entry name |
| `{entry_description}` | Entry description |
| `{entry_url}` | Entry URL |
| `{category_name}` | Category name |
| `{owner_name}` | Entry owner's name |
| `{owner_email}` | Entry owner's email |
| `{partner_name}` | Partner account name |

Available parameters depend on the event object type and the content parameters defined in the template.

## 10.6 Delivery via the Messaging Service

Email notifications are delivered through the Kaltura Messaging microservice, which provides modern email infrastructure:

| Property | Value |
|----------|-------|
| Delivery infrastructure | Kaltura Messaging Service → SendGrid |
| Default sender | `customer_service@kaltura.com` (configurable per partner) |
| Delivery latency | ~10-45 seconds after triggering event |
| Format | HTML by default (configurable via `format` field) |
| Content parameters | Resolved at dispatch time (e.g., `{entry_id}`, `{category_name}`) |

### Delivery Tracking

The Messaging service tracks each email through its delivery lifecycle:

| Status | Description |
|--------|-------------|
| `sending` | Email queued for delivery |
| `processed` | Email accepted by SendGrid |
| `delivered` | Email delivered to recipient's mailbox |
| `deferred` | Delivery delayed, will retry |
| `dropped` | Email dropped (invalid address, policy) |
| `bounce` | Email bounced (mailbox full, domain not found) |

### Engagement Tracking

After delivery, the Messaging service records engagement events:

| Event | Description |
|-------|-------------|
| `open` | Recipient opened the email |
| `click` | Recipient clicked a link in the email |
| `spamreport` | Recipient reported the email as spam |
| `unsubscribed` | Recipient unsubscribed via the email link |

Query delivery status and engagement data through the Messaging API's `message/stats` and `message/listDiscreteAggregateMessages` endpoints. See the [Messaging API guide](KALTURA_MESSAGING_API.md) for full tracking and reporting documentation.

### Custom Sender Domains

For branded sending domains and dedicated deliverability, configure a custom SendGrid provider through the Messaging API:

```bash
curl -X POST "$KALTURA_MESSAGING_URL/email-provider/add" \
  -H "Authorization: Bearer $KALTURA_KS" \
  -H "Content-Type: application/json" \
  -d '{
    "type": "sendGrid",
    "apiKey": "SG.your-sendgrid-api-key",
    "domains": ["notifications.example.com"],
    "defaultSender": "alerts@notifications.example.com"
  }'
```

See the [Messaging API guide](KALTURA_MESSAGING_API.md) sections 10-11 for full provider and domain configuration.

### Unsubscribe Management

The Messaging service provides CAN-SPAM compliant unsubscribe management. Users who unsubscribe from specific groups are automatically excluded from future emails to those groups. Manage unsubscribe preferences through the Messaging API's `unsubscribe-groups` and `unsubscribe-users` endpoints. See the [Messaging API guide](KALTURA_MESSAGING_API.md) section 9 for details.

## 10.7 Event-Triggered vs Application-Triggered Email

The Kaltura platform offers two complementary email approaches that share the same Messaging delivery infrastructure:

| | Event Notification Emails (this guide) | Messaging API Direct ([Messaging API guide](KALTURA_MESSAGING_API.md)) |
|---|---|---|
| **Trigger** | Automatic — fires when a Kaltura event matches template conditions | On-demand — your application calls `message/send` explicitly |
| **Recipients** | Defined in template (static, entry owner, category subscribers, group) | Specified at send time (`userIds`, `groupIds`) |
| **Template tokens** | Kaltura content parameters (`{entry_id}`, `{owner_email}`) | Arbitrary tokens (String, User, MagicLink, JwtQrCode, UnsubscribeUri) |
| **Use case** | Reactive system alerts: "entry ready", "upload complete", "REACH task done" | Proactive communications: invitations, reminders, campaigns |
| **Delivery & tracking** | Messaging Service → SendGrid (tracking via Messaging API) | Messaging Service → SendGrid (tracking via Messaging API) |

Choose event-triggered emails when you want Kaltura to automatically react to platform events with no application code needed. Choose the Messaging API directly when your application controls the timing, recipients, and personalization. Both can be used together — for example, HTTP webhooks for processing alerts plus Messaging API for user-facing campaigns.


# 11. Template CRUD Operations

## 11.1 Get a Template

```bash
curl -X POST "$KALTURA_SERVICE_URL/service/eventnotification_eventnotificationtemplate/action/get" \
  -d "ks=$KALTURA_KS" \
  -d "format=1" \
  -d "id=$TEMPLATE_ID"
```

## 11.2 Update a Template

```bash
curl -X POST "$KALTURA_SERVICE_URL/service/eventnotification_eventnotificationtemplate/action/update" \
  -d "ks=$KALTURA_KS" \
  -d "format=1" \
  -d "id=$TEMPLATE_ID" \
  -d "eventNotificationTemplate[objectType]=KalturaHttpNotificationTemplate" \
  -d "eventNotificationTemplate[name]=Updated Webhook Name" \
  -d "eventNotificationTemplate[url]=https://example.com/webhooks/v2"
```

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `id` | integer | Yes | Template ID to update |
| `eventNotificationTemplate[objectType]` | string | Yes | `KalturaHttpNotificationTemplate` or `KalturaEmailNotificationTemplate` |
| `eventNotificationTemplate[name]` | string | No | Updated template name |
| `eventNotificationTemplate[description]` | string | No | Updated description |
| `eventNotificationTemplate[url]` | string | No | Updated webhook URL (HTTP templates only) |
| `eventNotificationTemplate[method]` | integer | No | Updated HTTP method: 1=GET, 2=POST (HTTP templates only) |
| `eventNotificationTemplate[contentType]` | integer | No | Updated content type (HTTP templates only) |
| `eventNotificationTemplate[subject]` | string | No | Updated email subject (email templates only) |
| `eventNotificationTemplate[body]` | string | No | Updated email body (email templates only) |
| `eventNotificationTemplate[signSecret]` | string | No | Updated HMAC signing secret (HTTP templates only) |
| `eventNotificationTemplate[eventConditions]` | array | No | Updated event conditions |

Fields not included remain unchanged. The `status` field cannot be changed via `update` — use the `updateStatus` action instead (section 11.4).

## 11.3 List Your Templates

```bash
curl -X POST "$KALTURA_SERVICE_URL/service/eventnotification_eventnotificationtemplate/action/list" \
  -d "ks=$KALTURA_KS" \
  -d "format=1" \
  -d "filter[objectType]=KalturaEventNotificationTemplateFilter" \
  -d "filter[orderBy]=-createdAt" \
  -d "pager[objectType]=KalturaFilterPager" \
  -d "pager[pageSize]=25" \
  -d "pager[pageIndex]=1"
```

Returns templates owned by your partner. Use filter fields to narrow results:

| Filter Field | Description |
|-------------|-------------|
| `typeEqual` | Template type string (e.g., `httpNotification.Http`, `emailNotification.Email`) |
| `statusEqual` | Template status (1=DISABLED, 2=ACTIVE, 3=DELETED) |
| `eventTypeEqual` | Event type ID |
| `idEqual` | Exact template ID |
| `partnerIdEqual` | Partner ID |
| `systemNameEqual` | System name match |
| `orderBy` | Sort: `+createdAt`, `-createdAt`, `+updatedAt`, `-updatedAt`, `+id`, `-id` |

## 11.4 Update Template Status

Template status is read-only on the template object. Use the `updateStatus` action to activate or disable a template:

```bash
# Activate a template (status=2)
curl -X POST "$KALTURA_SERVICE_URL/service/eventnotification_eventnotificationtemplate/action/updateStatus" \
  -d "ks=$KALTURA_KS" \
  -d "format=1" \
  -d "id=$TEMPLATE_ID" \
  -d "status=2"

# Disable a template (status=1)
curl -X POST "$KALTURA_SERVICE_URL/service/eventnotification_eventnotificationtemplate/action/updateStatus" \
  -d "ks=$KALTURA_KS" \
  -d "format=1" \
  -d "id=$TEMPLATE_ID" \
  -d "status=1"
```

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `id` | integer | Yes | Template ID to update |
| `status` | integer | Yes | New status: 1=DISABLED, 2=ACTIVE |

Returns the updated template object. This is the only way to change a template's status — the `update` action rejects changes to the `status` field.

## 11.5 Delete a Template

Delete permanently removes a template. After deletion, `get` returns NOT_FOUND.

```bash
curl -X POST "$KALTURA_SERVICE_URL/service/eventnotification_eventnotificationtemplate/action/delete" \
  -d "ks=$KALTURA_KS" \
  -d "format=1" \
  -d "id=$TEMPLATE_ID"
```


# 12. Manual Dispatch

Fire a notification template on demand for a specific object, bypassing the automatic event trigger:

```bash
curl -X POST "$KALTURA_SERVICE_URL/service/eventnotification_eventnotificationtemplate/action/dispatch" \
  -d "ks=$KALTURA_KS" \
  -d "format=1" \
  -d "id=$TEMPLATE_ID" \
  -d "scope[objectType]=KalturaEventNotificationScope" \
  -d "scope[objectId]=$KALTURA_ENTRY_ID" \
  -d "scope[scopeObjectType]=1"
```

| Parameter | Type | Description |
|-----------|------|-------------|
| `id` | integer | Template ID to dispatch |
| `scope[objectType]` | string | Always `KalturaEventNotificationScope` |
| `scope[objectId]` | string | The object ID to include in the notification |
| `scope[scopeObjectType]` | integer/string | Object type matching the template's `eventObjectType` |

The dispatch action creates a batch job. The response includes a job ID for tracking.

Manual dispatch is useful for:
- Testing webhook endpoints during development
- Re-sending a failed notification
- Triggering notifications for objects that were created before the template existed


# 13. Common Integration Patterns

All patterns below create templates in DISABLED status. After creating, activate with:

```bash
curl -X POST "$KALTURA_SERVICE_URL/service/eventnotification_eventnotificationtemplate/action/updateStatus" \
  -d "ks=$KALTURA_KS" -d "format=1" -d "id=$TEMPLATE_ID" -d "status=2"
```

## 13.1 Entry Processing Complete Webhook

Notify your backend when any entry finishes transcoding:

```bash
# Step 1: Find the system template for "entry changed"
SYSTEM_TEMPLATES=$(curl -s -X POST "$KALTURA_SERVICE_URL/service/eventnotification_eventnotificationtemplate/action/listTemplates" \
  -d "ks=$KALTURA_KS" \
  -d "format=1" \
  -d "filter[objectType]=KalturaEventNotificationTemplateFilter" \
  -d "filter[typeEqual]=httpNotification.Http")

# Step 2: Clone and customize
curl -X POST "$KALTURA_SERVICE_URL/service/eventnotification_eventnotificationtemplate/action/clone" \
  -d "ks=$KALTURA_KS" \
  -d "format=1" \
  -d "id=$SYSTEM_TEMPLATE_ID" \
  -d "eventNotificationTemplate[objectType]=KalturaHttpNotificationTemplate" \
  -d "eventNotificationTemplate[name]=Entry Ready Notification" \
  -d "eventNotificationTemplate[url]=https://myapp.example.com/api/webhooks/entry-ready" \
  -d "eventNotificationTemplate[method]=2" \
  -d "eventNotificationTemplate[contentType]=2" \
  -d "eventNotificationTemplate[signSecret]=my-secret-key" \
  -d "eventNotificationTemplate[secureHashingAlgo]=2" \
  -d "eventNotificationTemplate[eventDelayedCondition]=1" \
  -d "eventNotificationTemplate[status]=1"
```

Setting `eventDelayedCondition=1` ensures the webhook fires only after the entry reaches READY status, so your receiver always gets fully-processed content.

## 13.2 REACH Task Completion Webhook

Get notified when a caption, translation, or other REACH enrichment task completes:

```bash
curl -X POST "$KALTURA_SERVICE_URL/service/eventnotification_eventnotificationtemplate/action/add" \
  -d "ks=$KALTURA_KS" \
  -d "format=1" \
  -d "eventNotificationTemplate[objectType]=KalturaHttpNotificationTemplate" \
  -d "eventNotificationTemplate[name]=REACH Task Complete" \
  -d "eventNotificationTemplate[eventType]=2" \
  -d "eventNotificationTemplate[eventObjectType]=42" \
  -d "eventNotificationTemplate[url]=https://myapp.example.com/api/webhooks/reach-done" \
  -d "eventNotificationTemplate[method]=2" \
  -d "eventNotificationTemplate[contentType]=2" \
  -d "eventNotificationTemplate[data][objectType]=KalturaHttpNotificationObjectData" \
  -d "eventNotificationTemplate[data][format]=1" \
  -d "eventNotificationTemplate[data][apiObjectType]=KalturaEntryVendorTask" \
  -d "eventNotificationTemplate[status]=1"
```

Object type 42 is `ENTRY_VENDOR_TASK` — fires for caption orders, translations, moderation, and all other REACH enrichment service tasks. The payload includes the vendor task object with `status`, `serviceType`, `serviceFeature`, and `entryId`.

## 13.3 Metadata Field Change Webhook (Approval Workflow)

Trigger a webhook when a custom metadata field changes — for example, when an approval status is updated in a content workflow:

```bash
curl -X POST "$KALTURA_SERVICE_URL/service/eventnotification_eventnotificationtemplate/action/add" \
  -d "ks=$KALTURA_KS" \
  -d "format=1" \
  -d "eventNotificationTemplate[objectType]=KalturaHttpNotificationTemplate" \
  -d "eventNotificationTemplate[name]=Approval Status Changed" \
  -d "eventNotificationTemplate[systemName]=APPROVAL_STATUS_CHANGED" \
  -d "eventNotificationTemplate[eventType]=6" \
  -d "eventNotificationTemplate[eventObjectType]=metadataEventNotifications.Metadata" \
  -d "eventNotificationTemplate[url]=https://myapp.example.com/api/webhooks/approval-changed" \
  -d "eventNotificationTemplate[method]=2" \
  -d "eventNotificationTemplate[contentType]=2" \
  -d "eventNotificationTemplate[eventConditions][0][objectType]=KalturaMetadataFieldChangedCondition" \
  -d "eventNotificationTemplate[eventConditions][0][xPath]=/metadata/ApprovalStatus" \
  -d "eventNotificationTemplate[eventConditions][0][profileSystemName]=Content_Workflow" \
  -d "eventNotificationTemplate[eventConditions][0][versionA]=-1" \
  -d "eventNotificationTemplate[eventConditions][0][versionB]=0" \
  -d "eventNotificationTemplate[userParameters][0][objectType]=KalturaEventNotificationParameter" \
  -d "eventNotificationTemplate[userParameters][0][key]=metadata_field" \
  -d "eventNotificationTemplate[userParameters][0][value][objectType]=KalturaStringValue" \
  -d "eventNotificationTemplate[userParameters][0][value][value]=ApprovalStatus" \
  -d "eventNotificationTemplate[status]=1"
```

This fires only when the `ApprovalStatus` field in the `Content_Workflow` metadata profile changes between versions. The `versionA=-1` / `versionB=0` comparison means "previous version vs. current version."

## 13.4 Content Moderation Workflow (Entry Status Change)

Webhook for moderation review — fires when an entry moves to MODERATE (status=5) or BLOCKED (status=6):

```bash
curl -X POST "$KALTURA_SERVICE_URL/service/eventnotification_eventnotificationtemplate/action/add" \
  -d "ks=$KALTURA_KS" \
  -d "format=1" \
  -d "eventNotificationTemplate[objectType]=KalturaHttpNotificationTemplate" \
  -d "eventNotificationTemplate[name]=Moderation Required" \
  -d "eventNotificationTemplate[eventType]=2" \
  -d "eventNotificationTemplate[eventObjectType]=1" \
  -d "eventNotificationTemplate[url]=https://myapp.example.com/api/webhooks/moderation" \
  -d "eventNotificationTemplate[method]=2" \
  -d "eventNotificationTemplate[contentType]=2" \
  -d "eventNotificationTemplate[eventConditions][0][objectType]=KalturaEventFieldCondition" \
  -d "eventNotificationTemplate[eventConditions][0][description]=Entry moved to moderation" \
  -d "eventNotificationTemplate[eventConditions][0][field][objectType]=KalturaEvalBooleanField" \
  -d "eventNotificationTemplate[eventConditions][0][field][code]=in_array({event.object.status},array(5,6))" \
  -d "eventNotificationTemplate[data][objectType]=KalturaHttpNotificationObjectData" \
  -d "eventNotificationTemplate[data][format]=1" \
  -d "eventNotificationTemplate[data][apiObjectType]=KalturaBaseEntry" \
  -d "eventNotificationTemplate[status]=1"
```

## 13.5 Category Membership Change Email

Email category managers when new users join their channel/category:

```bash
curl -X POST "$KALTURA_SERVICE_URL/service/eventnotification_eventnotificationtemplate/action/add" \
  -d "ks=$KALTURA_KS" \
  -d "format=1" \
  -d "eventNotificationTemplate[objectType]=KalturaEmailNotificationTemplate" \
  -d "eventNotificationTemplate[name]=New Category Member" \
  -d "eventNotificationTemplate[eventType]=1" \
  -d "eventNotificationTemplate[eventObjectType]=12" \
  -d "eventNotificationTemplate[format]=1" \
  -d "eventNotificationTemplate[subject]=New member joined category" \
  -d "eventNotificationTemplate[body]=A new user has joined a category you manage.<br>Category: {category_name}<br>User: {owner_name}" \
  -d "eventNotificationTemplate[fromEmail]=notifications@example.com" \
  -d "eventNotificationTemplate[fromName]=Content Platform" \
  -d "eventNotificationTemplate[to][objectType]=KalturaEmailNotificationStaticRecipientProvider" \
  -d "eventNotificationTemplate[to][emailRecipients][0][objectType]=KalturaEmailNotificationRecipient" \
  -d "eventNotificationTemplate[to][emailRecipients][0][email][objectType]=KalturaStringValue" \
  -d "eventNotificationTemplate[to][emailRecipients][0][email][value]=manager@example.com" \
  -d "eventNotificationTemplate[to][emailRecipients][0][name][objectType]=KalturaStringValue" \
  -d "eventNotificationTemplate[to][emailRecipients][0][name][value]=Category Manager" \
  -d "eventNotificationTemplate[status]=1"
```

Object type 12 is `CATEGORYKUSER` — fires when users are added to or removed from categories.

## 13.6 New Upload Email Alert

Email an admin when new content is uploaded:

```bash
curl -X POST "$KALTURA_SERVICE_URL/service/eventnotification_eventnotificationtemplate/action/add" \
  -d "ks=$KALTURA_KS" \
  -d "format=1" \
  -d "eventNotificationTemplate[objectType]=KalturaEmailNotificationTemplate" \
  -d "eventNotificationTemplate[name]=New Upload Alert" \
  -d "eventNotificationTemplate[eventType]=1" \
  -d "eventNotificationTemplate[eventObjectType]=1" \
  -d "eventNotificationTemplate[format]=1" \
  -d "eventNotificationTemplate[subject]=New entry uploaded: {entry_name}" \
  -d "eventNotificationTemplate[body]=A new entry has been uploaded.<br>Name: {entry_name}<br>ID: {entry_id}<br>Owner: {owner_name}" \
  -d "eventNotificationTemplate[fromEmail]=kaltura@example.com" \
  -d "eventNotificationTemplate[fromName]=Kaltura System" \
  -d "eventNotificationTemplate[to][objectType]=KalturaEmailNotificationStaticRecipientProvider" \
  -d "eventNotificationTemplate[to][emailRecipients][0][objectType]=KalturaEmailNotificationRecipient" \
  -d "eventNotificationTemplate[to][emailRecipients][0][email][objectType]=KalturaStringValue" \
  -d "eventNotificationTemplate[to][emailRecipients][0][email][value]=admin@example.com" \
  -d "eventNotificationTemplate[to][emailRecipients][0][name][objectType]=KalturaStringValue" \
  -d "eventNotificationTemplate[to][emailRecipients][0][name][value]=Admin" \
  -d "eventNotificationTemplate[status]=1"
```

## 13.7 Entry Deleted Webhook (Audit / Compliance)

Track all content deletions for compliance and audit logging:

```bash
curl -X POST "$KALTURA_SERVICE_URL/service/eventnotification_eventnotificationtemplate/action/add" \
  -d "ks=$KALTURA_KS" \
  -d "format=1" \
  -d "eventNotificationTemplate[objectType]=KalturaHttpNotificationTemplate" \
  -d "eventNotificationTemplate[name]=Entry Deleted Audit" \
  -d "eventNotificationTemplate[eventType]=7" \
  -d "eventNotificationTemplate[eventObjectType]=1" \
  -d "eventNotificationTemplate[url]=https://myapp.example.com/api/audit/entry-deleted" \
  -d "eventNotificationTemplate[method]=2" \
  -d "eventNotificationTemplate[contentType]=2" \
  -d "eventNotificationTemplate[data][objectType]=KalturaHttpNotificationObjectData" \
  -d "eventNotificationTemplate[data][format]=1" \
  -d "eventNotificationTemplate[data][apiObjectType]=KalturaBaseEntry" \
  -d "eventNotificationTemplate[signSecret]=audit-secret-key" \
  -d "eventNotificationTemplate[secureHashingAlgo]=2" \
  -d "eventNotificationTemplate[status]=1"
```

Event type 7 (OBJECT_DELETED) fires when an entry is deleted. Use this for audit trails and compliance records.

## 13.8 Clone-and-Customize Pattern (Recommended Workflow)

The recommended production pattern: list system templates by `systemName`, clone, and customize with userParameters. This approach inherits tested event/condition configurations and adds your customizations on top:

```bash
# Step 1: Find the system template by systemName
curl -s -X POST "$KALTURA_SERVICE_URL/service/eventnotification_eventnotificationtemplate/action/listTemplates" \
  -d "ks=$KALTURA_KS" \
  -d "format=1" \
  -d "filter[objectType]=KalturaEventNotificationTemplateFilter" \
  -d "filter[systemNameEqual]=ENTRY_CHANGED"

# Step 2: Clone with your URL and authentication
curl -X POST "$KALTURA_SERVICE_URL/service/eventnotification_eventnotificationtemplate/action/clone" \
  -d "ks=$KALTURA_KS" \
  -d "format=1" \
  -d "id=$SYSTEM_TEMPLATE_ID" \
  -d "eventNotificationTemplate[objectType]=KalturaHttpNotificationTemplate" \
  -d "eventNotificationTemplate[name]=CRM Entry Sync" \
  -d "eventNotificationTemplate[url]=https://crm.example.com/api/kaltura/entry-changed" \
  -d "eventNotificationTemplate[method]=2" \
  -d "eventNotificationTemplate[authUsername]=kaltura-integration" \
  -d "eventNotificationTemplate[authPassword]=integration-secret" \
  -d "eventNotificationTemplate[authenticationMethod]=1" \
  -d "eventNotificationTemplate[signSecret]=crm-webhook-secret" \
  -d "eventNotificationTemplate[secureHashingAlgo]=2" \
  -d "eventNotificationTemplate[data][objectType]=KalturaHttpNotificationObjectData" \
  -d "eventNotificationTemplate[data][format]=1" \
  -d "eventNotificationTemplate[data][apiObjectType]=KalturaBaseEntry" \
  -d "eventNotificationTemplate[status]=1"
```


# 14. API Actions Reference

| Action | Description |
|--------|-------------|
| `listTemplates` | List system templates available for cloning (partner 0) |
| `clone` | Clone a system template into your partner account |
| `add` | Create a new template from scratch |
| `get` | Retrieve a template by ID |
| `update` | Update template fields |
| `list` | List your partner's templates (with filters) |
| `updateStatus` | Change template status (activate/disable) |
| `delete` | Permanently delete a template |
| `dispatch` | Manually fire a template for a specific object |
| `listByPartner` | List templates across partners (admin) |


# 15. Error Handling

| Error Code | Meaning | Resolution |
|------------|---------|------------|
| `EVENT_NOTIFICATION_TEMPLATE_NOT_FOUND` | Template ID does not exist | Verify the ID; template may have been deleted (hard delete) |
| `SERVICE_FORBIDDEN` | Event Notification plugin not enabled | Contact your Kaltura account manager to enable the plugin |
| `PROPERTY_VALIDATION_NOT_UPDATABLE` | Attempted to update an immutable field (e.g., `status` via `update`) | Use `updateStatus` action to change template status |
| `DISPATCH_DISABLED` | Manual dispatch not enabled for this template | Enable manual dispatch in template configuration, or trigger via actual events |
| `INVALID_KS` | KS is invalid, expired, or lacks required privileges | Generate a fresh admin KS with `disableentitlement` privilege |
| HTTP 500 on `list` action | Transient backend issue (known intermittent) | Retry the request; use `get` by ID as a fallback for verification |

**Retry strategy:** For transient errors (HTTP 5xx, timeouts), retry with exponential backoff: 1s, 2s, 4s, with jitter, up to 3 retries. For client errors (`INVALID_KS`, `SERVICE_FORBIDDEN`, `EVENT_NOTIFICATION_TEMPLATE_NOT_FOUND`), fix the request before retrying — these will not resolve on their own. For async operations (webhook dispatch jobs), poll with increasing intervals (5s, 10s, 30s) rather than tight loops.

# 16. Best Practices

- **Clone system templates instead of creating from scratch.** System templates provide tested defaults for common event types; customize after cloning.
- **Verify webhook signatures with HMAC.** Compute the expected signature and compare with the header value to authenticate incoming webhooks.
- **Use Boolean templates as conditions for REACH automation rules.** Boolean templates evaluate without dispatching; pair them with `KalturaReachProfile.rules` for conditional auto-processing.
- **Use the Messaging Service for user-facing emails.** Email dispatch templates use the Messaging Service (SendGrid) infrastructure — configure domain authentication for deliverability.
- **Test with manual dispatch before enabling auto-fire.** Use `dispatch` to verify your endpoint handles the payload correctly before relying on live events.
- **Design for Kaltura's retry policy.** Kaltura retries failed webhook deliveries (HTTP 5xx or timeout) up to 10 times with exponential backoff over approximately 24 hours. Your endpoint should return HTTP 200 promptly to acknowledge receipt, then process the payload asynchronously. If your endpoint is down for an extended period, notifications will be lost after the retry window expires. Implement idempotency on your receiver — the same notification may be delivered more than once if your endpoint returns a non-200 status before Kaltura registers the acknowledgment.
- **Use AppTokens for production webhook receivers.** Webhook receivers that call back into the Kaltura API should use AppTokens, not hardcoded admin secrets.
- **Use `eventDelayedCondition` for content-dependent workflows.** Set `eventDelayedCondition=1` on templates that need fully-processed entries (e.g., ready for playback). This avoids webhook receivers dealing with entries still in transcoding.
- **Avoid the deprecated `notification` service.** The legacy `notification.getClientNotification` API (PHP-based notification handler) is deprecated and should not be used. Use the `eventnotification_eventnotificationtemplate` service documented in this guide for all event notification needs.

# 17. Related Guides

- **[Session Guide](KALTURA_SESSION_GUIDE.md)** — KS generation and management
- **[AppTokens API](KALTURA_APPTOKENS_API.md)** — Secure server-to-server auth
- **[Upload & Ingestion](KALTURA_UPLOAD_AND_INGESTION_API.md)** — Content upload and ingestion (entries that trigger webhooks)
- **[REACH API](KALTURA_REACH_API.md)** — Enrichment services marketplace: captions, translation, moderation, and more (ENTRY_VENDOR_TASK events)
- **[Agents Manager API](KALTURA_AGENTS_MANAGER_API.md)** — Automated content processing (alternative to webhooks for content workflows)
- **[Messaging API](KALTURA_MESSAGING_API.md)** — Template-based email messaging with delivery tracking, engagement analytics, and unsubscribe management (shared delivery infrastructure for email notifications; use directly for application-triggered emails)
- **[User Management API](KALTURA_USER_MANAGEMENT_API.md)** — User event notifications (user creation, role changes)
- **[Categories & Entitlements API](KALTURA_CATEGORIES_AND_ENTITLEMENTS_API.md)** — Category event notifications (category membership changes, entitlement updates)
- **[Custom Metadata API](KALTURA_CUSTOM_METADATA_API.md)** — Metadata change events (OBJECT_ADDED, OBJECT_DATA_CHANGED, OBJECT_DELETED) that trigger webhook notifications
- **[Captions & Transcripts API](KALTURA_CAPTIONS_AND_TRANSCRIPTS_API.md)** — Caption asset events that trigger webhook notifications
- **[Distribution](KALTURA_DISTRIBUTION_API.md)** — Trigger notifications on distribution status changes
- **[Events Platform](KALTURA_EVENTS_PLATFORM_API.md)** — Event lifecycle callbacks for virtual events
- **[Syndication](KALTURA_SYNDICATION_API.md)** — Trigger feed updates on content changes
- **[Analytics Reports](KALTURA_ANALYTICS_REPORTS_API.md)** — Trigger automated reporting on content events
- **[Gamification](KALTURA_GAMIFICATION_API.md)** — Event notifications feed gamification rules engine

# Kaltura Webhooks & Event Notifications API

Real-time HTTP webhooks and email notifications triggered by platform events — entry uploaded, transcoding complete, metadata changed, user added to category, and more. Clone pre-built system templates, configure your endpoint URL and payload, and activate.

**Base URL:** `https://www.kaltura.com/api_v3` (may differ by region/deployment)  
**Auth:** KS passed as `ks` parameter in POST form data (see [Session Guide](KALTURA_SESSION_GUIDE.md))  
**Format:** Form-encoded POST, `format=1` for JSON responses  
**Service:** `eventnotification_eventnotificationtemplate`  

<!-- Sections: 1.When to Use | 2.Prerequisites | 3.Quick Start | 4.Core Concepts | 5.Discover System Templates | 6.Clone & Configure | 7.HTTP Webhook Configuration | 8.Email Notification Configuration | 9.Webhook Signing | 10.Payload Structure | 11.Template Management | 12.Integration Patterns | 13.Error Handling | 14.Best Practices | 15.Related Guides -->


# 1. When to Use

- **Event-driven integrations** — Trigger automated workflows in external systems (CMS, LMS, CRM) when content events occur in Kaltura  
- **Real-time notifications** — Receive immediate HTTP callbacks when entries are created, updated, deleted, or reach specific statuses  
- **Workflow automation** — Chain Kaltura events to downstream processing (caption ordering, distribution publishing, compliance review) without polling  
- **User notifications** — Email entry owners, category managers, or groups when platform events occur  


# 2. Prerequisites

- A Kaltura account with the Event Notification plugin enabled (requires `EVENTNOTIFICATION_PLUGIN_PERMISSION` — one-time setup by your Kaltura account team)
- An ADMIN KS (type=2) with `disableentitlement` privilege
- For HTTP webhooks: an HTTPS endpoint to receive POST callbacks
- For email notifications: valid sender/recipient email addresses


# 3. Quick Start — Your First Webhook in 3 Steps

**Step 1 — Find a system template to clone:**

```bash
curl -X POST "$KALTURA_SERVICE_URL/service/eventnotification_eventnotificationtemplate/action/listTemplates" \
  -d "ks=$KALTURA_KS" \
  -d "format=1" \
  -d "filter[objectType]=KalturaEventNotificationTemplateFilter" \
  -d "filter[typeEqual]=httpNotification.Http"
```

Pick the template matching your event (e.g., "Entry Status Changed" for entry events). Note its `id`.

**Step 2 — Clone it with your URL:**

```bash
curl -X POST "$KALTURA_SERVICE_URL/service/eventnotification_eventnotificationtemplate/action/clone" \
  -d "ks=$KALTURA_KS" \
  -d "format=1" \
  -d "id=$SYSTEM_TEMPLATE_ID" \
  -d "eventNotificationTemplate[objectType]=KalturaHttpNotificationTemplate" \
  -d "eventNotificationTemplate[name]=My Entry Webhook" \
  -d "eventNotificationTemplate[systemName]=MY_ENTRY_WEBHOOK" \
  -d "eventNotificationTemplate[url]=https://myapp.example.com/webhooks/kaltura" \
  -d "eventNotificationTemplate[method]=2" \
  -d "eventNotificationTemplate[signSecret]=my-webhook-secret" \
  -d "eventNotificationTemplate[secureHashingAlgo]=2"
```

**Step 3 — Activate:**

```bash
curl -X POST "$KALTURA_SERVICE_URL/service/eventnotification_eventnotificationtemplate/action/updateStatus" \
  -d "ks=$KALTURA_KS" \
  -d "format=1" \
  -d "id=$TEMPLATE_ID" \
  -d "status=2"
```

Your endpoint now receives JSON POST requests when the matching event occurs. Verify the `X-KALTURA-SIGNATURE` header against `SHA256(signing_secret + raw_body)` to authenticate requests.


# 4. Core Concepts

## 4.1 How It Works

Templates define **what event** triggers a notification and **where** to send it. The system monitors all platform events and dispatches notifications when a template's conditions match.

```
Platform Event (entry created, status changed, user added to category...)
        │
        ▼
Template Match? (eventType + eventObjectType + eventConditions)
        │
        ▼
Dispatch (HTTP POST to your URL, or email via Messaging Service)
```

## 4.2 Template Types

| Type String | Object Type | Delivery |
|-------------|-------------|----------|
| `httpNotification.Http` | `KalturaHttpNotificationTemplate` | HTTP POST/GET to your endpoint |
| `emailNotification.Email` | `KalturaEmailNotificationTemplate` | Email via Messaging Service (SendGrid) |

## 4.3 Event Types

| Event Type | ID | Description |
|------------|----|-------------|
| OBJECT_ADDED | 1 | A new object was created |
| OBJECT_CHANGED | 2 | An object was modified |
| OBJECT_COPIED | 3 | An object was copied |
| OBJECT_CREATED | 5 | An object was fully created (post-processing complete) |
| OBJECT_DATA_CHANGED | 6 | An object's associated data changed |
| OBJECT_DELETED | 7 | An object was deleted |
| OBJECT_ERASED | 10 | An object was permanently erased |

## 4.4 Event Object Types

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
| CATEGORYKUSER | 12 | Category-user membership assignments |
| LIVE_STREAM | 38 | Live stream entries |
| ENTRY_VENDOR_TASK | 42 | REACH enrichment tasks |

Plugin-contributed object types (string IDs):

| Object Type | String ID |
|-------------|-----------|
| Metadata | `metadataEventNotifications.Metadata` |
| CuePoint | `cuePointEventNotifications.CuePoint` |
| CaptionAsset | `captionAssetEventNotifications.CaptionAsset` |
| TranscriptAsset | `transcriptAssetEventNotifications.TranscriptAsset` |
| AttachmentAsset | `attachmentAssetEventNotifications.AttachmentAsset` |
| ScheduleEvent | `scheduleEventNotifications.ScheduleEvent` |
| VirtualEvent | `virtualEventEventNotifications.VirtualEvent` |
| EntryDistribution | `contentDistributionEventNotifications.EntryDistribution` |

## 4.5 Template Status

| Status | ID | Description |
|--------|----|-------------|
| DISABLED | 1 | Template exists but does not fire |
| ACTIVE | 2 | Template fires on matching events |

Cloned templates start in DISABLED status. Use `updateStatus` to activate.

## 4.6 Customer Permissions Model

Notification templates are created by cloning pre-built system templates. The system provides templates for common event types (entry changes, user creation, flavor status, captions, metadata, distribution). After cloning, you configure the webhook URL, signing secret, payload data, and custom headers on your copy.

| What you can do | How |
|----------------|-----|
| Browse available event templates | `listTemplates` |
| Create a notification from a system template | `clone` |
| Configure URL, headers, signing, payload | `update` on your template |
| Activate / disable | `updateStatus` |
| List your templates | `list` |
| View a template | `get` |
| Delete a template | `delete` |


# 5. Discover System Templates

System templates (owned by partner 0) define tested event/object combinations. Browse them to find the right one for your use case.

## 5.1 List All HTTP System Templates

```bash
curl -X POST "$KALTURA_SERVICE_URL/service/eventnotification_eventnotificationtemplate/action/listTemplates" \
  -d "ks=$KALTURA_KS" \
  -d "format=1" \
  -d "filter[objectType]=KalturaEventNotificationTemplateFilter" \
  -d "filter[typeEqual]=httpNotification.Http"
```

## 5.2 List All Email System Templates

```bash
curl -X POST "$KALTURA_SERVICE_URL/service/eventnotification_eventnotificationtemplate/action/listTemplates" \
  -d "ks=$KALTURA_KS" \
  -d "format=1" \
  -d "filter[objectType]=KalturaEventNotificationTemplateFilter" \
  -d "filter[typeEqual]=emailNotification.Email"
```

## 5.3 Available System Templates (HTTP)

| System Name | Event | Object Type | Use Case |
|-------------|-------|-------------|----------|
| Entry Status Changed | OBJECT_COPIED (3) | ENTRY (1) | Entry status transitions |
| Entry Status Equals | OBJECT_COPIED (3) | ENTRY (1) | Entry reaches specific status |
| Entry Changed | OBJECT_COPIED (3) | ENTRY (1) | Any entry modification |
| Metadata Field Changed | OBJECT_DATA_CHANGED (6) | Metadata (plugin) | Custom metadata field updated |
| Entry Added to Category | OBJECT_CREATED (5) | CATEGORYENTRY (37) | Entry assigned to category |
| Entry Approved In Category | OBJECT_CHANGED (3) | CATEGORYENTRY (37) | Entry status changed to ACTIVE in category |
| Entry Rejected In Category | OBJECT_CHANGED (3) | CATEGORYENTRY (37) | Entry status changed to REJECTED in category |
| User was added to category | OBJECT_ADDED (2) | CATEGORYKUSER (12) | User added to category with ACTIVE status |
| User was removed from category | OBJECT_DELETED (7) | CATEGORYKUSER (12) | User removed from category |
| Flavor Asset Status Equals | OBJECT_COPIED (3) | FLAVORASSET (4) | Transcoding complete |
| Flavor Asset Status Changed | OBJECT_CHANGED (3) | FLAVORASSET (4) | Flavor processing transitions |
| New Caption Asset Added | OBJECT_CREATED (5) | CaptionAsset (plugin) | Caption uploaded |
| User created | OBJECT_CREATED (5) | KUSER (8) | New user provisioned |
| Category Created | OBJECT_CREATED (5) | CATEGORY (2) | New category added |
| Category Deleted | OBJECT_DELETED (7) | CATEGORY (2) | Category removed |

## 5.4 Available System Templates (Email)

| System Name | Event | Object Type | Use Case |
|-------------|-------|-------------|----------|
| User was added to category | OBJECT_CHANGED (2) | CATEGORYKUSER (12) | Category membership notification |
| User's role was changed | OBJECT_CHANGED (3) | CATEGORYKUSER (12) | Role change notification |
| User was removed from category | OBJECT_DELETED (7) | CATEGORYKUSER (12) | Membership removal notification |
| Subscriber Added to Channel | OBJECT_CREATED (5) | CATEGORYKUSER (12) | Channel subscription |

## 5.5 Filter Options

| Filter Field | Description |
|-------------|-------------|
| `typeEqual` | `httpNotification.Http` or `emailNotification.Email` |
| `orderBy` | `+createdAt`, `-createdAt`, `+id`, `-id` |

Use the pager for large result sets:

```bash
  -d "pager[objectType]=KalturaFilterPager" \
  -d "pager[pageSize]=50" \
  -d "pager[pageIndex]=1"
```


# 6. Clone & Configure a Template

Cloning creates a copy of a system template on your account. Set your endpoint URL and signing secret at clone time.

## 6.1 Clone an HTTP Template

```bash
curl -X POST "$KALTURA_SERVICE_URL/service/eventnotification_eventnotificationtemplate/action/clone" \
  -d "ks=$KALTURA_KS" \
  -d "format=1" \
  -d "id=$SYSTEM_TEMPLATE_ID" \
  -d "eventNotificationTemplate[objectType]=KalturaHttpNotificationTemplate" \
  -d "eventNotificationTemplate[name]=Entry Ready Webhook" \
  -d "eventNotificationTemplate[systemName]=MY_ENTRY_READY" \
  -d "eventNotificationTemplate[url]=https://myapp.example.com/webhooks/entry-ready" \
  -d "eventNotificationTemplate[method]=2" \
  -d "eventNotificationTemplate[signSecret]=my-webhook-secret" \
  -d "eventNotificationTemplate[secureHashingAlgo]=2"
```

## 6.2 Clone an Email Template

```bash
curl -X POST "$KALTURA_SERVICE_URL/service/eventnotification_eventnotificationtemplate/action/clone" \
  -d "ks=$KALTURA_KS" \
  -d "format=1" \
  -d "id=842" \
  -d "eventNotificationTemplate[objectType]=KalturaEmailNotificationTemplate" \
  -d "eventNotificationTemplate[name]=Category Member Added Email" \
  -d "eventNotificationTemplate[systemName]=MY_CATUSER_ADDED"
```

## 6.3 Clone Parameters

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `id` | integer | Yes | System template ID to clone |
| `eventNotificationTemplate[objectType]` | string | Yes | Must match the source template type |
| `eventNotificationTemplate[name]` | string | No | Override display name |
| `eventNotificationTemplate[systemName]` | string | No | Unique system name (must be unique across your account) |
| `eventNotificationTemplate[url]` | string | No | Webhook URL (HTTP templates) |
| `eventNotificationTemplate[method]` | integer | No | 1=GET, 2=POST |
| `eventNotificationTemplate[signSecret]` | string | No | HMAC signing secret |
| `eventNotificationTemplate[secureHashingAlgo]` | integer | No | 1=SHA1, 2=SHA256, 3=SHA384, 4=SHA512, 5=MD5 |

The cloned template inherits the source template's `eventType`, `eventObjectType`, and `eventConditions`. These fields are fixed at clone time.

## 6.4 Activate the Template

Cloned templates start in DISABLED status. Activate after verifying configuration:

```bash
curl -X POST "$KALTURA_SERVICE_URL/service/eventnotification_eventnotificationtemplate/action/updateStatus" \
  -d "ks=$KALTURA_KS" \
  -d "format=1" \
  -d "id=$TEMPLATE_ID" \
  -d "status=2"
```


# 7. HTTP Webhook Configuration

After cloning, configure your template's delivery settings using the `update` action.

## 7.1 Set Webhook URL and Payload

```bash
curl -X POST "$KALTURA_SERVICE_URL/service/eventnotification_eventnotificationtemplate/action/update" \
  -d "ks=$KALTURA_KS" \
  -d "format=1" \
  -d "id=$TEMPLATE_ID" \
  -d "eventNotificationTemplate[objectType]=KalturaHttpNotificationTemplate" \
  -d "eventNotificationTemplate[url]=https://myapp.example.com/webhooks/kaltura" \
  -d "eventNotificationTemplate[method]=2" \
  -d "eventNotificationTemplate[contentType]=2" \
  -d "eventNotificationTemplate[data][objectType]=KalturaHttpNotificationObjectData" \
  -d "eventNotificationTemplate[data][format]=1" \
  -d "eventNotificationTemplate[data][apiObjectType]=KalturaBaseEntry"
```

## 7.2 Updatable HTTP Fields

| Field | Type | Description |
|-------|------|-------------|
| `url` | string | Webhook endpoint URL |
| `method` | integer | 1=GET, 2=POST |
| `contentType` | integer | 1=form-encoded, 2=JSON, 3=XML, 4=text |
| `data[objectType]` | string | Payload type (see section 10) |
| `signSecret` | string | HMAC signing secret (write-only) |
| `secureHashingAlgo` | integer | Hash algorithm: 1=SHA1, 2=SHA256, 3=SHA384, 4=SHA512, 5=MD5 |
| `authUsername` | string | HTTP Basic Auth username (write-only) |
| `authPassword` | string | HTTP Basic Auth password (write-only) |
| `authenticationMethod` | integer | 1=BASIC, 2=DIGEST, 4=GSSNEGOTIATE, 8=NTLM |
| `customHeaders` | array | Custom HTTP headers |
| `userParameters` | array | Template-level static parameters |

## 7.3 Custom Headers

```bash
curl -X POST "$KALTURA_SERVICE_URL/service/eventnotification_eventnotificationtemplate/action/update" \
  -d "ks=$KALTURA_KS" \
  -d "format=1" \
  -d "id=$TEMPLATE_ID" \
  -d "eventNotificationTemplate[objectType]=KalturaHttpNotificationTemplate" \
  -d "eventNotificationTemplate[customHeaders][0][objectType]=KalturaKeyValue" \
  -d "eventNotificationTemplate[customHeaders][0][key]=X-Source-System" \
  -d "eventNotificationTemplate[customHeaders][0][value]=kaltura" \
  -d "eventNotificationTemplate[customHeaders][1][objectType]=KalturaKeyValue" \
  -d "eventNotificationTemplate[customHeaders][1][key]=X-Environment" \
  -d "eventNotificationTemplate[customHeaders][1][value]=production"
```

## 7.4 HTTP Authentication

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

## 7.5 User Parameters (Static Tokens)

User parameters store static values on the template. Reference them as `{key}` in the URL or payload.

```bash
curl -X POST "$KALTURA_SERVICE_URL/service/eventnotification_eventnotificationtemplate/action/update" \
  -d "ks=$KALTURA_KS" \
  -d "format=1" \
  -d "id=$TEMPLATE_ID" \
  -d "eventNotificationTemplate[objectType]=KalturaHttpNotificationTemplate" \
  -d "eventNotificationTemplate[userParameters][0][objectType]=KalturaEventNotificationParameter" \
  -d "eventNotificationTemplate[userParameters][0][key]=environment" \
  -d "eventNotificationTemplate[userParameters][0][value][objectType]=KalturaStringValue" \
  -d "eventNotificationTemplate[userParameters][0][value][value]=production"
```

## 7.6 Delayed Dispatch

Delay webhook delivery until the entry reaches READY status (useful for upload/transcoding events):

```bash
curl -X POST "$KALTURA_SERVICE_URL/service/eventnotification_eventnotificationtemplate/action/update" \
  -d "ks=$KALTURA_KS" \
  -d "format=1" \
  -d "id=$TEMPLATE_ID" \
  -d "eventNotificationTemplate[objectType]=KalturaHttpNotificationTemplate" \
  -d "eventNotificationTemplate[eventDelayedCondition]=1"
```


# 8. Email Notification Configuration

Email notifications combine the event notification trigger engine with the Kaltura Messaging microservice for delivery (SendGrid-based, with tracking and CAN-SPAM compliance).

## 8.1 Configure Email Fields After Cloning

```bash
curl -X POST "$KALTURA_SERVICE_URL/service/eventnotification_eventnotificationtemplate/action/update" \
  -d "ks=$KALTURA_KS" \
  -d "format=1" \
  -d "id=$TEMPLATE_ID" \
  -d "eventNotificationTemplate[objectType]=KalturaEmailNotificationTemplate" \
  -d "eventNotificationTemplate[subject]=Entry {entry_name} is ready" \
  -d "eventNotificationTemplate[body]=Entry {entry_id} has finished processing." \
  -d "eventNotificationTemplate[fromEmail]=notifications@example.com" \
  -d "eventNotificationTemplate[fromName]=Video Platform" \
  -d "eventNotificationTemplate[to][objectType]=KalturaEmailNotificationStaticRecipientProvider" \
  -d "eventNotificationTemplate[to][emailRecipients][0][objectType]=KalturaEmailNotificationRecipient" \
  -d "eventNotificationTemplate[to][emailRecipients][0][email][objectType]=KalturaStringValue" \
  -d "eventNotificationTemplate[to][emailRecipients][0][email][value]=admin@example.com" \
  -d "eventNotificationTemplate[to][emailRecipients][0][name][objectType]=KalturaStringValue" \
  -d "eventNotificationTemplate[to][emailRecipients][0][name][value]=Admin"
```

## 8.2 Email Template Fields

| Field | Type | Description |
|-------|------|-------------|
| `subject` | string | Email subject (supports `{token}` placeholders) |
| `body` | string | Email body — HTML or plain text (supports `{token}` placeholders) |
| `format` | integer | 1=HTML, 2=plain text, 3=both |
| `fromEmail` | string | Sender email address |
| `fromName` | string | Sender display name |
| `to` | object | Recipient provider |
| `cc` | object | CC recipient provider |
| `bcc` | object | BCC recipient provider |

## 8.3 Recipient Providers

### Static Recipients

```bash
  -d "eventNotificationTemplate[to][objectType]=KalturaEmailNotificationStaticRecipientProvider" \
  -d "eventNotificationTemplate[to][emailRecipients][0][objectType]=KalturaEmailNotificationRecipient" \
  -d "eventNotificationTemplate[to][emailRecipients][0][email][objectType]=KalturaStringValue" \
  -d "eventNotificationTemplate[to][emailRecipients][0][email][value]=admin@example.com" \
  -d "eventNotificationTemplate[to][emailRecipients][0][name][objectType]=KalturaStringValue" \
  -d "eventNotificationTemplate[to][emailRecipients][0][name][value]=Admin"
```

### Entry Owner (dynamic)

```bash
  -d "eventNotificationTemplate[to][objectType]=KalturaEmailNotificationUserRecipientProvider" \
  -d "eventNotificationTemplate[to][userId][objectType]=KalturaEvalStringField" \
  -d "eventNotificationTemplate[to][userId][code]={event.object.userId}"
```

### Category Subscribers

```bash
  -d "eventNotificationTemplate[to][objectType]=KalturaEmailNotificationCategoryRecipientProvider" \
  -d "eventNotificationTemplate[to][categoryId][objectType]=KalturaStringValue" \
  -d "eventNotificationTemplate[to][categoryId][value]=$CATEGORY_ID"
```

### Group Members

```bash
  -d "eventNotificationTemplate[to][objectType]=KalturaEmailNotificationGroupRecipientProvider" \
  -d "eventNotificationTemplate[to][groupId][objectType]=KalturaStringValue" \
  -d "eventNotificationTemplate[to][groupId][value]=content-team"
```

## 8.4 Content Parameters (Dynamic Tokens)

Content parameters resolve at dispatch time from the event context:

```bash
curl -X POST "$KALTURA_SERVICE_URL/service/eventnotification_eventnotificationtemplate/action/update" \
  -d "ks=$KALTURA_KS" \
  -d "format=1" \
  -d "id=$TEMPLATE_ID" \
  -d "eventNotificationTemplate[objectType]=KalturaEmailNotificationTemplate" \
  -d "eventNotificationTemplate[contentParameters][0][objectType]=KalturaEventNotificationParameter" \
  -d "eventNotificationTemplate[contentParameters][0][key]=entry_id" \
  -d "eventNotificationTemplate[contentParameters][0][value][objectType]=KalturaEvalStringField" \
  -d "eventNotificationTemplate[contentParameters][0][value][code]={event.object.id}" \
  -d "eventNotificationTemplate[contentParameters][1][objectType]=KalturaEventNotificationParameter" \
  -d "eventNotificationTemplate[contentParameters][1][key]=entry_name" \
  -d "eventNotificationTemplate[contentParameters][1][value][objectType]=KalturaEvalStringField" \
  -d "eventNotificationTemplate[contentParameters][1][value][code]={event.object.name}"
```

Common `{event.object.*}` fields: `id`, `name`, `description`, `userId`, `creatorId`, `tags`, `status`, `mediaType`, `duration`, `createdAt`, `updatedAt`.

## 8.5 Delivery Characteristics

| Property | Value |
|----------|-------|
| Infrastructure | Messaging Service → SendGrid |
| Delivery latency | ~10-45 seconds after event |
| Format | HTML by default (configurable) |
| Tracking | Per-recipient delivery and engagement via Messaging API |

## 8.6 Event-Triggered vs Application-Triggered Email

| | Event Notification Emails (this guide) | Messaging API Direct ([Messaging guide](KALTURA_MESSAGING_API.md)) |
|---|---|---|
| **Trigger** | Automatic on platform events | On-demand via `message/send` |
| **Recipients** | Defined in template | Specified at send time |
| **Use case** | System alerts: entry ready, task complete | Proactive: invitations, campaigns |


# 9. Webhook Signing (HMAC Verification)

## 9.1 Configure Signing

```bash
curl -X POST "$KALTURA_SERVICE_URL/service/eventnotification_eventnotificationtemplate/action/update" \
  -d "ks=$KALTURA_KS" \
  -d "format=1" \
  -d "id=$TEMPLATE_ID" \
  -d "eventNotificationTemplate[objectType]=KalturaHttpNotificationTemplate" \
  -d "eventNotificationTemplate[signSecret]=your-webhook-secret" \
  -d "eventNotificationTemplate[secureHashingAlgo]=2"
```

## 9.2 Verification Headers

Kaltura sends with each webhook request:

| Header | Value |
|--------|-------|
| `X-KALTURA-SIGNATURE` | `SHA256(signing_secret + raw_body)` — hex-encoded |
| `X-KALTURA-HASH-ALGO` | Hash algorithm used (e.g., `sha256`) |

The signing key is your `signSecret`. If no `signSecret` is configured, Kaltura uses your partner's admin secret.

## 9.3 Verify on Your Server

The signature is SHA256 of the signing secret concatenated with the raw POST body (plain concatenation, not HMAC):

```bash
EXPECTED=$(echo -n "${SIGNING_SECRET}${RAW_BODY}" | sha256sum | cut -d' ' -f1)
```

Compare `$EXPECTED` with the `X-KALTURA-SIGNATURE` header value.


# 10. Payload Structure

## 10.1 Default Behavior

System templates send an empty body by default. Configure payload data on your cloned template to include event data.

## 10.2 KalturaHttpNotificationObjectData (Recommended)

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
| `format` | integer | 1=JSON, 2=XML |
| `apiObjectType` | string | Object to serialize (e.g., `KalturaBaseEntry`, `KalturaMediaEntry`, `KalturaCategoryUser`) |

## 10.3 KalturaHttpNotificationDataText

Custom text body with content parameter placeholders:

```bash
  -d "eventNotificationTemplate[data][objectType]=KalturaHttpNotificationDataText" \
  -d "eventNotificationTemplate[data][content][objectType]=KalturaStringValue" \
  -d "eventNotificationTemplate[data][content][value]=Entry {entry_id} ({entry_name}) is now ready."
```

## 10.4 KalturaHttpNotificationDataFields

Key-value pairs in the POST body:

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

## 10.5 Webhook Payload Example

With `KalturaHttpNotificationObjectData` configured, the POST body contains:

```json
{
  "object": {
    "objectType": "KalturaBaseEntry",
    "id": "1_abc123",
    "name": "My Video",
    "status": 2
  },
  "eventObjectType": 1,
  "eventType": 3,
  "templateId": 26970222,
  "templateName": "Entry Ready Webhook",
  "templateSystemName": "MY_ENTRY_READY",
  "eventNotificationJobId": 33578094492,
  "objectType": "KalturaHttpNotification"
}
```

## 10.6 Delivery Characteristics

| Property | Value |
|----------|-------|
| Delivery latency | ~5-15 seconds after event |
| Default body (no data config) | Empty POST |
| With ObjectData config | JSON body, `application/json` |
| Retry behavior | Up to 10 retries with exponential backoff over ~24 hours on HTTP 5xx or timeout |


# 11. Template Management

## 11.1 Get a Template

```bash
curl -X POST "$KALTURA_SERVICE_URL/service/eventnotification_eventnotificationtemplate/action/get" \
  -d "ks=$KALTURA_KS" \
  -d "format=1" \
  -d "id=$TEMPLATE_ID"
```

## 11.2 List Your Templates

```bash
curl -X POST "$KALTURA_SERVICE_URL/service/eventnotification_eventnotificationtemplate/action/list" \
  -d "ks=$KALTURA_KS" \
  -d "format=1" \
  -d "filter[objectType]=KalturaEventNotificationTemplateFilter" \
  -d "filter[typeEqual]=httpNotification.Http" \
  -d "filter[orderBy]=-createdAt" \
  -d "pager[objectType]=KalturaFilterPager" \
  -d "pager[pageSize]=25" \
  -d "pager[pageIndex]=1"
```

| Filter Field | Description |
|-------------|-------------|
| `typeEqual` | `httpNotification.Http` or `emailNotification.Email` |
| `statusEqual` | 1=DISABLED, 2=ACTIVE |
| `idEqual` | Exact template ID |
| `systemNameEqual` | System name match |
| `orderBy` | `+createdAt`, `-createdAt`, `+updatedAt`, `-updatedAt`, `+id`, `-id` |

## 11.3 Update a Template

```bash
curl -X POST "$KALTURA_SERVICE_URL/service/eventnotification_eventnotificationtemplate/action/update" \
  -d "ks=$KALTURA_KS" \
  -d "format=1" \
  -d "id=$TEMPLATE_ID" \
  -d "eventNotificationTemplate[objectType]=KalturaHttpNotificationTemplate" \
  -d "eventNotificationTemplate[url]=https://myapp.example.com/webhooks/v2" \
  -d "eventNotificationTemplate[signSecret]=new-secret"
```

Fields not included remain unchanged.

## 11.4 Activate / Disable

```bash
curl -X POST "$KALTURA_SERVICE_URL/service/eventnotification_eventnotificationtemplate/action/updateStatus" \
  -d "ks=$KALTURA_KS" \
  -d "format=1" \
  -d "id=$TEMPLATE_ID" \
  -d "status=2"
```

Status values: 1=DISABLED, 2=ACTIVE. This is the only way to change status — the `update` action does not accept status changes.

## 11.5 Delete a Template

```bash
curl -X POST "$KALTURA_SERVICE_URL/service/eventnotification_eventnotificationtemplate/action/delete" \
  -d "ks=$KALTURA_KS" \
  -d "format=1" \
  -d "id=$TEMPLATE_ID"
```

Permanently removes the template.


# 12. Integration Patterns

All patterns follow the same workflow: `listTemplates` → `clone` → `update` (configure) → `updateStatus` (activate).

## 12.1 Entry Processing Complete Webhook

Notify your backend when entries finish transcoding.

```bash
curl -X POST "$KALTURA_SERVICE_URL/service/eventnotification_eventnotificationtemplate/action/listTemplates" \
  -d "ks=$KALTURA_KS" \
  -d "format=1" \
  -d "filter[objectType]=KalturaEventNotificationTemplateFilter" \
  -d "filter[typeEqual]=httpNotification.Http"
```

Find the "Entry Status Changed" template (eventType=3, eventObjectType=1), then clone:

```bash
curl -X POST "$KALTURA_SERVICE_URL/service/eventnotification_eventnotificationtemplate/action/clone" \
  -d "ks=$KALTURA_KS" \
  -d "format=1" \
  -d "id=$SYSTEM_TEMPLATE_ID" \
  -d "eventNotificationTemplate[objectType]=KalturaHttpNotificationTemplate" \
  -d "eventNotificationTemplate[name]=Entry Ready Notification" \
  -d "eventNotificationTemplate[systemName]=MY_ENTRY_READY" \
  -d "eventNotificationTemplate[url]=https://myapp.example.com/webhooks/entry-ready" \
  -d "eventNotificationTemplate[method]=2" \
  -d "eventNotificationTemplate[signSecret]=my-secret" \
  -d "eventNotificationTemplate[secureHashingAlgo]=2"
```

Configure payload and delayed dispatch (fires only when entry reaches READY):

```bash
curl -X POST "$KALTURA_SERVICE_URL/service/eventnotification_eventnotificationtemplate/action/update" \
  -d "ks=$KALTURA_KS" \
  -d "format=1" \
  -d "id=$TEMPLATE_ID" \
  -d "eventNotificationTemplate[objectType]=KalturaHttpNotificationTemplate" \
  -d "eventNotificationTemplate[eventDelayedCondition]=1" \
  -d "eventNotificationTemplate[data][objectType]=KalturaHttpNotificationObjectData" \
  -d "eventNotificationTemplate[data][format]=1" \
  -d "eventNotificationTemplate[data][apiObjectType]=KalturaBaseEntry"
```

Activate:

```bash
curl -X POST "$KALTURA_SERVICE_URL/service/eventnotification_eventnotificationtemplate/action/updateStatus" \
  -d "ks=$KALTURA_KS" \
  -d "format=1" \
  -d "id=$TEMPLATE_ID" \
  -d "status=2"
```

## 12.2 Caption/Transcript Added Webhook

Get notified when new captions or transcripts are added to entries:

```bash
curl -X POST "$KALTURA_SERVICE_URL/service/eventnotification_eventnotificationtemplate/action/listTemplates" \
  -d "ks=$KALTURA_KS" \
  -d "format=1" \
  -d "filter[objectType]=KalturaEventNotificationTemplateFilter" \
  -d "filter[typeEqual]=httpNotification.Http"
```

Find "New Caption Asset Added To Entry" (eventType=5, eventObjectType=captionAssetEventNotifications.CaptionAsset), then clone and configure.

## 12.3 Metadata Field Change Webhook

Clone the "Metadata Field Changed" system template (eventType=6, eventObjectType=metadataEventNotifications.Metadata). The template includes a `KalturaMetadataFieldChangedCondition` that fires on metadata version changes.

After cloning, update the user parameters to reference your metadata profile:

```bash
curl -X POST "$KALTURA_SERVICE_URL/service/eventnotification_eventnotificationtemplate/action/update" \
  -d "ks=$KALTURA_KS" \
  -d "format=1" \
  -d "id=$TEMPLATE_ID" \
  -d "eventNotificationTemplate[objectType]=KalturaHttpNotificationTemplate" \
  -d "eventNotificationTemplate[url]=https://myapp.example.com/webhooks/metadata-changed" \
  -d "eventNotificationTemplate[method]=2" \
  -d "eventNotificationTemplate[data][objectType]=KalturaHttpNotificationObjectData" \
  -d "eventNotificationTemplate[data][format]=1" \
  -d "eventNotificationTemplate[data][apiObjectType]=KalturaMetadata"
```

## 12.4 User Added to Category (Email)

Clone system template 842 ("User was added to category as [role]"):

```bash
curl -X POST "$KALTURA_SERVICE_URL/service/eventnotification_eventnotificationtemplate/action/clone" \
  -d "ks=$KALTURA_KS" \
  -d "format=1" \
  -d "id=842" \
  -d "eventNotificationTemplate[objectType]=KalturaEmailNotificationTemplate" \
  -d "eventNotificationTemplate[name]=New Category Member Alert" \
  -d "eventNotificationTemplate[systemName]=MY_CATUSER_ADDED"
```

Configure recipients and email content:

```bash
curl -X POST "$KALTURA_SERVICE_URL/service/eventnotification_eventnotificationtemplate/action/update" \
  -d "ks=$KALTURA_KS" \
  -d "format=1" \
  -d "id=$TEMPLATE_ID" \
  -d "eventNotificationTemplate[objectType]=KalturaEmailNotificationTemplate" \
  -d "eventNotificationTemplate[subject]=New member joined your category" \
  -d "eventNotificationTemplate[body]=A new user has been added to a category you manage." \
  -d "eventNotificationTemplate[fromEmail]=notifications@example.com" \
  -d "eventNotificationTemplate[fromName]=Video Platform" \
  -d "eventNotificationTemplate[to][objectType]=KalturaEmailNotificationStaticRecipientProvider" \
  -d "eventNotificationTemplate[to][emailRecipients][0][objectType]=KalturaEmailNotificationRecipient" \
  -d "eventNotificationTemplate[to][emailRecipients][0][email][objectType]=KalturaStringValue" \
  -d "eventNotificationTemplate[to][emailRecipients][0][email][value]=manager@example.com" \
  -d "eventNotificationTemplate[to][emailRecipients][0][name][objectType]=KalturaStringValue" \
  -d "eventNotificationTemplate[to][emailRecipients][0][name][value]=Category Manager"
```

## 12.5 Category Entry Approval/Rejection Webhook

Track when entries are approved or rejected in categories with moderation enabled:

```bash
curl -X POST "$KALTURA_SERVICE_URL/service/eventnotification_eventnotificationtemplate/action/listTemplates" \
  -d "ks=$KALTURA_KS" \
  -d "format=1" \
  -d "filter[objectType]=KalturaEventNotificationTemplateFilter" \
  -d "filter[typeEqual]=httpNotification.Http" \
  -d "filter[systemNameEqual]=HTTP_Entry_Approved_In_Category"
```

Clone the template for entry approval notifications:

```bash
curl -X POST "$KALTURA_SERVICE_URL/service/eventnotification_eventnotificationtemplate/action/clone" \
  -d "ks=$KALTURA_KS" \
  -d "format=1" \
  -d "id=$CATEGORY_ENTRY_APPROVED_TEMPLATE_ID" \
  -d "eventNotificationTemplate[objectType]=KalturaHttpNotificationTemplate" \
  -d "eventNotificationTemplate[name]=Category Entry Approved" \
  -d "eventNotificationTemplate[systemName]=MY_CATENTRY_APPROVED" \
  -d "eventNotificationTemplate[url]=https://myapp.example.com/webhooks/category-entry-approved" \
  -d "eventNotificationTemplate[method]=2" \
  -d "eventNotificationTemplate[signSecret]=my-webhook-secret" \
  -d "eventNotificationTemplate[secureHashingAlgo]=2"
```

Use the same approach with `HTTP_Entry_Rejected_In_Category` for rejection events. Both templates fire on `categoryEntry` status changes (eventType=3, eventObjectType=37) with conditions checking `CategoryEntryStatus::ACTIVE` or `CategoryEntryStatus::REJECTED`.

## 12.6 User Added/Removed from Category (HTTP Webhook)

Track category membership changes via HTTP webhooks (complement to the email templates in 12.4):

```bash
curl -X POST "$KALTURA_SERVICE_URL/service/eventnotification_eventnotificationtemplate/action/listTemplates" \
  -d "ks=$KALTURA_KS" \
  -d "format=1" \
  -d "filter[objectType]=KalturaEventNotificationTemplateFilter" \
  -d "filter[typeEqual]=httpNotification.Http" \
  -d "filter[systemNameEqual]=Http_User_Added_To_Category"
```

Clone for user membership webhooks:

```bash
curl -X POST "$KALTURA_SERVICE_URL/service/eventnotification_eventnotificationtemplate/action/clone" \
  -d "ks=$KALTURA_KS" \
  -d "format=1" \
  -d "id=$USER_ADDED_TO_CATEGORY_TEMPLATE_ID" \
  -d "eventNotificationTemplate[objectType]=KalturaHttpNotificationTemplate" \
  -d "eventNotificationTemplate[name]=User Joined Category Webhook" \
  -d "eventNotificationTemplate[systemName]=MY_USER_JOINED_CATEGORY" \
  -d "eventNotificationTemplate[url]=https://myapp.example.com/webhooks/user-category-join" \
  -d "eventNotificationTemplate[method]=2" \
  -d "eventNotificationTemplate[signSecret]=my-webhook-secret" \
  -d "eventNotificationTemplate[secureHashingAlgo]=2"
```

Use `User_Was_Removed_From_Category` for the removal counterpart. The user-added template fires on `OBJECT_ADDED` (eventType=2) for `CATEGORYKUSER` (eventObjectType=12) with status=ACTIVE. The removal template fires on `OBJECT_DELETED` (eventType=7).

## 12.7 Flavor Asset Status Change Webhook

Track transcoding progress per flavor:

```bash
curl -X POST "$KALTURA_SERVICE_URL/service/eventnotification_eventnotificationtemplate/action/clone" \
  -d "ks=$KALTURA_KS" \
  -d "format=1" \
  -d "id=$FLAVOR_STATUS_TEMPLATE_ID" \
  -d "eventNotificationTemplate[objectType]=KalturaHttpNotificationTemplate" \
  -d "eventNotificationTemplate[name]=Flavor Transcoding Complete" \
  -d "eventNotificationTemplate[systemName]=MY_FLAVOR_READY" \
  -d "eventNotificationTemplate[url]=https://myapp.example.com/webhooks/flavor-ready" \
  -d "eventNotificationTemplate[method]=2" \
  -d "eventNotificationTemplate[data][objectType]=KalturaHttpNotificationObjectData" \
  -d "eventNotificationTemplate[data][format]=1" \
  -d "eventNotificationTemplate[data][apiObjectType]=KalturaFlavorAsset"
```

## 12.8 CRM Sync (Clone-and-Customize)

Full production pattern with authentication and signing:

```bash
curl -X POST "$KALTURA_SERVICE_URL/service/eventnotification_eventnotificationtemplate/action/clone" \
  -d "ks=$KALTURA_KS" \
  -d "format=1" \
  -d "id=$SYSTEM_TEMPLATE_ID" \
  -d "eventNotificationTemplate[objectType]=KalturaHttpNotificationTemplate" \
  -d "eventNotificationTemplate[name]=CRM Entry Sync" \
  -d "eventNotificationTemplate[systemName]=CRM_ENTRY_SYNC" \
  -d "eventNotificationTemplate[url]=https://crm.example.com/api/kaltura/entry-changed" \
  -d "eventNotificationTemplate[method]=2" \
  -d "eventNotificationTemplate[authUsername]=kaltura-integration" \
  -d "eventNotificationTemplate[authPassword]=integration-secret" \
  -d "eventNotificationTemplate[authenticationMethod]=1" \
  -d "eventNotificationTemplate[signSecret]=crm-webhook-secret" \
  -d "eventNotificationTemplate[secureHashingAlgo]=2" \
  -d "eventNotificationTemplate[data][objectType]=KalturaHttpNotificationObjectData" \
  -d "eventNotificationTemplate[data][format]=1" \
  -d "eventNotificationTemplate[data][apiObjectType]=KalturaBaseEntry"
```


# 13. Error Handling

| Error Code | Meaning | Resolution |
|------------|---------|------------|
| `EVENT_NOTIFICATION_TEMPLATE_NOT_FOUND` | Template ID does not exist | Verify the ID; may have been deleted |
| `EVENT_NOTIFICATION_WRONG_TYPE` | Clone attempted with mismatched type | The `objectType` in clone must match the source template's type |
| `EVENT_NOTIFICATION_TEMPLATE_DUPLICATE_SYSTEM_NAME` | `systemName` already in use | Choose a unique system name |
| `SERVICE_FORBIDDEN` | Plugin not enabled or action restricted | Verify `EVENTNOTIFICATION_PLUGIN_PERMISSION` is enabled on your account |
| `PROPERTY_VALIDATION_NOT_UPDATABLE` | Attempted to update an immutable field | Use `updateStatus` to change status; `eventType` and `eventObjectType` are fixed at clone time |
| `INVALID_KS` | KS expired or lacks privileges | Generate a fresh admin KS with `disableentitlement` |

**Retry strategy:** For HTTP 5xx or timeouts, retry with exponential backoff (1s, 2s, 4s) up to 3 retries. Client errors (`INVALID_KS`, `SERVICE_FORBIDDEN`) require fixing the request.


# 14. Best Practices

- **Clone system templates rather than requesting custom configurations.** System templates provide tested event/condition combinations for common scenarios. Customize URL, payload, and signing after cloning.
- **Verify webhook signatures.** Compute `SHA256(signing_secret + raw_body)` and compare with the `X-KALTURA-SIGNATURE` header to authenticate incoming requests.
- **Return HTTP 200 promptly.** Acknowledge receipt immediately, then process asynchronously. Kaltura retries on 5xx/timeout up to 10 times over ~24 hours.
- **Design for at-least-once delivery.** The same notification may arrive more than once. Implement idempotency using `eventNotificationJobId`.
- **Use `eventDelayedCondition=1` for content workflows.** This ensures webhooks fire only after entries reach READY status, so receivers always get fully-processed content.
- **Use HTTPS endpoints.** Webhook URLs should use TLS for secure transit.
- **Use AppTokens for callback authentication.** Webhook receivers that call back into Kaltura should use AppTokens rather than hardcoded admin secrets.
- **Use Boolean templates as conditions for REACH automation rules.** Boolean notification templates evaluate without dispatching — pair them with `KalturaReachProfile.rules` for conditional auto-processing.


# 15. Related Guides

- **[Session Guide](KALTURA_SESSION_GUIDE.md)** — KS generation and management  
- **[AppTokens API](KALTURA_APPTOKENS_API.md)** — Secure server-to-server auth for webhook receivers  
- **[Upload & Ingestion](KALTURA_UPLOAD_AND_INGESTION_API.md)** — Content events that trigger webhooks  
- **[REACH API](KALTURA_REACH_API.md)** — Enrichment tasks (ENTRY_VENDOR_TASK events)  
- **[Messaging API](KALTURA_MESSAGING_API.md)** — Direct email sending with delivery tracking  
- **[Custom Metadata API](KALTURA_CUSTOM_METADATA_API.md)** — Metadata change events  
- **[Captions & Transcripts API](KALTURA_CAPTIONS_AND_TRANSCRIPTS_API.md)** — Caption asset events  
- **[Categories & Entitlements API](KALTURA_CATEGORIES_AND_ENTITLEMENTS_API.md)** — Category membership events  
- **[User Management API](KALTURA_USER_MANAGEMENT_API.md)** — User creation events  
- **[Distribution](KALTURA_DISTRIBUTION_API.md)** — Distribution status change events  
- **[Moderation](KALTURA_MODERATION_API.md)** — Content moderation workflows  

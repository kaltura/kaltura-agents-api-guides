# Kaltura Messaging API

The Messaging API enables sending personalized, template-based email communications to Kaltura users — event invitations, attendance confirmations, reminders, and follow-ups. Templates support dynamic tokens (user profile fields, magic login links, QR codes, unsubscribe links) that are resolved per-recipient at send time. Built-in delivery tracking, engagement analytics, and CAN-SPAM compliant unsubscribe management complete the lifecycle.

**Base URL:** `https://messaging.nvp1.ovp.kaltura.com/api/v1` (production NVP region)  
**Auth:** `Authorization: Bearer <KS>` header (ADMIN KS, type=2)  
**Format:** JSON request/response bodies, all endpoints use POST  
**Regions:** NVP (default `nvp1`), EU (`irp2`), DE (`frp2`)  

<!-- Sections: 1.When to Use | 2.Authentication | 3.Email Template Entity | 4.Token Types | 5.Manage Email Templates | 6.Send Messages | 7.Message Lifecycle | 8.Track Messages | 9.Delivery Reports | 10.Unsubscribe Management | 11.Email Provider Configuration | 12.Domain Configuration | 13.Error Handling | 14.Common Integration Patterns | 15.Best Practices | 16.Related Guides -->


# 1. When to Use

- **Event communications** — Event organizers sending personalized invitations, reminders, and follow-ups to attendees with dynamic tokens for names, magic login links, and QR codes  
- **Interactive Q&A and audience engagement** — Developers integrating real-time messaging alongside live video events to drive participation and collect audience questions  
- **Automated lifecycle messaging** — Operations teams configuring template-based email workflows triggered by registration, attendance, or content updates with built-in delivery tracking  
- **CAN-SPAM compliant bulk messaging** — Marketing teams sending branded email communications at scale with unsubscribe management, engagement analytics, and per-message delivery status  


# 2. Authentication

All requests require an ADMIN KS (type=2) in the `Authorization` header:

```
Authorization: Bearer <your_kaltura_session>
```

Generate an ADMIN KS via `session.start` (see [Session Guide](KALTURA_SESSION_GUIDE.md)) or `appToken.startSession` (see [AppTokens Guide](KALTURA_APPTOKENS_API.md)).

```bash
# Set up environment
export KALTURA_MESSAGING_URL="https://messaging.nvp1.ovp.kaltura.com/api/v1"
```


# 3. Email Template Entity

Every email template has this structure:

| Field | Type | Description |
|-------|------|-------------|
| `id` | string | Auto-generated unique identifier (read-only) |
| `partnerId` | integer | Partner ID extracted from KS (read-only) |
| `appGuid` | string | App Registry GUID this template belongs to |
| `name` | string | Template display name |
| `description` | string | Template description |
| `subject` | string | Email subject line (supports token references) |
| `body` | string | Email HTML body (supports token references) |
| `msgParamsMap` | object | Token definitions — maps token names to their types |
| `toAttributePath` | string | Token expression that resolves to the recipient email (e.g., `{recipient.email}`) |
| `from` | string | Sender email address |
| `fromName` | string | Sender display name (supports token references) |
| `cc` | string | CC email address |
| `bcc` | string | BCC email address |
| `unsubscribeGroups` | string[] | Unsubscribe group IDs for CAN-SPAM compliance |
| `status` | string | `enabled`, `disabled`, or `deleted` |
| `templateType` | string | Always `"email"` |
| `adminTags` | string | Comma-separated tags for filtering |
| `customHeaders` | object | Custom email headers (key-value pairs) |
| `numberOfTokenUsed` | integer | Number of tokens in the template (read-only) |
| `version` | integer | Auto-incrementing version number (read-only) |
| `emailProviderId` | string | Assigned email provider (read-only) |
| `createdAt` | string | ISO 8601 timestamp, e.g. `"2026-04-09T04:56:27.940Z"` (read-only) |
| `updatedAt` | string | ISO 8601 timestamp, e.g. `"2026-04-09T04:56:27.940Z"` (read-only) |


# 4. Token Types

Tokens are placeholders in the template subject, body, and fromName that get replaced with actual values at send time. Define tokens in `msgParamsMap` and reference them in the template.

**Token reference syntax:**
- User tokens: `{tokenName.fieldName}` (e.g., `{recipient.firstName}`)
- All other tokens: `{tokenName}` (e.g., `{eventLink}`)

## 4.1 Available Token Types

| Type | Description | Value at Send Time |
|------|-------------|--------------------|
| `User` | Kaltura user profile fields | User ID or `"Message.userId"` (auto-resolves from recipient) |
| `String` | Static text replacement | Any string value |
| `MagicLink` | Auto-login URL with embedded auth token | Object: `{baseURL, expiry, privileges}` |
| `Dynamic` | Type decided at send time | Resolved as String or MagicLink based on the value provided |
| `UnsubscribeUri` | CAN-SPAM unsubscribe link | URI string |
| `JwtQrCode` | QR code image with embedded JWT | Object: `{payload, secret, options?}` |

## 4.2 User Token Fields

When using a `User` type token, these fields are available from the Kaltura user record:

`id`, `partnerId`, `externalId`, `firstName`, `lastName`, `email`, `fullName`, `screenName`, `dateOfBirth`, `gender`, `thumbnailUrl`, `description`, `title`, `country`, `company`, `state`, `city`, `zip`

## 4.3 MagicLink Value Structure

```json
{
  "baseURL": "https://events.example.com/join",
  "expiry": 24,
  "privileges": "actionslimit:2"
}
```

| Field | Type | Description |
|-------|------|-------------|
| `baseURL` | string | Base URL for the magic link |
| `expiry` | integer | Link expiry in hours |
| `privileges` | string | KS privileges for the generated session |

## 4.4 JwtQrCode Value Structure

```json
{
  "payload": {"eventId": "12345", "checkIn": true},
  "secret": "your-jwt-secret",
  "options": {"color": {"dark": "#000000"}}
}
```

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `payload` | object | Yes | JWT payload data (key-value pairs) |
| `secret` | string | Yes | Secret for JWT signing |
| `options` | object | No | QR code rendering options (color settings) |


# 5. Manage Email Templates

## 5.1 Create a Template

```
POST /api/v1/email-template/add
Content-Type: application/json
Authorization: Bearer <KS>
```

```json
{
  "appGuid": "app-guid-from-registry",
  "name": "Event Invitation",
  "subject": "You're invited to {eventName}",
  "body": "<html><body><p>Hi {recipient.firstName},</p><p>Join us at {eventName}!</p><p><a href='{joinLink}'>Register</a></p></body></html>",
  "toAttributePath": "{recipient.email}",
  "msgParamsMap": {
    "recipient": {"type": "User"},
    "eventName": {"type": "String"},
    "joinLink": {"type": "MagicLink"}
  },
  "unsubscribeGroups": ["event-invitations"]
}
```

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `appGuid` | string | Yes | App Registry GUID (see [App Registry API](KALTURA_APP_REGISTRY_API.md)) |
| `name` | string | Yes | Template name |
| `subject` | string | Yes | Email subject (supports token references) |
| `body` | string | Yes | Email HTML body (supports token references) |
| `toAttributePath` | string | Yes | Token expression for recipient email |
| `msgParamsMap` | object | Yes | Token definitions (name → `{type}` mapping) |
| `description` | string | No | Template description |
| `from` | string | No | Sender email address |
| `fromName` | string | No | Sender display name |
| `cc` | string | No | CC email address |
| `bcc` | string | No | BCC email address |
| `unsubscribeGroups` | string[] | No | Unsubscribe group IDs |
| `status` | string | No | Defaults to `"enabled"` |
| `adminTags` | string | No | Comma-separated filter tags |
| `customHeaders` | object | No | Custom email headers |

**Response:** Full template object with generated `id`.

```bash
curl -X POST "$KALTURA_MESSAGING_URL/email-template/add" \
  -H "Authorization: Bearer $KALTURA_KS" \
  -H "Content-Type: application/json" \
  -d '{
    "appGuid": "'$APP_GUID'",
    "name": "Event Invitation",
    "subject": "Join us at {eventName}",
    "body": "<p>Hi {recipient.firstName}, you are invited to {eventName}.</p>",
    "toAttributePath": "{recipient.email}",
    "msgParamsMap": {
      "recipient": {"type": "User"},
      "eventName": {"type": "String"}
    }
  }'
```

Save the `id` from the response as `TEMPLATE_ID`.

## 5.2 Get a Template

```
POST /api/v1/email-template/get
Content-Type: application/json
Authorization: Bearer <KS>
```

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `id` | string | Yes | Template ID |

```bash
curl -X POST "$KALTURA_MESSAGING_URL/email-template/get" \
  -H "Authorization: Bearer $KALTURA_KS" \
  -H "Content-Type: application/json" \
  -d "{\"id\": \"$TEMPLATE_ID\"}"
```

**Response:** Full template object (see section 3 for field definitions).

## 5.3 Update a Template

```
POST /api/v1/email-template/update
Content-Type: application/json
Authorization: Bearer <KS>
```

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `id` | string | Yes | Template ID to update |
| `name` | string | No | Updated name |
| `subject` | string | No | Updated subject |
| `body` | string | No | Updated HTML body |
| `description` | string | No | Updated description |
| `from` | string | No | Updated sender email |
| `fromName` | string | No | Updated sender display name |
| `cc` | string | No | Updated CC address |
| `bcc` | string | No | Updated BCC address |
| `msgParamsMap` | object | No | Updated token definitions |
| `unsubscribeGroups` | string[] | No | Updated unsubscribe group IDs |
| `status` | string | No | `enabled`, `disabled`, or `deleted` |
| `adminTags` | string | No | Updated admin tags |
| `customHeaders` | object | No | Updated custom headers |

```bash
curl -X POST "$KALTURA_MESSAGING_URL/email-template/update" \
  -H "Authorization: Bearer $KALTURA_KS" \
  -H "Content-Type: application/json" \
  -d "{
    \"id\": \"$TEMPLATE_ID\",
    \"subject\": \"Updated: Join us at {eventName}\",
    \"description\": \"Updated event invitation template\"
  }"
```

Fields not included remain unchanged. The `version` increments on each update.

**Response:** Full updated template object with incremented `version`.

## 5.4 List Templates

```bash
curl -X POST "$KALTURA_MESSAGING_URL/email-template/list" \
  -H "Authorization: Bearer $KALTURA_KS" \
  -H "Content-Type: application/json" \
  -d '{
    "filter": {
      "appGuidIn": ["'$APP_GUID'"],
      "status": "enabled"
    },
    "pager": {"offset": 0, "limit": 25}
  }'
```

### Filter Fields

| Field | Type | Description |
|-------|------|-------------|
| `idIn` | string[] | Filter by template IDs |
| `appGuidIn` | string[] | Filter by App Registry GUIDs |
| `name` | string | Filter by name substring |
| `nameEq` | string | Filter by exact name match |
| `subject` | string | Filter by subject substring |
| `status` | string | `enabled`, `disabled`, or `deleted` |
| `adminTags` | string | Filter by admin tags substring |
| `adminTagsAll` | string | Match templates with all specified tags |
| `excludeAdminTags` | string | Exclude templates with these tags |
| `createdAtGreaterThanOrEqual` | string | ISO 8601 minimum creation date |
| `createdAtLessThanOrEqual` | string | ISO 8601 maximum creation date |
| `updatedAtGreaterThanOrEqual` | string | ISO 8601 minimum update date |
| `updatedAtLessThanOrEqual` | string | ISO 8601 maximum update date |

### Pager

| Field | Type | Default | Description |
|-------|------|---------|-------------|
| `offset` | integer | 0 | Records to skip |
| `limit` | integer | 30 | Max records to return |

**Response:** `{objects: [...], totalCount: N}`

## 5.5 Delete a Template

```
POST /api/v1/email-template/delete
Content-Type: application/json
Authorization: Bearer <KS>
```

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `id` | string | Yes | Template ID to delete |

```bash
curl -X POST "$KALTURA_MESSAGING_URL/email-template/delete" \
  -H "Authorization: Bearer $KALTURA_KS" \
  -H "Content-Type: application/json" \
  -d "{\"id\": \"$TEMPLATE_ID\"}"
```

Sets the template status to `deleted`. The template is excluded from `list` results filtered by `status: "enabled"`.


# 6. Send Messages

## 6.1 Send to Individual Users

```
POST /api/v1/message/send
Content-Type: application/json
Authorization: Bearer <KS>
```

```json
{
  "receiverType": "user",
  "userIds": ["user1@example.com", "user2@example.com"],
  "appGuid": "app-guid-from-registry",
  "templateId": "template-id",
  "type": "email",
  "msgParams": {
    "recipient": {"type": "User", "value": "Message.userId"},
    "eventName": {"type": "String", "value": "Annual Conference 2025"},
    "joinLink": {
      "type": "MagicLink",
      "value": {
        "baseURL": "https://events.example.com/join",
        "expiry": 48,
        "privileges": "actionslimit:2"
      }
    }
  },
  "session": "invitation-batch-2025-q4"
}
```

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `receiverType` | string | Yes | `"user"` or `"group"` |
| `userIds` | string[] | If user | Kaltura user IDs (email-based) |
| `groupIds` | string[] | If group | Group IDs to send to |
| `appGuid` | string | Yes | App Registry GUID |
| `templateId` | string | Yes | Email template ID |
| `type` | string | Yes | `"email"` |
| `msgParams` | object | Yes | Token values — name → `{type, value}` |
| `session` | string | No | Grouping label for tracking (e.g., `"weekly-digest"`) |
| `adminTags` | string | No | Comma-separated tags |
| `attachments` | array | No | Email attachments (see section 6.3) |
| `customHeaders` | object | No | Custom email headers (overrides template headers) |

The `msgParams` map provides runtime values for each token defined in the template's `msgParamsMap`. For `User` type tokens, set `value` to `"Message.userId"` to auto-resolve from each recipient's Kaltura profile.

**Response example:**

```json
{
  "id": "6621a3f0b2c4d5e6f7890abc",
  "bulkId": "bulk_6621a3f0",
  "partnerId": 123456,
  "appGuid": "app-guid-from-registry",
  "templateId": "template-id",
  "type": "email",
  "receiverType": "user",
  "status": "sending",
  "session": "invitation-batch-2025-q4",
  "createdAt": "2026-04-09T12:00:00.000Z",
  "updatedAt": "2026-04-09T12:00:00.000Z"
}
```

The response returns a bulk message object. The `id` is the internal message ID and `bulkId` is the external tracking identifier used with `message/stats` and `message/list`. The `status` starts as `"sending"` and transitions through the lifecycle described in section 7.

```bash
curl -X POST "$KALTURA_MESSAGING_URL/message/send" \
  -H "Authorization: Bearer $KALTURA_KS" \
  -H "Content-Type: application/json" \
  -d '{
    "receiverType": "user",
    "userIds": ["attendee@example.com"],
    "appGuid": "'$APP_GUID'",
    "templateId": "'$TEMPLATE_ID'",
    "type": "email",
    "msgParams": {
      "recipient": {"type": "User", "value": "Message.userId"},
      "eventName": {"type": "String", "value": "Q4 Town Hall"}
    }
  }'
```

## 6.2 Send to Groups

Set `receiverType` to `"group"` and provide `groupIds` instead of `userIds`:

```bash
curl -X POST "$KALTURA_MESSAGING_URL/message/send" \
  -H "Authorization: Bearer $KALTURA_KS" \
  -H "Content-Type: application/json" \
  -d '{
    "receiverType": "group",
    "groupIds": ["all-employees"],
    "appGuid": "'$APP_GUID'",
    "templateId": "'$TEMPLATE_ID'",
    "type": "email",
    "msgParams": {
      "recipient": {"type": "User", "value": "Message.userId"},
      "eventName": {"type": "String", "value": "Company All-Hands"}
    }
  }'
```

## 6.3 Attachments

Include file attachments with Base64-encoded content:

```json
{
  "attachments": [
    {
      "fileName": "agenda.pdf",
      "content": "JVBERi0xLjQKJcfs...",
      "mimeType": "application/pdf",
      "disposition": "attachment"
    }
  ]
}
```

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `fileName` | string | Yes | Display name of the attachment |
| `content` | string | Yes | Base64-encoded file content |
| `mimeType` | string | Yes | MIME type (e.g., `application/pdf`, `text/calendar`) |
| `disposition` | string | Yes | `"attachment"` or `"inline"` |
| `contentId` | string | No | Content ID for inline images referenced in HTML |


# 7. Message Lifecycle

## 7.1 Bulk Message Status

Each `message/send` call creates a bulk message that progresses through these states:

| Status | Description |
|--------|-------------|
| `sending` | Message is being processed and individual emails are being dispatched |
| `completed` | All individual emails have been processed |
| `failed` | Processing failed (check `errorEnum` and `errorDescription`) |
| `canceled` | Message was canceled before completion |

## 7.2 Discrete Message Status

Each recipient generates a discrete message with its own delivery lifecycle:

| Status | Description |
|--------|-------------|
| `sending` | Email queued for delivery |
| `processed` | Email accepted by the email provider |
| `delivered` | Email delivered to recipient's mailbox |
| `deferred` | Delivery delayed, will retry |
| `dropped` | Email dropped (invalid address, policy violation) |
| `bounce` | Email bounced (mailbox full, domain not found) |
| `error` | Delivery error |

## 7.3 Engagement Tracking Events

After delivery, these tracking events may update the discrete message status:

| Event | Description |
|-------|-------------|
| `open` | Recipient opened the email |
| `click` | Recipient clicked a link in the email |
| `spamreport` | Recipient reported the email as spam |
| `unsubscribed` | Recipient unsubscribed via the email link |

## 7.4 Discrete Error Codes

| Error | Description |
|-------|-------------|
| `emailNotResolvedToValidEmailAddress` | User ID could not be resolved to an email |
| `userUnsubscribeFromThisGroup` | User unsubscribed from the message's unsubscribe group |
| `userNotFoundInOurDb` | User ID not found in the system |
| `createMagicLinkFailed` | Failed to generate a magic login link |
| `createUnsubscribeUriLinkFailed` | Failed to generate an unsubscribe link |
| `createJwtQrCodeFailed` | Failed to generate a QR code |
| `sendGridError` | Email provider returned an error |


# 8. Track Messages

## 8.1 List Bulk Messages

```bash
curl -X POST "$KALTURA_MESSAGING_URL/message/list" \
  -H "Authorization: Bearer $KALTURA_KS" \
  -H "Content-Type: application/json" \
  -d '{
    "filter": {
      "appGuidIn": ["'$APP_GUID'"],
      "statusIn": ["completed"]
    },
    "pager": {"offset": 0, "limit": 25}
  }'
```

### Filter Fields

| Field | Type | Description |
|-------|------|-------------|
| `idIn` | string[] | Filter by bulk message IDs |
| `bulkIdIn` | string[] | Filter by external bulk IDs |
| `templateIdIn` | string[] | Filter by template IDs |
| `appGuidIn` | string[] | Filter by App Registry GUIDs |
| `sessionIn` | string[] | Filter by session labels |
| `statusIn` | string[] | Filter by bulk status (`sending`, `completed`, `failed`) |
| `receiverTypeIn` | string[] | Filter by receiver type (`user`, `group`) |
| `typeIn` | string[] | Filter by message type (`email`) |
| `groupIds` | string[] | Filter by group IDs |
| `userIds` | string[] | Filter by user IDs |
| `createdAtGreaterThanOrEqual` | string | ISO 8601 minimum creation date |
| `createdAtLessThanOrEqual` | string | ISO 8601 maximum creation date |
| `updatedAtGreaterThanOrEqual` | string | ISO 8601 minimum update date |
| `updatedAtLessThanOrEqual` | string | ISO 8601 maximum update date |

**Response:** `{objects: [...], totalCount: N}`

## 8.2 List Messages Grouped by Session

Group bulk messages by their `session` label for campaign-level views:

```bash
curl -X POST "$KALTURA_MESSAGING_URL/message/listGroupedBySession" \
  -H "Authorization: Bearer $KALTURA_KS" \
  -H "Content-Type: application/json" \
  -d '{
    "filter": {
      "appGuidIn": ["'$APP_GUID'"]
    },
    "pager": {"offset": 0, "limit": 25}
  }'
```

### Filter Fields

| Field | Type | Description |
|-------|------|-------------|
| `sessionIn` | string[] | Filter by session labels |
| `templateIdIn` | string[] | Filter by template IDs |
| `appGuidIn` | string[] | Filter by app GUIDs |
| `statusIn` | string[] | Filter by status |
| `adminTags` | string | Filter by admin tags substring |
| `excludeAdminTags` | string | Exclude by admin tags |
| `templateAdminTags` | string[] | Filter by template admin tags |
| `excludeTemplateAdminTags` | string[] | Exclude by template admin tags |
| `createdAtGreaterThanOrEqual` | string | ISO 8601 min date |
| `updatedAtGreaterThanOrEqual` | string | ISO 8601 min date |

## 8.3 Message Statistics

Get delivery statistics for a specific bulk message or session:

```bash
# Stats by bulk ID
curl -X POST "$KALTURA_MESSAGING_URL/message/stats" \
  -H "Authorization: Bearer $KALTURA_KS" \
  -H "Content-Type: application/json" \
  -d "{\"bulkId\": \"$BULK_ID\"}"

# Stats by session
curl -X POST "$KALTURA_MESSAGING_URL/message/stats" \
  -H "Authorization: Bearer $KALTURA_KS" \
  -H "Content-Type: application/json" \
  -d "{\"session\": \"invitation-batch-2025-q4\"}"
```

| Field | Type | Description |
|-------|------|-------------|
| `bulkId` | string | Bulk message external ID |
| `session` | string | Session label |

The response contains uppercase status keys with counts (e.g., `{"DELIVERED": 450, "BOUNCE": 3, "OPEN": 320}`).

## 8.4 Discrete Message Details

Track individual recipient delivery status:

```bash
curl -X POST "$KALTURA_MESSAGING_URL/message/listDiscreteAggregateMessages" \
  -H "Authorization: Bearer $KALTURA_KS" \
  -H "Content-Type: application/json" \
  -d '{
    "filter": {
      "sessionIn": ["invitation-batch-2025-q4"],
      "statusIn": ["bounce", "error"]
    },
    "pager": {"offset": 0, "limit": 50}
  }'
```

### Filter Fields

| Field | Type | Description |
|-------|------|-------------|
| `appGuidIn` | string[] | Filter by app GUIDs |
| `userId` | string | Filter by specific user ID |
| `sessionIn` | string[] | Filter by session labels |
| `statusIn` | string[] | Filter by discrete status |


# 9. Delivery Reports

Generate CSV delivery reports for a bulk message or session:

```
POST /api/v1/report/create
Content-Type: application/json
Authorization: Bearer <KS>
```

```bash
curl -X POST "$KALTURA_MESSAGING_URL/report/create" \
  -H "Authorization: Bearer $KALTURA_KS" \
  -H "Content-Type: application/json" \
  -d "{\"bulkId\": \"$BULK_ID\"}"
```

| Field | Type | Description |
|-------|------|-------------|
| `bulkId` | string | Bulk message external ID |
| `session` | string | Session label |

Provide either `bulkId` or `session` to scope the report.

**Response:** A report object with a download URL for the CSV file. The report generation may be asynchronous; poll the returned report ID if the URL is not immediately available.


# 10. Unsubscribe Management

CAN-SPAM compliant unsubscribe management with group-based opt-out.

## 10.1 List Unsubscribe Groups

List all unsubscribe groups defined across your templates:

```bash
curl -X POST "$KALTURA_MESSAGING_URL/unsubscribe-groups/list" \
  -H "Authorization: Bearer $KALTURA_KS" \
  -H "Content-Type: application/json" \
  -d '{}'
```

Groups are defined in template `unsubscribeGroups` arrays. This endpoint returns all unique groups.

## 10.2 Check User Unsubscribe Status

Get the unsubscribe groups a specific user has opted out of (requires a user-scoped KS):

```bash
curl -X POST "$KALTURA_MESSAGING_URL/unsubscribe-users/userGroupsStatus" \
  -H "Authorization: Bearer $USER_KS" \
  -H "Content-Type: application/json" \
  -d '{}'
```

## 10.3 Sync User Unsubscribe Preferences

Subscribe or unsubscribe a user from specific groups:

```bash
curl -X POST "$KALTURA_MESSAGING_URL/unsubscribe-users/syncGroups" \
  -H "Authorization: Bearer $USER_KS" \
  -H "Content-Type: application/json" \
  -d '{
    "unsubscribed": ["marketing-emails"],
    "subscribed": ["event-updates"]
  }'
```

| Field | Type | Description |
|-------|------|-------------|
| `unsubscribed` | string[] | Groups to unsubscribe from |
| `subscribed` | string[] | Groups to re-subscribe to |

## 10.4 List Unsubscribed Users

List all users who have unsubscribed from groups:

```bash
curl -X POST "$KALTURA_MESSAGING_URL/unsubscribe-users/list" \
  -H "Authorization: Bearer $KALTURA_KS" \
  -H "Content-Type: application/json" \
  -d '{
    "filter": {},
    "pager": {"offset": 0, "limit": 50}
  }'
```

## 10.5 Unsubscribe URI Configuration

Configure custom unsubscribe endpoints for specific applications.

### Add an Unsubscribe URI

```bash
curl -X POST "$KALTURA_MESSAGING_URL/unsubscribe-uri/add" \
  -H "Authorization: Bearer $KALTURA_KS" \
  -H "Content-Type: application/json" \
  -d '{
    "appGuid": "'$APP_GUID'",
    "uri": "https://events.example.com/unsubscribe"
  }'
```

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `appGuid` | string | Yes | App Registry GUID |
| `uri` | string | Yes | Custom unsubscribe endpoint URL |
| `status` | string | No | Defaults to `"enabled"` |

### Get an Unsubscribe URI

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `id` | string | Yes | Unsubscribe URI ID |

```bash
curl -X POST "$KALTURA_MESSAGING_URL/unsubscribe-uri/get" \
  -H "Authorization: Bearer $KALTURA_KS" \
  -H "Content-Type: application/json" \
  -d "{\"id\": \"$URI_ID\"}"
```

**Response:** Full unsubscribe URI object with `id`, `appGuid`, `uri`, `status`, `version`.

### Update an Unsubscribe URI

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `id` | string | Yes | Unsubscribe URI ID to update |
| `uri` | string | No | Updated unsubscribe endpoint URL |
| `status` | string | No | `enabled`, `disabled`, or `deleted` |

```bash
curl -X POST "$KALTURA_MESSAGING_URL/unsubscribe-uri/update" \
  -H "Authorization: Bearer $KALTURA_KS" \
  -H "Content-Type: application/json" \
  -d "{\"id\": \"$URI_ID\", \"uri\": \"https://events.example.com/unsubscribe-v2\"}"
```

**Response:** Updated unsubscribe URI object with incremented `version`.

### Delete an Unsubscribe URI

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `id` | string | Yes | Unsubscribe URI ID to delete |

```bash
curl -X POST "$KALTURA_MESSAGING_URL/unsubscribe-uri/delete" \
  -H "Authorization: Bearer $KALTURA_KS" \
  -H "Content-Type: application/json" \
  -d "{\"id\": \"$URI_ID\"}"
```

Permanently deletes the unsubscribe URI. Subsequent `get` calls return a not-found error.

### List Unsubscribe URIs

```bash
curl -X POST "$KALTURA_MESSAGING_URL/unsubscribe-uri/list" \
  -H "Authorization: Bearer $KALTURA_KS" \
  -H "Content-Type: application/json" \
  -d '{
    "filter": {"appGuidIn": ["'$APP_GUID'"]},
    "pager": {"offset": 0, "limit": 25}
  }'
```

### Filter Fields

| Field | Type | Description |
|-------|------|-------------|
| `idIn` | string[] | Filter by URI IDs |
| `appGuidIn` | string[] | Filter by app GUIDs |
| `uriIn` | string[] | Filter by URI values |
| `status` | string | `enabled`, `disabled`, or `deleted` |
| `createdAtGreaterThanOrEqual` | string | ISO 8601 min date |
| `updatedAtGreaterThanOrEqual` | string | ISO 8601 min date |


# 11. Email Provider Configuration

Configure a custom email service provider (SendGrid) for your account. By default, Kaltura provides a shared email provider. For branded sending domains and dedicated deliverability, configure your own.

## 11.1 Provider Entity

| Field | Type | Description |
|-------|------|-------------|
| `id` | string | Auto-generated identifier (read-only) |
| `partnerId` | integer | Partner ID (read-only) |
| `type` | string | Provider type: `"sendGrid"` |
| `apiKey` | string | SendGrid API key |
| `sendgridWebhookKey` | string | SendGrid webhook verification key |
| `domains` | string[] | Verified sender domains |
| `defaultSender` | string | Default sender email address |
| `unsubscribeClickTracking` | boolean | Enable SendGrid click tracking for unsubscribe links |
| `status` | string | `enabled`, `disabled`, or `deleted` |
| `overrideResidency` | string | Data residency override: `"EU"` or `"GLOBAL"` |
| `version` | integer | Auto-incrementing version (read-only) |
| `createdAt` | string | ISO 8601 timestamp (read-only) |
| `updatedAt` | string | ISO 8601 timestamp (read-only) |

## 11.2 Add a Provider

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `type` | string | Yes | Provider type: `"sendGrid"` |
| `apiKey` | string | Yes | SendGrid API key |
| `sendgridWebhookKey` | string | No | SendGrid webhook verification key |
| `domains` | string[] | No | Verified sender domains |
| `defaultSender` | string | No | Default sender email address |
| `unsubscribeClickTracking` | boolean | No | Enable SendGrid click tracking for unsubscribe links |
| `overrideResidency` | string | No | Data residency override: `"EU"` or `"GLOBAL"` |

**Response:** Full provider object with generated `id`, `version`, and timestamps.

```bash
curl -X POST "$KALTURA_MESSAGING_URL/email-provider/add" \
  -H "Authorization: Bearer $KALTURA_KS" \
  -H "Content-Type: application/json" \
  -d '{
    "type": "sendGrid",
    "apiKey": "SG.your-sendgrid-api-key",
    "sendgridWebhookKey": "your-webhook-verification-key",
    "domains": ["events.example.com"],
    "defaultSender": "events@events.example.com"
  }'
```

## 11.3 List Providers

```bash
curl -X POST "$KALTURA_MESSAGING_URL/email-provider/list" \
  -H "Authorization: Bearer $KALTURA_KS" \
  -H "Content-Type: application/json" \
  -d '{}'
```

## 11.4 Provider Lookup

Resolve which email provider will be used for a given app context.

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `appGuid` | string | No | App Registry GUID to check provider resolution for |

**Response:** The resolved provider object. Resolution order: partner + appGuid, then partner, then default (partner 0).

```bash
curl -X POST "$KALTURA_MESSAGING_URL/email-provider/lookup" \
  -H "Authorization: Bearer $KALTURA_KS" \
  -H "Content-Type: application/json" \
  -d "{\"appGuid\": \"$APP_GUID\"}"
```

The resolution order is: partner + appGuid → partner → default (partner 0).

## 11.5 Assign Provider to App

Assign a specific provider to an app context.

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `id` | string | Yes | Email provider ID |
| `appGuid` | string | Yes | App Registry GUID to assign the provider to |

```bash
curl -X POST "$KALTURA_MESSAGING_URL/email-provider/emailProviderAssignment" \
  -H "Authorization: Bearer $KALTURA_KS" \
  -H "Content-Type: application/json" \
  -d "{
    \"id\": \"$PROVIDER_ID\",
    \"appGuid\": \"$APP_GUID\"
  }"
```

**Response:** EmailProviderAssignmentRule object with `id`, `emailProviderId`, `appGuid`, `version`.

## 11.6 Enable / Disable a Provider

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `id` | string | Yes | Email provider ID |

**Response:** Updated provider object with new status.

```bash
# Enable
curl -X POST "$KALTURA_MESSAGING_URL/email-provider/enable" \
  -H "Authorization: Bearer $KALTURA_KS" \
  -H "Content-Type: application/json" \
  -d "{\"id\": \"$PROVIDER_ID\"}"

# Disable
curl -X POST "$KALTURA_MESSAGING_URL/email-provider/disable" \
  -H "Authorization: Bearer $KALTURA_KS" \
  -H "Content-Type: application/json" \
  -d "{\"id\": \"$PROVIDER_ID\"}"
```

## 11.7 Delete a Provider

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `id` | string | Yes | Email provider ID to delete |

```bash
curl -X POST "$KALTURA_MESSAGING_URL/email-provider/delete" \
  -H "Authorization: Bearer $KALTURA_KS" \
  -H "Content-Type: application/json" \
  -d "{\"id\": \"$PROVIDER_ID\"}"
```


# 12. Domain Configuration

Verify sender domains with your email provider for improved deliverability.

## 12.1 Add a Domain

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `domain` | string | Yes | The sender domain to verify (e.g., `events.example.com`) |
| `subdomain` | string | No | Subdomain prefix for DNS records (e.g., `mail`) |

```bash
curl -X POST "$KALTURA_MESSAGING_URL/domain/add" \
  -H "Authorization: Bearer $KALTURA_KS" \
  -H "Content-Type: application/json" \
  -d '{
    "domain": "events.example.com",
    "subdomain": "mail"
  }'
```

**Response:** Contains the DNS records (CNAME, TXT) to configure for domain verification. Add these records to your DNS configuration before activating.

## 12.2 Activate a Domain

After DNS propagation, activate the domain.

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `domain` | string | Yes | The domain to activate (must match a previously added domain) |
| `subdomain` | string | No | Subdomain prefix (must match the value used in `domain/add`) |

```bash
curl -X POST "$KALTURA_MESSAGING_URL/domain/activate" \
  -H "Authorization: Bearer $KALTURA_KS" \
  -H "Content-Type: application/json" \
  -d '{
    "domain": "events.example.com",
    "subdomain": "mail"
  }'
```

**Response:** Confirmation of domain activation. If DNS records are not yet propagated, the activation fails with an error.


# 13. Error Handling

Validation errors return HTTP 400. Application-level errors follow this structure:

```json
{
  "code": "ERROR_CODE",
  "message": "Description of the error"
}
```

### Bulk Message Error Codes

| Error | Meaning |
|-------|---------|
| `noActiveGroups` | All specified groups are inactive |
| `noActiveGroupUsers` | No active users found in any specified group |
| `someGroupsHaveNoActiveUsers` | Some groups have no active users |

**Retry strategy:** For transient errors (HTTP 5xx, timeouts), retry with exponential backoff: 1s, 2s, 4s, with jitter, up to 3 retries. For client errors (HTTP 400, `noActiveGroups`, `noActiveGroupUsers`, validation errors), fix the request before retrying — these will not resolve on their own. For async operations (message delivery tracking), poll with increasing intervals (5s, 10s, 30s) rather than tight loops.


# 14. Common Integration Patterns

## 14.1 Event Invitation Workflow

Complete flow from virtual event to personalized invitations:

```bash
# Prerequisites
# KALTURA_MESSAGING_URL="https://messaging.nvp1.ovp.kaltura.com/api/v1"
# KALTURA_APP_REGISTRY_URL="https://app-registry.nvp1.ovp.kaltura.com/api/v1"
# KALTURA_KS="<your admin KS>"

# Step 1: Get App GUID for your event
APP_GUID=$(curl -s -X POST "$KALTURA_APP_REGISTRY_URL/app-registry/list" \
  -H "Authorization: Bearer $KALTURA_KS" \
  -H "Content-Type: application/json" \
  -d "{\"filter\": {\"appCustomIdIn\": [\"$VIRTUAL_EVENT_ID\"]}}" \
  | jq -r '.objects[0].id')

# Step 2: Create an invitation template
TEMPLATE_ID=$(curl -s -X POST "$KALTURA_MESSAGING_URL/email-template/add" \
  -H "Authorization: Bearer $KALTURA_KS" \
  -H "Content-Type: application/json" \
  -d "{
    \"appGuid\": \"$APP_GUID\",
    \"name\": \"Event Invitation\",
    \"subject\": \"You're invited: {eventName}\",
    \"body\": \"<p>Hi {recipient.firstName},</p><p>Join us at {eventName}!</p><p><a href='{joinLink}'>Join Event</a></p>\",
    \"toAttributePath\": \"{recipient.email}\",
    \"msgParamsMap\": {
      \"recipient\": {\"type\": \"User\"},
      \"eventName\": {\"type\": \"String\"},
      \"joinLink\": {\"type\": \"MagicLink\"}
    }
  }" | jq -r '.id')

# Step 3: Send invitations
curl -X POST "$KALTURA_MESSAGING_URL/message/send" \
  -H "Authorization: Bearer $KALTURA_KS" \
  -H "Content-Type: application/json" \
  -d "{
    \"receiverType\": \"user\",
    \"userIds\": [\"attendee1@example.com\", \"attendee2@example.com\"],
    \"appGuid\": \"$APP_GUID\",
    \"templateId\": \"$TEMPLATE_ID\",
    \"type\": \"email\",
    \"msgParams\": {
      \"recipient\": {\"type\": \"User\", \"value\": \"Message.userId\"},
      \"eventName\": {\"type\": \"String\", \"value\": \"Annual Conference 2025\"},
      \"joinLink\": {\"type\": \"MagicLink\", \"value\": {\"baseURL\": \"https://events.example.com/join\", \"expiry\": 48, \"privileges\": \"actionslimit:2\"}}
    },
    \"session\": \"conference-2025-invitations\"
  }"
```

## 14.2 Delivery Tracking Dashboard

After sending, monitor delivery and engagement:

```bash
# Get overall delivery stats
curl -X POST "$KALTURA_MESSAGING_URL/message/stats" \
  -H "Authorization: Bearer $KALTURA_KS" \
  -H "Content-Type: application/json" \
  -d '{"session": "conference-2025-invitations"}'

# Find failed deliveries for follow-up
curl -X POST "$KALTURA_MESSAGING_URL/message/listDiscreteAggregateMessages" \
  -H "Authorization: Bearer $KALTURA_KS" \
  -H "Content-Type: application/json" \
  -d '{
    "filter": {
      "sessionIn": ["conference-2025-invitations"],
      "statusIn": ["bounce", "error", "dropped"]
    }
  }'
```

## 14.3 Unsubscribe-Aware Messaging

Set up templates with unsubscribe groups to respect user preferences:

```bash
# Step 1: Create unsubscribe URI for your app
URI_ID=$(curl -s -X POST "$KALTURA_MESSAGING_URL/unsubscribe-uri/add" \
  -H "Authorization: Bearer $KALTURA_KS" \
  -H "Content-Type: application/json" \
  -d "{
    \"appGuid\": \"$APP_GUID\",
    \"uri\": \"https://events.example.com/unsubscribe\"
  }" | jq -r '.id')

# Step 2: Create template with unsubscribe group
curl -X POST "$KALTURA_MESSAGING_URL/email-template/add" \
  -H "Authorization: Bearer $KALTURA_KS" \
  -H "Content-Type: application/json" \
  -d "{
    \"appGuid\": \"$APP_GUID\",
    \"name\": \"Event Updates\",
    \"subject\": \"Update: {eventName}\",
    \"body\": \"<p>{recipient.firstName}, here's an update.</p><p><a href='{unsubLink}'>Unsubscribe</a></p>\",
    \"toAttributePath\": \"{recipient.email}\",
    \"msgParamsMap\": {
      \"recipient\": {\"type\": \"User\"},
      \"eventName\": {\"type\": \"String\"},
      \"unsubLink\": {\"type\": \"UnsubscribeUri\"}
    },
    \"unsubscribeGroups\": [\"event-updates\"]
  }"
```

Users who unsubscribe from the `"event-updates"` group will be automatically excluded from future messages sent with that group.


# 15. Best Practices

- **Use CAN-SPAM compliant unsubscribe groups.** Assign unsubscribe groups to all marketing/event emails and include `{unsubLink}` tokens — users who unsubscribe are automatically excluded from future sends.
- **Use dynamic tokens for personalization.** Leverage `{recipient.*}`, `{magicLink}`, `{qrCodeLink}`, and custom tokens to create engaging, per-recipient emails without manual string substitution.
- **Configure domain authentication.** Set up SPF and DKIM records for your sending domain to maximize deliverability and avoid spam filters.
- **Track delivery stats and follow up on failures.** Use `msg-history/getStats` and `msg-history/getFiltered` to monitor bounce rates, open rates, and re-send to failed recipients.
- **Use AppTokens for production access.** Generate KS via `appToken.startSession` with HMAC — keep admin secrets off application servers.
- **Use the Messaging Service for all email communications.** Prefer the Messaging API over custom SMTP integrations — it provides tracking, analytics, and compliance out of the box.

# 16. Related Guides

- **[Session Guide](KALTURA_SESSION_GUIDE.md)** — KS generation and management
- **[AppTokens API](KALTURA_APPTOKENS_API.md)** — Secure server-to-server auth
- **[App Registry API](KALTURA_APP_REGISTRY_API.md)** — App GUID management (required for templates and messages)
- **[User Profile API](KALTURA_USER_PROFILE_API.md)** — User registration data (triggers messaging workflows)
- **[Events Platform API](KALTURA_EVENTS_PLATFORM_API.md)** — Virtual events (messaging for event communications)
- **[Webhooks API](KALTURA_WEBHOOKS_API.md)** — Event-driven HTTP callbacks; email notifications are delivered via the Messaging Service
- **[User Management API](KALTURA_USER_MANAGEMENT_API.md)** — Manage recipient users and groups for targeted messaging
- **[Analytics Reports](KALTURA_ANALYTICS_REPORTS_API.md)** — `message/stats` for delivery statistics
- **[Gamification](KALTURA_GAMIFICATION_API.md)** — Messaging events can trigger gamification rules

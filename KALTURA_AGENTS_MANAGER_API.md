# Kaltura Agents Manager API Guide

The Agents Manager lets you create **automated content-processing agents** that watch for events on your content and execute actions automatically — captioning new uploads, generating summaries, adding audio descriptions — without any manual steps. An agent is simple: **When** something happens (a trigger) **Do** something about it (actions).

**Base URL:** `https://agents-manager.nvp1.ovp.kaltura.com` (may differ by region/deployment)  
**Auth:** `Authorization: Bearer <YOUR_KS>` header  
**Format:** JSON request/response bodies, all endpoints use POST  

## Prerequisites

- Know how to generate Kaltura Sessions (KS) in your backend (see [Session Guide](KALTURA_SESSION_GUIDE.md))
- Have a Kaltura account with the Agents Manager capability enabled
- Have relevant services (e.g., REACH for captions) provisioned on your account (see [REACH Guide](KALTURA_REACH_API.md))


## Key Benefits

- **Hands-free content processing** — Agents run automatically when content events occur. No manual steps, no delays.
- **Consistent quality at scale** — Every piece of content gets the same treatment, whether you upload 10 videos or 10,000.
- **Immediate results** — Outputs (e.g., captions, summaries) are applied directly to the entry. No draft to review and publish.
- **On-demand flexibility** — Run agents on demand for specific content, or let them trigger automatically on every new upload.
- **Full visibility** — Track every execution with a unique trace ID. Query status at any time.


## Core Concepts

An agent is composed of three objects:

| Concept | What It Is |
|---|---|
| **Agent** | The top-level object that ties a trigger to actions. Has a name, description, and can be enabled or disabled. |
| **Trigger** | Defines **when** the agent runs — on a content event or on demand. Identified by a `systemName`. |
| **Actions** | Defines **what** the agent does when triggered — a workflow containing one or more action steps. |
| **Action Definitions** | The catalog of available action types for your account (e.g., captions, audio description). Each provides vendor/language combinations with `catalogItemId` values you reference when building your actions payload. |


## Available Triggers

Triggers are identified by `systemName`:

| systemName | Description |
|---|---|
| **ENTRY_READY** | Fires when a new entry finishes processing and is ready for playback. Ideal for post-upload automation. |
| **ENTRY_UPDATED** | Fires when an entry's content or metadata changes. Useful for re-processing after edits. |
| **ENTRY_ADDED_TO_CATEGORY** | Fires when an entry is assigned to a category. Enables category-specific workflows. |
| **RUN_ON_DEMAND** | Trigger an agent manually via the API on specific content, without waiting for an event. |


## Available Actions

Action types are listed dynamically via the Action Definitions API. Available actions depend on your account configuration and which services are provisioned. Examples include:

| Action Type | What It Does | Backed By |
|---|---|---|
| **captions** | Generates machine-powered captions in a specified language and applies them to the entry | REACH |
| **translation** | Translates captions or metadata into additional languages | REACH |
| **dubbing** | Generates dubbed audio tracks in target languages | REACH |
| **summary** | Generates an AI summary and applies it to the entry metadata | REACH |
| **metadata_enrichment** | Enriches entry metadata using AI (tags, keywords) | REACH |
| **moderation** | Applies content moderation | REACH |
| **publish_entry** | Publishes the entry to specified destinations | Native |

Most agent actions are powered by **Kaltura REACH** services. The `catalogItemId` values in the action definitions map directly to REACH vendor catalog items. See [REACH coverage](#kaltura-reach--the-services-behind-agent-actions) below for which services are available as agent actions vs. direct REACH API calls.

The actions available to your agents depend on which services are enabled on your Kaltura account. Your account's full catalog of available action types — including any services added after this guide was written — can always be retrieved at runtime by calling the **Action Definitions API** (see [Step 1](#1-discover-available-action-types) below). This ensures your integration automatically discovers new action types as they become available, without code changes.


# 1. Discover Available Action Types

Retrieve the catalog of actions available for your account. The response includes vendor information, supported languages, and `catalogItemId` values needed to build your actions payload.

**POST** `/api/v1/actionDefinition/list`

```json
{
  "partnerId": "12345"
}
```

**Response** — Each action definition includes its `type`, `tags`, and for actions backed by REACH services, a nested `vendors` array with per-language `catalogItemId` values and associated `reachProfiles`:

```json
{
  "totalCount": 7,
  "objects": [
    {
      "objectType": "ActionDefinition",
      "type": "captions",
      "tags": ["captions", "accessibility"],
      "vendors": [
        {
          "name": "Kaltura",
          "languages": [
            {
              "language": "English",
              "catalogItemId": 27762
            },
            {
              "language": "Spanish",
              "catalogItemId": 27801
            }
          ]
        }
      ],
      "reachProfiles": [
        {
          "id": 261,
          "name": "My-REACH-Profile"
        }
      ]
    },
    {
      "objectType": "ActionDefinition",
      "type": "summary",
      "tags": ["summary", "ai"]
    }
  ]
}
```

**Key points:**
- The `catalogItemId` inside `vendors[].languages[]` maps directly to a REACH vendor catalog item. See [KALTURA_REACH_API.md](KALTURA_REACH_API.md) for details.
- The `reachProfiles[].id` is needed when creating actions (the `reach_profile_id` field).
- Not all action types have vendors/languages (e.g., `summary`, `publish_entry` may have different structures).


# 2. Create a Trigger

Define when your agent should run. Triggers use a `systemName` to identify the event type.

**POST** `/api/v1/trigger/create`

```json
{
  "partnerId": "12345",
  "systemName": "ENTRY_READY",
  "triggerParameters": {}
}
```

- `systemName` — One of the available trigger types (see [Available Triggers](#available-triggers)).
- `triggerParameters` — Additional parameters for the trigger (e.g., category filters). Use `{}` for default behavior.

**Response** — The created trigger includes auto-generated `executionParameters`:

```json
{
  "id": "abc123def456",
  "partnerId": "12345",
  "status": "Enabled",
  "systemName": "ENTRY_READY",
  "executionParameters": { ... },
  "triggerParameters": {}
}
```


# 3. Create Actions

Define what your agent should do. Actions reference a `workflowId` and contain one or more `workflowActions`, each specifying a REACH profile, action type, and catalog item.

**POST** `/api/v1/actions/create`

```json
{
  "partnerId": "12345",
  "workflowId": "publishing_workflow_dag",
  "workflowActions": [
    {
      "reach_profile_id": 261,
      "type": "captions",
      "catalog_item_id": 27762
    }
  ]
}
```

- `workflowId` — The workflow template to use. Use `"publishing_workflow_dag"` for standard content processing workflows.
- `workflowActions` — Array of actions to perform. Each requires:
  - `reach_profile_id` — From the action definitions response (`reachProfiles[].id`).
  - `type` — The action type string (e.g., `"captions"`, `"summary"`).
  - `catalog_item_id` — From the action definitions response (`vendors[].languages[].catalogItemId`).

**Response**

```json
{
  "id": "xyz789abc012",
  "partnerId": "12345",
  "status": "Enabled",
  "workflowId": "publishing_workflow_dag",
  "workflowActions": [
    {
      "reach_profile_id": 261,
      "type": "captions",
      "catalog_item_id": 27762
    }
  ]
}
```


# 4. Create an Agent

Tie the trigger and actions together into an agent.

**POST** `/api/v1/agent/create`

```json
{
  "partnerId": "12345",
  "name": "Auto-Caption All New Videos",
  "description": "Generates English captions on every new entry",
  "triggerId": "abc123def456",
  "actionsId": "xyz789abc012",
  "status": "Enabled"
}
```

Enable the trigger and actions first, then set the agent status to `"Enabled"`. If you need to create the agent before its dependencies are ready, set status to `"Disabled"` and enable it after enabling the trigger and actions.

**Response** — Agent create returns the full agent with **inline** trigger and actions objects:

```json
{
  "id": "agent_001",
  "partnerId": "12345",
  "name": "Auto-Caption All New Videos",
  "description": "Generates English captions on every new entry",
  "status": "Enabled",
  "trigger": {
    "id": "abc123def456",
    "systemName": "ENTRY_READY",
    "status": "Enabled"
  },
  "actions": {
    "id": "xyz789abc012",
    "workflowId": "publishing_workflow_dag",
    "status": "Enabled",
    "workflowActions": [...]
  }
}
```

Note: The create response includes full inline `trigger` and `actions` objects. The list endpoint returns only `triggerId` and `actionsId` as string references (see below).


# 5. List Agents

Retrieve all agents configured for your account.

**POST** `/api/v1/agent/list`

```json
{
  "partnerId": "12345"
}
```

**Response** — The list endpoint returns `triggerId` and `actionsId` as string IDs (not inline objects):

```json
{
  "totalCount": 1,
  "objects": [
    {
      "id": "agent_001",
      "partnerId": "12345",
      "name": "Auto-Caption All New Videos",
      "status": "Enabled",
      "triggerId": "abc123def456",
      "actionsId": "xyz789abc012"
    }
  ]
}
```


# 6. Delete Resources

Each resource type has its own delete endpoint. **Triggers and actions must be deleted explicitly** — they are not automatically removed when an agent is deleted.

Delete the agent first, then its trigger and actions:

**POST** `/api/v1/agent/delete`
```json
{ "id": "agent_001" }
```

**POST** `/api/v1/trigger/delete`
```json
{ "id": "abc123def456" }
```

**POST** `/api/v1/actions/delete`
```json
{ "id": "xyz789abc012" }
```

Each delete returns the object with `"status": "Deleted"`.


# 7. Execution Tracking

Every agent execution is tracked and queryable:

- Each execution receives a unique **execution ID**.
- Query execution status to check whether a run is in progress, succeeded, or failed.
- All executions carry an end-to-end **trace ID** for debugging and audit purposes.


## Full Example: Auto-Caption Every New Video

```
Step 1:  Discover available actions
         POST /api/v1/actionDefinition/list
         → Find catalogItemId and reachProfileId for "captions" + "English"

Step 2:  Create a trigger
         POST /api/v1/trigger/create
         → systemName: "ENTRY_READY"
         → Returns trigger ID

Step 3:  Create actions
         POST /api/v1/actions/create
         → workflowId: "publishing_workflow_dag"
         → workflowActions with reach_profile_id, type, catalog_item_id
         → Returns actions ID

Step 4:  Create the agent
         POST /api/v1/agent/create
         → name: "Auto-Caption All New Videos"
         → Link triggerId + actionsId
         → status: "Enabled"

Done.    Every new video that finishes processing will
         automatically get English captions applied.
```

### curl Example

Set up your environment variables first:

```bash
export KALTURA_BASE_URL="https://agents-manager.nvp1.ovp.kaltura.com"
export KALTURA_PARTNER_ID="12345"
export KALTURA_KS="YOUR_KS"  # see KALTURA_SESSION_GUIDE.md
```

**1. List action definitions** — find the `catalogItemId` and `reachProfileId` for English captions:

```bash
curl -X POST "$KALTURA_BASE_URL/api/v1/actionDefinition/list" \
  -H "Authorization: Bearer $KALTURA_KS" \
  -H "Content-Type: application/json" \
  -d "{\"partnerId\": \"$KALTURA_PARTNER_ID\"}"
```

From the response, locate the `captions` action definition and note the `catalogItemId` for English (e.g., `27762`) and the `reachProfiles[].id` (e.g., `261`).

**2. Create a trigger** — fires on every new entry ready:

```bash
curl -X POST "$KALTURA_BASE_URL/api/v1/trigger/create" \
  -H "Authorization: Bearer $KALTURA_KS" \
  -H "Content-Type: application/json" \
  -d "{\"partnerId\": \"$KALTURA_PARTNER_ID\", \"systemName\": \"ENTRY_READY\", \"triggerParameters\": {}}"
```

Note the `id` from the response (e.g., `abc123def456`).

**3. Create actions** — generate English captions using the values from step 1:

```bash
curl -X POST "$KALTURA_BASE_URL/api/v1/actions/create" \
  -H "Authorization: Bearer $KALTURA_KS" \
  -H "Content-Type: application/json" \
  -d "{\"partnerId\": \"$KALTURA_PARTNER_ID\", \"workflowId\": \"publishing_workflow_dag\", \"workflowActions\": [{\"reach_profile_id\": 261, \"type\": \"captions\", \"catalog_item_id\": 27762}]}"
```

Note the `id` from the response (e.g., `xyz789abc012`).

**4. Create and enable the agent** — link the trigger and actions:

```bash
curl -X POST "$KALTURA_BASE_URL/api/v1/agent/create" \
  -H "Authorization: Bearer $KALTURA_KS" \
  -H "Content-Type: application/json" \
  -d "{\"partnerId\": \"$KALTURA_PARTNER_ID\", \"name\": \"Auto-Caption All New Videos\", \"description\": \"English captions on every new entry\", \"triggerId\": \"abc123def456\", \"actionsId\": \"xyz789abc012\", \"status\": \"Enabled\"}"
```

The response includes the full agent object with inline trigger and actions.


## Lifecycle Behavior

| What You Do | What Happens |
|---|---|
| **Disable** an agent | The agent stops firing — no new executions will start |
| **Re-enable** an agent | Processing resumes for new matching events |
| **Delete** an agent | The agent is removed. **Trigger and actions must be deleted separately.** |


## Kaltura REACH — The Services Behind Agent Actions

Many of the actions available to agents — captions, dubbing, translations, and content enrichment — are powered by **Kaltura REACH**, Kaltura's captioning and media enrichment services framework.

When you call the Action Definitions API, the `catalogItemId` values returned for actions like `captions` and `translation` map directly to REACH vendor catalog items. Each defines the vendor, quality tier (machine vs. human), language, and turnaround time.

Your Kaltura account must have REACH services provisioned for those action types to appear in the action definitions catalog. Contact your Kaltura account manager to enable or configure REACH services.

The Agents Manager supports these REACH services as action types: **captions, translation, dubbing, summary, moderation, and metadata enrichment**. For **AI Clips** (`serviceFeature=10`), **Quiz** (`serviceFeature=12`), and other REACH services, use the REACH API directly via `entryVendorTask.add` (see the [REACH guide](KALTURA_REACH_API.md)).

| REACH Service | How to Use |
|---|---|
| Captions (1) | Agent action: `"captions"` |
| Translation (2) | Agent action: `"translation"` |
| Dubbing (7) | Agent action: `"dubbing"` |
| Summary (13) | Agent action: `"summary"` |
| Moderation (15) | Agent action: `"moderation"` |
| Metadata Enrichment (16) | Agent action: `"metadata_enrichment"` |
| Clips (10) | [REACH API](KALTURA_REACH_API.md#ai-clips-workflow-content-lab) via `entryVendorTask.add` |
| Quiz (12) | [REACH API](KALTURA_REACH_API.md) via `entryVendorTask.add` |
| Live Caption (8) | [REACH API](KALTURA_REACH_API.md) via `entryVendorTask.add` |
| Live Translation (11) | [REACH API](KALTURA_REACH_API.md) via `entryVendorTask.add` |
| Video Analysis (14) | [REACH API](KALTURA_REACH_API.md) via `entryVendorTask.add` |

Always call `actionDefinition/list` at runtime to get the current list of supported action types for your account, as new action types may be added over time.

For the complete REACH API reference — including all available services, how to order tasks directly, enum values, and code examples — see **[KALTURA_REACH_API.md](KALTURA_REACH_API.md)**.


## Managing Agents via UI

In addition to the API, agents can be configured through Kaltura's management interfaces:

- **KMC (Kaltura Management Console)** — Full agent management for administrators.
- **KMS (Kaltura MediaSpace)** — Agent configuration within the end-user portal.
- **Custom applications** — Embed the agent management UI into your own applications using Kaltura's Unisphere framework, which provides embeddable components for Kaltura functionality.


## Scope

- **Triggers** fire on events (`ENTRY_READY`, `ENTRY_UPDATED`, `ENTRY_ADDED_TO_CATEGORY`) or on demand (`RUN_ON_DEMAND`).
- **Supported action types:** captions, translation, dubbing, summary, moderation, metadata enrichment. For AI Clips, Quiz, Live Captions, and Video Analysis, use the [REACH API](KALTURA_REACH_API.md) directly. Call `actionDefinition/list` to discover available action types for your account.


# 8. Error Handling

| Error Code / Status | Meaning | Resolution |
|---------------------|---------|------------|
| `401 Unauthorized` | Invalid or expired KS | Generate a fresh admin KS with Bearer auth |
| `404 Not Found` | Agent, trigger, or action ID does not exist | Verify the resource ID; it may have been deleted |
| `400 Bad Request` | Missing required field or invalid payload | Check the request body against the schema — `objectType`, `triggers`, `actions` are required |
| Execution status `FAILED` | Agent action failed during processing | Check execution history via `execution/list` — common causes: invalid entry, insufficient REACH credit, unsupported language |
| Execution status `PARTIAL` | Some actions succeeded, others failed | Review individual action results in the execution response |

**Retry strategy:** For transient errors (HTTP 5xx, timeouts), retry with exponential backoff: 1s, 2s, 4s, with jitter, up to 3 retries. For client errors (`401 Unauthorized`, `400 Bad Request`, `404 Not Found`), fix the request before retrying — these will not resolve on their own. For async operations (agent executions), poll with increasing intervals (5s, 10s, 30s) rather than tight loops.

# 9. Best Practices

- **Use specific triggers.** Prefer `ENTRY_READY` (fires once when transcoding completes) over `ENTRY_ADDED` (fires before content is playable).
- **Filter triggers by category.** Use `categoryIds` in trigger configuration to limit which entries an agent processes — avoids processing test or draft content.
- **Use REACH automation rules for simple single-action workflows** (e.g., "caption every new video"). Use Agents Manager for multi-step workflows (e.g., "caption, then translate to 3 languages, then generate summary").
- **Monitor execution history.** Poll `execution/list` to verify agents are firing and completing successfully.
- **Use AppTokens for production.** Create a scoped AppToken for your agent automation service rather than using raw admin secrets.
- **Set up one agent per workflow.** Separate agents for different processing pipelines (captioning, translation, moderation) makes debugging easier.

# 10. Related Guides

- **[Agents Widget](KALTURA_AGENTS_WIDGET_API.md)** — Embeddable UI for managing agents via a Unisphere drawer panel — the visual counterpart to this server-side API  
- **[Session Guide](KALTURA_SESSION_GUIDE.md)** — Generate the KS needed for Bearer auth
- **[AppTokens](KALTURA_APPTOKENS_API.md)** — Secure server-to-server auth for agent automation services
- **[REACH](KALTURA_REACH_API.md)** — The AI services (captions, translation, clips) that power agent actions
- **[Upload & Delivery](KALTURA_UPLOAD_AND_DELIVERY_API.md)** — Upload content that triggers agent processing
- **[AI Genie](KALTURA_AI_GENIE_API.md)** — Conversational AI search over content processed by agents
- **[eSearch](KALTURA_ESEARCH_API.md)** — Search entries to find content for agent processing
- **[Webhooks](KALTURA_WEBHOOKS_API.md)** — HTTP callbacks for agent execution events
- **[Categories & Access Control API](KALTURA_CATEGORIES_AND_ACCESS_CONTROL_API.md)** — Category-based agent triggers (filter agents to fire only for entries in specific categories)
- **[Events Platform](KALTURA_EVENTS_PLATFORM_API.md)** — Agent triggers can respond to event lifecycle changes
- **[Custom Metadata](KALTURA_CUSTOM_METADATA_API.md)** — Agent actions can update custom metadata fields

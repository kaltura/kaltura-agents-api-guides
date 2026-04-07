# Kaltura AI Genie API Guide

Kaltura AI Genie provides conversational AI search and generative answers over your video content library using RAG (Retrieval-Augmented Generation).

**Base URL:** `https://genie.nvp1.ovp.kaltura.com` (may differ by region/deployment)
**Auth:** `Authorization: KS <YOUR_KS>` header
**Format:** JSON request/response bodies, all endpoints use POST

## Prerequisites

This guide assumes you already:
- Know how to generate Kaltura Sessions (KS) in your backend, setting privileges.   
- Have a Kaltura account setup with an AI Genie configured.   
- Know how to use the Kaltura Player embeds.

Genie streams **structured generative answers** (flashcards, follow-ups, sources) plus “thinking/tool” status events. 

## Environments, Auth & Headers

**Base URL** (may differ based on your account region/deployment)
- `https://genie.nvp1.ovp.kaltura.com`

**Auth header**
```
Authorization: KS <YOUR_KS>
```

## Minimum KS Privileges (tune to your account)

```
setrole:PLAYBACK_BASE_ROLE,
sview:*,
enableentitlement,
privacycontext:<GENIE_ENABLED_CATEGORY_PRIVACY_CONTEXT>,
appid:<APP_NAME-APP_DOMAIN>,
sessionid:<GUID>,
genieid:default
```

Notes:

- `sview:*` - lets Genie return playable clips; your **entitlements** still gate access per user and privacy context.
- `privacycontext` - should match the category privacy context Genie indexes for your account.

## 1. Stateless RAG Search (no session, quick hits)

**POST** `/mcp/search`

**Parameters**
- **query** *(string, required)* – natural-language question or keywords.
- **include_sources** *(bool, optional, default: false)* – when `true`, returns source entries with entry IDs, timestamps, and per-entry text segments (see response shapes below).

### Text-only response (`include_sources: false` or omitted)

```json
// Request
{
  “query”: “how to create an interactive video?”,
  “include_sources”: false
}

// Response
{
  “status”: “success”,
  “data”: {
    “text”: “<stitched transcript segments text>”
  }
}
```

Returns **stitched plain text** from the most relevant media transcripts. Expect some repetition if multiple hits overlap; the service prioritizes recall over de-duplication.

### Response with sources (`include_sources: true`)

```json
// Request
{
  “query”: “how to create an interactive video?”,
  “include_sources”: true
}

// Response
{
  “status”: “success”,
  “data”: {
    “chapters”: [
      {
        “entry_id”: “1_abc12345”,
        “text”: “<transcript segment text>”,
        “start_time”: 5,
        “end_time”: 260
      },
      {
        “entry_id”: “1_def67890”,
        “text”: “<transcript segment text>”,
        “start_time”: 10,
        “end_time”: 425
      }
    ]
  }
}
```

Each chapter includes:
- **entry_id** — the Kaltura media entry that matched.
- **text** — the relevant transcript segment from that entry.
- **start_time** / **end_time** — time range in seconds within the entry.

Use these to deep-link into playback at the relevant point: `loadMedia({ entryId }, { startTime, clipTo })`.


## 2. Conversational Answers — **Streaming**

```bash
POST /assistant/converse
Content-Type: application/json
Accept: 
  - if sse=true  → text/event-stream (SSE-like NDJSON lines prefixed by `data:`)
  - else         → application/x-ndjson (pure NDJSON lines)
```

**Request body**

```json
{
  "userMessage": "<question>",
  "sse": true,
  "model_type": "fast",
  "threadId": "<optional — UUID from a previous response for multi-turn>",
  "force_experience": "flashcards"
}
```

**Parameters**

| Parameter | Type | Required | Description |
|---|---|---|---|
| `userMessage` | string | Yes | The user’s question or message. |
| `sse` | bool | Yes | `true` for SSE (`text/event-stream`), `false` for NDJSON (`application/x-ndjson`). |
| `model_type` | string | No | Controls the speed/depth trade-off. `"fast"` for quick answers, `"smart"` for deeper research-quality answers (takes longer). |
| `threadId` | string (UUID) | No | Pass the `threadId` from a previous response to continue a multi-turn conversation. The assistant retains context from earlier messages in the same thread. |
| `force_experience` | string | No | Force a specific output format. Known value: `"flashcards"` — ensures the response includes flashcard-style structured output. |

**Response metadata**

The **first event** in the stream (typically a `think` event) includes:
- **`threadId`** — UUID identifying this conversation thread. Store this to send follow-up messages.
- **`messageId`** — UUID identifying this specific response within the thread.

```json
{
  "role": "assistant",
  "type": "think",
  "content": "preparing to answer...",
  "segmentNumber": 1,
  "et": 0.025,
  "threadId": "ca0cb7ca-5fcf-4b75-860b-c48b8893883c",
  "messageId": "e755800ea80648a49213bb8f7c2fbb01",
  "segmentStart": true
}
```

**Content negotiation**
- **SSE** (recommended for live UIs): `Accept: text/event-stream` and body `{ "sse": true }`
- **NDJSON** (non-SSE clients): `Accept: application/x-ndjson` and body `{ "sse": false }`

**Segment types you’ll see in the streaming response**

The SSE/NDJSON emits one JSON object per line (SSE lines are prefixed with `data:`). The reference table below break down the events' **type** your stream can emit, plus the `unisphere-tool` subtypes.

**Stream event types (top-level `type`)**

| **Type** | **What it is** | **Content shape** (`content`) | **Key fields** (besides `content`) | **Primary use-cases in UI** | **Aggregation rules** | **Notes** |
|---|---|---|---|---|---|---|
| `think` | Model status / narration of internal progress. | Short status text (may be empty on the final line). | `segmentNumber`, `segmentStart?`, `isFinal?`, `et` | Show a transient “Preparing... / Thinking...” status/loading. | Independent lines. | Don’t persist; No need to log. Final packet will be `isFinal:true` with empty content. |
| `tool` | Declares a tool call the assistant is invoking. | One-line trace, e.g., `get_experience_instructions {"name":"flashcards"}`. | `segmentNumber`, `segmentStart?`, `et` | Brief “Using tool ...” chip while running. | Independent lines. | Internal telemetry; hide in UX / logs. |
| `tool_response` | The tool’s completion notification. | One-line result summary, e.g., `... responded with size 1715`. | `segmentNumber`, `segmentStart?`, `et` | Response to the “tool” call. | Independent lines. | Internal telemetry; hide in UX / logs. |
| `unisphere-tool` | **Payload stream** from a runtime widget. Use `metadata.runtimeName` to route. | Multi-line, **YAML/Markdown-like** text. | `segmentNumber`, `segmentStart`, `segmentEnd`, `metadata:{widgetName,runtimeName}`, `et` | Render structured results (flashcards/clips, follow-ups, sources, etc.). | **Concatenate all `content` for the same `segmentNumber` from `segmentStart`→`segmentEnd`**, then parse. | Multiple segments of this type can arrive (one per runtime). |
| `text` | The assistant’s **freeform answer** (markdown fragments). | Free text; may arrive in multiple chunks. | `segmentNumber`, `segmentStart?`, `et` | Show as the “Answer” section; append chunks as they arrive. | Concatenate in order of arrival. | Keep whitespace/newlines; post-process as needed. |
| `thread` | Thread metadata (e.g., a generated **title**). | Short YAML-ish lines, e.g., `title: "..."` | `segmentNumber`, `segmentStart`, `segmentEnd`, `et` | Update conversation title/breadcrumbs when `segmentEnd` lands. | Concatenate from `segmentStart`→`segmentEnd`, then parse key:values. | Typically one per response. |
| `share` | Share/bookmark metadata for the response. | Metadata payload. | `segmentNumber`, `et` | Enable share/bookmark UI actions. | Independent lines. | May appear alongside other event types. |

**Common fields across events:**  
`role:"assistant"`, `type`, `segmentNumber` (grouping key), `segmentStart`/`segmentEnd` (chunk boundaries), `et` (elapsed time hint), `metadata` (only on some types).

**The `unisphere-tool` runtimes (use `metadata.runtimeName`)**

| **runtimeName** | **What you get** | **How the `content` looks** | **Parse into** | **Typical UI** | **Primary actions** |
|---|---|---|---|---|---|
| `flashcards-tool` | The flashcards + citations to clips. | YAML/Markdown-like block containing a top-level `title`, `summary`, then `keypoints` (each with `title` / `summary`) and `citation.clips` lists. Each clip has `entry_id`, `start_time`, `end_time` (plus indexes/types). | **Hero**: `{title, summary}`; **Clips**: array of `{title, summary, entryId, start, end}` (map keys & normalize). | Card stack + **Clips** panel. | Bind **Play** to Kaltura Player: `loadMedia({ entryId }, { startTime, clipTo })`. |
| `followups-tool` | **Suggested next questions**. | Lines like: `questions:\n- How do I ...?\n- What types of ...?` | `string[]` follow-ups. | Clickable list (“Follow-ups”). | Clicking a follow-up re-asks the question via the `converse` call. |
| `sources-tool` | **Reference sources** used. | YAML list like: `- title: ...\n  entry_id: 1_abc...\n  type: video\n  duration: 104` | Array of `{title, entryId, type, duration?}`. | “Sources” list with **entry_id** visible. | Deep-link to video at `start_time` or make assets downloadable when available. | 

**Minimal client algorithm**

1. POST; open streamed body; iterate lines starting with `data:`.  
2. `JSON.parse(line.slice(5))`.  
3. Route by `type`:  
   - `text` → append.  
   - `thread`/`unisphere-tool` → buffer by `segmentNumber`; on `segmentEnd` parse once.  
4. From `flashcards-tool`: render hero + clips; de-dupe clips by `entryId:start:end`.  

**Resilience and parsing guardrails**
- `content` is YAML/markdown-ish and **arrives in small chunks, even mid-word**. Buffer until `segmentEnd` for any structured block. Collect all chunks for a segment, normalize whitespace/quotes, then extract fields.
- **`metadata.runtimeName`** is set on the `segmentStart` event but **may be absent on subsequent content chunks** for the same segment. Track `segmentNumber → runtimeName` from the start event and use that mapping when routing later chunks.
- Anchor on stable keys: `title:`, `summary:`, `citation:`, `clips:`, `entry_id`, `start_time`, `end_time`.  
- Normalize `\r`, smart quotes, and repeated whitespace before pattern matching.  
- Keep a `segmentNumber → {kind, buffer}` map; clear on `segmentEnd`.  
- De-dup clips by composite key `entryId:start:end`.  

**Parsing `flashcards-tool`(YAML-like)**

The `flashcards-tool` text looks like:

```
title: Kaltura Genie
summary: ...
keypoints:
- title: How to Access Genie
  summary: ...
  citation:
    clips:
    - entry_id: 1_umwrb2y9
      start_time: 11
      end_time: 25
```

A parser should:

- Read the **top** `title`/`summary` into a “hero” block.
- For each `keypoint`, attach its `title`/`summary` to the clips under `citation → clips`.
- Extract **entry_id**, **start_time**, **end_time** and de-dupe clips.

## 3. Smart Search Sessions — Polling (SSE alternative)

Use this when your client polls rather than holding an SSE stream. You open a session, then poll every N seconds until the final payload is ready. If your deployment returns 404 on these endpoints, use `/assistant/converse` (streaming) or `/mcp/search` (stateless).

### Flow

**Step 1: Start a session**

```
POST /kmedia/start-smart-search-session
Authorization: KS <KS>
Content-Type: application/json

{ "schemaVersion": 1, "data": { "question": "<user question>" } }
```

**Response**
```json
{
  "data": { "sessionId": "<SID>", "timestamp": 1712345678 }
}
```

**Step 2: Poll every X seconds** (send your latest seen `timestamp`)

```
POST /kmedia/get-smart-search-session
Authorization: KS <KS>
Content-Type: application/json

{ "schemaVersion": 1, "data": { "sessionId": "<SID>", "timestamp": <latestTimestamp> } }
```

**Stop when**
- `data.isFinal === true` → render results and stop
- you hit your timeout window (typically 20–30s), or the user cancels
- you get **401/403** (KS expired/no-permissions) → refresh KS and restart

> Always pass the **most recent** `timestamp` you received.  
> Polling responses are cached per session; subsequent polls typically return faster.  

### Response data

**Final response:**   

```json
{
  "data": {
    "version": 1,
    "threadId": "...",
    "messageId": "...",
    "question": "...",
    "elements": [
      { "type": "flashcards", "version": 1, "cards": [ /* … */ ] },
      { "type": "followups",  "version": 1, "followups": [ "…" ] },
      { "type": "sources",    "version": 1, "sources": [ /* … */ ] },
      { "type": "text",       "version": 1, "text": "…" }        // optional
    ],
    "isFinal": true
  },
  "timestamp": 1712345690
}
```

Unlike streaming, polling returns **one final bundle** under `data.elements` — no incremental “think/tool” events.

- **`flashcards`:**  
  - `cards[]` each has `title`, `description`, optional `subTitle`.  
  - Clip references may appear in **either**:
    - `cards[].videos[]` with `entryId`, `startTime`, `endTime`, or 
    - `cards[].chapters[]` with `entry_id`, `start_time`, `end_time`.   
  - The **first card’s** `title/description` are good “hero” text.   
  - If there is no standalone text element, you can synthesize an answer by joining `cards[].description`.  
- **`followups`** → `followups: string[]` (sometimes named `questions` in other payloads).  
- **`sources`** → list of `{ title, type, entryId, duration? }` for display or deep linking.  
- **`isFinal`** → `true` when the bundle is complete. Stop polling.  

### Error handling

- **401/403** → refresh KS (expired or missing privileges), then start a new session.  
- **5xx / network** → try adding a backoff to poll less frequently.  
- **Timeout** (no `isFinal` by your deadline) → try to restart the session with the same query.  


## Thumbnails for Source Entries

When displaying source entries or flashcard clips, fetch thumbnails from the Kaltura thumbnail API:

```
# Standard thumbnail (scaled to width)
https://www.kaltura.com/p/{partnerId}/thumbnail/entry_id/{entryId}/width/768

# Time-specific thumbnail (frame at a specific second)
https://www.kaltura.com/p/{partnerId}/thumbnail/entry_id/{entryId}/vid_sec/{seconds}/width/768
```

Use `vid_sec` to show a frame from the clip's `start_time` — this gives users a visual preview of the referenced moment.


## curl Examples

### Stateless RAG Search (`/mcp/search`)

```bash
curl -X POST "$GENIE_URL/mcp/search" \
  -H "Authorization: KS $KS" \
  -H "Content-Type: application/json" \
  -d '{
    "query": "how to create an interactive video?",
    "include_sources": true
  }'
```

### Streaming Conversation (`/assistant/converse`) with SSE

The `-N` flag disables output buffering so you see SSE events as they arrive:

```bash
curl -N -X POST "$GENIE_URL/assistant/converse" \
  -H "Authorization: KS $KS" \
  -H "Content-Type: application/json" \
  -d '{
    "userMessage": "What are the key features?",
    "sse": true,
    "model_type": "fast"
  }'
```

Each line in the response is prefixed with `data:` and contains a JSON object. Route by the `type` field (`text`, `unisphere-tool`, `thread`, etc.) as described in the streaming event tables above. The first event includes a `threadId` you can store for multi-turn follow-ups.

### Multi-turn Follow-up

Pass the `threadId` returned from a previous response to continue the conversation with full context:

```bash
curl -N -X POST "$GENIE_URL/assistant/converse" \
  -H "Authorization: KS $KS" \
  -H "Content-Type: application/json" \
  -d '{
    "userMessage": "Can you go deeper on the second point?",
    "sse": true,
    "model_type": "fast",
    "threadId": "<THREAD_ID_FROM_PREVIOUS_RESPONSE>"
  }'
```

The assistant remembers all prior messages in the thread and will answer in context. Parse the stream the same way as above.


## Related Guides

- **[Session Guide](KALTURA_SESSION_GUIDE.md)** — Generate the KS required for Genie auth (`KS` header)
- **[AppTokens](KALTURA_APPTOKENS_API.md)** — Secure KS generation for production Genie integrations
- **[eSearch](KALTURA_ESEARCH_API.md)** — Structured search (Genie uses this internally for RAG; use eSearch when you need precise filters)
- **[REACH](KALTURA_REACH_API.md)** — Enrich content with captions/transcripts that Genie indexes for better answers
- **[Upload & Delivery](KALTURA_UPLOAD_AND_DELIVERY_API.md)** — Upload content that becomes searchable via Genie
- **[Agents Manager](KALTURA_AGENTS_MANAGER_API.md)** — Automate content enrichment to improve Genie's knowledge base


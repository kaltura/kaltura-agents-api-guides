# Kaltura AI Genie API Guide

Kaltura AI Genie provides conversational AI search and generative answers over your video content library using RAG (Retrieval-Augmented Generation).

**Base URL:** `https://genie.nvp1.ovp.kaltura.com` (may differ by region/deployment)  
**Auth:** `Authorization: KS <YOUR_KS>` header  
**Format:** JSON request/response bodies, all endpoints use POST unless noted  

# When to Use

- **AI-powered video search** — Product teams building intelligent search experiences that let users find specific moments across large video libraries using natural language queries  
- **Conversational Q&A over video content** — Developers integrating a chat-based interface where users ask questions and receive AI-generated answers grounded in actual video content with source citations  
- **Knowledge extraction and content discovery** — Organizations surfacing insights from their video libraries by enabling users to query across transcripts, metadata, and visual content without watching every video  
- **Custom RAG integrations** — Backend developers building server-side workflows that programmatically query Genie's retrieval-augmented generation API for content indexing, reporting, or automated knowledge base construction  

# Prerequisites

This guide assumes you already:
- Know how to generate Kaltura Sessions (KS) in your backend, setting privileges.  
- Have a Kaltura account setup with an AI Genie configured (workspace and indexed category).  
- Know how to use the Kaltura Player embeds.

Genie streams **structured generative answers** (flashcards, follow-ups, sources) plus "thinking/tool" status events.  

> **Client-Side Widget Embed:** To embed the Genie conversational UI directly in a web page (the most common integration pattern), see the [Genie Widget Guide](KALTURA_GENIE_WIDGET_API.md). This guide covers the server-side HTTP API for building custom integrations and backend workflows.

## KS Privileges

The KS passed to Genie requires the same privilege set whether used via the widget or the HTTP API. See the [Genie Widget Guide — Section 5: KS Requirements](KALTURA_GENIE_WIDGET_API.md) for the full list of required privileges, the curl example for generating the KS, and the privacy context explanation.

**Additional HTTP-API-specific privileges:**

These privileges apply only to server-side API integrations and are not part of the standard widget KS:

| Privilege | Purpose |
|-----------|---------|
| `genieentryids:<ID1,ID2,...>` | Whitelist specific entry IDs for search — only these entries will be queryable |
| `agentid:<ID>` | Select a specific agent configuration |
| `geniegpcid:<ID>` | Select a partner config by its database ID directly |

<!-- Sections: 1.Architecture Overview | 2.Stateless RAG Search | 3.Streaming Conversation | 4.WebSocket Chat | 5.Thread Management | 6.Message Management | 7.Feedback | 8.Suggested Questions | 9.Status & Configuration | 10.Integration Flow | 11.Error Handling | 12.Best Practices | 13.Related Guides -->

# 1. Architecture Overview

## Indexing Pipeline

Content becomes searchable in Genie through an automated indexing pipeline:

1. **Content ingestion** — Kaltura entries with captions, transcripts, attached documents, or OCR data are eligible for indexing  
2. **Text extraction** — The indexer extracts text from caption assets, document attachments, and OCR results  
3. **Chunking** — Extracted text is split into chunks (approximately 3,000 characters) with metadata linking each chunk to its source entry and time range  
4. **Embedding** — Each chunk is converted to a 1,024-dimension vector embedding via an embedding model  
5. **Storage** — Embeddings are stored in a vector database (PostgreSQL with pgvector) for similarity search  

The indexer tracks its position using a timestamp — only entries updated since the last indexing run are processed.

**Content requirements for indexing:**
- Entries must have **captions, transcripts, or document attachments** — entries with only video/audio and no text assets will not be indexed  
- Use [REACH](KALTURA_REACH_API.md) or the [Agents Manager](KALTURA_AGENTS_MANAGER_API.md) enrichment pipeline to generate captions before expecting Genie search results  
- Document attachments (PDF, TXT) on entries are also indexed, enabling Genie to search across both video transcripts and supplementary documents  

## Search Pipeline

When a user queries Genie, the search follows this path:

1. **Query embedding** — The user's query text is converted to a vector embedding using the same model as indexing  
2. **Vector similarity search** — The query embedding is compared against stored chunks using cosine similarity in pgvector  
3. **Entitlement filtering** — Results are filtered based on the user's KS privileges (category, entry whitelist, privacy context)  
4. **Chapter merging** — Adjacent matching chunks from the same entry are merged into coherent segments with start/end timestamps  
5. **Response** — Merged results are returned as text or structured chapters with source attribution  

# 2. Stateless RAG Search

**POST** `/mcp/search`

A stateless, single-shot search endpoint. Returns relevant content from the indexed knowledge base without creating a conversation thread.

**Parameters**

| Parameter | Type | Required | Default | Description |
|---|---|---|---|---|
| `query` | string | Yes | — | Natural-language question or keywords |
| `include_sources` | bool | No | `false` | When `true`, returns structured chapters with entry IDs, timestamps, and text segments. When `false`, returns concatenated text |
| `top_n` | int | No | `5` | Maximum number of result chunks to return |
| `margins_in_seconds` | int | No | `15` | Time margin (in seconds) to add around matched segments for context |
| `with_line_numbers` | bool | No | `false` | Include line numbers in the returned text |

### Text-only response (`include_sources: false` or omitted)

```json
// Request
{
  "query": "how to create an interactive video?",
  "include_sources": false
}

// Response
{
  "status": "success",
  "data": {
    "text": "<stitched transcript segments text>"
  }
}
```

Returns **stitched plain text** from the most relevant media transcripts. Expect some repetition if multiple hits overlap; the service prioritizes recall over de-duplication.

### Response with sources (`include_sources: true`)

```json
// Request
{
  "query": "how to create an interactive video?",
  "include_sources": true,
  "top_n": 3
}

// Response
{
  "status": "success",
  "data": {
    "chapters": [
      {
        "entry_id": "1_abc12345",
        "text": "<transcript segment text>",
        "start_time": 5,
        "end_time": 260
      },
      {
        "entry_id": "1_def67890",
        "text": "<transcript segment text>",
        "start_time": 10,
        "end_time": 425
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

### Empty results

When no matching content is found (or the vector index has not been built yet), the API returns:

```json
{
  "status": "error",
  "data": "Sorry, I couldn't find relevant information in the knowledge base."
}
```

This is not an API error — it means the knowledge base has no content matching the query. Ensure entries have captions/transcripts and the indexer has processed them.


# 3. Streaming Conversation

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
  "sse": false,
  "model_type": "fast",
  "threadId": "<optional — UUID from a previous response for multi-turn>",
  "force_experience": "flashcards"
}
```

**Parameters**

| Parameter | Type | Required | Default | Description |
|---|---|---|---|---|
| `userMessage` | string | Yes | — | The user's question or message |
| `sse` | bool | No | `false` | `true` for SSE (`text/event-stream`), `false` for NDJSON (`application/x-ndjson`) |
| `model_type` | string | No | — | `"fast"` for quick answers, `"smart"` for deeper research-quality answers (takes longer) |
| `threadId` | string (UUID) | No | — | Pass the `threadId` from a previous response to continue a multi-turn conversation. The assistant retains context from earlier messages in the same thread |
| `force_experience` | string | No | — | Force a specific output format. Known value: `"flashcards"` — ensures the response includes flashcard-style structured output |
| `preload_entry_ids` | list[string] | No | — | Focus the conversation on specific entries by ID. The assistant will load these entries' content directly, bypassing vector search |
| `filter_entry_ids` | list[string] | No | — | Restrict knowledge base search to only these entry IDs |
| `exclude_entry_ids` | list[string] | No | — | Exclude these entry IDs from search results |
| `capabilities` | object | No | — | Toggle capabilities on/off. Keys: `use_knowledge_base`, `use_content_search`, `use_get_entry_content`, `include_sources`. Values: `"on"` or `"off"` |
| `add_message_in_db` | bool | No | `true` | Set to `false` to skip persisting this exchange in the conversation history |

**Response metadata**

The **first event** in the stream includes:
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
- **NDJSON** (recommended — simpler parsing): `Accept: application/x-ndjson` and body `{ "sse": false }`
- **SSE** (for live UIs): `Accept: text/event-stream` and body `{ "sse": true }`

**Segment types you'll see in the streaming response**

The stream emits one JSON object per line (SSE lines are prefixed with `data:`). The reference table below breaks down the events' **type**.

**Stream event types (top-level `type`)**

| **Type** | **What it is** | **Content shape** (`content`) | **Key fields** (besides `content`) | **Primary use-cases in UI** | **Aggregation rules** | **Notes** |
|---|---|---|---|---|---|---|
| `think` | Model status / narration of internal progress. | Short status text (may be empty on the final line). | `segmentNumber`, `segmentStart?`, `isFinal?`, `et` | Show a transient "Preparing... / Thinking..." status/loading. | Independent lines. | Transient only; discard after display. Final packet will be `isFinal:true` with empty content. |
| `tool` | Declares a tool call the assistant is invoking. | One-line trace, e.g., `get_experience_instructions {"name":"flashcards"}`. | `segmentNumber`, `segmentStart?`, `et` | Brief "Using tool ..." chip while running. | Independent lines. | Internal telemetry; hide in UX / logs. |
| `tool_response` | The tool's completion notification. | One-line result summary, e.g., `... responded with size 1715`. | `segmentNumber`, `segmentStart?`, `et` | Response to the "tool" call. | Independent lines. | Internal telemetry; hide in UX / logs. |
| `unisphere-tool` | **Payload stream** from a runtime widget. Use `metadata.runtimeName` to route. | Multi-line, **YAML/Markdown-like** text. | `segmentNumber`, `segmentStart`, `segmentEnd`, `metadata:{widgetName,runtimeName}`, `et` | Render structured results (flashcards/clips, follow-ups, sources, etc.). | **Concatenate all `content` for the same `segmentNumber` from `segmentStart`→`segmentEnd`**, then parse. | Multiple segments of this type can arrive (one per runtime). |
| `text` | The assistant's **freeform answer** (markdown fragments). | Free text; may arrive in multiple chunks. | `segmentNumber`, `segmentStart?`, `et` | Show as the "Answer" section; append chunks as they arrive. | Concatenate in order of arrival. | Keep whitespace/newlines; post-process as needed. |
| `thread` | Thread metadata (e.g., a generated **title**). | Short YAML-ish lines, e.g., `title: "..."` | `segmentNumber`, `segmentStart`, `segmentEnd`, `et` | Update conversation title/breadcrumbs when `segmentEnd` lands. | Concatenate from `segmentStart`→`segmentEnd`, then parse key:values. | Typically one per response. |
| `share` | Share/bookmark metadata for the response. | JSON string, e.g., `{"canShare": true}`. | `segmentNumber`, `et` | Enable share/bookmark UI actions. | Independent lines. | May appear alongside other event types. |
| `error` | Error from the assistant. | Error message or code string. | `segmentNumber`, `et` | Display error state to user. | Independent lines. | Check for this to handle failures gracefully. |

**Common fields across events:**  
`role:"assistant"`, `type`, `segmentNumber` (grouping key), `segmentStart`/`segmentEnd` (chunk boundaries), `et` (elapsed time hint), `metadata` (only on some types).

**The `unisphere-tool` runtimes (use `metadata.runtimeName`)**

| **runtimeName** | **What you get** | **How the `content` looks** | **Parse into** | **Typical UI** | **Primary actions** |
|---|---|---|---|---|---|
| `flashcards-tool` | The flashcards + citations to clips. | YAML/Markdown-like block containing a top-level `title`, `summary`, then `keypoints` (each with `title` / `summary`) and `citation.clips` lists. Each clip has `entry_id`, `start_time`, `end_time` (plus indexes/types). | **Hero**: `{title, summary}`; **Clips**: array of `{title, summary, entryId, start, end}` (map keys & normalize). | Card stack + **Clips** panel. | Bind **Play** to Kaltura Player: `loadMedia({ entryId }, { startTime, clipTo })`. |
| `followups-tool` | **Suggested next questions**. | Lines like: `questions:\n- How do I ...?\n- What types of ...?` | `string[]` follow-ups. | Clickable list ("Follow-ups"). | Clicking a follow-up re-asks the question via the `converse` call. |
| `sources-tool` | **Reference sources** used. | YAML list like: `- title: ...\n  entry_id: 1_abc...\n  type: video\n  duration: 104` | Array of `{title, entryId, type, duration?}`. | "Sources" list with **entry_id** visible. | Deep-link to video at `start_time` or make assets downloadable when available. |

**Minimal client algorithm**

1. POST; open streamed body; iterate lines (for NDJSON: parse each line as JSON; for SSE: strip `data:` prefix, then parse).  
2. Route by `type`:  
   - `text` → append to answer buffer.  
   - `thread`/`unisphere-tool` → buffer by `segmentNumber`; on `segmentEnd` parse once.  
3. From `flashcards-tool`: render hero + clips; de-dupe clips by `entryId:start:end`.  

**Resilience and parsing guardrails**
- `content` is YAML/markdown-ish and **arrives in small chunks, even mid-word**. Buffer until `segmentEnd` for any structured block. Collect all chunks for a segment, normalize whitespace/quotes, then extract fields.
- **`metadata.runtimeName`** is set on the `segmentStart` event but **may be absent on subsequent content chunks** for the same segment. Track `segmentNumber → runtimeName` from the start event and use that mapping when routing later chunks.
- Anchor on stable keys: `title:`, `summary:`, `citation:`, `clips:`, `entry_id`, `start_time`, `end_time`.  
- Normalize `\r`, smart quotes, and repeated whitespace before pattern matching.  
- Keep a `segmentNumber → {kind, buffer}` map; clear on `segmentEnd`.  
- De-dup clips by composite key `entryId:start:end`.  

**Parsing `flashcards-tool` (YAML-like)**

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

- Read the **top** `title`/`summary` into a "hero" block.
- For each `keypoint`, attach its `title`/`summary` to the clips under `citation → clips`.
- Extract **entry_id**, **start_time**, **end_time** and de-dupe clips.


# 4. WebSocket Chat

**WebSocket** `/assistant/ws`

A bidirectional WebSocket connection for real-time chat with abort support. Uses the same streaming event format as the HTTP `/assistant/converse` endpoint.

**Auth:** `Authorization: KS <token>` header (preferred) or `?ks=<token>` query parameter. WebSocket connections accept auth via either method. Authentication is validated **before** the WebSocket connection is accepted — invalid credentials result in a close with code 1008 (Policy Violation).

## Client Events

### Init — Start a new session

```json
{
  "event": "init",
  "data": {
    "capabilities": {"use_knowledge_base": "on"},
    "model_type": "fast",
    "force_experience": "flashcards",
    "opening_phrase": "Hello! How can I help you today?"
  }
}
```

**Server response:**

```json
{
  "event": "init_response",
  "status": "success",
  "threadId": "<UUID>",
  "messageId": "<UUID>",
  "openingPhrase": "Hello! How can I help you today?"
}
```

### Converse — Send a message

```json
{
  "event": "converse",
  "data": {
    "userMessage": "What topics are covered?",
    "threadId": "<UUID from init_response>",
    "model_type": "fast"
  }
}
```

The server streams back the same event format as HTTP `/assistant/converse` (think, tool, text, unisphere-tool, etc.) as individual JSON objects.

### Abort — Cancel an in-flight request

```json
{
  "event": "abort",
  "data": {
    "messageId": "<UUID of the response to cancel>",
    "deleteFromHistory": false
  }
}
```

**Server response:**

```json
{
  "event": "abort_response",
  "status": "success",
  "messageId": "<UUID>"
}
```

Set `deleteFromHistory: true` to remove the aborted message from the conversation thread.

## Error Events

```json
{
  "event": "error",
  "error": "Error description",
  "messageId": "<UUID if applicable>"
}
```


# 5. Thread Management

Genie automatically creates conversation threads when users send messages via `/assistant/converse`. These endpoints let you list, inspect, and clean up threads.

### List Threads

**POST** `/thread/list`

```json
{
  "filter": {
    "objectType": "GenieListThreadFilter",
    "orderBy": "-updatedAt"
  },
  "pager": {
    "pageIndex": 1,
    "pageSize": 10
  }
}
```

**Filter fields:**

| Field | Type | Description |
|---|---|---|
| `orderBy` | string | Sort order. `"-updatedAt"` for newest first, `"+updatedAt"` for oldest first |
| `statusIn` | list[int] | Filter by status. `[0]` = active threads |
| `contextIdEqual` | string | Filter threads tied to a specific entry ID (used when Genie is embedded on a specific video page) |

**Response:**

```json
{
  "objects": [
    {
      "id": "ca0cb7ca-5fcf-4b75-860b-c48b8893883c",
      "title": "Home buying process steps",
      "status": 0,
      "updatedAt": 1712345678
    }
  ],
  "totalCount": 42
}
```

### Delete Threads

**POST** `/thread/delete`

```json
{
  "thread_ids": ["<threadId1>", "<threadId2>"]
}
```

**Response:** Returns the list of deleted thread objects.


# 6. Message Management

### List Messages

**POST** `/message/list`

```json
{
  "filter": {
    "objectType": "GenieListMessageFilter",
    "threadIdEquals": "<threadId>",
    "orderBy": "+updatedAt"
  },
  "pager": {
    "pageIndex": 1,
    "pageSize": 100
  }
}
```

**Filter fields:**

| Field | Type | Description |
|---|---|---|
| `threadIdEquals` | string | Required — the thread to list messages from |
| `orderBy` | string | `"+updatedAt"` for chronological order |
| `isPositiveEquals` | bool | Filter by feedback status (only messages with positive/negative feedback) |
| `idEquals` | string | Get a specific message by ID (used for loading shared messages) |

Each message object contains an `assistant` field with the full conversation exchange:

```json
{
  "id": "<messageId>",
  "assistant": {
    "messages": [
      {"type": "human", "content": [{"text": "What is this about?"}]},
      {"type": "ai", "content": [{"text": "This video covers..."}]}
    ]
  }
}
```

### Share a Message

**POST** `/message/share`

Creates a shareable copy of a message that can be loaded by other users.

```json
{
  "id": "<messageId>",
  "newTitle": "Shared conversation about home buying"
}
```

**Response:**

```json
{
  "status": "success",
  "data": {
    "newMessageId": "<UUID of the shared copy>"
  }
}
```

To load a shared message, use `/message/list` with `filter.idEquals` set to the `newMessageId`.


# 7. Feedback

### Add Feedback

**POST** `/feedback/add`

Submit thumbs-up/down feedback on a Genie response.

```json
{
  "schemaVersion": 1,
  "data": {
    "is_positive": true,
    "message_id": "<messageId>",
    "comment": "Great answer, very helpful!"
  }
}
```

| Field | Type | Required | Description |
|---|---|---|---|
| `is_positive` | bool | Yes | `true` for thumbs up, `false` for thumbs down |
| `message_id` | string | No | The message ID this feedback is for |
| `comment` | string | No | Optional text comment explaining the rating |

**Response:**

```json
{
  "status": "success",
  "data": "Feedback added successfully"
}
```

### List Feedback

**POST** `/feedback/list`

```json
{
  "filter": {
    "objectType": "GenieListFeedbackFilter",
    "isPositiveEquals": false,
    "threadIdEquals": "<threadId>"
  },
  "pager": {"pageIndex": 1, "pageSize": 50}
}
```


# 8. Suggested Questions

**POST** `/followup/get-suggested-questions?new_response=true`

Returns a set of suggested questions drawn from the indexed knowledge base. Questions are filtered by the user's entitlements and cached for 5 minutes.

```json
// Request (empty body)
{}

// Response
{
  "status": "success",
  "data": [
    "What five questions should you ask before buying a home?",
    "What does the mind map help you decide about?",
    "Who is the man explaining the mind map content?"
  ]
}
```

The `new_response=true` query parameter returns the modern response format (list of strings). Typically returns 3 random questions from the indexed content.


# 9. Status & Configuration

**GET** `/assistant/status`

Returns the current configuration for the authenticated user's Genie workspace: AI consent status, avatar configuration, and whether the user is identified.

```json
// Response
{
  "aiConsent": {
    "approval_status": "approved by kaltura",
    "related_permissions": "FEATURE_CONTENT_LAB,FEATURE_GENIE_PERMISSION",
    "canSetConsent": false
  },
  "avatar": null,
  "identifiedUser": true
}
```

| Field | Type | Description |
|---|---|---|
| `aiConsent.approval_status` | string | Whether AI features are approved for this account |
| `aiConsent.canSetConsent` | bool | Whether the user can change consent settings |
| `avatar` | object or null | Avatar configuration if an AI avatar is enabled for this workspace |
| `identifiedUser` | bool | Whether the KS identifies a specific user (vs anonymous access) |

**GET** `/health`

Service health check (no auth required):

```json
{"status": "success", "version": "e91009d"}
```


# 10. Integration Flow

The typical integration flow for building a Genie-powered feature:

**Step 1: Initialize**
```
GET /assistant/status → get AI consent, avatar config, capabilities
```

**Step 2: Get suggested questions (optional)**
```
POST /followup/get-suggested-questions?new_response=true → display starter prompts
```

**Step 3: User asks a question**
```
POST /assistant/converse (stream) → parse streaming events for answer, sources, flashcards
```

Parse the stream by `type`:
- `text` → append to answer display
- `unisphere-tool` with `flashcards-tool` → render structured cards with video clips
- `unisphere-tool` with `followups-tool` → display follow-up question buttons
- `unisphere-tool` with `sources-tool` → display source entry references
- `thread` → extract conversation title on `segmentEnd`

**Step 4: User rates the answer**
```
POST /feedback/add → submit thumbs up/down with optional comment
```

**Step 5: User views conversation history**
```
POST /thread/list → get all threads
POST /message/list → load messages for selected thread
```

**Step 6: User shares an answer**
```
POST /message/share → create shareable message link
```

**Step 7: Clean up**
```
POST /thread/delete → delete threads when no longer needed
```

For **entry-specific** conversations (e.g., Genie embedded on a video page), use `preload_entry_ids` in the converse request to focus answers on that specific video's content.

For **stateless search** (no conversation, quick hits), use `/mcp/search` instead of `/assistant/converse`.


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
curl -X POST "$KALTURA_GENIE_URL/mcp/search" \
  -H "Authorization: KS $KALTURA_KS" \
  -H "Content-Type: application/json" \
  -d '{
    "query": "how to create an interactive video?",
    "include_sources": true,
    "top_n": 5
  }'
```

### RAG Search with Time Margins and Line Numbers

```bash
curl -X POST "$KALTURA_GENIE_URL/mcp/search" \
  -H "Authorization: KS $KALTURA_KS" \
  -H "Content-Type: application/json" \
  -d '{
    "query": "cloud computing benefits",
    "include_sources": true,
    "top_n": 3,
    "margins_in_seconds": 30,
    "with_line_numbers": true
  }'
```

### Streaming Conversation (`/assistant/converse`) with NDJSON

```bash
curl -N -X POST "$KALTURA_GENIE_URL/assistant/converse" \
  -H "Authorization: KS $KALTURA_KS" \
  -H "Content-Type: application/json" \
  -H "Accept: application/x-ndjson" \
  -d '{
    "userMessage": "What are the key features?",
    "sse": false,
    "model_type": "fast"
  }'
```

Each line in the response is a JSON object. Route by the `type` field (`text`, `unisphere-tool`, `thread`, etc.) as described in the streaming event tables above. The first event includes a `threadId` you can store for multi-turn follow-ups.

### Multi-turn Follow-up

Pass the `threadId` returned from a previous response to continue the conversation with full context:

```bash
curl -N -X POST "$KALTURA_GENIE_URL/assistant/converse" \
  -H "Authorization: KS $KALTURA_KS" \
  -H "Content-Type: application/json" \
  -d '{
    "userMessage": "Can you go deeper on the second point?",
    "sse": false,
    "model_type": "fast",
    "threadId": "<THREAD_ID_FROM_PREVIOUS_RESPONSE>"
  }'
```

### Entry-Specific Conversation

Focus the conversation on a specific video by providing its entry ID:

```bash
curl -N -X POST "$KALTURA_GENIE_URL/assistant/converse" \
  -H "Authorization: KS $KALTURA_KS" \
  -H "Content-Type: application/json" \
  -d '{
    "userMessage": "What is this video about?",
    "sse": false,
    "model_type": "fast",
    "preload_entry_ids": ["1_abc12345"]
  }'
```

### List Conversation Threads

```bash
curl -X POST "$KALTURA_GENIE_URL/thread/list" \
  -H "Authorization: KS $KALTURA_KS" \
  -H "Content-Type: application/json" \
  -d '{
    "filter": {
      "objectType": "GenieListThreadFilter",
      "orderBy": "-updatedAt"
    },
    "pager": {"pageIndex": 1, "pageSize": 10}
  }'
```

### Conversation with Capabilities and Entry Filters

```bash
# Disable knowledge base search, focus on a specific entry's content
curl -N -X POST "$KALTURA_GENIE_URL/assistant/converse" \
  -H "Authorization: KS $KALTURA_KS" \
  -H "Content-Type: application/json" \
  -d '{
    "userMessage": "Summarize this video",
    "sse": false,
    "model_type": "fast",
    "preload_entry_ids": ["1_abc12345"],
    "capabilities": {
      "use_knowledge_base": "off",
      "use_get_entry_content": "on",
      "include_sources": "on"
    }
  }'
```

### Filtered and Excluded Entries

```bash
# Search only within specific entries
curl -N -X POST "$KALTURA_GENIE_URL/assistant/converse" \
  -H "Authorization: KS $KALTURA_KS" \
  -H "Content-Type: application/json" \
  -d '{
    "userMessage": "What are the key takeaways?",
    "sse": false,
    "filter_entry_ids": ["1_abc12345", "1_def67890"]
  }'

# Exclude specific entries from search
curl -N -X POST "$KALTURA_GENIE_URL/assistant/converse" \
  -H "Authorization: KS $KALTURA_KS" \
  -H "Content-Type: application/json" \
  -d '{
    "userMessage": "What topics are covered?",
    "sse": false,
    "exclude_entry_ids": ["1_already_seen"]
  }'
```

### Ephemeral Conversation (Skip Persistence)

```bash
curl -N -X POST "$KALTURA_GENIE_URL/assistant/converse" \
  -H "Authorization: KS $KALTURA_KS" \
  -H "Content-Type: application/json" \
  -d '{
    "userMessage": "Quick question — what is this?",
    "sse": false,
    "model_type": "fast",
    "add_message_in_db": false
  }'
```

### Submit Feedback

```bash
curl -X POST "$KALTURA_GENIE_URL/feedback/add" \
  -H "Authorization: KS $KALTURA_KS" \
  -H "Content-Type: application/json" \
  -d '{
    "schemaVersion": 1,
    "data": {
      "is_positive": true,
      "message_id": "<MESSAGE_ID>",
      "comment": "Helpful answer"
    }
  }'
```


# 11. Error Handling

| Error / Status | Meaning | Resolution |
|----------------|---------|------------|
| `401 Unauthorized` | Invalid or expired KS | Generate a fresh KS; verify the `Authorization: KS $KALTURA_KS` header format (note: `KS` prefix, not `Bearer`) |
| `403 Forbidden` | Insufficient privileges or admin-only endpoint | Verify KS privileges include required `genieid` and category access |
| `404 Not Found` | Invalid endpoint path | Verify the base URL and path |
| `400 Bad Request` | Missing required field | Check that `query` (for search) or `userMessage` (for converse) is present |
| `{"status": "error", "data": "Sorry..."}` | No matching content in vector index | Verify content has captions/transcripts and the Genie indexer has processed them |
| SSE stream ends without `[DONE]` | Connection interrupted | Implement reconnection logic; use WebSocket for abort support |
| `threadId` not found | Conversation thread expired or invalid | Start a new conversation without `threadId` — threads are ephemeral |
| WebSocket close code `1008` | Auth failure before connection accepted | Verify KS is valid and not expired |
| WebSocket close code `1011` | Internal server error after connection | Reconnect with a new WebSocket connection |

**Retry strategy:** For transient errors (HTTP 5xx, timeouts, stream interruptions), retry with exponential backoff: 1s, 2s, 4s, with jitter, up to 3 retries. For client errors (`401 Unauthorized`, `400 Bad Request`, invalid `threadId`), fix the request before retrying — these will not resolve on their own.

# 12. Best Practices

- **Enrich content before querying.** Genie's RAG quality depends on captions, transcripts, and document attachments. Use REACH or the Agents Manager enrichment pipeline to process content before making it searchable.
- **Use `model_type: "fast"` for interactive UIs** where response latency matters. Use `"smart"` for batch or background analysis where quality matters more.
- **Use NDJSON (`sse: false`) for simpler parsing.** SSE adds a `data:` prefix that requires stripping. NDJSON is simpler and what the official Genie widget uses.
- **Use `preload_entry_ids` for entry-specific conversations.** When Genie is embedded alongside a specific video, pass that entry's ID so the assistant focuses on that content without relying on vector search.
- **Use `capabilities` to toggle features.** Set `use_knowledge_base: "off"` and `use_get_entry_content: "on"` when you want entry-specific answers without searching the broader knowledge base.
- **Reuse `threadId` for multi-turn conversations.** Pass the `threadId` from the previous response to maintain conversation context across multiple exchanges.
- **Use `force_experience`** to target a specific output format (e.g., `"flashcards"`) when you need structured data rather than freeform text.
- **Use WebSocket for real-time bidirectional chat.** WebSocket connections support aborting in-flight requests, which HTTP streaming does not.
- **Track `segmentNumber → runtimeName`** from `segmentStart` events. The `metadata.runtimeName` may be absent on subsequent chunks for the same segment.
- **Use AppTokens for production.** Generate scoped KS tokens server-side and keep admin secrets on the backend only.

# 13. Related Guides

- **[Session Guide](KALTURA_SESSION_GUIDE.md)** — Generate the KS required for Genie auth (`KS` header)
- **[AppTokens](KALTURA_APPTOKENS_API.md)** — Secure KS generation for production Genie integrations
- **[eSearch](KALTURA_ESEARCH_API.md)** — Structured search (Genie uses vector search internally; use eSearch when you need precise metadata filters)
- **[REACH](KALTURA_REACH_API.md)** — Enrich content with captions/transcripts that Genie indexes for better answers
- **[Upload & Ingestion](KALTURA_UPLOAD_AND_INGESTION_API.md)** — Upload content that becomes searchable via Genie
- **[Agents Manager](KALTURA_AGENTS_MANAGER_API.md)** — Automate content enrichment to improve Genie's knowledge base
- **[Events Platform](KALTURA_EVENTS_PLATFORM_API.md)** — Genie can search event-related content
- **[Genie Widget](KALTURA_GENIE_WIDGET_API.md)** — Genie conversational AI widget embed (client-side UI)  
- **[Experience Components](KALTURA_EXPERIENCE_COMPONENTS_API.md)** — Index of all embeddable components

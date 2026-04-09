---
name: kaltura-api
description: Build applications on Kaltura — The Agentic Digital Experience Platform. Covers authentication, content management, search, playback, AI-powered content enrichment, conversational AI, virtual events, and multi-stream. API v3 (form-encoded) and modern JSON APIs with curl examples and tested workflows.
---

# Kaltura API Integration

Kaltura — The Agentic Digital Experience Platform. Kaltura is powering rich, agentic digital experiences across organizational journeys for customers, employees, learners, and audiences. The Kaltura platform combines intelligent content creation, enterprise-grade content management and intelligence, and multimodal conversational engagement capabilities. Kaltura serves leading enterprises, financial institutions, educational institutions, media and telecom providers, and other organizations worldwide.

This skill gives you the knowledge map to build any integration on Kaltura's 80+ REST API services.

## Platform Overview

The platform is built on three core layers:

- **Intelligent Content Creation** — Recording, editing, AI-assisted content generation (transcription, translation, captioning, dubbing, summarization, chaptering, clipping, quiz generation), and avatar-based video creation
- **Enterprise-Grade Content Management and Intelligence** — Centralized management of live and on-demand content with metadata, permissions, workflows, analytics, and AI-driven workflow agents for automated content lifecycle operations
- **Multimodal Conversational Engagement** — Content hubs, virtual events and webinars, player embeds, LMS/CMS integrations, conversational AI agents (Kaltura Genies and Agentic Avatars), and TV streaming applications

Content is organized as **entries** (media objects with metadata, flavors, thumbnails, and captions). Every API call requires a **Kaltura Session (KS)** — a signed, time-limited auth token.

## Authentication

Two auth methods, depending on context:

| Method | When to Use | How |
|--------|-------------|-----|
| `session.start` | Internal backend tools where you control the environment | POST with `partnerId` + `adminSecret` → returns KS |
| `appToken.startSession` | Production integrations, partner apps, microservices | HMAC exchange with a pre-created token — no admin secret exposed |

KS types: **USER** (type=0) for end-user operations, **ADMIN** (type=2) for backend-only management.

For full auth details, KS privileges, and AppToken HMAC workflow:
- [Session Guide](../../../KALTURA_SESSION_GUIDE.md) — KS generation, types, privileges, security practices
- [AppTokens API](../../../KALTURA_APPTOKENS_API.md) — Create, distribute, and rotate scoped tokens

## API Patterns

### API v3 (most services)

```bash
curl -X POST "$KALTURA_SERVICE_URL/service/{service}/action/{action}" \
  -d "ks=$KALTURA_KS" \
  -d "format=1" \
  -d "param[key]=value"
```

- **Base URL:** `https://www.kaltura.com/api_v3`
- Form-encoded POST, always include `format=1` for JSON responses
- Nested params use bracket notation: `filter[nameContains]=test`

### Modern JSON APIs

Some newer services use JSON bodies with auth headers:

| API | Base URL | Auth Header |
|-----|----------|-------------|
| Events Platform | `https://events-api.nvp1.ovp.kaltura.com/api/v1` | `Authorization: Bearer $KALTURA_KS` |
| App Registry | `https://app-registry.nvp1.ovp.kaltura.com/api/v1` | `Authorization: Bearer $KALTURA_KS` |
| User Profile | `https://user.nvp1.ovp.kaltura.com/api/v1` | `Authorization: Bearer $KALTURA_KS` |
| Agents Manager | `https://agents-manager.nvp1.ovp.kaltura.com` | `Authorization: Bearer $KALTURA_KS` |
| AI Genie | `https://genie.nvp1.ovp.kaltura.com` | `Authorization: KS $KALTURA_KS` |
| Messaging | `https://messaging.nvp1.ovp.kaltura.com/api/v1` | `Authorization: Bearer $KALTURA_KS` |

## Common Integration Flows

### Upload → Process → Deliver → Embed

1. **Upload** content via chunked upload or import-from-URL
2. **Poll** for entry status to reach READY (status=2)
3. **Process** with AI services (captions, translation, summaries) via REACH or Agents
4. **Search** your content library with eSearch
5. **Embed** the player in your application

### Entry Status Lifecycle

| Status | Value | Meaning |
|--------|-------|---------|
| NO_CONTENT | -2 | Entry created, no media attached |
| IMPORT | 0 | Importing from URL |
| PRECONVERT | 1 | Queued for transcoding |
| READY | 2 | Playable |
| CONVERTING | 4 | Transcoding in progress |
| DELETED | 7 | Soft-deleted |

### Upload Lifecycle

```
uploadToken.add → uploadToken.upload (one or more chunks) → media.add → media.addContent
```

Shortcuts: `media.addFromUploadedFile` (create + attach in one call), `media.addFromUrl` (import from URL).

## Capability Map — Detailed Guides

Read the relevant guide when you need to implement a specific capability:

### Content Management

- **[Upload & Delivery API](../../../KALTURA_UPLOAD_AND_DELIVERY_API.md)** — Chunked/resumable uploads, import-from-URL, playback URLs (HLS/DASH), thumbnail API, flavor assets, download links. Start here for any content ingestion workflow.

- **[eSearch API](../../../KALTURA_ESEARCH_API.md)** — Full-text search across entries, captions, metadata, categories, and users. Supports AND/OR/NOT operators, nested filters, highlighting, facets, and sorting.

### Playback

- **[Player Embed Guide](../../../KALTURA_PLAYER_EMBED_GUIDE.md)** — Embed Kaltura's Player v7 via iframe or JavaScript SDK. Covers autoplay, clipping (start/end times), access-controlled playback with KS, and programmatic player control.

- **[Multi-Stream API](../../../KALTURA_MULTI_STREAM_API.md)** — Dual/multi-screen entries for Picture-in-Picture and Side-by-Side layouts. Parent-child entry relationships, Dual Screen player plugin, runtime layout switching.

### AI Services

- **[REACH API](../../../KALTURA_REACH_API.md)** — Order AI or human captions, translations (40+ languages), audio descriptions, in-video chapters, summaries, and smart clips. Results auto-attach to entries. Includes the AI Clips workflow for generating highlight reels.

- **[Agents Manager API](../../../KALTURA_AGENTS_MANAGER_API.md)** — Create automated content-processing agents with triggers ("when a new entry is uploaded") and actions ("generate captions, then translate to Spanish"). Hands-free processing at scale.

- **[AI Genie API](../../../KALTURA_AI_GENIE_API.md)** — Conversational AI search over your video library using RAG. Streaming responses with structured answers (flashcards, sources, follow-ups). Supports both semantic search and multi-turn conversations.

### Events & User Management

- **[Events Platform API](../../../KALTURA_EVENTS_PLATFORM_API.md)** — Create and manage virtual events (town halls, webinars, conferences). Modern REST API with session types (Interactive Room, LiveWebcast, SimuLive), team members, speakers, templates, and event duplication. Multi-region support.

- **[App Registry API](../../../KALTURA_APP_REGISTRY_API.md)** — Register and manage Kaltura application instances (KMS sites, Events Platform portals, custom apps). Each registered app gets a unique GUID used by other services to associate data with specific app contexts. When Events Platform creates a virtual event, the event ID becomes the `appCustomId` — use `appCustomIdIn` filter to resolve virtual event IDs to app GUIDs.

- **[User Profile API](../../../KALTURA_USER_PROFILE_API.md)** — Per-application user profile management with event attendance lifecycle tracking. Manage registration, attendance status progression (created → registered → confirmed → attended → participated), bulk user import, attendance reporting, and incremental data sync. Includes cross-service registration data retrieval (virtualEvent → App Registry → User Profile → user.list) and engagement analytics via Reports API (report IDs 3030, 3037). Depends on App Registry for app context.

- **[Messaging API](../../../KALTURA_MESSAGING_API.md)** — Template-based email messaging for event communications, attendee notifications, and personalized outreach. Create templates with dynamic tokens (user profile fields, magic login links, QR codes, unsubscribe links), send personalized emails to individual users or groups, track delivery status and engagement (opens, clicks, bounces), and manage CAN-SPAM compliant unsubscribe preferences. Depends on App Registry for app context (appGuid) and integrates with User Profile for recipient data.

## Environment Setup

```bash
export KALTURA_SERVICE_URL="https://www.kaltura.com/api_v3"
export KALTURA_PARTNER_ID="your_partner_id"
export KALTURA_KS="your_kaltura_session"
```

Regional deployments may use different base URLs. Check with your Kaltura account configuration.

---
name: kaltura-api
description: Build applications on Kaltura — The Agentic Digital Experience Platform. Covers authentication (sessions, AppTokens, SSO/SAML), content management (upload, search, categories, metadata, captions), playback, AI services (captions, translation, agents, conversational AI), virtual events, user management, multi-stream, distribution & syndication. API v3 (form-encoded) and modern JSON APIs with curl examples and tested workflows.
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
- [Auth Broker API](../../../KALTURA_AUTH_BROKER_API.md) — SSO/SAML configuration, app subscriptions, federated login

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
| Auth Broker | `https://auth.nvp1.ovp.kaltura.com/api/v1` | `Authorization: KS $KALTURA_KS` |
| Reports Microservice | `https://reports.nvp1.ovp.kaltura.com` | `Authorization: Bearer $KALTURA_KS` |
| Game Services (SCM) | `https://scm.nvp1.ovp.kaltura.com/api/v1` | `Authorization: Bearer $KALTURA_KS` |

> **Regional deployments** may use different base URLs (e.g., `irp2` for EU, `frp2` for DE). The URLs above are for the default NVP1 (US) region. Check your Kaltura account configuration for the correct regional endpoints.

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

- **[Categories & Access Control API](../../../KALTURA_CATEGORIES_AND_ACCESS_CONTROL_API.md)** — Hierarchical content taxonomy via `category` service, membership and entitlement via `categoryUser`, content assignment via `categoryEntry`, and `accessControlProfile` rules (geo/IP/domain/scheduling restrictions). Accounts with entitlement enabled require `disableentitlement` KS privilege for cross-category operations.

- **[Custom Metadata API](../../../KALTURA_CUSTOM_METADATA_API.md)** — XSD-based metadata schemas via `metadata_metadataProfile` plugin service with Kaltura-native types (textType, dateType, objectType, listType) and `<appinfo>` annotations for KMC rendering. Per-object structured metadata CRUD via `metadata_metadata` with optimistic locking, XSLT transformation pipeline, and eSearch integration via `KalturaESearchEntryMetadataItem`.

- **[Captions & Transcripts API](../../../KALTURA_CAPTIONS_AND_TRANSCRIPTS_API.md)** — Caption asset management (SRT/WebVTT/DFXP/SCC) via `caption_captionAsset` with two-step creation (add → setContent), on-the-fly WebVTT conversion, HLS segmented delivery, JSON serving for AI/LLM integrations, caption parameter templates via `caption_captionParams`, multi-language workflows, REACH integration for ASR/translation, and eSearch caption search via `KalturaESearchCaptionItem`.

### Playback

- **[Player Embed Guide](../../../KALTURA_PLAYER_EMBED_GUIDE.md)** — Embed Kaltura's Player v7 via iframe or JavaScript SDK. Covers autoplay, clipping (start/end times), access-controlled playback with KS, and programmatic player control.

- **[Multi-Stream API](../../../KALTURA_MULTI_STREAM_API.md)** — Dual/multi-screen entries for Picture-in-Picture and Side-by-Side layouts. Parent-child entry relationships, Dual Screen player plugin, runtime layout switching.

### AI Services

- **[REACH API](../../../KALTURA_REACH_API.md)** — Order AI or human captions, translations (40+ languages), audio descriptions, in-video chapters, summaries, and smart clips. Results auto-attach to entries. Includes the AI Clips workflow for generating highlight reels and REACH Automation Rules (Boolean event conditions, category conditions, always-on) for automatic processing of matching entries.

- **[Agents Manager API](../../../KALTURA_AGENTS_MANAGER_API.md)** — Create automated content-processing agents with triggers ("when a new entry is uploaded") and actions ("generate captions, then translate to Spanish"). Hands-free processing at scale.

- **[AI Genie API](../../../KALTURA_AI_GENIE_API.md)** — Conversational AI search over your video library using RAG. Streaming responses with structured answers (flashcards, sources, follow-ups). Supports both semantic search and multi-turn conversations.

### Events & User Management

- **[User Management API](../../../KALTURA_USER_MANAGEMENT_API.md)** — Full user lifecycle via `user` service (add, get, list, update, delete), login and credential management (enableLogin/disableLogin), role-based access control (RBAC) via `userRole` service (add, get, list, update, clone, delete), and groups via `group_group` service with `groupUser` membership. User statuses: 0 (BLOCKED), 1 (ACTIVE), 2 (DELETED).

- **[Auth Broker API](../../../KALTURA_AUTH_BROKER_API.md)** — SSO/SAML configuration microservice at `https://auth.nvp1.ovp.kaltura.com/api/v1`. Auth profiles (SAML IdP config with certificate, attribute mappings, group sync), app subscriptions (link apps to auth providers), SAML metadata endpoint, and SPA proxy for KMC. Uses `Authorization: KS <KS>` header (not Bearer).

- **[Events Platform API](../../../KALTURA_EVENTS_PLATFORM_API.md)** — Create and manage virtual events (town halls, webinars, conferences). Modern REST API with session types (Interactive Room, LiveWebcast, SimuLive), team members, speakers, templates, and event duplication. Multi-region support.

- **[App Registry API](../../../KALTURA_APP_REGISTRY_API.md)** — Register and manage Kaltura application instances (KMS sites, Events Platform portals, custom apps). Each registered app gets a unique GUID used by other services to associate data with specific app contexts. When Events Platform creates a virtual event, the event ID becomes the `appCustomId` — use `appCustomIdIn` filter to resolve virtual event IDs to app GUIDs.

- **[User Profile API](../../../KALTURA_USER_PROFILE_API.md)** — Per-application user profile management with event attendance lifecycle tracking. Manage registration, attendance status progression (created → registered → confirmed → attended → participated), bulk user import, attendance reporting, and incremental data sync. Includes cross-service registration data retrieval (virtualEvent → App Registry → User Profile → user.list) and engagement analytics via Reports API (report IDs 3030, 3037). Depends on App Registry for app context.

- **[Messaging API](../../../KALTURA_MESSAGING_API.md)** — Template-based email messaging for event communications, attendee notifications, and personalized outreach. Create templates with dynamic tokens (user profile fields, magic login links, QR codes, unsubscribe links), send personalized emails to individual users or groups, track delivery status and engagement (opens, clicks, bounces), and manage CAN-SPAM compliant unsubscribe preferences. Depends on App Registry for app context (appGuid) and integrates with User Profile for recipient data.

### Analytics & Gamification

- **[Analytics Reports API](../../../KALTURA_ANALYTICS_REPORTS_API.md)** — Pull analytics data: `report.getTable/getTotal/getGraphs` for VOD/Live/Webcast metrics, CSV exports via `getUrlForReportAsCsv` and `getCsvFromStringParams`, async Reports Microservice (generate/serve), live analytics via `liveReports.getEvents` and `beacon.list` for stream health. Pipe-delimited response format with paging, date-range filters, and multi-request batching.

- **[Analytics Events Collection API](../../../KALTURA_ANALYTICS_EVENTS_COLLECTION_API.md)** — Report playback and engagement events back to Kaltura analytics. `stats.collect` for server-side player events (WIDGET_LOADED, PLAY, quartiles, SEEK, buffer, replay), `analytics.trackEvent` for application-level tracking (PageLoad, ButtonClicked). Supports `appId` KS privilege for per-application segmentation and custom event context fields.

- **[Gamification API](../../../KALTURA_GAMIFICATION_API.md)** — Leaderboards, badges, certificates, lead scoring, and a rules engine via the Game Services (SCM) microservice. Rule types: sum, count, countUnique, countBoolean, external, override. Participation policies (display/do_not_display/do_not_save with email domain or group matching). Sub-leaderboards with filterPaths. Certificate PDF generation with text overlays. External events via CSV import. Scheduled game objects for automated status transitions.

### Distribution & Syndication

- **[Distribution & Syndication API](../../../KALTURA_DISTRIBUTION_AND_SYNDICATION_API.md)** — Push content to external platforms (YouTube, Facebook, FTP, Cross-Kaltura) via distribution connectors, and generate syndication feeds (Google Video Sitemap, Yahoo MRSS, iTunes Podcast, Roku) that external platforms pull via HTTP. Distribution profiles define automation rules (auto-submit on entry ready, moderation-gated, sunrise/sunset scheduling). Entry distributions track per-entry status through a state machine (PENDING → QUEUED → SUBMITTING → READY). Syndication feeds serve XML at public URLs with entry filtering, playlist scoping, and configurable caching. Uses `contentDistribution_*` plugin services for distribution and `syndicationFeed` service for feeds.

### Integration & Automation

- **[Webhooks & Event Notifications API](../../../KALTURA_WEBHOOKS_API.md)** — Real-time HTTP webhooks and email notifications triggered by content events (entry ready, metadata changed, caption added, REACH task completed). Clone pre-built system templates, configure webhook URLs with HMAC signing, set event conditions, and use manual dispatch for testing. Email notifications are delivered via the Messaging Service (SendGrid) with delivery tracking and engagement analytics. Uses the `eventnotification_eventnotificationtemplate` API v3 plugin service. Boolean Event Notification Templates serve as conditions for REACH Automation Rules (documented in the REACH guide).

## Security & Best Practices

When building on Kaltura, follow these principles for production-quality integrations:

- **Use AppTokens for production auth.** Never expose `adminSecret` in client code. Create scoped AppTokens with minimal privileges and rotate periodically. See [AppTokens API](../../../KALTURA_APPTOKENS_API.md).
- **Prefer USER KS (type=0)** for end-user operations. Reserve ADMIN KS (type=2) for backend-only management. Scope privileges with `edit:`, `sview:`, `setrole:`, `iprestrict:`.
- **Verify webhook signatures.** Validate `SHA256(signing_secret + body)` on all incoming HTTP webhooks before processing.
- **Use Kaltura's built-in services** rather than reimplementing. REACH for transcription/translation, Agents Manager for automated processing, Messaging for email delivery, eSearch for search, Access Control for content protection.
- **Handle errors and retries.** Check every API response for error codes. Implement exponential backoff for transient failures (HTTP 500, rate limits). Log error codes for debugging.
- **Set short KS expiry.** Default to 1-4 hour sessions. Use AppToken session renewal rather than long-lived admin sessions.
- **Sanitize inputs.** Validate user-provided entry IDs, search terms, and metadata before passing to API calls.
- **Use CAN-SPAM compliant email patterns.** Include unsubscribe links and respect opt-out preferences when using the Messaging API.

## Environment Setup

```bash
export KALTURA_SERVICE_URL="https://www.kaltura.com/api_v3"
export KALTURA_PARTNER_ID="your_partner_id"
export KALTURA_KS="your_kaltura_session"
```

Regional deployments may use different base URLs. Check with your Kaltura account configuration.

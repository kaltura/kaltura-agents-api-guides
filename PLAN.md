# Kaltura API Guides — Roadmap

**Current state:** 48 guides, 912 live-tested assertions, 4-tier flywheel structure.  
Completed guide details are in [README.md](README.md). Test inventory is in each `tests/test_*.py` file.

## Audit Findings (2026-04-21)

Gaps and improvements identified from a full documentation set audit:

### Stale Numbers
- ~~PLAN.md, SKILL.md, mkdocs.yml, context7.json had outdated guide/test counts~~ — Fixed
- README.md Distribution row said 84 tests, actual is 83 (40 + 43) — Fixed

### Missing from mkdocs.yml Nav
- ~~7 guides (Cue Points hub + 5 type guides + Moderation) missing from docs site navigation~~ — Fixed

### Missing Required Sections (per AGENTS.md)
- **Missing Prerequisites section:** Annotations, Multi-Stream, REACH, Thumbnail, Agents Manager (H2 not numbered H1), AI Genie (not numbered)
- **Missing Best Practices section:** eSearch, Experience Components
- **Non-standard header block:** Content Delivery (no Format line), Thumbnail (no Base URL/Format), VOD Avatar (non-standard Base URL label)

### Negative Framing (should rewrite positively)
- 8 guides with 6+ instances: Session Guide, VOD Avatar, Analytics Embed, REACH, AppTokens, Captions & Transcripts, Custom Metadata, Thumbnail

### Missing Business Context / Use Cases
- **Annotations** — technical-only, needs real-world scenarios (in-video discussions, peer review, content commenting)
- **Multi-Account Management** — no "When to Use" section, needs parent-child hierarchy use cases (multi-tenant SaaS, white-label portals, departmental isolation)
- **REACH** — platform benefits described but needs concrete enrichment scenarios (auto-caption all uploads, localize to 30 languages, compliance transcripts)

---

## Tier 1 — Critical Gaps (Core Video Operations)

These are fundamental video platform operations that virtually every integration uses. They represent the most significant coverage gaps.

### `KALTURA_TRANSCODING_AND_FLAVORS_API.md`

**Why:** Transcoding is how uploaded videos become playable renditions. Every customer who uploads video needs to understand conversion profiles, flavor parameters, and rendition management. KMC has a dedicated "Transcoding" section.

**Scope:**
- `conversionProfile.add` / `update` / `get` / `list` / `delete` / `setAsDefault` — transcoding profile lifecycle
- `flavorParams.add` / `update` / `get` / `list` / `delete` — encoding parameter definitions (codec, bitrate, resolution, frame rate)
- `conversionProfileAssetParams.list` / `update` — per-profile flavor param overrides (readyBehavior, systemName, forceNoneComplied)
- `flavorAsset.list` / `get` / `getUrl` / `convert` / `reconvert` / `delete` — per-entry rendition management
- `flavorParamsOutput.list` / `get` — actual output parameters used (may differ from input params)
- `mediaInfo.list` — technical metadata (codec info, dimensions, bitrate, duration)
- Transcoding workflow: upload → conversion profile selects flavor params → flavors created → status tracking
- Source-only and passthrough flavors
- Conditional flavors (create only if source meets criteria)

**Research needed:**
- Which `conversionProfile` and `flavorParams` actions are accessible with customer admin KS?
- Default conversion profiles per account — how are they assigned?
- `flavorAsset.convert` vs `flavorAsset.reconvert` — when to use each?
- Relationship between `flavorParams` (templates) and `flavorAsset` (instances)

**Dependencies:** Upload & Delivery (flavor assets already briefly mentioned)

**Estimated tests:** 25–35

---

### `KALTURA_CLIPPING_AND_TRIMMING_API.md`

**Why:** Video clipping (create a new entry from a segment) and trimming (modify in/out points) are among the most common video operations. Content Lab uses clipping, KMC exposes it, and the API enables automated highlight reels.

**Scope:**
- `media.addFromEntry` with `KalturaClipAttributes` in `operationAttributes` — create clip from existing entry
- `media.addFromFlavorAsset` — create entry from a specific flavor
- Clip attributes: `offset`, `duration`, `globalOffsetInDestination`
- Multi-segment concatenation — array of `operationAttributes` for stitching segments
- Content replacement workflow: `media.updateContent` → `media.approveReplace` / `media.cancelReplace`
- Trimming via content replacement (replace entry content with a trimmed version of itself)
- Effect operations: fade in/out via `KalturaEffectAttributes`

**Research needed:**
- Full `KalturaClipAttributes` field list
- Does `addFromEntry` preserve metadata, thumbnails, captions?
- Content replacement approval workflow — is it automatic or manual?
- Concatenation limits — max segments?
- Audio-only clipping support

**Dependencies:** Upload & Delivery (entry creation), Transcoding & Flavors (flavor-level clipping)

**Estimated tests:** 15–25

---

### ~~`KALTURA_THUMBNAIL_API.md`~~ — COMPLETED

**Status:** Published with 18 tests. Covers dynamic thumbnail URL (31 params), thumbAsset CRUD, thumbParams templates.

---

## Tier 2 — Next Guides (Planned Features)

### `KALTURA_LIVE_STREAMING_API.md`

**Why:** Live streaming is a core platform use case — RTMP/SRT ingest, simulive (pre-recorded as live), DVR, recording to VOD.

**Scope:**
- `liveStream.add` / `update` / `get` / `list` — live entry lifecycle
- Ingest protocols — RTMP primary/backup URLs, SRT configuration
- Simulive — schedule a VOD entry to play as live (`sourceType = LIVE_CHANNEL`)
- DVR — enable/configure DVR window
- Recording — `recordStatus`, automatic recording to VOD entry, `liveStreamEntry.recordedEntryId`
- Live-to-VOD workflow — recording completion, flavor conversion, entry linking
- Live transcoding profiles — `conversionProfileId` for adaptive bitrate
- Access control — geo-restriction, token auth for live streams
- Multi-region ingest — primary/backup streaming URLs
- `liveChannel` / `liveChannelSegment` — live channel playlists for linear programming
- `entryServerNode` — live entry connection tracking and monitoring
- `liveStats` — real-time viewer statistics

**Research needed:**
- Which `liveStream` actions are accessible with customer admin KS (not SERVICE_FORBIDDEN)?
- SRT ingest configuration — is it API-configurable or KMC-only?
- Simulive setup flow — does it use `liveStream` service or `scheduleEvent`?
- Recording concatenation behavior — how multiple recordings merge into one VOD entry
- Live captions via REACH (serviceFeature=8 LIVE_CAPTION) — integration with live stream
- `liveChannel` vs `liveStream` — when to use each

**Dependencies:** Transcoding & Flavors (live transcoding profiles), Player Embed (live playback), Scheduling (live event scheduling)

**Estimated tests:** 25–35

---

### `KALTURA_PLAYLIST_API.md`

**Why:** Content curation and sequenced playback. Playlists are used for player channels, auto-curated collections, and content hubs.

**Scope:**
- `playlist.add` / `update` / `get` / `delete` / `list` — CRUD
- Manual playlists — ordered list of entry IDs (`playlistContent` CSV)
- Dynamic playlists — filter rules (`KalturaMediaEntryFilterForPlaylist`), auto-updating
- `playlist.execute` — resolve a dynamic playlist to entries
- `playlist.executeFromContent` — execute with ad-hoc filter rules
- Playlist types — `STATIC_LIST` (3), `DYNAMIC` (10), `EXTERNAL` (101)
- Nesting — playlist entries within playlists
- Player integration — playlist player widget, continuous playback

**Research needed:**
- Full `playlistType` enum — which types are customer-accessible?
- Dynamic playlist filter capabilities — which filter fields are supported?
- `executeFromContent` vs `execute` — when to use each?
- Playlist player embed — does the Player v7 have a playlist plugin?
- Maximum entries per playlist — documented limits?

**Dependencies:** eSearch (filter rules use similar syntax), Player Embed (playlist playback)

**Estimated tests:** 15–20

---

### `KALTURA_SCHEDULING_API.md`

**Why:** Event scheduling for live sessions, webinars, recurring series. Ties together live streaming and virtual events.

**Scope:**
- `scheduleEvent.add` / `update` / `get` / `delete` / `list` — event lifecycle
- Event types — `RECORD_EVENT`, `LIVE_STREAM_EVENT`, `LIVE_REDIRECT_EVENT`, `VOD_EVENT`, `MEETING_EVENT`
- `scheduleResource.add` / `list` — resource management (cameras, rooms, encoders)
- `scheduleEventResource.add` — bind resources to events
- Recurring events — `recurrenceType`, `recurrence` object (RRULE-like), series management
- Conflict detection — `scheduleEvent.getConflicts` for resource booking
- Templates — `KalturaEntryScheduleEventBaseFilter` for batch operations
- Blackout windows — scheduling exclusion periods
- Integration with live entries — `templateEntryId` for live stream configuration

**Research needed:**
- Which `scheduleEvent` types are customer-accessible?
- Recurrence pattern syntax — is it iCal RRULE or custom?
- Conflict detection — does `getConflicts` work across resource types?
- How does scheduling connect to Events Platform events vs standalone live entries?
- `scheduleResource` types — camera, location, live entry — full enum

**Dependencies:** Live Streaming (scheduled live events), Events Platform (virtual event sessions), Categories (event categorization)

**Estimated tests:** 15–25

---

## Tier 3 — High-Impact Feature Areas

### `KALTURA_USER_ENTRY_API.md`

**Why:** Per-user engagement tracking: view history, watch later lists, quiz submissions, and playback progress. Powers "Continue Watching" and LMS features.

**Scope:**
- `userEntry.add` / `get` / `list` / `update` / `delete` / `bulkDelete` — user-entry lifecycle
- Entry types: `KalturaViewHistoryUserEntry`, `KalturaWatchLaterUserEntry`, `KalturaQuizUserEntry`, `KalturaRsvpUserEntry`
- View history — automatic tracking of last playback position, view count per user
- Watch later — user-curated lists
- Quiz submissions — `submitQuiz` action, scoring, attempts tracking
- Filtering — by user, entry, type, date range
- Privacy — per-user data scoping

**Research needed:**
- Which userEntry types are automatically created vs manually added?
- Quiz submission scoring — how does it integrate with the Quiz cue points?
- `KalturaRsvpUserEntry` — what triggers it?
- View history — is playback position tracked automatically by the player?

**Dependencies:** Quiz API (quiz submissions), Player Embed (automatic tracking)

**Estimated tests:** 15–20

---

### `KALTURA_DROP_FOLDER_API.md`

**Why:** Automated file ingestion from watched folders (FTP, SFTP, S3). The backbone of Zoom, Webex, and Teams integrations. Critical for enterprise bulk ingestion and migration workflows.

**Scope:**
- `dropFolder.add` / `update` / `get` / `list` / `delete` — drop folder lifecycle
- `dropFolderFile.add` / `get` / `list` / `update` / `updateStatus` / `delete` — file tracking
- Folder types: `LOCAL`, `FTP`, `SFTP`, `SCP`, `S3`, `WEBEX`, `ZOOM`
- File handling modes: `ADD_AS_NEW`, `MATCH_EXISTING_OR_ADD_AS_NEW`, `MATCH_EXISTING_OR_KEEP_IN_FOLDER`
- Ingestion rules: XML metadata files, CSV bulk, content matching
- Zoom integration architecture — how Zoom recordings auto-ingest via drop folder
- S3 drop folders — bucket configuration, IAM policies, event triggers

**Research needed:**
- Which drop folder types are customer-configurable via API vs admin-only?
- S3 drop folder setup — full configuration fields
- Zoom drop folder — is it API-manageable or provisioned by Kaltura support?
- File status lifecycle: `UPLOADING` → `PENDING` → `HANDLED` / `ERROR`

**Dependencies:** Upload & Delivery (content creation), Custom Metadata (XML ingestion)

**Estimated tests:** 15–20

---

### `KALTURA_INTERACTIVE_VIDEO_API.md`

**Why:** Branching/interactive video where viewers choose paths through hotspots. A major differentiating product feature with a dedicated interactivity plugin, node-based graph editor, and analytics.

**Scope:**
- Interactivity data model — nodes, paths, decision points
- `interactivity` plugin — get/update interactivity data for an entry
- `volatileInteractivity` — runtime state during playback
- Hotspot-based branching — clickable regions that navigate to different video segments
- Path analytics — which branches viewers chose
- Player plugin configuration for interactive playback
- Creating interactive video programmatically vs via the editor UI

**Research needed:**
- Is the interactivity API customer-facing or editor-only?
- Interactivity data format — JSON structure for nodes and paths
- Can interactive videos be created purely via API or does it require the editor?
- Analytics integration — how are path choices tracked?

**Dependencies:** Player Embed (interactivity plugin), Cue Points (hotspot cue points)

**Estimated tests:** 10–15

---

### `KALTURA_DRM_API.md`

**Why:** Multi-DRM content protection (Widevine, FairPlay, PlayReady) via Kaltura's uDRM module. Required for any customer with premium/protected content.

**Scope:**
- `drmProfile.add` / `update` / `get` / `list` — DRM profile configuration
- `drmPolicy` — licensing rules and restrictions
- Supported DRM systems: Google Widevine, Apple FairPlay, Microsoft PlayReady
- License acquisition flow — how the player obtains DRM licenses
- Content encryption — flavor-level encryption configuration
- Access control integration — DRM + geo-restriction + token auth
- Player configuration for DRM playback

**Research needed:**
- Which DRM actions are customer-configurable vs Kaltura-provisioned?
- License server URLs — per-region configuration
- FairPlay certificate management — API-driven?
- Offline DRM (download + protect) support

**Dependencies:** Transcoding & Flavors (encrypted flavors), Player Embed (DRM playback), Access Control

**Estimated tests:** 10–15

---

### `KALTURA_ENGAGEMENT_API.md`

**Why:** Social engagement features — likes, ratings, and polls — that drive viewer interaction. Polls are a key feature in live events and webcasting.

**Scope:**
- `like.like` / `unlike` / `checkLikeExists` / `list` — thumbs up/down per entry
- `rating.rate` / `getRating` / `removeRating` / `checkRating` — 1–5 star ratings
- `poll.add` / `vote` / `getVote` / `getVotes` / `resetVotes` — real-time polling
- Poll integration with live events and webcasting
- Like/rating aggregation in analytics

**Research needed:**
- Are likes per-user-per-entry or global?
- Poll persistence — cache-based or database?
- Poll integration with Events Platform — automatic or manual?
- Rating display in player — plugin configuration

**Dependencies:** Events Platform (polls in live events), Player Embed (engagement plugins)

**Estimated tests:** 15–20

---

## Tier 4 — Important Additions to Existing Guides

These don't need standalone guides but should be added to existing ones.

### Extend `KALTURA_API_GETTING_STARTED.md`

| Feature | Services | Description |
|---------|----------|-------------|
| **Response Profiles** | `responseProfile` (add/get/list/delete/recalculate) | Control API response shape — include related objects, restrict fields, enable joins. Major efficiency tool for any integration. |
| **BaseEntry Power Ops** | `baseEntry.clone`, `getContextData`, `getPlaybackContext`, `listByReferenceId` | Clone entries, evaluate access control rules, get advanced playback sources, lookup by referenceId. |
| **Short Links** | `shortLink` (add/get/list/update/delete/goto) | URL shortening for shareable content links. |
| **Export to CSV** | `exportCsv.serveCsv` | Bulk export of platform data for reporting. |

### Extend `KALTURA_USER_MANAGEMENT_API.md`

| Feature | Services | Description |
|---------|----------|-------------|
| **Group Management** | `groupUser` (add/delete/list/sync/update) | Group membership management. Groups are used for bulk entitlement, channel membership, and integration group syncing (Zoom/SAML). Users can belong to up to 1,024 groups. |
| **Advanced Permissions** | `permission` (add/get/list/update/delete/getCurrentPermissions), `permissionItem` (add/get/list/update/delete) | Fine-grained action-level RBAC beyond userRole. |
| **App-Specific Roles** | `userAppRole` | Application-specific user roles for multi-app deployments. |

### Extend `KALTURA_PLAYER_EMBED_GUIDE.md`

| Feature | Services | Description |
|---------|----------|-------------|
| **UiConf Management** | `uiConf` (add/clone/get/list/update/delete/listTemplates) | Programmatic player configuration management. Every player embed references a uiConf ID. |

### Extend `KALTURA_CAPTIONS_AND_TRANSCRIPTS_API.md`

| Feature | Services | Description |
|---------|----------|-------------|
| **Caption Search** | `captionAssetItem` (search/searchEntries/parse/list) | Search within caption text across entries. Full-text search for words/phrases in video captions. |
| **Caption Params** | `captionParams` (add/get/list/update/delete) | Caption generation parameter templates. |

### Extend `KALTURA_ANALYTICS_REPORTS_API.md`

| Feature | Services | Description |
|---------|----------|-------------|
| **CSV Export** | `exportCsv` | Bulk report export to CSV. |

---

## Tier 5 — Specialized / Niche

These serve specific enterprise use cases. Document only if customer demand warrants it.

### `KALTURA_CONTENT_LIFECYCLE_API.md`

**Why:** The `scheduledTaskProfile` service is the backend engine for KMC's Automation Manager — rule-based automated actions on content (delete after X days, change status, move categories, trigger REACH). Complements the Agents Manager guide.

**Services:** `scheduledTaskProfile` (add/delete/get/getDryRunResults/list/requestDryRun/update)

**Status:** DEFERRED — overlaps with Agents Manager; research whether this adds unique capabilities.

---

### `KALTURA_EXTERNAL_MEDIA_API.md`

**Why:** Manage entries that reference externally-hosted video (YouTube, Vimeo URLs) without re-hosting in Kaltura. Unified catalog across sources.

**Services:** `externalMedia` (add/count/delete/get/list/update)

**Status:** DEFERRED — niche use case for mixed-source catalogs.

---

### `KALTURA_AUDIT_TRAIL_API.md`

**Why:** Track all API actions on the account — who changed what, when. Compliance requirement for regulated enterprises.

**Services:** `auditTrail` (add/list)

**Status:** DEFERRED — compliance-specific, limited API surface.

---

### Delivery Profiles Guide

**Why:** CDN configuration, custom delivery profiles, serving rules. Relevant for customers with multi-CDN setups or custom domain requirements.

**Services:** `deliveryProfile.add` / `list` / `get`, `storageProfile`, flavor serving rules

**Status:** DEFERRED — highly specialized, most customers use default delivery.

---

### File Assets & Document Entries

**Why:** Non-media content management — `fileAsset` service, `KalturaDataEntry`, `KalturaDocumentEntry` types. Data entries for application storage, document entries for PDF/PPT hosting.

**Services:** `fileAsset.add` / `serve`, `data.add` / `serve`, `document.addFromUrl`

**Status:** DEFERRED — research suggests more widely used than assumed. Elevate if customer demand warrants.

---

### Batch Operations Guide

**Why:** Bulk content ingestion via CSV/XML — `bulkUpload.add`, `batchJob` monitoring. The general bulk upload workflow for entries, categories, users, and metadata.

**Services:** `bulkUpload.add` / `get` / `list` / `abort`

**Status:** DEFERRED — CSV format varies by object type. Needs systematic testing of each format.

---

### Virus Scan Profiles

**Why:** Automatic virus scanning of uploaded content before processing. ClamAV integration.

**Services:** `virusScanProfile` (add/delete/get/list/update)

**Status:** DEFERRED — enterprise security feature, typically admin-configured.

---

## Not Documented (By Design)

These are internal/infrastructure services, legacy/deprecated, or not customer-facing:

| Category | Services |
|----------|----------|
| **Internal infrastructure** | batch, batchcontrol, jobs, serverNode, fileSync, confMaps, systemPartner, varConsole, xInternal, metadataBatch, contentDistributionBatch |
| **Legacy/deprecated** | accessControl (→ accessControlProfile), adminUser (→ user+session), notification (→ eventNotificationTemplate), search (→ eSearch), upload (→ uploadToken), widget (→ uiConf+Player v7), mixing (obsolete), captureSpace (discontinued) |
| **Niche distribution connectors** | attUverse, avn, comcastMrss, ndn, synacorHbo, timeWarner, tvCom, unicorn, uverse (covered by generic Distribution framework) |
| **Specialized integrations** | pexip (SIP bridge), sharepointExtension, conference (SIP rooms), emailIngestionProfile |
| **Meta/schema** | schema, system (ping/getTime only) |


## API Landscape Reference

100+ REST API services. Grouped by developer need:

### Core Platform
- **Upload & Ingest** — `uploadToken`, `media.add`, `media.addContent`, `bulkUpload`, chunked/resumable uploads
- **Transcoding & Flavors** — `conversionProfile`, `flavorParams`, `flavorAsset`, `flavorParamsOutput`, `mediaInfo`
- **Content Delivery** — `playManifest` (HLS/DASH), thumbnail API, flavor assets, CDN profiles
- **Thumbnails** — `thumbAsset`, `thumbParams`, URL transformation API
- **Clipping & Trimming** — `media.addFromEntry` + `KalturaClipAttributes`, content replacement workflow
- **AppTokens & Auth** — `appToken.add/startSession`, secure server-to-server auth
- **User & Group Management** — `user.add/list/get`, `userRole`, `groupUser`, `permission`, groups, RBAC
- **Category & Organization** — `category`, `categoryUser`, `categoryEntry`, hierarchical taxonomy
- **Custom Metadata** — `metadataProfile` (XSD schemas), `metadata` (per-entry structured data)
- **Playlists** — `playlist.add/get/update`, manual + dynamic playlists
- **Caption Management** — `captionAsset` CRUD, `captionAssetItem` (search), SRT/VTT/DFXP
- **Access Control** — `accessControlProfile`, geo/IP/domain restrictions, scheduling rules
- **DRM** — `drmProfile`, `drmPolicy`, Widevine/FairPlay/PlayReady licensing
- **Response Profiles** — `responseProfile`, efficient API responses with field selection and joins

### Live & Events
- **Virtual Events Platform** — REST API at `events-api.{region}.ovp.kaltura.com` (OAS 3.0), event/session lifecycle, teams, templates. Has [MCP server](https://github.com/kaltura/mcp-events). Multi-region: NVP1, IRP2, FRP2
- **Live Streaming** — `liveStream.add/update`, `liveChannel`, RTMP/SRT ingest, simulive, recording to VOD
- **Scheduling** — `scheduleEvent`, `scheduleResource`, recurring events, resource booking
- **Rooms/Virtual Classroom** — No REST API (LTI/UI only)

### AI & Intelligence
- **AI Genie** — `/mcp/search`, `/assistant/converse`, `/assistant/ws`, threads, feedback, streaming RAG
- **REACH Services** — 22+ enrichment services: captions, translation, dubbing, clips, quiz, summary, moderation, 80+ languages, machine + human vendors
- **Agents Manager** — Automated content-processing agents with triggers + actions
- **Virtual Avatar** — AI avatars via `@unisphere/models-sdk-js`, WebRTC streaming, conversational AI

### Engagement & Interactivity
- **User Entry** — `userEntry` (view history, watch later, quiz submissions, progress tracking)
- **Interactive Video** — Branching paths, hotspot navigation, node-based interactivity graphs
- **Likes & Ratings** — `like`, `rating` (social engagement tracking)
- **Polls** — `poll` (real-time polling in live events)
- **Gamification** — Leaderboards, badges, certificates, lead scoring

### Integration & Automation
- **Webhooks** — `eventNotificationTemplate`, HTTP POST callbacks on entry events
- **Distribution Connectors** — `distributionProfile`, syndicate to YouTube/Facebook/etc.
- **Drop Folders** — `dropFolder`, `dropFolderFile`, automated ingestion (FTP/S3/Zoom/Webex)
- **Batch Operations** — `bulkUpload`, CSV/XML batch ingestion
- **Content Lifecycle** — `scheduledTaskProfile`, rule-based automation (delete, status change, REACH trigger)

### Analytics & Reporting
- **Analytics Reports** — `report.getTable/getTotal/getGraphs`, engagement metrics, heatmaps
- **Events Collection** — `stats.collect`, beacon API, real-time event tracking
- **Live Reports** — `liveReports.getEvents`, real-time viewer counts (subsection of Analytics Reports)
- **Audit Trail** — `auditTrail`, compliance logging of all API actions

### Experiences
- **Player Embed** — Player v7 setup, `uiConf` management, plugins, runtime API, multi-stream, side panels
- **Unisphere Framework** — Micro-frontend loader, workspace/runtime/visual lifecycle, 15 widgets, 33 runtimes, multi-region CDN
- **Experience Components** — Express Recorder, Captions Editor, Genie Widget, Media Manager, Content Lab, Agents Widget, VOD Avatar Studio, Conversational Avatar, CnC, Embeddable Analytics

### Platform & Admin
- **OTT/TV Platform** — Separate API for TVOD/SVOD apps (out of scope)
- **Moderation** — Content flagging, approval workflows, AI moderation via REACH
- **Multi-Account** — Parent-child account hierarchy, template management
- **Short Links** — `shortLink`, URL shortening for shareable content
- **External Media** — `externalMedia`, catalog entries referencing externally-hosted video
- **Client SDKs** — Auto-generated: PHP, Java, JavaScript, Python, Go, Ruby, C#


## Execution Pattern (for each guide)

1. Research API surface (live exploration + docs)
2. Verify accessibility — test every action with customer admin KS before documenting
3. Write guide with curl examples using shell variables
4. Create test file validating every documented endpoint
5. Run tests against live API — if test fails, guide is wrong
6. Update cross-references (GUIDE_MAP.md, AGENTS.md, README.md, context7.json, llms.txt, SKILL.md)
7. Commit with conventional format: `feat(scope): description`

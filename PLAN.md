# Kaltura API Guides — Roadmap

**Current state:** 40 guides, 828 live-tested assertions, 4-tier flywheel structure.  
Completed guide details are in [README.md](README.md). Test inventory is in each `tests/test_*.py` file.


## Next Guides

### `KALTURA_LIVE_STREAMING_API.md`

**Why:** Live streaming is a core platform use case — RTMP/SRT ingest, simulive (pre-recorded as live), DVR, recording to VOD. Currently undocumented.

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

**Research needed:**
- Which `liveStream` actions are accessible with customer admin KS (not SERVICE_FORBIDDEN)?
- SRT ingest configuration — is it API-configurable or KMC-only?
- Simulive setup flow — does it use `liveStream` service or `scheduleEvent`?
- Recording concatenation behavior — how multiple recordings merge into one VOD entry
- Live captions via REACH (serviceFeature=8 LIVE_CAPTION) — integration with live stream

**Dependencies:** Upload & Delivery (flavor profiles), Player Embed (live playback), Scheduling (live event scheduling)

**Estimated tests:** 20–30 (create/configure live entry, ingest URL generation, recording config, simulive setup, live-to-VOD)

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

**Estimated tests:** 15–20 (CRUD, static vs dynamic, execute, filters, paging)

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

**Estimated tests:** 15–25 (event CRUD, recurring patterns, resource booking, conflict detection)


## Deferred

These require specialized research or have limited customer-facing API surface.

### Delivery Profiles Guide

**Why:** CDN configuration, custom delivery profiles, serving rules. Relevant for customers with multi-CDN setups or custom domain requirements.

**Services:** `deliveryProfile.add` / `list` / `get`, `storageProfile`, flavor serving rules

**Status:** DEFERRED — highly specialized, most customers use default delivery. Only relevant for enterprise CDN configurations.

---

### File Assets & Document Entries

**Why:** Non-media content management — `fileAsset` service, `KalturaDataEntry`, `KalturaDocumentEntry` types. Used for PDF hosting, data attachments, and non-video file management.

**Services:** `fileAsset.add` / `serve`, `data.add`, `document.addFromUrl`

**Status:** DEFERRED — requires backend analysis to understand how `fileAsset` differs from `attachmentAsset` in permission model, serving, and storage. Limited customer use.

---

### Batch Operations Guide

**Why:** Bulk content ingestion via CSV/XML — `bulkUpload.add`, `batchJob` monitoring. Currently documented as a subsection within Categories & Access Control (category member bulk import) but the general bulk upload workflow is undocumented.

**Services:** `bulkUpload.add` / `get` / `list` / `abort`, `batchJob.getExclusiveAlmostDone`

**Status:** DEFERRED — bulk upload CSV format varies by object type (entries, categories, users, metadata). Needs systematic testing of each format.


## API Landscape Reference

100+ REST API services. Grouped by developer need:

### Core Platform
- **Upload & Ingest** — `uploadToken`, `media.add`, `media.addContent`, `bulkUpload`, chunked/resumable uploads
- **Content Delivery** — `playManifest` (HLS/DASH), thumbnail API, flavor assets, CDN profiles
- **AppTokens & Auth** — `appToken.add/startSession`, secure server-to-server auth
- **User & Group Management** — `user.add/list/get`, `userRole`, groups, RBAC
- **Category & Organization** — `category`, `categoryUser`, `categoryEntry`, hierarchical taxonomy
- **Custom Metadata** — `metadataProfile` (XSD schemas), `metadata` (per-entry structured data)
- **Playlists** — `playlist.add/get/update`, manual + dynamic playlists
- **Caption Management** — `captionAsset` CRUD, SRT/VTT/DFXP, search within captions
- **Access Control** — `accessControlProfile`, geo/IP/domain restrictions, scheduling rules

### Live & Events
- **Virtual Events Platform** — REST API at `events-api.{region}.ovp.kaltura.com` (OAS 3.0), event/session lifecycle, teams, templates. Has [MCP server](https://github.com/kaltura/mcp-events). Multi-region: NVP1, IRP2, FRP2
- **Live Streaming** — `liveStream.add/update`, RTMP/SRT ingest, simulive, recording to VOD
- **Scheduling** — `scheduleEvent`, `scheduleResource`, recurring events, resource booking
- **Rooms/Virtual Classroom** — No REST API (LTI/UI only)

### AI & Intelligence
- **AI Genie** — `/mcp/search`, `/assistant/converse`, streaming RAG answers
- **REACH Services** — 22+ enrichment services: captions, translation, dubbing, clips, quiz, summary, moderation, 80+ languages, machine + human vendors
- **Agents Manager** — Automated content-processing agents with triggers + actions
- **Virtual Avatar** — AI avatars via `@unisphere/models-sdk-js`, WebRTC streaming, conversational AI

### Integration & Automation
- **Webhooks** — `eventNotificationTemplate`, HTTP POST callbacks on entry events
- **Distribution Connectors** — `distributionProfile`, syndicate to YouTube/Facebook/etc.
- **Batch Operations** — `bulkUpload`, `batchJob`, CSV/XML batch ingestion

### Analytics & Reporting
- **Analytics Reports** — `report.getTable/getTotal/getGraphs`, engagement metrics, heatmaps
- **Events Collection** — `stats.collect`, beacon API, real-time event tracking
- **Live Reports** — `liveReports.getEvents`, real-time viewer counts (subsection of Analytics Reports)

### Experiences
- **Player Embed** — Player v7 setup, plugins, runtime API, multi-stream, side panels
- **Unisphere Framework** — Micro-frontend loader, workspace/runtime/visual lifecycle, 15 widgets, 33 runtimes, multi-region CDN
- **Experience Components** — Express Recorder, Captions Editor, Genie Widget, Media Manager, Content Lab, Agents Widget, VOD Avatar Studio, Conversational Avatar, CnC, Embeddable Analytics

### Platform & Admin
- **OTT/TV Platform** — Separate API for TVOD/SVOD apps (out of scope)
- **Moderation** — Content flagging, approval workflows, AI moderation via REACH
- **Multi-Account** — Parent-child account hierarchy, template management
- **Client SDKs** — Auto-generated: PHP, Java, JavaScript, Python, Go, Ruby, C#


## Execution Pattern (for each guide)

1. Research API surface (live exploration + docs)
2. Verify accessibility — test every action with customer admin KS before documenting
3. Write guide with curl examples using shell variables
4. Create test file validating every documented endpoint
5. Run tests against live API — if test fails, guide is wrong
6. Update cross-references (GUIDE_MAP.md, AGENTS.md, README.md, context7.json, llms.txt, SKILL.md)
7. Commit with conventional format: `feat(scope): description`

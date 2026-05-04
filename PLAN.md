# Kaltura API Guides — Roadmap

**Current state:** 50 guides, 960+ live-tested assertions, 1 playbook.  
Completed guide details: [README.md](README.md). Playbook plan: [playbooks/PLAYBOOK_PLAN.md](playbooks/PLAYBOOK_PLAN.md).

---

## Guide Gaps (Prioritized)

| # | Guide | Priority |
|---|-------|----------|
| 1 | Transcoding & Flavors | **Critical** |
| 2 | Player Configuration (uiConf) | **Critical** |
| ~~3~~ | ~~Clipping & Trimming~~ | ~~**Critical**~~ — **Done** as [Video Editing API](KALTURA_VIDEO_EDITING_API.md) |
| 4 | Live Streaming | **High** |
| 5 | DRM / Content Protection | **High** |
| 6 | Playlist | Medium |
| 7 | Scheduling | Medium |
| 8 | Drop Folder / Automated Ingest | Medium |

---

## Planned Guide Scopes

### `KALTURA_TRANSCODING_AND_FLAVORS_API.md`

Transcoding profile lifecycle, flavor params (codec/bitrate/resolution), per-entry flavor asset management, processing status tracking, source-only/passthrough/conditional flavors, mediaInfo.

**Estimated tests:** 25–35

### `KALTURA_PLAYER_CONFIGURATION_API.md`

uiConf CRUD, templates, cloning, plugin management, configuration JSON structure, per-embed overrides, domain whitelisting, player versioning, common configuration templates (mobile, accessibility, kiosk, dual-screen, ad-supported).

Complements the existing Player Embed guide (which covers embedding; this covers server-side configuration management).

**Estimated tests:** 20–25

### ~~`KALTURA_CLIPPING_AND_TRIMMING_API.md`~~ → Completed as `KALTURA_VIDEO_EDITING_API.md`

Expanded scope: trim, clip, multi-clip concat, overlay (PiP), chroma-key background replacement, nested composition, caption burn-in, fade effects, dimension control, audio mixing, waveform visualization.

**Actual tests:** 18

### `KALTURA_LIVE_STREAMING_API.md`

Live entry lifecycle, RTMP/SRT ingest, simulive, DVR, recording to VOD, access control for live, `entryServerNode` monitoring, `liveStats`.

**Estimated tests:** 25–35

### `KALTURA_DRM_API.md`

DRM profile configuration (Widevine, FairPlay, PlayReady), license acquisition flow, flavor-level encryption, access control integration.

**Estimated tests:** 10–15

### `KALTURA_PLAYLIST_API.md`

Playlist CRUD, manual (ordered entry IDs) vs dynamic (filter rules), `playlist.execute`, player integration.

**Estimated tests:** 15–20

### `KALTURA_SCHEDULING_API.md`

Schedule event lifecycle, event types, schedule resources, recurring events, conflict detection, live entry integration via `templateEntryId`.

**Estimated tests:** 15–25

### `KALTURA_DROP_FOLDER_API.md`

Drop folder lifecycle, file tracking, folder types (LOCAL, FTP, SFTP, S3, WEBEX, ZOOM), file handling modes, Zoom/Webex architecture, S3 event triggers.

**Estimated tests:** 15–20

---

## Existing Guide Extensions (Tier 4)

| Guide | Addition |
|-------|----------|
| Getting Started | Response Profiles, BaseEntry power ops, Short Links, CSV Export |
| User Management | Group Management, Advanced Permissions, App-Specific Roles |
| Player Embed | Cross-reference to Player Configuration, mobile optimization |
| Captions & Transcripts | Caption Search (`captionAssetItem`), Caption Params |
| Analytics Reports | CSV Export, Scheduled delivery, Custom date ranges |
| REACH | Automation rule troubleshooting, Credit monitoring |
| Access Control | DRM integration, CORS/domain whitelisting |
| Events Platform | Analytics export, Registration troubleshooting |

---

## Deferred / Evaluate

| Guide | Status | Notes |
|-------|--------|-------|
| Content Lifecycle | Deferred | Overlaps with Agents Manager |
| External Media | Deferred | Niche use case |
| Audit Trail | Evaluate | Legal compliance demand |
| Bulk Operations | Evaluate | Migration playbook dependency |
| Delivery Profiles | Deferred | Default delivery sufficient for most |
| User Entry | Evaluate | Powers quiz submissions + "Continue Watching" |
| Interactive Video | Evaluate | Branching/hotspot interactivity |
| Engagement (likes/polls) | Evaluate | Live event engagement features |

---

## API Landscape Reference

100+ REST API services grouped by developer need:

### Core Platform
- **Upload & Ingest** — `uploadToken`, `media.add`, `bulkUpload`, chunked uploads
- **Transcoding & Flavors** — `conversionProfile`, `flavorParams`, `flavorAsset`, `mediaInfo`
- **Content Delivery** — `playManifest` (HLS/DASH), thumbnail API, CDN profiles
- **Thumbnails** — `thumbAsset`, `thumbParams`, URL transformation API
- **Clipping & Trimming** — `media.addFromEntry` + `KalturaClipAttributes`
- **AppTokens & Auth** — `appToken.add/startSession`, secure session management
- **User & Group Management** — `user`, `userRole`, `groupUser`, `permission`, RBAC
- **Categories** — `category`, `categoryUser`, `categoryEntry`, hierarchy + entitlements
- **Custom Metadata** — `metadataProfile` (XSD), `metadata` (per-entry structured data)
- **Playlists** — `playlist` (manual + dynamic)
- **Captions** — `captionAsset` CRUD, `captionAssetItem` (search), SRT/VTT/DFXP
- **Player Configuration** — `uiConf` CRUD, templates, plugins, versioning
- **Access Control** — `accessControlProfile`, geo/IP/domain restrictions
- **DRM** — `drmProfile`, Widevine/FairPlay/PlayReady
- **LTI Integration** — KAF, LTI 1.1/1.3, deep linking, AGS, NRPS, Caliper

### Live & Events
- **Events Platform** — REST API (`events-api.{region}.ovp.kaltura.com`), event/session lifecycle
- **Live Streaming** — `liveStream`, RTMP/SRT, simulive, DVR, recording
- **Scheduling** — `scheduleEvent`, `scheduleResource`, recurring events
- **Rooms** — LTI/UI only (no REST API)

### AI & Intelligence
- **AI Genie** — RAG-based search, threads, streaming, feedback
- **REACH** — 22+ enrichment services, machine + human, 80+ languages
- **Agents Manager** — Automated content-processing (triggers + actions)
- **Avatar** — Conversational + VOD avatars

### Engagement & Interactivity
- **User Entry** — View history, watch later, quiz submissions
- **Interactive Video** — Branching paths, hotspot navigation
- **Likes/Ratings/Polls** — Social engagement
- **Gamification** — Leaderboards, badges, certificates

### Integration & Automation
- **Webhooks** — `eventNotificationTemplate`, HTTP callbacks
- **Distribution** — `distributionProfile`, syndicate to YouTube/Facebook/FTP
- **Drop Folders** — `dropFolder`, automated ingest (FTP/S3/Zoom/Webex)
- **Bulk Operations** — `bulkUpload`, CSV/XML batch ingestion

### Analytics & Reporting
- **Analytics Reports** — `report.getTable/getTotal/getGraphs`, engagement metrics
- **Events Collection** — `stats.collect`, beacon API, real-time tracking
- **Audit Trail** — `auditTrail`, compliance logging

### Experiences
- **Player Embed** — Player v7, plugins, runtime API
- **Unisphere Framework** — Micro-frontend loader, 15 widgets, multi-region CDN
- **Experience Components** — Express Recorder, Captions Editor, Genie Widget, Media Manager, Content Lab, Agents Widget, VOD Avatar, Conversational Avatar, CnC, Analytics Embed

# Kaltura API Guides — Master Plan & Roadmap

## Completed Guides

| # | Guide | Tests | Status |
|---|-------|-------|--------|
| 1 | `KALTURA_SESSION_GUIDE.md` | `test_session_api.py` (13 tests) | Done |
| 2 | `KALTURA_ESEARCH_API.md` | `test_esearch_api.py` (19 tests) | Done |
| 3 | `KALTURA_PLAYER_EMBED_GUIDE.md` | `test_player_embed_api.py` (14 tests) | Done |
| 4 | `KALTURA_REACH_API.md` (+ AI Clips workflow) | `test_reach_api.py` (32 tests), `test_clips_api.py` (15 tests) | Done |
| 5 | `KALTURA_AGENTS_MANAGER_API.md` | `test_agents_manager_api.py` (15 tests) | Done |
| 6 | `KALTURA_AI_GENIE_API.md` | `test_genie_api.py` (17 tests) | Done |
| 7 | `KALTURA_UPLOAD_AND_DELIVERY_API.md` | `test_upload_delivery_api.py` (34 tests) | Done |
| 8 | `KALTURA_APPTOKENS_API.md` | `test_apptokens_api.py` (17 tests) | Done |
| 9 | `KALTURA_EVENTS_PLATFORM_API.md` | `test_events_platform_api.py` (25 tests) | Done |
| 10 | `KALTURA_MULTI_STREAM_API.md` | `test_multi_stream_api.py` (23 tests) | Done |
| 11 | `KALTURA_APP_REGISTRY_API.md` | `test_app_registry_api.py` (20 tests) | Done |
| 12 | `KALTURA_USER_PROFILE_API.md` | `test_user_profile_api.py` (30 tests) | Done |
| 13 | `KALTURA_MESSAGING_API.md` | `test_messaging_api.py` (22 tests) | Done |
| 14 | `KALTURA_WEBHOOKS_API.md` | `test_webhooks_api.py` (34 tests) | Done |
| 15 | `KALTURA_USER_MANAGEMENT_API.md` | `test_user_management_api.py` (25 tests) | Done |
| 16 | `KALTURA_AUTH_BROKER_API.md` | `test_auth_broker_api.py` (13 tests) | Done |
| 17 | `KALTURA_CATEGORIES_AND_ACCESS_CONTROL_API.md` | `test_categories_access_control_api.py` (28 tests) | Done |
| 18 | `KALTURA_CUSTOM_METADATA_API.md` | `test_custom_metadata_api.py` (24 tests) | Done |
| 19 | `KALTURA_CAPTIONS_AND_TRANSCRIPTS_API.md` | `test_captions_transcripts_api.py` (36 tests) | Done |
| 20 | `KALTURA_ANALYTICS_REPORTS_API.md` | `test_analytics_reports_api.py` (35 tests) | Done |
| 21 | `KALTURA_ANALYTICS_EVENTS_COLLECTION_API.md` | `test_analytics_events_collection_api.py` (16 tests) | Done |
| 22 | `KALTURA_GAMIFICATION_API.md` | `test_gamification_api.py` (47 tests) | Done |
| 23 | `KALTURA_DISTRIBUTION_API.md` | `test_distribution_api.py` (41 tests), `test_distribution_profiles_e2e.py` (43 tests) | Done |
| 24 | `KALTURA_SYNDICATION_API.md` | `test_syndication_api.py` (14 tests) | Done |
| 25 | `KALTURA_API_GETTING_STARTED.md` | `test_getting_started_api.py` (13 tests) | Done |
| 26 | `KALTURA_EXPERIENCE_COMPONENTS_API.md` | `test_experience_components_api.py` (7 tests), `test_experience_components_e2e.py` (19 tests) | Done |
| 27 | `KALTURA_MULTI_ACCOUNT_MANAGEMENT_API.md` | `test_multi_account_api.py` (6 tests) | Done |
| 28 | `KALTURA_UNISPHERE_FRAMEWORK_API.md` | `test_unisphere_framework_api.py` (12 tests), `test_unisphere_framework_e2e.py` (9 tests) | Done |
| 29 | `KALTURA_MEDIA_MANAGER_API.md` | `test_media_manager_api.py` (11 tests) | Done |
| 30 | `KALTURA_CONTENT_LAB_API.md` | `test_content_lab_api.py` (9 tests) | Done |
| 31 | `KALTURA_AGENTS_WIDGET_API.md` | `test_agents_widget_api.py` (7 tests) | Done |
| 32 | `KALTURA_VOD_AVATAR_API.md` | `test_vod_avatar_api.py` (6 tests) | Done |
| 33 | `KALTURA_EXPRESS_RECORDER_API.md` | — (browser recording embed) | Done |
| 34 | `KALTURA_CAPTIONS_EDITOR_API.md` | — (iframe embed) | Done |
| 35 | `KALTURA_CONVERSATIONAL_AVATAR_API.md` | — (iframe/SDK embed) | Done |
| 36 | `KALTURA_CNC_API.md` | — (Events Platform component) | Done |
| 37 | `KALTURA_GENIE_WIDGET_API.md` | `test_genie_widget_api.py` (7 tests) | Done |
| 38 | `KALTURA_ANALYTICS_EMBED_API.md` | — (iframe embed) | Done |


## Full Kaltura API Landscape

100+ REST API services discovered. Grouped by developer need:

### Core Platform (foundation every integration needs)
- **Upload & Ingest** — `uploadToken`, `media.add`, `media.addContent`, `bulkUpload`, chunked/resumable uploads
- **Content Delivery** — `playManifest` (HLS/DASH), thumbnail API, flavor assets, CDN profiles
- **AppTokens & Auth** — `appToken.add/startSession`, secure server-to-server auth without admin secrets
- **User & Group Management** — `user.add/list/get`, `userRole`, groups, RBAC permissions
- **Category & Organization** — `category`, `categoryUser`, `categoryEntry`, hierarchical content taxonomy
- **Custom Metadata** — `metadataProfile` (XSD schemas), `metadata` (per-entry structured data)
- **Playlists** — `playlist.add/get/update`, manual + dynamic/rule-based playlists
- **Caption Management** — `captionAsset` CRUD, upload SRT/VTT/DFXP, search within captions
- **Access Control** — `accessControlProfile`, geo/IP/domain restrictions, scheduling rules

### Live & Events
- **Virtual Events Platform** — Dedicated REST API at `events-api.nvp1.ovp.kaltura.com` (OAS 3.0). Full event lifecycle: create/update/delete events, manage sessions (Interactive Room, LiveWebcast, SimuLive, VirtualLearningRoom), team members, speakers, templates, duplication. Auth via `Bearer KS`. Has an official MCP server: [kaltura/mcp-events](https://github.com/kaltura/mcp-events). Multi-region: NVP (prod), EU (IRP), DE (FRP).
- **Live Streaming** — `liveStream.add/update`, RTMP/SRT ingest, simulive (pre-recorded as live)
- **Scheduling** — `scheduleEvent`, `scheduleResource`, recurring events, resource booking
- **Rooms/Virtual Classroom** — No REST API (LTI/UI only)

### AI & Intelligence
- **AI Genie** — `/mcp/search`, `/assistant/converse`, streaming RAG answers (DONE)
- **REACH Services** — Captions, translation, dubbing, clips, quiz, summary, moderation (DONE)
- **Agents Manager** — Automated content-processing agents with triggers + actions (DONE)
- **Virtual Avatar** — AI avatars via `@unisphere/models-sdk-js`, WebRTC streaming, conversational AI

### Integration & Automation
- **Event Notifications / Webhooks** — `eventNotificationTemplate`, HTTP POST callbacks on entry events
- **Distribution Connectors** — `distributionProfile`, syndicate to YouTube/Facebook/etc.
- **Batch Operations** — `bulkUpload`, `batchJob`, CSV/XML batch ingestion

### Analytics & Reporting
- **Analytics** — `report.getTable/getTotal/getGraphs`, engagement metrics, heatmaps
- **Statistics** — Usage stats, viewer counts, bandwidth

### Advanced Features
- **Interactive Video** — Paths (branching), hotspots, in-video quizzes (limited REST API, mostly UI)
- **DRM & Content Protection** — `drmProfile`, license management, encryption
- **Clip/Trim** — `baseEntry.clone` + `KalturaClipAttributes` (documented in REACH guide)

### Platform & Admin
- **OTT/TV Platform** — Separate API for TVOD/SVOD apps (EPG, device management, channels)
- **Moderation** — Content flagging, approval workflows (limited dedicated API)
- **Client SDKs** — Auto-generated: PHP, Java, JavaScript, Python, Go, Ruby, C#
- **Unisphere** — Micro-frontend framework for composable Kaltura-embedded experiences (15 widgets, 33 runtimes, multi-region CDN)


## Prioritized Roadmap — Next Guides

### Completed (Tier 1-3)

~~1. `KALTURA_UPLOAD_AND_DELIVERY_API.md`~~ ✓ DONE  
~~2. `KALTURA_APPTOKENS_API.md`~~ ✓ DONE  
~~3. `KALTURA_EVENTS_PLATFORM_API.md`~~ ✓ DONE  
~~4. `KALTURA_AVATAR_API.md`~~ ✓ DONE (split into VOD Avatar Studio + Conversational Avatar)  
~~5. `KALTURA_WEBHOOKS_API.md`~~ ✓ DONE  
~~6. `KALTURA_ANALYTICS_API.md`~~ ✓ DONE (split into Analytics Reports + Events Collection)  
~~7. `KALTURA_CONTENT_MANAGEMENT_API.md`~~ ✓ DONE (split into User Management, Categories & Access Control, Custom Metadata, Captions & Transcripts)  
~~8. `KALTURA_DISTRIBUTION_API.md`~~ ✓ DONE + ~~`KALTURA_SYNDICATION_API.md`~~ ✓ DONE  

### Remaining — Next Guides

#### `KALTURA_LIVE_STREAMING_API.md`
**Why:** Live streaming is a core use case. RTMP/SRT ingest, simulive, recording.

**Scope:** `liveStream.add/update/get`, ingest protocols, simulive setup, recording to VOD, live-to-VOD workflow.

---

#### `KALTURA_PLAYLIST_API.md`
**Why:** Content curation. Manual + dynamic/rule-based playlists.

**Scope:** `playlist` CRUD, static vs dynamic, filter rules, execution.

---

#### `KALTURA_SCHEDULING_API.md`
**Why:** Event scheduling for live sessions, recurring events.

**Scope:** `scheduleEvent`, `scheduleResource`, recurring patterns, resource booking.

---

### Deferred

#### `KALTURA_FILE_ASSETS_API.md`
**Why:** Advanced non-media content management — `fileAsset` service, `dataEntry` type, document entries.

**Prerequisite:** Detailed analysis of `kaltura/server` backend flows for fileAsset, KalturaDataEntry, and KalturaDocumentEntry types. Must understand how fileAsset differs from attachmentAsset (permission model, serving, storage).

**Status:** DEFERRED — pending backend analysis.

---

#### Delivery Profiles Guide
**Why:** CDN configuration, serving rules, custom delivery profiles. Customer-relevant for advanced CDN setups.

**Status:** DEFERRED — highly specialized, planned for later.

---

#### Cue Points / Temporal Metadata API
**Why:** Chapters, annotations, hotspots, ad cue points — significant standalone guide.

**Status:** DEFERRED — planned for later.

---


## Execution Pattern (for each guide)

1. Research API surface (docs + live exploration)
2. Write guide with real request/response examples
3. Create test file validating every documented endpoint
4. Run tests against live API
5. Iterate until guide matches reality
6. All tests in `tests/` subfolder, config via `.env`

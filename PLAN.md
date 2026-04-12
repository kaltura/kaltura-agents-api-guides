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
| 7 | `KALTURA_UPLOAD_AND_DELIVERY_API.md` | `test_upload_delivery_api.py` (25 tests) | Done |
| 8 | `KALTURA_APPTOKENS_API.md` | `test_apptokens_api.py` (17 tests) | Done |
| 9 | `KALTURA_EVENTS_PLATFORM_API.md` | `test_events_platform_api.py` (23 tests) | Done |
| 10 | `KALTURA_MULTI_STREAM_API.md` | `test_multi_stream_api.py` (23 tests) | Done |
| 11 | `KALTURA_APP_REGISTRY_API.md` | `test_app_registry_api.py` (20 tests) | Done |
| 12 | `KALTURA_USER_PROFILE_API.md` | `test_user_profile_api.py` (30 tests) | Done |
| 13 | `KALTURA_MESSAGING_API.md` | `test_messaging_api.py` (21 tests) | Done |
| 14 | `KALTURA_WEBHOOKS_API.md` | `test_webhooks_api.py` (34 tests) | Done |
| 15 | `KALTURA_USER_MANAGEMENT_API.md` | `test_user_management_api.py` (24 tests) | Done |
| 16 | `KALTURA_AUTH_BROKER_API.md` | `test_auth_broker_api.py` (12 tests) | Done |
| 17 | `KALTURA_CATEGORIES_AND_ACCESS_CONTROL_API.md` | `test_categories_access_control_api.py` (27 tests) | Done |
| 18 | `KALTURA_CUSTOM_METADATA_API.md` | `test_custom_metadata_api.py` (22 tests) | Done |
| 19 | `KALTURA_CAPTIONS_AND_TRANSCRIPTS_API.md` | `test_captions_transcripts_api.py` (36 tests) | Done |
| 20 | `KALTURA_ANALYTICS_REPORTS_API.md` | `test_analytics_reports_api.py` (35 tests) | Done |
| 21 | `KALTURA_ANALYTICS_EVENTS_COLLECTION_API.md` | `test_analytics_events_collection_api.py` (16 tests) | Done |
| 22 | `KALTURA_GAMIFICATION_API.md` | `test_gamification_api.py` (45 tests) | Done |


## Full Kaltura API Landscape

80+ REST API services discovered. Grouped by developer need:

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
- **Unisphere** — UI component framework for building Kaltura-embedded experiences (early-stage)


## Prioritized Roadmap — Next Guides

### Tier 1: High Impact, High Usage (do next)

#### 1. `KALTURA_UPLOAD_AND_DELIVERY_API.md`
**Why:** Every Kaltura integration starts here. Most universally needed API.

**Scope:**
- Upload lifecycle: `uploadToken.add` -> chunked `uploadToken.upload` (resume, retry, `resumeAt`) -> `media.add` -> `media.addContent`
- Import from URL: `media.addFromUrl()`
- Bulk upload: `media.bulkUploadAdd()` (CSV/XML)
- Content delivery: `playManifest` (HLS/DASH adaptive streaming)
- Thumbnail API: `/thumbnail/entry_id/{id}/vid_sec/{s}/width/{w}`
- Flavor assets: transcoding profiles, listing available flavors
- Download vs playback URL distinction
- Full Python example: chunked upload of a video file

**Test plan:** Upload small file via chunks, verify entry, test import-from-URL, thumbnail extraction, playManifest generation, cleanup.

**Reference:** https://github.com/zoharbabin/kaltura_uploader/

---

#### 2. `KALTURA_APPTOKENS_API.md`
**Why:** Critical security infrastructure. Every production integration should use this. Complements Session Guide.

**Scope:**
- Why AppTokens vs raw admin secrets
- `appToken.add` — create with privileges, hash type, expiry
- `appToken.startSession` — HMAC-based KS generation
- `appToken.get`, `appToken.list`, `appToken.update`, `appToken.delete`
- Privilege scoping: `edit:entryId`, `sview:*`, `setrole:ROLE`, `iprestrict`, `urirestrict`
- Token rotation patterns
- Full Python example: create token, start session, make API call, rotate

**Test plan:** Create AppToken, start session from it, verify session works, verify privilege restrictions, delete token, verify revocation.

**Reference:** https://github.com/kaltura/kal-apptokens-utils

---

#### 3. `KALTURA_EVENTS_PLATFORM_API.md` — Virtual Events
**Why:** Dedicated modern REST API (OAS 3.0) with high customer demand. Many enterprise customers run virtual events (town halls, webinars, conferences) and want to automate creation/management via API and AI agents. Already has an official MCP server ([kaltura/mcp-events](https://github.com/kaltura/mcp-events)).

**Base URL:** `https://events-api.nvp1.ovp.kaltura.com/api/v1` (prod NVP)
**Auth:** `Authorization: Bearer <KS>`
**Regions:** NVP (default), EU (`irp2`), DE (`frp2`)

**Scope — Events:**
- `POST /events/create` — name, templateId, startDate, endDate, timezone, description
- `POST /events/list` — filter (idIn, searchTerm, date ranges, labels), pager (offset/limit), orderBy
- `POST /events/update` — name, description, dates, doorsOpenDate, timezone, labels, logoEntryId, bannerEntryId
- `POST /events/delete` — by event ID
- `POST /events/duplicate` — copy event with all config, returns job ID
- `POST /events/duplicateStatus` — poll duplication job status

**Scope — Sessions:**
- `POST /sessions/create` — session types: `MeetingEntry` (interactive room), `LiveWebcast`, `SimuLive` (pre-recorded as live), `LiveKME` (DIY live), `VirtualLearningRoom`
- `POST /sessions/list` — list all sessions for an event
- `POST /sessions/speakerList` — list speakers for a session
- Session visibility: `published`, `unlisted`, `private`
- SimuLive sessions reference a `sourceEntryId` (VOD entry)

**Scope — Team Members:**
- `POST /team-members/create`, `/update`, `/delete`, `/list`

**Scope — Templates:**
- Preset templates: `tm0000` (no session), `tm1000` (interactive room), `tm2000` (live webcast), `tm3000` (simulive), `tm4000` (room broadcasting to webcast)

**Test plan:** Create event from template, list events, update event, create sessions of different types, list sessions, list speakers, duplicate event, poll status, delete all. Full lifecycle.

**Reference:** https://github.com/kaltura/mcp-events (MCP server source code with schemas)

---

#### 4. `KALTURA_AVATAR_API.md`
**Why:** Highest novelty. AI-powered photorealistic avatars (eSelf acquisition). Very timely and differentiated.

**Scope:**
- Architecture: SDK-based vs API-based control
- Client SDK: `@unisphere/models-sdk-js`
- Backend session creation (returns JWT for frontend)
- Avatar capabilities: text-to-speech, audio playback, interruption, screen comprehension
- Integration with Genie (avatar + conversational AI)
- Browser support (WebRTC: Chrome 80+, Firefox 75+, Safari 14+)
- Full example: embed a talking avatar

**Test plan:** Backend session creation if API available. May be more doc-heavy given SDK nature.

**Note:** Early-stage API — document what exists, note evolving areas.

---

### Tier 2: High Value, Common Need

#### ~~5. `KALTURA_WEBHOOKS_API.md` — Event Notifications~~ ✓ DONE

---

---

#### 6. `KALTURA_LIVE_STREAMING_API.md`
**Why:** Live streaming is a core use case. RTMP/SRT ingest, simulive, recording.

**Scope:** `liveStream.add/update/get`, ingest protocols, simulive setup, recording to VOD, live-to-VOD workflow.

---

#### ~~7. `KALTURA_ANALYTICS_API.md`~~ ✓ DONE (split into Analytics Reports + Events Collection guides)

---

### Tier 3: Specialized but Valuable

#### 8. `KALTURA_CONTENT_MANAGEMENT_API.md` — Users, Categories, Metadata, Access Control
**Why:** Combines several related APIs that together handle "who can see what content and how it's organized."

**Scope:** `user` CRUD, `category` hierarchy, `categoryUser` entitlements, `metadataProfile` custom schemas, `accessControlProfile` rules, `captionAsset` management.

---

#### 9. `KALTURA_DISTRIBUTION_API.md`
**Why:** Multi-platform publishing (YouTube, Facebook, etc.). Valuable for media companies.

**Scope:** `distributionProfile` CRUD, connector configuration, metadata mapping, status tracking.

---

#### 10. `KALTURA_PLAYLIST_API.md`
**Why:** Content curation. Manual + dynamic/rule-based playlists.

**Scope:** `playlist` CRUD, static vs dynamic, filter rules, execution.

---

#### 11. `KALTURA_SCHEDULING_API.md`
**Why:** Event scheduling for live sessions, recurring events.

**Scope:** `scheduleEvent`, `scheduleResource`, recurring patterns, resource booking.

---


## Execution Pattern (for each guide)

1. Research API surface (docs + live exploration)
2. Write guide with real request/response examples
3. Create test file validating every documented endpoint
4. Run tests against live API
5. Iterate until guide matches reality
6. All tests in `tests/` subfolder, config via `.env`

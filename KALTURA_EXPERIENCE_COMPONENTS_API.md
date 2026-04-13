# Kaltura Experience Components API

Experience Components are front-end embeddable apps and widgets that simplify building rich media agentic applications. Instead of building recording, editing, or collaboration UIs from scratch, embed a Kaltura component and integrate via events and configuration.

**Auth:** KS passed via config object, URL parameter, or SDK constructor  
**Format:** JavaScript embed, iframe embed, or SDK  


# 1. Components

| Component | Embed Format | Auth | Standalone Guide |
|-----------|-------------|------|-----------------|
| **Player (PlayKit)** | iframe or JS | KS in provider config | [Player Embed Guide](KALTURA_PLAYER_EMBED_GUIDE.md) |
| **Express Recorder** | JS (`<script>`) | KS in config object | [Express Recorder](KALTURA_EXPRESS_RECORDER_API.md) |
| **Captions Editor** | iframe | KS as URL param | [Captions Editor](KALTURA_CAPTIONS_EDITOR_API.md) |
| **Conversational Avatar** | JS (iframe via SDK) | Client ID + Flow ID | [Conversational Avatar](KALTURA_CONVERSATIONAL_AVATAR_API.md) |
| **Chat & Collaborate** | Managed by Events Platform | Event session context | [Chat & Collaborate](KALTURA_CNC_API.md) |
| **Genie Widget** | ES module | KS in runtime settings | [Genie Widget](KALTURA_GENIE_WIDGET_API.md) |
| **Embeddable Analytics** | iframe + postMessage | ADMIN KS via postMessage | [Embeddable Analytics](KALTURA_ANALYTICS_EMBED_API.md) |

Each component creates, modifies, or interacts with Kaltura content and services — Express Recorder creates new media entries, Captions Editor modifies caption assets, the Player delivers content, and the Avatar drives AI conversations.


# 2. Component Summaries

**Player (PlayKit)** — The most widely used component. Adaptive video/audio playback with 30+ plugins for interactivity, accessibility, and analytics. Supports iframe and JavaScript embed modes with a rich event API and plugin ecosystem. See [Player Embed Guide](KALTURA_PLAYER_EMBED_GUIDE.md).

**Express Recorder** — Browser-based WebRTC recording for video, audio, and screen sharing. Creates Kaltura entries automatically upon upload. Supports Chrome, Firefox, and Opera. See [Express Recorder Guide](KALTURA_EXPRESS_RECORDER_API.md).

**Captions Editor (Captions Studio)** — Interactive caption editing with synchronized video playback and audio waveform visualization. Embedded as an iframe with URL parameters. Requires an existing caption asset. See [Captions Editor Guide](KALTURA_CAPTIONS_EDITOR_API.md).

**Conversational Avatar** — AI-powered video avatars for real-time conversations. The embed creates a sandboxed iframe and communicates via `postMessage`. Supports Dynamic Page Prompts to configure persona and behavior at runtime. See [Conversational Avatar Guide](KALTURA_CONVERSATIONAL_AVATAR_API.md). Kaltura also offers a full Avatar SDK (`@unisphere/models-sdk-js`) for direct WebRTC rendering and backend API control — the standalone guide covers both approaches.

**Chat & Collaborate (CnC)** — Real-time chat, Q&A, polls, announcements, and reactions alongside video content. Activated through the Events Platform — not a standalone embed. See [Chat & Collaborate Guide](KALTURA_CNC_API.md).

**Genie Widget** — Conversational AI search over your video library. Users ask natural-language questions and receive structured answers with video clip citations. Loaded as an ES module via the Unisphere loader. See [Genie Widget Guide](KALTURA_GENIE_WIDGET_API.md).

**Embeddable Analytics** — Analytics visualization dashboards embedded via iframe with a `postMessage` protocol. Provides the same views as the KMC — engagement, technology, geo, contributors, live stream health, and entity drill-downs. See [Embeddable Analytics Guide](KALTURA_ANALYTICS_EMBED_API.md).


# 3. Shared Best Practices

- **Scope the KS for each component.** Express Recorder needs `editadmintags:*`. Captions Editor needs edit permissions for caption assets. Genie needs `setrole:PLAYBACK_BASE_ROLE`. Analytics needs ADMIN KS (type=2). Use the minimum privileges required for each component.  
- **Handle session expiry for long-lived embeds.** Recording, caption editing, and avatar conversations can last longer than a typical KS TTL. Generate a KS with sufficient expiry for the expected session duration, or implement KS renewal in your application. For Embeddable Analytics, send an `updateConfig` message with a fresh KS.  
- **Verify entry readiness.** After Express Recorder uploads, the entry goes through transcoding. Poll `media.get` for `status=2` (READY) before redirecting users to playback or caption editing.  
- **Use HTTPS for all embed URLs.** All component embed URLs must use HTTPS for WebRTC, secure media access, iframe security policies, and ES module imports.  
- **Generate client-facing KS tokens server-side.** Components like Genie and the Player expose the KS in client-side code. Generate USER sessions (type=0) with minimal privileges on your backend. Never embed admin secrets in client-side code.  


# 4. Error Handling Overview

Each standalone guide includes component-specific error handling. Common patterns across all components:

- **KS expiry during long sessions** — Components do not automatically renew expired sessions. Uploads, saves, and API calls fail silently when the KS expires. Generate tokens with sufficient expiry or implement renewal logic.  
- **Missing permissions** — Components that require specific KS privileges (e.g., `editadmintags:*` for Express Recorder, analytics role for Embeddable Analytics) fail silently or show empty UIs when permissions are missing.  
- **Container/iframe not rendered** — Verify CSS selectors match existing DOM elements, iframe `src` URLs are accessible over HTTPS, and container elements have explicit dimensions.  


# 5. Related Guides

- **[Player Embed Guide](KALTURA_PLAYER_EMBED_GUIDE.md)** — Video/audio playback with 30+ plugins  
- **[Express Recorder](KALTURA_EXPRESS_RECORDER_API.md)** — Browser-based WebRTC recording  
- **[Captions Editor](KALTURA_CAPTIONS_EDITOR_API.md)** — Interactive caption editing with video/waveform sync  
- **[Conversational Avatar](KALTURA_CONVERSATIONAL_AVATAR_API.md)** — AI-powered conversational video avatar embed  
- **[Chat & Collaborate](KALTURA_CNC_API.md)** — Real-time chat and collaboration alongside video  
- **[Genie Widget](KALTURA_GENIE_WIDGET_API.md)** — Conversational AI search widget  
- **[Embeddable Analytics](KALTURA_ANALYTICS_EMBED_API.md)** — Analytics dashboards via iframe  
- **[Session Guide](KALTURA_SESSION_GUIDE.md)** — KS generation and privilege management for component authentication  
- **[Upload & Delivery](KALTURA_UPLOAD_AND_DELIVERY_API.md)** — Content lifecycle after Express Recorder creates entries  
- **[Captions & Transcripts](KALTURA_CAPTIONS_AND_TRANSCRIPTS_API.md)** — Caption asset CRUD for Captions Editor prerequisites  
- **[AI Genie API](KALTURA_AI_GENIE_API.md)** — Server-side Genie HTTP API for custom integrations  
- **[Events Platform](KALTURA_EVENTS_PLATFORM_API.md)** — Virtual events where CnC and Player are embedded together  
- **[Analytics Reports](KALTURA_ANALYTICS_REPORTS_API.md)** — Programmatic analytics data access  

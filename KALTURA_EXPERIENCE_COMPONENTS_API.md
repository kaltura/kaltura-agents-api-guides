# Kaltura Experience Components API

Experience Components are front-end embeddable apps and widgets that simplify building rich media agentic applications. Instead of building recording, editing, or collaboration UIs from scratch, embed a Kaltura component and integrate via events and configuration.

**Base URL:** Component-specific (see each section for embed URLs and CDN paths)  
**Auth:** KS passed via config object, URL parameter, or SDK constructor  
**Format:** JavaScript embed, iframe embed, or SDK  


# 1. Overview

Kaltura provides several embeddable experience components, each solving a specific integration need:

| Component | What It Does | When to Use It |
|-----------|-------------|----------------|
| **[Player (PlayKit)](#2-player-playkit)** | Adaptive video/audio playback with plugins | Embed video playback in any web application — the most widely used component |
| **[Express Recorder](#3-express-recorder)** | Browser-based WebRTC recording | Enable users to record video, audio, or screen directly in your app without native software |
| **[Captions Editor](#4-captions-editor-captions-studio)** | Interactive caption editing with video/waveform sync | Let users create and edit captions in-browser, synchronized to video playback |
| **[Conversational Avatar](#5-conversational-avatar)** | AI-powered conversational video avatar | Build AI interview simulators, training scenarios, conversational agents, and coaching bots |
| **[Chat & Collaborate (CnC)](#6-chat--collaborate-cnc)** | Real-time chat and collaboration alongside video | Add real-time chat, Q&A, and collaboration panels alongside video playback in content hubs and events |
| **[Embeddable Analytics](#7-embeddable-analytics)** | Analytics visualization dashboards | Embed Kaltura analytics views into admin panels or internal tools |

Each component creates, modifies, or interacts with Kaltura content and services — Express Recorder creates new media entries, Captions Editor modifies caption assets, the Player delivers content, and the Avatar drives AI conversations.


# 2. Player (PlayKit)

The Kaltura Player v7 (PlayKit) is the most widely used experience component. It provides adaptive video/audio playback with 30+ plugins for interactivity, accessibility, and analytics.

**When to use:** Embed video playback in any web page or application — from simple single-video embeds to complex multi-stream PIP layouts with live Q&A, transcripts, and quizzes.

The Player has its own dedicated guide. See **[Player Embed Guide](KALTURA_PLAYER_EMBED_GUIDE.md)** for iframe and JavaScript embed methods, plugin ecosystem, player KS configuration, event handling, and programmatic control.


# 3. Express Recorder

The Express Recorder provides browser-based WebRTC recording — video, audio, and screen sharing. It creates Kaltura entries automatically upon upload.

**When to use:**  
- **User-generated content** — Let employees or students record and submit video directly from your application  
- **Self-service video creation** — Enable video messages, video resumes, or testimonial collection without requiring desktop recording software  
- **Video assessment** — Capture practice presentations, interview recordings, or skill demonstrations  

**Supported browsers:** Chrome, Firefox, Opera (WebRTC required)

## 3.1 Embedding

Load the Express Recorder bundle from the Kaltura CDN and create an instance:

```html
<div id="recorder-container"></div>
<script src="https://www.kaltura.com/apps/expressrecorder/latest/express-recorder.js"></script>
<script>
  var component = Kaltura.ExpressRecorder.create('recorder-container', {
    ks: '$KALTURA_KS',
    serviceUrl: '$KALTURA_SERVICE_URL',
    partnerId: $KALTURA_PARTNER_ID,
    uiConfId: $KALTURA_PLAYER_ID,
    app: 'my-recording-app',
    playerUrl: 'https://cdnapisec.kaltura.com',
    conversionProfileId: 0,
    entryName: 'User Recording',
    allowVideo: true,
    allowAudio: true,
    allowScreenShare: false,
    maxRecordingTime: 300,
    showUploadUI: true
  });
</script>
```

## 3.2 Configuration

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `ks` | string | required | Kaltura Session token |
| `serviceUrl` | string | required | API base URL (e.g., `https://www.kaltura.com/api_v3`) |
| `partnerId` | number | required | Kaltura account ID |
| `uiConfId` | number | required | Player uiConf ID (for playback preview) |
| `app` | string | required | Application identifier |
| `playerUrl` | string | required | CDN URL for the player (e.g., `https://cdnapisec.kaltura.com`) |
| `conversionProfileId` | number | 0 | Conversion profile for transcoding (0 = account default) |
| `entryName` | string | `""` | Default name for created entries |
| `allowVideo` | boolean | true | Enable video recording |
| `allowAudio` | boolean | true | Enable audio recording |
| `allowScreenShare` | boolean | false | Enable screen capture recording |
| `maxRecordingTime` | number | unlimited | Maximum recording duration in seconds |
| `showUploadUI` | boolean | true | Show the upload progress UI after recording |

**KS privileges:** The KS must include `editadmintags:*` to allow the recorder to create entries.

## 3.3 Events

Listen for events on the component instance:

```javascript
component.instance.addEventListener('mediaUploadStarted', function(e) {
  console.log('Upload started, entryId:', e.detail.entryId);
});
```

| Event | Payload | Description |
|-------|---------|-------------|
| `recordingStarted` | — | User started recording |
| `recordingEnded` | — | User stopped recording |
| `recordingCancelled` | — | User cancelled the recording |
| `mediaUploadStarted` | `{ entryId }` | Upload began — returns the new entry ID |
| `mediaUploadProgress` | `{ loaded, total }` | Upload progress in bytes |
| `mediaUploadEnded` | `{ entryId }` | Upload completed successfully |
| `mediaUploadCancelled` | — | User cancelled the upload |
| `error` | `{ message }` | An error occurred |

## 3.4 Methods

| Method | Description |
|--------|-------------|
| `startRecording()` | Programmatically start recording |
| `stopRecording()` | Stop the current recording |
| `upload()` | Upload the recorded media to Kaltura |
| `cancelUpload()` | Cancel an in-progress upload |
| `saveCopy()` | Save a local copy of the recording |


# 4. Captions Editor (Captions Studio)

The Captions Editor provides an interactive caption editing interface with synchronized video playback and audio waveform visualization. Users can create, edit, and time captions directly in the browser.

**When to use:**  
- **Accessibility compliance** — Let content creators add and refine captions in a visual editor rather than editing raw SRT files  
- **Post-production captioning** — Correct AI-generated captions from REACH with precise timing adjustments  
- **Localization workflows** — Edit translated captions with synchronized playback for accuracy verification  

## 4.1 Prerequisites

The entry must have an existing caption asset before opening the editor. Create one using the Captions & Transcripts API if needed:

```bash
# Create a blank SRT caption asset for the entry
curl -X POST "$KALTURA_SERVICE_URL/service/caption_captionAsset/action/add" \
  -d "ks=$KALTURA_KS" \
  -d "format=1" \
  -d "entryId=ENTRY_ID" \
  -d "captionAsset[objectType]=KalturaCaptionAsset" \
  -d "captionAsset[language]=English" \
  -d "captionAsset[format]=1" \
  -d "captionAsset[label]=English"
```

See the [Captions & Transcripts Guide](KALTURA_CAPTIONS_AND_TRANSCRIPTS_API.md) for full caption asset management.

## 4.2 Embedding via iframe

Embed the editor using an iframe with URL parameters. The editor is hosted on the Kaltura CDN:

```html
<iframe
  src="https://www.kaltura.com/apps/captionstudio/latest/index.html?pid={PARTNER_ID}&ks={KS}&entryid={ENTRY_ID}&assetid={CAPTION_ASSET_ID}&maxcharsperline=42&cdnurl=https://cdnapisec.kaltura.com&serviceurl=https://www.kaltura.com"
  width="100%"
  height="700"
  allow="autoplay; encrypted-media"
  style="border: none;">
</iframe>
```

## 4.3 URL Parameters

| Parameter | Required | Description |
|-----------|----------|-------------|
| `pid` | yes | Kaltura partner ID |
| `ks` | yes | Kaltura Session token |
| `entryid` | yes | Media entry ID to edit captions for |
| `assetid` | yes | Caption asset ID to edit |
| `maxcharsperline` | no | Maximum characters per caption line (e.g., 42) |
| `cdnurl` | yes | CDN base URL (e.g., `https://cdnapisec.kaltura.com`) |
| `serviceurl` | yes | API base URL without `/api_v3` (e.g., `https://www.kaltura.com`) |

## 4.4 Workflow

1. List caption assets for the entry using `captionAsset.list`  
2. Pass the desired `assetid` to the Captions Editor iframe  
3. The user edits captions in the browser (timing, text, formatting)  
4. The editor saves changes directly to the caption asset via the Kaltura API  
5. Updated captions are immediately available for playback  

## 4.5 Editor Features

- **Waveform visualization** — Audio waveform display for precise caption timing  
- **Synchronized playback** — Video plays in sync with the caption timeline; click a caption to seek to that position  
- **Inline text editing** — Edit caption text, start/end times, and line breaks directly in the timeline  
- **Keyboard shortcuts** — Play/pause, jump to next/previous caption, split/merge captions  
- **Character limit enforcement** — `maxcharsperline` parameter enforces line length limits with visual indicators  
- **Auto-save** — Changes are saved to the caption asset automatically  


# 5. Conversational Avatar

Kaltura's Conversational Avatar provides AI-powered video avatars that can hold real-time conversations with users. The avatar speaks, listens, and responds using AI — enabling training simulations, coaching, interview practice, and conversational agents.

**When to use:**  
- **HR interview simulation** — Candidates practice with an AI interviewer that evaluates responses  
- **Sales and product training** — Employees practice scenarios with an AI coach that adapts to their answers  
- **Customer-facing conversational agents** — Embed an AI avatar that answers questions about your products or services  
- **Language learning** — Practice pronunciation and conversation with real-time feedback  

## 5.1 Embedding

The Avatar SDK creates a sandboxed iframe and communicates via `postMessage`. Load the SDK and initialize:

```html
<div id="avatar-container" style="width: 800px; height: 600px;"></div>
<script src="kaltura-avatar-sdk.min.js"></script>
<script>
  var sdk = new KalturaAvatarSDK({
    clientId: 'YOUR_CLIENT_ID',
    flowId: 'YOUR_FLOW_ID',
    container: '#avatar-container',
    config: { debug: false }
  });

  // Listen for avatar events
  sdk.on('showing-agent', function() {
    console.log('Avatar is ready');
    // Inject a Dynamic Page Prompt to configure the avatar's persona
    sdk.injectPrompt(JSON.stringify({
      role: 'Interview Coach',
      instructions: 'Ask about their experience with project management'
    }));
  });

  sdk.on('agent-talked', function(data) {
    console.log('Avatar said:', data.agentContent);
  });

  sdk.on('user-transcription', function(data) {
    console.log('User said:', data.userTranscription);
  });

  sdk.start();
</script>
```

## 5.2 Configuration

| Parameter | Required | Description |
|-----------|----------|-------------|
| `clientId` | yes | Kaltura avatar client identifier |
| `flowId` | yes | Identifies which avatar/flow to load |
| `container` | no | CSS selector string or HTMLElement for the iframe |
| `config.debug` | no | Enable console logging |
| `config.apiBaseUrl` | no | Override API URL (default: `https://api.avatar.us.kaltura.ai`) |
| `config.meetBaseUrl` | no | Override meeting URL (default: `https://meet.avatar.us.kaltura.ai`) |

## 5.3 Lifecycle and Events

The avatar progresses through states: `uninitialized` → `initializing` → `ready` → `in-conversation` → `ended`.

| Event | Data | Description |
|-------|------|-------------|
| `showing-agent` | — | Avatar is visible and ready (inject Dynamic Page Prompt here) |
| `agent-talked` | `{ agentContent }` | Avatar spoke — contains the text |
| `user-transcription` | `{ userTranscription }` | User's speech was transcribed |
| `conversation-ended` | — | Conversation finished |
| `error` | — | An error occurred |

## 5.4 Key Methods

| Method | Returns | Description |
|--------|---------|-------------|
| `start(options?)` | `Promise<iframe>` | Load assets and create the avatar iframe |
| `end()` | void | End the conversation and remove iframe |
| `destroy()` | void | Full cleanup (listeners, assets, iframe) |
| `injectPrompt(text)` | boolean | Send a Dynamic Page Prompt to configure the avatar's behavior |
| `getTranscript()` | Array | Full conversation transcript `[{role, text, timestamp}]` |
| `getTranscriptText(options?)` | string | Formatted transcript (text/markdown/json) |

The **Dynamic Page Prompt (DPP)** is the mechanism for customizing avatar behavior at runtime. Inject it on the `showing-agent` event to configure the avatar's persona, scenario, evaluation criteria, and guardrails.


# 6. Chat & Collaborate (CnC)

The Chat & Collaborate (CnC) component provides real-time communication and audience interaction alongside video content. It powers the collaboration layer in Kaltura virtual events and MediaSpace content pages.

**When to use:**  
- **Virtual events and webinars** — Add real-time audience chat and Q&A alongside live or recorded sessions  
- **Content hubs** — Enable discussion threads and collaboration on media content pages  
- **Learning platforms** — Facilitate student-instructor interaction alongside course videos  

## 6.1 Features

CnC provides a suite of collaboration modules that appear as panels alongside the video player:

| Module | Description |
|--------|-------------|
| **Group Chat** | Real-time text chat for all participants. Messages appear in chronological order with sender names and timestamps. Supports emoji reactions on messages. |
| **Q&A** | Structured question-and-answer panel. Attendees submit questions; moderators can review, approve, answer publicly, or answer privately. Supports upvoting to surface popular questions. |
| **Polls** | Live polling during sessions. Presenters create multiple-choice polls, attendees vote, and results display in real-time. |
| **Announcements** | One-way messages from moderators/presenters to all participants. Appear prominently in the chat area. |
| **Reactions** | Emoji reactions (applause, thumbs up, etc.) that float across the screen during live sessions. |

## 6.2 Integration

CnC is embedded as part of the Kaltura Events Platform or MediaSpace experience. It is not a standalone widget with a public embed API — it is automatically included when you create virtual event sessions through the Events Platform.

**How CnC is activated:**

1. Create a virtual event with sessions via the [Events Platform API](KALTURA_EVENTS_PLATFORM_API.md)  
2. Configure session settings to enable chat, Q&A, and/or polls  
3. When attendees join the event page, the CnC panels load automatically alongside the video player  
4. Moderators manage chat and Q&A through the event moderation interface  

**Configuration through Events Platform:**

- **Enable/disable modules** — Control which CnC features (chat, Q&A, polls) are available per session  
- **Moderation settings** — Set whether Q&A requires moderator approval before questions are visible  
- **Anonymity** — Configure whether attendees can post anonymously  
- **Pre/post-event behavior** — Control whether chat is available before the session starts or after it ends  

## 6.3 Data Access

Chat and Q&A data from events can be accessed through the Events Platform reporting endpoints. Use the analytics report types for virtual events to retrieve engagement metrics including chat message counts, Q&A participation, and poll responses. See the [Analytics Reports API](KALTURA_ANALYTICS_REPORTS_API.md) for event-specific report types (3009, 3010).


# 7. Embeddable Analytics

The Embeddable Analytics widget provides analytics visualization dashboards that can be embedded in third-party applications via iframe.

**When to use:**  
- **Admin dashboards** — Embed Kaltura analytics views into internal admin tools without building custom visualizations  
- **Client-facing reports** — Show usage analytics to customers in multi-tenant platforms  
- **Executive summaries** — Embed high-level engagement metrics in portals or intranets  

## 7.1 Embedding

Embed the analytics dashboard using an iframe with KS authentication:

```html
<iframe
  src="https://www.kaltura.com/apps/kmc/analytics/?pid={PARTNER_ID}&ks={KS}"
  width="100%"
  height="800"
  style="border: none;">
</iframe>
```

The embedded dashboard provides the same analytics views available in the Kaltura Management Console (KMC), including:

- **Content engagement** — Views, plays, play-through rates, average view time per entry  
- **Top content** — Most-viewed entries ranked by plays or minutes watched  
- **Viewer metrics** — Unique viewers, geographic distribution, device and browser breakdown  
- **Usage trends** — Time-series charts of bandwidth, storage, and viewing activity  

## 7.2 KS Requirements

The KS used for the analytics iframe must be an ADMIN KS (type=2) with sufficient permissions to access analytics data. Use a short-lived KS and refresh it when the user navigates to the analytics view.

## 7.3 Programmatic Alternative

For full programmatic access to analytics data (custom reports, CSV exports, time-series queries), use the [Analytics Reports API](KALTURA_ANALYTICS_REPORTS_API.md) instead of the embeddable widget. The API provides more granular control over report parameters, date ranges, and output formats.


# 8. Error Handling

- **Express Recorder `error` event** — Listen for `error` events on the component instance. The event payload includes a `message` field with details. Common causes: WebRTC not supported (Safari limitations), microphone/camera permissions denied, upload network failure.  
- **Captions Editor load failures** — If the iframe fails to load, verify the `ks` is valid and the `assetid` exists for the given `entryid`. An expired KS shows a login prompt; an invalid asset ID shows an empty editor.  
- **Avatar SDK `error` event** — The SDK emits `error` when the avatar fails to initialize or the conversation breaks. Check network connectivity to the avatar API endpoint.  
- **KS expiry during long sessions** — Components do not automatically renew expired sessions. If a user's recording or editing session exceeds the KS TTL, uploads and saves will fail silently. Generate KS tokens with sufficient expiry or implement renewal logic in your application.


# 9. Best Practices

- **Scope the KS for each component.** Express Recorder needs `editadmintags:*`. Captions Editor needs edit permissions for caption assets. Use the minimum privileges required.  
- **Handle session expiry for long-lived embeds.** Recording, caption editing, and avatar conversations can last longer than a typical KS TTL. Generate a KS with sufficient expiry for the expected session duration, or implement KS renewal in your application.  
- **Verify entry readiness.** After Express Recorder uploads, the entry goes through transcoding. Poll `media.get` for `status=2` (READY) before redirecting users to playback or caption editing.  
- **Create caption assets before opening the editor.** The Captions Studio requires an existing caption asset ID. Create a blank one programmatically if the entry has no captions yet.  
- **Use HTTPS for all embed URLs.** All component embed URLs must use HTTPS for WebRTC, secure media access, and iframe security policies.  
- **Inject Dynamic Page Prompts on the correct event.** For the Avatar SDK, always inject the DPP on the `showing-agent` event, not on an arbitrary timeout after `start()`.


# 10. Related Guides

- **[Player Embed Guide](KALTURA_PLAYER_EMBED_GUIDE.md)** — The most widely used experience component: video/audio playback with 30+ plugins  
- **[Session Guide](KALTURA_SESSION_GUIDE.md)** — KS generation and privilege management for component authentication  
- **[Upload & Delivery](KALTURA_UPLOAD_AND_DELIVERY_API.md)** — Content lifecycle after Express Recorder creates entries  
- **[Captions & Transcripts](KALTURA_CAPTIONS_AND_TRANSCRIPTS_API.md)** — Caption asset CRUD for Captions Editor prerequisites  
- **[AI Genie](KALTURA_AI_GENIE_API.md)** — Conversational AI search (related to Avatar conversational capabilities)  
- **[Events Platform](KALTURA_EVENTS_PLATFORM_API.md)** — Virtual events where CnC and Player are embedded together  
- **[Analytics Reports](KALTURA_ANALYTICS_REPORTS_API.md)** — Programmatic analytics data access (alternative to Embeddable Analytics widget)

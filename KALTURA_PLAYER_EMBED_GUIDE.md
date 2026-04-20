# Kaltura PlayKit Player: Embedding & Control Guide

Embed Kaltura's PlayKit player in web applications using iframe or dynamic JavaScript. Both methods support KS-based access control, clipping, autoplay, and full programmatic control via the player API.

**Base URL:** `https://cdnapisec.kaltura.com/p/{PARTNER_ID}/embedPlaykitJs/uiconf_id/{PLAYER_ID}` (may differ by region)  
**Auth:** Optional KS for access-controlled content (see [Session Guide](KALTURA_SESSION_GUIDE.md))  
**Format:** HTML embed (iframe) or JavaScript SDK (PlayKit)  


# 1. When to Use

- **Website and app video playback** — Embed adaptive video and audio playback in websites, web apps, and mobile web views using iframe or JavaScript integration.  
- **Branded player customization** — Configure player appearance (watermarks, custom CSS, UI component toggles) and behavior (autoplay, looping, stream priority) to match your application's branding.  
- **Interactive video delivery** — Enable in-player experiences such as chapter navigation, dual-screen slides, in-video quizzes, hotspots, and transcript search through the 30+ plugin ecosystem.  
- **Access-controlled content** — Deliver protected video content using KS-based authentication, entry-scoped sessions, privacy contexts, and IP tokenization for CDN-protected delivery.  
- **Programmatic player control** — Build custom playback workflows with play/pause/seek APIs, event listeners for progress tracking, and runtime plugin control for dynamic layout switching.


# 2. Prerequisites

- **KS (Kaltura Session):** Optional for public content. For access-controlled entries, generate a USER KS (type=0) scoped with `sview:ENTRY_ID` on your server and pass it to the player. For IP-tokenized delivery, include `iprestrict:VIEWER_IP`.  
- **Player instance (uiConfId):** A player configuration created in the KMC under Studio > TV Platform or Studio > Player. The `uiConfId` determines which plugins are available and the default player settings.  
- **Partner ID:** Your Kaltura account ID, used to construct the player library URL and authenticate API requests.  
- **Session management:** See [Session Guide](KALTURA_SESSION_GUIDE.md) for KS generation and privilege scoping.


# 3. Embed Type Comparison

- **Iframe embed** – Simplest drop-in, ideal for quick embedding where the host page manages layout only. Works well for sites that restrict JavaScript to first-party code. Control the configuration passed to the player by adding query string params.  
- **Dynamic JS (PlayKit)** – recommended when you need **runtime config**, **start time**, **programmatic control**, or richer integrations. 

# 4. Kaltura Player Iframe Embed

Use the Kaltura iframe endpoint and pass parameters via **query string**. This form accepts `entry_id`, `uiconf_id`, optional `ks`, and most common initial config and playback flags.

```html
<!-- Responsive container -->
<div style="position:relative;max-width:100%;aspect-ratio:16/9;">
  <iframe
    id="kaltura_player"
    title="Kaltura video"
    src="https://cdnapisec.kaltura.com/p/{PARTNER_ID}/embedPlaykitJs/partner_id/{PARTNER_ID}/uiconf_id/{PLAYER_INSTANCE_ID}?iframeembed=true&ks={KALTURA_SESSION}&entry_id={ENTRY_ID}&kalturaSeekFrom={CLIP_START_SECONDS}&kalturaClipTo={CLIP_END_SECONDS}&config[playback]={&quot;autoplay&quot;:true,&quot;mutedAutoPlay&quot;:true,&quot;muted&quot;:true}"
    allowfullscreen="" 
    allow="autoplay *; fullscreen *; encrypted-media *" 
    style="width: 100%; height: 100%; aspect-ratio: 16 / 9; min-width: 100%; background-color: black; border: 0px; border-radius: 0.5rem; overflow: hidden;" >
  </iframe>
</div>
```

### iframe Params Replacement Tokens

- {PARTNER_ID} - is your Kaltura account ID.  
- {PLAYER_INSTANCE_ID} - is your Player Instance ID (`uiConfId`). Find it in the Kaltura Management Console (KMC) under Studio > TV Platform or Studio > Player — each player configuration has a numeric ID displayed in the list or detail view.  
- {KALTURA_SESSION} - is a valid Kaltura Session that can be used to access the video Kaltura Entry ID to be played in this session (if playback is anonymous and the entry id open to public, this param can be skipped).   
- {ENTRY_ID} - The ID of the video to be played.   
- {CLIP_START_SECONDS} - will clip the video from that particular start second. if skipped - video will begin from the start.  
- {CLIP_END_SECONDS} - will clip the video to that second. if skipped, the video will play to its full duration.  

#### `config[playback]` params:

- `autoplay` - set to `true` to begin playback automatically or `false` to begin at paused state.  
- `muted` - set to `true` to begin playback muted (volume=0).  
- `mutedAutoPlay` - set to `true` to ensure autoplay always begin playback muted.  

### Other iframe Embed Notes

- To make the iframe responsive ensure a wrapping div is set and the iframe has a defined `aspect-ratio`.
- Set a meaningful `title` for accessibility and SEO.
- Ensure to include `allow` and `allowfullscreen` attributes for autoplay/PiP/encrypted-playback/fullscreen.  

> Note: we're using cdnapisec.kaltura.com in this example, but your account region/deployment may differ. Make sure to use the correct base URL of your Kaltura account.  

# 5. Dynamic JS (PlayKit) embed

Load the **PlayKit/Kaltura Player JS** for your PID/UiConfID, then call `KalturaPlayer.setup(...)` and `loadMedia(...)`.

> The code below assumes the same tokens as above.  

```html
<!-- 1) Load player library for your PID/UiConfID -->
<script src="https://cdnapisec.kaltura.com/p/{PARTNER_ID}/embedPlaykitJs/uiconf_id/{PLAYER_INSTANCE_ID}/kaltura-player.js" type="text/javascript"></script>

<!-- 2) Player container -->
<div id="kplayer" style="max-width:100%;aspect-ratio:16/9;"></div>

<script>
  // 3) Setup with provider + playback; pass KS here when needed
  try {
    const player = KalturaPlayer.setup({
      targetId: 'kplayer',
      provider: {
        partnerId: {PARTNER_ID},
        uiConfId: {PLAYER_INSTANCE_ID},
        ks: '{KALTURA_SESSION}' // optional if content is public
        // env: { serviceUrl: 'https://www.kaltura.com' } // override if needed
      },
      playback: {
        autoplay: true,
        muted: true    
      }
    });

    // 4) Load media and optionally start at N seconds
    player.loadMedia(
      { entryId: '{ENTRY_ID}' },
      { seekFrom: {CLIP_START_SECONDS}, clipTo: {CLIP_END_SECONDS} }  
    );
    // Wait for the player to be ready (tracks loaded, safe to query state)
    player.ready().then(() => {
      console.log("player is ready!");
    });
  } catch (e) {
    console.error(e.message);
  }
```

## 5.1 Full KalturaPlayer.setup() Config Object

The `KalturaPlayer.setup()` call accepts a configuration object with the following top-level sections:

```javascript
const player = KalturaPlayer.setup({
  targetId: 'kplayer',               // Required: DOM element ID for the player container
  log: { level: 'ERROR' },           // Log level: 'DEBUG', 'INFO', 'WARN', 'ERROR', 'OFF'

  provider: {
    partnerId: PARTNER_ID,           // Required: Kaltura partner ID (integer)
    uiConfId: UICONF_ID,            // Required: Player instance ID from KMC
    ks: 'KS_STRING',                // Optional: Kaltura Session for authenticated playback
    env: {
      serviceUrl: 'https://www.kaltura.com',  // API service URL (override for non-default regions)
      cdnUrl: 'https://cdnapisec.kaltura.com' // CDN URL (override for non-default regions)
    }
  },

  playback: {
    autoplay: true,                  // Auto-start playback (requires muted:true in most browsers)
    muted: false,                    // Start muted
    mutedAutoPlay: true,             // Fall back to muted autoplay if unmuted autoplay is blocked
    loop: false,                     // Loop playback when media ends
    startTime: 0,                    // Start playback at this position (seconds)
    volume: 1.0,                     // Initial volume (0.0 - 1.0)
    playsinline: true,               // Inline playback on mobile (no fullscreen takeover)
    preload: 'auto',                 // Preload behavior: 'auto', 'metadata', 'none'
    allowMutedAutoPlay: true,        // Allow muted autoplay as fallback
    streamPriority: [
      { engine: 'html5', format: 'hls' },
      { engine: 'html5', format: 'dash' },
      { engine: 'html5', format: 'progressive' }
    ]
  },

  ui: {
    disable: false,                  // Disable the entire UI
    css: '',                         // Custom CSS string injected into the player
    components: {
      seekbar: { disabled: false },  // Toggle individual UI components
      watermark: {
        img: 'https://example.com/logo.png',
        url: 'https://example.com',
        placement: 'top-left',       // 'top-left', 'top-right', 'bottom-left', 'bottom-right'
        timeout: 0                   // Seconds to show watermark (0 = always)
      }
    }
  },

  plugins: {
    // Plugin configs — see section 6.2 for details per plugin
  }
});
```

| Config Section | Purpose |
|---------------|---------|
| `targetId` | DOM element ID where the player renders. The element must exist before `setup()` is called. |
| `provider` | Kaltura account and authentication settings. `partnerId` and `uiConfId` are required. |
| `playback` | Playback behavior: autoplay, volume, looping, stream format priority. |
| `ui` | Player UI customization: disable controls, inject CSS, toggle components, add watermarks. |
| `plugins` | Plugin activation and configuration. Pass an empty object `{}` to enable with defaults, or provide config parameters. |
| `log` | Logging verbosity. Use `DEBUG` during development and `ERROR` in production. |

## 5.2 loadMedia() Options

The `player.loadMedia()` method accepts two arguments: a media info object and an optional options object:

```javascript
player.loadMedia(
  { entryId: 'ENTRY_ID' },          // Required: entry to load
  {
    seekFrom: 30,                    // Start playback at 30 seconds (clipping start)
    clipTo: 120,                     // End playback at 120 seconds (clipping end)
    startTime: 30                    // Alternative to seekFrom for setting start position
  }
);
```

| Parameter | Type | Description |
|-----------|------|-------------|
| `entryId` | string | Kaltura entry ID to load |
| `seekFrom` | number | Clip start position in seconds |
| `clipTo` | number | Clip end position in seconds |
| `startTime` | number | Initial playback position in seconds |


# 6. JS Control (Play/Pause/Seek/Volume)

With **dynamic JS embeds**, the player instance exposes standard controls:

```js
// Play / Pause
player.play();
player.pause();

// Seek (seconds)
player.currentTime = 90;

// Volume (0.0 – 1.0)
player.volume = 0.5;
```

These APIs are part of the web player’s base interface. Key properties and methods:

| API | Type | Description |
|-----|------|-------------|
| `player.play()` | method | Start playback |
| `player.pause()` | method | Pause playback |
| `player.currentTime` | get/set | Current playback position in seconds |
| `player.duration` | get | Total media duration in seconds |
| `player.volume` | get/set | Volume level (0.0 – 1.0) |
| `player.muted` | get/set | Mute state (boolean) |
| `player.playbackRate` | get/set | Playback speed (1.0 = normal) |
| `player.isLive()` | method | Whether the current media is a live stream |
| `player.ready()` | method | Returns a Promise that resolves when the player is ready for interaction |
| `player.loadMedia({entryId})` | method | Load a new media entry into the player |

## 6.1 Binding to JS player events (drive app flows)

The Kaltura player exposes a DOM-style event system and a Promise for readiness. Use it for analytics beacons, UI reactions, gated flows, etc.  

**Player core events consist of two event types:**

- **HTML5 Video Events** — Standard events from the underlying `<video>` element  
- **Player Custom Events** — Events specific to the Kaltura player that extend beyond standard HTML5 video  

All core events are accessible via `player.Event.Core` as shown in the example below.

### HTML5 Video Events

| Event | Constant | Callback Payload |
|-------|----------|-----------------|
| Play | `PLAY` | No payload. Fired when playback is requested (before media actually starts playing). |
| Pause | `PAUSE` | No payload. Fired when playback is paused. |
| Ended | `ENDED` | No payload. Fired when playback reaches the end of the media. |
| Seeking | `SEEKING` | No payload. The player's `currentTime` property reflects the target seek position. |
| Seeked | `SEEKED` | No payload. Fired when a seek operation completes. |
| Time Update | `TIME_UPDATE` | No payload. Fired continuously during playback (typically every 250ms). Read `player.currentTime` and `player.duration` for position data. |
| Volume Change | `VOLUME_CHANGE` | No payload. Read `player.volume` (0.0-1.0) for the new volume level. |
| Waiting | `WAITING` | No payload. Fired when playback stalls due to buffering. |
| Playing | `PLAYING` | No payload. Fired when playback resumes after buffering or pause. |
| Can Play | `CANPLAY` | No payload. Fired when enough data is buffered to begin playback. |
| Loaded Metadata | `LOADED_METADATA` | No payload. Fired when media metadata (duration, dimensions) is available. Read `player.duration` for the media length. |
| Loaded Data | `LOADED_DATA` | No payload. Fired when the first frame of the media is loaded. |
| Duration Change | `DURATION_CHANGE` | No payload. Fired when `player.duration` changes (e.g., live stream duration updates). |
| Rate Change | `RATE_CHANGE` | No payload. Read `player.playbackRate` for the new rate value. |
| Error | `ERROR` | `event.payload` — object with `severity` (number: 0=CRITICAL, 1=RECOVERABLE), `category` (number: 1=NETWORK, 2=TEXT, 3=MEDIA, 4=MANIFEST, 5=ENCRYPTION), `code` (number), and `data` (error details object). |

### Player Custom Events

| Event | Constant | Callback Payload |
|-------|----------|-----------------|
| Player State Changed | `PLAYER_STATE_CHANGED` | `event.payload.oldState` — object with `type` (string: `"idle"`, `"loading"`, `"playing"`, `"paused"`, `"buffering"`).  `event.payload.newState` — object with `type` (same values). |
| Media Loaded | `MEDIA_LOADED` | No payload. Fired after `loadMedia()` resolves and media sources are set. |
| First Play | `FIRST_PLAY` | No payload. Fired once per media load — the first time play is requested. |
| First Playing | `FIRST_PLAYING` | No payload. Fired once per media load — the first time media actually renders a frame. |
| Tracks Changed | `TRACKS_CHANGED` | `event.payload.tracks` — array of track objects, each with `type` (string: `"video"`, `"audio"`, `"text"`), `label` (string), `language` (string), `active` (boolean), and `index` (number). |
| Text Track Changed | `TEXT_TRACK_CHANGED` | `event.payload.selectedTextTrack` — track object with `language` (string), `label` (string), `kind` (string: `"subtitles"`, `"captions"`), `active` (boolean), and `index` (number). |
| Audio Track Changed | `AUDIO_TRACK_CHANGED` | `event.payload.selectedAudioTrack` — track object with `language` (string), `label` (string), `active` (boolean), and `index` (number). |
| Video Track Changed | `VIDEO_TRACK_CHANGED` | `event.payload.selectedVideoTrack` — track object with `width` (number), `height` (number), `bitrate` (number), `active` (boolean), and `bandwidth` (number). |
| Enter Fullscreen | `ENTER_FULLSCREEN` | No payload. Fired when the player enters fullscreen mode. |
| Exit Fullscreen | `EXIT_FULLSCREEN` | No payload. Fired when the player exits fullscreen mode. |
| Enter Picture-in-Picture | `ENTER_PICTURE_IN_PICTURE` | No payload. Fired when the player enters PiP mode. |
| Exit Picture-in-Picture | `EXIT_PICTURE_IN_PICTURE` | No payload. Fired when the player exits PiP mode. |
| Source Selected | `SOURCE_SELECTED` | `event.payload.selectedSource` — array of source objects, each with `mimetype` (string), `url` (string), `id` (string), `bandwidth` (number), `width` (number), `height` (number). |
| Change Source Started | `CHANGE_SOURCE_STARTED` | No payload. Fired when a new media source begins loading (e.g., after `loadMedia()`). |
| Change Source Ended | `CHANGE_SOURCE_ENDED` | No payload. Fired when the new media source has been applied. |
| Autoplay Failed | `AUTOPLAY_FAILED` | `event.payload` — object with `error` (string, browser's autoplay rejection reason). |
| Mute Change | `MUTE_CHANGE` | `event.payload.mute` — boolean, the new mute state. |
| Playback Start | `PLAYBACK_START` | No payload. Fired once per session when the first play begins (differs from `FIRST_PLAY` in that it fires after buffering completes). |
| Playback Ended | `PLAYBACK_ENDED` | No payload. Fired when all media in the playlist or single entry finishes. |
| Ad Started | `AD_STARTED` | `event.payload.adType` — string (`"preroll"`, `"midroll"`, `"postroll"`). `event.payload.adPosition` — number (ad index). |
| Ad Completed | `AD_COMPLETED` | `event.payload.adType` — string. `event.payload.adPosition` — number. |
| Ad Skipped | `AD_SKIPPED` | `event.payload.adType` — string. `event.payload.adPosition` — number. |

```html
<script>
  window.player = player;

  function onPlay()  { console.log('PLAY'); }
  function onPause() { console.log('PAUSE'); }
  function onEnded() { console.log('ENDED'); }
  function onError(ev){ console.error('ERROR', ev && ev.payload); }
  function onSeeking() { console.log('SEEKING...'); }
  function onSeeked()  { console.log('SEEKED'); }
  function onTimeUpdate() { console.log("currentTime: ", player.currentTime); }

  player.ready().then(() => {
    console.log("player is ready!");
    const E = player.Event.Core;
    // bind to events:  
    player.addEventListener(E.PLAY,        onPlay);
    player.addEventListener(E.PAUSE,       onPause);
    player.addEventListener(E.ENDED,       onEnded);
    player.addEventListener(E.ERROR,       onError);
    player.addEventListener(E.TIME_UPDATE, onTimeUpdate);
    player.addEventListener(E.SEEKING,     onSeeking);
    player.addEventListener(E.SEEKED,      onSeeked);
  });

  window.dispose = function() {
    console.log('disposing...');
    const E = player.Event.Core;
    window.player.removeEventListener(E.PLAY,        onPlay);
    window.player.removeEventListener(E.PAUSE,       onPause);
    window.player.removeEventListener(E.ENDED,       onEnded);
    window.player.removeEventListener(E.ERROR,       onError);
    window.player.removeEventListener(E.TIME_UPDATE, onTimeUpdate);
    window.player.removeEventListener(E.SEEKING,     onSeeking);
    window.player.removeEventListener(E.SEEKED,      onSeeked);
  }

</script>

```

## 6.2 PlayKit Plugin Ecosystem

The Kaltura Player v7 (PlayKit) supports 30+ plugins that extend playback with interactive features. Plugins are configured via the `plugins` block in `KalturaPlayer.setup()`:

```javascript
const player = KalturaPlayer.setup({
  targetId: 'kplayer',
  provider: { partnerId: PARTNER_ID, uiConfId: UICONF_ID, ks: KS },
  plugins: {
    dualscreen: {},       // enable Dual Screen plugin
    transcript: {},       // enable Transcript plugin
    navigation: {}        // enable Navigation plugin
  }
});
```

**Key plugins and their configuration parameters:**

### Dual Screen (`dualscreen`)

Multi-stream PIP / side-by-side layout switching for entries with a secondary stream (e.g., slides + presenter).

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `layout` | string | `"pip"` | Initial layout: `"pip"` (picture-in-picture), `"sbs"` (side-by-side), `"single"` (primary only), `"singleSecondary"` (secondary only) |
| `mainViewEntryId` | string | (auto) | Entry ID for the main (primary) view |
| `secondaryViewEntryId` | string | (auto) | Entry ID for the secondary view |
| `pip.position` | string | `"bottom-right"` | PiP window position: `"top-left"`, `"top-right"`, `"bottom-left"`, `"bottom-right"` |
| `inverse` | boolean | `false` | Swap primary and secondary media in the layout |
| `childSizeMultiplier` | number | `0.3` | PiP window size as a fraction of the player (0.0 - 1.0) |

```javascript
plugins: {
  dualscreen: {
    layout: 'sbs',
    inverse: false,
    childSizeMultiplier: 0.3
  }
}
```

### Navigation (`navigation`)

Chapter-based navigation with thumbnails from cue points defined on the entry.

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `position` | string | `"right"` | Panel position: `"right"`, `"left"`, `"top"`, `"bottom"` |
| `expandOnFirstPlay` | boolean | `true` | Auto-expand the navigation panel on first play |
| `visible` | boolean | `true` | Show the navigation panel |
| `itemsOrder.bySortOrder` | boolean | `true` | Sort chapters by the cue point `sortOrder` field |

```javascript
plugins: {
  navigation: {
    position: 'right',
    expandOnFirstPlay: true
  }
}
```

### Transcript (`transcript`)

Searchable transcript overlay synced to playback, using caption assets on the entry.

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `position` | string | `"right"` | Panel position: `"right"`, `"left"`, `"top"`, `"bottom"` |
| `expandOnFirstPlay` | boolean | `true` | Auto-expand the transcript panel on first play |
| `visible` | boolean | `true` | Show the transcript panel |
| `showTime` | boolean | `true` | Display timestamps next to each line |
| `scrollOffset` | number | `0` | Pixels to offset auto-scroll from the top |
| `searchDebounceTimeout` | number | `250` | Milliseconds to debounce search input |
| `searchNextPrevVisible` | boolean | `true` | Show next/previous navigation in search results |
| `downloadDisabled` | boolean | `false` | Hide the transcript download button |

```javascript
plugins: {
  transcript: {
    position: 'right',
    expandOnFirstPlay: true,
    showTime: true,
    downloadDisabled: false
  }
}
```

### Q&A (`qna`)

Live Q&A panel for virtual events, enabling audience questions and moderator responses.

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `position` | string | `"right"` | Panel position: `"right"`, `"left"` |
| `expandOnFirstPlay` | boolean | `false` | Auto-expand the Q&A panel on first play |
| `visible` | boolean | `true` | Show the Q&A panel |
| `dateFormat` | string | `"mmmm do, yyyy"` | Date display format for Q&A entries |
| `bannerDuration` | number | `5000` | Banner notification duration in milliseconds |

```javascript
plugins: {
  qna: {
    position: 'right',
    expandOnFirstPlay: false
  }
}
```

### Hotspots (`hotspots`)

Clickable overlay hotspots on video, defined via cue points with custom data.

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `visible` | boolean | `true` | Show hotspot overlays |

```javascript
plugins: {
  hotspots: {}
}
```

Hotspot content, position, and timing are defined by cue points on the entry (via the `cuePoint` API service), not by plugin config. The plugin reads these cue points and renders them at the specified times.

### In-Video Quiz (IVQ) (`ivq`)

Interactive quizzes during playback, pausing the video to present questions at configured cue points.

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `visible` | boolean | `true` | Show quiz overlays |

```javascript
plugins: {
  ivq: {}
}
```

Quiz questions, answers, and timing are defined by cue points on the entry (created via the `quiz` plugin in KMC or through the API). The IVQ plugin renders them during playback.

### SEO (`seo`)

Auto-generates JSON-LD structured data (`VideoObject` schema) for video entries to improve search engine discoverability.

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `includeDescription` | boolean | `true` | Include the entry description in the JSON-LD output |
| `includeThumbnail` | boolean | `true` | Include the thumbnail URL in the JSON-LD output |
| `includeUploadDate` | boolean | `true` | Include the upload date in the JSON-LD output |

```javascript
plugins: {
  seo: {}
}
```

### Downloads (`downloads`)

Adds a download button to the player UI that lists available flavor assets (transcoded versions) for download.

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `flavorParamIds` | string | `""` | Comma-separated flavor param IDs to offer for download. Empty string means all available flavors. |
| `presetName` | string | `""` | Name for the download preset group |
| `displayFlavors` | boolean | `true` | Show individual flavor selection (resolution/bitrate) in the download menu |
| `displayCaptions` | boolean | `true` | Show caption download options in the download menu |
| `displayAttachments` | boolean | `true` | Show attachment download options in the download menu |

```javascript
plugins: {
  downloads: {
    flavorParamIds: '',
    displayFlavors: true,
    displayCaptions: true
  }
}
```

### KAVA (`kava`)

Built-in analytics event reporting that sends playback metrics to the Kaltura Analytics system.

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `partnerId` | number | (from provider) | Override the partner ID for analytics reporting |
| `entryId` | string | (from media) | Override the entry ID for analytics reporting |
| `ks` | string | (from provider) | Override the KS for analytics reporting |
| `tamperAnalyticsHandler` | function | `null` | Callback to modify analytics events before sending. Receives the event object and returns modified event or `false` to cancel. |
| `customVar1` | string | `""` | Custom variable 1 (passed to analytics backend) |
| `customVar2` | string | `""` | Custom variable 2 |
| `customVar3` | string | `""` | Custom variable 3 |

```javascript
plugins: {
  kava: {
    customVar1: 'department-engineering',
    customVar2: 'campaign-q4'
  }
}
```

Three shared infrastructure packages power the interactive plugins: `kaltura-cuepoints` (temporal markers), `ui-managers` (shared UI components), and `timeline` (timeline visualization). These are bundled automatically when the plugin is enabled.

> Plugin availability depends on your player configuration (`uiConfId`). Configure plugins in the KMC under Studio > TV Platform (select a player, then edit its plugins) or via the `plugins` config block in `KalturaPlayer.setup()`.

## 6.3 Player Runtime API

After the player is created with `KalturaPlayer.setup()`, you can control plugins and player behavior at runtime using the service and plugin APIs.

### player.getService(name)

Retrieve a plugin service by name. Returns `undefined` if the plugin is not loaded for the current player configuration.

```javascript
var svc = player.getService('dualScreen');
if (svc) {
  svc.ready.then(function() {
    console.log('Dual Screen service is ready');
  });
} else {
  console.log('Dual Screen plugin not available in this player config');
}
```

| Method | Returns | Description |
|--------|---------|-------------|
| `player.getService(name)` | service object or `undefined` | Get a plugin's service interface. The `name` is the service registration name (e.g., `'dualScreen'`, `'sidePanels'`). |
| `service.ready` | Promise | Resolves when the service has finished initializing (e.g., secondary media is loaded for dual screen). |

### player.plugins.*

Access plugin instances directly to call runtime methods. Each plugin is accessible by its config key:

```javascript
// Access the Dual Screen plugin instance
var ds = player.plugins.dualscreen;

// Switch layouts at runtime (after service is ready)
var svc = player.getService('dualScreen');
svc.ready.then(function() {
  ds._switchToPIP({ force: true }, true);        // Switch to PiP layout
  ds._switchToSideBySide({ force: true }, true);  // Switch to side-by-side
  ds._switchToSingleMedia({ force: true }, true); // Switch to single view
  ds._switchToInversePIP({ force: true }, true);  // Switch to inverse PiP
});
```

> `player.configure()` only sets the initial config. It does not trigger runtime changes for plugins like Dual Screen. To control plugins at runtime, use the plugin instance methods (e.g., `player.plugins.dualscreen._switchTo*()`) after the service `ready` promise resolves.

### player.configure(config)

Updates player configuration at runtime. Effective for `playback` and `ui` settings, but **not** for plugin runtime state changes (plugins read config only at setup time):

```javascript
// These work at runtime:
player.configure({ playback: { volume: 0.5 } });
player.configure({ ui: { css: '.custom { color: red; }' } });

// This does NOT trigger a plugin layout change at runtime:
player.configure({ plugins: { dualscreen: { layout: 'sbs' } } });
// Instead, use: player.plugins.dualscreen._switchToSideBySide({ force: true }, true);
```

### player.destroy()

Destroys the player instance, removing all event listeners, stopping playback, and cleaning up the DOM. Call this when removing the player from the page:

```javascript
player.destroy();
```


# 7. Server-Side KS for Player

Generate a scoped USER KS (type=0) for player embeds. Use specific privileges to control what the player can access:

```bash
curl -X POST "$KALTURA_SERVICE_URL/service/session/action/start" \
  -d "format=1" \
  -d "partnerId=$KALTURA_PARTNER_ID" \
  -d "secret=$KALTURA_ADMIN_SECRET" \
  -d "type=0" \
  -d "userId=viewer@example.com" \
  -d "expiry=3600" \
  -d "privileges=sview:ENTRY_ID,appid:myapp-example.com,privacycontext:MY_PORTAL"
```

**Recommended player KS privileges:**

| Privilege | Purpose |
|-----------|---------|
| `sview:ENTRY_ID` | Restrict playback to a specific entry (or `sview:*` for all accessible entries) |
| `appid:APP_NAME-APP_DOMAIN` | Analytics tracking — identifies which app/domain generated the playback |
| `privacycontext:CATEGORY_NAME` | Scope access to entries in a specific privacy-enabled category |
| `setrole:PLAYBACK_BASE_ROLE` | Restrict the KS to read-only playback operations |
| `enableentitlement` | Enforce category entitlement checks |

## 7.1 IP Tokenization for CDN-Protected Content

When CDN tokenization is enforced on your account, the player KS must include the viewer's IP address so the CDN can validate the request:

1. **Server looks up the viewer's IP** from the HTTP request
2. **Generates a KS with `iprestrict:IP`** to bind the session to that IP
3. **Configures the player** to use HLS-only streaming (required for IP-tokenized delivery)

```javascript
const player = KalturaPlayer.setup({
  targetId: 'kplayer',
  provider: {
    partnerId: PARTNER_ID,
    uiConfId: UICONF_ID,
    ks: IP_RESTRICTED_KS  // KS includes iprestrict:VIEWER_IP
  },
  playback: {
    autoplay: true,
    streamPriority: [
      { engine: 'html5', format: 'hls' }  // Force HLS for CDN tokenization
    ]
  }
});
```

> IP tokenization requires account-level CDN configuration. Contact your Kaltura specialist for setup. See [Session Guide section 8.5](KALTURA_SESSION_GUIDE.md) for `iprestrict` privilege details.


# 8. Playback Progress Tracking (Quartile Events)

Track playback milestones (25%, 50%, 75%, 100%) using the `TIME_UPDATE` event:

```javascript
player.ready().then(() => {
  const milestones = { 25: false, 50: false, 75: false, 100: false };

  player.addEventListener(player.Event.Core.TIME_UPDATE, () => {
    const duration = player.duration;
    if (!duration) return;
    const pct = Math.floor((player.currentTime / duration) * 100);

    for (const mark of [25, 50, 75, 100]) {
      if (pct >= mark && !milestones[mark]) {
        milestones[mark] = true;
        console.log('Reached ' + mark + '% milestone');
        // Send analytics beacon: fetch('/api/track', { method: 'POST', body: ... })
      }
    }
  });

  player.addEventListener(player.Event.Core.ENDED, () => {
    if (!milestones[100]) {
      milestones[100] = true;
      console.log('Reached 100% milestone (ENDED)');
    }
  });
});
```

Use quartile tracking for custom engagement analytics, completion-gated content (e.g., unlock next module after 75%), or third-party analytics integration.


# 9. Error Handling

| Scenario | Detection | Resolution |
|----------|-----------|------------|
| Invalid `entryId` | Player shows "Media not found" error | Verify entry exists and has status=2 (READY) via `baseEntry.get` |
| Expired or invalid KS | Player shows access denied | Generate a fresh KS; for production, use AppToken session renewal |
| Player library not loaded | `KalturaPlayer is not defined` | Check the script `src` URL — verify `partnerId` and `uiConfId` are correct |
| Plugin not available | `player.getService('name')` returns undefined | The plugin may not be enabled for this player config — verify `uiConfId` |
| Autoplay blocked by browser | Video loads but does not play | Set `playback.autoplay: true` with `muted: true` — browsers require muted autoplay |

**Retry strategy:** For transient errors (expired KS, network failures), implement KS refresh logic and retry `loadMedia`. For client errors (invalid `entryId`, missing player library, wrong `uiConfId`), fix the configuration before retrying — these will not resolve on their own.

# 10. Best Practices

- **Use USER KS (type=0)** for player embeds. Scope to specific entries with `sview:entryId` when possible.
- **Set short KS expiry** (1-4 hours). For long-running pages, implement KS refresh logic.
- **Use iframe embed for simple integrations.** It handles library loading and configuration automatically.
- **Use JS embed for programmatic control.** When you need play/pause/seek, event listeners, or plugin interaction.
- **Load the player library once.** Cache the `<script>` tag and reuse it across videos. Use `KalturaPlayer.setup()` for each new player instance.
- **Use Access Control profiles** on entries for content protection (geo, domain, IP restrictions) rather than implementing client-side checks.
- **Debug with a generic event listener.** During development, log all player events to understand the event flow:
  ```javascript
  player.ready().then(() => {
    Object.keys(player.Event.Core).forEach(key => {
      player.addEventListener(player.Event.Core[key], () => {
        console.log('Event:', key);
      });
    });
  });
  ```

# 11. Related Guides

- **[Session Guide](KALTURA_SESSION_GUIDE.md)** — Generate KS for access-controlled player embeds
- **[AppTokens](KALTURA_APPTOKENS_API.md)** — Secure KS generation for production player integrations
- **[Content Delivery](KALTURA_CONTENT_DELIVERY_API.md)** — playManifest URLs, delivery profiles, and CDN configuration for playback
- **[eSearch](KALTURA_ESEARCH_API.md)** — Search for entries to embed in the player
- **[REACH](KALTURA_REACH_API.md)** — Add captions and translations that appear in the player
- **[Events Platform](KALTURA_EVENTS_PLATFORM_API.md)** — Create events with live webcast sessions (played via embedded player)
- **[Multi-Stream](KALTURA_MULTI_STREAM_API.md)** — Dual Screen / multi-screen entries for PiP and Side-by-Side playback
- **[Access Control API](KALTURA_ACCESS_CONTROL_API.md)** — Access control profiles for restricting player playback (geo, domain, IP, scheduling)
- **[Categories & Entitlements API](KALTURA_CATEGORIES_AND_ENTITLEMENTS_API.md)** — Category entitlements affecting content visibility
- **[API Getting Started](KALTURA_API_GETTING_STARTED.md)** — Foundation guide covering content model and API patterns
- **[Captions & Transcripts](KALTURA_CAPTIONS_AND_TRANSCRIPTS_API.md)** — Caption assets displayed in the player transcript plugin
- **[Analytics Reports](KALTURA_ANALYTICS_REPORTS_API.md)** — Player events feed analytics reports  
- **[Unisphere Framework](KALTURA_UNISPHERE_FRAMEWORK_API.md)** — Unisphere plugins for player integration (unisphere-service, unisphere, unisphere-genie)
- **[Cue Points & Interactive Video](KALTURA_CUE_POINTS_API.md)** — Chapters, slides, annotations, ads, quizzes, hotspots — data behind player timeline, navigation, and IVQ plugins
- **[Quiz API](KALTURA_QUIZ_API.md)** — Interactive video quiz lifecycle and IVQ player plugin


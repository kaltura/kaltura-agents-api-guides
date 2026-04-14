# Kaltura PlayKit Player: Embedding & Control Guide

Embed Kaltura's PlayKit player in web applications using iframe or dynamic JavaScript. Both methods support KS-based access control, clipping, autoplay, and full programmatic control via the player API.

**Embed Base URL:** `https://cdnapisec.kaltura.com/p/{PARTNER_ID}/embedPlaykitJs/uiconf_id/{PLAYER_ID}` (may differ by region)  
**Auth:** Optional KS for access-controlled content (see [Session Guide](KALTURA_SESSION_GUIDE.md))  
**Format:** HTML embed (iframe) or JavaScript SDK (PlayKit)  

# 1. When to use which embed

- **Iframe embed** – Simplest drop-in, ideal for quick embedding where the host page manages layout only. Works well for sites that restrict JavaScript to first-party code. Control the configuration passed to the player by adding query string params.  
- **Dynamic JS (PlayKit)** – recommended when you need **runtime config**, **start time**, **programmatic control**, or richer integrations. 

# 2. Kaltura Player Iframe Embed

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

# 3. Dynamic JS (PlayKit) embed

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

# 4. JS Control (Play/Pause/Seek/Volume)

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

## 4.1 Binding to JS player events (drive app flows)

The Kaltura player exposes a DOM-style event system and a Promise for readiness. Use it for analytics beacons, UI reactions, gated flows, etc.  

**Player core events consist of two event types:**

- **HTML5 Video Events** — Standard events from the underlying `<video>` element: `PLAY`, `PAUSE`, `ENDED`, `SEEKING`, `SEEKED`, `TIME_UPDATE`, `VOLUME_CHANGE`, `WAITING`, `PLAYING`, `CANPLAY`, `LOADED_METADATA`, `LOADED_DATA`, `DURATION_CHANGE`, `RATE_CHANGE`, `ERROR`.  
- **Player Custom Events** — Events specific to the Kaltura player that extend beyond standard HTML5 video: `PLAYER_STATE_CHANGED`, `MEDIA_LOADED`, `FIRST_PLAY`, `FIRST_PLAYING`, `TRACKS_CHANGED`, `TEXT_TRACK_CHANGED`, `AUDIO_TRACK_CHANGED`, `VIDEO_TRACK_CHANGED`, `ENTER_FULLSCREEN`, `EXIT_FULLSCREEN`, `ENTER_PICTURE_IN_PICTURE`, `EXIT_PICTURE_IN_PICTURE`, `SOURCE_SELECTED`, `CHANGE_SOURCE_STARTED`, `CHANGE_SOURCE_ENDED`, `AUTOPLAY_FAILED`, `MUTE_CHANGE`, `PLAYBACK_START`, `PLAYBACK_ENDED`, `AD_STARTED`, `AD_COMPLETED`, `AD_SKIPPED`.  

All core events are accessible via `player.Event.Core` as shown in the example below.

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

## 4.2 PlayKit Plugin Ecosystem

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

**Key plugins:**

| Plugin | Config Key | Purpose |
|--------|-----------|---------|
| Dual Screen | `dualscreen` | Multi-stream PIP / side-by-side layout switching |
| Navigation | `navigation` | Chapter-based navigation with thumbnails |
| Transcript | `transcript` | Searchable transcript overlay synced to playback |
| Q&A | `qna` | Live Q&A panel for virtual events |
| Hotspots | `hotspots` | Clickable overlay hotspots on video |
| In-Video Quiz (IVQ) | `ivq` | Interactive quizzes during playback |
| SEO | `seo` | Auto-generates JSON-LD structured data for video entries |
| Downloads | `downloads` | Download button for available flavors |
| KAVA | `kava` | Built-in analytics event reporting |

Three shared infrastructure packages power the interactive plugins: `kaltura-cuepoints` (temporal markers), `ui-managers` (shared UI components), and `timeline` (timeline visualization). These are bundled automatically when the plugin is enabled.

> Plugin availability depends on your player configuration (`uiConfId`). Configure plugins in the KMC under Studio > TV Platform (select a player, then edit its plugins) or via the `plugins` config block in `KalturaPlayer.setup()`.


# 5. Server-Side KS for Player

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

## 5.1 IP Tokenization for CDN-Protected Content

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


# 6. Playback Progress Tracking (Quartile Events)

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


# 7. Error Handling

| Scenario | Detection | Resolution |
|----------|-----------|------------|
| Invalid `entryId` | Player shows "Media not found" error | Verify entry exists and has status=2 (READY) via `baseEntry.get` |
| Expired or invalid KS | Player shows access denied | Generate a fresh KS; for production, use AppToken session renewal |
| Player library not loaded | `KalturaPlayer is not defined` | Check the script `src` URL — verify `partnerId` and `uiConfId` are correct |
| Plugin not available | `player.getService('name')` returns undefined | The plugin may not be enabled for this player config — verify `uiConfId` |
| Autoplay blocked by browser | Video loads but does not play | Set `playback.autoplay: true` with `muted: true` — browsers require muted autoplay |

**Retry strategy:** For transient errors (expired KS, network failures), implement KS refresh logic and retry `loadMedia`. For client errors (invalid `entryId`, missing player library, wrong `uiConfId`), fix the configuration before retrying — these will not resolve on their own.

# 8. Best Practices

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

# 9. Related Guides

- **[Session Guide](KALTURA_SESSION_GUIDE.md)** — Generate KS for access-controlled player embeds
- **[AppTokens](KALTURA_APPTOKENS_API.md)** — Secure KS generation for production player integrations
- **[Upload & Delivery](KALTURA_UPLOAD_AND_DELIVERY_API.md)** — Upload content and get playManifest URLs for playback
- **[eSearch](KALTURA_ESEARCH_API.md)** — Search for entries to embed in the player
- **[REACH](KALTURA_REACH_API.md)** — Add captions and translations that appear in the player
- **[Events Platform](KALTURA_EVENTS_PLATFORM_API.md)** — Create events with live webcast sessions (played via embedded player)
- **[Multi-Stream](KALTURA_MULTI_STREAM_API.md)** — Dual Screen / multi-screen entries for PiP and Side-by-Side playback
- **[Categories & Access Control API](KALTURA_CATEGORIES_AND_ACCESS_CONTROL_API.md)** — Access control profiles for restricting player playback (geo, domain, IP, scheduling)
- **[API Getting Started](KALTURA_API_GETTING_STARTED.md)** — Foundation guide covering content model and API patterns
- **[Captions & Transcripts](KALTURA_CAPTIONS_AND_TRANSCRIPTS_API.md)** — Caption assets displayed in the player transcript plugin
- **[Analytics Reports](KALTURA_ANALYTICS_REPORTS_API.md)** — Player events feed analytics reports  
- **[Unisphere Framework](KALTURA_UNISPHERE_FRAMEWORK_API.md)** — Unisphere plugins for player integration (unisphere-service, unisphere, unisphere-genie)


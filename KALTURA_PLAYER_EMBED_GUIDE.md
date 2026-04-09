# Kaltura PlayKit Player: Embedding & Control Guide

Embed Kaltura's PlayKit player in web applications using iframe or dynamic JavaScript. Both methods support KS-based access control, clipping, autoplay, and full programmatic control via the player API.

**Embed Base URL:** `https://cdnapisec.kaltura.com/p/{PARTNER_ID}/embedPlaykitJs/uiconf_id/{PLAYER_ID}` (may differ by region)
**Auth:** Optional KS for access-controlled content (see [Session Guide](KALTURA_SESSION_GUIDE.md))
**Format:** HTML embed (iframe) or JavaScript SDK (PlayKit)

# 1. When to use which embed

- **Iframe embed** – Simplest drop-in, great when you don’t need programmatic control from the host page. The iframe embed is good for sites that don't allow third-party JavaScript to be embedded in their pages. It is possible to control the configuration passed to the player by adding query strings params.   
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
- {PLAYER_INSTANCE_ID} - is your Player Instance ID from the [Player Studio](https://kmc.kaltura.com/index.php/kmcng/studio/v3).  
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

These APIs are part of the web player’s base interface (play/pause, `currentTime` getter/setter, `volume` getter/setter).  [See Kaltura Player API Docs for more](https://kaltura.github.io/kaltura-player-js/docs/guides.html)

## 4.1 Binding to JS player events (drive app flows)

The Kaltura player exposes a DOM-style event system and a Promise for readiness. Use it for analytics beacons, UI reactions, gated flows, etc.  

**Player core events consist of two event types:**

- **HTML5 Video Events** - These are various events sent by the browser when handling media that is embedded using the `<video>` element. The player runs on top of the HTML video element, which may trigger the events. [Information about these types of events can be found here](https://developer.mozilla.org/en-US/docs/Web/API/Document_Object_Model/Events#media).  
- **Player Custom Events** - These are special events that indicate a change in the state of the player that does not exist in the HTML5 video event list and that are related to the integral behavior of the player. These can include ads, switching to fullscreen, and tracks events.  
- [The full core events list can be found here](https://github.com/kaltura/playkit-js/blob/master/src/event/event-type.ts).

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


# 5. Related Guides

- **[Session Guide](KALTURA_SESSION_GUIDE.md)** — Generate KS for access-controlled player embeds
- **[AppTokens](KALTURA_APPTOKENS_API.md)** — Secure KS generation for production player integrations
- **[Upload & Delivery](KALTURA_UPLOAD_AND_DELIVERY_API.md)** — Upload content and get playManifest URLs for playback
- **[eSearch](KALTURA_ESEARCH_API.md)** — Search for entries to embed in the player
- **[REACH](KALTURA_REACH_API.md)** — Add captions and translations that appear in the player
- **[Events Platform](KALTURA_EVENTS_PLATFORM_API.md)** — Create events with live webcast sessions (played via embedded player)
- **[Multi-Stream](KALTURA_MULTI_STREAM_API.md)** — Dual Screen / multi-screen entries for PiP and Side-by-Side playback


# Kaltura Captions Editor API

The Captions Editor (Captions Studio) provides an interactive caption editing interface with synchronized video playback and audio waveform visualization. Users can create, edit, and time captions directly in the browser.

**Base URL:** `https://www.kaltura.com/apps/captionstudio/latest/index.html`  
**Auth:** KS passed via URL parameter  
**Format:** iframe embed  

<!-- Sections: 1.When to Use | 2.Prerequisites | 3.Embedding via iframe | 4.URL Parameters | 5.Workflow | 6.Editor Features | 7.Host-Page Integration | 8.Error Handling | 9.Best Practices | 10.Related Guides -->


# 1. When to Use

- **Accessibility compliance** — Let content creators add and refine captions in a visual editor rather than editing raw SRT files  
- **Post-production captioning** — Correct AI-generated captions from REACH with precise timing adjustments  
- **Localization workflows** — Edit translated captions with synchronized playback for accuracy verification  


# 2. Prerequisites

The entry must have an existing caption asset before opening the editor. Create one using the Captions & Transcripts API if needed:

```bash
# Create a blank SRT caption asset for the entry
curl -X POST "$KALTURA_SERVICE_URL/service/caption_captionAsset/action/add" \
  -d "ks=$KALTURA_KS" \
  -d "format=1" \
  -d "entryId=$KALTURA_ENTRY_ID" \
  -d "captionAsset[objectType]=KalturaCaptionAsset" \
  -d "captionAsset[language]=English" \
  -d "captionAsset[format]=1" \
  -d "captionAsset[label]=English"
```

See the [Captions & Transcripts Guide](KALTURA_CAPTIONS_AND_TRANSCRIPTS_API.md) for full caption asset management.


# 3. Embedding via iframe

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


# 4. URL Parameters

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `pid` | string | yes | Kaltura partner ID |
| `ks` | string | yes | Kaltura Session token |
| `entryid` | string | yes | Media entry ID to edit captions for |
| `assetid` | string | yes | Caption asset ID to edit |
| `maxcharsperline` | number | no | Maximum characters per caption line (e.g., `42`). When set, the editor shows visual indicators for lines exceeding this limit |
| `cdnurl` | string | yes | CDN base URL for loading the player (e.g., `https://cdnapisec.kaltura.com`) |
| `serviceurl` | string | yes | Kaltura API base URL without `/api_v3` suffix (e.g., `https://www.kaltura.com`) |

Build the iframe URL by appending all parameters as query string values. URL-encode the KS value since it may contain characters like `+` and `/`:

```javascript
var params = new URLSearchParams({
  pid: PARTNER_ID,
  ks: KS,
  entryid: ENTRY_ID,
  assetid: CAPTION_ASSET_ID,
  maxcharsperline: '42',
  cdnurl: 'https://cdnapisec.kaltura.com',
  serviceurl: 'https://www.kaltura.com'
});
var src = 'https://www.kaltura.com/apps/captionstudio/latest/index.html?' + params.toString();
document.getElementById('caption-editor').src = src;
```


# 5. Workflow

1. List caption assets for the entry using `captionAsset.list`  
2. Pass the desired `assetid` to the Captions Editor iframe  
3. The user edits captions in the browser (timing, text, formatting)  
4. The editor saves changes directly to the caption asset via the Kaltura API  
5. Updated captions are immediately available for playback  


# 6. Editor Features

- **Waveform visualization** — Audio waveform display for precise caption timing  
- **Synchronized playback** — Video plays in sync with the caption timeline; click a caption to seek to that position  
- **Inline text editing** — Edit caption text, start/end times, and line breaks directly in the timeline  
- **Keyboard shortcuts** — Play/pause, jump to next/previous caption, split/merge captions  
- **Character limit enforcement** — `maxcharsperline` parameter enforces line length limits with visual indicators  
- **Auto-save** — Changes are saved to the caption asset automatically  


# 7. Host-Page Integration

The Captions Editor iframe does not expose a `postMessage` API. There are no events emitted to the host page for save actions, edit state changes, or editor close actions. The editor saves changes directly to the Kaltura caption asset via the Kaltura API, bypassing the host page entirely.

## Detecting Caption Changes

To detect when a user has saved edits in the Captions Editor, poll the caption asset for changes using `captionAsset.get` and compare the `updatedAt` timestamp:

```bash
# Get the caption asset to check for updates
curl -X POST "$KALTURA_SERVICE_URL/service/caption_captionAsset/action/get" \
  -d "ks=$KALTURA_KS" \
  -d "format=1" \
  -d "captionAssetId=$CAPTION_ASSET_ID"
```

The response includes `updatedAt` (Unix timestamp). Compare this value against the timestamp recorded when the editor was opened. A newer `updatedAt` indicates the user has saved changes.

```javascript
// Record the initial timestamp when opening the editor
var initialUpdatedAt = captionAsset.updatedAt;

// Poll periodically or check when the user closes the editor
function checkForChanges() {
  // fetch captionAsset.get and compare updatedAt
  if (result.updatedAt > initialUpdatedAt) {
    console.log("Captions were modified");
    // Refresh player, update UI, etc.
  }
}
```

## Retrieving Updated Caption Content

After detecting changes, download the updated caption file:

```bash
# Get the download URL for the updated caption content
curl -X POST "$KALTURA_SERVICE_URL/service/caption_captionAsset/action/getUrl" \
  -d "ks=$KALTURA_KS" \
  -d "format=1" \
  -d "id=$CAPTION_ASSET_ID"
```

## Editor Lifecycle

The editor runs entirely within the iframe. To control its lifecycle from the host page:

- **Open the editor** — Set the iframe `src` to the editor URL with parameters  
- **Close the editor** — Remove the iframe from the DOM or set `src` to `about:blank`  
- **Refresh for a new asset** — Update the iframe `src` with the new `assetid` parameter  

There is no programmatic way to trigger save, undo, or other editor actions from the host page.


# 8. Error Handling

- **Editor load failures** — If the iframe fails to load, verify the `ks` is valid and the `assetid` exists for the given `entryid`. An expired KS shows a login prompt; an invalid asset ID shows an empty editor.  
- **Mixed content errors** — Always include `cdnurl=https://cdnapisec.kaltura.com` in the iframe URL. Without it, the editor attempts to load the player from HTTP, which is blocked by browser security policies.  
- **KS expiry during editing** — The editor does not automatically renew expired sessions. If an editing session exceeds the KS TTL, saves will fail silently. Generate a KS with sufficient expiry for the expected session duration.


# 9. Best Practices

- **Create caption assets before opening the editor.** The Captions Studio requires an existing caption asset ID. Create a blank one programmatically if the entry has no captions yet.  
- **Always include `cdnurl`.** The `cdnurl` parameter is required to avoid Mixed Content errors. Use `https://cdnapisec.kaltura.com`.  
- **Use HTTPS for all embed URLs.** The iframe URL and all parameters must use HTTPS for secure media access and iframe security policies.  
- **Handle session expiry.** Generate a KS with sufficient expiry for the expected editing session. A 2-hour KS covers most caption editing workflows.


# 10. Related Guides

- **[Experience Components Overview](KALTURA_EXPERIENCE_COMPONENTS_API.md)** — Index of all embeddable components with shared guidelines  
- **[Captions & Transcripts](KALTURA_CAPTIONS_AND_TRANSCRIPTS_API.md)** — Caption asset CRUD, SRT/VTT/DFXP formats, multi-language support  
- **[Session Guide](KALTURA_SESSION_GUIDE.md)** — KS generation and privilege management  
- **[REACH API](KALTURA_REACH_API.md)** — AI-generated captions that the editor can refine

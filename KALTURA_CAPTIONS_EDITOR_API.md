# Kaltura Captions Editor API

The Captions Editor (Captions Studio) provides an interactive caption editing interface with synchronized video playback and audio waveform visualization. Users can create, edit, and time captions directly in the browser.

**Base URL:** `https://www.kaltura.com/apps/captionstudio/latest/index.html`  
**Auth:** KS passed via URL parameter  
**Format:** iframe embed  


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
  -d "entryId=ENTRY_ID" \
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

| Parameter | Required | Description |
|-----------|----------|-------------|
| `pid` | yes | Kaltura partner ID |
| `ks` | yes | Kaltura Session token |
| `entryid` | yes | Media entry ID to edit captions for |
| `assetid` | yes | Caption asset ID to edit |
| `maxcharsperline` | no | Maximum characters per caption line (e.g., 42) |
| `cdnurl` | yes | CDN base URL (e.g., `https://cdnapisec.kaltura.com`) |
| `serviceurl` | yes | API base URL without `/api_v3` (e.g., `https://www.kaltura.com`) |


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


# 7. Error Handling

- **Editor load failures** — If the iframe fails to load, verify the `ks` is valid and the `assetid` exists for the given `entryid`. An expired KS shows a login prompt; an invalid asset ID shows an empty editor.  
- **Mixed content errors** — Always include `cdnurl=https://cdnapisec.kaltura.com` in the iframe URL. Without it, the editor attempts to load the player from HTTP, which is blocked by browser security policies.  
- **KS expiry during editing** — The editor does not automatically renew expired sessions. If an editing session exceeds the KS TTL, saves will fail silently. Generate a KS with sufficient expiry for the expected session duration.


# 8. Best Practices

- **Create caption assets before opening the editor.** The Captions Studio requires an existing caption asset ID. Create a blank one programmatically if the entry has no captions yet.  
- **Always include `cdnurl`.** The `cdnurl` parameter is required to avoid Mixed Content errors. Use `https://cdnapisec.kaltura.com`.  
- **Use HTTPS for all embed URLs.** The iframe URL and all parameters must use HTTPS for secure media access and iframe security policies.  
- **Handle session expiry.** Generate a KS with sufficient expiry for the expected editing session. A 2-hour KS covers most caption editing workflows.


# 9. Related Guides

- **[Experience Components Overview](KALTURA_EXPERIENCE_COMPONENTS_API.md)** — Index of all embeddable components with shared guidelines  
- **[Captions & Transcripts](KALTURA_CAPTIONS_AND_TRANSCRIPTS_API.md)** — Caption asset CRUD, SRT/VTT/DFXP formats, multi-language support  
- **[Session Guide](KALTURA_SESSION_GUIDE.md)** — KS generation and privilege management  
- **[REACH API](KALTURA_REACH_API.md)** — AI-generated captions that the editor can refine

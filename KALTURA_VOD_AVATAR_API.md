# Kaltura VOD Avatar Studio API

The VOD Avatar Studio is a Unisphere widget for creating pre-recorded avatar video presentations. Users select an AI avatar, write or paste a script, and the studio generates a professional video of the avatar delivering the content. The generated video is saved as a Kaltura entry.

**Base URL:** `https://unisphere.nvp1.ovp.kaltura.com/v1` (US region)  
**Auth:** KS passed via runtime settings  
**Format:** ES module JavaScript embed (Unisphere runtime)  

This guide covers the **VOD (Video on Demand) Avatar Studio** — a tool for generating pre-recorded avatar videos from scripts. For **real-time conversational avatars** that hold live AI-powered conversations with users, see the [Conversational Avatar Embed](KALTURA_CONVERSATIONAL_AVATAR_API.md).


# 1. When to Use

- **Training video production** — Generate professional training videos with AI presenters without recording equipment or on-camera talent  
- **Content localization** — Create avatar-narrated versions of content in multiple languages from translated scripts  
- **Executive communications** — Produce avatar-delivered announcements, updates, or presentations from written scripts  
- **Course creation** — Build educational video content at scale by scripting lessons and generating avatar presentations  

# 2. Prerequisites

- A valid Kaltura Session (KS) with admin privileges (type=2) for avatar service access and media entry creation (see [Session Guide](KALTURA_SESSION_GUIDE.md))  
- An avatar model and character configured on your account — contact your Kaltura account manager to provision the VOD Avatar feature and available presenters  
- The Unisphere widget loader URL for your region (default: `https://unisphere.nvp1.ovp.kaltura.com/v1`)  


# 3. Architecture

The VOD Avatar Studio has one runtime:

| Runtime | Widget Name | Purpose |
|---------|------------|---------|
| `studio` | `unisphere.widget.vod-avatars` | Avatar studio — script editor, avatar selection, video generation, and preview |

The widget communicates with the Kaltura Avatar backend service for avatar rendering and video generation. The generated videos are saved as standard Kaltura media entries accessible through the Kaltura API.

**VOD Avatar vs. Conversational Avatar:**

| Feature | VOD Avatar Studio | Conversational Avatar |
|---------|------------------|----------------------|
| **Interaction** | Pre-recorded — script in, video out | Real-time — live conversation via WebRTC |
| **Use case** | Training videos, presentations, announcements | Interview practice, coaching, conversational agents |
| **Embedding** | Unisphere widget (ES module) | iframe SDK or WebRTC SDK |
| **Output** | Kaltura media entry (video file) | Live audio/video stream |
| **Guide** | This guide | [Conversational Avatar Embed](KALTURA_CONVERSATIONAL_AVATAR_API.md) |


# 4. Embedding

Load the Unisphere loader and configure the VOD Avatar Studio runtime:

```html
<div id="avatar-studio" style="width: 100%; height: 100vh;"></div>
<script type="module">
  import { loader } from "https://unisphere.nvp1.ovp.kaltura.com/v1/loader/index.esm.js";

  const workspace = await loader({
    serverUrl: "https://unisphere.nvp1.ovp.kaltura.com/v1",
    appId: "my-app",
    appVersion: "1.0.0",
    session: { ks: "$KALTURA_KS", partnerId: $KALTURA_PARTNER_ID },
    runtimes: [{
      widgetName: "unisphere.widget.vod-avatars",
      runtimeName: "studio",
      settings: {
        ks: "$KALTURA_KS",
        partnerId: $KALTURA_PARTNER_ID,
        kalturaServerURI: "https://www.kaltura.com"
      },
      visuals: [{
        type: "page",
        target: "avatar-studio",
        settings: {}
      }]
    }]
  });

  // Wait for the studio runtime to load
  const studio = await workspace.getRuntimeAsync(
    "unisphere.widget.vod-avatars",
    "studio"
  );
</script>
```

The studio renders a full-page UI inside the container element. Users interact with the studio through the rendered interface to select avatars, write scripts, and generate videos.


# 5. Runtime Settings

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `ks` | string | yes | Kaltura Session token (admin KS recommended) |
| `partnerId` | number | yes | Partner ID (must be a number, not a string) |
| `kalturaServerURI` | string | yes | Kaltura API server URL (e.g., `https://www.kaltura.com`) |

The account must have the VOD Avatar feature enabled. Contact your Kaltura account manager to enable avatar services.


# 6. Studio Workflow

The VOD Avatar Studio provides a guided workflow:

1. **Select an avatar** — Choose from available AI avatar presenters  
2. **Write or paste a script** — Enter the text the avatar will deliver  
3. **Configure presentation** — Set language, style, and delivery options  
4. **Generate video** — The studio submits the script for rendering and tracks progress  
5. **Preview and publish** — Review the generated video and save it as a Kaltura entry  

The generated video is stored as a standard Kaltura media entry, accessible through the Kaltura API for playback, embedding, and further processing (captions, chapters, etc.).


# 7. Host-Page Integration

The VOD Avatar Studio is a self-contained UI. It does not expose programmatic methods for script input, avatar selection, generation triggering, or real-time progress events to the host page. All interaction happens through the rendered studio interface.

To detect when a video has been generated, poll the Kaltura API for new entries created by the studio. The studio saves generated videos as standard media entries owned by the KS user.

## Detecting Generated Videos

Poll `media.list` with a filter on the KS user and creation date to find newly generated avatar videos:

```bash
# List recent entries created by the avatar studio user
curl -X POST "$KALTURA_SERVICE_URL/service/media/action/list" \
  -d "ks=$KALTURA_KS" \
  -d "format=1" \
  -d "filter[objectType]=KalturaMediaEntryFilter" \
  -d "filter[createdAtGreaterThanOrEqual]=$TIMESTAMP" \
  -d "filter[orderBy]=-createdAt" \
  -d "pager[pageSize]=10"
```

Once you have the entry ID, poll `media.get` to check when rendering is complete:

```bash
# Check entry status (status=2 means READY)
curl -X POST "$KALTURA_SERVICE_URL/service/media/action/get" \
  -d "ks=$KALTURA_KS" \
  -d "format=1" \
  -d "entryId=$ENTRY_ID"
```

Entry status values:

| Status | Value | Meaning |
|--------|-------|---------|
| IMPORT | 0 | Entry created, awaiting content |
| PRECONVERT | 1 | Content uploaded, awaiting transcoding |
| READY | 2 | Video is ready for playback |
| ERROR_CONVERTING | -1 | Transcoding failed |

Poll at 10-15 second intervals until `status` equals `2` (READY). Avatar video rendering can take several minutes depending on script length.

## Workspace Lifecycle

The host page can manage the workspace session and lifecycle:

```javascript
// Refresh the KS when it approaches expiry
workspace.session.setData(prev => ({ ...prev, ks: "new-ks-value" }));

// Destroy the workspace when the user navigates away
workspace.kill();
```


# 8. KS Requirements

The VOD Avatar Studio accesses avatar services and creates media entries. Generate the KS server-side with admin privileges:

```bash
curl -X POST "$KALTURA_SERVICE_URL/service/session/action/start" \
  -d "format=1" \
  -d "secret=$KALTURA_ADMIN_SECRET" \
  -d "partnerId=$KALTURA_PARTNER_ID" \
  -d "type=2" \
  -d "userId=admin@example.com" \
  -d "expiry=86400"
```

**Required access:** The KS must have admin privileges (type=2) for avatar service access and media entry creation. The account must have the VOD Avatar feature provisioned.


# 9. Error Handling

- **Blank studio** — If the studio renders empty, verify the KS is valid and the `partnerId` matches your account. The account must have the VOD Avatar feature enabled. Check the browser console for API errors.  
- **No avatars available** — Avatar availability depends on your account configuration. Contact your Kaltura account manager to configure available avatar presenters.  
- **Video generation fails** — Verify the KS has admin privileges (type=2) and sufficient expiry for the generation duration. Long scripts may take several minutes to render.  
- **KS expiry** — Update the workspace session reactively: `workspace.session.setData(prev => ({ ...prev, ks: "new-ks" }))`.  


# 10. Best Practices

- **Generate the KS server-side.** The KS is visible in client-side code — generate it on your backend with admin privileges.  
- **Set `partnerId` as a number.** Unlike most Unisphere widgets that accept string IDs, the VOD Avatar Studio requires `partnerId` as a number type.  
- **Size the container for full-page layout.** The studio works best as a full-page experience with `width: 100%` and `height: 100vh`.  
- **Use HTTPS.** The Unisphere loader and all widget bundles require HTTPS.  
- **Process generated videos.** After generation, the resulting Kaltura entry can be processed with other services — enrich via [REACH](KALTURA_REACH_API.md) (captions, translation, metadata), generate chapters via [Content Lab](KALTURA_CONTENT_LAB_API.md), or set up automated processing via [Agents](KALTURA_AGENTS_MANAGER_API.md).  


# 11. Multi-Region

| Region | Server URL |
|--------|-----------|
| NVP1 (US, default) | `https://unisphere.nvp1.ovp.kaltura.com/v1` |
| IRP2 (EU) | `https://unisphere.irp2.ovp.kaltura.com/v1` |
| FRP2 (DE) | `https://unisphere.frp2.ovp.kaltura.com/v1` |

Set the `serverUrl` in the workspace configuration to match your Kaltura account region.


# 12. Related Guides

- **[Conversational Avatar Embed](KALTURA_CONVERSATIONAL_AVATAR_API.md)** — Real-time AI avatar conversations via iframe SDK or WebRTC — the live counterpart to this pre-recorded studio  
- **[Unisphere Framework](KALTURA_UNISPHERE_FRAMEWORK_API.md)** — The micro-frontend framework that powers this widget: loader, workspace lifecycle, services  
- **[Experience Components Overview](KALTURA_EXPERIENCE_COMPONENTS_API.md)** — Index of all embeddable components with shared guidelines  
- **[REACH API](KALTURA_REACH_API.md)** — Enrichment services: add captions, translations, dubbing, and more to generated avatar videos  
- **[Content Lab API](KALTURA_CONTENT_LAB_API.md)** — Generate summaries, chapters, or clips from avatar videos  
- **[Session Guide](KALTURA_SESSION_GUIDE.md)** — KS generation and privilege management  
- **[AppTokens API](KALTURA_APPTOKENS_API.md)** — Production token management for secure KS generation  

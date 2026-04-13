# Kaltura Express Recorder API

The Express Recorder provides browser-based WebRTC recording — video, audio, and screen sharing. It creates Kaltura entries automatically upon upload.

**Base URL:** `https://www.kaltura.com/apps/expressrecorder/latest/express-recorder.js`  
**Auth:** KS passed via config object  
**Format:** JavaScript embed  


# 1. When to Use

- **User-generated content** — Let employees or students record and submit video directly from your application  
- **Self-service video creation** — Enable video messages, video resumes, or testimonial collection without requiring desktop recording software  
- **Video assessment** — Capture practice presentations, interview recordings, or skill demonstrations  

**Supported browsers:** Chrome, Firefox, Opera (WebRTC required)


# 2. Embedding

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


# 3. Configuration

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


# 4. Events

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


# 5. Methods

| Method | Description |
|--------|-------------|
| `startRecording()` | Programmatically start recording |
| `stopRecording()` | Stop the current recording |
| `upload()` | Upload the recorded media to Kaltura |
| `cancelUpload()` | Cancel an in-progress upload |
| `saveCopy()` | Save a local copy of the recording |


# 6. Error Handling

- **`error` event** — Listen for `error` events on the component instance. The event payload includes a `message` field with details. Common causes: WebRTC not supported (Safari limitations), microphone/camera permissions denied, upload network failure.  
- **KS expiry during recording** — The recorder does not automatically renew expired sessions. If a recording session exceeds the KS TTL, uploads will fail silently. Generate a KS with sufficient expiry for the expected session duration.


# 7. Best Practices

- **Scope the KS.** The KS must include `editadmintags:*` to allow entry creation. Use the minimum additional privileges required.  
- **Verify entry readiness after upload.** After the recorder uploads, the entry goes through transcoding. Poll `media.get` for `status=2` (READY) before redirecting users to playback or caption editing.  
- **Use HTTPS.** The embed URL and all component URLs must use HTTPS for WebRTC and iframe security policies.  
- **Handle session expiry.** Generate a KS with sufficient expiry for the expected recording + upload duration. A 1-hour KS covers most use cases.


# 8. Related Guides

- **[Experience Components Overview](KALTURA_EXPERIENCE_COMPONENTS_API.md)** — Index of all embeddable components with shared guidelines  
- **[Session Guide](KALTURA_SESSION_GUIDE.md)** — KS generation and privilege management  
- **[Upload & Delivery](KALTURA_UPLOAD_AND_DELIVERY_API.md)** — Content lifecycle after the recorder creates entries  
- **[Player Embed Guide](KALTURA_PLAYER_EMBED_GUIDE.md)** — Embed playback for recorded content

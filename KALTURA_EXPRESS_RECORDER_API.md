# Kaltura Express Recorder API

The Express Recorder provides browser-based WebRTC recording — video, audio, and screen sharing. It creates Kaltura entries automatically upon upload.

**Base URL:** `https://www.kaltura.com/apps/expressrecorder/latest/express-recorder.js`  
**Auth:** KS passed via config object  
**Format:** JavaScript embed  

<!-- Sections: 1.When to Use | 2.Prerequisites | 3.Embedding | 4.Configuration | 5.Events | 6.Methods | 7.Error Handling | 8.Best Practices | 9.Related Guides -->


# 1. When to Use

- **User-generated content** — Let employees or students record and submit video directly from your application  
- **Self-service video creation** — Enable video messages, video resumes, or testimonial collection without requiring desktop recording software  
- **Video assessment** — Capture practice presentations, interview recordings, or skill demonstrations  

**Supported browsers:** Chrome, Firefox, Opera (WebRTC required)


# 2. Prerequisites

- **Kaltura Session (KS)** — A KS with `editadmintags:*` privilege is required for the recorder to create entries. See the [Session Guide](KALTURA_SESSION_GUIDE.md) for KS generation details.  
- **Recorder widget loaded from CDN** — Load the Express Recorder JavaScript bundle from the Kaltura CDN (`https://www.kaltura.com/apps/expressrecorder/latest/express-recorder.js`).  
- **Browser with WebRTC and getUserMedia** — The recorder requires WebRTC support for media capture. Chrome, Firefox, and Opera are recommended. The page must be served over HTTPS for camera and microphone access.  


# 3. Embedding

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


# 4. Configuration

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
| `maxRecordingTime` | number | unlimited | Maximum recording duration in seconds. Recording stops automatically when reached |
| `showUploadUI` | boolean | true | Show the upload progress UI after recording |
| `allowUpload` | boolean | true | Enable the upload step after recording. Set `false` to only allow local save via `saveCopy()` |

**KS privileges:** The KS must include `editadmintags:*` to allow the recorder to create entries.


# 5. Events

Listen for events on the component instance:

```javascript
component.instance.addEventListener('mediaUploadStarted', function(e) {
  console.log('Upload started, entryId:', e.detail.entryId);
});
```

| Event | Payload | Description |
|-------|---------|-------------|
| `recordingStarted` | — | User started recording. Fires when the WebRTC media stream begins capturing |
| `recordingEnded` | — | User stopped recording. The recorded blob is available for upload or local save |
| `recordingCancelled` | — | User cancelled the recording. No recorded media is retained |
| `mediaUploadStarted` | `{ entryId: string }` | Upload began. `entryId` is the Kaltura entry ID created for this recording. Use it to poll `media.get` for transcoding status |
| `mediaUploadProgress` | `{ loaded: number, total: number }` | Upload progress. `loaded` is bytes transferred, `total` is total bytes. Calculate percentage as `(loaded / total) * 100` |
| `mediaUploadEnded` | `{ entryId: string }` | Upload completed. The entry exists in Kaltura but may still be transcoding (status=1). Poll `media.get` for `status=2` (READY) before using the entry for playback |
| `mediaUploadCancelled` | — | User cancelled the upload. The entry may have been created but has no content — clean up with `media.delete` if needed |
| `error` | `{ message: string, code: string }` | An error occurred. Common codes: `PERMISSION_DENIED` (KS lacks required privileges), `NO_MEDIA_DEVICES` (camera/microphone not found), `BROWSER_NOT_SUPPORTED` (WebRTC unavailable) |


# 6. Methods

Call methods on the `component.instance` object returned by `Kaltura.ExpressRecorder.create()`:

```javascript
// Programmatic recording flow
component.instance.startRecording();

// Later, stop and upload
component.instance.stopRecording();
component.instance.upload();
```

| Method | Returns | Description |
|--------|---------|-------------|
| `startRecording()` | void | Programmatically start recording. Requests camera/microphone permissions if not already granted. Fires `recordingStarted` on success |
| `stopRecording()` | void | Stop the current recording. Fires `recordingEnded`. The recorded blob is held in memory until `upload()` or `saveCopy()` is called |
| `upload()` | void | Upload the recorded media to Kaltura. Creates a new entry and fires `mediaUploadStarted` with the `entryId`. Progress updates arrive via `mediaUploadProgress`, and `mediaUploadEnded` fires on completion |
| `cancelUpload()` | void | Cancel an in-progress upload. Fires `mediaUploadCancelled`. The partially uploaded entry may need cleanup via `media.delete` |
| `saveCopy()` | void | Save a local copy of the recording to the user's downloads folder. Does not upload to Kaltura |
| `destroy()` | void | Remove the recorder widget from the DOM and release all media streams (camera, microphone, screen). Call this when navigating away or removing the recorder from the page |


# 7. Error Handling

Listen for `error` events on the component instance. The event payload includes `message` and `code` fields:

```javascript
component.instance.addEventListener('error', function(e) {
  console.error('Recorder error:', e.detail.code, e.detail.message);
});
```

**Common error scenarios:**

- **Camera/microphone permissions denied** — The user denied the browser permission prompt. The recorder cannot function without media device access. Prompt the user to grant permissions in their browser settings.  
- **No media devices found** — The device has no camera or microphone. Common on desktops without a webcam. If `allowAudio` is `true` and `allowVideo` is `false`, a microphone is still required.  
- **Browser not supported** — WebRTC is unavailable. Safari has limited WebRTC support for recording. Chrome, Firefox, and Opera are recommended.  
- **KS expiry during recording** — The recorder does not automatically renew expired sessions. If a recording session exceeds the KS TTL, uploads will fail. Generate a KS with sufficient expiry for the expected session duration (recording time + upload time). A 2-hour KS covers most use cases.  
- **Upload network failure** — Intermittent network issues during upload. The recorder does not auto-retry. Listen for the `error` event and offer the user the option to retry with `upload()` or save locally with `saveCopy()`.


# 8. Best Practices

- **Scope the KS.** The KS must include `editadmintags:*` to allow entry creation. Use the minimum additional privileges required.  
- **Verify entry readiness after upload.** After the recorder uploads, the entry goes through transcoding. Poll `media.get` for `status=2` (READY) before redirecting users to playback or caption editing.  
- **Use HTTPS.** The embed URL and all component URLs must use HTTPS for WebRTC and iframe security policies.  
- **Handle session expiry.** Generate a KS with sufficient expiry for the expected recording + upload duration. A 1-hour KS covers most use cases.


# 9. Related Guides

- **[Experience Components Overview](KALTURA_EXPERIENCE_COMPONENTS_API.md)** — Index of all embeddable components with shared guidelines  
- **[Session Guide](KALTURA_SESSION_GUIDE.md)** — KS generation and privilege management  
- **[Upload & Ingestion](KALTURA_UPLOAD_AND_INGESTION_API.md)** — Content lifecycle after the recorder creates entries  
- **[Player Embed Guide](KALTURA_PLAYER_EMBED_GUIDE.md)** — Embed playback for recorded content

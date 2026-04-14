# Kaltura Conversational Avatar Embed

The Conversational Avatar embed provides AI-powered video avatars that hold real-time conversations with users. The avatar speaks, listens, and responds using AI — enabling training simulations, coaching, interview practice, and conversational agents. The embed creates a sandboxed iframe and communicates via `postMessage`.

**Base URL:** `https://api.avatar.us.kaltura.ai`  
**Auth:** Client ID + Flow ID  
**Format:** JavaScript embed (iframe via SDK)  

Kaltura also offers a full Avatar SDK (`@unisphere/models-sdk-js`) for direct WebRTC rendering, text-to-speech control (`sayText`, `sayAudio`, `interrupt`), session management, and backend API integration. The full SDK renders a `<video>` element directly in your DOM via WebRTC (no iframe) and supports both frontend-only and backend-controlled architectures. This guide covers the iframe-based conversational widget embed.


# 1. When to Use

- **HR interview simulation** — Candidates practice with an AI interviewer that evaluates responses  
- **Sales and product training** — Employees practice scenarios with an AI coach that adapts to their answers  
- **Customer-facing conversational agents** — Embed an AI avatar that answers questions about your products or services  
- **Language learning** — Practice pronunciation and conversation with real-time feedback  


# 2. Embedding

Load the Avatar SDK and initialize with your client and flow IDs:

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

The SDK creates a sandboxed iframe inside the container element. All communication between the host page and the avatar happens via `postMessage`.


# 3. Configuration

| Parameter | Required | Description |
|-----------|----------|-------------|
| `clientId` | yes | Kaltura avatar client identifier |
| `flowId` | yes | Identifies which avatar/flow to load |
| `container` | no | CSS selector string or HTMLElement for the iframe |
| `config.debug` | no | Enable console logging |
| `config.apiBaseUrl` | no | Override API URL (default: `https://api.avatar.us.kaltura.ai`) |
| `config.meetBaseUrl` | no | Override meeting URL (default: `https://meet.avatar.us.kaltura.ai`) |


# 4. Lifecycle and Events

The avatar progresses through states: `uninitialized` → `initializing` → `ready` → `in-conversation` → `ended`.

| Event | Data | Description |
|-------|------|-------------|
| `showing-agent` | — | Avatar is visible and ready (inject Dynamic Page Prompt here) |
| `agent-talked` | `{ agentContent }` | Avatar spoke — contains the text |
| `user-transcription` | `{ userTranscription }` | User's speech was transcribed |
| `conversation-ended` | — | Conversation finished |
| `error` | — | An error occurred |


# 5. Methods

| Method | Returns | Description |
|--------|---------|-------------|
| `start(options?)` | `Promise<iframe>` | Load assets and create the avatar iframe |
| `end()` | void | End the conversation and remove iframe |
| `destroy()` | void | Full cleanup (listeners, assets, iframe) |
| `injectPrompt(text)` | boolean | Send a Dynamic Page Prompt to configure the avatar's behavior |
| `getTranscript()` | Array | Full conversation transcript `[{role, text, timestamp}]` |
| `getTranscriptText(options?)` | string | Formatted transcript (text/markdown/json) |

The **Dynamic Page Prompt (DPP)** is the mechanism for customizing avatar behavior at runtime. Inject it on the `showing-agent` event to configure the avatar's persona, scenario, evaluation criteria, and guardrails.


# 6. Error Handling

- **`error` event** — The SDK emits `error` when the avatar fails to initialize or the conversation breaks. Check network connectivity to the avatar API endpoint.  
- **Container not rendered** — If the avatar iframe does not appear, verify the `container` selector matches an existing DOM element with explicit width and height.  
- **Microphone permissions** — The avatar requires microphone access for voice conversation. If the user denies permissions, the conversation cannot proceed. Handle this gracefully in your UI.  


# 7. Best Practices

- **Inject Dynamic Page Prompts on the correct event.** Always inject the DPP on the `showing-agent` event, not on an arbitrary timeout after `start()`. The avatar must be fully loaded before receiving prompts.  
- **Use HTTPS.** The embed requires a secure context for microphone access and iframe security policies.  
- **Size the container explicitly.** The avatar iframe fills the container element — set explicit `width` and `height` to control the layout.  
- **Clean up on navigation.** Call `destroy()` when the user navigates away from the page to release microphone access and remove the iframe.  


# 8. Related Guides

- **[VOD Avatar Studio](KALTURA_VOD_AVATAR_API.md)** — Pre-recorded avatar video generation from scripts — the pre-recorded counterpart to this real-time conversational embed  
- **[Experience Components Overview](KALTURA_EXPERIENCE_COMPONENTS_API.md)** — Index of all embeddable components with shared guidelines  
- **[Unisphere Framework](KALTURA_UNISPHERE_FRAMEWORK_API.md)** — The micro-frontend framework that hosts avatar runtimes via `unisphere.widget.vod-avatars`  
- **[AI Genie API](KALTURA_AI_GENIE_API.md)** — Conversational AI search (text-based, no avatar)  
- **[Events Platform](KALTURA_EVENTS_PLATFORM_API.md)** — Virtual events where avatars can serve as AI moderators or assistants

# Kaltura Genie Widget API

Kaltura Genie provides a conversational AI search widget that lets users ask natural-language questions about your video library and receive structured answers with video clip citations. The widget is embedded via the Kaltura Unisphere loader as an ES module.

**Base URL:** `https://unisphere.nvp1.ovp.kaltura.com/v1`  
**Auth:** KS passed via runtime settings  
**Format:** ES module JavaScript embed  


# 1. When to Use

- **Knowledge portals** — Add AI-powered video search to internal portals, help centers, or learning hubs  
- **Content discovery** — Let users find relevant moments across large video libraries using natural language  
- **Customer support** — Embed a conversational assistant that answers questions from your video knowledge base  
- **Training platforms** — Enable employees or students to search training video content conversationally  


# 2. Prerequisites

- **Kaltura Session (KS)** — A USER KS (type=0) with `setrole:PLAYBACK_BASE_ROLE` and `sview:*` privileges is recommended for the Genie widget. The KS is visible client-side, so generate it on your backend. See the [Session Guide](KALTURA_SESSION_GUIDE.md) for KS generation details.  
- **Genie feature enabled** — The account must have Genie (AI Search) enabled and configured. The account must have indexed content for Genie to search.  
- **Partner-specific Genie URL** — The Genie widget loads via the Unisphere loader from your region's endpoint (e.g., `https://unisphere.nvp1.ovp.kaltura.com/v1` for US). Match the `serverUrl` and `kalturaServerURI` to your Kaltura account region.  


# 3. Embedding

Load the Unisphere loader as an ES module and call `loader()` with your configuration:

```html
<div id="class-genie-container"></div>
<script type="module">
  import { loader } from "https://unisphere.nvp1.ovp.kaltura.com/v1/loader/index.esm.js";

  const options = {
    appId: "my-app",
    appVersion: "1.0.0",
    serverUrl: "https://unisphere.nvp1.ovp.kaltura.com/v1",
    ui: {
      theme: "light",
      language: "en-US"
    },
    runtimes: [{
      widgetName: "unisphere.widget.genie",
      runtimeName: "chat",
      settings: {
        kalturaServerURI: "https://www.kaltura.com",
        ks: "$KALTURA_KS",
        partnerId: "$KALTURA_PARTNER_ID"
      },
      visuals: [{
        type: "page",
        target: "class-genie-container",
        settings: {}
      }]
    }]
  };
  const workspace = await loader(options);

  // Get the runtime instance for programmatic interaction (see section 11)
  const genie = await workspace.getRuntimeAsync("unisphere.widget.genie", "chat");
</script>
```

The container `<div>` must have an `id` attribute matching the `target` value in the visuals config. The widget renders inside this container and fills the available space.


# 4. Configuration

## Top-Level Options

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `appId` | string | yes | Unique identifier for your application instance (e.g., `"my-portal"`) |
| `appVersion` | string | yes | Your application version (e.g., `"1.0.0"`) — useful for tracking and debugging |
| `serverUrl` | string | yes | Unisphere server URL: `https://unisphere.nvp1.ovp.kaltura.com/v1` |
| `ui.theme` | string or object | yes | `"light"`, `"dark"`, or a custom theme object (see section 7) |
| `ui.language` | string | no | UI language code (e.g., `"en-US"`, `"he-IL"`) — see section 10 for supported languages |
| `runtimes` | array | yes | Array of runtime configurations (one entry for Genie) |

## Runtime Settings

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `widgetName` | string | yes | Must be `"unisphere.widget.genie"` |
| `runtimeName` | string | yes | Must be `"chat"` |
| `settings.kalturaServerURI` | string | yes | Kaltura API endpoint (e.g., `https://www.kaltura.com`). Use your region's endpoint if applicable (e.g., `https://api.irp2.ovp.kaltura.com` for EU) |
| `settings.ks` | string | yes | Kaltura Session — must be a USER session (type=0). See section 5 |
| `settings.partnerId` | string | yes | Your Kaltura partner ID. Also accepted as `pid` |
| `settings.uiConfId` | string | no | UI Configuration ID for advanced customization |
| `settings.getSourceUrl` | function | no | Callback receiving `{ entryId, startTime }` — return a URL to the entry in your application. Omit or return empty string if your app has no entry page |
| `settings.shareUrl.queryParam` | string | no | URL query parameter name for conversation sharing (e.g., `"mid"`) |
| `settings.shareUrl.createUrl` | function | no | Callback receiving `{ messageId }` — return a shareable URL for the conversation |

## Visuals

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `visuals[].type` | string | yes | Currently only `"page"` is supported |
| `visuals[].target` | string | yes | The `id` attribute of the container `<div>` where the widget renders |
| `visuals[].settings` | object | yes | Pass an empty object `{}` — reserved for future visual type settings |
| `visuals[].settings.customization.initialPage.title` | string | no | Title displayed on the initial landing page (e.g., `"Ask Anything"`) |
| `visuals[].settings.customization.initialPage.initialQuestions` | array | no | Pre-populated question suggestions — see section 8 |


# 5. KS Requirements

The KS passed to the Genie widget is visible client-side. Generate it as a **USER session** (type=0) on your backend:

```bash
curl -X POST "$KALTURA_SERVICE_URL/service/session/action/start" \
  -d "format=1" \
  -d "secret=$KALTURA_ADMIN_SECRET" \
  -d "partnerId=$KALTURA_PARTNER_ID" \
  -d "type=0" \
  -d "userId=user@example.com" \
  -d "expiry=86400" \
  -d "privileges=setrole:PLAYBACK_BASE_ROLE,sview:*,appid:my-app-my-domain.com,sessionid:$(uuidgen)"
```

**Recommended privileges:**

| Privilege | Purpose |
|-----------|---------|
| `setrole:PLAYBACK_BASE_ROLE` | Restricts the KS to playback-only operations — recommended since the KS is exposed client-side |
| `sview:*` | Allows Genie to return playable clips. Entitlements still gate per-user access |
| `appid:<APP_NAME-APP_DOMAIN>` | Identifies the application in analytics |
| `sessionid:<GUID>` | Unique session identifier for tracking |

**Optional Genie-specific privileges:**

| Privilege | Purpose |
|-----------|---------|
| `genieid:<GENIE_ID>` | Select a specific Genie configuration when your account has multiple. Omit to use the default |
| `geniecategoryid:<CATEGORY_ID>` | Limit Genie queries to content published in the specified category only |
| `genieancestorid:<CATEGORY_ID>` | Limit Genie queries to content in the specified category or any of its descendants |

**Entitlement-protected content:** If Genie indexes content protected by entitlements, add the privacy context to the KS privileges:

```
enableentitlement,privacycontext:<PRIVACY_CONTEXT>
```

If only authenticated users access Genie, specify the `userId` when creating the KS to enable per-user entitlement checks.

See the [Session Guide](KALTURA_SESSION_GUIDE.md) for KS generation details and the [AppTokens Guide](KALTURA_APPTOKENS_API.md) for production token management.


# 6. Container CSS

The container `<div>` must be sized by your page layout — the widget fills the available space.

**Full-page layout:**

```css
#class-genie-container {
  display: flex;
  width: 100%;
  height: 100%;
  min-height: 100vh;
}
```

**Fixed-height panel within an existing page:**

```css
#class-genie-container {
  display: flex;
  width: 100%;
  height: 600px;
}
```


# 7. Custom Theming

Pass a theme object instead of `"light"` or `"dark"` to fully customize the widget appearance:

```javascript
const theme = {
  mode: "dark",
  palette: {
    primary: { light: "#2e89ff", main: "#006cfa", dark: "#0056c7", contrastText: "#ffffff" },
    secondary: { light: "#2e89ff", main: "#006cfa", dark: "#0056c7", contrastText: "#ffffff" },
    danger: { main: "#E95E6C", light: "#F2A1A9", dark: "#DB1E32", contrastText: "#000000" },
    success: { main: "#31B551", light: "#4ACE6B", dark: "#268C3F", contrastText: "#000000" },
    warning: { main: "#F26C0D", light: "#F58A3D", dark: "#C2570A", contrastText: "#000000" },
    info: { main: "#006EFA", light: "#4798FF", dark: "#004CAD", contrastText: "#FFFFFF" },
    surfaces: {
      background: "#06101e",
      paper: "#0b203c",
      elevated: "#102e56",
      protection: "#006cfa"
    },
    tone1: "#ffffff", tone2: "#a9c7ef", tone3: "#5390df",
    tone4: "#205dac", tone5: "#194a8a", tone6: "#11335f",
    tone7: "#0a1e38", tone8: "#000000"
  },
  typography: {
    fontFamily: "Rubik, Helvetica Neue, Segoe UI, sans-serif",
    webFontUrl: "https://fonts.googleapis.com/css2?family=Rubik:wght@400;700&display=swap",
    fontSize: 14,
    fontWeightRegular: 400,
    fontWeightBold: 700
  },
  shape: { roundness1: 8, roundness2: 8, roundness3: 16 },
  elevations: {
    low: "none",
    medium: "0px 0px 0px 1px rgba(0,0,0,0.2), 0px 4px 30px -8px rgba(0,0,0,0.2)",
    high: "0px 0px 0px 1px rgba(0,0,0,0.2), 0px 8px 60px -16px rgba(0,0,0,0.2)"
  },
  breakpoints: { sm: 600, md: 960, lg: 1280, xl: 1600 }
};

const options = {
  // ...other options...
  ui: { theme: theme, language: "en-US" },
  // ...runtimes...
};
```

**Theme properties:**

| Property | Description |
|----------|-------------|
| `mode` | `"light"` or `"dark"` — sets the base color scheme |
| `palette.primary` | Primary brand color with `light`, `main`, `dark`, `contrastText` variants |
| `palette.secondary` | Secondary brand color with the same variant structure |
| `palette.surfaces` | `background`, `paper`, `elevated`, `protection` — surface colors for UI layers |
| `palette.tone1`–`tone8` | Tonal scale from lightest to darkest for text, borders, and subtle UI elements |
| `palette.danger/success/warning/info` | Semantic colors for status indicators |
| `palette.translucent` | Translucent overlay colors with `main`, `dark`, `light`, `contrastText`, `commonBlack`, `commonWhite` |
| `palette.brand` | Custom brand colors (e.g., `brand.yellow.main`) |
| `typography.fontFamily` | Primary font stack |
| `typography.webFontUrl` | URL to load a web font (Google Fonts or similar) |
| `typography.fontSize` | Base font size in pixels |
| `typography.fontWeightLight/Regular/Medium/Bold` | Font weight values (300, 400, 500, 700) |
| `typography.heading1`–`heading5` | Heading styles with `fontWeight`, `fontSize`, `lineHeight`, `letterSpacing`, `fontFamily`, `topBottomMargins` |
| `typography.body1/body2` | Body text styles; `body1Highlight`/`body2Highlight` for bold variants |
| `typography.buttonLabel1/buttonLabel2` | Button text styles |
| `typography.formLabel/formError` | Form element text styles |
| `shape.roundness1/2/3` | Border radius values for small, medium, and large UI elements |
| `elevations.low/medium/high` | CSS box-shadow values for elevation levels |
| `breakpoints.sm/md/lg/xl` | Responsive breakpoint widths in pixels |


# 8. Initial Questions

Pre-populate the landing page with suggested questions using the `initialQuestions` array in the visuals settings:

```javascript
visuals: [{
  type: "page",
  target: "class-genie-container",
  settings: {
    customization: {
      initialPage: {
        title: "Ask Anything",
        initialQuestions: [
          { text: "How do I set up account alerts?", answerType: "flashcards" },
          { text: "What security features are available?", answerType: "flashcards" },
          { text: "How do I manage my profile settings?", answerType: "flashcards" }
        ]
      }
    }
  }
}]
```

Each question object has:  
- **`text`** — The question displayed to the user as a clickable suggestion  
- **`answerType`** — Response format hint (e.g., `"flashcards"` for structured card-based answers)


# 9. Source URL and Share URL Callbacks

Provide callbacks to integrate Genie with your application's navigation and sharing:

```javascript
settings: {
  // Deep-link to video entries in your application
  getSourceUrl: ({ entryId, startTime }) => {
    return `https://my-portal.example.com/watch?entry=${entryId}&st=${startTime}`;
  },
  // Enable conversation sharing
  shareUrl: {
    queryParam: "mid",
    createUrl: ({ messageId }) => {
      const url = new URL(window.location.href);
      url.searchParams.set("mid", messageId);
      return url.toString();
    }
  }
}
```

- **`getSourceUrl`** — Called when Genie displays source entry links in answers. Return a URL to the entry page in your application at the specified `startTime`. Return an empty string or omit the callback entirely if your application does not have entry pages.  
- **`shareUrl`** — Enables conversation sharing. `queryParam` names the URL parameter, and `createUrl` builds the shareable URL from the `messageId`.


# 10. Supported Languages

| Code | Language |
|------|----------|
| `en-US` | English (US) |
| `de-DE` | German |
| `es-ES` | Spanish |
| `fi-FI` | Finnish |
| `fr-CA` | French (Canada) |
| `fr-FR` | French (France) |
| `he-IL` | Hebrew |
| `it-IT` | Italian |
| `ja-JP` | Japanese |
| `ko-KR` | Korean |
| `nl-NL` | Dutch |
| `pt-BR` | Portuguese (Brazil) |
| `ru-RU` | Russian |
| `zh-CN` | Chinese (Simplified) |
| `zh-TW` | Chinese (Traditional) |

Short codes (e.g., `"en"`, `"he"`) are also accepted.


# 11. Workspace Lifecycle

The `loader()` function returns a workspace object for managing the Genie runtime:

```javascript
const workspace = await loader(options);
```

## Workspace Methods

| Method | Returns | Description |
|--------|---------|-------------|
| `getRuntime(widgetName, runtimeName)` | runtime | Get the Genie runtime synchronously. Returns `null` if not yet loaded |
| `getRuntimeAsync(widgetName, runtimeName)` | Promise&lt;runtime&gt; | Get the Genie runtime asynchronously. Resolves when the runtime finishes loading |
| `session.setData(updater)` | void | Update the workspace session. Use to refresh an expired KS without reloading the page |
| `kill()` | void | Destroy the workspace, release the Genie runtime, and remove rendered DOM elements. Call when navigating away from the page |

## Get Runtime Instance

```javascript
// Synchronous (returns null if not yet loaded)
const genie = workspace.getRuntime("unisphere.widget.genie", "chat");

// Asynchronous (waits for load)
const genie = await workspace.getRuntimeAsync("unisphere.widget.genie", "chat");
```

## KS Refresh

The widget does not automatically renew expired sessions. Refresh the KS without reloading:

```javascript
workspace.session.setData(prev => ({ ...prev, ks: "new-ks-token" }));
```

## Cleanup

Call `workspace.kill()` when the user navigates away from the Genie page to release resources:

```javascript
// On page unload or SPA route change
workspace.kill();
```


# 12. Server-Side API

The Genie widget communicates with the Genie server automatically. For custom integrations that bypass the widget (server-to-server RAG search, streaming conversations, polling sessions), see the [AI Genie API Guide](KALTURA_AI_GENIE_API.md).


# 13. Player Integration

The Genie chat can be embedded as a side panel inside the Kaltura Player v7 using three PlayKit plugins. This enables users to ask AI questions about the video they are watching.

## Plugin Dependencies

Three plugins work together — all three must be included in the player configuration:

| Plugin | Config Key | npm Package | Purpose |
|--------|-----------|-------------|---------|
| `@playkit-js/unisphere-service` | `unisphereService` | `@playkit-js/unisphere-service` | Required bridge — syncs player events with Unisphere services |
| `@playkit-js/unisphere` | `unisphere` | `@playkit-js/unisphere` | Loads Unisphere runtimes inside the player UI (container management) |
| `@playkit-js/unisphere-genie` | `genie` | `@playkit-js/unisphere-genie` | Loads the Genie AI chat as a player side panel |

## Genie Plugin Configuration

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `ks` | string | — | Explicit KS for Genie authentication |
| `fallbackToPlayerKS` | boolean | false | Use the player's provider KS when no explicit `ks` is set |
| `expandOnFirstPlay` | boolean | false | Auto-open the Genie side panel on first play |
| `position` | string | `"RIGHT"` | Side panel position |
| `expandMode` | string | `"ALONGSIDE"` | How the panel expands: `"ALONGSIDE"` (shrinks video) or `"OVER"` (overlays video) |

## Events

Listen for Genie player plugin events via the player's event system:

```javascript
player.addEventListener('GENIE_OPEN_MANUAL', function(e) {
  console.log('Genie panel opened by user');
});
```

| Event | Payload | Description |
|-------|---------|-------------|
| `GENIE_OPEN_AUTO` | — | Genie panel opened automatically (via `expandOnFirstPlay`). Fires once on first play |
| `GENIE_OPEN_MANUAL` | — | Genie panel opened by user clicking the Genie icon in the player controls |
| `GENIE_CLOSE` | — | Genie panel closed by user or programmatically |
| `GENIE_NEW_THREAD` | — | User started a new conversation thread, clearing the previous chat history |

## Player Setup Example

```html
<div id="player-container" style="width: 800px; height: 450px;"></div>
<script src="https://cdnapisec.kaltura.com/p/$KALTURA_PARTNER_ID/embedPlaykitJs/uiconf_id/$KALTURA_PLAYER_ID"></script>
<script>
  var player = KalturaPlayer.setup({
    targetId: "player-container",
    provider: {
      partnerId: $KALTURA_PARTNER_ID,
      uiConfId: $KALTURA_PLAYER_ID,
      ks: "$KALTURA_KS"
    },
    plugins: {
      unisphereService: {},
      unisphere: {},
      genie: {
        fallbackToPlayerKS: true,
        expandOnFirstPlay: false,
        position: "RIGHT",
        expandMode: "ALONGSIDE"
      }
    }
  });

  player.loadMedia({ entryId: "$ENTRY_ID" });
</script>
```

The `fallbackToPlayerKS: true` setting uses the player's provider KS for Genie authentication. If you need a separate KS with different privileges (e.g., `setrole:PLAYBACK_BASE_ROLE,sview:*` for Genie), pass it via the `ks` parameter instead.


# 14. Error Handling

- **Blank container** — If the widget container renders empty, verify the `ks` is valid and the `partnerId` matches your account. Check the browser console for CORS errors or ES module import failures. The container `<div>` must have an `id` attribute matching the `target` value in the visuals config.  
- **ES module import failure** — The Genie widget loads as an ES module (`type="module"`). Verify your page uses HTTPS and the browser supports ES modules. The `import` statement requires a script tag with `type="module"`.  
- **KS expiry** — The widget does not automatically renew expired sessions. Use `workspace.session.setData()` to refresh the KS before it expires (see section 11). Generate a KS with sufficient expiry for the expected session duration.  
- **Genie not configured for account** — If the widget loads but returns no results, verify that Genie (AI Search) is enabled and configured for your Kaltura account. The account must have indexed content for Genie to search.  
- **Entitlement-protected content not appearing** — If Genie returns fewer results than expected, verify the KS includes `enableentitlement,privacycontext:<PRIVACY_CONTEXT>` for entitlement-protected content (see section 5).  


# 15. Best Practices

- **Generate the KS server-side.** The Genie widget KS is visible client-side — generate USER sessions (type=0) with `setrole:PLAYBACK_BASE_ROLE` on your backend. Never embed admin secrets in client-side code.  
- **Scope content with category privileges.** Use `geniecategoryid` or `genieancestorid` KS privileges to limit queries to relevant content rather than exposing the entire library.  
- **Size the container explicitly.** The widget fills the available space in the container `<div>` — set explicit `width` and `height` via CSS.  
- **Use HTTPS.** The embed URL and all component URLs must use HTTPS for ES module imports and secure media access.  
- **Clean up on navigation.** Call `workspace.kill()` when the user navigates away from the Genie page to release all runtimes and remove rendered DOM elements (see section 11).  
- **Refresh KS before expiry.** Call `workspace.session.setData()` to refresh the KS without reloading the workspace. This avoids interrupting an active conversation.  


# 16. Related Guides

- **[Unisphere Framework](KALTURA_UNISPHERE_FRAMEWORK_API.md)** — The micro-frontend framework that powers this widget: loader, workspace lifecycle, services, multi-runtime composition  
- **[Experience Components Overview](KALTURA_EXPERIENCE_COMPONENTS_API.md)** — Index of all embeddable components with shared guidelines  
- **[AI Genie API](KALTURA_AI_GENIE_API.md)** — Server-side Genie HTTP API for custom integrations (RAG search, streaming conversations, polling)  
- **[Session Guide](KALTURA_SESSION_GUIDE.md)** — KS generation and privilege management  
- **[AppTokens API](KALTURA_APPTOKENS_API.md)** — Production token management for secure KS generation

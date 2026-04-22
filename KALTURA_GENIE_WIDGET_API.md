# Kaltura Genie Widget API

Kaltura Genie provides a conversational AI search widget that lets users ask natural-language questions about your video library and receive structured answers with video clip citations. The widget is embedded via the Kaltura Unisphere loader as an ES module.

**Base URL:** `https://unisphere.nvp1.ovp.kaltura.com/v1`  
**Auth:** KS passed via runtime settings  
**Format:** ES module JavaScript embed  

<!-- Sections: 1.When to Use | 2.Prerequisites | 3.Embedding | 4.Configuration | 5.KS Requirements | 6.Container CSS | 7.Custom Theming | 8.Initial Questions | 9.Source URL and Share URL Callbacks | 10.Supported Languages | 11.Workspace Lifecycle | 12.Server-Side API | 13.Player Integration | 14.Error Handling | 15.Best Practices | 16.Related Guides -->


# 1. When to Use

- **Knowledge portals** — Add AI-powered video search to internal portals, help centers, or learning hubs  
- **Content discovery** — Let users find relevant moments across large video libraries using natural language  
- **Customer support** — Embed a conversational assistant that answers questions from your video knowledge base  
- **Training platforms** — Enable employees or students to search training video content conversationally  


# 2. Prerequisites

- **Kaltura Session (KS)** — A USER KS (type=0) with all required privileges (see section 5). The KS is visible client-side, so generate it on your backend. Privileges include `setrole:PLAYBACK_BASE_ROLE`, `sview:*`, `enableentitlement`, `privacycontext`, `genieid`, and several others — all are required for correct operation. See the [Session Guide](KALTURA_SESSION_GUIDE.md) for KS generation details.  
- **Genie feature enabled** — The account must have Genie (AI Search) enabled and configured. The account must have indexed content for Genie to search.  
- **Partner-specific Genie URL** — The Genie widget loads via the Unisphere loader from your region's endpoint (e.g., `https://unisphere.nvp1.ovp.kaltura.com/v1` for US). Match the `serverUrl` and `kalturaServerURI` to your Kaltura account region.  


# 3. Embedding

The Genie widget is embedded in two phases: (1) initialize the Unisphere loader, then (2) load and mount the Genie runtime.

```html
<div id="classgenie"></div>

<!-- Phase 1: Initialize the Unisphere loader -->
<script type="module">
  import { loader } from
    "https://unisphere.nvp1.ovp.kaltura.com/v1/loader/index.esm.js";

  loader({
    serverUrl: "https://unisphere.nvp1.ovp.kaltura.com/v1",
    ui: { theme: "light", language: "en" }
  });
</script>

<!-- Phase 2: Load the Genie runtime and mount it -->
<script>
  function waitForUnisphere() {
    return new Promise(function(resolve) {
      if (window.unisphere && window.unisphere.instancesManager) {
        resolve(window.unisphere.instancesManager.get);
      } else {
        var handler = function() {
          document.removeEventListener("unisphere-ready", handler);
          resolve(window.unisphere.instancesManager.get);
        };
        document.addEventListener("unisphere-ready", handler);
      }
    });
  }

  waitForUnisphere().then(function(get) {
    get("").then(function(workspace) {
      workspace.loadRuntime("unisphere.widget.genie", "application", {
        genieServerUrl: "https://genie.nvp1.ovp.kaltura.com",
        ks: "$KALTURA_KS",
        pid: "$KALTURA_PARTNER_ID",
        uiConfId: "$KALTURA_PLAYER_ID",
        widgetId: "",
        kalturaServerURI: "https://cdnapisec.kaltura.com"
      }).then(function(result) {
        result.runtime.assignArea("classgenie");
      });
    });
  });
</script>
```

**How it works:**

1. The ES module `loader()` call initializes the Unisphere framework with server URL and UI settings. It does not load any runtimes yet.  
2. The `unisphere-ready` DOM event fires once the framework is initialized. The `waitForUnisphere()` helper resolves with the workspace getter function.  
3. `get("")` retrieves the default workspace instance.  
4. `workspace.loadRuntime()` loads the Genie widget with its settings (KS, partner ID, Genie server URL).  
5. `runtime.assignArea()` mounts the widget into the container `<div>` matching the given `id`.

The container `<div>` must have an `id` attribute matching the value passed to `assignArea()`. The widget renders inside this container and fills the available space.


# 4. Configuration

## Loader Options

These are passed to the `loader()` call in Phase 1:

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `serverUrl` | string | yes | Unisphere server URL: `https://unisphere.nvp1.ovp.kaltura.com/v1` |
| `ui.theme` | string or object | yes | `"light"`, `"dark"`, or a custom theme object (see section 7) |
| `ui.language` | string | no | UI language code (e.g., `"en-US"`, `"he-IL"`) — see section 10 for supported languages |

## Runtime Settings (loadRuntime parameters)

The third argument to `workspace.loadRuntime("unisphere.widget.genie", "application", settings)` accepts:

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `genieServerUrl` | string | yes | Genie backend URL: `https://genie.nvp1.ovp.kaltura.com` (use your region's endpoint) |
| `kalturaServerURI` | string | yes | Kaltura CDN API endpoint: `https://cdnapisec.kaltura.com` (use your region's endpoint if applicable) |
| `ks` | string | yes | Kaltura Session — must be a USER session (type=0) with all required privileges. See section 5 |
| `pid` | string | yes | Your Kaltura partner ID. Also accepted as `partnerId` |
| `uiConfId` | string | no | UI Configuration ID for player and widget customization |
| `widgetId` | string | no | Widget instance identifier (pass `""` for default) |
| `getSourceUrl` | function | no | Callback receiving `{ entryId, startTime }` — return a URL to the entry in your application. Omit or return empty string if your app has no entry page |
| `shareUrl.queryParam` | string | no | URL query parameter name for conversation sharing (e.g., `"mid"`) |
| `shareUrl.createUrl` | function | no | Callback receiving `{ messageId }` — return a shareable URL for the conversation |

## Mounting

After `loadRuntime()` resolves, call `runtime.assignArea(targetId)` to mount the widget into a container `<div>`:

```javascript
workspace.loadRuntime("unisphere.widget.genie", "application", settings)
  .then(function(result) {
    result.runtime.assignArea("classgenie");
  });
```

The `targetId` must match the `id` attribute of the container `<div>`.

## Customization via assignArea

Pass an optional settings object to `assignArea()` for visual customization:

| Parameter | Type | Description |
|-----------|------|-------------|
| `customization.initialPage.title` | string | Title displayed on the initial landing page (e.g., `"Ask Anything"`) |
| `customization.initialPage.initialQuestions` | array | Pre-populated question suggestions — see section 8 |


# 5. KS Requirements

The KS passed to the Genie widget is visible client-side. Generate it as a **USER session** (type=0) on your backend with all required privileges:

```bash
curl -X POST "$KALTURA_SERVICE_URL/service/session/action/start" \
  -d "format=1" \
  -d "secret=$KALTURA_ADMIN_SECRET" \
  -d "partnerId=$KALTURA_PARTNER_ID" \
  -d "type=0" \
  -d "userId=user@example.com" \
  -d "expiry=86400" \
  -d "privileges=setrole:PLAYBACK_BASE_ROLE,sview:*,eventsessioncontextid:*,privacycontext:$PRIVACY_CONTEXT,enableentitlement,appid:$APP_ID,virtualeventid:$VIRTUAL_EVENT_ID,restrictexplicitliveview:*,searchcontext:kms_esearch_history_global_context,genieid:$GENIE_ID"
```

**Required privileges:**

| Privilege | Purpose |
|-----------|---------|
| `setrole:PLAYBACK_BASE_ROLE` | Restricts the KS to playback-only operations — the KS is exposed client-side |
| `sview:*` | Allows Genie to return playable clips from search results |
| `enableentitlement` | Activates entitlement checks so Genie respects content permissions |
| `privacycontext:<PRIVACY_CONTEXT>` | Specifies which entitlement context applies to this session. The privacy context determines which content the user can access — Genie queries are filtered through this context. Use the privacy context value configured on your categories (see the [Categories & Entitlements Guide](KALTURA_CATEGORIES_AND_ENTITLEMENTS_API.md) for details on privacy contexts and how they control content visibility) |
| `appid:<APP_NAME>` | Identifies the application in analytics (e.g., `eventplatform-6500332.events.kaltura.com`) |
| `virtualeventid:<EVENT_ID>` | Associates the session with a specific virtual event for event-scoped Genie queries |
| `eventsessioncontextid:*` | Grants access to event session context data used by Genie for event-aware responses |
| `restrictexplicitliveview:*` | Enforces explicit live content view restrictions |
| `searchcontext:<CONTEXT>` | Sets the search context for eSearch queries (e.g., `kms_esearch_history_global_context` for global search history) |
| `genieid:<GENIE_ID>` | Selects the specific Genie workspace configuration for this session |

All privilege values are account-specific and site-specific. Obtain the correct values from your Kaltura account configuration.

**Content scoping privileges (optional):**

| Privilege | Purpose |
|-----------|---------|
| `geniecategoryid:<CATEGORY_ID>` | Limit Genie queries to content published in the specified category only |
| `genieancestorid:<CATEGORY_ID>` | Limit Genie queries to content in the specified category or any of its descendants |
| `sessionid:<GUID>` | Unique session identifier for analytics tracking |

## Privacy Context and Entitlements

The `privacycontext` privilege is critical for Genie to return correct results. Without the correct privacy context, Genie either returns no results (content is filtered out by entitlement checks) or returns content the user should not see (entitlement checks are bypassed).

The privacy context value is defined on your category entitlement settings. Each category with entitlements enabled has a `privacyContext` string that identifies the access boundary. When a KS includes `enableentitlement,privacycontext:<VALUE>`, the Kaltura API filters all content queries — including Genie's vector search — to return only entries the user is entitled to within that context.

For a complete explanation of privacy contexts, category entitlements, and how they interact with content access, see the [Categories & Entitlements Guide](KALTURA_CATEGORIES_AND_ENTITLEMENTS_API.md).

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

Pre-populate the landing page with suggested questions by passing a customization object to `assignArea()`:

```javascript
result.runtime.assignArea("classgenie", {
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
});
```

Each question object has:  
- **`text`** — The question displayed to the user as a clickable suggestion  
- **`answerType`** — Response format hint (e.g., `"flashcards"` for structured card-based answers)


# 9. Source URL and Share URL Callbacks

Provide callbacks in the `loadRuntime` settings to integrate Genie with your application's navigation and sharing:

```javascript
workspace.loadRuntime("unisphere.widget.genie", "application", {
  genieServerUrl: "https://genie.nvp1.ovp.kaltura.com",
  ks: "$KALTURA_KS",
  pid: "$KALTURA_PARTNER_ID",
  kalturaServerURI: "https://cdnapisec.kaltura.com",

  // Deep-link to video entries in your application
  getSourceUrl: function(params) {
    return "https://my-portal.example.com/watch?entry=" + params.entryId + "&st=" + params.startTime;
  },
  // Enable conversation sharing
  shareUrl: {
    queryParam: "mid",
    createUrl: function(params) {
      var url = new URL(window.location.href);
      url.searchParams.set("mid", params.messageId);
      return url.toString();
    }
  }
});
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

The `loader()` call initializes the Unisphere framework. Access the workspace via the `unisphere-ready` event:

```javascript
waitForUnisphere().then(function(get) {
  get("").then(function(workspace) {
    // workspace is ready — load runtimes, refresh KS, or clean up
  });
});
```

## Workspace Methods

| Method | Returns | Description |
|--------|---------|-------------|
| `loadRuntime(widgetName, runtimeName, settings)` | Promise&lt;{ runtime }&gt; | Load a widget runtime with the given settings. Call `runtime.assignArea(targetId)` to mount it |
| `session.setData(updater)` | void | Update the workspace session. Use to refresh an expired KS without reloading the page |
| `kill()` | void | Destroy the workspace, release all runtimes, and remove rendered DOM elements. Call when navigating away from the page |

## KS Refresh

The widget does not automatically renew expired sessions. Refresh the KS without reloading:

```javascript
workspace.session.setData(function(prev) {
  return Object.assign({}, prev, { ks: "new-ks-token" });
});
```

## Cleanup

Call `workspace.kill()` when the user navigates away from the Genie page to release resources:

```javascript
// On page unload or SPA route change
workspace.kill();
```


# 12. Server-Side API

The Genie widget communicates with the Genie server automatically. For custom integrations that bypass the widget (server-to-server RAG search, streaming conversations, thread management, feedback), see the [AI Genie API Guide](KALTURA_AI_GENIE_API.md).


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

The `fallbackToPlayerKS: true` setting uses the player's provider KS for Genie authentication. The player KS must include all required Genie privileges (see section 5). If the player KS has different privileges, pass a dedicated Genie KS via the `ks` parameter instead.


# 14. Error Handling

- **Blank container** — If the widget container renders empty, verify the `ks` is valid and the `partnerId` matches your account. Check the browser console for CORS errors or ES module import failures. The container `<div>` must have an `id` attribute matching the `target` value in the visuals config.  
- **ES module import failure** — The Genie widget loads as an ES module (`type="module"`). Verify your page uses HTTPS and the browser supports ES modules. The `import` statement requires a script tag with `type="module"`.  
- **KS expiry** — The widget does not automatically renew expired sessions. Use `workspace.session.setData()` to refresh the KS before it expires (see section 11). Generate a KS with sufficient expiry for the expected session duration.  
- **Genie not configured for account** — If the widget loads but returns no results, verify that Genie (AI Search) is enabled and configured for your Kaltura account. The account must have indexed content for Genie to search.  
- **Entitlement-protected content not appearing** — If Genie returns no results or fewer results than expected, verify the KS includes all required privileges (see section 5). The most common cause is a missing or incorrect `privacycontext` — this must match the privacy context value configured on your categories. See the [Categories & Entitlements Guide](KALTURA_CATEGORIES_AND_ENTITLEMENTS_API.md) for how to look up the correct privacy context value.  


# 15. Best Practices

- **Generate the KS server-side with all required privileges.** The Genie widget KS is visible client-side — generate USER sessions (type=0) on your backend with the full privilege set documented in section 5. Missing privileges cause silent failures (empty results, broken features).  
- **Use the correct privacy context.** The `privacycontext` privilege must match the value configured on your category entitlements. An incorrect privacy context causes Genie to return no results even when content is indexed. See the [Categories & Entitlements Guide](KALTURA_CATEGORIES_AND_ENTITLEMENTS_API.md).  
- **Scope content with category privileges.** Use `geniecategoryid` or `genieancestorid` KS privileges to further limit queries to relevant content within the entitlement boundary.  
- **Size the container explicitly.** The widget fills the available space in the container `<div>` — set explicit `width` and `height` via CSS.  
- **Use HTTPS.** The embed URL and all component URLs must use HTTPS for ES module imports and secure media access.  
- **Clean up on navigation.** Call `workspace.kill()` when the user navigates away from the Genie page to release all runtimes and remove rendered DOM elements (see section 11).  
- **Refresh KS before expiry.** Call `workspace.session.setData()` to refresh the KS without reloading the workspace. This avoids interrupting an active conversation.  


# 16. Related Guides

- **[Unisphere Framework](KALTURA_UNISPHERE_FRAMEWORK_API.md)** — The micro-frontend framework that powers this widget: loader, workspace lifecycle, services, multi-runtime composition  
- **[Experience Components Overview](KALTURA_EXPERIENCE_COMPONENTS_API.md)** — Index of all embeddable components with shared guidelines  
- **[AI Genie API](KALTURA_AI_GENIE_API.md)** — Server-side Genie HTTP API for custom integrations (RAG search, streaming conversations, threads, feedback)  
- **[Categories & Entitlements API](KALTURA_CATEGORIES_AND_ENTITLEMENTS_API.md)** — Privacy contexts, category entitlements, and content visibility rules that govern Genie search results  
- **[Session Guide](KALTURA_SESSION_GUIDE.md)** — KS generation and privilege management  
- **[AppTokens API](KALTURA_APPTOKENS_API.md)** — Production token management for secure KS generation

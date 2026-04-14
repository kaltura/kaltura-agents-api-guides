# Kaltura Unisphere Framework API

Unisphere is Kaltura's micro-frontend framework for embedding composable experiences.  
Load a workspace, configure runtimes (AI search, media manager, content lab, notifications),  
and use built-in services for theming, inter-runtime communication, and analytics.

**Base URL:** `https://unisphere.nvp1.ovp.kaltura.com/v1` (US region)  
**Auth:** KS passed via workspace session config or per-runtime settings  
**Format:** ES module JavaScript embed  


# 1. Architecture Overview

Unisphere follows a layered pipeline:

```
Loader (ES module) → Workspace → Services (9) → Runtimes → Visuals (DOM)
```

**Loader** — A single ES module imported from the Unisphere CDN. The loader fetches the environment manifest (`/v1/runtime.json`), resolves runtime bundle URLs, and bootstraps a workspace. No npm install or build step required.

**Workspace** — The orchestration container. It manages runtime lifecycle, connects built-in services, holds the reactive session store (KS, partnerId), and provides the host API for interacting with loaded runtimes.

**Services** — Nine built-in services available to all runtimes: pub-sub, storage, theme, user-settings, iframes, analytics, logger, developer, and utils. Services enable loose-coupled communication and shared state between runtimes.

**Runtimes** — Independent micro-applications identified by `widgetName` + `runtimeName`. Each runtime loads from a versioned bundle on the CDN. Status lifecycle: `requested` → `loading` → `loaded` / `error` / `skipped`.

**Visuals** — DOM elements mounted by runtimes. Visual types include `page`, `banner`, `popup`, `table`, and `dialog`. Each visual targets a DOM location: a CSS selector string, an element ID, or `{ target: 'body' }` for body-mounted overlays.

**Settings hierarchy** — Configuration cascades from workspace (global defaults) → runtime (per-runtime overrides) → visual (per-visual settings). Lower levels override higher levels.

The v1 API path (`/v1/`) provides long-term backward compatibility. All runtimes and services within v1 maintain stable interfaces.


# 2. Embedding a Workspace

Import the loader ES module from the Unisphere CDN and call `loader()` with your configuration. No npm install, bundler, or build step is needed — the CDN path works standalone in any HTML page:

```html
<div id="my-container"></div>
<script type="module">
  import { loader } from "https://unisphere.nvp1.ovp.kaltura.com/v1/loader/index.esm.js";

  const workspace = await loader({
    serverUrl: "https://unisphere.nvp1.ovp.kaltura.com/v1",
    appId: "my-app",
    appVersion: "1.0.0",
    session: {
      ks: "$KALTURA_KS",
      partnerId: "$KALTURA_PARTNER_ID"
    },
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
        target: "my-container",
        settings: {}
      }]
    }]
  });
</script>
```

**What happens internally:**

1. The loader fetches `/v1/runtime.json` from the Unisphere server  
2. The manifest declares all available widgets, their runtimes, and current versions  
3. The loader resolves each requested runtime's bundle URL  
4. Services are bootstrapped (pub-sub, theme, storage, etc.)  
5. Runtimes are loaded and mounted into the specified visual targets  

**For npm-based projects**, use `fetchAndLoadUnisphereWorkspace()` from the `@unisphere/runtime-js` package (available on public npm):

```javascript
import { fetchAndLoadUnisphereWorkspace } from "@unisphere/runtime-js";

const workspace = await fetchAndLoadUnisphereWorkspace({
  serverUrl: "https://unisphere.nvp1.ovp.kaltura.com/v1",
  // ...same config as loader()
});
```


# 3. Workspace Configuration

## Top-Level Options

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `serverUrl` | string | yes | Unisphere server URL (e.g., `https://unisphere.nvp1.ovp.kaltura.com/v1`) |
| `appId` | string | yes | Application identifier for tracking |
| `appVersion` | string | yes | Application version for tracking |
| `session.ks` | string | no | Kaltura Session shared across all runtimes |
| `session.partnerId` | string/number | no | Kaltura partner ID |
| `runtimes` | array | yes | Array of runtime configurations |
| `ui.theme` | string or object | no | `"light"`, `"dark"`, or a custom theme object (see section 9) |
| `ui.language` | string | no | Language code (e.g., `"en-US"`, `"he-IL"`) — 15 languages supported |
| `ui.bodyContainer.zIndex` | number | no | z-index for body-mounted visuals (popups, dialogs) |
| `devops.fetchStrategy` | string | no | `"esm"` (default) or `"scripts"` for legacy environments |

## Runtime Configuration

Each entry in the `runtimes` array configures one runtime:

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `widgetName` | string | yes | Experience identifier (e.g., `"unisphere.widget.genie"`) |
| `runtimeName` | string | yes | Runtime within the experience (e.g., `"chat"`) |
| `flavor` | string | no | Runtime variant (e.g., `"expo"` for lightweight version) |
| `settings` | object | yes | Runtime-specific configuration (varies by widget) |
| `visuals` | array | no | Visual mount configurations |
| `visuals[].type` | string | yes | Visual type: `"page"`, `"banner"`, `"popup"`, `"table"`, `"dialog"` |
| `visuals[].target` | string or object | yes | DOM target: CSS selector string, `{ target: "element", elementId: "id" }`, or `{ target: "body" }` |
| `visuals[].settings` | object | yes | Visual-specific settings (pass `{}` for defaults) |

## Multiple Runtimes

Load multiple runtimes in a single workspace by adding entries to the `runtimes` array:

```javascript
const workspace = await loader({
  serverUrl: "https://unisphere.nvp1.ovp.kaltura.com/v1",
  appId: "my-portal", appVersion: "1.0.0",
  session: { ks: KS, partnerId: PARTNER_ID },
  runtimes: [
    {
      widgetName: "unisphere.widget.genie",
      runtimeName: "chat",
      settings: { kalturaServerURI: "https://www.kaltura.com", ks: KS, partnerId: PARTNER_ID },
      visuals: [{ type: "page", target: "genie-panel", settings: {} }]
    },
    {
      widgetName: "unisphere.widget.media-manager",
      runtimeName: "kaltura-items-media-manager",
      settings: { contextType: "category" },
      visuals: [{ type: "table", target: "media-library", settings: {} }]
    }
  ]
});
```

All runtimes share the workspace session and services. Use pub-sub or storage services for cross-runtime communication.


# 4. Authentication

The KS (Kaltura Session) is passed via `session.ks` in the workspace configuration. All runtimes in the workspace share this session by default.

**Generate a USER KS (type=0) server-side:**

```bash
curl -X POST "$KALTURA_SERVICE_URL/service/session/action/start" \
  -d "format=1" \
  -d "secret=$KALTURA_ADMIN_SECRET" \
  -d "partnerId=$KALTURA_PARTNER_ID" \
  -d "type=0" \
  -d "userId=user@example.com" \
  -d "expiry=86400" \
  -d "privileges=setrole:PLAYBACK_BASE_ROLE,sview:*,appid:my-app-my-domain.com"
```

**Per-runtime KS override** — When runtimes need different privilege scopes, pass `ks` in the runtime's `settings`:

```javascript
runtimes: [{
  widgetName: "unisphere.widget.genie",
  runtimeName: "chat",
  settings: {
    ks: GENIE_KS,  // Overrides workspace session.ks
    partnerId: PARTNER_ID,
    kalturaServerURI: "https://www.kaltura.com"
  }
}]
```

**Reactive session updates** — Update the KS during long sessions without reloading:

```javascript
workspace.session.setData(prev => ({ ...prev, ks: "new-ks-value" }));
```

The required KS privileges depend on which Kaltura services the loaded runtimes call. For Genie, use `setrole:PLAYBACK_BASE_ROLE,sview:*`. For Media Manager, the KS needs access to `baseEntry`, `category`, and `uploadToken` services.

See the [Session Guide](KALTURA_SESSION_GUIDE.md) for KS generation details and the [AppTokens API](KALTURA_APPTOKENS_API.md) for production token management.


# 5. Available Experiences

The Unisphere manifest (`/v1/runtime.json`) declares all available widgets. All widget bundles are served from the public CDN — no npm install or private access required.

All widgets use the `unisphere.widget.*` naming convention.

## Customer-Facing Widgets

| Widget | Runtime(s) | Purpose | Guide |
|--------|-----------|---------|-------|
| `unisphere.widget.genie` | `chat`, `avatar`, `flashcards-tool`, `followups-tool`, `sources-tool` | AI conversational search + avatar | [Genie Widget](KALTURA_GENIE_WIDGET_API.md) |
| `unisphere.widget.media-manager` | `kaltura-items-media-manager` | Browse, select, upload entries | [Media Manager](KALTURA_MEDIA_MANAGER_API.md) |
| `unisphere.widget.content-lab` | `application`, `ai-consent` | AI content repurposing | [Content Lab](KALTURA_CONTENT_LAB_API.md) |
| `unisphere.widget.agents` | `manager` | Agent management drawer | [Agents Widget](KALTURA_AGENTS_WIDGET_API.md) |
| `unisphere.widget.vod-avatars` | `studio` | Pre-recorded avatar video studio | [VOD Avatar Studio](KALTURA_VOD_AVATAR_API.md) |
| `unisphere.widget.notifications` | `notifications` | Toast, alert, and overlay notifications | — |
| `unisphere.widget.in-app-messaging` | `engine`, `engine-expo`, `engine-modal`, `consent` | In-app messaging system | — |
| `unisphere.widget.reactions` | `showcase` | Live reactions overlay | — |

## Internal / Admin Widgets

These widgets are present in the manifest but serve internal or admin purposes:

| Widget | Runtime(s) | Purpose |
|--------|-----------|---------|
| `unisphere.widget.video-summary` | `ai-generator-demo`, `content-lab-ai-generator`, `kaltura-player-list` | Video summary tools |
| `unisphere.widget.streams-insights` | `quality-of-service` | Stream quality monitoring |
| `unisphere.widget.upgrade-player` | `application` | Player upgrade tool |
| `unisphere.widget.hello` | `hello-world` | Demo/starter widget |
| `unisphere.widget.core` | `dev-tools`, `workspace` | Internal framework services |
| `unisphere.widget.dx` | `dev-tools` | Developer tools |

## Presets

The manifest includes presets that auto-load runtimes:

- **`notifications`** (active by default) — Auto-loads the notifications runtime into body-mounted container  
- **`tools`** / **`ktools`** (inactive) — Developer tools presets  


# 6. Media Manager

The Media Manager widget (`unisphere.widget.media-manager`) provides a reusable runtime for browsing, selecting, and uploading Kaltura entries. It supports inline table and modal dialog visual types, select and manage modes, and programmatic control via `showDialog()` / `hideDialog()`.

See the **[Media Manager Guide](KALTURA_MEDIA_MANAGER_API.md)** for complete documentation including configuration, visual types, modes, runtime API, upload flow, and KS requirements.


# 7. Built-in Services

Services are accessed via `workspace.getService('service-id')`. All nine services are available to every runtime in the workspace.

## 7.1 Pub-Sub (`unisphere.service.pub-sub`)

Loose-coupled event system for cross-runtime communication:

```javascript
const pubSub = workspace.getService("unisphere.service.pub-sub");

// Publish an event
pubSub.emit({ id: "my-event", version: "1.0", payload: { data: "value" } });

// Subscribe to events
const unsubscribe = pubSub.subscribe("my-event", (payload) => {
  console.log("Received:", payload);
});

// Clean up
unsubscribe();
```

## 7.2 Storage (`unisphere.service.storage`)

Shared reactive state between runtimes:

```javascript
const storage = workspace.getService("unisphere.service.storage");

// Write
storage.update("my-namespace", "selectedEntryId", "0_abc123");

// Read
const value = storage.get("my-namespace", "selectedEntryId");

// Subscribe to changes
const unsubscribe = storage.subscribe(
  (value) => console.log("Changed:", value),
  { namespace: "my-namespace", property: "selectedEntryId", emitLastValue: true }
);
```

## 7.3 Theme (`unisphere.service.theme`)

Dynamic theme management:

```javascript
const theme = workspace.getService("unisphere.service.theme");

// Switch theme
theme.setTheme("dark");

// Listen for theme changes
const unsubscribe = theme.onThemeChanged((newTheme) => {
  console.log("Theme changed:", newTheme);
});

// Inject custom CSS for a runtime
const styles = theme.injectStyles(
  "unisphere.widget.genie", "chat",
  [".my-class { color: red; }"]
);
styles.remove(); // Clean up
```

## 7.4 User Settings (`unisphere.service.user-settings`)

Language preferences and legal consent:

```javascript
const settings = workspace.getService("unisphere.service.user-settings");

settings.setLanguage("he-IL");
const lang = settings.getLanguage();
settings.onLanguageChanged((newLang) => console.log("Language:", newLang));

settings.setUserLegalApproved();
const approved = settings.getUserLegalApproved();
```

## 7.5 Analytics (`unisphere.service.kaltura-analytics`)

```javascript
const analytics = workspace.getService("unisphere.service.kaltura-analytics");

analytics.registerUnisphereApp({ analyticsAppId: "my-app", appVersion: "1.0" });
analytics.report("my-app", { eventType: "click", target: "button" });
```

## 7.6 Logger (`unisphere.service.logger`)

```javascript
const loggerService = workspace.getService("unisphere.service.logger");
const logger = loggerService.getOrCreateLogger("app", "my-component");

logger.log("Info message");
logger.debug("Debug message");
logger.warn("Warning message");
logger.error("Error message");
```

## 7.7 Iframes (`unisphere.service.iframes`)

Cross-iframe communication for runtimes running in sandboxed iframes:

```javascript
const iframes = workspace.getService("unisphere.service.iframes");

iframes.notifyAll("event-type", "1.0", "my-source", { data: "value" });
const unsubscribe = iframes.onQuery("query-type", (payload, respond) => {
  respond({ result: "data" });
});
```

## 7.8 Developer (`unisphere.service.developer`)

Development and debugging tools. The Developer Toolbox opens with `Cmd+K` / `Ctrl+K` in staging or local environments:

- Runtime overrides — Load specific runtime versions during development  
- Macros — Automate repetitive development tasks  
- Diagnostic notifications — Debug service interactions  

## 7.9 Utils (`unisphere.service.utils`)

Utility functions for visual management:

- `createOrGetVisual()` — Create or retrieve a visual element  
- `removeVisualFromBody()` — Remove a body-mounted visual  
- `validateSchema()` — Validate configuration against a schema  
- `getRuntimeStyles()` — Get computed styles for a runtime  


# 8. Workspace API

After the loader returns a workspace, use these methods to interact with runtimes and services:

## Workspace Methods

| Method | Returns | Description |
|--------|---------|-------------|
| `getRuntime(widgetName, runtimeName)` | runtime or null | Get a loaded runtime synchronously |
| `getRuntimeAsync(widgetName, runtimeName)` | Promise\<runtime\> | Wait for a runtime to finish loading |
| `onRuntimeLoaded(widgetName, runtimeName, callback)` | unsubscribe fn | Listen for a runtime to load |
| `loadRuntime(widgetName, runtimeName, settings)` | Promise | Dynamically load a new runtime after workspace init |
| `getService(serviceId)` | service or null | Access a built-in service |
| `session` | TinyDataStore | Reactive session store (KS, partnerId) |
| `kill()` | void | Destroy the workspace and all runtimes |
| `getStatus()` | string | `"active"`, `"inactive"`, or `"deactivated"` |

## Runtime Methods

Once you have a runtime reference, control it with:

| Method | Description |
|--------|-------------|
| `updateSettings(settings)` | Push new configuration to a running runtime |
| `mountVisual({ type, target, settings })` | Mount a new visual into the DOM |
| `unmountVisual(id)` | Remove a mounted visual |

## Example: Wait for Runtime and Interact

```javascript
const workspace = await loader(options);

// Wait for the Genie chat runtime to load
const genie = await workspace.getRuntimeAsync(
  "unisphere.widget.genie", "chat"
);

// Update settings on a running runtime
genie.updateSettings({ ks: newKS });

// Mount an additional visual
genie.mountVisual({
  type: "popup",
  target: { target: "body" },
  settings: {}
});

// Clean up when navigating away (SPA)
workspace.kill();
```


# 9. Custom Theming

Pass `"light"` or `"dark"` as a string, or provide a full theme object for complete control:

```javascript
const theme = {
  mode: "dark",
  palette: {
    primary: { light: "#2e89ff", main: "#006cfa", dark: "#0056c7", contrastText: "#ffffff" },
    secondary: { light: "#2e89ff", main: "#006cfa", dark: "#0056c7", contrastText: "#ffffff" },
    surfaces: { background: "#06101e", paper: "#0b203c", elevated: "#102e56" },
    tone1: "#ffffff", tone2: "#a9c7ef", tone3: "#5390df",
    tone4: "#205dac", tone5: "#194a8a", tone6: "#11335f"
  },
  typography: {
    fontFamily: "Rubik, Helvetica Neue, Segoe UI, sans-serif",
    fontSize: 14
  },
  shape: { roundness1: 8, roundness2: 8, roundness3: 16 }
};

const workspace = await loader({
  // ...
  ui: { theme: theme, language: "en-US" },
  // ...
});
```

**Theme properties:**

| Category | Properties |
|----------|-----------|
| `palette.primary/secondary` | `light`, `main`, `dark`, `contrastText` |
| `palette.surfaces` | `background`, `paper`, `elevated`, `protection` |
| `palette.tone1`–`tone8` | Tonal scale from lightest to darkest |
| `palette.danger/success/warning/info` | Semantic status colors |
| `typography` | `fontFamily`, `webFontUrl`, `fontSize`, `fontWeightRegular/Bold` |
| `typography.heading1`–`heading5` | Heading styles (`fontWeight`, `fontSize`, `lineHeight`) |
| `shape` | `roundness1/2/3` — border radius for small/medium/large elements |
| `elevations` | `low/medium/high` — CSS box-shadow values |
| `breakpoints` | `sm/md/lg/xl` — responsive widths in pixels |

See the [Genie Widget Guide](KALTURA_GENIE_WIDGET_API.md) section 6 for a complete theme object example with all properties.


# 10. Player Integration

Three PlayKit plugins bridge Unisphere into the Kaltura Player v7:

| Plugin | Config Key | Purpose |
|--------|-----------|---------|
| `@playkit-js/unisphere-service` | `unisphereService` | Required bridge — syncs player events with Unisphere services |
| `@playkit-js/unisphere` | `unisphere` | Loads Unisphere runtimes inside the player UI |
| `@playkit-js/unisphere-genie` | `genie` | Loads Genie AI chat as a player side panel |

All three plugins are available on public npm (v0.0.x pre-release).

## Events Bridged

The unisphere-service plugin synchronizes: current playback time, pause/play state, side panel open/close, chapters, seek-to-time requests, and player resize.

## Genie Plugin Configuration

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `ks` | string | — | Explicit KS override for Genie |
| `fallbackToPlayerKS` | boolean | false | Use the player's provider KS if no explicit KS |
| `expandOnFirstPlay` | boolean | false | Auto-open the Genie side panel on first play |
| `position` | string | — | Side panel position |
| `expandMode` | string | — | Expansion behavior |

## Player Setup Example

```javascript
const player = KalturaPlayer.setup({
  targetId: "player-container",
  provider: {
    partnerId: PARTNER_ID,
    uiConfId: PLAYER_ID,
    ks: KS
  },
  plugins: {
    unisphereService: {
      serverUrl: "https://unisphere.nvp1.ovp.kaltura.com/v1"
    },
    unisphere: {},
    genie: {
      ks: GENIE_KS,
      fallbackToPlayerKS: true,
      expandOnFirstPlay: false
    }
  }
});

player.loadMedia({ entryId: ENTRY_ID });
```

The `unisphereService` plugin must always be included when using `unisphere` or `genie` plugins.

See the [Player Embed Guide](KALTURA_PLAYER_EMBED_GUIDE.md) for player setup fundamentals.


# 11. Building Custom Experiences

Developers can create custom Unisphere runtimes. All tools are on public npm — no private registry or Kaltura internal access needed.

## Scaffolding

```bash
# Create a new Unisphere project
npm create unisphere-project

# Add a runtime to an existing project
npx nx g @unisphere/nx:add-runtime

# Add a visual to a runtime
npx nx g @unisphere/nx:add-visual

# Add an application entry point
npx nx g @unisphere/nx:add-application
```

**Key npm packages (all public):**

| Package | Version | Purpose |
|---------|---------|---------|
| `create-unisphere-project` | 2.8.0 | Project scaffolding |
| `@unisphere/runtime-js` | 1.92.0 | Core runtime SDK and base classes |
| `@unisphere/nx` | 3.24.0 | NX workspace generators |

## Runtime Development

- **Widget name format:** `{company}.widget.{experience-name}`  
- **Runtime base class:** Extend `UnisphereRuntimeBase` from `@unisphere/runtime-js`  
- **Factory pattern:** Implement `UnisphereElementFactory.create()` for visual element creation  
- **Lifecycle hooks:** `_onVisualMount()`, `_onVisualUnmount()`, `_onKilled()`, `_onSettingsUpdated()`  
- **Service access:** `this._services.pubSub`, `this._services.storage`, `this._services.theme`  
- **Local development:** `npx unisphere runtime serve {name}` (serves on port 8300)  


# 12. Multi-Region

Unisphere is deployed across three regions. Use the region that matches your Kaltura account deployment:

| Region | Loader URL | Use For |
|--------|-----------|---------|
| NVP1 (US) | `https://unisphere.nvp1.ovp.kaltura.com/v1` | Default / US accounts |
| IRP2 (EU) | `https://unisphere.irp2.ovp.kaltura.com/v1` | European accounts |
| FRP2 (DE) | `https://unisphere.frp2.ovp.kaltura.com/v1` | German accounts |

Each region serves its own loader, runtime.json manifest, and widget bundles. Pass the appropriate region URL as the `serverUrl` in your workspace configuration.


# 13. Error Handling

- **Loader import failure** — The `import` statement requires HTTPS and a browser that supports ES modules. Verify your page uses `type="module"` on the script tag.  
- **Workspace bootstrap failure** — Check that `serverUrl` points to a valid Unisphere endpoint and `appId` is set. The loader will fail if it cannot fetch `/v1/runtime.json`.  
- **Runtime load error** — An invalid `widgetName` or `runtimeName` not present in the manifest causes the runtime status to become `error`. Verify widget names against the manifest.  
- **KS missing or expired** — Runtimes that call Kaltura APIs will fail silently or show empty states. Update the session reactively: `workspace.session.setData(prev => ({ ...prev, ks: "new-ks" }))`.  
- **Service access before runtime ready** — Use `getRuntimeAsync()` with `await` instead of `getRuntime()` to wait for the runtime to finish loading.  
- **Container not found** — The visual `target` must match an existing DOM element. If the element is not found, the visual will not mount.  


# 14. Best Practices

- **Generate KS server-side.** Workspace configuration is visible client-side — generate USER sessions (type=0) with scoped privileges on your backend. Use `setrole:PLAYBACK_BASE_ROLE` for read-only widgets.  
- **Use workspace session for shared KS.** Only use per-runtime `settings.ks` when runtimes genuinely need different privilege scopes.  
- **Size visual containers explicitly.** Runtimes fill their container — set explicit `width` and `height` via CSS.  
- **Match region to your account.** Use the Unisphere regional URL that corresponds to your Kaltura account deployment (NVP1, IRP2, or FRP2).  
- **Clean up workspaces.** Call `workspace.kill()` when navigating away in single-page applications to prevent memory leaks.  
- **Use pub-sub for loose coupling.** Runtimes should communicate via the pub-sub service, not direct references.  
- **Use storage for shared reactive state.** The storage service provides namespace-scoped, observable key-value storage.  
- **Use `"esm"` fetch strategy.** The default ESM strategy is recommended. The `"scripts"` strategy exists for legacy environments without ES module support.  
- **Use HTTPS.** All Unisphere CDN URLs and API endpoints require HTTPS.  


# 15. Related Guides

- **[Media Manager API](KALTURA_MEDIA_MANAGER_API.md)** — Browsable media library widget: select, upload, manage entries  
- **[Content Lab API](KALTURA_CONTENT_LAB_API.md)** — AI content repurposing widget: summaries, chapters, clips, quizzes  
- **[Agents Widget API](KALTURA_AGENTS_WIDGET_API.md)** — Agent management drawer: create and configure automated content-processing agents  
- **[VOD Avatar Studio API](KALTURA_VOD_AVATAR_API.md)** — Pre-recorded avatar video generation from scripts  
- **[Genie Widget API](KALTURA_GENIE_WIDGET_API.md)** — Conversational AI search widget with player integration  
- **[AI Genie API](KALTURA_AI_GENIE_API.md)** — Server-side Genie HTTP API for custom RAG integrations  
- **[Conversational Avatar](KALTURA_CONVERSATIONAL_AVATAR_API.md)** — AI-powered conversational video avatar embed  
- **[Experience Components](KALTURA_EXPERIENCE_COMPONENTS_API.md)** — Index of all embeddable components with shared guidelines  
- **[Player Embed Guide](KALTURA_PLAYER_EMBED_GUIDE.md)** — Player v7 embed with Unisphere plugin support  
- **[Session Guide](KALTURA_SESSION_GUIDE.md)** — KS generation and privilege management  
- **[AppTokens API](KALTURA_APPTOKENS_API.md)** — Production token management for secure KS generation

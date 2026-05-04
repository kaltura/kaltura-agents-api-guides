# Kaltura Media Manager API

The Media Manager is a Unisphere widget for browsing, selecting, and uploading Kaltura media entries. Embed an inline media library or open a modal entry picker — both support content browsing, selection callbacks, uploads, and entry management within a category scope.

**Base URL:** `https://unisphere.nvp1.ovp.kaltura.com/v1` (US region)  
**Auth:** KS passed via workspace session or per-runtime settings  
**Format:** ES module JavaScript embed (Unisphere runtime)  

<!-- Sections: 1.When to Use | 2.Prerequisites | 3.Embedding | 4.Configuration | 5.Visual Types | 6.Modes | 7.Runtime API | 8.Switching Categories at Runtime | 9.Upload Flow | 10.KS Requirements | 11.Container CSS | 12.Error Handling | 13.Best Practices | 14.Related Guides -->


# 1. When to Use

- **Content picker** — Let users browse and select entries from a Kaltura category to embed, reference, or attach to workflows  
- **Upload portal** — Provide a self-service upload interface scoped to a specific category  
- **Media library panel** — Embed an inline browsable media grid in your application  
- **Entry management** — Allow users to detach or delete entries from categories  

# 2. Prerequisites

- A valid Kaltura Session (KS) — ADMIN KS (type=2) for manage mode with uploads, or USER KS (type=0) for read-only select mode (see [Session Guide](KALTURA_SESSION_GUIDE.md))  
- The Unisphere Media Manager widget URL for your region (default: `https://unisphere.nvp1.ovp.kaltura.com/v1`)  
- A target container element in your page with an explicit `id` attribute for the widget to render into  


# 3. Embedding

The Media Manager loads as a Unisphere runtime from the CDN. Import the loader and configure a workspace with the `unisphere.widget.media-manager` widget:

```html
<div id="media-container" style="width: 100%; height: 600px;"></div>
<script type="module">
  import { loader } from "https://unisphere.nvp1.ovp.kaltura.com/v1/loader/index.esm.js";

  const workspace = await loader({
    serverUrl: "https://unisphere.nvp1.ovp.kaltura.com/v1",
    appId: "my-app",
    appVersion: "1.0.0",
    session: { ks: "$KALTURA_KS", partnerId: "$KALTURA_PARTNER_ID" },
    runtimes: [{
      widgetName: "unisphere.widget.media-manager",
      runtimeName: "kaltura-items-media-manager",
      settings: {
        contextType: "category",
        contextId: "$CATEGORY_ID"
      },
      visuals: [{
        type: "table",
        target: "media-container",
        settings: { mode: "select" }
      }]
    }]
  });

  // Get the runtime instance for programmatic interaction
  const mm = workspace.getRuntime(
    "unisphere.widget.media-manager",
    "kaltura-items-media-manager"
  );

  // Listen for entry selection
  mm.onRowSelected.subscribe(entry => {
    console.log("Selected:", entry.id, entry.name);
  });
</script>
```

The container `<div>` must have an `id` attribute matching the `target` value in the visual config (no `#` prefix). The widget renders inside this container and fills the available space.


# 4. Configuration

## Runtime Settings

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `contextType` | string | yes | Always `"category"` — scopes entries to a Kaltura category |
| `contextId` | string/number | no | Category ID to scope the media library to. Omit to show all accessible entries |
| `ks` | string | no | Override the workspace KS for this runtime |
| `partnerId` | number | no | Override the workspace partnerId |
| `supportDocuments` | boolean | no | Enable document entry upload and viewing |

## Visual Settings

Both `table` and `dialog` visual types accept the same settings:

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `mode` | string | no | `"select"` (browse and pick) or `"manage"` (browse, upload, delete/detach) |
| `customizations.manage.itemActions` | array | no | Available actions in manage mode (see below) |

### Item Actions

In `manage` mode, configure which actions appear for each entry. Include `schemaVersion: "1"` when using customizations:

```javascript
visuals: [{
  type: "table",
  target: "media-container",
  settings: {
    schemaVersion: "1",
    mode: "manage",
    customizations: {
      manage: {
        itemActions: [
          { action: "delete", label: "Remove permanently" },
          { action: "detach", label: "Remove from category" }
        ]
      }
    }
  }
}]
```

| Action | Description |
|--------|-------------|
| `delete` | Permanently delete the entry from Kaltura |
| `detach` | Remove the entry from the current category without deleting it |


# 5. Visual Types

## Table (Inline Library)

The `table` visual embeds an inline media grid directly in a container element. Use this when the media library is a persistent part of your page layout.

```javascript
visuals: [{
  type: "table",
  target: "media-container",
  settings: { mode: "select" }
}]
```

## Dialog (Modal Picker)

The `dialog` visual creates a modal overlay that opens and closes programmatically. Use this when users need to pick an entry without leaving their current context.

```javascript
visuals: [{
  type: "dialog",
  target: { target: "body" },
  settings: { mode: "select" }
}]
```

You can also open dialogs programmatically using the runtime API — see section 6.


# 6. Modes

## Select Mode

Users browse entries and click to select. A callback fires with the selected entry object.

```javascript
mm.onRowSelected.subscribe(entry => {
  console.log("Selected entry:", entry.id, entry.name);
  // entry is a KalturaBaseEntry object with id, name, description,
  // mediaType, createdAt, thumbnailUrl, etc.
});
```

## Manage Mode

Users browse entries with additional capabilities: upload new entries, and delete or detach existing entries from the category. Configure available actions via the `customizations.manage.itemActions` visual setting.

```javascript
runtimes: [{
  widgetName: "unisphere.widget.media-manager",
  runtimeName: "kaltura-items-media-manager",
  settings: { contextType: "category", contextId: "$CATEGORY_ID" },
  visuals: [{
    type: "table",
    target: "media-container",
    settings: {
      mode: "manage",
      customizations: {
        manage: {
          itemActions: [
            { action: "detach" }
          ]
        }
      }
    }
  }]
}]
```


# 7. Runtime API

After the workspace loads, get the runtime instance for programmatic control:

```javascript
const mm = workspace.getRuntime(
  "unisphere.widget.media-manager",
  "kaltura-items-media-manager"
);
```

Or wait for it to load asynchronously:

```javascript
const mm = await workspace.getRuntimeAsync(
  "unisphere.widget.media-manager",
  "kaltura-items-media-manager"
);
```

## Methods

| Method | Returns | Description |
|--------|---------|-------------|
| `showDialog(mode, onRowSelected)` | void | Open the modal picker in `"select"` or `"manage"` mode. The `onRowSelected` callback fires when a user selects an entry |
| `hideDialog()` | void | Close the modal picker programmatically |
| `updateSettings(settings)` | void | Update runtime settings at runtime (e.g., change `contextId` to switch categories without reloading) |

## Events

| Event | Data | Description |
|-------|------|-------------|
| `onRowSelected` | `KalturaBaseEntry` | Fires when a user selects an entry. Subscribe via `.subscribe()`. The entry object includes `id`, `name`, `description`, `mediaType`, `createdAt`, `thumbnailUrl`, `duration`, `plays`, and other standard entry fields |

## Entry Object Shape

The `onRowSelected` callback and `showDialog` callback both receive a `KalturaBaseEntry` object:

| Property | Type | Description |
|----------|------|-------------|
| `id` | string | Kaltura entry ID (e.g., `"0_abc123"`) |
| `name` | string | Entry display name |
| `description` | string | Entry description |
| `mediaType` | number | `1` = video, `2` = image, `5` = audio, `11` = document |
| `createdAt` | number | Unix timestamp of creation |
| `updatedAt` | number | Unix timestamp of last update |
| `thumbnailUrl` | string | URL to the entry thumbnail |
| `duration` | number | Duration in seconds (video/audio entries) |
| `plays` | number | Total play count |
| `views` | number | Total view count |
| `status` | number | Entry status: `0` = import, `1` = preconvert, `2` = ready, `3` = deleted, `7` = no content |

## Workspace-Level Methods

The `workspace` object returned by `loader()` provides lifecycle and session management:

| Method | Returns | Description |
|--------|---------|-------------|
| `getRuntime(widgetName, runtimeName)` | runtime | Get the runtime instance synchronously. Returns `null` if not yet loaded |
| `getRuntimeAsync(widgetName, runtimeName)` | Promise&lt;runtime&gt; | Get the runtime instance asynchronously. Resolves when the runtime finishes loading |
| `session.setData(updater)` | void | Update the workspace session. Use to refresh an expired KS without reloading the page |
| `kill()` | void | Destroy the workspace, release all runtimes, and remove rendered DOM elements. Call when navigating away from the page |

**KS refresh example:**

```javascript
// Refresh the KS without reloading the workspace
workspace.session.setData(prev => ({ ...prev, ks: "new-ks-token" }));
```

## Modal Picker Example

Open a modal picker without declaring a dialog visual in the initial config:

```javascript
// Open in select mode — callback fires on entry selection
mm.showDialog("select", entry => {
  console.log("User picked:", entry.id, entry.name);
  mm.hideDialog();
});
```

```javascript
// Open in manage mode — allows upload and entry actions
mm.showDialog("manage", entry => {
  console.log("Entry action:", entry.id);
});
```


# 8. Switching Categories at Runtime

Use `updateSettings` to change the category scope without reloading the workspace:

```javascript
// Switch to a different category
mm.updateSettings({
  contextType: "category",
  contextId: "67890"
});
```

The widget reloads its entry list from the new category.


# 9. Upload Flow

When a user uploads a file through the Media Manager in `manage` mode, the widget internally executes a multiRequest with:

1. `baseEntry.add` — Create the entry placeholder  
2. `uploadToken.add` — Create an upload token  
3. `baseEntry.updateContent` — Attach the uploaded file to the entry  
4. `categoryEntry.add` — Assign the new entry to the category context  

The KS used for the Media Manager must have sufficient privileges for these operations. An admin KS (type=2) or a user KS with content creation privileges is required.

After upload completes, the new entry appears in the media grid. The entry goes through transcoding (status=1) before becoming ready (status=2). The upload UI within the widget shows progress during the file transfer.


# 10. KS Requirements

The Media Manager accesses multiple Kaltura API services. Generate the KS server-side with appropriate privileges:

```bash
curl -X POST "$KALTURA_SERVICE_URL/service/session/action/start" \
  -d "format=1" \
  -d "secret=$KALTURA_ADMIN_SECRET" \
  -d "partnerId=$KALTURA_PARTNER_ID" \
  -d "type=2" \
  -d "userId=admin@example.com" \
  -d "expiry=86400"
```

**Required API access:** `baseEntry` (list, add, update, delete), `uploadToken` (add, upload), `categoryEntry` (add, delete), `category` (list).

For read-only select mode, a USER KS (type=0) with content browsing privileges is sufficient. For manage mode with uploads, an ADMIN KS (type=2) or a USER KS with explicit content creation privileges is required.

See the [Session Guide](KALTURA_SESSION_GUIDE.md) for KS generation details and the [AppTokens API](KALTURA_APPTOKENS_API.md) for production token management.


# 11. Container CSS

The Media Manager fills the available space in its container. Set explicit dimensions:

**Inline library panel:**

```css
#media-container {
  display: flex;
  width: 100%;
  height: 600px;
}
```

**Full-page layout:**

```css
#media-container {
  display: flex;
  width: 100%;
  height: 100%;
  min-height: 100vh;
}
```


# 12. Error Handling

- **Empty container** — If the widget renders empty, verify the KS is valid and the `partnerId` matches your account. Check the browser console for errors. The container `<div>` must have an `id` attribute matching the `target` value (no `#` prefix).  
- **No entries displayed** — Verify the `contextId` category exists and contains entries. If omitted, the widget shows all accessible entries.  
- **Upload fails** — The KS must have privileges for `baseEntry.add`, `uploadToken.add`, `baseEntry.updateContent`, and `categoryEntry.add`. An ADMIN KS (type=2) is recommended for manage mode.  
- **KS expiry** — The widget does not automatically renew expired sessions. Generate a KS with sufficient expiry or update the workspace session reactively: `workspace.session.setData(prev => ({ ...prev, ks: "new-ks" }))`.  


# 13. Best Practices

- **Generate the KS server-side.** The KS is visible in client-side code — generate it on your backend with minimal privileges for the intended mode.  
- **Scope with `contextId`.** Always set a `contextId` to limit the media library to a specific category rather than exposing the entire content library.  
- **Use select mode for pickers.** When users only need to choose an entry (not manage content), use `mode: "select"` to hide upload and delete actions.  
- **Size the container explicitly.** The widget fills the available space — set explicit `width` and `height` via CSS.  
- **Use HTTPS.** The Unisphere loader and all widget bundles require HTTPS.  
- **Clean up on navigation.** Call `workspace.kill()` when the user navigates away to release all runtimes and remove rendered DOM elements.  
- **Refresh KS before expiry.** Call `workspace.session.setData(prev => ({ ...prev, ks: "new-ks" }))` to refresh the KS without reloading the workspace.  

## Multi-Region CDN

| Region | Server URL |
|--------|-----------|
| NVP1 (US, default) | `https://unisphere.nvp1.ovp.kaltura.com/v1` |
| IRP2 (EU) | `https://unisphere.irp2.ovp.kaltura.com/v1` |
| FRP2 (DE) | `https://unisphere.frp2.ovp.kaltura.com/v1` |

Set the `serverUrl` in the workspace configuration to match your Kaltura account region.


# 14. Related Guides

- **[Unisphere Framework](KALTURA_UNISPHERE_FRAMEWORK_API.md)** — The micro-frontend framework that powers this widget: loader, workspace lifecycle, services, multi-runtime composition  
- **[Experience Components Overview](KALTURA_EXPERIENCE_COMPONENTS_API.md)** — Index of all embeddable components with shared guidelines  
- **[Upload & Ingestion](KALTURA_UPLOAD_AND_INGESTION_API.md)** — Content lifecycle and upload mechanics used internally by the Media Manager  
- **[Categories & Entitlements](KALTURA_CATEGORIES_AND_ENTITLEMENTS_API.md)** — Category hierarchy and membership for scoping the media library  
- **[Session Guide](KALTURA_SESSION_GUIDE.md)** — KS generation and privilege management  
- **[AppTokens API](KALTURA_APPTOKENS_API.md)** — Production token management for secure KS generation  

# Kaltura Agents Widget API

The Agents Widget is a Unisphere component that provides a UI for managing automated content-processing agents. It renders as a drawer panel where users can create, configure, enable, and monitor agents that automate tasks like captioning, summarization, translation, and moderation. The widget communicates with the Agents Manager backend service.

**Base URL:** `https://unisphere.nvp1.ovp.kaltura.com/v1` (US region)  
**Auth:** KS passed via runtime settings  
**Format:** ES module JavaScript embed (Unisphere runtime)  


# 1. When to Use

- **Agent management UI** — Embed a drawer panel where administrators create and manage automated content-processing agents  
- **Workflow automation** — Let users configure triggers (new upload, category assignment, on-demand) and actions (captions, translation, summary) without API calls  
- **Category-scoped automation** — Scope the agent management UI to a specific category so users only see agents relevant to their content  
- **Integrated admin panels** — Add agent management alongside other Kaltura widgets (Media Manager, Content Lab) in a unified application  


# 2. Architecture

The Agents Widget has one runtime:

| Runtime | Widget Name | Purpose |
|---------|------------|---------|
| `manager` | `unisphere.widget.agents` | Agent management drawer — create, configure, enable/disable, and monitor agents |

The widget communicates with the Agents Manager backend service (`agentsServiceURI`) for all CRUD operations. The Agents Manager API handles agent creation, trigger configuration, action definitions, and execution tracking. See the [Agents Manager API](KALTURA_AGENTS_MANAGER_API.md) for the full server-side API reference.

**Agent concepts:**
- **Triggers** — Events that start an agent: `ENTRY_READY` (new upload processed), `ENTRY_UPDATED` (content changed), `ENTRY_ADDED_TO_CATEGORY` (category assignment), `RUN_ON_DEMAND` (manual execution)  
- **Actions** — Tasks the agent performs: captions, translation, dubbing, summary, metadata enrichment, moderation, publish entry  
- **Action definitions** — The catalog of available action types for your account, retrieved dynamically from the Agents Manager API  


# 3. Embedding

Load the Unisphere loader and configure the agents manager runtime:

```html
<div id="agents-container" style="width: 100%; height: 100vh;"></div>
<script type="module">
  import { loader } from "https://unisphere.nvp1.ovp.kaltura.com/v1/loader/index.esm.js";

  const workspace = await loader({
    serverUrl: "https://unisphere.nvp1.ovp.kaltura.com/v1",
    appId: "my-app",
    appVersion: "1.0.0",
    session: { ks: "$KALTURA_KS", partnerId: "$KALTURA_PARTNER_ID" },
    runtimes: [{
      widgetName: "unisphere.widget.agents",
      runtimeName: "manager",
      settings: {
        ks: "$KALTURA_KS",
        pid: "$KALTURA_PARTNER_ID",
        agentsServiceURI: "https://agents-manager.nvp1.ovp.kaltura.com",
        kalturaServerURI: "https://www.kaltura.com",
        analyticsServerURI: "analytics.kaltura.com",
        hostAppName: 1
      },
      visuals: [{
        type: "drawer",
        target: "agents-container",
        settings: {}
      }]
    }]
  });

  // Get the runtime instance
  const agents = await workspace.getRuntimeAsync(
    "unisphere.widget.agents",
    "manager"
  );

  // Open the agents drawer
  agents.openDrawer();
</script>
```


# 4. Runtime Settings

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `ks` | string | yes | Kaltura Session token (admin KS recommended) |
| `pid` | string | yes | Partner ID |
| `agentsServiceURI` | string | yes | Agents Manager backend URL (e.g., `https://agents-manager.nvp1.ovp.kaltura.com`) |
| `kalturaServerURI` | string | yes | Kaltura API server URL (e.g., `https://www.kaltura.com`) |
| `analyticsServerURI` | string | yes | Analytics endpoint hostname (e.g., `analytics.kaltura.com`) |
| `hostAppName` | number | yes | Numeric host application identifier |
| `categoryId` | string | no | Scope the agent management UI to a specific category ID |

When `categoryId` is set, the widget only shows agents configured for that category and new agents default to that category scope.


# 5. Runtime API

After the workspace loads, get the runtime instance:

```javascript
const agents = await workspace.getRuntimeAsync(
  "unisphere.widget.agents",
  "manager"
);
```

## Methods

| Method | Parameters | Description |
|--------|-----------|-------------|
| `openDrawer()` | none | Open the agents management drawer panel |
| `closeDrawer()` | none | Close the agents management drawer panel |

### Open and Close the Drawer

```javascript
// Open the agents management drawer
agents.openDrawer();

// Close the drawer when done
agents.closeDrawer();
```

The drawer opens as a side panel overlaying or alongside the container element. Users can create new agents, edit existing ones, toggle agents on/off, and view execution history within the drawer.

## Events

The Agents Widget does not emit events to the host page. There are no callbacks for agent creation, configuration changes, or agent enable/disable actions. All agent management operations happen within the widget UI and are persisted directly to the Agents Manager backend.

To detect changes made through the widget programmatically, query the Agents Manager API from your server:

```bash
# List agents for the partner to detect changes
curl -X GET "https://agents-manager.nvp1.ovp.kaltura.com/api/agents?partnerId=$KALTURA_PARTNER_ID" \
  -H "Authorization: Bearer $KALTURA_KS" \
  -H "Content-Type: application/json"
```

See the [Agents Manager API](KALTURA_AGENTS_MANAGER_API.md) for the full server-side API reference including agent CRUD, trigger configuration, and execution history.

## Workspace Lifecycle

The host page can manage the workspace session and lifecycle:

```javascript
// Refresh the KS when it approaches expiry
workspace.session.setData(prev => ({ ...prev, ks: "new-ks-value" }));

// Destroy the workspace when the user navigates away
workspace.kill();
```


# 6. KS Requirements

The Agents Widget accesses the Agents Manager API and Kaltura entry services. Generate the KS server-side with admin privileges:

```bash
curl -X POST "$KALTURA_SERVICE_URL/service/session/action/start" \
  -d "format=1" \
  -d "secret=$KALTURA_ADMIN_SECRET" \
  -d "partnerId=$KALTURA_PARTNER_ID" \
  -d "type=2" \
  -d "userId=admin@example.com" \
  -d "expiry=86400"
```

**Required access:** The KS must have admin privileges (type=2) to create and manage agents. The Agents Manager backend validates permissions for agent CRUD operations.

The account must have the Agents Manager capability enabled. Available actions depend on which services (REACH for captions/translation/summary, etc.) are provisioned on your account.


# 7. Error Handling

- **Blank drawer** — If the drawer renders empty, verify the KS is valid, the `pid` matches your account, and the account has the Agents Manager capability enabled. Check the browser console for API errors.  
- **No action types available** — The available actions depend on which services are enabled on your account. Contact your Kaltura account manager to enable REACH services for captions, translation, summary, and other AI-powered actions.  
- **Agent creation fails** — Verify the KS has admin privileges (type=2). User-level sessions cannot create or modify agents.  
- **KS expiry** — Update the workspace session reactively: `workspace.session.setData(prev => ({ ...prev, ks: "new-ks" }))`.  


# 8. Best Practices

- **Generate the KS server-side.** The KS is visible in client-side code — generate it on your backend with admin privileges.  
- **Scope with `categoryId`.** When embedding the widget in a category-specific context, set `categoryId` to limit the agent management UI to that category.  
- **Use the Agents Manager API for automation.** The widget provides a UI for manual agent management. For programmatic agent creation and management, use the [Agents Manager API](KALTURA_AGENTS_MANAGER_API.md) directly.  
- **Match the `agentsServiceURI` to your region.** Use the correct Agents Manager endpoint for your Kaltura account region (see Multi-Region section below).  
- **Use HTTPS.** The Unisphere loader and all widget bundles require HTTPS.  


# 9. Multi-Region

| Region | Unisphere URL | Agents Manager URL |
|--------|--------------|-------------------|
| NVP1 (US, default) | `https://unisphere.nvp1.ovp.kaltura.com/v1` | `https://agents-manager.nvp1.ovp.kaltura.com` |
| IRP2 (EU) | `https://unisphere.irp2.ovp.kaltura.com/v1` | `https://agents-manager.irp2.ovp.kaltura.com` |
| FRP2 (DE) | `https://unisphere.frp2.ovp.kaltura.com/v1` | `https://agents-manager.frp2.ovp.kaltura.com` |

Set both `serverUrl` and `agentsServiceURI` to match your Kaltura account region.


# 10. Related Guides

- **[Agents Manager API](KALTURA_AGENTS_MANAGER_API.md)** — Server-side REST API for creating, managing, and executing agents programmatically  
- **[Unisphere Framework](KALTURA_UNISPHERE_FRAMEWORK_API.md)** — The micro-frontend framework that powers this widget: loader, workspace lifecycle, services  
- **[Experience Components Overview](KALTURA_EXPERIENCE_COMPONENTS_API.md)** — Index of all embeddable components with shared guidelines  
- **[REACH API](KALTURA_REACH_API.md)** — AI services (captions, translation, dubbing, summarization) that power agent actions  
- **[Session Guide](KALTURA_SESSION_GUIDE.md)** — KS generation and privilege management  
- **[AppTokens API](KALTURA_APPTOKENS_API.md)** — Production token management for secure KS generation  

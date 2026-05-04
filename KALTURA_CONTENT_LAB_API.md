# Kaltura Content Lab API

Content Lab is a Unisphere widget for AI-powered content repurposing. It generates summaries, chapters, clips, quizzes, and other derived content from video and audio entries. The widget renders as a drawer panel and integrates with Kaltura REACH services for AI processing.

**Base URL:** `https://unisphere.nvp1.ovp.kaltura.com/v1` (US region)  
**Auth:** KS passed via runtime settings  
**Format:** ES module JavaScript embed (Unisphere runtime)  

<!-- Sections: 1.When to Use | 2.Prerequisites | 3.Architecture | 4.Embedding | 5.Application Runtime Settings | 6.AI Consent Runtime Settings | 7.Runtime API | 8.KS Requirements | 9.Error Handling | 10.Best Practices | 11.Related Guides -->


# 1. When to Use

- **Video summarization** — Generate AI summaries with configurable writing style and detail level  
- **Chapter generation** — Auto-create navigable chapters from long-form video content  
- **Clip creation** — Extract highlight clips from full-length recordings  
- **Quiz generation** — Create assessment quizzes from educational or training video content  
- **Content repurposing** — Transform a single video into multiple derivative assets  


# 2. Prerequisites

- **ADMIN KS (type=2)** — Content Lab accesses REACH services, entry data, and the consent API. Generate an ADMIN Kaltura Session on your backend with sufficient privileges. See the [Session Guide](KALTURA_SESSION_GUIDE.md) for KS generation details.  
- **Content Lab feature enabled** — The account must have the `FEATURE_CONTENT_LAB` permission enabled.  
- **REACH plugin provisioned** — Content Lab orchestrates AI processing through Kaltura REACH services. A REACH profile with available catalog items must be configured on your account for summarization, chapter generation, clip creation, and quiz generation features.  


# 3. Architecture

Content Lab has two runtimes:

| Runtime | Widget Name | Purpose |
|---------|------------|---------|
| `application` | `unisphere.widget.content-lab` | Main Content Lab UI — drawer panel with AI processing tools |
| `ai-consent` | `unisphere.widget.content-lab` | AI consent banner — prompts users to approve AI feature usage |

The `ai-consent` runtime manages the approval flow required before AI features can be used. When embedded in a third-party application (not a Kaltura product), set `hostedInKalturaProduct: false` in the application runtime settings.

**Entry eligibility:** Content Lab requires entries that are:
- In READY status (status=2)  
- Video or audio media type  
- At least 60 seconds in duration  
- For live entries: must have a recording (`redirectEntryId` or `recordedEntryId`)  


# 4. Embedding

Load the Unisphere loader and configure both the application and ai-consent runtimes:

```html
<div id="content-lab-container" style="width: 100%; height: 100vh;"></div>
<script type="module">
  import { loader } from "https://unisphere.nvp1.ovp.kaltura.com/v1/loader/index.esm.js";

  const workspace = await loader({
    serverUrl: "https://unisphere.nvp1.ovp.kaltura.com/v1",
    appId: "my-app",
    appVersion: "1.0.0",
    session: { ks: "$KALTURA_KS", partnerId: "$KALTURA_PARTNER_ID" },
    runtimes: [
      {
        widgetName: "unisphere.widget.content-lab",
        runtimeName: "application",
        settings: {
          _schemaVersion: "1",
          ks: "$KALTURA_KS",
          pid: "$KALTURA_PARTNER_ID",
          uiconfId: "$KALTURA_PLAYER_ID",
          kalturaServerURI: "https://www.kaltura.com",
          analyticsServerURI: "analytics.kaltura.com",
          hostAppName: 1,
          hostedInKalturaProduct: false
        },
        visuals: [{
          type: "drawer",
          target: "content-lab-container",
          settings: {}
        }]
      },
      {
        widgetName: "unisphere.widget.content-lab",
        runtimeName: "ai-consent",
        settings: {
          _schemaVersion: "1",
          ks: "$KALTURA_KS",
          pid: "$KALTURA_PARTNER_ID",
          hostApp: "my-app",
          canSetConsent: true,
          kaltura: {
            analyticsServerURI: "analytics.kaltura.com",
            hostAppName: 1,
            hostAppVersion: "1.0.0"
          }
        },
        visuals: [{
          type: "banner",
          target: { target: "body" },
          settings: {}
        }]
      }
    ]
  });

  // Open Content Lab for a specific entry
  const contentLab = await workspace.getRuntimeAsync(
    "unisphere.widget.content-lab",
    "application"
  );
  contentLab.openApplication({
    entryId: "$KALTURA_ENTRY_ID",
    eventSessionContextId: "",
    type: "entry"
  });
</script>
```


# 5. Application Runtime Settings

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `_schemaVersion` | string | yes | Must be `"1"` |
| `ks` | string | yes | Kaltura Session token |
| `pid` | string | yes | Partner ID |
| `uiconfId` | string | yes | Player UI configuration ID for video preview |
| `kalturaServerURI` | string | yes | Kaltura API server URL (e.g., `https://www.kaltura.com`) |
| `analyticsServerURI` | string | yes | Analytics endpoint hostname (e.g., `analytics.kaltura.com`) |
| `hostAppName` | number | yes | Numeric host application identifier |
| `hostedInKalturaProduct` | boolean | no | Set `false` when embedding in third-party apps. Controls AI consent enforcement |
| `hostAppVersion` | string | no | Host application version string |
| `reachProfileId` | string | no | REACH profile ID for enrichment services |
| `loadThumbnailWithKS` | boolean | no | Append KS to thumbnail URLs (for access-controlled thumbnails) |
| `publishCategoryId` | string | no | Default category ID for publishing generated content |
| `hidePlaylists` | boolean | no | Hide playlist creation option |
| `hideTags` | boolean | no | Hide tags field |
| `hideAddCaptionsCTA` | boolean | no | Hide "Add Captions" call-to-action |


# 6. AI Consent Runtime Settings

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `_schemaVersion` | string | yes | Must be `"1"` |
| `ks` | string | yes | Kaltura Session token |
| `pid` | string | yes | Partner ID |
| `hostApp` | string | yes | Host application name string |
| `canSetConsent` | boolean | no | Whether the current user can approve AI consent. `true` shows approval checkbox, `false` shows "contact your admin" message |
| `kaltura.analyticsServerURI` | string | yes | Analytics endpoint hostname (e.g., `analytics.kaltura.com`) |
| `kaltura.hostAppName` | number | yes | Numeric host application identifier (matches application runtime `hostAppName`) |
| `kaltura.hostAppVersion` | string | yes | Host application version string |

## AI Consent Flow

Content Lab requires AI consent approval before processing. The consent API endpoint is:

```
POST https://consent.nvp1.ovp.kaltura.com/api/v1/consent/get-status
Authorization: Bearer $KALTURA_KS
Content-Type: application/json

{ "approved_entity": "AI" }
```

Consent statuses: `approved`, `not provided`, `approved by kaltura`, `rejected by kaltura`.

When the user approves consent via the `ai-consent` banner, the runtime sends:

```
POST https://consent.nvp1.ovp.kaltura.com/api/v1/consent/upsert-action
Authorization: Bearer $KALTURA_KS
Content-Type: application/json

{ "approval_status": "approved", "approving_app": "my-app", "approved_entity": "AI" }
```

The `ai-consent` runtime communicates with the application runtime via Unisphere pub-sub events:
- `unisphere.widget.content-lab.ai-consent-approved` — Consent granted, Content Lab enables AI features  
- `unisphere.widget.content-lab.ai-consent-dismiss` — User dismissed the consent banner  


# 7. Runtime API

## Application Runtime

```javascript
const contentLab = await workspace.getRuntimeAsync(
  "unisphere.widget.content-lab",
  "application"
);
```

| Method | Parameters | Description |
|--------|-----------|-------------|
| `openApplication(options)` | `{ entryId: string, eventSessionContextId: string, type: "entry" }` | Open Content Lab for a specific entry |
| `isEntryRelevant(entry)` | `KalturaMediaEntry` or `string` (entry ID) | Check if an entry is eligible for Content Lab processing |

### Entry Eligibility Check

```javascript
const result = await contentLab.isEntryRelevant("0_abc123");
if (result.canUse) {
  contentLab.openApplication({
    entryId: "0_abc123",
    eventSessionContextId: "",
    type: "entry"
  });
} else {
  console.log("Ineligible:", result.rejectionReason);
}
```

Rejection reasons: `ENTRY_NOT_READY`, `ENTRY_TYPE_NOT_SUPPORTED`, `ENTRY_DURATION_LESS_THAN_MIN`, `NO_REACH_PROFILE`, `NO_CATALOG_ITEMS`, `NO_REACH_PERMISSION`, `NO_CAPTIONS`, `NO_RECORDING`, `AI_CONSENT`, `GENERAL_ERROR`.

## AI Consent Runtime

```javascript
const aiConsent = await workspace.getRuntimeAsync(
  "unisphere.widget.content-lab",
  "ai-consent"
);
```

| Method | Parameters | Description |
|--------|-----------|-------------|
| `showAnnouncement(options?)` | `{ onSuccess?: () => void, entryId?: string }` | Show the AI consent announcement modal |

## Processing Completion

Content Lab does not emit events to the host page when AI processing tasks (summarization, chapter generation, clip creation, quiz generation) complete. All processing is handled server-side through Kaltura REACH services.

To detect when a task initiated through Content Lab has completed, poll the `entryVendorTask` API:

```bash
# List REACH tasks for an entry to check processing status
curl -X POST "$KALTURA_SERVICE_URL/service/reach_entryVendorTask/action/list" \
  -d "ks=$KALTURA_KS" \
  -d "format=1" \
  -d "filter[objectType]=KalturaEntryVendorTaskFilter" \
  -d "filter[entryIdEqual]=$KALTURA_ENTRY_ID" \
  -d "filter[orderBy]=-createdAt"
```

Task status values relevant to Content Lab:

| Status | Value | Meaning |
|--------|-------|---------|
| PENDING | 1 | Task submitted, awaiting processing |
| READY | 2 | Task completed successfully |
| PROCESSING | 3 | AI engine is working on the task |
| PENDING_MODERATION | 4 | Awaiting human review |
| REJECTED | 5 | Task rejected during moderation |
| ERROR | 6 | Task failed |

Poll at 15-30 second intervals. AI summarization and chapter generation typically complete within 1-5 minutes depending on entry duration. See the [REACH API](KALTURA_REACH_API.md) for the full vendor task lifecycle.

Alternatively, configure a [Webhook](KALTURA_EVENT_NOTIFICATIONS_WEBHOOK_AND_EMAIL_API.md) on the `entryVendorTask` event type to receive real-time HTTP callbacks when REACH tasks complete, instead of polling.

## Workspace Lifecycle

```javascript
// Refresh the KS when it approaches expiry
workspace.session.setData(prev => ({ ...prev, ks: "new-ks-value" }));

// Destroy the workspace when the user navigates away
workspace.kill();
```


# 8. KS Requirements

Content Lab accesses REACH services, entry data, and the consent API. Generate the KS server-side with sufficient privileges:

```bash
curl -X POST "$KALTURA_SERVICE_URL/service/session/action/start" \
  -d "format=1" \
  -d "secret=$KALTURA_ADMIN_SECRET" \
  -d "partnerId=$KALTURA_PARTNER_ID" \
  -d "type=2" \
  -d "userId=admin@example.com" \
  -d "expiry=86400"
```

**Required access:** `baseEntry` (get, list), `caption_captionAsset` (list), REACH services (vendorCatalogItem.list, entryVendorTask.add), consent API.

The account must have the `FEATURE_CONTENT_LAB` permission enabled.


# 9. Error Handling

- **Blank drawer** — If Content Lab renders empty, verify the KS is valid and the account has `FEATURE_CONTENT_LAB` enabled. Check the browser console for API errors.  
- **"Entry not eligible" messages** — The entry must be READY (status=2), video or audio type, and at least 60 seconds long. Use `isEntryRelevant()` to check eligibility before opening.  
- **AI consent required** — If the account has not approved AI consent, Content Lab features are disabled. Load the `ai-consent` runtime to show the approval banner.  
- **No REACH profile** — Content Lab requires a REACH profile with available catalog items. Contact your Kaltura account manager to enable REACH services.  
- **KS expiry** — Update the workspace session reactively: `workspace.session.setData(prev => ({ ...prev, ks: "new-ks" }))`.  


# 10. Best Practices

- **Check entry eligibility first.** Call `isEntryRelevant()` before opening Content Lab to avoid presenting a non-functional UI.  
- **Load both runtimes.** Always include the `ai-consent` runtime alongside the `application` runtime. Without consent, AI features are blocked.  
- **Set `hostedInKalturaProduct: false`.** When embedding Content Lab in your own application, this flag ensures the consent flow works correctly outside the KMC.  
- **Set `canSetConsent` based on user role.** Only admin users should be able to approve AI consent for the account. Regular users see a "contact your admin" message.  
- **Generate the KS server-side.** The KS is visible in client-side code — generate it on your backend.  
- **Use HTTPS.** The Unisphere loader and all widget bundles require HTTPS.  

## Multi-Region CDN

| Region | Server URL | Consent API |
|--------|-----------|-------------|
| NVP1 (US, default) | `https://unisphere.nvp1.ovp.kaltura.com/v1` | `https://consent.nvp1.ovp.kaltura.com/api/v1` |
| IRP2 (EU) | `https://unisphere.irp2.ovp.kaltura.com/v1` | `https://consent.irp2.ovp.kaltura.com/api/v1` |
| FRP2 (DE) | `https://unisphere.frp2.ovp.kaltura.com/v1` | `https://consent.frp2.ovp.kaltura.com/api/v1` |


# 11. Related Guides

- **[Unisphere Framework](KALTURA_UNISPHERE_FRAMEWORK_API.md)** — The micro-frontend framework that powers this widget: loader, workspace lifecycle, services  
- **[Experience Components Overview](KALTURA_EXPERIENCE_COMPONENTS_API.md)** — Index of all embeddable components with shared guidelines  
- **[REACH API](KALTURA_REACH_API.md)** — Enrichment services marketplace (captions, translation, summarization, and more) that Content Lab orchestrates  
- **[Agents Manager API](KALTURA_AGENTS_MANAGER_API.md)** — Automated content processing agents for batch AI operations  
- **[Moderation API](KALTURA_MODERATION_API.md)** — AI content screening via REACH alongside content repurposing  
- **[Session Guide](KALTURA_SESSION_GUIDE.md)** — KS generation and privilege management  
- **[AppTokens API](KALTURA_APPTOKENS_API.md)** — Production token management for secure KS generation  
- **[Cue Points & Interactive Video](KALTURA_CUE_POINTS_API.md)** — Chapters, quizzes, and annotations generated by Content Lab are stored as cue points
- **[Quiz API](KALTURA_QUIZ_API.md)** — Quiz questions generated by Content Lab
- **[Chapters & Slides API](KALTURA_CHAPTERS_AND_SLIDES_API.md)** — Chapters generated by Content Lab  

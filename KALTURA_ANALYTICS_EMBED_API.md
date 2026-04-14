# Kaltura Embeddable Analytics API

The Embeddable Analytics widget provides analytics visualization dashboards that can be embedded in third-party applications via iframe. The embedded dashboard provides the same analytics views available in the Kaltura Management Console (KMC), including content engagement, top content, viewer metrics, usage trends, and live stream health. The embed is framework-agnostic — the host drives it entirely through `postMessage`.

**Base URL:** `https://kmc.kaltura.com/apps/kmc-analytics/latest/index.html`  
**Auth:** ADMIN KS (type=2) passed via postMessage  
**Format:** iframe embed with postMessage protocol  


# 1. When to Use

- **Custom admin panels** — Embed analytics dashboards in your own admin interface without building custom reporting  
- **Content owner portals** — Show content creators their own analytics within your platform  
- **Event dashboards** — Display real-time event engagement metrics alongside event management tools  
- **White-label analytics** — Embed Kaltura analytics into your branded application with custom styling  


# 2. Embedding

Embed the analytics dashboard in an iframe:

```html
<iframe
  id="analytics"
  title="analytics-iframe"
  src="https://kmc.kaltura.com/apps/kmc-analytics/latest/index.html"
  width="100%"
  height="800"
  style="border: none;"
  allowfullscreen
  allow="autoplay *; fullscreen *; encrypted-media *">
</iframe>
```

The analytics app initializes via a `postMessage` handshake with the host page. Use vanilla JavaScript, React, Angular, Vue, or any framework to drive it.

**Alternative: Friendly Iframe Pattern**  
Instead of a standard cross-origin iframe, you can fetch the analytics HTML with `fetch()` and inject it via `srcdoc` for same-origin access. This gives the host page direct DOM access to the analytics content for tighter integration (e.g., reading layout dimensions without `postMessage`):

```javascript
fetch('https://kmc.kaltura.com/apps/kmc-analytics/latest/index.html')
  .then(r => r.text())
  .then(html => {
    var iframe = document.getElementById('analytics');
    iframe.srcdoc = html;
  });
```

The `postMessage` protocol works identically with both approaches.


# 3. Initialization Protocol

The analytics iframe communicates with the host via `window.postMessage`. The host must listen for messages and respond with configuration:

**Step 1 — Listen for `analyticsInit`:**  
When the iframe loads, it sends an `analyticsInit` message containing a `viewsConfig` object that describes available views and features.

**Step 2 — Respond with `init`:**  
The host sends an `init` message back to the iframe with the full configuration:

```javascript
window.addEventListener('message', function(e) {
  if (!e.data || e.data.messageType !== 'analyticsInit') return;

  var viewsConfig = e.data.payload.viewsConfig;
  var analyticsIframe = document.getElementById('analytics');

  analyticsIframe.contentWindow.postMessage({
    messageType: 'init',
    payload: {
      kalturaServer: {
        uri: '$SERVICE_URL'.replace('/api_v3', ''),
        previewUIConfV7: parseInt('$PLAYER_ID')
      },
      cdnServers: {
        serverUri: 'http://cdnapi.kaltura.com',
        securedServerUri: 'https://cdnapisec.kaltura.com'
      },
      ks: '$KS',
      pid: parseInt('$PARTNER_ID'),
      locale: 'en',
      live: { pollInterval: 30, healthNotificationsCount: 50 },
      menuConfig: { showMenu: false },
      viewsConfig: viewsConfig
    }
  }, '*');
});
```

**Step 3 — Wait for `analyticsInitComplete`:**  
The analytics app confirms initialization by sending `analyticsInitComplete`.

**Step 4 — Navigate to a view:**  
Send `navigate` and `updateFilters` messages to control the displayed view:

```javascript
// Navigate to partner engagement view
analyticsIframe.contentWindow.postMessage({
  messageType: 'navigate',
  payload: { url: '/analytics/engagement' }
}, '*');

// Set date filter
analyticsIframe.contentWindow.postMessage({
  messageType: 'updateFilters',
  payload: { queryParams: { dateBy: 'last30days' } }
}, '*');
```


# 4. Init Payload Reference

The `init` message payload configures the analytics app. All properties below are passed inside the `payload` object:

## Server Configuration

| Property | Type | Required | Description |
|----------|------|----------|-------------|
| `kalturaServer.uri` | string | yes | Kaltura API base URL without `/api_v3` (e.g., `https://www.kaltura.com`) |
| `kalturaServer.previewUIConfV7` | number | no | Player V7 uiConf ID for video previews inside analytics. Auto-detected from partner templates when omitted |
| `kalturaServer.previewUIConf` | number | no | Player V2 uiConf ID (legacy — prefer `previewUIConfV7`) |
| `kalturaServer.exportRoute` | string | no | Custom route for CSV export downloads |
| `cdnServers.serverUri` | string | no | CDN HTTP URL (e.g., `http://cdnapi.kaltura.com`) |
| `cdnServers.securedServerUri` | string | no | CDN HTTPS URL (e.g., `https://cdnapisec.kaltura.com`) |
| `analyticsServer.uri` | string | no | Analytics tracking server URL (e.g., `https://analytics.kaltura.com`) |

## Authentication & Identity

| Property | Type | Required | Description |
|----------|------|----------|-------------|
| `ks` | string | yes | Kaltura Session — must be ADMIN (type=2). See section 10 |
| `pid` | number | yes | Kaltura partner ID |
| `locale` | string | no | UI language code. Default: `en`. Supported: `de`, `en`, `es`, `fr`, `ja`, `nl`, `pt_br`, `ru`, `zh_hans`, `zh_hant` |
| `hostAppName` | number | no | Identifies the hosting application: `0` = KMC, `1` = MediaSpace, `11` = Events Platform |
| `hostAppVersion` | string | no | Version string of the host application (for tracking) |

## Display & Behavior

| Property | Type | Default | Description |
|----------|------|---------|-------------|
| `menuConfig.showMenu` | boolean | true | Show or hide the left navigation menu. Set `false` when embedding a specific view |
| `menuConfig.items` | array | default menu | Custom menu structure — array of `{ id, link, label, children }` |
| `viewsConfig` | object | full defaults | Controls visibility of every dashboard widget. See section 8 |
| `dateFormat` | string | `month-day-year` | Date display format: `month-day-year` or `day-month-year` |
| `contrastTheme` | boolean | false | Enable high-contrast accessibility theme |
| `loadThumbnailWithKs` | boolean | false | Append KS to thumbnail URLs (required for accounts with restricted content access) |
| `multiAccount` | boolean | false | Enable multi-account (sub-account) analytics. Requires `FEATURE_MULTI_ACCOUNT_ANALYTICS` permission on the account |
| `liveEntryUsersReports` | string | `All` | Live entry user report mode: `All` (anonymous + authenticated) or `Authenticated` (authenticated only) |

## Live Analytics

| Property | Type | Default | Description |
|----------|------|---------|-------------|
| `live.pollInterval` | number | 30 | Seconds between live dashboard data refreshes |
| `live.healthNotificationsCount` | number | 50 | Maximum stream health notifications to display |

## Scoped Analytics

| Property | Type | Description |
|----------|------|-------------|
| `predefinedFilter.ownerIdsIn` | string | Restrict reports to entries owned by this user ID. Use for "My Content" analytics |
| `customData.metadataProfileId` | number | Metadata profile ID for displaying custom metadata comments |
| `customData.disableUserDrilldown` | boolean | Prevent user drill-down navigation from entry detail views |
| `customData.eventId` | string | Events Platform: scope analytics to a specific event |
| `customData.eventContentCategoryFullName` | string | Events Platform: category full name for event content |
| `customData.eventSessionEntries` | string | Events Platform: comma-separated session entry IDs |
| `customData.exportEmail` | string | Email address for CSV export delivery |

## External Service Endpoints

| Property | Type | Description |
|----------|------|-------------|
| `externalServices.appRegistryEndpoint.uri` | string | App Registry service URL |
| `externalServices.userReportsEndpoint.uri` | string | User Reports service URL |
| `externalServices.userProfileEndpoint.uri` | string | User Profile service URL |
| `externalServices.chatAnalyticsEndpoint.uri` | string | Chat & Collaborate analytics service URL |

## Custom Styling

| Property | Type | Description |
|----------|------|-------------|
| `customStyle.baseClassName` | string | CSS class added to the iframe `<body>` — use as a scope prefix in `css` |
| `customStyle.css` | string | Raw CSS injected into the iframe `<head>`. Scope rules under `baseClassName` to avoid conflicts |

**Example:** Transparent background for embedding in a dark host page:

```javascript
customStyle: {
  baseClassName: 'myapp',
  css: 'body.myapp { background: transparent; } body.myapp .kMain { border: none; }'
}
```


# 5. Message Types

Messages **from analytics app to host:**  

| messageType | Payload | Description |
|-------------|---------|-------------|
| `analyticsInit` | `{ menuConfig: object, viewsConfig: object }` | App loaded — sends default menu and viewsConfig for host to merge or override before responding with `init` |
| `analyticsInitComplete` | — | Initialization complete, app ready for `navigate` and `updateFilters` |
| `updateLayout` | `{ height: number }` | Request host to resize iframe to the given height in pixels. Handle this to avoid scrollbars inside the iframe |
| `scrollTo` | `string` (pixel offset) | Request host to scroll the parent window to the specified pixel offset |
| `navigateTo` | `string` (URL path) | User clicked a drill-down link — host should handle navigation (see section 9). Path includes entity type and ID |
| `navigateBack` | — | User clicked back — host should navigate to the previous view |
| `modalOpened` | — | A modal dialog opened inside analytics (host can dim its own UI) |
| `modalClosed` | — | The modal dialog closed |
| `logout` | — | Request host to log the user out (handle by destroying the iframe or redirecting) |

Messages **from host to analytics app:**  

| messageType | Payload | Description |
|-------------|---------|-------------|
| `init` | Full config object | KS, pid, servers, viewsConfig — see section 4 for the complete payload reference |
| `navigate` | `{ url: string, queryParams: object, prevRoute: string }` | Navigate to a specific view. `url` is the analytics path (see section 6). `prevRoute` tracks the previous path for context-aware back navigation |
| `updateFilters` | `{ queryParams: object }` | Update date range or other filters. Pass `dateBy` for presets or `dateFrom`/`dateTo` for custom ranges (see section 7) |
| `updateConfig` | Partial config object | Update configuration at runtime — use to refresh an expiring KS (`{ ks: 'new-ks' }`) or change viewsConfig without reinitializing |
| `setLanguage` | `string` (locale code) | Change UI language at runtime (e.g., `'fr'`, `'ja'`). See supported locales in section 4 |
| `updateMultiAccount` | `{ multiAccount: boolean }` | Toggle multi-account analytics on or off. Requires `FEATURE_MULTI_ACCOUNT_ANALYTICS` permission |
| `toggleContrastTheme` | — | Toggle high-contrast accessibility theme on or off |
| `setLogsLevel` | `{ level: string }` | Set logging verbosity for debugging. Levels: `"off"`, `"error"`, `"warn"`, `"info"`, `"debug"`, `"trace"` |


# 6. Navigation Paths

Send these paths via the `navigate` message to display a specific analytics view. Paths with `{ID}` require the entity ID in a `queryParams.id` field.

## Dashboard Views

| Path | View |
|------|------|
| `/analytics/engagement` | Audience engagement — plays, minutes viewed, unique viewers over time |
| `/analytics/content-interactions` | Content interactions — shares, downloads, playback speed, moderation |
| `/analytics/technology` | Technology — devices, browsers, operating systems |
| `/analytics/geo-location` | Geographic location — viewer distribution by country and region |
| `/analytics/contributors` | Top contributors — upload activity, source breakdown |
| `/analytics/overview` | Bandwidth & storage overview |
| `/analytics/publisher` | Publisher storage usage |
| `/analytics/enduser` | End-user storage usage |
| `/analytics/live` | Live entries real-time dashboard |

## Entity Drill-Down Views

| Path | queryParams | View |
|------|-------------|------|
| `/analytics/entry` | `{ id: ENTRY_ID }` | VOD entry analytics — engagement, performance, geo, devices |
| `/analytics/entry-live` | `{ id: ENTRY_ID }` | Live entry real-time — viewers, bandwidth, stream health, geo |
| `/analytics/entry-webcast` | `{ id: ENTRY_ID }` | Webcast entry — engagement, Q&A tools, quality metrics |
| `/analytics/entry-ep` | `{ id: ENTRY_ID }` | Events Platform session — viewers, minutes viewed, polls, recordings |
| `/analytics/category` | `{ id: CATEGORY_ID }` | Category analytics — top videos, subcategories, performance |
| `/analytics/playlist` | `{ id: PLAYLIST_ID }` | Playlist analytics — top videos, engagement, performance |
| `/analytics/user` | `{ id: USER_ID }` | User analytics — viewing history, contributions, geo |
| `/analytics/virtual-event` | `{ id: EVENT_ID }` | Virtual event — registration funnel, geo, industries, roles |
| `/analytics/event` | `{ id: EVENT_ID }` | Event engagement — sessions, reactions, messages, on-demand content |
| `/user-ep/{USER_ID}/{EVENT_ID}/{USER_NAME}` | — | User analytics scoped to an event (params in the path, not queryParams) |
| `/analytics/export` | `{ id: EXPORT_ID }` | CSV export download page |

**Navigation example — drill into a specific entry:**

```javascript
analyticsIframe.contentWindow.postMessage({
  messageType: 'navigate',
  payload: { url: '/analytics/entry', queryParams: { id: '0_abc123' } }
}, '*');

analyticsIframe.contentWindow.postMessage({
  messageType: 'updateFilters',
  payload: { queryParams: { dateBy: 'last30days' } }
}, '*');
```

## Default Navigation Menu Structure

When `menuConfig.showMenu` is `true`, the analytics app displays this menu:

```
Audience
├── Engagement           /analytics/engagement
├── Content Interactions /analytics/content-interactions
├── Technology           /analytics/technology
└── Geo Location         /analytics/geo-location
Contributors             /analytics/contributors
Bandwidth & Storage
├── Overview             /analytics/overview
├── Publisher Storage     /analytics/publisher
└── End-User Storage     /analytics/enduser
Real-Time                /analytics/live
```

Set `menuConfig.showMenu` to `false` when embedding a single view (e.g., entry analytics within a content page).


# 7. Date Filters

Send date filters via the `updateFilters` message. The `dateBy` parameter accepts these values:

| dateBy Value | Description |
|--------------|-------------|
| `last7days` | Last 7 days |
| `last30days` | Last 30 days |
| `last3months` | Last 3 months |
| `last12months` | Last 12 months |
| `currentWeek` | Current calendar week |
| `currentMonth` | Current calendar month |
| `currentQuarter` | Current calendar quarter |
| `currentYear` | Current calendar year |
| `previousMonth` | Previous calendar month |
| `sinceCreation` | Since the entity was created (entry, event, category) |
| `sinceFirstBroadcast` | Since the first broadcast (live/webcast entries) |
| `sinceLastBroadcast` | Since the last broadcast (live/webcast entries) |

For custom date ranges, pass `dateFrom` and `dateTo` as ISO date strings instead of `dateBy`. Use `compareTo` to enable period-over-period comparison.

```javascript
// Custom date range with comparison
analyticsIframe.contentWindow.postMessage({
  messageType: 'updateFilters',
  payload: {
    queryParams: {
      dateFrom: '2025-01-01',
      dateTo: '2025-03-31',
      compareTo: 'previousMonth'
    }
  }
}, '*');
```


# 8. viewsConfig — Controlling Dashboard Widgets

The `viewsConfig` object controls which widgets, filters, and buttons appear in every analytics view. Each key maps to a UI element — set a key to `null` to hide it, or `{}` to show it with defaults.

**How it works:**  
1. The analytics app sends its full default `viewsConfig` in the `analyticsInit` message  
2. The host merges or overrides specific keys  
3. The host passes the modified `viewsConfig` back in the `init` message  

**Example — embed entry analytics with no back button and no syndication panel:**

```javascript
window.addEventListener('message', function(e) {
  if (!e.data || e.data.messageType !== 'analyticsInit') return;

  var viewsConfig = e.data.payload.viewsConfig;

  // Hide elements by setting keys to null
  viewsConfig.entry.backBtn = null;
  viewsConfig.entry.syndication = null;
  viewsConfig.entry.allDetails = null;
  viewsConfig.entry.totals.social = null;

  analyticsIframe.contentWindow.postMessage({
    messageType: 'init',
    payload: {
      // ...server config, ks, pid...
      viewsConfig: viewsConfig
    }
  }, '*');
});
```

## Top-Level Dashboard Structure

Each top-level key corresponds to a dashboard type. Within each, nested keys control individual widgets:

**`audience.engagement`** — title, backBtn, download, export, refineFilter (mediaType, playbackType, entrySource, tags, owners, categories, domains, geo), miniHighlights, miniTopVideos, miniPeakDay, topVideos, highlights (userFilter, userDrilldown), impressions, syndication  

**`audience.contentInteractions`** — export, refineFilter (mediaType, entrySource, tags, owners, categories, domains, geo), miniInteractions, miniTopShared, topPlaybackSpeed, topStats, interactions, moderation  

**`audience.geo`** — export, refineFilter (geo, playbackType, tags, categories, domains)  

**`audience.technology`** — export, devices, topBrowsers, topOs, refineFilter (playbackType)  

**`bandwidth.overview`** — export, refineFilter (mediaType, entrySource, owners, geo)  

**`bandwidth.publisher`** — export, refineFilter (mediaType, entrySource, geo)  

**`bandwidth.endUser`** — export, refineFilter (mediaType, entrySource, owners, geo)  

**`contributors`** — export, refineFilter (mediaType, entrySource, tags, owners, categories, domains, geo), miniHighlights, miniTopContributors, miniTopSources, highlights, contributors, sources  

**`entry`** — title, backBtn, export, refineFilter (geo, owners, categories, domains), details, allDetails, totals (social: likes, shares), entryPreview, userEngagement (userFilter), performance (userFilter, contextFilter), impressions, geo, devices, syndication  

**`entryLive`** — title, backBtn, owner, export, toggleLive, details, users, bandwidth, geo, status, player, streamHealth, devices, discovery (userFilter)  

**`entryWebcast`** — export, title, backBtn, download, linkToLive, details, miniHighlights, miniEngagement (questions, viewers), miniQuality, highlights, liveEngagement, tools (slides, polls, announcements, answers), insights, entryPreview, userEngagement (userFilter), geo, devices, domains, refineFilter (playbackType, owners, devices, browsers, domains, os, geo)  

**`entryEP`** — download, title, backBtn, miniViewers, miniMinutesViewed, miniEngagement, miniPlays, recordings, polls, session, userDrilldown, geo, devices  

**`event`** — title, backBtn, download, miniFunnel, miniProfile, miniMinutesViewed, miniReactions, miniMessages, miniEngagement, eventOverTime, sessions, contentOnDemand  

**`virtualEvent`** — title, backBtn, download, details, refineFilter (origin), miniFunnel, miniOrigin, status, highlights, topDevices, geo, roles, industries  

**`category`** — title, backBtn, export, refineFilter (mediaType, playbackType, entrySource, tags, owners, context, categories, domains, geo), details, miniHighlights, miniPageViews, miniTopViewers, miniTopVideos, insights (domains, geo, devices), performance (userDrilldown, userFilter, userSearch, userLink, entryDrilldown, entryFilter, entryLink), topVideos, subcategories, geo, devices, syndication  

**`playlist`** — title, backBtn, export, videos, refineFilter (mediaType, playbackType, entrySource, tags, owners, categories, domains, geo), details, miniHighlights, miniTopVideos, miniTopViewers, miniInsights (peakDay, domains, geo, devices), totals, performance (userDrilldown, userFilter, userLink, entryDrilldown, entryFilter, entryLink), topVideos, geo, devices, syndication  

**`user`** — title, backBtn, avatar, details, export, refineFilter (mediaType, entrySource, tags, categories, domains), totals (entries, social), geoDevices, lastViewedEntries, insights (minutesViewed, plays, domains, sources), viewer (viewedEntries, engagement), contributor (mediaUpload, topContent, sources)  

**`userEp`** — title, download, metricsCards, eventInteractivity, userDetails, minutesViewed, sessions, polls, contentOnDemand  


# 9. Handling Drill-Down Navigation

When a user clicks a drill-down link inside the analytics dashboard (e.g., clicking an entry name from the engagement view), the analytics app sends a `navigateTo` message to the host with a URL path like `/content/entries/entry/0_abc123?dateBy=last30days`.

The host must handle this message and decide whether to:  
1. **Navigate within analytics** — parse the entity type and ID from the URL, then send `navigate` + `updateFilters` messages back to the analytics iframe  
2. **Navigate to a host page** — redirect the user to your application's page for that entity (e.g., a content detail page)  

```javascript
window.addEventListener('message', function(e) {
  if (!e.data || e.data.messageType !== 'navigateTo') return;

  var url = e.data.payload;  // e.g., "/content/entries/entry/0_abc123?dateBy=last30days"

  // Option 1: Re-route back into analytics
  var entryMatch = url.match(/entry\/(\w+)/);
  if (entryMatch) {
    analyticsIframe.contentWindow.postMessage({
      messageType: 'navigate',
      payload: { url: '/analytics/entry', queryParams: { id: entryMatch[1] } }
    }, '*');
    return;
  }

  // Option 2: Navigate to your app's page
  window.location.href = '/my-app/content/' + entryMatch[1];
});
```

When drilling down, you may need to refresh the KS for the new scope. Send `updateConfig` with the new KS before sending `navigate`:

```javascript
analyticsIframe.contentWindow.postMessage({
  messageType: 'updateConfig',
  payload: { ks: newKs }
}, '*');

analyticsIframe.contentWindow.postMessage({
  messageType: 'navigate',
  payload: { url: '/analytics/entry', queryParams: { id: entryId } }
}, '*');
```


# 10. KS Requirements

The KS passed in the `init` message must be an ADMIN KS (type=2) with permissions to access analytics data. The user associated with the KS must have a role with analytics permissions — the `Publisher Administrator` role includes these by default.

Use a short-lived KS and refresh it when the user navigates to the analytics view. To refresh the KS during an active session, send an `updateConfig` message with the new KS.

For multi-account analytics, the parent account must have the `FEATURE_MULTI_ACCOUNT_ANALYTICS` permission, and the KS must be generated on the parent account. Set `multiAccount: true` in the init payload.


# 11. Error Handling

- **`analyticsInitComplete` not received** — If the postMessage handshake starts (`analyticsInit` received) but `analyticsInitComplete` never arrives, verify the KS user has a role with analytics permissions. The app fetches the user's role during initialization — a user with empty `roleIds` causes the init to stall. Use the `Publisher Administrator` role or another role that includes analytics access.  
- **Blank iframe** — Verify the iframe `src` URL is accessible and HTTPS is used. Check the browser console for mixed content warnings.  
- **KS expiry during session** — The analytics app does not automatically renew expired sessions. Send an `updateConfig` message with a fresh KS to renew the session without reloading the iframe.  
- **Cross-origin postMessage issues** — When using the standard cross-origin iframe, ensure you do not filter `event.origin` too strictly in your `message` listener. The analytics app runs on `kmc.kaltura.com`.  


# 12. Best Practices

- **Hide the menu for single-view embeds.** Set `menuConfig.showMenu` to `false` when embedding a specific analytics view (e.g., entry analytics on a content detail page).  
- **Handle `updateLayout` messages.** The analytics app sends `updateLayout` with the content height — resize the iframe dynamically to avoid scrollbars inside the iframe:  

```javascript
window.addEventListener('message', function(e) {
  if (!e.data || e.data.messageType !== 'updateLayout') return;
  var iframe = document.getElementById('analytics');
  iframe.style.height = e.data.payload.height + 'px';
});
```

- **Handle `navigateTo` messages.** When users click drill-down links, the analytics app sends navigation requests to the host. Implement routing logic to either re-navigate within the analytics iframe or redirect to your application's pages.  
- **Refresh the KS proactively.** Send `updateConfig` with a fresh KS before the current one expires. This avoids silent API failures within the analytics dashboard.  
- **Use `viewsConfig` to scope the UI.** Hide irrelevant widgets, filters, and buttons by setting their `viewsConfig` keys to `null`. This creates a focused, branded analytics experience.  


# 13. Complete Integration Example

A full working example that handles the init handshake, dynamic iframe sizing, navigation, and KS refresh:

```html
<iframe id="analytics" title="analytics-iframe"
  src="https://kmc.kaltura.com/apps/kmc-analytics/latest/index.html"
  width="100%" height="800" style="border: none;"
  allowfullscreen allow="autoplay *; fullscreen *; encrypted-media *">
</iframe>

<script>
  var analyticsIframe = document.getElementById('analytics');
  var currentKs = '$KS';

  window.addEventListener('message', function(e) {
    if (!e.data || !e.data.messageType) return;

    switch (e.data.messageType) {
      case 'analyticsInit':
        // Step 1: Receive defaults, customize, send init
        var viewsConfig = e.data.payload.viewsConfig;
        viewsConfig.entry.backBtn = null;  // Hide back button in entry view
        analyticsIframe.contentWindow.postMessage({
          messageType: 'init',
          payload: {
            kalturaServer: { uri: 'https://www.kaltura.com', previewUIConfV7: 56732362 },
            cdnServers: { securedServerUri: 'https://cdnapisec.kaltura.com' },
            ks: currentKs,
            pid: parseInt('$PARTNER_ID'),
            locale: 'en',
            menuConfig: { showMenu: false },
            viewsConfig: viewsConfig
          }
        }, '*');
        break;

      case 'analyticsInitComplete':
        // Step 2: App ready — navigate to the desired view
        analyticsIframe.contentWindow.postMessage({
          messageType: 'navigate',
          payload: { url: '/analytics/engagement' }
        }, '*');
        break;

      case 'updateLayout':
        // Step 3: Resize iframe to match content height
        analyticsIframe.style.height = e.data.payload.height + 'px';
        break;

      case 'navigateTo':
        // Step 4: Handle drill-down clicks
        var url = e.data.payload;
        var entryMatch = url.match(/entry\/(\w+)/);
        if (entryMatch) {
          analyticsIframe.contentWindow.postMessage({
            messageType: 'navigate',
            payload: { url: '/analytics/entry', queryParams: { id: entryMatch[1] } }
          }, '*');
        }
        break;
    }
  });

  // Refresh KS before expiry
  function refreshAnalyticsKs(newKs) {
    currentKs = newKs;
    analyticsIframe.contentWindow.postMessage({
      messageType: 'updateConfig',
      payload: { ks: newKs }
    }, '*');
  }
</script>
```


# 14. Programmatic Alternative

For full programmatic access to analytics data (custom reports, CSV exports, time-series queries), use the [Analytics Reports API](KALTURA_ANALYTICS_REPORTS_API.md) instead. The API provides more granular control over report parameters, date ranges, and output formats without requiring iframe integration.


# 15. Related Guides

- **[Experience Components Overview](KALTURA_EXPERIENCE_COMPONENTS_API.md)** — Index of all embeddable components with shared guidelines  
- **[Analytics Reports API](KALTURA_ANALYTICS_REPORTS_API.md)** — Programmatic analytics data access (alternative to iframe embed)  
- **[Session Guide](KALTURA_SESSION_GUIDE.md)** — KS generation and privilege management  
- **[Events Platform](KALTURA_EVENTS_PLATFORM_API.md)** — Virtual events with event-specific analytics views  
- **[Multi-Account Management](KALTURA_MULTI_ACCOUNT_MANAGEMENT_API.md)** — Cross-account analytics configuration

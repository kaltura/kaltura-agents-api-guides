# Kaltura LTI Integration Guide

Integrate Kaltura video experiences into any LTI-compliant platform via KAF (Kaltura Application Framework). KAF is a hosted middleware within MediaSpace (Content Hub) that accepts LTI launches and renders video modules inside platform iframes — no server-side installation required.

**Deployment:** Hosted at `https://{partnerId}.kaf.kaltura.com` — nothing to install on the host platform  
**Auth:** LTI 1.1 (OAuth 1.0a) and/or LTI 1.3 (JWT/OIDC) — both supported simultaneously  
**Format:** iframe-based; host platform constructs LTI launch → KAF renders in iframe  

<!-- Sections: 1.When to Use LTI vs Native APIs | 2.Architecture (2.1 Application Profiles) | 3.Authentication Flows | 4.Content Isolation | 5.KAF Modules | 6.Deep Linking | 7.Grade Passback | 8.NRPS | 9.Caliper Learning Analytics | 10.Role Mapping | 11.Platform Configuration | 12.KAF Standalone | 13.API Management of KAF Resources | 14.iframe Communication | 15.Error Handling | 16.Best Practices | 17.Related Guides -->

# 1. When to Use LTI vs. Native APIs

| Criterion | LTI / KAF | Native Kaltura APIs |
|-----------|-----------|-------------------|
| Deployment target | Any LTI-compliant platform (LMS, LXP, HR systems, CRM, custom portals) | Standalone apps, portals, custom UIs |
| UI rendering | KAF provides complete UI in iframe — zero frontend code | Build your own UI with Player embed, widgets, and API calls |
| User provisioning | Automatic via LTI claims (name, email, role) | Manual via `user.add` or SSO/Auth Broker |
| Content isolation | Built-in per-course isolation via LTI `context_id` → category mapping | Build your own access control logic |
| Grade sync | Built-in AGS/Basic Outcomes passback | Custom webhook or polling |
| Module activation | Toggle in KAF Admin — zero code | Full implementation required |
| Customization depth | Configuration-level (admin toggles, theming, CSS) | Full API-level control |

**Use LTI/KAF** when deploying into an LTI-compliant platform (LMS, LXP, training portal, HR system) where users need video workflows (upload, browse, embed, quiz, analytics) with minimal development effort.

**Use native APIs** when building a standalone application outside any LTI-capable platform, or when you need full programmatic control over every interaction.

# 2. Architecture

```
┌──────────────────┐     LTI Launch (POST)      ┌──────────────────────┐
│                  │ ─────────────────────────► │                      │
│  Host Platform   │                            │    KAF Instance      │
│ (LMS, LXP, HR,   │ ◄───────────────────────── │  {pid}.kaf.kaltura   │
│  CRM, Portal)    │ Deep Link / Grade / Resize │                      │
└──────────────────┘                            └──────────┬───────────┘
                                                           │
                                                    Kaltura API v3
                                                           │
                                                           ▼
                                                ┌──────────────────────┐
                                                │   Kaltura Backend    │
                                                │  (Media, Search,     │
                                                │   Analytics, REACH)  │
                                                └──────────────────────┘
```

Each Kaltura partner gets a dedicated KAF instance at `https://{partnerId}.kaf.kaltura.com`. KAF:

- Accepts LTI launch requests from the host platform
- Creates a Kaltura Session (KS) scoped to the launching user and course context
- Renders the requested module (My Media, Media Gallery, Content Picker, etc.)
- Communicates with Kaltura backend APIs on behalf of the user
- Returns data to the host platform via LTI protocols (grades, content links, resize events)

The KAF Admin panel configures modules, role mappings, and feature toggles.

**Readiness check:** `GET https://{partnerId}.kaf.kaltura.com/version` — returns version info if instance is active.

## 2.1 Application Profiles

Each KAF instance is provisioned with an **application profile** that determines which modules and authentication methods are available.

| Profile Category | Profiles | Auth Method | Grade Passback |
|-----------------|----------|-------------|----------------|
| Platform-agnostic LTI | `ltigeneric` | LTI 1.1/1.3 | No (no `ltigrading` module) |
| LMS-specific | `canvas`, `moodle`, `d2l`, `blackboard`, `bbultra`, `sakai`, `sakailti`, `schoology` | LTI 1.1/1.3 | Yes (`ltigrading` module included) |
| Microsoft | `teams`, `sharepointo365`, `sharepointonprem` | LTI/KS/O365 | Varies |
| Enterprise social | `jive`, `jive9`, `ibmconnections`, `staffbase` | KS-SSO | No |
| CMS/CRM | `aem`, `salesforce`, `ecm` | KS-SSO | No |
| Standalone portal | `mediaspace` | SSO/SAML | N/A |

**Key differences between profiles:**

- **LMS profiles** (Canvas, Moodle, etc.) include the `ltigrading` module for AGS/Basic Outcomes grade passback, plus platform-specific user ID mappings, OIDC configurations, and `postDeployment()` hooks that auto-create shared repository categories
- **`ltigeneric`** provides core LTI launch without grade passback and without `postDeployment()` auto-provisioning — use this for non-LMS platforms (CRM, HR systems, training portals). Grade passback is still possible via LTI 1.1 Basic Outcomes if you provide `lis_outcome_service_url` in the launch
- **KS-SSO profiles** (Jive, AEM, Salesforce) authenticate via Kaltura Session appended to URL (`/ks/{token}`) rather than LTI launch
- **Each profile has a root category** — auto-created at provisioning as the content container for that instance

# 3. Authentication Flows

## 3.1 LTI 1.1 (OAuth 1.0a HMAC)

1. User clicks a Kaltura tool link in the host platform
2. Platform constructs a POST form with LTI parameters (`user_id`, `roles`, `context_id`, `resource_link_id`)
3. Platform signs the request using HMAC-SHA1 with the shared secret (partner ID = consumer key)
4. Browser auto-submits the signed form to KAF's launch endpoint
5. KAF validates the HMAC signature against the stored consumer secret
6. KAF creates a scoped KS for the user and renders the module

## 3.2 LTI 1.3 (JWT/OIDC)

1. User clicks a Kaltura tool link in the host platform
2. Platform redirects to KAF's OIDC initiation endpoint (`/hosted/index/oidc-init`) with `login_hint` and `target_link_uri`
3. KAF redirects back to the platform's authorization endpoint with `state`, `nonce`, `redirect_uri`
4. Platform authenticates the user and generates a signed JWT (`id_token`)
5. Platform POSTs the JWT to KAF's launch endpoint (`/hosted/index/oauth2-launch`)
6. KAF retrieves the platform's public keys via JWKS endpoint
7. KAF validates the JWT signature, issuer, audience, and nonce
8. KAF creates a scoped KS and renders the module

KAF auto-detects the LTI version from the incoming request. Both versions can run simultaneously from the same instance.

## 3.3 Service-to-Service (AGS / NRPS)

For grade passback and roster retrieval, KAF authenticates directly to the platform:

1. KAF creates a signed JWT assertion using its private key
2. KAF sends a client credentials grant to the platform's token endpoint
3. Platform returns a scoped access token
4. KAF uses the token to call platform REST endpoints (scores, line items, memberships)

## 3.4 KAF Endpoints for LTI 1.3

| Endpoint | Purpose |
|----------|---------|
| `/hosted/index/oidc-init` | OIDC login initiation — platform redirects here |
| `/hosted/index/oauth2-launch` | Launch redirect URI — platform POSTs signed JWT here |
| `/hosted/index/lti-advantage-key-set` | JWKS endpoint — platform fetches KAF's public keys |

# 4. Content Isolation

KAF isolates content per course through two mechanisms:

## 4.1 LTI Context-Based Isolation

KAF maps the LTI `context_id` claim to a Kaltura category. Each course launches with its own `context_id`, so KAF creates and manages a separate category per course automatically. Users only see content within their current course context.

This is the primary isolation mechanism for KAF instances. Content uploaded in one course gallery is not visible in another course's gallery — KAF handles this without any API configuration.

## 4.2 Privacy Context (MediaSpace / Multi-Instance)

The `privacycontext` KS privilege enables content isolation between multiple instances sharing a Kaltura account. This applies to **MediaSpace** (standalone portal) deployments, not KAF/LTI instances.

KAF profiles set privacyContext to empty during provisioning — KAF relies on LTI context-based isolation instead of Kaltura's category entitlement system.

**When privacyContext matters:** If you have multiple **MediaSpace** instances on one account (e.g., separate portals for different institutions), each instance uses a distinct privacy context name to isolate content. The KS privilege `privacycontext:CONTEXT_NAME` combined with `enableentitlement` restricts visibility to matching categories.

**API management of categories for KAF** — see section 12 for curl examples of provisioning course categories from a SIS (Student Information System).

# 5. KAF Modules

| Module | Code Name | Endpoint | Purpose |
|--------|-----------|----------|---------|
| My Media | `mymedia` | `/hosted/index/my-media` | Personal media library — upload, manage, publish |
| Media Gallery | `coursegallery` | `/hosted/index/course-gallery` | Shared course/group media repository |
| Content Picker (BSE) | `browseembed` | `/browseandembed/index/browseandembed` | Select/embed entries into platform content editor |
| Interactive Video Quizzes (IVQ) | `kaftestme` | via My Media / Content Picker | In-video quiz creation and playback with grade passback |
| Meeting Room | `embeddedrooms` | `/embeddedrooms/index/view-room` | Entry-based meeting/virtual classroom rooms |
| Webcast | `kwebcast` | config module | Live streaming within courses |
| Content Lab | `kalturaai` | `/contentlab` | Content repurposing (summaries, chapters, clips, quizzes) |
| Genie AI | `genieai` | `/genie` | Conversational search over video library |
| Avatar VOD Studio | `avatarvodstudio` | `/avatarvodstudio/index/index` | Avatar video generation from scripts (Beta) |
| Chat & Collaborate | `chatandcollaboration` | config module | Real-time chat, Q&A, polls |

Modules are enabled/disabled per-partner in KAF Admin. Each module can be toggled independently.

**Module path pattern:** Modules with their own KAF admin tab (e.g., `genieai`, `avatarvodstudio`, `embeddedrooms`) use their own route prefix. Only standard views go through `/hosted/index/`.

**Meeting Room** requires additional custom LTI parameters: `custom_entry_id` (the room's entry ID) and `custom_room_moderator` (set to `1` for moderator rights). The launching user's `roles` must be `Instructor` for moderator access. Rooms are regular Kaltura entries (type=meeting) created via My Media → Add New → Meeting Room.

**Shared Repository** is not a standalone LTI placement. It appears as a tab within the Content Picker when enabled in KAF Admin (Hosted module → "Enable Shared Repository" + Channels module enabled). Users see it as a content source alongside "My Media" and "Media Gallery" tabs in the Browse & Embed interface.

**Network requirements:** All KAF modules require connectivity to `*.kaf.kaltura.com` and `*.kaltura.com`. Some modules additionally load components from `unisphere.*.ovp.kaltura.com` — ensure all Kaltura domains are allowlisted.

# 6. Deep Linking (Content Selection)

The Content Picker module enables users to select Kaltura entries for embedding in platform content.

**LTI 1.1 (ContentItemSelectionRequest):**

1. Platform sends `ContentItemSelectionRequest` with `content_item_return_url`
2. KAF renders the browse/search interface
3. User selects an entry
4. KAF POSTs a `ContentItemSelection` response back to `content_item_return_url`

**LTI 1.3 (Deep Linking):**

1. Platform launches with `LtiDeepLinkingRequest` message type
2. KAF renders the content picker
3. User selects an entry
4. KAF returns a signed JWT with `LtiDeepLinkingResponse` message type

**Fields returned:**

| Field | Description |
|-------|-------------|
| `url` | Launch URL for the selected entry |
| `entry_id` | Kaltura entry ID |
| `title` | Entry name |
| `thumbnailUrl` | Thumbnail image URL |
| `duration` | Duration in seconds |
| `width` / `height` | Player dimensions |

# 7. Grade Passback (AGS)

Interactive Video Quizzes (IVQ) and assignment modules pass scores back to the platform gradebook. Grade passback requires the `ltigrading` module, which is included in LMS-specific profiles (Canvas, Moodle, D2L, Blackboard, Sakai, Schoology) but not in `ltigeneric`.

**LTI 1.1 (Basic Outcomes):**  
KAF sends an XML `replaceResultRequest` to `lis_outcome_service_url`. Scores are normalized 0.0–1.0.

**LTI 1.3 (Assignment and Grade Services):**

1. KAF obtains a service token via client credentials grant (see §3.3)
2. KAF creates/updates a line item on the platform
3. KAF POSTs score records per student

Required scopes:
- `https://purl.imsglobal.org/spec/lti-ags/scope/lineitem`
- `https://purl.imsglobal.org/spec/lti-ags/scope/score`
- `https://purl.imsglobal.org/spec/lti-ags/scope/result.readonly`

# 8. NRPS (Roster Retrieval)

Names and Role Provisioning Services allows KAF to retrieve course membership from the platform.

**Scope:** `https://purl.imsglobal.org/spec/lti-nrps/scope/contextmembership.readonly`

**Flow:**

1. Launch includes `namesroleservice` claim with `context_memberships_url`
2. KAF obtains a service token with NRPS scope
3. KAF calls the membership endpoint to retrieve enrolled users and roles

**Status:** Implemented for LTI Advantage compliance. Membership data is retrieved but not yet consumed for pre-provisioning features.

# 9. Caliper Learning Analytics

KAF supports IMS Caliper 1.2 for emitting structured learning events (video views, quiz attempts, session tracking). The host platform acts as a Learning Record Store (LRS) — KAF discovers the event store via a profile URL provided in the LTI launch, then pushes events in real time.

## 9.1 LTI Parameters

Include these custom parameters in every launch to enable Caliper:

| Parameter | Value | Purpose |
|-----------|-------|---------|
| `custom_caliper_profile_url` | `{base_url}/caliper/profile` | KAF calls this to discover your event store |
| `custom_caliper_federated_session_id` | `session_{user_id}_{nonce}` | Correlates analytics events to the LTI session |

## 9.2 Profile Endpoint

Your platform exposes a profile endpoint. KAF calls it (server-to-server) to discover where to send events:

```json
{
  "id": "platform-lrs",
  "type": "EventStore",
  "apiUrl": "{base_url}/caliper/events",
  "apiKey": "{your_api_key}",
  "sendEvents": true,
  "includeActors": true,
  "includeGeneratedValues": true
}
```

## 9.3 Event Delivery

KAF POSTs Caliper event payloads to the `apiUrl` with `Authorization: {apiKey}` header. Event types include:

| Event Type | Trigger |
|-----------|---------|
| `MediaEvent` | Video play, pause, seek, complete |
| `NavigationEvent` | User navigates within KAF |
| `AssessmentEvent` | Quiz start, submit |
| `AssessmentItemEvent` | Individual question answered |
| `SessionEvent` | Login/logout |
| `ViewEvent` | Page/entry viewed |

## 9.4 KAF Configuration

In KAF Admin at `/admin/config/tab/caliper`, set `directCaliperIntegration=No`. This tells KAF to read the profile URL from the LTI launch parameters rather than using a hardcoded event store.

The profile URL must be reachable from KAF's servers — when developing locally, use a tunnel (e.g., cloudflared) so KAF can reach your endpoints.

# 10. Role Mapping

| LIS Role (from LTI) | Kaltura Role | Behavior |
|---------------------|--------------|----------|
| Instructor | Admin (course-level) | Upload, manage, publish, view analytics |
| TeachingAssistant | Moderator | Upload, manage own content, moderate submissions |
| Learner / Student | Viewer | View content, submit assignments, take quizzes |
| Administrator | Admin | Full course administration |
| ContentDeveloper | Admin | Same as Instructor |
| Guest | Guest | View-only, limited access (added Jan 2026) |

Role mapping is configurable per-platform in KAF Admin. Custom role strings can be mapped to Kaltura roles via the admin panel.

# 11. Platform Configuration

## 11.1 Canvas

Configure as an External Tool with JSON config URL:
- **Config URL:** `https://{partnerId}.kaf.kaltura.com/canvas/config.json`
- Enable LTI 1.3 in Canvas Developer Keys
- Required scopes: `lineitem`, `score`, `result.readonly`, `contextmembership.readonly`

## 11.2 Moodle

- Install the Kaltura Video Package plugin
- Configure LTI credentials (consumer key + shared secret for 1.1, or platform registration for 1.3)
- Toggle LTI version in plugin configuration (`lti_version` setting)

## 11.3 Blackboard (LTI 1.3 Advantage Certified)

- Register as LTI 1.3 tool in Blackboard admin
- Configure placement URLs per module
- Note: Blackboard Base64-encodes some LTI parameters (`user_id`, `context_title`, `lis_person_name_*`) — KAF handles decoding automatically

## 11.4 D2L / Brightspace

- Register external learning tool with OIDC and JWKS URLs
- Configure iframe height (recommended: 800px minimum)
- User ID claim: configurable via `lti13UserIdClaim` in KAF Admin

## 11.5 Sakai

- Configure via `basiclti.properties` or admin External Tools interface
- LTI 1.3 support available (added Jan 2023)

## 11.6 Generic LTI (Any Compliant Platform)

Any LTI 1.1 or 1.3 compliant platform works with KAF:
- **Launch URL:** `https://{partnerId}.kaf.kaltura.com/hosted/index/{module}`
- **Consumer Key / Client ID:** Provided by Kaltura
- **Shared Secret:** Provided by Kaltura (LTI 1.1 only)

**KAF-side settings (in KAF Admin):**

| Setting | Purpose |
|---------|---------|
| `lti13ClientId` | Client ID for this platform registration |
| `lti13PlatformOidcAuthUrl` | Platform authorization endpoint |
| `lti13AuthTokenUrl` | Platform token endpoint (for AGS/NRPS calls) |
| `lti13KeysUrl` | Platform JWKS endpoint (for JWT validation) |

# 12. KAF Standalone (Non-LTI Embed)

For embedding KAF modules in applications without LTI support, use KS-SSO (Single Sign-On via Kaltura Session). KS-SSO requires the KAF instance to be configured with `authMethod=ks` (used by profiles like Jive, AEM, Salesforce, and custom configurations). LTI-based profiles (`ltigeneric`, Canvas, Moodle, etc.) require a signed LTI launch for access.

**Pattern:** Append `/ks/{token}` to any KAF module URL.

**Generate a scoped KS for standalone embed:**

```bash
curl -X POST "$KALTURA_SERVICE_URL/service/session/action/start" \
  -d "format=1" \
  -d "partnerId=$KALTURA_PARTNER_ID" \
  -d "secret=$KALTURA_ADMIN_SECRET" \
  -d "type=0" \
  -d "userId=user@example.com" \
  -d "expiry=3600" \
  -d "privileges=disableentitlement"
```

**Construct the embed URL:**

```
https://{partnerId}.kaf.kaltura.com/hosted/index/my-media/ks/{KS_TOKEN}
```

Embed this URL in an iframe. The user sees their My Media library. The KAF instance must be configured with `authMethod=ks` — LTI-based profiles reject KS-SSO access and require a signed LTI launch instead.

# 13. API Management of KAF Resources

These Kaltura v3 API calls manage resources that KAF uses — for SIS (Student Information System) integrations that provision courses, enroll students, or sync content outside the LTI flow.

**Create a course category (for SIS sync):**

```bash
curl -X POST "$KALTURA_SERVICE_URL/service/category/action/add" \
  -d "ks=$KALTURA_KS" \
  -d "format=1" \
  -d "category[name]=COURSE_CS101_Fall2026" \
  -d "category[description]=CS101 Introduction to Computer Science"
```

Create course categories under the KAF instance's root category. KAF maps the LTI `context_id` to these categories automatically during LTI launches. Pre-provisioning from a SIS ensures the category exists before the first user launch.

**Enroll a student (from SIS roster):**

```bash
curl -X POST "$KALTURA_SERVICE_URL/service/categoryUser/action/add" \
  -d "ks=$KALTURA_KS" \
  -d "format=1" \
  -d "categoryUser[categoryId]=$COURSE_CATEGORY_ID" \
  -d "categoryUser[userId]=student@university.edu" \
  -d "categoryUser[permissionLevel]=0"
```

Permission levels: `0`=MEMBER (view), `2`=MODERATOR (manage content), `3`=MANAGER (manage members).

**Pre-assign content to a course:**

```bash
curl -X POST "$KALTURA_SERVICE_URL/service/categoryEntry/action/add" \
  -d "ks=$KALTURA_KS" \
  -d "format=1" \
  -d "categoryEntry[categoryId]=$COURSE_CATEGORY_ID" \
  -d "categoryEntry[entryId]=$KALTURA_ENTRY_ID"
```

These operations complement what KAF does automatically during LTI sessions. Use them when you need to pre-provision courses from a SIS before any user launches KAF, or when syncing enrollment data from external systems.

# 14. iframe Communication

KAF communicates with the host platform page via `postMessage`. Listen for these events to enable responsive embed behavior.

| Event Subject | Purpose | Data |
|---------------|---------|------|
| `lti.frameResize` | KAF content height changed | `{ height: pixels }` |
| `lti.navigation` | User navigated within KAF | Module path |
| `lti.contentSelected` | User selected content in Content Picker | Entry metadata |
| `lti.hideModuleHeader` | Request to hide platform navigation | — |

**Example listener:**

```javascript
window.addEventListener("message", function(event) {
  if (event.origin !== "https://{partnerId}.kaf.kaltura.com") return;
  var data = JSON.parse(event.data);
  if (data.subject === "lti.frameResize") {
    document.getElementById("kaf-iframe").style.height = data.height + "px";
  }
});
```

# 15. Error Handling

| Issue | Cause | Resolution |
|-------|-------|------------|
| Session conflict (multiple embeds) | Multiple KAF iframes share cookies | Use distinct `target` parameter per embed |
| Access denied to Media Gallery | User role not mapped or module disabled | Verify role mapping in KAF Admin; confirm module is enabled |
| Content not visible in course | Entry not assigned to course category | Upload must occur within KAF course context, or use categoryEntry.add via API |
| iframe fails to render | CSP blocks framing or third-party cookies blocked | Allowlist `*.kaf.kaltura.com` in frame-src |
| iframe height insufficient | Default too small for module content | Set min-height 800px; listen for `lti.frameResize` |
| LTI signature validation fails | Clock skew or wrong secret | Ensure server time is within 5 minutes of UTC; verify credentials |
| Grade not appearing in gradebook | AGS scopes not granted | Re-register tool with `lineitem` and `score` scopes |
| Modules not loading | Network blocks Kaltura domains | Allowlist `*.kaf.kaltura.com`, `*.kaltura.com`, `unisphere.*.ovp.kaltura.com` |
| Meeting Room shows "Application Error" | Wrong entry ID or wrong module path | Use `/embeddedrooms/index/view-room` with a valid `custom_entry_id` |
| Caliper events not received | Profile URL unreachable from KAF servers | Profile URL must be publicly accessible (use tunnel for localhost development) |
| Content Picker return fails (localhost) | Chrome Local Network Access blocks public-to-private redirect | Use a public HTTPS URL (cloudflared tunnel) for `content_item_return_url` |

# 16. Best Practices

1. **Choose the right application profile.** Use `ltigeneric` for non-LMS platforms. Use LMS-specific profiles (Canvas, Moodle, etc.) when you need grade passback via the `ltigrading` module.

2. **Use LTI 1.3 for new deployments.** Stronger security (signed JWTs vs. shared secrets), service-to-service auth for AGS/NRPS, and required by modern platforms.

3. **Configure role mappings explicitly.** Review default LIS-to-Kaltura mappings in KAF Admin. Some roles (e.g., TeachingAssistant) are not mapped by default and will be denied access until configured.

4. **Test with `ltigeneric` profile first.** Validate core LTI behavior before adding platform-specific configurations.

5. **Allowlist all Kaltura domains.** `*.kaf.kaltura.com`, `*.kaltura.com`, and `unisphere.*.ovp.kaltura.com` — not just for specific modules.

6. **Use separate KAF instances for multi-institution deployments.** Each institution gets its own KAF instance with a unique root category, ensuring content isolation.

7. **Listen for iframe postMessage events.** Implement `lti.frameResize` at minimum for responsive embedding.

8. **Set iframe minimum height to 800px.** Prevents content clipping while resize events propagate.

9. **Register both placements and deep links.** Configure navigation placements (Media Gallery, My Media) and editor placements (Content Picker) for the complete workflow.

10. **Use KAF Admin to manage module access.** Enable/disable modules centrally rather than building custom permission logic.

# 17. Related Guides

- **[LTI Platform Integration Playbook](playbooks/LTI_PLATFORM_INTEGRATION.md)** — Build an LTI consumer with Caliper analytics, grade passback, deep linking, and SIS provisioning (working sample app included)
- **[Categories & Entitlements](KALTURA_CATEGORIES_AND_ENTITLEMENTS_API.md)** — Category hierarchy, privacy contexts, membership, and entitlement enforcement
- **[User Management](KALTURA_USER_MANAGEMENT_API.md)** — User provisioning, roles (RBAC), and groups
- **[Quiz](KALTURA_QUIZ_API.md)** — Interactive Video Quiz creation, question types, scoring, and reports
- **[Analytics Reports](KALTURA_ANALYTICS_REPORTS_API.md)** — Engagement metrics, per-entry and per-user reports
- **[REACH](KALTURA_REACH_API.md)** — Enrichment services (captions, translation, moderation) for content
- **[Player Embed](KALTURA_PLAYER_EMBED_GUIDE.md)** — Player v7 embed for custom integrations outside KAF
- **[Unisphere Framework](KALTURA_UNISPHERE_FRAMEWORK_API.md)** — Micro-frontend framework for embeddable components
- **[Access Control](KALTURA_ACCESS_CONTROL_API.md)** — IP, domain, and geo restrictions for content delivery

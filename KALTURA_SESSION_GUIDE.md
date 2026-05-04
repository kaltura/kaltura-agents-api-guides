# Kaltura Session (KS) Generation and Management

Generate, use, and rotate Kaltura Sessions (KS) — the signed, time-limited tokens that authenticate every Kaltura API call and player embed.

**Base URL:** `https://www.kaltura.com/api_v3` (may differ by region/deployment)  
**Auth:** KS passed as `ks` parameter in POST form data, or as embed URL parameter  
**Format:** Form-encoded POST, `format=1` for JSON responses  

<!-- Sections: 1.When to Use | 2.Prerequisites | 3.What is a KS and when to use which flow | 4.Common security practices | 5.REST API Recipes | 6.Passing the KS to APIs and the Player | 7.Privileges: what to actually use | 8.Renewal, caching, and fallback | 9.Error Handling | 10.Best Practices | 11.Related Guides -->


# 1. When to Use

- **Every Kaltura API integration starts here** -- a valid Kaltura Session (KS) is required for every API call and player embed across the platform.  
- **Backend automation systems** generate server-side sessions with appropriate type, expiry, and privileges to control what each integration can access.  
- **Client-facing applications** use AppToken-based session exchange to obtain scoped KS tokens without exposing admin secrets to end users.  
- **Security and compliance teams** define session privilege policies that enforce content isolation, user tracking, and access boundaries.

# 2. Prerequisites

- **Partner ID:** Your Kaltura account identifier, available from the KMC under Settings > Integration Settings.  
- **Admin secret (for `session.start`):** Required for server-side KS generation. Keep strictly server-side; use AppTokens for client-facing integrations.  
- **Service URL:** Set `$KALTURA_SERVICE_URL` to your account's regional endpoint (default: `https://www.kaltura.com/api_v3`).  
- **Understanding of session types:** USER (type=0) for end-user contexts, ADMIN (type=2) for backend administration. This guide covers both.

# 3. What is a KS and when to use which flow

A Kaltura Session (KS) is a signed, time-limited token you attach to API calls and player embeds. KS can be USER (type=0) or ADMIN (type=2). Use USER for almost everything where an end-user is interacting with apps or data; use ADMIN only for trusted backend-only workflows with short TTLs and strict configurations (roles, privileges).

**Common use-cases and considerations:**  

*	Server-to-server or trusted backend: session.start → returns a KS with the privileges and expiry you request. Run this server-side only to keep secrets secure.
*	App-to-API with elevated but scoped permissions: use Application Tokens and appToken.startSession. You obtain a basic (unprivileged) KS, compute a hash with the app token, and exchange it for a privileged KS — keeping admin secrets and hashing strictly server-side.
*	Widget/player bootstrap (the player will generate this KS by itself if no KS was provided to the player: session.startWidgetSession to get a base KS used in the App Token flow.

## KS Internal Structure

A KS is a base64-encoded string containing these components:

| Field | Description |
|-------|-------------|
| Partner ID | The Kaltura account that issued the KS |
| User ID | The user identity bound to this session |
| Type | 0 = USER, 2 = ADMIN |
| Expiry | Unix timestamp when the KS becomes invalid |
| Privileges | Comma-separated privilege strings (e.g., `sview:*,privacycontext:PORTAL`) |
| Random number | Prevents replay of identical requests |
| KS data | Additional session context (action limits, session ID) |
| Signature | SHA-1 hash of all fields above — tamper-proofing |

KS v2 (current default) wraps the payload in AES-CBC encryption before base64 encoding, so the internal fields are not readable by inspecting the string. The server decrypts and validates on every request.

## KS Validation Flow

The server validates the KS on every API request in this sequence:

1. **Signature check** — Verify the SHA-1 signature matches the decrypted payload
2. **Expiry check** — Reject if the KS has expired (Unix timestamp comparison)
3. **Action limit** — If `actionslimit:N` is set, decrement and reject if exhausted
4. **Revocation check** — Check if `session.end` was called for this KS or its `sessionid` group
5. **Permission check** — Verify the KS type and role grant access to the requested service/action
6. **Entitlement check** — If entitlements are enabled, verify the user has category membership for the requested content
7. **Account check** — Verify the partner ID is active and the service is enabled
8. **Set user context** — Bind the validated userId to the request for ownership, analytics, and audit

If any step fails, the server returns a `KalturaAPIException` with the relevant error code (`INVALID_KS`, `EXPIRED_KS`, `SERVICE_FORBIDDEN`, etc.).

## KS Creation Methods — Comparison

| Method | Credentials Required | Best For | Trade-offs |
|--------|---------------------|----------|------------|
| `session.start` | partnerId + adminSecret | Backend tools, server-side automation | HTTP roundtrip; exposes admin secret (keep server-side only) |
| `session.startWidgetSession` | partnerId only (no secret) | Anonymous player bootstrap, AppToken base KS | Unprivileged — read-only access to public content |
| `appToken.startSession` | appToken ID + HMAC hash | Production integrations, client-facing apps | **Preferred**: no secrets exposed, revocable, scoped privileges |
| `user.loginByLoginId` | email + password | End-user self-authentication, mobile apps | User-managed credentials; requires user provisioning first |


# 4. Common security practices

*	Least privilege: Prefer USER KS; scope permissions to what the call needs.
*	Short TTLs: Set per the expected user interaction duration, balancing security with renewal frequency.
*	Backend only: Keep admin secrets and app token secrets on the server side.
*	Entitlements over broad privileges: Enforce access via Access Control/Entitlements and privacy context strings in KS. Use specific privileges; use `*` only for controlled internal ADMIN sessions.
* Rotate Application Tokens and Sessions regularly. Revoke as needed using `session.end`.
* **API secrets are permanent.** The `adminSecret` and `secret` for a Kaltura account cannot be regenerated, rotated, or revoked. If a secret is compromised, contact Kaltura support. Use Application Tokens (AppTokens) for all integrations — AppTokens can be revoked and reissued independently, giving you full credential lifecycle control. See [AppTokens Guide](KALTURA_APPTOKENS_API.md).

# 5. REST API Recipes

All calls use the v3 endpoint with form-encoded POST data and `format=1` for JSON responses.

`Base URL: https://www.kaltura.com/api_v3/` (this URL can change depending on geo region, or deployment, the account was configured on)

## 5.1. Generate a KS (backend) with session.start

```bash
curl -X POST "$KALTURA_SERVICE_URL/service/session/action/start" \
  -d "partnerId=$KALTURA_PARTNER_ID" \
  -d "secret=$KALTURA_ADMIN_SECRET" \
  -d "userId=testUser" \
  -d "type=0" \
  -d "expiry=1800" \
  -d "privileges=sview:*" \
  -d "format=1"
```

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `secret` | string | Yes | Admin secret (`type=2`) or user secret (`type=0`) |
| `partnerId` | integer | Yes | Your Kaltura partner ID |
| `type` | integer | Yes | `0` = USER, `2` = ADMIN |
| `userId` | string | No | User ID for the session (default: empty) |
| `expiry` | integer | No | TTL in seconds (default: 86400 = 24 hours) |
| `privileges` | string | No | Comma-separated privilege strings (e.g., `sview:*,edit:*`) |

**Response:** The KS string (with `format=1`, wrapped as `"djJ8OTc2NDYx..."`).

```json
"djJ8OTc2NDYx..."
```

* `type=0` is USER, `type=2` is ADMIN.
* `expiry` is in seconds (1800 = 30 minutes).

> When to use: server-side APIs, signed/secure player embeds, upload/edit tasks that your backend coordinates. Scope privileges to the minimum required for each session.


## 5.2. Bootstrap a base KS with session.startWidgetSession

```bash
curl -X POST "$KALTURA_SERVICE_URL/service/session/action/startWidgetSession" \
  -d "widgetId=_$KALTURA_PARTNER_ID" \
  -d "format=1"
```

* `widgetId` is `_<partnerId>` (underscore prefix).
* The response JSON contains `{ "result": { "ks": "<WIDGET_KS_STRING>", ... } }`.

> This will be used as initial session for AppTokens, or for non-authenticated light sessions such as anonymous player embeds (generated by the player itself when a KS is not provided).


## 5.3. AppTokens → Privileged KS with appToken.startSession

High level flow:

1.	Create & store an Application Token (this action is performed once by the account admin to provide API access to a 3rd party trusted-scope partner. This step basically provisions an application security scope). See the [AppTokens Guide](KALTURA_APPTOKENS_API.md) for full details.
2.	Get a base KS (e.g., widget session).
3.	Compute tokenHash = HASH( baseKS + token ) with the same hash type as the app token.
4.	Call appToken.startSession(tokenId, tokenHash, ...) to receive the privileged KS.

> Keep the token and hashing strictly server-side.
> `sessionPrivileges` and `sessionUserId` are locked at token creation and enforced on every session minted from the token. Configure them at creation time.

**Step 1 -- Get a widget (base) KS:**

```bash
curl -X POST "$KALTURA_SERVICE_URL/service/session/action/startWidgetSession" \
  -d "widgetId=_$KALTURA_PARTNER_ID" \
  -d "format=1"
```

Save the returned `result.ks` value as `WIDGET_KS`.

**Step 2 -- Compute the token hash:**

Compute `tokenHash = SHA256(WIDGET_KS + APP_TOKEN_VALUE)` using your language's crypto library. The hash algorithm must match what was set when the Application Token was created (SHA256 is recommended).

For example, in a shell:

```bash
TOKEN_HASH=$(echo -n "${WIDGET_KS}${KALTURA_APP_TOKEN}" | shasum -a 256 | awk '{print $1}')
```

**Step 3 -- Exchange for a privileged KS:**

```bash
curl -X POST "$KALTURA_SERVICE_URL/service/apptoken/action/startSession" \
  -d "ks=$WIDGET_KS" \
  -d "id=$KALTURA_APP_TOKEN_ID" \
  -d "tokenHash=$TOKEN_HASH" \
  -d "userId=testUser" \
  -d "type=0" \
  -d "expiry=1800" \
  -d "sessionPrivileges=sview:*" \
  -d "format=1"
```

* The response JSON contains the privileged KS in `result`.

> You can disable or delete tokens (`appToken.update` → status, or `appToken.delete`) immediately revoking the app’s ability to mint KS.

# 6. Passing the KS to APIs and the Player

* APIs: include ks=<SESSION_STRING> in form data for each call.
* Player embeds: pass ks in the player setup or in the iframe embed URL.

# 7. Privileges: what to actually use

Keep it tight:

* Playback: sview:* (+ enforce entitlements and access control profiles in your account configuration).
* Upload/edit tools: add only what’s required for the desired feature set (e.g., edit specific objects or rely on server APIs that hold ADMIN).
* Use privacy context (e.g., privacycontext:EDU_PORTAL) in KS to align with entitlement rules, ensuring the session is scoped to the appropriate user and content boundaries.
* Reserve `*` for short-lived backend ADMIN sessions that stay server-side.

# 8. Renewal, caching, and fallback

* TTL you control: you set expiry when starting the session; store issued_at + expiry in your app and refresh as needed *before it lapses*.
* Client pattern: your frontend should get KS rendered from your backend — secrets stay on the server.
* Pass KS in POST bodies so the token stays out of proxy caches and URL logs.
* The Kaltura API validates the KS on every request automatically and returns an error if it is invalid or expired. Validation is implicit — use any API call to confirm a KS is valid.
* Store KS in memory only; set `Cache-Control: no-store` headers to keep tokens ephemeral.
* Pass KS in POST bodies or PlayKit provider config — these transport channels keep the token private from referrer headers, logs, and proxies.
* Revoke a session immediately with `session.end`:

```bash
curl -X POST "$KALTURA_SERVICE_URL/service/session/action/end" \
  -d "ks=$KALTURA_KS" \
  -d "format=1"
```

After `session.end`, the KS is immediately rejected by all subsequent API calls. Use this for logout flows, session revocation, and security incident response.

# 9. Error Handling

* Common KS-related error codes: `INVALID_KS` (malformed, expired, or revoked), `MISSING_KS` (no KS provided), `SERVICE_FORBIDDEN` (KS lacks permission), `EXPIRED_KS` (session past TTL), `ACTION_BLOCKED` (action limit reached).
* On invalid/expired KS or insufficient privileges: re-issue with correct scope.
* On 5xx / transient: use exponential backoff (e.g., 500ms, 1s, 2s, jitter), and cap retries. Monitor your request rate to stay within throttling limits.
* Observability: log who asked for a session, requested TTL & privileges, and the call outcome (success/failure). Mask KS values in logs (show only last 6 chars) and store secrets exclusively in secret managers.

**Retry strategy:** For transient errors (HTTP 5xx, timeouts), retry with exponential backoff: 1s, 2s, 4s, with jitter, up to 3 retries. For client errors (4xx, `INVALID_KS`, insufficient privileges), fix the request parameters or re-issue the KS before retrying — these require corrective action to succeed.

# 10. Best Practices

- **Use AppTokens in production.** Generate KS via `appToken.startSession` with HMAC — keep admin secrets off application servers (see [AppTokens Guide](KALTURA_APPTOKENS_API.md)).
- **Use USER KS (type=0) for client-side operations.** Reserve ADMIN KS (type=2) for server-side workflows that require write access.
- **Set short TTLs.** 1 hour for user-facing sessions, 15 minutes for server-side automation. Shorter sessions reduce exposure if a token leaks.
- **Scope privileges minimally.** Use `setrole`, `privacycontext`, `sview`, and `iprestrict` to limit what a KS can access.
- **Call `session.end` to revoke when done.** Use the `sessionid` privilege to enable bulk logout across devices.
- **Pass KS in POST bodies.** POST bodies keep tokens private — URL parameters appear in referrer headers, proxy logs, and browser history.

## Mobile / Client-Side KS Best Practices

Mobile and single-page apps require special care because compiled binaries and client-side JavaScript are accessible to end users:

- **Keep `adminSecret` on your backend server.** API secrets are permanent — use Application Tokens (AppTokens) for all scenarios requiring revocable credentials. See [AppTokens Guide](KALTURA_APPTOKENS_API.md).
- **Generate KS server-side and pass to the client per-session.** Issue fresh KS tokens per session to ensure continuous access and maintain full revocation control.
- **Three recommended strategies for client-side KS:**
  1. **Anonymous access** — Use `session.startWidgetSession` for public, unauthenticated content (player bootstrap, public galleries).
  2. **Server-generated KS** — Your backend generates a scoped USER KS (via `session.start` or `appToken.startSession`) and passes it to the client per-session. Secrets remain exclusively on the server.
  3. **User login** — Use `user.loginByLoginId` for apps where users authenticate with their own credentials. The KS is generated server-side and returned to the client.

## Special Partner IDs

Certain partner IDs are reserved by the Kaltura platform for internal purposes:

| Partner ID | Purpose |
|-----------|---------|
| -1 | Batch Manager (internal job processing) |
| -2 | Admin Console |
| -3 | Hosted Pages |
| 0 | Shared/global resources |
| 99 | Default template partner |

These IDs appear in logs and system metadata. Customer accounts always have positive partner IDs.

## Entitlements & KS Privileges Patterns

### Make the client KS playback-only

Lock KS to a minimal playback role: add `setrole:PLAYBACK_BASE_ROLE` so only a white-listed set of read/player calls is allowed (e.g., `baseEntry.get`, `flavorAsset.list`).

If your content is public and unauthenticated, you can use a Widget KS instead (anonymous, READ-only, for publicly available assets). For protected content, issue a USER KS with entitlements (see below).

### Enforce entitlements with privacy context

If your catalog uses Entitlements, enable server-side checks on the KS and set the privacy context that scopes what the user can see:
* `enableentitlement` — tells Kaltura to enforce entitlement checks on this KS.
* `privacycontext:<LABEL>` — sets the entitlement partition (<LABEL> is free-text label you define in the KMC per category).

> Example: `enableentitlement,privacycontext:PORTAL_A` ensures results are scoped to the category membership of privacy context `PORTAL_A`. Use `enableentitlement` on all client-facing KS.

### Scope what can be viewed or listed

*	Playback scope: Allow all playback in the entitlement context: `sview:*`. *Or* lock to a single entry: `sview:<ENTRY_ID>` (use with KS-restricted access control to ensure entries require authenticated access).
*	Listing across owners: `list:*` enables listing entries beyond the session's current user. Use only when your UX requires global search/browse.

### Identify the user when you can

If your app requires authentication, set `userId` when you issue the KS. This ties server behavior and visibility to that user (e.g., lists are constrained for USER KS; ownership and visibility derive from the user in the KS, analytics are tied to the session' `userId`).

#### Analytics tracking

Specifying an app id (privilege: `appId:<APP_NAME-APP_DOMAIN>`) which contains the name and domain of the app allows you to get specific analytics per application, for cases where you’re running your application across various domains.

### Extra hardening knobs (use sparingly)

Add one or two of these when risk justifies it:

*	Action budget: `actionslimit:<N>` — cap how many API calls the KS can make.
*	IP lock: `iprestrict:<IPv4>` — restrict KS use to a single IP.
*	URI lock: `urirestrict:/api_v3/*` — restrict which API paths the KS can call.

> All three reduce blast radius if a KS leaks.
> NOTE: IP restriction works alongside CDN IP Tokenization, which requires a delivery profile configured on your account (one-time setup by your Kaltura account team).

### App-specific scoping (generic pattern)

Some applications read app-specific hints from the KS to route or filter queries (for example, an application ID or category constraints). Keep these server-parsed and use unique namespaces for each application:
For example: `genieid:<AI_GENIE_INSTANCE>`, etc. These can be read and used by the app and Kaltura backend in various contexts.

> Kaltura platform enforces only its known privileges; your app can parse and honor the custom ones as needed.

### Copy/paste privilege sets

* Authenticated playback (entitlements on): `setrole:PLAYBACK_BASE_ROLE,enableentitlement,privacycontext:PORTAL_A,sview:*`
* Single-item playback ticket: `setrole:PLAYBACK_BASE_ROLE,enableentitlement,privacycontext:PORTAL_A,sview:1_abcd1234,actionslimit:4`
* Hardened client KS (adds IP & URI restrictions): `setrole:PLAYBACK_BASE_ROLE,enableentitlement,privacycontext:PORTAL_A,sview:*,iprestrict:203.0.113.7,urirestrict:/api_v3/*`

(All examples assume a USER KS issued server-side and delivered to the client via POST body.)

> Use scoped privileges; reserve `disableentitlement` and broad write access for controlled backend ADMIN sessions.
> Issue ADMIN sessions server-side with short TTLs, and call `session.end` to revoke when done.

### Bulk logout / revocation via sessionid privilege

Set `sessionid:<GUID>` on the KS privileges and keep that GUID on your backend. To revoke an entire cohort of sessions (e.g., logout user from all devices), call `session.end` on a KS that has the same `sessionid:<GUID>` and reissue sessions with a new GUID.

`sessionid` privilege essentially groups a set of KS’s together. When `session.end` is called with a ks that has `sessionid=X`, all other KS’s that have `sessionid=X` become invalid as well.

# 11. Related Guides

- **[API Getting Started](KALTURA_API_GETTING_STARTED.md)** — API structure, first call, multirequest batching, error handling
- **[AppTokens API](KALTURA_APPTOKENS_API.md)** — Secure server-to-server auth without sharing admin secrets (HMAC-based KS generation)
- **[Upload & Ingestion](KALTURA_UPLOAD_AND_INGESTION_API.md)** — Upload content and manage entries (requires KS)
- **[Content Delivery](KALTURA_CONTENT_DELIVERY_API.md)** — Construct playback and download URLs (requires KS)
- **[eSearch](KALTURA_ESEARCH_API.md)** — Search entries, categories, users (requires KS)
- **[Player Embed](KALTURA_PLAYER_EMBED_GUIDE.md)** — Embed the player with KS for access-controlled content
- **[REACH](KALTURA_REACH_API.md)** — Enrichment services marketplace: captions, translation, moderation, AI analysis, and more (requires KS)
- **[Agents Manager](KALTURA_AGENTS_MANAGER_API.md)** — Automate workflows with triggers and actions (Bearer KS)
- **[AI Genie](KALTURA_AI_GENIE_API.md)** — Conversational AI and RAG search over video content (KS auth)
- **[Events Platform](KALTURA_EVENTS_PLATFORM_API.md)** — Virtual events with Bearer KS auth
- **[Multi-Stream](KALTURA_MULTI_STREAM_API.md)** — Dual/multi-screen entries (requires KS)
- **[App Registry](KALTURA_APP_REGISTRY_API.md)** — Register application instances (Bearer KS)
- **[User Profile](KALTURA_USER_PROFILE_API.md)** — Per-app user profiles and attendance (Bearer KS)
- **[Messaging](KALTURA_MESSAGING_API.md)** — Template-based email messaging (Bearer KS)
- **[Webhooks](KALTURA_EVENT_NOTIFICATIONS_WEBHOOK_AND_EMAIL_API.md)** — Event-driven HTTP callbacks and email notifications (requires KS)
- **[User Management API](KALTURA_USER_MANAGEMENT_API.md)** — Provision users and assign roles before creating sessions
- **[Categories & Entitlements API](KALTURA_CATEGORIES_AND_ENTITLEMENTS_API.md)** — Category entitlements and membership (related to `disableentitlement` / `enableentitlement` KS privileges)
- **[Access Control API](KALTURA_ACCESS_CONTROL_API.md)** — Access control profiles and rules for restricting content access
- **[Analytics Reports](KALTURA_ANALYTICS_REPORTS_API.md)** — `appId` privilege tags analytics per-application
- **[Custom Metadata](KALTURA_CUSTOM_METADATA_API.md)** — KS required for metadata profile management
- **[Distribution](KALTURA_DISTRIBUTION_API.md)** — Admin KS required for distribution profile management
- **[Multi-Account Management](KALTURA_MULTI_ACCOUNT_MANAGEMENT_API.md)** — `session.impersonate` for cross-account operations
- **[Experience Components](KALTURA_EXPERIENCE_COMPONENTS_API.md)** — KS passed to embedded components via config
- **[Gamification](KALTURA_GAMIFICATION_API.md)** — KS authentication for gamification microservice
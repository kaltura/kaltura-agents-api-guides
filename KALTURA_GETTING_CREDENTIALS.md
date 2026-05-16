# Kaltura API Credentials — Setup Guide

How to obtain and configure the credentials needed for all Kaltura API integrations.

**Applies to:** All Kaltura API services and embeddable components  
**Time to complete:** ~5 minutes (existing account) or ~15 minutes (new account)  
**Output:** A populated `.env` file ready for any guide in this project

<!-- Sections: 1.When to Use | 2.Get a Kaltura Account | 3.Find Your Partner ID and Admin Secret | 4.Determine Your Service URL | 5.Find Your Player ID | 6.Choose Your User ID | 7.Find Your Video Portal URL | 8.Configure Your Environment | 9.Verify Your Credentials | 10.Credential Reference | 11.Error Handling | 12.Best Practices | 13.Related Guides -->


# 1. When to Use

- **First-time developers** setting up their Kaltura API environment from scratch.
- **Development teams** onboarding new engineers to an existing Kaltura integration.
- **AI agents** that need to programmatically validate credentials before making API calls.


# 2. Get a Kaltura Account

Sign up for a Kaltura account at:

```
https://corp.kaltura.com/pricing/
```

Upon account creation, you receive:

| Credential | Description |
|-----------|-------------|
| Partner ID | Numeric account identifier |
| Admin Secret | Master API key for generating sessions |

Enterprise users with existing accounts: contact your Kaltura administrator for access.

Credentials are permanent per account. The Admin Secret is the single key used for all session generation — KS type (0 or 2) determines whether the resulting session has user-level or admin-level privileges.


# 3. Find Your Partner ID and Admin Secret

Open the KMC Integration Settings page:

```
https://kmc.kaltura.com/index.php/kmcng/settings/integrationSettings
```

Navigation path: Login to KMC → Settings → Integration.

The page displays:

| Field | Format | How to Copy |
|-------|--------|-------------|
| Partner ID | Numeric integer | Displayed directly |
| Admin Secret | 32-character string | Click the **Copy** button |

The Admin Secret has a dedicated Copy button — use it to copy the value directly to your clipboard.


# 4. Determine Your Service URL

The base API endpoint depends on your account's region:

| Region | Service URL |
|--------|------------|
| US (default) | `https://www.kaltura.com/api_v3` |
| EU | `https://www.kaltura.com/api_v3` |

To identify your region: check the domain in your KMC URL when logged in. Most accounts use the default US endpoint.

For microservice APIs (Agents Manager, AI Genie), the region code appears in the URL pattern: `https://{service}.{regionCode}.ovp.kaltura.com`


# 5. Find Your Player ID

Open the KMC Player Studio:

```
https://kmc.kaltura.com/index.php/kmcng/studio/v3
```

Each player configuration displays a numeric **ID** (also called uiConf ID) in the list. Copy the ID of the player you want to use for embedding.

If no players exist yet, create one from this studio page — the default configuration works for most use cases.


# 6. Choose Your User ID

The User ID identifies who performed each API action and who owns created content. Choose based on your use case:

| Scenario | Recommended User ID | Why |
|----------|-------------------|-----|
| Personal development | Your admin email | Content tied to your account |
| AI agent automation | `claude-code-kaltura-dev` | Identify agent-created content in reports |
| Application backend | `app-service-account` | Distinguish app actions from human actions |
| Testing | `test-automation` | Easy to filter in audit logs |

Any string works as a User ID. Choose one that helps you identify the source of actions in analytics reports and audit logs.


# 7. Find Your Video Portal URL (Optional)

Only needed for guides that interact with the Events Platform or embed portal components.

| Portal Type | Default URL Pattern |
|-------------|-------------------|
| Events Platform | `https://{PID}.events.kaltura.com` or `https://{PID}-{instance}.events.kaltura.com` |
| Content Hubs (MediaSpace) | `https://{PID}.mediaspace.kaltura.com` or `https://{PID}-{instance}.mediaspace.kaltura.com` |

The `{PID}` is your Partner ID and `{instance}` is a numeric instance identifier (e.g. `https://6500332.events.kaltura.com` or `https://6500332-1.events.kaltura.com`). Some accounts use a custom site name string instead of the PID.

The portal URL may also be a fully white-labeled custom domain (e.g. `https://video.yourcompany.com`). Find your portal URL by logging into your Kaltura site and checking the browser address bar.


# 8. Configure Your Environment

Create a `.env` file in your project root:

```bash
KALTURA_PARTNER_ID=your_partner_id
KALTURA_ADMIN_SECRET=your_admin_secret
KALTURA_SERVICE_URL=https://www.kaltura.com/api_v3
KALTURA_USER_ID=your_user_id
KALTURA_PLAYER_ID=your_player_id
KALTURA_VIDEO_PORTAL_BASE_URL=https://your-site.events.kaltura.com
```

For running curl examples directly, export as shell variables:

```bash
export KALTURA_PARTNER_ID=your_partner_id
export KALTURA_ADMIN_SECRET=your_admin_secret
export KALTURA_SERVICE_URL=https://www.kaltura.com/api_v3
export KALTURA_USER_ID=your_user_id
export KALTURA_PLAYER_ID=your_player_id
```

Add `.env` to your `.gitignore` to keep credentials out of version control.


# 9. Verify Your Credentials

Generate a Kaltura Session (KS) to confirm your credentials work:

```bash
curl -X POST "$KALTURA_SERVICE_URL/service/session/action/start" \
  -d "format=1" \
  -d "partnerId=$KALTURA_PARTNER_ID" \
  -d "secret=$KALTURA_ADMIN_SECRET" \
  -d "type=2" \
  -d "userId=$KALTURA_USER_ID"
```

A successful response returns a KS string (base64-encoded token). Save it:

```bash
export KALTURA_KS="the_returned_ks_string"
```

Verify the KS works by listing entries:

```bash
curl -X POST "$KALTURA_SERVICE_URL/service/baseEntry/action/list" \
  -d "ks=$KALTURA_KS" \
  -d "format=1" \
  -d "pager[pageSize]=1"
```

A successful response contains `"objectType": "KalturaBaseEntryListResponse"` with a `totalCount` field and an `objects` array.


# 10. Credential Reference

| Variable | Format | Source | Required |
|----------|--------|--------|----------|
| `KALTURA_PARTNER_ID` | Integer | KMC → Settings → Integration | Yes |
| `KALTURA_ADMIN_SECRET` | 32-char string | KMC → Settings → Integration (Copy button) | Yes |
| `KALTURA_SERVICE_URL` | URL | Based on account region | Yes |
| `KALTURA_USER_ID` | String | Your choice (see §6) | Yes |
| `KALTURA_PLAYER_ID` | Integer | KMC → Studio v3 | For player embeds |
| `KALTURA_VIDEO_PORTAL_BASE_URL` | URL | Your portal address bar | For portal integrations |


# 11. Error Handling

| Error Code | Meaning | Resolution |
|-----------|---------|-----------|
| `PARTNER_NOT_FOUND` | Partner ID does not exist | Verify the numeric ID from KMC Integration Settings |
| `INVALID_SECRET_TYPE` | Wrong secret or type mismatch | Confirm you copied the Admin Secret (not another value) and type matches (2=ADMIN, 0=USER) |
| `EXPIRED_KS` | Session token has expired | Generate a new KS with `session.start` |
| `INVALID_KS` | Malformed or tampered session string | Regenerate — ensure the full KS string was copied without truncation |


# 12. Best Practices

Prefer AppTokens for production applications. AppTokens provide better scoping, are revocable per-app, and eliminate the need to distribute the Admin Secret to multiple services. See **[AppTokens](KALTURA_APPTOKENS_API.md)** for implementation details.

Keep the Admin Secret exclusively on the server side. Treat it as a master key — it cannot be rotated or regenerated. Any service or person with the Admin Secret has full account access.

Store credentials in `.env` files and add `.env` to `.gitignore`. Use environment variables in all API calls rather than hardcoding values.

Use short-lived KS tokens (1-4 hours). Generate sessions on demand rather than storing long-lived tokens. AppTokens handle session renewal gracefully.

KS type determines privileges from the same Admin Secret:
- `type=2` (ADMIN) — full account management, user impersonation, content across all users
- `type=0` (USER) — scoped to the specified userId, suitable for client-side playback and user-specific operations

For organizations with multiple identity providers, the Auth Broker API integrates SSO/SAML/OIDC for end-user authentication without sharing API credentials.


# 13. Related Guides

- **[API Getting Started](KALTURA_API_GETTING_STARTED.md)** — API request structure, endpoints, multirequest batching, error handling
- **[Session Guide](KALTURA_SESSION_GUIDE.md)** — KS types, creation methods, privileges, validation, security
- **[AppTokens](KALTURA_APPTOKENS_API.md)** — Production auth without exposing secrets, HMAC-based session start, scoped per-app tokens
- **[Auth Broker (SSO)](KALTURA_AUTH_BROKER_API.md)** — Enterprise SSO/SAML/OIDC integration for organizations with multiple IdPs

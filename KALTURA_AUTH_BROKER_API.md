# Kaltura Auth Broker API

The Auth Broker is a standalone microservice for managing SSO authentication via SAML and OAuth2/OIDC identity providers. It handles IdP profile configuration, app-to-profile subscriptions, login flows, and just-in-time user provisioning — separate from the main Kaltura API v3.

**Base URL:** `https://auth.nvp1.ovp.kaltura.com/api/v1` (production NVP region)  
**Auth:** `Authorization: KS <KS>` header (KS prefix, not Bearer)  
**Format:** JSON request/response bodies, all endpoints use POST (except SAML metadata which is GET)  
**Regions:** NVP (default `nvp1`), EU (`irp2`), DE (`frp2`)  


# 1. When to Use

- **IT security teams** integrating Kaltura with enterprise SAML or OAuth2/OIDC identity providers for single sign-on  
- **Platform administrators** configuring federated authentication across multiple video portals and applications  
- **SSO rollout projects** enabling just-in-time user provisioning and group sync from IdP claims  
- **Multi-application environments** routing different apps to different identity providers via app subscriptions  
- **Compliance teams** enforcing centralized authentication policies across all Kaltura-powered properties


# 2. Prerequisites

- **KS type:** ADMIN KS (type=2) with `FEATURE_AUTH_BROKER_PERMISSION` enabled on the partner account  
- **Plugins:** Auth Broker microservice must be provisioned for your account (operates under system partner ID -17)  
- **Session guide:** Generate a KS using `session.start` or `appToken.startSession` (see [Session Guide](KALTURA_SESSION_GUIDE.md))


# 3. Authentication

All requests require a valid KS in the `Authorization` header with the `KS` prefix:

```
Authorization: KS <your_kaltura_session>
```

The `KS` prefix differs from other Kaltura microservices that use `Bearer`. The Auth Broker operates under system partner ID `-17` and requires the `FEATURE_AUTH_BROKER_PERMISSION` to be enabled on the partner account.

Generate a KS via `session.start` (see [Session Guide](KALTURA_SESSION_GUIDE.md)) or `appToken.startSession` (see [AppTokens Guide](KALTURA_APPTOKENS_API.md)).

```bash
# Set up environment
export KALTURA_AUTH_BROKER_URL="https://auth.nvp1.ovp.kaltura.com/api/v1"
```


# 4. Architecture Overview

The Auth Broker is a NestJS microservice with four service endpoints:

| Service | URL Path | Purpose |
|---------|----------|---------|
| auth-profile | `/api/v1/auth-profile/` | CRUD for SAML/OAuth2 IdP profiles |
| auth-manager | `/api/v1/auth-manager/` | Login flow, SAML/OIDC callbacks, SP metadata |
| app-subscription | `/api/v1/app-subscription/` | Subscribe apps to auth profiles |
| spa-proxy | `/api/v1/spa-proxy/` | SPA login proxy for KMC |

### Regional Endpoints

| Region | Base URL |
|--------|----------|
| NVP (default) | `https://auth.nvp1.ovp.kaltura.com/api/v1` |
| EU | `https://auth.irp2.ovp.kaltura.com/api/v1` |
| DE | `https://auth.frp2.ovp.kaltura.com/api/v1` |

Use the region that matches your Kaltura account deployment.

### Relationship to App Registry

The Auth Broker uses `appGuid` values from the [App Registry API](KALTURA_APP_REGISTRY_API.md) to link SSO profiles to specific application instances. Each app subscription references an `appGuid` and one or more `authProfileIds`, creating the bridge between "which app" and "which IdP handles login."


# 5. Auth Profile CRUD

Auth profiles define the connection to an identity provider (SAML or OAuth2/OIDC). Actions: `add`, `get`, `list`, `update`, `delete`, `generatePvKeys`.

## 5.1 Auth Profile Object

| Field | Type | Description |
|-------|------|-------------|
| `id` | string | Auto-generated MongoDB ObjectId (read-only) |
| `objectType` | string | Always `"AuthProfile"` (read-only) |
| `partnerId` | integer | Partner ID from KS (read-only) |
| `name` | string | Display name for the profile |
| `description` | string | Profile description |
| `providerType` | string | Identity provider type (see enum below) |
| `authStrategy` | string | `saml` or `oauth2` |
| `isAdminProfile` | boolean | Whether this profile is for admin users |
| `createNewUser` | boolean | Enable JIT user provisioning |
| `createNewGroups` | boolean | Auto-create groups from IdP claims |
| `removeFromExistingGroups` | boolean | Remove user from groups not in IdP claims |
| `userGroupsSyncAll` | boolean | Sync all groups from IdP (overrides mapping) |
| `userIdAttribute` | string | IdP attribute used as Kaltura user ID |
| `authStrategyConfig` | object | IdP-specific configuration (see section 5.2) |
| `userAttributeMappings` | object | Map IdP attributes to Kaltura user fields (see section 6) |
| `userGroupMappings` | object | Map IdP group claims to Kaltura groups (see section 7) |
| `ksPrivileges` | string | Additional KS privileges for authenticated users |
| `syncDelayTimeoutMin` | integer | Minutes to wait before syncing groups |
| `version` | integer | Auto-incrementing version (read-only) |
| `status` | string | `enabled` or `disabled` |
| `createdAt` | string | ISO 8601 timestamp (read-only) |
| `updatedAt` | string | ISO 8601 timestamp (read-only) |

### Provider Types

| Value | Description |
|-------|-------------|
| `azure` | Microsoft Azure AD / Entra ID |
| `okta` | Okta |
| `aws` | AWS IAM Identity Center (SSO) |
| `akamai` | Akamai Identity Cloud |
| `other` | Any other SAML/OAuth2 IdP |

### Auth Strategies

| Value | Description |
|-------|-------------|
| `saml` | SAML 2.0 SSO |
| `oauth2` | OAuth2 / OpenID Connect |

## 5.2 Auth Strategy Config (SAML)

The `authStrategyConfig` object for SAML profiles:

| Field | Type | Description |
|-------|------|-------------|
| `issuer` | string | SP entity ID / issuer name |
| `entryPoint` | string | IdP SSO URL (where SAML requests are sent) |
| `callbackUrl` | string | ACS URL — set to `https://auth.{region}.ovp.kaltura.com/api/v1/auth-manager/saml/ac` |
| `logoutUrl` | string | IdP Single Logout URL |
| `logoutCallbackUrl` | string | SP logout callback — set to `https://auth.{region}.ovp.kaltura.com/api/v1/auth-manager/saml/logout` |
| `cert` | string | IdP signing certificate (PEM, without headers) |
| `validateInResponseTo` | boolean | Validate SAML `InResponseTo` attribute |
| `digestAlgorithm` | string | `sha1` or `sha256` |
| `signatureAlgorithm` | string | `sha1` or `sha256` |
| `enableRequestSign` | boolean | Sign SAML authentication requests |
| `enableAssertsDecryption` | boolean | Decrypt encrypted SAML assertions |
| `disableRequestedAuthnContext` | boolean | Omit `RequestedAuthnContext` from SAML request |
| `requestIdExpirationPeriodMs` | integer | Request ID expiration in milliseconds (default: 28800000 = 8 hours) |

## 5.2b Auth Strategy Config (OAuth2/OIDC)

The `authStrategyConfig` object for OAuth2/OIDC profiles:

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `clientId` | string | Yes | OAuth2 client ID registered with the IdP |
| `clientSecret` | string | Yes | OAuth2 client secret from the IdP |
| `authorizationURL` | string | Yes | IdP authorization endpoint URL (where the browser is redirected to authenticate) |
| `tokenURL` | string | Yes | IdP token endpoint URL (used by the Auth Broker to exchange the authorization code for tokens) |
| `callbackUrl` | string | Yes | OAuth2/OIDC callback URL — set to `https://auth.{region}.ovp.kaltura.com/api/v1/auth-manager/oidc/ac` |
| `scope` | string | Yes | OAuth2 scopes to request (e.g., `"openid profile email"`) |
| `userInfoURL` | string | No | IdP userinfo endpoint URL (for fetching user attributes if not included in the ID token) |
| `logoutUrl` | string | No | IdP logout endpoint URL for single logout |
| `logoutCallbackUrl` | string | No | SP logout callback URL |
| `responseType` | string | No | OAuth2 response type (default: `"code"` for authorization code flow) |
| `issuer` | string | No | Expected token issuer for validation (e.g., `https://login.microsoftonline.com/{tenant}/v2.0`) |

### Example: Azure AD OAuth2/OIDC Profile

```bash
curl -X POST "$KALTURA_AUTH_BROKER_URL/auth-profile/add" \
  -H "Authorization: KS $KALTURA_KS" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Azure AD OIDC - Employees",
    "description": "OAuth2/OIDC SSO via Azure AD",
    "providerType": "azure",
    "authStrategy": "oauth2",
    "isAdminProfile": false,
    "createNewUser": true,
    "createNewGroups": true,
    "removeFromExistingGroups": false,
    "userGroupsSyncAll": false,
    "userIdAttribute": "email",
    "authStrategyConfig": {
      "clientId": "YOUR_AZURE_APP_CLIENT_ID",
      "clientSecret": "YOUR_AZURE_APP_CLIENT_SECRET",
      "authorizationURL": "https://login.microsoftonline.com/YOUR_TENANT_ID/oauth2/v2.0/authorize",
      "tokenURL": "https://login.microsoftonline.com/YOUR_TENANT_ID/oauth2/v2.0/token",
      "callbackUrl": "https://auth.nvp1.ovp.kaltura.com/api/v1/auth-manager/oidc/ac",
      "scope": "openid profile email",
      "userInfoURL": "https://graph.microsoft.com/oidc/userinfo",
      "issuer": "https://login.microsoftonline.com/YOUR_TENANT_ID/v2.0"
    },
    "userAttributeMappings": {
      "firstName": "given_name",
      "lastName": "family_name",
      "email": "email"
    },
    "userGroupMappings": {},
    "ksPrivileges": ""
  }'
```

### Example: Okta OAuth2/OIDC Profile

```bash
curl -X POST "$KALTURA_AUTH_BROKER_URL/auth-profile/add" \
  -H "Authorization: KS $KALTURA_KS" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Okta OIDC - Contractors",
    "description": "OAuth2/OIDC SSO via Okta",
    "providerType": "okta",
    "authStrategy": "oauth2",
    "createNewUser": true,
    "userIdAttribute": "email",
    "authStrategyConfig": {
      "clientId": "YOUR_OKTA_CLIENT_ID",
      "clientSecret": "YOUR_OKTA_CLIENT_SECRET",
      "authorizationURL": "https://YOUR_ORG.okta.com/oauth2/default/v1/authorize",
      "tokenURL": "https://YOUR_ORG.okta.com/oauth2/default/v1/token",
      "callbackUrl": "https://auth.nvp1.ovp.kaltura.com/api/v1/auth-manager/oidc/ac",
      "scope": "openid profile email groups",
      "userInfoURL": "https://YOUR_ORG.okta.com/oauth2/default/v1/userinfo",
      "issuer": "https://YOUR_ORG.okta.com/oauth2/default"
    },
    "userAttributeMappings": {
      "firstName": "given_name",
      "lastName": "family_name",
      "email": "email"
    },
    "userGroupMappings": {},
    "ksPrivileges": ""
  }'
```

### OAuth2/OIDC Attribute Names

When using OAuth2/OIDC, attribute names come from the ID token claims or userinfo endpoint response (standard OIDC claim names):

| Kaltura Field | OIDC Claim |
|---------------|-----------|
| `firstName` | `given_name` |
| `lastName` | `family_name` |
| `email` | `email` |

The `userIdAttribute` for OIDC profiles is typically `"email"` (the standard OIDC email claim). For Azure AD, `"preferred_username"` or `"email"` can also be used.

### SAML vs OAuth2/OIDC Comparison

| Aspect | SAML | OAuth2/OIDC |
|--------|------|-------------|
| Callback URL | `/auth-manager/saml/ac` | `/auth-manager/oidc/ac` |
| SP Metadata | Available via GET endpoint (section 11) | Not applicable (use client ID/secret registration) |
| Request Signing | Optional via `enableRequestSign` + `generatePvKeys` | Not applicable (uses client secret) |
| Assertion Decryption | Optional via `enableAssertsDecryption` | Not applicable (token-based) |
| IdP Setup | Upload SP metadata XML to IdP | Register callback URL and scopes in IdP OAuth2 app settings |
| Group Claims | Via SAML attribute assertions | Via OIDC `groups` scope and token claims |

> OAuth2/OIDC profiles require the IdP to support the authorization code flow. The Auth Broker exchanges the authorization code for tokens server-side, keeping the client secret secure. The `callbackUrl` must be registered as a valid redirect URI in the IdP's OAuth2 application configuration.

## 5.3 Add an Auth Profile

```
POST /api/v1/auth-profile/add
Content-Type: application/json
Authorization: KS <KS>
```

```bash
curl -X POST "$KALTURA_AUTH_BROKER_URL/auth-profile/add" \
  -H "Authorization: KS $KALTURA_KS" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Corporate Okta SSO",
    "description": "SAML SSO via Okta for all employees",
    "providerType": "okta",
    "authStrategy": "saml",
    "isAdminProfile": false,
    "createNewUser": true,
    "createNewGroups": true,
    "removeFromExistingGroups": false,
    "userGroupsSyncAll": false,
    "userIdAttribute": "Core_User_Email",
    "authStrategyConfig": {
      "issuer": "kaltura-sso-production",
      "entryPoint": "https://your-org.okta.com/app/APPID/sso/saml",
      "callbackUrl": "https://auth.nvp1.ovp.kaltura.com/api/v1/auth-manager/saml/ac",
      "logoutUrl": "https://your-org.okta.com/app/APPID/slo/saml",
      "logoutCallbackUrl": "https://auth.nvp1.ovp.kaltura.com/api/v1/auth-manager/saml/logout",
      "cert": "MIIDnj...(IdP certificate, base64 encoded)...",
      "validateInResponseTo": false,
      "digestAlgorithm": "sha1",
      "signatureAlgorithm": "sha1",
      "enableRequestSign": false,
      "enableAssertsDecryption": false,
      "disableRequestedAuthnContext": true,
      "requestIdExpirationPeriodMs": 28800000
    },
    "userAttributeMappings": {
      "firstName": "Core_User_FirstName",
      "lastName": "Core_User_LastName",
      "email": "Core_User_Email"
    },
    "userGroupMappings": {},
    "ksPrivileges": "",
    "syncDelayTimeoutMin": 5
  }'
```

**Request body parameters:**

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `name` | string | Yes | Display name for the profile |
| `providerType` | string | Yes | IdP provider: `azure`, `okta`, `aws`, `akamai`, `other` |
| `authStrategy` | string | Yes | `saml` or `oauth2` |
| `authStrategyConfig` | object | Yes | IdP connection settings (see section 5.2 for SAML, 5.2b for OAuth2/OIDC) |
| `userIdAttribute` | string | Yes | IdP attribute used as Kaltura user ID |
| `userAttributeMappings` | object | Yes | Map IdP attributes to Kaltura user fields (see section 6) |
| `userGroupMappings` | object | Yes | Map IdP groups to Kaltura groups (required even if empty `{}`) |
| `description` | string | No | Profile description |
| `isAdminProfile` | boolean | No | Whether this profile is for admin users (default: `false`) |
| `createNewUser` | boolean | No | Enable JIT user provisioning (default: `false`) |
| `createNewGroups` | boolean | No | Auto-create groups from IdP claims (default: `false`) |
| `removeFromExistingGroups` | boolean | No | Remove user from groups not in IdP claims (default: `false`) |
| `userGroupsSyncAll` | boolean | No | Sync all groups from IdP (default: `false`) |
| `ksPrivileges` | string | No | Additional KS privileges for authenticated users |
| `syncDelayTimeoutMin` | integer | No | Minutes to delay group sync after login |

Save the `id` from the response as `AUTH_PROFILE_ID`.

The `userGroupMappings` field is required even when empty. Omitting it results in a `USER_GROUPS_SYNC_ALL_FALSE_AND_GROUPS_MISSING` error when `userGroupsSyncAll` is `false`.

## 5.4 Get an Auth Profile

```
POST /api/v1/auth-profile/get
Content-Type: application/json
Authorization: KS <KS>
```

```bash
curl -X POST "$KALTURA_AUTH_BROKER_URL/auth-profile/get" \
  -H "Authorization: KS $KALTURA_KS" \
  -H "Content-Type: application/json" \
  -d "{\"id\": \"$AUTH_PROFILE_ID\"}"
```

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `id` | string | Yes | Auth profile ID (MongoDB ObjectId from the `add` response) |

**Response:** Full auth profile object.

## 5.5 List Auth Profiles

```
POST /api/v1/auth-profile/list
Content-Type: application/json
Authorization: KS <KS>
```

```bash
curl -X POST "$KALTURA_AUTH_BROKER_URL/auth-profile/list" \
  -H "Authorization: KS $KALTURA_KS" \
  -H "Content-Type: application/json" \
  -d '{
    "filter": {},
    "pager": {"offset": 0, "limit": 25}
  }'
```

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `filter` | object | No | Filter criteria (empty `{}` returns all profiles for the partner) |
| `filter.providerType` | string | No | Filter by provider type (`azure`, `okta`, `aws`, `akamai`, `other`) |
| `filter.authStrategy` | string | No | Filter by auth strategy (`saml` or `oauth2`) |
| `filter.status` | string | No | Filter by status (`enabled` or `disabled`) |
| `pager` | object | No | Pagination settings |
| `pager.offset` | integer | No | Number of records to skip (default: 0) |
| `pager.limit` | integer | No | Maximum records to return (default: 25) |

**Response:** `{ "objects": [...], "totalCount": N }` containing auth profile objects.

## 5.6 Update an Auth Profile

```
POST /api/v1/auth-profile/update
Content-Type: application/json
Authorization: KS <KS>
```

```bash
curl -X POST "$KALTURA_AUTH_BROKER_URL/auth-profile/update" \
  -H "Authorization: KS $KALTURA_KS" \
  -H "Content-Type: application/json" \
  -d "{
    \"id\": \"$AUTH_PROFILE_ID\",
    \"name\": \"Updated Okta SSO Profile\",
    \"createNewUser\": true
  }"
```

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `id` | string | Yes | Auth profile ID to update |
| (any writable field) | varies | No | Any field from the auth profile object (section 5.1) except read-only fields (`objectType`, `partnerId`, `version`, `createdAt`, `updatedAt`) |

Fields not included in the request remain unchanged. The `version` increments on each successful update.

## 5.7 Delete an Auth Profile

```
POST /api/v1/auth-profile/delete
Content-Type: application/json
Authorization: KS <KS>
```

```bash
curl -X POST "$KALTURA_AUTH_BROKER_URL/auth-profile/delete" \
  -H "Authorization: KS $KALTURA_KS" \
  -H "Content-Type: application/json" \
  -d "{\"id\": \"$AUTH_PROFILE_ID\"}"
```

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `id` | string | Yes | Auth profile ID to delete |

Remove all app subscriptions referencing this profile before deleting it.

## 5.8 Generate Private/Public Keys

Generate a key pair for SAML request signing or assertion decryption:

```bash
curl -X POST "$KALTURA_AUTH_BROKER_URL/auth-profile/generatePvKeys" \
  -H "Authorization: KS $KALTURA_KS" \
  -H "Content-Type: application/json" \
  -d "{\"id\": \"$AUTH_PROFILE_ID\"}"
```

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `id` | string | Yes | Auth profile ID to generate keys for |

Use this when `enableRequestSign` or `enableAssertsDecryption` is set to `true`. The generated public key is included in the SP metadata (see section 11). This action is only applicable to SAML auth profiles.


# 6. Attribute Mapping

The `userAttributeMappings` object maps IdP assertion attributes to Kaltura user fields. When a user authenticates via SSO, the Auth Broker reads the IdP response attributes and sets the corresponding Kaltura user fields.

| Kaltura Field | Description | Example IdP Attribute |
|---------------|-------------|----------------------|
| `firstName` | User's first name | `Core_User_FirstName` |
| `lastName` | User's last name | `Core_User_LastName` |
| `email` | User's email address | `Core_User_Email` |

```json
{
  "userAttributeMappings": {
    "firstName": "Core_User_FirstName",
    "lastName": "Core_User_LastName",
    "email": "Core_User_Email"
  }
}
```

The `userIdAttribute` field (top-level on the auth profile) specifies which IdP attribute is used as the Kaltura `userId`. This is typically the email attribute (e.g., `Core_User_Email`). The value from this attribute becomes the user's `externalId` in the Kaltura user record.

### Azure AD / Entra ID Attribute Names

| Kaltura Field | Azure AD Attribute |
|---------------|-------------------|
| `firstName` | `http://schemas.xmlsoap.org/ws/2005/05/identity/claims/givenname` |
| `lastName` | `http://schemas.xmlsoap.org/ws/2005/05/identity/claims/surname` |
| `email` | `http://schemas.xmlsoap.org/ws/2005/05/identity/claims/emailaddress` |

### Okta Attribute Names (SAML)

| Kaltura Field | Okta Attribute |
|---------------|---------------|
| `firstName` | `Core_User_FirstName` |
| `lastName` | `Core_User_LastName` |
| `email` | `Core_User_Email` |

### OAuth2/OIDC Standard Claim Names

When using `authStrategy: "oauth2"`, attribute names come from standard OIDC claims (ID token or userinfo response):

| Kaltura Field | OIDC Claim | Description |
|---------------|-----------|-------------|
| `firstName` | `given_name` | User's first name |
| `lastName` | `family_name` | User's last name |
| `email` | `email` | User's email address |

These claim names are consistent across Azure AD, Okta, and other OIDC-compliant providers. The `userIdAttribute` for OIDC profiles is typically `"email"` or `"preferred_username"`.


# 7. Group Sync

The Auth Broker can synchronize user group memberships from IdP claims to Kaltura groups using the `groupUser.sync` mechanism.

## 7.1 Configuration Fields

| Field | Type | Description |
|-------|------|-------------|
| `createNewGroups` | boolean | Auto-create Kaltura groups from IdP claims if they do not exist |
| `removeFromExistingGroups` | boolean | Remove user from Kaltura groups not present in IdP claims |
| `userGroupsSyncAll` | boolean | Sync all groups from the IdP group attribute (ignores `userGroupMappings`) |
| `userGroupMappings` | object | Map specific IdP group names to Kaltura group IDs |
| `syncDelayTimeoutMin` | integer | Minutes to delay group sync after login (allows batch processing) |

## 7.2 Group Mapping Modes

**Sync all groups** (`userGroupsSyncAll: true`): Every group from the IdP group attribute is synced to Kaltura. The `userGroupMappings` field is ignored.

**Map specific groups** (`userGroupsSyncAll: false`): Only groups listed in `userGroupMappings` are synced. The mapping translates IdP group names to Kaltura group IDs:

```json
{
  "userGroupsSyncAll": false,
  "userGroupMappings": {
    "IdP_Engineering_Team": "kaltura_engineering",
    "IdP_Marketing_Team": "kaltura_marketing"
  }
}
```

When `userGroupsSyncAll` is `false`, the `userGroupMappings` field is required (even if empty `{}`). Omitting it triggers the `USER_GROUPS_SYNC_ALL_FALSE_AND_GROUPS_MISSING` error.

## 7.3 Group Removal

When `removeFromExistingGroups` is `true`, users are removed from any Kaltura groups that are not present in the current IdP assertion. This ensures Kaltura group membership stays in sync with IdP state. When `false`, groups are only added — users keep existing Kaltura group memberships even if removed from the IdP group.


# 8. App Subscription CRUD

App subscriptions link registered applications (from the [App Registry](KALTURA_APP_REGISTRY_API.md)) to auth profiles, defining which IdP handles login for each app. Actions: `add`, `get`, `list`, `update`, `delete`.

## 8.1 App Subscription Object

| Field | Type | Description |
|-------|------|-------------|
| `id` | string | Auto-generated ID (read-only) |
| `objectType` | string | Always `"AppSubscription"` (read-only) |
| `partnerId` | integer | Partner ID from KS (read-only) |
| `name` | string | Subscription display name |
| `appGuid` | string | App GUID from the App Registry |
| `authProfileIds` | string[] | Array of auth profile IDs to use for this app |
| `status` | string | `enabled` or `disabled` |
| `version` | integer | Auto-incrementing version (read-only) |
| `appLandingPage` | string | URL to redirect after successful login (receives KS + JWT) |
| `appErrorPage` | string | URL to redirect on authentication error |
| `redirectMethod` | string | `HTTP-POST` or `HTTP-GET` — how to deliver credentials to landing page |
| `ksPrivileges` | string | KS privileges for sessions created through this subscription |
| `permissionList` | array | Permission list for fine-grained access control |
| `permissionListStatus` | string | `none`, `whitelist`, or `blacklist` |
| `attributePermissionListStatus` | string | `none`, `whitelist`, or `blacklist` |
| `userGroupsSyncAll` | boolean | Override profile-level group sync for this subscription |
| `createdAt` | string | ISO 8601 timestamp (read-only) |
| `updatedAt` | string | ISO 8601 timestamp (read-only) |

### Redirect Methods

| Value | Description |
|-------|-------------|
| `HTTP-POST` | Credentials sent as form POST body to landing page (more secure, prevents URL leakage) |
| `HTTP-GET` | Credentials appended as URL query parameters |

## 8.2 Add an App Subscription

```
POST /api/v1/app-subscription/add
Content-Type: application/json
Authorization: KS <KS>
```

```bash
curl -X POST "$KALTURA_AUTH_BROKER_URL/app-subscription/add" \
  -H "Authorization: KS $KALTURA_KS" \
  -H "Content-Type: application/json" \
  -d "{
    \"name\": \"Events Portal SSO\",
    \"appGuid\": \"$APP_GUID\",
    \"authProfileIds\": [\"$AUTH_PROFILE_ID\"],
    \"appLandingPage\": \"https://events.example.com/user/authenticate\",
    \"appErrorPage\": \"https://events.example.com/user/authenticate\",
    \"redirectMethod\": \"HTTP-POST\",
    \"ksPrivileges\": \"kmslogin\"
  }"
```

**Request body parameters:**

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `name` | string | Yes | Subscription display name |
| `appGuid` | string | Yes | App GUID from the [App Registry](KALTURA_APP_REGISTRY_API.md) |
| `authProfileIds` | string[] | Yes | Array of auth profile IDs to use for this app |
| `appLandingPage` | string | Yes | URL to redirect after successful login (receives KS + JWT) |
| `appErrorPage` | string | Yes | URL to redirect on authentication error |
| `redirectMethod` | string | No | `HTTP-POST` (default) or `HTTP-GET` — how to deliver credentials to landing page |
| `ksPrivileges` | string | No | KS privileges for sessions created through this subscription |
| `permissionList` | array | No | Permission list for fine-grained access control |
| `permissionListStatus` | string | No | `none` (default), `whitelist`, or `blacklist` |
| `attributePermissionListStatus` | string | No | `none` (default), `whitelist`, or `blacklist` |
| `userGroupsSyncAll` | boolean | No | Override profile-level group sync for this subscription |

Save the `id` from the response as `APP_SUBSCRIPTION_ID`. The `appGuid` must reference an existing, enabled app in the [App Registry](KALTURA_APP_REGISTRY_API.md).

## 8.3 Get an App Subscription

```bash
curl -X POST "$KALTURA_AUTH_BROKER_URL/app-subscription/get" \
  -H "Authorization: KS $KALTURA_KS" \
  -H "Content-Type: application/json" \
  -d "{\"id\": \"$APP_SUBSCRIPTION_ID\"}"
```

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `id` | string | Yes | App subscription ID |

**Response:** Full app subscription object.

## 8.4 List App Subscriptions

```bash
curl -X POST "$KALTURA_AUTH_BROKER_URL/app-subscription/list" \
  -H "Authorization: KS $KALTURA_KS" \
  -H "Content-Type: application/json" \
  -d '{
    "filter": {},
    "pager": {"offset": 0, "limit": 25}
  }'
```

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `filter` | object | No | Filter criteria (empty `{}` returns all subscriptions for the partner) |
| `filter.appGuid` | string | No | Filter by app GUID |
| `filter.status` | string | No | Filter by status (`enabled` or `disabled`) |
| `pager` | object | No | Pagination settings |
| `pager.offset` | integer | No | Number of records to skip (default: 0) |
| `pager.limit` | integer | No | Maximum records to return (default: 25) |

**Response:** `{ "objects": [...], "totalCount": N }` containing app subscription objects.

## 8.5 Update an App Subscription

```bash
curl -X POST "$KALTURA_AUTH_BROKER_URL/app-subscription/update" \
  -H "Authorization: KS $KALTURA_KS" \
  -H "Content-Type: application/json" \
  -d "{
    \"id\": \"$APP_SUBSCRIPTION_ID\",
    \"appLandingPage\": \"https://events.example.com/sso-redirect\",
    \"redirectMethod\": \"HTTP-GET\"
  }"
```

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `id` | string | Yes | App subscription ID to update |
| (any writable field) | varies | No | Any field from the app subscription object (section 8.1) except read-only fields (`objectType`, `partnerId`, `version`, `createdAt`, `updatedAt`) |

Fields not included in the request remain unchanged. The `version` increments on each successful update.

## 8.6 Delete an App Subscription

```bash
curl -X POST "$KALTURA_AUTH_BROKER_URL/app-subscription/delete" \
  -H "Authorization: KS $KALTURA_KS" \
  -H "Content-Type: application/json" \
  -d "{\"id\": \"$APP_SUBSCRIPTION_ID\"}"
```

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `id` | string | Yes | App subscription ID to delete |


# 9. SSO Login Flow

The complete SSO login sequence involves generating a token, redirecting to the IdP, and processing the callback.

## 9.1 Flow Sequence

**SAML flow:**

```
1. App calls generateAuthBrokerToken with {appGuid, authProfileId, origURL}
2. Auth Broker returns an encrypted token
3. App POSTs the token to /auth-manager/login
4. Auth Broker responds with 302 redirect to the IdP SAML SSO URL
5. User authenticates at the IdP
6. IdP POSTs SAML assertion to /auth-manager/saml/ac
7. Auth Broker validates the SAML assertion, extracts attributes
8. Auth Broker creates or updates the Kaltura user (JIT provisioning)
9. Auth Broker syncs group memberships from IdP claims
10. Auth Broker generates a KS and signs a JWT
11. Auth Broker redirects to appLandingPage with KS and JWT
```

**OAuth2/OIDC flow:**

```
1. App calls generateAuthBrokerToken with {appGuid, authProfileId, origURL}
2. Auth Broker returns an encrypted token
3. App POSTs the token to /auth-manager/login
4. Auth Broker responds with 302 redirect to the IdP authorization URL (with client_id, scope, redirect_uri)
5. User authenticates at the IdP and grants consent
6. IdP redirects to /auth-manager/oidc/ac with an authorization code
7. Auth Broker exchanges the code for access token + ID token at the IdP token URL
8. Auth Broker extracts user attributes from the ID token (or calls the userinfo endpoint)
9. Auth Broker creates or updates the Kaltura user (JIT provisioning)
10. Auth Broker syncs group memberships from token claims
11. Auth Broker generates a KS and signs a JWT
12. Auth Broker redirects to appLandingPage with KS and JWT
```

## 9.2 Generate Auth Broker Token

```
POST /api/v1/auth-manager/generateAuthBrokerToken
Content-Type: application/json
Authorization: KS <KS>
```

```bash
curl -X POST "$KALTURA_AUTH_BROKER_URL/auth-manager/generateAuthBrokerToken" \
  -H "Authorization: KS $KALTURA_KS" \
  -H "Content-Type: application/json" \
  -d "{
    \"appGuid\": \"$APP_GUID\",
    \"authProfileId\": \"$AUTH_PROFILE_ID\",
    \"origURL\": \"https://events.example.com/dashboard\"
  }"
```

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `appGuid` | string | Yes | App GUID from App Registry |
| `authProfileId` | string | Yes | Auth profile ID to use for login |
| `origURL` | string | Yes | URL to redirect back to after login |

**Response:** An encrypted token string.

## 9.3 Start Login

```
POST /api/v1/auth-manager/login
Content-Type: application/json
Authorization: KS <KS>
```

```bash
curl -X POST "$KALTURA_AUTH_BROKER_URL/auth-manager/login" \
  -H "Authorization: KS $KALTURA_KS" \
  -H "Content-Type: application/json" \
  -d "{\"token\": \"$ENCRYPTED_TOKEN\"}"
```

**Response:** HTTP 302 redirect to the IdP login page. The browser follows this redirect automatically.

## 9.4 Callback Endpoints

After the user authenticates at the IdP, the IdP sends the response to one of these callback URLs:

| Protocol | Callback URL | HTTP Method |
|----------|-------------|-------------|
| SAML | `/api/v1/auth-manager/saml/ac` | POST |
| OIDC | `/api/v1/auth-manager/oidc/ac` | GET or POST |
| OAuth2 | `/api/v1/auth-manager/oauth2/ac` | GET |

These callbacks are configured in the IdP and must match the `callbackUrl` in the auth profile's `authStrategyConfig`. The Auth Broker processes the callback, provisions the user, and redirects to the `appLandingPage` with credentials.


# 10. SPA Proxy

The SPA Proxy provides a login entry point for single-page applications like KMC that need to discover the correct auth profile and redirect flow.

```
POST /api/v1/spa-proxy/login
Content-Type: application/json
Authorization: KS <KS>
```

```bash
curl -X POST "$KALTURA_AUTH_BROKER_URL/spa-proxy/login" \
  -H "Authorization: KS $KALTURA_KS" \
  -H "Content-Type: application/json" \
  -d '{
    "appType": "kmc",
    "email": "user@example.com"
  }'
```

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `appType` | string | Yes | Application type (e.g., `kmc`, `kms`) |
| `email` | string | Yes | User email for IdP discovery |
| `organizationId` | string | No | Organization ID for multi-tenant setups |
| `authProfileId` | string | No | Specific auth profile to use (skips discovery) |

The SPA Proxy resolves the correct auth profile based on the email domain and app type, then initiates the login flow.

### Per-App Integration Patterns

| Application | Login Method | Landing Page |
|-------------|-------------|--------------|
| MediaSpace (KMS) | `generateAuthBrokerToken` | `/user/authenticate` |
| KMC | `sso.login` with fallback to `spa-proxy/login` | `/index.php/kmcng/actions/persist-login-by-ks` |
| Events Platform | Template-based auth profiles | `{epServer}/sso-redirect` |


# 11. SAML SP Metadata

Retrieve the SAML Service Provider metadata XML for a specific auth profile. This metadata is provided to the IdP during SSO setup.

```
GET /api/v1/auth-manager/saml/metadata/{partnerId}/{profileId}
```

```bash
curl -X GET "$KALTURA_AUTH_BROKER_URL/auth-manager/saml/metadata/$PARTNER_ID/$AUTH_PROFILE_ID"
```

**Response:** XML document containing the SP entity ID, ACS URL, logout URL, and (if generated) the SP signing/encryption certificate. Provide this metadata URL or download the XML file and upload it to your IdP configuration.


# 12. Multi-SSO Configuration

A partner can configure multiple identity providers and control how they are selected per application. This is useful when different user populations authenticate through different IdPs (e.g., employees via Azure AD, contractors via Okta).

## 12.1 Multiple Auth Profiles per Partner

Each call to `auth-profile/add` creates an independent IdP configuration. A single partner can have any number of auth profiles — one per identity provider or per authentication strategy:

```bash
# Create an Azure AD profile
curl -X POST "$KALTURA_AUTH_BROKER_URL/auth-profile/add" \
  -H "Authorization: KS $KALTURA_KS" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Azure AD - Employees",
    "providerType": "azure",
    "authStrategy": "saml",
    "createNewUser": true,
    "userIdAttribute": "http://schemas.xmlsoap.org/ws/2005/05/identity/claims/emailaddress",
    "authStrategyConfig": { ... },
    "userAttributeMappings": { ... },
    "userGroupMappings": {}
  }'
# Save response id as AZURE_PROFILE_ID

# Create an Okta profile
curl -X POST "$KALTURA_AUTH_BROKER_URL/auth-profile/add" \
  -H "Authorization: KS $KALTURA_KS" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Okta - Contractors",
    "providerType": "okta",
    "authStrategy": "saml",
    "createNewUser": true,
    "userIdAttribute": "Core_User_Email",
    "authStrategyConfig": { ... },
    "userAttributeMappings": { ... },
    "userGroupMappings": {}
  }'
# Save response id as OKTA_PROFILE_ID
```

Each profile has its own IdP connection settings, attribute mappings, group sync rules, and JIT provisioning behavior.

## 12.2 App-Level Profile Selection

An app subscription can reference multiple auth profiles via the `authProfileIds` array. When a login flow is initiated for that app, the system uses the `authProfileId` parameter in `generateAuthBrokerToken` to route the user to a specific IdP:

```bash
curl -X POST "$KALTURA_AUTH_BROKER_URL/app-subscription/add" \
  -H "Authorization: KS $KALTURA_KS" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Multi-SSO App",
    "appGuid": "'$APP_GUID'",
    "authProfileIds": ["'$AZURE_PROFILE_ID'", "'$OKTA_PROFILE_ID'"],
    "appLandingPage": "https://myapp.example.com/auth/callback",
    "appErrorPage": "https://myapp.example.com/auth/error",
    "ksPrivileges": "kmslogin"
  }'
```

When calling `generateAuthBrokerToken`, specify which profile to use:

```bash
# Route to Azure AD
curl -X POST "$KALTURA_AUTH_BROKER_URL/auth-manager/generateAuthBrokerToken" \
  -H "Authorization: KS $KALTURA_KS" \
  -H "Content-Type: application/json" \
  -d "{
    \"appGuid\": \"$APP_GUID\",
    \"authProfileId\": \"$AZURE_PROFILE_ID\",
    \"origURL\": \"https://myapp.example.com/dashboard\"
  }"
```

The specified `authProfileId` must be listed in the subscription's `authProfileIds` array.

## 12.3 Per-Subscription Overrides

Each app subscription can override `ksPrivileges` from the auth profile, allowing the same IdP profile to produce different session privileges per application. The `userIdAttribute` on the auth profile determines user identity, but the subscription's `ksPrivileges` controls what the resulting KS can access:

| Field | Auth Profile Level | App Subscription Level | Behavior |
|-------|-------------------|----------------------|----------|
| `ksPrivileges` | Default privileges for all apps | Override for this specific app | Subscription value takes precedence when set |
| `userGroupsSyncAll` | Default group sync mode | Override for this specific app | Subscription value takes precedence when set |

This allows a single Azure AD profile to grant `kmslogin` privileges for a MediaSpace subscription and different privileges for an Events Platform subscription, without duplicating the IdP configuration.

## 12.4 Organization-Based Routing

For `spa-proxy/login`, when no `authProfileId` is specified, the system can route users to the correct IdP based on `organizationId`:

```bash
curl -X POST "$KALTURA_AUTH_BROKER_URL/spa-proxy/login" \
  -H "Authorization: KS $KALTURA_KS" \
  -H "Content-Type: application/json" \
  -d '{
    "appType": "kmc",
    "email": "user@example.com",
    "organizationId": "org-acme-corp"
  }'
```

The `organizationId` enables domain-based IdP discovery: the system resolves which auth profile is associated with the organization and initiates the login flow with that IdP. This is useful in multi-tenant setups where different organizations within the same partner account use different identity providers.


# 13. Shared User Model

The Auth Broker integrates with the core Kaltura user system through the `externalId` field on the `KalturaUser` object.

## 13.1 External ID Linking

When a user authenticates via SSO, the Auth Broker sets the `externalId` on the Kaltura user record to the value of the `userIdAttribute` from the IdP assertion. This `externalId` is the key for all subsequent SSO lookups — if the user logs in again, the Auth Broker finds the existing Kaltura user by `externalId`.

## 13.2 JIT User Provisioning

When `createNewUser` is `true` on the auth profile, the Auth Broker automatically creates a new Kaltura user if no user with the matching `externalId` exists. The user's `firstName`, `lastName`, and `email` are populated from the `userAttributeMappings`.

When `createNewUser` is `false`, users must already exist in Kaltura — SSO login fails for unknown users.

## 13.3 Group Sync via groupUser

After user provisioning, the Auth Broker calls the `groupUser.sync` API to update group memberships based on IdP claims. This uses the `userGroupMappings` or `userGroupsSyncAll` configuration from the auth profile (see section 7).


# 14. Error Handling

Application-level errors return HTTP 200 with an error object:

```json
{
  "code": "OBJECT_NOT_FOUND",
  "message": "Description of the error",
  "objectType": "KalturaAPIException"
}
```

Validation errors (missing required fields, invalid values) return HTTP 400.

| Error Code | Meaning |
|------------|---------|
| `OBJECT_NOT_FOUND` | Auth profile or subscription not found for your partner |
| `USER_GROUPS_SYNC_ALL_FALSE_AND_GROUPS_MISSING` | `userGroupsSyncAll` is `false` but `userGroupMappings` field is missing — include `userGroupMappings` (even empty `{}`) |
| `INVALID_AUTH_STRATEGY` | `authStrategy` value is not `saml` or `oauth2` |
| `INVALID_PROVIDER_TYPE` | `providerType` value is not one of `azure`, `okta`, `aws`, `akamai`, `other` |
| `FEATURE_AUTH_BROKER_PERMISSION` | Partner does not have Auth Broker enabled — contact Kaltura support |
| `INVALID_KS` | KS is expired, malformed, or missing |
| `UNKNOWN_PARTNER_ID` | KS does not contain a valid partner ID |

**Retry strategy:** For transient errors (HTTP 5xx, timeouts), retry with exponential backoff: 1s, 2s, 4s, with jitter, up to 3 retries. For client errors (HTTP 400, `OBJECT_NOT_FOUND`, `USER_GROUPS_SYNC_ALL_FALSE_AND_GROUPS_MISSING`), fix the request before retrying — these will not resolve on their own.


# 15. Best Practices

- **Always include `userGroupMappings` when creating profiles.** Even if empty (`{}`), this field is required when `userGroupsSyncAll` is `false` to avoid validation errors.
- **Use `HTTP-POST` as the redirect method.** This prevents KS and JWT tokens from appearing in browser URL bars, server logs, and referrer headers.
- **Match callback URLs to your region.** The `callbackUrl` and `logoutCallbackUrl` in `authStrategyConfig` must use the same regional hostname as your Auth Broker base URL.
- **Download SP metadata for IdP setup.** Use the `/auth-manager/saml/metadata/{partnerId}/{profileId}` endpoint to get the SP metadata XML and upload it to your IdP.
- **Use `generatePvKeys` before enabling request signing.** Generate a key pair first, then set `enableRequestSign: true` on the profile update.
- **Set `createNewUser: true` for self-service SSO.** JIT provisioning reduces manual user management. Combine with group sync to automate role assignment.
- **Use `removeFromExistingGroups: true` for strict access control.** This ensures Kaltura group membership mirrors IdP state exactly, revoking access when users leave IdP groups.
- **Use AppTokens for production integrations.** Generate KS via `appToken.startSession` with HMAC — keep admin secrets off application servers.
- **Test with a single app subscription first.** Validate the full SSO flow (token generation, IdP redirect, callback, user provisioning) with one app before rolling out to multiple applications.


# 16. Related Guides

- **[Session Guide](KALTURA_SESSION_GUIDE.md)** — KS generation and management (Auth Broker uses KS prefix auth)
- **[AppTokens API](KALTURA_APPTOKENS_API.md)** — Secure server-to-server auth for production
- **[User Management API](KALTURA_USER_MANAGEMENT_API.md)** — Core user CRUD (Auth Broker provisions users via this API)
- **[User Profile API](KALTURA_USER_PROFILE_API.md)** — Per-app user profiles and event registration data
- **[App Registry API](KALTURA_APP_REGISTRY_API.md)** — Application instance registry (provides `appGuid` for subscriptions)
- **[Events Platform API](KALTURA_EVENTS_PLATFORM_API.md)** — Virtual events (uses Auth Broker for SSO login)

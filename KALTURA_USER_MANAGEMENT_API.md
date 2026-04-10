# Kaltura User Management API

The User Management API covers the core user identity layer: creating and managing users (`KalturaUser`), assigning roles for RBAC (`KalturaUserRole`), and managing group membership (`groupUser`). Every Kaltura service that references a userId — User Profile, Messaging, Events Platform, Webhooks — depends on a KalturaUser existing first.

**Base URL:** `https://www.kaltura.com/api_v3` (may differ by region/deployment)
**Auth:** KS passed as `ks` parameter in POST form data (see [Session Guide](KALTURA_SESSION_GUIDE.md))
**Format:** Form-encoded POST, `format=1` for JSON responses
**Services:** `user` (22 actions), `userRole` (6 actions), `group_group` (CRUD), `groupUser` (5 actions)


# 1. Authentication

All endpoints require an ADMIN KS (type=2) with appropriate permissions:

- **User CRUD:** `ADMIN_BASE` + `ADMIN_USER_ADD/UPDATE/DELETE` permissions
- **User Role CRUD:** `ADMIN_BASE` + `ADMIN_ROLE_ADD/UPDATE/DELETE` permissions
- **Group membership:** `CONTENT_MANAGE_ASSIGN_USER_GROUP` permission

Generate an ADMIN KS via `session.start` (see [Session Guide](KALTURA_SESSION_GUIDE.md)) or `appToken.startSession` (see [AppTokens Guide](KALTURA_APPTOKENS_API.md)).

```bash
# Set up environment
export KALTURA_SERVICE_URL="https://www.kaltura.com/api_v3"
```


# 2. KalturaUser Object

Every user in a Kaltura partner account is a `KalturaUser`:

| Field | Type | Description |
|-------|------|-------------|
| `id` | string | User identifier (set on creation, immutable). Often an email or username. |
| `partnerId` | integer | Partner ID (read-only, from KS) |
| `screenName` | string | Display name shown in UI |
| `fullName` | string | First + last name (read-only, derived from `firstName` + `lastName`) |
| `firstName` | string | First name |
| `lastName` | string | Last name |
| `email` | string | Email address |
| `type` | integer | `0` = USER (default), `200` = GROUP |
| `status` | integer | `0` = BLOCKED, `1` = ACTIVE, `2` = DELETED |
| `isAdmin` | boolean | Whether the user has admin privileges |
| `roleIds` | string | Comma-separated user role IDs |
| `roleNames` | string | Comma-separated role names (read-only) |
| `loginEnabled` | boolean | Whether the user can log in with credentials (read-only) |
| `externalId` | string | External identifier — set by [Auth Broker](KALTURA_AUTH_BROKER_API.md) for SSO users |
| `title` | string | Job title |
| `company` | string | Company name |
| `country` | string | Country |
| `state` | string | State/province |
| `city` | string | City |
| `zip` | string | Postal code |
| `thumbnailUrl` | string | User avatar URL |
| `description` | string | Free-text description |
| `tags` | string | Comma-separated tags |
| `dateOfBirth` | integer | Unix timestamp |
| `gender` | integer | `0` = UNKNOWN, `1` = MALE, `2` = FEMALE |
| `userMode` | integer | `0` = NORMAL, `1` = PROTECTED_ADMIN |
| `isSsoExcluded` | boolean | Whether user is excluded from SSO enforcement |
| `createdAt` | integer | Unix timestamp (read-only) |
| `updatedAt` | integer | Unix timestamp (read-only) |
| `lastLoginTime` | integer | Unix timestamp of last login (read-only) |
| `objectType` | string | Always `"KalturaUser"` (read-only) |

## 2.1 User Status Values

| Value | Name | Description |
|-------|------|-------------|
| 0 | BLOCKED | User is blocked — cannot create sessions |
| 1 | ACTIVE | Normal active user |
| 2 | DELETED | Soft-deleted |

## 2.2 User Types

| Value | Name | Description |
|-------|------|-------------|
| 0 | USER | Standard user |
| 200 | GROUP | Group (a virtual user that holds group membership via `groupUser`) |


# 3. User Provisioning Pathways

Users are created through several pathways:

| Pathway | How It Works | userId Format |
|---------|-------------|---------------|
| **API** (`user.add`) | Direct creation via API v3 | You set the `id` field |
| **CSV bulk import** | `user.addFromBulkUpload` with CSV file | From CSV column |
| **JIT via AuthBroker** | SSO login auto-creates user if `createNewUser: true` | From IdP `userIdAttribute` (typically email) |
| **Events registration** | User Profile API creates user internally if needed | Email address |
| **KMC admin UI** | Manual creation in Management Console | Email address |

## 3.1 Shared Users (SSO)

When [Auth Broker](KALTURA_AUTH_BROKER_API.md) provisions a user via SSO, it sets `externalId` on the KalturaUser to the value from the IdP's `userIdAttribute` (typically the email). This `externalId` becomes the shared key for looking up users across SSO logins.


# 4. User CRUD

## 4.1 Create a User

```
POST /service/user/action/add
```

```bash
curl -X POST "$KALTURA_SERVICE_URL/service/user/action/add" \
  -d "ks=$KALTURA_KS" \
  -d "format=1" \
  -d "user[objectType]=KalturaUser" \
  -d "user[id]=jane.doe@example.com" \
  -d "user[firstName]=Jane" \
  -d "user[lastName]=Doe" \
  -d "user[email]=jane.doe@example.com" \
  -d "user[type]=0"
```

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `user[objectType]` | string | Yes | Always `KalturaUser` |
| `user[id]` | string | Yes | Unique user identifier |
| `user[firstName]` | string | No | First name |
| `user[lastName]` | string | No | Last name |
| `user[email]` | string | No | Email address |
| `user[type]` | integer | No | `0` = USER (default), `200` = GROUP |
| `user[isAdmin]` | boolean | No | Grant admin privileges |
| `user[roleIds]` | string | No | Comma-separated role IDs to assign |
| `user[tags]` | string | No | Comma-separated tags |

**Response:** Full `KalturaUser` object with `status=1` (ACTIVE).

## 4.2 Get a User

```bash
curl -X POST "$KALTURA_SERVICE_URL/service/user/action/get" \
  -d "ks=$KALTURA_KS" \
  -d "format=1" \
  -d "userId=jane.doe@example.com"
```

Returns the full `KalturaUser` object. Returns `INVALID_USER_ID` if the user does not exist.

## 4.3 List Users

```bash
curl -X POST "$KALTURA_SERVICE_URL/service/user/action/list" \
  -d "ks=$KALTURA_KS" \
  -d "format=1" \
  -d "filter[objectType]=KalturaUserFilter" \
  -d "filter[statusEqual]=1" \
  -d "filter[orderBy]=-createdAt" \
  -d "pager[pageSize]=50" \
  -d "pager[pageIndex]=1"
```

**Filter fields (`KalturaUserFilter`):**

| Field | Description |
|-------|-------------|
| `idEqual` | Exact user ID match |
| `idIn` | Comma-separated list of user IDs |
| `statusEqual` | Filter by status (0, 1, 2) |
| `statusIn` | Comma-separated status values |
| `typeEqual` | Filter by type (0 = USER, 200 = GROUP) |
| `isAdminEqual` | Filter by admin flag |
| `firstNameStartsWith` | First name prefix match |
| `lastNameStartsWith` | Last name prefix match |
| `emailStartsWith` | Email prefix match |
| `tagsMultiLikeOr` | Tags (OR match) |
| `roleIdsEqual` | Filter by assigned role ID |
| `loginEnabledEqual` | Filter by login-enabled status |
| `createdAtGreaterThanOrEqual` | Unix timestamp minimum |
| `createdAtLessThanOrEqual` | Unix timestamp maximum |
| `orderBy` | `+createdAt`, `-createdAt`, `+updatedAt`, `-updatedAt` |

**Response:**

```json
{
  "totalCount": 42,
  "objects": [
    {
      "id": "jane.doe@example.com",
      "firstName": "Jane",
      "lastName": "Doe",
      "status": 1,
      "objectType": "KalturaUser"
    }
  ],
  "objectType": "KalturaUserListResponse"
}
```

## 4.4 Update a User

```bash
curl -X POST "$KALTURA_SERVICE_URL/service/user/action/update" \
  -d "ks=$KALTURA_KS" \
  -d "format=1" \
  -d "userId=jane.doe@example.com" \
  -d "user[objectType]=KalturaUser" \
  -d "user[firstName]=Janet" \
  -d "user[title]=Engineering Lead" \
  -d "user[company]=Acme Corp"
```

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `userId` | string | Yes | User to update |
| `user[objectType]` | string | Yes | Always `KalturaUser` |
| `user[firstName]` | string | No | Updated first name |
| `user[lastName]` | string | No | Updated last name |
| `user[email]` | string | No | Updated email |
| `user[roleIds]` | string | No | Updated role assignments |
| `user[isAdmin]` | boolean | No | Update admin status |
| `user[tags]` | string | No | Updated tags |

Fields not included remain unchanged. The `id` field cannot be changed after creation.

**Response:** Full updated `KalturaUser` object.

## 4.5 Delete a User

```bash
curl -X POST "$KALTURA_SERVICE_URL/service/user/action/delete" \
  -d "ks=$KALTURA_KS" \
  -d "format=1" \
  -d "userId=jane.doe@example.com"
```

Soft-deletes the user (`status` changes to `2`). The user object is returned with the updated status.

**Cascade behavior:** Deleting a KalturaUser soft-deletes all associated [User Profiles](KALTURA_USER_PROFILE_API.md) across all app instances. Delete user profiles explicitly first if you need to control the order.


# 5. Login & Credentials

## 5.1 Enable Login

Grant a user the ability to log in with email + password:

```bash
curl -X POST "$KALTURA_SERVICE_URL/service/user/action/enableLogin" \
  -d "ks=$KALTURA_KS" \
  -d "format=1" \
  -d "userId=jane.doe@example.com" \
  -d "loginId=jane.doe@example.com" \
  -d "password=SecureP@ssw0rd123"
```

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `userId` | string | Yes | User to enable login for |
| `loginId` | string | Yes | Login identifier (typically the email) |
| `password` | string | No | Initial password (auto-generated if omitted) |

After enabling login, the user's `loginEnabled` field becomes `true`.

## 5.2 Disable Login

```bash
curl -X POST "$KALTURA_SERVICE_URL/service/user/action/disableLogin" \
  -d "ks=$KALTURA_KS" \
  -d "format=1" \
  -d "userId=jane.doe@example.com"
```

Removes the user's ability to log in with credentials. SSO login via [Auth Broker](KALTURA_AUTH_BROKER_API.md) is not affected by this setting.

## 5.3 Login by Credentials

```bash
curl -X POST "$KALTURA_SERVICE_URL/service/user/action/loginByLoginId" \
  -d "format=1" \
  -d "loginId=jane.doe@example.com" \
  -d "password=SecureP@ssw0rd123" \
  -d "partnerId=$KALTURA_PARTNER_ID"
```

Returns a KS string on success. This action does not require an existing KS.

## 5.4 Reset Password

```bash
curl -X POST "$KALTURA_SERVICE_URL/service/user/action/resetPassword" \
  -d "format=1" \
  -d "email=jane.doe@example.com"
```

Sends a password reset email. Does not require a KS.

## 5.5 Set Initial Password

```bash
curl -X POST "$KALTURA_SERVICE_URL/service/user/action/setInitialPassword" \
  -d "format=1" \
  -d "hashKey=$HASH_KEY" \
  -d "newPassword=NewSecureP@ss456"
```

Sets a password using a hash key received via email (from `resetPassword` or invitation). Does not require a KS.


# 6. User Roles (RBAC)

Roles define what permissions a user has. Each role is a set of named permissions. Assign roles to users via `user[roleIds]`.

## 6.1 KalturaUserRole Object

| Field | Type | Description |
|-------|------|-------------|
| `id` | integer | Auto-generated role ID (read-only) |
| `name` | string | Role display name |
| `systemName` | string | System-level name (for built-in roles) |
| `description` | string | Role description |
| `status` | integer | `1` = ACTIVE, `3` = DELETED |
| `partnerId` | integer | `0` for system roles, your partner ID for custom roles |
| `permissionNames` | string | Comma-separated permission names |
| `tags` | string | Comma-separated tags |
| `createdAt` | integer | Unix timestamp (read-only) |
| `updatedAt` | integer | Unix timestamp (read-only) |

## 6.2 Create a Role

```bash
curl -X POST "$KALTURA_SERVICE_URL/service/userRole/action/add" \
  -d "ks=$KALTURA_KS" \
  -d "format=1" \
  -d "userRole[objectType]=KalturaUserRole" \
  -d "userRole[name]=Content Viewer" \
  -d "userRole[description]=Read-only access to content" \
  -d "userRole[permissionNames]=BASE_USER_SESSION_PERMISSION,PLAYBACK_BASE_PERMISSION"
```

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `userRole[objectType]` | string | Yes | Always `KalturaUserRole` |
| `userRole[name]` | string | Yes | Role name |
| `userRole[description]` | string | No | Description |
| `userRole[permissionNames]` | string | Yes | Comma-separated permission names |
| `userRole[tags]` | string | No | Tags for categorization |

**Common permission names:**

| Permission | Description |
|------------|-------------|
| `BASE_USER_SESSION_PERMISSION` | Required for basic user sessions |
| `PLAYBACK_BASE_PERMISSION` | View/play content |
| `CONTENT_INGEST_UPLOAD` | Upload content |
| `CONTENT_MANAGE_BASE` | Basic content management |
| `CONTENT_MANAGE_DELETE` | Delete content |
| `CONTENT_MANAGE_METADATA` | Edit content metadata |
| `ADMIN_BASE` | Admin panel access |
| `ANALYTICS_BASE` | View analytics |

**Response:** Full `KalturaUserRole` object with generated `id`.

## 6.3 Get a Role

```bash
curl -X POST "$KALTURA_SERVICE_URL/service/userRole/action/get" \
  -d "ks=$KALTURA_KS" \
  -d "format=1" \
  -d "userRoleId=12345"
```

## 6.4 List Roles

```bash
curl -X POST "$KALTURA_SERVICE_URL/service/userRole/action/list" \
  -d "ks=$KALTURA_KS" \
  -d "format=1" \
  -d "filter[objectType]=KalturaUserRoleFilter" \
  -d "filter[statusEqual]=1" \
  -d "filter[tagsMultiLikeOr]=custom" \
  -d "pager[pageSize]=50"
```

**Filter fields (`KalturaUserRoleFilter`):**

| Field | Description |
|-------|-------------|
| `idEqual` | Exact role ID |
| `idIn` | Comma-separated role IDs |
| `statusEqual` | `1` = ACTIVE, `3` = DELETED |
| `nameEqual` | Exact name match |
| `systemNameEqual` | Exact system name match |
| `tagsMultiLikeOr` | Tags (OR match) |
| `orderBy` | `+id`, `-id`, `+createdAt`, `-createdAt` |

## 6.5 Update a Role

```bash
curl -X POST "$KALTURA_SERVICE_URL/service/userRole/action/update" \
  -d "ks=$KALTURA_KS" \
  -d "format=1" \
  -d "userRoleId=12345" \
  -d "userRole[objectType]=KalturaUserRole" \
  -d "userRole[description]=Updated permissions" \
  -d "userRole[permissionNames]=BASE_USER_SESSION_PERMISSION,PLAYBACK_BASE_PERMISSION,CONTENT_MANAGE_BASE"
```

## 6.6 Clone a Role

```bash
curl -X POST "$KALTURA_SERVICE_URL/service/userRole/action/clone" \
  -d "ks=$KALTURA_KS" \
  -d "format=1" \
  -d "userRoleId=12345"
```

Creates a copy of an existing role. Useful for customizing built-in system roles without modifying the originals.

## 6.7 Delete a Role

```bash
curl -X POST "$KALTURA_SERVICE_URL/service/userRole/action/delete" \
  -d "ks=$KALTURA_KS" \
  -d "format=1" \
  -d "userRoleId=12345"
```

Sets `status=3` (DELETED). Users currently assigned this role retain it until their `roleIds` are updated.

## 6.8 Assigning Roles to Users

Use `user.update` with the `roleIds` field to assign one or more roles:

```bash
curl -X POST "$KALTURA_SERVICE_URL/service/user/action/update" \
  -d "ks=$KALTURA_KS" \
  -d "format=1" \
  -d "userId=jane.doe@example.com" \
  -d "user[objectType]=KalturaUser" \
  -d "user[roleIds]=12345"
```

Use this role ID with the `setrole:ROLE_ID` KS privilege (see [Session Guide](KALTURA_SESSION_GUIDE.md)) to create sessions that inherit the role's permissions.


# 7. Groups

Groups are virtual users (`type=200`) that hold membership via the `groupUser` service. Use groups as recipients in the [Messaging API](KALTURA_MESSAGING_API.md), notification targets in the [Webhooks API](KALTURA_WEBHOOKS_API.md), or for content entitlement via category membership.

## 7.1 Create a Group

Groups are created via the `group_group` service with `KalturaGroup`:

```bash
curl -X POST "$KALTURA_SERVICE_URL/service/group_group/action/add" \
  -d "ks=$KALTURA_KS" \
  -d "format=1" \
  -d "group[objectType]=KalturaGroup" \
  -d "group[id]=engineering-team" \
  -d "group[screenName]=Engineering Team" \
  -d "group[tags]=department"
```

**Response:** A `KalturaGroup` object (status=1, membersCount=0). Delete groups via `group_group.delete` with `groupId`.

## 7.2 Add User to Group

```bash
curl -X POST "$KALTURA_SERVICE_URL/service/groupUser/action/add" \
  -d "ks=$KALTURA_KS" \
  -d "format=1" \
  -d "groupUser[objectType]=KalturaGroupUser" \
  -d "groupUser[groupId]=engineering-team" \
  -d "groupUser[userId]=jane.doe@example.com"
```

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `groupUser[objectType]` | string | Yes | Always `KalturaGroupUser` |
| `groupUser[groupId]` | string | Yes | Group ID (must exist with type=200) |
| `groupUser[userId]` | string | Yes | User ID to add to the group |

**Response:**

```json
{
  "userId": "jane.doe@example.com",
  "groupId": "engineering-team",
  "status": 0,
  "partnerId": 976461,
  "createdAt": 1718467200,
  "updatedAt": 1718467200,
  "objectType": "KalturaGroupUser"
}
```

## 7.3 List Group Members

```bash
curl -X POST "$KALTURA_SERVICE_URL/service/groupUser/action/list" \
  -d "ks=$KALTURA_KS" \
  -d "format=1" \
  -d "filter[objectType]=KalturaGroupUserFilter" \
  -d "filter[groupIdEqual]=engineering-team"
```

**Filter fields (`KalturaGroupUserFilter`):**

At least one of these is required:

| Field | Description |
|-------|-------------|
| `groupIdEqual` | List members of a specific group |
| `groupIdIn` | List members of multiple groups |
| `userIdEqual` | List groups a specific user belongs to |
| `userIdIn` | List groups for multiple users |

## 7.4 Remove User from Group

```bash
curl -X POST "$KALTURA_SERVICE_URL/service/groupUser/action/delete" \
  -d "ks=$KALTURA_KS" \
  -d "format=1" \
  -d "userId=jane.doe@example.com" \
  -d "groupId=engineering-team"
```

## 7.5 Sync Group Membership

Replace all members of a group at once. Used by [Auth Broker](KALTURA_AUTH_BROKER_API.md) to sync IdP group claims to Kaltura groups:

```bash
curl -X POST "$KALTURA_SERVICE_URL/service/groupUser/action/sync" \
  -d "ks=$KALTURA_KS" \
  -d "format=1" \
  -d "userId=jane.doe@example.com" \
  -d "groupIds=engineering-team,product-team"
```

Sets the user's group membership to exactly the specified groups, removing them from any groups not in the list.


# 8. Bulk Operations

## 8.1 Bulk Upload Users

Import users from a CSV file:

```bash
curl -X POST "$KALTURA_SERVICE_URL/service/user/action/addFromBulkUpload" \
  -d "ks=$KALTURA_KS" \
  -d "format=1" \
  -F "fileData=@users.csv" \
  -F "bulkUploadData[objectType]=KalturaBulkUploadCsvJobData"
```

CSV columns: `userId`, `screenName`, `firstName`, `lastName`, `email`, `tags`, `gender`, `country`, `state`, `city`, `zip`, `dateOfBirth`, `description`, `company`, `title`.

## 8.2 Export Users to CSV

```bash
curl -X POST "$KALTURA_SERVICE_URL/service/user/action/exportToCsv" \
  -d "ks=$KALTURA_KS" \
  -d "format=1" \
  -d "filter[objectType]=KalturaUserFilter" \
  -d "filter[statusEqual]=1"
```

Returns a job ID. Retrieve the CSV file when the job completes using `user.serveCsv`.


# 9. Error Handling

| Error Code | Meaning |
|------------|---------|
| `INVALID_USER_ID` | User ID not found |
| `USER_ALREADY_EXISTS` | A user with this ID already exists |
| `USER_ROLE_NOT_FOUND` | Role ID not found |
| `INVALID_ROLE_ID` | Role ID is invalid |
| `PROPERTY_VALIDATION_CANNOT_BE_NULL` | Required filter property missing (e.g., groupUser.list needs groupIdEqual or userIdEqual) |
| `LOGIN_DATA_NOT_FOUND` | Login credentials not found for user |
| `PASSWORD_STRUCTURE_INVALID` | Password does not meet complexity requirements |
| `ADMIN_LOGIN_USERS_QUOTA_EXCEEDED` | Maximum admin users reached for the account |
| `USER_LOGIN_ALREADY_ENABLED` | Login already enabled for this user |
| `USER_LOGIN_ALREADY_DISABLED` | Login already disabled for this user |
| `INVALID_FIELD_VALUE` | Invalid value for a field (e.g., invalid email format) |

**Retry strategy:** For transient errors (HTTP 5xx, timeouts), retry with exponential backoff: 1s, 2s, 4s, with jitter, up to 3 retries. For client errors (HTTP 400, `INVALID_USER_ID`, `USER_ALREADY_EXISTS`), fix the request before retrying.


# 10. Best Practices

- **Use meaningful user IDs.** Email addresses work well as user IDs — they're unique, recognizable, and match the pattern used by AuthBroker SSO provisioning.
- **Use AppTokens for production auth.** Generate KS via `appToken.startSession` with HMAC — keep admin secrets off application servers. See [AppTokens API](KALTURA_APPTOKENS_API.md).
- **Scope roles with least privilege.** Create custom roles with only the permissions needed. Start from `BASE_USER_SESSION_PERMISSION` and add specific permissions. Use `userRole.clone` to customize built-in roles without modifying originals.
- **Prefer `setrole` over `isAdmin`.** Instead of making users admin, create a scoped role and use `setrole:ROLE_ID` in KS privileges (see [Session Guide](KALTURA_SESSION_GUIDE.md)) to limit what a session can do.
- **Clean up user profiles before deleting users.** Deleting a KalturaUser cascades to all User Profiles. If you need to preserve profile data or control the order, delete profiles first via the [User Profile API](KALTURA_USER_PROFILE_API.md).
- **Use groups for batch operations.** Create groups and use them as recipients in [Messaging](KALTURA_MESSAGING_API.md) and notification targets in [Webhooks](KALTURA_WEBHOOKS_API.md) rather than managing individual user lists.
- **Use `groupUser.sync` for SSO group management.** When integrating with an IdP that provides group claims, use sync to keep Kaltura groups in lockstep with the IdP rather than manual add/delete.


# 11. Related Guides

- **[Session Guide](KALTURA_SESSION_GUIDE.md)** — KS generation, `setrole:ROLE_ID` privilege, user vs admin sessions
- **[AppTokens API](KALTURA_APPTOKENS_API.md)** — Secure auth without admin secrets, privilege scoping
- **[Auth Broker API](KALTURA_AUTH_BROKER_API.md)** — SSO/SAML configuration, JIT user provisioning, group sync from IdP
- **[User Profile API](KALTURA_USER_PROFILE_API.md)** — Per-app user profiles, event registration and attendance (depends on KalturaUser existing)
- **[App Registry API](KALTURA_APP_REGISTRY_API.md)** — Application instance registration (apps reference users)
- **[Messaging API](KALTURA_MESSAGING_API.md)** — Email messaging to users and groups
- **[Webhooks API](KALTURA_WEBHOOKS_API.md)** — Event notifications targeting users and groups
- **[Events Platform API](KALTURA_EVENTS_PLATFORM_API.md)** — Virtual events with team members (userId in KS required)
- **[Categories & Access Control API](KALTURA_CATEGORIES_AND_ACCESS_CONTROL_API.md)** — Content organization with user-based category membership and entitlements

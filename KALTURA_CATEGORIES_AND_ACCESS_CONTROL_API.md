# Kaltura Categories & Access Control API

The Categories & Access Control API covers content organization and permissions: creating category hierarchies (`KalturaCategory`), managing category membership (`categoryUser`), assigning content to categories (`categoryEntry`), and controlling playback/access via access control profiles (`KalturaAccessControlProfile`). Categories are the foundation for Kaltura's entitlement system, which restricts content visibility based on user membership and KS privileges.

**Base URL:** `https://www.kaltura.com/api_v3` (may differ by region/deployment)  
**Auth:** KS passed as `ks` parameter in POST form data (see [Session Guide](KALTURA_SESSION_GUIDE.md))  
**Format:** Form-encoded POST, `format=1` for JSON responses  
**Services:** `category` (11 actions), `categoryUser` (10 actions), `categoryEntry` (9 actions), `accessControlProfile` (5 actions)  


# 1. Authentication

All endpoints require an ADMIN KS (type=2) with appropriate permissions:

- **Category CRUD:** `CONTENT_MANAGE_CATEGORY` permission
- **Category membership:** `CONTENT_MANAGE_CATEGORY` permission
- **Content assignment:** `CONTENT_MANAGE_ASSIGN_ENTRY_TO_CATEGORY` permission
- **Access control profiles:** `ACCESS_CONTROL_BASE` permission

Generate an ADMIN KS via `session.start` (see [Session Guide](KALTURA_SESSION_GUIDE.md)) or `appToken.startSession` (see [AppTokens Guide](KALTURA_APPTOKENS_API.md)).

```bash
# Set up environment
export KALTURA_SERVICE_URL="https://www.kaltura.com/api_v3"
```


# 2. KalturaCategory Object

Every category in a Kaltura partner account is a `KalturaCategory`:

| Field | Type | Description |
|-------|------|-------------|
| `id` | integer | Auto-generated category ID (read-only) |
| `name` | string | Category display name |
| `parentId` | integer | Parent category ID (`0` for root-level categories) |
| `fullName` | string | Full path from root (e.g., `"Media>Training>Onboarding"`) (read-only) |
| `fullIds` | string | Full ID path from root (e.g., `"12>45>78"`) (read-only) |
| `referenceId` | string | External reference identifier |
| `description` | string | Category description |
| `tags` | string | Comma-separated tags |
| `depth` | integer | Depth in the hierarchy (`0` for root) (read-only) |
| `entriesCount` | integer | Number of entries assigned (read-only) |
| `directEntriesCount` | integer | Entries assigned directly (not via subcategories) (read-only) |
| `directSubCategoriesCount` | integer | Number of immediate child categories (read-only) |
| `membersCount` | integer | Number of category members (read-only) |
| `status` | integer | Category status (see below) |
| `privacy` | integer | Privacy level (see below) |
| `privacyContext` | string | Privacy context label for entitlement |
| `appearInList` | integer | Who can see this category in listings (see below) |
| `contributionPolicy` | integer | Who can assign content (see below) |
| `inheritanceType` | integer | `1` = INHERIT from parent, `2` = MANUAL |
| `defaultPermissionLevel` | integer | Default permission for new members |
| `owner` | string | Owner user ID |
| `partnerId` | integer | Partner ID (read-only) |
| `createdAt` | integer | Unix timestamp (read-only) |
| `updatedAt` | integer | Unix timestamp (read-only) |
| `objectType` | string | Always `"KalturaCategory"` (read-only) |

## 2.1 Category Status Values

| Value | Name | Description |
|-------|------|-------------|
| 1 | UPDATING | Category is being updated (tree restructuring in progress) |
| 2 | ACTIVE | Normal active category |
| 3 | DELETED | Soft-deleted |
| 4 | PURGED | Permanently removed |

## 2.2 Privacy Levels

| Value | Name | Description |
|-------|------|-------------|
| 1 | ALL | Content is visible to everyone |
| 2 | AUTHENTICATED_USERS | Content is visible to authenticated users only |
| 3 | MEMBERS_ONLY | Content is visible only to category members |

## 2.3 Contribution Policy

| Value | Name | Description |
|-------|------|-------------|
| 1 | ALL | Any user can assign content to this category |
| 2 | MEMBERS_WITH_CONTRIBUTION_PERMISSION | Only members with CONTRIBUTOR permission or higher can assign content |

## 2.4 Appear In List

| Value | Name | Description |
|-------|------|-------------|
| 1 | PARTNER_ONLY | Visible to all partner users |
| 3 | CATEGORY_MEMBERS_ONLY | Visible only to category members |


# 3. Category CRUD

## 3.1 Create a Category

```
POST /service/category/action/add
```

```bash
curl -X POST "$KALTURA_SERVICE_URL/service/category/action/add" \
  -d "ks=$KALTURA_KS" \
  -d "format=1" \
  -d "category[objectType]=KalturaCategory" \
  -d "category[name]=Training" \
  -d "category[description]=Training materials" \
  -d "category[tags]=training,onboarding"
```

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `category[objectType]` | string | Yes | Always `KalturaCategory` |
| `category[name]` | string | Yes | Category display name |
| `category[parentId]` | integer | No | Parent category ID (omit or `0` for root-level) |
| `category[description]` | string | No | Description text |
| `category[tags]` | string | No | Comma-separated tags |
| `category[referenceId]` | string | No | External reference ID |
| `category[privacy]` | integer | No | Privacy level (1=ALL, 2=AUTHENTICATED, 3=MEMBERS_ONLY) |
| `category[privacyContext]` | string | No | Privacy context label for entitlement |
| `category[appearInList]` | integer | No | Visibility in listings (1=PARTNER_ONLY, 3=CATEGORY_MEMBERS_ONLY) |
| `category[contributionPolicy]` | integer | No | Who can assign content (1=ALL, 2=MEMBERS_WITH_CONTRIBUTION_PERMISSION) |

**Response:**

```json
{
  "id": 12345,
  "name": "Training",
  "fullName": "Training",
  "fullIds": "12345",
  "parentId": 0,
  "depth": 0,
  "status": 2,
  "privacy": 1,
  "entriesCount": 0,
  "directEntriesCount": 0,
  "directSubCategoriesCount": 0,
  "membersCount": 0,
  "description": "Training materials",
  "tags": "training,onboarding",
  "createdAt": 1718467200,
  "updatedAt": 1718467200,
  "objectType": "KalturaCategory"
}
```

### Creating a Child Category

Pass `parentId` to create a nested category:

```bash
curl -X POST "$KALTURA_SERVICE_URL/service/category/action/add" \
  -d "ks=$KALTURA_KS" \
  -d "format=1" \
  -d "category[objectType]=KalturaCategory" \
  -d "category[name]=Onboarding" \
  -d "category[parentId]=12345" \
  -d "category[description]=Onboarding materials"
```

The response includes the computed `fullName` (e.g., `"Training>Onboarding"`) and `fullIds` (e.g., `"12345>67890"`).

## 3.2 Get a Category

```bash
curl -X POST "$KALTURA_SERVICE_URL/service/category/action/get" \
  -d "ks=$KALTURA_KS" \
  -d "format=1" \
  -d "id=12345"
```

Returns the full `KalturaCategory` object. Returns `CATEGORY_NOT_FOUND` if the ID is invalid.

## 3.3 List Categories

```bash
curl -X POST "$KALTURA_SERVICE_URL/service/category/action/list" \
  -d "ks=$KALTURA_KS" \
  -d "format=1" \
  -d "filter[objectType]=KalturaCategoryFilter" \
  -d "filter[parentIdEqual]=0" \
  -d "filter[orderBy]=-createdAt" \
  -d "pager[pageSize]=50" \
  -d "pager[pageIndex]=1"
```

**Filter fields (`KalturaCategoryFilter`):**

| Field | Description |
|-------|-------------|
| `idEqual` | Exact category ID |
| `idIn` | Comma-separated category IDs |
| `parentIdEqual` | Filter by parent category (`0` for root categories) |
| `parentIdIn` | Comma-separated parent IDs |
| `fullNameStartsWithIn` | Full path prefix match (e.g., `"Training>"`) |
| `ancestorIdIn` | Categories under any of these ancestor IDs |
| `freeText` | Free-text search across name, description, tags |
| `tagsLike` | Tags match (OR) |
| `referenceIdEqual` | Exact reference ID match |
| `statusEqual` | Filter by status (1=UPDATING, 2=ACTIVE, 3=DELETED) |
| `privacyEqual` | Filter by privacy level |
| `orderBy` | `+createdAt`, `-createdAt`, `+updatedAt`, `-updatedAt`, `+name`, `-name`, `+depth`, `-depth` |

**Response:**

```json
{
  "totalCount": 5,
  "objects": [
    {
      "id": 12345,
      "name": "Training",
      "fullName": "Training",
      "parentId": 0,
      "status": 2,
      "objectType": "KalturaCategory"
    }
  ],
  "objectType": "KalturaCategoryListResponse"
}
```

## 3.4 Update a Category

```bash
curl -X POST "$KALTURA_SERVICE_URL/service/category/action/update" \
  -d "ks=$KALTURA_KS" \
  -d "format=1" \
  -d "id=12345" \
  -d "category[objectType]=KalturaCategory" \
  -d "category[description]=Updated training materials" \
  -d "category[tags]=training,updated"
```

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `id` | integer | Yes | Category ID to update |
| `category[objectType]` | string | Yes | Always `KalturaCategory` |
| `category[name]` | string | No | Updated name |
| `category[description]` | string | No | Updated description |
| `category[tags]` | string | No | Updated tags |
| `category[privacy]` | integer | No | Updated privacy level |
| `category[appearInList]` | integer | No | Updated visibility |
| `category[contributionPolicy]` | integer | No | Updated contribution policy |

Fields not included remain unchanged. **Response:** Full updated `KalturaCategory` object.

## 3.5 Delete a Category

```bash
curl -X POST "$KALTURA_SERVICE_URL/service/category/action/delete" \
  -d "ks=$KALTURA_KS" \
  -d "format=1" \
  -d "id=12345"
```

Deletes the category. Child categories are also deleted. Entries assigned to the category are unlinked (not deleted).

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `id` | integer | Yes | Category ID to delete |
| `moveEntriesToParentCategory` | integer | No | `1` to move entries to parent before deleting |

## 3.6 Clone a Category Branch

Duplicate a category and its entire subtree:

```
POST /service/category/action/clone
```

```bash
curl -X POST "$KALTURA_SERVICE_URL/service/category/action/clone" \
  -d "ks=$KALTURA_KS" \
  -d "format=1" \
  -d "id=12345" \
  -d "cloneOptions[objectType]=KalturaCategoryClone"
```

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `id` | integer | Yes | Source category ID to clone |
| `cloneOptions[objectType]` | string | Yes | Always `KalturaCategoryClone` |

**Response:** A new `KalturaCategory` object representing the cloned root. The entire branch (all descendants) is duplicated under the same parent as the source category. The cloned categories receive new IDs while preserving the hierarchy structure, names, and settings of the source branch.


# 4. Category Hierarchy

Categories form a tree structure via the `parentId` field. The API automatically computes path fields:

| Field | Example | Description |
|-------|---------|-------------|
| `parentId` | `12345` | Direct parent category ID (`0` for root) |
| `fullName` | `"Media>Training>Onboarding"` | Full path of names separated by `>` |
| `fullIds` | `"100>12345>67890"` | Full path of IDs separated by `>` |
| `depth` | `2` | Distance from root (`0` for root categories) |

## 4.1 Move a Category

Reparent a category under a different parent:

```bash
curl -X POST "$KALTURA_SERVICE_URL/service/category/action/move" \
  -d "ks=$KALTURA_KS" \
  -d "format=1" \
  -d "categoryIds=67890" \
  -d "targetCategoryParentId=99999"
```

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `categoryIds` | string | Yes | Comma-separated category IDs to move |
| `targetCategoryParentId` | integer | Yes | New parent category ID |

Moving a category updates `fullName`, `fullIds`, and `depth` for the category and all its descendants. The category status may temporarily become `1` (UPDATING) during the move operation.

## 4.2 Traversal Patterns

**List root categories:**
```bash
curl -X POST "$KALTURA_SERVICE_URL/service/category/action/list" \
  -d "ks=$KALTURA_KS" \
  -d "format=1" \
  -d "filter[objectType]=KalturaCategoryFilter" \
  -d "filter[parentIdEqual]=0"
```

**List children of a category:**
```bash
curl -X POST "$KALTURA_SERVICE_URL/service/category/action/list" \
  -d "ks=$KALTURA_KS" \
  -d "format=1" \
  -d "filter[objectType]=KalturaCategoryFilter" \
  -d "filter[parentIdEqual]=12345"
```

**List all descendants of a category:**
```bash
curl -X POST "$KALTURA_SERVICE_URL/service/category/action/list" \
  -d "ks=$KALTURA_KS" \
  -d "format=1" \
  -d "filter[objectType]=KalturaCategoryFilter" \
  -d "filter[ancestorIdIn]=12345"
```

**Find categories by path prefix:**
```bash
curl -X POST "$KALTURA_SERVICE_URL/service/category/action/list" \
  -d "ks=$KALTURA_KS" \
  -d "format=1" \
  -d "filter[objectType]=KalturaCategoryFilter" \
  -d "filter[fullNameStartsWithIn]=Training>"
```


# 5. Category Membership (categoryUser)

Category membership controls which users belong to a category. When entitlement is enabled, membership determines who can see content assigned to `MEMBERS_ONLY` categories.

## 5.1 KalturaCategoryUser Object

| Field | Type | Description |
|-------|------|-------------|
| `categoryId` | integer | Category ID |
| `userId` | string | User ID |
| `permissionLevel` | integer | Permission level (see below) |
| `status` | integer | Membership status (see below) |
| `partnerId` | integer | Partner ID (read-only) |
| `createdAt` | integer | Unix timestamp (read-only) |
| `updatedAt` | integer | Unix timestamp (read-only) |
| `objectType` | string | Always `"KalturaCategoryUser"` (read-only) |

### Permission Levels

| Value | Name | Description |
|-------|------|-------------|
| 0 | MANAGER | Full control: manage members, content, and category settings |
| 1 | MODERATOR | Approve/reject content and members |
| 2 | CONTRIBUTOR | Add content to the category |
| 3 | MEMBER | View content only |
| 4 | NONE | No permissions (membership exists but grants nothing) |

### Membership Status

| Value | Name | Description |
|-------|------|-------------|
| 1 | ACTIVE | Active membership |
| 2 | PENDING | Awaiting approval |
| 3 | NOT_ACTIVE | Deactivated |
| 4 | DELETED | Removed |

## 5.2 Add a Member

```bash
curl -X POST "$KALTURA_SERVICE_URL/service/categoryUser/action/add" \
  -d "ks=$KALTURA_KS" \
  -d "format=1" \
  -d "categoryUser[objectType]=KalturaCategoryUser" \
  -d "categoryUser[categoryId]=12345" \
  -d "categoryUser[userId]=jane.doe@example.com" \
  -d "categoryUser[permissionLevel]=3"
```

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `categoryUser[objectType]` | string | Yes | Always `KalturaCategoryUser` |
| `categoryUser[categoryId]` | integer | Yes | Category ID |
| `categoryUser[userId]` | string | Yes | User ID to add |
| `categoryUser[permissionLevel]` | integer | No | Permission level (default: `3` MEMBER) |

**Response:** Full `KalturaCategoryUser` object with `status=1` (ACTIVE).

## 5.3 Get a Member

```bash
curl -X POST "$KALTURA_SERVICE_URL/service/categoryUser/action/get" \
  -d "ks=$KALTURA_KS" \
  -d "format=1" \
  -d "categoryId=12345" \
  -d "userId=jane.doe@example.com"
```

## 5.4 List Members

```bash
curl -X POST "$KALTURA_SERVICE_URL/service/categoryUser/action/list" \
  -d "ks=$KALTURA_KS" \
  -d "format=1" \
  -d "filter[objectType]=KalturaCategoryUserFilter" \
  -d "filter[categoryIdEqual]=12345" \
  -d "pager[pageSize]=50"
```

**Filter fields (`KalturaCategoryUserFilter`):**

| Field | Description |
|-------|-------------|
| `categoryIdEqual` | Members of a specific category |
| `categoryIdIn` | Members of multiple categories |
| `userIdEqual` | Categories a specific user belongs to |
| `userIdIn` | Categories for multiple users |
| `permissionLevelEqual` | Filter by permission level |
| `statusEqual` | Filter by membership status |
| `orderBy` | `+createdAt`, `-createdAt` |

## 5.5 Update a Member

```bash
curl -X POST "$KALTURA_SERVICE_URL/service/categoryUser/action/update" \
  -d "ks=$KALTURA_KS" \
  -d "format=1" \
  -d "categoryId=12345" \
  -d "userId=jane.doe@example.com" \
  -d "categoryUser[objectType]=KalturaCategoryUser" \
  -d "categoryUser[permissionLevel]=2"
```

Updates the permission level or other mutable fields for an existing membership.

## 5.6 Delete a Member

```bash
curl -X POST "$KALTURA_SERVICE_URL/service/categoryUser/action/delete" \
  -d "ks=$KALTURA_KS" \
  -d "format=1" \
  -d "categoryId=12345" \
  -d "userId=jane.doe@example.com"
```

## 5.7 Activate / Deactivate a Member

Activate a pending or deactivated member:

```bash
curl -X POST "$KALTURA_SERVICE_URL/service/categoryUser/action/activate" \
  -d "ks=$KALTURA_KS" \
  -d "format=1" \
  -d "categoryId=12345" \
  -d "userId=jane.doe@example.com"
```

Deactivate an active member (preserves the membership record):

```bash
curl -X POST "$KALTURA_SERVICE_URL/service/categoryUser/action/deactivate" \
  -d "ks=$KALTURA_KS" \
  -d "format=1" \
  -d "categoryId=12345" \
  -d "userId=jane.doe@example.com"
```


# 6. Content Assignment (categoryEntry)

Assign media entries to categories to organize content and enforce entitlement rules.

## 6.1 KalturaCategoryEntry Object

| Field | Type | Description |
|-------|------|-------------|
| `categoryId` | integer | Category ID |
| `entryId` | string | Entry ID |
| `status` | integer | `1` = ACTIVE, `2` = PENDING, `3` = DELETED, `4` = REJECTED |
| `createdAt` | integer | Unix timestamp (read-only) |
| `objectType` | string | Always `"KalturaCategoryEntry"` (read-only) |

## 6.2 Assign an Entry to a Category

```bash
curl -X POST "$KALTURA_SERVICE_URL/service/categoryEntry/action/add" \
  -d "ks=$KALTURA_KS" \
  -d "format=1" \
  -d "categoryEntry[objectType]=KalturaCategoryEntry" \
  -d "categoryEntry[categoryId]=12345" \
  -d "categoryEntry[entryId]=0_abc123"
```

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `categoryEntry[objectType]` | string | Yes | Always `KalturaCategoryEntry` |
| `categoryEntry[categoryId]` | integer | Yes | Target category ID |
| `categoryEntry[entryId]` | string | Yes | Entry ID to assign |

**Response:** Full `KalturaCategoryEntry` object with `status=1` (ACTIVE).

## 6.3 List Category Entries

```bash
curl -X POST "$KALTURA_SERVICE_URL/service/categoryEntry/action/list" \
  -d "ks=$KALTURA_KS" \
  -d "format=1" \
  -d "filter[objectType]=KalturaCategoryEntryFilter" \
  -d "filter[categoryIdEqual]=12345" \
  -d "pager[pageSize]=50"
```

**Filter fields (`KalturaCategoryEntryFilter`):**

| Field | Description |
|-------|-------------|
| `categoryIdEqual` | Entries in a specific category |
| `categoryIdIn` | Entries in multiple categories |
| `entryIdEqual` | Categories for a specific entry |
| `statusEqual` | Filter by status (1=ACTIVE, 2=PENDING, 3=DELETED, 4=REJECTED) |
| `orderBy` | `+createdAt`, `-createdAt` |

## 6.4 Delete a Category Entry

```bash
curl -X POST "$KALTURA_SERVICE_URL/service/categoryEntry/action/delete" \
  -d "ks=$KALTURA_KS" \
  -d "format=1" \
  -d "entryId=0_abc123" \
  -d "categoryId=12345"
```

Removes the entry from the category. The entry itself is not deleted.

## 6.5 Moderate Category Entries

When a category has `contributionPolicy=2` (MEMBERS_WITH_CONTRIBUTION_PERMISSION), new assignments may enter `PENDING` status. Moderators and managers can approve or reject:

**Activate (approve) a pending entry:**
```bash
curl -X POST "$KALTURA_SERVICE_URL/service/categoryEntry/action/activate" \
  -d "ks=$KALTURA_KS" \
  -d "format=1" \
  -d "entryId=0_abc123" \
  -d "categoryId=12345"
```

**Reject a pending entry:**
```bash
curl -X POST "$KALTURA_SERVICE_URL/service/categoryEntry/action/reject" \
  -d "ks=$KALTURA_KS" \
  -d "format=1" \
  -d "entryId=0_abc123" \
  -d "categoryId=12345"
```

## 6.6 Sync Privacy Context

Synchronize the privacy context for all entries in a category. Use this after changing a category's `privacyContext`:

```bash
curl -X POST "$KALTURA_SERVICE_URL/service/categoryEntry/action/syncPrivacyContext" \
  -d "ks=$KALTURA_KS" \
  -d "format=1" \
  -d "entryId=0_abc123" \
  -d "categoryId=12345"
```


# 7. Access Control Profiles

Access control profiles define rules that restrict who can access content and how. Profiles are assigned to entries and evaluated at playback time.

## 7.1 KalturaAccessControlProfile Object

| Field | Type | Description |
|-------|------|-------------|
| `id` | integer | Auto-generated profile ID (read-only) |
| `name` | string | Profile display name |
| `description` | string | Profile description |
| `partnerId` | integer | Partner ID (read-only) |
| `isDefault` | integer | `1` if this is the default profile |
| `rules` | array | Array of `KalturaRule` objects |
| `systemName` | string | System-level name |
| `createdAt` | integer | Unix timestamp (read-only) |
| `updatedAt` | integer | Unix timestamp (read-only) |
| `objectType` | string | Always `"KalturaAccessControlProfile"` (read-only) |

## 7.2 Rule Structure

Each rule in the `rules` array has conditions, actions, and contexts:

```json
{
  "objectType": "KalturaRule",
  "actions": [
    {"objectType": "KalturaAccessControlBlockAction"}
  ],
  "conditions": [
    {
      "objectType": "KalturaIpCondition",
      "not": true,
      "values": [
        {"objectType": "KalturaStringValue", "value": "192.168.1.0/24"}
      ]
    }
  ],
  "contexts": [
    {"objectType": "KalturaContextTypeHolder", "type": 2}
  ]
}
```

**Common condition types:**

| Condition ObjectType | Description |
|---------------------|-------------|
| `KalturaIpCondition` | Match by IP address or CIDR range |
| `KalturaCountryCondition` | Match by country code |
| `KalturaSiteCondition` | Match by referring site (domain) |
| `KalturaUserAgentCondition` | Match by user-agent string |
| `KalturaFieldMatchCondition` | Match by entry metadata field |
| `KalturaAuthenticatedCondition` | Require valid KS |

**Common action types:**

| Action ObjectType | Description |
|------------------|-------------|
| `KalturaAccessControlBlockAction` | Block access entirely |
| `KalturaAccessControlPreviewAction` | Allow preview only (set `limit` in seconds) |
| `KalturaAccessControlLimitFlavorsAction` | Restrict to specific flavor IDs |

**Context types:**

| Value | Name | Description |
|-------|------|-------------|
| 1 | PLAY | Playback context |
| 2 | DOWNLOAD | Download context |
| 3 | THUMBNAIL | Thumbnail context |
| 4 | METADATA | Metadata context |

## 7.3 Create an Access Control Profile

```bash
curl -X POST "$KALTURA_SERVICE_URL/service/accessControlProfile/action/add" \
  -d "ks=$KALTURA_KS" \
  -d "format=1" \
  -d "accessControlProfile[objectType]=KalturaAccessControlProfile" \
  -d "accessControlProfile[name]=IP Restricted" \
  -d "accessControlProfile[description]=Allow only internal IPs"
```

To add rules with conditions:

```bash
curl -X POST "$KALTURA_SERVICE_URL/service/accessControlProfile/action/add" \
  -d "ks=$KALTURA_KS" \
  -d "format=1" \
  -d "accessControlProfile[objectType]=KalturaAccessControlProfile" \
  -d "accessControlProfile[name]=IP Restricted" \
  -d "accessControlProfile[description]=Block access outside internal network" \
  -d "accessControlProfile[rules][0][objectType]=KalturaRule" \
  -d "accessControlProfile[rules][0][actions][0][objectType]=KalturaAccessControlBlockAction" \
  -d "accessControlProfile[rules][0][conditions][0][objectType]=KalturaIpCondition" \
  -d "accessControlProfile[rules][0][conditions][0][not]=true" \
  -d "accessControlProfile[rules][0][conditions][0][values][0][objectType]=KalturaStringValue" \
  -d "accessControlProfile[rules][0][conditions][0][values][0][value]=192.168.1.0/24"
```

**Response:** Full `KalturaAccessControlProfile` object with generated `id`.

## 7.4 Get an Access Control Profile

```bash
curl -X POST "$KALTURA_SERVICE_URL/service/accessControlProfile/action/get" \
  -d "ks=$KALTURA_KS" \
  -d "format=1" \
  -d "id=12345"
```

## 7.5 List Access Control Profiles

```bash
curl -X POST "$KALTURA_SERVICE_URL/service/accessControlProfile/action/list" \
  -d "ks=$KALTURA_KS" \
  -d "format=1" \
  -d "filter[objectType]=KalturaAccessControlProfileFilter" \
  -d "pager[pageSize]=50"
```

**Filter fields (`KalturaAccessControlProfileFilter`):**

| Field | Description |
|-------|-------------|
| `idEqual` | Exact profile ID |
| `idIn` | Comma-separated profile IDs |
| `systemNameEqual` | Exact system name match |
| `createdAtGreaterThanOrEqual` | Unix timestamp minimum |
| `createdAtLessThanOrEqual` | Unix timestamp maximum |
| `orderBy` | `+createdAt`, `-createdAt` |

## 7.6 Update an Access Control Profile

```bash
curl -X POST "$KALTURA_SERVICE_URL/service/accessControlProfile/action/update" \
  -d "ks=$KALTURA_KS" \
  -d "format=1" \
  -d "id=12345" \
  -d "accessControlProfile[objectType]=KalturaAccessControlProfile" \
  -d "accessControlProfile[description]=Updated IP restrictions"
```

## 7.7 Delete an Access Control Profile

```bash
curl -X POST "$KALTURA_SERVICE_URL/service/accessControlProfile/action/delete" \
  -d "ks=$KALTURA_KS" \
  -d "format=1" \
  -d "id=12345"
```

Profiles assigned to entries are unlinked before deletion. Entries revert to the partner's default access control.


# 8. Entitlement

Entitlement is Kaltura's mechanism for restricting content access based on category membership. It combines category privacy, user membership, and KS privileges.

## 8.1 How Entitlement Works

1. **Category privacy** determines the baseline access rule (`privacy` field on `KalturaCategory`).
2. **Category membership** (`categoryUser`) determines which users have access to `MEMBERS_ONLY` categories.
3. **KS privileges** control whether entitlement is enforced and which privacy contexts are applied.

## 8.2 KS Privileges for Entitlement

Enable entitlement by adding the `enableentitlement` privilege to the KS, and specify the privacy context with `privacycontext`:

```bash
# Generate a KS with entitlement enabled
curl -X POST "$KALTURA_SERVICE_URL/service/session/action/start" \
  -d "format=1" \
  -d "partnerId=$KALTURA_PARTNER_ID" \
  -d "secret=$KALTURA_ADMIN_SECRET" \
  -d "type=0" \
  -d "userId=jane.doe@example.com" \
  -d "privileges=enableentitlement,privacycontext:mycontext"
```

| Privilege | Description |
|-----------|-------------|
| `enableentitlement` | Activates entitlement enforcement for this session |
| `privacycontext:LABEL` | Sets the privacy context to match against category `privacyContext` values |
| `disableentitlement` | Explicitly disables entitlement (default for ADMIN KS) |

## 8.3 Entitlement Decision Matrix

When entitlement is enabled, content visibility depends on category privacy and user membership:

| Category Privacy | User Is Member | Result |
|-----------------|----------------|--------|
| ALL (1) | N/A | Content visible |
| AUTHENTICATED_USERS (2) | N/A | Visible if KS has valid `userId` |
| MEMBERS_ONLY (3) | Yes (ACTIVE) | Content visible |
| MEMBERS_ONLY (3) | No | Content hidden |

## 8.4 Setting Up Entitlement

1. Create a category with `privacy=3` (MEMBERS_ONLY) and a `privacyContext`:

```bash
curl -X POST "$KALTURA_SERVICE_URL/service/category/action/add" \
  -d "ks=$KALTURA_KS" \
  -d "format=1" \
  -d "category[objectType]=KalturaCategory" \
  -d "category[name]=Restricted Content" \
  -d "category[privacy]=3" \
  -d "category[privacyContext]=restricted"
```

2. Add users as members of the category:

```bash
curl -X POST "$KALTURA_SERVICE_URL/service/categoryUser/action/add" \
  -d "ks=$KALTURA_KS" \
  -d "format=1" \
  -d "categoryUser[objectType]=KalturaCategoryUser" \
  -d "categoryUser[categoryId]=12345" \
  -d "categoryUser[userId]=jane.doe@example.com" \
  -d "categoryUser[permissionLevel]=3"
```

3. Assign entries to the category:

```bash
curl -X POST "$KALTURA_SERVICE_URL/service/categoryEntry/action/add" \
  -d "ks=$KALTURA_KS" \
  -d "format=1" \
  -d "categoryEntry[objectType]=KalturaCategoryEntry" \
  -d "categoryEntry[categoryId]=12345" \
  -d "categoryEntry[entryId]=0_abc123"
```

4. Generate a user KS with entitlement privileges for the matching privacy context:

```bash
curl -X POST "$KALTURA_SERVICE_URL/service/session/action/start" \
  -d "format=1" \
  -d "partnerId=$KALTURA_PARTNER_ID" \
  -d "secret=$KALTURA_ADMIN_SECRET" \
  -d "type=0" \
  -d "userId=jane.doe@example.com" \
  -d "privileges=enableentitlement,privacycontext:restricted"
```

Only `jane.doe@example.com` (a category member) can see entries in this category when using this KS. Other users with entitlement enabled for the same `privacycontext` are unable to see the entries.


# 9. Bulk Operations

Use bulk upload actions to create categories, assign members, or assign entries in batch via CSV.

## 9.1 Bulk Category Creation

Upload a CSV file to create multiple categories at once:

```
POST /service/category/action/addFromBulkUpload
```

```bash
curl -X POST "$KALTURA_SERVICE_URL/service/category/action/addFromBulkUpload" \
  -d "ks=$KALTURA_KS" \
  -d "format=1" \
  -d "bulkUploadData[objectType]=KalturaBulkUploadCsvJobData" \
  --form "fileData=@categories.csv"
```

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `fileData` | file | Yes | CSV file with category data |
| `bulkUploadData[objectType]` | string | Yes | Always `KalturaBulkUploadCsvJobData` |
| `bulkUploadCategoryData[objectType]` | string | No | `KalturaBulkUploadCategoryData` for additional options |

**CSV columns:** `name`, `parentId`, `referenceId`, `description`, `tags`, `privacy`, `contributionPolicy`, `appearInList`, `privacyContext`

**Response:** A `KalturaBulkUpload` job object with `id`, `status`, and `uploadedBy`. Poll the job status via `bulk.get` to track completion.

## 9.2 Bulk Membership Assignment

Assign multiple users to categories in batch:

```
POST /service/categoryUser/action/addFromBulkUpload
```

```bash
curl -X POST "$KALTURA_SERVICE_URL/service/categoryUser/action/addFromBulkUpload" \
  -d "ks=$KALTURA_KS" \
  -d "format=1" \
  -d "bulkUploadData[objectType]=KalturaBulkUploadCsvJobData" \
  --form "fileData=@category_members.csv"
```

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `fileData` | file | Yes | CSV file with membership data |
| `bulkUploadData[objectType]` | string | Yes | Always `KalturaBulkUploadCsvJobData` |
| `bulkUploadCategoryUserData[objectType]` | string | No | `KalturaBulkUploadCategoryUserData` for additional options |

**CSV columns:** `categoryId`, `userId`, `permissionLevel`, `status`

**Response:** A `KalturaBulkUpload` job object. Each row creates a `KalturaCategoryUser` membership record.

## 9.3 Bulk Content Assignment

Assign multiple entries to categories in batch:

```
POST /service/categoryEntry/action/addFromBulkUpload
```

```bash
curl -X POST "$KALTURA_SERVICE_URL/service/categoryEntry/action/addFromBulkUpload" \
  -d "ks=$KALTURA_KS" \
  -d "format=1" \
  -d "bulkUploadData[objectType]=KalturaBulkUploadCsvJobData" \
  --form "fileData=@category_entries.csv"
```

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `fileData` | file | Yes | CSV file with entry-category assignments |
| `bulkUploadData[objectType]` | string | Yes | Always `KalturaBulkUploadCsvJobData` |
| `bulkUploadCategoryEntryData[objectType]` | string | No | `KalturaBulkUploadCategoryEntryData` for additional options |

**CSV columns:** `categoryId`, `entryId`

**Response:** A `KalturaBulkUpload` job object. Each row creates a `KalturaCategoryEntry` assignment.

## 9.4 Tracking Bulk Job Status

Poll the bulk upload job to check completion:

```bash
curl -X POST "$KALTURA_SERVICE_URL/service/bulk/action/get" \
  -d "ks=$KALTURA_KS" \
  -d "format=1" \
  -d "id=$BULK_JOB_ID"
```

| Status Value | Name | Description |
|-------------|------|-------------|
| 0 | PENDING | Job queued |
| 1 | UPLOADING | File is being uploaded |
| 2 | UPLOADED | File uploaded, processing not started |
| 3 | PROCESSING | Job is in progress |
| 4 | PROCESSED | Job completed (check `errorCount` for partial failures) |
| 5 | ABORTED | Job was cancelled |


# 10. Error Handling

| Error Code | Meaning |
|------------|---------|
| `CATEGORY_NOT_FOUND` | Category ID does not exist |
| `DUPLICATE_CATEGORY` | A category with this name already exists under the same parent |
| `PARENT_CATEGORY_NOT_FOUND` | The specified `parentId` does not exist |
| `MAX_CATEGORY_DEPTH_REACHED` | Category hierarchy depth limit exceeded |
| `CANNOT_DELETE_OR_UPDATE_TOP_CATEGORY` | Cannot modify the root category |
| `CATEGORY_USER_ALREADY_EXISTS` | User is already a member of this category |
| `INVALID_ENTRY_ID` | Entry ID does not exist |
| `ENTRY_CATEGORY_ALREADY_EXISTS` | Entry is already assigned to this category |
| `CATEGORY_ENTRY_NOT_FOUND` | The entry is not assigned to this category |
| `ACCESS_CONTROL_NOT_FOUND` | Access control profile ID does not exist |
| `INVALID_USER_ID` | User ID does not exist |

**Retry strategy:** For transient errors (HTTP 5xx, timeouts), retry with exponential backoff: 1s, 2s, 4s, with jitter, up to 3 retries. For client errors (HTTP 400, `CATEGORY_NOT_FOUND`, `INVALID_ENTRY_ID`), fix the request before retrying.


# 11. Best Practices

- **Design hierarchy before creating categories.** Plan your category tree structure in advance. Moving categories later triggers a full path recalculation for all descendants.
- **Use `referenceId` for external system mapping.** Store external system IDs in `referenceId` to simplify integration and avoid needing to track Kaltura category IDs.
- **Delete children before parents.** When cleaning up category trees, delete child categories first. Deleting a parent cascades to children, but explicit ordering gives you more control.
- **Use `privacyContext` to segment entitlement.** Assign different `privacyContext` labels to different category trees so you can enable entitlement for specific contexts without affecting others.
- **Keep access control profiles simple.** Start with basic rules (IP, country) and add complexity as needed. Complex rule chains are harder to debug when access is unexpectedly blocked.
- **Use `contributionPolicy=2` for moderated categories.** Combined with `MEMBERS_WITH_CONTRIBUTION_PERMISSION`, this ensures only authorized users can assign content, with moderators approving additions.
- **Use `categoryUser` for fine-grained permissions.** Permission levels (MANAGER, MODERATOR, CONTRIBUTOR, MEMBER) provide granular control without needing separate access control profiles.
- **Prefer `enableentitlement` in USER KS.** ADMIN KS has entitlement disabled by default. For production playback, generate USER KS (type=0) with `enableentitlement` and the appropriate `privacycontext`.
- **32 categories per entry limit.** An entry can be assigned to a maximum of 32 categories. Plan your category hierarchy to avoid exceeding this limit with flat structures.
- **Entitlement decision flow.** The server evaluates access in this sequence:
  1. Check for `disableentitlement` KS privilege — if present, skip all entitlement checks
  2. Check `defaultEntitlementEnforcement` account setting — if disabled, allow access
  3. Check entry ownership — owners always have access
  4. Check edit/publish permission — users with these permissions on the category can access
  5. Check category privacy — `AUTHENTICATED_USERS` allows any logged-in user; `MEMBERS_ONLY` requires explicit `categoryUser` membership
  6. If no category grants access — deny
- **Access control profiles are per-action.** Profiles evaluate based on `contextType` — `PLAY` (1) for playback, `DOWNLOAD` (3) for downloads. A profile can allow playback but deny downloads. When creating rules, set `contexts` to specify which actions the rule applies to.


# 12. Related Guides

- **[Session Guide](KALTURA_SESSION_GUIDE.md)** — `enableentitlement`, `privacycontext` KS privileges, user vs admin sessions
- **[User Management API](KALTURA_USER_MANAGEMENT_API.md)** — Users for category membership (`categoryUser` references KalturaUser IDs)
- **[eSearch API](KALTURA_ESEARCH_API.md)** — Search entries by category assignment, search categories
- **[Agents Manager API](KALTURA_AGENTS_MANAGER_API.md)** — `ENTRY_ADDED_TO_CATEGORY` trigger for AI agent workflows
- **[Webhooks API](KALTURA_WEBHOOKS_API.md)** — Category event notifications (category created, entry assigned, etc.)
- **[Player Embed Guide](KALTURA_PLAYER_EMBED_GUIDE.md)** — Access control profiles affect playback; entitlement determines content visibility in player
- **[Distribution](KALTURA_DISTRIBUTION_API.md)** — Category-based content scoping for distribution profiles
- **[Syndication](KALTURA_SYNDICATION_API.md)** — Category filters for syndication feed content
- **[Gamification](KALTURA_GAMIFICATION_API.md)** — Category-based content scoping for gamification rules
